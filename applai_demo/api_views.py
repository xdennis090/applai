from __future__ import annotations

import json
import os
import re
import time
from copy import deepcopy
from io import BytesIO

import ollama
import requests
from PIL import Image, ImageOps
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.utils import timezone
from core.models import Bewerber, ZertifizierteSkills, SoftSkills, Stationen, Leistungseintraege
from accounts.models import CoverLetter, JobBookmark, PhotoSession, UserProfile
from applai_demo.prompt_templates import get_template_by_tone

User = get_user_model()

SAMPLE_JOBS = [
    {
        "title": "Werkstudent:in KI",
        "company": "ApplAI GmbH",
        "location": "Remote",
        "description": "Unterstützung beim Aufbau des KI-Bewerbungsassistenten.",
        "link": "https://example.com/jobs/applai-werkstudent",
    },
    {
        "title": "AI Product Associate",
        "company": "NextGen Labs",
        "location": "München",
        "description": "Koordination von LLM-Workflows und UX-Tests.",
        "link": "https://example.com/jobs/nextgen-associate",
    },
    {
        "title": "Junior Computer Vision",
        "company": "PixelPerfect",
        "location": "Augsburg",
        "description": "Bildoptimierung, Diffusion-Pipelines und Deployment.",
        "link": "https://example.com/jobs/pixelperfect-cv",
    },
    {
        "title": "Junior AI Developer (w/m/d)",
        "company": "anders & ganz GmbH",
        "location": "Hamburg / Berlin / Aachen",
        "description": "Entwicklung generativer KI-Anwendungen und KI-Agentensysteme. Schwerpunkt: Python, moderne KI-Frameworks, APIs und eigene Bibliotheken. Wir suchen jemanden mit Hands-on-Mentalität und MINT-Master-Abschluss.",
        "link": "https://www.anders-ganz.de/karriere/",
    },
]

DEFAULT_PROFILE = {
    "contact_email": "",
    "phone": "",
    "location": "",
    "education": "",
    "experience": "",
    "skills": [],
    "soft_skills": [],
    "hobbies": [],
    "resume_text": "",
}

COMFY_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFY_CHECKPOINT = os.getenv("COMFYUI_CHECKPOINT", "realvisxlV50_v50LightningBakedvae.safetensors")
COMFY_NEGATIVE_PROMPT = os.getenv(
    "COMFYUI_NEGATIVE_PROMPT",
    "lowres, blurry, distorted, bad hands, noisy background, changed identity, face swap, extra face, deformed face, gender swap",
)
COMFY_TIMEOUT = float(os.getenv("COMFYUI_TIMEOUT", "45"))
COMFY_STEPS = int(os.getenv("COMFYUI_STEPS", "18"))
COMFY_MAX_EDGE = 896
COMFY_DENOISE = float(os.getenv("COMFYUI_DENOISE", "0.30"))
DEFAULT_PHOTO_PROMPT = os.getenv(
    "COMFYUI_PHOTO_PROMPT",
    "professional corporate portrait, person wearing a simple elegant green blazer, high-end studio lighting, (modern blurred office background:1.3), soft bokeh, photorealistic, 8k, highly detailed",
)

# Reuse a single HTTP session to avoid socket exhaustion when talking to ComfyUI repeatedly.
_HTTP = requests.Session()
_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=8)
_HTTP.mount("http://", _ADAPTER)
_HTTP.mount("https://", _ADAPTER)


def _json(request) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _password_errors(password: str) -> list[str]:
    """Return human-readable password violations."""
    errors = []
    if len(password) < 8:
        errors.append("mindestens 8 Zeichen")
    if not re.search(r"[A-Za-z]", password):
        errors.append("mindestens ein Buchstabe")
    if not re.search(r"\d", password):
        errors.append("mindestens eine Zahl")
    return errors


def _ensure_profile(user: User) -> UserProfile:
    defaults = deepcopy(DEFAULT_PROFILE)
    defaults["contact_email"] = user.email or ""
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults=defaults)
    return profile


def _user_payload(user: User) -> dict:
    profile = _ensure_profile(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "profile": profile.as_payload(),
    }


def _comfy_url(path: str) -> str:
    base = COMFY_BASE_URL.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _build_bewerbungsfoto_workflow(image_name: str, prompt_text: str, negative_prompt: str, checkpoint: str) -> dict:
    seed = int(time.time()) % 2_147_483_647
    controlnet_model_name = "diffusion_pytorch_model.fp16.safetensors"
    return {
        "load_checkpoint": {"inputs": {"ckpt_name": checkpoint}, "class_type": "CheckpointLoaderSimple"},
        "load_image": {"inputs": {"image": image_name}, "class_type": "LoadImage"},
        "face_mask": {
            "inputs": {
                "image": ["load_image", 0], 
                "text": "face and hair",  
                "blur": 4.0,               
                "threshold": 0.4,         
                "dilation_factor": 1.9         
            },
            "class_type": "CLIPSeg"
        },
        "invert_mask": {"inputs": {"mask": ["face_mask", 0]}, "class_type": "InvertMask"},
        "load_controlnet": {"inputs": {"control_net_name": controlnet_model_name}, "class_type": "ControlNetLoader"},
        "canny_preprocessor": {
            "inputs": {"image": ["load_image", 0], "low_threshold": 100, "high_threshold": 200},
            "class_type": "CannyEdgePreprocessor"
        },
        "apply_controlnet": {
            "inputs": {
                "strength": 0.6,             
                "conditioning": ["positive", 0],
                "control_net": ["load_controlnet", 0],
                "image": ["canny_preprocessor", 0]
            },
            "class_type": "ControlNetApply"
        },
        "positive": {"inputs": {"text": prompt_text, "clip": ["load_checkpoint", 1]}, "class_type": "CLIPTextEncode"},
        "negative": {"inputs": {"text": negative_prompt, "clip": ["load_checkpoint", 1]}, "class_type": "CLIPTextEncode"},
        "vae_encode_inpaint": {
            "inputs": {
                "pixels": ["load_image", 0], 
                "vae": ["load_checkpoint", 2],
                "mask": ["invert_mask", 0],
                "grow_mask_by": 20          
            },
            "class_type": "VAEEncodeForInpaint"
        },    
        "k_sampler": {
            "inputs": {
                "seed": seed,
                "steps": 20,               
                "cfg": 3.0,                
                "sampler_name": "dpmpp_sde",
                "scheduler": "karras",
                "denoise": 0.85,             
                "model": ["load_checkpoint", 0],
                "positive": ["apply_controlnet", 0],
                "negative": ["negative", 0],
                "latent_image": ["vae_encode_inpaint", 0]
            },
            "class_type": "KSampler"
        },
        "decode": {"inputs": {"samples": ["k_sampler", 0], "vae": ["load_checkpoint", 2]}, "class_type": "VAEDecode"},
        "save_image": {"inputs": {"images": ["decode", 0], "filename_prefix": "final_result"}, "class_type": "SaveImage"}
    }

def _upload_to_comfy(image_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        w, h = img.size
        scale = COMFY_MAX_EDGE / max(w, h)
        new_w = int((w * scale) // 64) * 64
        new_h = int((h * scale) // 64) * 64
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        png_buffer = BytesIO()
        img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        response = _HTTP.post(
            _comfy_url("/upload/image"),
            files={"image": (f"{base_name}.png", png_buffer, "image/png")},
            data={"type": "input"},
            timeout=COMFY_TIMEOUT,
        )
    response.raise_for_status()
    data = response.json()
    return data.get("name") or data.get("filename")


def _queue_comfy_prompt(graph: dict) -> str:
    response = _HTTP.post(
        _comfy_url("/prompt"),
        json={"prompt": graph},
        timeout=COMFY_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    prompt_id = payload.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI prompt_id fehlt.")
    return prompt_id


def _poll_comfy_output(prompt_id: str) -> dict:
    deadline = time.time() + COMFY_TIMEOUT
    last_error = None
    while time.time() < deadline:
        try:
            response = _HTTP.get(_comfy_url(f"/history/{prompt_id}"), timeout=COMFY_TIMEOUT)
            if response.status_code == 404:
                time.sleep(1.0)
                continue
            response.raise_for_status()
            history = response.json()
            outputs = history.get(prompt_id, {}).get("outputs") or {}
            for node in outputs.values():
                images = node.get("images") or []
                if images:
                    return images[0]
        except Exception as exc:  
            last_error = exc
            time.sleep(1.0)
    if last_error:
        raise last_error
    raise TimeoutError("Kein Bild von ComfyUI erhalten.")


def _download_comfy_image(filename: str, subfolder: str = "", image_type: str = "output") -> bytes:
    last_exc = None
    for attempt in range(3):
        try:
            response = _HTTP.get(
                _comfy_url("/view"),
                params={"filename": filename, "subfolder": subfolder, "type": image_type},
                timeout=COMFY_TIMEOUT,
            )
            response.raise_for_status()
            return response.content
        except Exception as exc: 
            last_exc = exc
            time.sleep(0.7)
    raise last_exc


def run_comfy_generation(image_path: str, prompt_text: str, negative_prompt: str, checkpoint: str) -> dict:
    uploaded_name = _upload_to_comfy(image_path)
    graph = _build_bewerbungsfoto_workflow(uploaded_name, prompt_text, negative_prompt, checkpoint)
    prompt_id = _queue_comfy_prompt(graph)
    image_info = _poll_comfy_output(prompt_id)
    image_bytes = _download_comfy_image(
        image_info.get("filename"),
        image_info.get("subfolder"),
        image_info.get("type") or "output",
    )
    return {
        "prompt_id": prompt_id,
        "filename": image_info.get("filename") or "bewerbungsfoto.png",
        "bytes": image_bytes,
        "meta": image_info,
    }


@ensure_csrf_cookie
def session_view(request):
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})
    return JsonResponse({"authenticated": False}, status=200)


def register_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    payload = _json(request)
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    if not username:
        return JsonResponse({"error": "Bitte einen Benutzernamen angeben."}, status=400)
    if not password:
        return JsonResponse({"error": "Bitte ein Passwort angeben."}, status=400)
    pw_issues = _password_errors(password)
    if pw_issues:
        return JsonResponse(
            {
                "error": f"Passwort entspricht nicht den Richtlinien: {', '.join(pw_issues)}."
            },
            status=400,
        )
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"error": "Benutzername bereits vergeben."}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    _ensure_profile(user)
    login(request, user)
    return JsonResponse({"message": "registered", "user": _user_payload(user)}, status=201)


def login_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    payload = _json(request)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "Benutzername und Passwort erforderlich."}, status=400)
    try:
        user_obj = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return JsonResponse({"error": "Benutzername nicht gefunden."}, status=400)
    user = authenticate(request, username=user_obj.username, password=password)
    if not user:
        return JsonResponse({"error": "Passwort ist nicht korrekt."}, status=400)
    login(request, user)
    return JsonResponse({"message": "logged-in", "user": _user_payload(user)})


def logout_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    logout(request)
    return JsonResponse({"message": "logged-out"})


def profile_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    profile = _ensure_profile(request.user)
    if request.method == "GET":
        return JsonResponse({"profile": profile.as_payload()})
    payload = _json(request)
    for key in DEFAULT_PROFILE.keys():
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(getattr(profile, key), list):
            setattr(profile, key, value if isinstance(value, list) else [])
        else:
            setattr(profile, key, value or "")
    profile.save()
    return JsonResponse({"profile": profile.as_payload()})


def jobs_search_view(request):
    query = request.GET.get("query", "").lower()
    results = []
    for job in SAMPLE_JOBS:
        if query and query not in job["title"].lower() and query not in job["description"].lower():
            continue
        match_score = 80 if request.user.is_authenticated else 40
        results.append({**job, "match": {"score": match_score, "summary": "Demo-Match"}})
    return JsonResponse({"jobs": results, "profile_attached": request.user.is_authenticated})


def jobs_bookmarks_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    if request.method == "GET":
        bookmarks = [
            bookmark.as_payload()
            for bookmark in request.user.bookmarks.order_by("-created_at")
        ]
        return JsonResponse({"bookmarks": bookmarks})
    if request.method != "POST":
        return JsonResponse({"error": "Only GET/POST allowed"}, status=405)
    payload = _json(request)
    bookmark_id = payload.get("id")

    title = payload.get("title", "Unbenannt")
    company = payload.get("company", "")
    location = payload.get("location", "")
    description = payload.get("description", "")
    link = payload.get("link", "")
    match = payload.get("match", {}) or {}

    try:
        if bookmark_id:
            bookmark = JobBookmark.objects.get(id=bookmark_id, user=request.user)
            bookmark.title = title
            bookmark.company = company
            bookmark.location = location
            bookmark.description = description
            bookmark.link = link
            bookmark.match_score = match.get("score", 0) or 0
            bookmark.match_summary = match.get("summary", "Manuell gespeichert")
            bookmark.created_at = timezone.now()
            bookmark.save()
        else:
            bookmark = JobBookmark.objects.create(
                user=request.user,
                title=title,
                company=company,
                location=location,
                description=description,
                link=link,
                match_score=match.get("score", 0) or 0,
                match_summary=match.get("summary", "Manuell gespeichert"),
                created_at=timezone.now(),
            )

        return JsonResponse({"bookmark": bookmark.as_payload()}, status=201)

    except JobBookmark.DoesNotExist:
        return JsonResponse({"error": "Job-Eintrag nicht gefunden"}, status=404)


def jobs_bookmarks_delete_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)

    payload = _json(request)
    bookmark_id = payload.get("id")

    if not bookmark_id:
        return JsonResponse({"error": "id required"}, status=400)

    try:
        bookmark = JobBookmark.objects.get(id=bookmark_id, user=request.user)
        bookmark.delete()
        return JsonResponse({"deleted": bookmark_id})
    except JobBookmark.DoesNotExist:
        return JsonResponse({"error": "Job-Eintrag nicht gefunden"}, status=404)

def assistant_generate_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)

    payload = _json(request)
    
    job_title = payload.get("job_title", "Mitarbeiter")
    company = payload.get("company", "diesem Unternehmen")
    description = payload.get("job_description", "")
    tone_input = payload.get("tone", "formal")
    
    locked_intro = payload.get("locked_intro")
    locked_body = payload.get("locked_body")
    locked_outro = payload.get("locked_outro")

    try:
        bewerber = request.user.bewerber
        user_name = f"{bewerber.vorname} {bewerber.nachname}"
        skills_qs = ZertifizierteSkills.objects.filter(bewerber=bewerber).select_related('skill', 'skala_wert')
        hard_skills_text = ", ".join([s.skill.name for s in skills_qs])        
        exp_list = []
        for s in bewerber.stationen.all().order_by('-beginn'):
            leistungen = s.leistungen.all()
            leistungen_str = ". ".join([f"Erfolg: {l.titel} ({l.beschreibung})" for l in leistungen])
            
            station_info = f"Station: {s.position} bei {s.institution}"
            if leistungen_str:
                station_info += f" | Details: {leistungen_str}"
            exp_list.append(station_info)
        experience_text = "\n".join(exp_list)
        soft_skills_text = "\n".join([f"- {ss.skill.name}: {ss.begruendung}" for ss in SoftSkills.objects.filter(bewerber=bewerber)])
    except AttributeError:
        hard_skills_text = "Nicht angegeben"
        experience_text = "Keine Details vorhanden"
        soft_skills_text = "Keine Details vorhanden"

    reference_letter = get_template_by_tone(tone_input)

    prompt = (
        f"""
        Du bist ein professioneller KI-Bewerbungsassistent. Erstelle ein Anschreiben für '{job_title}' bei '{company}'.
        Schreibe das gesamte Anschreiben auf Deutsch.
        
        --- Formelle Hinweise ---
        1. Beginne immer mit einer Betreffzeile: 'Betreff: Bewerbung als {job_title}'.
        2. Nutze die Anrede: 'Sehr geehrte Damen und Herren,'.
        3. Beende den Text mit der Grußformel 'Mit freundlichen Grüßen', und {user_name} in der letzten Zeile.
        
        --- DATEN DES BEWERBERS (Nutze diese als konkrete Belege) ---
        Fähigkeiten: {hard_skills_text}
        Werdegang & Projekte: {experience_text}
        Stärken: {soft_skills_text}
        
        --- JOB-ANFORDERUNGEN ---
        Job Beschreibung auf die Bezug genommen werden soll: {description}
        
        --- STRUKTUR-VORLAGE ---
        Vorlage für den Aufbau eines Anschreibens: {reference_letter}
        """
    )

    model_name = payload.get("model") or os.getenv("OLLAMA_MODEL", "llama3:latest")

    final_intro, final_body, final_outro = locked_intro or "", locked_body or "", locked_outro or ""

    try:
        if not (locked_intro and locked_body and locked_outro):
            response = ollama.chat(model=model_name, messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.6})
            clean_response = response['message']['content']
            
            if "Betreff" in clean_response:
                clean_response = clean_response[clean_response.find("Betreff")-2:] 
            
            paragraphs = [p.strip() for p in clean_response.split('\n') if p.strip()]
            
            if len(paragraphs) >= 3:
                content_start_idx = 0
                header_lines = []
                for i, p in enumerate(paragraphs):
                    if "Betreff" in p or "Sehr geehrte" in p:
                        header_lines.append(p)
                        content_start_idx = i + 1
                
                header_html = "<br>".join(header_lines)
                
                if not locked_intro:
                    main_intro = paragraphs[content_start_idx] if content_start_idx < len(paragraphs) else ""
                    final_intro = f"{header_html}<br><br>{main_intro}"
                
                if not locked_body:
                    body_parts = paragraphs[content_start_idx+1:-1]
                    final_body = "\n\n".join(body_parts) if body_parts else "Details im persönlichen Gespräch."
                
                if not locked_outro:
                    final_outro = paragraphs[-1]
            else:
                final_body = clean_response

        full_text_html = f"{final_intro}<br><br>{final_body}<br><br>{final_outro}"

    except Exception as e:
        full_text_html = f"Fehler bei der Generierung: {str(e)}"

    cover_letter_obj = CoverLetter.objects.create(
        user=request.user,
        job_title=job_title,
        company=company,
        tone=tone_input,
        job_description=description,
        cover_letter=full_text_html,
        section_intro=final_intro,
        section_body=final_body,
        section_outro=final_outro,
        match_notes=f"Modell: {model_name}"
    )
    
    return JsonResponse({
        "application": cover_letter_obj.as_payload(), 
        "generated": {
            "cover_letter": full_text_html,
            "structure": {
                "Einleitung": final_intro,
                "Hauptteil": final_body,
                "Schluss": final_outro
            }
        }
    })
    
def assistant_history_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    applications = [
        application.as_payload()
        for application in request.user.cover_letters.order_by("-created_at")
    ]
    return JsonResponse({"applications": applications})


def assistant_chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    
    payload = _json(request)
    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "message required"}, status=400)

    current_intro = payload.get("current_intro", "")
    current_body = payload.get("current_body", "")
    current_outro = payload.get("current_outro", "")
    
    is_locked_intro = payload.get("is_locked_intro", False)
    is_locked_body = payload.get("is_locked_body", False)
    is_locked_outro = payload.get("is_locked_outro", False)
    
    job_title = payload.get("job_title", "Job")
    company = payload.get("company", "Firma")

    try:
        bewerber = request.user.bewerber
        skills_qs = ZertifizierteSkills.objects.filter(bewerber=bewerber).select_related('skill')
        hard_skills = ", ".join([s.skill.name for s in skills_qs])
        
        exp_list = []
        for s in bewerber.stationen.all():
            leistungen = ", ".join([l.titel for l in s.leistungen.all()])
            exp_list.append(f"- {s.position} ({leistungen})")
        experience_context = "\n".join(exp_list)
    except:
        hard_skills = "Nicht angegeben"
        experience_context = "Nicht angegeben"

    default_model = "qwen2.5:3b"
    if os.getenv("PC_MODE") == "True":
        default_model = "mistral-nemo"
    model_name = payload.get("model") or os.getenv("OLLAMA_MODEL", default_model)

    prompt = (
        f"Du bist ein intelligenter Text-Editor für Bewerbungsschreiben.\n"
        f"Deine Aufgabe: Ändere das Anschreiben basierend auf dem User-Wunsch: '{message}'\n\n"
        
        f"--- HINTERGRUND-WISSEN (Falls der User Details ergänzen will) ---\n"
        f"Skills des Bewerbers: {hard_skills}\n"
        f"Echte Projekte: {experience_context}\n\n"
        
        f"--- AKTUELLER TEXT ---\n"
        f"### EINLEITUNG\n{current_intro}\n\n"
        f"### HAUPTTEIL\n{current_body}\n\n"
        f"### SCHLUSS\n{current_outro}\n\n"
        
        f"--- REGELN ---\n"
        f"1. {'TEIL 1 (EINLEITUNG) ist GESPERRT. Nicht ändern!' if is_locked_intro else 'Teil 1 darf geändert werden.'}\n"
        f"2. {'TEIL 2 (HAUPTTEIL) ist GESPERRT. Nicht ändern!' if is_locked_body else 'Teil 2 darf geändert werden.'}\n"
        f"3. {'TEIL 3 (SCHLUSS) ist GESPERRT. Nicht ändern!' if is_locked_outro else 'Teil 3 darf geändert werden.'}\n"
        f"4. Nutze NUR die echten Fakten aus dem Hintergrund-Wissen.\n"
        f"5. Antworte NUR mit dem neuen Text. Nutze die Trenner: ### EINLEITUNG, ### HAUPTTEIL, ### SCHLUSS."
    )

    final_intro = current_intro
    final_body = current_body
    final_outro = current_outro
    reply_text = "Änderungen wurden übernommen."

    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt},
        ], options={'temperature': 0.3}) 
        
        raw_response = response['message']['content']
        
        def extract_section(section_name, text):
            pattern = rf"### {section_name}(.*?)(?=###|$)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else None

        new_intro = extract_section("EINLEITUNG", raw_response)
        new_body = extract_section("HAUPTTEIL", raw_response)
        new_outro = extract_section("SCHLUSS", raw_response)

        if new_intro and not is_locked_intro: final_intro = new_intro
        if new_body and not is_locked_body: final_body = new_body
        if new_outro and not is_locked_outro: final_outro = new_outro
            
    except Exception as e:
        reply_text = f"Fehler bei der Bearbeitung: {str(e)}"

    full_text_html = f"{final_intro}<br><br>{final_body}<br><br>{final_outro}"

    return JsonResponse({
        "reply": reply_text,
        "cover_letter": full_text_html,
        "structure": {
            "Einleitung": final_intro,
            "Hauptteil": final_body,
            "Schluss": final_outro
        }
    })


def assistant_save_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    payload = _json(request)
    model_name = payload.get("model") or "Standard-Modell"
    record_id = payload.get("id")
    cover_letter = (payload.get("cover_letter") or "").strip()
    job_title = payload.get("job_title") or "Entwurf"
    company = payload.get("company") or ""
    description = payload.get("job_description") or ""
    tone = payload.get("tone") or ""
    focus_points = payload.get("focus_points") or []
    if not isinstance(focus_points, list):
        focus_points = []
    match_notes = payload.get("match_notes") or "Manuell gespeichert"
    section_intro = payload.get("section_intro", "")
    section_body = payload.get("section_body", "")
    section_outro = payload.get("section_outro", "")
    try:
        if record_id:
            record = CoverLetter.objects.get(id=record_id, user=request.user)
            record.job_title = job_title
            record.company = company
            record.job_description = description
            record.tone = tone
            record.focus_points = focus_points

            if cover_letter:
                record.cover_letter = cover_letter

            record.section_intro = section_intro
            record.section_body = section_body
            record.section_outro = section_outro
            record.created_at = timezone.now()
            record.match_notes = f"Modell: {model_name}"
            record.save()
        else:
            record = CoverLetter.objects.create(
                user=request.user,
                job_title=job_title,
                company=company,
                job_description=description,
                tone=tone,
                focus_points=focus_points,
                cover_letter=cover_letter,
                match_notes=match_notes,
                section_intro=section_intro,
                section_body=section_body,
                section_outro=section_outro,
                created_at=timezone.now(),
            )

        return JsonResponse({"application": record.as_payload()}, status=201)

    except CoverLetter.DoesNotExist:
        return JsonResponse({"error": "Eintrag nicht gefunden"}, status=404)

def assistant_delete_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    payload = _json(request)
    record_id = payload.get("id")
    if not record_id:
        return JsonResponse({"error": "id required"}, status=400)
    try:
        record = CoverLetter.objects.get(id=record_id, user=request.user)
    except CoverLetter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    record.delete()
    return JsonResponse({"deleted": record_id})


def ollama_models_view(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    try:
        result = ollama.list()
        raw_models = result.get("models") if isinstance(result, dict) else getattr(result, "models", [])
        if raw_models is None:
            raw_models = []
        models = []
        for entry in raw_models:
            name = getattr(entry, "model", None)
            if not name and isinstance(entry, dict):
                name = entry.get("model") or entry.get("name")
            if not name:
                continue
            size = getattr(entry, "size", None)
            modified_at = getattr(entry, "modified_at", None)
            if isinstance(entry, dict):
                size = size or entry.get("size")
                modified_at = modified_at or entry.get("modified_at")
            if hasattr(modified_at, "isoformat"):
                modified_at = modified_at.isoformat()
            models.append({"name": name, "size": size, "modified_at": modified_at})
        return JsonResponse({"models": models, "available": True})
    except Exception as exc:
        return JsonResponse(
            {"models": [], "available": False, "error": f"Kann Ollama nicht erreichen: {exc}"},
            status=200,
        )


def comfy_models_view(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    try:
        items = []

        def _extract(payload):
            if not payload:
                return []
            if isinstance(payload, dict):
                for key in ("checkpoints", "models", "items", "model_list"):
                    if payload.get(key):
                        return payload.get(key)
                return payload.values()
            return payload

        def _collect_from_payload(payload):
            candidates = _extract(payload) or []
            for entry in candidates:
                if isinstance(entry, dict):
                    name = entry.get("filename") or entry.get("name") or entry.get("model_name")
                else:
                    name = entry
                if not name:
                    continue
                name_str = str(name)
                if name_str.lower() in {
                    "checkpoints",
                    "configs",
                    "loras",
                    "vae",
                    "text_encoders",
                    "diffusion_models",
                    "clip_vision",
                    "style_models",
                    "embeddings",
                    "diffusers",
                    "vae_approx",
                    "controlnet",
                    "gligen",
                    "upscale_models",
                    "latent_upscale_models",
                    "custom_nodes",
                    "hypernetworks",
                    "photomaker",
                    "classifiers",
                    "model_patches",
                    "audio_encoders",
                    "ipadapter",
                    "prompt_expansion",
                    "ultralytics",
                    "ultralytics_bbox",
                    "ultralytics_segm",
                    "sams",
                }:
                    continue
                items.append({"name": name_str})

        endpoints = [
            ("/models/checkpoints", None),
            ("/models", {"type": "checkpoint"}),
        ]
        for path, params in endpoints:
            try:
                resp = _HTTP.get(_comfy_url(path), params=params, timeout=COMFY_TIMEOUT)
                resp.raise_for_status()
                _collect_from_payload(resp.json())
                if items:
                    break
            except Exception:
                continue

        seen = set()
        unique_items = []
        for item in items:
            if item["name"] in seen:
                continue
            unique_items.append(item)
            seen.add(item["name"])
        if not unique_items and COMFY_CHECKPOINT:
            unique_items.append({"name": COMFY_CHECKPOINT})

        return JsonResponse({"models": unique_items})
    except Exception as exc:  
        return JsonResponse({"error": f"Kann ComfyUI nicht erreichen: {exc}"}, status=500)


def photos_generate_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)

    upload = request.FILES.get("photo") or request.FILES.get("file") or request.FILES.get("image")
    if not upload:
        return JsonResponse({"error": "Kein Foto hochgeladen."}, status=400)

    checkpoint = (request.POST.get("checkpoint") or request.POST.get("model") or "").strip() or COMFY_CHECKPOINT
    prompt_text = (request.POST.get("prompt") or DEFAULT_PHOTO_PROMPT).strip() or DEFAULT_PHOTO_PROMPT
    face_lock = (
        "Gesicht, Identität, Geschlecht und Frisur exakt wie im Upload behalten, kein Gender-Wechsel. "
        "Nur Kleidung auf formellen Business-Look (Anzug/Blazer/Bluse) anpassen."
    )
    if face_lock.lower() not in prompt_text.lower():
        prompt_text = f"{prompt_text} {face_lock}"

    negative_prompt = (request.POST.get("negative_prompt") or COMFY_NEGATIVE_PROMPT).strip() or COMFY_NEGATIVE_PROMPT
    negative_prompt = (
        negative_prompt
        + ", gender swap, male to female, female to male, feminized male, masculinized female, new face, different person, changed identity, blurred face,"
        " outdoor, cityscape, street, mountains, backpack, hoodie, t-shirt, casual wear, necklace, jewelry, accessories"
    )
    style = request.POST.get("style") or "studio"
    style_hints = {
        "studio": "neutraler Hintergrund, Studio-Licht, klare Kanten",
        "soft": "weiches Licht, warme Töne, leichte Vignette",
        "outdoor": "klarer Outdoor-Hintergrund, unscharfer Hintergrund, Tageslicht",
    }
    suffix = style_hints.get(style)
    if suffix and suffix not in prompt_text:
        prompt_text = f"{prompt_text}. {suffix}"

    session = PhotoSession.objects.create(
        user=request.user,
        prompt=prompt_text,
        adjustments={"style": style, "negative_prompt": negative_prompt, "checkpoint": checkpoint},
        notes="Bewerbungsfoto via ComfyUI",
        status="pending",
        created_at=timezone.now(),
    )
    session.source_image.save(upload.name, upload, save=True)

    try:
        result = run_comfy_generation(session.source_image.path, prompt_text, negative_prompt, checkpoint)
        session.status = "done"
        session.adjustments["workflow"] = "bewerbungsfoto"
        session.adjustments["comfy_prompt_id"] = result.get("prompt_id")
        session.result_image.save(result["filename"], ContentFile(result["bytes"]), save=False)
        session.save()
        return JsonResponse({"photo_session": session.as_payload()}, status=201)
    except Exception as exc:  
        session.status = "failed"
        session.error = str(exc)
        session.save(update_fields=["status", "error"])
        return JsonResponse(
            {"error": f"ComfyUI Fehler: {exc}"},
            status=502,
        )


def photos_optimize_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    payload = _json(request)
    adjustments = {
        "lighting": f"Belichtung mit {payload.get('lighting', 'neutralem Licht')} angepasst",
        "background": f"Hintergrund '{payload.get('background', 'Studio Grau')}' gesetzt",
        "crop": f"Beschnitt auf {payload.get('crop', 'Portrait 4:5')}",
    }
    record = PhotoSession.objects.create(
        user=request.user,
        adjustments=adjustments,
        notes="Demo-Optimierung gespeichert",
        status="done",
        created_at=timezone.now(),
    )
    return JsonResponse({"photo_job": record.as_payload()})


def photos_history_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    sessions = [
        session.as_payload() for session in request.user.photo_sessions.order_by("-created_at")
    ]
    return JsonResponse({"photo_sessions": sessions})

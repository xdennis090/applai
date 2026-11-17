from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from datetime import date
from django.db.models import Value, Case, When, IntegerField, DateField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.template.loader import render_to_string
from playwright.sync_api import sync_playwright
import base64
import os
from .models import (
    Bewerber, Stationen, StationenKategorien,
    ZertifizierteSkills, Kategorien, SkillKatalog, SkalaWerte,
    Leistungseintraege, LeistungseintraegeSkills, SoftSkills, Unterkategorien
)

from .forms import BasisdatenForm, BewerbungsFotoForm, StationForm, SkillForm, LeistungseintragForm, ProjectSkillForm


def group_competencies(skill_entries):

    grouped = {}
    for entry in skill_entries:
        name = entry.skill.name

        if name not in grouped:
            grouped[name] = {
                'skill_name': name,
                'skill_id': entry.skill.id,
                'best_rating': None,
                'best_rating_val': -1,
                'projects': [],
                'soft_entries': [],
                'cert_entries': [],
                'has_entries': False
            }

        group = grouped[name]
        group['has_entries'] = True

        if hasattr(entry, 'skala_wert') and entry.skala_wert:
            current_val = getattr(entry.skala_wert, 'rangwert', entry.skala_wert.pk)

            if current_val > group['best_rating_val']:
                group['best_rating_val'] = current_val
                group['best_rating'] = entry.skala_wert

                bez = entry.skala_wert.bezeichnung
                if "⭐" in bez:
                    last_idx = bez.rfind("⭐")
                    group['rating_stars'] = bez[:last_idx + 1]
                    group['rating_text'] = bez[last_idx + 1:].strip()
                else:
                    group['rating_stars'] = ""
                    group['rating_text'] = bez

        if entry.type == 'projekt':
            group['projects'].append({
                'titel': entry.leistungseintrag.titel,
                'kontext': entry.kontext,
                'id': entry.id,
                'delete_url': f"/delete_project_skill/{entry.id}/"
            })
        elif entry.type == 'soft':
            group['soft_entries'].append({
                'begruendung': entry.begruendung,
                'id': entry.id,
                'delete_url': f"/delete_soft_skill/{entry.id}/"
            })
        elif entry.type == 'zertifikat':
            group['cert_entries'].append({
                'ausstellungsdatum': entry.ausstellungsdatum,
                'id': entry.id,
                'delete_url': f"/delete_skill/{entry.id}/"
            })

    return grouped.values()

@login_required
def dashboard_view(request):
    bewerber = getattr(request.user, "bewerber", None)

    genutzte_kategorien = StationenKategorien.objects.filter(
        stationen__bewerber=bewerber
    ).distinct()

    genutzte_kategorien = genutzte_kategorien.annotate(
        custom_order=Case(
            When(name__icontains="Beruf", then=Value(1)),
            When(name__icontains="Akademisch", then=Value(2)),
            When(name__icontains="Ehrenamt", then=Value(3)),
            When(name__icontains="Private", then=Value(4)),
            default=Value(100),
            output_field=IntegerField(),
        )
    ).order_by('custom_order', 'name')

    stationen_gruppiert = []

    for kat in genutzte_kategorien:
        stationen = Stationen.objects.filter(
            bewerber=bewerber,
            kategorie=kat
        ).annotate(
            sort_ende=Coalesce(
                'ende',
                Value(date(2100, 1, 1)),
                output_field=DateField()
            )
        ).order_by('-sort_ende', '-beginn')

        stationen_gruppiert.append({
            'kategorie': kat,
            'stationen': stationen,
            'count': stationen.count()
        })

    zert_skills = list(ZertifizierteSkills.objects.filter(
        bewerber=bewerber
    ).select_related('skill', 'skala_wert', 'skill__kategorie'))

    for zs in zert_skills:
        zs.type = 'zertifikat'

    proj_skills = list(LeistungseintraegeSkills.objects.filter(
        leistungseintrag__station__bewerber=bewerber
    ).select_related('skill', 'skala_wert', 'skill__kategorie', 'leistungseintrag'))

    for ps in proj_skills:
        ps.type = 'projekt'

    soft_skills = list(SoftSkills.objects.filter(
        bewerber=bewerber
    ).select_related('skill', 'skill__kategorie'))

    for ss in soft_skills:
        ss.type = 'soft'

    alle_skills = zert_skills + proj_skills + soft_skills
    alle_skills.sort(key=lambda x: x.skill.name)

    raw_kategorien = {}
    for eintrag in alle_skills:
        kat_name = eintrag.skill.kategorie.name
        if kat_name not in raw_kategorien:
            raw_kategorien[kat_name] = []
        raw_kategorien[kat_name].append(eintrag)

    kompetenzen_gruppiert = {}
    for kat_name, eintraege in raw_kategorien.items():
        groups = group_competencies(eintraege)

        sorted_groups = sorted(
            groups,
            key=lambda x: (x['best_rating_val'], x['skill_name']),
            reverse=True
        )

        sorted_groups = sorted(groups, key=lambda x: x['skill_name'])
        sorted_groups = sorted(sorted_groups, key=lambda x: x['best_rating_val'],
                               reverse=True)

        kompetenzen_gruppiert[kat_name] = sorted_groups

    context = {
        'form': BasisdatenForm(instance=bewerber),
        'foto_form': BewerbungsFotoForm(instance=bewerber),
        'stationen_gruppiert': stationen_gruppiert,
        'station_form': StationForm(),
        'kompetenzen_gruppiert': kompetenzen_gruppiert,
        'skill_form': SkillForm()
    }

    return render(request, 'index.html', context)


@login_required
def update_basisdaten(request):
    if request.method != 'POST':
        return redirect('home')

    bewerber = getattr(request.user, "bewerber", None)
    form_type = request.POST.get('form_type')

    if form_type == 'basisdaten':
        form = BasisdatenForm(request.POST, instance=bewerber)
        if form.is_valid():
            bewerber_obj = form.save(commit=False)
            bewerber_obj.user = request.user
            bewerber_obj.save()
            return redirect('home')

    elif form_type == 'profilbild':
        form = BewerbungsFotoForm(request.POST, request.FILES, instance=bewerber)
        if form.is_valid():
            bewerber_obj = form.save(commit=False)
            if not bewerber_obj.user_id:
                bewerber_obj.user = request.user
            bewerber_obj.save()
            return redirect('home')

    return redirect('home')


@login_required
def add_station(request):
    if request.method == 'POST':
        form = StationForm(request.POST)
        if form.is_valid():
            neue_station = form.save(commit=False)
            bewerber = Bewerber.objects.get(user=request.user)
            neue_station.bewerber = bewerber
            neue_station.save()

    return redirect('home')


@login_required
@require_POST
def add_category_ajax(request):
    try:
        data = json.loads(request.body)
        kategorie_name = data.get('name')

        if not kategorie_name:
            return JsonResponse({'success': False, 'error': 'Kein Name angegeben'})

        kategorie, created = StationenKategorien.objects.get_or_create(
            name=kategorie_name
        )

        return JsonResponse({
            'success': True,
            'id': kategorie.id,
            'name': kategorie.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def delete_station(request, pk):
    station = get_object_or_404(Stationen, pk=pk, bewerber__user=request.user)
    station.delete()
    return redirect('home')


@login_required
def get_station_data(request, pk):
    station = get_object_or_404(Stationen, pk=pk, bewerber__user=request.user)

    data = {
        'id': station.id,
        'kategorie_id': station.kategorie.id if station.kategorie else '',
        'institution': station.institution,
        'beginn': station.beginn.strftime('%Y-%m-%d'),
        'ende': station.ende.strftime('%Y-%m-%d') if station.ende else '',
        'beschreibung': station.beschreibung_station,
        'position_raw': station.position,
        'studiengang': station.studiengang,
        'abschluss_grad': station.abschluss_grad,
        'abschluss_note': station.abschluss_note,
    }
    return JsonResponse(data)


@login_required
def edit_station(request, pk):
    station = get_object_or_404(Stationen, pk=pk, bewerber__user=request.user)

    if request.method == 'POST':
        form = StationForm(request.POST, instance=station)
        if form.is_valid():
            form.save()
            return redirect('home')

    return redirect('home')


def get_skills_options(request):

    kat_id = request.GET.get('kategorie_id')
    sub_id = request.GET.get('unterkategorie_id')
    data = {}
    skala_werte = []
    try:
        kategorie = Kategorien.objects.get(id=kat_id)
        if kategorie.standard_skala:
            skala_werte = list(
                SkalaWerte.objects.filter(skala=kategorie.standard_skala)
                .order_by('rangwert')
                .values('id', 'bezeichnung')
            )
    except Kategorien.DoesNotExist:
        pass
    data['skala_werte'] = skala_werte
    unterkategorien = []
    if kat_id:
        unterkategorien = list(
            Unterkategorien.objects.filter(kategorie_id=kat_id)
            .values('id', 'name')
            .order_by('name')
        )
    data['unterkategorien'] = unterkategorien

    skills_query = SkillKatalog.objects.filter(kategorie_id=kat_id)

    if sub_id:
        skills_query = skills_query.filter(unterkategorie_id=sub_id)

    data['skills'] = list(skills_query.values('id', 'name').order_by('name'))
    return JsonResponse(data)


def add_skill(request):
    if request.method == 'POST':
        bewerber = get_object_or_404(Bewerber, user=request.user)
        form = SkillForm(request.POST)

        kategorie_id = request.POST.get('kategorie_filter')
        if kategorie_id:
            try:
                kat_id = int(kategorie_id)

                if 'skill' in form.fields:
                    form.fields['skill'].queryset = SkillKatalog.objects.filter(kategorie_id=kat_id)

                if 'unterkategorie_filter' in form.fields:
                    form.fields['unterkategorie_filter'].queryset = Unterkategorien.objects.filter(kategorie_id=kat_id)

                kat = Kategorien.objects.get(id=kat_id)
                if kat.standard_skala and 'skala_wert' in form.fields:
                    form.fields['skala_wert'].queryset = SkalaWerte.objects.filter(skala=kat.standard_skala)

            except (ValueError, TypeError, Kategorien.DoesNotExist, KeyError):
                pass

        if form.is_valid():
            skill_entry = form.save(commit=False)
            skill_entry.bewerber = bewerber
            new_name = form.cleaned_data.get('new_skill_name')

            if new_name:
                kategorie_obj = get_object_or_404(Kategorien, id=kategorie_id)
                unterkategorie_obj = form.cleaned_data.get('unterkategorie_filter')
                existing_skill = SkillKatalog.objects.filter(
                    name__iexact=new_name,
                    kategorie=kategorie_obj
                ).first()

                if existing_skill:
                    skill_entry.skill = existing_skill
                else:
                    new_catalog_entry = SkillKatalog.objects.create(
                        name=new_name,
                        kategorie=kategorie_obj,
                        unterkategorie=unterkategorie_obj,
                        beschreibung="Manuell hinzugefügt"
                    )
                    skill_entry.skill = new_catalog_entry
                    print(f"Neuer Skill erstellt: {new_name} in {kategorie_obj} / {unterkategorie_obj}")

            elif not skill_entry.skill:
                return redirect('home')

            skill_entry.save()
            return redirect('home')
        else:
            print("Form Errors bei Add Skill:", form.errors)
            return redirect('home')

    return redirect('home')


def delete_skill(request, pk):
    skill = get_object_or_404(ZertifizierteSkills, pk=pk, bewerber__user=request.user)
    skill.delete()
    return redirect('home')


def add_leistung(request, station_id):
    station = get_object_or_404(Stationen, pk=station_id, bewerber__user=request.user)

    if request.method == 'POST':
        form = LeistungseintragForm(request.POST)
        if form.is_valid():
            leistung = form.save(commit=False)
            leistung.station = station
            leistung.save()
            return redirect('home')

    return redirect('home')


def delete_leistung(request, pk):
    leistung = get_object_or_404(Leistungseintraege, pk=pk, station__bewerber__user=request.user)
    leistung.delete()
    return redirect('home')


def add_project_skill(request, leistung_id):
    leistung = get_object_or_404(Leistungseintraege, pk=leistung_id, station__bewerber__user=request.user)

    if request.method == 'POST':
        form = ProjectSkillForm(request.POST)

        kategorie_id = request.POST.get('kategorie_filter')
        if kategorie_id:
            form.fields['skill'].queryset = SkillKatalog.objects.filter(kategorie_id=kategorie_id)
            try:
                kat = Kategorien.objects.get(id=kategorie_id)
                if kat.standard_skala:
                    form.fields['skala_wert'].queryset = SkalaWerte.objects.filter(skala=kat.standard_skala)
            except:
                pass

        if form.is_valid():
            entry = form.save(commit=False)
            entry.leistungseintrag = leistung
            entry.save()
            return redirect('home')
        else:
            print(form.errors)  # Debug

    return redirect('home')


def delete_project_skill(request, pk):
    entry = get_object_or_404(LeistungseintraegeSkills, pk=pk, leistungseintrag__station__bewerber__user=request.user)
    entry.delete()
    return redirect('home')


def delete_soft_skill(request, pk):
    entry = get_object_or_404(SoftSkills, pk=pk, bewerber__user=request.user)
    entry.delete()
    return redirect('home')


def delete_category_ajax(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cat_id = data.get('id')

            kategorie = StationenKategorien.objects.get(id=cat_id)

            if kategorie.name in ['Berufliche Laufbahn', 'Akademische Laufbahn', 'Ehrenamtliche Tätigkeiten', 'Private Projekte']:
                return JsonResponse({'success': False, 'error': 'Standardkategorien können nicht gelöscht werden.'})

            kategorie.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def export_pdf_view(request):
    bewerber = getattr(request.user, "bewerber", None)
    if not bewerber:
        return HttpResponse("Kein Bewerber gefunden", status=404)

    bewerbungsfoto_b64 = None
    if bewerber.bewerbungsfoto:
        try:
            file_path = bewerber.bewerbungsfoto.path
            if os.path.exists(file_path):
                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    extension = os.path.splitext(file_path)[1].lower().replace('.', '')
                    if extension == 'jpg':
                        extension = 'jpeg'
                    bewerbungsfoto_b64 = f"data:image/{extension};base64,{encoded_string}"
        except Exception:
            pass

    cert_skills = bewerber.zertifizierteskills_set.select_related(
        'skill', 'skill__kategorie', 'skill__unterkategorie', 'skala_wert'
    ).all()

    proj_skills = LeistungseintraegeSkills.objects.filter(
        leistungseintrag__station__bewerber=bewerber
    ).select_related(
        'skill', 'skill__kategorie', 'skill__unterkategorie', 'skala_wert'
    )

    soft_skills = bewerber.softskills_set.select_related(
        'skill', 'skill__kategorie'
    ).all()

    skill_map = {}

    for ps in proj_skills:
        ps.type = 'projekt'
        skill_map[ps.skill.id] = ps

    for ss in soft_skills:
        ss.type = 'soft'
        skill_map[ss.skill.id] = ss

    for cs in cert_skills:
        cs.type = 'zertifikat'
        skill_map[cs.skill.id] = cs

    unique_skills_list = list(skill_map.values())

    sorted_skills = sorted(unique_skills_list, key=lambda x: (
        x.skill.kategorie.name,
        getattr(x.skill.unterkategorie, 'name', '') if hasattr(x.skill,
                                                               'unterkategorie') and x.skill.unterkategorie else "",
        x.skill.name
    ))

    selected_style = request.GET.get('style', 'simple')
    selected_font = request.GET.get('font', 'quicksand')
    color_primary = request.GET.get('color_primary', '#1e40af')
    color_secondary = request.GET.get('color_secondary', '#f0f2f5')

    template_map = {
        'simple': 'pdf/cv_simple.html',
        'elegant': 'pdf/cv_elegant.html',
        'geometric': 'pdf/cv_geometric.html'
    }
    template_name = template_map.get(selected_style, 'pdf/cv_simple.html')

    font_map = {
        'quicksand': {
            'url': 'https://fonts.googleapis.com/css2?family=Quicksand:wght@400;700&display=swap',
            'family': "'Quicksand', sans-serif"
        },
        'roboto': {
            'url': 'https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap',
            'family': "'Roboto', sans-serif"
        },
        'oswald': {
            'url': 'https://fonts.googleapis.com/css2?family=Oswald:wght@400;700&display=swap',
            'family': "'Oswald', sans-serif"
        },
        'opensans': {
            'url': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap',
            'family': "'Open Sans', sans-serif"
        },
        'ubuntu': {
            'url': 'https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;700&display=swap',
            'family': "'Ubuntu', sans-serif"
        },
        'saira': {
            'url': 'https://fonts.googleapis.com/css2?family=Saira:wght@400;700&display=swap',
            'family': "'Saira', sans-serif"
        },
        'josefinsans': {
            'url': 'https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@400;700&display=swap',
            'family': "'Josefin Sans', sans-serif"
        },
        'bitter': {
            'url': 'https://fonts.googleapis.com/css2?family=Bitter:wght@400;700&display=swap',
            'family': "'Bitter', serif"
        }
    }

    font_config = font_map.get(selected_font, font_map['quicksand'])

    context = {
        'bewerber': bewerber,
        'all_skills': sorted_skills,
        'font_url': font_config['url'],
        'font_family': font_config['family'],
        'color_primary': color_primary,
        'color_secondary': color_secondary,
        'bewerbungsfoto_b64': bewerbungsfoto_b64,
    }

    html_string = render_to_string(template_name, context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.set_content(html_string, wait_until='networkidle')

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'}
        )

        browser.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Lebenslauf_{bewerber.nachname}_{selected_style}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response
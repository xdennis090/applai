from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models import Bewerber

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile_data")
    bewerber = models.ForeignKey(
        Bewerber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        help_text="Optionaler Verweis auf einen Bewerberdatensatz",
    )
    contact_email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    education = models.TextField(blank=True, default="")
    experience = models.TextField(blank=True, default="")
    resume_text = models.TextField(blank=True, default="")
    skills = models.JSONField(default=list, blank=True)
    soft_skills = models.JSONField(default=list, blank=True)
    hobbies = models.JSONField(default=list, blank=True)

    def as_payload(self):
        return {
            "contact_email": self.contact_email,
            "phone": self.phone,
            "location": self.location,
            "education": self.education,
            "experience": self.experience,
            "skills": self.skills or [],
            "soft_skills": self.soft_skills or [],
            "hobbies": self.hobbies or [],
            "resume_text": self.resume_text,
            "bewerber_id": self.bewerber_id,
            "bewerber_name": str(self.bewerber) if self.bewerber else None,
            "applications": [
                letter.as_payload() for letter in self.user.cover_letters.order_by("-created_at")
            ],
            "photo_sessions": [
                session.as_payload() for session in self.user.photo_sessions.order_by("-created_at")
            ],
        }

    def __str__(self):
        return f"Profile for {self.user.username}"


class CoverLetter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cover_letters")
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, default="")
    job_description = models.TextField(blank=True, null=True)
    tone = models.CharField(max_length=64, blank=True, default="")
    focus_points = models.JSONField(default=list, blank=True)
    section_intro = models.TextField(blank=True, default="")
    section_body = models.TextField(blank=True, default="")
    section_outro = models.TextField(blank=True, default="")
    cover_letter = models.TextField()
    match_notes = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    def as_payload(self):
        return {
            "id": str(self.id),
            "job_title": self.job_title,
            "company": self.company,
            "job_description": self.job_description,
            "focus_points": self.focus_points or [],
            "tone": self.tone,
            "cover_letter": self.cover_letter,
            "structure": {
                "Einleitung": self.section_intro,
                "Hauptteil": self.section_body,
                "Schluss": self.section_outro
            },            
            "match_notes": self.match_notes,
            "created_at": self.created_at.isoformat(),
        }

    def __str__(self):
        return f"{self.job_title} @ {self.company}".strip()


class JobBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    link = models.URLField(blank=True, default="")
    match_score = models.PositiveIntegerField(default=0)
    match_summary = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    def as_payload(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "link": self.link,
            "match_score": self.match_score,
            "match": {"score": self.match_score, "summary": self.match_summary},
            "created_at": self.created_at.isoformat(),
        }

    def __str__(self):
        return self.title


class PhotoSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="photo_sessions")
    adjustments = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    prompt = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=32, default="pending")
    error = models.TextField(blank=True, default="")
    source_image = models.ImageField(upload_to="photo_sessions/source/", blank=True, null=True)
    result_image = models.ImageField(upload_to="photo_sessions/result/", blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def as_payload(self):
        return {
            "id": str(self.id),
            "adjustments": self.adjustments or {},
            "notes": self.notes,
            "prompt": self.prompt,
            "status": self.status,
            "error": self.error,
            "source_image": self.source_image.url if self.source_image else None,
            "result_image": self.result_image.url if self.result_image else None,
            "created_at": self.created_at.isoformat(),
        }

    def __str__(self):
        return f"PhotoSession {self.created_at.isoformat()}"

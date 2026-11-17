from django.contrib import admin

from .models import CoverLetter, JobBookmark, PhotoSession, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bewerber", "contact_email", "location")
    search_fields = ("user__username", "contact_email", "bewerber__nachname", "bewerber__email")
    autocomplete_fields = ("bewerber",)


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "company", "created_at")
    list_filter = ("company", "created_at")


@admin.register(JobBookmark)
class JobBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "company", "match_score", "created_at")
    search_fields = ("title", "company")


@admin.register(PhotoSession)
class PhotoSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")

from django.contrib import admin
from .models import (
    Bewertungsskala, SkalaWerte, Kategorien, Unterkategorien, SkillKatalog,
    Firma, Ausschreibungen, AusschreibungReq,
    Bewerber, StationenKategorien, Stationen, Leistungseintraege,
    ZertifizierteSkills, SoftSkills, LeistungseintraegeSkills
)

@admin.register(SkalaWerte)
class SkalaWerteAdmin(admin.ModelAdmin):
    list_display = ('bezeichnung', 'skala', 'rangwert')
    list_filter = ('skala',)

@admin.register(SkillKatalog)
class SkillKatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'kategorie', 'unterkategorie')
    list_filter = ('kategorie',)
    search_fields = ('name',)

@admin.register(Unterkategorien)
class UnterkategorienAdmin(admin.ModelAdmin):
    list_display = ('name', 'kategorie')
    list_filter = ('kategorie',)

admin.site.register(Bewertungsskala)
admin.site.register(Kategorien)


class StationenInline(admin.StackedInline):
    model = Stationen
    extra = 0

class ZertifizierteSkillsInline(admin.TabularInline):
    model = ZertifizierteSkills
    extra = 0

class SoftSkillsInline(admin.TabularInline):
    model = SoftSkills
    extra = 0

@admin.register(Bewerber)
class BewerberAdmin(admin.ModelAdmin):
    list_display = ('vorname', 'nachname', 'email', 'user_display')
    search_fields = ('nachname', 'email')
    # Hier binden wir die Listen ein:
    inlines = [StationenInline, ZertifizierteSkillsInline, SoftSkillsInline]

    def user_display(self, obj):
        return obj.user.username if obj.user else "-"
    user_display.short_description = "User"


class AusschreibungReqInline(admin.TabularInline):
    model = AusschreibungReq
    extra = 0

@admin.register(Ausschreibungen)
class AusschreibungenAdmin(admin.ModelAdmin):
    list_display = ('titel', 'firma')
    inlines = [AusschreibungReqInline]

admin.site.register(Firma)

admin.site.register(StationenKategorien)
admin.site.register(Stationen)
admin.site.register(Leistungseintraege)
admin.site.register(ZertifizierteSkills)
admin.site.register(SoftSkills)
admin.site.register(LeistungseintraegeSkills)

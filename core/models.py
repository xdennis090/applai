from django.db import models
from django.contrib.auth.models import User


class Bewertungsskala(models.Model):
    """z.B. Sprachniveau (A1-C2) oder Expertise (1-5)"""
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Bewertungsskala"
        verbose_name_plural = "Bewertungsskalen"

    def __str__(self):
        return self.name


class SkalaWerte(models.Model):
    """Die einzelnen Stufen, z.B. 'C1' oder 'Experte'"""
    skala = models.ForeignKey(Bewertungsskala, on_delete=models.CASCADE)
    bezeichnung = models.CharField(max_length=100)
    rangwert = models.IntegerField(help_text="Wichtig für Vergleiche: 10, 20, 30...")

    class Meta:
        verbose_name = "Skalenwert"
        verbose_name_plural = "Skalenwerte"

    def __str__(self):
        return f"{self.bezeichnung} ({self.skala.name})"


class Kategorien(models.Model):
    """z.B. IT-Kenntnisse, Sprachen"""
    name = models.CharField(max_length=100)
    # Welche Skala gilt hier standardmäßig?
    standard_skala = models.ForeignKey(Bewertungsskala, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"

    def __str__(self):
        return self.name


class Unterkategorien(models.Model):
    """z.B. Programmiersprachen, Datenbanken"""
    kategorie = models.ForeignKey(Kategorien, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Unterkategorie"
        verbose_name_plural = "Unterkategorien"

    def __str__(self):
        return self.name


class SkillKatalog(models.Model):
    """Der eigentliche Skill, z.B. Python, SQL, Englisch"""
    kategorie = models.ForeignKey(Kategorien, on_delete=models.CASCADE)
    unterkategorie = models.ForeignKey(Unterkategorien, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    beschreibung = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Skill"
        verbose_name_plural = "Skill-Katalog"

    def __str__(self):
        return self.name


class Bewerber(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='bewerber',
        null=True,
        blank=True,
        help_text="Optionaler User, falls Bewerber mit einem Account verknüpft ist.",
    )

    vorname = models.CharField(max_length=100)
    nachname = models.CharField(max_length=100)
    email = models.EmailField(unique=True)  # unique=True weil im Diagramm "UK" (Unique Key) steht
    telefonnummer = models.CharField(max_length=50, blank=True)
    strasse = models.CharField(max_length=200, blank=True)
    hausnummer = models.CharField(max_length=20, blank=True)
    plz = models.CharField(max_length=10, blank=True)
    wohnort = models.CharField(max_length=100, blank=True)
    geburtsdatum = models.DateField(null=True, blank=True)
    familienstand = models.CharField(max_length=50, blank=True)
    bewerbungsfoto = models.ImageField(upload_to='bewerber_fotos/', blank=True, null=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bewerber"
        verbose_name_plural = "Bewerber"

    def __str__(self):
        return f"{self.vorname} {self.nachname}"


class StationenKategorien(models.Model):
    """z.B. Akademisch, Beruflich, Ehrenamt"""
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Stationen-Kategorie"
        verbose_name_plural = "Stationen-Kategorien"

    def __str__(self):
        return self.name


class Stationen(models.Model):
    """Ein Eintrag im Lebenslauf"""
    bewerber = models.ForeignKey(Bewerber, on_delete=models.CASCADE, related_name='stationen')
    kategorie = models.ForeignKey(StationenKategorien, on_delete=models.SET_NULL, null=True)
    institution = models.CharField(max_length=200, help_text="Firma/Uni")
    beginn = models.DateField()
    ende = models.DateField(null=True, blank=True)
    position = models.CharField(max_length=200)
    studiengang = models.CharField(max_length=200, blank=True)
    abschluss_grad = models.CharField(max_length=100, blank=True)  # B.Sc., Master
    abschluss_note = models.CharField(max_length=50, blank=True)
    beschreibung_station = models.TextField(blank=True)

    class Meta:
        verbose_name = "Lebenslauf-Station"
        verbose_name_plural = "Lebenslauf-Stationen"

    def __str__(self):
        return f"{self.position} bei {self.institution}"


class Leistungseintraege(models.Model):
    """Projekte oder Aufgaben innerhalb einer Station"""
    station = models.ForeignKey(Stationen, on_delete=models.CASCADE, related_name='leistungen')
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Leistungseintrag"
        verbose_name_plural = "Leistungseinträge"

    def __str__(self):
        return self.titel


class ZertifizierteSkills(models.Model):
    """Skills, die der Bewerber hat (mit Level)"""
    bewerber = models.ForeignKey(Bewerber, on_delete=models.CASCADE)
    skill = models.ForeignKey(SkillKatalog, on_delete=models.CASCADE)
    skala_wert = models.ForeignKey(SkalaWerte, on_delete=models.SET_NULL, null=True)
    ausstellungsdatum = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Zertifizierter Skill"
        verbose_name_plural = "Zertifizierte Skills"


class SoftSkills(models.Model):
    bewerber = models.ForeignKey(Bewerber, on_delete=models.CASCADE)
    skill = models.ForeignKey(SkillKatalog, on_delete=models.CASCADE)  # Oder Textfeld, je nach Logik
    begruendung = models.TextField(blank=True)

    class Meta:
        verbose_name = "Soft Skill"
        verbose_name_plural = "Soft Skills"


class LeistungseintraegeSkills(models.Model):
    """Welcher Skill wurde in welchem Projekt genutzt?"""
    leistungseintrag = models.ForeignKey(Leistungseintraege, on_delete=models.CASCADE)
    skill = models.ForeignKey(SkillKatalog, on_delete=models.CASCADE)
    skala_wert = models.ForeignKey(SkalaWerte, on_delete=models.SET_NULL, null=True, blank=True)
    kontext = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Projekt-Skill"
        verbose_name_plural = "Projekt-Skills"

class Firma(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Firma"
        verbose_name_plural = "Firmen"

    def __str__(self):
        return self.name


class Ausschreibungen(models.Model):
    firma = models.ForeignKey(Firma, on_delete=models.CASCADE)
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(default="")

    class Meta:
        verbose_name = "Stellenanzeige"
        verbose_name_plural = "Stellenanzeigen"

    def __str__(self):
        return self.titel


class AusschreibungReq(models.Model):
    """Anforderungen für eine Stelle"""
    ausschreibung = models.ForeignKey(Ausschreibungen, on_delete=models.CASCADE)
    skill = models.ForeignKey(SkillKatalog, on_delete=models.CASCADE)
    min_skala_wert = models.ForeignKey(SkalaWerte, on_delete=models.SET_NULL, null=True, help_text="Mindestanforderung")
    prioritaet = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Job-Anforderung"
        verbose_name_plural = "Job-Anforderungen"

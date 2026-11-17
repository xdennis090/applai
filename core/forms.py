from django import forms
from .models import Bewerber, Stationen, ZertifizierteSkills, SkillKatalog, SkalaWerte, Kategorien, Leistungseintraege, \
    LeistungseintraegeSkills, SoftSkills, Unterkategorien


class BasisdatenForm(forms.ModelForm):
    class Meta:
        model = Bewerber
        fields = [
            'vorname', 'nachname', 'familienstand', 'geburtsdatum',
            'email', 'telefonnummer', 'strasse', 'hausnummer',
            'wohnort', 'plz'
        ]
        widgets = {
            'geburtsdatum': forms.DateInput(attrs={'type': 'date'}),
        }

class BewerbungsFotoForm(forms.ModelForm):
    class Meta:
        model = Bewerber
        fields = ['bewerbungsfoto']

class StationForm(forms.ModelForm):
    ehrenamt_funktion = forms.CharField(required=False, label="Funktion / Rolle")
    privat_projekt_typ = forms.CharField(required=False, label="Projekt Art")
    position = forms.CharField(required=False, label="Position / Titel")

    class Meta:
        model = Stationen
        fields = [
            'kategorie', 'institution', 'beginn', 'ende',
            'position', 'studiengang', 'abschluss_grad', 'abschluss_note',
            'beschreibung_station'
        ]
        widgets = {
            'beginn': forms.DateInput(attrs={'type': 'date'}),
            'ende': forms.DateInput(attrs={'type': 'date'}),
            'beschreibung_station': forms.Textarea(attrs={'rows': 4}),
            'kategorie': forms.Select(attrs={'class': 'model-select', 'id': 'id_kategorie'}),
        }

    def save(self, commit=True):
        station = super().save(commit=False)
        data = self.cleaned_data

        if station.kategorie:
            kat_name = station.kategorie.name.lower()

            if "akademisch" in kat_name or "studium" in kat_name:
                station.position = data.get('studiengang') or data.get('abschluss_grad') or "Studium"

            elif "beruf" in kat_name or "arbeit" in kat_name:
                if not station.position:
                    station.position = "Angestellt"

            elif "ehrenamt" in kat_name:
                funktion = data.get('ehrenamt_funktion')
                current_pos = station.position

                if current_pos and funktion:
                    station.position = f"{current_pos} ({funktion})"
                elif funktion and not current_pos:
                    station.position = funktion

            elif ("private" in kat_name or "projekt" in kat_name) and data.get('privat_projekt_typ'):
                prefix = f"Projekttyp: {data.get('privat_projekt_typ')}\n"
                station.beschreibung_station = prefix + (station.beschreibung_station or "")

        if not station.position:
            station.position = "Keine Angabe"

        if commit:
            station.save()
        return station


class SkillForm(forms.ModelForm):
    new_skill_name = forms.CharField(
        required=False,
        label="Neuer Skill Name",
        widget=forms.TextInput(attrs={'placeholder': 'z.B. Django Rest Framework', 'class': 'text-input'})
    )
    kategorie_filter = forms.ModelChoiceField(
        queryset=Kategorien.objects.all(),
        label="Kategorie",
        required=False,
        widget=forms.Select(attrs={'class': 'model-select', 'id': 'skill-category-select'})
    )
    unterkategorie_filter = forms.ModelChoiceField(
        queryset=Unterkategorien.objects.none(),
        label="Unterkategorie (optional)",
        required=False,
        widget=forms.Select(attrs={'class': 'model-select', 'id': 'skill-subcategory-select'})
    )
    class Meta:
        model = ZertifizierteSkills
        fields = ['skill', 'skala_wert', 'ausstellungsdatum']
        widgets = {
            'skill': forms.Select(attrs={'class': 'model-select', 'id': 'skill-select'}),
            'skala_wert': forms.Select(attrs={'class': 'model-select', 'id': 'scale-select'}),
            'ausstellungsdatum': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skill'].required = False
        self.fields['skill'].queryset = SkillKatalog.objects.none()
        self.fields['skala_wert'].queryset = SkalaWerte.objects.none()
        self.fields['skala_wert'].required = False

class LeistungseintragForm(forms.ModelForm):
    class Meta:
        model = Leistungseintraege
        fields = ['titel', 'beschreibung']
        widgets = {
            'titel': forms.TextInput(attrs={'placeholder': 'Projektname / Aufgabe (z.B. Migration SQL-Datenbank)'}),
            'beschreibung': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Kurze Beschreibung der Tätigkeit...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beschreibung'].required = False


class ProjectSkillForm(forms.ModelForm):
    kategorie_filter = forms.ModelChoiceField(
        queryset=Kategorien.objects.all(),
        label="Kategorie",
        required=False,
        widget=forms.Select(attrs={'class': 'model-select', 'id': 'project-skill-cat-select'})
    )

    class Meta:
        model = LeistungseintraegeSkills
        fields = ['skill', 'skala_wert', 'kontext']
        widgets = {
            'skill': forms.Select(attrs={'class': 'model-select', 'id': 'project-skill-select'}),
            'skala_wert': forms.Select(attrs={'class': 'model-select', 'id': 'project-scale-select'}),
            'kontext': forms.TextInput(attrs={'placeholder': 'Was genau hast du damit gemacht?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kontext'].required = False
        self.fields['skill'].required = False
        self.fields['skill'].queryset = SkillKatalog.objects.none()
        self.fields['skala_wert'].queryset = SkalaWerte.objects.none()

        if 'kategorie_filter' in self.data:
            try:
                kat_id = int(self.data.get('kategorie_filter'))
                self.fields['skill'].queryset = SkillKatalog.objects.filter(kategorie_id=kat_id)

                kategorie = Kategorien.objects.get(id=kat_id)
                if kategorie.standard_skala:
                    self.fields['skala_wert'].queryset = SkalaWerte.objects.filter(skala=kategorie.standard_skala)
            except (ValueError, TypeError, Kategorien.DoesNotExist):
                pass


class SoftSkillForm(forms.ModelForm):
    kategorie_filter = forms.ModelChoiceField(
        queryset=Kategorien.objects.all(),
        label="Kategorie",
        required=False,
        widget=forms.Select(attrs={'class': 'model-select', 'id': 'soft-skill-cat-select'})
    )

    class Meta:
        model = SoftSkills
        fields = ['skill', 'begruendung']
        widgets = {
            'skill': forms.Select(attrs={'class': 'model-select', 'id': 'soft-skill-select'}),
            'begruendung': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Beispiel: "Ich habe in Projekt X bewiesen, dass ich teamfähig bin, weil..."'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skill'].queryset = SkillKatalog.objects.none()

        self.fields['begruendung'].required = False

        if 'kategorie_filter' in self.data:
            try:
                kat_id = int(self.data.get('kategorie_filter'))
                self.fields['skill'].queryset = SkillKatalog.objects.filter(kategorie_id=kat_id)
            except (ValueError, TypeError):
                pass
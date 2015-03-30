__author__ = 'kalmar'

from django import forms
from libhunter.models import LibraryType


class UploadForm(forms.Form):
    file = forms.FileField(label="", widget=forms.FileInput(attrs={'class': 'form-control'}), required=False)
    url = forms.URLField(label="", widget=forms.URLField(attrs={'class': 'form-control'}), required=False)
    library_type = forms.ChoiceField(label="", widget=forms.Select(attrs={'class': 'form-control'}), choices=[(lib.id, lib.name) for lib in LibraryType.objects.all()], required=True)


class SearchForm(forms.Form):
    function = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Function name ('return' for main's ret)"}), required=True)
    address = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Leaked address (hex)"}), required=True)
    library_type = forms.ChoiceField(label="", widget=forms.Select(attrs={'class': 'form-control'}), choices=[(lib.name, lib.name) for lib in LibraryType.objects.all()], required=True)
    bits = forms.ChoiceField(label="", widget=forms.Select(attrs={'style': "margin: 10px 0;", 'class': 'form-control'}), choices=[('32', '32 bit'), ('64', '64 bit')])
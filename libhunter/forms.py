__author__ = 'kalmar'

from django import forms


class UploadForm(forms.Form):
    file = forms.FileField(label='Select file', help_text='Select libc', widget=forms.FileInput(attrs={'class': 'form-control'}))

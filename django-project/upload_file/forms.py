from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class UploadForm(forms.Form):  
    file = forms.FileField() # for creating file input  

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith(('.pdf', '.docx', '.txt', '.doc')):
                raise forms.ValidationError('File must be a PDF, DOCX, DOC, or TXT.')
        return file
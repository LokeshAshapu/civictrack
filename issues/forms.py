from django import forms
from .models import CivicIssue

class CivicIssueForm(forms.ModelForm):
    class Meta:
        model = CivicIssue
        fields = '__all__'

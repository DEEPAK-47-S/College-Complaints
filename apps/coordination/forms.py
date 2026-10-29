from django import forms
from .models import CoordinationRecord, CoordinationNote
from apps.bureaus.models import Bureau
from apps.complaints.models import Complaint
from apps.accounts.models import User

class CoordinationCreateForm(forms.ModelForm):
    complaints = forms.ModelMultipleChoiceField(
        queryset=Complaint.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'coord_complaints'}),
        help_text="Select related complaints to link"
    )

    class Meta:
        model = CoordinationRecord
        fields = [
            'title',
            'coordinating_bureau',
            'participating_bureaus',
            'action_plan',
            'deadline'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Joint Scrutiny Title', 'id': 'coord_title'}),
            'coordinating_bureau': forms.Select(attrs={'class': 'form-select', 'id': 'coord_lead_bureau'}),
            'participating_bureaus': forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'coord_participating_bureaus'}),
            'action_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Joint inspection plan, evidence sharing schedule...', 'id': 'coord_plan'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'coord_deadline'}),
        }

class CoordinationNoteForm(forms.ModelForm):
    class Meta:
        model = CoordinationNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter joint observation or progress update...', 'id': 'coord_note_input'}),
        }

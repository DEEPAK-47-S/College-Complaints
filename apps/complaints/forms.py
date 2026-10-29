from django import forms
from .models import Complaint, ComplaintCategory, ComplaintDocument, ComplaintTransfer, ComplaintEscalation
from apps.institutions.models import Institution
from apps.bureaus.models import Bureau
from apps.accounts.models import User

class ComplaintCreateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'institution',
            'title',
            'category',
            'currently_assigned_bureau',
            'priority',
            'source_channel',
            'external_reference_no',
            'description',
        ]
        widgets = {
            'institution': forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'complaint_institution'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Grievance Subject / Title', 'id': 'complaint_title'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'complaint_category'}),
            'currently_assigned_bureau': forms.Select(attrs={'class': 'form-select', 'id': 'complaint_bureau'}),
            'priority': forms.Select(attrs={'class': 'form-select', 'id': 'complaint_priority'}),
            'source_channel': forms.Select(attrs={'class': 'form-select', 'id': 'complaint_source'}),
            'external_reference_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'External Reference / Diary No', 'id': 'complaint_ext_ref'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Detailed complaint narrative...', 'id': 'complaint_desc'}),
        }

class OfficerAssignmentForm(forms.Form):
    officer = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'assign_officer_select'})
    )
    remarks = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Assignment instructions'}),
        required=False
    )

    def __init__(self, *args, bureau=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bureau:
            # Filter officers belonging to the handling bureau
            self.fields['officer'].queryset = User.objects.filter(
                is_active=True,
                assigned_bureau=bureau,
                role=User.Role.CASE_OFFICER
            )

class StatusTransitionForm(forms.Form):
    new_status = forms.ChoiceField(
        choices=Complaint.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'transition_new_status'})
    )
    next_action_required = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Schedule hearing, await institution reply, prepare draft order', 'id': 'transition_next_action'}),
        required=False,
        help_text="Expected next operational or regulatory step"
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mandatory action remarks and regulatory findings...'}),
        required=True
    )

class TransferRequestForm(forms.ModelForm):
    class Meta:
        model = ComplaintTransfer
        fields = ['destination_bureau', 'reason']
        widgets = {
            'destination_bureau': forms.Select(attrs={'class': 'form-select', 'id': 'transfer_destination_bureau'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Justification for transferring to another Bureau'}),
        }

class EscalationRequestForm(forms.ModelForm):
    class Meta:
        model = ComplaintEscalation
        fields = ['escalation_level', 'reason']
        widgets = {
            'escalation_level': forms.Select(attrs={'class': 'form-select', 'id': 'escalate_level'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for escalating to Competent Authority'}),
        }

class DocumentUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'id': 'upload_file_input', 'accept': '.pdf,.png,.jpg,.jpeg'}),
        help_text="Allowed formats: PDF, PNG, JPG (Max 10MB)"
    )
    classification = forms.ChoiceField(
        choices=ComplaintDocument.Classification.choices,
        initial=ComplaintDocument.Classification.INTERNAL_ONLY,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'upload_classification'})
    )

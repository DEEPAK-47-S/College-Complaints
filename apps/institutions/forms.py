from django import forms
from .models import Institution

class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            'aicte_permanent_id',
            'name',
            'institution_type',
            'region',
            'state',
            'district',
            'pincode',
            'address',
            'contact_email',
            'contact_phone',
            'operational_status',
        ]
        widgets = {
            'aicte_permanent_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-10293847', 'id': 'inst_perm_id'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Institution Name', 'id': 'inst_name'}),
            'institution_type': forms.Select(attrs={'class': 'form-select', 'id': 'inst_type'}),
            'region': forms.Select(attrs={'class': 'form-select', 'id': 'inst_region'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State', 'id': 'inst_state'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District', 'id': 'inst_district'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN', 'id': 'inst_pincode'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Campus Address', 'id': 'inst_address'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@institution.edu', 'id': 'inst_email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91-XXXXXXXXXX', 'id': 'inst_phone'}),
            'operational_status': forms.Select(attrs={'class': 'form-select', 'id': 'inst_status'}),
        }

    def clean_aicte_permanent_id(self):
        perm_id = self.cleaned_data.get('aicte_permanent_id', '').strip().upper()
        # Ensure uniqueness case-insensitively
        qs = Institution.objects.filter(aicte_permanent_id__iexact=perm_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"An institution with AICTE Permanent ID '{perm_id}' is already registered.")
        return perm_id

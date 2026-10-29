from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm as BasePasswordChangeForm
from .models import User

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your username or email',
            'autofocus': True,
            'id': 'login_username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'id': 'login_password'
        })
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'email']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'profile_display_name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'profile_email'}),
        }

class PasswordChangeForm(BasePasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep existing password"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'display_name', 'role', 'assigned_bureau', 'authorized_region', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'assigned_bureau': forms.Select(attrs={'class': 'form-select'}),
            'authorized_region': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

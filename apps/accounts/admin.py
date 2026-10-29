from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .forms import UserAdminForm

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    list_display = ('username', 'email', 'display_name', 'role', 'assigned_bureau', 'authorized_region', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'assigned_bureau', 'authorized_region')
    search_fields = ('username', 'email', 'display_name')
    ordering = ('username',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('display_name', 'email')}),
        ('Organizational Role & Scope', {'fields': ('role', 'assigned_bureau', 'authorized_region')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

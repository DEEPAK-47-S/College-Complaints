from django.contrib import admin
from .models import Institution

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'aicte_permanent_id', 'institution_type', 'region', 'state', 'operational_status', 'created_at')
    list_filter = ('institution_type', 'region', 'operational_status', 'state')
    search_fields = ('name', 'aicte_permanent_id', 'district', 'state')
    readonly_fields = ('normalized_name', 'created_at', 'updated_at')

from django.contrib import admin
from .models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor_username', 'event_type', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('event_type', 'entity_type', 'timestamp')
    search_fields = ('actor_username', 'entity_id', 'request_correlation_id')
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin
from .models import SLAPolicy, Notification

@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'applicable_bureau', 'duration_days', 'is_working_days', 'is_active')
    list_filter = ('is_working_days', 'is_active', 'applicable_bureau')
    search_fields = ('name',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('created_at',)

from django.contrib import admin
from .models import CoordinationRecord, CoordinationNote

@admin.register(CoordinationRecord)
class CoordinationRecordAdmin(admin.ModelAdmin):
    list_display = ('coordination_no', 'title', 'coordinating_bureau', 'coordination_status', 'deadline', 'created_at')
    list_filter = ('coordination_status', 'coordinating_bureau', 'deadline')
    search_fields = ('coordination_no', 'title')

@admin.register(CoordinationNote)
class CoordinationNoteAdmin(admin.ModelAdmin):
    list_display = ('coordination', 'author', 'author_bureau', 'created_at')
    readonly_fields = ('created_at',)

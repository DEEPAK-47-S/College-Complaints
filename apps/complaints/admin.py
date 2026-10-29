from django.contrib import admin
from .models import (
    ComplaintCategory, Complaint, ComplaintDocument,
    ComplaintAction, ComplaintTransfer, ComplaintEscalation, CaseRelationship
)

@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_sla_days', 'is_active')
    search_fields = ('name', 'code')

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_no', 'institution', 'currently_assigned_bureau', 'current_status', 'priority', 'date_received', 'expected_disposal_date')
    list_filter = ('current_status', 'priority', 'currently_assigned_bureau', 'date_received')
    search_fields = ('complaint_no', 'title', 'institution__name', 'institution__aicte_permanent_id')
    readonly_fields = ('complaint_no', 'created_at', 'updated_at', 'disposed_at')

@admin.register(ComplaintDocument)
class ComplaintDocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'complaint', 'file_type', 'file_size', 'uploader', 'upload_timestamp')
    readonly_fields = ('checksum', 'upload_timestamp')

@admin.register(ComplaintAction)
class ComplaintActionAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'complaint', 'previous_status', 'new_status', 'responsible_officer', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(ComplaintTransfer)
class ComplaintTransferAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'source_bureau', 'destination_bureau', 'requested_by', 'approval_status', 'requested_at')

@admin.register(ComplaintEscalation)
class ComplaintEscalationAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'escalation_level', 'resolution_status', 'escalation_timestamp')

@admin.register(CaseRelationship)
class CaseRelationshipAdmin(admin.ModelAdmin):
    list_display = ('source_complaint', 'target_complaint', 'relationship_type', 'created_at')

from django.contrib import admin
from .models import OverlapCandidate

@admin.register(OverlapCandidate)
class OverlapCandidateAdmin(admin.ModelAdmin):
    list_display = ('first_complaint', 'second_complaint', 'combined_score', 'review_status', 'detection_timestamp')
    list_filter = ('review_status', 'institution_match_type', 'detection_timestamp')
    search_fields = ('first_complaint__complaint_no', 'second_complaint__complaint_no')
    readonly_fields = ('detection_timestamp',)

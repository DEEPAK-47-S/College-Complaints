from django.db.models import Count, Q
from .models import Institution

class Institution360Service:
    @staticmethod
    def get_dossier(institution_id, user=None):
        institution = Institution.objects.get(id=institution_id)
        
        # Scoped complaints
        complaints_qs = institution.complaints.select_related(
            'category', 'currently_assigned_bureau', 'currently_assigned_officer'
        ).order_by('-date_received')

        total_complaints = complaints_qs.count()
        active_complaints = complaints_qs.filter(current_status__in=['PENDING', 'UNDER_PROCESS', 'ESCALATED'])
        disposed_complaints = complaints_qs.filter(current_status='DISPOSED')
        transferred_complaints = complaints_qs.filter(current_status='TRANSFERRED')

        # Bureau involvement aggregation
        bureau_stats = complaints_qs.values(
            'currently_assigned_bureau__code',
            'currently_assigned_bureau__name'
        ).annotate(count=Count('id')).order_by('-count')

        # Categories distribution
        category_stats = complaints_qs.values(
            'category__name'
        ).annotate(count=Count('id')).order_by('-count')

        # Detect multiple bureaus actively investigating simultaneously (Institution-level overlap indicator!)
        active_bureaus = set(active_complaints.values_list('currently_assigned_bureau__code', flat=True))
        has_multi_bureau_active = len(active_bureaus) > 1

        # Check for confirmed / pending Overlap Candidates involving any complaint of this institution
        from apps.intelligence.models import OverlapCandidate
        overlap_candidates = OverlapCandidate.objects.filter(
            Q(first_complaint__institution=institution) | Q(second_complaint__institution=institution)
        ).select_related(
            'first_complaint__currently_assigned_bureau',
            'second_complaint__currently_assigned_bureau',
            'first_complaint__category',
            'second_complaint__category'
        ).distinct()

        active_overlaps = overlap_candidates.filter(review_status__in=['PENDING', 'CONFIRMED'])
        has_issue_level_overlap = active_overlaps.filter(semantic_similarity__gte=0.6).exists()

        # Check for Active Coordination Records
        from apps.coordination.models import CoordinationRecord
        coordination_records = CoordinationRecord.objects.filter(
            related_complaints__institution=institution
        ).distinct().select_related('coordinating_bureau')

        return {
            'institution': institution,
            'total_complaints': total_complaints,
            'active_count': active_complaints.count(),
            'disposed_count': disposed_complaints.count(),
            'transferred_count': transferred_complaints.count(),
            'bureau_stats': list(bureau_stats),
            'category_stats': list(category_stats),
            'active_bureaus': list(active_bureaus),
            'has_multi_bureau_active': has_multi_bureau_active,
            'has_issue_level_overlap': has_issue_level_overlap,
            'overlap_candidates': active_overlaps,
            'coordination_records': coordination_records,
            'recent_complaints': complaints_qs[:10],
            'all_complaints': complaints_qs,
        }

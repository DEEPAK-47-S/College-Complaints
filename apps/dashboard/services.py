from datetime import timedelta
from django.db.models import Count, Q, Avg
from django.utils import timezone
from apps.complaints.models import Complaint, ComplaintAction
from apps.intelligence.models import OverlapCandidate
from apps.notifications.models import Notification
from apps.accounts.models import User
from apps.bureaus.models import Bureau

from apps.accounts.queryset_scoping import get_scoped_complaints as scope_complaints, get_scoped_overlap_candidates

class DashboardMetricsService:
    @staticmethod
    def get_scoped_complaints(user):
        return scope_complaints(user)

    @classmethod
    def get_dashboard_kpis(cls, user):
        complaints_qs = cls.get_scoped_complaints(user)
        today = timezone.now().date()

        total = complaints_qs.count()
        pending = complaints_qs.filter(current_status=Complaint.Status.PENDING).count()
        under_process = complaints_qs.filter(current_status=Complaint.Status.UNDER_PROCESS).count()
        transferred = complaints_qs.filter(current_status=Complaint.Status.TRANSFERRED).count()
        escalated = complaints_qs.filter(current_status=Complaint.Status.ESCALATED).count()
        disposed = complaints_qs.filter(current_status=Complaint.Status.DISPOSED).count()

        # Overdue cases (disposal date passed and not yet disposed)
        overdue = complaints_qs.filter(
            expected_disposal_date__lt=today
        ).exclude(current_status=Complaint.Status.DISPOSED).count()

        # Overlaps
        overlaps_qs = get_scoped_overlap_candidates(user)
        pending_overlaps = overlaps_qs.filter(review_status=OverlapCandidate.ReviewStatus.PENDING).count()

        # Safe disposal rate (zero denominator protected)
        disposal_rate = round((disposed / total * 100), 1) if total > 0 else 0.0

        # Bureau workload breakdown
        bureau_workload = list(
            complaints_qs.values(
                'currently_assigned_bureau__code',
                'currently_assigned_bureau__name'
            ).annotate(count=Count('id')).order_by('-count')
        )

        # Regional distribution with display labels
        region_map = dict(User.Region.choices)
        regional_distribution = [
            {
                'region_code': item['institution__region'],
                'region_name': region_map.get(item['institution__region'], item['institution__region'] or 'Unassigned'),
                'count': item['count']
            }
            for item in complaints_qs.values('institution__region').annotate(count=Count('id')).order_by('-count')
            if item['institution__region']
        ]

        # Top High-Activity Institutions case status breakdown
        institution_stats = list(
            complaints_qs.values(
                'institution__id',
                'institution__name',
                'institution__aicte_permanent_id',
                'institution__region'
            ).annotate(
                total_cases=Count('id'),
                active_cases=Count('id', filter=~Q(current_status=Complaint.Status.DISPOSED)),
                disposed_cases=Count('id', filter=Q(current_status=Complaint.Status.DISPOSED)),
                overdue_cases=Count('id', filter=Q(expected_disposal_date__lt=today) & ~Q(current_status=Complaint.Status.DISPOSED))
            ).order_by('-total_cases')[:6]
        )

        # Monthly Intake vs Disposal (past 6 months)
        monthly_trends = []
        for i in range(5, -1, -1):
            target_month = today.replace(day=1) - timedelta(days=i * 30)
            month_label = target_month.strftime('%b %Y')
            month_intake = complaints_qs.filter(
                date_received__year=target_month.year,
                date_received__month=target_month.month
            ).count()
            month_disposed = complaints_qs.filter(
                disposed_at__year=target_month.year,
                disposed_at__month=target_month.month,
                current_status=Complaint.Status.DISPOSED
            ).count()
            monthly_trends.append({
                'month': month_label,
                'intake': month_intake,
                'disposed': month_disposed,
            })

        # Role-specific tailored metrics
        my_assigned_count = 0
        if user.role == User.Role.CASE_OFFICER:
            my_assigned_count = complaints_qs.filter(currently_assigned_officer=user).count()

        pending_transfers_count = 0
        if user.role in [User.Role.BUREAU_HEAD, User.Role.SUPER_ADMIN] and user.assigned_bureau:
            from apps.complaints.models import ComplaintTransfer
            pending_transfers_count = ComplaintTransfer.objects.filter(
                destination_bureau=user.assigned_bureau,
                approval_status=ComplaintTransfer.Status.PENDING
            ).count()

        escalated_cases_count = complaints_qs.filter(current_status=Complaint.Status.ESCALATED).count()

        regional_institutions_count = 0
        if user.role == User.Role.REGIONAL_OFFICER and user.authorized_region:
            from apps.institutions.models import Institution
            regional_institutions_count = Institution.objects.filter(region=user.authorized_region).count()

        # Recent activities visible to user
        recent_actions = ComplaintAction.objects.filter(
            complaint__in=complaints_qs
        ).select_related(
            'complaint', 'responsible_officer', 'responsible_bureau'
        ).order_by('-timestamp')[:8]

        # Urgent unread notifications for user
        urgent_notifications = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).select_related('related_complaint').order_by('-created_at')[:5]

        return {
            'total_complaints': total,
            'total': total,
            'pending_complaints': pending,
            'pending': pending,
            'under_process_complaints': under_process,
            'under_process': under_process,
            'transferred_complaints': transferred,
            'transferred': transferred,
            'escalated_complaints': escalated,
            'escalated': escalated,
            'disposed_complaints': disposed,
            'disposed': disposed,
            'overdue_complaints': overdue,
            'overdue': overdue,
            'pending_overlaps': pending_overlaps,
            'disposal_rate': disposal_rate,
            'my_assigned_count': my_assigned_count,
            'pending_transfers_count': pending_transfers_count,
            'escalated_cases_count': escalated_cases_count,
            'regional_institutions_count': regional_institutions_count,
            'bureau_workload': bureau_workload,
            'regional_distribution': regional_distribution,
            'institution_stats': institution_stats,
            'monthly_trends': monthly_trends,
            'recent_actions': recent_actions,
            'urgent_notifications': urgent_notifications,
        }

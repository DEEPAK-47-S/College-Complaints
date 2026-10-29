from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.complaints.models import Complaint
from apps.bureaus.models import Bureau
from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.accounts.queryset_scoping import get_scoped_complaints
from .services import ExportService

def get_filtered_complaints(request):
    complaints = get_scoped_complaints(request.user)

    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(current_status=status)

    bureau = request.GET.get('bureau')
    if bureau:
        complaints = complaints.filter(currently_assigned_bureau__code=bureau)

    priority = request.GET.get('priority')
    if priority:
        complaints = complaints.filter(priority=priority)

    search = request.GET.get('q')
    if search:
        complaints = complaints.filter(
            Q(complaint_no__icontains=search) |
            Q(title__icontains=search) |
            Q(institution__name__icontains=search)
        )

    return complaints

from .services import ExportService, AnalyticsReportService

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH, User.Role.REGIONAL_OFFICER)
def reports_index_view(request):
    complaints = get_filtered_complaints(request)
    report_type = request.GET.get('report_type', 'bureau_wise')

    # Compute data for all 9 statutory and management reports
    bureau_data = AnalyticsReportService.get_bureau_report(complaints)
    region_data = AnalyticsReportService.get_region_report(complaints)
    institution_data = AnalyticsReportService.get_institution_report(complaints)
    status_data = AnalyticsReportService.get_status_report(complaints)
    ageing_data = AnalyticsReportService.get_ageing_report(complaints)
    disposal_data = AnalyticsReportService.get_disposal_rate_report(complaints)
    overlap_data = AnalyticsReportService.get_overlap_report(request.user)
    monthly_data = AnalyticsReportService.get_monthly_performance_report(complaints)
    quarterly_data = AnalyticsReportService.get_quarterly_performance_report(complaints)

    return render(request, 'reports/index.html', {
        'report_type': report_type,
        'total_count': complaints.count(),
        'complaints': complaints[:25],
        'bureaus': Bureau.objects.filter(is_active=True),
        'statuses': Complaint.Status.choices,
        'priorities': Complaint.Priority.choices,
        # 9 Analytical Report Datasets
        'bureau_data': bureau_data,
        'region_data': region_data,
        'institution_data': institution_data,
        'status_data': status_data,
        'ageing_data': ageing_data,
        'disposal_data': disposal_data,
        'overlap_data': overlap_data,
        'monthly_data': monthly_data,
        'quarterly_data': quarterly_data,
    })

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH, User.Role.REGIONAL_OFFICER)
def export_csv_view(request):
    complaints = get_filtered_complaints(request)
    return ExportService.to_csv(complaints)

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH, User.Role.REGIONAL_OFFICER)
def export_excel_view(request):
    complaints = get_filtered_complaints(request)
    return ExportService.to_excel(complaints)

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.SENIOR_MGMT, User.Role.COMPETENT_AUTH, User.Role.REGIONAL_OFFICER)
def export_pdf_view(request):
    complaints = get_filtered_complaints(request)
    return ExportService.to_pdf(complaints)

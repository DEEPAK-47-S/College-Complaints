from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from .models import Institution
from .forms import InstitutionForm
from .services import Institution360Service
from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.audit.services import log_audit_event

@login_required
def institution_list_view(request):
    institutions = Institution.objects.all()

    # Regional officer scope
    if request.user.role == User.Role.REGIONAL_OFFICER and request.user.authorized_region:
        institutions = institutions.filter(region=request.user.authorized_region)

    search_query = (request.GET.get('q') or request.GET.get('search') or '').strip()
    if search_query:
        institutions = institutions.filter(
            Q(name__icontains=search_query) |
            Q(aicte_permanent_id__icontains=search_query) |
            Q(district__icontains=search_query) |
            Q(state__icontains=search_query)
        )

    region_filter = request.GET.get('region', '')
    if region_filter:
        institutions = institutions.filter(region=region_filter)

    type_filter = request.GET.get('type', '')
    if type_filter:
        institutions = institutions.filter(institution_type=type_filter)

    status_filter = request.GET.get('status', '')
    if status_filter:
        institutions = institutions.filter(operational_status=status_filter)

    paginator = Paginator(institutions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'institutions/institution_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'region_filter': region_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'regions': User.Region.choices,
        'types': Institution.InstitutionType.choices,
        'statuses': Institution.Status.choices,
        'total_count': institutions.count(),
    })

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.CASE_OFFICER, User.Role.REGIONAL_OFFICER)
def institution_create_view(request):
    form = InstitutionForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            institution = form.save()
            log_audit_event(
                actor=request.user,
                event_type="INSTITUTION_REGISTERED",
                entity_name="Institution",
                entity_id=str(institution.id),
                change_summary={
                    "name": institution.name,
                    "aicte_permanent_id": institution.aicte_permanent_id,
                    "region": institution.region
                },
                request=request
            )
            messages.success(request, f"Institution '{institution.name}' successfully registered with ID {institution.aicte_permanent_id}.")
            return redirect('institutions:detail', pk=institution.id)
        else:
            messages.error(request, "Please check the form inputs for errors.")

    return render(request, 'institutions/institution_form.html', {
        'form': form,
        'title': 'Register New Institution',
        'is_new': True
    })

@login_required
def institution_detail_view(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    # Check regional scope if regional officer
    if request.user.role == User.Role.REGIONAL_OFFICER and request.user.authorized_region:
        if institution.region != request.user.authorized_region:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You are not authorized to access institutions outside your region.")

    complaints = institution.complaints.select_related('category', 'currently_assigned_bureau').order_by('-date_received')[:10]
    return render(request, 'institutions/institution_detail.html', {
        'institution': institution,
        'recent_complaints': complaints,
    })

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD)
def institution_edit_view(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    form = InstitutionForm(request.POST or None, instance=institution)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            log_audit_event(
                actor=request.user,
                event_type="INSTITUTION_UPDATED",
                entity_name="Institution",
                entity_id=str(institution.id),
                change_summary={"updated_fields": list(form.changed_data)},
                request=request
            )
            messages.success(request, f"Institution '{institution.name}' updated successfully.")
            return redirect('institutions:detail', pk=institution.id)
        else:
            messages.error(request, "Please correct the errors in the form.")

    return render(request, 'institutions/institution_form.html', {
        'form': form,
        'institution': institution,
        'title': f"Edit {institution.name}",
        'is_new': False
    })

@login_required
def institution_360_view(request, pk):
    """
    ★ UNIQUE INNOVATION: Institution 360° Consolidated Dossier
    Presents an institution-centric multi-bureau intelligence perspective.
    """
    institution = get_object_or_404(Institution, pk=pk)
    if request.user.role == User.Role.REGIONAL_OFFICER and request.user.authorized_region:
        if institution.region != request.user.authorized_region:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You are not authorized to view the 360 dossier for an institution outside your region.")

    dossier = Institution360Service.get_dossier(institution.id, user=request.user)
    return render(request, 'institutions/institution_360.html', dossier)

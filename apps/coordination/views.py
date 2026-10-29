from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from .models import CoordinationRecord, CoordinationNote
from .forms import CoordinationCreateForm, CoordinationNoteForm
from .services import CoordinationService
from apps.complaints.models import Complaint
from apps.bureaus.models import Bureau
from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.accounts.access_policy import (
    user_can_view_coordination,
    user_can_add_coordination_note,
    user_can_update_coordination_status,
    user_can_create_coordination,
)
from apps.accounts.queryset_scoping import get_scoped_coordinations, get_scoped_complaints

@login_required
def coordination_list_view(request):
    records = get_scoped_coordinations(request.user)

    status_filter = request.GET.get('status')
    if status_filter:
        records = records.filter(coordination_status=status_filter)

    search = request.GET.get('q', '').strip()
    if search:
        records = records.filter(
            Q(coordination_no__icontains=search) |
            Q(title__icontains=search)
        )

    paginator = Paginator(records, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'coordination/coordination_list.html', {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'statuses': CoordinationRecord.Status.choices,
        'total_count': records.count(),
    })

@login_required
def coordination_create_view(request):
    if not user_can_create_coordination(request.user):
        raise PermissionDenied("You do not possess authority to initiate cross-bureau coordination.")

    candidate_id = request.GET.get('candidate_id')
    complaint_ids = request.GET.getlist('complaint_id')

    initial = {}
    complaints_preselected = []

    if candidate_id:
        from apps.intelligence.models import OverlapCandidate
        candidate = get_object_or_404(OverlapCandidate, pk=candidate_id)
        # Check user can access at least one complaint
        accessible_complaints = get_scoped_complaints(request.user)
        if not (accessible_complaints.filter(id=candidate.first_complaint_id).exists() or
                accessible_complaints.filter(id=candidate.second_complaint_id).exists()):
            raise PermissionDenied("You cannot establish coordination for complaints outside your jurisdictional clearance.")

        complaints_preselected = [candidate.first_complaint, candidate.second_complaint]
        initial = {
            'title': f"Joint Coordination: {candidate.first_complaint.institution.name}",
            'coordinating_bureau': candidate.first_complaint.currently_assigned_bureau,
            'participating_bureaus': [
                candidate.first_complaint.currently_assigned_bureau,
                candidate.second_complaint.currently_assigned_bureau
            ],
            'complaints': complaints_preselected,
            'action_plan': f"Joint investigation into reported issues across {candidate.first_complaint.complaint_no} and {candidate.second_complaint.complaint_no}."
        }
    elif complaint_ids:
        accessible = get_scoped_complaints(request.user).filter(id__in=complaint_ids)
        complaints_preselected = list(accessible)
        if len(complaints_preselected) < len(complaint_ids) and not request.user.is_superuser:
            raise PermissionDenied("One or more submitted complaints are outside your authorized clearance.")
        initial = {'complaints': complaints_preselected}

    form = CoordinationCreateForm(request.POST or None, initial=initial)
    if request.method == 'POST':
        if form.is_valid():
            selected_complaints = form.cleaned_data['complaints']
            # Server-side validation: Ensure user has clearance for these cases
            accessible_ids = set(get_scoped_complaints(request.user).values_list('id', flat=True))
            if not request.user.is_superuser and not request.user.role in [User.Role.SUPER_ADMIN, User.Role.COMPETENT_AUTH]:
                for c in selected_complaints:
                    if c.id not in accessible_ids:
                        raise PermissionDenied(f"Access denied to include complaint {c.complaint_no} in coordination.")

            coord = CoordinationService.initiate_coordination(
                title=form.cleaned_data['title'],
                coordinating_bureau=form.cleaned_data['coordinating_bureau'],
                participating_bureaus=form.cleaned_data['participating_bureaus'],
                complaints=selected_complaints,
                created_by=request.user,
                action_plan=form.cleaned_data['action_plan'],
                deadline=form.cleaned_data['deadline']
            )
            messages.success(request, f"Joint Coordination workspace {coord.coordination_no} established.")
            return redirect('coordination:detail', pk=coord.id)
        else:
            messages.error(request, "Please verify all fields in the coordination form.")

    return render(request, 'coordination/coordination_form.html', {
        'form': form,
        'title': 'Initiate Cross-Bureau Coordination'
    })

@login_required
def coordination_detail_view(request, pk):
    coord = get_object_or_404(
        CoordinationRecord.objects.select_related('coordinating_bureau', 'created_by').prefetch_related(
            'participating_bureaus', 'related_complaints__institution', 'related_complaints__currently_assigned_bureau',
            'responsible_officers', 'notes__author', 'notes__author_bureau'
        ),
        pk=pk
    )

    if not user_can_view_coordination(request.user, coord):
        raise PermissionDenied("You are not authorized to view this coordination workspace.")

    note_form = CoordinationNoteForm()
    can_manage = user_can_update_coordination_status(request.user, coord)
    can_add_note = user_can_add_coordination_note(request.user, coord)

    return render(request, 'coordination/coordination_detail.html', {
        'coordination': coord,
        'complaints': coord.related_complaints.all(),
        'notes': coord.notes.all(),
        'note_form': note_form,
        'can_manage': can_manage,
        'can_add_note': can_add_note,
        'statuses': CoordinationRecord.Status.choices,
    })

@login_required
def coordination_add_note_view(request, pk):
    if request.method != 'POST':
        return redirect('coordination:detail', pk=pk)

    coord = get_object_or_404(CoordinationRecord, pk=pk)
    if not user_can_add_coordination_note(request.user, coord):
        raise PermissionDenied("You are not authorized to record notes in this coordination workspace.")

    form = CoordinationNoteForm(request.POST)
    if form.is_valid():
        CoordinationService.add_note(coord, request.user, form.cleaned_data['note'])
        messages.success(request, "Coordination note recorded in shared timeline.")
    else:
        messages.error(request, "Note content cannot be empty.")

    return redirect('coordination:detail', pk=pk)

@login_required
def coordination_status_update_view(request, pk):
    if request.method != 'POST':
        return redirect('coordination:detail', pk=pk)

    coord = get_object_or_404(CoordinationRecord, pk=pk)
    if not user_can_update_coordination_status(request.user, coord):
        raise PermissionDenied("You are not authorized to update coordination status. Only Lead Bureau Head, Competent Authority, or Super Admin can modify coordination lifecycle.")

    new_status = request.POST.get('status')
    if new_status not in dict(CoordinationRecord.Status.choices):
        messages.error(request, "Invalid coordination status specified.")
        return redirect('coordination:detail', pk=pk)

    decision_summary = request.POST.get('decision_summary', '')
    CoordinationService.update_coordination_status(coord, new_status, request.user, decision_summary)
    messages.success(request, f"Coordination status updated to {new_status}.")
    return redirect('coordination:detail', pk=pk)

import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.db.models import Q
from django.utils import timezone

from .models import (
    Complaint, ComplaintCategory, ComplaintDocument,
    ComplaintAction, ComplaintTransfer, ComplaintEscalation, CaseRelationship
)
from .forms import (
    ComplaintCreateForm, OfficerAssignmentForm, StatusTransitionForm,
    TransferRequestForm, EscalationRequestForm, DocumentUploadForm
)
from .services import create_complaint, validate_and_save_document
from apps.workflows.services import WorkflowEngine
from apps.workflows.exceptions import WorkflowError
from apps.accounts.permissions import (
    user_can_access_complaint, user_can_modify_complaint, role_required,
    user_can_upload_document, user_can_download_document
)
from apps.accounts.queryset_scoping import get_scoped_complaints
from apps.accounts.models import User
from apps.bureaus.models import Bureau

@login_required
def complaint_list_view(request):
    complaints = get_scoped_complaints(request.user)

    user = request.user
    # Role Scoping
    if user.role == User.Role.BUREAU_HEAD:
        complaints = complaints.filter(currently_assigned_bureau=user.assigned_bureau)
    elif user.role == User.Role.CASE_OFFICER:
        # Bureau complaints or directly assigned
        complaints = complaints.filter(
            Q(currently_assigned_bureau=user.assigned_bureau) | Q(currently_assigned_officer=user)
        )
    elif user.role == User.Role.REGIONAL_OFFICER and user.authorized_region:
        complaints = complaints.filter(institution__region=user.authorized_region)

    # Search query
    search = request.GET.get('q', '').strip()
    if search:
        complaints = complaints.filter(
            Q(complaint_no__icontains=search) |
            Q(title__icontains=search) |
            Q(institution__name__icontains=search) |
            Q(institution__aicte_permanent_id__icontains=search) |
            Q(external_reference_no__icontains=search)
        )

    # Status filter
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(current_status=status)

    # Bureau filter (for roles with multi-bureau visibility)
    bureau_code = request.GET.get('bureau')
    if bureau_code:
        complaints = complaints.filter(currently_assigned_bureau__code=bureau_code)

    # Priority filter (FIXED: applied to database queryset)
    priority = request.GET.get('priority')
    if priority:
        complaints = complaints.filter(priority=priority)

    # Region filter
    region = request.GET.get('region')
    if region:
        complaints = complaints.filter(institution__region=region)

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        complaints = complaints.filter(category_id=category_id)

    # Date range filters
    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        complaints = complaints.filter(date_received__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        complaints = complaints.filter(date_received__lte=date_to)

    # Overdue filter
    is_overdue = request.GET.get('overdue')
    if is_overdue == '1':
        complaints = complaints.filter(
            expected_disposal_date__lt=timezone.now().date()
        ).exclude(current_status=Complaint.Status.DISPOSED)

    # Officer filter
    officer_id = request.GET.get('officer')
    if officer_id:
        complaints = complaints.filter(currently_assigned_officer_id=officer_id)

    # Sorting options
    sort = request.GET.get('sort', '-date_received')
    sort_options = {
        '-date_received': '-date_received',
        'date_received': 'date_received',
        'due_date': 'expected_disposal_date',
        '-due_date': '-expected_disposal_date',
        '-created_at': '-created_at',
    }
    complaints = complaints.order_by(sort_options.get(sort, '-date_received'))

    paginator = Paginator(complaints, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from .models import ComplaintCategory
    return render(request, 'complaints/complaint_list.html', {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status,
        'bureau_filter': bureau_code,
        'priority_filter': priority,
        'region_filter': region,
        'category_filter': category_id,
        'date_from': date_from,
        'date_to': date_to,
        'sort_filter': sort,
        'overdue_filter': is_overdue,
        'officer_filter': officer_id,
        'statuses': Complaint.Status.choices,
        'priorities': Complaint.Priority.choices,
        'regions': User.Region.choices,
        'categories': ComplaintCategory.objects.filter(is_active=True),
        'bureaus': Bureau.objects.filter(is_active=True),
        'total_count': complaints.count(),
    })

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.BUREAU_HEAD, User.Role.CASE_OFFICER, User.Role.REGIONAL_OFFICER)
def complaint_create_view(request):
    form = ComplaintCreateForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            try:
                complaint = create_complaint(
                    institution=form.cleaned_data['institution'],
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    category=form.cleaned_data['category'],
                    bureau=form.cleaned_data['currently_assigned_bureau'],
                    source_channel=form.cleaned_data['source_channel'],
                    created_by=request.user,
                    priority=form.cleaned_data['priority'],
                    external_reference_no=form.cleaned_data.get('external_reference_no', '')
                )
                messages.success(request, f"Complaint {complaint.complaint_no} registered successfully.")
                return redirect('complaints:detail', pk=complaint.id)
            except Exception as e:
                messages.error(request, f"Error registering complaint: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'complaints/complaint_form.html', {
        'form': form,
        'title': 'Register New Complaint / Grievance'
    })

@login_required
def complaint_detail_view(request, pk):
    complaint = get_object_or_404(
        Complaint.objects.select_related(
            'institution', 'category', 'currently_assigned_bureau', 'currently_assigned_officer', 'created_by'
        ),
        pk=pk
    )

    if not user_can_access_complaint(request.user, complaint):
        raise PermissionDenied("You are not authorized to view this complaint.")

    active_tab = request.GET.get('tab', 'overview')

    # Sub-data for tabs
    actions = complaint.actions.select_related('responsible_officer', 'responsible_bureau').order_by('-timestamp')
    documents = complaint.documents.select_related('uploader').order_by('-upload_timestamp')

    # Overlaps involving this complaint
    from apps.intelligence.models import OverlapCandidate
    overlaps = OverlapCandidate.objects.filter(
        Q(first_complaint=complaint) | Q(second_complaint=complaint)
    ).select_related(
        'first_complaint__currently_assigned_bureau',
        'second_complaint__currently_assigned_bureau',
        'first_complaint__category',
        'second_complaint__category'
    )

    # Relationships
    relationships = CaseRelationship.objects.filter(
        Q(source_complaint=complaint) | Q(target_complaint=complaint)
    ).select_related('source_complaint', 'target_complaint')

    # Coordinations
    coordinations = complaint.coordination_records.all().select_related('coordinating_bureau')

    # Forms for modals
    assign_form = OfficerAssignmentForm(bureau=complaint.currently_assigned_bureau)
    transition_form = StatusTransitionForm(initial={'new_status': complaint.current_status})
    transfer_form = TransferRequestForm()
    escalate_form = EscalationRequestForm()
    document_form = DocumentUploadForm()

    can_modify = user_can_modify_complaint(request.user, complaint)

    return render(request, 'complaints/complaint_detail.html', {
        'complaint': complaint,
        'active_tab': active_tab,
        'actions': actions,
        'documents': documents,
        'overlaps': overlaps,
        'relationships': relationships,
        'coordinations': coordinations,
        'assign_form': assign_form,
        'transition_form': transition_form,
        'transfer_form': transfer_form,
        'escalate_form': escalate_form,
        'document_form': document_form,
        'can_modify': can_modify,
    })

@login_required
def complaint_assign_view(request, pk):
    if request.method != 'POST':
        return redirect('complaints:detail', pk=pk)
    complaint = get_object_or_404(Complaint, pk=pk)
    if not (request.user.is_superuser or request.user.role in ['BUREAU_HEAD', 'SUPER_ADMIN']):
        raise PermissionDenied("Only Bureau Heads or Administrators can assign case officers.")

    form = OfficerAssignmentForm(request.POST, bureau=complaint.currently_assigned_bureau)
    if form.is_valid():
        officer = form.cleaned_data['officer']
        remarks = form.cleaned_data.get('remarks', '')
        try:
            WorkflowEngine.assign_officer(complaint, officer, request.user, remarks, request=request)
            messages.success(request, f"Case successfully assigned to {officer.display_name}.")
        except WorkflowError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Invalid assignment form submission.")

    return redirect('complaints:detail', pk=pk)

@login_required
def complaint_transition_view(request, pk):
    if request.method != 'POST':
        return redirect('complaints:detail', pk=pk)
    complaint = get_object_or_404(Complaint, pk=pk)

    if not user_can_modify_complaint(request.user, complaint):
        raise PermissionDenied("You are not authorized to transition the status of this complaint.")

    form = StatusTransitionForm(request.POST)
    if form.is_valid():
        new_status = form.cleaned_data['new_status']
        remarks = form.cleaned_data['remarks']
        next_action = form.cleaned_data.get('next_action_required')
        try:
            WorkflowEngine.transition_status(
                complaint, new_status, request.user, remarks,
                request=request, next_action_required=next_action
            )
            messages.success(request, f"Status updated to '{new_status}'.")
        except WorkflowError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Please provide valid status and remarks.")

    return redirect('complaints:detail', pk=pk)

@login_required
def complaint_transfer_view(request, pk):
    if request.method != 'POST':
        return redirect('complaints:detail', pk=pk)
    complaint = get_object_or_404(Complaint, pk=pk)
    form = TransferRequestForm(request.POST)
    if form.is_valid():
        try:
            WorkflowEngine.request_transfer(
                complaint,
                form.cleaned_data['destination_bureau'],
                request.user,
                form.cleaned_data['reason'],
                request=request
            )
            messages.success(request, "Transfer request submitted for approval.")
        except WorkflowError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Invalid transfer request.")

    return redirect('complaints:detail', pk=pk)

@login_required
def complaint_escalate_view(request, pk):
    if request.method != 'POST':
        return redirect('complaints:detail', pk=pk)
    complaint = get_object_or_404(Complaint, pk=pk)
    form = EscalationRequestForm(request.POST)
    if form.is_valid():
        try:
            WorkflowEngine.escalate_complaint(
                complaint,
                form.cleaned_data['escalation_level'],
                request.user,
                form.cleaned_data['reason'],
                request=request
            )
            messages.success(request, "Complaint successfully escalated to Competent Authority.")
        except WorkflowError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Invalid escalation submission.")

    return redirect('complaints:detail', pk=pk)

@login_required
def complaint_upload_document_view(request, pk):
    if request.method != 'POST':
        return redirect('complaints:detail', pk=pk)
    complaint = get_object_or_404(Complaint, pk=pk)

    if not user_can_upload_document(request.user, complaint):
        raise PermissionDenied("You are not authorized to upload documents to this case.")

    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            doc = validate_and_save_document(
                complaint=complaint,
                file_obj=request.FILES['file'],
                user=request.user,
                classification=form.cleaned_data['classification']
            )
            messages.success(request, f"Document '{doc.original_filename}' uploaded successfully.")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, 'message') else str(e))
    else:
        messages.error(request, "File upload failed. Ensure the file is a PDF/PNG/JPG under 10MB.")

    return redirect(f"/complaints/{pk}/?tab=documents")

@login_required
def complaint_download_document_view(request, pk, doc_id):
    """
    Private document streaming view (T25, T26)
    Validates user authorization and classification level before reading private media file.
    """
    complaint = get_object_or_404(Complaint, pk=pk)
    document = get_object_or_404(ComplaintDocument, pk=doc_id, complaint=complaint)

    if not user_can_download_document(request.user, document):
        raise PermissionDenied("You do not have clearance to access this classified document.")

    if not document.file or not os.path.exists(document.file.path):
        raise Http404("Document file could not be found.")

    return FileResponse(
        open(document.file.path, 'rb'),
        as_attachment=True,
        filename=document.original_filename
    )

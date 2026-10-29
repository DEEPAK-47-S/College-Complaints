from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, F
from .models import OverlapCandidate
from .services import OverlapDetectionService
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.accounts.access_policy import (
    user_can_view_overlap_candidate,
    user_can_review_overlap_candidate,
    user_can_view_complaint,
)
from apps.accounts.queryset_scoping import get_scoped_overlap_candidates

@login_required
def intelligence_dashboard_view(request):
    candidates = get_scoped_overlap_candidates(request.user)

    # Status filter
    status = request.GET.get('status', 'PENDING')
    if status and status != 'ALL':
        candidates = candidates.filter(review_status=status)

    # Cross-Bureau filter
    cross_bureau = request.GET.get('cross_bureau')
    if cross_bureau == '1':
        candidates = candidates.exclude(
            first_complaint__currently_assigned_bureau_id=F('second_complaint__currently_assigned_bureau_id')
        )

    # Search filter
    search = request.GET.get('q', '').strip()
    if search:
        candidates = candidates.filter(
            Q(first_complaint__complaint_no__icontains=search) |
            Q(second_complaint__complaint_no__icontains=search) |
            Q(first_complaint__institution__name__icontains=search) |
            Q(first_complaint__institution__aicte_permanent_id__icontains=search)
        )

    # Scoped metric counts
    scoped_base = get_scoped_overlap_candidates(request.user)
    total_count = scoped_base.count()
    pending_count = scoped_base.filter(review_status=OverlapCandidate.ReviewStatus.PENDING).count()
    confirmed_count = scoped_base.filter(review_status=OverlapCandidate.ReviewStatus.CONFIRMED).count()
    dismissed_count = scoped_base.filter(review_status=OverlapCandidate.ReviewStatus.DISMISSED).count()

    paginator = Paginator(candidates, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'intelligence/dashboard.html', {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status,
        'cross_bureau_filter': cross_bureau,
        'total_count': total_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'dismissed_count': dismissed_count,
        'statuses': OverlapCandidate.ReviewStatus.choices,
    })

@login_required
def candidate_detail_view(request, pk):
    candidate = get_object_or_404(
        OverlapCandidate.objects.select_related(
            'first_complaint__institution',
            'second_complaint__institution',
            'first_complaint__currently_assigned_bureau',
            'second_complaint__currently_assigned_bureau',
            'first_complaint__category',
            'second_complaint__category',
            'first_complaint__currently_assigned_officer',
            'second_complaint__currently_assigned_officer',
            'reviewed_by'
        ),
        pk=pk
    )

    if not user_can_view_overlap_candidate(request.user, candidate):
        raise PermissionDenied("You are not authorized to view this cross-case intelligence candidate.")

    can_review = user_can_review_overlap_candidate(request.user, candidate)

    # Scrutiny projection: If user cannot view full complaint details of one side, sanitize it
    first_allowed = user_can_view_complaint(request.user, candidate.first_complaint)
    second_allowed = user_can_view_complaint(request.user, candidate.second_complaint)

    first_description = (
        candidate.first_complaint.description
        if first_allowed
        else "[Confidential Grievance Narrative – Protected by Scrutiny Boundary]"
    )
    second_description = (
        candidate.second_complaint.description
        if second_allowed
        else "[Confidential Grievance Narrative – Protected by Scrutiny Boundary]"
    )

    # Gemini AI Deep Analysis
    from .gemini_service import GeminiAnalysisService
    gemini_data = GeminiAnalysisService.analyze_overlap(candidate)

    return render(request, 'intelligence/candidate_detail.html', {
        'candidate': candidate,
        'first': candidate.first_complaint,
        'second': candidate.second_complaint,
        'first_description': first_description,
        'second_description': second_description,
        'first_allowed': first_allowed,
        'second_allowed': second_allowed,
        'can_review': can_review,
        'gemini_data': gemini_data,
        'is_gemini_live': gemini_data.get('is_live_gemini', False),
    })

@login_required
def run_gemini_analysis_view(request, pk):
    candidate = get_object_or_404(OverlapCandidate, pk=pk)
    if not user_can_view_overlap_candidate(request.user, candidate):
        raise PermissionDenied("You are not authorized to analyze this candidate.")
    
    from .gemini_service import GeminiAnalysisService
    gemini_res = GeminiAnalysisService.analyze_overlap(candidate, force_refresh=True)
    if gemini_res.get('is_live_gemini'):
        messages.success(request, "Google Gemini AI live regulatory analysis updated successfully!")
    else:
        messages.info(request, "AI Semantic Analysis refreshed. (To activate live Google Gemini API, set GEMINI_API_KEY in .env)")
    return redirect('intelligence:detail', pk=pk)


@login_required
def candidate_review_action_view(request, pk):
    if request.method != 'POST':
        return redirect('intelligence:detail', pk=pk)

    candidate = get_object_or_404(OverlapCandidate, pk=pk)
    if not user_can_review_overlap_candidate(request.user, candidate):
        raise PermissionDenied("You do not hold review clearance for this overlap alert.")

    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '').strip()

    if not remarks:
        messages.error(request, "Review remarks are mandatory when confirming or dismissing an overlap candidate.")
        return redirect('intelligence:detail', pk=pk)

    if action == 'confirm':
        OverlapDetectionService.confirm_overlap(pk, request.user, remarks)
        messages.success(request, "Overlap confirmed as a related case. You can now initiate joint coordination.")
    elif action == 'dismiss':
        OverlapDetectionService.dismiss_overlap(pk, request.user, remarks)
        messages.info(request, "Overlap candidate marked as dismissed (false-positive).")
    elif action == 'separate':
        OverlapDetectionService.mark_as_separate_issues(pk, request.user, remarks)
        messages.info(request, "Grievances confirmed as distinct separate issues against the same institution.")
    else:
        messages.error(request, "Invalid review action.")

    return redirect('intelligence:detail', pk=pk)

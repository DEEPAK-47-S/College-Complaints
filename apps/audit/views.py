from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from apps.accounts.permissions import role_required
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from .models import AuditEvent

@login_required
@role_required(User.Role.SUPER_ADMIN, User.Role.SENIOR_MGMT, User.Role.BUREAU_HEAD)
def audit_log_list_view(request):
    events = AuditEvent.objects.all()

    # Scoping for Bureau Head: view events relevant to own bureau or actors
    if request.user.role == User.Role.BUREAU_HEAD:
        events = events.filter(actor__assigned_bureau=request.user.assigned_bureau)

    event_type = request.GET.get('event_type')
    if event_type:
        events = events.filter(event_type__icontains=event_type)

    entity_type = request.GET.get('entity_type')
    if entity_type:
        events = events.filter(entity_type__icontains=entity_type)

    search = request.GET.get('q')
    if search:
        events = events.filter(entity_id__icontains=search) | events.filter(actor_username__icontains=search)

    paginator = Paginator(events, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'audit/audit_list.html', {
        'page_obj': page_obj,
        'event_type': event_type,
        'entity_type': entity_type,
        'search': search,
    })

@login_required
@role_required(User.Role.SUPER_ADMIN)
def user_management_list_view(request):
    users = User.objects.all().select_related('assigned_bureau')
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'audit/user_list.html', {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'roles': User.Role.choices,
    })

@login_required
@role_required(User.Role.SUPER_ADMIN)
def bureau_management_list_view(request):
    bureaus = Bureau.objects.all()
    return render(request, 'audit/bureau_list.html', {'bureaus': bureaus})

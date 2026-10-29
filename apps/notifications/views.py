from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Notification
from .services import NotificationService

@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(recipient=request.user)

    filter_type = request.GET.get('type')
    if filter_type:
        notifications = notifications.filter(notification_type=filter_type)

    unread_only = request.GET.get('unread')
    if unread_only == '1':
        notifications = notifications.filter(is_read=False)

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'unread_only': unread_only,
        'types': Notification.Type.choices,
        'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count(),
    })

@login_required
def mark_notification_read_view(request, pk):
    if request.method == 'POST':
        NotificationService.mark_as_read(pk, request.user)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'notifications:list'
    return redirect(next_url)

@login_required
def mark_all_read_view(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
    return redirect('notifications:list')

@login_required
def unread_count_api_view(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    if request.headers.get('HX-Request'):
        if count > 0:
            return HttpResponse(f'<span class="badge bg-danger rounded-pill pulse-badge">{count}</span>')
        return HttpResponse('')
    return JsonResponse({'unread_count': count})

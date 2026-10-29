from .models import Notification

def unread_notifications_count(request):
    """
    Template context processor providing unread notifications count for badge rendering.
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}

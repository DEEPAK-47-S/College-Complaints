from datetime import timedelta
from django.utils import timezone
from .models import Notification
from apps.accounts.models import User

class NotificationService:
    @staticmethod
    def send_notification(recipient, notification_type, title, message, complaint=None, coordination=None, event_key=None):
        """
        Idempotent notification dispatch using deterministic event_key (T21).
        Guarantees zero alert flooding across multiple scanner runs.
        """
        if not event_key:
            target_id = str(complaint.id) if complaint else (str(coordination.id) if coordination else 'sys')
            today_str = timezone.now().strftime('%Y-%m-%d')
            event_key = f"{recipient.id}:{notification_type}:{target_id}:{today_str}"

        existing = Notification.objects.filter(event_key=event_key).first()
        if existing:
            return existing

        recent_threshold = timezone.now() - timedelta(hours=24)
        duplicate_check = Notification.objects.filter(
            recipient=recipient,
            notification_type=notification_type,
            related_complaint=complaint,
            related_coordination=coordination,
            is_read=False,
            created_at__gte=recent_threshold
        )
        if duplicate_check.exists():
            return duplicate_check.first()

        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_complaint=complaint,
            related_coordination=coordination,
            event_key=event_key
        )

    @staticmethod
    def send_cross_bureau_overlap_alert(overlap_candidate):
        """
        Alerts Bureau Heads of both handling Bureaus when a cross-bureau overlap is detected.
        """
        bureau_1 = overlap_candidate.first_complaint.currently_assigned_bureau
        bureau_2 = overlap_candidate.second_complaint.currently_assigned_bureau

        # Find Bureau Heads
        recipients = User.objects.filter(
            is_active=True,
            role=User.Role.BUREAU_HEAD,
            assigned_bureau__in=[bureau_1, bureau_2]
        )

        title = f"Cross-Bureau Overlap Alert: {overlap_candidate.first_complaint.institution.name}"
        msg = (
            f"A potential overlap was detected between {overlap_candidate.first_complaint.complaint_no} "
            f"({bureau_1.code}) and {overlap_candidate.second_complaint.complaint_no} ({bureau_2.code}). "
            f"Combined AI similarity score: {overlap_candidate.percentage_score}%."
        )

        created_alerts = []
        for officer in recipients:
            n = NotificationService.send_notification(
                recipient=officer,
                notification_type=Notification.Type.OVERLAP_ALERT,
                title=title,
                message=msg,
                complaint=overlap_candidate.first_complaint
            )
            created_alerts.append(n)
        return created_alerts

    @staticmethod
    def notify_officers_new_public_complaint(complaint):
        """
        Dispatches in-app notifications to active Case Officers, Bureau Heads, and Admins
        when a new public portal grievance is registered.
        """
        recipients = User.objects.filter(is_active=True).exclude(role=User.Role.COMPETENT_AUTH)
        title = f"New Public Grievance: {complaint.complaint_no}"
        msg = f"Public grievance registered for {complaint.institution.name} ({complaint.category.name}): '{complaint.title[:70]}'."
        for officer in recipients:
            NotificationService.send_notification(
                recipient=officer,
                notification_type=Notification.Type.ASSIGNMENT,
                title=title,
                message=msg,
                complaint=complaint,
                event_key=f"public_complaint:{officer.id}:{complaint.id}"
            )

    @staticmethod
    def mark_as_read(notification_id, user):
        if getattr(user, 'is_super_admin', False) or user.is_superuser:
            notification = Notification.objects.filter(id=notification_id).first()
        else:
            notification = Notification.objects.filter(id=notification_id, recipient=user).first()
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            return True
        return False

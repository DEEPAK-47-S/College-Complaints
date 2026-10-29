from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.complaints.models import Complaint
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.accounts.models import User

class Command(BaseCommand):
    help = "Idempotent SLA compliance scanner: checks overdue cases, approaching deadlines, and pending case ageing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--warning-days',
            type=int,
            default=5,
            help='Configurable threshold days prior to breach when approaching warning alerts trigger (default: 5 days)'
        )
        parser.add_argument(
            '--pending-reminder-days',
            type=int,
            default=7,
            help='Days a complaint remains in PENDING status before triggering a reminder to Bureau Head (default: 7 days)'
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        default_warning_days = options.get('warning_days', 5)
        pending_reminder_days = options.get('pending_reminder_days', 7)

        active_cases = Complaint.objects.filter(
            current_status__in=[
                Complaint.Status.PENDING,
                Complaint.Status.UNDER_PROCESS,
                Complaint.Status.ESCALATED
            ]
        ).exclude(expected_disposal_date__isnull=True)

        overdue_count = 0
        approaching_count = 0
        pending_reminder_count = 0

        for complaint in active_cases:
            recipients = set()
            if complaint.currently_assigned_officer:
                recipients.add(complaint.currently_assigned_officer)

            # Also notify Bureau Head
            bureau_heads = User.objects.filter(
                assigned_bureau=complaint.currently_assigned_bureau,
                role=User.Role.BUREAU_HEAD,
                is_active=True
            )
            for bh in bureau_heads:
                recipients.add(bh)

            # Determine configurable warning window for this complaint
            threshold_days = default_warning_days
            if complaint.applicable_sla_policy and complaint.applicable_sla_policy.escalation_threshold_days:
                threshold_days = complaint.applicable_sla_policy.escalation_threshold_days
            warning_window = today + timedelta(days=threshold_days)

            # Check 1: Overdue
            if complaint.expected_disposal_date < today:
                overdue_days = (today - complaint.expected_disposal_date).days
                for r in recipients:
                    NotificationService.send_notification(
                        recipient=r,
                        notification_type=Notification.Type.OVERDUE_ALERT,
                        title=f"URGENT: SLA Overdue on {complaint.complaint_no}",
                        message=f"Case {complaint.complaint_no} against '{complaint.institution.name}' is overdue by {overdue_days} day(s). Immediate disposal action required.",
                        complaint=complaint
                    )
                overdue_count += 1

            # Check 2: Approaching deadline (within configurable threshold)
            elif today <= complaint.expected_disposal_date <= warning_window:
                days_left = (complaint.expected_disposal_date - today).days
                for r in recipients:
                    NotificationService.send_notification(
                        recipient=r,
                        notification_type=Notification.Type.APPROACHING_SLA,
                        title=f"SLA Warning: {complaint.complaint_no} due in {days_left} day(s)",
                        message=f"Case {complaint.complaint_no} against '{complaint.institution.name}' has an approaching disposal deadline ({complaint.expected_disposal_date}).",
                        complaint=complaint
                    )
                approaching_count += 1

            # Check 3: Pending Case Ageing Reminder
            if complaint.current_status == Complaint.Status.PENDING:
                age_days = (today - complaint.date_received).days
                if age_days >= pending_reminder_days:
                    for bh in bureau_heads:
                        NotificationService.send_notification(
                            recipient=bh,
                            notification_type=Notification.Type.PENDING_REMINDER,
                            title=f"Pending Case Reminder: {complaint.complaint_no} unassigned ({age_days} days)",
                            message=f"Case {complaint.complaint_no} for '{complaint.institution.name}' has been in PENDING status for {age_days} days without officer assignment.",
                            complaint=complaint
                        )
                    pending_reminder_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA scan completed successfully: {active_cases.count()} cases evaluated, "
                f"{overdue_count} overdue cases notified, {approaching_count} approaching deadline warnings, "
                f"{pending_reminder_count} pending case reminders processed."
            )
        )

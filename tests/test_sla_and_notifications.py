from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.management import call_command
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory
from apps.notifications.models import Notification

class SLAAndNotificationTests(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.officer = User.objects.create_user(
            username='officer_sla',
            email='officer_sla@test.gov.in',
            password='TestPassword@123',
            role=User.Role.CASE_OFFICER,
            assigned_bureau=self.bureau
        )

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AICTE-SLA-TEST',
            name='SLA Institute of Engineering',
            institution_type='ENGINEERING',
            address='Ring Road',
            district='Jaipur',
            state='Rajasthan',
            region='NORTH_WEST',
            pincode='302001'
        )

        self.cat = ComplaintCategory.objects.create(code='SLA_CAT', name='SLA Test Category')

    def test_t20_overdue_case_alerts_work(self):
        """T20: Overdue cases generate an OVERDUE_ALERT notification."""
        past_date = timezone.now().date() - timedelta(days=10)
        overdue_complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-OVERDUE-01',
            institution=self.inst,
            title='Overdue Case for Inspection',
            description='Testing overdue breach detection',
            category=self.cat,
            currently_assigned_bureau=self.bureau,
            currently_assigned_officer=self.officer,
            current_status=Complaint.Status.UNDER_PROCESS,
            expected_disposal_date=past_date
        )

        call_command('check_sla_breaches')

        alert = Notification.objects.filter(
            recipient=self.officer,
            notification_type=Notification.Type.OVERDUE_ALERT,
            related_complaint=overdue_complaint
        ).first()

        self.assertIsNotNone(alert)
        self.assertIn('SLA Overdue', alert.title)

    def test_t21_repeated_scheduler_execution_does_not_generate_duplicate_notifications(self):
        """T21: Repeated check_sla_breaches executions do not spam duplicate alerts within 24 hours."""
        past_date = timezone.now().date() - timedelta(days=5)
        complaint = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-IDEM-01',
            institution=self.inst,
            title='Idempotency Test Case',
            description='Testing repeated scheduler runs',
            category=self.cat,
            currently_assigned_bureau=self.bureau,
            currently_assigned_officer=self.officer,
            current_status=Complaint.Status.UNDER_PROCESS,
            expected_disposal_date=past_date
        )

        # First run
        call_command('check_sla_breaches')
        initial_count = Notification.objects.filter(related_complaint=complaint).count()
        self.assertTrue(initial_count >= 1)

        # Second run immediately
        call_command('check_sla_breaches')
        second_count = Notification.objects.filter(related_complaint=complaint).count()

        # Count must remain strictly identical
        self.assertEqual(initial_count, second_count)

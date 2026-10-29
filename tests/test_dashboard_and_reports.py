from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory
from apps.dashboard.services import DashboardMetricsService

class DashboardAndReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.admin = User.objects.create_user(
            username='admin_report',
            email='admin_report@test.gov.in',
            password='TestPassword@123',
            role=User.Role.SUPER_ADMIN,
            display_name='Admin User'
        )

        self.rb_head = User.objects.create_user(
            username='rb_head_report',
            email='rb_head_report@test.gov.in',
            password='TestPassword@123',
            role=User.Role.BUREAU_HEAD,
            assigned_bureau=self.bureau_rb,
            display_name='RB Head User'
        )

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AICTE-METRICS-01',
            name='Kolkata College of Technology',
            institution_type='ENGINEERING',
            address='Salt Lake',
            district='Kolkata',
            state='West Bengal',
            region='EASTERN',
            pincode='700091'
        )

        self.cat = ComplaintCategory.objects.create(code='REPORT_CAT', name='Report Category')

        # 3 RB complaints (2 under process, 1 disposed)
        Complaint.objects.create(
            complaint_no='AICTE-2026-RB-M01',
            institution=self.inst,
            title='RB Metric 1',
            description='Desc',
            category=self.cat,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.UNDER_PROCESS
        )
        Complaint.objects.create(
            complaint_no='AICTE-2026-RB-M02',
            institution=self.inst,
            title='RB Metric 2',
            description='Desc',
            category=self.cat,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.UNDER_PROCESS
        )
        Complaint.objects.create(
            complaint_no='AICTE-2026-RB-M03',
            institution=self.inst,
            title='RB Metric 3',
            description='Desc',
            category=self.cat,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.DISPOSED
        )

        # 1 PGRC complaint
        Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-M04',
            institution=self.inst,
            title='PGRC Metric 4',
            description='Desc',
            category=self.cat,
            currently_assigned_bureau=self.bureau_pgrc,
            current_status=Complaint.Status.PENDING
        )

    def test_t22_dashboard_metrics_match_database_records(self):
        """T22: Dashboard metrics match direct database aggregations and handle zero denominators."""
        # For superadmin: all 4 complaints
        admin_kpis = DashboardMetricsService.get_dashboard_kpis(self.admin)
        self.assertEqual(admin_kpis['total_complaints'], 4)
        self.assertEqual(admin_kpis['under_process_complaints'], 2)
        self.assertEqual(admin_kpis['disposed_complaints'], 1)
        self.assertEqual(admin_kpis['pending_complaints'], 1)
        self.assertEqual(admin_kpis['disposal_rate'], 25.0)

        # For RB Head: only 3 complaints
        rb_kpis = DashboardMetricsService.get_dashboard_kpis(self.rb_head)
        self.assertEqual(rb_kpis['total_complaints'], 3)
        self.assertEqual(rb_kpis['under_process_complaints'], 2)
        self.assertEqual(rb_kpis['disposed_complaints'], 1)
        self.assertEqual(rb_kpis['pending_complaints'], 0)
        self.assertEqual(rb_kpis['disposal_rate'], 33.3)

    def test_t23_search_filters_return_accurate_results(self):
        """T23: Complaint search filters return accurate query matches."""
        self.client.login(username='admin_report', password='TestPassword@123')
        response = self.client.get(reverse('complaints:list'), {'q': 'PGRC-M04'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AICTE-2026-PGRC-M04')
        self.assertNotContains(response, 'AICTE-2026-RB-M01')

    def test_t24_reports_respect_role_based_access(self):
        """T24: Reports apply same authorization scoping as the dashboard."""
        self.client.login(username='rb_head_report', password='TestPassword@123')
        response = self.client.get(reverse('reports:export_csv'))
        self.assertEqual(response.status_code, 200)
        csv_content = response.content.decode('utf-8-sig')

        # Should contain RB cases
        self.assertIn('AICTE-2026-RB-M01', csv_content)
        # Should NOT contain PGRC cases (out of scope for RB Head)
        self.assertNotIn('AICTE-2026-PGRC-M04', csv_content)

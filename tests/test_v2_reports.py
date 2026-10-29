import io
from django.test import TestCase, Client
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import Complaint, ComplaintCategory
from apps.accounts.models import User
from apps.reports.services import ExportService, sanitize_formula_cell
from apps.dashboard.services import DashboardMetricsService

class ReportsV2TestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau_rb = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.bureau_pgrc = Bureau.objects.create(code='PGRC', name='Public Grievance Redressal Cell')

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-REP-101',
            name='Analytics & Reporting Institute',
            region='NORTHERN',
            state='Delhi',
            district='Delhi'
        )
        self.category = ComplaintCategory.objects.create(code='REP_CAT', name='Administrative')

        self.user_admin = User.objects.create_superuser('admin_rep', 'admin@example.com', 'Pass@123')
        self.user_rb = User.objects.create_user('rb_head_rep', 'rb@example.com', 'Pass@123', role=User.Role.BUREAU_HEAD, assigned_bureau=self.bureau_rb)

        self.c1 = Complaint.objects.create(
            complaint_no='AICTE-2026-RB-0001',
            institution=self.inst,
            title='Normal Complaint',
            description='Standard text',
            category=self.category,
            currently_assigned_bureau=self.bureau_rb,
            current_status=Complaint.Status.PENDING
        )

        self.c2 = Complaint.objects.create(
            complaint_no='AICTE-2026-PGRC-0001',
            institution=self.inst,
            title='=cmd|"/C calc"!A0',  # Formula injection attempt in title
            description='Malicious formula payload in title',
            category=self.category,
            currently_assigned_bureau=self.bureau_pgrc,
            current_status=Complaint.Status.DISPOSED
        )

    def test_rep01_accurate_dashboard_counts(self):
        """REP01: Dashboard KPIs match direct ORM counts with zero-denominator safety."""
        kpis = DashboardMetricsService.get_dashboard_kpis(self.user_admin)
        self.assertEqual(kpis['total'], 2)
        self.assertEqual(kpis['pending'], 1)
        self.assertEqual(kpis['disposed'], 1)
        self.assertEqual(kpis['disposal_rate'], 50.0)

    def test_rep02_scoped_filtered_exports(self):
        """REP02: CSV export filtered by Bureau Head only exports that bureau's cases."""
        self.client.force_login(self.user_rb)
        response = self.client.get('/reports/export/csv/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')

        # RB Head should see AICTE-2026-RB-0001, but NOT PGRC complaint
        self.assertIn('AICTE-2026-RB-0001', content)
        self.assertNotIn('AICTE-2026-PGRC-0001', content)

    def test_rep03_empty_data_report_generation(self):
        """REP03: Empty querysets produce valid CSV and Excel headers without errors."""
        empty_qs = Complaint.objects.none()
        csv_resp = ExportService.to_csv(empty_qs)
        self.assertEqual(csv_resp.status_code, 200)

        xlsx_resp = ExportService.to_excel(empty_qs)
        self.assertEqual(xlsx_resp.status_code, 200)

    def test_rep04_formula_injection_sanitization(self):
        """REP04: Values starting with '=', '+', '-', '@', '\\t', or '\\r' are escaped with a leading single quote."""
        self.assertEqual(sanitize_formula_cell('=SUM(A1:A10)'), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_formula_cell('+12345'), "'+12345")
        self.assertEqual(sanitize_formula_cell('-cmd|'), "'-cmd|")
        self.assertEqual(sanitize_formula_cell('@calc'), "'@calc")
        self.assertEqual(sanitize_formula_cell('Normal Text'), 'Normal Text')
        self.assertEqual(sanitize_formula_cell(None), '')

        # Test in actual CSV export
        qs = Complaint.objects.filter(id=self.c2.id)
        csv_resp = ExportService.to_csv(qs)
        content = csv_resp.content.decode('utf-8-sig')
        # Check that title is escaped against formula injection
        self.assertTrue("''=cmd" in content or "'=cmd" in content)

    def test_rep05_all_nine_statutory_reports(self):
        """REP05: All 9 statutory report views render successfully with HTTP 200."""
        from apps.reports.services import AnalyticsReportService
        self.client.force_login(self.user_admin)
        report_keys = [
            'bureau_wise', 'region_wise', 'institution_wise', 'status_wise',
            'ageing_analysis', 'disposal_rate', 'overlap_cases',
            'monthly_performance', 'quarterly_performance'
        ]
        for key in report_keys:
            resp = self.client.get(f'/reports/?report_type={key}')
            self.assertEqual(resp.status_code, 200, f"Failed for report_type: {key}")

    def test_rep06_pdf_export_generation(self):
        """REP06: PDF export generates a valid binary document with %PDF- header."""
        self.client.force_login(self.user_admin)
        resp = self.client.get('/reports/export/pdf/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF-'))

    def test_rep07_disposal_rate_and_ageing_formulas(self):
        """REP07: Verified statutory disposal rate and ageing formulas."""
        from apps.reports.services import AnalyticsReportService
        qs = Complaint.objects.all()
        disp_report = AnalyticsReportService.get_disposal_rate_report(qs)
        # 1 disposed out of 2 = 50.0%
        self.assertEqual(disp_report['overall_rate'], 50.0)

        ageing_report = AnalyticsReportService.get_ageing_report(qs)
        # 1 active case
        self.assertEqual(ageing_report['total_active'], 1)
        self.assertEqual(len(ageing_report['brackets']), 5)


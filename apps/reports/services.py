import csv
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from django.http import HttpResponse
from apps.complaints.models import Complaint
from apps.bureaus.models import Bureau
from apps.accounts.models import User
from apps.intelligence.models import OverlapCandidate

def sanitize_formula_cell(val):
    """
    Sanitizes cell value against CSV/Excel Formula Injection (CWE-1236).
    If a string starts with '=', '+', '-', '@', '\t', or '\r', escape with leading single quote.
    """
    if val is None:
        return ''
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s

class ExportService:
    @staticmethod
    def to_csv(queryset, filename='augis_complaints_export.csv'):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            'Complaint ID', 'Title', 'AICTE Permanent ID', 'Institution Name', 'Category',
            'Handling Bureau', 'Status', 'Priority', 'Date Received',
            'Expected Disposal', 'Assigned Officer'
        ])

        for c in queryset:
            writer.writerow([
                sanitize_formula_cell(c.complaint_no),
                sanitize_formula_cell(c.title),
                sanitize_formula_cell(c.institution.aicte_permanent_id if c.institution else ''),
                sanitize_formula_cell(c.institution.name if c.institution else ''),
                sanitize_formula_cell(c.category.name if c.category else ''),
                sanitize_formula_cell(c.currently_assigned_bureau.code if c.currently_assigned_bureau else ''),
                sanitize_formula_cell(c.get_current_status_display()),
                sanitize_formula_cell(c.get_priority_display()),
                sanitize_formula_cell(c.date_received.strftime('%Y-%m-%d') if c.date_received else ''),
                sanitize_formula_cell(c.expected_disposal_date.strftime('%Y-%m-%d') if c.expected_disposal_date else ''),
                sanitize_formula_cell(c.currently_assigned_officer.display_name if c.currently_assigned_officer else 'Unassigned')
            ])
        return response

    @staticmethod
    def to_excel(queryset, filename='augis_complaints_export.xlsx'):
        wb = Workbook()
        ws = wb.active
        ws.title = "AUGIS Complaints"

        # Headers
        headers = [
            'Complaint ID', 'Title', 'AICTE Permanent ID', 'Institution Name', 'Category',
            'Handling Bureau', 'Status', 'Priority', 'Date Received',
            'Expected Disposal', 'Assigned Officer'
        ]
        ws.append(headers)

        # Style header row
        header_fill = PatternFill(start_color="12345A", end_color="12345A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for c in queryset:
            ws.append([
                sanitize_formula_cell(c.complaint_no),
                sanitize_formula_cell(c.title),
                sanitize_formula_cell(c.institution.aicte_permanent_id if c.institution else ''),
                sanitize_formula_cell(c.institution.name if c.institution else ''),
                sanitize_formula_cell(c.category.name if c.category else ''),
                sanitize_formula_cell(c.currently_assigned_bureau.code if c.currently_assigned_bureau else ''),
                sanitize_formula_cell(c.get_current_status_display()),
                sanitize_formula_cell(c.get_priority_display()),
                sanitize_formula_cell(str(c.date_received) if c.date_received else ''),
                sanitize_formula_cell(str(c.expected_disposal_date) if c.expected_disposal_date else ''),
                sanitize_formula_cell(c.currently_assigned_officer.display_name if c.currently_assigned_officer else 'Unassigned')
            ])

        # Auto column width
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def to_pdf(queryset, title='AICTE Grievance Status Report', filename='augis_report.pdf'):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=20,
            leftMargin=20,
            topMargin=25,
            bottomMargin=25
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#12345A'),
            spaceAfter=10
        )

        elements.append(Paragraph(f"AUGIS - {title}", title_style))
        elements.append(Paragraph(f"Generated at: {queryset.model.objects.none() or ''}", styles['Normal']))
        elements.append(Spacer(1, 10))

        # Table data
        table_data = [[
            'ID', 'Permanent ID', 'Institution', 'Bureau', 'Status', 'Priority', 'Expected Date'
        ]]

        for c in queryset[:100]:  # Cap at 100 in PDF for performance
            table_data.append([
                c.complaint_no,
                c.institution.aicte_permanent_id if c.institution else '',
                (c.institution.name[:25] + '...') if (c.institution and len(c.institution.name) > 25) else (c.institution.name if c.institution else ''),
                c.currently_assigned_bureau.code if c.currently_assigned_bureau else '',
                c.get_current_status_display(),
                c.get_priority_display(),
                str(c.expected_disposal_date or 'N/A')
            ])

        table = Table(table_data, colWidths=[110, 80, 180, 60, 85, 60, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#12345A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename if filename.endswith(".pdf") else filename + ".pdf"}"'
        return response


class AnalyticsReportService:
    """
    Comprehensive Analytics & Statutory Reporting Engine for AUGIS V2.
    Implements all 9 statutory and management reports with exact mathematical definitions.
    """

    @staticmethod
    def get_bureau_report(complaints_qs):
        """1. Bureau-wise Complaint Report"""
        today = timezone.now().date()
        bureaus = Bureau.objects.filter(is_active=True).order_by('code')
        results = []
        for b in bureaus:
            b_cases = complaints_qs.filter(currently_assigned_bureau=b)
            tot = b_cases.count()
            pnd = b_cases.filter(current_status=Complaint.Status.PENDING).count()
            proc = b_cases.filter(current_status=Complaint.Status.UNDER_PROCESS).count()
            trans = b_cases.filter(current_status=Complaint.Status.TRANSFERRED).count()
            esc = b_cases.filter(current_status=Complaint.Status.ESCALATED).count()
            disp = b_cases.filter(current_status=Complaint.Status.DISPOSED).count()
            ovd = b_cases.filter(expected_disposal_date__lt=today).exclude(current_status=Complaint.Status.DISPOSED).count()
            rate = round((disp / tot * 100), 1) if tot > 0 else 0.0

            results.append({
                'bureau_code': b.code,
                'bureau_name': b.name,
                'total': tot,
                'pending': pnd,
                'under_process': proc,
                'transferred': trans,
                'escalated': esc,
                'disposed': disp,
                'overdue': ovd,
                'disposal_rate': rate,
            })
        return results

    @staticmethod
    def get_region_report(complaints_qs):
        """2. Region-wise Grievance Distribution Report"""
        today = timezone.now().date()
        region_map = dict(User.Region.choices)
        results = []
        for code, label in User.Region.choices:
            r_cases = complaints_qs.filter(institution__region=code)
            tot = r_cases.count()
            active = r_cases.exclude(current_status=Complaint.Status.DISPOSED).count()
            disp = r_cases.filter(current_status=Complaint.Status.DISPOSED).count()
            ovd = r_cases.filter(expected_disposal_date__lt=today).exclude(current_status=Complaint.Status.DISPOSED).count()
            compliance = round(((tot - ovd) / tot * 100), 1) if tot > 0 else 100.0

            results.append({
                'region_code': code,
                'region_name': label,
                'total': tot,
                'active': active,
                'disposed': disp,
                'overdue': ovd,
                'compliance_rate': compliance,
            })
        return sorted(results, key=lambda x: x['total'], reverse=True)

    @staticmethod
    def get_institution_report(complaints_qs):
        """3. Institution-wise Complaint History & High-Frequency Docket"""
        today = timezone.now().date()
        return list(
            complaints_qs.values(
                'institution__id',
                'institution__name',
                'institution__aicte_permanent_id',
                'institution__region',
                'institution__district',
                'institution__state'
            ).annotate(
                total=Count('id'),
                active=Count('id', filter=~Q(current_status=Complaint.Status.DISPOSED)),
                disposed=Count('id', filter=Q(current_status=Complaint.Status.DISPOSED)),
                overdue=Count('id', filter=Q(expected_disposal_date__lt=today) & ~Q(current_status=Complaint.Status.DISPOSED))
            ).order_by('-total')[:50]
        )

    @staticmethod
    def get_status_report(complaints_qs):
        """4. Status-wise Grievance Distribution Report"""
        tot = complaints_qs.count()
        status_data = []
        for code, label in Complaint.Status.choices:
            cnt = complaints_qs.filter(current_status=code).count()
            pct = round((cnt / tot * 100), 1) if tot > 0 else 0.0
            status_data.append({
                'code': code,
                'label': label,
                'count': cnt,
                'percentage': pct,
            })
        return {'total': tot, 'breakdown': status_data}

    @staticmethod
    def get_ageing_report(complaints_qs):
        """
        5. Pending Case Ageing Analysis
        Formula: Ageing = (Current Date - date_received) for non-disposed cases.
        Brackets: 0-15 days, 16-30 days, 31-60 days, 61-90 days, > 90 days.
        """
        today = timezone.now().date()
        active_cases = complaints_qs.exclude(current_status=Complaint.Status.DISPOSED)
        total_active = active_cases.count()

        brackets = [
            {'label': '0 – 15 Days (Fresh Intake)', 'min_days': 0, 'max_days': 15, 'badge': 'success'},
            {'label': '16 – 30 Days (Standard Scrutiny)', 'min_days': 16, 'max_days': 30, 'badge': 'info'},
            {'label': '31 – 60 Days (Approaching Critical)', 'min_days': 31, 'max_days': 60, 'badge': 'warning'},
            {'label': '61 – 90 Days (Severely Delayed)', 'min_days': 61, 'max_days': 90, 'badge': 'danger'},
            {'label': '> 90 Days (Chronic Pending)', 'min_days': 91, 'max_days': 99999, 'badge': 'dark'},
        ]

        bracket_results = []
        for b in brackets:
            min_date = today - timedelta(days=b['max_days'])
            max_date = today - timedelta(days=b['min_days'])
            cnt = active_cases.filter(date_received__gte=min_date, date_received__lte=max_date).count()
            pct = round((cnt / total_active * 100), 1) if total_active > 0 else 0.0
            bracket_results.append({
                'label': b['label'],
                'count': cnt,
                'percentage': pct,
                'badge': b['badge']
            })

        return {'total_active': total_active, 'brackets': bracket_results}

    @staticmethod
    def get_disposal_rate_report(complaints_qs):
        """
        6. Complaint Disposal Rate & Efficiency Report
        Statutory Definition: Disposal Rate (%) = (Total Disposed Cases / Total Received Cases) * 100
        """
        tot = complaints_qs.count()
        disp = complaints_qs.filter(current_status=Complaint.Status.DISPOSED).count()
        overall_rate = round((disp / tot * 100), 1) if tot > 0 else 0.0

        bureau_rates = []
        for b in Bureau.objects.filter(is_active=True).order_by('code'):
            b_tot = complaints_qs.filter(currently_assigned_bureau=b).count()
            b_disp = complaints_qs.filter(currently_assigned_bureau=b, current_status=Complaint.Status.DISPOSED).count()
            b_rate = round((b_disp / b_tot * 100), 1) if b_tot > 0 else 0.0
            bureau_rates.append({
                'bureau_code': b.code,
                'bureau_name': b.name,
                'total': b_tot,
                'disposed': b_disp,
                'rate': b_rate
            })

        return {
            'total_cases': tot,
            'total_disposed': disp,
            'overall_rate': overall_rate,
            'bureau_rates': sorted(bureau_rates, key=lambda x: x['rate'], reverse=True)
        }

    @staticmethod
    def get_overlap_report(user):
        """7. Overlapping & Duplicate Case Intelligence Report"""
        from apps.accounts.queryset_scoping import get_scoped_overlap_candidates
        candidates = get_scoped_overlap_candidates(user)
        tot = candidates.count()
        pnd = candidates.filter(review_status=OverlapCandidate.ReviewStatus.PENDING).count()
        conf = candidates.filter(review_status=OverlapCandidate.ReviewStatus.CONFIRMED).count()
        dism = candidates.filter(review_status=OverlapCandidate.ReviewStatus.DISMISSED).count()
        sep = candidates.filter(review_status=OverlapCandidate.ReviewStatus.SEPARATE_ISSUES).count()
        cross_bureau = candidates.exclude(
            first_complaint__currently_assigned_bureau_id=F('second_complaint__currently_assigned_bureau_id')
        ).count()

        top_candidates = candidates.select_related(
            'first_complaint__institution', 'second_complaint__institution',
            'first_complaint__currently_assigned_bureau', 'second_complaint__currently_assigned_bureau'
        )[:20]

        return {
            'total_pairs': tot,
            'pending': pnd,
            'confirmed': conf,
            'dismissed': dism,
            'separate': sep,
            'cross_bureau': cross_bureau,
            'top_candidates': top_candidates
        }

    @staticmethod
    def get_monthly_performance_report(complaints_qs):
        """8. Monthly Intake vs Disposal Velocity Report (12-Month Rolling)"""
        today = timezone.now().date()
        months = []
        for i in range(11, -1, -1):
            target_month = today.replace(day=1) - timedelta(days=i * 30)
            month_label = target_month.strftime('%b %Y')
            intake = complaints_qs.filter(date_received__year=target_month.year, date_received__month=target_month.month).count()
            disp = complaints_qs.filter(disposed_at__year=target_month.year, disposed_at__month=target_month.month, current_status=Complaint.Status.DISPOSED).count()
            rate = round((disp / intake * 100), 1) if intake > 0 else 0.0
            months.append({
                'month': month_label,
                'intake': intake,
                'disposed': disp,
                'net_change': intake - disp,
                'disposal_rate': rate
            })
        return months

    @staticmethod
    def get_quarterly_performance_report(complaints_qs):
        """9. Quarterly Statutory Performance Report"""
        current_year = timezone.now().year
        quarters = [
            {'quarter': f'Q1 {current_year}', 'months': [1, 2, 3], 'year': current_year},
            {'quarter': f'Q2 {current_year}', 'months': [4, 5, 6], 'year': current_year},
            {'quarter': f'Q3 {current_year}', 'months': [7, 8, 9], 'year': current_year},
            {'quarter': f'Q4 {current_year}', 'months': [10, 11, 12], 'year': current_year},
        ]
        results = []
        for q in quarters:
            intake = complaints_qs.filter(date_received__year=q['year'], date_received__month__in=q['months']).count()
            disp = complaints_qs.filter(disposed_at__year=q['year'], disposed_at__month__in=q['months'], current_status=Complaint.Status.DISPOSED).count()
            rate = round((disp / intake * 100), 1) if intake > 0 else 0.0
            results.append({
                'quarter': q['quarter'],
                'intake': intake,
                'disposed': disp,
                'net_backlog': intake - disp,
                'disposal_rate': rate
            })
        return results

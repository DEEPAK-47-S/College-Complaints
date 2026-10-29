import datetime
import json
import logging
import secrets
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import PublicEmailOTP, User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.notifications.services import NotificationService
from .models import Complaint, ComplaintCategory, ComplaintAction, ComplaintDocument
from .services import generate_complaint_number, validate_and_save_document
from apps.audit.services import log_audit_event

logger = logging.getLogger('augis.complaints.public')


def public_index_view(request):
    """Public Landing Page for College Grievances."""
    stats = {
        'total_institutions': Institution.objects.count(),
        'total_complaints': Complaint.objects.count(),
        'disposed_count': Complaint.objects.filter(current_status=Complaint.Status.DISPOSED).count(),
    }
    return render(request, 'public/index.html', {'stats': stats})


@require_http_methods(['POST'])
def send_otp_api(request):
    """
    API endpoint to dispatch a 6-digit OTP code to the citizen's Gmail / Email.
    Supports JSON body and form-encoded POST requests.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
            email = data.get('email', '').strip().lower()
        else:
            email = request.POST.get('email', '').strip().lower()
    except Exception:
        email = request.POST.get('email', '').strip().lower()

    if not email or '@' not in email:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid Gmail / Email address.'
        }, status=400)

    # Invalidate previous unused OTPs for this email
    PublicEmailOTP.objects.filter(email__iexact=email, is_used=False).update(is_used=True)

    # Generate 6-digit cryptographic OTP code
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    expires_at = timezone.now() + datetime.timedelta(minutes=10)

    PublicEmailOTP.objects.create(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at
    )

    # Dispatch email
    subject = f"Your Verification OTP for Grievance Portal: {otp_code}"
    body = (
        f"Dear Complainant / Citizen,\n\n"
        f"Your One-Time Password (OTP) for submitting a grievance on the College Grievance Portal is:\n\n"
        f"    {otp_code}\n\n"
        f"Validity: 10 minutes.\n"
        f"Please do not share this OTP with anyone.\n\n"
        f"Regards,\n"
        f"Public Grievance Redressal Cell (PGRC)\n"
        f"AICTE Unified Grievance Intelligence System (AUGIS)"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'AUGIS Grievance Portal <noreply@aicte-india.org>'),
            recipient_list=[email],
            fail_silently=True
        )
    except Exception as e:
        logger.warning(f"Public OTP email send failure: {e}")

    resp_data = {
        'success': True,
        'message': f'Verification OTP successfully sent to {email}. (Valid for 10 minutes)'
    }

    # If DEBUG is True, expose OTP in response for instant developer testing
    if settings.DEBUG:
        resp_data['otp'] = otp_code

    return JsonResponse(resp_data)


@require_http_methods(['POST'])
def verify_otp_api(request):
    """
    API endpoint to verify the 6-digit OTP code and authenticate citizen's email session.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
            email = data.get('email', '').strip().lower()
            entered_otp = data.get('otp', '').strip()
        else:
            email = request.POST.get('email', '').strip().lower()
            entered_otp = request.POST.get('otp', '').strip()
    except Exception:
        email = request.POST.get('email', '').strip().lower()
        entered_otp = request.POST.get('otp', '').strip()

    if not email or not entered_otp:
        return JsonResponse({
            'success': False,
            'message': 'Both email and 6-digit OTP code are required.'
        }, status=400)

    otp_record = PublicEmailOTP.objects.filter(
        email__iexact=email,
        is_used=False
    ).first()

    if otp_record and otp_record.is_valid and otp_record.otp_code == entered_otp:
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        # Store verified email in session
        request.session['verified_public_email'] = email
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'message': 'Email successfully verified!',
            'email': email
        })

    if otp_record:
        otp_record.attempts += 1
        otp_record.save(update_fields=['attempts'])
        if otp_record.attempts >= 5:
            return JsonResponse({
                'success': False,
                'message': 'Maximum attempts reached. Please request a new OTP code.'
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': 'Invalid or expired OTP code. Please check and try again.'
    }, status=400)


def public_submit_view(request):
    """
    Public Grievance Submission Form with Gmail OTP validation,
    institution selector, evidence upload, and unique Complaint ID generation.
    """
    institutions = Institution.objects.all().order_by('name')
    categories = ComplaintCategory.objects.filter(is_active=True).order_by('name')
    verified_email = request.session.get('verified_public_email', '')

    if request.method == 'POST':
        form_data = request.POST
        email = form_data.get('email', '').strip().lower()
        full_name = form_data.get('full_name', '').strip()
        mobile_number = form_data.get('mobile_number', '').strip()
        complainant_type = form_data.get('complainant_type', 'STUDENT')
        institution_id = form_data.get('institution', '').strip()
        other_institution_name = form_data.get('other_institution_name', '').strip()
        category_id = form_data.get('category', '').strip()
        title = form_data.get('title', '').strip()
        description = form_data.get('description', '').strip()
        issue_location = form_data.get('issue_location', '').strip()
        area = form_data.get('area', '').strip()
        priority = form_data.get('priority', 'MEDIUM')

        errors = []

        # Validate Email Verification
        session_verified = request.session.get('verified_public_email', '').strip().lower()
        if not session_verified or session_verified != email:
            errors.append('Please verify your Gmail / Email address with the 6-digit OTP code before submitting.')

        if not full_name or len(full_name) < 2:
            errors.append('Full Name is required (minimum 2 characters).')

        if not mobile_number or len(mobile_number) < 10:
            errors.append('A valid 10-digit Mobile Number is required.')

        if not category_id:
            errors.append('Please select a Grievance Category.')

        if not title or len(title) < 5:
            errors.append('Complaint Title is required (minimum 5 characters).')

        if not description or len(description) < 10:
            errors.append('Detailed Description is required (minimum 10 characters).')

        if not issue_location:
            errors.append('Campus / Location detail is required.')

        if not area:
            errors.append('Area / City / District is required.')

        category = ComplaintCategory.objects.filter(id=category_id).first() if category_id else None
        if not category:
            errors.append('Please select a valid grievance category.')

        # Institution resolution
        target_institution = None
        if institution_id == 'OTHER':
            clean_other = other_institution_name or 'Unlisted Institution / College'
            target_institution, _ = Institution.objects.get_or_create(
                aicte_permanent_id='GEN-OTHER',
                defaults={
                    'name': clean_other,
                    'normalized_name': clean_other.lower(),
                    'institution_type': Institution.InstitutionType.OTHER,
                    'address': issue_location or area or 'India',
                    'district': area or 'General',
                    'state': 'General',
                    'region': User.Region.CENTRAL,
                    'pincode': '000000'
                }
            )
        elif institution_id:
            target_institution = Institution.objects.filter(id=institution_id).first()

        if not target_institution:
            errors.append('Please select target college or institution.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'public/submit.html', {
                'institutions': institutions,
                'categories': categories,
                'form_data': form_data,
                'verified_email': session_verified,
            })

        # Resolve Default Bureau: PGRC (Public Grievance Redressal Cell) or first bureau
        bureau = Bureau.objects.filter(code='PGRC').first() or Bureau.objects.first()

        try:
            # Generate atomic sequential human-readable complaint ID (AICTE-2026-PGRC-XXXXX)
            complaint_no = generate_complaint_number(bureau.code)

            # Calculate SLA
            sla_days = category.default_sla_days if category else 30
            expected_disposal = timezone.now().date() + datetime.timedelta(days=sla_days)

            # Create Complaint Record
            complaint = Complaint.objects.create(
                complaint_no=complaint_no,
                institution=target_institution,
                title=title,
                description=description,
                category=category,
                source_channel=Complaint.SourceChannel.PORTAL,
                date_received=timezone.now().date(),
                current_status=Complaint.Status.PENDING,
                priority=priority,
                currently_assigned_bureau=bureau,
                expected_disposal_date=expected_disposal,
                complainant_name=full_name,
                complainant_email=email,
                complainant_phone=mobile_number,
                complainant_type=complainant_type,
                issue_location=issue_location,
                area=area,
                is_email_verified=True,
                created_by=None
            )

            # Record initial ComplaintAction
            ComplaintAction.objects.create(
                complaint=complaint,
                action_type=ComplaintAction.ActionType.CREATED,
                previous_status='',
                new_status=Complaint.Status.PENDING,
                responsible_officer=None,
                responsible_bureau=bureau,
                remarks=f"Grievance registered via Online Public Portal by {full_name} ({email}) with verified Gmail OTP."
            )

            # Handle Evidence Uploads
            files = request.FILES.getlist('evidence')
            for f in files:
                try:
                    validate_and_save_document(
                        complaint=complaint,
                        file_obj=f,
                        user=None,
                        classification=ComplaintDocument.Classification.PUBLIC_SUMMARY
                    )
                except Exception as file_err:
                    logger.warning(f"File upload warning for {f.name}: {file_err}")

            # Notify all active case officers and bureau heads
            try:
                NotificationService.notify_officers_new_public_complaint(complaint)
            except Exception as notif_err:
                logger.warning(f"Officer notification dispatch skipped: {notif_err}")

            # Trigger non-blocking AI overlap / duplicate detection
            try:
                from apps.intelligence.services import OverlapDetectionService
                OverlapDetectionService.detect_overlaps_for_complaint(complaint)
            except Exception as e:
                logger.warning(f"Overlap detection skipped: {e}")

            # Audit log
            log_audit_event(
                actor=None,
                event_type="PUBLIC_GRIEVANCE_REGISTERED",
                entity_name="Complaint",
                entity_id=str(complaint.id),
                change_summary={
                    "complaint_no": complaint.complaint_no,
                    "institution": target_institution.name,
                    "complainant": full_name,
                    "email": email
                },
                request=request
            )

            # Clear session verified email
            request.session.pop('verified_public_email', None)

            messages.success(request, f"Your grievance has been successfully submitted! Complaint ID: {complaint.complaint_no}")
            return redirect('public:success', complaint_no=complaint.complaint_no)

        except Exception as e:
            logger.exception("Error saving public complaint")
            messages.error(request, f"An error occurred while registering your complaint: {e}")
            return render(request, 'public/submit.html', {
                'institutions': institutions,
                'categories': categories,
                'form_data': form_data,
                'verified_email': session_verified,
            })

    return render(request, 'public/submit.html', {
        'institutions': institutions,
        'categories': categories,
        'form_data': {},
        'verified_email': verified_email,
    })


def public_success_view(request, complaint_no):
    """Success confirmation page displaying generated Complaint ID with copy & tracking links."""
    complaint = Complaint.objects.filter(complaint_no=complaint_no).first()
    if not complaint:
        messages.error(request, "Invalid or non-existent complaint reference ID.")
        return redirect('public:index')

    return render(request, 'public/success.html', {'complaint': complaint})


def public_track_view(request):
    """Search / Track Complaint Status page."""
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id', '').strip().upper()
        if complaint_id:
            return redirect('public:detail', complaint_no=complaint_id)
        messages.warning(request, "Please enter your Complaint ID to track status.")

    return render(request, 'public/track.html')


def public_detail_view(request, complaint_no):
    """
    Public Status & Visual Timeline Page for a given Complaint ID.
    Shows current status badge, target institution, latest officer response, and chronological timeline.
    """
    clean_no = complaint_no.strip().upper()
    complaint = Complaint.objects.filter(complaint_no__iexact=clean_no).first()

    if not complaint:
        messages.error(
            request,
            f"Complaint ID '{complaint_no}' was not found. Please verify your ID and try again."
        )
        return redirect('public:track')

    # Fetch chronological actions for timeline
    actions = complaint.actions.all().order_by('-timestamp')

    # Extract latest officer response or remark
    latest_response = ""
    for action in actions:
        if action.remarks and "Grievance registered via Online Public Portal" not in action.remarks:
            latest_response = action.remarks
            break

    return render(request, 'public/detail.html', {
        'complaint': complaint,
        'actions': actions,
        'latest_response': latest_response,
    })

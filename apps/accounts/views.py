import datetime
import logging
import secrets
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, ProfileForm, PasswordChangeForm
from .models import User, EmailOTP
from apps.audit.services import log_audit_event

logger = logging.getLogger('augis.security')

def send_user_otp(user, request):
    """Generates a secure 6-digit cryptographic OTP and dispatches it via email."""
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    expires_at = timezone.now() + datetime.timedelta(minutes=10)

    # Invalidate any existing unused OTPs
    EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    # Create active OTP record
    EmailOTP.objects.create(
        user=user,
        otp_code=otp_code,
        expires_at=expires_at
    )

    # Dispatch email
    subject = f"AUGIS Two-Factor Authentication: Your 6-Digit OTP is {otp_code}"
    body = (
        f"Dear {user.display_name},\n\n"
        f"Your One-Time Password (OTP) for accessing the AICTE Unified Grievance Intelligence System (AUGIS) is:\n\n"
        f"    {otp_code}\n\n"
        f"Designated Role: {user.get_role_display()}\n"
        f"Validity: 10 minutes\n\n"
        f"If you did not initiate this authentication request, please immediately contact the AICTE National Command Center.\n\n"
        f"Regards,\n"
        f"AICTE Information Security Cell"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
    except Exception as e:
        logger.warning(f"Email dispatch warning: {e}")

    return otp_code

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            
            # Check if 2FA is active
            if getattr(settings, 'AUTH_2FA_ENABLED', True):
                otp_code = send_user_otp(user, request)
                request.session['pre_auth_user_id'] = str(user.id)
                request.session['pre_auth_next'] = request.GET.get('next') or 'dashboard:index'
                
                messages.info(
                    request,
                    f"Two-factor OTP dispatched to {user.email}. (Testing Code: {otp_code})"
                )
                return redirect('accounts:verify_otp')
            else:
                # Direct login if 2FA is explicitly disabled
                login(request, user)
                log_audit_event(
                    actor=user,
                    event_type="LOGIN_SUCCESS",
                    entity_name="User",
                    entity_id=str(user.id),
                    change_summary={"username": user.username, "role": user.role},
                    request=request
                )
                messages.success(request, f"Welcome back, {user.display_name}!")
                next_url = request.GET.get('next') or 'dashboard:index'
                return redirect(next_url)
        else:
            log_audit_event(
                actor=None,
                event_type="LOGIN_FAILED",
                entity_name="User",
                entity_id=request.POST.get('username', 'unknown'),
                change_summary={"attempted_username": request.POST.get('username')},
                request=request
            )
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, 'accounts/login.html', {'form': form})

def verify_otp_view(request):
    """Validates the 6-digit OTP code before completing session authentication."""
    user_id = request.session.get('pre_auth_user_id')
    if not user_id:
        return redirect('accounts:login')

    user = User.objects.filter(id=user_id, is_active=True).first()
    if not user:
        return redirect('accounts:login')

    if request.method == 'POST':
        entered_otp = (request.POST.get('otp') or request.POST.get('otp_code') or '').strip()
        active_otp = EmailOTP.objects.filter(user=user, is_used=False).first()

        if active_otp and active_otp.is_valid and active_otp.otp_code == entered_otp:
            active_otp.is_used = True
            active_otp.save(update_fields=['is_used'])

            # Log user in
            login(request, user)

            next_url = request.session.pop('pre_auth_next', 'dashboard:index')
            request.session.pop('pre_auth_user_id', None)

            log_audit_event(
                actor=user,
                event_type="LOGIN_SUCCESS_2FA",
                entity_name="User",
                entity_id=str(user.id),
                change_summary={"username": user.username, "role": user.role, "2fa": "VERIFIED"},
                request=request
            )
            messages.success(request, f"Two-Factor Authentication verified. Welcome, {user.display_name}!")
            return redirect(next_url)
        else:
            if active_otp:
                active_otp.attempts += 1
                active_otp.save(update_fields=['attempts'])
            log_audit_event(
                actor=user,
                event_type="LOGIN_FAILED_2FA",
                entity_name="User",
                entity_id=str(user.id),
                change_summary={"username": user.username, "attempted_otp": entered_otp},
                request=request
            )
            messages.error(request, "Invalid or expired verification code. Please check your email or request a new code.")

    # Mask email for display: r***@aicte-india.org
    parts = user.email.split('@')
    masked_email = f"{parts[0][0]}***@{parts[1]}" if len(parts) == 2 else user.email

    return render(request, 'accounts/verify_otp.html', {
        'masked_email': masked_email,
        'user_name': user.display_name,
        'user_role': user.get_role_display()
    })

def resend_otp_view(request):
    """Regenerates and resends a fresh 6-digit OTP code."""
    user_id = request.session.get('pre_auth_user_id')
    if not user_id:
        return redirect('accounts:login')

    user = User.objects.filter(id=user_id, is_active=True).first()
    if user:
        otp_code = send_user_otp(user, request)
        messages.success(
            request,
            f"A fresh 6-digit OTP code has been re-sent to {user.email}. (Testing Code: {otp_code})"
        )

    return redirect('accounts:verify_otp')

@require_http_methods(["GET", "POST"])
def logout_view(request):
    if request.user.is_authenticated:
        user = request.user
        log_audit_event(
            actor=user,
            event_type="LOGOUT",
            entity_name="User",
            entity_id=str(user.id),
            change_summary={"username": user.username},
            request=request
        )
        logout(request)
        messages.info(request, "You have been logged out securely.")
    return redirect('accounts:login')

@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            log_audit_event(
                actor=request.user,
                event_type="PROFILE_UPDATE",
                entity_name="User",
                entity_id=str(request.user.id),
                change_summary={"display_name": request.user.display_name, "email": request.user.email},
                request=request
            )
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors in the profile form.")

    return render(request, 'accounts/profile.html', {
        'form': form,
        'user': request.user
    })

@login_required
def password_change_view(request):
    form = PasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_audit_event(
                actor=user,
                event_type="PASSWORD_CHANGE",
                entity_name="User",
                entity_id=str(user.id),
                change_summary={},
                request=request
            )
            messages.success(request, "Your password was changed successfully!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'accounts/password_change.html', {'form': form})

def access_denied_view(request, exception=None):
    return render(request, 'accounts/access_denied.html', status=403)

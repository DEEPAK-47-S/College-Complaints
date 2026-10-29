from .models import AuditEvent

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def log_audit_event(actor, event_type, entity_name, entity_id, change_summary=None, request=None):
    """
    Safely creates an immutable audit event without throwing exceptions that break business workflows.
    Never logs passwords or authorization tokens.
    """
    try:
        actor_username = 'SYSTEM'
        actor_user = None
        if actor and getattr(actor, 'is_authenticated', False):
            actor_user = actor
            actor_username = getattr(actor, 'username', 'UNKNOWN')

        correlation_id = getattr(request, 'correlation_id', '') if request else ''
        ip_addr = get_client_ip(request)

        safe_summary = {}
        if change_summary:
            for k, v in change_summary.items():
                if any(secret_key in k.lower() for secret_key in ['password', 'token', 'secret', 'key']):
                    safe_summary[k] = '[REDACTED]'
                else:
                    safe_summary[k] = str(v)

        return AuditEvent.objects.create(
            actor=actor_user,
            actor_username=actor_username,
            event_type=event_type,
            entity_type=entity_name,
            entity_id=str(entity_id),
            change_summary=safe_summary,
            request_correlation_id=correlation_id,
            ip_address=ip_addr
        )
    except Exception as e:
        # Avoid crashing primary transaction if audit writing encounters an issue
        import logging
        logging.getLogger('augis.audit').error(f"Failed to record audit event: {e}")
        return None

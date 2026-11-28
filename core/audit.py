from .models import AuditLog


def request_ip(request):
    """IP del cliente, confiando en el proxy solo si está configurado."""
    if not request:
        return None
    from django.conf import settings
    if getattr(settings, 'TRUST_PROXY_HEADERS', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR')


def record_audit(request, action, entity, entity_id, before=None, after=None,
                 *, actor=None, module='', outcome='success'):
    """Registra snapshots ya minimizados por el llamador.

    ``actor`` permite registrar eventos de autenticación donde
    ``request.user`` todavía es anónimo.
    """
    if actor is None and request is not None:
        candidate = getattr(request, 'user', None)
        actor = candidate if getattr(candidate, 'pk', None) else None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        module=module or entity,
        request_id=getattr(request, 'request_id', '') if request else '',
        outcome=outcome,
        user_agent=(request.META.get('HTTP_USER_AGENT', '') if request else '')[:255],
        before=before or {},
        after=after or {},
        ip=request_ip(request),
    )

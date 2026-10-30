from .models import AuditLog


def request_ip(request):
    """Obtiene la IP directa; no confía en X-Forwarded-For sin proxy confiable."""
    return request.META.get('REMOTE_ADDR') if request else None


def record_audit(request, action, entity, entity_id, before=None, after=None):
    """Registra únicamente snapshots ya minimizados por el llamador."""
    return AuditLog.objects.create(
        actor=getattr(request, 'user', None) if request else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        before=before or {},
        after=after or {},
        ip=request_ip(request),
    )

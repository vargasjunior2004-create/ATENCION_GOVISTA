from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Atencion, AtencionAccion, AtencionCatalogo


CATALOG_TYPES = ('attention_type', 'classification', 'channel', 'support_action')


def validate_catalog_type(catalog_type):
    if catalog_type not in CATALOG_TYPES:
        raise ValidationError({'catalog_type': 'Tipo de catálogo no válido.'})


def validate_catalog_entry(entry, expected_type):
    if entry.catalog_type != expected_type or not entry.active:
        raise ValidationError(
            f'El registro seleccionado no pertenece al catálogo {expected_type}.')


def start_attention(attention):
    if attention.status != 'open':
        raise ValidationError('Solo se puede iniciar una atención abierta.')
    if attention.started_at:
        raise ValidationError('La atención ya fue iniciada.')
    attention.started_at = timezone.now()
    attention.save(update_fields=['started_at', 'updated_at'])
    return attention


def finish_attention(attention):
    if attention.status != 'open':
        raise ValidationError('Solo se puede finalizar una atención abierta.')
    if not attention.started_at:
        raise ValidationError('La atención debe iniciarse antes de finalizarla.')
    ended_at = timezone.now()
    attention.ended_at = ended_at
    attention.duration_seconds = max(
        0, int((ended_at - attention.started_at).total_seconds()))
    attention.status = 'finished'
    attention.save(update_fields=[
        'ended_at', 'duration_seconds', 'status', 'updated_at'])
    return attention


@transaction.atomic
def add_attention_action(attention, action, user, notes=''):
    validate_catalog_entry(action, 'support_action')
    relation, created = AtencionAccion.objects.get_or_create(
        atencion=attention,
        action=action,
        defaults={'executed_by': user, 'notes': notes.strip()},
    )
    if not created:
        raise ValidationError({'action': 'La acción ya fue registrada en esta atención.'})
    return relation


def duration_as_timedelta(seconds):
    return timedelta(seconds=seconds or 0)

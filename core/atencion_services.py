from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Atencion, AtencionAccion, AtencionCatalogo, AtencionIdempotencyKey,
)


CATALOG_TYPES = ('attention_type', 'classification', 'channel', 'support_action')
CALL_CENTER_CHANNELS = {'mensaje', 'llamada'}


def validate_catalog_type(catalog_type):
    if catalog_type not in CATALOG_TYPES:
        raise ValidationError({'catalog_type': 'Tipo de catálogo no válido.'})


def validate_catalog_entry(entry, expected_type):
    if entry.catalog_type != expected_type or not entry.active:
        raise ValidationError(
            f'El registro seleccionado no pertenece al catálogo {expected_type}.')


def validate_call_center_channel(channel, user):
    if getattr(user, 'role', None) == 'call-center' and channel.code not in CALL_CENTER_CHANNELS:
        raise ValidationError(
            {'channel': 'Call Center solo puede utilizar Mensajes o Llamadas.'})


def get_open_attention(user, *, lock=False, exclude_id=None):
    queryset = Atencion.objects.filter(agent=user, status='open')
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    if lock:
        queryset = queryset.select_for_update()
    return queryset.order_by('-started_at', '-created_at').first()


@transaction.atomic
def create_started_attention(serializer, user, idempotency_key):
    existing_key = AtencionIdempotencyKey.objects.filter(
        user=user, key=idempotency_key).select_related('atencion').first()
    if existing_key:
        return existing_key.atencion, False

    if get_open_attention(user, lock=True):
        raise ValidationError(
            {'attention': 'El agente ya tiene una atención abierta.'})

    attention = serializer.save(
        registered_by=user,
        agent=user,
        started_at=timezone.now(),
        status='open',
    )
    try:
        with transaction.atomic():
            AtencionIdempotencyKey.objects.create(
                user=user, key=idempotency_key, atencion=attention)
    except IntegrityError:
        existing_key = AtencionIdempotencyKey.objects.select_related(
            'atencion').get(user=user, key=idempotency_key)
        return existing_key.atencion, False
    return attention, True


def start_attention(attention):
    with transaction.atomic():
        attention = Atencion.objects.select_for_update().get(pk=attention.pk)
        if attention.status != 'open':
            raise ValidationError('Solo se puede iniciar una atención abierta.')
        if attention.started_at:
            raise ValidationError('La atención ya fue iniciada.')
        if get_open_attention(
                attention.agent, lock=True, exclude_id=attention.pk):
            raise ValidationError(
                {'attention': 'El agente ya tiene una atención abierta.'})
        attention.started_at = timezone.now()
        attention.save(update_fields=['started_at', 'updated_at'])
        return attention


def finish_attention(attention):
    with transaction.atomic():
        attention = Atencion.objects.select_for_update().get(pk=attention.pk)
        if attention.status != 'open':
            raise ValidationError('Solo se puede finalizar una atención abierta.')
        if not attention.started_at:
            raise ValidationError('La atención debe iniciarse antes de finalizarla.')
        ended_at = timezone.now()
        duration_seconds = int((ended_at - attention.started_at).total_seconds())
        if duration_seconds < 0:
            raise ValidationError(
                {'ended_at': 'La finalización no puede ser anterior al inicio.'})
        attention.ended_at = ended_at
        attention.duration_seconds = duration_seconds
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

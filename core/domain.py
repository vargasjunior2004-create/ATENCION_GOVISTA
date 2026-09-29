"""Reglas del dominio de servicios de GO VISTA.

Este modulo es la unica fuente de verdad para el mapeo entre el tipo de
servicio (5 valores, granular) y el tipo de plan (3 valores, familiar).
Antes el mapeo estaba duplicado en reports.py, serializers.py, SaleForm.js
y SalesList.js, y cualquier ajuste habia que aplicarlo en cuatro lugares.
"""

# Tipo de servicio: 5 valores. Es lo que se registra en cada movimiento.
SERVICE_TYPE_LABELS = {
    'internet': 'INTERNET',
    'tv': 'TV ANALOGA',
    'tv_digital': 'TV DIGITAL',
    'combo_analog': 'INTERNET + TV ANALOGA',
    'combo_digital': 'INTERNET + TV DIGITAL',
}

# Familia de servicio a la que pertenece cada tipo. El catalogo de planes
# solo distingue tres familias, asi que un plan no puede decir si su combo
# es analogico o digital: eso solo vive en el tipo de servicio del movimiento.
SERVICE_TYPE_FAMILY = {
    'internet': 'internet',
    'tv': 'tv',
    'tv_digital': 'tv',
    'combo_analog': 'combo',
    'combo_digital': 'combo',
}

SERVICE_FAMILY_LABELS = {
    'internet': 'INTERNET',
    'tv': 'TV',
    'combo': 'COMBO',
}

# Servicio -> tipo de plan que ese servicio puede contratar.
SERVICE_TYPE_TO_PLAN_TYPE = {
    'internet': 'internet',
    'tv': 'tv',
    'tv_digital': 'tv',
    'combo_analog': 'combo',
    'combo_digital': 'combo',
}

REQUEST_TYPE_LABELS = {
    'nuevo_contrato': 'NUEVO CONTRATO',
    'cambio_plan': 'CAMBIO DE PLAN',
    'recontratacion': 'RECONTRATACION',
    'retiro': 'RETIRO',
    'adicion': 'ADICION',
    'otro': 'OTRO',
}

ADDITION_TYPE_LABELS = {
    'adicion_internet': 'ADICION INTERNET',
    'adicion_tv': 'ADICION TV',
}


def service_type_to_plan_type(service_type):
    """Tipo de plan que corresponde a un tipo de servicio, o None."""
    return SERVICE_TYPE_TO_PLAN_TYPE.get(service_type)


def service_family_label(family):
    return SERVICE_FAMILY_LABELS.get(family, family or '')


def previous_service_family(sale):
    """Familia del servicio anterior de un movimiento.

    Se toma de serviceTypeFrom cuando el operador lo registro. En los
    movimientos anteriores a esa columna, y en los que quedaron sin valor,
    se deduce del plan anterior, que siempre estuvo almacenado como FK.
    """
    if sale.serviceTypeFrom:
        return SERVICE_TYPE_FAMILY.get(sale.serviceTypeFrom)
    if sale.planFromId:
        return sale.planFromId.type
    return None


def is_service_change(sale):
    """True si el movimiento cambia de familia de servicio (Combo -> Internet)."""
    if sale.requestType != 'cambio_plan':
        return False
    previous = previous_service_family(sale)
    current = SERVICE_TYPE_FAMILY.get(sale.serviceType)
    return bool(previous and current and previous != current)


def sale_service_label(sale):
    """Texto de la columna SERVICIO.

    En un cambio de plan se muestra laconversion como 'COMBO -> INTERNET'.
    En el resto de movimientos no se toca nada, para no alterar la
    apariencia de los reportes que ya usa la operacion.
    """
    if sale.requestType == 'cambio_plan':
        previous = previous_service_family(sale)
        current = SERVICE_TYPE_FAMILY.get(sale.serviceType)
        if previous and current:
            return f'{service_family_label(previous)} → {service_family_label(current)}'
    return SERVICE_TYPE_LABELS.get(sale.serviceType, sale.serviceType or '')

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

# ------------------------------------------------------------------
# Tipos de solicitud
#
# El catalogo vive en la tabla TipoSolicitud, no aqui. Lo que este
# modulo fija es el significado de cada MODO, que es lo que decide el
# cobro: un tipo nuevo no elige sus reglas, elige un modo de esta lista.
#
# Los literales se repiten aqui a proposito. domain.py no importa models
# para poder cargarse sin el app registry (migraciones, imports tardios).
# Si se agrega un modo, sale una migracion.
MODO_NUEVO = 'nuevo'
MODO_RETIRO = 'retiro'
MODO_CAMBIO_PLAN = 'cambio_plan'
MODO_ADICION = 'adicion'
MODO_SIMPLE = 'simple'

# El cliente ya tiene el servicio instalado: no se cobra instalacion.
MODOS_SOLO_MENSUAL = (MODO_RETIRO, MODO_ADICION, MODO_CAMBIO_PLAN)
# Cuentan como instalacion en el dashboard.
MODOS_INSTALACION = (MODO_NUEVO,)


def request_type_catalog():
    """Todos los tipos de solicitud como {code: TipoSolicitud}.

    Una sola consulta. Los llamadores que recorren muchas ventas la
    generan una vez y la pasan por parametro, para no repetirla por fila.
    """
    from .models import TipoSolicitud

    return {tipo.code: tipo for tipo in TipoSolicitud.objects.all()}


def request_type_mode(code, catalog=None):
    """Modo de un tipo de solicitud.

    Un code que no esta en el catalogo cae en SIMPLE, o sea sin reglas
    especiales. No deberia ocurrir: la migracion siembra los tipos que ya
    usaban ventas y el borrado esta bloqueado si hay movimientos, asi
    que solo un alta con un code duplicado llegaria aqui.
    """
    if catalog is None:
        catalog = request_type_catalog()
    tipo = catalog.get(code)
    return tipo.modo if tipo is not None else MODO_SIMPLE


def request_type_label(code, catalog=None):
    """Nombre visible del tipo, en mayusculas como los reportes."""
    if catalog is None:
        catalog = request_type_catalog()
    tipo = catalog.get(code)
    if tipo is not None:
        return (tipo.nombre or '').upper()
    return code or ''


def codes_with_modes(modes, catalog=None):
    """Codigos de los tipos cuyo modo esta en modes."""
    if catalog is None:
        catalog = request_type_catalog()
    return [code for code, tipo in catalog.items() if tipo.modo in modes]


def sale_request_mode(sale, catalog=None):
    return request_type_mode(sale.requestType, catalog)

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


def is_service_change(sale, catalog=None):
    """True si el movimiento cambia de familia de servicio (Combo -> Internet)."""
    if request_type_mode(sale.requestType, catalog) != MODO_CAMBIO_PLAN:
        return False
    previous = previous_service_family(sale)
    current = SERVICE_TYPE_FAMILY.get(sale.serviceType)
    return bool(previous and current and previous != current)


def sale_service_label(sale, catalog=None):
    """Texto de la columna SERVICIO.

    En un cambio de plan se muestra laconversion como 'COMBO -> INTERNET'.
    En el resto de movimientos no se toca nada, para no alterar la
    apariencia de los reportes que ya usa la operacion.
    """
    if request_type_mode(sale.requestType, catalog) == MODO_CAMBIO_PLAN:
        previous = previous_service_family(sale)
        current = SERVICE_TYPE_FAMILY.get(sale.serviceType)
        if previous and current:
            return f'{service_family_label(previous)} → {service_family_label(current)}'
    return SERVICE_TYPE_LABELS.get(sale.serviceType, sale.serviceType or '')

# Reportes públicos y privacidad — Fase 3

## Modelo de protección

- Los enlaces son firmados con `django.core.signing` y salt contienen todos
  los filtros autorizados: fechas, tipo de solicitud, servicio, servicio
  anterior, motivos, formato, usuario emisor, identificador y expiración.
- La validez máxima es de una hora.
- Los parámetros enviados al endpoint público no modifican los filtros del
  token.
- Un token PDF no puede usarse en el endpoint XLSX, ni al revés.
- Las descargas llevan `Cache-Control: no-store`, `X-Robots-Tag: noindex,
  nofollow` y `Referrer-Policy: no-referrer`.
- Los reportes públicos enmascaran kardex, nombre del cliente y operador. Los
  reportes autenticados conservan sus columnas operativas.
- Emisión y descarga tienen límites de 10 y 30 solicitudes por hora,
  respectivamente, usando el throttling de DRF.

## Decisiones y límites

Los enlaces públicos no tienen todavía registro de uso único en base de datos;
la protección actual depende de la firma, expiración y throttling. La emisión
queda restringida al rol administrador. Para datos más sensibles debe usarse
la descarga autenticada, no un enlace público.

## Respuesta ante incidentes

Si un enlace se comparte accidentalmente, se puede invalidar rotando la
`DJANGO_SECRET_KEY`, lo que invalida todas las sesiones y enlaces firmados.
No se registran tokens ni payloads de ventas en logs.

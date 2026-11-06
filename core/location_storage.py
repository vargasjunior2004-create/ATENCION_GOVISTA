"""Almacenamiento privado de fotografías de ubicaciones en Supabase."""
import io
import os
import uuid

from django.conf import settings
from PIL import Image, UnidentifiedImageError


MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def optimize_photo(uploaded):
    """Valida y normaliza imágenes a JPEG, manteniendo el límite de 5 MB."""
    if uploaded.size > MAX_PHOTO_BYTES:
        raise ValueError('La fotografía supera el máximo permitido de 5 MB')
    if uploaded.content_type not in ALLOWED_TYPES:
        raise ValueError('Formato no permitido. Usa JPG, JPEG, PNG o WebP')
    try:
        image = Image.open(uploaded)
        image.verify()
        uploaded.seek(0)
        image = Image.open(uploaded).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError('El archivo no es una imagen válida')

    # La compresión también normaliza PNG/WebP y elimina metadatos EXIF.
    output = io.BytesIO()
    quality = 88
    image.save(output, format='JPEG', quality=quality, optimize=True)
    while output.tell() > MAX_PHOTO_BYTES and quality > 45:
        quality -= 8
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
    if output.tell() > MAX_PHOTO_BYTES:
        raise ValueError('No fue posible optimizar la fotografía por debajo de 5 MB')
    return output.getvalue(), 'image/jpeg'


def _client():
    url = getattr(settings, 'SUPABASE_URL', '')
    key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        raise RuntimeError('El almacenamiento de fotografías no está configurado')
    from supabase import create_client
    return create_client(url, key)


def upload_photo(content, content_type, customer_id):
    path = f'customers/{customer_id}/{uuid.uuid4().hex}.jpg'
    _client().storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        path, content, {'content-type': content_type, 'upsert': 'false'})
    return path


def signed_url(path, expires=300):
    if not path:
        return ''
    result = _client().storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(path, expires)
    return result.get('signedURL') or result.get('signedUrl') or ''

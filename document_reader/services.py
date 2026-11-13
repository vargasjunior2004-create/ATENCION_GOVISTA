import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance


MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 25
ALLOWED_IMAGES = {'.jpg', '.jpeg', '.png', '.webp'}


class DocumentReaderError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.status = status


@contextmanager
def temporary_upload(uploaded):
    suffix = Path(getattr(uploaded, 'name', '') or '').suffix.lower()
    if suffix != '.pdf' and suffix not in ALLOWED_IMAGES:
        raise DocumentReaderError('unsupported_format', 'Formato no permitido.')
    with tempfile.TemporaryDirectory(prefix='govista_sotv_') as directory:
        path = Path(directory) / f'document{suffix}'
        size = 0
        with path.open('wb') as target:
            for chunk in uploaded.chunks():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise DocumentReaderError(
                        'file_too_large', 'El archivo supera el máximo de 10 MB.', 413)
                target.write(chunk)
        if size == 0:
            raise DocumentReaderError('empty_file', 'El archivo está vacío.')
        yield path


def _prepare_image(image):
    image = ImageOps.exif_transpose(image).convert('L')
    if max(image.size) < 2400:
        image = image.resize(
            (image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    return ImageEnhance.Sharpness(image).enhance(1.4)


def _ocr(image):
    prepared = _prepare_image(image)
    thresholded = prepared.point(lambda pixel: 255 if pixel > 170 else 0)
    try:
        variants = [prepared, thresholded]
        candidates = []
        for variant in variants:
            for psm in (6, 11):
                text = pytesseract.image_to_string(
                    variant, lang='spa+eng', config=f'--psm {psm}', timeout=5)
                normalized = text.casefold()
                score = sum(term in normalized for term in (
                    'contrato', 'nombre', 'fecha', 'retiro', 'placa'))
                if 'retiro' in normalized and 'aparato' in normalized:
                    score += 3
                candidates.append((score, len(text), text))
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    except pytesseract.TesseractNotFoundError as exc:
        raise DocumentReaderError(
            'ocr_unavailable', 'El motor OCR no está disponible.', 503) from exc
    except RuntimeError as exc:
        raise DocumentReaderError(
            'ocr_timeout', 'El procesamiento OCR superó el tiempo permitido.', 504) from exc
    finally:
        thresholded.close()
        prepared.close()


def _extract_text(path):
    if path.suffix.lower() in ALLOWED_IMAGES:
        try:
            with Image.open(path) as image:
                return _ocr(image), 'image_ocr', 1
        except OSError as exc:
            raise DocumentReaderError('invalid_image', 'La imagen no es válida.') from exc

    if path.read_bytes()[:5] != b'%PDF-':
        raise DocumentReaderError('invalid_pdf', 'El archivo no tiene una firma PDF válida.')
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise DocumentReaderError('malformed_pdf', 'No fue posible abrir el PDF.', 422) from exc
    try:
        if document.is_encrypted:
            raise DocumentReaderError('encrypted_pdf', 'El PDF está cifrado.', 422)
        if not document.page_count or document.page_count > MAX_PAGES:
            raise DocumentReaderError('page_limit', 'El PDF no cumple el límite de páginas.', 413)
        digital = [page.get_text('text') for page in document]
        if any(text.strip() for text in digital):
            return '\n'.join(digital), 'digital_pdf', document.page_count
        pages = []
        for page in document:
            pixmap = page.get_pixmap(dpi=200, alpha=False)
            image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            try:
                pages.append(_ocr(image))
            finally:
                image.close()
        return '\n'.join(pages), 'scanned_pdf_ocr', document.page_count
    finally:
        document.close()


def _value(text, label):
    lines = text.replace('\r', '').split('\n')
    pattern = re.compile(rf'^\s*{label}\s*:?[ \t]*(.*)$', re.IGNORECASE)
    known_labels = re.compile(
        r'^\s*(contrato|nombre|fecha|placa|telefono|celular|direccion|barrio|'
        r'provincia|cto|latitud|longitud|observaciones|referencia)\b',
        re.IGNORECASE)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if value:
            return value
        if index + 1 < len(lines) and not known_labels.match(lines[index + 1]):
            return lines[index + 1].strip() or None
    return None


def _date(value):
    if not value:
        return None
    value = value.strip().replace('.', '')
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    months = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
    match = re.fullmatch(r'(\d{1,2})-([a-záéíóú]+)-(\d{4})', value.lower())
    if match and match.group(2)[:3] in months:
        return datetime(int(match.group(3)), months[match.group(2)[:3]],
                        int(match.group(1))).date().isoformat()
    return None


def extract_retirement(uploaded):
    with temporary_upload(uploaded) as path:
        text, source, page_count = _extract_text(path)
    serial_match = re.search(
        r'(?i)retiro\s+de\s+aparato\s*\(?\s*([A-Z0-9][A-Z0-9-]{4,})', text)
    data = {
        'date': _date(_value(text, 'fecha')),
        'clientCode': _value(text, 'contrato'),
        'clientName': _value(text, 'nombre'),
        'equipmentSerial': serial_match.group(1).strip() if serial_match else None,
        'requestType': 'retiro',
    }
    warnings = [
        f'Campo faltante: {key}' for key, value in data.items()
        if value in (None, '') and key not in {'requestType', 'date'}
    ]
    return {
        'source': source,
        'page_count': page_count,
        'document_type': 'retiro',
        'fields': data,
        'warnings': warnings,
    }

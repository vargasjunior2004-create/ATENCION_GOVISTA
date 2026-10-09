from io import BytesIO
from pathlib import Path

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

from .models import Sale
from .domain import (
    ADDITION_TYPE_LABELS, SERVICE_TYPE_LABELS,
    SERVICE_TYPE_TO_PLAN_TYPE, sale_service_label,
    request_type_label, request_type_mode, request_type_catalog,
    MODO_ADICION, MODO_CAMBIO_PLAN,
)

SIGNER = TimestampSigner()


def get_request_label(sale, catalog=None):
    """Label de solicitud para la columna SOLICITUD del reporte.

    El nombre sale del catalogo TipoSolicitud. Un code huerfano cae al
    propio code en mayusculas, para que un movimiento antiguo nunca
    quede en blanco.
    """
    mode = request_type_mode(sale.requestType, catalog)
    if mode == MODO_ADICION and sale.additionType:
        return ADDITION_TYPE_LABELS.get(sale.additionType, 'ADICION')
    return request_type_label(sale.requestType, catalog)

LOGO_PATH = Path(__file__).resolve().parent / 'logo.png'


def sign_report_token(payload):
    """Firma 'from:to' (o 'date') con expiración de 1 hora."""
    return SIGNER.sign(payload)


def unsign_report_token(token):
    """Valida la firma. Devuelve el payload o None si es inválida/expirada."""
    try:
        return SIGNER.unsign(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        return None


def _logo_image(max_width=50):
    """Devuelve un flowable Image con el logo de la empresa, o None si no existe."""
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image

        if not LOGO_PATH.exists():
            return None
        width, height = ImageReader(str(LOGO_PATH)).getSize()
        scale = max_width / width
        return Image(str(LOGO_PATH),
                     width=max_width, height=height * scale,
                     hAlign='CENTER')
    except Exception:
        return None


def _report_header(title, subtitle):
    """Logo + título + subtítulo para encabezar un reporte."""
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Spacer

    styles = getSampleStyleSheet()
    story = []
    logo = _logo_image()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 6))
    story.append(title)
    story.append(Spacer(1, 4))
    story.append(subtitle)
    story.append(Spacer(1, 10))
    return story


# ---------------------------------------------------------------- PDF (sales)

def _sales_queryset(from_date, to_date, request_type=None, service_type=None,
                    service_type_from=None):
    """Movimientos del rango con los filtros aplicados, en una sola regla."""
    from django.db.models import Q

    qs = Sale.objects.select_related('plan', 'planFromId', 'createdBy').filter(
        date__gte=from_date, date__lte=to_date)
    if request_type:
        qs = qs.filter(requestType=request_type)
    if service_type:
        qs = qs.filter(serviceType=service_type)
    if service_type_from:
        family = SERVICE_TYPE_TO_PLAN_TYPE.get(service_type_from)
        if family:
            qs = qs.filter(
                Q(serviceTypeFrom=service_type_from)
                | Q(serviceTypeFrom__isnull=True, planFromId__type=family))
        else:
            qs = qs.filter(serviceTypeFrom=service_type_from)
    return qs.order_by('date', 'id')


def _service_filter_label(service_type=None, service_type_from=None):
    """Texto del filtro de servicio para el titulo del reporte."""
    parts = []
    if service_type:
        parts.append(SERVICE_TYPE_LABELS.get(service_type, service_type))
    if service_type_from:
        parts.append(
            f'servicio anterior: '
            f'{SERVICE_TYPE_LABELS.get(service_type_from, service_type_from)}')
    return ' - '.join(parts) if parts else 'TODOS LOS SERVICIOS'


def build_sales_pdf(from_date, to_date, request_type=None, service_type=None,
                    service_type_from=None, show_motivos=False):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet
    from datetime import datetime

    sales = _sales_queryset(from_date, to_date, request_type, service_type,
                            service_type_from)

    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm)

    title_from = datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
    title_to = datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')

    catalog = request_type_catalog()
    request_label = (request_type_label(request_type, catalog) if request_type
                     else 'TODOS LOS MOVIMIENTOS')
    service_label = _service_filter_label(service_type, service_type_from)
    title = f'MOV. CLIENTES — {request_label} — {service_label}'

    story = _report_header(
        Paragraph(f'{title}<br/><font size="9">{title_from} al {title_to}</font>', styles['Title']),
        Paragraph('', styles['Normal']),
    )

    header = ['FECHA', 'KARDEX', 'CLIENTE', 'SERVICIO', 'SOLICITUD', 'PLAN']
    if show_motivos:
        header.append('MOTIVO')
    header += ['MONTO', 'OPERADOR']
    rows = [header]
    for s in sales:
        # Plan display: cambio_plan shows "anterior → nuevo"
        plan_label = s.plan.label if s.plan else ''
        if request_type_mode(s.requestType, catalog) == MODO_CAMBIO_PLAN and s.planFromId:
            plan_label = f'{s.planFromId.label} → {s.plan.label}'
        row = [
            s.date.strftime('%d/%m/%Y') if s.date else '',
            s.clientCode or '',
            s.clientName or '',
            sale_service_label(s, catalog),
            get_request_label(s, catalog),
            plan_label,
        ]
        if show_motivos:
            row.append(s.changeReason or '')
        row += [
            f'{float(s.total):.2f}',
            s.createdBy.name if s.createdBy else '',
        ]
        rows.append(row)

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'{len(sales)} registros en el periodo', styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- XLSX (sales)

def build_sales_xlsx(from_date, to_date, request_type=None, service_type=None,
                     service_type_from=None, show_motivos=False):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    sales = _sales_queryset(from_date, to_date, request_type, service_type,
                            service_type_from)

    wb = Workbook()
    ws = wb.active
    ws.title = 'MOV. CLIENTES'

    headers = ['FECHA', 'KARDEX', 'CLIENTE', 'SERVICIO', 'SOLICITUD', 'PLAN']
    if show_motivos:
        headers.append('MOTIVO')
    headers += ['MONTO', 'OPERADOR']

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='1D4ED8')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    catalog = request_type_catalog()
    for row_idx, s in enumerate(sales, 2):
        plan_label = s.plan.label if s.plan else ''
        if request_type_mode(s.requestType, catalog) == MODO_CAMBIO_PLAN and s.planFromId:
            plan_label = f'{s.planFromId.label} → {s.plan.label}'

        data_row = [
            s.date.strftime('%d/%m/%Y') if s.date else '',
            s.clientCode or '',
            s.clientName or '',
            sale_service_label(s, catalog),
            get_request_label(s, catalog),
            plan_label,
        ]
        if show_motivos:
            data_row.append(s.changeReason or '')
        data_row += [
            float(s.total),
            s.createdBy.name if s.createdBy else '',
        ]

        for col, value in enumerate(data_row, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            if isinstance(value, float):
                cell.number_format = '#,##0.00'

    column_widths = [14, 14, 35, 24, 20, 20]
    if show_motivos:
        column_widths.append(30)
    column_widths += [14, 20]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- PNG (sales)

def _wrap_text(text, font, max_width):
    """Parte un texto en lineas que caben en max_width.

    Sin esto, ImageDraw dibuja la cadena completa y se sale de la celda,
    encima de la columna siguiente. Parte palabras cuando una sola no
    cabe (ej. codigos de plan largos en la celda PLAN).
    """
    text = str(text)
    if not text:
        return ['']

    lines, current = [], ''
    for word in text.split(' '):
        candidate = f'{current} {word}'.strip()
        if font.getlength(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        if font.getlength(word) <= max_width:
            current = word
        else:
            fragment = ''
            for char in word:
                if font.getlength(fragment + char) <= max_width:
                    fragment += char
                else:
                    lines.append(fragment)
                    fragment = char
            current = fragment
    if current:
        lines.append(current)
    return lines or ['']


def build_sales_png(from_date, to_date, request_type=None, service_type=None,
                    service_type_from=None, show_motivos=False):
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime

    sales = _sales_queryset(from_date, to_date, request_type, service_type,
                            service_type_from)

    headers = ['FECHA', 'KARDEX', 'CLIENTE', 'SERVICIO', 'SOLICITUD', 'PLAN']
    col_widths = [140, 130, 300, 240, 180, 180]
    if show_motivos:
        headers.append('MOTIVO')
        col_widths.append(200)
    headers += ['MONTO', 'OPERADOR']
    col_widths += [120, 240]
    row_height = 40
    padding = 16

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
        font_bold = font
        font_title = font

    total_width = sum(col_widths) + padding * 2
    title_height = 60
    h_padding = 6
    line_height = font.size + 6

    # Primera pasada: envolver cada celda a su columna y medir la fila.
    # El alto total depende de esto, asi que va antes de crear la imagen.
    catalog = request_type_catalog()
    rows = []
    for s in sales:
        plan_label = s.plan.label if s.plan else ''
        if request_type_mode(s.requestType, catalog) == MODO_CAMBIO_PLAN and s.planFromId:
            plan_label = f'{s.planFromId.label} → {plan_label}'
        values = [
            s.date.strftime('%d/%m/%Y') if s.date else '',
            s.clientCode or '',
            s.clientName or '',
            sale_service_label(s, catalog),
            get_request_label(s, catalog),
            plan_label,
        ]
        if show_motivos:
            values.append(s.changeReason or '')
        values += [
            f'{float(s.total):.2f}',
            s.createdBy.name if s.createdBy else '',
        ]
        cells = [
            _wrap_text(v, font, col_widths[i] - h_padding * 2)
            for i, v in enumerate(values)
        ]
        height = max(row_height, max(len(c) for c in cells) * line_height + 20)
        rows.append((cells, height))

    body_height = sum(height for _, height in rows)
    img = Image.new('RGB', (total_width, title_height + row_height + body_height + 40), '#FFFFFF')
    draw = ImageDraw.Draw(img)

    # Title
    title_from = datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
    title_to = datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
    draw.text((padding, 15), f'MOV. CLIENTES  {title_from} al {title_to}', fill='#1D4ED8', font=font_title)

    # Header row
    y = title_height
    draw.rectangle([0, y, total_width, y + row_height], fill='#1D4ED8')
    x = padding
    for i, h in enumerate(headers):
        draw.text((x + h_padding, y + 10), h, fill='#FFFFFF', font=font_bold)
        x += col_widths[i]
    y += row_height

    # Segunda pasada: dibujar. La celda PLAN de un cambio de plan puede
    # ocupar dos lineas, y la fila crece para que nada invada MONTO.
    for idx, (cells, height) in enumerate(rows):
        draw.rectangle([0, y, total_width, y + height], fill='#F8FAFC' if idx % 2 == 0 else '#FFFFFF')
        x = padding
        for i, lines in enumerate(cells):
            for n, line in enumerate(lines):
                draw.text((x + h_padding, y + 10 + n * line_height), line, fill='#1E293B', font=font)
            x += col_widths[i]
        y += height

    # Footer
    draw.text((padding, y + 10), f'{len(sales)} registros', fill='#94A3B8', font=font)

    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf

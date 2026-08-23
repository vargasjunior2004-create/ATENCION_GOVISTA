from io import BytesIO
from pathlib import Path

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

from .models import Sale, CashCount, Outflow

SIGNER = TimestampSigner()

LOGO_PATH = Path(__file__).resolve().parent / 'logo.png'

DENOMINATIONS = [
    ('Moneda 0.50', 0.50), ('Moneda 1', 1), ('Moneda 2', 2), ('Moneda 5', 5),
    ('Billete 10', 10), ('Billete 20', 20), ('Billete 50', 50),
    ('Billete 100', 100), ('Billete 200', 200),
]


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

def build_sales_pdf(from_date, to_date):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet

    sales = Sale.objects.select_related('plan', 'createdBy').filter(
        date__gte=from_date, date__lte=to_date).order_by('date', 'id')

    # Service type mapping
    service_type_map = {
        'internet': 'INTERNET',
        'tv': 'TV ANALOGA',
        'tv_digital': 'TV DIGITAL',
        'combo_analog': 'INTERNET + TV ANALOGA',
        'combo_digital': 'INTERNET + TV DIGITAL',
    }

    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm)

    story = _report_header(
        Paragraph('MOV. CLIENTES', styles['Title']),
        Paragraph(f'Periodo: {from_date} al {to_date}', styles['Normal']),
    )

    header = ['Fecha', 'Kardex', 'Cliente', 'Servicio', 'Solicitud', 'Plan', 'Monto', 'Operador']
    rows = [header]
    total_sum = 0.0
    for s in sales:
        total_sum += float(s.plan.monthly)
        service_label = service_type_map.get(s.serviceType, s.serviceType)
        rows.append([
            s.date.strftime('%d/%m/%Y') if s.date else '',
            s.clientCode, s.clientName,
            service_label, s.get_requestType_display(),
            s.plan.label, f'{float(s.plan.monthly):.2f}',
            s.createdBy.name,
        ])
    rows.append(['', '', '', '', '', 'TOTAL', f'{total_sum:.2f}', ''])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -2), 7),
        ('FONTSIZE', (0, -1), (-1, -1), 8),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'{len(sales)} registros en el periodo', styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf


# --------------------------------------------------------------- PDF (caja)

def build_cash_pdf(date_str):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet

    cc = CashCount.objects.filter(date=date_str).first()
    outflows = list(Outflow.objects.filter(date=date_str))
    total_out = sum(float(o.amount) for o in outflows)

    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)

    registered_by = cc.createdBy.name if cc and cc.createdBy else None
    story = _report_header(
        Paragraph('Arqueo de Caja', styles['Title']),
        Paragraph(f'Fecha: {date_str}', styles['Normal']),
    )
    if registered_by:
        story.append(Paragraph(
            f'Registrado por: {registered_by}', styles['Normal']))
        story.append(Spacer(1, 6))
    else:
        story.append(Spacer(1, 6))

    if cc:
        rows = [['Denominación', 'Cantidad', 'Subtotal (Bs)']]
        for label, value in DENOMINATIONS:
            count = getattr(cc, {
                'Moneda 0.50': 'coin_050', 'Moneda 1': 'coin_1',
                'Moneda 2': 'coin_2', 'Moneda 5': 'coin_5',
                'Billete 10': 'bill_10', 'Billete 20': 'bill_20',
                'Billete 50': 'bill_50', 'Billete 100': 'bill_100',
                'Billete 200': 'bill_200',
            }[label])
            rows.append([label, str(count), f'{count * value:.2f}'])
        rows.append(['TOTAL CONTADO', '', f'{float(cc.total):.2f}'])
        table = Table(rows)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        story.append(table)
    else:
        story.append(Paragraph('No hay arqueo registrado para esta fecha.',
                               styles['Normal']))

    story.append(Spacer(1, 12))
    story.append(Paragraph('Salidas de Efectivo', styles['Heading2']))
    if outflows:
        rows = [['Hora', 'A quién', 'Concepto', 'Monto (Bs)']]
        for o in outflows:
            hora = o.created_at.strftime('%H:%M') if o.created_at else '—'
            rows.append([hora, o.personName, o.concept or '—', f'{float(o.amount):.2f}'])
        rows.append(['', '', 'TOTAL SALIDAS', f'{total_out:.2f}'])
        table = Table(rows)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fee2e2')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        story.append(table)
    else:
        story.append(Paragraph('Sin salidas registradas.', styles['Normal']))

    net = (float(cc.total) if cc else 0) - total_out
    story.append(Spacer(1, 12))
    story.append(Paragraph(f'EFECTIVO TOTAL: {net:.2f} Bs', styles['Title']))
    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- XLSX (sales)

def build_sales_xlsx(from_date, to_date):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    sales = Sale.objects.select_related('plan', 'createdBy').filter(
        date__gte=from_date, date__lte=to_date).order_by('date', 'id')

    wb = Workbook()
    ws = wb.active
    ws.title = 'MOV. CLIENTES'

    # Encabezados exactos como en el Excel original
    headers = [
        'FECHA', 'KARDEX', 'NOMBRE CLIENTE', 'TIPO DE SERVICIO', 'TIPO DE SOLICITUD',
        'PAQUETE TV CABLE', 'PAQUETE INTERNET', 'MONTO INICIAL', 'MONTO FINAL',
        'MOTIVO CAMBIO DE PLAN', 'PAQUETE CAMBIO TV CABLE', 'PAQUETE CAMBIO INTERNET',
        'DIFERENCIA', 'CAJERA(O)', 'COMENTARIOS'
    ]

    # Estilos
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='1D4ED8')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Service type mapping
    service_type_map = {
        'internet': 'INTERNET',
        'tv': 'TV ANALOGA',
        'tv_digital': 'TV DIGITAL',
        'combo_analog': 'INTERNET + TV ANALOGA',
        'combo_digital': 'INTERNET + TV DIGITAL',
    }

    # Escribir datos
    for row_idx, s in enumerate(sales, 2):
        service_label = service_type_map.get(s.serviceType, s.serviceType)
        
        # Determine package TV and Internet based on service type
        paq_tv = ''
        paq_inet = ''
        if 'tv' in s.serviceType or 'combo' in s.serviceType:
            paq_tv = s.plan.label
        if 'internet' in s.serviceType or 'combo' in s.serviceType:
            paq_inet = s.plan.label

        data_row = [
            s.date.strftime('%d/%m/%Y') if s.date else '',
            s.clientCode,
            s.clientName,
            service_label,
            s.get_requestType_display(),
            paq_tv,
            paq_inet,
            float(s.plan.monthly),
            float(s.plan.total) if s.requestType == 'cambio_plan' else '',
            s.changeReason if s.requestType == 'cambio_plan' else '',
            '',  # Paquete cambio TV (no aplica por ahora)
            '',  # Paquete cambio Internet (no aplica por ahora)
            float(s.plan.total - s.plan.monthly) if s.requestType == 'cambio_plan' else '',
            s.createdBy.name,
            s.notes,
        ]

        for col, value in enumerate(data_row, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            if col in [8, 9, 13]:  # Montos
                cell.number_format = '#,##0.00'

    # Anchos de columna
    column_widths = [12, 10, 25, 22, 16, 22, 22, 14, 22, 22, 22, 14, 12, 22, 30]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else 'A' + chr(64 + i - 26)].width = width

    # Fila de total
    total_row = len(sales) + 3
    ws.cell(row=total_row, column=7, value='TOTAL').font = Font(bold=True)
    ws.cell(row=total_row, column=7).border = thin_border
    total_sum = sum(float(s.plan.monthly) for s in sales)
    ws.cell(row=total_row, column=8, value=total_sum).font = Font(bold=True)
    ws.cell(row=total_row, column=8).number_format = '#,##0.00'
    ws.cell(row=total_row, column=8).border = thin_border

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

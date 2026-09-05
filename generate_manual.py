#!/usr/bin/env python3
"""Genera el Manual de Usuario de GO VISTA - Movimiento de Clientes."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from pathlib import Path
import datetime

OUTPUT = Path(__file__).parent / "MANUAL_USUARIO_GO_VISTA.pdf"

BLUE = colors.HexColor("#1d4ed8")
LIGHT_BLUE = colors.HexColor("#dbeafe")
RED = colors.HexColor("#dc2626")
LIGHT_RED = colors.HexColor("#fee2e2")
GREEN = colors.HexColor("#16a34a")
LIGHT_GREEN = colors.HexColor("#dcfce7")
SLATE = colors.HexColor("#1e293b")
GRAY = colors.HexColor("#64748b")
LIGHT_GRAY = colors.HexColor("#f1f5f9")


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=28, leading=34, textColor=BLUE, spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=14, leading=18, textColor=GRAY, spaceAfter=6, alignment=TA_CENTER))
    styles.add(ParagraphStyle("ChTitle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=BLUE, spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("SecTitle", parent=styles["Heading2"], fontSize=13, leading=16, textColor=SLATE, spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, textColor=SLATE, alignment=TA_JUSTIFY, spaceAfter=4))
    styles.add(ParagraphStyle("Bul", parent=styles["Normal"], fontSize=10, leading=14, textColor=SLATE, leftIndent=20, spaceAfter=2))
    styles.add(ParagraphStyle("Warn", parent=styles["Normal"], fontSize=10, leading=14, textColor=RED, leftIndent=10, spaceBefore=4, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=GRAY, alignment=TA_CENTER))
    return styles


def warning_box(text, styles):
    data = [[Paragraph(f"ADVERTENCIA: {text}", styles["Warn"])]]
    t = Table(data, colWidths=["*"])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), LIGHT_RED), ("BOX", (0,0), (-1,-1), 1.5, RED), ("LEFTPADDING", (0,0), (-1,-1), 12), ("RIGHTPADDING", (0,0), (-1,-1), 12), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    return t


def note_box(text, styles):
    data = [[Paragraph(f"Nota: {text}", styles["Body"])]]
    t = Table(data, colWidths=["*"])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), LIGHT_BLUE), ("BOX", (0,0), (-1,-1), 1, BLUE), ("LEFTPADDING", (0,0), (-1,-1), 12), ("RIGHTPADDING", (0,0), (-1,-1), 12), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    return t


def tip_box(text, styles):
    data = [[Paragraph(f"Consejo: {text}", styles["Body"])]]
    t = Table(data, colWidths=["*"])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), LIGHT_GREEN), ("BOX", (0,0), (-1,-1), 1, GREEN), ("LEFTPADDING", (0,0), (-1,-1), 12), ("RIGHTPADDING", (0,0), (-1,-1), 12), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    return t


def tbl(headers, rows, cw=None):
    s = getSampleStyleSheet()
    data = [[Paragraph(h, s["Normal"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), s["Normal"]) for c in r])
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,0), 9), ("FONTSIZE", (0,1), (-1,-1), 8), ("GRID", (0,0), (-1,-1), 0.4, colors.grey), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT_GRAY]), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    return t


def build_manual():
    S = build_styles()
    story = []

    # PORTADA
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("GO VISTA", S["CoverTitle"]))
    story.append(Paragraph("Movimiento de Clientes", S["CoverTitle"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="60%", thickness=2, color=BLUE, spaceAfter=8))
    story.append(Paragraph("Manual de Usuario", S["CoverSub"]))
    story.append(Paragraph("Sistema de Registro y Control de Movimientos FTTH", S["CoverSub"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Version 3.0 — {datetime.date.today().strftime('%B %Y')}", S["CoverSub"]))
    story.append(Paragraph("GO VISTA — Telecomunicaciones Bolivia", S["CoverSub"]))
    story.append(PageBreak())

    # TABLA DE CONTENIDOS
    story.append(Paragraph("Tabla de Contenidos", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    for n, t in [("1.","Introduccion"),("2.","Requisitos de Acceso"),("3.","Inicio de Sesion"),("4.","Dashboard"),("5.","Registro de Movimientos"),("6.","Lista de Movimientos"),("7.","Reportes (PDF, Excel, Foto)"),("8.","Arqueo de Caja"),("9.","Gestion de Planes (Admin)"),("10.","Gestion de Usuarios (Admin)"),("11.","Edicion y Eliminacion"),("12.","Sesion y Seguridad"),("13.","Advertencias Importantes"),("14.","Solucion de Problemas")]:
        story.append(Paragraph(f"<b>{n}</b> {t}", S["Body"]))
    story.append(PageBreak())

    # 1. INTRODUCCION
    story.append(Paragraph("1. Introduccion", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("GO VISTA — Movimiento de Clientes es un sistema web disenado para el registro y control de movimientos diarios de telecomunicaciones FTTH. Permite registrar instalaciones, cambios de plan, retiros, recontractaciones y otras operaciones, asi como generar reportes en PDF, Excel e imagen (PNG).", S["Body"]))
    story.append(Paragraph("El sistema esta compuesto por un backend en Django (Python) y un frontend en React, alojado en Render con base de datos PostgreSQL en Supabase.", S["Body"]))
    story.append(Paragraph("<b>Sobre el servidor:</b> El sistema corre en Render (servicio gratuito). Render apaga la aplicacion despues de 15 minutos sin uso para ahorrar recursos. Cuando alguien vuelve a entrar, el servidor se enciende solo pero puede tardar entre 30 y 60 segundos en cargar la primera vez. Esto es NORMAL y no afecta sus datos.", S["Body"]))
    story.append(Paragraph("<b>Sus datos:</b> Toda la informacion se guarda en Supabase (base de datos en la nube). Cuando Render se apaga, sus datos NO se pierden. Supabase mantiene la informacion de forma segura y permanente.", S["Body"]))

    # 2. REQUISITOS
    story.append(Paragraph("2. Requisitos de Acceso", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Para acceder al sistema necesita:", S["Body"]))
    for b in ["Un navegador web actualizado (Chrome, Firefox, Edge, Safari)", "Conexion a internet", "Usuario y contrasena proporcionados por el administrador"]:
        story.append(Paragraph(f"• {b}", S["Bul"]))
    story.append(Paragraph("URL de acceso:", S["SecTitle"]))
    story.append(Paragraph("<b>https://atencion-govista-2.onrender.com</b>", S["Body"]))
    story.append(warning_box("La sesion expira automaticamente despues de 5 minutos de inactividad. Guarde su trabajo frecuentemente.", S))
    story.append(PageBreak())

    # 3. INICIO DE SESION
    story.append(Paragraph("3. Inicio de Sesion", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Al abrir la aplicacion, se mostrara la pantalla de login. Ingrese su <b>nombre de usuario</b> (no correo electronico) y su contrasena.", S["Body"]))
    story.append(Paragraph("Pasos:", S["SecTitle"]))
    for i, st in enumerate(["Ingrese su nombre de usuario en el campo correspondiente", "Ingrese su contrasena", "Haga clic en el boton de login", "Si los datos son correctos, sera redirigido al Dashboard"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(Paragraph("Credenciales por defecto:", S["SecTitle"]))
    story.append(tbl(["Usuario","Contrasena","Rol"], [["Administrador","admin123","admin"],["JUNIOR","admin123","admin"]], cw=[5*cm,4*cm,3*cm]))
    story.append(warning_box("Las contrasenas por defecto deben cambiarse despues del primer ingreso. Nunca comparta sus credenciales.", S))
    story.append(PageBreak())

    # 4. DASHBOARD
    story.append(Paragraph("4. Dashboard", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("El Dashboard es la pantalla principal que muestra un resumen de las operaciones. Contiene las siguientes secciones:", S["Body"]))
    story.append(Paragraph("4.1 Resumen de Movimientos", S["SecTitle"]))
    story.append(Paragraph("Muestra el total de movimientos registrados (hoy, esta semana y este mes) con sus montos correspondientes. Solo los administradores ven las estadisticas semanales y mensuales.", S["Body"]))
    story.append(Paragraph("4.2 Resumen de Instalaciones", S["SecTitle"]))
    story.append(Paragraph("Muestra las instalaciones nuevas (nuevos contratos) del dia, semana y mes.", S["Body"]))
    story.append(Paragraph("4.3 Resumen de Retiros", S["SecTitle"]))
    story.append(Paragraph("Muestra los retiros registrados del dia, semana y mes.", S["Body"]))
    story.append(Paragraph("4.4 Botones de Reportes", S["SecTitle"]))
    story.append(Paragraph("En la parte superior derecha del Dashboard hay tres botones:", S["Body"]))
    story.append(tbl(["Boton","Funcion","Formato"], [["Excel","Descarga archivo Excel del dia","XLSX (14 columnas)"],["Foto","Descarga imagen del reporte del dia","PNG"],["Planilla PDF","Descarga PDF del reporte del dia","PDF (8 columnas)"]], cw=[3*cm,6*cm,5*cm]))
    story.append(note_box("Los reportes solo se generan si hay movimientos registrados en el dia. Si no hay movimientos, el boton mostrara 'Sin movimientos hoy'.", S))
    story.append(PageBreak())

    # 5. REGISTRO DE MOVIMIENTOS
    story.append(Paragraph("5. Registro de Movimientos", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Para registrar un nuevo movimiento, haga clic en el boton '+' o en 'Nuevo Movimiento' en el menu lateral. Se abrira el formulario de registro.", S["Body"]))
    story.append(Paragraph("5.1 Campos del Formulario", S["SecTitle"]))
    story.append(tbl(["Campo","Descripcion","Obligatorio"], [["Codigo Cliente (Kardex)","Identificador unico del cliente. Auto-completa el nombre.","Si"],["Nombre del Cliente","Nombre completo del cliente. Se auto-completa con el kardex.","Si"],["Tipo de Servicio","Internet, TV Analoga, TV Digital, Combo Analogo, Combo Digital","Si"],["Tipo de Solicitud","Nuevo Contrato, Cambio de Plan, Recontractacion, Retiro, Adicion, Baja Temporal, Otro","Si"],["Plan","Plan seleccionado segun el tipo de servicio","Si"],["Monto","Calculado automaticamente: Mensualidad + Instalacion","Automatico"],["Fecha","Se establece automaticamente (hora de Bolivia, UTC-4)","Automatico"],["Motivo del Cambio","Solo requerido si el tipo es 'Cambio de Plan'","Condicionado"],["Comentarios","Observaciones adicionales (opcional)","No"]], cw=[4*cm,8*cm,3*cm]))
    story.append(Paragraph("5.2 Proceso de Registro", S["SecTitle"]))
    for i, st in enumerate(["Ingrese el kardex del cliente. Si ya existe, el nombre se auto-completara.", "Si el kardex es nuevo, ingrese manualmente el nombre del cliente.", "Seleccione el tipo de servicio.", "Seleccione el tipo de solicitud.", "Seleccione el plan correspondiente. El monto se calcula automaticamente.", "Haga clic en 'Vista Previa' para revisar los datos.", "Si todo es correcto, confirme el registro."], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(warning_box("El monto mostrado es la SUMA de mensualidad + instalacion. El sistema calcula el monto total a partir del plan seleccionado. Nunca se edita manualmente.", S))
    story.append(tip_box("Todos los campos de texto se guardan en MAYUSCULAS automaticamente. No es necesario escribir en mayusculas.", S))
    story.append(PageBreak())

    # 6. LISTA DE MOVIMIENTOS
    story.append(Paragraph("6. Lista de Movimientos", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("La lista de movimientos muestra todos los registros con opciones de filtrado y busqueda. Se muestra 25 registros por pagina.", S["Body"]))
    story.append(Paragraph("6.1 Filtros Disponibles", S["SecTitle"]))
    story.append(tbl(["Filtro","Funcion"], [["Fecha Desde","Filtra movimientos desde una fecha especifica"],["Fecha Hasta","Filtra movimientos hasta una fecha especifica"],["Tipo de Solicitud","Filtra por tipo: Nuevo Contrato, Cambio de Plan, Retiro, etc."],["Tipo de Servicio","Filtra por servicio: Internet, TV, Combo, etc."]], cw=[4*cm,12*cm]))
    story.append(Paragraph("6.2 Opciones por Registro", S["SecTitle"]))
    story.append(Paragraph("Cada registro en la lista tiene las siguientes acciones:", S["Body"]))
    for a in ["Ver detalles completos del movimiento", "Editar (solo administradores)", "Eliminar (solo administradores, con confirmacion)"]:
        story.append(Paragraph(f"• {a}", S["Bul"]))
    story.append(Paragraph("6.3 Paginacion", S["SecTitle"]))
    story.append(Paragraph("La lista se divide en paginas de 25 registros. Use los botones de navegacion para moverse entre paginas.", S["Body"]))
    story.append(PageBreak())

    # 7. REPORTES
    story.append(Paragraph("7. Reportes (PDF, Excel, Foto)", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("El sistema genera reportes en tres formatos diferentes, cada uno con un proposito especifico.", S["Body"]))
    story.append(Paragraph("7.1 Reporte PDF (Planilla)", S["SecTitle"]))
    story.append(Paragraph("El PDF es la planilla oficial de movimientos. Contiene 8 columnas:", S["Body"]))
    story.append(tbl(["Columna","Descripcion"], [["Fecha","Fecha del movimiento (dd/mm/aaaa)"],["Kardex","Codigo del cliente"],["Cliente","Nombre del cliente"],["Servicio","Tipo de servicio (INTERNET, TV, COMBO)"],["Solicitud","Tipo de solicitud (INSTALACION, RETIRO, etc.)"],["Plan","Nombre del plan contratado"],["Monto Ini","Monto total (mensualidad + instalacion)"],["Dif","Diferencia (mismo monto que Monto Ini)"],["Operador","Nombre del usuario que registro el movimiento"]], cw=[3*cm,13*cm]))
    story.append(Paragraph("7.2 Reporte Excel (XLSX)", S["SecTitle"]))
    story.append(Paragraph("El Excel contiene 14 columnas segun el formato de la empresa. Incluye campos adicionales como paquetes de TV e Internet por separado.", S["Body"]))
    story.append(Paragraph("7.3 Foto (PNG)", S["SecTitle"]))
    story.append(Paragraph("La foto es una imagen del reporte en formato compacto. Contiene las mismas columnas basicas que el PDF en formato visual.", S["Body"]))
    story.append(Paragraph("7.4 Generacion de Reportes", S["SecTitle"]))
    for i, st in enumerate(["Vaya al Dashboard o a la seccion de Reportes", "Seleccione el rango de fechas (desde y hasta)", "Haga clic en el boton del formato deseado (PDF, Excel o Foto)", "El archivo se descargara automaticamente"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(Paragraph("7.5 Links Publicos", S["SecTitle"]))
    story.append(Paragraph("El sistema genera links publicos con firma digital que expiran en 1 hora. Estos links permiten descargar reportes sin necesidad de iniciar sesion.", S["Body"]))
    story.append(warning_box("Los links publicos expiran en 1 hora. Si un link no funciona, solicite uno nuevo al administrador.", S))
    story.append(PageBreak())

    # 8. ARQUEO DE CAJA
    story.append(Paragraph("8. Arqueo de Caja", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("El arqueo de caja permite registrar el conteo de efectivo por denominacion y las salidas de efectivo del dia.", S["Body"]))
    story.append(Paragraph("8.1 Conteo de Efectivo", S["SecTitle"]))
    story.append(Paragraph("Ingrese la cantidad de billetes y monedas de cada denominacion:", S["Body"]))
    story.append(tbl(["Denominacion","Valor"], [["Moneda 0.50","0.50 Bs"],["Moneda 1","1.00 Bs"],["Moneda 2","2.00 Bs"],["Moneda 5","5.00 Bs"],["Billete 10","10.00 Bs"],["Billete 20","20.00 Bs"],["Billete 50","50.00 Bs"],["Billete 100","100.00 Bs"],["Billete 200","200.00 Bs"]], cw=[5*cm,4*cm]))
    story.append(Paragraph("8.2 Salidas de Efectivo", S["SecTitle"]))
    story.append(Paragraph("Registre las salidas de efectivo indicando:", S["Body"]))
    for f in ["Nombre de la persona que recibe el efectivo", "Monto de la salida", "Concepto o motivo de la salida"]:
        story.append(Paragraph(f"• {f}", S["Bul"]))
    story.append(Paragraph("8.3 Reporte de Arqueo", S["SecTitle"]))
    story.append(Paragraph("Puede generar un PDF del arqueo de caja que incluye:", S["Body"]))
    for r in ["Tabla de conteo por denominacion con subtotales", "Total contado en efectivo", "Lista de salidas de efectivo con hora y concepto", "Efectivo total (contado + salidas)"]:
        story.append(Paragraph(f"• {r}", S["Bul"]))
    story.append(note_box("Cada usuario tiene su propio arqueo de caja. Los administradores pueden ver los arqueos de todos los usuarios.", S))
    story.append(PageBreak())

    # 9. GESTION DE PLANES
    story.append(Paragraph("9. Gestion de Planes (Solo Admin)", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Los administradores pueden gestionar los planes de servicio disponibles para registro de movimientos.", S["Body"]))
    story.append(Paragraph("9.1 Campos de un Plan", S["SecTitle"]))
    story.append(tbl(["Campo","Descripcion"], [["Codigo","Identificador unico del plan (ej: FTTH-100)"],["Nombre","Nombre descriptivo del plan"],["Tipo","Internet, TV o Combo"],["Velocidad","Velocidad en Mbps (para planes de internet)"],["Mensualidad","Costo mensual del servicio"],["Instalacion","Costo de instalacion (cobrado una vez)"],["Monto Total","Mensualidad + Instalacion (calculado automaticamente)"],["Estado","Activo o Inactivo"],["Legacy","Si es true, el plan es del catalogo anterior y no aparece en nuevos movimientos"]], cw=[4*cm,12*cm]))
    story.append(Paragraph("9.2 Busqueda de Planes", S["SecTitle"]))
    story.append(Paragraph("Use el campo de busqueda para filtrar planes por codigo, nombre o tipo. La busqueda se ejecuta en tiempo real.", S["Body"]))
    story.append(Paragraph("9.3 Planes Legacy", S["SecTitle"]))
    story.append(Paragraph("Los planes marcados como 'legacy' son planes del catalogo anterior. No aparecen en el formulario de nuevos movimientos, pero si se mantienen en movimientos anteriores.", S["Body"]))
    story.append(Paragraph("Para cambiar el estado de un plan, use el boton 'Inhabilitar como actual' o 'Marcar como actual'.", S["Body"]))
    story.append(warning_box("No elimine planes que tengan movimientos asociados. El sistema lo impedira. Primero debe eliminar los movimientos relacionados.", S))
    story.append(PageBreak())

    # 10. GESTION DE USUARIOS
    story.append(Paragraph("10. Gestion de Usuarios (Solo Admin)", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Los administradores pueden crear, editar y eliminar usuarios del sistema.", S["Body"]))
    story.append(Paragraph("10.1 Roles", S["SecTitle"]))
    story.append(tbl(["Rol","Permisos"], [["admin","Acceso total: crear, editar, eliminar movimientos, planes y usuarios"],["ventas","Solo puede registrar movimientos y ver reportes"]], cw=[3*cm,13*cm]))
    story.append(Paragraph("10.2 Crear Usuario", S["SecTitle"]))
    story.append(Paragraph("Para crear un nuevo usuario:", S["Body"]))
    for i, st in enumerate(["Vaya a la seccion 'Usuarios' en el menu lateral", "Haga clic en 'Nuevo Usuario'", "Ingrese el nombre de usuario", "Ingrese la contrasena", "Seleccione el rol (admin o ventas)", "Guarde los cambios"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(warning_box("Un administrador no puede eliminarse a si mismo. Si necesita eliminar su cuenta, solicite a otro administrador que lo haga.", S))
    story.append(PageBreak())

    # 11. EDICION Y ELIMINACION
    story.append(Paragraph("11. Edicion y Eliminacion", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("11.1 Editar Movimientos", S["SecTitle"]))
    story.append(Paragraph("Solo los administradores pueden editar movimientos. Para editar:", S["Body"]))
    for i, st in enumerate(["Busque el movimiento en la lista", "Haga clic en el icono de editar (lapiz)", "Modifique los campos necesarios", "Guarde los cambios"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(Paragraph("Al editar un movimiento, el sistema registra automaticamente quien lo edito y cuando.", S["Body"]))
    story.append(Paragraph("11.2 Eliminar Movimientos, Planes o Usuarios", S["SecTitle"]))
    story.append(Paragraph("Solo los administradores pueden eliminar registros. Al hacer clic en eliminar, aparecera un cuadro de confirmacion:", S["Body"]))
    for i, st in enumerate(["Haga clic en el icono de eliminar (basurero)", "Se mostrara un cuadro de confirmacion con el titulo 'Eliminar movimiento' (o plan/usuario)", "Revise cuidadosamente la informacion mostrada", "Haga clic en 'Si, eliminar' para confirmar, o 'Cancelar' para abortar"], 1):
        story.append(Paragraph(f"<b>{i}.</b> {st}", S["Bul"]))
    story.append(warning_box("La eliminacion es PERMANENTE y no se puede deshacer. Asegurese de seleccionar el registro correcto antes de confirmar.", S))
    story.append(note_box("No se pueden eliminar planes que tengan movimientos asociados. El sistema mostrara un error si intenta hacerlo.", S))
    story.append(PageBreak())

    # 12. SESION Y SEGURIDAD
    story.append(Paragraph("12. Sesion y Seguridad", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("12.1 Duracion de la Sesion", S["SecTitle"]))
    story.append(tbl(["Configuracion","Valor"], [["Tiempo de vida del token JWT","5 minutos"],["Tiempo de inactividad permitido","5 minutos (solo clicks)"],["Tipo de autenticacion","Bearer token (JWT)"],["Cierre automatico","En respuesta 401 del servidor"],["Render — Tiempo sin uso","15 minutos (apaga el servidor, NO borra datos)"],["Render — Despertar","30-60 segundos la primera vez despues de apagado"]], cw=[6*cm,10*cm]))
    story.append(Paragraph("12.2 Cierre de Sesion", S["SecTitle"]))
    story.append(Paragraph("Para cerrar sesion, haga clic en su nombre de usuario en la esquina superior derecha y seleccione 'Cerrar Sesion'.", S["Body"]))
    story.append(Paragraph("12.3 Seguridad", S["SecTitle"]))
    for p in ["Las contrasenas se almacenan hasheadas (nunca en texto plano)", "Los tokens JWT tienen tiempo de expiracion limitado", "El sistema detecta inactividad y cierra la sesion automaticamente", "Los administradores no pueden eliminarse a si mismos", "Las eliminaciones requieren confirmacion explicita"]:
        story.append(Paragraph(f"• {p}", S["Bul"]))
    story.append(warning_box("Nunca cierre el navegador sin cerrar sesion primero. Si otro usuario accede al mismo equipo, podria ver datos sensibles.", S))
    story.append(PageBreak())

    # 13. ADVERTENCIAS
    story.append(Paragraph("13. Advertencias Importantes", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(Paragraph("Lea cuidadosamente las siguientes advertencias antes de usar el sistema:", S["Body"]))
    for title, desc in [
        ("Primera vez en Render — Tiempo de carga", "La primera vez que accede al sistema despues de un periodo sin uso, la pagina puede tardar entre 30 y 60 segundos en cargar. Esto es normal: Render (el servidor gratuito) apaga la aplicacion despues de 15 minutos de inactividad para ahorrar recursos. Cuando alguien la vuelve a abrir, el servidor se enciende automaticamente pero necesita unos segundos para arrancar. No cierre el navegador; espere a que cargue."),
        ("Render se apaga despues de 15 minutos", "Si nadie usa el sistema durante 15 minutos, Render apaga el servidor automaticamente. Esto NO afecta sus datos (ver siguiente punto). Solo significa que la proxima vez que alguien entre, tardara un poco mas en cargar. Una vez que alguien lo usa, todo funciona normalmente."),
        ("Sus datos estan seguros en Supabase", "Toda la informacion (movimientos, planes, usuarios, arqueos) se guarda en Supabase, una base de datos en la nube con respaldo automatico. Cuando Render se apaga, los datos NO se pierden. Supabase mantiene la informacion de forma segura y permanente. Puede acceder a sus datos desde cualquier momento, sin importar si el servidor esta activo o no."),
        ("Sesion — 5 minutos de inactividad", "La sesion del usuario expira despues de 5 minutos sin hacer clic en nada. Si la sesion expira, debera volver a ingresar su usuario y contrasena. Guarde su trabajo frecuentemente para evitar perder datos no guardados."),
        ("Eliminaciones permanentes", "Las eliminaciones de movimientos, planes y usuarios son PERMANENTES y no se pueden deshacer. Asegurese de seleccionar el registro correcto antes de confirmar."),
        ("Reportes — Monto automatico", "El 'Monto' en los reportes es la suma de mensualidad + instalacion. Este valor se calcula automaticamente a partir del plan seleccionado y no se puede editar manualmente."),
        ("Planes legacy", "Los planes marcados como 'legacy' (catalogo anterior) no aparecen en el formulario de nuevos movimientos. Si necesita usar un plan legacy, contacte al administrador para desmarcar la opcion."),
        ("Contrasenas — No compartir", "Nunca comparta sus credenciales de acceso. Cada usuario debe tener su propia cuenta. Si sospecha que su contrasena fue comprometida, contacte al administrador inmediatamente."),
        ("Navegador actualizado", "Use navegadores actualizados (Chrome, Firefox, Edge). El sistema puede no funcionar correctamente en navegadores antiguos o no soportados."),
        ("Conexion a internet", "El sistema requiere conexion a internet permanente. Si se corta la conexion, los datos no se guardaran hasta que se restablezca. Verifique siempre que el guardado fue exitoso."),
        ("Horario del sistema", "Todos los registros usan la zona horaria de Bolivia (UTC-4). La fecha se establece automaticamente al registrar un movimiento."),
    ]:
        story.append(Paragraph(f"<b>{title}:</b>", S["Warn"]))
        story.append(Paragraph(desc, S["Body"]))
    story.append(PageBreak())

    # 14. SOLUCION DE PROBLEMAS
    story.append(Paragraph("14. Solucion de Problemas", S["ChTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=8))
    story.append(tbl(["Problema","Solucion"], [
        ["La pagina tarda mucho en cargar la primera vez", "Es normal. Render apaga el servidor despues de 15 minutos sin uso. Espere 30-60 segundos y la pagina cargara. No cierre el navegador."],
        ["No puedo iniciar sesion", "Verifique su nombre de usuario y contrasena. El login usa el nombre (no el correo electronico). Verifique que no haya espacios extra."],
        ["La pagina no carga", "Verifique su conexion a internet. Intente refrescar la pagina (Ctrl+F5). Si persiste, espere unos minutos y vuelva a intentar."],
        ["Se cerro sesion inesperadamente", "La sesion expiro por inactividad (5 minutos). Inicie sesion nuevamente. Guarde su trabajo frecuentemente."],
        ["El reporte no se genera", "Verifique que haya movimientos en el rango de fechas seleccionado. Si no hay movimientos, el reporte no se puede generar."],
        ["No puedo eliminar un plan", "El plan tiene movimientos asociados. Primero debe editar o eliminar los movimientos que usan ese plan, y luego elimine el plan."],
        ["El monto no es correcto", "El monto se calcula automaticamente a partir del plan. Para cambiarlo, debe cambiar el plan del movimiento."],
        ["No veo todos los movimientos", "Verifique los filtros de fecha. Los movimientos pueden estar filtrados por rango de fechas. Limpie los filtros para ver todo."],
        ["El sistema esta lento", "Puede deberse a alta demanda o a que el servidor se esta despertando. Espere unos minutos y vuelva a intentar."],
        ["Error 403 Forbidden", "Su usuario no tiene permisos para esta accion. Solo los administradores pueden editar/eliminar registros. Contacte al administrador."],
        ["Error 500 Internal Server Error", "Error del servidor. Intente de nuevo en unos minutos. Si persiste, contacte al administrador."],
        ["No se guardo mi registro", "Verifique su conexion a internet. Si la conexion se interrumpio, el registro no se guardo. Intente nuevamente."],
    ], cw=[5*cm,11*cm]))

    # FOOTER
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE, spaceAfter=4))
    story.append(Paragraph(f"GO VISTA — Movimiento de Clientes | Manual de Usuario v3.0 | {datetime.date.today().strftime('%d/%m/%Y')}", S["Footer"]))
    story.append(Paragraph("Soporte: https://github.com/vargasjunior2004-create/ATENCION_GOVISTA", S["Footer"]))

    return story


def main():
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm, title="Manual de Usuario - GO VISTA Movimiento de Clientes", author="GO VISTA")
    doc.build(build_manual())
    print(f"PDF generado: {OUTPUT}")
    print(f"Tamano: {OUTPUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()

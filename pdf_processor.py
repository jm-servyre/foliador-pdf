# pdf_processor.py

from io import BytesIO
from datetime import datetime
import os

# Dependencias de procesamiento de PDF
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


# --- Funciones de Utilidad de Log ---

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    
def log_success(start_number, pages_foliated, corner):
    """Registra una operación de foliado exitosa."""
    log_entry = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | SUCCESS | "
        f"Folios: {start_number:04} a {start_number + pages_foliated - 1:04} | "
        f"Páginas: {pages_foliated} | "
        f"Esquina: {corner}\n"
    )
    with open(os.path.join(LOG_DIR, "folios_generados_web.txt"), "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

def log_error(error_message, details=None):
    """Registra un error grave en un archivo de errores separado."""
    details_str = f" | Detalles: {details}" if details else ""
    log_entry = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ERROR | "
        f"{error_message}{details_str}\n"
    )
    with open(os.path.join(LOG_DIR, "errores_procesamiento.txt"), "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

# --- Funciones Centrales ---

def crear_folio_pdf(page_width, page_height, folio_text, font, font_size, 
                        offset_cm, corner, orientation) -> BytesIO:
    """Crea un PDF en memoria (capa) con el número de folio."""
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    can.setFont(font, font_size)

    margin = offset_cm * cm
    
    if "right" in corner:
        x_position = page_width - margin
        align_func = can.drawRightString
    else: 
        x_position = margin 
        align_func = can.drawString
    
    if "bottom" in corner:
        y_position = margin 
    else: 
        y_position = page_height - margin - font_size 
    
    if orientation == "vertical":
        can.translate(x_position, y_position)
        can.rotate(90)
        can.drawString(0, 0, folio_text)
    else: 
        align_func(x_position, y_position, folio_text)
            
    can.save()
    packet.seek(0)
    return packet


def agregar_folios_web(input_path, output_path, font="Courier-Bold", font_size=16, 
                        start_number=1, offset_cm=1, 
                        corner="bottom-right", orientation="horizontal",
                        start_page=1, end_page=None, 
                        preview_mode=False) -> bool:
    """
    Agrega folios a un PDF dentro de un rango de páginas opcional,
    incluyendo las páginas anteriores sin foliado.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Manejar PDF cifrado
        if reader.is_encrypted:
            log_error("PDF cifrado detectado", details=input_path)
            return False

        total_pages_in_file = len(reader.pages)
        
        # --- 1. Lógica de Determinación de Rango ---
        start_index = max(0, int(start_page) - 1) 
        
        if end_page is None or end_page == "" or int(end_page) == 0:
            end_index = total_pages_in_file
        else:
            end_index = min(total_pages_in_file, int(end_page))
        
        pages_before_range = reader.pages[0:start_index]
        pages_to_process = reader.pages[start_index:end_index] 
        
        pages_foliated_count = len(pages_to_process)
        
        if pages_foliated_count <= 0 and not preview_mode:
             raise ValueError("El rango de páginas especificado es inválido o está fuera de los límites del PDF.")

        # --- 2. Añadir Páginas Anteriores SIN Foliar ---
        if not preview_mode:
            for page in pages_before_range:
                writer.add_page(page) 

        # --- 3. Foliado y Añadir Páginas del Rango ---
        
        folio_actual = start_number
        
        for page in pages_to_process:
            
            folio_text = f"{folio_actual:04}" 

            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # 1. Crear la superposición (Reportlab)
            overlay_buffer = crear_folio_pdf(
                page_width, page_height, folio_text, font, font_size, 
                offset_cm, corner, orientation
            )
            
            # 2. Leer la superposición binaria (pypdf)
            overlay_reader = PdfReader(overlay_buffer)
            
            # 3. Combinar las páginas
            page.merge_page(overlay_reader.pages[0]) 
            
            # 4. Añadir la página foliada al escritor
            writer.add_page(page)
            folio_actual += 1

        # 5. Escribir el resultado final
        with open(output_path, "wb") as f:
            writer.write(f)
        
        # Registro de Éxito
        if not preview_mode:
             log_success(start_number, pages_foliated_count, corner)

        return True

    except Exception as e:
        log_error("Fallo al procesar PDF", details=str(e))
        print(f"Error grave durante el foliado: {e}")
        return False
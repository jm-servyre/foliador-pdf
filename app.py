# app.py

import os
import uuid
import time
import io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, Response

# Intentar importar la librería de procesamiento de PDF (puede fallar si no hay dependencias)
try:
    from pdf_processor import agregar_folios_web
    PDF_PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"Error al importar pdf_processor: {e}. El foliado estará deshabilitado.")
    PDF_PROCESSOR_AVAILABLE = False

# Intentar importar la librería de vista previa (requiere Poppler)
try:
    from pdf2image import convert_from_bytes
    PDF_PREVIEW_AVAILABLE = True
except ImportError as e:
    print(f"Error al importar pdf2image: {e}. La vista previa estará deshabilitada. Asegúrate de tener Poppler instalado.")
    PDF_PREVIEW_AVAILABLE = False


app = Flask(__name__)
app.secret_key = str(uuid.uuid4()) # Clave secreta para mensajes flash
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024 # Límite: 2 GB (2 Gigabytes)
TEMP_FOLDER = os.path.join(os.getcwd(), 'temp_files')
ALLOWED_EXTENSIONS = {'pdf'}

# --- Funciones de Utilidad ---

def allowed_file(filename):
    return '.' in filename and \
                filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_temp_files(hours_old=1):
    """Elimina archivos temporales más antiguos que las horas especificadas."""
    print("Iniciando limpieza de archivos temporales...")
    now = time.time()
    cutoff = now - (hours_old * 3600)
    
    count = 0
    
    if os.path.exists(TEMP_FOLDER):
        for filename in os.listdir(TEMP_FOLDER):
            file_path = os.path.join(TEMP_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    file_mod_time = os.stat(file_path).st_mtime
                    if file_mod_time < cutoff:
                        os.remove(file_path)
                        count += 1
            except Exception as e:
                print(f"Error al intentar limpiar el archivo {file_path}: {e}")
    
    print(f"Limpieza finalizada. Archivos eliminados: {count}.")


# --- Manejador de Errores ---

@app.errorhandler(413)
def too_large_error(e):
    # Esto captura el error de tamaño si Werkzeug lo lanza, y permite un mensaje flash.
    flash('🚨 Error de Carga (413): El archivo excede el límite de 2GB o hubo un error de comunicación.', 'error')
    return redirect(url_for('upload_file')), 413


# --- Rutas de la Aplicación ---

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        
        # 0. Validar si se recibió un archivo
        if 'pdf_file' not in request.files or request.files['pdf_file'].filename == '':
            flash('No se seleccionó ningún archivo.', 'error')
            return redirect(url_for('upload_file'))
        
        file = request.files['pdf_file']
        
        if not allowed_file(file.filename):
            flash('Tipo de archivo no permitido. Solo se aceptan PDFs.', 'error')
            return redirect(url_for('upload_file'))

        # Proceso de Foliado
        try:
            # Generar nombres de archivo únicos y seguros
            file_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            original_extension = filename.rsplit('.', 1)[1].lower()
            
            temp_input_path = os.path.join(TEMP_FOLDER, f'{file_id}_input.{original_extension}')
            temp_output_path = os.path.join(TEMP_FOLDER, f'{file_id}_foliado.{original_extension}')

            # Guardar el archivo temporalmente
            file.save(temp_input_path)

            # 2. Obtener Parámetros
            start_number = int(request.form.get('start_number', 1))
            
            # Manejo de start_page (si viene vacío, es 1)
            start_page_raw = request.form.get('start_page')
            start_page = int(start_page_raw) if start_page_raw and start_page_raw.isdigit() else 1
            
            # Manejo de end_page (si viene vacío, es None)
            end_page_raw = request.form.get('end_page')
            end_page = int(end_page_raw) if end_page_raw and end_page_raw.isdigit() else None
            
            # PARÁMETROS DE ESTILO
            font_size = int(request.form.get('font_size', 16))
            offset_cm = float(request.form.get('offset', 1.0))
            corner = request.form.get('corner', 'bottom-right')
            orientation = request.form.get('orientation', 'horizontal')
            
            # 3. Procesar el Archivo (Llamada a pdf_processor.py)
            success = agregar_folios_web(
                input_path=temp_input_path,
                output_path=temp_output_path,
                font="Courier-Bold", # Fuente fija para estilo sello/máquina de escribir
                font_size=font_size,
                start_number=start_number,
                offset_cm=offset_cm,
                corner=corner,
                orientation=orientation,
                start_page=start_page,
                end_page=end_page,
                preview_mode=False
            )

            if success and os.path.exists(temp_output_path):
                # 4. Enviar el archivo procesado para descarga (VERSION ROBUSTA)
                try:
                    # Crear un nombre de archivo limpio
                    base_filename = filename.rsplit('.', 1)[0]
                    download_filename = f"Foliado_{base_filename}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    
                    # Usar Response para asegurar el manejo correcto del header Content-Disposition
                    with open(temp_output_path, 'rb') as f:
                        data = f.read()
                    
                    response = Response(data, mimetype='application/pdf')
                    # Esencial para que script.js pueda leer el nombre correcto:
                    response.headers['Content-Disposition'] = f'attachment; filename="{download_filename}"'
                    
                    # 5. Limpieza de archivos después de la descarga exitosa
                    os.remove(temp_input_path)
                    os.remove(temp_output_path)
                    
                    return response
                
                except Exception as e:
                    flash(f'Error al enviar el archivo para descarga: {e}', 'error')
                    
            else:
                flash('Fallo el proceso de foliado. El archivo puede estar cifrado o el rango es inválido.', 'error')
                
        except Exception as e:
            flash(f'Ocurrió un error inesperado durante el procesamiento: {e}', 'error')
            print(f"Error en upload_file: {e}")
            
        finally:
            # Limpieza robusta en caso de fallo intermedio
            if 'temp_input_path' in locals() and os.path.exists(temp_input_path):
                try:
                    os.remove(temp_input_path)
                except OSError:
                    pass # Ya no existe o permisos
            if 'temp_output_path' in locals() and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except OSError:
                    pass # Ya no existe o permisos
                
        return redirect(url_for('upload_file'))

    return render_template(
        'index.html', 
        pdf_processor_available=PDF_PROCESSOR_AVAILABLE,
        pdf_preview_available=PDF_PREVIEW_AVAILABLE
    )


@app.route('/preview', methods=['POST'])
def preview_file():
    if not PDF_PREVIEW_AVAILABLE:
        return "Vista previa no disponible (Poppler missing).", 501
    
    if 'pdf_file' not in request.files or not request.files['pdf_file'].filename:
        return "No se recibió archivo para vista previa.", 400

    file = request.files['pdf_file']
    file_bytes = file.read()
    
    if not file_bytes:
        return "Archivo vacío.", 400

    temp_input_path = None
    temp_output_path = None
    
    try:
        file_id = str(uuid.uuid4())
        temp_input_path = os.path.join(TEMP_FOLDER, f'{file_id}_input_preview.pdf')
        temp_output_path = os.path.join(TEMP_FOLDER, f'{file_id}_output_preview.pdf')
        
        # Guardar el archivo temporalmente
        with open(temp_input_path, 'wb') as f:
            f.write(file_bytes)

        # 2. Obtener parámetros
        start_number = int(request.form.get('start_number_prev', 1))
        
        # Manejo de start_page (si viene vacío, es 1)
        start_page_raw = request.form.get('start_page_prev')
        start_page = int(start_page_raw) if start_page_raw and start_page_raw.isdigit() else 1

        # El end_page para preview siempre será la start_page
        end_page = start_page 
        
        # PARÁMETROS DE ESTILO
        font_size = int(request.form.get('font_size_prev', 16))
        offset_cm = float(request.form.get('offset_prev', 1.0))
        corner = request.form.get('corner_prev', 'bottom-right')
        orientation = request.form.get('orientation_prev', 'horizontal')
        
        # 3. Foliar solo la primera página seleccionada (start_page a end_page=start_page)
        success = agregar_folios_web(
            input_path=temp_input_path,
            output_path=temp_output_path,
            font="Courier-Bold",
            font_size=font_size,
            start_number=start_number,
            offset_cm=offset_cm,
            corner=corner,
            orientation=orientation,
            start_page=start_page,
            end_page=end_page, # Foliar solo esta página
            preview_mode=True
        )
        
        if success and os.path.exists(temp_output_path):
            
            with open(temp_output_path, 'rb') as f:
                pdf_bytes_foliado = f.read()

            # 4. Convertir la página foliada a imagen PNG
            images = convert_from_bytes(
                pdf_file=pdf_bytes_foliado, 
                first_page=1, 
                last_page=1, 
                fmt='png', 
                dpi=72 # OPTIMIZACIÓN
            )
            
            if images:
                # 5. Devolver la imagen PNG binaria usando io.BytesIO
                img_io = images[0]
                img_byte_arr = io.BytesIO()
                img_io.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                # Devuelve el binario directamente
                return send_file(img_byte_arr, mimetype='image/png')
            else:
                return "No se pudo generar la imagen de vista previa.", 500

        else:
            return "Fallo al foliar para la vista previa. ¿Archivo cifrado?", 500
            
    except Exception as e:
        print(f"Error en preview_file: {e}")
        # Devuelve 500 para indicar que el servidor tuvo un problema
        return f"Error en el servidor: {e}", 500
    
    finally:
        # Limpieza de archivos temporales de vista previa
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except OSError:
                pass
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
            except OSError:
                pass


# --- Inicio del Servidor ---

if __name__ == '__main__':
    # 1. Asegurar la existencia de las carpetas
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 2. LIMPIEZA ROBUSTA al inicio
    cleanup_temp_files(hours_old=1)

    print("Servidor Flask corriendo. Accede en: http://localhost:5000/")
    
    # Usar host='0.0.0.0' para que sea accesible desde otras PCs en la red local
    app.run(host='0.0.0.0', debug=True)
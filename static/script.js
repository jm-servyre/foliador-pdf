// static/script.js

document.addEventListener('DOMContentLoaded', function() {
    
    // === ELEMENTOS ===
    const form = document.getElementById('foliator-form'); 
    const fileInput = document.getElementById('pdf_file'); // Input oculto (principal)
    const submitButton = document.getElementById('submit-button');
    const previewImage = document.getElementById('preview-image');
    const previewContainer = document.getElementById('preview-container');
    const previewMessage = document.getElementById('preview-message');

    const dragDropZone = document.getElementById('drag-drop-label');
    const dragFileInput = document.getElementById('pdf_file_drag'); // Input visible de arrastre

    // ELEMENTOS DEL MODAL DE CARGA
    const loadingModal = document.getElementById('loading-modal');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('progress-text');

    // ¡ELEMENTOS CLAVE PARA EL FLUJO!
    const fileUploadSection = document.getElementById('action-row'); 
    const configPreviewSection = document.getElementById('config-and-preview-section'); 
    
    // ELEMENTOS PARA LA ACTUALIZACIÓN DEL FOLIO SIMULADO
    const currentFolioDisplay = document.getElementById('current-folio-number'); 
    const startNumberInput = document.getElementById('start_number'); // Input del número inicial
    const startPageInput = document.getElementById('start_page'); // Input de la página inicial

    // CONSTANTE
    const MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024; // Límite de 2 GB (debe coincidir con app.py)
    
    // CLAVE: Selecciona todos los inputs y selects dentro de las secciones de configuración/estilo
    const controls = document.querySelectorAll('#foliator-form input:not([type="hidden"]):not(#pdf_file), #foliator-form select');
    
    let previewTimeout;
    const DEBOUNCE_DELAY = 750;

    // ----------------------------------------------------------------------
    // --- FUNCIONES DE UTILIDAD ---
    // ----------------------------------------------------------------------

    function updateSimulatedFolio() {
        // Obtener el número inicial (start_number)
        const startNumber = parseInt(startNumberInput.value) || 1;
        
        // Formatear a 4 dígitos con padding de cero (e.g., 1 -> 0001)
        let simulatedFolio = String(startNumber).padStart(4, '0');
        
        // Actualizar el elemento en el HTML
        if (currentFolioDisplay) {
             currentFolioDisplay.textContent = `#${simulatedFolio}`;
        }
    }


    function updateSubmitButtonState() {
        const fileValid = fileInput.files.length > 0 && fileInput.files[0].size <= MAX_FILE_SIZE_BYTES;
        submitButton.disabled = !fileValid;
        return fileValid;
    }
    
    function validateFileSize() {
        if (fileInput.files.length === 0) return true; 

        const file = fileInput.files[0];
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        
        if (file.size > MAX_FILE_SIZE_BYTES) {
            alert(`🚨 ERROR: El archivo excede el límite máximo de ${MAX_FILE_SIZE_BYTES / (1024 * 1024 * 1024)} GB. Tu archivo es de ${fileSizeMB} MB.`);
            
            // Restablecer inputs y vista a la pantalla inicial
            fileInput.value = ''; 
            dragFileInput.value = ''; 
            updateSubmitButtonState();
            
            configPreviewSection.style.display = 'none';
            fileUploadSection.style.display = 'block';

            previewImage.style.display = 'none';
            previewMessage.textContent = 'Sube un PDF para ver la previsualización de la primera página.';
            dragDropZone.innerHTML = '<span class="drag-icon">📁</span> Arrastra tu archivo PDF aquí o haz clic para seleccionar.';
            
            return false;
        }
        
        return true;
    }

    // ----------------------------------------------------------------------
    // --- LÓGICA DE VISTA PREVIA (AJAX) ---
    // ----------------------------------------------------------------------
    function generatePreview() {
        if (fileInput.files.length === 0 || fileInput.files[0].type !== "application/pdf") {
            previewImage.style.display = 'none';
            previewMessage.textContent = 'Sube un PDF para ver la previsualización de la primera página.';
            previewContainer.appendChild(previewMessage); 
            return;
        }
        
        if (!validateFileSize()) {
            return; 
        }

        // Siempre actualiza el número de folio mostrado ANTES de la petición
        updateSimulatedFolio(); 

        clearTimeout(previewTimeout);
        previewTimeout = setTimeout(() => {
            const file = fileInput.files[0];
            const formData = new FormData();
            
            // 1. Añade el archivo
            formData.append('pdf_file', file);
            
            // 2. Añade los controles (usando el sufijo _prev)
            controls.forEach(control => {
                formData.append(control.name + '_prev', control.value);
            });
            
            previewMessage.innerHTML = 'Generando vista previa... <span class="loading">Cargando.</span>';
            previewImage.style.display = 'none';

            fetch('/preview', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    return response.blob(); 
                }
                // Manejo de errores detallado
                return response.text().then(text => {
                    const status = response.status;
                    let error_message = status === 500 ? 'Error interno del servidor (Revisa log de Flask).' : (text || `Estado: ${status}`);
                    throw new Error(error_message);
                });
            })
            .then(imageBlob => {
                const imageUrl = URL.createObjectURL(imageBlob);
                previewImage.src = imageUrl;
                previewMessage.textContent = 'Previsualización de la primera página foliada:';
                previewImage.style.display = 'block';
            })
            .catch(error => {
                console.error('Error en la vista previa:', error);
                previewMessage.innerHTML = `<p style="color:red;">Error: No se pudo generar la vista previa. (${error.message || 'Error desconocido'})</p>`;
                previewImage.style.display = 'none';
            });

        }, DEBOUNCE_DELAY); 
    }
    
    // ----------------------------------------------------------------------
    // --- LÓGICA DE SUBIDA XHR (FOLIAR Y DESCARGAR) ---
    // ----------------------------------------------------------------------
    function handleFileUpload(event) {
        event.preventDefault(); 
        
        if (!validateFileSize()) {
            return; 
        }

        if (fileInput.files.length === 0) return;

        // 1. Mostrar el modal e iniciar barra
        loadingModal.style.display = 'flex';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();

        // 2. Configurar el Evento de Progreso
        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                const percentRound = Math.round(percentComplete);
                progressBar.style.width = percentRound + '%';
                progressText.textContent = percentRound + '%';
            }
        };

        // 3. Configurar la Respuesta del Servidor
        xhr.onload = function() {
            loadingModal.style.display = 'none'; 
            
            if (xhr.status === 200) {
                // Lógica de descarga
                const disposition = xhr.getResponseHeader('Content-Disposition');
                let filename = 'foliado.pdf';
                
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    // Expresión regular para extraer el nombre del archivo
                    const filenameRegex = /filename="?([^";]+)"?/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        // Decodificar el nombre de archivo, eliminando comillas si existen
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }
                
                // Crea un Blob (archivo binario) con el contenido de la respuesta
                const blob = new Blob([xhr.response], { type: 'application/pdf' });
                const url = window.URL.createObjectURL(blob); // Crea una URL temporal para el Blob
                
                // Crea un enlace temporal para forzar la descarga
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                
                // Simula el clic y elimina el enlace
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Libera la URL temporal del Blob
                window.URL.revokeObjectURL(url);
                
                // Recargar para volver a la zona de arrastre inicial
                window.location.reload();
            
            } else if (xhr.status === 302) {
                // Redirección (manejo de errores de Flask como 413)
                alert('La subida fue rechazada. Revisa el mensaje de error en la página.');
                window.location.href = '/'; 
            }
            else {
                // Error general o 500
                alert(`Error ${xhr.status} en el servidor o al procesar el archivo. Por favor, revise el formato y tamaño.`);
                window.location.reload(); 
            }
        };

        // 4. Configurar el Error
        xhr.onerror = function() {
            loadingModal.style.display = 'none';
            alert('Error de red o conexión fallida.');
            window.location.reload();
        };
        
        xhr.open('POST', form.action);
        xhr.responseType = 'arraybuffer'; // Esencial para manejar archivos binarios
        xhr.send(formData);
    }


    // ----------------------------------------------------------------------
    // --- LÓGICA DE DROPZONE Y TRANSICIÓN DE PANTALLAS ---
    // ----------------------------------------------------------------------

    function transferFile(fileList) {
        if (fileList.length > 0) {
            const file = fileList[0];
            
            // 1. Mostrar estado de "Archivo Cargado" y animación temporal
            dragDropZone.classList.add('file-loaded'); 
            dragDropZone.innerHTML = '<span class="drag-icon">⏳</span> Procesando Archivo...'; 
            
            // Transferir el archivo al input oculto principal
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files; 
            
            updateSubmitButtonState();
            
            // 2. Temporizador para la transición de pantallas
            setTimeout(() => {
                
                // Disparar evento change para activar la vista previa
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Ocultar la zona de arrastre principal
                fileUploadSection.style.display = 'none'; 
                
                // Mostrar la sección de configuración y vista previa (activando el grid)
                configPreviewSection.style.display = 'grid'; 
                
                // Limpiar la clase de animación
                dragDropZone.classList.remove('file-loaded');
                
            }, 500); 

        }
    }

    function highlightDropzone(event) {
        event.preventDefault();
        dragDropZone.classList.add('dropzone-highlight');
    }

    function unhighlightDropzone(event) {
        event.preventDefault();
        if (!dragDropZone.classList.contains('file-loaded')) { 
             dragDropZone.classList.remove('dropzone-highlight');
        }
    }

    function handleDrop(event) {
        event.preventDefault();
        unhighlightDropzone(event);

        if (event.dataTransfer.files.length > 0) {
            transferFile(event.dataTransfer.files);
        }
    }

    // ----------------------------------------------------------------------
    // --- CONFIGURAR LISTENERS ---
    // ----------------------------------------------------------------------

    // Subida y foliado final
    form.addEventListener('submit', handleFileUpload); 

    // Escuchar el cambio en el input OCULTO (principal)
    fileInput.addEventListener('change', () => {
        validateFileSize();
        updateSubmitButtonState();
        generatePreview(); 
    });
    
    // Escuchar el cambio en el input VISIBLE DE ARRASTRE (activa la transición)
    dragFileInput.addEventListener('change', function() {
        transferFile(this.files);
    });

    // Escucha cambios en los controles para regenerar la vista previa.
    controls.forEach(control => {
        control.addEventListener('change', generatePreview);
        if (control.type === 'number' || control.type === 'text') {
            control.addEventListener('keyup', generatePreview);
        }
        // Listener extra para actualización inmediata del texto del folio
        control.addEventListener('change', updateSimulatedFolio);
        if (control.type === 'number' || control.type === 'text') {
            control.addEventListener('keyup', updateSimulatedFolio);
        }
    });

    // Listeners de Dropzone (Arrastrar y Soltar)
    if (dragDropZone) {
        dragDropZone.addEventListener('dragover', highlightDropzone);
        dragDropZone.addEventListener('dragleave', unhighlightDropzone);
        dragDropZone.addEventListener('drop', handleDrop);
    }

    // Prevenir el comportamiento por defecto de arrastrar archivos fuera de la zona
    document.body.addEventListener('dragover', (e) => e.preventDefault());
    document.body.addEventListener('drop', (e) => e.preventDefault());

    // Inicializar el estado del botón y el número de folio al cargar la página
    updateSubmitButtonState();
    updateSimulatedFolio(); // Llama para inicializar el número de folio
});
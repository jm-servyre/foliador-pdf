# 📁 Foliador PDF Web (v3)

Aplicación web desarrollada en Python (Flask) para agregar folios (numeración de páginas) de forma segura y personalizada a documentos PDF, permitiendo definir el número inicial, rango de páginas, posición y estilo.

---

## 🚀 Funcionalidades Principales

* **Foliado Selectivo:** Define el número de folio inicial, página de inicio y página final para el proceso.
* **Personalización:** Configura tamaño de fuente, margen (en cm) y esquina de posición (superior/inferior, izquierda/derecha).
* **Vista Previa en Tiempo Real:** Muestra una imagen de la primera página foliada para verificar el estilo antes de la descarga final.
* **Descarga Robusta:** Manejo de archivos binarios para garantizar la descarga correcta del PDF foliado.
* **Control de Versiones (v3):** Código refactorizado para la separación de lógica (pdf_processor.py) y corrección de bugs de caché.

---

## 🛠️ Requisitos e Instalación

### Requisitos del Sistema

1.  **Python 3.x**
2.  **Poppler** (Necesario para la vista previa de PDF a Imagen. Debe ser instalado a nivel de sistema operativo. [Instrucciones de Poppler](https://poppler.freedesktop.org/))

### Pasos de Instalación

1.  **Clonar el Repositorio:**
    ```bash
    git clone [https://github.com/](https://github.com/)[TU_USUARIO]/foliador-pdf-web.git
    cd foliador-pdf-web
    ```
2.  **Crear y Activar Entorno Virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    .\venv\Scripts\activate   # Windows
    ```
3.  **Instalar Dependencias de Python:**
    ```bash
    pip install Flask pypdf reportlab pdf2image
    ```

---

## ▶️ Uso de la Aplicación

1.  **Ejecutar el Servidor Flask:**
    ```bash
    python app.py
    ```
2.  **Acceder:** Abre tu navegador y ve a `http://127.0.0.1:5000/`.
3.  **Procesar:**
    * Arrastra tu PDF a la zona de carga.
    * Configura el número inicial y el rango.
    * Verifica la vista previa.
    * Haz clic en **"Foliar y Descargar PDF"**.

---

## 🧑‍💻 Contacto

Desarrollado por **Jorge Meneses**.

¿Dudas o sugerencias? Contáctame a: <jorge.meneses@servyre.com>

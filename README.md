# Herramienta Multimedia

Aplicación de escritorio en Python para la descarga, conversión y procesamiento de archivos de audio y video. Construida con una arquitectura modular y una interfaz gráfica moderna basada en CustomTkinter.

---

## Características

* **Descarga de Medios:**
  * Descargas desde YouTube, TikTok, Instagram, Twitter/X, SoundCloud y más (mediante `yt-dlp`).
  * Selección de calidad de video (desde 360p hasta 4K / 2160p).
  * Extracción y descarga directa de audio en múltiples formatos (`MP3`, `M4A`, `FLAC`, `WAV`, `OPUS`) con selección de bitrate (hasta 320 kbps).
  * Incrustación automática de carátulas (thumbnail) y metadatos en archivos de audio.
  * Inspección previa con visualización de título, canal, duración y miniatura antes de descargar.
  * Soporte de cookies de navegador para evitar bloqueos y verificaciones bot.

* **Herramientas de Conversión y Edición:**
  * Conversión entre formatos de video (`mp4`, `avi`, `mkv`, `mov`, `webm`, `flv`, `wmv`, `gif`) y audio (`mp3`, `wav`, `m4a`, `flac`, `ogg`, `aac`, `wma`).
  * Reporte de progreso en tiempo real (0% a 100%) durante la conversión.
  * Compresión de video en dos pasadas con ajustes predefinidos para WhatsApp (16 MB / 64 MB), Discord (25 MB / 50 MB) o tamaño personalizado.
  * Recorte de archivos multimedia (inicio y fin).
  * Extracción de audio desde pistas de video con un solo clic.

* **Gestión de Tareas y Experiencia de Usuario:**
  * Cola de tareas en segundo plano para procesar múltiples descargas y conversiones sin bloquear la interfaz.
  * Interfaz moderna con soporte para Modo Oscuro, Modo Claro y sincronización con el sistema.
  * Detección automática de `ffmpeg.exe` y `ffprobe.exe` en rutas locales o en el sistema (sin requerir configuración manual de variables de entorno).

---

## Requisitos

* **Python 3.10+**
* **FFmpeg**: Los binarios (`ffmpeg.exe` y `ffprobe.exe`) pueden ubicarse en la carpeta `ffmpeg/bin/` del proyecto o estar instalados en el PATH del sistema.

---

## Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <CARPETA_DEL_REPOSITORIO>
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación:**
   ```bash
   python main.py
   ```

---

## Compilar a Ejecutable (.exe)

Para empaquetar la aplicación como un ejecutable autónomo para Windows:

```bash
python build_exe.py
```

El ejecutable se generará en la carpeta `dist/DescargarConvertir.exe`.

---

## Estructura del Proyecto

```text
├── src/
│   ├── core/
│   │   ├── ffmpeg_manager.py     # Detección y gestión de binarios FFmpeg
│   │   ├── downloader.py         # Motor de descarga con yt-dlp
│   │   ├── converter.py          # Motor de conversión, compresión y recorte
│   │   └── queue_manager.py      # Gestor de cola de tareas en segundo plano
│   └── ui/
│       ├── app.py                # Ventana principal y barra de estado
│       ├── tab_download.py       # Pestaña de descargas y previsualización
│       ├── tab_convert.py        # Pestaña de conversión y herramientas
│       ├── tab_queue.py          # Pestaña de cola e historial
│       └── tab_settings.py       # Pestaña de configuración
├── main.py                       # Punto de entrada de la aplicación
├── build_exe.py                  # Script de compilación con PyInstaller
├── requirements.txt              # Dependencias de Python
└── .gitignore                    # Archivos y carpetas excluidos del repositorio
```

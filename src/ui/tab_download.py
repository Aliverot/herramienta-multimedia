"""
Pestaña de descargas con previsualización de enlaces multimedia.
"""

import os
import threading
import io
import urllib.request
from pathlib import Path
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image

from src.core.downloader import Downloader, MediaInfo, DownloadProgress
from src.ui.tab_settings import load_config


class TabDownload(ctk.CTkFrame):
    """Pestaña de descarga con inspección previa, miniatura y opciones de calidad."""

    def __init__(self, parent, app):
        """Inicializa la pestaña de descargas."""
        super().__init__(parent)
        self.app = app
        self._downloader: Downloader | None = None
        self.current_media_info: MediaInfo | None = None
        self._thumbnail_image = None  # Mantener referencia para evitar garbage collection

        # Contenedor scrollable
        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # --- a) URL Input ---
        ctk.CTkLabel(
            self.container, text="Enlace URL:", font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 5))

        frame_url = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_url.pack(fill="x", pady=(0, 15))

        self.entry_url = ctk.CTkEntry(
            frame_url,
            placeholder_text="Pega aquí el enlace de YouTube, TikTok, Instagram...",
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_url.bind("<Return>", lambda event: self._inspect_url())

        self.btn_paste = ctk.CTkButton(
            frame_url,
            text="📋 Pegar",
            width=75,
            command=self._paste_url,
        )
        self.btn_paste.pack(side="left", padx=(0, 5))

        self.btn_clear = ctk.CTkButton(
            frame_url,
            text="✕",
            width=35,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self._clear_url,
        )
        self.btn_clear.pack(side="left", padx=(0, 5))

        self.btn_inspect = ctk.CTkButton(
            frame_url, text="🔍 Inspeccionar", width=120, command=self._inspect_url
        )
        self.btn_inspect.pack(side="right")

        # --- b) Preview Card (oculta inicialmente) ---
        self.frame_preview = ctk.CTkFrame(
            self.container, border_width=1, corner_radius=8
        )

        self.lbl_thumbnail = ctk.CTkLabel(
            self.frame_preview, text="Cargando...", width=160, height=90
        )
        self.lbl_thumbnail.grid(row=0, column=0, rowspan=4, padx=10, pady=10)

        self.lbl_title = ctk.CTkLabel(
            self.frame_preview,
            text="Título: ...",
            font=("Segoe UI", 12, "bold"),
            wraplength=400,
            justify="left",
        )
        self.lbl_title.grid(row=0, column=1, sticky="nw", padx=(0, 10), pady=(10, 0))

        self.lbl_channel = ctk.CTkLabel(self.frame_preview, text="Canal: ...")
        self.lbl_channel.grid(row=1, column=1, sticky="w", padx=(0, 10))

        self.lbl_duration = ctk.CTkLabel(self.frame_preview, text="Duración: ...")
        self.lbl_duration.grid(row=2, column=1, sticky="w", padx=(0, 10))

        self.lbl_platform = ctk.CTkLabel(self.frame_preview, text="Plataforma: ...")
        self.lbl_platform.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=(0, 10))

        self.frame_preview.columnconfigure(1, weight=1)

        # --- c) Options Section ---
        self.frame_options = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frame_options.pack(fill="x", pady=(0, 15))
        self.frame_options.grid_columnconfigure(0, weight=1)
        self.frame_options.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_options, text="Tipo de descarga:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self.var_type = ctk.StringVar(value="Video (MP4)")
        self.opt_type = ctk.CTkOptionMenu(
            self.frame_options,
            variable=self.var_type,
            values=[
                "Canción (Audio MP3)",
                "Video (MP4)",
                "Playlist Audio",
                "Playlist Video",
            ],
            command=self._on_type_change,
        )
        self.opt_type.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(self.frame_options, text="Calidad:").grid(
            row=0, column=1, sticky="w", pady=(0, 5)
        )

        self.var_quality = ctk.StringVar(value="Mejor disponible")
        self.opt_quality = ctk.CTkOptionMenu(
            self.frame_options,
            variable=self.var_quality,
            values=[
                "Mejor disponible",
                "2160p (4K)",
                "1440p (2K)",
                "1080p",
                "720p",
                "480p",
                "360p",
            ],
        )
        self.opt_quality.grid(row=1, column=1, sticky="ew")

        # --- d) Audio Options (ocultas por defecto) ---
        self.frame_audio = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frame_audio.grid_columnconfigure(0, weight=1)
        self.frame_audio.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_audio, text="Formato de audio:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        cfg = load_config()
        self.var_audio_fmt = ctk.StringVar(value=cfg.get("audio_format", "mp3"))
        ctk.CTkOptionMenu(
            self.frame_audio,
            variable=self.var_audio_fmt,
            values=["mp3", "m4a", "flac", "wav", "opus"],
        ).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(self.frame_audio, text="Calidad de audio:").grid(
            row=0, column=1, sticky="w", pady=(0, 5)
        )
        bitrate_cfg = str(cfg.get("audio_bitrate", "192")).replace(" kbps", "").replace("k", "")
        init_qual = f"{bitrate_cfg} kbps"
        self.var_audio_qual = ctk.StringVar(value=init_qual)
        ctk.CTkOptionMenu(
            self.frame_audio,
            variable=self.var_audio_qual,
            values=["128 kbps", "192 kbps", "256 kbps", "320 kbps"],
        ).grid(row=1, column=1, sticky="ew")

        self.var_embed_thumbnail = ctk.BooleanVar(value=bool(cfg.get("embed_thumbnail", True)))
        ctk.CTkCheckBox(
            self.frame_audio,
            text="Incrustar carátula",
            variable=self.var_embed_thumbnail,
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.var_embed_meta = ctk.BooleanVar(value=bool(cfg.get("embed_metadata", True)))
        ctk.CTkCheckBox(
            self.frame_audio,
            text="Incrustar metadatos",
            variable=self.var_embed_meta,
        ).grid(row=2, column=1, sticky="w", pady=(10, 0))

        # --- e) Destination ---
        ctk.CTkLabel(
            self.container, text="Guardar en:", font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(15, 5))

        frame_dest = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_dest.pack(fill="x", pady=(0, 15))

        default_path = cfg.get("download_folder") or str(Path.home() / "Downloads")
        self.var_dest = ctk.StringVar(value=default_path)
        ctk.CTkEntry(
            frame_dest, textvariable=self.var_dest, state="disabled"
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            frame_dest, text="📂 Cambiar", command=self._select_folder
        ).pack(side="right")

        # --- f) Action Buttons ---
        frame_actions = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_actions.pack(fill="x", pady=(15, 0))

        self.btn_download = ctk.CTkButton(
            frame_actions,
            text="⬇️ Descargar Ahora",
            fg_color="#28a745",
            hover_color="#218838",
            command=self._start_download,
        )
        self.btn_download.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_queue = ctk.CTkButton(
            frame_actions,
            text="📋 Añadir a Cola",
            fg_color="#007bff",
            hover_color="#0069d9",
            command=self._add_to_queue,
        )
        self.btn_queue.pack(side="right", fill="x", expand=True)

    # ──────────── Métodos ────────────

    def _get_clipboard_content(self) -> tuple[str | None, str | None]:
        """
        Lee el portapapeles de manera resiliente en Windows.
        Retorna (texto_extraido, mensaje_explicativo_si_no_hay_texto).
        """
        # 1. Intentar primero con Tkinter
        try:
            val = self.clipboard_get()
            if val and val.strip():
                return val.strip(), None
        except Exception:
            pass

        # 2. Intentar vía API Win32 (ctypes) para evitar bloqueos temporales o problemas de formato
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                import time

                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                user32.OpenClipboard.argtypes = [wintypes.HWND]
                user32.OpenClipboard.restype = wintypes.BOOL
                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = wintypes.BOOL
                user32.GetClipboardData.argtypes = [wintypes.UINT]
                user32.GetClipboardData.restype = wintypes.HANDLE
                kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalLock.restype = wintypes.LPVOID
                kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalUnlock.restype = wintypes.BOOL

                # Reintentar un par de veces si otra aplicación tiene el portapapeles abierto
                for _ in range(3):
                    if user32.OpenClipboard(None):
                        try:
                            CF_UNICODETEXT = 13
                            h_glb = user32.GetClipboardData(CF_UNICODETEXT)
                            if h_glb:
                                p_glb = kernel32.GlobalLock(h_glb)
                                if p_glb:
                                    try:
                                        val_win = ctypes.c_wchar_p(p_glb).value
                                        if val_win and val_win.strip():
                                            return val_win.strip(), None
                                    finally:
                                        kernel32.GlobalUnlock(h_glb)
                        finally:
                            user32.CloseClipboard()
                    time.sleep(0.04)

                # Si no hubo texto, detectar el contenido real del portapapeles
                CF_BITMAP = 2
                CF_DIB = 8
                CF_DIBV5 = 17
                CF_HDROP = 15
                if (
                    user32.IsClipboardFormatAvailable(CF_BITMAP)
                    or user32.IsClipboardFormatAvailable(CF_DIB)
                    or user32.IsClipboardFormatAvailable(CF_DIBV5)
                ):
                    return None, (
                        "El portapapeles contiene una imagen o captura de pantalla, no texto.\n\n"
                        "Por favor copia primero la dirección URL del video (Ctrl + C) antes de presionar 'Pegar'."
                    )
                if user32.IsClipboardFormatAvailable(CF_HDROP):
                    return None, (
                        "El portapapeles contiene un archivo del Explorador de Windows, no un enlace.\n\n"
                        "Copia la URL del video con Ctrl + C y vuelve a intentarlo."
                    )
            except Exception:
                pass

        return None, (
            "El portapapeles está vacío o no contiene texto legible.\n\n"
            "Copia un enlace URL en tu navegador (Ctrl + C) y vuelve a presionar '📋 Pegar'."
        )

    def _paste_url(self):
        """Pega el contenido del portapapeles en el campo de URL e inicia la inspección."""
        text, err_msg = self._get_clipboard_content()
        if text:
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, text)
            self._inspect_url()
        else:
            messagebox.showinfo("Portapapeles", err_msg or "No se pudo leer texto del portapapeles.")

    def _clear_url(self):
        """Limpia el campo de URL y oculta la tarjeta de previsualización."""
        self.entry_url.delete(0, "end")
        self.frame_preview.pack_forget()
        self.current_media_info = None
        self._thumbnail_image = None
        self.btn_inspect.configure(state="normal", text="🔍 Inspeccionar")

    def _inspect_url(self):
        """Inspecciona un enlace para obtener metadatos y miniatura."""
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa un enlace URL.")
            return

        self.btn_inspect.configure(state="disabled", text="Inspeccionando...")
        self.frame_preview.pack(fill="x", pady=(0, 15), before=self.frame_options)
        self.lbl_thumbnail.configure(image=None, text="Cargando...")
        self.lbl_title.configure(text="Título: Cargando...")
        self.lbl_channel.configure(text="Canal: Cargando...")
        self.lbl_duration.configure(text="Duración: Cargando...")
        self.lbl_platform.configure(text="Plataforma: Cargando...")

        def thread_target():
            try:
                downloader = Downloader()
                info = downloader.extract_info(url)
                self.current_media_info = info
                self.after(0, lambda: self._update_preview(info))
            except Exception as e:
                self.after(0, lambda: self._inspect_error(str(e)))

        threading.Thread(target=thread_target, daemon=True).start()

    def _update_preview(self, info: MediaInfo):
        """Actualiza la tarjeta de previsualización con los datos extraídos."""
        self.btn_inspect.configure(state="normal", text="🔍 Inspeccionar")
        self.lbl_title.configure(text=f"Título: {info.title}")
        self.lbl_channel.configure(text=f"Canal: {info.channel}")
        self.lbl_duration.configure(text=f"Duración: {info.duration_str}")
        self.lbl_platform.configure(text=f"Plataforma: {info.platform.capitalize()}")

        # Cargar miniatura en segundo plano
        if info.thumbnail_url:
            threading.Thread(
                target=self._load_thumbnail, args=(info.thumbnail_url,), daemon=True
            ).start()
        else:
            self.lbl_thumbnail.configure(text="Sin carátula")

        # Actualizar formatos disponibles en el selector de calidad
        if info.formats_available and not info.is_playlist:
            quality_values = ["Mejor disponible"] + info.formats_available
            self.opt_quality.configure(values=quality_values)

    def _load_thumbnail(self, url: str):
        """Descarga y muestra la miniatura del video."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as u:
                raw_data = u.read()
            img = Image.open(io.BytesIO(raw_data))
            img.thumbnail((160, 90), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(160, 90)
            )
            # Guardar referencia para evitar GC
            self._thumbnail_image = ctk_img
            self.after(0, lambda: self.lbl_thumbnail.configure(image=ctk_img, text=""))
        except Exception:
            self.after(0, lambda: self.lbl_thumbnail.configure(text="Error al cargar"))

    def _inspect_error(self, error_msg: str):
        """Maneja errores durante la inspección."""
        self.btn_inspect.configure(state="normal", text="🔍 Inspeccionar")
        self.frame_preview.pack_forget()
        self.app.update_status("Estado: Error al inspeccionar enlace", "#dc3545")

        hint = ""
        lower_err = error_msg.lower()
        if (
            "unavailable" in lower_err
            or "no disponible" in lower_err
            or "removed" in lower_err
            or "private video" in lower_err
            or "not available" in lower_err
        ):
            hint = (
                "\n\n💡 Causa: Este video ya no está disponible en YouTube.\n"
                "El creador lo ha eliminado, lo ha puesto como privado o no está disponible en tu región."
            )
        elif "sign in" in lower_err or "bot" in lower_err or "login" in lower_err:
            hint = (
                "\n\n💡 Sugerencia: YouTube requiere verificación anti-bot. "
                "Puedes configurar cookies en la pestaña '⚙️ Ajustes'."
            )
        elif "403" in lower_err or "forbidden" in lower_err:
            hint = (
                "\n\n💡 Sugerencia: Error de acceso (403 Forbidden). "
                "Prueba configurando cookies de navegador en '⚙️ Ajustes'."
            )

        clean_err = error_msg.replace("ERROR: ", "").strip()
        messagebox.showerror(
            "Error de Inspección",
            f"No se pudo obtener información del enlace:\n\n{clean_err}{hint}",
        )

    def _on_type_change(self, value: str):
        """Cambia las opciones visibles según el tipo de descarga seleccionado."""
        is_audio = "Audio" in value or "Canción" in value
        if is_audio:
            self.frame_audio.pack(fill="x", pady=(0, 15), after=self.frame_options)
            self.opt_quality.configure(
                values=["Mejor disponible", "320 kbps", "256 kbps", "192 kbps", "128 kbps"]
            )
            self.var_quality.set("Mejor disponible")
        else:
            self.frame_audio.pack_forget()
            self.opt_quality.configure(
                values=[
                    "Mejor disponible",
                    "2160p (4K)",
                    "1440p (2K)",
                    "1080p",
                    "720p",
                    "480p",
                    "360p",
                ]
            )
            self.var_quality.set("Mejor disponible")

    def _select_folder(self):
        """Abre diálogo para seleccionar carpeta de destino."""
        folder = filedialog.askdirectory(initialdir=self.var_dest.get())
        if folder:
            self.var_dest.set(folder)

    def reload_config(self):
        """Recarga en caliente las preferencias guardadas desde la configuración."""
        cfg = load_config()
        new_folder = cfg.get("download_folder")
        if new_folder and os.path.isdir(new_folder):
            self.var_dest.set(new_folder)

        self.var_audio_fmt.set(cfg.get("audio_format", "mp3"))
        bitrate_cfg = str(cfg.get("audio_bitrate", "192")).replace(" kbps", "").replace("k", "")
        self.var_audio_qual.set(f"{bitrate_cfg} kbps")
        self.var_embed_thumbnail.set(bool(cfg.get("embed_thumbnail", True)))
        self.var_embed_meta.set(bool(cfg.get("embed_metadata", True)))

    def _get_download_params(self) -> dict:
        """Recopila los parámetros de descarga desde la interfaz."""
        type_val = self.var_type.get()
        is_audio = "Audio" in type_val or "Canción" in type_val
        is_playlist = "Playlist" in type_val

        quality = self.var_quality.get()
        if quality == "Mejor disponible":
            format_quality = "best"
        else:
            # Extraer "1080" de "1080p" o "320" de "320 kbps"
            format_quality = quality.split("p")[0].split(" ")[0]
            if not format_quality.replace("p", "").isdigit():
                format_quality = "best"
            else:
                format_quality = format_quality + "p" if "kbps" not in quality else format_quality

        # Obtener cookies del tab de ajustes si existe
        cookies_browser = None
        if hasattr(self.app, "tab_settings"):
            cookies_browser = self.app.tab_settings.get_cookies_browser()

        return {
            "url": self.entry_url.get().strip(),
            "output_dir": self.var_dest.get(),
            "media_type": "audio" if is_audio else "video",
            "format_quality": format_quality if not is_audio else "best",
            "is_playlist": is_playlist,
            "audio_bitrate": self.var_audio_qual.get().split(" ")[0] if is_audio else "192",
            "audio_format": self.var_audio_fmt.get() if is_audio else "mp3",
            "embed_thumbnail": self.var_embed_thumbnail.get(),
            "embed_metadata": self.var_embed_meta.get(),
            "cookies_browser": cookies_browser,
        }

    def _start_download(self):
        """Inicia la descarga en un hilo separado."""
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa un enlace URL.")
            return

        params = self._get_download_params()

        self.btn_download.configure(state="disabled")
        self.btn_queue.configure(state="disabled")
        self.app.update_status("Estado: Preparando descarga...", "#007bff")
        self.app.update_progress(0)

        def on_cancel():
            if self._downloader:
                self._downloader.cancel()

        self.app.enable_cancel(on_cancel)

        def thread_target():
            try:
                self._downloader = Downloader()
                success = self._downloader.download(
                    url=params["url"],
                    output_dir=params["output_dir"],
                    media_type=params["media_type"],
                    format_quality=params["format_quality"],
                    is_playlist=params["is_playlist"],
                    audio_bitrate=params["audio_bitrate"],
                    audio_format=params["audio_format"],
                    embed_thumbnail=params["embed_thumbnail"],
                    embed_metadata=params["embed_metadata"],
                    cookies_browser=params["cookies_browser"],
                    progress_callback=self._on_download_progress,
                )
                self.after(0, lambda: self._download_complete(success))
            except Exception as e:
                self.after(0, lambda: self._download_error(str(e)))

        threading.Thread(target=thread_target, daemon=True).start()

    def _on_download_progress(self, progress: DownloadProgress):
        """Callback de progreso de descarga (llamado desde hilo)."""
        def update():
            self.app.update_progress(progress.percent / 100.0)
            if progress.status == "downloading":
                self.app.update_status(
                    f"Descargando: {progress.percent:.1f}% | {progress.speed} | ETA: {progress.eta}",
                    "#007bff",
                )
            elif progress.status == "converting":
                self.app.update_status("Procesando archivo...", "#ffc107")
        self.after(0, update)

    def _download_complete(self, success: bool):
        """Maneja la finalización de la descarga."""
        self.btn_download.configure(state="normal")
        self.btn_queue.configure(state="normal")
        self.app.disable_cancel()

        last_error = getattr(self._downloader, "last_error", None) if self._downloader else None
        was_cancelled = getattr(self._downloader, "is_cancelled", False) if self._downloader else False
        self._downloader = None

        if success:
            self.app.update_status("Estado: ¡Descarga completada!", "#28a745")
            self.app.update_progress(1.0)
            resp = messagebox.askyesno(
                "Éxito",
                f"Descarga completada.\nGuardado en:\n{self.var_dest.get()}\n\n¿Deseas abrir la carpeta?",
            )
            if resp:
                try:
                    os.startfile(self.var_dest.get())
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")
        elif was_cancelled:
            self.app.update_status("Estado: Descarga cancelada por el usuario", "#ffc107")
            self.app.update_progress(0)
        else:
            err_msg = last_error or "Ocurrió un error inesperado al descargar el contenido."
            self._download_error(err_msg)

    def _download_error(self, error_msg: str):
        """Maneja errores durante la descarga con sugerencias útiles."""
        self.btn_download.configure(state="normal")
        self.btn_queue.configure(state="normal")
        self.app.disable_cancel()
        self.app.update_status("Estado: Error en la descarga", "#dc3545")
        self.app.update_progress(0)
        self._downloader = None

        hint = ""
        lower_err = error_msg.lower()
        if (
            "unavailable" in lower_err
            or "no disponible" in lower_err
            or "removed" in lower_err
            or "private video" in lower_err
            or "not available" in lower_err
        ):
            hint = (
                "\n\n💡 Motivo: El video ya no está disponible en YouTube.\n"
                "El creador lo ha eliminado, lo ha puesto en modo privado o está bloqueado en tu región."
            )
        elif "sign in" in lower_err or "bot" in lower_err or "login" in lower_err:
            hint = (
                "\n\n💡 Sugerencia: YouTube suele solicitar confirmación anti-bot. "
                "Puedes habilitar las cookies de tu navegador en la pestaña '⚙️ Ajustes'."
            )
        elif "403" in lower_err or "forbidden" in lower_err:
            hint = (
                "\n\n💡 Sugerencia: Error de acceso (403 Forbidden). "
                "YouTube denegó la descarga directa. Prueba configurando cookies en '⚙️ Ajustes'."
            )
        elif "cookie" in lower_err and ("database" in lower_err or "could not copy" in lower_err):
            hint = (
                "\n\n💡 Motivo: El navegador seleccionado tiene su archivo de cookies bloqueado "
                "(suele ocurrir si el navegador está abierto).\n"
                "Sugerencia: Cambia 'Cookies del Navegador' a 'ninguno' en la pestaña '⚙️ Ajustes' o cierra el navegador."
            )

        clean_err = error_msg.replace("ERROR: ", "").strip()
        messagebox.showerror(
            "Error en la Descarga",
            f"Ocurrió un error durante la descarga:\n\n{clean_err}{hint}",
        )

    def _add_to_queue(self):
        """Añade la descarga actual a la cola de tareas."""
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingresa un enlace URL.")
            return

        params = self._get_download_params()
        title = (
            self.current_media_info.title
            if self.current_media_info
            else url[:50]
        )

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            from src.core.queue_manager import TaskType

            queue_mgr.add_task(TaskType.DOWNLOAD, f"⬇️ {title}", params)
            messagebox.showinfo("Cola", f"'{title}' añadido a la cola de descargas.")
            self.app.update_status("Elemento añadido a la cola", "gray")

            # Refrescar vista de cola
            if hasattr(self.app, "tab_queue"):
                self.app.tab_queue.refresh_tasks()
        else:
            messagebox.showinfo("Cola", "El gestor de cola no está disponible.")

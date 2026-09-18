"""
Pestaña de conversión, compresión, recorte y extracción de audio.
"""

import os
import threading
import tkinter.filedialog as filedialog
from tkinter import messagebox
import customtkinter as ctk

from src.core.converter import (
    Converter,
    ConversionProgress,
    FORMATOS_VIDEO,
    FORMATOS_AUDIO,
    PRESETS_COMPRESION,
)


class TabConvert(ctk.CTkFrame):
    """Pestaña de herramientas de conversión multimedia."""

    def __init__(self, parent, app):
        """Inicializa la pestaña con sub-pestañas de herramientas."""
        super().__init__(parent)
        self.app = app
        self._converter: Converter | None = None

        from src.ui.tab_settings import load_config
        self._default_dest = load_config().get("download_folder") or os.getcwd()

        # Sub-pestañas
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_convert = self.tabview.add("🔄 Convertir")
        self.tab_compress = self.tabview.add("📦 Comprimir")
        self.tab_trim = self.tabview.add("✂️ Recortar")
        self.tab_extract = self.tabview.add("🎵 Extraer Audio")

        self._setup_convert_tab()
        self._setup_compress_tab()
        self._setup_trim_tab()
        self._setup_extract_tab()

    # ─────────── Sub-tab: Convertir ───────────

    def _setup_convert_tab(self):
        frame = self.tab_convert

        ctk.CTkLabel(frame, text="Archivo de origen:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        src_frame = ctk.CTkFrame(frame, fg_color="transparent")
        src_frame.pack(fill="x", padx=10, pady=5)

        self.conv_src_var = ctk.StringVar()
        self.conv_dest_dir_var = ctk.StringVar(value=self._default_dest)

        ctk.CTkEntry(src_frame, textvariable=self.conv_src_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            src_frame,
            text="Buscar...",
            width=100,
            command=lambda: self._select_file(
                self.conv_src_var, self.conv_dest_dir_var, update_formats=True
            ),
        ).pack(side="right")

        ctk.CTkLabel(frame, text="Convertir a formato:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        self.conv_format_var = ctk.StringVar()
        self.conv_format_menu = ctk.CTkOptionMenu(
            frame, variable=self.conv_format_var, values=["Seleccione un archivo primero"]
        )
        self.conv_format_menu.pack(anchor="w", padx=10, pady=5)
        self.conv_format_menu.configure(state="disabled")

        ctk.CTkLabel(frame, text="Guardar en:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        dest_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkEntry(dest_frame, textvariable=self.conv_dest_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            dest_frame,
            text="📂 Cambiar",
            width=100,
            command=lambda: self._select_folder(self.conv_dest_dir_var),
        ).pack(side="right")

        btn_action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=10, pady=20)

        self.btn_convert = ctk.CTkButton(
            btn_action_frame,
            text="🔄 Convertir Ahora",
            height=40,
            font=("Segoe UI", 13, "bold"),
            command=self._start_conversion,
        )
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_queue_convert = ctk.CTkButton(
            btn_action_frame,
            text="📋 Añadir a Cola",
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#007bff",
            hover_color="#0069d9",
            command=self._queue_conversion,
        )
        self.btn_queue_convert.pack(side="right", fill="x", expand=True)

    # ─────────── Sub-tab: Comprimir ───────────

    def _setup_compress_tab(self):
        frame = self.tab_compress

        ctk.CTkLabel(frame, text="Archivo de origen:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        src_frame = ctk.CTkFrame(frame, fg_color="transparent")
        src_frame.pack(fill="x", padx=10, pady=5)

        self.comp_src_var = ctk.StringVar()
        self.comp_dest_dir_var = ctk.StringVar(value=self._default_dest)

        ctk.CTkEntry(src_frame, textvariable=self.comp_src_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            src_frame,
            text="Buscar...",
            width=100,
            command=lambda: self._select_file(self.comp_src_var, self.comp_dest_dir_var),
        ).pack(side="right")

        ctk.CTkLabel(frame, text="Preset de compresión:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )

        preset_labels = [v["label"] for v in PRESETS_COMPRESION.values()]
        self.comp_preset_var = ctk.StringVar(value=preset_labels[0])
        ctk.CTkOptionMenu(
            frame,
            variable=self.comp_preset_var,
            values=preset_labels,
            command=self._on_preset_change,
        ).pack(anchor="w", padx=10, pady=5)

        # Custom size frame (oculto)
        self.comp_custom_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctk.CTkLabel(self.comp_custom_frame, text="Tamaño máximo (MB):").pack(
            side="left", padx=(0, 10)
        )
        self.comp_custom_size_var = ctk.StringVar(value="10")
        ctk.CTkEntry(
            self.comp_custom_frame, textvariable=self.comp_custom_size_var, width=100
        ).pack(side="left")

        ctk.CTkLabel(frame, text="Guardar en:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        dest_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkEntry(dest_frame, textvariable=self.comp_dest_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            dest_frame,
            text="📂 Cambiar",
            width=100,
            command=lambda: self._select_folder(self.comp_dest_dir_var),
        ).pack(side="right")

        btn_action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=10, pady=20)

        self.btn_compress = ctk.CTkButton(
            btn_action_frame,
            text="📦 Comprimir Ahora",
            height=40,
            font=("Segoe UI", 13, "bold"),
            command=self._start_compression,
        )
        self.btn_compress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_queue_compress = ctk.CTkButton(
            btn_action_frame,
            text="📋 Añadir a Cola",
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#007bff",
            hover_color="#0069d9",
            command=self._queue_compression,
        )
        self.btn_queue_compress.pack(side="right", fill="x", expand=True)

    # ─────────── Sub-tab: Recortar ───────────

    def _setup_trim_tab(self):
        frame = self.tab_trim

        ctk.CTkLabel(frame, text="Archivo de origen:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        src_frame = ctk.CTkFrame(frame, fg_color="transparent")
        src_frame.pack(fill="x", padx=10, pady=5)

        self.trim_src_var = ctk.StringVar()
        self.trim_dest_dir_var = ctk.StringVar(value=self._default_dest)

        ctk.CTkEntry(src_frame, textvariable=self.trim_src_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            src_frame,
            text="Buscar...",
            width=100,
            command=lambda: self._select_file(self.trim_src_var, self.trim_dest_dir_var),
        ).pack(side="right")

        time_frame = ctk.CTkFrame(frame, fg_color="transparent")
        time_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(time_frame, text="Tiempo de inicio:", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.trim_start_var = ctk.StringVar()
        ctk.CTkEntry(
            time_frame, textvariable=self.trim_start_var, placeholder_text="HH:MM:SS o MM:SS"
        ).grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(time_frame, text="Tiempo de fin:", font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.trim_end_var = ctk.StringVar()
        ctk.CTkEntry(
            time_frame, textvariable=self.trim_end_var, placeholder_text="HH:MM:SS o MM:SS"
        ).grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Guardar en:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        dest_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkEntry(dest_frame, textvariable=self.trim_dest_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            dest_frame,
            text="📂 Cambiar",
            width=100,
            command=lambda: self._select_folder(self.trim_dest_dir_var),
        ).pack(side="right")

        btn_action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=10, pady=20)

        self.btn_trim = ctk.CTkButton(
            btn_action_frame,
            text="✂️ Recortar Ahora",
            height=40,
            font=("Segoe UI", 13, "bold"),
            command=self._start_trim,
        )
        self.btn_trim.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_queue_trim = ctk.CTkButton(
            btn_action_frame,
            text="📋 Añadir a Cola",
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#007bff",
            hover_color="#0069d9",
            command=self._queue_trim,
        )
        self.btn_queue_trim.pack(side="right", fill="x", expand=True)

    # ─────────── Sub-tab: Extraer Audio ───────────

    def _setup_extract_tab(self):
        frame = self.tab_extract

        ctk.CTkLabel(
            frame, text="Archivo de origen (Video):", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(10, 0), padx=10)
        src_frame = ctk.CTkFrame(frame, fg_color="transparent")
        src_frame.pack(fill="x", padx=10, pady=5)

        self.ext_src_var = ctk.StringVar()
        self.ext_dest_dir_var = ctk.StringVar(value=self._default_dest)

        ctk.CTkEntry(src_frame, textvariable=self.ext_src_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            src_frame,
            text="Buscar...",
            width=100,
            command=lambda: self._select_file(self.ext_src_var, self.ext_dest_dir_var),
        ).pack(side="right")

        options_frame = ctk.CTkFrame(frame, fg_color="transparent")
        options_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(options_frame, text="Formato de salida:", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.ext_format_var = ctk.StringVar(value="mp3")
        ctk.CTkOptionMenu(
            options_frame,
            variable=self.ext_format_var,
            values=["mp3", "aac", "m4a", "flac", "wav", "ogg"],
        ).grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(options_frame, text="Calidad:", font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.ext_quality_var = ctk.StringVar(value="192 kbps")
        ctk.CTkOptionMenu(
            options_frame,
            variable=self.ext_quality_var,
            values=["128 kbps", "192 kbps", "256 kbps", "320 kbps"],
        ).grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Guardar en:", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        dest_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkEntry(dest_frame, textvariable=self.ext_dest_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        ctk.CTkButton(
            dest_frame,
            text="📂 Cambiar",
            width=100,
            command=lambda: self._select_folder(self.ext_dest_dir_var),
        ).pack(side="right")

        btn_action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=10, pady=20)

        self.btn_extract = ctk.CTkButton(
            btn_action_frame,
            text="🎵 Extraer Audio Ahora",
            height=40,
            font=("Segoe UI", 13, "bold"),
            command=self._start_extraction,
        )
        self.btn_extract.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_queue_extract = ctk.CTkButton(
            btn_action_frame,
            text="📋 Añadir a Cola",
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#007bff",
            hover_color="#0069d9",
            command=self._queue_extraction,
        )
        self.btn_queue_extract.pack(side="right", fill="x", expand=True)

    # ─────────── Métodos comunes ───────────

    def _select_file(self, var: ctk.StringVar, dest_var: ctk.StringVar | None = None, update_formats: bool = False):
        """Abre diálogo de selección de archivo."""
        filepath = filedialog.askopenfilename(title="Seleccionar archivo")
        if filepath:
            var.set(filepath)
            if dest_var is not None:
                dest_var.set(os.path.dirname(filepath))
            if update_formats:
                self._update_format_options(filepath)

    def _select_folder(self, var: ctk.StringVar):
        """Abre diálogo de selección de carpeta."""
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            var.set(folder)

    def _update_format_options(self, filepath: str):
        """Actualiza las opciones de formato según el tipo de archivo seleccionado."""
        ext = os.path.splitext(filepath)[1].lower().lstrip(".")
        is_video = ext in FORMATOS_VIDEO
        is_audio = ext in FORMATOS_AUDIO

        options = []
        if is_video:
            options += [f"🎥 Video: {f}" for f in FORMATOS_VIDEO if f != ext]
            options += [f"🎵 Audio: {f}" for f in FORMATOS_AUDIO]
        elif is_audio:
            options += [f"🎵 Audio: {f}" for f in FORMATOS_AUDIO if f != ext]
        else:
            options += [f"🎥 Video: {f}" for f in FORMATOS_VIDEO]
            options += [f"🎵 Audio: {f}" for f in FORMATOS_AUDIO]

        if options:
            self.conv_format_menu.configure(state="normal", values=options)
            self.conv_format_var.set(options[0])
        else:
            self.conv_format_menu.configure(state="disabled", values=["Formato no soportado"])
            self.conv_format_var.set("Formato no soportado")

    def _on_preset_change(self, value: str):
        """Muestra/oculta campo de tamaño personalizado."""
        if value == "Personalizado":
            self.comp_custom_frame.pack(anchor="w", padx=10, pady=5)
        else:
            self.comp_custom_frame.pack_forget()

    def _get_preset_key(self, label: str) -> str:
        """Obtiene la clave del preset a partir de su etiqueta visible."""
        for key, val in PRESETS_COMPRESION.items():
            if val["label"] == label:
                return key
        return "custom"

    # ─────────── Operaciones en hilo ───────────

    def _on_progress(self, progress: ConversionProgress):
        """Callback de progreso (llamado desde hilo de trabajo)."""
        def update_ui():
            self.app.update_progress(progress.percent / 100.0)
            status_text = f"{progress.status.capitalize()}: {progress.percent:.0f}%"
            if progress.eta:
                status_text += f" | ETA: {progress.eta}"
            if progress.elapsed_time:
                status_text += f" | Transcurrido: {progress.elapsed_time}"
            self.app.update_status(status_text, "#007bff")
        self.after(0, update_ui)

    def _on_complete(self, success: bool, operation: str):
        """Maneja la finalización de una operación."""
        def update_ui():
            self.app.disable_cancel()
            self.app.update_progress(1.0 if success else 0.0)
            was_cancelled = getattr(self._converter, "is_cancelled", False) if self._converter else False
            if success:
                self.app.update_status(f"Estado: ¡{operation} completada!", "#28a745")
                messagebox.showinfo("Éxito", f"La operación '{operation}' se completó con éxito.")
            elif was_cancelled:
                self.app.update_status(f"Estado: {operation} cancelada por el usuario", "#ffc107")
            else:
                err_detail = ""
                if self._converter and getattr(self._converter, "last_error", None):
                    err_detail = f"\n\nDetalle técnico:\n{self._converter.last_error[:250]}"
                self.app.update_status(f"Estado: Error en {operation}", "#dc3545")
                messagebox.showerror("Error", f"Ocurrió un error en la operación '{operation}'.{err_detail}")
            self._converter = None
        self.after(0, update_ui)

    def _setup_cancel(self):
        """Configura el botón de cancelar para la operación actual."""
        def on_cancel():
            if self._converter:
                self._converter.cancel()
        self.app.enable_cancel(on_cancel)

    def _start_conversion(self):
        """Inicia la conversión de formato."""
        src = self.conv_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        fmt_val = self.conv_format_var.get()
        if not fmt_val or "no soportado" in fmt_val.lower():
            messagebox.showerror("Error", "Seleccione un formato de destino válido.")
            return

        dest_dir = self.conv_dest_dir_var.get()
        target_fmt = fmt_val.split(": ")[-1]
        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}.{target_fmt}"
        out_path = os.path.join(dest_dir, out_filename)

        self.app.update_status("Estado: Iniciando conversión...", "#007bff")
        self._setup_cancel()

        def worker():
            try:
                self._converter = Converter()
                success = self._converter.convert(src, out_path, progress_callback=self._on_progress)
                self._on_complete(success, "Conversión")
            except Exception as e:
                self._on_complete(False, f"Conversión: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_compression(self):
        """Inicia la compresión de video."""
        src = self.comp_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        dest_dir = self.comp_dest_dir_var.get()
        preset_label = self.comp_preset_var.get()
        preset_key = self._get_preset_key(preset_label)

        custom_size_mb = None
        if preset_key == "custom":
            try:
                custom_size_mb = float(self.comp_custom_size_var.get())
            except ValueError:
                messagebox.showerror("Error", "Ingrese un tamaño válido en MB.")
                return

        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}_comprimido.mp4"
        out_path = os.path.join(dest_dir, out_filename)

        self.app.update_status("Estado: Iniciando compresión...", "#007bff")
        self._setup_cancel()

        def worker():
            try:
                self._converter = Converter()
                success = self._converter.compress_video(
                    src, out_path, preset=preset_key,
                    custom_size_mb=custom_size_mb,
                    progress_callback=self._on_progress,
                )
                self._on_complete(success, "Compresión")
            except Exception as e:
                self._on_complete(False, f"Compresión: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_trim(self):
        """Inicia el recorte del archivo."""
        src = self.trim_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        start_time = self.trim_start_var.get().strip()
        end_time = self.trim_end_var.get().strip()
        if not start_time or not end_time:
            messagebox.showerror("Error", "Ingrese los tiempos de inicio y fin.")
            return

        dest_dir = self.trim_dest_dir_var.get()
        ext = os.path.splitext(src)[1]
        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}_recortado{ext}"
        out_path = os.path.join(dest_dir, out_filename)

        self.app.update_status("Estado: Iniciando recorte...", "#007bff")
        self._setup_cancel()

        def worker():
            try:
                self._converter = Converter()
                success = self._converter.trim(
                    src, out_path, start_time, end_time,
                    progress_callback=self._on_progress,
                )
                self._on_complete(success, "Recorte")
            except Exception as e:
                self._on_complete(False, f"Recorte: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_extraction(self):
        """Inicia la extracción de audio."""
        src = self.ext_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        fmt = self.ext_format_var.get()
        quality = self.ext_quality_var.get().split(" ")[0] + "k"
        dest_dir = self.ext_dest_dir_var.get()

        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}.{fmt}"
        out_path = os.path.join(dest_dir, out_filename)

        self.app.update_status("Estado: Extrayendo audio...", "#007bff")
        self._setup_cancel()

        def worker():
            try:
                self._converter = Converter()
                success = self._converter.extract_audio(
                    src, out_path, audio_format=fmt,
                    bitrate=quality,
                    progress_callback=self._on_progress,
                )
                self._on_complete(success, "Extracción de audio")
            except Exception as e:
                self._on_complete(False, f"Extracción de audio: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def reload_config(self):
        """Recarga la carpeta destino por defecto cuando se actualiza en Ajustes."""
        from src.ui.tab_settings import load_config
        cfg = load_config()
        folder = cfg.get("download_folder")
        if folder and os.path.isdir(folder):
            self._default_dest = folder
            if not self.conv_src_var.get():
                self.conv_dest_dir_var.set(folder)
            if not self.comp_src_var.get():
                self.comp_dest_dir_var.set(folder)
            if not self.trim_src_var.get():
                self.trim_dest_dir_var.set(folder)
            if not self.ext_src_var.get():
                self.ext_dest_dir_var.set(folder)

    # ─────────── Métodos de Encolado a QueueManager ───────────

    def _queue_conversion(self):
        """Añade la tarea de conversión a la cola de procesamiento."""
        src = self.conv_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        fmt_val = self.conv_format_var.get()
        if not fmt_val or "no soportado" in fmt_val.lower() or "seleccione" in fmt_val.lower():
            messagebox.showerror("Error", "Seleccione un formato de destino válido.")
            return

        dest_dir = self.conv_dest_dir_var.get()
        target_fmt = fmt_val.split(": ")[-1].strip()
        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}.{target_fmt}"
        out_path = os.path.join(dest_dir, out_filename)

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            from src.core.queue_manager import TaskType
            queue_mgr.add_task(
                TaskType.CONVERSION,
                f"🔄 Convertir: {os.path.basename(src)} → {target_fmt}",
                {"input_path": src, "output_path": out_path}
            )
            messagebox.showinfo("Cola", f"Conversión de '{os.path.basename(src)}' añadida a la cola.")
            self.app.update_status("Tarea añadida a la cola", "gray")
            if hasattr(self.app, "tab_queue"):
                self.app.tab_queue.refresh_tasks()
        else:
            messagebox.showwarning("Cola", "El gestor de cola no está disponible.")

    def _queue_compression(self):
        """Añade la tarea de compresión a la cola de procesamiento."""
        src = self.comp_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        dest_dir = self.comp_dest_dir_var.get()
        preset_label = self.comp_preset_var.get()
        preset_key = self._get_preset_key(preset_label)

        custom_size_mb = None
        if preset_key == "custom":
            try:
                custom_size_mb = float(self.comp_custom_size_var.get())
            except ValueError:
                messagebox.showerror("Error", "Ingrese un tamaño válido en MB.")
                return

        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}_comprimido.mp4"
        out_path = os.path.join(dest_dir, out_filename)

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            from src.core.queue_manager import TaskType
            queue_mgr.add_task(
                TaskType.COMPRESSION,
                f"📦 Comprimir: {os.path.basename(src)} ({preset_label})",
                {
                    "input_path": src,
                    "output_path": out_path,
                    "preset": preset_key,
                    "custom_size_mb": custom_size_mb
                }
            )
            messagebox.showinfo("Cola", f"Compresión de '{os.path.basename(src)}' añadida a la cola.")
            self.app.update_status("Tarea añadida a la cola", "gray")
            if hasattr(self.app, "tab_queue"):
                self.app.tab_queue.refresh_tasks()
        else:
            messagebox.showwarning("Cola", "El gestor de cola no está disponible.")

    def _queue_trim(self):
        """Añade la tarea de recorte a la cola de procesamiento."""
        src = self.trim_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        start_time = self.trim_start_var.get().strip()
        end_time = self.trim_end_var.get().strip()
        if not start_time or not end_time:
            messagebox.showerror("Error", "Ingrese los tiempos de inicio y fin.")
            return

        dest_dir = self.trim_dest_dir_var.get()
        ext = os.path.splitext(src)[1]
        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}_recortado{ext}"
        out_path = os.path.join(dest_dir, out_filename)

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            from src.core.queue_manager import TaskType
            queue_mgr.add_task(
                TaskType.TRIM,
                f"✂️ Recortar: {os.path.basename(src)} [{start_time} - {end_time}]",
                {
                    "input_path": src,
                    "output_path": out_path,
                    "start_time": start_time,
                    "end_time": end_time
                }
            )
            messagebox.showinfo("Cola", f"Recorte de '{os.path.basename(src)}' añadido a la cola.")
            self.app.update_status("Tarea añadida a la cola", "gray")
            if hasattr(self.app, "tab_queue"):
                self.app.tab_queue.refresh_tasks()
        else:
            messagebox.showwarning("Cola", "El gestor de cola no está disponible.")

    def _queue_extraction(self):
        """Añade la tarea de extracción de audio a la cola de procesamiento."""
        src = self.ext_src_var.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Seleccione un archivo de origen válido.")
            return

        fmt = self.ext_format_var.get()
        quality = self.ext_quality_var.get().split(" ")[0] + "k"
        dest_dir = self.ext_dest_dir_var.get()

        out_filename = f"{os.path.splitext(os.path.basename(src))[0]}.{fmt}"
        out_path = os.path.join(dest_dir, out_filename)

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            from src.core.queue_manager import TaskType
            queue_mgr.add_task(
                TaskType.EXTRACTION,
                f"🎵 Extraer audio: {os.path.basename(src)} ({fmt})",
                {
                    "input_path": src,
                    "output_path": out_path,
                    "audio_format": fmt,
                    "bitrate": quality
                }
            )
            messagebox.showinfo("Cola", f"Extracción de audio de '{os.path.basename(src)}' añadida a la cola.")
            self.app.update_status("Tarea añadida a la cola", "gray")
            if hasattr(self.app, "tab_queue"):
                self.app.tab_queue.refresh_tasks()
        else:
            messagebox.showwarning("Cola", "El gestor de cola no está disponible.")

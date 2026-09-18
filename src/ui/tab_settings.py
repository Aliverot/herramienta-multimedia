"""
Pestaña de ajustes y configuración de la suite multimedia.
Permite configurar rutas, cookies, tema visual y verificar FFmpeg.
"""

import os
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Ruta del archivo de configuración
_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".herramienta_multimedia")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")
_LEGACY_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".suite_multimedia_pro", "config.json")

DEFAULT_CONFIG = {
    "download_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    "cookies_browser": "ninguno",
    "theme": "system",
    "audio_format": "mp3",
    "audio_bitrate": "192",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "max_concurrent": 1,
}


def load_config() -> dict:
    """Carga la configuración desde el archivo JSON."""
    try:
        target_file = _CONFIG_FILE if os.path.exists(_CONFIG_FILE) else _LEGACY_CONFIG_FILE
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                return config
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Guarda la configuración en el archivo JSON."""
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")


class TabSettings(ctk.CTkFrame):
    """Pestaña de ajustes y configuración general."""

    def __init__(self, parent, app):
        """Inicializa la pestaña de ajustes."""
        super().__init__(parent)
        self.app = app
        self.config = load_config()

        # --- Contenedor scrollable ---
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ============================================
        # SECCIÓN: Apariencia
        # ============================================
        self._create_section_header(container, "🎨 Apariencia")

        theme_frame = ctk.CTkFrame(container, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            theme_frame, text="Tema visual:", font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 10))

        self.theme_var = ctk.StringVar(value=self.config.get("theme", "system"))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["system", "dark", "light"],
            variable=self.theme_var,
            command=self._on_theme_change,
            width=150,
        )
        self.theme_menu.pack(side="left")

        ctk.CTkLabel(
            theme_frame,
            text="(Sistema / Oscuro / Claro)",
            font=("Segoe UI", 10),
            text_color="gray50",
        ).pack(side="left", padx=10)

        # ============================================
        # SECCIÓN: Carpeta por defecto
        # ============================================
        self._create_section_header(container, "📂 Carpeta de Descarga Predeterminada")

        folder_frame = ctk.CTkFrame(container, fg_color="transparent")
        folder_frame.pack(fill="x", padx=20, pady=5)

        self.folder_var = ctk.StringVar(
            value=self.config.get("download_folder", DEFAULT_CONFIG["download_folder"])
        )
        folder_entry = ctk.CTkEntry(
            folder_frame,
            textvariable=self.folder_var,
            width=400,
            state="disabled",
        )
        folder_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            folder_frame,
            text="📂 Cambiar",
            width=100,
            command=self._select_default_folder,
        ).pack(side="left")

        # ============================================
        # SECCIÓN: Cookies de navegador
        # ============================================
        self._create_section_header(container, "🍪 Cookies de Navegador (Anti-bloqueo)")

        cookies_desc = ctk.CTkLabel(
            container,
            text="Usa cookies de tu navegador solo si experimentas bloqueos tipo 'Sign in / bot'.\n"
            "💡 Recomendado: 'ninguno'. Si seleccionas un navegador, asegúrate de tenerlo cerrado al descargar.",
            font=("Segoe UI", 11),
            text_color="gray50",
            justify="left",
        )
        cookies_desc.pack(fill="x", padx=20, pady=(0, 5))

        cookies_frame = ctk.CTkFrame(container, fg_color="transparent")
        cookies_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            cookies_frame, text="Navegador:", font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 10))

        browsers = ["ninguno", "chrome", "edge", "firefox", "brave", "opera"]
        self.cookies_var = ctk.StringVar(
            value=self.config.get("cookies_browser", "ninguno")
        )
        self.cookies_menu = ctk.CTkOptionMenu(
            cookies_frame,
            values=browsers,
            variable=self.cookies_var,
            width=150,
        )
        self.cookies_menu.pack(side="left")

        # ============================================
        # SECCIÓN: Valores por defecto de audio
        # ============================================
        self._create_section_header(container, "🎵 Configuración de Audio por Defecto")

        audio_frame = ctk.CTkFrame(container, fg_color="transparent")
        audio_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            audio_frame, text="Formato:", font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 10))

        self.audio_format_var = ctk.StringVar(
            value=self.config.get("audio_format", "mp3")
        )
        ctk.CTkOptionMenu(
            audio_frame,
            values=["mp3", "m4a", "flac", "wav", "opus"],
            variable=self.audio_format_var,
            width=100,
        ).pack(side="left", padx=(0, 20))

        ctk.CTkLabel(
            audio_frame, text="Calidad:", font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 10))

        self.audio_bitrate_var = ctk.StringVar(
            value=self.config.get("audio_bitrate", "192")
        )
        ctk.CTkOptionMenu(
            audio_frame,
            values=["128", "192", "256", "320"],
            variable=self.audio_bitrate_var,
            width=100,
        ).pack(side="left")

        ctk.CTkLabel(
            audio_frame, text="kbps", font=("Segoe UI", 11), text_color="gray50"
        ).pack(side="left", padx=5)

        # Checkboxes de metadatos
        meta_frame = ctk.CTkFrame(container, fg_color="transparent")
        meta_frame.pack(fill="x", padx=20, pady=5)

        self.thumbnail_var = ctk.BooleanVar(
            value=self.config.get("embed_thumbnail", True)
        )
        ctk.CTkCheckBox(
            meta_frame,
            text="Incrustar carátula (thumbnail) en archivos de audio",
            variable=self.thumbnail_var,
            font=("Segoe UI", 11),
        ).pack(side="left", padx=(0, 20))

        self.metadata_var = ctk.BooleanVar(
            value=self.config.get("embed_metadata", True)
        )
        ctk.CTkCheckBox(
            meta_frame,
            text="Incrustar metadatos (título, artista)",
            variable=self.metadata_var,
            font=("Segoe UI", 11),
        ).pack(side="left")

        # ============================================
        # SECCIÓN: Rendimiento y Concurrencia de Cola
        # ============================================
        self._create_section_header(container, "⚡ Rendimiento y Concurrencia de Cola")

        concurrent_frame = ctk.CTkFrame(container, fg_color="transparent")
        concurrent_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            concurrent_frame, text="Tareas simultáneas en cola:", font=("Segoe UI", 12)
        ).pack(side="left", padx=(0, 10))

        self.concurrent_var = ctk.StringVar(
            value=str(self.config.get("max_concurrent", 1))
        )
        self.concurrent_menu = ctk.CTkOptionMenu(
            concurrent_frame,
            values=["1", "2", "3"],
            variable=self.concurrent_var,
            width=80,
        )
        self.concurrent_menu.pack(side="left")

        ctk.CTkLabel(
            concurrent_frame,
            text="(1 recomendado para evitar saturar CPU o ancho de banda)",
            font=("Segoe UI", 10),
            text_color="gray50",
        ).pack(side="left", padx=10)

        # ============================================
        # SECCIÓN: Estado de FFmpeg
        # ============================================
        self._create_section_header(container, "⚙️ Estado de FFmpeg")

        ffmpeg_frame = ctk.CTkFrame(container, corner_radius=8)
        ffmpeg_frame.pack(fill="x", padx=20, pady=5)

        self.ffmpeg_status_label = ctk.CTkLabel(
            ffmpeg_frame,
            text="Verificando...",
            font=("Segoe UI", 12),
            justify="left",
        )
        self.ffmpeg_status_label.pack(padx=15, pady=10, anchor="w")

        ctk.CTkButton(
            ffmpeg_frame,
            text="🔄 Verificar FFmpeg",
            width=150,
            command=self._check_ffmpeg,
        ).pack(padx=15, pady=(0, 10), anchor="w")

        # Verificar FFmpeg al inicio
        self.after(500, self._check_ffmpeg)

        # ============================================
        # BOTÓN GUARDAR
        # ============================================
        save_frame = ctk.CTkFrame(self, fg_color="transparent")
        save_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            save_frame,
            text="💾 Guardar Configuración",
            width=200,
            height=36,
            font=("Segoe UI", 13, "bold"),
            fg_color="#28a745",
            hover_color="#218838",
            command=self._save_settings,
        ).pack(side="right")

        ctk.CTkButton(
            save_frame,
            text="↩️ Restaurar Valores",
            width=160,
            height=36,
            font=("Segoe UI", 12),
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self._restore_defaults,
        ).pack(side="right", padx=10)

    def _create_section_header(self, parent, text: str):
        """Crea un encabezado de sección con separador."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=(15, 2))

        ctk.CTkLabel(
            frame, text=text, font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        ctk.CTkFrame(frame, height=1, fg_color="gray60").pack(
            fill="x", pady=(3, 0)
        )

    def _on_theme_change(self, value: str):
        """Cambia el tema visual en tiempo real."""
        ctk.set_appearance_mode(value)
        if hasattr(self.app, "set_theme"):
            self.app.set_theme(value)

    def _select_default_folder(self):
        """Abre diálogo para seleccionar la carpeta de descarga predeterminada."""
        path = filedialog.askdirectory(title="Selecciona la carpeta predeterminada")
        if path:
            self.folder_var.set(path)

    def _check_ffmpeg(self):
        """Verifica el estado de FFmpeg."""
        try:
            from src.core.ffmpeg_manager import get_manager

            mgr = get_manager()
            if mgr.is_available:
                version = mgr.get_version()
                self.ffmpeg_status_label.configure(
                    text=f"✅ FFmpeg detectado correctamente\n"
                    f"📍 Ruta: {mgr.ffmpeg_path}\n"
                    f"📌 Versión: {version}",
                    text_color=("green", "#4CAF50"),
                )
            else:
                self.ffmpeg_status_label.configure(
                    text="❌ FFmpeg NO encontrado\n"
                    "Coloca los binarios en la carpeta ffmpeg/bin/ del proyecto.",
                    text_color=("red", "#f44336"),
                )
        except Exception as e:
            self.ffmpeg_status_label.configure(
                text=f"⚠️ Error al verificar FFmpeg:\n{e}",
                text_color=("orange", "#FF9800"),
            )

    def _save_settings(self):
        """Guarda toda la configuración y la aplica en caliente."""
        try:
            concurrent_val = int(self.concurrent_var.get())
        except (ValueError, TypeError):
            concurrent_val = 1

        self.config.update(
            {
                "download_folder": self.folder_var.get(),
                "cookies_browser": self.cookies_var.get(),
                "theme": self.theme_var.get(),
                "audio_format": self.audio_format_var.get(),
                "audio_bitrate": self.audio_bitrate_var.get(),
                "embed_thumbnail": self.thumbnail_var.get(),
                "embed_metadata": self.metadata_var.get(),
                "max_concurrent": concurrent_val,
            }
        )
        save_config(self.config)

        # Aplicar concurrencia a la cola activa si está disponible
        if hasattr(self.app, "queue_manager") and self.app.queue_manager is not None:
            self.app.queue_manager.max_concurrent = concurrent_val

        # Notificar en caliente a las pestañas de descargas y conversión
        if hasattr(self.app, "tab_download") and hasattr(self.app.tab_download, "reload_config"):
            self.app.tab_download.reload_config()
        if hasattr(self.app, "tab_convert") and hasattr(self.app.tab_convert, "reload_config"):
            self.app.tab_convert.reload_config()

        messagebox.showinfo(
            "Configuración", "✅ Configuración guardada exitosamente."
        )

    def _restore_defaults(self):
        """Restaura los valores por defecto."""
        confirm = messagebox.askyesno(
            "Restaurar",
            "¿Estás seguro de restaurar los valores predeterminados?",
        )
        if not confirm:
            return

        self.config = DEFAULT_CONFIG.copy()
        self.folder_var.set(self.config["download_folder"])
        self.cookies_var.set(self.config["cookies_browser"])
        self.theme_var.set(self.config["theme"])
        self.audio_format_var.set(self.config["audio_format"])
        self.audio_bitrate_var.set(self.config["audio_bitrate"])
        self.thumbnail_var.set(self.config["embed_thumbnail"])
        self.metadata_var.set(self.config["embed_metadata"])
        self.concurrent_var.set(str(self.config.get("max_concurrent", 1)))

        ctk.set_appearance_mode(self.config["theme"])
        save_config(self.config)

        # Aplicar concurrencia restablecida al QueueManager
        if hasattr(self.app, "queue_manager") and self.app.queue_manager is not None:
            self.app.queue_manager.max_concurrent = self.config.get("max_concurrent", 1)

        # Notificar en caliente a las pestañas de descargas y conversión
        if hasattr(self.app, "tab_download") and hasattr(self.app.tab_download, "reload_config"):
            self.app.tab_download.reload_config()
        if hasattr(self.app, "tab_convert") and hasattr(self.app.tab_convert, "reload_config"):
            self.app.tab_convert.reload_config()

        messagebox.showinfo("Restaurado", "✅ Valores restaurados correctamente.")

    def get_cookies_browser(self) -> str | None:
        """Retorna el navegador de cookies configurado, o None si es 'ninguno'."""
        browser = self.cookies_var.get()
        return None if browser == "ninguno" else browser

    def get_download_folder(self) -> str:
        """Retorna la carpeta de descarga configurada."""
        return self.folder_var.get()

    def get_audio_defaults(self) -> dict:
        """Retorna los valores por defecto de audio."""
        return {
            "format": self.audio_format_var.get(),
            "bitrate": self.audio_bitrate_var.get(),
            "embed_thumbnail": self.thumbnail_var.get(),
            "embed_metadata": self.metadata_var.get(),
        }

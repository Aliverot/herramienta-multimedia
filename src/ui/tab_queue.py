"""
Pestaña de cola de descargas e historial.
Muestra las tareas activas, pendientes y completadas.
"""

import os
import customtkinter as ctk
from tkinter import messagebox


class TabQueue(ctk.CTkFrame):
    """Pestaña de cola de tareas e historial de descargas/conversiones."""

    def __init__(self, parent, app):
        """Inicializa la pestaña de cola."""
        super().__init__(parent)
        self.app = app
        self._task_widgets: dict[str, ctk.CTkFrame] = {}

        # --- Encabezado ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="📋 Cola de Tareas",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        # Botones de acción globales
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        self.btn_clear = ctk.CTkButton(
            btn_frame,
            text="🗑️ Limpiar Historial",
            width=140,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self._clear_completed,
        )
        self.btn_clear.pack(side="right", padx=5)

        self.btn_cancel_all = ctk.CTkButton(
            btn_frame,
            text="⛔ Cancelar Todo",
            width=130,
            fg_color="#dc3545",
            hover_color="#c82333",
            command=self._cancel_all,
        )
        self.btn_cancel_all.pack(side="right", padx=5)

        # --- Separador ---
        ctk.CTkFrame(self, height=2, fg_color="gray70").pack(
            fill="x", padx=15, pady=5
        )

        # --- Lista de tareas (scrollable) ---
        self.tasks_container = ctk.CTkScrollableFrame(
            self, label_text="Tareas", label_font=("Segoe UI", 12)
        )
        self.tasks_container.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        # Mensaje vacío
        self.empty_label = ctk.CTkLabel(
            self.tasks_container,
            text="No hay tareas en la cola.\nAñade descargas o conversiones desde las otras pestañas.",
            font=("Segoe UI", 12),
            text_color="gray50",
        )
        self.empty_label.pack(pady=40)

        # --- Estadísticas ---
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_stats = ctk.CTkLabel(
            stats_frame,
            text="Activas: 0  |  Pendientes: 0  |  Completadas: 0",
            font=("Segoe UI", 11),
            text_color="gray50",
        )
        self.lbl_stats.pack(side="left")

    def refresh_tasks(self):
        """Refresca la lista de tareas desde el QueueManager."""
        try:
            from src.core.queue_manager import QueueManager
        except ImportError:
            return

        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr is None:
            return

        tasks = queue_mgr.get_all_tasks()

        if not tasks:
            self.empty_label.pack(pady=40)
            self._clear_task_widgets()
            self._update_stats(0, 0, 0)
            return

        self.empty_label.pack_forget()

        current_ids = set()
        activas = 0
        pendientes = 0
        completadas = 0

        for task in tasks:
            current_ids.add(task.id)
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)

            if status_val == "running":
                activas += 1
            elif status_val == "pending":
                pendientes += 1
            else:
                completadas += 1

            if task.id in self._task_widgets:
                self._update_task_widget(task)
            else:
                self._create_task_widget(task)

        # Eliminar widgets de tareas que ya no existen
        for tid in list(self._task_widgets.keys()):
            if tid not in current_ids:
                self._task_widgets[tid].destroy()
                del self._task_widgets[tid]

        self._update_stats(activas, pendientes, completadas)

    def _create_task_widget(self, task):
        """Crea un widget visual para una tarea."""
        frame = ctk.CTkFrame(self.tasks_container, corner_radius=8)
        frame.pack(fill="x", padx=5, pady=3)

        # Título y tipo
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=(8, 2))

        status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
        type_val = task.type.value if hasattr(task.type, "value") else str(task.type)

        icon = self._get_status_icon(status_val)
        type_icon = self._get_type_icon(type_val)

        ctk.CTkLabel(
            info_frame,
            text=f"{icon} {task.title}",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info_frame,
            text=f"{type_icon} {type_val.capitalize()}",
            font=("Segoe UI", 10),
            text_color="gray50",
        ).pack(side="right")

        # Barra de progreso
        progress_frame = ctk.CTkFrame(frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=10, pady=(2, 2))

        progress_bar = ctk.CTkProgressBar(progress_frame, height=10)
        progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        progress_bar.set(task.progress / 100.0)

        lbl_percent = ctk.CTkLabel(
            progress_frame,
            text=f"{task.progress:.0f}%",
            font=("Segoe UI", 10),
            width=45,
        )
        lbl_percent.pack(side="right")

        # Botón de cancelar (solo para running/pending)
        action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=(0, 6))

        color = self._get_status_color(status_val)
        ctk.CTkLabel(
            action_frame,
            text=status_val.capitalize(),
            font=("Segoe UI", 10),
            text_color=color,
        ).pack(side="left")

        right_actions = ctk.CTkFrame(action_frame, fg_color="transparent")
        right_actions.pack(side="right")

        if status_val in ("running", "pending"):
            btn_cancel = ctk.CTkButton(
                right_actions,
                text="❌ Cancelar",
                width=85,
                height=24,
                font=("Segoe UI", 10),
                fg_color="#dc3545",
                hover_color="#c82333",
                command=lambda tid=task.id: self._cancel_task(tid),
            )
            btn_cancel.pack(side="right")
        elif status_val == "completed" and task.output_path:
            btn_open = ctk.CTkButton(
                right_actions,
                text="📂 Abrir",
                width=80,
                height=24,
                font=("Segoe UI", 10),
                fg_color="#28a745",
                hover_color="#218838",
                command=lambda p=task.output_path: self._open_folder(p),
            )
            btn_open.pack(side="right")
        elif status_val in ("failed", "cancelled"):
            btn_retry = ctk.CTkButton(
                right_actions,
                text="🔄 Reintentar",
                width=90,
                height=24,
                font=("Segoe UI", 10),
                fg_color="#007bff",
                hover_color="#0069d9",
                command=lambda tid=task.id: self._retry_task(tid),
            )
            btn_retry.pack(side="right", padx=(5, 0))

            if status_val == "failed" and task.error_message:
                btn_err = ctk.CTkButton(
                    right_actions,
                    text="❓ Ver Error",
                    width=85,
                    height=24,
                    font=("Segoe UI", 10),
                    fg_color="#6c757d",
                    hover_color="#5a6268",
                    command=lambda err=task.error_message, title=task.title: self._show_error_dialog(title, err),
                )
                btn_err.pack(side="right")

        # Guardar referencia
        frame._progress_bar = progress_bar
        frame._lbl_percent = lbl_percent
        self._task_widgets[task.id] = frame

    def _update_task_widget(self, task):
        """Actualiza un widget de tarea existente."""
        frame = self._task_widgets.get(task.id)
        if frame and hasattr(frame, "_progress_bar"):
            frame._progress_bar.set(task.progress / 100.0)
            frame._lbl_percent.configure(text=f"{task.progress:.0f}%")

    def _clear_task_widgets(self):
        """Elimina todos los widgets de tareas."""
        for widget in self._task_widgets.values():
            widget.destroy()
        self._task_widgets.clear()

    def _update_stats(self, activas: int, pendientes: int, completadas: int):
        """Actualiza las estadísticas mostradas."""
        self.lbl_stats.configure(
            text=f"Activas: {activas}  |  Pendientes: {pendientes}  |  Completadas: {completadas}"
        )

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "running": "⏳",
            "pending": "🕐",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }
        return icons.get(status, "❓")

    def _get_type_icon(self, type_str: str) -> str:
        icons = {
            "download": "⬇️",
            "conversion": "🔄",
            "compression": "📦",
            "extraction": "🎵",
            "trim": "✂️",
        }
        return icons.get(type_str, "📄")

    def _get_status_color(self, status: str) -> str:
        colors = {
            "running": "#007bff",
            "pending": "#ffc107",
            "completed": "#28a745",
            "failed": "#dc3545",
            "cancelled": "#6c757d",
        }
        return colors.get(status, "gray")

    def _cancel_task(self, task_id: str):
        """Cancela una tarea específica."""
        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            queue_mgr.cancel_task(task_id)
            self.after(300, self.refresh_tasks)

    def _cancel_all(self):
        """Cancela todas las tareas."""
        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            queue_mgr.cancel_all()
            self.after(300, self.refresh_tasks)

    def _clear_completed(self):
        """Limpia las tareas completadas/fallidas/canceladas."""
        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            queue_mgr.clear_completed()
            self.after(200, self.refresh_tasks)

    def _retry_task(self, task_id: str):
        """Reintenta una tarea fallida o cancelada."""
        queue_mgr = getattr(self.app, "queue_manager", None)
        if queue_mgr:
            queue_mgr.retry_task(task_id)
            self.after(200, self.refresh_tasks)

    def _show_error_dialog(self, title: str, error_message: str):
        """Muestra un diálogo explicativo detallado con el error reportado."""
        hint = ""
        lower_err = str(error_message).lower()
        if "sign in" in lower_err or "bot" in lower_err or "login" in lower_err:
            hint = "\n\n💡 Sugerencia: YouTube suele solicitar confirmación anti-bot. Puedes habilitar las cookies de tu navegador en la pestaña '⚙️ Ajustes'."
        messagebox.showerror(
            "Detalle del Error",
            f"Tarea: {title}\n\nMotivo del fallo:\n{error_message}{hint}"
        )

    def _open_folder(self, path: str):
        """Abre la carpeta o resalta el archivo directamente en el Explorador de Windows."""
        try:
            if os.path.isfile(path):
                import subprocess
                subprocess.Popen(
                    f'explorer /select,"{os.path.abspath(path)}"',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            elif os.path.isdir(path):
                os.startfile(path)
            else:
                parent = os.path.dirname(path)
                if os.path.isdir(parent):
                    os.startfile(parent)
                else:
                    messagebox.showwarning("Aviso", f"La ruta ya no existe en el disco:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la ubicación:\n{e}")

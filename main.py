"""
Herramienta Multimedia - Punto de entrada principal.
Descargador, conversor y procesamiento de medios con interfaz moderna.
"""

import sys
import os

# Agregar la raíz del proyecto al path para imports correctos
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.queue_manager import QueueManager
from src.ui.app import App


def main():
    """Inicia la aplicación Herramienta Multimedia."""
    from src.ui.tab_settings import load_config
    config = load_config()
    max_concurrent = int(config.get("max_concurrent", 1))

    # Crear instancia del gestor de cola
    queue_manager = QueueManager(max_concurrent=max_concurrent)

    # Crear y configurar la aplicación
    app = App()
    app.queue_manager = queue_manager

    # Conectar callbacks de la cola con la UI
    def on_task_status_change(task):
        """Actualiza la pestaña de cola cuando cambia el estado de una tarea."""
        if hasattr(app, "tab_queue"):
            app.after(0, app.tab_queue.refresh_tasks)

    def on_task_progress(task_id: str, percent: float):
        """Actualiza la barra de progreso global con el progreso de la cola."""
        app.after(0, lambda: app.update_progress(percent / 100.0))

    queue_manager.set_status_callback(on_task_status_change)
    queue_manager.set_progress_callback(on_task_progress)

    # Iniciar la aplicación
    app.run()


if __name__ == "__main__":
    main()

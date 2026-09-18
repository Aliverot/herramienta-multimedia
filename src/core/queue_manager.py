"""
Módulo del gestor de cola de tareas para la suite multimedia.
Administra la ejecución secuencial y concurrente de tareas de descarga, conversión,
compresión, extracción de audio y recorte.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Any


class TaskType(Enum):
    """Tipos de tareas multimedia soportadas."""
    DOWNLOAD = 'download'
    CONVERSION = 'conversion'
    COMPRESSION = 'compression'
    EXTRACTION = 'extraction'
    TRIM = 'trim'


class TaskStatus(Enum):
    """Estados posibles de una tarea en la cola."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Task:
    """
    Representa una tarea individual dentro del gestor de cola.
    """
    id: str  # UUID
    type: TaskType
    status: TaskStatus
    title: str  # Nombre descriptivo
    params: dict  # Parámetros necesarios para la ejecución
    progress: float = 0.0  # Progreso 0-100
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None


class QueueManager:
    """
    Gestor de cola de tareas multimedia con soporte para ejecución en hilos y concurrencia.
    """

    def __init__(self, max_concurrent: int = 1):
        """
        Inicializa la cola de tareas, bloqueos y estructuras de control.

        Args:
            max_concurrent: Cantidad máxima de tareas concurrentes (por defecto 1).
        """
        self._queue: list[Task] = []
        self._tasks = self._queue
        self._lock = threading.RLock()
        self.max_concurrent: int = max(1, max_concurrent)
        self._max_concurrent = self.max_concurrent

        # Diccionario para mapear ID de tarea a su hilo de trabajo
        self._threads: dict[str, threading.Thread] = {}
        self._workers = self._threads

        # Diccionario para mapear ID de tarea a su motor activo (Downloader o Converter)
        self._engines: dict[str, Any] = {}

        # Diccionario para eventos de cancelación individuales
        self._cancel_events: dict[str, threading.Event] = {}

        # Callbacks de estado y progreso
        self._status_callback: Optional[Callable[[Task], None]] = None
        self._progress_callback: Optional[Callable[[str, float], None]] = None

    def add_task(
        self,
        task_type: TaskType | dict,
        title: Optional[str] = None,
        params: Optional[dict] = None
    ) -> str:
        """
        Crea una nueva tarea con UUID generado, estado PENDING, la agrega a la cola
        e inicia su procesamiento si hay capacidad disponible.

        Soporta tanto la firma estándar (task_type, title, params) como el paso
        directo de un diccionario de opciones de interfaz.

        Args:
            task_type: Tipo de tarea (TaskType) o diccionario con datos de la tarea.
            title: Nombre descriptivo para mostrar en la interfaz.
            params: Diccionario con todos los parámetros de ejecución.

        Returns:
            El identificador único (UUID) de la tarea creada.
        """
        if isinstance(task_type, dict):
            p = dict(task_type)
            type_str = str(p.get("task_type") or p.get("type", "")).lower()
            if "convert" in type_str:
                resolved_type = TaskType.CONVERSION
            elif "compress" in type_str:
                resolved_type = TaskType.COMPRESSION
            elif "extract" in type_str:
                resolved_type = TaskType.EXTRACTION
            elif "trim" in type_str:
                resolved_type = TaskType.TRIM
            else:
                resolved_type = TaskType.DOWNLOAD
            resolved_title = title or p.get("title") or p.get("url") or "Tarea Multimedia"
            resolved_params = p
        elif isinstance(task_type, str):
            try:
                resolved_type = TaskType(task_type.lower())
            except ValueError:
                resolved_type = TaskType.DOWNLOAD
            resolved_title = title or "Tarea Multimedia"
            resolved_params = params or {}
        else:
            resolved_type = task_type
            resolved_title = title or "Tarea Multimedia"
            resolved_params = params or {}

        task_id = str(uuid.uuid4())
        initial_output = (
            resolved_params.get("output_path")
            or resolved_params.get("dest")
            or resolved_params.get("output_dir")
        )

        task = Task(
            id=task_id,
            type=resolved_type,
            status=TaskStatus.PENDING,
            title=resolved_title,
            params=resolved_params,
            progress=0.0,
            error_message=None,
            created_at=datetime.now(),
            completed_at=None,
            output_path=initial_output
        )

        with self._lock:
            self._queue.append(task)
            self._cancel_events[task_id] = threading.Event()

        # Notificar creación de la tarea en estado PENDING
        self._notify_status_callback(task)

        # Iniciar ejecución si hay espacio disponible
        self._process_next()

        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """
        Establece el estado de la tarea en CANCELLED y señaliza la cancelación
        al motor de descarga o conversión en ejecución.

        Args:
            task_id: Identificador de la tarea a cancelar.

        Returns:
            True si la tarea fue cancelada exitosamente, False si no existía o ya concluyó.
        """
        with self._lock:
            task = self.get_task(task_id)
            if task is None:
                return False

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False

            is_running = (task.status == TaskStatus.RUNNING)
            engine = self._engines.get(task_id)

            cancel_event = self._cancel_events.get(task_id)
            if cancel_event:
                cancel_event.set()

            self._update_task_status(task, TaskStatus.CANCELLED)

        # Señalizar cancelación al motor activo inmediatamente fuera del bloqueo
        if is_running and engine is not None:
            if hasattr(engine, "cancel"):
                try:
                    engine.cancel()
                except Exception:
                    pass

        # Procesar siguiente tarea pendiente
        self._process_next()
        return True

    def retry_task(self, task_id: str) -> bool:
        """
        Reencola una tarea que falló o fue cancelada, reiniciando su estado
        a PENDING, restableciendo su progreso a 0.0 y limpiando errores previos.

        Args:
            task_id: Identificador único de la tarea a reintentar.

        Returns:
            True si la tarea fue reencolada con éxito, False si no existe o aún está activa.
        """
        with self._lock:
            task = self.get_task(task_id)
            if task is None:
                return False

            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                return False

            task.status = TaskStatus.PENDING
            task.progress = 0.0
            task.error_message = None
            task.completed_at = None
            self._cancel_events[task_id] = threading.Event()
            self._threads.pop(task_id, None)
            self._engines.pop(task_id, None)

        # Notificar fuera del bloqueo para evitar deadlocks con la GUI
        self._notify_status_callback(task)

        # Iniciar ejecución si hay espacio disponible
        self._process_next()
        return True

    def _cleanup_partial_files(self, task: Task) -> None:
        """
        Limpia archivos temporales o incompletos (.part, .temp, .ytdl)
        generados si una tarea fue cancelada o falló, evitando dejar residuos en disco.
        """
        try:
            target = task.output_path
            if not target:
                return

            # Si es un archivo directo resultante de conversión/compresión/recorte que quedó incompleto
            if os.path.isfile(target):
                try:
                    os.remove(target)
                except Exception:
                    pass

            # Si es un directorio de descarga, buscar archivos residuales .part o .ytdl
            target_dir = target if os.path.isdir(target) else os.path.dirname(target)
            if os.path.isdir(target_dir):
                for entry in os.listdir(target_dir):
                    if entry.endswith((".part", ".ytdl", ".temp")):
                        full_entry = os.path.join(target_dir, entry)
                        try:
                            os.remove(full_entry)
                        except Exception:
                            pass
        except Exception:
            pass

    def cancel_all(self) -> None:
        """
        Cancela todas las tareas pendientes y en ejecución.
        """
        with self._lock:
            active_ids = [
                t.id for t in self._queue
                if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ]

        for tid in active_ids:
            self.cancel_task(tid)

    def remove_task(self, task_id: str) -> bool:
        """
        Elimina una tarea completada, fallida o cancelada de la cola.

        Args:
            task_id: Identificador de la tarea a remover.

        Returns:
            True si se removió la tarea, False si no existía o continúa activa.
        """
        with self._lock:
            task = self.get_task(task_id)
            if task is None:
                return False

            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                return False

            self._queue = [t for t in self._queue if t.id != task_id]
            self._tasks = self._queue
            self._threads.pop(task_id, None)
            self._engines.pop(task_id, None)
            self._cancel_events.pop(task_id, None)
            return True

    def clear_completed(self) -> int:
        """
        Elimina todas las tareas completadas, fallidas y canceladas del historial.

        Returns:
            Cantidad de tareas eliminadas.
        """
        with self._lock:
            finished = [
                t.id for t in self._queue
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            self._queue = [t for t in self._queue if t.id not in finished]
            self._tasks = self._queue
            for tid in finished:
                self._threads.pop(tid, None)
                self._engines.pop(tid, None)
                self._cancel_events.pop(tid, None)
            return len(finished)

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retorna una tarea específica de la cola según su ID.

        Args:
            task_id: Identificador de la tarea buscada.

        Returns:
            Instancia de Task si se encuentra, o None en caso contrario.
        """
        with self._lock:
            for task in self._queue:
                if task.id == task_id:
                    return task
            return None

    def _find_task(self, task_id: str) -> Optional[Task]:
        """Método de compatibilidad interna para buscar tareas."""
        return self.get_task(task_id)

    def get_all_tasks(self) -> list[Task]:
        """
        Retorna una lista con todas las tareas registradas.
        """
        with self._lock:
            return list(self._queue)

    def get_active_tasks(self) -> list[Task]:
        """
        Retorna todas las tareas activas (en ejecución o pendientes).
        """
        with self._lock:
            return [
                t for t in self._queue
                if t.status in (TaskStatus.RUNNING, TaskStatus.PENDING)
            ]

    def get_history(self) -> list[Task]:
        """
        Retorna las tareas en el historial (completadas, fallidas o canceladas).
        """
        with self._lock:
            return [
                t for t in self._queue
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]

    def set_status_callback(self, callback: Callable[[Task], None]) -> None:
        """
        Establece la función callback que se invocará ante cambios de estado de una tarea.

        Args:
            callback: Función que recibe el objeto Task actualizado.
        """
        with self._lock:
            self._status_callback = callback

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """
        Establece la función callback para reportar progreso porcentual.

        Args:
            callback: Función que recibe (task_id, porcentaje).
        """
        with self._lock:
            self._progress_callback = callback

    def _process_next(self) -> None:
        """
        Comprueba si existen tareas pendientes y si la cantidad de tareas en ejecución
        es inferior a max_concurrent. En tal caso, inicia las tareas pendientes en
        hilos de trabajo independientes.
        """
        tasks_to_start: list[Task] = []

        with self._lock:
            running_count = sum(1 for t in self._queue if t.status == TaskStatus.RUNNING)
            for task in self._queue:
                if running_count >= self.max_concurrent:
                    break
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.RUNNING
                    running_count += 1
                    tasks_to_start.append(task)

        for task in tasks_to_start:
            # Notificar transición a RUNNING
            self._notify_status_callback(task)

            worker = threading.Thread(
                target=self._execute_task,
                args=(task,),
                name=f"TaskWorker-{task.id[:8]}",
                daemon=True
            )
            with self._lock:
                self._threads[task.id] = worker
            worker.start()

    def _update_task_status(
        self,
        task: Task,
        status: TaskStatus,
        error: Optional[str] = None
    ) -> None:
        """
        Actualiza el estado de una tarea de forma thread-safe y notifica al callback de estado.

        Args:
            task: Tarea cuyo estado se actualizará.
            status: Nuevo estado de la tarea.
            error: Mensaje de error descriptivo en caso de fallo.
        """
        with self._lock:
            task.status = status
            if error is not None:
                task.error_message = error
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.completed_at = datetime.now()

        self._notify_status_callback(task)

    def _notify_status(self, task: Task) -> None:
        """Alias de compatibilidad para notificar cambios de estado."""
        self._notify_status_callback(task)

    def _notify_status_callback(self, task: Task) -> None:
        """
        Ejecuta el callback de estado fuera de bloqueos para evitar interbloqueos con la interfaz.
        """
        cb = None
        with self._lock:
            cb = self._status_callback

        if cb:
            try:
                cb(task)
            except Exception:
                pass

    def _execute_task(self, task: Task) -> None:
        """
        Método de trabajo ejecutado en un hilo de fondo.
        Según el task.type ejecuta:
        - DOWNLOAD: Crea Downloader de src.core.downloader y llama a download().
        - CONVERSION: Crea Converter de src.core.converter y llama a convert().
        - COMPRESSION: Crea Converter y llama a compress_video().
        - EXTRACTION: Crea Converter y llama a extract_audio().
        - TRIM: Crea Converter y llama a trim().

        Actualiza el estado final de la tarea e inicia la siguiente tarea en cola al finalizar.
        """
        engine: Any = None
        success: bool = False
        error_msg: Optional[str] = None
        cancel_event = self._cancel_events.get(task.id)

        def on_progress(prog: Any) -> None:
            if task.status == TaskStatus.CANCELLED:
                return

            percent = 0.0
            if hasattr(prog, "percent"):
                percent = float(prog.percent)
            elif hasattr(prog, "percentage"):
                percent = float(prog.percentage)
            elif isinstance(prog, (int, float)):
                percent = float(prog)

            percent = min(100.0, max(0.0, percent))
            task.progress = percent

            # Si el progreso reporta el nombre del archivo descargado, registrar ruta precisa
            if hasattr(prog, "filename") and prog.filename and task.type == TaskType.DOWNLOAD:
                base_dir = (
                    task.params.get("output_dir")
                    or task.params.get("dest")
                    or task.params.get("output_path")
                    or os.getcwd()
                )
                cand_file = os.path.join(base_dir, prog.filename)
                if os.path.isfile(cand_file):
                    task.output_path = cand_file

            cb = None
            with self._lock:
                cb = self._progress_callback

            if cb:
                try:
                    cb(task.id, percent)
                except Exception:
                    pass

            if cancel_event and cancel_event.is_set() and engine is not None:
                if hasattr(engine, "cancel"):
                    try:
                        engine.cancel()
                    except Exception:
                        pass

        try:
            if task.type == TaskType.DOWNLOAD:
                from src.core.downloader import Downloader
                downloader = Downloader()
                engine = downloader
                with self._lock:
                    self._engines[task.id] = engine

                params = task.params
                url = params.get("url", "")
                output_dir = (
                    params.get("output_dir")
                    or params.get("dest")
                    or params.get("output_path")
                    or os.getcwd()
                )
                task.output_path = output_dir

                raw_type = str(params.get("media_type") or params.get("type", "")).lower()
                if any(w in raw_type for w in ("audio", "canción", "cancion", "mp3")):
                    media_type = "audio"
                else:
                    media_type = "video"

                raw_quality = str(params.get("format_quality") or params.get("quality", "best")).lower()
                if "mejor" in raw_quality or "best" in raw_quality:
                    format_quality = "best"
                elif "2160" in raw_quality or "4k" in raw_quality:
                    format_quality = "2160p"
                elif "1440" in raw_quality or "2k" in raw_quality:
                    format_quality = "1440p"
                elif "1080" in raw_quality:
                    format_quality = "1080p"
                elif "720" in raw_quality:
                    format_quality = "720p"
                elif "480" in raw_quality:
                    format_quality = "480p"
                elif "360" in raw_quality:
                    format_quality = "360p"
                else:
                    format_quality = params.get("format_quality", "best")

                is_playlist = bool(params.get("is_playlist", False) or ("playlist" in raw_type))
                audio_bitrate = str(params.get("audio_bitrate", "192")).replace(" kbps", "").replace("k", "")
                audio_format = str(params.get("audio_format", "mp3"))
                embed_thumbnail = bool(params.get("embed_thumbnail", True))
                embed_metadata = bool(params.get("embed_metadata", True))
                cookies_browser = params.get("cookies_browser")

                success = downloader.download(
                    url=url,
                    output_dir=output_dir,
                    media_type=media_type,
                    format_quality=format_quality,
                    is_playlist=is_playlist,
                    audio_bitrate=audio_bitrate,
                    audio_format=audio_format,
                    embed_thumbnail=embed_thumbnail,
                    embed_metadata=embed_metadata,
                    cookies_browser=cookies_browser,
                    progress_callback=on_progress
                )
                if not success and getattr(downloader, "last_error", None):
                    error_msg = downloader.last_error

            elif task.type == TaskType.CONVERSION:
                from src.core.converter import Converter
                converter = Converter()
                engine = converter
                with self._lock:
                    self._engines[task.id] = engine

                params = task.params
                input_path = params.get("input_path") or params.get("src", "")
                output_path = params.get("output_path") or params.get("dest", "")
                task.output_path = output_path

                success = converter.convert(
                    input_path=input_path,
                    output_path=output_path,
                    progress_callback=on_progress
                )
                if not success and getattr(converter, "last_error", None):
                    error_msg = converter.last_error

            elif task.type == TaskType.COMPRESSION:
                from src.core.converter import Converter
                converter = Converter()
                engine = converter
                with self._lock:
                    self._engines[task.id] = engine

                params = task.params
                input_path = params.get("input_path") or params.get("src", "")
                output_path = params.get("output_path") or params.get("dest", "")
                preset = params.get("preset", "whatsapp_16mb")
                custom_size_mb = params.get("custom_size_mb")
                task.output_path = output_path

                success = converter.compress_video(
                    input_path=input_path,
                    output_path=output_path,
                    preset=preset,
                    custom_size_mb=custom_size_mb,
                    progress_callback=on_progress
                )
                if not success and getattr(converter, "last_error", None):
                    error_msg = converter.last_error

            elif task.type == TaskType.EXTRACTION:
                from src.core.converter import Converter
                converter = Converter()
                engine = converter
                with self._lock:
                    self._engines[task.id] = engine

                params = task.params
                input_path = params.get("input_path") or params.get("src", "")
                output_path = params.get("output_path") or params.get("dest", "")
                audio_format = params.get("audio_format", "mp3")
                bitrate = params.get("bitrate", "192k")
                task.output_path = output_path

                success = converter.extract_audio(
                    input_path=input_path,
                    output_path=output_path,
                    audio_format=audio_format,
                    bitrate=bitrate,
                    progress_callback=on_progress
                )
                if not success and getattr(converter, "last_error", None):
                    error_msg = converter.last_error

            elif task.type == TaskType.TRIM:
                from src.core.converter import Converter
                converter = Converter()
                engine = converter
                with self._lock:
                    self._engines[task.id] = engine

                params = task.params
                input_path = params.get("input_path") or params.get("src", "")
                output_path = params.get("output_path") or params.get("dest", "")
                start_time = params.get("start_time", "00:00:00")
                end_time = params.get("end_time", "00:00:00")
                task.output_path = output_path

                success = converter.trim(
                    input_path=input_path,
                    output_path=output_path,
                    start_time=start_time,
                    end_time=end_time,
                    progress_callback=on_progress
                )
                if not success and getattr(converter, "last_error", None):
                    error_msg = converter.last_error
            else:
                error_msg = f"Tipo de tarea no reconocido: {task.type}"
                success = False

        except Exception as e:
            error_msg = str(e)
            success = False

        finally:
            with self._lock:
                self._engines.pop(task.id, None)

            # Verificar si la tarea fue cancelada
            is_cancelled = (task.status == TaskStatus.CANCELLED)
            if not is_cancelled and cancel_event and cancel_event.is_set():
                is_cancelled = True
            if not is_cancelled and engine is not None:
                if getattr(engine, "_cancelled", False):
                    is_cancelled = True
                elif getattr(engine, "_cancel_flag", None) is not None and engine._cancel_flag.is_set():
                    is_cancelled = True

            if is_cancelled:
                # Limpiar cualquier archivo residual incompleto (.part, .temp, etc.)
                self._cleanup_partial_files(task)
                if task.status != TaskStatus.CANCELLED:
                    self._update_task_status(task, TaskStatus.CANCELLED)
            elif success:
                task.progress = 100.0
                cb = None
                with self._lock:
                    cb = self._progress_callback
                if cb:
                    try:
                        cb(task.id, 100.0)
                    except Exception:
                        pass
                self._update_task_status(task, TaskStatus.COMPLETED)
            else:
                msg = (
                    error_msg
                    or getattr(engine, "last_error", None)
                    or "La operación falló o no se completó satisfactoriamente."
                )
                # Limpiar archivo generado si quedó corrupto o incompleto tras fallo
                self._cleanup_partial_files(task)
                self._update_task_status(task, TaskStatus.FAILED, error=msg)

            # Continuar con la siguiente tarea de la cola
            self._process_next()

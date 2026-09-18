"""Módulo para la administración y detección centralizada de FFmpeg y FFprobe.

Proporciona una clase singleton para gestionar los binarios multimedia, verificar
su disponibilidad, consultar versiones y obtener metadatos y duración de archivos de medios.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class FFmpegManager:
    """Administrador singleton para los ejecutables y utilidades de FFmpeg y FFprobe."""

    _instance: Optional["FFmpegManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "FFmpegManager":
        """Garantiza la creación de una única instancia de la clase (patrón Singleton)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Inicializa la búsqueda y configuración de rutas para ffmpeg.exe y ffprobe.exe."""
        if getattr(self, "_initialized", False):
            return

        # Determinar la raíz del proyecto:
        # - Si estamos ejecutando como .exe de PyInstaller, usar la carpeta del ejecutable
        # - Si estamos ejecutando como script .py, subir 2 niveles desde src/core/
        if getattr(sys, 'frozen', False):
            # Ejecutable empaquetado con PyInstaller
            self._project_root: Path = Path(sys.executable).resolve().parent
        else:
            # Ejecución normal como script Python
            self._project_root: Path = Path(__file__).resolve().parents[2]

        self.ffmpeg_path: Optional[str] = self._find_binary("ffmpeg")
        self.ffprobe_path: Optional[str] = self._find_binary("ffprobe")
        self._initialized = True

    def _find_binary(self, binary_name: str) -> Optional[str]:
        """Busca un ejecutable según las prioridades establecidas:
        1. ./DescaradorConvertidor/ffmpeg/bin/ (relativo a la raíz del proyecto)
        2. ./ffmpeg/bin/ (relativo a la raíz del proyecto)
        3. PATH del sistema operativo

        Args:
            binary_name: Nombre base del binario (ej. 'ffmpeg' o 'ffprobe').

        Returns:
            Ruta absoluta en cadena de texto si se encuentra el archivo, o None.
        """
        meipass = getattr(sys, '_MEIPASS', None)
        candidate_dirs = []
        if meipass:
            candidate_dirs.append(Path(meipass) / "ffmpeg" / "bin")
            candidate_dirs.append(Path(meipass))

        candidate_dirs.extend([
            self._project_root / "ffmpeg" / "bin",
            self._project_root / "DescaradorConvertidor" / "ffmpeg" / "bin",
            self._project_root / "bin",
            self._project_root,
        ])

        # Priorizar extensión .exe en Windows
        executable_names = (
            [f"{binary_name}.exe", binary_name]
            if sys.platform == "win32"
            else [binary_name, f"{binary_name}.exe"]
        )

        # 1 y 2. Búsqueda en directorios locales relativos a la raíz del proyecto
        for directory in candidate_dirs:
            for exe_name in executable_names:
                candidate_file = directory / exe_name
                if candidate_file.is_file():
                    return str(candidate_file.resolve())

        # 3. Búsqueda en el PATH del sistema
        for exe_name in executable_names:
            found_in_path = shutil.which(exe_name)
            if found_in_path:
                return str(Path(found_in_path).resolve())

        return None

    @property
    def is_available(self) -> bool:
        """Indica si tanto FFmpeg como FFprobe fueron encontrados y existen en el disco.

        Returns:
            bool: True si ambos ejecutables están presentes, False en caso contrario.
        """
        return bool(
            self.ffmpeg_path
            and self.ffprobe_path
            and Path(self.ffmpeg_path).is_file()
            and Path(self.ffprobe_path).is_file()
        )

    def get_ffmpeg(self) -> str:
        """Obtiene la ruta absoluta al ejecutable ffmpeg.exe.

        Returns:
            str: Ruta absoluta del ejecutable FFmpeg.

        Raises:
            FileNotFoundError: Si no se encuentra el binario de FFmpeg.
        """
        if not self.ffmpeg_path or not Path(self.ffmpeg_path).is_file():
            raise FileNotFoundError(
                "No se encontró el ejecutable de FFmpeg. "
                "Verifique que ffmpeg.exe se encuentre en 'DescaradorConvertidor/ffmpeg/bin/', "
                "'ffmpeg/bin/' o esté configurado en el PATH del sistema."
            )
        return self.ffmpeg_path

    def get_ffprobe(self) -> str:
        """Obtiene la ruta absoluta al ejecutable ffprobe.exe.

        Returns:
            str: Ruta absoluta del ejecutable FFprobe.

        Raises:
            FileNotFoundError: Si no se encuentra el binario de FFprobe.
        """
        if not self.ffprobe_path or not Path(self.ffprobe_path).is_file():
            raise FileNotFoundError(
                "No se encontró el ejecutable de FFprobe. "
                "Verifique que ffprobe.exe se encuentre en 'DescaradorConvertidor/ffmpeg/bin/', "
                "'ffmpeg/bin/' o esté configurado en el PATH del sistema."
            )
        return self.ffprobe_path

    def get_version(self) -> str:
        """Ejecuta 'ffmpeg -version' y extrae la primera línea de salida.

        Returns:
            str: Primera línea informativa con la versión de FFmpeg.

        Raises:
            FileNotFoundError: Si el binario no está disponible.
            RuntimeError: Si ocurre un error durante la ejecución del subproceso.
        """
        ffmpeg_exe = self.get_ffmpeg()
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        try:
            result = subprocess.run(
                [ffmpeg_exe, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=True,
            )
            lines = result.stdout.strip().splitlines()
            if lines:
                return lines[0].strip()
            return ""
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(
                f"Error al ejecutar FFmpeg para obtener la versión: {error_msg}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Fallo inesperado al consultar la versión de FFmpeg: {e}"
            ) from e

    def get_media_duration(self, file_path: str) -> float:
        """Obtiene la duración en segundos de un archivo multimedia usando FFprobe.

        Args:
            file_path: Ruta al archivo multimedia a consultar.

        Returns:
            float: Duración total del archivo en segundos.

        Raises:
            FileNotFoundError: Si el archivo multimedia o FFprobe no existen.
            RuntimeError: Si ocurre un error al consultar el archivo con FFprobe.
        """
        target = Path(file_path).resolve()
        if not target.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo multimedia especificado: {file_path}"
            )

        ffprobe_exe = self.get_ffprobe()
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        cmd = [
            ffprobe_exe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(target),
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=True,
            )
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line and line != "N/A":
                    try:
                        val = float(line)
                        if val > 0:
                            return val
                    except ValueError:
                        continue

            for line in result.stdout.strip().splitlines():
                try:
                    return float(line.strip())
                except ValueError:
                    continue

            return 0.0
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(
                f"FFprobe reportó un error al calcular la duración de '{file_path}': {error_msg}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error al obtener la duración de '{file_path}': {e}"
            ) from e

    def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Obtiene información completa (duración, códec, resolución, bitrate, etc.)
        de un archivo multimedia como un diccionario estructurado utilizando FFprobe.

        Args:
            file_path: Ruta al archivo multimedia a analizar.

        Returns:
            Dict[str, Any]: Diccionario con la metadata detallada del archivo multimedia.

        Raises:
            FileNotFoundError: Si el archivo multimedia o FFprobe no existen.
            RuntimeError: Si la consulta falla o los datos devueltos no son válidos.
        """
        target = Path(file_path).resolve()
        if not target.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo multimedia especificado: {file_path}"
            )

        ffprobe_exe = self.get_ffprobe()
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        cmd = [
            ffprobe_exe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(target),
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=True,
            )
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(
                f"FFprobe falló al obtener información de '{file_path}': {error_msg}"
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Respuesta JSON no válida de FFprobe para '{file_path}': {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error al obtener la información multimedia de '{file_path}': {e}"
            ) from e

        streams = data.get("streams", [])
        format_info = data.get("format", {})

        video_stream = next(
            (s for s in streams if s.get("codec_type") == "video"), None
        )
        audio_stream = next(
            (s for s in streams if s.get("codec_type") == "audio"), None
        )

        duration: float = 0.0
        for cand in [
            format_info.get("duration"),
            video_stream.get("duration") if video_stream else None,
            audio_stream.get("duration") if audio_stream else None,
        ]:
            if cand is not None and cand != "N/A":
                try:
                    duration = float(cand)
                    break
                except (ValueError, TypeError):
                    pass

        width = video_stream.get("width") if video_stream else None
        height = video_stream.get("height") if video_stream else None
        resolution = f"{width}x{height}" if (width and height) else None

        video_codec = video_stream.get("codec_name") if video_stream else None
        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        codec = video_codec or audio_codec

        bitrate = (
            format_info.get("bit_rate")
            or (video_stream.get("bit_rate") if video_stream else None)
            or (audio_stream.get("bit_rate") if audio_stream else None)
        )

        size = None
        size_raw = format_info.get("size")
        if size_raw is not None:
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                pass

        return {
            "duration": duration,
            "codec": codec,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "resolution": resolution,
            "width": width,
            "height": height,
            "bitrate": bitrate,
            "size": size,
            "format_name": format_info.get("format_name"),
            "format_long_name": format_info.get("format_long_name"),
            "streams": streams,
            "format": format_info,
        }


def get_manager() -> FFmpegManager:
    """Devuelve la instancia única (singleton) de FFmpegManager.

    Returns:
        FFmpegManager: Instancia global del administrador de FFmpeg.
    """
    return FFmpegManager()

import os
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

from src.core.ffmpeg_manager import get_manager

FORMATOS_VIDEO = ['mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', 'wmv', 'gif']
FORMATOS_AUDIO = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'wma']

PRESETS_COMPRESION = {
    'whatsapp_16mb': {'max_size_mb': 16, 'label': 'WhatsApp (16 MB)'},
    'whatsapp_64mb': {'max_size_mb': 64, 'label': 'WhatsApp (64 MB)'},
    'discord_25mb': {'max_size_mb': 25, 'label': 'Discord (25 MB)'},
    'discord_50mb': {'max_size_mb': 50, 'label': 'Discord (50 MB)'},
    'custom': {'max_size_mb': None, 'label': 'Personalizado'},
}

@dataclass
class ConversionProgress:
    """Clase para representar el progreso de la conversión."""
    status: str
    percent: float
    elapsed_time: str
    eta: str
    current_size: str

class Converter:
    """Clase para manejar las conversiones, compresiones y recortes con FFmpeg."""
    
    def __init__(self):
        """Inicializa el convertidor con las rutas de los binarios."""
        manager = get_manager()
        self._ffmpeg_path = manager.get_ffmpeg()
        self._ffprobe_path = manager.get_ffprobe()
        self._process: Optional[subprocess.Popen] = None
        self._cancelled: bool = False
        self.last_error: Optional[str] = None

    def cancel(self):
        """Cancela la operación actual."""
        self._cancelled = True
        if self._process is not None:
            try:
                self._process.kill()
            except Exception:
                pass

    def reset(self):
        """Restablece el estado de cancelación y error."""
        self._cancelled = False
        self.last_error = None

    def _get_duration(self, file_path: str) -> float:
        """Obtiene la duración del archivo multimedia en segundos utilizando ffprobe."""
        try:
            cmd = [
                self._ffprobe_path,
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, check=True, creationflags=creationflags
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _format_time(self, seconds: float) -> str:
        """Formatea un tiempo en segundos a un string HH:MM:SS."""
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02}:{minutes:02}:{secs:02}"
        return f"{minutes:02}:{secs:02}"

    def _format_size(self, bytes_size: int) -> str:
        """Formatea el tamaño en bytes a MB/KB."""
        if bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        return f"{bytes_size / (1024 * 1024):.1f} MB"

    def _run_ffmpeg(self, cmd: list[str], total_duration: float, progress_callback: Optional[Callable[[ConversionProgress], None]], status_label: str, percent_offset: float = 0.0, percent_range: float = 100.0) -> bool:
        """Ejecuta un comando de FFmpeg y reporta el progreso.

        Drena stderr en un hilo secundario para evitar deadlocks en Windows
        cuando el búfer de la tubería se llena con advertencias de FFmpeg.
        Almacena las últimas líneas de stderr en self.last_error si el
        proceso termina con error.
        """
        if self._cancelled:
            return False

        full_cmd = [self._ffmpeg_path] + cmd
        # Insertar flags de progreso y sobrescritura
        if "-y" not in full_cmd:
            full_cmd.insert(1, "-y")

        # Necesitamos el output de progress, así que agregamos flags
        full_cmd.extend(["-progress", "pipe:1", "-nostats"])

        # Buffer circular para capturar las últimas líneas de stderr
        stderr_lines: deque[str] = deque(maxlen=30)

        def _drain_stderr(pipe):
            """Lee stderr línea por línea en un hilo aparte para evitar
            que el búfer de la tubería se llene y bloquee el proceso."""
            try:
                for raw_line in pipe:
                    stderr_lines.append(raw_line.rstrip())
            except Exception:
                pass

        try:
            self._process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Iniciar hilo de drenado de stderr
            stderr_thread = threading.Thread(
                target=_drain_stderr,
                args=(self._process.stderr,),
                daemon=True
            )
            stderr_thread.start()

            start_time = time.time()

            while self._process.poll() is None:
                if self._cancelled:
                    self._process.kill()
                    return False

                line = self._process.stdout.readline()
                if not line:
                    continue

                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        out_time_ms = int(line.split("=")[1])
                        out_time_sec = out_time_ms / 1_000_000.0

                        percent = 0.0
                        if total_duration > 0:
                            percent = (out_time_sec / total_duration) * 100.0

                        if percent > 100.0:
                            percent = 100.0

                        final_percent = percent_offset + (percent * percent_range / 100.0)

                        elapsed = time.time() - start_time
                        eta_sec = 0.0
                        if final_percent > 0:
                            total_estimated = elapsed / (final_percent / 100.0)
                            eta_sec = total_estimated - elapsed

                        if progress_callback:
                            progress_callback(ConversionProgress(
                                status=status_label,
                                percent=final_percent,
                                elapsed_time=self._format_time(elapsed),
                                eta=self._format_time(eta_sec),
                                current_size=""
                            ))
                    except ValueError:
                        pass

            # Esperar a que termine el hilo de drenado de stderr
            stderr_thread.join(timeout=5)

            # Capturar error real si FFmpeg falló
            if self._process.returncode != 0:
                error_text = "\n".join(stderr_lines).strip()
                if error_text:
                    self.last_error = error_text

            return self._process.returncode == 0

        except Exception as e:
            self.last_error = str(e)
            return False
        finally:
            self._process = None

    def convert(self, input_path: str, output_path: str, progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Convierte un archivo multimedia de un formato a otro."""
        self.reset()
        duration = self._get_duration(input_path)
        
        # Intentar stream copy primero
        cmd_copy = ["-i", input_path, "-c", "copy", output_path]
        if self._run_ffmpeg(cmd_copy, duration, progress_callback, "converting"):
            if progress_callback:
                progress_callback(ConversionProgress("finished", 100.0, "", "", ""))
            return True
            
        if self._cancelled:
            return False
            
        # Si copy falla, re-codificar completamente
        cmd_encode = ["-i", input_path, output_path]
        success = self._run_ffmpeg(cmd_encode, duration, progress_callback, "converting")
        
        if success and progress_callback:
            progress_callback(ConversionProgress("finished", 100.0, "", "", ""))
            
        return success

    def compress_video(self, input_path: str, output_path: str, preset: str = 'whatsapp_16mb', custom_size_mb: Optional[float] = None, progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Comprime un video para un tamaño específico usando 2 pasadas."""
        self.reset()
        
        target_size_mb = custom_size_mb
        if preset in PRESETS_COMPRESION and PRESETS_COMPRESION[preset]['max_size_mb'] is not None:
            target_size_mb = PRESETS_COMPRESION[preset]['max_size_mb']
            
        if not target_size_mb:
            return False
            
        duration = self._get_duration(input_path)
        if duration <= 0:
            return False
            
        target_size_bytes = target_size_mb * 1024 * 1024
        
        # Audio bitrate = 128k = 128 * 1024 bits/s
        audio_bitrate = 128 * 1024
        
        # Calcular target_bitrate en bits por segundo
        # target_size_bytes * 8 = total de bits
        # total_bitrate = total_bits / duration
        # video_bitrate = total_bitrate - audio_bitrate
        total_bitrate = (target_size_bytes * 8) / duration
        video_bitrate = total_bitrate - audio_bitrate
        
        if video_bitrate <= 0:
            video_bitrate = 100 * 1024 # Min bitrate 100k
            
        video_bitrate_k = int(video_bitrate / 1024)
        
        # Crear directorio temporal para los archivos de log de las 2 pasadas
        passlog_dir = tempfile.mkdtemp(prefix="smp_passlog_")
        passlog_prefix = os.path.join(passlog_dir, "ffmpeg2pass")
        
        # Pasada 1
        cmd_pass1 = [
            "-y", "-i", input_path,
            "-c:v", "libx264",
            "-b:v", f"{video_bitrate_k}k",
            "-pass", "1",
            "-passlogfile", passlog_prefix,
            "-an",
            "-f", "null",
            "NUL" if os.name == 'nt' else "/dev/null"
        ]
        
        success_pass1 = self._run_ffmpeg(cmd_pass1, duration, progress_callback, "compressing", 0.0, 50.0)
        
        if not success_pass1 or self._cancelled:
            self._cleanup_passlog_dir(passlog_dir)
            return False
            
        # Pasada 2
        cmd_pass2 = [
            "-y", "-i", input_path,
            "-c:v", "libx264",
            "-b:v", f"{video_bitrate_k}k",
            "-pass", "2",
            "-passlogfile", passlog_prefix,
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]
        
        success_pass2 = self._run_ffmpeg(cmd_pass2, duration, progress_callback, "compressing", 50.0, 50.0)
        
        self._cleanup_passlog_dir(passlog_dir)
        
        if success_pass2 and progress_callback:
            progress_callback(ConversionProgress("finished", 100.0, "", "", ""))
            
        return success_pass2

    def _cleanup_passlog_dir(self, passlog_dir: str):
        """Limpia el directorio temporal de los archivos de log de 2 pasadas."""
        try:
            import shutil
            if os.path.isdir(passlog_dir):
                shutil.rmtree(passlog_dir, ignore_errors=True)
        except Exception:
            pass

    def _cleanup_passlogs(self):
        """Limpia archivos de registro residuales en el directorio de trabajo (compatibilidad)."""
        for file in os.listdir("."):
            if file.startswith("ffmpeg2pass"):
                try:
                    os.remove(file)
                except Exception:
                    pass

    def extract_audio(self, input_path: str, output_path: str, audio_format: str = 'mp3', bitrate: str = '192k', progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Extrae el audio de un archivo multimedia."""
        self.reset()
        duration = self._get_duration(input_path)
        
        codecs = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'flac': 'flac',
            'wav': 'pcm_s16le',
            'ogg': 'libvorbis',
            'm4a': 'aac',
            'wma': 'wmav2'
        }
        
        codec = codecs.get(audio_format, 'libmp3lame')
        
        cmd = [
            "-i", input_path,
            "-vn",
            "-acodec", codec,
            "-b:a", bitrate,
            output_path
        ]
        
        success = self._run_ffmpeg(cmd, duration, progress_callback, "extracting")
        
        if success and progress_callback:
            progress_callback(ConversionProgress("finished", 100.0, "", "", ""))
            
        return success

    def trim(self, input_path: str, output_path: str, start_time: str, end_time: str, progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Recorta un archivo multimedia desde un tiempo de inicio hasta un tiempo de fin."""
        self.reset()
        
        def parse_time(time_str: str) -> float:
            try:
                if ":" in time_str:
                    parts = time_str.split(":")
                    if len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    elif len(parts) == 2:
                        return int(parts[0]) * 60 + float(parts[1])
                return float(time_str)
            except Exception:
                return 0.0
                
        start_sec = parse_time(start_time)
        end_sec = parse_time(end_time)
        duration = end_sec - start_sec if end_sec > start_sec else self._get_duration(input_path) - start_sec
        
        cmd = [
            "-ss", start_time,
            "-to", end_time,
            "-i", input_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        
        success = self._run_ffmpeg(cmd, duration, progress_callback, "trimming")
        
        if success and progress_callback:
            progress_callback(ConversionProgress("finished", 100.0, "", "", ""))
            
        return success

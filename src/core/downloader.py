"""
Módulo de motor de descarga para la suite multimedia.
Utiliza yt-dlp para soportar múltiples plataformas (YouTube, TikTok, Instagram, etc.).
"""

import os
import re
import threading
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
import yt_dlp

from src.core.ffmpeg_manager import get_manager

@dataclass
class MediaInfo:
    """Información extraída de un enlace multimedia."""
    title: str
    channel: str
    duration: float  # segundos
    duration_str: str  # formato como '5:23'
    thumbnail_url: str
    url: str
    is_playlist: bool
    playlist_title: Optional[str]
    playlist_count: Optional[int]
    formats_available: List[str]  # ej. ['2160p', '1440p', '1080p', '720p', '480p', '360p']
    estimated_filesize: Optional[int]  # bytes
    platform: str  # 'youtube', 'tiktok', etc.

@dataclass
class DownloadProgress:
    """Progreso de la descarga para actualizar la interfaz."""
    status: str  # 'downloading', 'converting', 'finished', 'error'
    percent: float  # 0-100
    speed: str  # ej. '5.2 MiB/s'
    eta: str  # ej. '00:32'
    downloaded: str  # ej. '45.3 MiB'
    total: str  # ej. '120.5 MiB'
    filename: str

class DownloaderException(Exception):
    """Excepción personalizada para errores del descargador."""
    pass

class CancelledError(Exception):
    """Excepción para cuando se cancela la descarga."""
    pass

class Downloader:
    """Clase principal encargada de manejar descargas con yt-dlp."""

    def __init__(self):
        """Inicializa el descargador y configura la ruta de FFmpeg."""
        self._cancel_flag = threading.Event()
        self.ffmpeg_path = get_manager().get_ffmpeg()
        self.last_error: Optional[str] = None
        
    def _format_duration(self, seconds: float) -> str:
        """Formatea segundos a cadena de texto (ej. MM:SS)."""
        if not seconds:
            return "0:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
        
    def _clean_ansi(self, text: str) -> str:
        """Elimina códigos de escape ANSI de una cadena."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def extract_info(self, url: str) -> MediaInfo:
        """Extrae metadatos del enlace sin descargarlo."""
        opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': self.ffmpeg_path,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise DownloaderException("No se pudo extraer información del enlace.")

                is_playlist = 'entries' in info
                
                # Extraer formatos de video disponibles
                formats_available = []
                if not is_playlist and 'formats' in info:
                    heights = set()
                    for f in info['formats']:
                        h = f.get('height')
                        if h and isinstance(h, int) and h >= 360:
                            heights.add(h)
                    
                    # Convertir a lista de strings
                    valid_res = sorted(list(heights), reverse=True)
                    formats_available = [f"{h}p" for h in valid_res]
                    if not formats_available:
                        formats_available = ['best']

                platform = info.get('extractor_key', 'Desconocido').lower()
                
                duration = float(info.get('duration', 0) or 0)
                
                return MediaInfo(
                    title=info.get('title', 'Sin título'),
                    channel=info.get('uploader', info.get('channel', 'Desconocido')),
                    duration=duration,
                    duration_str=self._format_duration(duration),
                    thumbnail_url=info.get('thumbnail', ''),
                    url=info.get('webpage_url', url),
                    is_playlist=is_playlist,
                    playlist_title=info.get('title') if is_playlist else None,
                    playlist_count=info.get('playlist_count') if is_playlist else None,
                    formats_available=formats_available,
                    estimated_filesize=info.get('filesize_approx', info.get('filesize')),
                    platform=platform
                )
        except Exception as e:
            raise DownloaderException(f"Error al extraer información: {str(e)}")

    def cancel(self):
        """Marca la bandera de cancelación."""
        self._cancel_flag.set()

    def reset(self):
        """Restablece la bandera de cancelación y el error."""
        self._cancel_flag.clear()
        self.last_error = None

    def _get_video_format_string(self, quality: str) -> str:
        """Obtiene la cadena de formato para yt-dlp según la calidad deseada.

        Ya no se fuerza [ext=mp4] porque en YouTube las calidades 1080p+
        usan VP9/AV1 con audio Opus. Se deja que yt-dlp elija el mejor
        códec disponible y FFmpeg combine las pistas en MP4 final
        (controlado por 'merge_output_format' en las opciones de descarga).
        """
        if quality == 'best':
            return 'bestvideo+bestaudio/best'

        # Eliminar 'p' si está presente y obtener altura
        h = quality.replace('p', '')
        if h.isdigit():
            return f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'

        return 'bestvideo+bestaudio/best'

    def download(self, 
                 url: str, 
                 output_dir: str, 
                 media_type: str, 
                 format_quality: str, 
                 is_playlist: bool, 
                 audio_bitrate: str = '192', 
                 audio_format: str = 'mp3', 
                 embed_thumbnail: bool = True, 
                 embed_metadata: bool = True, 
                 cookies_browser: Optional[str] = None, 
                 progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> bool:
        """
        Descarga el medio según los parámetros proporcionados.
        """
        self.reset()
        
        # Plantilla de salida: playlists en subcarpeta numerada, individuales sueltas
        if is_playlist:
            outtmpl = os.path.join(
                output_dir,
                '%(playlist_title)s',
                '%(playlist_index)02d - %(title)s.%(ext)s'
            )
        else:
            outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')
        
        # Configuración básica
        opts: Dict[str, Any] = {
            'outtmpl': outtmpl,
            'ffmpeg_location': self.ffmpeg_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'noplaylist': not is_playlist,
            'ignoreerrors': is_playlist,  # Saltar videos caídos en playlists
        }

        # Cookies
        if cookies_browser:
            opts['cookiesfrombrowser'] = [cookies_browser]

        # Configurar para Audio o Video
        if media_type == 'audio':
            opts['format'] = 'bestaudio/best'
            postprocessors: List[Dict[str, Any]] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': audio_bitrate,
            }]
            
            if embed_metadata:
                postprocessors.append({'key': 'FFmpegMetadata'})
                
            if embed_thumbnail:
                postprocessors.append({'key': 'EmbedThumbnail'})
                opts['writethumbnail'] = True
                
            opts['postprocessors'] = postprocessors
        else:
            # Video: FFmpeg combina las pistas descargadas (VP9+Opus, etc.) en MP4
            opts['format'] = self._get_video_format_string(format_quality)
            opts['merge_output_format'] = 'mp4'
            if embed_metadata:
                opts['postprocessors'] = [{'key': 'FFmpegMetadata'}]

        # Hook de progreso
        def progress_hook(d: Dict[str, Any]):
            if self._cancel_flag.is_set():
                raise CancelledError("Descarga cancelada por el usuario.")

            if not progress_callback:
                return

            status = d.get('status', 'unknown')
            
            if status == 'downloading':
                # Parsear progreso
                percent_str = self._clean_ansi(d.get('_percent_str', '0.0%')).strip('%')
                try:
                    percent = float(percent_str)
                except ValueError:
                    percent = 0.0

                prog = DownloadProgress(
                    status='downloading',
                    percent=percent,
                    speed=self._clean_ansi(d.get('_speed_str', 'N/A')).strip(),
                    eta=self._clean_ansi(d.get('_eta_str', 'N/A')).strip(),
                    downloaded=self._clean_ansi(d.get('_downloaded_bytes_str', 'N/A')).strip(),
                    total=self._clean_ansi(d.get('_total_bytes_str', d.get('_estimated_total_bytes_str', 'N/A'))).strip(),
                    filename=os.path.basename(d.get('filename', ''))
                )
                progress_callback(prog)
                
            elif status == 'finished':
                prog = DownloadProgress(
                    status='converting',
                    percent=100.0,
                    speed='',
                    eta='',
                    downloaded='',
                    total='',
                    filename=os.path.basename(d.get('filename', ''))
                )
                progress_callback(prog)
                
            elif status == 'error':
                prog = DownloadProgress(
                    status='error',
                    percent=0.0,
                    speed='',
                    eta='',
                    downloaded='',
                    total='',
                    filename=os.path.basename(d.get('filename', ''))
                )
                progress_callback(prog)

        opts['progress_hooks'] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                
                # Reportar completado si no fue cancelado
                if not self._cancel_flag.is_set() and progress_callback:
                    prog = DownloadProgress(
                        status='finished',
                        percent=100.0,
                        speed='',
                        eta='',
                        downloaded='',
                        total='',
                        filename=''
                    )
                    progress_callback(prog)
                return True
                
        except CancelledError:
            return False
        except Exception as e:
            err_str = str(e)
            # Si falló porque las cookies del navegador están bloqueadas o encriptadas con DPAPI (Chrome 127+),
            # reintentar automáticamente sin cookies para permitir descargas públicas
            if 'cookiesfrombrowser' in opts and any(k in err_str.lower() for k in ['cookie', 'could not copy', 'database', 'dpapi', 'decrypt']):
                try:
                    opts_no_cookies = dict(opts)
                    opts_no_cookies.pop('cookiesfrombrowser', None)
                    with yt_dlp.YoutubeDL(opts_no_cookies) as ydl_retry:
                        ydl_retry.download([url])
                        if not self._cancel_flag.is_set() and progress_callback:
                            prog = DownloadProgress(
                                status='finished',
                                percent=100.0,
                                speed='',
                                eta='',
                                downloaded='',
                                total='',
                                filename=''
                            )
                            progress_callback(prog)
                        return True
                except CancelledError:
                    return False
                except Exception as retry_err:
                    err_str = str(retry_err)

            # Capturar el error real para exponerlo en la cola/UI
            self.last_error = err_str
            if progress_callback:
                prog = DownloadProgress(
                    status='error',
                    percent=0.0,
                    speed='',
                    eta='',
                    downloaded='',
                    total='',
                    filename=''
                )
                progress_callback(prog)
            return False

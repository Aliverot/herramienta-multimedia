"""
Script para compilar Herramienta Multimedia como ejecutable portable (.exe).
Usa PyInstaller para empaquetar la aplicación con FFmpeg incluido.

Ejecución: python build_exe.py
"""

import os
import subprocess
import sys

# Forzar UTF-8 en la consola de Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Rutas del proyecto
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FFMPEG_BIN_DIR = os.path.join(PROJECT_ROOT, "DescaradorConvertidor", "ffmpeg", "bin")
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")
ICON_PATH = None  # Opcional: ruta a un archivo .ico para el ejecutable

# Archivos de FFmpeg a incluir
FFMPEG_FILES = []
if os.path.isdir(FFMPEG_BIN_DIR):
    for f in os.listdir(FFMPEG_BIN_DIR):
        full_path = os.path.join(FFMPEG_BIN_DIR, f)
        if os.path.isfile(full_path):
            FFMPEG_FILES.append(full_path)


def build():
    """Construye el ejecutable con PyInstaller."""
    print("=" * 60)
    print("  Herramienta Multimedia - Compilador de Ejecutable")
    print("=" * 60)
    print()

    if not os.path.isfile(MAIN_SCRIPT):
        print(f"❌ Error: No se encontró {MAIN_SCRIPT}")
        sys.exit(1)

    # Construir lista de --add-data para FFmpeg
    add_data_args = []
    for ffmpeg_file in FFMPEG_FILES:
        # En Windows el separador es ';'
        add_data_args.extend([
            "--add-data", f"{ffmpeg_file};ffmpeg/bin"
        ])

    print(f"📦 Archivos de FFmpeg a incluir: {len(FFMPEG_FILES)}")
    for f in FFMPEG_FILES:
        print(f"   • {os.path.basename(f)}")
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "DescargarConvertir",
        "--clean",
    ]

    # Agregar ícono si existe
    if ICON_PATH and os.path.isfile(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    # Agregar archivos de FFmpeg
    cmd.extend(add_data_args)

    # Hidden imports necesarios
    hidden_imports = [
        "customtkinter",
        "darkdetect",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "yt_dlp",
        "src",
        "src.core",
        "src.core.ffmpeg_manager",
        "src.core.downloader",
        "src.core.converter",
        "src.core.queue_manager",
        "src.ui",
        "src.ui.app",
        "src.ui.tab_download",
        "src.ui.tab_convert",
        "src.ui.tab_queue",
        "src.ui.tab_settings",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Agregar datos de CustomTkinter
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        cmd.extend(["--add-data", f"{ctk_path};customtkinter"])
        print(f"✅ CustomTkinter encontrado en: {ctk_path}")
    except ImportError:
        print("⚠️  CustomTkinter no encontrado, puede fallar la compilación.")

    # Script principal
    cmd.append(MAIN_SCRIPT)

    print(f"\n🔨 Ejecutando PyInstaller...")
    print(f"   Comando: {' '.join(cmd[:8])}...\n")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        import shutil
        release_dir = os.path.join(PROJECT_ROOT, "SuiteMultimedia_Portable")
        os.makedirs(release_dir, exist_ok=True)
        exe_src = os.path.join(PROJECT_ROOT, "dist", "DescargarConvertir.exe")
        if os.path.isfile(exe_src):
            shutil.copy2(exe_src, os.path.join(release_dir, "DescargarConvertir.exe"))
        ffmpeg_src = os.path.join(PROJECT_ROOT, "DescaradorConvertidor", "ffmpeg")
        if os.path.isdir(ffmpeg_src) and not os.path.isdir(os.path.join(release_dir, "ffmpeg")):
            shutil.copytree(ffmpeg_src, os.path.join(release_dir, "ffmpeg"))
        print()
        print("=" * 60)
        print("  ¡Compilación exitosa!")
        print(f"  Ejecutable standalone listo en: dist/DescargarConvertir.exe")
        print(f"  Carpeta portable con FFmpeg: SuiteMultimedia_Portable/")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("  ❌ Error durante la compilación.")
        print("  Revisa los mensajes de error arriba.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    build()

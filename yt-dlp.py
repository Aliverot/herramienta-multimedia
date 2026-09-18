import yt_dlp

def descargar_media(url, tipo, es_playlist=False):
    """Configura yt-dlp según el tipo y si es una lista de reproducción."""
    
    # 📁 MAGIA DE CARPETAS: 
    # Si es playlist, crea una carpeta con el título de la lista y numera los archivos.
    # Si no, simplemente guarda el archivo suelto con su título.
    if es_playlist:
        plantilla_salida = '%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s'
    else:
        plantilla_salida = '%(title)s.%(ext)s'

    if tipo == 'audio':
        opciones = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': plantilla_salida,
            # Si elegiste individual, bloquea las playlists (útil si el enlace tiene un "&list=")
            'noplaylist': not es_playlist, 
            'ignoreerrors': True # Si un video de la lista está borrado, lo salta y sigue con el resto
        }
    elif tipo == 'video':
        opciones = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': plantilla_salida,
            'noplaylist': not es_playlist,
            'ignoreerrors': True
        }
    else:
        return

    texto_tipo = "Lista de " + tipo if es_playlist else tipo
    print(f"\n⏳ Iniciando descarga de {texto_tipo}...")
    
    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            ydl.download([url])
        print(f"✅ ¡Descarga de {texto_tipo} completada con éxito!\n")
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}\n")


def menu_principal():
    """Muestra el menú interactivo al usuario."""
    print("=== 🎬 Descargador Pro de yt-dlp 🎵 ===")
    
    while True:
        print("\n¿Qué deseas hacer?")
        print("1. 🎵 Descargar UNA canción (Solo Audio MP3)")
        print("2. 🎬 Descargar UN video (Video + Audio MP4)")
        print("3. 📚 Descargar PLAYLIST completa de música (Audio MP3)")
        print("4. 📽️ Descargar PLAYLIST completa de videos (Video MP4)")
        print("5. ❌ Salir del programa")
        
        opcion = input("\n👉 Elige una opción (1-5): ")
        
        if opcion == '5':
            print("¡Hasta luego! Cerrando programa...")
            break
            
        elif opcion in ['1', '2', '3', '4']:
            enlace = input("🔗 Pega el enlace aquí: ")
            
            if opcion == '1':
                descargar_media(enlace, 'audio', es_playlist=False)
            elif opcion == '2':
                descargar_media(enlace, 'video', es_playlist=False)
            elif opcion == '3':
                descargar_media(enlace, 'audio', es_playlist=True)
            elif opcion == '4':
                descargar_media(enlace, 'video', es_playlist=True)
        else:
            print("⚠️ Opción no válida. Por favor, escribe un número del 1 al 5.\n")

if __name__ == "__main__":
    menu_principal()
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import subprocess
import threading
import os
import time
import re

# --- LISTAS DE FORMATOS ---
FORMATOS_VIDEO = ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv", "gif"]
FORMATOS_AUDIO = ["mp3", "wav", "m4a", "flac", "ogg", "aac", "wma"]

# --- VARIABLES GLOBALES ---
cancelar_flag = False
proceso_ffmpeg = None

# --- FUNCIONES DE CONTROL ---

def cancelar_proceso():
    global cancelar_flag, proceso_ffmpeg
    cancelar_flag = True
    etiqueta_estado.config(text="Estado: Cancelando, por favor espera...", fg="orange")
    
    if proceso_ffmpeg is not None:
        try:
            proceso_ffmpeg.kill()
        except:
            pass

def reiniciar_interfaz():
    boton_descargar.config(state="normal")
    boton_convertir.config(state="normal" if combo_formatos.get() else "disabled")
    boton_cancelar.config(state="disabled")
    barra_progreso.stop()
    barra_progreso.config(mode='determinate', value=0)

class CanceladoPorUsuario(Exception):
    pass

def abrir_carpeta(ruta):
    """Abre la carpeta en el explorador de archivos de Windows."""
    try:
        os.startfile(ruta)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

# --- SECCIÓN DE DESCARGA ---

def hook_progreso(d):
    global cancelar_flag
    if cancelar_flag:
        raise CanceladoPorUsuario("Descarga cancelada por el usuario.")
        
    if d['status'] == 'downloading':
        porcentaje_str = d.get('_percent_str', '0.0%')
        porcentaje_limpio = re.sub(r'\x1b\[[0-9;]*m', '', porcentaje_str).replace('%', '').strip()
        try:
            porcentaje = float(porcentaje_limpio)
            ventana.after(0, lambda: barra_progreso.config(value=porcentaje))
        except ValueError:
            pass

def seleccionar_carpeta_destino():
    ruta = filedialog.askdirectory(title="Selecciona la carpeta de destino")
    if ruta:
        variable_ruta.set(ruta)

def iniciar_descarga():
    global cancelar_flag
    url = entrada_url.get()
    opcion = combo_opciones.get()
    calidad = combo_calidad.get()
    carpeta_destino = variable_ruta.get()
    
    if not url:
        messagebox.showwarning("Advertencia", "Por favor, ingresa un enlace.")
        return
    if not os.path.isdir(carpeta_destino):
        messagebox.showwarning("Advertencia", "La ruta de destino no es válida.")
        return

    cancelar_flag = False
    boton_descargar.config(state="disabled")
    boton_convertir.config(state="disabled")
    boton_cancelar.config(state="normal")
    barra_progreso.config(mode='determinate', value=0)
    etiqueta_estado.config(text="Estado: Preparando descarga...", fg="blue")
    
    tipo = 'audio' if 'Audio' in opcion else 'video'
    es_playlist = 'Playlist' in opcion

    hilo = threading.Thread(target=procesar_descarga, args=(url, tipo, es_playlist, calidad, carpeta_destino))
    hilo.start()

def procesar_descarga(url, tipo, es_playlist, calidad, carpeta_destino):
    plantilla_salida = '%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s' if es_playlist else '%(title)s.%(ext)s'

    opciones = {
        'paths': {'home': carpeta_destino}, 
        'outtmpl': plantilla_salida,
        'noplaylist': not es_playlist,
        # ⚠️ SOLUCIÓN: Solo ignora errores si es una playlist
        'ignoreerrors': es_playlist, 
        'progress_hooks': [hook_progreso]
    }

    if tipo == 'audio':
        opciones.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    elif tipo == 'video':
        if calidad == "Mejor disponible":
            formato_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            res = calidad.replace('p', '')
            formato_str = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
        opciones.update({'format': formato_str})

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            # ydl.download devuelve 0 si fue exitoso, u otro número si hubo fallos
            codigo_retorno = ydl.download([url])
            
        if not cancelar_flag:
            if codigo_retorno != 0 and es_playlist:
                # Si es playlist y hubo errores (ej. algunos videos borrados/privados)
                ventana.after(0, lambda: etiqueta_estado.config(text="Estado: Playlist con advertencias", fg="orange"))
                def mostrar_aviso():
                    respuesta = messagebox.askyesno("Aviso", f"La playlist se procesó, pero algunos elementos fallaron o no están disponibles.\n\n¿Deseas abrir la carpeta de destino?")
                    if respuesta:
                        abrir_carpeta(carpeta_destino)
                ventana.after(0, mostrar_aviso)
                
            elif codigo_retorno != 0 and not es_playlist:
                # Si es un solo archivo y falló, forzamos el error
                raise Exception("El enlace proporcionado no es compatible o el contenido no está disponible.")
                
            else:
                # Éxito total y limpio
                ventana.after(0, lambda: etiqueta_estado.config(text="Estado: ¡Descarga completada!", fg="green"))
                def mostrar_exito():
                    respuesta = messagebox.askyesno("Éxito", f"Descarga finalizada.\nGuardado en:\n{carpeta_destino}\n\n¿Deseas abrir la carpeta ahora?")
                    if respuesta:
                        abrir_carpeta(carpeta_destino)
                ventana.after(0, mostrar_exito)
            
    except CanceladoPorUsuario:
        ventana.after(0, lambda: etiqueta_estado.config(text="Estado: Descarga cancelada.", fg="red"))
    except Exception as e:
        if not cancelar_flag:
            ventana.after(0, lambda: etiqueta_estado.config(text="Estado: Error en la descarga", fg="red"))
            # Limpiamos el mensaje de error para que sea amigable en la ventana
            mensaje_error = str(e)
            if "Unsupported URL" in mensaje_error:
                mensaje_error = "El enlace no es compatible o no es válido para descargar."
            ventana.after(0, lambda: messagebox.showerror("Error", f"No se pudo realizar la descarga:\n{mensaje_error}"))
    finally:
        ventana.after(0, reiniciar_interfaz)

# --- SECCIÓN DEL CONVERSOR ---

def seleccionar_carpeta_destino_conv():
    ruta = filedialog.askdirectory(title="Selecciona la carpeta de destino")
    if ruta:
        variable_ruta_conv.set(ruta)

def seleccionar_archivo():
    ruta = filedialog.askopenfilename(title="Selecciona un archivo")
    if ruta:
        entrada_archivo.delete(0, tk.END)
        entrada_archivo.insert(0, ruta)
        
        # Al seleccionar un archivo, ponemos su carpeta como destino por defecto
        carpeta_origen = os.path.dirname(ruta)
        variable_ruta_conv.set(carpeta_origen)
        
        _, extension_con_punto = os.path.splitext(ruta)
        ext_original = extension_con_punto.lower().replace('.', '') 
        
        opciones_validas = []
        
        if ext_original in FORMATOS_VIDEO:
            for f in FORMATOS_VIDEO:
                if f != ext_original: opciones_validas.append(f"🎥 Video: {f}")
            for f in FORMATOS_AUDIO:
                opciones_validas.append(f"🎵 Audio: {f}")
        elif ext_original in FORMATOS_AUDIO:
            for f in FORMATOS_AUDIO:
                if f != ext_original: opciones_validas.append(f"🎵 Audio: {f}")
        else:
            for f in FORMATOS_VIDEO: opciones_validas.append(f"🎥 Video: {f}")
            for f in FORMATOS_AUDIO: opciones_validas.append(f"🎵 Audio: {f}")
            
        if opciones_validas:
            combo_formatos['values'] = opciones_validas
            combo_formatos.current(0) 
            combo_formatos.config(state="readonly")
            boton_convertir.config(state="normal")
        else:
            combo_formatos.set('')
            combo_formatos.config(state="disabled")
            boton_convertir.config(state="disabled")

def iniciar_conversion():
    global cancelar_flag
    archivo_origen = entrada_archivo.get()
    seleccion = combo_formatos.get()
    carpeta_destino = variable_ruta_conv.get()
    
    if not archivo_origen or not os.path.exists(archivo_origen) or not seleccion:
        return
    if not os.path.isdir(carpeta_destino):
        messagebox.showwarning("Advertencia", "La ruta de destino no es válida.")
        return

    cancelar_flag = False
    formato_destino = seleccion.split(": ")[1]

    if formato_destino == "mov":
        respuesta = messagebox.askyesno("Advertencia", "La conversión a MOV puede tardar bastante.\n¿Deseas continuar?")
        if not respuesta:
            return

    boton_descargar.config(state="disabled")
    boton_convertir.config(state="disabled")
    boton_cancelar.config(state="normal")
    
    barra_progreso.config(mode='indeterminate')
    barra_progreso.start(15)
    etiqueta_estado.config(text="Estado: Convirtiendo...", fg="blue")
    
    hilo = threading.Thread(target=procesar_conversion, args=(archivo_origen, formato_destino, carpeta_destino))
    hilo.start()

def procesar_conversion(archivo_origen, formato_destino, carpeta_destino):
    global proceso_ffmpeg, cancelar_flag
    
    # Extraemos solo el nombre del archivo sin la ruta ni la extensión
    nombre_base = os.path.splitext(os.path.basename(archivo_origen))[0]
    _, extension_con_punto = os.path.splitext(archivo_origen)
    ext_original = extension_con_punto.lower().replace('.', '')
    
    # Construimos la nueva ruta usando la carpeta elegida
    archivo_destino = os.path.join(carpeta_destino, f"{nombre_base}.{formato_destino}")
    
    es_mismo_tipo = (ext_original in FORMATOS_VIDEO and formato_destino in FORMATOS_VIDEO) or \
                    (ext_original in FORMATOS_AUDIO and formato_destino in FORMATOS_AUDIO)
    
    comandos_a_intentar = []
    if es_mismo_tipo:
        comandos_a_intentar.append(['ffmpeg', '-y', '-i', archivo_origen, '-c', 'copy', archivo_destino])
        
    comandos_a_intentar.append(['ffmpeg', '-y', '-i', archivo_origen, archivo_destino])
    
    exito = False
    
    for comando in comandos_a_intentar:
        if cancelar_flag:
            break
            
        try:
            proceso_ffmpeg = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            while proceso_ffmpeg.poll() is None:
                if cancelar_flag:
                    proceso_ffmpeg.kill()
                    break
                time.sleep(0.2)
                
            if proceso_ffmpeg.returncode == 0 and not cancelar_flag:
                exito = True
                break 
                
        except Exception:
            pass 

    if cancelar_flag:
        ventana.after(0, lambda: etiqueta_estado.config(text="Estado: Conversión cancelada.", fg="red"))
        if os.path.exists(archivo_destino):
            try: os.remove(archivo_destino)
            except: pass
    elif exito:
        ventana.after(0, lambda: etiqueta_estado.config(text="Estado: ¡Conversión completada!", fg="green"))
        
        # Mensaje con opción para abrir la carpeta
        def mostrar_exito_conv():
            respuesta = messagebox.askyesno("Éxito", f"Archivo convertido a {formato_destino}.\nGuardado en:\n{carpeta_destino}\n\n¿Deseas abrir la carpeta ahora?")
            if respuesta:
                abrir_carpeta(carpeta_destino)
        ventana.after(0, mostrar_exito_conv)
        
    else:
        ventana.after(0, lambda: etiqueta_estado.config(text="Estado: Error en conversión", fg="red"))
        ventana.after(0, lambda: messagebox.showerror("Error", "No se pudo convertir el archivo."))
        
    proceso_ffmpeg = None
    ventana.after(0, reiniciar_interfaz)

# --- INTERFAZ GRÁFICA ---

ventana = tk.Tk()
ventana.title("Herramienta Multimedia General")
ventana.geometry("550x650") # Ventana un poco más alta y ancha
ventana.resizable(False, False)

notebook = ttk.Notebook(ventana)
notebook.pack(pady=10, expand=True)

frame_descarga = ttk.Frame(notebook, width=530, height=430)
frame_conversion = ttk.Frame(notebook, width=530, height=430)

frame_descarga.pack(fill='both', expand=True)
frame_conversion.pack(fill='both', expand=True)

notebook.add(frame_descarga, text='Descargar Media')
notebook.add(frame_conversion, text='Convertir Archivos')

# --- Pestaña Descarga ---
tk.Label(frame_descarga, text="Enlace URL:", font=("Arial", 10, "bold")).pack(pady=(10, 0))
entrada_url = tk.Entry(frame_descarga, width=60)
entrada_url.pack(pady=5)

# Selector de Calidad
tk.Label(frame_descarga, text="Calidad de Video (Solo aplica a MP4):", font=("Arial", 9)).pack(pady=(5, 0))
combo_calidad = ttk.Combobox(frame_descarga, values=["Mejor disponible", "1080p", "720p", "480p", "360p"], width=20, state="readonly")
combo_calidad.current(0)
combo_calidad.pack(pady=5)

tk.Label(frame_descarga, text="Tipo de Descarga:", font=("Arial", 9)).pack(pady=(5, 0))
combo_opciones = ttk.Combobox(frame_descarga, values=["Canción Individual (Audio MP3)", "Video Individual (Video MP4)", "Playlist Completa (Audio MP3)", "Playlist Completa (Video MP4)"], width=40, state="readonly")
combo_opciones.current(0)
combo_opciones.pack(pady=5)

# Selector de Carpeta Descarga
tk.Label(frame_descarga, text="Guardar en:", font=("Arial", 9, "bold")).pack(pady=(10, 0))
frame_ruta = tk.Frame(frame_descarga)
frame_ruta.pack(pady=5)

ruta_por_defecto = os.path.join(os.path.expanduser('~'), 'Downloads')
if not os.path.exists(ruta_por_defecto): ruta_por_defecto = os.getcwd()

variable_ruta = tk.StringVar(value=ruta_por_defecto)
entrada_ruta = tk.Entry(frame_ruta, textvariable=variable_ruta, width=45, state="readonly")
entrada_ruta.pack(side=tk.LEFT, padx=5)

boton_ruta = tk.Button(frame_ruta, text="📂 Cambiar", command=seleccionar_carpeta_destino)
boton_ruta.pack(side=tk.LEFT)

boton_descargar = tk.Button(frame_descarga, text="Descargar", bg="lightgreen", font=("Arial", 10, "bold"), command=iniciar_descarga)
boton_descargar.pack(pady=20)

# --- Pestaña Conversión ---
tk.Label(frame_conversion, text="Archivo a convertir:", font=("Arial", 10, "bold")).pack(pady=10)
frame_seleccion = tk.Frame(frame_conversion)
frame_seleccion.pack(pady=5)

entrada_archivo = tk.Entry(frame_seleccion, width=45)
entrada_archivo.pack(side=tk.LEFT, padx=5)

boton_buscar = tk.Button(frame_seleccion, text="Buscar...", command=seleccionar_archivo)
boton_buscar.pack(side=tk.LEFT)

tk.Label(frame_conversion, text="Convertir a formato:", font=("Arial", 10)).pack(pady=10)
combo_formatos = ttk.Combobox(frame_conversion, values=[], width=20, state="disabled")
combo_formatos.pack(pady=5)

# Selector de Carpeta Conversión
tk.Label(frame_conversion, text="Guardar en:", font=("Arial", 9, "bold")).pack(pady=(10, 0))
frame_ruta_conv = tk.Frame(frame_conversion)
frame_ruta_conv.pack(pady=5)

variable_ruta_conv = tk.StringVar()
entrada_ruta_conv = tk.Entry(frame_ruta_conv, textvariable=variable_ruta_conv, width=45, state="readonly")
entrada_ruta_conv.pack(side=tk.LEFT, padx=5)

boton_ruta_conv = tk.Button(frame_ruta_conv, text="📂 Cambiar", command=seleccionar_carpeta_destino_conv)
boton_ruta_conv.pack(side=tk.LEFT)

boton_convertir = tk.Button(frame_conversion, text="🔄 Convertir Archivo", bg="lightblue", font=("Arial", 10, "bold"), command=iniciar_conversion, state="disabled")
boton_convertir.pack(pady=20)

# --- Controles Generales (Inferiores) ---
frame_controles = tk.Frame(ventana)
frame_controles.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=20)

barra_progreso = ttk.Progressbar(frame_controles, orient="horizontal", length=400, mode="determinate")
barra_progreso.pack(side=tk.TOP, pady=5)

frame_estado = tk.Frame(frame_controles)
frame_estado.pack(side=tk.TOP, fill=tk.X)

etiqueta_estado = tk.Label(frame_estado, text="Estado: Esperando acción...", font=("Arial", 10, "italic"))
etiqueta_estado.pack(side=tk.LEFT)

boton_cancelar = tk.Button(frame_estado, text="❌ Cancelar", bg="salmon", font=("Arial", 9, "bold"), command=cancelar_proceso, state="disabled")
boton_cancelar.pack(side=tk.RIGHT)

ventana.mainloop()
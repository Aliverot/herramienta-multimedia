"""
Módulo de la ventana principal de la aplicación.
"""
import customtkinter as ctk
from typing import Callable, Optional


class App(ctk.CTk):
    """
    Ventana principal de Suite Multimedia Pro.
    """
    
    def __init__(self) -> None:
        """Inicializa la interfaz gráfica de la ventana principal."""
        super().__init__()
        
        # Configuración de la ventana
        self.title('Herramienta Multimedia')
        self.geometry('800x650')
        self.minsize(700, 550)
        
        # Tema y apariencia
        from src.ui.tab_settings import load_config
        saved_theme = load_config().get("theme", "system")
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme('blue')
        
        # Configuración del grid principal (1 columna, 3 filas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Cabecera
        self.grid_rowconfigure(1, weight=1) # Tabs
        self.grid_rowconfigure(2, weight=0) # Barra de estado
        
        self._create_header()
        self._create_tabs()
        self._create_status_bar()

    def _create_header(self) -> None:
        """Crea la cabecera superior con el título y subtítulo."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=(15, 10))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text='Herramienta Multimedia',
            font=('Segoe UI', 20, 'bold')
        )
        title_label.pack(anchor='center')
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text='Descarga, conversión y procesamiento de medios',
            font=('Segoe UI', 12),
            text_color='gray'
        )
        subtitle_label.pack(anchor='center')
        
    def _create_tabs(self) -> None:
        """Crea el control de pestañas y las vistas."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky='nsew', padx=20, pady=5)
        
        # Añadir pestañas
        self.tab_names = ['⬇️ Descargas', '🔄 Conversor', '📋 Cola', '⚙️ Ajustes']
        for name in self.tab_names:
            self.tabview.add(name)
            
        # Importaciones diferidas para evitar ciclos
        from src.ui.tab_download import TabDownload
        from src.ui.tab_convert import TabConvert
        from src.ui.tab_queue import TabQueue
        from src.ui.tab_settings import TabSettings
        
        # Inicializar contenido de las pestañas
        # Se pasa 'self' como parent para que las tabs puedan acceder a la app principal
        self.tab_download = TabDownload(self.tabview.tab('⬇️ Descargas'), app=self)
        self.tab_download.pack(fill="both", expand=True)
        
        self.tab_convert = TabConvert(self.tabview.tab('🔄 Conversor'), app=self)
        self.tab_convert.pack(fill="both", expand=True)
        
        self.tab_queue = TabQueue(self.tabview.tab('📋 Cola'), app=self)
        self.tab_queue.pack(fill="both", expand=True)
        
        self.tab_settings = TabSettings(self.tabview.tab('⚙️ Ajustes'), app=self)
        self.tab_settings.pack(fill="both", expand=True)
        
    def _create_status_bar(self) -> None:
        """Crea la barra de estado inferior."""
        status_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        status_frame.grid(row=2, column=0, sticky='ew', padx=0, pady=(10, 0))
        
        # Configurar grid de la barra de estado
        status_frame.grid_columnconfigure(0, weight=1) # Status label
        status_frame.grid_columnconfigure(1, weight=2) # Progress bar
        status_frame.grid_columnconfigure(2, weight=0) # Botón cancelar
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text='Estado: Listo',
            font=('Segoe UI', 12),
            text_color='gray'
        )
        self.status_label.grid(row=0, column=0, sticky='w', padx=20, pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(status_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=1, sticky='ew', padx=20, pady=10)
        self.progress_bar.set(0)
        
        self.cancel_button = ctk.CTkButton(
            status_frame,
            text='Cancelar',
            fg_color='#dc3545',
            hover_color='#c82333',
            font=('Segoe UI', 12, 'bold'),
            width=100,
            state='disabled'
        )
        self.cancel_button.grid(row=0, column=2, sticky='e', padx=20, pady=10)

    def update_status(self, text: str, color: str = 'gray') -> None:
        """
        Actualiza el texto y color de la etiqueta de estado.
        """
        self.status_label.configure(text=text, text_color=color)
        
    def update_progress(self, value: float) -> None:
        """
        Actualiza la barra de progreso.
        """
        self.progress_bar.set(value)
        
    def set_progress_mode(self, mode: str) -> None:
        """
        Establece el modo de la barra de progreso ('determinate' o 'indeterminate').
        """
        self.progress_bar.configure(mode=mode)
        
    def start_progress_indeterminate(self) -> None:
        """
        Inicia la animación de la barra de progreso indeterminada.
        """
        self.set_progress_mode('indeterminate')
        self.progress_bar.start()
        
    def stop_progress(self) -> None:
        """
        Detiene la animación y restablece la barra de progreso.
        """
        self.progress_bar.stop()
        self.set_progress_mode('determinate')
        self.progress_bar.set(0)
        
    def enable_cancel(self, command: Callable) -> None:
        """
        Habilita el botón de cancelar y asigna su comando.
        """
        self.cancel_button.configure(state='normal', command=command)
        
    def disable_cancel(self) -> None:
        """
        Deshabilita el botón de cancelar.
        """
        self.cancel_button.configure(state='disabled')
        
    def set_theme(self, mode: str) -> None:
        """
        Cambia el modo de apariencia.
        
        Args:
            mode: 'dark', 'light', o 'system'
        """
        ctk.set_appearance_mode(mode)
        
    def run(self) -> None:
        """
        Inicia el bucle principal de la aplicación.
        """
        self.mainloop()

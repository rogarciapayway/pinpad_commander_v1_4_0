#!/usr/bin/env python3
"""
Sistema de tooltips para mostrar descripciones de campos
"""

import tkinter as tk
import customtkinter as ctk

class ToolTip:
    """
    Tooltip simple que muestra texto al pasar el mouse sobre un widget
    """
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        # Bind eventos
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None):
        """Mostrar tooltip al entrar con el mouse"""
        if self.text:
            self.show_tooltip(event)
    
    def on_leave(self, event=None):
        """Ocultar tooltip al salir con el mouse"""
        self.hide_tooltip()
    
    def on_motion(self, event=None):
        """Actualizar posición del tooltip al mover el mouse"""
        if self.tooltip_window:
            self.update_position(event)
    
    def show_tooltip(self, event):
        """Crear y mostrar ventana de tooltip"""
        if self.tooltip_window:
            return
        
        # Crear ventana toplevel
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)
        
        # Configurar estilo
        self.tooltip_window.configure(bg="#2b2b2b", relief="solid", borderwidth=1)
        
        # Crear label con el texto
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9),
            padx=8,
            pady=4,
            wraplength=300,
            justify="left"
        )
        label.pack()
        
        # Posicionar tooltip
        self.update_position(event)
    
    def update_position(self, event):
        """Actualizar posición del tooltip"""
        if not self.tooltip_window:
            return
        
        # Obtener posición del cursor
        x = event.x_root + 10
        y = event.y_root + 10
        
        # Ajustar si se sale de la pantalla
        screen_width = self.tooltip_window.winfo_screenwidth()
        screen_height = self.tooltip_window.winfo_screenheight()
        
        tooltip_width = self.tooltip_window.winfo_reqwidth()
        tooltip_height = self.tooltip_window.winfo_reqheight()
        
        if x + tooltip_width > screen_width:
            x = event.x_root - tooltip_width - 10
        
        if y + tooltip_height > screen_height:
            y = event.y_root - tooltip_height - 10
        
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def hide_tooltip(self):
        """Ocultar y destruir tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
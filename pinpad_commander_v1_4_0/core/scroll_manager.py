#!/usr/bin/env python3
"""
Gestor de scroll unificado para PinPad Commander

Este módulo proporciona un sistema de scroll estandarizado que se aplica
consistentemente a todos los widgets de la aplicación.
"""

import tkinter as tk
from typing import Callable, Optional, Any
from .scroll_utils import (
    get_widget_scroll_info, create_scroll_function, is_at_scroll_limit,
    bind_scroll_events, unbind_scroll_events, get_scroll_diagnostics
)


class ScrollManager:
    """
    Gestor centralizado de scroll para toda la aplicación.
    
    Proporciona comportamiento de scroll consistente y configurable
    para todos los widgets que lo requieran.
    """
    
    def __init__(self, main_window):
        """
        Inicializar el gestor de scroll.
        
        Args:
            main_window: Ventana principal de la aplicación
        """
        self.main_window = main_window
        self.scroll_speed = 3  # Líneas por tick de scroll
        self.global_scroll_func = None
        self._bound_widgets = set()
        
    def set_global_scroll(self, scroll_func: Callable[[int], None]):
        """
        Establecer función de scroll global.
        
        Args:
            scroll_func: Función que maneja el scroll global
        """
        self.global_scroll_func = scroll_func
    
    def bind_widget(self, widget: Any, scroll_func: Optional[Callable[[int], None]] = None, 
                   enable_fallback: bool = True):
        """
        Vincular widget al sistema de scroll unificado.
        
        Args:
            widget: Widget a vincular
            scroll_func: Función personalizada de scroll (opcional)
            enable_fallback: Si usar fallback al scroll global
        """
        if widget in self._bound_widgets:
            return
            
        def combined_scroll_func(delta):
            # Usar función personalizada si está disponible
            if scroll_func:
                # Verificar si necesita fallback al scroll global
                if enable_fallback and self.global_scroll_func:
                    if self._should_fallback_to_global(widget, delta):
                        self.global_scroll_func(delta)
                        return
                
                scroll_func(delta)
            
            # Usar scroll global si está disponible
            elif self.global_scroll_func:
                self.global_scroll_func(delta)
        
        bind_scroll_events(widget, combined_scroll_func)
        self._bound_widgets.add(widget)
    
    def _should_fallback_to_global(self, widget: Any, delta: int) -> bool:
        """
        Determinar si debe usar fallback al scroll global.
        
        Args:
            widget: Widget a verificar
            delta: Delta del scroll
            
        Returns:
            True si debe usar fallback global
        """
        direction = "up" if delta > 0 else "down"
        return is_at_scroll_limit(widget, direction)
    
    def create_scroll_func(self, widget: Any, scroll_type: str = "auto") -> Callable[[int], None]:
        """
        Crear función de scroll apropiada para el widget.
        
        Args:
            widget: Widget para el cual crear la función
            scroll_type: Tipo de scroll ("auto", "textbox", "canvas", "scrollable_frame")
            
        Returns:
            Función de scroll configurada
        """
        return create_scroll_function(widget, self.scroll_speed)
    

    
    def bind_all_children(self, parent_widget: Any, scroll_func: Optional[Callable[[int], None]] = None):
        """
        Vincular recursivamente todos los widgets hijos.
        
        Args:
            parent_widget: Widget padre
            scroll_func: Función de scroll a aplicar
        """
        def bind_recursive(widget):
            try:
                self.bind_widget(widget, scroll_func)
                for child in widget.winfo_children():
                    bind_recursive(child)
            except Exception:
                pass
        
        bind_recursive(parent_widget)
    
    def setup_main_scroll(self):
        """Configurar scroll principal de la aplicación."""
        def global_scroll(delta):
            if hasattr(self.main_window, 'scrollable_frame'):
                try:
                    self.main_window.scrollable_frame._parent_canvas.yview_scroll(
                        int(-self.scroll_speed * (delta / 120)), "units"
                    )
                except Exception:
                    pass
        
        self.set_global_scroll(global_scroll)
        self.bind_widget(self.main_window, global_scroll, enable_fallback=False)
    
    def setup_communication_panel_scroll(self):
        """Configurar scroll para paneles de comunicación."""
        try:
            comm_panel = self.main_window.communication_panel
            
            # HEX Text
            if hasattr(comm_panel, 'hex_text'):
                hex_scroll = self.create_scroll_func(comm_panel.hex_text, "textbox")
                self.bind_widget(comm_panel.hex_text, hex_scroll)
            
            # Parsed Text (tkinter Text)
            if hasattr(comm_panel, 'parsed_text'):
                parsed_scroll = self.create_scroll_func(comm_panel.parsed_text, "text")
                self.bind_widget(comm_panel.parsed_text, parsed_scroll)
            
            # Command JSON Text
            if hasattr(comm_panel, 'cmd_json_text'):
                cmd_json_scroll = self.create_scroll_func(comm_panel.cmd_json_text, "text")
                self.bind_widget(comm_panel.cmd_json_text, cmd_json_scroll)
            
            # App Log Text
            if hasattr(comm_panel, 'app_log_text'):
                app_log_scroll = self.create_scroll_func(comm_panel.app_log_text, "textbox")
                self.bind_widget(comm_panel.app_log_text, app_log_scroll)
                
        except Exception as e:
            print(f"Error configurando scroll de paneles de comunicación: {e}")
    
    def add_widget_to_scroll(self, widget: Any, scroll_func: Optional[Callable[[int], None]] = None):
        """Método público para agregar widgets al sistema de scroll."""
        if scroll_func is None:
            scroll_func = self.create_scroll_func(widget)
        
        if scroll_func:
            self.bind_widget(widget, scroll_func)
            return True
        return False
    
    def setup_params_scroll(self):
        """Configurar scroll para panel de parámetros."""
        try:
            params_frame = self.main_window.command_panel.params_frame
            params_scroll = self.create_scroll_func(params_frame, "scrollable_frame")
            self.bind_widget(params_frame, params_scroll)
            
            # Vincular widgets hijos cuando se crean
            def bind_params_children():
                self.bind_all_children(params_frame, params_scroll)
            
            self.main_window.after(100, bind_params_children)
            
        except Exception as e:
            print(f"Error configurando scroll de parámetros: {e}")
    
    def refresh_all_bindings(self):
        """Refrescar todos los bindings de scroll."""
        widgets_to_rebind = list(self._bound_widgets)
        self._bound_widgets.clear()
        
        for widget in widgets_to_rebind:
            try:
                unbind_scroll_events(widget)
                scroll_func = self.create_scroll_func(widget)
                if scroll_func:
                    self.bind_widget(widget, scroll_func)
            except Exception as e:
                print(f"Error refrescando binding para {widget}: {e}")
    
    def setup_all_scrolls(self):
        """Configurar todos los scrolls de la aplicación."""
        try:
            self.setup_main_scroll()
            self.setup_communication_panel_scroll()
            self.setup_params_scroll()
            
            # Log de configuración
            print(f"✅ ScrollManager configurado - {len(self._bound_widgets)} widgets vinculados")
        except Exception as e:
            print(f"❌ Error configurando ScrollManager: {e}")
    
    def set_scroll_speed(self, speed: int):
        """
        Cambiar velocidad de scroll.
        
        Args:
            speed: Nueva velocidad (líneas por tick)
        """
        old_speed = self.scroll_speed
        self.scroll_speed = max(1, min(10, speed))
        
        if old_speed != self.scroll_speed:
            # Refrescar bindings con nueva velocidad
            self.refresh_all_bindings()
            print(f"🔄 Velocidad de scroll cambiada de {old_speed} a {self.scroll_speed}")
    
    def unbind_widget(self, widget: Any):
        """
        Desvincular widget del sistema de scroll.
        
        Args:
            widget: Widget a desvincular
        """
        unbind_scroll_events(widget)
        self._bound_widgets.discard(widget)
    
    def get_bound_widgets_count(self) -> int:
        """
        Obtener número de widgets vinculados.
        
        Returns:
            Número de widgets vinculados al sistema de scroll
        """
        return len(self._bound_widgets)
    
    def refresh_params_scroll(self):
        """Refrescar scroll del panel de parámetros después de crear widgets dinámicos."""
        try:
            params_frame = self.main_window.command_panel.params_frame
            
            def params_scroll_func(delta):
                try:
                    params_frame._parent_canvas.yview_scroll(
                        int(-self.scroll_speed * (delta / 120)), "units"
                    )
                except Exception:
                    pass
            
            def bind_all_params_widgets(parent):
                try:
                    self.bind_widget(parent, params_scroll_func, enable_fallback=False)
                    for child in parent.winfo_children():
                        bind_all_params_widgets(child)
                except Exception:
                    pass
            
            bind_all_params_widgets(params_frame)
            
        except Exception as e:
            print(f"Error refrescando scroll de parámetros: {e}")
    
    def get_diagnostics(self) -> str:
        """
        Obtener información de diagnóstico del sistema de scroll.
        
        Returns:
            String con información de diagnóstico
        """
        diagnostics = [
            f"ScrollManager - Widgets vinculados: {len(self._bound_widgets)}",
            f"Velocidad de scroll: {self.scroll_speed}",
            f"Scroll global configurado: {self.global_scroll_func is not None}",
            "",
            "Widgets vinculados:"
        ]
        
        for i, widget in enumerate(self._bound_widgets, 1):
            try:
                widget_info = get_scroll_diagnostics(widget)
                diagnostics.append(f"{i}. {widget_info}")
                diagnostics.append("")
            except Exception as e:
                diagnostics.append(f"{i}. Error obteniendo info: {e}")
                diagnostics.append("")
        
        return "\n".join(diagnostics)
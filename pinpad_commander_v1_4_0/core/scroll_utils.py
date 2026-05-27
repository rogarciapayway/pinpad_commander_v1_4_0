#!/usr/bin/env python3
"""
Utilidades para el sistema de scroll unificado

Funciones de ayuda para configurar y gestionar el scroll
en diferentes tipos de widgets.
"""

from typing import Any, Callable, Optional


def get_widget_scroll_info(widget: Any) -> dict:
    """
    Obtener información sobre las capacidades de scroll de un widget.
    
    Args:
        widget: Widget a analizar
        
    Returns:
        Diccionario con información de scroll
    """
    info = {
        "type": "unknown",
        "can_scroll": False,
        "has_yview": False,
        "has_canvas": False,
        "is_textbox": False,
        "scroll_method": None
    }
    
    try:
        # CTkTextbox
        if hasattr(widget, '_textbox'):
            info.update({
                "type": "ctk_textbox",
                "can_scroll": True,
                "has_yview": True,
                "is_textbox": True,
                "scroll_method": "textbox"
            })
        
        # CTkScrollableFrame
        elif hasattr(widget, '_parent_canvas'):
            info.update({
                "type": "ctk_scrollable_frame",
                "can_scroll": True,
                "has_canvas": True,
                "scroll_method": "canvas"
            })
        
        # tkinter Text, Listbox, etc.
        elif hasattr(widget, 'yview') and hasattr(widget, 'insert'):
            info.update({
                "type": "tk_text",
                "can_scroll": True,
                "has_yview": True,
                "scroll_method": "text"
            })
        
        # Canvas u otros widgets con yview
        elif hasattr(widget, 'yview'):
            info.update({
                "type": "tk_scrollable",
                "can_scroll": True,
                "has_yview": True,
                "scroll_method": "canvas"
            })
        
        # Widget sin scroll
        else:
            info.update({
                "type": "non_scrollable",
                "can_scroll": False,
                "scroll_method": "none"
            })
            
    except Exception:
        pass
    
    return info


def create_scroll_function(widget: Any, scroll_speed: int = 3) -> Optional[Callable[[int], None]]:
    """
    Crear función de scroll apropiada para un widget específico.
    
    Args:
        widget: Widget para el cual crear la función
        scroll_speed: Velocidad de scroll en líneas por tick
        
    Returns:
        Función de scroll o None si no es aplicable
    """
    info = get_widget_scroll_info(widget)
    
    if not info["can_scroll"]:
        return None
    
    scroll_method = info["scroll_method"]
    
    if scroll_method == "textbox":
        return lambda delta: widget._textbox.yview_scroll(
            int(-scroll_speed * (delta / 120)), "units"
        )
    
    elif scroll_method == "text":
        return lambda delta: widget.yview_scroll(
            int(-scroll_speed * (delta / 120)), "units"
        )
    
    elif scroll_method == "canvas":
        if hasattr(widget, '_parent_canvas'):
            return lambda delta: widget._parent_canvas.yview_scroll(
                int(-scroll_speed * (delta / 120)), "units"
            )
        else:
            return lambda delta: widget.yview_scroll(
                int(-scroll_speed * (delta / 120)), "units"
            )
    
    return None


def is_at_scroll_limit(widget: Any, direction: str) -> bool:
    """
    Verificar si un widget está en el límite de scroll.
    
    Args:
        widget: Widget a verificar
        direction: "up" o "down"
        
    Returns:
        True si está en el límite especificado
    """
    try:
        info = get_widget_scroll_info(widget)
        
        if not info["can_scroll"]:
            return True
        
        # Obtener posición de scroll
        if info["scroll_method"] == "textbox":
            top, bottom = widget._textbox.yview()
        elif info["scroll_method"] == "canvas" and hasattr(widget, '_parent_canvas'):
            top, bottom = widget._parent_canvas.yview()
        elif info["has_yview"]:
            top, bottom = widget.yview()
        else:
            return True
        
        # Verificar límites
        if direction == "up":
            return top <= 0
        elif direction == "down":
            return bottom >= 1
        
    except Exception:
        pass
    
    return True


def bind_scroll_events(widget: Any, scroll_func: Callable[[int], None]):
    """
    Vincular eventos de scroll a un widget.
    
    Args:
        widget: Widget a vincular
        scroll_func: Función de scroll a ejecutar
    """
    def on_mousewheel(event):
        scroll_func(event.delta)
        return "break"
    
    def on_button4(event):
        scroll_func(120)
        return "break"
    
    def on_button5(event):
        scroll_func(-120)
        return "break"
    
    try:
        widget.bind("<MouseWheel>", on_mousewheel)
        widget.bind("<Button-4>", on_button4)
        widget.bind("<Button-5>", on_button5)
    except Exception:
        pass


def unbind_scroll_events(widget: Any):
    """
    Desvincular eventos de scroll de un widget.
    
    Args:
        widget: Widget a desvincular
    """
    try:
        widget.unbind("<MouseWheel>")
        widget.unbind("<Button-4>")
        widget.unbind("<Button-5>")
    except Exception:
        pass


def configure_scroll_propagation(parent_widget: Any, child_widgets: list, 
                               scroll_manager: Any):
    """
    Configurar propagación de scroll entre widgets padre e hijos.
    
    Args:
        parent_widget: Widget padre
        child_widgets: Lista de widgets hijos
        scroll_manager: Instancia del ScrollManager
    """
    try:
        # Crear función de scroll para el padre
        parent_scroll = scroll_manager.create_scroll_func(parent_widget)
        
        if parent_scroll:
            # Vincular padre
            scroll_manager.bind_widget(parent_widget, parent_scroll)
            
            # Vincular hijos con fallback al padre
            for child in child_widgets:
                child_scroll = scroll_manager.create_scroll_func(child)
                if child_scroll:
                    def combined_scroll(delta, child_func=child_scroll, parent_func=parent_scroll):
                        # Intentar scroll del hijo primero
                        info = get_widget_scroll_info(child)
                        if info["can_scroll"]:
                            direction = "up" if delta > 0 else "down"
                            if is_at_scroll_limit(child, direction):
                                parent_func(delta)
                            else:
                                child_func(delta)
                        else:
                            parent_func(delta)
                    
                    scroll_manager.bind_widget(child, combined_scroll, enable_fallback=False)
                else:
                    # Si el hijo no puede hacer scroll, usar el del padre
                    scroll_manager.bind_widget(child, parent_scroll, enable_fallback=False)
                    
    except Exception as e:
        print(f"Error configurando propagación de scroll: {e}")


def get_scroll_diagnostics(widget: Any) -> str:
    """
    Obtener información de diagnóstico sobre el scroll de un widget.
    
    Args:
        widget: Widget a diagnosticar
        
    Returns:
        String con información de diagnóstico
    """
    info = get_widget_scroll_info(widget)
    
    diagnostics = [
        f"Widget: {widget.__class__.__name__}",
        f"Tipo: {info['type']}",
        f"Puede hacer scroll: {info['can_scroll']}",
        f"Método de scroll: {info['scroll_method']}"
    ]
    
    if info["can_scroll"]:
        try:
            if info["scroll_method"] == "textbox":
                top, bottom = widget._textbox.yview()
            elif info["scroll_method"] == "canvas" and hasattr(widget, '_parent_canvas'):
                top, bottom = widget._parent_canvas.yview()
            elif info["has_yview"]:
                top, bottom = widget.yview()
            else:
                top, bottom = 0, 1
            
            diagnostics.extend([
                f"Posición superior: {top:.3f}",
                f"Posición inferior: {bottom:.3f}",
                f"En límite superior: {top <= 0}",
                f"En límite inferior: {bottom >= 1}"
            ])
        except Exception as e:
            diagnostics.append(f"Error obteniendo posición: {e}")
    
    return "\n".join(diagnostics)
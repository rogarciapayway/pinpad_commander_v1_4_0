#!/usr/bin/env python3
"""
PinPad Commander - Aplicación modular refactorizada

Esta aplicación permite comunicarse con dispositivos PinPad mediante comandos seriales.
Soporta múltiples comandos (Y02, Y03, Y06, Y0I, Y19) con parsing automático de respuestas,
manejo de RSA, y logging detallado.
"""

import sys
import os
import tkinter as tk
import logging

# Agregar directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==================== CONFIGURACIÓN DE SEGURIDAD ====================
try:
    from security_config import setup_security
    setup_security()
except ImportError:
    logging.basicConfig(level=logging.INFO)

# ==================== IMPORTS DE MÓDULOS ====================
from ui.main_window import MainWindow
from core.communication import SerialCommunication
from crypto.rsa_handler import RSAHandler
from core.data_processor import DataProcessor
from core.response_parser import ResponseParser
from core.command_handler import CommandHandler
from core.logger import AppLogger

# Gestores especializados
from core.event_manager import EventManager
from core.config_manager import ConfigManager
from core.serial_manager import SerialManager
from core.rsa_manager import RSAManager
from core.ui_manager import UIManager
from core.emv_manager import EMVManager
from core.scroll_manager import ScrollManager

# Patches de compatibilidad
from y19_autopem_patch import attach_y19_autopem_support
from ui_logpanel_patch import attach_log_panel

# Bridge ISO
from core.bridge_manager import BridgeManager


class PinPadCommanderModular:
    """
    Clase principal de la aplicación PinPad Commander.
    
    Coordina todos los componentes mediante gestores especializados:
    - UI: Interfaz gráfica con CustomTkinter
    - Comunicación: Manejo de puerto serial
    - RSA: Criptografía y manejo de claves
    - Parser: Análisis de respuestas del dispositivo
    - Logger: Registro de actividad
    """
    
    def __init__(self):
        """Inicializar la aplicación y todos sus componentes"""
        # ==================== LOGGING ====================
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing PinPad Commander Modular")
        
        # ==================== COMPONENTES PRINCIPALES ====================
        self.window = MainWindow()
        
        # Módulos core
        self.comm = SerialCommunication()
        self.rsa = RSAHandler()
        self.processor = DataProcessor()
        self.parser = ResponseParser(self.comm, self.processor, self)
        self.command_handler = CommandHandler(self)
        self.app_logger = AppLogger(self.window)
        
        # Gestores especializados
        self.event_manager = EventManager(self)
        self.config_manager = ConfigManager(self)
        self.serial_manager = SerialManager(self)
        self.rsa_manager = RSAManager(self)
        self.ui_manager = UIManager(self)
        self.emv_manager = EMVManager(self)
        self.scroll_manager = self.window.scroll_manager
        self.bridge_manager = BridgeManager(self)  # Usar el scroll manager de la ventana
        
        # ==================== VARIABLES DE ESTADO ====================
        self.cfg = {}
        self.current_cmd_id = ""
        self.params_widgets = {}
        self._last_sent = {}
        self._last_y19_result = None
        self.rsa_padding = tk.StringVar(value="RAW-NoPadding")
        
        # ==================== INICIALIZACIÓN ====================
        self.emv_manager.load_emv_tags()
        self.config_manager.load_initial_config()
        self.event_manager.connect_all_events()
        self._apply_patches()
        
        # Refrescar puertos al inicio
        self.window.after(100, self._refresh_ports)
        
        # Configurar callback para refrescar scroll cuando se rendericen parámetros
        original_render = self._render_param_fields
        def enhanced_render():
            original_render()
            self.window.after(100, self.scroll_manager.refresh_params_scroll)
        self._render_param_fields = enhanced_render

    # ==================== MÉTODOS DELEGADOS ====================
    
    def _toggle_port(self):
        """Delegar a SerialManager"""
        self.serial_manager.toggle_port()
    
    def _refresh_ports(self):
        """Delegar a SerialManager"""
        self.serial_manager.refresh_ports()
    
    def _load_rsa_key(self):
        """Delegar a RSAManager"""
        self.rsa_manager.load_rsa_key()
    
    def _load_public_key(self):
        """Delegar a RSAManager"""
        self.rsa_manager.load_public_key()
    
    def _choose_config(self):
        """Delegar a UIManager"""
        self.ui_manager.choose_config()
    
    def _render_param_fields(self):
        """Delegar a UIManager"""
        self.ui_manager.render_param_fields()
    
    def _apply_y02_suggested(self):
        """Delegar a UIManager"""
        self.ui_manager.apply_y02_suggested()
    
    def _enable_y02_suggestion(self, parsed):
        """Delegar a UIManager"""
        self.ui_manager.enable_y02_suggestion(parsed)
    
    def _on_padding_change(self, value):
        """Delegar a UIManager"""
        self.ui_manager.on_padding_change(value)
    
    def _on_cmd_selected(self, value=None):
        """Delegar a UIManager"""
        self.ui_manager.on_cmd_selected(value)
    
    # ==================== MÉTODOS EMV ====================
    
    def _bcd_digits(self, hex_str: str) -> str:
        """Delegar a EMVManager"""
        return self.emv_manager.bcd_digits(hex_str)
    
    def _amount_from_bcd_hex(self, hex_str: str, exp: int = 2):
        """Delegar a EMVManager"""
        return self.emv_manager.amount_from_bcd_hex(hex_str, exp)
    
    def _emv_pretty(self, tlv: dict):
        """Delegar a EMVManager"""
        return self.emv_manager.emv_pretty(tlv)

    # ==================== COMPATIBILIDAD LEGACY ====================
    
    def _apply_patches(self):
        """Aplicar patches de compatibilidad para módulos legacy"""
        # Exponer variables de estado a través de la ventana
        self.window.params_widgets = self.params_widgets
        self.window.cfg = self.cfg
        self.window._render_param_fields = self._render_param_fields
        
        # Mapear componentes de UI para compatibilidad
        self.window.params_frame = self.window.command_panel.params_frame
        self.window.main_notebook = self.window.communication_panel
        self.window.log_frame_tab = self.window.communication_panel.log_frame_tab
        self.window.hex_text = self.window.communication_panel.hex_text
        self.window.parsed_text = self.window.communication_panel.parsed_text
        self.window.raw_hex_entry = self.window.communication_panel.raw_hex_entry
        
        # Crear proxy para current_cmd_id
        self.window.current_cmd_id = tk.StringVar()
        self.window.current_cmd_id.set = lambda x: setattr(self, 'current_cmd_id', x)
        self.window.current_cmd_id.get = lambda: getattr(self, 'current_cmd_id', '')
        
        # Exponer componentes necesarios
        self.window.y02_btn = self.window.command_panel.y02_btn
        self.window._last_sent = self._last_sent
        self.window.mask_pan = self.window.connection_panel.mask_pan_var
        self.window.rsa_padding = self.rsa_padding
        
        # Aplicar patches externos
        attach_y19_autopem_support(type(self.window))
        attach_log_panel(type(self.window))
        
        # Atajos de teclado
        self.window.bind_all("<Control-h>", lambda e: self.compact_history())
        self.window.bind_all("<Control-Shift-H>", lambda e: self.clear_history())
        
        # Configurar velocidad de scroll personalizada si es necesario
        # self.scroll_manager.set_scroll_speed(5)  # Opcional: cambiar velocidad

    # ==================== MÉTODOS DE HISTORIAL ====================
    
    def compact_history(self):
        """Método público para compactar historial"""
        self.app_logger.compact_history()
        self.window.status.set("🗂️ Historial compactado")
    
    def clear_history(self):
        """Método público para limpiar historial"""
        self.app_logger.clear_history()
        self.window.status.set("🧹 Historial limpiado")

    # ==================== DELEGACIÓN DE LOGGING ====================
    
    def _log_hex(self, direction, data):
        """Delegar logging hexadecimal al AppLogger"""
        try:
            self.app_logger.log_hex(direction, data)
        except Exception as e:
            print(f"Error logging hex: {e}")
    
    def _log_text(self, text):
        """Delegar logging de texto al AppLogger"""
        try:
            self.app_logger.log_text(text)
        except Exception as e:
            print(f"Error logging text: {e}")
    
    def _log_parsed(self, obj):
        """Delegar logging de objetos parseados al AppLogger"""
        try:
            self.app_logger.log_parsed(obj)
        except Exception as e:
            print(f"Error logging parsed: {e}")
            print(f"Object: {obj}")

    # ==================== EJECUCIÓN DE LA APLICACIÓN ====================
    
    def run(self):
        """Ejecutar el bucle principal de la aplicación"""
        self.window.mainloop()


# ==================== PUNTO DE ENTRADA ====================

def main():
    """Función principal de la aplicación"""
    app = PinPadCommanderModular()
    app.run()


if __name__ == "__main__":
    main()
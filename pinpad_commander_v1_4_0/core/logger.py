#!/usr/bin/env python3
"""
Logger para la aplicación PinPad Commander
"""

import json
import logging
from datetime import datetime


class UILogHandler(logging.Handler):
    """Handler personalizado para mostrar logs en la UI"""
    def __init__(self, app_logger):
        super().__init__()
        self.app_logger = app_logger
        self.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.app_logger.log_app(msg, record.levelname)
        except Exception:
            pass


class AppLogger:
    def __init__(self, window):
        self.window = window
        self.max_lines = 1000  # Límite de líneas antes de compactar
        self._setup_logging_handler()
        
        # Configurar scroll para widgets de log cuando estén disponibles
        self.window.after(200, self._setup_log_scrolls)
    
    def _setup_log_scrolls(self):
        """Configurar scroll para widgets de log específicos"""
        try:
            if hasattr(self.window, 'scroll_manager'):
                scroll_manager = self.window.scroll_manager
                
                # Configurar scroll para widgets de log que puedan no estar en setup inicial
                if hasattr(self.window, 'communication_panel'):
                    comm_panel = self.window.communication_panel
                    
                    # Re-configurar scrolls para asegurar consistencia
                    if hasattr(comm_panel, 'hex_text'):
                        scroll_manager.bind_widget(comm_panel.hex_text, 
                                                  scroll_manager.create_scroll_func(comm_panel.hex_text))
                    
                    if hasattr(comm_panel, 'parsed_text'):
                        scroll_manager.bind_widget(comm_panel.parsed_text, 
                                                  scroll_manager.create_scroll_func(comm_panel.parsed_text))
                    
                    if hasattr(comm_panel, 'cmd_json_text'):
                        scroll_manager.bind_widget(comm_panel.cmd_json_text, 
                                                  scroll_manager.create_scroll_func(comm_panel.cmd_json_text))
                    
                    if hasattr(comm_panel, 'app_log_text'):
                        scroll_manager.bind_widget(comm_panel.app_log_text, 
                                                  scroll_manager.create_scroll_func(comm_panel.app_log_text))
        except Exception as e:
            print(f"Error configurando scrolls de log: {e}")
    
    def _setup_logging_handler(self):
        """Configurar handler para capturar logs de la aplicación"""
        try:
            # Crear handler personalizado
            ui_handler = UILogHandler(self)
            ui_handler.setLevel(logging.INFO)
            
            # Agregar al logger raíz
            root_logger = logging.getLogger()
            root_logger.addHandler(ui_handler)
            
            # También agregar a loggers específicos
            for logger_name in ['PinPadCommanderModular', 'CommandHandler', 'SerialCommunication', 'RSAHandler']:
                logger = logging.getLogger(logger_name)
                logger.addHandler(ui_handler)
                
        except Exception as e:
            print(f"Error configurando logging handler: {e}")
    
    def log_hex(self, direction, data):
        """Log de datos en hexadecimal"""
        try:
            show_ts = self.window.connection_panel.timestamps_var.get()
        except:
            show_ts = True
            
        ts = datetime.now().strftime("%H:%M:%S") if show_ts else ""
        
        # Iconos para diferentes tipos de mensajes
        if direction == "TX":
            icon = "→"
        elif direction == "RX":
            icon = "←"
        else:
            icon = "ℹ️"
        
        # Formatear mensaje
        hex_str = " ".join(f"{b:02X}" for b in data)
        if ts:
            msg = f"[{ts}] {icon} {direction}: {hex_str}\n"
        else:
            msg = f"{icon} {direction}: {hex_str}\n"
            
        try:
            hex_widget = self.window.communication_panel.hex_text
            if hasattr(hex_widget, '_textbox'):
                # CTkTextbox
                hex_widget._textbox.insert("end", msg)
                hex_widget._textbox.see("end")
            else:
                # tkinter Text
                hex_widget.insert("end", msg)
                hex_widget.see("end")
            
            self.window.communication_panel.raw_hex_entry.delete(0, "end")
            self.window.communication_panel.raw_hex_entry.insert(0, "".join(f"{b:02X}" for b in data))
            self._compact_if_needed(hex_widget)
        except AttributeError as e:
            print(f"LOG HEX ERROR: {e}")
            print(f"LOG: {msg.strip()}")
    
    def log_text(self, text):
        """Log de texto"""
        try:
            show_ts = self.window.connection_panel.timestamps_var.get()
        except:
            show_ts = True
            
        ts = datetime.now().strftime("%H:%M:%S") if show_ts else ""
        
        # Formatear mensaje de texto
        if ts:
            msg = f"[{ts}] 💬 {text}"
        else:
            msg = f"💬 {text}"
            
        try:
            hex_widget = self.window.communication_panel.hex_text
            if hasattr(hex_widget, '_textbox'):
                # CTkTextbox
                hex_widget._textbox.insert("end", msg)
                hex_widget._textbox.see("end")
            else:
                # tkinter Text
                hex_widget.insert("end", msg)
                hex_widget.see("end")
            
            self._compact_if_needed(hex_widget)
        except AttributeError as e:
            print(f"LOG TEXT ERROR: {e}")
            print(f"LOG: {msg.strip()}")
    
    def log_parsed(self, obj):
        """Log de objeto parseado con colores JSON"""
        # Formatear JSON con mejor presentación
        formatted_json = json.dumps(obj, ensure_ascii=False, indent=2)
        
        # Agregar separador visual
        separator = "\n" + "="*50 + "\n"
        
        try:
            show_ts = self.window.connection_panel.timestamps_var.get()
        except:
            show_ts = True
            
        timestamp = datetime.now().strftime("%H:%M:%S") if show_ts else ""
        
        if timestamp:
            header = f"[{timestamp}] 🔍 RESPUESTA PARSEADA:\n"
        else:
            header = "🔍 RESPUESTA PARSEADA:\n"
            
        try:
            text_widget = self.window.communication_panel.parsed_text
            
            # Configurar tags de colores si no existen
            self._setup_json_colors(text_widget)
            
            # Insertar header y separador
            text_widget.insert("end", separator + header)
            
            # Insertar JSON con colores
            self._insert_colored_json(text_widget, formatted_json)
            text_widget.insert("end", "\n")
            
            text_widget.see("end")
            self._compact_if_needed(text_widget)
        except AttributeError as e:
            print(f"LOG PARSED ERROR: {e}")
            print(f"PARSED: {formatted_json}")
    
    def _setup_json_colors(self, text_widget):
        """Configurar tags de colores para JSON"""
        try:
            # Colores para tema oscuro
            text_widget.tag_configure("json_key", foreground="#9CDCFE")      # Azul claro para claves
            text_widget.tag_configure("json_string", foreground="#CE9178")   # Naranja para strings
            text_widget.tag_configure("json_number", foreground="#B5CEA8")   # Verde para números
            text_widget.tag_configure("json_bool", foreground="#569CD6")     # Azul para booleanos
            text_widget.tag_configure("json_null", foreground="#569CD6")     # Azul para null
            text_widget.tag_configure("json_punct", foreground="#D4D4D4")    # Gris claro para puntuación
        except Exception as e:
            print(f"Error configurando colores JSON: {e}")
    
    def _insert_colored_json(self, text_widget, json_str):
        """Insertar JSON con colores de sintaxis"""
        import re
        
        try:
            # Obtener posición inicial
            start_line = int(text_widget.index("end-1c").split('.')[0])
            text_widget.insert("end", json_str)
            
            # Aplicar colores línea por línea
            lines = json_str.split('\n')
            for line_offset, line in enumerate(lines):
                current_line = start_line + line_offset
                
                # Claves JSON
                for match in re.finditer(r'"([^"\\]|\\.)*"\s*:', line):
                    start_idx = f"{current_line}.{match.start()}"
                    end_idx = f"{current_line}.{match.end()-1}"
                    text_widget.tag_add('json_key', start_idx, end_idx)
                
                # Strings (que no sean claves)
                for match in re.finditer(r'"([^"\\]|\\.)*"', line):
                    if not re.match(r'"([^"\\]|\\.)*"\s*:', line[match.start():]):
                        start_idx = f"{current_line}.{match.start()}"
                        end_idx = f"{current_line}.{match.end()}"
                        text_widget.tag_add('json_string', start_idx, end_idx)
                
                # Números
                for match in re.finditer(r'\b\d+\.?\d*\b', line):
                    start_idx = f"{current_line}.{match.start()}"
                    end_idx = f"{current_line}.{match.end()}"
                    text_widget.tag_add('json_number', start_idx, end_idx)
                
                # Booleanos
                for match in re.finditer(r'\b(true|false)\b', line):
                    start_idx = f"{current_line}.{match.start()}"
                    end_idx = f"{current_line}.{match.end()}"
                    text_widget.tag_add('json_bool', start_idx, end_idx)
                
                # Null
                for match in re.finditer(r'\bnull\b', line):
                    start_idx = f"{current_line}.{match.start()}"
                    end_idx = f"{current_line}.{match.end()}"
                    text_widget.tag_add('json_null', start_idx, end_idx)
                    
        except Exception as e:
            print(f"Error coloreando JSON: {e}")
            # Si falla el coloreado, el texto ya está insertado
    
    def _compact_if_needed(self, text_widget):
        """Compactar historial si excede el límite de líneas"""
        try:
            # Determinar si es CTkTextbox o tkinter Text
            if hasattr(text_widget, '_textbox'):
                # CTkTextbox
                lines = int(text_widget._textbox.index('end-1c').split('.')[0])
                if lines > self.max_lines:
                    keep_lines = 500
                    start_line = lines - keep_lines + 1
                    text_widget._textbox.delete('1.0', f'{start_line}.0')
                    text_widget._textbox.insert('1.0', f"[{datetime.now().strftime('%H:%M:%S')}] 🗂️ Historial compactado - mostrando últimas {keep_lines} líneas\n")
            else:
                # tkinter Text
                lines = int(text_widget.index('end-1c').split('.')[0])
                if lines > self.max_lines:
                    keep_lines = 500
                    start_line = lines - keep_lines + 1
                    text_widget.delete('1.0', f'{start_line}.0')
                    text_widget.insert('1.0', f"[{datetime.now().strftime('%H:%M:%S')}] 🗂️ Historial compactado - mostrando últimas {keep_lines} líneas\n")
        except Exception as e:
            print(f"Error compactando historial: {e}")
    
    def compact_history(self):
        """Compactar manualmente todo el historial"""
        try:
            # Compactar panel hex
            hex_widget = self.window.communication_panel.hex_text
            self._compact_widget_manually(hex_widget, "HEX")
            
            # Compactar panel parsed
            parsed_widget = self.window.communication_panel.parsed_text
            self._compact_widget_manually(parsed_widget, "parseado")
            
            # Compactar panel comandos JSON
            try:
                cmd_json_widget = self.window.communication_panel.cmd_json_text
                self._compact_widget_manually(cmd_json_widget, "comandos JSON")
            except AttributeError:
                pass  # La pestaña de comandos JSON no existe aún
                
        except Exception as e:
            print(f"Error en compactación manual: {e}")
    
    def _compact_widget_manually(self, widget, widget_name):
        """Compactar un widget específico manualmente"""
        try:
            if hasattr(widget, '_textbox'):
                # CTkTextbox
                lines = int(widget._textbox.index('end-1c').split('.')[0])
                if lines > 100:
                    keep_lines = 50
                    start_line = lines - keep_lines + 1
                    widget._textbox.delete('1.0', f'{start_line}.0')
                    widget._textbox.insert('1.0', f"[{datetime.now().strftime('%H:%M:%S')}] 🗂️ Historial {widget_name} compactado\n")
            else:
                # tkinter Text
                lines = int(widget.index('end-1c').split('.')[0])
                if lines > 100:
                    keep_lines = 50
                    start_line = lines - keep_lines + 1
                    widget.delete('1.0', f'{start_line}.0')
                    widget.insert('1.0', f"[{datetime.now().strftime('%H:%M:%S')}] 🗂️ Historial {widget_name} compactado\n")
        except Exception as e:
            print(f"Error compactando {widget_name}: {e}")
    
    def compact_app_log(self):
        """Compactar manualmente el log de aplicación"""
        try:
            app_log_widget = self.window.communication_panel.app_log_text
            self._compact_widget_manually(app_log_widget, "aplicación")
        except Exception as e:
            print(f"Error compactando log de aplicación: {e}")
    
    def clear_history(self):
        """Limpiar completamente el historial"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Limpiar panel hex
            hex_widget = self.window.communication_panel.hex_text
            self._clear_widget(hex_widget, f"[{timestamp}] 🧹 Historial limpiado\n")
            
            # Limpiar panel parsed
            parsed_widget = self.window.communication_panel.parsed_text
            self._clear_widget(parsed_widget, f"[{timestamp}] 🧹 Historial limpiado\n")
            
            # Limpiar panel comandos JSON
            try:
                cmd_json_widget = self.window.communication_panel.cmd_json_text
                self._clear_widget(cmd_json_widget, f"[{timestamp}] 🧹 Historial comandos JSON limpiado\n")
            except AttributeError:
                pass  # La pestaña de comandos JSON no existe aún
        except Exception as e:
            print(f"Error limpiando historial: {e}")
    
    def _clear_widget(self, widget, message):
        """Limpiar un widget específico"""
        try:
            if hasattr(widget, '_textbox'):
                # CTkTextbox
                widget._textbox.delete('1.0', 'end')
                widget._textbox.insert('1.0', message)
            else:
                # tkinter Text
                widget.delete('1.0', 'end')
                widget.insert('1.0', message)
        except Exception as e:
            print(f"Error limpiando widget: {e}")
    
    def clear_app_log(self):
        """Limpiar completamente el log de aplicación"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            app_log_widget = self.window.communication_panel.app_log_text
            self._clear_widget(app_log_widget, f"[{timestamp}] 🧹 Log de aplicación limpiado\n")
        except Exception as e:
            print(f"Error limpiando log de aplicación: {e}")
    
    def compact_cmd_json(self):
        """Compactar manualmente el log de comandos JSON"""
        try:
            cmd_json_widget = self.window.communication_panel.cmd_json_text
            self._compact_widget_manually(cmd_json_widget, "comandos JSON")
        except Exception as e:
            print(f"Error compactando log de comandos JSON: {e}")
    
    def clear_cmd_json(self):
        """Limpiar completamente el log de comandos JSON"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            cmd_json_widget = self.window.communication_panel.cmd_json_text
            self._clear_widget(cmd_json_widget, f"[{timestamp}] 🧹 Log de comandos JSON limpiado\n")
        except Exception as e:
            print(f"Error limpiando log de comandos JSON: {e}")
    
    def log_app(self, message, level="INFO"):
        """Log de mensajes de la aplicación"""
        try:
            show_ts = self.window.connection_panel.timestamps_var.get()
        except:
            show_ts = True
            
        ts = datetime.now().strftime("%H:%M:%S") if show_ts else ""
        
        # Iconos según nivel de log
        icons = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥"
        }
        icon = icons.get(level, "📝")
        
        # Formatear mensaje
        if ts:
            msg = f"[{ts}] {icon} {message}\n"
        else:
            msg = f"{icon} {message}\n"
            
        try:
            # Mostrar SOLO en el panel de log de aplicación
            app_log_widget = self.window.communication_panel.app_log_text
            if hasattr(app_log_widget, '_textbox'):
                # CTkTextbox
                app_log_widget._textbox.insert("end", msg)
                app_log_widget._textbox.see("end")
            else:
                # tkinter Text
                app_log_widget.insert("end", msg)
                app_log_widget.see("end")
            
            self._compact_if_needed(app_log_widget)
        except AttributeError as e:
            print(f"LOG APP ERROR: {e}")
            print(f"LOG: {msg.strip()}")
    
    def log_command_json(self, command_id, command_config, parameters, frame_hex):
        """Log de comando enviado en formato JSON"""
        try:
            show_ts = self.window.connection_panel.timestamps_var.get()
        except:
            show_ts = True
            
        timestamp = datetime.now().strftime("%H:%M:%S") if show_ts else ""
        
        # Construir parámetros con descripción
        parameters_with_desc = {}
        request_fields = command_config.get("request", {}).get("fields", [])
        
        for field in request_fields:
            field_name = field.get("name")
            if field_name in parameters:
                parameters_with_desc[field_name] = {
                    "value": parameters[field_name],
                    "description": field.get("description", "")
                }
        
        # Construir objeto JSON del comando
        command_json = {
            "timestamp": datetime.now().isoformat(),
            "command_id": command_id,
            "command_info": {
                "cid": command_config.get("cid", ""),
                "description": command_config.get("description", ""),
                "timeout_sec": command_config.get("io", {}).get("timeout_sec", 5)
            },
            "parameters": parameters_with_desc,
            "frame": {
                "hex": frame_hex,
                "length": len(bytes.fromhex(frame_hex.replace(" ", "")))
            }
        }
        
        # Formatear JSON con mejor presentación
        formatted_json = json.dumps(command_json, ensure_ascii=False, indent=2)
        
        # Agregar separador visual
        separator = "\n" + "="*50 + "\n"
        
        if timestamp:
            header = f"[{timestamp}] 📤 COMANDO ENVIADO:\n"
        else:
            header = "📤 COMANDO ENVIADO:\n"
            
        try:
            text_widget = self.window.communication_panel.cmd_json_text
            
            # Configurar tags de colores si no existen
            self._setup_cmd_json_colors(text_widget)
            
            # Insertar header y separador
            text_widget.insert("end", separator + header)
            
            # Insertar JSON con colores
            self._insert_colored_json(text_widget, formatted_json)
            text_widget.insert("end", "\n")
            
            text_widget.see("end")
            self._compact_if_needed(text_widget)
        except AttributeError as e:
            print(f"LOG COMMAND JSON ERROR: {e}")
            print(f"COMMAND JSON: {formatted_json}")
    
    def _setup_cmd_json_colors(self, text_widget):
        """Configurar tags de colores para JSON de comandos"""
        try:
            # Colores para tema oscuro (mismos que JSON normal)
            text_widget.tag_configure("json_key", foreground="#9CDCFE")      # Azul claro para claves
            text_widget.tag_configure("json_string", foreground="#CE9178")   # Naranja para strings
            text_widget.tag_configure("json_number", foreground="#B5CEA8")   # Verde para números
            text_widget.tag_configure("json_bool", foreground="#569CD6")     # Azul para booleanos
            text_widget.tag_configure("json_null", foreground="#569CD6")     # Azul para null
            text_widget.tag_configure("json_punct", foreground="#D4D4D4")    # Gris claro para puntuación
        except Exception as e:
            print(f"Error configurando colores JSON de comandos: {e}")
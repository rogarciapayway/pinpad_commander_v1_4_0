#!/usr/bin/env python3
"""
Gestor de eventos de la aplicación
"""

class EventManager:
    """Maneja la conexión de eventos entre UI y lógica de negocio"""
    
    def __init__(self, app):
        self.app = app
    
    def connect_all_events(self):
        """Conectar todos los eventos de la aplicación"""
        self._connect_connection_events()
        self._connect_command_events()
        self._connect_history_events()
        self._connect_log_events()
        self._connect_clipboard_events()
        self._connect_bridge_events()
        self.app._refresh_ports()
    
    def _connect_connection_events(self):
        """Conectar eventos del panel de conexión"""
        panel = self.app.window.connection_panel
        panel.connect_btn.configure(command=self.app._toggle_port)
        panel.refresh_btn.configure(command=self.app._refresh_ports)
        panel.rsa_btn.configure(command=self.app._load_rsa_key)
        panel.pub_btn.configure(command=self.app._load_public_key)
        panel.config_btn.configure(command=self.app._choose_config)
        panel.rsa_padding_combo.configure(command=self.app._on_padding_change)
    
    def _connect_command_events(self):
        """Conectar eventos del panel de comandos"""
        panel = self.app.window.command_panel
        panel.cmd_combo.configure(command=self.app._on_cmd_selected)
        panel.send_btn.configure(command=self.app.command_handler.send_command)
        panel.y02_btn.configure(command=self.app._apply_y02_suggested)
    
    def _connect_history_events(self):
        """Conectar eventos de historial"""
        try:
            comm_panel = self.app.window.communication_panel
            
            def find_buttons(widget, button_texts):
                buttons = {}
                for child in widget.winfo_children():
                    if hasattr(child, 'cget'):
                        try:
                            text = child.cget('text')
                            if text in button_texts:
                                buttons[text] = child
                        except:
                            pass
                    buttons.update(find_buttons(child, button_texts))
                return buttons
            
            button_texts = ['🗂️ Compactar', '🧹 Limpiar']
            buttons = find_buttons(comm_panel, button_texts)
            
            for text, button in buttons.items():
                if '🗂️ Compactar' in text:
                    button.configure(command=self.app.app_logger.compact_history)
                elif '🧹 Limpiar' in text:
                    button.configure(command=self.app.app_logger.clear_history)
        except Exception as e:
            print(f"Error conectando botones de historial: {e}")
    
    def _connect_log_events(self):
        """Conectar eventos del log de aplicación"""
        try:
            panel = self.app.window.communication_panel
            panel.log_compact_btn.configure(command=self.app.app_logger.compact_app_log)
            panel.log_clear_btn.configure(command=self.app.app_logger.clear_app_log)
        except AttributeError:
            pass
    
    def _connect_clipboard_events(self):
        """Conectar eventos de copiar y limpiar"""
        try:
            panel = self.app.window.communication_panel
            panel.hex_copy_btn.configure(command=self._copy_hex)
            panel.hex_clear_btn.configure(command=self._clear_hex)
            panel.json_copy_btn.configure(command=self._copy_json)
            panel.json_clear_btn.configure(command=self._clear_json)
            panel.cmd_json_copy_btn.configure(command=self._copy_cmd_json)
            panel.cmd_json_clear_btn.configure(command=self._clear_cmd_json)
        except AttributeError:
            pass
    
    def _copy_hex(self):
        """Copiar contenido HEX al portapapeles"""
        try:
            content = self.app.window.communication_panel.hex_text.get("1.0", "end-1c")
            self.app.window.clipboard_clear()
            self.app.window.clipboard_append(content)
            self.app.window.status.set("📋 HEX copiado")
        except Exception as e:
            self.app.window.status.set(f"❌ Error copiando HEX: {e}")
    
    def _clear_hex(self):
        """Limpiar contenido HEX"""
        try:
            self.app.window.communication_panel.hex_text.delete("1.0", "end")
            self.app.window.communication_panel.raw_hex_entry.delete(0, "end")
            self.app.window.status.set("🗑️ HEX limpiado")
        except Exception as e:
            self.app.window.status.set(f"❌ Error limpiando HEX: {e}")
    
    def _copy_json(self):
        """Copiar contenido JSON al portapapeles"""
        try:
            content = self.app.window.communication_panel.parsed_text.get("1.0", "end-1c")
            self.app.window.clipboard_clear()
            self.app.window.clipboard_append(content)
            self.app.window.status.set("📋 JSON copiado")
        except Exception as e:
            self.app.window.status.set(f"❌ Error copiando JSON: {e}")
    
    def _clear_json(self):
        """Limpiar contenido JSON"""
        try:
            self.app.window.communication_panel.parsed_text.delete("1.0", "end")
            self.app.window.status.set("🗑️ JSON limpiado")
        except Exception as e:
            self.app.window.status.set(f"❌ Error limpiando JSON: {e}")
    
    def _copy_cmd_json(self):
        """Copiar contenido JSON de comandos al portapapeles"""
        try:
            content = self.app.window.communication_panel.cmd_json_text.get("1.0", "end-1c")
            self.app.window.clipboard_clear()
            self.app.window.clipboard_append(content)
            self.app.window.status.set("Comandos JSON copiados")
        except Exception as e:
            self.app.window.status.set("Error copiando comandos JSON")
    
    def _clear_cmd_json(self):
        """Limpiar contenido JSON de comandos"""
        try:
            self.app.window.communication_panel.cmd_json_text.delete("1.0", "end")
            self.app.window.status.set("Comandos JSON limpiados")
        except Exception as e:
            self.app.window.status.set("Error limpiando comandos JSON")
    
    def _connect_bridge_events(self):
        """Conectar eventos del bridge ISO"""
        try:
            panel = self.app.window.connection_panel
            panel.bridge_echo_btn.configure(command=self.app.bridge_manager.echo_test)
        except AttributeError:
            pass
        try:
            panel = self.app.window.communication_panel
            panel.iso_copy_btn.configure(command=self._copy_iso)
            panel.iso_clear_btn.configure(command=self._clear_iso)
        except AttributeError:
            pass
    
    def _copy_iso(self):
        """Copiar contenido ISO al portapapeles"""
        try:
            content = self.app.window.communication_panel.iso_text.get("1.0", "end-1c")
            self.app.window.clipboard_clear()
            self.app.window.clipboard_append(content)
            self.app.window.status.set("ISO copiado")
        except Exception:
            pass
    
    def _clear_iso(self):
        """Limpiar contenido ISO"""
        try:
            self.app.window.communication_panel.iso_text.delete("1.0", "end")
            self.app.window.status.set("ISO limpiado")
        except Exception:
            pass
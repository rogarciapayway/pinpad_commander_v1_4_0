#!/usr/bin/env python3
"""
Gestor de configuración de la aplicación
"""

import os
import json
import html
import logging
from tkinter import messagebox

class ConfigManager:
    """Maneja la carga y validación de configuraciones"""
    
    def __init__(self, app):
        self.app = app
    
    def load_initial_config(self):
        """Cargar configuración inicial desde config/commands.json"""
        config_path = os.path.join("config", "commands.json")
        if os.path.exists(config_path):
            self.load_config(config_path)
    
    def validate_config_path(self, path):
        """Validar ruta de configuración para prevenir ataques de path traversal"""
        try:
            abs_path = os.path.abspath(os.path.normpath(path))
            
            allowed_dirs = [
                os.path.abspath("config"),
                os.path.abspath(os.getcwd())
            ]
            
            path_allowed = any(abs_path.startswith(allowed_dir + os.sep) or abs_path == allowed_dir 
                             for allowed_dir in allowed_dirs)
            
            if not path_allowed:
                raise ValueError(f"Path not in allowed directories: {path}")
            
            if not abs_path.lower().endswith('.json'):
                raise ValueError(f"Invalid file extension. Only .json files allowed")
                
            return abs_path
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid config path: {e}")
    
    def load_config(self, path):
        """Cargar archivo de configuración JSON con validación de seguridad"""
        try:
            validated_path = self.validate_config_path(path)
            
            with open(validated_path, "r", encoding="utf-8") as f:
                self.app.cfg = json.load(f)
            
            if not isinstance(self.app.cfg, dict):
                raise ValueError("Config must be a JSON object")
            
            # Establecer valores por defecto del protocolo
            self.app.cfg.setdefault("stx", 2)
            self.app.cfg.setdefault("etx", 3)
            self.app.cfg.setdefault("fs", 28)
            
            commands = self.app.cfg.get("commands", {})
            if not isinstance(commands, dict):
                raise ValueError("Commands section must be an object")
            
            # Actualizar UI
            cmds = sorted(list(commands.keys()))
            self.app.window.command_panel.cmd_combo.configure(values=cmds)
            
            if cmds:
                self.app.window.command_panel.cmd_combo.set(cmds[0])
                self.app.current_cmd_id = cmds[0]
            
            self.app._render_param_fields()
            
            # Aplicar soporte Y19 después de cargar configuración
            from y19_autopem_patch import attach_y19_autopem_support
            self.app.window.after_idle(lambda: attach_y19_autopem_support(type(self.app.window)))
            
            safe_filename = html.escape(os.path.basename(validated_path))
            self.app.window.status.set(f"⚙️ Config cargada: {safe_filename}")
            logging.info(f"Configuration loaded from {validated_path}")
            
        except (IOError, json.JSONDecodeError, KeyError) as e:
            logging.error(f"Configuration error: {e}")
            messagebox.showerror("Error de configuración", str(e))
        except Exception as e:
            logging.error(f"Unexpected configuration error: {e}")
            messagebox.showerror("Error de configuración", "Error inesperado al cargar configuración")
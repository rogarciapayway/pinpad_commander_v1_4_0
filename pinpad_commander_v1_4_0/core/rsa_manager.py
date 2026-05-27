#!/usr/bin/env python3
"""
Gestor de claves RSA
"""

import os
import json
import logging
from tkinter import messagebox, filedialog

class RSAManager:
    """Maneja las operaciones de claves RSA"""
    
    def __init__(self, app):
        self.app = app
    
    def load_rsa_key(self):
        """Cargar clave RSA privada desde archivo PEM"""
        path = filedialog.askopenfilename(
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
        )
        if not path:
            return
        
        try:
            self.app.rsa.load_key_from_file(path)
            self.app.window.status.set(f"🔑 RSA privada cargada: {os.path.basename(path)}")
        except (IOError, ValueError, KeyError) as e:
            logging.error(f"RSA key loading error: {e}")
            messagebox.showerror("Clave inválida", str(e))
        except Exception as e:
            logging.error(f"Unexpected RSA key error: {e}")
            messagebox.showerror("Clave inválida", "Error inesperado al cargar clave RSA")
    
    def load_public_key(self):
        """Cargar clave pública RSA y extraer módulo N para comando Y19"""
        path = filedialog.askopenfilename(
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
        )
        if not path:
            return
        
        try:
            with open(path, "rb") as f:
                key_data = f.read()
            
            from Crypto.PublicKey import RSA
            public_key = RSA.import_key(key_data)
            
            n_hex = format(public_key.n, 'X')
            e_hex = format(public_key.e, 'X')
            
            self._update_y19_config(n_hex, e_hex)
            self._update_rsa_fields(n_hex, e_hex)
            
            self.app.window.status.set(f"📄 Clave pública cargada: {os.path.basename(path)}")
        except (IOError, ValueError, KeyError) as e:
            logging.error(f"Public key loading error: {e}")
            messagebox.showerror("Error cargando clave pública", str(e))
        except Exception as e:
            logging.error(f"Unexpected public key error: {e}")
            messagebox.showerror("Error cargando clave pública", "Error inesperado al cargar clave pública")
    
    def _update_y19_config(self, n_hex, e_hex):
        """Actualizar configuración Y19 con nuevos valores RSA"""
        if "Y19" in self.app.cfg.get("commands", {}):
            y19_fields = self.app.cfg["commands"]["Y19"].get("request", {}).get("fields", [])
            for field in y19_fields:
                if isinstance(field, dict):
                    if field.get("name") == "RSA":
                        field["default"] = n_hex
                    elif field.get("name") == "EXP":
                        field["default"] = e_hex
            
            config_path = os.path.join("config", "commands.json")
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.app.cfg, f, ensure_ascii=False, indent=2)
            except (IOError, PermissionError) as e:
                logging.warning(f"No se pudo guardar configuración: {e}")
            except Exception as e:
                logging.error(f"Unexpected error saving configuration: {e}")
    
    def _update_rsa_fields(self, n_hex, e_hex):
        """Actualizar campos RSA en la UI"""
        rsa_widget = self.app.params_widgets.get("RSA")
        if rsa_widget:
            rsa_widget.delete(0, "end")
            rsa_widget.insert(0, n_hex)
        
        if self.app.current_cmd_id != "Y19":
            old_cmd = self.app.current_cmd_id
            self.app.current_cmd_id = "Y19"
            self.app._render_param_fields()
            
            y19_rsa_widget = self.app.params_widgets.get("RSA")
            if y19_rsa_widget:
                y19_rsa_widget.delete(0, "end")
                y19_rsa_widget.insert(0, n_hex)
            y19_exp_widget = self.app.params_widgets.get("EXP")
            if y19_exp_widget:
                y19_exp_widget.delete(0, "end")
                y19_exp_widget.insert(0, e_hex)
            
            self.app.current_cmd_id = old_cmd
            self.app._render_param_fields()
        else:
            exp_widget = self.app.params_widgets.get("EXP")
            if exp_widget:
                exp_widget.delete(0, "end")
                exp_widget.insert(0, e_hex)
    
    def load_rsa_to_field(self, entry_widget):
        """Cargar clave pública RSA directamente a un campo específico"""
        path = filedialog.askopenfilename(
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
        )
        if not path:
            return
        
        try:
            with open(path, "rb") as f:
                key_data = f.read()
            
            from Crypto.PublicKey import RSA
            public_key = RSA.import_key(key_data)
            n_hex = format(public_key.n, 'X')
            
            entry_widget.delete(0, "end")
            entry_widget.insert(0, n_hex)
            
            self.app.window.status.set(f"📂 RSA actualizado desde: {os.path.basename(path)}")
        except (IOError, ValueError, KeyError) as e:
            logging.error(f"RSA field loading error: {e}")
            messagebox.showerror("Error cargando RSA", str(e))
        except Exception as e:
            logging.error(f"Unexpected RSA field error: {e}")
            messagebox.showerror("Error cargando RSA", "Error inesperado al cargar RSA")
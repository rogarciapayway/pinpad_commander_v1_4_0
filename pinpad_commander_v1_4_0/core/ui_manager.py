#!/usr/bin/env python3
"""
Gestor de interfaz de usuario
"""

import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from ui.tooltip import ToolTip

class UIManager:
    """Maneja las operaciones de interfaz de usuario"""
    
    def __init__(self, app):
        self.app = app
    
    def render_param_fields(self):
        """Renderizar campos de parámetros dinámicamente según el comando seleccionado"""
        # Limpiar UI anterior
        for widget in self.app.window.command_panel.params_frame.winfo_children():
            widget.destroy()
        self.app.params_widgets.clear()
        
        cmd_id = self.app.window.command_panel.cmd_combo.get()
        if not cmd_id or not self.app.cfg or "commands" not in self.app.cfg:
            return
        
        self.app.current_cmd_id = cmd_id
        cdef = self.app.cfg["commands"].get(cmd_id, {})
        
        # Actualizar descripción del comando
        desc = cdef.get("description", "")
        self.app.window.command_panel.desc_label.configure(text=desc)
        
        req = cdef.get("request", {})
        fields = req.get("fields", [])
        
        if fields:
            for idx, fld in enumerate(fields):
                name = fld.get("name")
                default = fld.get("default", "")
                description = fld.get("description", "")
                
                param_frame = ctk.CTkFrame(self.app.window.command_panel.params_frame, fg_color="transparent")
                param_frame.pack(fill="x", padx=5, pady=2)
                
                # Nombre del campo (izquierda)
                label = ctk.CTkLabel(param_frame, text=f"{name}:", 
                                    font=ctk.CTkFont(size=10, weight="bold"), width=60)
                label.pack(side="left", padx=(0,5))
                
                # Campo de entrada (centro)
                if name == "RSA":
                    entry_widget = self._create_rsa_field(param_frame, name, default)
                else:
                    entry_widget = self._create_normal_field(param_frame, name, default)
                
                # Descripción con ícono (derecha)
                if description:
                    desc_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
                    desc_frame.pack(side="left", padx=(10,0))
                    
                    # Ícono de información
                    info_label = ctk.CTkLabel(desc_frame, text="ℹ️", width=20)
                    info_label.pack(side="left")
                    
                    # Texto de descripción
                    desc_text = description.split(' ', 1)[1] if ' ' in description else description
                    desc_label = ctk.CTkLabel(desc_frame, text=desc_text, 
                                            font=ctk.CTkFont(size=9), 
                                            text_color="gray70")
                    desc_label.pack(side="left", padx=(5,0))
                    
                    # Tooltip en el ícono
                    ToolTip(info_label, description)
        else:
            no_params_label = ctk.CTkLabel(self.app.window.command_panel.params_frame, 
                                           text="📝 Sin parámetros",
                                           font=ctk.CTkFont(size=11))
            no_params_label.pack(pady=10)
    
    def _create_rsa_field(self, parent, name, default):
        """Crear campo RSA con botón de carga de archivo"""
        entry_frame = ctk.CTkFrame(parent, fg_color="transparent")
        entry_frame.pack(side="left", fill="x", expand=True)
        
        ent = ctk.CTkEntry(entry_frame, height=24, width=580, placeholder_text=f"{name}")
        ent.insert(0, str(default))
        ent.pack(side="left", padx=(0,3))
        
        load_btn = ctk.CTkButton(entry_frame, text="📂", width=30, height=24,
                               command=lambda e=ent: self.app.rsa_manager.load_rsa_to_field(e))
        load_btn.pack(side="left")
        
        self.app.params_widgets[name] = ent
        return ent
    
    def _create_normal_field(self, parent, name, default):
        """Crear campo normal de entrada"""
        ent = ctk.CTkEntry(parent, height=24, width=120, placeholder_text=f"{name}")
        ent.insert(0, str(default))
        ent.pack(side="left")
        
        self.app.params_widgets[name] = ent
        return ent
    
    def apply_y02_suggested(self):
        """Aplicar configuración Y02 sugerida basada en Y19 exitoso anterior"""
        if not self.app._last_y19_result:
            from tkinter import messagebox
            messagebox.showinfo("Y02 sugerido", "Aún no hay un Y19 exitoso.")
            return
        
        self.app.window.command_panel.cmd_combo.set("Y02 Transacción")
        self.app.current_cmd_id = "Y02 Transacción"
        self.render_param_fields()
        
        # Heredar parámetros de Y19
        last_raw = getattr(self.app, '_last_y19_raw_values', {})
        
        for param in ["ENC", "IMP", "ICB"]:
            if param in last_raw:
                widget = self.app.params_widgets.get(param)
                if widget:
                    widget.delete(0, "end")
                    widget.insert(0, last_raw[param])
        
        self.app.window.status.set("Preset Y02 aplicado con herencia de Y19. Revisá y enviá.")
    
    def enable_y02_suggestion(self, parsed):
        """Habilitar botón de sugerencia Y02 tras Y19 exitoso solo si MDI != 'L'"""
        try:
            # Buscar MDI en la respuesta parseada
            mdi = None
            if isinstance(parsed, dict) and "fields" in parsed:
                for field_name, field_value in parsed["fields"].items():
                    if isinstance(field_value, dict) and "MDI" in field_value:
                        mdi = field_value["MDI"]
                        break
                    elif field_name == "MDI":
                        mdi = field_value
                        break
            
            # Solo habilitar Y02 si MDI != 'L' (CTLS)
            if mdi and mdi != "L":
                self.app.window.command_panel.y02_btn.configure(state="normal")
                self.app.window.status.set(f"✅ Y19 exitoso (MDI={mdi}) | 💡 Usar Y02 sugerido disponible")
            else:
                self.app.window.command_panel.y02_btn.configure(state="disabled")
                if mdi == "L":
                    self.app.window.status.set("✅ Y19 exitoso (CTLS) - Transacción finalizada")
                else:
                    self.app.window.status.set("✅ Y19 exitoso - MDI no detectado")
        except AttributeError:
            pass
    
    def on_padding_change(self, value):
        """Callback cuando cambia el modo de padding RSA"""
        self.app.rsa_padding.set(value)
    
    def on_cmd_selected(self, value=None):
        """Callback cuando se selecciona un comando en el ComboBox"""
        cmd_id = value or self.app.window.command_panel.cmd_combo.get()
        self.app.current_cmd_id = cmd_id
        
        # Deshabilitar botón Y02 al cambiar comando
        try:
            self.app.window.command_panel.y02_btn.configure(state="disabled")
        except AttributeError:
            pass
        
        self.render_param_fields()
    
    def choose_config(self):
        """Abrir diálogo para elegir archivo de configuración personalizado"""
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")], 
            initialdir=os.path.join(os.getcwd(), "config")
        )
        if path:
            self.app.config_manager.load_config(path)
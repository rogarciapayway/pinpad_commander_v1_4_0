#!/usr/bin/env python3
"""
Gestor de comunicación serial
"""

import logging
from tkinter import messagebox

class SerialManager:
    """Maneja las operaciones de puerto serial"""
    
    def __init__(self, app):
        self.app = app
    
    def refresh_ports(self):
        """Actualizar lista de puertos COM disponibles"""
        ports = self.app.comm.get_available_ports()
        current_value = self.app.window.connection_panel.port_combo.get()
        
        self.app.window.connection_panel.port_combo.configure(values=ports)
        
        # Mantener selección si aún existe
        if current_value in ports:
            self.app.window.connection_panel.port_combo.set(current_value)
        elif ports:
            self.app.window.connection_panel.port_combo.set(ports[0])
        
        # Actualizar status
        self.app.window.status.set(f"🔄 {len(ports)} puertos encontrados")
    
    def toggle_port(self):
        """Alternar conexión del puerto serial (abrir/cerrar)"""
        if self.app.comm.is_connected():
            self._disconnect_port()
        else:
            self._connect_port()
    
    def _disconnect_port(self):
        """Desconectar puerto serial"""
        self.app.comm.disconnect()
        self.app.window.connection_panel.connect_btn.configure(text="🔌 Abrir Puerto")
        self.app.window.conn_status.set("❌ Desconectado")
        self.app.window.status.set("ℹ️ Puerto cerrado")
    
    def _connect_port(self):
        """Conectar puerto serial"""
        try:
            port_with_desc = self.app.window.connection_panel.port_combo.get()
            if not port_with_desc:
                messagebox.showerror("Error", "Selecciona un puerto COM")
                return
            
            # Extraer solo el nombre del puerto (ej: "COM5" de "COM5 - USB Serial Port")
            port = port_with_desc.split(" - ")[0]
            
            baudrate = int(self.app.window.connection_panel.baud_entry.get() or "115200")
            timeout = float(self.app.window.connection_panel.timeout_entry.get() or "1.0")
            
            self.app.comm.connect(port, baudrate, timeout, 
                            self.app.cfg.get("stx", 2),
                            self.app.cfg.get("etx", 3),
                            self.app.cfg.get("fs", 28))
            
            self.app.window.connection_panel.connect_btn.configure(text="❌ Cerrar Puerto")
            self.app.window.conn_status.set(f"✅ Conectado: {port}")
            self.app.window.status.set("✅ Puerto abierto correctamente")
            
        except Exception as e:
            messagebox.showerror("Error al abrir puerto", str(e))
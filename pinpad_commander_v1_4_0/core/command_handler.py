#!/usr/bin/env python3
"""
Manejador de comandos del PinPad
"""

import re
import threading
from tkinter import messagebox


class CommandHandler:
    def __init__(self, app):
        self.app = app
    
    def send_command(self):
        """Enviar comando"""
        if not self.app.comm.is_connected():
            messagebox.showwarning("Puerto cerrado", "Abrí el puerto antes de enviar.")
            return
        
        if not self.app.current_cmd_id:
            messagebox.showerror("Sin comando", "Elegí un comando.")
            return
        
        try:
            cdef = self.app.cfg["commands"][self.app.current_cmd_id]
            reqdef = cdef.get("request", {})
        except KeyError:
            error_msg = f"Comando {self.app.current_cmd_id} no encontrado en configuración"
            messagebox.showerror("Error", error_msg)
            return
        
        # Recopilar valores de parámetros
        values = {}
        for fld in reqdef.get("fields", []):
            name = fld.get("name")
            widget = self.app.params_widgets.get(name)
            raw = widget.get() if widget else ""
            val = self._format_value(raw, fld.get("format"))
            values[name] = val
        
        self.app._last_sent[self.app.current_cmd_id] = values
        
        # Guardar valores originales para Y19 (para herencia Y02)
        if self.app.current_cmd_id == "Y19 Transacción":
            raw_values = {}
            for fld in reqdef.get("fields", []):
                name = fld.get("name")
                widget = self.app.params_widgets.get(name)
                if widget:
                    raw_values[name] = widget.get()  # Valor sin formatear
            self.app._last_y19_raw_values = raw_values
        
        # Construir frame
        try:
            frame = self._build_frame(cdef, reqdef, values)
            self.app._log_hex("TX", frame)
            
            # Registrar comando en formato JSON
            frame_hex = " ".join(f"{b:02X}" for b in frame)
            self.app.app_logger.log_command_json(self.app.current_cmd_id, cdef, values, frame_hex)
            
            # Enviar en hilo separado
            threading.Thread(target=self._io_exchange, args=(frame, cdef), daemon=True).start()
        except (ValueError, KeyError, TypeError) as e:
            error_msg = f"Error al construir trama {self.app.current_cmd_id}: {str(e)}"
            self.app._log_text(f"❌ {error_msg}\n")
            messagebox.showerror("Error al construir trama", error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al construir trama {self.app.current_cmd_id}: {str(e)}"
            self.app._log_text(f"❌ {error_msg}\n")
            messagebox.showerror("Error al construir trama", error_msg)
    
    def _format_value(self, value, fmt):
        """Formatear valor según especificación"""
        if not isinstance(fmt, dict) or not fmt:
            return value
        
        t = fmt.get("type")
        if t == "amount":
            decs = int(fmt.get("decimals", 2))
            pad = int(fmt.get("pad", 0))
            v = value.strip().replace(",", ".")
            v = "0" if v == "" else v
            left, right = v.split(".", 1) if "." in v else (v, "")
            right = right.ljust(decs, "0")[:decs]
            num_str = left + right
            if pad > 0:
                return num_str.zfill(pad)[:pad]  # Truncar si excede el padding
            return num_str
        elif t == "padleft":
            length = int(fmt.get("len", 0))
            char = fmt.get("ch", "0")
            v = str(value).strip()
            return v.zfill(length) if char == "0" else v.rjust(length, char)
        elif t == "padright":
            length = int(fmt.get("len", 0))
            char = fmt.get("ch", " ")
            v = str(value).strip()
            return v.ljust(length, char)[:length]  # Truncar si excede la longitud
        elif t == "hex":
            pad = int(fmt.get("pad", 0))
            v = value.strip().replace(" ", "").upper()
            return v.zfill(pad) if pad else v
        elif t == "string":
            pad = int(fmt.get("pad", 0))
            return value.ljust(pad)[:pad] if pad else value
        elif t == "upper":
            return str(value).upper()
        elif t == "digits":
            return re.sub(r'[^0-9]', '', str(value))
        return value
    
    def _build_frame(self, cdef, reqdef, values):
        """Construir trama del comando"""
        segments = reqdef.get("segments")
        if segments:
            payload = b""
            fs_b = bytes([self.app.cfg.get("fs", 28)])
            for seg in segments:
                st = seg.get("type")
                if st == "fs":
                    payload += fs_b
                elif st == "field":
                    payload += values.get(seg.get("name"), "").encode("ascii", errors="ignore")
                elif st == "concat":
                    for nm in seg.get("fields", []):
                        payload += values.get(nm, "").encode("ascii", errors="ignore")
                elif st == "literal":
                    payload += str(seg.get("value", "")).encode("ascii", errors="ignore")
            
            body = cdef.get("cid", self.app.current_cmd_id).encode("ascii") + payload + bytes([self.app.cfg.get("etx", 3)])
            lrc_val = self._calculate_lrc(body)
            return bytes([self.app.cfg.get("stx", 2)]) + body + bytes([lrc_val])
        else:
            data_fields = [values.get(fld.get("name"), "") for fld in reqdef.get("fields", [])]
            if hasattr(self.app.comm, 'codec') and self.app.comm.codec:
                return self.app.comm.codec.build_frame(cdef.get("cid", self.app.current_cmd_id), data_fields)
            else:
                frame_parts = []
                frame_parts.append(bytes([self.app.cfg.get("stx", 2)]))
                frame_parts.append(cdef.get("cid", "").encode("ascii"))
                
                fs_byte = bytes([self.app.cfg.get("fs", 28)])
                for fld in reqdef.get("fields", []):
                    name = fld.get("name")
                    value = values.get(name, "")
                    frame_parts.append(str(value).encode("ascii"))
                    frame_parts.append(fs_byte)
                
                frame_parts.append(bytes([self.app.cfg.get("etx", 3)]))
                frame_data = b"".join(frame_parts)
                body = frame_data[1:]
                lrc_val = self._calculate_lrc(body)
                return frame_data + bytes([lrc_val])
    
    def _calculate_lrc(self, data):
        """Calcular LRC"""
        lrc = 0
        for b in data:
            lrc ^= b
        return lrc
    
    def _io_exchange(self, frame, cdef):
        """Intercambio I/O en hilo separado"""
        try:
            self.app.comm.ser.reset_input_buffer()
            self.app.comm.ser.write(frame)
            self.app.comm.ser.flush()
            
            # Leer ACK si se espera
            ack_expected = cdef.get("io", {}).get("expect_ack", True)
            if ack_expected and self.app.window.command_panel.ack_var.get():
                b = self.app.comm.ser.read(1)
                if b == b'\x06':
                    self.app._log_hex("RX", b)
            
            # Y06 no espera respuesta
            if self.app.current_cmd_id == "Y06":
                self.app._log_text("Y06 enviado - No se espera respuesta.\n")
                self.app.window.after(0, lambda: self.app.window.status.set("✅ Y06 enviado (sin respuesta)"))
                return
            
            timeout = cdef.get("io", {}).get("timeout_sec", 5.0)
            self.app._log_text(f"Esperando respuesta (timeout={timeout}s)...\n")
            
            response = self.app.comm.read_frame(timeout)
            if response:
                self.app._log_hex("RX", response)
                self.app.window.after(0, lambda: self._process_response(response, cdef))
            else:
                self.app._log_text("No se recibió respuesta dentro del timeout.\n")
                self.app.window.after(0, lambda: self.app.window.status.set(f"⚠️ Sin respuesta (timeout {timeout}s)"))
        except (OSError, IOError) as e:
            self.app._log_text(f"Error I/O: {e}\n")
            self.app.window.after(0, lambda: messagebox.showerror("Error I/O", str(e)))
        except Exception as e:
            self.app._log_text(f"Error I/O inesperado: {e}\n")
            self.app.window.after(0, lambda: messagebox.showerror("Error I/O", "Error inesperado de comunicación"))
    
    def _process_response(self, response, cdef):
        """Procesar respuesta recibida"""
        try:
            ok, parsed = self.app.parser.validate_and_parse(response, cdef, self.app.current_cmd_id)
            if ok:
                self.app._log_parsed(parsed)
                if parsed.get("cid") == "Y19":
                    self.app._last_y19_result = parsed
                    self.app._enable_y02_suggestion(parsed)
                    # Bridge ISO: si esta ON, procesar Y19 -> ISO 0200
                    # Para manual (MDI=M), esperar al Y02
                    try:
                        self.app.bridge_manager.process_y19_response(parsed)
                    except Exception as e:
                        self.app._log_text('Bridge ISO error: %s\n' % e)
                elif parsed.get("cid") == "Y02":
                    # Bridge ISO: si modo manual, Y02 tiene el PAN real
                    try:
                        self.app.bridge_manager.process_y02_response(parsed)
                    except Exception as e:
                        self.app._log_text('Bridge ISO Y02 error: %s\n' % e)
                self.app.window.status.set("Respuesta procesada")
                self.app.window.status.set("✅ Respuesta procesada")
            else:
                self.app._log_text(parsed + "\n")
                self.app.window.status.set(f"❌ Error: {parsed}")
        except Exception as e:
            self.app.window.status.set(f"❌ Error: {str(e)}")
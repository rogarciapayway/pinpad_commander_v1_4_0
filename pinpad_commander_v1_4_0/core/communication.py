import serial
import serial.tools.list_ports
import time
import threading
import logging
from protocol import FrameCodec, FSParser, hexlify

class SerialCommunication:
    def __init__(self):
        self.ser = None
        self.codec = None
        
    def get_available_ports(self):
        ports = []
        for p in serial.tools.list_ports.comports():
            # Formato: "COM1 - USB Serial Port"
            desc = p.description if p.description else "Unknown Device"
            ports.append(f"{p.device} - {desc}")
        return ports
    
    def connect(self, port, baudrate=115200, timeout=1.0, stx=2, etx=3, fs=28):
        try:
            self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            self.codec = FrameCodec(stx=stx, etx=etx, fs=fs)
            logging.info(f"Connected to {port} at {baudrate} baud")
            return True
        except serial.SerialException as e:
            self.ser = None
            logging.error(f"Serial connection error: {e}")
            raise serial.SerialException(f"Failed to connect to {port}: {e}")
        except Exception as e:
            self.ser = None
            logging.error(f"Unexpected connection error: {e}")
            raise RuntimeError(f"Connection failed: {e}")
    
    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except (OSError, AttributeError):
                pass
        self.ser = None
    
    def is_connected(self):
        return self.ser and self.ser.is_open
    
    def send_frame(self, frame):
        if not self.is_connected():
            raise RuntimeError("Puerto no conectado")
        try:
            self.ser.reset_input_buffer()
            self.ser.write(frame)
            self.ser.flush()
        except serial.SerialException as e:
            logging.error(f"Error sending frame: {e}")
            raise serial.SerialException(f"Failed to send frame: {e}")
    
    def read_frame(self, timeout_override=None):
        if not self.is_connected():
            return None
            
        try:
            tout = float(timeout_override if timeout_override is not None else self.ser.timeout or 5.0)
            t0 = time.time()
            
            # Buscar STX con timeout
            stx_found = False
            while time.time() - t0 < tout:
                try:
                    b = self.ser.read(1)
                    if not b:
                        continue
                    if b == bytes([self.codec.stx]):
                        stx_found = True
                        break
                except serial.SerialException as e:
                    logging.error(f"Serial error reading STX: {e}")
                    return None
            
            if not stx_found:
                return None
                
            buf = bytearray()
            buf.append(self.codec.stx)
            
            # Leer resto del frame con timeout extendido
            while time.time() - t0 < tout * 3:
                try:
                    b = self.ser.read(1)
                    if not b:
                        continue
                    buf += b
                    if b == bytes([self.codec.etx]):
                        lrc = self.ser.read(1)
                        if not lrc:
                            continue
                        buf += lrc
                        return bytes(buf)
                    
                    # Prevenir frames excesivamente largos
                    if len(buf) > 8192:
                        logging.error("Frame too large, aborting")
                        return None
                        
                except serial.SerialException as e:
                    logging.error(f"Serial error reading frame: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logging.error(f"Unexpected error in read_frame: {e}")
            return None
    
    def send_and_receive(self, frame, timeout_override=None):
        """Enviar frame y recibir respuesta"""
        self.send_frame(frame)
        return self.read_frame(timeout_override)
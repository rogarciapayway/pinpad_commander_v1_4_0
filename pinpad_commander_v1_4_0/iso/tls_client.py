"""
Cliente TLS para comunicación ISO 8583 con el host.

Maneja conexión TLS, envío de mensajes con header de longitud,
y recepción de respuestas.
"""

import ssl
import socket
import struct
import logging
import time


class TLSClient:
    def __init__(self, host: str, port: int, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.ssl_sock = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.settimeout(15.0)  # timeout agresivo para connect

            self.ssl_sock = ctx.wrap_socket(raw, server_hostname=self.host)
            self.ssl_sock.connect((self.host, self.port))
            self.ssl_sock.settimeout(self.timeout)  # timeout normal para operaciones

            self.logger.info(f"TLS connected to {self.host}:{self.port}")
            return True

        except (socket.error, ssl.SSLError, OSError, socket.timeout) as e:
            self.logger.error(f"TLS connection failed: {e}")
            self.disconnect()
            raise ConnectionError(f"No se pudo conectar a {self.host}:{self.port}: {e}")

    def disconnect(self):
        if self.ssl_sock:
            try:
                self.ssl_sock.close()
            except Exception:
                pass
            self.ssl_sock = None

    def is_connected(self) -> bool:
        if not self.ssl_sock:
            return False
        try:
            # Verificar que el socket sigue vivo
            self.ssl_sock.getpeername()
            return True
        except Exception:
            self.ssl_sock = None
            return False

    def send(self, data: bytes) -> None:
        if not self.is_connected():
            raise ConnectionError("No hay conexión TLS activa")
        try:
            self.ssl_sock.sendall(data)
            self.logger.info(f"TX: {len(data)} bytes")
            self.logger.debug(f"TX HEX: {data.hex().upper()}")
        except (socket.error, ssl.SSLError, OSError) as e:
            self.logger.error(f"Send error: {e}")
            self.disconnect()
            raise ConnectionError(f"Error enviando datos: {e}")

    def receive(self, timeout: float = None) -> bytes:
        if not self.is_connected():
            raise ConnectionError("No hay conexión TLS activa")

        tout = timeout or self.timeout
        self.ssl_sock.settimeout(tout)

        try:
            # Leer 2 bytes de longitud (Big Endian)
            len_bytes = self._recv_exact(2)
            if not len_bytes:
                return b''

            msg_len = struct.unpack('>H', len_bytes)[0]
            self.logger.debug(f"Esperando {msg_len} bytes de mensaje")

            msg_data = self._recv_exact(msg_len)
            if not msg_data:
                return b''

            self.logger.info(f"RX: {len(msg_data)} bytes")
            self.logger.debug(f"RX HEX: {msg_data.hex().upper()}")
            return msg_data

        except socket.timeout:
            self.logger.warning(f"Timeout esperando respuesta ({tout}s)")
            return b''
        except (socket.error, ssl.SSLError, OSError) as e:
            self.logger.error(f"Receive error: {e}")
            self.disconnect()
            raise ConnectionError(f"Error recibiendo datos: {e}")

    def _recv_exact(self, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = self.ssl_sock.recv(n - len(buf))
            if not chunk:
                return b''
            buf += chunk
        return buf

    def send_and_receive(self, data: bytes, timeout: float = None) -> bytes:
        self.send(data)
        return self.receive(timeout)

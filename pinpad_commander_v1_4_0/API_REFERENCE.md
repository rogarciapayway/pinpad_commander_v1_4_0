# API Reference - PinPad Commander

## 📋 Índice

- [Clases Principales](#clases-principales)
- [Módulos Core](#módulos-core)
- [Interfaces de Comunicación](#interfaces-de-comunicación)
- [Criptografía](#criptografía)
- [Parsers y Decodificadores](#parsers-y-decodificadores)
- [Gestores Especializados](#gestores-especializados)
- [Utilidades](#utilidades)

## 🏗️ Clases Principales

### PinPadCommanderModular

**Descripción**: Clase principal que coordina todos los componentes de la aplicación.

```python
class PinPadCommanderModular:
    def __init__(self)
    def run(self) -> None
    def compact_history(self) -> None
    def clear_history(self) -> None
```

**Métodos**:

#### `__init__(self)`
Inicializa la aplicación y todos sus componentes.

**Parámetros**: Ninguno

**Ejemplo**:
```python
app = PinPadCommanderModular()
```

#### `run(self) -> None`
Ejecuta el bucle principal de la aplicación GUI.

**Ejemplo**:
```python
app = PinPadCommanderModular()
app.run()  # Inicia la interfaz gráfica
```

#### `compact_history(self) -> None`
Compacta el historial de logs eliminando entradas duplicadas.

#### `clear_history(self) -> None`
Limpia completamente el historial de logs.

---

## 🔧 Módulos Core

### SerialCommunication

**Descripción**: Maneja la comunicación serie con dispositivos PinPad.

```python
class SerialCommunication:
    def __init__(self, timeout: float = 5.0)
    def connect(self, port: str, baudrate: int = 115200) -> bool
    def disconnect(self) -> None
    def send_command(self, frame: bytes, timeout: float = None) -> bytes
    def is_connected(self) -> bool
    def get_available_ports(self) -> List[str]
```

**Métodos**:

#### `connect(self, port: str, baudrate: int = 115200) -> bool`
Establece conexión con el dispositivo PinPad.

**Parámetros**:
- `port` (str): Puerto serie (ej: "COM3", "/dev/ttyUSB0")
- `baudrate` (int): Velocidad de comunicación (default: 115200)

**Retorna**: `bool` - True si la conexión fue exitosa

**Ejemplo**:
```python
comm = SerialCommunication()
if comm.connect("COM3", 115200):
    print("Conectado exitosamente")
```

#### `send_command(self, frame: bytes, timeout: float = None) -> bytes`
Envía un comando al dispositivo y espera respuesta.

**Parámetros**:
- `frame` (bytes): Frame completo del comando
- `timeout` (float): Timeout en segundos (opcional)

**Retorna**: `bytes` - Respuesta del dispositivo

**Excepciones**:
- `TimeoutError`: Si no hay respuesta en el tiempo especificado
- `ConnectionError`: Si no hay conexión activa

**Ejemplo**:
```python
frame = build_y0i_frame()
response = comm.send_command(frame, timeout=10.0)
```

### ResponseParser

**Descripción**: Analiza y decodifica respuestas del dispositivo PinPad.

```python
class ResponseParser:
    def __init__(self, comm: SerialCommunication, processor: DataProcessor, app)
    def parse_response(self, command_id: str, response: bytes) -> dict
    def decode_field(self, value: str, decoder: str) -> Any
    def parse_emv_tlv(self, hex_data: str) -> dict
```

**Métodos**:

#### `parse_response(self, command_id: str, response: bytes) -> dict`
Parsea la respuesta completa de un comando.

**Parámetros**:
- `command_id` (str): ID del comando (ej: "Y19", "Y02")
- `response` (bytes): Respuesta cruda del dispositivo

**Retorna**: `dict` - Datos parseados y decodificados

**Ejemplo**:
```python
parser = ResponseParser(comm, processor, app)
parsed = parser.parse_response("Y19", response_bytes)
print(parsed['tarj_enmascarada'])  # Número de tarjeta enmascarado
```

#### `decode_field(self, value: str, decoder: str) -> Any`
Decodifica un campo individual según el tipo especificado.

**Parámetros**:
- `value` (str): Valor a decodificar
- `decoder` (str): Tipo de decodificador ("trim", "hex", "tlv_hex", etc.)

**Retorna**: `Any` - Valor decodificado

**Decodificadores disponibles**:
- `trim`: Elimina espacios en blanco
- `hex`: Convierte de hexadecimal a bytes
- `tlv_hex`: Parsea formato TLV desde hex
- `hex_ascii_printable`: Filtra caracteres ASCII imprimibles
- `bcd_digits`: Convierte BCD a dígitos

### DataProcessor

**Descripción**: Procesa y formatea datos para comandos.

```python
class DataProcessor:
    def __init__(self)
    def format_field(self, value: Any, format_config: dict) -> str
    def build_command_frame(self, command_config: dict, params: dict) -> bytes
    def validate_field(self, value: Any, validation_rules: dict) -> bool
```

**Métodos**:

#### `format_field(self, value: Any, format_config: dict) -> str`
Formatea un campo según la configuración especificada.

**Parámetros**:
- `value` (Any): Valor a formatear
- `format_config` (dict): Configuración de formato

**Ejemplo**:
```python
processor = DataProcessor()
formatted = processor.format_field("123.45", {
    "type": "amount",
    "decimals": 2,
    "pad": 12
})
# Resultado: "000012345"
```

**Formateadores disponibles**:
- `padleft`: Rellena a la izquierda
- `padright`: Rellena a la derecha
- `upper`: Convierte a mayúsculas
- `amount`: Formatea importes monetarios
- `digits`: Extrae solo dígitos

---

## 🔐 Criptografía

### RSAHandler

**Descripción**: Maneja operaciones de criptografía RSA.

```python
class RSAHandler:
    def __init__(self)
    def load_private_key(self, key_path: str, password: str = None) -> bool
    def load_public_key(self, key_path: str) -> bool
    def encrypt(self, data: bytes, padding: str = "RAW-NoPadding") -> bytes
    def decrypt(self, data: bytes, padding: str = "RAW-NoPadding") -> bytes
    def get_public_key_hex(self) -> str
```

**Métodos**:

#### `load_private_key(self, key_path: str, password: str = None) -> bool`
Carga una clave privada RSA desde archivo.

**Parámetros**:
- `key_path` (str): Ruta al archivo de clave privada
- `password` (str): Contraseña de la clave (opcional)

**Retorna**: `bool` - True si la carga fue exitosa

**Formatos soportados**:
- PEM
- DER
- PKCS#8
- PKCS#1

**Ejemplo**:
```python
rsa = RSAHandler()
if rsa.load_private_key("private_key.pem", "password123"):
    print("Clave privada cargada")
```

#### `decrypt(self, data: bytes, padding: str = "RAW-NoPadding") -> bytes`
Desencripta datos usando la clave privada cargada.

**Parámetros**:
- `data` (bytes): Datos encriptados
- `padding` (str): Tipo de padding ("RAW-NoPadding", "PKCS1", "OAEP")

**Retorna**: `bytes` - Datos desencriptados

**Excepciones**:
- `ValueError`: Si no hay clave privada cargada
- `CryptoError`: Si falla la desencriptación

---

## 🎯 Gestores Especializados

### SerialManager

**Descripción**: Gestiona conexiones y operaciones del puerto serie.

```python
class SerialManager:
    def __init__(self, app: PinPadCommanderModular)
    def toggle_port(self) -> None
    def refresh_ports(self) -> None
    def get_connection_status(self) -> str
```

### RSAManager

**Descripción**: Gestiona operaciones de criptografía RSA.

```python
class RSAManager:
    def __init__(self, app: PinPadCommanderModular)
    def load_rsa_key(self) -> None
    def load_public_key(self) -> None
    def get_key_info(self) -> dict
```

### UIManager

**Descripción**: Gestiona la interfaz de usuario y eventos.

```python
class UIManager:
    def __init__(self, app: PinPadCommanderModular)
    def render_param_fields(self) -> None
    def on_cmd_selected(self, value: str = None) -> None
    def apply_y02_suggested(self) -> None
```

### EMVManager

**Descripción**: Gestiona operaciones específicas de EMV.

```python
class EMVManager:
    def __init__(self, app: PinPadCommanderModular)
    def load_emv_tags(self) -> None
    def emv_pretty(self, tlv_data: dict) -> str
    def bcd_digits(self, hex_str: str) -> str
    def amount_from_bcd_hex(self, hex_str: str, exp: int = 2) -> str
```

**Métodos**:

#### `emv_pretty(self, tlv_data: dict) -> str`
Convierte datos TLV EMV a formato legible.

**Parámetros**:
- `tlv_data` (dict): Datos TLV parseados

**Retorna**: `str` - Representación legible de los datos EMV

**Ejemplo**:
```python
emv_manager = EMVManager(app)
tlv_data = {"9F02": "000000012345", "5F2A": "0032"}
pretty = emv_manager.emv_pretty(tlv_data)
# Resultado:
# 9F02 (Amount, Authorised): 123.45
# 5F2A (Transaction Currency Code): 032 (ARS)
```

---

## 🛠️ Utilidades

### FrameCodec

**Descripción**: Codifica y decodifica frames del protocolo.

```python
class FrameCodec:
    def __init__(self, stx: int = 0x02, etx: int = 0x03, fs: int = 0x1C)
    def build_frame(self, cid: str, fields: List[str]) -> bytes
    def extract(self, frame: bytes) -> Tuple[str, bytes]
    def validate_lrc(self, frame: bytes) -> bool
    @staticmethod
    def lrc(data: bytes) -> int
```

**Métodos**:

#### `build_frame(self, cid: str, fields: List[str]) -> bytes`
Construye un frame completo del protocolo.

**Parámetros**:
- `cid` (str): Command ID (3 caracteres)
- `fields` (List[str]): Lista de campos del comando

**Retorna**: `bytes` - Frame completo con STX, ETX y LRC

**Ejemplo**:
```python
codec = FrameCodec()
frame = codec.build_frame("Y0I", [])
# Resultado: b'\x02Y0I\x03J'
```

#### `extract(self, frame: bytes) -> Tuple[str, bytes]`
Extrae CID y payload de un frame.

**Parámetros**:
- `frame` (bytes): Frame completo

**Retorna**: `Tuple[str, bytes]` - (CID, payload)

**Excepciones**:
- `ValueError`: Si el frame es inválido

### FSParser

**Descripción**: Parser para campos separados por FS (Field Separator).

```python
class FSParser:
    def __init__(self, fs: int = 0x1C)
    def parse(self, payload: bytes) -> List[str]
```

---

## 📊 Eventos y Callbacks

### EventManager

**Descripción**: Gestiona eventos y callbacks del sistema.

```python
class EventManager:
    def __init__(self, app: PinPadCommanderModular)
    def connect_all_events(self) -> None
    def emit_event(self, event_name: str, *args, **kwargs) -> None
    def register_callback(self, event_name: str, callback: Callable) -> None
```

**Eventos disponibles**:
- `connection_changed`: Cambio en el estado de conexión
- `command_sent`: Comando enviado al dispositivo
- `response_received`: Respuesta recibida del dispositivo
- `parsing_completed`: Parsing de respuesta completado
- `error_occurred`: Error en cualquier operación

**Ejemplo**:
```python
def on_response_received(command_id, response_data):
    print(f"Respuesta recibida para {command_id}")

event_manager.register_callback("response_received", on_response_received)
```

---

## 🔧 Configuración

### ConfigManager

**Descripción**: Gestiona la carga y guardado de configuraciones.

```python
class ConfigManager:
    def __init__(self, app: PinPadCommanderModular)
    def load_initial_config(self) -> None
    def load_commands(self) -> dict
    def load_emv_tags(self) -> dict
    def save_user_preferences(self, preferences: dict) -> None
```

**Archivos de configuración**:
- `config/commands.json`: Definición de comandos
- `config/emv_tags.json`: Tags EMV estándar
- `config/field_decoders.json`: Decodificadores de campos
- `config/response_parsers.json`: Configuración de parsers
- `config/validation_rules.json`: Reglas de validación

---

## 📝 Logging

### AppLogger

**Descripción**: Sistema de logging de la aplicación.

```python
class AppLogger:
    def __init__(self, window: MainWindow)
    def log_hex(self, direction: str, data: bytes) -> None
    def log_text(self, text: str) -> None
    def log_parsed(self, parsed_data: dict) -> None
    def compact_history(self) -> None
    def clear_history(self) -> None
```

**Métodos**:

#### `log_hex(self, direction: str, data: bytes) -> None`
Registra datos en formato hexadecimal.

**Parámetros**:
- `direction` (str): "TX" para enviado, "RX" para recibido
- `data` (bytes): Datos a registrar

#### `log_parsed(self, parsed_data: dict) -> None`
Registra datos parseados en formato legible.

**Parámetros**:
- `parsed_data` (dict): Datos parseados a registrar

---

## 🚨 Excepciones Personalizadas

```python
class PinPadError(Exception):
    """Excepción base para errores del PinPad"""
    pass

class CommunicationError(PinPadError):
    """Error de comunicación con el dispositivo"""
    pass

class ParsingError(PinPadError):
    """Error al parsear respuesta del dispositivo"""
    pass

class CryptoError(PinPadError):
    """Error en operaciones criptográficas"""
    pass

class ConfigurationError(PinPadError):
    """Error en configuración"""
    pass
```

---

## 📚 Ejemplos de Uso

### Ejemplo Completo: Ejecutar Comando Y19

```python
from app_modular_refactored import PinPadCommanderModular

# Inicializar aplicación
app = PinPadCommanderModular()

# Conectar al dispositivo
if app.serial_manager.comm.connect("COM3"):
    print("Conectado al PinPad")
    
    # Cargar clave RSA
    if app.rsa.load_private_key("private_key.pem"):
        print("Clave RSA cargada")
        
        # Configurar parámetros del comando Y19
        params = {
            "RSA": app.rsa.get_public_key_hex(),
            "EXP": "10001",
            "IMP": "123.45",
            "TTY": "00"
        }
        
        # Ejecutar comando
        try:
            response = app.command_handler.execute_command("Y19", params)
            print("Transacción completada:", response)
        except Exception as e:
            print("Error en transacción:", e)
    
    # Desconectar
    app.serial_manager.comm.disconnect()
```

### Ejemplo: Parser Personalizado

```python
def custom_field_parser(data: str) -> dict:
    """Parser personalizado para campo específico"""
    parts = data.split('|')
    return {
        'field1': parts[0] if len(parts) > 0 else '',
        'field2': parts[1] if len(parts) > 1 else '',
        'timestamp': datetime.now().isoformat()
    }

# Registrar parser personalizado
app.parser.register_custom_parser('custom_field', custom_field_parser)
```

---

Esta referencia de API proporciona una documentación completa de todas las clases, métodos y funcionalidades disponibles en PinPad Commander.
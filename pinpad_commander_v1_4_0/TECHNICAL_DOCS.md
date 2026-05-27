# Documentación Técnica - PinPad Commander v1.4.0

## 🏗️ Arquitectura del Sistema

### Patrón de Diseño

El proyecto implementa una **arquitectura modular basada en gestores especializados** con los siguientes patrones:

- **Facade Pattern**: `PinPadCommanderModular` actúa como fachada principal
- **Manager Pattern**: Gestores especializados para cada responsabilidad
- **Observer Pattern**: Sistema de eventos para comunicación entre componentes
- **Strategy Pattern**: Diferentes estrategias de parsing según el comando
- **Factory Pattern**: Creación dinámica de parsers y decodificadores
- **Command Pattern**: Manejo de comandos con configuración JSON

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                PinPadCommanderModular                       │
│                    (Facade Principal)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌─────────────┐
│UI Layer │    │ Core Layer  │    │Crypto Layer │
└─────────┘    └─────────────┘    └─────────────┘
    │                 │                 │
    ▼                 ▼                 ▼
┌──────────┐   ┌──────────────┐   ┌─────────────┐
│MainWindow│   │SerialComm    │   │RSAHandler   │
│Tooltip   │   │DataProcessor │   │             │
└──────────┘   │ResponseParser│   └─────────────┘
               │CommandHandler│
               │Logger        │
               │EventManager  │
               │ConfigManager │
               │SerialManager │
               │RSAManager    │
               │UIManager     │
               │EMVManager    │
               └──────────────┘
```

### Gestores Especializados

#### **EventManager** (`core/event_manager.py`)
- Conecta eventos de UI con handlers de negocio
- Gestiona callbacks y bindings
- Centraliza la comunicación entre componentes

#### **ConfigManager** (`core/config_manager.py`)
- Carga configuraciones JSON desde `/config`
- Gestiona comandos, parsers y decodificadores
- Maneja configuración de usuario

#### **SerialManager** (`core/serial_manager.py`)
- Gestiona conexión/desconexión de puertos
- Refresca lista de puertos disponibles
- Maneja estados de conexión

#### **RSAManager** (`core/rsa_manager.py`)
- Carga claves RSA públicas y privadas
- Gestiona configuración de padding
- Integra con RSAHandler para operaciones criptográficas

#### **UIManager** (`core/ui_manager.py`)
- Renderiza formularios dinámicos de parámetros
- Gestiona selección de comandos
- Maneja sugerencias Y02 automáticas

#### **EMVManager** (`core/emv_manager.py`)
- Carga tags EMV desde configuración
- Formatea datos EMV para visualización
- Convierte formatos BCD y amounts

## 🔧 Módulos Core

### 1. Communication (`core/communication.py`)

**Responsabilidades:**
- Gestión de conexiones serie con `pyserial`
- Protocolo de frames con STX/ETX/LRC
- Control de timeouts y reconexiones automáticas
- Validación de integridad de datos con LRC
- Manejo de errores de comunicación

**Métodos principales:**
```python
class SerialCommunication:
    def get_available_ports(self) -> List[str]
    def connect(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> bool
    def disconnect(self) -> None
    def send_frame(self, frame: bytes) -> None
    def read_frame(self, timeout_override: float = None) -> bytes
    def send_and_receive(self, frame: bytes, timeout_override: float = None) -> bytes
    def is_connected(self) -> bool
```

**Protocolo de Frame:**
```
[STX][CID][FS][FIELD1][FS][FIELD2]...[ETX][LRC]
 02   Y19  1C   DATA    1C   DATA     03   XX

STX = 0x02 (Start of Text)
ETX = 0x03 (End of Text)  
FS  = 0x1C (Field Separator)
LRC = XOR de todos los bytes desde STX hasta ETX (inclusive)
```

**Manejo de Errores:**
- Timeout en lectura de STX
- Frames excesivamente largos (>8KB)
- Errores de puerto serie
- Validación LRC automática

### 2. Response Parser (`core/response_parser.py`)

**Responsabilidades:**
- Parsing dinámico basado en configuración JSON
- Decodificación de campos según tipo y contexto
- Manejo de formato EMV TLV con validación
- Post-procesamiento con RSA y enmascarado
- Parsing específico por comando (Y02, Y03, Y19)
- Manejo de errores Y0E con códigos descriptivos

**Decodificadores disponibles:**
```python
DECODERS = {
    'trim': 'Eliminar espacios en blanco',
    'hex': 'Convertir de hexadecimal a mayúsculas',
    'tlv_hex': 'Parser TLV desde hexadecimal',
    'hex_ascii_printable': 'Convertir hex a ASCII imprimible',
    'bankver': 'Separar código banco y versión',
    'bcd_digits': 'Convertir BCD a dígitos'
}
```

**Post-procesadores:**
```python
POST_PROCESSORS = {
    'rsa_decrypt': 'Desencriptar con RSA según padding configurado',
    'emv_pretty': 'Formatear TLV EMV con nombres descriptivos',
    'parse_track2': 'Parsear Track2 con validación Luhn',
    'parse_pan_field': 'Parsear PAN con enmascarado automático',
    'mask_pan': 'Enmascarar PAN (6 primeros + 4 últimos)',
    'parse_cau_field': 'Manejar campos CAU vacíos'
}
```

**Parsing Dinámico Y02:**
- Utiliza MDI del Y19 anterior para seleccionar campos
- Configuración específica por modo de ingreso
- Fallback a campos por defecto si no hay contexto

**Manejo de Errores Y0E:**
- Carga códigos de error desde `config/y0e_errors.json`
- Extrae comando origen y código de error
- Proporciona descripciones legibles

### 3. RSA Handler (`crypto/rsa_handler.py`)

**Responsabilidades:**
- Carga segura de claves RSA desde archivos .pem/.key
- Encriptación/desencriptación con múltiples paddings
- Validación de rutas y formatos de archivo
- Manejo seguro de memoria y errores
- Integración con `pycryptodome` para operaciones criptográficas

**Formatos de padding soportados:**
```python
PADDING_MODES = {
    'RAW-NoPadding': 'Sin padding, operación RSA directa',
    'PKCS1v15': 'PKCS#1 v1.5 padding (RFC 3447)',
    'OAEP-SHA1': 'OAEP padding con SHA-1 hash'
}
```

**Validaciones de Seguridad:**
- Prevención de path traversal
- Validación de extensiones de archivo
- Verificación de tamaño de datos
- Manejo de errores criptográficos
- Limpieza de datos sensibles

**Métodos principales:**
```python
class RSAHandler:
    def load_key_from_file(self, path: str) -> bool
    def get_key_params(self) -> Tuple[int, int, int]  # n, d, k
    def decrypt_raw(self, cipher_bytes: bytes) -> dict
    def decrypt_pkcs_or_oaep(self, cipher_bytes: bytes, padding: str) -> dict
    def decrypt_bytes(self, cipher_bytes: bytes, mode: str) -> dict
    def hex_to_bytes_safe(self, hex_str: str) -> bytes
```

### 4. Data Processor (`core/data_processor.py`)

**Responsabilidades:**
- Parsing de TLV EMV con validación de seguridad
- Formateo de campos según configuración
- Conversión de formatos (amount, BCD, hex)
- Validación de datos de entrada
- Prevención de ataques XSS y DoS

**Funciones principales:**
```python
class DataProcessor:
    @staticmethod
    def parse_tlv_hex(hex_ascii: str) -> dict
    
    @classmethod
    def emv_pretty(cls, tlv: dict) -> dict
    
    @staticmethod
    def mask_pan_value(pan: str) -> str
    
    @staticmethod
    def parse_track2_ascii(s: str) -> dict
    
    @staticmethod
    def luhn_check(pan: str) -> bool
```

**Tags EMV Soportados:**
```python
EMV_TAG_NAMES = {
    "9F02": "importe",
    "9F03": "cashback", 
    "9A": "fecha",
    "9C": "tipo_txn",
    "95": "TVR",
    "9F26": "ARQC",
    "9F27": "CVM_Result",
    "9F33": "Terminal_Capabilities",
    "84": "AID",
    "5F2A": "Moneda"
    # ... más tags
}
```

**Validaciones de Seguridad:**
- Sanitización de entrada con `html.escape()`
- Límite de tamaño para prevenir DoS (16KB)
- Límite de iteraciones en parsing TLV (1000)
- Límite de tags por estructura (256)
- Validación de bounds en arrays

## 🎨 Interfaz de Usuario

### Arquitectura UI

La interfaz utiliza **CustomTkinter** con tema oscuro y estructura modular compacta:

```
MainWindow (CTkScrollableFrame principal)
├── Header (Título y versión)
├── ConnectionPanel (Puerto serie, RSA, opciones)
├── CommandPanel (Selección, parámetros, acciones)
├── CommunicationPanel (Pestañas de logs)
│   ├── HEX Tab (Datos hexadecimales)
│   ├── JSON Tab (Respuestas parseadas con colores)
│   ├── Comandos Tab (Log de comandos JSON)
│   └── Log Tab (Log de aplicación)
└── StatusBar (Estado de conexión y aplicación)
```

### Características de UI

#### **Scroll Unificado**
- Sistema de scroll global que se propaga a todos los componentes
- Fallback inteligente cuando un componente no puede hacer scroll
- Soporte para mouse wheel y botones 4/5

#### **Paneles Dinámicos**
- **ConnectionPanel**: Una sola fila compacta con todos los controles
- **CommandPanel**: Formularios generados dinámicamente desde JSON
- **CommunicationPanel**: Pestañas con colores de sintaxis JSON

#### **Colores de Sintaxis JSON**
```python
JSON_COLORS = {
    "key": "#9CDCFE",      # Azul claro para claves
    "string": "#CE9178",   # Naranja para strings
    "number": "#B5CEA8",   # Verde para números
    "bool": "#569CD6",     # Azul para booleanos
    "null": "#569CD6",     # Azul para null
    "punct": "#D4D4D4"     # Gris claro para puntuación
}
```

#### **Menús Contextuales**
- Click derecho en paneles JSON para copiar/limpiar
- Atajos de teclado: Ctrl+H (compactar), Ctrl+Shift+H (limpiar)
- Botones de acción en cada pestaña

#### **Tooltips Informativos**
- Tooltips en botones con descripciones de funcionalidad
- Información contextual sobre parámetros
- Ayuda integrada en la interfaz

## 📊 Sistema de Configuración

### Archivos de Configuración

Todos los archivos de configuración están en el directorio `/config` en formato JSON:

#### **commands.json** - Definición de Comandos
```json
{
  "stx": 2,
  "etx": 3, 
  "fs": 28,
  "commands": {
    "Y19 Transacción": {
      "cid": "Y19",
      "description": "💳 Transacción (Y19) — RSA/EXP",
      "request": {
        "fields": [
          {
            "name": "RSA",
            "description": "🔑 Clave pública RSA en hexadecimal",
            "default": "B110F42E...",
            "format": {"type": "upper"}
          }
        ]
      },
      "response": {
        "validate_cid": true,
        "parser": {
          "type": "fs",
          "fields": [...]
        }
      },
      "io": {
        "expect_ack": true,
        "timeout_sec": 45
      }
    }
  }
}
```

#### **emv_tags.json** - Tags EMV Estándar
```json
{
  "9F02": {
    "name": "Amount, Authorised",
    "description": "Importe autorizado de la transacción",
    "format": "numeric",
    "length": "6"
  },
  "9F26": {
    "name": "Application Cryptogram", 
    "description": "Criptograma de aplicación (ARQC/TC/AAC)",
    "format": "binary",
    "length": "8"
  }
}
```

#### **field_decoders.json** - Decodificadores de Campo
```json
{
  "decoders": {
    "bankver": {
      "description": "Separar código de banco y versión",
      "fields": {
        "bank_code": {"name": "COD_BANCO", "length": 6},
        "version": {"name": "VERSION_PP", "trim": true}
      }
    },
    "hex_ascii_printable": {
      "description": "Convertir hex a ASCII imprimible",
      "char_range": {"min": 32, "max": 126}
    }
  },
  "post_processors": {
    "parse_track2": {
      "regex": "([0-9]{12,19})(?:=|D)([0-9]{2})([0-9]{2})([0-9]{3})?([0-9]*)",
      "fields": ["pan", "exp_yy", "exp_mm", "service_code", "discretionary"],
      "pan_mask": {
        "min_length": 10,
        "show_first": 6,
        "show_last": 4,
        "mask_char": "*"
      }
    }
  }
}
```

#### **response_parsers.json** - Parsers Personalizados
```json
{
  "parsers": {
    "parse_ctls_data": {
      "description": "Parser para datos CTLS",
      "fields": [
        {
          "name": "track2_encrypted",
          "start": 0,
          "length": 256,
          "post_process": "rsa_decrypt"
        }
      ]
    }
  }
}
```

#### **validation_rules.json** - Reglas de Validación
```json
{
  "validation": {
    "cid_validation": {
      "error_command": "Y0E",
      "special_cases": {
        "Y19_variants": {
          "pattern": "Y19*",
          "accept_as": "Y19"
        }
      },
      "error_fields": {
        "command": {"start": 0, "length": 3},
        "error_code": {"start": 3, "length": 2}
      }
    }
  },
  "parsing": {
    "default_parser": {
      "type": "fs",
      "fields": []
    },
    "field_naming": {
      "default_prefix": "FIELD_",
      "index_start": 1
    }
  }
}
```

#### **y0e_errors.json** - Códigos de Error
```json
{
  "00": "Operación exitosa",
  "01": "Error de comunicación",
  "02": "Timeout de operación",
  "FF": "Error desconocido"
}
```

## 🔐 Seguridad y Criptografía

### Manejo de Datos Sensibles

#### **Enmascaramiento Automático de PAN**
```python
def mask_pan_value(pan: str) -> str:
    """Enmascara PAN mostrando primeros 6 y últimos 4 dígitos"""
    pan = re.sub(r'[^0-9]', '', pan or '')
    if len(pan) < 10:
        return pan
    return pan[:6] + '*' * (len(pan)-10) + pan[-4:]
```

**Configuración de Enmascarado:**
- Checkbox "🔒 Enmascarar" en panel de conexión
- Aplicado automáticamente a PAN, Track1, Track2
- Remueve campos sensibles de logs cuando está habilitado
- Configuración persistente por sesión

#### **Validación de Archivos RSA**
```python
def _validate_path(self, path: str) -> str:
    """Validar ruta para prevenir path traversal"""
    abs_path = os.path.abspath(os.path.normpath(path))
    
    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {path}")
    
    if not abs_path.lower().endswith(('.pem', '.key')):
        raise ValueError("Only .pem and .key files allowed")
    
    if ".." in path or "\\\\" in path:
        raise ValueError(f"Potentially unsafe path: {path}")
    
    return abs_path
```

#### **Sanitización de Entrada**
```python
# En DataProcessor.parse_tlv_hex()
safe_hex = html.escape(hex_ascii)  # Prevenir XSS
hs = re.sub(r"[^0-9A-Fa-f]", "", safe_hex)  # Solo hex válido

if len(hs) > 16384:  # Límite DoS
    return {"_raw": safe_hex, "_error": "Data too large"}
```

### Operaciones Criptográficas

#### **Modos de Padding RSA**
```python
class RSAHandler:
    def decrypt_bytes(self, cipher_bytes: bytes, mode: str) -> dict:
        if mode == "RAW-NoPadding":
            return self.decrypt_raw(cipher_bytes)
        elif mode in ["PKCS1v15", "OAEP-SHA1"]:
            return self.decrypt_pkcs_or_oaep(cipher_bytes, mode)
```

**RAW-NoPadding:**
- Operación RSA directa: `m = c^d mod n`
- Para datos de longitud exacta de clave
- Usado en protocolos PinPad específicos

**PKCS1v15:**
- Padding estándar PKCS#1 v1.5
- Compatible con la mayoría de implementaciones
- Manejo de errores con sentinel

**OAEP-SHA1:**
- Padding OAEP con hash SHA-1
- Mayor seguridad criptográfica
- Recomendado para nuevas implementaciones

#### **Integración con Parsing**
```python
def _decrypt_rsa_blob(self, hex_str: str) -> dict:
    """Desencriptar blob RSA con contexto de aplicación"""
    # Validar tamaño vs clave
    key_bytes = (self.app.rsa.private_key.size_in_bits() + 7) // 8
    mode = self.app.rsa_padding.get()
    
    # Intentar desencriptación directa
    if len(hex_str) == key_bytes * 2:
        return self.app.rsa.decrypt_bytes(bytes.fromhex(hex_str), mode)
    
    # Buscar en sub-campos TLV
    tlv = self.processor.parse_tlv_hex(hex_str)
    candidates = {}
    for tag, valhex in tlv.items():
        if len(valhex) == key_bytes * 2:
            candidates[tag] = self.app.rsa.decrypt_bytes(
                bytes.fromhex(valhex), mode
            )
    
    return {"candidates": candidates} if candidates else {"error": "No valid cipher found"}
```

## 📡 Protocolo de Comunicación

### Estructura de Frame

```
Byte    Field       Description                 Example
0       STX         Start of Text (0x02)       02
1-3     CID         Command ID (3 chars)       Y19
4       FS          Field Separator (0x1C)     1C
5-N     PAYLOAD     Command data fields        RSA_KEY1CEXP1CIMP...
N+1     ETX         End of Text (0x03)         03
N+2     LRC         XOR checksum               4A
```

### Implementación del Protocolo

#### **FrameCodec** (`protocol.py`)
```python
class FrameCodec:
    def __init__(self, stx=0x02, etx=0x03, fs=0x1C):
        self.stx = stx
        self.etx = etx  
        self.fs = fs
    
    def build_frame(self, cid: str, fields: List[str]) -> bytes:
        """Construir frame con CID y campos"""
        body = cid.encode('ascii')
        if fields:
            joined = bytes([self.fs]).join(
                [str(f).encode('ascii', errors='ignore') for f in fields]
            )
            body += joined
        body += bytes([self.etx])
        lrc_val = self.lrc(body)
        return bytes([self.stx]) + body + bytes([lrc_val])
    
    @staticmethod
    def lrc(data: bytes) -> int:
        """Calcular LRC (XOR de todos los bytes)"""
        x = 0
        for b in data:
            x ^= b
        return x & 0xFF
    
    def validate_lrc(self, frame: bytes) -> bool:
        """Validar LRC del frame recibido"""
        if not frame or len(frame) < 4:
            return False
        calc = self.lrc(frame[1:-1])
        return calc == frame[-1]
    
    def extract(self, frame: bytes) -> Tuple[str, bytes]:
        """Extraer CID y payload del frame"""
        if not self.validate_lrc(frame):
            raise ValueError("LRC inválido")
        if frame[0] != self.stx or frame[-2] != self.etx:
            raise ValueError("STX/ETX inválido")
        
        inner = frame[1:-2]
        cid = inner[:3].decode('ascii', errors='replace')
        payload = inner[3:]
        return cid, payload
```

#### **FSParser** - Parser de Campos
```python
class FSParser:
    def __init__(self, fs=0x1C):
        self.fs = fs
    
    def parse(self, payload: bytes) -> List[str]:
        """Parsear payload en campos separados por FS"""
        parts = payload.split(bytes([self.fs])) if payload else [b'']
        out = [p.decode('ascii', errors='ignore') for p in parts]
        if out and out[0] == '':
            out = out[1:]  # Remover campo vacío inicial
        return out
```

### Manejo de Comunicación

#### **Lectura de Frame con Timeout**
```python
def read_frame(self, timeout_override=None):
    """Leer frame completo con manejo de timeout"""
    tout = float(timeout_override or self.ser.timeout or 5.0)
    t0 = time.time()
    
    # Buscar STX
    stx_found = False
    while time.time() - t0 < tout:
        b = self.ser.read(1)
        if b == bytes([self.codec.stx]):
            stx_found = True
            break
    
    if not stx_found:
        return None
    
    # Leer hasta ETX+LRC
    buf = bytearray([self.codec.stx])
    while time.time() - t0 < tout * 3:
        b = self.ser.read(1)
        if not b:
            continue
        buf += b
        if b == bytes([self.codec.etx]):
            lrc = self.ser.read(1)
            if lrc:
                buf += lrc
                return bytes(buf)
        
        # Prevenir frames excesivamente largos
        if len(buf) > 8192:
            return None
    
    return None
```

### Estados y Manejo de Errores

#### **Estados de Conexión**
```python
CONNECTION_STATES = {
    "disconnected": "❌ Desconectado",
    "connecting": "🔄 Conectando...",
    "connected": "✅ Conectado",
    "sending": "📤 Enviando...",
    "receiving": "📥 Recibiendo...",
    "error": "⚠️ Error"
}
```

#### **Manejo de Errores**
- **Timeout**: Reintentos automáticos con backoff
- **LRC inválido**: Rechazo de frame y solicitud de reenvío
- **Desconexión**: Detección automática y reconexión
- **Buffer overflow**: Protección contra frames maliciosos
- **Encoding errors**: Manejo graceful con reemplazo de caracteres

## 📊 Sistema de Logging

### AppLogger (`core/logger.py`)

Sistema de logging avanzado con múltiples paneles y colores de sintaxis:

#### **Tipos de Log**
```python
class AppLogger:
    def log_hex(self, direction: str, data: bytes):
        """Log de datos hexadecimales con timestamps"""
    
    def log_text(self, text: str):
        """Log de mensajes de texto"""
    
    def log_parsed(self, obj: dict):
        """Log de objetos parseados con colores JSON"""
    
    def log_app(self, message: str, level: str = "INFO"):
        """Log de mensajes de aplicación"""
    
    def log_command_json(self, command_id: str, command_config: dict, 
                        parameters: dict, frame_hex: str):
        """Log estructurado de comandos enviados"""
```

#### **Gestión de Historial**
```python
# Compactación automática
def _compact_if_needed(self, text_widget):
    lines = int(text_widget.index('end-1c').split('.')[0])
    if lines > self.max_lines:  # 1000 líneas por defecto
        keep_lines = 500
        # Mantener solo las últimas 500 líneas
        text_widget.delete('1.0', f'{lines - keep_lines + 1}.0')

# Compactación manual
def compact_history(self):  # Ctrl+H
    """Compactar todos los paneles de log"""

def clear_history(self):    # Ctrl+Shift+H
    """Limpiar completamente el historial"""
```

#### **Log de Comandos JSON**
Registro estructurado de cada comando enviado:

```json
{
  "timestamp": "2024-10-24T10:30:15.123456",
  "command_id": "Y19 Transacción",
  "command_info": {
    "cid": "Y19",
    "description": "💳 Transacción (Y19) — RSA/EXP",
    "timeout_sec": 45
  },
  "parameters": {
    "RSA": {
      "value": "B110F42EDD15B735...",
      "description": "🔑 Clave pública RSA en hexadecimal"
    },
    "EXP": {
      "value": "10001",
      "description": "🔢 Exponente RSA (típicamente 65537)"
    }
  },
  "frame": {
    "hex": "02 59 31 39 B1 10 F4...",
    "length": 256
  }
}
```

## 🧪 Testing y Debugging

### Herramientas de Debug Integradas

#### **Visualización Hexadecimal**
```python
def hexlify(b: bytes) -> str:
    """Formatear bytes como hex espaciado"""
    return ' '.join(f'{x:02X}' for x in b)

def unhexlify(s: str) -> bytes:
    """Convertir hex espaciado a bytes"""
    s = s.replace(' ', '').replace('\n', '').replace('\t', '')
    return binascii.unhexlify(s)
```

#### **Análisis de Protocolo**
```python
class FrameCodec:
    def validate_lrc(self, frame: bytes) -> bool:
        """Validar integridad del frame"""
        if not frame or len(frame) < 4:
            return False
        calc = self.lrc(frame[1:-1])
        received = frame[-1]
        return calc == received
    
    def extract(self, frame: bytes) -> Tuple[str, bytes]:
        """Extraer y validar componentes del frame"""
        if not self.validate_lrc(frame):
            raise ValueError("LRC inválido")
        if frame[0] != self.stx:
            raise ValueError("STX inválido")
        if frame[-2] != self.etx:
            raise ValueError("ETX inválido")
        # ... extracción segura
```

#### **Logging de Desarrollo**
```python
# En security_config.py
def setup_security():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/pinpad_commander_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
```

### Manejo de Errores

#### **Excepciones Personalizadas**
```python
# En communication.py
try:
    self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
except serial.SerialException as e:
    logging.error(f"Serial connection error: {e}")
    raise serial.SerialException(f"Failed to connect to {port}: {e}")
except Exception as e:
    logging.error(f"Unexpected connection error: {e}")
    raise RuntimeError(f"Connection failed: {e}")
```

#### **Validación de Entrada**
```python
# En rsa_handler.py
def _validate_path(self, path):
    try:
        abs_path = os.path.abspath(os.path.normpath(path))
        if not os.path.isfile(abs_path):
            raise ValueError(f"File not found: {path}")
        if not abs_path.lower().endswith(('.pem', '.key')):
            raise ValueError("Only .pem and .key files allowed")
        return abs_path
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid file path: {e}")
```

## 🔧 Extensibilidad

### Agregar Nuevos Comandos

1. **Definir en `config/commands.json`**:
```json
{
  "Y99 Nuevo Comando": {
    "cid": "Y99",
    "description": "🆕 Nuevo comando personalizado",
    "request": {
      "fields": [
        {
          "name": "PARAM1",
          "description": "Parámetro personalizado",
          "default": "valor_default"
        }
      ]
    },
    "response": {
      "parser": {
        "type": "fs",
        "fields": [
          {
            "name": "resultado",
            "description": "Resultado del comando",
            "decode": "trim"
          }
        ]
      }
    }
  }
}
```

2. **Agregar parser personalizado** (opcional):
```python
# En response_parser.py
def _parse_y99_custom(self, value):
    """Parser específico para Y99"""
    return {
        "processed_value": value.upper(),
        "timestamp": datetime.now().isoformat()
    }
```

### Agregar Nuevos Decodificadores

1. **Definir en `config/field_decoders.json`**:
```json
{
  "decoders": {
    "custom_decoder": {
      "description": "Decodificador personalizado",
      "format": "custom",
      "parameters": {
        "separator": "|",
        "fields": ["field1", "field2"]
      }
    }
  }
}
```

2. **Implementar en `ResponseParser`**:
```python
# En _process_field_spec()
elif decode == "custom_decoder":
    decoder_config = self.field_decoders["decoders"][decode]
    separator = decoder_config["parameters"]["separator"]
    fields = decoder_config["parameters"]["fields"]
    parts = val.split(separator)
    out_val = {field: parts[i] if i < len(parts) else "" 
               for i, field in enumerate(fields)}
```

---

**Desarrollado por**: Matias Rodriguez Alemany  
**Versión**: 1.4.0  
**Última actualización**: Octubre 2024  
**Tecnologías**: Python 3.8+, CustomTkinter, PySerial, PyCryptodomex': frame.hex().upper()
        }
```

## 🚀 Optimización y Performance

### Caching de Configuración

```python
class ConfigCache:
    """Cache LRU para configuraciones frecuentemente accedidas"""
    
    def __init__(self, max_size: int = 128):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
```

### Pool de Conexiones

```python
class ConnectionPool:
    """Pool de conexiones serie para múltiples dispositivos"""
    
    def __init__(self, max_connections: int = 5):
        self.connections = {}
        self.max_connections = max_connections
    
    def get_connection(self, port: str) -> SerialCommunication:
        if port not in self.connections:
            if len(self.connections) >= self.max_connections:
                self._cleanup_oldest_connection()
            self.connections[port] = SerialCommunication()
        return self.connections[port]
```

### Async Processing

```python
import asyncio

class AsyncCommandProcessor:
    """Procesador asíncrono de comandos"""
    
    async def process_command_async(self, command: str, params: dict) -> dict:
        """Procesa comando de forma asíncrona"""
        loop = asyncio.get_event_loop()
        
        # Ejecutar en thread pool para operaciones bloqueantes
        result = await loop.run_in_executor(
            None, 
            self._process_command_sync, 
            command, 
            params
        )
        
        return result
```

## 📈 Monitoreo y Métricas

### Sistema de Métricas

```python
class MetricsCollector:
    """Recolector de métricas de rendimiento"""
    
    def __init__(self):
        self.metrics = {
            'commands_sent': 0,
            'commands_successful': 0,
            'commands_failed': 0,
            'avg_response_time': 0.0,
            'connection_errors': 0
        }
    
    def record_command(self, command: str, success: bool, response_time: float):
        self.metrics['commands_sent'] += 1
        if success:
            self.metrics['commands_successful'] += 1
        else:
            self.metrics['commands_failed'] += 1
        
        # Actualizar tiempo promedio de respuesta
        self._update_avg_response_time(response_time)
```

### Health Check

```python
class HealthChecker:
    """Verificador de salud del sistema"""
    
    def check_system_health(self) -> dict:
        return {
            'serial_connection': self._check_serial_connection(),
            'rsa_keys_loaded': self._check_rsa_keys(),
            'config_valid': self._check_configuration(),
            'memory_usage': self._get_memory_usage(),
            'disk_space': self._get_disk_space()
        }
```

## 🔧 Extensibilidad

### Plugin System

```python
class PluginManager:
    """Gestor de plugins para extensibilidad"""
    
    def __init__(self):
        self.plugins = {}
        self.hooks = {}
    
    def register_plugin(self, name: str, plugin: 'Plugin'):
        self.plugins[name] = plugin
        plugin.initialize(self)
    
    def execute_hook(self, hook_name: str, *args, **kwargs):
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                callback(*args, **kwargs)
```

### Custom Decoders

```python
class CustomDecoder:
    """Base para decodificadores personalizados"""
    
    def decode(self, data: str) -> Any:
        raise NotImplementedError
    
    def validate(self, data: str) -> bool:
        raise NotImplementedError

class BankSpecificDecoder(CustomDecoder):
    """Decodificador específico para banco"""
    
    def decode(self, data: str) -> dict:
        # Lógica específica del banco
        return parsed_data
```

## 📚 Referencias y Estándares

### Estándares EMV

- **EMV 4.3**: Especificación de tarjetas con chip
- **ISO 8583**: Formato de mensajes financieros
- **ISO 7816**: Tarjetas de identificación con circuitos integrados

### Protocolos de Comunicación

- **RS-232**: Estándar de comunicación serie
- **ASCII**: Codificación de caracteres
- **LRC**: Longitudinal Redundancy Check

### Criptografía

- **RSA**: Rivest-Shamir-Adleman
- **PKCS#1**: Public-Key Cryptography Standards
- **OAEP**: Optimal Asymmetric Encryption Padding

---

Esta documentación técnica proporciona una visión detallada de la arquitectura, implementación y extensibilidad del sistema PinPad Commander.
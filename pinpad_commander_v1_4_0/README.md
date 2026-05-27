# PinPad Commander v1.4.0

## 📋 Descripción General

**PinPad Commander** es una aplicación de escritorio desarrollada en Python que permite la comunicación y control de dispositivos PinPad mediante protocolo serial. La aplicación está diseñada para facilitar el testing, debugging y operación de terminales de punto de venta (POS) que manejan transacciones con tarjetas de crédito y débito.

### 🎯 Características Principales

- **Comunicación Serial**: Interfaz completa para conectar y comunicarse con dispositivos PinPad
- **Múltiples Comandos**: Soporte para comandos Y02, Y03, Y06, Y0I, Y19, Y0P, Y77, Y0Q, Y26, Y0C
- **Criptografía RSA**: Manejo de claves públicas/privadas para encriptación de datos sensibles
- **Parser Inteligente**: Análisis automático de respuestas con formato EMV TLV
- **Interfaz Gráfica**: UI moderna desarrollada con CustomTkinter
- **Logging Avanzado**: Sistema de registro detallado con rotación de archivos
- **Log de Comandos JSON**: Registro estructurado de comandos enviados con parámetros y descripciones
- **Configuración Flexible**: Archivos JSON para personalizar comandos y parsers

## 🏗️ Arquitectura del Proyecto

### Estructura de Directorios

```
pinpad_commander_v1_4_0/
├── app_modular_refactored.py      # Aplicación principal
├── protocol.py                    # Protocolo de comunicación
├── security_config.py             # Configuración de seguridad
├── requirements.txt               # Dependencias Python
├── install.bat                    # Script de instalación
├── run_PPCommander.bat           # Script de ejecución
├── config/                       # Archivos de configuración
│   ├── commands.json             # Definición de comandos
│   ├── emv_tags.json            # Tags EMV estándar
│   ├── field_decoders.json      # Decodificadores de campos
│   ├── response_parsers.json    # Parsers de respuestas
│   ├── validation_rules.json    # Reglas de validación
│   └── y0e_errors.json          # Códigos de error
├── core/                        # Módulos principales
│   ├── communication.py         # Comunicación serial
│   ├── command_handler.py       # Manejo de comandos
│   ├── data_processor.py        # Procesamiento de datos
│   ├── response_parser.py       # Parser de respuestas
│   ├── logger.py               # Sistema de logging
│   ├── config_manager.py       # Gestión de configuración
│   ├── serial_manager.py       # Gestión de puerto serial
│   ├── rsa_manager.py          # Gestión RSA
│   ├── ui_manager.py           # Gestión de UI
│   ├── emv_manager.py          # Gestión EMV
│   └── event_manager.py        # Gestión de eventos
├── crypto/                     # Módulos de criptografía
│   └── rsa_handler.py         # Manejo de RSA
├── ui/                        # Interfaz de usuario
│   ├── main_window.py         # Ventana principal
│   └── tooltip.py             # Tooltips
├── logs/                      # Archivos de log
└── patches/                   # Parches de compatibilidad
    ├── y19_autopem_patch.py   # Patch Y19 AutoPEM
    └── ui_logpanel_patch.py   # Patch panel de logs
```

### 🔧 Componentes Principales

#### 1. **Aplicación Principal** (`app_modular_refactored.py`)
- Clase `PinPadCommanderModular`: Coordinador principal de la aplicación
- Inicialización de todos los componentes
- Gestión del ciclo de vida de la aplicación
- Delegación de responsabilidades a gestores especializados

#### 2. **Comunicación Serial** (`core/communication.py`)
- Manejo de conexiones serie
- Envío y recepción de datos
- Control de timeouts y reconexiones
- Validación de frames con LRC

#### 3. **Criptografía RSA** (`crypto/rsa_handler.py`)
- Carga de claves públicas/privadas
- Encriptación/desencriptación de datos sensibles
- Soporte para múltiples formatos de padding
- Validación de claves

#### 4. **Parser de Respuestas** (`core/response_parser.py`)
- Análisis automático de respuestas del PinPad
- Decodificación de campos según configuración
- Soporte para formato EMV TLV
- Parsing dinámico basado en modo de ingreso

#### 5. **Interfaz Gráfica** (`ui/main_window.py`)
- UI moderna con CustomTkinter
- Paneles organizados por funcionalidad
- Formularios dinámicos para parámetros
- Visualización de logs en tiempo real
- Panel dedicado para comandos JSON con colores de sintaxis

#### 6. **Logger de Comandos** (`core/logger.py`)
- Registro estructurado de comandos enviados en formato JSON
- Incluye parámetros con valores y descripciones extraidas de commands.json
- Información completa del frame hexadecimal y metadatos
- Timestamps y configuración del comando

## 🚀 Instalación y Configuración

### Requisitos del Sistema

- **Python 3.8+**
- **Windows 10/11** (recomendado)
- **Puerto Serial** disponible para conexión con PinPad

### Dependencias

```bash
# Instalar dependencias
pip install -r requirements.txt
```

**Dependencias principales:**
- `customtkinter>=5.2.0` - Framework de UI moderna
- `pycryptodome>=3.19.0` - Criptografía RSA
- `pyserial>=3.5` - Comunicación serial

### Instalación Rápida

1. **Clonar/Descargar** el proyecto
2. **Ejecutar** `install.bat` (instala dependencias automáticamente)
3. **Ejecutar** `run_PPCommander.bat` para iniciar la aplicación

### Instalación Manual

```bash
# Navegar al directorio del proyecto
cd pinpad_commander_v1_4_0

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app_modular_refactored.py
```

## 📖 Guía de Uso

### 1. **Conexión al PinPad**

1. **Conectar** el dispositivo PinPad al puerto serial
2. **Seleccionar** el puerto COM correcto en la aplicación
3. **Hacer clic** en "Conectar" para establecer la conexión
4. **Verificar** el estado de conexión en la barra de estado

### 2. **Comandos Disponibles**

#### **Y0I - Información del Dispositivo**
- **Propósito**: Obtener información básica del PinPad
- **Parámetros**: Ninguno
- **Respuesta**: Propietario, fabricante, modelo, versiones, número de serie

#### **Y19 - Transacción Completa**
- **Propósito**: Ejecutar transacción completa con RSA
- **Parámetros**: Clave RSA, exponente, importes, configuraciones
- **Respuesta**: Datos de tarjeta, criptogramas EMV, PIN encriptado

#### **Y02 - Lectura de Tarjeta**
- **Propósito**: Leer tarjeta por banda magnética, chip o manual
- **Parámetros**: Flags de configuración, importes
- **Respuesta**: Datos de tarjeta según modo de ingreso

#### **Y03 - Confirmación EMV**
- **Propósito**: Confirmar transacción EMV con códigos de autorización
- **Parámetros**: Código de autorización, código de respuesta
- **Respuesta**: Confirmación de procesamiento

#### **Y06 - Cancelación**
- **Propósito**: Cancelar operación en curso
- **Parámetros**: Timeout
- **Respuesta**: Estado de cancelación

#### **Y0P - Impresión de Ticket**
- **Propósito**: Imprimir comprobante de transacción
- **Parámetros**: Datos del comercio, transacción, configuraciones
- **Respuesta**: Confirmación de impresión

### 3. **Configuración RSA**

1. **Cargar Clave Privada**: Para desencriptar respuestas
2. **Cargar Clave Pública**: Para enviar en comandos Y19
3. **Seleccionar Padding**: RAW-NoPadding, PKCS1, OAEP

### 4. **Análisis de Respuestas**

- **Panel Hex**: Muestra datos en formato hexadecimal
- **Panel JSON**: Muestra datos interpretados y decodificados
- **Panel Comandos**: Log estructurado de comandos enviados con parámetros y descripciones
- **Panel Logs**: Historial completo de comunicación

### 5. **Panel de Comandos JSON**

El panel de comandos JSON registra automáticamente cada comando enviado con información detallada:

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
    },
    "IMP": {
      "value": "000000012345",
      "description": "💰 Importe de la transacción"
    }
  },
  "frame": {
    "hex": "02 59 31 39 B1 10 F4...",
    "length": 256
  }
}
```

**Funcionalidades del Panel:**
- **Colores de sintaxis** para mejor legibilidad del JSON
- **Menú contextual** con opciones de copiar y limpiar
- **Compactación automática** cuando excede el límite de líneas
- **Scroll unificado** integrado con el sistema existente

## ⚙️ Configuración Avanzada

### Archivos de Configuración

#### **commands.json**
Define la estructura de comandos, parámetros y parsers:

```json
{
  "commands": {
    "Y19 Transacción": {
      "cid": "Y19",
      "description": "💳 Transacción (Y19) — RSA/EXP",
      "request": {
        "fields": [...],
        "segments": [...]
      },
      "response": {
        "parser": {...}
      }
    }
  }
}
```

#### **emv_tags.json**
Diccionario de tags EMV estándar para interpretación:

```json
{
  "9F02": {
    "name": "Amount, Authorised",
    "description": "Importe autorizado de la transacción"
  }
}
```

#### **field_decoders.json**
Decodificadores personalizados para campos específicos:

```json
{
  "trim": "Eliminar espacios en blanco",
  "hex": "Convertir de hexadecimal",
  "tlv_hex": "Parser TLV desde hexadecimal"
}
```

### Variables de Entorno

```bash
# Configuración de logging
PINPAD_LOG_LEVEL=INFO
PINPAD_LOG_DIR=./logs

# Configuración de comunicación
PINPAD_DEFAULT_PORT=COM3
PINPAD_DEFAULT_BAUDRATE=115200
```

## 🔐 Seguridad

### Manejo de Datos Sensibles

- **Encriptación RSA**: Todos los datos sensibles se manejan encriptados
- **Masking PAN**: Números de tarjeta se enmascaran automáticamente
- **Logs Seguros**: Datos sensibles no se registran en logs
- **Claves Privadas**: Se cargan desde archivos externos, no embebidas

### Configuración de Seguridad

El archivo `security_config.py` establece:
- Configuración de logging seguro
- Validación de entrada de datos
- Manejo seguro de excepciones
- Limpieza de memoria para datos sensibles

## 🐛 Troubleshooting

### Problemas Comunes

#### **Error de Conexión Serial**
```
Error: No se puede abrir el puerto COM3
```
**Solución**:
1. Verificar que el dispositivo esté conectado
2. Comprobar que el puerto no esté en uso por otra aplicación
3. Verificar permisos de usuario para acceso a puertos serie

#### **Error de RSA**
```
Error: No se puede desencriptar los datos
```
**Solución**:
1. Verificar que la clave privada sea correcta
2. Comprobar el formato de padding seleccionado
3. Validar que la clave pública enviada coincida con la privada

#### **Error de Parsing**
```
Error: No se puede parsear la respuesta
```
**Solución**:
1. Verificar la configuración del parser en commands.json
2. Comprobar que la respuesta tenga el formato esperado
3. Revisar los logs para identificar el punto de falla

### Logs de Debug

Los logs se almacenan en `logs/pinpad_commander_YYYYMMDD.log`:

```
2024-01-15 10:30:15 INFO - Connecting to COM3
2024-01-15 10:30:15 DEBUG - Sending: 02 59 30 49 03 4A
2024-01-15 10:30:16 DEBUG - Received: 02 59 30 49 1C ...
2024-01-15 10:30:16 INFO - Command Y0I completed successfully
```

### Panel de Comandos JSON

Además de los logs tradicionales, la aplicación incluye un panel dedicado que muestra cada comando enviado en formato JSON estructurado, incluyendo:

- **Timestamp** del envío
- **Información del comando** (CID, descripción, timeout)
- **Parámetros** con valores y descripciones extraidas de commands.json
- **Frame hexadecimal** completo con longitud
- **Colores de sintaxis** para mejor visualización

## 🔄 Desarrollo y Extensión

### Agregar Nuevos Comandos

1. **Definir en commands.json**:
```json
{
  "Y99 Nuevo Comando": {
    "cid": "Y99",
    "description": "Descripción del comando",
    "request": {
      "fields": [...]
    },
    "response": {
      "parser": {...}
    }
  }
}
```

2. **Implementar parser personalizado** (si es necesario):
```python
def parse_y99_response(self, data):
    # Lógica de parsing específica
    return parsed_data
```

### Agregar Nuevos Decodificadores

En `field_decoders.json`:
```json
{
  "custom_decoder": {
    "description": "Decodificador personalizado",
    "function": "custom_decode_function"
  }
}
```

### Testing

```bash
# Ejecutar tests unitarios
python -m pytest tests/

# Test de comunicación
python -m pytest tests/test_communication.py

# Test de parsing
python -m pytest tests/test_parser.py
```

## 📊 Monitoreo y Métricas

### Métricas de Rendimiento

- **Tiempo de respuesta** promedio por comando
- **Tasa de éxito** de transacciones
- **Errores de comunicación** por sesión
- **Uso de memoria** y CPU

### Alertas y Notificaciones

- Desconexión inesperada del dispositivo
- Errores de validación LRC
- Timeouts de comunicación
- Errores de desencriptación RSA

## 🤝 Contribución

### Guías de Contribución

1. **Fork** del repositorio
2. **Crear** branch para nueva funcionalidad
3. **Implementar** cambios con tests
4. **Documentar** nuevas funcionalidades
5. **Enviar** Pull Request

### Estándares de Código

- **PEP 8** para estilo de Python
- **Type hints** para funciones públicas
- **Docstrings** para módulos y clases
- **Tests unitarios** para nueva funcionalidad


## 📞 Soporte

Para soporte técnico o reportar bugs:

- **Email**: merodriguez@payway.com.ar
- **Issues**: GitHub Issues del proyecto
- **Documentación**: Wiki del proyecto

---

**Desarrollado por**: Matias Rodriguez Alemany 
**Versión**: 1.4.0  
**Última actualización**: Octubre 2024
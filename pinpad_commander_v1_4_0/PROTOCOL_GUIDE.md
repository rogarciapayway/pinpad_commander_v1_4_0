# 📋 Guía de Protocolo PinPad - Comandos Hexadecimales

## 🎯 Introducción

Esta guía explica cómo construir y revisar comandos hexadecimales para dispositivos PinPad. Los comandos siguen un protocolo específico con estructura de frames, validación LRC y campos definidos.

## 🏗️ Estructura General de Comandos

### Frame Básico
```
STX + CID + DATOS + ETX + LRC
```

- **STX**: `02` (Start of Text)
- **CID**: Código de comando (3 caracteres ASCII)
- **DATOS**: Parámetros del comando separados por FS (`1C`)
- **ETX**: `03` (End of Text)
- **LRC**: Checksum de validación (XOR de todos los bytes)

### Separadores
- **FS (Field Separator)**: `1C` - Separa campos principales
- **US (Unit Separator)**: `1F` - Separa subcampos

## 📡 Comandos Principales

### Y0I - Información del Dispositivo

**Propósito**: Obtener información básica del PinPad

**Estructura**:
```
02 59 30 49 03 4A
```

**Desglose**:
- `02`: STX
- `59 30 49`: "Y0I" en ASCII
- `03`: ETX
- `4A`: LRC

**Sin parámetros adicionales**

---

### Y19 - Transacción Completa con RSA

**Propósito**: Ejecutar transacción completa con criptografía RSA

**Estructura**:
```
02 59 31 39 [RSA_KEY] 1C [EXP] 1C [IMP] 1C [ICB] 1C [FLAGS] 03 [LRC]
```

**Parámetros**:
1. **RSA**: Clave pública RSA (512 bytes en hexadecimal)
2. **EXP**: Exponente RSA (típicamente `10001`)
3. **IMP**: Importe (12 dígitos BCD, ej: `000000012345` = $123.45)
4. **ICB**: Importe cashback (12 dígitos BCD)
5. **FLAGS**: Configuraciones adicionales

**Ejemplo**:
```
02 59 31 39 B110F42EDD15B735... 1C 10001 1C 000000012345 1C 000000000000 1C 0 03 XX
```

---

### Y02 - Lectura de Tarjeta

**Propósito**: Leer tarjeta por banda magnética, chip o entrada manual

**Estructura**:
```
02 59 30 32 [U4D][CDS][ET1][SPI][PTC][PMK][WRK] 1C [ENC][IMP][ICB] 03 [LRC]
```

**Parámetros**:
1. **U4D**: Últimos 4 dígitos (0=No, 1=Sí)
2. **CDS**: Código de seguridad (0=No, 1=Sí)
3. **ET1**: Enviar Track 1 (0=No, 1=Sí)
4. **SPI**: Solicitar PIN (0=No, 1=Sí)
5. **PTC**: Pedir tipo de cuenta (0=No, 1=Sí)
6. **PMK**: Posición Master Key (1=Test, 2=Prod Lane, G=Prod N910)
7. **WRK**: Working Key (N=No)
8. **ENC**: Encriptación (0=No, 1=Sí)
9. **IMP**: Importe (12 dígitos BCD)
10. **ICB**: Importe cashback (12 dígitos BCD)

**Ejemplo**:
```
02 59 30 32 0010011 1C 0000000012345000000000000 03 XX
```

---

### Y03 - Confirmación EMV

**Propósito**: Confirmar transacción EMV con códigos de autorización

**Estructura**:
```
02 59 30 33 [COD_AUT] 1C [COD_RESP] 03 [LRC]
```

**Parámetros**:
1. **COD_AUT**: Código de autorización del host
2. **COD_RESP**: Código de respuesta (00=Aprobado, otros=Rechazado)

**Ejemplo**:
```
02 59 30 33 123456 1C 00 03 XX
```

---

### Y06 - Cancelación

**Propósito**: Cancelar operación en curso

**Estructura**:
```
02 59 30 36 [TIMEOUT] 03 [LRC]
```

**Parámetros**:
1. **TIMEOUT**: Tiempo límite en segundos

**Ejemplo**:
```
02 59 30 36 30 03 XX
```

---

### Y0P - Impresión de Ticket

**Propósito**: Imprimir comprobante de transacción

**Estructura**:
```
02 59 30 50 [DATOS_COMERCIO] 1C [DATOS_TRANSACCION] 1C [CONFIG] 03 [LRC]
```

**Parámetros**:
1. **DATOS_COMERCIO**: Información del comercio
2. **DATOS_TRANSACCION**: Datos de la transacción
3. **CONFIG**: Configuraciones de impresión

---

## 🔍 Análisis de Respuestas

### Estructura de Respuesta
```
STX + CID + MDI + FS + DATOS + ETX + LRC
```

- **MDI**: Modo de Ingreso (B=Banda, C=Chip, M=Manual)
- **DATOS**: Campos separados por FS según el MDI

### Modos de Ingreso (MDI)

#### Banda Magnética (B)
Campos típicos:
- Tarjeta enmascarada
- Fecha + Track 1 encriptado
- Track 2 encriptado
- Código de seguridad
- Número de serie
- Tipo de cuenta + PIN
- KSN

#### Chip EMV (C)
Campos típicos:
- Tarjeta enmascarada
- Fecha + Track 2 encriptado
- Datos EMV TLV
- AID de aplicación
- Criptogramas EMV
- Tipo de cuenta + PIN
- KSN

#### Manual (M)
Campos típicos:
- Tarjeta encriptada
- Fecha + Código de seguridad
- Número de serie
- Tipo de cuenta + PIN
- KSN

## 🔧 Cálculo de LRC

El LRC (Longitudinal Redundancy Check) se calcula como XOR de todos los bytes del frame:

```python
def calculate_lrc(data_bytes):
    lrc = 0
    for byte in data_bytes:
        lrc ^= byte
    return lrc
```

**Ejemplo**:
```
Frame: 02 59 30 49 03
LRC = 02 ^ 59 ^ 30 ^ 49 ^ 03 = 4A
```

## 📝 Formato de Datos

### Importes BCD
Los importes se codifican en BCD (Binary Coded Decimal):
- 12 dígitos totales
- 2 decimales implícitos
- Padding con ceros a la izquierda

**Ejemplo**: $123.45 → `000000012345`

### Fechas
Formato: `AAMMDD`
- AA: Año (2 dígitos)
- MM: Mes (01-12)
- DD: Día (01-31)

### Claves RSA
- Longitud: 512 bytes (1024 caracteres hex)
- Formato: Hexadecimal sin espacios
- Exponente típico: `10001` (65537 decimal)

## ⚠️ Validaciones Importantes

### 1. Longitud de Frame
- Verificar que el frame tenga la longitud esperada
- Comprobar presencia de STX y ETX

### 2. LRC
- Calcular LRC de todo el frame (sin incluir el LRC)
- Comparar con el LRC recibido

### 3. Formato de Campos
- Validar longitud de importes (12 dígitos)
- Verificar formato de fechas
- Comprobar caracteres válidos en cada campo

### 4. Separadores
- Usar FS (`1C`) entre campos principales
- Usar US (`1F`) para subcampos cuando sea necesario

## 🛠️ Herramientas de Debug

### Visualización Hexadecimal
```
02 59 31 39 B1 10 F4 2E DD 15 B7 35 ... 1C 31 30 30 30 31 1C 30 30 30 30 30 30 30 31 32 33 34 35 03 XX
│  │  │  │  └─────────────────────────────┘    │  │  │  │  │  │    │  │  │  │  │  │  │  │  │  │  │  │  │  └─ LRC
│  │  │  │           RSA Key                   │  │  │  │  │  │    │  │  │  │  │  │  │  │  │  │  │  │  └─ ETX
│  │  │  │                                     │  │  │  │  │  │    └─────────────────────────────────┘
│  │  │  │                                     │  │  │  │  │  │              Importe
│  │  │  │                                     │  │  │  │  │  └─ "1" (ASCII)
│  │  │  │                                     │  │  │  │  └─ "0" (ASCII)
│  │  │  │                                     │  │  │  └─ "0" (ASCII)
│  │  │  │                                     │  │  └─ "0" (ASCII)
│  │  │  │                                     │  └─ "1" (ASCII)
│  │  │  │                                     └─ FS
│  │  │  └─ "9" (ASCII)
│  │  └─ "1" (ASCII)
│  └─ "Y" (ASCII)
└─ STX
```

### Conversión ASCII-HEX
- `Y` = `59`
- `0` = `30`
- `I` = `49`
- `1` = `31`
- `9` = `39`

## 📚 Ejemplos Completos

### Y0I (Información)
```
Comando: 02 59 30 49 03 4A
Respuesta: 02 59 30 49 50 41 59 57 41 59 1C 4E 45 54 50 41 59 1C ... 03 XX
```

### Y02 (Lectura básica)
```
Comando: 02 59 30 32 30 30 31 30 30 31 31 1C 30 30 30 30 30 30 30 31 32 33 34 35 30 30 30 30 30 30 30 30 30 30 30 30 03 XX
Respuesta: 02 59 30 32 42 1C 34 32 34 32 2A 2A 2A 2A 2A 2A 2A 2A 31 32 33 34 1C ... 03 XX
```

### Y19 (Transacción completa)
```
Comando: 02 59 31 39 [512_bytes_RSA] 1C 31 30 30 30 31 1C 30 30 30 30 30 30 30 31 32 33 34 35 1C 30 30 30 30 30 30 30 30 30 30 30 30 1C 30 03 XX
Respuesta: 02 59 31 39 43 1C [datos_emv_completos] 03 XX
```

---

**Nota**: Esta guía debe usarse junto con la documentación técnica específica del dispositivo PinPad y las especificaciones del protocolo de comunicación implementado.
# Documentación de Configuración ISO 8583

## Estructura de Directorios

El sistema cuenta con 3 directorios principales de configuración en `configIso/`:

### 1. **campos_iso/** - Definiciones de Campos ISO 8583

Contiene las especificaciones detalladas de todos los campos del protocolo ISO 8583:

#### **campos_iso.json**
Define cada campo ISO con su estructura completa:
- **Nombre y descripción** del campo
- **Formato** (LLVAR, LLLVAR, n6, an12, etc.)
- **Tipo de dato** (numeric, alphanumeric, binary, etc.)
- **Codificación** (BCD, ASCII)
- **Reglas de negocio** específicas
- **Validaciones** requeridas

Campos principales documentados:
- Campo 2: Número de tarjeta (PAN)
- Campo 3: Código de procesamiento (tipo de transacción)
- Campo 4: Importe de la transacción
- Campo 7, 12, 13: Fecha y hora
- Campo 11: Número de trace del sistema
- Campo 22: Modo de ingreso (manual, banda, chip, contactless)
- Campo 35/45: Datos de track 2 y track 1
- Campo 39: Código de respuesta
- Campo 48: Cuotas/datos originales
- Campo 52: PIN Block
- Campo 55: TAGs EMV o código de seguridad
- Campo 59: Lista de productos
- Campo 62: Número de ticket
- Campo 63: Mensajes del host

#### **codigos_respuesta.json**
Catálogo completo de códigos de respuesta ISO:
- **00, 11, 85**: Aprobada
- **01, 02, 76, 91**: Pedir autorización
- **05, 51, 54, 55, 57**: Denegadas (varios motivos)
- **96**: Error en sistema
- **94**: Número de secuencia duplicada
- Cada código incluye descripción y referencia de acción

#### **emv_tags.json**
Diccionario de TAGs EMV para transacciones con chip y contactless:
- TAGs de identificación (4F, 50, 5A, 84)
- TAGs de fecha y moneda (9A, 5F2A, 5F24)
- TAGs de transacción (9C, 9F02, 9F03, 9F26, 9F36)
- TAGs de terminal (9F1A, 9F1C, 9F33, 9F35)
- TAGs de criptografía (8F, 90, 91, 92, 93)
- Reglas de validación para modo chip (051) y contactless (071)

#### **productos.json**
Define los productos que viajan en el campo 59:

**Productos Mandatorios:**
- **021**: Indicador de capacidad máxima de captura de la terminal
  - Siempre presente
  - Valores: 1=Manual, 2=Banda, 5=Chip, 7=Contactless

**Productos Opcionales:**
- **022**: Indicador de Fallback (cuando chip falla)
- **028**: Indicador de encripción 3DES/DUKPT
- **078**: Indicador de mPOS (incluye subcampo 211 para MasterCard)
- **083**: Indicador de operatoria QR (en cierre de lote)
- **084**: KSN DUKPT (Key Serial Number)

Cada producto tiene estructura BCD/ASCII definida con longitudes y subcampos.

#### **validaciones_mensajeria.json**
Reglas de validación condicionales:
- Si campo 52 (PIN) presente → productos 028 y 084 requeridos
- Si campo 22 = chip/contactless → validar TAGs EMV en campo 55
- Si operaciones QR en cierre → producto 083 requerido
- Si mPOS con MasterCard → subcampo 211 en producto 078
- Validaciones de coherencia entre capacidades y modo de ingreso

---

### 2. **Types-Iso/** - Plantillas de Mensajes ISO

Contiene las plantillas de cada tipo de mensaje ISO 8583 organizado por operación:

#### **Estructura de Carpetas:**
- `compra_online/` - Compras en línea
- `Anulacion_compra/` - Anulaciones
- `Devolucion_online/` - Devoluciones
- `Pre_autorizacion/` - Pre-autorizaciones
- `Anulacion_pre_autorizacion/` - Anulación de pre-autorizaciones
- `Compra_offline_captura/` - Compras offline
- `Anulacion_offline_captura/` - Anulaciones offline
- `Advice_compra/` - Advice de compra
- `Advice_anulacion/` - Advice de anulación
- `Advice_devolucion/` - Advice de devolución
- `reversos/` - Reversos
- `Cierre_lote/` - Cierre de lote
- `Echo_test/` - Echo test

#### **Tipos de Mensaje:**
- **0200**: Request de autorización
- **0210**: Response de autorización
- **0220**: Advice request
- **0230**: Advice response
- **0400**: Reverso request
- **0410**: Reverso response
- **0500**: Cierre de lote request
- **0510**: Cierre de lote response
- **0800**: Echo test request
- **0810**: Echo test response
- **0100**: Pre-autorización request
- **0110**: Pre-autorización response

#### **Variantes por Modo de Ingreso:**
Cada operación puede tener variantes según el modo:
- `_banda.json` - Lectura de banda magnética
- `_chip.json` - Lectura de chip EMV
- `_contactless.json` - Lectura contactless/NFC
- `_manual.json` - Ingreso manual

#### **Estructura de Plantilla:**
Cada archivo JSON contiene:
- `tipo_mensaje`: Código del mensaje (0200, 0210, etc.)
- `descripcion`: Descripción de la operación
- `modo_ingreso`: Modo aplicable
- `campos`: Objeto con todos los campos del mensaje
  - Cada campo tiene: formato, atributo (M/O/C), descripción
  - Atributos condicionales (C1-C7) según reglas de negocio

---

### 3. **Valores/** - Valores de Referencia

#### **valores_atributos_formato.json**
Define los tipos de datos y formatos utilizados:

**Atributos de Tipo:**
- `b`: Información binaria (hex)
- `a`: Alfanumérico con espacios
- `n`: Solo valores numéricos
- `s`: Solo caracteres especiales
- `an`: Caracteres alfanuméricos
- `ans`: Alfanuméricos y especiales

**Formatos de Longitud:**
- `FIXED`: Campo de largo fijo (ej: n6)
- `LVAR`: Longitud variable con 1 dígito de longitud
- `LLVAR`: Longitud variable con 2 dígitos de longitud
- `LLLVAR`: Longitud variable con 3 dígitos de longitud

**Atributos de Mandatorio:**
- `M`: Campo Mandatorio
- `O`: Campo Opcional
- `C1`: Mandatorio si no encriptan Tracks
- `C2`: Mandatorio si no se lee Track I
- `C3`: Mandatorio si es requerido por el Emisor
- `C4`: Mandatorio si la Tarjeta solicita PIN
- `C5`: Mandatorio para Cash Back
- `C6`: Mandatorio si ingreso manual
- `C7`: Mandatorio si ingreso por banda magnética

---

## Uso del Sistema

### Flujo de Generación de Casos de Prueba:

1. **Seleccionar tipo de operación** (compra, anulación, devolución, etc.)
2. **Seleccionar modo de ingreso** (banda, chip, contactless, manual)
3. **Cargar plantilla** correspondiente desde `Types-Iso/`
4. **Validar campos** usando definiciones de `campos_iso/`
5. **Aplicar reglas** de `validaciones_mensajeria.json`
6. **Generar productos** según `productos.json`
7. **Validar TAGs EMV** si aplica usando `emv_tags.json`
8. **Verificar código de respuesta** con `codigos_respuesta.json`
9. **Aplicar formatos** según `valores_atributos_formato.json`

### Validaciones Críticas:

- Campo 11 (trace) debe ser consecutivo excepto en reversos
- Campo 62 (ticket) debe ser consecutivo por operación aprobada
- Campos 7, 12, 13 deben ser coherentes en fecha/hora
- Campo 22 debe coincidir con producto 021
- Si hay PIN (campo 52) → productos 028 y 084 obligatorios
- Si chip/contactless → validar TAGs EMV en campo 55
- Campo 59 siempre debe contener al menos producto 021

---

## Estado de la Configuración

✅ **Sin errores detectados** en la estructura de archivos JSON
✅ Todas las referencias cruzadas son coherentes
✅ Las validaciones condicionales están bien definidas
✅ Los códigos de respuesta están completos
✅ Las plantillas de mensajes cubren todos los escenarios
✅ Los TAGs EMV están correctamente mapeados

## Próximos Pasos Sugeridos

1. Implementar parser de mensajes ISO 8583
2. Crear validador de campos según reglas
3. Desarrollar generador de casos de prueba
4. Implementar encoder/decoder de formatos BCD/ASCII
5. Crear módulo de validación de TAGs EMV
6. Desarrollar API REST para generación de mensajes

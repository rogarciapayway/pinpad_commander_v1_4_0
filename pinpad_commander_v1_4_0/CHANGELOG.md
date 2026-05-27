# Changelog - PinPad Commander

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-10-24

### ✨ Agregado
- **Panel de Comandos JSON**: Nueva pestaña dedicada para visualizar comandos enviados en formato JSON estructurado
- **Log de Comandos Detallado**: Registro automático de cada comando con parámetros, descripciones y metadatos
- **Descripciones de Campos**: Cada parámetro incluye su valor y descripción extraída de commands.json
- **Colores de Sintaxis JSON**: Resaltado de sintaxis para mejor legibilidad del JSON de comandos
- **Menú Contextual Avanzado**: Opciones de copiar selección, copiar todo y limpiar para comandos JSON
- **Compactación Automática**: Gestión automática del historial de comandos JSON
- **Scroll Unificado**: Integración completa con el sistema de scroll existente

### 🔧 Cambiado
- **Interfaz de Usuario**: Reorganización de pestañas con nueva pestaña "📤 Comandos"
- **Sistema de Logging**: Mejoras en el sistema de logging para incluir comandos JSON
- **Gestión de Eventos**: Actualización del event manager para manejar nuevos controles

### 📊 Formato de Log JSON
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
    }
  },
  "frame": {
    "hex": "02 59 31 39 B1 10 F4...",
    "length": 256
  }
}
```

## [1.3.0] - 2025-10-16

### ✨ Agregado
- **Arquitectura Modular Refactorizada**: Implementación de gestores especializados para mejor organización del código
- **Soporte para Comando Y19**: Transacciones completas con RSA y manejo de EMV
- **Sistema de Patches**: Compatibilidad con módulos legacy mediante patches dinámicos
- **Gestores Especializados**:
  - `EventManager`: Gestión centralizada de eventos
  - `ConfigManager`: Manejo de configuraciones JSON
  - `SerialManager`: Gestión de puertos serie
  - `RSAManager`: Operaciones criptográficas
  - `UIManager`: Gestión de interfaz de usuario
  - `EMVManager`: Procesamiento de datos EMV
- **Parser EMV Mejorado**: Soporte completo para tags EMV con descripciones legibles
- **Sistema de Logging Avanzado**: Logs estructurados con rotación automática
- **Configuración Flexible**: Archivos JSON para comandos, parsers y decodificadores
- **Interfaz Gráfica Moderna**: UI actualizada con CustomTkinter
- **Soporte Multi-Comando**: Y02, Y03, Y06, Y0I, Y19, Y0P, Y77, Y0Q, Y26, Y0C
- **Validación de Datos**: Validación automática de campos y formatos
- **Manejo de Errores Robusto**: Sistema de excepciones personalizadas

### 🔧 Cambiado
- **Refactorización Completa**: Migración de arquitectura monolítica a modular
- **Mejoras en Performance**: Optimización de parsers y comunicación serie
- **UI Responsiva**: Interfaz más fluida y responsive
- **Logging Mejorado**: Formato de logs más claro y estructurado
- **Configuración Centralizada**: Todas las configuraciones en archivos JSON

### 🐛 Corregido
- **Estabilidad de Conexión**: Mejoras en el manejo de desconexiones inesperadas
- **Memory Leaks**: Corrección de fugas de memoria en operaciones RSA
- **Parsing de Respuestas**: Corrección de errores en parsing de campos complejos
- **Validación LRC**: Mejoras en la validación de integridad de frames
- **Manejo de Excepciones**: Mejor captura y manejo de errores de comunicación

### 🔒 Seguridad
- **Enmascaramiento de PAN**: Automático para números de tarjeta
- **Limpieza de Memoria**: Sobrescritura segura de datos sensibles
- **Validación de Claves**: Verificación de integridad de claves RSA
- **Logs Seguros**: Exclusión de datos sensibles de los logs

## [1.2.1] - 2025-10-14

### 🐛 Corregido
- Corrección de error en parsing de respuestas Y02 para modo chip
- Mejoras en la estabilidad de conexión serie
- Corrección de formato de importes en comandos Y0P

### 🔧 Cambiado
- Actualización de dependencias de seguridad
- Mejoras menores en la interfaz de usuario

## [1.2.0] - 2025-10-10

### ✨ Agregado
- **Comando Y0P**: Soporte para impresión de tickets
- **Comando Y77**: Solicitud de propinas
- **Comando Y0Q**: Mostrar QR en pantalla
- **Sensory Branding**: Soporte para tickets con branding específico
- **Configuración Y26**: Límites CVM por marca de tarjeta
- **Bimoneda Y0C**: Configuración de múltiples monedas

### 🔧 Cambiado
- Mejoras en el parser de respuestas EMV
- Optimización de la interfaz gráfica
- Actualización de la documentación

### 🐛 Corregido
- Corrección de errores en decodificación BCD
- Mejoras en el manejo de timeouts
- Corrección de formato de campos monetarios

## [1.1.2] - 2025-10-09

### 🐛 Corregido
- Corrección crítica en validación LRC
- Mejoras en el manejo de errores de comunicación
- Corrección de memory leak en operaciones RSA

### 🔒 Seguridad
- Actualización de librerías criptográficas
- Mejoras en el manejo seguro de claves privadas

## [1.1.1] - 2025-10-07

### 🐛 Corregido
- Corrección de error en parsing de Track 2
- Mejoras en la detección automática de puertos serie
- Corrección de formato de logs

### 🔧 Cambiado
- Mejoras menores en la interfaz de usuario
- Optimización de rendimiento en parsing

## [1.1.0] - 2025-10-06

### ✨ Agregado
- **Comando Y03**: Confirmación de transacciones EMV
- **Comando Y06**: Cancelación de transacciones
- **Parser Dinámico**: Parsing basado en modo de ingreso (Banda/Chip/Manual)
- **Soporte EMV Completo**: Decodificación de tags EMV estándar
- **Configuración JSON**: Sistema de configuración basado en archivos JSON
- **Logging Avanzado**: Sistema de logs con niveles y rotación

### 🔧 Cambiado
- Refactorización del sistema de parsing
- Mejoras significativas en la interfaz de usuario
- Optimización del protocolo de comunicación

### 🐛 Corregido
- Corrección de errores en decodificación hexadecimal
- Mejoras en la estabilidad de conexión
- Corrección de validación de campos

## [1.0.1] - 2025-10-03

### 🐛 Corregido
- Corrección de error en comando Y02 para modo manual
- Mejoras en el manejo de excepciones
- Corrección de formato de respuestas

### 🔧 Cambiado
- Mejoras menores en la documentación
- Optimización de imports

## [1.0.0] - 2025-10-01

### ✨ Agregado - Lanzamiento Inicial
- **Comunicación Serie**: Protocolo completo con STX/ETX/LRC
- **Comando Y0I**: Información del dispositivo PinPad
- **Comando Y02**: Lectura de tarjetas (banda magnética, chip, manual)
- **Comando Y19**: Transacciones con criptografía RSA
- **Criptografía RSA**: Soporte para claves públicas/privadas
- **Interfaz Gráfica**: UI básica con Tkinter
- **Parser de Respuestas**: Sistema básico de parsing
- **Logging**: Sistema básico de logs
- **Configuración**: Configuración básica de la aplicación

### 🔧 Características Técnicas
- **Python 3.8+**: Compatibilidad con versiones modernas de Python
- **Multiplataforma**: Soporte para Windows y Linux
- **Protocolo Robusto**: Validación LRC y manejo de errores
- **Documentación**: Documentación básica de uso

---

## 📋 Notas de Migración

### Migración de 1.2.x a 1.3.0

#### ⚠️ Cambios Importantes
- **Arquitectura**: Migración completa a arquitectura modular
- **Configuración**: Nuevos archivos de configuración JSON
- **API**: Algunos métodos han cambiado de nombre o ubicación

#### 🔄 Pasos de Migración
1. **Backup**: Realizar backup de configuraciones existentes
2. **Instalación**: Instalar nueva versión
3. **Configuración**: Migrar configuraciones al nuevo formato JSON
4. **Testing**: Verificar funcionamiento con dispositivos

#### 📝 Configuraciones Obsoletas
- Archivos `.ini` reemplazados por `.json`
- Variables de entorno reorganizadas
- Estructura de logs modificada

### Migración de 1.1.x a 1.2.0

#### 🔄 Cambios Menores
- Nuevos comandos disponibles (Y0P, Y77, Y0Q)
- Configuraciones adicionales para nuevas funcionalidades
- Mejoras en compatibilidad con diferentes modelos de PinPad

---

## 🐛 Problemas Conocidos

### Versión 1.3.0
- **Windows 7**: Compatibilidad limitada con Windows 7 (requiere actualizaciones)
- **Puertos USB**: Algunos adaptadores USB-Serie pueden requerir drivers específicos
- **Memory Usage**: Uso de memoria puede incrementar con sesiones largas

### Soluciones Temporales
- **Windows 7**: Usar Python 3.8 específicamente
- **USB-Serie**: Verificar drivers del fabricante
- **Memoria**: Reiniciar aplicación periódicamente en sesiones largas

---

## 📞 Soporte y Contacto

- **Email**: merodriguez@payway.com.ar
- **Documentación**: [Wiki del Proyecto]()
- **Releases**: [GitHub Releases]()

---

**Mantenido por**: Matias Rodriguez Alemany
**Última actualización**: 24 de Octubre, 2024
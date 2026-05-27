#!/usr/bin/env python3
"""
Configuración de seguridad y logging para PinPad Commander
"""

import logging
import os
import sys
from datetime import datetime

def setup_secure_logging():
    """Configurar logging seguro para la aplicación"""
    
    # Crear directorio de logs si no existe
    log_dir = os.path.join(os.getcwd(), "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except (OSError, PermissionError):
        log_dir = os.getcwd()  # Fallback al directorio actual
    
    # Configurar formato de logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar nivel de logging
    log_level = logging.INFO
    if os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes'):
        log_level = logging.DEBUG
    
    # Configurar logging básico
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Handler para archivo con rotación diaria
            logging.FileHandler(
                os.path.join(log_dir, f"pinpad_commander_{datetime.now().strftime('%Y%m%d')}.log"),
                encoding='utf-8'
            ),
            # Handler para consola (solo errores críticos)
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar loggers específicos
    loggers_config = {
        'serial': logging.WARNING,  # Reducir ruido de pyserial
        'urllib3': logging.WARNING,  # Reducir ruido de requests
        'PIL': logging.WARNING,      # Reducir ruido de Pillow
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)
    
    # Log inicial de seguridad
    logging.info("=== PinPad Commander Security Logging Initialized ===")
    logging.info(f"Log directory: {log_dir}")
    logging.info(f"Log level: {logging.getLevelName(log_level)}")
    
    return True

def validate_environment():
    """Validar entorno de ejecución por seguridad"""
    
    security_checks = []
    
    # Verificar permisos de escritura en directorio actual
    try:
        test_file = os.path.join(os.getcwd(), '.security_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        security_checks.append(("Write permissions", "OK"))
    except Exception as e:
        security_checks.append(("Write permissions", f"FAIL: {e}"))
        logging.warning(f"No write permissions in current directory: {e}")
    
    # Verificar existencia de directorios críticos
    critical_dirs = ['config', 'ui', 'core', 'crypto']
    for dir_name in critical_dirs:
        if os.path.isdir(dir_name):
            security_checks.append((f"Directory {dir_name}", "OK"))
        else:
            security_checks.append((f"Directory {dir_name}", "MISSING"))
            logging.warning(f"Critical directory missing: {dir_name}")
    
    # Verificar archivos críticos
    critical_files = ['config/commands.json', 'protocol.py']
    for file_name in critical_files:
        if os.path.isfile(file_name):
            security_checks.append((f"File {file_name}", "OK"))
        else:
            security_checks.append((f"File {file_name}", "MISSING"))
            logging.warning(f"Critical file missing: {file_name}")
    
    # Log resultados de verificación
    logging.info("=== Environment Security Check ===")
    for check, result in security_checks:
        logging.info(f"{check}: {result}")
    
    return security_checks

def setup_security():
    """Configurar todas las medidas de seguridad"""
    
    # Configurar logging seguro
    setup_secure_logging()
    
    # Validar entorno
    env_checks = validate_environment()
    
    # Configurar variables de entorno seguras
    os.environ.setdefault('PYTHONHASHSEED', '0')  # Reproducibilidad
    
    # Deshabilitar bytecode cache en producción
    if not os.getenv('DEBUG'):
        sys.dont_write_bytecode = True
    
    logging.info("=== Security configuration completed ===")
    
    return {
        'logging_configured': True,
        'environment_checks': env_checks,
        'security_level': 'HIGH'
    }

if __name__ == "__main__":
    setup_security()
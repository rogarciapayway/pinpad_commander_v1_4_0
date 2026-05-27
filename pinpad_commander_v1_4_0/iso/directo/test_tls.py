"""
Test directo de conexión TLS + Echo Test ISO 8583.

Uso:
    python test_tls.py
    python test_tls.py --host ws1.prismamp.com --port 8443
"""

import sys
import os
import argparse
import json
import logging

# Agregar paths para imports
ISO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ISO_DIR))

from iso.tls_client import TLSClient
from iso.iso8583_builder import build_echo_test, parse_response

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)


def load_config():
    config_path = os.path.join(ISO_DIR, 'parametria', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_echo_test(host, port, terminal_id, merchant_id, nii='0721'):
    log.info('=' * 50)
    log.info('TEST CONEXIÓN TLS + ECHO TEST')
    log.info('=' * 50)
    log.info(f'Host: {host}:{port}')
    log.info(f'Terminal: {terminal_id} | Merchant: {merchant_id}')
    log.info('-' * 50)

    # 1. Conectar
    log.info('[1] Conectando TLS...')
    client = TLSClient(host, port, timeout=20.0)
    try:
        client.connect()
        log.info('[1] ✅ Conexión TLS establecida')
    except Exception as e:
        log.error(f'[1] ❌ Fallo conexión: {e}')
        return False

    # 2. Construir Echo Test
    log.info('[2] Construyendo Echo Test (0800)...')
    msg = build_echo_test(terminal_id, merchant_id, nii)
    log.info(f'[2] TX: {" ".join("%02X" % b for b in msg)}')

    # 3. Enviar y recibir
    log.info('[3] Enviando...')
    try:
        response = client.send_and_receive(msg, timeout=20.0)
    except Exception as e:
        log.error(f'[3] ❌ Error: {e}')
        client.disconnect()
        return False

    if not response:
        log.error('[3] ❌ Sin respuesta (timeout)')
        client.disconnect()
        return False

    log.info(f'[3] RX: {" ".join("%02X" % b for b in response)}')

    # 4. Parsear respuesta
    log.info('[4] Parseando respuesta...')
    parsed = parse_response(response)
    mti = parsed.get('mti', '')
    resp_code = parsed.get('fields', {}).get(39, '')
    log.info(f'[4] MTI: {mti} | Campo 39: {resp_code or "(no presente)"}')

    if mti == '0810':
        log.info('[4] ✅ ECHO TEST OK - Host respondió 0810')
    elif resp_code == '00':
        log.info('[4] ✅ ECHO TEST APROBADO')
    else:
        log.warning(f'[4] ⚠️ Respuesta inesperada: MTI={mti} F39={resp_code}')

    # 5. Desconectar
    client.disconnect()
    log.info('[5] Desconectado')
    log.info('=' * 50)

    return mti == '0810' or resp_code == '00'


def main():
    parser = argparse.ArgumentParser(description='Test TLS + Echo Test ISO 8583')
    parser.add_argument('--host', help='Host destino')
    parser.add_argument('--port', type=int, help='Puerto TLS')
    parser.add_argument('--terminal', help='Terminal ID (8 chars)')
    parser.add_argument('--merchant', help='Merchant ID (15 chars)')
    parser.add_argument('--nii', default=None, help='NII (default: desde config.json)')
    args = parser.parse_args()

    # Cargar config
    cfg = load_config()
    terminal_cfg = cfg.get('terminal', {})
    nii_cfg = cfg.get('nii', {})
    # Usar primer acquirer para host/port
    default_acq = cfg.get('acquirers', [{}])[0]

    host = args.host or default_acq.get('ip', 'ws1.prismamp.com')
    port = args.port or int(default_acq.get('ipPort', '8443'))
    terminal = args.terminal or terminal_cfg.get('terminalId', '74000025')
    merchant = args.merchant or '03659307'
    nii = args.nii or nii_cfg.get('echo', '0112')

    success = run_echo_test(host, port, terminal, merchant, nii)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

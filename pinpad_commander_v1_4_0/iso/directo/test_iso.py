"""
Test directo de mensaje ISO 0200 - Replay desde log.

Toma un request hex del log y lo reenvía al host cambiando
trace/ticket/timestamp para que sea único.

Uso:
    python test_iso.py
    python test_iso.py --nii 0721
    python test_iso.py --nii 0112
"""

import sys
import os
import argparse
import json
import struct
import logging
import random
from datetime import datetime

ISO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ISO_DIR))

from iso.tls_client import TLSClient
from iso.iso8583_builder import build_message, parse_response

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)


def load_config():
    config_path = os.path.join(ISO_DIR, 'parametria', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_iso_test(host, port, terminal, merchant, nii, monto=123.45):
    log.info('=' * 60)
    log.info('TEST ISO 0200 - COMPRA CONTACTLESS')
    log.info('=' * 60)
    log.info(f'Host: {host}:{port}')
    log.info(f'Terminal: {terminal} | Merchant: {merchant} | NII: {nii}')
    log.info(f'Monto: ${monto}')
    log.info('-' * 60)

    now = datetime.now()
    trace = str(random.randint(1, 999999)).zfill(6)
    ticket = str(random.randint(1, 9999)).zfill(4)
    tpdu = '60%s0000' % nii

    # Construir 0200 compra contactless (simulada sin track2 real)
    # Usamos track2 de prueba del log
    track2 = '4507990000006454D28072014560000000'

    fields = {
        3:  '000000',
        4:  str(int(round(monto * 100))).zfill(12),
        7:  now.strftime('%m%d%H%M%S'),
        11: trace,
        12: now.strftime('%H%M%S'),
        13: now.strftime('%m%d'),
        22: '0071',  # contactless
        24: nii,
        25: '00',
        35: track2,
        41: terminal.ljust(8)[:8],
        42: merchant.ljust(15)[:15],
        48: '001',
        49: '032',
        55: '9505000000000000' +
            '9A03' + now.strftime('%y%m%d') +
            '9C0100' +
            '9F020600000001234' + '5' +
            '9F03060000000000000' + '0' +
            '9F10070601120' +
            '3A10200' +
            '0' +
            '9F2608AABBCCDD11223344' +
            '9F2701' + '80' +
            '9F3303E0F8C8' +
            '9F34033F0000' +
            '9F360200FF' +
            '9F3704AABBCCDD',
        59: '02100010040707',
        60: 'PAYWAY_COE',
        62: ticket,
    }

    msg = build_message('0200', tpdu, fields)
    log.info(f'[1] Mensaje construido: {len(msg)} bytes')
    log.info(f'[1] TX: {" ".join("%02X" % b for b in msg[:40])} ...')

    # Conectar
    log.info(f'[2] Conectando TLS a {host}:{port}...')
    client = TLSClient(host, port, timeout=20.0)
    try:
        client.connect()
        log.info('[2] ✅ Conectado')
    except Exception as e:
        log.error(f'[2] ❌ {e}')
        return False

    # Enviar
    log.info('[3] Enviando 0200...')
    try:
        response = client.send_and_receive(msg, timeout=20.0)
    except Exception as e:
        log.error(f'[3] ❌ {e}')
        client.disconnect()
        return False

    if not response:
        log.error('[3] ❌ Sin respuesta')
        client.disconnect()
        return False

    log.info(f'[3] RX: {len(response)} bytes')

    # Parsear
    parsed = parse_response(response)
    mti = parsed.get('mti', '????')
    fields_resp = parsed.get('fields', {})
    resp_code = fields_resp.get(39, '??')
    auth_code = fields_resp.get(38, '')

    log.info(f'[4] MTI: {mti} | F39: {resp_code} | F38: {auth_code}')

    if resp_code == '00':
        log.info(f'[4] ✅ APROBADA - Auth: {auth_code}')
    elif resp_code == '05':
        log.info('[4] ⚠️ DENEGADA (05) - Tarjeta de prueba sin fondos')
    elif resp_code == '57':
        log.info('[4] ⚠️ TRANSACCIÓN NO PERMITIDA (57)')
    else:
        log.info(f'[4] Respuesta: {resp_code}')

    log.info(f'[4] Campos: {list(fields_resp.keys())}')
    for k, v in sorted(fields_resp.items()):
        log.info(f'    F{k:03d}: {v}')

    client.disconnect()
    log.info('[5] Desconectado')
    log.info('=' * 60)

    return resp_code != '??'


def main():
    parser = argparse.ArgumentParser(description='Test ISO 0200 directo')
    parser.add_argument('--host', help='Host destino')
    parser.add_argument('--port', type=int, help='Puerto TLS')
    parser.add_argument('--terminal', help='Terminal ID')
    parser.add_argument('--merchant', help='Merchant ID')
    parser.add_argument('--nii', default='0721', help='NII (default: 0721 para transacciones)')
    parser.add_argument('--monto', type=float, default=123.45, help='Monto en pesos')
    args = parser.parse_args()

    cfg = load_config()
    default_acq = cfg.get('acquirers', [{}])[0]
    terminal_cfg = cfg.get('terminal', {})

    host = args.host or default_acq.get('ip', 'ws1.prismamp.com')
    port = args.port or int(default_acq.get('ipPort', '8443'))
    terminal = args.terminal or terminal_cfg.get('terminalId', '74000025')
    merchant = args.merchant or '03659307'

    success = run_iso_test(host, port, terminal, merchant, args.nii, args.monto)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

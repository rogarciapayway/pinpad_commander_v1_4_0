"""
Test ISO 0200 - Ingreso Manual (basado en trama real).

Envía una compra manual con PAN, vencimiento y CVV.
NII: 0721 (transacciones Visa)

Uso:
    python test_manual.py
    python test_manual.py --monto 50.00
    python test_manual.py --pan 4507990000001026 --venc 2503
"""

import sys
import os
import argparse
import json
import random
import logging
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


def run_manual_test(host, port, terminal, merchant, nii, pan, venc, cvv, monto):
    log.info('=' * 60)
    log.info('TEST ISO 0200 - COMPRA MANUAL')
    log.info('=' * 60)
    log.info(f'Host: {host}:{port} | NII: {nii}')
    log.info(f'Terminal: {terminal} | Merchant: {merchant}')
    log.info(f'PAN: {pan[:6]}****{pan[-4:]} | Venc: {venc} | Monto: ${monto}')
    log.info('-' * 60)

    now = datetime.now()
    trace = str(random.randint(1, 999999)).zfill(6)
    ticket = str(random.randint(1, 9999)).zfill(4)
    tpdu = '60%s0000' % nii

    fields = {
        2:  pan,
        3:  '000000',
        4:  str(int(round(monto * 100))).zfill(12),
        7:  now.strftime('%m%d%H%M%S'),
        11: trace,
        12: now.strftime('%H%M%S'),
        13: now.strftime('%m%d'),
        14: venc,
        19: '0032',
        22: '0011',
        24: nii,
        25: '00',
        41: terminal.ljust(8)[:8],
        42: merchant.ljust(15)[:15],
        48: '001',
        49: '032',
        55: cvv,
        59: '0091001004009102100010040701',
        60: 'PAYWAY_COE',
        62: ticket,
    }

    msg = build_message('0200', tpdu, fields)
    log.info(f'[1] Mensaje: {len(msg)} bytes | Trace: {trace} | Ticket: {ticket}')
    log.info(f'[1] HEX: {" ".join("%02X" % b for b in msg)}')

    # Conectar
    log.info(f'[2] Conectando TLS...')
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
        log.error('[3] ❌ Sin respuesta (timeout)')
        client.disconnect()
        return False

    # Parsear
    log.info(f'[4] RX: {len(response)} bytes')
    log.info(f'[4] HEX: {" ".join("%02X" % b for b in response)}')

    parsed = parse_response(response)
    mti = parsed.get('mti', '????')
    fields_resp = parsed.get('fields', {})
    resp_code = fields_resp.get(39, '??')
    auth_code = fields_resp.get(38, '')
    ref = fields_resp.get(37, '')

    log.info(f'[5] MTI: {mti} | F39: {resp_code} | F38: {auth_code} | F37: {ref}')

    if resp_code == '00':
        log.info(f'[5] ✅ APROBADA - Auth: {auth_code}')
    elif resp_code == '05':
        log.info('[5] ❌ DENEGADA (05)')
    elif resp_code == '57':
        log.info('[5] ❌ TRANSACCIÓN NO PERMITIDA (57)')
    else:
        log.info(f'[5] Respuesta: {resp_code}')

    log.info('[5] Campos:')
    for k, v in sorted(fields_resp.items()):
        log.info(f'    F{k:03d}: {v}')

    client.disconnect()
    log.info('[6] Desconectado')
    log.info('=' * 60)

    return resp_code not in ('??', '')


def main():
    parser = argparse.ArgumentParser(description='Test ISO 0200 Manual')
    parser.add_argument('--host', help='Host destino')
    parser.add_argument('--port', type=int, help='Puerto TLS')
    parser.add_argument('--terminal', help='Terminal ID')
    parser.add_argument('--merchant', help='Merchant ID')
    parser.add_argument('--nii', default='0721', help='NII (default: 0721)')
    parser.add_argument('--pan', default='4507990000001026', help='PAN')
    parser.add_argument('--venc', default='2503', help='Vencimiento YYMM')
    parser.add_argument('--cvv', default='830', help='CVV/CVC')
    parser.add_argument('--monto', type=float, default=100.00, help='Monto en pesos')
    args = parser.parse_args()

    cfg = load_config()
    default_acq = cfg.get('acquirers', [{}])[0]
    terminal_cfg = cfg.get('terminal', {})
    nii_cfg = cfg.get('nii', {})

    host = args.host or default_acq.get('ip', 'ws1.prismamp.com')
    port = args.port or int(default_acq.get('ipPort', '8443'))
    terminal = args.terminal or terminal_cfg.get('terminalId', '74000025')
    merchant = args.merchant or '03659307'
    nii = args.nii or nii_cfg.get('Visa', '0721')

    success = run_manual_test(host, port, terminal, merchant, nii,
                              args.pan, args.venc, args.cvv, args.monto)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

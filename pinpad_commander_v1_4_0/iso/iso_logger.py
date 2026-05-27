"""
Logger de transacciones ISO 8583.

Graba cada request 0200 y response 0210 en archivos diarios.
Formato: logIso/YYYYMMDD_transacciones.log
"""

import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logIso')


def _ensure_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def _get_log_path():
    _ensure_dir()
    return os.path.join(LOG_DIR, '%s_transacciones.log' % datetime.now().strftime('%Y%m%d'))


def _get_seq(path):
    if not os.path.exists(path):
        return 1
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in reversed(lines):
            if line.startswith('=== TXN #'):
                return int(line.split('#')[1].split(' ')[0]) + 1
    except Exception:
        pass
    return 1


def _format_hex(raw_hex):
    clean = raw_hex.replace(' ', '')
    lines = []
    for i in range(0, len(clean), 32):
        chunk = clean[i:i+32]
        spaced = ' '.join(chunk[j:j+4] for j in range(0, len(chunk), 4))
        lines.append('    %s' % spaced)
    return '\n'.join(lines)


def _format_fields(parsed):
    lines = []
    fields = parsed.get('fields', {})
    for fnum, fval in sorted(fields.items()):
        lines.append('    -> F%03d: [%s]' % (fnum, fval))
    return '\n'.join(lines)


def log_transaction(result, marca, modo, mdi):
    """
    Grabar transaccion en archivo diario.

    Args:
        result: dict del TransactionManager.execute()
        marca: str marca detectada
        modo: str modo de ingreso
        mdi: str MDI del PinPad
    """
    try:
        path = _get_log_path()
        seq = _get_seq(path)
        now = datetime.now()
        metadata = result.get('metadata', {})
        conn = result.get('connection', {})
        parsed = result.get('parsed', {})
        resp_code = result.get('response_code', 'XX')
        resp_desc = result.get('response_description', '')

        with open(path, 'a', encoding='utf-8') as f:
            f.write('=== TXN #%04d %s ===\n' % (seq, now.strftime('%Y-%m-%d %H:%M:%S')))
            f.write('Marca: %s | Modo: %s (MDI=%s) | Monto: $%.2f\n' % (
                marca, modo, mdi, metadata.get('monto', 0)))
            f.write('Terminal: %s | Merchant: %s\n' % (
                conn.get('terminal_id', '?').strip(),
                conn.get('merchant_id', '?').strip()))
            f.write('NII: %s | TPDU: %s | Host: %s:%s\n' % (
                conn.get('nii', '?'), conn.get('tpdu', '?'),
                conn.get('host', '?'), conn.get('port', '?')))
            f.write('Trace: %s | Ticket: %s\n' % (
                metadata.get('trace', '?'), metadata.get('ticket', '?')))
            f.write('\n')

            # REQUEST 0200
            f.write('--- REQUEST 0200 ---\n')
            req_hex = result.get('request_hex', '')
            if req_hex:
                f.write(_format_hex(req_hex) + '\n')
            f.write('\n')

            # RESPONSE 0210
            if result.get('success'):
                f.write('--- RESPONSE %s ---\n' % parsed.get('mti', '0210'))
                f.write('Codigo: %s - %s\n' % (resp_code, resp_desc))
                f.write('TPDU: %s | MTI: %s\n' % (parsed.get('tpdu', '?'), parsed.get('mti', '?')))
                f.write('Campos: %s\n' % parsed.get('bitmap_fields', []))
                f.write(_format_fields(parsed) + '\n')
                resp_hex = result.get('response_hex', '')
                if resp_hex:
                    f.write('\nHEX:\n')
                    f.write(_format_hex(resp_hex) + '\n')
            else:
                f.write('--- ERROR ---\n')
                f.write('%s\n' % result.get('error', 'Sin respuesta'))

            f.write('\n' + '=' * 60 + '\n\n')

        log.info('TXN #%04d grabada en %s', seq, os.path.basename(path))

    except Exception as e:
        log.error('Error grabando transaccion: %s', e)

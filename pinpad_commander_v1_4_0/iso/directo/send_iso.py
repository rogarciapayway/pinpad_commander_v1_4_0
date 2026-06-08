"""
Envío directo de mensaje ISO por consola.

Pega un fragmento hex (con o sin espacios/saltos de línea),
se conecta al host, lo envía y muestra la respuesta.

Uso:
    python send_iso.py
    python send_iso.py --host ws1.prismamp.com --port 8443
"""

import sys
import os
import ssl
import socket
import struct
import argparse
import json

ISO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    config_path = os.path.join(ISO_DIR, 'parametria', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_response_fields(data):
    """Parser mínimo para extraer campos clave de la respuesta."""
    if len(data) < 15:
        return {}

    from iso.iso8583_builder import parse_response
    sys.path.insert(0, os.path.dirname(ISO_DIR))
    parsed = parse_response(data)
    return parsed


def send_and_receive(host, port, packet):
    """Conectar TLS, enviar paquete y recibir respuesta."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    ss = ctx.wrap_socket(s, server_hostname=host)

    try:
        ss.connect((host, port))
    except Exception as e:
        print(f'\n  ERROR Error conectando a {host}:{port}: {e}')
        return None

    ss.sendall(packet)

    ss.settimeout(15)
    try:
        hdr = b''
        while len(hdr) < 2:
            chunk = ss.recv(2 - len(hdr))
            if not chunk:
                print('\n  ERROR Conexión cerrada sin respuesta')
                ss.close()
                return None
            hdr += chunk

        msg_len = struct.unpack('>H', hdr)[0]

        data = b''
        while len(data) < msg_len:
            chunk = ss.recv(msg_len - len(data))
            if not chunk:
                break
            data += chunk

        ss.close()
        return data

    except socket.timeout:
        print('\n  ❌ Timeout esperando respuesta')
        ss.close()
        return None
    except Exception as e:
        print(f'\n  ERROR: {e}')
        ss.close()
        return None


def main():
    parser = argparse.ArgumentParser(description='Envío directo ISO por consola')
    parser.add_argument('--host', help='Host destino')
    parser.add_argument('--port', type=int, help='Puerto TLS')
    args = parser.parse_args()

    cfg = load_config()
    default_acq = cfg.get('acquirers', [{}])[0]

    host = args.host or default_acq.get('ip', 'ws1.prismamp.com')
    port = args.port or int(default_acq.get('ipPort', '8443'))

    print('=' * 60)
    print('  ENVÍO DIRECTO ISO 8583')
    print('=' * 60)
    print(f'  Host: {host}:{port}')
    print('-' * 60)
    print()
    print('  Pegá el mensaje ISO en hex (con o sin espacios).')
    print('  Puede incluir el header de longitud (2 bytes) o no.')
    print('  Terminá con una línea vacía:')
    print()

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line.strip())

    if not lines:
        print('  No se ingresó ningún dato.')
        return

    # Limpiar hex: quitar espacios, tabs, saltos
    raw_hex = ''.join(lines).replace(' ', '').replace('\t', '').replace('\n', '')

    # Validar hex
    try:
        msg_bytes = bytes.fromhex(raw_hex)
    except ValueError as e:
        print(f'\n  ERROR en hex: {e}')
        return

    # Determinar si tiene header de longitud
    # Si los primeros 2 bytes coinciden con el largo restante, ya tiene header
    if len(msg_bytes) >= 2:
        declared_len = struct.unpack('>H', msg_bytes[:2])[0]
        if declared_len == len(msg_bytes) - 2:
            # Ya tiene header de longitud
            packet = msg_bytes
        else:
            # No tiene header, agregarlo
            packet = struct.pack('>H', len(msg_bytes)) + msg_bytes
    else:
        packet = struct.pack('>H', len(msg_bytes)) + msg_bytes

    msg_without_header = packet[2:]
    tpdu = msg_without_header[:5].hex().upper()
    nii = tpdu[2:6]

    print()
    print(f'  TX: {len(packet)} bytes (msg: {len(msg_without_header)})')
    print(f'  TPDU: {tpdu} | NII: {nii}')
    print(f'  Conectando a {host}:{port}...')

    response = send_and_receive(host, port, packet)

    if not response:
        return

    print()
    print(f'  OK RX: {len(response)} bytes')
    print()
    print('  HEX:')

    # Mostrar hex formateado en bloques de 16 bytes
    hex_str = response.hex().upper()
    for i in range(0, len(hex_str), 32):
        chunk = hex_str[i:i+32]
        formatted = ' '.join(chunk[j:j+4] for j in range(0, len(chunk), 4))
        print(f'    {formatted}')

    # Parsear respuesta
    print()
    sys.path.insert(0, os.path.dirname(ISO_DIR))
    from iso.iso8583_builder import parse_response
    parsed = parse_response(response)

    mti = parsed.get('mti', '????')
    fields = parsed.get('fields', {})
    resp_code = fields.get(39, '??')

    print(f'  MTI: {mti}')
    print(f'  Código respuesta (F39): {resp_code}')

    # Mostrar campos principales
    if fields.get(38):
        print(f'  Auth (F38): {fields[38]}')
    if fields.get(37):
        print(f'  Ref (F37): {fields[37]}')

    # Campo 63 - mensaje del host (convertir a ASCII)
    if fields.get(63):
        f63 = fields[63]
        print(f'  Mensaje host (F63): {f63}')

    # Mostrar todos los campos
    print()
    print('  Campos:')
    for k, v in sorted(fields.items()):
        print(f'    F{k:03d}: {v}')

    print()
    print('=' * 60)

    print()
    input('  Presioná ENTER para salir...')


if __name__ == '__main__':
    main()

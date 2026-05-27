"""
Replay de mensaje ISO real desde log.

Toma el hex de un request exitoso del log y lo reenvía tal cual.
Sirve para validar que la conexión TLS + formato funciona.

El host probablemente responda con error de trace duplicado (94)
o denegada, pero confirma que el formato es correcto.
"""

import sys
import os
import ssl
import socket
import struct
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

ISO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ISO_DIR))
from iso.iso8583_builder import parse_response


# TXN #0045 del log - Visa contactless $888.77 con NII 0721 - fue APROBADA
# Este es el request hex real (sin los 2 bytes de longitud del header)
TXN_APROBADA_HEX = (
    "6007210000020032382780"
    "20C582340000000000000088770506164228304412164228050600320071000007210037450799000000645"
    "4D28072014560000000000F37343030303032353033363539333037202020202020200001310003303031"
    "30333230323434393530353030303030303030303039413033323630353036394330313030394630323036"
    "30303030303030383838373739463033303630303030303030303030303039463130303730363031313230"
    "33413032303030394632363038363434453833364237324145313443303946323730313830394633333033"
    "45304638433839463334303333463030303039463336303230303437394633373034393043364644333339"
    "46314530383338333533313330343934333433303039463645303432303730303030303834303741303030"
    "30303030303331303130354633343031303038323032323030303546324130323030333332001430323130"
    "30303130303430373037001050415957415F434F450004343731370"
).replace("\n", "")

# Limpiar y convertir
def clean_hex(h):
    return bytes.fromhex(h.replace(" ", "").replace("\n", ""))


def replay_message(host, port, msg_hex):
    log.info('=' * 60)
    log.info('REPLAY ISO - Mensaje real del log')
    log.info('=' * 60)
    log.info(f'Host: {host}:{port}')

    # El mensaje del log ya incluye TPDU, solo agregar header de longitud
    try:
        msg = clean_hex(msg_hex)
    except Exception as e:
        log.error(f'Error parseando hex: {e}')
        return

    # Agregar header de longitud
    pkt = struct.pack('>H', len(msg)) + msg
    log.info(f'TX: {len(pkt)} bytes (header 2 + msg {len(msg)})')
    log.info(f'TPDU: {msg[:5].hex().upper()}')

    # Conectar
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    ss = ctx.wrap_socket(s, server_hostname=host)

    try:
        ss.connect((host, port))
        log.info('TLS conectado')
    except Exception as e:
        log.error(f'Connect fail: {e}')
        return

    ss.sendall(pkt)
    log.info('Enviado, esperando...')

    ss.settimeout(10)
    try:
        # Leer header de longitud
        len_bytes = ss.recv(2)
        if not len_bytes:
            log.error('Conexión cerrada sin datos')
            ss.close()
            return

        msg_len = struct.unpack('>H', len_bytes)[0]
        log.info(f'Header indica {msg_len} bytes')

        # Leer mensaje
        data = b''
        while len(data) < msg_len:
            chunk = ss.recv(msg_len - len(data))
            if not chunk:
                break
            data += chunk

        log.info(f'RX: {len(data)} bytes')
        log.info(f'HEX: {" ".join("%02X" % b for b in data)}')

        # Parsear
        parsed = parse_response(data)
        mti = parsed.get('mti', '????')
        fields = parsed.get('fields', {})
        resp_code = fields.get(39, '??')
        auth = fields.get(38, '')

        log.info(f'MTI: {mti} | F39: {resp_code} | F38: {auth}')
        for k, v in sorted(fields.items()):
            log.info(f'  F{k:03d}: {v}')

        if resp_code == '00':
            log.info('✅ APROBADA')
        elif resp_code == '94':
            log.info('⚠️ Trace duplicado (esperado en replay)')
        else:
            log.info(f'Respuesta: {resp_code}')

    except socket.timeout:
        log.error('Timeout esperando respuesta')
    except Exception as e:
        log.error(f'Error: {e}')
    finally:
        ss.close()

    log.info('=' * 60)


if __name__ == '__main__':
    # TXN #0045 del log - Visa CTLS $888.77 NII 0721 -> APROBADA
    # Hex completo incluyendo header de longitud (017C = 380 bytes)
    full_packet = (
        "017C 6007 2100 0002 0032 3827 8020 C582"
        " 3400 0000 0000 0008 8877 0506 1642 2830"
        " 4412 1642 2805 0600 3200 7100 0007 2100"
        " 3745 0799 0000 0064 54D2 8072 0145 6000"
        " 0000 000F 3734 3030 3030 3235 3033 3635"
        " 3933 3037 2020 2020 2020 2000 0131 0003"
        " 3030 3130 3332 0244 3935 3035 3030 3030"
        " 3030 3030 3030 3941 3033 3236 3035 3036"
        " 3943 3031 3030 3946 3032 3036 3030 3030"
        " 3030 3038 3838 3737 3946 3033 3036 3030"
        " 3030 3030 3030 3030 3030 3946 3130 3037"
        " 3036 3031 3132 3033 4130 3230 3030 3946"
        " 3236 3038 3634 3645 3833 3642 3732 4145"
        " 3134 4330 3946 3237 3031 3830 3946 3333"
        " 3033 4530 4638 4338 3946 3334 3033 3346"
        " 3030 3030 3946 3336 3032 3030 3437 3946"
        " 3337 3034 3930 4336 4644 3333 3946 3145"
        " 3038 3338 3335 3331 3330 3439 3433 3433"
        " 3030 3946 3645 3034 3230 3730 3030 3030"
        " 3834 3037 4130 3030 3030 3030 3033 3130"
        " 3130 3546 3334 3031 3030 3832 3032 3230"
        " 3030 3546 3241 3032 3030 3332 0014 3032"
        " 3130 3030 3130 3034 3037 3037 0010 5041"
        " 5957 4159 5F43 4F45 0004 3437 3137"
    ).replace(" ", "")

    # El paquete ya incluye header de longitud, enviarlo directo como bytes
    pkt = bytes.fromhex(full_packet)

    # Enviar directo (pkt ya tiene header + mensaje)
    log.info('=' * 60)
    log.info('REPLAY ISO - TXN#45 Visa CTLS $888.77 NII 0721')
    log.info('=' * 60)
    log.info(f'TX: {len(pkt)} bytes')
    log.info(f'TPDU: {pkt[2:7].hex().upper()}')

    import ssl, socket
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    ss = ctx.wrap_socket(s, server_hostname='ws1.prismamp.com')
    ss.connect(('ws1.prismamp.com', 8443))
    log.info('TLS conectado')

    ss.sendall(pkt)
    log.info('Enviado, esperando...')

    ss.settimeout(10)
    try:
        # Leer header
        hdr = b''
        while len(hdr) < 2:
            hdr += ss.recv(2 - len(hdr))
        msg_len = struct.unpack('>H', hdr)[0]
        # Leer body
        data = b''
        while len(data) < msg_len:
            chunk = ss.recv(msg_len - len(data))
            if not chunk:
                break
            data += chunk
        log.info(f'RX: {len(data)} bytes')
        log.info(f'HEX: {" ".join("%02X" % b for b in data)}')
        parsed = parse_response(data)
        fields = parsed.get('fields', {})
        log.info(f'MTI: {parsed.get("mti")} | F39: {fields.get(39, "?")} | F38: {fields.get(38, "")}')
    except socket.timeout:
        log.error('Timeout')
    except Exception as e:
        log.error(f'Error: {e}')
    finally:
        ss.close()

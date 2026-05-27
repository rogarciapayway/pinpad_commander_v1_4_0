"""
Prueba variantes de formato para Echo Test.
El host cierra conexión - probamos distintos formatos de header.
"""
import ssl, socket, struct, time
from datetime import datetime

def str_to_bcd(s):
    if len(s) % 2:
        s = '0' + s
    return bytes(int(s[i:i+2], 16) for i in range(0, len(s), 2))

def build_echo(terminal, merchant, nii):
    now = datetime.now()
    tpdu = bytes.fromhex('60' + nii + '0000')
    mti = str_to_bcd('0800')
    f3 = str_to_bcd('990000')
    f7 = str_to_bcd(now.strftime('%m%d%H%M%S'))
    f11 = str_to_bcd('000001')
    f12 = str_to_bcd(now.strftime('%H%M%S'))
    f13 = str_to_bcd(now.strftime('%m%d'))
    f24 = str_to_bcd(nii)
    f41 = terminal.ljust(8)[:8].encode()
    f42 = merchant.ljust(15)[:15].encode()
    f60_data = b'WPH0001'
    f60 = str_to_bcd('%04d' % len(f60_data)) + f60_data

    bitmap = struct.pack('>Q', sum(1 << (64 - f) for f in [3, 7, 11, 12, 13, 24, 41, 42, 60]))
    body = f3 + f7 + f11 + f12 + f13 + f24 + f41 + f42 + f60
    msg = tpdu + mti + bitmap + body
    return msg

def try_send(label, packet):
    print(f'\n--- {label} ---')
    print('TX (%d bytes):' % len(packet), ' '.join('%02X' % b for b in packet[:30]), '...')
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    ss = ctx.wrap_socket(s, server_hostname='ws1.prismamp.com')
    try:
        ss.connect(('ws1.prismamp.com', 8443))
    except Exception as e:
        print(f'  Connect FAIL: {e}')
        return
    
    ss.sendall(packet)
    ss.settimeout(8)
    try:
        time.sleep(0.5)
        r = ss.recv(4096)
        if r:
            print('  RX (%d bytes):' % len(r), ' '.join('%02X' % b for b in r))
        else:
            print('  RX: conexion cerrada')
    except socket.timeout:
        print('  RX: timeout')
    except Exception as e:
        print('  RX error:', e)
    finally:
        ss.close()


msg = build_echo('74000025', '03659307', '0721')

# Variante 1: Header 2 bytes Big Endian (longitud del mensaje sin header)
pkt1 = struct.pack('>H', len(msg)) + msg
try_send('Variante 1: Header BE len(msg)=%d' % len(msg), pkt1)

# Variante 2: Sin header (solo mensaje)
try_send('Variante 2: Sin header', msg)

# Variante 3: Header con longitud incluyendo TPDU pero sin contar header
# (igual que variante 1 pero por claridad)

# Variante 4: Header 2 bytes con longitud del mensaje SIN TPDU
msg_sin_tpdu = msg[5:]  # quitar 5 bytes de TPDU
pkt4 = struct.pack('>H', len(msg_sin_tpdu)) + msg
try_send('Variante 4: Header len(sin_tpdu)=%d, msg completo' % len(msg_sin_tpdu), pkt4)

# Variante 5: NII diferente (0112 es comun en testing)
msg5 = build_echo('74000025', '03659307', '0112')
pkt5 = struct.pack('>H', len(msg5)) + msg5
try_send('Variante 5: NII=0112', pkt5)

# Variante 6: Sin campo 60
now = datetime.now()
tpdu6 = bytes.fromhex('6007210000')
mti6 = str_to_bcd('0800')
f3 = str_to_bcd('990000')
f7 = str_to_bcd(now.strftime('%m%d%H%M%S'))
f11 = str_to_bcd('000001')
f12 = str_to_bcd(now.strftime('%H%M%S'))
f13 = str_to_bcd(now.strftime('%m%d'))
f24 = str_to_bcd('0721')
f41 = b'74000025'
f42 = b'03659307       '
bitmap6 = struct.pack('>Q', sum(1 << (64 - f) for f in [3, 7, 11, 12, 13, 24, 41, 42]))
body6 = f3 + f7 + f11 + f12 + f13 + f24 + f41 + f42
msg6 = tpdu6 + mti6 + bitmap6 + body6
pkt6 = struct.pack('>H', len(msg6)) + msg6
try_send('Variante 6: Sin campo 60', pkt6)

print('\n--- FIN ---')

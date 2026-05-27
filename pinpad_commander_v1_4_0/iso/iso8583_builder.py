"""
ISO 8583 Message Builder / Parser

Formatos verificados contra traza real del SPP Payway:
- Campo 2 (PAN): LLVAR BCD (1 byte len BCD + PAN en BCD)
- Campo 35 (Track2): LLVAR BCD (1 byte len BCD + Track2 en BCD, = -> D, pad F)
- Campo 49 (Moneda): FIXED ASCII 3 bytes
- LLLVAR: 2 bytes len BCD + data ASCII
"""

import struct
import re
from datetime import datetime


def _str_to_bcd(s):
    if len(s) % 2:
        s = '0' + s
    return bytes(int(s[i:i+2], 16) for i in range(0, len(s), 2))


def _bcd_to_str(b):
    return ''.join('%02X' % byte for byte in b)


def _build_bitmap(field_numbers):
    result = 0
    for f in field_numbers:
        if 1 <= f <= 64:
            result |= (1 << (64 - f))
    return struct.pack('>Q', result)


def _parse_bitmap(data):
    val = struct.unpack('>Q', data[:8])[0]
    return [i+1 for i in range(64) if val & (1 << (63-i))]


# Definicion de campos - verificado contra traza real
# encoding: 'bcd_fixed', 'bcd_llvar', 'bcd_track', 'ascii_fixed', 'ascii_lllvar'
FIELD_DEFS = {
    2:  {'type': 'LLVAR',  'enc': 'bcd'},        # PAN: 1 byte len BCD + PAN BCD
    3:  {'type': 'FIXED',  'enc': 'bcd',  'dig': 6},
    4:  {'type': 'FIXED',  'enc': 'bcd',  'dig': 12},
    7:  {'type': 'FIXED',  'enc': 'bcd',  'dig': 10},
    11: {'type': 'FIXED',  'enc': 'bcd',  'dig': 6},
    12: {'type': 'FIXED',  'enc': 'bcd',  'dig': 6},
    13: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    14: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    15: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    17: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    19: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    22: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    23: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    24: {'type': 'FIXED',  'enc': 'bcd',  'dig': 4},
    25: {'type': 'FIXED',  'enc': 'bcd',  'dig': 2},
    34: {'type': 'LLVAR',  'enc': 'ascii'},
    35: {'type': 'LLVAR',  'enc': 'track2'},      # Track2: 1 byte len BCD + BCD con D y F
    37: {'type': 'FIXED',  'enc': 'ascii', 'len': 12},
    38: {'type': 'FIXED',  'enc': 'ascii', 'len': 6},
    39: {'type': 'FIXED',  'enc': 'ascii', 'len': 2},
    41: {'type': 'FIXED',  'enc': 'ascii', 'len': 8},
    42: {'type': 'FIXED',  'enc': 'ascii', 'len': 15},
    45: {'type': 'LLVAR',  'enc': 'ascii'},
    46: {'type': 'LLLVAR', 'enc': 'ascii'},
    48: {'type': 'LLLVAR', 'enc': 'ascii'},
    49: {'type': 'FIXED',  'enc': 'ascii', 'len': 3},   # Moneda: ASCII 3 bytes "032"
    52: {'type': 'FIXED',  'enc': 'binary', 'len': 8},
    54: {'type': 'LLLVAR', 'enc': 'ascii'},
    55: {'type': 'LLLVAR', 'enc': 'ascii'},
    59: {'type': 'LLLVAR', 'enc': 'ascii'},
    60: {'type': 'LLLVAR', 'enc': 'ascii'},
    62: {'type': 'LLLVAR', 'enc': 'ascii'},
    63: {'type': 'LLLVAR', 'enc': 'ascii'},
    90: {'type': 'FIXED',  'enc': 'bcd',  'dig': 42},
}


def _encode_field(fnum, value):
    fdef = FIELD_DEFS.get(fnum)
    if not fdef:
        raise ValueError('Campo %d no definido' % fnum)

    ftype = fdef['type']
    enc = fdef['enc']

    if ftype == 'FIXED':
        if enc == 'bcd':
            padded = value.zfill(fdef['dig'])[:fdef['dig']]
            return _str_to_bcd(padded)
        elif enc == 'ascii':
            padded = value.ljust(fdef['len'])[:fdef['len']]
            return padded.encode('ascii')
        elif enc == 'binary':
            clean = re.sub(r'[^0-9A-Fa-f]', '', value)
            return bytes.fromhex(clean.ljust(fdef['len'] * 2, '0')[:fdef['len'] * 2])

    elif ftype == 'LLVAR':
        if enc == 'bcd':
            # Campo 2 (PAN): longitud = cantidad de digitos del PAN
            pan_digits = re.sub(r'[^0-9]', '', value)
            data_len = len(pan_digits)
            len_byte = _str_to_bcd('%02d' % data_len)
            # PAN en BCD, pad con F si impar
            bcd_str = pan_digits
            if len(bcd_str) % 2:
                bcd_str += 'F'
            return len_byte + bytes.fromhex(bcd_str)

        elif enc == 'track2':
            # Campo 35 (Track2): longitud = cantidad de nibbles
            # Convertir = a D, pad con F si impar
            t2 = value.upper().replace('=', 'D')
            data_len = len(t2)
            len_byte = _str_to_bcd('%02d' % data_len)
            if len(t2) % 2:
                t2 += 'F'
            return len_byte + bytes.fromhex(t2)

        else:  # ascii
            data_len = len(value)
            len_byte = _str_to_bcd('%02d' % data_len)
            return len_byte + value.encode('ascii')

    elif ftype == 'LLLVAR':
        # 2 bytes longitud BCD + data ASCII
        data_len = len(value)
        len_bytes = _str_to_bcd('%04d' % data_len)
        return len_bytes + value.encode('ascii')

    raise ValueError('Formato no soportado: %s/%s campo %d' % (ftype, enc, fnum))


def build_message(mti, tpdu, fields):
    tpdu_bytes = bytes.fromhex(tpdu)
    mti_bytes = _str_to_bcd(mti)

    field_nums = sorted(fields.keys())
    bitmap = _build_bitmap(field_nums)

    body = b''
    for fnum in field_nums:
        body += _encode_field(fnum, fields[fnum])

    message = tpdu_bytes + mti_bytes + bitmap + body
    length = struct.pack('>H', len(message))
    return length + message


def parse_response(data):
    if len(data) < 15:
        return {'error': 'Respuesta muy corta: %d bytes' % len(data)}

    tpdu = data[:5].hex().upper()
    mti = _bcd_to_str(data[5:7])
    present = _parse_bitmap(data[7:15])

    fields = {}
    pos = 15

    for fnum in present:
        fdef = FIELD_DEFS.get(fnum)
        if not fdef:
            fields[fnum] = '[UNKNOWN F%d]' % fnum
            break

        try:
            ftype = fdef['type']
            enc = fdef['enc']

            if ftype == 'FIXED':
                if enc == 'bcd':
                    blen = (fdef['dig'] + 1) // 2
                    fields[fnum] = _bcd_to_str(data[pos:pos+blen])[:fdef['dig']]
                    pos += blen
                elif enc == 'ascii':
                    fields[fnum] = data[pos:pos+fdef['len']].decode('ascii', errors='replace')
                    pos += fdef['len']
                elif enc == 'binary':
                    fields[fnum] = data[pos:pos+fdef['len']].hex().upper()
                    pos += fdef['len']

            elif ftype == 'LLVAR':
                ll = int(_bcd_to_str(data[pos:pos+1]))
                pos += 1
                if enc in ('bcd', 'track2'):
                    blen = (ll + 1) // 2
                    fields[fnum] = _bcd_to_str(data[pos:pos+blen])[:ll]
                    pos += blen
                else:
                    fields[fnum] = data[pos:pos+ll].decode('ascii', errors='replace')
                    pos += ll

            elif ftype == 'LLLVAR':
                ll = int(_bcd_to_str(data[pos:pos+2]))
                pos += 2
                fields[fnum] = data[pos:pos+ll].decode('ascii', errors='replace')
                pos += ll

        except Exception as e:
            fields[fnum] = '[ERROR: %s]' % e
            break

    return {'tpdu': tpdu, 'mti': mti, 'bitmap_fields': present, 'fields': fields}


def build_echo_test(terminal_id, merchant_id, nii='0112'):
    now = datetime.now()
    tpdu = '60%s0000' % nii.zfill(4)[:4]
    fields = {
        3:  '990000',
        7:  now.strftime('%m%d%H%M%S'),
        11: '000001',
        12: now.strftime('%H%M%S'),
        13: now.strftime('%m%d'),
        24: nii.zfill(4)[:4],
        41: terminal_id.ljust(8)[:8],
        42: merchant_id.ljust(15)[:15],
        60: 'WPH0001',
    }
    return build_message('0800', tpdu, fields)

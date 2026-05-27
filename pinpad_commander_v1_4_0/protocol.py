
import binascii

def hexlify(b: bytes) -> str:
    return ' '.join(f'{x:02X}' for x in b)

def unhexlify(s: str) -> bytes:
    s = s.replace(' ', '').replace('\n', '').replace('\t', '')
    try:
        return binascii.unhexlify(s)
    except binascii.Error as e:
        raise ValueError(f"Cadena hex inválida: {e}")

class FrameCodec:
    def __init__(self, stx=0x02, etx=0x03, fs=0x1C):
        self.stx = stx
        self.etx = etx
        self.fs = fs

    @staticmethod
    def lrc(data: bytes) -> int:
        x = 0
        for b in data:
            x ^= b
        return x & 0xFF

    def build_frame(self, cid: str, fields):
        body = cid.encode('ascii')
        if fields:
            joined = bytes([self.fs]).join([str(f).encode('ascii', errors='ignore') for f in fields])
            body += joined
        body += bytes([self.etx])
        lrc_val = self.lrc(body)
        return bytes([self.stx]) + body + bytes([lrc_val])

    def validate_lrc(self, frame: bytes) -> bool:
        if not frame or len(frame) < 4:
            return False
        calc = self.lrc(frame[1:-1])
        return calc == frame[-1]

    def extract(self, frame: bytes):
        if not self.validate_lrc(frame):
            raise ValueError("LRC inválido")
        if frame[0] != self.stx:
            raise ValueError("STX inválido")
        if frame[-2] != self.etx:
            raise ValueError("ETX inválido")
        inner = frame[1:-2]
        if len(inner) < 3:
            raise ValueError("Frame muy corto")
        cid = inner[:3].decode('ascii', errors='replace')
        payload = inner[3:]
        return cid, payload

class FSParser:
    def __init__(self, fs=0x1C):
        self.fs = fs

    def parse(self, payload: bytes):
        parts = payload.split(bytes([self.fs])) if payload else [b'']
        out = [p.decode('ascii', errors='ignore') for p in parts]
        if out and out[0] == '':
            out = out[1:]
        return out

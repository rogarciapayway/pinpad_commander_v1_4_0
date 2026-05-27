"""
Motor de transacciones ISO 8583

Formatos verificados contra trazas reales de clientes homologados.
"""

import json
import os
import re
import random
import logging
from datetime import datetime

from .iso8583_builder import build_message, build_echo_test, parse_response

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARAMETRIA_DIR = os.path.join(BASE_DIR, 'parametria')
CONFIG_ISO_DIR = os.path.join(BASE_DIR, 'serverISO', 'configIso')


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_merchants():
    return _load_json(os.path.join(PARAMETRIA_DIR, 'merchants.json'))

def load_acquirer_groups():
    return _load_json(os.path.join(PARAMETRIA_DIR, 'acquirerGroup.json'))

def load_spp_config():
    return _load_json(os.path.join(PARAMETRIA_DIR, 'config.json'))

def load_codigos_respuesta():
    return _load_json(os.path.join(CONFIG_ISO_DIR, 'campos_iso', 'codigos_respuesta.json'))


# NII por marca - se carga desde nii_config.json
def _load_nii_config():
    nii_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nii_config.json')
    try:
        with open(nii_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('nii_por_marca', {}), data.get('nii_default', '0721')
    except Exception as e:
        log.warning('No se pudo cargar nii_config.json: %s', e)
        return {}, '0721'

_NII_MARCA, _NII_DEFAULT = _load_nii_config()
NII_POR_MARCA = _NII_MARCA or {
    'Visa': '0721',
    'MasterCard': '0721',
    'Maestro': '0721',
    'Cabal': '0721',
    'Discover': '0721',
    'Amex': '0721',
}

# POS Entry Mode (campo 22, 4 digitos BCD)
POS_ENTRY = {
    'manual': '0011',
    'banda': '0021',
    'chip': '0051',
    'contactless': '0071',
}

CAPACIDAD = {'manual': '1', 'banda': '2', 'chip': '5', 'contactless': '7'}


def formato_monto(monto):
    return str(int(round(monto * 100))).zfill(12)

def gen_trace():
    return str(random.randint(1, 999999)).zfill(6)

def gen_ticket():
    return str(random.randint(1, 9999)).zfill(4)

def gen_track2(pan, venc=None):
    if not pan:
        return ''
    v = venc or '2812'
    return '%s=%s101' % (pan, v)


def build_campo_59(modo):
    """Campo 59: producto 021 mandatorio."""
    cap = CAPACIDAD.get(modo, '7')
    return '0210001004070' + cap


class ParametriaResolver:
    def __init__(self):
        self.merchants = []
        self.acquirer_groups = []
        self.spp_config = {}
        self._loaded = False

    def load(self):
        try:
            self.merchants = load_merchants()
            self.acquirer_groups = load_acquirer_groups()
            self.spp_config = load_spp_config()
            self._loaded = True
        except Exception as e:
            log.warning('No se pudo cargar parametria SPP: %s', e)

    def resolve(self, marca, terminal_override=None, merchant_override=None):
        if not self._loaded:
            self.load()

        merchant_entry = None
        marca_upper = marca.upper()
        for m in self.merchants:
            if marca_upper in m.get('name', '').upper():
                merchant_entry = m
                break

        acq_group = None
        if merchant_entry:
            agid = merchant_entry.get('acquirerGroupId')
            for ag in self.acquirer_groups:
                if ag.get('acquirerGroupId') == agid:
                    acq_group = ag
                    break

        terminal_id = terminal_override or (acq_group or {}).get('terminalId', '12345678')
        merchant_id = merchant_override or (merchant_entry or {}).get('commerce', '03659307')
        host = (acq_group or {}).get('ip', 'ws1.prismamp.com')
        port = int((acq_group or {}).get('ipPort', '8443'))

        # NII segun marca de tarjeta
        nii = NII_POR_MARCA.get(marca, _NII_DEFAULT)
        tpdu = '60%s0000' % nii

        return {
            'terminal_id': terminal_id.ljust(8)[:8],
            'merchant_id': merchant_id.ljust(15)[:15],
            'nii': nii,
            'host': host,
            'port': port,
            'tpdu': tpdu,
        }


class TransactionBuilder:
    def __init__(self):
        self.parametria = ParametriaResolver()
        self._trace_counter = random.randint(1, 500000)
        self._ticket_counter = random.randint(1, 5000)

    def load_config(self):
        self.parametria.load()

    def next_trace(self):
        self._trace_counter = (self._trace_counter + 1) % 1000000
        return str(self._trace_counter).zfill(6)

    def next_ticket(self):
        self._ticket_counter = (self._ticket_counter + 1) % 10000
        if self._ticket_counter == 0:
            self._ticket_counter = 1
        return str(self._ticket_counter).zfill(4)

    def build_transaction(self, params):
        self.parametria.load()

        tipo_msg = params.get('tipo_mensaje', '0200')
        modo = params.get('modo', 'manual')
        marca = params.get('marca', 'Visa')
        pan = params.get('pan', '')
        monto = params.get('monto', 100.0)
        codigo_proc = params.get('codigo_proc', '000000')

        conn = self.parametria.resolve(
            marca,
            terminal_override=params.get('terminal_id'),
            merchant_override=params.get('merchant_id')
        )

        now = datetime.now()
        trace = self.next_trace()
        ticket = self.next_ticket()
        venc = params.get('vencimiento', '')

        # --- Echo Test ---
        if tipo_msg == '0800':
            return build_echo_test(conn['terminal_id'], conn['merchant_id'], conn['nii'])

        # --- Cierre de Lote ---
        if tipo_msg == '0500':
            fields = {
                3: '920000', 7: now.strftime('%m%d%H%M%S'), 11: trace,
                12: now.strftime('%H%M%S'), 13: now.strftime('%m%d'),
                15: now.strftime('%m%d'), 24: conn['nii'],
                41: conn['terminal_id'], 42: conn['merchant_id'],
                60: 'PAYWAY_COE',
            }
            return build_message('0500', conn['tpdu'], fields)

        # --- Campos base para 0200/0220/0400 ---
        fields = {
            3: codigo_proc,
            4: formato_monto(monto),
            7: now.strftime('%m%d%H%M%S'),
            11: trace,
            12: now.strftime('%H%M%S'),
            13: now.strftime('%m%d'),
            22: POS_ENTRY.get(modo, '0011'),
            24: conn['nii'],
            25: '00',
            41: conn['terminal_id'],
            42: conn['merchant_id'],
            49: '032',
        }

        # Campos transaccionales comunes (no para reverso)
        if tipo_msg != '0400':
            fields[48] = params.get('cuotas', '001')
            fields[59] = build_campo_59(modo)
            fields[60] = 'PAYWAY_COE'
            fields[62] = ticket

        # --- Campos por modo de ingreso ---
        if modo == 'manual':
            if not pan:
                raise ValueError('PAN requerido para modo manual')
            fields[2] = pan
            if venc:
                fields[14] = venc
            fields[19] = '0032'
            cvv = params.get('cvv', '')
            if cvv:
                fields[55] = cvv

        elif modo == 'banda':
            fields[19] = '0032'
            fields[35] = params.get('track2') or gen_track2(pan, venc)
            track1 = params.get('track1', '')
            if track1:
                fields[45] = track1
            else:
                fields[46] = '1'

        elif modo == 'chip':
            fields[23] = params.get('secuencia', '0000')
            fields[35] = params.get('track2') or gen_track2(pan, venc)
            emv = params.get('emv_data', '')
            if emv:
                fields[55] = emv
            fields[46] = '1'

        elif modo == 'contactless':
            fields[19] = '0032'
            fields[23] = params.get('secuencia', '0000')
            fields[35] = params.get('track2') or gen_track2(pan, venc)
            emv = params.get('emv_data', '')
            if emv:
                fields[55] = emv
            fields[46] = '1'

        # PIN block
        if params.get('pin_block'):
            fields[52] = params['pin_block']

        # Cashback en campo 54
        if params.get('cashback'):
            fields[54] = formato_monto(params['cashback'])

        # Reverso
        if tipo_msg == '0400':
            fields[90] = params.get('original_data', '020011000000'.ljust(42, '0'))
            for f in [48, 59, 60, 62, 45, 46, 55]:
                fields.pop(f, None)

        # Advice
        if tipo_msg == '0220':
            fields[17] = now.strftime('%m%d')
            if params.get('ref_number'):
                fields[37] = params['ref_number']
            if params.get('auth_code'):
                fields[38] = params['auth_code']

        # Limpiar vacios
        fields = {k: v for k, v in fields.items() if v}

        return build_message(tipo_msg, conn['tpdu'], fields)

    def build_and_get_info(self, params):
        marca = params.get('marca', 'Visa')
        conn = self.parametria.resolve(
            marca,
            terminal_override=params.get('terminal_id'),
            merchant_override=params.get('merchant_id')
        )
        msg = self.build_transaction(params)
        return {
            'message': msg,
            'connection': conn,
            'metadata': {
                'tipo_mensaje': params.get('tipo_mensaje', '0200'),
                'modo': params.get('modo', 'manual'),
                'marca': marca,
                'codigo_proc': params.get('codigo_proc', '000000'),
                'monto': params.get('monto', 100.0),
                'trace': str(self._trace_counter).zfill(6),
                'ticket': str(self._ticket_counter).zfill(4),
            }
        }


class TransactionManager:
    def __init__(self):
        self.builder = TransactionBuilder()
        self.codigos_respuesta = {}

    def load(self):
        self.builder.load_config()
        try:
            data = load_codigos_respuesta()
            self.codigos_respuesta = data.get('codigos_respuesta', {})
        except Exception:
            self.codigos_respuesta = {}

    def get_response_description(self, code):
        entry = self.codigos_respuesta.get(code, {})
        if isinstance(entry, dict):
            return entry.get('descripcion', 'Desconocido')
        return str(entry)

    def execute(self, params, tls_client):
        info = self.builder.build_and_get_info(params)
        msg = info['message']
        conn = info['connection']
        req_hex = ' '.join('%02X' % b for b in msg)

        try:
            response_data = tls_client.send_and_receive(msg, timeout=30.0)
        except Exception as e:
            return {'success': False, 'error': str(e), 'request_hex': req_hex,
                    'metadata': info['metadata'], 'connection': conn}

        if not response_data:
            return {'success': False, 'error': 'Sin respuesta (timeout)',
                    'request_hex': req_hex, 'metadata': info['metadata'], 'connection': conn}

        resp_hex = ' '.join('%02X' % b for b in response_data)
        parsed = parse_response(response_data)
        resp_code = parsed.get('fields', {}).get(39, 'XX')

        return {
            'success': True,
            'request_hex': req_hex,
            'response_hex': resp_hex,
            'parsed': parsed,
            'response_code': resp_code,
            'response_description': self.get_response_description(resp_code),
            'metadata': info['metadata'],
            'connection': conn,
        }

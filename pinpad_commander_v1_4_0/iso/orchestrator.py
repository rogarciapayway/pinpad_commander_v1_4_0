"""
Orquestador de transaccion integrada PinPad + ISO 8583

Flujo completo:
  1. Y19 al PinPad -> lee tarjeta (chip/banda/ctls/manual)
  2. Extrae datos de la respuesta Y19
  3. Resuelve parametria (terminal, merchant, NII) segun marca
  4. Construye mensaje ISO 8583 0200
  5. Envia via TLS al host
  6. Parsea respuesta 0210
  7. Si chip/contactless -> construye Y03 para confirmar EMV
  8. Retorna resultado completo

Uso desde Commander:
    orchestrator = TransactionOrchestrator()
    orchestrator.configure(terminal_id='74000025', merchant_id='03659307')
    result = orchestrator.process_y19_response(parsed_y19, monto=100.0)
    if result['needs_y03']:
        y03_params = result['y03_params']
        # enviar Y03 al PinPad con y03_params
"""

import logging
from .pinpad_bridge import (
    extract_y19_data, build_iso_params, build_y03_params,
    needs_y03, get_transaction_summary, MDI_TO_MODE
)
from .transaction_engine import TransactionManager
from .tls_client import TLSClient

log = logging.getLogger(__name__)


class TransactionOrchestrator:
    """Orquesta el flujo completo PinPad -> ISO 8583 -> Host."""

    def __init__(self):
        self.tx_manager = TransactionManager()
        self.tls_client = None
        self.terminal_id = None
        self.merchant_id = None
        self.host = 'ws1.prismamp.com'
        self.port = 8443
        self._last_y19_data = None
        self._last_iso_result = None

    def configure(self, terminal_id=None, merchant_id=None,
                  host=None, port=None):
        if terminal_id:
            self.terminal_id = terminal_id
        if merchant_id:
            self.merchant_id = merchant_id
        if host:
            self.host = host
        if port:
            self.port = port

    def load(self):
        self.tx_manager.load()

    def connect_host(self):
        # Siempre crear conexion nueva para cada operacion
        if self.tls_client:
            try:
                self.tls_client.disconnect()
            except Exception:
                pass
        self.tls_client = TLSClient(self.host, self.port, timeout=30.0)
        self.tls_client.connect()
        log.info('Conectado a %s:%d', self.host, self.port)
        return True

    def disconnect_host(self):
        if self.tls_client:
            self.tls_client.disconnect()
            self.tls_client = None

    def process_y19_response(self, parsed_y19, monto=100.0,
                              codigo_proc='000000', marca='Visa',
                              cuotas='001', cashback=None, campo_59=None):
        """
        Procesar respuesta Y19 y ejecutar transaccion ISO completa.
        """
        if not self.tx_manager.codigos_respuesta:
            self.load()

        # 1. Extraer datos del Y19
        log.info('[STEP 1] Extrayendo datos Y19...')
        y19_data = extract_y19_data(parsed_y19)
        self._last_y19_data = y19_data
        mdi = y19_data.get('mdi', 'M')

        log.info('[STEP 1] OK: MDI=%s PAN=%s Track2=%s EMV=%d',
                 mdi, y19_data.get('pan_masked', '****'),
                 'SI' if y19_data.get('track2') else 'NO',
                 len(y19_data.get('emv_tags', '')))

        if not y19_data.get('pan') and not y19_data.get('track2'):
            if y19_data.get('emv_tags') and mdi in ('C', 'L'):
                log.info('Chip/CTLS sin PAN claro - usando track2 encriptado + EMV')
                if y19_data.get('track2_encrypted'):
                    y19_data['track2'] = y19_data['track2_encrypted']
                if y19_data.get('pan_masked'):
                    y19_data['pan'] = y19_data['pan_masked'].replace('*', '0')
            else:
                return {
                    'success': False,
                    'error': 'No se pudo extraer PAN ni Track2 de la respuesta Y19',
                    'y19_data': y19_data,
                }

        # 2. Construir parametros ISO
        log.info('[STEP 2] Construyendo params ISO...')
        tx_config = {
            'monto': monto,
            'codigo_proc': codigo_proc,
            'terminal_id': self.terminal_id,
            'merchant_id': self.merchant_id,
            'marca': marca,
            'cuotas': cuotas,
            'cashback': cashback,
            'campo_59': campo_59,
        }
        try:
            iso_params = build_iso_params(y19_data, tx_config)
            log.info('[STEP 2] OK: modo=%s pan=%s...', iso_params.get('modo'), iso_params.get('pan', '')[:6])
        except Exception as e:
            log.error('[STEP 2] FAIL: %s', e)
            return {
                'success': False,
                'error': 'Error construyendo params ISO: %s' % e,
                'y19_data': y19_data,
            }

        # 3. Conectar al host
        log.info('[STEP 3] Conectando TLS a %s:%d...', self.host, self.port)
        try:
            self.connect_host()
            log.info('[STEP 3] OK: Conectado')
        except Exception as e:
            log.error('[STEP 3] FAIL: %s', e)
            return {
                'success': False,
                'error': 'Error conectando al host: %s' % e,
                'y19_data': y19_data,
            }

        # 4. Ejecutar transaccion ISO
        log.info('[STEP 4] Ejecutando ISO 0200...')
        try:
            iso_result = self.tx_manager.execute(iso_params, self.tls_client)
            log.info('[STEP 4] OK: success=%s code=%s',
                     iso_result.get('success'), iso_result.get('response_code', '?'))
        except Exception as e:
            log.error('[STEP 4] FAIL: %s', e)
            return {
                'success': False,
                'error': 'Error ejecutando ISO: %s' % e,
                'y19_data': y19_data,
            }
        self._last_iso_result = iso_result

        # 5. Determinar si necesita Y03 (solo si aprobada)
        y03_needed = False
        y03_params = None
        if not iso_result.get('success'):
            return {
                'success': False,
                'error': iso_result.get('error', 'Sin respuesta del host'),
                'y19_data': y19_data,
                'iso_result': iso_result,
                'needs_y03': False,
                'y03_params': None,
                'summary': get_transaction_summary(y19_data, iso_result),
            }

        resp_code = iso_result.get('parsed', {}).get('fields', {}).get(39, 'XX')
        if needs_y03(mdi) and resp_code in ('00', '11', '85'):
            y03_needed = True
            y03_params = build_y03_params(iso_result.get('parsed', {}))

        # 6. Generar resumen
        summary = get_transaction_summary(y19_data, iso_result)

        return {
            'success': iso_result.get('success', False),
            'y19_data': y19_data,
            'iso_result': iso_result,
            'needs_y03': y03_needed,
            'y03_params': y03_params,
            'summary': summary,
        }

    def echo_test(self):
        """Ejecutar Echo Test para validar conectividad."""
        if not self.tx_manager.codigos_respuesta:
            self.load()

        try:
            self.connect_host()
        except Exception as e:
            return {'success': False, 'error': str(e)}

        from .transaction_engine import _NII_DEFAULT
        from .iso8583_builder import build_echo_test, parse_response
        # Resolver NII de echo desde parametria
        conn = self.tx_manager.builder.parametria.resolve('Visa',
            terminal_override=self.terminal_id, echo=True)
        terminal = conn['terminal_id']
        merchant = self.merchant_id or '03659307'
        nii = conn['nii']
        msg = build_echo_test(terminal, merchant, nii)

        try:
            response_data = self.tls_client.send_and_receive(msg, timeout=20.0)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        if not response_data:
            return {'success': False, 'error': 'Sin respuesta (timeout)'}

        parsed = parse_response(response_data)
        return {'success': True, 'parsed': parsed}

    def send_raw_transaction(self, params):
        """
        Enviar transaccion ISO directa (sin PinPad).
        Util para pruebas manuales.
        """
        if not self.tx_manager.codigos_respuesta:
            self.load()

        if not params.get('terminal_id'):
            params['terminal_id'] = self.terminal_id
        if not params.get('merchant_id'):
            params['merchant_id'] = self.merchant_id

        try:
            self.connect_host()
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return self.tx_manager.execute(params, self.tls_client)

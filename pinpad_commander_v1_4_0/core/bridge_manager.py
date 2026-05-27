"""
Gestor del Bridge ISO para PinPad Commander.

Cuando el bridge esta ON, despues de cada Y19 exitoso:
1. Extrae datos de la respuesta
2. Arma ISO 0200
3. Envia al host via TLS
4. Muestra resultado en pestana ISO 8583
5. Si chip/ctls, prepara Y03
"""

import json
import threading
import logging
from datetime import datetime

from iso.orchestrator import TransactionOrchestrator
from iso.pinpad_bridge import extract_y19_data, MDI_TO_MODE, needs_y03
from iso.iso_logger import log_transaction

log = logging.getLogger(__name__)


class BridgeManager:
    def __init__(self, app):
        self.app = app
        self.orchestrator = TransactionOrchestrator()
        self._loaded = False
        self._pending_manual_y19 = None

    def _ensure_loaded(self):
        if not self._loaded:
            try:
                self.orchestrator.load()
                self._loaded = True
            except Exception as e:
                log.warning('Error cargando config ISO: %s', e)

    def is_enabled(self):
        try:
            return self.app.window.connection_panel.bridge_var.get()
        except Exception:
            return False

    def _get_terminal(self):
        try:
            return self.app.window.connection_panel.bridge_terminal_entry.get().strip() or '74000025'
        except Exception:
            return '74000025'

    def _get_merchant(self):
        try:
            return self.app.window.connection_panel.bridge_merchant_entry.get().strip() or '03659307'
        except Exception:
            return '03659307'

    def _update_tls_status(self, text, color='gray50'):
        try:
            self.app.window.communication_panel.iso_tls_label.configure(
                text='TLS: %s' % text, text_color=color)
        except Exception:
            pass

    def _log_iso(self, text, tag=None):
        try:
            widget = self.app.window.communication_panel.iso_text
            widget.insert('end', text, tag)
            widget.see('end')
        except Exception as e:
            log.debug('Error logging ISO: %s', e)

    def _log_iso_line(self, text, tag=None):
        self._log_iso(text + '\n', tag)

    def echo_test(self):
        self._ensure_loaded()
        terminal = self._get_terminal()
        merchant = self._get_merchant()

        self.orchestrator.configure(terminal_id=terminal, merchant_id=merchant)

        self._log_iso_line('=' * 50, 'dim')
        self._log_iso_line('[%s] Echo Test 0800' % datetime.now().strftime('%H:%M:%S'), 'header')
        self._log_iso_line('  Terminal: %s  Merchant: %s' % (terminal, merchant))
        self._update_tls_status('Conectando...', '#d29922')

        def _run():
            try:
                result = self.orchestrator.echo_test()
                self.app.window.after(0, lambda: self._show_echo_result(result))
            except Exception as e:
                self.app.window.after(0, lambda: self._show_echo_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _show_echo_result(self, result):
        if result.get('success'):
            parsed = result.get('parsed', {})
            code = parsed.get('fields', {}).get(39, 'OK')
            mti = parsed.get('mti', '?')
            self._log_iso_line('  Respuesta: %s (MTI=%s)' % (code, mti), 'ok')
            self._update_tls_status('OK', '#3fb950')
            self.app.window.status.set('Echo Test ISO: OK')
        else:
            self._log_iso_line('  Error: %s' % result.get('error', '?'), 'fail')
            self._update_tls_status('FAIL', '#f85149')
        self._log_iso_line('')

    def _show_echo_error(self, error):
        self._log_iso_line('  Error: %s' % error, 'fail')
        self._update_tls_status('ERROR', '#f85149')
        self._log_iso_line('')

    def _extract_monto(self, parsed_y19):
        """Extraer monto: primero del tag EMV 9F02, luego del campo IMP enviado."""
        monto = 0.0
        try:
            fields = parsed_y19.get('fields', {})
            cpg = fields.get('CPG', {})
            if isinstance(cpg, dict):
                tlv = cpg.get('tlv', {})
                if isinstance(tlv, dict) and tlv.get('9F02'):
                    monto = int(tlv['9F02']) / 100.0
        except Exception:
            pass
        if monto == 0.0:
            try:
                last_sent = self.app._last_sent.get('Y19 Transaccion', {})
                if not last_sent:
                    last_sent = self.app._last_sent.get('Y19 Transacci\u00f3n', {})
                imp_raw = last_sent.get('IMP', '')
                if imp_raw:
                    if '.' in str(imp_raw):
                        monto = float(imp_raw)
                    elif len(str(imp_raw)) >= 3:
                        monto = int(imp_raw) / 100.0
            except Exception:
                pass
        if monto == 0.0:
            monto = 100.0  # fallback
        return monto

    def process_y19_response(self, parsed_y19):
        """
        Hook llamado despues de un Y19 exitoso.
        Si bridge esta ON, ejecuta el flujo ISO en background.
        Para modo manual (MDI=M), solo guarda contexto y espera Y02.
        """
        if not self.is_enabled():
            return

        if not isinstance(parsed_y19, dict) or parsed_y19.get('cid') != 'Y19':
            return

        # Detectar MDI
        fields = parsed_y19.get('fields', {})
        mdi = fields.get('MDI', '?')

        # Para modo manual, guardar contexto y esperar Y02
        if mdi == 'M':
            self._pending_manual_y19 = parsed_y19
            terminal = self._get_terminal()
            merchant = self._get_merchant()
            monto = self._extract_monto(parsed_y19)
            marca = self._detect_marca(parsed_y19)
            self.app.window.after(0, lambda: self._log_bridge_header(
                mdi, 'manual', marca, monto, terminal, merchant))
            self.app.window.after(0, lambda: self._log_iso_line(
                '  Esperando Y02 para obtener PAN...', 'dim'))
            log.info('[BRIDGE] MDI=M, esperando Y02 para PAN completo')
            return

        # Para chip/contactless/banda, procesar directamente
        self._pending_manual_y19 = None
        terminal = self._get_terminal()
        merchant = self._get_merchant()
        monto = self._extract_monto(parsed_y19)

        def _run():
            try:
                self._ensure_loaded()
                self.orchestrator.configure(terminal_id=terminal, merchant_id=merchant)
                marca = self._detect_marca(parsed_y19)
                fields = parsed_y19.get('fields', {})
                mdi = fields.get('MDI', '?')
                modo = MDI_TO_MODE.get(mdi, '?')

                self.app.window.after(0, lambda: self._log_bridge_header(
                    mdi, modo, marca, monto, terminal, merchant))

                log.info('[BRIDGE] Llamando orchestrator: marca=%s mdi=%s monto=%.2f', marca, mdi, monto)
                result = self.orchestrator.process_y19_response(
                    parsed_y19=parsed_y19,
                    monto=monto,
                    marca=marca,
                    cuotas='001'
                )
                log.info('[BRIDGE] Orchestrator retorno: success=%s', result.get('success') if result else 'NONE')
                self.app.window.after(0, lambda: self._show_iso_result(result, parsed_y19))
            except Exception as e:
                import traceback
                err_detail = traceback.format_exc()
                log.error('[BRIDGE] Exception en thread: %s\n%s', e, err_detail)
                self.app.window.after(0, lambda: self._show_iso_error('%s' % e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def process_y02_response(self, parsed_y02):
        """
        Hook llamado despues de un Y02 exitoso.
        Si hay un Y19 manual pendiente, combina datos y envia al host.
        """
        if not self.is_enabled():
            return

        if not self._pending_manual_y19:
            return

        parsed_y19 = self._pending_manual_y19
        self._pending_manual_y19 = None

        terminal = self._get_terminal()
        merchant = self._get_merchant()
        monto = self._extract_monto(parsed_y19)

        def _run():
            try:
                self._ensure_loaded()
                self.orchestrator.configure(terminal_id=terminal, merchant_id=merchant)
                marca = self._detect_marca(parsed_y19)

                # Combinar datos Y19 + Y02 para modo manual
                combined = self._combine_y19_y02(parsed_y19, parsed_y02)

                # Verificar que se obtuvo PAN
                from iso.pinpad_bridge import extract_y19_data
                y19_data = extract_y19_data(combined)
                if not y19_data.get('pan'):
                    # Debug: mostrar estructura Y02 para diagnostico
                    y02_fields = parsed_y02.get('fields', {})
                    tarj = y02_fields.get('tarj_enmascarada', {})
                    tarj_type = type(tarj).__name__
                    rsa_keys = []
                    if isinstance(tarj, dict):
                        rsa = tarj.get('rsa', {})
                        if isinstance(rsa, dict):
                            rsa_keys = list(rsa.keys())
                    err_msg = 'No se pudo extraer PAN del Y02. tarj_type=%s rsa_keys=%s' % (tarj_type, rsa_keys)
                    log.error('[BRIDGE] %s', err_msg)
                    self.app.window.after(0, lambda: self._log_iso_line(
                        '  ERROR: %s' % err_msg, 'fail'))
                    self.app.window.after(0, lambda: self._log_iso_line(''))
                    return

                self.app.window.after(0, lambda: self._log_iso_line(
                    '  Y02 recibido - PAN obtenido, enviando ISO...', 'dim'))

                log.info('[BRIDGE] Manual: Y02 recibido, enviando ISO. marca=%s monto=%.2f pan=%s****',
                         marca, monto, y19_data['pan'][:6])
                result = self.orchestrator.process_y19_response(
                    parsed_y19=combined,
                    monto=monto,
                    marca=marca,
                    cuotas='001'
                )
                log.info('[BRIDGE] Orchestrator retorno: success=%s', result.get('success') if result else 'NONE')
                self.app.window.after(0, lambda: self._show_iso_result(result, combined))
            except Exception as e:
                import traceback
                err_detail = traceback.format_exc()
                log.error('[BRIDGE] Exception en thread Y02: %s\n%s', e, err_detail)
                self.app.window.after(0, lambda: self._show_iso_error('%s' % e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _combine_y19_y02(self, parsed_y19, parsed_y02):
        """
        Combinar datos del Y19 y Y02 para modo manual.
        Y19 tiene: MDI, tarj_enmasc (enmascarado), monto
        Y02 tiene: PAN RSA decrypted, FDV, CVV
        """
        import re as _re
        combined = dict(parsed_y19)
        combined['fields'] = dict(parsed_y19.get('fields', {}))

        y02_fields = parsed_y02.get('fields', {})
        pan_found = None

        # Extraer PAN del Y02 RSA decrypted
        tarj = y02_fields.get('tarj_enmascarada', {})
        if isinstance(tarj, dict):
            rsa = tarj.get('rsa', {})
            if isinstance(rsa, dict):
                # Track2 parseado del RSA
                t2 = rsa.get('rsa_track2', {})
                if t2 and t2.get('pan'):
                    combined['fields']['tc2'] = {'rsa': {'rsa_track2': t2}}
                    pan_found = t2['pan']
                    log.info('[BRIDGE] PAN del Y02 RSA track2: %s****', pan_found[:6])
                # Track1 parseado
                t1 = rsa.get('rsa_track1', {})
                if t1 and t1.get('pan') and not pan_found:
                    pan_found = t1['pan']
                # Si no hay track2 parseado, buscar PAN en rsa_plain_ascii
                if not pan_found:
                    ascii_out = rsa.get('rsa_plain_ascii', '')
                    if ascii_out:
                        # Intentar extraer PAN: puede ser solo digitos o track2 format
                        digits = _re.sub(r'[^0-9]', '', ascii_out.strip())
                        if 13 <= len(digits) <= 19:
                            pan_found = digits
                            log.info('[BRIDGE] PAN del Y02 RSA ascii directo: %s****', pan_found[:6])
                        elif len(digits) > 19:
                            # Puede tener padding, tomar primeros 16-19 digitos
                            # Buscar patron de PAN (empieza con 3,4,5,6)
                            m = _re.search(r'[3456]\d{12,18}', digits)
                            if m:
                                pan_found = m.group(0)
                                log.info('[BRIDGE] PAN del Y02 RSA ascii (regex): %s****', pan_found[:6])
                    # Tambien buscar en rsa_plain_hex (PAN en BCD)
                    if not pan_found:
                        hex_out = rsa.get('rsa_plain_hex', '')
                        if hex_out:
                            # PAN en BCD: buscar secuencia de digitos valida
                            clean = hex_out.upper().replace('F', '').replace(' ', '')
                            m = _re.search(r'[3456]\d{12,18}', clean)
                            if m:
                                pan_found = m.group(0)
                                log.info('[BRIDGE] PAN del Y02 RSA hex: %s****', pan_found[:6])

        # Si encontramos PAN pero no se creo tc2, inyectar manualmente
        if pan_found and 'tc2' not in combined['fields']:
            # Obtener vencimiento del Y02
            ven = y02_fields.get('ven', '') or combined['fields'].get('ven', '')
            yy = ven[:2] if len(ven) >= 2 else '28'
            mm = ven[2:4] if len(ven) >= 4 else '12'
            combined['fields']['tc2'] = {
                'rsa': {
                    'rsa_track2': {
                        'pan': pan_found,
                        'pan_mask': pan_found[:6] + '****' + pan_found[-4:],
                        'exp_yy': yy,
                        'exp_mm': mm,
                        'service_code': '201',
                        'discretionary': '0000000000',
                        'luhn_ok': True
                    }
                }
            }

        # FDV (vencimiento) del Y02
        ven = y02_fields.get('ven', '')
        if ven:
            combined['fields']['ven'] = ven

        # CDS (codigo seguridad/CVV) del Y02
        cod_seg = y02_fields.get('cod_seg', {})
        if isinstance(cod_seg, dict):
            rsa_cs = cod_seg.get('rsa', {})
            if isinstance(rsa_cs, dict):
                ascii_out = rsa_cs.get('rsa_plain_ascii', '')
                if ascii_out:
                    cvv_digits = _re.sub(r'[^0-9]', '', ascii_out.strip())
                    if 3 <= len(cvv_digits) <= 4:
                        combined['fields']['csv'] = cvv_digits
                        log.info('[BRIDGE] CVV del Y02: ***')

        return combined

    def _log_bridge_header(self, mdi, modo, marca, monto, terminal, merchant):
        """Log del header del bridge en la UI (llamar desde hilo principal)."""
        self._log_iso_line('=' * 50, 'dim')
        self._log_iso_line('[%s] Bridge ISO - Procesando Y19' % datetime.now().strftime('%H:%M:%S'), 'header')
        self._log_iso_line('  Modo: %s (%s)  Marca: %s  Monto: $%.2f' % (mdi, modo, marca, monto))
        self._log_iso_line('  Terminal: %s  Merchant: %s' % (terminal, merchant))
        self._update_tls_status('Enviando 0200...', '#d29922')

    def _show_iso_result(self, result, parsed_y19):
        if not result:
            self._log_iso_line('  ERROR: Resultado vacio', 'fail')
            self._update_tls_status('ERROR', '#f85149')
            self._log_iso_line('')
            return

        if not result.get('success'):
            error = result.get('error', 'Error desconocido')
            self._log_iso_line('  ERROR: %s' % error, 'fail')
            # Mostrar datos extraidos para debug
            y19_data = result.get('y19_data', {})
            if y19_data:
                self._log_iso_line('  Debug - PAN: %s' % y19_data.get('pan', 'NONE'), 'dim')
                self._log_iso_line('  Debug - Track2: %s' % ('SI' if y19_data.get('track2') else 'NO'), 'dim')
                self._log_iso_line('  Debug - EMV: %s' % ('SI' if y19_data.get('emv_tags') else 'NO'), 'dim')
                self._log_iso_line('  Debug - MDI: %s' % y19_data.get('mdi', '?'), 'dim')
            self._update_tls_status('ERROR', '#f85149')
            self.app.window.status.set('Bridge ISO: Error - %s' % error)

            # Grabar error en log diario
            try:
                fields = parsed_y19.get('fields', {}) if parsed_y19 else {}
                mdi_e = fields.get('MDI', '?')
                modo_e = MDI_TO_MODE.get(mdi_e, '?')
                marca_e = self._detect_marca(parsed_y19) if parsed_y19 else '?'
                log_transaction(result, marca_e, modo_e, mdi_e)
            except Exception:
                pass

            self._log_iso_line('')
            return

        summary = result.get('summary', {})
        iso = result.get('iso_result', {})
        parsed = iso.get('parsed', {})
        iso_fields = parsed.get('fields', {})
        code = summary.get('response_code', '??')
        desc = summary.get('response_desc', '')

        if code == '00':
            self._log_iso_line('  >> APROBADA <<', 'ok')
            self._update_tls_status('0210 OK (%s)' % code, '#3fb950')
        else:
            self._log_iso_line('  >> RESPUESTA: %s - %s <<' % (code, desc), 'fail')
            self._update_tls_status('0210 (%s)' % code, '#d29922')

        self._log_iso_line('  Auth: %s  Ref: %s' % (
            summary.get('auth_code', '-'), summary.get('ref_number', '-')), 'value')

        self._log_iso_line('  Campos respuesta:', 'dim')
        for fnum, fval in sorted(iso_fields.items()):
            self._log_iso('    F%03d: ' % fnum, 'field')
            self._log_iso_line(str(fval), 'value')

        if result.get('needs_y03'):
            y03 = result.get('y03_params', {})
            self._log_iso_line('')
            self._log_iso_line('  Requiere Y03 (EMV confirmation):', 'header')
            self._log_iso_line('    CAU=%s CRE=%s RCP=%s' % (
                y03.get('CAU', ''), y03.get('CRE', ''), y03.get('RCP', 'N')), 'value')
            self._auto_send_y03(y03)

        self.app.window.status.set('Bridge ISO: %s - %s' % (code, desc))

        # Grabar en log diario
        try:
            fields = parsed_y19.get('fields', {}) if parsed_y19 else {}
            mdi = fields.get('MDI', '?')
            modo_str = MDI_TO_MODE.get(mdi, '?')
            marca_str = self._detect_marca(parsed_y19) if parsed_y19 else '?'
            log_transaction(iso, marca_str, modo_str, mdi)
        except Exception as e:
            log.debug('Error grabando log ISO: %s', e)

        self._log_iso_line('')

    def _show_iso_error(self, error):
        self._log_iso_line('  ERROR: %s' % error, 'fail')
        self._update_tls_status('ERROR', '#f85149')
        self._log_iso_line('')

    def _auto_send_y03(self, y03_params):
        """Enviar Y03 automaticamente al PinPad con resultado del host."""
        if not self.app.comm.is_connected():
            self._log_iso_line('  [!] PinPad desconectado, no se puede enviar Y03', 'fail')
            return

        try:
            cau = y03_params.get('CAU', '      ')
            cre = y03_params.get('CRE', '00')
            rcp = y03_params.get('RCP', 'N')

            codec = self.app.comm.codec
            y03_frame = codec.build_frame('Y03', [cau + cre + rcp])

            self._log_iso_line('  Enviando Y03 al PinPad...', 'dim')
            self.app.comm.send_frame(y03_frame)
            self.app._log_hex('TX', y03_frame)

            # Leer ACK
            ack = self.app.comm.ser.read(1)
            if ack == b'\x06':
                self._log_iso_line('  Y03 ACK recibido', 'dim')

            # Leer respuesta Y03
            resp = self.app.comm.read_frame(timeout_override=30)
            if resp:
                self.app._log_hex('RX', resp)
                self._log_iso_line('  Y03 completado', 'ok')
            else:
                self._log_iso_line('  Y03 sin respuesta', 'fail')

        except Exception as e:
            self._log_iso_line('  Error Y03: %s' % e, 'fail')

    def _detect_marca(self, parsed_y19):
        """Detectar marca de tarjeta desde la respuesta Y19."""
        fields = parsed_y19.get('fields', {})

        # Por nombre (campo app_emv o nombre)
        for name_key in ('app_emv', 'nombre'):
            nombre = fields.get(name_key, '')
            if isinstance(nombre, str) and nombre.strip():
                n = nombre.upper()
                if 'VISA' in n or 'PAYWAVE' in n:
                    return 'Visa'
                if 'MASTER' in n or 'PAYPASS' in n:
                    return 'MasterCard'
                if 'MAESTRO' in n:
                    return 'Maestro'
                if 'CABAL' in n or 'DISCOVER' in n:
                    return 'Cabal'
                if 'AMEX' in n or 'AMERICAN' in n:
                    return 'Amex'

        # Por AID
        aid = fields.get('aid', '')
        if isinstance(aid, str) and aid:
            if aid.upper().startswith('A000000003'):
                return 'Visa'
            if aid.upper().startswith('A000000004'):
                return 'MasterCard'
            if aid.upper().startswith('A000000005'):
                return 'Maestro'
            if aid.upper().startswith('A000000025'):
                return 'Amex'
            if aid.upper().startswith('A000000152'):
                return 'Cabal'

        # Por PAN (BIN)
        pan = ''
        tc2 = fields.get('tc2', {})
        if isinstance(tc2, dict):
            rsa = tc2.get('rsa', {})
            t2 = rsa.get('rsa_track2', {})
            if t2:
                pan = t2.get('pan', '')
        if not pan:
            tarj = fields.get('tarj_enmasc', '')
            if isinstance(tarj, str):
                pan = tarj.replace('*', '')

        if pan:
            if pan.startswith('4'):
                return 'Visa'
            if pan[:2] in ('51','52','53','54','55') or (22 <= int(pan[:4] or '0') // 100 <= 27):
                return 'MasterCard'
            if pan.startswith('34') or pan.startswith('37'):
                return 'Amex'
            if pan.startswith('50'):
                return 'Maestro'
            if pan[:2] in ('60','65'):
                return 'Cabal'

        return 'Visa'

    def disconnect(self):
        try:
            self.orchestrator.disconnect_host()
            self._update_tls_status('--', 'gray50')
        except Exception:
            pass

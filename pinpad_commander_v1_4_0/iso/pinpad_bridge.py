"""
PinPad to ISO 8583 Bridge

Mapea la respuesta del comando Y19 del PinPad a los parametros
necesarios para construir un mensaje ISO 8583 (0200).

Flujo:
  1. PinPad Commander envia Y19 -> PinPad lee tarjeta
  2. PinPad responde con datos (PAN, Track2, EMV, PIN, etc.)
  3. Este bridge extrae los datos y los mapea a campos ISO
  4. TransactionBuilder construye el 0200
  5. Se envia via TLS al host
  6. Si chip/ctls -> Y03 al PinPad con resultado
"""

import re
import logging

log = logging.getLogger(__name__)

# Mapeo MDI del PinPad -> modo ISO
MDI_TO_MODE = {
    'M': 'manual',
    'B': 'banda',
    'C': 'chip',
    'L': 'contactless',
}

# Mapeo MDI -> POS Entry Mode (campo 22)
MDI_TO_POS_ENTRY = {
    'M': '0011',
    'B': '0021',
    'C': '0051',
    'L': '0071',
}


def _extract_pan_from_emv(result, fields):
    """Extraer PAN y Track2 de tags EMV (para chip/contactless)."""
    # Buscar en CPG (Y19) o EMV_TLV_2 (Y02)
    for emv_key in ('CPG', 'EMV_TLV_2'):
        emv = fields.get(emv_key, {})
        if isinstance(emv, dict):
            tlv = emv.get('tlv', emv)
            if not isinstance(tlv, dict):
                continue

            # Tag 5A = PAN
            pan_hex = tlv.get('5A', '')
            if pan_hex and not result.get('pan'):
                # PAN en BCD, quitar trailing F
                pan = pan_hex.replace('F', '').replace('f', '')
                if len(pan) >= 12:
                    result['pan'] = pan
                    log.info('PAN extraido de EMV tag 5A: %s****%s', pan[:6], pan[-4:])

            # Tag 57 = Track2 Equivalent Data
            t2_hex = tlv.get('57', '')
            if t2_hex and not result.get('track2'):
                # Track2 en BCD: PAN D YYMM SVC DISC
                t2_str = t2_hex.upper().replace('F', '')
                # Convertir D -> =
                t2_ascii = t2_str.replace('D', '=')
                if '=' in t2_ascii and len(t2_ascii) >= 16:
                    result['track2'] = t2_ascii
                    log.info('Track2 extraido de EMV tag 57')
                    # Extraer PAN del track2 si no lo tenemos
                    if not result.get('pan'):
                        pan_part = t2_ascii.split('=')[0]
                        if len(pan_part) >= 12:
                            result['pan'] = pan_part

            # Tag 9F26 = ARQC (criptograma)
            # Tag 9F27 = CID (Cryptogram Information Data)
            # Estos ya van en emv_tags

    # Si aun no tenemos PAN, intentar extraer de tarj_enmasc quitando *
    if not result.get('pan') and result.get('pan_masked'):
        masked = result['pan_masked']
        # Si no tiene asteriscos, es el PAN real
        if '*' not in masked and len(masked) >= 12:
            result['pan'] = masked


def _extract_track2_from_rsa(result, fields):
    """Extraer Track2 de datos RSA desencriptados."""
    fdv_tc2_raw = fields.get('FDV_TC2', '')
    if isinstance(fdv_tc2_raw, str) and len(fdv_tc2_raw) > 4:
        tc2_hex = fdv_tc2_raw[4:]
        if tc2_hex and len(tc2_hex) > 10:
            result['track2_encrypted'] = tc2_hex


def extract_y19_data(parsed_response):
    """
    Extraer datos relevantes de la respuesta Y19 parseada.

    Args:
        parsed_response: dict con la respuesta Y19 parseada por response_parser

    Returns:
        dict con datos extraidos listos para el bridge
    """
    fields = parsed_response.get('fields', {})
    result = {
        'mdi': None,
        'pan': None,
        'pan_masked': None,
        'vencimiento': None,
        'track2': None,
        'track1': None,
        'emv_tags': None,
        'cvv': None,
        'pin_block': None,
        'ksn': None,
        'secuencia': '000',
        'track1_no_leido': None,
        'aid': None,
        'tipo_cuenta': None,
        'tipo_transaccion': None,
        'monto_adicional': None,
    }

    # MDI (modo de ingreso)
    mdi = fields.get('MDI')
    if mdi:
        result['mdi'] = mdi

    # PAN - puede venir de diferentes campos segun MDI
    # En Y19, tarj_enmasc tiene el PAN (enmascarado o RSA encrypted)
    tarj = fields.get('tarj_enmasc', '')
    if isinstance(tarj, dict):
        # RSA decrypted - buscar PAN en track2 parseado
        rsa_data = tarj.get('rsa', {})
        t2 = rsa_data.get('rsa_track2', {})
        if t2:
            result['pan'] = t2.get('pan', '')
            result['pan_masked'] = t2.get('pan_mask', '')
        # O del track1
        t1 = rsa_data.get('rsa_track1', {})
        if t1 and not result['pan']:
            result['pan'] = t1.get('pan', '')
    elif isinstance(tarj, str) and tarj:
        # PAN directo (enmascarado)
        result['pan_masked'] = tarj

    # Tambien buscar PAN en parse_pan_field
    pan_field = fields.get('tarj_enmascarada', '')
    if isinstance(pan_field, dict):
        if pan_field.get('pan_full'):
            result['pan'] = pan_field['pan_full']
        elif pan_field.get('pan_display'):
            result['pan_masked'] = pan_field['pan_display']
        rsa_data = pan_field.get('rsa', {})
        if rsa_data:
            t2 = rsa_data.get('rsa_track2', {})
            if t2 and t2.get('pan'):
                result['pan'] = t2['pan']

    # Para contactless/chip: extraer PAN de EMV tags
    # Tag 5A = PAN, Tag 57 = Track2 Equivalent Data
    _extract_pan_from_emv(result, fields)

    # Fecha de vencimiento - puede venir como 'ven' o 'FDV'
    for fdv_key in ('ven', 'FDV'):
        fdv = fields.get(fdv_key)
        if fdv and isinstance(fdv, str) and len(fdv) >= 4:
            result['vencimiento'] = fdv[:4]
            break

    # Track 2 (RSA encrypted -> decrypted)
    # Commander parsea como 'tc2' (lowercase) con estructura {hex, rsa}
    for tc2_key in ('tc2', 'TC2', 'FDV_TC2'):
        tc2 = fields.get(tc2_key, {})
        if isinstance(tc2, dict) and 'rsa' in tc2:
            rsa = tc2.get('rsa', {})
            # Buscar track2 parseado del RSA decrypt
            for t2_key in ('rsa_track2', 'track2_parsed'):
                t2_parsed = rsa.get(t2_key, {})
                if t2_parsed and t2_parsed.get('pan'):
                    pan = t2_parsed['pan']
                    yy = t2_parsed.get('exp_yy', '')
                    mm = t2_parsed.get('exp_mm', '')
                    svc = t2_parsed.get('service_code', '')
                    disc = t2_parsed.get('discretionary', '')
                    result['track2'] = '%s=%s%s%s%s' % (pan, yy, mm, svc, disc)
                    if not result['pan']:
                        result['pan'] = pan
                    result['pan_masked'] = t2_parsed.get('pan_mask', '')
                    if not result['vencimiento'] and yy and mm:
                        result['vencimiento'] = yy + mm
                    break
            if result['track2']:
                break

    # FDV_TC2 (chip mode)
    fdv_tc2 = fields.get('FDV_TC2')
    if isinstance(fdv_tc2, str):
        if len(fdv_tc2) >= 4:
            result['vencimiento'] = fdv_tc2[:4]

    # Track 2 directo (si viene como string)
    if not result['track2']:
        for key in ['TC2', 'track2']:
            val = fields.get(key)
            if isinstance(val, str) and '=' in val:
                result['track2'] = val
                break

    # EMV Tags (criptograma)
    cpg = fields.get('CPG', {})
    if isinstance(cpg, dict):
        tlv = cpg.get('tlv', {})
        if tlv and isinstance(tlv, dict):
            # Reconstruir TLV hex string
            emv_hex = ''
            for tag, val in tlv.items():
                if tag.startswith('_'):
                    continue
                tag_hex = tag
                val_hex = val if isinstance(val, str) else ''
                val_bytes = len(val_hex) // 2
                emv_hex += '%s%02X%s' % (tag_hex, val_bytes, val_hex)
            if emv_hex:
                result['emv_tags'] = emv_hex

    # EMV TLV directo (Y02 chip mode)
    emv_tlv2 = fields.get('EMV_TLV_2', {})
    if isinstance(emv_tlv2, dict):
        tlv = emv_tlv2.get('tlv', {})
        if tlv:
            emv_hex = ''
            for tag, val in tlv.items():
                if tag.startswith('_'):
                    continue
                val_hex = val if isinstance(val, str) else ''
                val_bytes = len(val_hex) // 2
                emv_hex += '%s%02X%s' % (tag, val_bytes, val_hex)
            if emv_hex:
                result['emv_tags'] = emv_hex

    # CVV - puede venir como 'csv', 'CDS', 'cvv'
    for cvv_key in ('csv', 'CDS', 'cvv'):
        cds = fields.get(cvv_key)
        if cds and isinstance(cds, str) and cds.strip() and cds != '[EMPTY]':
            # csv del Y19 puede ser '221' (service code) no CVV real
            # Solo tomar si parece CVV (3-4 digitos)
            val = cds.strip()
            if len(val) <= 4 and val.isdigit():
                result['cvv'] = val
            break

    # Tag 9C (tipo transaccion) y 9F03 (monto adicional) desde CPG
    cpg_for_txn = fields.get('CPG', {})
    if isinstance(cpg_for_txn, dict):
        tlv_txn = cpg_for_txn.get('tlv', {})
        if isinstance(tlv_txn, dict):
            # Tag 9C -> tipo transaccion (00=compra, 09=cashback, etc.)
            tag_9c = tlv_txn.get('9C', '')
            if tag_9c and tag_9c != '00':
                result['tipo_transaccion'] = tag_9c
            # Tag 9F03 -> monto adicional (cashback/propina)
            tag_9f03 = tlv_txn.get('9F03', '')
            if tag_9f03 and int(tag_9f03) > 0:
                result['monto_adicional'] = tag_9f03

    # PIN Block - puede venir como 'pin', 'PIN'
    for pin_key in ('pin', 'PIN'):
        pin = fields.get(pin_key, '')
        if isinstance(pin, str) and pin.strip():
            result['pin_block'] = pin.strip()
            break
    tdc_pin = fields.get('TDC_PIN')
    if isinstance(tdc_pin, dict) and tdc_pin.get('PIN'):
        result['pin_block'] = tdc_pin['PIN']

    # KSN
    ksn = fields.get('ksn', '')
    if isinstance(ksn, str) and ksn.strip():
        result['ksn'] = ksn.strip()

    # Secuencia PAN (campo 23) - puede venir como 'sec_pan', 'NSP', o en CPG tag 5F34
    for nsp_key in ('sec_pan', 'NSP'):
        nsp = fields.get(nsp_key, '')
        if isinstance(nsp, str) and nsp.strip():
            result['secuencia'] = nsp.strip().zfill(4)
            break
    # Tambien del EMV tag 5F34
    cpg = fields.get('CPG', {})
    if isinstance(cpg, dict):
        tlv = cpg.get('tlv', {})
        if isinstance(tlv, dict) and tlv.get('5F34'):
            result['secuencia'] = tlv['5F34'].zfill(4)

    # Track1 no leido
    for t1_key in ('t1_no_leido', '1NL'):
        t1nl = fields.get(t1_key, '')
        if isinstance(t1nl, str) and t1nl.strip():
            result['track1_no_leido'] = t1nl.strip()
            break

    # Track2 encriptado (para chip/contactless sin RSA decrypt)
    _extract_track2_from_rsa(result, fields)

    # AID
    aid = fields.get('aid', '')
    if isinstance(aid, str) and aid.strip():
        result['aid'] = aid.strip()

    # Tipo de cuenta
    for tdc_key in ('tipo_cuenta', 'TDC'):
        tdc = fields.get(tdc_key, '')
        if isinstance(tdc, str) and tdc.strip():
            result['tipo_cuenta'] = tdc.strip()
            break

    return result


def build_iso_params(y19_data, transaction_config):
    """
    Construir parametros para TransactionBuilder a partir de datos Y19.

    Args:
        y19_data: dict de extract_y19_data()
        transaction_config: dict con configuracion de la transaccion:
            - monto: float
            - codigo_proc: str (000000=compra, 020000=anulacion, etc.)
            - terminal_id: str
            - merchant_id: str
            - marca: str
            - cuotas: str (ej: "001")
            - cashback: float (opcional)

    Returns:
        dict listo para TransactionBuilder.build_transaction()
    """
    mdi = y19_data.get('mdi', 'M')
    modo = MDI_TO_MODE.get(mdi, 'manual')

    # Codigo de procesamiento: tag 9C define los primeros 2 digitos
    # 00 = compra, 09 = compra + cashback/monto adicional
    tipo_txn = y19_data.get('tipo_transaccion', '')
    if tipo_txn:
        codigo_proc = tipo_txn.zfill(2) + '0000'
    else:
        codigo_proc = transaction_config.get('codigo_proc', '000000')

    params = {
        'tipo_mensaje': '0200',
        'modo': modo,
        'marca': transaction_config.get('marca', 'Visa'),
        'pan': y19_data.get('pan', ''),
        'monto': transaction_config.get('monto', 100.0),
        'codigo_proc': codigo_proc,
        'terminal_id': transaction_config.get('terminal_id'),
        'merchant_id': transaction_config.get('merchant_id'),
        'cuotas': transaction_config.get('cuotas', '001'),
    }

    # Vencimiento
    if y19_data.get('vencimiento'):
        params['vencimiento'] = y19_data['vencimiento']

    # Track2
    if y19_data.get('track2'):
        params['track2'] = y19_data['track2']

    # Track1
    if y19_data.get('track1'):
        params['track1'] = y19_data['track1']

    # EMV tags (chip/contactless)
    if y19_data.get('emv_tags') and modo in ('chip', 'contactless'):
        params['emv_data'] = y19_data['emv_tags']

    # CVV (manual)
    if y19_data.get('cvv') and modo == 'manual':
        params['cvv'] = y19_data['cvv']

    # PIN block
    if y19_data.get('pin_block'):
        params['pin_block'] = y19_data['pin_block']

    # Secuencia PAN
    if y19_data.get('secuencia'):
        params['secuencia'] = y19_data['secuencia']

    # Cashback
    if transaction_config.get('cashback'):
        params['cashback'] = transaction_config['cashback']

    # Monto adicional desde tag 9F03 (cashback/propina) -> Campo 54
    # Si 9F03 tiene valor > 0, habilitar campo 54
    monto_adicional = y19_data.get('monto_adicional')
    if monto_adicional:
        # monto_adicional viene como string BCD del tag 9F03 (ej: '000000010000')
        # Lo pasamos directo como cashback para que se incluya en campo 54
        try:
            monto_adic_int = int(monto_adicional)
            if monto_adic_int > 0:
                params['cashback'] = monto_adic_int / 100.0
                log.info('Monto adicional (9F03): %s -> campo 54: %.2f',
                         monto_adicional, params['cashback'])
        except (ValueError, TypeError):
            pass

    # Campo 59 override
    if transaction_config.get('campo_59'):
        params['campo_59'] = transaction_config['campo_59']

    return params


def build_y03_params(iso_response):
    """
    Construir parametros para comando Y03 a partir de la respuesta ISO 0210.

    Args:
        iso_response: dict parseado de la respuesta 0210

    Returns:
        dict con CAU, CRE, RCP para enviar Y03 al PinPad
    """
    fields = iso_response.get('fields', {})

    auth_code = fields.get(38, '      ')
    resp_code = fields.get(39, '00')

    # Tags EMV de respuesta (campo 55 del 0210)
    emv_resp = fields.get(55, '')

    return {
        'CAU': auth_code.ljust(6)[:6],
        'CRE': resp_code[:2],
        'RCP': emv_resp if emv_resp else 'N',
    }


def needs_y03(mdi):
    """Determinar si se necesita Y03 segun el modo de ingreso."""
    return mdi in ('C', 'L')  # Chip y Contactless requieren confirmacion EMV


def get_transaction_summary(y19_data, iso_result):
    """
    Generar resumen de la transaccion para logging/UI.

    Returns:
        dict con resumen legible
    """
    mdi = y19_data.get('mdi', '?')
    modo = MDI_TO_MODE.get(mdi, 'desconocido')

    summary = {
        'modo_ingreso': modo,
        'mdi': mdi,
        'pan_masked': y19_data.get('pan_masked', '****'),
        'tiene_emv': bool(y19_data.get('emv_tags')),
        'tiene_pin': bool(y19_data.get('pin_block')),
        'requiere_y03': needs_y03(mdi),
    }

    if iso_result and iso_result.get('success'):
        parsed = iso_result.get('parsed', {})
        fields = parsed.get('fields', {})
        summary['response_code'] = fields.get(39, 'XX')
        summary['auth_code'] = fields.get(38, '')
        summary['ref_number'] = fields.get(37, '')
        summary['response_desc'] = iso_result.get('response_description', '')

    return summary

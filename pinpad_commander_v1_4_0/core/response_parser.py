#!/usr/bin/env python3
"""
Parser de respuestas del PinPad
"""

import re
import json
import os
import logging
from core.data_processor import DataProcessor


class ResponseParser:
    def __init__(self, comm, processor=None, app=None):
        self.comm = comm
        self.processor = processor or DataProcessor()
        self.app = app  # Referencia a la aplicación principal para acceder a mask_pan
        self.error_codes = self._load_error_codes()
        self.custom_parsers = self._load_custom_parsers()
        self.field_decoders = self._load_field_decoders()
        self.validation_rules = self._load_validation_rules()
    
    def _load_error_codes(self):
        """Cargar códigos de error Y0E desde configuración"""
        try:
            error_config_path = os.path.join("config", "y0e_errors.json")
            if os.path.exists(error_config_path):
                with open(error_config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"FF": "Error desconocido"}
    
    def _load_custom_parsers(self):
        """Cargar parsers personalizados desde configuración"""
        try:
            parser_config_path = os.path.join("config", "response_parsers.json")
            if os.path.exists(parser_config_path):
                with open(parser_config_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("parsers", {})
        except (IOError, json.JSONDecodeError, KeyError) as e:
            logging.debug(f"Could not load custom parsers: {e}")
        except Exception as e:
            logging.warning(f"Unexpected error loading parsers: {e}")
        return {}
    
    def _load_field_decoders(self):
        """Cargar configuración de decodificadores de campo"""
        try:
            config_path = os.path.join("config", "field_decoders.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _load_validation_rules(self):
        """Cargar reglas de validación"""
        try:
            config_path = os.path.join("config", "validation_rules.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def get_error_description(self, error_code):
        """Obtener descripción del código de error Y0E"""
        return self.error_codes.get(error_code, f"Error desconocido ({error_code})")
    
    def validate_and_parse(self, raw, cdef, ui_cmd_id):
        """Validar y parsear respuesta"""
        try:
            if not self.comm.codec.validate_lrc(raw):
                return False, "LRC inválido"
            
            cid, payload = self.comm.codec.extract(raw)
            expected = cdef.get("cid", ui_cmd_id)
            
            # Usar configuración para validación de CID
            validation_config = self.validation_rules.get("validation", {}).get("cid_validation", {})
            error_command = validation_config.get("error_command", "Y0E")
            
            if cid not in (expected, error_command):
                # Verificar casos especiales
                special_cases = validation_config.get("special_cases", {})
                y19_config = special_cases.get("Y19_variants", {})
                if expected.startswith(y19_config.get("pattern", "Y19").replace("*", "")) and cid == y19_config.get("accept_as", "Y19"):
                    pass
                else:
                    return False, f"CID inesperado: {cid}"
            
            if cid == error_command:
                error_fields = validation_config.get("error_fields", {})
                cmd_field = error_fields.get("command", {"start": 0, "length": 3})
                err_field = error_fields.get("error_code", {"start": 3, "length": 2})
                
                cri = payload[cmd_field["start"]:cmd_field["start"]+cmd_field["length"]].decode(errors="ignore") if len(payload) >= cmd_field["start"]+cmd_field["length"] else ""
                coe = payload[err_field["start"]:err_field["start"]+err_field["length"]].decode(errors="ignore") if len(payload) >= err_field["start"]+err_field["length"] else ""
                error_desc = self.get_error_description(coe)
                return False, f"{error_command}: Comando={cri} Error={coe} ({error_desc})"
            
            return self._parse_response(cid, payload, cdef)
                
        except Exception as e:
            return False, f"Error de parseo: {e}"
    
    def _parse_response(self, cid, payload, cdef):
        """Parsear respuesta según definición"""
        # Usar configuración por defecto si no se especifica
        default_parser = self.validation_rules.get("parsing", {}).get("default_parser", {"type": "fs", "fields": []})
        parser_def = cdef.get("response", {}).get("parser", default_parser)
        
        if parser_def.get("type") == "fs":
            from protocol import FSParser
            
            # Obtener campos según configuración dinámica
            fields = self._get_dynamic_fields(cid, parser_def)
            
            parser = FSParser(fs=self.comm.codec.fs)
            values = parser.parse(payload)
            raw_parts = payload.split(bytes([self.comm.codec.fs]))
            if raw_parts and raw_parts[0] == b"":
                raw_parts = raw_parts[1:]
            fs_hex_segments = [p.hex().upper() for p in raw_parts]
            
            mapping = {}
            for i, spec in enumerate(fields):
                val = values[i] if i < len(values) else ""
                if isinstance(spec, str):
                    mapping[spec] = val
                else:
                    mapping.update(self._process_field_spec(spec, val, i))
            
            result = {
                "cid": cid,
                "fields": mapping,
                "fs_segments": values,
                "fs_hex_segments": fs_hex_segments,
                "raw_payload": payload.decode(errors="ignore"),
                "debug_field_count": len(fields),
                "debug_segment_count": len(values)
            }
            
            # Post-procesar Y19 para guardar MDI
            if cid == "Y19":
                self._save_y19_mdi(result)
            # Post-procesar Y03 para separar RESP de datos EMV
            elif cid == "Y03":
                result = self._parse_y03_format(result)
                # Procesar tag_emv como TLV si existe
                if "fields" in result and "tag_emv" in result["fields"]:
                    tag_emv = result["fields"]["tag_emv"]
                    if isinstance(tag_emv, str) and tag_emv.strip():
                        tlv_parsed = self.processor.parse_tlv_hex(tag_emv)
                        emv_result = {"tlv": tlv_parsed}
                        if self.app and hasattr(self.app, '_emv_pretty'):
                            emv_result["pretty"] = self.app._emv_pretty(tlv_parsed)
                        else:
                            emv_result["pretty"] = tlv_parsed
                        result["fields"]["tag_emv"] = emv_result
            
            return True, result
        else:
            return True, {"cid": cid, "raw_payload": payload.decode(errors="ignore")}
    
    def _process_field_spec(self, spec, val, index):
        """Procesar especificación de campo"""
        # Usar configuración para nombres de campo por defecto
        field_naming = self.validation_rules.get("parsing", {}).get("field_naming", {})
        default_prefix = field_naming.get("default_prefix", "FIELD_")
        index_start = field_naming.get("index_start", 1)
        name = spec.get("name", f"{default_prefix}{index+index_start}")
        decode = spec.get("decode")
        flatten = spec.get("flatten", False)
        post = spec.get("post")
        out_val = val
        
        # Decodificación
        if decode == "tlv_hex":
            out_val = self.processor.parse_tlv_hex(val)
        elif decode == "hex":
            out_val = val.replace(" ", "").upper()
        elif decode == "trim":
            out_val = val.strip()
        elif decode in self.field_decoders.get("decoders", {}):
            decoder_config = self.field_decoders["decoders"][decode]
            if decode == "bankver":
                s = val.strip()
                fields_config = decoder_config.get("fields", {})
                bank_config = fields_config.get("bank_code", {})
                version_config = fields_config.get("version", {})
                
                bank_length = bank_config.get("length", 6)
                cod = s[:bank_length] if len(s) >= bank_length else s
                ver = s[bank_length:]
                if version_config.get("trim", False):
                    ver = ver.strip()
                
                out_val = {
                    bank_config.get("name", "COD_BANCO"): cod,
                    version_config.get("name", "VERSION_PP"): ver
                }
            elif decode == "hex_ascii_printable":
                char_range = decoder_config.get("char_range", {"min": 32, "max": 126})
                hs = re.sub(r"[^0-9A-Fa-f]", "", val or "")
                try:
                    txt = "".join(chr(c) for c in bytes.fromhex(hs) if char_range["min"] <= c <= char_range["max"])
                    out_val = txt if txt else val
                except (ValueError, TypeError) as e:
                    logging.debug(f"Error converting hex to ASCII: {e}")
                    out_val = val
        
        # Post-procesamiento
        if post == "rsa_decrypt" and isinstance(out_val, str):
            if out_val.strip():
                rsa_result = self._decrypt_rsa_blob(out_val.strip())
                out_val = {"hex": out_val, "rsa": rsa_result}
        elif post == "emv_pretty" and isinstance(out_val, dict):
            if self.app and hasattr(self.app, '_emv_pretty'):
                out_val = {"tlv": out_val, "pretty": self.app._emv_pretty(out_val)}
            else:
                out_val = {"tlv": out_val, "pretty": out_val}
        elif post == "parse_track2" and isinstance(out_val, str):
            if out_val.strip():
                t2 = self._parse_track2_ascii(out_val.strip())
                out_val = {"track2": t2} if t2 else out_val
        elif post == "parse_pan_field" and isinstance(out_val, str):
            out_val = self._parse_pan_field(out_val.strip())
        elif post in self.custom_parsers and isinstance(out_val, str):
            out_val = self._parse_with_config(post, out_val.strip())
        elif post == "parse_cau_field" and isinstance(out_val, str):
            out_val = self._parse_cau_field(out_val)


        elif post == "parse_fdv_tc2" and isinstance(out_val, str):
            out_val = self._parse_fdv_tc2_field(out_val)
        elif post == "parse_1nl_nsf" and isinstance(out_val, str):
            out_val = self._parse_1nl_nsf_field(out_val)
        elif post == "parse_cse_cbc_nya" and isinstance(out_val, str):
            out_val = self._parse_cse_cbc_nya_field(out_val)
        elif post == "parse_reg_mdi_ver" and isinstance(out_val, str):
            out_val = self._parse_reg_mdi_ver_field(out_val)
        elif post == "parse_cau_cre_nsp_apn" and isinstance(out_val, str):
            out_val = self._parse_cau_cre_nsp_apn_field(out_val)
        elif post == "parse_cau_cre_rcp" and isinstance(out_val, str):
            out_val = self._parse_cau_cre_rcp(out_val)
        elif post == "parse_1nl_cds" and isinstance(out_val, str):
            out_val = self._parse_1nl_cds_field(out_val)
        elif post == "parse_tdc_pin" and isinstance(out_val, str):
            out_val = self._parse_tdc_pin_field(out_val)
        elif post == "parse_fdv_cds" and isinstance(out_val, str):
            out_val = self._parse_fdv_cds_field(out_val)
        elif post == "parse_tdc_pvf_pin" and isinstance(out_val, str):
            out_val = self._parse_tdc_pvf_pin_field(out_val)
        
        if flatten and isinstance(out_val, dict):
            return out_val
        else:
            return {name: out_val}
    
    def _parse_track2_ascii(self, s):
        """Parsear Track2 desde ASCII usando configuración"""
        if not s:
            return None
        
        # Obtener configuración del parser Track2
        track2_config = self.field_decoders.get("post_processors", {}).get("parse_track2", {})
        regex_pattern = track2_config.get("regex", r'([0-9]{12,19})(?:=|D)([0-9]{2})([0-9]{2})([0-9]{3})?([0-9]*)')
        field_names = track2_config.get("fields", ["pan", "exp_yy", "exp_mm", "service_code", "discretionary"])
        
        m = re.search(regex_pattern, s)
        if not m:
            return None
        
        field_values = m.groups()
        pan = field_values[0] if len(field_values) > 0 else ""
        yy = field_values[1] if len(field_values) > 1 else ""
        mm = field_values[2] if len(field_values) > 2 else ""
        svc = field_values[3] if len(field_values) > 3 else ""
        disc = field_values[4] if len(field_values) > 4 else ""
        
        def mask_pan(pan):
            pan_mask_config = track2_config.get("pan_mask", {})
            min_length = pan_mask_config.get("min_length", 10)
            show_first = pan_mask_config.get("show_first", 6)
            show_last = pan_mask_config.get("show_last", 4)
            mask_char = pan_mask_config.get("mask_char", "*")
            
            pan = re.sub(r'[^0-9]', '', pan or '')
            if len(pan) < min_length:
                return pan
            return pan[:show_first] + mask_char * (len(pan)-show_first-show_last) + pan[-show_last:]
        
        def yy_mm_to_iso(yy, mm):
            date_config = track2_config.get("date_format", {})
            century_cutoff = date_config.get("century_cutoff", 79)
            default_century = date_config.get("default_century", 2000)
            fallback_century = date_config.get("fallback_century", 1900)
            
            try:
                y = int(yy)
                m = int(mm)
                century = default_century if y <= century_cutoff else fallback_century
                return f"{century + y:04d}-{m:02d}"
            except Exception:
                return f"20{yy}-{mm}"
        
        def luhn_check(pan):
            if not isinstance(pan, str):
                return False
            digits = [int(c) for c in re.sub(r'[^0-9]', '', pan)]
            if not digits:
                return False
            checksum = 0
            parity = (len(digits) - 2) % 2
            for i, d in enumerate(digits[:-1]):
                if i % 2 == parity:
                    d = d * 2
                    if d > 9:
                        d -= 9
                checksum += d
            return (checksum + digits[-1]) % 10 == 0
        
        t2 = {
            "pan_mask": mask_pan(pan),
            "pan": pan,
            "pan_len": len(pan),
            "exp_yy": yy,
            "exp_mm": mm,
            "service_code": svc,
            "discretionary": disc,
            "expiry_iso": yy_mm_to_iso(yy, mm),
            "luhn_ok": luhn_check(pan)
        }
        
        # Aplicar enmascarado si está habilitado
        try:
            if self.app and hasattr(self.app.window, 'connection_panel') and self.app.window.connection_panel.mask_pan_var.get():
                t2.pop("pan", None)
            else:
                t2.setdefault("pan_mask", mask_pan(pan))
        except (AttributeError, KeyError) as e:
            logging.debug(f"Could not apply PAN masking: {e}")
        
        return t2
    
    def _decrypt_rsa_blob(self, hex_str):
        """Desencriptar blob RSA"""
        if not self.app or not hasattr(self.app, 'rsa') or not self.app.rsa.private_key:
            return {"error": "No hay clave RSA cargada"}
        
        hs = re.sub(r"[^0-9A-Fa-f]", "", hex_str or "")
        if not hs:
            return {"error": "Hex vacío"}
        
        key_bytes = (self.app.rsa.private_key.size_in_bits() + 7) // 8
        mode = self.app.rsa_padding.get() if hasattr(self.app, "rsa_padding") else "PKCS1v15"
        
        debug_info = {
            "hex_length": len(hs),
            "expected_length": key_bytes * 2,
            "key_size_bits": self.app.rsa.private_key.size_in_bits(),
            "padding_mode": mode
        }
        
        if len(hs) == key_bytes * 2:
            try:
                blob = bytes.fromhex(hs)
            except Exception as e:
                return {"error": f"HEX inválido: {e}", "debug": debug_info}
            result = self.app.rsa.decrypt_bytes(blob, mode)
            result["debug"] = debug_info
            return self._process_rsa_result(result)
        
        # Intentar parsear como TLV
        tlv = self.processor.parse_tlv_hex(hs)
        if tlv and list(tlv.keys()) != ["_raw"]:
            res = {
                "note": f"Cipher HEX no coincide con tamaño de clave ({len(hs)//2} vs {key_bytes}). Probando sub-tags.",
                "candidates": {},
                "debug": debug_info
            }
            for tag, valhex in tlv.items():
                if len(valhex) == key_bytes * 2:
                    try:
                        result = self.app.rsa.decrypt_bytes(bytes.fromhex(valhex), mode)
                        res["candidates"][tag] = self._process_rsa_result(result)
                    except Exception as e:
                        res["candidates"][tag] = {"error": str(e)}
            if res["candidates"]:
                return res
        
        if mode == "RAW-NoPadding":
            try:
                whole = bytes.fromhex(hs)
            except Exception as e:
                return {"error": f"HEX inválido: {e}", "debug": debug_info}
            result = self.app.rsa.decrypt_raw(whole)
            result["debug"] = debug_info
            return {"note": "RAW fallback: desencriptando el blob completo con zero-left-pad/truncate a k bytes.", **self._process_rsa_result(result)}
        
        return {"error": f"No hay sub-campos con longitud {key_bytes} bytes dentro del TLV.", "debug": debug_info}
    
    def _process_rsa_result(self, rsa_result):
        """Procesar resultado de desencriptado RSA aplicando enmascarado si es necesario"""
        if "error" in rsa_result:
            return rsa_result
        
        result = rsa_result.copy()
        
        # Verificar si el enmascarado está habilitado
        mask_enabled = False
        try:
            if (self.app and hasattr(self.app.window, 'connection_panel') and 
                self.app.window.connection_panel.mask_pan_var.get()):
                mask_enabled = True
        except Exception:
            pass
        
        # Si enmascarado está habilitado, remover campos sensibles
        if mask_enabled:
            result.pop("rsa_plain_hex", None)
            result.pop("rsa_plain_ascii", None)
        
        # Parsear Track1 y Track2 si existe ASCII
        ascii_out = rsa_result.get("rsa_plain_ascii", "")
        if ascii_out:
            # Intentar parsear como Track1 primero
            t1 = self._parse_track1_ascii(ascii_out.strip())
            if t1:
                if mask_enabled:
                    # Remover campo raw del track1 si está enmascarado
                    t1.pop("raw", None)
                result["rsa_track1"] = t1
            
            # Intentar parsear como Track2
            t2 = self._parse_track2_ascii(ascii_out.strip())
            if t2:
                if mask_enabled:
                    # Solo incluir versión enmascarada del track2
                    t2.pop("pan", None)  # Remover PAN completo
                result["rsa_track2"] = t2
        
        # Parsear TLV si existe (solo si no está enmascarado)
        if not mask_enabled:
            hex_out = result.get("rsa_plain_hex", "")
            if hex_out:
                tlv = self.processor.parse_tlv_hex(hex_out)
                if tlv and list(tlv.keys()) != ["_raw"]:
                    result["rsa_tlv"] = tlv
                    val57 = tlv.get("57")
                    if val57:
                        try:
                            vb = bytes.fromhex(val57)
                            s = ''.join(f"{b>>4:X}{b&0xF:X}" for b in vb).replace('D', '=')
                            t2b = self._parse_track2_ascii(s)
                            if t2b:
                                result.setdefault("rsa_track2", t2b)
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Could not parse TLV track2: {e}")
        
        return result
    

    
    def _parse_with_config(self, parser_name, value):
        """Parsear usando configuración JSON"""
        if parser_name not in self.custom_parsers:
            return value
        
        config = self.custom_parsers[parser_name]
        fields = config.get("fields", [])
        result = {}
        
        for field_config in fields:
            field_name = field_config.get("name")
            
            # Si tiene valor fijo
            if "value" in field_config:
                result[field_name] = field_config["value"]
                continue
            
            # Extraer substring
            start = field_config.get("start", 0)
            length = field_config.get("length")
            end = field_config.get("end")
            
            if length is not None:
                field_value = value[start:start+length] if start+length <= len(value) else value[start:]
            elif end is not None:
                field_value = value[start:end]
            else:
                field_value = value[start:]
            
            # Aplicar decodificación
            decode = field_config.get("decode")
            if decode == "hex_to_ascii":
                try:
                    field_value = bytes.fromhex(field_value).decode('ascii', errors='ignore')
                except (ValueError, TypeError) as e:
                    logging.debug(f"Could not decode hex to ASCII: {e}")
            
            # Aplicar post-procesamiento
            post_process = field_config.get("post_process")
            if post_process == "rsa_decrypt" and field_value.strip():
                rsa_result = self._decrypt_rsa_blob(field_value.strip())
                # Para CTLS, también intentar parsear Track2 del resultado RSA
                if "rsa_plain_ascii" in rsa_result:
                    track2_parsed = self._parse_track2_ascii(rsa_result["rsa_plain_ascii"])
                    if track2_parsed:
                        rsa_result["track2_parsed"] = track2_parsed
                field_value = {"hex": field_value, "rsa": rsa_result}
            
            result[field_name] = field_value
        
        return result
    
    def _parse_pan_field(self, tja_value):
        """Parsear campo TJA del Y19 - maneja enmascarado según configuración"""
        if not tja_value:
            return tja_value
        
        # Extraer solo dígitos del campo TJA
        pan_digits = re.sub(r'[^0-9]', '', tja_value)
        
        if len(pan_digits) < 10:
            return tja_value  # Devolver tal como viene si es muy corto
        
        # Crear versión enmascarada (8 primeros + 4 últimos)
        pan_masked = pan_digits[:8] + '*' * (len(pan_digits)-12) + pan_digits[-4:]
        
        result = {
            "tja_original": tja_value,
            "pan_masked": pan_masked,
            "pan_length": len(pan_digits)
        }
        
        # Aplicar enmascarado según configuración
        try:
            if (self.app and hasattr(self.app.window, 'connection_panel') and 
                self.app.window.connection_panel.mask_pan_var.get()):
                # Si enmascarado está habilitado, no incluir PAN completo
                result["pan_display"] = pan_masked
            else:
                # Si enmascarado está deshabilitado, incluir PAN completo
                result["pan_full"] = pan_digits
                result["pan_display"] = pan_digits
        except (AttributeError, KeyError) as e:
            logging.debug(f"Could not apply PAN field masking: {e}")
            # Fallback: solo mostrar enmascarado
            result["pan_display"] = pan_masked
        
        return result
    
    def _parse_cau_field(self, value):
        """Parsear campo CAU - maneja espacios como campo vacío"""
        if not value or value.strip() == "" or all(c == ' ' for c in value):
            return "[EMPTY]"
        return value.strip()
    

    
    def _parse_track1_ascii(self, track1_ascii):
        """Parsear Track 1 desde ASCII desencriptado"""
        if not track1_ascii or not isinstance(track1_ascii, str):
            return None
        
        # Patrón para formato PinPad: B<PAN>^<Name>^<Expiry><Discretionary>
        pattern = r'B([0-9]{12,19})\^([^\^]*)\^([0-9]{6})([0-9]*)?'
        match = re.search(pattern, track1_ascii)
        
        if not match:
            return None
        
        pan = match.group(1)
        name = match.group(2).strip()
        expiry_data = match.group(3)  # 6 dígitos: YYMMSC (YY=año, MM=mes, SC=service code)
        discretionary = match.group(4) or ""
        
        # Extraer fecha y service code
        exp_yy = expiry_data[:2]
        exp_mm = expiry_data[2:4] 
        service_code = expiry_data[4:6]
        
        def mask_pan_track1(pan):
            if len(pan) < 10:
                return pan
            return pan[:6] + "*" * (len(pan)-10) + pan[-4:]
        
        result = {
            "pan_masked": mask_pan_track1(pan),
            "cardholder_name": name.replace("/", " ").strip(),
            "exp_yy": exp_yy,
            "exp_mm": exp_mm,
            "expiry_yymm": exp_yy + exp_mm,
            "service_code": service_code,
            "discretionary": discretionary.strip(),
            "raw": track1_ascii
        }
        
        # Aplicar enmascarado según configuración
        try:
            if (self.app and hasattr(self.app.window, 'connection_panel') and 
                not self.app.window.connection_panel.mask_pan_var.get()):
                result["pan"] = pan
        except (AttributeError, KeyError):
            pass
        
        return result
    
    def _get_dynamic_fields(self, cid, parser_def):
        """Obtener campos dinámicos según configuración y contexto"""
        # Si no es Y02 o no tiene configuración dinámica, usar campos normales
        if cid != "Y02" or not parser_def.get("dynamic_by_mdi"):
            return parser_def.get("fields", [])
        
        # Obtener MDI del Y19 anterior
        mdi = getattr(self, '_last_y19_mdi', None)
        
        # Buscar configuración específica para el MDI
        mdi_configs = parser_def.get("mdi_configs", {})
        if mdi and mdi in mdi_configs:
            fields = mdi_configs[mdi].get("fields", [])
            logging.info(f"Using Y02 fields for MDI={mdi}: {mdi_configs[mdi].get('description', 'Unknown')}")
            return fields
        
        # Fallback a campos por defecto
        default_fields = parser_def.get("default_fields", parser_def.get("fields", []))
        if mdi:
            logging.warning(f"No specific Y02 configuration for MDI={mdi}, using default fields")
        else:
            logging.info("No Y19 MDI context available, using default Y02 fields")
        
        return default_fields
    
    def _save_y19_mdi(self, parsed_result):
        """Guardar MDI del Y19 para usar en Y02"""
        if not isinstance(parsed_result, dict) or "fields" not in parsed_result:
            return
        
        # Buscar MDI en los campos parseados
        for field_name, field_value in parsed_result["fields"].items():
            if isinstance(field_value, dict) and "MDI" in field_value:
                self._last_y19_mdi = field_value["MDI"]
                logging.info(f"Saved Y19 MDI for Y02 parsing: {self._last_y19_mdi}")
                break
            elif field_name == "MDI":
                self._last_y19_mdi = field_value
                logging.info(f"Saved Y19 MDI for Y02 parsing: {self._last_y19_mdi}")
                break
    

    
    def _parse_y03_format(self, parsed_result):
        """Post-procesar resultado Y03 para separar RESP de datos EMV"""
        if not isinstance(parsed_result, dict) or "fields" not in parsed_result:
            return parsed_result
        
        # Si solo hay 1 segmento, los datos EMV están concatenados con RESP
        if parsed_result.get("debug_segment_count", 0) == 1:
            resp_field = parsed_result["fields"].get("RESP", "")
            if isinstance(resp_field, str) and len(resp_field) > 8:
                # Formato Y03: CAU(6) + CRE(2) + datos EMV
                resp_part = resp_field[:8]  # CAU(6) + CRE(2)
                emv_part = resp_field[8:]   # Datos EMV
                
                # Actualizar RESP
                parsed_result["fields"]["RESP"] = resp_part
                
                # Parsear datos EMV
                if emv_part.strip():
                    tlv_parsed = self.processor.parse_tlv_hex(emv_part)
                    emv_result = {"tlv": tlv_parsed}
                    if self.app and hasattr(self.app, '_emv_pretty'):
                        emv_result["pretty"] = self.app._emv_pretty(tlv_parsed)
                    else:
                        emv_result["pretty"] = tlv_parsed
                    parsed_result["fields"]["EMV_TLV_3"] = emv_result
        
        return parsed_result
    


    

    
    def _parse_fdv_tc2_field(self, value):
        """Parsear campo FDV_TC2"""
        if not value or len(value) < 4:
            return value
        
        result = {"FDV": value[:4]}
        tc2_hex = value[4:]
        
        if tc2_hex.strip():
            rsa_result = self._decrypt_rsa_blob(tc2_hex.strip())
            result["TC2"] = {"hex": tc2_hex, "rsa": rsa_result}
        
        return result
    
    def _parse_1nl_nsf_field(self, value):
        """Parsear campo 1NL_NSF"""
        if not value or len(value) < 1:
            return value
        
        return {
            "1NL": value[:1],
            "NSF": value[1:] if len(value) > 1 else ""
        }
    
    def _parse_cse_cbc_nya_field(self, value):
        """Parsear campo CSE_CBC_NYA"""
        if not value or len(value) < 6:
            return value
        
        return {
            "CSE": value[:3],
            "CBC": value[3:6],
            "NYA": value[6:].strip() if len(value) > 6 else ""
        }
    
    def _parse_reg_mdi_ver_field(self, value):
        """Parsear campo REG_MDI_VER"""
        if not value or len(value) < 7:
            return value
        
        mdi_value = value[6:7]
        # Guardar MDI en contexto para otros parsers
        self._current_mdi = mdi_value
        
        return {
            "REG": value[:6],
            "MDI": mdi_value,
            "VER": value[7:] if len(value) > 7 else "",
            "card_type": self._get_card_type_from_mdi(mdi_value)
        }
    
    def _parse_1nl_cds_field(self, value):
        """Parsear campo 1NL_CDS para banda magnética"""
        if not value or len(value) < 1:
            return {"1NL": "", "CDS": ""}
        
        return {
            "1NL": value[:1],
            "CDS": "[EMPTY]"  # CDS siempre vacío en banda
        }
    
    def _parse_tdc_pin_field(self, value):
        """Parsear campo TDC_PIN"""
        if not value:
            return {"TDC": "", "PIN": ""}
        
        return {
            "TDC": value.strip(),
            "PIN": ""  # PIN separado si existe
        }
    
    def _parse_fdv_cds_field(self, value):
        """Parsear campo FDV_CDS para manual"""
        if not value or len(value) < 4:
            return {"FDV": "", "CDS": ""}
        
        return {
            "FDV": value[:4],
            "CDS": value[4:].strip() if len(value) > 4 else ""
        }
    
    def _parse_tdc_pvf_pin_field(self, value):
        """Parsear campo TDC_PVF_PIN para chip"""
        if not value:
            return {"TDC": "", "PVF": "", "PIN": ""}
        
        return {
            "TDC": value[:1] if len(value) >= 1 else "",
            "PVF": "",  # PVF si existe
            "PIN": ""   # PIN si existe
        }
    
    def _parse_cau_cre_nsp_apn_field(self, value):
        """Parsear campo CAU_CRE_NSP_APN"""
        if not value:
            return {"CAU": "[EMPTY]", "CRE": "", "NSP": "", "APN": ""}
        
        result = {
            "CAU": "[EMPTY]",
            "CRE": value[:2] if len(value) >= 2 else "",
            "NSP": value[2:5] if len(value) >= 5 else "",
            "APN": ""
        }
        
        apn_hex = value[5:] if len(value) > 5 else ""
        if apn_hex:
            try:
                result["APN"] = bytes.fromhex(apn_hex).decode('ascii', errors='ignore')
            except (ValueError, TypeError):
                result["APN"] = apn_hex
        
        return result
    
    def _parse_cau_cre_rcp(self, value):
        """Parsear campo CAU_CRE_RCP del Y03"""
        if not value or len(value) < 8:
            return value
        
        # Estructura: CAU(6) + CRE(2) + datos EMV TLV
        result = {
            "cod_aut": value[:6],
            "cod_resp": value[6:8]
        }
        
        # Datos EMV TLV (resto)
        emv_data = value[8:] if len(value) > 8 else ""
        if emv_data.strip():
            tlv_parsed = self.processor.parse_tlv_hex(emv_data)
            emv_result = {"tlv": tlv_parsed}
            if self.app and hasattr(self.app, '_emv_pretty'):
                emv_result["pretty"] = self.app._emv_pretty(tlv_parsed)
            else:
                emv_result["pretty"] = tlv_parsed
            result["tag_emv"] = emv_result
        else:
            result["tag_emv"] = emv_data
        
        return result
    

import re
import json
import logging
import html

class DataProcessor:
    EMV_TAG_NAMES = {
        "9F02": "importe", "9F03": "cashback", "9A": "fecha", "9C": "tipo_txn", "95": "TVR", "9F26": "ARQC",
        "9F27": "CVM_Result", "9F33": "Terminal_Capabilities", "9F34": "CVM_List", "9F36": "ATC", "9F37": "Unpredictable_Number",
        "9F1E": "Terminal_ID", "9F6E": "Visa_Magstripe_Cap", "84": "AID", "5F34": "PAN_Sequence", "82": "AIP", "5F2A": "Moneda"
    }
    
    @staticmethod
    def parse_tlv_hex(hex_ascii):
        # Sanitizar entrada para prevenir XSS
        if not hex_ascii:
            return {"_raw": ""}
        
        # Validar y sanitizar entrada
        if not isinstance(hex_ascii, str):
            hex_ascii = str(hex_ascii)
        
        safe_hex = html.escape(hex_ascii)
        hs = re.sub(r"[^0-9A-Fa-f]", "", safe_hex)
        
        if not hs:
            return {"_raw": safe_hex}
        
        # Limitar tamaño para prevenir ataques DoS
        if len(hs) > 16384:
            logging.warning(f"TLV hex data too large: {len(hs)} chars")
            return {"_raw": safe_hex, "_error": "Data too large"}
        
        try:
            data = bytes.fromhex(hs)
        except ValueError as e:
            logging.debug(f"Invalid hex data: {e}")
            return {"_raw": safe_hex, "_error": "Invalid hex"}
        
        i, out = 0, {}
        max_iterations = 1000
        iterations = 0
        
        while i < len(data) and iterations < max_iterations:
            iterations += 1
            
            if i >= len(data):
                break
                
            tag = data[i]
            i += 1
            
            # Manejar tags multi-byte con bounds checking
            if (tag & 0x1F) == 0x1F:
                if i >= len(data):
                    break
                tag = (tag << 8) | data[i]
                i += 1
                if (tag & 0x80) and i < len(data):
                    tag = (tag << 8) | data[i]
                    i += 1
            
            if i >= len(data):
                break
                
            L = data[i]
            i += 1
            
            # Manejar length multi-byte con bounds checking
            if L & 0x80:
                n = L & 0x7F
                if n > 4 or i + n > len(data):
                    break
                L = 0
                for _ in range(n):
                    if i >= len(data):
                        break
                    L = (L << 8) | data[i]
                    i += 1
                if L > len(data) - i or L > 8192:
                    break
            
            if i + L > len(data):
                break
                
            val = data[i:i+L]
            i += L
            
            if len(out) > 256:
                out["_warning"] = "Too many tags, truncated"
                break
                
            out[f"{tag:X}"] = val.hex().upper()
        
        if iterations >= max_iterations:
            out["_warning"] = "Parsing truncated due to complexity"
            
        return out
    
    @classmethod
    def emv_pretty(cls, tlv):
        if not isinstance(tlv, dict):
            return tlv
        
        pretty = {}
        exp = 2
        
        try:
            for tag, val in tlv.items():
                if not isinstance(tag, str) or not isinstance(val, str):
                    continue
                
                safe_tag = re.sub(r'[^0-9A-Fa-f]', '', tag)[:10]
                safe_val = re.sub(r'[^0-9A-Fa-f]', '', val)[:100]
                
                name = cls.EMV_TAG_NAMES.get(safe_tag, safe_tag)
                
                if safe_tag in ("9F02", "9F03"):
                    pretty[name] = cls._amount_from_bcd_hex(safe_val, exp)
                elif safe_tag == "9A" and len(safe_val) == 6:
                    try:
                        yy, mm, dd = safe_val[0:2], safe_val[2:4], safe_val[4:6]
                        year = int(yy)
                        month = int(mm)
                        day = int(dd)
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            pretty[name] = f"20{yy}-{mm}-{dd}"
                        else:
                            pretty[name] = safe_val
                    except (ValueError, IndexError):
                        pretty[name] = safe_val
                elif safe_tag == "5F2A" and len(safe_val) == 4:
                    try:
                        currency_digits = cls._bcd_digits(safe_val)
                        if currency_digits.isdigit():
                            pretty[name] = currency_digits.zfill(3)
                        else:
                            pretty[name] = safe_val
                    except Exception:
                        pretty[name] = safe_val
                else:
                    pretty[name] = safe_val
                
                if len(pretty) > 100:
                    pretty["_warning"] = "Too many fields, truncated"
                    break
        
        except Exception as e:
            logging.error(f"Error in EMV pretty formatting: {e}")
            return {"_error": "EMV formatting failed", "_raw": tlv}
        
        return pretty
    
    @staticmethod
    def _bcd_digits(hex_str):
        hex_str = re.sub(r"[^0-9A-Fa-f]", "", hex_str or "")
        return "".join(str(int(ch, 16)) for ch in hex_str if ch in "0123456789ABCDEFabcdef")
    
    @classmethod
    def _amount_from_bcd_hex(cls, hex_str, exp=2):
        try:
            digits = cls._bcd_digits(hex_str)
            if not digits:
                return str(hex_str)
            
            if len(digits) > 20:
                logging.warning(f"BCD amount too long: {len(digits)} digits")
                return str(hex_str)
            
            if exp < 0 or exp > 10:
                exp = 2
            
            if len(digits) <= exp:
                digits = digits.zfill(exp + 1)
            
            return digits[:-exp] + "." + digits[-exp:]
        except Exception as e:
            logging.debug(f"Error converting BCD amount: {e}")
            return str(hex_str)
    
    @staticmethod
    def mask_pan_value(pan):
        pan = re.sub(r'[^0-9]', '', pan or '')
        if len(pan) < 10:
            return pan
        return pan[:6] + '*' * (len(pan)-10) + pan[-4:]
    
    @staticmethod
    def parse_track2_ascii(s):
        if not s:
            return None
        m = re.search(r'([0-9]{12,19})(?:=|D)([0-9]{2})([0-9]{2})([0-9]{3})?([0-9]*)', s)
        if not m:
            return None
        pan, yy, mm, svc, disc = m.groups()
        return {
            "pan_mask": DataProcessor.mask_pan_value(pan),
            "pan": pan,
            "pan_len": len(pan),
            "exp_yy": yy,
            "exp_mm": mm,
            "service_code": svc,
            "discretionary": disc,
            "expiry_iso": DataProcessor._yy_mm_to_iso(yy, mm),
            "luhn_ok": DataProcessor.luhn_check(pan)
        }
    
    @staticmethod
    def luhn_check(pan):
        if not isinstance(pan, str):
            raise TypeError("PAN debe ser una cadena")
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
    
    @staticmethod
    def _yy_mm_to_iso(yy, mm):
        try:
            y = int(yy)
            m = int(mm)
            if not (0 <= y <= 99) or not (1 <= m <= 12):
                return f"20{yy}-{mm}"
            century = 2000 if y <= 79 else 1900
            return f"{century + y:04d}-{m:02d}"
        except (ValueError, TypeError) as e:
            logging.debug(f"Error converting date {yy}/{mm}: {e}")
            return f"20{yy}-{mm}"
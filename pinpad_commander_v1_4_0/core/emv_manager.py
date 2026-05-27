#!/usr/bin/env python3
"""
Gestor de tags EMV
"""

import os
import json
import re
import logging

class EMVManager:
    """Maneja las operaciones relacionadas con tags EMV"""
    
    def __init__(self, app):
        self.app = app
        self.EMV_TAG_NAMES = {}
        self.emv_special = {}
    
    def load_emv_tags(self):
        """Cargar diccionario de tags EMV desde configuración"""
        try:
            emv_config_path = os.path.join("config", "emv_tags.json")
            if os.path.exists(emv_config_path):
                with open(emv_config_path, "r", encoding="utf-8") as f:
                    emv_config = json.load(f)
                    self.EMV_TAG_NAMES = emv_config.get("tags", {})
                    self.emv_special = emv_config.get("special_processing", {})
            else:
                # Fallback básico si no existe el archivo
                self.EMV_TAG_NAMES = {
                    "9F02":"importe","9F03":"cashback","9A":"fecha","9C":"tipo_txn","95":"TVR","9F26":"ARQC",
                    "84":"AID","82":"AIP","5F2A":"Moneda"
                }
                self.emv_special = {"amounts": ["9F02", "9F03"], "dates": ["9A"], "currencies": ["5F2A"]}
        except Exception as e:
            logging.warning(f"Error cargando tags EMV: {e}")
            self.EMV_TAG_NAMES = {}
            self.emv_special = {}
    
    def bcd_digits(self, hex_str: str) -> str:
        """Extraer dígitos BCD de una cadena hexadecimal"""
        hex_str = re.sub(r"[^0-9A-Fa-f]", "", hex_str or "")
        return "".join(str(int(ch, 16)) for ch in hex_str if ch in "0123456789ABCDEFabcdef")
    
    def amount_from_bcd_hex(self, hex_str: str, exp: int = 2):
        """Convertir cantidad BCD hexadecimal a formato decimal"""
        digits = self.bcd_digits(hex_str)
        if not digits: 
            return hex_str
        if len(digits) <= exp: 
            digits = digits.zfill(exp + 1)
        return digits[:-exp] + "." + digits[-exp:]
    
    def emv_pretty(self, tlv: dict):
        """Convertir tags EMV a formato legible con nombres descriptivos"""
        if not isinstance(tlv, dict): 
            return tlv
        pretty = {}
        exp = 2
        
        for tag, val in tlv.items():
            name = self.EMV_TAG_NAMES.get(tag, tag)
            if tag in self.emv_special.get("amounts", []):
                pretty[name] = self.amount_from_bcd_hex(val, exp)
            elif tag in self.emv_special.get("dates", []) and len(val) == 6:
                yy, mm, dd = val[0:2], val[2:4], val[4:6]
                pretty[name] = f"20{yy}-{mm}-{dd}"
            elif tag in self.emv_special.get("currencies", []) and len(val) == 4:
                pretty[name] = self.bcd_digits(val).zfill(3)
            else:
                pretty[name] = val
        return pretty
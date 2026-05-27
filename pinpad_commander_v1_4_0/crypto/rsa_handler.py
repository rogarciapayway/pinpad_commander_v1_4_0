import re
import logging
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, PKCS1_OAEP
from Crypto.Hash import SHA1

class RSAHandler:
    def __init__(self):
        self.private_key = None
    
    def _validate_path(self, path):
        """Validar ruta para prevenir path traversal"""
        try:
            # Normalizar y resolver la ruta
            abs_path = os.path.abspath(os.path.normpath(path))
            
            # Verificar que el archivo existe y es un archivo regular
            if not os.path.isfile(abs_path):
                raise ValueError(f"File not found or not a regular file: {path}")
            
            # Verificar extensión permitida
            if not abs_path.lower().endswith(('.pem', '.key')):
                raise ValueError(f"Invalid file extension. Only .pem and .key files allowed")
            
            # Verificar que no contenga secuencias peligrosas
            if ".." in path or path.startswith("/") or "\\\\" in path:
                raise ValueError(f"Potentially unsafe path: {path}")
            
            return abs_path
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid file path: {e}")
    
    def load_key_from_file(self, path):
        try:
            validated_path = self._validate_path(path)
            with open(validated_path, "rb") as f:
                key_data = f.read()
            self.private_key = RSA.import_key(key_data)
            logging.info(f"RSA key loaded successfully from {os.path.basename(validated_path)}")
            return True
        except (ValueError, OSError) as e:
            logging.error(f"Failed to load RSA key from {path}: {e}")
            raise ValueError(f"Failed to load RSA key: {e}")
        except Exception as e:
            logging.error(f"Unexpected error loading RSA key from {path}: {e}")
            raise RuntimeError(f"Failed to load RSA key from {path}: {e}")
    
    def get_key_params(self):
        if not self.private_key:
            return None
        try:
            n = getattr(self.private_key, "n", None)
            d = getattr(self.private_key, "d", None)
            if n is None or d is None:
                return None
            k = (n.bit_length() + 7) // 8
            return n, d, k
        except Exception:
            return None
    
    def decrypt_raw(self, cipher_bytes):
        params = self.get_key_params()
        if not params:
            return {"error": "No hay clave RSA válida cargada"}
        
        n, d, k = params
        c = cipher_bytes
        
        # Validar tamaño de entrada
        if len(c) == 0:
            return {"error": "Cipher data is empty"}
        
        if len(c) != k:
            if len(c) < k:
                c = (b"\x00" * (k - len(c))) + c
            else:
                c = c[-k:]
        
        c_int = int.from_bytes(c, "big", signed=False)
        try:
            # Validar que c_int < n para evitar errores de módulo
            if c_int >= n:
                return {"error": "Cipher value too large for key modulus"}
            m_int = pow(c_int, d, n)
        except (ValueError, OverflowError) as e:
            logging.error(f"RSA decryption error: {e}")
            return {"error": f"RSA decryption failed: {e}"}
        except Exception as e:
            logging.error(f"Unexpected RSA error: {e}")
            return {"error": f"Unexpected decryption error: {e}"}
        
        try:
            pt = m_int.to_bytes(k, "big", signed=False)
            hex_out = pt.hex().upper()
            ascii_out = "".join(chr(x) for x in pt if 32 <= x <= 126)
            
            return {
                "rsa_plain_hex": hex_out,
                "rsa_plain_ascii": ascii_out,
                "k": k
            }
        except (ValueError, OverflowError) as e:
            logging.error(f"Error converting decrypted data: {e}")
            return {"error": f"Failed to convert decrypted data: {e}"}
    
    def decrypt_pkcs_or_oaep(self, cipher_bytes, padding="PKCS1v15"):
        if not self.private_key:
            return {"error": "No RSA private key loaded"}
        
        if not cipher_bytes:
            return {"error": "Cipher data is empty"}
        
        try:
            if padding == "OAEP-SHA1":
                cipher = PKCS1_OAEP.new(self.private_key, hashAlgo=SHA1)
                pt = cipher.decrypt(cipher_bytes)
            else:
                cipher = PKCS1_v1_5.new(self.private_key)
                sentinel = b"__RSA_FAIL__"
                pt = cipher.decrypt(cipher_bytes, sentinel)
                if pt == sentinel:
                    return {"error": "RSA PKCS#1 v1.5: decryption failed"}
        except (ValueError, TypeError) as e:
            logging.error(f"RSA {padding} decryption error: {e}")
            return {"error": f"RSA {padding} decryption failed: {e}"}
        except (ValueError, TypeError, OverflowError) as e:
            logging.error(f"RSA decryption error: {e}")
            return {"error": f"RSA decrypt error: {e}"}
        except Exception as e:
            logging.error(f"Unexpected RSA error: {e}")
            return {"error": "RSA decryption failed"}
        
        try:
            hex_out = pt.hex().upper()
            ascii_out = "".join(chr(c) for c in pt if 32 <= c <= 126)
            
            return {
                "rsa_plain_hex": hex_out,
                "rsa_plain_ascii": ascii_out
            }
        except Exception as e:
            logging.error(f"Error processing decrypted data: {e}")
            return {"error": f"Failed to process decrypted data: {e}"}
    
    def decrypt_bytes(self, cipher_bytes, mode="PKCS1v15"):
        if mode == "RAW-NoPadding":
            return self.decrypt_raw(cipher_bytes)
        elif mode in ["PKCS1v15", "OAEP-SHA1"]:
            return self.decrypt_pkcs_or_oaep(cipher_bytes, mode)
        else:
            # Fallback para modos desconocidos
            return self.decrypt_pkcs_or_oaep(cipher_bytes, "PKCS1v15")
    
    def hex_to_bytes_safe(self, hex_str):
        try:
            if not hex_str:
                return b""
            # Sanitizar entrada para prevenir inyección
            clean_hex = re.sub(r"[^0-9A-Fa-f]", "", str(hex_str))
            if len(clean_hex) % 2 != 0:
                clean_hex = "0" + clean_hex
            return bytes.fromhex(clean_hex)
        except (ValueError, TypeError) as e:
            logging.debug(f"Error converting hex string: {str(hex_str)[:50]}... - {e}")
            return b""
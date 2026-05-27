
from __future__ import annotations
import os, json, time, logging
from typing import Optional

def _import_rsa():
    try:
        from Crypto.PublicKey import RSA  # type: ignore
        return RSA
    except Exception as e:
        raise RuntimeError("Necesitás pycryptodome. Instalalo con: pip install pycryptodome") from e

def _validate_pem_path(pem_path: str) -> str:
    """Validar ruta PEM para prevenir path traversal"""
    try:
        abs_path = os.path.abspath(pem_path)
        if not os.path.isfile(abs_path):
            raise ValueError(f"File not found: {pem_path}")
        if not abs_path.lower().endswith(('.pem', '.key')):
            raise ValueError(f"Invalid file extension: {pem_path}")
        return abs_path
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid PEM path: {e}")

def _read_pem_get_n_e(pem_path: str):
    RSA = _import_rsa()
    try:
        validated_path = _validate_pem_path(pem_path)
        with open(validated_path, "rb") as f:
            key_data = f.read()
            if len(key_data) > 65536:
                raise ValueError("PEM file too large")
            key = RSA.import_key(key_data)
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise FileNotFoundError(f"Error al leer archivo PEM: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid PEM file: {e}")
    
    if not hasattr(key, "n") or not hasattr(key, "e"):
        raise ValueError("La clave no parece RSA (no encuentro n/e).")
    return int(key.n), int(key.e)

def _hex_modulus_padded(n: int) -> str:
    kbytes = (n.bit_length() + 7) // 8
    return format(n, "X").upper().rjust(kbytes * 2, "0")

def _hex_exponent(e: int) -> str:
    return format(e, "X").upper()

def _guess_commands_json_paths() -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "config", "commands.json"),
        os.path.join(os.getcwd(), "config", "commands.json"),
        "config/commands.json",
    ]
    seen, uniq = set(), []
    for p in candidates:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq

def _validate_commands_json_path(commands_json_path: Optional[str]) -> str:
    """Validar ruta de commands.json de forma segura"""
    if commands_json_path is None:
        for cand in _guess_commands_json_paths():
            if os.path.isfile(cand):
                commands_json_path = cand
                break
    
    if not commands_json_path:
        raise FileNotFoundError("No pude encontrar config/commands.json")
    
    try:
        abs_path = os.path.abspath(commands_json_path)
        allowed_dirs = [
            os.path.abspath("config"),
            os.path.abspath(os.path.dirname(__file__)),
            os.path.abspath(os.getcwd())
        ]
        
        path_allowed = False
        for allowed_dir in allowed_dirs:
            if not allowed_dir.endswith(os.sep):
                allowed_dir += os.sep
            if abs_path.startswith(allowed_dir) or abs_path == allowed_dir.rstrip(os.sep):
                path_allowed = True
                break
        
        if not path_allowed:
            raise ValueError(f"Path not allowed: {commands_json_path}")
        
        if not abs_path.lower().endswith('.json'):
            raise ValueError(f"Invalid extension: {commands_json_path}")
        
        return abs_path
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path: {e}")

def _persist_rsa_default_to_commands_json(n_hex: str, commands_json_path: Optional[str]=None) -> str:
    if not n_hex or not isinstance(n_hex, str) or len(n_hex) > 8192:
        raise ValueError("Invalid RSA hex value")
    
    commands_json_path = _validate_commands_json_path(commands_json_path)

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = f"{commands_json_path}.bak.{ts}"
    
    try:
        with open(commands_json_path, "rb") as f_in, open(bak, "wb") as f_out:
            f_out.write(f_in.read())
    except (IOError, PermissionError, OSError) as e:
        raise IOError(f"Error al crear backup: {e}")

    try:
        with open(commands_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        raise ValueError(f"Error al leer JSON: {e}")

    if isinstance(data, dict) and isinstance(data.get("commands"), dict):
        cmds = data["commands"]
    elif isinstance(data, dict) and isinstance(data.get("commands"), list):
        cmds = data["commands"]
    else:
        raise ValueError("commands.json: formato no soportado (se espera dict con 'commands').")

    if isinstance(cmds, dict):
        y19 = cmds.get("Y19")
    else:
        y19 = next((c for c in cmds if isinstance(c, dict) and c.get("id") == "Y19"), None)
    if not y19:
        raise KeyError("No encontré comando Y19 en commands.json.")

    fields = (y19.get("request") or {}).get("fields", [])
    rsa_param = next((p for p in fields if isinstance(p, dict) and p.get("name") == "RSA"), None)
    if not rsa_param:
        raise KeyError("No encontré el parámetro 'RSA' dentro de Y19.")

    rsa_param["default"] = n_hex

    try:
        with open(commands_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except (IOError, PermissionError) as e:
        raise IOError(f"Error al escribir JSON: {e}")

    return commands_json_path

def attach_y19_autopem_support(AppClass):
    if getattr(AppClass, "_Y19_AUTOMEMO_APPLIED", False):
        return AppClass

    orig_init = getattr(AppClass, "__init__", None)
    def __init__(self, *args, **kwargs):
        if orig_init: orig_init(self, *args, **kwargs)
        self._last_public_pem_path: Optional[str] = None
    AppClass.__init__ = __init__

    def _on_load_public_pem_into_y19(self, pem_path: Optional[str]=None, commands_json_path: Optional[str]=None):
        from tkinter import filedialog, messagebox
        try:
            import customtkinter as ctk
        except ImportError:
            from tkinter import ttk
        try:
            if pem_path is None:
                initialdir = os.path.dirname(self._last_public_pem_path) if getattr(self, "_last_public_pem_path", None) else None
                pem_path = filedialog.askopenfilename(
                    title="Seleccionar clave pública (public.pem)",
                    filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
                    initialdir=initialdir if initialdir else "/"
                )
                if not pem_path:
                    return

            n, e = _read_pem_get_n_e(pem_path)
            n_hex = _hex_modulus_padded(n)
            e_hex = _hex_exponent(e)

            rsa_w = getattr(self, "params_widgets", {}).get("RSA")
            exp_w = getattr(self, "params_widgets", {}).get("EXP")
            if rsa_w: rsa_w.delete(0, "end"); rsa_w.insert(0, n_hex)
            if exp_w: exp_w.delete(0, "end"); exp_w.insert(0, e_hex)

            self._last_public_pem_path = pem_path

            saved_path = _persist_rsa_default_to_commands_json(n_hex, commands_json_path)

            # Log de parseo
            if hasattr(self, "_append_log"):
                try:
                    bits = len(n_hex) * 4
                    n_preview = f"{n_hex[:16]}...{n_hex[-16:]}" if len(n_hex) > 32 else n_hex
                    self._append_log(f"[public.pem] Archivo: {pem_path}")
                    self._append_log(f"[public.pem] Tamaño clave: {bits} bits")
                    self._append_log(f"[public.pem] Persistido default RSA en: {saved_path}")
                except Exception:
                    pass

            # Actualizar cfg en memoria
            try:
                cfg = getattr(self, "cfg", None)
                if isinstance(cfg, dict) and "commands" in cfg:
                    y19 = cfg["commands"].get("Y19 Transacción")
                    if y19:
                        for p in y19.get("request", {}).get("fields", []):
                            if p.get("name") == "RSA":
                                p["default"] = n_hex
                                break
            except Exception:
                pass

            # Re-render preservando valores (excepto RSA que forzamos al nuevo)
            try:
                snapshot = {}
                for name, w in getattr(self, "params_widgets", {}).items():
                    try: 
                        snapshot[name] = w.get()
                    except Exception as e: 
                        logging.debug(f"Error obteniendo valor de {name}: {e}")
                self._render_param_fields()
                for name, val in snapshot.items():
                    if name != "RSA":
                        w = getattr(self, "params_widgets", {}).get(name)
                        if w:
                            try: 
                                w.delete(0,"end"); w.insert(0, val)
                            except Exception as e: 
                                logging.debug(f"Error restaurando valor de {name}: {e}")
                w = getattr(self, "params_widgets", {}).get("RSA")
                if w: 
                    w.delete(0,"end"); w.insert(0, n_hex)
            except Exception as e:
                logging.debug(f"Error en re-render: {e}")

            try: 
                self.update_idletasks()
            except Exception as e:
                logging.debug(f"Error en update_idletasks: {e}")

            if hasattr(self, "status") and getattr(self, "status", None) is not None:
                try: 
                    self.status.set(f"Clave pública cargada ({len(n_hex)*4} bits). Default RSA persistido en {saved_path}")
                except Exception as e:
                    logging.debug(f"Error actualizando status: {e}")
            else:
                messagebox.showinfo("Y19", f"Default RSA actualizado en:\n{saved_path}")

        except Exception as ex:
            try:
                if hasattr(self, "status") and getattr(self, "status", None) is not None:
                    self.status.set(f"Error al cargar/persistir RSA: {ex}")
                else:
                    messagebox.showerror("Error", f"{ex}")
            except Exception as e:
                logging.debug(f"Error mostrando mensaje: {e}")
            raise

    AppClass._on_load_public_pem_into_y19 = _on_load_public_pem_into_y19

    # Envolver render para garantizar el botón junto a RSA
    try:
        _orig_render = getattr(AppClass, "_render_param_fields", None)
        if callable(_orig_render):
            def _render_param_fields_wrapped(self, *args, **kwargs):
                res = _orig_render(self, *args, **kwargs)
                try:
                    from tkinter import ttk
                    w = getattr(self, "params_widgets", {}).get("RSA")
                    if w:
                        row = w.grid_info().get("row", 0)
                        if hasattr(self, "_btn_load_public_pem") and self._btn_load_public_pem:
                            try: self._btn_load_public_pem.destroy()
                            except Exception: pass
                        # Crear botón con CustomTkinter
                        try:
                            import customtkinter as ctk
                            self._btn_load_public_pem = ctk.CTkButton(
                                w.master,  # Usar el contenedor padre del widget RSA
                                text="📁 Cargar public.pem",
                                width=150,
                                command=getattr(self, "_on_load_public_pem_into_y19", lambda: None)
                            )
                            self._btn_load_public_pem.pack(side="right", padx=10)
                        except ImportError:
                            # Fallback a tkinter estándar
                            from tkinter import ttk
                            self._btn_load_public_pem = ttk.Button(
                                self.params_frame,
                                text="Cargar public.pem…",
                                command=getattr(self, "_on_load_public_pem_into_y19", lambda: None)
                            )
                            try:
                                self._btn_load_public_pem.grid(row=row, column=2, sticky="w", padx=6, pady=2)
                            except Exception:
                                self._btn_load_public_pem.pack(side="right", padx=10)
                except Exception as e:
                    logging.debug(f"Error creando botón: {e}")
                return res
            AppClass._render_param_fields = _render_param_fields_wrapped
    except Exception as e:
        logging.debug(f"Error en wrapper de render: {e}")

    AppClass._Y19_AUTOMEMO_APPLIED = True
    return AppClass

attach = attach_y19_autopem_support

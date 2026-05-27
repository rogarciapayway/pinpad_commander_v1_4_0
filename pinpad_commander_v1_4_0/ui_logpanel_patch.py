
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import logging

def attach_log_panel(AppClass):
    if getattr(AppClass, "_LOGPANEL_APPLIED", False):
        return AppClass

    orig_init = getattr(AppClass, "__init__", None)
    def __init__(self, *args, **kwargs):
        if orig_init: orig_init(self, *args, **kwargs)
        try:
            style = ttk.Style(self)
            try: 
                style.theme_use("clam")
            except tk.TclError as e: 
                logging.debug(f"Error configurando tema: {e}")
            style.configure("TLabel", padding=(2, 1))
            style.configure("TButton", padding=(10, 6))
            style.configure("Section.TLabelframe", padding=10)
            style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        except Exception as e:
            logging.debug(f"Error configurando estilos: {e}")
        try:
            self.bind_all("<Control-Shift-C>", lambda e: getattr(self, "_copy_log", lambda: None)())
            self.bind_all("<Control-Shift-K>", lambda e: getattr(self, "_clear_log", lambda: None)())
        except Exception as e:
            logging.debug(f"Error configurando atajos: {e}")
    AppClass.__init__ = __init__

    def _build_log_panel(self):
        try:
            if getattr(self, "_log_frame", None) and getattr(self, "_log_text", None):
                return
            self._log_frame = ttk.LabelFrame(self, text="Log de parseo RSA", style="Section.TLabelframe")
            try: next_row = self.grid_size()[1] if hasattr(self, "grid_size") else 99
            except Exception: next_row = 99
            self._log_frame.grid(row=next_row, column=0, columnspan=3, sticky="nsew", padx=8, pady=(6, 8))
            try:
                self.grid_rowconfigure(next_row, weight=1)
                self.grid_columnconfigure(0, weight=1)
            except Exception:
                pass
            bar = ttk.Frame(self._log_frame)
            bar.pack(side="top", fill="x")
            ttk.Label(bar, text="Atajos: Ctrl+Shift+C = Copiar  |  Ctrl+Shift+K = Limpiar").pack(side="left", padx=4)
            self._btn_copy_log = ttk.Button(bar, text="Copiar", command=lambda: getattr(self, "_copy_log")())
            self._btn_copy_log.pack(side="right", padx=4)
            self._btn_clear_log = ttk.Button(bar, text="Limpiar", command=lambda: getattr(self, "_clear_log")())
            self._btn_clear_log.pack(side="right")
            # Ajustar altura y fuente según resolución
            try:
                screen_height = self.winfo_screenheight()
                log_height = 8 if screen_height < 900 else 12 if screen_height < 1200 else 15
                log_font_size = 9 if screen_height < 900 else 10 if screen_height < 1200 else 11
            except:
                log_height, log_font_size = 12, 10
                
            self._log_text = scrolledtext.ScrolledText(self._log_frame, wrap="none", height=log_height)
            try: 
                self._log_text.configure(font=("Consolas", log_font_size), bg="#2c3e50", fg="#ecf0f1", 
                                       insertbackground="#ecf0f1", selectbackground="#34495e")
            except Exception as e: 
                logging.debug(f"Error configurando fuente: {e}")
            self._log_text.configure(state="disabled")
            self._log_text.pack(side="top", fill="both", expand=True, padx=5, pady=(0, 5))
        except Exception:
            pass
    AppClass._build_log_panel = _build_log_panel

    def _append_log(self, msg: str):
        try:
            if not getattr(self, "_log_text", None):
                self._build_log_panel()
            self._log_text.configure(state="normal")
            self._log_text.insert("end", (msg if msg.endswith("\n") else msg + "\n"))
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        except Exception as e:
            logging.debug(f"Error agregando al log: {e}")
    def _clear_log(self):
        try:
            if getattr(self, "_log_text", None):
                self._log_text.configure(state="normal")
                self._log_text.delete("1.0", "end")
                self._log_text.configure(state="disabled")
        except Exception as e:
            logging.debug(f"Error limpiando log: {e}")
    def _copy_log(self):
        try:
            if getattr(self, "_log_text", None):
                text = self._log_text.get("1.0", "end-1c")
                self.clipboard_clear()
                self.clipboard_append(text)
        except Exception as e:
            logging.debug(f"Error copiando log: {e}")

    AppClass._append_log = _append_log
    AppClass._clear_log = _clear_log
    AppClass._copy_log = _copy_log

    try:
        orig_build = getattr(AppClass, "_build_ui", None)
        if callable(orig_build):
            def _build_ui_wrapped(self, *args, **kwargs):
                res = orig_build(self, *args, **kwargs)
                try: self._build_log_panel()
                except Exception: pass
                return res
            AppClass._build_ui = _build_ui_wrapped
    except Exception:
        pass

    AppClass._LOGPANEL_APPLIED = True
    return AppClass

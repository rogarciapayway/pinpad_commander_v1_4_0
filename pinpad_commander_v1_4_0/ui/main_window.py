import customtkinter as ctk
import tkinter as tk
from core.scroll_manager import ScrollManager

# Configurar tema de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self, title="PinPad Commander", version="1.4.0"):
        super().__init__()
        self.title(f"🔐 {title} v{version}")
        
        # Configurar ventana
        self._setup_window()
        
        # Inicializar gestor de scroll
        self.scroll_manager = ScrollManager(self)
        
        # Crear paneles
        self._create_panels()
        
        # Configurar scroll después de crear paneles
        self.after(100, self._setup_all_scrolls)
    
    def _setup_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        min_width, min_height = 1100, 650
        max_width, max_height = 1600, 1000
        
        window_width = max(min_width, min(window_width, max_width))
        window_height = max(min_height, min(window_height, max_height))
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(min_width, min_height)
        
        # Configurar grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
    
    def _create_panels(self):
        # Header compacto
        self._create_header()
        
        # Panel principal con scroll
        self._create_main_panel()
        
        # Status bar
        self._create_status_bar()
    
    def _create_header(self):
        header_frame = ctk.CTkFrame(self, height=50, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,5))
        header_frame.grid_propagate(False)
        
        title_label = ctk.CTkLabel(header_frame, 
                                  text="🔐 PinPad Commander v1.4.0", 
                                  font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(expand=True)
    
    def _create_main_panel(self):
        main_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        
        self.scrollable_frame = main_frame
        
        # Crear paneles compactos
        self._create_connection_panel()
        self._create_command_panel()
        self._create_communication_panel()
    
    def _create_connection_panel(self):
        """Crear panel de conexión compacto"""
        conn_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=8, height=95)
        conn_frame.pack(fill="x", padx=5, pady=3)
        conn_frame.pack_propagate(False)
        
        # Contenido en una sola fila compacta
        content_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=8)
        
        # Grupo 1: Conexión
        conn_group = ctk.CTkFrame(content_frame, fg_color="transparent")
        conn_group.pack(side="left", fill="y")
        
        ctk.CTkLabel(conn_group, text="🔌 Puerto:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        port_row = ctk.CTkFrame(conn_group, fg_color="transparent")
        port_row.pack(fill="x", pady=(2,0))
        
        self.port_combo = ctk.CTkComboBox(port_row, width=150, height=26, state="readonly")
        self.port_combo.pack(side="left", padx=(0,3))
        
        self.refresh_btn = ctk.CTkButton(port_row, text="🔄", width=25, height=26)
        self.refresh_btn.pack(side="left", padx=(0,3))
        
        # Tooltip para el botón de refresh
        from ui.tooltip import ToolTip
        ToolTip(self.refresh_btn, "Refrescar lista de puertos COM")
        
        self.baud_combo = ctk.CTkComboBox(port_row, width=80, height=26, 
                                         values=["115200", "230400"], state="normal")
        self.baud_combo.set("115200")
        self.baud_combo.pack(side="left", padx=2)
        
        self.timeout_entry = ctk.CTkEntry(port_row, width=40, height=26, placeholder_text="1.0")
        self.timeout_entry.insert(0, "1.0")
        self.timeout_entry.pack(side="left", padx=2)
        
        self.connect_btn = ctk.CTkButton(port_row, text="🔌 Conectar", width=70, height=26)
        self.connect_btn.pack(side="left", padx=(3,0))
        
        # Separador
        ctk.CTkFrame(content_frame, width=1, fg_color="gray40").pack(side="left", fill="y", padx=10)
        
        # Grupo 2: Archivos
        files_group = ctk.CTkFrame(content_frame, fg_color="transparent")
        files_group.pack(side="left", fill="y")
        
        ctk.CTkLabel(files_group, text="📁 Archivos:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        files_row = ctk.CTkFrame(files_group, fg_color="transparent")
        files_row.pack(fill="x", pady=(2,0))
        
        self.rsa_btn = ctk.CTkButton(files_row, text="🔑 RSA", width=50, height=26)
        self.rsa_btn.pack(side="left", padx=(0,3))
        
        self.pub_btn = ctk.CTkButton(files_row, text="📄 PUB", width=45, height=26)
        self.pub_btn.pack(side="left", padx=(0,3))
        
        self.config_btn = ctk.CTkButton(files_row, text="⚙️ Config", width=55, height=26)
        self.config_btn.pack(side="left", padx=(0,3))
        
        # Padding RSA
        self.rsa_padding_combo = ctk.CTkComboBox(files_row, width=80, height=26, 
                                               values=["RAW-NoPadding", "OAEP-SHA1", "PKCS1v15"],
                                               state="readonly")
        self.rsa_padding_combo.set("RAW-NoPadding")
        self.rsa_padding_combo.pack(side="left")
        
        # Separador
        ctk.CTkFrame(content_frame, width=1, fg_color="gray40").pack(side="left", fill="y", padx=10)
        
        # Grupo 3: Opciones
        options_group = ctk.CTkFrame(content_frame, fg_color="transparent")
        options_group.pack(side="left", fill="y")
        
        ctk.CTkLabel(options_group, text="⚙️ Opciones:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        options_row = ctk.CTkFrame(options_group, fg_color="transparent")
        options_row.pack(fill="x", pady=(2,0))
        
        self.timestamps_var = tk.BooleanVar(value=True)
        timestamps_cb = ctk.CTkCheckBox(options_row, text="⏰", variable=self.timestamps_var, width=30)
        timestamps_cb.pack(side="left", padx=(0,5))
        
        self.mask_pan_var = tk.BooleanVar(value=True)
        mask_cb = ctk.CTkCheckBox(options_row, text="🔒 Enmascarar", variable=self.mask_pan_var, width=30)
        mask_cb.pack(side="left")
        
        # Separador
        ctk.CTkFrame(content_frame, width=1, fg_color="gray40").pack(side="left", fill="y", padx=10)
        
        # Grupo 4: Bridge ISO
        bridge_group = ctk.CTkFrame(content_frame, fg_color="transparent")
        bridge_group.pack(side="left", fill="y")
        
        ctk.CTkLabel(bridge_group, text="🌐 Bridge ISO:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        bridge_row = ctk.CTkFrame(bridge_group, fg_color="transparent")
        bridge_row.pack(fill="x", pady=(2,0))
        
        self.bridge_var = tk.BooleanVar(value=False)
        self.bridge_switch = ctk.CTkSwitch(bridge_row, text="", variable=self.bridge_var,
                                           width=40, command=self._on_bridge_toggle)
        self.bridge_switch.pack(side="left", padx=(0,3))
        
        self.bridge_status_label = ctk.CTkLabel(bridge_row, text="OFF",
                                                font=ctk.CTkFont(size=10), text_color="gray50")
        self.bridge_status_label.pack(side="left", padx=(0,5))
        
        self.bridge_echo_btn = ctk.CTkButton(bridge_row, text="Echo", width=40, height=22,
                                             state="disabled")
        self.bridge_echo_btn.pack(side="left", padx=(0,3))
        
        # Fila 2: Terminal / Merchant
        bridge_row2 = ctk.CTkFrame(bridge_group, fg_color="transparent")
        bridge_row2.pack(fill="x", pady=(2,0))
        
        self.bridge_terminal_entry = ctk.CTkEntry(bridge_row2, width=75, height=22,
                                                   placeholder_text="Terminal",
                                                   font=ctk.CTkFont(size=9))
        self.bridge_terminal_entry.insert(0, "74000025")
        self.bridge_terminal_entry.pack(side="left", padx=(0,3))
        
        self.bridge_merchant_entry = ctk.CTkEntry(bridge_row2, width=75, height=22,
                                                   placeholder_text="Merchant",
                                                   font=ctk.CTkFont(size=9))
        self.bridge_merchant_entry.insert(0, "03659307")
        self.bridge_merchant_entry.pack(side="left")
        
        # Crear objeto connection_panel para compatibilidad
        self.connection_panel = type('ConnectionPanel', (), {
            'connect_btn': self.connect_btn,
            'rsa_btn': self.rsa_btn,
            'pub_btn': self.pub_btn,
            'config_btn': self.config_btn,
            'port_combo': self.port_combo,
            'baud_entry': self.baud_combo,  # Mantener nombre para compatibilidad
            'timeout_entry': self.timeout_entry,
            'timestamps_var': self.timestamps_var,
            'mask_pan_var': self.mask_pan_var,
            'rsa_padding_combo': self.rsa_padding_combo,
            'refresh_btn': self.refresh_btn,
            'bridge_var': self.bridge_var,
            'bridge_switch': self.bridge_switch,
            'bridge_status_label': self.bridge_status_label,
            'bridge_echo_btn': self.bridge_echo_btn,
            'bridge_terminal_entry': self.bridge_terminal_entry,
            'bridge_merchant_entry': self.bridge_merchant_entry
        })()
    
    def _create_command_panel(self):
        cmd_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=8)
        cmd_frame.pack(fill="both", expand=True, padx=5, pady=3)
        
        # Header compacto
        header_frame = ctk.CTkFrame(cmd_frame, fg_color="transparent", height=50)
        header_frame.pack(fill="x", padx=10, pady=8)
        header_frame.pack_propagate(False)
        
        # Fila única con comando, botones y opciones
        cmd_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        cmd_row.pack(fill="both", expand=True)
        
        # Comando
        cmd_group = ctk.CTkFrame(cmd_row, fg_color="transparent")
        cmd_group.pack(side="left", fill="y")
        
        ctk.CTkLabel(cmd_group, text="📡 Comando:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.cmd_combo = ctk.CTkComboBox(cmd_group, width=180, height=26, state="readonly")
        self.cmd_combo.pack(pady=(2,0))
        
        # Botones
        buttons_group = ctk.CTkFrame(cmd_row, fg_color="transparent")
        buttons_group.pack(side="left", fill="y", padx=(15,0))
        
        ctk.CTkLabel(buttons_group, text="🚀 Acciones:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        btn_row = ctk.CTkFrame(buttons_group, fg_color="transparent")
        btn_row.pack(pady=(2,0))
        
        self.send_btn = ctk.CTkButton(btn_row, text="📤 Enviar", width=65, height=26)
        self.send_btn.pack(side="left", padx=(0,3))
        
        self.y02_btn = ctk.CTkButton(btn_row, text="💡 Y02", width=50, height=26, state="disabled")
        self.y02_btn.pack(side="left")
        
        # Opciones
        options_group = ctk.CTkFrame(cmd_row, fg_color="transparent")
        options_group.pack(side="left", fill="y", padx=(15,0))
        
        ctk.CTkLabel(options_group, text="⚙️ Config:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        self.ack_var = tk.BooleanVar(value=True)
        ack_cb = ctk.CTkCheckBox(options_group, text="ACK", variable=self.ack_var, width=40)
        ack_cb.pack(pady=(2,0))
        
        # Descripción
        desc_group = ctk.CTkFrame(cmd_row, fg_color="transparent")
        desc_group.pack(side="right", fill="both", expand=True, padx=(15,0))
        
        ctk.CTkLabel(desc_group, text="📝 Descripción:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.desc_label = ctk.CTkLabel(desc_group, text="", font=ctk.CTkFont(size=10), 
                                      text_color=("gray90", "gray70"), anchor="w")
        self.desc_label.pack(fill="x", pady=(2,0))
        
        # Parámetros más compactos
        self.params_frame = ctk.CTkScrollableFrame(cmd_frame, height=120, corner_radius=6)
        self.params_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
        # El scroll se configurará automáticamente por el ScrollManager
        
        # Crear objeto command_panel para compatibilidad
        self.command_panel = type('CommandPanel', (), {
            'cmd_combo': self.cmd_combo,
            'desc_label': self.desc_label,
            'send_btn': self.send_btn,
            'y02_btn': self.y02_btn,
            'ack_var': self.ack_var,
            'params_frame': self.params_frame
        })()
    
    def _create_communication_panel(self):
        comm_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=8)
        comm_frame.pack(fill="both", expand=True, padx=5, pady=3)
        
        # Pestañas reorganizadas
        notebook = ctk.CTkTabview(comm_frame, height=280)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        
        # 1. Pestaña HEX (ancho completo)
        hex_tab = notebook.add("📡 HEX")
        
        hex_content = ctk.CTkFrame(hex_tab, fg_color="transparent")
        hex_content.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Botones para HEX
        hex_buttons = ctk.CTkFrame(hex_content, fg_color="transparent", height=30)
        hex_buttons.pack(fill="x", pady=(0,5))
        hex_buttons.pack_propagate(False)
        
        self.hex_copy_btn = ctk.CTkButton(hex_buttons, text="📋 Copiar", width=70, height=25)
        self.hex_copy_btn.pack(side="left", padx=(0,5))
        
        self.hex_clear_btn = ctk.CTkButton(hex_buttons, text="🗑️ Limpiar", width=70, height=25)
        self.hex_clear_btn.pack(side="left")
        
        self.hex_text = ctk.CTkTextbox(hex_content, height=150, 
                                      font=ctk.CTkFont(family="Consolas", size=9))
        self.hex_text.pack(fill="both", expand=True, pady=(0,5))
        
        # HEX continuo
        self.raw_hex_entry = ctk.CTkEntry(hex_content, height=22,
                                         font=ctk.CTkFont(family="Consolas", size=8),
                                         placeholder_text="HEX continuo...")
        self.raw_hex_entry.pack(fill="x")
        
        # 2. Pestaña JSON
        json_tab = notebook.add("🔍 JSON")
        
        json_content = ctk.CTkFrame(json_tab, fg_color="transparent")
        json_content.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Botones para JSON
        json_buttons = ctk.CTkFrame(json_content, fg_color="transparent", height=30)
        json_buttons.pack(fill="x", pady=(0,5))
        json_buttons.pack_propagate(False)
        
        self.json_copy_btn = ctk.CTkButton(json_buttons, text="📋 Copiar", width=70, height=25)
        self.json_copy_btn.pack(side="left", padx=(0,5))
        
        self.json_clear_btn = ctk.CTkButton(json_buttons, text="🗑️ Limpiar", width=70, height=25)
        self.json_clear_btn.pack(side="left")
        
        # Usar tkinter Text con colores personalizados para JSON
        import tkinter as tk
        from tkinter import ttk
        
        # Frame para Text con scrollbar personalizada
        text_frame = tk.Frame(json_content, bg="#212121")
        text_frame.pack(fill="both", expand=True)
        
        # Configurar estilo dark para scrollbar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.Vertical.TScrollbar',
                       background='#2b2b2b',
                       troughcolor='#1a1a1a',
                       bordercolor='#2b2b2b',
                       arrowcolor='#ffffff',
                       darkcolor='#2b2b2b',
                       lightcolor='#2b2b2b')
        
        scrollbar = ttk.Scrollbar(text_frame, style='Dark.Vertical.TScrollbar')
        scrollbar.pack(side="right", fill="y")
        
        self.parsed_text = tk.Text(text_frame,
                                  font=("Consolas", 12),
                                  bg="#1a1a1a", fg="#ffffff",
                                  insertbackground="white",
                                  selectbackground="#404040",
                                  wrap="word",
                                  yscrollcommand=scrollbar.set)
        self.parsed_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.parsed_text.yview)
        
        # Configurar colores para JSON
        self._configure_json_colors()
        
        # Menú contextual
        self._create_json_context_menu()
        
        # 3. Pestaña Comandos JSON
        cmd_json_tab = notebook.add("📤 Comandos")
        
        cmd_json_content = ctk.CTkFrame(cmd_json_tab, fg_color="transparent")
        cmd_json_content.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Botones para Comandos JSON
        cmd_json_buttons = ctk.CTkFrame(cmd_json_content, fg_color="transparent", height=30)
        cmd_json_buttons.pack(fill="x", pady=(0,5))
        cmd_json_buttons.pack_propagate(False)
        
        self.cmd_json_copy_btn = ctk.CTkButton(cmd_json_buttons, text="📋 Copiar", width=70, height=25)
        self.cmd_json_copy_btn.pack(side="left", padx=(0,5))
        
        self.cmd_json_clear_btn = ctk.CTkButton(cmd_json_buttons, text="🗑️ Limpiar", width=70, height=25)
        self.cmd_json_clear_btn.pack(side="left")
        
        # Frame para Text con scrollbar personalizada para comandos
        cmd_text_frame = tk.Frame(cmd_json_content, bg="#212121")
        cmd_text_frame.pack(fill="both", expand=True)
        
        cmd_scrollbar = ttk.Scrollbar(cmd_text_frame, style='Dark.Vertical.TScrollbar')
        cmd_scrollbar.pack(side="right", fill="y")
        
        self.cmd_json_text = tk.Text(cmd_text_frame,
                                    font=("Consolas", 12),
                                    bg="#1a1a1a", fg="#ffffff",
                                    insertbackground="white",
                                    selectbackground="#404040",
                                    wrap="word",
                                    yscrollcommand=cmd_scrollbar.set)
        self.cmd_json_text.pack(side="left", fill="both", expand=True)
        cmd_scrollbar.config(command=self.cmd_json_text.yview)
        
        # Configurar colores para JSON de comandos
        self._configure_cmd_json_colors()
        
        # Menú contextual para comandos JSON
        self._create_cmd_json_context_menu()
        
        # 4. Pestaña ISO 8583
        iso_tab = notebook.add("🌐 ISO 8583")
        
        iso_content = ctk.CTkFrame(iso_tab, fg_color="transparent")
        iso_content.pack(fill="both", expand=True, padx=3, pady=3)
        
        iso_buttons = ctk.CTkFrame(iso_content, fg_color="transparent", height=30)
        iso_buttons.pack(fill="x", pady=(0,5))
        iso_buttons.pack_propagate(False)
        
        self.iso_copy_btn = ctk.CTkButton(iso_buttons, text="📋 Copiar", width=70, height=25)
        self.iso_copy_btn.pack(side="left", padx=(0,5))
        
        self.iso_clear_btn = ctk.CTkButton(iso_buttons, text="🗑️ Limpiar", width=70, height=25)
        self.iso_clear_btn.pack(side="left")
        
        self.iso_tls_label = ctk.CTkLabel(iso_buttons, text="TLS: --",
                                          font=ctk.CTkFont(size=9), text_color="gray50")
        self.iso_tls_label.pack(side="right", padx=5)
        
        iso_text_frame = tk.Frame(iso_content, bg="#212121")
        iso_text_frame.pack(fill="both", expand=True)
        
        iso_scrollbar = ttk.Scrollbar(iso_text_frame, style='Dark.Vertical.TScrollbar')
        iso_scrollbar.pack(side="right", fill="y")
        
        self.iso_text = tk.Text(iso_text_frame,
                                font=("Consolas", 11),
                                bg="#0d1117", fg="#c9d1d9",
                                insertbackground="white",
                                selectbackground="#264f78",
                                wrap="word",
                                yscrollcommand=iso_scrollbar.set)
        self.iso_text.pack(side="left", fill="both", expand=True)
        iso_scrollbar.config(command=self.iso_text.yview)
        
        self.iso_text.tag_configure("header", foreground="#58a6ff", font=("Consolas", 11, "bold"))
        self.iso_text.tag_configure("ok", foreground="#3fb950")
        self.iso_text.tag_configure("fail", foreground="#f85149")
        self.iso_text.tag_configure("field", foreground="#d2a8ff")
        self.iso_text.tag_configure("value", foreground="#a5d6ff")
        self.iso_text.tag_configure("dim", foreground="#484f58")
        
        # 5. Pestaña Log
        log_tab = notebook.add("📄 Log")
        
        log_content = ctk.CTkFrame(log_tab, fg_color="transparent")
        log_content.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Header con botones de control
        log_header = ctk.CTkFrame(log_content, fg_color="transparent", height=35)
        log_header.pack(fill="x", pady=(0,5))
        log_header.pack_propagate(False)
        
        ctk.CTkLabel(log_header, text="📄 Log de Aplicación", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", pady=8)
        
        # Botones de control
        btn_frame = ctk.CTkFrame(log_header, fg_color="transparent")
        btn_frame.pack(side="right", pady=5)
        
        self.log_compact_btn = ctk.CTkButton(btn_frame, text="🗂️ Compactar", width=80, height=25)
        self.log_compact_btn.pack(side="left", padx=(0,5))
        
        self.log_clear_btn = ctk.CTkButton(btn_frame, text="🧹 Limpiar", width=70, height=25)
        self.log_clear_btn.pack(side="left")
        
        # Área de log de aplicación
        self.app_log_text = ctk.CTkTextbox(log_content, 
                                          font=ctk.CTkFont(family="Consolas", size=9))
        self.app_log_text.pack(fill="both", expand=True)
        
        # El scroll se configurará automáticamente por el ScrollManager
        
        # Crear objeto communication_panel para compatibilidad
        self.communication_panel = type('CommunicationPanel', (), {
            'hex_text': self.hex_text,
            'parsed_text': self.parsed_text,
            'raw_hex_entry': self.raw_hex_entry,
            'log_frame_tab': log_tab,
            'app_log_text': self.app_log_text,
            'cmd_json_text': self.cmd_json_text,
            'log_compact_btn': self.log_compact_btn,
            'log_clear_btn': self.log_clear_btn,
            'hex_copy_btn': self.hex_copy_btn,
            'hex_clear_btn': self.hex_clear_btn,
            'json_copy_btn': self.json_copy_btn,
            'json_clear_btn': self.json_clear_btn,
            'cmd_json_copy_btn': self.cmd_json_copy_btn,
            'cmd_json_clear_btn': self.cmd_json_clear_btn,
            'iso_text': self.iso_text,
            'iso_copy_btn': self.iso_copy_btn,
            'iso_clear_btn': self.iso_clear_btn,
            'iso_tls_label': self.iso_tls_label
        })()
    
    def _create_json_context_menu(self):
        """Crear menú contextual para el panel JSON"""
        import tkinter as tk
        
        self.json_context_menu = tk.Menu(self, tearoff=0)
        self.json_context_menu.add_command(label="📋 Copiar Selección", command=self._copy_json_selection)
        self.json_context_menu.add_command(label="📋 Copiar Todo", command=self._copy_all_json)
        self.json_context_menu.add_separator()
        self.json_context_menu.add_command(label="🗑️ Limpiar", command=self._clear_json)
        
        # Bind del click derecho
        self.parsed_text.bind("<Button-3>", self._show_json_context_menu)
        
        # Dar foco al widget para capturar eventos de scroll
        self.parsed_text.focus_set()
    
    def _show_json_context_menu(self, event):
        """Mostrar menú contextual"""
        try:
            self.json_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.json_context_menu.grab_release()
    
    def _copy_json_selection(self):
        """Copiar texto seleccionado del JSON"""
        try:
            selected_text = self.parsed_text.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass  # No hay selección
    
    def _copy_all_json(self):
        """Copiar todo el contenido JSON"""
        content = self.parsed_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
    
    def _clear_json(self):
        """Limpiar el panel JSON"""
        self.parsed_text.delete("1.0", "end")
    
    def _configure_cmd_json_colors(self):
        """Configurar colores para resaltado de JSON de comandos"""
        # Definir tags de colores para JSON de comandos (mismos colores que JSON normal)
        self.cmd_json_text.tag_configure("key", foreground="#79c0ff")      # Azul para claves
        self.cmd_json_text.tag_configure("string", foreground="#a5d6ff")   # Azul claro para strings
        self.cmd_json_text.tag_configure("number", foreground="#79c0ff")   # Azul para números
        self.cmd_json_text.tag_configure("boolean", foreground="#ff7b72")  # Rojo para booleanos
        self.cmd_json_text.tag_configure("null", foreground="#8b949e")     # Gris para null
        self.cmd_json_text.tag_configure("brace", foreground="#f85149")    # Rojo para llaves
    
    def _create_cmd_json_context_menu(self):
        """Crear menú contextual para el panel JSON de comandos"""
        import tkinter as tk
        
        self.cmd_json_context_menu = tk.Menu(self, tearoff=0)
        self.cmd_json_context_menu.add_command(label="📋 Copiar Selección", command=self._copy_cmd_json_selection)
        self.cmd_json_context_menu.add_command(label="📋 Copiar Todo", command=self._copy_all_cmd_json)
        self.cmd_json_context_menu.add_separator()
        self.cmd_json_context_menu.add_command(label="🗑️ Limpiar", command=self._clear_cmd_json)
        
        # Bind del click derecho
        self.cmd_json_text.bind("<Button-3>", self._show_cmd_json_context_menu)
        
        # Dar foco al widget para capturar eventos de scroll
        self.cmd_json_text.focus_set()
    
    def _show_cmd_json_context_menu(self, event):
        """Mostrar menú contextual para comandos JSON"""
        try:
            self.cmd_json_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.cmd_json_context_menu.grab_release()
    
    def _copy_cmd_json_selection(self):
        """Copiar texto seleccionado del JSON de comandos"""
        try:
            selected_text = self.cmd_json_text.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass  # No hay selección
    
    def _copy_all_cmd_json(self):
        """Copiar todo el contenido JSON de comandos"""
        content = self.cmd_json_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
    
    def _clear_cmd_json(self):
        """Limpiar el panel JSON de comandos"""
        self.cmd_json_text.delete("1.0", "end")
    
    def _configure_json_colors(self):
        """Configurar colores para resaltado de JSON"""
        # Definir tags de colores para JSON
        self.parsed_text.tag_configure("key", foreground="#79c0ff")      # Azul para claves
        self.parsed_text.tag_configure("string", foreground="#a5d6ff")   # Azul claro para strings
        self.parsed_text.tag_configure("number", foreground="#79c0ff")   # Azul para números
        self.parsed_text.tag_configure("boolean", foreground="#ff7b72")  # Rojo para booleanos
        self.parsed_text.tag_configure("null", foreground="#8b949e")     # Gris para null
        self.parsed_text.tag_configure("brace", foreground="#f85149")    # Rojo para llaves
    

    
    def _create_status_bar(self):
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=6)
        status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5,10))
        status_frame.grid_propagate(False)
        
        # Contenedor compacto
        status_content = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Status principal
        self.status = tk.StringVar(value="✅ Listo")
        status_label = ctk.CTkLabel(status_content, textvariable=self.status,
                                   font=ctk.CTkFont(size=10))
        status_label.pack(side="left")
        
        # Status de conexión
        self.conn_status = tk.StringVar(value="❌ Desconectado")
        conn_label = ctk.CTkLabel(status_content, textvariable=self.conn_status,
                                 font=ctk.CTkFont(size=10))
        conn_label.pack(side="right")
    
    def _on_bridge_toggle(self):
        if self.bridge_var.get():
            self.bridge_status_label.configure(text="ON", text_color="#3fb950")
            self.bridge_echo_btn.configure(state="normal")
        else:
            self.bridge_status_label.configure(text="OFF", text_color="gray50")
            self.bridge_echo_btn.configure(state="disabled")
    
    def _setup_params_scroll_handling(self):
        """Configurar manejo unificado del scroll para el área de parámetros"""
        # El scroll se configurará automáticamente por el ScrollManager
        pass
    
    def _setup_all_scrolls(self):
        """Configurar todos los scrolls usando el ScrollManager"""
        self.scroll_manager.setup_all_scrolls()
    

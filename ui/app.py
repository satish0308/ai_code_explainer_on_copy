"""
Main application — tabbed control panel.
Tabs: Monitor | Test LLM | Logs
"""

import datetime
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_providers import build_provider
from clipboard_monitor import ClipboardMonitor
from config import Config
from ui.popup import ExplanationPopup
from ui.settings import SettingsDialog

# ── Palette ──────────────────────────────────────────────────────────────────
BG = "#1e1e2e"
PANEL = "#181825"
SURFACE = "#313244"
TEXT = "#cdd6f4"
MUTED = "#6c7086"
ACCENT = "#89b4fa"
SUCCESS = "#a6e3a1"
ERROR = "#f38ba8"
WARN = "#fab387"
CODE_BG = "#11111b"
BORDER = "#45475a"

PROVIDER_COLORS = {
    "openai": "#74c7ec",
    "nvidia": "#a6e3a1",
    "gemini": "#f9e2af",
    "ollama": "#cba6f7",
}

# Font definitions - cross-platform compatible
# Uses system UI fonts that work on Windows, macOS, and Linux
import platform

SYSTEM = platform.system()
if SYSTEM == "Darwin":  # macOS
    F_HEADER = ("SF Pro Display", 13, "bold")
    F_UI = ("SF Pro Display", 11)
    F_SMALL = ("SF Pro Display", 10)
    F_MONO = ("Menlo", 10)
    F_LOG = ("Menlo", 9)
elif SYSTEM == "Windows":
    F_HEADER = ("Segoe UI", 13, "bold")
    F_UI = ("Segoe UI", 11)
    F_SMALL = ("Segoe UI", 10)
    F_MONO = ("Consolas", 10)
    F_LOG = ("Consolas", 9)
else:  # Linux
    F_HEADER = ("DejaVu Sans", 11, "bold")
    F_UI = ("DejaVu Sans", 10)
    F_SMALL = ("DejaVu Sans", 9)
    F_MONO = ("DejaVu Sans Mono", 9)
    F_LOG = ("DejaVu Sans Mono", 8)

LOG_COLORS = {
    "INFO": ACCENT,
    "DEBUG": MUTED,
    "WARN": WARN,
    "ERROR": ERROR,
}


# ── App ───────────────────────────────────────────────────────────────────────


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_obj = Config()
        self._active_popup = None
        self._history: list[tuple[str, str]] = []
        self._processing = False
        self._log_queue: queue.Queue = queue.Queue()

        self._setup_window()
        self._apply_ttk_style()
        self._build_ui()
        self._start_monitor()
        self._try_tray()
        self._poll_logs()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Auto Code Explainer")
        self.configure(bg=BG)
        # Increased default size for better visibility
        self.geometry("1100x800+60+60")
        self.minsize(850, 640)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Apply DPI scaling on Windows
        if SYSTEM == "Windows":
            try:
                from ctypes import windll

                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

    def _apply_ttk_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook", background=PANEL, borderwidth=0, tabmargins=0)
        s.configure(
            "TNotebook.Tab",
            background=PANEL,
            foreground=MUTED,
            padding=[18, 8],
            font=F_UI,
            borderwidth=0,
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", ACCENT)],
        )
        s.configure("TFrame", background=BG)
        s.configure("TSeparator", background=BORDER)

    # ── Top header ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=PANEL, pady=10)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        tk.Label(
            hdr,
            text="</> Auto Code Explainer",
            fg=TEXT,
            bg=PANEL,
            font=F_HEADER,
            padx=16,
        ).grid(row=0, column=0, sticky="w")

        self.provider_badge = tk.Label(
            hdr, text="", fg=ACCENT, bg=SURFACE, font=F_SMALL, padx=10, pady=3
        )
        self.provider_badge.grid(row=0, column=1, sticky="w", padx=8)

        # Toggle
        self.toggle_var = tk.BooleanVar(value=self.config_obj.enabled)
        self.toggle_btn = tk.Button(
            hdr,
            text="OFF",
            width=7,
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            command=self._toggle,
        )
        self.toggle_btn.grid(row=0, column=2, padx=6)

        tk.Button(
            hdr,
            text="Settings",
            fg=MUTED,
            bg=SURFACE,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=F_SMALL,
            padx=12,
            pady=4,
            command=self._open_settings,
        ).grid(row=0, column=3, padx=(0, 12))

        # Notebook (tabs)
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=1, column=0, sticky="nsew")

        self._build_monitor_tab()
        self._build_test_tab()
        self._build_logs_tab()

        # Bottom status bar
        bar = tk.Frame(self, bg=PANEL, height=28)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            bar,
            textvariable=self.status_var,
            fg=MUTED,
            bg=PANEL,
            font=F_SMALL,
            anchor="w",
            padx=12,
        ).pack(side="left", fill="y")

        # Init labels
        self._update_toggle_btn()
        self._update_provider_badge()

    # ── Monitor tab ───────────────────────────────────────────────────────────

    def _build_monitor_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Monitor  ")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        # Status strip
        strip = tk.Frame(f, bg=SURFACE, pady=10)
        strip.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        strip.columnconfigure(1, weight=1)

        self.monitor_dot = tk.Label(
            strip, text="●", fg=SUCCESS, bg=SURFACE, font=("DejaVu Sans", 14), padx=10
        )
        self.monitor_dot.grid(row=0, column=0)

        self.monitor_status_lbl = tk.Label(
            strip, text="", fg=TEXT, bg=SURFACE, font=F_UI, anchor="w"
        )
        self.monitor_status_lbl.grid(row=0, column=1, sticky="ew")

        self.proc_lbl = tk.Label(
            strip, text="", fg=WARN, bg=SURFACE, font=F_SMALL, padx=10
        )
        self.proc_lbl.grid(row=0, column=2)

        # Clipboard debug line
        self.clip_lbl = tk.Label(
            f,
            text="Last clipboard read: —",
            fg=MUTED,
            bg=BG,
            font=F_LOG,
            anchor="w",
            padx=16,
        )
        self.clip_lbl.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        # History
        hist_hdr = tk.Frame(f, bg=BG, padx=16, pady=6)
        hist_hdr.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        hist_hdr.columnconfigure(0, weight=1)

        tk.Label(
            hist_hdr,
            text="Recent Snippets  (double-click to re-explain)",
            fg=MUTED,
            bg=BG,
            font=F_SMALL,
        ).grid(row=0, column=0, sticky="w")
        tk.Button(
            hist_hdr,
            text="Clear",
            fg=MUTED,
            bg=BG,
            activebackground=SURFACE,
            relief="flat",
            cursor="hand2",
            font=F_SMALL,
            command=self._clear_history,
        ).grid(row=0, column=1)

        list_frame = tk.Frame(f, bg=BG, padx=16)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        sb = tk.Scrollbar(list_frame, bg=SURFACE, troughcolor=BG)
        sb.grid(row=0, column=1, sticky="ns")

        self.hist_list = tk.Listbox(
            list_frame,
            bg=SURFACE,
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#000",
            relief="flat",
            font=F_MONO,
            activestyle="none",
            cursor="hand2",
            yscrollcommand=sb.set,
            borderwidth=0,
            highlightthickness=0,
        )
        self.hist_list.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        sb.config(command=self.hist_list.yview)
        self.hist_list.bind("<Double-Button-1>", self._reopen_from_history)

    # ── Test LLM tab ─────────────────────────────────────────────────────────

    def _build_test_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Test LLM  ")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=2)
        f.rowconfigure(3, weight=3)

        # Input area
        tk.Label(
            f, text="Paste code to test:", fg=MUTED, bg=BG, font=F_SMALL, anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))

        self.test_input = scrolledtext.ScrolledText(
            f,
            height=10,
            bg=CODE_BG,
            fg=SUCCESS,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=F_MONO,
            wrap="none",
        )
        self.test_input.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))

        # Controls row
        ctrl = tk.Frame(f, bg=BG, padx=16, pady=4)
        ctrl.grid(row=2, column=0, sticky="ew")
        ctrl.columnconfigure(1, weight=1)

        # Prompt selector for test tab
        tk.Label(ctrl, text="Prompt:", fg=MUTED, bg=BG, font=F_SMALL).grid(
            row=0, column=0, padx=(0, 6)
        )

        self.test_prompt_var = tk.StringVar(value=self.config_obj.active_prompt)
        self.test_prompt_combo = ttk.Combobox(
            ctrl,
            textvariable=self.test_prompt_var,
            values=self.config_obj.prompt_names,
            state="readonly",
            font=F_SMALL,
            width=26,
        )
        self.test_prompt_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.explain_btn = tk.Button(
            ctrl,
            text="Explain Code",
            bg=ACCENT,
            fg="#000",
            activebackground="#74c7ec",
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 11, "bold"),
            padx=16,
            pady=6,
            command=self._test_explain,
        )
        self.explain_btn.grid(row=0, column=2)

        self.test_status_lbl = tk.Label(ctrl, text="", fg=MUTED, bg=BG, font=F_SMALL)
        self.test_status_lbl.grid(row=0, column=3, sticky="w", padx=10)

        tk.Button(
            ctrl,
            text="Clear",
            fg=MUTED,
            bg=SURFACE,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=F_SMALL,
            padx=10,
            pady=5,
            command=self._clear_test,
        ).grid(row=0, column=4)

        # Zoom controls for explanation text
        tk.Frame(ctrl, bg=SURFACE, width=1).grid(
            row=0, column=5, sticky="ns", padx=(10, 4)
        )
        tk.Button(
            ctrl,
            text="-",
            fg=MUTED,
            bg=SURFACE,
            activeforeground=TEXT,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            padx=8,
            pady=2,
            command=lambda: self._resize_test_output(-2),
        ).grid(row=0, column=6, padx=(0, 2))
        self._test_output_size_lbl = tk.Label(
            ctrl, text="11pt", fg=MUTED, bg=SURFACE, font=("DejaVu Sans", 9), width=4
        )
        self._test_output_size_lbl.grid(row=0, column=7, padx=(0, 2))
        tk.Button(
            ctrl,
            text="+",
            fg=ACCENT,
            bg=SURFACE,
            activeforeground=TEXT,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            padx=8,
            pady=2,
            command=lambda: self._resize_test_output(+2),
        ).grid(row=0, column=8)

        # Output area
        tk.Label(
            f, text="Explanation:", fg=MUTED, bg=BG, font=F_SMALL, anchor="w"
        ).grid(row=3, column=0, sticky="new", padx=16, pady=(4, 2))

        self.test_output = scrolledtext.ScrolledText(
            f,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=F_UI,
            wrap="word",
            spacing1=2,
            spacing3=2,
            state="disabled",
        )
        self.test_output.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.test_output.tag_configure("error", foreground=ERROR)
        self.test_output.tag_configure("done_marker", foreground=SUCCESS)

        # Zoom controls for explanation text
        self._test_output_font_size = 11  # default size
        self.test_output.bind("<Control-MouseWheel>", self._on_test_output_zoom)
        self.test_output.bind("<Control-Button-4>", self._on_test_output_zoom)
        self.test_output.bind("<Control-Button-5>", self._on_test_output_zoom)

        self._test_queue: queue.Queue = queue.Queue()

    # ── Logs tab ──────────────────────────────────────────────────────────────

    def _build_logs_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Logs  ")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)

        log_frame = tk.Frame(f, bg=PANEL, padx=0, pady=0)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            bg=PANEL,
            fg=MUTED,
            insertbackground=TEXT,
            relief="flat",
            font=F_LOG,
            wrap="word",
            state="disabled",
        )
        self.log_box.grid(row=0, column=0, sticky="nsew")

        for level, color in LOG_COLORS.items():
            self.log_box.tag_configure(level, foreground=color)
        self.log_box.tag_configure("TIME", foreground="#45475a")
        self.log_box.tag_configure("MSG", foreground=TEXT)

        # Zoom controls for log text
        self._log_font_size = 9  # default from F_LOG
        self.log_box.bind("<Control-MouseWheel>", self._on_log_zoom)
        self.log_box.bind("<Control-Button-4>", self._on_log_zoom)
        self.log_box.bind("<Control-Button-5>", self._on_log_zoom)

        btn_bar = tk.Frame(f, bg=BG, pady=6)
        btn_bar.grid(row=1, column=0, sticky="ew", padx=12)

        tk.Button(
            btn_bar,
            text="Clear Logs",
            fg=MUTED,
            bg=SURFACE,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=F_SMALL,
            padx=10,
            pady=4,
            command=self._clear_logs,
        ).pack(side="left")

        self.autoscroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            btn_bar,
            text="Auto-scroll",
            variable=self.autoscroll_var,
            fg=MUTED,
            bg=BG,
            activebackground=BG,
            selectcolor=SURFACE,
            font=F_SMALL,
        ).pack(side="left", padx=12)

        # Zoom controls for log text
        tk.Frame(btn_bar, bg=SURFACE, width=1).pack(side="left", fill="y", padx=10)
        tk.Button(
            btn_bar,
            text="-",
            fg=MUTED,
            bg=SURFACE,
            activeforeground=TEXT,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            padx=8,
            pady=2,
            command=lambda: self._resize_log(-2),
        ).pack(side="left", padx=(10, 2))
        self._log_size_lbl = tk.Label(
            btn_bar, text="9pt", fg=MUTED, bg=SURFACE, font=("DejaVu Sans", 9), width=4
        )
        self._log_size_lbl.pack(side="left", padx=(0, 2))
        tk.Button(
            btn_bar,
            text="+",
            fg=ACCENT,
            bg=SURFACE,
            activeforeground=TEXT,
            activebackground=BORDER,
            relief="flat",
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            padx=8,
            pady=2,
            command=lambda: self._resize_log(+2),
        ).pack(side="left", padx=2)

    # ── Toggle & labels ───────────────────────────────────────────────────────

    def _update_toggle_btn(self):
        enabled = self.toggle_var.get()
        self.toggle_btn.configure(
            text="ON" if enabled else "OFF",
            bg=SUCCESS if enabled else SURFACE,
            fg="#000" if enabled else MUTED,
            activebackground=SUCCESS if enabled else BORDER,
        )
        if hasattr(self, "monitor_dot"):
            self.monitor_dot.configure(fg=SUCCESS if enabled else MUTED)
        if hasattr(self, "monitor_status_lbl"):
            self.monitor_status_lbl.configure(
                text=(
                    "Watching clipboard — copy any code to explain it automatically"
                    if enabled
                    else "Monitoring paused — click ON to resume"
                ),
                fg=TEXT if enabled else MUTED,
            )
        self.status_var.set("Monitoring active" if enabled else "Monitoring paused")

    def _update_provider_badge(self):
        p = self.config_obj.provider
        m = self.config_obj.current_model
        color = PROVIDER_COLORS.get(p, ACCENT)
        self.provider_badge.configure(
            text=f"  {p.upper()}  ·  {m}  ",
            fg=color,
        )

    # ── Monitor logic ─────────────────────────────────────────────────────────

    def _toggle(self):
        new_val = not self.toggle_var.get()
        self.toggle_var.set(new_val)
        self.config_obj.enabled = new_val
        if hasattr(self, "_monitor"):
            self._monitor.set_enabled(new_val)
        self._update_toggle_btn()

    def _start_monitor(self):
        self._monitor = ClipboardMonitor(
            callback=self._on_code_detected,
            log_callback=self._on_log,
            min_code_length=self.config_obj.data.get("min_code_length", 20),
        )
        self._monitor.set_enabled(self.config_obj.enabled)
        self._monitor.start()

    def _on_log(self, level: str, msg: str):
        """Called from background thread — queue it for the UI thread."""
        self._log_queue.put((level, msg))

    def _poll_logs(self):
        try:
            while True:
                level, msg = self._log_queue.get_nowait()
                self._append_log(level, msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_logs)

    def _append_log(self, level: str, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:11]
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] ", "TIME")
        self.log_box.insert("end", f"{level:<5} ", level)
        self.log_box.insert("end", f"{msg}\n", "MSG")
        if self.autoscroll_var.get():
            self.log_box.see("end")
        self.log_box.configure(state="disabled")

        # Mirror important messages to status bar
        if level in ("WARN", "ERROR"):
            self.status_var.set(f"{level}: {msg[:80]}")

        # Update clip label on Monitor tab
        if "Clipboard changed" in msg or "clipboard" in msg.lower():
            short = msg[:90]
            if hasattr(self, "clip_lbl"):
                self.clip_lbl.configure(text=f"Clipboard: {short}")

    def _clear_logs(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _resize_log(self, delta: int):
        """Resize font in Logs tab."""
        new_size = max(8, min(30, self._log_font_size + delta))
        self._log_font_size = new_size
        self.log_box.configure(font=("Consolas", new_size))
        self._log_size_lbl.configure(text=f"{new_size}pt")

    def _on_log_zoom(self, event):
        """Handle Ctrl+MouseWheel to zoom log text."""
        if hasattr(event, "num"):  # Linux X11
            delta = +2 if event.num == 4 else -2
        else:  # Windows / WSL
            delta = +2 if event.delta > 0 else -2
        new_size = max(8, min(30, self._log_font_size + delta))
        self._log_font_size = new_size
        self.log_box.configure(font=("Consolas", new_size))
        self._log_size_lbl.configure(text=f"{new_size}pt")
        return "break"

    def _on_code_detected(self, code: str):
        if self._processing:
            self._on_log(
                "DEBUG", "Popup suppressed — already processing another snippet"
            )
            return
        self.after(0, lambda: self._show_explanation(code))

    def _show_explanation(self, code: str):
        if self._processing:
            return
        self._processing = True
        self.proc_lbl.configure(text="⏳ Explaining…")
        self._on_log("INFO", f"Opening explanation popup ({len(code)} chars)")

        preview = code.strip().splitlines()[0][:70]
        self._history.insert(0, (preview, code))
        self._history = self._history[:20]
        self._refresh_history()

        if self._active_popup and self._active_popup.winfo_exists():
            self._active_popup.destroy()

        try:
            provider = build_provider(self.config_obj)
        except Exception as e:
            self._on_log("ERROR", f"Provider build failed: {e}")
            self.proc_lbl.configure(text=f"Provider error: {e}")
            self._processing = False
            return

        def make_stream_fn(prompt_text: str):
            def _gen():
                yield from provider.explain(code, prompt_text)

            return _gen()

        popup = ExplanationPopup(
            self,
            code=code,
            provider_name=self.config_obj.provider,
            model=self.config_obj.current_model,
            make_stream_fn=make_stream_fn,
            prompts=self.config_obj.prompts,
            active_prompt=self.config_obj.active_prompt,
            config=self.config_obj,
        )
        popup.protocol("WM_DELETE_WINDOW", lambda: self._on_popup_close(popup))
        self._active_popup = popup
        self._processing = False
        self.proc_lbl.configure(text="")

    def _on_popup_close(self, popup):
        popup.destroy()
        self._processing = False
        self.proc_lbl.configure(text="")

    # ── History ───────────────────────────────────────────────────────────────

    def _refresh_history(self):
        self.hist_list.delete(0, "end")
        for preview, _ in self._history:
            self.hist_list.insert("end", f"  {preview}")

    def _reopen_from_history(self, event):
        sel = self.hist_list.curselection()
        if not sel:
            return
        _, code = self._history[sel[0]]
        self._show_explanation(code)

    def _clear_history(self):
        self._history.clear()
        self._refresh_history()

    # ── Test LLM tab logic ────────────────────────────────────────────────────

    def _test_explain(self):
        code = self.test_input.get("1.0", "end-1c").strip()
        if not code:
            self.test_status_lbl.configure(text="Paste some code first", fg=WARN)
            return

        self.explain_btn.configure(state="disabled", text="⏳ Generating…")
        self.test_status_lbl.configure(text="Calling model…", fg=MUTED)
        self.test_output.configure(state="normal")
        self.test_output.delete("1.0", "end")
        self.test_output.configure(state="disabled")
        self._on_log("INFO", f"Test explain triggered ({len(code)} chars)")

        # Reset font size on new explain
        self._resize_test_output(0)

        prompt_name = self.test_prompt_var.get()
        prompt_text = self.config_obj.get_prompt_text(prompt_name)
        self._on_log("INFO", f"Test prompt: '{prompt_name}'")

        def run():
            try:
                provider = build_provider(self.config_obj)
                self._on_log(
                    "INFO",
                    f"Using {self.config_obj.provider} / {self.config_obj.current_model}",
                )
                for chunk in provider.explain(code, prompt_text):
                    self._test_queue.put(("chunk", chunk))
                self._test_queue.put(("done", None))
            except Exception as e:
                self._on_log("ERROR", f"Test explain error: {e}")
                self._test_queue.put(("error", str(e)))

        threading.Thread(target=run, daemon=True).start()
        self._poll_test_queue()

    def _poll_test_queue(self):
        done = False
        try:
            while True:
                kind, data = self._test_queue.get_nowait()
                if kind == "chunk":
                    self.test_output.configure(state="normal")
                    self.test_output.insert("end", data)
                    self.test_output.see("end")
                    self.test_output.configure(state="disabled")
                elif kind == "done":
                    self.test_status_lbl.configure(text="Done ✓", fg=SUCCESS)
                    self.test_output.configure(state="normal")
                    self.test_output.insert(
                        "end", "\n\n─── Complete ───", "done_marker"
                    )
                    self.test_output.see("end")
                    self.test_output.configure(state="disabled")
                    self.explain_btn.configure(state="normal", text="▶  Explain Code")
                    self._on_log("INFO", "Test explain completed")
                    done = True
                elif kind == "error":
                    self.test_status_lbl.configure(text=f"Error: {data[:50]}", fg=ERROR)
                    self.test_output.configure(state="normal")
                    self.test_output.insert("end", f"\n\n[Error: {data}]", "error")
                    self.test_output.configure(state="disabled")
                    self.explain_btn.configure(state="normal", text="▶  Explain Code")
                    done = True
        except queue.Empty:
            pass

        if not done:
            self.after(50, self._poll_test_queue)

    def _clear_test(self):
        self.test_input.delete("1.0", "end")
        self.test_output.configure(state="normal")
        self.test_output.delete("1.0", "end")
        self.test_output.configure(state="disabled")
        self.test_status_lbl.configure(text="")

    def _resize_test_output(self, delta: int):
        """Resize font in Test LLM tab explanation output."""
        new_size = max(9, min(40, self._test_output_font_size + delta))
        self._test_output_font_size = new_size
        self.test_output.configure(font=("Segoe UI", new_size))
        self._test_output_size_lbl.configure(text=f"{new_size}pt")

    def _on_test_output_zoom(self, event):
        """Handle Ctrl+MouseWheel to zoom explanation text in Test LLM tab."""
        if hasattr(event, "num"):  # Linux X11
            delta = +2 if event.num == 4 else -2
        else:  # Windows / WSL
            delta = +2 if event.delta > 0 else -2
        new_size = max(9, min(40, self._test_output_font_size + delta))
        self._test_output_font_size = new_size
        self.test_output.configure(font=("Segoe UI", new_size))
        return "break"

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        def on_save():
            self._monitor.set_enabled(self.config_obj.enabled)
            self._monitor.set_min_length(
                self.config_obj.data.get("min_code_length", 20)
            )
            self.toggle_var.set(self.config_obj.enabled)
            self._update_toggle_btn()
            self._update_provider_badge()
            # Refresh prompt combo with updated list
            names = self.config_obj.prompt_names
            self.test_prompt_combo.configure(values=names)
            if self.test_prompt_var.get() not in names:
                self.test_prompt_var.set(self.config_obj.active_prompt)
            self._on_log(
                "INFO",
                f"Settings saved — provider={self.config_obj.provider} model={self.config_obj.current_model}",
            )

        SettingsDialog(self, self.config_obj, on_save=on_save)

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _try_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            img = Image.new("RGBA", (64, 64), "#1e1e2e")
            d = ImageDraw.Draw(img)
            d.rectangle([8, 8, 56, 56], fill="#89b4fa", outline="#cdd6f4", width=2)

            menu = pystray.Menu(
                pystray.MenuItem(
                    "Show", lambda i, item: self.after(0, self.deiconify), default=True
                ),
                pystray.MenuItem(
                    "Toggle ON/OFF", lambda i, item: self.after(0, self._toggle)
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Quit", lambda i, item: (i.stop(), self.after(0, self.quit))
                ),
            )
            self._tray_icon = pystray.Icon(
                "code-explainer", img, "Code Explainer", menu
            )
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except Exception as e:
            pass  # Tray not critical

    def _on_close(self):
        self.withdraw()

    def run(self):
        self.mainloop()
        if hasattr(self, "_monitor"):
            self._monitor.stop()

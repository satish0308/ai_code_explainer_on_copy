"""
Explanation popup window.
- Streams AI response with live text
- Prompt selector bar: switch prompt and Re-explain without closing
- A− / A+ buttons (and Ctrl+scroll) resize the explanation text live
- Audio output for explanation content
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
from typing import Callable, Generator


DARK_BG      = "#1e1e2e"
DARK_PANEL   = "#181825"
DARK_TEXT    = "#cdd6f4"
DARK_MUTED   = "#6c7086"
DARK_ACCENT  = "#89b4fa"
DARK_CODE_BG = "#11111b"
DARK_SURFACE = "#313244"
DARK_SUCCESS = "#a6e3a1"
DARK_ERROR   = "#f38ba8"

FONT_MONO   = ("Consolas",  12)
FONT_SMALL  = ("Segoe UI",  11)
FONT_HEADER = ("Segoe UI",  14, "bold")

DEFAULT_SIZE = 28   # explanation body default pt
MIN_SIZE     = 8
MAX_SIZE     = 60


class ExplanationPopup(tk.Toplevel):
    def __init__(
        self,
        parent,
        code: str,
        provider_name: str,
        model: str,
        make_stream_fn: Callable[[str], Generator[str, None, None]],
        prompts: list[dict],
        active_prompt: str,
        config=None,
    ):
        super().__init__(parent)
        self.code           = code
        self.provider_name  = provider_name
        self.model          = model
        self.make_stream_fn = make_stream_fn
        self.prompts        = prompts
        self._queue         = queue.Queue()
        self._streaming     = False
        self._font_size     = DEFAULT_SIZE   # tracks current body font size
        self.config         = config  # for audio settings

        self._setup_window()
        self._build_ui(active_prompt)
        self._start_stream()
        self._poll_queue()

    def _speak_explanation(self, text: str):
        """Speak the explanation text using system TTS."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Adjust rate - slightly slower for better clarity
            engine.setProperty('rate', 150)
            # Speak the text
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            self.status_var.set("Install pyttsx3 for audio: pip install pyttsx3")
            self.status_lbl.configure(fg=DARK_ERROR)
            self.after(2500, lambda: self.status_var.set("Done  ✓" if not self._streaming else "Generating…"))
        except Exception as e:
            self.status_var.set(f"Audio error: {e}")
            self.status_lbl.configure(fg=DARK_ERROR)
            self.after(2500, lambda: self.status_var.set("Done  ✓" if not self._streaming else "Generating…"))

    # ── Window ────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Code Explainer")
        self.configure(bg=DARK_BG)
        self.attributes("-topmost", True)
        w, h = 880, 720
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(560, 420)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self, active_prompt: str):
        # Row 0 – header
        hdr = tk.Frame(self, bg=DARK_PANEL, padx=14, pady=10)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        tk.Label(hdr, text="⬤", fg=DARK_ACCENT, bg=DARK_PANEL,
                 font=("", 9)).grid(row=0, column=0, padx=(0, 8))
        tk.Label(hdr, text="Code Explanation", fg=DARK_TEXT,
                 bg=DARK_PANEL, font=FONT_HEADER).grid(row=0, column=1, sticky="w")
        tk.Label(hdr, text=f"{self.provider_name.upper()}  ·  {self.model}",
                 fg=DARK_MUTED, bg=DARK_PANEL,
                 font=FONT_SMALL).grid(row=1, column=1, sticky="w")
        tk.Button(hdr, text="✕", fg=DARK_MUTED, bg=DARK_PANEL,
                  activeforeground=DARK_ERROR, activebackground=DARK_PANEL,
                  relief="flat", cursor="hand2", font=("", 13),
                  command=self._close).grid(row=0, column=2, rowspan=2, padx=6)

        # Row 1 – prompt bar
        pbar = tk.Frame(self, bg=DARK_SURFACE, padx=12, pady=8)
        pbar.grid(row=1, column=0, sticky="ew")
        pbar.columnconfigure(1, weight=1)

        tk.Label(pbar, text="Prompt:", fg=DARK_MUTED, bg=DARK_SURFACE,
                 font=FONT_SMALL).grid(row=0, column=0, padx=(0, 8))

        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("P.TCombobox", fieldbackground=DARK_BG, background=DARK_SURFACE,
                    foreground=DARK_TEXT, selectbackground=DARK_ACCENT,
                    selectforeground="#000", arrowcolor=DARK_ACCENT)

        self.prompt_var = tk.StringVar(value=active_prompt)
        ttk.Combobox(pbar, textvariable=self.prompt_var,
                     values=[p["name"] for p in self.prompts],
                     state="readonly", font=FONT_SMALL,
                     style="P.TCombobox").grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.reexplain_btn = tk.Button(
            pbar, text="↺  Re-explain", bg=DARK_ACCENT, fg="#000",
            activebackground="#74c7ec", relief="flat", cursor="hand2",
            font=("Segoe UI", 11, "bold"), padx=14, pady=4,
            command=self._reexplain,
        )
        self.reexplain_btn.grid(row=0, column=2, padx=(0, 4))

        # Row 2 – paned: code top, explanation bottom
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg=DARK_SURFACE,
                               sashwidth=5, sashrelief="flat")
        paned.grid(row=2, column=0, sticky="nsew")

        # Code panel
        cf = tk.Frame(paned, bg=DARK_CODE_BG)
        tk.Label(cf, text="Copied Code", fg=DARK_MUTED, bg=DARK_CODE_BG,
                 font=FONT_SMALL, anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.code_box = scrolledtext.ScrolledText(
            cf, height=6, bg=DARK_CODE_BG, fg="#a6e3a1",
            font=FONT_MONO, relief="flat", state="disabled",
            insertbackground=DARK_TEXT, selectbackground=DARK_ACCENT, wrap="none",
        )
        self.code_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._insert_code()
        paned.add(cf, minsize=90)

        # Explanation panel
        ef = tk.Frame(paned, bg=DARK_BG)
        tk.Label(ef, text="Explanation", fg=DARK_MUTED, bg=DARK_BG,
                 font=FONT_SMALL, anchor="w").pack(fill="x", padx=12, pady=(8, 2))

        self.exp_box = scrolledtext.ScrolledText(
            ef, bg=DARK_BG, fg=DARK_TEXT,
            font=("Segoe UI", self._font_size),   # initial font
            relief="flat", state="disabled",
            insertbackground=DARK_TEXT, selectbackground=DARK_ACCENT,
            wrap="word", spacing1=4, spacing3=4,
        )
        self.exp_box.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Define all tags — "body" is applied to EVERY inserted chunk
        self.exp_box.tag_configure("body",
            font=("Segoe UI", self._font_size),
            foreground=DARK_TEXT)
        self.exp_box.tag_configure("header",
            font=("Segoe UI", self._font_size + 3, "bold"),
            foreground=DARK_ACCENT, spacing1=10, spacing3=4)
        self.exp_box.tag_configure("code_inline",
            font=("Consolas", max(MIN_SIZE, self._font_size - 1)),
            background=DARK_CODE_BG, foreground="#a6e3a1")
        self.exp_box.tag_configure("error",
            foreground=DARK_ERROR)

        # Ctrl+scroll resizes font - bind to both exp_box and popup window
        # This is needed for WSL compatibility where event delivery may vary
        self.exp_box.bind("<Control-MouseWheel>", self._on_ctrl_scroll)
        self.exp_box.bind("<Control-Button-4>", self._on_ctrl_scroll)
        self.exp_box.bind("<Control-Button-5>", self._on_ctrl_scroll)
        self.bind("<Control-MouseWheel>", self._on_ctrl_scroll)
        self.bind("<Control-Button-4>", self._on_ctrl_scroll)
        self.bind("<Control-Button-5>", self._on_ctrl_scroll)

        paned.add(ef, minsize=140)

        # Row 3 – status bar
        sbar = tk.Frame(self, bg=DARK_PANEL, height=34)
        sbar.grid(row=3, column=0, sticky="ew")
        sbar.grid_propagate(False)

        self.status_var = tk.StringVar(value="Generating explanation…")
        self.status_lbl = tk.Label(sbar, textvariable=self.status_var,
                                   fg=DARK_MUTED, bg=DARK_PANEL, font=FONT_SMALL, anchor="w")
        self.status_lbl.pack(side="left", padx=12, pady=4)

        # Close / Copy buttons (right side)
        for txt, cmd in [("Close", self._close), ("Copy", self._copy_explanation)]:
            tk.Button(sbar, text=txt, fg=DARK_MUTED, bg=DARK_PANEL,
                      activeforeground=DARK_TEXT, activebackground=DARK_SURFACE,
                      relief="flat", cursor="hand2", font=FONT_SMALL,
                      padx=10, pady=3, command=cmd).pack(side="right", padx=6, pady=4)

        # Separator
        tk.Frame(sbar, bg=DARK_SURFACE, width=1).pack(side="right", fill="y", pady=4)

        # Audio button (speak explanation)
        self.audio_btn = tk.Button(sbar, text="🔊", fg=DARK_ACCENT, bg=DARK_PANEL,
                                   activeforeground=DARK_TEXT, activebackground=DARK_SURFACE,
                                   relief="flat", cursor="hand2",
                                   font=("Segoe UI", 12), padx=10, pady=3,
                                   command=self._speak_explanation_current)
        self.audio_btn.pack(side="right", padx=2, pady=4)

        # A+ button
        tk.Button(sbar, text="A+", fg=DARK_ACCENT, bg=DARK_PANEL,
                  activeforeground=DARK_TEXT, activebackground=DARK_SURFACE,
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 12, "bold"), padx=10, pady=3,
                  command=lambda: (print("A+ clicked"), self._resize_font(2))).pack(side="right", padx=2, pady=4)

        # Size label
        self.font_size_lbl = tk.Label(sbar, text=f"{self._font_size}pt",
                                      fg=DARK_MUTED, bg=DARK_PANEL,
                                      font=FONT_SMALL, width=5)
        self.font_size_lbl.pack(side="right", pady=4)

        # A− button
        tk.Button(sbar, text="A−", fg=DARK_MUTED, bg=DARK_PANEL,
                  activeforeground=DARK_TEXT, activebackground=DARK_SURFACE,
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 12, "bold"), padx=10, pady=3,
                  command=lambda: (print("A− clicked"), self._resize_font(-2))).pack(side="right", padx=2, pady=4)

        tk.Frame(sbar, bg=DARK_SURFACE, width=1).pack(side="right", fill="y", pady=4)

        self.bind("<Escape>", lambda _: self._close())

    # ── Font resizing ─────────────────────────────────────────────────────────

    def _resize_font(self, delta: int):
        new_size = max(MIN_SIZE, min(MAX_SIZE, self._font_size + delta))
        if new_size == self._font_size:
            return
        self._font_size = new_size

        # Update tag configurations with new font size
        self.exp_box.tag_configure("body",
            font=("Segoe UI", new_size), foreground=DARK_TEXT)
        self.exp_box.tag_configure("header",
            font=("Segoe UI", new_size + 3, "bold"),
            foreground=DARK_ACCENT, spacing1=10, spacing3=4)
        self.exp_box.tag_configure("code_inline",
            font=("Consolas", max(MIN_SIZE, new_size - 1)),
            background=DARK_CODE_BG, foreground="#a6e3a1")

        # Force a complete redraw
        self.exp_box.configure(state="normal")

        # Remove all tags completely
        self.exp_box.tag_remove("body", "1.0", "end")
        self.exp_box.tag_remove("header", "1.0", "end")
        self.exp_box.tag_remove("code_inline", "1.0", "end")
        self.exp_box.tag_remove("error", "1.0", "end")

        # Get text and reinsert with body tag
        text_content = self.exp_box.get("1.0", "end-1c")
        self.exp_box.delete("1.0", "end")

        if text_content:
            self.exp_box.insert("1.0", text_content, "body")

        # Update label before forcing redraw
        self.font_size_lbl.configure(text=f"{new_size}pt")

        # Force all pending updates to process
        self.exp_box.update_idletasks()
        self.update_idletasks()

        self.exp_box.configure(state="disabled")
        print(f"Font resized to {new_size}pt (delta: {delta})")  # Debug

    def _on_ctrl_scroll(self, event):
        # Debug: print event details
        print(f"Event: {event}, widget: {event.widget}, num: {getattr(event, 'num', 'N/A')}, delta: {getattr(event, 'delta', 'N/A')}")

        # Detect scroll direction based on event source
        if hasattr(event, "num"):          # Linux X11
            # Button-4 = scroll up, Button-5 = scroll down
            delta = +2 if event.num == 4 else -2
            print(f"Linux scroll: num={event.num}, delta={delta}")
        elif hasattr(event, "delta"):      # Windows / WSL
            # Positive delta = scroll up, negative = scroll down
            delta = +2 if event.delta > 0 else -2
            print(f"Windows/WSL scroll: delta={event.delta}, result={delta}")
        else:
            print("No delta/num attribute found")
            return "break"

        self._resize_font(delta)
        print(f"Font size now: {self._font_size}pt")
        return "break"

    # ── Streaming ─────────────────────────────────────────────────────────────

    def _current_prompt_text(self) -> str:
        name = self.prompt_var.get()
        for p in self.prompts:
            if p["name"] == name:
                return p["text"]
        return self.prompts[0]["text"] if self.prompts else ""

    def _start_stream(self):
        self._streaming = True
        self.reexplain_btn.configure(state="disabled")
        gen = self.make_stream_fn(self._current_prompt_text())
        threading.Thread(target=self._stream_worker, args=(gen,), daemon=True).start()

    def _stream_worker(self, gen):
        try:
            for chunk in gen:
                self._queue.put(("chunk", chunk))
            self._queue.put(("done", None))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self._queue.get_nowait()
                if kind == "chunk":
                    self._append_text(data)
                elif kind == "done":
                    self._streaming = False
                    self.status_var.set("Done  ✓")
                    self.status_lbl.configure(fg=DARK_SUCCESS)
                    self.reexplain_btn.configure(state="normal")
                    # Speak if audio enabled
                    if self.config and self.config.data.get("enable_audio", False):
                        threading.Thread(target=self._speak_explanation_current, daemon=True).start()
                elif kind == "error":
                    self._streaming = False
                    self._append_text(f"\n\n[Error: {data}]", extra_tag="error")
                    self.status_var.set(f"Error: {data[:70]}")
                    self.status_lbl.configure(fg=DARK_ERROR)
                    self.reexplain_btn.configure(state="normal")
        except queue.Empty:
            pass
        if self._streaming or not self._queue.empty():
            self.after(40, self._poll_queue)

    def _reexplain(self):
        if self._streaming:
            return
        self.exp_box.configure(state="normal")
        self.exp_box.delete("1.0", "end")
        self.exp_box.configure(state="disabled")
        self.status_var.set("Generating explanation…")
        self.status_lbl.configure(fg=DARK_MUTED)
        self._start_stream()
        self._poll_queue()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _insert_code(self):
        self.code_box.configure(state="normal")
        code = self.code.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        self.code_box.insert("1.0", code)
        self.code_box.configure(state="disabled")

    def _append_text(self, text: str, extra_tag: str = None):
        """Always tag with 'body' so _resize_font can re-render via tag_configure."""
        self.exp_box.configure(state="normal")
        tags = ("body", extra_tag) if extra_tag else ("body",)
        self.exp_box.insert("end", text, tags)
        self.exp_box.see("end")
        self.exp_box.configure(state="disabled")

    def _copy_explanation(self):
        self.exp_box.configure(state="normal")
        text = self.exp_box.get("1.0", "end-1c")
        self.exp_box.configure(state="disabled")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Copied to clipboard!")
        self.after(2000, lambda: self.status_var.set(
            "Done  ✓" if not self._streaming else "Generating…"))

    def _close(self):
        self._streaming = False
        self.destroy()

    def _speak_explanation_current(self):
        """Speak the current explanation text."""
        self.exp_box.configure(state="normal")
        text = self.exp_box.get("1.0", "end-1c")
        self.exp_box.configure(state="disabled")
        if text.strip():
            # Run TTS in a separate thread to not block UI
            threading.Thread(target=self._speak_explanation, args=(text,), daemon=True).start()
        else:
            self.status_var.set("No explanation to speak")
            self.after(1500, lambda: self.status_var.set("Generating explanation…" if self._streaming else "Done  ✓"))

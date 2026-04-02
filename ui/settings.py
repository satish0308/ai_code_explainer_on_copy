"""
Settings dialog — Provider, Models, Prompts, Preferences tabs.
"""

import copy
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config import Config, DEFAULT_PROMPTS
from ai_providers import build_provider, OllamaProvider

BG          = "#1e1e2e"
PANEL       = "#181825"
TEXT        = "#cdd6f4"
MUTED       = "#6c7086"
ACCENT      = "#89b4fa"
SURFACE     = "#313244"
BORDER      = "#45475a"
SUCCESS     = "#a6e3a1"
ERROR       = "#f38ba8"
CODE_BG     = "#11111b"

F_UI    = ("Segoe UI", 11)
F_SMALL = ("Segoe UI", 10)
F_BOLD  = ("Segoe UI", 11, "bold")
F_MONO  = ("Consolas", 11)


def _entry(parent, **kw) -> tk.Entry:
    e = tk.Entry(parent, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 font=F_UI, **kw)
    return e


def _section(parent, title: str, row: int, colspan: int = 3):
    f = tk.Frame(parent, bg=BG)
    f.grid(row=row, column=0, columnspan=colspan, sticky="ew", padx=14, pady=(14, 4))
    tk.Label(f, text=title, fg=ACCENT, bg=BG, font=F_BOLD).pack(side="left")
    tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=8)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config: Config, on_save=None):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save
        # Working copy of prompts — only written to config on Save
        self._prompts: list[dict] = copy.deepcopy(config.prompts)

        self.title("Settings — Auto Code Explainer")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        w, h = 720, 640
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(600, 500)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_ui()
        self.grab_set()

    # ── Shell ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",     background=PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=[16, 8], font=F_UI)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", ACCENT)])
        style.configure("TFrame", background=BG)
        style.configure("TCombobox",
                        fieldbackground=SURFACE, background=SURFACE,
                        foreground=TEXT, selectbackground=ACCENT,
                        selectforeground="#000", arrowcolor=ACCENT)

        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew")

        self._build_provider_tab(nb)
        self._build_models_tab(nb)
        self._build_prompts_tab(nb)
        self._build_preferences_tab(nb)

        # Bottom bar
        bar = tk.Frame(self, bg=PANEL, pady=8)
        bar.grid(row=1, column=0, sticky="ew")

        tk.Button(bar, text="Save", bg=ACCENT, fg="#000",
                  activebackground="#74c7ec", relief="flat", cursor="hand2",
                  font=F_BOLD, padx=22, pady=6,
                  command=self._save).pack(side="right", padx=14)

        tk.Button(bar, text="Cancel", bg=PANEL, fg=MUTED,
                  activebackground=SURFACE, relief="flat", cursor="hand2",
                  font=F_UI, padx=14, pady=6,
                  command=self.destroy).pack(side="right", padx=4)

        self.status_lbl = tk.Label(bar, text="", fg=MUTED, bg=PANEL, font=F_SMALL)
        self.status_lbl.pack(side="left", padx=14)

    # ── Provider tab ──────────────────────────────────────────────────────────

    def _build_provider_tab(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="  Provider  ")
        f.columnconfigure(1, weight=1)

        _section(f, "Active Provider", 0)
        self.provider_var = tk.StringVar(value=self.config.provider)
        for i, (val, label, desc) in enumerate([
            ("ollama", "Ollama (Local)", "No API key — runs on your machine"),
            ("openai", "OpenAI",         "GPT-4o, GPT-4-turbo, o3-mini …"),
            ("nvidia", "NVIDIA NIM",     "Cloud-hosted open models via NVIDIA"),
            ("gemini", "Google Gemini",  "Gemini 2.0 Flash, 1.5 Pro …"),
        ]):
            row = tk.Frame(f, bg=BG)
            row.grid(row=i + 1, column=0, columnspan=3, sticky="ew", padx=16, pady=3)
            tk.Radiobutton(row, text=label, variable=self.provider_var, value=val,
                           bg=BG, fg=TEXT, activebackground=BG, activeforeground=ACCENT,
                           selectcolor=SURFACE, font=F_BOLD,
                           cursor="hand2").pack(side="left")
            tk.Label(row, text=f"  {desc}", fg=MUTED, bg=BG,
                     font=F_SMALL).pack(side="left")

        _section(f, "API Keys", 5)
        self.openai_key = self._key_row(f, "OpenAI API Key", 6,
                                        self.config.data["api_keys"].get("openai", ""))
        self.nvidia_key = self._key_row(f, "NVIDIA API Key", 7,
                                        self.config.data["api_keys"].get("nvidia", ""))
        self.gemini_key = self._key_row(f, "Gemini API Key", 8,
                                        self.config.data["api_keys"].get("gemini", ""))

        _section(f, "Ollama", 9)
        tk.Label(f, text="Ollama Host", fg=TEXT, bg=BG,
                 font=F_UI).grid(row=10, column=0, sticky="w", padx=16, pady=4)
        self.ollama_host = _entry(f, width=42)
        self.ollama_host.insert(0, self.config.data.get("ollama_host", "http://localhost:11434"))
        self.ollama_host.grid(row=10, column=1, sticky="ew", padx=(0, 14), pady=4)

        self.test_btn = tk.Button(f, text="Test Connection", fg=TEXT,
                                  bg=SURFACE, activebackground=BORDER,
                                  relief="flat", cursor="hand2", font=F_UI,
                                  padx=12, pady=5, command=self._test_connection)
        self.test_btn.grid(row=11, column=1, sticky="w", padx=(0, 14), pady=8)

        self.test_result = tk.Label(f, text="", fg=MUTED, bg=BG, font=F_SMALL)
        self.test_result.grid(row=12, column=0, columnspan=2, padx=16, sticky="w")

    def _key_row(self, parent, label: str, row: int, value: str) -> tk.Entry:
        tk.Label(parent, text=label, fg=TEXT, bg=BG,
                 font=F_UI).grid(row=row, column=0, sticky="w", padx=16, pady=4)
        e = _entry(parent, show="•", width=42)
        e.insert(0, value)
        e.grid(row=row, column=1, sticky="ew", padx=(0, 14), pady=4)
        return e

    # ── Models tab ────────────────────────────────────────────────────────────

    def _build_models_tab(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="  Models  ")
        f.columnconfigure(1, weight=1)
        self.model_vars = {}
        self.model_combos = {}

        for i, (provider, label, defaults) in enumerate([
            ("openai", "OpenAI Model",
             ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini", "o3-mini"]),
            ("nvidia", "NVIDIA Model", [
                "meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct",
                "meta/llama-3.3-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct",
                "mistralai/mixtral-8x22b-instruct-v0.1", "deepseek-ai/deepseek-r1",
            ]),
            ("gemini", "Gemini Model", [
                "gemini-2.0-flash", "gemini-2.0-flash-lite",
                "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-pro-exp-03-25",
            ]),
            ("ollama", "Ollama Model", []),
        ]):
            _section(f, label, i * 3)
            var = tk.StringVar(value=self.config.data["models"].get(provider, ""))
            self.model_vars[provider] = var
            combo = ttk.Combobox(f, textvariable=var, values=defaults, width=42, font=F_UI)
            combo.grid(row=i * 3 + 1, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
            self.model_combos[provider] = combo

            if provider == "ollama":
                tk.Button(f, text="Refresh from Ollama", fg=TEXT, bg=SURFACE,
                          activebackground=BORDER, relief="flat", cursor="hand2",
                          font=F_SMALL, padx=10, pady=4,
                          command=self._refresh_ollama_models
                          ).grid(row=i * 3 + 2, column=0, sticky="w", padx=16, pady=2)

    # ── Prompts tab ───────────────────────────────────────────────────────────

    def _build_prompts_tab(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="  Prompts  ")
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)

        # ---- Left: list of prompts ----
        left = tk.Frame(f, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 6), pady=14)
        left.rowconfigure(1, weight=1)

        tk.Label(left, text="Saved Prompts", fg=ACCENT, bg=BG,
                 font=F_BOLD).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        list_frame = tk.Frame(left, bg=SURFACE)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        sb = tk.Scrollbar(list_frame, bg=SURFACE, troughcolor=BG)
        sb.grid(row=0, column=1, sticky="ns")

        self.prompt_list = tk.Listbox(
            list_frame, bg=SURFACE, fg=TEXT,
            selectbackground=ACCENT, selectforeground="#000",
            relief="flat", font=F_UI, activestyle="none",
            cursor="hand2", width=22,
            yscrollcommand=sb.set,
            highlightthickness=0, borderwidth=0,
        )
        self.prompt_list.grid(row=0, column=0, sticky="nsew")
        sb.config(command=self.prompt_list.yview)
        self.prompt_list.bind("<<ListboxSelect>>", self._on_prompt_select)

        # Buttons below list
        btn_row = tk.Frame(left, bg=BG)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        tk.Button(btn_row, text="+ New", fg=TEXT, bg=SURFACE,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  font=F_SMALL, padx=8, pady=4,
                  command=self._new_prompt).pack(side="left", padx=(0, 4))

        tk.Button(btn_row, text="Duplicate", fg=TEXT, bg=SURFACE,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  font=F_SMALL, padx=8, pady=4,
                  command=self._duplicate_prompt).pack(side="left", padx=4)

        self.del_btn = tk.Button(btn_row, text="Delete", fg=ERROR, bg=SURFACE,
                                 activebackground=BORDER, relief="flat", cursor="hand2",
                                 font=F_SMALL, padx=8, pady=4,
                                 command=self._delete_prompt)
        self.del_btn.pack(side="left", padx=4)

        # ---- Right: editor ----
        right = tk.Frame(f, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 14), pady=14)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        tk.Label(right, text="Prompt Name", fg=MUTED, bg=BG,
                 font=F_SMALL).grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.prompt_name_var = tk.StringVar()
        self.prompt_name_entry = _entry(right)
        self.prompt_name_entry.config(textvariable=self.prompt_name_var, width=36)
        self.prompt_name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        tk.Label(right, text="Prompt Text", fg=MUTED, bg=BG,
                 font=F_SMALL).grid(row=2, column=0, sticky="w", pady=(0, 2))

        self.prompt_body = tk.Text(
            right, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT,
            font=F_MONO, wrap="word",
        )
        self.prompt_body.grid(row=3, column=0, sticky="nsew")

        save_row = tk.Frame(right, bg=BG)
        save_row.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        tk.Button(save_row, text="Save Prompt", bg=ACCENT, fg="#000",
                  activebackground="#74c7ec", relief="flat", cursor="hand2",
                  font=F_BOLD, padx=14, pady=5,
                  command=self._save_current_prompt).pack(side="left")

        tk.Button(save_row, text="Set as Default", fg=TEXT, bg=SURFACE,
                  activebackground=BORDER, relief="flat", cursor="hand2",
                  font=F_SMALL, padx=10, pady=5,
                  command=self._set_default_prompt).pack(side="left", padx=8)

        tk.Button(save_row, text="Reset All to Built-in", fg=MUTED, bg=BG,
                  activebackground=SURFACE, relief="flat", cursor="hand2",
                  font=F_SMALL, padx=8, pady=5,
                  command=self._reset_prompts).pack(side="right")

        self.prompt_save_lbl = tk.Label(save_row, text="", fg=MUTED, bg=BG, font=F_SMALL)
        self.prompt_save_lbl.pack(side="left", padx=8)

        # Default badge shown next to active prompt
        self._default_name = self.config.active_prompt

        self._refresh_prompt_list()
        # Select the active prompt initially
        names = [p["name"] for p in self._prompts]
        if self._default_name in names:
            idx = names.index(self._default_name)
            self.prompt_list.selection_set(idx)
            self.prompt_list.see(idx)
            self._load_prompt_into_editor(idx)

    def _refresh_prompt_list(self):
        self.prompt_list.delete(0, "end")
        for p in self._prompts:
            mark = " ★" if p["name"] == self._default_name else ""
            self.prompt_list.insert("end", f"  {p['name']}{mark}")

    def _on_prompt_select(self, _event=None):
        sel = self.prompt_list.curselection()
        if sel:
            self._load_prompt_into_editor(sel[0])

    def _load_prompt_into_editor(self, idx: int):
        p = self._prompts[idx]
        self.prompt_name_var.set(p["name"])
        self.prompt_body.delete("1.0", "end")
        self.prompt_body.insert("1.0", p["text"])
        self.prompt_save_lbl.configure(text="")

    def _save_current_prompt(self):
        sel = self.prompt_list.curselection()
        if not sel:
            self.prompt_save_lbl.configure(text="Select a prompt first", fg=ERROR)
            return
        idx = sel[0]
        name = self.prompt_name_var.get().strip()
        body = self.prompt_body.get("1.0", "end-1c").strip()
        if not name:
            self.prompt_save_lbl.configure(text="Name cannot be empty", fg=ERROR)
            return
        if not body:
            self.prompt_save_lbl.configure(text="Prompt text cannot be empty", fg=ERROR)
            return
        # If name changed and now matches another prompt, warn
        old_name = self._prompts[idx]["name"]
        if name != old_name:
            names = [p["name"] for p in self._prompts]
            if name in names:
                self.prompt_save_lbl.configure(text="Name already exists", fg=ERROR)
                return
            if self._default_name == old_name:
                self._default_name = name
        self._prompts[idx] = {"name": name, "text": body}
        self._refresh_prompt_list()
        self.prompt_list.selection_set(idx)
        self.prompt_save_lbl.configure(text="Saved ✓", fg=SUCCESS)
        self.after(2000, lambda: self.prompt_save_lbl.configure(text=""))

    def _set_default_prompt(self):
        sel = self.prompt_list.curselection()
        if not sel:
            return
        # Save current edits first so name is up to date
        self._save_current_prompt()
        idx = sel[0]
        self._default_name = self._prompts[idx]["name"]
        self._refresh_prompt_list()
        self.prompt_list.selection_set(idx)
        self.prompt_save_lbl.configure(text=f"Default set to '{self._default_name}'", fg=SUCCESS)
        self.after(2000, lambda: self.prompt_save_lbl.configure(text=""))

    def _new_prompt(self):
        base = "New Prompt"
        names = {p["name"] for p in self._prompts}
        name, n = base, 1
        while name in names:
            n += 1
            name = f"{base} {n}"
        self._prompts.append({"name": name, "text": "Enter your prompt here…"})
        self._refresh_prompt_list()
        idx = len(self._prompts) - 1
        self.prompt_list.selection_clear(0, "end")
        self.prompt_list.selection_set(idx)
        self.prompt_list.see(idx)
        self._load_prompt_into_editor(idx)

    def _duplicate_prompt(self):
        sel = self.prompt_list.curselection()
        if not sel:
            return
        src = self._prompts[sel[0]]
        base = f"{src['name']} (copy)"
        names = {p["name"] for p in self._prompts}
        name, n = base, 1
        while name in names:
            n += 1
            name = f"{base} {n}"
        self._prompts.append({"name": name, "text": src["text"]})
        self._refresh_prompt_list()
        idx = len(self._prompts) - 1
        self.prompt_list.selection_clear(0, "end")
        self.prompt_list.selection_set(idx)
        self.prompt_list.see(idx)
        self._load_prompt_into_editor(idx)

    def _delete_prompt(self):
        sel = self.prompt_list.curselection()
        if not sel:
            return
        if len(self._prompts) <= 1:
            messagebox.showwarning("Cannot Delete", "You must keep at least one prompt.", parent=self)
            return
        idx = sel[0]
        name = self._prompts[idx]["name"]
        if not messagebox.askyesno("Delete Prompt", f"Delete '{name}'?", parent=self):
            return
        self._prompts.pop(idx)
        if self._default_name == name:
            self._default_name = self._prompts[0]["name"]
        self._refresh_prompt_list()
        new_idx = min(idx, len(self._prompts) - 1)
        self.prompt_list.selection_set(new_idx)
        self._load_prompt_into_editor(new_idx)

    def _reset_prompts(self):
        if not messagebox.askyesno(
            "Reset Prompts",
            "Replace all prompts with the built-in defaults? Your custom prompts will be lost.",
            parent=self,
        ):
            return
        self._prompts = copy.deepcopy(DEFAULT_PROMPTS)
        self._default_name = self._prompts[0]["name"]
        self._refresh_prompt_list()
        self.prompt_list.selection_set(0)
        self._load_prompt_into_editor(0)

    # ── Preferences tab ───────────────────────────────────────────────────────

    def _build_preferences_tab(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="  Preferences  ")
        f.columnconfigure(1, weight=1)

        _section(f, "Code Detection", 0)
        tk.Label(f, text="Min Code Length (chars)", fg=TEXT, bg=BG,
                 font=F_UI).grid(row=1, column=0, sticky="w", padx=16, pady=6)
        self.min_len = _entry(f, width=10)
        self.min_len.insert(0, str(self.config.data.get("min_code_length", 20)))
        self.min_len.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=6)

        tk.Label(f, text="Lower = triggers on shorter snippets  (recommended: 20–50)",
                 fg=MUTED, bg=BG, font=F_SMALL).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=16)

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _test_connection(self):
        self.test_result.configure(text="Testing…", fg=MUTED)
        self.test_btn.configure(state="disabled")

        def run():
            self._apply_to_config()
            try:
                provider = build_provider(self.config)
                ok, msg = provider.validate()
                color = SUCCESS if ok else ERROR
                text = "Connection OK ✓" if ok else f"Failed: {msg}"
                self.after(0, lambda: self.test_result.configure(text=text, fg=color))
            except Exception as e:
                self.after(0, lambda: self.test_result.configure(
                    text=f"Error: {e}", fg=ERROR))
            finally:
                self.after(0, lambda: self.test_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def _refresh_ollama_models(self):
        host = self.ollama_host.get().strip()
        models = OllamaProvider(host=host, model="").list_models()
        if models:
            self.model_combos["ollama"].configure(values=models)
            if not self.model_vars["ollama"].get():
                self.model_vars["ollama"].set(models[0])
        else:
            messagebox.showwarning("Ollama", "No models found. Is Ollama running?", parent=self)

    def _apply_to_config(self):
        self.config.data["provider"] = self.provider_var.get()
        self.config.data["api_keys"]["openai"] = self.openai_key.get().strip()
        self.config.data["api_keys"]["nvidia"] = self.nvidia_key.get().strip()
        self.config.data["api_keys"]["gemini"] = self.gemini_key.get().strip()
        self.config.data["ollama_host"]        = self.ollama_host.get().strip()
        for p, var in self.model_vars.items():
            self.config.data["models"][p] = var.get().strip()
        try:
            self.config.data["min_code_length"] = int(self.min_len.get().strip())
        except ValueError:
            pass
        # Prompts
        self.config.data["prompts"]       = self._prompts
        self.config.data["active_prompt"] = self._default_name

    def _save(self):
        self._apply_to_config()
        self.config.save()
        self.status_lbl.configure(text="Saved ✓", fg=SUCCESS)
        self.after(1500, self.destroy)
        if self.on_save:
            self.on_save()

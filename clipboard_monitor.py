"""
Background thread that polls the clipboard every 500ms.
When new content is detected that looks like code, fires the callback.
Emits structured log events via log_callback.
"""

import re
import subprocess
import sys
import threading
from typing import Callable, Optional

# ── Clipboard readers ────────────────────────────────────────────────────────


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


_WSL = _is_wsl()


def _try_cmd(cmd: list, timeout: float = 2.0) -> Optional[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        pass
    return None


def _get_clipboard_wsl() -> Optional[str]:
    """Read Windows clipboard via PowerShell — works for apps like VS Code on WSL2."""
    val = _try_cmd(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-command",
            "Get-Clipboard",
        ],
        timeout=3.0,
    )
    if val is not None:
        # PowerShell adds \r\n line endings — normalize
        return val.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return None


def _get_clipboard() -> tuple[str, str]:
    """Returns (content, source_name). source_name is used for logging."""
    # WSL2: Windows clipboard via PowerShell must come FIRST because VS Code,
    # browsers, and all Windows apps write to the Windows clipboard, not X11.
    if _WSL:
        val = _get_clipboard_wsl()
        if val:
            return val, "powershell(WSL)"

    # 1. Try pyperclip (handles Linux/Windows/Mac via backends)
    try:
        import pyperclip

        val = pyperclip.paste()
        if val:
            return val, "pyperclip"
    except Exception:
        pass

    # 2. Linux X11/Wayland fallbacks
    if sys.platform.startswith("linux"):
        for cmd, name in [
            (["xclip", "-selection", "clipboard", "-o"], "xclip"),
            (["xsel", "--clipboard", "--output"], "xsel"),
            (["wl-paste", "--no-newline"], "wl-paste"),
        ]:
            val = _try_cmd(cmd)
            if val is not None:
                return val, name

    return "", "none"


# ── Code detection heuristics ────────────────────────────────────────────────

_CODE_PATTERNS = [
    r"\b(def|function|class|import|from|require|include|export|module)\b",
    r"\b(var|let|const|return|async|await|yield)\b",
    r"\b(public|private|protected|static|void|int|str|bool|float)\b",
    r"\b(if|else|for|while|switch|case|try|catch|finally|except|raise)\b",
    r"[{}\[\]];",
    r"=>|->|::|===|!==|\+=|-=|\*=",
    r"^\s{2,}\S",
    r"#include|#define|#ifndef|#pragma",
    r"print\s*\(|console\.(log|error)|System\.out\.",
    r"@\w+\s*[\n(]",
    r"<[a-zA-Z][^>]*>.*</[a-zA-Z]",
    r"\$\w+\s*=",
    r"(?i)\bSELECT\b.+\bFROM\b|\bINSERT\s+INTO\b|\bUPDATE\b.+\bSET\b|\bDELETE\s+FROM\b",
]

_COMPILED = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in _CODE_PATTERNS]


def is_likely_code(text: str, min_length: int = 20) -> tuple[bool, str]:
    """Returns (is_code, reason_string)."""
    text = text.strip()
    if len(text) < min_length:
        return False, f"too short ({len(text)} < {min_length} chars)"

    if text.startswith("```") or text.startswith("~~~"):
        return True, "markdown code fence detected"

    matched = [_CODE_PATTERNS[i] for i, pat in enumerate(_COMPILED) if pat.search(text)]
    score = len(matched)

    lines = text.splitlines()
    indented = sum(1 for l in lines if l.startswith(("  ", "\t")))
    if indented >= 2:
        score += 1
        matched.append("indentation")

    if score >= 2:
        return True, f"score={score}, matched: {', '.join(matched[:3])}"
    return False, f"score={score} (need ≥2) — looks like plain text"


# ── Monitor ──────────────────────────────────────────────────────────────────


class ClipboardMonitor:
    def __init__(
        self,
        callback: Callable[[str], None],
        log_callback: Optional[Callable[[str, str], None]] = None,
        min_code_length: int = 20,
        poll_interval: float = 0.6,
    ):
        self.callback = callback
        self.log = log_callback or (lambda level, msg: None)
        self.min_code_length = min_code_length
        self.poll_interval = poll_interval
        self._last_content: str = ""
        self._enabled: bool = True
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="clipboard-monitor"
        )
        self._thread.start()
        self.log("INFO", "Clipboard monitor started")

    def stop(self):
        self._stop_event.set()
        self.log("INFO", "Clipboard monitor stopped")

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.log("INFO", f"Monitoring {'enabled' if enabled else 'disabled'}")

    def set_min_length(self, length: int):
        self.min_code_length = length

    def _run(self):
        content, source = _get_clipboard()
        self._last_content = content
        self.log("DEBUG", f"Clipboard backend: {source}")
        if not content and source == "none":
            self.log(
                "WARN",
                "No clipboard backend found! Install xclip: sudo apt install xclip",
            )

        while not self._stop_event.wait(self.poll_interval):
            try:
                content, source = _get_clipboard()

                if not content:
                    continue

                if content == self._last_content:
                    continue

                prev_preview = self._last_content[:40].replace("\n", "↵")
                new_preview = content[:40].replace("\n", "↵")
                self.log(
                    "DEBUG", f"Clipboard changed ({len(content)} chars) via {source}"
                )
                self.log("DEBUG", f"  Preview: {new_preview!r}")
                self._last_content = content

                if not self._enabled:
                    self.log("DEBUG", "Skipped — monitoring is disabled")
                    continue

                is_code, reason = is_likely_code(content, self.min_code_length)
                if is_code:
                    self.log("INFO", f"Code detected! {reason}")
                    self.callback(content)
                else:
                    self.log("DEBUG", f"Not code: {reason}")

            except Exception as e:
                self.log("ERROR", f"Monitor loop error: {e}")

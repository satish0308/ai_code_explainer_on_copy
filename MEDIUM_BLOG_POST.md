# Building an AI-Powered Code Explainer Desktop App with Python

> How I built a cross-platform desktop application that automatically explains code you copy — using local AI or cloud LLMs — and what I learned along the way.

*By [Satish Hiremath](https://github.com/satish0308)*

---

## Introduction

I'm guessing you've been there: you copy a code snippet from Stack Overflow, documentation, or a chat AI, only to forget what it does minutes later. Or maybe you're reviewing someone else's code and wish you had a quick explanation handy.

That's why I built **Auto Code Explainer** — a desktop application that monitors your clipboard and automatically explains code snippets using AI. It's like having a senior developer whispering explanations over your shoulder while you code.

Here's what makes this project interesting:
- It works **locally** with Ollama (no API keys needed) or with cloud providers (OpenAI, NVIDIA NIM, Google Gemini)
- It's **cross-platform** — Windows, Linux, macOS, and WSL2
- It streams AI responses **live** as they're generated
- It's built entirely in Python with Tkinter — no web framework required

In this post, I'll walk through the architecture, the technical challenges, and the lessons learned building this tool.

---

## The Core Idea

The concept is simple:
1. Monitor the clipboard for changes
2. Detect when code has been copied
3. Send it to an AI provider with a context-aware prompt
4. Stream the explanation back in real-time
5. Display it in a popup window

The magic is in the details — especially making it work seamlessly across different platforms and AI providers.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Auto Code Explainer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Clipboard │  │  AI Provider │  │  Explain     │          │
│  │  Monitor    │→ │  Integrations│→ │  Popup UI    │          │
│  └─────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                  │                  │
│         ▼                 ▼                  ▼                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ xclip/xsel  │  │ OpenAI API   │  │ Main Window  │          │
│  │ PowerShell  │  │ NVIDIA NIM   │  │ Settings     │          │
│  │ pyperclip   │  │ Google Gemini│  │ History      │          │
│  └─────────────┘  │ Ollama       │  └──────────────┘          │
│                   └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

Let me walk you through the main components:

#### 1. Clipboard Monitor (`clipboard_monitor.py`)

This is where the magic happens. The monitor runs in a background thread, polling the clipboard every 500ms:

```python
class ClipboardMonitor:
    def __init__(
        self,
        callback: Callable[[str], None],
        log_callback: Optional[Callable[[str, str], None]] = None,
        min_code_length: int = 20,
        poll_interval: float = 0.6,
    ):
        self.callback = callback  # Called when code is detected
        self.log = log_callback   # For UI logging
        self.min_code_length = min_code_length
        self.poll_interval = poll_interval
```

The cross-platform clipboard reader is particularly interesting:

```python
def _get_clipboard() -> tuple[str, str]:
    """Returns (content, source_name)."""
    # WSL2: Windows clipboard via PowerShell must come FIRST
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
```

**Key insight**: On WSL2, we must read from Windows PowerShell first because VS Code and other Windows apps write to the Windows clipboard, not the X11 clipboard. Getting this ordering right was crucial for the tool to work consistently.

#### 2. Code Detection Heuristics

Not every clipboard change is code. We need smart detection:

```python
_CODE_PATTERNS = [
    r"\b(def|function|class|import|from|export)\b",           # Python/JS keywords
    r"\b(if|else|for|while|switch|try|catch)\b",             # Control flow
    r"\b(var|let|const|return|async|await)\b",               # Variables
    r"\b(public|private|protected|static|void|int|str)\b",   # Types
    r"[{}\[\]];",                                            # Brackets
    r"=>|->|::|===|\+=|-=|\*=",                               # Operators
    r"^\s{2,}\S",                                            # Indented lines
    r"#include|#define|#ifndef|#pragma",                     # C/C++
    r"print\s*\(|console\.(log|error)|System\.out\.",        # Output
    r"<[a-zA-Z][^>]*>.*</[a-zA-Z]",                          # HTML/XML
    r"\$\w+\s*=",                                            # Variables
    r"(?i)\bSELECT\b.+\bFROM\b|\bINSERT\s+INTO\b",          # SQL
]

def is_likely_code(text: str, min_length: int = 20) -> tuple[bool, str]:
    text = text.strip()
    if len(text) < min_length:
        return False, f"too short ({len(text)} < {min_length} chars)"

    # Check for markdown code fences
    if text.startswith("```") or text.startswith("~~~"):
        return True, "markdown code fence detected"

    # Score-based detection
    matched = [_CODE_PATTERNS[i] for i, pat in enumerate(_COMPILED) if pat.search(text)]
    score = len(matched)
    
    # Bonus for indentation (real code often has structure)
    lines = text.splitlines()
    indented = sum(1 for l in lines if l.startswith(("  ", "\t")))
    if indented >= 2:
        score += 1
        matched.append("indentation")

    if score >= 2:
        return True, f"score={score}, matched: {', '.join(matched[:3])}"
    return False, f"score={score} (need ≥2) — looks like plain text"
```

This heuristic approach works well because:
- It's lightweight (no external dependencies)
- It's fast (regex is compiled once)
- It's flexible (different code styles trigger different patterns)

#### 3. AI Provider Integrations (`ai_providers.py`)

The provider architecture uses a clean interface with a factory pattern:

```python
class AIProvider(ABC):
    @abstractmethod
    def explain(self, code: str, system_prompt: str) -> Generator[str, None, None]:
        """Yield text chunks as they stream in."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return available model names."""
        ...

    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        """Return (ok, error_message)."""
        ...
```

Here's the OpenAI implementation (streaming):

```python
class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def explain(self, code: str, system_prompt: str) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Explain this code:\n\n```\n{code}\n```"},
            ],
        }
        with requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=60,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                if line == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta  # Live streaming!
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
```

**Key insight**: Using `Generator[str, None, None]` with `yield` allows us to stream responses. This is crucial for UX — users see the explanation build in real-time instead of waiting for the full response.

I implemented providers for:
- **OpenAI** (GPT-4o, GPT-4-turbo, o1, o3)
- **NVIDIA NIM** (Llama, Mistral, Gemma — cloud-hosted open models)
- **Google Gemini** (2.0 Flash, 1.5 Pro)
- **Ollama** (local models like Llama 3.2)

NVIDIA NIM is interesting — it's OpenAI-compatible, so I inherited from `OpenAIProvider` and just overrode the defaults:

```python
class NvidiaProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, api_key: str, model: str, base_url: str = DEFAULT_BASE_URL):
        super().__init__(api_key, model, base_url)
```

#### 4. Tkinter UI (`ui/app.py`, `ui/popup.py`, `ui/settings.py`)

I chose Tkinter because:
- It's built into Python (no extra installation)
- It works everywhere (Windows, Linux, macOS)
- It's lightweight and fast

The UI is dark-themed (eye-friendly for late-night coding):

```python
# Palette - dark theme
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
```

The main window is a tabbed notebook:
- **Monitor tab** — shows clipboard status and history
- **Test LLM tab** — manually test different prompts/models
- **Logs tab** — diagnostic info and clipboard activity

Here's the ExplanationPopup — it has a split view (code on top, explanation below):

```python
class ExplanationPopup(tk.Toplevel):
    def __init__(self, parent, code, provider_name, model, make_stream_fn, ...):
        # Setup window
        self.title("Code Explainer")
        self.attributes("-topmost", True)  # Always on top
        self.geometry(f"960x800+{(sw-w)//2}+{(sh-h)//2}")
        
        # PanedWindow for split view
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg=DARK_SURFACE)
        paned.grid(row=2, column=0, sticky="nsew")
        
        # Code panel (top)
        cf = tk.Frame(paned, bg=DARK_CODE_BG)
        # ... code display ...
        paned.add(cf, minsize=90)
        
        # Explanation panel (bottom)
        ef = tk.Frame(paned, bg=DARK_BG)
        # ... explanation display ...
        paned.add(ef, minsize=140)
```

The streaming explanation worker runs in a separate thread:

```python
def _start_stream(self):
    self._streaming = True
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
    # Check queue every 40ms and update UI
    # This is the Tkinter-safe way to update from background threads
```

**Key insight**: Tkinter is not thread-safe. All UI updates must happen on the main thread. I used a queue pattern — the background thread puts chunks in a queue, and the main thread polls the queue and updates the text widget.

#### 5. Configuration (`config.py`)

Configuration is stored in `~/.auto-code-explainer/config.json`:

```python
DEFAULT_CONFIG = {
    "provider": "ollama",
    "models": {
        "openai": "gpt-4o-mini",
        "nvidia": "meta/llama-3.1-70b-instruct",
        "gemini": "gemini-2.0-flash",
        "ollama": "llama3.2",
    },
    "api_keys": {"openai": "", "nvidia": "", "gemini": ""},
    "ollama_host": "http://localhost:11434",
    "enabled": True,
    "min_code_length": 20,
    "prompts": DEFAULT_PROMPTS,
    "active_prompt": "General Explainer",
    "enable_audio": False,
}
```

Built-in prompts include:
- **General Explainer** — balanced technical explanation
- **Beginner Friendly** — simple language, step-by-step
- **Senior Code Review** — bugs, performance, security issues
- **Security Audit** — OWASP Top 10 analysis
- **Business Logic** — non-technical explanation
- **Add Comments** — inline comments for your code

---

## Technical Challenges & Solutions

### Challenge 1: Cross-Platform Clipboard

**Problem**: Different platforms have different clipboard systems. Linux has X11 and Wayland (with multiple tools), Windows has its own API, macOS has Cocoa, and WSL2 adds another layer.

**Solution**: I implemented a fallback chain:
1. WSL2: PowerShell clipboard (highest priority)
2. pyperclip (cross-platform abstraction)
3. Linux-specific fallbacks (xclip, xsel, wl-paste)

This ensures the tool works whether you're on Ubuntu with Wayland, Windows with VS Code, or WSL2 with VS Code Remote.

### Challenge 2: Streaming UI Updates

**Problem**: Tkinter is single-threaded. You can't update widgets from a background thread.

**Solution**: Queue pattern with polling:
- Background thread puts chunks in a queue
- Main thread polls every 40ms and updates UI
- This keeps the UI responsive without blocking

### Challenge 3: Code Detection Accuracy

**Problem**: How do we distinguish code from plain text without false positives?

**Solution**: Score-based detection with multiple heuristics:
- Keyword matches (def, function, class, etc.)
- Code structure (brackets, indentation)
- Markdown code fences
- Language-specific patterns (SQL, HTML, etc.)

The scoring system ensures at least 2 matching patterns before triggering.

### Challenge 4: Font Resizing

**Problem**: Users want to adjust text size, but Tkinter font changes are global.

**Solution**: Tag-based rendering with dynamic re-tagging:

```python
def _resize_font(self, delta: int):
    new_size = max(MIN_SIZE, min(MAX_SIZE, self._font_size + delta))
    
    # Update tag configurations
    self.exp_box.tag_configure("body", font=("Segoe UI", new_size))
    self.exp_box.tag_configure("header", font=("Segoe UI", new_size + 3, "bold"))
    
    # Re-apply tags to existing text
    text_content = self.exp_box.get("1.0", "end-1c")
    self.exp_box.delete("1.0", "end")
    if text_content:
        self.exp_box.insert("1.0", text_content, "body")
```

This ensures all existing text is re-rendered with the new font size.

### Challenge 5: System Tray Icon

**Problem**: The app should minimize to the system tray for quick access.

**Solution**: pystray for system tray integration (optional feature):

```python
def _try_tray(self):
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        # Create icon
        img = Image.new("RGBA", (64, 64), "#1e1e2e")
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, 56, 56], fill="#89b4fa", outline="#cdd6f4", width=2)
        
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("Show", ...),
            pystray.MenuItem("Toggle ON/OFF", ...),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", ...),
        )
        
        self._tray_icon = pystray.Icon("code-explainer", img, "Code Explainer", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()
    except Exception:
        pass  # Tray not critical — app works without it
```

---

## Setting Up Your Development Environment

Here's how to set up the project locally:

```bash
# Clone the repository
git clone https://github.com/yourusername/auto-code-explainer.git
cd auto-code-explainer

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

**Prerequisites**:
- Python 3.8 or higher
- `pip` (Python package manager)

**Optional system dependencies**:
- Linux: `sudo apt install xclip xsel wl-clipboard`
- Windows: `pip install pywin32` (for system tray)
- macOS: Usually works out of the box

---

## Running Tests

The project includes unit tests using pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ui --cov=clipboard_monitor --cov=config --cov=ai_providers

# Run specific test file
pytest tests/test_ai_providers.py -v
```

Coverage is tracked via Codecov, and CI/CD validates the package on every PR.

---

## Deployment

The project uses Poetry for packaging and distribution:

```bash
# Build the package
poetry build

# The wheel will be in dist/
# Install locally
pip install dist/auto_code_explainer-0.2.0-py3-none-any.whl

# Run from installed package
auto-code-explainer
```

**Current status**: The tool is ready to use. I'm considering publishing to PyPI, but for now, it's best installed from source.

---

## Lessons Learned

### 1. Start Simple, Iterate Fast

I started with just clipboard polling and a basic popup. The AI integration came later. Each feature was added incrementally, tested, and refined.

### 2. Cross-Platform is Hard

Every platform has its quirks:
- Linux: Different clipboard tools (xclip vs xsel vs wl-paste)
- macOS: System permissions for automation
- Windows: DPI scaling, different font rendering
- WSL2: Two separate clipboard systems

**Advice**: Test early on multiple platforms. Don't assume one approach works everywhere.

### 3. Streaming is a UX Game-Changer

People much prefer seeing text appear in real-time vs waiting for a full response. The streaming implementation added only ~50 lines of code but made the app feel much more responsive.

### 4. Tkinter is Underrated

Yes, it's old. But it's:
- Built into Python (no extra download)
- Works everywhere (Windows, Linux, macOS, WSL)
- Fast and lightweight
- Perfect for simple desktop utilities

For this type of tool, Tkinter is the pragmatic choice.

### 5. Configuration Matters

Early versions had hardcoded values. The config system evolved over time to support:
- Multiple AI providers
- Custom prompts
- Per-provider models
- User preferences

**Advice**: Design your config format early. It's harder to refactor later.

---

## Future Roadmap

Here's what I'm thinking about adding:

- **Export explanations** — Save explanations as Markdown files
- **Keyboard shortcuts** — Quick access without mouse
- **Multiple languages** — Detect code language and adjust prompt
- **Snippets library** — Save and manage your favorite explanations
- **Collaborative prompts** — Share custom prompts with team
- **Performance metrics** — Show token usage and response time

---

## Getting Started

If you want to try Auto Code Explainer:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python main.py`
4. Configure your AI provider (Ollama for free local AI, or cloud APIs)
5. Toggle ON and start copying code!

---

## Resources & Links

- **GitHub**: [github.com/yourusername/auto-code-explainer](https://github.com/yourusername/auto-code-explainer)
- **Issue Tracker**: Report bugs or request features
- **Contributing**: PRs are welcome! Check `CONTRIBUTING.md` for guidelines

---

## Thanks for Reading!

If you found this helpful, follow me on GitHub for more Python/AI projects. Have questions? Let me know in the comments!

---

## Appendix: Project Structure

```
auto-code-explainer/
├── main.py                    # Entry point
├── config.py                  # Configuration management
├── ai_providers.py            # AI provider integrations
├── clipboard_monitor.py       # Clipboard polling and code detection
├── ui/
│   ├── __init__.py
│   ├── app.py                 # Main application window
│   ├── popup.py               # Explanation popup dialog
│   └── settings.py            # Settings configuration dialog
├── tests/
│   ├── __init__.py
│   ├── test_ai_providers.py
│   ├── test_clipboard_monitor.py
│   ├── test_config.py
│   └── test_font.py
├── pyproject.toml             # Poetry configuration
├── requirements.txt           # Runtime dependencies
├── README.md                  # Project documentation
└── .github/
    └── workflows/
        └── validate.yml       # CI/CD pipeline
```

---

*Cover image: A screenshot of the Auto Code Explainer in action, showing the explanation popup with code on top and AI-generated explanation below.*

# Auto Code Explainer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

> Automatically explains code as you copy it. Supports OpenAI, NVIDIA NIM, Google Gemini, and local Ollama.

## Why This Was Built

As a developer, I often copy code snippets from documentation, Stack Overflow, or chat AI tools only to forget what they do minutes later. This tool solves that by:

- **Zero-effort learning**: Explains code automatically the moment you copy it
- **Multi-provider support**: Use local models (Ollama) or cloud APIs (OpenAI, NVIDIA, Gemini)
- **Multiple explanation styles**: Beginner-friendly, senior code review, security audit, and more
- **Cross-platform**: Works on Windows, Linux, and macOS (including WSL)

## Features

- **Automatic clipboard monitoring** - Detects code snippets and explains them automatically
- **Live streaming responses** - See AI responses as they're generated
- **Multi-provider support**:
  - OpenAI (GPT-4o, GPT-4-turbo, o3-mini, etc.)
  - NVIDIA NIM (Llama, Mistral, Gemma, etc.)
  - Google Gemini (2.0 Flash, 1.5 Pro, etc.)
  - Ollama (local - Llama 3.2, etc.)
- **Custom prompts** - Create and save your own explanation styles
- **Audio output** - Listen to explanations (optional)
- **Cross-platform** - Windows, Linux, macOS, WSL2
- **Settings UI** - Configure providers, models, prompts, and preferences
- **History tracking** - Re-explain past snippets
- **Dark theme UI** - Modern, eye-friendly interface

## Screenshots

### Main Application Window
```
┌─────────────────────────────────────────────────────────────────┐
│ </> Auto Code Explainer           ●  [ON]  [Settings]          │
├─────────────────────────────────────────────────────────────────┤
│  ● Watching clipboard — copy any code to explain automatically │
│                                                                 │
│  Last clipboard read: def fibonacci(n):                         │
│                                                                 │
│  Recent Snippets                    [Clear]                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  def fibonacci(n):                                      │   │
│  │  if n <= 1:                                             │   │
│  │      return n                                           │   │
│  │  return fibonacci(n-1) + fibonacci(n-2)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Explanation Popup
```
┌─────────────────────────────────────────────────────────────────┐
│ ● Code Explanation    OLLAMA - llama3.2              [X]      │
├─────────────────────────────────────────────────────────────────┤
│ Prompt: [General Explainer ▼]  [Re-explain]                   │
├─────────────────────────────────────────────────────────────────┤
│ Copied Code                                                     │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ def fibonacci(n):                                       │   │
│ │     if n <= 1:                                          │   │
│ │         return n                                        │   │
│ │     return fibonacci(n-1) + fibonacci(n-2)              │   │
│ └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Explanation                                                     │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ This function calculates Fibonacci numbers using       │   │
│ │ recursion. The base case returns n for n ≤ 1. For      │   │
│ │ larger values, it recursively calls itself twice...    │   │
│ └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ [Volume] [A-] 14pt [A+] [Close] [Copy]                        │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Dialog
```
┌─────────────────────────────────────────────────────────────────┐
│ Settings - Auto Code Explainer                                  │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│  Provider       │  Models         │  Prompts        │  Pref.    │
├─────────────────┴─────────────────┴─────────────────┴───────────┤
│  Active Provider                                                │
│  ○ Ollama (Local) - No API key — runs on your machine          │
│  ○ OpenAI - GPT-4o, GPT-4-turbo, o3-mini                       │
│  ○ NVIDIA NIM - Cloud-hosted open models                       │
│  ○ Google Gemini - Gemini 2.0 Flash, 1.5 Pro                   │
│                                                                 │
│  API Keys                                                       │
│  OpenAI API Key  [____________________________________]       │
│  NVIDIA API Key  [____________________________________]       │
│  Gemini API Key  [____________________________________]       │
│                                                                 │
│  Ollama Host     [http://localhost:11434]  [Test Connection]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download

```bash
cd /path/to/ai_code_explainer_on_copy
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install System Dependencies

#### Linux (Ubuntu/Debian)
```bash
# Clipboard support
sudo apt install xclip xsel wl-clipboard

# Optional: For system tray
sudo apt install python3-dev python3-tk
```

#### macOS
```bash
# Clipboard support (usually already available)
# Install pyperclip if needed
pip install pyperclip
```

#### Windows
```bash
# Clipboard support via pyperclip (included in requirements)
# System tray requires:
pip install pywin32
```

#### WSL2 (Windows Subsystem for Linux)
```bash
# WSL uses Windows clipboard via PowerShell automatically
# No additional setup needed for clipboard
```

## How to Run

### Method 1: Direct Execution

```bash
# From the project directory
python main.py

# Or with python3
python3 main.py
```

### Method 2: Create a Desktop Shortcut

#### Linux
```bash
# Create a launcher script
echo '#!/bin/bash
cd /path/to/ai_code_explainer_on_copy
python3 main.py' | sudo tee /usr/local/bin/code-explainer > /dev/null
sudo chmod +x /usr/local/bin/code-explainer
```

#### Windows
Create a batch file `code-explainer.bat`:
```batch
@echo off
cd "C:\path\to\ai_code_explainer_on_copy"
python main.py
```

#### macOS
Create an Automator app or use:
```bash
echo '#!/bin/bash
cd /path/to/ai_code_explainer_on_copy
python3 main.py' > /Applications/code-explainer
chmod +x /Applications/code-explainer
```

### First Run

1. Launch the application
2. The app will minimize to system tray (if available) or show the main window
3. Click **Settings** to configure:
   - Choose your AI provider
   - Add API keys (if using cloud providers)
   - Select your model
4. Toggle **ON** to start monitoring your clipboard
5. Copy any code snippet - the explanation popup will appear automatically

## Quick Start Guide

1. **Install** the dependencies: `pip install -r requirements.txt`
2. **Run**: `python main.py`
3. **Configure**: Click Settings → Choose provider (default: Ollama)
4. **Enable**: Toggle the ON/OFF switch to start monitoring
5. **Copy code**: Paste any code into your clipboard → automatic explanation!
6. **Customize**: Adjust font size with `Ctrl + MouseWheel` in explanation windows

## Configuration

### Supported Providers

| Provider | API Key Required | Local | Models |
|----------|------------------|-------|--------|
| Ollama | ❌ No | ✅ Yes | Any installed locally |
| OpenAI | ✅ Yes | ❌ No | GPT-4o, GPT-4-turbo, o1, o3 |
| NVIDIA NIM | ✅ Yes | ❌ No | Llama, Mistral, Gemma |
| Gemini | ✅ Yes | ❌ No | Gemini 2.0 Flash, 1.5 Pro |

### Built-in Prompts

1. **General Explainer** - Balanced technical explanation
2. **Beginner Friendly** - Simple language, step-by-step
3. **Senior Code Review** - Bugs, performance, security issues
4. **Security Audit** - OWASP Top 10 analysis
5. **Business Logic** - Non-technical explanation
6. **Add Comments** - Inline comments for your code

### Config File Location

Configuration is stored at:
- Linux/Mac: `~/.auto-code-explainer/config.json`
- Windows: `%APPDATA%\.auto-code-explainer\config.json`

## Usage Tips

- **Font resizing**: Use `Ctrl + MouseWheel` to adjust text size in explanation windows
- **Re-explain**: Change the prompt and click "Re-explain" without closing the popup
- **Audio**: Enable in Settings → Preferences to hear explanations
- **Min code length**: Adjust in Settings to trigger on shorter snippets
- **Code detection**: Works on indented blocks, code fences, and typical code patterns

## Troubleshooting

### "No clipboard backend found"
- **Linux**: Install `xclip` or `xsel`: `sudo apt install xclip`
- **macOS**: `pip install pyperclip` should work out of box
- **Windows**: pyperclip handles this automatically
- **WSL**: PowerShell clipboard integration is used automatically

### "Cannot connect to Ollama"
- Ensure Ollama is running: `ollama serve`
- Check host URL in Settings matches your Ollama installation
- Pull a model: `ollama pull llama3.2`

### "Invalid API key"
- Verify your API key in Settings → Provider tab
- Test connection with the "Test Connection" button
- Check that your key has credits/usage remaining

### Popup doesn't appear on copy
- Toggle monitoring OFF and back ON
- Check the Logs tab for diagnostic messages
- Verify code length meets minimum (default: 20 chars)

## Development

### Project Structure
```
ai_code_explainer_on_copy/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── ai_providers.py      # AI provider integrations
├── clipboard_monitor.py # Clipboard polling and code detection
├── ui/
│   ├── __init__.py
│   ├── app.py           # Main window
│   ├── popup.py         # Explanation popup
│   └── settings.py      # Settings dialog
└── requirements.txt
```

### Adding a New AI Provider

1. Add a class extending `AIProvider` in `ai_providers.py`
2. Implement `explain()`, `list_models()`, and `validate()`
3. Add to the `build_provider()` factory function

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with Python and Tkinter
- Clipboard monitoring inspired by various open-source projects
- AI provider implementations based on official API documentation

---

**Happy coding!** 🚀

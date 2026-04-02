import json
from pathlib import Path

DEFAULT_PROMPTS = [
    {
        "name": "General Explainer",
        "text": (
            "You are a code explainer. When given a code snippet, explain what it does clearly and concisely. "
            "Cover: what the code does overall, how key parts work, and any notable patterns or potential issues. "
            "Keep explanations beginner-friendly but technically accurate. Format with clear sections."
        ),
    },
    {
        "name": "Beginner Friendly",
        "text": (
            "Explain this code to someone who is just learning to program. "
            "Avoid jargon — when you must use a technical term, define it in plain English. "
            "Use simple analogies where helpful. Walk through what happens step by step, "
            "as if narrating the code's execution. End with a one-sentence summary of what the code achieves."
        ),
    },
    {
        "name": "Senior Code Review",
        "text": (
            "You are a senior software engineer reviewing this code. "
            "Identify: (1) what the code does, (2) potential bugs or edge cases, "
            "(3) performance concerns, (4) security issues if any, "
            "(5) suggestions to improve readability or maintainability. "
            "Be direct and specific — point to line-level issues where possible."
        ),
    },
    {
        "name": "Security Audit",
        "text": (
            "Perform a security-focused analysis of this code. "
            "Look for: injection vulnerabilities, authentication/authorization flaws, "
            "insecure data handling, hardcoded secrets, unsafe deserialization, "
            "input validation gaps, and any OWASP Top 10 concerns. "
            "Rate each finding as Critical / High / Medium / Low. "
            "Suggest specific fixes for each issue found."
        ),
    },
    {
        "name": "Business Logic",
        "text": (
            "Explain the business logic and intent behind this code in plain English. "
            "Ignore implementation details — focus on WHAT business problem it solves "
            "and WHY it might have been written this way. "
            "Describe it as you would to a non-technical stakeholder or product manager."
        ),
    },
    {
        "name": "Add Comments",
        "text": (
            "Add inline comments to this code to explain what each significant block does. "
            "Return the full code with comments added. Keep comments concise but informative. "
            "Also add a brief docstring or header comment summarising the overall purpose."
        ),
    },
]

DEFAULT_CONFIG = {
    "provider": "ollama",
    "models": {
        "openai": "gpt-4o-mini",
        "nvidia": "meta/llama-3.1-70b-instruct",
        "gemini": "gemini-2.0-flash",
        "ollama": "llama3.2",
    },
    "api_keys": {
        "openai": "",
        "nvidia": "",
        "gemini": "",
    },
    "ollama_host": "http://localhost:11434",
    "nvidia_base_url": "https://integrate.api.nvidia.com/v1",
    "enabled": True,
    "min_code_length": 20,
    "prompts": DEFAULT_PROMPTS,
    "active_prompt": "General Explainer",
    # Audio output settings
    "enable_audio": False,
    # legacy field kept for migration
    "system_prompt": "",
}


class Config:
    def __init__(self):
        self.config_path = Path.home() / ".auto-code-explainer" / "config.json"
        self.data = self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    saved = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                for k, v in saved.items():
                    if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                # Ensure prompts list always has content
                if not merged.get("prompts"):
                    merged["prompts"] = DEFAULT_PROMPTS
                # Migrate old system_prompt to a custom prompt entry
                old = merged.get("system_prompt", "").strip()
                if old:
                    names = [p["name"] for p in merged["prompts"]]
                    if "Custom (migrated)" not in names:
                        merged["prompts"].append({"name": "Custom (migrated)", "text": old})
                    merged["system_prompt"] = ""
                return merged
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)

    # ── Prompt helpers ────────────────────────────────────────────────────────

    @property
    def prompts(self) -> list[dict]:
        return self.data.get("prompts", DEFAULT_PROMPTS)

    @property
    def prompt_names(self) -> list[str]:
        return [p["name"] for p in self.prompts]

    @property
    def active_prompt(self) -> str:
        return self.data.get("active_prompt", self.prompt_names[0] if self.prompts else "")

    @active_prompt.setter
    def active_prompt(self, name: str):
        self.data["active_prompt"] = name
        self.save()

    def get_prompt_text(self, name: str) -> str:
        for p in self.prompts:
            if p["name"] == name:
                return p["text"]
        # Fallback to first prompt
        return self.prompts[0]["text"] if self.prompts else ""

    @property
    def active_prompt_text(self) -> str:
        return self.get_prompt_text(self.active_prompt)

    # ── Provider helpers ──────────────────────────────────────────────────────

    @property
    def provider(self):
        return self.data["provider"]

    @provider.setter
    def provider(self, v):
        self.data["provider"] = v
        self.save()

    @property
    def enabled(self):
        return self.data["enabled"]

    @enabled.setter
    def enabled(self, v):
        self.data["enabled"] = v
        self.save()

    @property
    def current_model(self):
        return self.data["models"].get(self.provider, "")

    @current_model.setter
    def current_model(self, v):
        self.data["models"][self.provider] = v
        self.save()

    @property
    def current_api_key(self):
        return self.data["api_keys"].get(self.provider, "")

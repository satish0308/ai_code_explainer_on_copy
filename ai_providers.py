"""
AI provider integrations: OpenAI, NVIDIA NIM, Gemini, Ollama.
All providers implement a streaming `explain(code, system_prompt)` generator.
"""

import requests
import json
from abc import ABC, abstractmethod
from typing import Generator, Optional


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


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            models = [m["id"] for m in resp.json().get("data", [])]
            # Filter to chat models
            chat_models = [m for m in models if any(x in m for x in ["gpt", "o1", "o3", "llama", "mistral", "deepseek"])]
            return sorted(chat_models) or models[:20]
        except Exception:
            return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

    def validate(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "API key is required"
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 401:
                return False, "Invalid API key"
            resp.raise_for_status()
            return True, ""
        except requests.ConnectionError:
            return False, "Cannot connect to API"
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# NVIDIA NIM (OpenAI-compatible)
# ---------------------------------------------------------------------------

class NvidiaProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, api_key: str, model: str, base_url: str = DEFAULT_BASE_URL):
        super().__init__(api_key, model, base_url)

    def list_models(self) -> list[str]:
        # NVIDIA NIM popular models
        return [
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.2-3b-instruct",
            "mistralai/mixtral-8x22b-instruct-v0.1",
            "mistralai/mistral-large-2-instruct",
            "google/gemma-2-27b-it",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "deepseek-ai/deepseek-r1",
            "qwen/qwen2.5-72b-instruct",
        ]

    def validate(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "NVIDIA API key is required"
        return super().validate()


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

class GeminiProvider(AIProvider):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def explain(self, code: str, system_prompt: str) -> Generator[str, None, None]:
        url = f"{self.BASE_URL}/models/{self.model}:streamGenerateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Explain this code:\n\n```\n{code}\n```"}],
                }
            ],
            "generationConfig": {"temperature": 0.3},
        }
        with requests.post(
            url,
            params={"key": self.api_key, "alt": "sse"},
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
                try:
                    chunk = json.loads(line)
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text = part.get("text", "")
                            if text:
                                yield text
                except (json.JSONDecodeError, KeyError):
                    continue

    def list_models(self) -> list[str]:
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-2.5-pro-exp-03-25",
        ]

    def validate(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Gemini API key is required"
        try:
            resp = requests.get(
                f"{self.BASE_URL}/models",
                params={"key": self.api_key},
                timeout=10,
            )
            if resp.status_code == 400:
                return False, "Invalid API key"
            resp.raise_for_status()
            return True, ""
        except requests.ConnectionError:
            return False, "Cannot connect to Gemini API"
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------

class OllamaProvider(AIProvider):
    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model

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
            f"{self.host}/api/chat",
            json=payload,
            stream=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    def validate(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            if not models:
                return False, "Ollama is running but no models are installed. Run: ollama pull llama3.2"
            names = [m["name"] for m in models]
            if self.model and self.model not in names and f"{self.model}:latest" not in names:
                return False, f"Model '{self.model}' not found. Available: {', '.join(names[:5])}"
            return True, ""
        except requests.ConnectionError:
            return False, f"Cannot connect to Ollama at {self.host}. Is Ollama running?"
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_provider(config) -> AIProvider:
    provider = config.provider
    if provider == "openai":
        return OpenAIProvider(
            api_key=config.data["api_keys"]["openai"],
            model=config.data["models"]["openai"],
        )
    elif provider == "nvidia":
        return NvidiaProvider(
            api_key=config.data["api_keys"]["nvidia"],
            model=config.data["models"]["nvidia"],
            base_url=config.data.get("nvidia_base_url", NvidiaProvider.DEFAULT_BASE_URL),
        )
    elif provider == "gemini":
        return GeminiProvider(
            api_key=config.data["api_keys"]["gemini"],
            model=config.data["models"]["gemini"],
        )
    elif provider == "ollama":
        return OllamaProvider(
            host=config.data.get("ollama_host", "http://localhost:11434"),
            model=config.data["models"]["ollama"],
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

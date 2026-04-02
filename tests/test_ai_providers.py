"""
Tests for AI provider integrations.
Note: These tests use mocking to avoid actual API calls.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch

from ai_providers import (
    OpenAIProvider,
    NvidiaProvider,
    GeminiProvider,
    OllamaProvider,
    build_provider,
)


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    @patch("ai_providers.requests")
    def test_list_models(self, mock_requests):
        """Test listing models."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-3.5-turbo"},
                {"id": "custom-llama-7b"},
            ]
        }
        mock_requests.get.return_value = mock_response

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        models = provider.list_models()

        assert "gpt-4o" in models
        assert "gpt-3.5-turbo" in models

    @patch("ai_providers.requests")
    def test_validate_success(self, mock_requests):
        """Test API key validation success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        provider = OpenAIProvider(api_key="valid-key", model="gpt-4o")
        ok, msg = provider.validate()

        assert ok is True
        assert msg == ""

    @patch("ai_providers.requests")
    def test_validate_invalid_key(self, mock_requests):
        """Test API key validation with invalid key."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response

        provider = OpenAIProvider(api_key="invalid-key", model="gpt-4o")
        ok, msg = provider.validate()

        assert ok is False
        assert "Invalid API key" in msg


class TestNvidiaProvider:
    """Tests for NVIDIA NIM provider."""

    def test_default_base_url(self):
        """Test default base URL."""
        provider = NvidiaProvider(api_key="test-key", model="llama")
        assert provider.base_url == "https://integrate.api.nvidia.com/v1"

    @patch("ai_providers.requests")
    def test_list_models(self, mock_requests):
        """Test listing models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        provider = NvidiaProvider(api_key="test-key", model="llama")
        models = provider.list_models()

        assert len(models) > 0
        assert any("llama" in m.lower() for m in models)


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_init_with_custom_host(self):
        """Test initialization with custom host."""
        provider = OllamaProvider(host="http://custom-host:9999", model="llama")
        assert provider.host == "http://custom-host:9999"

    @patch("ai_providers.requests")
    def test_list_models_success(self, mock_requests):
        """Test listing models from Ollama."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:latest"},
            ]
        }
        mock_requests.get.return_value = mock_response

        provider = OllamaProvider(host="http://localhost:11434", model="llama3")
        models = provider.list_models()

        assert len(models) == 2
        assert "llama3:latest" in models

    @patch("ai_providers.requests")
    def test_validate_no_models(self, mock_requests):
        """Test validation when no models are installed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_requests.get.return_value = mock_response

        provider = OllamaProvider(host="http://localhost:11434", model="llama3")
        ok, msg = provider.validate()

        assert ok is False
        assert "no models are installed" in msg.lower()


class TestBuildProvider:
    """Tests for the build_provider factory function."""

    def test_build_openai(self):
        """Test building OpenAI provider."""
        config = Mock()
        config.provider = "openai"
        config.data = {
            "api_keys": {"openai": "test-key"},
            "models": {"openai": "gpt-4o"},
        }

        provider = build_provider(config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4o"

    def test_build_nvidia(self):
        """Test building NVIDIA provider."""
        config = Mock()
        config.provider = "nvidia"
        config.data = {
            "api_keys": {"nvidia": "test-key"},
            "models": {"nvidia": "llama"},
        }

        provider = build_provider(config)
        assert isinstance(provider, NvidiaProvider)

    def test_build_gemini(self):
        """Test building Gemini provider."""
        config = Mock()
        config.provider = "gemini"
        config.data = {
            "api_keys": {"gemini": "test-key"},
            "models": {"gemini": "gemini-2.0-flash"},
        }

        provider = build_provider(config)
        assert isinstance(provider, GeminiProvider)

    def test_build_ollama(self):
        """Test building Ollama provider."""
        config = Mock()
        config.provider = "ollama"
        config.data = {
            "models": {"ollama": "llama3"},
            "ollama_host": "http://localhost:11434",
        }

        provider = build_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_build_unknown_provider(self):
        """Test building with unknown provider raises error."""
        config = Mock()
        config.provider = "unknown"
        config.data = {}

        try:
            build_provider(config)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown provider: unknown" in str(e)

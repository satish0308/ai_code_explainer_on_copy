"""
Tests for the configuration module.
"""

import json
import os

# Mock the config module by adding parent to path
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_CONFIG, DEFAULT_PROMPTS, Config


def test_config_default_values():
    """Test that config loads with default values when no file exists."""
    # Create a temporary directory for config
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_home = Path(tmpdir)
        config_path = temp_home / ".auto-code-explainer" / "config.json"

        # Temporarily set config to use temp directory
        config = Config.__new__(Config)
        config.config_path = config_path
        config.data = config._load()

        # Verify defaults
        assert config.data["provider"] == "ollama"
        assert config.data["enabled"] is True
        assert config.data["min_code_length"] == 20
        assert len(config.data["prompts"]) == len(DEFAULT_PROMPTS)


def test_config_save_and_load():
    """Test that config can be saved and reloaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_home = Path(tmpdir)
        config_path = temp_home / ".auto-code-explainer" / "config.json"

        config = Config.__new__(Config)
        config.config_path = config_path

        # Set custom values
        config.data = DEFAULT_CONFIG.copy()
        config.data["provider"] = "openai"
        config.data["enabled"] = False
        config.data["min_code_length"] = 50

        # Save
        config.save()

        # Verify file exists
        assert config_path.exists()

        # Load fresh
        config2 = Config.__new__(Config)
        config2.config_path = config_path
        config2.data = config2._load()

        # Verify values persisted
        assert config2.data["provider"] == "openai"
        assert config2.data["enabled"] is False
        assert config2.data["min_code_length"] == 50


def test_config_migrates_old_system_prompt():
    """Test migration of old system_prompt field to custom prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_home = Path(tmpdir)
        config_path = temp_home / ".auto-code-explainer" / "config.json"

        # Create config with old format
        old_config = DEFAULT_CONFIG.copy()
        old_config["system_prompt"] = "You are a helpful assistant."
        old_config["prompts"] = []  # Empty prompts to trigger migration

        with open(config_path, "w") as f:
            json.dump(old_config, f)

        # Load and check migration
        config = Config.__new__(Config)
        config.config_path = config_path
        config.data = config._load()

        # system_prompt should be cleared and custom prompt created
        assert config.data.get("system_prompt") == ""

        prompt_names = [p["name"] for p in config.data["prompts"]]
        assert "Custom (migrated)" in prompt_names


def test_config_get_prompt_text():
    """Test prompt text retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_home = Path(tmpdir)
        config_path = temp_home / ".auto-code-explainer" / "config.json"

        config = Config.__new__(Config)
        config.config_path = config_path
        config.data = DEFAULT_CONFIG.copy()

        # Test getting a known prompt
        prompt_text = config.get_prompt_text("General Explainer")
        assert "code explainer" in prompt_text.lower()

        # Test fallback for unknown prompt
        prompt_text = config.get_prompt_text("Unknown Prompt")
        assert prompt_text is not None  # Returns first prompt


def test_config_active_prompt():
    """Test active prompt property."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_home = Path(tmpdir)
        config_path = temp_home / ".auto-code-explainer" / "config.json"

        config = Config.__new__(Config)
        config.config_path = config_path
        config.data = DEFAULT_CONFIG.copy()

        # Test getter
        assert config.active_prompt == "General Explainer"

        # Test setter
        config.active_prompt = "Beginner Friendly"
        assert config.active_prompt == "Beginner Friendly"
        assert config.data["active_prompt"] == "Beginner Friendly"

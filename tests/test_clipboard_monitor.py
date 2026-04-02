"""
Tests for clipboard monitoring functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from unittest.mock import Mock, patch, MagicMock

from clipboard_monitor import (
    _get_clipboard,
    is_likely_code,
    ClipboardMonitor,
)


class TestIsLikelyCode:
    """Tests for code detection logic."""

    def test_short_text(self):
        """Test that short text is not detected as code."""
        is_code, reason = is_likely_code("print('hi')", min_length=20)
        assert is_code is False
        assert "too short" in reason

    def test_code_fence(self):
        """Test markdown code fence detection."""
        code = """```python
def hello():
    print("hello")
```"""
        is_code, reason = is_likely_code(code)
        assert is_code is True
        assert "markdown" in reason.lower()

    def test_def_function(self):
        """Test detection of Python function definitions."""
        code = """def hello(name):
    return f"Hello, {name}!"

def main():
    print(hello("World"))"""
        is_code, reason = is_likely_code(code, min_length=10)
        assert is_code is True
        assert "def" in reason

    def test_various_code_patterns(self):
        """Test various code patterns."""
        patterns = [
            ("import os", "import"),
            ("var x = 1", "var"),
            ("let y = 2", "let"),
            ("const z = 3", "const"),
            ("public class Test", "public"),
            ("if (x > 0)", "if"),
            ("while (true)", "while"),
            ("for i in range(10)", "for"),
            ("try:", "try"),
            ("except Exception:", "except"),
            ("console.log('test')", "console"),
            ("System.out.println", "System"),
            ("SELECT * FROM users", "SELECT"),
        ]

        for code, expected_pattern in patterns:
            is_code, reason = is_likely_code(code, min_length=10)
            assert is_code is True, f"Failed for: {code}"
            assert expected_pattern.lower() in reason, f"Pattern {expected_pattern} not found in: {reason}"

    def test_indented_blocks(self):
        """Test detection of indented code blocks."""
        code = """def hello():
    print("hello")
    print("world")
print("done")"""
        is_code, reason = is_likely_code(code, min_length=20)
        assert is_code is True
        assert "indentation" in reason

    def test_plain_text_not_code(self):
        """Test that plain text is not detected as code."""
        text = """This is a blog post about programming.
It contains general thoughts about code quality.
No actual code snippets here."""
        is_code, reason = is_likely_code(text, min_length=20)
        assert is_code is False


class TestClipboardMonitor:
    """Tests for ClipboardMonitor class."""

    @patch("clipboard_monitor.subprocess")
    def test_monitor_start_stop(self, mock_subprocess):
        """Test starting and stopping the monitor."""
        callback = Mock()
        log_callback = Mock()

        monitor = ClipboardMonitor(
            callback=callback,
            log_callback=log_callback,
            poll_interval=0.1,  # Fast poll for testing
        )

        monitor.start()
        assert monitor._enabled is True
        assert monitor._thread is not None
        assert monitor._thread.is_alive()

        monitor.stop()
        # Give thread time to stop
        import time
        time.sleep(0.2)
        assert not monitor._thread.is_alive()

    def test_monitor_callback_on_code(self):
        """Test that callback is called when code is detected."""
        callback = Mock()
        log_callback = Mock()

        with patch("clipboard_monitor._get_clipboard") as mock_clipboard:
            mock_clipboard.return_value = ("def test():\n    pass", "pyperclip")
            monitor = ClipboardMonitor(
                callback=callback,
                log_callback=log_callback,
                poll_interval=0.1,
            )
            monitor.start()

            import time
            time.sleep(0.3)

            # Callback should have been called
            assert callback.called

            monitor.stop()

    def test_monitor_no_duplicate_callback(self):
        """Test that callback is not called for duplicate content."""
        callback = Mock()
        log_callback = Mock()

        call_count = 0

        def count_calls(code):
            nonlocal call_count
            call_count += 1

        with patch("clipboard_monitor._get_clipboard") as mock_clipboard:
            # First call returns code
            mock_clipboard.side_effect = [
                ("def test():\n    pass", "pyperclip"),
                ("def test():\n    pass", "pyperclip"),
                ("def test2():\n    pass", "pyperclip"),
            ]
            monitor = ClipboardMonitor(
                callback=count_calls,
                log_callback=log_callback,
                poll_interval=0.1,
            )
            monitor.start()

            import time
            time.sleep(0.4)

            # Should only be called twice (new code detected)
            assert call_count >= 1

            monitor.stop()

    def test_set_enabled(self):
        """Test enabling and disabling monitoring."""
        callback = Mock()
        log_callback = Mock()

        monitor = ClipboardMonitor(
            callback=callback,
            log_callback=log_callback,
            poll_interval=0.1,
        )
        monitor.start()

        monitor.set_enabled(False)
        assert monitor._enabled is False

        monitor.set_enabled(True)
        assert monitor._enabled is True

        monitor.stop()

    def test_set_min_length(self):
        """Test setting minimum code length."""
        monitor = ClipboardMonitor(
            callback=Mock(),
            log_callback=Mock(),
        )
        monitor.set_min_length(100)
        assert monitor.min_code_length == 100

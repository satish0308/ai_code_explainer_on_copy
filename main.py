#!/usr/bin/env python3
"""
Auto Code Explainer — entry point.

Monitors your clipboard. When you copy code (Ctrl+C),
it automatically explains it using your configured AI provider.
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        from ui.app import App
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

    app = App()
    app.run()


def get_app():
    """Get the app instance for testing purposes."""
    from ui.app import App
    return App()


if __name__ == "__main__":
    main()

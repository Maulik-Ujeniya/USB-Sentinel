"""
USB-Sentinel — Main Entry Point
Run this file to start everything:
  python main.py

This will:
  1. Initialize the database
  2. Start the Flask web dashboard on http://localhost:5000
  3. Optionally start USB protection watcher in the background
"""

import os
import sys
import threading
import webbrowser
import time

# Ensure core/ is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.db import init_db, get_setting


def start_dashboard(port=5000):
    """Start the Flask dashboard."""
    # Import here to avoid circular imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "gui", "dashboard"))
    from gui.dashboard.app import app
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def start_protection():
    """Start the USB watcher in a background thread."""
    try:
        from core.detector import start_watching
        start_watching()
    except Exception as e:
        print(f"  [WARNING] USB watcher error: {e}")


def main():
    port = 5000

    print()
    print("  +==========================================+")
    print("  |         USB-Sentinel                     |")
    print("  |     USB Security & Inspection Tool       |")
    print("  +==========================================+")
    print()

    # Step 1: Initialize database
    print("  > Initializing database...")
    init_db()
    print("  [OK] Database ready")

    # Step 2: Start USB protection if enabled
    auto_protect = get_setting("start_protection_on_launch", "1")
    if auto_protect == "1":
        print("  > Starting USB protection watcher...")
        watcher_thread = threading.Thread(target=start_protection, daemon=True)
        watcher_thread.start()
        print("  [OK] USB watcher running in background")
    else:
        print("  > USB protection auto-start is disabled (enable in Settings)")

    # Step 3: Open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    # Step 4: Start Flask dashboard (blocks)
    print(f"\n  [OK] Dashboard starting at: http://localhost:{port}")
    print("  [OK] Press Ctrl+C to stop\n")

    try:
        start_dashboard(port)
    except KeyboardInterrupt:
        print("\n  USB-Sentinel stopped. Goodbye!")


if __name__ == "__main__":
    main()

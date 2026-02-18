"""Desktop launcher — opens the app in a native macOS window.

Features:
  - Native menu bar (File, View, Help)
  - Window position/size persistence across launches
  - Loading splash while Flask starts
  - Native macOS notifications for background events
  - Auto git-sync on close
"""
import json
import logging
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import webview
from webview.menu import Menu, MenuAction, MenuSeparator

from config import WEB_HOST, WEB_PORT, DATA_DIR
from core.git_sync import sync_to_git
from web.app import create_app

logger = logging.getLogger(__name__)

# --- Window State Persistence ---

_WINDOW_STATE_FILE = DATA_DIR / ".window_state.json"
_DEFAULT_STATE = {"x": None, "y": None, "width": 1440, "height": 900}


def _load_window_state():
    """Load saved window position/size, or return defaults."""
    try:
        if _WINDOW_STATE_FILE.exists():
            state = json.loads(_WINDOW_STATE_FILE.read_text())
            merged = {**_DEFAULT_STATE, **state}
            # Validate saved position is on a visible screen
            try:
                from AppKit import NSScreen
                screens = NSScreen.screens()
                if screens and merged["x"] is not None and merged["y"] is not None:
                    visible = False
                    for screen in screens:
                        frame = screen.frame()
                        sx, sy = frame.origin.x, frame.origin.y
                        sw, sh = frame.size.width, frame.size.height
                        # Check if at least part of the window is on this screen
                        if (merged["x"] < sx + sw and merged["x"] + merged["width"] > sx and
                                merged["y"] < sy + sh and merged["y"] + merged["height"] > sy):
                            visible = True
                            break
                    if not visible:
                        merged["x"] = None
                        merged["y"] = None
            except ImportError:
                pass  # AppKit not available — skip validation
            return merged
    except Exception:
        pass
    return _DEFAULT_STATE.copy()


def _save_window_state(window):
    """Persist current window geometry."""
    try:
        state = {
            "x": window.x,
            "y": window.y,
            "width": window.width,
            "height": window.height,
        }
        _WINDOW_STATE_FILE.write_text(json.dumps(state))
    except Exception:
        pass


# --- Native macOS Notifications ---

def send_notification(title, message, sound=True):
    """Send a native macOS notification via osascript."""
    try:
        # Sanitize inputs to prevent osascript injection
        safe_title = str(title).replace("\\", "\\\\").replace('"', '\\"')
        safe_message = str(message).replace("\\", "\\\\").replace('"', '\\"')
        sound_part = 'sound name "default"' if sound else ""
        script = (
            f'display notification "{safe_message}" '
            f'with title "{safe_title}" {sound_part}'
        )
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# --- Loading Splash ---

_SPLASH_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
    background: #1a1a1a;
    color: #e0dcd3;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    flex-direction: column;
    gap: 24px;
  }
  .title { font-size: 28px; font-weight: 600; letter-spacing: -0.5px; }
  .subtitle { font-size: 14px; color: #888; }
  .spinner {
    width: 32px; height: 32px;
    border: 3px solid #333;
    border-top-color: #bc6c5a;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
  <div class="title">Research Taxonomy Library</div>
  <div class="spinner"></div>
  <div class="subtitle">Starting up...</div>
</body>
</html>
"""


# --- Menu Actions ---

_window_ref = None
_port_ref = None


def _menu_export_json():
    if _window_ref:
        _window_ref.evaluate_js("safeFetch('/api/export/json?project_id=' + currentProjectId).then(r => r.blob()).then(b => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'taxonomy_data.json'; a.click(); })")


def _menu_export_csv():
    if _window_ref:
        _window_ref.evaluate_js("safeFetch('/api/export/csv?project_id=' + currentProjectId).then(r => r.blob()).then(b => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'taxonomy_export.csv'; a.click(); })")


def _menu_reload():
    if _window_ref:
        _window_ref.evaluate_js("location.reload()")


def _menu_toggle_theme():
    if _window_ref:
        _window_ref.evaluate_js("toggleTheme()")


def _menu_shortcuts():
    if _window_ref:
        _window_ref.evaluate_js("toggleShortcutsOverlay()")


def _menu_tour():
    if _window_ref:
        _window_ref.evaluate_js("startProductTour()")


def _build_menus():
    """Build native macOS menu bar."""
    file_menu = Menu(
        "File",
        [
            MenuAction("Export JSON", _menu_export_json),
            MenuAction("Export CSV", _menu_export_csv),
            MenuSeparator(),
            MenuAction("Sync to Git", lambda: sync_to_git("Manual sync")),
        ],
    )
    view_menu = Menu(
        "View",
        [
            MenuAction("Toggle Dark Mode", _menu_toggle_theme),
            MenuAction("Reload", _menu_reload),
        ],
    )
    help_menu = Menu(
        "Help",
        [
            MenuAction("Keyboard Shortcuts", _menu_shortcuts),
            MenuAction("Product Tour", _menu_tour),
        ],
    )
    return [file_menu, view_menu, help_menu]


# --- JS ↔ Python API (exposed to frontend) ---

class DesktopAPI:
    """Methods callable from JS via window.pywebview.api.*"""

    def notify(self, title, message):
        send_notification(title, message)

    def sync_git(self, message="Manual sync"):
        sync_to_git(message)


# --- Server Helpers ---

def _find_free_port(preferred):
    """Return preferred port if available, otherwise find a free one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((WEB_HOST, preferred))
            return preferred
        except OSError:
            s.bind((WEB_HOST, 0))
            return s.getsockname()[1]


def _run_flask(app, port):
    """Run Flask in a background thread (no reloader in desktop mode)."""
    app.run(host=WEB_HOST, port=port, debug=False, use_reloader=False)


def _wait_for_server(host, port, retries=30):
    """Block until the Flask server accepts connections."""
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


# --- Main ---

def _on_closing():
    """Save window state and git-sync on close (non-blocking)."""
    if _window_ref:
        _save_window_state(_window_ref)
    # Fire git sync in a daemon thread so the window closes immediately
    threading.Thread(target=sync_to_git, args=("App closed — auto-save",), daemon=True).start()
    return True


def main():
    global _window_ref, _port_ref

    port = _find_free_port(WEB_PORT)
    _port_ref = port
    flask_app = create_app()

    # Start Flask server in background
    server = threading.Thread(target=_run_flask, args=(flask_app, port), daemon=True)
    server.start()

    # Load saved window geometry
    state = _load_window_state()

    # Show splash while Flask starts
    api = DesktopAPI()
    window = webview.create_window(
        title="Research Taxonomy Library",
        html=_SPLASH_HTML,
        width=state["width"],
        height=state["height"],
        min_size=(1024, 680),
        x=state["x"],
        y=state["y"],
        js_api=api,
    )
    _window_ref = window
    window.events.closing += _on_closing

    def _navigate_when_ready():
        """Wait for Flask, then navigate from splash to the app."""
        if _wait_for_server(WEB_HOST, port):
            window.load_url(f"http://{WEB_HOST}:{port}")
        else:
            window.load_html(
                "<html><body style='font-family:system-ui;display:flex;align-items:center;"
                "justify-content:center;height:100vh;color:#bc6c5a'>"
                "<h2>Failed to start server. Check the terminal for errors.</h2>"
                "</body></html>"
            )

    window.events.loaded += _navigate_when_ready

    webview.start(menu=_build_menus())


if __name__ == "__main__":
    main()

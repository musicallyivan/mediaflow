"""Linux entry point for Media Flow.

Keeps the main application shared with Windows while adapting the few
Windows-specific integration points for Linux.
"""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

import app


def _remove_windows_store_buttons(widget: object) -> None:
    """Remove Microsoft Store controls from the Linux PRO dialog."""
    children = getattr(widget, "winfo_children", lambda: [])()
    for child in children:
        try:
            text = str(child.cget("text"))
        except Exception:
            text = ""
        if "Microsoft Store" in text:
            try:
                child.destroy()
            except Exception:
                pass
        else:
            _remove_windows_store_buttons(child)


_original_pro_build_ui = app.ProUpgradeModal._build_ui


def _linux_pro_build_ui(self: app.ProUpgradeModal) -> None:
    _original_pro_build_ui(self)
    _remove_windows_store_buttons(self)


app.ProUpgradeModal._build_ui = _linux_pro_build_ui


def _linux_open_history_file(self: app.MediaConverterApp, path_str: str) -> None:
    if not os.path.exists(path_str):
        return
    try:
        subprocess.Popen(["xdg-open", str(Path(path_str).parent)])
    except Exception:
        try:
            webbrowser.open(Path(path_str).parent.as_uri())
        except Exception:
            pass


app.MediaConverterApp._open_history_file = _linux_open_history_file


def _linux_check_for_updates(self: app.MediaConverterApp, silent: bool = False) -> None:
    """Linux updates are distributed as GitHub release archives."""
    if not silent:
        webbrowser.open("https://github.com/musicallyivan/mediaflow/releases")
        app.messagebox.showinfo(
            app.APP_TITLE,
            "Las actualizaciones de Linux se publican en GitHub Releases. Se ha abierto la página de descargas.",
        )


app.MediaConverterApp._check_for_updates = _linux_check_for_updates


def main() -> None:
    # Make bundled ffmpeg/ffprobe discoverable by the shared application.
    app_dir = Path(sys.argv[0]).resolve().parent
    os.environ["PATH"] = f"{app_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    window = app.MediaConverterApp()
    window.title(f"{app.APP_TITLE} — Linux v{app.APP_VERSION}")
    window.mainloop()


if __name__ == "__main__":
    main()

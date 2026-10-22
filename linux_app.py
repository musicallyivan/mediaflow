"""Linux entry point for Media Flow.

Adapts desktop integration, font selection, and system notifications for Linux distributions.
"""

from __future__ import annotations

import os
import shutil
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
                parent = getattr(child, "master", None)
                child.destroy()
                if parent and len(getattr(parent, "winfo_children", lambda: [])()) == 0:
                    parent.destroy()
            except Exception:
                pass
        else:
            _remove_windows_store_buttons(child)


_original_pro_build_ui = app.ProUpgradeModal._build_ui


def _linux_pro_build_ui(self: app.ProUpgradeModal) -> None:
    _original_pro_build_ui(self)
    _remove_windows_store_buttons(self)


app.ProUpgradeModal._build_ui = _linux_pro_build_ui


def _linux_check_for_updates(self: app.MediaConverterApp, silent: bool = False) -> None:
    """Linux updates are distributed as GitHub release archives."""
    if not silent:
        webbrowser.open(f"https://github.com/{app.GITHUB_REPO}/releases")
        app.messagebox.showinfo(
            app.APP_TITLE,
            "Las actualizaciones de Linux se publican en GitHub Releases. Se ha abierto la página de descargas en tu navegador.",
        )


app.MediaConverterApp._check_for_updates = _linux_check_for_updates


def main() -> None:
    # Ensure bundled ffmpeg/ffprobe or common Linux bin directories are prioritized
    app_dir = Path(sys.argv[0]).resolve().parent
    extra_paths = [
        str(app_dir),
        str(app_dir / "bin"),
        str(Path.home() / ".local" / "bin"),
        "/usr/local/bin",
        "/usr/bin",
    ]
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{os.pathsep.join(extra_paths)}{os.pathsep}{current_path}"

    window = app.MediaConverterApp()
    window.title(f"{app.APP_TITLE} Suite — Linux v{app.APP_VERSION}")
    window.mainloop()


if __name__ == "__main__":
    main()

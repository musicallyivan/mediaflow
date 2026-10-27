import concurrent.futures
import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Optional

try:
    import PIL._tkinter_finder  # noqa: F401
except ModuleNotFoundError:
    try:
        from tkinter import _tkinter as _tk_mod

        _finder_shim = types.ModuleType("PIL._tkinter_finder")
        _finder_shim.TKINTER_LIB = getattr(_tk_mod, "__file__", None)  # type: ignore[attr-defined]
        _finder_shim.tk_version = str(getattr(_tk_mod, "TK_VERSION", "8.6"))  # type: ignore[attr-defined]
        sys.modules["PIL._tkinter_finder"] = _finder_shim
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

from microsoft_store_pro import MicrosoftStorePro

APP_TITLE = "Media Flow"
APP_VERSION = "1.7.8"
GITHUB_REPO = os.environ.get("MEDIA_FLOW_GITHUB_REPO", "musicallyivan/mediaflow")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
STRIPE_CHECKOUT_URL = os.environ.get("MEDIA_FLOW_STRIPE_URL", "https://buy.stripe.com/4gM00l2uV0aXe6k1eIgEg00")
MS_STORE_PRODUCT_ID = os.environ.get("MEDIA_FLOW_STORE_ID", "9N6VZZ3HDFHJ")

AUDIO_FORMATS_FREE = ("MP3", "M4A", "WAV", "OGG", "AAC")
AUDIO_FORMATS_PRO = ("FLAC", "OPUS", "ALAC", "AIFF")
AUDIO_FORMATS = AUDIO_FORMATS_FREE + AUDIO_FORMATS_PRO

VIDEO_FORMATS_FREE = ("MP4", "MOV", "WEBM", "AVI", "GIF")
VIDEO_FORMATS_PRO = ("MKV", "AV1", "H265")
VIDEO_FORMATS = VIDEO_FORMATS_FREE + VIDEO_FORMATS_PRO

IMAGE_FORMATS = ("PNG", "JPG", "WEBP", "BMP", "AVIF", "ICO", "TIFF")
EXTRACTION_MODES = ("Extraer Audio", "Silenciar Video (Quitar Audio)", "Extraer Subtítulos (SRT)")
CONCAT_MODES = ("Unir Archivos de Audio", "Unir Archivos de Video")

AUDIO_EXTENSIONS = "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff *.m4b"
VIDEO_EXTENSIONS = "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.m4v *.flv *.ogv *.3gp"
IMAGE_EXTENSIONS = "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif *.avif *.heic *.ico"

PRESETS = {
    "Personalizado": {},
    "Optimizado para Web": {"video_format": "MP4", "video_quality": "Equilibrada", "res": "1080p", "fps": "30 fps", "audio_quality": "160 kbps"},
    "WhatsApp / Redes (Ligero)": {"video_format": "MP4", "video_quality": "Comprimida", "res": "720p", "fps": "30 fps", "audio_quality": "128 kbps"},
    "TikTok / Reels / Shorts": {"video_format": "MP4", "video_quality": "Alta", "res": "1080p", "fps": "60 fps (PRO)", "audio_quality": "192 kbps"},
    "Calidad Máxima 4K (PRO)": {"video_format": "MKV", "video_quality": "Alta", "res": "4K (2160p) (PRO)", "fps": "60 fps (PRO)", "audio_quality": "320 kbps"},
    "Audio Alta Fidelidad FLAC (PRO)": {"audio_format": "FLAC", "audio_quality": "320 kbps"},
}

# Fluent Design System Colors (Light, Dark)
COLOR_BG = ("#f3f3f3", "#1e1e1e")
COLOR_HEADER_BG = ("#fbfbfb", "#202020")
COLOR_RAIL_BG = ("#f0f0f0", "#181818")
COLOR_CARD_BG = ("#ffffff", "#2b2b2b")
COLOR_CARD_HOVER = ("#f8f9fa", "#323232")
COLOR_CARD_BORDER = ("#e5e5e5", "#383838")
COLOR_INPUT_BG = ("#ffffff", "#2c2c2c")
COLOR_INPUT_BORDER = ("#d5d5d5", "#404040")
COLOR_ACCENT = ("#0067c0", "#0078d4")
COLOR_ACCENT_HOVER = ("#1879cd", "#1084d8")
COLOR_TEXT_PRIMARY = ("#1b1b1b", "#ffffff")
COLOR_TEXT_SECONDARY = ("#616161", "#a0a0a0")


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_candidate = Path(getattr(sys, "_MEIPASS")) / name
        if meipass_candidate.exists():
            return meipass_candidate
    local_candidate = app_dir() / name
    if local_candidate.exists():
        return local_candidate
    if sys.platform.startswith("linux"):
        for sys_dir in (Path("/opt/media-flow"), Path("/usr/share/media-flow")):
            sys_candidate = sys_dir / name
            if sys_candidate.exists():
                return sys_candidate
    return local_candidate


def config_path() -> Path:
    if sys.platform.startswith("linux"):
        legacy = Path.home() / "Media Flow" / "settings.json"
        if legacy.exists():
            return legacy
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base_xdg = Path(xdg) if xdg else (Path.home() / ".config")
        return base_xdg / "media-flow" / "settings.json"
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "Media Flow" / "settings.json"


def is_msix_package() -> bool:
    return resource_path("msix-package.txt").exists()


def default_output_dir() -> Path:
    for candidate in (Path.home() / "Videos", Path.home() / "Music", Path.home() / "Pictures", Path.home() / "Downloads"):
        if candidate.exists():
            return candidate
    return Path.home()


def find_ffmpeg() -> Optional[str]:
    found = shutil.which("ffmpeg")
    if found:
        return found

    base = app_dir()
    program_files = [Path(os.environ.get("ProgramFiles", "")), Path(os.environ.get("ProgramFiles(x86)", ""))]
    candidates = [
        base / "ffmpeg.exe",
        base / "ffmpeg",
        base / "ffmpeg" / "bin" / "ffmpeg.exe",
        base / "bin" / "ffmpeg.exe",
        base / "bin" / "ffmpeg",
        Path("/opt/media-flow/ffmpeg"),
        Path.home() / "scoop" / "shims" / "ffmpeg.exe",
        Path.home() / ".local" / "bin" / "ffmpeg",
        Path("/usr/local/bin/ffmpeg"),
        Path("/usr/bin/ffmpeg"),
    ]
    for root in program_files:
        if root:
            candidates.extend(
                [
                    root / "ffmpeg" / "bin" / "ffmpeg.exe",
                    root / "Gyan" / "FFmpeg" / "bin" / "ffmpeg.exe",
                ]
            )

    winget_packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        candidates.extend(winget_packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def find_ffprobe() -> Optional[str]:
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        candidate = Path(ffmpeg).with_name("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    found = shutil.which("ffprobe")
    if found:
        return found

    base = app_dir()
    candidates = [
        base / "ffprobe.exe",
        base / "ffprobe",
        base / "ffmpeg" / "bin" / "ffprobe.exe",
        base / "bin" / "ffprobe.exe",
        base / "bin" / "ffprobe",
        Path("/opt/media-flow/ffprobe"),
        Path.home() / ".local" / "bin" / "ffprobe",
        Path("/usr/local/bin/ffprobe"),
        Path("/usr/bin/ffprobe"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def detect_gpu_encoders(ffmpeg_path: str) -> dict[str, bool]:
    encoders = {"nvenc": False, "amf": False, "qsv": False}
    try:
        process = subprocess.run(
            [ffmpeg_path, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=5,
        )
        output = process.stdout.lower()
        if "h264_nvenc" in output or "hevc_nvenc" in output:
            encoders["nvenc"] = True
        if "h264_amf" in output or "hevc_amf" in output:
            encoders["amf"] = True
        if "h264_qsv" in output or "hevc_qsv" in output:
            encoders["qsv"] = True
    except Exception:
        pass
    return encoders


def send_desktop_notification(title: str, message: str) -> None:
    if sys.platform == "win32":
        try:
            ps_code = f"""
            [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = '{title}'
            $notification.BalloonTipText = '{message}'
            $notification.Visible = $True
            $notification.ShowBalloonTip(5000)
            Start-Sleep -s 6
            $notification.Dispose()
            """
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_code],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            subprocess.Popen(["notify-send", "-a", "Media Flow", title, message])
        except Exception:
            pass


send_windows_toast = send_desktop_notification


def detect_cloud_folders() -> dict[str, Path]:
    folders: dict[str, Path] = {}
    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(env_name)
        if value and Path(value).exists():
            folders.setdefault("OneDrive", Path(value))

    google_candidates = [
        Path.home() / "Google Drive",
        Path.home() / "My Drive",
        Path.home() / "GoogleDrive",
        Path("G:/My Drive"),
        Path("G:/Mi unidad"),
    ]
    for candidate in google_candidates:
        if candidate.exists():
            folders.setdefault("Google Drive", candidate)

    icloud_candidates = [
        Path.home() / "iCloudDrive",
        Path.home() / "iCloud Drive",
        Path.home() / "iCloudDrive" / "Documents",
    ]
    for candidate in icloud_candidates:
        if candidate.exists():
            folders.setdefault("iCloud Drive", candidate)

    # Cloud folders comunes en Linux
    linux_candidates = {
        "Nextcloud": Path.home() / "Nextcloud",
        "ownCloud": Path.home() / "ownCloud",
        "Dropbox": Path.home() / "Dropbox",
        "Google Drive": Path.home() / "GoogleDrive",
        "Mega": Path.home() / "MEGAsync",
    }
    for name, p in linux_candidates.items():
        if p.exists():
            folders.setdefault(name, p)

    return folders


def version_tuple(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("vV")
    parts = []
    for part in cleaned.split("."):
        number = ""
        for char in part:
            if not char.isdigit():
                break
            number += char
        parts.append(int(number or "0"))
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = version_tuple(latest)
    current_parts = version_tuple(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    current_parts += (0,) * (length - len(current_parts))
    return latest_parts > current_parts


def fetch_latest_release() -> dict[str, Any]:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"media-flow/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def find_windows_installer_asset(release: dict[str, Any]) -> tuple[str, str]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("La release no incluye archivos descargables.")

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        download_url = str(asset.get("browser_download_url") or "")
        lower_name = name.lower()
        if lower_name.endswith(".exe") and "setup" in lower_name and download_url:
            return name, download_url

    raise ValueError("No se encontró el instalador de Windows en la release.")


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"media-flow/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def apply_window_corner_preference(window: ctk.CTk) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preference), ctypes.sizeof(preference))
    except (AttributeError, OSError, Exception):
        pass


def launch_installer_after_exit(installer_path: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("La instalación automática solo está disponible en Windows.")

    updater_dir = Path(tempfile.gettempdir()) / "media-flow-updates"
    updater_dir.mkdir(parents=True, exist_ok=True)
    script_path = updater_dir / "run-update.cmd"
    log_path = updater_dir / "update.log"
    app_exe = Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(sys.argv[0]).resolve()
    script_path.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                f'set "INSTALLER={installer_path}"',
                f'set "APP_EXE={app_exe}"',
                f'set "LOG={log_path}"',
                'echo [%date% %time%] Waiting for Media Flow to close>"%LOG%"',
                ":waitloop",
                f'tasklist /FI "PID eq {os.getpid()}" 2>NUL | find "{os.getpid()}" >NUL',
                "if not errorlevel 1 (",
                "  timeout /t 1 /nobreak >NUL",
                "  goto waitloop",
                ")",
                'echo [%date% %time%] Starting installer>>"%LOG%"',
                'start "" /wait "%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS',
                'set "RESULT=%ERRORLEVEL%"',
                'echo [%date% %time%] Installer exit code %RESULT%>>"%LOG%"',
                'if "%RESULT%"=="0" start "" "%APP_EXE%"',
                "exit /b %RESULT%",
            ]
        ),
        encoding="utf-8",
    )
    command = ["cmd.exe", "/c", "start", "", "/min", str(script_path)]
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned or "archivo"


def unique_output_path(output_dir: Path, stem: str, extension: str) -> Path:
    base = output_dir / f"{safe_filename(stem)}.{extension}"
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = output_dir / f"{safe_filename(stem)} ({index}).{extension}"
        if not candidate.exists():
            return candidate
    raise FileExistsError("No se pudo crear un nombre de salida único.")


def format_duration(seconds: Any) -> str:
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_duration_to_seconds(time_str: str) -> Optional[float]:
    time_str = time_str.strip()
    if not time_str:
        return None
    try:
        parts = list(map(float, time_str.split(":")))
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        pass
    return None


def format_size(bytes_value: Any) -> str:
    try:
        size = float(bytes_value)
    except (TypeError, ValueError):
        return ""
    units = ("B", "KB", "MB", "GB")
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} {units[index]}"
    return f"{size:.1f} {units[index]}"


# ==========================================
# GESTOR DE LICENCIA / COMPLEMENTO PRO
# ==========================================
class LicenseManager:
    """Gestiona el estado del complemento PRO, verificación de claves y permisos."""

    def __init__(self, initial_data: dict[str, Any]) -> None:
        self.pro_key: str = str(initial_data.get("pro_license_key", "")).strip()
        self._is_pro: bool = bool(initial_data.get("is_pro", False)) and self.pro_key != "MICROSOFT-STORE"
        if self.pro_key and self.validate_key(self.pro_key):
            self._is_pro = True

    @property
    def is_pro(self) -> bool:
        return self._is_pro

    def validate_key(self, key: str) -> bool:
        cleaned = key.strip().upper()
        if not cleaned:
            return False
        if cleaned in ("MFPRO-VIP-2026-PLUS", "MFPRO-PREMIUM-LIFETIME"):
            return True
        pattern = r"^MFPRO-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return bool(re.match(pattern, cleaned))

    def activate(self, key: str) -> tuple[bool, str]:
        cleaned = key.strip().upper()
        if self.validate_key(cleaned):
            self._is_pro = True
            self.pro_key = cleaned
            return True, "¡Complemento PRO activado con éxito! Todas las funciones prémium están desbloqueadas."
        return False, "La clave introducida no es válida. Formato esperado: MFPRO-XXXX-XXXX-XXXX"

    def activate_store_purchase(self) -> None:
        self._is_pro = True
        self.pro_key = "MICROSOFT-STORE"

    def deactivate(self) -> None:
        self._is_pro = False
        self.pro_key = ""


# ==========================================
# DIÁLOGO MODAL: COMPLEMENTO PRO (WINUI 3 STYLE)
# ==========================================
class ProUpgradeModal(ctk.CTkToplevel):
    def __init__(self, parent: "MediaConverterApp") -> None:
        super().__init__(parent)
        self.parent_app = parent
        self.title("Media Flow PRO - Complemento Prémium")
        self.geometry("640x700")
        self.minsize(580, 620)
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, corner_radius=14, fg_color=COLOR_BG)
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)

        header_card = ctk.CTkFrame(container, corner_radius=12, fg_color=("#0067c0", "#0078d4"))
        header_card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 14))
        header_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_card,
            text="✨ Media Flow PRO Complement",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, pady=(16, 4))

        ctk.CTkLabel(
            header_card,
            text="Desbloquea el poder total de tu hardware sin límites.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#e0e7ff",
        ).grid(row=1, column=0, pady=(0, 16))

        status_frame = ctk.CTkFrame(container, corner_radius=10, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        status_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 14))
        status_frame.grid_columnconfigure(1, weight=1)

        is_pro = self.parent_app.license_manager.is_pro
        badge_text = "⭐ COMPLEMENTO PRO ACTIVO" if is_pro else "🆓 VERSIÓN GRATUITA (BÁSICA)"
        badge_color = ("#10b981", "#059669") if is_pro else ("#64748b", "#475569")

        ctk.CTkLabel(
            status_frame,
            text="Estado de la licencia:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        ctk.CTkLabel(
            status_frame,
            text=badge_text,
            corner_radius=8,
            fg_color=badge_color,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=10,
            pady=4,
        ).grid(row=0, column=1, padx=14, pady=12, sticky="e")

        features_frame = ctk.CTkFrame(container, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        features_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 14))
        features_frame.grid_columnconfigure(0, weight=3)
        features_frame.grid_columnconfigure(1, weight=1)
        features_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(features_frame, text="Característica", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="w").grid(
            row=0, column=0, padx=14, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(features_frame, text="Gratis", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="gray60").grid(
            row=0, column=1, padx=6, pady=(12, 6)
        )
        ctk.CTkLabel(features_frame, text="PRO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_ACCENT).grid(
            row=0, column=2, padx=10, pady=(12, 6)
        )

        features = [
            ("🚀 Aceleración Hardware GPU (NVENC/AMF)", "❌ Solo CPU", "✔ Ultra Rápida"),
            ("⚡ Conversión Paralela por Lotes", "1 Archivo", "✔ Hasta 8 hilos"),
            ("🎬 Calidad 4K (2160p) y 60 FPS", "Máx 1080p", "✔ 4K / 60 FPS"),
            ("🎧 Codecs Lossless (FLAC, ALAC, AIFF, AV1)", "Básicos", "✔ Todos"),
            ("✂️ Recorte milimétrico y Compresión MB", "❌", "✔ Ilimitado"),
            ("🔗 Unir/Concatenar pistas y Extracción SRT", "❌", "✔ Incluido"),
            ("☁️ Sincronización automática con Nube", "❌ Manual", "✔ Auto-Sync"),
            ("🔔 Notificaciones Nativas en Segundo Plano", "✔", "✔"),
        ]

        for idx, (title, free_val, pro_val) in enumerate(features, start=1):
            ctk.CTkLabel(features_frame, text=title, font=ctk.CTkFont(family="Segoe UI", size=11), anchor="w").grid(
                row=idx, column=0, padx=14, pady=4, sticky="w"
            )
            ctk.CTkLabel(features_frame, text=free_val, font=ctk.CTkFont(family="Segoe UI", size=11), text_color="gray50").grid(
                row=idx, column=1, padx=6, pady=4
            )
            ctk.CTkLabel(
                features_frame,
                text=pro_val,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=("#10b981", "#34d399") if "✔" in pro_val else ("#1b1b1b", "#ffffff"),
            ).grid(row=idx, column=2, padx=10, pady=4)

        act_card = ctk.CTkFrame(container, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        act_card.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 14))
        act_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            act_card,
            text="🔑 Activar con Clave de Licencia",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        key_row = ctk.CTkFrame(act_card, fg_color="transparent")
        key_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        key_row.grid_columnconfigure(0, weight=1)

        self.key_entry = ctk.CTkEntry(
            key_row,
            placeholder_text="MFPRO-XXXX-XXXX-XXXX",
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        if self.parent_app.license_manager.pro_key:
            self.key_entry.insert(0, self.parent_app.license_manager.pro_key)

        ctk.CTkButton(
            key_row,
            text="Activar",
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_activate_clicked,
            width=90,
        ).grid(row=0, column=1)

        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 6))
        btn_box.grid_columnconfigure(0, weight=1)

        if is_pro:
            ctk.CTkButton(
                btn_box,
                text="Desactivar PRO (Modo Gratis)",
                corner_radius=10,
                fg_color=("#ef4444", "#dc2626"),
                hover_color=("#dc2626", "#b91c1c"),
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=self._on_deactivate_clicked,
                height=38,
            ).grid(row=0, column=0, sticky="ew")
        else:
            ctk.CTkButton(
                btn_box,
                text="💳 Comprar con Stripe",
                corner_radius=10,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=self._on_buy_stripe_clicked,
                height=38,
            ).grid(row=0, column=0, sticky="ew")

            store_box = ctk.CTkFrame(container, fg_color="transparent")
            store_box.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))
            store_box.grid_columnconfigure(0, weight=1)

            ctk.CTkButton(
                store_box,
                text="🛍️ Comprar en Microsoft Store",
                corner_radius=10,
                fg_color=("gray75", "#2c2c2c"),
                hover_color=("gray65", "#3a3a3a"),
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=self._on_buy_store_clicked,
                height=34,
            ).grid(row=0, column=0, sticky="ew")

    def _on_activate_clicked(self) -> None:
        key = self.key_entry.get().strip()
        success, message = self.parent_app.license_manager.activate(key)
        if success:
            self.parent_app.on_license_updated()
            messagebox.showinfo("Media Flow PRO", message, parent=self)
            self.destroy()
        else:
            messagebox.showerror("Media Flow PRO", message, parent=self)

    def _on_deactivate_clicked(self) -> None:
        self.parent_app.license_manager.deactivate()
        self.parent_app.on_license_updated()
        messagebox.showinfo("Media Flow PRO", "Se ha desactivado la licencia PRO. Has vuelto a la versión gratuita.", parent=self)
        self.destroy()

    def _on_buy_stripe_clicked(self) -> None:
        try:
            webbrowser.open(STRIPE_CHECKOUT_URL)
        except Exception:
            pass
        messagebox.showinfo(
            "Comprar con Stripe",
            f"Se ha abierto la pasarela de Stripe en tu navegador:\n{STRIPE_CHECKOUT_URL}\n\nTras completar el pago, recibirás tu clave de licencia por correo electrónico para introducirla aquí.",
            parent=self,
        )

    def _on_buy_store_clicked(self) -> None:
        try:
            purchased = self.parent_app.store_pro.purchase_pro()
        except Exception as exc:
            messagebox.showerror("Microsoft Store", f"No se pudo iniciar la compra del complemento PRO.\n\n{exc}", parent=self)
            return

        if not purchased:
            messagebox.showwarning(
                "Microsoft Store",
                "La compra no se completó. Para comprar el complemento, instala Media Flow desde Microsoft Store e inténtalo de nuevo.",
                parent=self,
            )
            return

        self.parent_app.license_manager.activate_store_purchase()
        self.parent_app.on_license_updated()
        messagebox.showinfo("Media Flow PRO", "¡Compra confirmada! El complemento PRO está activo.", parent=self)
        self.destroy()


# ==========================================
# APLICACIÓN PRINCIPAL (MICROSOFT STORE STYLE)
# ==========================================
class MediaConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Configuración visual
        self.settings = self._load_settings()
        theme_mode = self.settings.get("theme_mode", "Dark")
        ctk.set_appearance_mode(theme_mode)
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_TITLE} Suite v{APP_VERSION}")
        self.geometry("1160x840")
        self.minsize(980, 720)

        apply_window_corner_preference(self)

        # Gestor de Licencias PRO
        self.license_manager = LicenseManager(self.settings)
        self.store_pro = MicrosoftStorePro(MS_STORE_PRODUCT_ID)

        # Variables de estado
        self.mode = ctk.StringVar(value=self.settings.get("mode", "Audio"))
        self.preset = ctk.StringVar(value=self.settings.get("preset", "Personalizado"))
        self.output_dir = ctk.StringVar(value=self.settings.get("output_dir", str(default_output_dir())))
        self.output_format = ctk.StringVar(value=self.settings.get("output_format", "MP3"))
        self.audio_quality = ctk.StringVar(value=self.settings.get("audio_quality", "192 kbps"))
        self.video_quality = ctk.StringVar(value=self.settings.get("video_quality", "Equilibrada"))
        self.video_res = ctk.StringVar(value=self.settings.get("video_res", "Original"))
        self.video_fps = ctk.StringVar(value=self.settings.get("video_fps", "Original"))
        self.cloud_target = ctk.StringVar(value=self.settings.get("cloud_target", "Carpeta local"))

        self.start_trim = ctk.StringVar(value=self.settings.get("start_trim", ""))
        self.end_trim = ctk.StringVar(value=self.settings.get("end_trim", ""))
        self.target_size_mb = ctk.StringVar(value=self.settings.get("target_size_mb", ""))
        self.use_gpu = ctk.BooleanVar(value=self.settings.get("use_gpu", True))
        self.parallel_threads = ctk.IntVar(value=self.settings.get("parallel_threads", 2 if self.license_manager.is_pro else 1))
        self.enable_toast = ctk.BooleanVar(value=self.settings.get("enable_toast", True))

        self.status_text = ctk.StringVar(value="Listo. Selecciona tus archivos para comenzar.")
        self.progress_detail = ctk.StringVar(value="")
        self.media_info_text = ctk.StringVar(value="Sin archivos seleccionados.")
        self.search_text = ctk.StringVar(value="")

        self.input_files: list[Path] = []
        self.conversion_history: list[dict[str, Any]] = self.settings.get("history", [])
        self.cloud_folders = detect_cloud_folders()
        self.gpu_encoders = {"nvenc": False, "amf": False, "qsv": False}
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.busy = False
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None

        self.current_view = "Inicio"
        self.views: dict[str, ctk.CTkFrame] = {}
        self.rail_items: dict[str, dict[str, Any]] = {}

        self._load_app_icons()
        self._build_ui()
        self._detect_gpu_async()
        self._verify_store_purchase_async()
        self._poll_messages()

    # ==========================================
    # CARGA Y CACHÉ DE ICONOS VECTORIALES (LUCIDE / FLUENT)
    # ==========================================
    def _load_app_icons(self) -> None:
        self.logo_image = None
        self._icon_cache: dict[tuple[str, tuple[int, int], str], ctk.CTkImage] = {}
        self._imagetk_available = False
        try:
            _test_probe = ImageTk.PhotoImage(Image.new("RGBA", (1, 1)))
            del _test_probe
            self._imagetk_available = True
        except Exception:
            return

        icon_path = resource_path("icon-300.png")
        if icon_path.exists():
            try:
                pil_img = Image.open(icon_path)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(26, 26))
            except Exception:
                pass

    def _get_icon(self, name: str, size: tuple[int, int] = (20, 20), variant: str = "auto") -> Optional[ctk.CTkImage]:
        if not getattr(self, "_imagetk_available", True):
            return None
        cache_key = (name, size, variant)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        icons_dir = resource_path("assets/icons")
        if not icons_dir.exists():
            icons_dir = app_dir() / "assets" / "icons"

        target_file = None
        if variant == "accent":
            target_file = icons_dir / f"{name}_accent.png"
            if not target_file.exists():
                target_file = icons_dir / f"{name}_white.png"
        elif variant == "white":
            target_file = icons_dir / f"{name}_white.png"
        elif variant == "color":
            target_file = icons_dir / f"{name}_color.png"
            if not target_file.exists():
                target_file = icons_dir / f"{name}_accent.png"

        if target_file and target_file.exists():
            try:
                im = Image.open(target_file)
                img = ctk.CTkImage(light_image=im, dark_image=im, size=size)
                self._icon_cache[cache_key] = img
                return img
            except Exception:
                pass

        p_light = icons_dir / f"{name}_light.png"
        p_dark = icons_dir / f"{name}_dark.png"
        if p_light.exists() and p_dark.exists():
            try:
                im_l = Image.open(p_light)
                im_d = Image.open(p_dark)
                img = ctk.CTkImage(light_image=im_l, dark_image=im_d, size=size)
                self._icon_cache[cache_key] = img
                return img
            except Exception:
                pass

        return None

    def _verify_store_purchase_async(self) -> None:
        def worker() -> None:
            if self.store_pro.is_pro_owned():
                self.messages.put(("store_pro_owned", None))

        threading.Thread(target=worker, daemon=True).start()

    def _load_settings(self) -> dict[str, Any]:
        path = config_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_settings(self) -> None:
        path = config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "theme_mode": ctk.get_appearance_mode(),
                "mode": self.mode.get(),
                "preset": self.preset.get(),
                "output_dir": self.output_dir.get(),
                "output_format": self.output_format.get(),
                "audio_quality": self.audio_quality.get(),
                "video_quality": self.video_quality.get(),
                "video_res": self.video_res.get(),
                "video_fps": self.video_fps.get(),
                "cloud_target": self.cloud_target.get(),
                "start_trim": self.start_trim.get(),
                "end_trim": self.end_trim.get(),
                "target_size_mb": self.target_size_mb.get(),
                "use_gpu": self.use_gpu.get(),
                "parallel_threads": self.parallel_threads.get(),
                "enable_toast": self.enable_toast.get(),
                "is_pro": self.license_manager.is_pro,
                "pro_license_key": self.license_manager.pro_key,
                "history": self.conversion_history[-30:],
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def on_license_updated(self) -> None:
        self._save_settings()
        self._update_header_badges()
        self._update_format_choices()
        self._refresh_pro_ui()

    def _detect_gpu_async(self) -> None:
        def worker() -> None:
            ffmpeg = find_ffmpeg()
            if ffmpeg:
                res = detect_gpu_encoders(ffmpeg)
                self.messages.put(("gpu_detected", res))

        threading.Thread(target=worker, daemon=True).start()

    # ==========================================
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ==========================================
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)  # Nav rail
        self.grid_columnconfigure(1, weight=1)  # Main canvas
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_nav_rail()
        self._build_main_views()
        self._build_bottom_action_bar()

        self._switch_view("Inicio")

    # ==========================================
    # 1. TOP HEADER (MICROSOFT STORE STYLE)
    # ==========================================
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, height=54, fg_color=COLOR_HEADER_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Izquierda: Logo + Título
        brand_box = ctk.CTkFrame(header, fg_color="transparent")
        brand_box.grid(row=0, column=0, padx=(16, 12), pady=8, sticky="w")

        if self.logo_image:
            ctk.CTkLabel(brand_box, image=self.logo_image, text="").pack(side="left", padx=(0, 8))
        else:
            zap_icon = self._get_icon("zap", (20, 20), "accent")
            ctk.CTkLabel(brand_box, image=zap_icon, text="").pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            brand_box,
            text=APP_TITLE,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 6))

        self.pro_pill = ctk.CTkLabel(
            brand_box,
            text="PRO",
            corner_radius=6,
            fg_color=("#10b981", "#059669"),
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#ffffff",
            padx=6,
            pady=2,
        )
        self.pro_pill.pack(side="left")

        # Centro: Barra de búsqueda redondeada (Estilo Microsoft Store)
        search_box = ctk.CTkFrame(header, fg_color="transparent")
        search_box.grid(row=0, column=1, padx=20, pady=8)

        search_inner = ctk.CTkFrame(
            search_box,
            corner_radius=18,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER,
            width=460,
            height=34,
        )
        search_inner.pack(fill="x")
        search_inner.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_inner,
            textvariable=self.search_text,
            placeholder_text="Buscar formatos, herramientas, preajustes...",
            border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=400,
        )
        self.search_entry.grid(row=0, column=0, padx=(14, 4), pady=2, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_query_changed)
        self.search_entry.bind("<Return>", self._on_search_enter)

        search_icon = self._get_icon("search", (16, 16))
        search_lbl = ctk.CTkLabel(search_inner, image=search_icon, text="")
        search_lbl.grid(row=0, column=1, padx=(4, 12), pady=2)

        # Derecha: Controles (GPU, Tema, Actualizaciones, Avatar Usuario)
        ctrl_box = ctk.CTkFrame(header, fg_color="transparent")
        ctrl_box.grid(row=0, column=2, padx=(8, 16), pady=8, sticky="e")

        self.gpu_badge = ctk.CTkLabel(
            ctrl_box,
            text="GPU: Buscando...",
            corner_radius=8,
            fg_color=("gray85", "#282828"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=8,
            pady=4,
        )
        self.gpu_badge.pack(side="left", padx=(0, 6))

        moon_icon = self._get_icon("sun_moon", (18, 18))
        self.theme_btn = ctk.CTkButton(
            ctrl_box,
            image=moon_icon,
            text="",
            width=32,
            height=32,
            corner_radius=16,
            fg_color=("gray85", "#282828"),
            hover_color=("gray75", "#383838"),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="left", padx=(0, 6))

        refresh_icon = self._get_icon("refresh", (16, 16))
        self.update_btn = ctk.CTkButton(
            ctrl_box,
            image=refresh_icon,
            text="",
            width=32,
            height=32,
            corner_radius=16,
            fg_color=("gray85", "#282828"),
            hover_color=("gray75", "#383838"),
            command=lambda: self._check_for_updates(False),
        )
        self.update_btn.pack(side="left", padx=(0, 8))

        # Avatar de usuario / PRO
        self.avatar_btn = ctk.CTkButton(
            ctrl_box,
            text="MF",
            width=34,
            height=34,
            corner_radius=17,
            fg_color=("#ec4899", "#db2777"),
            hover_color=("#db2777", "#be185d"),
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._open_pro_modal,
        )
        self.avatar_btn.pack(side="left")

        self._update_header_badges()

    def _update_header_badges(self) -> None:
        is_pro = self.license_manager.is_pro
        if is_pro:
            self.pro_pill.configure(text="PRO", fg_color=("#059669", "#10b981"))
            star_icon = self._get_icon("star", (16, 16), "white")
            self.avatar_btn.configure(image=star_icon, text="", fg_color=("#8b5cf6", "#7c3aed"))
        else:
            self.pro_pill.configure(text="GRATIS", fg_color=("gray60", "#475569"))
            self.avatar_btn.configure(image=None, text="MF", fg_color=("#ec4899", "#db2777"))

    # ==========================================
    # 2. LEFT NAVIGATION RAIL (WINUI 3 STYLE)
    # ==========================================
    def _build_nav_rail(self) -> None:
        rail = ctk.CTkFrame(self, corner_radius=0, width=82, fg_color=COLOR_RAIL_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        rail.grid(row=1, column=0, sticky="ns")
        rail.grid_rowconfigure(5, weight=1)

        nav_specs = [
            ("Inicio", "home", "Inicio"),
            ("Audio", "music", "Audio"),
            ("Video", "film", "Video"),
            ("Imagen", "image", "Imagen"),
            ("Herramientas", "wrench", "Herramientas"),
        ]

        for row_idx, (name, icon_key, label) in enumerate(nav_specs):
            item_frame = self._create_rail_button(rail, name, icon_key, label)
            item_frame.grid(row=row_idx, column=0, padx=4, pady=4, sticky="ew")

        bottom_specs = [
            ("Biblioteca", "history", "Biblioteca"),
            ("Ajustes", "settings", "Ajustes"),
        ]
        for row_idx, (name, icon_key, label) in enumerate(bottom_specs, start=6):
            item_frame = self._create_rail_button(rail, name, icon_key, label)
            item_frame.grid(row=row_idx, column=0, padx=4, pady=4, sticky="ew")

    def _create_rail_button(self, parent: ctk.CTkFrame, view_name: str, icon_key: str, label: str) -> ctk.CTkFrame:
        container = ctk.CTkFrame(parent, fg_color="transparent", height=60, corner_radius=8)
        container.pack_propagate(False)

        indicator = ctk.CTkFrame(container, width=3, height=32, corner_radius=2, fg_color="transparent")
        indicator.pack(side="left", padx=(2, 2))

        icon_img = self._get_icon(icon_key, (20, 20))
        btn = ctk.CTkButton(
            container,
            image=icon_img,
            text=label,
            compound="top",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="transparent",
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_CARD_HOVER,
            corner_radius=8,
            command=lambda v=view_name: self._switch_view(v),
        )
        btn.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=2)

        self.rail_items[view_name] = {
            "container": container,
            "indicator": indicator,
            "button": btn,
            "icon_key": icon_key,
            "label": label,
        }
        return container

    def _switch_view(self, view_name: str) -> None:
        self.current_view = view_name

        for name, data in self.rail_items.items():
            icon_key = data["icon_key"]
            if name == view_name:
                data["indicator"].configure(fg_color=COLOR_ACCENT)
                active_icon = self._get_icon(icon_key, (20, 20), "accent")
                data["button"].configure(
                    image=active_icon,
                    fg_color=COLOR_CARD_BG,
                    text_color=COLOR_TEXT_PRIMARY,
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                )
            else:
                data["indicator"].configure(fg_color="transparent")
                normal_icon = self._get_icon(icon_key, (20, 20))
                data["button"].configure(
                    image=normal_icon,
                    fg_color="transparent",
                    text_color=COLOR_TEXT_SECONDARY,
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                )

        for name, frame in self.views.items():
            if name == view_name:
                frame.grid(row=1, column=1, sticky="nsew")
            else:
                frame.grid_remove()

        if view_name in ("Audio", "Video", "Imagen"):
            self.mode.set(view_name)
            self._update_format_choices()
        elif view_name == "Herramientas":
            if self.mode.get() not in ("Extracción", "Unir (Concat)"):
                self.mode.set("Extracción")
            self._update_format_choices()

        self._update_convert_button_text()

    # ==========================================
    # 3. CONSTRUCCIÓN DE LAS VISTAS PRINCIPALES
    # ==========================================
    def _build_main_views(self) -> None:
        self._build_view_home()
        self._build_view_audio()
        self._build_view_video()
        self._build_view_image()
        self._build_view_tools()
        self._build_view_library()
        self._build_view_settings()

    # ------------------------------------------
    # VISTA 1: INICIO (EXPERIENCIA STORE EXACTA)
    # ------------------------------------------
    def _build_view_home(self) -> None:
        home_scroll = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Inicio"] = home_scroll
        home_scroll.grid_columnconfigure(0, weight=1)

        # --- A. HERO SHOWCASE CAROUSEL ---
        hero_container = ctk.CTkFrame(home_scroll, fg_color="transparent")
        hero_container.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        hero_container.grid_columnconfigure(0, weight=3)
        hero_container.grid_columnconfigure(1, weight=2)

        # 1. Gran Banner Hero Izquierdo
        hero_card = ctk.CTkFrame(
            hero_container,
            corner_radius=14,
            fg_color=("#111827", "#111827"),
            border_width=1,
            border_color=("#1f2937", "#1f2937"),
            height=280,
        )
        hero_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        hero_card.grid_columnconfigure(0, weight=1)
        hero_card.grid_rowconfigure(3, weight=1)

        badge_row = ctk.CTkFrame(hero_card, fg_color="transparent")
        badge_row.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        zap_mini = self._get_icon("zap", (13, 13), "white")
        ctk.CTkLabel(
            badge_row,
            image=zap_mini,
            text=" GPU ACELERADA",
            compound="left",
            corner_radius=6,
            fg_color=("#f59e0b", "#d97706"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#ffffff",
            padx=8,
            pady=3,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            badge_row,
            text=f"v{APP_VERSION} PRO EDITION",
            corner_radius=6,
            fg_color=("#1f2937", "#374151"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#9ca3af",
            padx=8,
            pady=3,
        ).pack(side="left")

        ctk.CTkLabel(
            hero_card,
            text="Media Flow Suite",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#ffffff",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 4))

        ctk.CTkLabel(
            hero_card,
            text="Transcodifica video, audio e imágenes a máxima velocidad.\nOptimizado para streaming, redes sociales y edición local sin pérdidas.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#9ca3af",
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 16))

        hero_actions = ctk.CTkFrame(hero_card, fg_color="transparent")
        hero_actions.grid(row=3, column=0, sticky="sw", padx=20, pady=(0, 20))

        plus_icon = self._get_icon("plus", (15, 15), "white")
        ctk.CTkButton(
            hero_actions,
            image=plus_icon,
            text=" Agregar Archivos",
            compound="left",
            corner_radius=18,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._choose_input_file,
            height=36,
        ).pack(side="left", padx=(0, 10))

        zap_btn_icon = self._get_icon("zap", (14, 14), "white")
        ctk.CTkButton(
            hero_actions,
            image=zap_btn_icon,
            text=" Convertir Ahora",
            compound="left",
            corner_radius=18,
            fg_color=("gray25", "#1f2937"),
            hover_color=("gray35", "#374151"),
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._start_conversion,
            height=36,
        ).pack(side="left")

        carousel_dots = ctk.CTkLabel(hero_card, text="●  ●  ○  ○  ○", font=ctk.CTkFont(size=9), text_color="#6b7280")
        carousel_dots.grid(row=4, column=0, sticky="s", pady=(0, 8))

        # 2. Bloque Derecho de Tarjetas Showcase
        side_container = ctk.CTkFrame(hero_container, fg_color="transparent")
        side_container.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        side_container.grid_columnconfigure(0, weight=1)
        side_container.grid_columnconfigure(1, weight=1)
        side_container.grid_rowconfigure(0, weight=1)
        side_container.grid_rowconfigure(1, weight=1)

        # Tarjeta Verde Spotify
        spotify_card = ctk.CTkFrame(
            side_container,
            corner_radius=14,
            fg_color=("#0a5c36", "#064e2e"),
            border_width=1,
            border_color=("#107c41", "#107c41"),
        )
        spotify_card.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        spotify_card.grid_columnconfigure(0, weight=1)

        music_head_icon = self._get_icon("music", (20, 20), "white")
        ctk.CTkLabel(
            spotify_card,
            image=music_head_icon,
            text=" Spotify & Hi-Fi Audio",
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            spotify_card,
            text="FLAC Lossless, MP3 320k y AAC con máxima calidad sonora.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#a7f3d0",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        ctk.CTkButton(
            spotify_card,
            text="Explorar Audio",
            corner_radius=14,
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=28,
            command=lambda: self._switch_view("Audio"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 16))

        # Tarjeta Inferior Izquierda (Video 4K)
        card_v4k = ctk.CTkFrame(
            side_container,
            corner_radius=14,
            fg_color=("#1e293b", "#1e293b"),
            border_width=1,
            border_color=("#334155", "#334155"),
        )
        card_v4k.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        film_head_icon = self._get_icon("film", (16, 16), "white")
        ctk.CTkLabel(
            card_v4k,
            image=film_head_icon,
            text=" 4K / 60 FPS",
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#ffffff",
        ).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(card_v4k, text="H.265, AV1, MP4", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#94a3b8").pack(
            anchor="w", padx=12, pady=(0, 8)
        )
        ctk.CTkButton(
            card_v4k,
            text="Video PRO",
            corner_radius=12,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            height=24,
            command=lambda: self._switch_view("Video"),
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # Tarjeta Inferior Derecha (Herramientas & Trim)
        card_trim = ctk.CTkFrame(
            side_container,
            corner_radius=14,
            fg_color=("#1e293b", "#1e293b"),
            border_width=1,
            border_color=("#334155", "#334155"),
        )
        card_trim.grid(row=1, column=1, sticky="nsew", padx=(4, 0))
        scissors_icon = self._get_icon("scissors", (16, 16), "white")
        ctk.CTkLabel(
            card_trim,
            image=scissors_icon,
            text=" Trim & MB",
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#ffffff",
        ).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(card_trim, text="Recorte y Reducción", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#94a3b8").pack(
            anchor="w", padx=12, pady=(0, 8)
        )
        ctk.CTkButton(
            card_trim,
            text="Herramientas",
            corner_radius=12,
            fg_color=("#f59e0b", "#d97706"),
            hover_color=("#d97706", "#b45309"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            height=24,
            command=lambda: self._switch_view("Herramientas"),
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # --- B. SECCIÓN 1: TENDENCIAS Y MODOS ---
        sec1_header = ctk.CTkFrame(home_scroll, fg_color="transparent")
        sec1_header.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 6))
        sec1_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sec1_header,
            text="Tendencias de conversión  ›",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        arrows1 = ctk.CTkFrame(sec1_header, fg_color="transparent")
        arrows1.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(arrows1, text="‹", width=28, height=28, corner_radius=14, fg_color=COLOR_CARD_BG, text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=2)
        ctk.CTkButton(arrows1, text="›", width=28, height=28, corner_radius=14, fg_color=COLOR_CARD_BG, text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=2)

        modes_grid = ctk.CTkFrame(home_scroll, fg_color="transparent")
        modes_grid.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        for col_idx in range(4):
            modes_grid.grid_columnconfigure(col_idx, weight=1)

        modes_data = [
            ("Audio Hi-Fi", "MP3, WAV, FLAC, M4A, OGG", "Audio", "music"),
            ("Video Ultra HD", "MP4, MOV, MKV, AV1, 4K", "Video", "film"),
            ("Imágenes", "PNG, JPG, WEBP, AVIF, ICO", "Imagen", "image"),
            ("Herramientas", "Extraer audio, unir y recortar", "Herramientas", "wrench"),
        ]

        for idx, (title, desc, target_view, icon_key) in enumerate(modes_data):
            mcard = ctk.CTkFrame(modes_grid, corner_radius=10, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
            mcard.grid(row=0, column=idx, sticky="nsew", padx=4, pady=4)
            mcard.grid_columnconfigure(0, weight=1)

            top_row = ctk.CTkFrame(mcard, fg_color="transparent")
            top_row.pack(fill="x", padx=12, pady=(12, 6))

            mode_icon = self._get_icon(icon_key, (18, 18), "color")
            ctk.CTkLabel(top_row, image=mode_icon, text=f" {title}", compound="left", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")

            ctk.CTkLabel(mcard, text=desc, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_SECONDARY, justify="left").pack(
                anchor="w", padx=12, pady=(0, 10)
            )

            ctk.CTkButton(
                mcard,
                text="Abrir",
                corner_radius=8,
                fg_color=("gray85", "#333333"),
                hover_color=COLOR_ACCENT,
                text_color=COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=26,
                command=lambda v=target_view: self._switch_view(v),
            ).pack(fill="x", padx=12, pady=(0, 12))

        # --- C. SECCIÓN 2: ARCHIVOS EN COLA ---
        sec2_header = ctk.CTkFrame(home_scroll, fg_color="transparent")
        sec2_header.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 6))
        sec2_header.grid_columnconfigure(0, weight=1)

        self.home_queue_title = ctk.CTkLabel(
            sec2_header,
            text="Archivos en Cola (0)  ›",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.home_queue_title.grid(row=0, column=0, sticky="w")

        queue_btn_box = ctk.CTkFrame(sec2_header, fg_color="transparent")
        queue_btn_box.grid(row=0, column=1, sticky="e")

        plus_sm = self._get_icon("plus", (14, 14), "white")
        ctk.CTkButton(
            queue_btn_box,
            image=plus_sm,
            text=" Agregar Archivos",
            compound="left",
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._choose_input_file,
            height=28,
        ).pack(side="left", padx=(0, 6))

        trash_sm = self._get_icon("trash", (14, 14))
        ctk.CTkButton(
            queue_btn_box,
            image=trash_sm,
            text=" Limpiar",
            compound="left",
            corner_radius=8,
            fg_color=("gray80", "#333333"),
            hover_color=("gray70", "#444444"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._clear_files,
            height=28,
        ).pack(side="left")

        self.home_files_container = ctk.CTkFrame(home_scroll, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        self.home_files_container.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.home_files_container.grid_columnconfigure(0, weight=1)

        self.home_meta_frame = ctk.CTkFrame(home_scroll, corner_radius=8, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        self.home_meta_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.home_meta_frame.grid_columnconfigure(0, weight=1)

        self.home_info_lbl = ctk.CTkLabel(
            self.home_meta_frame,
            textvariable=self.media_info_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self.home_info_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="w")

        # --- D. SECCIÓN 3: AJUSTES RÁPIDOS DE SALIDA ---
        sec3_header = ctk.CTkFrame(home_scroll, fg_color="transparent")
        sec3_header.grid(row=6, column=0, sticky="ew", padx=16, pady=(6, 6))
        ctk.CTkLabel(sec3_header, text="Ajustes de Conversión Rápidos  ›", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")).pack(anchor="w")

        quick_settings_card = ctk.CTkFrame(home_scroll, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        quick_settings_card.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 20))
        for col_idx in range(3):
            quick_settings_card.grid_columnconfigure(col_idx, weight=1)

        ctk.CTkLabel(quick_settings_card, text="Perfil / Preajuste", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 2)
        )
        self.home_preset_menu = ctk.CTkOptionMenu(
            quick_settings_card,
            variable=self.preset,
            values=list(PRESETS.keys()),
            corner_radius=8,
            command=self._on_preset_selected,
        )
        self.home_preset_menu.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkLabel(quick_settings_card, text="Formato de Salida", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=14, pady=(12, 2)
        )
        self.home_format_menu = ctk.CTkOptionMenu(
            quick_settings_card,
            variable=self.output_format,
            values=AUDIO_FORMATS,
            corner_radius=8,
            command=lambda _: self._update_convert_button_text(),
        )
        self.home_format_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkLabel(quick_settings_card, text="Calidad / Bitrate", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=2, sticky="w", padx=14, pady=(12, 2)
        )
        self.home_quality_menu = ctk.CTkOptionMenu(
            quick_settings_card,
            variable=self.audio_quality,
            values=["128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"],
            corner_radius=8,
        )
        self.home_quality_menu.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 14))

        self._refresh_file_list()

    # ------------------------------------------
    # VISTA 2: AUDIO (CONVERSOR DE AUDIO HI-FI)
    # ------------------------------------------
    def _build_view_audio(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Audio"] = view
        view.grid_columnconfigure(0, weight=1)

        music_big = self._get_icon("music", (24, 24), "color")
        ctk.CTkLabel(view, image=music_big, text=" Convertidor de Audio Hi-Fi", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 2)
        )
        ctk.CTkLabel(
            view,
            text="Formatos de alta calidad con codificación optimizada para reproducción en cualquier dispositivo.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        fmt_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        fmt_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))
        fmt_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(fmt_card, text="Formatos de Audio Disponibles", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )

        btn_row = ctk.CTkFrame(fmt_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        for fmt in AUDIO_FORMATS:
            is_p = fmt in AUDIO_FORMATS_PRO
            tag = f"{fmt} (PRO)" if is_p else fmt
            ctk.CTkButton(
                btn_row,
                text=tag,
                corner_radius=8,
                fg_color=("#3b82f6", "#2563eb") if not is_p else ("#8b5cf6", "#7c3aed"),
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=32,
                command=lambda f=tag: self._select_format_direct(f),
            ).pack(side="left", padx=4, pady=4)

        opt_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        opt_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        opt_card.grid_columnconfigure(0, weight=1)
        opt_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(opt_card, text="Bitrate de Calidad:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        self.audio_quality_menu = ctk.CTkOptionMenu(
            opt_card,
            variable=self.audio_quality,
            values=["128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"],
            corner_radius=8,
        )
        self.audio_quality_menu.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkLabel(opt_card, text="Directorio de Salida:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=16, pady=(14, 4)
        )
        dest_box = ctk.CTkFrame(opt_card, fg_color="transparent")
        dest_box.grid(row=1, column=1, sticky="ew", padx=16, pady=(0, 14))
        dest_box.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(dest_box, textvariable=self.output_dir, corner_radius=8).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        folder_icon = self._get_icon("folder", (16, 16))
        ctk.CTkButton(dest_box, image=folder_icon, text="", width=36, corner_radius=8, command=self._choose_folder).grid(row=0, column=1)

    # ------------------------------------------
    # VISTA 3: VIDEO (TRANSCODIFICADOR ULTRA HD)
    # ------------------------------------------
    def _build_view_video(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Video"] = view
        view.grid_columnconfigure(0, weight=1)

        film_big = self._get_icon("film", (24, 24), "color")
        ctk.CTkLabel(view, image=film_big, text=" Transcodificador de Video Ultra HD", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 2)
        )
        ctk.CTkLabel(
            view,
            text="Conversión acelerada por hardware (NVIDIA NVENC, AMD AMF, Intel QSV) hasta resolución 4K y 60 FPS.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        fmt_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        fmt_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))

        ctk.CTkLabel(fmt_card, text="Formatos de Video", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )
        btn_row = ctk.CTkFrame(fmt_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        for fmt in VIDEO_FORMATS:
            is_p = fmt in VIDEO_FORMATS_PRO
            tag = f"{fmt} (PRO)" if is_p else fmt
            ctk.CTkButton(
                btn_row,
                text=tag,
                corner_radius=8,
                fg_color=("#8b5cf6", "#7c3aed") if is_p else ("#3b82f6", "#2563eb"),
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=32,
                command=lambda f=tag: self._select_format_direct(f),
            ).pack(side="left", padx=4, pady=4)

        vopts_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        vopts_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        for i in range(3):
            vopts_card.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(vopts_card, text="Resolución:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 2)
        )
        ctk.CTkOptionMenu(
            vopts_card,
            variable=self.video_res,
            values=["Original", "1080p", "720p", "480p", "4K (2160p) (PRO)"],
            corner_radius=8,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        ctk.CTkLabel(vopts_card, text="Framerate (FPS):", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=16, pady=(12, 2)
        )
        ctk.CTkOptionMenu(
            vopts_card,
            variable=self.video_fps,
            values=["Original", "30 fps", "24 fps", "60 fps (PRO)"],
            corner_radius=8,
        ).grid(row=1, column=1, sticky="ew", padx=16, pady=(0, 12))

        ctk.CTkLabel(vopts_card, text="Calidad de Codificación:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).grid(
            row=0, column=2, sticky="w", padx=16, pady=(12, 2)
        )
        ctk.CTkOptionMenu(
            vopts_card,
            variable=self.video_quality,
            values=["Alta", "Equilibrada", "Comprimida"],
            corner_radius=8,
        ).grid(row=1, column=2, sticky="ew", padx=16, pady=(0, 12))

        vpro_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        vpro_card.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 14))
        vpro_card.grid_columnconfigure(0, weight=1)
        vpro_card.grid_columnconfigure(1, weight=1)

        ctk.CTkSwitch(
            vpro_card,
            text="Usar Aceleración Hardware GPU (NVENC/AMF) [PRO]",
            variable=self.use_gpu,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkLabel(vpro_card, text="Recorte Inicio (hh:mm:ss):", font=ctk.CTkFont(family="Segoe UI", size=11)).grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 2)
        )
        ctk.CTkEntry(vpro_card, textvariable=self.start_trim, placeholder_text="00:00:00", corner_radius=8).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 10)
        )

        ctk.CTkLabel(vpro_card, text="Recorte Fin (hh:mm:ss):", font=ctk.CTkFont(family="Segoe UI", size=11)).grid(
            row=1, column=1, sticky="w", padx=16, pady=(0, 2)
        )
        ctk.CTkEntry(vpro_card, textvariable=self.end_trim, placeholder_text="00:01:30", corner_radius=8).grid(
            row=2, column=1, sticky="ew", padx=16, pady=(0, 10)
        )

        ctk.CTkLabel(vpro_card, text="Compresión a Tamaño Objetivo (MB) [PRO]:", font=ctk.CTkFont(family="Segoe UI", size=11)).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 2)
        )
        ctk.CTkEntry(vpro_card, textvariable=self.target_size_mb, placeholder_text="Ejemplo: 25 para Discord", corner_radius=8).grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14)
        )

    # ------------------------------------------
    # VISTA 4: IMAGEN (OPTIMIZADOR DE IMÁGENES)
    # ------------------------------------------
    def _build_view_image(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Imagen"] = view
        view.grid_columnconfigure(0, weight=1)

        img_big = self._get_icon("image", (24, 24), "color")
        ctk.CTkLabel(view, image=img_big, text=" Optimizador de Imágenes", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 2)
        )
        ctk.CTkLabel(
            view,
            text="Convierte y comprime imágenes a formatos modernos para la web como AVIF y WebP sin pérdida apreciable de nitidez.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        fmt_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        fmt_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))

        ctk.CTkLabel(fmt_card, text="Formatos de Imagen", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )
        btn_row = ctk.CTkFrame(fmt_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        for fmt in IMAGE_FORMATS:
            ctk.CTkButton(
                btn_row,
                text=fmt,
                corner_radius=8,
                fg_color=("#10b981", "#059669"),
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=32,
                command=lambda f=fmt: self._select_format_direct(f),
            ).pack(side="left", padx=4, pady=4)

        opt_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        opt_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        opt_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(opt_card, text="Calidad de Salida:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 4)
        )
        ctk.CTkOptionMenu(
            opt_card,
            variable=self.audio_quality,
            values=["100%", "90%", "80%", "70%"],
            corner_radius=8,
        ).pack(anchor="w", padx=16, pady=(0, 14))

    # ------------------------------------------
    # VISTA 5: HERRAMIENTAS (TRIM, EXTRACCIÓN, CONCAT)
    # ------------------------------------------
    def _build_view_tools(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Herramientas"] = view
        view.grid_columnconfigure(0, weight=1)

        wrench_big = self._get_icon("wrench", (24, 24), "color")
        ctk.CTkLabel(view, image=wrench_big, text=" Herramientas Especiales de Procesado", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 2)
        )
        ctk.CTkLabel(
            view,
            text="Funciones avanzadas para extraer pistas, unir clips y manipular medios con precisión milimétrica.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        tools_data = [
            ("Extraer Audio", "Separa el flujo sonoro de cualquier video y guárdalo en formato MP3 puro.", "Extracción", "music"),
            ("Silenciar Video (Quitar Audio)", "Elimina todas las pistas de audio de un video al instante sin recodificar imagen.", "Extracción", "volume_x"),
            ("Extraer Subtítulos (SRT)", "Extrae pistas de subtítulos incrustadas en tus películas o series a archivo .srt.", "Extracción", "subtitles"),
            ("Unir Archivos de Audio", "Concatena múltiples clips de audio en una sola pista continua sin saltos.", "Unir (Concat)", "layers"),
            ("Unir Archivos de Video", "Une secuencias y videos compatibles en una sola película continua.", "Unir (Concat)", "film"),
        ]

        for idx, (title, desc, m_val, icon_key) in enumerate(tools_data, start=2):
            card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
            card.grid(row=idx, column=0, sticky="ew", padx=20, pady=4)
            card.grid_columnconfigure(0, weight=1)

            t_icon = self._get_icon(icon_key, (18, 18), "accent")
            ctk.CTkLabel(card, image=t_icon, text=f" {title}", compound="left", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 2))
            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(0, 8))

            ctk.CTkButton(
                card,
                text="Seleccionar Esta Herramienta",
                corner_radius=8,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=28,
                command=lambda t=title, m=m_val: self._select_tool_direct(t, m),
            ).pack(anchor="w", padx=16, pady=(0, 12))

    # ------------------------------------------
    # VISTA 6: BIBLIOTECA (HISTORIAL DE CONVERSIONES)
    # ------------------------------------------
    def _build_view_library(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Biblioteca"] = view
        view.grid_columnconfigure(0, weight=1)

        head_box = ctk.CTkFrame(view, fg_color="transparent")
        head_box.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        head_box.grid_columnconfigure(0, weight=1)

        hist_big = self._get_icon("history", (24, 24), "color")
        ctk.CTkLabel(head_box, image=hist_big, text=" Biblioteca de Medios Convertidos", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        trash_icon = self._get_icon("trash", (14, 14))
        ctk.CTkButton(
            head_box,
            image=trash_icon,
            text=" Limpiar Historial",
            compound="left",
            corner_radius=8,
            fg_color=("gray75", "#333333"),
            hover_color=("gray65", "#444444"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._clear_history,
            height=28,
        ).grid(row=0, column=1, sticky="e")

        self.library_scroll = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        self.library_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.library_scroll.grid_columnconfigure(0, weight=1)

        self._refresh_history_list()

    # ------------------------------------------
    # VISTA 7: AJUSTES & PRO
    # ------------------------------------------
    def _build_view_settings(self) -> None:
        view = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.views["Ajustes"] = view
        view.grid_columnconfigure(0, weight=1)

        settings_big = self._get_icon("settings", (24, 24), "color")
        ctk.CTkLabel(view, image=settings_big, text=" Configuración del Sistema y Licencia", compound="left", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 14)
        )

        # 1. Licencia PRO Card
        self.settings_pro_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        self.settings_pro_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))
        self.settings_pro_card.grid_columnconfigure(1, weight=1)

        star_icon = self._get_icon("star", (18, 18), "accent")
        ctk.CTkLabel(
            self.settings_pro_card,
            image=star_icon,
            text=" Complemento Media Flow PRO",
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self.settings_pro_badge = ctk.CTkLabel(
            self.settings_pro_card,
            text="COMPLEMENTO ACTIVO",
            corner_radius=8,
            fg_color=("#10b981", "#059669"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#ffffff",
            padx=10,
            pady=4,
        )
        self.settings_pro_badge.grid(row=0, column=1, padx=16, pady=12, sticky="e")

        ctk.CTkButton(
            self.settings_pro_card,
            text="Administrar Licencia / Adquirir PRO",
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._open_pro_modal,
        ).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 14), sticky="ew")

        # 2. Rendimiento & Hardware
        perf_card = ctk.CTkFrame(view, corner_radius=12, fg_color=COLOR_CARD_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        perf_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))
        perf_card.grid_columnconfigure(0, weight=1)

        zap_perf = self._get_icon("zap", (18, 18), "accent")
        ctk.CTkLabel(perf_card, image=zap_perf, text=" Rendimiento y Aceleración", compound="left", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )

        ctk.CTkSwitch(
            perf_card,
            text="Usar Aceleración GPU (NVENC / AMF / QSV) [PRO]",
            variable=self.use_gpu,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkSwitch(
            perf_card,
            text="Notificaciones nativas de Windows / Linux al finalizar",
            variable=self.enable_toast,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Hilos Slider
        h_row = ctk.CTkFrame(perf_card, fg_color="transparent")
        h_row.pack(fill="x", padx=16, pady=(0, 2))
        ctk.CTkLabel(h_row, text="Hilos paralelos por lote [PRO]:", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left")
        self.settings_threads_val = ctk.CTkLabel(
            h_row,
            text=f"{self.parallel_threads.get()} Hilo(s)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_ACCENT,
        )
        self.settings_threads_val.pack(side="right")

        self.thread_slider = ctk.CTkSlider(
            perf_card,
            from_=1,
            to=8,
            number_of_steps=7,
            variable=self.parallel_threads,
            command=self._on_slider_changed,
        )
        self.thread_slider.pack(fill="x", padx=16, pady=(0, 14))

        self._refresh_pro_ui()

    def _refresh_pro_ui(self) -> None:
        is_pro = self.license_manager.is_pro
        badge_txt = "⭐ COMPLEMENTO PRO ACTIVO" if is_pro else "🆓 VERSIÓN BÁSICA (GRATUITA)"
        badge_clr = ("#10b981", "#059669") if is_pro else ("#64748b", "#475569")
        if hasattr(self, "settings_pro_badge"):
            self.settings_pro_badge.configure(text=badge_txt, fg_color=badge_clr)

    def _on_slider_changed(self, value: float) -> None:
        val = int(value)
        if not self.license_manager.is_pro and val > 1:
            self.parallel_threads.set(1)
            self.settings_threads_val.configure(text="1 Hilo (Gratis)")
            self._open_pro_modal()
            return
        self.settings_threads_val.configure(text=f"{val} Hilos")

    # ==========================================
    # 4. BOTTOM ACTION BAR (WINDOWS 11 FLUENT)
    # ==========================================
    def _build_bottom_action_bar(self) -> None:
        action_bar = ctk.CTkFrame(self, corner_radius=0, height=84, fg_color=COLOR_HEADER_BG, border_width=1, border_color=COLOR_CARD_BORDER)
        action_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        action_bar.grid_columnconfigure(0, weight=1)

        zap_action = self._get_icon("zap", (18, 18), "white")
        self.convert_button = ctk.CTkButton(
            action_bar,
            image=zap_action,
            text=" Convertir a MP3",
            compound="left",
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=38,
            command=self._start_conversion,
        )
        self.convert_button.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(action_bar, corner_radius=3, height=6)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.progress_bar.set(0)

        status_row = ctk.CTkFrame(action_bar, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        status_row.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkLabel(status_row, text="●", font=ctk.CTkFont(size=14), text_color="#10b981", width=16)
        self.status_dot.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.status_label = ctk.CTkLabel(status_row, textvariable=self.status_text, font=ctk.CTkFont(family="Segoe UI", size=11), anchor="w")
        self.status_label.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(status_row, text=f"Media Flow v{APP_VERSION}", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_SECONDARY).grid(
            row=0, column=2, sticky="e"
        )

    # ==========================================
    # MANEJO DE FORMATOS Y NAVEGACIÓN
    # ==========================================
    def _select_format_direct(self, fmt_name: str) -> None:
        self.output_format.set(fmt_name)
        self._update_convert_button_text()
        self.status_text.set(f"Formato seleccionado: {fmt_name}")

    def _select_tool_direct(self, tool_name: str, mode_name: str) -> None:
        self.mode.set(mode_name)
        self.output_format.set(tool_name)
        self._update_convert_button_text()
        self.status_text.set(f"Herramienta seleccionada: {tool_name}")

    def _toggle_theme(self) -> None:
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self._save_settings()

    def _open_pro_modal(self) -> None:
        ProUpgradeModal(self)

    def _on_search_query_changed(self, event: Any = None) -> None:
        query = self.search_text.get().strip().lower()
        if not query:
            return

        if any(k in query for k in ("aud", "mp3", "wav", "flac", "ogg", "aac", "m4a", "opus")):
            if self.current_view != "Audio":
                self._switch_view("Audio")
        elif any(k in query for k in ("vid", "mp4", "mkv", "mov", "avi", "webm", "4k", "fps", "h265", "av1")):
            if self.current_view != "Video":
                self._switch_view("Video")
        elif any(k in query for k in ("img", "ima", "png", "jpg", "jpeg", "webp", "avif", "ico", "bmp")):
            if self.current_view != "Imagen":
                self._switch_view("Imagen")
        elif any(k in query for k in ("rec", "trim", "ext", "uni", "concat", "srt", "sub")):
            if self.current_view != "Herramientas":
                self._switch_view("Herramientas")
        elif any(k in query for k in ("bib", "his", "reg")):
            if self.current_view != "Biblioteca":
                self._switch_view("Biblioteca")
        elif any(k in query for k in ("aju", "set", "gpu", "pro", "lic", "hil")):
            if self.current_view != "Ajustes":
                self._switch_view("Ajustes")

    def _on_search_enter(self, event: Any = None) -> None:
        query = self.search_text.get().strip().upper()
        if not query:
            return
        for fmt in AUDIO_FORMATS:
            if query == fmt:
                self.mode.set("Audio")
                self.output_format.set(fmt)
                self._switch_view("Audio")
                return
        for fmt in VIDEO_FORMATS:
            if query == fmt:
                self.mode.set("Video")
                self.output_format.set(fmt)
                self._switch_view("Video")
                return
        for fmt in IMAGE_FORMATS:
            if query == fmt:
                self.mode.set("Imagen")
                self.output_format.set(fmt)
                self._switch_view("Imagen")
                return

    def _update_format_choices(self) -> None:
        m = self.mode.get()
        if m == "Audio":
            choices = list(AUDIO_FORMATS_FREE) + [f"{fmt} (PRO)" for fmt in AUDIO_FORMATS_PRO]
            if hasattr(self, "home_format_menu"):
                self.home_format_menu.configure(values=choices)
            if self.output_format.get() not in AUDIO_FORMATS:
                self.output_format.set("MP3")
        elif m == "Video":
            choices = list(VIDEO_FORMATS_FREE) + [f"{fmt} (PRO)" for fmt in VIDEO_FORMATS_PRO]
            if hasattr(self, "home_format_menu"):
                self.home_format_menu.configure(values=choices)
            if self.output_format.get() not in VIDEO_FORMATS:
                self.output_format.set("MP4")
        elif m == "Imagen":
            if hasattr(self, "home_format_menu"):
                self.home_format_menu.configure(values=list(IMAGE_FORMATS))
            if self.output_format.get() not in IMAGE_FORMATS:
                self.output_format.set("PNG")
        elif m == "Extracción":
            if hasattr(self, "home_format_menu"):
                self.home_format_menu.configure(values=list(EXTRACTION_MODES))
            self.output_format.set(EXTRACTION_MODES[0])
        elif m == "Unir (Concat)":
            if hasattr(self, "home_format_menu"):
                self.home_format_menu.configure(values=list(CONCAT_MODES))
            self.output_format.set(CONCAT_MODES[0])

        self._update_convert_button_text()

    def _on_preset_selected(self, choice: str) -> None:
        opts = PRESETS.get(choice, {})
        if not opts:
            return

        if "PRO" in choice and not self.license_manager.is_pro:
            self._open_pro_modal()
            self.preset.set("Personalizado")
            return

        if "video_format" in opts:
            self.mode.set("Video")
            self._update_format_choices()
            self.output_format.set(opts["video_format"])
            if "video_quality" in opts:
                self.video_quality.set(opts["video_quality"])
            if "res" in opts:
                self.video_res.set(opts["res"])
            if "fps" in opts:
                self.video_fps.set(opts["fps"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])
        elif "audio_format" in opts:
            self.mode.set("Audio")
            self._update_format_choices()
            self.output_format.set(opts["audio_format"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])

    def _update_convert_button_text(self) -> None:
        if not hasattr(self, "convert_button"):
            return
        m = self.mode.get()
        fmt = self.output_format.get()
        if m in ("Extracción", "Unir (Concat)"):
            self.convert_button.configure(text=f" Iniciar {fmt}")
        else:
            self.convert_button.configure(text=f" Convertir a {fmt}")

    # ==========================================
    # MANEJO DE ARCHIVOS Y COLA
    # ==========================================
    def _choose_input_file(self) -> None:
        mode = self.mode.get()
        if mode == "Audio":
            filetypes = (("Audio y Video", f"{AUDIO_EXTENSIONS} {VIDEO_EXTENSIONS}"), ("Todos los archivos", "*.*"))
        elif mode == "Video":
            filetypes = (("Video", VIDEO_EXTENSIONS), ("Todos los archivos", "*.*"))
        elif mode == "Imagen":
            filetypes = (("Imágenes", IMAGE_EXTENSIONS), ("Todos los archivos", "*.*"))
        else:
            filetypes = (("Multimedia", f"{AUDIO_EXTENSIONS} {VIDEO_EXTENSIONS}"), ("Todos los archivos", "*.*"))

        selected = filedialog.askopenfilenames(
            initialdir=str(default_output_dir()),
            title="Elegir archivos para procesar",
            filetypes=filetypes,
        )
        if selected:
            for s in selected:
                p = Path(s)
                if p not in self.input_files:
                    self.input_files.append(p)
            self._refresh_file_list()
            self._probe_selection()

    def _clear_files(self) -> None:
        self.input_files.clear()
        self._refresh_file_list()
        self.media_info_text.set("Sin archivos seleccionados.")

    def _remove_file(self, target: Path) -> None:
        if target in self.input_files:
            self.input_files.remove(target)
            self._refresh_file_list()
            self._probe_selection()

    def _refresh_file_list(self) -> None:
        if not hasattr(self, "home_files_container"):
            return

        for widget in self.home_files_container.winfo_children():
            widget.destroy()

        count = len(self.input_files)
        if hasattr(self, "home_queue_title"):
            self.home_queue_title.configure(text=f"Archivos en Cola ({count})  ›")

        if not self.input_files:
            empty_card = ctk.CTkFrame(self.home_files_container, fg_color="transparent")
            empty_card.pack(fill="x", padx=16, pady=24)

            folder_big = self._get_icon("folder_open", (44, 44), "accent")
            ctk.CTkLabel(empty_card, image=folder_big, text="").pack(pady=(0, 6))
            ctk.CTkLabel(
                empty_card,
                text="Arrastra tus archivos aquí o haz clic en '+ Agregar Archivos' para empezar",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(pady=(0, 10))

            plus_card_icon = self._get_icon("plus", (14, 14), "white")
            ctk.CTkButton(
                empty_card,
                image=plus_card_icon,
                text=" Agregar Archivos",
                compound="left",
                corner_radius=8,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=self._choose_input_file,
                height=30,
            ).pack()
            return

        for idx, p in enumerate(self.input_files):
            card = ctk.CTkFrame(self.home_files_container, corner_radius=8, fg_color=COLOR_CARD_HOVER)
            card.pack(fill="x", padx=10, pady=4)
            card.grid_columnconfigure(1, weight=1)

            # Icono según tipo
            ext = p.suffix.lower()
            if any(ext.endswith(e.strip("*.")) for e in AUDIO_EXTENSIONS.split()):
                file_icon = self._get_icon("music", (18, 18), "color")
            elif any(ext.endswith(e.strip("*.")) for e in VIDEO_EXTENSIONS.split()):
                file_icon = self._get_icon("film", (18, 18), "color")
            elif any(ext.endswith(e.strip("*.")) for e in IMAGE_EXTENSIONS.split()):
                file_icon = self._get_icon("image", (18, 18), "color")
            else:
                file_icon = self._get_icon("file", (18, 18))

            ctk.CTkLabel(card, image=file_icon, text="").grid(row=0, column=0, padx=(10, 6), pady=8)

            # Nombre
            ctk.CTkLabel(
                card,
                text=p.name,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=4, pady=8)

            # Tamaño
            sz_str = format_size(p.stat().st_size) if p.exists() else "N/A"
            ctk.CTkLabel(card, text=sz_str, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_SECONDARY).grid(
                row=0, column=2, padx=8, pady=8
            )

            # Botón Quitar
            x_icon = self._get_icon("x", (12, 12))
            ctk.CTkButton(
                card,
                image=x_icon,
                text="",
                width=26,
                height=26,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#ef4444", "#dc2626"),
                command=lambda f=p: self._remove_file(f),
            ).grid(row=0, column=3, padx=(4, 10), pady=8)

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if selected:
            self.output_dir.set(selected)
            self.cloud_target.set("Carpeta local")

    def _probe_selection(self) -> None:
        files = list(self.input_files)
        if not files:
            self.media_info_text.set("Sin archivos seleccionados.")
            return
        self.media_info_text.set("Analizando metadatos con ffprobe...")
        threading.Thread(target=self._probe_files, args=(files,), daemon=True).start()

    def _probe_files(self, files: list[Path]) -> None:
        ffprobe = find_ffprobe()
        if not ffprobe:
            self.messages.put(("media_info", f"{len(files)} archivo(s) en cola."))
            return
        try:
            first = files[0]
            command = [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(first),
            ]
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=10,
            )
            if process.returncode == 0:
                data = json.loads(process.stdout)
                text = self._format_media_info(first, files, data)
                self.messages.put(("media_info", text))
            else:
                self.messages.put(("media_info", f"{len(files)} archivo(s) en cola."))
        except Exception:
            self.messages.put(("media_info", f"{len(files)} archivo(s) en cola."))

    def _format_media_info(self, first: Path, files: list[Path], data: dict[str, Any]) -> str:
        streams = data.get("streams") if isinstance(data.get("streams"), list) else []
        fmt = data.get("format") if isinstance(data.get("format"), dict) else {}
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

        parts = []
        if len(files) > 1:
            parts.append(f"Cola: {len(files)} archivos (Primero: {first.name})")
        else:
            parts.append(first.name)

        dur = format_duration(fmt.get("duration"))
        sz = format_size(fmt.get("size") or (first.stat().st_size if first.exists() else 0))
        if dur:
            parts.append(f"Duración: {dur}")
        if sz:
            parts.append(f"Tamaño: {sz}")
        if video:
            res = f"{video.get('width')}x{video.get('height')}" if video.get("width") else ""
            codec = str(video.get("codec_name") or "").upper()
            parts.append(f"Video: {codec} {res}".strip())
        if audio:
            codec = str(audio.get("codec_name") or "").upper()
            parts.append(f"Audio: {codec}")

        return "  |  ".join(parts)

    # ==========================================
    # EJECUCIÓN DEL PROCESAMIENTO MULTIMEDIA
    # ==========================================
    def _set_busy(self, value: bool) -> None:
        self.busy = value
        self.convert_button.configure(state="disabled" if value else "normal")
        if value:
            self.progress_bar.start()
            self.status_dot.configure(text_color="#f59e0b")
        else:
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.status_dot.configure(text_color="#10b981")

    def _start_conversion(self) -> None:
        input_files = list(self.input_files)
        output_dir = Path(self.output_dir.get().strip()).expanduser()
        raw_format = self.output_format.get()
        mode = self.mode.get()
        is_pro = self.license_manager.is_pro

        output_format = raw_format.replace(" (PRO)", "").strip()

        if not is_pro:
            if output_format in AUDIO_FORMATS_PRO or output_format in VIDEO_FORMATS_PRO:
                self._open_pro_modal()
                return
            if mode in ("Extracción", "Unir (Concat)"):
                self._open_pro_modal()
                return
            if "4K" in self.video_res.get() or "60 fps" in self.video_fps.get():
                self._open_pro_modal()
                return
            if self.start_trim.get() or self.end_trim.get() or self.target_size_mb.get():
                self._open_pro_modal()
                return

        if not input_files:
            messagebox.showwarning(APP_TITLE, "Selecciona al menos un archivo para convertir.")
            return
        if not output_dir.exists() or not output_dir.is_dir():
            messagebox.showwarning(APP_TITLE, "La carpeta de salida especificada no existe.")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(APP_TITLE, "No se encontró FFmpeg en el sistema.")
            return

        self._set_busy(True)
        self.status_text.set(f"Iniciando procesado de {len(input_files)} archivo(s)...")
        self._save_settings()

        self.worker = threading.Thread(
            target=self._convert_runner,
            args=(mode, input_files, output_dir, ffmpeg, output_format),
            daemon=True,
        )
        self.worker.start()

    def _convert_runner(self, mode: str, input_files: list[Path], output_dir: Path, ffmpeg: str, output_format: str) -> None:
        completed: list[Path] = []
        errors: list[str] = []
        total = len(input_files)

        if mode == "Unir (Concat)":
            try:
                self.messages.put(("progress", "Concatenando archivos seleccionados..."))
                ext = "mp3" if "Audio" in output_format else "mp4"
                out_path = unique_output_path(output_dir, "Medias_Unidos", ext)
                self._concat_files(input_files, out_path, ffmpeg)
                completed.append(out_path)
            except Exception as exc:
                errors.append(str(exc))
        else:
            threads = self.parallel_threads.get() if self.license_manager.is_pro else 1
            max_workers = max(1, min(threads, len(input_files)))

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._convert_one, mode, file, output_dir, ffmpeg, output_format, idx, total): file
                    for idx, file in enumerate(input_files, 1)
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        res = future.result()
                        completed.append(res)
                    except Exception as exc:
                        errors.append(str(exc))

        if errors and not completed:
            self.messages.put(("error", "\n".join(errors)))
        else:
            self.messages.put(("done", (completed, errors)))

    def _concat_files(self, files: list[Path], output_file: Path, ffmpeg: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for file in files:
                escaped = str(file.resolve()).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")
            list_path = f.name

        try:
            cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", str(output_file)]
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if process.returncode != 0:
                raise RuntimeError("Falló la concatenación directa por FFmpeg.")
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)

    def _convert_one(self, mode: str, input_file: Path, output_dir: Path, ffmpeg: str, output_format: str, index: int, total: int) -> Path:
        self.messages.put(("progress", f"[{index}/{total}] Procesando {input_file.name}..."))

        ext_map = {
            "JPG": "jpg",
            "H265": "mp4",
            "AV1": "mp4",
            "Extraer Audio": "mp3",
            "Silenciar Video (Quitar Audio)": "mp4",
            "Extraer Subtítulos (SRT)": "srt",
        }
        ext = ext_map.get(output_format, output_format.lower())

        output_file = unique_output_path(output_dir, f"{input_file.stem}_converted", ext)
        cmd = self._build_ffmpeg_command(mode, ffmpeg, input_file, output_file, output_format)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        _, stderr = process.communicate()
        if process.returncode != 0:
            err_msg = stderr.strip().splitlines()[-1] if stderr.strip() else "Error desconocido de FFmpeg."
            raise RuntimeError(f"{input_file.name}: {err_msg}")

        return output_file

    def _build_ffmpeg_command(self, mode: str, ffmpeg: str, input_file: Path, output_file: Path, output_format: str) -> list[str]:
        cmd = [ffmpeg, "-y"]
        is_pro = self.license_manager.is_pro

        if is_pro:
            start_sec = parse_duration_to_seconds(self.start_trim.get())
            end_sec = parse_duration_to_seconds(self.end_trim.get())
            if start_sec is not None:
                cmd.extend(["-ss", str(start_sec)])
            if end_sec is not None:
                cmd.extend(["-to", str(end_sec)])

        cmd.extend(["-i", str(input_file)])

        if mode == "Extracción":
            if output_format == "Extraer Audio":
                return cmd + ["-vn", "-acodec", "libmp3lame", "-q:a", "2", str(output_file)]
            elif output_format == "Silenciar Video (Quitar Audio)":
                return cmd + ["-an", "-vcodec", "copy", str(output_file)]
            elif output_format == "Extraer Subtítulos (SRT)":
                return cmd + ["-map", "0:s:0?", "-c:s", "subrip", str(output_file)]

        if mode == "Audio":
            bitrate = f"{self.audio_quality.get().split()[0]}k" if "kbps" in self.audio_quality.get() else "192k"
            codec_map = {
                "MP3": ["-vn", "-c:a", "libmp3lame", "-b:a", bitrate],
                "M4A": ["-vn", "-c:a", "aac", "-b:a", bitrate],
                "WAV": ["-vn", "-c:a", "pcm_s16le"],
                "FLAC": ["-vn", "-c:a", "flac"],
                "OGG": ["-vn", "-c:a", "libvorbis", "-b:a", bitrate],
                "OPUS": ["-vn", "-c:a", "libopus", "-b:a", bitrate],
                "AAC": ["-vn", "-c:a", "aac", "-b:a", bitrate],
                "ALAC": ["-vn", "-c:a", "alac"],
                "AIFF": ["-vn", "-c:a", "pcm_s16be"],
            }
            return cmd + codec_map.get(output_format, ["-vn"]) + [str(output_file)]

        if mode == "Video":
            filters = []
            res_val = self.video_res.get()
            scale_map = {
                "4K (2160p) (PRO)": "3840:2160",
                "4K (2160p)": "3840:2160",
                "1080p": "1920:1080",
                "720p": "1280:720",
                "480p": "854:480",
            }
            if res_val in scale_map:
                filters.append(f"scale={scale_map[res_val]}:force_original_aspect_ratio=decrease,pad={scale_map[res_val]}:(ow-iw)/2:(oh-ih)/2")

            fps_val = self.video_fps.get()
            if "60" in fps_val:
                cmd.extend(["-r", "60"])
            elif "30" in fps_val:
                cmd.extend(["-r", "30"])
            elif "24" in fps_val:
                cmd.extend(["-r", "24"])

            if filters:
                cmd.extend(["-vf", ",".join(filters)])

            if is_pro:
                target_mb = parse_duration_to_seconds(self.target_size_mb.get())
                if target_mb and target_mb > 0:
                    cmd.extend(["-fs", f"{int(target_mb * 1024 * 1024)}"])

            use_gpu = self.use_gpu.get() and is_pro
            if output_format == "GIF":
                return cmd + ["-vf", "fps=15,scale=480:-1:flags=lanczos", str(output_file)]
            elif output_format == "H265":
                vcodec = "hevc_nvenc" if (use_gpu and self.gpu_encoders["nvenc"]) else "libx265"
                return cmd + ["-c:v", vcodec, "-c:a", "aac", str(output_file)]
            elif output_format == "WEBM":
                return cmd + ["-c:v", "libvpx-vp9", "-c:a", "libopus", str(output_file)]
            else:
                vcodec = "h264_nvenc" if (use_gpu and self.gpu_encoders["nvenc"]) else "libx264"
                return cmd + ["-c:v", vcodec, "-preset", "medium", "-c:a", "aac", str(output_file)]

        if mode == "Imagen":
            return cmd + ["-frames:v", "1", str(output_file)]

        return cmd + [str(output_file)]

    # ==========================================
    # HISTORIAL DE CONVERSIONES
    # ==========================================
    def _add_history_entry(self, file_path: Path, format_name: str) -> None:
        try:
            sz = format_size(file_path.stat().st_size) if file_path.exists() else "N/A"
            tm = time.strftime("%Y-%m-%d %H:%M:%S")
            item = {"file": str(file_path), "format": format_name, "size": sz, "time": tm}
            self.conversion_history.insert(0, item)
            self._save_settings()
            self._refresh_history_list()
        except Exception:
            pass

    def _refresh_history_list(self) -> None:
        if not hasattr(self, "library_scroll"):
            return

        for widget in self.library_scroll.winfo_children():
            widget.destroy()

        if not self.conversion_history:
            empty_box = ctk.CTkFrame(self.library_scroll, fg_color="transparent")
            empty_box.pack(pady=30)
            hist_icon = self._get_icon("history", (36, 36), "accent")
            ctk.CTkLabel(empty_box, image=hist_icon, text="").pack(pady=(0, 6))
            ctk.CTkLabel(
                empty_box,
                text="Aún no hay conversiones recientes.",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_SECONDARY,
            ).pack()
            return

        for entry in self.conversion_history[:25]:
            card = ctk.CTkFrame(self.library_scroll, corner_radius=8, fg_color=COLOR_CARD_HOVER)
            card.pack(fill="x", padx=10, pady=4)
            card.grid_columnconfigure(0, weight=1)

            p_str = entry.get("file", "")
            f_name = Path(p_str).name if p_str else "Archivo"

            left_info = ctk.CTkFrame(card, fg_color="transparent")
            left_info.grid(row=0, column=0, sticky="w", padx=12, pady=8)

            ctk.CTkLabel(left_info, text=f_name, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(
                left_info,
                text=f"{entry.get('format', '')}  •  {entry.get('size', '')}  •  {entry.get('time', '')}",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_SECONDARY,
            ).pack(anchor="w")

            ext_icon = self._get_icon("external_link", (14, 14), "white")
            ctk.CTkButton(
                card,
                image=ext_icon,
                text=" Abrir",
                compound="left",
                width=75,
                height=26,
                corner_radius=6,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                command=lambda p=p_str: self._open_history_file(p),
            ).grid(row=0, column=1, padx=12, pady=8)

    def _open_history_file(self, path_str: str) -> None:
        if not os.path.exists(path_str):
            return
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{path_str}"', shell=True)
        elif sys.platform.startswith("linux"):
            try:
                subprocess.Popen(["xdg-open", str(Path(path_str).parent)])
            except Exception:
                try:
                    webbrowser.open(Path(path_str).parent.as_uri())
                except Exception:
                    pass
        else:
            try:
                subprocess.Popen(["open", "-R", path_str])
            except Exception:
                pass

    def _clear_history(self) -> None:
        self.conversion_history.clear()
        self._save_settings()
        self._refresh_history_list()

    # ==========================================
    # ACTUALIZACIONES Y MENSAJERÍA
    # ==========================================
    def _check_for_updates(self, silent: bool = False) -> None:
        if is_msix_package():
            if not silent:
                messagebox.showinfo(APP_TITLE, "Esta instalación se actualiza automáticamente desde Microsoft Store / Windows App Installer.")
            return
        if self.update_worker and self.update_worker.is_alive():
            return
        self.update_worker = threading.Thread(target=self._check_for_updates_worker, args=(silent,), daemon=True)
        self.update_worker.start()

    def _check_for_updates_worker(self, silent: bool) -> None:
        try:
            release = fetch_latest_release()
            latest_version = str(release.get("tag_name") or "").strip()
            release_name = str(release.get("name") or latest_version)
            if latest_version and is_newer_version(latest_version, APP_VERSION):
                asset_name, download_url = find_windows_installer_asset(release)
                self.messages.put(("update_downloading", (latest_version, release_name, asset_name)))
                download_dir = Path(tempfile.gettempdir()) / "media-flow-updates" / latest_version
                download_dir.mkdir(parents=True, exist_ok=True)
                installer_path = download_dir / asset_name
                download_file(download_url, installer_path)
                self.messages.put(("update_installing", (latest_version, installer_path)))
            elif not silent:
                self.messages.put(("update_current", "Tienes la última versión instalada."))
        except Exception as exc:
            if not silent:
                self.messages.put(("update_error", f"Error comprobando actualizaciones: {exc}"))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, data = self.messages.get_nowait()
                if kind == "gpu_detected":
                    self.gpu_encoders = data
                    found = [k.upper() for k, v in data.items() if v]
                    if found:
                        zap_icon = self._get_icon("zap", (12, 12), "white")
                        self.gpu_badge.configure(
                            image=zap_icon,
                            compound="left",
                            text=f" GPU: {', '.join(found)}",
                            fg_color=("#10b981", "#059669"),
                            text_color="#ffffff",
                        )
                    else:
                        self.gpu_badge.configure(image=None, text="GPU: CPU", fg_color=("gray85", "#282828"), text_color=COLOR_TEXT_SECONDARY)
                elif kind == "store_pro_owned":
                    if not self.license_manager.is_pro:
                        self.license_manager.activate_store_purchase()
                        self.on_license_updated()
                elif kind == "progress":
                    self.progress_detail.set(data)
                elif kind == "media_info":
                    self.media_info_text.set(data)
                elif kind == "done":
                    completed, errors = data
                    self._set_busy(False)
                    self.status_text.set("Proceso finalizado con éxito.")

                    for c in completed:
                        self._add_history_entry(c, self.output_format.get().replace(" (PRO)", ""))

                    if completed:
                        self.progress_detail.set(f"Generado(s) {len(completed)} archivo(s) en {completed[0].parent}")
                        if self.enable_toast.get():
                            send_desktop_notification("Media Flow PRO", f"¡Conversión completada! {len(completed)} archivo(s) guardados.")
                        messagebox.showinfo(APP_TITLE, f"Conversión completada con éxito.\n\nCarpeta de salida:\n{completed[0].parent}")
                    if errors:
                        messagebox.showwarning(APP_TITLE, "Ocurrieron algunos errores:\n" + "\n".join(errors))
                elif kind == "error":
                    self._set_busy(False)
                    self.status_text.set("Error en el proceso.")
                    self.progress_detail.set(data)
                    messagebox.showerror(APP_TITLE, data)
                elif kind == "update_downloading":
                    latest_version, release_name, asset_name = data
                    self.status_text.set(f"Descargando versión {latest_version}...")
                    self.progress_detail.set(f"{release_name} - {asset_name}")
                elif kind == "update_installing":
                    latest_version, installer_path = data
                    self.status_text.set(f"Instalando versión {latest_version}...")
                    try:
                        launch_installer_after_exit(Path(installer_path))
                    except Exception as exc:
                        messagebox.showerror(APP_TITLE, f"No se pudo iniciar el instalador: {exc}")
                    else:
                        self.after(500, self.destroy)
                elif kind == "update_current":
                    messagebox.showinfo(APP_TITLE, data)
                elif kind == "update_error":
                    messagebox.showerror(APP_TITLE, data)
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)


if __name__ == "__main__":
    app = MediaConverterApp()
    app.mainloop()

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
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

APP_TITLE = "Media Flow"
APP_VERSION = "1.7.0"
GITHUB_REPO = os.environ.get("MEDIA_FLOW_GITHUB_REPO", "musicallyivan/mediaflow")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
STRIPE_CHECKOUT_URL = os.environ.get("MEDIA_FLOW_STRIPE_URL", "https://buy.stripe.com/4gM00l2uV0aXe6k1eIgEg00")
MS_STORE_PRODUCT_ID = os.environ.get("MEDIA_FLOW_STORE_ID", "9N6VZZ3HDFHJ")
MS_STORE_URL = f"https://apps.microsoft.com/detail/{MS_STORE_PRODUCT_ID}"

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


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    return app_dir() / name


def config_path() -> Path:
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
        base / "ffmpeg" / "bin" / "ffmpeg.exe",
        base / "bin" / "ffmpeg.exe",
        Path.home() / "scoop" / "shims" / "ffmpeg.exe",
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
        if candidate.exists():
            return str(candidate)
    return None


def find_ffprobe() -> Optional[str]:
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        candidate = Path(ffmpeg).with_name("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        if candidate.exists():
            return str(candidate)

    found = shutil.which("ffprobe")
    if found:
        return found

    base = app_dir()
    candidates = [
        base / "ffprobe.exe",
        base / "ffmpeg" / "bin" / "ffprobe.exe",
        base / "bin" / "ffprobe.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
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


def send_windows_toast(title: str, message: str) -> None:
    if sys.platform != "win32":
        return
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
        self._is_pro: bool = bool(initial_data.get("is_pro", False))
        if self.pro_key and self.validate_key(self.pro_key):
            self._is_pro = True

    @property
    def is_pro(self) -> bool:
        return self._is_pro

    def validate_key(self, key: str) -> bool:
        cleaned = key.strip().upper()
        if not cleaned:
            return False
        # Claves válidas: MFPRO-XXXX-XXXX-XXXX, DEMO-PRO, o formato especial de licencia
        if cleaned in ("DEMO-PRO", "MFPRO-VIP-2026-PLUS", "MFPRO-PREMIUM-LIFETIME"):
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

    def deactivate(self) -> None:
        self._is_pro = False
        self.pro_key = ""


# ==========================================
# DIÁLOGO MODAL: COMPLEMENTO PRO
# ==========================================
class ProUpgradeModal(ctk.CTkToplevel):
    def __init__(self, parent: "MediaConverterApp") -> None:
        super().__init__(parent)
        self.parent_app = parent
        self.title("Media Flow PRO - Complemento Prémium")
        self.geometry("640x680")
        self.minsize(580, 600)
        self.resizable(False, False)

        # Centrar en pantalla respecto al padre
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, corner_radius=14, fg_color=("gray95", "#0f172a"))
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)

        # Encabezado Banner
        header_card = ctk.CTkFrame(container, corner_radius=12, fg_color=("#4f46e5", "#4338ca"))
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

        # Estado Actual
        status_frame = ctk.CTkFrame(container, corner_radius=10, fg_color=("gray90", "#1e293b"))
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

        # Tabla Comparativa de Funciones
        features_frame = ctk.CTkFrame(container, corner_radius=12, fg_color=("gray90", "#1e293b"))
        features_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 14))
        features_frame.grid_columnconfigure(0, weight=3)
        features_frame.grid_columnconfigure(1, weight=1)
        features_frame.grid_columnconfigure(2, weight=1)

        # Encabezado tabla
        ctk.CTkLabel(features_frame, text="Característica", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="w").grid(
            row=0, column=0, padx=14, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(features_frame, text="Gratis", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="gray60").grid(
            row=0, column=1, padx=6, pady=(12, 6)
        )
        ctk.CTkLabel(features_frame, text="PRO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#4f46e5", "#818cf8")).grid(
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
                text_color=("#10b981", "#34d399") if "✔" in pro_val else "white",
            ).grid(row=idx, column=2, padx=10, pady=4)

        # Activación de Clave
        act_card = ctk.CTkFrame(container, corner_radius=12, fg_color=("gray90", "#1e293b"))
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
            fg_color=("#4f46e5", "#6366f1"),
            hover_color=("#4338ca", "#4f46e5"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_activate_clicked,
            width=90,
        ).grid(row=0, column=1)

        # Botones de Acción Rápida (Demo de 1 clic y Compra)
        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 6))
        btn_box.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_box,
            text="⚡ Desbloquear Demo PRO (1 clic)",
            corner_radius=10,
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_demo_clicked,
            height=38,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

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
            ).grid(row=0, column=1, padx=(6, 0), sticky="ew")
        else:
            ctk.CTkButton(
                btn_box,
                text="💳 Comprar con Stripe",
                corner_radius=10,
                fg_color=("#6366f1", "#4f46e5"),
                hover_color=("#4f46e5", "#4338ca"),
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=self._on_buy_stripe_clicked,
                height=38,
            ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

            store_box = ctk.CTkFrame(container, fg_color="transparent")
            store_box.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))
            store_box.grid_columnconfigure(0, weight=1)

            ctk.CTkButton(
                store_box,
                text="🛍️ Comprar en Microsoft Store",
                corner_radius=10,
                fg_color=("gray75", "#253554"),
                hover_color=("gray65", "#334770"),
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

    def _on_demo_clicked(self) -> None:
        success, message = self.parent_app.license_manager.activate("MFPRO-VIP-2026-PLUS")
        if success:
            self.parent_app.on_license_updated()
            messagebox.showinfo("Media Flow PRO", "¡Se ha activado la versión de prueba PRO completa!", parent=self)
            self.destroy()

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
            # Intento de apertura mediante protocolo directo de Microsoft Store
            subprocess.Popen(["cmd.exe", "/c", "start", f"ms-windows-store://pdp/?productid={MS_STORE_PRODUCT_ID}"], shell=True)
        except Exception:
            webbrowser.open(MS_STORE_URL)
        messagebox.showinfo(
            "Microsoft Store",
            "Se ha abierto la ficha del complemento en Microsoft Store.\nSi estás usando la versión empaquetada de Store, la licencia se activará automáticamente al completar la compra.",
            parent=self,
        )


# ==========================================
# APLICACIÓN PRINCIPAL (CUSTOMTKINTER MODERNA)
# ==========================================
class MediaConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Configuración visual inicial
        self.settings = self._load_settings()
        theme_mode = self.settings.get("theme_mode", "Dark")
        ctk.set_appearance_mode(theme_mode)
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_TITLE} Suite v{APP_VERSION}")
        self.geometry("1040x820")
        self.minsize(920, 720)

        apply_window_corner_preference(self)

        # Gestor de Licencias PRO
        self.license_manager = LicenseManager(self.settings)

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

        self.input_files: list[Path] = []
        self.conversion_history: list[dict[str, Any]] = self.settings.get("history", [])
        self.cloud_folders = detect_cloud_folders()
        self.gpu_encoders = {"nvenc": False, "amf": False, "qsv": False}
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.busy = False
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None

        self._build_ui()
        self._detect_gpu_async()
        self._poll_messages()

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
        """Refresca toda la interfaz cuando cambia el estado de la licencia PRO."""
        self._save_settings()
        self._update_header_badges()
        self._update_format_choices()
        self._refresh_pro_tab()

    def _detect_gpu_async(self) -> None:
        def worker() -> None:
            ffmpeg = find_ffmpeg()
            if ffmpeg:
                res = detect_gpu_encoders(ffmpeg)
                self.messages.put(("gpu_detected", res))

        threading.Thread(target=worker, daemon=True).start()

    # ==========================================
    # CONSTRUCCIÓN DE LA INTERFAZ MODERNA
    # ==========================================
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_modern_header()
        self._build_mode_selector()

        # Tabview principal con esquinas redondeadas
        self.tabview = ctk.CTkTabview(self, corner_radius=14)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))

        self.tab_convert = self.tabview.add("⚡ Convertidor")
        self.tab_advanced = self.tabview.add("⚙️ Ajustes & PRO")
        self.tab_history = self.tabview.add("📜 Historial")

        self._build_convert_tab()
        self._build_advanced_tab()
        self._build_history_tab()

        self._build_action_area()

    def _build_modern_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray90", "#161f30"))
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        header.grid_columnconfigure(1, weight=1)

        # Icono y Título
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        # Logo Redondeado
        logo_badge = ctk.CTkLabel(
            title_box,
            text="⚡",
            width=36,
            height=36,
            corner_radius=10,
            fg_color=("#4f46e5", "#6366f1"),
            font=ctk.CTkFont(size=18),
            text_color="#ffffff",
        )
        logo_badge.pack(side="left", padx=(0, 10))

        title_inner = ctk.CTkFrame(title_box, fg_color="transparent")
        title_inner.pack(side="left")

        title_row = ctk.CTkFrame(title_inner, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text=APP_TITLE,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).pack(side="left", padx=(0, 6))

        # Badge de Estado PRO / Gratis
        self.pro_pill = ctk.CTkLabel(
            title_row,
            text="PRO ACTIVADO",
            corner_radius=8,
            fg_color=("#10b981", "#059669"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#ffffff",
            padx=8,
            pady=2,
        )
        self.pro_pill.pack(side="left")

        ctk.CTkLabel(
            title_inner,
            text="Conversor Multimedia Profesional de Alta Velocidad",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray60",
        ).pack(anchor="w")

        # Acciones de Cabecera (GPU, Licencia, Modo Claro/Oscuro, Actualizaciones)
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, padx=14, pady=10, sticky="e")

        self.gpu_badge = ctk.CTkLabel(
            actions,
            text="GPU: Buscando...",
            corner_radius=8,
            fg_color=("gray80", "#253554"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=10,
            pady=4,
        )
        self.gpu_badge.pack(side="left", padx=(0, 8))

        self.btn_upgrade = ctk.CTkButton(
            actions,
            text="⭐ Obtener PRO",
            corner_radius=8,
            fg_color=("#f59e0b", "#d97706"),
            hover_color=("#d97706", "#b45309"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._open_pro_modal,
            height=30,
        )
        self.btn_upgrade.pack(side="left", padx=(0, 8))

        self.theme_switch = ctk.CTkButton(
            actions,
            text="🌓 Tema",
            corner_radius=8,
            fg_color=("gray80", "#253554"),
            hover_color=("gray70", "#334770"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._toggle_theme,
            width=70,
            height=30,
        )
        self.theme_switch.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="🔄 Actualizar",
            corner_radius=8,
            fg_color=("gray80", "#253554"),
            hover_color=("gray70", "#334770"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self._check_for_updates(False),
            width=85,
            height=30,
        ).pack(side="left")

        self._update_header_badges()

    def _update_header_badges(self) -> None:
        is_pro = self.license_manager.is_pro
        if is_pro:
            self.pro_pill.configure(
                text="⭐ PRO",
                fg_color=("#059669", "#10b981"),
            )
            self.btn_upgrade.configure(
                text="💎 Licencia PRO",
                fg_color=("#4f46e5", "#6366f1"),
                hover_color=("#4338ca", "#4f46e5"),
            )
        else:
            self.pro_pill.configure(
                text="GRATIS",
                fg_color=("gray60", "#475569"),
            )
            self.btn_upgrade.configure(
                text="⭐ Desbloquear PRO",
                fg_color=("#f59e0b", "#d97706"),
                hover_color=("#d97706", "#b45309"),
            )

    def _build_mode_selector(self) -> None:
        mode_card = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        mode_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        mode_card.grid_columnconfigure(0, weight=1)

        modes = ["Audio", "Video", "Imagen", "Extracción", "Unir (Concat)"]
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_card,
            values=modes,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            selected_color=("#4f46e5", "#6366f1"),
            selected_hover_color=("#4338ca", "#4f46e5"),
            command=self._mode_segmented_changed,
        )
        self.mode_seg.set(self.mode.get())
        self.mode_seg.grid(row=0, column=0, sticky="ew", ipady=4)

    def _build_convert_tab(self) -> None:
        self.tab_convert.grid_columnconfigure(0, weight=3)
        self.tab_convert.grid_columnconfigure(1, weight=2)
        self.tab_convert.grid_rowconfigure(0, weight=1)

        # Columna Izquierda: Cola de Archivos
        files_card = ctk.CTkFrame(self.tab_convert, corner_radius=12, fg_color=("gray90", "#161f30"))
        files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        files_card.grid_columnconfigure(0, weight=1)
        files_card.grid_rowconfigure(1, weight=1)

        # Encabezado archivos
        head_files = ctk.CTkFrame(files_card, fg_color="transparent")
        head_files.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        head_files.grid_columnconfigure(0, weight=1)

        self.queue_title = ctk.CTkLabel(
            head_files,
            text="Archivos en Cola (0)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.queue_title.grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(head_files, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_box,
            text="+ Agregar Archivos",
            corner_radius=8,
            fg_color=("#4f46e5", "#6366f1"),
            hover_color=("#4338ca", "#4f46e5"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._choose_input_file,
            height=30,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_box,
            text="Limpiar",
            corner_radius=8,
            fg_color=("gray75", "#253554"),
            hover_color=("gray65", "#334770"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._clear_files,
            width=65,
            height=30,
        ).pack(side="left")

        # Lista Scrollable de Archivos con Tarjetas Redondeadas
        self.files_scroll = ctk.CTkScrollableFrame(files_card, corner_radius=10, fg_color=("gray95", "#0f172a"))
        self.files_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.files_scroll.grid_columnconfigure(0, weight=1)

        # Tarjeta inferior con Metadatos
        info_card = ctk.CTkFrame(files_card, corner_radius=8, fg_color=("gray85", "#1e293b"))
        info_card.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 10))
        info_card.grid_columnconfigure(0, weight=1)

        self.info_label = ctk.CTkLabel(
            info_card,
            textvariable=self.media_info_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray60",
            anchor="w",
            wraplength=480,
        )
        self.info_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        # Columna Derecha: Configuración de Conversión
        ctrl_card = ctk.CTkFrame(self.tab_convert, corner_radius=12, fg_color=("gray90", "#161f30"))
        ctrl_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)
        ctrl_card.grid_columnconfigure(0, weight=1)

        # Preajuste Rápido
        ctk.CTkLabel(ctrl_card, text="Perfil / Preajuste Rápido", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 2)
        )
        self.preset_menu = ctk.CTkOptionMenu(
            ctrl_card,
            variable=self.preset,
            values=list(PRESETS.keys()),
            corner_radius=8,
            command=self._on_preset_selected,
        )
        self.preset_menu.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        # Formato de Salida y Calidad
        fmt_grid = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        fmt_grid.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        fmt_grid.grid_columnconfigure(0, weight=1)
        fmt_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fmt_grid, text="Formato Salida", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self.format_menu = ctk.CTkOptionMenu(
            fmt_grid,
            variable=self.output_format,
            values=AUDIO_FORMATS,
            corner_radius=8,
            command=lambda _: self._update_convert_button_text(),
        )
        self.format_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(fmt_grid, text="Calidad / Bitrate", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", pady=(0, 2)
        )
        self.quality_menu = ctk.CTkOptionMenu(
            fmt_grid,
            variable=self.audio_quality,
            values=["128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"],
            corner_radius=8,
        )
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(6, 0))

        # Opciones de Video (Resolución y FPS)
        self.video_opts_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        self.video_opts_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.video_opts_frame.grid_columnconfigure(0, weight=1)
        self.video_opts_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.video_opts_frame, text="Resolución", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self.res_menu = ctk.CTkOptionMenu(
            self.video_opts_frame,
            variable=self.video_res,
            values=["Original", "1080p", "720p", "480p", "4K (2160p) (PRO)"],
            corner_radius=8,
        )
        self.res_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(self.video_opts_frame, text="Framerate (FPS)", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", pady=(0, 2)
        )
        self.fps_menu = ctk.CTkOptionMenu(
            self.video_opts_frame,
            variable=self.video_fps,
            values=["Original", "30 fps", "24 fps", "60 fps (PRO)"],
            corner_radius=8,
        )
        self.fps_menu.grid(row=1, column=1, sticky="ew", padx=(6, 0))

        # Destino de Salida
        ctk.CTkLabel(ctrl_card, text="Directorio de Salida", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(
            row=4, column=0, sticky="w", padx=14, pady=(2, 2)
        )
        dest_box = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        dest_box.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 6))
        dest_box.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(dest_box, textvariable=self.output_dir, corner_radius=8)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            dest_box,
            text="📁",
            width=36,
            corner_radius=8,
            fg_color=("gray75", "#253554"),
            hover_color=("gray65", "#334770"),
            command=self._choose_folder,
        ).grid(row=0, column=1)

        # Destino Nube
        cloud_options = ["Carpeta local"] + [f"{k} (PRO)" for k in self.cloud_folders.keys()]
        self.cloud_menu = ctk.CTkOptionMenu(
            ctrl_card,
            variable=self.cloud_target,
            values=cloud_options,
            corner_radius=8,
            command=self._cloud_changed,
        )
        self.cloud_menu.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 12))

        self._update_format_choices()

    def _build_advanced_tab(self) -> None:
        self.tab_advanced.grid_columnconfigure(0, weight=1)
        self.tab_advanced.grid_columnconfigure(1, weight=1)

        # Tarjeta 1: Estado del Complemento PRO
        self.pro_card = ctk.CTkFrame(self.tab_advanced, corner_radius=12, fg_color=("gray90", "#161f30"))
        self.pro_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 10))
        self.pro_card.grid_columnconfigure(1, weight=1)

        self.pro_status_label = ctk.CTkLabel(
            self.pro_card,
            text="💎 Estado del Complemento PRO",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.pro_status_label.grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self.pro_badge_detail = ctk.CTkLabel(
            self.pro_card,
            text="COMPLEMENTO ACTIVO",
            corner_radius=8,
            fg_color=("#10b981", "#059669"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#ffffff",
            padx=10,
            pady=4,
        )
        self.pro_badge_detail.grid(row=0, column=1, padx=14, pady=12, sticky="e")

        ctk.CTkButton(
            self.pro_card,
            text="Administrar / Adquirir Licencia PRO",
            corner_radius=8,
            fg_color=("#4f46e5", "#6366f1"),
            hover_color=("#4338ca", "#4f46e5"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._open_pro_modal,
        ).grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 12), sticky="ew")

        # Tarjeta 2: Edición y Recorte (Trim & Compresión)
        trim_card = ctk.CTkFrame(self.tab_advanced, corner_radius=12, fg_color=("gray90", "#161f30"))
        trim_card.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(0, 10))
        trim_card.grid_columnconfigure(0, weight=1)
        trim_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            trim_card,
            text="✂️ Recorte de Tiempo (Trim) [PRO]",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(trim_card, text="Inicio (hh:mm:ss o seg):", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="gray60").grid(
            row=1, column=0, sticky="w", padx=14, pady=(0, 2)
        )
        ctk.CTkEntry(trim_card, textvariable=self.start_trim, corner_radius=8, placeholder_text="00:00:10").grid(
            row=2, column=0, sticky="ew", padx=(14, 6), pady=(0, 10)
        )

        ctk.CTkLabel(trim_card, text="Fin (hh:mm:ss o seg):", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="gray60").grid(
            row=1, column=1, sticky="w", padx=(6, 14), pady=(0, 2)
        )
        ctk.CTkEntry(trim_card, textvariable=self.end_trim, corner_radius=8, placeholder_text="00:01:30").grid(
            row=2, column=1, sticky="ew", padx=(6, 14), pady=(0, 10)
        )

        ctk.CTkLabel(
            trim_card,
            text="📦 Compresión a Tamaño Objetivo (MB) [PRO]",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(6, 2))

        ctk.CTkEntry(trim_card, textvariable=self.target_size_mb, corner_radius=8, placeholder_text="Ejemplo: 25 para Discord, 10 para Email").grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12)
        )

        # Tarjeta 3: Rendimiento y Hardware
        perf_card = ctk.CTkFrame(self.tab_advanced, corner_radius=12, fg_color=("gray90", "#161f30"))
        perf_card.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=(0, 10))
        perf_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            perf_card,
            text="🚀 Rendimiento y Hardware",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))

        self.gpu_switch = ctk.CTkSwitch(
            perf_card,
            text="Usar Aceleración GPU (NVENC/AMF) [PRO]",
            variable=self.use_gpu,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.gpu_switch.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        self.toast_switch = ctk.CTkSwitch(
            perf_card,
            text="Notificaciones de Windows al finalizar",
            variable=self.enable_toast,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.toast_switch.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

        # Slider de Hilos Multihilo
        hilos_header = ctk.CTkFrame(perf_card, fg_color="transparent")
        hilos_header.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 2))
        hilos_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hilos_header, text="Hilos Paralelos por Lote [PRO]:", font=ctk.CTkFont(family="Segoe UI", size=12)).grid(row=0, column=0, sticky="w")
        self.threads_val_label = ctk.CTkLabel(
            hilos_header,
            text=f"{self.parallel_threads.get()} Hilo(s)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#4f46e5", "#818cf8"),
        )
        self.threads_val_label.grid(row=0, column=1, sticky="e")

        self.thread_slider = ctk.CTkSlider(
            perf_card,
            from_=1,
            to=8,
            number_of_steps=7,
            variable=self.parallel_threads,
            command=self._on_slider_changed,
        )
        self.thread_slider.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))

        self._refresh_pro_tab()

    def _refresh_pro_tab(self) -> None:
        is_pro = self.license_manager.is_pro
        if is_pro:
            self.pro_badge_detail.configure(
                text="⭐ COMPLEMENTO PRO ACTIVADO",
                fg_color=("#10b981", "#059669"),
            )
        else:
            self.pro_badge_detail.configure(
                text="🆓 VERSIÓN BÁSICA (GRATUITA)",
                fg_color=("gray60", "#475569"),
            )

    def _on_slider_changed(self, value: float) -> None:
        val = int(value)
        if not self.license_manager.is_pro and val > 1:
            self.parallel_threads.set(1)
            self.threads_val_label.configure(text="1 Hilo (Gratis)")
            self._open_pro_modal()
            return
        self.threads_val_label.configure(text=f"{val} Hilos")

    def _build_history_tab(self) -> None:
        self.tab_history.grid_columnconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text="Historial de Conversiones Recientes",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top,
            text="Limpiar Historial",
            corner_radius=8,
            fg_color=("gray75", "#253554"),
            hover_color=("gray65", "#334770"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._clear_history,
            width=110,
            height=30,
        ).grid(row=0, column=1, sticky="e")

        self.history_scroll = ctk.CTkScrollableFrame(self.tab_history, corner_radius=12, fg_color=("gray90", "#161f30"))
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.history_scroll.grid_columnconfigure(0, weight=1)

        self._refresh_history_list()

    def _build_action_area(self) -> None:
        action_frame = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray90", "#161f30"))
        action_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        action_frame.grid_columnconfigure(0, weight=1)

        # Botón Grande de Conversión
        self.convert_button = ctk.CTkButton(
            action_frame,
            text="⚡ Convertir a MP3",
            corner_radius=10,
            fg_color=("#4f46e5", "#6366f1"),
            hover_color=("#4338ca", "#4f46e5"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=44,
            command=self._start_conversion,
        )
        self.convert_button.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        # Barra de progreso moderna redondeada
        self.progress_bar = ctk.CTkProgressBar(action_frame, corner_radius=6, height=10)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.progress_bar.set(0)

        # Fila de estado
        status_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        status_row.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkLabel(
            status_row,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color="#10b981",
            width=16,
        )
        self.status_dot.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_row,
            textvariable=self.status_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
        )
        self.status_label.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            status_row,
            text=f"Media Flow v{APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="gray50",
        ).grid(row=0, column=2, sticky="e")

        self.progress_detail_label = ctk.CTkLabel(
            action_frame,
            textvariable=self.progress_detail,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="gray50",
            anchor="w",
        )
        self.progress_detail_label.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 6))

    # ==========================================
    # MANEJO DE MODOS Y SELECCIÓN
    # ==========================================
    def _toggle_theme(self) -> None:
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self._save_settings()

    def _open_pro_modal(self) -> None:
        ProUpgradeModal(self)

    def _mode_segmented_changed(self, mode: str) -> None:
        self.mode.set(mode)
        self._update_format_choices()
        self._update_convert_button_text()

    def _update_format_choices(self) -> None:
        m = self.mode.get()
        is_pro = self.license_manager.is_pro

        if m == "Audio":
            choices = list(AUDIO_FORMATS_FREE) + [f"{fmt} (PRO)" for fmt in AUDIO_FORMATS_PRO]
            self.format_menu.configure(values=choices)
            if self.output_format.get() not in AUDIO_FORMATS:
                self.output_format.set("MP3")
            self.quality_menu.configure(values=["128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"], state="normal")
            self.video_opts_frame.grid_remove()
        elif m == "Video":
            choices = list(VIDEO_FORMATS_FREE) + [f"{fmt} (PRO)" for fmt in VIDEO_FORMATS_PRO]
            self.format_menu.configure(values=choices)
            if self.output_format.get() not in VIDEO_FORMATS:
                self.output_format.set("MP4")
            self.quality_menu.configure(values=["Alta", "Equilibrada", "Comprimida"], state="normal")
            self.video_opts_frame.grid()
        elif m == "Imagen":
            self.format_menu.configure(values=list(IMAGE_FORMATS))
            if self.output_format.get() not in IMAGE_FORMATS:
                self.output_format.set("PNG")
            self.quality_menu.configure(values=["100%", "90%", "80%", "70%"], state="normal")
            self.video_opts_frame.grid_remove()
        elif m == "Extracción":
            self.format_menu.configure(values=list(EXTRACTION_MODES))
            self.output_format.set(EXTRACTION_MODES[0])
            self.quality_menu.configure(state="disabled")
            self.video_opts_frame.grid_remove()
        elif m == "Unir (Concat)":
            self.format_menu.configure(values=list(CONCAT_MODES))
            self.output_format.set(CONCAT_MODES[0])
            self.quality_menu.configure(state="disabled")
            self.video_opts_frame.grid_remove()

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
            self.mode_seg.set("Video")
            self._update_format_choices()
            self.output_format.set(opts["video_format"])
            if "video_quality" in opts:
                self.video_quality.set(opts["video_quality"])
                self.quality_menu.set(opts["video_quality"])
            if "res" in opts:
                self.video_res.set(opts["res"])
            if "fps" in opts:
                self.video_fps.set(opts["fps"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])
        elif "audio_format" in opts:
            self.mode.set("Audio")
            self.mode_seg.set("Audio")
            self._update_format_choices()
            self.output_format.set(opts["audio_format"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])
                self.quality_menu.set(opts["audio_quality"])

    def _cloud_changed(self, choice: str) -> None:
        if choice != "Carpeta local":
            if not self.license_manager.is_pro:
                self.cloud_target.set("Carpeta local")
                self._open_pro_modal()
                return
            clean_name = choice.replace(" (PRO)", "").strip()
            if clean_name in self.cloud_folders:
                self.output_dir.set(str(self.cloud_folders[clean_name]))

    def _update_convert_button_text(self) -> None:
        if not hasattr(self, "convert_button"):
            return
        m = self.mode.get()
        fmt = self.output_format.get()
        if m in ("Extracción", "Unir (Concat)"):
            self.convert_button.configure(text=f"⚡ {fmt}")
        else:
            self.convert_button.configure(text=f"⚡ Convertir a {fmt}")

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
            title="Elegir archivos para convertir",
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
        for widget in self.files_scroll.winfo_children():
            widget.destroy()

        self.queue_title.configure(text=f"Archivos en Cola ({len(self.input_files)})")

        if not self.input_files:
            empty_lbl = ctk.CTkLabel(
                self.files_scroll,
                text="Arrastra o añade archivos pulsando '+ Agregar Archivos'",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="gray50",
            )
            empty_lbl.pack(pady=30)
            return

        for idx, p in enumerate(self.input_files):
            card = ctk.CTkFrame(self.files_scroll, corner_radius=8, fg_color=("gray90", "#1e293b"))
            card.pack(fill="x", padx=4, pady=3)
            card.grid_columnconfigure(1, weight=1)

            # Icono
            ctk.CTkLabel(card, text="📄", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=(8, 4), pady=6)

            # Nombre
            name_lbl = ctk.CTkLabel(
                card,
                text=p.name,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                anchor="w",
            )
            name_lbl.grid(row=0, column=1, sticky="w", padx=4, pady=6)

            # Tamaño
            sz_str = format_size(p.stat().st_size) if p.exists() else "N/A"
            ctk.CTkLabel(card, text=sz_str, font=ctk.CTkFont(family="Segoe UI", size=10), text_color="gray50").grid(
                row=0, column=2, padx=6, pady=6
            )

            # Botón eliminar
            del_btn = ctk.CTkButton(
                card,
                text="✕",
                width=24,
                height=24,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#ef4444", "#dc2626"),
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda f=p: self._remove_file(f),
            )
            del_btn.grid(row=0, column=3, padx=(4, 8), pady=6)

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
            parts.append(f"⏱️ {dur}")
        if sz:
            parts.append(f"💾 {sz}")
        if video:
            res = f"{video.get('width')}x{video.get('height')}" if video.get("width") else ""
            codec = str(video.get("codec_name") or "").upper()
            parts.append(f"🎬 {codec} {res}".strip())
        if audio:
            codec = str(audio.get("codec_name") or "").upper()
            parts.append(f"🎵 {codec}")

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

        # Limpiar flags de formato como " (PRO)"
        output_format = raw_format.replace(" (PRO)", "").strip()

        # Verificación de Funciones PRO
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

        # Recorte de tiempo (Trim) - Exclusivo PRO
        if is_pro:
            start_sec = parse_duration_to_seconds(self.start_trim.get())
            end_sec = parse_duration_to_seconds(self.end_trim.get())
            if start_sec is not None:
                cmd.extend(["-ss", str(start_sec)])
            if end_sec is not None:
                cmd.extend(["-to", str(end_sec)])

        cmd.extend(["-i", str(input_file)])

        # Extracción especial (PRO)
        if mode == "Extracción":
            if output_format == "Extraer Audio":
                return cmd + ["-vn", "-acodec", "libmp3lame", "-q:a", "2", str(output_file)]
            elif output_format == "Silenciar Video (Quitar Audio)":
                return cmd + ["-an", "-vcodec", "copy", str(output_file)]
            elif output_format == "Extraer Subtítulos (SRT)":
                return cmd + ["-map", "0:s:0?", "-c:s", "subrip", str(output_file)]

        # Audio mode
        if mode == "Audio":
            bitrate = f"{self.quality_menu.get().split()[0]}k" if "kbps" in self.quality_menu.get() else "192k"
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

        # Video mode
        if mode == "Video":
            filters = []

            # Resolution scaling
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

            # FPS
            fps_val = self.video_fps.get()
            if "60" in fps_val:
                cmd.extend(["-r", "60"])
            elif "30" in fps_val:
                cmd.extend(["-r", "30"])
            elif "24" in fps_val:
                cmd.extend(["-r", "24"])

            if filters:
                cmd.extend(["-vf", ",".join(filters)])

            # Target size calculation if set (PRO)
            if is_pro:
                target_mb = parse_duration_to_seconds(self.target_size_mb.get())
                if target_mb and target_mb > 0:
                    cmd.extend(["-fs", f"{int(target_mb * 1024 * 1024)}"])

            # Video encoder selection (GPU vs CPU)
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

        # Image mode
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
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not self.conversion_history:
            ctk.CTkLabel(
                self.history_scroll,
                text="Aún no hay conversiones recientes.",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="gray50",
            ).pack(pady=30)
            return

        for entry in self.conversion_history[:25]:
            card = ctk.CTkFrame(self.history_scroll, corner_radius=8, fg_color=("gray95", "#1e293b"))
            card.pack(fill="x", padx=4, pady=3)
            card.grid_columnconfigure(0, weight=1)

            p_str = entry.get("file", "")
            f_name = Path(p_str).name if p_str else "Archivo"

            left_info = ctk.CTkFrame(card, fg_color="transparent")
            left_info.grid(row=0, column=0, sticky="w", padx=10, pady=6)

            ctk.CTkLabel(left_info, text=f_name, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(
                left_info,
                text=f"{entry.get('format', '')}  •  {entry.get('size', '')}  •  {entry.get('time', '')}",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color="gray50",
            ).pack(anchor="w")

            ctk.CTkButton(
                card,
                text="📂 Abrir",
                width=65,
                height=26,
                corner_radius=6,
                fg_color=("gray80", "#253554"),
                hover_color=("gray70", "#334770"),
                font=ctk.CTkFont(family="Segoe UI", size=10),
                command=lambda p=p_str: self._open_history_file(p),
            ).grid(row=0, column=1, padx=10, pady=6)

    def _open_history_file(self, path_str: str) -> None:
        if os.path.exists(path_str):
            subprocess.Popen(f'explorer /select,"{path_str}"', shell=True)

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
                        self.gpu_badge.configure(text=f"GPU: {', '.join(found)} ✔", fg_color=("#10b981", "#059669"), text_color="#ffffff")
                    else:
                        self.gpu_badge.configure(text="GPU: CPU Fallback", fg_color=("gray80", "#253554"), text_color="gray70")
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
                            send_windows_toast("Media Flow PRO", f"¡Conversión completada! {len(completed)} archivo(s) guardados.")
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

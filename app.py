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
from pathlib import Path
from typing import Any, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Media Flow"
APP_VERSION = "1.6.1"
GITHUB_REPO = os.environ.get("MEDIA_FLOW_GITHUB_REPO", "musicallyivan/mediaflow")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

AUDIO_FORMATS = ("MP3", "M4A", "WAV", "FLAC", "OGG", "OPUS", "AAC", "ALAC", "AIFF")
VIDEO_FORMATS = ("MP4", "MOV", "WEBM", "MKV", "GIF", "AVI", "AV1", "H265")
IMAGE_FORMATS = ("PNG", "JPG", "WEBP", "BMP", "AVIF", "ICO", "TIFF")
EXTRACTION_MODES = ("Extraer Audio", "Silenciar Video (Quitar Audio)", "Extraer Subtítulos (SRT)")
CONCAT_MODES = ("Unir Archivos de Audio", "Unir Archivos de Video")

AUDIO_EXTENSIONS = "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff *.m4b"
VIDEO_EXTENSIONS = "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.m4v *.flv *.ogv *.3gp"
IMAGE_EXTENSIONS = "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif *.avif *.heic *.ico"

PRESETS = {
    "Personalizado": {},
    "Optimizado para Web": {"video_format": "MP4", "video_quality": "Equilibrada", "res": "1080p", "fps": "30", "audio_quality": "160 kbps"},
    "WhatsApp / Redes (Ligero)": {"video_format": "MP4", "video_quality": "Comprimida", "res": "720p", "fps": "30", "audio_quality": "128 kbps"},
    "Calidad Máxima (Lossless)": {"video_format": "MKV", "video_quality": "Alta", "res": "Original", "fps": "Original", "audio_quality": "320 kbps"},
    "TikTok / Reels / Shorts": {"video_format": "MP4", "video_quality": "Alta", "res": "1080p", "fps": "60", "audio_quality": "192 kbps"},
    "Audio Alta Fidelidad": {"audio_format": "FLAC", "audio_quality": "320 kbps"},
}

THEMES = {
    "light": {
        "window": "#f1f5f9",
        "surface": "#ffffff",
        "surface_alt": "#e2e8f0",
        "card_border": "#cbd5e1",
        "glass_highlight": "#ffffff",
        "text": "#0f172a",
        "text_muted": "#64748b",
        "accent": "#4f46e5",
        "accent_hover": "#4338ca",
        "accent_soft": "#e0e7ff",
        "accent_glow": "#6366f1",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "input_bg": "#ffffff",
        "button_bg": "#e2e8f0",
        "button_hover": "#cbd5e1",
        "badge_bg": "#e0e7ff",
        "badge_fg": "#3730a3",
        "shadow": "#cbd5e1",
        "tree_even": "#ffffff",
        "tree_odd": "#f8fafc",
    },
    "dark": {
        "window": "#090d16",
        "surface": "#131c2e",
        "surface_alt": "#1a263e",
        "card_border": "#253554",
        "glass_highlight": "#2d4066",
        "text": "#f8fafc",
        "text_muted": "#94a3b8",
        "accent": "#6366f1",
        "accent_hover": "#4f46e5",
        "accent_soft": "#1e1b4b",
        "accent_glow": "#818cf8",
        "success": "#10b981",
        "danger": "#f87171",
        "warning": "#fbbf24",
        "input_bg": "#0a1120",
        "button_bg": "#1e2a42",
        "button_hover": "#2c3d5f",
        "badge_bg": "#1b243b",
        "badge_fg": "#a5b4fc",
        "shadow": "#030712",
        "tree_even": "#131c2e",
        "tree_odd": "#0d1424",
    },
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

    raise ValueError("No se encontro el instalador de Windows en la release.")


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"media-flow/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def apply_window_corner_preference(window: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        preference = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preference), ctypes.sizeof(preference))
    except (AttributeError, OSError, tk.TclError):
        pass


def launch_installer_after_exit(installer_path: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("La instalacion automatica solo esta disponible en Windows.")

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
    raise FileExistsError("No se pudo crear un nombre de salida unico.")


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


def rounded_rectangle(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: Any) -> None:
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)


class MediaConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} Pro v{APP_VERSION}")
        self.geometry("980x780")
        self.minsize(880, 680)

        apply_window_corner_preference(self)
        self.settings = self._load_settings()

        # Variables
        self.theme_name = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.mode = tk.StringVar(value=self.settings.get("mode", "Audio"))
        self.preset = tk.StringVar(value=self.settings.get("preset", "Personalizado"))
        self.output_dir = tk.StringVar(value=self.settings.get("output_dir", str(default_output_dir())))
        self.output_format = tk.StringVar(value=self.settings.get("output_format", "MP3"))
        self.audio_quality = tk.StringVar(value=self.settings.get("audio_quality", "192 kbps"))
        self.video_quality = tk.StringVar(value=self.settings.get("video_quality", "Equilibrada"))
        self.video_res = tk.StringVar(value=self.settings.get("video_res", "Original"))
        self.video_fps = tk.StringVar(value=self.settings.get("video_fps", "Original"))
        self.cloud_target = tk.StringVar(value=self.settings.get("cloud_target", "Carpeta local"))
        
        self.start_trim = tk.StringVar(value="")
        self.end_trim = tk.StringVar(value="")
        self.target_size_mb = tk.StringVar(value="")
        self.use_gpu = tk.BooleanVar(value=self.settings.get("use_gpu", True))
        self.parallel_threads = tk.IntVar(value=self.settings.get("parallel_threads", 2))
        self.enable_toast = tk.BooleanVar(value=self.settings.get("enable_toast", True))

        self.status = tk.StringVar(value="Listo. Arrastra o selecciona tus archivos para empezar.")
        self.progress_text = tk.StringVar(value="")
        self.media_info = tk.StringVar(value="Sin archivos seleccionados.")
        
        self.input_files: list[Path] = []
        self.conversion_history: list[dict[str, Any]] = self.settings.get("history", [])
        self.cloud_folders = detect_cloud_folders()
        self.gpu_encoders = {"nvenc": False, "amf": False, "qsv": False}
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.busy = False
        self.progress_phase = 0
        self.pulse_phase = 0
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None
        self.mode_buttons: dict[str, tk.Button] = {}
        self.canvases: list[tk.Canvas] = []

        self.style = ttk.Style()
        self._build_ui()
        self._apply_theme()
        self._detect_gpu_async()
        self._poll_messages()

    @property
    def palette(self) -> dict[str, str]:
        return THEMES.get(self.theme_name.get(), THEMES["dark"])

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
                "theme": self.theme_name.get(),
                "mode": self.mode.get(),
                "preset": self.preset.get(),
                "output_dir": self.output_dir.get(),
                "output_format": self.output_format.get(),
                "audio_quality": self.audio_quality.get(),
                "video_quality": self.video_quality.get(),
                "video_res": self.video_res.get(),
                "video_fps": self.video_fps.get(),
                "cloud_target": self.cloud_target.get(),
                "use_gpu": self.use_gpu.get(),
                "parallel_threads": self.parallel_threads.get(),
                "enable_toast": self.enable_toast.get(),
                "history": self.conversion_history[-20:],
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _detect_gpu_async(self) -> None:
        def worker() -> None:
            ffmpeg = find_ffmpeg()
            if ffmpeg:
                res = detect_gpu_encoders(ffmpeg)
                self.messages.put(("gpu_detected", res))
        threading.Thread(target=worker, daemon=True).start()

    def _build_ui(self) -> None:
        self.main = ttk.Frame(self, style="App.TFrame", padding=16)
        self.main.pack(fill="both", expand=True)
        self.main.columnconfigure(0, weight=1)

        self._build_header()
        self._build_mode_selector()

        # Notebook tabs for main content & options
        self.notebook = ttk.Notebook(self.main)
        self.notebook.grid(row=2, column=0, sticky="nsew", pady=(10, 10))
        self.main.rowconfigure(2, weight=1)

        self.tab_convert = ttk.Frame(self.notebook, style="App.TFrame", padding=10)
        self.tab_advanced = ttk.Frame(self.notebook, style="App.TFrame", padding=10)
        self.tab_history = ttk.Frame(self.notebook, style="App.TFrame", padding=10)

        self.notebook.add(self.tab_convert, text=" ⚡ Convertidor ")
        self.notebook.add(self.tab_advanced, text=" ⚙️ Ajustes Avanzados ")
        self.notebook.add(self.tab_history, text=" 📜 Historial ")

        self._build_convert_tab()
        self._build_advanced_tab()
        self._build_history_tab()

        self._build_action_area()

    def _build_header(self) -> None:
        header = ttk.Frame(self.main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(1, weight=1)

        self.logo = tk.Canvas(header, width=42, height=42, highlightthickness=0)
        self.logo.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
        self.canvases.append(self.logo)

        title_frame = ttk.Frame(header, style="App.TFrame")
        title_frame.grid(row=0, column=1, sticky="w")
        ttk.Label(title_frame, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Label(title_frame, text=" PRO", style="ProBadge.TLabel").pack(side="left", padx=6)

        ttk.Label(
            header,
            text="Procesador multimedia de alto rendimiento local.",
            style="Muted.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        actions = ttk.Frame(header, style="App.TFrame")
        actions.grid(row=0, column=2, rowspan=2, sticky="e")
        
        self.gpu_label = ttk.Label(actions, text="GPU: Buscando...", style="Badge.TLabel")
        self.gpu_label.grid(row=0, column=0, padx=(0, 8))

        self.theme_button = ttk.Button(actions, text="🌙 Modo Oscuro", command=self._toggle_theme, style="Secondary.TButton")
        self.theme_button.grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="🔄 Actualizar", command=self._check_for_updates, style="Secondary.TButton").grid(row=0, column=2)

    def _build_mode_selector(self) -> None:
        self.mode_card = ttk.Frame(self.main, style="Card.TFrame", padding=6)
        self.mode_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        modes = ("Audio", "Video", "Imagen", "Extracción", "Unir (Concat)")
        for index, mode_name in enumerate(modes):
            self.mode_card.columnconfigure(index, weight=1, uniform="mode")
            button = tk.Button(
                self.mode_card,
                text=mode_name,
                relief="flat",
                borderwidth=0,
                font=("Segoe UI", 10, "bold"),
                command=lambda v=mode_name: self._mode_changed(v),
                cursor="hand2",
            )
            button.grid(row=0, column=index, sticky="ew", padx=3, ipady=8)
            self.mode_buttons[mode_name] = button

    def _build_convert_tab(self) -> None:
        self.tab_convert.columnconfigure(0, weight=3)
        self.tab_convert.columnconfigure(1, weight=2)
        self.tab_convert.rowconfigure(0, weight=1)

        # Left Column: Files list / Treeview
        files_card = ttk.Frame(self.tab_convert, style="Card.TFrame", padding=14)
        files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        files_card.columnconfigure(0, weight=1)
        files_card.rowconfigure(2, weight=1)

        header_files = ttk.Frame(files_card, style="Card.TFrame")
        header_files.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header_files.columnconfigure(0, weight=1)

        ttk.Label(header_files, text="Archivos en Cola", style="Section.TLabel").grid(row=0, column=0, sticky="w")

        btn_box = ttk.Frame(header_files, style="Card.TFrame")
        btn_box.grid(row=0, column=1, sticky="e")
        ttk.Button(btn_box, text="+ Agregar", command=self._choose_input_file, style="Secondary.TButton").pack(side="left", padx=2)
        ttk.Button(btn_box, text="Limpiar", command=self._clear_files, style="Secondary.TButton").pack(side="left", padx=2)

        # Treeview list
        columns = ("name", "size", "status")
        self.file_tree = ttk.Treeview(files_card, columns=columns, show="headings", height=8, selectmode="extended")
        self.file_tree.heading("name", text="Nombre del Archivo")
        self.file_tree.heading("size", text="Tamaño")
        self.file_tree.heading("status", text="Estado")
        self.file_tree.column("name", width=260, stretch=True)
        self.file_tree.column("size", width=90, anchor="e")
        self.file_tree.column("status", width=120, anchor="center")
        self.file_tree.grid(row=2, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(files_card, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=2, column=1, sticky="ns")

        self.info_label = ttk.Label(files_card, textvariable=self.media_info, style="CardMuted.TLabel", wraplength=450)
        self.info_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # Right Column: Conversion & Output Controls
        ctrl_card = ttk.Frame(self.tab_convert, style="Card.TFrame", padding=14)
        ctrl_card.grid(row=0, column=1, sticky="nsew")
        ctrl_card.columnconfigure(0, weight=1)

        # Preajustes
        ttk.Label(ctrl_card, text="Perfil / Preajuste Rápido", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(ctrl_card, textvariable=self.preset, values=list(PRESETS.keys()), state="readonly")
        self.preset_combo.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # Format & Quality
        fmt_frame = ttk.Frame(ctrl_card, style="Card.TFrame")
        fmt_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        fmt_frame.columnconfigure(0, weight=1)
        fmt_frame.columnconfigure(1, weight=1)

        ttk.Label(fmt_frame, text="Formato Salida", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.format_combo = ttk.Combobox(fmt_frame, textvariable=self.output_format, values=AUDIO_FORMATS, state="readonly")
        self.format_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0), padx=(0, 6))
        self.format_combo.bind("<<ComboboxSelected>>", lambda _: self._update_convert_button_text())

        ttk.Label(fmt_frame, text="Calidad / Bitrate", style="Section.TLabel").grid(row=0, column=1, sticky="w")
        self.quality_combo = ttk.Combobox(fmt_frame, textvariable=self.audio_quality, values=("128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"), state="readonly")
        self.quality_combo.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        # Resolution & FPS (for Video)
        self.video_opts_frame = ttk.Frame(ctrl_card, style="Card.TFrame")
        self.video_opts_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.video_opts_frame.columnconfigure(0, weight=1)
        self.video_opts_frame.columnconfigure(1, weight=1)

        ttk.Label(self.video_opts_frame, text="Resolución", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.res_combo = ttk.Combobox(self.video_opts_frame, textvariable=self.video_res, values=("Original", "4K (2160p)", "1080p", "720p", "480p"), state="readonly")
        self.res_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0), padx=(0, 6))

        ttk.Label(self.video_opts_frame, text="Framerate (FPS)", style="Section.TLabel").grid(row=0, column=1, sticky="w")
        self.fps_combo = ttk.Combobox(self.video_opts_frame, textvariable=self.video_fps, values=("Original", "60 fps", "30 fps", "24 fps"), state="readonly")
        self.fps_combo.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        # Output Destination
        ttk.Label(ctrl_card, text="Directorio de Salida", style="Section.TLabel").grid(row=4, column=0, sticky="w")
        dest_row = ttk.Frame(ctrl_card, style="Card.TFrame")
        dest_row.grid(row=5, column=0, sticky="ew", pady=(4, 6))
        dest_row.columnconfigure(0, weight=1)
        
        self.folder_entry = ttk.Entry(dest_row, textvariable=self.output_dir)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(dest_row, text="📁", width=3, command=self._choose_folder, style="Secondary.TButton").grid(row=0, column=1)

        cloud_values = ["Carpeta local"] + list(self.cloud_folders.keys())
        self.cloud_combo = ttk.Combobox(ctrl_card, textvariable=self.cloud_target, values=cloud_values, state="readonly")
        self.cloud_combo.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.cloud_combo.bind("<<ComboboxSelected>>", lambda _: self._cloud_changed())

    def _build_advanced_tab(self) -> None:
        self.tab_advanced.columnconfigure(0, weight=1)
        self.tab_advanced.columnconfigure(1, weight=1)

        # Card 1: Edición y Recorte
        trim_card = ttk.Frame(self.tab_advanced, style="Card.TFrame", padding=14)
        trim_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        trim_card.columnconfigure(0, weight=1)
        trim_card.columnconfigure(1, weight=1)

        ttk.Label(trim_card, text="✂️ Recorte de Tiempo (Trim)", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        
        ttk.Label(trim_card, text="Inicio (hh:mm:ss o seg):", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(trim_card, textvariable=self.start_trim).grid(row=2, column=0, sticky="ew", padx=(0, 6), pady=(2, 8))

        ttk.Label(trim_card, text="Fin (hh:mm:ss o seg):", style="CardMuted.TLabel").grid(row=1, column=1, sticky="w")
        ttk.Entry(trim_card, textvariable=self.end_trim).grid(row=2, column=1, sticky="ew", pady=(2, 8))

        ttk.Label(trim_card, text="📦 Compresión a Tamaño Objetivo (MB)", style="Section.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))
        ttk.Entry(trim_card, textvariable=self.target_size_mb).grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Label(trim_card, text="Ejemplo: '25' para Discord, '10' para Email (Calcula bitrate automáticamente)", style="CardMuted.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # Card 2: Rendimiento y Hardware
        perf_card = ttk.Frame(self.tab_advanced, style="Card.TFrame", padding=14)
        perf_card.grid(row=0, column=1, sticky="nsew", pady=(0, 10))

        ttk.Label(perf_card, text="🚀 Rendimiento y Hardware", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        ttk.Checkbutton(perf_card, text="Usar Aceleración GPU si está disponible", variable=self.use_gpu, style="Card.TCheckbutton").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(perf_card, text="Notificaciones Nativas de Windows al terminar", variable=self.enable_toast, style="Card.TCheckbutton").grid(row=2, column=0, sticky="w", pady=4)

        ttk.Label(perf_card, text="Hilos Paralelos por Lote:", style="CardMuted.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 2))
        ttk.Spinbox(perf_card, from_=1, to=8, textvariable=self.parallel_threads, width=10).grid(row=4, column=0, sticky="w")

    def _build_history_tab(self) -> None:
        self.tab_history.columnconfigure(0, weight=1)
        self.tab_history.rowconfigure(1, weight=1)

        top = ttk.Frame(self.tab_history, style="App.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(top, text="Historial de Conversiones Recientes", style="Section.TLabel").pack(side="left")
        ttk.Button(top, text="Limpiar Historial", command=self._clear_history, style="Secondary.TButton").pack(side="right")

        cols = ("file", "format", "size", "time")
        self.history_tree = ttk.Treeview(self.tab_history, columns=cols, show="headings")
        self.history_tree.heading("file", text="Archivo Generado")
        self.history_tree.heading("format", text="Formato")
        self.history_tree.heading("size", text="Tamaño")
        self.history_tree.heading("time", text="Fecha / Hora")
        self.history_tree.column("file", width=260, stretch=True)
        self.history_tree.column("format", width=80, anchor="center")
        self.history_tree.column("size", width=100, anchor="e")
        self.history_tree.column("time", width=140, anchor="center")
        self.history_tree.grid(row=1, column=0, sticky="nsew")

        self.history_tree.bind("<Double-1>", self._open_history_file)
        self._refresh_history_tree()

    def _build_action_area(self) -> None:
        self.convert_button = ttk.Button(self.main, text="Convertir a MP3", command=self._start_conversion, style="Primary.TButton")
        self.convert_button.grid(row=3, column=0, sticky="ew", pady=(10, 8), ipady=10)

        self.progress_canvas = tk.Canvas(self.main, height=12, highlightthickness=0)
        self.progress_canvas.grid(row=4, column=0, sticky="ew")
        self.progress_canvas.bind("<Configure>", lambda _: self._draw_progress_bar())
        self.canvases.append(self.progress_canvas)

        status_row = ttk.Frame(self.main, style="App.TFrame")
        status_row.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        status_row.columnconfigure(1, weight=1)

        self.status_dot = tk.Canvas(status_row, width=18, height=18, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.canvases.append(self.status_dot)

        ttk.Label(status_row, textvariable=self.status, style="Status.TLabel", wraplength=650).grid(row=0, column=1, sticky="w")
        ttk.Label(status_row, text=f"Media Flow v{APP_VERSION}", style="Muted.TLabel").grid(row=0, column=2, sticky="e")
        ttk.Label(status_row, textvariable=self.progress_text, style="Muted.TLabel", wraplength=720).grid(row=1, column=1, columnspan=2, sticky="w", pady=(3, 0))

    def _configure_style(self) -> None:
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        p = self.palette
        self.configure(bg=p["window"])
        self.style.configure("App.TFrame", background=p["window"])
        self.style.configure("Card.TFrame", background=p["surface"], relief="flat")
        self.style.configure("Title.TLabel", background=p["window"], foreground=p["text"], font=("Segoe UI", 20, "bold"))
        self.style.configure("ProBadge.TLabel", background=p["accent_soft"], foreground=p["accent_glow"], font=("Segoe UI", 10, "bold"), padding=(6, 2))
        self.style.configure("Badge.TLabel", background=p["badge_bg"], foreground=p["badge_fg"], font=("Segoe UI", 9, "bold"), padding=(8, 3))
        self.style.configure("Muted.TLabel", background=p["window"], foreground=p["text_muted"], font=("Segoe UI", 9))
        self.style.configure("CardMuted.TLabel", background=p["surface"], foreground=p["text_muted"], font=("Segoe UI", 9))
        self.style.configure("Section.TLabel", background=p["surface"], foreground=p["text"], font=("Segoe UI", 10, "bold"))
        self.style.configure("Status.TLabel", background=p["window"], foreground=p["text"], font=("Segoe UI", 10))
        self.style.configure("Card.TCheckbutton", background=p["surface"], foreground=p["text"], font=("Segoe UI", 10))

        # Entry & Combobox glass styling
        self.style.configure("TEntry", fieldbackground=p["input_bg"], foreground=p["text"], bordercolor=p["card_border"], lightcolor=p["card_border"], darkcolor=p["card_border"], padding=8)
        self.style.configure("TCombobox", fieldbackground=p["input_bg"], foreground=p["text"], bordercolor=p["card_border"], arrowcolor=p["text"], padding=8)
        self.style.map("TCombobox", fieldbackground=[("readonly", p["input_bg"])], foreground=[("readonly", p["text"])])
        self.style.configure("TSpinbox", fieldbackground=p["input_bg"], foreground=p["text"], bordercolor=p["card_border"], padding=6)

        # Primary Action Button (Convertir)
        self.style.configure(
            "Primary.TButton",
            background=p["accent"],
            foreground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            padding=11,
            borderwidth=0,
            relief="flat",
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", p["accent_hover"]), ("disabled", p["card_border"])],
            foreground=[("active", "#ffffff"), ("disabled", p["text_muted"])],
        )

        # Secondary Action Buttons (+ Agregar, Limpiar, Buscar actualizaciones, Modo oscuro, 📁)
        self.style.configure(
            "Secondary.TButton",
            background=p["button_bg"],
            foreground=p["text"],
            font=("Segoe UI", 9, "bold"),
            padding=7,
            borderwidth=1,
            bordercolor=p["card_border"],
            lightcolor=p["card_border"],
            darkcolor=p["card_border"],
            relief="flat",
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", p["button_hover"])],
            foreground=[("active", p["text"])],
        )

        # Notebook Tabs (Convertidor / Ajustes Avanzados / Historial)
        self.style.configure(
            "TNotebook",
            background=p["window"],
            borderwidth=0,
            tabmargins=[2, 5, 2, 0],
        )
        self.style.configure(
            "TNotebook.Tab",
            background=p["surface_alt"],
            foreground=p["text"],
            padding=(16, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=1,
            bordercolor=p["card_border"],
            lightcolor=p["card_border"],
            darkcolor=p["card_border"],
            relief="flat",
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", p["surface"]), ("active", p["button_hover"])],
            foreground=[("selected", p["accent_glow"]), ("active", p["text"])],
            bordercolor=[("selected", p["accent"])],
        )

        # Treeview Glass Table
        self.style.configure("Treeview", background=p["surface"], foreground=p["text"], fieldbackground=p["surface"], rowheight=28, borderwidth=0)
        self.style.configure("Treeview.Heading", background=p["surface_alt"], foreground=p["text"], font=("Segoe UI", 9, "bold"), borderwidth=0)
        self.style.map("Treeview", background=[("selected", p["accent_soft"])], foreground=[("selected", "#ffffff")])

        if hasattr(self, "file_tree"):
            self.file_tree.tag_configure("even", background=p["tree_even"], foreground=p["text"])
            self.file_tree.tag_configure("odd", background=p["tree_odd"], foreground=p["text"])
        if hasattr(self, "history_tree"):
            self.history_tree.tag_configure("even", background=p["tree_even"], foreground=p["text"])
            self.history_tree.tag_configure("odd", background=p["tree_odd"], foreground=p["text"])

    def _apply_theme(self) -> None:
        self._configure_style()
        p = self.palette
        self.theme_button.configure(text="☀️ Modo Claro" if self.theme_name.get() == "dark" else "🌙 Modo Oscuro")
        for c in self.canvases:
            c.configure(bg=p["window"])
        self.logo.configure(bg=p["window"])
        self.progress_canvas.configure(bg=p["window"])
        self.status_dot.configure(bg=p["window"])
        self._draw_logo()
        self._draw_progress_bar()
        self._update_mode_buttons()
        self._draw_status_dot()
        self._refresh_file_tree()
        self._refresh_history_tree()

    def _toggle_theme(self) -> None:
        self.theme_name.set("dark" if self.theme_name.get() == "light" else "light")
        self._apply_theme()
        self._save_settings()

    def _draw_logo(self) -> None:
        p = self.palette
        self.logo.delete("all")
        # Glass sphere badge background
        self.logo.create_oval(1, 1, 41, 41, fill=p["accent_soft"], outline=p["card_border"])
        self.logo.create_oval(3, 3, 39, 39, fill="", outline=p["glass_highlight"], width=1)
        
        # Glowing inner bars
        rounded_rectangle(self.logo, 12, 11, 30, 17, 3, fill=p["accent_glow"], outline="")
        rounded_rectangle(self.logo, 9, 20, 33, 26, 3, fill=p["accent"], outline="")
        rounded_rectangle(self.logo, 15, 29, 27, 34, 3, fill=p["accent_glow"], outline="")

    def _update_mode_buttons(self) -> None:
        p = self.palette
        selected = self.mode.get()
        for mode, button in self.mode_buttons.items():
            is_selected = mode == selected
            button.configure(
                bg=p["accent"] if is_selected else p["surface_alt"],
                fg="#ffffff" if is_selected else p["text"],
                activebackground=p["accent_hover"] if is_selected else p["button_hover"],
                activeforeground="#ffffff" if is_selected else p["text"],
                relief="flat",
                borderwidth=0,
            )

    def _mode_changed(self, mode: str) -> None:
        self.mode.set(mode)
        if mode == "Audio":
            self.format_combo.configure(values=AUDIO_FORMATS)
            if self.output_format.get() not in AUDIO_FORMATS:
                self.output_format.set("MP3")
            self.quality_combo.configure(values=("128 kbps", "160 kbps", "192 kbps", "256 kbps", "320 kbps"), state="readonly")
            self.video_opts_frame.grid_remove()
        elif mode == "Video":
            self.format_combo.configure(values=VIDEO_FORMATS)
            if self.output_format.get() not in VIDEO_FORMATS:
                self.output_format.set("MP4")
            self.quality_combo.configure(values=("Alta", "Equilibrada", "Comprimida"), state="readonly")
            self.video_opts_frame.grid()
        elif mode == "Imagen":
            self.format_combo.configure(values=IMAGE_FORMATS)
            if self.output_format.get() not in IMAGE_FORMATS:
                self.output_format.set("PNG")
            self.quality_combo.configure(values=("100%", "90%", "80%", "70%"), state="readonly")
            self.video_opts_frame.grid_remove()
        elif mode == "Extracción":
            self.format_combo.configure(values=EXTRACTION_MODES)
            self.output_format.set(EXTRACTION_MODES[0])
            self.quality_combo.configure(state="disabled")
            self.video_opts_frame.grid_remove()
        elif mode == "Unir (Concat)":
            self.format_combo.configure(values=CONCAT_MODES)
            self.output_format.set(CONCAT_MODES[0])
            self.quality_combo.configure(state="disabled")
            self.video_opts_frame.grid_remove()

        self._update_convert_button_text()
        self._update_mode_buttons()

    def _on_preset_selected(self, _event: Any) -> None:
        name = self.preset.get()
        opts = PRESETS.get(name, {})
        if not opts:
            return
        if "video_format" in opts:
            self._mode_changed("Video")
            self.output_format.set(opts["video_format"])
            if "video_quality" in opts:
                self.video_quality.set(opts["video_quality"])
                self.quality_combo.set(opts["video_quality"])
            if "res" in opts:
                self.video_res.set(opts["res"])
            if "fps" in opts:
                self.video_fps.set(opts["fps"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])
        elif "audio_format" in opts:
            self._mode_changed("Audio")
            self.output_format.set(opts["audio_format"])
            if "audio_quality" in opts:
                self.audio_quality.set(opts["audio_quality"])
                self.quality_combo.set(opts["audio_quality"])

    def _update_convert_button_text(self) -> None:
        m = self.mode.get()
        fmt = self.output_format.get()
        if m in ("Extracción", "Unir (Concat)"):
            self.convert_button.configure(text=fmt)
        else:
            self.convert_button.configure(text=f"Convertir a {fmt}")

    def _choose_input_file(self) -> None:
        mode = self.mode.get()
        if mode == "Audio":
            filetypes = (("Audio y video", f"{AUDIO_EXTENSIONS} {VIDEO_EXTENSIONS}"), ("Todos los archivos", "*.*"))
        elif mode == "Video":
            filetypes = (("Video", VIDEO_EXTENSIONS), ("Todos los archivos", "*.*"))
        elif mode == "Imagen":
            filetypes = (("Imagen", IMAGE_EXTENSIONS), ("Todos los archivos", "*.*"))
        else:
            filetypes = (("Multimedia", f"{AUDIO_EXTENSIONS} {VIDEO_EXTENSIONS}"), ("Todos los archivos", "*.*"))

        selected = filedialog.askopenfilenames(initialdir=str(default_output_dir()), title="Elegir archivos", filetypes=filetypes)
        if selected:
            for s in selected:
                p = Path(s)
                if p not in self.input_files:
                    self.input_files.append(p)
            self._refresh_file_tree()
            self._probe_selection()

    def _clear_files(self) -> None:
        self.input_files.clear()
        self._refresh_file_tree()
        self.media_info.set("Sin archivos seleccionados.")

    def _refresh_file_tree(self) -> None:
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        for idx, p in enumerate(self.input_files):
            size_str = format_size(p.stat().st_size) if p.exists() else "Desconocido"
            tag = "even" if idx % 2 == 0 else "odd"
            self.file_tree.insert("", "end", values=(p.name, size_str, "Pendiente"), tags=(tag,))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if selected:
            self.output_dir.set(selected)
            self.cloud_target.set("Carpeta local")

    def _cloud_changed(self) -> None:
        selected = self.cloud_target.get()
        if selected in self.cloud_folders:
            self.output_dir.set(str(self.cloud_folders[selected]))

    def _probe_selection(self) -> None:
        files = list(self.input_files)
        if not files:
            self.media_info.set("Sin archivos seleccionados.")
            return
        self.media_info.set("Analizando metadatos...")
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

        return " | ".join(parts)

    def _set_busy(self, value: bool) -> None:
        self.busy = value
        self.convert_button.configure(state="disabled" if value else "normal")
        if value:
            self._animate_progress()
        else:
            self.progress_phase = 0
            self._draw_progress_bar()
        self._draw_status_dot()

    def _draw_progress_bar(self) -> None:
        p = self.palette
        canvas = self.progress_canvas
        canvas.delete("all")
        w = max(canvas.winfo_width(), 1)
        h = max(canvas.winfo_height(), 12)
        # Frosted glass track
        rounded_rectangle(canvas, 0, 0, w, h, 6, fill=p["surface_alt"], outline=p["card_border"])
        rounded_rectangle(canvas, 1, 1, w - 1, h - 1, 5, fill="", outline=p["glass_highlight"])
        if self.busy:
            bw = max(w // 3, 120)
            x = (self.progress_phase % (w + bw)) - bw
            rounded_rectangle(canvas, x, 1, x + bw, h - 1, 5, fill=p["accent"], outline="")
            if x + bw > 0 and x + bw < w:
                canvas.create_oval(x + bw - 6, 2, x + bw, h - 2, fill=p["accent_glow"], outline="")

    def _animate_progress(self) -> None:
        if not self.busy:
            return
        self.progress_phase += 16
        self._draw_progress_bar()
        self.after(35, self._animate_progress)

    def _draw_status_dot(self) -> None:
        p = self.palette
        self.status_dot.delete("all")
        if self.busy:
            self.status_dot.create_oval(1, 1, 17, 17, fill=p["accent_soft"], outline=p["accent_glow"])
            self.status_dot.create_oval(5, 5, 13, 13, fill=p["accent_glow"], outline="")
        else:
            self.status_dot.create_oval(2, 2, 16, 16, fill="#064e3b" if self.theme_name.get() == "dark" else "#d1fae5", outline="")
            self.status_dot.create_oval(5, 5, 13, 13, fill=p["success"], outline="")

    def _start_conversion(self) -> None:
        input_files = list(self.input_files)
        output_dir = Path(self.output_dir.get().strip()).expanduser()
        output_format = self.output_format.get()
        mode = self.mode.get()

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
        self.status.set(f"Iniciando procesado de {len(input_files)} archivo(s)...")
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
                self._concat_files(input_files, out_path, ffmpeg, "Audio" in output_format)
                completed.append(out_path)
            except Exception as exc:
                errors.append(str(exc))
        else:
            max_workers = min(self.parallel_threads.get(), len(input_files))
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

    def _concat_files(self, files: list[Path], output_file: Path, ffmpeg: str, is_audio: bool) -> None:
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
        
        ext_map = {"JPG": "jpg", "H265": "mp4", "AV1": "mp4", "Extraer Audio": "mp3", "Silenciar Video (Quitar Audio)": "mp4", "Extraer Subtítulos (SRT)": "srt"}
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

        # Recorte de tiempo (Trim)
        start_sec = parse_duration_to_seconds(self.start_trim.get())
        end_sec = parse_duration_to_seconds(self.end_trim.get())

        if start_sec is not None:
            cmd.extend(["-ss", str(start_sec)])
        if end_sec is not None:
            cmd.extend(["-to", str(end_sec)])

        cmd.extend(["-i", str(input_file)])

        # Extracción especial
        if mode == "Extracción":
            if output_format == "Extraer Audio":
                return cmd + ["-vn", "-acodec", "libmp3lame", "-q:a", "2", str(output_file)]
            elif output_format == "Silenciar Video (Quitar Audio)":
                return cmd + ["-an", "-vcodec", "copy", str(output_file)]
            elif output_format == "Extraer Subtítulos (SRT)":
                return cmd + ["-map", "0:s:0?", "-c:s", "subrip", str(output_file)]

        # Audio mode
        if mode == "Audio":
            bitrate = f"{self.quality_combo.get().split()[0]}k" if "kbps" in self.quality_combo.get() else "192k"
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
            scale_map = {"4K (2160p)": "3840:2160", "1080p": "1920:1080", "720p": "1280:720", "480p": "854:480"}
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

            # Target size calculation if set
            target_mb = parse_duration_to_seconds(self.target_size_mb.get())
            if target_mb and target_mb > 0:
                cmd.extend(["-fs", f"{int(target_mb * 1024 * 1024)}"])

            # Video encoder selection (GPU vs CPU)
            use_gpu = self.use_gpu.get()
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

    def _add_history_entry(self, file_path: Path, format_name: str) -> None:
        try:
            sz = format_size(file_path.stat().st_size) if file_path.exists() else "N/A"
            tm = time.strftime("%Y-%m-%d %H:%M:%S")
            item = {"file": str(file_path), "format": format_name, "size": sz, "time": tm}
            self.conversion_history.insert(0, item)
            self._save_settings()
            self._refresh_history_tree()
        except Exception:
            pass

    def _refresh_history_tree(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for idx, entry in enumerate(self.conversion_history[:20]):
            tag = "even" if idx % 2 == 0 else "odd"
            self.history_tree.insert("", "end", values=(entry.get("file", ""), entry.get("format", ""), entry.get("size", ""), entry.get("time", "")), tags=(tag,))

    def _open_history_file(self, _event: Any) -> None:
        sel = self.history_tree.selection()
        if sel:
            item = self.history_tree.item(sel[0])
            path_str = item["values"][0]
            if os.path.exists(path_str):
                subprocess.Popen(f'explorer /select,"{path_str}"', shell=True)

    def _clear_history(self) -> None:
        self.conversion_history.clear()
        self._save_settings()
        self._refresh_history_tree()

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
                        self.gpu_label.configure(text=f"GPU: {', '.join(found)} ✔")
                    else:
                        self.gpu_label.configure(text="GPU: CPU Fallback")
                elif kind == "progress":
                    self.progress_text.set(data)
                elif kind == "media_info":
                    self.media_info.set(data)
                elif kind == "done":
                    completed, errors = data
                    self._set_busy(False)
                    self.status.set("Proceso finalizado con éxito.")
                    
                    for c in completed:
                        self._add_history_entry(c, self.output_format.get())
                    
                    if completed:
                        self.progress_text.set(f"Generado(s) {len(completed)} archivo(s) en {completed[0].parent}")
                        if self.enable_toast.get():
                            send_windows_toast("Media Flow Pro", f"¡Conversión completada! {len(completed)} archivos guardados.")
                        messagebox.showinfo(APP_TITLE, f"Conversión completada con éxito.\n\nCarpeta:\n{completed[0].parent}")
                    if errors:
                        messagebox.showwarning(APP_TITLE, f"Ocurrieron algunos errores:\n" + "\n".join(errors))
                elif kind == "error":
                    self._set_busy(False)
                    self.status.set("Error en el proceso.")
                    self.progress_text.set(data)
                    messagebox.showerror(APP_TITLE, data)
                elif kind == "update_downloading":
                    latest_version, release_name, asset_name = data
                    self.status.set(f"Descargando versión {latest_version}...")
                    self.progress_text.set(f"{release_name} - {asset_name}")
                elif kind == "update_installing":
                    latest_version, installer_path = data
                    self.status.set(f"Instalando versión {latest_version}...")
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

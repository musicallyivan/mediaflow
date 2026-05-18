import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional
import tkinter as tk


APP_TITLE = "Media Flow"
APP_VERSION = "1.4.0"
GITHUB_REPO = os.environ.get("MEDIA_CONVERTER_GITHUB_REPO", "musicallyivan/media-converter")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LATEST_RELEASE_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"

AUDIO_FORMATS = ("MP3", "M4A", "WAV", "FLAC", "OGG")
VIDEO_FORMATS = ("MP4", "MOV", "WEBM", "MKV")
IMAGE_FORMATS = ("PNG", "JPG", "WEBP", "BMP")

AUDIO_EXTENSIONS = "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma"
VIDEO_EXTENSIONS = "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.m4v"
IMAGE_EXTENSIONS = "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif"

THEMES = {
    "light": {
        "window": "#eef2f7",
        "surface": "#ffffff",
        "surface_alt": "#f6f8fb",
        "text": "#111827",
        "muted": "#667085",
        "border": "#d8dee8",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_soft": "#dbeafe",
        "success": "#16a34a",
        "danger": "#dc2626",
        "input": "#ffffff",
        "button": "#e8edf3",
        "button_hover": "#dbe3ec",
        "shadow": "#d9e0ea",
    },
    "dark": {
        "window": "#0f172a",
        "surface": "#172033",
        "surface_alt": "#111a2d",
        "text": "#eef2ff",
        "muted": "#a7b1c2",
        "border": "#2d3b52",
        "accent": "#60a5fa",
        "accent_hover": "#3b82f6",
        "accent_soft": "#1e3a5f",
        "success": "#22c55e",
        "danger": "#f87171",
        "input": "#0f172a",
        "button": "#23314a",
        "button_hover": "#2e3f5d",
        "shadow": "#0a1020",
    },
}


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_output_dir() -> Path:
    for candidate in (Path.home() / "Music", Path.home() / "Videos", Path.home() / "Pictures", Path.home() / "Downloads"):
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


class MediaConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("860x680")
        self.minsize(760, 620)

        self.theme_name = tk.StringVar(value="light")
        self.mode = tk.StringVar(value="Audio")
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.output_format = tk.StringVar(value="MP3")
        self.audio_quality = tk.StringVar(value="192 kbps")
        self.video_quality = tk.StringVar(value="Equilibrada")
        self.cloud_target = tk.StringVar(value="Carpeta local")
        self.status = tk.StringVar(value="Elige un archivo para empezar.")
        self.progress_text = tk.StringVar(value="")
        self.cloud_folders = detect_cloud_folders()
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None
        self.mode_buttons: dict[str, tk.Button] = {}
        self.canvases: list[tk.Canvas] = []
        self.busy = False
        self.progress_phase = 0
        self.pulse_phase = 0

        self._build_ui()
        self.after(100, self._poll_messages)
        self.after(120, self._animate_status_dot)
        self.after(1500, lambda: self._check_for_updates(silent=True))

    @property
    def palette(self) -> dict[str, str]:
        return THEMES[self.theme_name.get()]

    def _build_ui(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._configure_style()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.main = ttk.Frame(self, style="App.TFrame", padding=24)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(3, weight=1)

        self._build_header()
        self._build_mode_selector()
        self._build_conversion_card()
        self._build_output_card()
        self._build_action_area()
        self._apply_theme()
        self._mode_changed("Audio")

    def _build_header(self) -> None:
        header = ttk.Frame(self.main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self.logo = tk.Canvas(header, width=48, height=48, highlightthickness=0)
        self.logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))
        self.canvases.append(self.logo)

        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            header,
            text="Convierte audio, video e imagenes. Guarda localmente o en carpetas sincronizadas.",
            style="Muted.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        header_actions = ttk.Frame(header, style="App.TFrame")
        header_actions.grid(row=0, column=2, rowspan=2, sticky="e")
        self.theme_button = ttk.Button(header_actions, text="Modo oscuro", command=self._toggle_theme, style="Secondary.TButton")
        self.theme_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(header_actions, text="Buscar actualizaciones", command=self._check_for_updates, style="Secondary.TButton").grid(row=0, column=1)

    def _build_mode_selector(self) -> None:
        self.mode_card = ttk.Frame(self.main, style="Card.TFrame", padding=8)
        self.mode_card.grid(row=1, column=0, sticky="ew", pady=(22, 16))
        for index, mode in enumerate(("Audio", "Video", "Imagen")):
            self.mode_card.columnconfigure(index, weight=1, uniform="mode")
            button = tk.Button(
                self.mode_card,
                text=mode,
                relief="flat",
                borderwidth=0,
                font=("Segoe UI", 11, "bold"),
                command=lambda value=mode: self._mode_changed(value),
                cursor="hand2",
            )
            button.grid(row=0, column=index, sticky="ew", padx=4, ipady=10)
            self.mode_buttons[mode] = button

    def _build_conversion_card(self) -> None:
        self.content_card = ttk.Frame(self.main, style="Card.TFrame", padding=20)
        self.content_card.grid(row=2, column=0, sticky="ew")
        self.content_card.columnconfigure(0, weight=1)

        ttk.Label(self.content_card, text="Archivo de entrada", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self.content_card, text="Selecciona un archivo local compatible.", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))

        file_row = ttk.Frame(self.content_card, style="Card.TFrame")
        file_row.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        file_row.columnconfigure(0, weight=1)
        self.file_entry = ttk.Entry(file_row, textvariable=self.input_file)
        self.file_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(file_row, text="Elegir archivo", command=self._choose_input_file, style="Secondary.TButton").grid(row=0, column=1, padx=(10, 0))

        options = ttk.Frame(self.content_card, style="Card.TFrame")
        options.grid(row=3, column=0, sticky="ew")
        for column in range(3):
            options.columnconfigure(column, weight=1, uniform="options")

        ttk.Label(options, text="Formato", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.format_combo = ttk.Combobox(options, textvariable=self.output_format, values=AUDIO_FORMATS, state="readonly")
        self.format_combo.grid(row=1, column=0, sticky="ew", pady=(6, 0), padx=(0, 10))
        self.format_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_convert_button_text())

        ttk.Label(options, text="Calidad de audio", style="Section.TLabel").grid(row=0, column=1, sticky="w")
        self.audio_quality_combo = ttk.Combobox(
            options,
            textvariable=self.audio_quality,
            values=("128 kbps", "192 kbps", "256 kbps", "320 kbps"),
            state="readonly",
        )
        self.audio_quality_combo.grid(row=1, column=1, sticky="ew", pady=(6, 0), padx=(0, 10))

        ttk.Label(options, text="Calidad visual", style="Section.TLabel").grid(row=0, column=2, sticky="w")
        self.visual_quality_combo = ttk.Combobox(
            options,
            textvariable=self.video_quality,
            values=("Alta", "Equilibrada", "Comprimida"),
            state="readonly",
        )
        self.visual_quality_combo.grid(row=1, column=2, sticky="ew", pady=(6, 0))

    def _build_output_card(self) -> None:
        self.output_card = ttk.Frame(self.main, style="Card.TFrame", padding=20)
        self.output_card.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.output_card.columnconfigure(0, weight=1)

        ttk.Label(self.output_card, text="Destino", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        cloud_text = "Las carpetas sincronizadas aparecen aqui si el cliente oficial esta instalado."
        ttk.Label(self.output_card, text=cloud_text, style="CardMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))

        destination_row = ttk.Frame(self.output_card, style="Card.TFrame")
        destination_row.grid(row=2, column=0, sticky="ew")
        destination_row.columnconfigure(1, weight=1)

        cloud_values = ["Carpeta local"] + list(self.cloud_folders.keys())
        self.cloud_combo = ttk.Combobox(destination_row, textvariable=self.cloud_target, values=cloud_values, state="readonly", width=18)
        self.cloud_combo.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.cloud_combo.bind("<<ComboboxSelected>>", lambda _event: self._cloud_changed())

        self.folder_entry = ttk.Entry(destination_row, textvariable=self.output_dir)
        self.folder_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(destination_row, text="Elegir carpeta", command=self._choose_folder, style="Secondary.TButton").grid(row=0, column=2, padx=(10, 0))

        detected = ", ".join(self.cloud_folders.keys()) if self.cloud_folders else "No se han detectado carpetas de nube."
        self.cloud_status = ttk.Label(self.output_card, text=f"Detectado: {detected}", style="CardMuted.TLabel")
        self.cloud_status.grid(row=3, column=0, sticky="w", pady=(12, 0))

    def _build_action_area(self) -> None:
        self.convert_button = ttk.Button(self.main, text="Convertir a MP3", command=self._start_conversion, style="Primary.TButton")
        self.convert_button.grid(row=4, column=0, sticky="ew", pady=(18, 10), ipady=8)

        self.progress_canvas = tk.Canvas(self.main, height=12, highlightthickness=0)
        self.progress_canvas.grid(row=5, column=0, sticky="ew")
        self.progress_canvas.bind("<Configure>", lambda _event: self._draw_progress_bar())
        self.canvases.append(self.progress_canvas)

        status_row = ttk.Frame(self.main, style="App.TFrame")
        status_row.grid(row=6, column=0, sticky="ew", pady=(14, 0))
        status_row.columnconfigure(1, weight=1)

        self.status_dot = tk.Canvas(status_row, width=18, height=18, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.canvases.append(self.status_dot)
        ttk.Label(status_row, textvariable=self.status, style="Status.TLabel", wraplength=650).grid(row=0, column=1, sticky="w")
        ttk.Label(status_row, text=f"Version {APP_VERSION}", style="Muted.TLabel").grid(row=0, column=2, sticky="e")
        ttk.Label(status_row, textvariable=self.progress_text, style="Muted.TLabel", wraplength=720).grid(row=1, column=1, columnspan=2, sticky="w", pady=(5, 0))

    def _configure_style(self) -> None:
        palette = self.palette
        self.configure(bg=palette["window"])
        self.style.configure("App.TFrame", background=palette["window"])
        self.style.configure("Card.TFrame", background=palette["surface"], relief="flat")
        self.style.configure("Title.TLabel", background=palette["window"], foreground=palette["text"], font=("Segoe UI", 24, "bold"))
        self.style.configure("Muted.TLabel", background=palette["window"], foreground=palette["muted"], font=("Segoe UI", 9))
        self.style.configure("CardMuted.TLabel", background=palette["surface"], foreground=palette["muted"], font=("Segoe UI", 9))
        self.style.configure("Section.TLabel", background=palette["surface"], foreground=palette["text"], font=("Segoe UI", 10, "bold"))
        self.style.configure("Status.TLabel", background=palette["window"], foreground=palette["text"], font=("Segoe UI", 10))
        self.style.configure("TEntry", fieldbackground=palette["input"], foreground=palette["text"], bordercolor=palette["border"], lightcolor=palette["border"], darkcolor=palette["border"], padding=8)
        self.style.configure("TCombobox", fieldbackground=palette["input"], foreground=palette["text"], bordercolor=palette["border"], arrowcolor=palette["text"], padding=8)
        self.style.map("TCombobox", fieldbackground=[("readonly", palette["input"])], foreground=[("readonly", palette["text"])])
        self.style.configure("Primary.TButton", background=palette["accent"], foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=11, borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", palette["accent_hover"]), ("disabled", palette["border"])])
        self.style.configure("Secondary.TButton", background=palette["button"], foreground=palette["text"], padding=9, borderwidth=0)
        self.style.map("Secondary.TButton", background=[("active", palette["button_hover"])])

    def _apply_theme(self) -> None:
        self._configure_style()
        palette = self.palette
        self.theme_button.configure(text="Modo claro" if self.theme_name.get() == "dark" else "Modo oscuro")
        for canvas in self.canvases:
            canvas.configure(bg=palette["window"])
        self.logo.configure(bg=palette["window"])
        self.progress_canvas.configure(bg=palette["window"])
        self.status_dot.configure(bg=palette["window"])
        self._draw_logo()
        self._draw_progress_bar()
        self._update_mode_buttons()
        self._draw_status_dot()

    def _toggle_theme(self) -> None:
        self.theme_name.set("dark" if self.theme_name.get() == "light" else "light")
        self._apply_theme()

    def _draw_logo(self) -> None:
        palette = self.palette
        self.logo.delete("all")
        self.logo.create_oval(2, 2, 46, 46, fill=palette["accent_soft"], outline=palette["accent"])
        self.logo.create_rectangle(15, 14, 33, 20, fill=palette["accent"], outline="")
        self.logo.create_rectangle(12, 24, 36, 30, fill=palette["accent_hover"], outline="")
        self.logo.create_rectangle(18, 34, 30, 39, fill=palette["accent"], outline="")

    def _update_mode_buttons(self) -> None:
        palette = self.palette
        selected = self.mode.get()
        for mode, button in self.mode_buttons.items():
            is_selected = mode == selected
            button.configure(
                bg=palette["accent"] if is_selected else palette["surface_alt"],
                fg="#ffffff" if is_selected else palette["text"],
                activebackground=palette["accent_hover"] if is_selected else palette["button_hover"],
                activeforeground="#ffffff" if is_selected else palette["text"],
            )

    def _mode_changed(self, mode: str) -> None:
        self.mode.set(mode)
        if mode == "Audio":
            self.format_combo.configure(values=AUDIO_FORMATS)
            self.output_format.set("MP3")
            self.audio_quality_combo.configure(state="readonly")
            self.visual_quality_combo.configure(state="disabled")
            self.status.set("Elige un archivo de audio o video para extraer o convertir audio.")
        elif mode == "Video":
            self.format_combo.configure(values=VIDEO_FORMATS)
            self.output_format.set("MP4")
            self.audio_quality_combo.configure(state="readonly")
            self.visual_quality_combo.configure(state="readonly", values=("Alta", "Equilibrada", "Comprimida"))
            if self.video_quality.get() not in ("Alta", "Equilibrada", "Comprimida"):
                self.video_quality.set("Equilibrada")
            self.status.set("Elige un archivo de video para convertirlo a otro contenedor o codec.")
        else:
            self.format_combo.configure(values=IMAGE_FORMATS)
            self.output_format.set("PNG")
            self.audio_quality_combo.configure(state="disabled")
            self.visual_quality_combo.configure(state="readonly", values=("100", "90", "80", "70"))
            if self.video_quality.get() not in ("100", "90", "80", "70"):
                self.video_quality.set("90")
            self.status.set("Elige una imagen para convertirla a otro formato.")
        self._update_convert_button_text()
        self._update_mode_buttons()
        self._draw_status_dot()

    def _update_convert_button_text(self) -> None:
        self.convert_button.configure(text=f"Convertir a {self.output_format.get()}")

    def _choose_input_file(self) -> None:
        mode = self.mode.get()
        if mode == "Audio":
            filetypes = (("Audio y video", f"{AUDIO_EXTENSIONS} {VIDEO_EXTENSIONS}"), ("Todos los archivos", "*.*"))
        elif mode == "Video":
            filetypes = (("Video", VIDEO_EXTENSIONS), ("Todos los archivos", "*.*"))
        else:
            filetypes = (("Imagen", IMAGE_EXTENSIONS), ("Todos los archivos", "*.*"))

        selected = filedialog.askopenfilename(initialdir=str(default_output_dir()), title="Elegir archivo", filetypes=filetypes)
        if selected:
            self.input_file.set(selected)
            self.progress_text.set(Path(selected).name)

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if selected:
            self.output_dir.set(selected)
            self.cloud_target.set("Carpeta local")

    def _cloud_changed(self) -> None:
        selected = self.cloud_target.get()
        if selected in self.cloud_folders:
            self.output_dir.set(str(self.cloud_folders[selected]))

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
        palette = self.palette
        canvas = self.progress_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 12)
        canvas.create_rectangle(0, 0, width, height, fill=palette["surface_alt"], outline=palette["border"])
        if self.busy:
            block_width = max(width // 3, 120)
            x = (self.progress_phase % (width + block_width)) - block_width
            canvas.create_rectangle(x, 0, x + block_width, height, fill=palette["accent"], outline="")

    def _animate_progress(self) -> None:
        if not self.busy:
            return
        self.progress_phase += 16
        self._draw_progress_bar()
        self.after(35, self._animate_progress)

    def _draw_status_dot(self) -> None:
        palette = self.palette
        self.status_dot.delete("all")
        color = palette["accent"] if self.busy else palette["success"]
        self.status_dot.create_oval(4, 4, 14, 14, fill=color, outline="")

    def _animate_status_dot(self) -> None:
        palette = self.palette
        self.pulse_phase = (self.pulse_phase + 1) % 28
        radius = 4 + abs(14 - self.pulse_phase) / 7
        center = 9
        color = palette["accent"] if self.busy else palette["success"]
        self.status_dot.delete("all")
        self.status_dot.create_oval(center - radius, center - radius, center + radius, center + radius, fill=color, outline="")
        self.after(120 if self.busy else 180, self._animate_status_dot)

    def _start_conversion(self) -> None:
        input_file = Path(self.input_file.get().strip()).expanduser()
        output_dir = Path(self.output_dir.get().strip()).expanduser()
        output_format = self.output_format.get()

        if not input_file.exists() or not input_file.is_file():
            messagebox.showwarning(APP_TITLE, "Elige primero un archivo valido.")
            return
        if not output_dir.exists() or not output_dir.is_dir():
            messagebox.showwarning(APP_TITLE, "La carpeta de salida no existe.")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(
                APP_TITLE,
                "No encuentro ffmpeg.\n\n"
                "Instala ffmpeg con instalar_requisitos.bat y vuelve a abrir esta ventana, "
                "o copia ffmpeg.exe dentro de esta carpeta.",
            )
            return

        self._set_busy(True)
        self.status.set(f"Convirtiendo a {output_format}...")
        self.progress_text.set("Preparando archivo de salida.")
        self.worker = threading.Thread(
            target=self._convert,
            args=(self.mode.get(), input_file, output_dir, ffmpeg, output_format),
            daemon=True,
        )
        self.worker.start()

    def _check_for_updates(self, silent: bool = False) -> None:
        if "/" not in GITHUB_REPO:
            if not silent:
                messagebox.showinfo(APP_TITLE, "Todavia falta configurar el repositorio de GitHub en app.py.")
            return
        if self.update_worker and self.update_worker.is_alive():
            return
        self.update_worker = threading.Thread(target=self._check_for_updates_worker, args=(silent,), daemon=True)
        self.update_worker.start()

    def _check_for_updates_worker(self, silent: bool) -> None:
        try:
            release = fetch_latest_release()
            latest_version = str(release.get("tag_name") or "").strip()
            release_url = str(release.get("html_url") or LATEST_RELEASE_PAGE)
            release_name = str(release.get("name") or latest_version)
            if latest_version and is_newer_version(latest_version, APP_VERSION):
                self.messages.put(("update_available", (latest_version, release_name, release_url)))
            elif not silent:
                self.messages.put(("update_current", "Ya tienes la ultima version disponible."))
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            if not silent:
                self.messages.put(("update_error", f"No se pudo comprobar si hay actualizaciones.\n\n{exc}"))

    def _convert(self, mode: str, input_file: Path, output_dir: Path, ffmpeg: str, output_format: str) -> None:
        try:
            extension = "jpg" if output_format == "JPG" else output_format.lower()
            output_file = unique_output_path(output_dir, f"{input_file.stem} convertido", extension)
            command = self._build_ffmpeg_command(mode, ffmpeg, input_file, output_file, output_format)

            self.messages.put(("progress", f"Creando {output_file.name}"))
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            _, stderr = process.communicate()
            if process.returncode != 0:
                detail = stderr.strip().splitlines()[-1] if stderr.strip() else "ffmpeg no pudo convertir el archivo."
                raise RuntimeError(detail)
            self.messages.put(("done", output_file))
        except Exception as exc:
            text = str(exc)
            if "ffmpeg" in text.lower():
                text = "ffmpeg no pudo convertir este archivo. Comprueba que el archivo no este danado y que el formato sea compatible."
            self.messages.put(("error", text))

    def _build_ffmpeg_command(self, mode: str, ffmpeg: str, input_file: Path, output_file: Path, output_format: str) -> list[str]:
        base = [ffmpeg, "-y", "-i", str(input_file)]
        bitrate = f"{self.audio_quality.get().split()[0]}k"

        if mode == "Audio":
            codec_map = {
                "MP3": ["-vn", "-codec:a", "libmp3lame", "-b:a", bitrate],
                "M4A": ["-vn", "-codec:a", "aac", "-b:a", bitrate],
                "WAV": ["-vn", "-codec:a", "pcm_s16le"],
                "FLAC": ["-vn", "-codec:a", "flac"],
                "OGG": ["-vn", "-codec:a", "libvorbis", "-b:a", bitrate],
            }
            return base + codec_map[output_format] + [str(output_file)]

        if mode == "Video":
            crf = {"Alta": "18", "Equilibrada": "23", "Comprimida": "28"}.get(self.video_quality.get(), "23")
            if output_format == "WEBM":
                return base + ["-c:v", "libvpx-vp9", "-crf", crf, "-b:v", "0", "-c:a", "libopus", "-b:a", bitrate, str(output_file)]
            return base + ["-c:v", "libx264", "-preset", "medium", "-crf", crf, "-c:a", "aac", "-b:a", bitrate, "-movflags", "+faststart", str(output_file)]

        image_quality = self.video_quality.get()
        quality_args = []
        if output_format in ("JPG", "WEBP"):
            qscale = {"100": "2", "90": "4", "80": "8", "70": "12"}.get(image_quality, "4")
            quality_args = ["-q:v", qscale]
        return base + ["-frames:v", "1"] + quality_args + [str(output_file)]

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, text = self.messages.get_nowait()
                if kind == "progress":
                    self.progress_text.set(text)
                elif kind == "done":
                    output_file = Path(text)
                    self._set_busy(False)
                    self.status.set("Conversion completada.")
                    self.progress_text.set(str(output_file))
                    messagebox.showinfo(APP_TITLE, f"Listo:\n{output_file}")
                elif kind == "error":
                    self._set_busy(False)
                    self.status.set("No se pudo convertir el archivo.")
                    self.progress_text.set(text)
                    messagebox.showerror(APP_TITLE, text)
                elif kind == "update_available":
                    latest_version, release_name, release_url = text
                    should_open = messagebox.askyesno(
                        APP_TITLE,
                        "Hay una nueva version disponible.\n\n"
                        f"Version instalada: {APP_VERSION}\n"
                        f"Version nueva: {latest_version}\n"
                        f"{release_name}\n\n"
                        "Quieres abrir la pagina de descarga?",
                    )
                    if should_open:
                        webbrowser.open(release_url)
                elif kind == "update_current":
                    messagebox.showinfo(APP_TITLE, text)
                elif kind == "update_error":
                    messagebox.showerror(APP_TITLE, text)
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)


if __name__ == "__main__":
    app = MediaConverterApp()
    app.mainloop()

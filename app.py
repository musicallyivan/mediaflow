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


APP_TITLE = "Convertidor Multimedia"
APP_VERSION = "1.2.0"
GITHUB_REPO = os.environ.get("MEDIA_CONVERTER_GITHUB_REPO", "musicallyivan/media-converter")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LATEST_RELEASE_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"

AUDIO_FORMATS = ("MP3", "M4A", "WAV", "FLAC", "OGG")
VIDEO_FORMATS = ("MP4", "MOV", "WEBM", "MKV")
IMAGE_FORMATS = ("PNG", "JPG", "WEBP", "BMP")

AUDIO_EXTENSIONS = "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma"
VIDEO_EXTENSIONS = "*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.m4v"
IMAGE_EXTENSIONS = "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif"


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
            "User-Agent": f"media-converter/{APP_VERSION}",
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
        self.geometry("760x610")
        self.minsize(680, 560)
        self.configure(bg="#f4f6f8")

        self.mode = tk.StringVar(value="Audio")
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.output_format = tk.StringVar(value="MP3")
        self.audio_quality = tk.StringVar(value="192 kbps")
        self.video_quality = tk.StringVar(value="Equilibrada")
        self.image_quality = tk.StringVar(value="90")
        self.cloud_target = tk.StringVar(value="Carpeta local")
        self.status = tk.StringVar(value="Elige un archivo para empezar.")
        self.progress_text = tk.StringVar(value="")
        self.cloud_folders = detect_cloud_folders()
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None

        self._build_ui()
        self.after(100, self._poll_messages)
        self.after(1500, lambda: self._check_for_updates(silent=True))

    def _build_ui(self) -> None:
        self._configure_style()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, style="App.TFrame", padding=24)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text=APP_TITLE, style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(header, text="Convierte audio, video e imagenes. Guarda localmente o en carpetas sincronizadas.", style="Muted.TLabel")
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        update_button = ttk.Button(header, text="Buscar actualizaciones", command=self._check_for_updates, style="Secondary.TButton")
        update_button.grid(row=0, column=1, rowspan=2, sticky="e")

        mode_row = ttk.Frame(main, style="Card.TFrame", padding=10)
        mode_row.grid(row=1, column=0, sticky="ew", pady=(22, 16))
        for index, mode in enumerate(("Audio", "Video", "Imagen")):
            mode_row.columnconfigure(index, weight=1)
            button = ttk.Radiobutton(
                mode_row,
                text=mode,
                value=mode,
                variable=self.mode,
                command=self._mode_changed,
                style="Mode.TRadiobutton",
            )
            button.grid(row=0, column=index, sticky="ew", padx=3)

        content = ttk.Frame(main, style="Card.TFrame", padding=18)
        content.grid(row=2, column=0, sticky="ew")
        content.columnconfigure(0, weight=1)

        file_label = ttk.Label(content, text="Archivo de entrada", style="Section.TLabel")
        file_label.grid(row=0, column=0, sticky="w")

        file_row = ttk.Frame(content, style="Card.TFrame")
        file_row.grid(row=1, column=0, sticky="ew", pady=(6, 16))
        file_row.columnconfigure(0, weight=1)

        file_entry = ttk.Entry(file_row, textvariable=self.input_file)
        file_entry.grid(row=0, column=0, sticky="ew")

        file_button = ttk.Button(file_row, text="Elegir archivo", command=self._choose_input_file)
        file_button.grid(row=0, column=1, padx=(10, 0))

        options = ttk.Frame(content, style="Card.TFrame")
        options.grid(row=2, column=0, sticky="ew")
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        options.columnconfigure(2, weight=1)

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

        output = ttk.Frame(main, style="Card.TFrame", padding=18)
        output.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        output.columnconfigure(0, weight=1)

        ttk.Label(output, text="Destino", style="Section.TLabel").grid(row=0, column=0, sticky="w")

        destination_row = ttk.Frame(output, style="Card.TFrame")
        destination_row.grid(row=1, column=0, sticky="ew", pady=(6, 12))
        destination_row.columnconfigure(1, weight=1)

        cloud_values = ["Carpeta local"] + list(self.cloud_folders.keys())
        self.cloud_combo = ttk.Combobox(destination_row, textvariable=self.cloud_target, values=cloud_values, state="readonly", width=18)
        self.cloud_combo.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.cloud_combo.bind("<<ComboboxSelected>>", lambda _event: self._cloud_changed())

        folder_entry = ttk.Entry(destination_row, textvariable=self.output_dir)
        folder_entry.grid(row=0, column=1, sticky="ew")

        folder_button = ttk.Button(destination_row, text="Elegir carpeta", command=self._choose_folder)
        folder_button.grid(row=0, column=2, padx=(10, 0))

        self.convert_button = ttk.Button(main, text="Convertir a MP3", command=self._start_conversion, style="Primary.TButton")
        self.convert_button.grid(row=4, column=0, sticky="ew", pady=(18, 10), ipady=8)

        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.grid(row=5, column=0, sticky="ew")

        status_row = ttk.Frame(main, style="App.TFrame")
        status_row.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        status_row.columnconfigure(0, weight=1)

        ttk.Label(status_row, textvariable=self.status, style="Status.TLabel", wraplength=620).grid(row=0, column=0, sticky="w")
        ttk.Label(status_row, text=f"Version {APP_VERSION}", style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(status_row, textvariable=self.progress_text, style="Muted.TLabel", wraplength=620).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self._mode_changed()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f4f6f8")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#16202a", font=("Segoe UI", 22, "bold"))
        style.configure("Muted.TLabel", background="#f4f6f8", foreground="#647282", font=("Segoe UI", 9))
        style.configure("Section.TLabel", background="#ffffff", foreground="#2b3642", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background="#f4f6f8", foreground="#2b3642", font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor="#c9d2dc", padding=7)
        style.configure("TCombobox", fieldbackground="#ffffff", bordercolor="#c9d2dc", padding=7)
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=10)
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#9fb7ee")])
        style.configure("Secondary.TButton", background="#e8edf3", foreground="#26313d", padding=8)
        style.map("Secondary.TButton", background=[("active", "#dbe3ec")])
        style.configure("Mode.TRadiobutton", background="#ffffff", foreground="#2b3642", padding=10, indicatorcolor="#ffffff")

    def _mode_changed(self) -> None:
        mode = self.mode.get()
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

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if selected:
            self.output_dir.set(selected)
            self.cloud_target.set("Carpeta local")

    def _cloud_changed(self) -> None:
        selected = self.cloud_target.get()
        if selected in self.cloud_folders:
            self.output_dir.set(str(self.cloud_folders[selected]))

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

        self.convert_button.configure(state="disabled")
        self.progress.start(12)
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
                    self.progress.stop()
                    self.convert_button.configure(state="normal")
                    self.status.set("Conversion completada.")
                    self.progress_text.set(str(output_file))
                    messagebox.showinfo(APP_TITLE, f"Listo:\n{output_file}")
                elif kind == "error":
                    self.progress.stop()
                    self.convert_button.configure(state="normal")
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

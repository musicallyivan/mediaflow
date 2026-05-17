import json
import os
import queue
import shutil
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional


APP_TITLE = "Descargar YouTube a MP3/MP4"
APP_VERSION = "1.0.1"
GITHUB_REPO = os.environ.get("YTMP3_GITHUB_REPO", "musicallyivan/youtube-mp3-downloader")
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LATEST_RELEASE_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_download_dir() -> Path:
    music = Path.home() / "Music"
    downloads = Path.home() / "Downloads"
    if music.exists():
        return music
    if downloads.exists():
        return downloads
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
        Path.home()
        / "AppData"
        / "Local"
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "ffmpeg-8.0-full_build"
        / "bin"
        / "ffmpeg.exe",
    ]
    for root in program_files:
        if root:
            candidates.extend(
                [
                    root / "ffmpeg" / "bin" / "ffmpeg.exe",
                    root / "Gyan" / "FFmpeg" / "bin" / "ffmpeg.exe",
                ]
            )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    winget_packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        for candidate in winget_packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"):
            if candidate.exists():
                return str(candidate)
    return None


def selected_cookie_options(browser: str, cookies_file: str) -> dict:
    if browser != "Ninguno":
        return {"cookiesfrombrowser": (browser.lower(),)}
    if cookies_file:
        return {"cookiefile": str(Path(cookies_file).expanduser())}
    return {}


def javascript_runtime_options() -> dict:
    node = shutil.which("node")
    if node:
        return {"js_runtimes": {"node": {"path": node}}}
    deno = shutil.which("deno")
    if deno:
        return {"js_runtimes": {"deno": {"path": deno}}}
    return {}


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
            "User-Agent": f"youtube-mp3-downloader/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


class YouTubeMp3App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("620x560")
        self.minsize(560, 530)

        self.output_dir = tk.StringVar(value=str(default_download_dir()))
        self.url = tk.StringVar()
        self.download_format = tk.StringVar(value="MP3")
        self.audio_quality = tk.StringVar(value="192 kbps")
        self.browser_cookies = tk.StringVar(value="Ninguno")
        self.cookies_file = tk.StringVar(value="")
        self.status = tk.StringVar(value="Pega un enlace de YouTube para empezar.")
        self.progress_text = tk.StringVar(value="")
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.update_worker: Optional[threading.Thread] = None

        self._build_ui()
        self.after(100, self._poll_messages)
        self.after(1500, lambda: self._check_for_updates(silent=True))

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=24)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)

        title = ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        url_label = ttk.Label(main, text="Enlace del video")
        url_label.grid(row=1, column=0, sticky="w", pady=(22, 6))

        url_entry = ttk.Entry(main, textvariable=self.url, font=("Segoe UI", 11))
        url_entry.grid(row=2, column=0, sticky="ew")
        url_entry.focus()

        folder_label = ttk.Label(main, text="Carpeta de destino")
        folder_label.grid(row=3, column=0, sticky="w", pady=(18, 6))

        folder_row = ttk.Frame(main)
        folder_row.grid(row=4, column=0, sticky="ew")
        folder_row.columnconfigure(0, weight=1)

        folder_entry = ttk.Entry(folder_row, textvariable=self.output_dir)
        folder_entry.grid(row=0, column=0, sticky="ew")

        folder_button = ttk.Button(folder_row, text="Elegir...", command=self._choose_folder)
        folder_button.grid(row=0, column=1, padx=(8, 0))

        format_label = ttk.Label(main, text="Formato y calidad de audio")
        format_label.grid(row=5, column=0, sticky="w", pady=(18, 6))

        format_row = ttk.Frame(main)
        format_row.grid(row=6, column=0, sticky="ew")
        format_row.columnconfigure(1, weight=1)

        format_combo = ttk.Combobox(
            format_row,
            textvariable=self.download_format,
            values=("MP3", "MP4"),
            state="readonly",
            width=12,
        )
        format_combo.grid(row=0, column=0, sticky="w")
        format_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_download_button_text())

        quality_combo = ttk.Combobox(
            format_row,
            textvariable=self.audio_quality,
            values=("128 kbps", "192 kbps", "256 kbps", "320 kbps"),
            state="readonly",
            width=12,
        )
        quality_combo.grid(row=0, column=1, sticky="w", padx=(8, 0))

        cookies_label = ttk.Label(main, text="Cookies de YouTube (si YouTube pide iniciar sesion)")
        cookies_label.grid(row=7, column=0, sticky="w", pady=(18, 6))

        cookies_row = ttk.Frame(main)
        cookies_row.grid(row=8, column=0, sticky="ew")
        cookies_row.columnconfigure(1, weight=1)

        browser_combo = ttk.Combobox(
            cookies_row,
            textvariable=self.browser_cookies,
            values=("Ninguno", "Chrome", "Edge", "Firefox"),
            state="readonly",
            width=12,
        )
        browser_combo.grid(row=0, column=0, sticky="w")

        cookies_entry = ttk.Entry(cookies_row, textvariable=self.cookies_file)
        cookies_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        cookies_button = ttk.Button(cookies_row, text="cookies.txt...", command=self._choose_cookies_file)
        cookies_button.grid(row=0, column=2, padx=(8, 0))

        self.download_button = ttk.Button(
            main,
            text="Descargar MP3",
            command=self._start_download,
        )
        self.download_button.grid(row=9, column=0, sticky="ew", pady=(24, 8), ipady=6)

        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.grid(row=10, column=0, sticky="ew", pady=(4, 8))

        status = ttk.Label(main, textvariable=self.status, wraplength=540)
        status.grid(row=11, column=0, sticky="w")

        progress_detail = ttk.Label(main, textvariable=self.progress_text, foreground="#555555")
        progress_detail.grid(row=12, column=0, sticky="w", pady=(6, 0))

        footer = ttk.Frame(main)
        footer.grid(row=13, column=0, sticky="ew", pady=(20, 0))
        footer.columnconfigure(0, weight=1)

        version_label = ttk.Label(footer, text=f"Version {APP_VERSION}", foreground="#666666")
        version_label.grid(row=0, column=0, sticky="w")

        update_button = ttk.Button(footer, text="Buscar actualizaciones", command=self._check_for_updates)
        update_button.grid(row=0, column=1, sticky="e")

    def _update_download_button_text(self) -> None:
        self.download_button.configure(text=f"Descargar {self.download_format.get()}")

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if selected:
            self.output_dir.set(selected)

    def _choose_cookies_file(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=str(app_dir()),
            title="Elegir cookies.txt",
            filetypes=(("Cookies", "*.txt"), ("Todos los archivos", "*.*")),
        )
        if selected:
            self.cookies_file.set(selected)

    def _start_download(self) -> None:
        url = self.url.get().strip()
        output_dir = Path(self.output_dir.get()).expanduser()
        download_format = self.download_format.get()
        audio_quality = self.audio_quality.get().split()[0]
        browser = self.browser_cookies.get()
        cookies_file = self.cookies_file.get().strip()
        using_cookies_file = browser == "Ninguno" and bool(cookies_file)

        if not url:
            messagebox.showwarning(APP_TITLE, "Pega primero un enlace de YouTube.")
            return
        if not output_dir.exists():
            messagebox.showwarning(APP_TITLE, "La carpeta de destino no existe.")
            return
        if using_cookies_file and not Path(cookies_file).expanduser().exists():
            messagebox.showwarning(APP_TITLE, "El archivo cookies.txt no existe.")
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

        self.download_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set(f"Descargando {download_format} con audio a {audio_quality} kbps...")
        self.progress_text.set("")

        self.worker = threading.Thread(
            target=self._download,
            args=(url, str(output_dir), ffmpeg, browser, cookies_file, download_format, audio_quality),
            daemon=True,
        )
        self.worker.start()

    def _check_for_updates(self, silent: bool = False) -> None:
        if "/" not in GITHUB_REPO:
            if not silent:
                messagebox.showinfo(
                    APP_TITLE,
                    "Todavia falta configurar el repositorio de GitHub en app.py para poder buscar actualizaciones.",
                )
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

    def _download(
        self,
        url: str,
        output_dir: str,
        ffmpeg: str,
        browser: str,
        cookies_file: str,
        download_format: str,
        audio_quality: str,
    ) -> None:
        try:
            import yt_dlp

            ffmpeg_dir = str(Path(ffmpeg).resolve().parent)
            extension = download_format.lower()

            def hook(data: dict) -> None:
                status = data.get("status")
                if status == "downloading":
                    percent = data.get("_percent_str", "").strip()
                    speed = data.get("_speed_str", "").strip()
                    eta = data.get("_eta_str", "").strip()
                    detail = " ".join(part for part in [percent, speed, f"ETA {eta}" if eta else ""] if part)
                    self.messages.put(("progress", detail))
                elif status == "finished":
                    if download_format == "MP3":
                        self.messages.put(("progress", "Convirtiendo a MP3..."))
                    else:
                        self.messages.put(("progress", "Preparando MP4..."))

            options = {
                "outtmpl": os.path.join(output_dir, "%(title).200B.%(ext)s"),
                "noplaylist": True,
                "ffmpeg_location": ffmpeg_dir,
                "progress_hooks": [hook],
                "quiet": True,
                "no_warnings": True,
                "retries": 5,
                "fragment_retries": 5,
                "windowsfilenames": True,
            }
            if download_format == "MP3":
                options.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": audio_quality,
                            }
                        ],
                    }
                )
            else:
                options.update(
                    {
                        "format": (
                            f"bv*[ext=mp4]+ba[ext=m4a][abr<={audio_quality}]/"
                            f"bv*[ext=mp4]+ba[abr<={audio_quality}]/"
                            f"b[ext=mp4][abr<={audio_quality}]/"
                            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best"
                        ),
                        "merge_output_format": "mp4",
                    }
                )
            options.update(selected_cookie_options(browser, cookies_file))
            options.update(javascript_runtime_options())

            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(url, download=True)
                title = info.get("title") or "video"

            self.messages.put(("done", (title, extension)))
        except ModuleNotFoundError:
            self.messages.put(
                (
                    "error",
                    "Falta instalar yt-dlp. Ejecuta instalar_y_abrir.bat o usa: pip install -r requirements.txt",
                )
            )
        except Exception as exc:
            text = str(exc)
            lowered = text.lower()
            if "sign in to confirm" in lowered or "not a bot" in lowered or "cookies" in lowered:
                text = (
                    "No se han podido usar las cookies de YouTube.\n\n"
                    "Prueba primero esto:\n"
                    "1. Inicia sesion en YouTube en el navegador elegido.\n"
                    "2. Cierra todas las ventanas de ese navegador.\n"
                    "3. Abre el Administrador de tareas y termina los procesos que queden de Chrome, Edge o Firefox.\n"
                    "4. Vuelve a abrir este programa y descarga otra vez.\n\n"
                    "Si sigue fallando, usa la opcion mas fiable: exporta las cookies de YouTube en formato Netscape "
                    "a un archivo cookies.txt, seleccionalo con el boton cookies.txt... y deja el navegador en Ninguno."
                )
            elif "ffmpeg" in lowered:
                text = (
                    "ffmpeg no esta instalado o no se puede ejecutar.\n\n"
                    "Ejecuta instalar_requisitos.bat, cierra esta ventana y vuelve a abrir instalar_y_abrir.bat. "
                    "Tambien puedes copiar ffmpeg.exe dentro de la carpeta del programa."
                )
            self.messages.put(("error", text))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, text = self.messages.get_nowait()
                if kind == "progress":
                    self.progress_text.set(text)
                elif kind == "done":
                    title, extension = text
                    self.progress.stop()
                    self.download_button.configure(state="normal")
                    self.status.set(f"Listo: {title}")
                    self.progress_text.set(f"El archivo {extension.upper()} esta en la carpeta elegida.")
                    messagebox.showinfo(APP_TITLE, f"Listo: {title}")
                elif kind == "error":
                    self.progress.stop()
                    self.download_button.configure(state="normal")
                    self.status.set("No se pudo descargar el archivo.")
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
    app = YouTubeMp3App()
    app.mainloop()

# 💻 Compilación y Guía de Desarrollo

Esta guía detalla la arquitectura del proyecto, la ejecución desde el código fuente y las instrucciones para generar instaladores ejecutable `.exe` y paquetes `MSIX`.

---

## 🛠️ Requisitos del Sistema

1. **Windows 10 o Windows 11**.
2. **Python 3.10** o superior.
3. **FFmpeg / FFprobe** (colocados en la raíz del proyecto o agregados al `PATH` de Windows).

---

## 🚀 Ejecución desde el Código Fuente

1. Clona el repositorio oficial de GitHub:
   ```cmd
   git clone https://github.com/musicallyivan/mediaflow.git
   cd mediaflow
   ```
2. Ejecuta el script de requisitos si es necesario:
   ```cmd
   instalar_requisitos.bat
   ```
3. Inicia la aplicación directamente con Python:
   ```cmd
   python app.py
   ```

---

## 📦 Generación de Ejecutables (.exe) e Instaladores

### 1. Empaquetar con PyInstaller
Para crear un archivo binario standalone con PyInstaller:
```cmd
pyinstaller --noconsole --onefile --name="MediaFlow" --icon="assets/icon-300.ico" app.py
```

### 2. Generar Instalador de Windows con Inno Setup
El repositorio incluye el archivo de configuración `installer.iss` preparado para **Inno Setup**:

1. Abre `installer.iss` con Inno Setup Compiler.
2. Haz clic en **Compile** (o presiona `Ctrl + F9`).
3. El instalador ejecutable guiado se generará en la carpeta `packaging/output/`.

---

## 📂 Estructura del Proyecto

* **`app.py`** — Aplicación principal de escritorio con interfaz gráfica Tkinter Pro (Glassmorphism), hilos multihilo y llamadas a FFmpeg.
* **`website/`** — Sitio web oficial del proyecto con convertidor WebAssembly en línea y política de privacidad.
* **`android-app/`** — Versión nativa para Android compilada en Kotlin con FFmpegKit.
* **`installer.iss`** — Script de compilación de instalador guiado para Windows.
* **`STORE_LISTING.md`** — Textos de ficha oficial preparados para Microsoft Partner Center.

---

## 📱 Versión Nativa para Android (`android-app/`)

En la carpeta `android-app/` se encuentra el proyecto nativo para dispositivos Android:
* Desarrollado en Android Studio con Kotlin nativo (sin WebView).
* Utiliza el selector de archivos del sistema Android.
* Procesa conversiones en segundo plano mediante `FFmpegKit`.

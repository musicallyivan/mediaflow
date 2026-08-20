# ❓ Preguntas Frecuentes (FAQ)

Respuestas a las dudas más habituales sobre el funcionamiento, privacidad y solución de problemas en **Media Flow Pro**.

---

### 🔒 Privacidad y Seguridad

#### ¿Media Flow sube mis archivos a algún servidor en Internet?
**No.** Media Flow procesa el 100% de tus archivos de forma estrictamente local en la memoria y almacenamiento de tu propio ordenador utilizando `FFmpeg`.

#### ¿Requiere crear cuenta o iniciar sesión?
**No.** La aplicación no solicita correos electrónicos, contraseñas ni suscripciones de ningún tipo.

#### ¿Funciona sin conexión a Internet?
**Sí.** Todas las herramientas de conversión, recorte, compresión y extracción funcionan perfectamente sin conexión a Internet (offline).

---

### ☁️ Carpetas Sincronizadas y Nube

#### ¿Cómo funciona la sincronización con OneDrive, Google Drive o iCloud Drive?
Media Flow no pide credenciales de nube. Detecta si las carpetas oficiales de OneDrive, Google Drive o iCloud están instaladas en tu equipo Windows. Al elegir una de ellas como destino, Media Flow guarda el archivo en esa carpeta física local y tu cliente oficial instalado se encarga de subirlo a la nube.

---

### ⚡ Rendimiento y Solución de Problemas

#### ¿Qué hago si la app dice que no encuentra FFmpeg?
Si ejecutas la app desde el código fuente sin empaquetar, puedes descargar `ffmpeg.exe` y colocarlo en la misma carpeta que `app.py` o ejecutar el script `instalar_requisitos.bat`. En las versiones empaquetadas (`.exe` instalador o paquete `MSIX`), FFmpeg viene incluido automáticamente.

#### ¿Por qué un archivo GIF ocupa más espacio que el video original?
El formato GIF fue creado en 1987 y no posee algoritmos modernos de compresión de video. Para clips de más de 10 segundos, se recomienda utilizar el formato **MP4** o **WEBM** para mantener un peso reducido.

#### ¿Cómo se actualiza la aplicación?
* **Instalador `.exe`:** La app comprueba automáticamente las releases de GitHub. Si hay una versión nueva, descarga el instalador y lo ejecuta en segundo plano.
* **Microsoft Store / MSIX:** La actualización se gestiona de forma totalmente transparente a través de Windows App Installer o Microsoft Store.

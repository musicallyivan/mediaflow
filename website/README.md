# Media Flow — Sitio Web Renovado (Estilo Apple.com)

Página web oficial de presentación para **Media Flow Suite**, diseñada con la estética de **Apple.com**: tipografía San Francisco (`-apple-system`), efectos de cristal esmerilado (*frosted glass blur*), paleta oscura cinematográfica y animaciones cinéticas fluidas en scroll, widgets y carruseles.

---

## 🌟 Características de Diseño

1. **Tipografía y Estética Apple**:
   - Pila tipográfica `-apple-system, BlinkMacSystemFont, "SF Pro Display"`.
   - Contraste de texto y kerning calibrado al milímetro con gradientes monocromáticos y acentos en azul Apple (`#0071e3`).
   - Botones tipo *pill* con radios redondeados de 980px y microinteracciones de escala.

2. **Animaciones Cinéticas ("Que se mueven")**:
   - **Aurora Fluida de Fondo**: Resplandor dinámico animado en el fondo del Hero.
   - **Ticker Marquee Infinito**: Cinta continua de formatos de audio, video y codecs que se desplazan de forma ininterrumpida.
   - **Efecto Parallax 3D**: Las tarjetas responden al cursor del ratón con inclinación tridimensional e iluminación dinámica de foco.
   - **Revelación con Scroll**: Elementos que aparecen suavemente con curvas elásticas de Apple (`cubic-bezier(0.16, 1, 0.3, 1)`).
   - **Contadores Numéricos Animados**: Conteo en vivo de métricas de rendimiento (10x, 4K 60fps, 100% Local).
   - **Visualizador de Audio en Tiempo Real**: Barras de ecualizador de espectro sonoro animadas dinámicamente.

3. **Simulador / Playground de Conversión Interactivo**:
   - Widget interactivo que permite al visitante alternar archivos de prueba, elegir formatos de salida (MP4, H.265, AV1, FLAC, MP3), iniciar una conversión simulada y ver el progreso con métricas de tasa de fotogramas y velocidad en megabytes por segundo.

4. **Visor de Interfaz con Cambio de Modo**:
   - Maqueta interactiva que permite alternar instantáneamente entre la vista en **Modo Oscuro** y **Modo Claro** del software.

5. **Hub de Descargas Multiplataforma**:
   - Tarjetas dedicadas para **Windows 11 & 10** (Instalador .exe, Portable .zip, Microsoft Store) y **Linux** (.tar.gz, GitHub y ejecución con `python3 linux_app.py`).

---

## 🚀 Cómo Visualizar o Alojar la Web

### En Local (Navegador)
Abre directamente `G:\mediaflow-web\index.html` con cualquier navegador web (Chrome, Edge, Firefox, Safari) o usa un servidor local rápido:

```bash
# Con Python
cd G:\mediaflow-web
python -m http.server 8080
```
Y abre en tu navegador: `http://localhost:8080`

### Despliegue en Producción
Compatible sin build steps con:
- **GitHub Pages**
- **Vercel**
- **Netlify**
- **Cloudflare Pages**

# 🚀 Aceleración por Hardware (GPU)

Media Flow Pro incluye detección y codificación acelerada por hardware de manera nativa. Esto permite delegar la conversión pesada de video en el chip dedicado de tu tarjeta gráfica en lugar de saturar el procesador (CPU).

---

## 💻 Tarjetas Gráficas y Encoders Compatibles

| Fabricante | Tecnología de Codificación | Encoders Detectados por Media Flow |
| :--- | :--- | :--- |
| **NVIDIA** | NVIDIA NVENC | `h264_nvenc`, `hevc_nvenc` |
| **AMD** | AMD AMF / VCE | `h264_amf`, `hevc_amf` |
| **Intel** | Intel QuickSync (QSV) | `h264_qsv`, `hevc_qsv` |

---

## 🔍 ¿Cómo Saber si la Aceleración por GPU Está Activa?

Al iniciar la aplicación, Media Flow realiza un análisis silencioso en segundo plano ejecutando `ffmpeg -encoders`.

* En la esquina superior derecha de la ventana verás la etiqueta de estado:
  * **`GPU: NVENC ✔`** — Tarjeta NVIDIA detectada y activa.
  * **`GPU: AMF ✔`** — Tarjeta AMD detectada y activa.
  * **`GPU: QSV ✔`** — Procesador Intel con GPU integrada activo.
  * **`GPU: CPU Fallback`** — Si no hay GPU compatible, se utiliza codificación limpia por procesador (`libx264`/`libx265`).

---

## ⚡ Ventajas de Usar la GPU

1. **Velocidad Hasta 10x Mayor:** Conversiones de películas o clips largos en cuestión de segundos.
2. **Menor Consumo de CPU:** Tu ordenador se mantendrá fluido sin congelarse ni sobrecalentarse mientras convierte en segundo plano.
3. **Conversión Paralela por Lotes:** Procesa múltiples videos simultáneamente combinando la GPU con hilos multihilo.

---

## ⚙️ Cómo Activar o Desactivar la Aceleración por GPU

1. Abre la pestaña **`⚙️ Ajustes Avanzados`**.
2. Marca o desmarca la casilla **"Usar Aceleración GPU si está disponible"**.
3. Las preferencias se guardan automáticamente para futuras ejecuciones.

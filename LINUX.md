# Media Flow en Linux

Media Flow comparte el mismo motor de conversión de la versión de escritorio de Windows, pero dispone de un punto de entrada específico para Linux.

## Compatibilidad

- Linux x86_64.
- X11 o Wayland.
- Python 3.13 para desarrollo.
- FFmpeg y FFprobe se incluyen en los paquetes generados por GitHub Actions.

## Desarrollo local

Instala las dependencias de `requirements.txt` y FFmpeg desde los repositorios de tu distribución. Después ejecuta:

```bash
python3 linux_app.py
```

## Paquete descargable

Las releases incluyen `media-flow-vX.Y.Z-linux-x86_64.tar.gz`.

Extrae el archivo y ejecuta:

```bash
chmod +x media-flow
./media-flow
```

La versión Linux no muestra la compra de Microsoft Store, ya que Microsoft Store solo está disponible en Windows. La activación PRO mediante clave de licencia y Stripe sigue disponible.

Las actualizaciones de Linux se distribuyen mediante GitHub Releases.

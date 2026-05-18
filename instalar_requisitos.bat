@echo off
setlocal

echo Instalando Python 3 y ffmpeg con winget...
echo Puede que Windows pida permisos de administrador.
echo.

winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements

echo.
echo Cierra esta ventana y abre instalar_y_abrir.bat.
pause

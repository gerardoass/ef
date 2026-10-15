@echo off
cd /d "%~dp0"
echo ====================================================
echo      COMPILANDO NETGUARD (MODO PRODUCCION)
echo ====================================================
echo.

:: 1. Limpieza estricta de residuos locales previos
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

:: 2. Comando de compilacion llamando al modulo de Python directamente
python -m PyInstaller ^
  --noconfirm --clean --onefile --windowed --uac-admin ^
  --icon "icono.ico" ^
  --name "NetGuard" ^
  --collect-all scapy ^
  --collect-all customtkinter ^
  --hidden-import scapy.arch.windows ^
  --hidden-import scapy.layers.12 ^
  --hidden-import scapy.layers.inet ^
  --hidden-import PIL._tkinter_finder ^
  --exclude-module matplotlib ^
  --exclude-module numpy.testing ^
  main.py

echo.
echo ====================================================
echo      PROCESO TERMINADO. REVISA LA CARPETA "DIST"
echo ====================================================
pause

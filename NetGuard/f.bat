@echo off
setlocal
cd /d "%~dp0"

echo ===========================================
echo  NetGuard - Compilacion Directa con Icono
echo ===========================================
echo.

echo [1/2] Borrando cache de analisis y residuos...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q ui\__pycache__ 2>nul
rmdir /s /q core\__pycache__ 2>nul
rmdir /s /q __pycache__ 2>nul

echo [2/2] Compilando con PyInstaller (Sin UPX)...
echo.

:: Comando directo inyectando el icono y forzando las carpetas internas
python -m PyInstaller --clean --noconfirm --onefile --windowed --noupx --icon="icono.ico" --hidden-import=scapy.all --hidden-import=customtkinter --hidden-import=ui.theme --hidden-import=ui.console --hidden-import=ui.app --hidden-import=core.scanner --hidden-import=core.arp --hidden-import=core.flood --hidden-import=core.latency main.py

if errorlevel 1 goto err

echo.
echo ===========================================
echo  OK -> dist\NetGuard.exe creado con exito!
echo ===========================================
pause
exit /b 0

:err
echo.
echo ===========================================
echo  FALLO EN EL BUILD (revisa las lineas de arriba)
echo ===========================================
pause
exit /b 1

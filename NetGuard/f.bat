@echo off
cd /d "%~dp0"
echo ===========================================
echo   EJECUTANDO DIAGNOSTICO DE PYINSTALLER
echo ===========================================
echo.

:: Borrar cualquier residuo corrupto previo
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

:: Intentar compilar en modo consola puro para ver el error
python -m PyInstaller --clean --noconfirm --onefile --console main.py

echo.
echo ===========================================
echo   REVISA LAS LINEAS DE ARRIBA PARA VER EL ERROR
echo ===========================================
pause

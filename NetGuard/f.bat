@echo off
setlocal
cd /d "%~dp0"

echo ===========================================
echo  NetGuard - build limpio del ejecutable
echo ===========================================
echo.

echo [1/2] Borrando cache de analisis y bytecode...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q ui\__pycache__ 2>nul
rmdir /s /q core\__pycache__ 2>nul
rmdir /s /q __pycache__ 2>nul

echo [2/2] Compilando con PyInstaller...
echo.
python -m PyInstaller --clean --noconfirm netguard.spec
if errorlevel 1 goto err

echo.
echo ===========================================
echo  OK -> dist\NetGuard.exe
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

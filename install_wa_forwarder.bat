@echo off
chcp 65001 > nul
title Instalador – WhatsApp Forwarder

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║       Instalador del WhatsApp Forwarder              ║
echo ║  Reenvío automático de imágenes y archivos           ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Verificar que Python está instalado
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo         Descárgalo desde https://python.org
    pause
    exit /b 1
)

echo [OK] Python detectado:
python --version
echo.

:: Instalar dependencias de Python
echo [1/3] Instalando dependencias Python...
pip install -r requirements_wa.txt
if %errorlevel% neq 0 (
    echo [ERROR] Falló la instalación de dependencias. Revisa tu conexión a internet.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.
echo.

:: Instalar Chromium para Playwright
echo [2/3] Instalando Chromium para Playwright (puede tardar varios minutos)...
playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Falló la instalación de Chromium.
    echo         Intenta ejecutar manualmente: playwright install chromium
    pause
    exit /b 1
)
echo [OK] Chromium instalado.
echo.

:: Crear acceso directo en el Inicio
echo [3/3] Creando acceso directo en el menú de inicio...
set SCRIPT_DIR=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

:: Usar PowerShell para crear el acceso directo
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WScriptShell = New-Object -ComObject WScript.Shell; ^
   $Shortcut = $WScriptShell.CreateShortcut('%STARTUP_DIR%\WAForwarder.lnk'); ^
   $Shortcut.TargetPath = 'pythonw.exe'; ^
   $Shortcut.Arguments = '%SCRIPT_DIR%wa_forwarder.pyw'; ^
   $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; ^
   $Shortcut.Description = 'WhatsApp Forwarder'; ^
   $Shortcut.Save()"

if %errorlevel% neq 0 (
    echo [ADVERTENCIA] No se pudo crear el acceso directo de inicio automático.
    echo              Puedes iniciarlo manualmente con doble clic en wa_forwarder.pyw
) else (
    echo [OK] Acceso directo creado en: %STARTUP_DIR%\WAForwarder.lnk
    echo      El forwarder se iniciará automáticamente al iniciar Windows.
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║            ✅ Instalación completada                 ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  PRÓXIMOS PASOS:                                     ║
echo ║                                                      ║
echo ║  1. Haz doble clic en  wa_forwarder.pyw             ║
echo ║  2. Aparecerá un ícono "W" en la bandeja del sistema ║
echo ║  3. Clic derecho → ⚙️ Configurar grupos              ║
echo ║  4. Ingresa los nombres EXACTOS de los grupos        ║
echo ║  5. Clic derecho → ▶ Iniciar Monitor                 ║
echo ║  6. Escanea el QR de WhatsApp en el navegador        ║
echo ║     (solo la primera vez)                            ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause

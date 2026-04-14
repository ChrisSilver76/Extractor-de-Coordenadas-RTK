@echo off
:: ============================================================
::  compilar.bat — Extractor de Coordenadas RTK  v1.2.0
::  Autor: ChrisSilver76
::
::  INSTRUCCIONES:
::    1. Coloca este .bat junto a extractor_rtk.py e Icono.ico en:
::       C:\Users\chris\OneDrive\Desktop\Extractor_de_Coordenadas_RTK\
::    2. Doble clic en compilar.bat
::    3. El .exe aparece en:  dist\Extractor de Coordenadas RTK.exe
::
::  REQUISITOS PREVIOS (solo la primera vez):
::    pip install pyinstaller customtkinter tkinterdnd2
::    (pandas YA NO es necesario — fue reemplazado por stdlib csv)
::
::  TAMANIO ESPERADO DEL .EXE: ~35-50 MB  (antes: ~200 MB con pandas)
:: ============================================================

title Compilando Extractor de Coordenadas RTK...
echo.
echo  ==========================================================
echo   EXTRACTOR DE COORDENADAS RTK  --  Compilador PyInstaller
echo  ==========================================================
echo.

:: ── 1. Verificar PyInstaller ──────────────────────────────────
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] PyInstaller no encontrado. Ejecuta:
    echo          pip install pyinstaller
    echo.
    pause
    exit /b 1
)
echo  [OK] PyInstaller encontrado.

:: ── 2. Verificar que el icono existe ─────────────────────────
if not exist "Icono.ico" (
    echo  [ADVERTENCIA] Icono.ico no encontrado. Compilando sin icono.
    set "ICON_FLAG="
    set "ICON_DATA="
) else (
    echo  [OK] Icono.ico encontrado.
    set "ICON_FLAG=--icon=Icono.ico"
    set "ICON_DATA=--add-data Icono.ico;."
)

:: ── 3. Limpiar compilaciones anteriores ──────────────────────
echo.
echo  [1/3] Limpiando compilaciones anteriores...
if exist "build\"    rmdir /s /q build
if exist "dist\"     rmdir /s /q dist
if exist "*.spec"    del /q *.spec
echo  Listo.

:: ── 4. Compilar ───────────────────────────────────────────────
::
::  NOTA SOBRE EL TAMANIO:
::  pandas fue eliminado del codigo — ya no se importa.
::  Esto reduce el .exe de ~200 MB a ~35-50 MB.
::
::  --collect-data customtkinter  incluye los temas JSON de CTk
::  --hidden-import tkinterdnd2   incluye DnD si esta instalado
::  NO se incluyen hidden-imports de pandas (ya no se usa)
::
echo.
echo  [2/3] Compilando... (puede tardar 1-3 minutos)
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Extractor de Coordenadas RTK" ^
    %ICON_FLAG% ^
    %ICON_DATA% ^
    --collect-data customtkinter ^
    --hidden-import tkinterdnd2 ^
    extractor_rtk.py

:: ── 5. Verificar resultado ────────────────────────────────────
echo.
if exist "dist\Extractor de Coordenadas RTK.exe" (
    echo  [3/3] Compilacion exitosa!
    echo.
    echo  Ejecutable generado en:
    echo    dist\Extractor de Coordenadas RTK.exe
    echo.
    for %%F in ("dist\Extractor de Coordenadas RTK.exe") do (
        echo  Tamano del .exe: %%~zF bytes
    )
    echo.
    echo  Puedes borrar las carpetas build\ y __pycache__
) else (
    echo  [ERROR] La compilacion fallo.
    echo  Revisa los mensajes anteriores en busca de errores.
    echo  Tip: ejecuta el .bat desde CMD para ver el log completo.
)

echo.
echo  ==========================================================
pause

@echo off
chcp 65001 >nul
title Neutron AI - Build EXE
cd /d "%~dp0"

echo ============================================
echo   Sestaveni Neutron AI do .exe (PyInstaller)
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python neni nainstalovany nebo neni v PATH.
    echo Stahni ho z https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Kontroluji PyInstaller...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Instaluji PyInstaller...
    python -m pip install pyinstaller
)

echo.
echo Kontroluji llama-cpp-python (pro lokalni modely)...
python -c "import llama_cpp" >nul 2>nul
if errorlevel 1 (
    echo [INFO] llama-cpp-python neni nainstalovany.
    echo        Exe pak nebude umet lokalni .gguf modely, jen online API.
    echo        Pro pridani podpory: pip install llama-cpp-python
    set COLLECT=
) else (
    set COLLECT=--collect-all llama_cpp
)

echo.
echo Sestavuji exe, chvili to potrva...
echo.

python -m PyInstaller --onefile --console --name "NeutronAI" %COLLECT% neutron-ai.py

echo.
if exist "dist\NeutronAI.exe" (
    echo Kopiruji settings.json a slozku models do dist\ ...
    if not exist "dist\settings.json" copy /y "settings.json" "dist\settings.json" >nul
    if not exist "dist\models" mkdir "dist\models"
    echo ============================================
    echo  Hotovo! Najdes: dist\NeutronAI.exe
    echo.
    echo  Do dist\models vloz sve .gguf modely.
    echo  API klice doplnis do dist\settings.json
    echo ============================================
) else (
    echo Sestaveni se nezdarilo, zkontroluj hlasky vyse.
)

pause
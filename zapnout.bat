@echo off
chcp 65001 >nul
title Neutron AI
cd /d "%~dp0"

if exist "NeutronAI.exe" (
    NeutronAI.exe
    goto end
)

if exist "dist\NeutronAI.exe" (
    cd dist
    NeutronAI.exe
    goto end
)

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python neni nainstalovany nebo neni v PATH.
        echo Stahni ho z https://www.python.org/downloads/
        pause
        exit /b 1
    )
    py neutron-ai.py
) else (
    python neutron-ai.py
)

:end
pause
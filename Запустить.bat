@echo off
setlocal
title LavochkaBBS - close this window to stop the bot
cd /d "%~dp0"

if exist "dist\quickexit\xlamBOT\xlamBOT.exe" (
    "dist\quickexit\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\counters\xlamBOT\xlamBOT.exe" (
    "dist\counters\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\encoding\xlamBOT\xlamBOT.exe" (
    "dist\encoding\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\selection\xlamBOT\xlamBOT.exe" (
    "dist\selection\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\roster\xlamBOT\xlamBOT.exe" (
    "dist\roster\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\current\xlamBOT\xlamBOT.exe" (
    "dist\current\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\repaired\xlamBOT\xlamBOT.exe" (
    "dist\repaired\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist "dist\xlamBOT\xlamBOT.exe" (
    "dist\xlamBOT\xlamBOT.exe"
    pause
    exit /b 0
)

if exist ".venv\Scripts\python.exe" goto dependencies

py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 (
    py -3.11 -m venv .venv
    if errorlevel 1 goto failed
    goto dependencies
)
python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed

:dependencies
if exist ".venv\xlambot-ready" goto launch
echo Preparing xlamBOT. The first launch needs internet and may take several minutes.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo ready>".venv\xlambot-ready"

:launch
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failed
exit /b 0

:missing_python
echo Install Python 3.11.9 for Windows from:
echo https://www.python.org/downloads/release/python-3119/
echo Choose Windows installer (64-bit) and enable Add python.exe to PATH.
echo Then close this window and open this file again.
pause
exit /b 1

:failed
echo.
echo xlamBOT could not start. Keep this window open to read the error above.
pause
exit /b 1

@echo off
setlocal
title LavochkaBBS - bot console
cd /d "%~dp0"

rem Prefer current sources when their dependencies are already installed.
if not exist ".venv\Scripts\python.exe" goto packaged
".venv\Scripts\python.exe" -c "import adbutils, av, cv2, discord, flask, numpy, onnxruntime, requests, toml, PIL, Crypto, pytesseract" >nul 2>&1
if not errorlevel 1 goto source

:packaged
for %%D in (account-profile cpu-fallback quickexit counters encoding selection roster current repaired) do (
    if exist "dist\%%D\xlamBOT\xlamBOT.exe" (
        set "BOT_PROGRAM=dist\%%D\xlamBOT\xlamBOT.exe"
        goto launch
    )
)
if exist "dist\xlamBOT\xlamBOT.exe" (
    set "BOT_PROGRAM=dist\xlamBOT\xlamBOT.exe"
    goto launch
)
if exist ".venv\Scripts\python.exe" goto dependencies

py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if errorlevel 1 goto system_python
py -3.11 -m venv .venv
if errorlevel 1 goto failed
goto dependencies

:system_python
python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed

:dependencies
echo Preparing xlamBOT. The first launch needs internet and may take several minutes.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo ready>".venv\xlambot-ready"

:source
set "BOT_PROGRAM=.venv\Scripts\python.exe"
set "BOT_SOURCE=-Source"

:launch
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-bot.ps1" -Program "%BOT_PROGRAM%" %BOT_SOURCE%
set "BOT_EXIT_CODE=%errorlevel%"
echo.
echo Bot stopped. Exit code: %BOT_EXIT_CODE%. Details are saved in the logs folder.
pause
exit /b %BOT_EXIT_CODE%

:missing_python
echo Install Python 3.11.9 for Windows from:
echo https://www.python.org/downloads/release/python-3119/
echo Choose Windows installer (64-bit) and enable Add python.exe to PATH.
pause
exit /b 1

:failed
echo.
echo xlamBOT could not start. Keep this window open to read the error above.
pause
exit /b 1

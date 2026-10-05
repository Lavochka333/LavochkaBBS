@echo off
setlocal
cd /d "%~dp0"
title LavochkaBBS - Stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-bot.ps1"
pause

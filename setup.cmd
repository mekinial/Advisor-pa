@echo off
rem Windows setup for the Advisor PA kit (runs setup.ps1; no administrator rights needed).
rem   setup                     first-time setup
rem   setup background          turn on the background jobs (after Telegram works)
rem   setup remove-background   turn them off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
if "%~1"=="" pause

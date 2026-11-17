@echo off
rem Run one of the PA's tools with the PA's own Python (Windows PowerShell / Command Prompt):
rem   pa telegram_post main "Hello"      (= Tools\telegram_post.py)
rem   pa .claude\skills\financial-health-check\scripts\health_check.py <file>
setlocal
set "DIR=%~dp0"
set "PY=%DIR%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=py"
if "%~1"=="" (
  echo usage: pa ^<tool^> [args]   tools:
  for %%f in ("%DIR%Tools\*.py") do if /I not "%%~nf"=="pa_config" echo   %%~nf
  exit /b 1
)
set "T=%~1"
set "F=%DIR%Tools\%T%.py"
if /I "%T:~-3%"==".py" (set "F=%T%" & if not exist "%T%" set "F=%DIR%%T%")
shift
set "ARGS="
:loop
if "%~1"=="" goto run
set ARGS=%ARGS% %1
shift
goto loop
:run
"%PY%" -X utf8 "%F%" %ARGS%

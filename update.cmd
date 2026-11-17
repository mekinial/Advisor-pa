@echo off
rem Get the latest version of the PA kit on Windows (double-click, or run "update" in this folder).
rem Uses Git Bash, which comes with Git for Windows (Claude Code needs it too).
setlocal
set "B=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%B%" set "B=%LocalAppData%\Programs\Git\bin\bash.exe"
if not exist "%B%" (
  echo Git for Windows was not found. Install it:  winget install --id Git.Git -e
  pause & exit /b 1
)
"%B%" "%~dp0update.sh"
if "%~1"=="" pause

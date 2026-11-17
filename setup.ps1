# One-time setup on a Windows PC (the Windows version of setup.sh). Safe to run again: never overwrites their own files.
# Run it through setup.cmd (double-click, or type the line in PowerShell / Command Prompt inside this folder):
#   setup.cmd                     Python environment, folders, their own config/template files
#   setup.cmd background          background jobs: Telegram line at sign-in (Startup folder shortcut), watchdog every
#                                 5 min, Drive sync every 10 min, WhatsApp check 4:07am (if on), all in Task Scheduler.
#                                 Run this AFTER Telegram is set up and tested.
#   setup.cmd remove-background   turn those background jobs off again
# Nothing here needs administrator rights, and no system or security setting is changed.
param([string]$Mode = "")
if ($Mode -eq "nopause") { $Mode = "" }
$ErrorActionPreference = "Continue"   # native tools (py, pip) write notes to stderr; exit codes are checked instead
$Dir = $PSScriptRoot
Set-Location $Dir
$Py = Join-Path $Dir ".venv\Scripts\python.exe"
$PyW = Join-Path $Dir ".venv\Scripts\pythonw.exe"
$Tasks = @("AdvisorPA watchdog", "AdvisorPA Drive sync", "AdvisorPA WhatsApp check")
$Startup = Join-Path ([Environment]::GetFolderPath("Startup")) "AdvisorPA Telegram line.lnk"

function Say($t) { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# Background jobs are made with schtasks.exe and a task definition file: it works on every Windows 10/11 PC without
# administrator rights (the ScheduledTasks PowerShell commands are missing or broken on some PCs). Each job runs as
# them, only while they are signed in, with no window (pythonw), also on battery.
function X($s) { [Security.SecurityElement]::Escape($s) }
function Add-Job($name, $script, $argsLine, $trigger, [switch]$Disabled) {
    $arguments = ("-X utf8 `"" + (Join-Path $Dir "Tools\$script") + "`" " + $argsLine).Trim()
    $enabled = if ($Disabled) { "false" } else { "true" }
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>$(X "Advisor PA kit ($Dir). Turn off: setup.cmd remove-background")</Description></RegistrationInfo>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>$enabled</Enabled>
  </Settings>
  <Triggers>$trigger</Triggers>
  <Actions Context="Author"><Exec>
    <Command>$(X $PyW)</Command><Arguments>$(X $arguments)</Arguments><WorkingDirectory>$(X $Dir)</WorkingDirectory>
  </Exec></Actions>
</Task>
"@
    $f = Join-Path $env:TEMP "advisorpa-task.xml"
    [IO.File]::WriteAllText($f, $xml, [Text.Encoding]::Unicode)
    $out = & schtasks.exe /Create /TN $name /XML $f /F 2>&1
    Remove-Item $f -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) { Write-Host "  on: $name" } else { Write-Host "  FAILED: $name  ($out)"; $script:failed = $true }
}

function Every($minutes) {   # starts in a minute, repeats for ever
    $start = (Get-Date).AddMinutes(1).ToString("yyyy-MM-ddTHH:mm:00")
    "<TimeTrigger><StartBoundary>$start</StartBoundary><Repetition><Interval>PT$($minutes)M</Interval></Repetition></TimeTrigger>"
}

function Daily($hhmm) {
    "<CalendarTrigger><StartBoundary>2026-01-01T$($hhmm):00</StartBoundary><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>"
}

function Remove-Job($name) {
    & schtasks.exe /Query /TN $name 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { & schtasks.exe /Delete /TN $name /F 2>&1 | Out-Null }
    Write-Host "  off: $name"
}

if ($Mode -eq "background") {
    if (-not (Test-Path $PyW)) { Write-Host "Run setup.cmd first (no .venv yet)."; exit 1 }
    New-Item -ItemType Directory -Force (Join-Path $Dir "Drafts\Status") | Out-Null
    Say "Turning on background jobs"
    $sh = New-Object -ComObject WScript.Shell
    $lnk = $sh.CreateShortcut($Startup)
    $lnk.TargetPath = $PyW
    $lnk.Arguments = "-X utf8 `"" + (Join-Path $Dir "Tools\line.py") + "`" start"
    $lnk.WorkingDirectory = $Dir
    $lnk.Description = "Starts the Advisor PA Telegram line at sign-in (hidden)"
    $lnk.Save()
    Write-Host "  on: Telegram line at sign-in (Startup folder shortcut)"
    Add-Job "AdvisorPA watchdog" "telegram_watchdog.py" "" (Every 5)
    Add-Job "AdvisorPA Drive sync" "drive_sync.py" "" (Every 10)
    & $Py -c "import sys; sys.path.insert(0, 'Tools'); import pa_config as C; sys.exit(0 if C.CFG['whatsapp'].get('enabled') else 1)"
    if ($LASTEXITCODE -eq 0) {
        Add-Job "AdvisorPA WhatsApp check" "whatsapp_scan.py" "run" (Daily "04:07")
        Write-Host "  (the WhatsApp check needs WhatsApp desktop open and signed in at that time)"
    } else {
        Remove-Job "AdvisorPA WhatsApp check" | Out-Null
        Write-Host "  WhatsApp check is off (config.json whatsapp.enabled)"
    }
    if ($script:failed) { Write-Host "Some jobs could not be made (see FAILED above)."; exit 1 }
    Write-Host "Done. They run while the PC is on and they are signed in. Turn off: setup.cmd remove-background"
    exit 0
}
if ($Mode -eq "remove-background") {
    foreach ($t in $Tasks) { Remove-Job $t }
    if (Test-Path $Startup) { Remove-Item $Startup }
    Write-Host "  off: Telegram line at sign-in"
    exit 0
}

Say "1/4 Checking tools"
$missing = @()
if (-not (Have git)) { $missing += "Git:          winget install --id Git.Git -e" }
$base = $null
function Test-Py([string[]]$cmd) {   # true when this Python is 3.11 or newer
    try {
        $rest = @(); if ($cmd.Count -gt 1) { $rest = $cmd[1..($cmd.Count - 1)] }
        & $cmd[0] @rest -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}
$cands = @()
if (Have py) { $cands += , @("py", "-3.12"); $cands += , @("py", "-3.13"); $cands += , @("py", "-3.11"); $cands += , @("py", "-3") }
if (Have python) { $cands += , @("python") }
foreach ($c in $cands) { if (Test-Py $c) { $base = $c; break } }
if (-not $base) { $missing += "Python 3.12:  winget install --id Python.Python.3.12 -e" }
$claude = (Have claude) -or (Test-Path "$env:USERPROFILE\.local\bin\claude.exe")
if (-not $claude) { $missing += "Claude Code:  irm https://claude.ai/install.ps1 | iex" }
if (-not ((Have bun) -or (Test-Path "$env:USERPROFILE\.bun\bin\bun.exe"))) { $missing += "Bun:          irm bun.sh/install.ps1 | iex   (the Telegram plugin needs it)" }
if ($missing.Count) {
    Write-Host "Missing (paste each line in PowerShell, then close and reopen it and run setup.cmd again):"
    $missing | ForEach-Object { Write-Host "  $_" }
    if (-not $base) { exit 1 }
}
if (-not ((Test-Path "$env:ProgramFiles\Google\Chrome\Application\chrome.exe") -or (Test-Path "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"))) {
    Write-Host "Note: PDFs are printed with Chrome or Edge; neither was found."
}

Say "2/4 Python environment (.venv)"
if (-not (Test-Path $Py)) {
    if ($base.Count -gt 1) { & $base[0] $base[1] -m venv .venv } else { & $base[0] -m venv .venv }
    if (-not (Test-Path $Py)) { Write-Host "Could not make the Python environment (.venv)."; exit 1 }
}
& $Py -m pip install -q --upgrade pip
& $Py -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed (see above)."; exit 1 }
Write-Host "  ok"

Say "3/4 Folders"
$dirs = "Data\Clients", "Data\Investments", "Forms\Blank", "Drafts\Reminders", "Drafts\Follow-ups", "Drafts\Meetings",
        "Drafts\Analysis", "Drafts\Forms", "Drafts\Client Reports", "Drafts\Investment Reports", "Drafts\Drive",
        "Drafts\Status", "Drafts\Jobs", "Drafts\Office", "Drafts\Pipeline backups", "Drafts\Game Plan"
foreach ($d in $dirs) { New-Item -ItemType Directory -Force (Join-Path $Dir $d) | Out-Null }
Write-Host "  ok"

Say "4/4 Your own files (kept private, never part of updates)"
function Copy-Once($from, $to) {
    if (Test-Path $to) { Write-Host "  kept:    $to" } else { Copy-Item $from $to; Write-Host "  created: $to" }
}
Copy-Once "config.example.json" "config.json"
Copy-Once "templates\Me.example.md" "Me.md"
Copy-Once "templates\Preferences.example.md" "Preferences.md"
Copy-Once "templates\Voice.example.md" "Voice.md"
Copy-Once "templates\Client Policies TEMPLATE.xlsx" "Data\Client Policies.xlsx"
Copy-Once "templates\pipeline-TEMPLATE.csv" "Data\pipeline.csv"

Say "Setup done."
Write-Host "Next: in this folder type  claude  and say:  Set me up, follow SETUP-FOR-CLAUDE.md"

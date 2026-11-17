"""Start, stop or check the Telegram line on a Mac or a Windows PC (one command for both).

  ./pa line start              start it (does nothing if it's already running)
  ./pa line start --visible    start it in a window you can see: use the FIRST time, to answer Claude Code's
                               start-up questions (trust the folders, confirm the channel), then close nothing:
                               it keeps running. (Mac: it always runs in tmux; look with tmux attach -t pa-line.)
  ./pa line stop               stop it; the watchdog then leaves it stopped until "line start"
  ./pa line status             running or not
  ./pa line restart            stop and start again (used by update.sh; safe to run from inside the line)

The line is Claude Code with the Telegram channel. Keep only ONE copy: two copies on the same bot fight over
messages (start checks). It runs unattended, so --permission-mode auto lets the safety checker decide instead of
waiting for a click, and --add-dir gives it the folder where Telegram photos/files land plus their product/forms
libraries and their memory folder. ADMIN_TEAM_LINE=telegram tells the hooks that this is the Telegram line.

Mac: hands over to Tools/start_line.sh / stop_line.sh (tmux session "pa-line").
Windows: runs Claude Code in its own classic console window (conhost), hidden unless --visible. Closing that
window, or "line stop", ends the line. At sign-in it is started by a shortcut in the Startup folder
(setup.cmd background).
"""
import os, sys, json, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
ST = os.path.join(ROOT, "Drafts", "Status")
OFF = os.path.join(ST, "line-off")      # "line stop" creates it so the watchdog leaves the line stopped
HERE = os.path.abspath(__file__)
# Which processes count as the line. Only changed by the kit's own tests, so a test never touches a real line.
PNAME = os.environ.get("PA_LINE_TEST_PNAME", "claude.exe")
MATCH = os.environ.get("PA_LINE_TEST_MATCH", "--channels")


def _ps(cmd):
    return C.run_hidden(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout


def _line_procs(then):
    """PowerShell: the line's processes, piped into `then`."""
    return (f"Get-CimInstance Win32_Process -Filter \"Name='{PNAME}'\" | "
            f"Where-Object {{ $_.CommandLine -match '{MATCH}' }} | ForEach-Object {{ {then} }}")


def pids():
    """Process ids of running line copies."""
    if C.IS_WIN:
        out = _ps(_line_procs("$_.ProcessId"))
    else:
        out = subprocess.run(["pgrep", "-f", "claude.*" + MATCH], capture_output=True, text=True).stdout
    return [int(p) for p in out.split() if p.isdigit() and int(p) != os.getpid()]


def started_at():
    """Epoch time the newest running line copy started, or 0."""
    if C.IS_WIN:
        out = _ps(_line_procs("[int64](($_.CreationDate.ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds)"))
        nums = [int(x) for x in out.split() if x.isdigit()]
        return max(nums) if nums else 0
    best = 0
    for p in pids():
        e = subprocess.run(["ps", "-o", "etime=", "-p", str(p)], capture_output=True, text=True).stdout.strip()
        if not e:
            continue
        days, _, rest = e.rpartition("-")
        parts = [int(x) for x in rest.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        secs = (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
        best = max(best, int(time.time() - secs))
    return best


def add_dirs():
    """Folders the line may read. They are created now if missing, so the set never changes later: each new folder
    makes Claude Code ask "trust this folder?" at the next start, and a hidden line can't answer that."""
    slug = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in ROOT)
    mem = os.path.join(os.path.expanduser("~"), ".claude", "projects", slug, "memory")
    dirs = []
    for d in (C.TG_INBOX, mem, C.PRODUCT_LIBRARY, C.FORMS_LIBRARY):
        if d:
            os.makedirs(d, exist_ok=True)
            dirs.append(d)
    return dirs


def start(visible=False):
    os.makedirs(ST, exist_ok=True)
    if os.path.exists(OFF):
        os.remove(OFF)
    if not C.IS_WIN:
        r = subprocess.run(["/bin/bash", os.path.join(ROOT, "Tools", "start_line.sh")], capture_output=True, text=True, timeout=60)
        print((r.stdout + r.stderr).strip())
        return
    if pids():
        print("Telegram line is already running.")
        return
    py = sys.executable.replace("pythonw.exe", "python.exe")     # a console Python, so Claude Code gets a console
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 1 if visible else 0                          # SW_SHOWNORMAL / SW_HIDE
    subprocess.Popen(["conhost.exe", py, "-X", "utf8", HERE, "run"], cwd=ROOT, startupinfo=si,
                     creationflags=0x00000010 | 0x00000200,      # new console, own process group
                     close_fds=True)
    for _ in range(20):
        time.sleep(1)
        if pids():
            print("Telegram line started" + (" (window open: answer any start-up question there, then leave it)."
                                             if visible else " (hidden)."))
            return
    print("Started, but Claude Code isn't showing yet. Check again with: ./pa line status"
          + ("" if visible else "   (first time? use: ./pa line start --visible)"))


def run():
    """Windows only: runs inside the line's own console window. Ends when Claude Code ends."""
    os.chdir(ROOT)
    env = dict(os.environ, ADMIN_TEAM_LINE="telegram")
    test = os.environ.get("PA_LINE_TEST_CMD")                    # used only to test the window handling
    cmd = test.split() if test else [C.claude_bin(), "--channels", "plugin:telegram@claude-plugins-official",
                                     "--permission-mode", "auto", "--add-dir", *add_dirs()]
    try:
        os.system("title PA - Telegram line")
    except Exception:
        pass
    sys.exit(subprocess.call(cmd, env=env))


def stop(keep_on=False):
    os.makedirs(ST, exist_ok=True)
    if not keep_on:
        open(OFF, "w").close()
    if not C.IS_WIN:
        r = subprocess.run(["/bin/bash", os.path.join(ROOT, "Tools", "stop_line.sh")] + (["--keep-on"] if keep_on else []),
                           capture_output=True, text=True, timeout=60)
        print((r.stdout + r.stderr).strip())
        return
    n = len(pids())
    # Claude Code first, then the console window(s) that hosted it (also clears any left behind earlier).
    _ps(_line_procs("Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue") + "; "
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'line\\.py\"?\\s+run' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    print(f"Telegram line stopped ({n} process)." if n else "Telegram line was not running.")


def restart():
    """Stop and start again from a separate background process, so it also works when called from inside the line
    (e.g. "update the PA" on Telegram: stopping the line would otherwise also stop the command doing the restart)."""
    log = open(os.path.join(ST, "line-restart.log"), "a")
    C.start_detached([sys.executable, "-X", "utf8", HERE, "_restart"], cwd=ROOT,
                     stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    print("Telegram line will restart in a few seconds.")


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("start", "stop", "status", "run", "restart", "_restart"):
        sys.exit(__doc__)
    os.makedirs(ST, exist_ok=True)
    if a[0] == "start":
        start(visible="--visible" in a)
    elif a[0] == "stop":
        stop(keep_on="--keep-on" in a)
    elif a[0] == "restart":
        restart()
    elif a[0] == "_restart":
        time.sleep(5)            # let the caller finish its reply first
        stop(keep_on=True)
        time.sleep(4)
        start()
    elif a[0] == "run":
        run()
    else:
        p = pids()
        print(f"Telegram line is running (pid {', '.join(map(str, p))})." if p else
              "Telegram line is NOT running" + (" (stopped on purpose: ./pa line start)." if os.path.exists(OFF) else "."))


if __name__ == "__main__":
    main()

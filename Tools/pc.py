"""Small computer remote for the Telegram line (Mac; Windows also works).

  ./pa pc screenshot        take a screenshot and post it to HQ General
  ./pa pc status            uptime, battery/power, disk space, Claude processes running, jobs
  ./pa pc open "<path|url>"  open a file, folder or web page (for when she's back at the desk soon)

No system or security settings are ever changed here (no sleep/power/lock/shutdown).
On a Mac the first screenshot needs Screen Recording permission for the Terminal app (macOS asks once).
"""
import sys, os, time, subprocess, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
PY = C.PY


def sh(cmd):
    try:
        return C.run_hidden(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def screenshot():
    out = os.path.join(ROOT, "Drafts", "Status", "screen.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if C.IS_MAC:
        sh(["screencapture", "-x", out])
    elif C.IS_WIN:
        sh(["powershell", "-NoProfile", "-Command",
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
            "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
            "$g=[System.Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size);"
            f"$bmp.Save('{out}',[System.Drawing.Imaging.ImageFormat]::Png)"])
    if not os.path.exists(out) or time.time() - os.path.getmtime(out) > 30:
        sys.exit("Screenshot failed (the computer may be locked or asleep, or Screen Recording isn't allowed).")
    r = subprocess.run(PY + [os.path.join(ROOT, "Tools", "telegram_post.py"), "main",
                             "🖥 Screen " + time.strftime("%H:%M"), "--file", out], capture_output=True, text=True)
    print(out, (r.stdout or r.stderr).strip())


def status():
    free = shutil.disk_usage(os.path.expanduser("~")).free / 1e9
    if C.IS_MAC:
        up = sh(["uptime"]).split(",")[0].split("up")[-1].strip()
        batt = sh(["pmset", "-g", "batt"]).splitlines()
        power = batt[1].split("\t")[-1].split(";")[0:2] if len(batt) > 1 else ["desktop power"]
        power = " ".join(x.strip() for x in power) + (" (plugged in)" if batt and "AC Power" in batt[0] else " (on battery)")
        chats = sh(["pgrep", "-fc", "claude"]) or "0"
    else:
        up = sh(["powershell", "-NoProfile", "-Command", "$o=Get-CimInstance Win32_OperatingSystem; $u=(Get-Date)-$o.LastBootUpTime; '{0}d {1}h {2}m' -f $u.Days,$u.Hours,$u.Minutes"])
        power = sh(["powershell", "-NoProfile", "-Command", "$b=Get-CimInstance Win32_Battery; if($b){'{0}%' -f $b.EstimatedChargeRemaining}else{'desktop power'}"])
        chats = sh(["powershell", "-NoProfile", "-Command", "(Get-Process claude -ErrorAction SilentlyContinue).Count"]) or "0"
    print(f"Up {up} · Power: {power} · Disk: {free:.0f} GB free · Claude processes: {chats}")
    j = subprocess.run(PY + [os.path.join(ROOT, "Tools", "run_job.py"), "list"], capture_output=True, text=True).stdout
    print("Jobs:\n" + j.strip())


def open_thing(target):
    if C.IS_MAC:
        subprocess.run(["open", target], check=False)
    elif C.IS_WIN:
        os.startfile(target)
    else:
        subprocess.run(["xdg-open", target], check=False)
    print("Opened: " + target)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "screenshot":
        screenshot()
    elif a[0] == "status":
        status()
    elif a[0] == "open" and len(a) > 1:
        open_thing(a[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

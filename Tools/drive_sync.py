"""Keep chosen local files mirrored to Google Drive (one-way: local -> Drive). Uses Google Drive for desktop.

Files and target folders are set in config.json "drive_sync": {"Data/Client Policies.xlsx": "Clients"}
(the folder is inside "My Drive"). Copies a file when the local copy is newer or a different size.
Runs every 10 min (launchd job made by setup.sh), and on demand:
    ./pa drive_sync          (sync now)
    ./pa drive_sync --status (show what's synced)
Log: Drafts/Status/drive-sync.log
"""
import os, sys, shutil, time, string, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

LOG = os.path.join(C.ROOT, "Drafts", "Status", "drive-sync.log")
FILES = {C.path(src): folder for src, folder in C.CFG.get("drive_sync", {}).items() if not src.startswith("_")}  # local file -> folder in My Drive


def my_drive():
    """The "My Drive" folder of Google Drive for desktop (config files.google_drive overrides)."""
    if C.CFG["files"].get("google_drive"):
        p = C.path(C.CFG["files"]["google_drive"])
        return p if os.path.isdir(p) else None
    if C.IS_MAC:
        found = sorted(glob.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive")))
        return found[0] if found else None
    for d in string.ascii_uppercase[3:]:
        p = d + ":" + os.sep + "My Drive"
        if os.path.isdir(p):
            return p
    return None


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M ") + msg + "\n")


def main():
    status = "--status" in sys.argv
    if not FILES:
        print("Nothing to sync: config.json drive_sync is empty")
        return
    md = my_drive()
    if not md:
        msg = "Google Drive for desktop isn't running (no My Drive folder found); nothing synced"
        print(msg)
        if not status:
            log(msg)
        return
    for src, folder in FILES.items():
        if not os.path.exists(src):
            print("missing:", src)
            continue
        dst = os.path.join(md, *folder.replace(chr(92), "/").split("/"), os.path.basename(src))
        newer = (not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst) + 2
                 or os.path.getsize(src) != os.path.getsize(dst))
        if status:
            print(("needs sync: " if newer else "up to date: ") + dst)
            continue
        if newer:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                log(f"synced {os.path.basename(src)} -> {folder}")
                print("synced:", dst)
            except Exception as e:  # e.g. file mid-save in Excel; next run retries
                log(f"failed {os.path.basename(src)}: {e}")
                print("failed:", e)


if __name__ == "__main__":
    main()

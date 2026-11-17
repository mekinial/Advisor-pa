"""Run an agent task as a separate background job on this computer, so the Telegram chat stays free.

  ./pa run_job start <agent> "<task>"    start a job; prints its id at once
  ./pa run_job list                       running + recent jobs
  ./pa run_job show <id>                  the job's result text

<agent> = follow-up, meeting-prep, data-analyst, admin-forms, client-report, proposal-writer, investment-writer,
drive-organizer or coordinator. The job is a headless Claude Code run (claude -p, auto permission mode) in the
PA folder using that agent's playbook and all ground rules. Steps that need an approval are skipped, not
waited on. When it ends, its summary (and any files it made) is posted to the agent's HQ topic, and the
status board gets start/done lines. Output: Drafts/Jobs/<id>.md. At most 3 jobs run at once.
"""
import sys, os, json, time, subprocess, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
JOBS = os.path.join(ROOT, "Drafts", "Jobs")
PY = C.PY
TOPIC = {"coordinator": "main", "drive-organizer": "admin", "follow-up": "follow-up", "data-analyst": "data-analyst",
         "admin-forms": "admin-forms", "client-report": "reports", "proposal-writer": "reports",
         "investment-writer": "reports", "meeting-prep": "meetings"}
ADD_DIRS = [d for d in (C.PRODUCT_LIBRARY, C.FORMS_LIBRARY, C.TG_INBOX) if d and os.path.isdir(d)]
TOOL = lambda name: os.path.join(ROOT, "Tools", name)


def meta_path(jid):
    return os.path.join(JOBS, jid + ".json")


def load(jid):
    return json.load(open(meta_path(jid), encoding="utf-8"))


def save(m):
    json.dump(m, open(meta_path(m["id"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def jobs():
    os.makedirs(JOBS, exist_ok=True)
    out = []
    for f in sorted(os.listdir(JOBS)):
        if f.endswith(".json"):
            try:
                out.append(json.load(open(os.path.join(JOBS, f), encoding="utf-8")))
            except Exception:
                pass
    return out


def start(agent, task):
    if agent not in TOPIC:
        sys.exit(f"Unknown agent '{agent}'. Use one of: {', '.join(TOPIC)}")
    running = [j for j in jobs() if j["status"] == "running"]
    if len(running) >= 3:
        sys.exit("3 jobs are already running; wait for one to finish (run_job list).")
    jid = time.strftime("%Y%m%d-%H%M%S") + "-" + agent
    m = {"id": jid, "agent": agent, "task": task[:500], "status": "running", "started": time.time()}
    save(m)
    p = C.start_detached(PY + [os.path.abspath(__file__), "_run", jid], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    m["runner_pid"] = p.pid
    save(m)
    C.run_hidden(PY + [TOOL("hq_status.py"), "start", agent, task[:120]], capture_output=True)
    print(f"Job started: {jid}")


def _run(jid):
    m = load(jid)
    agent, task = m["agent"], m["task"]
    playbook = "" if agent == "coordinator" else f" Use the playbook in .claude/agents/{agent}.md."
    prompt = (f"You are the Admin Team's {agent} agent, running as a background job the adviser started from Telegram."
              f"{playbook} Follow every ground rule in CLAUDE.md (draft only, never contact anyone, no NRIC/policy "
              f"numbers/bank details, facts only from files). Nobody can answer questions or approve steps while "
              f"you run: if something needs the adviser, skip it and say so.\n\nTask: {task}\n\n"
              "Save anything you make under Drafts/. Finish with a short summary for the adviser (max 5 lines, plain text), "
              "then one last line starting 'FILES:' with the absolute paths of files they should see, separated by ' | ' "
              "(or 'FILES: none').")
    out_md = os.path.join(JOBS, jid + ".md")
    env = dict(os.environ); env.pop("ADMIN_TEAM_LINE", None)
    cmd = [C.claude_bin(), "-p", prompt, "--permission-mode", "auto"] + (["--add-dir", *ADD_DIRS] if ADD_DIRS else [])
    try:
        r = C.run_hidden(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=3 * 3600, env=env)
        text, ok = (r.stdout or "").strip() or (r.stderr or "").strip(), r.returncode == 0
    except subprocess.TimeoutExpired:
        text, ok = "Stopped after 3 hours without finishing.", False
    open(out_md, "w", encoding="utf-8").write(f"# Job {jid}\n\nTask: {task}\n\n{text}\n")
    files = []
    mm = re.search(r"^FILES:\s*(.+)$", text, re.M)
    if mm and mm.group(1).strip().lower() != "none":
        files = [f.strip() for f in mm.group(1).split("|") if os.path.isfile(f.strip())]
    summary = re.sub(r"^FILES:.*$", "", text, flags=re.M).strip()[-900:] or "(no summary)"
    m.update(status="done" if ok else "failed", ended=time.time(), files=files)
    save(m)
    icon = "✅" if ok else "⚠️"
    post = PY + [TOOL("telegram_post.py"), TOPIC[agent], f"{icon} Job done ({agent}): {task[:80]}\n\n{summary}"]
    if files:
        post += ["--file", files[0]]
    C.run_hidden(post, capture_output=True, timeout=120)
    for f in files[1:4]:
        C.run_hidden(PY + [TOOL("telegram_post.py"), TOPIC[agent], os.path.basename(f), "--file", f],
                     capture_output=True, timeout=120)
    C.run_hidden(PY + [TOOL("telegram_post.py"), "main", f"{icon} {agent} job finished: {task[:60]} → in its topic"],
                 capture_output=True)
    C.run_hidden(PY + [TOOL("hq_status.py"), "done", agent, f"{task[:80]} → Drafts/Jobs/{jid}.md"], capture_output=True)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "start" and len(a) >= 3:
        start(a[1], " ".join(a[2:]))
    elif a[0] == "_run":
        _run(a[1])
    elif a[0] == "list":
        js = jobs()[-15:]
        if not js:
            print("No jobs yet."); return
        for j in js:
            if j["status"] == "running" and not C.pid_alive(j.get("runner_pid", 0)):
                j["status"] = "failed (stopped)"; save(j)
            mins = ((j.get("ended") or time.time()) - j["started"]) / 60
            print(f"{j['id']}  {j['status']}  {mins:.0f} min  {j['task'][:70]}")
    elif a[0] == "show" and len(a) > 1:
        print(open(os.path.join(JOBS, a[1] + ".md"), encoding="utf-8").read())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

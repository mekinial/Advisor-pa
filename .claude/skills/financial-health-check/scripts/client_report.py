"""Client-friendly PDF: the health check as pictures first, words second.

  ./pa client_report <numbers.json> <story.json> [--legacy <legacy.json>] [--out <file.pdf>] [--html]

<numbers.json>  output of health_check.py --json (all figures come from here; nothing is recalculated)
<story.json>    the plain-language words, written per client (see ../assets/client-story-template.json)
--legacy        optional output of legacy_plan.py --json, adds a "Who gets what" page
--html          also keep the .html next to the PDF (for checking layout)

Never includes internal notes: only the story file's client-facing fields and the calculator's numbers.
Printed with Google Chrome or Microsoft Edge (headless). Local only.
"""
import json, sys, os, html, math, subprocess, tempfile, datetime

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), *[".."] * 4, "Tools"))
try:
    import pa_config as _C
    ADVISER, FIRM = _C.ME.get("full_name") or "Your adviser", _C.ME.get("firm") or ""
except Exception:
    ADVISER, FIRM = "Your adviser", ""


def _browser():
    try:
        import make_pdf
        return make_pdf.browser()
    except Exception:
        return "msedge"
DISCLAIMER = ("This report is for discussion only and is based on the information you shared on the date shown. "
              "It is not an offer or a recommendation to buy any product. Guidelines are general rules of thumb; "
              "the right amount for you depends on a full needs analysis. Projections are illustrative and not "
              "guaranteed; investment values can fall as well as rise. Any recommendation is subject to a fact-find "
              "and suitability assessment. This document has not been reviewed by the Monetary Authority of Singapore.")

C = {"navy": "#14213D", "ink": "#22304A", "muted": "#6B7489", "line": "#E6E2DA", "paper": "#FFFDF9",
     "sand": "#F6EFE4", "coral": "#E76F51", "teal": "#2A9D8F", "amber": "#E9A23B", "sky": "#5B8DB8",
     "plum": "#8E6C8A", "green": "#2A9D8F", "red": "#D1495B"}
PALETTE = [C["navy"], C["teal"], C["amber"], C["coral"], C["sky"], C["plum"]]
E = html.escape


def m(x, short=True):
    """Money, short form for charts: $1.2M, $471k, $6,041."""
    if x is None:
        return "—"
    a = abs(x)
    s = (f"${a / 1e6:.1f}M".replace(".0M", "M") if a >= 1e6 else f"${a / 1e3:.0f}k" if a >= 1e4 and short
         else f"${a:,.0f}")
    return "-" + s if x < 0 else s


# ---------------------------------------------------------------- charts (inline SVG)
def donut(parts, size=190, hole=0.62, centre_top="", centre_bottom=""):
    parts = [(k, v) for k, v in parts if v and v > 0]
    tot = sum(v for _, v in parts) or 1
    r, cx, cy = size / 2 - 4, size / 2, size / 2
    a0, segs = -math.pi / 2, []
    for i, (k, v) in enumerate(parts):
        a1 = a0 + 2 * math.pi * v / tot
        large = 1 if a1 - a0 > math.pi else 0
        if len(parts) == 1:
            segs.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PALETTE[i]}"/>')
        else:
            x0, y0, x1, y1 = cx + r * math.cos(a0), cy + r * math.sin(a0), cx + r * math.cos(a1), cy + r * math.sin(a1)
            segs.append(f'<path d="M{cx},{cy} L{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f} Z" '
                        f'fill="{PALETTE[i % len(PALETTE)]}"/>')
        a0 = a1
    svg = (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(segs)}'
           f'<circle cx="{cx}" cy="{cy}" r="{r * hole}" fill="#fff"/>'
           f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" class="d-top">{E(centre_top)}</text>'
           f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" class="d-bot">{E(centre_bottom)}</text></svg>')
    legend = "".join(f'<div class="lg"><i style="background:{PALETTE[i % len(PALETTE)]}"></i>{E(k)}'
                     f'<b>{m(v)}</b><span>{v / tot * 100:.0f}%</span></div>' for i, (k, v) in enumerate(parts))
    return f'<div class="donut">{svg}<div class="legend">{legend}</div></div>'


def flow_bar(income, parts):
    """Money in each month and where it goes, as one stacked bar."""
    parts = [(k, v, col) for k, v, col in parts if v and v > 0]
    tot = max(income or 0, sum(v for _, v, _ in parts)) or 1
    segs = "".join(f'<div class="seg" style="width:{v / tot * 100:.2f}%;background:{col}">'
                   f'{E(m(v, False)) if v / tot > 0.09 else ""}</div>' for k, v, col in parts)
    legend = "".join(f'<div class="lg"><i style="background:{col}"></i>{E(k)}<b>{m(v, False)}</b></div>'
                     for k, v, col in parts)
    return (f'<div class="flow"><div class="flow-in">Comes in each month <b>{m(income, False)}</b></div>'
            f'<div class="bar">{segs}</div><div class="legend row">{legend}</div></div>')


def cover_bars(rows):
    """Have vs guideline, one row each. Bar scaled to the larger of the two; marker = guideline."""
    out = []
    for r in rows:
        have, tgt, lab = r.get("have") or 0, r.get("target"), r["label"]
        monthly = "monthly" in lab.lower()
        lab = lab.replace(" (monthly)", "")
        if tgt is None and not have:
            continue
        top = max(have, tgt or 0) or 1
        ok = tgt is None or have >= tgt
        col = C["teal"] if ok else C["coral"]
        pct = tgt / top * 100 if tgt else 0
        mark = (f'<div class="tick{" r" if pct > 82 else " l" if pct < 18 else ""}" style="left:{pct:.1f}%"><span>Guideline {m(tgt, False if monthly else True)}'
                f'{"/mo" if monthly else ""}</span></div>') if tgt else ""
        status = ("In place" if tgt is None else "No longer needed" if tgt == 0 else "On track" if ok else f"Short by {m(tgt - have)}"
                  + ("/mo" if monthly else ""))
        out.append(f'<div class="cb"><div class="cb-l">{E(lab)}<em class="{ "ok" if ok else "gap"}">{status}</em></div>'
                   f'<div class="cb-track"><div class="cb-fill" style="width:{have / top * 100:.1f}%;background:{col}">'
                   f'<span>{m(have, not monthly)}{"/mo" if monthly else ""}</span></div>{mark}</div></div>')
    return '<div class="covers">' + "".join(out) + "</div>"


def retirement_bar(want, sources):
    sources = [(k, v) for k, v in sources if v and v > 0]
    built = sum(v for _, v in sources)
    top = max(want or 0, built) or 1
    segs = "".join(f'<div class="seg" style="width:{v / top * 100:.2f}%;background:{PALETTE[(i + 1) % len(PALETTE)]}">'
                   f'{E(m(v, False)) if v / top > 0.1 else ""}</div>' for i, (k, v) in enumerate(sources))
    gap = max((want or 0) - built, 0)
    gapseg = (f'<div class="seg gapseg" style="width:{gap / top * 100:.2f}%">'
              f'{"Gap " + m(gap, False) if gap / top > 0.12 else ""}</div>') if gap else ""
    legend = "".join(f'<div class="lg"><i style="background:{PALETTE[(i + 1) % len(PALETTE)]}"></i>{E(short_src(k))}'
                     f'<b>{m(v, False)}</b></div>' for i, (k, v) in enumerate(sources))
    if gap:
        legend += f'<div class="lg"><i class="gapdot"></i>Still to find<b>{m(gap, False)}</b></div>'
    return (f'<div class="ret"><div class="ret-row"><div class="ret-l">What you want</div>'
            f'<div class="bar"><div class="seg" style="width:{(want or 0) / top * 100:.2f}%;background:{C["navy"]}">'
            f'{m(want, False)} a month</div></div></div>'
            f'<div class="ret-row"><div class="ret-l">What you\'re building</div><div class="bar">{segs}{gapseg}</div></div>'
            f'<div class="legend row">{legend}</div></div>')


def short_src(k):
    k = k.split("(")[0].strip()
    return {"Investments & spare cash at 4% drawdown": "Your savings & investments",
            "SRS ÷ 10 yrs": "SRS"}.get(k, k)


def gauge(value, target, label):
    """Half-circle gauge for the emergency cushion (months)."""
    frac = 0 if not target else min((value or 0) / (target * 2), 1)
    a = math.pi * (1 - frac)
    x, y = 90 + 70 * math.cos(a), 90 - 70 * math.sin(a)
    tx = math.pi * (1 - 0.5)
    col = C["teal"] if (value or 0) >= (target or 0) else C["amber"] if (value or 0) >= (target or 0) / 2 else C["coral"]
    return (f'<svg width="180" height="104" viewBox="0 0 180 104">'
            f'<path d="M20,90 A70,70 0 0 1 160,90" fill="none" stroke="{C["line"]}" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M20,90 A70,70 0 0 1 {x:.1f},{y:.1f}" fill="none" stroke="{col}" stroke-width="16" stroke-linecap="round"/>'
            f'<line x1="90" y1="14" x2="90" y2="28" stroke="{C["navy"]}" stroke-width="2"/>'
            f'<text x="90" y="78" text-anchor="middle" class="g-big">{value or 0:.1f}</text>'
            f'<text x="90" y="98" text-anchor="middle" class="g-sm">{E(label)}</text></svg>')


def light(status):
    return {"g": C["green"], "a": C["amber"], "r": C["red"]}.get(status, C["muted"])


def scorecard(v, ret):
    def band(x, good, ok, higher=True):
        if x is None:
            return "n", "Not enough information yet"
        if higher:
            return ("g" if x >= good else "a" if x >= ok else "r"), None
        return ("g" if x <= good else "a" if x <= ok else "r"), None
    em = v["emergency"]
    items = []
    s, _ = band(None if em["months_have"] is None else em["months_have"] / (em["months_target"] or 1), 1, 0.5)
    items.append(("Emergency cushion", s, f'{(em["months_have"] or 0):.0f} months of spending set aside '
                  f'(guideline {em["months_target"]:g})' if em["months_have"] is not None else "Not enough information yet"))
    s, _ = band(v["savings_pct"], 0.10, 0.05)
    items.append(("Saving habit", s, f'{(v["savings_pct"] or 0) * 100:.0f}% of what comes in is saved (guideline 10%+)'
                  if v["savings_pct"] is not None else "Not enough information yet"))
    s, _ = band(v["debt_pct"], 0.30, 0.50, higher=False)
    items.append(("Borrowing", s, "Debt-free" if v["debt_pct"] == 0 else f'Debts are {(v["debt_pct"] or 0) * 100:.0f}% of what you own'
                  if v["debt_pct"] is not None else "Not enough information yet"))
    s, _ = band(v["premium_pct"], 0.10, 0.15, higher=False)
    items.append(("Cost of protection", s, f'{(v["premium_pct"] or 0) * 100:.0f}% of income (guideline up to 10–15%)'
                  if v["premium_pct"] is not None else "Not enough information yet"))
    s, _ = band(v["invested_pct"], 0.5, 0.25)
    items.append(("Money working for you", s, f'{(v["invested_pct"] or 0) * 100:.0f}% of your wealth is invested (guideline 50%+)'
                  if v["invested_pct"] is not None else "Not enough information yet"))
    prot = [p for p in v["protection"] if p.get("target")]
    ok = sum(1 for p in prot if (p.get("have") or 0) >= p["target"])
    if v.get("stage") == "The Distributor":
        items.append(("Long-term care", "g" if v["ltc"] else "r",
                      "Care cover in place" if v["ltc"] else "No long-term care cover yet"))
    else:
        items.append(("Protection", "g" if prot and ok == len(prot) else "a" if ok else "r" if prot else "n",
                      f"{ok} of {len(prot)} areas meet the guideline" if prot else "Not enough information yet"))
    if ret:
        g = ret.get("gap") or 0
        s = "g" if g <= 0 else "a" if g / (ret.get("want") or 1) <= 0.25 else "r"
        items.append(("Retirement", s, "On track for your goal" if g <= 0 else f'{(1 - g / ret["want"]) * 100:.0f}% of your goal is covered so far'))
    return '<div class="score">' + "".join(
        f'<div class="sc"><i style="background:{light(st)}"></i><div><b>{E(t)}</b><span>{E(d)}</span></div></div>'
        for t, st, d in items) + "</div>"


def cards(title, items, cls, icon):
    if not items:
        return ""
    return (f'<div class="card {cls}"><div class="card-h"><span class="ic">{icon}</span>{E(title)}</div><ul>'
            + "".join(f"<li>{E(x)}</li>" for x in items) + "</ul></div>")


def legacy_bars(lg):
    tgt = lg.get("target") or {}
    now, total = lg.get("now") or {}, lg.get("total") or 1
    names = list(dict.fromkeys(list(tgt) + [k for k, v in now.items() if v]))
    rows = []
    for i, k in enumerate(names):
        a = (now.get(k) or 0) / total * 100
        b = (tgt.get(k) or 0) * 100
        rows.append(f'<div class="lgrow"><div class="lgname">{E(k)}</div><div class="lgbars">'
                    f'<div class="lgb"><div style="width:{a:.1f}%;background:{C["muted"]}"></div><span>Today {a:.0f}%</span></div>'
                    + (f'<div class="lgb"><div style="width:{b:.1f}%;background:{PALETTE[(i + 1) % 6]}"></div><span>Your wish {b:.0f}%</span></div>' if tgt else "")
                    + "</div></div>")
    return '<div class="legacy">' + "".join(rows) + "</div>"


def route_map(channels):
    """Each asset and the 'rulebook' that moves it, as coloured route pills."""
    def style(route):
        r = route.lower()
        if "public trustee" in r or "no nomination" in r:
            return C["coral"], "Stuck: " + ("Public Trustee" if "trustee" in r else "waits for probate")
        if "cpf nomination" in r:
            return C["teal"], "CPF nomination"
        if "insurance nomination" in r:
            return C["amber"], "Insurance nomination"
        if "joint tenancy" in r:
            return C["plum"], "Goes to co-owner"
        return C["navy"], "Your will" if "will" in r else "Estate"
    rows = []
    for ch in channels:
        col, lab = style(ch["route"])
        rows.append(f'<div class="rt"><div class="rt-a"><b>{E(ch["asset"])}</b><span>{E(ch["value"])}</span></div>'
                    f'<div class="rt-arrow" style="background:{col}"></div>'
                    f'<div class="rt-p" style="background:{col}">{E(lab)}</div></div>')
    return '<div class="routes">' + "".join(rows) + "</div>"


def checklist(items):
    ic = {"yes": (C["teal"], "✓"), "no": (C["coral"], "×"), "unknown": (C["muted"], "?")}
    return '<div class="ecl">' + "".join(
        f'<div class="ec"><i style="background:{ic[s][0]}">{ic[s][1]}</i>{E(t)}</div>' for t, s in items) + "</div>"


COVER_WHAT = [
    ("Death / TPD", "A lump sum for your family if you pass away or become totally and permanently disabled."),
    ("Critical illness", "A lump sum if you're diagnosed with a serious illness, so you can focus on getting better."),
    ("Early critical illness", "Pays out at an earlier stage of a serious illness, when treatment often starts."),
    ("Disability income", "A monthly income if illness or injury stops you from working for a long time."),
]

KIND_COL = {"now": C["navy"], "retire": C["amber"], "cpf": C["sky"], "goal": C["plum"], "family": C["teal"],
            "warn": C["red"], "end": C["muted"], "custom": C["teal"]}


def short_event(e):
    k, lab = e["kind"], e["label"]
    return {"now": "Today", "retire": "Retire", "warn": "Savings run out", "end": f"Age {e['age']}"}.get(k) or \
        ("CPF LIFE" if "LIFE" in lab else "CPF at 55" if k == "cpf" else lab.split(" (")[0])


def life_chart(t):
    """Liquid money by age: today's path (teal) and the plan (navy), each a middle line inside a
    cautious-to-hopeful band; life phases behind; milestone pins above."""
    W, H, L, R_, T, B = 640, 272, 52, 18, 70, 28
    now, plan = t["now"], None   # the plan has its own page (plan_chart)
    s = now["middle"]["series"]
    a0, a1 = s[0][0], t["plan_to"]
    paths = [now] + ([plan] if plan else [])
    pol = (t.get("policies") or {}).get("series") or []
    pold = dict(pol)
    stack = [[a, p + pold.get(a, 0)] for a, p in s] if any(v for _, v in pol) else []
    top = max([p for d in paths for k in d for _, p in d[k]["series"]] + [p for _, p in stack]) * 1.1 or 1
    x = lambda a: L + (a - a0) / max(a1 - a0, 1) * (W - L - R_)
    pins, rows = [], []      # stagger pin labels into rows so they never overlap (6px gap between pills)
    for e in t["events"]:
        if not a0 <= e["age"] <= a1:
            continue
        ex, lab = x(e["age"]), short_event(e)
        w = len(lab) * 6.2 + 14
        cx = min(max(ex, w / 2 + 2), W - w / 2 - 2)
        r = next((i for i, end in enumerate(rows) if end < cx - w / 2 - 6), None)
        if r is None:
            rows.append(0)
            r = len(rows) - 1
        rows[r] = cx + w / 2
        pins.append((e, ex, cx, w, lab, r))
    T = 14 + len(rows) * 22 + 12      # pin area grows with the rows it needs
    H = T + 186
    y = lambda v: T + (1 - min(v, top) / top) * (H - T - B)
    ra = max(min(t["retire_age"], a1), a0)
    out = [f'<rect x="{L}" y="{T}" width="{x(ra) - L:.1f}" height="{H - T - B}" fill="{C["sand"]}"/>',
           f'<rect x="{x(ra):.1f}" y="{T}" width="{x(a1) - x(ra):.1f}" height="{H - T - B}" fill="#EEF5F4"/>']
    for f in (0.25, 0.5, 0.75, 1):
        v = top / 1.1 * f
        out.append(f'<line x1="{L}" x2="{W - R_}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{C["line"]}" stroke-width="1"/>'
                   f'<text x="{L - 6}" y="{y(v) + 3:.1f}" text-anchor="end" class="ax">{m(v)}</text>')
    pl = lambda ser: " ".join(f"{x(a):.1f},{y(p):.1f}" for a, p in ser)
    for d, col, dash in ((now, C["teal"], ""), (plan, C["navy"], ' stroke-dasharray="7 4"')):
        if not d:
            continue
        hi, lo = d["hopeful"]["series"], d["cautious"]["series"]
        band = pl(hi) + " " + pl(list(reversed(lo)))
        out.append(f'<polygon points="{band}" fill="{col}" opacity=".16"/>'
                   f'<polyline points="{pl(d["middle"]["series"])}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"{dash}/>')
    if stack:   # policy cash values sit on top of savings (not spendable unless cashed in)
        out.append(f'<polygon points="{pl(s)} {pl(list(reversed(stack)))}" fill="{C["amber"]}" opacity=".55"/>')
    for a in range((a0 // 10 + 1) * 10, a1 + 1, 10):
        out.append(f'<text x="{x(a):.1f}" y="{H - B + 15}" text-anchor="middle" class="ax">{a}</text>')
    out.append(f'<text x="{x(a0):.1f}" y="{H - B + 15}" text-anchor="middle" class="ax">{a0}</text>'
               f'<line x1="{L}" x2="{W - R_}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{C["muted"]}" stroke-width="1"/>'
               f'<text x="{(L + x(ra)) / 2:.1f}" y="{H - B - 6}" text-anchor="middle" class="ph">{"WORKING YEARS" if x(ra) - L > 90 else ""}</text>'
               f'<text x="{(x(ra) + x(a1)) / 2:.1f}" y="{H - B - 6}" text-anchor="middle" class="ph">RETIREMENT</text>')
    sd = dict(s)
    lines, pills = [], []
    for e, ex, cx, w, lab, r in pins:
        ly = 16 + r * 22
        col = KIND_COL.get(e["kind"], C["teal"])
        val = sd.get(e["age"], 0)
        lines.append(f'<line x1="{ex:.1f}" x2="{ex:.1f}" y1="{ly + 9}" y2="{y(val):.1f}" stroke="{col}" stroke-width="1.2" stroke-dasharray="3 3"/>'
                     f'<circle cx="{ex:.1f}" cy="{y(val):.1f}" r="4.5" fill="#fff" stroke="{col}" stroke-width="2.5"/>')
        pills.append(f'<rect x="{cx - w / 2:.1f}" y="{ly - 8}" width="{w:.1f}" height="17" rx="8.5" fill="{col}" stroke="#fff" stroke-width="1.5"/>'
                     f'<text x="{cx:.1f}" y="{ly + 4.3}" text-anchor="middle" class="pin">{E(lab)}</text>')
    out += lines + pills      # pills drawn last so no dashed line ever runs through a label
    key = (f'<div class="legend row" style="margin-top:1mm;font-size:8.5pt"><div class="lg"><i style="background:{C["teal"]}"></i>As things are today</div>'
           + (f'<div class="lg"><i style="background:{C["navy"]}"></i>With the plan</div>' if plan else "")
           + (f'<div class="lg"><i style="background:{C["amber"]}"></i>Policy cash values</div>' if stack else "")
           + '<div class="lg" style="color:#6B7489">Shaded: from cautious to hopeful markets. The middle line is in between.</div></div>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" class="life">{"".join(out)}</svg>{key}'


def plan_chart(t):
    """The plan on its own: drawing the full goal vs living on for-life income, with today's path faint behind."""
    W, H, L, R_, T, B = 640, 280, 52, 96, 30, 30
    a0, a1 = t["series"][0][0], t["plan_to"]
    lines = [(t["now"], C["teal"], "As things are", False), (t["plan"], C["navy"], "Plan, full goal", True),
             (t["forlife"], C["amber"], "Plan, for life", True)]
    top = max(p for d, *_ in lines for _, p in d["middle"]["series"]) * 1.3 or 1   # bands are clipped to this
    x = lambda a: L + (a - a0) / max(a1 - a0, 1) * (W - L - R_)
    y = lambda v: T + (1 - min(v, top) / top) * (H - T - B)
    ra = max(min(t["retire_age"], a1), a0)
    out = [f'<rect x="{L}" y="{T}" width="{x(ra) - L:.1f}" height="{H - T - B}" fill="{C["sand"]}"/>',
           f'<rect x="{x(ra):.1f}" y="{T}" width="{x(a1) - x(ra):.1f}" height="{H - T - B}" fill="#EEF5F4"/>']
    for f in (0.25, 0.5, 0.75, 1):
        v = top / 1.3 * f
        out.append(f'<line x1="{L}" x2="{x(a1)}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{C["line"]}"/>'
                   f'<text x="{L - 6}" y="{y(v) + 3:.1f}" text-anchor="end" class="ax">{m(v)}</text>')
    pl = lambda ser: " ".join(f"{x(a):.1f},{y(p):.1f}" for a, p in ser)
    ends = []
    for d, col, lab, band in lines:
        if band:
            out.append(f'<polygon points="{pl(d["hopeful"]["series"])} {pl(list(reversed(d["cautious"]["series"])))}" fill="{col}" opacity=".14"/>')
        sw, op = ("3", "1") if band else ("2", ".75")
        out.append(f'<polyline points="{pl(d["middle"]["series"])}" fill="none" stroke="{col}" stroke-width="{sw}" opacity="{op}" stroke-linejoin="round"/>')
        ends.append([y(d["middle"]["series"][-1][1]), col, lab, d["middle"]["series"][-1][1]])
    ends.sort(reverse=True)                 # keep end labels apart, stacking upwards from the bottom
    ends[0][0] = min(ends[0][0], H - B - 12)
    for i in range(1, len(ends)):
        ends[i][0] = min(ends[i][0], ends[i - 1][0] - 27)
    for ey, col, lab, val in ends:
        out.append(f'<text x="{x(a1) + 6}" y="{ey - 1:.1f}" class="endl" fill="{col}">{E(lab)}</text>'
                   f'<text x="{x(a1) + 6}" y="{ey + 10:.1f}" class="endv" fill="{col}">{m(val)}</text>')
    for a in range((a0 // 10 + 1) * 10, a1 + 1, 10):
        out.append(f'<text x="{x(a):.1f}" y="{H - B + 15}" text-anchor="middle" class="ax">{a}</text>')
    out.append(f'<text x="{x(a0):.1f}" y="{H - B + 15}" text-anchor="middle" class="ax">{a0}</text>'
               f'<line x1="{L}" x2="{x(a1)}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{C["muted"]}"/>'
               f'<line x1="{x(ra):.1f}" x2="{x(ra):.1f}" y1="{T}" y2="{y(0):.1f}" stroke="{C["amber"]}" stroke-dasharray="3 3"/>'
               f'<text x="{x(ra):.1f}" y="{T - 9}" text-anchor="middle" class="ph">RETIRE AT {t["retire_age"]:g}</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" class="life">{"".join(out)}</svg>'


def lasts_range(d, plan_to):
    ages = [d[k]["lasts"] or plan_to + 1 for k in ("cautious", "middle", "hopeful")]
    f = lambda a: f"{plan_to}+" if a > plan_to else str(a)
    return f(min(ages)) if min(ages) == max(ages) else f"{f(min(ages))}–{f(max(ages))}"


def dream_panel(t):
    """The goal we plan for: income for life that never touches the savings, so they are passed on."""
    fl, want = t.get("for_life"), t.get("want")
    if not fl:
        return ""
    now, plan = fl["now"], fl.get("plan")
    best = max(now, plan or 0)
    off = want and want > best * 3          # goal far off the scale: show it as text, not a marker
    top = max(best, 0 if off else (want or 0)) * 1.08 or 1
    bar = lambda v, col: (f'<div class="dr-bar"><div style="width:{max(v / top * 100, 3):.1f}%;background:{col}"></div>'
                          f'<strong>{m(v, False)} a month</strong></div>')
    mark = (f'<div class="dr-goal" style="left:calc(28mm + (100% - 28mm) * {want / top:.3f})"><span>Your goal {m(want, False)}</span></div>'
            if want and not off else "")
    rows = (f'<div class="dr-row"><div>As things are</div>{bar(now, C["teal"])}</div>'
            + (f'<div class="dr-row"><div>With the plan</div>{bar(plan, C["navy"])}</div>' if plan else "")
            + (f'<div class="dr-row"><div style="color:{C["amber"]};font-weight:700">Your goal</div>{bar(want, C["amber"])}</div>'
               if want and not off else ""))
    if want and best >= want:
        verdict = (f'<div class="dr-v ok">✓ Your {m(want, False)} a month is covered for life, and your savings keep growing '
                   f'for the people you love.</div>')
    elif want:
        cap = fl.get("capital_needed")
        verdict = (f'<div class="dr-v">Your goal is {m(want, False)} a month' + (" (let's confirm this together)" if off else "")
                   + (f'. For it never to run out, you\'d need about <b>{m(cap)}</b> invested by {t["retire_age"]:g}, '
                      f'or a mix of the steps below.' if cap else ".") + "</div>")
    else:
        verdict = '<div class="dr-v">Once we agree your retirement income goal, we\'ll show how close you are.</div>'
    return (f'<div class="dream"><div class="dr-h">The goal: money that never runs out</div>'
            f'<div class="dr-s">What your money could pay you every month for life, from lifelong income (CPF LIFE, annuities) '
            f'plus only the growth on your savings, so the savings themselves are left to pass on.</div>'
            f'<div class="dr-rows">{rows}</div>{verdict}</div>')


def lever_rows(t):
    """One bar per lever vs today. Working clients: money at retirement. Near/at retirement: age savings last to."""
    now, pt = t["now"]["middle"], t["plan_to"]
    by_money = t["retire_age"] - t["series"][0][0] >= 5
    val = (lambda d: d["at_retirement"]) if by_money else (lambda d: min(d["lasts"] or pt + 1, pt + 1))
    lab = (lambda d: m(d["at_retirement"]) + f' at {d.get("retire_age", t["retire_age"]):g}') if by_money else \
        (lambda d: (f'lasts to {d["lasts"]}' if d["lasts"] else f"lasts past {pt}")
                   + f' · {min(d["lasts"] or pt, pt) - t["retire_age"]:g} yrs of retirement')
    rows = [("As things are today", "", None, now)] + [(l["title"], l["how"], l["in_plan"], l) for l in t["levers"]]
    lo = 0 if by_money else min(t["retire_age"], pt)   # bar = years of retirement covered
    hi = max(val(d) for *_, d in rows) or 1
    out = []
    for title, how, in_plan, d in rows:
        w = max((val(d) - lo) / max(hi - lo, 1) * 100, 3)
        col = C["muted"] if in_plan is None else C["navy"] if in_plan else C["amber"]
        tag = "" if in_plan is None else f'<em class="{"inplan" if in_plan else "opt"}">{"In the plan" if in_plan else "Your choice"}</em>'
        out.append(f'<div class="lv"><div class="lv-t"><b>{E(title)}</b>{tag}<span>{E(how)}</span></div>'
                   f'<div class="lv-bar"><div style="width:{w:.1f}%;background:{col}"></div><strong>{E(lab(d))}</strong></div></div>')
    return '<div class="levers">' + "".join(out) + "</div>"


def life_path(t):
    """The milestones as a row of age bubbles, full wording."""
    return '<div class="path">' + "".join(
        f'<div class="pt"><i style="background:{KIND_COL.get(e["kind"], C["teal"])}">{e["age"]}</i><span>{E(e["label"])}</span></div>'
        for e in t["events"]) + "</div>"


CSS = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: {C['ink']}; font-size: 10.5pt; line-height: 1.5; background: #fff; }}
p, li, .lead, .s, span {{ text-wrap: pretty; }}
.page {{ width: 210mm; height: 297mm; padding: 13mm 16mm 20mm; position: relative; page-break-after: always; overflow: hidden; background: {C['paper']}; display: flex; flex-direction: column; }}
.page > * {{ flex: none; }}
.page > .disc {{ margin-top: auto !important; }}
.page:last-child {{ page-break-after: auto; }}
h2 {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 700; color: {C['navy']}; font-size: 21pt; margin: 1mm 0 2mm; letter-spacing: -.01em; }}
h3 {{ font-size: 11pt; color: {C['navy']}; margin: 6mm 0 3mm; text-transform: uppercase; letter-spacing: .08em; }}
.kicker {{ color: {C['coral']}; font-weight: 700; letter-spacing: .14em; font-size: 8.5pt; text-transform: uppercase; }}
.lead {{ font-size: 11pt; line-height: 1.55; color: {C['ink']}; max-width: 160mm; margin: 2mm 0 5mm; }}
.foot {{ position: absolute; bottom: 8mm; left: 16mm; right: 16mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: {C['muted']}; border-top: 1px solid {C['line']}; padding-top: 2mm; }}
/* cover */
.cover {{ background: {C['navy']}; color: #fff; padding: 0; display: block; }}
.cover .art {{ position: absolute; inset: 0; }}
.cover .inner {{ position: relative; padding: 30mm 18mm 0; }}
.cover h1 {{ max-width: 135mm; font-family: Georgia, serif; font-size: 40pt; line-height: 1.05; margin: 6mm 0 4mm; font-weight: 700; }}
.cover .for {{ font-size: 15pt; opacity: .92; }}
.cover .meta {{ margin-top: 3mm; font-size: 10pt; opacity: .75; }}
.badge {{ display: inline-block; background: {C['amber']}; color: {C['navy']}; font-weight: 700; padding: 1.5mm 4mm; border-radius: 20px; font-size: 9pt; letter-spacing: .06em; }}
.note {{ position: absolute; left: 18mm; right: 18mm; bottom: 26mm; background: #fff; color: {C['ink']}; border-radius: 6mm; padding: 7mm 8mm 6mm; box-shadow: 0 6px 20px rgba(0,0,0,.18); }}
.note .hand {{ font-family: 'Segoe Print', 'Segoe Script', cursive; font-size: 11pt; line-height: 1.6; color: {C['navy']}; }}
.note .sig {{ margin-top: 3mm; font-size: 9pt; color: {C['muted']}; }}
.cover .firm {{ position: absolute; left: 18mm; bottom: 12mm; font-size: 8.5pt; opacity: .7; }}
/* tiles */
.tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin: 2mm 0 3mm; }}
.tile {{ background: #fff; border: 1px solid {C['line']}; border-radius: 4mm; padding: 4mm; }}
.tile .v {{ font-family: Georgia, serif; font-size: 19pt; font-weight: 700; color: {C['navy']}; }}
.tile .l {{ font-size: 8.5pt; color: {C['muted']}; text-transform: uppercase; letter-spacing: .06em; }}
.tile .s {{ font-size: 8.5pt; line-height: 1.4; color: {C['ink']}; margin-top: 1.2mm; }}
.tile.accent {{ background: {C['sand']}; border-color: {C['sand']}; }}
/* bars & legends */
.bar {{ display: flex; height: 13mm; border-radius: 3mm; overflow: hidden; background: {C['line']}; }}
.seg {{ height: 100%; color: #fff; font-weight: 600; font-size: 9pt; display: flex; align-items: center; justify-content: center; white-space: nowrap; overflow: hidden; }}
.legend {{ display: flex; flex-direction: column; gap: 3mm; }}
.legend.row {{ flex-direction: row; flex-wrap: wrap; gap: 2.5mm 8mm; margin-top: 3.5mm; }}
.lg {{ display: flex; align-items: center; gap: 2mm; font-size: 9.5pt; }}
.lg i {{ width: 3.5mm; height: 3.5mm; border-radius: 1mm; display: inline-block; }}
.lg b {{ margin-left: 1.5mm; color: {C['navy']}; }}
.lg span {{ color: {C['muted']}; font-size: 8.5pt; margin-left: 1mm; }}
.flow-in {{ font-size: 10pt; color: {C['muted']}; margin-bottom: 2.5mm; }} .flow-in b {{ color: {C['navy']}; font-size: 12pt; }}
.donut {{ display: flex; align-items: center; gap: 8mm; }}
.d-top {{ font-family: Georgia, serif; font-size: 17px; font-weight: 700; fill: {C['navy']}; }}
.d-bot {{ font-size: 10px; fill: {C['muted']}; text-transform: uppercase; letter-spacing: .08em; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; align-items: start; }}
.panel {{ background: #fff; border: 1px solid {C['line']}; border-radius: 4mm; padding: 5.5mm 6mm; }}
/* scorecard */
.score {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3.5mm 4mm; }}
.sc {{ display: flex; gap: 3mm; align-items: flex-start; background: #fff; border: 1px solid {C['line']}; border-radius: 3mm; padding: 3.5mm 4mm; }}
.sc i {{ width: 4.5mm; height: 4.5mm; border-radius: 50%; flex: none; margin-top: .8mm; }}
.sc b {{ display: block; color: {C['navy']}; font-size: 10pt; margin-bottom: .5mm; }} .sc span {{ font-size: 9pt; line-height: 1.4; color: {C['muted']}; }}
/* good / not so good / bad */
.cards {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4mm; margin-top: 1mm; }}
.card {{ border-radius: 4mm; padding: 4.5mm 4.5mm 3mm; background: #fff; border: 1px solid {C['line']}; border-top: 4px solid; }}
.card.good {{ border-color: {C['teal']}; }} .card.mid {{ border-color: {C['amber']}; }} .card.bad {{ border-color: {C['coral']}; }}
.card-h {{ font-weight: 700; color: {C['navy']}; display: flex; align-items: center; gap: 2mm; font-size: 10.5pt; }}
.card ul {{ padding-left: 4.5mm; margin: 3mm 0 1mm; font-size: 9.5pt; line-height: 1.45; }} .card li {{ margin-bottom: 2.2mm; }}
.ic {{ display: inline-flex; width: 6mm; height: 6mm; border-radius: 50%; align-items: center; justify-content: center; color: #fff; font-size: 9pt; }}
.good .ic {{ background: {C['teal']}; }} .mid .ic {{ background: {C['amber']}; }} .bad .ic {{ background: {C['coral']}; }}
/* protection */
.covers {{ display: flex; flex-direction: column; gap: 9mm; margin: 1mm 0 8mm; }}
.cb-l {{ display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: {C['navy']}; margin-bottom: 1.8mm; }}
.cb-l em {{ font-style: normal; font-size: 9pt; padding: .5mm 2.5mm; border-radius: 10px; }}
.cb-l em.ok {{ background: #E3F3F1; color: {C['teal']}; }} .cb-l em.gap {{ background: #FBE7E2; color: {C['coral']}; }}
.cb-track {{ position: relative; height: 7.5mm; background: {C['line']}; border-radius: 2.5mm; }}
.cb-fill {{ height: 100%; border-radius: 2.5mm; display: flex; align-items: center; padding-left: 3mm; color: #fff; font-weight: 600; font-size: 9.5pt; }}
.tick {{ position: absolute; top: -1.5mm; bottom: -1.5mm; border-left: 2px dashed {C['navy']}; }}
.tick span {{ position: absolute; top: calc(100% + 1mm); left: 0; transform: translateX(-50%); white-space: nowrap; font-size: 8pt; font-weight: 600; color: {C['navy']}; }}
.tick.r span {{ left: auto; right: -1mm; transform: none; }} .tick.l span {{ left: -1mm; transform: none; }}
.chips {{ display: flex; gap: 3mm; flex-wrap: wrap; margin-top: 2mm; }}
.chip {{ display: flex; align-items: center; gap: 2mm; background: #fff; border: 1px solid {C['line']}; border-radius: 20px; padding: 2mm 4mm; font-size: 9.5pt; }}
.chip i {{ width: 5mm; height: 5mm; border-radius: 50%; color: #fff; font-style: normal; font-size: 8pt; display: inline-flex; align-items: center; justify-content: center; }}
/* retirement */
.ret-row {{ display: grid; grid-template-columns: 40mm 1fr; align-items: center; gap: 3mm; margin-bottom: 3mm; }}
.ret .bar {{ height: 10mm; }}
.ret-l {{ font-weight: 600; color: {C['navy']}; }}
.gapseg {{ background: repeating-linear-gradient(45deg, #FBE7E2, #FBE7E2 6px, #F6D2C8 6px, #F6D2C8 12px); color: {C['coral']}; }}
.gapdot {{ background: #F6D2C8; border: 1px solid {C['coral']}; }}
.g-big {{ font-family: Georgia, serif; font-size: 26px; font-weight: 700; fill: {C['navy']}; }} .g-sm {{ font-size: 10px; fill: {C['muted']}; }}
/* goals timeline */
.tl {{ position: relative; margin: 4mm 0 2mm; display: flex; gap: 4mm; }}
.tl .g {{ flex: 1; background: #fff; border: 1px solid {C['line']}; border-radius: 4mm; padding: 3.5mm 4mm; border-top: 4px solid {C['sky']}; }}
.tl .g b {{ display: block; color: {C['navy']}; }} .tl .g .amt {{ font-family: Georgia, serif; font-size: 13pt; font-weight: 700; color: {C['navy']}; }}
.tl .g span {{ font-size: 8.5pt; color: {C['muted']}; }}
/* actions */
.steps {{ display: flex; flex-direction: column; gap: 2.6mm; margin-top: 1mm; }}
.step {{ display: grid; grid-template-columns: 11mm 1fr; gap: 4mm; background: #fff; border: 1px solid {C['line']}; border-radius: 4mm; padding: 3mm 4.5mm; align-items: center; }}
.step .n {{ width: 11mm; height: 11mm; border-radius: 50%; background: {C['navy']}; color: #fff; font-family: Georgia, serif; font-weight: 700; font-size: 14pt; display: flex; align-items: center; justify-content: center; }}
.step:nth-child(1) .n {{ background: {C['coral']}; }} .step:nth-child(2) .n {{ background: {C['amber']}; }}
.step b {{ color: {C['navy']}; font-size: 11pt; }} .step p {{ margin: .8mm 0 0; font-size: 9.5pt; line-height: 1.45; }} .step .why {{ color: {C['muted']}; }}
.check {{ list-style: none; padding: 0; margin: 1mm 0 0; columns: 2; column-gap: 8mm; font-size: 9.5pt; line-height: 1.45; }}
.check li {{ padding-left: 6mm; position: relative; margin-bottom: 2.2mm; break-inside: avoid; }}
.check li:before {{ content: ''; position: absolute; left: 0; top: .9mm; width: 3.4mm; height: 3.4mm; border: 1.5px solid {C['teal']}; border-radius: 1mm; }}
/* legacy */
.legacy {{ display: flex; flex-direction: column; gap: 5mm; margin-top: 3mm; }}
.lgrow {{ display: grid; grid-template-columns: 30mm 1fr; gap: 3mm; align-items: center; }}
.lgname {{ font-weight: 700; color: {C['navy']}; }}
.lgb {{ position: relative; height: 6mm; background: {C['line']}; border-radius: 2mm; margin: 1mm 0; }}
.lgb div {{ height: 100%; border-radius: 2mm; }} .lgb span {{ position: absolute; left: 2mm; top: .3mm; font-size: 8.5pt; color: #fff; font-weight: 600; text-shadow: 0 0 2px rgba(0,0,0,.4); }}
.callout {{ background: {C['sand']}; border-radius: 4mm; padding: 4.5mm 5.5mm; font-size: 10pt; line-height: 1.55; margin-top: 6mm; }}
.callout b {{ color: {C['navy']}; }}
.take {{ margin-top: 8mm; background: {C['navy']}; color: #fff; border-radius: 5mm; padding: 6mm 7mm; position: relative; }}
.take .hand {{ font-family: 'Segoe Print', 'Segoe Script', cursive; font-size: 10.5pt; line-height: 1.6; }}
.take .sig {{ font-size: 8.5pt; opacity: .7; margin-top: 2mm; }}
.routes {{ display: flex; flex-direction: column; gap: 3mm; }}
.rt {{ display: grid; grid-template-columns: 62mm 14mm 1fr; align-items: center; }}
.rt-a {{ background: #fff; border: 1px solid {C['line']}; border-radius: 2.5mm; padding: 2mm 3mm; display: flex; justify-content: space-between; font-size: 9.5pt; }}
.rt-a span {{ color: {C['muted']}; }}
.rt-arrow {{ height: 2px; position: relative; }} .rt-arrow:after {{ content: ''; position: absolute; right: -1px; top: -4px; border: 5px solid transparent; border-left-color: inherit; }}
.rt-p {{ color: #fff; font-weight: 600; font-size: 9pt; border-radius: 20px; padding: 2mm 4mm; justify-self: start; }}
.ecl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2.5mm; }}
.ec {{ display: flex; align-items: center; gap: 2.5mm; background: #fff; border: 1px solid {C['line']}; border-radius: 3mm; padding: 2.5mm 3mm; font-size: 9.5pt; }}
.ec i {{ width: 5.5mm; height: 5.5mm; border-radius: 50%; color: #fff; font-style: normal; font-weight: 700; font-size: 9pt; display: inline-flex; align-items: center; justify-content: center; flex: none; }}
/* life timeline */
.life {{ display: block; margin-top: 1mm; }}
.life .ax {{ font-size: 10px; fill: {C['muted']}; }} .life .ph {{ font-size: 9px; fill: {C['muted']}; letter-spacing: .12em; font-weight: 700; }}
.life .pin {{ font-size: 10px; fill: #fff; font-weight: 700; }}
.path {{ display: flex; flex-wrap: wrap; gap: 2.5mm 3mm; margin-top: 0; }}
.pt {{ display: flex; align-items: center; gap: 2mm; background: #fff; border: 1px solid {C['line']}; border-radius: 20px; padding: 1mm 3.5mm 1mm 1mm; font-size: 9pt; }}
.pt i {{ font-style: normal; color: #fff; font-weight: 700; font-size: 8.5pt; width: 7.5mm; height: 7.5mm; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; flex: none; }}
.phases {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4mm; margin-top: 7mm; }}
.phase {{ background: #fff; border: 1px solid {C['line']}; border-radius: 4mm; padding: 3.5mm 4mm; position: relative; }}
.phase b {{ display: block; color: {C['navy']}; font-size: 10.5pt; }} .phase .ages {{ font-size: 8.5pt; color: {C['muted']}; text-transform: uppercase; letter-spacing: .06em; }}
.phase p {{ margin: 1.5mm 0 0; font-size: 9pt; line-height: 1.45; }}
.phase.here {{ border: 2px solid {C['coral']}; }}
.phase.here:after {{ content: 'You are here'; position: absolute; top: -2.6mm; right: 4mm; background: {C['coral']}; color: #fff; font-size: 7.5pt; font-weight: 700; padding: .4mm 2.5mm; border-radius: 10px; }}
/* dream panel */
.dream {{ background: {C['navy']}; color: #fff; border-radius: 5mm; padding: 5.5mm 7mm; margin-top: 1mm; }}
.dr-h {{ font-family: Georgia, serif; font-size: 14pt; font-weight: 700; }}
.dr-s {{ font-size: 8.5pt; line-height: 1.45; opacity: .8; margin: 1.5mm 0 4mm; }}
.dr-rows {{ position: relative; display: flex; flex-direction: column; gap: 2.5mm; padding-bottom: 0; }}
.dr-row {{ display: grid; grid-template-columns: 28mm 1fr; align-items: center; font-size: 9.5pt; }}
.dr-bar {{ display: flex; align-items: center; gap: 2.5mm; }} .dr-bar div {{ height: 6.5mm; border-radius: 2mm; }}
.dr-bar div[style*="{C['navy']}"] {{ background: #fff !important; }}
.dr-bar strong {{ white-space: nowrap; font-size: 10pt; }}
.dr-goal {{ position: absolute; top: -1mm; bottom: 0; border-left: 2px dashed {C['amber']}; }}
.dr-goal span {{ position: absolute; bottom: -3.5mm; left: 1.5mm; font-size: 7.5pt; color: {C['amber']}; white-space: nowrap; font-weight: 700; }}
.dr-v {{ margin-top: 4mm; font-size: 10pt; background: rgba(255,255,255,.1); border-radius: 3mm; padding: 2.5mm 3.5mm; }}
.dr-v.ok {{ background: {C['teal']}; font-weight: 600; }}
.life .endl {{ font-size: 9.5px; font-weight: 700; }} .life .endv {{ font-size: 10px; }}
.pcards {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4mm; margin-top: 6mm; }}
.pc {{ background: #fff; border: 1px solid {C['line']}; border-top: 4px solid; border-radius: 4mm; padding: 3.5mm 4mm; }}
.pc-l {{ font-size: 8pt; text-transform: uppercase; letter-spacing: .06em; color: {C['muted']}; }}
.pc b {{ display: block; color: {C['navy']}; font-size: 10pt; margin-top: 1mm; }}
.pc-v {{ font-family: Georgia, serif; font-size: 15pt; font-weight: 700; color: {C['navy']}; margin-top: 1mm; }}
.pc span {{ font-size: 8.5pt; color: {C['muted']}; }}
.pc.dreamc {{ background: #FFF7E8; }} .pc.dreamc .pc-v {{ color: #B7791F; }}
/* levers */
.levers {{ display: flex; flex-direction: column; gap: 3.5mm; margin-top: 1mm; }}
.lv {{ display: grid; grid-template-columns: 78mm 1fr; gap: 4mm; align-items: center; background: #fff; border: 1px solid {C['line']}; border-radius: 3.5mm; padding: 3mm 4mm; }}
.lv-t b {{ color: {C['navy']}; font-size: 10pt; }} .lv-t span {{ display: block; font-size: 8.5pt; color: {C['muted']}; margin-top: .5mm; }}
.lv-t em {{ font-style: normal; font-size: 7.5pt; font-weight: 700; padding: .3mm 2mm; border-radius: 10px; margin-left: 2mm; white-space: nowrap; }}
.lv-t em.inplan {{ background: {C['navy']}; color: #fff; }} .lv-t em.opt {{ background: #FCEFD9; color: #9A6510; }}
.lv-bar {{ display: flex; align-items: center; gap: 2.5mm; }} .lv-bar div {{ height: 6mm; border-radius: 2mm; }}
.lv-bar strong {{ font-size: 9.5pt; color: {C['navy']}; white-space: nowrap; }}
.what {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
.wt {{ background: #fff; border: 1px solid {C['line']}; border-left: 4px solid {C['teal']}; border-radius: 3mm; padding: 4mm 4.5mm; }}
.wt b {{ display: block; color: {C['navy']}; font-size: 10pt; margin-bottom: 1mm; }} .wt span {{ font-size: 9.5pt; line-height: 1.5; color: {C['ink']}; }}
.roomy .tl {{ margin: 6mm 0 4mm; gap: 5mm; }} .roomy .tl .g {{ padding: 5mm 5mm 4.5mm; }} .roomy .tl .g .amt {{ font-size: 17pt; margin: 1mm 0; }}
.roomy h3 {{ margin-top: 12mm; }} .roomy .ret .bar {{ height: 12mm; }} .roomy .ret-row {{ margin-bottom: 4mm; }}
.disc {{ font-size: 7.5pt; line-height: 1.5; color: {C['muted']}; margin-top: 6mm; border-top: 1px solid {C['line']}; padding-top: 3mm; }}
"""


def cover_art():
    # soft rising curves: a gentle "path forward" motif
    return ('<svg class="art" viewBox="0 0 210 297" preserveAspectRatio="none">'
            f'<circle cx="196" cy="22" r="40" fill="{C["coral"]}" opacity=".9"/>'
            f'<circle cx="196" cy="22" r="27" fill="{C["amber"]}" opacity=".9"/>'
            f'<path d="M0,210 C60,170 120,230 210,150 L210,297 L0,297 Z" fill="{C["teal"]}" opacity=".35"/>'
            f'<path d="M0,235 C70,200 140,250 210,190 L210,297 L0,297 Z" fill="{C["teal"]}" opacity=".55"/>'
            f'<path d="M0,262 C80,235 150,270 210,230 L210,297 L0,297 Z" fill="#0E1A31"/></svg>')


def foot(name, n):
    return f'<div class="foot"><span>{E(name)} · Financial Health Check</span><span>{E(ADVISER)} · {E(FIRM)}</span><span>{n}</span></div>'


def build(num, story, legacy=None):
    v, ret = num["visual"], num.get("retirement")
    name = story.get("client_name") or v.get("name") or ""
    first = name.split()[0] if name else ""
    date = story.get("date") or datetime.date.today().strftime("%d %B %Y")
    pages, pn = [], 1

    # ---- 1. cover
    pages.append(f'''<div class="page cover">{cover_art()}<div class="inner">
      <span class="badge">{E((v.get("stage") or "").replace("The ", "").upper())} STAGE</span>
      <h1>{E(story.get("title") or "Your Financial Health Check")}</h1>
      <div class="for">Prepared for {E(name)}</div><div class="meta">{E(date)}</div></div>
      <div class="note"><div class="hand">{E(story.get("adviser_note", ""))}</div>
      <div class="sig">— {E(ADVISER)}, your financial adviser</div></div>
      <div class="firm">{E(FIRM)}</div></div>''')

    # ---- 2. snapshot
    inc = v["income"]["take_home"]
    mo = v["money_out"]
    em = v["emergency"]
    late = v.get("stage") == "The Distributor"
    prot = [p for p in v["protection"] if p.get("target")]
    ok = sum(1 for p in prot if (p.get("have") or 0) >= p["target"])
    tiles = (f'<div class="tiles">'
             f'<div class="tile accent"><div class="l">What you own, less debts</div><div class="v">{m(v["net_worth"])}</div><div class="s">Net worth</div></div>'
             f'<div class="tile"><div class="l">Left over each month</div><div class="v">{m(mo["left_over"], False)}</div><div class="s">after spending &amp; saving</div></div>'
             f'<div class="tile"><div class="l">Emergency cushion</div><div class="v">{(em["months_have"] or 0):.0f} mo</div><div class="s">guideline {em["months_target"]:g} months</div></div>'
             + (f'<div class="tile"><div class="l">Long-term care</div><div class="v">{"In place" if v["ltc"] else "Not yet"}</div><div class="s">cover if you ever need care</div></div></div>'
              if late else f'<div class="tile"><div class="l">Protection</div><div class="v">{ok}/{len(prot)}</div><div class="s">areas meet the guideline</div></div></div>'))
    flow = flow_bar(inc, [("Day-to-day spending", mo["spending"], C["sky"]), ("Insurance", mo["insurance"], C["plum"]),
                          ("Regular savings", mo["savings"], C["teal"]), ("Left over", mo["left_over"], C["amber"])])
    assets = donut(list(v["assets"].items()), centre_top=m(sum(x for x in v["assets"].values())), centre_bottom="you own")
    pages.append(f'''<div class="page"><div class="kicker">01 · Snapshot</div><h2>Where you stand today</h2>
      <p class="lead">{E(story.get("where_you_stand", ""))}</p>{tiles}
      <h3>Your money each month</h3>{flow}
      <div class="two" style="margin-top:8mm"><div class="panel"><h3 style="margin-top:0">What you own</h3>{assets}</div>
      <div class="panel" style="text-align:center"><h3 style="margin-top:0;text-align:left">Emergency cushion</h3>
      {gauge(em["months_have"], em["months_target"], "months of spending in cash")}
      <div style="font-size:9pt;color:{C["muted"]}">Guideline for you: {em["months_target"]:g} months ({m(em["target_amount"], False)})</div></div></div>
      {foot(name, pn + 1)}</div>''')
    pn += 1

    # ---- 3. health check
    pages.append(f'''<div class="page"><div class="kicker">02 · Health check</div><h2>How your finances are doing</h2>
      <p class="lead">A quick check-up across the areas that matter most. Green is on track, amber is worth attention, red needs action.</p>
      {scorecard(v, ret)}
      <h3>What we found</h3><div class="cards">
      {cards("What's working", story.get("good"), "good", "✓")}
      {cards("Worth improving", story.get("not_so_good"), "mid", "!")}
      {cards("Needs action", story.get("bad"), "bad", "×")}</div>
      {f'<div class="take"><div class="hand">{E(story["adviser_take"])}</div><div class="sig">— {E(ADVISER)}</div></div>' if story.get("adviser_take") else ''}
      {foot(name, pn + 1)}</div>''')
    pn += 1

    # ---- 4. protection
    chips = "".join(f'<div class="chip"><i style="background:{C["teal"] if y else C["coral"]}">{"✓" if y else "×"}</i>{E(t)}</div>'
                    for t, y in (("Hospital plan", v["hospital"]), ("Hospital rider", v["hospital_rider"]),
                                 ("Long-term care", v["ltc"])))
    goals = [g for g in v.get("goals", []) if g.get("cost")]
    tl = "".join(f'<div class="g" style="border-top-color:{PALETTE[(i + 2) % 6]}"><span>{E(g.get("term") or "")}'
                 f'{" · " + str(int(g["year"])) if g.get("year") else " · date to set"}</span><b>{E(g["name"])}</b>'
                 f'<div class="amt">{m(g["cost"])}</div><span>{E(g["monthly"]) if g.get("year") else "We will set a date together"}</span></div>'
                 for i, g in enumerate(goals[:4]))
    ret_html = ""
    if ret:
        built = sum(x for _, x in (v.get("retirement_sources") or []) if x and x > 0)   # same sums as retirement_bar
        gap = max((ret["want"] or 0) - built, 0)
        ret_tiles = (f'<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin:1mm 0 6mm">'
                     f'<div class="tile accent"><div class="l">What you want</div><div class="v">{m(ret["want"], False)}</div><div class="s">a month in retirement</div></div>'
                     f'<div class="tile"><div class="l">Covered so far</div><div class="v">{m(built, False)}</div>'
                     f'<div class="s">{built / (ret["want"] or 1) * 100:.0f}% of your goal</div></div>'
                     f'<div class="tile"><div class="l">Still to find</div><div class="v"{f" style=color:{C["coral"]}" if gap else ""}>{m(gap, False)}</div>'
                     f'<div class="s">a month</div></div></div>') if ret.get("want") else ""
        ret_html = (f'<h3>Retirement at {v["retire_age"]:g}</h3><!--RT-->'
                    + retirement_bar(ret["want"], v.get("retirement_sources") or [])
                    + f'<p style="font-size:9.5pt;line-height:1.55;margin:4mm 0 0;max-width:160mm">{E(story.get("retirement_note", ""))}</p>')
    if late:
        rows = [{"label": r["label"].replace("Death / TPD", "Life cover · for your legacy").replace("Critical illness", "Critical illness · health buffer"),
                 "have": r["have"], "target": None} for r in v["protection"][:2] if r.get("have")]
        prot_panel = (cover_bars(rows) + f'<div class="chips">{chips}</div>'
                      f'<div style="font-size:8pt;line-height:1.5;color:{C["muted"]};margin-top:4mm">Income-replacement guidelines no longer apply once '
                      f'you stop working. What matters now is protecting your retirement money from big health and care costs.</div>')
        prot_title = "Protecting your retirement"
    else:
        prot_panel = (cover_bars(v["protection"]) + f'<div class="chips">{chips}</div>'
                      f'<div style="font-size:8pt;line-height:1.5;color:{C["muted"]};margin-top:4mm">Planners Inc guidelines, capped at your working years left: '
                      f'death/disability 12× income · critical illness 5× · early CI 3× · disability income 75% of salary.</div>')
        prot_title = "If something happens"
    prot_html = (f'''<div class="kicker">03 · Protection</div><h2>{prot_title}</h2>
      <p class="lead">{E(story.get("protection_note", "How your cover compares with the Planners Inc guidelines for someone at your stage of life."))}</p>
      <div class="panel">{prot_panel}</div>''')
    goals_html = (f'''<div class="kicker">04 · {"Retirement income" if late and not tl else "Your goals"}</div><h2>{"Your retirement paycheque" if late and not tl else "What you're working towards"}</h2>
      <p class="lead">{E(story.get("goals_note", ""))}</p>
      {f'<div class="tl">{tl}</div>' if tl else ''}
      {ret_html}''')
    ret_disc = ('<div class="disc">Retirement figures are a first sketch in today\'s dollars, using an illustrative 4% yearly drawdown '
                'and 2.5% inflation. They are not projections or guarantees.</div>') if ret else ""
    # one page when it fits comfortably; protection and goals get a page each when there is a lot of both
    n_bars = 2 if late else sum(1 for r in v["protection"] if r.get("target") is not None or r.get("have"))
    if tl and ret and n_bars >= 3:
        what = [(lab, txt) for lab, txt in COVER_WHAT if any(lab == (r.get("label") or "").replace(" (monthly)", "")
                                                         for r in v["protection"])]
        what_html = ('<h3>What each cover is for</h3><div class="what">' + "".join(
            f'<div class="wt"><b>{E(lab)}</b><span>{E(txt)}</span></div>' for lab, txt in what) + '</div>') if what else ""
        pages.append(f'<div class="page">{prot_html}{what_html}{foot(name, pn + 1)}</div>')
        pn += 1
        pages.append(f'<div class="page roomy">{goals_html.replace("<!--RT-->", ret_tiles)}{ret_disc}{foot(name, pn + 1)}</div>')
    else:
        pages.append(f'<div class="page">{prot_html}<div style="height:8mm"></div>{goals_html}{ret_disc}{foot(name, pn + 1)}</div>')
    pn += 1

    sec = 5
    # ---- 5. lifetime timeline (+ 5b. making it last)
    t = v.get("timeline")
    if t and t.get("now"):
        a0, ra, pt = t["series"][0][0], t["retire_age"], t["plan_to"]
        nm, pl = t["now"]["middle"], (t.get("plan") or {}).get("middle")
        rng = lasts_range(t["now"], pt)
        short = nm["lasts"] is not None
        plan_s = lambda txt: f'<div class="s" style="color:{C["navy"]};font-weight:600">With the plan: {txt}</div>' if pl else ""
        prop = t.get("property") or 0
        pleg = (t.get("policies") or {}).get("legacy") or 0
        tiles5 = (f'<div class="tiles" style="grid-template-columns:repeat(3,1fr)">'
                  f'<div class="tile accent"><div class="l">Ready to use at {ra:g}</div><div class="v">{m(nm["at_retirement"])}</div>'
                  f'<div class="s">as things are (middle case)</div>{plan_s(m(pl["at_retirement"]) if pl else "")}</div>'
                  f'<div class="tile"><div class="l">Savings last until</div><div class="v"{f" style=color:{C["red"]}" if short else ""}>'
                  f'{"Age " + rng if short else "For life ✓"}</div><div class="s">{"depending on markets" if short else "and still growing to pass on"}</div>'
                  f'{plan_s(lasts_range(t["plan"], pt)) if pl else ""}</div>'
                  f'<div class="tile"><div class="l">Left to pass on at {pt}</div><div class="v">{m(nm["left_at_end"] + pleg)}</div>'
                  f'<div class="s">{"savings + policy payouts" if pleg else "in savings"}{", plus your home (" + m(prop) + " today)" if prop else ""}</div>'
                  f'{plan_s(m(pl["left_at_end"] + pleg)) if pl else ""}</div></div>')
        here = "work" if a0 < ra else "ret"
        phases = (f'<div class="phases"><div class="phase{" here" if here == "work" else ""}" style="border-top:4px solid {C["amber"]}">'
                  f'<div class="ages">Age {a0}–{ra:g}</div><b>Working years</b><p>Insurance guards your income. If something happens, '
                  f'your cover replaces your salary for you and your family, while savings build up.</p></div>'
                  f'<div class="phase{" here" if here == "ret" else ""}" style="border-top:4px solid {C["teal"]}">'
                  f'<div class="ages">Age {ra:g}–{pt}</div><b>Retirement</b><p>Your money pays you. CPF LIFE, savings and investments '
                  f'become your paycheque, and health and care cover protect it.</p></div>'
                  f'<div class="phase" style="border-top:4px solid {C["plum"]}"><div class="ages">Beyond</div><b>Legacy</b>'
                  f'<p>What you pass on. Your will, nominations and remaining assets go to the people you choose.</p></div></div>')
        r = t["returns"]
        assume = (f'Illustrative only, in today\'s dollars. Cash is assumed to grow {r["cash"] * 100:.1f}% a year after inflation; invested money '
                  f'{r["cautious"] * 100:.1f}% (cautious), {r["middle"] * 100:.1f}% (middle) or {r["hopeful"] * 100:.1f}% (hopeful) after inflation'
                  + (f'; in retirement you draw {m(t["want"], False)} a month, less CPF LIFE and other lifelong income' if t.get("want") else "")
                  + '. Not a projection or guarantee; returns vary and investment values can fall.')
        pages.append(f'''<div class="page"><div class="kicker">0{sec} · Your timeline</div><h2>Your life, mapped out</h2>
          <p class="lead">{E(story.get("timeline_note") or f"How your money could move from today to age {pt}, in today's dollars, as you work, retire and plan what to pass on.")}</p>
          {tiles5}<div class="panel" style="padding:4mm 5mm 3mm">{life_chart(t)}</div>
          <h3>Milestones along the way</h3>{life_path(t)}{"" if (t.get("plan") and t.get("forlife")) else phases}
          <div class="disc">{E(assume)}</div>
          {foot(name, pn + 1)}</div>''')
        pn += 1
        sec += 1
        if t.get("levers"):
            by_money = ra - a0 >= 5
            pt_l = lasts_range(t["plan"], pt) if pl else None
            summary = ((f'<b>Doing the steps marked "In the plan"</b> could grow your money at {ra:g} from {m(nm["at_retirement"])} to about '
                        f'{m(pl["at_retirement"])}, and your savings would last to about {pt_l} depending on markets.') if pl and by_money else
                       (f'<b>Doing the steps marked "In the plan"</b> could make your savings last to about {pt_l} depending on markets, '
                        f'instead of {rng} as things are.') if pl else
                       '<b>Each of these is a choice we can weigh together.</b>')
            pages.append(f'''<div class="page"><div class="kicker">0{sec} · Making it {"grow" if by_money else "last"}</div>
              <h2>{"How to grow it and make it last" if by_money else "How to make your money last longer"}</h2>
              <p class="lead">{E(story.get("levers_note") or ("Whatever markets do, these are the things within your control. Each bar shows what one step does on its own (middle case)." ))}</p>
              {dream_panel(t)}
              <h3>{"Your money at " + format(ra, "g") + ", step by step" if by_money else "How long your savings last, step by step"}</h3>
              {lever_rows(t)}
              <div class="callout">{summary}</div>
              <div class="disc">{E(assume)} "Your choice" steps change how you live (when you retire or what you spend), so they are not
              counted in the plan unless you decide to.</div>
              {foot(name, pn + 1)}</div>''')
            pn += 1
            sec += 1
        if t.get("plan") and t.get("forlife"):
            fm, want = t["forlife_monthly"], t.get("want")
            fl = t["forlife"]["middle"]
            pc_html = (f'<div class="pcards">'
                     f'<div class="pc" style="border-top-color:{C["teal"]}"><div class="pc-l">As things are</div>'
                     + (f'<b>Spending {m(want, False)} a month</b><div class="pc-v">Lasts to {lasts_range(t["now"], pt)}</div>' if want else '<b>No goal set yet</b>')
                     + '<span>depending on markets</span></div>'
                     f'<div class="pc" style="border-top-color:{C["navy"]}"><div class="pc-l">With the plan</div>'
                     + (f'<b>Spending {m(want, False)} a month</b><div class="pc-v">Lasts to {lasts_range(t["plan"], pt)}</div>' if want else '<b>No goal set yet</b>')
                     + '<span>depending on markets</span></div>'
                     f'<div class="pc dreamc" style="border-top-color:{C["amber"]}"><div class="pc-l">With the plan, for life</div>'
                     f'<b>Spending {m(fm, False)} a month</b><div class="pc-v">Never runs out ✓</div>'
                     f'<span>about {m(fl["left_at_end"] + ((t.get("policies") or {}).get("legacy") or 0))} left to pass on at {pt}'
                     f'{" incl. policy payouts" if (t.get("policies") or {}).get("legacy") else ""} (middle case)</span></div></div>')
            pages.append(f'''<div class="page"><div class="kicker">0{sec} · Your plan</div><h2>Your plan, year by year</h2>
              <p class="lead">{E(story.get("plan_note") or f"The same plan, two ways to live on it. Spend your full goal and your savings are drawn down over time; live on what your money pays you for life and your savings stay whole, to pass on.")}</p>
              <div class="panel" style="padding:4mm 5mm 3mm">{plan_chart(t)}</div>
              {pc_html}{phases}
              <div class="callout" style="margin-top:6mm"><b>Where we're heading:</b> income that never runs out, with your savings still there for the people you love.
              Every step in the plan moves the gold line up: more growth before {ra:g} means more income for life after it.</div>
              <div class="disc">{E(assume)} "For life" spending is your lifelong income (CPF LIFE, annuities) plus only the growth on your savings in the middle case.</div>
              {foot(name, pn + 1)}</div>''')
            pn += 1
            sec += 1

    # ---- 6. legacy (optional)
    if legacy and legacy.get("now"):
        pages.append(f'''<div class="page"><div class="kicker">0{sec} · Legacy</div><h2>Who gets what</h2>
          <p class="lead">{E(story.get("legacy_note", ""))}</p>
          <div class="panel"><h3 style="margin-top:0">Share of what you leave</h3>{legacy_bars(legacy)}</div>
          {f'<h3>How each asset passes on today</h3>{route_map(legacy["channels"])}' if legacy.get("channels") else ''}
          {f'<h3>Your estate checklist</h3>{checklist(legacy["checklist"])}' if legacy.get("checklist") else ''}
          <div class="callout"><b>Three things decide who gets what:</b> your will, your CPF and insurance nominations, and how your
          property is held. A complete plan makes all three point the same way. We will draft it with an estate lawyer.</div>
          {foot(name, pn + 1)}</div>''')
        pn += 1
        sec += 1

    # ---- 7. plan
    steps = "".join(f'<div class="step"><div class="n">{i + 1}</div><div><b>{E(a.get("title", ""))}</b>'
                    f'<p class="why">{E(a.get("why", ""))}</p><p>{E(a.get("how", ""))}</p></div></div>'
                    for i, a in enumerate(story.get("actions", [])[:6]))
    pol_todo = ((v.get("timeline") or {}).get("policies") or {}).get("todo") or []
    names = []
    for x in pol_todo:      # one client-friendly line: which policies we need papers for
        names += [n.strip() for n in x.split(":", 1)[-1].split(",") if n.strip() not in names]
    pol_todo = ["Latest statements and benefit illustrations for: " + ", ".join(dict.fromkeys(names))] if names else []
    nxt = "".join(f"<li>{E(x)}</li>" for x in list(story.get("next_steps", [])) + pol_todo)
    pages.append(f'''<div class="page"><div class="kicker">0{sec} · Your plan</div>
      <h2>What we'll do, step by step</h2><p class="lead">In order of what matters most. Each step protects the ones after it.</p>
      <div class="steps">{steps}</div>
      {f'<h3>For our next meeting</h3><ul class="check">{nxt}</ul>' if nxt else ''}
      <div class="disc">{E(DISCLAIMER)}</div>
      {foot(name, pn + 1)}</div>''')
    return f'<!doctype html><html><head><meta charset="utf-8"><title>{E(name)} · Financial Health Check</title><style>{CSS}</style></head><body>{"".join(pages)}</body></html>'


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    num = json.load(open(a[0], encoding="utf-8"))
    story = json.load(open(a[1], encoding="utf-8"))
    legacy = json.load(open(a[a.index("--legacy") + 1], encoding="utf-8")) if "--legacy" in a else None
    out = a[a.index("--out") + 1] if "--out" in a else os.path.splitext(a[1])[0].replace("-story", "") + "-client.pdf"
    page = build(num, story, legacy)
    out = os.path.abspath(out)
    tmp = os.path.splitext(out)[0] + ".html"
    open(tmp, "w", encoding="utf-8").write(page)
    try:
        subprocess.run([_browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer", "--print-background",
                        f"--print-to-pdf={out}", "file://" + ("/" if os.name == "nt" else "") + tmp.replace("\\", "/")],
                       check=True, timeout=120, capture_output=True)
    finally:
        if "--html" not in a:
            os.remove(tmp)
    if not os.path.exists(out):
        sys.exit("PDF was not created.")
    print(out)


if __name__ == "__main__":
    main()

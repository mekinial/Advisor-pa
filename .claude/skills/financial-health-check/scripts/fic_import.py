"""Turn a client's FIC (Export tab) into the health check's fact-find JSON.

  ./pa fic_import <fic-raw.json> --out <first name>-factfind.json

<fic-raw.json> is what Claude saves after reading the client's FIC with the Sheets connector.

v3 FIC (Export tab has a "fic.version" row): ONE read.
  {"source": "<FIC file name> (Google Drive, read <date>)",
   "export_all": values of  Export!A1:AM115}
  Columns A-B are the field | value rows. From column E the tab carries the tables, each under a "## name"
  marker with its own heading row: policies, goals_st, goals_mt, goals_lt, dependants, lifelong, and (optional,
  from the Investments tab) holdings.

v2 FIC (Export tab without "fic.version"): the seven ranges, as before.
  {"source": ..., "export": Export!A1:B80, "policies": 'Existing Policies'!A7:AE40,
   "goals_st": Goals!C14:H18, "goals_mt": Goals!I14:N18, "goals_lt": Goals!O14:S18,
   "dependants": 'About You & Estate'!B14:F19, "lifelong": 'About You & Estate'!B33:F38}

Every table is read BY COLUMN HEADING, never by position, so a column that was added or moved cannot shift the
numbers. If a heading the health check needs is missing, it stops and says which one.
Anything blank stays null, so the calculator lists it as missing. Policy numbers are never copied.
"""
import json, re, sys, datetime

SUPPORTED = 3   # newest FIC layout this importer knows

# v2 column order, used only when a v2 FIC is read without its heading row
V2_POLICY_HEAD = ["Company", "Policy Name", "Policy Term /Start Date", "Policy Number", "Policy Purpose",
                  "Death & TPD Provision", "TI Provision", "Early Payout Critical Illness Provision",
                  "Critical Illness Provision", "Accidental Death Provision", "Accidental Perm. Disablement Provision",
                  "Hospital & Surgical, Medical Expenses Reimbursement", "Loss of Income Provision", "Riders / Others",
                  "Annual Premium", "Payment Mode / Details", "Cash Portion / Notes", "Start Date", "Cover Ends at Age",
                  "Cash / Surrender Value", "Value as at (date)", "Projected Value at Retirement Age (from illustration)",
                  "Maturity Age", "Maturity Amount", "Payout per Year", "Payout from Age", "Payout Guaranteed? (Y/N)",
                  "Death Benefit Only (e.g. annuity, no TPD)", "Nominated? (None / Revocable / Trust) & Nominee",
                  "Premium Ends (year)", "Who Pays (self / parent / CPF / MediSave)"]
V2_GOAL_HEAD = ["Goals", "", "Amount", "", "Target year", "Saved so far"]
V2_GOAL_LT_HEAD = ["Goals", "", "Amount", "Target year", "Saved so far"]
DEP_HEAD = ["Name", "Relation", "Age", "Monthly support", "Years of support left"]
LIFE_HEAD = ["Source", "Monthly", "From age", "To age", "Guaranteed? (Y/N)"]

# key -> how to recognise its heading (after lower-casing and squeezing spaces). "=" exact, "^" starts with, else contains
POLICY_COLS = {
    "company": "^company", "plan": "policy name", "purpose": "policy purpose", "death_tpd": "death & tpd",
    "ti": "^ti ", "early_ci": "early payout critical", "ci": "^critical illness", "accidental_death": "accidental death",
    "apd": "accidental perm", "hospital": "hospital & surgical", "loss_income": "loss of income",
    "annual_premium": "annual premium", "payment_mode": "payment mode", "ends_age": "cover ends",
    "cash_value": "cash / surrender value", "value_date": "value as at", "value_at_ret": "projected value",
    "maturity_age": "maturity age", "maturity_amount": "maturity amount", "payout_year": "payout per year",
    "payout_from": "payout from age", "payout_guaranteed": "payout guaranteed", "death_benefit": "death benefit only",
    "nominated": "^nominated", "premium_ends": "premium ends", "who_pays": "who pays",
    "status": "=status", "ptype": "=policy type", "whose": "whose policy", "ward": "hospital ward", "rider": "hospital rider",
}
POLICY_NEED = ("plan", "death_tpd", "annual_premium")
GOAL_COLS = {"name": "^goal", "cost": "^amount", "year": "target year", "saved": "saved"}
DEP_COLS = {"name": "^name", "relation": "relation", "age": "^age", "monthly_support": "monthly support", "support_years": "years of support"}
LIFE_COLS = {"label": "^source", "amount": "^monthly", "from_age": "from age", "to_age": "to age", "guaranteed": "guaranteed"}
HOLD_COLS = {"name": "^fund or platform", "type": "=type", "value": "^value", "monthly_topup": "monthly top-up", "as_at": "^as at"}

TYPE_FROM_LIST = {  # the v3 "Policy Type" dropdown -> the calculator's type words
    "term": "term", "whole life": "whole life", "critical illness": "critical illness", "hospital plan": "IP",
    "hospital plan rider": "IP rider", "medishield life": "MediShield Life", "personal accident": "personal accident",
    "disability income": "disability income", "long-term care": "long-term care", "endowment / savings": "endowment",
    "annuity": "annuity (single premium)", "investment-linked": "whole life ILP", "other": "policy",
}
SAMPLE = {  # Mr Prospect's figures in the Master Copy: leftovers in a client's copy are flagged
    "income.gross_monthly": 13333, "assets.cash": 30000, "assets.cpf_oa": 77894, "assets.cpf_sa": 21569,
    "assets.cpf_ma": 29650, "assets.unit_trusts": 150000, "assets.policy_cash_value": 81000, "assets.home": 950000,
    "liabilities.mortgage_home": 475000,
}


def num(v):
    """'$1,234.50' -> 1234.5, '2.5%' -> 0.025, '' -> None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("S$", "").replace("$", "")
    if not s or s in ("-", "—", "?"):
        return None
    pct = s.endswith("%")
    s = s.rstrip("%").strip()
    try:
        x = float(s)
    except ValueError:
        m = re.search(r"-?\d+(\.\d+)?", s)
        if not m:
            return None
        x = float(m.group())
    return x / 100 if pct else x


def text(v):
    s = "" if v is None else str(v).strip()
    return s or None


def yes_no(v):
    s = (text(v) or "").lower()
    if s.startswith("y") or s == "true":
        return True
    if s.startswith("n") and not s.startswith("not") or s == "false":
        return False
    return None


def norm(h):
    return " ".join(str(h or "").lower().split())


def parse_date(v):
    s = text(v)
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%b %Y", "%B %Y", "%m/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def table(rows, cols, need=(), what="table"):
    """rows[0] is the heading row. Returns one dict per data row, keyed by cols' keys. Stops if a needed heading is gone."""
    if not rows:
        return []
    heads = [norm(h) + " " for h in rows[0]]
    idx = {}
    for key, pat in cols.items():
        for i, h in enumerate(heads):
            hit = (h.strip() == pat[1:]) if pat.startswith("=") else h.startswith(pat[1:]) if pat.startswith("^") else pat in h
            if hit and i not in idx.values():
                idx[key] = i
                break
    gone = [k for k in need if k not in idx]
    if gone:
        sys.exit(f"STOP: the {what} is missing the heading(s) for: {', '.join(gone)}. This FIC's layout doesn't match "
                 f"what the importer knows. Nothing was imported; check the heading row before trying again.")
    return [{k: (r[i] if i < len(r) else None) for k, i in idx.items()} for r in rows[1:]]


def sections(export_all):
    """Split the v3 Export tab: fields from columns A-B, tables from column E under their '## name' markers."""
    fields = [r[:2] for r in export_all if r and text(r[0])]
    out, cur = {}, None
    for r in export_all:
        cell = text(r[4]) if len(r) > 4 else None
        if cell and cell.startswith("##"):
            cur = cell.lstrip("# ").strip()
            out[cur] = []
            continue
        if cur and cur != "end":
            out[cur].append(list(r[4:]))
    for k in out:  # drop blank rows at the end of each table
        while out[k] and not any(text(x) for x in out[k][-1]):
            out[k].pop()
    return fields, out


def policy_type(purpose, name):
    p = f"{purpose or ''} {name or ''}".lower()
    for pat, t in (("\\bmsl\\b|medishield", "MediShield Life"), ("care ?shield|carshield|eldershield|long.term (care|disab)", "long-term care"),
                   ("annuit", "annuity (single premium)"), ("endowment", "endowment"), ("ilp|investment.linked", "whole life ILP"),
                   ("whole life", "whole life"), ("wealth|accumulation", "investment-linked / wealth"),
                   ("rider.*hosp|hosp.*rider|hns rider|total ?care", "IP rider"),
                   ("shield|supreme ?health|hns|hosp|reimburs", "IP"), ("accident", "personal accident"),
                   ("disab|payassure", "disability income"), ("critical|criticare", "critical illness"), ("term", "term")):
        if re.search(pat, p):
            return t
    return purpose or "policy"


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    raw = json.load(open(a[0], encoding="utf-8"))
    out = a[a.index("--out") + 1] if "--out" in a else None
    notes, missing = [], []

    if "export_all" in raw:                                    # v3: one read
        fields, sec = sections(raw["export_all"])
        ex = {str(r[0]).strip(): (r[1] if len(r) > 1 else None) for r in fields}
        ver = num(ex.get("fic.version"))
        if not ver:
            sys.exit("STOP: this Export tab has no 'fic.version' row, so it is the older (v2) layout. Read the seven v2 "
                     "ranges instead (see the top of fic_import.py). Nothing was imported.")
        if ver > SUPPORTED:
            notes.append(f"This FIC is layout v{ver:g}; the importer knows up to v{SUPPORTED}. Check the figures carefully.")
        for k in ("policies", "goals_st", "goals_mt", "goals_lt", "dependants", "lifelong"):
            if k not in sec:
                sys.exit(f"STOP: the Export tab has no '## {k}' table. Read Export!A1:AM115 in full. Nothing was imported.")
        pol_rows, st_rows, mt_rows, lt_rows = sec["policies"], sec["goals_st"], sec["goals_mt"], sec["goals_lt"]
        dep_rows, life_rows = sec["dependants"], sec["lifelong"]
        hold_rows = sec.get("holdings", [])                    # optional: FICs without the new Investments tab have none
    else:                                                      # v2: seven ranges, headings added from the known order
        ex = {str(r[0]).strip(): (r[1] if len(r) > 1 else None) for r in raw.get("export", []) if r and r[0]}
        ver = 2
        pol_rows = [V2_POLICY_HEAD] + raw.get("policies", [])
        st_rows = [V2_GOAL_HEAD] + raw.get("goals_st", [])
        mt_rows = [V2_GOAL_HEAD] + raw.get("goals_mt", [])
        lt_rows = [V2_GOAL_LT_HEAD] + raw.get("goals_lt", [])
        dep_rows = [DEP_HEAD] + raw.get("dependants", [])
        life_rows = [LIFE_HEAD] + raw.get("lifelong", [])
        hold_rows = []
    g = lambda k: ex.get(k)
    n = lambda k: num(ex.get(k))

    name = text(g("client.name"))
    if name and name.lower().startswith("mr prospect"):
        notes.append("This FIC still shows the 'Mr Prospect' demo: the figures may be template samples, not the client's.")
    else:
        same = [k for k, v in SAMPLE.items() if n(k) is not None and round(n(k)) == v]
        if len(same) >= 3:
            notes.append("These figures are identical to the Master Copy's sample (Mr Prospect) and may be leftovers, not the "
                         "client's own: " + ", ".join(same) + ". Confirm each one.")

    ffd = text(g("fact_find_date"))
    if ver >= 3 and not ffd:
        missing.append("date of this review (About You & Estate)")
    ffd_date = parse_date(ffd) or datetime.date.today()

    exp = {k: n(f"expenses.{k}") for k in ("mortgage", "loans", "family", "tax", "food", "transport", "bills", "subscriptions",
                                          "memberships", "shopping", "personal", "insurance", "committed_savings")}
    f = {
        "_sources": raw.get("source", f"Client FIC (v{ver:g}), Export tab"),
        "fic_layout": ver,
        "fact_find_date": ffd_date.isoformat(),
        "client": {
            "name": name, "age": n("client.age"),
            "marital_status": (text(g("client.marital_status")) or "").lower() or None,
            "children": n("client.children"),
            "income_irregular": str(g("client.income_irregular")).upper() == "TRUE",
            "dependants": [],
        },
        "income": {"gross_monthly": n("income.gross_monthly"), "take_home_monthly": n("income.take_home_monthly"),
                   "bonus_annual": n("income.bonus_annual"), "rental_monthly": None, "other_monthly": None},
        "expenses": {
            "family": exp["family"], "bills": sum(x or 0 for x in (exp["bills"], exp["subscriptions"], exp["memberships"])),
            "tax": exp["tax"], "loans": (exp["mortgage"] or 0) + (exp["loans"] or 0), "food": exp["food"],
            "transport": exp["transport"], "insurance": exp["insurance"], "charity": 0,
            "personal": (exp["personal"] or 0) + (exp["shopping"] or 0), "committed_savings": exp["committed_savings"],
            "discretionary": 0, "other": 0,
        },
        "fixed_expense_keys": ["family", "bills", "tax", "loans", "insurance"],
        "debt_repayments_monthly": {"mortgage": exp["mortgage"], "non_mortgage": exp["loans"]},
        "assets": {
            "cash": n("assets.cash"), "cpf_oa": n("assets.cpf_oa"),
            "cpf_sa": (n("assets.cpf_sa") or 0) + (n("assets.cpf_ra") or 0) if (n("assets.cpf_sa") is not None or n("assets.cpf_ra") is not None) else None,
            "cpf_ma": n("assets.cpf_ma"), "cpf_investments": n("assets.cpf_investments"),
            "home": n("assets.home"), "investment_property": n("assets.other_property"),
            "unit_trusts": n("assets.unit_trusts"), "bonds": n("assets.bonds"),
            "policy_cash_value": n("assets.policy_cash_value"), "srs": n("assets.srs"),
            "other_investments": n("assets.annuities"), "personal_use": n("assets.personal"),
        },
        "liabilities": {"mortgage_home": n("liabilities.mortgage_home"), "mortgage_investment": n("liabilities.mortgage_investment"),
                        "car_loan": n("liabilities.car"), "study_loan": n("liabilities.study"),
                        "renovation_loan": n("liabilities.renovation"), "instalments": n("liabilities.instalments")},
        "insurance": [],
        "insurance_family": [],
        "national": {"has_ip": None, "ip_ward": None, "has_rider": None, "careshield": None},
        "legacy": {"will": yes_no(g("legacy.will")), "cpf_nomination": yes_no(g("legacy.cpf_nomination")),
                   "lpa": yes_no(g("legacy.lpa")), "acp": yes_no(g("legacy.acp")), "target_amount": n("legacy.target_amount")},
        "estate_hints": {"home_type": text(g("estate.home_type")), "home_holding": text(g("estate.home_holding")),
                         "co_owner": text(g("estate.co_owner")), "wish": text(g("estate.wish")),
                         "wish_detail": text(g("estate.wish_detail")), "executor": text(g("legacy.executor")),
                         "_note": "For legacy_plan.py: build the estate block from these plus the policies' nominations."},
        "retirement": {
            "retire_age": n("retirement.retire_age"), "monthly_today": n("retirement.monthly_today"),
            "cpf_life_monthly": n("retirement.cpf_life_monthly"), "spouse_cpf_life_monthly": n("retirement.spouse_cpf_life_monthly"),
            "other_monthly_income": [], "srs_at_retirement": None, "srs_draw_years": 10, "drawdown_rate": 0.04,
            "cpf_oa_withdrawable": str(g("retirement.cpf_oa_withdrawable")).upper() == "TRUE",
            "plan_to_age": n("retirement.plan_to_age") or 90, "cpf_life_start_age": n("retirement.cpf_life_start_age") or 65,
        },
        "goals": [],
        "assumptions": {
            "inflation": n("assumptions.inflation") or 0.025, "cash_return": n("assumptions.cash_return") or 0.015,
            "return_pre_retirement": n("assumptions.scenario_returns.middle") or 0.04,
            "return_post_retirement": n("assumptions.scenario_returns.middle") or 0.04,
            "scenario_returns": {"cautious": n("assumptions.scenario_returns.cautious") or 0.025,
                                 "middle": n("assumptions.scenario_returns.middle") or 0.04,
                                 "hopeful": n("assumptions.scenario_returns.hopeful") or 0.06},
            "family_share_of_spending": 0.7, "goal_returns": {"ST": 0.02, "MT": 0.03, "LT": 0.04},
        },
        "wealth_insights": {"what_wealth_means": text(g("wealth_insights.what_wealth_means")),
                            "biggest_money_worry": text(g("wealth_insights.biggest_money_worry")),
                            "ideal_lifestyle": text(g("wealth_insights.ideal_lifestyle"))},
    }
    age = f["client"]["age"]

    # dependants
    for d in table(dep_rows, DEP_COLS, what="dependants table"):
        if text(d.get("name")) or text(d.get("relation")):
            f["client"]["dependants"].append({"name": text(d.get("name")), "relation": text(d.get("relation")),
                                              "age": num(d.get("age")), "monthly_support": num(d.get("monthly_support")),
                                              "support_years": num(d.get("support_years"))})
    # lifelong income (rental already coming in also counts as income today)
    rent_now = 0
    for d in table(life_rows, LIFE_COLS, what="lifelong income table"):
        if text(d.get("label")) and num(d.get("amount")):
            fa = num(d.get("from_age"))
            f["retirement"]["other_monthly_income"].append({"label": text(d["label"]), "amount": num(d["amount"]),
                                                            "from_age": fa, "to_age": num(d.get("to_age")),
                                                            "guaranteed": yes_no(d.get("guaranteed"))})
            if "rent" in text(d["label"]).lower() and (fa is None or (age is not None and fa <= age)):
                rent_now += num(d["amount"])
    if rent_now:
        f["income"]["rental_monthly"] = rent_now

    # what they hold today (Investments tab) and their risk profile: both optional
    holdings, old_hold = [], []
    for h in table(hold_rows, HOLD_COLS, what="holdings table"):
        hname = text(h.get("name"))
        if not hname or hname.lower() == "total":
            continue
        row = {"name": hname, "type": text(h.get("type")), "value": num(h.get("value")),
               "monthly_topup": num(h.get("monthly_topup")), "as_at": text(h.get("as_at"))}
        hd = parse_date(row["as_at"])
        if hd and (ffd_date - hd).days > 365:
            old_hold.append(f"{hname} (as at {hd:%b %Y})")
        holdings.append({k: v for k, v in row.items() if v is not None})
    if holdings:
        f["holdings"] = holdings
        held = sum(h.get("value") or 0 for h in holdings)
        al = f["assets"]["unit_trusts"]
        if al is not None and abs(held - al) > 1:
            notes.append(f"Holdings on the Investments tab add up to ${held:,.0f} but the Assets & Liabilities tab shows "
                         f"${al:,.0f} for investments. Confirm which is right.")
        if old_hold:
            notes.append("Holding values more than a year old, ask for a current statement: " + "; ".join(old_hold) + ".")
    inv = {"risk_profile": text(g("investments.risk_profile")), "risk_assessed_on": text(g("investments.risk_assessed_on")),
           "yearly_addition": n("investments.yearly_addition")}
    if any(v is not None for v in inv.values()):
        f["investments"] = inv
        if holdings and not inv["risk_profile"]:
            missing.append("risk profile (Investments tab)")

    # policies
    pay_from_policies, stale, untyped = [], [], []
    for p_ in table(pol_rows, POLICY_COLS, POLICY_NEED, "Existing Policies table"):
        a0, plan = text(p_.get("company")), text(p_.get("plan"))
        if a0 and a0.lower().startswith("total"):
            break
        if not plan or plan.lower() in ("employee benefits",):
            continue
        plan = " ".join(plan.split())
        status = (text(p_.get("status")) or "").lower()
        mode = (text(p_.get("payment_mode")) or "").lower()
        if status and not status.startswith("in force"):
            word = "proposed, not bought yet" if status.startswith("proposed") else text(p_.get("status"))
            notes.append(f"{plan} is marked '{word}' in the FIC: left out of the cover totals.")
            continue
        if not status and re.search(r"laps|surrender(ed)?$|terminated|cancel", mode):
            notes.append(f"{plan} is marked '{text(p_.get('payment_mode'))}' in the FIC: left out of the cover totals. Confirm it's no longer in force.")
            continue
        purpose = text(p_.get("purpose"))
        listed = (text(p_.get("ptype")) or "").lower()
        typ = TYPE_FROM_LIST.get(listed) or policy_type(purpose, plan)
        if ver >= 3 and not listed:
            untyped.append(plan)
        p = {"insurer": a0, "plan": plan, "type": typ,
             "death_tpd": num(p_.get("death_tpd")), "ti": num(p_.get("ti")), "early_ci": num(p_.get("early_ci")),
             "ci": num(p_.get("ci")), "accidental_death": num(p_.get("accidental_death")), "apd": num(p_.get("apd")),
             "hospital": text(p_.get("hospital")) if typ.startswith("IP") else None,
             "ward": text(p_.get("ward")) if typ.startswith("IP") else None,
             "loss_of_income_monthly": num(p_.get("loss_income")), "annual_premium": num(p_.get("annual_premium")),
             "ends_age": num(p_.get("ends_age")), "cash_value": num(p_.get("cash_value")),
             "cash_value_date": text(p_.get("value_date")),
             "cash_value_at_retirement": num(p_.get("value_at_ret")),
             "maturity_age": num(p_.get("maturity_age")), "maturity_amount": num(p_.get("maturity_amount")),
             "death_benefit": num(p_.get("death_benefit")), "nominated": text(p_.get("nominated")),
             "premium_ends": text(p_.get("premium_ends")), "who_pays": text(p_.get("who_pays")), "count_for_retirement": False}
        if typ.startswith("annuity") and p["death_tpd"] and not p["death_benefit"]:
            p["death_benefit"], p["death_tpd"] = p["death_tpd"], None      # annuity death benefits have no TPD
        clean = {k: v for k, v in p.items() if v is not None or k in ("cash_value", "nominated")}
        whose = (text(p_.get("whose")) or "self").lower()
        if whose != "self":
            clean["whose"] = whose
            f["insurance_family"].append(clean)
            notes.append(f"{plan} covers the client's {whose}, not the client: left out of the client's cover totals.")
            continue
        if yes_no(p_.get("rider")) is not None and typ == "IP":
            clean["rider"] = yes_no(p_.get("rider"))
        if p["cash_value"] is not None:
            vd = parse_date(p["cash_value_date"])
            if vd and (ffd_date - vd).days > 365:
                stale.append(f"{plan} (as at {vd:%b %Y})")
        if num(p_.get("payout_year")):
            pay_from_policies.append({"label": f"{plan} payout", "amount": round(num(p_["payout_year"]) / 12, 2),
                                      "from_age": num(p_.get("payout_from")), "guaranteed": yes_no(p_.get("payout_guaranteed"))})
        f["insurance"].append(clean)
    if not f["retirement"]["other_monthly_income"]:
        f["retirement"]["other_monthly_income"] = pay_from_policies
    if not f["insurance_family"]:
        del f["insurance_family"]
    ips = [p for p in f["insurance"] if p["type"] == "IP" and not re.search(r"msl|medishield", p["plan"].lower())]
    names = " ".join(f"{p['plan']} {p['type']}".lower() for p in f["insurance"])
    f["national"]["has_ip"] = bool(ips)
    riders = [p["rider"] for p in ips if "rider" in p]
    f["national"]["has_rider"] = any(p["type"] == "IP rider" for p in f["insurance"]) or (any(riders) if riders else False)
    f["national"]["ip_ward"] = next((p["ward"] for p in ips if p.get("ward")), None)
    f["national"]["careshield"] = bool(re.search(r"care ?shield|carshield|long-term care", names))
    if stale:
        notes.append("Cash values more than a year old, ask for a current statement: " + "; ".join(stale) + ".")
    if untyped:
        notes.append("No Policy Type picked in the FIC, so the type was guessed from the name: " + ", ".join(untyped) + ".")
    if ver >= 3 and ips and not f["national"]["ip_ward"]:
        missing.append("hospital plan ward class")

    # goals
    def add_goals(rows, term, head):
        for gl in table(rows, GOAL_COLS, ("name", "cost"), f"{head} goals table"):
            gname = text(gl.get("name"))
            if not gname or "retirement income" in gname.lower():
                continue
            f["goals"].append({"name": gname, "term": term, "cost": num(gl.get("cost")), "year": num(gl.get("year")),
                               "saved": num(gl.get("saved")) or 0})
    add_goals(st_rows, "ST", "short-term")
    add_goals(mt_rows, "MT", "medium-term")
    add_goals(lt_rows, "LT", "long-term")

    # what's still missing (also the PDF's next-meeting list)
    checks = [("date of birth / age", f["client"]["age"]), ("marital status", f["client"]["marital_status"]),
              ("gross income", f["income"]["gross_monthly"]), ("retirement age", f["retirement"]["retire_age"]),
              ("retirement income wanted", f["retirement"]["monthly_today"]), ("CPF LIFE estimate", f["retirement"]["cpf_life_monthly"]),
              ("will", f["legacy"]["will"]), ("CPF nomination", f["legacy"]["cpf_nomination"]),
              ("how the home is held", f["estate_hints"]["home_holding"])]
    missing += [k for k, v in checks if v is None]
    missing += [f"target year for {gl['name']}" for gl in f["goals"] if gl["year"] is None]
    f["_missing_from_fic"] = missing
    if notes:
        f["_notes"] = notes
    s = json.dumps(f, indent=2, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(s)
        print(f"Saved {out} (FIC layout v{ver:g}). Policies: {len(f['insurance'])}, goals: {len(f['goals'])}. "
              f"Missing: {', '.join(missing) or 'nothing'}")
        for x in notes:
            print("NOTE:", x)
    else:
        print(s)


if __name__ == "__main__":
    main()

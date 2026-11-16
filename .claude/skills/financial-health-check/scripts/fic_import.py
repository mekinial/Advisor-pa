"""Turn a v2 FIC's Export tab into the health check's fact-find JSON.

  ./pa fic_import <fic-raw.json> --out <first name>-factfind.json

<fic-raw.json> is what Claude saves after reading the client's FIC with the Sheets connector:
  {
    "source": "<FIC file name> (Google Drive, read <date>)",
    "export":     values of  Export!A1:B80            (field | value rows)
    "policies":   values of  'Existing Policies'!A7:AE40
    "goals_st":   values of  Goals!C14:H15
    "goals_mt":   values of  Goals!I14:N18
    "goals_lt":   values of  Goals!O14:S18
    "dependants": values of  'About You & Estate'!B14:F19
    "lifelong":   values of  'About You & Estate'!B33:F38
  }
Anything blank stays null, so the calculator lists it as missing. Policy numbers (column D) are never copied.
"""
import json, re, sys, datetime


def num(v):
    """'$1,234.50' -> 1234.5, '2.5%' -> 0.025, '' -> None."""
    if v is None:
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


def row(r, i):
    return r[i] if i < len(r) else None


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
    ex = {str(r[0]).strip(): (r[1] if len(r) > 1 else None) for r in raw.get("export", []) if r and r[0]}
    g = lambda k: ex.get(k)
    n = lambda k: num(ex.get(k))
    notes, missing = [], []

    name = text(g("client.name"))
    if name and name.lower().startswith("mr prospect"):
        notes.append("This FIC still shows the 'Mr Prospect' demo: the figures may be template samples, not the client's.")

    exp = {k: n(f"expenses.{k}") for k in ("mortgage", "loans", "family", "tax", "food", "transport", "bills", "subscriptions",
                                          "memberships", "shopping", "personal", "insurance", "committed_savings")}
    f = {
        "_sources": raw.get("source", "Client FIC (v2), Export tab"),
        "fact_find_date": text(g("fact_find_date")) or datetime.date.today().isoformat(),
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
        "national": {"has_ip": None, "ip_ward": None, "has_rider": None, "careshield": None},
        "legacy": {"will": yes_no(g("legacy.will")), "cpf_nomination": yes_no(g("legacy.cpf_nomination")),
                   "lpa": yes_no(g("legacy.lpa")), "acp": yes_no(g("legacy.acp")), "target_amount": None},
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

    # dependants
    for r in raw.get("dependants", []):
        if text(row(r, 0)) or text(row(r, 1)):
            f["client"]["dependants"].append({"name": text(row(r, 0)), "relation": text(row(r, 1)), "age": num(row(r, 2)),
                                              "monthly_support": num(row(r, 3)), "support_years": num(row(r, 4))})
    # lifelong income
    for r in raw.get("lifelong", []):
        if text(row(r, 0)) and num(row(r, 1)):
            f["retirement"]["other_monthly_income"].append({"label": text(row(r, 0)), "amount": num(row(r, 1)),
                                                            "from_age": num(row(r, 2)), "to_age": num(row(r, 3)),
                                                            "guaranteed": yes_no(row(r, 4))})
    # policies (column D = policy number: never read; Q = cash portion of premium / notes)
    pay_from_policies = []
    for r in raw.get("policies", []):
        a0, plan = text(row(r, 0)), text(row(r, 1))
        if a0 and a0.lower().startswith("total"):
            break
        if not plan or plan.lower() in ("employee benefits",):
            continue
        purpose = text(row(r, 4))
        if re.search(r"laps|surrender(ed)?$|terminated|cancel", (text(row(r, 15)) or "").lower()):
            notes.append(f"{' '.join(plan.split())} is marked '{text(row(r, 15))}' in the FIC: left out of the cover totals. Confirm it's no longer in force.")
            continue
        typ = policy_type(purpose, plan)
        p = {"insurer": a0, "plan": " ".join(plan.split()), "type": typ,
             "death_tpd": num(row(r, 5)), "ti": num(row(r, 6)), "early_ci": num(row(r, 7)), "ci": num(row(r, 8)),
             "accidental_death": num(row(r, 9)), "apd": num(row(r, 10)),
             "hospital": text(row(r, 11)) if typ.startswith("IP") else None,
             "loss_of_income_monthly": num(row(r, 12)), "annual_premium": num(row(r, 14)),
             "ends_age": num(row(r, 18)), "cash_value": num(row(r, 19)), "cash_value_at_retirement": num(row(r, 21)),
             "maturity_age": num(row(r, 22)), "maturity_amount": num(row(r, 23)),
             "death_benefit": num(row(r, 27)), "nominated": text(row(r, 28)), "premium_ends": text(row(r, 29)),
             "who_pays": text(row(r, 30)), "count_for_retirement": False}
        if typ.startswith("annuity") and p["death_tpd"] and not p["death_benefit"]:
            p["death_benefit"], p["death_tpd"] = p["death_tpd"], None      # annuity death benefits have no TPD
        if num(row(r, 24)):
            pay_from_policies.append({"label": f"{p['plan']} payout", "amount": round(num(row(r, 24)) / 12, 2),
                                      "from_age": num(row(r, 25)), "guaranteed": yes_no(row(r, 26))})
        f["insurance"].append({k: v for k, v in p.items() if v is not None or k in ("cash_value", "nominated")})
    if not f["retirement"]["other_monthly_income"]:
        f["retirement"]["other_monthly_income"] = pay_from_policies
    names = " ".join(f"{p['plan']} {p['type']}".lower() for p in f["insurance"])
    f["national"]["has_ip"] = any(p["type"] == "IP" and not re.search(r"msl|medishield", p["plan"].lower()) for p in f["insurance"])
    f["national"]["has_rider"] = any(p["type"] == "IP rider" for p in f["insurance"])
    f["national"]["careshield"] = bool(re.search(r"care ?shield|carshield|long-term care", names))

    # goals
    def add_goals(rows, ni, ai, yi, si, term):
        for r in rows:
            gname = text(row(r, ni))
            if not gname or "retirement income" in gname.lower():
                continue
            f["goals"].append({"name": gname, "term": term, "cost": num(row(r, ai)), "year": num(row(r, yi)),
                               "saved": num(row(r, si)) or 0})
    add_goals(raw.get("goals_st", []), 0, 2, 4, 5, "ST")
    add_goals(raw.get("goals_mt", []), 0, 2, 4, 5, "MT")
    add_goals(raw.get("goals_lt", []), 0, 2, 3, 4, "LT")

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
        print(f"Saved {out}. Policies: {len(f['insurance'])}, goals: {len(f['goals'])}. Missing: {', '.join(missing) or 'nothing'}")
        for x in notes:
            print("NOTE:", x)
    else:
        print(s)


if __name__ == "__main__":
    main()

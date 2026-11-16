"""Financial health check calculator (Planners Inc Financial Inventory Check method).

  ./pa health_check <client.json> [--out report.md] [--json result.json] [--year 2026]

Reads a client fact-find as JSON (see ../assets/client-template.json), works out:
  1. Financial ratios (Planners Inc FIC "Financial Ratios" sheet, with its benchmarks)
  2. Cash flow and the 6-account allocation (emergency, happiness, ST, MT, LT, insurance)
  3. Protection: what they have vs general guides (LIA 9x / 4x) and a needs-based check
  4. Retirement number: want vs projected income (the "My Retirement Number" workshop method)
  5. Goals funding: what each ST / MT / LT goal needs per month from today
  6. Flags: every shortfall found, ranked, for the adviser to turn into actions

Numbers only. Missing inputs are reported as missing, never guessed. Every rule of thumb and
assumption is printed beside its result so it can be labelled as a guide in client material.
Standard library only; nothing leaves this PC.
"""
import json, sys, datetime

A = {}  # assumptions actually used (printed at the end)


def num(x):
    """None for missing / blank, float otherwise."""
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def tot(d, keys=None):
    """Sum of the known values in a dict (None if nothing known)."""
    if not d:
        return None
    vals = [num(v) for k, v in d.items() if (keys is None or k in keys)]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def money(x, dp=0):
    if x is None:
        return "—"
    s = f"{abs(x):,.{dp}f}"
    return f"-${s}" if x < 0 else f"${s}"


def pct(x):
    if x is None:
        return "—"
    v = x * 100
    return f"{v:.1f}%" if abs(v) < 10 and round(v, 1) != round(v) else f"{v:.0f}%"


def div(a, b):
    return None if a is None or not b else a / b


def fv(pv, rate, years):
    return pv * (1 + rate) ** years


def pmt_needed(target, rate, months):
    """Monthly saving needed to reach target in `months` at annual `rate` (end of month)."""
    if months <= 0:
        return target
    r = rate / 12
    return target / months if r == 0 else target * r / ((1 + r) ** months - 1)


def fv_monthly(p, rate, months):
    r = rate / 12
    return p * months if r == 0 else p * (((1 + r) ** months - 1) / r)


def load_guides(c):
    """Protection guides: references/protection-guides.json, overridden per client by assumptions.protection_guides."""
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "protection-guides.json")
    try:
        g = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        g = {}
    g.update(c.get("assumptions", {}).get("protection_guides") or {})
    return g


class Report:
    def __init__(self):
        self.lines, self.flags = [], []

    def h(self, t):
        self.lines += ["", f"## {t}", ""]

    def p(self, t=""):
        self.lines.append(t)

    def table(self, head, rows):
        self.lines.append("| " + " | ".join(head) + " |")
        self.lines.append("|" + "---|" * len(head))
        for r in rows:
            self.lines.append("| " + " | ".join(str(c) for c in r) + " |")
        self.lines.append("")

    def flag(self, prio, area, text):
        """prio 1 = act now, 2 = soon, 3 = review / nice to have."""
        self.flags.append({"priority": prio, "area": area, "issue": text})


def main(path, year):
    c = json.load(open(path, encoding="utf-8"))
    R = Report()
    cl = c.get("client", {})
    inc, exp = c.get("income", {}), c.get("expenses", {})
    ast, lia = c.get("assets", {}), c.get("liabilities", {})
    age = num(cl.get("age"))
    ret_age_given = num(c.get("retirement", {}).get("retire_age")) or num(cl.get("retire_age"))
    ret_age = ret_age_given or 65
    irregular = bool(cl.get("income_irregular"))
    infl = num(c.get("assumptions", {}).get("inflation")) or 0.025
    A["inflation"] = infl

    R.p(f"# Financial health check: {cl.get('name', '(name)')}")
    R.p(f"_Worked from the fact-find dated {c.get('fact_find_date', '(no date given)')}. Figures in today's dollars unless stated._")

    # ---------------- cash flow ----------------
    gross = num(inc.get("gross_monthly"))
    take = num(inc.get("take_home_monthly"))
    other_in = tot(inc, ["rental_monthly", "other_monthly"]) or 0
    bonus = num(inc.get("bonus_annual")) or 0
    take_total = (take or 0) + other_in if take is not None else None
    expenses = tot(exp)
    committed = num(exp.get("committed_savings")) or 0
    spend = None if expenses is None else expenses - committed          # what life costs (excl. savings)
    fixed_keys = c.get("fixed_expense_keys") or ["family", "bills", "tax", "loans", "insurance"]
    fixed = tot(exp, fixed_keys)
    surplus = None if take_total is None or expenses is None else take_total - expenses
    prem_total = sum(num(p.get("annual_premium")) or 0 for p in c.get("insurance", []))

    R.h("1. Cash flow")
    R.table(["Item", "Monthly", "Yearly"], [
        ["Gross income", money(gross), money(None if gross is None else gross * 12 + bonus)],
        ["Take-home (+ rental / other)", money(take_total), money(None if take_total is None else take_total * 12)],
        ["Bonus", "", money(bonus)],
        ["Spending (excl. committed savings)", money(spend), money(None if spend is None else spend * 12)],
        ["Committed savings / investments", money(committed), money(committed * 12)],
        ["Surplus after everything", money(surplus), money(None if surplus is None else surplus * 12)],
        ["Insurance premiums (from policy list)", money(prem_total / 12), money(prem_total)],
    ])
    if take_total is None or expenses is None:
        R.flag(1, "Cash flow", "Income or expenses missing: cash flow, ratios and goals can't be worked out properly.")
    elif surplus < 0:
        R.flag(1, "Cash flow", f"Spending more than they take home ({money(surplus)}/month).")

    # ---------------- balance sheet ----------------
    cash = tot(ast, ["cash", "foreign_currency"])
    cpf = tot(ast, ["cpf_oa", "cpf_sa", "cpf_ma", "cpf_investments"])
    cpf_ma = num(ast.get("cpf_ma")) or 0
    prop_home = num(ast.get("home")) or 0
    prop = tot(ast, ["home", "investment_property"])
    invested = tot(ast, ["stocks", "unit_trusts", "bonds", "policy_cash_value", "business", "srs", "other_investments"])
    personal = tot(ast, ["personal_use"])
    assets = sum(x or 0 for x in (cash, cpf, prop, invested, personal)) if any(
        x is not None for x in (cash, cpf, prop, invested, personal)) else None
    liabs = tot(lia) or 0
    nw = None if assets is None else assets - liabs

    R.h("2. Balance sheet")
    R.table(["", "Amount"], [
        ["Cash / near cash", money(cash)], ["CPF (OA+SA+MA+CPFIS)", money(cpf)], ["Property", money(prop)],
        ["Invested assets (incl. policy cash values, SRS)", money(invested)], ["Personal-use assets", money(personal)],
        ["**Total assets**", money(assets)], ["Total liabilities", money(liabs)], ["**Net worth**", money(nw)],
    ])

    # ---------------- ratios ----------------
    dr = c.get("debt_repayments_monthly", {})
    debt_m = tot(dr)
    nonmort_m = num(dr.get("non_mortgage"))
    rows, ratio_out = [], {}

    def ratio(name, val, guide, ok, fmt=pct, area="Ratios", prio=2, why=""):
        status = "—" if val is None else ("OK" if ok(val) else "Look at")
        rows.append([name, fmt(val), guide, status])
        ratio_out[name] = val
        if val is not None and not ok(val):
            R.flag(prio, area, f"{name} is {fmt(val)} (guide: {guide}). {why}".strip())

    months_fmt = lambda v: "—" if v is None else f"{v:.1f} months"
    # Emergency cash (Planners Inc): single 3 / married no kids 6 / 1 kid 9 / 2+ kids 12 months of spending
    G0 = load_guides(c)
    em_tbl = G0.get("emergency_months") or {"single": 3, "married_no_kids": 6, "married_1_kid": 9, "married_2_kids": 12}
    married = str(cl.get("marital_status", "")).lower().startswith("married") or any(
        str(d.get("relation", "")).lower() in ("spouse", "wife", "husband") for d in (cl.get("dependants") or []))
    kids = cl.get("children")
    kids = int(num(kids)) if num(kids) is not None else sum(
        1 for d in (cl.get("dependants") or []) if str(d.get("relation", "")).lower() in ("child", "son", "daughter"))
    household = ("married_2_kids" if kids >= 2 else "married_1_kid" if kids == 1 else "married_no_kids") if married \
        else ("married_2_kids" if kids >= 2 else "married_1_kid" if kids == 1 else "single")
    em_target = num(em_tbl.get(household)) or 6
    hh_label = household.replace("_", " ").replace("2 kids", "2+ kids")
    if irregular and em_target < 12:
        em_target = 12
        hh_label += ", irregular income"
    A[f"emergency_fund_months ({hh_label})"] = em_target
    ratio("Basic liquidity (cash ÷ monthly spending)", div(cash, spend),
          f"{em_target:g} months ({hh_label}; Planners Inc)",
          lambda v: v >= em_target, months_fmt, "Emergency fund", 1,
          "Emergency fund is short.")
    ratio("Liquid assets ÷ net worth", div(cash, nw), "≥ 15%", lambda v: v >= 0.15)
    ratio("Savings ratio (surplus ÷ take-home)", div(surplus, take_total), "≥ 10%", lambda v: v >= 0.10)
    ratio("Savings ratio incl. committed savings", div(None if surplus is None else surplus + committed, take_total),
          "≥ 10%", lambda v: v >= 0.10)
    ratio("Debt ÷ assets", div(liabs, assets), "≤ 50%", lambda v: v <= 0.50, prio=1)
    ratio("Solvency (net worth ÷ assets)", div(nw, assets), "higher is stronger", lambda v: v >= 0.50)
    ratio("Fixed expenses ÷ take-home", div(fixed, take_total), "≤ 55%", lambda v: v <= 0.55)
    ratio("Debt service (all repayments ÷ take-home)", div(debt_m, take_total), "≤ 35%", lambda v: v <= 0.35, prio=1)
    ratio("Non-mortgage debt service", div(nonmort_m, take_total), "≤ 15%", lambda v: v <= 0.15, prio=1)
    ratio("Invested assets ÷ net worth", div(invested, nw), "≥ 50%", lambda v: v >= 0.50, prio=3,
          why="Wealth is mostly in cash, CPF or the home rather than working investments.")
    ratio("CPF + home ÷ net worth", div(None if cpf is None else cpf + prop_home, nw),
          "no fixed guide; lower = more liquid (over 75% flagged for review)", lambda v: v <= 0.75, prio=3,
          why="Most wealth is locked in CPF and the home.")
    ratio("Protection premiums ÷ take-home (yearly)", div(prem_total, None if take_total is None else take_total * 12),
          "≤ 15% (MoneySense); ≤ 10% (Planners Inc house guide)", lambda v: v <= 0.15, prio=2,
          why="Premiums are heavy for the income; check for overlap before adding more.")
    R.h("3. Financial ratios (Planners Inc FIC benchmarks)")
    R.table(["Ratio", "Result", "Guide", "Status"], rows)

    # ---------------- 6 accounts ----------------
    R.h("4. Six-account allocation (Planners Inc)")
    em_need = None if spend is None else spend * em_target
    lt_min = None if take_total is None else take_total * 0.10
    ins_cap10 = None if take_total is None else take_total * 0.10
    ins_cap15 = None if take_total is None else take_total * 0.15
    R.table(["Account", "Guide", "Amount", "Now"], [
        ["Emergency fund", f"{em_target:g} months of spending ({hh_label})", money(em_need), money(cash)],
        ["Happiness fund", "bonus or 1 month's income", money(bonus or take_total), ""],
        ["Short-term goals (≤ 5 yrs)", "from goals below", "", ""],
        ["Mid-term goals (5–15 yrs)", "from goals below", "", ""],
        ["Long-term / retirement", "≥ 10% of take-home", f"{money(lt_min)}/mo", f"{money(committed)}/mo committed"],
        ["Insurance", "≤ 10% (house) / 15% (MoneySense) of take-home",
         f"{money(ins_cap10)}–{money(ins_cap15)}/mo", f"{money(prem_total / 12)}/mo"],
    ])
    if em_need is not None and cash is not None and cash < em_need:
        R.p(f"Emergency fund short by **{money(em_need - cash)}** against {em_target:g} months.")
    if lt_min is not None and committed < lt_min:
        R.flag(2, "Long-term savings", f"Committed savings {money(committed)}/mo is under 10% of take-home ({money(lt_min)}/mo).")

    # ---------------- protection ----------------
    pols = c.get("insurance", [])
    cols = ["death_tpd", "ti", "early_ci", "ci", "accidental_death", "apd"]
    have = {k: 0.0 for k in cols}
    hosp_plans, loi, ltc = [], 0.0, 0.0
    for p in pols:
        ends = num(p.get("ends_age"))
        for k in cols:
            have[k] += num(p.get(k)) or 0
        if p.get("hospital"):
            hosp_plans.append(f"{p.get('plan', '?')} ({p.get('hospital')})")
        loi += num(p.get("loss_of_income_monthly")) or 0
        ltc += num(p.get("ltc_monthly")) or 0
        if ends and age and ends < ret_age and (num(p.get("death_tpd")) or num(p.get("ci"))):
            R.flag(3, "Protection", f"{p.get('plan', 'A policy')} ends at age {ends:.0f}, before retirement at {ret_age:.0f}.")
        if p.get("nominated") is False:
            R.flag(2, "Legacy", f"No nomination on {p.get('plan', 'a policy')}.")
    annual = None if gross is None else gross * 12 + bonus
    G = load_guides(c)
    src = G.get("source") or "guide"
    deps = cl.get("dependants") or []

    # ---- life stage: insurance guards the working years; later the focus moves to income and legacy ----
    working = None if age is None else max(ret_age - age, 0)
    if age is None:
        stage, focus = "Unknown", "age missing: stage can't be set"
    elif working <= 5:      # by THEIR retirement age: someone 60 working to 70 is still building and protecting
        stage, focus = "The Distributor", "retirement income, health and long-term care, legacy"
    elif age >= 50:
        stage, focus = "The Optimiser", "closing the retirement gap; protection tapering as working years run out"
    elif age >= 40:
        stage, focus = "The Accumulator", "growth, and protecting a growing family and income"
    else:
        stage, focus = "The Builder", "foundation: emergency cash, protecting income, starting early"
    late = stage == "The Distributor"
    if not ret_age_given:
        R.flag(1, "Setup", "Retirement age not captured; 65 assumed. Their own retirement age sets how long cover "
               "must protect their income, so confirm it.")
        A["retirement_age"] = "65 (assumed, not captured)"
    else:
        A["retirement_age"] = f"{ret_age:g} (client's choice)"
    A["life_stage"] = f"{stage} (working years left: {'?' if working is None else f'{working:.0f}'})"

    def target(key, base, taper=True):
        """Planners Inc multiple of yearly income, capped at the working years left (cover replaces the income
        that would still have been earned). Returns (need, multiple used, full multiple)."""
        x = num(G.get(key))
        if x is None or base is None:
            return None, None, x
        used = min(x, working) if taper and working is not None else x
        return used * base, used, x

    need_dtpd, m_dtpd, f_dtpd = target("death_tpd_x_annual_income", annual)
    need_ti, m_ti, f_ti = target("ti_x_annual_income", annual)
    need_ci, m_ci, f_ci = target("ci_x_annual_income", annual)
    need_eci, m_eci, f_eci = target("early_ci_x_annual_income", annual)
    need_pa, m_pa, f_pa = target("personal_accident_x_annual_income", annual)
    dpct = num(G.get("disability_income_pct_of_monthly_income"))
    need_loi = None if dpct is None or gross is None or (working is not None and working <= 2) else dpct * gross
    for k, v, f in (("death_tpd", m_dtpd, f_dtpd), ("ci", m_ci, f_ci), ("early_ci", m_eci, f_eci)):
        if v is not None:
            A[f"{k}_multiple ({src})"] = f"{v:g}" + (f" (full {f:g}, capped at working years left)" if v < f else "")
    if dpct is not None:
        A[f"disability_income_pct ({src})"] = dpct
    unset = [k for k in ("death_tpd_x_annual_income", "ci_x_annual_income") if num(G.get(k)) is None]
    if unset:
        R.flag(1, "Setup", "Protection guides not set in references/protection-guides.json "
               f"({', '.join(unset)}): no protection targets worked out.")

    # needs-based death / TPD (only if dependants given): covers dependants even past retirement
    nb = None
    if deps and spend is not None:
        support_yrs = max(num(d.get("support_years")) or 0 for d in deps)
        share = num(c.get("assumptions", {}).get("family_share_of_spending")) or 0.7
        A["family_share_of_spending"] = share
        hps = bool(c.get("national", {}).get("hps"))
        debts = liabs - ((num(lia.get("mortgage_home")) or 0) if hps else 0)
        A["home_loan_left_out_of_needs_based (HPS covers it)"] = hps
        nb = spend * 12 * share * support_yrs + debts + sum(num(g.get("cost")) or 0 for g in c.get("goals", [])
                                                             if g.get("for_dependants")) - (cash or 0) - (invested or 0)
        nb = max(nb, 0)
    nb_wins = nb is not None and need_dtpd is not None and nb > need_dtpd
    if nb_wins:
        need_dtpd = nb   # dependants who rely on them beyond the working years
    legacy_target = num(c.get("legacy", {}).get("target_amount"))

    def gap(need, got):
        return None if need is None else max(need - got, 0)

    def guide_txt(need, used, full, unit="× yearly income"):
        if need is None:
            return "not set"
        if used == 0:
            return f"none for income (no working years left; full guide {full:g}{unit})"
        capped = f", capped from {full:g}× at {working:.0f} working yrs left" if full and used < full else ""
        return f"{money(need)} ({used:g}{unit}{capped}, {src})"

    R.h("5. Protection")
    R.p(f"**Life stage: {stage}.** Focus: {focus}. Insurance guards the working years, so the income-based targets "
        "below are capped at the years of income still to be earned, and fall away at retirement. After that the "
        "plan shifts to passive income, health and care costs, and what is left behind.")
    R.p("")
    dtxt = (f"{money(nb)} (needs-based: dependants' support beyond the working years)" if nb_wins
            else guide_txt(need_dtpd, m_dtpd, f_dtpd))
    prow = [["Death / TPD", money(have["death_tpd"]), dtxt, money(gap(need_dtpd, have["death_tpd"]))]]
    if need_ti is not None:
        prow.append(["Terminal illness", money(have["ti"]), guide_txt(need_ti, m_ti, f_ti), money(gap(need_ti, have["ti"]))])
    if nb is not None and not nb_wins:
        prow.append(["Death / TPD (needs-based check)", money(have["death_tpd"]),
                     money(nb) + f" (family spending {pct(A['family_share_of_spending'])} × years + debts − liquid assets)",
                     money(gap(nb, have["death_tpd"]))])
    if late:
        dis_txt = "not needed: retirement within 2 years" if working is not None and working <= 2 else "replaces part of income if unable to work"
    else:
        dis_txt = "replaces part of income if unable to work"
    prow += [
        ["Critical illness (late stage)", money(have["ci"]), guide_txt(need_ci, m_ci, f_ci), money(gap(need_ci, have["ci"]))],
        ["Early / multi-pay CI", money(have["early_ci"]), guide_txt(need_eci, m_eci, f_eci) if f_eci else "not set; discuss",
         money(gap(need_eci, have["early_ci"])) if f_eci else "—"],
        ["Accidental death / disablement", f"{money(have['accidental_death'])} / {money(have['apd'])}",
         guide_txt(need_pa, m_pa, f_pa) if f_pa else "discuss", money(gap(need_pa, have["apd"])) if need_pa else "—"],
        ["Hospital (IP + rider)", ", ".join(hosp_plans) or "none listed", "IP matched to ward preference", ""],
        ["Disability income", f"{money(loi)}/mo",
         f"{money(need_loi)}/mo ({pct(dpct)} of gross monthly income, {src})" if need_loi else dis_txt,
         f"{money(gap(need_loi, loi))}/mo" if need_loi else ""],
        ["Long-term care", f"{money(ltc)}/mo" + (" + CareShield Life" if c.get("national", {}).get("careshield") else ""),
         "CareShield base ~$689/mo (2026) vs care costs $2.5k–6k/mo", ""],
        ["Legacy (what is left behind)", money(have["death_tpd"]) + " insurance + estate",
         (money(legacy_target) + " (client's wish)") if legacy_target else "ask what they want to leave, and to whom",
         (money(gap(legacy_target, have["death_tpd"])) + " before estate") if legacy_target else ""],
    ]
    if G.get("show_lia_minimum_for_reference") and annual:
        prow.append(["(LIA minimum, for reference)", "", f"Death/TPD {money(9 * annual)} · CI {money(4 * annual)}", ""])
    R.table(["Cover", "Have", "Guide", "Gap"], prow)

    if annual is None:
        R.flag(1, "Protection", "Gross income missing: protection guides can't be worked out.")
    else:
        if need_dtpd and have["death_tpd"] < need_dtpd:
            tail = "; has dependants." if deps else ("; few working years left, so this is mostly a legacy question now."
                                                     if late else ".")
            R.flag(1 if deps else 3 if late else 2, "Protection",
                   f"Death/TPD {money(have['death_tpd'])} vs {money(need_dtpd)} (gap {money(need_dtpd - have['death_tpd'])}){tail}")
        if need_ci and have["ci"] < need_ci:
            R.flag(2 if late else 1, "Protection", f"Critical illness {money(have['ci'])} vs {money(need_ci)} "
                   f"({m_ci:g}× income) (gap {money(need_ci - have['ci'])}).")
        if need_ti and have["ti"] < need_ti:
            R.flag(3 if late else 2, "Protection", f"Terminal illness {money(have['ti'])} vs {money(need_ti)} "
                   f"(gap {money(need_ti - have['ti'])}).")
        if need_eci and have["early_ci"] < need_eci:
            R.flag(3 if late else 2, "Protection", f"Early CI {money(have['early_ci'])} vs {money(need_eci)} "
                   f"({m_eci:g}× income) (gap {money(need_eci - have['early_ci'])}).")
        if need_loi and 0 < loi < need_loi:
            R.flag(2, "Protection", f"Disability income {money(loi)}/mo vs {pct(dpct)} of income ({src}) {money(need_loi)}/mo.")
        if late and have["ci"]:
            R.flag(3, "Protection", "Near or past retirement, existing CI cover acts mainly as a health buffer. Keep it "
                   "if the premiums fit the retirement budget.")
    nat = c.get("national", {})
    if not hosp_plans and not nat.get("has_ip"):
        R.flag(1, "Protection", "No Integrated Shield plan listed (MediShield Life only).")
    elif nat.get("has_ip") and nat.get("has_rider") is False:
        R.flag(3, "Protection", "IP without a rider: co-insurance and deductible are paid out of pocket.")
    if loi == 0 and gross and need_loi:
        R.flag(2, "Protection", "No disability income cover: a long illness or injury would stop income and drain savings.")
    if not nat.get("careshield") and ltc == 0:
        R.flag(1 if late or (age or 0) >= 50 else 2, "Protection", "No CareShield Life / long-term care cover listed.")
    if late and not legacy_target:
        R.flag(2, "Legacy", "Legacy wishes not captured: what to leave behind, to whom, and how (nominations, will).")

    # ---------------- retirement ----------------
    R.h("6. Retirement number")
    rt = c.get("retirement", {})
    want = num(rt.get("monthly_today"))
    dd = num(rt.get("drawdown_rate")) or 0.04
    real = (num(c.get("assumptions", {}).get("return_pre_retirement")) or 0.04) - infl
    A["drawdown_rate"], A["real_return_pre_retirement"] = dd, real
    yrs = None if age is None else max(ret_age - age, 0)
    if want is None or yrs is None:
        R.p("Desired retirement income or age missing: can't work out the retirement gap.")
        R.flag(2, "Retirement", "Retirement goal (monthly amount in today's dollars) not captured yet.")
        ret_out = None
    else:
        em_keep = em_need or 0
        pot_now = (invested or 0) - (num(ast.get("policy_cash_value")) or 0) - (num(ast.get("srs")) or 0) \
            + max((cash or 0) - em_keep, 0)
        oa_used = 0
        if rt.get("cpf_oa_withdrawable"):   # 55+ with RA set aside: OA can be withdrawn and deployed
            oa_used = num(ast.get("cpf_oa")) or 0
            pot_now += oa_used
            A["cpf_oa_counted_as_retirement_capital"] = money(oa_used)
        pot_ret = fv(pot_now, real, yrs) + fv_monthly(committed, real, yrs * 12)
        srs = num(rt.get("srs_at_retirement")) or 0
        srs_m = srs / (num(rt.get("srs_draw_years")) or 10) / 12
        src = [["CPF LIFE (estimate given)", num(rt.get("cpf_life_monthly"))],
               ["Spouse CPF LIFE", num(rt.get("spouse_cpf_life_monthly"))]]
        src += [[o.get("label", "Other income"), num(o.get("amount"))] for o in rt.get("other_monthly_income", [])]
        src += [[f"SRS ÷ {num(rt.get('srs_draw_years')) or 10:.0f} yrs", srs_m if srs else None],
                [f"Investments & spare cash at {pct(dd)} drawdown", pot_ret * dd / 12]]
        projected = sum(v for _, v in src if v)
        ret_sources = [[k, v] for k, v in src if v]
        g = want - projected
        R.table(["", "Monthly (today's $)"],
                [["**What they want**", money(want)]] + [[k, money(v)] for k, v in src] +
                [["**What they're building**", money(projected)], ["**Gap**", money(max(g, 0)) if g > 0 else "none — on track"]])
        R.p(f"In {yrs:.0f} years at {pct(infl)} inflation, {money(want)} today is about **{money(fv(want, infl, yrs))}/month**.")
        R.p(f"Investments and spare cash today ({money(pot_now)}, after keeping the emergency fund"
            + (f", incl. {money(oa_used)} withdrawable CPF OA" if oa_used else "") + ") plus committed savings of "
            f"{money(committed)}/mo, grown at {pct(real)} real a year, give about {money(pot_ret)} by {ret_age:.0f}.")
        cpf_m = num(rt.get("cpf_life_monthly")) or 0
        if ret_age < 65 and cpf_m:
            bridge = cpf_m * 12 * (65 - ret_age)
            ret_out_bridge = bridge
            R.p(f"**Bridge:** CPF LIFE starts at 65, so retiring at {ret_age:.0f} leaves {65 - ret_age:.0f} years without it: "
                f"about **{money(bridge)}** (today's $) has to come from savings first.")
            R.flag(2, "Retirement", f"Retiring at {ret_age:.0f}: ~{money(bridge)} needed to bridge to CPF LIFE at 65.")
        if num(rt.get("cpf_life_monthly")) is not None:
            R.p("_CPF LIFE estimates are in payout-year dollars; treating them as today's dollars flatters the "
                "projection. Confirm the client's figure and plan type (Standard / Basic / Escalating)._")
        if num(rt.get("cpf_life_monthly")) is None:
            R.flag(2, "Retirement", "CPF LIFE estimate missing: get it from the CPF Retirement Payout Planner.")
        ret_out = {"want": want, "projected": projected, "gap": max(g, 0), "years": yrs}
        if g > 0:
            lump = g * 12 / dd
            extra = pmt_needed(lump, real, yrs * 12) if yrs else lump
            ret_out.update(lump_needed=lump, extra_monthly=extra)
            if yrs >= 3:
                R.p(f"To close a {money(g)}/month gap needs about **{money(lump)}** more by retirement "
                    f"(gap × 12 ÷ {pct(dd)}), or about **{money(extra)}/month** more saved from now (at {pct(real)} real).")
                how = f"needs ~{money(extra)}/month more from now"
            else:
                R.p(f"To close a {money(g)}/month gap needs about **{money(lump)}** more capital at {pct(dd)} "
                    f"(gap × 12 ÷ {pct(dd)}). With retirement {yrs:.0f} year(s) away, saving alone won't close it: "
                    "look at the other levers (how existing money is deployed for income, CPF LIFE plan / deferral, "
                    "working longer or part-time, adjusting the target).")
                how = f"~{money(lump)} more capital, or other levers"
            R.flag(1 if yrs <= 10 else 2, "Retirement",
                   f"Retirement gap {money(g)}/month ({pct(div(g, want))} of goal); {how}.")

    # ---------------- goals ----------------
    R.h("7. Goals (ST / MT / LT)")
    rates = c.get("assumptions", {}).get("goal_returns") or {"ST": 0.02, "MT": 0.03, "LT": 0.04}
    A["goal_returns"] = rates
    grows, need_total, undated = [], 0.0, []
    for gl in c.get("goals", []):
        cost, saved = num(gl.get("cost")), num(gl.get("saved")) or 0
        yr = num(gl.get("year"))
        if cost is None or yr is None:
            grows.append([gl.get("name"), gl.get("term", ""), money(cost), "—", "—", "—",
                          "year missing" if cost is not None else "cost missing"])
            undated.append(gl.get("name"))
            continue
        n = max(yr - year, 0)
        term = gl.get("term") or ("ST" if n <= 5 else "MT" if n <= 15 else "LT")
        r = rates.get(term, 0.03)
        future = fv(cost, infl, n)
        short = max(future - fv(saved, r, n), 0)
        m = pmt_needed(short, r, n * 12) if n else short
        need_total += m if n else 0
        grows.append([gl.get("name"), term, money(cost), f"{yr:.0f}", money(future), money(saved), f"{money(m)}/mo"])
    if grows:
        R.table(["Goal", "Term", "Cost today", "Year", "Cost then", "Set aside", "Needed from now"], grows)
        if undated:
            R.p(f"Can't total the monthly need yet: no target year (or cost) for {', '.join(undated)}.")
            R.flag(2, "Goals", f"Target year or cost missing for: {', '.join(undated)}.")
        if surplus is not None and need_total:
            R.p(f"The dated goals need about **{money(need_total)}/month**; current surplus is {money(surplus)}/month.")
            if need_total > surplus + committed:
                R.flag(1, "Goals", f"Goals need ~{money(need_total)}/month but surplus + committed savings is "
                       f"{money(surplus + committed)}: prioritise, push dates, or raise income.")
    else:
        R.p("No goals captured yet.")
        R.flag(2, "Goals", "No short / mid / long-term goals captured.")

    # ---------------- legacy ----------------
    lg = c.get("legacy", {})
    missing = [k.replace("_", " ").upper() if k in ("lpa", "acp") else k.replace("_", " ")
               for k in ("will", "cpf_nomination", "lpa", "acp") if lg.get(k) is False]
    unknown = [k.replace("_", " ") for k in ("will", "cpf_nomination", "lpa") if lg.get(k) is None]
    R.h("8. Legacy")
    R.p(f"Not yet done: {', '.join(missing) or 'none'}" + (f". Not asked yet: {', '.join(unknown)}." if unknown else "."))
    if missing:
        R.flag(2 if deps else 3, "Legacy", f"Not done: {', '.join(missing)}.")
    if age and age >= 55:
        R.flag(3, "Retirement", "55+: review cover every 2–3 years; look at CPF LIFE plan choice, RA top-ups and property monetisation.")

    # ---------------- lifetime timeline ----------------
    # Year-by-year path of liquid money from today to the planning age, in today's dollars (real returns).
    # Two buckets: cash (incl. withdrawable CPF OA) earns the cash rate; invested money earns the market rate,
    # run three ways (cautious / middle / hopeful) because markets can go either way.
    # Working years: committed savings go in, dated goals come out. Retirement: the target income is drawn,
    # net of CPF LIFE (from its start age) and other lifelong income.
    # Then each lever (invest the surplus, put spare cash to work, retire later, spend less, defer CPF LIFE)
    # is re-run on its own, and the money levers together make "the plan".
    timeline = None
    if age is not None:
        R.h("9. Lifetime timeline (illustrative)")
        asm = c.get("assumptions", {})
        plan_to = int(num(rt.get("plan_to_age")) or 90)
        cash_r = (num(asm.get("cash_return")) if num(asm.get("cash_return")) is not None else 0.015) - infl
        mid_nom = num(asm.get("return_pre_retirement")) or 0.04
        scen = asm.get("scenario_returns") or {"cautious": 0.025, "middle": mid_nom, "hopeful": 0.06}
        scen = {k: num(v) - infl for k, v in scen.items()}
        A["plan_to_age"] = plan_to
        A["cash_real_return"] = cash_r
        A["invested_real_return (cautious / middle / hopeful)"] = " / ".join(pct(scen[k]) for k in ("cautious", "middle", "hopeful"))
        oa_in = (num(ast.get("cpf_oa")) or 0) if rt.get("cpf_oa_withdrawable") else 0
        cash0 = (cash or 0) + oa_in
        inv0 = max((invested or 0) - (num(ast.get("policy_cash_value")) or 0) - (num(ast.get("srs")) or 0), 0)
        srs_join = num(rt.get("srs_at_retirement"))
        srs_join = (num(ast.get("srs")) or 0) if srs_join is None else srs_join
        cpf_m = num(rt.get("cpf_life_monthly")) or 0
        cpf_start = int(num(rt.get("cpf_life_start_age")) or 65)
        other_m = sum(num(o.get("amount")) or 0 for o in rt.get("other_monthly_income", [])) \
            + (num(rt.get("spouse_cpf_life_monthly")) or 0)
        goal_at = {}
        for gl in c.get("goals", []):
            gy, gc = num(gl.get("year")), num(gl.get("cost"))
            if gy is not None and gc:
                goal_at.setdefault(int(age + gy - year), []).append((gl.get("name"), gc))
        a0 = int(age)
        keep = em_need or 0

        # ---- policies: cash values, maturities and death benefits (facts from the FIC / statements only)
        # Values are in today's dollars: illustrated future values are deflated by inflation. Policy cash values are
        # NOT spendable by default (cashing in ends the cover); set count_for_retirement on a policy to use it.
        VALUE_TYPES = ("whole life", "ilp", "investment", "endowment", "annuity")
        pols_v, mat_at, todo_pol, db_face, pol_list = [], {}, [], 0.0, []
        for p in c.get("insurance", []):
            typ, pname = (p.get("type") or "").lower(), p.get("plan") or "policy"
            has_val = any(k in typ for k in VALUE_TYPES)
            ends = num(p.get("ends_age"))
            dbv = num(p.get("death_benefit")) or num(p.get("death_tpd")) or 0
            if dbv and "term" not in typ and (ends is None and has_val or (ends or 0) >= plan_to):
                db_face += dbv                      # cover that is still there at the planning age
            if not has_val:
                continue
            cv, cvr = num(p.get("cash_value")), num(p.get("cash_value_at_retirement"))
            ma, mamt = num(p.get("maturity_age")), num(p.get("maturity_amount"))
            if ma and mamt and ma >= a0:
                mat_at[int(ma)] = mat_at.get(int(ma), 0) + mamt / (1 + infl) ** (ma - age)
            if cv is None:
                todo_pol.append(("cash", pname))
            if cvr is None and a0 < ret_age and "annuity" not in typ and not (ma and ma <= ret_age):
                todo_pol.append(("illus", pname))
            if cv is not None:
                cvr_r = None if cvr is None else cvr / (1 + infl) ** max(ret_age - age, 0)
                pols_v.append({"name": pname, "now": cv, "ret": cvr_r, "count": bool(p.get("count_for_retirement")),
                               "mat": int(ma) if ma else None})
            pol_list.append({"name": pname, "cash_value": cv, "value_at_retirement": cvr, "death_benefit": dbv or None})
        pv_total_only = num(ast.get("policy_cash_value")) if not pols_v else None
        if pv_total_only:                           # FIC gives one total only: carry it flat
            pols_v.append({"name": "Policies (FIC total)", "now": pv_total_only, "ret": None, "count": False, "mat": None})

        def polval(a_, counted=None):
            """Policy cash values at age a_ (today's $). counted: None = all, True/False = only those."""
            t_ = 0.0
            for pv in pols_v:
                if counted is not None and pv["count"] != counted or (pv["mat"] and a_ >= pv["mat"]):
                    continue
                if pv["ret"] is not None and ret_age > a0:
                    k = min(max(a_ - a0, 0) / (ret_age - a0), 1)
                    t_ += pv["now"] * (pv["ret"] / pv["now"]) ** k if pv["now"] > 0 else pv["ret"] * k
                else:
                    t_ += pv["now"] if pv["ret"] is None else pv["ret"]
            return t_

        def sim(r_inv, extra=0.0, move_cash=False, retire=None, spend_f=1.0, cpf_age=None, want_m=None):
            """One path. Returns (series, runs_out_age, money_at_retirement, left_at_end)."""
            retire = ret_age if retire is None else retire
            cpf_age = cpf_start if cpf_age is None else cpf_age
            cpf_pay = cpf_m * (1.07 ** max(cpf_age - cpf_start, 0)) if cpf_m else 0  # CPF: up to ~7% more a year deferred
            cb, ib = cash0, inv0
            if move_cash:                       # keep the emergency fund in cash, invest the rest
                spare = max(cb - keep, 0)
                cb, ib = cb - spare, ib + spare
            if retire < a0:
                ib += srs_join
            ser, out, at_r = [], None, None
            for a_ in range(a0, plan_to + 1):
                if a_ == int(retire):
                    ib += srs_join + polval(a_, True)   # policies marked count_for_retirement are cashed in
                    at_r = cb + ib
                cb += mat_at.get(a_, 0)                 # endowment / policy maturities arrive as cash
                ser.append([a_, round(cb + ib)])
                cb, ib = cb * (1 + cash_r), ib * (1 + r_inv)
                if a_ < retire:
                    ib += (committed + extra) * 12
                else:
                    w_ = want if want_m is None else want_m
                    draw = 0 if w_ is None else max(w_ * spend_f - (cpf_pay if a_ >= cpf_age else 0) - other_m, 0) * 12
                    take = min(draw, cb)          # spend cash first, then investments
                    cb -= take
                    ib -= draw - take
                out_goal = sum(gc for _, gc in goal_at.get(a_, []))
                take = min(out_goal, cb)
                cb -= take
                ib -= out_goal - take
                if cb + ib < 0 and out is None:
                    out = a_ + 1
                if ib < 0:
                    cb, ib = max(cb + ib, 0), 0
            if at_r is None:
                at_r = ser[0][1]
            return ser, out, at_r, ser[-1][1]

        def lasts(o):
            return o[1] if o[1] and o[1] <= plan_to else None

        now = {k: sim(r) for k, r in scen.items()}
        # ---- levers, each on its own vs today's setup (middle case)
        lv_cfg = c.get("levers", {}) or {}
        working = a0 < ret_age
        spare_cash = max(cash0 - keep, 0)
        extra_m = num(lv_cfg.get("invest_monthly"))
        if extra_m is None and ret_age - a0 >= 3 and surplus and surplus > 0:
            extra_m = round(surplus * 0.5, -2)   # default: invest half of what's left over each month
        levers = []

        def add(key, title, how, in_plan, **kw):
            o = sim(scen["middle"], **kw)
            levers.append({"key": key, "title": title, "how": how, "in_plan": in_plan, "lasts": lasts(o),
                           "at_retirement": o[2], "left_at_end": o[3], "retire_age": kw.get("retire", ret_age)})
        if extra_m:
            add("invest_monthly", f"Invest {money(extra_m)} a month", "from the money left over each month, until you retire",
                True, extra=extra_m)
        if spare_cash > 10000 and lv_cfg.get("invest_idle_cash", True):
            add("invest_idle_cash", f"Put {money(spare_cash)} of spare cash to work",
                "keep your emergency fund in cash and invest the rest for income and growth", True, move_cash=True)
        if working and lv_cfg.get("retire_later_years", 2):
            yl = int(lv_cfg.get("retire_later_years", 2))
            add("retire_later", f"Retire {yl} years later, at {ret_age + yl:.0f}", "or keep some part-time income for those years",
                False, retire=ret_age + yl)
        if want and lv_cfg.get("spend_less_pct", 0.1):
            sp = num(lv_cfg.get("spend_less_pct", 0.1))
            add("spend_less", f"Spend {sp * 100:.0f}% less in retirement", f"{money(want * (1 - sp))} a month instead of {money(want)}",
                False, spend_f=1 - sp)
        if cpf_m and a0 < 70 and lv_cfg.get("defer_cpf_life_to", 70):
            da = int(lv_cfg.get("defer_cpf_life_to", 70))
            add("defer_cpf", f"Start CPF LIFE at {da} instead of {cpf_start}",
                f"payouts rise by up to ~7% for each year you defer, to about {money(cpf_m * 1.07 ** (da - cpf_start))} a month",
                bool(lv_cfg.get("plan_defer_cpf", False)), cpf_age=da)
        base = now["middle"]
        b_last = lasts(base) or plan_to + 1
        levers = [l for l in levers if (l["lasts"] or plan_to + 1) > b_last or l["left_at_end"] > base[3] * 1.01 + 1000
                  or (working and l["at_retirement"] > base[2] * 1.02)]   # only levers that actually help
        plan_kw = {}
        for l in levers:
            if l["in_plan"]:
                plan_kw.update({"invest_monthly": {"extra": extra_m}, "invest_idle_cash": {"move_cash": True},
                                "defer_cpf": {"cpf_age": int(lv_cfg.get("defer_cpf_life_to", 70))}}.get(l["key"], {}))
        plan = {k: sim(r, **plan_kw) for k, r in scen.items()} if plan_kw else None

        events = [{"age": a0, "label": "Today", "kind": "now"}]
        if age < 55:
            events.append({"age": 55, "label": "CPF: savings above your Full Retirement Sum can be withdrawn", "kind": "cpf"})
        if ret_age > age:
            events.append({"age": int(ret_age), "label": f"You retire at {ret_age:.0f}", "kind": "retire"})
        if cpf_start >= age:
            events.append({"age": cpf_start, "label": "CPF LIFE payouts begin" + (f" (~{money(cpf_m)}/mo)" if cpf_m else ""), "kind": "cpf"})
        for ga, gs in goal_at.items():
            for gname, gc in gs:
                events.append({"age": ga, "label": f"{gname} ({money(gc)})", "kind": "goal"})
        for d in cl.get("dependants", []) or []:
            if num(d.get("age")) is not None and num(d.get("support_years")) is not None:
                events.append({"age": int(age + num(d["support_years"])),
                               "label": f"{(d.get('name') or d.get('relation') or 'Dependant').capitalize()} independent", "kind": "family"})
        for e in c.get("timeline_events", []) or []:   # the client's own milestones: {"age": 45, "label": "Upgrade home"}
            if num(e.get("age")) is not None:
                events.append({"age": int(num(e["age"])), "label": e.get("label", ""), "kind": e.get("kind", "custom")})
        ro_mid = lasts(now["middle"])
        if ro_mid:
            events.append({"age": ro_mid, "label": "Savings run out at this pace (middle case)", "kind": "warn"})
        events.append({"age": plan_to, "label": f"Planning age {plan_to}", "kind": "end"})
        events.sort(key=lambda e: e["age"])
        home = (num(ast.get("home")) or 0) + (num(ast.get("other_property")) or 0)

        def pack(d):
            return None if d is None else {k: {"series": o[0], "lasts": lasts(o), "at_retirement": o[2], "left_at_end": o[3]}
                                           for k, o in d.items()}
        # ---- "for life" income: what their money can pay every month without ever eating into the capital
        # (lifelong income + only the real growth on savings, middle case), so the capital is left as legacy.
        passive = other_m + cpf_m
        mid = scen["middle"]

        def blend(move):
            cb, ib = cash0, inv0
            if move:
                sp = max(cb - keep, 0)
                cb, ib = cb - sp, ib + sp
            return (cb * cash_r + ib * mid) / (cb + ib) if cb + ib else mid
        r_now, r_plan = blend(False), blend("move_cash" in plan_kw)
        for_life = {"passive": passive,
                    "now": passive + max(now["middle"][2] * r_now, 0) / 12,
                    "plan": passive + max(plan["middle"][2] * r_plan, 0) / 12 if plan else None,
                    "capital_needed": (max((want or 0) - passive, 0) * 12 / mid) if want and mid > 0 else None,
                    "rate": mid}
        fl_m = for_life["plan"] if plan else for_life["now"]
        forlife = {k: sim(r, want_m=fl_m, **plan_kw) for k, r in scen.items()}
        db_today = db_face / (1 + infl) ** max(plan_to - age, 0)
        pol_end = polval(plan_to, False)
        pol_legacy = max(db_today, pol_end)            # on death the policy pays its death benefit (covers the cash value)
        todo_txt = []
        cash_n = [n for k, n in todo_pol if k == "cash"]
        ill_n = [n for k, n in todo_pol if k == "illus"]
        if cash_n:
            todo_txt.append("Current cash / surrender value for: " + ", ".join(cash_n))
        if ill_n:
            todo_txt.append(f"Illustrated value at {ret_age:.0f} (benefit illustration) for: " + ", ".join(ill_n))
        for tx in todo_txt:
            R.flag(2, "Policies", tx + ".")
        policies = {"series": [[a_, round(polval(a_, False))] for a_ in range(a0, plan_to + 1)], "now": polval(a0),
                    "db_face": db_face, "db_today": db_today, "legacy": pol_legacy, "todo": todo_txt, "list": pol_list,
                    "source": "FIC total" if pv_total_only else "per policy" if pols_v else None}
        timeline = {"now": pack(now), "plan": pack(plan), "forlife": pack(forlife), "forlife_monthly": fl_m,
                    "policies": policies,
                    "levers": levers, "events": events, "retire_age": ret_age,
                    "plan_to": plan_to, "property": home, "cpf_start": cpf_start, "want": want, "for_life": for_life,
                    "returns": {"cash": cash_r, **scen}, "series": now["middle"][0]}
        R.p(f"**Policies:** cash values today {money(policies['now'])}" + (f" ({policies['source']})" if policies['source'] else " (none on file)")
            + f"; death benefits still in force at {plan_to}: {money(db_face)} face value, about {money(db_today)} in today's dollars. "
            f"Left to pass on at {plan_to} (middle case, as things are): savings {money(now['middle'][3])} + policies {money(pol_legacy)}"
            + (f" + property {money(home)}" if home else "") + ". Cash values are not counted as spendable unless a policy is marked count_for_retirement.")
        if todo_txt:
            R.p("**Policy data to collect:** " + "; ".join(todo_txt) + ".")
        R.p(f"**For-life income** (lifelong income {money(passive)}/mo + only the real growth on savings, capital left intact): "
            f"as things are ~{money(for_life['now'])}/mo" + (f", with the plan ~{money(for_life['plan'])}/mo" if plan else "")
            + (f". Never-runs-out number for {money(want)}/mo: about {money(for_life['capital_needed'])} invested at retirement "
               f"(gap × 12 ÷ {pct(mid)} real)." if for_life["capital_needed"] is not None else "."))

        def lasts_txt(d):
            ages = [lasts(d[k]) or plan_to + 1 for k in ("cautious", "middle", "hopeful")]
            f = lambda x: f"{plan_to}+" if x > plan_to else str(x)
            return f(min(ages)) if min(ages) == max(ages) else f"{f(min(ages))}–{f(max(ages))}"
        R.p(f"Starting money: {money(cash0)} in cash" + (f" (incl. {money(oa_in)} withdrawable CPF OA)" if oa_in else "")
            + f" and {money(inv0)} invested. Cash earns {pct(cash_r)} real; invested money {pct(scen['cautious'])} / "
            f"{pct(scen['middle'])} / {pct(scen['hopeful'])} real (cautious / middle / hopeful). Committed savings "
            f"{money(committed)}/mo go in until retirement; dated goals come out in their year; left-over cash flow is not counted.")
        R.table(["", "At retirement (middle)", "Savings last until", f"Left at {plan_to} (middle)"],
                [["As things are", money(now["middle"][2]), lasts_txt(now), money(now["middle"][3])]]
                + ([["With the plan", money(plan["middle"][2]), lasts_txt(plan), money(plan["middle"][3])]] if plan else []))
        if levers:
            R.table(["Lever (on its own, middle case)", "At retirement", "Savings last until", f"Left at {plan_to}", "In the plan"],
                    [[l["title"], money(l["at_retirement"]), str(l["lasts"] or f"{plan_to}+"), money(l["left_at_end"]),
                      "yes" if l["in_plan"] else "option"] for l in levers])
        if want is None:
            R.p("No retirement income target: the retirement years show growth only, no spending.")
        elif ro_mid:
            R.p(f"**At {money(want)}/month, savings run out around age {lasts_txt(now)}** depending on markets "
                f"(planning age {plan_to}). After that only CPF LIFE" + (" and other lifelong income remain." if other_m else " remains."))
            R.flag(1 if ro_mid - age <= 25 else 2, "Retirement",
                   f"At the target income, savings run out around age {lasts_txt(now)} (planning age {plan_to}).")

    # ---------------- flags ----------------
    R.h("10. Shortfalls found (ranked)")
    R.flags.sort(key=lambda f: f["priority"])
    label = {1: "Act now", 2: "Soon", 3: "Review"}
    R.table(["#", "Priority", "Area", "Issue"], [[i + 1, label[f["priority"]], f["area"], f["issue"]] for i, f in enumerate(R.flags)])
    R.h("Assumptions used (label these as illustrative)")
    for k, v in A.items():
        R.p(f"- {k.replace('_', ' ')}: {v if not isinstance(v, float) else pct(v) if v < 1 else v}")
    lv = locals()
    visual = {   # everything the client PDF (client_report.py) draws, so it never redoes the maths
        "name": cl.get("name"), "age": age, "retire_age": ret_age, "stage": lv.get("stage"),
        "income": {"gross_monthly": gross, "take_home": take_total, "bonus_annual": bonus},
        "money_out": {"spending": None if spend is None else spend - prem_total / 12, "insurance": prem_total / 12,
                      "savings": committed, "left_over": surplus},
        "assets": {"Cash": cash or 0, "CPF": cpf or 0, "Property": prop or 0, "Investments": invested or 0,
                   "Other": personal or 0},
        "liabilities": liabs, "net_worth": nw,
        "emergency": {"months_have": div(cash, spend), "months_target": em_target, "target_amount": em_need,
                      "cash": cash},
        "protection": [
            {"label": "Death / TPD", "have": have["death_tpd"], "target": lv.get("need_dtpd")},
            {"label": "Critical illness", "have": have["ci"], "target": lv.get("need_ci")},
            {"label": "Early critical illness", "have": have["early_ci"], "target": lv.get("need_eci")},
            {"label": "Disability income (monthly)", "have": loi, "target": lv.get("need_loi")},
        ],
        "hospital": bool(hosp_plans) or bool(c.get("national", {}).get("has_ip")),
        "hospital_rider": bool(c.get("national", {}).get("has_rider")),
        "ltc": ltc > 0 or bool(c.get("national", {}).get("careshield")),
        "retirement_sources": lv.get("ret_sources", []),
        "goals": [{"name": g[0], "term": g[1], "cost": num(gg.get("cost")), "year": num(gg.get("year")), "monthly": g[6]}
                  for g, gg in zip(grows, c.get("goals", []))],
        "premium_pct": div(prem_total, None if take_total is None else take_total * 12),
        "savings_pct": div(None if surplus is None else surplus + committed, take_total),
        "debt_pct": div(liabs, assets),
        "invested_pct": div(invested, nw),
        "timeline": timeline,
    }
    return R, {"ratios": ratio_out, "retirement": ret_out, "flags": R.flags, "assumptions": A,
               "cash_flow": {"take_home": take_total, "spend": spend, "surplus": surplus, "committed": committed},
               "net_worth": nw, "visual": visual}


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    yr = int(a[a.index("--year") + 1]) if "--year" in a else datetime.date.today().year
    rep, data = main(a[0], yr)
    text = "\n".join(rep.lines) + "\n"
    if "--out" in a:
        open(a[a.index("--out") + 1], "w", encoding="utf-8").write(text)
    if "--json" in a:
        json.dump(data, open(a[a.index("--json") + 1], "w", encoding="utf-8"), indent=2, default=str)
    print(text)

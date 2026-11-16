"""Legacy planner: who gets what, through which channel, and how to make it fair.

  ./pa legacy_plan <client.json> [--out legacy.md] [--json legacy.json]

Reads the "estate" block of a client fact-find (see ../assets/legacy-template.json) and works out:
  1. Which rulebook moves each asset (from the Estate Planning Workshop notes): the will (or intestacy if none),
     CPF nomination, insurance nomination, or how property is held (joint tenancy = survivorship).
  2. What each heir receives today, if nothing changes (no will -> Intestate Succession Act 1967 split).
  3. What each heir receives under the client's wish (equal or chosen shares), including specific gifts
     (e.g. "the flat to Louis") of unequal value.
  4. Equalisation: how the rest of the estate should be split, and how much extra (e.g. insurance nominated to
     the others) is needed when one heir's specific gift is bigger than their fair share.
  5. Liquidity: what has to be paid before heirs get anything (debts, funeral, the HDB CPF refund) and what is
     frozen until probate.
  6. Flags: conflicts between will and joint tenancy, missing nominations, minors, HDB eligibility, Faraid.

General information for planning conversations only, not legal advice: every plan goes to a lawyer to draft.
Standard library only; nothing leaves this PC.
"""
import json, sys

def num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def money(x):
    if x is None:
        return "—"
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%".replace(".0%", "%")


L, FLAGS = [], []


def p(t=""):
    L.append(t)


def h(t):
    L.extend(["", f"## {t}", ""])


def table(head, rows):
    L.append("| " + " | ".join(head) + " |")
    L.append("|" + "---|" * len(head))
    for r in rows:
        L.append("| " + " | ".join(str(c) for c in r) + " |")
    L.append("")


def flag(prio, text):
    FLAGS.append((prio, text))


def intestacy(fam):
    """Intestate Succession Act 1967 (non-Muslims), as taught in the Estate Planning Workshop. Returns {heir: share}."""
    spouse = fam.get("spouse_name") if fam.get("spouse") else None
    kids = fam.get("children") or []
    parents = fam.get("parents") or []
    sibs = fam.get("siblings") or []
    if spouse and kids:
        out = {spouse: 0.5}
        out.update({k: 0.5 / len(kids) for k in kids})
        return out, "Spouse 50% · children share 50% equally"
    if kids:
        return {k: 1 / len(kids) for k in kids}, "Children share everything equally"
    if spouse and parents:
        out = {spouse: 0.5}
        out.update({q: 0.5 / len(parents) for q in parents})
        return out, "Spouse 50% · parents share 50%"
    if spouse:
        return {spouse: 1.0}, "Spouse receives 100%"
    if parents:
        return {q: 1 / len(parents) for q in parents}, "Parents share everything equally"
    if sibs:
        return {s: 1 / len(sibs) for s in sibs}, "Siblings share equally (no spouse, children or parents)"
    return {"(further relatives / the State)": 1.0}, "Further relatives, then the Government"


def main(path):
    c = json.load(open(path, encoding="utf-8"))
    e = c.get("estate") or {}
    name = c.get("client", {}).get("name", "(client)")
    fam = e.get("family", {})
    p(f"# Legacy plan: {name}")
    p("_General information to plan the conversation. Not legal advice: the will, trusts and nominations are "
      "drafted by a lawyer._")
    if not e:
        p("\nNo `estate` block in the fact-find. Fill in assets, family and wishes first (legacy-template.json).")
        return {}
    if e.get("muslim"):
        flag(1, "Muslim estate: Faraid under the Administration of Muslim Law Act applies (Inheritance Certificate "
                "from the Syariah Court). A wasiat can only pass up to 1/3 to non-heirs. The shares below are NOT "
                "Faraid shares: work this one with a lawyer.")

    heirs = list(dict.fromkeys(
        ([fam.get("spouse_name")] if fam.get("spouse") and fam.get("spouse_name") else [])
        + (fam.get("children") or []) + list((e.get("wish") or {}).get("shares", {}).keys())))
    has_will = bool(e.get("will"))
    intest, intest_rule = intestacy(fam)

    # ---------------- 1. channels ----------------
    rows, estate_pool, cpf_refunds = [], [], 0.0
    outside = {}          # heir -> amount received outside the will
    gifts = {}            # heir -> net value of specific gifts in the will
    liquid_estate = 0.0   # cash-like assets in the estate (frozen until probate)
    w_fixed, w_adj = {}, 0.0   # wish scenario: what's pinned to a person vs what the will/nominations can steer
    cpf_nom = None
    fast_amt = 0.0   # reaches family quickly: nominated CPF/insurance, survivorship
    def pin(k, v):
        w_fixed[k] = w_fixed.get(k, 0) + v
    debts = num(e.get("debts")) or 0
    for a in e.get("assets", []):
        t = a.get("type", "other")
        val = (num(a.get("value")) or 0) * (num(a.get("share")) if num(a.get("share")) is not None else 1)
        mort = num(a.get("mortgage")) or 0
        holding = a.get("holding", "sole")
        if t == "cpf":
            nom = a.get("nominees") or {}
            cpf_nom = nom or None
            w_adj += val
            if nom:
                for k, s in nom.items():
                    outside[k] = outside.get(k, 0) + val * s
                fast_amt += val
                rows.append([a.get("name", "CPF"), money(val), "CPF nomination", ", ".join(f"{k} {pct(s)}" for k, s in nom.items())])
            else:
                rows.append([a.get("name", "CPF"), money(val), "No nomination → Public Trustee → intestacy", intest_rule])
                for k, s in intest.items():
                    outside[k] = outside.get(k, 0) + val * s
                flag(1, f"No CPF nomination: {money(val)} goes to the Public Trustee, is split by intestacy law "
                        "(not the client's wishes), takes months, and incurs a fee (~$900 per $100k). Free to fix online.")
            continue
        if t == "insurance":
            nom = a.get("nominees") or {}
            kind = a.get("nomination", "none")
            if kind == "trust" and nom:
                for k, s_ in nom.items():
                    pin(k, val * s_)
            else:
                w_adj += val
            if nom and kind in ("revocable", "trust"):
                for k, s in nom.items():
                    outside[k] = outside.get(k, 0) + val * s
                fast_amt += val
                law = "s.132 trust (irrevocable)" if kind == "trust" else "s.133 revocable"
                rows.append([a.get("name", "Policy"), money(val), f"Insurance nomination ({law})",
                             ", ".join(f"{k} {pct(s)}" for k, s in nom.items())])
            else:
                estate_pool.append((a.get("name", "Policy"), val))
                liquid_estate += val
                rows.append([a.get("name", "Policy"), money(val), "No nomination → falls into the estate", "will / intestacy"])
                flag(2, f"{a.get('name', 'A policy')} has no nomination: its payout waits for probate instead of "
                        "reaching the family in weeks.")
            continue
        if t.startswith("property"):
            refund = num(a.get("cpf_refund")) or 0
            net = val - mort - refund
            if holding == "joint_tenancy":
                co = a.get("co_owner", "co-owner")
                outside[co] = outside.get(co, 0) + val - mort
                if a.get("to") and a.get("to") != co:   # wish assumes the holding is changed so the will can pass it
                    refund = num(a.get("cpf_refund")) or 0
                    pin(a["to"], val - mort - (refund if t == "property_hdb" else 0))
                    w_adj += refund if t == "property_hdb" else 0
                else:
                    pin(co, val - mort)
                fast_amt += val - mort
                rows.append([a.get("name", "Property"), money(val), "Joint tenancy → survivorship", f"{co} automatically"])
                if a.get("to") and a.get("to") != co:
                    flag(1, f"{a.get('name')}: the wish is for {a['to']} to get it, but it's held in joint tenancy "
                            f"with {co}, so it passes to {co} automatically and the will can't change that. "
                            "Consider severing to tenancy-in-common (lawyer).")
                continue
            if t == "property_hdb":
                cpf_refunds += refund
                if refund:
                    p("")
                if a.get("to"):
                    flag(2, f"{a.get('name')} (HDB) to {a['to']}: they must be eligible to own it (SC/PR, HDB rules), and "
                            f"the CPF used plus interest ({money(refund)}) must be refunded before transfer. "
                            "If they can't fund that, they may have to sell.")
            if a.get("to"):
                pin(a["to"], net)
                w_adj += refund          # the CPF refund goes back to CPF, then out by CPF nomination
            else:
                w_adj += val - mort
            channel = "Will (specific gift)" if a.get("to") and has_will else "Estate → will / intestacy"
            if holding == "tenancy_in_common":
                channel += " · tenancy-in-common share"
            if a.get("to") and has_will:
                gifts[a["to"]] = gifts.get(a["to"], 0) + net
                rows.append([a.get("name", "Property"), money(val), channel,
                             f"{a['to']} (net {money(net)} after loan {money(mort)} & CPF refund {money(refund)})"])
            else:
                estate_pool.append((a.get("name", "Property"), net))
                rows.append([a.get("name", "Property"), money(val), channel, f"net {money(net)} into the estate"])
            continue
        # cash, investments, SRS, business, other: all pass by will (frozen until probate)
        to = a.get("to")
        if to:
            pin(to, val - mort)
        else:
            w_adj += val - mort
        if to and has_will:
            gifts[to] = gifts.get(to, 0) + val - mort
            rows.append([a.get("name", t), money(val), "Will (specific gift)", to])
        else:
            estate_pool.append((a.get("name", t), val - mort))
            rows.append([a.get("name", t), money(val), "Estate → will / intestacy", "frozen until probate"])
        if t in ("cash", "investments", "srs"):
            liquid_estate += val - mort

    h("1. Which rulebook moves each asset")
    p("A will controls only what's in the estate. CPF follows the CPF nomination, insurance follows its nomination, "
      "and jointly held property goes to the surviving joint owner. Each of these overrides the will.")
    p("")
    table(["Asset", "Value", "Passes by", "To"], rows)

    if cpf_refunds and has_will:
        for k, sh in (cpf_nom or intest).items():
            outside[k] = outside.get(k, 0) + cpf_refunds * sh
    residual = sum(v for _, v in estate_pool) - debts
    funeral = num(e.get("funeral_and_costs")) or 0
    residual -= funeral
    total = residual + sum(gifts.values()) + sum(outside.values())

    # ---------------- 2. today ----------------
    h("2. What each person gets today, if nothing changes")
    who = list(dict.fromkeys(heirs + list(outside) + list(gifts) + list(intest)))
    if has_will:
        res_split = (e.get("will_residuary_shares") or {})
        p(f"The client has a will. Residuary estate {money(residual)} split per the will"
          + ("" if res_split else " (shares not recorded: ask for the will)") + ".")
    else:
        res_split = intest
        p(f"**No will:** the estate ({money(residual)} after debts and costs) is split by the Intestate Succession Act: "
          f"{intest_rule}.")
        flag(1, "No will: the estate follows the Intestate Succession Act, whatever the client would have wanted.")
    p("")
    now = {}
    for k in who:
        now[k] = outside.get(k, 0) + gifts.get(k, 0) + residual * res_split.get(k, 0)
    table(["Person", "Outside the will", "Specific gifts", "From the estate", "Total", "Share"],
          [[k, money(outside.get(k, 0)), money(gifts.get(k, 0)), money(residual * res_split.get(k, 0)),
            money(now[k]), pct(now[k] / total if total else None)] for k in who if now[k] or k in heirs])

    # ---------------- 3+4. wish & equalisation ----------------
    wish = e.get("wish") or {}
    out = {"total": total, "now": now}
    h("3. What they want, and how to make it fair")
    if not wish:
        p("Wishes not captured yet. Ask: who should benefit, equally or in different amounts, does anyone get a "
          "specific asset (the flat, the car, the business), and should anyone's share be held in trust?")
        flag(2, "Legacy wishes not captured.")
    else:
        if wish.get("type") == "equal":
            names = wish.get("heirs") or (fam.get("children") or heirs)
            target = {k: 1 / len(names) for k in names}
        else:
            target = {k: num(v) or 0 for k, v in (wish.get("shares") or {}).items()}
            tot_s = sum(target.values()) or 1
            target = {k: v / tot_s for k, v in target.items()}
        adj = w_adj - debts - (num(e.get("funeral_and_costs")) or 0)
        stray = {k: v for k, v in w_fixed.items() if k not in target and v}
        if stray:
            flag(2, "Some assets are meant for people outside the main split: "
                    + ", ".join(f"{k} {money(v)}" for k, v in stray.items()) + ".")
        base = adj + sum(v for k, v in w_fixed.items() if k in target)
        need_T = max([w_fixed.get(k, 0) / sh for k, sh in target.items() if sh] + [base])
        topup = max(need_T - base, 0)
        T = base + topup
        need = {k: max(target[k] * T - w_fixed.get(k, 0), 0) for k in target}
        p("This assumes the client's wishes are put in place: a will for the specific gifts, and the CPF and "
          "insurance nominations and the rest of the estate used to balance things out. Irrevocable (s.132) trust "
          "nominations can't be changed.")
        p("")
        table(["Person", "Fair share", "Fair amount", "Specific gifts / trust nominations", "Needs from the rest",
               "Today (if nothing changes)"],
              [[k, pct(target[k]), money(target[k] * T), money(w_fixed.get(k, 0)), money(need[k]), money(now.get(k, 0))]
               for k in target])
        p(f"Money that can be steered (estate after debts and costs, CPF incl. HDB CPF refunds, revocable policies): "
          f"**{money(adj)}**.")
        if topup > 0:
            over = [k for k in target if w_fixed.get(k, 0) > target[k] * base]
            under = [k for k in target if need[k] > 0]
            p(f"**Equalising:** {', '.join(over)}'s specific gift is worth more than a fair share of everything. "
              f"To even it out without selling the asset, about **{money(topup)}** more is needed for "
              f"{', '.join(under)}. This can be new or existing life insurance nominated to them, which is paid outside probate "
              "within weeks. The alternative is to accept an unequal split on purpose and write that into the will.")
            flag(1, f"Unequal assets: ~{money(topup)} of extra legacy (e.g. insurance nominated to {', '.join(under)}) "
                    "is needed to give everyone their fair share.")
        tot_need = sum(need.values())
        if tot_need:
            p("Split the steerable money roughly as: " + ", ".join(f"{k} {pct(need[k] / tot_need)}" for k in target)
              + ". Apply this to the will's residuary estate, the CPF nomination and revocable policy nominations, "
              "or point whole channels at one person where that's simpler (e.g. CPF all to one person, cash to another).")
        gaps = {k: target[k] * T - now.get(k, 0) for k in target}
        if any(abs(v) > max(1000, 0.02 * T) for v in gaps.values()):
            flag(1, "Today's arrangements don't match the wish: "
                    + "; ".join(f"{k} {'+' if v > 0 else ''}{money(v)}" for k, v in gaps.items()) + ".")
        out.update(target=target, topup=topup, steerable=adj, needs=need)

    # ---------------- 5. liquidity ----------------
    h("4. Liquidity: what has to be paid before anyone inherits")
    fast = fast_amt
    table(["", "Amount"], [
        ["Debts to settle", money(debts)], ["Funeral and estate costs (as recorded)", money(funeral)],
        ["HDB CPF refunds the property heirs must fund", money(cpf_refunds)],
        ["Cash-type assets in the estate (frozen 3–6 months, longer if contested)", money(liquid_estate)],
        ["Reaches the family quickly (nominated CPF / insurance, survivorship)", money(fast)],
    ])
    if not funeral:
        flag(3, "Funeral and estate costs not recorded: ask for an estimate.")
    if debts + funeral > liquid_estate:
        flag(1, f"Not enough cash in the estate ({money(liquid_estate)}) to settle debts and costs ({money(debts + funeral)}): "
                "the family may have to sell an asset. A nominated policy can bridge this.")

    # ---------------- 6. other checks ----------------
    for k, age in (fam.get("ages") or {}).items():
        if num(age) is not None and num(age) < 21:
            flag(1, f"{k} is under 21: name a testamentary guardian, and consider a trust (or s.132 trust nomination) "
                    "so the money isn't paid out in one lump sum at 21.")
    if e.get("lpa") is False:
        flag(2, "No LPA: if capacity is lost, the family needs a court deputyship (slow, costly). Form 1 is free for "
                "citizens from 1 Apr 2026.")
    if fam.get("recently_married_or_divorced"):
        flag(1, "Marriage revokes an earlier will, but divorce does NOT: review the will and all nominations.")

    h("5. To do (ranked)")
    lab = {1: "Act now", 2: "Soon", 3: "Review"}
    table(["#", "Priority", "Item"], [[i + 1, lab[pr], t] for i, (pr, t) in enumerate(sorted(FLAGS, key=lambda f: f[0]))])
    p("Next step: take this to an estate lawyer to draft the will, any trust and nomination changes. "
      "Make sure the will, CPF nomination, insurance nominations and property holding all point the same way.")
    out["flags"] = FLAGS
    out["channels"] = [{"asset": r[0], "value": r[1], "route": r[2], "to": r[3]} for r in rows]
    ins = [x for x in e.get("assets", []) if x.get("type") == "insurance"]
    cpf = [x for x in e.get("assets", []) if x.get("type") == "cpf"]
    homes = [x for x in e.get("assets", []) if str(x.get("type", "")).startswith("property")]
    def st(x):
        return "yes" if x is True else "no" if x is False else "unknown"
    known = e.get("confirmed", True)   # False = will/nominations not asked yet -> show "?" not "x"
    def yn(flag_yes, has_items=True):
        if not has_items:
            return "unknown"
        return "yes" if flag_yes else ("no" if known else "unknown")
    out["checklist"] = [
        ["A valid, up-to-date will", yn(bool(e.get("will")))],
        ["CPF nomination", yn(bool(cpf) and all(c.get("nominees") for c in cpf), bool(cpf))],
        ["Insurance nominations", yn(bool(ins) and all(i.get("nominees") for i in ins), bool(ins))],
        ["Know how your home is held", "yes" if homes and all(h.get("holding_confirmed") for h in homes) else "unknown"],
        ["Lasting Power of Attorney", st(e.get("lpa"))],
        ["Cash ready for costs during probate", "yes" if fast > 0 else "no"],
    ]
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    data = main(a[0])
    text = "\n".join(L) + "\n"
    if "--out" in a:
        open(a[a.index("--out") + 1], "w", encoding="utf-8").write(text)
    if "--json" in a:
        json.dump(data, open(a[a.index("--json") + 1], "w", encoding="utf-8"), indent=2, default=str)
    print(text)

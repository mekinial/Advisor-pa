---
name: financial-health-check
description: Analyse one person's finances and portfolio the Planners Inc way (Financial Inventory Check), including legacy and estate distribution (who inherits what, intestacy, CPF/insurance nominations, joint tenancy, equalising unequal assets like property vs cash). Works out their ratios, protection gaps against the Planners Inc protection guidelines, emergency fund, retirement number vs projected income, ST/MT/LT goal funding and legacy gaps, then turns every shortfall into prioritised things to do. Use this whenever the adviser asks to review, analyse or "do a health check / FIC / needs analysis / gap analysis" on a client or lead. Also use it when she asks whether someone is on track for retirement or a goal, what they're missing, how much cover they need, or what to talk about at a review meeting, even if she doesn't say "health check". The proposal-writer and client-report agents use it as their analysis step.
---

# Financial health check

This skill turns a fact-find into a clear picture of where someone stands, what's missing, and what to do
next. It uses the Planners Inc framework the adviser already uses with clients: the Financial Inventory Check (FIC),
the Good / Not so good / Bad analysis, the six accounts, and the four-question retirement number. The point
is to make her review meetings faster and sharper, not to replace her judgement. Everything is a draft for
her.

## The workflow

### 1. Gather the facts (only real ones)

**Fast path: the client's FIC has a hidden "Export" tab.** Read `Export!A1:C80` first and look for a `fic.version` row.
1. Save what you read as `Drafts/Client Reports/<first name>-fic-raw.json`:
   - **v3 (there is a `fic.version` row): ONE read**, `Export!A1:AM115`:
     ```json
     {"source": "<FIC file name> (Google Drive, read <date>)", "export_all": Export!A1:AM115}
     ```
   - **v2 (no `fic.version` row): seven ranges**:
     ```json
     {"source": "<FIC file name> (Google Drive, read <date>)",
      "export": Export!A1:B80, "policies": 'Existing Policies'!A7:AE40,
      "goals_st": Goals!C14:H18, "goals_mt": Goals!I14:N18, "goals_lt": Goals!O14:S18,
      "dependants": 'About You & Estate'!B14:F19, "lifelong": 'About You & Estate'!B33:F38}
     ```
2. Build the fact-find:
   `./pa .claude/skills/financial-health-check/scripts/fic_import.py "<fic-raw.json>" --out "Drafts/Client Reports/<first name>-factfind.json"`
3. Read what it prints:
   - **Missing** fields go on the next-meeting list.
   - **STOP** means the sheet's layout doesn't match (it names the heading). Fix the heading in the FIC or ask; never
     work around it by reading cells by position.
   - It warns when the FIC still shows the Mr Prospect demo, or when figures identical to the sample are left in a
     renamed copy.
   - It leaves out policies whose Status isn't "In force" (or, in v2, marked Lapsed), and policies that cover a
     spouse, child or parent (kept under `insurance_family`), and says so.
   - It flags cash values more than a year old and policies with no Policy Type picked.
   - If the FIC has the new Investments tab, it also brings in what they hold today (`holdings`) and their risk
     profile (`investments`), and says when the holdings don't add up to the Assets & Liabilities figure.
   - Policy numbers are never read.
4. Add the estate block from `estate_hints` if a legacy plan is wanted. Then continue at step 2.

The importer reads both layouts: v3 (status and type dropdowns, one-read Export tab) and v2.
An older FIC with no Export tab still needs the manual route below.

Look in these places, and note which file each fact came from:

- **The client's FIC in Google Drive.** Search Drive for `<name> Financial Inventory Check` and read it with
  the Sheets connector. Sheets: You, Cash Flow, CPF, Assets & Liabilities, Current Insurance,
  Wealth Insights, Wealth Projections. Take figures from the **Cash Flow, Assets & Liabilities and Existing
  Policies** tabs. The newer Master Copy-based FICs often still have the template's sample numbers on the
  "Data Sheet" and "Goals" tabs (e.g. CPF 100,000 / 40,000 / 43,040, a GWA illustration of 1,124,537). If a figure matches the
  template, treat it as missing and say so in "Check before presenting".
- `Data/Clients/<Name>/`: goals, statements, notes.
- `Drafts/Meetings/*-<first name>-notes.md`: what they said at meetings (goals, worries, life events).
- **Policies workbook** `Data/Client Policies.xlsx` (read only).
  The "All Policies" sheet has their GE policies. Read it with openpyxl.
- `Data/pipeline.csv`: stage and notes.

Copy `assets/client-template.json` to `Drafts/Client Reports/<first name>-factfind.json` and fill it in.
**Leave unknowns as null.** The calculator reports them as missing, and a list of what to ask is far more
useful to the adviser than a guess. Never put NRIC, policy numbers or bank details in this file. Health details
don't belong in it either. If they matter (e.g. an exclusion), mention them only in "Check before presenting".

For clients aged 55+ whose Retirement Account is set aside, CPF OA can be withdrawn. Set
`"cpf_oa_withdrawable": true` under `retirement` so the OA counts as retirement capital. the adviser's roadmaps count it
that way (e.g. "liquid cash" = cash + OA).

**Policy values.** On each policy in `insurance`, fill in whatever the files give:
- `cash_value`: current surrender value
- `cash_value_at_retirement`: the benefit illustration's value at their retirement age
- `maturity_age` / `maturity_amount`
- `death_benefit`: for death-only payouts such as annuity death benefits. It counts towards legacy but not the
  protection check.

The FIC's Existing Policies tab has no cash value column. The A&L tab has only one total ("Insurance Policies
Surrender Value"), so put that in `assets.policy_cash_value`. It's carried flat if no per-policy values exist. Annuity
details are in Existing Policies "Riders / Others" (expected payouts, death benefit). Anything missing goes
automatically on the calculator's "Policy data to collect" list, the flags, and the client PDF's next-meeting
checklist.

The calculator then works out:
- **Policy cash values over time**, in today's dollars, shown as a gold layer on the timeline. They're not counted
  as spendable unless `count_for_retirement` is true, because cashing in ends the cover.
- **Maturities**, which arrive as cash at their age.
- **Death benefits still in force at the planning age** (whole life, ILP, annuities; not term). These are added to
  "Left to pass on" in today's dollars: the larger of the death benefit and the cash value.

If income, expenses or age are missing, you can still run it. Say plainly that the result is partial and
list what to collect.

### 2. Run the calculator

```
./pa .claude/skills/financial-health-check/scripts/health_check.py "Drafts/Client Reports/<first name>-factfind.json" --out "Drafts/Client Reports/<first name>-health-check-numbers-YYYY-MM-DD.md" --json "<same>.json"
```

It does all the arithmetic:
- cash flow and balance sheet
- the 11 FIC ratios against their guides
- the six-account allocation
- protection vs the Planners Inc guidelines (12× death/TPD/TI, 5× CI, 3× early CI, 75% disability income) and a
  needs-based check
- retirement want vs projected income and the gap
- monthly saving needed per goal
- a ranked list of shortfalls

Don't redo these sums by hand, and don't change its numbers in the write-up. If something looks wrong,
fix the input JSON and run it again.

### 3. Write the analysis

Read `references/benchmarks.md` for the guides and their sources. Read `references/retirement.md` when
there's a retirement question or the client is 50+.

Save to `Drafts/Client Reports/<first name>-health-check-YYYY-MM-DD.md` with this structure:

```markdown
# <Name>: financial health check (<date>)

## At a glance                      ← for the adviser: 5 lines max
Stage/persona, net worth, surplus, the 3 biggest gaps, what's missing from the fact-find.

## Where you stand today            ← client-facing from here down
Short narrative in plain English using their own words from Wealth Insights / meeting notes.

## The analysis
**Good**: genuine strengths first (be specific: "you already keep 7 months of expenses in cash").
**Not so good**: things that aren't ideal yet.
**Bad**: real problems that need fixing.

## Your numbers
Cash flow, the ratios table (Result / Guide / Status) and the six accounts, from the calculator.

## Protection
What they have vs the guides, per type (death/TPD, CI, early CI, hospital, disability income,
long-term care, accident). Show the working. Note existing DPS/HPS/group cover.

## Goals
ST / MT / LT goals: cost today, cost then, set aside, monthly needed. Say whether the surplus covers them.

## Retirement
The four questions: want → have → heading → gap, with the 4% and inflation assumptions stated.

## What to do, in order
Numbered actions, most urgent first (see "Turning gaps into actions").

## Next steps
What to bring or confirm at the next meeting.

## Check before presenting           ← for the adviser only; make_pdf.py strips this section
Missing facts, assumptions to confirm, anything sensitive, figures older than 12 months.
```

### Life stage changes what matters

the adviser's view: **insurance guards the working years.** If something happens while someone is still earning, cover
replaces that income for them and their dependants. As people get older, the job shifts from covering working
income to **generating passive cash flow and leaving a legacy.** The calculator does this automatically:

- Death/TPD/TI, CI and early CI targets are the Planners Inc multiples **capped at the working years left**
  (the retirement age **the client sets** − age), applied to their **current** income. Someone at peak earnings
  just before retiring is measured on that peak, e.g. 63, earning $200k, retiring at 65 → 2 × $200k. Someone
  of 60 working to 70 still gets 10× and stays in a working stage. Always capture their planned retirement age.
  If it's missing, 65 is assumed and flagged. At 34 the full 12× applies. At 57 with 8 years left it's 8×, and at 64 it's 1×.
  After retirement there's no income left to replace.
- Disability income is only targeted while more than 2 working years remain.
- Dependants override the taper. If a dependant needs support beyond retirement, the needs-based figure is used.
- Long-term care rises to "Act now" from 50, and legacy wishes are flagged for the Distributor stage.

| Stage | Age | What the report should lead with |
|---|---|---|
| The Builder | under 40 | Emergency cash, protecting income (full multiples), starting long-term savings early |
| The Accumulator | 40–49 | Protection for a growing family and income, growth, lifestyle creep vs goals |
| The Optimiser | 50–59 | The retirement gap in real numbers. Protection tapers as working years run out. LTC and CPF levers |
| The Distributor | ≤ 5 yrs to **their own** retirement age | Retirement income that lasts (CPF LIFE, the three buckets), health and long-term care, premiums that continue after salary, legacy (will, nominations, LPA, what to leave and to whom) |

For a Distributor, frame existing life/CI cover as a **health buffer and legacy**, not an income gap. Don't
recommend new income-replacement cover unless someone still depends on their income.

### Legacy: who gets what, and how to make it fair

When legacy comes up (any Distributor client, anyone with property or a blended family, or when the adviser asks "how
should X leave things"), run the legacy planner as well. Read `references/legacy.md` first. It follows the adviser's
Estate Planning Workshop.

1. Add an `estate` block to the fact-find (copy from `assets/legacy-template.json`). It needs:
   - family: spouse, children and their ages, parents, siblings
   - each asset with its value, loan, how it's held (sole / joint tenancy / tenancy-in-common), the HDB CPF refund,
     and who it's meant for (`to`)
   - CPF and insurance nominations
   - whether there's a will
   - the wish: equal, or chosen shares
2. Run: `./pa .claude/skills/financial-health-check/scripts/legacy_plan.py "<factfind.json>" --out "Drafts/Client Reports/<first name>-legacy-YYYY-MM-DD.md"`
3. It shows:
   - which rulebook moves each asset
   - what each person gets **today** (intestacy if there's no will)
   - the fair amount per person under their wish, with specific assets valued net of loans and CPF refunds
   - how to split the rest to balance unequal assets
   - how much extra (e.g. nominated insurance) is needed when one asset is worth more than a fair share
   - liquidity during the probate freeze
   - conflicts: joint tenancy vs the will, missing nominations, minors, HDB eligibility, Faraid
4. In the write-up, explain it in plain words, e.g. "Today Amy would get 71% and Ben 29%. To make it 50/50…".
   Make sure the will, CPF nomination, insurance nominations and how the property is held all point the same way.
   Always end with "draft with an estate lawyer". Never present it as legal advice.

### Turning gaps into actions

The calculator's ranked list is the raw material. Turn each item into an action the client can picture,
and order them the way a sound plan does. Each step protects the ones after it. This order is for the working
stages. For a Distributor, lead with retirement income, then long-term care and health, then premiums vs the
retirement budget, then legacy:

1. **Stop the bleeding.** Negative cash flow, high-interest debt, and debt-service ratios over the guide.
2. **Emergency fund.** Build it to the Planners Inc level for their household before investing more:
   single 3 months, married with no kids 6, 1 kid 9, 2 or more kids 12 (12 if income is irregular). Fill in
   `marital_status` and `children` in the fact-find so the calculator picks the right level.
3. **Protect the income and the family.** Hospital first, then death/TPD and CI gaps (term cover is the
   cost-effective way to close a pure gap), then disability income and long-term care.
4. **Fund the goals.** ST in safe places (FD, T-bills, SSB), MT from the surplus, LT at 10%+ of income.
5. **Retirement.** Use the levers: time, contributions (CPF top-ups, SRS), growth, income generation,
   protection and expectations. Review what they already own before adding anything new.
6. **Legacy.** Will, CPF nomination, insurance nominations, LPA, ACP. These are quick wins with no cost to the client.

For each action, say **why** (which number it fixes) and **what kind of solution** fits. Don't name a
specific plan unless the adviser asked for one or already noted it. If she did, get product facts from the
GE Product Library (`Tools/library_search.py search "..."`) and quote the document. Never use memory for
premiums, features or illustrations.

## Rules that keep this MAS-safe

- **Facts only from the files.** If a figure isn't there, it's missing. Don't estimate it.
- **Label every rule of thumb as a general guide.** Name its source (Planners Inc, MoneySense), and say that the
  right amount depends on a full needs analysis.
- **Protection is measured against the Planners Inc guidelines** in `references/protection-guides.json`, not the
  LIA 9×/4× (the adviser sees that as the bare minimum and wants a comfortable buffer for a catastrophic illness).
  Don't quote 9×/4× unless she asks. If the file's guides are unset, say so rather than falling back to LIA.
- **Projections are illustrative.** Write "illustrative, not guaranteed" next to the 4% drawdown, the
  inflation rate and any return assumption. CPF LIFE amounts must be the client's own estimate from the
  CPF planner.
- **No guaranteed-return language** for anything market-linked. Say that ILP and fund values can fall.
- **No NRIC, policy numbers, bank details or health details** in anything the client will see.
- **Recommend kinds of solution, not products.** "Term cover to 65 to close the death/TPD gap", not a plan name,
  unless the adviser chose it.

### 4. The client version (a visual PDF they can keep)

The analysis `.md` is the adviser's working copy. Never give it to a client: "At a glance" and "Check before presenting"
are internal. For the client, make a separate visual PDF:

1. Run the calculator with `--json` (step 2). Its `visual` block holds every figure the charts use.
2. Write `Drafts/Client Reports/<first name>-story.json` from `assets/client-story-template.json`. It holds the words
   only: plain English, short bullets, in the adviser's voice, with a warm cover note from her. Leave out internal notes and
   anything you're unsure of. Every figure must match the calculator. If a goal or figure is uncertain, say "let's
   confirm" rather than presenting it as fact.
3. Render:
   `./pa .claude/skills/financial-health-check/scripts/client_report.py "<numbers.json>" "<story.json>" --out "Drafts/Client Reports/<first name>-health-check-client-YYYY-MM-DD.pdf" [--legacy "<legacy.json>"]`
4. Check the layout before handing it over. Add `--html`, open the `.html` in the browser pane, and make sure nothing
   runs past the footer on any page, especially the protection-and-goals page when there are 4 goals and retirement.
   Shorten the story text if it does.

What the PDF contains:
- a cover with the adviser's handwritten-style note and their life stage
- a snapshot page: net worth / surplus / emergency / protection tiles, a money-each-month bar, a what-you-own donut,
  and an emergency-cushion gauge
- a traffic-light health check plus "What's working / Worth improving / Needs action" cards and the adviser's take
- protection: cover vs the Planners Inc guideline bars, plus hospital and LTC ticks. Goals as cards, and a retirement
  "what you want vs what you're building" bar
- a life timeline page, from today to their planning age (default 90; set `retirement.plan_to_age`):
  - tiles for money at retirement, the age savings last to (a range), and what's left to pass on, each
    "as things are" and "with the plan"
  - a chart of liquid money by age with two paths: **as things are** (teal) and **with the plan** (navy, dashed).
    Each is a middle line inside a cautious-to-hopeful band, because markets can go either way
  - milestone pins (today, CPF at 55, retirement, CPF LIFE, dated goals, dependants independent, `timeline_events`,
    savings run out), and "Working years → Retirement → Legacy" phase cards with "You are here"
- a **"Making it grow / Making it last"** page: one bar per lever, each on its own vs today (middle case).
  Working clients (5+ years to retirement) see money at retirement; near or in retirement, the age savings last to
  and years of retirement covered. Levers:
  - invest part of the monthly surplus (default half, only with 3+ working years; `levers.invest_monthly`)
  - put spare cash above the emergency fund to work
  - retire N years later (`levers.retire_later_years`, default 2)
  - spend X% less in retirement (`levers.spend_less_pct`, default 10%)
  - defer CPF LIFE to 70 (CPF: up to ~7% more a year deferred)

  Only levers that actually help are shown. The first two are money levers and make up "the plan". The others are
  lifestyle choices ("Your choice"), except CPF deferral when `levers.plan_defer_cpf` is true.

  How the calculator's section 9 works, all in today's dollars:
  - Cash (incl. withdrawable CPF OA) grows at `cash_return` (default 1.5%, about −1% real).
  - Invested money grows at `scenario_returns` cautious / middle / hopeful (default 2.5% / 4% / 6%, i.e. 0% / 1.5% /
    3.5% real).
  - Committed savings go in until retirement, and dated goals come out in their year. Left-over cash flow counts
    only through the invest lever.
  - In retirement it spends cash first and draws the target income minus CPF LIFE and other lifelong income. If
    lifelong income covers the target, savings keep growing.
  - **The goal we plan for is money that never runs out** and is passed on. The levers page opens with "The goal:
    money that never runs out". **For-life income** = lifelong income (CPF LIFE + annuities in
    `other_monthly_income`) + only the real growth on savings at retirement. The capital stays intact as legacy.
    It shows as-things-are vs with-the-plan vs their goal. When the goal is covered it says so. When it isn't, it
    gives the **never-runs-out number**: (goal − lifelong income) × 12 ÷ middle real return, invested by retirement.
    If someone's lifelong income already covers the goal, their timeline shows "For life ✓" and keeps growing.
  - **"Your plan, year by year"** page (after the levers page): its own chart with three paths, each in the middle case
    with a band: as things are (teal), the plan spending the full goal (navy), and the plan living on for-life
    income (gold, stays whole to pass on). Three cards underneath compare them. The timeline chart shows only
    today's path, so the plan isn't lost in it. Optional story field: `plan_note`.
  - Treat the band as the honest message: "depending on markets". Never quote one age as a prediction.
- an optional legacy page (who gets what today vs their wish)
- a numbered plan, a next-meeting checklist, and the MAS-safe disclaimer

## When it's done

- Tell the adviser the 3 biggest gaps, what's missing from the fact-find, and the file paths.
- For a PDF, hand over to proposal-writer, or run
  `./pa make_pdf "<draft.md>" --client "<Name>" --kind "Financial Health Check"`.
- If she's on Telegram, post it to the reports topic:
  `./pa telegram_post reports "<Name>: health check ready, <n> gaps" --file "<pdf or md>"`.

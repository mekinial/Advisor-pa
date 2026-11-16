# Benchmarks and where they come from

Use these as **general guides**, never as requirements. In anything a client will see, write
"a common guide is…" or "as a general rule of thumb…", and name the source when one exists.

## Financial ratios: Planners Inc Financial Inventory Check ("Financial Ratios" sheet)

| Ratio | Formula | Guide | What it tells you |
|---|---|---|---|
| Basic liquidity | Cash or near cash ÷ monthly expenses | Planners Inc emergency-cash months by household (see below) | Whether they can ride out an emergency without selling investments or borrowing |
| Liquid assets to net worth | Cash or near cash ÷ net worth | ≥ 15% | Whether enough of their wealth is reachable |
| Savings ratio | Savings ÷ income: (1) positive cash flow, (2) positive cash flow + committed savings | ≥ 10% | Whether they are building anything |
| Debt to assets | Total liabilities ÷ total assets | > 50% is a concern | Medium- to long-term solvency |
| Solvency | Net worth ÷ total assets | Higher is stronger | Long-term solvency |
| Fixed expenses | Fixed expenses ÷ take-home income | ≤ 55% | Room to adjust if income drops |
| Debt service | All loan repayments ÷ take-home income | ≤ 35% | Debt burden |
| Non-mortgage debt service | Non-mortgage repayments ÷ take-home income | ≤ 15% | Consumer-debt burden |
| Invested assets to net worth | Invested assets ÷ net worth (incl. home) | ≥ 50% | Whether wealth is working, not just sitting in the home and CPF |
| Wealth in CPF + property | (CPF + home) ÷ net worth | Higher = less liquid | How locked-up their wealth is |

The calculator treats "fixed expenses" as family contribution, bills, tax, loans and insurance by default.
Override this with `fixed_expense_keys` if the client's situation differs.

## Protection targets: Planners Inc guidelines (protection-guides.json)

| Need | Planners Inc guideline (shared by a Planners Inc colleague; adjust to your own) |
|---|---|
| Death, TPD and terminal illness | 12× annual income |
| Critical illness (late stage) | 5× annual income |
| Early critical illness | 3× annual income |
| Disability income | 75% of gross monthly income |
| Emergency cash | single: 3 months · married, no kids: 6 · married, 1 kid: 9 · married, 2+ kids: 12 (12 if income is irregular) |

**These are adjusted for age.** Insurance guards the working years. The death/TPD/TI, CI and early CI multiples
are capped at the number of working years left (the client's own chosen retirement age − age), applied to
current income. A 57-year-old retiring at 65 is measured at 8×, not 12×. A 60-year-old working to 70 is measured at 10×. Disability income stops being targeted within 2 years of retirement. Dependants who
need support past retirement override the cap through the needs-based figure. After retirement, the focus
moves to passive income, health and care, and legacy.

Here, annual income means gross monthly × 12 plus bonus. "Months" means months of spending, excluding committed savings.

the adviser measures cover against the **Planners Inc guidelines**, not the LIA 9×/4×. She sees LIA as the bare minimum,
and the Planners Inc levels give a more comfortable buffer if a catastrophic illness happens. The multiples
are in `protection-guides.json`, covering death/TPD, CI, early CI, personal accident and disability income as a
percentage of income. The calculator reads them from there. Call them "the Planners Inc guideline" in reports.

## Other protection points: MoneySense "Basic Financial Planning Guide"

- **Spend at most 15% of take-home pay on protection.** Bundled products such as whole life can go above
  this because they include savings.
- **Hospital:** MediShield Life covers large bills. An Integrated Shield Plan (IP) adds to it, and should match the
  ward they would actually use. MoneySense notes that about half of IP holders stay in B2/C wards, where
  MediShield Life may be enough. IP premiums rise steeply with age, and above the MediSave withdrawal
  limit they are paid in cash.
- **Long-term care:** CareShield Life covers Singapore citizens and PRs born in 1980 or later. Severe disability means being
  unable to do 3 of the 6 activities of daily living. Supplements raise the payout.
- **DPS** (Dependants' Protection Scheme) gives term cover to 65 on CPF contributors. **HPS** (Home Protection
  Scheme) covers HDB loans paid with CPF. Count both as existing cover.
- **Term insurance** is the most cost-effective way to cover a gap. Locking in premiums while young keeps them lower.

## Planners Inc house guides (from Planners Inc financial reports)

- **Insurance at no more than 10% of income**, unless there are specific circumstances. This is stricter than MoneySense's 15%;
  show both.
- **Six accounts** for restructuring cash flow:
  1. Emergency fund: by household, 3 / 6 / 9 / 12 months (see the table above)
  2. Happiness fund: the bonus, or 1 month of income
  3. Short-term goals (now to ~5 years): FD, T-bills, SSB, high-yield savings
  4. Mid-term goals (~5–15 years): the remaining surplus
  5. Long-term / retirement: at least 10% of income
  6. Insurance: at most 10% of income
- **Analysis style:** the client sees **Good / Not so good / Bad**. Start with genuine strengths
  (responsible, goal-driven, healthy, family-oriented), then what's not ideal, then real problems.

## Needs-based death / TPD (when there are dependants)

Lump sum needed = family's share of monthly spending × 12 × years they need support
+ outstanding debts + goals that are for the dependants (e.g. education)
− liquid assets and investments already there.

The default family share is 70% of current spending; adjust it from the fact-find. Show this beside the
9× figure. Neither one is "the answer". The conversation decides.

## Legacy (MoneySense / My Legacy portal)

Will, CPF nomination (a will does **not** cover CPF), insurance nominations (Insurance Act), Lasting
Power of Attorney, and Advance Care Plan. Without a CPF nomination, CPF goes to the Public Trustee under
intestacy rules. Review nominations after marriage, divorce or children.

# Legacy: who gets what, and how to make it fair

Source: the adviser's *Estate Planning Workshop: Who Gets What When I'm Gone?*, with the legal section presented by
Mr Zamiq Azmeer, Advocate & Solicitor. This is general information to shape the conversation, not legal advice.
Every will, trust, severance or nomination change goes to a lawyer. Verify fees and figures before quoting them.

## The questions to ask

1. **Who should benefit?** Spouse, children (from which marriage?), parents, siblings, a partner, a charity.
2. **Equally, or in different amounts?** Reasons for unequal splits include a child who already got help with a
   home, a child with special needs, a caregiver child, or a business successor.
3. **Does anyone get a specific asset?** For example the home, a second property, the car or the business. What are
   these worth, net of loans, and what about the CPF refund on an HDB flat?
4. **When and how?** A lump sum, or held in trust and released over time (minors, special needs, spendthrifts)?
5. **Who's in charge?** The executor, a guardian for children under 21, and LPA donees with a replacement.
6. **Is there enough cash** to pay debts and costs while the estate is frozen?

## Three rulebooks: a will is only one of them

| What controls it | Assets |
|---|---|
| **The will** (no will → Intestate Succession Act) | Bank accounts, investments, SRS, personal assets, property in sole name or tenancy-in-common, policies with no nomination |
| **Nominations** (outside the will) | CPF (all accounts) by CPF nomination. Life insurance by s.133 revocable or s.132 trust nomination |
| **How it's held** (outside the will) | Property in joint tenancy goes to the surviving joint owner by survivorship. Assets in a trust follow the trust deed |

- **CPF with no nomination** goes to the Public Trustee, is split under intestacy law, takes months, and costs a fee
  (about $900 on $100k, more on larger sums). Nominating is free online.
- **s.133 revocable nomination:** anyone can be named, it can be changed any time, and it's paid outside probate.
  A clearly drafted later will can override it.
- **s.132 trust nomination:** only a spouse and/or children can be named. It's irrevocable without their consent,
  protected from creditors, and overrides the will. Policies from before Sep 2009 may carry an implied trust.
- **Joint tenancy overrides the will.** If the wish is for someone other than the co-owner to get it, they need to
  sever to tenancy-in-common (lawyer). See the 2021 Lim Sze Wei case in the deck.
- **HDB:** the beneficiary must be eligible to own it (SC/PR, HDB rules). The CPF used plus accrued interest must be
  refunded before transfer or sale. That money goes back into the deceased's CPF and then out by CPF nomination,
  so the heir who gets the flat effectively receives value minus loan minus CPF refund.

## No will: Intestate Succession Act 1967 (non-Muslims)

| Who survives | Split |
|---|---|
| Spouse only | Spouse 100% |
| Spouse + children | Spouse 50%, children share 50% equally |
| Children only | Children share equally |
| Spouse + parents (no children) | Spouse 50%, parents 50% |
| Parents only | Parents equally |
| Then siblings, grandparents, uncles and aunts | Then the Government |

Unmarried partners, stepchildren, in-laws, friends and charities get nothing. **Muslims:** Faraid applies under
AMLA, and a wasiat can only pass up to 1/3 to non-heirs. The calculator doesn't model Faraid, so refer these to a lawyer.

Other points from the deck:
- **Marriage revokes an earlier will, but divorce doesn't.**
- A will must be signed in front of 2 witnesses who are present together, and a gift to a witness (or the witness's
  spouse) is void.
- The probate freeze is 3–6 months, or 12–24+ months if contested.

## Making it fair when the assets aren't equal

The calculator (`scripts/legacy_plan.py`) does this:

1. **What's pinned:** each specific gift, valued **net** of its loan and (for HDB) the CPF refund, plus any s.132
   trust nominations.
2. **What can be steered:** the residuary estate, CPF (including refunds flowing back), and revocable policies, minus
   debts and costs.
3. **Fair amount per heir** = their share × (pinned + steerable). Each heir's shortfall is filled from the steerable money.
4. **When one gift is worth more than that heir's fair share of everything**, no split of the rest can balance it.
   The extra needed is `gift ÷ their share − total`. The fix is life insurance nominated to the others (paid
   outside probate, within weeks), or a **deliberately** unequal split written into the will.
5. **Turning it into documents:** use the suggested percentages for the will's residue, the CPF nomination and
   revocable nominations. Or, more simply, point whole channels at one person, e.g. CPF to Amy, cash to Ben.

Singapore has no estate duty (abolished 2008), so the issues are **fairness, liquidity and timing**, not tax.

## Liquidity

Debts, funeral and estate costs, and HDB CPF refunds all come due while sole-name accounts are frozen until the
Grant of Probate. Money that reaches the family quickly comes from nominated CPF, nominated insurance and survivorship.
If the estate's cash can't cover what's due, a nominated policy bridges the gap. Otherwise an asset may have to be sold.

## Trusts (from the deck: worth it for specific goals, not for everyone)

Trusts suit young or vulnerable beneficiaries (release money over time, special needs), adding conditions and
protection, private succession of a business or property, and insurance paired with a standby trust. They cost
more and add complexity. Say honestly when a client doesn't need one.

## The checklist (from the deck's estate health check)

- A valid, up-to-date will
- A CPF nomination
- Knowing how the home is held
- Insurance nominations up to date
- An LPA
- A guardian named for young children
- Enough cash for debts and costs
- The family knowing where the documents are kept

# Start here — opening prompt for a fresh session

Paste this at the top of a new chat. Everything the previous session learned
that still matters is either in the tests or in the documents below.

---

## Say this

> I'm continuing work on PathAhead in this folder. Before doing anything:
> read `START_HERE.md`, `NEXT.md`, `ROADMAP_UI.md` and `ISSUES_v0.2.md`,
> then run the verification commands to confirm the repo is green.
>
> **All eleven university/polytechnic institutions are loaded, `fit scoring`
> reads `complete`, and the UI roadmap U1–U5 is built.** The two items that
> were outstanding on 2026-08-04 are both closed, and the whole suite is
> green:
>
> **Update 2026-08-10: all three stages are in — PSLE, O-Level/SEC, and
> A-Level.** `#/` is now a three-door chooser with a distinct CSS accent per
> track (`data-track`) and navigation scoped to whichever track a family is
> in, plus a compact "Change track" link back to the chooser. `#/olevel`
> scores L1R5 (2027 JAE, legacy O-Level) and L1R4 (2028 PSE, the incoming
> Secondary Education Certificate) via a new third rule kind,
> `required_plus_best_n`, present in both engines with golden fixtures. It
> also scores the ELR2B2 polytechnic route from the same subjects, via a new
> `also_scored_under` mechanism that lets the ~330 polytechnic outcomes
> already loaded for A-Level answer to a SECOND transition rather than being
> duplicated. 16 JC/MI institutions' worth of real cut-off data is loaded from
> MOE SchoolFinder; the 2028 SEC transitions are aggregate-only by design —
> no institution has published a course cut-off under a system that has not
> run its first cohort yet. See `packs/singapore/olevel.yaml`'s header comment
> for exactly what is and is not real data. The DOM suite is **94/96**, not
> 75/77: 19 checks were added (7 for `#/olevel`, 3 for the door/nav redesign,
> plus 9 already-counted PSLE ones carried forward) and the **same two
> failures from before persist**, both in the A-Level profile step, both
> written up in `docs/UI_CHECK_FAILURES_2026-08-09.md`. Read that before you
> assume you broke something.
>
> **Update 2026-08-09: the PSLE stage went in first.** It scores, it resolves
> Posting Groups, `#/psle` was a working second front door, and `lowest_sum`
> exists in both engines with fixtures that exercise it. Secondary schools are
> deliberately not loaded — see `packs/singapore/psle.yaml` for why, and
> `docs/POST_PSLE_AND_PORTAL.md` for the design this came from.
>
> 1. **The DOM suite has been run** (2026-08-05, 66/66). The one failure it
>    found was in the CHECK, not the app: it searched each card's text for
>    the literal "SP", and a card names the institution the way a family
>    says it — "Singapore Polytechnic". Rows now carry `data-course` and the
>    check compares ids against the pack.
> 2. **Polytechnic fees are loaded for four of the five** — NYP, RP, SP and
>    TP, each from its own page. Fee coverage 111 → 266 of 330 courses, and
>    the static site 111 → 265 indexable pages.
>
> **The one open data item is Ngee Ann's fee table.** Its fee page returned
> an empty body on every route tried on 2026-08-05, while its FAQ and
> academic-matters pages fetched normally. All 41 NP courses carry a note
> saying so and pointing at the page. The other four polytechnics publish
> *identical* tuition, which makes filling NP in by inference feel almost
> safe. It is not — their supplementary fees all differ, which is what shows
> these are four separate publications — and a test fails if anyone does it.
> Read the CHANGELOG entry before touching it.
>
> Three rules from earlier sessions that each cost something real:
> **never assert a limitation you have not tested**; **never demo with data
> shaped to pass** — test with input written the way a real person would
> type it; and **when a test fails, find out which side is wrong before
> changing either.** The last one caught two would-be regressions in the
> session that wrote U3.

---

## Verify the repo is green before changing anything

```bash
npm run check:fast                       # golden + filters + flows + static site, ~1s, no jsdom
npm run check:ui                         # the DOM suite — needs jsdom, see the note above
pytest -q                                # 255 tests, across three stages and one engine
python app/cli.py health --gate          # data health, exits non-zero if not shippable
python app/cli.py build --out dist
python app/cli.py build --out web/data    # what the BROWSER loads -- serve does this too
node tools/check_golden.mjs              # Python and browser engines agree — 23 fixtures, three rule kinds
npm install && node tools/check_ui.mjs   # 96 checks, drives the real HTML in a DOM — 94/96, see the update above
```

If all six pass except the two documented DOM failures, the state described below is accurate.

**`web/data/` is what the browser actually loads.** `dist/` is not; the app
never reads it. These drifted once and the whole UI suite went green against an
hour-old bundle that was missing a fix entirely. `check_ui.mjs` now reads the
served bundle and fails if it is older than any pack YAML, but if you are
debugging "my change isn't showing up", this is why.

---

## Where it stands

| | |
|---|---|
| **Courses** | 330 — NTU 46, NP 41, RP 41, TP 41, SIT 40, NYP 39, SP 34, NUS 21, SUSS 12, SMU 10, SUTD 5 |
| **Polytechnic GPAs** | 44 (the diploma-holder route *into* a degree — not the same thing as the polytechnic courses now in the pack) |
| **Fees** | **266 of 330** — NUS, NTU (4 bands), SMU (2 bands), SIT, and four polytechnics (NYP, RP, SP, TP). SIT is charged **per credit unit**, not per year, and is modelled that way rather than divided into a fake annual figure. The four polytechnics publish identical tuition — SGD 3,100 citizen — from four separate pages, and each cites its own. **Missing: NP (41, page unreachable), SUSS (12), SUTD (5), SIT (4), NTU (2)** |
| **Salary / employment** | 12 courses with a salary range (GES via data.gov.sg) plus 30 SIT courses with an employment rate. SIT's bare median is deliberately not shown |
| **Fit scoring** | **complete** as of 2026-08-03 — all eleven institutions loaded, so the PREVIEW gate is down. Re-read SAFEGUARDS.md 5.1 before anything shortlist-shaped is built on top of it |
| **Evidence axis** | Three published shapes: percentile bands (NUS, NTU, SMU), banded profiles (SIT, SUSS) and full admitted min-max ranges (NYP, NP, SP, TP, RP). SUTD publishes none and says so; so does SP for one course |
| **Institutions** | **11 of 11.** Nothing is missing from the pool any more |
| **Citations** | Every figure links to the page it came from. `Fact.url` holds the exact page where that is narrower than the source's own URL — SP's 33 bands each cite their own course page — and falls back to the source URL otherwise, which is the common case. All **1,055** outcome facts resolve to a link |
| **Interface** | ROADMAP_UI **U1–U5 built**: hash router and nav, the course/university/fees pages, filter-search-density, a 342-page static site (**265 indexable**, up from 111), and `#/explore`, `#/results-day`, `#/perspectives`. U3's DOM wiring is verified as of 2026-08-05 |
| **Tests** | 255 Python + 23 cross-engine fixtures (three rule kinds: `weighted_best_n_with_substitution`, `lowest_sum`, `required_plus_best_n`) + 40 DOM-free checks (filters 15, flows 10, static site 18, `check_boot`) + 96 DOM checks in `check_ui.mjs` (94 passing, 2 documented pre-existing failures) |

---

## What to read, in order

1. **`NEXT.md`** — the work queue, with verified URLs and data shapes. Start at §4.
2. **`ISSUES_v0.2.md`** — what was broken and why. §A, §B, §C, §D, §E and §G
   are fixed, and §F and §H are largely so. What is left there is cosmetic:
   §G4 and §G5 are PDF rendering artefacts (list bullets, native select
   arrows), and §H's sort/filter by salary or employment rate is deliberately
   unbuilt — see SAFEGUARDS.md 5.1 on why those are never sort keys.
3. **`ROADMAP_UI.md`** — the multi-page redesign. **Do not start this until the
   data work in NEXT.md is done**; the gate is written into the document.
4. **`BACKLOG.md`** — things considered and deliberately not scheduled, with
   the reasoning. Read it before proposing one of them again. B1 (an LLM/SLM to
   interpret the free-text goal field) is the substantial one.
5. **`SAFEGUARDS.md`** — the rules that must not be broken. Every one has a
   failing test behind it.

---

## Mistakes worth not repeating

**"PDFs can't be parsed."** Asserted without trying. `web_fetch` handles them
fine — the NTU grade-profile PDF came back as a clean table on the first
attempt. If you catch yourself declaring a limitation, test it first.

**A demo profile that used subject codes spelled exactly as the data file
spells them.** It scored 81 and looked wonderful. A real student clicking
"Further Mathematics" in the app's own dropdown scored 24, because matching was
exact-string. That reached a child, who read twenty-one "weak match" verdicts as
a judgement about herself.

**A sensible default is still an assertion.** Loading the NTU fees needed a
duration per course, and four years is the obvious answer. NTU's Academic
Handbook says Accountancy and Business are three. Nothing would have flagged
the guess — the tests only check that a duration is plausible, and four is
plausible. Look the number up even when you are confident, especially when it
multiplies a fee.

**A course taught in Chinese, recommended to a student who does not read
Chinese.** Reported from real use, 2026-08-03. Ngee Ann's Diploma in Chinese
Studies ranked **second of 296** at 67/100, every point of it from generic
overlap — *"you work best through exams"*. The pack held a rich editorial
description of the course and no record that it requires Chinese or that half
of it is taught in Chinese.

Three lessons, and the third is the general one:

1. **A fit score answers "how well does this suit you". It cannot answer "are
   you eligible", and it must not be asked to.** Eligibility is now checked
   before preference and produces no score at all — because a *low* score is
   still a ranking, and would have put the course above hundreds of others.
2. **The absence of a constraint is not the same as its absence in reality.**
   Nothing flagged the gap. Every test passed. The pack simply did not know.
3. **Rich editorial data made the hole invisible.** The course had interests,
   subjects, sectors, a summary — everything the scorer needed to feel
   confident. Completeness of the fields you happen to have says nothing about
   the fields you never thought to add.

`tests/test_fit_calibration.py` exists because of these. It tests whether the
output is *meaningful*, not whether the machinery is consistent — 128 tests
passed on the version that told a child she was a weak match for everything.
Add to that file whenever you touch scoring.

---

## Model choice

Most of what remains is mechanical: transcribing fee tables, threading a field
through model → loader → bundle → UI, writing tests to an established pattern.
A fast model handles that well, and the guardrails above make it low-risk.

Escalate for decisions about **meaning**: the SUTD/SIT/SUSS band type in
`NEXT.md` §2 is one, because the tempting move — flattening banded percentages
into a fake 10th/90th percentile — would look tidier and would be a lie.

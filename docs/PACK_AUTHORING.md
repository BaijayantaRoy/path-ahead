# Writing and fixing a data pack

**The engine is the easy part. The data is the project.**

A pack is plain YAML. Nothing in it executes. It is meant to be readable — and
correctable — by a teacher or counsellor who does not write code, because those
are the people most likely to spot a wrong figure.

---

## Fixing one number (the most valuable contribution there is)

1. Find the file under `packs/<country>/`. Cut-off points and grade profiles
   live in `outcomes.yaml`; formulas live in `transitions.yaml`.
2. Change the value **and** the fields that travel with it:

```yaml
band:
  p10: "AAA/B"
  p90: "AAA/A"
  p10_points: 60          # the three H2 grades converted on the H2 scale
  p90_points: 60
  basis: 3 H2 grades, out of 60
  fact:
    value: "AAA/B to AAA/A"
    as_of_year: 2026            # <- the year the figure DESCRIBES
    source: nus-igp-2027        # <- must exist in pack.yaml sources
    confidence: high            # high | medium | low
    stale_after: 2028-01-31     # <- when it stops being current
```

3. Bump `pack.version` in `pack.yaml`.
4. Run the gate:

```bash
pathahead health --gate --pack packs/singapore
```

That is the whole workflow. If the gate is green, open a pull request.

### The four fields that are not optional

| Field | Why it exists |
|---|---|
| `as_of_year` | The year the figure describes, not the year you found it. A 2025 profile published in January 2026 is `2025`. |
| `source` | An id from the `sources:` block. A fact citing an undeclared source fails to load. |
| `confidence` | `high` = the primary official publication. `medium` = a reputable secondary source. `low` = inferred. The release floor is `medium`; `low` fails the gate. |
| `stale_after` | Usually the next publication cycle. Past this date the app greys the figure out and links to the official page — it never quietly shows it as current. |

---

## Sources and licences

Every source declares a licence, so obligations travel with the data and the
attribution block is generated rather than hand-maintained.

```yaml
sources:
  - id: nus-igp-2026
    name: Indicative Grade Profile
    publisher: NUS Office of Admissions
    url: https://www.nus.edu.sg/oam/admissions/indicative-grade-profile
    retrieved: 2026-08-02
    licence: institution-tou
    note: >
      What was on the page, and anything a future maintainer needs to know.
```

| Licence id | Meaning | You may |
|---|---|---|
| `sg-odl-1.0` | Singapore Open Data Licence v1.0 | Redistribute and modify, **with conspicuous attribution and a link to the licence**, and without implying official status |
| `moe-tou` | MOE Terms of Use | Cite and link. **Do not** reproduce text, tables or documents, and do not reuse commercially |
| `institution-tou` | A university or school's own terms | Cite and link |
| `derived` | Computed by PathAhead from cited sources | Redistribute, with the derivation documented |

**The rule that keeps this safe: encode facts, never prose.** A cut-off point, a
grade-point value and a formula are facts, and facts are not what copyright
protects. The explanatory wording, the table as laid out, the PDF — those
belong to the publisher. Record the figure, write your own sentence, and link
to the original. Prefer `data.gov.sg` where the same figure is available there,
because its licence is clean.

Never scrape in bulk. Never mirror. See [SAFEGUARDS.md §3](../SAFEGUARDS.md).

---

## Adding a whole country

The generic engine needs **zero new code**. The deliverable is the pack.

```
packs/<country>/
├── pack.yaml           metadata + sources + attribution
├── stages.yaml         the exams
├── cohorts.yaml        "what year is the child in" -> which rulebook
├── transitions.yaml    the scoring rules, dated and versioned
├── outcomes.yaml       destinations, with their published bands
├── routes.yaml         how you get there (>= 3 per destination, see below)
└── prerequisites.yaml  subject dependencies
```

### The order to write them in

1. **Stages.** What exams exist, who runs them, at what age.
2. **Cohorts.** Map each school year to a stage, an exam year and an admission
   year. Get this right first — everything indexes off it, and it is the one
   question a family can actually answer.
3. **Transitions.** Pick a rule kind (below), supply parameters and scales, date
   it, cite it. Add `caveats` for anything a user must be told.
4. **Outcomes.** Destinations with their published bands. Add `overlays` for
   interviews, portfolios, tests and subject requirements — these must never be
   silently dropped.
5. **Routes.** At least three per destination group, at least one non-direct.
   **The engine enforces this**; see below.
6. **Prerequisites.** Subject dependencies, especially ones decided years
   earlier.

### Choosing a rule kind

| Kind | Shape | Example |
|---|---|---|
| `weighted_best_n_with_substitution` | best N + compulsory + best-of bonus, capped, higher is better | Singapore A-Level UAS (70) |
| `lowest_sum` | sum every required subject, lower is better | PSLE (AL1–AL8, 4–32) |
| `required_plus_best_n` | one compulsory + best N groups, lower is better | L1R5, L1R4, ELR2B2 |

If none fits, write a new one — `engine/rules/<kind>.py`, registered in
`engine/rules/__init__.py`. Two requirements:

- **It must emit a trace**, not just a value. Every step a human would write on
  paper is a `Step`. This is the contract, and it is what makes a wrong pack
  visibly wrong.
- **It must be pure.** No clock, no network, no globals. That is what lets
  golden fixtures pin it and lets the browser engine mirror it.

Then mirror it in `web/index.html` (in the block marked `engine:`) and add
fixtures — CI will fail until both agree.

### Why routes are mandatory

`engine/backward.py` sets `MIN_ROUTES = 3` and refuses to return a plan with
fewer, or with no non-direct route. A single required score delivered on its
own to a teenager is a verdict, not guidance.

Every education system has these routes; they are just rarely written down.
Look for: a vocational-to-degree ladder, an aptitude or portfolio-based
admission scheme, an equivalent programme at a different institution, and a
retake, appeal or later-entry path. If you genuinely cannot find three, the
pack says so honestly and the app points the user at a counsellor.

---

## Before you open a pull request

```bash
pathahead health --gate --pack packs/<country>   # must exit 0
pytest -q                                        # engine + safeguards
python tools/make_golden.py && node tools/check_golden.mjs   # both engines agree
```

Review checklist — the same one the pack copilot's output must pass:

- [ ] Every fact has `as_of_year`, `source`, `confidence`, `stale_after`
- [ ] Every source has a working URL, a retrieval date and a licence id
- [ ] `direction` matches reality (is lower better, or higher?)
- [ ] Stage and year-level names match what local families actually say
- [ ] Interviews, portfolios and tests are recorded as overlays
- [ ] At least three routes per destination group, one of them non-direct
- [ ] No publisher's prose, tables or documents copied into the pack
- [ ] Attribution block names every licence that requires one
- [ ] Golden fixtures added for any new rule kind, and reviewed in the diff

---

## A note on the AI copilot

`tools/pack_copilot.py` (planned) will draft a pack from a country's official
documents, with every extracted number linked to its page and flagged for
confidence. It is a **maintainer tool**. It never ships inside the user app, and
its output is a draft pull request that a human signs off against the checklist
above — never a live data path.

It is the one component in the whole system capable of inventing a figure,
which is exactly why it is kept furthest from the user.

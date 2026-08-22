# Contributing to PathAhead

Two kinds of contribution matter here, and the first one needs no code at all.

---

## If you teach, tutor, counsel, or have been through this as a parent

**You are the most valuable contributor this project has.** The engine is
arithmetic; the data is where this is right or wrong, and you are the person
who would notice.

- **Correct a figure.** Every number in the app has a report link that opens a
  pre-filled issue. Wrong cut-off, wrong year, wrong grade point — please say
  so. This is the single most useful thing anyone can do here.
- **Add the routes we are missing.** `packs/singapore/routes.yaml` lists five
  ways into a university course. There are more, and the people who know them
  are counsellors, not developers. A route we do not list is a door a student
  never sees.
- **Fix the wording.** If a sentence would land badly on a seventeen-year-old
  reading it alone at midnight, that is a bug. Open an issue quoting the exact
  sentence — no code needed.
- **Extend a stage.** PSLE, O-Level/SEC and A-Level are all authored now, but
  coverage is not total — 3 of ~19 JAE-entry JCs have no cited grade range
  yet, and per-programme subject prerequisites are PDFs that change every
  year. Someone who works with these exams every year will catch a gap or a
  stale figure far faster than someone reading circulars from scratch.

See [docs/PACK_AUTHORING.md](docs/PACK_AUTHORING.md). The files are plain YAML
with comments, and a wrong pack fails the build before it can reach anyone.

---

## If you write code

```bash
git clone https://github.com/BaijayantaRoy/path-ahead && cd path-ahead
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

pytest -q                                          # 300+ tests, under a few seconds
ruff check .
python app/cli.py health --gate                    # the data gate
python tools/make_golden.py && node tools/check_golden.mjs   # both engines agree
python app/cli.py serve                            # the app itself
```

### The seams

| I want to... | Change |
|---|---|
| Fix or add data | `packs/<country>/*.yaml` — no code |
| Add a scoring formula shape | `engine/rules/<kind>.py` + mirror in `web/index.html` + golden fixtures |
| Add a country | A new pack directory. The engine needs nothing |
| Change the UI | `web/index.html` — one self-contained file, no build step |
| Change explanations | `engine/explain.py` (Tier 0) — no model involved |

### Rules that are not negotiable

These are safeguards with tests behind them. A pull request that weakens one
will fail CI, and the test failure is the review comment.

1. **No number without provenance.** Every `Fact` carries `as_of_year`,
   `source`, `confidence` and `stale_after`. The loader refuses a pack that
   breaks this.
2. **Every score carries a trace.** A rule kind that returns a value without
   steps is not finished. The trace is the product.
3. **`MIN_ROUTES = 3.`** Backward mode never returns a lone required score.
   See `tests/test_safeguards.py`.
4. **No identity fields, ever.** No name, NRIC, email, school, account. No
   analytics, no telemetry, no third-party scripts. CI greps for all of them.
5. **No verdict language.** A banned-phrase list is checked against every
   string the engine can emit. Add to it rather than working around it.
6. **Never sort by selectivity.** Results are alphabetical. Tested.
7. **The AI never produces a number.** Anything narrated must pass
   `engine/guardrail.py`. Adversarial cases run in CI.
8. **Both engines must agree.** Golden fixtures are replayed through Python and
   JavaScript. A changed fixture means a real family's answer moved — commit it
   deliberately, and say why in the pull request.

### Style

Ruff handles formatting concerns. Beyond that: **comments explain why, not
what.** A comment that says a safeguard exists and what it prevents is worth
five that restate the code. The reader we are writing for is a maintainer two
years from now trying to work out whether a rule is load-bearing.

Plain English in user-facing strings. British spelling, Singapore terminology
("Junior College", "polytechnic", "Mother Tongue"), and a reading level a
worried parent can manage at midnight.

---

## Reporting a problem

- **A wrong number** → open an issue with the figure, the correct value, and
  the official page you found it on. This is the highest-value report.
- **Wording that would hurt someone** → quote the sentence. Treated as a bug.
- **A security or privacy concern** → open an issue; if it involves user data
  exposure, say so in the title and it will be triaged first.

---

## What this project will not accept

- Anything that adds analytics, telemetry, accounts, or an identity field.
- Ranking or league-table features, or sorting by selectivity.
- Predicted probabilities of admission. The publishers do not provide the data
  for it, and a confident-looking percentage would be the most harmful thing
  this tool could show.
- Advertising, sponsored placement, or paid tiers. Beyond the ethics, staying
  non-commercial is what keeps the project on the right side of the source
  terms recorded in [SAFEGUARDS.md](SAFEGUARDS.md).
- Bulk scraping or republication of official data.

---

By contributing you agree your work is licensed under the [MIT Licence](LICENSE),
and that any data you add complies with its source's terms as recorded in the
pack's `sources:` block.

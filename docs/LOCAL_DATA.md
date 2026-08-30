# Local-only data overlays

> **Nothing in this document is legal advice, and nothing in it grants you a
> right to use anyone's data.** It explains a technical facility and the
> reasoning behind it. Whether you may lawfully hold a particular copy of a
> particular dataset, in your jurisdiction, for your purpose, is your
> decision and your responsibility — not this project's.

---

## What PathAhead publishes, and what it does not

PathAhead ships every figure it is free to ship, cited to its publisher, with
its retrieval date and its licence attached. That covers most of the pack.

It does **not** ship Posting Group cut-off points for individual secondary
schools.

Those figures are MOE's. MOE publishes them on each school's own page in
[SchoolFinder](https://www.moe.gov.sg/schoolfinder), and MOE's
[Terms of Use](https://www.moe.gov.sg/terms-of-use) reserve the right to
reproduce material from their site. Anyone may read the figures; that is a
different thing from this project being free to copy a few hundred of them
into a public repository and redistribute them under an MIT licence. A
compiled table of every school's cut-off is also somebody's compilation,
whoever did the compiling.

There is a fair-dealing argument available — the numbers are facts, facts are
not what copyright protects, the use is non-commercial and arguably
transformative. It is a decent argument. It has not been tested, and this
project is not the right vehicle for testing it, because the people who would
bear the consequence of it being wrong are families using a free tool.

**So the published build carries none of those figures, and the app links each
school to its own SchoolFinder page instead.** You read the official number at
source: current, in MOE's framing, with MOE's caveats attached. That is also
strictly better as a product — a copied snapshot starts going stale the moment
the next posting exercise runs, and this one never can.

---

## The overlay facility

An individual may still hold their own copy of figures they have gathered, for
their own private study. If you do, PathAhead will use it.

Create:

```
packs/singapore/local/cutoff.json
```

```json
{
  "admiralty-secondary-school": {
    "years": {
      "2025": { "pg3": [16, 22], "pg2": [21, 25], "pg1": [25, 29], "ip": null }
    }
  },
  "anderson-secondary-school": {
    "years": {
      "2025": { "pg3": [9, 11], "pg2": null, "pg1": null, "ip": null }
    },
    "note": "Optional, shown on the school's card."
  }
}
```

- Keys are school ids exactly as they appear in
  `packs/singapore/secondary-schools.yaml`. A typo fails the load loudly
  rather than silently dropping a school.
- **The schema is keyed by year**, because that is the only thing a refresh
  of this file can honestly hold: MOE's SchoolFinder never shows more than
  the current admissions cycle per school, and there is no archive to
  backfill from (checked 2026-08-30 -- no earlier SchoolFinder snapshot
  exists anywhere reachable from MOE itself). A REAL multi-year trend from
  *your own* copy is built the only honest way there is: run this same
  refresh again next admissions cycle and add that year alongside the ones
  already here, never replacing them. `engine/loader.py:_cutoff_trend`
  computes mean, median and a plain-language direction from however many
  years are actually present -- one today, more as this file is kept up to
  date over time.
  (Separately, PathAhead *does* now cite one already-public, independently
  spot-checked third-party multi-year compilation -- see "Third-party public
  trend citation" below. That is a different mechanism from this local
  overlay, kept deliberately apart from it.)
- Each band is `[first_posted, last_posted]` -- the PSLE Score of the first
  and the last student posted to that Posting Group. The reach filter, and
  the trend, both read the second number, the cut-off proper.
- `null` for a Posting Group the school does not offer or does not publish
  in a given year. A missing band is treated as *unknown*, never as *out of
  reach*.
- Optional `"note": "..."` per school (not per year), shown on that
  school's card.

Then rebuild the pack:

```bash
python app/cli.py build --out web/data
```

### What changes when it is present

- School cards show your figures, labelled **"From your own local copy (not
  published by PathAhead)"**, alongside the SchoolFinder link so you can check
  them against the source.
- The "only schools within reach of your PSLE score" filter appears. Without
  an overlay it is not rendered at all, because there would be nothing for it
  to compare against.
- `pack.local_overlay_applied` becomes `True`.

### What does not change

- The shortlist is still never ranked or sorted by cut-off
  ([SAFEGUARDS.md](../SAFEGUARDS.md) §5.1). Reach is a filter. It narrows what
  is shown; it never reorders what remains.
- A school with no figure in your file still shows, marked *unable to be
  judged*. Absence of data never becomes a negative signal.

---

## Why it cannot be committed by accident

Three independent mechanisms, because one is a habit and three is a design:

1. **`.gitignore` covers `packs/*/local/`** and every sibling pattern, so the
   file is invisible to `git add -A`.
2. **The overlay is applied at pack *load* time, not at pack *build* time**
   (`engine/loader.py:_apply_local_overlays`). `secondary-schools.yaml` is a
   tracked file; anything written into it can be committed. The overlay's
   figures exist only in memory, and memory cannot be pushed.
3. **CI fails on any tracked pack containing cut-off figures**, and on any
   committed file under `packs/*/local/`. See `.github/workflows/ci.yml`.

The compiled bundles (`dist/`, `web/data/`) are gitignored too, and CI rebuilds
them from the tracked YAML — so a release artifact built by CI cannot contain
overlay data even if the machine that pushed had an overlay.

---

## If you are thinking of publishing a fork with data included

Don't do it on the strength of this document. Two things worth knowing first:

- **Ask instead.** MOE's Terms of Use describe a permission process. A free,
  non-commercial, open-source tool that deep-links back to the official source
  is a sympathetic request, and written permission converts the whole question
  from an argument into a fact. This is the recommended path, and it costs an
  email.
- **Attribution is not a licence.** Crediting a source does not grant you the
  right to copy it. Nor does "it was already public", "it is only facts", or
  "someone else published a table of it first".

If you obtain permission, the overlay format above is the supported way to load
the data, and `engine/model.py:KNOWN_LICENCES` is where a new licence id
belongs so that the obligation travels with the data.

---

## Third-party public trend citation

`packs/singapore/cutoff-trend-public.yaml` is a **different mechanism** from
the local overlay above, and it is worth being precise about why, because the
two look similar (both end up rendering a year-on-year cut-off table on a
school's card) while being governed by opposite rules.

|  | `packs/singapore/local/cutoff.json` | `packs/singapore/cutoff-trend-public.yaml` |
|---|---|---|
| What it holds | **MOE's own** per-school figures | A third party's own **already-public** compilation of the same kind of figure |
| Whose licence applies | MOE's Terms of Use (reproduction reserved) | The third party's own site is the publisher; PathAhead cites it, it does not scrape or re-derive MOE's figures itself |
| Tracked in git? | **No** -- `.gitignore`'d, never committed | **Yes** -- committed, ships in every build |
| Verified how? | By you, personally, against your own source | Spot-checked by this project against live MOE SchoolFinder pages before being trusted (below) |
| Shown as | "From your own local copy" | A separately-boxed table with its own inline attribution, url and disclaimer |

The source is [SG School Kaki](https://sgschoolkaki.com/psle-trends), an
unofficial, community-compiled site (not MOE, not PathAhead) — fetched
2026-08-30. Before this file was written, the single "cut-off" figure the site
publishes per school per year was cross-checked against four schools' live
MOE SchoolFinder pages (Admiralty, Assumption English, Outram, Crescent
Girls' — chosen for different profiles: a girls' school with no PG1, a
school with a large single-year swing, an SAP-adjacent school, and an
otherwise-average one). All four matched exactly, confirming the site's
number is each school's **PG3 upper bound** — the historic single
"cut-off point" quoted before Singapore split posting into PG1/PG2/PG3 bands.
The earlier years (2021-2024) could not be independently verified the same
way, because no official multi-year archive exists to check them against; the
in-app disclaimer says so.

139 of the pack's 147 schools matched a site row by (normalized) name. The 8
that did not are exactly the specialised-admission schools that carry no
PSLE-score cut-off at all (School of the Arts, NUS High, Singapore Sports
School, and the rest of that set) — a consistency check, not a gap. 2
site rows had no match in the pack (Fajar Secondary, Teck Whye Secondary),
which appear to have since closed or merged.

This file is deliberately tracked and published, unlike the local overlay,
because it is not a reproduction of MOE's own SchoolFinder page — it is
citation of a third party's own already-public compilation, carried through
to the UI with its own attribution and disclaimer, the same way any other
secondary source in this pack is cited. See the file's own header comment,
`engine/model.py`'s `cutoff_public_trend_source` field comment, and
`engine/loader.py:_apply_public_cutoff_trend` for the mechanics.

---

## Related

- [SAFEGUARDS.md](../SAFEGUARDS.md) §3 — the per-source licensing posture
- `tools/build_secondary_schools_pack.py` — the build, and why it writes nulls
- `engine/loader.py:_apply_local_overlays` — the merge, and why it is here
- `engine/school_fit.py:within_reach` — the filter, and why absence is never a no
- `packs/singapore/cutoff-trend-public.yaml` — the third-party public trend citation, its own header comment
- `engine/loader.py:_apply_public_cutoff_trend` — how that citation is validated and computed

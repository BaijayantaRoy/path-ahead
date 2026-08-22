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
  "admiralty-secondary-school": { "pg3": [16, 22], "pg2": [21, 25], "pg1": [25, 29], "ip": null },
  "anderson-secondary-school":  { "pg3": [9, 11],  "pg2": null,     "pg1": null,     "ip": null }
}
```

- Keys are school ids exactly as they appear in
  `packs/singapore/secondary-schools.yaml`. A typo fails the load loudly
  rather than silently dropping a school.
- Each band is `[first_posted, last_posted]` — the PSLE Score of the first and
  the last student posted to that Posting Group. The reach filter reads the
  second number, the cut-off proper.
- `null` for a Posting Group the school does not offer or does not publish.
  A missing band is treated as *unknown*, never as *out of reach*.
- Optional `"note": "..."` per school, shown on that school's card.

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

## Related

- [SAFEGUARDS.md](../SAFEGUARDS.md) §3 — the per-source licensing posture
- `tools/build_secondary_schools_pack.py` — the build, and why it writes nulls
- `engine/loader.py:_apply_local_overlays` — the merge, and why it is here
- `engine/school_fit.py:within_reach` — the filter, and why absence is never a no

## What this changes and why

<!-- One or two sentences. If this fixes an issue, write "Closes #123". -->

## Checklist

- [ ] `ruff check .` passes
- [ ] `pytest -q` passes
- [ ] If a scoring formula or fact shape changed: `python tools/make_golden.py && node tools/check_golden.mjs` — both engines still agree, and I reviewed the fixture diff (a changed fixture means a real family's answer moved)
- [ ] If the UI changed: `npm run check` (includes `check:web`, the DOM checks, and the static-site checks)
- [ ] If I added or edited a fact: it carries `as_of_year`, `source`, `confidence` and `stale_after`, and the source is declared in a `sources:` block with a real, dated URL
- [ ] I did not add analytics, telemetry, an account, an identity field, a ranking/league-table sort, or a predicted admission probability — see [CONTRIBUTING.md § What this project will not accept](../CONTRIBUTING.md#what-this-project-will-not-accept)
- [ ] If this touches `packs/*/local/` or cut-off figures: I did not add anything there to the tracked YAML — see [docs/LOCAL_DATA.md](../docs/LOCAL_DATA.md)

## Anything a reviewer should know

<!-- Trade-offs, things you're unsure about, or context that isn't obvious from the diff. -->

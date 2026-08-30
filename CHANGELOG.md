# Changelog

All notable changes to PathAhead. Data pack releases are versioned separately
from the app (`sg-2026.1`), because a corrected figure should not need a code
release.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.1.1] — 2026-08-30

### Fixed — text going invisible in Evening Mode on the PSLE, O-Level and A-Level pages

Reported by a parent as "some fonts are not visible in dark mode in a few screens." The two dark states in the app are independent: the OS `prefers-color-scheme:dark` setting, and the in-app Evening Mode toggle (`data-theme="evening"`, which also applies automatically by the clock). Each track page additionally sets its own accent colour (`data-track="psle|olevel|alevel"`). The track rule carried no light/dark condition of its own, so it always won the cascade over `[data-theme="evening"]`'s dark values — silently reverting `--brand`, `--brand-deep`, `--brand-soft`, `--brand-ink` and `--focus` to their light-mode numbers while `--paper`/`--card`/`--ink` correctly went dark. Every plain link, section eyebrow, disclosure arrow and highlighted-row background (anything using those five variables) then rendered as dark-on-dark. OS dark mode was unaffected — only the manual toggle, which is what most people mean by "dark mode."

Fixed with three explicit `[data-theme="evening"][data-track="…"]` rules restoring the same values already used (and already contrast-proven) for OS dark mode on each track. Confirmed with an automated sweep that walks every route in the app across light/OS-dark/Evening Mode and measures rendered text-vs-background contrast: 40 flagged instances before the fix, 0 after, re-verified visually on all three track pages. Also tightened `.pf-step span` (the choice-flow and tie-break diagram captions) from `--ink-3` to `--ink-2`, after the same sweep caught it measuring 4.35-4.44:1 against its tinted `.risk`/`.good` backgrounds — just under the 4.5:1 floor.

## [1.1.0] — 2026-08-29

### Added — "How your six school choices actually decide a place": the S1 posting mechanism, explained and made concrete

Until now `psle.yaml`'s `transitions[].rule_params.posting` (`primary_criterion`, `tie_breakers`, `address_effect`) was sourced but never rendered anywhere in the app — a parent who searched the PSLE page for how the six choices actually get processed found nothing, despite how much a wrong choice order can cost. New card on the PSLE page:

- A worked example (invented Schools A-G, an invented score) shown as two complete, parallel six-row lists side by side (`psleWorkedExampleCompare()` / `psleExampleListTable()`) — identical for Choices 1-5, differing only at Choice 6 — rather than one merged seven-row table. An early merged version read the run of early "No"s as the family's own mistake, when the actual point is the opposite: choices that do not clear cost nothing.
- A picture of the general rule (`psleChoiceFlowDiagram()`): one child's own six choices, checked in order, falling through to the nearest school by registered address only if none of the six held.
- A "When two children are tied on score" section: the three MOE tie-breakers as three steps (`psleTieBreakerSteps()`); a concrete Family 1 / Family 2 / School H example at the one point this actually matters — a school's published cut-off equal to the score you are checking it against, not comfortably below it (`psleTieDiagram()`, `psleTieExample()`); and those same three steps walked through again with the two families' actual ranks filled in, the deciding step (Choice order) visually marked apart from the other two (`psleTieBreakerApplied()`).
- Two callout styles pulled out of the ordinary note stack so the single most load-bearing sentence in each half of the card does not read as just one more box among several: `.psle-insight` (solid, high-contrast, for the one-sentence mechanism finding) and `.psle-practical` (a labelled "Practical difference" chip, for the one piece of advice worth acting on).

The mechanism itself was corrected mid-development after a parent using PathAhead pushed back hard on an early draft, which had implied a school's Choice-1 applicants are seated before its Choice-2 applicants are even considered — rank first, score second. Re-checked against MOE's own tie-breaker worked example (a Choice-1 and a Choice-2 applicant with the *identical* score, compared directly for the same last seat) confirms the opposite: a school's places go to whichever of its applicants have the strongest PSLE Score, however each of them ranked it; choice order is a tie-breaker only between applicants tied on score, and otherwise only decides which of the schools a child's score clears, the child is actually sent to. `psle.yaml` gained a fifth caveat recording the correction, dated and sourced, with a comment for the next maintainer explaining why.

### Added — rank your own six choices, on the PSLE school shortlist

A "Your six choices" panel (`renderPsleChoices()`) next to the school shortlist: a "Choice order" picker on every school card (`psleChoicePicker()`) lets a family assign ranks 1-6 to schools from their own filtered shortlist, one school per rank. The panel shows all six slots filled or empty, flags a rank held by a school that no longer reads as in-reach once the family's search narrows (gated on at least one school actually having a judged reach — never fires on merely-unknown reach), and reminds the family if fewer than six ranks are set. Printable: the picker becomes a plain "Choice N" line on paper rather than a dead `<select>`. Still a record of the family's own choices, never a suggestion or a ranking PathAhead makes on their behalf (SAFEGUARDS.md 5.1).

### Added — PSLE key dates, as a timeline

Four new milestones in `milestones.yaml` — oral exams, written exams, results released, S1 posting results — each with a per-year note on how much the date has moved historically and a live source link, rendered as a visual calendar strip (`psleCalendarStrip()`): four points positioned by real elapsed time between the first and last milestone, with a "Today" marker when today falls within that span, and the exact date under each dot.

### Fixed — key-dates calendar dots clipping their own month/day text

`.psle-cal`'s fixed height was shorter than its actual content (dot + label + date), and `.psle-cal-wrap`'s `overflow-x:auto` was silently forcing `overflow-y` to clip too, per the CSS overflow spec, even though `overflow-y` was never itself set to anything but the default. The date under every milestone was invisible. Fixed by sizing the box to its content and giving the scroll wrapper top padding, rather than by removing the horizontal scroll needed on narrow screens.

### Added — an explicit AL-score search on the PSLE school shortlist, one score or a range, 2026-08-29

The reach filter used to be implicit: it only ever compared the school shortlist against whatever was typed into "If you have the score" (the Posting Group calculator further up the page), so browsing the shortlist against a hypothetical or estimated score meant either reusing that field for two purposes at once or having no way to explore a score you don't actually have yet.

"Search schools by AL score" is now its own control, entirely independent of the calculator, with two modes:

- **Upper bound** — one AL score. Functionally identical to the old reach filter (a "Use the `N` entered above" button offers the one deliberate bridge back to the calculator's value, on a click, never automatically).
- **Range** — a best-case and a worst-case AL score, for a family working from an estimate (a mock exam, a teacher's guess) rather than a result.

`engine/school_fit.py:combined_reach()` (mirrored exactly by `web/src/app.js:combinedReach()`) checks both ends of the range and answers one of four states — `in-reach` (in reach even at the worse end), `possible` (in reach only near the better end — a caller must label this as depending on the best case, never as a plain match), `out-of-reach` (the one state the shortlist filter actually hides on), or `unknown` (no cut-off published, or a score fell outside the Posting Group table — shown, never hidden, same as `within_reach()`'s own `None`). An upper-bound search is the one-point degenerate case (`lo_score == hi_score`), not a second code path, so it can never quietly drift from `within_reach()`.

Still a FILTER, never a score or a sort key (SAFEGUARDS.md 5.1): nothing here reorders the shortlist, and "possible" is an honest caveat on a visible card, not a number. Six new golden fixtures (`combined_reach_cases` in `evals/golden/rules.json`) and 7 new direct unit tests (`tests/test_school_fit.py`) cover all four states, the margin, and the degenerate-range identity against `within_reach()`.

### Added — a hover title on every button, chip, toggle, dropdown and nav link, site-wide, 2026-08-29

Every interactive control across the app — the main navigation and the "Everything else" list (built from the same `ROUTES` table, each entry now carrying a one-line `desc`), every filter chip and tri-state toggle on the PSLE school shortlist (including the new AL-score search above), the A-Level profile builder's interest/priority/stream/constraint chips, the course filter dropdowns, the O-Level cohort and subject-removal controls, the Two-of-you perspective questions, and the header/footer's logo, theme toggle and links — now carries a `title` attribute explaining what it does or means, shown by the browser on hover. Applied to `web/src/app.js` and `web/src/body.html` alike, so it reaches both the in-app views and the static shell, and therefore the GitHub Pages build too (rebuilt into `web/index.html` via `tools/build_web.py`).

Titles were written to add information the visible label doesn't already give — what a toggle does, what a link leads to, what a figure means — rather than just repeating the button's own text back at it. `npm run check:ui` (116/116) and the golden cross-engine suite were re-run after the sweep; nothing in the DOM structure or button text changed, only the added attribute.

## [1.0.0] — 2026-08-19

First public release. All three stages of Singapore's education system are
built and verified: PSLE → secondary school, O-Level/SEC → JC/MI/polytechnic,
and A-Level → university, with 815 cited facts across 68 sources.

Everything below this heading is the development history that produced 1.0.0,
kept in full rather than collapsed, because several entries record *why* a
design is the way it is — and a future maintainer who does not know that will
undo it. The published git history begins at 1.0.0; this file is where the
reasoning lives.

### Changed — release-readiness pass: privacy leak closed, cut-off data withdrawn, desktop build added, 2026-08-14

A full pre-release audit against four questions — ready to publish, private enough, any data or PII leakage, any breach of Singapore law or the project's licences. The report is in `RELEASE_REVIEW_2026-08-14.md`. Four blockers were found; all four are resolved below, plus everything on the should-fix list.

**The privacy leak.** `web/index.html` loaded Inter and Outfit from Google's CDN on every page view, sending each visitor's IP address, User-Agent and Referer to Google before the page rendered. On a tool for children whose header says *"nothing you type here leaves this device"*. Three lines below those `<link>` tags the file's own comment read *"no fonts fetched"*. It went unnoticed because `tools/serve.py` sets `default-src 'self'`, which **blocks** the request locally — so it only ever fired for real users on GitHub Pages, where a response header cannot reach. Removed; the type now uses each platform's own UI font, with Inter and Outfit still named first so a reader who has them locally gets them at no network cost. `index.html` now carries its own `<meta>` CSP so the guarantee travels with the file — onto Pages, a USB stick, or a `file://` open. CI gained a check that the meta CSP exists and starts from `default-src 'self'`.

**Cut-off data withdrawn from the published build.** Previously the pack shipped Posting Group cut-off points for 139 schools, transcribed from a third party's compiled table, under a licence label reading *"no content reproduced"*, while `SAFEGUARDS.md` §3b forbade *"wholesale republication"*. Three things that could not all be true. A fair-dealing argument was available and is probably sound — but the people who would bear the cost of it being wrong are families using a free tool, so:

- The public pack carries **no** cut-off figures. Every school card deep-links to that school's own MOE SchoolFinder page, and the reader gets the official figure at source: current, in MOE's framing, with MOE's caveats. Better as a product too — a copied snapshot starts going stale the moment the next posting exercise runs.
- New licence id `moe-tou-linked` — "linked at source; nothing reproduced here" — so the distinction lives in the data rather than in prose.
- An individual may keep a private copy at `packs/<id>/local/` for their own study. Merged **at load time** by `engine/loader.py`, never at build time, because `secondary-schools.yaml` is tracked and anything written into it can be committed; a value that exists only in memory cannot be. Gitignored as a second line of defence, not the only one. Labelled in the UI as the reader's own, never as something PathAhead published. See `docs/LOCAL_DATA.md`.
- CI fails on any tracked pack containing cut-off figures, on any committed file under `packs/*/local/`, and on a published pack that carries them.
- `SAFEGUARDS.md` §3b gained answer 6, reconciling the document with the code and stating the general rule: **where a fair-dealing argument would be needed to justify shipping something, do not ship it.**

**ODL attribution, actually rendered.** The Singapore Open Data Licence requires a conspicuous notice *in the product* with a live link to the licence. The footer carried the sentence as inert text with a bare URL. `Source.licence_url` now survives pack compilation, `linkifyUrls()` renders pack-authored URLs as real links, `#/data` shows the notice prominently and hyperlinks every licence name, and the attribution text was rewritten to the licence's own example format — naming the datasets and the access date.

**Repository.** Initialised (it never had been). Removed a stray 449 KB print-to-PDF of a live session and a 70-byte file containing `404 Not Found`. `web/site/` (391 generated files) is now gitignored and built by CI instead of committed. `package-lock.json` is now committed rather than ignored, so builds are reproducible. Dropped `playwright-core`, a runtime dependency nothing imported.

**Two long-standing DOM failures fixed, and one was hiding a real bug.** `constraint chips renders` was simply stale — the UI deliberately consolidated four chips into two, and the check was never updated. `how many optional questions are answered is stated` was the interesting one: the anti-nagging regex fired on *"none of them is required"*, the same shape as a banned-phrase guard firing on *"does not guarantee a place"*. Rewriting the sentence exposed the actual defect — `FIT_SIGNALS` has 9 entries but the browser only ever sets 7, so the progress line could reach at most **"7 of 9 answered"** and a family who had answered everything on screen was told two were missing, with no way to find them. Fixed with `ASKED_SIGNALS`; `FIT_SIGNALS` left alone because it defines `signals_available` in a real score and must match the Python engine. `check:ui` is now **116/116** for the first time.

**`ruff check .` passes for the first time** — 12 findings, 11 of them pre-existing, meaning the lint job in CI had never been green.

**Also:** `robots.txt` and `sitemap.txt` moved to the deploy root (they were being written to `web/site/`, so GitHub Pages served them at `/site/robots.txt` where no crawler looks — the careful `noindex` work on 98 incomplete pages was resting on a file nothing read). CI now builds the static site before deploying and passes `--base`. A standing "What PathAhead is, and what it is not" card is reachable from the footer and repeated on `#/data`.

### Added — a self-contained desktop build, 2026-08-14

`desktop.py` plus `tools/build_desktop.py` produce a single executable — about 7 MB — that runs PathAhead with no install, no Python, and no internet. Double-click, a browser opens on the app served from `127.0.0.1`. `.github/workflows/release.yml` builds Windows, macOS and Linux binaries on tag, verifies each one actually serves the app before publishing, and attaches them with SHA256 sums.

It serves the same `web/index.html` as the hosted build against the same compiled pack — one artifact, tested once. Two things it deliberately does:

- **Refuses to build if a local data overlay is present**, unless given `--include-local`, which stamps `-LOCAL-DO-NOT-SHARE` into the filename. An `.exe` is a redistribution like any other and a worse one to get wrong: a reviewer can read a git diff, but nobody inspects a binary before forwarding it to a WhatsApp group.
- **Makes the privacy claim checkable.** "Nothing leaves this device" is hard for a non-technical reader to verify on a website. An executable they can run with the wifi off is a claim they can test in ten seconds.

`tests/test_desktop.py` adds 9 tests covering the parts that decide whether the packaged app is safe: that it binds loopback and not every interface, that every response carries the CSP and the hardening headers, that path traversal cannot escape the web root, and that `_MEIPASS` resolution works frozen and unfrozen.

### Added — every school card states last year's published PSLE Score range, unconditionally, 2026-08-13

Asked directly: make sure the latest (2025) Posting Group range shows for every school on the PSLE shortlist. Until this change, the published `cutoff_2025` figure only surfaced through the reach filter's copy — true "in reach" / "out of reach" sentences once a PSLE score was entered, or the cut-off note for the 8 schools with none, but never the raw range itself, and never before a score existed.

- **New: `cutoffRangeText()` / `cutoffRangeLine()` (`web/index.html`).** Formats a school's PG3/PG2/PG1 (and IP, where it has its own row) range from `cutoff_2025` into one line — `"Last year's PSLE Score range by Posting Group (2025 S1 Posting Exercise; lower is stronger): PG3 16–22 · PG2 21–25 · PG1 25–29."` — dated, sourced, and stating which direction is stronger every time, since a bigger PSLE Score reads as "better" to anyone used to ordinary exam grades and is the opposite. Shown on **every** school card, before a PSLE score is entered or after, regardless of whether the reach filter is engaged. The 8 schools with no published cut-off show their existing `cutoff_note` explanation instead — never blank, never silently different from the 139 that do have one.
- **`reachLine()` simplified** to only the two personalised cases (in reach / out of reach for THIS family's score); the "no cut-off published at all" case moved into `cutoffRangeLine()` so it no longer depends on a score having been entered first.
- **Still a display, never a rank.** The shortlist's sort order (distance, then name) and every filter's behaviour are unchanged — this only adds a line of published fact to every card, per SAFEGUARDS.md 4b ("these are last year's numbers, not this year's outcome"). No banned phrase, no threshold framed as a guarantee.
- Explainer copy above the form ("How these filters work") updated to describe the always-visible range separately from the reach filter, and to state the lower-is-stronger direction once, up front.

Verification: 1 new DOM check confirming the range renders with no PSLE score set (a school with data, and one without); 111/113 UI checks (same 2 pre-existing documented failures). Full suite green: `pytest` (295 tests), `check_golden.mjs` (37/37, unaffected — pure display change, no engine logic touched), `python app/cli.py health --gate` (PASS).

### Changed — the school shortlist is filters only, all the way down; the match SCORE is gone, 2026-08-13

Asked directly, after the reach/distance filter work below shipped: "I think
scoring does not make any sense here, may be all conditions just help to
filter out." Right. The weighted 0–100 "Match" score that ranked all 147
schools was still there underneath the two new filters, and on review it was
the same SAFEGUARDS.md 5.1 risk the cut-off data itself had already been
kept out of — a percentage and a bar chart read as a verdict on a school no
matter how carefully the copy around them explains they are not one, and
ranking real schools by "how well they match" sits one small step from
ranking them by how good they are. The fix is not a better score. It is no
score.

- **`engine/school_fit.py` rewritten.** `score_school`, `SchoolFitScore`,
  `SchoolFitFactor`, `shortlist`'s score-then-name sort, `WEIGHTED_DIMENSIONS`,
  `IMPORTANCE_LEVELS`, `dimension_weights`, `MIN_SIGNALS` — all gone. In their
  place: `match_school()` returns a `SchoolMatch` with three fields that
  never combine into a number — `eligible` (the sex-based admission fact,
  still three states: true / false / "can't confirm yet"), `matches_preferences`
  (true iff every filter the family actually set is satisfied — AND logic,
  no weighting), and `distance_km` (unchanged, informational). `shortlist()`
  now sorts strictly by distance (closest first, when a postal code was
  given) then name — both explicitly allowed under SAFEGUARDS.md 5.1's own
  wording ("fit, programme and location"); it does not drop ineligible or
  non-matching schools itself, exactly like `within_reach()` already didn't —
  that stays the caller's job, counted and reported, never silent.
- **The old "how close to home" scored dimension is retired.** It used to be
  a three-tier own-district/same-region/elsewhere score derived from postal
  code alone. That's redundant with the real km-band filter shipped in the
  previous entry below, so there is now exactly one "how far" mechanism
  instead of two that could disagree with each other. Postal district still
  shows as an informational tag on every card.
- **Every remaining preference (co-ed/single-sex, SAP, IP, Autonomous, GEP,
  school type) is now a plain AND-filter**, same shape as the reach and
  distance filters: set it, and it hides schools that don't match; leave it
  at "No preference", and it does nothing. The tri-state buttons were
  relabelled "No preference" / "Only show these" / "Hide these" to say what
  they now actually do, replacing "Prefer" / "Prefer not", which read as a
  soft nudge on a score that no longer exists.
- **The "How much does each of these matter?" importance-weighting UI is
  gone** (`renderSchoolRanking()`, `PS.importance`) — there is nothing left
  to weight. All 147 schools show by default now; previously nothing
  rendered until at least one preference was set.
- **The sex-eligibility gate changed shape, not substance.** A student who
  cannot attend a single-sex school still never sees it ranked or scored —
  now it is hidden outright, the one unconditional hide in the whole
  feature, with the hidden count stated plainly in the summary
  ("N not admitting your child's sex"). An unanswered sex still leaves
  single-sex schools visible with a caveat rather than guessing, unchanged
  from before.
- **Copy rewritten throughout**: `NOT_AN_ADMISSION_ESTIMATE` →
  `FILTER_DISCLAIMER`; "How this ranking works" → "How these filters work";
  every "score"/"rank"/"match score" reference in the honesty section and
  "what is not here yet" rewritten to describe filtering.

Verification: `tests/test_school_fit.py` rewritten for the filter design (42
tests, up from 40 — same file, different claims); 7 golden fixtures replaced
(`school_fit_cases` → `school_match_cases`, 37/37 cross-engine parity, down
one fixture net since the retired proximity-tiers case had no filter
equivalent to replace it with); `tools/check_ui.mjs`'s school-shortlist
section rewritten (16 checks, 110/112 UI checks overall — same 2
pre-existing documented failures, nothing new). Full suite green: `pytest`
(295 tests), `check:site` (18/18), `check_golden.mjs` (37/37), `check_ui.mjs`
(110/112), `python app/cli.py health --gate` (PASS).

### Added — cut-off-based reach and distance FILTERS for the school shortlist, 2026-08-13

Asked directly: families already have a target score in mind, MOE publishes
the previous year's Posting Group cut-off exactly so people can use it when
choosing schools, and hiding that number from a tool built to help with this
exact decision was making PathAhead less useful than MOE's own SchoolFinder
tool — not more honest. Fair, and the shortlist was missing something real.

What did NOT change: SAFEGUARDS.md 5.1 ("never rank schools by cut-off
point... the single easiest way for a tool like this to cause harm in
Singapore") still holds exactly as written. The shortlist is still sorted
purely by preference match and distance, never by selectivity, and this
round adds no "top schools" list, no league table, no default sort by
cut-off. What changed is a new, separate kind of control: a FILTER, which
narrows which of the 147 schools appear without ever touching the order
of what remains.

- **New data: `cutoff_2025`, for 139 of 147 schools.** December 2025 S1
  Posting Exercise (2026 intake) Posting Group 1/2/3 and Integrated
  Programme cut-off points. MOE's own SchoolFinder tool is a client-rendered
  application with no bulk export PathAhead's build process can fetch, so
  this was retrieved via KiasuParents' compiled table (which states its own
  source and date as "MOE SchoolFinder, May 2026") and recorded at
  `confidence: medium` rather than `high` for exactly that reason — the
  figures are MOE's, the retrieval path was not a first-hand fetch. The 8
  schools with no row (auditions, aptitude tests, sports trials, or a
  customised curriculum instead of the standard PSLE-score exercise) carry
  an explicit `cutoff_note` explaining why, rather than silently having
  nothing. See `tools/build_secondary_schools_pack.py`.
- **New: `within_reach()` (Python + JS, cross-engine parity verified).** A
  yes/no/unknown question, never a score: does last year's cut-off, for
  whichever Posting Group the family's own PSLE score has opened, suggest a
  school is realistically still worth a spot on a real six-school list. A
  2-point margin is always applied rather than a hard line at last year's
  number, because MOE's own words are that cut-off points "can fluctuate by
  a few points year-on-year." Returns `None`/`null` — never `False` — when
  PathAhead genuinely cannot judge (no cut-off published, or the score fell
  outside the published table); callers must show these schools, not treat
  "cannot tell" as "no". See `engine/school_fit.py`.
- **New UI: "narrow the list further"**, on `#/psle`. Two filters, both
  disabled with an explanatory hint until their prerequisite is set: a
  straight-line distance band (5/10/20km — still not a travel time, still
  informational, still never scored) shown alongside the existing
  district/region proximity tiers rather than replacing them per feedback;
  and a reach toggle that hides schools clearly past cut-off+margin while
  always keeping specialised-admission and outside-table schools visible,
  marked as unable to be judged. The visible list is still sorted by fit and
  distance throughout — filters narrow, they never reorder. The "what is not
  here yet" section and the school-fit honesty copy were both updated to
  describe this accurately (the old "no licensed cut-off source exists" line
  was true in an earlier session and is not true anymore).

Verification: 9 new Python tests for `within_reach` (40 total in
`test_school_fit.py`), 7 new golden fixtures (38/38 cross-engine parity), 5
new DOM checks (a prerequisite-disabled check, a distance-filter effect
check, a reach-filter effect check proving both the hide and the
never-hide-unknown cases, plus one existing check rewritten for the new
"what is not here yet" copy) — 110/112 UI checks (same 2 pre-existing
documented failures). Two real bugs caught and fixed during this pass, not
by these tests but by building them: entering a PSLE score after already
viewing the shortlist left the reach filter stuck showing "enter your score
first" (the score field's `oninput` never repainted the shortlist section);
and the distance-filter chips never repainted their own pressed-state on
click. Full suite green: `pytest` (295 tests), `check:fast`,
`check_golden.mjs` (38/38), `check_ui.mjs` (110/112), `python app/cli.py
health --gate`.

### Fixed / Added — sex-eligibility gate and a real distance signal, 2026-08-13

Reviewed again, this time from a parent's perspective rather than a
developer's: "you can not show only boys or only girls school" for a
student who cannot attend one, and "include approximate travel time based on
postal code." Both were real gaps.

- **A boys'-only or girls'-only school could appear as a scored option for a
  student who cannot attend it.** An earlier version of `school_fit.py`
  treated single-sex admission as a soft, scored preference dimension rather
  than a hard eligibility gate — the same class of mistake `fit.py` already
  guards against for subject and language requirements. Fixed by asking for
  the student's sex directly (`SchoolPreferences.student_sex`) and checking
  it *before* any preference scoring, mirroring `fit.py`'s own
  eligibility-before-preference pattern exactly: a school the student cannot
  attend now gets **no score at all** — never a low one — with a plain
  reason shown instead ("does not admit boys" / sex not yet answered). The
  "co-ed or single-sex" soft preference no longer offers an option the
  student's sex has already ruled out. Verified with 6 new Python tests, 2
  new golden fixtures (cross-engine parity, 31/31), and 2 new DOM checks.
- **Added a real, honestly-labelled distance to each school.** "How close to
  home" was, and still is, scored only by postal-district/region tiers —
  never by distance, per the project's standing "nothing you type leaves
  this device" rule, since a live routing call would mean the family's
  postal code left the device. What's new: every school's postal code and
  every postal district's representative anchor point were geocoded ONCE,
  offline, at pack-build time via OneMap Singapore (`onemap-geocoding-2026`,
  `sg-odl-1.0`) — the same pattern already used for the school directory
  itself. A straight-line (haversine) distance is now computed entirely
  client-side from those pre-fetched coordinates, shown next to each school
  labelled explicitly as "straight-line (not a travel time)," and is purely
  informational — it never feeds the match score. A "Get directions" link
  opens Google Maps with the school's own public address as the
  destination; it never carries the family's typed postal code, so the
  "nothing you type leaves this device" promise holds even when a family
  clicks through. Verified with 7 new Python tests (including that
  `distance_km` stays populated even for a school the sex gate has just
  excluded, and that it never moves the score), 1 new golden fixture
  assertion (`distance_km` cross-engine parity), and 2 new DOM checks
  (including one that asserts the family's own postal code is absent from
  the outbound link's URL).

Verification: `pytest` (all school-fit tests green, 38 total), `check:fast`,
`check_golden.mjs` (31/31), `check_ui.mjs` (107/109, same 2 pre-existing
documented failures), `python app/cli.py health --gate`.

### Fixed — a self-review of the school shortlist found a real bug and three weak spots, 2026-08-12

Asked to critique the shortlist added two days earlier rather than assume it
was fine. It wasn't, quite.

- **A literal "null" rendered on screen.** `Element.replaceChildren(x)` does
  not skip a bare `null` argument — it stringifies it to a text node reading
  `null`. Both `renderRanking()` (the A-Level importance ranking, shipped
  well before this session) and the new `renderSchoolRanking()` called
  `actions.replaceChildren(cond ? el(...) : null)` directly, so anyone who
  had not yet touched an importance slider saw the word "null" sitting on
  the page. This was a pre-existing defect in the shipped A-Level page,
  copied into the new PSLE code without anyone noticing either instance —
  reviewed as a whole rather than confirmed working. Fixed in both places by
  filtering the ternary out of an array before spreading it into
  `replaceChildren`, and a DOM check now guards each site so it can't come
  back quietly.
- **Setting one preference produced a list that looked broken, not honest.**
  "Co-ed" alone ties 124 of 147 schools at the same score, and the shortlist
  showed the first ten of those alphabetically — reading as arbitrary rather
  than as "not enough set yet." The A-Level fit page already solved this
  exact problem with a "nothing stands out yet" note; the PSLE shortlist
  didn't have the equivalent. It does now — a nudge naming the tie and
  pointing at what would separate it, only shown when the tie is wide enough
  to matter.
- **The postal code field sat two screens away from "your address does not
  help you get in"** with nothing connecting them. A parent who read the
  honesty section above and then scrolled to a form asking for a postal code
  could reasonably read that as a contradiction. The field's own hint now
  says explicitly that this is separate from S1 posting, which never touches
  an address, and that this postal code only helps the family compare
  schools by their own convenience.
- **No way to start over.** Seven preferences, a postal code and a
  seven-row importance ranking, and clearing them meant touching each
  control by hand. A "Clear all preferences" button now appears once
  anything is set.
- **"How this ranking works" sat in a collapsed disclosure after the results,
  not before them.** Asked explicitly for the algorithm to be explained, and
  then wrote the explanation in the one place a skeptical reader is least
  likely to open before typing anything. It now opens by default, above the
  preference form, not below it.
- Smaller: the tri-state labels "Yes please" / "Avoid" read as tonally
  inconsistent with the rest of the page and are now "Prefer" / "Prefer
  not"; the dimension list inside the algorithm explanation had no CSS rule
  (`.plain-list`) and fell back to default browser bullets — it has one now.

Verification: 2 new DOM checks (one per `replaceChildren(null)` site), 1
existing check adjusted for the new tied-at-top summary text, full suite
still green — `pytest`, `check:fast`, `check_golden.mjs` (29/29),
`check_ui.mjs` (103/105, same 2 pre-existing documented failures).

### Added — a real school shortlist on `#/psle`, 2026-08-10

The PSLE page used to score a Posting Group and stop, with a note that
secondary schools themselves were "a separate piece of work with a licensing
review attached." This is that work — a shortlist of all 147 schools a PSLE
cohort can be posted to, ranked against what a family actually says they're
looking for, with the reasoning shown for every school, every time.

**The licensing gap is closed, with a different source.** MOE SchoolFinder's
Terms of Use permit citing and deep-linking but not copying its data, which
is why schools were left out the first time. `data.gov.sg` publishes MOE's
own "General information of schools" dataset — 337 schools, all levels —
under the Singapore Open Data Licence v1.0, which explicitly permits
commercial use, modification and redistribution with attribution. Filtered
to the 147 that take a normal S1 intake from PSLE (excluding primary schools,
JCs and the Millennia Institute; including the through-train `MIXED LEVEL`
schools like Raffles Institution and Hwa Chong), transcribed with name,
address, postal code, MRT/bus description, school type, gender composition,
and SAP / Autonomous / Gifted / Integrated Programme flags — every field
verbatim, none reinterpreted. A second small table, Singapore's 28 postal
districts (SingPost's own scheme, transcribed from a public secondary
source), turns a postal code into a district and one of five editorial
regions PathAhead defines itself and says so.

**What is still deliberately not here: cut-off points.** No permissively
licensed source for per-school Posting Group ranges exists — SchoolFinder is
still cite-and-link-only for that figure, and no dataset on data.gov.sg
publishes it. So the shortlist never estimates, implies, or ranks by which
schools a PSLE score could reach. It answers a narrower, different question —
which schools match what you said matters to you — and the distinction is
structural, not just a caveat: there is no eligibility axis in this feature
at all, because there is no data to check eligibility against. `engine/
school_fit.py` mirrors `engine/fit.py`'s course-fit engine (weighted
dimensions, importance set by the family, a dimension scored only when both
sides of it — the preference and the school's own data — exist) with the one
exception course fit doesn't need: single-sex admission is a structural fact,
not a soft preference, and the ranking says so rather than silently hiding
gender-restricted schools from a family who never stated a gender.

**Seven scored dimensions**, each optional, each dropped from scoring
entirely (never penalised) when unanswered: how close to home (own postal
district scores highest, same broad region scores partway, elsewhere scores
lowest — never a fabricated distance or travel time, because Singapore's
transfer-dependent transit network would make a straight-line number
misleading), co-ed or single-sex, Special Assistance Plan, Integrated
Programme, Autonomous status, a Gifted Education Programme branch, and school
type. A family can weight any of them "doesn't matter" through "most," the
same importance scale `#/alevel` already uses, and a dimension ranked
"doesn't matter" leaves the fraction entirely rather than counting at zero.

**Two known, stated gaps, not silently filled:** co-curricular activities (a
data.gov.sg dataset exists; pulling and cleaning it did not make this pass)
and religious or primary-school affiliation (true and checkable per school,
but not in any dataset PathAhead can cite in bulk — hand-curating 147 schools
one at a time is exactly the kind of unverifiable transcription this project
avoids).

**Also fixed in passing:** the masthead "PathAhead" wordmark was a plain
`<div>` — clicking it did nothing, and the only way back to the chooser from
deep inside a track was the small "Change track" link, which doesn't even
appear on shared pages like `#/data`. It's a link to `#/` now, from anywhere.

Verification: 18 new Python tests (`tests/test_school_fit.py`), 6 new
cross-engine golden fixtures (29/29 agree between Python and the browser, up
from 23), 6 new DOM checks plus 2 rewritten ones whose old assertions no
longer matched a page that legitimately grew a second citation and a second
optional input (101/103 passing, up from 94/96 — the 2 remaining failures are
the same pre-existing, documented ones). Full suite green: `pytest`,
`check:fast`, `check_golden.mjs`, `check_ui.mjs`, `health --gate`.

### Fixed — the chooser's nav contradicted its own door cards, 2026-08-10

Caught from a screenshot of the shipped page, not from a test — a real gap in
what was reviewed before the three-door redesign above was called done.

The `#/` nav read **A-Level, Sources, After PSLE, O-Level, No idea yet,
Results day, Two of you.** The door cards two inches below it went **After
PSLE, O-Level, A-Level.** Two pieces of navigation on the same screen
disagreeing about the order of a family's own life through school — and the
nav also duplicated the three doors as bare, equally-weighted pills next to
four utility pages, with no way to tell which four of the seven were "pick
your stage."

The cause: `buildNav()` filtered `ROUTES` and rendered whatever order the
array happened to hold — A-Level's entry, because A-Level was the first
stage this app ever had, sitting years before PSLE's or O-Level's entries in
the same file. Nothing enforced door order against card order; they were two
independently-written lists that happened to agree until a third stage made
them not.

- **The chooser's nav now shows exactly the three doors**, in a fixed
  `TRACK_ENTRY_ORDER` (PSLE, O-Level, A-Level) that both the nav and the door
  cards read from — one order, not two. Sources, No idea yet, Results day and
  Two of you moved to the "If none of those is where you are" list on the
  page body, where each already had a sentence explaining what it was for;
  the nav pill never had room for that context.
- **`.card::before`'s top accent stripe** ran brand → a fixed orange → the
  plum "editorial" colour on every card, on every page, regardless of track —
  so a card on the moss PSLE page carried an orange-to-purple stripe that
  matched nothing else on it. Now runs brand → brand-deep, both of which
  follow `data-track`, so the stripe is always the current track's own
  colour.
- **`#/more`'s mobile catch-all was unreachable from either nav** — a
  pre-existing gap the same rewrite touched in passing, fixed alongside it
  rather than left for a second pass.
- One new DOM check pins the chooser's nav to exactly `psle,olevel,alevel`,
  in that order, so this specific disagreement cannot silently return.

### Added — the O-Level/SEC stage, `#/olevel`, and the three-door redesign, 2026-08-10

The third and last stage. PathAhead now scores every transition Singapore's
school system has between Primary 1 and university, across three genuinely
distinct tracks with their own look, their own navigation, and their own
front door — the redesign the PSLE work's front-door fix was heading toward.

- **A third rule kind, `required_plus_best_n`.** L1R5, L1R4 and the ELR2B2
  approximation are one compulsory subject plus the best N of each of a list
  of groups, lower is better — already implemented in Python from an earlier
  session, ported to the browser engine here (`web/index.html`'s
  `requiredPlusBestN`), with five new golden fixtures chosen to exercise every
  group shape: a plain run, the floor of the scale, a group whose pool empties
  and must fall back correctly (`used` removing consumed subjects), the 2028
  SEC cohort's four-subject ceiling, and the polytechnic group with no pool
  restriction at all. 23/23 fixtures agree between the two engines.
- **`packs/singapore/olevel.yaml`** — sources, three cohorts (Sec 2/3/4, routed
  by the year Secondary 1 started, not by exam year), 25 O-Level subjects, and
  four transitions: `o-level-to-jc-mi-2027` and `o-level-to-polytechnic-2027`
  (the legacy O-Level, real course data), `sec-to-jc-mi-2028` and
  `sec-to-polytechnic-2028` (the incoming SEC, aggregate-only — no institution
  has published a course-level cut-off under a system that has not run yet,
  and asserting one would be inventing a number). 33 JC/MI course outcomes
  across 16 institutions, each read from that school's own MOE SchoolFinder
  page and individually dated.
- **`also_scored_under` on `Outcome`, and `Pack.outcomes_for()` reading it.**
  The ~330 polytechnic outcomes already loaded for A-Level are an O-Level
  applicant's OWN basis, not a foreign one — so rather than duplicate 330 rows
  into a second file, `_attach_cross_transition_reuse` (in `engine/loader.py`)
  tags them, once, with the O-Level polytechnic transition's id. A-Level's
  existing "declined comparison" behaviour is unchanged; the same records now
  additionally answer to a second, real comparison for a different reader.
- **`assess_min_max_band`, and a `comparable_here` check that is no longer a
  blanket "no."** A min-max band used to be rejected outright if `comparable:
  true`, because the only min-max bands in the pack were A-Level-context
  polytechnic ranges where that was always a mistake. It stopped being always
  true the moment an O-Level transition scores an L1R5/L1R4 aggregate
  NATIVELY against a min-max JC/MI range — there `comparable: true` is
  correct. What still cannot happen — a min-max band narrated in percentile
  words — is now enforced structurally: `forward.py` branches on
  `band.statistic` before choosing `assess_band` or `assess_min_max_band`,
  each with its own vocabulary (`HEADLINE_MINMAX`/`EXPLANATION_MINMAX` beside
  the existing `HEADLINE`/`EXPLANATION`, mirrored in the JS engine).
- **`explore_secondary()`** scores a second transition from the same grade
  sheet without cohort resolution — the mechanism behind the O-Level page
  showing an ELR2B2 polytechnic route alongside the primary L1R5/L1R4 one,
  from one set of entered grades, never asked for twice.
- **The three-door redesign.** `#/` now sets a distinct CSS accent per track
  (`data-track="psle|olevel|alevel"`, reusing the palette's already
  WCAG-AA-checked moss and plum pairs rather than inventing new ones) and
  scopes the top nav and tab bar to the current track's own pages plus a
  compact "Change track" link back to the chooser — a parent on the PSLE page
  no longer sees Fees, Dates or Ways In, which belong to A-Level alone.
  10 new checks cover the accent switching per route, the A-Level-only pages
  disappearing from PSLE/O-Level nav, and the change-track link appearing only
  inside a track.
- **`#/olevel`** — cohort choice before a single grade, same "no form above
  the fold" reasoning as `#/psle`: which rulebook applies (L1R5 on the 2027
  JAE, or L1R4 on the 2028 PSE) depends on the year Secondary 1 started, not
  on results day. A complete sheet shows the full derivation trace, the JC/MI
  outcomes it reaches, and the polytechnic ELR2B2 route from the same
  subjects; an incomplete one fails with the missing group named, never a
  crash; the SEC-era cohorts state plainly that no course data exists yet
  rather than showing last cohort's numbers next to a different ceiling.
  7 new DOM checks, including one confirming Millennia Institute (scored on
  L1R4, not this page's L1R5) is shown but never placed in a bucket.
- **Two real gaps the new pack exposed in existing guards, both fixed at the
  source rather than by exempting the new data**: the stream-coverage filter
  check assumed every outcome belonged to the A-Level sector taxonomy, which
  a JC "Science (27S)" course never did — scoped to the outcomes the stream
  picker actually governs. The static-site "no third-party resource" check
  had no allowance for `moe.gov.sg`, because no course `url` had ever pointed
  there before a JC/MI outcome with no listing page of its own needed to.
- **The same "does not guarantee a place" mistake, caught the same way.**
  Two caveats in the new pack tripped the banned-phrase guard on a negation.
  Rewritten, not loosened — see
  [docs/UI_CHECK_FAILURES_2026-08-09.md](docs/UI_CHECK_FAILURES_2026-08-09.md)
  for why that is the standing rule here.

**What is explicitly an approximation, and says so on every screen that shows
it:** ELR2B2's "2 relevant subjects" are course-specific in reality (an
engineering diploma and a business diploma name different subjects); PathAhead
computes English plus the best 4 of everything else instead, because the
per-course relevant-subject list is not loaded. Bonus points (CCA, language,
affiliated-JC) are not modelled anywhere in this stage, so every aggregate
shown is the GROSS figure, not the NET one JAE actually posts on — the more
conservative of the two.

**Not green**, unchanged from before this work: `check:ui` is **94/96**. Both
failures predate the O-Level stage and sit in the A-Level profile step —
`conChips` renders 2 chips where the check expects 4, and the progress note's
reassurance trips the anti-nagging regex on the word "required". See
[docs/UI_CHECK_FAILURES_2026-08-09.md](docs/UI_CHECK_FAILURES_2026-08-09.md).

### Added — the PSLE stage, and `#/psle`, 2026-08-09

Phase B, minus schools. PathAhead now scores a second transition and has a
second front door. The engine needed no new concepts, which is what
[ROADMAP.md §1](ROADMAP.md) predicted when it argued for building the hardest
stage first: this was pack-authoring plus one rule kind that already existed.

- **`packs/singapore/psle.yaml`** — the whole stage in one reviewable file.
  Seven cited MOE sources, the P5 and P6 cohorts, the four subjects and their
  Foundation variants, the AL scale, the Posting Group table, and the
  tie-breaker and DSA rules as caveats. Verified against `moe.gov.sg` on
  2026-08-09; see [docs/POST_PSLE_AND_PORTAL.md](docs/POST_PSLE_AND_PORTAL.md) §1.
- **`engine/posting.py`** — score → Posting Group, entirely pack-driven. It
  **refuses to extrapolate**: 31, 32, and 26–30 without AL7 in both English and
  Mathematics return `outside_the_table` with the published route and the named
  schools, never an invented fourth group and never "no group", which a parent
  reads as "no school".
- **`lowest_sum` ported to the browser engine**, with five golden fixtures that
  exercise it in both. This is the direct answer to the session where the
  cross-engine check passed 11/11 on code it had never run — a rule that
  nothing replays is present, not verified.
- **`#/psle`** — a separate landing page rather than a mode of `#/`. A P6
  parent and a JC2 student are not the same reader, and folding both into one
  page settles the tone on whichever already exists. No transcript is asked for
  above the fold; the route for a score outside the published table is a door,
  not a footer. 11 new DOM checks.

**Schools are deliberately absent.** Cut-off ranges are published per school and
per Posting Group in SchoolFinder under MOE's Terms of Use, which permit citing
and deep-linking but not copying. Loading 148 schools is a separate piece of
work with a licensing review attached, and the page says so rather than leaving
a gap that looks unfinished.

#### `#/` is now a stage chooser, not the A-Level form

The front door had been the A-Level grades table since the first release. That
was defensible with one stage and indefensible with two: the parent of a
Primary 6 child arrived at a form asking for H2 subject grades.

- **`#/`** — one question, three doors, no form control anywhere on it. This is
  the design [docs/POST_PSLE_AND_PORTAL.md](docs/POST_PSLE_AND_PORTAL.md) §4
  called for and the first pass only half-did.
- **`#/alevel`** — the A-Level questions, unchanged. Every "back to the start"
  link now points here rather than at the chooser.
- **The unbuilt stage is on the page.** O-Level/SEC has a door that is not a
  link and says what is missing and why. A stage silently absent from the list
  is how a family concludes the tool has nothing for them; "coming soon" is
  worse. Equal width and equal weight across all three, so none reads as the
  main one.

Six new checks, including: the front door carries no `input` or `select`; every
stage in the pack has a door; a door is a link **only** when the pack holds a
transition that can score it; and an unbuilt stage may not say "coming soon".

#### The regression this shipped with, and how it got through

**Adding the PSLE cohorts to the pack put "Primary 5" and "Primary 6" into the
A-Level start page's year-level dropdown.** Choosing Primary 6 correctly read
back *"sitting the Primary School Leaving Examination in 2026"* and then asked
the parent for H2 subjects and General Paper on the very next card. Reported
from real use, and it was in the build for the length of one session.

The cause is one unfiltered line — `pack.cohorts.forEach(...)` — and the reason
it survived is more instructive than the line. `check_ui.mjs` had a check on
that dropdown the whole time: *"cohort question is populated"*, asserting at
least three options. Five is at least three, so it passed. **A count is not a
guard.** What mattered was *which* cohorts, and nothing asserted that.

Fixed by making the stage structural rather than remembered: `#view-start`
carries `data-stage="a-level"` and the dropdown is filtered by it, so a cohort
belonging to another stage cannot appear. Cohorts that are filtered out are
*named on the page* with a link to the page that serves them — an option
silently removed is how a family concludes the tool has nothing for them.

Three new checks, and the first was confirmed to fail against the bug before
being kept: the year-level list may only offer cohorts of this page's stage;
cohorts from other stages must be named and linked; and the grade rows may only
offer subject levels the stage actually examines.

#### Two bugs, both found by guards rather than by review

- **`_normalise_grade` rejected its own output.** `GradeSheet.to_dict()` writes
  the normalised grade, so `"FA"` came back in through every round trip — a
  saved profile, a golden fixture, a replayed bundle — and was refused as not
  being an Achievement Level. Normalising is now idempotent. The new fixtures
  caught it; nothing else would have.
- **A safeguard fired on a reassurance.** `test_no_banned_phrase_reaches_the_user`
  bans `guarantee a place`, and the new caveat said *"does not guarantee a
  place"*. The sentence was rewritten rather than the guard loosened. The same
  pattern is live elsewhere in the repo and is written up in
  [docs/UI_CHECK_FAILURES_2026-08-09.md](docs/UI_CHECK_FAILURES_2026-08-09.md).

#### One correction to the research, worth recording

**A home address does not help a child get into a secondary school.** The S1
tie-breakers are citizenship, then choice order, then a computerised ballot;
distance is not among them, and matters only when a child cannot be placed in
any of their six choices. Distance *is* a criterion at Primary 1 registration,
which families conflate with this constantly. The location field is therefore
worth having for commute estimation and for nothing else, and the UI says so
where the field is.

#### Not green

`check:ui` is **75/77**. Both failures predate this work and sit in the A-Level
profile step — `conChips` renders 2 chips where the check expects 4, and the
progress note's reassurance trips the anti-nagging regex on the word
"required". Written up rather than fixed, because each needs a decision about
which side is wrong. `START_HERE.md`'s claim of 66/66 was already stale.

### Added — polytechnic tuition fees for four of the five, 2026-08-05

Fee coverage **111 → 266 of 330 courses**, and the static site **111 → 265
indexable pages**. Transcribed from four separate fee pages: NYP, RP, SP and
TP.

- **All four publish the identical AY2026 tuition**: SGD 3,100 citizen, 6,400
  PR, 12,400 international (ASEAN), 13,600 (non-ASEAN). Four publishers
  agreeing is the most inviting thing in this pack to tidy up, so each figure
  cites the polytechnic that will bill the family, and
  `test_each_polytechnic_fee_cites_the_polytechnic_that_will_bill_you` fails if
  they are ever collapsed into one source.
- **The supplementary fee differs at every one of them** — SP 77.52, TP 83.15,
  RP 86.50, NYP 88.09 a year for a citizen. Small money, but it is the proof
  that these are four publications rather than one figure republished, and it
  is the reason the identical tuition is not evidence about the fifth. It is
  carried in the note on every course, because a family is billed it.
- **The figure recorded is subsidised tuition, not "fees payable"** — the same
  measurement the six universities hold. Mixing the two would put SP's 3,177.52
  beside NUS's 8,250 as though they were comparable.
- **The tuition-grant bond travels with the fee**, as everywhere else: no bond
  for citizens, three years for PRs and international students, and the
  polytechnics' own statement that buying out means liquidated damages set by
  MOE rather than simply repaying the grant.
- **Two figures deliberately not recorded.** The non-subsidised rate for a
  student who declines the grant — every polytechnic says such a student pays
  full fees and none publishes the number — and the SGD 2,100 rate for citizens
  aged 40 and over, which is named in the note but is not the school-leaver
  cohort this transition is about.
- **A correction to NEXT.md §4b.** It recorded on 2026-08-03 that TP published
  no AY2026/2027 international table and that its visible international figure
  was the AY2025/2026 one. TP has since published both the ASEAN and non-ASEAN
  tables, and those are what is loaded.

### Not added — Ngee Ann, on purpose

NP's fee page returned an empty body on every route tried on 2026-08-05, while
its FAQ and academic-matters pages fetched normally. Its 41 courses carry a
`fee_note` saying PathAhead could not retrieve the page, and linking to it.

Filling them in from the other four would have flipped 41 courses from "no fee"
to priced with nothing visibly wrong. MOE setting a common subsidised rate is an
inference about a process, not a figure Ngee Ann published — and the
supplementary fee, which differs at all four, shows these are separate
publications. `test_ngee_ann_shows_no_fee_rather_than_its_neighbours_fee` pins
it.

### Fixed — two checks that would have gone on passing over stale copy

Both found by running the DOM suite, which had not run since U3.

- **`filtering by institution shows only that institution` was failing on a
  correctly filtered list.** It searched each rendered row for the literal
  "SP"; a course card names the institution the way a family says it —
  "Singapore Polytechnic" — and its id is lower-case. The filter was right and
  the assertion was wrong. Every row now carries `data-course`, and the check
  compares ids against the pack. It also switches to compact mode, which is
  unpaged, to prove nothing was silently *dropped* as well as nothing leaked.
- **`a missing fee reads as missing, not as free` named a Singapore Polytechnic
  course as its example of an unpriced one**, and failed the moment SP was
  priced — for the happiest possible reason. It now asks the bundle which
  courses lack a fee and samples one of each kind.
- **The fees page's "most misleading gap" warning said "no polytechnic course
  carries a fee figure yet".** True when written, false the morning four
  polytechnics loaded. It is now computed: whichever institution has the most
  unpriced courses is named, and the warning disappears when there are none. A
  caveat that outlives its cause teaches readers to discount every caveat on the
  page.

### Fixed — the UI tests were green against a file the app never loads

Found while checking whether the previous fix had actually reached the screen.
It had not.

- `serve` compiles the pack into **`web/data/`**, which is what the browser
  fetches. `build --out dist` writes somewhere else entirely. `check_ui.mjs`
  read `dist/`.
- So the language fix passed all 33 checks while `web/data/singapore.json` was
  still an hour old and contained **no `language_requirement` at all**. Every
  test was green against data the user would never see. That is the worst kind
  of green: it does not fail, it just stops meaning anything.
- `check_ui.mjs` now reads the served bundle, and a new check fails outright if
  it is older than any pack YAML — verified by touching a source file and
  watching it go red.

### Fixed — a course taught in Chinese was recommended to a student who does not read Chinese

Reported from real use, and the worst bug in the project so far.

- **What happened.** Ngee Ann's Diploma in Chinese Studies came out as the
  **second strongest match of 296 courses** for a student who does not read
  Chinese. It scored 67/100 and every point came from generic overlap — *"you
  work best through exams, and so does much of this course"*. Nothing in the
  pack recorded that NP requires Higher Chinese 1-4 or Chinese 1-3 to be
  considered, or that NP states **at least half the course is conducted in
  Chinese**.
- **The score was not too high — a score at all was the error.** Any number
  puts a course into a ranking; a low one would have ranked it above hundreds
  of others just the same. `score_outcome` now checks eligibility *before*
  preference and returns no score, with the requirement stated.
- **`LanguageRequirement` is official data with a source**, carrying both the
  published entry grade and, separately, `taught_in_language` — whether the
  teaching itself is in that language. The second field is the one a grade
  table would never tell you and the one that decides whether three years are
  livable.
- **The course is shown, not hidden.** The requirement sits at O-Level while
  forward mode collects A-Level subjects, so PathAhead cannot verify it either
  way — and a course removed silently is one a family never gets to argue with.
- **PathAhead now asks, once, in step two:** which mother tongue did you offer
  at O-Level? It is deliberately **not** one of the eight optional fit
  questions and cannot move any score up or down — it is an eligibility fact,
  not a preference. "None of these" is stored as an answer, distinct from
  silence, so a student who answers is never told again that PathAhead needs to
  know.
- Verified and loaded for three NP courses. **Four more are named in `NEXT.md`
  §5a as unverified and still scored blind** — including
  `ntu-linguistics-multilingual-studies`, which is probably taught in English
  *about* languages and must not be given a requirement by pattern-matching its
  name.

### Fixed — three identical scores presented as "your strongest matches"

- The same screenshot showed three cards reading **67/100** with the identical
  one-line reason. That is ISSUES_v0.2.md §A repeating on the fit axis: no
  discrimination, dressed as a ranking.
- The summary is now withheld unless the top three are genuinely
  distinguishable — not just distinct scores across the pack, but different
  *lead reasons* between the three. The first version of the guard checked
  scores alone and let three courses tied at 100 straight through; the UI test
  caught it.
- When it is withheld, the page says why and what would change it, rather than
  showing three arbitrary cards.

### Changed — the page is warm now, and that is a decision about tone

- **The accent was a cool teal (`#1d4d4f`) on grey-leaning paper.** It read
  clinical. A page that tells a seventeen-year-old where their life might go
  should not feel like a bank statement. Everything now sits on a warm axis:
  oat paper, a brown-black rather than a neutral "black", and a burnt
  terracotta accent (`#a8481b`) with moss, amber and plum alongside it.
- **Shadows are tinted brown, not black.** A neutral shadow over warm paper is
  the fastest way to make a warm palette look muddy.
- **Contrast is enforced, in both modes, against the surface each colour is
  actually used on.** `--ink-3` had to be darkened twice: `#8a7a6b` measured
  4.04:1 on the card, and `#7d6d5e` still measured 4.25:1 on the *sunk* tiles,
  which is exactly where the axis labels sit. Checking against the card alone
  would have passed a value that fails where it is used. Warm palettes drift
  pale, and the drift is invisible to whoever makes the change, so the floor is
  now a test rather than an intention.
- **A second test asserts the palette stays warm** — red channel ahead of blue
  on the accent and all three paper surfaces. Swinging back to a blue-green is
  a design decision that should be made out loud, not by editing one hex.
- Steps are numbered with a filled counter, so the shape of the task is visible
  before any of it is read. Each result bucket carries a spine in its own
  colour, which is what tells a reader which verdict they are still inside
  after scrolling through some of 296 courses. A selected chip is *filled*
  rather than tinted — across twelve chips a tint reads as "maybe".
- The disclosure triangle and the timeline dots are drawn shapes rather than
  text glyphs, which is also what fixes their rendering in print (§G4).
- Native `select` arrows are drawn as CSS chevrons, fixing the scribbles §G5
  reported in the printed PDF.

### Fixed — the printed page was losing the thing it was printed for

- **`@media print` no longer hides every `button`.** That one rule was behind
  ISSUES_v0.2.md §C and §D: chips, segmented answers, the remove controls and
  the whole per-factor derivation are buttons or sit behind one, so the
  printout came out as a bare "23 / 100" with no reasoning and no visible
  answers — the exact gap that started this work. The rule now is that an
  **action** disappears and an **answer** prints: a verb like "Clear" is noise
  on paper, a chosen option prints as static text, and an unanswered group says
  "— not answered" rather than leaving a silent blank.
- **Collapsed disclosures are opened before printing and restored after.** CSS
  cannot reopen a closed `<details>`; only the element can. Safari fires
  neither `beforeprint` nor `afterprint`, so a `matchMedia("print")` fallback
  does the same job.
- **Printing expands every bucket.** A printout that silently stopped at ten
  courses would be a different document from the one on screen, with no way for
  the reader to tell.

### Fixed — copy that did not add up

- **"Your 60 against CCC/C–AAB/B" is gone** (§G1). A point total set against
  letter grades is incoherent; the card now leads with the student's own
  profile — "Your AAA (60 points) against CCC/C–AAB/B" — because the letters
  are what a family recognises and the number is the arithmetic behind them.
- **Two maxima now say which is which** (§G2). "70 out of 70" beside "PathAhead
  uses 60" explained nothing; the note names what each number is *for*.
- **General Paper is no longer offered as a level and then asked for as a
  subject** (§G3), which produced a row reading "General Paper / General Paper".
  Mother Tongue deliberately stays a level, because which language you took is
  a real question.
- **Stacked grade rows keep their labels** (§F). Below 44rem `thead` is hidden,
  which left three unlabelled boxes with no way to tell level from subject from
  grade. Two conflicting media queries were also leaking the mobile layout on to
  desktop.

### Added — the list is navigable at 296 courses

- **Each bucket shows ten and offers the rest** (§F). At 21 courses the wall of
  cards was tiring; at 296 it is unusable. Because the order is the student's
  own stated preferences, the ones shown first are the ones they asked for —
  never the most selective.
- **The shortlist is visible from the start** (§H), saying what it is for.
  It previously appeared only once something was in it, so nothing ever invited
  anyone to add the first course and the feature went undiscovered.
- **How many optional questions are answered is stated**, framed as what one
  more would unlock and never as a nag — every one of them is optional and a
  blank answer is a valid one.
- **Headroom above the floor of last year's intake is now shown.** The engine
  has returned it since the §A fix and nothing displayed it. It is the figure
  that still discriminates where published profiles saturate — 18 of 21 NUS
  courses share a p90 of 60.
- **"description is PathAhead's own, not the institution's" is said once**,
  above the list, instead of on all 296 cards. At that volume a caveat stops
  being read and becomes wallpaper.

### Added — SIT fees, and a fee model that does not flatten how they are charged

- **36 of 40 SIT courses now carry a cost.** `outcomes with a fee figure` goes
  from 75 to 111.
- **`fee_basis: per_credit`.** SIT charges per **credit unit**, not per year,
  and states that fees are payable while candidature is active, derived each
  trimester from the modules actually registered. Dividing a programme total by
  a nominal number of years would have produced a figure that looked exactly
  like NUS's, was never published, and would be wrong for any student taking a
  lighter or heavier load — which is the whole point of charging that way.
  `annual_fee_*` stays empty and `total_for()` multiplies credits by rate the
  way SIT does. The loader **refuses** a per-credit block carrying an annual fee.
- **`fee_note` records a gap that is a decision.** SIT lists Civil Engineering
  and Nursing twice, at different credit loads and different rates, and this
  pack does not record which partner each course is with. Four courses are left
  without a figure and carry the reason, so the absence defends itself instead
  of inviting a later session to fill it in from the nearest plausible number.
- Health's fee count used `annual_fee_citizen`, which would have reported every
  SIT course as feeless when the full programme cost is known.

### Added — polytechnic diplomas, and a third kind of published evidence

- **134 → 296 courses; 6 → 10 of 11 institutions.** Nanyang (39) and Ngee Ann
  (41) come from data.gov.sg under the Singapore Open Data Licence v1.0, each
  with three separate admissions exercises; Temasek (41) and Republic (41) come
  from their own published tables, each with the current exercise only.
  Singapore Polytechnic is the last one left — it publishes per course page,
  and `NEXT.md` §4b records the three shortcuts already ruled out.
- **What each institution publishes is recorded, not normalised.** NP and RP
  state an ELR2B2 *type* per course (A/B/C/D differ in which subjects count as
  relevant); NYP and TP do not. Where a type is published it goes into the
  basis; where it is not, the basis stays the generic "net ELR2B2" rather than
  inventing a letter. RP's asterisk for courses with vacancies remaining after
  JAE posting is carried too, with RP's own stated appeal condition.
- **Polytechnic diplomas appear in the same list as degrees**, marked as a
  different route. Showing them only after a student "misses" a university
  range would teach exactly the ranking this project refuses to teach.
- **`statistic` on `GradeBand`: `p10_p90` or `min_max`.** The polytechnics
  publish the net ELR2B2 aggregate of the *lowest and highest ranked student
  admitted* — the entire cohort. A university's 10th-90th percentile cuts both
  tails off by construction, so the polytechnic range is necessarily wider from
  the same intake. Storing one as the other and saying nothing would have made
  every polytechnic course read as far less selective than it is. NYP Nursing
  spans 3 to 28 across three years because one admitted student sat at 28.
  `assess_band()` now raises rather than describe a `min_max` in percentile
  words, and `STATISTIC_WORDS` holds the two vocabularies apart.
- **Comparability generalised from `BandedProfile` to any published figure.**
  It was never a property of the banded shape; it is a property of the claim.
  `GradeBand` now carries `scale` and `comparable`, and `forward` routes an
  incomparable band to `assess_published_on_another_basis()` — which has its
  own copy, because the existing PUBLISHED_ON_ANOTHER_BASIS text says "this
  university" and "a scale that no longer matches", and a polytechnic is not a
  university and its scale has not been retired.
- **Three years are kept as three exercises.** `GradeBand.history` sits beside
  the band and is never merged into it: a union of three min-max ranges is a
  figure nobody published, and it would widen every year, making courses look
  less selective the longer PathAhead ran. `years_covered` and `years_label`
  travel to the card, so a one-year figure and a three-year one cannot render
  identically.

### Fixed — a comparison that would have been confidently wrong

- **An A-Level score is never placed against an ELR2B2 O-Level aggregate.** The
  reason runs deeper than units. Temasek Polytechnic's own admissions guide
  sets it out: through JAE an A-Level holder is admitted on their *GCE O-Level*
  results, and through the Direct Admissions Exercise they enter a shortened 2
  or 2.5-year diploma assessed on "academic results and/or interview/test" with
  no published aggregate at all. There is no route under which that number is
  the applicant's own, so no arithmetic makes the comparison valid. A student
  with AAA would otherwise have cleared all 80 polytechnic ranges at once —
  the same failure family as the retired-UAS bug, and as ISSUES_v0.2.md §A.
- **The coverage gate names all five polytechnics individually.** It previously
  held the literal string `"Polytechnic"`, which no institution is called, so
  it could never be satisfied — accidentally safe. A family flag that any one
  polytechnic satisfied would have lifted PREVIEW with four still missing.
- **The card no longer prints "Your 60 against 3–28".** Both the results card
  and the compare table name the unit and say the figure is not being compared.
- **`check_ui.mjs` no longer asserts that the first card is an NUS card**,
  which quietly encoded a sort order into a test about labelling. It now checks
  every card, and a new check reads a polytechnic card end to end.
- The `other-autonomous-universities` route claimed PathAhead held figures for
  NUS only. It has held all six since the previous release.

### Added — SUTD, SIT and SUSS, and a second kind of published profile

- **77 → 134 courses; 3 → 6 institutions.** Polytechnics are now the only gap
  before `fit scoring` can stop saying PREVIEW.
- **`BandedProfile` beside `GradeBand`.** Three universities publish the share
  of applicants in each score band who got through a stage, which is a
  different claim from a 10th-90th percentile range and is now held as one.
  The loader refuses any course carrying both shapes.
- **`assess_banded()` beside `assess_band()`**, returning the same vocabulary
  of named buckets so a reader can compare two courses without the data
  conflating them. Mirrored in the browser engine.
- **A new verdict: "Published, but on a different scale".** SUSS and SIT both
  publish against the retired 90-point UAS while the AY2026 score is out of 70.
  Their bands are shown; the comparison is withheld, with the reason said
  plainly. A tool that had quietly compared the two would have been wrong in a
  way nobody would have noticed.
- **SUSS's two stages are kept as two.** Clearing the grade band gets you an
  interview, not a place — SUSS shortlisted 72.6% of the top A-Level band for
  Psychology and offered 18.7%. The engine leads with the offer.
- **Censored figures stay censored.** "Below 5%" is carried verbatim rather
  than being given an invented midpoint.
- **SUTD carries no band at all**, because SUTD publishes none — its subject
  profile is an overlay, and every SUTD entry records that the pillar is chosen
  after a common first year.
- Health coverage now separates `outcomes with a banded profile`, `on a retired
  scale` and `outcomes with no profile`, so a different publishing shape is not
  reported as a hole in the pack.
- Sources `suss-igp-2026`, `sit-igp-2025`, `sutd-igp-2026`.

### Fixed

- `_assess_outcome` fell back to the polytechnic pool when a course had no
  A-Level figures, comparing a score out of 70 against a GPA out of 4.00. There
  is now no fallback between pools at all.

### Not added, on purpose

- **SIT's salary figures.** SIT publishes a bare median with no quartiles, and
  PathAhead shows a range or nothing. The employment rate is loaded for the 30
  programmes that have one.
- **SIT's A-Level percentages**, which its own footnote says are aggregated
  across an academic cluster rather than a programme.


### Added — NTU and SMU tuition fees

- **Fee coverage: 21 → 75 of 77 courses.** All four NTU bands (general,
  Accountancy/Business, Medicine, Renaissance Engineering) and both SMU bands
  (Law, everything else), each with the four published subsidised tiers, the
  duration, and the tuition-grant bond. Figures transcribed from the AY2026
  tables and cross-checked against AY2025, which has the identical structure.
- **Durations sourced, not assumed.** From the period-of-candidature table in
  NTU's Academic Handbook (Cohort AY2025-26, §3.2). It turns out **Accountancy
  and Business are three-year programmes**, so their total is SGD 28,500, not
  the SGD 38,000 a four-year default would have produced.
- **Fee coverage in the health report** — `outcomes with a fee figure` and
  `outcomes without a fee figure`, so the gap is visible on every run.
- Sources `ntu-fees`, `smu-fees`, `ntu-candidature`.

### Not added, on purpose

- **NTU's non-subsidised rate for the general band.** NTU publishes two figures
  — SGD 40,600 lab-based, SGD 36,350 non-lab-based — and no mapping from
  programme to cluster. The field is left empty and both figures are named in
  the note, rather than PathAhead inventing a classification the university
  withheld; guessing wrong is roughly SGD 17,000 across four years for a family
  paying non-subsidised fees.
- **The two NIE education programmes** (BA/BSc in an Academic Discipline and in
  Education) carry no cost block, because no published normal candidature could
  be found for them. An annual fee with no duration is not a usable number.

### Added — tests

- `test_ntus_lab_split_is_left_empty_rather_than_guessed` — the deliberate gap
  stays deliberate, and the note keeps naming both figures.
- `test_ntu_accountancy_and_business_stay_three_year_programmes`.
- `test_a_course_with_no_fee_figure_says_so_rather_than_showing_zero` — an
  absent fee must never render as a zero, which reads as free.

---

## [0.2.0] — 2026-08-02

The input set was too thin, there was no reasoning, and the interface was
generic. This release addresses all three, and adds the outcome data families
actually ask about. Written up in [DESIGN_REVIEW_2.md](DESIGN_REVIEW_2.md).

### Added — the second axis

- **Fit scoring, 0–100, fully derived.** Every point traces back to something
  the student typed: *"+25 this course builds on computing and mathematics,
  which you said you enjoy"*, *"−0 you prefer team work; this course is mostly
  individual"*. Reasons are ordered strongest-first, and the confidence note
  says how many questions the score rests on.
- **The two axes are never blended.** Fit is scored because it is computed from
  the student's own answers. Evidence stays a named bucket and a published
  range, because scoring it would be predicting an admissions committee.
- **A coverage gate, enforced.** With one university loaded, ranking would be
  misinformation with a progress bar. Fit therefore runs in **preview**, says
  so, and CI forbids the word "best" until the pack covers all six autonomous
  universities and the polytechnics.
- **No answers, no score** — an empty profile returns "not enough to judge",
  never a misleading 50.

### Added — richer input

- `StudentProfile`: interests (RIASEC, six taps), which subjects they actually
  *enjoy* as distinct from score well in, preferred assessment style, working
  style, priorities, National Service, cost sensitivity, willingness to sit
  interviews, and a free-text goal. Every field optional and skippable.
- **The goal field is honest about doing nothing.** With no model running,
  keyword-matching free text would produce confident nonsense, so PathAhead
  reflects the sentence back beside the options instead of pretending to
  interpret it — and says exactly that on screen.

### Added — outcome data

- **Graduate Employment Survey figures** from data.gov.sg under the Singapore
  Open Data Licence: employment rate, and gross monthly salary as a **25th–75th
  percentile range with the median**, never a bare number. 12 of 21 courses
  have a 1:1 match; the other 9 explain *why* they do not rather than showing
  nothing — Medicine and Pharmacy because graduates enter training years,
  Engineering because it is common-entry and the survey reports nine separate
  degrees.
- **Salary is never a sort key.** It enters fit only if the student says
  earnings matter, and then the reasoning says so.
- Cost, including the **MOE Tuition Grant service bond**, surfaced as an
  overlay rather than fine print.
- **Flexibility** — "can I change my mind?" — per course: late major
  declaration, common first year, what it keeps open and what it forecloses.

### Added — the calendar

- **A personalised timeline** from the resolved cohort: results, application
  windows, interview season, offers, acceptance deadline, open house. Every
  date marked approximate and linked to the official page.
- **National Service is modelled.** Apply, defer, serve, start about two years
  later — with a note that the salary figures on screen describe people who
  graduated years earlier.
- Calendar export (`.ics`), from both the CLI and the browser.

### Added — interface

- **Complete visual rebuild.** Warm paper, a serif for reading and a sans for
  checking, a real type scale, an SVG score dial, two-axis result cards,
  timeline, shortlist and a printable side-by-side comparison.
- **Subject type-ahead** — a full ARIA combobox with keyboard navigation, that
  understands what people actually type ("chem", "econs", "further maths").
- New CLI commands: `pathahead fit` and `pathahead timeline`.

### Changed

- `Fact` gains a `basis` field: **official** or **editorial**. Course
  characterisations are opinions, render differently, never mix with published
  figures, and carry an invitation to disagree. The health gate's confidence
  floor applies only to official claims — grading an opinion on "confidence"
  would be a category error.
- Data Health reports coverage, editorial counts, and fit preview status.

### Fixed

- **Cross-engine parity for fit.** Fit now exists in Python and JavaScript, so
  it gets golden fixtures too. The check immediately caught two real
  divergences: Python's banker's rounding versus JavaScript's round-half-up
  (`round(6.25, 1)` → 6.2 vs 6.3), and a 15.5 score becoming 15 in the CLI and
  16 on screen. Both fixed with explicit half-away-from-zero helpers.
- **An invented date was removed rather than downgraded.** A draft carried a
  guessed "appeal window" milestone; the health gate rejected it for being
  below the confidence floor. A tool that refuses to show an invented cut-off
  must equally refuse to show an invented date.

### Known gaps, stated rather than hidden

- NTU, SMU, SUTD, SIT and SUSS grade profiles — NTU publishes as PDF only.
  Until these land, fit stays in preview.
- Per-course tuition fees; the bond is surfaced, the figures are linked.
- PSLE and O-Level/SEC packs.

---

## [0.1.1] — 2026-08-02

Fixes found on the first real run, on Windows.

### Fixed

- **The launcher window no longer prints a traceback when a browser tab is
  reloaded or closed.** `ConnectionAbortedError` (WinError 10053) and its
  siblings are a browser hanging up mid-transfer, not a fault — they are now
  swallowed silently. Anything else is reported as one readable line instead of
  a stack. A parent is told to leave that window open; what appears in it is
  part of the product.
- **The local server is now threaded.** Previously a single stalled connection
  could freeze the whole app.
- **A busy port is no longer fatal.** If 8902 is taken — usually a PathAhead
  window already open — it steps up to the next free port and says so, rather
  than failing with a socket error.
- **Startup messages are flushed immediately**, so they appear even when the
  launcher's output is redirected to a file.

### Added

- `X-Frame-Options: DENY` on locally served pages.
- `tests/test_serve.py` — 15 tests covering disconnect classification, the
  security headers, loopback-only binding, silence about what was requested,
  threading under a stalled client, and a live reproduction of the exact
  mid-transfer abort that caused this release.

---

## [0.1.0] — 2026-08-02

First working version. A-Level → university for Singapore, end to end.

### Engine

- Pathway graph: `Stage`, `Transition`, `Outcome`, `Prerequisite`, `Route`,
  `Cohort`, and the `Fact` envelope that wraps every number with its year,
  source, licence, confidence and expiry date.
- Three scoring rule kinds, each emitting a full derivation trace rather than a
  bare value:
  - `weighted_best_n_with_substitution` — Singapore's 70-point University
    Admission Score
  - `lowest_sum` — the PSLE shape (AL1–AL8, 4–32, lower is better)
  - `required_plus_best_n` — L1R5, the incoming L1R4, and ELR2B2
- **Cohort routing as a core concept.** "What year is your child in now?"
  resolves deterministically to a stage, exam year, admission year and rule
  version, and is read back in plain words. A cohort outside the loaded rules
  raises with advice rather than scoring under a formula that does not apply.
- **Eligibility and competitiveness are separated.** Results come back in named
  buckets — *meets the stated requirement*, *at or above / within / below last
  year's range*, *not enough verified data* — never a probability or a verdict.
- **Backward mode with `MIN_ROUTES = 3`**, enforced in the engine. A plan is
  never a single required score; where the pack cannot supply three routes with
  at least one non-direct, it says so and points at a counsellor.
- Tier-0 explanations built from the trace. No model, no key, no network.
- `guardrail.py`: every number in AI-generated prose must trace back to the
  computed result, or the whole narration is discarded in favour of the
  deterministic template.
- `health.py`: Data Health as a **CI gate**, not only a report.
- `freshness.py`: visible data age, per-field staleness, and an update check
  that sends no identifiers and fails silently offline.

### Data — `sg-2026.1`

- Singapore pack: A-Level → university under the 70-point UAS.
- 21 NUS programmes with AY2025/2026 grade profiles and intake figures, from
  the NUS Office of Admissions publication (high confidence).
- **Handles the discontinuity that every other calculator ignores:** NUS states
  no grade profile exists yet on the 70-point basis. PathAhead computes the
  70-point score *and* a separate 3-H2 figure that is actually comparable to
  the published profiles, and explains on screen why they differ.
- Five routes into a university course, including polytechnic-to-degree,
  aptitude-based admission, other universities, and retake/appeal.
- Grade-point table marked **medium confidence**, with the reason recorded in
  the source note — pending primary confirmation.

### Apps

- **Browser build** (`web/index.html`) — one self-contained file, no framework,
  no external resources, no storage. Serves as both the zero-install web
  version and the local desktop app, so there is only one artifact to test.
- **CLI** — `levels`, `courses`, `score`, `explore`, `plan`, `whatif`,
  `health`, `build`, `serve`. Errors are a sentence plus advice, never a
  traceback.
- **Installers** for Windows, macOS and Linux. About three minutes, roughly
  40 KB, no AI model.

### Engineering

- 80 tests covering arithmetic, traces, cohort routing, pack validation, bundle
  integrity, the health gate, freshness, the safeguards and the AI guardrail.
- **Cross-engine golden check**: shared fixtures replayed through both the
  Python engine and the JavaScript engine extracted from the live HTML file,
  compared value-by-value and step-by-step. Caught a real bug on its first run.
- CI: lint, tests on Python 3.10–3.13, the data health gate, the cross-engine
  check, safeguard greps (no identity fields, no telemetry, no third-party
  resources), and GitHub Pages deployment.
- Weekly maintainer-only source watcher that respects `robots.txt`, stores only
  hashes, and opens an issue rather than editing anything.

### Documentation

- `SAFEGUARDS.md` — PDPA and children's data, source licensing, disclaimers,
  wellbeing safeguards, AI governance, pre-launch checklist.
- `DESIGN_REVIEW.md` — the architecture review that shaped this build.
- `docs/GETTING_STARTED.md`, `docs/PACK_AUTHORING.md`, `docs/DECISIONS.md`,
  `CONTRIBUTING.md`.

### Not in this release

- NTU, SMU, SUTD, SIT and SUSS grade profiles.
- PSLE and O-Level/SEC packs (the rule kinds are implemented and tested; the
  data is not authored).
- Per-programme subject prerequisites (published as annually-changing PDFs;
  PathAhead links rather than copies).
- The optional AI tiers: narrator, results-slip OCR, and the pack copilot.
- Pack signing beyond checksums.

Nothing is published publicly until the portfolio's publication gate clears.

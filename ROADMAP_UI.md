# Roadmap — from one long page to a navigable site

> Requested 2026-08-02. **Not to be started until the data work in
> [NEXT.md](NEXT.md) is done.** The current single page is ugly at 77 courses
> and will be unusable at 200; but a prettier shell around a half-loaded pack
> helps nobody. Data first, then this.

---

## The constraint that shapes everything

PathAhead's install is ~40 KB and three minutes because `web/index.html` is a
**single self-contained file with no build step and no framework**. That one
property gives:

- Tier A (a link on GitHub Pages) and Tier B (the local app) are the *same
  artifact*, so there is no server-only code path that ships untested;
- `tools/check_golden.mjs` can extract the engine from the live HTML and prove
  it agrees with Python;
- a parent can read the source if they want to.

**Any multi-page design that breaks this is the wrong design.** That rules out
React/Vue/Next, and it rules out hand-written separate `.html` files that would
each need their own copy of the engine.

---

## Phase U1 — hash router inside the single file — **DONE 2026-08-03**

Built. `web/index.html` went from 1,995 to 2,327 lines (127 KB), still one
self-contained file with **no build step and no external reference** — checked,
not assumed: `grep -c 'src="http\|<script src'` returns 0.

Eleven routes resolve, plus `#/more` for the mobile overflow and a real
not-found page. Both navigations are generated from one `ROUTES` table, so the
desktop bar and the phone tab bar cannot drift apart — there is a check for
exactly that.

**Three decisions worth carrying forward.**

1. **`#results` kept its old meaning.** It is still hidden until `run()`
   succeeds; what changed is that its cards became separate views. That is why
   all 34 pre-existing DOM checks still pass untouched — the restructure did
   not quietly redefine what they were asserting.
2. **Run-gated routes get a gate, not an error.** Asking for `#/result` before
   answering anything shows "Answer step two first" with a link to the
   questions. The check asserts the words *error*, *invalid* and *failed* do
   not appear: a first-time visitor arriving on a deep link has done nothing
   wrong, and SAFEGUARDS 5.3 applies to the shell as much as to a course card.
3. **`#/course/<id>`, `#/uni/<id>`, `#/fees` and `#/data` are real now, not
   placeholders.** U2 deepens them, but a page that says "coming soon" to a
   parent looking for a fee is worse than one that states what is and is not
   known. `#/uni/<id>` already names its own coverage gap — how many of that
   institution's courses have no fee figure — because honesty about coverage
   belongs on the university page, not in a global banner.

**The privacy rule is enforced twice.** `navigate()` is the only writer of
`location.hash`. One check walks every route with real answers loaded and
asserts no typed value and no query string reaches the URL; a second greps the
source for any `location.hash =` assignment built from `P.`, `S.rows`,
`S.profile`, `S.result`, `goalText` or `readGrades`, so a future edit that
serialises the profile fails the build even on a route the first check does not
walk.

`tools/check_ui.mjs`: **34 → 46 checks.**

### The original plan, for reference

Real URLs, real back button, real shareable links, still one file.

```
#/                    start — cohort, grades, the optional questions
#/result              your score, the derivation, what happens next
#/courses             all courses, filterable
#/course/nus-medicine one course in full          <-- the deep-link that matters
#/uni/ntu             one university
#/fees                fees and funding across universities
#/dates               the calendar
#/routes              ways in that are not the direct one
#/compare             your shortlist, side by side
#/data                sources, licences, health, how to report an error
```

**Navigation.** Persistent top nav on desktop; a bottom tab bar on mobile,
because the thumb is at the bottom of the phone and this is a phone-first
audience. Overflow behind a menu, never the primary routes.

**State.** Grades and profile live in one module-level store, in memory, and
survive route changes without a reload. They are **never** written to disk and
**never** put in the URL.

> **Privacy constraint, non-negotiable.** A URL may identify a *course* or a
> *university*. It may never carry a student's grades, profile or shortlist.
> Shareable links are for "look at this course", not "look at my child". Add a
> CI grep for it, the same way telemetry is already blocked.

**Testing.** `tools/check_ui.mjs` grows a route suite: every route renders,
back/forward works, deep links resolve, state survives navigation, and no route
leaks profile data into `location`.

---

## Phase U2 — the pages that carry the weight — **DONE 2026-08-03**

All three built. `tools/check_ui.mjs`: **46 → 59 checks.**

**`#/course/<id>`** renders the nine sections in the specified order, and a
check asserts the order rather than merely their presence — the order *is* the
design, because it is the order a family asks in. Notable decisions:

- **"⚑ looks wrong" sits on every figure**, not once in the footer, and each
  link pre-fills the issue with the pack version and the field id so a report
  is actionable without the reporter explaining where they were standing
  (SAFEGUARDS 5.7). They are hidden in print — an interactive affordance has no
  meaning on paper — while the citations beside them stay, which is checked.
- **The fit derivation is on the page, not behind a disclosure.** Hiding it
  behind a click then hiding it again in print was ISSUES §C and §D.
- **A missing fee is stated as missing.** A check asserts no course page ever
  renders `$0`, because a blank fee on the cheapest route is the single most
  misleading thing this pack could show.
- **Salary is a range or nothing.** Checked both ways: quartiles shown where
  they exist, and where only a median exists the page says why it shows none.
- **Ways in lists at least three, direct first** (SAFEGUARDS 5.2), and says the
  direct one is first because it is most common, not because it is best.

**`#/uni/<id>`** groups by faculty, lists A–Z within each group, and states its
own coverage gap in the institution's own terms — "a fee figure for 34 of 34
courses" — because honesty about coverage belongs on the page it applies to,
not in a global banner that makes every page equally suspect. A check asserts
the listing is not ordered by selectivity.

**`#/fees`** has the citizenship selector at the top, and treats the tuition
grant as the substance rather than a footnote: it is a subsidy with a condition,
the condition differs by citizenship, and declining it means the non-subsidised
rate. A check asserts the phrase "not a discount" survives. The institution
table is A–Z and a check asserts it is **not** sorted by cost.

The page also names its own worst gap in a warning box: no polytechnic course
carries a fee yet, so on this page the cheaper route looks like the one with no
information. That is stated on the page rather than left for a reader to
misread.

### The original plan, for reference

### `#/course/<id>` — the page this whole project exists for

One course, everything known, in the order a family asks:

1. What it is — the editorial description, labelled as ours
2. Evidence — grade profile, poly GPA, places, with year and source
3. Fit — if they have answered anything, with the full derivation visible
4. Money — fees by citizenship, total, bond, financial aid links
5. Outcomes — GES salary range, employment rate, where graduates go
6. Reversibility — can you change your mind?
7. Ways in — the ≥3 routes, direct one first
8. Dates specific to this course — interview and portfolio windows
9. Every source, linked · "this looks wrong" on every figure

This is the page people will actually share with each other. It should print
to one clean sheet.

### `#/uni/<id>` — one university

Profile, faculties, the fee bands as published, every course grouped by
faculty, and what PathAhead does *not* yet hold for them. Honesty about
coverage belongs on the university page, not buried in a global banner.

### `#/fees` — the page parents open first

Fee comparison across universities and faculties, citizenship selector at the
top, the tuition-grant bond explained properly rather than as a footnote,
financial aid and loan routes, and a plain worked total for a four-year degree.

---

## Phase U3 — density and finding things — **BUILT, DOM WIRING UNVERIFIED**

Filter bar, type-as-you-speak search and card/compact density are in
`#/courses`. Facets: institution, field, interest, assessment style,
interview/portfolio, "can change direction later", and whether a fee figure is
held. **No facet for selectivity or pay**, and the bar says so on screen —
absence that is not explained reads as an omission rather than a decision.

Compact mode is deliberately **not paged**: the point of it is to scan 330
courses at once, so paging it would defeat it.

> **Caveat, recorded honestly.** `tools/check_ui.mjs` could not be run to
> completion when U3 landed: `jsdom` stopped loading in that environment
> (`require('jsdom')` exceeding 40s, via CJS and ESM, with every one of its own
> dependencies loading in under a second and `node -e "1"` at 24ms). So the
> **logic** is verified — `tools/check_filters.mjs` extracts `searchHit` and
> `matchesFilters` verbatim from the shipped HTML and runs them against the real
> pack, 10/10 — but **the wiring from the controls to those functions is not**.
> Run `npm run check:ui` somewhere jsdom works before trusting this phase.

Writing `check_filters.mjs` immediately paid for itself: it failed on
"filters combine", reporting that the search filter had been dropped. It had
not. SP's *Mechatronics & Robotics* matches "engineering" through its **sector**,
not its title — which is deliberate, because someone types "engineering", not
"mechatronics". The assertion was too narrow, not the code. Had the code been
"fixed" to match, searching by field would have been silently removed.

### The original plan, for reference

- **Filter and facet** on `#/courses`: university, faculty, interest area,
  assessment style, extra-assessment required, fee band, flexibility. Never a
  filter on selectivity or pay — those remain information, never sort keys.
- **Search** across course names, codes and aliases, using the same
  type-as-you-speak matching the subject combobox already has.
- **Density modes**: card view for browsing, compact table for scanning 200
  courses, and a print view for the conversation with a form teacher.

---

## Phase U4 — pre-rendered static pages — **DONE 2026-08-03**

`tools/build_static.mjs` emits 342 pages — one per course, one per institution,
a site index, `sitemap.txt` and `robots.txt`. `tools/check_static.mjs` reads the
emitted HTML back and compares it with the pack: **12/12**.

**The gate is implemented, not merely obeyed.** U4's own condition — *"do this
only after the content is right; indexing 77 pages of half-loaded data is worse
than indexing nothing"* — is **not met**: 219 of 330 courses still have no fee
figure. Refusing to build would have left the phase undone; building blind
would have published hundreds of pages with holes. So the gate runs **per page**:

- a course with a published admission range **and** a fee figure → `index, follow`
- anything else → `noindex, follow`, plus a visible line naming what is missing

Today that is **111 indexable, 219 noindex**. Nothing is hidden from a person
who follows a link; what is withheld is the invitation for a search engine to
send a stranger to a page that cannot answer what they searched for. As the
pack fills in, pages flip on their own — `npm run site:report` prints how many
would. The sitemap lists only the 111, because advertising a `noindex` page is
a contradiction a crawler will notice.

Checked: figures match the pack, no page renders `$0` for a fee it does not
hold, salary appears only as a range, pack text is HTML-escaped rather than
injected, pages carry no script and no third-party resource, institution pages
link only to their own courses, and nothing is ordered by selectivity.

### The original plan, for reference

Hash routes are invisible to search engines. Families search. So:
`tools/build_pack.py` grows a static site generator that emits a real
`courses/nus-medicine/index.html` per course, per university and per topic,
using the same templates the router uses, with the interactive app hydrating on
top.

Result: real URLs, indexable pages, works with JavaScript off, still no
framework and still no build step for the *user* — only for the maintainer.

**Do this only after the content is right.** Indexing 77 pages of half-loaded
data is worse than indexing nothing.

---

## Phase U5 — the flows still missing — **DONE 2026-08-03**

All three exist. **None of them asks for a grade before it will speak to you**,
which is the point: the app had exactly one front door and it wanted a
transcript. `tools/check_flows.mjs` — 10/10.

**`#/explore`** — interests only, no grades, no score. Picking a second interest
**narrows** (`every`, not `some`), because a control that widened when you added
a constraint would be lying about what it does; that is pinned by a test. When
nothing matches it says so plainly and blames its own characterisations, not
the person's taste.

**`#/results-day`** — leads with the non-direct routes, never shows a score, and
never asks what the grades were. It says outright that a grade profile
describes one intake in one year and is not a description of the person, and it
points at the ECG counsellor and the admissions office while admitting that on
that particular day PathAhead is the weaker option.

**`#/perspectives`** — the parent and the young person answer the same four
questions separately, then see where they agree and differ. The roadmap
deferred this as "needs real care", so the care is where the harm would be:

- **It never scores, ranks or arbitrates.** A test asserts the output contains
  no score, no percentage, and none of *better*, *worse*, *should*, *correct*,
  *wrong*, *win* or *recommend*. A parent already holds more authority than a
  child in this conversation; a tool that picked a winner would hand them a
  verdict to point at.
- **An answer only one person gave is a DIFFERENCE, not agreement.** The
  tempting shortcut is to skip questions one side left blank, which silently
  turns "we have never discussed this" into "we agree". Pinned by a test.
- Nothing is stored or transmitted; you hand the device over and switch.

### The original plan, for reference

- **`#/explore`** — start from interests, no grades, no destination. The most
  common real state is "I have no idea", and there is still no front door for it.
- **`#/results-day`** — a one-tap entry point for the day it went badly, that
  leads with routes and never with a score.
- **Two perspectives** — parent and child each answer, then see where they
  agree and differ. High value, needs real care, still deliberately deferred.

---

## Sequencing, and what must be true first

```
NEXT.md §1  NTU + SMU fees          ─┐
NEXT.md §2  SUTD/SIT/SUSS band type  ├─ data first, then
NEXT.md §4  polytechnic destinations ─┘
                    │
                    ▼
        U1 router → U2 pages → U3 density → U4 static → U5 flows
```

**Gate before starting U1:** `pathahead health` must show all six universities
plus polytechnics, and `fit scoring` must read `complete` rather than
`PREVIEW`. A navigable site built over a preview-quality pack would make the
gaps harder to see, not easier.

---

## What must not change, whatever the shell looks like

Every one of these has a failing test behind it. They are not style
preferences.

1. Fit is scored; evidence is never scored. The two axes are never blended.
2. Our data gaps never cost the student points.
3. Answering more about yourself never lowers your score.
4. Backward mode returns at least three routes, one non-direct.
5. Nothing is ordered by selectivity or by pay.
6. No wording judges the student.
7. No identity fields, no telemetry, no third-party resources — and now, no
   personal data in a URL.
8. Both engines agree, checked in CI against shared fixtures.

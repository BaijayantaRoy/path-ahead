# v0.2 — what is actually wrong

Findings from the 23-page PDF of a real session, verified against the code
where possible. Ordered by severity, not by how easy they are to fix.

Two of these mean **the two axes I built this release around are both
non-functional in practice.** They are not polish items.

---

## A. ~~Blocking~~ FIXED 2026-08-02 — the evidence axis had almost no resolution

**Symptom.** A student with AAA/A gets *"At or above last year's range"* for
**all 21 courses**. Medicine, Dentistry and Landscape Architecture are rendered
identically. One bucket, 21 cards, no discrimination whatsoever.

**Verified:**

```
distinct (p10, p90) pairs across 21 courses : 6
p90 values                                  : {60.0: 18, 57.5: 2, 55.0: 1}
student with AAA/A -> comparison score      : 60.0  (the maximum)
buckets: at_or_above_range 21 · within_range 0 · below_range 0
```

**Root cause — mine.** I converted published grade profiles (`AAA/A`, `AAB/B`,
`CCC/C`) into a 0–60 point sum. Because A = 20, every profile whose three H2
grades are AAA collapses to exactly 60 — that is **18 of 21 courses**. The
entire competitive top of the distribution maps to a single value, so anyone
with three As is "at or above" everything and anyone with AAB is below all of
it. The scale has six distinct values total.

Grade profiles are **ordinal strings**, and I flattened them into a number that
looks quantitative and isn't. The three-bucket design was sound; the encoding
underneath it destroyed the signal.

**FIXED.** The cause was subtler than "the encoding is wrong". A *degenerate*
band — where the 10th and 90th percentile are the same profile — means the
entire admitted cohort shared one profile. Matching it exactly is a genuinely
different situation from clearing a range, and collapsing the two is what put
everything in one bucket.

Three buckets now exist where there was one:

| | |
|---|---|
| **Above last year's range** | clear of the whole band |
| **At the top of last year's range** | level with the 90th percentile of a real spread |
| **Level with last year's profile** | everyone admitted had exactly this, so there is no headroom — and the non-grade parts of the decision carry more weight here than anywhere |

A top student across 77 courses now gets **9 / 48 / 20** instead of 77-in-one.
Medicine reads "level with the profile"; Landscape Architecture reads "above
the range" — same grades, two situations a family should read differently.
`assess_band` also returns headroom above the floor, which is the figure that
still discriminates where the published profiles saturate.

Guarded by `test_the_evidence_axis_does_not_collapse_into_one_bucket` and
`test_a_saturated_profile_reads_differently_from_a_wide_one`.

**Original diagnosis, for the record.** Compare grade profiles as profiles — position within the
letter distribution, or a much finer basis (individual subject grades against
the profile's, with distance) — plus at minimum a "how close to the top of the
range" indicator so AAA-for-Medicine and AAA-for-Landscape-Architecture read
differently.

---

## B. Blocking — fit scoring punishes honesty, and mis-scores subjects

### B1. Naming more of yourself lowers your score

Interest points are `25 × (overlap ÷ how many you picked)`. Verified:

```
interests ('I',)          -> 25.0 / 25    total 67/100
interests ('I','R')       -> 25.0 / 25    total 67/100
interests ('I','R','C')   -> 16.7 / 25    total 50/100
```

A student who names three interests is **penalised** against one who names one.
The denominator should be the course's profile, not the length of the student's
own list. This is indefensible and I should have caught it in the tests — the
existing tests check determinism and traceability but never checked monotonic
behaviour.

### B2. Subject matching is exact-string on codes

```
enjoys ('mathematics',)         -> 8.3 / 25
enjoys ('further-mathematics',) -> 0.0 / 25
```

**Further Mathematics scores zero on every maths-heavy course.** The user's
session enjoyed Further Mathematics, so Computer Science — a course built on
maths — scored **23/100, "weak"**. Any subject not spelled exactly as the
pack's affinity list gets nothing. There is no synonym, parent-subject or
partial-credit handling at all.

### B3. Combined effect: the axis conveys nothing

For the profile in this session, across the whole pack:

```
highest fit anywhere : 49  (Architecture)
range                : 0 – 49
```

**Nothing reaches "moderate".** Every card reads *limited* or *weak*. A student
is told, 21 times, that nothing much suits them. That is worse than showing no
fit score at all — it is actively discouraging, and it is wrong.

---

## C. ~~Serious — the reasoning is hidden~~ FIXED 2026-08-03

**Root cause, and it was one line.** `@media print { header.top,.actions,footer
.links,button,details.disclosure summary {display:none} }`.

`button` hid the chips, the segmented answers, the remove controls and the
action rows. `details.disclosure summary` hid the heading of the derivation.
Together they produced the bare "23 / 100" with no reasoning — and the same
rule is the whole of §D below, which was never isolated because the diagnosis
stopped at "I cannot reconcile this from the PDF alone".

**The rule now is that an ACTION disappears and an ANSWER prints.** A verb
("Clear everything") is noise on paper. A `[aria-pressed=true]` option prints as
static text; an `[aria-pressed=false]` one does not print at all, because an
option nobody chose is not an answer; and a group with nothing chosen prints
"— not answered" rather than a silent blank a reader cannot interpret.

Two things CSS alone could not do, so they are handled in script:

- **A closed `<details>` cannot be reopened by CSS.** The closed state belongs
  to the element. `beforeprint` opens every one and `afterprint` restores them.
  Safari fires neither event, so `matchMedia("print")` is wired as a fallback.
- **Progressive disclosure would have truncated the printout.** Each bucket
  shows ten courses on screen; printing expands all of them first, because a
  printout that silently stopped at ten would be a different document from the
  one on screen with no way to tell.

Guarded by `printing does not hide the answers or the reasoning`, `printing
opens every collapsed disclosure` and `printing shows every course, not just
the first page` in `tools/check_ui.mjs`.

**Original diagnosis, for the record.**

The per-factor derivation — the whole point of this release — sits behind a
collapsed `<details open=false>` labelled "why", and the print stylesheet drops
`details.disclosure summary`. **The printed artefact shows a bare "23 / 100"
with no reasoning at all.** The exact gap that started this work.

At least the top three factors must be visible without interaction, and the
full derivation must survive printing.

---

## D. ~~Serious — two input controls render empty~~ FIXED 2026-08-03

**Candidate (1) was right.** `@media print { button { display:none } }` stripped
every button, which is why the segmented controls showed "nothing but a stray
mark" (the `.seg` border, with its contents gone) while the chips appeared to
survive — the chips that survived were the *selected* ones, whose pressed state
was carried by a background colour the print stylesheet did not remove.

The honest note in the original diagnosis was the useful part: *"Regardless of
which it is, hiding `button` in print is a bug."* That was true, and acting on
it fixed both §C and §D at once. See §C for what replaced the rule.

**Original diagnosis, for the record.**

"How do you do your best work?" and "And do you prefer to work…" show **nothing
but a stray mark**. So 2 of the 8 signals were unanswerable, which is part of
why every fit score was low.

**Honest status: not yet isolated.** I verified in a real DOM (jsdom) that the
buttons *are* created — three in each segment — so it is not a logic fault.
Two candidate causes:

1. `@media print { button { display:none } }` strips every button. That would
   also explain the missing **× remove** buttons and the missing **"Add a
   subject" / "Show me the result" / "Clear"** action rows.
2. A screen-CSS fault specific to `.seg`.

Against (1): the chips are also `<button>` elements and they clearly survived,
with their selected states. I cannot reconcile that from the PDF alone and need
to reproduce it in a real browser on your machine.

**Regardless of which it is, hiding `button` in print is a bug.** This app tells
people to print the page and take it to a form teacher; printing currently
destroys the controls and the answers. Printed output should render each control
as static text showing the chosen value.

---

## E. ~~Structural — fit is computed, then ignored~~ FIXED

Fit now orders within each bucket, with an explicit A-to-Z alternative and a
"Where your answers point" summary above the list. Ranking by stated preference
is permitted; ranking by selectivity or pay is not, and neither is ever a sort
key. Guarded by `results are ordered by match, strongest first`.

**Original diagnosis, for the record.**

I sort alphabetically inside each bucket, deliberately, to avoid ranking by
selectivity. But since every course landed in one bucket (issue A), the output
is **21 alphabetical cards** and the fit score has no effect on what the user
sees first. I computed the thing you asked for and then declined to use it.

Fit should order within a bucket — that is ranking by *stated preference*, not
by prestige, and it is exactly what the safeguard was meant to permit.

---

## F. ~~Density and layout~~ MOSTLY FIXED 2026-08-03

The pack has since grown from 21 courses to 296, which made every row in the
table below worse rather than better. What changed:

| Was | Now |
|---|---|
| 21 near-identical cards, no top-N or collapse | Each bucket shows **ten** and offers "Show all N". Because the order is the student's own stated preferences, the ten shown are the ones they asked for — never the most selective. Printing expands everything |
| *"description is PathAhead's own"* ×21 | Said **once**, above the list. At 296 cards a caveat stops being read and becomes wallpaper. The per-card tag is now the two-word "our description" |
| Bucket name in both heading and every badge | Still both — the badge is what survives when a card is read on its own, e.g. on the shortlist |
| No labels in stacked mode | Every cell carries `data-label`, rendered above it below 44rem. Two conflicting media queries were also leaking the mobile layout on to desktop, which is why the grade rows stacked at full width |
| Poor pagination | `break-inside:avoid` on `li.course`, `break-after:avoid` on headings, link URLs suppressed |

Still open, and cosmetic: the repeated *"based on N of 8 things you told us"*
and the repeated basis string. Both are per-card because both are per-card
facts; neither is wrong, only repetitive.

**Original diagnosis, for the record.**

| | |
|---|---|
| **21 near-identical cards, ~11 pages** | No top-N, no filter, no collapse. An undifferentiated wall |
| **Repetition** | *"description is PathAhead's own"* ×21 · *"based on 5 of 8 things you told us"* ×21 · *"3 H2 grades, out of 60"* ×21 · bucket name in both the section heading and every badge |
| **Label collision** | "FIT — BASED ON WHAT YOU TOLD US" overruns its column; "US" wraps and crowds the number |
| **Grade rows use the mobile layout at desktop width** | Three full-width stacked boxes per subject, ~2 pages for 4 subjects |
| **No labels in stacked mode** | `thead` is hidden, so the rows are three unlabelled boxes — you cannot tell level from subject from grade |
| **Four stacked caveats before the result** | The warnings dominate the answer on the score card |
| **Poor pagination** | Page 1 is ~60% empty, page 3 ~75% empty — `break-inside:avoid` on tall cards |

---

## G. ~~Copy and coherence~~ 1, 2, 3 and 6 FIXED 2026-08-03

1. **FIXED.** The card leads with the student's own profile in the shape the
   universities publish: *"Your AAA (60 points) against CCC/C–AAB/B (2025)"*.
   Letters are what a family recognises; the number is the arithmetic behind
   them. Guarded by `the student's result is not a number set against letter
   grades`.
2. **FIXED.** The note now names what each number is *for* — 70 is the
   admission score universities use, 60 is only for reading last year's
   profiles, and no profile exists yet on the new basis.
3. **FIXED.** General Paper is a subject, not a level: choosing it pins the row
   and prints the name once instead of producing "General Paper / General
   Paper". Mother Tongue deliberately stays a level, because which language you
   took is a real question. Guarded by `General Paper is not offered as both a
   level and a subject`.
6. **FIXED** by §F: the coverage warning, the goal reflection and the
   not-a-prediction line still exist but the list they precede is now paged, so
   they no longer dominate the first screen of results.

4 and 5 are unfixed and are **PDF rendering artefacts** rather than markup
faults — list bullets rendering as dark squares and native `select` arrows
rendering as scribbles are the print pipeline's doing, not the page's.

**Original list, for the record.**

1. **"Your 60 against CCC/C–AAB/B (2025)"** — a number compared to letter
   grades. Incoherent. Should read *"your AAA against CCC–AAB"*.
2. **"PathAhead uses 60 — your 3 best H2 grades, out of 60"** sits next to
   **"70 out of 70"**. Two maxima, both maxed, no clarity about which matters.
3. **"General Paper" and "Mother Tongue" are offered as *levels***, producing a
   row reading **"General Paper / General Paper"**. They are subjects; the
   levels are H1/H2/H3. Conceptually wrong and visibly silly.
4. Timeline bullets render as small dark squares rather than dots.
5. Native select arrows render as scribbles in the PDF.
6. Three stacked notice boxes (coverage warning, goal reflection,
   not-a-prediction) before the first course.

---

## H. ~~Missing~~ MOSTLY ADDRESSED

- ~~No sort by fit~~ — sorting by match is the default, with A-to-Z alongside.
  **Sorting or filtering by salary or employment rate is deliberately not
  built** and should not be proposed again: SAFEGUARDS.md 5.1 forbids ranking
  by pay or selectivity, and a filter is a ranking with extra steps. Filtering
  by *institution* or *field* is a legitimate future addition and is not the
  same thing.
- ~~No "your strongest matches" summary~~ — "Where your answers point" sits
  above the list.
- ~~The shortlist is undiscoverable~~ — the card is now visible from the start
  with an empty state saying what it is for, instead of appearing only after
  something has been added to it. Guarded by `the shortlist invites a first
  course instead of hiding`.
- ~~No indication of how many optional questions are answered~~ — stated above
  the button, framed as what one more would unlock. Never as a nag: every one
  is optional and a blank answer is valid. The test asserts the copy contains
  no "must", "should", "need to" or "required".

**Original list, for the record.**

- No sort or filter by fit, salary, employment rate or flexibility.
- No "your strongest matches" summary at the top of the options list.
- The shortlist/compare feature is undiscoverable — it only appears once you
  have added something, and nothing invites you to.
- No indication of how many optional questions are answered, or what answering
  one more would unlock.

---

## What I got wrong, in one line each

- I encoded an **ordinal** grade profile as a **cardinal** score and lost the
  signal (A).
- I normalised interest matching by the **user's** input length instead of the
  **course's** profile (B1).
- I matched subjects by **exact code equality** with no synonyms (B2).
- I hid the derivation behind a disclosure and then hid it again in print (C, D).
- I wrote tests for determinism and traceability but **none for whether the
  scores were meaningful** — no monotonicity test, no spread test, no test that
  a realistic profile produces discrimination across the pack. All 128 tests
  pass on a system that ranks 21 courses identically.

That last one is the real lesson: the test suite checks that the machinery is
consistent, not that the output is useful.

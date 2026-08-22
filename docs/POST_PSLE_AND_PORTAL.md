# PathAhead — the path after PSLE, the SEC cutover, and the three-door portal

> **Status: design decision document. Nothing here is built yet.**
> Written 2026-08-09. Companion to [SAFEGUARDS.md](../SAFEGUARDS.md),
> [ROADMAP.md](../ROADMAP.md) Phases B and C, and [ROADMAP_UI.md](../ROADMAP_UI.md).
>
> This document does four things, in this order, because the later ones depend
> on the earlier ones:
>
> 1. **§1–§3** — what is actually true about the post-PSLE and post-secondary
>    pathways, verified against primary sources on 2026-08-09.
> 2. **§4** — the portal: three separate landing pages, one shell, and how the
>    existing routes fold in without breaking the 265-page static site.
> 3. **§5** — the data-capture model, including the postal-code question and
>    the PDPA position that has to be written down before a single field ships.
> 4. **§6** — the logo, and what was ruled out before drawing began.
>
> **§7** lists the new safeguards this work creates. Every one of them needs a
> failing test before the feature that would break it exists — that is the
> house rule, and this document is where the debt is recorded.

---

## 0. The one-paragraph version

PathAhead today answers one question: *A-Level → which university course.* The
work described here adds the other two Singapore transitions, and they are not
the same product wearing a different hat. **Post-PSLE the user is a parent and
the subject is a twelve-year-old**, which changes the tone, the legal posture
and the questions that may be asked. **Post-secondary is mid-cutover**: the
2026 Secondary 4 cohort is the last to sit the GCE O-Level, and everyone behind
them sits the Secondary Education Certificate under a different set of
admission formulas — formulas that share names and numbers with the old ones
while meaning different things. A tool that treats the three stages as one form
with a different dropdown will be wrong in the two places it most matters.
Hence three landing pages, not one.

---

## 1. After PSLE — what is actually true

*All figures in this section verified 2026-08-09 against `moe.gov.sg`. Confidence
`high` unless marked otherwise. Each is a fact, encoded and cited, never MOE's
prose reproduced — per [SAFEGUARDS.md §3b](../SAFEGUARDS.md).*

### 1.1 The score

Four subjects — English, Mother Tongue, Mathematics, Science. Each scored on an
Achievement Level from AL1 to AL8 against **fixed benchmark bands**, not against
the cohort. The PSLE Score is the sum, ranging **4 to 32**, with 4 the best.
Twenty-nine possible scores.

| AL | Raw mark |
|---|---|
| 1 | ≥ 90 |
| 2 | 85–89 |
| 3 | 80–84 |
| 4 | 75–79 |
| 5 | 65–74 |
| 6 | 45–64 |
| 7 | 20–44 |
| 8 | < 20 |

The bands are deliberately uneven: MOE states it expects slightly under half the
cohort to score AL1–AL4, so the upper bands are narrower. **This is a fact worth
surfacing in the UI**, because a parent reading "AL5 = 65–74" without it will
assume a 20-mark band means the child is far from AL4, when the distribution
says otherwise.

**Foundation-level subjects** are graded AL A–C, and mapped for S1 posting:

| Foundation grade | Raw mark | Maps to Standard AL |
|---|---|---|
| A | 75–100 | 6 |
| B | 30–74 | 7 |
| C | < 30 | 8 |

**MTL-exempted students** are assigned an MTL score between AL6 and AL8, derived
by reference to peers with similar English/Maths/Science results, so that every
child has a four-subject score for posting.

This fits `engine/rules/lowest_sum.py` exactly as written — sum all, lower is
better. **Phase B is pack-authoring, not engine work**, which is what
[ROADMAP.md §1](../ROADMAP.md) predicted. The one engine addition needed is the
Foundation and exemption **mapping layer** before the sum.

### 1.2 Posting Groups — an eligibility gate, not a score

| PSLE Score | Posting Group | Indicative level for most subjects at start of S1 |
|---|---|---|
| 4–20 | 3 | G3 |
| 21–22 | **2 or 3** | G2 or G3 |
| 23–24 | 2 | G2 |
| 25 | **1 or 2** | G1 or G2 |
| 26–30, *with AL7 or better in English **and** Mathematics* | 1 | G1 |

Four rules travel with that table and all four are load-bearing in the UI:

- Eligible for one group → no choice.
- Eligible for two → pick one, and **it applies to all six school choices**.
  You cannot mix posting groups across your list.
- Submit nothing → assigned the **more** academically demanding group.
- PG1 and PG2 students may take English, Maths, Science and/or MTL at a more
  demanding level if they did well in them at PSLE. Full Subject-Based Banding
  means the posting group sets a starting point, not a ceiling.

**The gap in that table is the most important thing on this page.** A score of
31 or 32, or 26–30 without AL7 in both English and Maths, does not appear. Those
children do not qualify for a secondary course and are served by **NorthLight
School** and **Assumption Pathway School**, graduating with an ITE Skills
Certificate at the end of Year 4. **Crest Secondary** and **Spectra Secondary**
serve students eligible for the most practice-oriented pathway.

A landing page that only speaks to families aiming at a cut-off of 8 fails the
families who need it most. This route gets a **first-class door on the PSLE
landing page**, described in its own terms with its own onward routes — not a
consolation panel below the fold. Precedent already exists: `#/results-day` was
built for exactly this at A-Level.

> ⚠️ **Confidence `medium` on the boundary itself.** MOE's posting-group page
> states the table above and does not state what happens outside it; the
> school-types page describes NorthLight and Assumption Pathway as being for
> students "who do not qualify for a secondary course of education after the
> PSLE" without naming a score. PathAhead must therefore say *"a place is
> offered through a different route"* and link, rather than assert a threshold
> nobody published.

### 1.3 S1 Posting — and what the address does and does not do

Six school choices, ranked. Posting is by PSLE score, then choice order, then
vacancies. Better scores are considered first.

**Tie-breakers, in order** — used only when two students with the same score
compete for the last place:

1. **Citizenship** — Singapore Citizen, then Permanent Resident, then
   International Student.
2. **Choice order of schools** — the student who ranked it higher gets it.
3. **Computerised balloting.**

> ⚠️ **Two MOE pages disagree, and PathAhead must record both.** The Full SBB
> infographic (`tie-breaker.pdf`) gives the three-step order above. The page at
> `/secondary/s1-posting/results/how-posted` states that choice order does *not*
> give priority — but it is describing the **2020 P6 cohort** and closes by
> saying the process changed from 2021. This is a stale page, not a
> contradiction in policy. Encode the infographic's rule, cite both URLs with
> their dates, and **do not silently pick one** — that is the whole point of
> dated facts with confidence levels.

**Home address is not a tie-breaker at S1 posting.** It matters in exactly two
ways, and neither is an advantage:

- If a student cannot be placed in **any** of their six choices, they are posted
  to the **nearest available school based on the registered address**. MOE
  advises keeping the address current with the primary school by October.
- Travel time — four years of a daily commute — is a real family constraint that
  no admission rule touches.

This finding directly shapes §5. Families routinely confuse this with **P1
registration**, where distance *is* a formal criterion. Saying so explicitly is
one of the more useful sentences the product can write.

**Cut-off points.** SchoolFinder publishes, per school and per posting group,
the PSLE score of the **first and last student posted there last year**. Three
consequences:

- This is a `min_max` statistic — the same shape as the polytechnics' published
  ranges, and it must never be described in percentile words.
  [SAFEGUARDS §4 b2](../SAFEGUARDS.md) already forbids this and
  `engine/buckets.py:assess_band()` already raises. The guard extends to S1
  unchanged.
- COPs fluctuate a few points year on year with each cohort's results and
  choices.
- **Meeting the COP does not guarantee admission** — MOE says so plainly.
  Students who met it were tie-broken out.

**Affiliated schools** publish a separate affiliation range. **SAP schools**
show the Higher Chinese grade of the first and last student admitted, in
brackets — (D), (M), (P) — and students with a pass or better in HCL *and* a
PSLE score of 14 or better get a posting advantage that **applies before the
tie-breakers**.

### 1.4 Everything the score does not decide

These all hang off the PSLE result and none of them is the posting group. They
are the substance of a P6 parent's real question — *what will my child actually
be able to do?* — and no consumer tool collects them in one place.

| Thing | Criterion |
|---|---|
| Higher MTL in secondary | PSLE MTL AL1/AL2, **or** HMTL Distinction/Merit. Schools may admit others with exceptional ability. |
| Foreign Language (French, German, Japanese, Spanish) | PSLE score **≤ 8**. Japanese also needs a pass in Chinese/Higher Chinese. SC/PR, or child of one. |
| Asian Language (Arabic, Bahasa Indonesia) | PSLE score **≤ 24**. Bahasa Indonesia not open to those who offered Malay/Higher Malay. SC/PR, or child of one. |
| Malay / Chinese Special Programme | PSLE score **≤ 24**, and not having offered that language as MTL. |
| SAP posting advantage | HCL Pass/Merit/Distinction **and** PSLE ≤ 14. |

### 1.5 DSA-Sec — the route that closes before the exam

P6 students apply to up to **three school-and-talent-area combinations** on
talent in sports, CCAs and specific academic areas, **before PSLE results
exist**. The 2026 exercise: applications closed 2 June 2026, outcomes from
schools by 28 August 2026, school-choice ranking by 23 October 2026.

The binding term is the one families miss: **a child admitted through DSA-Sec
cannot submit S1 school choices and cannot transfer.** The commitment runs for
the duration of the programme. A tool that shows DSA as simply "another way in"
without that sentence is doing harm.

### 1.6 School types

Government · Government-aided (either may be Autonomous and/or SAP) ·
Independent (two offer the IB Diploma) · **Specialised Independent** — NUS High,
School of Science and Technology, Singapore Sports School, School of the Arts ·
**Specialised** — NorthLight, Assumption Pathway, Crest, Spectra.

> ⚠️ MOE's school-types page was **last updated 1 February 2021** and still uses
> pre-FSBB vocabulary ("Normal (Technical) course"). Encode the school types;
> do **not** encode the stream language. Mark the source `confidence: medium`
> and re-verify before Phase B ships.

---

## 2. The cutover — who sits what, and why it decides everything

This is the single highest-value fact in the whole secondary stage, and it is
answerable from one question a family can always answer: **which year did you
start Secondary 1?**

| Started Sec 1 | Sits | In | Results | Applies through | In |
|---|---|---|---|---|---|
| **2023** | GCE O-Level / N-Level — **the last cohort ever** | Oct–Nov 2026 | Jan 2027 | **JAE** | 2027 |
| **2024** | Secondary Education Certificate | 2027 | Jan 2028 | **PSE** | 2028 |
| **2025 and after** | SEC | 2028+ | | PSE | 2029+ |

From 2027 the GCE N(T), N(A) and O-Level are combined and renamed the
**Singapore-Cambridge Secondary Education Certificate**, jointly awarded by
SEAB, MOE and Cambridge. There is no change in overall examination standards.
Students sit each subject at its own level — G1, G2 or G3 — and receive **one
certificate** listing all of them.

### 2.1 SEC grading, and the mapping that makes aggregates possible

At subject level the grading structures are unchanged from what they replace:

- **G1** — A, B, C, D, E
- **G2** — 1, 2, 3, 4, 5, 6
- **G3** — A1, A2, B3, B4, C5, C6, D7, E8, 9

A certificate is awarded for E8 or better (G3), 5 or better (G2), D or better
(G1).

Grades are mapped **only** when an aggregate must be computed across levels —
ELMAB3 for Year 2 Higher Nitec and the Polytechnic Foundation Programme, ELR2B2
for polytechnic admission:

| G3 | → G2 | | G2 | → G1 |
|---|---|---|---|---|
| A1–B3 | 1 | | 1–3 | A |
| B4–C6 | 2 | | 4 | B |
| D7 | 3 | | 5 | C |
| E8 | 4 | | 6 | D |
| 9 | 5 | | | E |

G3 → G1 goes through G2 in two steps, never directly. This is a clean fit for a
new `mapped_aggregate` rule kind — the mapping table is data, not code.

**Timetable changes that matter to a student's year:** English and Mother Tongue
written papers move to **September**; everything else runs October–November in
one common period; MTL has **one sitting only** across G1/G2/G3 and G3 Higher
MTL; and there is **one common results release in January**, replacing the
December N-Level / January O-Level split.

### 2.2 PSE 2028 — one exercise, new formulas

The Post-Secondary Admissions Exercise replaces the separate JAE, polytechnic
and ITE exercises with **one application** through the Post-Sec Portal, using
Singpass, open for **6 calendar days** from the SEC results release. All
candidates who sat SEC at any level are eligible, including school candidates of
all nationalities and SC/PR private candidates. Applicants may **combine results
from up to two examination years** of SEC, GCE N-/O-Level, or a mix.

**JC and MI** — gross **L1R4**, all subjects at **G3** (an O-Level grade counts
as G3-equivalent):

```
L1R4 = L1 + R1 + R2 + R3 + R4
  L1  G3 English or Higher Mother Tongue
  R1  best Humanities
  R2  best Mathematics or Science
  R3  best Humanities, Mathematics or Science
  R4  any best-scoring subject
```

Threshold: **≤ 16 for JC**, **≤ 20 for MI**. With HMTL, both aggregates are
computed and the better qualifying one is used. A language cannot be counted
twice as both MTL and HMTL. Religious Knowledge is excluded.

Minimum grades: G3 English A1–C6 · one Mathematics (G3 A.Math or Math) A1–D7 ·
MTL at G3 A1–D7, G2 1–5 or G1 A–D · HMTL at G3 A1–E8. Conditional admission
exists for those who miss them.

Bonus points: up to **3** from a combination of types, plus **2** more for
selection into certain JC programmes (which then must be offered at A-Level).
**Net = gross − bonus.**

**Polytechnic** — **ELR2B2 net ≤ 22**; Diploma in Nursing uses ELR2B2-C **≤ 24**.
Plus the course's own minimum entry requirements.

```
ELR2B2 net = EL + R1 + R2 + B1 + B2 − CCA bonus
  EL, R1, R2, B1   G3 grade
  B2               may be TAKEN at G2 or G3, but is always
                   COMPUTED as the G2-equivalent grade
```

The precision matters: it is not "one of five subjects may be at G2". It is that
**B2 is always scored on the G2 scale**, even when the subject was taken at G3 —
a G3 B4 is mapped to G2 grade 2 before it enters the sum. If two G3 subjects are
used for B1 and B2, the better one takes B1 and the other is mapped down. G3
grade 9 and G2 grades 5 and 6 cannot be used at all. O-Level counts as G3,
N(A)-Level as G2.

CCA bonus: **2** points for Excellent / A1–A2, **1** for Good / B3–C6.

The cut-off moved from 26 to 22 *because* B2 is now mapped to a G2 grade —
**it is not a tightening**, and rendering the two years on one axis would say it
was.

**ITE** — 2-Year and 3-Year Higher Nitec courses are applied for through the
same PSE. **ELMAB3**, computed on G2-mapped grades, governs Year 2 Higher Nitec
and the Polytechnic Foundation Programme.

**Talent routes still run before the exams** — DSA-JC, Poly-EAE, ITE-EAE, from
mid-2027. CCA records must be verified by September 2027, because CCA bonus
points feed the net aggregate.

**A fifth year in secondary school** is explicitly named by MOE as an
alternative to progressing. Almost nothing on the market shows it. PathAhead
will.

### 2.3 Three number-shaped traps

These are the SEC-era equivalents of the `min_max` problem the pack already
guards against, and each needs a test before the pack can hold both eras.

1. **L1R5 ≤ 20 → L1R4 ≤ 16 is not a rescaling.** Different subject count *and*
   different ceiling. Any tool that converts between them, or shows a
   "difference of 4", is lying. They must never appear in the same comparison.
2. **MI's threshold is 20 under both systems, and it is not the same 20.**
   Today's is an O-Level-basis L1R4; 2028's is a G3-basis L1R4 under a unified
   exercise. Same name, same number, different claim — precisely the
   [§4 b2](../SAFEGUARDS.md) situation.
3. **The polytechnic cut-off "improving" from 26 to 22 is an artefact of the
   mapping.** Rendered as a trend line it would tell a family the polytechnics
   got harder. They did not.

> ⚠️ **The legacy JAE rules are `confidence: medium` and must be re-fetched.**
> `moe.gov.sg/post-secondary/admissions/jae` was, as of 2026-08-09, still
> showing the **2022** exercise (last updated 3 February 2022). The 2027 JAE
> page — the last one that will ever exist — should be captured when published.
> Until then, JC L1R5 ≤ 20 / MI L1R4 ≤ 20 / polytechnic ELR2B2 carry medium
> confidence and cite the research brief, not a live page.

---

## 3. What this means for the engine and the packs

Good news first: **nothing here demands an engine rewrite**, which is the
payoff for building A-Level first.

| Need | Where it lands |
|---|---|
| PSLE sum, lower-is-better | `rules/lowest_sum.py` — already implemented and tested |
| L1R4, L1R5, ELR2B2, ELMAB3 | `rules/required_plus_best_n.py` — the shape already exists |
| Foundation AL A–C → 6/7/8; MTL exemption | **New**: a `grade_mapping` pre-pass in `engine/grades.py` |
| SEC G3 → G2 → G1 mapping for aggregates | **New**: same pre-pass, table-driven from the pack |
| Posting group as a gate | `engine/fit.py` eligibility path — the pattern from [ADR-0003](decisions/0003-eligibility-is-not-a-low-score.md) applies unchanged |
| S1 COP ranges | `engine/buckets.py` `min_max` — no change |
| Two eras side by side | `transitions.yaml` already versions by `applies_to_exam_years` |
| Cohort → rulebook routing | `cohorts.yaml` — extend `year_level` to cover P5/P6 and Sec 1–5 |

New pack files:

```
packs/singapore/
  stages.yaml                 ← fill in the psle and o-level stubs
  cohorts.yaml                ← + p5, p6, sec-1…sec-5, keyed on Sec 1 entry year
  transitions/
    psle-to-secondary-2026.yaml
    o-level-to-post-sec-2027.yaml     ← legacy, sunsetting, medium confidence
    sec-to-post-sec-2028.yaml         ← incoming
  schools.yaml                ← secondary schools, types, COP ranges per posting group
  subjects-psle.yaml
  subjects-sec.yaml           ← with G1/G2/G3 levels
```

`schools.yaml` is the big one and it has a licensing split worth planning
around: **school directory data is on data.gov.sg under the Singapore Open Data
Licence** (general information of schools, subjects offered, CCAs) and may be
redistributed with attribution; **COP ranges come from SchoolFinder under MOE's
terms** and must be encoded as facts with deep links, never mirrored. Prefer the
ODL source wherever both exist — [SAFEGUARDS §3a](../SAFEGUARDS.md).

`StudentProfile` needs to become stage-aware. It currently hardcodes A-Level
assumptions — `languages_offered` is documented as "at O-Level",
`national_service` is meaningless to a twelve-year-old. Recommended shape: keep
one class, add a `stage` field and a `SIGNALS_BY_STAGE` mapping, so the
"based on 4 of the 8 things you told us" confidence line keeps working per stage
rather than being reinvented three times.

---

## 4. The portal — three landing pages, one shell

**Decision: three separate landing pages.** A P6 parent and a JC2 student are
not the same reader. They differ in who is holding the phone, what vocabulary
means anything, what the decision is, and what the law requires. A single
landing page with a stage dropdown would force one tone onto all three, and the
tone it would land on is the A-Level one, because that is what exists.

### 4.1 Routes

```
#/                    thin stage chooser — the smallest page in the app
#/psle                PSLE landing        (P5 / P6, parent-facing)
#/sec                 Secondary landing   (Sec 1–5, both eras)
#/alevel              A-Level landing     (today's #/ moves here)
```

Each stage owns a namespaced subtree:

```
#/psle/schools   #/psle/school/<id>   #/psle/posting   #/psle/dsa   #/psle/result
#/sec/courses    #/sec/course/<id>    #/sec/aggregates #/sec/eae    #/sec/result
#/alevel/courses #/alevel/course/<id> #/alevel/fees    …            (existing set)
```

**The root is deliberately thin.** It is one question and three answers, it
remembers the last choice in `localStorage`, and it is not a marketing page. A
family arriving in the week of results should be one tap from the right place.

**Old hashes must keep working.** `#/courses`, `#/course/<id>`, `#/fees`,
`#/data` and the rest are live in a **265-page indexable static site** and in
whatever bookmarks exist. Ship a redirect map in the router — `#/courses` →
`#/alevel/courses` — and add a check to `tools/check_static.mjs` that every
pre-existing hash still resolves. Do this in the **same commit** as the rename;
a redirect added later is a redirect that was missing in production.

Shared across all three: masthead, disclaimer band, theme toggle, `#/data`
(sources), `#/more`, and the safeguard copy. The topnav and tabbar are
**per-stage** — a PSLE parent should never see "Fees" meaning university fees.
A stage chip in the masthead shows where you are and switches.

### 4.2 The PSLE landing page

**Reader:** a parent, usually the mother, usually on a phone, usually anxious.
The child is twelve and may be reading over their shoulder. Assume both.

**Hero.** One line of orientation, then the line that sets the whole tone:

> **Your child sits the PSLE in November. Here is what happens after.**
>
> A PSLE score decides a posting group and a set of schools. It does not decide
> what your child can become — and the schools themselves will tell you the
> same thing.

**Three doors, above the fold, no form.** The existing app opens with a
dropdown and a grades table. That is right for a JC2 student who came to
calculate something. It is wrong for a P6 parent in June who does not yet have
a score and does not know what she is looking for.

| Door | For | Goes to |
|---|---|---|
| **We have a score** | Late November onward | Posting groups, eligible schools, what the ranges mean |
| **Not yet — we are choosing** | The other eleven months | Schools by what they offer, DSA, travel time |
| **Explain the system** | Anyone | ALs, posting groups, Full SBB, the six choices, the timeline |

**The timeline strip**, dated to the current exercise and cited per date: DSA-Sec
opens → DSA-Sec closes → PSLE papers → results → six choices (about five
working days) → posting. The window between results and choices is the tightest
real deadline in the whole product, and it should be visible before it arrives,
not during.

**Three cards that are always present, never behind a toggle:**

1. **What a cut-off point is.** Last year's first and last student posted, per
   posting group. It moves. Meeting it does not guarantee a place — some
   students who met it were tie-broken out.
2. **The DSA commitment.** Accept a DSA place and you give up your six S1
   choices and the ability to transfer. Say it before the application, not after.
3. **If the score is outside the posting table.** Named, described in its own
   terms, with the ITE Skills Certificate route out. First-class, not a footer.

**What the PSLE landing page must never do:** rank children, rank schools by
anything other than a criterion the family chose, describe a COP in percentile
words, or produce a "fit score" for a school. Schools get **eligibility and
attributes**; the family does the choosing. A fit score for a twelve-year-old
against a school is the [ADR-0003](decisions/0003-eligibility-is-not-a-low-score.md)
mistake with higher stakes.

### 4.3 The Secondary / SEC landing page

**Reader:** a Sec 1–4 student, often with a parent beside them. Old enough to
consent for themselves under the PDPC guidance — *if the copy is readily
understandable by them*, which is a design requirement, not a disclaimer.

**The first question is not grades. It is the year they started Secondary 1** —
because that one answer selects between two entirely different rulebooks, and
nothing else in the product has that much leverage. Reuse the existing
`cohortEcho` pattern and read it back loudly:

> You started Secondary 1 in **2023**. You sit the **GCE O-Level** in October
> 2026 — the last cohort ever to do so — and you apply through the **JAE** in
> January 2027.

> You started Secondary 1 in **2024**. You sit the **SEC** in 2027 and apply
> through the **Post-Secondary Admissions Exercise** in 2028. Your seniors'
> cut-off numbers are not comparable to yours, and this page will tell you why
> every time it shows one.

**Then four doors**, not three — JC/MI · Polytechnic · ITE · **a fifth year in
secondary**. The fourth is real, MOE names it, and no consumer tool shows it.

**A "what changed" panel, for SEC students only**, stating plainly: L1R5 ≤ 20
became L1R4 ≤ 16 and is *not* a rescaling; the polytechnic cut-off moved 26 → 22
*because* one subject is now mapped to G2, not because it got harder; one
application instead of three; one results release in January; English and MTL
papers move to September.

**The subject-level planner is the highest-leverage feature in the product.**
Under Full SBB, a Sec 2 student choosing whether to take Maths at G2 or G3 is
making a post-secondary admissions decision two years early, and almost
certainly does not know it — JC needs every L1R4 subject at G3, while
polytechnic will allow exactly one at G2 from 2028. Working that backwards from
a course to a subject-level choice is precisely what `engine/backward.py`
already does. Nothing else on the market does this.

### 4.4 The A-Level landing page

Largely today's `#/` view, moved. Two edits: the hero no longer has to be the
whole product's front door, so it can address a JC1/JC2/MI student directly; and
the existing `#/explore`, `#/results-day` and `#/perspectives` views become
`#/alevel/…` while staying reachable, since each has a natural sibling in the
other two stages later.

### 4.5 Build order

1. Route namespacing + redirect map + static-site check. **No new content.**
   Ship it green.
2. `#/` stage chooser and the shared shell.
3. PSLE pack (§3) behind a `PREVIEW` gate — the coverage-gate pattern from
   `pathahead-coverage-gate` applies: name the schools that are loaded, do not
   imply a set that is not.
4. `#/psle` landing and views.
5. SEC/O-Level dual-era pack.
6. `#/sec` landing and views.
7. Subject-level planner.

---

## 5. Data capture — what is asked, what it buys, and what it costs

**Decision taken: postal-code-precision location, held locally, never
transmitted.** §5.2 accepts that decision and then recommends one modification,
with the reasoning, because the research in §1.3 changed what the field is worth.

### 5.1 The fields

Every field is optional and skipping costs confidence, never function — the
existing `answered()` / signal-count mechanism extends unchanged.

| Field | Stage | What it actually buys | Kind |
|---|---|---|---|
| Cohort / Sec 1 entry year | all | Selects the rulebook. The single highest-value question in the product. | routing |
| Subject grades | all | The score | input |
| Subject **levels** (G1/G2/G3) | sec | Which aggregates can even be computed | eligibility |
| MTL / Higher MTL | psle, sec | L1 substitution, SAP advantage, HMTL and third-language criteria | eligibility |
| Citizenship | all | Tie-breaker #1 at S1; PSE eligibility; fees | eligibility |
| CCA attainment tier | sec | PSE bonus points (max 3, +2 for certain JC programmes) | input |
| Interests (RIASEC ×6) | sec, alevel | Fit, as today | preference |
| Priorities, working style | sec, alevel | Fit, as today | preference |
| **Home location** | psle, sec | **Travel time only. See §5.2.** | preference |

**Never collected, at any stage:** name, child's name, school name, NRIC, email,
phone, date of birth, exact address, or a persisted photograph of a results
slip. The fields do not exist. This is unchanged from
[SAFEGUARDS §2](../SAFEGUARDS.md) and nothing in this document weakens it.

### 5.2 The postal code — an honest accounting

The research in §1.3 changed the value of this field, and the product has to say
so rather than let a parent infer otherwise:

| What a parent may assume | What is true |
|---|---|
| Living near a school helps at posting | **No.** Distance is not an S1 tie-breaker. Citizenship, then choice order, then ballot. |
| Like P1 registration | **That is a different exercise.** Distance *is* a criterion at P1. Families conflate the two constantly. |
| It affects the cut-off | No. COPs are score ranges from last year's posting. |
| It is worth entering anyway | **Yes** — a four-year daily commute is a real constraint, and it decides which of six choices is liveable. |

So the field is offered, it is genuinely useful, and **the field's own helper
text states that it changes travel time and nothing about admission.** That is
the `eligibility-before-preference` lesson in a new place: never let a field
imply a power it does not have.

**A 6-digit Singapore postal code identifies a building.** For a landed
property it is effectively a home address, attached in-session to a
twelve-year-old's exam results. That is the most sensitive combination anywhere
in this product, so:

1. **No geocoding API.** Converting a postal code to coordinates through OneMap
   or any other service would send a child's home address to a third party and
   break the "computed on this device" promise printed on the first screen.
   Non-negotiable.
2. Which leaves two ways to get coordinates offline, and both have a cost:
   - Bundle a full postal-code table — roughly 140,000 entries, several MB. It
     breaks the single-file, no-build-step architecture that makes this app
     auditable.
   - Bundle a **postal-sector** table — the first two digits, 28 sectors,
     around 1–3 km resolution. A few hundred bytes.

**Recommendation, for your decision:** keep the familiar 6-digit input, because
that is what families know and it is one field — then **truncate to the sector
on entry, discard the last four digits before anything is stored or computed,
and say so on screen** as it happens:

> *We keep the first two digits (`53`) and forget the rest. That is enough to
> estimate travel time and not enough to find your home.*

Sector resolution is sufficient to rank six schools by commute, which is the
only thing the field is for. It costs nothing architecturally and removes the
one genuinely identifying data point in the product. **If you want true 6-digit
precision instead, the cost is a multi-megabyte bundled table and a rewrite of
§2 of SAFEGUARDS — say so and it will be built that way.**

### 5.3 Storage, and the PDPA position

| | |
|---|---|
| **Default** | Session memory. Nothing written to disk. |
| **Opt-in** | An explicit *Save this on this device* control writing to `localStorage`, with a nickname the user picks — the app suggests "Child 1" and never asks for a real name. |
| **Deletion** | *Forget everything* visible on every stage, one tap, no confirmation maze. Clears storage and memory. |
| **Transmission** | None. No server, no analytics, no crash reporting, no fonts fetched at runtime, no geocoding call. |

**The PDPA position, written down as SAFEGUARDS §2 requires.**

The PDPC's [Advisory Guidelines on Children's Personal Data](https://www.twobirds.com/en/insights/2024/singapore/singapore-pdpc-issues-advisory-guidelines-on-the-pdpa)
(28 March 2024) treat anyone 18 or younger as a child, require **parental
consent below 13**, and require that policies be **readily understandable by the
child** for ages 13–17.

PathAhead's answer is structural rather than procedural: **the operator collects
nothing.** Data entered stays in the browser's memory on the user's own device
and is transmitted nowhere. There is no collection, use or disclosure by an
organisation, so the consent obligations do not attach. That is the honest legal
reading and it is also why the architecture was chosen.

Three things follow anyway, because "we are not obliged to" is a poor reason not
to:

1. **The PSLE track is addressed to a parent.** Its copy says "your child"
   throughout. A twelve-year-old arriving alone still sees nothing harmful, but
   the page is not written to solicit them.
2. **The purpose note comes before the field, not after.** Each optional field
   states in one sentence what it changes, in language a twelve-year-old can
   read. That is the PDPC's 13–17 standard applied to the under-13 track,
   voluntarily, because it is the right bar.
3. **If a hosted build is ever served from a maintainer-controlled domain**, the
   privacy note must state the host's own access-log retention honestly. GitHub
   Pages remains the recommendation for exactly that reason.

> ⚠️ Not legal advice. Before any public launch this position should be reviewed
> by someone qualified in Singapore law — the standing caveat at the top of
> SAFEGUARDS.md applies to this section in particular.

---

## 6. The logo

**Ruled out before drawing anything:** shields, crests, laurels, torches,
mortarboards, open books, and MOE's or any institution's colours — [SAFEGUARDS
§4a](../SAFEGUARDS.md) forbids anything that reads as official. **Also ruled
out: upward arrows and ascending staircases**, the default vocabulary of every
education logo on the market. "Up" means "better", and a mark whose whole idea
is that one direction is better contradicts the product on the masthead of every
page. All three candidates are horizontal for that reason.

| | Idea | Reads as | Against it |
|---|---|---|---|
| **A · The Fork** | One point on a path; two ways continue, mirrored so neither sits above the other | A choice, with no correct answer | A binary, when the product's whole point is that there are more than two ways |
| **B · Wordmark + waypoint** | Type only, with one terracotta dot between *Path* and *Ahead* | Quiet, editorial, honest | No mark means nothing to put in a favicon but a letter; least memorable |
| **C · The Fan** | Where you stand now, and three routes continuing outward | Many real futures from one position | Three lines at 16px need the counters checked carefully |

**Recommendation: C, with B's typographic lockup beside it.** C states the
product's actual claim — *you are here, and there is more than one way on* — and
its three strokes happen to correspond to the three stages without labouring the
point. A is the safer mark and the weaker idea.

Files written: `web/assets/logo-a-fork.svg`, `web/assets/logo-c-fan.svg`,
`web/assets/favicon-a-fork.svg`, `web/assets/favicon-c-fan.svg`. The masthead
marks use `currentColor`, so they inherit the ink in light, dark and evening
themes with no extra rules and no second asset. Both carry `<title>` and
`<desc>`. Inline them into `web/index.html` rather than linking — the
single-file, no-network rule holds.

---

## 7. New safeguards this work creates

Each needs a **failing test written before** the feature that could break it —
the rule that
[`pathahead-golden-fixtures-must-exercise-new-gates`](../evals/golden) exists to
enforce, after a cross-engine check passed 11/11 on code it never ran.

| # | Rule | Test |
|---|---|---|
| S1 | An S1 cut-off range is a `min_max` and is never described in percentile words | extend `test_a_min_max_band_is_never_described_as_a_percentile_band` to S1 |
| S2 | A posting group is an eligibility gate. A school a child cannot be posted to gets **no score at all**, not a low one | new — mirrors ADR-0003 |
| S3 | No fit score is ever computed for a child against a school | new |
| S4 | L1R5 and L1R4 are never converted into each other, differenced, or shown on one axis | new |
| S5 | MI's L1R4 ≤ 20 (O-Level basis) and PSE's L1R4 ≤ 20 (G3 basis) are distinct facts and never merge | new — §4 b2 shape |
| S6 | The polytechnic cut-off 26 → 22 is never rendered as a trend | new — §4 b4 shape |
| S7 | A cohort's rules are selected from the Sec 1 entry year, and a mismatch fails loudly rather than defaulting | new |
| S8 | The "did not qualify for a secondary course" route is reachable from the PSLE landing page | new — a DOM check in `check_ui.mjs` |
| S9 | Nothing writes to `localStorage` without an explicit user action | new — DOM check |
| S10 | No code path sends a postal code, or any input, over the network | new — static check on the bundle |

---

## 8. Open questions for you

1. **Postal code: sector-only (recommended, §5.2) or true 6-digit?** The second
   costs a multi-megabyte bundle and a SAFEGUARDS §2 rewrite.
2. **Logo: C, or A, or wordmark-only?** C is recommended.
3. **Does the root `#/` stage chooser survive**, or should the three landings be
   fully separate entry points with no shared front door? A shared root is
   assumed above.
4. **Is the legacy 2027 JAE pack worth building at all?** It serves exactly one
   cohort for one exercise, then is dead. Building it proves the dual-era
   architecture — which is the portfolio argument — but a 2028 SEC-only pack
   ships sooner.
5. **Does the PSLE stage need school-level data on day one**, or does it ship
   first as *explain the system + posting groups + timeline* with schools
   following? The second is a week's work; the first is `schools.yaml` and a
   licensing review.

---

## 9. Sources

Verified 2026-08-09. Facts encoded, prose never reproduced —
[SAFEGUARDS §3b](../SAFEGUARDS.md).

**PSLE and S1 posting**

- [PSLE scoring system — MOE](https://www.moe.gov.sg/psle-fsbb/psle/psle-scoring-system) — AL bands, Foundation mapping, MTL exemption, HCL/SAP, HMTL and third-language criteria
- [What are Posting Groups — MOE](https://www.moe.gov.sg/secondary/s1-posting/how-to-choose/what-are-posting-groups) — the PG table and its four rules
- [S1 Posting process — MOE](https://www.moe.gov.sg/secondary/s1-posting) — timeline, six choices
- [How posting works — MOE](https://www.moe.gov.sg/secondary/s1-posting/how-posting-works)
- [Tie-breakers in the S1 Posting System (PDF) — MOE](https://www.moe.gov.sg/microsites/psle-fsbb/assets/infographics/new-psle-scoring-system/tie-breaker.pdf) — the current three-step order
- [How your child is posted — MOE](https://www.moe.gov.sg/secondary/s1-posting/results/how-posted) — ⚠️ describes the **2020** cohort; the address-fallback rule is here
- [Understand PSLE score ranges — MOE](https://www.moe.gov.sg/secondary/s1-posting/how-to-choose/understand-psle-score-ranges) — COP definition, affiliated and SAP ranges
- [DSA-Sec — MOE](https://www.moe.gov.sg/secondary/dsa) — dates and the binding commitment
- [School types — MOE](https://www.moe.gov.sg/secondary/schools/types) — ⚠️ last updated 1 Feb 2021, pre-FSBB vocabulary

**SEC and post-secondary**

- [Secondary Education Certificate — SEAB](https://www.seab.gov.sg/secondary-education-certificate-sec/) — grading, grade mapping, timetable, results release. Last updated 14 May 2026
- [Post-Secondary Admissions Exercise — MOE](https://www.moe.gov.sg/post-secondary/admissions/pse) — the unified exercise, key dates. Last updated 13 Mar 2026
- [PSE: junior colleges and Millennia Institute — MOE](https://www.moe.gov.sg/post-secondary/admissions/pse/jc-and-mi) — L1R4, thresholds, minimum grades, bonus points. Last updated 16 Mar 2026
- [PSE: polytechnic diploma courses — MOE](https://www.moe.gov.sg/post-secondary/admissions/pse/polytechnic-diploma-course) — ELR2B2 ≤ 22, the B2 G2-mapping, CCA bonus table. Last updated 16 Mar 2026
- [Joint Admissions Exercise — MOE](https://www.moe.gov.sg/post-secondary/admissions/jae) — ⚠️ showing the **2022** exercise as of 2026-08-09; legacy rules remain `confidence: medium`
- [Would there still be GCE N-/O-Level qualifications after 2027? — SEAB](https://ask.gov.sg/seab/questions/cmkkrkf6c0019pnhlauyrt2mj)

**Licensing**

- [Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence) — school directory, subjects offered, CCA data
- [MOE Terms of Use](https://www.moe.gov.sg/terms-of-use) — SchoolFinder COP data: cite and deep-link, never mirror
- [PDPC Advisory Guidelines on Children's Personal Data](https://www.twobirds.com/en/insights/2024/singapore/singapore-pdpc-issues-advisory-guidelines-on-the-pdpa)

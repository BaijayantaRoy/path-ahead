# Next — exactly where to pick up

Written 2026-08-02 at the end of a long session. Everything below is verified:
URLs fetched and confirmed to parse, shapes inspected. No guesses.

**Correction to an earlier claim in this repo:** `web_fetch` parses PDFs
perfectly. The NTU IGP PDF returned a clean table on the first attempt. Any
note saying "PDF-only, cannot parse" was wrong and has been removed. Fetch the
PDF.

---

## 1. ~~NTU and SMU tuition fees~~ — DONE 2026-08-02

Fee coverage went from **21 courses to 75 of 77**. Both fee tables are in, with
all four NTU bands and both SMU bands, and the health report now prints fee
coverage every run so this is visible rather than remembered.

Sources added: `ntu-fees`, `smu-fees`, and `ntu-candidature` — the last one
matters more than it sounds, because an annual fee without a duration is not
a number a family can use.

**Two things worth carrying forward.**

**a. NTU's Accountancy and Business are THREE-year programmes.** The normal
candidature table in NTU's Academic Handbook (Cohort AY2025-26, §3.2) says so
plainly. Assuming four — the obvious default — overstates the bill by SGD 9,500
and would have gone unnoticed. `test_ntu_accountancy_and_business_stay_three_year_programmes`
now pins it. The handbook is the right source for every NTU duration; it also
gives 4.5 for the Renaissance Engineering Programme and 4 for Chinese Medicine.

**b. `annual_fee_no_grant` is deliberately empty for NTU's general band.**
NTU publishes two non-subsidised rates — SGD 40,600 lab-based, SGD 36,350
non-lab-based — and publishes no mapping from programme to cluster. Not on the
AY2026 page, not on the AY2025 page, and not in the overstayers' fee PDF, which
uses the same two clusters without naming their members. Classifying the
courses ourselves would be inventing something the university withheld, and a
wrong call is a ~SGD 17,000 four-year error for a non-subsidised student. The
field stays empty; the note on every affected course names both figures so a
reader can work out their own case.
`test_ntus_lab_split_is_left_empty_rather_than_guessed` stops a later session
tidying it away. **If you want to close it properly, ask NTU admissions for the
classification and cite the reply.**

**Still open, small:** `ntu-arts-academic-discipline-education` and
`ntu-science-academic-discipline-education` carry no cost block. NTU's fee band
covers them, but neither NIE nor NTU publishes a normal candidature for the
BA/BSc (Academic Discipline and Education) anywhere found — it is absent from
the Academic Handbook table, the NIE admissions page and the double-major
flyer. They are the 2 of 77 in `outcomes without a fee figure`.

---

## 2. ~~SUTD, SIT and SUSS~~ — DONE 2026-08-02

**77 → 134 courses. Institutions 3 → 6.** Only polytechnics now stand between
the pack and `fit scoring: complete`.

`BandedProfile` and `ProfileBand` sit beside `GradeBand`, `assess_banded()`
beside `assess_band()`, and the loader refuses any course that carries both
shapes. The browser engine mirrors it and `check_ui` still passes.

**Correction to what this section used to say.** The sketch here was wrong in
four ways, all of them discovered by reading the actual publications:

1. **The scale, which is the one that would have shipped.** SUSS and SIT both
   publish against the **retired 90-point UAS** (3 H2 + H1 + GP + PW). The
   AY2026 score is out of 70 (3 H2 + GP). A student's 60 is not their 60. Both
   universities footnote the change themselves. A comparison would have looked
   completely ordinary and been wrong — the same failure family as ISSUES §A,
   but a unit error rather than an encoding one. Every affected profile is
   marked `comparable: false`; the bands are shown, the verdict is withheld,
   and the new `PUBLISHED_ON_ANOTHER_BASIS` bucket says why in the student's
   own language.
2. **SUSS publishes two stages, not one share** — shortlisted, then offered.
   Keeping only the first would badly overstate a student's position: SUSS
   shortlisted 72.6% of the top A-Level band for Psychology and offered 18.7%.
   `stage` is on the type and the engine leads with the offer.
3. **Censored values are data.** SUSS prints "Below 5%" in many cells.
   `share_label` keeps the words; `share` stays None. Inventing a midpoint
   would be manufacturing data.
4. **SIT's A-Level figures are cluster-level** — its own footnote 1 says so —
   so they are not attached to individual courses. SIT courses therefore carry
   polytechnic GPA bands only, and an A-Level student gets an honest
   `DATA_INCOMPLETE` naming the reason.

An earlier draft of `_assess_outcome` fell back to the polytechnic pool when
the A-Level pool was empty and compared a score out of 70 against a GPA out of
4.00. `test_an_a_level_score_is_never_placed_against_a_polytechnic_gpa_band`
exists because of it.

**Deliberately not loaded: SIT's salary figures.** SIT publishes a bare median
with no quartiles, and this project shows a range or nothing — `test_fit_and_timeline`
enforces `p25 <= median <= p75`. The employment *rate* is loaded for the 30
programmes that have one. If SIT ever publishes quartiles, that is free data.

---

## 2b. What is still open on these three

Three things remain on these universities, all small:

- **Ask SUSS and SIT to republish on the new UAS.** The moment either does, flip
  `comparable` to true, drop the `uas_90_retired` scale tag, and 12 courses gain
  a real verdict. `health` prints `on a retired scale` every run so this stays
  visible rather than forgotten.
- **SIT's cluster-level A-Level table** could be attached to a *cluster* page
  once `ROADMAP_UI.md` U2 exists — it is genuine information, just not
  course-level information.
- **SUSS and SIT fee tables.** Neither is loaded; `outcomes without a fee figure`
  is 59, of which 57 are these three universities.

Editorial descriptions for all 57 new courses are PathAhead's own, at
course-family level, and labelled as such. They are the least verified thing in
the pack and the first place a reader is invited to correct us.

---

## 3. ~~The evidence axis collapses~~ — DONE 2026-08-02

Fixed. Degenerate bands (p10 == p90, meaning the whole admitted cohort shared
one profile) are now a distinct verdict from clearing a range. A top student
across 77 courses gets 9 / 48 / 20 instead of 77-in-one. See ISSUES_v0.2.md §A.

Still worth doing later: `assess_band` returns headroom above the floor but the
UI does not surface it yet. It is the figure that discriminates where published
profiles saturate.

---

## 4. ~~Polytechnic destinations~~ — ALL FIVE, 2026-08-03

**134 → 330 courses. Institutions 6 → 11 of 11.** The machinery is built,
tested and honest, and all five polytechnics are loaded. The gate now reads
`complete`. See §4b for how the last one went in and what it changed.

The proposal in the old §4 (below, kept for its research) was right about the
shape and wrong about two things.

**a. The three-year decision needed inverting.** The plan said "carry the
latest three years, not one", reasoning that a single cut-off point is a bare
number. But each year is *already* a range, so that reason was satisfied by one
year — and merging three years into one min-max would have produced a figure no
institution published, widening every year until a course looked less selective
the longer PathAhead had been running. `GradeBand.history` now carries earlier
years **beside** the band, never folded into it, and the card says how many
exercises it is showing.

**b. Why the comparison is refused is not what the plan said.** The plan framed
it as a units problem — an O-Level aggregate out of 26, lower-is-better, versus
an A-Level score out of 70. True, but not the real reason, and a units-only
framing invites a later session to "fix" it with a conversion.

Temasek Polytechnic's own admissions guide settles it. An A-Level holder has
two routes into a polytechnic and **neither runs on their A-Level score**:

- Through **JAE**, they apply on their **GCE O-Level results**. The published
  range does apply — but to a number PathAhead does not hold for them.
- Through the **Direct Admissions Exercise**, they enter a shortened **2 or
  2.5-year** diploma, admitted on "academic results and/or interview/test where
  applicable and subject to the availability of vacancies". **No aggregate is
  published for this route at all.**

So there is no arithmetic that makes the comparison valid, and the card says so
in the student's own language while showing the numbers in full. This also
corroborates the SUTD FAQ claim about exemptions of up to two semesters:
3 years becomes 2 or 2.5.

**c. The coverage-gate decision, taken and written down.** `REQUIRED_COVERAGE`
now names **all five polytechnics individually** — NYP, NP, SP, TP, RP. The old
literal `"Polytechnic"` could never be satisfied, which was accidentally safe;
a family flag that any one polytechnic satisfied would have lifted PREVIEW with
four institutions missing. `test_one_polytechnic_does_not_lift_the_preview_label`
pins it.

**d. `assess_band()` now raises** rather than describe a `min_max` in
percentile words, and `assess_published_on_another_basis()` has its **own**
explanation — reusing the SUSS/SIT one would have told a family that a
polytechnic is a university and that its scale had been retired. Neither is
true.

---

## 4b. ~~Singapore Polytechnic — the last institution~~ — DONE 2026-08-03

**296 → 330 courses. Institutions 10 → 11 of 11. `fit scoring` reads
`complete` for the first time.** The `SP` table sits beside `NYP`, `NP`, `TP`
and `RP` in `tools/build_polytechnic_pack.py`; the source is `sp-course-elr2b2`.

### How the enumeration was actually done

The three ruled-out shortcuts below were all confirmed still true. The way in
was a fourth route the old note did not consider: **the ten school pages list
their own courses**, even though they carry no figures. Fetch
`/courses/schools/{abe,sb,cls,soc,eee,lsc,mad,mae,msa,sma}`, take the course
links, then fetch those. MSA and LSC turn out to offer no full-time diplomas at
all — they are service schools — which is why ten school pages yield eight with
courses.

### Three things found that a faster transcription would have got wrong

1. **Forty course pages are thirty-four courses.** The seven
   "Diploma in MAD, ..." pages all carry the same code **S29**, the same range
   and an intake SP labels *"For Entire Cohort of Diploma in Media, Arts &
   Design"*. They are specialisations chosen inside one JAE course. Loading
   them as seven would have inflated SP by six courses and repeated one
   admissions range as though it were six independent ones.
2. **SP is mixed on the ELR2B2 type, and the split is not random.** Business is
   type B, computing and maritime business C, the built environment and design
   D, media A — and **every science and engineering course publishes no type at
   all**. `None` in the table means "checked the page, SP states none", not
   "not looked up". This is the case §4b's own rule was written for.
3. **The Diploma in Nautical Studies publishes no aggregate range and no JAE
   course code**, though it does publish entry requirements. It carries **no
   band** — the same shape SUTD's five courses have. PathAhead does not say why
   the figure is absent, because SP does not say, and a plausible reason would
   be the same invention as a plausible figure. Guarded by
   `test_a_polytechnic_course_without_a_published_range_carries_no_band`, which
   fails if a later session either deletes the course or gives it a borrowed
   range.

Two figures corroborated the transcription against §4b's own spot-checks
exactly: Common ICT Programme 5–17 intake 247, Common Engineering Programme
3–19 intake 384.

### Two tests changed, and why — read this before assuming they were weakened

Finishing the coverage forced two assertions that could not survive it.

- `test_fit_is_in_preview_while_the_pool_is_partial` asserted the pool **was**
  partial. That stopped being true the moment SP went in. It is now
  `test_the_preview_label_tracks_coverage_in_both_directions`, which pins the
  mechanism instead: complete coverage clears PREVIEW, and a simulated gap
  restores it and names what is missing. Strictly more than the original tested.
- `test_the_evidence_axis_still_discriminates_across_the_larger_pack` asserted
  no bucket exceeds 60% of the pack. `published_on_another_basis` is now 207 of
  330, because 195 polytechnic courses publish an ELR2B2 aggregate this project
  refuses to compare. That bucket is **not a verdict** — it is the refusal to
  give one — so measuring it beside the verdicts made the test a report on the
  pack's composition rather than on the axis's resolution. It now requires that
  no *verdict* dominates, and separately that the courses which do get a verdict
  are spread across at least three of them with none above 80%. A §A-style
  collapse still fails it loudly.

### Checked with real input, not a fixture shaped to pass

A JC2 profile with H2 Further Mathematics, Physics, Economics and GP, and the
goal *"i want to work with my hands on real machines, not sit in an office"*:
all 34 SP courses score, SP's engineering diplomas lead its list, Nautical
Studies lands in `data_incomplete` with no invented verdict and ranks 72nd of
327 rather than being floated to the top by its missing data, and SP's fit
order is demonstrably **not** its selectivity order (SAFEGUARDS 5.1).

One honest wrinkle that showed up and is worth someone's attention: **fit scores
saturate at 100 across whole course families.** Twelve courses tie at 100 for
that profile. This is not a scoring bug — editorial data is written at
course-family level, so two polytechnic engineering diplomas are genuinely
identical on every axis the scorer can see. The UI already refuses to dress ties
as a ranking, but the fix is per-course editorial data, which is §5's largest
open item and now the pack's weakest link.

### The SP obstacle, kept for the record

The three shortcuts ruled out on 2026-08-03 and re-confirmed:

- `sp.edu.sg/courses` and `/courses/diplomas` — client-rendered; a plain fetch
  returns "Showing 0 - 0 of 0 Full-Time Diplomas". Still true.
- `sp.edu.sg/admissions/guides/singapore-polytechnic-jae-2026` — a counselling
  schedule, no figures. Still true.
- The **school** pages carry no aggregate figures — true, but they *do* list the
  courses, which is what made the job tractable.

Also tried and not useful: `sitemap.xml`, the Sitefinity `/api/default/`
endpoint, and the Course Eligibility Calculator page, all of which return
nothing to a plain fetch.

### What is loaded, and in what shape

| | Source | Courses | Years | Aggregate type published? |
|---|---|---|---|---|
| **NYP** | data.gov.sg `d_eb7bb85a49e021e63f9cb7b54497a400` | 39 | 2024, 2025, 2026 | No |
| **NP** | data.gov.sg, one dataset per year (collection 1502) | 41 | 2023, 2024, 2025 | **Yes** — A/B/C/D |
| **TP** | `tp.edu.sg/.../course-intake-aggregate-range.html` | 41 | 2026 only | No |
| **RP** | `rp.edu.sg/admissions/intake/` | 41 | 2026 only | **Yes** — A/B/C/D |
| **SP** | 34 individual course pages under `/courses/schools/…` | 34 | 2026 only | **Mixed** — see §4b |

NP is a year behind the rest because data.gov.sg's most recent NP dataset is the
2025 exercise. That is visible on every card rather than smoothed over.

### The rule that must survive any future transcription

**Do not transcribe from an aggregator.** Sites like sgschoolkaki.com have all
five polytechnics in one tidy table. Every figure in this pack cites the
institution that published it, and a third-party copy is not that. This is not
pedantry: a search snippet for TP during an earlier session reported "Common
Design Programme, 5-12, intake 261", and TP's own page says Common Design is
6-15 with an intake of 75 — the 5-12/261 belonged to Common *Business*. The
aggregator layer had already lost the mapping. SP was transcribed from 34 of
SP's own course pages for exactly this reason, slow as that was.

## 4c. Polytechnic fees — FOUR OF FIVE LOADED, 2026-08-05

**Fee coverage 111 → 266 of 330. Static site 111 → 265 indexable pages.**
NYP, RP, SP and TP are in, each transcribed from its own fee page. The tables
below are kept because they are the transcription record.

**All four publish the same AY2026 tuition:** SGD 3,100 citizen (under 40),
6,400 PR, 12,400 international (ASEAN), 13,600 (non-ASEAN). Reading four pages
to find four identical numbers felt like waste until it wasn't — it turned up
three things a copy would have got wrong, and they are written into
`tools/build_polytechnic_pack.py` above `FEES`:

1. **The supplementary fee differs at every one** — SP 77.52, TP 83.15,
   RP 86.50, NYP 88.09 for a citizen. This is the load-bearing detail: it is
   what proves these are four publications rather than one figure republished,
   and therefore what makes the identical tuition *not* evidence about Ngee Ann.
2. **TP's AY2026/2027 international tables now exist.** §4b recorded on
   2026-08-03 that they did not. They do, for both ASEAN and non-ASEAN, and
   they are what is loaded. The instruction that produced this — check each
   page rather than assume the split is universal — was right; the answer just
   changed.
3. **Every one publishes SGD 2,100 for citizens aged 40 and above** under the
   SkillsFuture Mid-Career Enhanced Subsidy. Named in the note, not loaded as
   the tier, because this transition is about the school-leaver cohort.

### The one open item: Ngee Ann

`https://www.np.edu.sg/admissions-enrolment/academic-matters/course-fees`
returns an **empty body** — 200, no content — over https, http, with and
without a trailing slash. So do NP's "Guide to Fees and Financial Assistance"
PDF and its course-fees FAQ PDF. NP's *other* pages fetch normally
(`/admissions-enrolment/enrolment/faqs` and `/admissions-enrolment/academic-matters`
both returned full text on 2026-08-05), so this is that page, not the domain.
A JavaScript-rendered browser fetch is the obvious next thing to try.

Re-attempted 2026-08-05 and still dead: a site-scoped web search finds the page
and confirms an AY2026 table exists on it, but no snippet ever carries the
figures — so search is not a way round this either. Four routes now ruled out.

All 41 NP courses carry a `fee_note` saying PathAhead could not retrieve the
page, and linking to it. **Do not fill them in from the other four.** MOE
setting a common subsidised rate is an inference about a process, not a figure
Ngee Ann published, and the supplementary fee differs at all four.
`test_ngee_ann_shows_no_fee_rather_than_its_neighbours_fee` fails if anyone
does.

### The transcription record

- **Singapore Polytechnic**, `sp.edu.sg/admissions/course-fees/full-time-diploma`,
  table 1, "New students enrolling in AY2026", page states *"Information is
  correct as of 07 May 2026"*:

  | | Tuition fee / year | Fees payable / year |
  |---|---|---|
  | Singapore Citizen (under 40) | $3,100.00 | $3,177.52 |
  | Singapore PR | $6,400.00 | $6,507.52 |
  | International (ASEAN) | $12,400.00 | $12,567.99 |
  | International (non-ASEAN) | $13,600.00 | $13,767.99 |

  Four decisions carried into the load, all four of which turned out to apply
  to every polytechnic and not just SP:

  1. **Use the tuition fee, not "fees payable", for the tier fields** — that is
     what the university entries hold, and `test_published_fee_tiers_are_internally_consistent`
     compares them. The difference (exam, sports, insurance, union, CLASS
     licence — $77.52 a year for a citizen) belongs in the fact note, because it
     is real money a family will be billed.
  2. **AY2026 splits international students into ASEAN and non-ASEAN for the
     first time.** That maps onto the existing `annual_fee_international` and
     `annual_fee_is_other` exactly as NUS uses them. SP states the split takes
     effect from AY2026, so earlier years are not comparable.
  3. **`annual_fee_no_grant` stays empty.** SP says students who reject the
     Tuition Grant "must pay full fees, including 9% GST on the TG amount" but
     publishes no figure. Same decision as NTU's lab/non-lab split — do not
     compute it.
  4. **Duration is 3 years**, which SMA's own page states for its diplomas.
     A Direct Admissions Exercise entrant does 2 or 2.5, which is why §4b keeps
     that distinction; the published fee is the 3-year full-time one.

- **Temasek Polytechnic**,
  `tp.edu.sg/admissions-and-finance/fees-financial-matters.html`, the
  "AY2026/2027 April Intake" tables. TP's page is a dropdown per intake year
  and per citizenship, and every year's table is in the served HTML:

  | | Subsidised tuition / year | Total payable / year |
  |---|---|---|
  | Singapore Citizen (under 40) | S$3,100.00 | S$3,183.15 |
  | Singapore PR | S$6,400.00 | S$6,513.15 |
  | International (ASEAN) | S$12,400.00 | S$12,573.65 |
  | International (non-ASEAN) | S$13,600.00 | S$13,773.65 |

  Do not confuse TP's **PFP** tables (S$4,150 PR, S$12,140 IS) with the diploma
  ones — they sit on the same page and are a different programme.

- **Nanyang Polytechnic**,
  `nyp.edu.sg/student/study/financial-matters/annual-course-fees`, the AY2026
  row of a table that also carries 2023, 2024 and 2025. Page states *"correct
  as of 14 May 2026"*. Tuition S$3,100 / 6,400 / 12,400 / 13,600, plus a
  supplementary fee of S$88.09 for a citizen, 118.09 PR, 178.59 IS. NYP's
  four-year table is the clearest illustration of the cohort-based structure:
  a 2024 entrant is still billed the 2024 rate.

- **Republic Polytechnic**, `rp.edu.sg/student/financial-matters/course-fees/`,
  "Admission Year 2026", page last updated 27 February 2026. Same four tuition
  figures; supplementary S$86.50 / 116.50 / 177.00. RP is the one that lists
  the eleven ASEAN member states its ASEAN rate covers.
- **SP, TP and RP carry one year each**, because that is all they publish. If any
  of them ever posts an archive, `history` takes it without a code change.
- **RP's vacancy asterisk is carried in the fact note**, not surfaced in the UI.
  It marks courses that still had places after JAE posting, which is the
  difference between an appeal with somewhere to go and one without.

---

## 4 (original research, kept) — Polytechnic destinations, researched 2026-08-02

The last thing between the pack and `fit scoring: complete`. **Two decisions
were taken with the user and should not be relitigated:**

1. Polytechnic diplomas go in the **same list** an A-Level student sees, marked
   as a different route. They are a real destination — SUTD's own FAQ points
   A-Level holders at polytechnics, which grant module exemptions of up to two
   semesters. The JAE figure is shown and **not** compared.
2. Carry the **latest three years**, not one. A single cut-off point is a bare
   number, and this project shows a range or nothing.

### The data — verified, and better than expected

`data.gov.sg`, Singapore Open Data Licence v1.0, one dataset per polytechnic.
Confirmed working:

```
NYP   d_eb7bb85a49e021e63f9cb7b54497a400   563 rows, academic years 2014-2026
      https://data.gov.sg/api/action/datastore_search?resource_id=<id>&limit=140&sort=_id%20desc
      fields: academic_year, jae_cluster, jae_course_code, course_name, gceo_cut_off_point
```

**AY2026 is already published**, so this is current data, not last year's.

Two API warnings, both cost time: the v2 endpoint
(`api-production.data.gov.sg/v2/public/api/datasets`) **silently ignores its own
`query` and `agencies` parameters** and returns the same unfiltered first page
every time — do not trust it for discovery. The CKAN-style
`data.gov.sg/api/action/datastore_search` works properly, including `sort` and
`limit`. `package_search` returns empty.

The other four polytechnic dataset IDs still need finding, one at a time, by
web search. **Ngee Ann's is shaped differently** — "Planned Intake and Cut-off
Points", published as a separate dataset per year — so expect to normalise.

### The modelling problem, which is real

Read the column metadata before writing any code. `gceo_cut_off_point` is:

> "the net aggregate (after deducting CCA bonus points) **lowest and highest
> aggregate who were admitted**" — column description: *"Range from Lowest to
> Highest Ranked student cut-off-points"*.

That is a **full min-to-max of everyone admitted**, not a 10th-90th percentile.
It is a *third* published shape, after the percentile band and the banded
profile:

| Shape | Who | What the endpoints mean |
|---|---|---|
| `GradeBand` | NUS, NTU, SMU | 10th and 90th percentile — the middle 80% |
| `BandedProfile` | SIT, SUSS | share of applicants in each band who got through |
| **min-max range** | polytechnics | the **whole** admitted cohort, outliers included |

**Do not put a min-max into `GradeBand` and leave it at that.** A full range is
necessarily wider than a p10-p90, so polytechnic courses would render as
dramatically less selective than universities when the difference is the
statistic, not the selectivity. NYP Nursing is "3 to 28" — nearly the entire
scale — because one admitted student had a 28, which a p10-p90 would have
excluded by construction.

Proposed, not yet built: add three fields to `GradeBand` rather than a third
type, because the *structure* is identical and only the meaning differs.

```python
statistic: str = "p10_p90"   # "p10_p90" | "min_max" -- what the ends MEAN
scale: str = ""              # "uas_70" | "elr2b2_olevel"
comparable: bool = True      # same flag BandedProfile already carries
```

Then generalise the check in `forward._assess_outcome`: comparability is a
property of any published figure, not just a banded one. An ELR2B2 aggregate is
an O-Level statistic and lower-is-better, so `comparable: false` for the
A-Level transition and the existing `PUBLISHED_ON_ANOTHER_BASIS` bucket already
says the right thing. Add a calibration test that a `min_max` band is never
described in the words used for a percentile band.

### One trap in the coverage gate

`fit.coverage()` counts `institution_short` across the **whole pack**, while
`score_all()` ranks a single transition. `REQUIRED_COVERAGE` contains the
literal string `"Polytechnic"`, so naming an institution `NYP` will not satisfy
it — which is accidentally correct, and should be made deliberate. Decide
explicitly whether the gate needs **all five** polytechnics before
`fit scoring` may read `complete`, and write that down. Do not let the PREVIEW
label lift because one polytechnic was loaded.

---

## 4d. Fit saturation — measured, and the fix is NOT what it looked like

`python tools/check_saturation.py` prints what a real profile actually gets.
For the Further-Mathematics profile from §4b's real-input check:

```
scored 325 of 330 courses
  distinct scores      : 61
  courses tied at top  : 20      <- at 100/100
```

**Do not trust that number from this page — run the script.** It was 27 when
first measured and is 20 now, and *no scoring code changed in between*. What
changed was the DATA: loading polytechnic fees gave a cost-sensitive profile a
Cost bucket to score, which pulled courses apart that had been tied. The tie
count is a property of coverage as much as of the scorer, so it moves whenever
a gap is filled. That is also the encouraging reading — filling gaps reduces
saturation on its own.

**Two corrections to what this repo previously said.**

1. **The top tie is 27 courses, not 12.** The earlier figure came from printing
   the top twelve and observing they were all 100 — which counts the page, not
   the tie. `check_saturation.py` exists so this is measured rather than
   eyeballed.

2. **Per-course DESCRIPTIONS cannot fix this, and it was wrong to imply they
   would.** `engine/fit.py` never reads `editorial.summary` — grep it. Scoring
   runs entirely on the STRUCTURED editorial fields: `interests`,
   `subject_affinity`, `assessment_style`, `teamwork`, `maths_intensity`,
   `writing_intensity`. Singapore Polytechnic now has 34 distinct summaries and
   still contributes 6 courses to the tie at 100, because all 34 still draw
   their structured fields from ~20 shared course families.

   So the prose and the arithmetic are two separate jobs:

   - **Summaries** make two courses distinguishable to a PERSON reading a card.
     Worth doing — that is what a family reads — but it moves no number.
   - **Structured fields** make them distinguishable to the SCORER. Nothing
     else will reduce these ties.

   The check prints both, so the difference stays visible: at 100 there are
   currently *13 descriptions for 27 courses*, and the structured profiles
   behind them are fewer still.

**Where to start.** The tie at 100 spans SIT 6, SP 6, NP 5, NYP/TP/RP 3 each —
engineering and built-environment courses whose families were written broadly.
Differentiating `maths_intensity`, `assessment_style` and `subject_affinity`
per course across those ~27 would do more for the fit axis than the next
hundred summaries. Neither is a scoring bug: `test_fit_calibration.py` already
proves the machinery is monotonic and honest. This is a data-resolution
problem, and it is now the pack's weakest link.

---

## 5a. Language requirements — three done, four unverified. DO THIS NEXT.

**The bug, because it is worth stating plainly.** A student who does not read
Chinese was shown Ngee Ann's Diploma in Chinese Studies as her **second
strongest match out of 296 courses**, at 67/100. Every point came from generic
overlap — *"you work best through exams, and so does much of this course"* —
because nothing in the pack recorded that NP requires Higher Chinese 1-4 or
Chinese 1-3 to be considered, and states that **at least half the course is
conducted in Chinese**.

The score was not too high. **A score at all was the error**: any number puts
the course into a ranking, and a low one would have ranked it above hundreds of
others just the same. `LanguageRequirement` now blocks scoring outright, the
card still shows the course and the requirement, and the student is asked once
in step two which mother tongue they offered.

**Verified and loaded** (from each course's own Entry Requirements table):

| Course | Requirement | Taught in it |
|---|---|---|
| `np-chinese-studies` | Higher Chinese 1-4, or Chinese 1-3 | yes |
| `np-chinese-media-and-communication` | Higher Chinese 1-4, or Chinese 1-3 | yes |
| `np-tamil-studies-with-early-education` | Tamil Language | yes |

**Three of the four resolved 2026-08-03**, from NTU's own programme pages
(source `ntu-programme-requirements`; the IGP page does *not* carry entry
conditions, which is why the pack's `url` field was no help):

| Course | Outcome | Taught in it |
|---|---|---|
| `ntu-chinese-medicine` | O Level pass in Chinese Language | **yes** — NTU calls it *"a bilingual course with English and Mandarin as the media of instruction"* |
| `ntu-chinese` | H2 Chinese, or good H1 Chinese, or good O Level (Higher) Chinese | **not asserted** — NTU states no language of instruction |
| `ntu-linguistics-multilingual-studies` | **none — deliberately** | n/a |

Two of these were nearly got wrong in *opposite* directions, which is the
point of the section:

- **`ntu-chinese` is the one the old note called "almost certainly taught in
  Chinese".** NTU does not say that anywhere on the programme page. It calls
  its graduates "bilingual and bicultural", which is a claim about outcomes,
  not about the medium of instruction. The grade condition is recorded and
  `taught_in_language` is left **false**, because the entry condition alone is
  what blocks the scoring; asserting the teaching language would have been an
  invention that changes what the card tells a family.
- **`ntu-linguistics-multilingual-studies` gets no requirement at all.** Its
  published curriculum is a linguistics curriculum taught *about* languages —
  Structure of Modern English, Phonetics and Phonology, Language and the
  Computer — and NTU sets no language condition. Adding one on the strength of
  "Multilingual" in the title would have blocked a course for students entitled
  to it. `test_a_language_requirement_is_never_added_by_pattern_matching_the_name`
  pins all three ids so a later session cannot tidy any of them.

**Still open: `suss-chinese-studies`.** SUSS's own programme page is
client-rendered and returns nothing to a plain fetch, and no browser tool was
available in this session. SUSS's *general* full-time admission criteria page
does carry a Mother Tongue Language requirement, but it applies to every
programme and is satisfied by **any** assigned MTL — Chinese, Malay or Tamil —
so it does **not** establish a Chinese-specific condition for this degree.
Nothing was added. To close it: open
`suss.edu.sg/courses/detail/Bachelor-of-Arts-in-Chinese-Studies` in a real
browser, or ask SUSS admissions and cite the reply.

**How to do it right:** open the course's own entry-requirements page, transcribe
the grade condition verbatim into `label`, and set `taught_in_language` only if
the institution says the teaching is in that language. `taught_in_language` is
the field that matters most and the one a grade table will never tell you — it
is the difference between a hurdle at the door and three years a student cannot
follow.

---

## 5b. One SIT figure worth a second pair of eyes

`sit-physiotherapy` computes to **S$37,440** (240 credits × S$156.00, both
verbatim from SIT's AY2026 fee PDF). A snippet from SIT's own Physiotherapy
*course* page quoted **S$37,200** during the same session.

The difference is S$240 — which is exactly the annual miscellaneous fee SUSS
publishes, and close to one credit unit. It is more likely that the course page
is a cycle behind, or quotes a slightly different inclusion, than that the fee
table is wrong; the fee table is the authoritative document and is what is
loaded. But S$240 is not nothing to a family, and the discrepancy was seen
rather than reasoned about, so it is written down rather than resolved by
assumption.

**To close it:** open a couple of SIT course pages directly and compare the
"total programme fee" they quote against credits × rate from the fee table. If
the course pages disagree systematically, the pack should cite the course pages
instead. If it is one course, it is a typo on one side and worth telling SIT.

---

## 5. Smaller, already scoped

- Per-course editorial descriptions for NTU and SMU. They are currently written
  at course-*family* level and say so in the fact note. The 57 SIT/SUSS/SUTD
  descriptions and the 162 polytechnic ones are in the same position, and
  together they are the least verified thing in the pack by a wide margin.
- GES employment data for NTU and SMU courses — the dataset already covers all
  six universities; only NUS has been mapped. Note that **SIT's bare median is
  deliberately not loaded**: this project shows a range or nothing, and
  `test_fit_and_timeline` enforces `p25 <= median <= p75`.
- ~~SIT fee table~~ — **DONE 2026-08-03.** 36 of 40 SIT courses, on the
  `per_credit` basis SIT actually charges. See §5b for one figure worth
  double-checking, and `tools/add_sit_fees.py` for the four courses
  deliberately left empty.
- **SUSS fees.** Not loaded. `suss.edu.sg/admissions/financial-matters/
  tuition-fee-subsidy/full-time-undergraduate` is the page; the AY2026 amounts
  were not visible in search results and the page was not fetched. SUSS also
  publishes an annual miscellaneous fee of S$240, which is the kind of figure
  this pack should carry rather than leave to a family to discover.
- **Polytechnic fees.** None of the 162 polytechnic courses carries one, and
  this is now the largest and most misleading gap in the pack: the cheaper
  route is currently the one that looks like it has no information. Fees are
  published per polytechnic, not per course, so this is five figures and a
  shared `cost` block — much less work than it sounds.
- `outcomes without a fee figure` is **185**, of which 162 are polytechnics.

---

## How to verify anything here still holds

```bash
pytest -q                                  # 199 tests
python app/cli.py health --gate            # data health
python app/cli.py build --out dist
python app/cli.py build --out web/data     # what the BROWSER loads
node tools/check_golden.mjs                # both engines agree
npm install && node tools/check_ui.mjs     # 34 UI checks, real DOM
```

The health report prints coverage every run — `institutions covered`,
`outcomes with a fee figure` and `fit scoring` are the three lines that tell you
how far this got. As of 2026-08-03 they read **11**, **111 of 330**, and
**complete**. The middle one is the one still worth moving.

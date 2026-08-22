# PathAhead — Safeguards, Disclaimers and Legal Posture

> Planning only — nothing built yet. This document exists because of the decision on 2026-08-02 that PathAhead is intended as **a real public tool Singapore families use**, not only a portfolio artifact. On that premise the safeguards are part of the architecture, and this file is written *before* the first line of code (see [DESIGN_REVIEW.md](DESIGN_REVIEW.md) §8, task A0).
> Companions: [README.md](README.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [DESIGN_REVIEW.md](DESIGN_REVIEW.md) · [ROADMAP.md](ROADMAP.md)
> ⚠️ Not legal advice. This is a design posture assembled from public sources, not a compliance opinion. Before any public launch, the disclaimer text and data-licensing position in §3 should be checked by someone qualified in Singapore law.

---

## 1. The governing idea

This tool touches three things that each raise the bar on their own, and it touches all three at once: **children's personal data**, **government-published information**, and **a decision families are frightened about**. The safest design is not the one with the longest disclaimer — it is the one that has as little to disclaim as possible.

Three structural choices do most of the work, and every one of them is also a better product:

1. **Collect nothing.** No accounts, no names, no email, no NRIC, no school, no telemetry. Most data-protection obligations attach to data an organisation *collects*; collect none and they largely do not arise.
2. **Compute locally.** Tier A runs entirely in the browser; Tier B runs entirely on the user's machine. Grades never reach a server the maintainer controls.
3. **Assert only what is published, and cite it.** Every number carries its year, source and confidence; nothing is inferred and presented as fact.

---

## 2. Personal data — PDPA and children

Singapore's PDPC issued [Advisory Guidelines on the PDPA for Children's Personal Data in the Digital Environment](https://www.twobirds.com/en/insights/2024/singapore/singapore-pdpc-issues-advisory-guidelines-on-the-pdpa) on 28 March 2024. They are not legally binding, but the PDPC is expected to interpret the PDPA consistently with them. The parts that bear on this project:

- A **"child" is anyone 18 or younger** for the purposes of the guidelines — which covers essentially the entire student-facing user base across all three stages (PSLE ~12, O-Level/SEC ~16, A-Level ~18).
- **Below 13:** consent must come from a parent or guardian, who must be notified of the purposes of collection, use and disclosure.
- **13 to 17:** the child can give valid consent, but **only if the policies are readily understandable by the child** — and if the organisation has reason to believe the child doesn't understand the consequences, parental consent is required instead.
- The under-13 rule is therefore squarely in scope for the PSLE stage, and the "readily understandable by the child" test applies across the rest.

**Design answers, in order of preference:**

| Data | Decision |
|---|---|
| Name, email, NRIC, school, contact | **Never collected.** Not optional-with-a-checkbox — the fields do not exist. |
| Grades / scores | Entered per session, **held in memory only** in Tier A; in Tier B, saved locally only if the user explicitly saves a profile. |
| Saved profiles (Tier B) | Optional, local file or SQLite on the user's own machine, labelled with a **nickname the user chooses** — the app suggests "Child 1", never asks for a real name. One-click **Delete everything**, always visible, no confirmation maze. |
| Uploaded results-slip photos (Tier C OCR) | Processed and **discarded immediately**; never written to disk by default; never sent anywhere unless the user has explicitly chosen a non-local model, which triggers the persistent warning banner. |
| Telemetry, analytics, crash reporting | **None. Ever.** Same posture as BandUp and the rest of the portfolio. |
| Update check | Unauthenticated `GET` with **no identifiers and no query parameters** — the request reveals nothing beyond "someone fetched a public release list." |

**On-screen statement, verbatim, on the first screen:**
> *PathAhead does not ask for your name, your child's name, your school, or any contact details — and it never sends your grades anywhere. Everything is worked out on this device.*

If a hosted Tier A build is ever served from a domain the maintainer controls, the **privacy policy must state the hosting provider's own access-log retention** honestly, since that is the one place data touches infrastructure outside the user's device. GitHub Pages is the recommended host precisely because that story is short and verifiable.

---

## 3. Source data — licensing, attribution, and what may not be copied

This is the area most likely to be got wrong, and it splits into two very different regimes.

### 3a. Data from data.gov.sg — permissive, with conditions

Datasets published under the [Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence) may be used, modified, adapted and redistributed, commercially or not, under a worldwide royalty-free licence — **but**:

- A **conspicuous attribution notice** naming the source agency, with a **link to the current version of the licence**, must appear in any product or website using the data.
- The data must **not be used in a way that suggests official status or agency endorsement.**
- Agency intellectual property rights cannot be enforced by the user.

Relevant datasets confirmed to exist there include MOE's [General information of schools](https://data.gov.sg/datasets/d_688b934f82c1059ed0a6993d2a829089/view), [Subjects Offered](https://data.gov.sg/datasets/d_f1d144e423570c9d84dbc5102c2e664d/view), university intake/enrolment figures, and per-polytechnic [O-Level aggregate cut-off points by course](https://data.gov.sg/datasets/d_eb7bb85a49e021e63f9cb7b54497a400/view). A meaningful slice of the polytechnic and school-directory data therefore has a **clean redistribution licence** — worth using preferentially wherever a choice exists.

### 3b. Data from moe.gov.sg, SEAB and university sites — restrictive

MOE's [Terms of Use](https://www.moe.gov.sg/terms-of-use) state that apart from fair dealing for private study, research, criticism or review, **no part of the website may be reproduced or reused for any commercial purpose without prior written permission**, and several MOE-affiliated sites additionally prohibit modification of materials and require a written permission request stating intent, manner, timeframe and identity.

**Design answers:**

1. **Encode facts, never prose.** A cut-off point, a grade-point value, an aggregate formula — these are facts, and facts are not what copyright protects. MOE's *explanatory wording, tables as laid out, diagrams and PDFs* are. PathAhead stores the fact and writes its own sentence.
2. **Deep-link, never mirror.** Every figure links to the official page it came from. The app is a pointer to the source, not a replacement for it.
3. **No bulk downloading, no wholesale republication, no scraping.** The Phase D watcher fetches a short allowlist at weekly cadence, respects `robots.txt`, and only diffs a hash to tell a human to go look ([DESIGN_REVIEW.md](DESIGN_REVIEW.md) §6). It never builds a mirror.
4. **Stay free and non-commercial.** MIT licence, no ads, no paid tier, no donations tied to the data. This keeps the project on the clean side of the "commercial purposes" line in MOE's terms — and if the project ever contemplates monetisation, this document must be revisited *first*, not after.
5. **Per-source licence in the pack schema.** Every source record carries a `licence` field (`sg-odl-1.0`, `moe-tou`, `moe-tou-linked`, `institution-tou`, …) so obligations travel with the data and the attribution block can be generated automatically rather than maintained by hand.
6. **Where answer 1 and answer 3 collide, answer 3 wins.** *Added 2026-08-14.*

   Answers 1 and 3 are in tension at the boundary, and the project walked into that boundary. "Facts are not copyrightable" is a real principle; "no wholesale republication" is a real limit; and a table of Posting Group cut-off points for 139 secondary schools is simultaneously a set of facts *and* a substantial dataset. For a fortnight the pack shipped that table while this document forbade it, and while the source record labelled its own licence *"no content reproduced"*. All three could not be true at once.

   The resolution is not a better argument. It is not shipping the data:

   - **The published pack carries no per-school cut-off figures at all.** Every school card deep-links to that school's own SchoolFinder page, and the reader gets the official figure at source — current, in MOE's framing, with MOE's caveats. Enforced by CI, not by intention (`No cut-off figures in any tracked pack`).
   - **A new licence id, `moe-tou-linked`,** marks a source PathAhead points at but holds nothing from. It exists so this distinction is visible in the data rather than remembered in prose.
   - **An individual may keep a private copy** for their own study at `packs/<id>/local/`, which is gitignored, merged in memory at load time, never written to a tracked file, and labelled in the UI as the reader's own rather than PathAhead's. See [docs/LOCAL_DATA.md](docs/LOCAL_DATA.md). Whether that is lawful for a given person is that person's call; the default is empty and the instructions point at the primary source.

   **The general rule this establishes:** where a fair-dealing argument would be *needed* to justify shipping something, do not ship it. A defensible argument is not the same as a settled question, and the people who would bear the cost of the argument failing are families using a free tool. Link out instead — it is the lawful position and, for anything that changes yearly, the more useful one.

   The unresolved item in §7 — a review by someone qualified in Singapore law — remains unresolved and is not substituted by any of the above.

**Attribution block, rendered in-app and in the README:**
> *Contains information from data.gov.sg, accessed under the [Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence). Other figures are cited to, and linked from, their official publisher. PathAhead is not affiliated with, endorsed by, or connected to any of these sources.*

---

## 4. Not official, not advice, not a prediction — and how to say so without a wall of text

Three separate claims are being disclaimed, and users read none of them if they arrive as one grey paragraph.

**(a) Not official.** No MOE, SEAB, school or university crest, logo, colour scheme or typeface. No product or repo name containing "MOE", "SEAB", "PSLE", "JAE" or an institution's name in a way that implies origin. Nothing that suggests official status — required both by the Open Data Licence's endorsement clause and by ordinary honesty.

> *PathAhead is an independent, open-source tool. It is not affiliated with, endorsed by, or connected to the Ministry of Education, SEAB, Cambridge Assessment, or any school, polytechnic, ITE or university.*

**(b) Not a prediction.** Indicative Grade Profiles are the 10th–90th percentile of the *previous* cohort admitted, not thresholds; MOE and the universities say so themselves. Cut-off points are historical. Admission at several institutions is explicitly holistic — interviews, portfolios, aptitude tests, and non-academic factors that no formula captures.

> *These are last year's numbers, not this year's outcome. Real admission decisions consider more than a score.*

**(b2) Two numbers with the same shape are not the same claim.** The pack holds three published statistics, and they are never converted into each other or described in each other's words:

| Statistic | Who | What the endpoints mean |
|---|---|---|
| `p10_p90` | NUS, NTU, SMU | 10th and 90th percentile — the middle 80%, both tails removed by construction |
| `BandedProfile` | SIT, SUSS | share of applicants in each published band who got through one stage |
| `min_max` | NYP, NP | the **lowest and highest ranked student admitted** — the entire cohort |

A min-max is necessarily wider than a p10-p90 drawn from the same intake. Rendering them alike would make a polytechnic course read as far less selective than it is, when the only difference is which statistic the institution chose to publish. `engine/buckets.py:assess_band()` raises rather than describe a `min_max` in percentile words, and `STATISTIC_WORDS` holds the two vocabularies apart. Guarded by `test_a_min_max_band_is_never_described_as_a_percentile_band`.

**(b3) A published figure is shown, and refused, when it is not the applicant's own.** Comparability is a property of *any* published figure. Where the basis does not match the score PathAhead computes for that transition, the numbers are shown in the publisher's terms and the verdict is withheld — never a silent conversion, and never a "no data" card that reads as a gap in the student.

Two cases exist today, and they are refused for **different** reasons, so they must not share copy:

- **SUSS and SIT** publish against the retired 90-point UAS while the AY2026 score is out of 70. A *retired scale*, same qualification.
- **The polytechnics** publish a net ELR2B2 **O-Level** aggregate. Not a retired scale — a *different qualification*, and one that no route makes the applicant's own: through JAE an A-Level holder is admitted on their O-Level results, and through the Direct Admissions Exercise there is no published aggregate at all. A polytechnic is also not a university, and copy that calls it one is wrong on the card.

Guarded by `test_every_polytechnic_band_declines_the_comparison` and `test_a_top_student_gets_no_verdict_on_a_polytechnic_course` — a student with AAA would otherwise clear all 80 polytechnic ranges at once.

**(b4) Years are exercises, not a pool.** Where several years of the same figure are published they are carried side by side and never merged. A union of three min-max ranges is a number nobody published, and it widens every year — so a course would look less selective the longer PathAhead had been running. The card names how many exercises it is showing, so a one-year figure and a three-year one cannot render identically.

**(c) Not advice.** The tool explains published rules. It does not tell a family what to choose.

> *This tool explains how the published rules work. It does not tell you what to choose. For decisions about your child's education, speak to their school's teachers and Education & Career Guidance counsellor, or the institution's own admissions office.*

**Placement rules — this is what makes disclaimers actually work:**

- The **not-a-prediction line appears with every result**, inline, in the same visual weight as the result — never only in a footer or an About page.
- The **not-official line appears in the app header, the README, and the repo description** — the three places someone forms an impression.
- Nothing is hidden behind an "I agree" gate that trains users to click through.
- Language stays at a **plain reading level** and structurally supports a Chinese / Malay / Tamil string pack, reusing BandUp's language-pack pattern. A disclaimer only the fluent can read is not a disclaimer.

Singapore's [Consumer Protection (Fair Trading) Act](https://sso.agc.gov.sg/act/cpfta2003) governs false or misleading representations in business-to-consumer transactions; a free tool with no transaction sits largely outside it, but **"do not make misleading representations" is the standard to hold regardless**, and is the reason the three-bucket result design in [DESIGN_REVIEW.md](DESIGN_REVIEW.md) §2 (Gap 2) matters more than any wording.

---

## 5. Wellbeing safeguards — the Singapore-specific ones

These are not legal requirements. They are the difference between a tool that helps and a tool that adds to a pressure this country already has plenty of. They are enforced in code and copy, not in a policy page.

1. **Never rank schools.** No "top schools" list, no league table, no default sort by cut-off point. Results sort by **fit, programme and location** — never by selectivity descending. This is the single easiest way for a tool like this to cause harm in Singapore, and it is entirely avoidable.
2. **Never a dead end.** Backward mode returns **at least three routes**, at least one of them non-direct — poly→degree, PFP, ITE→poly, SIT/SUSS/SUTD, retake, appeal ([DESIGN_REVIEW.md](DESIGN_REVIEW.md) Gap 4). Enforced by the engine, not by prompt wording.
3. **No verdict language.** Never "you missed the cutoff," "you don't qualify," "unrealistic." Instead: *"this course was more competitive than your current score in last year's exercise — here's what else is open."* A style guide with a banned-phrase list, checked in review, mirrors the `bannedPhrases` discipline already used elsewhere in this portfolio.
4. **No identity attached to a score.** No leaderboards, no sharing features, no comparison to "other users." The tool has no other users as far as any individual user is concerned.
5. **Holistic factors are never silently dropped.** Where a course uses interviews, portfolios or aptitude tests, the Outcome carries an explicit overlay flag and the UI shows it — omitting it would make the score look more decisive than it is.
6. **Point to humans, by name of role.** School teachers, the school's ECG counsellor, and the institution's admissions office — surfaced as a standing element of the results screen, not buried in an FAQ.
7. **A visible correction channel.** A "this number looks wrong" link on every figure, opening a pre-filled GitHub issue with the pack version and field id. A tool that claims citation rigour and offers no way to report an error has a hole exactly where its credibility should be.

---

## 6. AI-specific governance

Singapore's IMDA maintains the [Model AI Governance Framework](https://aiverifyfoundation.sg/wp-content/uploads/2024/05/Model-AI-Governance-Framework-for-Generative-AI-May-2024-1-1.pdf), extended to generative AI in 2024 and to [agentic AI in 2026](https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/press-releases/2026/new-model-ai-governance-framework-for-agentic-ai). It is **voluntary** — no compliance obligation attaches to an open-source hobby project. It is nonetheless worth mapping to, for two reasons: it is the regional reference standard, and it is directly on-brand for a maintainer whose public identity is *"AI Strategy, Agentic Systems & Governance."* A short `docs/AI_GOVERNANCE.md` mapping PathAhead's design to the framework's dimensions is a differentiating portfolio artifact that almost no comparable repo carries.

The substantive AI safeguards, independent of any framework:

- **The AI never produces a number.** Tier 0 is complete without a model; the narrator receives only the computed result object and is never asked to recall anything.
- **The numeric guardrail is enforcement, not intent.** Every number in generated prose must trace back to the result object, or the narration is rejected and the deterministic template output is shown instead ([DESIGN_REVIEW.md](DESIGN_REVIEW.md) §4). Adversarial prompts are part of the CI suite.
- **The pack-authoring copilot never ships in the user app.** It is the one component capable of inventing a figure; it lives in `tools/`, runs only for maintainers, and its output is a **draft pull request requiring human sign-off against a review checklist** — never a live data path.
- **AI is labelled where it is used.** When a narration is model-generated, the UI says so.
- **Non-local models trigger a persistent on-screen warning**, exactly as in BandUp — because at that moment the child's grades genuinely do leave the machine.

---

## 7. Pre-launch checklist

Nothing goes public before the ODBI line clears (`PLAN_ASSUME_NO.md`). When it does, this must all be true:

- [ ] No field anywhere collects a name, NRIC, school, email or contact detail
- [ ] No telemetry, analytics or crash reporting in any build; update check carries no identifiers
- [ ] "Delete everything" works, is one click, and is visible without hunting
- [ ] Not-official notice in app header, README and repo description
- [ ] Not-a-prediction line renders inline with **every** result
- [ ] Signpost to teachers / ECG counsellor / admissions office on the results screen
- [ ] data.gov.sg attribution block with a live link to the Open Data Licence
- [ ] Every fact carries `{as_of_year, source, licence, confidence, stale_after}`; Data Health CI gate green
- [ ] No MOE/SEAB/institution logos, crests, colours, or prose reproduced anywhere
- [ ] No school ranking, no default sort by selectivity, anywhere in the UI
- [ ] Backward mode returns ≥3 routes in every tested case, or an honest "route data incomplete"
- [ ] Banned-phrase copy review passed
- [ ] Numeric guardrail adversarial suite passing in CI
- [ ] "This number looks wrong" link live on every figure
- [ ] MIT licence, no ads, no paid tier, no data-linked donations
- [ ] Disclaimer wording and §3 data-licensing position reviewed by someone qualified in Singapore law

---

## Sources

- [Singapore's PDPC Issues Advisory Guidelines on the PDPA for Children's Personal Data in the Digital Environment — Bird & Bird](https://www.twobirds.com/en/insights/2024/singapore/singapore-pdpc-issues-advisory-guidelines-on-the-pdpa)
- [The protection of children's personal data in the digital environment: Singapore issues Advisory Guidelines — Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/9a61f19c/the-protection-of-childrens-personal-data-in-the-digital-environment)
- [Singapore Open Data Licence v1.0 — data.gov.sg](https://data.gov.sg/open-data-licence)
- [Terms of Use — MOE](https://www.moe.gov.sg/terms-of-use)
- [Nanyang Polytechnic GCE 'O' Level Aggregate Cut-Off-Points by Course — data.gov.sg](https://data.gov.sg/datasets/d_eb7bb85a49e021e63f9cb7b54497a400/view)
- [General information of schools — MOE, data.gov.sg](https://data.gov.sg/datasets/d_688b934f82c1059ed0a6993d2a829089/view)
- [Model AI Governance Framework for Generative AI — AI Verify Foundation / IMDA](https://aiverifyfoundation.sg/wp-content/uploads/2024/05/Model-AI-Governance-Framework-for-Generative-AI-May-2024-1-1.pdf)
- [New Model AI Governance Framework for Agentic AI — IMDA, 2026](https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/press-releases/2026/new-model-ai-governance-framework-for-agentic-ai)
- [Consumer Protection (Fair Trading) Act 2003 — Singapore Statutes Online](https://sso.agc.gov.sg/act/cpfta2003)

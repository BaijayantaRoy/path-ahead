# PathAhead — Singapore Research Brief

> Planning only — nothing here is built yet. Researched via web search on 2026-08-02; see §5 References. This is a **starting brief for the build phase, not settled fact** — every number and formula below must be re-verified against the primary MOE/SEAB/university source immediately before the corresponding stage is built, per this project's own design principle (ARCHITECTURE.md §3: nothing is a bare number). Treat anything sourced from a third-party explainer site below as `confidence: medium` until replaced with a primary citation.

Build order per the user's instruction: **A-Level → PSLE → O-Level/SEC.**

---

## 1. A-Level → University (build first)

**What it is:** GCE A-Level (Singapore-Cambridge), typically sat at the end of Junior College (2 years post-O-Level) or Millennia Institute (3 years). Feeds admission to NUS, NTU, SMU, SUTD, SIT, SUSS, and overseas universities.

**The scoring system changed in 2026** — this is the project's central, concrete justification (see README.md §1). As of 2026:

- **University Admission Score, "RP70"**, replacing the older 90-point Rank Points scale.
- Formula: **3 H2 subjects** (best/relevant three) at up to **20 points each** (60 max) + **General Paper** at up to **10 points** = **70 max**.
- A 4th H2 or H1 subject, and Mother Tongue Language, are counted **only if they improve the total** (a "best-of" substitution, not always-included).
- Grade points: H2 — A=20, B=17.5, C=15, D=12.5, E=10, S=5. H1 grades are worth half the equivalent H2 value.
- Result is compared against each university's own published **Indicative Grade Profile (IGP)** — the **10th and 90th percentile** score of the *previous* year's admitted cohort for that course, not a hard cutoff. MOE/the universities are explicit that IGP is indicative, and actual admission is holistic (interviews, portfolios, and non-academic factors apply for some courses, especially at SMU, SUTD, NUS/NTU specific programmes).

**DSA overlay:** Direct School Admission at the JC level (DSA-JC) lets Secondary 4 students with recognised talents/achievements apply directly to a JC before O-Level results are out; DSA-JC applicants forfeit the ordinary Joint Admissions Exercise route and cannot transfer JCs after results. This doesn't affect the *A-Level→University* transition directly but does affect *how a student arrived at* the JC stage — relevant for backward/goal-seeking mode (ARCHITECTURE.md §4), since "how do I get into a good JC" is a real upstream question for the same family asking about university outcomes.

**Must verify before build:**
- The exact current-year RP70 formula and grade-point table, direct from each university's admissions office page (this brief is sourced from aggregator/calculator sites, not the primary NUS/NTU/SMU pages — `confidence: medium`).
- Each university's current published IGP ranges per course (published fresh each admissions cycle — will not match a "2026" number by the time this stage is actually built).
- Whether SUTD/SIT/SUSS use RP70 identically or apply their own variant (they were not directly confirmed in this research pass).
- Holistic/non-academic admission factors per course (portfolio, interview, aptitude test) — these exist and must be represented as a caveat/overlay, not silently dropped.

---

## 2. PSLE → Secondary School (build second)

**What it is:** Primary School Leaving Examination, sat at the end of Primary 6 (age ~12). Determines secondary school posting.

**Scoring:** Achievement Level (AL) per subject — **English, Mathematics, Science, Mother Tongue** — each graded AL1 (best) to AL8 (weakest) against fixed benchmark bands (not cohort-relative), roughly: AL1 = 90–100 marks, AL2 = 85–89, AL3 = 80–84, AL4 = 75–79, AL5 = 65–74, AL6 = 45–64, AL7 = 20–44, AL8 = below 20. **PSLE Score = sum of the 4 subject ALs**, range **4 (best) to 32 (weakest)**.

**Posting:** Each secondary school has a historical **Cut-Off Point (COP)** range based on PSLE scores of students it admitted in prior years (roughly 4 at the most selective end, up to the low-to-mid 20s at the other). Since the **2024 Full Subject-Based Banding (Full SBB)** rollout, the old Express / Normal(Academic) / Normal(Technical) streams have been removed for new Secondary 1 cohorts; students are posted via **Posting Groups 1, 2, 3 (PG1/PG2/PG3)** instead, and can take individual subjects at different **subject levels (G1/G2/G3)** rather than being locked into one stream for every subject. **Foundation-level subjects** (for students who need them) are scored AL A–C rather than AL1–8 and mapped separately for posting.

**DSA overlay:** Direct School Admission at Secondary 1 (DSA-Sec1) lets a Primary 6 student apply to up to 3 school/talent-area combinations based on a portfolio (certificates, achievements, testimonials) before PSLE results are known; Integrated Programme schools admit a notably larger share via DSA (30–35%) than non-IP schools (up to 20%).

**Must verify before build:**
- Current-year PG1/PG2/PG3 posting mechanics and how COP ranges are now published under Full SBB (the "single COP per school" model is a legacy-system simplification; Full SBB may publish COP per posting group, not per school as a whole — needs primary-source confirmation).
- Current AL mark-band boundaries (these are reviewed periodically).
- DSA-Sec1 quota percentages and timeline for the specific admission year being modelled.

---

## 3. O-Level → JC / Polytechnic / ITE, transitioning to SEC (build third — deliberately last, and deliberately not "just O-Level")

**This stage cannot be scoped as "O-Level" alone.** Research surfaced a hard fact that reshapes it entirely:

- **2026 is the last year the GCE O-Level and N-Level qualifications are awarded.** The current Secondary 4 cohort (who started Sec 1 in 2023) is the final one to sit O-Level/N-Level under the existing system.
- From **2027**, O-Level and N-Level are replaced entirely by the **Singapore-Cambridge Secondary Education Certificate (SEC)** — the first SEC cohort is students who started Secondary 1 in 2024, sitting the new exam in 2027.
- **Post-secondary admission itself changes with it.** The first SEC-based Post-Secondary Admissions Exercise (**PSE**, replacing today's separate JAE/polytechnic/ITE exercises with one unified process) runs in **2028**. Under it: **JC qualifying aggregate becomes L1R4 ≤ 16** (replacing today's L1R5 ≤ 20 — a different subject-count formula *and* a different ceiling, not a rescaled version of the same one); polytechnics use an **adapted ELR2B2**; a new **ELMAB3** aggregate (computed on G2-equivalent grades) governs the Polytechnic Foundation Programme; ITE accepts **G1/G2 grades directly**, which previously required separate N-Level certificates.

**Today's (2026, legacy) system, for reference:** GCE O-Level holders need a gross **L1R5 aggregate ≤ 20** (1 Language + Relevant 5 subjects) to qualify for JC, or **L1R4 ≤ 20** for Millennia Institute. Polytechnics historically use **ELR2B2** (English, 2 Relevant, 2 Best). ITE evaluates **course-specific Minimum Entry Requirements (MERs)** rather than one universal aggregate. Actual net aggregate cutoffs per JC/course are published fresh each year via MOE's SchoolFinder/CourseFinder after JAE posting.

**The design consequence:** this stage's pack must model **two scoring-rule eras side by side from day one** — `o-level-legacy-2026.yaml` (L1R5/L1R4/ELR2B2, sunsetting) and `sec-2028.yaml` (L1R4≤16/adapted-ELR2B2/ELMAB3/G1-G2-direct, incoming) — exactly the multi-formula-by-year scenario ARCHITECTURE.md §2 is designed around. Building "just O-Level" here would ship a stage that's obsolete within roughly a year of release; building it as an explicit legacy/incoming pair is what makes this the strongest possible proof of the whole architecture, not just the hardest-to-avoid case.

**Must verify before build (this stage carries the most live policy risk of the three):**
- Whether MOE has published further SEC/PSE detail beyond what's summarized here by the time this stage is built — this is an actively evolving policy, publicly mid-rollout, and the single fastest-moving fact in this entire brief.
- The exact ELMAB3 formula and which schools/courses it governs.
- Whether DSA mechanics at the JC level (DSA-JC, §1) change under the PSE.
- Confirm the 2026 cohort is indeed the last O-Level cohort by the time this stage is built (this brief's most load-bearing single fact).

---

## 4. Cross-cutting notes for all three stages

- **Every official figure in this brief should be treated as `confidence: medium`** (sourced via aggregated web search, not verified against the primary MOE/SEAB/university PDF directly) until the build-time research pass replaces it with a primary source and bumps it to `high`. This brief's job is to make that build-time pass fast, not to replace it.
- **Primary sources to track going forward:** `moe.gov.sg` (PSLE, JAE, PSE, DSA sections), `seab.gov.sg` (SEC/O-Level examination specifics), each university's own admissions office page (NUS/NTU/SMU/SUTD/SIT/SUSS) for IGP publications, and MOE's SchoolFinder/CourseFinder tools for net aggregate/COP data released after each posting cycle.
- **None of this should be scraped in bulk or republished wholesale** — cite and link, the same posture BandUp already takes toward SEAB rubric descriptors.

## 5. References (search-sourced, 2026-08-02 — replace with primary citations at build time)

- [PSLE AL Score Explained: Achievement Levels, Calculator & Posting Groups (2026)](https://www.brightstartsg.com/guides/psle-explained)
- [PSLE Scoring System 2026: AL1-AL8 Bands & Cut-Off Points](https://ancourage.academy/articles/psle-scoring-system-guide-singapore)
- [Joint Admissions Exercise (JAE) — MOE](https://www.moe.gov.sg/post-secondary/admissions/jae)
- [JAE 2026 Web FAQ (PDF) — MOE](https://isomer-user-content.by.gov.sg/145/02de4e60-d167-4e1a-aa44-50ceef017642/JAE-2026-WebFAQ.pdf)
- [Joint Admissions Exercise (JAE) — ITE entry via GCE O-Level](https://www.ite.edu.sg/secondary-school-students/admissions/entry-qualifications/gce-o-level/for-gce-o-students-jae/)
- [A-Level Rank Points 2026: How RP Is Calculated for University Admission](https://www.smartcalculator.sg/articles/a-level-rank-points-2026)
- [A-Level Rank Point Calculator Singapore — 70 Point System (2026)](https://www.universities.sg/calculator/)
- [Compare NUS NTU SMU IGP AY2026/2027](https://sgschoolkaki.com/university-igp-comparison-2025-2026)
- [Singapore Overhauls Secondary Education: O-Levels, N-Levels Out by 2027 — AACRAO](https://www.aacrao.org/edge/emergent-news/singapore-overhauls-secondary-education-o-levels-n-levels-out-by-2027/)
- [Understanding Full-Subject Based Banding (FSBB)](https://geniebook.com/exam-preparation/gce-o-level/article/everything-about-full-subject-based-banding)
- [Full Subject–Based Banding (Full SBB) — MOE Meridian Secondary](https://www.meridiansec.moe.edu.sg/student-information/full-sbb/)
- [Secondary Education Certificate (SEC) — SEAB](https://www.seab.gov.sg/secondary-education-certificate-sec/)
- [Would there still be GCE N(T)-/N(A)- and O-Level qualifications in or after 2027? — SEAB](https://ask.gov.sg/seab/questions/cmkkrkf6c0019pnhlauyrt2mj)
- [SEC Exam Grades Explained: Scoring, JC/Poly Admission (2027)](https://ingelsoong.com/sec-exam-grades-jc-poly-admission-2027/)
- [Direct School Admission for junior colleges (DSA-JC) — MOE](https://www.moe.gov.sg/dsa-jc)
- [DSA Singapore 2026: Complete Guide to Direct School Admission](https://sgschoolkaki.com/blog/dsa-singapore-2026-guide)

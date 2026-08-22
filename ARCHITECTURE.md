# PathAhead — Architecture

> **This document is the original design. It has been superseded in four places by [DESIGN_REVIEW.md](DESIGN_REVIEW.md), which is what was actually built** — read that alongside this one, and prefer it where they disagree. The four changes: rule *kinds* replaced the formula-string DSL (§2 here), `Cohort` and `Prerequisite` joined the core model (§1), eligibility and competitiveness were split into named buckets (§4), and the Data Health report became a CI gate rather than a release artifact (§3).
>
> For the shipped code, `engine/` is the source of truth and its module docstrings explain the reasoning inline.

---

## 1. Core abstraction: the Pathway Graph

Every country's exam-to-next-stage system reduces to the same shape: a graph of **Stages** connected by **Transitions**, each Transition governed by a **Scoring Rule** that maps a student's results to a set of **Outcomes**.

```
CountryPack (e.g. singapore/)
 └─ Stage            (psle, o-level-sec, a-level)
     └─ Transition    (psle→secondary, o-level→jc-poly-ite, a-level→university)
         ├─ ScoringRule   (dated, versioned — see §2)
         ├─ Outcome[]     (specific schools/JCs/polys/unis/courses)
         └─ Overlay[]     (DSA, Foundation-level subjects, appeals — side paths onto the main rule)
```

**Stage** — what exam this is, who sits it, at what age, under whose authority (SEAB, a university consortium, etc.). Stages are largely static metadata.

**Transition** — the actual decision point. This is where almost all the complexity and all the yearly churn lives. A Transition is never a single hardcoded formula — see §2.

**ScoringRule** — a declarative, dated formula. Singapore alone needs at least three fundamentally different *shapes* of scoring rule live in the same year (2026):
- **Sum, lower-is-better, fixed bands** — PSLE: sum of four Achievement Levels (AL1–AL8 per subject), range 4–32, school Cut-Off Points are historical ranges.
- **Weighted sum with substitution, lower-is-better, legacy** — O-Level: L1R5 (1 Language + Relevant 5) or L1R4 for Millennia Institute, gross aggregate ≤ 20 to qualify for JC/MI.
- **Weighted sum with substitution, HIGHER-is-better, normalised to a fixed ceiling, and holistic on top** — A-Level: RP70 — three H2 subjects (A=20…S=5 each) + General Paper (max 10) = up to 70, with a 4th H2/H1 and Mother Tongue counted only if they *improve* the score, then compared against each university's published Indicative Grade Profile (a 10th–90th percentile *range*, not a cutoff).

And a **fourth shape enters in 2027–2028**: SEC replaces O-Level with G1/G2/G3 subject levels, and the post-secondary aggregate becomes L1R4 ≤ 16 for JC (a *different* ceiling and formula from the L1R5 it replaces), an adapted ELR2B2 for polytechnics, a new ELMAB3 for the Polytechnic Foundation Programme, and direct G1/G2 acceptance for ITE — live alongside the outgoing L1R5 formula during the transition years. **This is not a hypothetical stress-test of the design — it is the literal, dated, sourced reality this project ships into.** See SINGAPORE_RESEARCH.md for the full citation trail.

**Outcome** — a destination node (a specific JC, polytechnic course, or university programme) carrying its own historical data: COP ranges, IGP bands, whether DSA is a live alternate path onto it, links to the school/faculty's own admissions page.

## 2. Scoring rules are data, not code — a safe formula DSL

The only way "config, not code" survives contact with four different formula shapes (and community-contributed country packs later) without becoming an unreviewable pile of special cases is a small, declarative expression language — not a place where a pack can execute arbitrary Python.

Sketch (illustrative, not final syntax):

```yaml
# packs/singapore/stages/a-level/transitions/university-2026.yaml
id: a-level-to-university
as_of_year: 2026
direction: higher_is_better
ceiling: 70
source:
  url: https://www.universities.sg/  # illustrative — replace with the actual official IGP/RP publication at build time
  retrieved: 2026-08-02
  confidence: medium   # "medium" because this was sourced via search, not the primary MOE/university PDF — build-time task: replace with primary source
formula: >
  min(70,
    top_n_h2(subjects, 3, grade_points) +
    grade_points(general_paper, halved=false) +
    best_of(
      grade_points(fourth_subject, halved=is_h1(fourth_subject)),
      grade_points(mother_tongue, halved=is_h1(mother_tongue))
    )
  )
grade_scale:
  h2: { A: 20, B: 17.5, C: 15, D: 12.5, E: 10, S: 5 }
  h1: { A: 10, B: 8.75, C: 7.5, D: 6.25, E: 5, S: 2.5 }
```

`top_n_h2`, `grade_points`, `best_of` are the *entire* function surface the DSL exposes — a fixed library of safe, pure, side-effect-free primitives (evaluated with something like Python's `simpleeval`, not `eval()`), so a pack is reviewable by reading it, and a malicious or broken pack can't do anything worse than compute a wrong number. This matters more here than in BandUp, because a country pack could plausibly come from an outside contributor later, whereas an exam rubric pack is lower-stakes and more likely self-authored.

**The versioning discipline that follows from this:** `a-level/transitions/university-2025.yaml`, `university-2026.yaml`, and eventually `university-2027-sec-transition.yaml` all coexist. The engine picks the rule whose `as_of_year` matches the admission cycle being asked about, and a `changed_from` field lets the tool proactively say *"heads up — this differs from last year's formula"* rather than silently applying whichever file happens to load last.

## 3. The data contract: nothing is a bare number

Every value the engine surfaces — a COP, an IGP band, a grade-point table entry — carries the same envelope:

```yaml
value: 20
as_of_year: 2025
source: { name: "MOE SchoolFinder", url: "...", retrieved: "2026-08-02" }
confidence: high | medium | low   # high = primary official publication; medium = reputable secondary source; low = inferred/estimated
```

The engine refuses to render a number without this envelope. The UI always shows the year and, on request, the source — the same "unofficial, here's our calibration" honesty BandUp already applies to SEAB band descriptors. A **Data Health report** (mirroring BandUp's eval-benchmark credibility artifact) ships with every release: how many facts per pack, how many are `high` vs `medium` vs `low` confidence, how stale the oldest one is. That report is a fork-worthy artifact in its own right — it's the thing that lets a stranger trust the tool without trusting the author.

## 4. Two engine modes

**Forward mode** — "here's my result, what are my options": walk from a Stage's actual score through its Transition's ScoringRule to the set of eligible/likely Outcomes, each annotated with its confidence band (not a single verdict).

**Backward / goal-seeking mode** — "I want Course X at University Y — what do I need, and what's the realistic path there": walk the graph in reverse from a named Outcome, back through its Transition's ScoringRule to the score/grade combination required, then further back through the *previous* Stage's Transition to check that combination is even reachable from where the student is now (e.g., "you'd need H2 Chemistry — does your current subject combination allow adding that at A-Level, or does it depend on a Sec 4 combined-science choice you made two years ago"). This second mode is the genuinely novel one — nothing public does multi-hop backward planning across Singapore's pathway stages today.

Both modes are pure graph/arithmetic operations. The LLM sits *outside* this and never computes a number itself (see §5).

## 5. Where AI actually adds value (and where it deliberately doesn't)

The scoring engine needs zero AI to work — it's data plus arithmetic. AI's job is everywhere *around* that core, and this is where the "AI angle" for this specific tool must be made explicit and real, not bolted on:

1. **Config-authoring copilot — the flagship AI capability.** Feed it a country's raw official documents (MOE circulars, university admissions PDFs, exam-board FAQs); it drafts a candidate Country Pack — Stages, Transitions, a proposed ScoringRule expression, Outcome data — with every extracted number linked back to a page/URL and a confidence flag, plus a structured human-review checklist before merge. This is the actual answer to "make it a full research + configuration plugin thing": turning "add a new country" from a multi-week manual research slog into an AI-drafted, human-verified pull request. Reuses Docling for PDF parsing, matching the portfolio's existing default.
2. **Constrained narrator.** Turns the engine's structured, cited output into plain-English explanation, tone-adjusted for student vs. parent vs. counsellor view (§6) — but is only ever allowed to narrate numbers the engine already computed and cited. It cannot introduce a figure that didn't come from a ScoringRule evaluation. This constraint is enforced structurally (the narrator's prompt receives only the computed result object, never asked to "recall" a cutoff from its own training), not just requested politely.
3. **Backward-goal dialogue.** Multi-turn conversation orchestrating the backward-mode engine call (§4) — "what if I dropped H2 Further Math," "what if I aimed for NTU instead of NUS" — the LLM plans which engine queries to run and stitches the narrative together; the underlying numbers are still deterministic per query.
4. **Results-slip OCR (reuse, not new build).** Photograph a PSLE/O-Level/A-Level results slip; reuse BandUp's existing VLM OCR pipeline verbatim to extract subject grades as structured input, instead of manual entry.
5. **Citation verification layer.** Every claim the narrator makes gets checked against the retrieved source text using the same NLI/entailment approach planned for **rag-that-cites** (BGE-M3 embeddings + reranker + HHEM-2.1-Open/DeBERTa-NLI) — unverifiable narration is flagged before it reaches the user. Strongly consider building this alongside or just after rag-that-cites so PathAhead inherits the verification engine rather than re-deriving it.

## 6. Multi-view rendering

Same underlying result, three tones — directly reusing BandUp's teacher/student dual-mode pattern rather than inventing a fourth UX paradigm for the portfolio:

- **Student view** — simple, encouraging, one clear "here's what this means for you" framing, minimal jargon.
- **Parent view** — full transparency: every source, every confidence flag, historical trend across the last several admission cycles, explicit "this is a range, not a promise" framing given the real anxiety this topic carries in Singapore.
- **Counsellor/school view** — batch mode across a cohort, exportable, same citation rigor, closest analogue to BandUp's teacher batch-marking mode.

## 7. Extending to a new country (the actual "plugin" workflow)

1. Point the config-authoring copilot (§5.1) at the new country's official admission documents.
2. Copilot drafts `packs/<country>/` — Stages, Transitions, ScoringRule expressions, Outcome data, all cited.
3. Human reviews the draft against the checklist (does every number have a `high`-confidence primary source; does the formula direction — higher/lower-is-better — match reality; do the Stage names match local terminology).
4. Run the pack against the shared eval harness (§8) — a handful of known, published real cases ("this student's known results → this known outcome") to sanity-check the ScoringRule before merge.
5. Merge. The generic engine (forward mode, backward mode, multi-view rendering, citation layer) requires zero new code — the entire deliverable is the pack.

A second, non-Singapore pack (candidates: UK GCSE→A-Level→UCAS, or India Class 10→Class 12→JEE/NEET — whichever turns out to have the cleanest single official public formula) should exist before the project claims to be "a general framework" rather than "a Singapore tool with aspirations." That's a Roadmap item, not a v1 blocker — see ROADMAP.md.

## 8. Eval harness (the credibility artifact, BandUp-style)

A set of real, published historical cases per Transition — e.g., "a student admitted to NUS Computer Science in the 2025 cycle with these H2 grades" sourced from published IGP data — that the engine must reproduce correctly (within the honest range it claims, not a false exact match). This is the same trust-building move as BandUp's 20-composition calibration set, applied to pathway data instead of essay marking.

## 9. Indicative repo layout

```
path-ahead/
├── engine/            # forward + backward graph walker, DSL evaluator — country-agnostic
├── packs/
│   └── singapore/
│       ├── psle/
│       ├── o-level-sec/     # models BOTH the outgoing O-Level and incoming SEC formulas
│       └── a-level/
├── copilot/           # config-authoring assistant (Docling ingestion + drafting + citation check)
├── verify/            # NLI/citation verification layer (shared lineage with rag-that-cites)
├── ui/                 # student / parent / counsellor views
├── evals/              # per-transition calibration cases
└── docs/
```

This mirrors `psle-composition-coach`'s existing `app/ · assets/ · config.yaml · data/ · docs/ · evals/ · tests/` shape closely enough that anyone familiar with BandUp's repo will find their way around this one immediately — intentional, for portfolio coherence.

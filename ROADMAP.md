# PathAhead — Roadmap

> **Status update, 2026-08-02: Phase A is built.** v0.1.0 ships the engine, the Singapore A-Level pack, the CLI, the browser app, 80 tests, the cross-engine golden check, the Data Health gate and CI. See [CHANGELOG.md](CHANGELOG.md) for exactly what landed and what did not. The phase table below is kept as written for the record; the amendments in [DESIGN_REVIEW.md §8](DESIGN_REVIEW.md) are the ones that were actually followed — Cohort, the three-bucket split, the derivation trace and the Data Health gate all moved into A1 rather than arriving later.
>
> Still ahead: PSLE (Phase B), O-Level/SEC (Phase C), the remaining five universities, and the optional AI tiers. Nothing is published publicly until the ODBI gate clears.

> Original planning note: this is the build sequence, portfolio slot, risk register, and the open decisions only the user can make.

---

## 1. Why build the A-Level stage first (validating the instinct, not just following it)

Building the *hardest* stage first is the right call, for a concrete architectural reason: A-Level → University is the only one of the three Singapore transitions that is simultaneously **multi-institution** (six local universities, each with its own IGP), **higher-is-better with substitution logic** (best-of-4th-subject-or-Mother-Tongue), **normalised to a shifting ceiling** (the 2026 RP90→RP70 change), and **explicitly holistic on top of the formula** (IGP is a percentile range, not a cutoff, and some courses add interviews/portfolios). PSLE (single formula, sum, lower-is-better, one national posting system) and O-Level (two formulas at most, legacy + incoming SEC) are both strictly simpler shapes of the same underlying graph.

If the engine and formula DSL (ARCHITECTURE.md §1–2) can represent A-Level cleanly, PSLE and O-Level become "write a pack," not "extend the engine." Building the easy case first would risk discovering — after PSLE is "done" — that the engine's assumptions don't hold for A-Level's messier shape, forcing a rewrite. Hardest case first is the sequencing that avoids that.

---

## 2. Phase breakdown

### A-Level → University (Phase A, build first)

| Phase | Deliverable | Effort |
|---|---|---|
| A1 | Pathway-graph data model + safe formula DSL engine + Singapore A-Level pack (RP70, all 6 local universities, primary-sourced grade tables and current IGPs) — CLI only | 2 weekends |
| A2 | Backward/goal-seeking mode + what-if simulator (retake a subject, drop the 4th H2/H1, add H3) | 1–2 weekends |
| A3 | Constrained narrator (plain-English, cited) + student/parent/counsellor views | 1 weekend |
| A4 | Results-slip photo input (reuse BandUp's VLM OCR) + DSA-JC overlay | 1 weekend |
| A5 | Citation/trust layer + eval harness (real published IGP cases) + Data Health report | 1–2 weekends |

**Definition of done:** typed or photographed H1/H2/H3 + GP grades → a cited, ranged list of realistic university/course options, a working backward-mode query ("what do I need for Course X"), and a published Data Health report showing source confidence across the pack.

### PSLE → Secondary (Phase B, build second)

| Phase | Deliverable | Effort |
|---|---|---|
| B1 | Singapore PSLE pack (AL1–8, COP ranges, Full SBB / PG1-PG2-PG3 posting model) on the existing engine | 1 weekend |
| B2 | DSA-Sec1 overlay + backward mode ("I want School X, what AL do I need") | 1 weekend |
| B3 | Narrator/views/OCR reuse (mostly free — built in Phase A) + eval harness | 3–4 hrs |

**Definition of done:** 4 subject Achievement Levels in → a realistic school range with historical COP trend and a DSA note, cited.

### O-Level → JC/Poly/ITE, transitioning to SEC (Phase C, build third — deliberately last)

| Phase | Deliverable | Effort |
|---|---|---|
| C1 | Legacy O-Level pack (L1R5/L1R4, adapted ELR2B2, ITE MERs) — the outgoing system | 1 weekend |
| C2 | Incoming SEC/PSE pack (L1R4 ≤ 16, adapted ELR2B2, ELMAB3, direct G1/G2 for ITE) with a prominent "this system is mid-rollout, verify current status" banner | 1–2 weekends (more research-heavy — this is the fastest-moving policy area in the whole project) |
| C3 | Cohort-year routing: detect whether a student's cohort sits legacy O-Level or SEC and select the right pack automatically | 3–4 hrs |
| C4 | Eval harness + Data Health report | half day |

**Definition of done:** correctly routes a 2026-cohort student to legacy O-Level rules and a 2024-Sec-1-cohort (first SEC, 2027) student to SEC rules, both cited, with the transition itself explained in plain English.

### Generalization (Phase D, after Singapore ships)

| Phase | Deliverable | Effort |
|---|---|---|
| D1 | Document and package the config-authoring copilot as a usable, standalone contributor tool | 1 weekend |
| D2 | Second country pack as proof-of-concept (candidates: UK GCSE→A-Level→UCAS; India Class 10→Class 12→JEE/NEET — pick whichever has the cleanest single public formula) | 1–2 weekends |

This phase is what earns the "open framework," not just "Singapore tool," positioning — it shouldn't be skipped, but it's explicitly *after* all three Singapore stages, not a v1 blocker.

---

## 3. Portfolio sequencing — proposed slot change

`PORTFOLIO_PLAN.md` currently has this as P2: `requirements-copilot` (a BA/professional tool, not edtech). The user wants this project **second**. Proposal — **not yet applied to `PORTFOLIO_PLAN.md` or the parent `_cc/meta.json`, pending go-ahead:**

```
P1  psle-composition-coach (BandUp)   — done, v2.3.0
P2  path-ahead                        — NEW, this project
P3  requirements-copilot              — was P2, bumped one slot
P4  doc2exam                          — was P3
P5  fine-tune release                 — was P4
P6  voice-tutor                       — was P5
P7  rag-that-cites                    — was P6
```

**Worth deciding explicitly (§5, open question):** ARCHITECTURE.md's trust layer (§5.5) wants to reuse rag-that-cites' NLI verification engine, but rag-that-cites is currently P7 — after path-ahead. Two ways to resolve this, not mutually exclusive: (a) path-ahead ships v1 with a lighter interim citation check and adopts the full rag-that-cites engine once that repo exists, or (b) pull rag-that-cites' verification-layer work forward to run alongside path-ahead Phase A5. Recommend (a) — don't let one repo's sequencing hold another hostage — but flagging since it's a real cross-repo dependency, not a hypothetical one.

---

## 4. Risk register

- 🔴 **Policy volatility** — the SEC/PSE system (Phase C) is still mid-rollout; details available today may be incomplete or change again before Phase C is actually built. Mitigation: Phase C is scheduled last, buying the most possible research runway, and its pack is explicitly versioned/dated per ARCHITECTURE.md §2 rather than treated as settled.
- 🔴 **False-precision / emotional-stakes risk** — this tool touches real family anxiety around a child's academic future. Mitigation: ranges and confidence bands everywhere (never a bare cutoff), explicit "unofficial, not affiliated with MOE/SEAB/any university" disclaimers, tone calibrated per view (§ARCHITECTURE §6), never a promise of an outcome.
- 🟠 **Holistic-admission risk** — A-Level→University (and some DSA routes) include interviews, portfolios, and aptitude tests that no formula captures. Mitigation: represent these as explicit overlay flags on the relevant Outcome nodes, never silently dropped.
- 🟠 **Data licensing/ToS risk** — official data must be cited and linked, never scraped in bulk or republished wholesale, same posture BandUp takes toward SEAB rubric descriptors.
- 🟠 **Community-pack trust/security risk** — once contributions are accepted, a malicious or broken pack is a real concern. Mitigation: the safe formula DSL (ARCHITECTURE.md §2) has no arbitrary code execution surface, by construction.
- 🟡 **Scope creep** — DSA depth, IB as an A-Level alternative, overseas university pathways, and the second-country pack are all tempting to front-load. Mitigation: each phase above has an explicit Definition of Done; anything past it is a v2/Phase D+ item, not a silent scope expansion.
- 🟡 **ODBI/employment gate** — same constraint as the rest of this portfolio: build privately, publish only after the ODBI approval line clears, per `PLAN_ASSUME_NO.md`. No change from how BandUp is already being handled.

---

## 5. Open questions — only the user can decide these

1. ~~**Final name**~~ — **Decided 2026-08-02: PathAhead.** Folder renamed `pathway-os` → `path-ahead` accordingly. See README.md §6 for the full decision trail (several earlier candidates turned out to collide with real existing products).
2. **Update `PORTFOLIO_PLAN.md` and the parent `_cc/meta.json` now, or wait for go-ahead?** Left untouched for this pass, per "don't start anything yet" — ready to update the moment you say go.
3. **v1 DSA depth** — both Sec1-DSA and JC-DSA in v1, or start with just one and add the other later?
4. **Is IB in scope at all?** Some Singapore schools offer the International Baccalaureate as an A-Level alternative. Recommend explicitly **out of v1**, flagged for a later phase — confirm.
5. **rag-that-cites sequencing** (§3) — ship path-ahead v1 with an interim citation check and adopt the full engine later, or pull rag-that-cites forward? Recommend the former.
6. **Second-country candidate** (Phase D2) — UK, India, or something else? Or defer the decision entirely until Phase A–C are done?
7. **Live data-refresh pipeline** — is an automated "watch MOE/university pages for changes" pipeline in scope for v1, or is v1 manually-updated-yearly with the refresh pipeline a v2 ambition? Recommend the latter for v1 — it's a meaningfully bigger and riskier (ToS-sensitive) build than the rest of Phase A–C combined.

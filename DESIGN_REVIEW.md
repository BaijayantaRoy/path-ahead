# PathAhead — Design Review

> Planning only — still nothing built. This document reviews [ARCHITECTURE.md](ARCHITECTURE.md) and [ROADMAP.md](ROADMAP.md) against four decisions taken on 2026-08-02, and proposes concrete changes before any code is written.
> Companions: [README.md](README.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [SINGAPORE_RESEARCH.md](SINGAPORE_RESEARCH.md) · [ROADMAP.md](ROADMAP.md) · [SAFEGUARDS.md](SAFEGUARDS.md)
> Portfolio context: [PORTFOLIO_PLAN.md](../PORTFOLIO_PLAN.md) · [MODEL_STACK.md](../MODEL_STACK.md) · reference implementation: [BandUp](../psle-composition-coach/)

---

## 0. Decisions taken (2026-08-02)

| # | Question | Decision |
|---|---|---|
| 1 | Install story | **Part of the GitHub portfolio strategy — same shape as BandUp, plus an installer.** Expanded in §5 into a three-tier model, because PathAhead can go *further* than BandUp here. |
| 2 | AI posture | **No-AI core, optional AI extras.** Nothing about the tool is blocked by having no key and no GPU. |
| 3 | Data refresh | **Signed pack releases, app auto-checks staleness on launch.** |
| 4 | Ambition | **A real public tool Singapore families use** — so safeguards are designed in now, not retrofitted. |

Decision 4 is the one that changes the most. A portfolio artifact can have a disclaimer paragraph. A tool a worried parent actually opens at 11pm the night before JAE closes needs the safeguards to be *structural* — in the data model, the copy, and the default screen — not in a footer. That premise runs through everything below and is spelled out in [SAFEGUARDS.md](SAFEGUARDS.md).

---

## 1. What the existing architecture gets right — keep, don't touch

Four things in ARCHITECTURE.md are load-bearing and correct, and this review does not weaken any of them:

1. **Scoring rules as dated, versioned, cited configuration** rather than code. The 2026 RP90→RP70 change and the 2027 O-Level→SEC replacement already prove the point; this is the whole reason the project is worth building.
2. **The LLM never computes a number.** §5's trust boundary is right, and §4 below makes it *enforceable* rather than merely intended.
3. **Every value carries `{value, as_of_year, source, confidence}`.** No bare numbers. This is the difference between this tool and every calculator site currently ranking on Google.
4. **Hardest transition first (A-Level → University).** The sequencing argument in ROADMAP §1 is sound — if the model can express RP70's substitution-and-ceiling shape, PSLE and O-Level/SEC are pack-writing, not engine work.

Everything below is either a gap, a mis-sized component, or a consequence of Decision 4.

---

## 2. The five structural gaps

### Gap 1 — `Cohort` is missing from the core model, and it is the first thing a user knows about themselves

The architecture routes on `as_of_year`. But a family does not know "which admission cycle am I in" — they know **"my child is in Secondary 2 this year."** Everything else is derivable from that one fact, and getting it wrong is catastrophic in exactly the years this tool ships into:

- A child in Sec 4 in 2026 sits **O-Level**, enters **JAE** in 2027, under **L1R5 ≤ 20**.
- A child in Sec 3 in 2026 started Sec 1 in 2024, sits **SEC** in 2027, enters the **PSE** in 2028, under **L1R4 ≤ 16**.

One school year apart, two entirely different rulebooks. If the app asks "which year are you applying for?" a parent will guess, and the tool will confidently apply the wrong formula — the exact failure mode the whole project exists to prevent.

**Change:** make `Cohort` a first-class entity in the A1 data model. The app's first question is *"What year is your child in now?"* (plus school type where ambiguous). `Cohort` resolves deterministically to `(stage, exam_year, admission_year, rule_version)`, and the app states the resolution back in plain words: *"So: SEC in 2027, post-secondary admission in 2028, under the new L1R4 rules."*

ROADMAP currently has this as **C3, "3–4 hrs"**. It belongs in **A1**. Cohort routing is not a late convenience; it is the index into the entire versioned-rule design, and building the engine without it means every rule lookup gets refactored later.

### Gap 2 — Eligibility and competitiveness are conflated, and they carry completely different truth values

Two questions hide inside "what are my options," and they are not the same kind of claim:

| | Eligibility | Competitiveness |
|---|---|---|
| Example | "L1R5 ≤ 20 qualifies you for JC" | "Your 68 vs. NUS CS's 2025 IGP band of 69–72" |
| Nature | Hard, published, binary | Soft, historical, indicative |
| Can the tool assert it? | **Yes** — it's a stated rule | **No** — only "here is last year's range" |
| Changes when? | On policy change | Every single cycle |

Rendering both in the same list, in the same colour, with the same confidence, is precisely how a careful tool becomes a misleading one.

**Change:** every Outcome is returned in one of three explicitly-named buckets, never a score or a verdict:

- **Meets the stated requirement** — deterministic, cited, safe to assert.
- **Within last year's admitted range** — with the band and the year shown inline, always.
- **Below last year's admitted range** — phrased as *"more competitive than your current score last cycle,"* never *"you missed the cutoff,"* and never without alternate routes attached (Gap 4).

### Gap 3 — Backward mode needs a `Prerequisite` graph, or it is just the calculator run in reverse

ARCHITECTURE §4 makes the right claim: multi-hop backward planning is the genuinely novel capability. But the example it gives — *"you'd need H2 Chemistry — does your current subject combination allow that, or did it depend on a Sec 4 choice you made two years ago"* — cannot be answered by any scoring rule. It needs a **different kind of data the model doesn't have**: subject prerequisite chains, subject-combination constraints, and school-level subject availability.

Without it, backward mode degrades to "solve the arithmetic for the target number," which several calculator sites already approximate. With it, the tool can say the thing no one else says: *"That route needs H2 Chemistry, which needs O-Level Pure or Combined Chemistry — check your Sec 3 subject choice before committing to this goal."*

**Change:** add `Prerequisite` as a fourth entity alongside Stage / Transition / Outcome — edges carrying `{requires, at_stage, source, confidence}`. Scope it *narrowly* for v1 (A-Level H2 subject prerequisites for the highest-demand university courses only); breadth is a later pack-authoring problem, not an engine one.

### Gap 4 — Backward mode has an unnamed safety problem, and its fix is also the product's best feature

"To read Medicine at NUS you need AAA/A" is an accurate sentence that, delivered to a 15-year-old on a screen with no other content, becomes a verdict on their worth. A disclaimer does not fix this. A **design rule** does.

**Change — non-negotiable, enforced in the engine, not the prompt:** backward mode never returns a single path. It returns **at least three**, and at least one must be a non-direct route. Singapore genuinely has these and no public calculator surfaces them:

- polytechnic diploma → university degree (with advanced standing at some faculties)
- Polytechnic Foundation Programme; ITE → poly progression
- SIT / SUSS / SUTD as different-shaped rather than lesser routes
- retake, appeal, and later-entry routes, with their real constraints stated

If the pack cannot supply three routes for a given Outcome, the engine returns "route data incomplete for this destination" rather than a lone hard number. This is simultaneously the ethical safeguard and the single most differentiating feature in the whole design — the entire existing market of calculators answers "did I make it," and none answers "what else is open."

### Gap 5 — The data, not the engine, is the actual project — and the repo is shaped as if the opposite were true

The engine is arithmetic over a graph: realistically low thousands of lines, and finished early. The real work is keeping correct: 6 universities × ~150 courses of IGP bands, ~140 secondary schools' COP ranges under Full SBB posting groups, 5 polytechnics × ~200 courses, ITE MERs — all republished every cycle, under two coexisting rulebooks during 2027–2028.

That reframing has three consequences the current layout doesn't reflect:

1. **Packs must version and ship independently of the app** (this is Decision 3 — see §6).
2. **The Data Health report must be a CI gate, not a release artifact.** ARCHITECTURE §3 describes it as a published credibility report. Make it a build check too: a PR that leaves a required field at `low` confidence, or that ships a fact past its `stale_after` date, fails. Credibility that is merely *reported* drifts; credibility that is *enforced* holds.
3. **The pack-authoring copilot is a maintainer tool, and must never ship inside the user app** (see §4).

---

## 3. Right-sizing the formula DSL — keep the idea, change the shape

ARCHITECTURE §2's instinct is correct (data, not code; no arbitrary execution). The proposed *implementation* — a free-text formula string evaluated by `simpleeval` — is the wrong trade for two reasons.

**Reason 1: an expression evaluator returns a number, and the number is not the product.** For a parent, this is the product:

```
Your best 3 H2 subjects
  H2 Chemistry      A   →  20.0
  H2 Biology        A   →  20.0
  H2 Mathematics    B   →  17.5                    subtotal  57.5
General Paper       A   →  10.0                    subtotal  67.5
Bonus — best of your 4th subject or Mother Tongue
  H1 Economics      C   →   7.5
  Mother Tongue     B   →   8.75  ← counted        subtotal  76.25
Capped at the 70-point maximum                     TOTAL     70.0
```

That derivation trace is what earns trust, what makes the tool teachable, and what makes a wrong pack *visibly* wrong instead of quietly wrong. A string expression gives you `70.0` and nothing else.

**Reason 2: a fixed set of rule shapes is more reviewable than a free grammar.** Singapore needs three shapes today and a fourth in 2027 — not arbitrary expressions.

**Change:** rules are declared as a **named rule kind plus typed parameters**, and the evaluator emits `(value, trace[])` rather than a scalar.

```yaml
# packs/singapore/a-level/transitions/university-2026.yaml
id: a-level-to-university
cohort_applies_to: { exam_year: 2026, admission_year: 2027 }
direction: higher_is_better
rule:
  kind: weighted_best_n_with_substitution
  core:        { from: h2_subjects, take: 3, scale: h2 }
  mandatory:   { subject: general_paper, scale: gp }
  bonus:       { best_of: [fourth_subject, mother_tongue], only_if_improves: true }
  cap:         70
scales:
  h2: { A: 20, B: 17.5, C: 15, D: 12.5, E: 10, S: 5 }
  h1: { A: 10, B: 8.75, C: 7.5, D: 6.25, E: 5, S: 2.5 }
  gp: { A: 10, B: 8.75, C: 7.5, D: 6.25, E: 5, S: 2.5 }
source:
  url: "<primary university admissions page — resolve at build time>"
  retrieved: 2026-08-02
  licence: moe-tou            # see SAFEGUARDS.md §3
  confidence: medium          # medium until replaced with a primary source
changed_from:
  ref: university-2025.yaml
  summary: "90-point Rank Points replaced by the 70-point University Admission Score."
```

Each `kind` is a small, tested, pure function that knows how to narrate its own steps. A new country pack picks a kind or contributes one via PR — which is *reviewable code with tests*, a far better security posture than reviewing an expression grammar for escapes. Keep a guarded general-expression escape hatch on the backlog; do not build it for v1.

---

## 4. AI — where it lives, and the guardrail that makes §5's trust boundary real

Decision 2 gives four tiers. The important property: **Tier 0 is complete on its own.** A user with no GPU, no key and no internet gets correct numbers, a full derivation trace, cited sources, three-bucket results and alternate routes. Everything above Tier 0 is a comfort, never a capability gate.

| Tier | What | Ships by default | Needs |
|---|---|---|---|
| **0 — Core** | Engine, derivation trace, template explanations, three-bucket results, backward mode, all citations | ✅ **Yes** | Nothing |
| **1 — Narrator** | Plain-English rewrite of the trace, tone per view; multi-turn what-if dialogue | ❌ Opt-in | Ollama `qwen3:4b`/`8b`, or OpenAI-compatible, or an existing Claude/Codex subscription |
| **2 — OCR** | Photograph the results slip instead of typing grades | ❌ Opt-in | `qwen2.5vl:3b`/`7b` or a cloud vision model |
| **3 — Pack copilot** | Docling → official PDFs → drafted pack + citations + review checklist | 🚫 **Maintainer-only, never in the user app** | Frontier model |

Tiers 1 and 2 reuse **BandUp's provider layer verbatim** — local Ollama default, OpenAI-compatible endpoint, Gemini one-click preset, subscription route, and the same persistent on-screen warning whenever a non-local provider is active. This is the "extract the shared lib" move `PORTFOLIO_PLAN.md` already anticipates for P3, arriving one repo earlier. Model choices follow the existing 8/16/24 GB tiers in [MODEL_STACK.md](../MODEL_STACK.md); re-verify at kickoff per its own cadence note.

### The numeric guardrail — enforcement, not intention

ARCHITECTURE §5.2 says the narrator "cannot introduce a figure that didn't come from a ScoringRule evaluation," enforced structurally. Here is the actual mechanism, and it is cheap:

1. The narrator receives **only** the result object as JSON. It is never asked to recall anything.
2. Its output is scanned for every numeric token.
3. Each token must appear in the result object (or be a trivially derived quantity from it — a difference or a count, whitelisted).
4. **Any unmatched number rejects the whole narration**, and the Tier-0 template output is shown instead, silently and correctly.

This is deterministic, testable in CI with adversarial prompts, and needs no NLI stack. It resolves **ROADMAP open question 5 in favour of option (a)**: ship v1 with this guardrail, adopt `rag-that-cites`' entailment engine later for *prose* claims (which this check does not cover) without holding either repo hostage.

---

## 5. Install and first-run — PathAhead should be the easiest thing in the whole portfolio

The buried lede of Decision 2: **BandUp's install pulls ~11 GB of models; PathAhead's core needs a few megabytes of YAML and no model at all.** That is not a minor difference — it means PathAhead can reach a tier of user BandUp structurally cannot, and it should be the headline of the README rather than a footnote.

### Three tiers, one codebase

**Tier A — zero install.** A static, fully client-side build published to GitHub Pages. A parent taps a link on their phone and uses it. No server, no account, no upload — the numbers are computed in the browser and nothing is transmitted. This is only possible *because* the core has no AI dependency, and it is the single biggest reach multiplier available. Cost: free hosting, one build step. (Gated on the ODBI publish line like everything else — see §8.)

**Tier B — local install.** `PathAhead_Install.bat/.sh` + `PathAhead_Start.bat/.sh`, same convention and self-healing launcher behaviour as BandUp, opening a local web UI. Adds saved child profiles, pack auto-update, offline use, PDF export, and counsellor batch mode. Install is *dramatically* shorter than BandUp's because there is no model pull — realistically Python plus a `pip install`, and honest about it: **"about 3 minutes, roughly 40 MB, no AI model needed."**

**Tier C — AI extras.** Opt-in from Settings, exactly as in BandUp, with the same "this leaves your machine" banner. Never on the critical path.

`docs/GETTING_STARTED.md` mirrors BandUp's zero-assumption walkthrough, but should be *much* shorter — and saying so explicitly ("shorter than you expect, because this tool doesn't need an AI model") is good README copy.

### First-run flow for someone who has never installed anything

The three-view model (student / parent / counsellor) in ARCHITECTURE §6 is a persona menu at second zero, which is a decision a stressed user should not have to make before seeing any value. Invert it:

1. **"What year is your child in now?"** — a dropdown. That's it. (This is Gap 1's `Cohort`.)
2. The app states the resolution in words, so a wrong answer is caught immediately: *"So: SEC in 2027, admission in 2028, under the new L1R4 rules. Not right? Change the year."*
3. **Enter grades** — one screen, subject rows, grade dropdowns. Or **"Try a sample"** — a fully worked example, one tap, no typing, which is how a first-time user should always be able to see the output before committing effort. (BandUp already proves this pattern with "Try a sample essay.")
4. **Results**, with the derivation trace collapsed behind *"Show me how this was worked out."*
5. Tone is **one toggle — "Show me the details" on/off** — not a persona choice. Counsellor batch mode stays a separate entry point, since that user genuinely is different.

**Never ask for a name, NRIC, school, or email.** The tool must be fully usable with zero identifying information, and it should say so on screen. This is both the best UX and, per [SAFEGUARDS.md](SAFEGUARDS.md) §2, the cleanest possible PDPA position.

---

## 6. Data refresh — the concrete mechanism

Per Decision 3: packs version and ship independently of the app, like virus definitions.

**Split the repos.** `path-ahead` (engine, UI, launchers, MIT) and `path-ahead-packs` (data only, its own release cadence, its own licence notices per §3 of SAFEGUARDS). A COP correction becomes a pack release, not a code release — and pack releases can be reviewed by a teacher who cannot read Python.

**Pack identity and compatibility.** `sg-2026.3`, plus a `pack_format` integer the engine range-checks. An engine refuses a pack whose format it doesn't understand, with a plain-English "please update the app" rather than a stack trace.

**Signing.** Each release ships `manifest.json` + `SHA256SUMS` + a **minisign/cosign signature**; the public key is baked into the app. Unsigned or mismatched packs are refused. No paid certificate, no CA, no cost.

**Update check.** A plain unauthenticated `GET` to the GitHub Releases API on launch — **no query parameters, no identifiers, no telemetry in either direction**. Failure is silent and non-blocking; offline is a fully supported state, not a degraded one.

**Staleness is always visible, per-field.** A global banner (*"Data as of 14 Jul 2026 · 19 days old · update available"*) plus per-field enforcement: every fact carries a `stale_after`, and past it the number renders greyed with *"this figure predates the latest posting cycle — verify on SchoolFinder,"* deep-linked to the official page. **Stale data is never silently shown as current.** During the 2027–2028 SEC transition, packs additionally carry a `policy_status: settled | mid_rollout` flag that renders a standing banner on affected screens.

**The watcher (Phase D, maintainer-only).** A weekly GitHub Action fetches a short allowlist of official pages, normalises and hashes the relevant section, and **opens an issue when the hash changes**. It is not a scraper, not a bulk downloader, not user-facing, and never auto-publishes — it only tells a human to go look. That keeps the ToS exposure in §3 of SAFEGUARDS close to zero while still giving the "AI-assisted maintenance" story real substance.

---

## 7. Revised repo layout

```
path-ahead/                        # engine + app  (MIT)
├── engine/
│   ├── model/                     # Stage · Transition · Outcome · Prerequisite · Cohort
│   ├── rules/                     # one tested module per rule kind; each emits its own trace
│   ├── forward.py  backward.py    # backward.py enforces the ≥3-routes rule (Gap 4)
│   └── trace.py                   # derivation trace → template explanation (Tier 0)
├── packs/                         # dev copy only; releases come from path-ahead-packs
├── ai/                            # provider layer (lifted from BandUp) · narrator · numeric guardrail · OCR
├── web/                           # static client-side build → GitHub Pages (Tier A)
├── ui/                            # local app (Tier B) incl. counsellor batch mode
├── evals/                         # published historical cases per transition
├── tools/                         # pack copilot (maintainer-only) · watcher · data-health CI
├── docs/                          # GETTING_STARTED · USER_GUIDE · PACK_AUTHORING · AI_GOVERNANCE · FAQ
├── SAFEGUARDS.md                  # the disclaimers and legal posture, as a first-class doc
├── PathAhead_Install.bat/.sh      PathAhead_Start.bat/.sh
└── .github/workflows/             # pack validation · data-health gate · guardrail adversarial tests · watcher
```

This stays recognisably BandUp-shaped (launchers at root, `docs/`, `evals/`, MIT) so the portfolio reads as one hand, while adding the three things this project needs that BandUp didn't: a separate data repo, a static web tier, and safeguards as a document rather than a paragraph.

---

## 8. Roadmap changes

**Move earlier — into A1:**

- `Cohort` as a core entity and the first UI question (was C3).
- The eligibility / competitiveness three-bucket split (was implicit).
- Derivation trace as the engine's primary return value (was folded into A3's narrator).
- Data Health as a **CI gate** (was A5, report-only).

**Add:**

- **A0 (half day)** — repo scaffold, MIT licence, `SAFEGUARDS.md`, disclaimer copy, and the no-affiliation notice, *before* the first line of engine code. On a tool for real families, the safeguards are the foundation, not the trim.
- **A2b (1 weekend)** — the static zero-install web build (Tier A). Highest reach-per-hour item in the plan.
- **A3b (half day)** — the numeric guardrail plus its adversarial CI suite.
- **B2b / C-adjacent (1 weekend)** — **JAE/PSE choice-ordering sanity check.** A family ranks up to 12 choices; ordering them badly is a common and costly error, and the tool can flag "every one of your 12 choices was above your score last year — consider adding a safer option" without predicting anything. Arguably more useful than the aggregate calculator itself, and nothing public does it.

**Recommended answers to the open questions in ROADMAP §5:**

| # | Question | Recommendation |
|---|---|---|
| 2 | Update `PORTFOLIO_PLAN.md` / `_cc/meta.json` now? | Yes, on go-ahead — P2, with `requirements-copilot` bumped to P3. |
| 3 | v1 DSA depth | **DSA-JC only in v1** (it sits on the A-Level stage, which is Phase A); DSA-Sec1 arrives with Phase B. Both modelled as Overlays from day one so neither is a retrofit. |
| 4 | IB in scope? | **Out of v1**, confirmed. It is a separate qualification with separate university mappings — a Phase D pack, not a v1 stage. |
| 5 | `rag-that-cites` sequencing | **Option (a)**, resolved by §4's numeric guardrail. Adopt the entailment engine later for prose claims only. |
| 6 | Second country | **Defer the choice** until Phase A–C ship. Note that UK/UCAS is the better *architectural* stress test (tariff points + contextual offers), while India is the larger audience — decide when the engine's real constraints are known, not now. |
| 7 | Live data-refresh pipeline | **Split it.** Signed pack auto-update ships in **v1** (Decision 3 — it is modest work and is what keeps a real user correct). The source watcher stays **Phase D and maintainer-only**, never a live user-facing pipeline. |

**Unchanged:** the ODBI publish gate. Everything above — including the Tier A public web build, which is the most exposed piece — stays private until that line clears, per `PLAN_ASSUME_NO.md`. Build now, publish on the yes.

---

## 9. What would make this fail, in order of likelihood

1. **Data rot.** The engine will be right and the numbers will quietly go stale. Mitigation: pack releases, per-field `stale_after`, visible data age, Data Health as a CI gate, and a prominent "this number looks wrong" link that opens a pre-filled issue. *A tool claiming citation rigour with no correction channel has a credibility hole where its best feature should be.*
2. **Scope gravity toward the calculator.** The calculator is the easy, familiar, already-crowded part. The defensible parts are backward mode with prerequisites, alternate routes, cohort routing, and choice-ordering. Guard the Definition of Done at each phase.
3. **Policy churn during 2027–2028** outrunning the packs. Mitigation: `policy_status: mid_rollout` banners, the watcher, and Phase C scheduled last for maximum runway.
4. **Tone failure at the moment it matters most.** A correct, cold "below last year's range" delivered to a 15-year-old is a product failure even when the arithmetic is perfect. Mitigation: the ≥3-routes rule in the engine, and the copy rules in [SAFEGUARDS.md](SAFEGUARDS.md) §4 — enforced in code and reviewed as carefully as the formulas.

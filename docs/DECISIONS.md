# Decisions

A short log of choices that would otherwise be re-litigated, with the reasoning
that settled them. Preserved from the planning phase so the *why* survives the
code.

---

## The name — PathAhead (decided 2026-08-02)

The brief was a name plain enough to tell the whole story on its own, not a
clever abstraction. The trail:

- **PathFinderSG** (original working title) — hard-codes Singapore into a name
  meant to extend beyond it.
- **PathwayOS**, **Wayfinder**, **CompassOS**, **EduGraph** — rejected after
  search turned up direct collisions. PathwayOS is a real, acquired K-12
  platform (Vector Solutions); Wayfinder is a real Stanford d.school K-12 SEL
  platform; a Pathfinder direction collided with several existing "Career
  Pathfinder" products in this exact category.
- **NextPath** (from the phrase "Find Your Next Path") — taken twice over,
  including a near-exact conceptual match: a product helping Indian Class 12
  students navigate post-board pathways with real cut-offs.
- **NextPathSG** — clean in search, kept as a fallback, not chosen.
- **PathAhead** — clean in search, plain English, tells the story in two words,
  ownable without a disambiguating suffix.

**Repo/folder: `path-ahead`.** Singapore ships as `packs/singapore/`. Do not
append "SG" to the product name: Singapore is the flagship pack, not the
ceiling.

---

## Rule kinds instead of a formula DSL (2026-08-02)

The earlier design proposed YAML formula strings evaluated with `simpleeval`.
Rejected in [DESIGN_REVIEW.md §3](../DESIGN_REVIEW.md) for two reasons:

1. **An expression evaluator returns a number, and the number is not the
   product.** For a parent, the derivation trace is the product. A rule kind
   can narrate "your Mother Tongue was counted because it scored higher than
   your H1 Economics"; a string expression returns `70.0`.
2. **A fixed set of shapes is more reviewable than a free grammar.** A new
   country pack picks a kind, or contributes one as tested code — a far better
   review surface than auditing an expression grammar for escapes.

A guarded general-expression escape hatch stays on the backlog. It is not
needed for any Singapore formula, present or announced.

---

## The comparison basis is not the headline score (2026-08-02)

NUS states that no grade profile exists yet for the 70-point University
Admission Score, because AY2026/2027 is its first year, and advises applicants
to read the **three H2 grades** in the published profile as the indication of
competitiveness.

So PathAhead computes two numbers and labels both:

- the **University Admission Score** (out of 70) — what universities will use;
- the **three H2 subtotal** (out of 60) — what is actually comparable to a
  published profile.

Declared per transition in the pack as `comparison_component` and
`comparison_basis`; never inferred by the engine. Every other calculator in
this space compares the 70-point score to an old-basis profile without saying
so.

---

## MIN_ROUTES = 3, enforced in the engine (2026-08-02)

"To read Medicine you need AAA" is accurate and, delivered alone to a
seventeen-year-old, is a verdict on their worth. A disclaimer does not fix
that. `engine/backward.py` refuses to return a plan with fewer than three
routes, at least one of them non-direct; where the pack cannot supply them it
returns "route data incomplete" and points at a counsellor.

This is simultaneously the ethical safeguard and the single most
differentiating feature: the entire existing market answers "did I make it",
and none answers "what else is open".

---

## Two engines, cross-checked, rather than one engine shipped twice (2026-08-02)

Considered and rejected: Pyodide (≈10 MB to a phone for arithmetic), and a
server-side API (creates a place for a child's grades to be sent).

Chosen: implement the rule kinds in Python and in JavaScript, and make CI
replay shared golden fixtures — value *and every trace step* — through both.
Disagreement beyond `1e-9` fails the build. This keeps Tier A (a link, zero
install) and Tier B (a local app) the same artifact, and it caught a real bug
on its first run.

---

## AI is never on the critical path (2026-08-02)

Decided: no-AI core, optional AI extras. Someone with no key, no GPU and no
internet gets the complete product. The pack-authoring copilot — the one
component capable of inventing a figure — lives in `tools/`, runs only for
maintainers, and produces a draft pull request requiring human sign-off. It
never ships inside the user app.

The narrator guardrail (`engine/guardrail.py`) resolved the open question about
sequencing against `rag-that-cites`: PathAhead ships v1 with the deterministic
numeric check and can adopt the entailment engine later, for prose claims only.
Neither repo holds the other hostage.

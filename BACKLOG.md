# Backlog — considered, not scheduled

Things worth doing that are **not** in [NEXT.md](NEXT.md). NEXT.md is "pick this
up now". This file is "we have thought about it, here is what we concluded, do
not re-derive it from scratch."

---

## B1. An LLM or SLM to interpret free text

**Requested 2026-08-02.** Status: **accepted in principle, unscheduled.**

### The gap it would close

`StudentProfile.goal_text` asks *"In your own words, what do you want to be
doing in ten years?"* — and then does nothing with it. `engine/profile.py:reflect_goal`
prints the sentence back beside the options and says on screen that PathAhead
is not interpreting it.

That was the right call at the time and it is documented as such: with no model
running, keyword-matching free text produces confident nonsense, and confident
nonsense aimed at a seventeen-year-old is the specific failure this project
exists to avoid. But it is still a gap. A student who writes *"I want to work
with kids who have trouble speaking"* has just told us a great deal — Speech and
Language Therapy at SIT, Early Childhood Education at SUSS, Psychology — and we
answer with a shrug.

The same applies to two other free-text-ish surfaces:

- **Subject entry.** Already solved deterministically with type-ahead and
  synonym families after the Further Mathematics incident. Does **not** need a
  model, and should not get one.
- **"This looks wrong" reports.** Free text in, and currently no triage at all.

### The constraint that shapes the whole design

**The scored path must stay deterministic.** Two engines — `engine/rules/` and
the copy inside `web/index.html` — are cross-checked in CI against recorded
fixtures, and disagreement beyond `1e-9` fails the build. A model in the scoring
path breaks that guarantee outright: the same student, same words, two runs,
two scores, and no way to tell a wrong pack from a wrong sample.

So the model may **never** produce a number. The only shape that works:

```
free text  ->  [model]  ->  PROPOSED structured signals
                              ("healthcare", "S", "works with children")
                                     |
                          student sees them and confirms, edits or rejects
                                     |
                          deterministic engine scores the CONFIRMED signals
```

The model becomes an input method, like the type-ahead — a faster way to fill in
fields the student could have filled in themselves. Everything downstream stays
reproducible, traceable and cross-checked, and the derivation still reads
*"+8 because you said healthcare interests you"*, never *"+8 because a model
read your paragraph"*.

This also makes the failure mode survivable. A bad interpretation becomes a
wrong chip the student can delete, not a wrong score they cannot see.

### What must not break

Every one of these already has a test behind it.

1. **Tier 0 stays complete with no model, no key, no GPU and no network.** The
   install stays ~40 KB and three minutes. Interpretation is a comfort, never a
   capability gate — the same rule the Narrator and OCR tiers already follow.
2. **Nothing leaves the device without an explicit, per-session choice.** A
   goal sentence is more personal than a grade. A local SLM is the default
   posture; a cloud endpoint must be opt-in, named, and visible while it is on.
   The CI grep that blocks telemetry should be extended to cover this.
3. **Answering more about yourself never lowers your score.** An interpretation
   that adds signals must not be able to push a score down — the B1 bug in
   `ISSUES_v0.2.md`, in a new costume. Needs a monotonicity test written against
   interpreted input specifically.
4. **Our data gaps never cost the student points.** If the model declines, or
   the text is genuinely "no idea", the result must be identical to today's —
   not a penalty for having been vague.
5. **The two axes stay unblended.** Interpretation feeds *fit*, which is scored
   because it comes from what the student said. It must never touch *evidence*,
   which is published data about an admissions round and is never scored.
6. **"No idea" remains a real answer.** It says so in the placeholder text. A
   model that treats vagueness as a problem to be solved would quietly punish
   the students this tool is most for.

### Open questions — these are the user's to answer, not ours

- **Where does it run?** A small model in-browser via WebGPU keeps Tier 0's
  privacy story intact but adds a download that contradicts "no AI model to
  download". A local Ollama endpoint reuses the Tier 1 plumbing that already
  exists. A cloud endpoint is the easiest and the least consistent with the rest
  of the project.
- **How small can it be?** The task is short-text classification into a closed
  vocabulary — six RIASEC interests, a sector list, a handful of attributes.
  That is a genuinely small problem, possibly small enough for a fine-tuned
  encoder rather than a generative model, which would sidestep most of the
  non-determinism and most of the download.
- **Does it become Tier 3, or fold into Tier 1?** Tier 1 is output rewriting.
  This is input interpretation and is riskier, because output can be re-read
  and input feeds a score. Arguably it deserves its own tier and its own
  on-screen label.
- **Does the eval harness cover it?** `evals/` currently records exact values.
  Interpretation needs a different kind of eval — a set of real sentences with
  expected signal sets, scored on precision rather than equality, and reviewed
  by a person who has met a seventeen-year-old.

### Where to start when it is scheduled

Not with the model. With ~50 real goal sentences, hand-labelled with the
signals a careful human would extract, committed to `evals/`. If a deterministic
baseline gets most of them, the model is not the interesting part. If it does
not, that file is the eval and the fine-tuning set both.

---

## B2. Ask NTU for its lab-based / non-lab-based programme list

`annual_fee_no_grant` is empty for ~40 NTU courses because NTU publishes two
non-subsidised rates and no mapping from programme to cluster. One email to NTU
admissions closes it with a citable source. See [NEXT.md](NEXT.md) §1b.

---

## B3. SIT and SUSS on the new UAS

Twelve courses carry `comparable: false` because SIT and SUSS publish against
the retired 90-point UAS. When either republishes on the AY2026 basis, flip the
flag and those courses gain a real verdict. `pathahead health` prints
`on a retired scale` every run so this does not get forgotten.

---

## B4. SIT salary quartiles

SIT publishes a bare median with no quartiles, and PathAhead shows a range or
nothing. If SIT ever publishes p25/p75, roughly 30 courses gain salary data for
free.

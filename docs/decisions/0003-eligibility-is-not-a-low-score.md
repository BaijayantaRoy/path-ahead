# 3. Eligibility is not a low score

**Status:** accepted, 9 August 2026
**Supersedes in part:** the generic `subject_requirement` overlay

## The report

A parent opened PathAhead, filtered to what their daughter was studying, and
found NTU's **Physics / Applied Physics at 52 out of 100** — for a student
taking no Physics at all. Their question was the right one: how does a course
you cannot apply for appear in a list of how well courses suit you?

## What was actually wrong

Not the number. 52 is not "a bit optimistic" that could be tuned to 20. **Any**
number was wrong, because a score is a position in a ranking, and 52/100 put a
closed door above two hundred courses the student could have walked through.
Tuning it down would have moved the problem, not fixed it.

We already knew this. `LanguageRequirement` exists because Ngee Ann's Chinese
Studies came out second-strongest of 296 courses for a student who does not read
Chinese, and `START_HERE.md` states the rule that came out of it:

> A fit score answers "how well does this suit you". It cannot answer "are you
> eligible", and it must not be asked to — because a low score is still a
> ranking.

The lesson was applied to language and never generalised. Language is the rare
case. **Subjects are the common one**, and standing in for them was a blanket
overlay reading *"Programmes may require specific subjects. Check the
university's own prerequisite list."* That sentence hands our missing homework
to a sixteen-year-old and prints the score anyway.

## Decision

Published subject prerequisites are **eligibility**, checked before any
preference scoring, in both engines.

1. **`SubjectRequirement` on `Outcome`**, alongside `LanguageRequirement`.
   `subjects` is a list of *alternatives* — NTU's "Physics/Chemistry/Biology" is
   one requirement with three acceptable answers, not three requirements.
2. **An unmet requirement produces no score at all**, never a low one. The
   course stays in the list — a course removed silently is one a family never
   gets to argue with — and states the requirement **verbatim**, with a link to
   the institution's own page.
3. **Eligibility runs ahead of the minimum-signals check.** "You have not
   answered enough for a fit score" is a statement about the student, and it is
   the wrong thing to say about a course whose door is shut regardless of what
   they answer.
4. **No new question.** Subjects come off the grades table the student already
   fills in.

## The judgement calls, and why

**Not told ≠ does not have.** `subjects_offered` is `None` until a subject is
named, and `None` produces "tell PathAhead your subjects" rather than a refusal.
Collapsing the two would block students who simply had not filled in the form.

**"Which subjects do you take" is not "which do you enjoy".** Plenty of people
take H2 Chemistry and do not enjoy it. Reusing `enjoyed_subjects` as the
eligibility signal would have blocked them from every chemistry-gated course on
the strength of a preference question — confident wrongness of exactly the kind
this project exists to avoid. `enjoyed_subjects` counts as *evidence of
offering* (naming Chemistry as a favourite plainly means you take it), never as
the whole answer.

**Grade conditions are not encoded.** NTU asks for "a good grade in General
Paper" on dozens of programmes. Nearly every A-Level candidate sits GP, and
PathAhead does not hold grades — gating on it would block almost everyone on a
condition almost everyone meets. Where NTU says "a good grade in H1
Mathematics", the **subject** is checked and the grade is not, and the course
page says so.

**Under-blocking is the deliberate direction.** A wrongly blocked course costs a
student an option they had. A wrongly scored one costs them a caveat. Only the
first is unrecoverable.

**Subjects fold onto families.** Telling a student taking Further Mathematics
that they do not take Mathematics would be a wrong answer delivered with total
confidence.

**Typed names resolve, not just clicked ones.** Someone who types "Physics" and
never clicks the suggestion still takes Physics. Relying on the combobox's
`row.code` alone would leave them with the slug `h2-physics`, no match, and a
course withheld from someone who qualifies — the same bug pointing the costlier
way. `resolveSubjectCode` matches the pack's names and aliases, and
`check_boot.mjs` pins it.

## Where the data comes from

NTU's own table, *Minimum Subject Requirements for Students with
Singapore-Cambridge GCE 'A' Level*, stamped "correct as at February 2026":

<https://www.ntu.edu.sg/media/docs/default-source/undergraduate-admissions/msr/emsr_alevel.pdf>

Every label is transcribed, not paraphrased. A rewritten entry condition is how
a family ends up applying for something they cannot take.

## What is still open, and said out loud

33 of 134 university-direct courses carry requirements — all of NTU's that have
one. NUS, SIT, SMU, SUSS and SUTD have none loaded yet, and those courses behave
the way Applied Physics used to.

Rather than hide that, it is stated in two places: the **Data Health report**
prints the count per institution with every release, and each affected **course
page** says "prerequisites not checked here" in the same spot where the
requirement would otherwise appear. Silence there would read as "no
prerequisites", and a reader has no way to tell our gap from the institution's
absence of one.

## Consequences

- `FIT_SIGNALS` gains `subjects_offered`, so the "based on N of M" denominator
  moves from 8 to 9.
- Two golden fixtures now exercise a gated course. The previous four were all
  NUS courses with no requirements between them, so when the gate was added
  every fixture still agreed and the parity check proved nothing about the new
  code — a cross-engine test that cannot fail is a green light with the bulb
  taken out. Adding them immediately caught two real divergences: an em dash in
  one engine and `--` in the other, and the two engines disagreeing about
  whether eligibility or the signal count came first.
- `test_an_empty_profile_gets_no_score_rather_than_a_misleading_fifty` was
  pinning a sentence rather than the rule it was written to protect. It now
  asserts "no score, with a reason a student can act on".

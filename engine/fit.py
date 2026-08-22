"""Fit: how well a course matches what the student told us about themselves.

This is the second axis, and it is deliberately a different KIND of claim from
the first.

    Evidence      -- "your 3 H2 grades against last year's admitted range".
                     A published fact about an admissions outcome. Never
                     scored, because scoring it would be predicting a
                     committee's decision.

    Fit           -- "how well this course matches what you said you enjoy,
                     how you like to work, and what you want". Computed
                     entirely from the student's OWN answers. Scoring this is
                     legitimate, because every point is traceable back to
                     something they typed.

The two are never blended into one number. A course can score 92 on fit and sit
below last year's range — and that is precisely the situation where the
alternate routes matter most, so the UI leads with them rather than the gap.

Two hard rules enforced here rather than in the interface:

  1. **No answers, no score.** An empty profile produces "not enough to judge",
     never a misleading 50.
  2. **Partial pool, no superlatives.** While the pack covers a fraction of the
     real option space, fit runs in preview mode and the word "best" is
     forbidden. Ranking against an unrepresentative pool is not incomplete
     information; it is misinformation with a progress bar.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .model import Outcome, Pack
from .profile import INTERESTS, StudentProfile

#: Below this many answered questions, no score is shown at all.
MIN_SIGNALS = 2

#: The dimensions a student can rank, in the order they are offered.
#:
#: Each entry is (key, label, what ordering it higher actually does).
WEIGHTED_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("interests",   "The kind of work that pulls at you",
     "courses whose work matches what you are drawn to score higher"),
    ("subjects",    "Studying subjects you enjoy",
     "courses built on subjects you said you enjoy score higher"),
    ("assessment",  "How you are assessed",
     "courses assessed the way you do your best work score higher"),
    ("teamwork",    "Working alone or with others",
     "courses matching your preferred working style score higher"),
    ("cost",        "What it costs",
     "cheaper courses score higher, using the published fee for your citizenship"),
    ("earnings",    "Earnings and job prospects after graduating",
     "courses with stronger published graduate outcomes score higher"),
    ("extra",       "Avoiding interviews, tests and portfolios",
     "courses admitting on grades alone score higher"),
)
DIMENSION_KEYS = tuple(d[0] for d in WEIGHTED_DIMENSIONS)
DIMENSION_LABEL = {k: label for k, label, _ in WEIGHTED_DIMENSIONS}


IMPORTANCE_LEVELS: tuple[tuple[int, str], ...] = (
    (0, "Doesn't matter"),
    (1, "A little"),
    (2, "Quite a lot"),
    (3, "Most"),
)


def dimension_weights(profile: StudentProfile) -> dict[str, float]:
    """Turn the student's importance levels into a weight per dimension.

    The level IS the weight: "Most" counts three times what "A little" does.
    Deliberately the plainest mapping there is, because a weight a
    seventeen-year-old cannot verify by looking at it is the thing this rewrite
    exists to remove. Anything smoother would be a better curve and an
    unexplainable one.

    Nothing set weights everything equally at 1.0 -- a real default, stated on
    screen. Level 0 weighs nothing and leaves the fraction entirely.
    """
    chosen = {k: int(v) for k, v in profile.importance if k in DIMENSION_KEYS}
    if not chosen:
        return {k: 1.0 for k in DIMENSION_KEYS}
    return {k: float(max(0, min(3, chosen.get(k, 0)))) for k in DIMENSION_KEYS}


def _has_extra(outcome) -> bool:
    """Does this course admit on more than grades?

    Mirrors hasExtra() in the browser build; the golden fixtures replay both.
    """
    from .model import OverlayKind

    extra = {OverlayKind.INTERVIEW, OverlayKind.PORTFOLIO,
             OverlayKind.APTITUDE_TEST, OverlayKind.AUDITION}
    return any(o.kind in extra for o in (outcome.overlays or ()))


def _r1(x: float) -> float:
    """Round to one decimal place, half away from zero.

    NOT Python's built-in round(), which is banker's rounding: round(6.25, 1)
    gives 6.2 while JavaScript's Math.round gives 6.3. The cross-engine golden
    check caught exactly that on its first run — the CLI and the browser
    disagreeing about a fit factor by a tenth of a point. Points are never
    negative here, but the helper handles sign anyway so it stays correct if
    that ever changes.
    """
    import math

    return math.floor(x * 10 + 0.5) / 10 if x >= 0 else -(math.floor(-x * 10 + 0.5) / 10)


def _r0(x: float) -> int:
    """Round to a whole number, half away from zero -- matching Math.round().

    Same reason as _r1: the final 0-100 score is computed twice, once here and
    once in the browser, and a score of 15.5 must not become 15 in the CLI and
    16 on screen. Caught by the cross-engine golden check.
    """
    import math

    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


#: Institutions the pack must cover before fit stops being a preview.
#:
#: Singapore's six autonomous universities and all five polytechnics, each named
#: individually. This was a deliberate decision, recorded here because the
#: alternative is tempting and wrong.
#:
#: The gate previously held the literal string "Polytechnic", which no
#: institution is called -- so it could never be satisfied, which was
#: accidentally safe. Replacing it with a family flag that ANY polytechnic
#: satisfies would have let PREVIEW lift the moment one was loaded, and fit
#: would then have ranked a student against a pool missing four institutions
#: while presenting itself as complete. Naming all five means the label can only
#: change when the claim behind it is true.
#:
#: If a sixth polytechnic is ever established, this list is the one place that
#: has to change, and the health report will say `institutions missing` until
#: it does.
REQUIRED_COVERAGE = {
    "NUS", "NTU", "SMU", "SUTD", "SIT", "SUSS",
    "NYP", "NP", "SP", "TP", "RP",
}


@dataclass(frozen=True, slots=True)
class FitFactor:
    """One reason, with its arithmetic and the input it came from."""

    label: str
    points: float
    max_points: float
    reason: str
    source: str                 # which profile field produced this
    basis: str = "editorial"    # course characterisations are opinions
    #: Which rankable dimension this came from, and the two numbers behind
    #: `points`. Carried so a card can show "matched 50% x importance 4 = 2.0"
    #: rather than a bare score the reader has to take on trust.
    dimension: str = ""
    weight: float = 0.0
    match: float = 0.0          # 0.0-1.0, before weighting

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "points": self.points,
            "max_points": self.max_points,
            "reason": self.reason,
            "source": self.source,
            "basis": self.basis,
            "dimension": self.dimension,
            "weight": self.weight,
            "match": self.match,
        }


@dataclass(slots=True)
class FitScore:
    outcome_id: str
    score: int | None                # 0-100, or None when not enough was answered
    factors: list[FitFactor] = field(default_factory=list)
    signals_used: int = 0
    signals_available: int = 0
    preview: bool = True
    unscored_reason: str | None = None
    #: Things we could not assess because PATHAHEAD lacks the data. Shown to
    #: the reader so a gap in our pack never reads as a gap in them.
    not_assessed: list[str] = field(default_factory=list)

    @property
    def band(self) -> str:
        """Describes the MATCH, never the person.

        The previous wording ended at "weak", which a seventeen-year-old reads
        as a verdict on herself rather than on a course description written by
        a stranger. Nothing here is a judgement about the student.
        """
        if self.score is None:
            return "not enough answered"
        if self.score >= 75:
            return "close match"
        if self.score >= 50:
            return "good overlap"
        if self.score >= 25:
            return "some overlap"
        return "little overlap"

    @property
    def confidence_note(self) -> str:
        if self.score is None:
            return self.unscored_reason or "Not enough answered to judge fit."
        return (
            f"Based on {self.signals_used} of the "
            f"{self.signals_available} things you told us."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "score": self.score,
            "band": self.band,
            "preview": self.preview,
            "signals_used": self.signals_used,
            "signals_available": self.signals_available,
            "confidence_note": self.confidence_note,
            "unscored_reason": self.unscored_reason,
            "not_assessed": list(self.not_assessed),
            "factors": [f.to_dict() for f in self.factors],
        }


@dataclass(slots=True)
class FitCoverage:
    """The engine's honest account of its own blind spot."""

    institutions: list[str]
    missing: list[str]
    outcomes: int
    scored_outcomes: int
    complete: bool

    @property
    def warning(self) -> str | None:
        if self.complete:
            return None
        return (
            f"Fit is in preview. PathAhead currently holds course data for "
            f"{', '.join(self.institutions)} only — not "
            f"{', '.join(self.missing)}. A course that would suit you better may "
            f"simply not be loaded yet, so treat this as a starting point for a "
            f"conversation, not a shortlist."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "institutions": self.institutions,
            "missing": self.missing,
            "outcomes": self.outcomes,
            "scored_outcomes": self.scored_outcomes,
            "complete": self.complete,
            "warning": self.warning,
        }


def coverage(pack: Pack) -> FitCoverage:
    present = {o.institution_short for o in pack.outcomes.values()}
    missing = sorted(REQUIRED_COVERAGE - present)
    return FitCoverage(
        institutions=sorted(present),
        missing=missing,
        outcomes=len(pack.outcomes),
        scored_outcomes=sum(1 for o in pack.outcomes.values() if o.editorial),
        complete=not missing,
    )


# --------------------------------------------------------------------------
# the scorer
# --------------------------------------------------------------------------


def _family(code: str, families: Mapping[str, str] | None) -> str:
    """Fold a subject onto its family so Further Mathematics counts as maths.

    Same resolver the preference half already uses. Eligibility that says
    "you do not take Mathematics" to someone taking Further Mathematics would
    be a wrong answer delivered with total confidence, which is worse than no
    answer at all.
    """
    c = (code or "").strip().lower()
    return (families or {}).get(c, c)


def score_outcome(
    outcome: Outcome,
    profile: StudentProfile,
    *,
    preview: bool = True,
    families: Mapping[str, str] | None = None,
) -> FitScore:
    """Score one course against one profile, showing every step.

    THE RULE THAT MATTERS MOST, learned the hard way:

        A factor is scored only when we have BOTH sides of it -- the student's
        answer AND the pack's data. If PathAhead is missing the data, the
        factor is DROPPED, never scored zero.

    An earlier version scored 0/15 for "what you said matters" on Medicine,
    because MOE does not survey Medicine graduates, and 5/10 for cost on every
    single course because no fee figures are loaded. Those are penalties for
    *our* gaps, charged to a seventeen-year-old, and they dragged every course
    in the pack below 50. A child read that as a verdict on herself.

    Nothing about the student's answers may be diluted by what we failed to
    collect.
    """
    available = len(StudentProfile.SIGNALS)
    fam = dict(families or {})

    def resolve(code: str) -> str:
        return fam.get(code, code)

    # ELIGIBILITY RUNS FIRST -- ahead of even the "you have not answered
    # enough for a fit score" check, which is a statement about the STUDENT and
    # therefore the wrong thing to say about a course whose door is shut
    # regardless of what they answer.
    #
    # The two engines disagreed on this ordering for a while and nobody noticed,
    # because no fixture happened to include a gated course. The browser checked
    # eligibility first, Python checked signals first, and the same student
    # would have been told two different things by the website and the app.
    lr = outcome.language_requirement
    if lr is not None:
        offered = profile.languages_offered
        if offered is None:
            return FitScore(
                outcome_id=outcome.id,
                score=None,
                signals_used=profile.signal_count,
                signals_available=available,
                preview=preview,
                unscored_reason=(
                    f"This course requires {lr.label} at {lr.at_stage.replace('-', ' ').upper()}"
                    + (", and is taught substantially in that language. "
                       if lr.taught_in_language else ". ")
                    + "PathAhead has not been told which mother tongue you "
                      "offered, so it will not rank this as a match either way. "
                      "Answer that question above and it will."
                ),
            )
        if lr.language not in offered:
            return FitScore(
                outcome_id=outcome.id,
                score=None,
                signals_used=profile.signal_count,
                signals_available=available,
                preview=preview,
                unscored_reason=(
                    f"This course requires {lr.label} at "
                    f"{lr.at_stage.replace('-', ' ').upper()}"
                    + (", and is taught substantially in that language"
                       if lr.taught_in_language else "")
                    + ", which is not among the ones you said you offered. "
                      "It is left here rather than hidden, because the "
                      "requirement is the institution's to waive, not "
                      "PathAhead's to assume."
                ),
            )

    # A published SUBJECT requirement, checked the same way and for the same
    # reason as the language one above.
    #
    # This is the bug a parent caught: NTU's Physics / Applied Physics was
    # shown at 52/100 to a student with no Physics. Fifty-two is not "a bit
    # low" -- it is a confident-looking number on a door that is shut, and it
    # ranked that course above two hundred others the student could actually
    # walk through. The overlay we were relying on said "programmes may require
    # specific subjects, check the university's list", which hands our missing
    # homework to a sixteen-year-old and prints the score anyway.
    #
    # The lesson had already been learned once, for the Chinese-medium
    # diploma, and then not generalised. Language was the rare case. Subjects
    # are the common one.
    for req in outcome.subject_requirements:
        wanted = {_family(c, families) for c in req.subjects}
        # NTU's own wording already carries the level ("H2 Level pass in
        # Physics"), so prefixing it produces "H2 H2 Level pass in Physics".
        # Only synthesise a level where there is no published label to quote.
        named = req.label
        level = ""
        if not named:
            named = " or ".join(c.replace("-", " ").title() for c in req.subjects)
            level = f"{req.at_level.upper()} " if req.at_level else ""
        if profile.subjects_offered is None:
            return FitScore(
                outcome_id=outcome.id, score=None,
                signals_used=profile.signal_count, signals_available=available,
                preview=preview,
                unscored_reason=(
                    f"{outcome.institution_short or outcome.institution} asks for "
                    f"{level}{named} before it will consider an application here. "
                    "PathAhead has not been told which subjects you take, so it "
                    "will not rank this as a match either way. Fill in the "
                    "subjects you are taking and it will."
                ),
            )
        offered = {_family(c, families) for c in profile.subjects_offered}
        offered |= {_family(c, families) for c in profile.enjoyed_subjects}
        if not (wanted & offered):
            return FitScore(
                outcome_id=outcome.id, score=None,
                signals_used=profile.signal_count, signals_available=available,
                preview=preview,
                unscored_reason=(
                    f"{outcome.institution_short or outcome.institution} asks for "
                    f"{level}{named} here, which is not among the subjects you "
                    "said you take. It is left in the list rather than hidden, "
                    "because the requirement is the institution's to state and "
                    "to waive, not PathAhead's to assume you cannot meet."
                    + (f" {req.detail}" if req.detail else "")
                ),
            )

    if profile.signal_count < MIN_SIGNALS:
        return FitScore(
            outcome_id=outcome.id,
            score=None,
            signals_used=profile.signal_count,
            signals_available=available,
            preview=preview,
            unscored_reason=(
                "Answer at least two of the optional questions and PathAhead "
                "will show how well this course matches what you said — with "
                "the reasoning, line by line."
            ),
        )

    # --- eligibility before preference -------------------------------
    # A course taught in a language the student does not offer is not a weak
    # match; it is a different question, and answering it with a number is
    # what went wrong. NP's Diploma in Chinese Studies came out as the second
    # strongest match of 296 for a student who does not read Chinese, on 67
    # points of purely generic overlap -- "you work best through exams".
    #
    # So this check runs BEFORE any scoring, and it produces no score at all
    # rather than a low one. A low score would still be a ranking, and would
    # still put the course above hundreds of others.
    #
    # The course is not hidden. PathAhead does not know what it has not been
    # told, the requirement sits at O-Level while forward mode collects
    # A-Level subjects, and a course removed silently is one a family never
    # gets to argue with.
    ed = outcome.editorial
    if ed is None:
        return FitScore(
            outcome_id=outcome.id,
            score=None,
            signals_used=profile.signal_count,
            signals_available=available,
            preview=preview,
            unscored_reason=(
                "PathAhead has no description of what this course is like, so "
                "it will not guess at a match."
            ),
        )

    factors: list[FitFactor] = []
    used: set[str] = set()
    skipped: list[str] = []

    weights = dimension_weights(profile)

    def add(label, points, max_points, reason, source, dimension=""):
        """Record one dimension, scaled by how the STUDENT ranked it.

        `points`/`max_points` arrive on the old fixed scale (25, 15, 10...);
        what survives is only their ratio -- the raw match. The weight then
        comes entirely from the student's ordering, so the old unargued
        constants no longer influence anything. A dimension ranked nowhere
        weighs 0 and is dropped from BOTH sides of the fraction, because
        "this does not matter to me" must mean nothing rather than a little.
        """
        dim = dimension or source
        w = weights.get(dim, 1.0)
        if w <= 0:
            skipped.append(f"{DIMENSION_LABEL.get(dim, dim)} -- you ranked this as not mattering")
            return
        m = 0.0 if max_points <= 0 else max(0.0, min(1.0, points / max_points))
        factors.append(FitFactor(label, _r1(m * w), w, reason, source,
                                 dimension=dim, weight=w, match=m))
        used.add(source)

    # --- interests --------------------------------------------------
    # Denominator is the COURSE's profile, never the length of the student's
    # own list. Naming more of yourself must never lower your score.
    if profile.interests and ed.interests:
        overlap = [i for i in profile.interests if i in ed.interests]
        target = min(len(ed.interests), 2) or 1
        pts = _r1(25.0 * min(1.0, len(overlap) / target))
        names = [INTERESTS[i][0].lower() for i in overlap]
        add(
            "What pulls at you",
            pts,
            25.0,
            (
                f"you chose {', '.join(names)}, which is what this course draws on"
                if overlap
                else "you picked different kinds of work from the ones this course mainly draws on"
            ),
            "interests",
            dimension="interests",
        )

    # --- subjects they enjoy ----------------------------------------
    # Matched by subject FAMILY, so Further Mathematics counts as mathematics.
    if profile.enjoyed_subjects and ed.subject_affinity:
        enjoyed = {resolve(s.lower()) for s in profile.enjoyed_subjects}
        affinity = {resolve(s.lower()) for s in ed.subject_affinity}
        hits = sorted(enjoyed & affinity)
        target = min(len(affinity), 3) or 1
        pts = _r1(25.0 * min(1.0, len(hits) / target))
        # A zero must read as a difference between two things, never as a
        # deficit in the student -- so it names what the course leans on
        # rather than saying what they failed to pick.
        others = ", ".join(sorted(affinity - enjoyed)[:3])
        add(
            "Subjects you enjoy",
            pts,
            25.0,
            (
                f"this course is built on {', '.join(hits)}, which you said you enjoy"
                if hits
                else f"this course leans mostly on {others}, and you picked different subjects"
            ),
            "enjoyed_subjects",
            dimension="subjects",
        )

    # --- how they are assessed --------------------------------------
    if profile.assessment_style and ed.assessment_style:
        match = profile.assessment_style in ed.assessment_style
        add(
            "How you are assessed",
            15.0 if match else 0.0,
            15.0,
            (
                f"you work best through {profile.assessment_style}, and so does much of this course"
                if match
                else f"you work best through {profile.assessment_style}; this course leans on "
                f"{', '.join(ed.assessment_style)}"
            ),
            "assessment_style",
            dimension="assessment",
        )

    # --- alone or with others ---------------------------------------
    if profile.teamwork and ed.teamwork:
        if profile.teamwork == ed.teamwork:
            pts, reason = 10.0, f"this course is mostly {ed.teamwork} work, which is what you prefer"
        elif "mixed" in (profile.teamwork, ed.teamwork):
            pts, reason = 5.0, "partly a match on working style"
        else:
            pts, reason = 0.0, f"you prefer {profile.teamwork} work; this course is mostly {ed.teamwork}"
        add("Working style", pts, 10.0, reason, "teamwork", dimension="teamwork")

    # --- what they say matters --------------------------------------
    # Scored ONLY against priorities we can actually assess for this course.
    # A course is never marked down because a survey does not cover it.
    if profile.priorities:
        emp = outcome.employment
        parts: list[tuple[float, str]] = []
        if "earnings" in profile.priorities and emp and emp.has_salary:
            parts.append((
                10.0,
                f"you said financial security matters; graduates of this course reported a "
                f"{emp.fact.as_of_year if emp.fact else ''} median of "
                f"${emp.gross_median:,}".replace("  ", " "),
            ))
        if "stability" in profile.priorities and emp and emp.employment_rate:
            share = 10.0 if emp.employment_rate >= 90 else 5.0
            parts.append((
                share,
                f"you said a steady path matters; {emp.employment_rate:g}% of graduates were "
                f"in employment within six months",
            ))
        if parts:
            add(
                "What you said matters",
                _r1(sum(p for p, _ in parts) / len(parts)),
                10.0,
                "; ".join(r for _, r in parts),
                "priorities",
                dimension="earnings",
            )
        else:
            skipped.append(
                "what you said matters most -- PathAhead has no published outcome figures "
                "for this course, which says nothing about the course"
            )

    # --- extra assessment -------------------------------------------
    # Extra assessment and cost no longer wait on a yes/no toggle. Those
    # toggles asked the same question the importance rows ask, so they were
    # removed; how much either counts is the weight, and whether it is SCORED
    # depends only on whether the data exists.
    needs_extra = _has_extra(outcome)
    add(
        "Extra assessment",
        0.0 if needs_extra else 10.0,
        10.0,
        (
            "this course requires an interview, test or portfolio, which you asked to count"
            if needs_extra
            else "no extra interview, test or portfolio is required, which you asked to count"
        ),
        "willing_extra_assessment",
        dimension="extra",
    )

    if outcome.cost:
        total = outcome.cost.total_for(profile.citizenship)
        if total is None:
            skipped.append("cost -- PathAhead does not carry a fee figure for this course yet")
        else:
            pts = 10.0 if total <= 40000 else 5.0
            why = f"the published course fee comes to about ${total:,.0f} in total"
            if outcome.cost.bond_note:
                why += ". " + outcome.cost.bond_note
            add("Cost", pts, 10.0, why, "cost_sensitive", dimension="cost")

    if not factors:
        return FitScore(
            outcome_id=outcome.id,
            score=None,
            signals_used=profile.signal_count,
            signals_available=available,
            preview=preview,
            unscored_reason=(
                "What you answered does not overlap with what PathAhead knows "
                "about this course, so it will not invent a match."
            ),
        )

    earned = sum(f.points for f in factors)
    possible = sum(f.max_points for f in factors)
    score = _r0(100 * earned / possible) if possible else None

    factors.sort(key=lambda f: (-(f.points / f.max_points if f.max_points else 0), f.label))

    return FitScore(
        outcome_id=outcome.id,
        score=score,
        factors=factors,
        signals_used=len(used),
        signals_available=available,
        preview=preview,
        not_assessed=skipped,
    )


def subject_families(pack: Pack) -> dict[str, str]:
    """subject code -> family code, so Further Mathematics counts as maths.

    Exact-code matching meant a student whose favourite subject was Further
    Mathematics scored zero on every mathematics-heavy course. Declared in the
    pack rather than hardcoded, because subject naming is a country thing.
    """
    return {
        str(s["code"]): str(s.get("family", s["code"]))
        for s in (pack.subjects or [])
    }


def score_all(pack: Pack, profile: StudentProfile, transition_id: str) -> dict[str, FitScore]:
    cov = coverage(pack)
    fam = subject_families(pack)
    return {
        o.id: score_outcome(o, profile, preview=not cov.complete, families=fam)
        for o in pack.outcomes_for(transition_id)
    }


def explain_fit(fit: FitScore, outcome: Outcome) -> str:
    """Plain text derivation. No model involved, and none needed."""
    lines = [f"Fit — {outcome.display}"]
    if fit.score is None:
        lines += ["", f"  {fit.unscored_reason}"]
        return "\n".join(lines)

    lines.append("")
    lines.append(f"  {fit.score} / 100   ({fit.band})")
    lines.append("")
    for f in fit.factors:
        sign = "+" if f.points > 0 else " "
        lines.append(f"  {sign}{f.points:g} of {f.max_points:g}   {f.label}")
        lines.append(f"        {f.reason}")
    if fit.not_assessed:
        lines.append("")
        lines.append("  Not counted either way, because PathAhead is missing the data:")
        for x in fit.not_assessed:
            lines.append(f"    - {x}")
    lines.append("")
    lines.append(f"  {fit.confidence_note}")
    lines.append(
        "  Course descriptions are PathAhead's own characterisation, not the "
        "institution's. If one is wrong, please tell us."
    )
    return "\n".join(lines)

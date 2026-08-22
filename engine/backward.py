"""Backward mode: "I want to end up there -- what do I need, and what else works?"

This module carries a hard rule that is a safety requirement, not a feature:

    MIN_ROUTES -- a plan is never a single number.

"To read Medicine you need AAA/A" is accurate, and delivered on its own to a
fifteen-year-old it is a verdict on their worth. A disclaimer does not fix
that; a design rule does. If the pack cannot supply at least MIN_ROUTES ways
to reach a destination, this module returns "route data incomplete" rather
than a lone hard number.

See DESIGN_REVIEW.md Gap 4 and SAFEGUARDS.md 5.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import InputError
from .grades import GradeSheet
from .model import Outcome, Pack, Prerequisite, Route, Transition
from .trace import Derivation

#: Never fewer than this many ways forward. Enforced, not aspirational.
MIN_ROUTES = 3


@dataclass(slots=True)
class Gap:
    """The distance between where a student is and a published band."""

    current: float | None
    target_low: float
    target_high: float
    basis: str
    band_year: int
    direction: str

    @property
    def difference(self) -> float | None:
        if self.current is None:
            return None
        if self.direction == "higher_is_better":
            return round(self.target_low - self.current, 4)
        return round(self.current - self.target_low, 4)

    def sentence(self) -> str:
        lo, hi = min(self.target_low, self.target_high), max(self.target_low, self.target_high)
        base = (
            f"Students admitted in {self.band_year} sat between {lo:g} and {hi:g} "
            f"({self.basis})."
        )
        if self.current is None:
            return base
        d = self.difference
        if d is None or d <= 0:
            return base + " Your current result is already inside or above that range."
        return base + f" You are {abs(d):g} away from the lower end of it."

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": self.current,
            "target_low": self.target_low,
            "target_high": self.target_high,
            "basis": self.basis,
            "band_year": self.band_year,
            "difference": self.difference,
            "sentence": self.sentence(),
        }


@dataclass(slots=True)
class Plan:
    outcome: Outcome
    transition: Transition
    gap: Gap | None
    routes: list[Route]
    prerequisites: list[Prerequisite]
    extra_assessment: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    complete: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": {
                "id": self.outcome.id,
                "name": self.outcome.name,
                "institution": self.outcome.institution,
                "institution_short": self.outcome.institution_short,
                "url": self.outcome.url,
            },
            "gap": self.gap.to_dict() if self.gap else None,
            "routes": [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "label": r.label,
                    "summary": r.summary,
                    "steps": list(r.steps),
                    "typical_duration": r.typical_duration,
                    "caveat": r.caveat,
                }
                for r in self.routes
            ],
            "prerequisites": [
                {
                    "id": p.id,
                    "requires_subject": p.requires_subject,
                    "at_stage": p.at_stage,
                    "depends_on_earlier": p.depends_on_earlier,
                    "detail": p.detail,
                    "as_of_year": p.fact.as_of_year,
                }
                for p in self.prerequisites
            ],
            "extra_assessment": list(self.extra_assessment),
            "notes": list(self.notes),
            "complete": self.complete,
        }


def plan(
    pack: Pack,
    outcome_id: str,
    *,
    current: Derivation | None = None,
    comparison_score: float | None = None,
    grades: GradeSheet | None = None,
) -> Plan:
    """Work backwards from a destination to what it takes, and what else works."""
    outcome = pack.outcomes.get(outcome_id)
    if outcome is None:
        raise InputError(
            f"no course called {outcome_id!r} in this data pack",
            advice="Search for the course by name; the id must match exactly.",
        )
    transition = pack.transitions[outcome.transition_id]

    gap = None
    if outcome.band is not None:
        gap = Gap(
            current=comparison_score if comparison_score is not None else (current.value if current else None),
            target_low=outcome.band.p10_points,
            target_high=outcome.band.p90_points,
            basis=outcome.band.basis,
            band_year=outcome.band.fact.as_of_year,
            direction=transition.direction,
        )

    routes = pack.routes_for(outcome)
    prerequisites = pack.prerequisites_for(outcome)
    notes: list[str] = []
    complete = True

    # --- the MIN_ROUTES rule ------------------------------------------
    direct = [r for r in routes if r.kind == "direct"]
    others = [r for r in routes if r.kind != "direct"]
    if len(routes) < MIN_ROUTES or not others:
        complete = False
        notes.append(
            "PathAhead will not show a single required score on its own. This data "
            "pack does not yet list enough alternative routes to this course, so "
            "the requirement above is shown with that caveat. The official "
            "admissions page is the right next stop, and a school counsellor can "
            "talk through routes this tool does not know about."
        )
    ordered = direct + sorted(others, key=lambda r: (r.kind != "alternative", r.label))

    if outcome.has_extra_assessment:
        notes.append(
            "This course also assesses applicants beyond their grades. Meeting the "
            "grade profile is one part of the decision, not the whole of it."
        )
    if gap is not None and gap.difference is not None and gap.difference > 0:
        notes.append(
            "The figures above describe last year's admitted students. They are not "
            "a pass mark, and they change every year."
        )

    return Plan(
        outcome=outcome,
        transition=transition,
        gap=gap,
        routes=ordered,
        prerequisites=prerequisites,
        extra_assessment=[f"{o.label}: {o.detail}" for o in outcome.overlays],
        notes=notes,
        complete=complete,
    )


def what_if(
    pack: Pack,
    grades: GradeSheet,
    transition: Transition,
    changes: dict[str, str],
) -> tuple[Derivation, Derivation]:
    """Recompute with some grades changed. Returns (before, after).

    Used by the what-if simulator: "what if I got a B in H2 Maths instead?".
    Deterministic; the AI tier only ever decides *which* what-ifs to run.
    """
    from .forward import score as _score
    from .grades import SubjectGrade

    before = _score(pack, grades, transition)
    updated = []
    unknown = [c for c in changes if grades.by_code(c) is None]
    if unknown:
        raise InputError(
            f"no such subject in your entry: {', '.join(unknown)}",
            advice="Use the subject codes shown in your results table.",
        )
    for s in grades.subjects:
        if s.code in changes:
            updated.append(SubjectGrade(s.code, s.name, s.level, changes[s.code].upper()))
        else:
            updated.append(s)
    after = _score(pack, GradeSheet(grades.stage_id, tuple(updated)), transition)
    return before, after

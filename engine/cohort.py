"""Cohort resolution -- the first question, and the one everything hangs on.

A family knows "my child is in Secondary 3 this year". They do not know which
admission cycle that implies, and in Singapore right now the answer decides
which of two entirely different rulebooks applies:

    Sec 4 in 2026  ->  O-Level 2026  ->  JAE 2027   ->  L1R5 <= 20
    Sec 3 in 2026  ->  SEC 2027      ->  PSE  2028  ->  L1R4 <= 16

One school year apart. Guessing here produces a confidently wrong answer under
the wrong formula, which is the exact failure this whole project exists to
prevent. So: ask the question people can answer, resolve it deterministically
from pack data, and read the resolution back in plain words.
"""

from __future__ import annotations

from .errors import InputError
from .model import CohortResolution, CohortRule, Pack


def resolve(pack: Pack, year_level: str, current_year: int) -> CohortResolution:
    """Turn 'jc-2' + 2026 into a fully-specified rulebook selection."""
    try:
        rule: CohortRule = pack.cohort_rules[year_level]
    except KeyError as exc:
        known = ", ".join(sorted(pack.cohort_rules)) or "(none in this pack)"
        raise InputError(
            f"unknown year level {year_level!r}",
            advice=f"Choose one of: {known}.",
        ) from exc

    exam_year = current_year + rule.years_to_exam
    admission_year = exam_year + rule.admission_offset

    resolution = CohortResolution(
        year_level=rule.year_level,
        label=rule.label,
        current_year=current_year,
        stage_id=rule.stage_id,
        exam_year=exam_year,
        admission_year=admission_year,
        transition_id=rule.transition_id,
        note=rule.note,
    )

    transition = pack.transitions.get(rule.transition_id)
    if transition is None:
        raise InputError(
            f"this pack has no rules loaded for {rule.label}",
            advice=(
                "PathAhead has not yet loaded the rules for this stage. "
                "The stages that are ready are listed on the start screen."
            ),
        )
    if transition.applies_to_exam_years and exam_year not in transition.applies_to_exam_years:
        # Not fatal -- but the user must be told, loudly, rather than silently
        # scored under a rule that does not apply to them.
        raise InputError(
            f"the loaded rules cover exam years "
            f"{_years(transition.applies_to_exam_years)}, but {rule.label} in "
            f"{current_year} sits the exam in {exam_year}",
            advice=(
                "The rules for that year have not been published or loaded yet. "
                "Check back after the next data update rather than relying on "
                "this year's formula."
            ),
        )
    return resolution


def _years(years: tuple[int, ...]) -> str:
    if not years:
        return "any year"
    if len(years) == 1:
        return str(years[0])
    return f"{min(years)}-{max(years)}"

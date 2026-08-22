"""lowest_sum

The PSLE shape: sum every required subject's Achievement Level. Lower is
better, the floor is (subjects x best AL), the ceiling is (subjects x worst AL).

No substitution, no cap, no optional components -- which is exactly why it is
worth having as a separate kind rather than bending the A-Level rule to fit.
A rule kind should be readable in one screen by someone who is not a
programmer, because the people best placed to spot a wrong rule are teachers.
"""

from __future__ import annotations

from ..errors import RuleError
from ..grades import grade_points
from ..trace import Derivation, Step, StepKind
from .base import RuleContext


class LowestSumRule:
    kind = "lowest_sum"
    summary = "Add up every required subject's grade points. Lower is better."

    def evaluate(self, ctx: RuleContext) -> Derivation:
        p = ctx.params
        required = list(p["required_subjects"])
        scale_name = str(p["scale"])

        d = Derivation(
            value=0.0,
            max_value=float(p["worst_possible"]) if p.get("worst_possible") else None,
            direction="lower_is_better",
            unit=str(p.get("unit", "points")),
        )
        for caveat in ctx.caveats:
            d.warnings.append(caveat)

        d.add(Step(StepKind.HEADING, p.get("label", "Your subjects")))
        total = 0.0
        missing: list[str] = []
        for spec in required:
            code = str(spec["code"])
            subject = ctx.grades.by_code(code)
            if subject is None:
                matches = [s for s in ctx.grades.subjects if s.name.lower() == str(spec["name"]).lower()]
                subject = matches[0] if matches else None
            if subject is None:
                # `accepts` names the other subject codes that satisfy this
                # requirement. It exists because of Foundation-level PSLE
                # subjects: a child who sits Foundation Mathematics HAS sat the
                # Mathematics requirement, and matching on the code or the name
                # alone would report their four-subject score as missing a
                # subject -- which is both wrong and, to a parent reading it,
                # an accusation.
                #
                # Deliberately a pack field rather than an engine rule. Which
                # subject stands in for which is a policy fact about one
                # country's examination, and belongs in the file a teacher can
                # read, not in the scoring code.
                for alt in spec.get("accepts", ()) or ():
                    subject = ctx.grades.by_code(str(alt))
                    if subject is not None:
                        break
            if subject is None:
                missing.append(str(spec["name"]))
                continue
            pts = grade_points(ctx.scales, spec.get("scale", scale_name), subject.grade)
            total += pts
            d.add(
                Step(
                    StepKind.COMPONENT,
                    f"{subject.name}  {_al(subject.grade)}",
                    detail=_foundation_note(subject.grade, pts),
                    points=pts,
                    running_total=round(total, 4),
                )
            )

        if missing:
            raise RuleError(
                f"missing required subject(s): {', '.join(missing)}",
                advice=(
                    "This score adds up all four subjects. Please enter a grade for: "
                    + ", ".join(missing)
                    + "."
                ),
            )

        total = round(total, 4)
        d.value = total
        d.add(Step(StepKind.TOTAL, p.get("total_label", "Total score"), running_total=total))
        d.add(
            Step(
                StepKind.NOTE,
                f"Lower is better. The best possible is {p.get('best_possible', '?')} "
                f"and the weakest is {p.get('worst_possible', '?')}.",
            )
        )
        return d

    def best_possible(self, ctx: RuleContext) -> float:
        p = ctx.params
        if p.get("best_possible") is not None:
            return float(p["best_possible"])
        scale = ctx.scales[str(p["scale"])]
        return min(scale.values()) * len(p["required_subjects"])


def _al(grade: str) -> str:
    """Render a grade the way the examination board writes it.

    Foundation grades arrive normalised as "FA"/"FB"/"FC" so that a Foundation
    A can never be confused with a Standard A -- but "FA" is an internal
    spelling and no family should ever be shown it.

    Any change here must be made in the JS engine's `alLabel` at the same time.
    The two are compared step-by-step by tools/check_golden.mjs, which is what
    stops them drifting apart.
    """
    if grade.isdigit():
        return f"AL{grade}"
    if len(grade) == 2 and grade[0] == "F" and grade[1] in "ABC":
        return f"Foundation {grade[1]}"
    return grade


def _foundation_note(grade: str, points: float) -> str | None:
    """Say out loud that a Foundation grade was mapped, and to what.

    Without this the trace shows "Foundation Mathematics — 6" and leaves a
    parent to work out where the 6 came from. The whole point of a derivation
    trace is that nobody has to.
    """
    if len(grade) == 2 and grade[0] == "F" and grade[1] in "ABC":
        return (
            f"Foundation {grade[1]} counts as AL{int(points)} of the Standard "
            "scale when the four subjects are added up."
        )
    return None

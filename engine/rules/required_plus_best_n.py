"""required_plus_best_n

The O-Level / SEC aggregate shape: one compulsory subject (a language) plus
the best N of a set of relevant subjects. Lower is better.

    L1R5  = English + best 5 relevant   (legacy O-Level, JC entry, <= 20)
    L1R4  = English + best 4 relevant   (SEC-era JC entry from 2028, <= 16)
    ELR2B2 = English + 2 relevant + 2 best  (polytechnic entry)

All three are this one kind with different parameters. That is the whole
argument for rule kinds over hardcoded formulas: the 2027 change is a data
edit, not an engine change.
"""

from __future__ import annotations

from ..errors import RuleError
from ..grades import SubjectGrade, grade_points
from ..trace import Derivation, Step, StepKind
from .base import RuleContext


class RequiredPlusBestNRule:
    kind = "required_plus_best_n"
    summary = (
        "One compulsory subject plus the best N of a relevant set. "
        "Lower is better. Covers L1R5, L1R4 and ELR2B2."
    )

    def evaluate(self, ctx: RuleContext) -> Derivation:
        p = ctx.params
        scale_name = str(p["scale"])
        groups = list(p["groups"])

        d = Derivation(
            value=0.0,
            max_value=float(p["worst_possible"]) if p.get("worst_possible") else None,
            direction="lower_is_better",
        )
        for caveat in ctx.caveats:
            d.warnings.append(caveat)

        used: set[str] = set()
        total = 0.0

        for group in groups:
            label = group.get("label", "Subjects")
            take = int(group.get("take", 1))
            pool = self._pool(ctx, group, used)

            if len(pool) < take:
                raise RuleError(
                    f"{label}: need {take} subject(s), found {len(pool)}",
                    advice=(
                        f"This aggregate uses {take} subject(s) for '{label}'. "
                        "Please add the missing subject(s)."
                    ),
                )

            scored = sorted(
                ((s, grade_points(ctx.scales, scale_name, s.grade)) for s in pool),
                key=lambda pair: (pair[1], pair[0].name),  # lower is better
            )
            counted, spare = scored[:take], scored[take:]

            d.add(Step(StepKind.HEADING, label))
            for subject, pts in counted:
                total += pts
                used.add(subject.code)
                d.add(
                    Step(
                        StepKind.COMPONENT,
                        f"{subject.name}  {_ol(subject.grade)}",
                        points=pts,
                        running_total=round(total, 4),
                    )
                )
            for subject, pts in spare:
                d.add(
                    Step(
                        StepKind.EXCLUDED,
                        f"{subject.name}  {_ol(subject.grade)}",
                        detail=f"only the best {take} count in this group",
                        points=pts,
                    )
                )
            d.add(Step(StepKind.SUBTOTAL, "Subtotal", running_total=round(total, 4)))

        total = round(total, 4)
        d.value = total
        d.add(Step(StepKind.TOTAL, p.get("total_label", "Aggregate"), running_total=total))
        if p.get("qualifying_max") is not None:
            d.add(
                Step(
                    StepKind.NOTE,
                    f"An aggregate of {p['qualifying_max']:g} or lower meets the stated "
                    "requirement. Lower is better.",
                )
            )
        return d

    @staticmethod
    def _pool(ctx: RuleContext, group, used: set[str]) -> list[SubjectGrade]:
        codes = group.get("codes")
        tags = set(group.get("tags") or [])
        pool: list[SubjectGrade] = []
        for s in ctx.grades.subjects:
            if s.code in used:
                continue
            if codes and s.code not in codes:
                continue
            if tags and not (tags & {s.level}):
                continue
            pool.append(s)
        return pool

    def best_possible(self, ctx: RuleContext) -> float:
        p = ctx.params
        if p.get("best_possible") is not None:
            return float(p["best_possible"])
        scale = ctx.scales[str(p["scale"])]
        take = sum(int(g.get("take", 1)) for g in p["groups"])
        return min(scale.values()) * take


#: O-Level/SEC results are published as A1/A2/B3/.../F9; the bare digit is
#: what `grade_points` actually adds up (see `_OLEVEL_LETTER_GRADES` in
#: engine/grades.py, which stores this digit as the canonical grade). Nobody
#: should ever be shown their own child's result as a bare "3" when the
#: results slip says "B3" -- same reasoning as `_al()` in lowest_sum.py for
#: PSLE, and the same requirement: change the JS `olLabel()` in the same
#: commit, since tools/check_golden.mjs compares these step labels verbatim
#: between the two engines.
_OLEVEL_DISPLAY = {
    "1": "A1", "2": "A2", "3": "B3", "4": "B4",
    "5": "C5", "6": "C6", "7": "D7", "8": "E8", "9": "F9",
}


def _ol(grade: str) -> str:
    """Render a stored O-Level/SEC digit grade the way the results slip does."""
    return _OLEVEL_DISPLAY.get(grade, grade)

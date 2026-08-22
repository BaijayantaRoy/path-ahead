"""weighted_best_n_with_substitution

The shape Singapore's A-Level University Admission Score takes from 2026:

    best N subjects at one level, on one scale
  + a mandatory subject on its own scale
  + a bonus that is the best of several candidates, counted only if it improves
  = capped at a ceiling

Higher is better. The same shape covers any "best three plus a compulsory
paper, with an optional booster" system, which is why it is a named kind and
not a Singapore special case.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..errors import RuleError
from ..grades import SubjectGrade, grade_points
from ..trace import Derivation, Step, StepKind
from .base import RuleContext


class WeightedBestNWithSubstitution:
    kind = "weighted_best_n_with_substitution"
    summary = (
        "Best N subjects at one level, plus a compulsory subject, plus the best "
        "of several optional subjects if it improves the total, capped at a ceiling."
    )

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _score(ctx: RuleContext, subject: SubjectGrade, scale: str) -> float:
        return grade_points(ctx.scales, scale, subject.grade)

    @staticmethod
    def _candidates(ctx: RuleContext, spec: Mapping[str, Any]) -> list[SubjectGrade]:
        levels = spec.get("levels") or [spec.get("level")]
        levels = [lv for lv in levels if lv]
        if not levels:
            raise RuleError("rule parameter is missing a subject level")
        return ctx.grades.at_level(*levels)

    def _scale_for(self, spec: Mapping[str, Any], subject: SubjectGrade) -> str:
        """A candidate may be scored on a scale that depends on its level."""
        by_level = spec.get("scale_by_level")
        if by_level:
            try:
                return by_level[subject.level]
            except KeyError as exc:
                raise RuleError(
                    f"no scale declared for level {subject.level!r} in this rule"
                ) from exc
        scale = spec.get("scale")
        if not scale:
            raise RuleError("rule parameter is missing a grade scale")
        return str(scale)

    # -- evaluation ------------------------------------------------------

    def evaluate(self, ctx: RuleContext) -> Derivation:
        p = ctx.params
        core = p["core"]
        take = int(core["take"])
        cap = float(p["cap"]) if p.get("cap") is not None else None

        d = Derivation(value=0.0, max_value=cap, direction="higher_is_better")
        for caveat in ctx.caveats:
            d.warnings.append(caveat)

        # --- core: the best N ------------------------------------------
        core_subjects = self._candidates(ctx, core)
        if len(core_subjects) < take:
            raise RuleError(
                f"this score needs {take} subjects at level "
                f"{'/'.join(core.get('levels') or [core.get('level')])}, "
                f"but only {len(core_subjects)} were entered",
                advice=(
                    f"Add your remaining subjects. The score is built from your best "
                    f"{take} of them."
                ),
            )

        scored = sorted(
            ((s, self._score(ctx, s, self._scale_for(core, s))) for s in core_subjects),
            key=lambda pair: (-pair[1], pair[0].name),
        )
        counted, spare = scored[:take], scored[take:]

        d.add(Step(StepKind.HEADING, core.get("label", f"Your best {take} subjects")))
        total = 0.0
        for subject, pts in counted:
            total += pts
            d.add(
                Step(
                    StepKind.COMPONENT,
                    f"{subject.display}  {subject.grade}",
                    points=pts,
                    running_total=round(total, 4),
                )
            )
        for subject, pts in spare:
            d.add(
                Step(
                    StepKind.EXCLUDED,
                    f"{subject.display}  {subject.grade}",
                    detail=f"only your best {take} count here",
                    points=pts,
                )
            )
        core_subtotal_label = core.get("subtotal_label", "Subtotal")
        d.add(Step(StepKind.SUBTOTAL, core_subtotal_label, running_total=round(total, 4)))

        # --- mandatory component ---------------------------------------
        mandatory = p.get("mandatory")
        if mandatory:
            subs = self._candidates(ctx, mandatory)
            if not subs:
                raise RuleError(
                    f"{mandatory.get('label', 'a compulsory subject')} is missing",
                    advice=(
                        f"{mandatory.get('label', 'This subject')} counts towards the "
                        "score and must be entered."
                    ),
                )
            subject = subs[0]
            pts = self._score(ctx, subject, self._scale_for(mandatory, subject))
            total += pts
            d.add(Step(StepKind.HEADING, mandatory.get("label", "Compulsory subject")))
            d.add(
                Step(
                    StepKind.COMPONENT,
                    f"{subject.display}  {subject.grade}",
                    points=pts,
                    running_total=round(total, 4),
                )
            )
            d.add(Step(StepKind.SUBTOTAL, "Subtotal", running_total=round(total, 4)))

        # --- bonus: best of, only if it improves ------------------------
        bonus = p.get("bonus")
        if bonus:
            best: tuple[SubjectGrade, float] | None = None
            considered: list[tuple[SubjectGrade, float]] = []
            for spec in bonus["best_of"]:
                for subject in self._candidates(ctx, spec):
                    if subject.code in {c.code for c, _ in considered}:
                        continue
                    if any(subject.code == c.code for c, _ in counted):
                        continue  # already counted in the core
                    pts = self._score(ctx, subject, self._scale_for(spec, subject))
                    considered.append((subject, pts))
                    if best is None or pts > best[1]:
                        best = (subject, pts)

            d.add(Step(StepKind.HEADING, bonus.get("label", "Bonus subject")))
            if not considered:
                d.add(
                    Step(
                        StepKind.NOTE,
                        "No optional subject entered, so no bonus was added.",
                    )
                )
            else:
                # "counted only if it improves the total": with a positive-only
                # scale that reduces to "counted if it scores above zero".
                improves = best is not None and (
                    best[1] > 0 or not bonus.get("only_if_improves", True)
                )
                for subject, pts in considered:
                    if best and subject.code == best[0].code and improves:
                        total += pts
                        d.add(
                            Step(
                                StepKind.SUBSTITUTION,
                                f"{subject.display}  {subject.grade}",
                                detail="counted - the higher of your optional subjects",
                                points=pts,
                                running_total=round(total, 4),
                            )
                        )
                    else:
                        d.add(
                            Step(
                                StepKind.EXCLUDED,
                                f"{subject.display}  {subject.grade}",
                                detail="the other optional subject scored higher",
                                points=pts,
                            )
                        )
                d.add(Step(StepKind.SUBTOTAL, "Subtotal", running_total=round(total, 4)))

        # --- cap --------------------------------------------------------
        uncapped = round(total, 4)
        if cap is not None and uncapped > cap:
            d.add(
                Step(
                    StepKind.CAP,
                    f"Capped at the maximum of {cap:g}",
                    detail=f"your components added to {uncapped:g}",
                    running_total=cap,
                )
            )
            total = cap
            if p.get("cap_note"):
                d.warnings.append(str(p["cap_note"]))

        total = round(total, 4)
        d.value = total
        d.add(Step(StepKind.TOTAL, p.get("total_label", "Total"), running_total=total))
        return d

    # -- ceiling ---------------------------------------------------------

    def best_possible(self, ctx: RuleContext) -> float:
        p = ctx.params
        if p.get("cap") is not None:
            return float(p["cap"])
        core = p["core"]
        best = max(self._scale(ctx, core).values())
        total = best * int(core["take"])
        if p.get("mandatory"):
            total += max(self._scale(ctx, p["mandatory"]).values())
        return total

    @staticmethod
    def _scale(ctx: RuleContext, spec: Mapping[str, Any]) -> Mapping[str, float]:
        name = spec.get("scale")
        if name:
            return ctx.scales[str(name)]
        by_level = spec.get("scale_by_level") or {}
        merged: dict[str, float] = {}
        for scale_name in by_level.values():
            merged.update(ctx.scales[scale_name])
        return merged

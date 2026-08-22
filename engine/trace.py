"""The derivation trace -- the actual product.

A scoring engine that returns 70.0 tells a worried parent nothing. A scoring
engine that returns the *steps* lets them check the arithmetic, understand the
rule, and spot a wrong data pack immediately.

Every rule kind emits its own trace. Nothing in PathAhead may return a score
without one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepKind(str, Enum):
    HEADING = "heading"        # section label, no arithmetic
    COMPONENT = "component"    # a subject contributing points
    EXCLUDED = "excluded"      # a subject considered and not counted
    SUBTOTAL = "subtotal"      # running total so far
    SUBSTITUTION = "substitution"
    CAP = "cap"                # a ceiling was applied
    TOTAL = "total"
    NOTE = "note"              # a caveat the user must see


@dataclass(frozen=True, slots=True)
class Step:
    kind: StepKind
    label: str
    detail: str | None = None
    points: float | None = None
    running_total: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "detail": self.detail,
            "points": self.points,
            "running_total": self.running_total,
        }


@dataclass(slots=True)
class Derivation:
    """The full worked answer: value, ceiling, direction and every step."""

    value: float
    max_value: float | None
    direction: str
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unit: str = "points"

    def add(self, step: Step) -> None:
        self.steps.append(step)

    def numbers(self) -> set[float]:
        """Every number this derivation legitimately produced.

        Used by the AI narrator guardrail: any figure in generated prose that
        is not in this set (or trivially derived from it) rejects the whole
        narration. See engine/guardrail.py.
        """
        out: set[float] = {round(self.value, 4)}
        if self.max_value is not None:
            out.add(round(float(self.max_value), 4))
        for s in self.steps:
            for v in (s.points, s.running_total):
                if v is not None:
                    out.add(round(float(v), 4))
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "max_value": self.max_value,
            "direction": self.direction,
            "unit": self.unit,
            "steps": [s.to_dict() for s in self.steps],
            "warnings": list(self.warnings),
        }

    # -- rendering -------------------------------------------------------

    def as_text(self, indent: str = "") -> str:
        """Plain-text worked answer. No AI involved, and none needed."""
        lines: list[str] = []
        for s in self.steps:
            if s.kind is StepKind.HEADING:
                lines.append(f"{indent}{s.label}")
            elif s.kind is StepKind.NOTE:
                lines.append(f"{indent}  ! {s.label}")
            elif s.kind is StepKind.EXCLUDED:
                detail = f"  {s.detail}" if s.detail else ""
                lines.append(f"{indent}  - {s.label:<34}{_fmt(s.points):>7}   not counted{detail}")
            elif s.kind in (StepKind.SUBTOTAL, StepKind.TOTAL) or s.kind is StepKind.CAP:
                lines.append(f"{indent}  {s.label:<36}{_fmt(s.running_total):>7}")
            else:
                detail = f"  {s.detail}" if s.detail else ""
                lines.append(f"{indent}  {s.label:<36}{_fmt(s.points):>7}{detail}")
        return "\n".join(lines)


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    return f"{v:g}"


def merge_warnings(*groups: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for g in groups:
        for w in g:
            if w not in seen:
                seen.append(w)
    return seen

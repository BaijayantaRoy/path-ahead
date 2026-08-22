"""The contract every scoring rule kind implements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..grades import GradeSheet
from ..trace import Derivation


@dataclass(frozen=True, slots=True)
class RuleContext:
    """Everything a rule may read. Notably: no clock, no network, no globals.

    Rules are pure functions of (params, scales, grades). That is what makes
    them testable against golden fixtures and portable to the browser engine.
    """

    params: Mapping[str, Any]
    scales: Mapping[str, Mapping[str, float]]
    grades: GradeSheet
    caveats: tuple[str, ...] = ()


class RuleKind(Protocol):
    kind: str
    summary: str

    def evaluate(self, ctx: RuleContext) -> Derivation:
        """Compute the score AND the worked steps that produced it."""
        ...

    def best_possible(self, ctx: RuleContext) -> float:
        """The ceiling of this rule -- used by backward mode."""
        ...

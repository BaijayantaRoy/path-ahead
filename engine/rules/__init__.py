"""Scoring rule kinds.

A pack does not contain code. It names a *rule kind* and supplies typed
parameters. Each kind is a small, pure, tested function that knows how to
narrate its own arithmetic.

This is deliberately not a general expression evaluator. Three reasons:

1. A trace beats a number. A rule kind can explain "your 4th subject was
   swapped in because it scored higher than your Mother Tongue"; an
   expression string can only return 70.0.
2. A fixed set of kinds is reviewable. A contributor adding a country pack
   picks a kind or submits a new one as tested code -- a far better review
   surface than auditing an expression grammar for escapes.
3. There is no arbitrary execution surface at all, by construction.

Adding a kind: write the module, register it below, add golden fixtures in
evals/golden/. The CI cross-checks every fixture against both the Python
engine and the JavaScript engine that powers the browser build.
"""

from __future__ import annotations

from ..errors import UnknownRuleKind
from .base import RuleContext, RuleKind
from .lowest_sum import LowestSumRule
from .required_plus_best_n import RequiredPlusBestNRule
from .weighted_best_n import WeightedBestNWithSubstitution

_REGISTRY: dict[str, RuleKind] = {}


def register(rule: RuleKind) -> RuleKind:
    _REGISTRY[rule.kind] = rule
    return rule


for _r in (WeightedBestNWithSubstitution(), LowestSumRule(), RequiredPlusBestNRule()):
    register(_r)


def get_rule(kind: str) -> RuleKind:
    try:
        return _REGISTRY[kind]
    except KeyError as exc:
        raise UnknownRuleKind(
            f"this engine does not implement the scoring rule {kind!r}",
            advice=(
                "The data pack is newer than the app. Please update PathAhead, "
                "then try again."
            ),
        ) from exc


def available_kinds() -> list[str]:
    return sorted(_REGISTRY)


__all__ = ["RuleContext", "RuleKind", "available_kinds", "get_rule", "register"]

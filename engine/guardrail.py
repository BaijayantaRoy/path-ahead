"""The numeric guardrail: enforcement, not intention.

ARCHITECTURE.md promises the AI narrator "cannot introduce a figure that
didn't come from the engine". Promises made in a prompt are requests. This is
the mechanism that makes it a property of the system:

  1. The narrator receives ONLY the computed result object. It is never asked
     to recall anything.
  2. Every numeric token in its output is extracted.
  3. Each must appear in the derivation's own set of numbers, or be trivially
     derived from it (a difference of two of them, or a small count).
  4. Any unmatched number rejects the WHOLE narration. The deterministic
     Tier-0 template output is shown instead -- silently, and correctly.

Deterministic, testable, and it needs no NLI stack. Adversarial cases live in
tests/test_guardrail.py and run in CI.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

#: Matches a bare figure. The trailing lookahead deliberately allows sentence
#: punctuation -- an early version used (?![\w.]) and silently missed every
#: number that ended a sentence, which is exactly where an invented cut-off
#: would appear ("...you need at least 68.4."). Caught by test_guardrail.py.
_NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\w)")

#: Ordinals, years-in-prose and small counts appear legitimately in narration
#: ("the 10th percentile", "three subjects"). They are allowed only if the
#: pack/derivation supplied them, EXCEPT for this tiny fixed allowlist.
_ALWAYS_ALLOWED = {0.0, 1.0, 2.0, 3.0, 4.0, 10.0, 90.0, 100.0}

_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class GuardrailVerdict:
    ok: bool
    offending: tuple[float, ...] = ()
    reason: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.ok


def extract_numbers(text: str) -> list[float]:
    return [float(m.group(1)) for m in _NUMBER_RE.finditer(text)]


def _allowed_set(allowed: Iterable[float]) -> set[float]:
    base = {round(float(a), 4) for a in allowed}
    # Differences between any two engine numbers are legitimate ("4.5 short of").
    derived = {
        round(abs(a - b), 4) for a in base for b in base if a != b
    }
    return base | derived | _ALWAYS_ALLOWED


def check(text: str, allowed: Iterable[float]) -> GuardrailVerdict:
    """Verify that every number in `text` traces back to the engine."""
    permitted = _allowed_set(allowed)
    offending: list[float] = []
    for n in extract_numbers(text):
        if not any(abs(n - p) < _TOLERANCE for p in permitted):
            offending.append(n)
    if offending:
        return GuardrailVerdict(
            ok=False,
            offending=tuple(offending),
            reason=(
                "the narration contained "
                + ", ".join(f"{n:g}" for n in offending)
                + ", which the engine never computed"
            ),
        )
    return GuardrailVerdict(ok=True)


def narrate_safely(
    candidate: str,
    allowed: Iterable[float],
    fallback: str,
) -> tuple[str, GuardrailVerdict]:
    """Return the model's narration if it passes, otherwise the template text.

    The caller shows whichever string comes back. A rejected narration is a
    non-event for the user: they still get a correct, complete explanation.
    """
    verdict = check(candidate, allowed)
    return (candidate if verdict.ok else fallback), verdict


def numbers_from_results(*sources: Sequence[float] | Iterable[float]) -> set[float]:
    out: set[float] = set()
    for s in sources:
        out |= {round(float(x), 4) for x in s}
    return out

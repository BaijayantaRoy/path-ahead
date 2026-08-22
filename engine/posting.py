"""Posting Groups — a gate, not a score.

A PSLE Score decides which of three Posting Groups a child may enter secondary
school through. This module turns a score into that answer and nothing else.

**It deliberately cannot rank, and deliberately cannot guess.** Two rules from
earlier in this project apply directly and both were paid for:

1. *Eligibility is not a low score* (docs/decisions/0003). A posting group says
   which secondary courses are open. It says nothing about which school would
   suit a child, and if this module ever grows a number that could be sorted,
   that is the bug.

2. *The absence of a constraint is not the same as its absence in reality.*
   MOE's published table covers PSLE Scores 4 to 30, and only 26 to 30 when
   English and Mathematics are both AL7 or better. What happens outside it is
   not published on that page. This module returns `outside_the_table` and the
   pack's own words for it — it does not extrapolate a fourth group, and it
   does not say "no group", which a parent would read as "no school".

Everything here is driven by `rule_params.posting_groups` in the pack. There
are no thresholds in this file, because MOE can change them and a data file
should be the only thing that has to change when they do.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .model import Transition


@dataclass(frozen=True, slots=True)
class PostingGroupResult:
    """Which Posting Groups a score opens, and what the family must decide.

    `groups` is empty exactly when the score falls outside the published table.
    That is not the same as "not eligible for anything", and `outside_table`
    carries the pack's wording for it so no caller has to invent any.
    """

    score: float
    groups: tuple[int, ...] = ()
    indicative_level: str = ""
    note: str = ""
    #: True when the family must choose between two groups.
    is_a_choice: bool = False
    #: What happens if no school choices are submitted at all.
    default_group: int | None = None
    #: The chosen group applies to every one of the six school choices.
    choice_applies_to_all_six: bool = True
    #: Set when the score is outside the published table.
    outside_table: Mapping[str, Any] | None = None
    #: Published conditions this score met or failed, in the family's words.
    conditions: tuple[str, ...] = ()
    #: Populated when a row was matched on score but its extra condition was
    #: not met — so the caller can say WHICH condition, rather than going
    #: silent and letting the family assume the worst.
    unmet_conditions: tuple[str, ...] = field(default=())

    @property
    def is_outside_table(self) -> bool:
        return not self.groups


def resolve_posting_group(
    transition: Transition,
    score: float,
    *,
    subject_als: Mapping[str, float] | None = None,
) -> PostingGroupResult:
    """Map a PSLE Score onto the Posting Groups the pack publishes.

    `subject_als` supplies individual Achievement Levels by subject code, which
    the 26–30 row needs: it applies only when English and Mathematics are both
    AL7 or better. Pass nothing and a row carrying such a condition is treated
    as **unproven rather than failed** — the result reports the condition as
    unmet and names it, because a tool that quietly demotes a child for a
    question it never asked is the failure mode this project exists to avoid.
    """
    spec = (transition.rule_params or {}).get("posting_groups")
    if not spec:
        raise KeyError(
            f"transition {transition.id!r} does not declare posting_groups; "
            "this is a data pack problem, not something the user did"
        )

    rows: Sequence[Mapping[str, Any]] = spec.get("groups", ()) or ()
    applies_to_all = bool(spec.get("choice_applies_to_all_six", True))

    for row in rows:
        low, high = float(row["min"]), float(row["max"])
        if not (low <= score <= high):
            continue

        unmet = _unmet(row.get("also_requires"), subject_als)
        if unmet:
            # The score lands in this row but its published condition is not
            # met (or was never asked). Keep walking: a later row may take it.
            # If none does, the score is outside the table, which is the
            # honest answer rather than a guess in either direction.
            continue

        groups = tuple(int(g) for g in row.get("groups", ()))
        return PostingGroupResult(
            score=score,
            groups=groups,
            indicative_level=str(row.get("level", "")),
            note=str(row.get("note", "")),
            is_a_choice=len(groups) > 1,
            default_group=_default_group(groups, spec.get("default_when_unsubmitted")),
            choice_applies_to_all_six=applies_to_all,
            conditions=_conditions(row.get("also_requires")),
        )

    return PostingGroupResult(
        score=score,
        outside_table=spec.get("outside_the_table"),
        choice_applies_to_all_six=applies_to_all,
        unmet_conditions=tuple(
            c
            for row in rows
            if float(row["min"]) <= score <= float(row["max"])
            for c in _conditions(row.get("also_requires"))
        ),
    )


def _default_group(groups: tuple[int, ...], policy: Any) -> int | None:
    """Which group applies when a family submits no school choices at all.

    MOE assigns the MORE academically demanding group in that case. The policy
    is named in the pack rather than assumed here, so a country whose default
    runs the other way needs no code change.
    """
    if not groups:
        return None
    if len(groups) == 1:
        return groups[0]
    if str(policy) == "most_demanding":
        return max(groups)
    if str(policy) == "least_demanding":
        return min(groups)
    return None


def _conditions(also_requires: Any) -> tuple[str, ...]:
    if not also_requires:
        return ()
    subjects = also_requires.get("subjects", ()) or ()
    max_al = also_requires.get("max_al")
    if not subjects or max_al is None:
        return ()
    names = " and ".join(_pretty(str(s)) for s in subjects)
    return (f"AL{int(max_al)} or better in {names}",)


def _unmet(also_requires: Any, subject_als: Mapping[str, float] | None) -> tuple[str, ...]:
    """Which of a row's extra conditions are not demonstrably met."""
    if not also_requires:
        return ()
    subjects = list(also_requires.get("subjects", ()) or ())
    max_al = also_requires.get("max_al")
    if not subjects or max_al is None:
        return ()
    if subject_als is None:
        return _conditions(also_requires)
    failed = [
        s for s in subjects if subject_als.get(str(s)) is None or subject_als[str(s)] > float(max_al)
    ]
    return _conditions(also_requires) if failed else ()


def _pretty(code: str) -> str:
    return {
        "psle-english": "English Language",
        "psle-mathematics": "Mathematics",
        "psle-science": "Science",
        "psle-mtl": "Mother Tongue Language",
    }.get(code, code.replace("psle-", "").replace("-", " ").title())

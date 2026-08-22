"""PathAhead engine -- an open engine for understanding education pathways.

The whole of the core works with no AI model, no API key, no GPU and no
network. Everything above that is optional.

    from engine import load_pack, GradeSheet, explore

    pack = load_pack("packs/singapore")
    grades = GradeSheet.parse("a-level", [
        "h2 Chemistry=A", "h2 Biology=A", "h2 Mathematics=B",
        "gp General Paper=A", "mtl Chinese=B",
    ])
    result = explore(pack, year_level="jc-2", current_year=2026, grades=grades)
    print(result.derivation.as_text())
"""

from __future__ import annotations

__version__ = "1.0.0"

from .backward import MIN_ROUTES, Plan, plan, what_if
from .buckets import Assessment, Bucket
from .cohort import resolve as resolve_cohort
from .errors import (
    DataIncomplete,
    InputError,
    PackError,
    PackFormatError,
    PackIntegrityError,
    PathAheadError,
    RuleError,
    UnknownRuleKind,
)
from .explain import (
    NOT_A_PREDICTION,
    NOT_ADVICE,
    NOT_OFFICIAL,
    explain_options,
    explain_plan,
    explain_score,
    explain_what_if,
)
from .forward import ForwardResult, OutcomeResult, explore, score
from .freshness import Freshness, check_for_update
from .freshness import describe as describe_freshness
from .grades import GradeSheet, SubjectGrade
from .guardrail import check as guardrail_check
from .guardrail import narrate_safely
from .health import HealthReport, check_pack
from .loader import load_pack, verify_bundle
from .model import PACK_FORMAT, Fact, Outcome, Pack, Source, Transition
from .rules import available_kinds
from .trace import Derivation, Step, StepKind

__all__ = [  # noqa: RUF022  -- grouped by role, which is more useful than alphabetical
    "__version__",
    "PACK_FORMAT",
    "MIN_ROUTES",
    # loading
    "load_pack",
    "verify_bundle",
    "Pack",
    "Source",
    "Fact",
    "Outcome",
    "Transition",
    # input
    "GradeSheet",
    "SubjectGrade",
    "resolve_cohort",
    # engine
    "explore",
    "score",
    "plan",
    "what_if",
    "ForwardResult",
    "OutcomeResult",
    "Plan",
    "Assessment",
    "Bucket",
    "Derivation",
    "Step",
    "StepKind",
    "available_kinds",
    # explanation (tier 0)
    "explain_score",
    "explain_options",
    "explain_plan",
    "explain_what_if",
    "NOT_A_PREDICTION",
    "NOT_ADVICE",
    "NOT_OFFICIAL",
    # ai guardrail (tier 1)
    "guardrail_check",
    "narrate_safely",
    # data stewardship
    "check_pack",
    "HealthReport",
    "describe_freshness",
    "check_for_update",
    "Freshness",
    # errors
    "PathAheadError",
    "PackError",
    "PackFormatError",
    "PackIntegrityError",
    "RuleError",
    "UnknownRuleKind",
    "InputError",
    "DataIncomplete",
]

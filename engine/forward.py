"""Forward mode: "here are my results -- what are my options?"

Pure arithmetic over the pathway graph. No AI, no network, no clock beyond
staleness checks. The output is a structured object carrying its own
derivation, its own citations and its own honesty about what it does not know.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any

from .buckets import (
    DISPLAY_ORDER,
    Assessment,
    Bucket,
    assess_band,
    assess_banded,
    assess_min_max_band,
    assess_published_on_another_basis,
    incomplete,
)
from .cohort import resolve
from .errors import InputError
from .grades import GradeSheet
from .model import CohortResolution, Outcome, Pack, Transition
from .rules import RuleContext, get_rule
from .trace import Derivation


@dataclass(slots=True)
class OutcomeResult:
    outcome: Outcome
    assessment: Assessment
    extra_assessment: list[str] = field(default_factory=list)
    citation: dict[str, Any] | None = None
    stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.outcome.id,
            "name": self.outcome.name,
            "institution": self.outcome.institution,
            "institution_short": self.outcome.institution_short,
            "faculty": self.outcome.faculty,
            "url": self.outcome.url,
            "assessment": self.assessment.to_dict(),
            "extra_assessment": list(self.extra_assessment),
            "citation": self.citation,
            "stale": self.stale,
            "band": (
                {
                    "p10": self.outcome.band.p10,
                    "p90": self.outcome.band.p90,
                    "p10_points": self.outcome.band.p10_points,
                    "p90_points": self.outcome.band.p90_points,
                    "basis": self.outcome.band.basis,
                    "year": self.outcome.band.fact.as_of_year,
                    "statistic": self.outcome.band.statistic,
                    "scale": self.outcome.band.scale,
                    "comparable": self.outcome.band.comparable,
                    "years_covered": self.outcome.band.years_covered,
                    "years_label": self.outcome.band.years_label,
                    "history": [
                        {"year": h.year, "low": h.low, "high": h.high, "label": h.label}
                        for h in self.outcome.band.history
                    ],
                }
                if self.outcome.band
                else None
            ),
            "banded": [
                {
                    "stage": p.stage,
                    "basis": p.basis,
                    "scale": p.scale,
                    "qualification": p.qualification,
                    "comparable": p.comparable,
                    "applies_to": p.applies_to,
                    "year": p.fact.as_of_year,
                    "bands": [
                        {"label": b.label, "share_label": b.share_label, "share": b.share}
                        for b in p.bands
                    ],
                }
                for p in self.outcome.banded
            ],
            "intake": self.outcome.intake.value if self.outcome.intake else None,
        }


@dataclass(slots=True)
class ForwardResult:
    """Everything the UI needs, and nothing the UI has to guess."""

    pack_id: str
    pack_version: str
    #: None for a result built by `explore_secondary()` -- a second aggregate
    #: scored from the same grade sheet against an explicitly-named
    #: transition, with no cohort question asked a second time.
    cohort: CohortResolution | None
    transition: Transition
    derivation: Derivation
    comparison_score: float | None
    comparison_basis: str
    results: list[OutcomeResult]
    warnings: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)

    def by_bucket(
        self, fits: dict[str, Any] | None = None
    ) -> dict[Bucket, list[OutcomeResult]]:
        """Group results, ordered by MATCH when a fit score exists.

        Sorting by fit is sorting by the student's own stated preferences, so
        it is permitted and useful. Sorting by selectivity or by pay is not,
        and never happens -- see SAFEGUARDS.md 5.1. Without fit scores the
        order is alphabetical, never a ranking.
        """
        out: dict[Bucket, list[OutcomeResult]] = {b: [] for b in DISPLAY_ORDER}
        for r in self.results:
            out[r.assessment.bucket].append(r)

        def alpha(r: OutcomeResult):
            return (r.outcome.institution_short, r.outcome.name)

        for bucket in out:
            if fits:
                out[bucket].sort(
                    key=lambda r: (
                        -(fits[r.outcome.id].score
                          if fits.get(r.outcome.id) and fits[r.outcome.id].score is not None
                          else -1),
                        *alpha(r),
                    )
                )
            else:
                out[bucket].sort(key=alpha)
        return {b: v for b, v in out.items() if v}

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack": {"id": self.pack_id, "version": self.pack_version},
            "cohort": None if self.cohort is None else {
                "year_level": self.cohort.year_level,
                "label": self.cohort.label,
                "current_year": self.cohort.current_year,
                "stage": self.cohort.stage_id,
                "exam_year": self.cohort.exam_year,
                "admission_year": self.cohort.admission_year,
                "sentence": self.cohort.sentence(),
                "note": self.cohort.note,
            },
            "transition": {
                "id": self.transition.id,
                "name": self.transition.name,
                "direction": self.transition.direction,
                "policy_status": self.transition.policy_status,
                "changed_from": self.transition.changed_from,
            },
            "derivation": self.derivation.to_dict(),
            "comparison_score": self.comparison_score,
            "comparison_basis": self.comparison_basis,
            "results": [r.to_dict() for r in self.results],
            "warnings": list(self.warnings),
            "notices": list(self.notices),
        }


def score(pack: Pack, grades: GradeSheet, transition: Transition) -> Derivation:
    """Evaluate one transition's rule against one grade sheet."""
    rule = get_rule(transition.rule_kind)
    ctx = RuleContext(
        params=transition.rule_params,
        scales=transition.scales,
        grades=grades,
        caveats=transition.caveats,
    )
    return rule.evaluate(ctx)


def explore(
    pack: Pack,
    *,
    year_level: str,
    current_year: int,
    grades: GradeSheet,
    today: _dt.date | None = None,
) -> ForwardResult:
    today = today or _dt.date.today()
    cohort = resolve(pack, year_level, current_year)
    transition = pack.transitions[cohort.transition_id]
    derivation = score(pack, grades, transition)

    notices: list[str] = []
    if transition.policy_status == "mid_rollout":
        notices.append(
            "These rules are part of a system that is still being rolled out. "
            "Check the official page before making a decision on them."
        )
    if transition.changed_from:
        summary = transition.changed_from.get("summary")
        if summary:
            notices.append(f"What changed since last year: {summary}")

    # The comparison score may differ from the headline score. In Singapore's
    # 2026 A-Level cycle it does: the headline is the new 70-point score, but
    # the only published grade profiles are on the previous basis, so the
    # honest comparison uses the 3 H2 grades exactly as NUS advises. This is
    # declared in the pack, never inferred here.
    comparison_key = transition.rule_params.get("comparison_component")
    comparison_score: float | None = derivation.value
    if comparison_key:
        comparison_score = _component_total(derivation, comparison_key)

    results: list[OutcomeResult] = []
    for outcome in pack.outcomes_for(transition.id):
        results.append(
            _assess_outcome(pack, outcome, comparison_score, transition, today)
        )

    return ForwardResult(
        pack_id=pack.id,
        pack_version=pack.version,
        cohort=cohort,
        transition=transition,
        derivation=derivation,
        comparison_score=comparison_score,
        comparison_basis=transition.comparison_basis,
        results=results,
        warnings=list(derivation.warnings),
        notices=notices,
    )


def explore_secondary(
    pack: Pack,
    *,
    transition_id: str,
    grades: GradeSheet,
    today: _dt.date | None = None,
) -> ForwardResult:
    """Score the SAME grade sheet against a second, explicitly-named
    transition, without going through cohort resolution.

    Built for the O-Level stage, which is one exam feeding two different
    published aggregates -- L1R5 for JC/MI and ELR2B2 for polytechnics -- and
    therefore needs two different `Transition` objects scored from one
    `GradeSheet`. `CohortRule` deliberately names exactly one transition per
    cohort (ADR-precedent: PSLE keeps its posting-group logic INSIDE its one
    transition rather than growing a second cohort concept for it), so the
    second aggregate is reached directly by id instead of by pretending the
    family answered a second "what year are you in" question they were never
    asked.

    Everything else -- the derivation, the outcome pool, the citations -- is
    identical in shape to `explore()`, because a family reading two results on
    one screen should not have to learn two different report formats.
    """
    today = today or _dt.date.today()
    try:
        transition = pack.transitions[transition_id]
    except KeyError as exc:
        raise InputError(
            f"this pack has no transition {transition_id!r} loaded",
            advice="This is a data pack problem, not something you did.",
        ) from exc
    derivation = score(pack, grades, transition)
    comparison_key = transition.rule_params.get("comparison_component")
    comparison_score: float | None = derivation.value
    if comparison_key:
        comparison_score = _component_total(derivation, comparison_key)

    results = [
        _assess_outcome(pack, outcome, comparison_score, transition, today)
        for outcome in pack.outcomes_for(transition.id)
    ]

    return ForwardResult(
        pack_id=pack.id,
        pack_version=pack.version,
        cohort=None,
        transition=transition,
        derivation=derivation,
        comparison_score=comparison_score,
        comparison_basis=transition.comparison_basis,
        results=results,
        warnings=list(derivation.warnings),
        notices=[],
    )


def _component_total(derivation: Derivation, key: str) -> float | None:
    """Pull a named subtotal out of the trace, so the comparison basis is
    itself traceable rather than recomputed by a second code path."""
    for step in derivation.steps:
        if step.label.lower().startswith(key.lower()) and step.running_total is not None:
            return step.running_total
    # Fall back to the first subtotal, which is the core group by construction.
    for step in derivation.steps:
        if step.kind.value == "subtotal" and step.running_total is not None:
            return step.running_total
    return None


def _assess_outcome(
    pack: Pack,
    outcome: Outcome,
    comparison_score: float | None,
    transition: Transition,
    today: _dt.date,
) -> OutcomeResult:
    extra = [f"{o.label}: {o.detail}" for o in outcome.overlays]

    if outcome.band is None and outcome.banded:
        # A banded profile is a different published claim from a percentile
        # band, and is assessed by its own function so the two can never be
        # blended. Where more than one stage is published, lead with the one
        # that decides an offer -- being shortlisted is not being admitted.
        # This transition is the A-Level route, so ONLY the A-Level pool may be
        # used. There is deliberately no fallback to another pool: a
        # polytechnic GPA out of 4.00 and an A-Level score out of 70 are
        # different units, and quietly placing one against the other is the
        # exact failure this type was introduced to prevent.
        pool = [p for p in outcome.banded if p.qualification == "a-level"]
        if not pool:
            return OutcomeResult(
                outcome=outcome,
                assessment=incomplete(
                    "this university does not publish a figure for A-Level applicants "
                    "at course level, so there is nothing here to compare you against"
                ),
                extra_assessment=extra,
            )
        # Where two stages are published, lead with the one that decides an
        # offer. Being shortlisted is not being admitted.
        profile = next((p for p in pool if p.stage == "offered"), pool[0])
        src = pack.source(profile.fact.source_id)
        return OutcomeResult(
            outcome=outcome,
            assessment=assess_banded(
                profile,
                comparison_score if profile.comparable else None,
                band_year=profile.fact.as_of_year,
                confidence=profile.fact.confidence,
            ),
            extra_assessment=extra,
            citation={
                "source": src.name,
                "publisher": src.publisher,
                "url": src.url,
                "retrieved": src.retrieved.isoformat(),
                "licence": src.licence,
                "licence_name": src.licence_name,
                "as_of_year": profile.fact.as_of_year,
                "confidence": profile.fact.confidence,
                "note": profile.fact.note,
            },
            stale=profile.fact.is_stale(today),
        )

    if outcome.band is None:
        return OutcomeResult(
            outcome=outcome,
            assessment=incomplete("no verified grade profile loaded for this course"),
            extra_assessment=extra,
        )

    # Comparability is a property of a published figure AND the transition
    # asking about it -- not a fixed fact about the figure alone. A
    # polytechnic's ELR2B2 range is `comparable: False` under the A-Level
    # transition (an A-Level score cannot be placed against an O-Level
    # aggregate), and genuinely comparable under a transition the outcome
    # opted into via `also_scored_under` -- an O-Level applicant's own ELR2B2
    # score IS that range's basis. See Outcome.also_scored_under.
    comparable_here = outcome.band.comparable or transition.id in outcome.also_scored_under

    # This branch has to come before the comparison_score check: a
    # polytechnic's ELR2B2 range is worth showing to a student whether or not
    # their subjects produce an A-Level score, because it is the same number
    # either way and it is not being compared with anything.
    if not comparable_here:
        src = pack.source(outcome.band.fact.source_id)
        return OutcomeResult(
            outcome=outcome,
            assessment=assess_published_on_another_basis(
                outcome.band,
                band_year=outcome.band.fact.as_of_year,
                confidence=outcome.band.fact.confidence,
            ),
            extra_assessment=extra,
            citation={
                "source": src.name,
                "publisher": src.publisher,
                "url": src.url,
                "retrieved": src.retrieved.isoformat(),
                "licence": src.licence,
                "licence_name": src.licence_name,
                "as_of_year": outcome.band.fact.as_of_year,
                "confidence": outcome.band.fact.confidence,
                "note": outcome.band.fact.note,
            },
            stale=outcome.band.fact.is_stale(today),
        )

    if comparison_score is None:
        return OutcomeResult(
            outcome=outcome,
            assessment=incomplete("your entered subjects do not produce a comparable score"),
            extra_assessment=extra,
        )

    band = outcome.band
    # assess_band refuses anything but a p10_p90 statistic outright -- that
    # guard stays exactly as strict as it was; a min_max band that reaches
    # here (comparable_here=True, via also_scored_under) is routed to its own
    # function with its own vocabulary instead of relaxing that guard.
    if band.statistic == "min_max":
        assessment = assess_min_max_band(
            comparison_score,
            band.p10_points,
            band.p90_points,
            direction=transition.direction,
            band_year=band.fact.as_of_year,
            confidence=band.fact.confidence,
        )
    else:
        assessment = assess_band(
            comparison_score,
            band.p10_points,
            band.p90_points,
            direction=transition.direction,
            band_year=band.fact.as_of_year,
            basis=band.basis,
            confidence=band.fact.confidence,
            statistic=band.statistic,
        )
    src = pack.source(band.fact.source_id)
    return OutcomeResult(
        outcome=outcome,
        assessment=assessment,
        extra_assessment=extra,
        citation={
            "source": src.name,
            "publisher": src.publisher,
            "url": src.url,
            "retrieved": src.retrieved.isoformat(),
            "licence": src.licence,
            "licence_name": src.licence_name,
            "as_of_year": band.fact.as_of_year,
            "confidence": band.fact.confidence,
            "note": band.fact.note,
        },
        stale=band.fact.is_stale(today),
    )

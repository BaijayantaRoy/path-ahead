"""Data Health -- a CI gate, not just a report.

ARCHITECTURE.md described this as a published credibility artifact. That is
half of it. Credibility that is only *reported* drifts; credibility that is
*enforced* holds. So the same computation does both jobs:

    pathahead health              -> human-readable report
    pathahead health --gate       -> exit code 1 if the pack is not shippable

A pack fails the gate when it ships a fact that is already past its
`stale_after` date, when a required field sits at `low` confidence, or when
citations point at licences whose obligations are not met.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .model import CONFIDENCE_ORDER, KNOWN_LICENCES, Pack


@dataclass(slots=True)
class HealthIssue:
    severity: str        # "fail" | "warn" | "info"
    path: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "path": self.path, "message": self.message}


@dataclass(slots=True)
class HealthReport:
    pack_id: str
    pack_version: str
    generated: _dt.date
    total_facts: int
    by_confidence: dict[str, int]
    stale: int
    oldest_year: int | None
    newest_retrieval: _dt.date | None
    issues: list[HealthIssue] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)

    @property
    def failures(self) -> list[HealthIssue]:
        return [i for i in self.issues if i.severity == "fail"]

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack": {"id": self.pack_id, "version": self.pack_version},
            "generated": self.generated.isoformat(),
            "total_facts": self.total_facts,
            "by_confidence": self.by_confidence,
            "stale": self.stale,
            "oldest_year": self.oldest_year,
            "newest_retrieval": self.newest_retrieval.isoformat() if self.newest_retrieval else None,
            "coverage": self.coverage,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
        }

    def as_text(self) -> str:
        lines = [
            f"Data Health -- {self.pack_id} {self.pack_version}",
            f"generated {self.generated.isoformat()}",
            "",
            f"  facts            {self.total_facts}",
            f"  high confidence  {self.by_confidence.get('high', 0)}",
            f"  medium           {self.by_confidence.get('medium', 0)}",
            f"  low              {self.by_confidence.get('low', 0)}",
            f"  stale today      {self.stale}",
            f"  oldest data year {self.oldest_year if self.oldest_year else '-'}",
            f"  last retrieved   {self.newest_retrieval.isoformat() if self.newest_retrieval else '-'}",
        ]
        if self.coverage:
            lines.append("")
            lines.append("  coverage")
            for k, v in self.coverage.items():
                lines.append(f"    {k:<34}{v}")
        if self.issues:
            lines.append("")
            for sev in ("fail", "warn", "info"):
                group = [i for i in self.issues if i.severity == sev]
                if not group:
                    continue
                lines.append(f"  {sev.upper()}")
                for i in group:
                    lines.append(f"    {i.path}: {i.message}")
        lines.append("")
        lines.append("  RESULT: " + ("PASS" if self.passed else "FAIL"))
        return "\n".join(lines)

    def as_markdown(self) -> str:
        badge = "PASS" if self.passed else "FAIL"
        rows = [
            f"# Data Health -- `{self.pack_id}` {self.pack_version}",
            "",
            f"**{badge}** - generated {self.generated.isoformat()}",
            "",
            "| Measure | Value |",
            "|---|---|",
            f"| Facts | {self.total_facts} |",
            f"| High confidence | {self.by_confidence.get('high', 0)} |",
            f"| Medium confidence | {self.by_confidence.get('medium', 0)} |",
            f"| Low confidence | {self.by_confidence.get('low', 0)} |",
            f"| Stale today | {self.stale} |",
            f"| Oldest data year | {self.oldest_year or '-'} |",
            f"| Last retrieved | {self.newest_retrieval or '-'} |",
        ]
        for k, v in self.coverage.items():
            rows.append(f"| {k} | {v} |")
        if self.issues:
            rows += ["", "## Issues", "", "| Severity | Path | Message |", "|---|---|---|"]
            for i in self.issues:
                rows.append(f"| {i.severity} | `{i.path}` | {i.message} |")
        return "\n".join(rows)


def check_pack(
    pack: Pack,
    *,
    today: _dt.date | None = None,
    min_confidence: str = "medium",
) -> HealthReport:
    today = today or _dt.date.today()
    issues: list[HealthIssue] = []
    confidences: Counter[str] = Counter()
    stale = 0
    years: list[int] = []
    retrievals: list[_dt.date] = []

    floor = CONFIDENCE_ORDER[min_confidence]
    editorial = 0

    for path, fact in pack.all_facts():
        # Editorial characterisations are opinions, not factual claims. They are
        # counted and reported, but grading them on "confidence" would be a
        # category error -- so the release floor does not apply to them.
        if fact.is_editorial:
            editorial += 1
            if fact.is_stale(today):
                issues.append(
                    HealthIssue("warn", path, "editorial description is due a review")
                )
            continue
        confidences[fact.confidence] += 1
        years.append(fact.as_of_year)
        if fact.is_stale(today):
            stale += 1
            issues.append(
                HealthIssue(
                    "fail",
                    path,
                    f"past its stale_after date ({fact.stale_after}); refresh before release",
                )
            )
        elif fact.days_until_stale(today) is not None and fact.days_until_stale(today) < 45:  # type: ignore[operator]
            issues.append(
                HealthIssue(
                    "warn", path, f"expires in {fact.days_until_stale(today)} days"
                )
            )
        if CONFIDENCE_ORDER[fact.confidence] < floor:
            issues.append(
                HealthIssue(
                    "fail",
                    path,
                    f"confidence {fact.confidence!r} is below the {min_confidence!r} floor "
                    "required for release",
                )
            )
        if fact.source_id not in pack.sources:
            issues.append(HealthIssue("fail", path, f"cites unknown source {fact.source_id!r}"))

    for src in pack.sources.values():
        retrievals.append(src.retrieved)
        if src.licence not in KNOWN_LICENCES:
            issues.append(
                HealthIssue(
                    "warn",
                    f"source.{src.id}",
                    f"declares an unrecognised licence {src.licence!r}; obligations cannot be "
                    "generated automatically",
                )
            )
        if not src.url.startswith("http"):
            issues.append(HealthIssue("fail", f"source.{src.id}", "has no usable URL"))

    # -- the >=3 routes rule, checked as data, not just at runtime --------
    from .backward import MIN_ROUTES

    thin = []
    for outcome in pack.outcomes.values():
        routes = pack.routes_for(outcome)
        if len(routes) < MIN_ROUTES or not any(r.kind != "direct" for r in routes):
            thin.append(outcome.id)
    if thin:
        issues.append(
            HealthIssue(
                "warn",
                "routes",
                f"{len(thin)} outcome(s) have fewer than {MIN_ROUTES} routes or no "
                f"alternative route; backward mode will flag them as incomplete "
                f"(e.g. {', '.join(sorted(thin)[:3])})",
            )
        )

    from .fit import coverage as fit_coverage

    cov = fit_coverage(pack)
    if not cov.complete:
        issues.append(
            HealthIssue(
                "warn",
                "fit.coverage",
                "fit scoring runs in preview: the pack covers "
                f"{', '.join(cov.institutions)} but not {', '.join(cov.missing)}. "
                "Ranking against a partial pool must never be presented as a shortlist.",
            )
        )

    banded = sum(1 for o in pack.outcomes.values() if o.band is not None)
    with_salary = sum(
        1 for o in pack.outcomes.values() if o.employment and o.employment.has_salary
    )
    # Money is the question families ask first, so how far the fee tables have
    # been loaded belongs in the coverage report rather than in someone's head.
    with_fee = sum(
        1 for o in pack.outcomes.values() if o.cost and o.cost.has_any_fee
    )
    with_banded = sum(1 for o in pack.outcomes.values() if o.banded)
    no_profile = sum(
        1 for o in pack.outcomes.values() if o.band is None and not o.banded
    )
    # Worth its own line: these are courses where the institution published
    # real figures against a scale that no longer matches how scores are
    # computed, so the engine shows them and withholds the comparison. It
    # should shrink to zero as each university republishes.
    on_retired_scale = sum(
        1
        for o in pack.outcomes.values()
        if any(not p.comparable for p in o.banded)
    )
    # A third published shape. `min_max` is the lowest AND highest ranked
    # student admitted -- the whole cohort -- while `p10_p90` cuts both tails
    # off by construction. Counting them on one line would let a reader think
    # 116 courses carry the same kind of evidence when they carry two, and the
    # wider one would read as "less selective" purely because of the statistic.
    percentile_bands = sum(
        1 for o in pack.outcomes.values()
        if o.band is not None and o.band.statistic == "p10_p90"
    )
    min_max_bands = sum(
        1 for o in pack.outcomes.values()
        if o.band is not None and o.band.statistic == "min_max"
    )
    # Bands shown without a verdict, for the same reason the banded profiles
    # are: the published basis is not the basis PathAhead scores on.
    bands_not_compared = sum(
        1 for o in pack.outcomes.values() if o.band is not None and not o.band.comparable
    )
    multi_year_bands = sum(
        1 for o in pack.outcomes.values()
        if o.band is not None and o.band.years_covered > 1
    )
    coverage = {
        "outcomes": len(pack.outcomes),
        "outcomes with a grade band": banded,
        "  10th-90th percentile": percentile_bands,
        "  full admitted min-max": min_max_bands,
        "  shown but not compared": bands_not_compared,
        "  carrying 2 or more years": multi_year_bands,
        # Two published shapes, counted separately on purpose. A course with a
        # banded profile is not a gap in the pack -- it is a university that
        # publishes something else, and lumping the two together would hide
        # both how much is loaded and how much is genuinely missing.
        "outcomes with a banded profile": with_banded,
        "  on a retired scale": on_retired_scale,
        "outcomes with no profile": no_profile,
        "outcomes with employment data": with_salary,
        "outcomes with a fee figure": with_fee,
        "outcomes without a fee figure": len(pack.outcomes) - with_fee,
        "outcomes described (editorial)": cov.scored_outcomes,
        "editorial statements": editorial,
        "institutions covered": len(cov.institutions),
        "institutions missing": len(cov.missing),
        "fit scoring": "complete" if cov.complete else "PREVIEW",
        "milestones": len(pack.milestones),
        "routes": len(pack.routes),
        "prerequisites": len(pack.prerequisites),
        "transitions": len(pack.transitions),
        "sources": len(pack.sources),
    }

    return HealthReport(
        pack_id=pack.id,
        pack_version=pack.version,
        generated=today,
        total_facts=sum(confidences.values()),
        by_confidence=dict(confidences),
        stale=stale,
        oldest_year=min(years) if years else None,
        newest_retrieval=max(retrievals) if retrievals else None,
        issues=issues,
        coverage=coverage,
    )

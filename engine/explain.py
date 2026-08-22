"""Tier 0 explanations -- plain English, no model, no key, no GPU.

This is the default and it is complete on its own. An LLM narrator (Tier 1) is
an optional comfort layered on top; it is never what makes the tool work.

For arithmetic, a template built from the derivation trace is not a poor
substitute for a language model -- it is strictly better. It cannot hallucinate
a number, it is identical every time, and it runs offline in microseconds.
"""

from __future__ import annotations

from .backward import Plan
from .forward import ForwardResult
from .model import Pack

#: Rendered wherever a result is shown. Never only in a footer.
NOT_A_PREDICTION = (
    "These are last year's published figures, not this year's outcome. "
    "Real admission decisions consider more than a score."
)

NOT_ADVICE = (
    "PathAhead explains how the published rules work. It does not tell you what "
    "to choose. For decisions about your child's education, speak to their "
    "school's teachers and Education & Career Guidance counsellor, or the "
    "institution's own admissions office."
)

NOT_OFFICIAL = (
    "PathAhead is an independent, open-source tool. It is not affiliated with, "
    "endorsed by, or connected to the Ministry of Education, SEAB, Cambridge "
    "Assessment, or any school, polytechnic, ITE or university."
)


def explain_score(result: ForwardResult, *, detail: bool = True) -> str:
    """The worked answer, in words a parent can check line by line."""
    d = result.derivation
    lines: list[str] = []

    lines.append(result.cohort.sentence())
    if result.cohort.note:
        lines.append(f"  {result.cohort.note}")
    lines.append("")

    lines.append(f"{result.transition.name}")
    if detail:
        lines.append("")
        lines.append(d.as_text())
    else:
        cap = f" out of {d.max_value:g}" if d.max_value else ""
        lines.append(f"  Your score: {d.value:g}{cap}")

    if result.comparison_score is not None and result.comparison_basis:
        lines.append("")
        lines.append(
            f"For comparing against published grade profiles, PathAhead uses "
            f"{result.comparison_score:g} ({result.comparison_basis})."
        )

    for notice in result.notices:
        lines.append("")
        lines.append(f"Note: {notice}")
    for warning in result.warnings:
        lines.append("")
        lines.append(f"Caution: {warning}")

    return "\n".join(lines)


def explain_options(result: ForwardResult, pack: Pack) -> str:
    grouped = result.by_bucket()
    if not grouped:
        return "No courses are loaded for this stage yet."

    lines: list[str] = []
    for _bucket, items in grouped.items():
        first = items[0].assessment
        lines.append("")
        lines.append(f"{first.headline}  ({len(items)})")
        lines.append(f"  {first.explanation}")
        lines.append("")
        for item in items:
            flag = " *" if item.outcome.has_extra_assessment else ""
            stale = "  [figure is out of date - check the official page]" if item.stale else ""
            band = ""
            if item.outcome.band:
                b = item.outcome.band
                band = f"   {b.p10}-{b.p90} ({b.fact.as_of_year})"
            lines.append(f"    {item.outcome.display}{flag}{band}{stale}")
        if any(i.outcome.has_extra_assessment for i in items):
            lines.append("")
            lines.append("    * also requires an interview, test or portfolio")

    lines.append("")
    lines.append(NOT_A_PREDICTION)
    return "\n".join(lines)


def explain_plan(plan: Plan) -> str:
    lines: list[str] = [f"Getting to {plan.outcome.display}"]
    if plan.outcome.faculty:
        lines.append(f"  {plan.outcome.faculty}, {plan.outcome.institution}")
    lines.append("")

    if plan.gap:
        lines.append(plan.gap.sentence())
    else:
        lines.append(
            "PathAhead does not have a verified grade profile for this course yet, "
            "so it will not estimate one."
        )
    lines.append("")

    if plan.prerequisites:
        lines.append("Subjects this route depends on")
        for p in plan.prerequisites:
            lines.append(f"  - {p.requires_subject} at {p.at_stage}")
            if p.depends_on_earlier:
                lines.append(f"      which usually depends on: {p.depends_on_earlier}")
            if p.detail:
                lines.append(f"      {p.detail}")
        lines.append("")

    lines.append(f"Ways in ({len(plan.routes)})")
    for r in plan.routes:
        tag = {"direct": "direct", "alternative": "another way", "second-chance": "second chance"}[r.kind]
        lines.append("")
        lines.append(f"  {r.label}  [{tag}]")
        lines.append(f"    {r.summary}")
        for step in r.steps:
            lines.append(f"      - {step}")
        if r.typical_duration:
            lines.append(f"    Typically takes: {r.typical_duration}")
        if r.caveat:
            lines.append(f"    Note: {r.caveat}")

    for note in plan.notes:
        lines.append("")
        lines.append(note)

    lines.append("")
    lines.append(NOT_ADVICE)
    return "\n".join(lines)


def explain_what_if(before, after, transition_name: str) -> str:
    delta = round(after.value - before.value, 4)
    direction = "higher" if delta > 0 else ("lower" if delta < 0 else "the same")
    lines = [
        f"{transition_name}",
        f"  Before: {before.value:g}",
        f"  After:  {after.value:g}",
        "",
        f"That is {abs(delta):g} {direction}." if delta else "That makes no difference to the total.",
        "",
        after.as_text(),
    ]
    return "\n".join(lines)

"""Compile a YAML pack into the JSON bundle that ships.

Packs version and release independently of the app, like virus definitions:
a corrected cut-off point becomes a data release, not a code release, and a
data release can be reviewed by a teacher who does not read Python.

Outputs three files:

    <id>.json           the bundle the app and the browser build load
    <id>.manifest.json  sha256 + version + counts; the engine refuses a
                        mismatch, so a damaged or altered pack cannot load
    <id>.health.md      the Data Health report, published with the release

Signing (minisign/cosign) wraps the manifest in tools/sign_pack.py. The
checksum is the part the engine always enforces; the signature is the part that
proves who built it.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine import check_pack, load_pack  # noqa: E402
from engine.model import PACK_FORMAT, Pack  # noqa: E402


def _subject_requirement_gap(pack: Pack) -> str:
    """Name the courses whose prerequisites nobody has checked yet.

    The bug that produced this section was a student with no Physics being
    shown NTU's Physics / Applied Physics at 52/100. NTU's requirements are now
    loaded, so that specific course is safe -- and every course still missing
    them behaves exactly the way that one used to.

    A gap that is only visible as an absence gets forgotten. Printing it as a
    number, in the report published with every release, is what stops "we will
    do the rest later" from quietly becoming never.
    """
    uni = [o for o in pack.outcomes.values() if o.route_group == "university-direct"]
    if not uni:
        return ""
    by_inst: dict[str, list[int]] = {}
    for o in uni:
        row = by_inst.setdefault(o.institution_short or o.institution, [0, 0])
        row[1] += 1
        if o.subject_requirements:
            row[0] += 1
    have = sum(r[0] for r in by_inst.values())
    lines = [
        "",
        "## Subject prerequisites",
        "",
        f"{have} of {len(uni)} university-direct courses carry the subjects their",
        "institution requires. The rest are scored WITHOUT that check, which is the",
        "condition that once showed a student with no Physics a 52/100 on Applied",
        "Physics. Those courses say so on their own page rather than implying the",
        "check was made.",
        "",
        "| Institution | Requirements loaded | Courses |",
        "| --- | ---: | ---: |",
    ]
    for inst in sorted(by_inst):
        got, total = by_inst[inst]
        lines.append(f"| {inst} | {got} | {total} |")
    lines += [
        "",
        "Loaded from each institution's own published table. Nothing here is",
        "inferred from a course title: a guess about eligibility is the one kind",
        "of guess this project will not make.",
    ]
    return "\n".join(lines)


def to_bundle(pack: Pack) -> dict[str, Any]:
    """Serialise a Pack back to the same schema the loader reads.

    Round-tripping through the loader's own schema (rather than inventing a
    second wire format) means the browser engine and the Python engine consume
    an identical document, which is what makes the golden cross-check in CI
    meaningful.
    """
    return {
        "pack": {
            "id": pack.id,
            "country": pack.country,
            "name": pack.name,
            "version": pack.version,
            "pack_format": PACK_FORMAT,
            "published": pack.published.isoformat(),
            "description": pack.description,
            "attribution": pack.attribution,
        },
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "publisher": s.publisher,
                "url": s.url,
                "retrieved": s.retrieved.isoformat(),
                "licence": s.licence,
                "licence_name": s.licence_name,
                # Carried into the compiled pack so the browser can render a
                # live link to the licence text. The Singapore Open Data
                # Licence requires exactly that link in the product itself --
                # see Source.licence_url and SAFEGUARDS.md 3a.
                "licence_url": s.licence_url,
                "note": s.note,
            }
            for s in pack.sources.values()
        ],
        "stages": [
            {
                "id": s.id,
                "name": s.name,
                "authority": s.authority,
                "typical_age": s.typical_age,
                "description": s.description,
                "subject_levels": list(s.subject_levels),
            }
            for s in pack.stages.values()
        ],
        "cohorts": [
            {
                "year_level": c.year_level,
                "label": c.label,
                "stage": c.stage_id,
                "years_to_exam": c.years_to_exam,
                "admission_offset": c.admission_offset,
                "transition": c.transition_id,
                "note": c.note,
            }
            for c in pack.cohort_rules.values()
        ],
        "transitions": [
            {
                "id": t.id,
                "stage": t.stage_id,
                "name": t.name,
                "applies_to_exam_years": list(t.applies_to_exam_years),
                "admission_years": list(t.admission_years),
                "direction": t.direction,
                "rule_kind": t.rule_kind,
                "rule_params": t.rule_params,
                "scales": t.scales,
                "comparison_basis": t.comparison_basis,
                "changed_from": t.changed_from,
                "policy_status": t.policy_status,
                "caveats": list(t.caveats),
                "fact": t.fact.to_dict(),
            }
            for t in pack.transitions.values()
        ],
        "outcomes": [
            {
                "id": o.id,
                "institution": o.institution,
                "institution_short": o.institution_short,
                "name": o.name,
                "faculty": o.faculty,
                "transition": o.transition_id,
                "url": o.url,
                "route_group": o.route_group,
                "tags": list(o.tags),
                "band": (
                    {
                        "p10": o.band.p10,
                        "p90": o.band.p90,
                        "p10_points": o.band.p10_points,
                        "p90_points": o.band.p90_points,
                        "basis": o.band.basis,
                        # What the endpoints MEAN, and whether they may be
                        # compared with the score this transition computes. The
                        # browser engine refuses the comparison on these, so
                        # dropping them from the bundle would silently turn an
                        # O-Level aggregate back into a verdict.
                        "statistic": o.band.statistic,
                        "scale": o.band.scale,
                        "comparable": o.band.comparable,
                        "years_covered": o.band.years_covered,
                        "years_label": o.band.years_label,
                        "history": [
                            {"year": h.year, "low": h.low, "high": h.high, "label": h.label}
                            for h in o.band.history
                        ],
                        "fact": o.band.fact.to_dict(),
                    }
                    if o.band
                    else None
                ),
                "intake": o.intake.to_dict() if o.intake else None,
                "banded": [
                    {
                        "stage": p.stage,
                        "basis": p.basis,
                        "scale": p.scale,
                        "qualification": p.qualification,
                        "comparable": p.comparable,
                        "applies_to": p.applies_to,
                        "bands": [
                            {
                                "label": b.label,
                                "share_label": b.share_label,
                                "low": b.low,
                                "high": b.high,
                                "share": b.share,
                            }
                            for b in p.bands
                        ],
                        "fact": p.fact.to_dict(),
                    }
                    for p in o.banded
                ],
                "poly_gpa": (
                    {
                        "p10": o.poly_gpa.p10,
                        "p90": o.poly_gpa.p90,
                        "fact": o.poly_gpa.fact.to_dict() if o.poly_gpa.fact else None,
                    }
                    if o.poly_gpa
                    else None
                ),
                "employment": (
                    {
                        "employment_rate": o.employment.employment_rate,
                        "employment_rate_ft_perm": o.employment.employment_rate_ft_perm,
                        "gross_median": o.employment.gross_median,
                        "gross_p25": o.employment.gross_p25,
                        "gross_p75": o.employment.gross_p75,
                        "covers": o.employment.covers,
                        "unavailable_reason": o.employment.unavailable_reason,
                        "fact": o.employment.fact.to_dict() if o.employment.fact else None,
                    }
                    if o.employment
                    else None
                ),
                "cost": (
                    {
                        "annual_fee_citizen": o.cost.annual_fee_citizen,
                        "annual_fee_pr": o.cost.annual_fee_pr,
                        "annual_fee_international": o.cost.annual_fee_international,
                        "annual_fee_is_other": o.cost.annual_fee_is_other,
                        "annual_fee_no_grant": o.cost.annual_fee_no_grant,
                        "bond_years_citizen": o.cost.bond_years_citizen,
                        "bond_years_pr_is": o.cost.bond_years_pr_is,
                        "fee_group": o.cost.fee_group,
                        "years": o.cost.years,
                        "tuition_grant_available": o.cost.tuition_grant_available,
                        "bond_note": o.cost.bond_note,
                        # SIT charges per credit unit and publishes no annual
                        # figure. Dropping these would leave the browser with a
                        # course whose cost is knowable and unshown.
                        "fee_basis": o.cost.fee_basis,
                        "total_credits": o.cost.total_credits,
                        "fee_per_credit_citizen": o.cost.fee_per_credit_citizen,
                        "fee_per_credit_pr": o.cost.fee_per_credit_pr,
                        "fee_per_credit_international": o.cost.fee_per_credit_international,
                        "fee_per_credit_is_other": o.cost.fee_per_credit_is_other,
                        "fee_per_credit_no_grant": o.cost.fee_per_credit_no_grant,
                        "total_citizen": o.cost.total_for("citizen"),
                        "total_pr": o.cost.total_for("pr"),
                        "total_international": o.cost.total_for("international"),
                        "fact": o.cost.fact.to_dict() if o.cost.fact else None,
                    }
                    if o.cost
                    else None
                ),
                "flexibility": (
                    {
                        "declares_major_later": o.flexibility.declares_major_later,
                        "common_first_year": o.flexibility.common_first_year,
                        "switching_note": o.flexibility.switching_note,
                        "keeps_open": list(o.flexibility.keeps_open),
                        "forecloses": list(o.flexibility.forecloses),
                        "fact": o.flexibility.fact.to_dict() if o.flexibility.fact else None,
                    }
                    if o.flexibility
                    else None
                ),
                "editorial": (
                    {
                        "interests": list(o.editorial.interests),
                        "subject_affinity": list(o.editorial.subject_affinity),
                        "assessment_style": list(o.editorial.assessment_style),
                        "work_setting": list(o.editorial.work_setting),
                        "teamwork": o.editorial.teamwork,
                        "maths_intensity": o.editorial.maths_intensity,
                        "writing_intensity": o.editorial.writing_intensity,
                        "sectors": list(o.editorial.sectors),
                        "summary": o.editorial.summary,
                        "fact": o.editorial.fact.to_dict() if o.editorial.fact else None,
                    }
                    if o.editorial
                    else None
                ),
                # Why a fee is absent, where the absence is a decision. Without
                # this the browser shows a bare dash and the reader cannot tell
                # it apart from a figure nobody has got round to loading.
                "fee_note": o.fee_note,
                # Without this the browser cannot tell that a course is taught
                # in a language, and would go back to ranking it blind.
                "language_requirement": (
                    {
                        "language": o.language_requirement.language,
                        "label": o.language_requirement.label,
                        "at_stage": o.language_requirement.at_stage,
                        "taught_in_language": o.language_requirement.taught_in_language,
                        "detail": o.language_requirement.detail,
                        "fact": (o.language_requirement.fact.to_dict()
                                 if o.language_requirement.fact else None),
                    }
                    if o.language_requirement
                    else None
                ),
                # Eligibility. The browser must block on this too, or the
                # engines disagree about who may be scored.
                "subject_requirements": [
                    {"subjects": list(r.subjects), "at_level": r.at_level,
                     "label": r.label, "detail": r.detail,
                     "fact": r.fact.to_dict() if r.fact else None}
                    for r in o.subject_requirements
                ],
                # How long it runs. Held apart from `cost` so a course without
                # a loaded fee still knows its own length.
                "duration": (
                    {
                        "years": o.duration.years,
                        "structure": o.duration.structure,
                        "fact": o.duration.fact.to_dict() if o.duration.fact else None,
                    }
                    if o.duration
                    else None
                ),
                # Whether a licensing body recognises the qualification. For
                # nursing, optometry and the like this decides whether you can
                # practise at all.
                "accreditation": [
                    {"body": a.body, "label": a.label, "detail": a.detail,
                     "fact": a.fact.to_dict() if a.fact else None}
                    for a in o.accreditation
                ],
                # Where it leads next, and with how much advanced standing.
                "progression": [
                    {"label": p.label, "exemption": p.exemption, "detail": p.detail,
                     "fact": p.fact.to_dict() if p.fact else None}
                    for p in o.progression
                ],
                "overlays": [
                    {
                        "kind": ov.kind.value,
                        "label": ov.label,
                        "detail": ov.detail,
                        "source": ov.source_id,
                    }
                    for ov in o.overlays
                ],
            }
            for o in pack.outcomes.values()
        ],
        "routes": [
            {
                "id": r.id,
                "applies_to": list(r.applies_to),
                "kind": r.kind,
                "label": r.label,
                "summary": r.summary,
                "steps": list(r.steps),
                "typical_duration": r.typical_duration,
                "caveat": r.caveat,
                "source": r.source_id,
            }
            for r in pack.routes
        ],
        "milestones": [
            {
                "id": m.id,
                "label": m.label,
                "detail": m.detail,
                "year_offset": m.year_offset,
                "month": m.month,
                "day": m.day,
                "kind": m.kind,
                "applies_to": list(m.applies_to),
                "requires_service": m.requires_service,
                "approximate": m.approximate,
                "url": m.url,
                "fact": m.fact.to_dict() if m.fact else None,
            }
            for m in pack.milestones
        ],
        "subjects": pack.subjects,
        "interests": pack.interests,
        "schools": pack.schools,
        "postal_districts": pack.postal_districts,
        "prerequisites": [
            {
                "id": p.id,
                "applies_to": list(p.applies_to),
                "requires_subject": p.requires_subject,
                "at_stage": p.at_stage,
                "depends_on_earlier": p.depends_on_earlier,
                "detail": p.detail,
                "fact": p.fact.to_dict(),
            }
            for p in pack.prerequisites
        ],
    }


def build(pack_dir: str | Path, out_dir: str | Path) -> dict[str, Path]:
    pack = load_pack(pack_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bundle = to_bundle(pack)
    bundle_path = out / f"{pack.id}.json"
    payload = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False)
    bundle_path.write_text(payload, encoding="utf-8")

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    report = check_pack(pack)

    manifest = {
        "pack_id": pack.id,
        "version": pack.version,
        "pack_format": PACK_FORMAT,
        "published": pack.published.isoformat(),
        "built": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": digest,
        "bytes": bundle_path.stat().st_size,
        "counts": {
            "sources": len(pack.sources),
            "transitions": len(pack.transitions),
            "outcomes": len(pack.outcomes),
            "routes": len(pack.routes),
            "prerequisites": len(pack.prerequisites),
            "facts": report.total_facts,
        },
        "health": {
            "passed": report.passed,
            "by_confidence": report.by_confidence,
            "stale": report.stale,
        },
    }
    manifest_path = out / f"{pack.id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    health_path = out / f"{pack.id}.health.md"
    health_path.write_text(
        report.as_markdown() + "\n" + _subject_requirement_gap(pack) + "\n",
        encoding="utf-8",
    )

    return {"bundle": bundle_path, "manifest": manifest_path, "health": health_path}


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", default=str(REPO / "packs" / "singapore"))
    ap.add_argument("--out", default=str(REPO / "dist"))
    args = ap.parse_args(argv)
    for label, path in build(args.pack, args.out).items():
        print(f"{label:<10}{path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

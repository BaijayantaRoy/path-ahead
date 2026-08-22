"""Loading and validating a data pack.

Two formats, one loader:

  * YAML source (packs/<id>/) -- human-authored, comment-friendly, reviewable
    by a teacher who does not write code. Needs PyYAML.
  * Compiled JSON bundle (dist/packs/<id>.json) -- what ships, what the browser
    build fetches, what gets checksummed and signed. Needs nothing.

Validation is strict and the messages are aimed at a pack author, not a user:
a pack that would produce a wrong number must fail to load rather than load
quietly.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .errors import PackError, PackFormatError, PackIntegrityError
from .model import (
    PACK_FORMAT,
    Accreditation,
    BandedProfile,
    BandYear,
    CohortRule,
    Cost,
    Duration,
    EditorialProfile,
    Employment,
    Fact,
    Flexibility,
    GradeBand,
    LanguageRequirement,
    Milestone,
    Outcome,
    Overlay,
    OverlayKind,
    Pack,
    PolyGpa,
    Prerequisite,
    ProfileBand,
    Progression,
    Route,
    Source,
    Stage,
    SubjectRequirement,
    Transition,
)

_PACK_FILES = (
    "pack.yaml",
    "cohorts.yaml",
    "stages.yaml",
    "subjects.yaml",
    "interests.yaml",
    "transitions.yaml",
    # One stage, one file: sources, cohorts, subjects and the transition for
    # the PSLE stage live together in psle.yaml. It is listed AFTER
    # stages.yaml, subjects.yaml and transitions.yaml because _read_yaml_dir
    # merges lists by appending and dicts by updating -- so a stage-scoped
    # file can only ever add to the shared sections, never silently replace
    # something another file already declared.
    "psle.yaml",
    # Same one-stage-one-file rule as psle.yaml above: the O-Level stage's
    # sources, cohorts, subjects, transitions (2027 legacy AND 2028 SEC) and
    # JC/MI outcomes all live in olevel.yaml. It is listed after psle.yaml and
    # before outcomes-polytechnic.yaml so that _attach_cross_transition_reuse
    # (which needs olevel.yaml's transition ids already merged in) runs after
    # both this file and the polytechnic outcomes it tags are loaded -- see
    # that function in this module for why the ordering there, not here, is
    # what actually matters.
    "olevel.yaml",
    # Secondary-school directory + postal-district table for the PSLE
    # shortlisting stage (school_fit.py). Listed after psle.yaml so
    # psle.yaml's own sources/cohorts are already merged, and it declares no
    # transitions or outcomes of its own, so ordering relative to
    # outcomes*.yaml does not matter the way it does for olevel.yaml above.
    "secondary-schools.yaml",
    "outcomes.yaml",
    "outcomes-ntu-smu.yaml",
    "outcomes-sutd-sit-suss.yaml",
    "outcomes-polytechnic.yaml",
    "profiles.yaml",
    "routes.yaml",
    "prerequisites.yaml",
    "milestones.yaml",
)


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------


def load_pack(path: str | Path) -> Pack:
    """Load a pack from a directory of YAML files or a compiled .json bundle."""
    p = Path(path)
    if p.is_dir():
        return _from_mapping(_read_yaml_dir(p), origin=str(p))
    if p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        return _from_mapping(data, origin=str(p))
    raise PackError(
        f"{p} is neither a pack directory nor a compiled .json pack",
        advice="Point PathAhead at packs/singapore or at a compiled pack bundle.",
    )


def verify_bundle(bundle_path: str | Path, manifest_path: str | Path | None = None) -> str:
    """Check a compiled pack against its manifest checksum. Returns the digest.

    Signature verification (minisign/cosign) sits on top of this in
    tools/sign_pack.py; the checksum is the part the engine always enforces.
    """
    b = Path(bundle_path)
    digest = hashlib.sha256(b.read_bytes()).hexdigest()
    m = Path(manifest_path) if manifest_path else b.with_suffix(".manifest.json")
    if not m.exists():
        raise PackIntegrityError(
            f"no manifest found for {b.name}",
            advice="Re-download the data pack. A pack without a manifest is not trusted.",
        )
    manifest = json.loads(m.read_text(encoding="utf-8"))
    expected = manifest.get("sha256")
    if expected != digest:
        raise PackIntegrityError(
            f"{b.name} does not match its manifest checksum",
            advice=(
                "The data file may be damaged or altered. Delete it and let "
                "PathAhead download a fresh copy."
            ),
        )
    return digest


# --------------------------------------------------------------------------
# YAML reading
# --------------------------------------------------------------------------


def _read_yaml_dir(directory: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise PackError(
            "PyYAML is needed to read pack source files",
            advice="Run the installer again, or use a compiled .json pack instead.",
        ) from exc

    merged: dict[str, Any] = {}
    for name in _PACK_FILES:
        f = directory / name
        if not f.exists():
            continue
        loaded = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, Mapping):
            raise PackError(f"{f}: expected a mapping at the top level")
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key].extend(value)
            elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value
    if not merged:
        raise PackError(
            f"{directory} contains no pack files",
            advice=f"A pack directory needs at least pack.yaml. Looked for: {', '.join(_PACK_FILES)}.",
        )
    return merged


# --------------------------------------------------------------------------
# mapping -> Pack
# --------------------------------------------------------------------------


def _require(d: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise PackError(f"{where}: missing required field {key!r}")
    return d[key]


def _from_mapping(data: Mapping[str, Any], *, origin: str) -> Pack:
    meta = _require(data, "pack", origin)
    fmt = int(meta.get("pack_format", 0))
    if fmt != PACK_FORMAT:
        raise PackFormatError(
            f"pack format {fmt} but this engine speaks format {PACK_FORMAT}",
            advice=(
                "Update PathAhead to read this data pack, or use a data pack "
                "that matches your version of the app."
            ),
        )

    pack = Pack(
        id=str(_require(meta, "id", origin)),
        country=str(meta.get("country", "")),
        name=str(_require(meta, "name", origin)),
        version=str(_require(meta, "version", origin)),
        pack_format=fmt,
        published=_date(_require(meta, "published", origin)),
        description=str(meta.get("description", "")),
        attribution=list(meta.get("attribution", [])),
    )

    # -- sources ---------------------------------------------------------
    for row in data.get("sources", []) or []:
        src = Source.from_dict(row)
        pack.sources[src.id] = src
    if not pack.sources:
        raise PackError(
            f"{origin}: a pack must declare at least one source",
            advice="Every number in PathAhead has to be traceable. Add a sources: block.",
        )

    # -- stages ----------------------------------------------------------
    for row in data.get("stages", []) or []:
        stage = Stage(
            id=str(row["id"]),
            name=str(row["name"]),
            authority=str(row.get("authority", "")),
            typical_age=str(row.get("typical_age", "")),
            description=str(row.get("description", "")),
            subject_levels=tuple(row.get("subject_levels", ())),
        )
        pack.stages[stage.id] = stage

    # -- cohort rules ----------------------------------------------------
    for row in data.get("cohorts", []) or []:
        cr = CohortRule(
            year_level=str(row["year_level"]),
            label=str(row["label"]),
            stage_id=str(row["stage"]),
            years_to_exam=int(row["years_to_exam"]),
            admission_offset=int(row.get("admission_offset", 1)),
            transition_id=str(row["transition"]),
            note=row.get("note"),
        )
        pack.cohort_rules[cr.year_level] = cr

    # -- transitions -----------------------------------------------------
    for row in data.get("transitions", []) or []:
        where = f"{origin}: transition {row.get('id')!r}"
        fact = Fact.from_dict(_require(row, "fact", where))
        _check_source(pack, fact, where)
        t = Transition(
            id=str(row["id"]),
            stage_id=str(row["stage"]),
            name=str(row["name"]),
            applies_to_exam_years=tuple(int(y) for y in row.get("applies_to_exam_years", ())),
            admission_years=tuple(int(y) for y in row.get("admission_years", ())),
            direction=str(row.get("direction", "higher_is_better")),  # type: ignore[arg-type]
            rule_kind=str(_require(row, "rule_kind", where)),
            rule_params=dict(_require(row, "rule_params", where)),
            scales={k: {kk: float(vv) for kk, vv in v.items()} for k, v in row.get("scales", {}).items()},
            fact=fact,
            comparison_basis=str(row.get("comparison_basis", "")),
            changed_from=row.get("changed_from"),
            policy_status=str(row.get("policy_status", "settled")),  # type: ignore[arg-type]
            caveats=tuple(row.get("caveats", ())),
        )
        if t.stage_id not in pack.stages:
            raise PackError(f"{where}: refers to unknown stage {t.stage_id!r}")
        pack.transitions[t.id] = t

    # -- outcomes --------------------------------------------------------
    for row in data.get("outcomes", []) or []:
        where = f"{origin}: outcome {row.get('id')!r}"
        band = None
        if row.get("band"):
            b = row["band"]
            bfact = Fact.from_dict(_require(b, "fact", where + " band"))
            _check_source(pack, bfact, where + " band")
            statistic = str(b.get("statistic", "p10_p90"))
            if statistic not in ("p10_p90", "min_max"):
                raise PackError(
                    f"{where} band: unknown statistic {statistic!r}. The endpoints of "
                    f"a band mean nothing until this says what they are; guessing "
                    f"would let a full min-to-max range be read as a middle-80% "
                    f"percentile band."
                )
            band = GradeBand(
                p10=str(b["p10"]),
                p90=str(b["p90"]),
                p10_points=float(b["p10_points"]),
                p90_points=float(b["p90_points"]),
                basis=str(b.get("basis", "")),
                fact=bfact,
                statistic=statistic,
                scale=str(b.get("scale", "")),
                comparable=bool(b.get("comparable", True)),
                history=tuple(
                    BandYear(
                        year=int(h["year"]),
                        low=float(h["low"]),
                        high=float(h["high"]),
                        label=str(h.get("label", "")),
                    )
                    for h in b.get("history", []) or []
                ),
            )
        banded: list[BandedProfile] = []
        for p in row.get("banded", []) or []:
            pfact = Fact.from_dict(_require(p, "fact", where + " banded"))
            _check_source(pack, pfact, where + " banded")
            banded.append(
                BandedProfile(
                    stage=str(p["stage"]),
                    basis=str(p["basis"]),
                    scale=str(p["scale"]),
                    qualification=str(p.get("qualification", "a-level")),
                    comparable=bool(p.get("comparable", True)),
                    applies_to=str(p.get("applies_to", "programme")),
                    bands=tuple(
                        ProfileBand(
                            label=str(b["label"]),
                            share_label=str(b["share_label"]),
                            low=_num(b.get("low")),
                            high=_num(b.get("high")),
                            share=_num(b.get("share")),
                        )
                        for b in p.get("bands", []) or []
                    ),
                    fact=pfact,
                )
            )
        if band and banded:
            raise PackError(
                f"{where}: has both a percentile band and a banded profile. They are "
                f"different published claims and holding both invites blending them. "
                f"Record whichever the institution actually publishes."
            )

        intake = None
        if row.get("intake"):
            intake = Fact.from_dict(row["intake"])
            _check_source(pack, intake, where + " intake")

        overlays = tuple(
            Overlay(
                kind=OverlayKind(o["kind"]),
                label=str(o["label"]),
                detail=str(o.get("detail", "")),
                source_id=o.get("source"),
            )
            for o in row.get("overlays", []) or []
        )
        poly_gpa = None
        if row.get("poly_gpa"):
            g = row["poly_gpa"]
            gfact = None
            if g.get("fact"):
                gfact = Fact.from_dict(g["fact"])
                _check_source(pack, gfact, where + " poly_gpa")
            poly_gpa = PolyGpa(p10=float(g["p10"]), p90=float(g["p90"]), fact=gfact)

        employment = None
        if row.get("employment"):
            e = row["employment"]
            efact = None
            if e.get("fact"):
                efact = Fact.from_dict(e["fact"])
                _check_source(pack, efact, where + " employment")
            employment = Employment(
                employment_rate=_num(e.get("employment_rate")),
                employment_rate_ft_perm=_num(e.get("employment_rate_ft_perm")),
                gross_median=_int(e.get("gross_median")),
                gross_p25=_int(e.get("gross_p25")),
                gross_p75=_int(e.get("gross_p75")),
                covers=str(e.get("covers", "")),
                fact=efact,
                unavailable_reason=e.get("unavailable_reason"),
            )

        cost = None
        if row.get("cost"):
            c = row["cost"]
            cfact = None
            if c.get("fact"):
                cfact = Fact.from_dict(c["fact"])
                _check_source(pack, cfact, where + " cost")
            cost = Cost(
                annual_fee_citizen=_int(c.get("annual_fee_citizen")),
                annual_fee_pr=_int(c.get("annual_fee_pr")),
                annual_fee_international=_int(c.get("annual_fee_international")),
                annual_fee_is_other=_int(c.get("annual_fee_is_other")),
                annual_fee_no_grant=_int(c.get("annual_fee_no_grant")),
                bond_years_citizen=int(c.get("bond_years_citizen", 0)),
                bond_years_pr_is=int(c.get("bond_years_pr_is", 3)),
                fee_group=c.get("fee_group"),
                years=_num(c.get("years")),
                tuition_grant_available=bool(c.get("tuition_grant_available", True)),
                bond_note=c.get("bond_note"),
                fact=cfact,
                fee_basis=str(c.get("fee_basis", "annual")),
                total_credits=_int(c.get("total_credits")),
                fee_per_credit_citizen=_num(c.get("fee_per_credit_citizen")),
                fee_per_credit_pr=_num(c.get("fee_per_credit_pr")),
                fee_per_credit_international=_num(c.get("fee_per_credit_international")),
                fee_per_credit_is_other=_num(c.get("fee_per_credit_is_other")),
                fee_per_credit_no_grant=_num(c.get("fee_per_credit_no_grant")),
            )
            if cost.fee_basis not in ("annual", "per_credit"):
                raise PackError(
                    f"{where} cost: unknown fee_basis {cost.fee_basis!r}. A fee means "
                    f"nothing until this says whether it is charged per year or per "
                    f"credit unit."
                )
            if cost.fee_basis == "per_credit" and cost.annual_fee_citizen:
                raise PackError(
                    f"{where} cost: a per-credit programme carries an annual fee. "
                    f"SIT charges per credit unit and publishes no annual figure; "
                    f"dividing the total by a nominal number of years would invent "
                    f"one, and it would be wrong for any student taking a lighter "
                    f"or heavier load."
                )
            if cost.fee_basis == "per_credit" and not cost.total_credits:
                raise PackError(
                    f"{where} cost: a per-credit fee with no credit total cannot "
                    f"produce a number a family can use."
                )

        language_requirement = None
        if row.get("language_requirement"):
            lr = row["language_requirement"]
            lrfact = None
            if lr.get("fact"):
                lrfact = Fact.from_dict(lr["fact"])
                _check_source(pack, lrfact, where + " language_requirement")
            language_requirement = LanguageRequirement(
                language=str(lr["language"]),
                label=str(lr["label"]),
                at_stage=str(lr.get("at_stage", "o-level")),
                taught_in_language=bool(lr.get("taught_in_language", False)),
                detail=str(lr.get("detail", "")),
                fact=lrfact,
            )

        flexibility = None
        if row.get("flexibility"):
            f = row["flexibility"]
            ffact = None
            if f.get("fact"):
                ffact = Fact.from_dict(f["fact"])
                _check_source(pack, ffact, where + " flexibility")
            flexibility = Flexibility(
                declares_major_later=bool(f.get("declares_major_later", False)),
                common_first_year=bool(f.get("common_first_year", False)),
                switching_note=f.get("switching_note"),
                keeps_open=tuple(f.get("keeps_open", ())),
                forecloses=tuple(f.get("forecloses", ())),
                fact=ffact,
            )

        editorial = None
        if row.get("editorial"):
            ed = row["editorial"]
            edfact = None
            if ed.get("fact"):
                edfact = Fact.from_dict(ed["fact"])
                _check_source(pack, edfact, where + " editorial")
                if not edfact.is_editorial:
                    raise PackError(
                        f"{where}: an editorial profile must declare basis: editorial",
                        advice=(
                            "PathAhead's own characterisation of a course is an opinion, "
                            "not a published fact, and must be labelled as one."
                        ),
                    )
            editorial = EditorialProfile(
                interests=tuple(ed.get("interests", ())),
                subject_affinity=tuple(ed.get("subject_affinity", ())),
                assessment_style=tuple(ed.get("assessment_style", ())),
                work_setting=tuple(ed.get("work_setting", ())),
                teamwork=ed.get("teamwork"),
                maths_intensity=ed.get("maths_intensity"),
                writing_intensity=ed.get("writing_intensity"),
                sectors=tuple(ed.get("sectors", ())),
                summary=ed.get("summary"),
                fact=edfact,
            )

        # -- duration, accreditation, progression ------------------------
        duration = None
        # A duration recorded inside a cost block is still a duration. Rather
        # than leave 75 university courses showing no length while every
        # polytechnic shows one, lift it out — same published figure, same
        # source, so nothing is invented. An explicit `duration:` block always
        # wins, because it can also carry structure.
        if not row.get("duration") and cost is not None and cost.years:
            duration = Duration(years=float(cost.years), structure="", fact=cost.fact)
        if row.get("duration"):
            d = row["duration"]
            dfact = None
            if d.get("fact"):
                dfact = Fact.from_dict(d["fact"])
                _check_source(pack, dfact, where + " duration")
            duration = Duration(
                years=float(d["years"]),
                structure=str(d.get("structure", "")),
                fact=dfact,
            )

        # `row` and `where` are bound as defaults rather than captured. This
        # closure is defined inside the outcome loop and, today, is always
        # consumed within the same iteration -- so capturing would work. It
        # would stop working the moment someone stored the generator and
        # drained it later, at which point every outcome would be validated
        # against the LAST row's data and the error messages would name the
        # wrong course. Binding at definition costs nothing and removes the
        # trap; it also satisfies ruff's B023, which is flagging exactly this.
        def _sub_facts(key, where_label, row=row, where=where):
            rows = row.get(key, []) or []
            for r in rows:
                if r.get("fact"):
                    f = Fact.from_dict(r["fact"])
                    _check_source(pack, f, f"{where} {where_label}")
                    yield r, f
                else:
                    yield r, None

        # -- subject requirements (ELIGIBILITY, checked before preference) --
        subject_requirements = tuple(
            SubjectRequirement(
                subjects=tuple(str(x) for x in (r.get("subjects") or ())),
                at_level=str(r.get("at_level", "")),
                label=str(r.get("label", "")),
                detail=str(r.get("detail", "")),
                fact=f,
            )
            for r, f in _sub_facts("subject_requirements", "subject requirement")
        )

        accreditation = tuple(
            Accreditation(body=str(r["body"]), label=str(r["label"]),
                          detail=str(r.get("detail", "")), fact=f)
            for r, f in _sub_facts("accreditation", "accreditation")
        )
        progression = tuple(
            Progression(label=str(r["label"]), exemption=str(r.get("exemption", "")),
                        detail=str(r.get("detail", "")), fact=f)
            for r, f in _sub_facts("progression", "progression")
        )

        out = Outcome(
            id=str(row["id"]),
            institution=str(row["institution"]),
            institution_short=str(row.get("institution_short", row["institution"])),
            name=str(row["name"]),
            faculty=row.get("faculty"),
            transition_id=str(row["transition"]),
            band=band,
            intake=intake,
            overlays=overlays,
            url=row.get("url"),
            route_group=str(row.get("route_group", "university-direct")),
            tags=tuple(row.get("tags", ())),
            employment=employment,
            cost=cost,
            flexibility=flexibility,
            editorial=editorial,
            poly_gpa=poly_gpa,
            banded=tuple(banded),
            fee_note=row.get("fee_note"),
            language_requirement=language_requirement,
            subject_requirements=subject_requirements,
            duration=duration,
            accreditation=accreditation,
            progression=progression,
            also_scored_under=tuple(row.get("also_scored_under", ())),
        )
        if out.transition_id not in pack.transitions:
            raise PackError(f"{where}: refers to unknown transition {out.transition_id!r}")
        pack.outcomes[out.id] = out

    # -- routes ----------------------------------------------------------
    for row in data.get("routes", []) or []:
        pack.routes.append(
            Route(
                id=str(row["id"]),
                applies_to=tuple(row["applies_to"]),
                kind=str(row.get("kind", "alternative")),  # type: ignore[arg-type]
                label=str(row["label"]),
                summary=str(row["summary"]),
                steps=tuple(row.get("steps", ())),
                typical_duration=row.get("typical_duration"),
                caveat=row.get("caveat"),
                source_id=row.get("source"),
            )
        )

    # -- prerequisites ---------------------------------------------------
    for row in data.get("prerequisites", []) or []:
        where = f"{origin}: prerequisite {row.get('id')!r}"
        fact = Fact.from_dict(_require(row, "fact", where))
        _check_source(pack, fact, where)
        pack.prerequisites.append(
            Prerequisite(
                id=str(row["id"]),
                applies_to=tuple(row["applies_to"]),
                requires_subject=str(row["requires_subject"]),
                at_stage=str(row["at_stage"]),
                depends_on_earlier=row.get("depends_on_earlier"),
                detail=str(row.get("detail", "")),
                fact=fact,
            )
        )

    # -- milestones ------------------------------------------------------
    for row in data.get("milestones", []) or []:
        where = f"{origin}: milestone {row.get('id')!r}"
        mfact = None
        if row.get("fact"):
            mfact = Fact.from_dict(row["fact"])
            _check_source(pack, mfact, where)
        pack.milestones.append(
            Milestone(
                id=str(row["id"]),
                label=str(row["label"]),
                detail=str(row.get("detail", "")),
                year_offset=int(row.get("year_offset", 0)),
                month=int(row["month"]),
                day=int(row["day"]),
                kind=str(row.get("kind", "event")),  # type: ignore[arg-type]
                applies_to=tuple(row.get("applies_to", ())),
                requires_service=bool(row.get("requires_service", False)),
                approximate=bool(row.get("approximate", True)),
                url=row.get("url"),
                fact=mfact,
            )
        )

    # -- reference lists (typeahead + interest taxonomy) -----------------
    pack.subjects = list(data.get("subjects", []) or [])
    pack.interests = list(data.get("interests", []) or [])
    pack.schools = list(data.get("schools", []) or [])
    pack.postal_districts = list(data.get("postal_districts", []) or [])

    _apply_local_overlays(pack, origin)
    _attach_cross_transition_reuse(pack)
    _validate(pack, origin)
    return pack


#: Files under `packs/<id>/local/` that this loader will merge if they exist.
#: The whole directory is gitignored -- see .gitignore and docs/LOCAL_DATA.md.
_LOCAL_DIR = "local"


def _apply_local_overlays(pack: Pack, origin: Path | None) -> None:
    """Merge any local-only data the person running this has supplied.

    PathAhead publishes no Posting Group cut-off points. They are MOE's to
    publish, they are published per school on SchoolFinder, and MOE's Terms
    of Use reserve reproduction -- so the public pack carries none of them
    and the app deep-links to the official page instead. That is the shipped
    behaviour and it is not a gap; see
    tools/build_secondary_schools_pack.py.

    An individual may nonetheless hold their own copy for private study. If
    `packs/<id>/local/cutoff.json` exists, it is merged HERE, at load time,
    into the in-memory pack only. It is deliberately not merged at
    pack-build time, because `secondary-schools.yaml` is a tracked file and
    anything written into it can be committed by accident; a value that only
    ever exists in memory cannot be. `.gitignore` covers the directory as a
    second line of defence, not the only one.

    Silent when absent, because absent is the normal case. Loud when present
    but malformed, because a family relying on a figure deserves to know the
    file it came from was broken rather than get a quietly wrong answer.
    """
    # `origin` is a str for a YAML directory and something else (or absent)
    # for a compiled bundle. Only a real directory can carry an overlay; a
    # compiled JSON pack is a published artifact and must never gain one.
    if not origin:
        return
    origin_dir = Path(str(origin))
    if not origin_dir.is_dir():
        return
    overlay_path = origin_dir / _LOCAL_DIR / "cutoff.json"
    if not overlay_path.exists():
        return

    try:
        rows = json.loads(overlay_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(
            f"{overlay_path}: local cut-off overlay could not be read -- {exc}",
            "Fix or delete the file. PathAhead works without it; it will link "
            "to MOE SchoolFinder instead.",
        ) from exc
    if not isinstance(rows, Mapping):
        raise PackError(
            f"{overlay_path}: expected an object keyed by school id",
            'Format: {"admiralty-secondary-school": {"pg3": [16, 22], ...}, ...}',
        )

    known = {str(s.get("id")) for s in pack.schools}
    unknown = sorted(k for k in rows if k not in known)
    if unknown:
        raise PackError(
            f"{overlay_path}: {len(unknown)} school id(s) are not in this pack: "
            f"{unknown[:5]}",
            "School ids must match the pack exactly. A typo here would silently "
            "drop a school's figures.",
        )

    applied = 0
    for school in pack.schools:
        row = rows.get(str(school.get("id")))
        if not row:
            continue
        school["cutoff_2025"] = {k: row.get(k) for k in ("pg3", "pg2", "pg1", "ip")}
        if row.get("note"):
            school["cutoff_note"] = str(row["note"])
        else:
            # The shipped note explains that PathAhead does not republish
            # these figures. Once a local copy IS present that sentence is no
            # longer true for this school, so it must not stay on the card.
            school.pop("cutoff_note", None)
        school["cutoff_local"] = True
        applied += 1
    pack.local_overlay_applied = applied > 0


def _num(v: Any) -> float | None:
    if v in (None, "", "N.A.", "n.a."):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def _check_source(pack: Pack, fact: Fact, where: str) -> None:
    if fact.source_id not in pack.sources:
        raise PackError(
            f"{where}: cites unknown source {fact.source_id!r}",
            advice="Every fact must point at an id declared in the sources: block.",
        )


#: route_group values whose min-max ELR2B2 band is a genuine O-Level statistic
#: -- see Outcome.also_scored_under. Naming the route_group here, rather than
#: hand-adding `also_scored_under: [...]` to several hundred YAML rows, keeps
#: the one-line-per-fact authoring style the rest of this pack uses: nobody
#: transcribing a polytechnic fee or a course name needs to know this exists.
_POLYTECHNIC_ROUTE_GROUPS = ("polytechnic-diploma",)


def _attach_cross_transition_reuse(pack: Pack) -> None:
    """Tag existing outcomes as also-scoreable under a second transition.

    Runs once, after every outcome is built and before validation, so
    `also_scored_under` is populated the same way whether a pack author wrote
    it by hand (rare) or it was inferred here (the common case, for the
    polytechnics). If the O-Level pack has not been loaded alongside this one,
    the target transition id simply is not in `pack.transitions` and this is a
    silent no-op -- the A-Level-only pack must build and behave exactly as it
    did before this function existed.
    """
    target = "o-level-to-polytechnic-2027"
    if target not in pack.transitions:
        return
    for outcome_id, outcome in list(pack.outcomes.items()):
        if outcome.route_group not in _POLYTECHNIC_ROUTE_GROUPS:
            continue
        if target in outcome.also_scored_under:
            continue
        pack.outcomes[outcome_id] = dataclasses.replace(
            outcome, also_scored_under=(*outcome.also_scored_under, target)
        )


def _validate(pack: Pack, origin: str) -> None:
    """Cross-entity checks that catch the mistakes a pack author actually makes."""
    problems: list[str] = []

    for cr in pack.cohort_rules.values():
        if cr.transition_id not in pack.transitions:
            problems.append(
                f"cohort {cr.year_level!r} points at unknown transition {cr.transition_id!r}"
            )
        if cr.stage_id not in pack.stages:
            problems.append(f"cohort {cr.year_level!r} points at unknown stage {cr.stage_id!r}")

    from .rules import available_kinds  # local import: avoids a cycle

    kinds = set(available_kinds())
    for t in pack.transitions.values():
        if t.rule_kind not in kinds:
            problems.append(
                f"transition {t.id!r} uses rule kind {t.rule_kind!r}, which this engine "
                f"does not implement (known: {', '.join(sorted(kinds))})"
            )
        if t.direction not in ("higher_is_better", "lower_is_better"):
            problems.append(f"transition {t.id!r} has invalid direction {t.direction!r}")

    for o in pack.outcomes.values():
        if not o.band:
            continue
        # The swapped-endpoint check only makes sense for a band published on
        # the same scale the transition scores on. A min-max ELR2B2 range is
        # lower-is-better and sits on an A-Level transition that is
        # higher-is-better, so the endpoints are ordered by the publisher's
        # convention, not ours, and comparing them here would flag every
        # polytechnic course as broken.
        if (
            o.band.statistic == "p10_p90"
            and o.band.comparable
            and o.band.p10_points > o.band.p90_points
        ):
            t = pack.transitions[o.transition_id]
            if t.direction == "higher_is_better":
                problems.append(
                    f"outcome {o.id!r}: 10th-percentile points exceed 90th-percentile "
                    "points on a higher-is-better transition (probably swapped)"
                )
        if o.band.statistic == "min_max" and o.band.p10_points > o.band.p90_points:
            problems.append(
                f"outcome {o.id!r}: a min-max band has its low endpoint above its high "
                "endpoint. Record the lowest admitted aggregate first."
            )
        # A comparable min-max band used to be rejected outright here, because
        # the only min-max bands in the pack were polytechnic ranges shown to
        # A-Level holders -- an A-Level score genuinely cannot be placed on an
        # O-Level aggregate's range, so `comparable` could only be a mistake.
        # That stopped being true once the O-Level stage's own transitions
        # (o-level-to-jc-mi-2027 and friends) score an L1R5/L1R4 aggregate
        # NATIVELY against a min-max JC/MI range: there `comparable: true` is
        # correct, not a slip. What still must never happen is a min-max band
        # being narrated in percentile words -- that is enforced structurally
        # in engine/forward.py, which branches on `band.statistic` before
        # calling `assess_band` (percentile vocabulary) or
        # `assess_min_max_band` (its own HEADLINE_MINMAX/EXPLANATION_MINMAX
        # vocabulary, see engine/buckets.py) and by
        # `test_a_min_max_band_is_never_described_as_a_percentile_band`. So
        # the one thing this check still needs to catch is a `comparable`
        # min-max band on a transition this engine cannot actually score that
        # way -- i.e. one missing from RULE KINDS entirely, which the loop
        # above already rejects on its own. There is nothing left for this
        # block to add; it is kept here, empty of a rule, so the next person
        # reads why before reintroducing the blanket ban.

    if problems:
        raise PackError(
            f"{origin}: pack failed validation\n  - " + "\n  - ".join(problems),
            advice="Fix the data pack; PathAhead will not load a pack it cannot trust.",
        )


def _date(value: Any) -> _dt.date:
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value))


def iter_pack_dirs(root: str | Path) -> Iterable[Path]:
    r = Path(root)
    if not r.exists():
        return []
    return sorted(p for p in r.iterdir() if p.is_dir() and (p / "pack.yaml").exists())

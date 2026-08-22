"""The safeguards, tested as behaviour rather than trusted as intentions.

Every assertion here maps to a numbered rule in SAFEGUARDS.md. A safeguard
that is only written down is a wish; a safeguard with a failing test is a
property of the system.
"""

from __future__ import annotations

import re

from engine import (
    NOT_A_PREDICTION,
    NOT_ADVICE,
    NOT_OFFICIAL,
    Bucket,
    explain_options,
    explain_plan,
    explore,
    plan,
)
from engine.backward import MIN_ROUTES
from engine.buckets import EXPLANATION, HEADLINE
from engine.profile import StudentProfile

# --- SAFEGUARDS 5.3: no verdict language --------------------------------

#: Phrases that must never reach a user. Checked against every piece of copy
#: the engine can emit, not just spot-checked in review.
BANNED = [
    r"\byou will get in\b",
    r"\bmissed the cut ?off\b",
    r"\byou failed\b",
    r"\bunrealistic\b",
    r"\bnot good enough\b",
    r"\bimpossible\b",
    r"\bno chance\b",
    r"\bguarantee[ds]? (?:you )?(?:a place|admission)\b",
    r"\bdon'?t bother\b",
    r"\byou don'?t qualify\b",
]


def _all_copy(pack, result, plans) -> str:
    parts = [
        NOT_A_PREDICTION,
        NOT_ADVICE,
        NOT_OFFICIAL,
        *HEADLINE.values(),
        *EXPLANATION.values(),
        explain_options(result, pack),
        *(explain_plan(p) for p in plans),
        *(r.summary for r in pack.routes),
        *(r.caveat or "" for r in pack.routes),
        *(t.name for t in pack.transitions.values()),
        *(c for t in pack.transitions.values() for c in t.caveats),
    ]
    return "\n".join(parts).lower()


def test_no_banned_phrase_reaches_the_user(pack, strong_grades, modest_grades):
    for grades in (strong_grades, modest_grades):
        result = explore(pack, year_level="jc-2", current_year=2026, grades=grades)
        plans = [plan(pack, oid, comparison_score=result.comparison_score)
                 for oid in ("nus-medicine", "nus-computer-science", "nus-nursing")]
        copy = _all_copy(pack, result, plans)
        for pattern in BANNED:
            assert not re.search(pattern, copy), f"banned phrase matched: {pattern}"


# --- SAFEGUARDS 5.2 / DESIGN_REVIEW Gap 4: never a dead end -------------


def test_backward_mode_never_returns_a_lone_number(pack):
    for outcome_id in pack.outcomes:
        p = plan(pack, outcome_id)
        if p.complete:
            assert len(p.routes) >= MIN_ROUTES, outcome_id
            assert any(r.kind != "direct" for r in p.routes), outcome_id
        else:
            # An incomplete plan must SAY so, in words, not just omit routes.
            assert p.notes, outcome_id
            assert any("counsellor" in n.lower() for n in p.notes), outcome_id


def test_the_hardest_case_still_offers_ways_forward(pack, modest_grades):
    """A modest result asking about the most competitive course in the pack is
    the exact moment this tool could do harm. It must still end constructively."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=modest_grades)
    p = plan(pack, "nus-medicine", comparison_score=result.comparison_score)
    text = explain_plan(p)
    assert len(p.routes) >= MIN_ROUTES
    assert "another way" in text or "second chance" in text
    assert "counsellor" in text.lower() or "admissions office" in text.lower()


# --- SAFEGUARDS 5.1: never rank by selectivity ---------------------------


def test_results_are_never_ordered_by_selectivity(pack, strong_grades):
    """Without fit scores the order is alphabetical -- never a ranking by how
    hard a course is to get into."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    for _bucket, items in result.by_bucket().items():
        if len(items) < 2:
            continue
        keys = [(i.outcome.institution_short, i.outcome.name) for i in items]
        assert keys == sorted(keys), "ordering must be alphabetical, never by competitiveness"


def test_ordering_by_fit_is_allowed_and_is_not_ordering_by_pay(pack, strong_grades):
    """Fit is the student's own stated preference, so it may order the list.
    Salary must never correlate with the ordering it produces."""
    from engine.fit import score_all

    profile = StudentProfile(
        interests=("S", "I"), enjoyed_subjects=("biology", "chemistry"),
        assessment_style="practical", teamwork="team",
    )
    fits = score_all(pack, profile, "a-level-to-university-2026")
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    for _bucket, items in result.by_bucket(fits).items():
        scores = [
            fits[i.outcome.id].score for i in items
            if fits.get(i.outcome.id) and fits[i.outcome.id].score is not None
        ]
        assert scores == sorted(scores, reverse=True), "fit ordering is not descending"
        salaries = [
            i.outcome.employment.gross_median for i in items
            if i.outcome.employment and i.outcome.employment.has_salary
        ]
        if len(salaries) > 2:
            assert salaries != sorted(salaries, reverse=True), (
                "the list came out ordered by pay, which must never be a sort key"
            )


def test_below_range_is_a_named_bucket_not_a_score(pack, modest_grades):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=modest_grades)
    for r in result.results:
        assert r.assessment.bucket in set(Bucket)
        assert r.assessment.headline
        assert r.assessment.explanation
        # No percentage, probability or odds anywhere in the verdict.
        assert "%" not in r.assessment.headline
        assert "chance" not in r.assessment.explanation.lower()


# --- SAFEGUARDS 5.5: holistic factors are never dropped ------------------


def test_extra_assessment_is_always_surfaced(pack, strong_grades):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    for r in result.results:
        if r.outcome.has_extra_assessment:
            assert r.extra_assessment, r.outcome.id
            assert any("interview" in e.lower() or "assessment" in e.lower()
                       for e in r.extra_assessment)


def test_courses_with_interviews_are_flagged_in_the_options_text(pack, strong_grades):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    text = explain_options(result, pack)
    assert "interview, test or portfolio" in text


# --- SAFEGUARDS 2: the tool collects nothing -----------------------------


#: Fields that identify a person. Course names and institution names are of
#: course present -- what must never appear is anything about the *student*.
IDENTIFYING = (
    "nric",
    "email",
    "phone",
    "mobile",
    "address",
    "postal_code",
    "student_name",
    "student_id",
    "full_name",
    "dob",
    "date_of_birth",
    "ip",
    "user_id",
    "session_id",
)


def test_no_engine_output_has_a_field_for_identity(pack, strong_grades):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    payload = result.to_dict()

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                key = k.lower()
                assert key not in IDENTIFYING, f"identifying field {path}.{k}"
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(payload)


def test_grade_sheet_carries_no_student_identity(strong_grades):
    d = strong_grades.to_dict()
    assert set(d) == {"stage", "subjects"}
    for s in d["subjects"]:
        assert set(s) == {"code", "name", "level", "grade"}


# --- SAFEGUARDS 4b: not-a-prediction travels with every band -------------


def test_every_banded_result_carries_a_year_and_a_citation(pack, strong_grades):
    """Anything derived from a published figure must arrive with the year it
    was published and a link to where it came from.

    Two published shapes now exist -- a 10th-90th percentile band, and a banded
    profile giving the share of applicants in each band who got through. Both
    must cite. A course with neither must say it has neither, and the only
    bucket permitted without a citation is DATA_INCOMPLETE.
    """
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    for r in result.results:
        a_level_evidence = r.outcome.band is not None or any(
            p.qualification == "a-level" for p in r.outcome.banded
        )
        if not a_level_evidence:
            # SIT publishes its A-Level figures per cluster, not per course, so
            # there is genuinely nothing to place this student against.
            assert r.assessment.bucket is Bucket.DATA_INCOMPLETE, r.outcome.id
            assert r.citation is None, r.outcome.id
            continue
        assert r.citation is not None, r.outcome.id
        assert r.citation["url"].startswith("http")
        assert r.citation["as_of_year"]
        if r.outcome.band is not None:
            assert r.assessment.band_year == r.outcome.band.fact.as_of_year
        else:
            years = {p.fact.as_of_year for p in r.outcome.banded}
            assert r.assessment.band_year in years, r.outcome.id


def test_no_bare_number_is_ever_surfaced(pack):
    """Every Fact in the pack must carry year, source and confidence."""
    for path, fact in pack.all_facts():
        assert fact.as_of_year, path
        assert fact.source_id in pack.sources, path
        assert fact.confidence in ("high", "medium", "low"), path


def test_sources_declare_a_licence_so_obligations_travel_with_the_data(pack):
    from engine.model import KNOWN_LICENCES

    for src in pack.sources.values():
        assert src.licence in KNOWN_LICENCES, f"{src.id} has an unrecognised licence"
        assert src.url.startswith("http")
        assert src.retrieved


# --- SAFEGUARDS 4a: no implied official status ---------------------------


def test_disclaimers_name_the_bodies_they_disclaim(pack):
    for body in ("Ministry of Education", "SEAB", "university"):
        assert body.lower() in NOT_OFFICIAL.lower()


def test_pack_attribution_disclaims_endorsement(pack):
    joined = " ".join(pack.attribution).lower()
    assert "not affiliated" in joined
    assert "endorsed" in joined

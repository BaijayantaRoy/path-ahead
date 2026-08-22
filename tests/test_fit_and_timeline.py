"""Fit scoring, the coverage gate, and the timeline.

The rule this file exists to defend: **fit is scored, evidence is not.** Fit
is computed from what the student typed, so every point is traceable and
scoring it is honest. Evidence is a published fact about an admissions
outcome, so scoring it would be predicting a committee's decision.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from engine import explore, milestones
from engine import fit as fit_module
from engine.cohort import resolve
from engine.fit import MIN_SIGNALS, coverage, explain_fit, score_all, score_outcome
from engine.profile import INTERESTS, StudentProfile, reflect_goal

TODAY = _dt.date(2026, 8, 2)


@pytest.fixture
def techie():
    return StudentProfile(
        interests=("I", "R"),
        enjoyed_subjects=("mathematics", "computing"),
        assessment_style="coursework",
        teamwork="individual",
        priorities=("earnings", "stability"),
        willing_extra_assessment=False,
        cost_sensitive=True,
        goal_text="build things people actually use",
    )


@pytest.fixture
def carer():
    return StudentProfile(
        interests=("S",),
        enjoyed_subjects=("biology", "chemistry"),
        assessment_style="practical",
        teamwork="team",
        willing_extra_assessment=True,
    )


# --- the hard rules -------------------------------------------------------


def test_an_empty_profile_gets_no_score_rather_than_a_misleading_fifty(pack):
    scores = score_all(pack, StudentProfile(), "a-level-to-university-2026")
    assert scores, "outcomes should still be listed"
    assert all(s.score is None for s in scores.values())
    # The rule this test protects is "no score", not one particular sentence.
    # Once eligibility began running ahead of the signal count, a course with a
    # published subject prerequisite started giving the more useful answer --
    # naming the subject NTU requires, rather than telling a student who has
    # answered nothing that they have answered nothing. Both are refusals to
    # score; pinning the wording would have forced the worse one.
    for s in scores.values():
        reason = s.unscored_reason or ""
        assert reason, "a course with no score must say why"
        assert ("at least two" in reason
                or "has not been told" in reason
                or "not among the subjects" in reason), reason


def test_one_answer_is_not_enough(pack):
    thin = StudentProfile(interests=("I",))
    assert thin.signal_count < MIN_SIGNALS
    assert score_outcome(pack.outcomes["nus-computer-science"], thin).score is None


def test_the_preview_label_tracks_coverage_in_both_directions(pack, techie, monkeypatch):
    """PREVIEW must follow the pool, not a hand-set flag.

    This test used to assert that the pool WAS partial, which was true while
    institutions were still being loaded and stopped being true the moment
    Singapore Polytechnic went in -- the eleventh and last. An assertion that
    the work is unfinished cannot survive the work being finished, so what is
    pinned here now is the mechanism that made the label trustworthy: complete
    coverage clears PREVIEW, and any gap restores it and names what is missing.

    The incomplete half is simulated by adding an institution to the gate that
    the pack cannot contain, rather than by deleting real courses. It exercises
    exactly the code path a real gap would.
    """
    cov = coverage(pack)
    assert cov.complete, (
        f"every institution in REQUIRED_COVERAGE is loaded, so fit should no "
        f"longer be in preview; missing={cov.missing}"
    )
    assert not cov.missing
    assert not cov.warning, "a complete pool must not carry a coverage warning"
    scores = score_all(pack, techie, "a-level-to-university-2026")
    assert scores, "no outcomes scored"
    assert not any(s.preview for s in scores.values()), (
        "coverage is complete but scores are still flagged preview"
    )

    # Now open a hole in the gate and confirm the label comes straight back.
    monkeypatch.setattr(
        fit_module, "REQUIRED_COVERAGE", fit_module.REQUIRED_COVERAGE | {"NEW-INSTITUTION"}
    )
    gapped = coverage(pack)
    assert not gapped.complete, "a gap in coverage must not read as complete"
    assert "NEW-INSTITUTION" in gapped.missing, "a partial pool must name what it is missing"
    assert "preview" in gapped.warning.lower()
    assert all(
        s.preview for s in score_all(pack, techie, "a-level-to-university-2026").values()
    ), "coverage is incomplete but scores are not flagged preview"


def test_the_coverage_warning_never_uses_the_word_best(pack):
    """Ranking a partial pool must never be presented as a shortlist."""
    assert "best" not in (coverage(pack).warning or "").lower()


def test_evidence_is_never_expressed_as_a_fit_style_score(pack, techie):
    """The two axes must stay separate: no blended 'match' number anywhere."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_grades())
    for r in result.results:
        d = r.assessment.to_dict()
        assert "score" not in d
        assert "%" not in (d["headline"] or "")


# --- the arithmetic -------------------------------------------------------


def _grades():
    from engine import GradeSheet

    return GradeSheet.parse(
        "a-level",
        ["h2 Mathematics=A", "h2 Computing=A", "h2 Physics=B", "gp General Paper=A"],
    )


def test_fit_is_deterministic(pack, techie):
    a = score_outcome(pack.outcomes["nus-computer-science"], techie)
    b = score_outcome(pack.outcomes["nus-computer-science"], techie)
    assert a.score == b.score
    assert [f.to_dict() for f in a.factors] == [f.to_dict() for f in b.factors]


def test_every_point_is_traceable_to_something_the_student_said(pack, techie):
    fit = score_outcome(pack.outcomes["nus-computer-science"], techie)
    assert fit.factors
    for f in fit.factors:
        assert f.reason, f.label
        assert f.source in StudentProfile.SIGNALS, f.source
        assert 0 <= f.points <= f.max_points


def test_score_equals_the_sum_of_its_factors(pack, techie):
    fit = score_outcome(pack.outcomes["nus-computer-science"], techie)
    earned = sum(f.points for f in fit.factors)
    possible = sum(f.max_points for f in fit.factors)
    from engine.fit import _r0
    assert fit.score == _r0(100 * earned / possible)


def test_different_students_get_different_answers(pack, techie, carer):
    cs = pack.outcomes["nus-computer-science"]
    nursing = pack.outcomes["nus-nursing"]
    assert score_outcome(cs, techie).score > score_outcome(nursing, techie).score
    assert score_outcome(nursing, carer).score > score_outcome(cs, carer).score


def test_reasons_are_ordered_strongest_first(pack, techie):
    fit = score_outcome(pack.outcomes["nus-computer-science"], techie)
    ratios = [f.points / f.max_points for f in fit.factors]
    assert ratios == sorted(ratios, reverse=True)


def test_a_negative_signal_is_stated_not_hidden(pack):
    """Someone who wants to avoid interviews must be told a course needs one.

    The intent is unchanged; the mechanism is not. "Happy to sit interviews"
    used to be a yes/no toggle AND an importance row — the same question twice
    on one page — so the toggle went and the weight is now the whole signal.
    A student who gives it any weight must still see the factor, scored zero,
    saying plainly that this course requires one.
    """
    p = StudentProfile(
        interests=("I",), enjoyed_subjects=("biology",),
        importance=(("extra", 3), ("interests", 1)),
    )
    fit = score_outcome(pack.outcomes["nus-medicine"], p)
    extra = [f for f in fit.factors if f.dimension == "extra"]
    assert extra, "a weighted dimension vanished instead of scoring zero"
    assert extra[0].points == 0
    assert "requires an interview" in extra[0].reason
    # And it must read as a difference between two things, not a deficit.
    assert "you" in extra[0].reason.lower()


# --- earnings is opt-in, never a default ----------------------------------


def test_salary_only_enters_fit_when_the_student_says_it_matters(pack):
    base = StudentProfile(interests=("I",), enjoyed_subjects=("mathematics",))
    with_money = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",), priorities=("earnings",)
    )
    cs = pack.outcomes["nus-computer-science"]
    assert not any(f.source == "priorities" for f in score_outcome(cs, base).factors)
    money = [f for f in score_outcome(cs, with_money).factors if f.source == "priorities"]
    assert money and "financial security matters" in money[0].reason


def test_results_are_never_ordered_by_salary(pack, techie):
    """Default ordering is alphabetical; pay is never a sort key."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_grades())
    for _bucket, items in result.by_bucket().items():
        keys = [(i.outcome.institution_short, i.outcome.name) for i in items]
        assert keys == sorted(keys)


# --- editorial data is labelled as opinion --------------------------------


def test_course_descriptions_declare_themselves_editorial(pack):
    for o in pack.outcomes.values():
        if o.editorial and o.editorial.fact:
            assert o.editorial.fact.is_editorial, o.id
            assert o.editorial.fact.source_id == "pathahead-editorial"


def test_editorial_facts_are_excluded_from_the_official_confidence_floor(pack):
    official = dict(pack.official_facts())
    assert official, "there must still be official facts"
    assert all(not f.is_editorial for f in official.values())
    assert len(official) < len(dict(pack.all_facts()))


def test_fit_explanation_says_the_descriptions_are_ours(pack, techie):
    text = explain_fit(
        score_outcome(pack.outcomes["nus-computer-science"], techie),
        pack.outcomes["nus-computer-science"],
    )
    assert "PathAhead's own characterisation" in text
    assert "tell us" in text


# --- employment data ------------------------------------------------------


def test_salary_is_always_a_range_never_a_bare_median(pack):
    for o in pack.outcomes.values():
        e = o.employment
        if e and e.has_salary:
            assert e.gross_p25 is not None and e.gross_p75 is not None, o.id
            assert e.gross_p25 <= e.gross_median <= e.gross_p75, o.id


def test_missing_salary_explains_itself_rather_than_showing_nothing(pack):
    medicine = pack.outcomes["nus-medicine"].employment
    assert not medicine.has_salary
    assert "training" in medicine.unavailable_reason


def test_employment_data_is_licensed_and_attributed(pack):
    src = pack.source("ges-datagov")
    assert src.licence == "sg-odl-1.0"
    assert src.redistributable
    joined = " ".join(pack.attribution).lower()
    assert "open data licence" in joined


# --- the goal field is honest about doing nothing -------------------------


def test_free_text_goal_is_reflected_back_not_interpreted(pack):
    p = StudentProfile(goal_text="something outdoors, not stuck at a desk")
    lines = reflect_goal(p, [])
    assert any("not tried to interpret" in x for x in lines)
    assert any("outdoors" in x for x in lines)


def test_no_goal_means_no_noise():
    assert reflect_goal(StudentProfile(), []) == []


# --- timeline -------------------------------------------------------------


def test_timeline_is_ordered_and_dated_from_the_cohort(pack):
    cohort = resolve(pack, "jc-2", 2026)
    tl = milestones.build(pack, cohort, today=TODAY)
    assert tl.entries
    dates = [e.date for e in tl.entries]
    assert dates == sorted(dates)
    assert all(e.date.year >= 2026 for e in tl.entries)


def test_every_milestone_says_it_is_approximate_and_links_out(pack):
    cohort = resolve(pack, "jc-2", 2026)
    tl = milestones.build(pack, cohort, today=TODAY)
    assert all(e.approximate for e in tl.entries)
    assert any("official page" in n for n in tl.notes)


def test_national_service_shifts_the_start_and_says_so(pack):
    cohort = resolve(pack, "jc-2", 2026)
    without = milestones.build(pack, cohort, national_service=False, today=TODAY)
    with_ns = milestones.build(pack, cohort, national_service=True, today=TODAY)
    assert with_ns.starts_year == without.starts_year + milestones.NS_YEARS
    assert any("National Service" in n for n in with_ns.notes)
    assert any("not a setback" in n for n in with_ns.notes)
    assert len(with_ns.entries) > len(without.entries)


def test_ns_warns_that_salary_figures_will_have_moved(pack):
    cohort = resolve(pack, "jc-2", 2026)
    tl = milestones.build(pack, cohort, national_service=True, today=TODAY)
    assert any("graduated years before you" in n for n in tl.notes)


def test_the_application_deadline_is_present_and_flagged(pack):
    cohort = resolve(pack, "jc-2", 2026)
    tl = milestones.build(pack, cohort, today=TODAY)
    closes = [e for e in tl.entries if e.milestone_id == "university-application-closes"]
    assert closes, "the deadline families miss must be in the timeline"
    assert "differ between universities" in closes[0].detail


def test_no_invented_dates_survive_the_health_floor(pack):
    """An earlier draft carried a guessed appeal-window date. The gate rejected
    it, and it was removed rather than downgraded. This pins that decision."""
    assert not any(m.id == "appeal-window" for m in pack.milestones)
    for m in pack.milestones:
        if m.fact:
            assert m.fact.confidence in ("high", "medium"), m.id


def test_timeline_exports_a_calendar_file(pack):
    cohort = resolve(pack, "jc-2", 2026)
    ics = milestones.build(pack, cohort, today=TODAY).as_ics()
    assert ics.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in ics
    assert "approximate" in ics


def test_timeline_renders_as_text(pack):
    cohort = resolve(pack, "jc-2", 2026)
    text = milestones.build(pack, cohort, today=TODAY).as_text()
    assert "What happens next" in text
    assert "official page" in text


# --- flexibility ----------------------------------------------------------


def test_the_broad_entry_programme_is_marked_as_keeping_options_open(pack):
    chs = pack.outcomes["nus-humanities-sciences"].flexibility
    assert chs.declares_major_later and chs.common_first_year
    assert chs.score >= 2


def test_professional_programmes_are_honest_about_being_harder_to_leave(pack):
    med = pack.outcomes["nus-medicine"].flexibility
    assert not med.declares_major_later
    assert "transfer" in med.switching_note.lower()


# --- interest taxonomy ----------------------------------------------------


def test_the_interest_taxonomy_matches_the_pack(pack):
    codes = {i["code"] for i in pack.interests}
    assert codes == set(INTERESTS)


def test_subjects_list_supports_how_people_actually_type(pack):
    by_code = {s["code"]: s for s in pack.subjects}
    assert "econs" in by_code["economics"]["aka"]
    assert "chem" in by_code["chemistry"]["aka"]
    assert any("further maths" in s.get("aka", []) for s in pack.subjects)

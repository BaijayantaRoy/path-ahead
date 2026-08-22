"""Polytechnic diplomas: a third published shape, and the ways it could lie.

The pack already held two shapes of published evidence -- a 10th-90th percentile
grade profile (NUS, NTU, SMU) and a banded share-of-applicants profile (SIT,
SUSS). The polytechnics are a third: the net ELR2B2 aggregate of the lowest and
highest ranked student admitted through the Joint Admissions Exercise.

It looks exactly like the first one. Two numbers, a low and a high. That
resemblance is the whole danger, and every test in this file is about a specific
way the resemblance could produce a confident wrong answer:

  1. A min-max is the WHOLE admitted cohort; a p10-p90 cuts both tails off by
     construction. From the same intake the min-max is necessarily wider, so
     rendering them in the same words makes polytechnics look far less selective
     than they are. NYP Nursing spans 3 to 28 -- nearly the entire scale --
     because one admitted student sat at 28.

  2. The number is an O-Level aggregate, on a scale of 4 to 26 where LOWER is
     better. The transition it appears in scores an A-Level result out of 70
     where higher is better. Comparing them would produce a verdict that looked
     completely ordinary and was meaningless -- the same failure family as the
     retired-UAS bug in NEXT.md section 2, and as ISSUES_v0.2.md section A.

  3. Deeper than units: no route admits an A-Level holder on that number at all.
     Through JAE they are admitted on their O-Level results; through the Direct
     Admissions Exercise there is no published aggregate. So there is no version
     of this comparison that becomes valid with better arithmetic.

  4. Three years of data must stay three exercises. Merging them into one range
     would invent a figure nobody published, and it would widen every year --
     so a course would look less selective the longer PathAhead had been running.
"""

from __future__ import annotations

import pytest

from engine.buckets import (
    STATISTIC_WORDS,
    Bucket,
    assess_band,
    assess_published_on_another_basis,
)
from engine.fit import REQUIRED_COVERAGE, coverage
from engine.forward import explore
from engine.grades import GradeSheet

POLYTECHNICS = {"NYP", "NP", "SP", "TP", "RP"}


def _polytechnic_outcomes(pack):
    return [o for o in pack.outcomes.values() if o.institution_short in POLYTECHNICS]


def _banded_polytechnic_outcomes(pack):
    """Polytechnic courses whose publisher actually prints an aggregate range.

    Not all of them do. Singapore Polytechnic's Diploma in Nautical Studies
    publishes entry requirements but no net ELR2B2 range and no JAE course code,
    so it carries no band -- the same shape SUTD's five courses have. The tests
    about what a band must SAY apply to the courses that have one; the test
    below about courses that do not is what stops a band-less course being
    quietly dropped, or quietly given a made-up range.
    """
    return [o for o in _polytechnic_outcomes(pack) if o.band is not None]


def test_a_polytechnic_course_without_a_published_range_carries_no_band(pack):
    """The absence must survive as an absence.

    Two ways this could rot. A later session could delete the course, because a
    course with no number looks broken -- and then a real SP diploma silently
    stops existing in a tool families use to decide what to apply for. Or it
    could be given a range borrowed from a sibling course, a school average, or
    an aggregator, any of which would look entirely ordinary on the card.
    Neither is allowed: the course is present, and its band is None.
    """
    bandless = [o for o in _polytechnic_outcomes(pack) if o.band is None]
    assert bandless, (
        "no band-less polytechnic course found. If SP started publishing a "
        "range for Nautical Studies, load it and delete this test. If the "
        "course was dropped instead, put it back -- it is a real diploma."
    )
    for o in bandless:
        assert o.band is None
        assert not o.banded, (
            f"{o.id}: a banded profile appeared where no range is published"
        )
        assert o.editorial is not None, (
            f"{o.id}: no editorial data, so the course cannot be reasoned about "
            f"at all and would be dead weight on the page"
        )


def _top_grades() -> GradeSheet:
    """The strongest A-Level result there is.

    Deliberately the maximum: if any comparison against an O-Level aggregate
    were going to slip through, this is the profile that would sail past every
    polytechnic range and report a clean sweep of "above the range".
    """
    return GradeSheet.parse(
        "a-level",
        [
            "h2 Mathematics=A",
            "h2 Physics=A",
            "h2 Chemistry=A",
            "gp General Paper=A",
        ],
    )


# -- 1. the statistic must never borrow the other one's words ----------------

def test_a_min_max_band_is_never_described_as_a_percentile_band():
    """The copy is chosen from `statistic`, and the two vocabularies differ.

    If a later change makes these strings equal, the distinction has been
    quietly lost even though every other test still passes.
    """
    percentile = STATISTIC_WORDS["p10_p90"]
    full_range = STATISTIC_WORDS["min_max"]
    assert percentile["what_it_is"] != full_range["what_it_is"]
    assert "middle 80%" in percentile["what_it_is"]
    assert "whole cohort" in full_range["what_it_is"]
    # The min-max copy must say WHY it is wider, or a reader will draw the
    # obvious and wrong conclusion from the width alone.
    assert "wider" in full_range["what_it_is"]


def test_assess_band_refuses_a_min_max_rather_than_mislabelling_it():
    """Failing loudly beats emitting percentile copy over a full range."""
    with pytest.raises(ValueError, match="min_max"):
        assess_band(
            60.0, 3.0, 28.0,
            direction="higher_is_better",
            band_year=2026,
            basis="net ELR2B2 O-Level aggregate, where lower is better",
            confidence="high",
            statistic="min_max",
        )


# -- 2 and 3. an A-Level score is never placed against an ELR2B2 aggregate ---

def test_every_polytechnic_band_declines_the_comparison(pack):
    outcomes = _banded_polytechnic_outcomes(pack)
    assert outcomes, "no polytechnic outcomes loaded; this file is testing nothing"
    for o in outcomes:
        assert o.band.statistic == "min_max", f"{o.id}: wrong statistic"
        assert o.band.scale == "elr2b2_olevel", f"{o.id}: wrong scale"
        assert not o.band.comparable, (
            f"{o.id}: marked comparable. An O-Level aggregate out of 26 where "
            f"lower is better is not an A-Level score out of 70 where higher is."
        )


def test_a_top_student_gets_no_verdict_on_a_polytechnic_course(pack):
    """The strongest possible A-Level result must not clear an O-Level range.

    A student with AAA/A has a comparison score of 60. Every polytechnic range
    tops out at 28. On a naive higher-is-better comparison all of them would
    read "Above last year's range" -- a clean sweep of confident nonsense.
    """
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_top_grades())
    poly = [r for r in result.results if r.outcome.institution_short in POLYTECHNICS]
    assert poly, "no polytechnic results returned"
    for r in poly:
        if r.outcome.band is None:
            # No published range, so there is nothing to decline to compare.
            # The one thing that must never happen is a verdict appearing from
            # nowhere -- least of all a flattering one.
            assert r.assessment.bucket is Bucket.DATA_INCOMPLETE, (
                f"{r.outcome.id}: has no published range but got "
                f"{r.assessment.bucket.value}"
            )
            continue
        assert r.assessment.bucket is Bucket.PUBLISHED_ON_ANOTHER_BASIS, (
            f"{r.outcome.id}: got {r.assessment.bucket.value}, which is a verdict"
        )
        assert r.assessment.bucket is not Bucket.ABOVE_RANGE


def test_the_polytechnic_comparison_line_never_puts_the_two_numbers_together(pack):
    """"Your 60 against 3-28" is the exact sentence this must not produce."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_top_grades())
    score = result.comparison_score
    for r in result.results:
        if r.outcome.institution_short not in POLYTECHNICS or r.outcome.band is None:
            continue
        line = (r.assessment.comparison or "").lower()
        assert "you " not in line, f"{r.outcome.id}: comparison line addresses the student's score"
        assert f"{score:g}" not in line or "not compared" in line
        assert "not compared" in line, f"{r.outcome.id}: does not say the figure is not compared"


def test_the_range_is_still_shown_rather_than_hidden(pack):
    """Refusing the comparison is not the same as withholding the data.

    A family reading this card should still learn what the course actually
    admitted. DATA_INCOMPLETE would be the wrong bucket: we are not missing
    anything.
    """
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_top_grades())
    for r in result.results:
        if r.outcome.institution_short not in POLYTECHNICS or r.outcome.band is None:
            continue
        band = r.outcome.band
        line = r.assessment.comparison or ""
        assert f"{band.p10_points:g}" in line and f"{band.p90_points:g}" in line, (
            f"{r.outcome.id}: the published range is not on the card"
        )
        assert r.assessment.bucket is not Bucket.DATA_INCOMPLETE


def test_an_incomparable_band_is_shown_even_without_a_comparable_score(pack):
    """The range does not depend on the student having a score.

    It is the same published number either way, and it is not being compared
    with anything -- so a student whose subjects produce no A-Level score should
    still see it rather than a "not enough data" card that blames them.
    """
    outcome = next(o for o in _banded_polytechnic_outcomes(pack))
    a = assess_published_on_another_basis(
        outcome.band,
        band_year=outcome.band.fact.as_of_year,
        confidence=outcome.band.fact.confidence,
    )
    assert a.bucket is Bucket.PUBLISHED_ON_ANOTHER_BASIS
    assert a.explanation


# -- 4. years stay separate --------------------------------------------------

def test_history_is_carried_beside_the_band_and_never_merged(pack):
    """Each year is one exercise.

    A merged three-year min-max would be a number no institution published, and
    it would grow monotonically with every year added.
    """
    with_history = [o for o in _banded_polytechnic_outcomes(pack) if o.band.history]
    assert with_history, "no polytechnic course carries an earlier year"
    for o in with_history:
        band = o.band
        assert band.years_covered == 1 + len(band.history)
        for h in band.history:
            assert h.year != band.fact.as_of_year, f"{o.id}: duplicate year in history"
            assert h.year < band.fact.as_of_year, f"{o.id}: history is not earlier"
        # The band's endpoints must be the LATEST year's published pair --
        # exactly what `fact.value` records verbatim from the source. If a
        # future change starts merging years, this is the assertion that breaks.
        assert f"{band.p10_points:g} to {band.p90_points:g}" == band.fact.value

    # And at least one course must actually prove the merge is not happening:
    # somewhere in the pack an earlier year has to sit outside the current band,
    # so a union would be visibly wider than what is published.
    assert any(
        any(h.low < o.band.p10_points or h.high > o.band.p90_points for h in o.band.history)
        for o in with_history
    ), "no course has an earlier year outside its current range; the test proves nothing"


def test_the_year_count_is_visible_rather_than_implied(pack):
    """A one-year figure and a three-year one must not render identically."""
    outcomes = _banded_polytechnic_outcomes(pack)
    counts = {o.band.years_covered for o in outcomes}
    for o in outcomes:
        assert o.band.years_label, f"{o.id}: no year label"
        assert str(o.band.fact.as_of_year) in o.band.years_label
    if len(counts) > 1:
        multi = next(o for o in outcomes if o.band.years_covered > 1)
        single = next(o for o in outcomes if o.band.years_covered == 1)
        assert multi.band.years_label != single.band.years_label


# -- the coverage gate -------------------------------------------------------

def test_one_polytechnic_does_not_lift_the_preview_label(pack):
    """The decision, written down as a test.

    REQUIRED_COVERAGE names all five polytechnics individually. A family flag
    that any single polytechnic satisfied would have lifted PREVIEW while four
    institutions were still missing, and fit would then have ranked a student
    against a partial pool while presenting itself as complete.
    """
    assert POLYTECHNICS <= REQUIRED_COVERAGE, (
        "the gate must name every polytechnic, not a family string"
    )
    assert "Polytechnic" not in REQUIRED_COVERAGE, (
        "a family string no institution is named cannot be satisfied or reasoned about"
    )
    cov = coverage(pack)
    present = POLYTECHNICS & set(cov.institutions)
    if present and present != POLYTECHNICS:
        assert not cov.complete, (
            f"loaded {sorted(present)} but the gate reads complete with "
            f"{sorted(POLYTECHNICS - present)} missing"
        )


# -- the route, which is the part a family acts on ---------------------------

def test_a_polytechnic_diploma_offers_a_route_an_a_level_holder_can_use(pack):
    """JAE is not the A-Level holder's route, and the pack must say so.

    Temasek Polytechnic's own guide: through JAE an A-Level holder is admitted
    on their GCE O-Level results; through the Direct Admissions Exercise they
    enter a shortened 2 or 2.5-year diploma, assessed on academic results and
    interview. A card that showed only the JAE range would be pointing a JC
    student at a door that is not theirs.
    """
    routes = [r for r in pack.routes if "polytechnic-diploma" in r.applies_to]
    assert len(routes) >= 3, "backward mode refuses to answer with fewer than three routes"
    assert any(r.kind != "direct" for r in routes), "every route is the direct one"
    dae = next((r for r in routes if "direct admissions" in r.label.lower()), None)
    assert dae is not None, "no Direct Admissions Exercise route for A-Level holders"
    assert "2" in dae.typical_duration, "the shortened duration is the point of this route"


def test_polytechnic_courses_sit_in_the_same_list_as_degrees(pack):
    """A deliberate decision: diplomas are a destination, not a consolation.

    Showing them only after a student "misses" a university range would teach
    exactly the ranking this project refuses to teach.
    """
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_top_grades())
    shorts = {r.outcome.institution_short for r in result.results}
    assert POLYTECHNICS & shorts, "polytechnics are absent from a top student's list"
    assert {"NUS", "NTU"} & shorts, "universities are absent"


# ---------------------------------------------------------------------------
# Fees, loaded 2026-08-05.
#
# Four of the five polytechnics publish AY2026 tuition, and all four figures
# are identical: 3,100 / 6,400 / 12,400 / 13,600. Identical numbers from four
# separate publishers are the most inviting thing in this pack to "tidy up" —
# by copying them onto the fifth, or by folding them into one shared constant.
# These tests exist to make either move fail loudly.
# ---------------------------------------------------------------------------
PRICED_POLYTECHNICS = {"NYP", "SP", "TP", "RP"}
FEE_SOURCES = {"NYP": "nyp-fees", "SP": "sp-fees", "TP": "tp-fees", "RP": "rp-fees"}


def test_a_polytechnic_fee_is_the_tuition_figure_not_the_total_payable(pack):
    """Every polytechnic prints two numbers a row apart: subsidised tuition, and
    the larger "fees payable" that adds the supplementary charge. The
    universities in this pack hold tuition, so mixing the two would put SP's
    3,177.52 beside NUS's 8,250 as though they were the same measurement.

    The supplementary fee is not dropped — it is named in the note, because a
    family is billed it — but it is not folded into the headline number.
    """
    checked = 0
    for o in _polytechnic_outcomes(pack):
        if o.institution_short not in PRICED_POLYTECHNICS:
            continue
        c = o.cost
        assert c and c.annual_fee_citizen, f"{o.id}: priced polytechnic lost its fee"
        checked += 1
        assert (c.annual_fee_citizen, c.annual_fee_pr) == (3100, 6400), o.id
        assert (c.annual_fee_international, c.annual_fee_is_other) == (12400, 13600), o.id
        assert c.years == 3, f"{o.id}: a full-time diploma is three years"
        # The supplementary fee survives, in words, on the course.
        assert "supplementary fee" in (c.fact.note or ""), (
            f"{o.id}: the supplementary fee a family is actually billed is missing"
        )
    assert checked >= 150, f"only {checked} polytechnic courses carry a fee"


def test_each_polytechnic_fee_cites_the_polytechnic_that_will_bill_you(pack):
    """Four publications that agree are still four publications.

    If a later session ever collapses these into one shared source id, this
    fails — and it should, because a figure has to be traceable to the
    institution that will send the invoice, not to the one whose page was
    easiest to fetch.
    """
    for o in _polytechnic_outcomes(pack):
        short = o.institution_short
        if short not in PRICED_POLYTECHNICS:
            continue
        assert o.cost.fact.source_id == FEE_SOURCES[short], (
            f"{o.id}: fee cites {o.cost.fact.source_id}, not {short}'s own fee page"
        )


def test_ngee_ann_shows_no_fee_rather_than_its_neighbours_fee(pack):
    """NP's fee page could not be retrieved on 2026-08-05. Its 41 courses carry
    a note saying so and pointing at the page.

    The temptation this pins down is specific and strong: the other four agree
    exactly, MOE plausibly sets the rate centrally, and filling NP in would
    flip 41 courses from "no fee" to priced with no visible cost. But the
    supplementary fee differs at all four polytechnics, which proves these are
    four separate publications rather than one figure republished — so the
    agreement is evidence about a process, not a number Ngee Ann published.
    """
    np_courses = [o for o in _polytechnic_outcomes(pack) if o.institution_short == "NP"]
    assert np_courses, "Ngee Ann has vanished from the pack"
    for o in np_courses:
        assert not (o.cost and o.cost.has_any_fee), (
            f"{o.id}: carries a fee Ngee Ann did not publish here"
        )
        assert o.fee_note, f"{o.id}: an absent fee with no reason reads as a to-do"
        assert "np.edu.sg" in o.fee_note, (
            f"{o.id}: the note does not say where the real number is"
        )


def test_no_polytechnic_invents_the_fee_for_a_student_without_the_grant(pack):
    """Each polytechnic says a student who declines the tuition grant pays full
    fees, and none of the four prints that figure. Same decision as NTU's
    lab/non-lab split: an unpublished number is not computed here.
    """
    for o in _polytechnic_outcomes(pack):
        if o.cost:
            assert not o.cost.annual_fee_no_grant, (
                f"{o.id}: recorded a non-subsidised fee no polytechnic publishes"
            )


def test_no_polytechnic_card_reads_as_a_judgement(pack):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=_top_grades())
    banned = ["weak", "poor", "unsuitable", "not good enough", "fall back", "settle for",
              "less competitive", "easier"]
    for r in result.results:
        if r.outcome.institution_short not in POLYTECHNICS:
            continue
        text = " ".join(
            filter(None, [r.assessment.headline, r.assessment.explanation, r.assessment.comparison])
        ).lower()
        for word in banned:
            assert word not in text, f"{r.outcome.id}: card says {word!r}"

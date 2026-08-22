"""Two published shapes, kept apart.

Three of Singapore's six autonomous universities do not publish a 10th-90th
percentile grade profile. SUSS and SIT publish *banded percentages* -- the
share of applicants in each score band who got through a stage -- and SUTD
publishes a subject profile and no bands at all.

The tempting move is to flatten a banded profile into a p10/p90. It would make
every course render identically and it would be a lie: you cannot recover a
percentile from a share, and inventing one manufactures a precision three
universities deliberately withheld.

The other trap is subtler and is the one that would actually have shipped.
SUSS and SIT publish against the RETIRED 90-point UAS. The AY2026 score is out
of 70. A student's 60 is not their 60 -- and a tool that compared them would
produce a verdict that looked entirely ordinary and was wrong. Every test below
exists to keep one of those two doors shut.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from engine.buckets import Bucket, assess_banded
from engine.forward import explore
from engine.model import BandedProfile, Fact, ProfileBand

TODAY = _dt.date(2026, 8, 2)


def _fact():
    return Fact(value="test", as_of_year=2025, source_id="suss-igp-2026", confidence="high")


# --- 1. the shapes are never conflated -----------------------------------


def test_no_outcome_holds_both_a_percentile_band_and_a_banded_profile(pack):
    """They are different published claims. Holding both invites averaging them."""
    for o in pack.outcomes.values():
        assert not (o.band and o.banded), (
            f"{o.id}: has a percentile band AND a banded profile. Record whichever "
            f"the institution actually publishes, not both."
        )


def test_a_banded_profile_exposes_no_percentile_fields(pack):
    """If p10/p90 never exist on this type, nothing downstream can read them."""
    for o in pack.outcomes.values():
        for profile in o.banded:
            for forbidden in ("p10", "p90", "p10_points", "p90_points"):
                assert not hasattr(profile, forbidden), (
                    f"{o.id}: BandedProfile grew a {forbidden!r}. A share of applicants "
                    f"is not a percentile and must not be able to masquerade as one."
                )


# --- 2. the scale mismatch, which is the one that would have shipped -----


def test_every_retired_scale_profile_is_marked_not_comparable(pack):
    """SUSS and SIT publish against a UAS that was retired before this cohort
    sits its exams. Marking one comparable would silently re-enable the bad
    comparison for every course that shares the scale."""
    seen = 0
    for o in pack.outcomes.values():
        for profile in o.banded:
            if profile.scale == "uas_90_retired":
                seen += 1
                assert not profile.comparable, (
                    f"{o.id}: a 90-point UAS profile is marked comparable. The score "
                    f"PathAhead computes is out of 70; these are different units."
                )
                assert "90" in profile.basis, o.id
    assert seen >= 20, "the retired-scale profiles vanished; this test guards nothing"


def test_a_student_is_never_placed_against_a_retired_scale(pack, strong_grades):
    """The verdict must be withheld, and the bands must still be shown."""
    result = explore(pack, year_level="jc-2", current_year=2026,
                     grades=strong_grades, today=TODAY)
    checked = 0
    for r in result.results:
        retired = [p for p in r.outcome.banded
                   if p.qualification == "a-level" and not p.comparable]
        if not retired:
            continue
        checked += 1
        assert r.assessment.bucket is Bucket.PUBLISHED_ON_ANOTHER_BASIS, r.outcome.id
        # withheld, but not hidden: the published figures still reach the reader
        assert r.assessment.comparison and "%" in r.assessment.comparison, r.outcome.id
        assert r.citation is not None, r.outcome.id
    assert checked >= 10, "no retired-scale course was assessed; the test is inert"


def test_an_a_level_score_is_never_placed_against_a_polytechnic_gpa_band(pack, strong_grades):
    """SIT publishes GPA bands per course and A-Level figures only per cluster.
    An earlier version fell back to the GPA bands when the A-Level pool was
    empty, and cheerfully compared a score out of 70 against a GPA out of 4.00.
    """
    result = explore(pack, year_level="jc-2", current_year=2026,
                     grades=strong_grades, today=TODAY)
    checked = 0
    for r in result.results:
        has_alevel = r.outcome.band is not None or any(
            p.qualification == "a-level" for p in r.outcome.banded
        )
        has_poly_bands = any(
            p.qualification == "polytechnic-diploma" for p in r.outcome.banded
        )
        if has_alevel or not has_poly_bands:
            continue
        checked += 1
        assert r.assessment.bucket is Bucket.DATA_INCOMPLETE, r.outcome.id
        assert r.assessment.comparison is None, (
            f"{r.outcome.id}: produced a comparison from a pool this student is "
            f"not in."
        )
    assert checked >= 30, "SIT's courses stopped exercising this path"


# --- 3. censored figures stay censored ------------------------------------


def test_a_censored_share_is_never_given_a_number(pack):
    """SUSS prints "Below 5%" rather than a figure in many cells. Filling in a
    midpoint would be inventing data, and the censoring itself is informative."""
    seen = 0
    for o in pack.outcomes.values():
        for profile in o.banded:
            for band in profile.bands:
                if band.share_label.lower().startswith("below"):
                    seen += 1
                    assert band.share is None, (
                        f"{o.id}: '{band.share_label}' was turned into {band.share}. "
                        f"The publisher chose not to give a number."
                    )
    assert seen > 0, "no censored share left in the pack; this test guards nothing"


def test_the_published_wording_survives_into_what_a_reader_sees():
    profile = BandedProfile(
        stage="offered",
        basis="UAS out of 90 (retired)",
        scale="uas_90_retired",
        comparable=False,
        bands=(
            ProfileBand(label="UAS below 60.00", share_label="Below 5%", high=59.99),
            ProfileBand(label="UAS at least 60.00", share_label="47.9%", low=60.0,
                        high=90.0, share=47.9),
        ),
        fact=_fact(),
    )
    a = assess_banded(profile, 65.0, band_year=2025, confidence="high")
    assert a.bucket is Bucket.PUBLISHED_ON_ANOTHER_BASIS
    assert "Below 5%" in a.comparison
    assert "47.9%" in a.comparison


# --- 4. the two stages stay two stages ------------------------------------


def test_suss_carries_both_stages_and_leads_with_the_offer(pack, strong_grades):
    """Clearing SUSS's grade band gets you an interview, not a place. Keeping
    only the shortlisting figure would overstate a student's position badly --
    Psychology shortlisted 72.6% of the top A-Level band and offered 18.7%."""
    suss = [o for o in pack.outcomes.values() if o.institution_short == "SUSS"]
    assert suss
    for o in suss:
        stages = {p.stage for p in o.banded if p.qualification == "a-level"}
        assert stages == {"shortlisted", "offered"}, o.id

    result = explore(pack, year_level="jc-2", current_year=2026,
                     grades=strong_grades, today=TODAY)
    psych = next(r for r in result.results if r.outcome.id == "suss-psychology")
    assert "18.7%" in psych.assessment.comparison
    assert "72.6%" not in psych.assessment.comparison


def test_every_suss_course_says_the_interview_decides(pack):
    for o in pack.outcomes.values():
        if o.institution_short != "SUSS":
            continue
        assert o.has_extra_assessment, o.id
        detail = " ".join(x.detail for x in o.overlays)
        assert "three-stage" in detail or "3-stage" in detail, o.id


# --- 5. SUTD publishes no band, and says so rather than implying one -------


def test_sutd_has_no_band_and_no_banded_profile(pack):
    sutd = [o for o in pack.outcomes.values() if o.institution_short == "SUTD"]
    assert len(sutd) >= 5
    for o in sutd:
        assert o.band is None and not o.banded, (
            f"{o.id}: SUTD publishes a subject profile, not a band. Anything here "
            f"was constructed rather than published."
        )
        detail = " ".join(x.detail for x in o.overlays)
        assert "H2 Mathematics" in detail, o.id


def test_sutd_says_the_pillar_is_chosen_after_the_first_year(pack):
    """The most useful thing PathAhead can tell someone who is not yet sure."""
    for o in pack.outcomes.values():
        if o.institution_short != "SUTD":
            continue
        assert o.flexibility and o.flexibility.common_first_year, o.id
        assert o.flexibility.declares_major_later, o.id


# --- 6. the comparable path works, for the pool it belongs to -------------


@pytest.mark.parametrize(
    "gpa,expected",
    [(2.5, Bucket.BELOW_RANGE), (3.4, Bucket.WITHIN_RANGE), (3.9, Bucket.ABOVE_RANGE)],
)
def test_a_comparable_banded_profile_places_a_score_in_its_published_band(gpa, expected):
    profile = BandedProfile(
        stage="offered",
        basis="polytechnic GPA out of 4.00",
        scale="poly_gpa_4",
        qualification="polytechnic-diploma",
        comparable=True,
        bands=(
            ProfileBand(label="GPA below 3.20", share_label="3.0%", high=3.19, share=3.0),
            ProfileBand(label="GPA 3.20 to below 3.60", share_label="40.6%", low=3.20,
                        high=3.59, share=40.6),
            ProfileBand(label="GPA 3.60 to 4.00", share_label="62.1%", low=3.60,
                        high=4.00, share=62.1),
        ),
        fact=_fact(),
    )
    a = assess_banded(profile, gpa, band_year=2025, confidence="high")
    assert a.bucket is expected
    # never a probability for THIS student
    assert "chance" not in a.explanation.lower()
    assert "likely" not in a.explanation.lower()


#: Buckets that are NOT a verdict about the student. Each one is PathAhead
#: declining to draw a conclusion and saying why -- an O-Level aggregate that
#: cannot be set against an A-Level score, or a course whose publisher prints
#: no profile at all. They are outcomes of the coverage, not of the axis.
_NON_VERDICT = (Bucket.PUBLISHED_ON_ANOTHER_BASIS, Bucket.DATA_INCOMPLETE)


def test_the_evidence_axis_still_discriminates_across_the_larger_pack(pack, strong_grades):
    """Courses must not collapse into one verdict -- the failure that made
    ISSUES_v0.2 §A a blocker.

    Scoped to the courses where a verdict is actually GIVEN. When the four
    polytechnics went in, `published_on_another_basis` became the largest single
    bucket in the pack, and it grew again with SP: 195 of 330 courses now
    publish a net ELR2B2 aggregate that this project deliberately refuses to
    compare with an A-Level score. Measuring the refusal alongside the verdicts
    would make this test a report on the pack's COMPOSITION rather than on the
    axis's resolution, and it would fail simply because honest coverage grew.

    The whole-pack guard is kept, but sharpened: if any bucket does exceed 60%
    of the pack it must be one of the non-verdict ones. A real verdict collapse
    -- every course reading "at or above last year's range", which is exactly
    what §A was -- still fails here, loudly.
    """
    result = explore(pack, year_level="jc-2", current_year=2026,
                     grades=strong_grades, today=TODAY)
    counts: dict[Bucket, int] = {}
    for r in result.results:
        counts[r.assessment.bucket] = counts.get(r.assessment.bucket, 0) + 1
    assert len(counts) >= 4, f"only {len(counts)} distinct verdicts across the pack: {counts}"

    # No VERDICT may swallow the pack.
    for bucket, n in counts.items():
        if bucket not in _NON_VERDICT:
            assert n < len(result.results) * 0.6, (
                f"one verdict swallowed the pack: {counts}")

    # And among the courses actually given a verdict, the axis must still have
    # resolution -- at least three distinct verdicts, none of them taking 80%.
    verdicts = {b: n for b, n in counts.items() if b not in _NON_VERDICT}
    scored = sum(verdicts.values())
    assert scored, "no course got a verdict at all; the axis is doing nothing"
    assert len(verdicts) >= 3, f"only {len(verdicts)} distinct verdicts given: {verdicts}"
    assert max(verdicts.values()) < scored * 0.8, (
        f"one verdict swallowed the courses that got one: {verdicts}")

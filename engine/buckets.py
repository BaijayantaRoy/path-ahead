"""Eligibility and competitiveness are different kinds of claim.

    "An aggregate of 20 or lower qualifies you for JC"   -- a published rule.
      PathAhead may assert this.

    "Your score against last year's admitted range"      -- a historical band.
      PathAhead may only describe it, never turn it into a verdict.

Rendering both in the same colour with the same confidence is how a careful
tool becomes a misleading one. So the engine returns a named bucket, never a
probability and never a yes/no.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Bucket(str, Enum):
    MEETS_REQUIREMENT = "meets_requirement"
    DOES_NOT_MEET_REQUIREMENT = "does_not_meet_requirement"
    ABOVE_RANGE = "above_range"
    #: Everyone admitted last year had this exact profile. Distinct from
    #: "above the range" and the distinction matters enormously: a student
    #: with AAA is comfortably clear of Landscape Architecture, and merely
    #: level with Medicine. Collapsing the two put all 21 courses in one
    #: bucket and made the whole axis useless.
    EXACTLY_AT_PROFILE = "exactly_at_profile"
    AT_OR_ABOVE_RANGE = "at_or_above_range"
    WITHIN_RANGE = "within_range"
    BELOW_RANGE = "below_range"
    #: The university published something, and it does not line up with the
    #: score we compute. Distinct from DATA_INCOMPLETE, which means we have
    #: nothing. Here we have their figures and are declining to misuse them --
    #: SUSS and SIT publish against the retired 90-point UAS while the AY2026
    #: score is out of 70, so the numbers look comparable and are not.
    PUBLISHED_ON_ANOTHER_BASIS = "published_on_another_basis"
    DATA_INCOMPLETE = "data_incomplete"


#: Copy rules live here, in one place, so they can be reviewed like code.
#: Note what is absent: "you qualify", "you missed the cutoff", "unrealistic".
#: See SAFEGUARDS.md 5.3 for why.
HEADLINE: dict[Bucket, str] = {
    Bucket.MEETS_REQUIREMENT: "Meets the stated requirement",
    Bucket.DOES_NOT_MEET_REQUIREMENT: "Below the stated requirement",
    Bucket.ABOVE_RANGE: "Above last year's range",
    Bucket.EXACTLY_AT_PROFILE: "Level with last year's profile",
    Bucket.AT_OR_ABOVE_RANGE: "At the top of last year's range",
    Bucket.WITHIN_RANGE: "Within last year's range",
    Bucket.BELOW_RANGE: "Below last year's range",
    Bucket.PUBLISHED_ON_ANOTHER_BASIS: "Published, but on a different scale",
    Bucket.DATA_INCOMPLETE: "Not enough verified data yet",
}

EXPLANATION: dict[Bucket, str] = {
    Bucket.MEETS_REQUIREMENT: (
        "This is a published requirement, so this part is a straightforward yes."
    ),
    Bucket.DOES_NOT_MEET_REQUIREMENT: (
        "This is a published requirement and your current result is below it. "
        "Other routes to the same destination are listed below."
    ),
    Bucket.ABOVE_RANGE: (
        "Your result is clear of the whole range of students admitted last year. "
        "That is a good sign, not a guarantee -- places, applicants and "
        "requirements change every year."
    ),
    Bucket.EXACTLY_AT_PROFILE: (
        "Every student admitted to this course last year had exactly this "
        "profile, and so do you. There is no headroom above it, so the parts of "
        "the decision that are not grades -- interviews, portfolios, subject "
        "prerequisites -- carry more weight here than almost anywhere else."
    ),
    Bucket.AT_OR_ABOVE_RANGE: (
        "Your result sits at the top of the range of students admitted last "
        "year. A good sign, not a guarantee -- places, applicants and "
        "requirements change every year."
    ),
    Bucket.WITHIN_RANGE: (
        "Your result sits inside the range of students admitted last year. "
        "Admission still depends on this year's applicants and places."
    ),
    Bucket.BELOW_RANGE: (
        "This course was more competitive than your current result in last "
        "year's exercise. That is last year's picture, not a decision about "
        "you -- and there are other ways in, listed below."
    ),
    Bucket.PUBLISHED_ON_ANOTHER_BASIS: (
        "This university does publish figures, and they are shown below -- but "
        "they are measured on a scale that no longer matches the one your score "
        "is calculated on, so putting your number next to theirs would give you "
        "a false answer. Read their bands as background, and treat the parts of "
        "the decision that are not grades as carrying real weight here."
    ),
    Bucket.DATA_INCOMPLETE: (
        "PathAhead does not yet have a verified figure for this course, so it "
        "will not show you a guess. The official page is linked instead."
    ),
}

#: Ordering for display. Never sort by selectivity: see SAFEGUARDS.md 5.1.
DISPLAY_ORDER: list[Bucket] = [
    Bucket.MEETS_REQUIREMENT,
    Bucket.ABOVE_RANGE,
    Bucket.AT_OR_ABOVE_RANGE,
    Bucket.EXACTLY_AT_PROFILE,
    Bucket.WITHIN_RANGE,
    Bucket.BELOW_RANGE,
    Bucket.DOES_NOT_MEET_REQUIREMENT,
    Bucket.PUBLISHED_ON_ANOTHER_BASIS,
    Bucket.DATA_INCOMPLETE,
]


@dataclass(frozen=True, slots=True)
class Assessment:
    bucket: Bucket
    headline: str
    explanation: str
    comparison: str | None = None
    band_year: int | None = None
    confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket.value,
            "headline": self.headline,
            "explanation": self.explanation,
            "comparison": self.comparison,
            "band_year": self.band_year,
            "confidence": self.confidence,
        }


def assess_band(
    score: float,
    p10: float,
    p90: float,
    *,
    direction: str,
    band_year: int,
    basis: str,
    confidence: str,
    statistic: str = "p10_p90",
) -> Assessment:
    """Place a score against a published percentile band.

    `p10`/`p90` are the 10th and 90th percentile of last year's admitted
    students -- deliberately not treated as a threshold, because the
    institutions that publish them say explicitly that they are not one.

    `statistic` is asserted rather than assumed. Every caller that reaches here
    should be passing a percentile band; a min-max full admitted range means
    something else and belongs in `assess_published_on_another_basis`. Failing
    loudly is better than silently emitting percentile copy over a full range.
    """
    if statistic != "p10_p90":
        raise ValueError(
            f"assess_band describes a 10th-90th percentile band, but was given "
            f"statistic={statistic!r}. A full admitted range is a different claim "
            f"and must not borrow this wording."
        )
    lo, hi = (min(p10, p90), max(p10, p90))
    degenerate = lo == hi   # the whole admitted cohort shared one profile

    if direction == "higher_is_better":
        if degenerate and score == hi:
            bucket = Bucket.EXACTLY_AT_PROFILE
        elif score > hi:
            bucket = Bucket.ABOVE_RANGE
        elif score >= lo:
            bucket = (
                Bucket.AT_OR_ABOVE_RANGE if score == hi else Bucket.WITHIN_RANGE
            )
        else:
            bucket = Bucket.BELOW_RANGE
    else:
        if degenerate and score == lo:
            bucket = Bucket.EXACTLY_AT_PROFILE
        elif score < lo:
            bucket = Bucket.ABOVE_RANGE
        elif score <= hi:
            bucket = (
                Bucket.AT_OR_ABOVE_RANGE if score == lo else Bucket.WITHIN_RANGE
            )
        else:
            bucket = Bucket.BELOW_RANGE

    # Headroom: how far clear of the FLOOR of last year's intake. This is the
    # figure that actually discriminates at the top, where the published
    # profiles saturate.
    headroom = (score - lo) if direction == "higher_is_better" else (lo - score)

    return Assessment(
        bucket=bucket,
        headline=HEADLINE[bucket],
        explanation=EXPLANATION[bucket],
        comparison=(
            f"you {score:g} - {band_year} range {lo:g} to {hi:g} ({basis})"
            + (f", {headroom:g} clear of the floor" if headroom > 0 else "")
        ),
        band_year=band_year,
        confidence=confidence,
    )


#: The words each published statistic is allowed to be described in.
#:
#: A 10th-90th percentile band and a full min-to-max admitted range have the
#: same SHAPE -- two numbers -- and completely different meanings. The middle
#: 80% excludes both tails by construction; a min-max includes every admitted
#: student, so it is necessarily wider from the same intake. Describing the
#: second in the language of the first would tell a family that a polytechnic
#: course is far less selective than a degree when the only difference is which
#: statistic the institution chose to publish.
#:
#: Guarded by `test_a_min_max_band_is_never_described_as_a_percentile_band`.
STATISTIC_WORDS: dict[str, dict[str, str]] = {
    "p10_p90": {
        "short": "range",
        "phrase": "the range of students admitted last year",
        "what_it_is": (
            "the 10th to 90th percentile of last year's intake -- the middle "
            "80%, with the highest and lowest admitted students left out"
        ),
    },
    "min_max": {
        "short": "full admitted range",
        "phrase": "the full range of students admitted",
        "what_it_is": (
            "the lowest and the highest aggregate of anyone admitted through "
            "the Joint Admissions Exercise -- the whole cohort, not a middle "
            "band. It is wider than a university's published percentile range "
            "for that reason alone, which is a difference in what was counted, "
            "not a difference in how hard the course is to get into"
        ),
    },
}


def assess_published_on_another_basis(band: Any, *, band_year: int, confidence: str) -> Assessment:
    """Show a published band and decline to score against it.

    Used where the institution publishes a real figure on a basis that does not
    match the score PathAhead computes for this transition. The polytechnics
    publish a net ELR2B2 O-Level aggregate; this transition scores an A-Level
    result out of 70. Both are numbers, neither is the other, and putting them
    side by side would produce a verdict that looked ordinary and was nonsense.

    So the numbers are shown, in the publisher's own words, and the verdict is
    withheld -- the same contract `assess_banded` honours for SUSS and SIT.
    """
    words = STATISTIC_WORDS.get(band.statistic, STATISTIC_WORDS["p10_p90"])
    lo, hi = (min(band.p10_points, band.p90_points), max(band.p10_points, band.p90_points))
    span = band.years_label or str(band_year)
    years_note = (
        f" These are {band.years_covered} separate admissions exercises, shown "
        f"side by side rather than merged, so you can see how much the figure "
        f"moves from year to year."
        if band.years_covered > 1
        else " This is a single year's exercise, so there is no way to see from"
             " it how much the figure moves year to year."
    )
    return Assessment(
        bucket=Bucket.PUBLISHED_ON_ANOTHER_BASIS,
        headline=HEADLINE[Bucket.PUBLISHED_ON_ANOTHER_BASIS],
        # Deliberately NOT the shared PUBLISHED_ON_ANOTHER_BASIS explanation.
        # That one is written for SUSS and SIT, and says "this university" and
        # "a scale that no longer matches" -- both wrong here. A polytechnic is
        # not a university, and its scale has not been retired: it is a live
        # measure of a different qualification. Reusing the string would have
        # been tidy and would have told a family something untrue.
        explanation=(
            f"This is a real published figure and it is shown here in full. It "
            f"is measured on {band.basis}, which is a different qualification "
            f"from the one your result is on -- so putting your number next to "
            f"it would give you an answer that looked sensible and meant "
            f"nothing. What it records is {words['what_it_is']}.{years_note} "
            f"To find out where you would actually stand, ask the admissions "
            f"office: the routes below set out which one applies to you."
        ),
        comparison=(
            f"{words['short']} {lo:g} to {hi:g} ({band.basis}, {span}) - "
            f"not compared with your result, because it is not the same measure"
        ),
        band_year=band_year,
        confidence=confidence,
    )


def _band_summary(profile: Any) -> str:
    """The published bands, in the university's own words.

    Reproduced rather than reduced. "Below 5%" stays "Below 5%": inventing a
    midpoint for a figure the publisher chose to censor would be manufacturing
    data, and the censoring itself tells a reader something.
    """
    return " | ".join(f"{b.label}: {b.share_label}" for b in profile.bands)


def assess_banded(
    profile: Any,
    score: float | None,
    *,
    band_year: int,
    confidence: str,
) -> Assessment:
    """Place a score against a *banded* profile — a different published claim
    from a percentile band, and kept different.

    Where `profile.comparable` is False the bands are still shown and the
    verdict is withheld. That is the whole point of the type: SUSS and SIT
    publish real, useful figures against a UAS scale that was retired before
    this cohort sits its exams, and a tool that quietly compared a 70-point
    score to a 90-point band would be wrong in a way nobody would notice.
    """
    stage_word = "shortlisted" if profile.stage == "shortlisted" else "offered a place"

    if not profile.comparable:
        return Assessment(
            bucket=Bucket.PUBLISHED_ON_ANOTHER_BASIS,
            headline=HEADLINE[Bucket.PUBLISHED_ON_ANOTHER_BASIS],
            explanation=(
                f"{EXPLANATION[Bucket.PUBLISHED_ON_ANOTHER_BASIS]} "
                f"Theirs is {profile.basis}."
            ),
            comparison=(
                f"share of applicants {stage_word}, by {profile.basis} "
                f"({band_year}) - {_band_summary(profile)}"
            ),
            band_year=band_year,
            confidence=confidence,
        )

    if score is None:
        return incomplete("your entered subjects do not produce a score on this basis")

    # Comparable case: say which published band the student falls in, and what
    # share of that band got through. Still never a probability for THIS
    # student -- a share of a past cohort is not a personal chance.
    hit = None
    for b in profile.bands:
        low_ok = b.low is None or score >= b.low
        high_ok = b.high is None or score <= b.high
        if low_ok and high_ok:
            hit = b
            break

    if hit is None:
        return incomplete("your score falls outside every band this university published")

    top = profile.bands[-1] if profile.bands else None
    if hit is top and len(profile.bands) > 1:
        bucket = Bucket.ABOVE_RANGE
    elif hit is profile.bands[0] and len(profile.bands) > 1:
        bucket = Bucket.BELOW_RANGE
    else:
        bucket = Bucket.WITHIN_RANGE

    return Assessment(
        bucket=bucket,
        headline=HEADLINE[bucket],
        explanation=(
            f"Of the applicants in this band last year, {hit.share_label} were "
            f"{stage_word}. That is what happened to a group, not a prediction "
            f"about you, and this university weighs more than grades."
        ),
        comparison=(
            f"you {score:g} - {hit.label}, where {hit.share_label} were "
            f"{stage_word} ({profile.basis}, {band_year})"
        ),
        band_year=band_year,
        confidence=confidence,
    )


def assess_requirement(
    score: float, threshold: float, *, direction: str, confidence: str
) -> Assessment:
    meets = score <= threshold if direction == "lower_is_better" else score >= threshold
    bucket = Bucket.MEETS_REQUIREMENT if meets else Bucket.DOES_NOT_MEET_REQUIREMENT
    return Assessment(
        bucket=bucket,
        headline=HEADLINE[bucket],
        explanation=EXPLANATION[bucket],
        comparison=f"you {score:g} - requirement {threshold:g}",
        confidence=confidence,
    )


#: Wording for a full admitted range, kept apart from HEADLINE/EXPLANATION so
#: the two vocabularies can never accidentally converge -- see
#: `test_a_min_max_band_is_never_described_as_a_percentile_band`.
HEADLINE_MINMAX: dict[Bucket, str] = {
    Bucket.ABOVE_RANGE: "Above the full range of students admitted",
    Bucket.EXACTLY_AT_PROFILE: "Level with every student admitted last year",
    Bucket.AT_OR_ABOVE_RANGE: "At the strongest end of last year's intake",
    Bucket.WITHIN_RANGE: "Within the full range of students admitted",
    Bucket.BELOW_RANGE: "Below the full range of students admitted",
}

EXPLANATION_MINMAX: dict[Bucket, str] = {
    Bucket.ABOVE_RANGE: (
        "Your aggregate is stronger than every student admitted last year, tails "
        "included -- this range is the whole intake, not a middle band. A good "
        "sign, not a guarantee."
    ),
    Bucket.EXACTLY_AT_PROFILE: (
        "Every student admitted last year had exactly this aggregate, and so do "
        "you. The parts of the decision that are not grades carry real weight "
        "here."
    ),
    Bucket.AT_OR_ABOVE_RANGE: (
        "Your aggregate matches the strongest student admitted last year, out of "
        "the whole intake. A good sign, not a guarantee -- places, applicants and "
        "requirements change every year."
    ),
    Bucket.WITHIN_RANGE: (
        "Your aggregate sits inside the full range of students admitted last "
        "year -- the whole intake, not a middle band with the tails removed. "
        "Admission still depends on this year's applicants and places."
    ),
    Bucket.BELOW_RANGE: (
        "Last year's weakest admitted aggregate was still stronger than yours. "
        "That is last year's picture, not a decision about you, and there are "
        "other ways in."
    ),
}


def assess_min_max_band(
    score: float,
    lo: float,
    hi: float,
    *,
    direction: str,
    band_year: int,
    confidence: str,
) -> Assessment:
    """Place a score against a full admitted range -- the whole cohort, tails
    included, never described in the middle-80% language `assess_band` uses.

    This exists for exactly the case `assess_band` refuses: an ELR2B2 aggregate
    scored by an O-Level applicant against a polytechnic's own published
    min-max range IS that applicant's own basis, and a full range is a real,
    citable figure -- just a different published claim from a percentile band,
    with its own vocabulary (STATISTIC_WORDS["min_max"]) and its own bucket
    wording (HEADLINE_MINMAX / EXPLANATION_MINMAX above).

    Comparing an A-Level score against this same range is the wrong call for a
    different reason entirely -- wrong BASIS, not wrong SHAPE -- and stays
    routed through `assess_published_on_another_basis`, which this function
    does not touch and does not replace.
    """
    lo, hi = (min(lo, hi), max(lo, hi))
    degenerate = lo == hi

    if direction == "higher_is_better":
        if degenerate and score == hi:
            bucket = Bucket.EXACTLY_AT_PROFILE
        elif score > hi:
            bucket = Bucket.ABOVE_RANGE
        elif score >= lo:
            bucket = Bucket.AT_OR_ABOVE_RANGE if score == hi else Bucket.WITHIN_RANGE
        else:
            bucket = Bucket.BELOW_RANGE
    else:
        if degenerate and score == lo:
            bucket = Bucket.EXACTLY_AT_PROFILE
        elif score < lo:
            bucket = Bucket.ABOVE_RANGE
        elif score <= hi:
            bucket = Bucket.AT_OR_ABOVE_RANGE if score == lo else Bucket.WITHIN_RANGE
        else:
            bucket = Bucket.BELOW_RANGE

    headroom = (score - lo) if direction == "higher_is_better" else (lo - score)
    words = STATISTIC_WORDS["min_max"]

    return Assessment(
        bucket=bucket,
        headline=HEADLINE_MINMAX[bucket],
        explanation=EXPLANATION_MINMAX[bucket],
        comparison=(
            f"you {score:g} - {band_year} {words['short']} {lo:g} to {hi:g}"
            + (f", {headroom:g} clear of the floor" if headroom > 0 else "")
        ),
        band_year=band_year,
        confidence=confidence,
    )


def incomplete(reason: str) -> Assessment:
    return Assessment(
        bucket=Bucket.DATA_INCOMPLETE,
        headline=HEADLINE[Bucket.DATA_INCOMPLETE],
        explanation=f"{EXPLANATION[Bucket.DATA_INCOMPLETE]} ({reason})",
    )

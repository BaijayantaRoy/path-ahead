"""Calibration: is the output actually *meaningful* to a real person?

This file exists because 128 tests passed on a version that told a
seventeen-year-old, twenty-one times, that she was a weak match for
everything. Every one of those tests checked that the machinery was
self-consistent. Not one checked that the answer was sensible.

The rules below are the ones that were violated:

  1. Missing data on OUR side must never cost the student points.
  2. Answering more about yourself must never lower your score.
  3. A realistic profile must produce discrimination, and a top score that
     is not discouraging.
  4. Nothing shown to a student may read as a judgement about them.

Profiles here are written the way a real person answers, not the way the
data is stored — that was the other half of the failure. The demo profile
used subject codes spelled exactly as the pack spells them and scored 81;
a real teenager picking "Further Mathematics" scored 24.
"""

from __future__ import annotations

import pytest

from engine.fit import score_all, score_outcome, subject_families
from engine.profile import StudentProfile


@pytest.fixture
def fam(pack):
    return subject_families(pack)


def _spread(pack, profile):
    scores = [
        s.score
        for s in score_all(pack, profile, "a-level-to-university-2026").values()
        if s.score is not None
    ]
    return min(scores), max(scores), scores


#: Profiles written as real students answer. Deliberately includes the exact
#: session that shipped broken.
REALISTIC = {
    "further-maths-and-design": StudentProfile(
        interests=("R", "A", "C"),
        enjoyed_subjects=("further-mathematics",),
        priorities=("earnings", "impact", "autonomy", "stability"),
    ),
    "sciences-caring": StudentProfile(
        interests=("S", "I"),
        enjoyed_subjects=("biology", "chemistry"),
        assessment_style="practical",
        teamwork="team",
    ),
    "humanities-writer": StudentProfile(
        interests=("A", "E"),
        enjoyed_subjects=("literature", "history"),
        assessment_style="coursework",
        priorities=("impact",),
    ),
    "undecided-broad": StudentProfile(
        interests=("I",),
        enjoyed_subjects=("mathematics", "economics"),
        teamwork="mixed",
    ),
    "everything-answered": StudentProfile(
        interests=("I", "R", "C"),
        enjoyed_subjects=("mathematics", "physics", "computing"),
        assessment_style="exams",
        teamwork="individual",
        priorities=("earnings", "mastery"),
        willing_extra_assessment=True,
        cost_sensitive=False,
    ),
}


# --- 1. our data gaps must never cost the student -------------------------


def test_a_course_with_no_survey_data_is_not_marked_down_for_it(pack, fam):
    """Medicine has no GES salary — MOE does not survey it. The old version
    scored 0/15 for "what you said matters" because of that."""
    p = StudentProfile(
        interests=("I", "S"),
        enjoyed_subjects=("biology", "chemistry"),
        priorities=("earnings", "stability"),
    )
    fit = score_outcome(pack.outcomes["nus-medicine"], p, families=fam)
    scored = [f for f in fit.factors if f.source == "priorities"]
    assert not scored, "a course must not be scored on data we do not have"
    assert fit.not_assessed, "and the gap must be shown to the reader"
    assert any("says nothing about the course" in x for x in fit.not_assessed)


def test_cost_is_scored_only_where_a_fee_figure_exists(pack, fam):
    """The old version gave 5/10 for cost to all 21 courses because no fee
    figures were loaded — a flat penalty with zero discriminating value.

    Now that NUS fees are loaded, cost SHOULD score for NUS and must still be
    dropped for the universities whose fee tables are not in the pack yet."""
    p = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",), cost_sensitive=True
    )
    scored_without_data = []
    scored_with_data = 0
    for outcome in pack.outcomes.values():
        fit = score_outcome(outcome, p, families=fam)
        cost = [f for f in fit.factors if f.source == "cost_sensitive"]
        # `has_any_fee`, not `annual_fee_citizen`: SIT charges per credit unit
        # and publishes no annual figure at all, yet the full programme cost is
        # known. Checking the annual field alone would have declared 36 courses
        # feeless when the number a family plans around is right there.
        has_fee = outcome.cost and outcome.cost.has_any_fee
        if cost and not has_fee:
            scored_without_data.append(outcome.id)
        if cost and has_fee:
            scored_with_data += 1
        if has_fee is None or not has_fee:
            assert any("fee" in x for x in fit.not_assessed) or not cost
    assert not scored_without_data, f"cost scored with no fee figure: {scored_without_data}"
    assert scored_with_data > 0, "cost never scored even where fees are loaded"


def test_a_course_taught_in_a_language_is_not_ranked_without_being_asked(pack, fam):
    """The failure that made this test exist.

    A student who does not read Chinese was shown Ngee Ann's Diploma in Chinese
    Studies as her SECOND STRONGEST match out of 296 courses. It scored 67/100,
    and every point came from generic overlap -- "you work best through exams,
    and so does much of this course" -- because nothing in the pack recorded
    that NP requires Higher Chinese 1-4 or Chinese 1-3 to be considered, and
    states that at least half the course is conducted in Chinese.

    The score was not too high. A score at all was the error: any number puts
    the course in a ranking, and a low one would have ranked it above hundreds
    of others just the same.
    """
    with_lang = [o for o in pack.outcomes.values() if o.language_requirement]
    assert with_lang, "no course records a language requirement; this test proves nothing"

    unasked = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",), assessment_style="exams"
    )
    assert unasked.languages_offered is None
    for o in with_lang:
        fit = score_outcome(o, unasked, families=fam)
        assert fit.score is None, (
            f"{o.id}: scored {fit.score} for a student who was never asked "
            f"whether they offer {o.language_requirement.language}"
        )
        assert o.language_requirement.label in (fit.unscored_reason or ""), (
            f"{o.id}: does not say what the requirement actually is"
        )


def test_saying_you_do_not_offer_the_language_is_different_from_not_being_asked(pack, fam):
    """"None of these" is an answer, and must not be treated as silence.

    A student who has said they offer no mother tongue should not keep being
    told PathAhead needs to know.
    """
    o = next(o for o in pack.outcomes.values() if o.language_requirement)
    said_none = StudentProfile(
        interests=("I",), assessment_style="exams", languages_offered=()
    )
    fit = score_outcome(o, said_none, families=fam)
    assert fit.score is None
    assert "not been told" not in (fit.unscored_reason or ""), (
        "a student who answered is being told they have not answered"
    )
    assert "not among the ones you said" in (fit.unscored_reason or "")


def test_offering_the_language_lets_the_course_be_scored_normally(pack, fam):
    """The block is about eligibility, not about discouraging anyone.

    A student who does offer Chinese should see Chinese Studies scored like any
    other course -- the requirement is met, so it stops being the question.
    """
    o = pack.outcomes["np-chinese-studies"]
    offers = StudentProfile(
        interests=("A",), enjoyed_subjects=("chinese",), assessment_style="coursework",
        languages_offered=("chinese",),
    )
    fit = score_outcome(o, offers, families=fam)
    assert fit.score is not None, "a qualified student was still refused a score"
    assert fit.factors, "scored with no reasoning"


def test_a_blocked_course_is_explained_rather_than_judged(pack, fam):
    """It is not hidden and it is not a verdict.

    PathAhead does not know what it has not been told -- the requirement sits
    at O-Level while forward mode collects A-Level subjects -- and a course
    removed silently is one a family never gets to argue with.
    """
    banned = ["weak", "poor", "unsuitable", "not for you", "cannot", "you failed",
              "you don't", "you do not have"]
    unasked = StudentProfile(interests=("I",), assessment_style="exams")
    for o in (o for o in pack.outcomes.values() if o.language_requirement):
        reason = (score_outcome(o, unasked, families=fam).unscored_reason or "").lower()
        for word in banned:
            assert word not in reason, f"{o.id}: reason says {word!r}"
        # And it must point at the thing that would change the answer.
        assert "answer" in reason or "said" in reason


def test_every_language_requirement_carries_its_source(pack):
    """This is an official entry condition, not PathAhead's opinion of a course."""
    for o in pack.outcomes.values():
        lr = o.language_requirement
        if not lr:
            continue
        assert lr.fact is not None, f"{o.id}: language requirement with no source"
        assert lr.fact.basis == "official", f"{o.id}: recorded as editorial"
        assert lr.fact.source_id in pack.sources, f"{o.id}: cites an unknown source"
        assert lr.language in {"chinese", "malay", "tamil"}, f"{o.id}: {lr.language}"


def test_a_language_requirement_is_never_added_by_pattern_matching_the_name(pack):
    """The same mistake has two directions, and both reach a real student.

    Adding a requirement a university does not set would block a course for
    someone entitled to it. NTU's Bachelor of Arts (Hons) in Linguistics and
    Multilingual Studies has "Multilingual" in its title and is the obvious
    candidate for a careless match, but its published curriculum is a
    linguistics curriculum taught ABOUT languages -- Structure of Modern
    English, Phonetics and Phonology, Language and the Computer -- and NTU
    states no language condition for it. It must stay unrequired.

    NTU's Bachelor of Arts (Hons) in Chinese does set one, so name-matching
    would have got that pair right by luck and this pair wrong. The rule is to
    read the university's own entry requirements, which is why both ids are
    pinned here by hand.
    """
    lms = pack.outcomes["ntu-linguistics-multilingual-studies"]
    assert lms.language_requirement is None, (
        "NTU states no language condition for Linguistics and Multilingual "
        "Studies; adding one blocks a course for students entitled to it"
    )

    chinese = pack.outcomes["ntu-chinese"]
    assert chinese.language_requirement is not None, (
        "NTU sets a Chinese subject condition for BA Chinese; it must be recorded"
    )
    # NTU does not state a language of instruction for BA Chinese, only for
    # Chinese Medicine. The two must not be levelled up to each other.
    assert chinese.language_requirement.taught_in_language is False, (
        "NTU does not say BA Chinese is taught in Chinese; do not assert it"
    )
    med = pack.outcomes["ntu-chinese-medicine"]
    assert med.language_requirement is not None
    assert med.language_requirement.taught_in_language is True, (
        "NTU calls Chinese Medicine a bilingual course with Mandarin as a "
        "medium of instruction; that is the fact that decides livability"
    )


def _all_facts(outcome):
    """Every Fact hanging off one outcome, wherever it lives."""
    out = []
    for holder in (outcome.band, outcome.cost, outcome.employment, outcome.flexibility,
                   outcome.editorial, outcome.poly_gpa, outcome.language_requirement):
        f = getattr(holder, "fact", None)
        if f is not None:
            out.append(f)
    if outcome.intake is not None:
        out.append(outcome.intake)
    for b in outcome.banded:
        if b.fact is not None:
            out.append(b.fact)
    return out


def test_every_figure_can_be_checked_against_its_own_source(pack):
    """A citation a reader cannot click is not a citation.

    This project's whole claim is that every number is traceable, and until
    now that was true at the level of a SOURCE list at the bottom of the page.
    A reader looking at one fee wants the page that fee came from, next to the
    fee. Every fact must therefore resolve to a URL — its own if it has one,
    otherwise its source's, which is the common case and perfectly fine: the
    same link beside twenty figures is still twenty figures someone can check.
    """
    unresolvable = []
    for o in pack.outcomes.values():
        for f in _all_facts(o):
            if f.citation_url(pack) is None:
                unresolvable.append(f"{o.id}:{f.source_id}")
    assert not unresolvable, (
        f"{len(unresolvable)} figures cannot be checked by a reader, e.g. "
        f"{unresolvable[:5]}"
    )


def test_a_source_that_is_many_pages_cites_the_page_not_the_listing(pack):
    """Singapore Polytechnic is the case this exists for.

    Its aggregate ranges live on thirty-four separate course pages. Citing the
    course LISTING for all of them would send a reader to a page that does not
    even render the courses without JavaScript and ask them to go and find the
    number. Each SP band therefore carries its own page, and the fallback to
    the source URL must not quietly swallow that.
    """
    sp = [o for o in pack.outcomes.values()
          if o.institution_short == "SP" and o.band is not None]
    assert len(sp) >= 30, f"only {len(sp)} SP courses with a band"
    for o in sp:
        url = o.band.fact.url
        assert url, f"{o.id}: band cites the listing rather than its own page"
        assert url.startswith("https://www.sp.edu.sg/courses/schools/"), f"{o.id}: {url}"
        assert o.url == url, (
            f"{o.id}: the course's own link and its band citation disagree"
        )
    # And they must be distinct pages, not the same one repeated.
    assert len({o.band.fact.url for o in sp}) >= 30, "SP citations collapsed to one page"


def test_a_description_shared_by_many_courses_is_the_exception_not_the_rule(pack):
    """Two courses with identical text are identical to the scorer.

    This is the mechanism behind the saturation seen in testing: twelve
    courses tied at 100 because family-level editorial made them
    indistinguishable. It is also what let a Chinese-medium diploma read as a
    generic media course. Singapore Polytechnic is now written per course and
    is the worked example; this pins it so a later regeneration cannot quietly
    drop back to the family text.
    """
    sp = [o for o in pack.outcomes.values() if o.institution_short == "SP"]
    assert len(sp) >= 30, f"only {len(sp)} SP courses"
    summaries = [o.editorial.summary for o in sp if o.editorial and o.editorial.summary]
    assert len(summaries) == len(sp), "an SP course has no description at all"
    assert len(set(summaries)) == len(sp), (
        f"SP has {len(set(summaries))} distinct descriptions for {len(sp)} courses; "
        f"per-course text has regressed to family level"
    )
    # And they must actually say something, not be a stub.
    for o in sp:
        assert len(o.editorial.summary) >= 60, f"{o.id}: description is a stub"


def test_the_new_course_parameters_each_carry_a_source(pack):
    """Duration, accreditation and progression are claims, not decoration.

    Duration multiplies a fee. Accreditation decides whether someone may
    lawfully practise. Progression is why a family picks a diploma at all.
    None of them may sit on a card without something a reader can check.
    """
    for o in pack.outcomes.values():
        if o.duration is not None:
            assert o.duration.years and 1 <= o.duration.years <= 8, (
                f"{o.id}: implausible duration {o.duration.years}")
            assert o.duration.fact is not None, f"{o.id}: duration with no source"
            assert o.duration.fact.citation_url(pack), f"{o.id}: duration not checkable"
        for a in o.accreditation:
            assert a.body and a.label, f"{o.id}: accreditation missing body or label"
            assert a.fact is not None, f"{o.id}: accreditation with no source"
            assert a.fact.citation_url(pack), f"{o.id}: accreditation not checkable"
        for p in o.progression:
            assert p.label, f"{o.id}: progression with no destination"
            assert p.fact is not None, f"{o.id}: progression with no source"


def test_accreditation_is_claimed_only_where_a_register_exists(pack):
    """A licensing claim is the most consequential thing on a course page.

    Claiming one that does not exist would send someone into a course
    believing it opens a register it does not. So the bodies named here are a
    closed set, and a new one has to be added deliberately.
    """
    known = {
        "Singapore Nursing Board",
        "Singapore Dental Council",
        "Optometrists and Opticians Board",
    }
    for o in pack.outcomes.values():
        for a in o.accreditation:
            assert a.body in known, (
                f"{o.id} claims accreditation by {a.body!r}, which is not in the "
                f"reviewed set. Adding a licensing body is a deliberate act — "
                f"check the regulator's own remit first."
            )
    accredited = [o.id for o in pack.outcomes.values() if o.accreditation]
    assert accredited, "no course carries accreditation; the field is doing nothing"


def test_the_student_sets_the_weights_not_pathahead(pack, fam):
    """The point of the rewrite, as an assertion.

    The old scorer gave interests 25 points and working style 10 — asserting,
    with nothing behind it, that what a student is drawn to matters two and a
    half times more than who they work with. That is a value judgement, and it
    belongs to the person making the decision.
    """
    from engine.fit import dimension_weights

    o = pack.outcomes["nus-computer-science"]
    base = dict(interests=("I",), enjoyed_subjects=("mathematics",),
                assessment_style="exams", teamwork="individual")

    # Nothing ranked -> everything equal, and that default is REAL, not hidden.
    flat = StudentProfile(**base)
    assert set(dimension_weights(flat).values()) == {1.0}

    # Ranked -> first place counts most, last counts least, linearly.
    ranked = StudentProfile(**base, importance=(("teamwork", 3), ("interests", 2), ("subjects", 1)))
    w = dimension_weights(ranked)
    assert w["teamwork"] == 3.0 and w["interests"] == 2.0 and w["subjects"] == 1.0
    # Ties are allowed, because "these two matter the same" is a real answer
    # that a strict ordering would have forced someone to break arbitrarily.
    tied = StudentProfile(**base, importance=(("teamwork", 3), ("interests", 3)))
    tw = dimension_weights(tied)
    assert tw["teamwork"] == tw["interests"] == 3.0

    # Raising something's importance must not lower its contribution.
    a = {f.dimension: f for f in score_outcome(o, flat, families=fam).factors}
    b = {f.dimension: f for f in score_outcome(o, ranked, families=fam).factors}
    if "teamwork" in a and "teamwork" in b:
        assert b["teamwork"].points >= a["teamwork"].points, (
            "raising a dimension's importance reduced what it contributed"
        )


def test_a_dimension_set_to_does_not_matter_counts_for_nothing(pack, fam):
    """"This does not matter to me" has to mean nothing, or it is not an answer.

    Scoring it at a low weight instead would keep a course the student does not
    care about quietly nudging their list.
    """
    o = pack.outcomes["nus-computer-science"]
    p = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",),
        assessment_style="exams", teamwork="individual",
        importance=(("interests", 3),),        # everything else left at 0
    )
    fit = score_outcome(o, p, families=fam)
    dims = {f.dimension for f in fit.factors}
    assert dims == {"interests"}, f"unranked dimensions still scored: {dims}"
    # ...and it left the denominator too, so the score is not dragged down.
    assert fit.score == 100 or all(f.match < 1.0 for f in fit.factors), (
        "an unranked dimension is still in the denominator"
    )


def test_every_factor_can_be_read_as_match_times_weight(pack, fam):
    """The card claims `match x weight = points`. It must actually be true."""
    o = pack.outcomes["nus-computer-science"]
    p = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",),
        assessment_style="exams", teamwork="individual",
        importance=(("interests", 3), ("subjects", 2), ("assessment", 1), ("teamwork", 1)),
    )
    for f in score_outcome(o, p, families=fam).factors:
        assert 0.0 <= f.match <= 1.0, f"{f.dimension}: match {f.match} out of range"
        assert f.weight > 0, f"{f.dimension}: a scored factor with no weight"
        assert f.max_points == f.weight, f"{f.dimension}: max is not the weight"
        assert abs(f.points - round(f.match * f.weight, 1)) < 0.05, (
            f"{f.dimension}: {f.match} x {f.weight} != {f.points}"
        )


def test_weighting_earnings_cannot_promote_courses_on_missing_data(pack, fam):
    """The guard on SAFEGUARDS 5.1.

    Only 12 of 330 courses hold salary data. If a course without it were scored
    zero on earnings, ranking earnings first would push the 12 that happen to
    have data up the list — a pay ranking arrived at by accident of coverage.
    """
    p = StudentProfile(
        interests=("I",), enjoyed_subjects=("mathematics",),
        priorities=("earnings",), importance=(("earnings", 3), ("interests", 1)),
    )
    for o in pack.outcomes.values():
        fit = score_outcome(o, p, families=fam)
        earn = [f for f in fit.factors if f.dimension == "earnings"]
        if earn and not (o.employment and o.employment.gross_median):
            raise AssertionError(
                f"{o.id}: scored on earnings without published salary data"
            )


def test_published_fee_tiers_are_internally_consistent(pack):
    """Citizen < PR < international < non-subsidised, every time. A tier out of
    order means a transcription error, and families make real decisions on it."""
    for o in pack.outcomes.values():
        c = o.cost
        if not (c and c.annual_fee_citizen):
            continue
        tiers = [c.annual_fee_citizen, c.annual_fee_pr, c.annual_fee_international,
                 c.annual_fee_is_other, c.annual_fee_no_grant]
        tiers = [t for t in tiers if t]
        assert tiers == sorted(tiers), f"{o.id}: fee tiers out of order {tiers}"
        assert c.years and 3 <= c.years <= 6, f"{o.id}: implausible duration {c.years}"


def test_per_credit_fee_tiers_are_internally_consistent(pack):
    """The same transcription check for the institution that charges per credit.

    SIT's table has five columns per programme and it is exactly the kind of
    table where a column slips. A tier out of order here is a four-figure error
    in a number a family plans around.
    """
    checked = 0
    for o in pack.outcomes.values():
        c = o.cost
        if not (c and c.fee_basis == "per_credit"):
            continue
        checked += 1
        tiers = [c.fee_per_credit_citizen, c.fee_per_credit_pr,
                 c.fee_per_credit_international, c.fee_per_credit_is_other,
                 c.fee_per_credit_no_grant]
        tiers = [t for t in tiers if t]
        assert tiers == sorted(tiers), f"{o.id}: per-credit tiers out of order {tiers}"
        assert c.total_credits and 100 <= c.total_credits <= 300, (
            f"{o.id}: implausible credit total {c.total_credits}"
        )
        # And the derived total has to land somewhere a degree actually costs.
        total = c.total_for("citizen")
        assert total and 15_000 <= total <= 60_000, f"{o.id}: implausible total {total}"
    assert checked > 0, "no per-credit programme in the pack; this test proves nothing"


def test_a_per_credit_programme_never_claims_an_annual_fee(pack):
    """SIT publishes no annual figure, and inventing one is the tempting move.

    Dividing a programme total by a nominal number of years would produce a
    number that looks exactly like NUS's and is wrong for any student taking a
    lighter or heavier load -- which is the whole reason SIT charges this way.
    The loader refuses it; this pins the pack itself.
    """
    for o in pack.outcomes.values():
        c = o.cost
        if c and c.fee_basis == "per_credit":
            assert not c.annual_fee_citizen, f"{o.id}: invented an annual fee"
            assert not c.annual_fee_pr, f"{o.id}: invented an annual PR fee"


def test_a_missing_fee_that_is_a_decision_says_why(pack):
    """A blank cost cell reads as "not loaded yet" and invites a later session
    to fill it in from the nearest plausible number.

    SIT lists Civil Engineering and Nursing twice, at different credit loads and
    different rates, and this pack does not record which partner each course is
    with. Those gaps are decisions, and they carry their reason.
    """
    explained = [o for o in pack.outcomes.values() if o.fee_note]
    assert explained, "no course records why its fee is absent"
    for o in explained:
        assert not (o.cost and o.cost.has_any_fee), (
            f"{o.id}: has both a fee and a note explaining why it has none"
        )
        assert len(o.fee_note) > 60, f"{o.id}: the reason is too thin to act on"


def test_the_tuition_grant_bond_is_never_silently_dropped(pack):
    """Families discover the bond late. It must travel with every fee."""
    for o in pack.outcomes.values():
        c = o.cost
        if c and c.annual_fee_citizen:
            assert c.bond_note and "3 years" in c.bond_note, o.id
            assert c.bond_years_citizen == 0 or c.bond_years_citizen >= 4, o.id
            assert c.bond_years_pr_is >= 3, o.id


def test_no_factor_is_ever_scored_zero_because_of_our_own_gap(pack, fam):
    """A zero must always mean a genuine mismatch the student would recognise,
    never 'PathAhead has not loaded this yet'."""
    ours = ("no published", "does not carry", "not loaded", "no figure", "no fee")
    for name, profile in REALISTIC.items():
        for outcome in pack.outcomes.values():
            for f in score_outcome(outcome, profile, families=fam).factors:
                if f.points == 0:
                    assert not any(
                        phrase in f.reason.lower() for phrase in ours
                    ), f"{name}/{outcome.id}: zero blamed on our data — {f.reason}"


# --- 1b. the evidence axis must actually discriminate ---------------------


def test_the_evidence_axis_does_not_collapse_into_one_bucket(pack):
    """A top student once got the SAME verdict for all 21 courses, because
    three A grades summed to the ceiling for 18 of them. Medicine and
    Landscape Architecture rendered identically."""
    from engine import GradeSheet, explore

    top = GradeSheet.parse("a-level", ["h2 A=A", "h2 B=A", "h2 C=A", "gp GP=A"])
    buckets = explore(pack, year_level="jc-2", current_year=2026, grades=top).by_bucket()
    assert len(buckets) >= 3, (
        f"a top student got only {len(buckets)} distinct verdict(s) across "
        f"{len(pack.outcomes)} courses — the axis has collapsed again"
    )
    biggest = max(len(v) for v in buckets.values())
    assert biggest < len(pack.outcomes) * 0.8, "one bucket swallowed nearly everything"


def test_a_saturated_profile_reads_differently_from_a_wide_one(pack):
    """The distinction that was lost: level with Medicine, clear of Landscape
    Architecture — the same grades, two genuinely different situations."""
    from engine import Bucket, GradeSheet, explore

    top = GradeSheet.parse("a-level", ["h2 A=A", "h2 B=A", "h2 C=A", "gp GP=A"])
    results = {
        r.outcome.id: r.assessment.bucket
        for r in explore(pack, year_level="jc-2", current_year=2026, grades=top).results
    }
    assert results["nus-medicine"] is Bucket.EXACTLY_AT_PROFILE
    assert results["nus-landscape-architecture"] is Bucket.ABOVE_RANGE


def test_being_level_with_a_profile_says_what_else_decides_it(pack):
    """No headroom means the non-grade parts decide. Say so, kindly."""
    from engine.buckets import EXPLANATION, Bucket

    text = EXPLANATION[Bucket.EXACTLY_AT_PROFILE].lower()
    assert "no headroom" in text
    assert "interviews" in text and "portfolios" in text


# --- 2. answering more must never hurt ------------------------------------


@pytest.mark.parametrize("outcome_id", ["nus-computer-science", "nus-nursing", "nus-architecture"])
def test_naming_more_interests_never_lowers_the_score(pack, fam, outcome_id):
    outcome = pack.outcomes[outcome_id]
    base = ("I",)
    previous = None
    for extra in ((), ("R",), ("R", "C")):
        p = StudentProfile(interests=base + extra, enjoyed_subjects=("mathematics",))
        got = score_outcome(outcome, p, families=fam).score
        if previous is not None:
            assert got >= previous, (
                f"{outcome_id}: naming {len(base + extra)} interests scored {got}, "
                f"below {previous} for fewer — honesty must not be punished"
            )
        previous = got


@pytest.mark.parametrize("outcome_id", ["nus-computer-science", "nus-humanities-sciences"])
def test_naming_more_enjoyed_subjects_never_lowers_the_score(pack, fam, outcome_id):
    outcome = pack.outcomes[outcome_id]
    previous = None
    for subjects in (
        ("mathematics",),
        ("mathematics", "physics"),
        ("mathematics", "physics", "art", "history"),
    ):
        p = StudentProfile(interests=("I",), enjoyed_subjects=subjects)
        got = score_outcome(outcome, p, families=fam).score
        if previous is not None:
            assert got >= previous, f"{outcome_id}: listing more subjects lowered the score"
        previous = got


# --- 3. the output has to mean something ----------------------------------


@pytest.mark.parametrize("name", list(REALISTIC))
def test_every_realistic_student_has_something_that_suits_them(pack, name):
    """No student may be told that nothing in the pack overlaps with them.
    The shipped version topped out at 49 for a real profile."""
    _lo, hi, _all = _spread(pack, REALISTIC[name])
    assert hi >= 50, (
        f"{name}: highest fit anywhere was {hi}. A student reading 21 cards all "
        f"below 50 concludes the problem is her."
    )


@pytest.mark.parametrize("name", list(REALISTIC))
def test_fit_discriminates_across_the_pack(pack, name):
    """If every course scores the same, the axis is decoration."""
    lo, hi, _ = _spread(pack, REALISTIC[name])
    assert hi - lo >= 20, f"{name}: spread {lo}-{hi} is too flat to be useful"


def test_different_students_get_genuinely_different_shortlists(pack):
    def top3(profile):
        ranked = sorted(
            (s for s in score_all(pack, profile, "a-level-to-university-2026").values()
             if s.score is not None),
            key=lambda s: -s.score,
        )
        return {s.outcome_id for s in ranked[:3]}

    a = top3(REALISTIC["sciences-caring"])
    b = top3(REALISTIC["humanities-writer"])
    assert a != b, "two very different students got the same top three"


def test_the_regression_that_shipped(pack, fam):
    """The exact session that upset a child. Further Mathematics must count."""
    her = REALISTIC["further-maths-and-design"]
    fit = score_outcome(pack.outcomes["nus-computer-science"], her, families=fam)
    subjects = [f for f in fit.factors if f.source == "enjoyed_subjects"]
    assert subjects and subjects[0].points > 0, (
        "Further Mathematics scored zero on a mathematics-heavy course"
    )
    _lo, hi, _ = _spread(pack, her)
    assert hi >= 60, f"her best match was only {hi}"


# --- 4. nothing may read as a judgement about the student -----------------

#: Words that describe a person rather than an overlap between a person and a
#: course description written by a stranger.
JUDGEMENTAL = ("weak", "poor", "bad", "unsuitable", "unsuited", "not good", "failing", "low ability")


def test_band_labels_describe_the_match_not_the_person(pack, fam):
    seen = set()
    for _name, profile in REALISTIC.items():
        for outcome in pack.outcomes.values():
            seen.add(score_outcome(outcome, profile, families=fam).band)
    for band in seen:
        for word in JUDGEMENTAL:
            assert word not in band.lower(), f"band {band!r} judges the student"


def test_no_factor_wording_judges_the_student(pack, fam):
    for profile in REALISTIC.values():
        for outcome in pack.outcomes.values():
            fit = score_outcome(outcome, profile, families=fam)
            for f in fit.factors:
                for word in JUDGEMENTAL:
                    assert word not in f.reason.lower(), f"{f.label}: {f.reason}"


def test_a_zero_scoring_factor_still_explains_itself_kindly(pack, fam):
    """A mismatch must read as a difference between two things, not a deficit."""
    p = StudentProfile(
        interests=("S",), enjoyed_subjects=("literature",), teamwork="individual"
    )
    fit = score_outcome(pack.outcomes["nus-medicine"], p, families=fam)
    zeros = [f for f in fit.factors if f.points == 0]
    for f in zeros:
        assert "you" in f.reason.lower(), f"{f.label} does not connect back to the student"
        assert not f.reason.lower().startswith("you do not"), f.label


# --- 5. subject families ---------------------------------------------------


def test_further_mathematics_counts_as_mathematics(pack, fam):
    assert fam["further-mathematics"] == "mathematics"
    cs = pack.outcomes["nus-computer-science"]
    plain = score_outcome(
        cs, StudentProfile(interests=("I",), enjoyed_subjects=("mathematics",)), families=fam
    )
    further = score_outcome(
        cs,
        StudentProfile(interests=("I",), enjoyed_subjects=("further-mathematics",)),
        families=fam,
    )
    assert plain.score == further.score


def test_every_subject_family_points_at_a_real_subject(pack):
    codes = {s["code"] for s in pack.subjects}
    for s in pack.subjects:
        assert s.get("family", s["code"]) in codes, f"{s['code']} has a dangling family"


# --- 5. a gap we chose must stay a gap, not drift into a guess -------------

def test_ntus_lab_split_is_left_empty_rather_than_guessed(pack):
    """NTU publishes two non-subsidised rates for its general band -- SGD 40,600
    lab-based and SGD 36,350 non-lab-based -- and publishes no mapping from
    programme to cluster.

    Filling that field means inventing the classification NTU withheld, and a
    wrong call is roughly a SGD 17,000 error across four years for a family
    paying non-subsidised fees. So the field stays empty and the note names
    both figures. This test exists so a later session cannot quietly tidy the
    gap away.
    """
    checked = 0
    for o in pack.outcomes.values():
        c = o.cost
        if not (c and c.fee_group and c.fee_group.startswith("All Programmes")):
            continue
        checked += 1
        assert c.annual_fee_no_grant is None, (
            f"{o.id}: a no-grant fee appeared for NTU's general band. NTU does "
            f"not publish which programmes are lab-based; if that changed, cite "
            f"the source in the fact note before filling this in."
        )
        note = (c.fact.note or "") if c.fact else ""
        assert "40,600" in note and "36,350" in note, (
            f"{o.id}: the note must still name both published figures, so a "
            f"reader can work out their own case."
        )
    assert checked >= 30, "the NTU general band vanished; this test stopped guarding anything"


def test_ntu_accountancy_and_business_stay_three_year_programmes(pack):
    """Assuming four years is the natural mistake here, and it overstates the
    bill by a full year of fees. NTU's Academic Handbook puts the normal
    candidature for both at three years."""
    for cid in ("ntu-accountancy", "ntu-business"):
        c = pack.outcomes[cid].cost
        assert c and c.years == 3, f"{cid}: expected a 3-year candidature, got {c and c.years}"
        assert c.total_for("citizen") == 28500, cid


def test_a_course_with_no_fee_figure_says_so_rather_than_showing_zero(pack):
    """Two NTU programmes have no published normal candidature we could find,
    so they carry no cost block at all. An absent fee must stay absent -- never
    a zero, which a family would read as free."""
    for o in pack.outcomes.values():
        if o.cost is None:
            continue
        assert o.cost.annual_fee_citizen != 0, f"{o.id}: zero is not a fee"
        assert o.cost.years != 0, f"{o.id}: zero is not a duration"


# ---------------------------------------------------------------------------
# Subject prerequisites
#
# Reported by a parent looking at the real site: NTU's Physics / Applied
# Physics came back 52 out of 100 for a student taking no Physics at all. The
# score was not merely optimistic -- it was an answer to a question fit scoring
# is not allowed to be asked. Fifty-two still ranks that course above two
# hundred others the student could walk into tomorrow.
#
# The identical bug had already been found and fixed once, on a Chinese-medium
# diploma, which is why the language test above exists. Language turned out to
# be the rare case and subjects the common one, and the fix was never
# generalised. These tests are here so it cannot un-generalise again.
# ---------------------------------------------------------------------------


def test_a_student_with_no_physics_is_never_shown_a_score_on_applied_physics(pack, fam):
    o = pack.outcomes["ntu-physics-applied-physics"]
    assert o.subject_requirements, (
        "NTU publishes 'H2 Level pass in Physics, and H2 Level pass in "
        "Mathematics' for this programme. Without it loaded the engine has "
        "nothing to check and scores the course anyway."
    )
    p = StudentProfile(
        interests=("investigative",),
        subjects_offered=("mathematics", "economics", "literature"),
        assessment_style="exams",
        teamwork="alone",
    )
    fit = score_outcome(o, p, families=fam)
    assert fit.score is None, (
        f"scored {fit.score} for a student with no Physics. A number here is "
        "worse than silence: it ranks a closed door against open ones."
    )
    assert "Physics" in (fit.unscored_reason or ""), (
        "the reason must name the subject, or the student cannot act on it"
    )


def test_the_requirement_is_quoted_from_the_institution_not_paraphrased(pack):
    o = pack.outcomes["ntu-physics-applied-physics"]
    labels = [r.label for r in o.subject_requirements]
    assert "H2 Level pass in Physics" in labels, (
        "a rewritten entry condition is how a family applies for something "
        "they cannot take; the student must read NTU's own words"
    )
    for r in o.subject_requirements:
        assert r.fact is not None and r.fact.source_id, f"{r.label}: uncited"


def test_further_mathematics_satisfies_a_mathematics_requirement(pack, fam):
    """Folding onto families is not a nicety -- it is the difference between
    a correct block and a confidently wrong one."""
    o = pack.outcomes["ntu-mathematical-sciences"]
    assert any("Mathematics" in (r.label or "") for r in o.subject_requirements)
    p = StudentProfile(
        interests=("investigative",),
        subjects_offered=("further-mathematics", "physics", "chemistry"),
        assessment_style="exams",
        teamwork="alone",
    )
    fit = score_outcome(o, p, families=fam)
    assert fit.score is not None, (
        "told a student taking Further Mathematics that they do not take "
        f"Mathematics: {fit.unscored_reason}"
    )


def test_not_being_told_the_subjects_is_not_treated_as_not_having_them(pack, fam):
    """Our missing answer must read as 'come back and tell me', never as 'no'."""
    o = pack.outcomes["ntu-physics-applied-physics"]
    p = StudentProfile(
        interests=("investigative",),
        enjoyed_subjects=("economics",),
        assessment_style="exams",
        teamwork="alone",
    )
    fit = score_outcome(o, p, families=fam)
    assert fit.score is None
    reason = fit.unscored_reason or ""
    assert "has not been told" in reason, reason
    assert "not among the subjects" not in reason, (
        "silence was reported as a refusal"
    )


def test_a_grade_condition_on_general_paper_never_blocks_anybody(pack):
    """NTU asks for 'a good grade in General Paper' on dozens of programmes.
    Nearly every A-Level candidate sits GP, and PathAhead does not hold
    grades -- encoding that as a gate would block almost everyone on a
    condition almost everyone meets."""
    for o in pack.outcomes.values():
        for r in o.subject_requirements:
            joined = " ".join(r.subjects).lower()
            assert "general-paper" not in joined and "general paper" not in joined, (
                f"{o.id}: gating on General Paper"
            )
            assert "knowledge" not in joined, f"{o.id}: gating on Knowledge & Inquiry"


def test_courses_with_a_requirement_are_listed_not_hidden(pack, fam):
    """A course removed silently is one a family never gets to argue with."""
    gated = [o for o in pack.outcomes.values() if o.subject_requirements]
    assert len(gated) >= 30, f"only {len(gated)} courses carry requirements"
    p = StudentProfile(interests=("artistic",), subjects_offered=("literature",))
    for o in gated:
        fit = score_outcome(o, p, families=fam)
        assert fit.outcome_id == o.id, "a gated course dropped out of the result"
        if fit.score is None:
            assert fit.unscored_reason, f"{o.id}: unscored with no explanation"

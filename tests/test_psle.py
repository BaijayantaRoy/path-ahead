"""The PSLE stage: scoring, Foundation subjects, and Posting Groups.

Two of these tests guard rules that cost something real elsewhere in this
project, transplanted to a stage where the person on the other end is twelve:

  * **Eligibility is not a low score** (docs/decisions/0003). A Posting Group
    is a gate. If anything here ever returns a rankable number, that is the bug.

  * **The absence of a constraint is not the same as its absence in reality.**
    MOE's published table stops at 30. PathAhead must say what is published and
    stop, rather than inventing a fourth group or reporting "no group", which a
    parent reads as "no school".
"""

from __future__ import annotations

import pytest

from engine import GradeSheet
from engine.errors import InputError, RuleError
from engine.forward import score
from engine.posting import resolve_posting_group

TRANSITION = "psle-to-secondary-2026"


@pytest.fixture
def psle(pack):
    return pack.transitions[TRANSITION]


def sheet(**grades: str) -> GradeSheet:
    """Build a PSLE grade sheet from keyword arguments.

    Written the way a person enters results, not the way the pack stores them:
    `sheet(english="AL3", mathematics="1")` mixes the two spellings a real
    parent uses within one call, on purpose.
    """
    codes = {
        "english": ("psle-english", "English Language"),
        "mathematics": ("psle-mathematics", "Mathematics"),
        "science": ("psle-science", "Science"),
        "mtl": ("psle-mtl", "Mother Tongue Language"),
        "english_f": ("psle-english-foundation", "Foundation English Language"),
        "mathematics_f": ("psle-mathematics-foundation", "Foundation Mathematics"),
        "science_f": ("psle-science-foundation", "Foundation Science"),
        "mtl_f": ("psle-mtl-foundation", "Foundation Mother Tongue Language"),
    }
    rows = []
    for key, grade in grades.items():
        code, name = codes[key]
        rows.append({"code": code, "name": name, "level": "subject", "grade": grade})
    return GradeSheet.from_dicts("psle", rows)


# ---------------------------------------------------------------- scoring


def test_the_score_is_the_sum_of_four_achievement_levels(pack, psle):
    d = score(pack, sheet(english="AL3", mathematics="AL1", science="AL2", mtl="AL2"), psle)
    assert d.value == 8
    assert d.direction == "lower_is_better"


def test_al_prefix_is_optional_because_people_type_both(pack, psle):
    with_prefix = score(pack, sheet(english="AL4", mathematics="AL4", science="AL4", mtl="AL4"), psle)
    without = score(pack, sheet(english="4", mathematics="4", science="4", mtl="4"), psle)
    assert with_prefix.value == without.value == 16


def test_the_best_possible_score_is_four_not_zero(pack, psle):
    d = score(pack, sheet(english="AL1", mathematics="AL1", science="AL1", mtl="AL1"), psle)
    assert d.value == 4


def test_the_weakest_possible_score_is_thirty_two(pack, psle):
    d = score(pack, sheet(english="AL8", mathematics="AL8", science="AL8", mtl="AL8"), psle)
    assert d.value == 32


def test_a_missing_subject_is_an_error_with_advice_never_a_silent_zero(pack, psle):
    with pytest.raises(RuleError) as exc:
        score(pack, sheet(english="AL3", mathematics="AL3", science="AL3"), psle)
    assert "Mother Tongue" in str(exc.value)


def test_a_grade_this_exam_does_not_use_is_rejected_with_advice(pack):
    for not_a_psle_grade in ("D", "E", "AL9", "0", "U"):
        with pytest.raises(InputError) as exc:
            sheet(english=not_a_psle_grade)
        assert "AL1 to AL8" in (exc.value.advice or "")


def test_a_bare_letter_is_read_as_a_foundation_grade_and_this_is_a_known_limitation(pack, psle):
    """Documenting real behaviour rather than an intention.

    At PSLE a bare "A", "B" or "C" is a Foundation grade, so the normaliser
    accepts it as one -- it cannot tell from the letter alone whether the
    parent meant a Foundation subject. Entering "B" against *Standard* English
    therefore scores AL7 rather than erroring.

    In the app this cannot happen: the subject is chosen from a list, and
    Foundation subjects are separate entries. Via the CLI it can. The gap is
    small and it is recorded here rather than left for someone to rediscover;
    closing it means cross-checking the grade against the subject's own level,
    which is a change to `grades.py`, not to this stage.
    """
    d = score(pack, sheet(english="B", mathematics="AL1", science="AL1", mtl="AL1"), psle)
    assert d.value == 10  # 7 + 1 + 1 + 1


# ------------------------------------------------------------- foundation


def test_a_foundation_subject_satisfies_the_standard_requirement(pack, psle):
    """The sheet is complete. Reporting a missing subject here would be wrong,
    and to the parent reading it, it reads as an accusation about their child."""
    d = score(pack, sheet(english="AL5", mathematics_f="A", science="AL6", mtl="AL7"), psle)
    assert d.value == 24  # 5 + 6 + 6 + 7


def test_foundation_grades_map_to_al6_al7_al8(pack, psle):
    a = score(pack, sheet(english_f="A", mathematics_f="A", science_f="A", mtl_f="A"), psle)
    b = score(pack, sheet(english_f="B", mathematics_f="B", science_f="B", mtl_f="B"), psle)
    c = score(pack, sheet(english_f="C", mathematics_f="C", science_f="C", mtl_f="C"), psle)
    assert (a.value, b.value, c.value) == (24, 28, 32)


def test_a_foundation_grade_is_never_shown_as_its_internal_spelling(pack, psle):
    """Foundation A is normalised to "FA" so it cannot collide with a Standard
    A. That spelling is ours and must never reach a family."""
    d = score(pack, sheet(english_f="A", mathematics="AL5", science="AL5", mtl="AL5"), psle)
    labels = " ".join(s.label for s in d.steps)
    assert "FA" not in labels
    assert "Foundation A" in labels


def test_the_trace_says_where_a_mapped_foundation_number_came_from(pack, psle):
    d = score(pack, sheet(english_f="A", mathematics="AL5", science="AL5", mtl="AL5"), psle)
    details = [s.detail for s in d.steps if s.detail]
    assert any("counts as AL6" in x for x in details)


# ---------------------------------------------------------- posting groups


@pytest.mark.parametrize(
    ("psle_score", "expected"),
    [(4, (3,)), (12, (3,)), (20, (3,)), (21, (2, 3)), (22, (2, 3)),
     (23, (2,)), (24, (2,)), (25, (1, 2)), (26, (1,)), (30, (1,))],
)
def test_the_published_table_is_reproduced_exactly(psle, psle_score, expected):
    got = resolve_posting_group(
        psle, psle_score, subject_als={"psle-english": 4, "psle-mathematics": 4}
    )
    assert got.groups == expected


def test_two_groups_is_a_choice_and_it_applies_to_all_six_school_choices(psle):
    got = resolve_posting_group(psle, 21, subject_als={})
    assert got.is_a_choice
    assert got.choice_applies_to_all_six


def test_submitting_nothing_assigns_the_more_demanding_group(psle):
    assert resolve_posting_group(psle, 21, subject_als={}).default_group == 3
    assert resolve_posting_group(psle, 25, subject_als={}).default_group == 2


def test_the_26_to_30_row_requires_al7_in_english_and_maths(psle):
    met = resolve_posting_group(psle, 28, subject_als={"psle-english": 7, "psle-mathematics": 6})
    assert met.groups == (1,)
    unmet = resolve_posting_group(psle, 28, subject_als={"psle-english": 8, "psle-mathematics": 6})
    assert unmet.is_outside_table


def test_an_unasked_condition_is_reported_not_assumed(psle):
    """Nothing was asked about English and Maths, so nothing may be concluded.
    The result names the condition rather than going silent -- a tool that
    quietly demotes a child over a question it never put is the failure this
    project exists to avoid."""
    got = resolve_posting_group(psle, 28)
    assert got.is_outside_table
    assert got.unmet_conditions
    assert "English Language" in got.unmet_conditions[0]


@pytest.mark.parametrize("psle_score", [31, 32])
def test_a_score_outside_the_table_gets_the_published_route_not_a_guess(psle, psle_score):
    got = resolve_posting_group(psle, psle_score, subject_als={})
    assert got.groups == ()
    assert got.outside_table is not None
    assert "different route" in got.outside_table["headline"]
    # Named schools, so the answer is actionable rather than a dead end.
    assert "NorthLight" in got.outside_table["body"]


def test_the_outside_table_answer_never_says_the_child_failed(psle):
    got = resolve_posting_group(psle, 32, subject_als={})
    text = (got.outside_table["headline"] + " " + got.outside_table["body"]).lower()
    for word in ("fail", "failed", "did not qualify", "not eligible", "unfortunately", "sorry"):
        assert word not in text, f"{word!r} has no place in what a parent reads here"


def test_a_posting_group_result_carries_no_number_that_was_not_published(psle):
    """A gate, not a score -- see docs/decisions/0003.

    The first version of this test flagged every scalar on the object and
    failed on `default_group`, which is a Posting Group NUMBER that MOE
    publishes, not something PathAhead computed. The blunt version would have
    forced a worse design to satisfy it.

    The rule that actually matters is narrower and is the one checked here:
    every number on this object is either the score the caller passed in or a
    Posting Group identifier that MOE published. Nothing is derived, so there
    is nothing here to rank a child by.
    """
    got = resolve_posting_group(psle, 12, subject_als={})
    published_group_numbers = {1, 2, 3}
    for name in got.__slots__:
        value = getattr(got, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        assert name == "score" or value in published_group_numbers, (
            f"{name} is a number PathAhead derived. A derived number gets sorted."
        )

    # And no field may even be NAMED like a score. A field called `rank` or
    # `fit` invites a UI to render it as one, whatever it holds today.
    for forbidden in ("rank", "fit", "percentile", "percent", "rating", "grade_of_child"):
        assert not any(forbidden in name for name in got.__slots__)


# ----------------------------------------------------------------- cohort


def test_a_primary_cohort_resolves_to_the_psle_rulebook(pack):
    for year_level in ("pri-5", "pri-6"):
        rule = pack.cohort_rules[year_level]
        assert rule.stage_id == "psle"
        assert rule.transition_id == TRANSITION


def test_the_psle_stage_no_longer_claims_to_be_unloaded(pack):
    """The stage description said 'Not yet loaded in this pack'. It is now, and
    a stale sentence in the one place a reader checks is worse than none."""
    assert "not yet loaded" not in pack.stages["psle"].description.lower()


# ------------------------------------------------------------ provenance


def test_every_psle_source_is_cited_and_licensed(pack):
    for source_id in (
        "moe-psle-scoring-2026",
        "moe-posting-groups-2026",
        "moe-s1-tiebreakers-2026",
        "moe-s1-posting-2026",
        "moe-s1-score-ranges-2026",
        "moe-dsa-sec-2026",
    ):
        src = pack.source(source_id)
        assert src.url.startswith("https://www.moe.gov.sg/")
        assert src.licence == "moe-tou"
        assert not src.redistributable, "MOE content is cited and linked, never mirrored"


def test_the_stale_school_types_page_is_marked_as_such(pack):
    """It was last updated in February 2021 and still uses pre-Full-SBB stream
    language. A source that is quietly out of date is worse than a missing one."""
    note = pack.source("moe-school-types-2021").note or ""
    assert "1 February 2021" in note
    assert "re-verify" in note.lower()


def test_the_tie_breaker_disagreement_between_two_moe_pages_is_recorded(pack, psle):
    """Two MOE pages disagree because one is stale. Picking one silently would
    throw away the only evidence that the question was ever examined."""
    caveats = " ".join(psle.caveats).lower()
    assert "tie-breaker" in caveats
    assert "2020" in caveats


def test_the_address_rule_is_recorded_before_anyone_builds_a_distance_feature(psle):
    posting = psle.rule_params["posting"]
    assert "NOT a tie-breaker" in posting["address_effect"]
    assert "Primary 1" in posting["address_effect"]


def test_the_dsa_commitment_is_stated_as_a_caveat_not_a_footnote(psle):
    caveats = " ".join(psle.caveats)
    assert "cannot submit" in caveats and "cannot transfer" in caveats

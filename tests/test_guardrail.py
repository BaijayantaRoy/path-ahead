"""Adversarial tests for the AI numeric guardrail.

The narrator (Tier 1) is optional and never ships enabled. But when it is on,
this is the mechanism that stops a language model inventing a cut-off point and
a parent believing it. These are the attacks it has to survive.
"""

from __future__ import annotations

import pytest

from engine import explore, narrate_safely
from engine.guardrail import check, extract_numbers


@pytest.fixture
def derivation(pack, strong_grades):
    return explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades).derivation


# --- the happy path ------------------------------------------------------


def test_narration_using_only_engine_numbers_passes(derivation):
    text = (
        "Your three best H2 subjects came to 57.5, General Paper added 10, "
        "and your Mother Tongue added 8.75, so the total was capped at 70."
    )
    assert check(text, derivation.numbers()).ok


def test_prose_with_no_numbers_at_all_passes(derivation):
    assert check("Your subjects together reached the maximum for this score.",
                 derivation.numbers()).ok


def test_a_difference_between_two_engine_numbers_is_allowed(derivation):
    # 70 - 57.5 = 12.5; the narrator may legitimately compute a gap.
    assert check("You were 12.5 short of the ceiling on H2 subjects alone.",
                 derivation.numbers()).ok


# --- the attacks ---------------------------------------------------------


def test_an_invented_cutoff_is_rejected(derivation):
    verdict = check("Most students admitted to Medicine scored at least 68.4.",
                    derivation.numbers())
    assert not verdict.ok
    assert 68.4 in verdict.offending


def test_an_invented_percentage_is_rejected(derivation):
    verdict = check("You have roughly a 73% chance of an offer.", derivation.numbers())
    assert not verdict.ok


def test_a_hallucinated_year_is_rejected(derivation):
    verdict = check("The 2019 profile for this course was lower.", derivation.numbers())
    assert not verdict.ok
    assert 2019 in verdict.offending


def test_a_plausible_but_unsourced_intake_figure_is_rejected(derivation):
    verdict = check("There are 240 places on this course.", derivation.numbers())
    assert not verdict.ok


def test_numbers_hidden_inside_words_are_still_caught(derivation):
    verdict = check("Aim for band 63.5 next year.", derivation.numbers())
    assert not verdict.ok


def test_one_bad_number_rejects_the_whole_narration(derivation):
    """Partial acceptance would be worse than rejection: the user cannot tell
    which sentence was the invented one."""
    text = "Your total was 70, and the cut-off is 66.5."
    verdict = check(text, derivation.numbers())
    assert not verdict.ok
    assert verdict.offending == (66.5,)


# --- the fallback --------------------------------------------------------


def test_rejected_narration_falls_back_to_the_template_silently(derivation):
    fallback = derivation.as_text()
    out, verdict = narrate_safely(
        "You need 68.9 for this course.", derivation.numbers(), fallback
    )
    assert not verdict.ok
    assert out == fallback, "the user must still get a correct, complete explanation"


def test_accepted_narration_is_passed_through(derivation):
    good = "Your three H2 subjects contributed 57.5 points."
    out, verdict = narrate_safely(good, derivation.numbers(), "fallback")
    assert verdict.ok
    assert out == good


# --- the extractor itself ------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("70", [70.0]),
        ("57.5 and 8.75", [57.5, 8.75]),
        ("no digits here", []),
        ("H2 Chemistry", []),          # a level name is not a number
        ("AY2025/2026", [2026.0]),     # 2025 is glued to letters; 2026 is bare
        ("you need at least 68.4.", [68.4]),   # sentence-final figure
        ("band 63.5, roughly", [63.5]),
        ("scored 60, needed 62", [60.0, 62.0]),
    ],
)
def test_number_extraction(text, expected):
    assert extract_numbers(text) == expected


def test_derivation_numbers_include_every_step_value(derivation):
    numbers = derivation.numbers()
    assert 70.0 in numbers          # the total
    assert 57.5 in numbers          # the H2 subtotal
    assert 20.0 in numbers          # an individual component
    assert 76.25 in numbers         # the uncapped figure, shown in the cap step

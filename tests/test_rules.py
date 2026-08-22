"""The arithmetic, and the trace that explains it.

A wrong number here is a wrong answer to a family, so these tests assert the
*steps* as well as the total: a score that happens to come out right via the
wrong route is still a bug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import GradeSheet, available_kinds
from engine.errors import InputError, RuleError
from engine.forward import score
from engine.trace import StepKind

REPO = Path(__file__).resolve().parent.parent


def _sheet(*entries: str) -> GradeSheet:
    return GradeSheet.parse("a-level", list(entries))


def _t(pack):
    return pack.transitions["a-level-to-university-2026"]


# --- the core shape ------------------------------------------------------


def test_three_h2_plus_gp_reaches_the_ceiling(pack):
    d = score(pack, _sheet("h2 A=A", "h2 B=A", "h2 C=A", "gp GP=A"), _t(pack))
    assert d.value == 70
    assert d.max_value == 70


def test_only_the_best_three_h2_count(pack):
    d = score(pack, _sheet("h2 A=A", "h2 B=A", "h2 C=A", "h2 D=A", "gp GP=A"), _t(pack))
    assert d.value == 70
    excluded = [s for s in d.steps if s.kind is StepKind.EXCLUDED]
    assert len(excluded) == 1, "the fourth H2 must be shown as considered-and-excluded"
    assert "best 3 count" in (excluded[0].detail or "")


def test_h1_is_worth_half_of_h2(pack):
    t = _t(pack)
    assert t.scales["h1"]["A"] * 2 == t.scales["h2"]["A"]
    assert t.scales["h1"]["B"] * 2 == t.scales["h2"]["B"]


def test_ungraded_scores_zero_rather_than_failing(pack):
    d = score(pack, _sheet("h2 A=C", "h2 B=D", "h2 C=U", "gp GP=E"), _t(pack))
    assert d.value == 15 + 12.5 + 0 + 5


# --- the substitution ----------------------------------------------------


def test_bonus_picks_the_higher_of_the_two_candidates(pack):
    d = score(
        pack,
        _sheet("h2 A=B", "h2 B=B", "h2 C=C", "gp GP=B", "h1 Maths=E", "mtl Malay=A"),
        _t(pack),
    )
    chosen = [s for s in d.steps if s.kind is StepKind.SUBSTITUTION]
    assert len(chosen) == 1
    assert "Malay" in chosen[0].label
    assert chosen[0].points == 10


def test_no_optional_subject_is_stated_not_silently_skipped(pack):
    d = score(pack, _sheet("h2 A=A", "h2 B=B", "h2 C=C", "gp GP=B"), _t(pack))
    notes = [s for s in d.steps if s.kind is StepKind.NOTE]
    assert any("No optional subject" in s.label for s in notes)


def test_cap_is_applied_and_announced(pack):
    d = score(
        pack,
        _sheet("h2 A=A", "h2 B=A", "h2 C=B", "gp GP=A", "mtl Chinese=B"),
        _t(pack),
    )
    caps = [s for s in d.steps if s.kind is StepKind.CAP]
    assert d.value == 70
    assert len(caps) == 1, "a cap that bites must appear in the trace"
    assert "76.25" in (caps[0].detail or ""), "the uncapped total must still be shown"
    assert any("capped" in w.lower() for w in d.warnings)


# --- the trace contract --------------------------------------------------


def test_every_score_carries_a_trace_ending_in_a_total(pack):
    d = score(pack, _sheet("h2 A=A", "h2 B=B", "h2 C=C", "gp GP=D"), _t(pack))
    assert d.steps, "a score without a trace is not an answer"
    assert d.steps[-1].kind is StepKind.TOTAL
    assert d.steps[-1].running_total == d.value


def test_running_total_is_monotonic_through_counted_components(pack):
    d = score(pack, _sheet("h2 A=A", "h2 B=B", "h2 C=C", "gp GP=D"), _t(pack))
    totals = [s.running_total for s in d.steps if s.running_total is not None]
    assert totals == sorted(totals), "the running total must never go backwards"


def test_trace_renders_without_raising(pack, strong_grades):
    text = score(pack, strong_grades, _t(pack)).as_text()
    assert "University Admission Score" in text
    assert "Capped" in text


# --- input handling ------------------------------------------------------


def test_too_few_h2_subjects_gives_advice_not_a_traceback(pack):
    with pytest.raises(RuleError) as exc:
        score(pack, _sheet("h2 A=A", "h2 B=B", "gp GP=C"), _t(pack))
    assert "3 subjects" in exc.value.message
    assert exc.value.advice


def test_missing_general_paper_is_explained(pack):
    with pytest.raises(RuleError) as exc:
        score(pack, _sheet("h2 A=A", "h2 B=B", "h2 C=C"), _t(pack))
    assert "General Paper" in exc.value.message


def test_unreadable_grade_entry_gives_advice(pack):
    with pytest.raises(InputError) as exc:
        GradeSheet.parse("a-level", ["this is not a subject"])
    assert "LEVEL Name=Grade" in exc.value.advice


def test_invalid_grade_is_rejected_rather_than_scored_as_zero():
    with pytest.raises(InputError):
        GradeSheet.parse("a-level", ["h2 Chemistry=Z"])


# --- other rule kinds exist and are registered ---------------------------


def test_all_three_singapore_formula_shapes_are_implemented():
    kinds = set(available_kinds())
    assert {"weighted_best_n_with_substitution", "lowest_sum", "required_plus_best_n"} <= kinds


def test_lowest_sum_matches_psle_shape():
    """PSLE: four ALs summed, lower is better. Proves the engine is not
    A-Level-shaped, which is the whole architectural claim."""
    from engine.rules import get_rule
    from engine.rules.base import RuleContext

    scales = {"al": {str(i): float(i) for i in range(1, 9)}}
    params = {
        "scale": "al",
        "label": "Your four subjects",
        "total_label": "PSLE Score",
        "best_possible": 4,
        "worst_possible": 32,
        "required_subjects": [
            {"code": "english", "name": "English"},
            {"code": "mathematics", "name": "Mathematics"},
            {"code": "science", "name": "Science"},
            {"code": "mother-tongue", "name": "Mother Tongue"},
        ],
    }
    grades = GradeSheet.from_dicts(
        "psle",
        [
            {"code": "english", "name": "English", "grade": "AL1"},
            {"code": "mathematics", "name": "Mathematics", "grade": "2"},
            {"code": "science", "name": "Science", "grade": "AL3"},
            {"code": "mother-tongue", "name": "Mother Tongue", "grade": "2"},
        ],
    )
    d = get_rule("lowest_sum").evaluate(RuleContext(params, scales, grades))
    assert d.value == 8
    assert d.direction == "lower_is_better"


def test_required_plus_best_n_matches_l1r5_shape():
    """L1R5 and the 2028 L1R4 are the same rule kind with different numbers --
    which is exactly why the 2027 policy change is a data edit, not a rewrite."""
    from engine.rules import get_rule
    from engine.rules.base import RuleContext

    scales = {"ol": {str(i): float(i) for i in range(1, 10)}}
    subjects = [
        {"code": "english", "name": "English", "grade": "2"},
        {"code": "amath", "name": "A Maths", "grade": "1"},
        {"code": "chem", "name": "Chemistry", "grade": "2"},
        {"code": "phys", "name": "Physics", "grade": "3"},
        {"code": "hist", "name": "History", "grade": "4"},
        {"code": "art", "name": "Art", "grade": "8"},
        {"code": "mt", "name": "Mother Tongue", "grade": "3"},
    ]
    grades = GradeSheet.from_dicts("o-level", subjects)
    params = {
        "scale": "ol",
        "total_label": "L1R5",
        "qualifying_max": 20,
        "groups": [
            {"label": "Language (L1)", "take": 1, "codes": ["english"]},
            {"label": "Best 5 relevant (R5)", "take": 5},
        ],
    }
    d = get_rule("required_plus_best_n").evaluate(RuleContext(params, scales, grades))
    # English 2 + best five of {1,2,3,4,3,8} = 1+2+3+3+4 = 13  -> 15
    assert d.value == 15
    assert d.direction == "lower_is_better"


# --- golden fixtures -----------------------------------------------------


def test_golden_fixtures_still_reproduce(pack):
    """The same fixtures CI replays through the browser engine.

    If this fails, either the engine changed or a fixture is stale -- and
    either way a real family's answer just moved, so it is a reviewed change,
    not a `--update-goldens` reflex.
    """
    path = REPO / "evals" / "golden" / "rules.json"
    if not path.exists():
        pytest.skip("run tools/make_golden.py first")
    data = json.loads(path.read_text(encoding="utf-8"))
    for case in data["cases"]:
        transition = pack.transitions[case["transition"]]
        grades = GradeSheet.from_dicts(transition.stage_id, case["subjects"])
        got = score(pack, grades, transition)
        assert got.value == case["expected"]["value"], case["id"]
        assert [s.label for s in got.steps] == [
            s["label"] for s in case["expected"]["steps"]
        ], case["id"]

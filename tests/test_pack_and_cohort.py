"""Pack loading, validation, cohort routing, freshness and the health gate."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from engine import check_pack, describe_freshness, explore, load_pack, resolve_cohort
from engine.errors import InputError, PackError, PackFormatError
from engine.freshness import UpdateCheck, _is_newer

REPO = Path(__file__).resolve().parent.parent


# --- cohort routing: the first question ----------------------------------


def test_jc2_resolves_to_this_years_exam(pack):
    r = resolve_cohort(pack, "jc-2", 2026)
    assert (r.exam_year, r.admission_year) == (2026, 2027)


def test_jc1_resolves_to_next_years_exam(pack):
    r = resolve_cohort(pack, "jc-1", 2026)
    assert (r.exam_year, r.admission_year) == (2027, 2028)


def test_resolution_is_read_back_in_plain_words(pack):
    """A wrong answer to the first question must be catchable by the user."""
    s = resolve_cohort(pack, "jc-2", 2026).sentence()
    assert "Junior College 2" in s and "2026" in s and "2027" in s


def test_a_cohort_outside_the_loaded_rules_refuses_rather_than_guessing(pack):
    """The critical failure mode: silently scoring someone under a formula that
    does not apply to them. It must raise, with advice."""
    with pytest.raises(InputError) as exc:
        resolve_cohort(pack, "jc-2", 2035)
    assert "have not been published or loaded" in exc.value.advice


def test_unknown_year_level_lists_the_valid_ones(pack):
    with pytest.raises(InputError) as exc:
        resolve_cohort(pack, "primary-4", 2026)
    assert "jc-2" in exc.value.advice


# --- pack integrity ------------------------------------------------------


def test_pack_loads_with_the_expected_shape(pack):
    assert pack.id == "singapore"
    assert pack.transitions and pack.outcomes and pack.routes and pack.sources
    assert all(o.transition_id in pack.transitions for o in pack.outcomes.values())


def test_every_fact_cites_a_declared_source(pack):
    for path, fact in pack.all_facts():
        assert fact.source_id in pack.sources, path


def test_a_pack_from_the_future_is_refused_with_advice(tmp_path):
    bad = tmp_path / "pack.yaml"
    bad.write_text(
        "pack:\n  id: x\n  name: X\n  version: v1\n  pack_format: 99\n"
        "  published: 2026-01-01\nsources: []\n",
        encoding="utf-8",
    )
    with pytest.raises(PackFormatError) as exc:
        load_pack(tmp_path)
    assert "Update PathAhead" in exc.value.advice


def test_a_pack_with_no_sources_is_refused(tmp_path):
    (tmp_path / "pack.yaml").write_text(
        "pack:\n  id: x\n  name: X\n  version: v1\n  pack_format: 1\n"
        "  published: 2026-01-01\n",
        encoding="utf-8",
    )
    with pytest.raises(PackError) as exc:
        load_pack(tmp_path)
    assert "at least one source" in exc.value.message


def test_a_fact_citing_an_unknown_source_is_refused(tmp_path):
    (tmp_path / "pack.yaml").write_text(
        """
pack: {id: x, name: X, version: v1, pack_format: 1, published: 2026-01-01}
sources:
  - {id: real, name: Real, url: "https://example.org", retrieved: 2026-01-01, licence: derived}
stages:
  - {id: s, name: S}
transitions:
  - id: t
    stage: s
    name: T
    rule_kind: lowest_sum
    rule_params: {scale: a, required_subjects: []}
    scales: {a: {"1": 1}}
    fact: {value: 1, as_of_year: 2026, source: ghost}
""",
        encoding="utf-8",
    )
    with pytest.raises(PackError) as exc:
        load_pack(tmp_path)
    assert "ghost" in exc.value.message


def test_an_unknown_rule_kind_is_refused_at_load_time(tmp_path):
    (tmp_path / "pack.yaml").write_text(
        """
pack: {id: x, name: X, version: v1, pack_format: 1, published: 2026-01-01}
sources:
  - {id: s1, name: S, url: "https://example.org", retrieved: 2026-01-01, licence: derived}
stages:
  - {id: s, name: S}
transitions:
  - id: t
    stage: s
    name: T
    rule_kind: quantum_vibes
    rule_params: {}
    scales: {}
    fact: {value: 1, as_of_year: 2026, source: s1}
""",
        encoding="utf-8",
    )
    with pytest.raises(PackError) as exc:
        load_pack(tmp_path)
    assert "quantum_vibes" in exc.value.message


# --- compiled bundle round-trip -----------------------------------------


def test_compiled_bundle_loads_back_identically(pack, tmp_path):
    """The browser build and the Python engine must consume the same document."""
    from tools.build_pack import build

    paths = build(REPO / "packs" / "singapore", tmp_path)
    reloaded = load_pack(paths["bundle"])
    assert reloaded.id == pack.id
    assert reloaded.version == pack.version
    assert set(reloaded.outcomes) == set(pack.outcomes)
    for oid, o in pack.outcomes.items():
        if o.band:
            assert reloaded.outcomes[oid].band.p10_points == o.band.p10_points


def test_manifest_checksum_matches_the_bundle(tmp_path):
    from engine import verify_bundle
    from tools.build_pack import build

    paths = build(REPO / "packs" / "singapore", tmp_path)
    digest = verify_bundle(paths["bundle"], paths["manifest"])
    assert len(digest) == 64


def test_a_tampered_bundle_is_rejected(tmp_path):
    from engine import verify_bundle
    from engine.errors import PackIntegrityError
    from tools.build_pack import build

    paths = build(REPO / "packs" / "singapore", tmp_path)
    data = json.loads(paths["bundle"].read_text(encoding="utf-8"))
    data["outcomes"][0]["band"]["p10_points"] = 1.0     # a plausible-looking edit
    paths["bundle"].write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(PackIntegrityError):
        verify_bundle(paths["bundle"], paths["manifest"])


# --- health gate ---------------------------------------------------------


def test_the_shipped_pack_passes_its_own_health_gate(pack, today):
    report = check_pack(pack, today=today)
    assert report.passed, [i.message for i in report.failures]
    assert report.total_facts > 0
    assert report.by_confidence.get("high", 0) > 0


def test_the_gate_fails_a_pack_that_has_gone_stale(pack):
    """The whole point: an app shipping last year's numbers as current must not
    be able to pass CI."""
    future = _dt.date(2030, 1, 1)
    report = check_pack(pack, today=future)
    assert not report.passed
    assert any("stale_after" in i.message for i in report.failures)


def test_the_gate_fails_when_the_confidence_floor_is_raised(pack, today):
    """The pack has medium-confidence facts by design, flagged in the source
    notes. Demanding 'high' must therefore fail -- proving the floor is real."""
    report = check_pack(pack, today=today, min_confidence="high")
    assert not report.passed
    assert any("below the 'high' floor" in i.message for i in report.failures)


def test_health_report_renders_both_ways(pack, today):
    report = check_pack(pack, today=today)
    assert "RESULT: PASS" in report.as_text()
    assert "| Facts |" in report.as_markdown()


# --- freshness -----------------------------------------------------------


def test_freshness_banner_always_states_the_data_age(pack, today):
    f = describe_freshness(pack, today)
    assert "Data as of" in f.banner
    assert f.level in ("ok", "info", "warn")


def test_old_data_escalates_the_banner(pack):
    assert describe_freshness(pack, _dt.date(2029, 1, 1)).level == "warn"


@pytest.mark.parametrize(
    "candidate,current,expected",
    [("sg-2026.2", "sg-2026.1", True), ("sg-2026.1", "sg-2026.1", False),
     ("sg-2025.9", "sg-2026.1", False), ("sg-2027.0", "sg-2026.5", True)],
)
def test_version_comparison(candidate, current, expected):
    assert _is_newer(candidate, current) is expected


def test_offline_update_check_is_a_non_event():
    """Offline is a supported state, not a degraded one."""
    check = UpdateCheck(available=False, error="no network")
    assert "works offline" in check.message("sg-2026.1")


def test_update_check_sends_no_identifiers():
    """Read the implementation as data: no query string may be constructed."""
    src = (REPO / "engine" / "freshness.py").read_text(encoding="utf-8")
    body = src.split("def check_for_update")[1].split("def _latest_tag")[0]
    assert "urlencode" not in body
    assert "params" not in body
    assert "?" not in body.split("Request(")[1].split(")")[0]


# --- end to end ----------------------------------------------------------


def test_explore_produces_a_serialisable_result(pack, strong_grades):
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    payload = json.dumps(result.to_dict())
    assert len(payload) > 500
    assert result.comparison_score == 57.5
    assert result.derivation.value == 70


def test_comparison_score_is_not_the_headline_score(pack, strong_grades):
    """The core honesty move: the 70-point score is NOT comparable to a
    published grade profile, so a different, declared basis is used."""
    result = explore(pack, year_level="jc-2", current_year=2026, grades=strong_grades)
    assert result.comparison_score != result.derivation.value
    assert result.comparison_basis
    assert any("70-point basis" in w for w in result.warnings)

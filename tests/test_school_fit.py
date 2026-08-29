"""Tests for engine/school_fit.py -- the PSLE-stage shortlisting FILTERS.

This used to be a scorer (test_school_fit.py tested percentages, weighted
dimensions, importance levels). Review on 2026-08-13 concluded the score
itself -- not just the cut-off data feeding it -- was the SAFEGUARDS.md 5.1
risk, so the module was rewritten to filter rather than rank. These tests
follow that rewrite: an unset filter must never hide a school, a set filter
must hide every non-matching school and no matching one, the eligibility
gate stays a hard, unconditional, three-state fact (never a preference),
and the shortlist's ORDER never depends on how well a school matches
anything -- only on distance and name.
"""

from __future__ import annotations

import re

from engine.school_fit import (
    DIMENSION_KEYS,
    FILTER_DISCLAIMER,
    REACH_MARGIN,
    SchoolPreferences,
    combined_reach,
    distance_km,
    explain_school_match,
    haversine_km,
    match_all,
    match_school,
    postal_sector_index,
    resolve_district,
    shortlist,
    within_reach,
)
from tests.test_safeguards import BANNED

# --- postal code -> district resolution ----------------------------------


def test_a_real_postal_code_resolves_to_its_district(pack):
    idx = postal_sector_index(pack)
    # 737916 is Admiralty Secondary's own postal code, sector 73 -> district 25.
    row = resolve_district(idx, "737916")
    assert row is not None
    assert row["district"] == "25"
    assert row["region"] == "NORTH"


def test_a_malformed_postal_code_resolves_to_nothing(pack):
    idx = postal_sector_index(pack)
    assert resolve_district(idx, "") is None
    assert resolve_district(idx, "1234") is None
    assert resolve_district(idx, "not a postal code") is None


def test_every_school_in_the_pack_has_a_resolvable_district(pack):
    """The build script raises if any postal code fails to resolve, so this
    is really a regression guard on the pack, not the engine -- but it
    belongs here because it is exactly the invariant match_school relies on.
    """
    idx = postal_sector_index(pack)
    for school in pack.schools:
        assert resolve_district(idx, school["postal_code"]) is not None, school["name"]


# --- no filters set: every eligible school matches, nothing is hidden -----


def test_no_filters_set_means_every_eligible_school_matches(pack):
    prefs = SchoolPreferences()
    assert prefs.signal_count == 0
    matches = match_all(pack, prefs)
    assert matches
    for m in matches.values():
        assert m.matches_preferences is True
        assert m.unmet == ()


def test_one_filter_is_enough_to_start_hiding_non_matches(pack):
    prefs = SchoolPreferences(gender="girls")
    matches = match_all(pack, prefs)
    boys_schools = [
        m for sid, m in matches.items()
        if next(s for s in pack.schools if s["id"] == sid)["gender"] == "boys"
    ]
    assert boys_schools
    assert all(m.matches_preferences is False for m in boys_schools)


# --- unset filters never count against a school -----------------------


def test_unset_filters_never_appear_in_unmet(pack):
    school = next(s for s in pack.schools if s["id"] == "admiralty-secondary-school")
    prefs = SchoolPreferences(gender="co-ed")  # nothing else set
    m = match_school(school, prefs)
    assert m.matches_preferences is True  # Admiralty is co-ed
    assert m.unmet == ()


def test_a_miss_on_one_dimension_does_not_touch_an_unset_dimension(pack):
    school = next(s for s in pack.schools if s["id"] == "admiralty-secondary-school")
    # Admiralty is co-ed and not SAP. Ask for a girls' school (a miss) while
    # leaving SAP unset -- the miss must show up alone, not spill over.
    prefs = SchoolPreferences(gender="girls")
    m = match_school(school, prefs)
    assert m.matches_preferences is False
    assert m.unmet == ("gender",)


# --- "how close to home" is a distance-band filter, not a dimension here --
# The old categorical own-district/same-region/elsewhere scoring dimension
# is retired; distance_km() plus a caller-chosen km band is the one "how
# far" mechanism now (see the module docstring).


def test_haversine_of_a_point_against_itself_is_zero():
    assert haversine_km(1.35, 103.82, 1.35, 103.82) == 0.0


def test_haversine_matches_a_known_singapore_distance():
    # Woodlands Regional Centre (~1.4360, 103.7860) to Raffles Place
    # (~1.2840, 103.8510) is a roughly-18km straight-line hop across the
    # island -- sanity-checked against a public distance calculator (which
    # agrees to within 0.1km), not just internal consistency.
    d = haversine_km(1.4360, 103.7860, 1.2840, 103.8510)
    assert 18.0 < d < 19.0


def test_distance_km_is_none_without_a_home_district(pack):
    school = pack.schools[0]
    assert distance_km(school, None) is None


def test_distance_km_is_none_if_either_point_lacks_coordinates(pack):
    school_no_coords = {**pack.schools[0], "lat": None, "lng": None}
    home = {"lat": 1.35, "lng": 103.82}
    assert distance_km(school_no_coords, home) is None
    assert distance_km(pack.schools[0], {"lat": None, "lng": None}) is None


def test_distance_km_is_a_real_positive_number_for_two_geocoded_points(pack):
    by_id = {s["id"]: s for s in pack.schools}
    admiralty = by_id["admiralty-secondary-school"]
    idx = postal_sector_index(pack)
    home = resolve_district(idx, admiralty["postal_code"])
    d = distance_km(admiralty, home)
    assert d is not None
    assert d >= 0.0
    # Admiralty's own district anchor point should be close to Admiralty
    # itself -- a sanity ceiling, not a precise claim.
    assert d < 10.0


def test_distance_km_is_populated_even_for_a_school_gated_out_by_student_sex(pack):
    """distance is informational and is never withheld by the eligibility
    gate -- a family should still see how far away a school is even when
    told it is not an option for their child, so they understand the answer
    rather than just seeing it vanish."""
    girls_school = next(s for s in pack.schools if s["gender"] == "girls")
    prefs = SchoolPreferences(postal_code=girls_school["postal_code"], student_sex="male")
    result = match_school(girls_school, prefs, district_index=pack)
    assert result.eligible is False
    assert result.distance_km is not None


# --- within_reach(): a FILTER, never a score, never a sort key -------------
# SAFEGUARDS.md 5.1: "never rank schools by cut-off point." within_reach()
# answers a yes/no/unknown question a caller can use to narrow a list; it is
# never wired into match_school() or SchoolMatch, and these tests never
# check that it is -- there is no score for it to move, and no field on
# SchoolMatch it could feed even if it wanted to.
#
# These cases use SYNTHETIC schools, not rows from the pack, and that is
# deliberate on two counts.
#
# First, correctness: as of 2026-08-14 PathAhead does not republish Posting
# Group cut-off points at all (see engine/loader.py:_apply_local_overlays and
# docs/LOCAL_DATA.md), so every school in a clean checkout has
# `cutoff_2025: None`. Tests that read figures out of the pack passed only on
# a machine that happened to hold a private overlay and failed in CI -- which
# is precisely backwards, since CI is the environment that matches what users
# get.
#
# Second, and true regardless: a unit test of a comparison should own the
# numbers it compares. Pinning `within_reach` to Admiralty's real 2025 cut-off
# meant a genuine change in MOE's published figures would fail a test about
# arithmetic, and the failure would say nothing useful about either.


def _school(school_id="test-secondary-school", **cutoffs):
    """A minimal school row shaped the way within_reach() reads one.

    Only `id` and `cutoff_2025` matter here. Bands are given as
    [first_posted, last_posted]; within_reach only reads the second, which is
    the cut-off proper -- the score of the last student admitted.
    """
    bands = {k: cutoffs.get(k) for k in ("pg3", "pg2", "pg1", "ip")}
    return {"id": school_id, "cutoff_2025": None if not any(bands.values()) else bands}


def test_within_reach_true_for_a_score_comfortably_inside_the_cutoff():
    school = _school(pg3=[16, 22])
    assert within_reach(school, 20, (3,)) is True


def test_within_reach_true_exactly_at_the_margin_boundary():
    """cutoff + REACH_MARGIN is still in reach -- the margin exists
    precisely so a hard line is never drawn at last year's number."""
    school = _school(pg3=[16, 22])
    assert within_reach(school, 22 + REACH_MARGIN, (3,)) is True


def test_within_reach_false_one_point_past_the_margin():
    school = _school(pg3=[16, 22])
    assert within_reach(school, 22 + REACH_MARGIN + 1, (3,)) is False


def test_within_reach_is_none_not_false_when_no_cutoff_is_published():
    """No cut-off held for this school -- either because it admits through a
    specialised route outside the S1 Posting Exercise, or (the shipped case)
    because PathAhead does not republish these figures at all. Both must
    answer None: 'cannot tell' is not the same claim as 'not in reach', and a
    caller must show these schools rather than silently treating the absence
    of data as a no."""
    school = _school()  # cutoff_2025 is None
    assert school["cutoff_2025"] is None
    assert within_reach(school, 10, (3,)) is None


def test_every_school_in_a_clean_checkout_answers_none(pack):
    """The shipped state, asserted rather than assumed.

    PathAhead publishes no cut-off figures, so in a clean checkout every one
    of the 147 schools must answer 'cannot tell' -- never 'not in reach'. A
    regression that started shipping figures, or one that turned a missing
    figure into a negative, would both surface here.

    Skipped on a machine holding a private local overlay, because there the
    pack legitimately does carry figures and this invariant does not apply.
    """
    if pack.local_overlay_applied:
        import pytest

        pytest.skip("a local cut-off overlay is present; this asserts the published state")
    for school in pack.schools:
        assert school.get("cutoff_2025") is None, school["id"]
        assert within_reach(school, 10, (3,)) is None, school["id"]


def test_within_reach_is_none_when_family_groups_is_empty():
    """An empty tuple means the family's PSLE score fell outside the
    published Posting Group table entirely -- also 'cannot tell', not 'no'."""
    school = _school(pg3=[16, 22])
    assert within_reach(school, 31, ()) is None


def test_within_reach_is_none_when_the_familys_group_has_no_published_band():
    """A school publishing PG3/PG2 but not PG1 -- a family whose score opens
    only PG1 must get None for this school, not a false negative manufactured
    from a band nobody published."""
    school = _school(pg3=[16, 22], pg2=[21, 25])
    assert school["cutoff_2025"]["pg1"] is None
    assert within_reach(school, 26, (1,)) is None


def test_within_reach_checks_either_group_when_a_choice_is_offered():
    """A score that opens a CHOICE between two Posting Groups is in reach if
    EITHER group's cutoff would admit it -- the family could choose that one."""
    school = _school(pg3=[16, 22], pg2=[21, 25])
    assert within_reach(school, 27, (3,)) is False  # PG3 alone: 27 > 22+2
    assert within_reach(school, 27, (2, 3)) is True  # PG2 admits: 27 <= 25+2


def test_within_reach_respects_a_custom_margin():
    school = _school(pg3=[16, 22])
    assert within_reach(school, 23, (3,), margin=0) is False
    assert within_reach(school, 22, (3,), margin=0) is True


def test_within_reach_is_never_part_of_a_schoolmatch(pack):
    """within_reach() and match_school() are two separate call paths -- this
    guards against a future change accidentally wiring reach into the match
    by checking the dataclass simply has no field for it."""
    from dataclasses import fields

    from engine.school_fit import SchoolMatch

    assert "within_reach" not in {f.name for f in fields(SchoolMatch)}
    assert "reach" not in {f.name for f in fields(SchoolMatch)}


# --- combined_reach(): the EXPLICIT AL-score search, one score or a range -
# The shortlist's "Search by AL score" control (web/src/app.js:renderSchoolPrefs),
# independent of whatever the family typed into the Posting Group calculator
# elsewhere on the page. Same discipline as within_reach() above -- a caller
# only ever hides on "out-of-reach"; the other three states stay visible and
# differ only in which honest caveat a caller shows.


def test_combined_reach_in_reach_when_both_ends_clear_the_cutoff():
    school = _school(pg3=[16, 22])
    assert combined_reach(school, 18, 20, (3,), (3,)) == "in-reach"


def test_combined_reach_possible_when_only_the_better_end_clears():
    """The worse end of the range misses; the better end still clears --
    'possible', never plain 'in-reach', so a caller can't present it as a
    confirmed match."""
    school = _school(pg3=[16, 22])
    assert combined_reach(school, 20, 27, (3,), (3,)) == "possible"


def test_combined_reach_out_of_reach_when_neither_end_clears():
    school = _school(pg3=[16, 22])
    assert combined_reach(school, 26, 30, (3,), (3,)) == "out-of-reach"


def test_combined_reach_is_unknown_not_out_of_reach_when_no_cutoff_is_published():
    school = _school()  # cutoff_2025 is None
    assert combined_reach(school, 10, 12, (3,), (3,)) == "unknown"


def test_combined_reach_with_equal_ends_matches_a_plain_within_reach_call():
    """An 'upper bound' search is lo_score == hi_score with the same groups
    at both ends -- the one-point degenerate case of a range, not a second
    code path that could quietly drift from within_reach() over time."""
    school = _school(pg3=[16, 22])
    for score in (18, 22 + REACH_MARGIN, 22 + REACH_MARGIN + 1, 30):
        want = "in-reach" if within_reach(school, score, (3,)) else "out-of-reach"
        assert combined_reach(school, score, score, (3,), (3,)) == want


def test_combined_reach_respects_a_custom_margin():
    school = _school(pg3=[16, 22])
    assert combined_reach(school, 23, 23, (3,), (3,), margin=0) == "out-of-reach"
    assert combined_reach(school, 22, 22, (3,), (3,), margin=0) == "in-reach"


def test_combined_reach_never_returns_a_boolean_or_none():
    """Every return path is one of the four named strings -- a caller
    (schoolCard()'s data-reach attribute, in particular) must never see a
    bare True/False/None it could confuse with within_reach()'s own return."""
    school = _school(pg3=[16, 22])
    for lo, hi in ((18, 20), (20, 27), (26, 30)):
        result = combined_reach(school, lo, hi, (3,), (3,))
        assert result in ("in-reach", "possible", "out-of-reach", "unknown")
    assert combined_reach(_school(), 10, 12, (3,), (3,)) == "unknown"


# --- SAP / IP / Autonomous / Gifted: want vs avoid, both filter honestly ---


def test_wanting_and_avoiding_a_trait_are_both_filters_not_just_wanting(pack):
    sap_school = next(s for s in pack.schools if s["sap"])
    non_sap_school = next(s for s in pack.schools if not s["sap"])

    wants_sap = SchoolPreferences(want_sap=True)
    avoids_sap = SchoolPreferences(want_sap=False)

    assert match_school(sap_school, wants_sap).matches_preferences is True
    assert match_school(sap_school, avoids_sap).matches_preferences is False
    assert match_school(non_sap_school, wants_sap).matches_preferences is False
    assert match_school(non_sap_school, avoids_sap).matches_preferences is True


def test_gifted_and_ip_and_autonomous_all_filter_symmetrically(pack):
    for field_name, key in (("gifted", "want_gifted"), ("ip", "want_ip"), ("autonomous", "want_autonomous")):
        has_it = next(s for s in pack.schools if s[field_name])
        lacks_it = next(s for s in pack.schools if not s[field_name])
        wants = SchoolPreferences(**{key: True})
        avoids = SchoolPreferences(**{key: False})
        assert match_school(has_it, wants).matches_preferences is True, field_name
        assert match_school(lacks_it, avoids).matches_preferences is True, field_name
        assert match_school(has_it, avoids).matches_preferences is False, field_name
        assert match_school(lacks_it, wants).matches_preferences is False, field_name


def test_school_type_filter_matches_on_the_stated_label(pack):
    govt = next(s for s in pack.schools if s["type_label"] == "Government school")
    independent = next(s for s in pack.schools if s["type_label"] == "Independent school")
    prefs = SchoolPreferences(school_types=("Government school",))
    assert match_school(govt, prefs).matches_preferences is True
    assert match_school(independent, prefs).matches_preferences is False


def test_school_type_filter_accepts_any_one_of_several_picked_types(pack):
    govt = next(s for s in pack.schools if s["type_label"] == "Government school")
    aided = next(s for s in pack.schools if s["type_label"] == "Government-aided school")
    independent = next(s for s in pack.schools if s["type_label"] == "Independent school")
    prefs = SchoolPreferences(school_types=("Government school", "Government-aided school"))
    assert match_school(govt, prefs).matches_preferences is True
    assert match_school(aided, prefs).matches_preferences is True
    assert match_school(independent, prefs).matches_preferences is False


# --- student_sex: an eligibility gate, not a preference --------------------
# A boys' school does not admit girls and vice versa. Checked BEFORE any
# preference filter and independent of every one of them. Three states, and
# only one of them (False) ever hides a school unconditionally.


def test_a_single_sex_school_is_ineligible_not_merely_unmatched_for_the_wrong_sex(pack):
    girls_school = next(s for s in pack.schools if s["gender"] == "girls")
    boys_school = next(s for s in pack.schools if s["gender"] == "boys")

    prefs_boy = SchoolPreferences(student_sex="male")
    prefs_girl = SchoolPreferences(student_sex="female")

    boy_at_girls_school = match_school(girls_school, prefs_boy)
    assert boy_at_girls_school.eligible is False
    assert "does not admit boys" in boy_at_girls_school.eligibility_reason

    girl_at_boys_school = match_school(boys_school, prefs_girl)
    assert girl_at_boys_school.eligible is False
    assert "does not admit girls" in girl_at_boys_school.eligibility_reason


def test_a_single_sex_school_is_eligible_for_the_matching_sex(pack):
    girls_school = next(s for s in pack.schools if s["gender"] == "girls")
    boys_school = next(s for s in pack.schools if s["gender"] == "boys")

    assert match_school(girls_school, SchoolPreferences(student_sex="female")).eligible is True
    assert match_school(boys_school, SchoolPreferences(student_sex="male")).eligible is True


def test_a_single_sex_school_is_unconfirmed_when_the_students_sex_is_unknown(pack):
    girls_school = next(s for s in pack.schools if s["gender"] == "girls")
    # Plenty of other filters set -- the gate must still fire regardless,
    # because it does not depend on how many preferences were set.
    prefs = SchoolPreferences(want_sap=True, want_ip=True, want_autonomous=True)
    result = match_school(girls_school, prefs)
    assert result.eligible is None
    assert "has not been told your child's sex" in result.eligibility_reason


def test_a_co_ed_school_is_always_eligible_regardless_of_student_sex(pack):
    co_ed_school = next(s for s in pack.schools if s["gender"] == "co-ed")
    for sex in (None, "male", "female"):
        result = match_school(co_ed_school, SchoolPreferences(student_sex=sex))
        assert result.eligible is True, sex


def test_student_sex_is_not_counted_as_a_signal(pack):
    # It is a fact that gates eligibility, not a preference the family is
    # filtering on -- setting it alone must not count toward signal_count.
    prefs = SchoolPreferences(student_sex="male")
    assert prefs.signal_count == 0


def test_wrong_sex_schools_are_ineligible_regardless_of_matching_every_other_filter(pack):
    # A girls' school matching every other filter (SAP, distance) must still
    # come back ineligible for a boy -- eligibility is checked first and is
    # entirely independent of matches_preferences, exactly like fit.py's
    # subject gate short-circuits before scoring.
    girls_sap_school = next(s for s in pack.schools if s["gender"] == "girls" and s["sap"])
    prefs = SchoolPreferences(
        student_sex="male", want_sap=True, postal_code=girls_sap_school["postal_code"],
    )
    result = match_school(girls_sap_school, prefs, district_index=pack)
    assert result.eligible is False
    # matches_preferences is independent of eligibility -- this school DOES
    # match the SAP filter (gender was never set as a preference here), and
    # that must still be reported honestly even though it is not an option.
    assert result.matches_preferences is True


# --- shortlist ordering: distance then name, never anything match-shaped --


def test_shortlist_with_no_postal_code_is_sorted_alphabetically(pack):
    prefs = SchoolPreferences()
    rows = shortlist(pack, prefs)
    names = [school["name"] for school, _ in rows]
    assert names == sorted(names)


def test_shortlist_with_a_postal_code_is_sorted_by_distance_then_name(pack):
    admiralty = next(s for s in pack.schools if s["id"] == "admiralty-secondary-school")
    prefs = SchoolPreferences(postal_code=admiralty["postal_code"])
    rows = shortlist(pack, prefs)
    dists = [m.distance_km for _, m in rows]
    known = [d for d in dists if d is not None]
    assert known == sorted(known)
    # every school with a known distance sorts before every school without one
    assert all(d is not None for d in dists[: len(known)])
    # ties at the same distance break alphabetically by name
    tie_groups: dict[float, list[str]] = {}
    for school, m in rows:
        if m.distance_km is not None:
            tie_groups.setdefault(m.distance_km, []).append(school["name"])
    for names in tie_groups.values():
        assert names == sorted(names)


def test_shortlist_order_does_not_depend_on_preference_filters(pack):
    """Setting a preference changes WHICH rows a caller would keep, never
    the relative order of the ones that remain -- shortlist() itself does
    not even look at matches_preferences when sorting."""
    prefs_unfiltered = SchoolPreferences()
    prefs_filtered = SchoolPreferences(gender="co-ed")
    unfiltered_names = [s["name"] for s, _ in shortlist(pack, prefs_unfiltered)]
    filtered_names = [s["name"] for s, _ in shortlist(pack, prefs_filtered)]
    # same relative order for schools present in both (all of them, since
    # shortlist() never drops rows itself)
    assert unfiltered_names == filtered_names


def test_shortlist_limit_truncates_display_but_matching_still_covers_the_whole_pool(pack):
    prefs = SchoolPreferences(gender="co-ed")
    full = shortlist(pack, prefs)
    limited = shortlist(pack, prefs, limit=5)
    assert len(full) == len(pack.schools)
    assert len(limited) == 5
    assert limited == full[:5]


def test_shortlist_never_drops_a_school_itself(pack):
    """shortlist() reports match info for every school; hiding non-matching
    or ineligible ones is a caller's job (the UI), exactly like the
    distance-band and reach filters already work -- this guards against
    that responsibility silently creeping into the engine."""
    prefs = SchoolPreferences(gender="girls", want_sap=True, school_types=("Independent school",))
    rows = shortlist(pack, prefs)
    assert len(rows) == len(pack.schools)


# --- no verdict / admission-estimate language anywhere --------------------


def test_no_banned_phrase_in_school_match_copy(pack):
    prefs = SchoolPreferences(
        postal_code="737916",
        gender="co-ed",
        want_sap=True,
        want_ip=True,
        want_autonomous=True,
        want_gifted=True,
        school_types=("Government school", "Independent school"),
    )
    rows = shortlist(pack, prefs)
    copy_parts = [FILTER_DISCLAIMER]
    for school, m in rows[:20]:
        copy_parts.append(explain_school_match(m, school))
    copy = "\n".join(copy_parts).lower()
    for pattern in BANNED:
        assert not re.search(pattern, copy), f"banned phrase matched: {pattern}"


def test_the_filter_disclaimer_never_uses_the_word_guarantee(pack):
    # Extra-explicit regression guard: an earlier draft of a disclaimer like
    # this said "does not guarantee a place", which trips the same
    # banned-phrase regex it was trying to reassure someone with. Rewrite
    # the sentence, not the guard -- see memory note on this exact failure
    # mode.
    assert "guarantee" not in FILTER_DISCLAIMER.lower()


def test_dimension_keys_cover_every_filter_dimension_label():
    from engine.school_fit import DIMENSION_LABEL

    assert set(DIMENSION_LABEL) == set(DIMENSION_KEYS)
    assert "proximity" not in DIMENSION_KEYS  # retired -- see module docstring

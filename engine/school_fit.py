"""School fit: which of the 147 schools a PSLE cohort can be posted to are
even worth a closer look, given what a family says matters to them -- and,
separately, which of MOE's own facts about a school rule it out entirely.

This module used to compute a weighted match SCORE and rank schools by it.
It no longer does. Review on 2026-08-13 concluded the score itself was the
problem, not just the cut-off data feeding it: a percentage and a bar chart
read as a verdict on a school no matter how carefully the copy around them
explains they are not one, and ranking 147 real schools by "how well they
match" sits one small step from ranking them by how good they are -- exactly
what SAFEGUARDS.md 5.1 exists to prevent ("never rank schools... results
sort by fit, programme and location -- never by selectivity descending").
The fix is not a better score. It is no score.

Every dimension below is now a FILTER: set it, and it hides schools that
don't match; leave it unset, and it does nothing. Nothing here earns
points, nothing is weighted by importance, and nothing about a shown
school implies it is "better" than one a filter hid -- only that it does
or does not match what was asked. What remains after filtering is sorted
by distance (when a postal code was given) and then by name -- both
allowed under SAFEGUARDS.md 5.1's own words, and neither one selectivity.

    Evidence  -- a Posting Group cut-off / Aggregate Score range. PathAhead
                 holds a `cutoff_current` figure for 139 of the 147 schools
                 (see tools/build_secondary_schools_pack.py for where it
                 came from and why it is recorded at `confidence: medium`,
                 not `high`). This module still never turns it into a score
                 or a sort key -- see `within_reach()` below. What it buys
                 is the same thing every other dimension here buys: a
                 family can narrow 147 schools to ones realistically in
                 reach of their own PSLE score, while the schools that
                 remain stay sorted by distance and name, exactly as they
                 always have. `combined_reach()` answers the same question
                 for an EXPLICIT search a family types directly into the
                 shortlist filter -- a single score, or a range for a
                 family working from an estimate rather than a result --
                 independent of whatever they entered into the Posting
                 Group calculator elsewhere on the page.

    Filters   -- "does this school match what you said you're looking
                 for": close to home (a straight-line distance band), co-ed
                 or single-sex, SAP, the Integrated Programme, Autonomous
                 status, the Gifted Education Programme, school type. Every
                 one of these is a real thing parents and students weigh
                 when shortlisting -- see FILTER_DIMENSIONS below for what
                 each one actually means and why it is here. "How close to
                 home" used to be a separate scored dimension with its own
                 categorical own-district / same-region / elsewhere logic;
                 that is now retired in favour of the honest, real km-band
                 filter (`distance_km()` + a caller-side band choice), so
                 there is exactly one "how far" mechanism instead of two
                 that could disagree with each other.

There IS one real eligibility gate, and it is not a preference at all: a
boys' school does not admit girls, and a girls' school does not admit
boys. An earlier version of this module treated that as a scored
PREFERENCE dimension -- reasoning that building a second eligibility
system for one field was more machinery than it was worth. That reasoning
was wrong, caught in review 2026-08-13: a single-sex school a student
cannot physically attend is not "a weaker match", it is not a real option,
and it must not sit in the same list as schools the student CAN attend
even at zero points on one dimension out of several. `student_sex` is
asked for directly and checked BEFORE any preference filter runs, in the
same place and for the same reason `fit.py`'s language and subject-
requirement gates run first: eligibility is not a low score -- now it is
not a filter either, it is the one thing here that hides a school
unconditionally, with no toggle to override it, because it is a fact
about the school, not a want of the family's.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .model import Pack

#: The preference dimensions a family can filter on, in the order offered.
#: Each entry is (key, label, what setting it hides). "Proximity" is
#: deliberately absent -- see the module docstring for why "how close to
#: home" is now the km-band filter (distance_km()) rather than a dimension
#: here.
FILTER_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("gender", "Co-ed or single-sex",
     "hides schools that are not the kind you picked"),
    ("sap", "Special Assistance Plan (bilingual, Chinese language and "
     "culture emphasis)",
     "hides schools that don't match what you asked for or against"),
    ("ip", "Integrated Programme (one six-year run through to A-Level or the "
     "IB, without sitting O-Levels)",
     "hides schools that don't match what you asked for or against"),
    ("autonomous", "Autonomous status (extra funding for facilities and "
     "programmes, and its own admission exercise)",
     "hides non-Autonomous schools if you asked for one"),
    ("gifted", "A Gifted Education Programme branch at secondary level",
     "hides schools without a GEP branch if you asked for one"),
    ("school_type", "Government, government-aided, independent or "
     "specialised",
     "hides schools of a type you did not pick"),
)
DIMENSION_KEYS = tuple(d[0] for d in FILTER_DIMENSIONS)
DIMENSION_LABEL = {k: label for k, label, _ in FILTER_DIMENSIONS}


@dataclass(slots=True)
class SchoolPreferences:
    """What a family typed. Every field below, when set, is a FILTER: it
    hides schools that don't match, and never scores or reorders what
    remains. An unanswered field simply does not filter -- the same rule
    the distance-band and reach filters already follow when left at "Any
    distance" / "Show all schools".
    """

    #: A 6-digit Singapore postal code, or None if not given. Only ever used
    #: to look up a postal DISTRICT and a straight-line distance -- never
    #: geocoded to an exact address. See resolve_district() / distance_km().
    postal_code: str | None = None
    #: "male" | "female", or None if not given. NOT a preference -- this is
    #: the fact that gates whether a single-sex school is even a possible
    #: option, checked before any filter. See SchoolMatch.eligible.
    student_sex: str | None = None
    #: "co-ed" | "girls" | "boys", or None for no filter. A filter among the
    #: schools student_sex has already made possible -- e.g. a boy is
    #: eligible for both co-ed and boys' schools, and may still filter down
    #: to just one. This never overrides the hard gate above.
    gender: str | None = None
    #: True = only SAP schools, False = only non-SAP schools, None = no filter.
    want_sap: bool | None = None
    want_ip: bool | None = None
    want_autonomous: bool | None = None
    want_gifted: bool | None = None
    #: Which type_label(s) are acceptable. Empty tuple = no filter.
    school_types: tuple[str, ...] = ()

    @property
    def signal_count(self) -> int:
        """How many filters are actually set -- used only to decide whether
        a "clear all" affordance has anything to clear, never to gate
        whether schools are shown (the unfiltered pool always is)."""
        n = 0
        if self.postal_code:
            n += 1
        if self.gender:
            n += 1
        if self.want_sap is not None:
            n += 1
        if self.want_ip is not None:
            n += 1
        if self.want_autonomous is not None:
            n += 1
        if self.want_gifted is not None:
            n += 1
        if self.school_types:
            n += 1
        return n


def postal_sector_index(pack: Pack) -> dict[str, dict[str, Any]]:
    """sector (first two digits of a postal code) -> that district's row.

    Built once per pack rather than once per school; see subject_families()
    in fit.py for the same reasoning -- deriving it 147 times is wasted work
    and, worse, a chance for one call site to build it slightly differently
    from another.
    """
    idx: dict[str, dict[str, Any]] = {}
    for row in pack.postal_districts or ():
        for sector in row.get("sectors", ()):
            idx[str(sector)] = row
    return idx


def resolve_district(pack_or_index, postal_code: str) -> dict[str, Any] | None:
    """A 6-digit (or loosely-formatted) postal code -> its district row, or
    None if it does not look like a real Singapore postal code.

    Accepts either a Pack (builds the index) or an already-built index, so
    callers matching many schools against one family's postal code can
    build the index once via postal_sector_index() and pass it straight
    through.
    """
    idx = (
        postal_sector_index(pack_or_index)
        if isinstance(pack_or_index, Pack)
        else pack_or_index
    )
    digits = "".join(ch for ch in (postal_code or "") if ch.isdigit())
    if len(digits) != 6:
        return None
    return idx.get(digits[:2])


#: Mean Earth radius in km -- the constant every haversine implementation
#: uses; not a PathAhead choice.
_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle (straight-line) distance between two points, in km.

    This is deliberately NOT a travel time: a routed transit or driving
    time needs a live call to a routing service, which would mean the
    postal code a family typed left the device. This number answers a
    narrower, honest question -- "roughly how far apart are these two
    points on a map" -- and every place it is shown says so explicitly
    rather than implying it is a commute.

    The two points behind this call are real: a school's own geocoded
    postal code, and a representative anchor point for the family's postal
    DISTRICT (never their exact address, which PathAhead never geocodes at
    all -- see resolve_district()). Both are fetched once, offline, at pack
    build time from OneMap Singapore, the national mapping authority's own
    geocoder -- see tools/build_secondary_schools_pack.py.
    """
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlng / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def distance_km(school: Mapping[str, Any], home_district: Mapping[str, Any] | None) -> float | None:
    """Straight-line km from a family's postal-district anchor to a school,
    or None if either point's coordinates are missing.

    Doubles as the "how close to home" FILTER's input (a caller compares
    this against a chosen km band) and as an honest informational number
    shown on every card. It is also the sort key `shortlist()` uses when a
    postal code was given -- see that function's docstring.
    """
    if home_district is None:
        return None
    lat1, lng1 = home_district.get("lat"), home_district.get("lng")
    lat2, lng2 = school.get("lat"), school.get("lng")
    if None in (lat1, lng1, lat2, lng2):
        return None
    return round(haversine_km(lat1, lng1, lat2, lng2), 1)


#: PSLE-score points of slack allowed past a school's published cut-off
#: point before treating it as out of reach. MOE's own words: cut-off
#: points "can fluctuate by a few points year-on-year" -- a hard boundary
#: at exactly last year's number would silently exclude schools that are
#: genuinely still in play this year. Chosen, not fitted: this is a
#: planning margin, not a statistical estimate.
REACH_MARGIN = 2


def within_reach(
    school: Mapping[str, Any],
    psle_score: float,
    family_groups: Sequence[int],
    *,
    margin: int = REACH_MARGIN,
) -> bool | None:
    """Whether a school's most recently published cut-off, for whichever
    Posting Group(s) the family's own PSLE score has actually opened,
    suggests the school is realistically still worth a spot on a real
    six-school list.

    A FILTER, not a score and not a sort key -- see SAFEGUARDS.md 5.1
    ("never rank schools by cut-off point"). It answers a yes/no
    reachability question so a family can narrow 147 schools to ones worth
    reading about in detail; it never orders what remains.

    `family_groups` is `PostingGroupResult.groups` from
    `engine/posting.py:resolve_posting_group` -- computed once per family,
    not here, so this module never needs to know how a PSLE score becomes a
    Posting Group. Passing which group(s) a score has ALREADY opened (rather
    than the raw score alone) means a family whose score allows a choice
    between two groups is judged against BOTH, since they could choose
    either.

    Returns None -- never False -- when PathAhead genuinely cannot judge:
    no cut-off is published for this school (`cutoff_current` is None -- see
    tools/build_secondary_schools_pack.py for which 8 schools and why), or
    the family's score fell outside the published Posting Group table
    entirely (`family_groups` is empty). A caller must SHOW these schools,
    with the reason, rather than silently treating "cannot tell" as "no" --
    the same rule this project applies everywhere an absence of data is
    not the same as an absence in reality.
    """
    cutoffs = school.get("cutoff_current")
    if not cutoffs or not family_groups:
        return None
    seen_a_published_group = False
    for group in family_groups:
        band = cutoffs.get(f"pg{int(group)}")
        if band is None:
            continue
        seen_a_published_group = True
        cop = band[1]
        if cop is not None and psle_score <= cop + margin:
            return True
    return False if seen_a_published_group else None


def combined_reach(
    school: Mapping[str, Any],
    lo_score: float,
    hi_score: float,
    lo_groups: Sequence[int],
    hi_groups: Sequence[int],
    *,
    margin: int = REACH_MARGIN,
) -> str:
    """Reach across an explicit, possibly-uncertain AL-score search -- the
    band a family typed directly into the shortlist filter, independent of
    whatever they entered into the Posting Group calculator above it (see
    the "explicit search" control in web/src/app.js:renderSchoolPrefs). Pass
    `lo_score == hi_score` (and the same groups for both) for a single exact
    score -- an "upper bound" search is the degenerate one-point case of a
    range, not a second code path, so within_reach() itself never needed
    duplicating.

    Still a FILTER, never a score: this never orders schools, and a caller
    only ever HIDES on one of the four strings below -- "out-of-reach" --
    exactly the way a plain within_reach()===False already only ever hid.
    The other three all stay visible; they differ only in which honest
    caveat a caller shows next to a school, the same "cannot judge" is not
    "no" principle within_reach()'s own None already follows.

        "in-reach"     -- in reach even at the band's WORSE (higher) end --
                          the strongest signal within_reach() can give.
        "possible"     -- in reach only near the band's BETTER (lower) end.
                          A caller must label this as depending on the
                          better end of the search, never as a plain match.
        "out-of-reach" -- not in reach anywhere across the band -- the one
                          state a shortlist filter actually hides on.
        "unknown"      -- PathAhead cannot judge at either end (no cut-off
                          published for this school, or a score fell
                          outside the published Posting Group table) --
                          shown, never hidden, same as within_reach()'s own
                          None.

    `lo_groups`/`hi_groups` are each end's own `PostingGroupResult.groups`
    (`engine/posting.py:resolve_posting_group`), resolved by the caller once
    per end -- exactly what within_reach() already expects for one score.
    """
    reach_worst = within_reach(school, hi_score, hi_groups, margin=margin)
    reach_best = within_reach(school, lo_score, lo_groups, margin=margin)
    if reach_worst is True:
        return "in-reach"
    if reach_best is True:
        return "possible"
    if reach_best is False and reach_worst is False:
        return "out-of-reach"
    return "unknown"


@dataclass(frozen=True, slots=True)
class SchoolMatch:
    """Whether one school should appear in a shortlist for one family --
    never how well it scores, because nothing here scores.

    `eligible` is the sex-based admission fact, not a preference:
      * True  -- co-ed, or single-sex and the right sex for this child
      * False -- single-sex and the WRONG sex for this child; not a real
                 option, and the only field here that hides a school
                 unconditionally, with no toggle to override it
      * None  -- single-sex and the child's sex has not been answered yet;
                 PathAhead cannot confirm either way, so a caller should
                 keep the school visible with a plain caveat rather than
                 guess -- the same "absence of data is not absence in
                 reality" rule `within_reach()` follows for a missing
                 cut-off.

    `matches_preferences` is True when the school satisfies every filter
    the family actually SET (gender, SAP, IP, Autonomous, GEP, school
    type). A filter left unset never counts against a school. True
    vacuously when nothing is set, so an unfiltered family sees every
    eligible school.

    `unmet` names which set filters this school failed to match -- kept
    for transparency and for tests, even though a caller will typically
    hide a non-matching school rather than show it with an explanation.
    """

    school_id: str
    eligible: bool | None
    eligibility_reason: str | None
    matches_preferences: bool
    unmet: tuple[str, ...] = ()
    #: Real straight-line km from the family's postal district to this
    #: school, when a postal code was given and both points are geocoded.
    #: Populated independently of eligibility/matches_preferences, so it is
    #: present even for a school a filter would hide.
    distance_km: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "school_id": self.school_id,
            "eligible": self.eligible,
            "eligibility_reason": self.eligibility_reason,
            "matches_preferences": self.matches_preferences,
            "unmet": list(self.unmet),
            "distance_km": self.distance_km,
        }


#: Shown once, above every shortlist, never per-school -- mirrors the old
#: NOT_AN_ADMISSION_ESTIMATE's placement, updated for a filter rather than
#: a ranking.
FILTER_DISCLAIMER = (
    "These are filters, not a ranking. Setting one hides schools that "
    "don't match it; the ones left are sorted by distance and name only, "
    "never by how closely they match what you asked for and never by how "
    "competitive a school is. PathAhead does not hold Posting Group data "
    "for individual schools beyond the published cut-off filter below, "
    "and even that never reorders anything -- see the Posting Group "
    "calculator on this page for a direct answer to what your child's "
    "score can reach."
)


def match_school(
    school: Mapping[str, Any],
    prefs: SchoolPreferences,
    *,
    district_index: Mapping[str, dict[str, Any]] | Pack | None = None,
) -> SchoolMatch:
    """Check one school against one family's filters.

    Same order as fit.py's score_outcome and within_reach() above: the one
    hard, unconditional fact (sex-based admission) is resolved first and
    independently of everything else; the family's own filters are then
    checked, but only the ones actually set. Nothing the family did not
    set ever counts against a school, and nothing PathAhead failed to load
    ever counts against a school either.
    """
    school_id = str(school.get("id", ""))

    # Computed once, independently of eligibility/filters below -- distance
    # is populated whenever a postal code was given, whether or not the
    # school ends up eligible or matching. It never gates or filters by
    # itself; a caller compares it against a chosen km band. See
    # distance_km()'s docstring.
    dist_km: float | None = None
    if prefs.postal_code:
        idx0 = (
            postal_sector_index(district_index)
            if isinstance(district_index, Pack)
            else (district_index or {})
        )
        home = resolve_district(idx0, prefs.postal_code)
        dist_km = distance_km(school, home)

    # ELIGIBILITY, checked first -- see SchoolMatch.eligible's docstring for
    # the three states. A single-sex school's admission policy is a fact
    # about the school, not a preference to filter on, and it is the only
    # thing here that can hide a school with no toggle to override it.
    eligible: bool | None = True
    eligibility_reason: str | None = None
    school_gender = school.get("gender")
    if school_gender in ("girls", "boys"):
        if prefs.student_sex is None:
            eligible = None
            eligibility_reason = (
                f"This is a {school_gender} school. PathAhead has not been told "
                "your child's sex, so it cannot confirm whether this school is "
                "even an option — answer that above and this will resolve one "
                "way or the other."
            )
        else:
            wrong_sex = (
                (school_gender == "girls" and prefs.student_sex == "male")
                or (school_gender == "boys" and prefs.student_sex == "female")
            )
            if wrong_sex:
                not_admits = "boys" if school_gender == "girls" else "girls"
                eligible = False
                eligibility_reason = (
                    f"This is a {school_gender} school; it does not admit "
                    f"{not_admits}. Not a preference to weigh — not a real "
                    "option for this child."
                )

    # PREFERENCE FILTERS -- each one only ever checked if the family set it.
    unmet: list[str] = []

    if prefs.gender and school.get("gender") != prefs.gender:
        unmet.append("gender")

    if prefs.want_sap is not None and bool(school.get("sap")) != prefs.want_sap:
        unmet.append("sap")

    if prefs.want_ip is not None and bool(school.get("ip")) != prefs.want_ip:
        unmet.append("ip")

    if prefs.want_autonomous is not None and bool(school.get("autonomous")) != prefs.want_autonomous:
        unmet.append("autonomous")

    if prefs.want_gifted is not None and bool(school.get("gifted")) != prefs.want_gifted:
        unmet.append("gifted")

    if prefs.school_types and school.get("type_label") not in set(prefs.school_types):
        unmet.append("school_type")

    return SchoolMatch(
        school_id=school_id,
        eligible=eligible,
        eligibility_reason=eligibility_reason,
        matches_preferences=not unmet,
        unmet=tuple(unmet),
        distance_km=dist_km,
    )


def match_all(pack: Pack, prefs: SchoolPreferences) -> dict[str, SchoolMatch]:
    """Match every school in the pack against one family's filters."""
    idx = postal_sector_index(pack)
    return {
        str(s["id"]): match_school(s, prefs, district_index=idx)
        for s in (pack.schools or ())
    }


def shortlist(
    pack: Pack, prefs: SchoolPreferences, *, limit: int | None = None
) -> list[tuple[dict[str, Any], SchoolMatch]]:
    """Every school paired with its match info, sorted by distance (when a
    postal code was given, closest first, unknown-distance last) and then
    by name -- never by anything resembling selectivity or preference
    match, per SAFEGUARDS.md 5.1 ("results sort by fit, programme and
    location -- never by selectivity descending"; this module no longer
    computes a "fit" number at all, so location and name are what is left).

    This function does NOT drop ineligible or non-matching schools itself
    -- that decision, and counting how many were hidden and why, belongs to
    the caller, exactly as it already does for the distance-band and reach
    filters. `limit` truncates for display only; matching itself always
    runs over the full pool.
    """
    matches = match_all(pack, prefs)
    by_id = {str(s["id"]): s for s in (pack.schools or ())}
    rows = [(by_id[sid], m) for sid, m in matches.items() if sid in by_id]
    rows.sort(key=lambda row: (
        row[1].distance_km is None,
        row[1].distance_km if row[1].distance_km is not None else 0.0,
        row[0]["name"],
    ))
    return rows[:limit] if limit else rows


def explain_school_match(match: SchoolMatch, school: Mapping[str, Any]) -> str:
    """Plain text derivation, same shape as fit.py's explain_fit."""
    lines = [f"School match — {school.get('name', match.school_id)}"]
    lines.append("")
    if match.eligible is False:
        lines.append(f"  Not an option: {match.eligibility_reason}")
        return "\n".join(lines)
    if match.eligible is None:
        lines.append(f"  Can't confirm yet: {match.eligibility_reason}")
        lines.append("")
    lines.append(f"  Matches your filters: {'yes' if match.matches_preferences else 'no'}")
    if match.unmet:
        lines.append(
            "  Did not match: "
            + ", ".join(DIMENSION_LABEL.get(k, k) for k in match.unmet)
        )
    if match.distance_km is not None:
        lines.append(f"  ≈{match.distance_km:g} km away (straight-line)")
    lines.append("")
    lines.append(f"  {FILTER_DISCLAIMER}")
    return "\n".join(lines)

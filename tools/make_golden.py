"""Generate the golden fixtures that keep the two engines honest.

PathAhead has two implementations of the same rule kinds: Python (engine/) and
JavaScript (web/index.html). That duplication buys a zero-install browser app
without shipping a 10 MB runtime to a phone -- but duplication only stays safe
if something checks it.

These fixtures are that something. Each one records a grade sheet and the exact
value AND full step trace the Python engine produced. CI replays every fixture
through the JS engine (tools/check_golden.mjs) and fails the build on any
disagreement beyond 1e-9.

Regenerate deliberately, never casually: a changed fixture is a changed answer
for a real family, and should be reviewed as such in the diff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine import GradeSheet, load_pack  # noqa: E402
from engine.fit import score_outcome, subject_families  # noqa: E402
from engine.forward import score  # noqa: E402
from engine.profile import StudentProfile  # noqa: E402
from engine.school_fit import (  # noqa: E402
    SchoolPreferences,
    combined_reach,
    match_school,
    within_reach,
)

#: Cases chosen to exercise every branch, including the awkward ones.
CASES: list[dict] = [
    {
        "id": "perfect-three-h2-and-gp",
        "why": "the ceiling, reached without any bonus subject",
        "year_level": "jc-2",
        "subjects": [
            {"level": "h2", "name": "Mathematics", "grade": "A"},
            {"level": "h2", "name": "Physics", "grade": "A"},
            {"level": "h2", "name": "Chemistry", "grade": "A"},
            {"level": "gp", "name": "General Paper", "grade": "A"},
        ],
    },
    {
        "id": "bonus-pushes-past-cap",
        "why": "the cap actually bites, and the trace must say so",
        "year_level": "jc-2",
        "subjects": [
            {"level": "h2", "name": "Chemistry", "grade": "A"},
            {"level": "h2", "name": "Biology", "grade": "A"},
            {"level": "h2", "name": "Mathematics", "grade": "B"},
            {"level": "gp", "name": "General Paper", "grade": "A"},
            {"level": "h1", "name": "Economics", "grade": "C"},
            {"level": "mtl", "name": "Chinese", "grade": "B"},
        ],
    },
    {
        "id": "four-h2-only-best-three-count",
        "why": "a fourth H2 must be excluded from the core, not silently added",
        "year_level": "jc-2",
        "subjects": [
            {"level": "h2", "name": "Mathematics", "grade": "A"},
            {"level": "h2", "name": "Physics", "grade": "B"},
            {"level": "h2", "name": "Chemistry", "grade": "C"},
            {"level": "h2", "name": "Economics", "grade": "D"},
            {"level": "gp", "name": "General Paper", "grade": "C"},
        ],
    },
    {
        "id": "mother-tongue-beats-fourth-subject",
        "why": "the substitution must pick the higher of the two candidates",
        "year_level": "jc-2",
        "subjects": [
            {"level": "h2", "name": "Literature", "grade": "B"},
            {"level": "h2", "name": "History", "grade": "B"},
            {"level": "h2", "name": "Economics", "grade": "C"},
            {"level": "gp", "name": "General Paper", "grade": "B"},
            {"level": "h1", "name": "Mathematics", "grade": "E"},
            {"level": "mtl", "name": "Malay", "grade": "A"},
        ],
    },
    {
        "id": "ungraded-subject-scores-zero",
        "why": "a U must score zero rather than raise an error or be dropped",
        "year_level": "jc-2",
        "subjects": [
            {"level": "h2", "name": "Mathematics", "grade": "C"},
            {"level": "h2", "name": "Physics", "grade": "D"},
            {"level": "h2", "name": "Chemistry", "grade": "U"},
            {"level": "gp", "name": "General Paper", "grade": "E"},
        ],
    },
    {
        "id": "jc1-cohort-next-years-exam",
        "why": "cohort routing: JC1 sits the exam a year later and must still resolve",
        "year_level": "jc-1",
        "subjects": [
            {"level": "h2", "name": "Mathematics", "grade": "B"},
            {"level": "h2", "name": "Chemistry", "grade": "B"},
            {"level": "h2", "name": "Biology", "grade": "B"},
            {"level": "gp", "name": "General Paper", "grade": "C"},
        ],
    },
    # -- PSLE -------------------------------------------------------------
    #
    # These are the first fixtures on a SECOND rule kind, and they exist
    # because of what happened the last time a gate was added: the cross-engine
    # check passed 11 of 11 on code it had never run. A `lowest_sum` rule in
    # the browser that nothing replays is not verified, it is merely present.
    # Every branch of it is exercised below -- a plain sheet, a Foundation
    # substitution, the best possible score and the weakest one inside the
    # published Posting Group table.
    {
        "id": "psle-typical-four-subjects",
        "why": "the ordinary case: four Standard subjects, summed, lower is better",
        "year_level": "pri-6",
        "subjects": [
            {"code": "psle-english", "name": "English Language", "grade": "AL3"},
            {"code": "psle-mathematics", "name": "Mathematics", "grade": "AL1"},
            {"code": "psle-science", "name": "Science", "grade": "AL2"},
            {"code": "psle-mtl", "name": "Mother Tongue Language", "grade": "AL2"},
        ],
    },
    {
        "id": "psle-best-possible-score",
        "why": "the floor of the scale. Four AL1s is a PSLE Score of 4, not of 0",
        "year_level": "pri-6",
        "subjects": [
            {"code": "psle-english", "name": "English Language", "grade": "AL1"},
            {"code": "psle-mathematics", "name": "Mathematics", "grade": "AL1"},
            {"code": "psle-science", "name": "Science", "grade": "AL1"},
            {"code": "psle-mtl", "name": "Mother Tongue Language", "grade": "AL1"},
        ],
    },
    {
        "id": "psle-foundation-subject-substitutes",
        "why": (
            "a Foundation subject satisfies the Standard requirement and maps to "
            "AL6-AL8. Both engines must accept the sheet as complete -- reporting "
            "a missing subject here would be wrong, and to a parent it reads as "
            "an accusation about their child"
        ),
        "year_level": "pri-6",
        "subjects": [
            {"code": "psle-english", "name": "English Language", "grade": "AL5"},
            {
                "code": "psle-mathematics-foundation",
                "name": "Foundation Mathematics",
                "grade": "A",
            },
            {"code": "psle-science", "name": "Science", "grade": "AL6"},
            {"code": "psle-mtl", "name": "Mother Tongue Language", "grade": "AL7"},
        ],
    },
    {
        "id": "psle-all-foundation-subjects",
        "why": "every subject at Foundation level: FA/FB/FC must all map, and the label must never show 'FA'",
        "year_level": "pri-6",
        "subjects": [
            {"code": "psle-english-foundation", "name": "Foundation English Language", "grade": "A"},
            {"code": "psle-mathematics-foundation", "name": "Foundation Mathematics", "grade": "B"},
            {"code": "psle-science-foundation", "name": "Foundation Science", "grade": "C"},
            {"code": "psle-mtl-foundation", "name": "Foundation Mother Tongue Language", "grade": "B"},
        ],
    },
    {
        "id": "psle-p5-cohort-next-years-exam",
        "why": "cohort routing on a second stage: P5 resolves to the same transition a year out",
        "year_level": "pri-5",
        "subjects": [
            {"code": "psle-english", "name": "English Language", "grade": "AL6"},
            {"code": "psle-mathematics", "name": "Mathematics", "grade": "AL5"},
            {"code": "psle-science", "name": "Science", "grade": "AL6"},
            {"code": "psle-mtl", "name": "Mother Tongue Language", "grade": "AL4"},
        ],
    },
    # -- O-Level / SEC ------------------------------------------------------
    #
    # A THIRD rule kind, `required_plus_best_n` -- the L1R5/L1R4/ELR2B2 shape.
    # Same lesson as the PSLE fixtures above, applied again: a rule kind that
    # exists in Python and is merely assumed to exist in JS is not verified.
    # These exercise the groups mechanism directly -- a compulsory subject, a
    # single-take group, a group drawing from TWO tag pools at once (R3), the
    # "any N remaining" group with no pool restriction, and the letter-number
    # grade spelling ("A2", "B3") a family actually types.
    {
        "id": "olevel-l1r5-typical-seven-subjects",
        "why": (
            "the ordinary case: 7 subjects entered, L1R5 picks English + best "
            "Humanities + best Math/Science + best remaining of either + best "
            "2 of everything left. Exercises every group in one pass"
        ),
        "transition_id": "o-level-to-jc-mi-2027",
        "year_level": "sec-4",
        "subjects": [
            {"code": "ol-english", "name": "English Language", "grade": "A2"},
            {"code": "ol-elit", "name": "English Literature", "grade": "B3"},
            {"code": "ol-history", "name": "History", "grade": "A1"},
            {"code": "ol-emath", "name": "Mathematics", "grade": "A1"},
            {"code": "ol-amath", "name": "Additional Mathematics", "grade": "B4"},
            {"code": "ol-physics", "name": "Physics", "grade": "A2"},
            {"code": "ol-chemistry", "name": "Chemistry", "grade": "B3"},
        ],
    },
    {
        "id": "olevel-l1r5-best-possible-score",
        "why": "the floor of the scale: six A1s is an L1R5 of 6, not of 0",
        "transition_id": "o-level-to-jc-mi-2027",
        "year_level": "sec-4",
        "subjects": [
            {"code": "ol-english", "name": "English Language", "grade": "A1"},
            {"code": "ol-history", "name": "History", "grade": "A1"},
            {"code": "ol-emath", "name": "Mathematics", "grade": "A1"},
            {"code": "ol-physics", "name": "Physics", "grade": "A1"},
            {"code": "ol-chemistry", "name": "Chemistry", "grade": "A1"},
            {"code": "ol-biology", "name": "Biology", "grade": "A1"},
        ],
    },
    {
        "id": "olevel-l1r5-only-one-humanities-subject",
        "why": (
            "with a single Humanities subject, R1 consumes it and R3 must fall "
            "back to the Mathematics/Science pool entirely -- proving `used` "
            "correctly empties the Humanities pool rather than reusing R1's pick"
        ),
        "transition_id": "o-level-to-jc-mi-2027",
        "year_level": "sec-4",
        "subjects": [
            {"code": "ol-english", "name": "English Language", "grade": "B3"},
            {"code": "ol-combined-humanities", "name": "Combined Humanities", "grade": "C5"},
            {"code": "ol-emath", "name": "Mathematics", "grade": "A2"},
            {"code": "ol-amath", "name": "Additional Mathematics", "grade": "B3"},
            {"code": "ol-physics", "name": "Physics", "grade": "B4"},
            {"code": "ol-chemistry", "name": "Chemistry", "grade": "C5"},
        ],
    },
    {
        "id": "sec-l1r4-2028-cohort",
        "why": (
            "the SEC-era formula on a different cohort and a different ceiling: "
            "4 subjects, not 5, and this transition carries NO course outcomes "
            "yet -- the derivation must still be complete and correct on its own"
        ),
        "transition_id": "sec-to-jc-mi-2028",
        "year_level": "sec-3",
        "subjects": [
            {"code": "ol-english", "name": "English Language", "grade": "A2"},
            {"code": "ol-geography", "name": "Geography", "grade": "B3"},
            {"code": "ol-emath", "name": "Mathematics", "grade": "A1"},
            {"code": "ol-physics", "name": "Physics", "grade": "B4"},
            {"code": "ol-chemistry", "name": "Chemistry", "grade": "A2"},
        ],
    },
    {
        "id": "olevel-elr2b2-generic-polytechnic",
        "why": (
            "the polytechnic-facing transition: English plus the best 4 "
            "remaining, no tag restriction on the second group at all -- the "
            "simplest group shape, and the one most likely to be got right by "
            "accident if the tagged groups above were wrong"
        ),
        "transition_id": "o-level-to-polytechnic-2027",
        "year_level": "sec-4",
        "subjects": [
            {"code": "ol-english", "name": "English Language", "grade": "B3"},
            {"code": "ol-emath", "name": "Mathematics", "grade": "A2"},
            {"code": "ol-combined-science", "name": "Combined Science", "grade": "B4"},
            {"code": "ol-poa", "name": "Principles of Accounts", "grade": "C5"},
            {"code": "ol-art", "name": "Art", "grade": "A1"},
            {"code": "ol-history", "name": "History", "grade": "C6"},
        ],
    },
]


#: Fit profiles, replayed through both engines. Fit now exists twice as well,
#: so it gets the same parity guarantee the scoring rules do -- otherwise the
#: browser could quietly disagree with the CLI about why a course suits you.
FIT_CASES: list[dict] = [
    {
        "id": "fit-subject-gate-blocked",
        "why": (
            "the reported bug: a student with no Physics must get NO score on "
            "Applied Physics from EITHER engine. If the two disagree here, the "
            "website and the app tell one family two different things about "
            "whether a door is open."
        ),
        "profile": {
            "interests": ["I"],
            "enjoyed_subjects": ["economics"],
            "subjects_offered": ["mathematics", "economics", "literature"],
            "assessment_style": "exams",
            "teamwork": "individual",
        },
    },
    {
        "id": "fit-subject-gate-satisfied-by-family",
        "why": (
            "Further Mathematics satisfies a Mathematics requirement, in both "
            "engines. Blocking here would take away a course the student is "
            "plainly qualified for, which is the costlier direction to be "
            "wrong in."
        ),
        "profile": {
            "interests": ["I"],
            "subjects_offered": ["further-mathematics", "physics", "chemistry"],
            "assessment_style": "exams",
            "teamwork": "individual",
        },
    },
    {
        "id": "fit-technical-individual",
        "why": "every factor engaged, including a zero-scoring one",
        "profile": {
            "interests": ["I", "R"],
            "enjoyed_subjects": ["mathematics", "computing"],
            "assessment_style": "coursework",
            "teamwork": "individual",
            "priorities": ["earnings", "stability"],
            "willing_extra_assessment": False,
            "cost_sensitive": True,
            "goal_text": "build things people actually use",
        },
    },
    {
        "id": "fit-caring-team",
        "why": "a different student must get a different ordering",
        "profile": {
            "interests": ["S"],
            "enjoyed_subjects": ["biology", "chemistry"],
            "assessment_style": "practical",
            "teamwork": "team",
            "willing_extra_assessment": True,
        },
    },
    {
        "id": "fit-regression-further-maths-real-session",
        "why": (
            "the real session that shipped broken: Further Mathematics must count as "
            "mathematics, and courses with no survey data must not be marked down for it"
        ),
        "profile": {
            "interests": ["R", "A", "C"],
            "enjoyed_subjects": ["further-mathematics"],
            "priorities": ["earnings", "impact", "autonomy", "stability"],
        },
    },
    {
        "id": "fit-below-minimum-signals",
        "why": "one answer must produce no score at all, not a misleading 50",
        "profile": {"interests": ["A"]},
    },
    {
        "id": "fit-no-answers",
        "why": "an empty profile must decline to score",
        "profile": {},
    },
]

#: Outcomes the fit fixtures are checked against -- deliberately spanning a
#: technical course, a caring one, and one that requires an interview.
# Two of these carry PUBLISHED SUBJECT PREREQUISITES, and that is the point.
# The first version of this list held four NUS courses with no requirements
# between them, so when the subject gate was added every fixture still agreed
# and the parity check proved nothing about the new code. A cross-engine test
# that cannot fail is a green light with the bulb taken out.
FIT_OUTCOMES = [
    "nus-computer-science",
    "nus-nursing",
    "nus-medicine",
    "nus-humanities-sciences",
    "ntu-physics-applied-physics",   # H2 Physics and H2 Mathematics
    "ntu-mathematical-sciences",     # H2 Mathematics, satisfied by Further Maths
]


#: School-fit preference cases, replayed through both engines exactly like
#: FIT_CASES above. Each names the specific schools it needs to prove its
#: point -- chosen once, here, by querying the compiled pack for a concrete
#: example of each trait (a SAP school, an IP school, a girls' school, and so
#: on) rather than hardcoding ids that happen to work today and rot silently
#: if the pack is ever regenerated with a different school list.
SCHOOL_MATCH_CASES: list[dict] = [
    {
        "id": "school-match-no-filters",
        "why": "nothing set must match every eligible school -- an unfiltered family sees the whole pool",
        "preferences": {},
        "schools": ["admiralty-secondary-school", "anglican-high-school"],
    },
    {
        "id": "school-match-one-filter-is-enough",
        "why": (
            "a single filter hides a non-matching school outright. "
            "student_sex is set to 'female' purely so the (separately "
            "tested) sex-eligibility gate does not mask this case's actual "
            "point: a girls' school CHIJ Katong is eligible for a girl, and "
            "still fails to match because it is not co-ed"
        ),
        "preferences": {"gender": "co-ed", "student_sex": "female"},
        "schools": ["admiralty-secondary-school", "chij-katong-convent"],
    },
    {
        "id": "school-match-distance-km-with-a-postal-code",
        "why": (
            "distance_km is informational and drives the shortlist's sort "
            "order and the separate km-band filter, never a match dimension "
            "here -- this case exists to keep the two engines' haversine "
            "arithmetic in agreement, not to test filtering"
        ),
        "preferences": {"postal_code": "737916"},  # Admiralty's own postal code
        "schools": [
            "admiralty-secondary-school",
            "ahmad-ibrahim-secondary-school",
            "beatty-secondary-school",
        ],
    },
    {
        "id": "school-match-wanting-every-trait",
        "why": "every 'want' filter engaged at once, against schools that do and do not have each trait",
        "preferences": {
            "want_sap": True, "want_ip": True, "want_autonomous": True, "want_gifted": True,
            "school_types": ["Independent school"],
        },
        "schools": [
            "anglican-high-school",              # sap, not ip/autonomous/gifted/independent
            "anglo-chinese-school-independent",   # ip, gifted, independent -- not sap
            "anderson-secondary-school",          # autonomous, not the others
            "admiralty-secondary-school",         # none of the above
        ],
    },
    {
        "id": "school-match-sex-eligibility-gate",
        "why": (
            "the fix for the 2026-08-13 review finding: a single-sex school "
            "must be INELIGIBLE, never merely a non-match, for a student who "
            "cannot attend it -- and unconfirmed for a different, clearly "
            "stated reason when student_sex is simply not yet known. Checked "
            "before any preference filter, independent of every one of them. "
            "A postal code is also set here to prove distance_km is "
            "populated even for a school this gate has just excluded -- "
            "distance is informational and never gated"
        ),
        "preferences": {
            "student_sex": "male", "want_sap": True, "want_ip": True, "want_autonomous": True,
            "postal_code": "737916",
        },
        "schools": [
            "chij-katong-convent",         # girls' school -- wrong sex, must be ineligible
            "anglo-chinese-school-barker-road",  # boys' school -- right sex, must match normally
            "admiralty-secondary-school",  # co-ed -- gate never applies, must match normally
        ],
    },
    {
        "id": "school-match-sex-unknown-gates-single-sex-schools-only",
        "why": "no student_sex at all must gate girls'/boys' schools specifically, not co-ed ones",
        "preferences": {"want_sap": True},
        "schools": [
            "chij-katong-convent",  # girls' school -- sex unknown, must be unconfirmed
            "admiralty-secondary-school",  # co-ed -- must still match normally
        ],
    },
    {
        "id": "school-match-avoiding-every-trait",
        "why": "the mirror image: 'avoid SAP/IP/Autonomous/Gifted' must match the traits' ABSENCE, not just skip them",
        "preferences": {
            "want_sap": False, "want_ip": False, "want_autonomous": False, "want_gifted": False,
        },
        "schools": [
            "admiralty-secondary-school",         # has none of the four -- should match
            "anglo-chinese-school-independent",   # has ip and gifted -- should not match
        ],
    },
]

#: within_reach() cases -- the cut-off FILTER, never a score.
#:
#: Each case carries its OWN synthetic school rather than naming one from the
#: pack, because as of 2026-08-14 the pack contains no cut-off figures at all:
#: PathAhead does not republish them, and the app deep-links to MOE
#: SchoolFinder instead (see engine/loader.py:_apply_local_overlays). Fixtures
#: that read figures out of the pack would compare None against None on every
#: machine except one holding a private overlay -- passing while proving
#: nothing, which is worse than failing.
#:
#: Owning the numbers also makes each case readable on its own terms. A band
#: is [first_posted, last_posted]; within_reach reads the second, the cut-off
#: proper. With pg3 at 22 and the default margin of 2, 24 is the highest score
#: still "in reach" and 25 is the first "no".
WITHIN_REACH_CASES: list[dict] = [
    {
        "id": "within-reach-clear-yes",
        "why": "a score comfortably inside the cut-off is in reach",
        "school": {"pg3": [16, 22]},
        "psle_score": 20, "family_groups": [3], "margin": 2,
    },
    {
        "id": "within-reach-margin-boundary",
        "why": "a score exactly cutoff+margin is still in reach -- the margin exists precisely for this case",
        "school": {"pg3": [16, 22]},
        "psle_score": 24, "family_groups": [3], "margin": 2,
    },
    {
        "id": "within-reach-clear-no",
        "why": "one point past cutoff+margin is genuinely out of reach",
        "school": {"pg3": [16, 22]},
        "psle_score": 25, "family_groups": [3], "margin": 2,
    },
    {
        "id": "within-reach-no-cutoff-held-is-unknown-not-no",
        "why": (
            "no cutoff held for this school -- whether because it admits through a "
            "specialised route, or (the shipped case) because PathAhead does not "
            "republish these figures -- must answer None, never False. 'Cannot tell' "
            "is not the same claim as 'not in reach'"
        ),
        "school": None,
        "psle_score": 10, "family_groups": [3], "margin": 2,
    },
    {
        "id": "within-reach-score-outside-posting-table-is-unknown",
        "why": "empty family_groups (score outside the published Posting Group table) must also answer None",
        "school": {"pg3": [16, 22]},
        "psle_score": 31, "family_groups": [], "margin": 2,
    },
    {
        "id": "within-reach-group-with-no-published-band-is-unknown",
        "why": (
            "a school with PG3/PG2 but no PG1 band -- a family in PG1 must get None "
            "for THIS school, not a false negative from a band that was never published"
        ),
        "school": {"pg3": [16, 22], "pg2": [21, 25]},
        "psle_score": 26, "family_groups": [1], "margin": 2,
    },
    {
        "id": "within-reach-a-choice-between-groups-checks-either",
        "why": (
            "a score that opens a CHOICE between two Posting Groups (family_groups has 2 entries) "
            "is in reach if EITHER group's cutoff would admit it -- the family could choose that one"
        ),
        "school": {"pg3": [16, 22], "pg2": [21, 25]},
        "psle_score": 27, "family_groups": [2, 3], "margin": 2,
    },
]


#: combined_reach() cases -- the EXPLICIT AL-score search (a single score,
#: or a range for a family working from an estimate rather than a result),
#: independent of the Posting Group calculator elsewhere on the page. Each
#: case reuses a WITHIN_REACH_CASES-style synthetic school; see that list's
#: own comment for why the school travels with the fixture rather than
#: being looked up in the pack.
COMBINED_REACH_CASES: list[dict] = [
    {
        "id": "combined-reach-both-ends-in-reach",
        "why": "the whole range clears the cut-off -- the strongest signal, shown as in-reach",
        "school": {"pg3": [16, 22]},
        "lo_score": 18, "hi_score": 20, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
    {
        "id": "combined-reach-only-the-better-end-clears",
        "why": (
            "the better (lower) end of the range is in reach but the worse end is not -- "
            "'possible', never plain in-reach, so a caller cannot present it as a match"
        ),
        "school": {"pg3": [16, 22]},
        "lo_score": 20, "hi_score": 27, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
    {
        "id": "combined-reach-neither-end-clears",
        "why": "not in reach anywhere across the range -- the one state a shortlist filter actually hides on",
        "school": {"pg3": [16, 22]},
        "lo_score": 26, "hi_score": 30, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
    {
        "id": "combined-reach-no-cutoff-held-is-unknown",
        "why": "no cut-off held for this school -- must answer unknown, never out-of-reach",
        "school": None,
        "lo_score": 10, "hi_score": 12, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
    {
        "id": "combined-reach-exact-score-degenerate-range",
        "why": (
            "an 'upper bound' search is lo_score==hi_score with the same groups at both ends -- "
            "this must equal a plain within_reach() call, not a second, subtly different code path"
        ),
        "school": {"pg3": [16, 22]},
        "lo_score": 24, "hi_score": 24, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
    {
        "id": "combined-reach-exact-score-degenerate-range-out-of-reach",
        "why": "the same degenerate-range identity, one point past the margin -- must be out-of-reach",
        "school": {"pg3": [16, 22]},
        "lo_score": 25, "hi_score": 25, "lo_groups": [3], "hi_groups": [3], "margin": 2,
    },
]


def _synthetic_school(bands: dict | None) -> dict:
    """A school row shaped the way within_reach() reads one, from a fixture's
    own `school` field. `None` means no cut-off held at all."""
    if bands is None:
        return {"id": "fixture-school", "cutoff_current": None}
    return {
        "id": "fixture-school",
        "cutoff_current": {k: bands.get(k) for k in ("pg3", "pg2", "pg1", "ip")},
    }


def generate(pack_dir: Path, out_dir: Path) -> Path:
    pack = load_pack(pack_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for case in CASES:
        # Most fixtures resolve their transition the way a real student does:
        # from the year level, through cohort routing. A few -- the ones
        # naming a SECOND transition scored from the same grade sheet, like
        # the O-Level-to-polytechnic ELR2B2 case -- name `transition_id`
        # directly, the same way engine/forward.py:explore_secondary() does,
        # because cohort resolution only ever points at ONE transition and
        # the second one is reached without it.
        if "transition_id" in case:
            transition = pack.transitions[case["transition_id"]]
        else:
            cohort = pack.cohort_rules[case["year_level"]]
            transition = pack.transitions[cohort.transition_id]
        grades = GradeSheet.from_dicts(transition.stage_id, case["subjects"])
        derivation = score(pack, grades, transition)
        fixtures.append(
            {
                "id": case["id"],
                "why": case["why"],
                "pack": pack.id,
                "pack_version": pack.version,
                "transition": transition.id,
                "year_level": case.get("year_level"),
                "subjects": grades.to_dict()["subjects"],
                "expected": derivation.to_dict(),
            }
        )
    fam = subject_families(pack)
    fit_fixtures = []
    for case in FIT_CASES:
        profile = StudentProfile.from_dict(case["profile"])
        expected = {}
        for oid in FIT_OUTCOMES:
            fit = score_outcome(pack.outcomes[oid], profile, families=fam)
            expected[oid] = {
                "score": fit.score,
                "unscored_reason": fit.unscored_reason,
                "not_assessed": list(fit.not_assessed),
                "factors": [
                    {"label": f.label, "points": f.points, "max_points": f.max_points}
                    for f in fit.factors
                ],
            }
        fit_fixtures.append(
            {
                "id": case["id"],
                "why": case["why"],
                "profile": case["profile"],
                "outcomes": FIT_OUTCOMES,
                "expected": expected,
            }
        )

    schools_by_id = {s["id"]: s for s in pack.schools}
    school_match_fixtures = []
    for case in SCHOOL_MATCH_CASES:
        prefs = SchoolPreferences(
            postal_code=case["preferences"].get("postal_code"),
            student_sex=case["preferences"].get("student_sex"),
            gender=case["preferences"].get("gender"),
            want_sap=case["preferences"].get("want_sap"),
            want_ip=case["preferences"].get("want_ip"),
            want_autonomous=case["preferences"].get("want_autonomous"),
            want_gifted=case["preferences"].get("want_gifted"),
            school_types=tuple(case["preferences"].get("school_types", ())),
        )
        expected = {}
        for sid in case["schools"]:
            m = match_school(schools_by_id[sid], prefs, district_index=pack)
            expected[sid] = {
                "eligible": m.eligible,
                "eligibility_reason": m.eligibility_reason,
                "matches_preferences": m.matches_preferences,
                "unmet": list(m.unmet),
                "distance_km": m.distance_km,
            }
        school_match_fixtures.append(
            {
                "id": case["id"],
                "why": case["why"],
                "preferences": case["preferences"],
                "schools": case["schools"],
                "expected": expected,
            }
        )

    within_reach_fixtures = []
    for case in WITHIN_REACH_CASES:
        school = _synthetic_school(case["school"])
        got = within_reach(
            school, case["psle_score"], tuple(case["family_groups"]),
            margin=case["margin"],
        )
        within_reach_fixtures.append(
            {
                "id": case["id"],
                "why": case["why"],
                # The full school row travels WITH the fixture, so
                # check_golden.mjs feeds the JS engine exactly the same input
                # rather than looking anything up in a pack that no longer
                # carries cut-off figures.
                "school": school,
                "psle_score": case["psle_score"],
                "family_groups": case["family_groups"],
                "margin": case["margin"],
                "expected": got,
            }
        )

    combined_reach_fixtures = []
    for case in COMBINED_REACH_CASES:
        school = _synthetic_school(case["school"])
        got = combined_reach(
            school, case["lo_score"], case["hi_score"],
            tuple(case["lo_groups"]), tuple(case["hi_groups"]),
            margin=case["margin"],
        )
        combined_reach_fixtures.append(
            {
                "id": case["id"],
                "why": case["why"],
                # Same reasoning as within_reach_fixtures above: the school
                # travels WITH the fixture so check_golden.mjs feeds the JS
                # engine identical input rather than reading cut-off figures
                # out of a pack that no longer carries any.
                "school": school,
                "lo_score": case["lo_score"],
                "hi_score": case["hi_score"],
                "lo_groups": case["lo_groups"],
                "hi_groups": case["hi_groups"],
                "margin": case["margin"],
                "expected": got,
            }
        )

    path = out_dir / "rules.json"
    path.write_text(
        json.dumps(
            {
                "generated_by": "tools/make_golden.py",
                "cases": fixtures,
                "fit_cases": fit_fixtures,
                "school_match_cases": school_match_fixtures,
                "within_reach_cases": within_reach_fixtures,
                "combined_reach_cases": combined_reach_fixtures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def main() -> int:
    path = generate(REPO / "packs" / "singapore", REPO / "evals" / "golden")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"wrote {len(data['cases'])} golden case(s) -> {path}")
    for c in data["cases"]:
        print(f"  {c['id']:<38}{c['expected']['value']:g}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

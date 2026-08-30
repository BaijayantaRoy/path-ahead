"""The pathway graph: the shapes every country pack is made of.

Five entities, and one envelope that wraps every single number:

    Cohort        who the student is, in time  -> resolves to a rule version
    Stage         an exam (PSLE, A-Level, SEC)
    Transition    the admission decision after a Stage, governed by a ScoringRule
    Outcome       a destination (a course at a university, a JC, a poly diploma)
    Prerequisite  a subject/qualification edge that a Route depends on
    Route         a way to reach an Outcome, direct or otherwise

The envelope is `Fact`. The engine refuses to surface a bare number: every
value carries its year, its source, its confidence and its expiry. That single
constraint is what separates this from every calculator site on the web.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

# Engine <-> pack compatibility. Bump ONLY on a breaking pack schema change.
PACK_FORMAT = 1

Confidence = Literal["high", "medium", "low"]

CONFIDENCE_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

#: What KIND of claim a value is -- which is a different question from how
#: confident we are in it.
#:
#:   "official"  -- a figure published by an institution or agency. A fact.
#:                  Confidence says how well-sourced it is.
#:   "editorial" -- PathAhead's own characterisation of a course ("suits
#:                  hands-on learners"). NOT a fact, and not something the
#:                  institution said. Rendered differently, never mixed with
#:                  official figures, and always carrying an invitation to
#:                  disagree.
#:
#: Conflating these would be the quiet way this project loses its integrity:
#: "we're unsure of this fact" and "this is an opinion" are not the same thing.
Basis = Literal["official", "editorial"]

#: Licence identifiers a source may declare. Obligations travel with the data
#: so the attribution block can be generated rather than hand-maintained.
KNOWN_LICENCES = {
    "sg-odl-1.0": (
        "Singapore Open Data Licence v1.0",
        "https://data.gov.sg/open-data-licence",
        True,  # redistributable
    ),
    "moe-tou": (
        "MOE Terms of Use (facts cited and linked; no content reproduced)",
        "https://www.moe.gov.sg/terms-of-use",
        False,
    ),
    # Distinct from `moe-tou` on purpose. `moe-tou` means "PathAhead holds a
    # figure from this source and shows it, relying on the fact/expression
    # distinction". `moe-tou-linked` means "PathAhead holds NOTHING from this
    # source and sends the reader to it" -- the strongest possible position,
    # used where the material is a substantial dataset rather than an
    # isolated fact and copying it would be reproduction whatever the
    # fact/expression argument says. Introduced 2026-08-14 when the
    # per-school Posting Group cut-offs were removed from the published pack
    # in favour of a deep link. See tools/build_secondary_schools_pack.py.
    "moe-tou-linked": (
        "MOE Terms of Use (linked at source; nothing reproduced here)",
        "https://www.moe.gov.sg/terms-of-use",
        False,
    ),
    "institution-tou": (
        "Institution website terms of use (facts cited and linked)",
        None,
        False,
    ),
    "derived": ("Derived by PathAhead from cited sources", None, True),
}


def _parse_date(value: Any, field_name: str) -> _dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{field_name}: expected an ISO date (YYYY-MM-DD), got {value!r}") from exc


# --------------------------------------------------------------------------
# The envelope
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Source:
    """Where a number came from, and what may legally be done with it."""

    id: str
    name: str
    publisher: str
    url: str
    retrieved: _dt.date
    licence: str
    note: str | None = None

    @property
    def licence_name(self) -> str:
        return KNOWN_LICENCES.get(self.licence, (self.licence, None, False))[0]

    @property
    def licence_url(self) -> str | None:
        """The licence's own canonical page, where one exists.

        Not decoration. The Singapore Open Data Licence v1.0 requires that any
        product using an ODL dataset carry "a conspicuous notice acknowledging
        the source of the datasets and including a link to the most recent
        version of this Licence". That link has to reach the reader, so it has
        to reach the UI -- which means it has to survive pack compilation
        rather than living only in this table. Added 2026-08-14, when a review
        found the app rendering the bare string "sg-odl-1.0" and satisfying
        the condition nowhere but the README.
        """
        return KNOWN_LICENCES.get(self.licence, (None, None, False))[1]

    @property
    def redistributable(self) -> bool:
        return KNOWN_LICENCES.get(self.licence, (None, None, False))[2]

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Source:
        return cls(
            id=str(d["id"]),
            name=str(d["name"]),
            publisher=str(d.get("publisher", d["name"])),
            url=str(d["url"]),
            retrieved=_parse_date(d["retrieved"], "retrieved"),  # type: ignore[arg-type]
            licence=str(d.get("licence", "institution-tou")),
            note=d.get("note"),
        )


@dataclass(frozen=True, slots=True)
class Fact:
    """A value that knows its own provenance and its own expiry date.

    `stale_after` is the date past which this figure should no longer be
    presented as current -- typically the next publication cycle. The UI greys
    a stale fact and links to the official page rather than hiding the age.
    """

    value: Any
    as_of_year: int
    source_id: str
    confidence: Confidence = "medium"
    stale_after: _dt.date | None = None
    note: str | None = None
    basis: Basis = "official"
    #: The exact page this ONE figure came from, where that is narrower than
    #: the source's own URL.
    #:
    #: A source is a publication -- "NUS tuition fees", "SP course pages" --
    #: and a source-level link is the right citation when one page carries
    #: every figure drawn from it. It is the WRONG citation when the source is
    #: really a set of pages: Singapore Polytechnic publishes an aggregate
    #: range on each of thirty-four separate course pages, so citing
    #: sp.edu.sg/courses/diplomas for all of them sends a reader to a listing
    #: and asks them to go and find it.
    #:
    #: Empty means "the source's URL is the right link", which is the common
    #: case and not a gap. `citation_url` resolves the two, so callers never
    #: have to know which applies.
    url: str | None = None

    @property
    def is_editorial(self) -> bool:
        return self.basis == "editorial"

    def is_stale(self, today: _dt.date | None = None) -> bool:
        if self.stale_after is None:
            return False
        return (today or _dt.date.today()) > self.stale_after

    def days_until_stale(self, today: _dt.date | None = None) -> int | None:
        if self.stale_after is None:
            return None
        return (self.stale_after - (today or _dt.date.today())).days

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Fact:
        return cls(
            value=d["value"],
            as_of_year=int(d["as_of_year"]),
            source_id=str(d["source"]),
            confidence=d.get("confidence", "medium"),
            stale_after=_parse_date(d.get("stale_after"), "stale_after"),
            note=d.get("note"),
            basis=d.get("basis", "official"),
            url=(str(d["url"]).strip() or None) if d.get("url") else None,
        )

    def citation_url(self, pack: Pack | None = None) -> str | None:
        """Where a reader should click to check THIS figure.

        The fact's own page if it has one, otherwise the source's. Callers get
        the most specific link available without having to know which exists,
        which is the point: a citation that is one click from the number is a
        citation people actually follow.
        """
        if self.url:
            return self.url
        if pack is None:
            return None
        src = pack.sources.get(self.source_id)
        return getattr(src, "url", None) if src else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "as_of_year": self.as_of_year,
            "source": self.source_id,
            "confidence": self.confidence,
            "stale_after": self.stale_after.isoformat() if self.stale_after else None,
            "note": self.note,
            "basis": self.basis,
            "url": self.url,
        }


# --------------------------------------------------------------------------
# Cohort -- the first thing a user knows about themselves
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CohortRule:
    """Maps 'what year is your child in now' to a rule version.

    Declared in the pack, never inferred by the engine, because the mapping is
    a policy fact like any other and must carry a source.
    """

    year_level: str            # "jc-2", "sec-4", "pri-6"
    label: str                 # "Junior College 2"
    stage_id: str              # "a-level"
    years_to_exam: int         # 0 = sits the exam this calendar year
    admission_offset: int      # exam_year + offset = admission year
    transition_id: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CohortResolution:
    """The engine's answer to 'which rulebook applies to me', in full.

    Deliberately verbose: the UI reads this back to the user in plain words so
    a wrong answer to the very first question is caught immediately, rather
    than silently producing a confident result under the wrong formula.
    """

    year_level: str
    label: str
    current_year: int
    stage_id: str
    exam_year: int
    admission_year: int
    transition_id: str
    note: str | None = None

    def sentence(self) -> str:
        return (
            f"{self.label} in {self.current_year} means sitting {self.stage_id.upper()} "
            f"in {self.exam_year}, applying for admission in {self.admission_year}."
        )


# --------------------------------------------------------------------------
# Graph entities
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Stage:
    id: str
    name: str
    authority: str
    typical_age: str
    description: str
    subject_levels: tuple[str, ...] = ()


class OverlayKind(str, Enum):
    """Things a formula cannot capture, which must never be silently dropped."""

    INTERVIEW = "interview"
    PORTFOLIO = "portfolio"
    APTITUDE_TEST = "aptitude_test"
    AUDITION = "audition"
    DSA = "dsa"
    SUBJECT_REQUIREMENT = "subject_requirement"


@dataclass(frozen=True, slots=True)
class Overlay:
    kind: OverlayKind
    label: str
    detail: str
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class BandYear:
    """One earlier year of the same published figure, kept verbatim.

    Prior years are carried BESIDE the current band, never merged into it.
    Merging three years of min-max into one wider min-max would produce a
    number no institution ever published, and it would widen with every year
    added -- so a course would look less and less selective the longer
    PathAhead had been running. Each year is one exercise and stays one
    exercise; what the reader gets is the movement between them, which is the
    honest thing three years of data actually tells you.
    """

    year: int
    low: float
    high: float
    label: str      # verbatim as published, e.g. "10 to 17"


@dataclass(frozen=True, slots=True)
class GradeBand:
    """Two published endpoints and a statement of what the endpoints MEAN.

    NOT a cutoff. The engine never compares against a single threshold, because
    the publishers themselves do not publish one.

    Two different published statistics share this structure, and the difference
    between them is the whole reason `statistic` exists:

    ``p10_p90``
        NUS, NTU and SMU publish the 10th and 90th percentile of last year's
        admitted students -- the middle 80%, with the tails cut off by
        construction.

    ``min_max``
        The polytechnics publish the net ELR2B2 aggregate of the **lowest and
        highest ranked student admitted** through the Joint Admissions
        Exercise. That is the WHOLE admitted cohort, outliers included.

    A min-max range is necessarily wider than a p10-p90 drawn from the same
    intake. Storing a min-max here and saying nothing would render polytechnic
    courses as dramatically less selective than universities when the
    difference is the statistic, not the selectivity: NYP Nursing spans "3 to
    28", nearly the entire scale, because one admitted student sat at 28 --
    a percentile band would have excluded them by construction.

    So the words the UI is allowed to use are chosen from `statistic`, and
    `test_a_min_max_band_is_never_described_as_a_percentile_band` fails if a
    later change lets the percentile copy leak onto a full range.

    `scale` and `comparable` carry the same meaning they carry on
    `BandedProfile`, deliberately: comparability is a property of any published
    figure, not a quirk of one shape. An ELR2B2 aggregate is an O-Level
    statistic on a lower-is-better scale of 4 to 26, so it cannot be placed
    against an A-Level score out of 70 -- `comparable: False` routes it to
    PUBLISHED_ON_ANOTHER_BASIS, which already says the right thing.
    """

    p10: str            # e.g. "AAA/A" -- as published, verbatim shape
    p90: str
    p10_points: float   # comparable indicator computed by the pack compiler
    p90_points: float
    basis: str          # what the points mean, e.g. "3 H2 subjects, max 60"
    fact: Fact
    #: What the two endpoints MEAN. "p10_p90" | "min_max".
    statistic: str = "p10_p90"
    #: Machine tag for the unit, e.g. "" | "uas_70" | "elr2b2_olevel".
    scale: str = ""
    #: False when the published basis does not match the score PathAhead
    #: computes for this transition. The bands are still shown; the verdict is
    #: withheld.
    comparable: bool = True
    #: Earlier years of the SAME figure, most recent first. Never merged into
    #: the endpoints above. NYP publishes 2014-2026 and NP a dataset per year,
    #: so both can carry history; SP, TP and RP publish only the current
    #: exercise, so theirs is empty and the card says so rather than letting a
    #: one-year figure and a three-year figure render identically.
    history: tuple[BandYear, ...] = ()

    @property
    def years_covered(self) -> int:
        """How many separate published exercises this outcome can show."""
        return 1 + len(self.history)

    @property
    def years_label(self) -> str:
        """e.g. "2024, 2025 and 2026" -- the years, never a merged range."""
        years = [self.fact.as_of_year, *(h.year for h in self.history)]
        years = sorted(set(years))
        if len(years) == 1:
            return str(years[0])
        return ", ".join(str(y) for y in years[:-1]) + f" and {years[-1]}"


@dataclass(frozen=True, slots=True)
class ProfileBand:
    """One published score band, and how many applicants in it got through.

    `share` is None when the university deliberately censored the figure --
    SUSS prints "Below 5%" rather than a number in many cells. That is a
    published fact, not a missing one, so `share_label` keeps the words the
    university actually used and the UI shows those rather than inventing a
    midpoint.
    """

    label: str                  # verbatim, e.g. "UAS at least 60.00 (60.00 - 90.00)"
    share_label: str            # verbatim, e.g. "72.1%" or "Below 5%"
    low: float | None = None    # None where the band is open-ended
    high: float | None = None
    share: float | None = None  # None where the university censored the figure


@dataclass(frozen=True, slots=True)
class BandedProfile:
    """What share of applicants in each published band got through one stage.

    A DIFFERENT KIND of claim from a 10th-90th percentile GradeBand, and the
    two must never be silently converted into each other. A percentile band
    says "the middle 80% of people we admitted looked like this". A banded
    profile says "of the people who applied with this, N% got through". You
    cannot derive either from the other, and pretending otherwise would
    fabricate a precision three universities deliberately did not publish.

    Two fields carry the honesty:

    `stage` -- SUSS shortlists on grades and then decides on a three-stage
    assessment, so "shortlisted" and "offered" are different questions and a
    single share would lose the one that matters most.

    `comparable` -- False when the published basis no longer matches the score
    PathAhead computes. SUSS and SIT both publish against the retired 90-point
    UAS (3 H2 + H1 + GP + PW) while the AY2026 score is out of 70 (3 H2 + GP).
    A student's 60 is not their 60. When this is False the engine shows the
    published bands and refuses the comparison, rather than producing a verdict
    that would look ordinary and be wrong.
    """

    stage: str                  # "shortlisted" | "offered"
    basis: str                  # human-readable, e.g. "polytechnic GPA out of 4.00"
    scale: str                  # machine tag, e.g. "poly_gpa_4" | "uas_90_retired"
    bands: tuple[ProfileBand, ...]
    fact: Fact
    #: Which pool this describes. Diploma holders and A-Level holders are
    #: assessed separately by every university here, so their figures are
    #: separate facts and are never merged into one.
    qualification: str = "a-level"
    comparable: bool = True
    applies_to: str = "programme"   # "programme" | "cluster" -- SIT's A-Level
                                    # figures are aggregated across a cluster
                                    # and attaching them to one course would
                                    # be a misattribution.


@dataclass(frozen=True, slots=True)
class PolyGpa:
    """The 10th-90th percentile GPA of polytechnic diploma holders admitted.

    Carried because "polytechnic then a degree" is a route PathAhead insists on
    showing, and a route with no numbers attached is a platitude. Diploma-holder
    places are a distinct and competitive pool -- a different route, not an
    easier one.
    """

    p10: float
    p90: float
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Employment:
    """What actually happened to people who did this course.

    From the Graduate Employment Survey, run jointly by the six autonomous
    universities and published by MOE on data.gov.sg under the Singapore Open
    Data Licence. Surveyed roughly six months after final examinations.

    A *range*, never a bare median -- the same discipline the grade bands
    already follow, and for the same reason: the median alone invites being
    read as "what I will earn".
    """

    employment_rate: float | None          # % in employment overall
    employment_rate_ft_perm: float | None  # % in full-time permanent work
    gross_median: int | None               # gross monthly, SGD
    gross_p25: int | None
    gross_p75: int | None
    covers: str                            # which degree(s) this figure covers
    fact: Fact | None = None
    unavailable_reason: str | None = None  # e.g. professional training year

    @property
    def has_salary(self) -> bool:
        return self.gross_median is not None


@dataclass(frozen=True, slots=True)
class Cost:
    """What a family will actually pay, and what accepting help commits them to.

    The tuition grant bond is here rather than in a footnote because families
    routinely discover it late, and it is a multi-year commitment rather than
    a detail.
    """

    #: The tiers universities actually publish. All figures SGD per year.
    #: SC and PR figures exclude GST (MOE subsidises it); the international and
    #: non-subsidised figures include GST.
    annual_fee_citizen: int | None            # Singapore Citizen, with grant
    annual_fee_pr: int | None                 # Permanent Resident, with grant
    annual_fee_international: int | None      # International (ASEAN), with grant
    annual_fee_is_other: int | None = None    # International (non-ASEAN), with grant
    annual_fee_no_grant: int | None = None    # no tuition grant at all
    years: float | None = None
    tuition_grant_available: bool = True
    bond_note: str | None = None
    #: Years of service owed for accepting the grant. Citizens owe none for the
    #: grant itself; PRs and international students owe three. Medicine and
    #: Dentistry carry a separate, longer bond with the Ministry of Health.
    bond_years_citizen: int = 0
    bond_years_pr_is: int = 3
    fee_group: str | None = None              # the faculty band the fee is set by
    fact: Fact | None = None

    #: How the institution actually charges. "annual" | "per_credit".
    #:
    #: NUS, NTU and SMU publish a fee per academic year. SIT does not: it
    #: charges per credit unit, and states that fees "are payable as long as a
    #: student's candidature remains active", derived each trimester from the
    #: modules actually registered. Dividing a programme total by a nominal
    #: number of years would manufacture an annual figure SIT deliberately does
    #: not publish, and it would be wrong for any student who takes a lighter or
    #: heavier load -- which is the whole point of charging this way.
    #:
    #: So for a per-credit programme `annual_fee_*` stays empty and the TOTAL is
    #: the real number, computed the way the publisher computes it: credits
    #: times rate. Same principle as NTU's lab/non-lab split, which is also left
    #: empty rather than guessed.
    fee_basis: str = "annual"
    total_credits: int | None = None
    fee_per_credit_citizen: float | None = None
    fee_per_credit_pr: float | None = None
    fee_per_credit_international: float | None = None
    fee_per_credit_is_other: float | None = None
    fee_per_credit_no_grant: float | None = None

    def annual_for(self, citizenship: str) -> int | None:
        return {
            "citizen": self.annual_fee_citizen,
            "pr": self.annual_fee_pr,
            "international": self.annual_fee_international,
            "international_other": self.annual_fee_is_other,
            "no_grant": self.annual_fee_no_grant,
        }.get(citizenship)

    def per_credit_for(self, citizenship: str) -> float | None:
        return {
            "citizen": self.fee_per_credit_citizen,
            "pr": self.fee_per_credit_pr,
            "international": self.fee_per_credit_international,
            "international_other": self.fee_per_credit_is_other,
            "no_grant": self.fee_per_credit_no_grant,
        }.get(citizenship)

    def bond_for(self, citizenship: str) -> int:
        return self.bond_years_citizen if citizenship == "citizen" else self.bond_years_pr_is

    def total_for(self, citizenship: str) -> int | None:
        """The whole bill, computed the way the publisher computes it."""
        if self.fee_basis == "per_credit":
            rate = self.per_credit_for(citizenship)
            if rate is None or self.total_credits is None:
                return None
            return round(rate * self.total_credits)
        fee = self.annual_for(citizenship)
        if fee is None or self.years is None:
            return None
        return int(fee * self.years)

    @property
    def has_any_fee(self) -> bool:
        """Whether this course can show a family a cost at all.

        Health coverage counted `annual_fee_citizen` alone, which would have
        reported every SIT course as having no fee figure when in fact the full
        programme cost is known and published -- just not per year.
        """
        return bool(self.annual_fee_citizen or self.fee_per_credit_citizen)


@dataclass(frozen=True, slots=True)
class SubjectRequirement:
    """A subject the institution requires before it will consider you.

    THIS IS AN ELIGIBILITY FACT, NOT A PREFERENCE, and the distinction is the
    whole reason the type exists.

    A student with no H2 Physics was shown NTU's Physics / Applied Physics at
    52/100. The score was not too high -- a score at all was the error, because
    any number puts the course into a ranking and a low one ranks it above
    hundreds of others just the same. This is the identical failure to the
    Chinese-medium diploma that `LanguageRequirement` was built to stop; that
    lesson was fixed for one dimension and never generalised to subjects, which
    is the far more common case.

    The pack previously carried only a blanket overlay -- "programmes may
    require specific subjects, check the university's list" -- which turns our
    missing data into the reader's homework while still printing a score.

    Unlike a language, nothing extra has to be asked: the subjects are already
    collected in step two, so the engine can check the grade sheet directly.
    """

    #: Subject codes, any ONE of which satisfies the requirement. NTU asks for
    #: "Physics, Chemistry or Biology", which is one requirement with three
    #: acceptable answers, not three requirements.
    subjects: tuple[str, ...]
    #: Minimum level, e.g. "h2". Empty means any level counts.
    at_level: str = ""
    #: Verbatim from the institution, because a paraphrased entry condition is
    #: how a family ends up applying for something they cannot take.
    label: str = ""
    detail: str = ""
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Duration:
    """How long it takes, and whether you specialise straight away.

    Held separately from `Cost` because it is a fact about the COURSE, not
    about the money. It was previously only ever recorded inside a cost block,
    which meant 255 of 330 courses had no duration at all simply because
    nobody had loaded their fee — and duration is the number that multiplies a
    fee, so a family reading an annual figure had nothing to multiply it by.
    """

    years: float
    #: "common first year, specialise from year two", "2 or 2.5 via DAE".
    structure: str = ""
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Accreditation:
    """Recognition by a body that licenses practice.

    For some courses this is more consequential than any grade figure: an
    unaccredited nursing or optometry qualification may not let you register
    to practise at all. Where it applies it belongs beside the course, not
    three clicks into a professional body's website.
    """

    body: str                   # "Singapore Nursing Board"
    label: str                  # what holding this qualification permits
    detail: str = ""
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Progression:
    """Where this course can lead next.

    The polytechnic-to-degree route is a first-class destination in this pack,
    and a diploma's value to a family often turns on which degrees accept it
    and with how much exemption. Recorded per destination so it can be cited.
    """

    label: str                  # "BEng Mechanical Engineering, NTU"
    #: Advanced standing, module exemptions, shortened candidature.
    exemption: str = ""
    detail: str = ""
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Flexibility:
    """How reversible is this choice?

    The most useful thing you can tell a seventeen-year-old who does not yet
    know themselves. Advice that stays good even if they turn out to be wrong
    about what they want.
    """

    declares_major_later: bool
    common_first_year: bool
    switching_note: str | None
    keeps_open: tuple[str, ...] = ()
    forecloses: tuple[str, ...] = ()
    fact: Fact | None = None

    @property
    def score(self) -> int:
        """0-3, coarse on purpose. Used for the 'keeps doors open' filter."""
        return int(self.declares_major_later) + int(self.common_first_year) + (
            1 if self.keeps_open else 0
        )


@dataclass(frozen=True, slots=True)
class EditorialProfile:
    """PathAhead's own characterisation of what a course is like.

    NOT published by the institution. Always rendered as opinion, always
    carrying an invitation to disagree. This is what makes fit reasoning
    possible at all, and it is the part most likely to be wrong -- so it is
    labelled as loudly as the design allows.
    """

    interests: tuple[str, ...] = ()      # RIASEC codes: R I A S E C
    subject_affinity: tuple[str, ...] = ()   # subject slugs this builds on
    assessment_style: tuple[str, ...] = ()   # exams | coursework | practical
    work_setting: tuple[str, ...] = ()       # lab | studio | office | field ...
    teamwork: str | None = None              # individual | mixed | team
    maths_intensity: str | None = None       # low | medium | high
    writing_intensity: str | None = None
    sectors: tuple[str, ...] = ()            # where graduates tend to go
    summary: str | None = None
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Outcome:
    """A destination: a specific course at a specific institution."""

    id: str
    institution: str
    institution_short: str
    name: str
    faculty: str | None = None
    transition_id: str = ""
    band: GradeBand | None = None
    intake: Fact | None = None
    overlays: tuple[Overlay, ...] = ()
    url: str | None = None
    route_group: str = "university-direct"
    tags: tuple[str, ...] = ()
    employment: Employment | None = None
    cost: Cost | None = None
    flexibility: Flexibility | None = None
    editorial: EditorialProfile | None = None
    poly_gpa: PolyGpa | None = None
    #: Why there is no fee figure, where the absence is a DECISION rather than a
    #: to-do. A blank cost cell reads as "not loaded yet" and invites a later
    #: session to fill it in from the nearest plausible published number. Where
    #: the publisher's own naming makes the mapping ambiguous -- SIT lists Civil
    #: Engineering and Nursing twice, at different credit loads and rates -- the
    #: reason is recorded on the course so the gap defends itself.
    fee_note: str | None = None
    #: A language this course requires or is taught in. See LanguageRequirement.
    language_requirement: LanguageRequirement | None = None
    #: Subjects required for consideration. Eligibility, not preference:
    #: an unmet requirement produces NO score, never a low one.
    subject_requirements: tuple[SubjectRequirement, ...] = ()
    #: How long it runs, independent of whether a fee is loaded.
    duration: Duration | None = None
    #: Licensing bodies that recognise this qualification.
    accreditation: tuple[Accreditation, ...] = ()
    #: Where it leads next, with any advanced standing.
    progression: tuple[Progression, ...] = ()
    #: Zero or more banded profiles. A course has EITHER a percentile `band`
    #: or `banded` profiles, never both -- they are different published claims
    #: and holding both would invite blending them. SUSS carries two (one per
    #: stage); SUTD carries none at all and says so.
    banded: tuple[BandedProfile, ...] = ()
    #: Additional transitions this outcome may ALSO be assessed under, beyond
    #: its primary `transition_id`.
    #:
    #: Exists for exactly one situation so far: the five polytechnics publish
    #: an ELR2B2 min-max range that is a genuine O-Level statistic, loaded once
    #: under `a-level-to-university-2026` and shown to A-Level students with
    #: `band.comparable: False` -- correctly, since an A-Level score cannot be
    #: placed against it (SAFEGUARDS.md 4b3). An O-Level student's OWN ELR2B2
    #: score is a different question with a different answer: the same range
    #: is now the applicant's own basis, and declining the comparison would be
    #: withholding a real answer rather than avoiding a false one.
    #:
    #: Rather than duplicate 330 outcome records under a second transition_id,
    #: or let one Outcome belong to several transitions equally (which would
    #: make "the primary one" ambiguous everywhere else in the codebase that
    #: assumes exactly one), `also_scored_under` is a deliberately narrow
    #: escape hatch: the outcome's identity, editorial content and PRIMARY
    #: transition are unchanged, and only `outcomes_for()` and the
    #: comparability check in `forward.py` know it exists.
    also_scored_under: tuple[str, ...] = ()

    @property
    def comparable_banded(self) -> tuple[BandedProfile, ...]:
        """Only the profiles whose basis still matches how scores are computed."""
        return tuple(b for b in self.banded if b.comparable)

    @property
    def display(self) -> str:
        return f"{self.name} ({self.institution_short})"

    @property
    def has_extra_assessment(self) -> bool:
        return any(
            o.kind
            in {
                OverlayKind.INTERVIEW,
                OverlayKind.PORTFOLIO,
                OverlayKind.APTITUDE_TEST,
                OverlayKind.AUDITION,
            }
            for o in self.overlays
        )


@dataclass(frozen=True, slots=True)
class LanguageRequirement:
    """A language this course requires, or is actually taught in.

    This type exists because of a real failure. A student who does not read
    Chinese was shown NP's Diploma in Chinese Studies as her second-strongest
    match out of 296 courses. The fit score was 67/100 and every point of it
    came from generic signals -- "you work best through exams" -- because
    nothing in the pack recorded that Ngee Ann requires Higher Chinese grade
    1-4 or Chinese grade 1-3 to be *considered*, and states that at least half
    the course is conducted in Chinese.

    Two separate claims live here and both matter:

    `label`/`at_stage` -- the published ENTRY requirement. Note the stage: it is
    an O-Level requirement, and PathAhead's forward mode collects A-Level
    subjects, so the engine cannot verify it from the grades it holds. It has to
    ask, or decline to score.

    `taught_in_language` -- whether the teaching itself is in that language.
    This is the part a grade table would never tell you and the part that
    actually decides whether a course is livable. A student could in principle
    scrape the entry grade and still be unable to sit through the course.

    A course carrying one of these is never ranked as a match for a student who
    has not said they offer the language. Not hidden -- shown, with the
    requirement stated -- because PathAhead does not know what it has not been
    told, and a course removed silently is a course a family never gets to
    argue with.
    """

    language: str               # "chinese" | "malay" | "tamil"
    label: str                  # verbatim, e.g. "Higher Chinese 1-4, or Chinese 1-3"
    at_stage: str = "o-level"   # where the requirement is set
    taught_in_language: bool = False
    detail: str = ""
    fact: Fact | None = None


@dataclass(frozen=True, slots=True)
class Prerequisite:
    """A subject/qualification edge. Answers 'is this goal even reachable?'."""

    id: str
    applies_to: tuple[str, ...]   # outcome ids or tags
    requires_subject: str
    at_stage: str
    depends_on_earlier: str | None  # e.g. an O-Level subject choice
    detail: str
    fact: Fact


@dataclass(frozen=True, slots=True)
class Route:
    """One way to reach a destination. Never the only way.

    `backward.plan()` refuses to return fewer than MIN_ROUTES of these, because
    a single hard number delivered to a 15-year-old is a verdict, not advice.
    """

    id: str
    applies_to: tuple[str, ...]
    kind: Literal["direct", "alternative", "second-chance"]
    label: str
    summary: str
    steps: tuple[str, ...]
    typical_duration: str | None = None
    caveat: str | None = None
    source_id: str | None = None


# --------------------------------------------------------------------------
# Transition + pack
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Milestone:
    """A dated thing that happens, relative to the exam year.

    The question a family actually asks at the kitchen table is not "what is my
    score" but "what do we have to do, and by when". Missing a deadline is
    worse than missing a grade profile by two points, and unlike the grade
    profile it is entirely preventable.

    `month`/`day` are relative to `year_offset` from the exam year, so one
    declaration serves every cohort.
    """

    id: str
    label: str
    detail: str
    year_offset: int          # 0 = exam year, 1 = the year after
    month: int
    day: int
    kind: Literal["result", "application", "assessment", "decision", "appeal", "event", "service"]
    applies_to: tuple[str, ...] = ()      # stage ids, or () for all
    requires_service: bool = False        # only shown if NS applies
    approximate: bool = True              # dates move year to year
    url: str | None = None
    fact: Fact | None = None

    def date_for(self, exam_year: int) -> _dt.date:
        return _dt.date(exam_year + self.year_offset, self.month, self.day)


@dataclass(frozen=True, slots=True)
class Transition:
    id: str
    stage_id: str
    name: str
    applies_to_exam_years: tuple[int, ...]
    admission_years: tuple[int, ...]
    direction: Literal["higher_is_better", "lower_is_better"]
    rule_kind: str
    rule_params: Mapping[str, Any]
    scales: Mapping[str, Mapping[str, float]]
    fact: Fact
    comparison_basis: str = ""
    changed_from: Mapping[str, Any] | None = None
    policy_status: Literal["settled", "mid_rollout"] = "settled"
    caveats: tuple[str, ...] = ()


@dataclass(slots=True)
class Pack:
    """A country's education system, as data."""

    id: str
    country: str
    name: str
    version: str
    pack_format: int
    published: _dt.date
    description: str
    sources: dict[str, Source] = field(default_factory=dict)
    stages: dict[str, Stage] = field(default_factory=dict)
    transitions: dict[str, Transition] = field(default_factory=dict)
    outcomes: dict[str, Outcome] = field(default_factory=dict)
    cohort_rules: dict[str, CohortRule] = field(default_factory=dict)
    routes: list[Route] = field(default_factory=list)
    prerequisites: list[Prerequisite] = field(default_factory=list)
    attribution: list[str] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    subjects: list[dict[str, Any]] = field(default_factory=list)
    interests: list[dict[str, Any]] = field(default_factory=list)
    # Secondary-school directory rows (packs/singapore/secondary-schools.yaml)
    # and the postal-district table used to derive each school's `district`/
    # `region`. Loosely typed like subjects/interests above rather than given
    # their own dataclasses -- see engine/school_fit.py, which is the only
    # code that reads these and does its own validation of the shape it
    # needs.
    schools: list[dict[str, Any]] = field(default_factory=list)
    postal_districts: list[dict[str, Any]] = field(default_factory=list)

    #: True when engine/loader.py merged a local-only data overlay into this
    #: pack in memory -- currently only `packs/<id>/local/cutoff.json`.
    #:
    #: The published build is always False: PathAhead does not redistribute
    #: Posting Group cut-off points, and links to MOE SchoolFinder instead.
    #: A person may hold their own copy for private study, and when they do,
    #: this flag is what lets the UI say so plainly rather than presenting
    #: locally-sourced figures as though PathAhead published them. See
    #: engine/loader.py:_apply_local_overlays and docs/LOCAL_DATA.md.
    local_overlay_applied: bool = False

    #: Attribution + disclaimer for `school["cutoff_public_trend"]` (below),
    #: from packs/<id>/cutoff-trend-public.yaml if that file is present.
    #: Unlike local_overlay_applied above, this is TRACKED and PUBLISHED --
    #: not MOE's own per-school figure, which this project does not
    #: republish, but a citation of an already-public third-party
    #: compilation with its own attribution and disclaimer carried right
    #: through to the UI. See engine/loader.py:_apply_public_cutoff_trend
    #: and CHANGELOG.md for how this was sourced and spot-checked.
    cutoff_public_trend_source: dict[str, Any] | None = None

    # -- lookups ---------------------------------------------------------

    def source(self, source_id: str) -> Source:
        try:
            return self.sources[source_id]
        except KeyError as exc:
            raise KeyError(f"pack {self.id}: unknown source id {source_id!r}") from exc

    def outcomes_for(self, transition_id: str) -> list[Outcome]:
        return [
            o for o in self.outcomes.values()
            if o.transition_id == transition_id or transition_id in o.also_scored_under
        ]

    def routes_for(self, outcome: Outcome) -> list[Route]:
        keys = {outcome.id, outcome.route_group, *outcome.tags}
        return [r for r in self.routes if keys & set(r.applies_to)]

    def prerequisites_for(self, outcome: Outcome) -> list[Prerequisite]:
        keys = {outcome.id, outcome.route_group, *outcome.tags}
        return [p for p in self.prerequisites if keys & set(p.applies_to)]

    def all_facts(self) -> Iterable[tuple[str, Fact]]:
        """Every Fact in the pack, with a dotted path. Feeds the health gate."""
        for t in self.transitions.values():
            yield f"transition.{t.id}.rule", t.fact
        for o in self.outcomes.values():
            if o.band:
                yield f"outcome.{o.id}.band", o.band.fact
            if o.intake:
                yield f"outcome.{o.id}.intake", o.intake
            if o.poly_gpa and o.poly_gpa.fact:
                yield f"outcome.{o.id}.poly_gpa", o.poly_gpa.fact
            if o.employment and o.employment.fact:
                yield f"outcome.{o.id}.employment", o.employment.fact
            if o.cost and o.cost.fact:
                yield f"outcome.{o.id}.cost", o.cost.fact
            if o.flexibility and o.flexibility.fact:
                yield f"outcome.{o.id}.flexibility", o.flexibility.fact
            if o.editorial and o.editorial.fact:
                yield f"outcome.{o.id}.editorial", o.editorial.fact
        for p in self.prerequisites:
            yield f"prerequisite.{p.id}", p.fact
        for m in self.milestones:
            if m.fact:
                yield f"milestone.{m.id}", m.fact

    def official_facts(self) -> Iterable[tuple[str, Fact]]:
        """Only the claims that assert something published. The health gate's
        confidence floor applies to these; editorial characterisations are
        opinions and are counted separately rather than graded."""
        for path, fact in self.all_facts():
            if not fact.is_editorial:
                yield path, fact

    def fit_pool_coverage(self) -> dict[str, Any]:
        """How much of the real option space fit scoring can actually see.

        Ranking against an unrepresentative pool is not incomplete information
        -- it is misinformation with a progress bar. So the engine measures its
        own blind spot and the UI is forbidden from saying "best" until this
        is complete. See DESIGN_REVIEW_2.md 0.
        """
        institutions = {o.institution_short for o in self.outcomes.values()}
        scored = sum(1 for o in self.outcomes.values() if o.editorial)
        return {
            "institutions": sorted(institutions),
            "institution_count": len(institutions),
            "outcomes": len(self.outcomes),
            "outcomes_with_editorial": scored,
            "complete": False,  # flipped only when the pack declares full coverage
        }

    def year_levels(self) -> Sequence[CohortRule]:
        return sorted(self.cohort_rules.values(), key=lambda c: (c.stage_id, c.years_to_exam))

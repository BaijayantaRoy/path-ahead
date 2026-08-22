"""What the student tells us about themselves.

Every field is optional. Every field is skippable. Nothing here identifies a
person: there is no name, no school, no contact detail, and no field that could
hold one. A profile is held in memory for the length of a session and written
to disk only if the user explicitly saves one, locally.

The design rule that matters: **each question must earn its place.** A form
that takes twenty minutes gets abandoned at minute three by a family who are
already anxious. So the profile is built from a small number of high-signal
questions, each of which visibly changes the reasoning, and skipping any of
them costs confidence rather than breaking anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: RIASEC -- Holland's interest categories. Public domain, decades of use in
#: career guidance, and used here in its plain-language form rather than as a
#: psychometric instrument. PathAhead asks which activities pull at you; it
#: does not claim to have measured your personality.
INTERESTS: dict[str, tuple[str, str]] = {
    "R": ("Building and making", "hands-on work, machines, materials, the outdoors"),
    "I": ("Investigating and analysing", "figuring out why things work, evidence, experiments"),
    "A": ("Designing and creating", "visual work, writing, performing, original ideas"),
    "S": ("Helping and teaching", "working with people, care, guidance, community"),
    "E": ("Leading and persuading", "starting things, selling ideas, taking charge"),
    "C": ("Organising and systems", "structure, accuracy, data, making things run well"),
}

ASSESSMENT_STYLES = {
    "exams": "Exams — I do my best work under timed pressure",
    "coursework": "Projects and coursework — I do better with time to build something",
    "practical": "Hands-on and practical — I learn by doing rather than reading",
}

TEAMWORK = {
    "individual": "On my own",
    "mixed": "A mix",
    "team": "In a team",
}

PRIORITIES = {
    "earnings": "Financial security",
    "impact": "Doing something useful for people",
    "mastery": "Getting really good at one thing",
    "autonomy": "Freedom over how I work",
    "stability": "A steady, predictable path",
    "creativity": "Making things that did not exist before",
}

TRAJECTORY = {"improving": "Improving", "steady": "Holding steady", "slipping": "Slipping"}


@dataclass(slots=True)
class StudentProfile:
    """Everything optional. Nothing identifying.

    `answered()` drives the confidence figure shown next to every fit score:
    "based on 4 of the 8 things you told us". A profile that answers nothing
    produces no fit score at all, rather than a misleading 50%.
    """

    # --- goals -------------------------------------------------------
    goal_text: str = ""                       # free text, their own words
    target_outcome_id: str | None = None      # a named course, if they have one
    priorities: tuple[str, ...] = ()          # keys of PRIORITIES

    # --- interests ---------------------------------------------------
    interests: tuple[str, ...] = ()           # RIASEC keys, up to 3
    enjoyed_subjects: tuple[str, ...] = ()    # subject codes from their own entry

    #: Subjects the student is actually taking. NOT the same question as
    #: `enjoyed_subjects`, and conflating the two would break in the direction
    #: that costs the student: plenty of people take H2 Chemistry and do not
    #: enjoy it, and blocking them from every chemistry-gated course because
    #: they did not tick it as a favourite is exactly the kind of confident
    #: wrongness this project exists to avoid.
    #:
    #: None means "not told", which is different from () meaning "told, and it
    #: is none of these". Courses with a published subject requirement go
    #: unscored under None, the same way they do for an unanswered mother
    #: tongue -- because guessing eligibility is the one thing a fit score must
    #: never do.
    subjects_offered: tuple[str, ...] | None = None

    # --- how they work ----------------------------------------------
    assessment_style: str | None = None
    teamwork: str | None = None

    #: How much each dimension counts, as the student set it.
    #:
    #: THIS IS THE POINT OF THE WHOLE SCORER. The first version assigned
    #: interests 25 points and working style 10 -- numbers nobody could
    #: justify, which meant PathAhead was quietly asserting that what a student
    #: is drawn to matters two and a half times more than who they work with.
    #: That is a value judgement, and it belongs to the person deciding.
    #:
    #: A LEVEL per dimension rather than a strict order. Ordering seven things
    #: was tried and was the wrong shape twice over: it forces a sequence where
    #: people think in degrees, it forbids ties that are real ("these two
    #: matter the same"), and every interaction for reordering is bad -- drag
    #: fights page scroll on a phone and is unusable from a keyboard, while
    #: up/down needs six taps to move one row and makes you re-read the list
    #: after each one.
    #:
    #: Pairs of (dimension key, 0-3). 0 = does not matter and is dropped from
    #: BOTH sides of the fraction. Empty = nothing set, so everything counts
    #: equally, which is a stated default rather than a hidden prior.
    importance: tuple[tuple[str, int], ...] = ()

    # --- languages offered -------------------------------------------
    #: Mother-tongue languages the student offered at O-Level, e.g. ("chinese",).
    #:
    #: NOT a fit signal, and deliberately not in SIGNALS below. This is an
    #: eligibility fact, not a preference: a handful of courses require a
    #: language at O-Level and are taught in it, and answering this cannot
    #: raise or lower any score. It exists only so PathAhead stops ranking a
    #: course conducted in Chinese as a strong match for a student who does not
    #: read Chinese.
    #:
    #: `None` means the question has not been answered, which is different from
    #: the empty tuple meaning "none of them". The engine treats those two
    #: differently and says which it is.
    languages_offered: tuple[str, ...] | None = None

    # --- constraints -------------------------------------------------
    citizenship: str = "citizen"              # citizen | pr | international
    national_service: bool = False
    open_to_longer_route: bool | None = None  # poly -> degree, etc.
    cost_sensitive: bool | None = None
    willing_extra_assessment: bool | None = None

    # --- trajectory --------------------------------------------------
    subject_trajectory: dict[str, str] = field(default_factory=dict)

    #: The questions that count toward fit confidence, in asking order.
    SIGNALS = (
        "interests",
        "enjoyed_subjects",
        "subjects_offered",
        "assessment_style",
        "teamwork",
        "priorities",
        "goal_text",
        "willing_extra_assessment",
        "cost_sensitive",
    )

    def answered(self) -> list[str]:
        out = []
        for name in self.SIGNALS:
            value = getattr(self, name)
            if value not in (None, "", (), [], {}):
                out.append(name)
        return out

    @property
    def signal_count(self) -> int:
        return len(self.answered())

    @property
    def is_empty(self) -> bool:
        return self.signal_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_text": self.goal_text,
            "target_outcome_id": self.target_outcome_id,
            "priorities": list(self.priorities),
            "interests": list(self.interests),
            "enjoyed_subjects": list(self.enjoyed_subjects),
            "subjects_offered": (None if self.subjects_offered is None else list(self.subjects_offered)),
            "assessment_style": self.assessment_style,
            "teamwork": self.teamwork,
            "citizenship": self.citizenship,
            "national_service": self.national_service,
            "open_to_longer_route": self.open_to_longer_route,
            "cost_sensitive": self.cost_sensitive,
            "willing_extra_assessment": self.willing_extra_assessment,
            "subject_trajectory": dict(self.subject_trajectory),
            "signals_answered": self.answered(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StudentProfile:
        return cls(
            goal_text=str(d.get("goal_text", "")),
            target_outcome_id=d.get("target_outcome_id"),
            priorities=tuple(d.get("priorities", ())),
            interests=tuple(d.get("interests", ())),
            enjoyed_subjects=tuple(d.get("enjoyed_subjects", ())),
            subjects_offered=(None if d.get("subjects_offered") is None else tuple(d["subjects_offered"])),
            assessment_style=d.get("assessment_style"),
            teamwork=d.get("teamwork"),
            citizenship=str(d.get("citizenship", "citizen")),
            national_service=bool(d.get("national_service", False)),
            open_to_longer_route=d.get("open_to_longer_route"),
            cost_sensitive=d.get("cost_sensitive"),
            willing_extra_assessment=d.get("willing_extra_assessment"),
            subject_trajectory=dict(d.get("subject_trajectory", {})),
        )


def reflect_goal(profile: StudentProfile, outcomes: list) -> list[str]:
    """Read the student's own words back at the moment of decision.

    Tier 0 has no language model, and pretending to understand free text with
    keyword matching would produce confident nonsense. What it CAN do -- and
    what is genuinely useful -- is put their own sentence back in front of them
    beside the shortlist, so they check it themselves.

    Semantic matching waits for Tier 1. The UI must not imply otherwise.
    """
    if not profile.goal_text.strip():
        return []
    return [
        f"You wrote: “{profile.goal_text.strip()}”",
        "PathAhead has not tried to interpret that — it has no language model "
        "running, and guessing would be worse than useless. Read it back "
        "against the list below and see whether it still fits.",
    ]

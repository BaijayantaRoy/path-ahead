"""What a student actually enters, and how it is validated.

Deliberately tolerant on input (people type "h2 chem A", "A", "a") and strict
on meaning: an unrecognised grade is an error with advice, never a silent zero.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import InputError

#: Subject levels PathAhead understands. `gp` and `mtl` are separated from
#: plain `h1` because the scoring rules treat them differently.
LEVELS = ("h1", "h2", "h3", "gp", "mtl", "pw", "subject")

#: A-Level grades, best to worst. `U` scores zero everywhere.
A_LEVEL_GRADES = ("A", "B", "C", "D", "E", "S", "U")

#: PSLE Achievement Levels, best to worst.
PSLE_ALS = tuple(str(i) for i in range(1, 9))

#: O-Level/SEC results are published as these letter-number pairs; the number
#: alone is what the aggregate formulas add up (a "B3" is worth 3, an "F9" is
#: worth 9). Accepting this spelling as input is a convenience -- a parent
#: reads it off the results slip -- and the canonical stored form is always
#: the bare digit on the right, so a bare "3" typed directly means the same
#: thing as "B3". See `_normalise_grade` for the round trip.
_OLEVEL_LETTER_GRADES = {
    "A1": "1", "A2": "2", "B3": "3", "B4": "4",
    "C5": "5", "C6": "6", "D7": "7", "E8": "8", "F9": "9",
}

_SUBJECT_RE = re.compile(
    r"^\s*(?:(?P<level>h1|h2|h3|gp|mtl|pw)\s*[:\s]\s*)?(?P<name>[A-Za-z0-9&,()/.\- ]+?)\s*[=:]\s*(?P<grade>[A-Za-z0-9]+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SubjectGrade:
    code: str
    name: str
    level: str
    grade: str

    @property
    def display(self) -> str:
        prefix = {"h1": "H1", "h2": "H2", "h3": "H3", "gp": "", "mtl": "", "pw": ""}.get(
            self.level, ""
        )
        return f"{prefix} {self.name}".strip()


@dataclass(frozen=True, slots=True)
class GradeSheet:
    """One student's results for one exam. Never carries a name or an id."""

    stage_id: str
    subjects: tuple[SubjectGrade, ...]

    def at_level(self, *levels: str) -> list[SubjectGrade]:
        wanted = {lv.lower() for lv in levels}
        return [s for s in self.subjects if s.level in wanted]

    def first_at_level(self, level: str) -> SubjectGrade | None:
        found = self.at_level(level)
        return found[0] if found else None

    def by_code(self, code: str) -> SubjectGrade | None:
        for s in self.subjects:
            if s.code == code:
                return s
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage_id,
            "subjects": [
                {"code": s.code, "name": s.name, "level": s.level, "grade": s.grade}
                for s in self.subjects
            ],
        }

    # -- construction ----------------------------------------------------

    @classmethod
    def from_dicts(cls, stage_id: str, rows: Iterable[Mapping[str, Any]]) -> GradeSheet:
        subjects = []
        for i, row in enumerate(rows):
            level = str(row.get("level", "subject")).lower()
            if level not in LEVELS:
                raise InputError(
                    f"unknown subject level {level!r}",
                    advice=f"Subject levels must be one of: {', '.join(LEVELS)}.",
                )
            name = str(row.get("name") or row.get("code") or f"Subject {i + 1}").strip()
            code = str(row.get("code") or _slug(f"{level}-{name}"))
            grade = _normalise_grade(str(row["grade"]), stage_id)
            subjects.append(SubjectGrade(code=code, name=name, level=level, grade=grade))
        if not subjects:
            raise InputError(
                "no subjects given",
                advice="Enter at least one subject and grade before asking for a result.",
            )
        return cls(stage_id=stage_id, subjects=tuple(subjects))

    @classmethod
    def parse(cls, stage_id: str, entries: Sequence[str]) -> GradeSheet:
        """Parse CLI-style entries such as 'h2 Chemistry=A' or 'gp GP=B'."""
        rows: list[dict[str, Any]] = []
        for entry in entries:
            m = _SUBJECT_RE.match(entry)
            if not m:
                raise InputError(
                    f"could not read {entry!r}",
                    advice=(
                        "Write each subject as LEVEL Name=Grade, for example: "
                        '"h2 Chemistry=A"  "gp General Paper=B"  "mtl Chinese=C".'
                    ),
                )
            rows.append(
                {
                    "level": (m.group("level") or "subject").lower(),
                    "name": m.group("name").strip(),
                    "grade": m.group("grade"),
                }
            )
        return cls.from_dicts(stage_id, rows)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalise_grade(raw: str, stage_id: str) -> str:
    g = raw.strip().upper()
    if stage_id == "psle":
        if g.startswith("AL"):
            g = g[2:]
        if g in PSLE_ALS:
            return g
        if g in {"A", "B", "C"}:  # Foundation-level subjects are graded A-C
            return f"F{g}"
        # Normalising must be idempotent. "FA" is this function's OWN output,
        # and it comes back in through every round trip: GradeSheet.to_dict()
        # writes the normalised grade, so a saved profile, a golden fixture or
        # a bundle replayed through from_dicts() re-enters here already
        # normalised. Rejecting our own spelling made the golden fixtures fail
        # to reproduce -- which is what caught this.
        if g in {"FA", "FB", "FC"}:
            return g
        raise InputError(
            f"{raw!r} is not a PSLE Achievement Level",
            advice="PSLE subjects are AL1 to AL8 (or A, B, C for Foundation-level subjects).",
        )
    if g in A_LEVEL_GRADES:
        return g
    if g in _OLEVEL_LETTER_GRADES:
        # A parent types what the results slip says -- "A1", "B3", "F9" -- and
        # the canonical form stored here is the bare digit, same shape as the
        # numeric input below. required_plus_best_n's `_ol()` (and the JS
        # `olLabel()`) turn the digit back into this exact spelling for
        # display, the same round trip lowest_sum already does for PSLE's
        # AL-prefix. Never store "A1" itself: two different digits can share
        # a letter ("A1" and "A2" are both "A"), so keeping the letter would
        # throw away the number that the aggregate actually adds up.
        return _OLEVEL_LETTER_GRADES[g]
    if g.isdigit():
        # O-Level and SEC subject grades are numeric (1-9). Validation against
        # the actual scale happens in grade_points(), which knows what the pack
        # declares -- this function only normalises shape.
        return g
    if g in {"PASS", "P"}:
        return "PASS"
    if g in {"FAIL", "F"}:
        return "FAIL"
    raise InputError(
        f"{raw!r} is not a grade this exam uses",
        advice=(
            f"Grades for this exam are {', '.join(A_LEVEL_GRADES)} "
            "(or a subject grade from 1 to 9 at O-Level/SEC)."
        ),
    )


def grade_points(scales: Mapping[str, Mapping[str, float]], scale_name: str, grade: str) -> float:
    """Look up a grade on a named scale declared by the pack.

    The scale lives in the pack, not in this file. That is the whole point:
    when a scoring system changes, a data file changes, not this function.
    """
    try:
        scale = scales[scale_name]
    except KeyError as exc:
        raise InputError(
            f"the pack does not define a grade scale called {scale_name!r}",
            advice="This is a data pack problem, not something you did. Please report it.",
        ) from exc
    if grade not in scale:
        raise InputError(
            f"grade {grade!r} is not on the {scale_name!r} scale",
            advice=f"Valid grades on this scale: {', '.join(scale.keys())}.",
        )
    return float(scale[grade])

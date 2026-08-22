"""The timeline — "what do we have to do, and by when?"

The question a family actually asks at the kitchen table is rarely "what is my
score". It is what closes first. Missing an application window is worse than
missing a grade profile by two points, and unlike the grade profile it is
entirely preventable.

Two things this module handles that nothing else in the tool does:

  * **National Service.** For roughly half of every cohort the timeline is not
    exam → apply → start. It is exam → apply → defer → serve about two years →
    start. Boys and girls in the same class are on different clocks, and a
    salary figure read at eighteen is not the one they graduate into.

  * **Honest approximation.** These dates move every year. Every milestone is
    marked approximate and linked to the official page. The app tells you what
    is coming and then tells you to check it — which is the correct division of
    labour between a tool and an institution.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any

from .model import CohortResolution, Pack

#: Full-time National Service, in years. Used only to shift the timeline.
NS_YEARS = 2


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    milestone_id: str
    label: str
    detail: str
    date: _dt.date
    kind: str
    approximate: bool
    url: str | None
    days_away: int
    passed: bool

    @property
    def when(self) -> str:
        if self.passed:
            return "already passed"
        if self.days_away == 0:
            return "today"
        if self.days_away == 1:
            return "tomorrow"
        if self.days_away < 31:
            return f"in {self.days_away} days"
        months = round(self.days_away / 30.4)
        if months < 24:
            return f"in about {months} month{'s' if months != 1 else ''}"
        return f"in about {round(self.days_away / 365.25)} years"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.milestone_id,
            "label": self.label,
            "detail": self.detail,
            "date": self.date.isoformat(),
            "kind": self.kind,
            "approximate": self.approximate,
            "url": self.url,
            "days_away": self.days_away,
            "passed": self.passed,
            "when": self.when,
        }


@dataclass(slots=True)
class Timeline:
    entries: list[TimelineEntry]
    notes: list[str]
    starts_year: int | None          # when study actually begins
    service_applied: bool

    @property
    def next_up(self) -> TimelineEntry | None:
        upcoming = [e for e in self.entries if not e.passed]
        return upcoming[0] if upcoming else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "notes": list(self.notes),
            "starts_year": self.starts_year,
            "service_applied": self.service_applied,
            "next": self.next_up.to_dict() if self.next_up else None,
        }

    def as_text(self) -> str:
        lines = ["What happens next"]
        for e in self.entries:
            mark = "  " if e.passed else "> "
            approx = " (approximate — check the official page)" if e.approximate else ""
            lines.append(f"{mark}{e.date.isoformat()}  {e.when:<22}{e.label}{approx}")
            if e.detail:
                lines.append(f"       {e.detail}")
        for n in self.notes:
            lines += ["", f"  {n}"]
        return "\n".join(lines)

    def as_ics(self, calendar_name: str = "PathAhead") -> str:
        """An .ics file, because a timeline that stays in a browser tab is not
        much use to a family whose problem is remembering."""
        out = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//PathAhead//EN",
            f"X-WR-CALNAME:{calendar_name}",
        ]
        for e in self.entries:
            if e.passed:
                continue
            stamp = e.date.strftime("%Y%m%d")
            out += [
                "BEGIN:VEVENT",
                f"UID:{e.milestone_id}-{stamp}@pathahead.local",
                f"DTSTART;VALUE=DATE:{stamp}",
                f"SUMMARY:{e.label}" + (" (approximate)" if e.approximate else ""),
                f"DESCRIPTION:{e.detail} Check the official page before relying on this date.",
                "END:VEVENT",
            ]
        out.append("END:VCALENDAR")
        return "\r\n".join(out)


def build(
    pack: Pack,
    cohort: CohortResolution,
    *,
    national_service: bool = False,
    today: _dt.date | None = None,
) -> Timeline:
    today = today or _dt.date.today()
    entries: list[TimelineEntry] = []

    for m in pack.milestones:
        if m.applies_to and cohort.stage_id not in m.applies_to:
            continue
        if m.requires_service and not national_service:
            continue
        date = m.date_for(cohort.exam_year)
        delta = (date - today).days
        entries.append(
            TimelineEntry(
                milestone_id=m.id,
                label=m.label,
                detail=m.detail,
                date=date,
                kind=m.kind,
                approximate=m.approximate,
                url=m.url,
                days_away=max(delta, 0),
                passed=delta < 0,
            )
        )

    entries.sort(key=lambda e: e.date)

    notes: list[str] = [
        "These dates move from year to year. PathAhead shows you what is coming; "
        "the official page is what you should rely on."
    ]
    starts = cohort.admission_year
    if national_service:
        starts = cohort.admission_year + NS_YEARS
        notes.append(
            f"You have told PathAhead that National Service applies. You would normally "
            f"apply and accept a place in {cohort.admission_year} and then defer, "
            f"starting your course around {starts}. That is a published, ordinary route "
            f"— not a setback — and universities run a distinct admissions path for "
            f"returning servicemen."
        )
        notes.append(
            "It also means the salary and employment figures you read now describe "
            "people who graduated years before you will. Read them as a shape, not a "
            "promise."
        )

    return Timeline(
        entries=entries, notes=notes, starts_year=starts, service_applied=national_service
    )

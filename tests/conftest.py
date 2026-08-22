from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine import GradeSheet, load_pack  # noqa: E402

#: Frozen "today" so staleness tests do not rot with the wall clock.
TODAY = _dt.date(2026, 8, 2)


@pytest.fixture(scope="session")
def pack():
    return load_pack(REPO / "packs" / "singapore")


@pytest.fixture
def today():
    return TODAY


@pytest.fixture
def strong_grades():
    return GradeSheet.parse(
        "a-level",
        [
            "h2 Chemistry=A",
            "h2 Biology=A",
            "h2 Mathematics=B",
            "gp General Paper=A",
            "h1 Economics=C",
            "mtl Chinese=B",
        ],
    )


@pytest.fixture
def modest_grades():
    return GradeSheet.parse(
        "a-level",
        [
            "h2 Mathematics=C",
            "h2 Physics=D",
            "h2 Chemistry=D",
            "gp General Paper=C",
        ],
    )

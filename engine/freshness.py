"""How old is this data, and does a newer pack exist?

Two rules, both non-negotiable:

  * Data age is ALWAYS visible. Not on an About page -- on the screen showing
    the numbers.
  * The update check reveals nothing about the user. A plain unauthenticated
    GET with no query parameters and no identifiers, and a silent, harmless
    failure when offline. Offline is a fully supported state, not a degraded
    one.
"""

from __future__ import annotations

import datetime as _dt
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .model import Pack

USER_AGENT = "PathAhead/0.1 (+https://github.com/BaijayantaRoy/path-ahead)"
DEFAULT_TIMEOUT = 4.0


@dataclass(frozen=True, slots=True)
class Freshness:
    pack_id: str
    version: str
    published: _dt.date
    age_days: int
    stale_facts: int
    total_facts: int

    @property
    def banner(self) -> str:
        age = (
            "today"
            if self.age_days == 0
            else ("yesterday" if self.age_days == 1 else f"{self.age_days} days ago")
        )
        base = f"Data as of {self.published.isoformat()} - updated {age}"
        if self.stale_facts:
            return (
                f"{base}. {self.stale_facts} of {self.total_facts} figures are past "
                "their publication cycle and are shown greyed out."
            )
        return base

    @property
    def level(self) -> str:
        if self.stale_facts:
            return "warn"
        if self.age_days > 365:
            return "warn"
        if self.age_days > 120:
            return "info"
        return "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "published": self.published.isoformat(),
            "age_days": self.age_days,
            "stale_facts": self.stale_facts,
            "total_facts": self.total_facts,
            "banner": self.banner,
            "level": self.level,
        }


def describe(pack: Pack, today: _dt.date | None = None) -> Freshness:
    today = today or _dt.date.today()
    facts = list(pack.all_facts())
    return Freshness(
        pack_id=pack.id,
        version=pack.version,
        published=pack.published,
        age_days=(today - pack.published).days,
        stale_facts=sum(1 for _, f in facts if f.is_stale(today)),
        total_facts=len(facts),
    )


@dataclass(frozen=True, slots=True)
class UpdateCheck:
    available: bool
    latest: str | None = None
    url: str | None = None
    error: str | None = None

    def message(self, current: str) -> str:
        if self.error:
            return "Could not check for a data update. PathAhead works offline; nothing is missing."
        if self.available:
            return f"A newer data pack is available: {self.latest} (you have {current})."
        return f"Your data pack ({current}) is the latest available."


def check_for_update(
    releases_url: str,
    current_version: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> UpdateCheck:
    """Ask a public releases feed whether a newer pack exists.

    Sends: a GET, a User-Agent, nothing else. No query string, no identifiers,
    no body, no cookies. Receives: JSON. Fails silently and safely.
    """
    request = urllib.request.Request(
        releases_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return UpdateCheck(available=False, error=str(exc))

    latest = _latest_tag(payload)
    if latest is None:
        return UpdateCheck(available=False, error="release feed had no recognisable version")
    return UpdateCheck(
        available=_is_newer(latest, current_version),
        latest=latest,
        url=_html_url(payload),
    )


def _latest_tag(payload: Any) -> str | None:
    if isinstance(payload, dict):
        return payload.get("tag_name") or payload.get("version")
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return first.get("tag_name") or first.get("version")
    return None


def _html_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        return payload.get("html_url")
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0].get("html_url")
    return None


def _is_newer(candidate: str, current: str) -> bool:
    def parts(v: str) -> tuple[int, ...]:
        cleaned = "".join(c if c.isdigit() or c == "." else "." for c in v)
        return tuple(int(p) for p in cleaned.split(".") if p.isdigit())

    a, b = parts(candidate), parts(current)
    if not a or not b:
        return candidate != current
    return a > b

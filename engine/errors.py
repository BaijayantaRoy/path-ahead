"""Exception hierarchy for PathAhead.

Every error a user can plausibly cause carries a plain-English `advice` string.
The CLI and web layers show `advice`, never a traceback: a parent who typed a
grade wrong should be told what to fix, not shown a stack.
"""

from __future__ import annotations


class PathAheadError(Exception):
    """Base for everything raised by the engine."""

    def __init__(self, message: str, advice: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.advice = advice or "Please check your input and try again."

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class PackError(PathAheadError):
    """The data pack is malformed, unreadable, or internally inconsistent."""


class PackFormatError(PackError):
    """The pack was written for a different engine format version."""


class PackIntegrityError(PackError):
    """The pack failed checksum or signature verification."""


class RuleError(PathAheadError):
    """A scoring rule could not be evaluated."""


class UnknownRuleKind(RuleError):
    """The pack asked for a rule kind this engine version does not implement."""


class InputError(PathAheadError):
    """The user's grades or cohort could not be interpreted."""


class DataIncomplete(PathAheadError):
    """The pack does not carry enough verified data to answer honestly.

    This is deliberately an error and not a silent fallback. PathAhead would
    rather say "we don't have this yet" than show a plausible-looking number
    that nobody has checked.
    """

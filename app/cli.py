"""PathAhead command line.

    pathahead levels                        which year levels this pack knows
    pathahead courses                       what destinations are loaded
    pathahead score   --year-level jc-2 ... your worked-out score
    pathahead explore --year-level jc-2 ... your score plus your options
    pathahead plan    nus-medicine ...      what it takes, and what else works
    pathahead whatif  --change maths=A ...  recompute with a grade changed
    pathahead health  [--gate] [--markdown] the data health report
    pathahead build   [--out dist]          compile the pack for release
    pathahead serve   [--port 8902]         run the local app

Errors are shown as a sentence plus advice, never a traceback. Someone using
this at 11pm the night before an application deadline should be told what to
fix, not shown a stack.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # allows `python app/cli.py` without installing
    sys.path.insert(0, str(REPO))

from engine import (  # noqa: E402
    NOT_ADVICE,
    NOT_OFFICIAL,
    GradeSheet,
    PathAheadError,
    __version__,
    check_pack,
    describe_freshness,
    explain_options,
    explain_plan,
    explain_score,
    explain_what_if,
    explore,
    load_pack,
    plan,
    what_if,
)

DEFAULT_PACK = REPO / "packs" / "singapore"

_ANSI = {"dim": "\033[2m", "bold": "\033[1m", "off": "\033[0m"}


def _supports_colour() -> bool:
    return (sys.stdout.isatty() and sys.platform != "win32") or bool(
        sys.stdout.isatty() and __import__("os").environ.get("WT_SESSION")
    )


def _c(text: str, style: str) -> str:
    return f"{_ANSI[style]}{text}{_ANSI['off']}" if _supports_colour() else text


def _rule(title: str = "") -> str:
    return _c("-" * 72 + (f" {title}" if title else ""), "dim")


# --------------------------------------------------------------------------


def _add_grade_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pack", default=str(DEFAULT_PACK), help="pack directory or compiled .json")
    p.add_argument("--year-level", required=True, help="e.g. jc-2 (see: pathahead levels)")
    p.add_argument("--year", type=int, default=_dt.date.today().year, help="the current calendar year")
    p.add_argument(
        "grades",
        nargs="+",
        metavar="SUBJECT=GRADE",
        help='e.g. "h2 Chemistry=A" "h2 Biology=A" "h2 Maths=B" "gp General Paper=A"',
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pathahead",
        description="Understand how education pathways actually work. Free, open, and offline.",
        epilog=NOT_OFFICIAL,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"PathAhead {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("levels", help="list the year levels this pack understands")
    q.add_argument("--pack", default=str(DEFAULT_PACK))

    q = sub.add_parser("courses", help="list the destinations this pack has loaded")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--search", default="", help="filter by name")

    q = sub.add_parser("score", help="work out your score, with every step shown")
    _add_grade_args(q)
    q.add_argument("--brief", action="store_true", help="just the number")
    q.add_argument("--json", action="store_true", help="machine-readable output")

    q = sub.add_parser("explore", help="your score plus the destinations it reaches")
    _add_grade_args(q)
    q.add_argument("--json", action="store_true")

    q = sub.add_parser("plan", help="work backwards from a destination")
    q.add_argument("outcome", help="course id (see: pathahead courses)")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--year-level", default=None)
    q.add_argument("--year", type=int, default=_dt.date.today().year)
    q.add_argument("grades", nargs="*", metavar="SUBJECT=GRADE")
    q.add_argument("--json", action="store_true")

    q = sub.add_parser("whatif", help="recompute with one or more grades changed")
    _add_grade_args(q)
    q.add_argument(
        "--change",
        action="append",
        required=True,
        metavar="CODE=GRADE",
        help="e.g. --change h2-mathematics=A (codes are shown by `score`)",
    )

    q = sub.add_parser("timeline", help="what happens next, and when")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--year-level", required=True)
    q.add_argument("--year", type=int, default=_dt.date.today().year)
    q.add_argument("--ns", action="store_true", help="National Service applies")
    q.add_argument("--ics", metavar="FILE", help="also write a calendar file")

    q = sub.add_parser("fit", help="how well courses match what you tell it about yourself")
    _add_grade_args(q)
    q.add_argument("--interest", action="append", default=[], metavar="CODE",
                   help="R I A S E C — repeatable, up to 3")
    q.add_argument("--enjoy", action="append", default=[], metavar="SUBJECT",
                   help="a subject code you actually enjoy — repeatable")
    q.add_argument("--style", choices=["exams", "coursework", "practical"])
    q.add_argument("--teamwork", choices=["individual", "mixed", "team"])
    q.add_argument("--priority", action="append", default=[], metavar="KEY",
                   help="earnings impact mastery autonomy stability creativity")
    q.add_argument("--no-extra-assessment", action="store_true",
                   help="you would rather not sit interviews or build a portfolio")
    q.add_argument("--cost-matters", action="store_true")
    q.add_argument("--goal", default="", help="in your own words")
    q.add_argument("--top", type=int, default=6)

    q = sub.add_parser("health", help="data health report for a pack")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--gate", action="store_true", help="exit 1 if the pack is not shippable")
    q.add_argument("--markdown", action="store_true")
    q.add_argument("--json", action="store_true")
    q.add_argument("--min-confidence", default="medium", choices=["low", "medium", "high"])

    q = sub.add_parser("build", help="compile a pack to a signed-ready JSON bundle")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--out", default=str(REPO / "dist"))

    q = sub.add_parser("serve", help="run the local app in your browser")
    q.add_argument("--pack", default=str(DEFAULT_PACK))
    q.add_argument("--port", type=int, default=8902)
    q.add_argument("--no-browser", action="store_true")
    return p


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def cmd_levels(args) -> int:
    pack = load_pack(args.pack)
    print(f"{pack.name} ({pack.version})\n")
    print(f"  {'year level':<12}{'what it means':<34}{'exam':<8}{'admission'}")
    year = _dt.date.today().year
    for cr in pack.year_levels():
        print(
            f"  {cr.year_level:<12}{cr.label:<34}"
            f"{year + cr.years_to_exam:<8}{year + cr.years_to_exam + cr.admission_offset}"
        )
    print(f"\n{_c('Stages not yet loaded in this pack are listed in ROADMAP.md.', 'dim')}")
    return 0


def cmd_courses(args) -> int:
    pack = load_pack(args.pack)
    needle = args.search.lower()
    rows = [
        o
        for o in sorted(pack.outcomes.values(), key=lambda o: (o.institution_short, o.name))
        if needle in o.name.lower() or needle in o.institution_short.lower()
    ]
    print(f"{len(rows)} destination(s) in {pack.id} {pack.version}\n")
    for o in rows:
        band = f"{o.band.p10}-{o.band.p90} ({o.band.fact.as_of_year})" if o.band else "no band loaded"
        flag = " *" if o.has_extra_assessment else "  "
        print(f"  {o.id:<32}{o.institution_short:<6}{o.name[:38]:<40}{band}{flag}")
    print(f"\n  {_c('* also requires an interview, test or portfolio', 'dim')}")
    return 0


def _grades_from(args) -> GradeSheet:
    return GradeSheet.parse("a-level", args.grades)


def cmd_score(args) -> int:
    pack = load_pack(args.pack)
    result = explore(
        pack, year_level=args.year_level, current_year=args.year, grades=_grades_from(args)
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print(_rule())
    print(explain_score(result, detail=not args.brief))
    print(_rule())
    print(_c(describe_freshness(pack).banner, "dim"))
    return 0


def cmd_explore(args) -> int:
    pack = load_pack(args.pack)
    result = explore(
        pack, year_level=args.year_level, current_year=args.year, grades=_grades_from(args)
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print(_rule())
    print(explain_score(result))
    print()
    print(_rule("your options"))
    print(explain_options(result, pack))
    print()
    print(_rule())
    print(NOT_ADVICE)
    print(_c(describe_freshness(pack).banner, "dim"))
    return 0


def cmd_plan(args) -> int:
    pack = load_pack(args.pack)
    comparison = None
    if args.grades and args.year_level:
        result = explore(
            pack, year_level=args.year_level, current_year=args.year, grades=_grades_from(args)
        )
        comparison = result.comparison_score
    p = plan(pack, args.outcome, comparison_score=comparison)
    if args.json:
        print(json.dumps(p.to_dict(), indent=2))
        return 0
    print(_rule())
    print(explain_plan(p))
    print(_rule())
    return 0


def cmd_whatif(args) -> int:
    pack = load_pack(args.pack)
    grades = _grades_from(args)
    result = explore(pack, year_level=args.year_level, current_year=args.year, grades=grades)
    changes = {}
    for c in args.change:
        code, _, grade = c.partition("=")
        changes[code.strip()] = grade.strip()
    before, after = what_if(pack, grades, result.transition, changes)
    print(_rule())
    print(explain_what_if(before, after, result.transition.name))
    print(_rule())
    return 0


def cmd_timeline(args) -> int:
    from engine import milestones as _ms
    from engine.cohort import resolve as _resolve

    pack = load_pack(args.pack)
    cohort = _resolve(pack, args.year_level, args.year)
    tl = _ms.build(pack, cohort, national_service=args.ns)
    print(_rule())
    print(cohort.sentence())
    print()
    print(tl.as_text())
    if tl.service_applied:
        print()
        print(f"  You would expect to start studying around {tl.starts_year}.")
    print(_rule())
    if args.ics:
        Path(args.ics).write_text(tl.as_ics(), encoding="utf-8")
        print(f"  calendar written to {args.ics}")
    return 0


def cmd_fit(args) -> int:
    from engine.fit import coverage as _cov
    from engine.fit import explain_fit, score_all
    from engine.profile import StudentProfile

    pack = load_pack(args.pack)
    result = explore(
        pack, year_level=args.year_level, current_year=args.year, grades=_grades_from(args)
    )
    profile = StudentProfile(
        interests=tuple(i.upper() for i in args.interest[:3]),
        enjoyed_subjects=tuple(args.enjoy),
        assessment_style=args.style,
        teamwork=args.teamwork,
        priorities=tuple(args.priority),
        willing_extra_assessment=(False if args.no_extra_assessment else None),
        cost_sensitive=(True if args.cost_matters else None),
        goal_text=args.goal,
    )

    cov = _cov(pack)
    print(_rule())
    if cov.warning:
        print(f"  {cov.warning}\n")
    if profile.goal_text.strip():
        print(f'  You wrote: "{profile.goal_text.strip()}"')
        print("  PathAhead has not interpreted that — there is no model running here.\n")

    scores = score_all(pack, profile, result.transition.id)
    ranked = sorted(
        (s for s in scores.values() if s.score is not None), key=lambda s: -s.score
    )
    if not ranked:
        any_score = next(iter(scores.values()), None)
        print(f"  {any_score.unscored_reason if any_score else 'Nothing to score.'}")
        print(_rule())
        return 0

    for s in ranked[: args.top]:
        outcome = pack.outcomes[s.outcome_id]
        print(explain_fit(s, outcome))
        band = (
            f"{outcome.band.p10}-{outcome.band.p90} ({outcome.band.fact.as_of_year})"
            if outcome.band
            else "no band loaded"
        )
        print(f"  Evidence (separate axis): your {result.comparison_score:g} against {band}")
        emp = outcome.employment
        if emp and emp.has_salary:
            print(
                f"  Graduates {emp.fact.as_of_year}: ${emp.gross_p25:,}-${emp.gross_p75:,}, "
                f"median ${emp.gross_median:,}; {emp.employment_rate:g}% employed in six months"
            )
        elif emp and emp.unavailable_reason:
            print(f"  Graduate outcomes: {emp.unavailable_reason}")
        print()
    print(_rule())
    print(NOT_ADVICE)
    return 0


def cmd_health(args) -> int:
    pack = load_pack(args.pack)
    report = check_pack(pack, min_confidence=args.min_confidence)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    elif args.markdown:
        print(report.as_markdown())
    else:
        print(report.as_text())
    return 0 if (report.passed or not args.gate) else 1


def cmd_build(args) -> int:
    from tools.build_pack import build

    paths = build(args.pack, args.out)
    for label, path in paths.items():
        print(f"  {label:<10}{path}")
    return 0


def cmd_serve(args) -> int:
    from tools.serve import serve

    return serve(args.pack, port=args.port, open_browser=not args.no_browser)


_COMMANDS = {
    "levels": cmd_levels,
    "courses": cmd_courses,
    "score": cmd_score,
    "explore": cmd_explore,
    "plan": cmd_plan,
    "whatif": cmd_whatif,
    "timeline": cmd_timeline,
    "fit": cmd_fit,
    "health": cmd_health,
    "build": cmd_build,
    "serve": cmd_serve,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _COMMANDS[args.command](args)
    except PathAheadError as exc:
        print(f"\n  {_c('Something needs fixing:', 'bold')} {exc.message}", file=sys.stderr)
        print(f"  {exc.advice}\n", file=sys.stderr)
        return 2
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

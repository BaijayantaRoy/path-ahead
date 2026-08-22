"""Write published subject prerequisites into the pack.

WHY THIS FILE EXISTS
--------------------
A parent opened PathAhead, saw NTU's Physics / Applied Physics scored 52/100,
and asked how a student with no Physics could be shown that course at all. They
were right, and the answer is not that 52 was too high -- it is that any number
was wrong. A score puts a course into a ranking, and 52 still ranks it above two
hundred courses the student could actually enrol in.

We already knew this. `LanguageRequirement` was built after exactly the same bug
on a Chinese-medium diploma, and START_HERE states the rule plainly: a fit score
answers "how well does this suit you" and must never be asked "are you
eligible". The lesson was applied to one dimension and never generalised. What
stood in for subject prerequisites was a blanket overlay reading "programmes may
require specific subjects, check the university's list" -- which is our missing
homework handed to a sixteen-year-old, with the score printed anyway.

WHERE THE DATA COMES FROM
-------------------------
NTU publishes one authoritative table: "Minimum Subject Requirements for
Students with Singapore-Cambridge GCE 'A' Level", stamped "Information is
correct as at February 2026", covering the AY2026-27 application window.

    https://www.ntu.edu.sg/media/docs/default-source/undergraduate-admissions/msr/emsr_alevel.pdf

Every `label` below is transcribed from that table, not paraphrased. A rewritten
entry condition is how a family ends up applying for something they cannot take,
so the student reads NTU's words and can check them against NTU's own page.

WHAT IS DEuliberately NOT ENCODED
---------------------------------
The table carries three kinds of condition and only one of them belongs in a
hard gate:

  1. "H2 Level pass in Physics"                 -> encoded. A subject you either
                                                    offer or do not.
  2. "A good grade in General Paper"            -> NOT encoded. Nearly every
                                                    A-Level candidate sits GP;
                                                    the condition is about the
                                                    grade, and PathAhead does not
                                                    hold grades. Gating on it
                                                    would block almost everyone
                                                    on a condition almost
                                                    everyone meets.
  3. "A good grade in H1 Level Mathematics"     -> encoded as the SUBJECT only.
                                                    We can tell whether someone
                                                    offers Mathematics. We cannot
                                                    tell whether their grade is
                                                    "good", so we check the half
                                                    we can and say so.

Erring toward under-blocking is deliberate. A wrongly blocked course costs a
student an option they had; a wrongly scored one costs them a caveat. Only the
first is unrecoverable.

`subjects` is a list of alternatives -- "Physics/Chemistry/Biology" is ONE
requirement with three acceptable answers, and offering any one satisfies it.
Two separate requirements ("Mathematics, AND Physics/Chemistry/Biology") are two
entries, and both must be met.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "packs" / "singapore"

SOURCE = "ntu-msr-alevel"
AS_OF = 2026

# Shorthands for the combinations NTU repeats across dozens of programmes.
MATH = (["mathematics"], "h2", "H2 Level pass in Mathematics")
MATH_H1 = (["mathematics"], "h1", "H1 Level pass in Mathematics")
SCI = (
    ["physics", "chemistry", "biology", "computing"],
    "h2",
    "H2 Level pass in Physics/Chemistry/Biology/Computing",
)
SCI_NO_COMP = (
    ["physics", "chemistry", "biology"],
    "h2",
    "H2 Level pass in Physics/Chemistry/Biology",
)

#: outcome id -> list of (subject alternatives, level, NTU's own wording)
#:
#: Transcribed row by row. Where an outcome covers a family of programmes that
#: NTU lists separately (its double-major and second-major variants), the entry
#: records only what EVERY variant in that family requires, because blocking on
#: a condition that applies to one branch would cost a student the others.
NTU: dict[str, list[tuple[list[str], str, str]]] = {
    # -- College of Computing and Data Science ------------------------
    # "H2 Mathematics, OR H2 Physics/Computing" -- one requirement, three
    # acceptable answers, so it is a single entry and not two.
    "ntu-artificial-intelligence-and-society": [
        (["mathematics", "physics", "computing"], "h2",
         "H2 Level pass in Mathematics, or H2 Level pass in Physics/Computing"),
    ],
    "ntu-computer-science": [
        (["mathematics", "physics", "computing"], "h2",
         "H2 Level pass in Mathematics, or H2 Level pass in Physics/Computing"),
    ],
    "ntu-computer-engineering": [MATH, SCI],
    "ntu-data-science-artificial-intelligence": [MATH],
    # -- Renaissance Engineering --------------------------------------
    "ntu-renaissance-engineering": [MATH, SCI],
    # -- College of Engineering ---------------------------------------
    "ntu-aerospace-engineering": [MATH, SCI],
    "ntu-bioengineering": [MATH, SCI],
    "ntu-chemical-biomolecular-engineering": [MATH, SCI],
    "ntu-civil-engineering": [MATH, SCI],
    "ntu-electrical-electronic-engineering": [MATH, SCI],
    "ntu-environmental-engineering": [MATH, SCI],
    "ntu-information-engineering-media": [MATH, SCI],
    "ntu-materials-engineering": [MATH, SCI_NO_COMP],
    "ntu-mechanical-engineering": [MATH, SCI],
    "ntu-robotics": [MATH, SCI],
    "ntu-process-engineering-and-synthetic-chemistry": [
        MATH,
        (["chemistry"], "h2", "H2 Level pass in Chemistry"),
    ],
    # Maritime Studies asks at H1, or an O-Level Additional Mathematics pass.
    # Level is recorded but the check is on the subject, per the module note.
    "ntu-maritime-studies": [
        (["mathematics"], "h1",
         "H1 Level pass in Mathematics, or 'O' Level/equivalent pass in "
         "Additional Mathematics"),
    ],
    # -- College of Science -------------------------------------------
    "ntu-physics-applied-physics": [
        (["physics"], "h2", "H2 Level pass in Physics"),
        MATH,
    ],
    "ntu-biological-sciences": [MATH_H1, SCI_NO_COMP],
    "ntu-chemistry-biological-chemistry": [
        (["chemistry"], "h2", "H2 Level pass in Chemistry"),
        (["mathematics", "physics"], "h2",
         "H2 Level pass in Mathematics/Physics"),
    ],
    "ntu-mathematical-sciences": [MATH],
    "ntu-environmental-earth-systems-science": [
        MATH_H1,
        (["physics", "chemistry", "biology", "computing", "economics"], "h2",
         "H2 Level pass in Physics/Chemistry/Biology/Computing/Economics"),
    ],
    # Chinese Medicine also requires 'O' Level Chinese; that half is already
    # carried by the existing LanguageRequirement, and duplicating it here
    # would state the same condition to the reader twice.
    "ntu-chinese-medicine": [MATH_H1, SCI_NO_COMP],
    # -- Lee Kong Chian School of Medicine ----------------------------
    "ntu-medicine": [
        (["chemistry"], "h2", "H2 Level pass in Chemistry"),
        (["biology", "physics"], "h2", "H2 Level pass in Biology/Physics"),
    ],
    # -- Humanities, Arts and Social Sciences -------------------------
    # Only the rows with a genuine SUBJECT condition appear. "A good grade in
    # General Paper" is a grade condition on a subject nearly everyone sits,
    # and is left to the course page rather than turned into a gate.
    "ntu-economics": [
        (["mathematics"], "h1", "A good grade in H1 Level Mathematics"),
    ],
    "ntu-economics-and-data-science": [
        (["mathematics"], "h2", "A good grade in H2 Level Mathematics"),
    ],
    "ntu-philosophy-politics-and-economics": [
        (["mathematics"], "h2", "A good grade in H2 Level Mathematics"),
    ],
    "ntu-psychology": [
        (["mathematics"], "h1", "A good grade in H1 Level Mathematics"),
    ],
    "ntu-communication-studies": [
        (["mathematics"], "h1",
         "H1 Level pass in Mathematics, or 'O' level/equivalent pass in "
         "Additional Mathematics"),
    ],
    # -- Nanyang Business School --------------------------------------
    "ntu-applied-computing-in-finance": [
        (["mathematics"], "h2", "H2 Level Pass in Maths"),
    ],
    "ntu-accountancy": [
        (["mathematics"], "h1",
         "H1 Level pass in Mathematics, or 'O' Level/equivalent pass in "
         "Additional Mathematics"),
    ],
    "ntu-business": [
        (["mathematics"], "h1",
         "H1 Level pass in Mathematics, or 'O' Level/equivalent pass in "
         "Additional Mathematics"),
    ],
    # -- National Institute of Education ------------------------------
    "ntu-sport-science-management": [
        (["mathematics"], "h1",
         "H1 Level pass in Mathematics, or 'O' level/equivalent pass in "
         "Additional Mathematics"),
    ],
}

DETAIL = (
    "NTU publishes this in its Minimum Subject Requirements table for "
    "Singapore-Cambridge GCE 'A' Level applicants. Where it asks for a "
    "\"good grade\", PathAhead checks only that you offer the subject -- it "
    "does not hold your grades and will not guess at them."
)

URL = (
    "https://www.ntu.edu.sg/media/docs/default-source/undergraduate-admissions/"
    "msr/emsr_alevel.pdf"
)


def block(reqs: list[tuple[list[str], str, str]], indent: str = "    ") -> str:
    out = [f"{indent}subject_requirements:"]
    for subjects, level, label in reqs:
        out += [
            f"{indent}  - subjects: [{', '.join(subjects)}]",
            f"{indent}    at_level: {level}",
            f'{indent}    label: "{label}"',
            f'{indent}    detail: >-',
        ]
        out += [f"{indent}      {line}" for line in _wrap(DETAIL, 68)]
        out += [
            f"{indent}    fact:",
            f'{indent}      value: "{label}"',
            f"{indent}      as_of_year: {AS_OF}",
            f"{indent}      source: {SOURCE}",
            f"{indent}      confidence: high",
            f"{indent}      stale_after: 2027-02-28",
            f"{indent}      url: {URL}",
        ]
    return "\n".join(out) + "\n"


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def apply(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    written = 0
    for oid, reqs in NTU.items():
        anchor = f"  - id: {oid}\n"
        if anchor not in text:
            continue
        start = text.index(anchor)
        if "subject_requirements:" in text[start:start + 400]:
            continue  # already applied; this script is safe to re-run
        # Insert immediately after the id line, where a reader looking at the
        # outcome sees the eligibility condition before any of its statistics.
        at = start + len(anchor)
        text = text[:at] + block(reqs) + text[at:]
        written += 1
    path.write_text(text, encoding="utf-8")
    return written


def main() -> int:
    total = 0
    for name in ("outcomes-ntu-smu.yaml", "outcomes.yaml"):
        f = PACK / name
        if f.exists():
            n = apply(f)
            total += n
            print(f"{name}: wrote {n} outcome(s)")
    missing = sorted(NTU) if total == 0 else []
    if missing:
        print("no outcomes matched; ids may have changed", file=sys.stderr)
        return 1
    print(f"total: {total} of {len(NTU)} NTU programmes carry requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

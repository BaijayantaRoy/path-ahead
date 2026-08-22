"""Does the fit axis actually discriminate, for a real profile?

    python tools/check_saturation.py

Not a pass/fail gate — a measurement, printed. `test_fit_calibration.py`
guards the rules; this answers the question those rules exist to serve: when
someone real answers the questions, do they get a ranked list or a wall of
identical numbers?

It exists because 128 tests once passed on a version that told a child she was
a weak match for everything, and because large clusters of courses later tied
at the top for a realistic profile — not a scoring bug, but a symptom of
editorial data written at course-FAMILY level, which makes two courses
literally identical to the scorer.

No figure is quoted in this docstring on purpose. The count moves whenever the
DATA moves, not only when the scorer changes: loading polytechnic fees added a
Cost bucket and the top tie fell from 27 to 20 without a line of scoring code
being touched. A number written here would be stale within a session. Run it.
"""
import sys
from collections import Counter
from pathlib import Path

# Run from anywhere: tools/ is not a package root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.fit import score_all
from engine.loader import load_pack
from engine.profile import StudentProfile

pack = load_pack(Path("packs/singapore"))

# The profile from the real-input check: a student who took Further
# Mathematics, likes building things, wants to work with their hands.
profile = StudentProfile(
    interests=("R", "I"),
    enjoyed_subjects=("further-mathematics", "physics"),
    assessment_style="practical",
    teamwork="team",
    priorities=("earnings", "stability"),
    cost_sensitive=True,
    goal_text="i want to work with my hands on real machines, not sit in an office",
)

scores = score_all(pack, profile, "a-level-to-university-2026")
scored = {k: v.score for k, v in scores.items() if v.score is not None}
print(f"scored {len(scored)} of {len(scores)} courses\n")

counts = Counter(scored.values())
top = max(counts) if counts else 0
print(f"  distinct scores      : {len(counts)}")
print(f"  highest score        : {top}")
print(f"  courses tied at top  : {counts[top]}")
print(f"  largest tie anywhere : {counts.most_common(1)[0][1]} "
      f"(at {counts.most_common(1)[0][0]})")

print("\n  biggest tie clusters:")
for score, n in counts.most_common(5):
    if n < 2:
        continue
    ids = [k for k, v in scored.items() if v == score][:3]
    insts = Counter(pack.outcomes[i].institution_short for i, v in scored.items() if v == score)
    print(f"    {n:3} courses at {score:5.1f}  {dict(insts)}")
    for i in ids:
        print(f"          {pack.outcomes[i].institution_short} {pack.outcomes[i].name}")

# Do tied courses at least differ in what they SAY? Two courses with the same
# score and the same sentence are a tie wearing a rosette.
print("\n  do tied courses read differently?")
for score, n in counts.most_common(3):
    if n < 2:
        continue
    ids = [k for k, v in scored.items() if v == score]
    summaries = {
        (pack.outcomes[i].editorial.summary if pack.outcomes[i].editorial else None)
        for i in ids
    }
    verdict = "distinguishable" if len(summaries) == n else (
        f"{len(summaries)} descriptions for {n} courses")
    print(f"    at {score:5.1f}: {verdict}")

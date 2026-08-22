# Two pre-existing `check:ui` failures, found 2026-08-09 — RESOLVED 2026-08-14

> **Status: both fixed.** `check:ui` is 116/116. This file is kept because the
> second failure was hiding a real user-facing bug, and because both are good
> examples of a guard doing its job and being ignored.

Found while verifying the PSLE stage. Neither was caused by that work — both
sat in the A-Level profile step. They were recorded rather than fixed at the
time, because each needed a decision about which side was wrong, and that
decision was deferred. They then stayed open for five days and became "the two
known failures", which is how a red suite stops being informative.

---

## 1. `constraint chips renders` — 2 rendered, expected at least 4

**The check was wrong.** `tools/check_ui.mjs` asserted `#conChips` renders at
least 4 chips. `web/index.html`'s `CON` defines exactly two, and deliberately:

> *"Cost is a real constraint" and "Happy to sit interviews" used to live here
> AND as importance rows — the same question in two idioms, on one page. They
> are now asked once, as importance. What is left are the two that are facts
> about a situation rather than preferences, so they have no importance row.*

That is a good decision and the check simply predated it.

**Fix:** the expectation is now 2, with the reasoning inline, plus a new check
(`the profile step asks nothing twice`) that asserts cost and extra-assessment
have *not* reappeared as chips — so the consolidation is protected rather than
merely done.

---

## 2. `how many optional questions are answered is stated` — and the real bug underneath

**Both sides were wrong, and the second one mattered.**

The surface problem was the one recorded on 2026-08-09: the anti-nagging regex
bans `/must|should|need to|required/i` from the progress note, and the note
said *"none of them is required"* — the opposite of nagging, matched anyway
because the regex cannot see the negation. Same shape as `test_safeguards.py`
banning `guarantee a place` and a caveat saying *"does not guarantee a place"*.

**Fix:** rephrased to *"every one of them is optional"*. The guard was not
loosened. Teaching a regex about negation is a fragile thing to do, and the
rewritten sentence is no worse.

**But the 2026-08-09 note also asked the right follow-up question** — whether
`cost_sensitive` and `willing_extra_assessment` should still be in `SIGNALS`
if the UI no longer asks them — and the answer turned out to be a live bug:

- `FIT_SIGNALS` has 9 entries and mirrors `engine/fit.py`.
- The browser sets only 7 of them. `cost_sensitive` and
  `willing_extra_assessment` are initialised to `null` and never written,
  because those questions became importance rows (see failure 1).
- `paintSignalProgress()` counted all 9.

So the progress line could reach at most **"7 of 9 answered"**. A family who
answered every question on the screen was told two were still missing, with no
way to find them. That shipped, and no test caught it, because the only check
looking at that line was failing for an unrelated reason and had been
mentally filed as noise.

**Fix:** a new `ASKED_SIGNALS` — `FIT_SIGNALS` minus the two the browser does
not ask — drives the progress line. `FIT_SIGNALS` is untouched, because it
defines `signals_available` inside a score and must stay identical to the
Python engine; changing it to fix a UI counter would have broken cross-engine
parity on a number that appears in real output.

---

## What this cost, and the lesson

Five days of a two-failure suite, during which a real bug sat inside one of
the failures. A known-failing check is not a known state — it is a place where
new failures arrive unnoticed.

If a check cannot be fixed immediately, the options are: fix the code, fix the
check, or mark it skipped **with the reason in the skip message** so the suite
returns to green and a new failure is still visible. Leaving it red and
writing a document is the option that looks most responsible and works least
well.

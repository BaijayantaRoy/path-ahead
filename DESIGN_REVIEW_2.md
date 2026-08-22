# PathAhead — Design Review 2

## What a student and a parent would still find missing

> Written 2026-08-02, before the v0.2 build. The first review ([DESIGN_REVIEW.md](DESIGN_REVIEW.md)) asked *"is the architecture right?"*. This one asks a harder question: **sit at the kitchen table at 11pm with a worried parent and a frightened seventeen-year-old, open the app, and see what it fails to answer.**
>
> Companions: [README.md](README.md) · [SAFEGUARDS.md](SAFEGUARDS.md) · [ROADMAP.md](ROADMAP.md)

---

## 0. The blocking issue: fit scoring is meaningless at current breadth

**Do not ship fit scoring over 21 NUS courses.**

Fit ranks options against each other. With one university loaded, every ranking is drawn from a pool that excludes NTU, SMU, SUTD, SIT, SUSS, all five polytechnics and ITE. A student whose genuine best fit is an SIT applied degree or a Temasek Polytechnic diploma would be shown a confident, well-reasoned, beautifully-rendered **wrong answer** — and the reasoning would make it *more* persuasive, not less.

That is a worse failure than having no fit score at all. A ranking over an unrepresentative pool is not incomplete information; it is misinformation with a progress bar.

**Consequence for sequencing.** Breadth comes before intelligence:

1. All six autonomous universities (published IGPs — same NUS pattern, five more sources).
2. The five polytechnics (JAE cut-off points are on data.gov.sg, cleanly licensed).
3. ITE, at least at course-family level.
4. *Then* fit scoring.

Until breadth exists, fit runs in an explicitly labelled **preview** mode: shown, clearly marked as covering NUS only, and never described as "your best match". The Data Health report gains a `fit_pool_coverage` measure, and the UI refuses to use the word "best" while coverage is partial.

---

## 1. The question the app never answers: *when?*

Missing entirely, and probably the single highest-value addition.

At the kitchen table the live question is rarely "what is my score". It is **"what do we have to do, and by when?"** Every one of these is published, dated, and citable:

- A-Level results release
- Application windows — **which differ by university**, and one of them will close first
- Interview, portfolio and aptitude-test dates for the courses that need them
- Offer release, and the deadline to accept
- Appeal windows, which are short and easy to miss
- NS enlistment timing, and how deferment interacts with an offer
- Open house dates

Missing a deadline is more catastrophic than missing a grade profile by two points, and unlike the grade profile it is entirely preventable. NUS already publishes *Important Dates* and *Faculty Interview and Test Dates* as separate pages.

**Design:** a `Milestone` entity on the pathway graph, and a **personalised timeline** generated from the resolved cohort — "you are here, this is what is next, this is what closes first." It should be exportable to a calendar file, because that is how it actually gets used. A parent who gets nothing else from this app but a correct timeline has been well served.

---

## 2. National Service: a two-year hole in the model

For roughly half of every cohort the timeline the app currently draws is simply wrong.

A male student sits the A-Level, applies, receives an offer, **defers, serves for about two years, and matriculates at 20 or 21**. NUS publishes a *Reserved Places for Full-Time National Servicemen* page precisely because this is a distinct admissions path. Nothing in PathAhead models it, which means:

- The admission year shown is right; the **start** year is wrong.
- Boys and girls in the same JC class are on different clocks, and a sibling comparison will confuse a family.
- Labour-market data for a course will have moved by two years before he enrols — so the salary figure he reads at 18 is not the one he graduates into.
- The two years are themselves a planning object: some students use them to reconsider entirely, and the app should treat that as normal rather than invisible.

**Design:** `service_obligation` as an optional cohort attribute, feeding the timeline and carrying a plain note that a deferred place is a normal, published route — not a setback.

---

## 3. Money, and the bond nobody mentions until it is too late

A parent's first three questions include "how much". PathAhead currently says nothing.

- Tuition fees vary by course **and by citizenship** — Singapore Citizen, PR, International are three different numbers.
- The **MOE Tuition Grant** is the mechanism that makes the citizen price what it is.
- **Accepting the tuition grant as a non-citizen carries a service bond** — a multi-year obligation to work in Singapore. Families discover this late, and it is a genuine life decision, not a footnote.
- Financing exists and is under-used: CPF Education Loan Scheme, the Post-Secondary Education Account, MENDAKI subsidy, bursaries, work-study routes.
- The four-year cost of a degree versus a three-year diploma is a real comparison for a family under pressure, and one that pushes people toward routes they had dismissed.

**Design:** cost as a first-class, cited outcome attribute with a citizenship selector, and financing surfaced as a *route enabler* rather than a fine print. The bond gets an explicit overlay, in the same class as "this course requires an interview" — a thing that is never silently dropped.

**The ethical line stays where it was:** cost is information, never a sort key, and it enters the fit score only if the family says money is a constraint — in which case the reasoning says so out loud.

---

## 4. Students choose a *name*, not a course

An eighteen-year-old picks "Business Analytics" with essentially no idea what the weeks look like. This is what drives people to switch or drop out, and no calculator addresses it.

What they actually need to know:

- How much mathematics is genuinely in it
- How much writing, how much group work, how much lab or studio time
- Whether there is a compulsory internship or attachment
- Contact hours versus independent study
- How it is assessed — which the fit model already asks them about, so the two sides finally meet

Much of this is published in course structure pages. It is thin, tedious data to gather and it is exactly what a student wants at 11pm.

---

## 5. "Can I change my mind?" — the most important question nobody scores

A seventeen-year-old is being asked to commit on the basis of self-knowledge they do not yet have. The honest, kind, *and* accurate thing a guidance tool can do is tell them **how reversible each choice is**:

- Broad-entry programmes where you declare a major later
- Common first years where you choose your specialisation afterwards
- Double majors, minors, and how easy internal transfer actually is
- Where a route forecloses options and where it keeps them open

**Design:** a `flexibility` attribute per outcome — how late you can specialise, whether internal transfer is realistic, what it forecloses. And a positive treatment: *"if you are not sure yet, these keep the most doors open."*

That framing is worth more to an undecided student than any fit score, because it is advice that is robust to them being wrong about themselves.

---

## 6. The app assumes you have a destination. Most students do not.

Every flow currently starts from grades or from a named course. The most common real state is **"I have no idea what I want to do."**

There is no exploration mode. There should be: start from interests, work outward, discover courses that were never on the list. This is also where the fit reasoning earns its keep — not to rank a shortlist someone already had, but to surface the option they had never heard of.

---

## 7. Reverse GES: what does this course actually *lead to*?

Students reason "Medicine → doctor" and then have no model at all for "Economics → ?".

The Graduate Employment Survey reports employment by sector, not just salary. *"Graduates of this course went into financial services, technology, public sector..."* is citable, official, and answers the question a student is actually asking, which is **"what happens to people like me?"** — not "what is the median".

And salary should be shown the way the grade profiles already are: **a range with a year and a source**, never a bare median. Same envelope, same discipline, same reason.

---

## 8. Decisions are made by comparing, and there is no comparison view

The real ritual is a family sitting down with three or four shortlisted courses and arguing. PathAhead offers one list and one plan view.

Missing: a **shortlist**, and a side-by-side comparison across every axis — evidence, fit, cost, outcomes, flexibility, deadlines, extra assessments. Plus a printable version, because the output of that argument is a conversation with a form teacher, and paper is what gets carried into it.

---

## 9. The parent and the child do not agree

This is the elephant in the Singaporean kitchen, and a tool that pretends otherwise is not being useful.

A design that helps without taking sides: **let each of them fill in their own view, then show where they agree and where they differ.** No verdict, no arbitration — just "you both rated stability highly; you differ on how much hands-on work matters."

Naming a disagreement calmly, with evidence on both sides, is often the entire service. This must be handled with real care and no cleverness, but leaving it out is a decision too.

---

## 10. Results day went badly

The moment of maximum distress and maximum need, and there is no path built for it.

It should be reachable in one tap and it should **lead with routes, never with a score**. The engine's `MIN_ROUTES` rule already encodes the right instinct; this is the flow where that instinct matters most, and it deserves its own entry point rather than being the tail end of a calculator.

---

## 11. Smaller gaps, in rough order of value

- **Appeals, concretely.** Everyone asks. It differs per institution and is tightly time-boxed. One generic route sentence is not enough.
- **Scholarships**, including bonded ones (PSC, MOE Teaching, defence). These change the calculus completely and are invisible here.
- **Aptitude-Based Admissions as something you prepare for**, not just a route that exists.
- **Overseas universities.** A large share of Singaporean families consider them. At minimum, acknowledge and link rather than implying the six local universities are the world.
- **IB, NUS High and IP students.** Different qualifications, entirely unmodelled. Currently they get nothing and are not told why.
- **Open house dates and named humans.** The app should end by pushing toward people and events, not only URLs.
- **Multiple children.** Parents have more than one, and comparing siblings is a real and delicate use.
- **Mother Tongue interface support.** Structural support was designed for and never built. A disclaimer only the fluent can read is not a disclaimer.
- **"Will this field still exist in six years?"** Everyone is thinking it. Do not predict — but SkillsFuture publishes official growth sectors, and citing that is honest where forecasting is not.

---

## 12. Honest critique of the v0.2 plan itself

**The free-text goal field does almost nothing in Tier 0.** With no model, "I want to work on climate but not stuck in an office" cannot be semantically matched. Keyword matching would be a party trick that produces confident nonsense. The honest Tier-0 use is to **reflect it back at the point of decision** — *"you said you did not want to be at a desk all day; two of your three top matches are desk-based"* — which is genuinely useful and requires no intelligence. Real matching waits for Tier 1, and the UI should not imply otherwise.

**A high fit score on an out-of-reach course can be cruel.** "This is a 94% match for you" next to "below last year's range" needs deliberate handling: lead with the routes, not the gap. The two axes must be designed together, not merely displayed together.

**Interest questions must not feel like a quiz.** Six taps, meaningful, done. The moment it feels like a personality test, an anxious family closes the tab.

**Every added question must earn its place.** Each one should visibly state what it unlocks, and skipping must be genuinely free — fit confidence goes down, nothing breaks, no nagging.

---

## 13. What this means for the build

**In v0.2 (now):**

- Fit scoring in labelled preview mode, NUS-only, never called "best"
- The full input model — goals, interests, subject enjoyment, working style, constraints, trajectory
- GES outcomes: salary *range* and employment rate per course, cited, plus sector destinations
- Milestones and a personalised timeline, including NS
- Cost, tuition grant and the bond, as cited overlays
- Flexibility ("can I change my mind") per outcome
- Shortlist and side-by-side comparison, printable
- Exploration mode for the student with no destination
- A "results day was hard" entry point
- Subject typeahead, and the UI rebuild

**Next, and blocking the removal of the preview label:**

- The other five universities, then the polytechnics, then ITE

**Deliberately deferred, and recorded so it is a decision rather than an oversight:**

- Parent-versus-child comparison — high value, needs its own care
- Overseas universities, IB/NUS High/IP qualifications
- Mother Tongue interface
- Scholarships in depth

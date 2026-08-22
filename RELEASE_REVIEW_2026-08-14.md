# PathAhead — pre-release review, 2026-08-14

A full audit of the repository against four questions: is it ready for a public
GitHub release, is it private enough, does it leak data or PII, and does it
violate Singapore law or the licences it relies on.

Scope: every tracked and untracked file in the project root, the browser build,
the Python engine and CLI, the data packs, the build tooling, the CI workflows,
and the project's own governance documents. Findings are grounded in what the
code actually does, not in what the documentation claims it does — several of
the findings below are precisely the gap between those two.

> ⚠️ Not legal advice. This is an engineering and compliance review. Items in
> §2 marked **[LEGAL]** need a Singapore-qualified lawyer before public launch,
> as `SAFEGUARDS.md` §7 already anticipates.

---

> ## ✅ REMEDIATION COMPLETE — 2026-08-14
>
> Every technical blocker and should-fix item in this report has been resolved.
> See the CHANGELOG entry *"release-readiness pass"* for what changed and why.
>
> **Two items remain, and neither is a code change:**
>
> 1. **The ODBI publication gate (§1.4)** — the project's own rule that nothing
>    goes public until an employment/outside-interest approval line clears. Only
>    you can confirm this.
> 2. **A review by someone qualified in Singapore law (§2.1 item 15)** — the
>    last unchecked box in `SAFEGUARDS.md` §7. The licensing posture is now
>    considerably more conservative than when this report was written (nothing
>    under a restrictive licence is redistributed at all), which makes that
>    review easier, not unnecessary.
>
> Current state: `ruff` clean · 305 tests · 37/37 cross-engine · 19/19 static ·
> **116/116 DOM** · health gate PASS · every CI safeguard gate passing.
> Verified in a simulated clean checkout, which is what CI will see.

---

## Verdict *(as first written, before remediation)*

**Not ready to publish today. Close, though — and the gap is smaller than the
list below makes it look.**

Two of the four blockers are one-line fixes. One is a decision, not a task. One
is the project's own governance gate, which is not mine to clear.

The engineering underneath is genuinely strong: no secrets, no telemetry, no
tracking, no PII collection, no persistence, no analytics SDK, a strict CSP on
the local server, 295 passing tests, a cross-engine parity suite, and a CI
pipeline that enforces the safeguards rather than describing them. The problems
are concentrated in a small number of places where the shipped artifact drifted
away from the promises the project makes about itself.

| Area | State at review | Now |
|---|---|---|
| Secrets / credentials | ✅ Clean — nothing found | ✅ |
| PII collection | ✅ Clean — the fields genuinely do not exist | ✅ |
| Telemetry / analytics | ✅ Clean — none, and CI enforces it | ✅ |
| Local data persistence | ✅ Clean — memory only, deliberately | ✅ |
| Typed data leaving the device | ✅ Clean — verified call site by call site | ✅ |
| **Third-party requests on page load** | ❌ **Blocker — Google Fonts** | ✅ Removed; meta CSP added |
| **Data licence compliance** | ❌ **Blocker — ODL attribution + MOE reproduction** | ✅ Attribution rendered; data withdrawn |
| **Repository hygiene** | ❌ **Blocker — no git repo, stray artifacts** | ✅ Initialised and cleaned |
| **Governance gate** | ❌ **Blocker — the project's own ODBI line** | ⏳ **Yours to confirm** |
| Singapore law (PDPA, CPFTA) | ⚠️ Good posture, two gaps below | ✅ Gaps closed; legal review still advised |
| Safeguards implementation | ✅ Strong, with one stale claim | ✅ Reconciled (§3b answer 6) |

---

## 1. Blockers — do not publish until these are resolved

### 1.1 The app loads Google Fonts on every page view ❌

`web/index.html`, lines 9–11:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:...&family=Outfit:..." rel="stylesheet">
```

Three lines further down, the same file's own header comment reads:

```
PathAhead — one file. No framework, no fonts fetched, no trackers.
Everything runs in the browser; there is no server to send anything to.
```

And the page header, visible on every screen, tells the reader:

> *Nothing you type here leaves this device.*

**What actually happens.** Before the page renders, the browser makes two
requests to Google. Google receives the visitor's IP address, User-Agent, and
(for the stylesheet) a Referer. This happens automatically, with no user
action, on every single page load.

**Why this is the most serious finding in the repo.** It does not leak typed
data — grades, postal code and free text genuinely stay in memory, which I
verified call site by call site. But it does disclose to a third-party
advertising company that a given device visited a PSLE planning tool. The users
are Singaporean children and their parents. The whole value proposition of this
project is that it is the tool that does not do this.

**It is also already forbidden by this project's own CI.** `.github/workflows/ci.yml`
line 163 fails the build on any external resource in `web/index.html` outside an
allowlist of `moe.gov.sg`, `nus.edu.sg`, `data.gov.sg`, `github.com/BaijayantaRoy`.
Running that exact gate today:

```
https://fonts.googleapis.com
https://fonts.googleapis.com/css2?family=Inter:...
https://fonts.gstatic.com
https://www.google.com/maps/dir/?api=1&destination=...
```

**CI fails right now.** The first public push would go red.

There is a second, quieter tell that the intent was always "no external
resources": `tools/serve.py` sets `Content-Security-Policy: default-src 'self'`,
which *blocks* these font requests during local development. So the fonts
silently never load when the maintainer tests locally — and do load for every
real user on GitHub Pages, where no such header can be set. The bug is invisible
in exactly the environment it was written in.

**Fix — 3 lines, no visual risk.** Delete lines 9–11. The CSS already has full
fallback stacks:

```css
--serif: "Outfit", ui-sans-serif, system-ui, sans-serif
--sans:  "Inter",  ui-sans-serif, system-ui, -apple-system, sans-serif
```

Removing the link degrades to the system UI font with no layout breakage. If the
typography matters, self-host the two WOFF2 files under `web/assets/` and add an
`@font-face` block — that keeps the look and the promise. Either way, add
`<meta http-equiv="Content-Security-Policy" content="default-src 'self'; ...">`
to `index.html` so the guarantee travels with the file to GitHub Pages instead of
living only in the local dev server.

**Also fix the Maps allowlist.** The "Get directions" link is a deliberate,
documented, user-initiated click-through carrying only the school's own public
address (verified: the family's postal code is not attached, and there is a DOM
check asserting exactly that). It is defensible — but CI does not know that. Add
`google\.com/maps` to the allowlist regex with a comment explaining why, so the
gate keeps protecting you instead of being disabled.

---

### 1.2 Data licence compliance — two distinct problems **[LEGAL]** ❌

#### (a) The Singapore Open Data Licence attribution is missing from the product

ODL v1.0 (fetched and read in full during this review) states:

> "You must include **in your products, applications or websites** that Use the
> datasets, a **conspicuous notice** acknowledging the source of the datasets and
> **including a link to the most recent version of this Licence**."

Five sources in the pack are `sg-odl-1.0`, including the school directory that
the entire PSLE shortlist is built on.

What the app renders on `#/data` (`web/index.html:3919`) is the bare licence *id*
as plain text — `sg-odl-1.0` — with no acknowledgement sentence and no link to
the licence. `README.md` has a sentence and a link; the **application does not**.

`SAFEGUARDS.md` §3b already specifies the exact block and says it is *"rendered
in-app and in the README"*. It is not in-app. The requirement was written down
and then not implemented.

This is a breach of a licence condition, and ODL §"Termination" allows the
Agency to terminate the licence immediately on breach. It is also the cheapest
fix in this document.

**Fix.** Render on `#/data`, and ideally in the footer:

> Contains information from the *General information of schools* dataset,
> accessed 2026-08-13 from data.gov.sg, which is made available under the terms
> of the [Singapore Open Data Licence version 1.0](https://data.gov.sg/open-data-licence).
> PathAhead is not affiliated with, endorsed by, or connected to any of these sources.

`engine/model.py:KNOWN_LICENCES` already holds the licence URL — it simply is not
being used at render time. Make the licence id a hyperlink and add the notice.

#### (b) The 2025 cut-off data is a wholesale reproduction, sourced third-hand

This is the one that needs a real decision, and possibly a lawyer.

`packs/singapore/secondary-schools.yaml` now carries `cutoff_2025` for 139 of 147
schools — roughly a thousand data points. Its source record says:

```yaml
licence: moe-tou
licence_name: "MOE Terms of Use (facts cited and linked; no content reproduced)"
url: https://www.moe.gov.sg/schoolfinder
```

Three problems, in increasing order of seriousness:

1. **The licence label is now false for this source.** "No content reproduced" is
   accurate for the other 28 `moe-tou` sources, which cite a rule and link to it.
   This source reproduces an entire dataset. The label should not claim otherwise.

2. **`url` points somewhere the data did not come from.** The figures were not
   retrieved from `moe.gov.sg/schoolfinder` — SchoolFinder is a client-rendered
   app with no bulk export, as the note candidly explains. They were transcribed
   from KiasuParents' compiled table. The `note` field is admirably honest about
   this; the `url` field, which is what the UI actually renders as "source", is
   not. A reader clicking through cannot verify the number against what was used.

3. **It copies a third party's compilation.** KiasuParents did the work of
   assembling 139 schools into one table. Copying that table wholesale engages
   *their* rights and *their* site terms, independently of MOE's position.
   Individual cut-off numbers are facts and facts are not copyrightable; an
   exhaustive list is weak as an original compilation under the Copyright Act
   2021. So the risk is low rather than nil — but it is not zero, it is
   undisclosed to the reader, and KiasuParents receives no attribution anywhere
   in the shipped product.

   Separately, `SAFEGUARDS.md` §3b design answer 3 commits the project to
   *"no bulk downloading, no wholesale republication"*. This is wholesale
   republication. The document and the pack now disagree.

**Options, best first.**

- **Ask MOE for written permission.** Their ToU has a permission process; a free,
  non-commercial, open-source public-good tool that deep-links back to
  SchoolFinder is a sympathetic request. This is the only option that makes the
  feature unambiguously safe, and it costs an email.
- **Ship the filter without shipping the table.** Keep `within_reach()`, but have
  it read a cut-off the *user* enters or confirms from SchoolFinder, and
  deep-link each school to its own SchoolFinder page. Slower for the user;
  eliminates the redistribution question entirely.
- **Publish as-is with corrected metadata.** Fix the licence label, point `url`
  at the page actually used, credit KiasuParents in-app, and record the
  fair-dealing argument (research/private study, non-commercial, transformative,
  facts not prose). Defensible, not risk-free. If you take this route, do it
  *knowingly* — write the reasoning down in `SAFEGUARDS.md` and reconcile §3b so
  the document stops contradicting the pack.

Whichever you choose, **update `SAFEGUARDS.md` §3b in the same commit.** The
current state — a safeguards document forbidding the thing the pack does — is
worse than either resolution, because it makes the whole document less credible.

---

### 1.3 There is no git repository ❌

```
$ git rev-parse --is-inside-work-tree
fatal: not a git repository
```

The project has never been initialised or committed. Nothing is under version
control. This is a blocker in the literal sense — there is nothing to push — but
it also means several things worth handling deliberately on the first commit
rather than cleaning up in the second:

**Delete before the first commit:**

| Path | Why |
|---|---|
| `ges_data.json` | 70 bytes containing `404 Not Found` — a failed download saved by mistake |
| `PathAhead — understand the path ahead.pdf` | 449 KB Chrome print-to-PDF of a live session. It embeds a worked example's typed grades and leaks the OS version in metadata. A tool that promises never to persist what a family types should not ship a file containing what someone typed — even a demo. |

**Add to `.gitignore` before the first commit:**

| Path | Why |
|---|---|
| `web/site/` | 393 generated files, 3.1 MB. CI never rebuilds it (the Pages job runs `cli.py build` but not `build_static.mjs`), so committing it means shipping build output that silently drifts from the pack. Either gitignore it and add `npm run site` to the Pages job, or commit it knowingly and add a CI check that it is up to date. Ignoring it and building in CI is the right call. |

**Remove from `.gitignore`:**

| Path | Why |
|---|---|
| `package-lock.json` | Currently ignored. Without a committed lockfile, CI's `npm install` resolves floating `^` ranges, so builds are not reproducible and a compromised transitive dependency lands with no diff. Lockfiles should be committed. |

**Also:** `playwright-core` is declared as a **runtime** dependency in
`package.json` but is imported nowhere in the codebase. It is the single largest
contributor to a 27 MB `node_modules`. Remove it.

Confirmed already correctly ignored: `.venv/`, `node_modules/`, `__pycache__/`,
`dist/`, `web/data/`, `*.profile.json`, `profiles/`, `logs/`. The ignore file's
comment about never committing user data is good practice and should stay.

---

### 1.4 The project's own publication gate has not cleared ❌

This one is not a code finding, and it is not mine to resolve — but it outranks
everything above it.

`SAFEGUARDS.md` §7, first line:

> "Nothing goes public before the ODBI line clears (`PLAN_ASSUME_NO.md`)."

Repeated in `ROADMAP.md` (twice) and `DESIGN_REVIEW.md` (twice):

> "build privately, publish only after the ODBI approval line clears… Build now,
> publish on the yes."

`PLAN_ASSUME_NO.md` is not in this repository — it appears to be a
portfolio-level governance document covering outside-business-interest /
employment approval.

**By the project's own stated rule, PathAhead is not cleared for public release
until that line clears.** No technical fix changes this. Please confirm the ODBI
position before pushing, and — if it has cleared — update these four references
so the repository stops telling readers it is embargoed.

---

## 2. Should fix before launch

### 2.1 `SAFEGUARDS.md` §7 checklist — actual state

I walked all fifteen items against the code rather than the document.

| # | Item | State |
|---|---|---|
| 1 | No field collects name / NRIC / school / email / contact | ✅ Verified. Every `<input>`, `<select>` and `<textarea>` enumerated; none identify. CI gate passes. |
| 2 | No telemetry, analytics or crash reporting; update check carries no identifiers | ✅ Verified. `check_for_update()` sends a bare GET with a UA and nothing else — and is exported but **never called**, so no check happens at all. |
| 3 | "Delete everything" one click, visible | ⚠️ **N/A but claimed.** Nothing persists, so there is nothing to delete — arguably better. But `SAFEGUARDS.md` §2 promises the control for Tier B. Either build it or scope the claim to "not applicable: nothing is stored". |
| 4 | Not-official notice in app header, README, repo description | ✅ In header (`index.html:851`, every page) and README. Repo description is set at push time — remember it. |
| 5 | Not-a-prediction line inline with every result | ✅ Verified at three call sites. |
| 6 | Signpost to teachers / ECG counsellor / admissions | ✅ Present. |
| 7 | data.gov.sg attribution block with live licence link | ❌ **See §1.2(a).** README only, not in-app. |
| 8 | Every fact carries provenance; health gate green | ✅ `health --gate` → **PASS**, 66 sources. |
| 9 | No MOE/SEAB/institution logos, crests, colours or prose | ✅ Four own-design SVGs only; no crest, no institutional imagery, no reproduced prose. |
| 10 | No school ranking, no default sort by selectivity | ✅ Strongly verified. The school match score was removed entirely on 2026-08-13; sorting is distance-then-name. Multiple tests and DOM checks enforce it. |
| 11 | Backward mode returns ≥3 routes, or an honest incomplete | ⚠️ `health --gate` **WARNs**: 33 outcomes have fewer than 3 routes. `engine/backward.py` does return "route data incomplete" honestly, so the safeguard holds — but 33 is a lot of thin coverage to launch with. Worth a pass. |
| 12 | Banned-phrase copy review passed | ✅ `test_safeguards.py` + `test_guardrail.py` green (35 tests). |
| 13 | Numeric guardrail adversarial suite passing | ✅ Green. |
| 14 | "This number looks wrong" link on every figure | ✅ Present; carries only pack version, course id, field id — verified no user data in the prefilled issue body. |
| 15 | Disclaimer wording and §3 licensing reviewed by a Singapore lawyer | ❌ **Not done.** Given §1.2, this is now the item that matters most. |

### 2.2 `robots.txt` will not be found where it is published

`build_static.mjs` writes `robots.txt` and `sitemap.txt` into `web/site/`, but the
Pages job uploads `path: web`, making the site root `web/`. Crawlers look for
`/robots.txt`; the file lands at `/site/robots.txt` and is ignored. The
`Sitemap:` line is also only emitted when a `BASE` env var is set, which CI never
sets — so it is absent entirely.

Not a legal issue. But the static site was carefully built to `noindex` 98
incomplete pages, and that intent is undermined if the crawl directives are
misplaced. Move both to the deploy root, and set `BASE` in the Pages job.

### 2.3 Stale self-descriptions

- `START_HERE.md` claims the DOM suite is 66/66 as of 2026-08-05. It is
  **111/113** today, with two known, documented failures
  (`docs/UI_CHECK_FAILURES_2026-08-09.md`). The doc that new readers are pointed
  at first is the one that is most out of date.
- Those two failures (`constraint chips renders`, `how many optional questions
  are answered is stated`) have been open since 2026-08-09 and are honestly
  recorded as needing a product decision. Fine to launch with — but a red CI
  badge on a public repo invites the wrong first impression. Either fix them or
  mark them skipped-with-reason so CI is green and the reason is still visible.
- **Latent CI trap:** the "no superlatives" gate only runs when fit coverage is
  partial. Coverage is currently `complete = True`, so it is skipped. If coverage
  ever regresses, the grep will fire on an HTML *comment* at `index.html:942`
  that describes a past bug ("ranked a Chinese-medium diploma as a top match").
  Reword the comment now.

---

## 3. What is genuinely good

Worth stating plainly, because the blocker list above is not the whole picture
and this is unusually disciplined work.

**Privacy engineering.** The `localStorage` decision is the tell. There is a
theme toggle — the single most common excuse to write to disk — and the code
deliberately keeps it in memory, with a comment explaining that a shared family
computer must carry nothing between sessions. That is choosing the promise over
the convenience when nobody would have noticed either way.

**The local server.** `127.0.0.1` only, request logging suppressed *as a stated
privacy choice* ("a local request log is a record of what a family looked up"),
`default-src 'self'` CSP, `Referrer-Policy: no-referrer`, `nosniff`,
`X-Frame-Options: DENY`. Better hardened than most production deployments.

**No injection surface.** Exactly two `innerHTML` uses, both hard-coded SVG icons.
Everything else builds DOM through a helper that uses `textContent`. Free-text
input (`goal_text`) is echoed back safely and never interpreted.

**CI that enforces rather than describes.** Identity-field grep, telemetry-domain
grep, superlative gate tied to actual coverage, editorial-labelling assertion,
cross-engine golden replay, and a data-health gate that blocks release on stale
figures. The third-party-resource gate is the reason §1.1 is catchable at all —
it works, it is just currently being failed rather than heeded.

**Honest data modelling.** Three published statistics kept in separate
vocabularies so a polytechnic min-max can never render as a percentile band.
Absence of data returning `None` and never `False`. Eligibility as a gate rather
than a low score. The `cutoff_2025` source note is more candid about its own
weakness than most commercial products manage.

**Test discipline.** 295 Python tests, 37/37 cross-engine fixtures, 111/113 DOM
checks, 18/18 static-site checks, health gate PASS. Verified fresh during this
review, not taken from the changelog.

---

## 4. Answers to the four questions asked

**Is it ready for a GitHub release?**
No — four blockers (§1). Two are one-line fixes, one is a data-licensing
decision, one is your own ODBI gate. Realistically an afternoon of work plus
whatever the licensing decision requires.

**Is it private enough?**
Almost. The architecture is genuinely private — no accounts, no storage, no
telemetry, no server, computation entirely local. One leak: Google Fonts
discloses every visitor's IP to Google on page load, which contradicts the
header text on every screen. Fix that and the claim becomes literally true.

**Any data or PII leakage?**
No PII leakage. No secrets, no credentials, no API keys, no email addresses, no
machine paths, no usernames beyond the maintainer's intended public GitHub
identity. Nothing a user types reaches the network — verified at every call
site. Two lesser items: the Google Fonts request (metadata, not content), and
the stray session-print PDF that should be deleted before the first commit.

**Any violation of Singapore law?**
Nothing criminal, nothing close. PDPA posture is strong — the safest possible
design, which is to collect nothing, so most obligations never attach; the
under-13 consent problem is avoided rather than managed. CPFTA's
misleading-representation standard is the one to watch, and it points at the
same place as everything else: the app currently tells every reader nothing
leaves their device while making a third-party request. Two live licence issues
(§1.2) — the ODL attribution gap is a clear breach of a condition and trivially
fixed; the MOE/KiasuParents cut-off reproduction is a real question that
deserves either written permission or a lawyer's read. `SAFEGUARDS.md` §7's last
unchecked item is exactly that review, and it should stay unchecked until it
happens.

---

## 5. Remediation checklist

**Blockers**

- [ ] Remove the three Google Fonts lines from `web/index.html`; self-host WOFF2 if the typography matters
- [ ] Add a `<meta>` CSP to `web/index.html` so the guarantee survives GitHub Pages
- [ ] Add `google\.com/maps` to the CI third-party allowlist, with a comment
- [ ] Render the ODL attribution notice + licence hyperlink on `#/data` and in the footer
- [ ] Decide the `cutoff_2025` licensing question; reconcile `SAFEGUARDS.md` §3b with whatever you choose
- [ ] Fix the `moe-schoolfinder-cop-2025` `licence_name` and `url`; credit KiasuParents in-app
- [ ] `git init`; delete `ges_data.json` and the session PDF; gitignore `web/site/`; un-ignore `package-lock.json`; drop `playwright-core`
- [ ] Confirm the ODBI publication gate, or update the four documents that say it is closed

**Should fix**

- [ ] Get a Singapore-qualified review of §3 licensing and the disclaimer wording
- [ ] Move `robots.txt` / `sitemap.txt` to the deploy root; set `BASE` in the Pages job
- [ ] Resolve or explicitly skip the two known DOM failures so CI is green on day one
- [ ] Update `START_HERE.md`'s stale test counts
- [ ] Reword the `index.html:942` comment that would trip the superlative gate
- [ ] Either build the Tier B "Delete everything" control or scope the §2 claim
- [ ] Consider improving route coverage for the 33 thin outcomes

**Before pushing**

- [ ] Set the GitHub repo description to include the not-affiliated notice (§7 item 4)
- [ ] Verify CI is green on the first push — it will not be until §1.1 is fixed

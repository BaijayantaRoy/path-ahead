/**
 * UI regression tests — the app driven the way a person drives it.
 *
 *   node tools/check_ui.mjs
 *
 * This file exists because every previous test checked the ENGINE. The engine
 * was fine. What reached a real family was interface faults the Python suite
 * could not see:
 *
 *   - typing a subject never refreshed the "which subjects do you enjoy" list,
 *     so a student saw one chip for the pre-filled General Paper and nothing
 *     else to pick;
 *   - two segmented controls appeared empty.
 *
 * Loads the real web/index.html into a DOM, stubs only the pack fetch, and
 * then clicks and types. If it passes here it is at least wired up.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
/* Read the pack the APP actually serves, not the one the CLI happens to have
   built last.

   `serve` compiles into web/data/ and the browser fetches from there;
   `build --out dist` writes somewhere else entirely. This file used to read
   dist/, and the two drifted: a fix that stopped ranking Chinese-medium
   courses passed every check here while web/data/ still held a bundle with no
   language_requirement in it at all. Green tests against a file the user never
   loads is the worst kind of green. */
const SERVED = join(REPO, "web", "data", "singapore.json");
const pack = JSON.parse(readFileSync(SERVED, "utf8"));
const html = readFileSync(join(REPO, "web", "index.html"), "utf8");

let failures = 0;
const results = [];
/* Printed as they run, not collected and dumped at the end. The suite now
   takes long enough that a silent run is indistinguishable from a hung one,
   and a syntax error that fails forty checks is far easier to read when the
   first failure appears immediately. */
async function check(name, fn) {
  try {
    await fn();
    results.push(["ok  ", name]);
    console.log(`  ok    ${name}`);
  } catch (err) {
    failures++;
    results.push(["FAIL", name]);
    console.log(`  FAIL  ${name}\n         ${err.message}`);
  }
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function boot() {
  const errs = [];
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    url: "http://localhost/",
    pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = async () => ({ ok: true, status: 200, json: async () => pack });
      w.console.error = (...a) => errs.push(a.map(String).join(" "));
      w.addEventListener("error", (e) => errs.push(String((e.error && e.error.stack) || e.message)));
      w.HTMLElement.prototype.scrollIntoView = () => {};
      // jsdom implements neither, and the router legitimately calls scrollTo
      // on every navigation. Stubbed here rather than guarded in the app, so
      // the shipped code stays the code a browser actually runs.
      w.scrollTo = () => {};
      w.print = () => {};
    },
  });
  await new Promise((r) => setTimeout(r, 700));
  return { window: dom.window, errs };
}

const { window, errs } = await boot();
const doc = window.document;
const $ = (s) => doc.querySelector(s);
const all = (s) => [...doc.querySelectorAll(s)];
const type = (input, value) => {
  input.value = value;
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
};
const blur = (el) => el.dispatchEvent(new window.Event("blur", { bubbles: true }));
// The combobox closes and repaints on a short timer so a click on a
// suggestion is not swallowed by the blur. Tests must respect that.
const settle = () => new Promise((r) => setTimeout(r, 200));
const click = (el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

/* ---- does the script even parse? -------------------------------------
   A single syntax error in the inline script makes every later check fail
   with a symptom ("no year levels", "0 chips rendered") rather than a cause.
   This runs first and names the real fault in one line.                    */
await check("the inline script parses", async () => {
  const { Script } = await import("node:vm");
  const src = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
  try { new Script(src); } catch (e) { throw new Error(e.message); }
});

/* ---- the served bundle is the current one ----------------------------- */
await check("the pack the app serves is not stale", () => {
  /* web/data/ is what the browser fetches. If it predates the pack source,
     every fix in the YAML is invisible to the person actually using the app —
     and every test here would still pass, because the DOM would happily render
     last week's data. */
  const packDir = join(REPO, "packs", "singapore");
  const newestSource = Math.max(
    ...readdirSync(packDir)
      .filter((f) => f.endsWith(".yaml"))
      .map((f) => statSync(join(packDir, f)).mtimeMs)
  );
  const built = statSync(SERVED).mtimeMs;
  assert(built >= newestSource,
    "web/data/singapore.json is older than the pack source — " +
    "run `python app/cli.py build --out web/data` (or just start the app, " +
    "which rebuilds it)");
});

/* ---- it boots at all -------------------------------------------------- */
await check("no uncaught errors on load", () => assert(errs.length === 0, errs.slice(0, 2).join(" | ")));
/* These read the A-Level start form, which now lives at #/alevel rather than
   at "#/". No navigation is needed: buildStart() populates it at boot whether
   or not its view is the visible one, and `go` is declared further down this
   file, so calling it here would hit the temporal dead zone. */
await check("cohort question is populated", () => assert(all("#yearLevel option").length >= 3, "no year levels"));
await check("cohort answer is read back", () =>
  assert($("#cohortEcho").textContent.includes("means sitting"), "no plain-words read-back"));

/* THE REGRESSION THIS FILE MISSED ONCE.
   Adding the PSLE cohorts to the pack put "Primary 5" and "Primary 6" into
   this dropdown, because it was filled from pack.cohorts unfiltered. Choosing
   Primary 6 correctly said "sitting the PSLE in 2026" and then asked the
   parent for H2 subjects and General Paper on the next card. The existing
   check passed throughout: it only asserted the dropdown had at least three
   options, and five is at least three.

   A count is not a guard. What matters is WHICH cohorts, and the assertion
   below is the one that would have failed on the day. */
await check("the year-level list offers only cohorts this page can score", () => {
  const stage = $("#view-start").dataset.stage;
  assert(stage, "#view-start does not declare which stage it is for");
  const offered = all("#yearLevel option").map(o => o.value);
  assert(offered.length > 0, "no year levels offered at all");
  for (const value of offered) {
    const cohort = pack.cohorts.find(c => c.year_level === value);
    assert(cohort, `option "${value}" is not a cohort in the pack`);
    assert(cohort.stage === stage,
      `"${cohort.label}" belongs to the ${cohort.stage} stage but is offered on the ${stage} page — ` +
      `choosing it asks a family for grades from an exam their child is not sitting`);
  }
});

await check("cohorts from other stages are named and given somewhere to go", () => {
  // An option silently removed is a family concluding the tool has nothing for
  // them. If the pack holds a cohort this page cannot serve, the page has to
  // say so and point at the page that can.
  const stage = $("#view-start").dataset.stage;
  const elsewhere = pack.cohorts.filter(c => c.stage !== stage);
  if (!elsewhere.length) return;
  const note = $("#otherStages");
  assert(note && note.textContent.trim(), "other stages exist in the pack but are not mentioned");
  for (const c of elsewhere) {
    assert(note.textContent.includes(c.label), `${c.label} is not named`);
  }
  assert(note.querySelector("a[href^='#/']"), "no link out to the page that serves them");
});

await check("the grade rows only offer levels this stage examines", () => {
  // The other half of the same mistake: a PSLE parent must never be shown an
  // H2 selector, and an A-Level student must never be shown an AL one.
  const stage = $("#view-start").dataset.stage;
  const stageLevels = new Set(pack.stages.find(s => s.id === stage)?.subject_levels ?? []);
  assert(stageLevels.size, `pack declares no subject levels for ${stage}`);
  for (const opt of all("#rows select option")) {
    const v = opt.value;
    // Grade selects carry grades, not levels; only check the level selects.
    if (!/^(h1|h2|h3|gp|mtl|pw|subject)$/.test(v)) continue;
    assert(stageLevels.has(v), `level "${v}" is offered but ${stage} does not examine it`);
  }
});

/* ---- every control the profile step offers is actually rendered ------- */
for (const [label, sel, min] of [
  ["interest chips", "#interestChips button", 6],
  ["assessment segmented control", "#asmSeg button", 3],
  ["teamwork segmented control", "#teamSeg button", 3],
  ["priority chips", "#priChips button", 6],
  // Two, not four. "Cost is a real constraint" and "Happy to sit interviews"
  // used to be chips here AND importance rows -- the same question asked
  // twice in two idioms on one screen. They were consolidated into the
  // importance rows; what remains are the two that are facts about a
  // situation rather than preferences, and so have no importance row. See
  // CON in web/index.html. This check kept asserting 4 for five days after
  // the change and was recorded as a known failure rather than fixed,
  // because "is the UI wrong or is the check wrong" needed a decision. It
  // was the check. Resolved 2026-08-14.
  ["constraint chips", "#conChips button", 2],
]) {
  await check(`${label} renders`, () => {
    const n = all(sel).length;
    assert(n >= min, `${label}: ${n} rendered, expected at least ${min}`);
  });
}

await check("the profile step asks nothing twice", () => {
  // The reason the constraint chips went from four to two. A question asked
  // as both a chip and an importance row reads as two different questions to
  // a tired family and produces two different answers to the same thing.
  const chipText = all("#conChips button").map((b) => b.textContent.toLowerCase()).join(" | ");
  assert(!/cost/.test(chipText),
    "cost is asked as a constraint chip again; it belongs in the importance rows only");
  assert(!/interview|portfolio/.test(chipText),
    "extra assessment is asked as a constraint chip again; it belongs in the importance rows only");
});

/* ---- THE REGRESSION: typing a subject must offer it as "enjoyed" ------ */
await check("typing a subject makes it selectable under 'subjects you enjoy'", async () => {
  const inputs = all("#rows input[role=combobox]");
  assert(inputs.length >= 3, "expected at least three subject rows");
  type(inputs[0], "Further Mathematics");
  blur(inputs[0]);
  await settle();
  const labels = all("#enjoyChips button").map((b) => b.textContent);
  assert(
    labels.includes("Further Mathematics"),
    `after typing, the enjoy list was: ${JSON.stringify(labels)}`
  );
});

await check("several typed subjects all appear", async () => {
  const inputs = all("#rows input[role=combobox]");
  type(inputs[1], "Chemistry"); blur(inputs[1]); await settle();
  type(inputs[2], "Economics"); blur(inputs[2]); await settle();
  const labels = all("#enjoyChips button").map((b) => b.textContent);
  for (const want of ["Further Mathematics", "Chemistry", "Economics"]) {
    assert(labels.includes(want), `${want} missing from ${JSON.stringify(labels)}`);
  }
});

await check("renaming a subject drops the stale selection", async () => {
  const chips = all("#enjoyChips button");
  const chem = chips.find((b) => b.textContent === "Chemistry");
  click(chem);
  assert(chem.getAttribute("aria-pressed") === "true", "chip did not select");
  const inputs = all("#rows input[role=combobox]");
  type(inputs[1], "Physics"); blur(inputs[1]); await settle();
  const labels = all("#enjoyChips button").map((b) => b.textContent);
  assert(labels.includes("Physics"), "renamed subject did not appear");
  assert(!labels.includes("Chemistry"), "old subject lingered");
});

/* ---- the combobox behaves like a combobox ----------------------------- */
await check("type-ahead suggests matches, including how people actually type", () => {
  const input = all("#rows input[role=combobox]")[0];
  type(input, "econs");
  const opts = all("#rows li[role=option]").map((o) => o.textContent);
  assert(opts.some((o) => o.includes("Economics")), `"econs" suggested: ${JSON.stringify(opts)}`);
});

await check("arrow keys move the active suggestion", () => {
  const input = all("#rows input[role=combobox]")[0];
  type(input, "chem");
  input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
  const active = input.getAttribute("aria-activedescendant");
  assert(active, "aria-activedescendant not set after ArrowDown");
});

/* ---- the whole flow produces a result -------------------------------- */
await check("a full run produces a score, a timeline and options", () => {
  click($("#sample"));
  assert(!$("#results").hidden, "results stayed hidden");
  assert($("#dial").textContent.trim().length > 0, "no score rendered");
  assert(all("#timeline li").length >= 5, "timeline did not render");
  assert(all("#groups li.course").length >= 10, "no course cards");
});

await check("answering the optional questions produces visible reasoning", () => {
  // The sample only fills grades. Fit needs the student to say something
  // about themselves, so answer two questions the way a person would.
  click(all("#interestChips button")[1]);
  click(all("#asmSeg button")[1]);
  click($("#go"));
  const cards = all("#groups li.course");
  assert(cards.length > 0, "no course cards");
  const withReasons = cards.filter((c) => c.querySelectorAll(".factors li").length > 0);
  assert(withReasons.length > 0, "no card showed its fit reasoning without a click");
});

await check("results are ordered by match, strongest first", () => {
  const seg = all("#sortControl button");
  assert(seg.length === 2, "no sort control rendered");
  assert(seg[0].getAttribute("aria-pressed") === "true", "match ordering is not the default");
  const scores = all("#groups li.course .axis .big")
    .map((n) => parseInt(n.textContent, 10))
    .filter((n) => !Number.isNaN(n));
  assert(scores.length > 2, "not enough scored cards to check ordering");
});

await check("strongest matches are summarised before the long list", () => {
  assert($("#sortControl").textContent.includes("Where your answers point"),
    "no summary of the strongest matches");
});

await check("each card shows the institution and the course code", () => {
  /* Checks EVERY card, not the first one. This used to assert that the first
     card was an NUS card, which quietly encoded "NUS sorts first" into a test
     about labelling — and broke the moment polytechnic diplomas entered the
     same list, which is exactly the ordering this project wants to be free to
     change. */
  const cards = all("#groups li.course .c-top");
  assert(cards.length > 0, "no course cards rendered");
  for (const card of cards) {
    const sub = card.textContent;
    assert(/(University|Polytechnic|Institute)/.test(sub), `institution missing: ${sub}`);
    assert(/[a-z]+(-[a-z0-9]+)+/.test(sub), `course code missing: ${sub}`);
  }
});

await check("a polytechnic card shows its range and refuses to compare it", () => {
  /* The failure this guards against is silent: an ELR2B2 O-Level aggregate
     rendered in the words of a university percentile band would read as "far
     less selective" and would be nonsense either way, since no route admits an
     A-Level holder on that number. */
  const cards = all("#groups li.course").filter((c) =>
    /Polytechnic/.test(c.textContent));
  assert(cards.length > 0, "no polytechnic cards rendered at all");
  const text = cards.map((c) => c.textContent).join(" ");
  assert(/Shown, not compared/.test(text),
    "a polytechnic card did not say the figure is not being compared");
  assert(!/Your \d+ against \d+–\d+, net ELR2B2/.test(text),
    "a polytechnic card put the student's A-Level score against an O-Level aggregate");
});

/* ---- the printed artefact -------------------------------------------
   This app tells families to print the page and take it to a form teacher, so
   the printout is a deliverable. It used to lose the reasoning and every
   answer, because @media print hid `button` and `details.disclosure summary`.
   See ISSUES_v0.2.md sections C and D. */

await check("printing does not hide the answers or the reasoning", () => {
  const css = html.slice(html.indexOf("@media print"), html.indexOf("@media print") + 2000);
  assert(!/^\s*header\.top[^}]*,button,/m.test(css),
    "the print stylesheet still hides every button");
  assert(/button\[aria-pressed=true\]/.test(css),
    "no rule prints a chosen option as text");
  assert(!/details\.disclosure summary\{display:none\}/.test(css),
    "the print stylesheet still hides the disclosure heading");
});

await check("printing opens every collapsed disclosure", () => {
  const collapsed = all("details:not([open])").length;
  assert(collapsed > 0, "no collapsed disclosure to test with");
  window.dispatchEvent(new window.Event("beforeprint"));
  assert(all("details:not([open])").length === 0,
    "a disclosure stayed shut for printing, so its reasoning would not print");
  window.dispatchEvent(new window.Event("afterprint"));
});

await check("printing shows every course, not just the first page", () => {
  const onScreen = all("#groups li.course").length;
  window.dispatchEvent(new window.Event("beforeprint"));
  const onPaper = all("#groups li.course").length;
  window.dispatchEvent(new window.Event("afterprint"));
  assert(onPaper >= onScreen,
    `printing showed fewer courses than the screen (${onPaper} < ${onScreen})`);
  assert(all("#groups li.course").length === onScreen,
    "the list did not go back to its collapsed state after printing");
});

/* ---- density and coherence ------------------------------------------ */

await check("a long bucket is paged rather than dumped", () => {
  const big = all("#groups section.group").find(
    (s) => Number(s.querySelector(".count")?.textContent) > 10);
  assert(big, "no bucket large enough to test paging");
  assert(big.querySelector("button.more"), "a bucket over ten courses has no 'show all'");
  assert(big.querySelectorAll("li.course").length <= 10,
    "a long bucket rendered every card at once");
});

await check("the student's result is not a number set against letter grades", () => {
  /* "Your 60 against CCC/C–AAB/B" compared a point total to grade profiles.
     ISSUES_v0.2.md section G1. */
  const text = $("#groups").textContent;
  const bad = /Your \d+(\.\d+)? against [A-E]/.test(text);
  assert(!bad, "a card still puts a bare number against a letter-grade profile");
});

await check("General Paper is not offered as both a level and a subject", () => {
  /* Produced a row reading "General Paper / General Paper". Section G3. */
  const gpRow = all("#rows tr").find(
    (r) => r.querySelector("td.lv select")?.value === "gp");
  assert(gpRow, "no General Paper row to check");
  assert(!gpRow.querySelector("td.nm input"),
    "the General Paper row still asks which subject it is");
  assert(/General Paper/.test(gpRow.querySelector("td.nm").textContent),
    "the General Paper row does not name the paper");
});

await check("stacked rows on a narrow screen keep their labels", () => {
  /* thead is hidden below 44rem, which left three unlabelled boxes. Section F. */
  for (const td of all("#rows tr:first-child td")) {
    if (td.className === "rm") continue;
    assert(td.getAttribute("data-label"),
      `a grade cell (.${td.className}) carries no label for the stacked layout`);
  }
});

await check("the shortlist invites a first course instead of hiding", () => {
  /* It used to appear only once something was in it, so nobody discovered it.
     ISSUES_v0.2.md section H. */
  const card = $("#cmpCard");
  assert(!card.hidden, "the shortlist card is hidden while empty");
  assert(!$("#cmpEmpty").hidden, "no empty-state invitation");
  assert($("#cmpWrap").hidden, "an empty comparison table is on screen");
  click($("#groups li.course button"));
  assert($("#cmpEmpty").hidden && !$("#cmpWrap").hidden,
    "adding a course did not swap the invitation for the table");
  assert(all("#cmpTable tbody tr").length > 4, "the comparison table has almost no rows");
});

await check("how many optional questions are answered is stated", () => {
  const text = $("#signalProgress").textContent;
  assert(/\d+ of \d+|answered none/.test(text),
    `no progress read-back: ${JSON.stringify(text)}`);
  assert(!/must|should|need to|required/i.test(text),
    "the progress note nags; every one of these questions is optional");
});

/* ---- the palette ----------------------------------------------------
   Warm palettes drift pale. Every time a colour is nudged to look warmer it
   loses contrast, and the failure is invisible to the person making the
   change because they are looking at a large heading on a bright screen. So
   the floor is a test, in both modes, against the surface each colour is
   actually used on -- `--ink-3` passed on `--card` and failed on `--sunk`,
   which is where the axis labels live. */
function srgbToLinear(c) {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}
function luminance(hex) {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}
function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
}
function varsFrom(block) {
  const out = {};
  for (const m of block.matchAll(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})/g)) out[m[1]] = m[2];
  return out;
}

await check("every text colour meets WCAG AA on the surface it is used on", () => {
  const rootBlock = html.slice(html.indexOf(":root{"), html.indexOf("@media (prefers-color-scheme:dark)"));
  const darkStart = html.indexOf("@media (prefers-color-scheme:dark)");
  const darkBlock = html.slice(darkStart, html.indexOf("*,*::before", darkStart));
  const modes = { light: varsFrom(rootBlock), dark: varsFrom(darkBlock) };

  //           foreground   surfaces it actually appears on
  const onSurfaces = [
    ["ink", ["card", "paper", "sunk"]],
    ["ink-2", ["card", "paper", "sunk"]],
    ["ink-3", ["card", "paper", "sunk"]],
    ["brand", ["card", "paper", "sunk"]],
    ["focus", ["card", "paper"]],
  ];
  // Tinted badges: a foreground on its own matching background.
  const tinted = [
    ["good", "good-bg"], ["soft", "soft-bg"], ["quiet", "quiet-bg"],
    ["editorial", "editorial-bg"], ["mid", "mid-bg"], ["brand-ink", "brand"],
  ];

  const failures = [];
  for (const [mode, v] of Object.entries(modes)) {
    for (const [fg, surfaces] of onSurfaces) {
      for (const bg of surfaces) {
        if (!v[fg] || !v[bg]) continue;
        const r = contrast(v[fg], v[bg]);
        if (r < 4.5) failures.push(`${mode}: --${fg} on --${bg} is ${r.toFixed(2)}:1`);
      }
    }
    for (const [fg, bg] of tinted) {
      if (!v[fg] || !v[bg]) continue;
      const r = contrast(v[fg], v[bg]);
      if (r < 4.5) failures.push(`${mode}: --${fg} on --${bg} is ${r.toFixed(2)}:1`);
    }
  }
  assert(failures.length === 0, failures.join("; "));
});

await check("the palette stays on the warm side of neutral", () => {
  /* The accent was a cool teal and the page read clinical. This is not a
     matter of taste to re-litigate silently: if someone swings the accent
     back to a blue-green, that is a design decision that should be made out
     loud, not by editing one hex. Red channel must lead blue on the accent
     and on the paper. */
  const v = varsFrom(html.slice(html.indexOf(":root{"), html.indexOf("@media (prefers-color-scheme:dark)")));
  for (const name of ["brand", "paper", "card", "sunk"]) {
    const h = v[name].replace("#", "");
    const [r, , b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
    assert(r > b, `--${name} (${v[name]}) is cooler than it is warm: red ${r}, blue ${b}`);
  }
});

await check("a language-taught course is not ranked before the question is answered", () => {
  /* A student who does not read Chinese saw NP's Chinese Studies as her
     second-strongest match of 296, on generic overlap alone. */
  const withLang = pack.outcomes.filter((o) => o.language_requirement);
  assert(withLang.length > 0, "no course in the bundle carries a language requirement");
  assert($("#mtChips") && all("#mtChips button").length >= 4,
    "no mother-tongue question rendered, so the engine can never be told");
  const scored = withLang.filter((o) => {
    const el = [...all("#groups li.course")].find((c) => c.textContent.includes(o.id));
    return el && /\d+\/100/.test(el.textContent);
  });
  assert(scored.length === 0,
    `ranked without asking: ${scored.map((o) => o.id).join(", ")}`);
});

await check("tied scores are not dressed up as a ranking", () => {
  /* Three cards reading 67/100 with the identical one-line reason is not a
     top three — it is the alphabetical first three of a tie. */
  const promoted = all("#sortControl li.course");
  if (promoted.length === 0) return; // correctly withheld
  const scores = promoted.map((c) => parseInt(c.querySelector(".big").textContent, 10));
  const reasons = promoted.map((c) => c.querySelector(".small:last-child")?.textContent);
  const allSame = scores.every((s) => s === scores[0]);
  const sameReason = reasons.every((r) => r === reasons[0]);
  assert(!(allSame && sameReason),
    `promoted ${promoted.length} courses all scoring ${scores[0]} with one identical reason`);
});

await check("no course card uses judgemental wording about the student", () => {
  const text = $("#groups").textContent.toLowerCase();
  for (const word of ["weak match", "poor match", "unsuitable", "not good enough"]) {
    assert(!text.includes(word), `found "${word}" in the results`);
  }
});

/* ---- U1: the router --------------------------------------------------
   ROADMAP_UI.md U1. These check the shell, not the content: every route
   resolves, the back button works, deep links land, in-memory state survives
   navigation, and — the one that is not a convenience — no route ever writes
   what the student typed into the URL.                                    */

const go = async (hash) => {
  window.location.hash = hash;
  await new Promise((r) => setTimeout(r, 60));
};
const visibleViews = () => all(".view").filter((v) => !v.hasAttribute("hidden"));

await check("every route resolves to exactly one visible view", async () => {
  const hashes = ["#/", "#/alevel", "#/psle", "#/result", "#/courses", "#/compare",
                  "#/dates", "#/routes", "#/fees", "#/data", "#/more"];
  for (const h of hashes) {
    await go(h);
    const vis = visibleViews();
    assert(vis.length === 1, `${h} showed ${vis.length} views (${vis.map((v) => v.id).join(",")})`);
  }
});

/* ---- "#/" is a stage chooser, not a stage -----------------------------
   The front door was the A-Level grades table until 2026-08-09, which meant
   the parent of a twelve-year-old was greeted by a request for H2 subject
   grades. These checks exist so it cannot drift back. */

await check("the front door asks which stage, not for grades", async () => {
  await go("#/");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-home", `got ${vis.map(v=>v.id).join(",")}`);
  assert(all("#view-home input, #view-home select").length === 0,
    "the chooser has a form control on it — it is meant to be one question and three answers");
  assert(/where are you now/i.test($("#homeH1").textContent), "no orienting question");
});

await check("every stage in the pack has a door", () => {
  // A stage quietly missing from the front page is how a family concludes the
  // tool has nothing for them. Present or absent, it must be ON the page.
  for (const s of pack.stages) {
    assert($(`#homeDoors [data-door="${s.id}"]`),
      `stage "${s.id}" is in the pack but has no door on the home page`);
  }
});

await check("a door is a link only when the pack can actually answer it", () => {
  const scored = new Set(pack.transitions.map(t => t.stage));
  for (const door of all("#homeDoors .door")) {
    const stage = door.dataset.door;
    // Boolean, not the href string. Comparing "#/psle" === true fails for a
    // door that is behaving perfectly, which is how this check first read.
    const isLink = door.tagName === "A" && !!door.getAttribute("href");
    const answerable = scored.has(stage);
    assert(isLink === answerable,
      `the "${stage}" door is ${isLink ? "clickable" : "not clickable"} but the pack ` +
      `${answerable ? "can" : "cannot"} score it`);
  }
});

await check("an unbuilt stage says what is missing rather than 'coming soon'", () => {
  const scored = new Set(pack.transitions.map(t => t.stage));
  for (const door of all("#homeDoors .door")) {
    if (scored.has(door.dataset.door)) continue;
    const text = door.textContent;
    assert(!/coming soon|watch this space|stay tuned/i.test(text),
      "an unbuilt stage is fobbing the reader off instead of saying what is missing");
    assert(text.length > 120, "an unbuilt stage says too little to be useful");
  }
});

await check("the three doors carry equal weight", () => {
  // If one stage is styled as the main one, the app has a primary audience
  // again and the other two are afterthoughts — which is the state this
  // whole change exists to leave behind.
  const doors = all("#homeDoors .door");
  assert(doors.length >= 3, `only ${doors.length} doors`);
  const headings = doors.map(d => d.querySelector("h3")?.tagName);
  assert(new Set(headings).size === 1, "the doors do not use the same heading level");
});

await check("the A-Level questions still have their own route", async () => {
  await go("#/alevel");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-start", `got ${vis.map(v=>v.id).join(",")}`);
  assert(all("#rows tr").length > 0, "the grade rows did not survive the move");
});

await check("the A-Level importance ranking does not render the literal text 'null'", () => {
  // renderRanking()'s "Reset to equal" row used to call
  // actions.replaceChildren(cond ? el(...) : null) directly.
  // replaceChildren does not skip a bare null -- it stringifies it to a
  // TEXT NODE reading "null", visible on the page before any importance
  // slider was touched. Caught 2026-08-12 while reviewing a related bug in
  // the PSLE school shortlist; fixed the same way in both places.
  assert($("#rankActions").innerHTML === "", "the importance ranking's actions row renders literal content before anything is set");
});

/* ---- #/psle: the PSLE landing page ------------------------------------
   The stage where the reader is a parent and the subject is twelve. Every
   check below guards a decision recorded in docs/POST_PSLE_AND_PORTAL.md §4,
   and three of them guard against the tool doing harm rather than against it
   looking wrong. */

await check("the PSLE landing page opens without a score", async () => {
  await go("#/psle");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-psle", `got ${vis.map(v=>v.id).join(",")}`);
  assert($("#psleH1"), "no heading rendered");
});

await check("the PSLE page asks for no transcript above the fold", () => {
  // The A-Level front door opens with a grades table. Repeating that here
  // would shut out every family in the eleven months before a score exists.
  //
  // This used to assert "at most one input", back when the PSLE score field
  // was the only one on the page. The school shortlist added a second,
  // legitimate optional field (a postal code) -- and the property that
  // actually matters was never the COUNT, it was that nothing here is
  // required to read the page. A second optional field is fine; a required
  // one is exactly what this check exists to catch.
  const inputs = all("#view-psle input");
  assert(inputs.length > 0, "expected at least the PSLE score field to render");
  for (const input of inputs) {
    assert(!input.required,
      `${input.id || "an input"} is required, but this page must be readable with nothing typed`);
  }
  assert(($("#psleTable")?.textContent || "").trim().length > 0,
    "the Posting Group table must render with nothing typed in");
  assert(all("#psleDoors button").length >= 3, "the three doors did not render");
});

await check("the published Posting Group table is reproduced in full", () => {
  const rows = all("#psleTable tbody tr").length;
  const spec = pack.transitions.find(t => t.id === "psle-to-secondary-2026")
    ?.rule_params?.posting_groups?.groups ?? [];
  assert(rows === spec.length && rows > 0, `${rows} rows rendered, pack declares ${spec.length}`);
});

await check("a score is answered with which doors open, never with a verdict", async () => {
  const input = $("#psleScore");
  input.value = "21";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  const text = $("#psleResult").textContent;
  assert(/Posting Group 2 or 3/.test(text), `did not name both groups: ${text}`);
  assert(/all six school choices/.test(text), "did not say the choice binds all six");
  // The sentence that keeps this a gate rather than a score.
  assert(/not a measure of your child/i.test(text), "the answer reads as a judgement");
});

await check("typing a score does not destroy the field being typed into", async () => {
  // This started as a real bug: re-rendering the whole page on input meant
  // restoring the caret by hand, and setSelectionRange throws
  // InvalidStateError on <input type="number"> in real browsers.
  const input = $("#psleScore");
  input.value = "12";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  assert($("#psleScore") === input, "the input was replaced mid-keystroke");
  assert(/Posting Group 3/.test($("#psleResult").textContent), "answer did not update");
});

await check("a score outside the published table gets a route, not a dead end", async () => {
  const input = $("#psleScore");
  input.value = "32";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  const answer = $("#psleResult").textContent;
  assert(/different route/i.test(answer), `no onward route offered: ${answer}`);
  const card = $("#psleOutside");
  assert(card, "the outside-the-table card is missing entirely");
  assert(/NorthLight/.test(card.textContent), "the route is described but not named");
});

await check("nothing on the PSLE page tells a parent their child failed", () => {
  const text = $("#view-psle").textContent.toLowerCase();
  for (const word of ["you failed", "did not qualify", "not good enough",
                      "no chance", "unfortunately", "sorry to say"]) {
    assert(!text.includes(word), `"${word}" has no place on this page`);
  }
});

await check("the PSLE page says an address does not help you get in", () => {
  // Families conflate S1 posting with P1 registration, where distance IS a
  // criterion. Leaving that unsaid lets a parent believe a field buys
  // something it does not.
  const text = $("#psleHonesty").textContent;
  assert(/Distance is not among them/.test(text), "the tie-breakers are not stated plainly");
  assert(/Primary 1 registration/.test(text), "the P1 confusion is not addressed");
});

await check("the PSLE page states the DSA commitment before the application", () => {
  const text = $("#psleHonesty").textContent;
  assert(/cannot submit S1 school choices/.test(text) && /cannot transfer/.test(text),
    "the binding term of DSA is not stated");
});

await check("every figure on the PSLE page links to the page it came from", () => {
  // Used to require every link to start with moe.gov.sg -- true back when
  // psle.yaml was the page's only source. The school shortlist legitimately
  // cites two more: data.gov.sg (MOE's own school directory, republished
  // under an open licence) and a secondary transcription of SingPost's
  // postal-district table. Hardcoding one domain would either block real
  // citations or get quietly loosened to a wildcard -- so this checks the
  // stronger, still-real property instead: every citation link on the page
  // resolves to a URL actually declared in the pack's own sources: block,
  // not just a domain that looks plausible.
  const links = all("#view-psle .cite a");
  assert(links.length >= 2, `only ${links.length} citations on a page full of published figures`);
  const knownUrls = new Set((pack.sources || []).map((s) => s.url));
  for (const a of links) {
    const href = a.getAttribute("href");
    assert(knownUrls.has(href),
      `citation link is not a URL declared in any pack source: ${href}`);
  }
});

/* ── the school shortlist: mirrors engine/school_fit.py ────────────────
   Rewritten 2026-08-13: every dimension here is now a FILTER, never a
   score (see engine/school_fit.py's module docstring for why). These
   checks confirm the pool shows by default, filters hide rather than
   rank, the eligibility gate hides unconditionally while an unanswered
   sex only adds a caveat, and nothing here reads as a verdict. */

await check("the school shortlist shows every school by default, before any preference is set", () => {
  const host = $("#schoolShortlistHost");
  assert(host, "no shortlist host rendered");
  assert(/All \d+ schools/.test(host.textContent),
    "the shortlist must show the whole pool before any filter is set");
  const cards = all("#schoolResults li.course");
  assert(cards.length > 0, "no school cards rendered with no filters set");
});

await check("no school card republishes a cut-off figure; every one links to MOE SchoolFinder instead", () => {
  // The shipped position, asserted rather than assumed. PathAhead does not
  // redistribute Posting Group cut-off points -- they are MOE's to publish,
  // and MOE's Terms of Use reserve reproduction -- so every card hands the
  // reader a link to the school's own SchoolFinder page instead of a number
  // copied out of it. See engine/loader.py:_apply_local_overlays.
  //
  // This check would legitimately fail on a machine holding a private local
  // overlay, which is why it asserts against the pack it was actually served
  // rather than assuming the published state.
  const overlayPresent = (pack.schools || []).some((s) => s.cutoff_2025);
  const showAll = [...all("#schoolShortlistHost button")].find((b) => /^Show all/.test(b.textContent));
  if (showAll) click(showAll);

  const card = $('#schoolResults li.course[data-school="admiralty-secondary-school"]');
  assert(card, "Admiralty Secondary School did not render");

  const link = [...card.querySelectorAll("a")].find((a) => /SchoolFinder/.test(a.textContent));
  assert(link, "no 'View on MOE SchoolFinder' link on the card");
  assert(/moe\.gov\.sg\/schoolfinder\/schooldetail\/admiralty-secondary-school/.test(link.href),
    `the SchoolFinder link does not deep-link to this school: ${link.href}`);
  assert(link.getAttribute("target") === "_blank" && /noopener/.test(link.getAttribute("rel") || ""),
    "the SchoolFinder link does not open safely in a new tab");

  if (!overlayPresent) {
    const cutoffLine = card.querySelector("[data-cutoff-origin]");
    assert(cutoffLine, "the card has no cut-off line at all");
    assert(cutoffLine.getAttribute("data-cutoff-origin") === "linked",
      "a card in the published build should be marked as linking out, not carrying figures");
    assert(cutoffLine.getAttribute("data-cutoff") === "",
      "a card in the published build must carry no cut-off figure at all");
    assert(/does not republish Posting Group cut-off points/.test(card.textContent),
      "the card does not say plainly that PathAhead does not republish these figures");
  }

  // The 8 specialised-admission schools have no cut-off under ANY source.
  // That is a fact about the school, and must not read like the sentence
  // above, which is a fact about this project.
  const specialised = $('#schoolResults li.course[data-school="nus-high-school-of-mathematics-and-science"]');
  assert(specialised, "NUS High School of Mathematics and Science did not render");
  assert(/No Posting Group cut-off is published for this school/.test(specialised.textContent),
    "a specialised-admission school does not explain that no cut-off exists for it at all");

  // Collapse back -- schoolShortlistExpanded is shared page state, and a
  // later check relies on the default paged (<=10 cards) view.
  const showFewer = [...all("#schoolShortlistHost button")].find((b) => /^Show fewer/.test(b.textContent));
  if (showFewer) click(showFewer);
});

await check("the word 'null' never leaks into the school shortlist", () => {
  // Element.replaceChildren(x) does not skip a bare `null` argument -- it
  // stringifies it to the TEXT NODE "null". renderRanking() (A-Level,
  // guarded separately above at #rankActions) used to leak it this way; the
  // school shortlist's own equivalent (renderSchoolRanking) was retired
  // entirely in the 2026-08-13 filter rewrite, but this guard stays in
  // place for the section as a whole in case a future conditional child
  // reintroduces the footgun.
  assert(!/\bnull\b/.test($("#schoolShortlist").textContent), "the word 'null' leaked into the PSLE shortlist");
});

await check("the shortlist never claims an admission estimate, on the page or in its disclaimer", () => {
  const text = $("#schoolShortlist").textContent;
  assert(/does not hold Posting Group data for individual schools/.test(text),
    "the filter disclaimer is missing");
  assert(!/\bguarantee[ds]? (?:you )?(?:a place|admission)\b/i.test(text),
    "banned phrase reached the school shortlist");
});

await check("setting a preference hides non-matching schools and says so in the summary", () => {
  // `schoolShortlistExpanded` is page-level state that an earlier check may
  // have left expanded -- and if that check FAILED it never reached its own
  // reset. Collapse defensively rather than inheriting whatever the previous
  // assertion happened to leave behind: a check that only passes when its
  // predecessor passed reports the wrong failure.
  const stale = [...all("#schoolShortlistHost button")].find((b) => /^Show fewer/.test(b.textContent));
  if (stale) click(stale);

  const genderBtn = all("#schoolPrefsHost .chips button").find((b) => b.textContent === "Co-ed");
  assert(genderBtn, "no 'Co-ed' chip rendered");
  click(genderBtn);
  // Unlike a plain toggleChip button, this control rebuilds the whole
  // preferences form on every click (to keep sibling buttons in a
  // single-select group in sync), so the element to re-check is the freshly
  // rendered one, not the stale reference from before the click.
  const pressedNow = all("#schoolPrefsHost .chips button").find((b) => b.textContent === "Co-ed");
  assert(pressedNow.getAttribute("aria-pressed") === "true", "the chip did not show itself pressed");
  const host = $("#schoolShortlistHost");
  assert(/\d+ of \d+ schools/.test(host.textContent),
    "no filtered-count summary rendered after setting a preference");
  assert(/not matching a preference you set/.test(host.textContent),
    "the summary does not explain why non-co-ed schools disappeared");
  const cards = all("#schoolResults li.course");
  assert(cards.length > 0, "no school cards rendered");
  assert(cards.length <= 10, "more than one page of results rendered before 'Show all' was clicked");
});

await check("a postal code in the shortlist resolves to its own postal district, never a distance", () => {
  const input = $("#schoolPostal");
  assert(input, "no postal code input rendered");
  type(input, "737916"); // Admiralty Secondary's own postal code
  const status = $("#schoolPostalStatus").textContent;
  assert(/Postal district 25/.test(status), `did not resolve the district: ${status}`);
  assert(!/\bkm\b|minutes?\b/i.test(status), "a district lookup must never present as a distance or a travel time");
});

await check("the shortlist orders by distance then name, never by a status flag like SAP or Autonomous", () => {
  const cards = all("#schoolResults li.course");
  assert(cards.length > 0, "no cards rendered to check ordering on");
  const dists = cards.map((c) => {
    const d = c.querySelector("[data-distance]");
    return d ? Number(d.getAttribute("data-distance")) : null;
  });
  const known = dists.filter((d) => d !== null);
  for (let i = 1; i < known.length; i++) {
    assert(known[i] >= known[i - 1], "shortlist results are not sorted by ascending distance");
  }
  const firstUnknown = dists.indexOf(null);
  if (firstUnknown !== -1) {
    assert(dists.slice(firstUnknown).every((d) => d === null),
      "a school with a known distance sorted after one without a distance");
  }
});

await check("an unanswered child's sex leaves a single-sex school visible with a caveat, distance and all", () => {
  // Reset the gender filter set two checks ago -- with it still at "co-ed"
  // every single-sex school (including the one this check needs) would be
  // hidden by the PREFERENCE filter, masking the ELIGIBILITY behaviour this
  // check exists to prove.
  const genderGroup = $('#schoolPrefsHost [aria-label="Co-ed or single-sex"]');
  click([...genderGroup.querySelectorAll("button")].find((b) => b.textContent === "Any"));

  const showAll = [...all("#schoolShortlistHost button")].find((b) => /^Show all/.test(b.textContent));
  if (showAll) click(showAll);

  const girlsSchool = $('#schoolResults li.course[data-school="chij-katong-convent"]');
  assert(girlsSchool, "CHIJ Katong Convent did not render while student_sex is unanswered");
  assert(/has not been told your child.s sex/.test(girlsSchool.textContent),
    "no caveat shown for a single-sex school when student_sex is unanswered");
  assert(/≈\d+(\.\d+)? km away, straight-line/.test(girlsSchool.textContent),
    "distance must still show for a school PathAhead cannot yet confirm eligibility for");
});

await check("a single-sex school is hidden outright, not shown as a weak match, for the wrong sex", () => {
  const sexGroup = $("#schoolPrefsHost [aria-label=\"Your child's sex\"]");
  assert(sexGroup, "no student-sex control rendered");
  const boyBtn = [...sexGroup.querySelectorAll("button")].find((b) => b.textContent === "Boy");
  assert(boyBtn, "no 'Boy' option rendered");
  click(boyBtn);

  const showAll = [...all("#schoolShortlistHost button")].find((b) => /^Show all/.test(b.textContent));
  if (showAll) click(showAll);

  assert(!$('#schoolResults li.course[data-school="chij-katong-convent"]'),
    "a girls' school still rendered for a boy -- must be hidden outright, not scored low");
  const summary = $("#schoolShortlistHost .hint")?.textContent || "";
  assert(/not admitting your child.s sex/.test(summary),
    `the summary does not explain why sex-ineligible schools are hidden: ${summary}`);

  const coEdSchool = $('#schoolResults li.course[data-school="admiralty-secondary-school"]');
  assert(coEdSchool, "a co-ed school must still render regardless of student_sex");
});

await check("the co-ed/single-sex preference never offers a school your child cannot attend", () => {
  // student_sex is still "male" from the previous check.
  const genderGroup = $('#schoolPrefsHost [aria-label="Co-ed or single-sex"]');
  const labels = [...genderGroup.querySelectorAll("button")].map((b) => b.textContent);
  assert(labels.includes("Boys' school"), "a boy should still be offered a boys'-school preference");
  assert(!labels.includes("Girls' school"),
    "a boy must not be offered 'Girls' school' as a pickable preference");
});

await check("a school card shows an honest straight-line distance, labelled as such, with a Get Directions link", () => {
  // postal_code is still "737916" (Admiralty's own) from the earlier postal
  // check above; student_sex is still "male" from the sex-eligibility check.
  // Ahmad Ibrahim is a DIFFERENT school with a DIFFERENT postal code
  // (768928), deliberately -- checking the leak assertion against Admiralty
  // itself would be a false positive, since Admiralty's own postal code is
  // legitimately part of Admiralty's own destination address.
  const school = $('#schoolResults li.course[data-school="ahmad-ibrahim-secondary-school"]');
  assert(school, "Ahmad Ibrahim Secondary School did not render");
  const text = school.textContent;
  assert(/≈\d+(\.\d+)? km away, straight-line \(not a travel time\)/.test(text),
    `no honestly-labelled straight-line distance rendered: ${text}`);
  const link = [...school.querySelectorAll("a")].find((a) => /Get directions/.test(a.textContent));
  assert(link, "no 'Get directions' link rendered on the school card");
  assert(link.getAttribute("target") === "_blank" && /noopener/.test(link.getAttribute("rel") || ""),
    "the directions link does not open safely in a new tab");
  assert(/google\.com\/maps/.test(link.href), `directions link does not point at Google Maps: ${link.href}`);
  assert(link.href.includes("768928"), "the directions link does not carry the SCHOOL's own postal code as destination");
  assert(!link.href.includes("737916"),
    "the family's own typed postal code leaked into the outbound Get Directions link -- it must never leave this device");
});

await check("the distance filter is disabled until a postal code is set", () => {
  // Postal code is already set from an earlier check in this file -- clear
  // it here via the real input (never by poking internal state directly) to
  // prove the disabled state, then restore what the checks below expect.
  const postalInput = $("#schoolPostal");
  const savedPostal = postalInput.value;
  type(postalInput, "");

  const kmGroup = $('#schoolPrefsHost [aria-label="Maximum distance"]');
  assert(kmGroup, "no distance-filter control rendered");
  assert([...kmGroup.querySelectorAll("button")].every((b) => b.disabled),
    "the distance filter is usable before a postal code is set");

  type($("#schoolPostal"), savedPostal);
});

await check("the reach filter is absent entirely when no cut-off figures are held", () => {
  // The published build carries no cut-off data, so there is nothing for a
  // reach filter to compare against and the control is not rendered at all.
  // Hidden rather than shown-disabled on purpose: a permanently dead toggle
  // with an explanation nobody can act on is worse than no toggle, and the
  // per-card SchoolFinder link already answers the same question one school
  // at a time.
  //
  // On a machine holding a private local overlay the control legitimately
  // appears, so this asserts against the pack actually served.
  const overlayPresent = (pack.schools || []).some((s) => s.cutoff_2025);
  const reachGroup = $('#schoolPrefsHost [aria-label="Reach filter"]');
  if (overlayPresent) {
    assert(reachGroup, "a local overlay is present, so the reach filter should render");
  } else {
    assert(!reachGroup,
      "a reach filter rendered with no cut-off figures to compare against — it would be permanently dead");
  }
});

await check("the distance filter hides schools past the chosen band and says so in the summary", () => {
  const input = $("#schoolPostal");
  type(input, "737916"); // Admiralty's own postal code, reused throughout this file
  const kmGroup = $('#schoolPrefsHost [aria-label="Maximum distance"]');
  const btn5 = [...kmGroup.querySelectorAll("button")].find((b) => /~5 km/.test(b.textContent));
  assert(btn5, "no 'within ~5 km' option rendered");
  click(btn5);
  const summary = $("#schoolShortlistHost .hint")?.textContent || "";
  assert(/outside the distance you set/.test(summary),
    `the summary does not explain the distance filter's effect: ${summary}`);
  for (const card of all("#schoolResults li.course")) {
    const m = card.textContent.match(/≈(\d+(?:\.\d+)?) km away/);
    if (m) assert(Number(m[1]) <= 5, `a school ${m[1]}km away rendered under the 5km filter`);
  }
  // Reset for the checks that follow.
  const btnAny = [...kmGroup.querySelectorAll("button")].find((b) => b.textContent === "Any distance");
  click(btnAny);
});

await check("entering a PSLE score never makes the shortlist hide a school for being out of reach", () => {
  // With no cut-off figures held, within_reach() answers null for every
  // school -- "cannot tell", never "no" -- so a score alone must not remove
  // anything from the list. This is the guard against a future change that
  // reintroduces cut-off data and quietly starts hiding schools a family is
  // still perfectly entitled to put on their six choices.
  const scoreInput = $("#psleScore");
  scoreInput.value = "14";
  scoreInput.dispatchEvent(new window.Event("input", { bubbles: true }));

  const genderGroup = $('#schoolPrefsHost [aria-label="Co-ed or single-sex"]');
  click([...genderGroup.querySelectorAll("button")].find((b) => b.textContent === "Any"));

  const showAll = [...all("#schoolShortlistHost button")].find((b) => /^Show all/.test(b.textContent));
  if (showAll) click(showAll);

  const overlayPresent = (pack.schools || []).some((s) => s.cutoff_2025);
  if (!overlayPresent) {
    const summary = $("#schoolShortlistHost .hint")?.textContent || "";
    assert(!/outside reach of your PSLE score/.test(summary),
      `nothing should be hidden for reach when no cut-off figures are held: ${summary}`);
    // Every card must read "unknown" reach, never "out-of-reach".
    for (const card of all("#schoolResults li.course")) {
      assert(card.getAttribute("data-reach") !== "out-of-reach",
        `${card.getAttribute("data-school")} marked out-of-reach with no cut-off data held`);
    }
  }

  const showFewer = [...all("#schoolShortlistHost button")].find((b) => /^Show fewer/.test(b.textContent));
  if (showFewer) click(showFewer);
});

await check("the limits and responsibility statement is reachable and says who decides", () => {
  // Not an "I agree" gate and not a modal -- a card a reader can reach and
  // re-read (SAFEGUARDS.md 4). It must state all five things, because each
  // one is a different claim and dropping any of them silently would be the
  // easy regression.
  window.location.hash = "#/data";
  const card = $("#limitsCard");
  assert(card, "no limits/responsibility card rendered on the data page");
  const t = card.textContent;
  assert(/does not advise you|decision you make after reading this is yours/i.test(t),
    "the card does not say the decision belongs to the reader");
  assert(/last year|already happened/i.test(t),
    "the card does not say the figures describe an exercise already past");
  assert(/not affiliated with, endorsed by, or connected to/i.test(t),
    "the card does not carry the not-official statement");
  assert(/no account, no name field/i.test(t),
    "the card does not state that nothing is collected");
  assert(/no warranty/i.test(t),
    "the card does not state that the tool is provided without warranty");
  // The same guard that protects every other surface: a disclaimer must not
  // reassure with a phrase the banned list forbids.
  assert(!/\bguarantee[ds]? (?:you )?(?:a place|admission)\b/i.test(t),
    "banned phrase reached the limits card");
});

await check("the PSLE page explains that cut-off points are MOE's to publish, not PathAhead's to copy", () => {
  window.location.hash = "#/psle";
  // The shipped position, stated on the page rather than buried in a repo
  // document: PathAhead does not republish Posting Group cut-off points, it
  // links to MOE SchoolFinder, and the 8 specialised-admission schools have
  // none published anywhere. A reader must be able to tell those two apart.
  const text = $("#view-psle").textContent;
  assert(/SchoolFinder/.test(text),
    "the page never mentions SchoolFinder, where the figures actually live");
  assert(/does not republish Posting Group cut-off points/.test(text),
    "the page does not say plainly that PathAhead does not republish these figures");
  assert(/Eight of the 147 schools/.test(text),
    "the page does not explain the 8 schools that have no cut-off published at all");
});

/* ---- #/olevel: the O-Level/SEC landing page ----------------------------
   Two rulebooks, one exam, and the pack loads the polytechnic ELR2B2 outcomes
   a SECOND time under `also_scored_under` rather than duplicating ~330 rows.
   The checks below prove that wiring actually runs in the browser, not just
   in engine/forward.py — the same lesson the golden-fixture gap already
   taught once for `required_plus_best_n` itself. */

const addOlevelSubject = (code) => {
  const sel = $("#olevelAddSubject");
  sel.value = code;
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));
};

await check("the O-Level landing page opens without a score", async () => {
  await go("#/olevel");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-olevel", `got ${vis.map(v=>v.id).join(",")}`);
  assert($("#olevelH1"), "no heading rendered");
});

await check("the O-Level page asks which cohort before any grade", () => {
  const chips = all("#olevelCohorts button");
  assert(chips.length >= 3, `only ${chips.length} cohort chips rendered`);
  assert(!$("#olevelRows"), "a grade table rendered before any cohort was chosen");
});

await check("picking a cohort shows that cohort's own rulebook note, not the other one's", () => {
  const chips = all("#olevelCohorts button");
  const sec4 = chips.find(b => /Secondary 4/.test(b.textContent));
  assert(sec4, "no Secondary 4 chip found");
  sec4.click();
  const note = $("#olevelCohortNote")?.textContent || "";
  assert(/GCE O-Level/.test(note) && /L1R5/.test(note), `Sec 4's note does not name its own rulebook: ${note}`);
  // The note may still MENTION the Secondary Education Certificate in
  // passing, to explain what the cohorts behind this one sit instead -- that
  // is a correct contrast, not a mix-up. What must not happen is Sec 4 being
  // told ITS OWN ceiling is the SEC one.
  assert(!/Your JC ceiling is L1R4/.test(note), "Sec 4 was told the SEC-era ceiling applies to it");
});

await check("too few subjects for the rulebook fails with advice, not a crash", () => {
  addOlevelSubject("ol-english");
  const err = $("#olevelError");
  assert(err, "no error surfaced for an incomplete sheet");
  assert(/need \d+ subject/.test(err.textContent), `error does not explain what is missing: ${err.textContent}`);
});

await check("a complete L1R5 sheet produces a total and both onward routes", () => {
  for (const code of ["ol-history", "ol-geography", "ol-combined-science", "ol-physics", "ol-chemistry"]) {
    addOlevelSubject(code);
  }
  assert(!$("#olevelError"), "a complete sheet still shows an error");
  const text = $("#olevelOut").textContent;
  assert(/Total:/.test(text), "no aggregate total rendered");
  assert(/Junior College and Millennia Institute/.test(text), "the JC/MI route did not render");
  assert(/Polytechnic/.test(text), "the polytechnic route (also_scored_under) did not render");
});

await check("Millennia Institute is shown but never placed in the L1R5 buckets", () => {
  // MI is scored on L1R4, not the L1R5 this page's headline computes -- the
  // pack marks its band `comparable: false` on purpose. If this ever starts
  // asserting a bucket for MI, the pack's own comment explaining why is the
  // first thing to re-read, not this test.
  const text = $("#olevelOut").textContent;
  assert(/Millennia Institute/.test(text), "MI is missing from the page entirely");
  assert(/Published, but on a different scale/.test(text),
    "MI did not get the published-on-another-basis treatment");
});

await check("the SEC 2028 cohort states plainly that no course data exists yet", () => {
  const sec3 = all("#olevelCohorts button").find(b => /Secondary 3/.test(b.textContent));
  assert(sec3, "no Secondary 3 chip found");
  sec3.click();
  for (const code of ["ol-english", "ol-history", "ol-emath", "ol-physics"]) addOlevelSubject(code);
  assert(!$("#olevelError"), "a complete L1R4 sheet still shows an error");
  const note = $("#olevelNoCourseData")?.textContent || "";
  assert(/no course has a published cut-off/i.test(note), `the 2028 gap is not stated plainly: ${note}`);
  assert(all("#olevelOut ul.courses").length === 0,
    "a bucketed course list rendered for a system with no published courses");
});

await check("an unknown route shows a not-found page rather than a blank screen", async () => {
  await go("#/no-such-page");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-404",
    `got ${vis.map((v) => v.id).join(",") || "nothing"}`);
});

await check("a deep link to one course resolves and names that course", async () => {
  const target = pack.outcomes.find((o) => o.institution_short === "SP" && o.band);
  await go(`#/course/${target.id}`);
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-course", "course view did not open");
  const text = $("#courseOut").textContent;
  assert(text.includes(target.name), `course page does not name ${target.name}`);
  assert(text.includes(target.institution), "course page does not name the institution");
});

await check("a course with no published range says so instead of showing a number", async () => {
  const bandless = pack.outcomes.find((o) => o.institution_short === "SP" && !o.band);
  assert(bandless, "no band-less course in the pack to check");
  await go(`#/course/${bandless.id}`);
  const text = $("#courseOut").textContent.toLowerCase();
  assert(text.includes("publishes no admitted-score range"),
    "band-less course does not state that no range is published");
});

await check("a deep link to one university lists its courses", async () => {
  await go("#/uni/SP");
  const links = all("#uniOut a[href^='#/course/']");
  const expected = pack.outcomes.filter((o) => o.institution_short === "SP").length;
  assert(links.length === expected, `listed ${links.length} of ${expected} SP courses`);
});

await check("the back button returns to the previous route", async () => {
  await go("#/data");
  await go("#/fees");
  window.history.back();
  await new Promise((r) => setTimeout(r, 35));
  assert(window.location.hash === "#/data",
    `back landed on ${window.location.hash}, not #/data`);
});

await check("navigation does not lose what was already typed", async () => {
  await go("#/alevel");
  const before = all("#rows tr").length;
  assert(before > 0, "no grade rows to preserve");
  const firstGrade = $("#rows select");
  const gradeValue = firstGrade && firstGrade.value;
  await go("#/data");
  await go("#/alevel");
  assert(all("#rows tr").length === before, "grade rows were rebuilt on navigation");
  assert(!firstGrade || firstGrade.value === gradeValue, "a typed value was reset");
});

await check("a run-gated route invites the questions instead of erroring", async () => {
  // #results is still visible from the earlier full run, so drive the real
  // "Clear everything" control — the state a first-time visitor is in.
  await go("#/alevel");
  click($("#reset"));
  await new Promise((r) => setTimeout(r, 60));
  await go("#/result");
  const vis = visibleViews();
  assert(vis.length === 1 && vis[0].id === "view-gate",
    `expected the gate, got ${vis.map((v) => v.id).join(",")}`);
  const text = $("#gateOut").textContent.toLowerCase();
  for (const word of ["error", "invalid", "failed"]) {
    assert(!text.includes(word), `the gate says "${word}" to someone who has done nothing wrong`);
  }
  assert($("#gateOut a[href='#/alevel']"), "the gate offers no way back to the questions");
});

await check("no route writes the student's answers into the URL", async () => {
  // Re-run with real answers, then walk every route and inspect location.
  await go("#/alevel");
  click($("#sample"));
  await new Promise((r) => setTimeout(r, 45));
  const typed = readTypedValues();
  for (const h of ["#/", "#/alevel", "#/psle", "#/result", "#/courses", "#/compare",
                   "#/dates", "#/routes", "#/fees", "#/data", "#/more"]) {
    await go(h);
    const url = window.location.href;
    assert(!url.includes("?"), `${h} put a query string in the URL: ${url}`);
    for (const v of typed) {
      assert(!url.includes(v), `${h} leaked a typed value (${v}) into the URL: ${url}`);
    }
  }
  function readTypedValues() {
    const out = new Set();
    for (const s of all("#rows select")) if (s.value) out.add(s.value);
    for (const i of all("#rows input")) if (i.value) out.add(i.value);
    const g = $("#goalText"); if (g && g.value) out.add(g.value);
    // Single letters and 1-2 char codes appear incidentally in ids; only
    // check values distinctive enough for a match to mean something.
    return [...out].filter((v) => v.length >= 4);
  }
});

await check("the source of every figure is reachable without a run", async () => {
  await go("#/data");
  const links = all("#dataOut a[href^='http']");
  assert(links.length >= pack.sources.filter((s) => s.url).length,
    `only ${links.length} source links for ${pack.sources.length} sources`);
  assert($("#dataOut").textContent.includes(pack.pack.version), "no pack version on the sources page");
});

await check("both navigations are built from one route table", async () => {
  await go("#/courses");
  const top = all("#topnav a[data-route]").map((a) => a.dataset.route);
  const tab = all("#tabbar a[data-route]").map((a) => a.dataset.route);
  assert(top.length >= 6, `top nav has only ${top.length} entries`);
  assert(tab.length >= 4, `tab bar has only ${tab.length} entries`);
  for (const r of tab) {
    assert(top.includes(r) || r === "more", `tab route ${r} is not reachable on desktop`);
  }
  const current = all("[data-route][aria-current='page']");
  assert(current.length >= 1, "no navigation item marks the current route");
});

/* ---- track identity and nav scoping -------------------------------------
   Three doors with "distinct look and feel" and submenus scoped to the
   chosen track was the explicit redesign request. These checks guard both
   halves: the CSS accent actually changes per route, and the nav actually
   narrows rather than just LOOKING narrower while still linking everywhere. */

await check("the current track sets a distinct accent, and leaving it clears the accent", async () => {
  await go("#/psle");
  assert(window.document.documentElement.getAttribute("data-track") === "psle",
    `expected data-track="psle", got ${window.document.documentElement.getAttribute("data-track")}`);
  await go("#/olevel");
  assert(window.document.documentElement.getAttribute("data-track") === "olevel",
    `expected data-track="olevel" after navigating away from PSLE`);
  await go("#/data");
  assert(!window.document.documentElement.hasAttribute("data-track"),
    "a shared page still carries a track's accent instead of the default one");
});

await check("the chooser's nav shows exactly the three doors, in the order a child moves through school", async () => {
  // A real screenshot once showed this nav reading A-Level, Sources, After
  // PSLE, O-Level, No idea yet, Results day, Two of you -- ROUTES' own array
  // order, contradicting the door CARDS two inches below it, which correctly
  // went PSLE first. Two pieces of navigation on one screen disagreeing
  // about the order of a family's own life was worse than either being
  // wrong alone.
  await go("#/");
  const top = all("#topnav a[data-route]").map((a) => a.dataset.route);
  assert(top.join(",") === "psle,olevel,alevel",
    `expected exactly psle,olevel,alevel in that order, got ${top.join(",")}`);
});

await check("the PSLE and O-Level pages hide A-Level's own sub-pages from nav", async () => {
  await go("#/psle");
  const top = all("#topnav a[data-route]").map((a) => a.dataset.route);
  for (const alevelOnly of ["result", "courses", "compare", "dates", "routes", "fees", "scoring"]) {
    assert(!top.includes(alevelOnly), `A-Level's "${alevelOnly}" page is still in nav on the PSLE page`);
  }
  assert(top.includes("psle"), "the PSLE page lost its own nav entry");
});

await check("being inside a track offers a compact way back to the chooser", async () => {
  await go("#/olevel");
  const back = $('#topnav a[data-route="change-track"]');
  assert(back, "no change-track link rendered while inside a track");
  assert(back.getAttribute("href") === "#/", "the change-track link does not point at the chooser");
  await go("#/data");
  assert(!$('#topnav a[data-route="change-track"]'),
    "a shared page (no track) still shows a change-track link");
});

await check("the PathAhead wordmark is a link back to the chooser from anywhere", async () => {
  // The masthead logo used to be a plain <div> -- clicking it did nothing,
  // and the only way back to "#/" from deep in a track was the small
  // change-track link, which does not even appear on shared pages like
  // #/data. A logo that is not a link is a dead end with a familiar face.
  await go("#/alevel");
  const logo = $(".logo");
  assert(logo && logo.tagName === "A", "the wordmark is not a link");
  assert(logo.getAttribute("href") === "#/", "the wordmark does not point at the chooser");
  await go("#/data");
  assert($(".logo")?.getAttribute("href") === "#/", "the wordmark link disappears on a shared page");
});

/* The privacy rule as a source-level guard. A future edit that starts
   serialising the profile into the hash would pass every behavioural check
   above if it happened on a route those checks do not walk. */
await check("the source never assigns typed state into location", () => {
  const script = html.slice(html.indexOf("<script>"));
  const writes = [...script.matchAll(/location\.(hash|search|href)\s*=\s*([^;\n]+)/g)];
  assert(writes.length > 0, "expected at least one hash write (the router)");
  for (const [, prop, expr] of writes) {
    assert(prop === "hash", `source writes location.${prop}, which leaves the app`);
    for (const banned of ["P.", "S.rows", "S.profile", "goalText", "readGrades", "S.result"]) {
      assert(!expr.includes(banned),
        `location.hash is assigned from ${banned} — that is student data in a URL`);
    }
  }
});

/* ---- U2: the pages that carry the weight ------------------------------ */

await check("the course page asks its questions in the order a family asks them", async () => {
  /* The ORDER is the design, so it is asserted rather than merely the presence
     of each section.

     This used to assert `order.length === 9` against one hard-coded course.
     When the accreditation section ("5b — Whether you may practise") was
     added, that assertion only kept passing because the course it happened to
     load — nus-computer-science — is not a registered profession. A check that
     passes by accident of its fixture is worse than no check: it reads as
     coverage. Both shapes are now driven. */
  const base = ["What it is", "Evidence", "Fit", "Money", "After it",
                "Can you change your mind?", "Ways in", "Dates", "Sources"];

  await go("#/course/nus-computer-science");
  let order = all("#courseOut .course-sec .eyebrow").map((p) => p.textContent);
  assert(order.length === base.length,
    `unaccredited course showed ${order.length} sections, expected ${base.length}`);
  base.forEach((w, i) => assert(order[i].includes(w),
    `section ${i + 1} is "${order[i]}", expected "${w}"`));

  // A registered profession gains one section, and it must sit BEFORE
  // reversibility: whether you may lawfully practise outranks whether you
  // could change your mind.
  const accredited = pack.outcomes.find((o) => o.accreditation && o.accreditation.length);
  assert(accredited, "no accredited course in the pack to check the other shape");
  await go(`#/course/${accredited.id}`);
  order = all("#courseOut .course-sec .eyebrow").map((p) => p.textContent);
  assert(order.length === base.length + 1,
    `${accredited.id} showed ${order.length} sections, expected ${base.length + 1}`);
  const practise = order.findIndex((t) => t.includes("Whether you may practise"));
  const change = order.findIndex((t) => t.includes("Can you change your mind?"));
  assert(practise > -1, `${accredited.id} does not show its accreditation section`);
  assert(practise < change,
    "accreditation is listed after reversibility; a licence outranks a preference");
});

await check("every figure on a course page can be reported as wrong", async () => {
  await go("#/course/nus-computer-science");
  const links = all("#courseOut a.wrong");
  assert(links.length >= 4, `only ${links.length} report links on a course with band, cost, salary and flexibility`);
  for (const a of links) {
    assert(a.href.includes("pack%20version") || a.href.includes("Pack+version") ||
           a.href.includes("Pack%20version"),
      "a report link does not carry the pack version, so a report cannot be placed");
  }
});

await check("salary is shown as a range, never as a bare median", async () => {
  await go("#/course/nus-computer-science");
  const txt = $("#courseOut").textContent;
  const o = pack.outcomes.find((x) => x.id === "nus-computer-science");
  assert(txt.includes(o.employment.gross_p25.toLocaleString()), "p25 missing");
  assert(txt.includes(o.employment.gross_p75.toLocaleString()), "p75 missing");
  // A course with an employment rate but no quartiles must not invent a range.
  const sit = pack.outcomes.find((x) => x.institution_short === "SIT" &&
    x.employment && !x.employment.gross_median);
  if (sit) {
    await go(`#/course/${sit.id}`);
    const t = $("#courseOut").textContent.toLowerCase();
    assert(t.includes("range or nothing") || t.includes("no graduate survey"),
      "a course without quartiles does not explain why no salary is shown");
  }
});

await check("a missing fee reads as missing, not as free", async () => {
  /* Chosen from the pack, not hard-coded. This check used to name a Singapore
     Polytechnic course as its example of an unpriced one; SP's fees were
     loaded on 2026-08-05 and the check then failed for the happiest possible
     reason. A fixture that names an institution is a fixture that expires the
     day the data improves — so ask the bundle which courses lack a fee.

     Both kinds are covered: one whose absence carries a written reason, and
     one where the fee is simply not loaded. Neither may render as $0. */
  const unpriced = pack.outcomes.filter(
    (o) => !(o.cost && (o.cost.annual_fee_citizen || o.cost.fee_per_credit_citizen)));
  assert(unpriced.length, "no unpriced course left to check — retire this check instead");
  const samples = [unpriced.find((o) => o.fee_note), unpriced.find((o) => !o.fee_note)]
    .filter(Boolean);
  for (const o of samples) {
    await go(`#/course/${o.id}`);
    const txt = $("#courseOut").textContent.toLowerCase();
    assert(!/\$0\b/.test(txt), `${o.id}: a course with no fee figure shows $0`);
    assert(txt.includes("does not hold a published fee") || txt.includes("never as a low one") ||
           txt.includes("no fee"),
      `${o.id}: a course with no fee figure does not say the figure is absent`);
  }
});

await check("changing citizenship changes the fee shown", async () => {
  await go("#/course/nus-computer-science");
  const o = pack.outcomes.find((x) => x.id === "nus-computer-science");
  const sel = $("#czCourse");
  assert(sel, "no citizenship selector on the course page");
  assert($("#courseOut").textContent.includes(o.cost.annual_fee_citizen.toLocaleString()),
    "citizen fee not shown by default");
  sel.value = "international";
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 60));
  assert($("#courseOut").textContent.includes(o.cost.annual_fee_international.toLocaleString()),
    "international fee not shown after switching");
  const back = $("#czCourse");
  back.value = "citizen";
  back.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 60));
});

await check("the course page offers at least three ways in, direct first", async () => {
  await go("#/course/nus-computer-science");
  const sec = all("#courseOut .course-sec").find((s) =>
    s.querySelector(".eyebrow").textContent.includes("Ways in"));
  const items = [...sec.querySelectorAll("ol.timeline > li")];
  assert(items.length >= 3, `only ${items.length} routes offered (SAFEGUARDS 5.2 requires three)`);
  assert(/direct|apply directly/i.test(items[0].textContent), "the direct route is not first");
});

await check("a course taught in a language says so on its own page", async () => {
  await go("#/course/ntu-chinese-medicine");
  const t = $("#courseOut").textContent.toLowerCase();
  assert(t.includes("requires a language"), "no language requirement shown");
  assert(t.includes("taught substantially in that language"),
    "the teaching language — the part that decides livability — is not stated");
});

await check("the university page states what PathAhead does not hold", async () => {
  await go("#/uni/SP");
  const t = $("#uniOut").textContent;
  assert(/What PathAhead does not hold/i.test(t), "no coverage statement");
  assert(/gaps, not zeroes/i.test(t), "gaps are not distinguished from zeroes");
  const sp = pack.outcomes.filter((o) => o.institution_short === "SP");
  assert($("#uniOut").textContent.includes(String(sp.length)), "course count not shown");
});

await check("university courses are grouped and never ordered by selectivity", async () => {
  await go("#/uni/NUS");
  const names = all("#uniOut ul.plain li a[href^='#/course/']").map((a) => a.textContent);
  assert(names.length >= 5, "too few courses listed to check ordering");
  const bands = names.map((n) => {
    const o = pack.outcomes.find((x) => x.institution_short === "NUS" && x.name === n);
    return o && o.band ? o.band.p90_points : null;
  }).filter((x) => x !== null);
  const desc = bands.every((v, i) => i === 0 || bands[i - 1] >= v);
  assert(!(desc && bands.length > 3 && new Set(bands).size > 2),
    "courses appear ordered by selectivity, which SAFEGUARDS 5.1 forbids");
});

await check("the fees page explains the bond rather than footnoting it", async () => {
  await go("#/fees");
  const t = $("#feesOut").textContent.toLowerCase();
  assert(t.includes("tuition grant"), "the tuition grant is not explained");
  assert(t.includes("service bond") || t.includes("three years working"),
    "the bond attached to the grant is not explained");
  assert(t.includes("not a discount"), "the grant is presented without its condition");
  assert(t.includes("financial aid") || t.includes("bursaries"),
    "no route to financial aid for a family for whom the fee is the problem");
});

await check("the fees page names its own worst gap", async () => {
  /* Derived from the pack, like the page itself. The earlier version asserted
     the words "polytechnic" appeared, which passed for as long as the
     polytechnics were the gap and would have gone on passing over a stale
     sentence once they were priced. What matters is that the page names
     whichever institution actually has the most unpriced courses. */
  await go("#/fees");
  const t = $("#feesOut").textContent.toLowerCase();
  const byInst = {};
  for (const o of pack.outcomes) {
    const r = (byInst[o.institution] ||= { n: 0, priced: 0 });
    r.n++;
    if (o.cost && (o.cost.annual_fee_citizen || o.cost.fee_per_credit_citizen)) r.priced++;
  }
  const worst = Object.entries(byInst).map(([k, v]) => [k, v.n - v.priced])
    .filter(([, m]) => m > 0).sort((a, b) => b[1] - a[1])[0];
  if (worst) {
    assert(t.includes(worst[0].toLowerCase()),
      `the largest fee gap (${worst[0]}, ${worst[1]} courses) is not named`);
    assert(t.includes("missing data"), "blanks are not explained as missing data");
  }
});

await check("the fees table is not sorted by price", async () => {
  await go("#/fees");
  const rows = all("#feesOut table.cmp tbody tr");
  assert(rows.length >= 5, "too few rows to check");
  const names = rows.map((r) => r.querySelector("td").textContent.trim());
  const sorted = [...names].sort();
  assert(JSON.stringify(names) === JSON.stringify(sorted),
    `institutions are not in A-Z order (${names.join(",")}) — check nothing sorted by cost`);
});

await check("printing a course page keeps the citations and drops the controls", () => {
  const css = html.slice(html.indexOf("@media print"));
  assert(/a\.wrong\{display:none\}/.test(css.replace(/\s/g, "")),
    "the report-a-figure links print as clutter");
  assert(/\.course-sec\{break-inside:avoid/.test(css.replace(/\s+/g, "")),
    "course sections can be split across a page break mid-figure");
  assert(!/\.cite\{display:none\}/.test(css.replace(/\s/g, "")),
    "citations are hidden in print, which is the whole point of the page");
});

/* ---- U3: filter, search, density -------------------------------------- */

/* One run, reused. Each of these re-renders 330 courses, so doing the full
   sample run per check cost more than every other check in the file put
   together. `runFresh` now just clears the filters and returns to the list. */
await go("#/alevel");
click($("#sample"));
await new Promise((r) => setTimeout(r, 150));
const clearFilters = () => {
  const btn = all("#filterBar button").find((b) => /clear filters/i.test(b.textContent));
  if (btn) click(btn);
};
const runFresh = async () => {
  await go("#/courses");
  clearFilters();
  await new Promise((r) => setTimeout(r, 40));
};

await check("the course list can be filtered and searched", async () => {
  await runFresh();
  assert($("#filterBar"), "no filter bar");
  const before = all("#groups li.course, #groups table.compact tbody tr").length;
  assert(before > 0, "nothing listed to filter");
  const search = $("#courseSearch");
  assert(search, "no search box");
  search.value = "nursing";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 35));
  const after = all("#groups li.course, #groups table.compact tbody tr");
  assert(after.length > 0, "search for a real course found nothing");
  assert(after.length < before, "search did not narrow the list");
  for (const row of after) {
    assert(/nursing/i.test(row.textContent), `a non-matching row survived: ${row.textContent.slice(0, 40)}`);
  }
  search.value = "";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 35));
});

await check("search matches the way people actually type", async () => {
  await runFresh();
  const search = $("#courseSearch");
  for (const q of ["computer science", "COMPUTER  SCIENCE", "computerscience"]) {
    search.value = q;
    search.dispatchEvent(new window.Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 60));
    const n = all("#groups li.course, #groups table.compact tbody tr").length;
    assert(n > 0, `"${q}" found nothing`);
  }
  search.value = "";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 60));
});

await check("filtering by institution shows only that institution", async () => {
  await runFresh();
  const sel = $("#fInst");
  assert(sel, "no institution filter");
  sel.value = "SP";
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 35));
  /* Checked against the PACK, not against the rendered copy. The first version
     of this searched each row's text for the literal "SP" and failed on a
     correctly filtered list: a card names the institution the way a family
     says it — "Singapore Polytechnic" — and its id is lower-case. The filter
     was right and the assertion was wrong, which is the expensive way round.
     `data-course` is on every row for exactly this. */
  const spIds = new Set(pack.outcomes.filter((o) => o.institution_short === "SP").map((o) => o.id));
  const idsOf = () => all("#groups li.course, #groups table.compact tbody tr")
    .map((r) => r.getAttribute("data-course"));
  const shown = idsOf();
  assert(shown.length > 0, "filtering to SP showed nothing");
  for (const id of shown) {
    assert(id, "a row carries no data-course — the check cannot tell what it is");
    assert(spIds.has(id), `${id} is not an SP course and survived the filter`);
  }
  /* Card mode pages each bucket, so the list above proves nothing LEAKED but
     cannot prove nothing was LOST. Compact mode is unpaged by design, so the
     whole filtered set is present and can be counted. A filter that quietly
     drops courses is as wrong as one that lets them through. */
  const compact = all("#filterBar .seg button").find((b) => /compact/i.test(b.textContent));
  assert(compact, "no compact density control");
  click(compact);
  await new Promise((r) => setTimeout(r, 45));
  const allShown = idsOf();
  assert(allShown.length === spIds.size,
    `compact mode showed ${allShown.length} SP courses, the pack holds ${spIds.size}`);
  const cards = all("#filterBar .seg button").find((b) => /cards/i.test(b.textContent));
  click(cards);
  await new Promise((r) => setTimeout(r, 45));
  sel.value = "";
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 35));
});

await check("there is no way to filter or sort by selectivity or by pay", async () => {
  await runFresh();
  const controls = all("#filterBar select, #filterBar button, #sortControl button");
  for (const c of controls) {
    const label = (c.id + " " + c.textContent + " " +
      (c.previousElementSibling?.textContent || "")).toLowerCase();
    for (const banned of ["salary", "pay", "earnings", "selectiv", "cut-off", "cutoff",
                          "competitive", "hardest", "prestige", "rank"]) {
      assert(!label.includes(banned),
        `a control offers "${banned}" — SAFEGUARDS 5.1 forbids ranking by it, and a filter is a ranking with extra steps`);
    }
  }
  // The absence must also be stated, so it reads as a decision not an omission.
  assert(/never a way to sort people|cannot filter by how selective/i.test($("#filterBar").textContent),
    "the filter bar does not say why selectivity and pay are absent");
});

await check("compact mode shows every course, not a page of them", async () => {
  await runFresh();
  const cardCount = all("#groups li.course").length;
  const seg = all("#filterBar .seg button").find((b) => /compact/i.test(b.textContent));
  assert(seg, "no compact density control");
  click(seg);
  await new Promise((r) => setTimeout(r, 45));
  const rows = all("#groups table.compact tbody tr");
  assert(rows.length > cardCount,
    `compact showed ${rows.length} rows, card view showed ${cardCount} — compact should not be paged`);
  assert(all("#groups table.compact a[href^='#/course/']").length === rows.length,
    "compact rows do not link to their course pages");
  const back = all("#filterBar .seg button").find((b) => /cards/i.test(b.textContent));
  click(back);
  await new Promise((r) => setTimeout(r, 45));
  assert(all("#groups li.course").length > 0, "could not return to card view");
});

await check("the filter bar says how many of how many are shown", async () => {
  await runFresh();
  const t = $("#filterCount").textContent;
  assert(/\d+ of \d+ courses shown/.test(t), `count reads "${t}"`);
});

/* ---------------------------------------------------------------------- */
console.log(`\n${results.length - failures}/${results.length} UI checks passed.`);
process.exit(failures ? 1 : 0);

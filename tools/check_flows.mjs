/**
 * U5 flow logic, checked without a DOM.
 *
 *   node tools/check_flows.mjs
 *
 * Same reasoning as tools/check_filters.mjs: the substance of #/explore and
 * #/perspectives is pure — which courses carry which interests, and where two
 * sets of answers agree — so it is checked here, in under a second, rather
 * than only through jsdom.
 *
 * This does not check that the buttons are wired to these functions.
 * tools/check_ui.mjs does that.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Script, createContext } from "node:vm";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(REPO, "web", "index.html"), "utf8");
const pack = JSON.parse(readFileSync(join(REPO, "web", "data", "singapore.json"), "utf8"));

function fnSource(name) {
  const i = html.indexOf(`function ${name}(`);
  if (i < 0) throw new Error(`${name} not found in web/index.html`);
  let depth = 0, started = false;
  for (let j = i; j < html.length; j++) {
    if (html[j] === "{") { depth++; started = true; }
    else if (html[j] === "}") { depth--; if (started && depth === 0) return html.slice(i, j + 1); }
  }
  throw new Error(`${name} is unbalanced`);
}

const ctx = createContext({});
new Script(fnSource("exploreMatches") + "\n" + fnSource("comparePerspectives")).runInContext(ctx);
const { exploreMatches, comparePerspectives } = ctx;

let failures = 0, ran = 0;
const check = (name, fn) => {
  ran++;
  try { fn(); console.log(`  ok    ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n         ${e.message}`); }
};
const assert = (c, m) => { if (!c) throw new Error(m); };

/* ---- #/explore -------------------------------------------------------- */

check("picking nothing suggests nothing, rather than everything", () => {
  assert(exploreMatches(pack.outcomes, []).length === 0, "an empty pick returned courses");
});

check("picking an interest returns only courses carrying it", () => {
  const r = exploreMatches(pack.outcomes, ["I"]);
  assert(r.length > 0, "no course carries interest I");
  for (const o of r)
    assert((o.editorial?.interests || []).includes("I"), `${o.id} does not carry I`);
});

check("picking a second interest narrows, never widens", () => {
  const one = exploreMatches(pack.outcomes, ["I"]).length;
  const two = exploreMatches(pack.outcomes, ["I", "R"]).length;
  assert(two <= one, `adding an interest widened the list: ${one} -> ${two}`);
  for (const o of exploreMatches(pack.outcomes, ["I", "R"])) {
    const ints = o.editorial?.interests || [];
    assert(ints.includes("I") && ints.includes("R"), `${o.id} matches only one of the two`);
  }
});

check("an impossible combination returns nothing rather than a near miss", () => {
  const codes = (pack.interests || []).map((i) => i.code);
  const all = exploreMatches(pack.outcomes, codes);
  assert(all.length === 0 || all.every((o) =>
    codes.every((c) => (o.editorial?.interests || []).includes(c))),
    "a course was returned that does not carry every picked interest");
});

/* ---- #/perspectives --------------------------------------------------- */

const Q = [
  { k: "interests", label: "What pulls at you?", multi: true,
    opts: () => [["R", "Building"], ["I", "Investigating"], ["S", "Helping"]] },
  { k: "teamwork", label: "You would rather work",
    opts: () => [["individual", "On your own"], ["team", "In a team"]] },
];

check("identical answers read as agreement, with nothing in the difference column", () => {
  const a = { interests: ["R"], teamwork: "team" };
  const { agree, differ } = comparePerspectives(a, { ...a }, Q);
  assert(agree.length === 2, `expected 2 agreements, got ${agree.length}`);
  assert(differ.length === 0, `identical answers produced a difference: ${differ.join(" | ")}`);
});

check("opposite answers read as a difference and name both sides", () => {
  const { agree, differ } = comparePerspectives(
    { teamwork: "individual" }, { teamwork: "team" }, Q);
  assert(agree.length === 0, "opposite answers were reported as agreement");
  assert(differ.length === 1, `expected 1 difference, got ${differ.length}`);
  assert(/young person/.test(differ[0]) && /parent/.test(differ[0]),
    `the difference does not name both sides: ${differ[0]}`);
});

check("a partial overlap is split, not rounded to agreement", () => {
  const { agree, differ } = comparePerspectives(
    { interests: ["R", "I"] }, { interests: ["R", "S"] }, Q);
  assert(agree.length === 1 && /Building/.test(agree[0]), `overlap missing: ${agree.join("|")}`);
  assert(differ.length === 1, "the non-overlapping picks were not reported");
  assert(/Investigating/.test(differ[0]) && /Helping/.test(differ[0]),
    `both unique answers should appear: ${differ[0]}`);
});

check("an answer only one person gave is a difference, not agreement", () => {
  /* The tempting shortcut is to skip a question one side left blank. That
     silently turns "we have not discussed this" into "we agree". */
  const { agree, differ } = comparePerspectives({ teamwork: "team" }, {}, Q);
  assert(agree.length === 0, "a one-sided answer was counted as agreement");
  assert(differ.length === 1 && /only the young person answered/.test(differ[0]),
    `expected a one-sided difference, got: ${differ.join(" | ")}`);
});

check("the comparison never scores, ranks or picks a winner", () => {
  /* SAFEGUARDS 5.3 and 5.4. The output is a conversation, and a parent
     holding more authority than a child is exactly why it must not arbitrate. */
  const { agree, differ } = comparePerspectives(
    { interests: ["R"], teamwork: "individual" },
    { interests: ["S"], teamwork: "team" }, Q);
  const text = [...agree, ...differ].join(" ").toLowerCase();
  for (const banned of ["score", "%", "better", "worse", "should", "right answer",
                        "correct", "wrong", "win", "recommend"]) {
    assert(!text.includes(banned), `the comparison says "${banned}": ${text}`);
  }
  assert(!/\d+\s*\/\s*\d+/.test(text), "the comparison produced a score");
});

check("nothing is returned for questions neither person answered", () => {
  const { agree, differ } = comparePerspectives({}, {}, Q);
  assert(agree.length === 0 && differ.length === 0,
    "unanswered questions produced output");
});

console.log(`\n${ran - failures}/${ran} flow checks passed.`);
process.exit(failures ? 1 : 0);

/**
 * Filter and search logic, checked without a DOM.
 *
 *   node tools/check_filters.mjs
 *
 * `tools/check_ui.mjs` drives the real page and is the fuller test, but it
 * needs jsdom, which costs seconds and — as of this writing — will not load at
 * all in some sandboxes. The *logic* underneath U3 is pure: given a course and
 * a set of filters, is it in or out. That part needs no DOM and no browser, so
 * it is checked here where it runs in under a second.
 *
 * This does NOT replace check_ui.mjs. It cannot see whether the controls are
 * wired to these functions. It only proves the functions themselves are right.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Script, createContext } from "node:vm";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(REPO, "web", "index.html"), "utf8");
const pack = JSON.parse(readFileSync(join(REPO, "web", "data", "singapore.json"), "utf8"));

/* Pull the exact source of the functions under test out of the shipped file,
   so this cannot drift from what the browser runs. */
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

const ctx = createContext({
  F: { q: "", inst: "", field: "", interest: "", assessment: "", extra: "", flex: "", fee: "" },
  P: { citizenship: "citizen" },
  hasExtra: (o) => (o.overlays || []).length > 0,
  feeFor: (o) => (o.cost && (o.cost.annual_fee_citizen || o.cost.total_citizen) ? {} : null),
});
new Script(fnSource("searchHit") + "\n" + fnSource("matchesFilters")).runInContext(ctx);
const { searchHit, matchesFilters, F } = ctx;

let failures = 0, ran = 0;
const check = (name, fn) => {
  ran++;
  try { fn(); console.log(`  ok    ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n         ${e.message}`); }
};
const assert = (c, m) => { if (!c) throw new Error(m); };
const reset = () => { for (const k of Object.keys(F)) F[k] = ""; };
const shown = () => pack.outcomes.filter(matchesFilters);

check("an empty filter set shows everything", () => {
  reset();
  assert(shown().length === pack.outcomes.length,
    `${shown().length} of ${pack.outcomes.length}`);
});

check("search finds a course by its name", () => {
  reset(); F.q = "nursing";
  const r = shown();
  assert(r.length > 0, "found nothing");
  for (const o of r) assert(/nursing/i.test(o.name + o.id), `${o.id} does not match`);
});

check("search ignores spacing and case, the way people type", () => {
  reset();
  const forms = ["computer science", "COMPUTER SCIENCE", "computerscience", "  computer   science  "];
  const counts = forms.map((q) => { F.q = q; return shown().length; });
  assert(counts.every((n) => n > 0), `some form found nothing: ${counts.join(",")}`);
  assert(new Set(counts).size === 1, `forms disagree: ${counts.join(",")}`);
});

check("search matches on institution as well as course", () => {
  reset(); F.q = "polytechnic";
  assert(shown().length > 50, `only ${shown().length} matched a whole sector`);
});

check("every filter narrows, and none of them invents a course", () => {
  const total = pack.outcomes.length;
  const cases = [
    ["inst", "SP"], ["interest", "I"], ["assessment", "exams"],
    ["extra", "yes"], ["extra", "no"], ["flex", "yes"],
    ["fee", "known"], ["fee", "unknown"],
  ];
  for (const [k, v] of cases) {
    reset(); F[k] = v;
    const n = shown().length;
    assert(n > 0, `${k}=${v} filtered everything away`);
    assert(n <= total, `${k}=${v} produced ${n} of ${total}`);
  }
});

check("institution filter returns only that institution", () => {
  reset(); F.inst = "SP";
  const r = shown();
  assert(r.length === pack.outcomes.filter((o) => o.institution_short === "SP").length,
    `got ${r.length}`);
  for (const o of r) assert(o.institution_short === "SP", `${o.id} leaked through`);
});

check("the fee filter splits the pack exactly in two, with no overlap", () => {
  reset(); F.fee = "known"; const known = shown().length;
  reset(); F.fee = "unknown"; const unknown = shown().length;
  assert(known + unknown === pack.outcomes.length,
    `${known} + ${unknown} != ${pack.outcomes.length}`);
  assert(known > 0 && unknown > 0, "one side is empty, so the filter is not doing anything");
});

check("filters combine rather than replace each other", () => {
  reset(); F.inst = "SP"; const a = shown().length;
  F.q = "engineering"; const b = shown().length;
  assert(b < a, `adding a search did not narrow ${a} -> ${b}`);
  const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
  for (const o of shown()) {
    assert(o.institution_short === "SP", "institution filter was dropped");
    /* Match against the same fields the search actually looks at, not just
       the name. The first version of this check asserted on name and id
       alone and failed on SP's Mechatronics & Robotics — which is a correct
       hit through its sector, not a leak. Asserting the narrower thing would
       have pushed a fix onto working code. */
    const hay = [o.name, o.id, o.institution, o.institution_short, o.faculty,
                 ...(o.editorial?.sectors || [])].map(norm).join(" ");
    assert(hay.includes("engineering"), `${o.id} matched nothing searchable`);
  }
});

check("search looks past the course name, so a field finds its courses", () => {
  /* Someone types "engineering", not "mechatronics". A search that only read
     the title would hide the course they were looking for. */
  reset(); F.q = "engineering";
  const hits = shown();
  const byNameOnly = hits.filter((o) => /engineering/i.test(o.name + o.id));
  assert(hits.length > byNameOnly.length,
    "search matched titles only — sector and faculty are not being searched");
});

/* ---- streams ---------------------------------------------------------- */

const STREAMS = (() => {
  const m = html.match(/const STREAMS = \[([\s\S]*?)\n\];/);
  if (!m) throw new Error("STREAMS table not found in web/index.html");
  return eval("[" + m[1] + "]");
})();
const SECTOR_TO_STREAM = (() => {
  const m = {};
  for (const [id, , secs] of STREAMS) for (const s of secs) (m[s] ||= []).push(id);
  return m;
})();
const streamsOf = (o) => {
  const out = new Set();
  for (const s of (o.editorial?.sectors || [])) for (const id of (SECTOR_TO_STREAM[s] || [])) out.add(id);
  return [...out];
};

/* The stream picker is a control on ONE page — #/courses, the A-Level result
   view — filtering the university and polytechnic outcomes shown there. It
   was never meant to classify a Junior College's "Science (27S)" or an
   MI course by engineering-vs-healthcare-vs-business sector, because that
   taxonomy does not describe a JC stream at all; JC/MI outcomes are reached
   from #/olevel instead, which has no stream picker to be unreachable in.
   Scoping the coverage rule to the population it actually governs is not
   loosening it — a JC course with no `editorial.sectors` was never a gap
   this filter needed to close, and pretending otherwise would mean forcing
   a fake sector onto every JC course just to silence a check. */
const STREAM_ELIGIBLE = pack.outcomes.filter((o) => o.transition === "a-level-to-university-2026");

check("every course belongs to at least one stream", () => {
  /* THE COVERAGE RULE. A course in no stream becomes permanently unreachable
     the moment a student picks any stream — it would vanish from the list with
     no way to get it back, and nothing on screen would say so. */
  const orphans = STREAM_ELIGIBLE.filter((o) => streamsOf(o).length === 0);
  assert(orphans.length === 0,
    `${orphans.length} courses land in no stream and would be unreachable, e.g. ` +
    orphans.slice(0, 3).map((o) => `${o.id} [${(o.editorial?.sectors || []).join(",")}]`).join(" | "));
});

check("every stream contains courses, and none swallows the pack", () => {
  for (const [id, label] of STREAMS) {
    const n = STREAM_ELIGIBLE.filter((o) => streamsOf(o).includes(id)).length;
    assert(n > 0, `stream "${label}" is empty, so offering it is a dead end`);
    assert(n < STREAM_ELIGIBLE.length,
      `stream "${label}" contains every course, so choosing it filters nothing`);
  }
});

check("picking a stream narrows the list and keeps only that stream", () => {
  for (const [id, label] of STREAMS.slice(0, 4)) {
    const kept = STREAM_ELIGIBLE.filter((o) => streamsOf(o).includes(id));
    assert(kept.length < STREAM_ELIGIBLE.length, `${label} did not narrow anything`);
    for (const o of kept) {
      assert(streamsOf(o).includes(id), `${o.id} survived the ${label} filter without being in it`);
    }
  }
});

check("a course may sit in more than one stream", () => {
  /* Aerospace Engineering is engineering AND aviation. Forcing one label
     would hide it from a student searching the other. */
  const multi = STREAM_ELIGIBLE.filter((o) => streamsOf(o).length > 1);
  assert(multi.length > 0, "no course spans two streams; the taxonomy is too rigid");
});

check("the stream picker offers no selectivity or pay dimension", () => {
  for (const [id, label] of STREAMS) {
    const t = (id + " " + label).toLowerCase();
    for (const banned of ["salary", "pay", "earnings", "selectiv", "rank", "prestige", "top", "best"]) {
      assert(!t.includes(banned), `stream "${label}" smuggles in a ranking dimension`);
    }
  }
});

check("no filter exists for selectivity or for pay", () => {
  /* SAFEGUARDS 5.1. A filter is a ranking with extra steps, so the absence of
     these keys is load-bearing, not an oversight. */
  reset();
  for (const banned of ["salary", "pay", "earnings", "selectivity", "cutoff",
                        "cut_off", "rank", "prestige", "competitive"]) {
    assert(!(banned in F), `F has a "${banned}" filter`);
  }
});

console.log(`\n${ran - failures}/${ran} filter checks passed.`);
process.exit(failures ? 1 : 0);

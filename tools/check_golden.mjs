/**
 * Cross-engine check: replay every golden fixture through the JavaScript
 * engine extracted from web/index.html and compare against what the Python
 * engine recorded.
 *
 *   node tools/check_golden.mjs
 *
 * The JS engine is read out of the HTML rather than kept in a separate file on
 * purpose: the browser build must stay a single self-contained file a parent
 * can open, and this check must test THAT file, not a copy of it that might
 * drift from it.
 *
 * Fails the build on any disagreement in the final value or in any step.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const TOL = 1e-9;

/* ---- pull the engine out of the single-file app ---------------------- */
const html = readFileSync(join(REPO, "web", "index.html"), "utf8");
const scriptBody = html.split("<script>").pop().split("</script>")[0];

const START = "/* ---------- engine: grade lookup ---------- */";
const END = "/* =====================================================================\n   UI";
const engineSrc = scriptBody.slice(scriptBody.indexOf(START), scriptBody.indexOf(END));
if (!engineSrc.includes("weightedBestN")) {
  console.error("could not locate the engine section inside web/index.html");
  process.exit(2);
}

const factory = new Function(
  `${engineSrc}\nreturn { weightedBestN, gradePoints, RULES, PAError, scoreFit, fitCoverage, matchSchool, shortlistSchools, withinReach, combinedReach };`
);
const { RULES, scoreFit, matchSchool, withinReach, combinedReach } = factory();

/* The compiled pack, from the one place every other tool in this directory
   reads it: web/data/. This file used to read dist/ instead, and nothing
   caught it locally because a developer running `npm run check` has both
   directories lying around from earlier builds. CI does not: a clean
   checkout has neither, so whichever one the workflow happened to build
   was the only one that existed, and the tool that wanted the other one
   died on ENOENT. Both workflows failed this way, in mirror image --
   ci.yml built dist/ and check_ui.mjs wanted web/data/; release.yml built
   web/data/ and this file wanted dist/. One canonical location, so there
   is no second place for the two to disagree about. */
const PACK = join(REPO, "web", "data", "singapore.json");
if (!existsSync(PACK)) {
  console.error(
    `no compiled pack at ${PACK}\n` +
    "  run: python app/cli.py build --out web/data"
  );
  process.exit(2);
}
const packJson = JSON.parse(readFileSync(PACK, "utf8"));
const FAM = Object.fromEntries((packJson.subjects || []).map(s => [s.code, s.family || s.code]));

/* ---- replay the fixtures -------------------------------------------- */
const golden = JSON.parse(readFileSync(join(REPO, "evals", "golden", "rules.json"), "utf8"));
const pack = packJson;

let failures = 0;
let checked = 0;

for (const c of golden.cases) {
  checked++;
  const t = pack.transitions.find((t) => t.id === c.transition);
  if (!t) {
    console.error(`FAIL ${c.id}: transition ${c.transition} not in the compiled pack`);
    failures++;
    continue;
  }
  const fn = RULES[t.rule_kind];
  if (!fn) {
    console.error(`FAIL ${c.id}: the browser engine has no rule kind "${t.rule_kind}"`);
    failures++;
    continue;
  }

  let got;
  try {
    got = fn(t.rule_params, t.scales, c.subjects, t.caveats);
  } catch (err) {
    console.error(`FAIL ${c.id}: browser engine threw -- ${err.message}`);
    failures++;
    continue;
  }

  const want = c.expected;
  const problems = [];

  if (Math.abs(got.value - want.value) > TOL) {
    problems.push(`value ${got.value} != ${want.value}`);
  }
  if (got.steps.length !== want.steps.length) {
    problems.push(`${got.steps.length} steps vs ${want.steps.length}`);
  } else {
    want.steps.forEach((w, i) => {
      const g = got.steps[i];
      if (g.kind !== w.kind) problems.push(`step ${i} kind ${g.kind} != ${w.kind}`);
      if (g.label !== w.label) problems.push(`step ${i} label "${g.label}" != "${w.label}"`);
      for (const f of ["points", "running_total"]) {
        const a = g[f] ?? null, b = w[f] ?? null;
        if (a === null && b === null) continue;
        if (a === null || b === null || Math.abs(a - b) > TOL) {
          problems.push(`step ${i} ${f} ${a} != ${b}`);
        }
      }
    });
  }

  if (problems.length) {
    failures++;
    console.error(`FAIL ${c.id}`);
    for (const p of problems.slice(0, 6)) console.error(`       ${p}`);
  } else {
    console.log(`  ok   ${c.id.padEnd(38)} ${got.value}`);
  }
}

/* ---- fit parity ------------------------------------------------------
   Fit exists twice as well, so it gets the same guarantee. Without this the
   browser could quietly disagree with the CLI about *why* a course suits
   someone, which is exactly the kind of drift nobody notices until a family
   is looking at two different answers. */
for (const c of golden.fit_cases ?? []) {
  checked++;
  const profile = {
    interests: [], enjoyed_subjects: [], priorities: [],
    assessment_style: null, teamwork: null, goal_text: "",
    willing_extra_assessment: null, cost_sensitive: null,
    ...c.profile,
  };
  const problems = [];

  for (const oid of c.outcomes) {
    const outcome = pack.outcomes.find((o) => o.id === oid);
    if (!outcome) { problems.push(`outcome ${oid} not in the compiled pack`); continue; }

    let got;
    try {
      got = scoreFit(outcome, profile, FAM);
    } catch (err) {
      problems.push(`${oid}: browser fit threw -- ${err.message}`);
      continue;
    }
    const want = c.expected[oid];

    if (got.score !== want.score) problems.push(`${oid}: score ${got.score} != ${want.score}`);
    if (want.score === null) {
      if (got.unscored_reason !== want.unscored_reason) {
        problems.push(`${oid}: unscored reason differs`);
      }
      continue;
    }
    // "not assessed" must match too: a gap in OUR data has to be reported
    // identically in both engines, or one of them is silently penalising.
    if ((got.not_assessed || []).length !== (want.not_assessed || []).length) {
      problems.push(`${oid}: not_assessed ${(got.not_assessed||[]).length} vs ${(want.not_assessed||[]).length}`);
    }
    if (got.factors.length !== want.factors.length) {
      problems.push(`${oid}: ${got.factors.length} factors vs ${want.factors.length}`);
      continue;
    }
    want.factors.forEach((w, i) => {
      const g = got.factors[i];
      if (g.label !== w.label) problems.push(`${oid} factor ${i}: "${g.label}" != "${w.label}"`);
      if (Math.abs(g.points - w.points) > TOL) {
        problems.push(`${oid} factor ${i} points ${g.points} != ${w.points}`);
      }
      if (Math.abs(g.max - w.max_points) > TOL) {
        problems.push(`${oid} factor ${i} max ${g.max} != ${w.max_points}`);
      }
    });
  }

  if (problems.length) {
    failures++;
    console.error(`FAIL ${c.id}`);
    for (const p of problems.slice(0, 6)) console.error(`       ${p}`);
  } else {
    console.log(`  ok   ${c.id.padEnd(38)} fit across ${c.outcomes.length} courses`);
  }
}

/* ---- school match parity ------------------------------------------------
   Same guarantee, for the PSLE-stage shortlisting FILTERS: every dimension
   here is a filter, not a score, so this checks that both engines agree on
   eligibility, which filters a school does and doesn't match, and distance
   -- the only claims this feature makes at all (SAFEGUARDS.md 5.1). */
const districtIdx = Object.fromEntries(
  (pack.postal_districts||[]).flatMap(row => (row.sectors||[]).map(sector => [String(sector), row]))
);
for (const c of golden.school_match_cases ?? []) {
  checked++;
  const prefs = {
    postal_code: null, student_sex: null, gender: null, want_sap: null, want_ip: null,
    want_autonomous: null, want_gifted: null, school_types: [],
    ...c.preferences,
  };
  const problems = [];

  for (const sid of c.schools) {
    const school = pack.schools.find((s) => s.id === sid);
    if (!school) { problems.push(`school ${sid} not in the compiled pack`); continue; }

    let got;
    try {
      got = matchSchool(school, prefs, districtIdx);
    } catch (err) {
      problems.push(`${sid}: browser matchSchool threw -- ${err.message}`);
      continue;
    }
    const want = c.expected[sid];

    if (got.eligible !== want.eligible) problems.push(`${sid}: eligible ${got.eligible} != ${want.eligible}`);
    if (want.eligible !== true) {
      if (got.eligibility_reason !== want.eligibility_reason) {
        problems.push(`${sid}: eligibility_reason differs`);
      }
    }
    if (got.matches_preferences !== want.matches_preferences) {
      problems.push(`${sid}: matches_preferences ${got.matches_preferences} != ${want.matches_preferences}`);
    }
    const gu = [...(got.unmet||[])].sort(), wu = [...(want.unmet||[])].sort();
    if (gu.length !== wu.length || gu.some((v,i)=>v!==wu[i])) {
      problems.push(`${sid}: unmet [${gu}] != [${wu}]`);
    }
    {
      const gd = got.distance_km ?? null, wd = want.distance_km ?? null;
      if ((gd === null) !== (wd === null)) {
        problems.push(`${sid}: distance_km null-ness differs (${gd} vs ${wd})`);
      } else if (gd !== null && Math.abs(gd - wd) > 0.05) {
        problems.push(`${sid}: distance_km ${gd} != ${wd}`);
      }
    }
  }

  if (problems.length) {
    failures++;
    console.error(`FAIL ${c.id}`);
    for (const p of problems.slice(0, 6)) console.error(`       ${p}`);
  } else {
    console.log(`  ok   ${c.id.padEnd(38)} school match across ${c.schools.length} schools`);
  }
}

/* ---- within_reach parity -----------------------------------------------
   The cut-off reach filter: a yes/no/unknown question, never a score and
   never a sort key (SAFEGUARDS.md 5.1). Checked the same way as everything
   else here -- both engines must agree, not just "both run without error". */
// Each fixture carries its own synthetic school. Nothing is looked up in the
// compiled pack, because the pack no longer holds cut-off figures at all --
// PathAhead does not republish them (see engine/loader.py). Looking one up
// would compare null against null and prove nothing.
for (const c of golden.within_reach_cases ?? []) {
  checked++;
  const problems = [];
  {
    const got = withinReach(c.school, c.psle_score, c.family_groups, c.margin);
    if (got !== c.expected) problems.push(`within_reach ${got} != ${c.expected}`);
  }
  if (problems.length) {
    failures++;
    console.error(`FAIL ${c.id}`);
    for (const p of problems.slice(0, 6)) console.error(`       ${p}`);
  } else {
    console.log(`  ok   ${c.id.padEnd(38)} within_reach = ${c.expected}`);
  }
}

/* ---- combined_reach parity ---------------------------------------------
   The EXPLICIT AL-score search filter (a single score, or a range) -- same
   yes/no/unknown discipline as within_reach above, just answered across a
   band instead of one point. Each fixture carries its own synthetic school,
   same reasoning as within_reach_cases. */
for (const c of golden.combined_reach_cases ?? []) {
  checked++;
  const problems = [];
  {
    const got = combinedReach(c.school, c.lo_score, c.hi_score, c.lo_groups, c.hi_groups, c.margin);
    if (got !== c.expected) problems.push(`combined_reach ${got} != ${c.expected}`);
  }
  if (problems.length) {
    failures++;
    console.error(`FAIL ${c.id}`);
    for (const p of problems.slice(0, 6)) console.error(`       ${p}`);
  } else {
    console.log(`  ok   ${c.id.padEnd(38)} combined_reach = ${c.expected}`);
  }
}

console.log(
  `\n${checked - failures}/${checked} fixtures agree between the Python and browser engines.`
);
process.exit(failures ? 1 : 0);

/**
 * The generated static site, checked against the pack it came from.
 *
 *   node tools/build_static.mjs && node tools/check_static.mjs
 *
 * A generator is a second place figures can go wrong, and this one renders
 * from JSON rather than from the app's own DOM, so nothing stops the two
 * drifting except a test. These checks read the emitted HTML and compare it
 * with the bundle.
 */
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const SITE = join(REPO, "web", "site");
const pack = JSON.parse(readFileSync(join(REPO, "web", "data", "singapore.json"), "utf8"));

let failures = 0, ran = 0;
const check = (name, fn) => {
  ran++;
  try { fn(); console.log(`  ok    ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n         ${e.message}`); }
};
const assert = (c, m) => { if (!c) throw new Error(m); };
const read = (p) => readFileSync(join(SITE, p), "utf8");
/* robots.txt and sitemap.txt live at the DEPLOY ROOT (web/), not alongside
   the generated pages in web/site/ -- GitHub Pages publishes web/ as the site
   root, so a robots.txt any deeper is at a path no crawler requests. Moved
   2026-08-14; this reader follows them. */
const readRoot = (p) => readFileSync(join(REPO, "web", p), "utf8");

function feeFor(o) {
  const c = o.cost; if (!c) return null;
  if (c.fee_basis === "per_credit") return c.total_citizen ? { total: c.total_citizen } : null;
  return c.annual_fee_citizen ? { annual: c.annual_fee_citizen } : null;
}
const indexable = (o) => !!(o.band || (o.banded && o.banded.length)) && !!feeFor(o);

check("a page exists for every course and every institution", () => {
  for (const o of pack.outcomes)
    assert(existsSync(join(SITE, "courses", o.id, "index.html")), `missing page for ${o.id}`);
  const insts = new Set(pack.outcomes.map((o) => o.institution_short));
  for (const s of insts)
    assert(existsSync(join(SITE, "uni", s, "index.html")), `missing page for ${s}`);
  assert(existsSync(join(SITE, "index.html")), "no site index");
});

check("the gate is applied per page, in both directions", () => {
  let idx = 0, noidx = 0;
  for (const o of pack.outcomes) {
    const html = read(join("courses", o.id, "index.html"));
    const isNo = /content="noindex, follow"/.test(html);
    const isIdx = /content="index, follow"/.test(html);
    assert(isNo || isIdx, `${o.id} declares no robots policy`);
    if (indexable(o)) { assert(isIdx, `${o.id} is complete but marked noindex`); idx++; }
    else { assert(isNo, `${o.id} is incomplete but offered to search engines`); noidx++; }
  }
  assert(idx > 0 && noidx > 0, `gate is not discriminating: ${idx} indexed, ${noidx} not`);
});

/* Course names carry ampersands — "Arts (Academic Discipline & Education)",
   "Mechatronics & Robotics" — so a page comparison has to be made against the
   escaped form. The first version of this check compared raw text and failed
   on correctly-escaped output, which would have argued for removing the
   escaping. */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

check("an incomplete page says what is missing rather than hiding it", () => {
  const thin = pack.outcomes.find((o) => !indexable(o));
  const html = read(join("courses", thin.id, "index.html"));
  assert(/This page is incomplete/.test(html), `${thin.id} does not say it is incomplete`);
  assert(html.includes(esc(thin.name)), "an incomplete page withholds the course name");
});

check("text from the pack is escaped, not injected raw", () => {
  const amp = pack.outcomes.find((o) => o.name.includes("&"));
  assert(amp, "no course name with an ampersand to check");
  const html = read(join("courses", amp.id, "index.html"));
  assert(html.includes(esc(amp.name)), `${amp.id}: escaped name missing`);
  assert(!html.includes(`<h1>${amp.name}</h1>`), `${amp.id}: name written raw into HTML`);
});

check("the sitemap advertises only pages that invite indexing", () => {
  const urls = readRoot("sitemap.txt").trim().split("\n").filter(Boolean);
  const expected = pack.outcomes.filter(indexable).length;
  assert(urls.length === expected, `sitemap lists ${urls.length}, expected ${expected}`);
  for (const u of urls) {
    const id = u.replace(/\/$/, "").split("/").pop();
    const o = pack.outcomes.find((x) => x.id === id);
    assert(o && indexable(o), `sitemap advertises ${id}, which is not indexable`);
  }
});

check("robots.txt and the sitemap are at the deploy root, where a crawler looks", () => {
  // The 98 noindex pages are careful work. It only counts if the crawl
  // directives are somewhere a crawler actually requests -- /robots.txt, not
  // /site/robots.txt. This is the guard on that, because the failure mode is
  // completely silent: everything still builds, and nothing is ever read.
  const robots = readRoot("robots.txt");
  assert(/User-agent:\s*\*/i.test(robots), "robots.txt has no user-agent line");
  let strayed = false;
  try { readFileSync(join(SITE, "robots.txt"), "utf8"); strayed = true; } catch { /* expected */ }
  assert(!strayed,
    "a robots.txt was written into web/site/, where GitHub Pages serves it at /site/robots.txt and no crawler reads it");
});

check("published figures on a page match the pack", () => {
  const withAll = pack.outcomes.filter((o) => o.band && feeFor(o) && o.employment?.gross_median);
  assert(withAll.length > 0, "no course rich enough to check");
  for (const o of withAll.slice(0, 25)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(o.band.p10) && html.includes(o.band.p90),
      `${o.id}: band ${o.band.p10}-${o.band.p90} not on the page`);
    const fee = feeFor(o);
    const shown = (fee.annual ?? fee.total).toLocaleString("en-SG");
    assert(html.includes(shown), `${o.id}: fee ${shown} not on the page`);
    assert(html.includes(o.employment.gross_p25.toLocaleString("en-SG")),
      `${o.id}: salary lower quartile not on the page`);
  }
});

check("a course with no fee never renders a zero", () => {
  const none = pack.outcomes.filter((o) => !feeFor(o)).slice(0, 40);
  for (const o of none) {
    const html = read(join("courses", o.id, "index.html"));
    assert(!/\$0\b/.test(html), `${o.id} renders $0 for a fee it does not hold`);
  }
});

check("a course taught in a language says so", () => {
  const lang = pack.outcomes.filter((o) => o.language_requirement?.taught_in_language);
  assert(lang.length > 0, "no such course in the pack");
  for (const o of lang) {
    const html = read(join("courses", o.id, "index.html"));
    assert(/taught substantially in that language/.test(html),
      `${o.id} omits the teaching language`);
  }
});

check("salary is a range, never a bare median", () => {
  for (const o of pack.outcomes.filter((x) => x.employment?.gross_median).slice(0, 20)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(o.employment.gross_p25.toLocaleString("en-SG")) &&
           html.includes(o.employment.gross_p75.toLocaleString("en-SG")),
      `${o.id} shows a median without its quartiles`);
  }
});

check("the pages are self-contained — no third-party resource", () => {
  const files = [join("courses", pack.outcomes[0].id, "index.html"), "index.html"];
  for (const f of files) {
    const html = read(f);
    assert(!/<script/i.test(html), `${f} ships script into a static page`);
    assert(!/<link[^>]+stylesheet/i.test(html), `${f} pulls an external stylesheet`);
    const externals = [...html.matchAll(/(?:src|href)="(https?:\/\/[^"]+)"/g)].map((m) => m[1]);
    for (const u of externals) {
      // moe.gov.sg joined this list for the same reason data.gov.sg did: a
      // Junior College or Millennia Institute has no course-listing page of
      // its own the way a university or polytechnic does, so its `url`
      // legitimately points at MOE's own SchoolFinder page instead of an
      // .edu.sg domain.
      assert(/github\.com|\.edu\.sg|data\.gov\.sg|suss\.edu\.sg|moe\.gov\.sg/.test(u),
        `${f} links out to an unexpected host: ${u}`);
    }
  }
});

check("institution pages link only to courses that exist", () => {
  const insts = new Set(pack.outcomes.map((o) => o.institution_short));
  for (const s of insts) {
    const html = read(join("uni", s, "index.html"));
    const ids = [...html.matchAll(/href="\.\.\/\.\.\/courses\/([^/"]+)\//g)].map((m) => m[1]);
    const own = pack.outcomes.filter((o) => o.institution_short === s).map((o) => o.id);
    assert(ids.length === own.length, `${s} lists ${ids.length} of ${own.length} courses`);
    for (const id of ids) assert(own.includes(id), `${s} links to ${id}, which is not its course`);
  }
});

check("every figure on a page can be checked at its source", () => {
  /* The claim this project makes is that every number is traceable. A source
     list at the bottom is not that; a link beside the number is. */
  const rich = pack.outcomes.filter((o) => o.band && feeFor(o) && o.employment?.gross_median);
  assert(rich.length > 0, "no course rich enough to check");
  for (const o of rich.slice(0, 20)) {
    const html = read(join("courses", o.id, "index.html"));
    const cites = [...html.matchAll(/<p class="cite">([\s\S]*?)<\/p>/g)].map((m) => m[1]);
    assert(cites.length >= 3, `${o.id}: only ${cites.length} citations`);
    const linked = cites.filter((c) => /check the source/.test(c));
    assert(linked.length >= 3,
      `${o.id}: ${linked.length} of ${cites.length} citations are clickable`);
  }
});

check("a course links to the institution's own page for it", () => {
  for (const o of pack.outcomes.filter((x) => x.url).slice(0, 30)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(`href="${o.url}"`),
      `${o.id} does not link to its own course page (${o.url})`);
  }
});

check("Singapore Polytechnic cites the course page, not the listing", () => {
  /* SP publishes per course. A listing link would make a reader hunt. */
  const sp = pack.outcomes.filter((o) => o.institution_short === "SP" && o.band);
  const seen = new Set();
  for (const o of sp) {
    const html = read(join("courses", o.id, "index.html"));
    const u = o.band.fact.url;
    assert(u && u.startsWith("https://www.sp.edu.sg/courses/schools/"),
      `${o.id}: band cites ${u}`);
    assert(html.includes(u), `${o.id}: its own citation URL is not on the page`);
    seen.add(u);
  }
  assert(seen.size >= 30, `SP citations collapsed to ${seen.size} distinct pages`);
});

check("the static page shows what the app shows", () => {
  /* The generator renders from JSON, not from the app's DOM, so a field added
     to one and not the other drifts silently. This is the check that notices. */
  for (const o of pack.outcomes.filter((x) => x.duration).slice(0, 20)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(`${o.duration.years} years`),
      `${o.id}: duration on the app but not on the static page`);
  }
  for (const o of pack.outcomes.filter((x) => x.progression && x.progression.length).slice(0, 10)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(esc(o.progression[0].label)),
      `${o.id}: progression missing from the static page`);
  }
});

check("places appear on the static page as well as in the app", () => {
  const withIntake = pack.outcomes.filter((o) => o.intake);
  assert(withIntake.length > 0, "no course carries an intake figure");
  for (const o of withIntake.slice(0, 20)) {
    const html = read(join("courses", o.id, "index.html"));
    assert(html.includes(esc(String(o.intake.value))),
      `${o.id}: intake shown in the app but missing from the static page`);
  }
});

check("a registered profession says so on the static page too", () => {
  const acc = pack.outcomes.filter((o) => o.accreditation && o.accreditation.length);
  assert(acc.length > 0, "no accredited course in the pack");
  for (const o of acc) {
    const html = read(join("courses", o.id, "index.html"));
    assert(/registered profession/.test(html), `${o.id}: accreditation not shown`);
    assert(html.includes(esc(o.accreditation[0].body)), `${o.id}: licensing body not named`);
  }
});

check("nothing is ordered by selectivity or by pay", () => {
  /* SAFEGUARDS 5.1 applies to generated pages too — arguably more, because a
     static page is what a stranger sees first. */
  const s = "NUS";
  const html = read(join("uni", s, "index.html"));
  const names = [...html.matchAll(/href="\.\.\/\.\.\/courses\/[^"]+\/">([^<]+)</g)].map((m) => m[1]);
  const bands = names.map((n) => {
    const o = pack.outcomes.find((x) => x.institution_short === s && x.name === n);
    return o?.band?.p90_points ?? null;
  }).filter((v) => v !== null);
  const descending = bands.every((v, i) => i === 0 || bands[i - 1] >= v);
  assert(!(descending && new Set(bands).size > 2),
    "courses appear ordered by selectivity on a generated page");
});

console.log(`\n${ran - failures}/${ran} static-site checks passed.`);
process.exit(failures ? 1 : 0);

/**
 * Static site generator — ROADMAP_UI.md phase U4.
 *
 *   node tools/build_static.mjs [--out web/site]
 *
 * Hash routes are invisible to search engines, and families search. This emits
 * a real indexable page per course and per institution, containing the same
 * published figures the app shows, with a link that hands over to the
 * interactive app.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * THE GATE, and why it is implemented rather than merely obeyed.
 *
 * ROADMAP_UI U4 says: "Do this only after the content is right. Indexing 77
 * pages of half-loaded data is worse than indexing nothing." That condition is
 * NOT met — 219 of 330 courses still carry no fee figure, and every editorial
 * description is written at course-family level.
 *
 * Refusing to build the generator would have left the phase undone; building it
 * blind would have published hundreds of pages with holes in them, which is
 * exactly what the roadmap warns against. So the gate is enforced page by page
 * instead of once for the whole site:
 *
 *   - a page whose course has a published admission range AND a fee figure is
 *     emitted indexable;
 *   - any other page is emitted with `robots: noindex, follow` and a visible
 *     line saying what is missing.
 *
 * Nothing is hidden from a person who follows a link. What is withheld is the
 * invitation for a search engine to send strangers to a page that cannot answer
 * the question they searched for. As the pack fills in, pages become indexable
 * on their own, and `--report` prints how many would flip.
 * ─────────────────────────────────────────────────────────────────────────
 *
 * No framework, no build step for the USER — this runs for the maintainer only,
 * and the app it links to is still the same single self-contained file.
 */
import { readFileSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const OUT = join(REPO, argOf("--out") || join("web", "site"));
const REPORT_ONLY = args.includes("--report");
const BASE = argOf("--base") || "";        // e.g. https://example.github.io/path-ahead
function argOf(flag) { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : null; }

const pack = JSON.parse(readFileSync(join(REPO, "web", "data", "singapore.json"), "utf8"));

const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => "$" + Number(n).toLocaleString("en-SG");
const sourceById = (id) => pack.sources.find((s) => s.id === id);

/** Feed the same citizenship default the app uses. */
function feeFor(o) {
  const c = o.cost; if (!c) return null;
  if (c.fee_basis === "per_credit")
    return c.total_citizen ? { total: c.total_citizen, basis: "per_credit", credits: c.total_credits } : null;
  if (!c.annual_fee_citizen) return null;
  return { annual: c.annual_fee_citizen, total: c.total_citizen || (c.years ? c.annual_fee_citizen * c.years : null),
           years: c.years, basis: "annual" };
}

/** The gate. Both halves must hold for a page to invite a search engine. */
function indexable(o) {
  const hasRange = !!(o.band || (o.banded && o.banded.length));
  const hasFee = !!feeFor(o);
  return { ok: hasRange && hasFee, hasRange, hasFee };
}

const CSS = `
:root{--bg:#fdfaf5;--card:#fff;--ink:#2a211b;--ink-2:#5b4d42;--ink-3:#746455;
 --rule:#e6dbcb;--brand:#a8481b;--brand-deep:#8a3a15;--brand-soft:#fbe8da}
@media(prefers-color-scheme:dark){:root{--bg:#191410;--card:#221b16;--ink:#f3e9dd;
 --ink-2:#c8b6a4;--ink-3:#9a8878;--rule:#3a2f26}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:52rem;margin:0 auto;padding:1.5rem 1.1rem 4rem}
a{color:var(--brand-deep)}
h1{font:600 1.9rem/1.2 "Iowan Old Style",Palatino,Georgia,serif;margin:.2rem 0 .4rem}
h2{font:600 1.15rem/1.3 inherit;margin:1.6rem 0 .4rem}
.eyebrow{font:700 .7rem/1 inherit;letter-spacing:.12em;text-transform:uppercase;
 color:var(--brand);margin:0 0 .3rem}
.card{background:var(--card);border:1px solid var(--rule);border-radius:12px;
 padding:1.1rem 1.2rem;margin:0 0 1rem}
.fig{font:600 1.4rem/1.2 "Iowan Old Style",Palatino,Georgia,serif;margin:.2rem 0}
.cite{font-size:.78rem;color:var(--ink-3);margin:.3rem 0 0}
.hint{color:var(--ink-3);font-size:.9rem}
.note{border-left:3px solid var(--brand);background:var(--brand-soft);
 padding:.7rem .9rem;border-radius:8px;margin:.7rem 0;color:#3a2a20}
@media(prefers-color-scheme:dark){.note{background:#33241c;color:var(--ink)}}
ul.plain{list-style:none;padding:0;margin:.5rem 0 0}
ul.plain li{padding:.4rem 0;border-bottom:1px solid var(--rule)}
.btn{display:inline-block;background:var(--brand);color:#fffcf7;text-decoration:none;
 padding:.6rem 1rem;border-radius:8px;font-weight:600;margin:.3rem .3rem .3rem 0}
footer{border-top:1px solid var(--rule);margin-top:2rem;padding-top:1rem;
 font-size:.82rem;color:var(--ink-3)}
`.trim();

function page({ title, description, robots, canonical, body }) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<meta name="robots" content="${robots}">
${canonical ? `<link rel="canonical" href="${esc(canonical)}">` : ""}
<style>${CSS}</style>
</head>
<body>
<div class="wrap">
${body}
<footer>
<p>PathAhead is an independent, open-source tool. Not affiliated with, endorsed by,
or connected to the Ministry of Education, SEAB, Cambridge Assessment, or any school,
polytechnic, ITE or university.</p>
<p>Data pack ${esc(pack.pack.version)}, published ${esc(pack.pack.published)}.
Every figure cites the institution that published it.
<a href="https://github.com/BaijayantaRoy/path-ahead">Source and data</a>.</p>
</footer>
</div>
</body>
</html>`;
}

/** The fact's own page if it has one, otherwise the source's. A shared link
    repeated beside twenty figures is still twenty figures a reader can check,
    which is the whole point — far better than one list at the bottom. */
const citeUrl = (f) => (f && f.url) || (f && sourceById(f.source)?.url) || null;

function factCite(f, label) {
  if (!f) return "";
  const s = sourceById(f.source);
  const u = citeUrl(f);
  return `<p class="cite">${esc(label)}: ${esc(f.value)}${f.as_of_year ? ` (${f.as_of_year})` : ""}${
    s ? ` — ${esc(s.publisher)}` : ""}${
    u ? ` · <a href="${esc(u)}" rel="noopener nofollow">check the source ↗</a>`
      : (f.basis === "editorial"
          ? ` — PathAhead's own wording, so there is no page to check it against.` : "")}</p>`;
}

function coursePage(o) {
  const g = indexable(o);
  const fee = feeFor(o);
  const ed = o.editorial || {};
  const rel = `${BASE}/courses/${o.id}/`;
  const parts = [];

  parts.push(`<p class="eyebrow"><a href="../../uni/${esc(o.institution_short)}/">${esc(o.institution)}</a></p>`);
  parts.push(`<h1>${esc(o.name)}</h1>`);
  if (o.faculty) parts.push(`<p class="hint">${esc(o.faculty)}</p>`);

  if (!g.ok) {
    const missing = [!g.hasRange ? "a published admission range" : null,
                     !g.hasFee ? "a fee figure" : null].filter(Boolean).join(" and ");
    parts.push(`<div class="note"><strong>This page is incomplete.</strong> PathAhead does not
      yet hold ${esc(missing)} for this course, so it is deliberately not offered to search
      engines — a page that cannot answer the question someone searched for is worse than no
      page at all. Everything PathAhead does hold is below.</div>`);
  }

  if (o.language_requirement) {
    const lr = o.language_requirement;
    parts.push(`<div class="note"><strong>Requires a language.</strong> ${esc(lr.label)}${
      lr.taught_in_language ? " This course is taught substantially in that language." : ""}</div>`);
  }

  parts.push(`<div class="card"><h2>What it is</h2>`);
  parts.push(ed.summary
    ? `<p>${esc(ed.summary)}</p><p class="cite">This description is PathAhead's own, written at
       course-family level rather than for this course specifically.</p>`
    : `<p class="hint">No description held.</p>`);
  if (o.url) parts.push(`<p class="cite">Course details and entry requirements:
    <a href="${esc(o.url)}" rel="noopener nofollow">${esc(o.institution)}'s own page
    for this course ↗</a></p>`);
  parts.push(`</div>`);

  parts.push(`<div class="card"><h2>Last published range</h2>`);
  if (o.band) {
    parts.push(`<p class="fig">${esc(o.band.p10)} to ${esc(o.band.p90)}</p>`);
    if (o.band.basis) parts.push(`<p class="hint">${esc(o.band.basis)}</p>`);
    if (o.band.comparable === false) parts.push(`<p class="hint">Published on a different basis
      from an A-Level score. PathAhead shows it and does not compare the two.</p>`);
    parts.push(factCite(o.band.fact, "Source"));
  } else if (o.banded && o.banded.length) {
    for (const b of o.banded) {
      parts.push(`<ul class="plain">${b.bands.map((x) =>
        `<li>${esc(x.label)}: ${esc(x.share_label ?? (x.share != null ? x.share + "%" : "not published"))}</li>`).join("")}</ul>`);
      parts.push(factCite(b.fact, "Source"));
    }
  } else {
    parts.push(`<p class="hint">This institution publishes no admitted-score range for this
      course. PathAhead does not fill that gap with a figure from anywhere else.</p>`);
  }
  parts.push(`</div>`);

  parts.push(`<div class="card"><h2>Cost, for a Singapore Citizen</h2>`);
  if (fee && fee.basis === "annual") {
    parts.push(`<p class="fig">${money(fee.annual)} a year</p>`);
    if (fee.total) parts.push(`<p>${money(fee.total)} over ${fee.years} years at today's published rate.</p>`);
  } else if (fee) {
    parts.push(`<p class="fig">${money(fee.total)} in total</p>`);
    parts.push(`<p>Charged per credit unit, not per year — ${fee.credits} credits.</p>`);
  } else {
    parts.push(`<p class="hint">${esc(o.fee_note ||
      "PathAhead does not hold a published fee for this course. An absent fee is shown as absent, never as a low one.")}</p>`);
  }
  if (o.cost) {
    const bond = o.cost.bond_years_citizen;
    parts.push(`<p>${bond ? `Accepting the tuition grant commits a citizen to ${bond} years working for a Singapore entity.`
      : "The tuition grant itself carries no service bond for Singapore Citizens."}</p>`);
    parts.push(factCite(o.cost.fact, "Source"));
  }
  parts.push(`</div>`);

  // Places. The app shows this and the static page did not — a field rendered
  // in one and not the other is exactly the drift check_static.mjs exists to
  // catch, and it caught this.
  if (o.intake) {
    parts.push(`<div class="card"><h2>Places</h2>
      <p class="fig">${esc(o.intake.value)}</p>
      <p class="hint">Planned intake for the ${esc(String(o.intake.as_of_year))} exercise.</p>
      ${factCite(o.intake, "Places")}</div>`);
  }

  if (o.accreditation && o.accreditation.length) {
    parts.push(`<div class="card"><h2>Whether you may practise</h2>
      <p>This is a registered profession. The qualification is what opens the register,
      and without registration the work cannot lawfully be done.</p>` +
      o.accreditation.map((a) => `<h2 style="font-size:1rem">${esc(a.body)}</h2>
        <p>${esc(a.label)}</p>${a.detail ? `<p class="hint">${esc(a.detail)}</p>` : ""}
        ${factCite(a.fact, "Accreditation")}`).join("") +
      `<p class="cite">Confirm the current accredited-qualification list with the board
      itself. The register is the authority here, not PathAhead.</p></div>`);
  }

  if (o.duration || (o.progression && o.progression.length)) {
    const bits = [`<div class="card"><h2>Length, and where it leads</h2>`];
    if (o.duration) {
      bits.push(`<p class="fig">${o.duration.years} years</p>`);
      if (o.duration.structure) bits.push(`<p class="hint">${esc(o.duration.structure)}</p>`);
      bits.push(factCite(o.duration.fact, "Duration"));
    }
    for (const p of o.progression || []) {
      bits.push(`<p><strong>${esc(p.label)}</strong>${p.exemption ? ` — ${esc(p.exemption)}` : ""}</p>`);
      if (p.detail) bits.push(`<p class="hint">${esc(p.detail)}</p>`);
      bits.push(factCite(p.fact, "Progression"));
    }
    bits.push(`</div>`);
    parts.push(bits.join("\n"));
  }

  const emp = o.employment;
  if (emp && emp.gross_median) {
    parts.push(`<div class="card"><h2>After it</h2>
      <p class="fig">${money(emp.gross_p25)} – ${money(emp.gross_p75)}</p>
      <p class="hint">Gross monthly salary about six months after graduating. Median
      ${money(emp.gross_median)}. A range, because a median alone says nothing about spread.</p>
      ${emp.employment_rate ? `<p>${emp.employment_rate}% in work within six months.</p>` : ""}
      ${factCite(emp.fact, "Source")}</div>`);
  }

  parts.push(`<div class="card">
    <h2>See this with your own grades</h2>
    <p>PathAhead can show how this course compares with what you actually took, with every
    line of the arithmetic shown. Nothing you type leaves your device.</p>
    <p><a class="btn" href="${BASE}/../index.html#/course/${esc(o.id)}">Open in PathAhead</a>
    ${o.url ? `<a class="btn" href="${esc(o.url)}" rel="noopener nofollow">The institution's own page</a>` : ""}</p>
  </div>`);

  return page({
    title: `${o.name} — ${o.institution} | PathAhead`,
    description: ed.summary
      ? `${o.name} at ${o.institution}. ${ed.summary}`.slice(0, 180)
      : `${o.name} at ${o.institution}: published admission range, fees and sources.`,
    robots: g.ok ? "index, follow" : "noindex, follow",
    canonical: BASE ? rel : "",
    body: parts.join("\n"),
  });
}

function uniPage(short, list) {
  const byFac = {};
  for (const o of list) (byFac[o.faculty || "Other"] ||= []).push(o);
  const withFee = list.filter(feeFor).length;
  const idx = list.filter((o) => indexable(o).ok).length;

  const body = [
    `<p class="eyebrow">${esc(short)}</p>`,
    `<h1>${esc(list[0].institution)}</h1>`,
    `<p class="hint">${list.length} course${list.length === 1 ? "" : "s"} in this data pack.</p>`,
    `<div class="note"><strong>What PathAhead does not hold for ${esc(short)}.</strong>
      A fee figure for ${list.length - withFee} of ${list.length} courses. Those are gaps,
      not zeroes.</div>`,
    ...Object.entries(byFac).sort().map(([fac, os]) => `<div class="card"><h2>${esc(fac)}</h2>
      <ul class="plain">${os.slice().sort((a, b) => a.name.localeCompare(b.name))
        .map((o) => `<li><a href="../../courses/${esc(o.id)}/">${esc(o.name)}</a>${
          indexable(o).ok ? "" : ` <span class="hint">— incomplete</span>`}</li>`).join("")}</ul></div>`),
  ].join("\n");

  return page({
    title: `${list[0].institution} — courses | PathAhead`,
    description: `Every ${short} course in the PathAhead data pack, with published admission ranges, fees and sources.`,
    robots: idx > 0 ? "index, follow" : "noindex, follow",
    canonical: BASE ? `${BASE}/uni/${short}/` : "",
    body,
  });
}

function indexPage(byInst, stats) {
  const body = [
    `<h1>PathAhead — Singapore education pathways</h1>`,
    `<p class="hint">${pack.outcomes.length} destinations across ${Object.keys(byInst).length}
      institutions, every figure cited to the institution that published it.</p>`,
    `<div class="note">${stats.indexable} of ${pack.outcomes.length} course pages are complete
      enough to be offered to search engines. The rest are published but marked
      <code>noindex</code> until PathAhead holds both a published admission range and a fee
      figure for them.</div>`,
    `<div class="card"><h2>Institutions</h2><ul class="plain">${
      Object.entries(byInst).sort().map(([k, v]) =>
        `<li><a href="uni/${esc(k)}/">${esc(v[0].institution)}</a> — ${v.length} courses</li>`).join("")
    }</ul></div>`,
    `<div class="card"><h2>Work it out with your own grades</h2>
      <p><a class="btn" href="../index.html#/">Open PathAhead</a></p></div>`,
  ].join("\n");
  return page({
    title: "PathAhead — understand the path ahead",
    description: "Singapore education pathways: published admission ranges, fees and graduate outcomes, each cited to its source.",
    robots: "index, follow",
    canonical: BASE ? `${BASE}/` : "",
    body,
  });
}

/* ---------------------------------------------------------------- build */
const byInst = {};
for (const o of pack.outcomes) (byInst[o.institution_short] ||= []).push(o);

const stats = { total: pack.outcomes.length, indexable: 0, noRange: 0, noFee: 0 };
for (const o of pack.outcomes) {
  const g = indexable(o);
  if (g.ok) stats.indexable++;
  if (!g.hasRange) stats.noRange++;
  if (!g.hasFee) stats.noFee++;
}

if (REPORT_ONLY) {
  console.log(`  ${stats.indexable} of ${stats.total} course pages would be indexable`);
  console.log(`  ${stats.noFee} lack a fee figure`);
  console.log(`  ${stats.noRange} lack a published admission range`);
  console.log(`\n  The gate is per page: as the pack fills in, pages flip to indexable`);
  console.log(`  on their own. No re-run of anything else is needed.`);
  process.exit(0);
}

rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });

let written = 0;
for (const o of pack.outcomes) {
  const dir = join(OUT, "courses", o.id);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "index.html"), coursePage(o), "utf8");
  written++;
}
for (const [short, list] of Object.entries(byInst)) {
  const dir = join(OUT, "uni", short);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "index.html"), uniPage(short, list), "utf8");
  written++;
}
writeFileSync(join(OUT, "index.html"), indexPage(byInst, stats), "utf8");
written++;

/* robots.txt and a sitemap listing ONLY the indexable pages. A sitemap that
   advertises a page marked noindex is a contradiction a crawler will notice.

   Both are written to the DEPLOY ROOT, not to OUT. The static pages live in
   web/site/, but GitHub Pages publishes web/ as the site root -- so a
   robots.txt inside web/site/ lands at /site/robots.txt, which is not a
   place any crawler looks. It was written there until 2026-08-14, which
   meant the careful noindex work on 98 incomplete pages was resting on a
   directive nothing ever read. */
const urls = pack.outcomes.filter((o) => indexable(o).ok).map((o) => `${BASE}/courses/${o.id}/`);
const DEPLOY_ROOT = join(REPO, "web");
writeFileSync(join(DEPLOY_ROOT, "sitemap.txt"), urls.join("\n") + "\n", "utf8");
writeFileSync(join(DEPLOY_ROOT, "robots.txt"),
  `User-agent: *\nAllow: /\n${BASE ? `Sitemap: ${BASE}/sitemap.txt\n` : ""}`, "utf8");

console.log(`  wrote ${written} pages to ${OUT.replace(REPO + "/", "")}`);
console.log(`  ${stats.indexable} indexable · ${stats.total - stats.indexable} noindex ` +
            `(${stats.noFee} missing a fee, ${stats.noRange} missing a range)`);
console.log(`  sitemap lists ${urls.length} URLs`);
if (!BASE) {
  console.log("  note: no --base given, so robots.txt omits the Sitemap: line " +
              "(CI passes --base; a local build does not need it)");
}

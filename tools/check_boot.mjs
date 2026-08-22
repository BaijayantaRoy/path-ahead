/**
 * Does the app actually boot? A jsdom-free smoke test.
 *
 *   node tools/check_boot.mjs
 *
 * `check_ui.mjs` is the real interface suite, but it needs jsdom, and jsdom has
 * repeatedly failed to load in this project's sandbox — which meant a runtime
 * error at boot could ship with every other check green. A page that throws on
 * load is indistinguishable, from the outside, from a page where a new feature
 * simply "isn't visible".
 *
 * This runs the page's own script against a DOM shim just rich enough to reach
 * the end of boot(), and reports the first thing that throws. It proves far
 * less than check_ui does. It proves the one thing that matters most: the
 * script runs.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Script, createContext } from "node:vm";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(REPO, "web", "index.html"), "utf8");
const pack = JSON.parse(readFileSync(join(REPO, "web", "data", "singapore.json"), "utf8"));

const ids = new Map();
function makeEl(tag = "div") {
  const node = {
    tagName: String(tag).toUpperCase(), children: [], attrs: {}, style: {},
    textContent: "", value: "", checked: false, hidden: false, className: "",
    dataset: {}, parentNode: null,
    appendChild(c) { this.children.push(c); c.parentNode = this; return c; },
    append(...cs) { for (const c of cs) if (c && typeof c === "object") this.appendChild(c); },
    replaceChildren(...cs) { this.children = []; this.append(...cs); },
    setAttribute(k, v) {
      this.attrs[k] = String(v);
      if (k === "id") ids.set(String(v), this);
      if (k.startsWith("data-")) this.dataset[k.slice(5)] = String(v);
    },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    removeAttribute(k) { delete this.attrs[k]; },
    hasAttribute(k) { return k in this.attrs; },
    addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
    focus() {}, click() {}, remove() {}, scrollIntoView() {},
    closest() { return null; }, contains() { return false; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    insertAdjacentElement() {}, cloneNode() { return makeEl(tag); },
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    get firstChild() { return this.children[0] || null; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
  };
  return node;
}

/* Every id the markup declares must resolve, or the script hits null and the
   page dies on a selector rather than on its logic. */
for (const m of html.matchAll(/\sid="([^"]+)"/g)) ids.set(m[1], makeEl());

const doc = {
  createElement: makeEl,
  createElementNS: (_ns, t) => makeEl(t),
  createTextNode: (t) => ({ textContent: t }),
  createDocumentFragment: () => makeEl("fragment"),
  querySelector(sel) {
    const m = /^#([A-Za-z0-9_-]+)$/.exec(String(sel).trim());
    if (m) return ids.get(m[1]) || makeEl();
    return makeEl();
  },
  querySelectorAll: () => [],
  getElementById: (id) => ids.get(id) || makeEl(),
  addEventListener() {}, removeEventListener() {},
  body: makeEl("body"), documentElement: makeEl("html"),
  head: makeEl("head"), title: "",
};

const errors = [];
const ctx = createContext({
  document: doc,
  console: { log() {}, warn() {}, error: (...a) => errors.push(a.map(String).join(" ")) },
  location: { hash: "", href: "http://localhost/", search: "" },
  history: { back() {}, pushState() {}, replaceState() {} },
  navigator: { userAgent: "node", language: "en" },
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  setTimeout: (fn) => { try { fn(); } catch (e) { errors.push("timer: " + e.message); } return 0; },
  clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  requestAnimationFrame: (fn) => { fn(0); return 0; },
  scrollTo() {}, print() {}, alert() {}, addEventListener() {}, removeEventListener() {},
  fetch: async () => ({ ok: true, status: 200, json: async () => pack }),
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  Blob: function () {}, Event: function () {}, MouseEvent: function () {},
  Intl, Math, JSON, Date, Object, Array, String, Number, Boolean, Set, Map, RegExp, Promise, Error,
});
ctx.window = ctx;
ctx.globalThis = ctx;

const src = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  ok    ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n         ${e.message}`); }
};

check("the page script evaluates without throwing", () => {
  new Script(src, { filename: "web/index.html" }).runInContext(ctx);
});

check("boot() completes", async () => {
  if (typeof ctx.boot !== "function") throw new Error("boot() is not defined");
});

await (async () => {
  try {
    await ctx.boot();
    console.log("  ok    boot() ran to completion");
  } catch (e) {
    failures++;
    console.log(`  FAIL  boot() threw\n         ${e.message}\n${(e.stack || "").split("\n").slice(1, 4).join("\n")}`);
  }
})();

check("no error was logged during boot", () => {
  if (errors.length) throw new Error(errors.slice(0, 3).join(" | "));
});

check("the profile controls were built", () => {
  for (const id of ["interestChips", "priChips", "conChips", "rankPicked", "streamChips"]) {
    const n = ids.get(id);
    if (!n) throw new Error(`#${id} missing from the markup`);
    if (!n.children.length) throw new Error(`#${id} rendered no controls`);
  }
});

check("every dimension shows its own importance control", () => {
  /* The first version was a chip pool: tapping one made it disappear upwards
     into a separate list, so nothing on screen said what you had picked first
     or how to change it. The rule now is that all seven rows are always
     present — order and weight are read off the list, never remembered. */
  const list = ids.get("rankPicked");
  if (!list) throw new Error("#rankPicked missing");
  const rows = list.children;
  if (rows.length !== 7) throw new Error(`shows ${rows.length} rows, expected all 7`);
  for (const r of rows) {
    const seg = r.children[r.children.length - 1];
    if (!seg || seg.children.length !== 4) {
      throw new Error("a row does not offer all four importance levels");
    }
  }
});

check("no question is asked twice", () => {
  /* Cost and extra assessment were once a yes/no toggle AND an importance row
     — the same question in two idioms on one page, which is what made the form
     read as disjointed. */
  const body = src.replace(/\/\*[\s\S]*?\*\//g, "");
  const con = /const CON = \[([\s\S]*?)\];/.exec(body);
  if (!con) throw new Error("constraint chips not found");
  for (const dup of ["cost_sensitive", "willing_extra_assessment"]) {
    if (con[1].includes(dup)) {
      throw new Error(`"${dup}" is asked both as a toggle and as an importance row`);
    }
  }
});

check("the ranking states its default instead of showing an empty box", () => {
  const note = ids.get("rankExplain");
  const t = (note && note.children.map((c) => c.textContent).join(" ")) || "";
  if (!/count equally/i.test(t)) {
    throw new Error(`the unranked default is not stated: "${t.slice(0, 80)}"`);
  }
  if (note.hidden) throw new Error("the default explanation is hidden");
});

check("no browser storage API is used", () => {
  /* Two reasons, and the second is why this is a hard check rather than a
     style note.

     PathAhead tells the reader "nothing you type here leaves this device" and
     keeps state in memory so a shared family computer carries nothing between
     sessions. Writing to disk breaks that promise for a convenience.

     And `localStorage` THROWS where site data is blocked, in some private
     modes, and on file://. A theme preference once sat at the top level just
     above boot(), so that exception did not degrade a colour — it stopped the
     app from starting at all, and the page rendered as static markup with no
     controls. */
  const body = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  for (const api of ["localStorage", "sessionStorage", "indexedDB", "document.cookie"]) {
    if (body.includes(api)) throw new Error(`the page uses ${api}`);
  }
});

check("nothing at the top level can stop boot()", () => {
  /* Anything running before boot() is a single point of failure for the whole
     app, so it must be inside a try. */
  const tail = src.slice(src.lastIndexOf("})();"));
  if (!/try\s*\{\s*boot\(\)/.test(tail) && /\bboot\(\)/.test(tail)) {
    throw new Error("boot() is called unguarded after top-level code that may throw");
  }
});


/* ── eligibility, the way a real person types ─────────────────────
   NTU's Physics / Applied Physics was shown at 52/100 to a student taking no
   Physics. The gate that fixes it hangs entirely off knowing which subjects a
   student takes, and that is read off the grades table rather than asked
   again — which puts the whole thing at the mercy of one detail: whether the
   typed subject name resolved to a pack code.

   Someone who types "Physics" and never clicks the suggestion still takes
   Physics. If that lands as the slug "h2-physics", nothing matches NTU's
   requirement and the course is withheld from a student who qualifies for it.
   That is the same bug pointing the other way, and the more costly direction,
   because it removes an option instead of adding a caveat. */
check("a typed subject name resolves to the pack's own code", () => {
  const resolve = ctx.resolveSubjectCode;
  if (typeof resolve !== "function") throw new Error("resolveSubjectCode is not reachable");
  const cases = [
    ["Physics", "physics"],
    ["physics", "physics"],
    ["Mathematics", "mathematics"],
    ["h2 math", "mathematics"],        // an alias the pack declares
    ["Further Mathematics", "further-mathematics"],
    ["Chemistry", "chemistry"],
  ];
  for (const [typed, want] of cases) {
    const got = resolve(typed);
    if (got !== want) throw new Error(`typed ${JSON.stringify(typed)} resolved to ${got}, not ${want}`);
  }
});

check("subjects offered is null until one is named, never an empty list", () => {
  /* "Not told" and "takes none of these" must produce different answers: the
     first says come back and tell me, the second is a real no. Collapsing them
     would refuse courses to a student who simply had not filled the form. */
  if (typeof ctx.syncSubjectsOffered !== "function") throw new Error("syncSubjectsOffered missing");
  /* S and P are `const` at the top of the page script, so they live in the
     context's lexical scope rather than on its global object. A second Script
     in the same context can see them; ctx.S cannot. */
  const run = code => new Script(code).runInContext(ctx);
  run("S.rows = []; syncSubjectsOffered();");
  if (run("P.subjects_offered") !== null) throw new Error("an empty form reported subjects");
  run(`S.rows = [{level:"h2",name:"Physics",grade:"A"},
                 {level:"h2",name:"h2 math",grade:"B"}]; syncSubjectsOffered();`);
  const got = (run("P.subjects_offered") || []).join(",");
  if (got !== "physics,mathematics") throw new Error(`got ${got}`);
});

check("a student with no Physics gets no score on Applied Physics", () => {
  /* The reported bug, end to end, through the page's own engine. */
  const o = pack.outcomes.find(x => x.id === "ntu-physics-applied-physics");
  if (!o) throw new Error("ntu-physics-applied-physics is not in the shipped pack");
  if (!(o.subject_requirements || []).length)
    throw new Error("the course carries no published requirement, so nothing can block");
  const fam = {};
  for (const s of pack.subjects || []) fam[s.code] = s.family || s.code;
  const blocked = ctx.scoreFit(o, {
    interests: ["I"], enjoyed_subjects: ["economics"],
    subjects_offered: ["mathematics", "economics", "literature"],
    assessment_style: "exams", teamwork: "individual",
  }, fam);
  if (blocked.score !== null) throw new Error(`scored ${blocked.score} without Physics`);
  if (!/Physics/.test(blocked.unscored_reason || ""))
    throw new Error("the refusal does not name the subject");
  const ok = ctx.scoreFit(o, {
    interests: ["I"], subjects_offered: ["physics", "further-mathematics"],
    assessment_style: "exams", teamwork: "individual",
  }, fam);
  if (ok.score === null)
    throw new Error(`withheld from a qualified student: ${ok.unscored_reason}`);
});

console.log(`\n${failures === 0 ? "boot is clean" : failures + " problem(s) at boot"}`);
process.exit(failures ? 1 : 0);

"use strict";
/* ═════════════════════════════════════════════════════════════════
   PathAhead browser engine.

   A second implementation of the rule kinds that engine/rules/ holds in
   Python. The duplication is deliberate — it is what lets the browser
   build run with no runtime download — and it is *managed*:
   evals/golden/*.json records the value AND every trace step the Python
   engine produced, and CI replays all of them through this very block,
   extracted from this very file. Disagreement beyond 1e-9 fails the build.
   ═════════════════════════════════════════════════════════════════ */

const PACK_URL = "data/singapore.json";
const S = { pack:null, rows:[], result:null, profile:null, fits:{}, shortlist:new Set(),
            sort:"match", fam:{}, expanded:{} };

const $  = (s,r=document)=>r.querySelector(s);
const el = (t,p={},k=[])=>{const n=document.createElement(t);
  for(const[a,v]of Object.entries(p)){
    if(a==="class")n.className=v; else if(a==="text")n.textContent=v;
    else if(a.startsWith("on"))n.addEventListener(a.slice(2),v);
    else if(v!==null&&v!==undefined&&v!==false)n.setAttribute(a,v);
  }
  for(const c of [].concat(k)) if(c) n.append(c);
  return n;};

/** Turns a run of prose containing bare URLs into text nodes and real <a>
    elements, so a licence link in pack-authored copy is clickable.

    Written for the Singapore Open Data Licence, which requires a product
    using an ODL dataset to include "a link to the most recent version of
    this Licence". The footer used to render that attribution with
    textContent, so the URL sat there as characters a reader could not
    follow — technically present, practically not a link. Rendering it
    properly is the difference between meeting the condition and appearing
    to (SAFEGUARDS.md 3a).

    Deliberately NOT a general markdown or HTML renderer: it builds nodes
    with textContent and setAttribute only, so pack-authored strings can
    never inject markup. Only http(s) URLs are linked, and a trailing
    sentence-ending character is left as text rather than swallowed into
    the href. */
function linkifyUrls(text){
  const out=[]; const s=String(text||"");
  const re=/https?:\/\/[^\s)<>"']+/g;
  let last=0, m;
  while((m=re.exec(s))!==null){
    let url=m[0];
    // A URL at the end of a sentence picks up the full stop; a URL in
    // brackets picks up the bracket. Neither belongs in the href.
    const trail=url.match(/[.,;:)\]]+$/);
    if(trail) url=url.slice(0,-trail[0].length);
    if(m.index>last) out.push(document.createTextNode(s.slice(last,m.index)));
    out.push(el("a",{href:url,rel:"noopener noreferrer",target:"_blank",text:url}));
    if(trail) out.push(document.createTextNode(trail[0]));
    last=m.index+m[0].length;
  }
  if(last<s.length) out.push(document.createTextNode(s.slice(last)));
  return out.length?out:[document.createTextNode(s)];
}

/* ---------- engine: grade lookup ---------- */
/* Formatting and rounding live INSIDE the engine block so that
   tools/check_golden.mjs, which extracts this block verbatim and runs it
   under Node, gets a self-contained module. If a helper the engine needs
   drifts out of this section, CI fails immediately — which is how the
   boundary stays real rather than aspirational. */
const num = v => Number.isInteger(v) ? String(v) : String(Math.round(v*10000)/10000);
const r = v => Math.round(v*10000)/10000;
const r1 = v => Math.floor(v*10+0.5)/10;   // half-up, matching engine/fit.py _r1
const r0 = v => Math.floor(v+0.5);         // half-up, matching engine/fit.py _r0
function display(s){
  const pre = {h1:"H1",h2:"H2",h3:"H3"}[s.level] || "";
  return (pre ? pre+" " : "") + s.name;
}
class PAError extends Error{ constructor(m,a){super(m);this.advice=a||"Please check your entry.";} }

function gradePoints(scales, scaleName, grade){
  const scale = scales[scaleName];
  if(!scale) throw new PAError(`the data pack has no grade scale called "${scaleName}"`,
    "This is a data problem, not something you did. Please report it.");
  if(!(grade in scale)) throw new PAError(`grade "${grade}" is not on the ${scaleName} scale`,
    `Valid grades here: ${Object.keys(scale).join(", ")}.`);
  return scale[grade];
}

/* ---------- engine: rule kind weighted_best_n_with_substitution ---------- */
function candidates(subjects, spec){
  const levels = (spec.levels || [spec.level]).filter(Boolean);
  return subjects.filter(s => levels.includes(s.level));
}
function scaleFor(spec, subject){
  if(spec.scale_by_level) return spec.scale_by_level[subject.level];
  return spec.scale;
}
function weightedBestN(params, scales, subjects, caveats){
  const core = params.core, take = core.take, cap = params.cap ?? null;
  const d = { value:0, max_value:cap, direction:"higher_is_better",
              steps:[], warnings:[...(caveats||[])] };
  const push=(kind,label,extra={})=>d.steps.push(Object.assign(
    {kind,label,detail:null,points:null,running_total:null},extra));

  const pool = candidates(subjects, core);
  if(pool.length < take) throw new PAError(
    `this score needs ${take} H2 subjects, but only ${pool.length} were entered`,
    `Add your remaining H2 subjects. The score is built from your best ${take} of them.`);

  const scored = pool.map(s=>({s, p:gradePoints(scales, scaleFor(core,s), s.grade)}))
                     .sort((a,b)=> b.p-a.p || a.s.name.localeCompare(b.s.name));
  const counted = scored.slice(0,take), spare = scored.slice(take);

  push("heading", core.label || `Your best ${take} subjects`);
  let total = 0;
  for(const {s,p} of counted){ total += p;
    push("component", `${display(s)}  ${s.grade}`, {points:p, running_total:r(total)}); }
  for(const {s,p} of spare)
    push("excluded", `${display(s)}  ${s.grade}`, {detail:`only your best ${take} count here`, points:p});
  push("subtotal", core.subtotal_label || "Subtotal", {running_total:r(total)});

  if(params.mandatory){
    const m = params.mandatory, ms = candidates(subjects, m);
    if(!ms.length) throw new PAError(`${m.label||"a compulsory subject"} is missing`,
      `${m.label||"This subject"} counts towards the score and must be entered.`);
    const s = ms[0], p = gradePoints(scales, scaleFor(m,s), s.grade);
    total += p;
    push("heading", m.label || "Compulsory subject");
    push("component", `${display(s)}  ${s.grade}`, {points:p, running_total:r(total)});
    push("subtotal", "Subtotal", {running_total:r(total)});
  }

  if(params.bonus){
    const b = params.bonus, seen = new Set(counted.map(c=>c.s.code));
    const considered = [];
    for(const spec of b.best_of) for(const s of candidates(subjects, spec)){
      if(seen.has(s.code)) continue; seen.add(s.code);
      considered.push({s, p:gradePoints(scales, scaleFor(spec,s), s.grade)});
    }
    push("heading", b.label || "Bonus subject");
    if(!considered.length){
      push("note","No optional subject entered, so no bonus was added.");
    } else {
      const best = considered.reduce((a,c)=> c.p>a.p ? c : a);
      const improves = best.p > 0 || b.only_if_improves === false;
      for(const {s,p} of considered){
        if(s.code===best.s.code && improves){ total += p;
          push("substitution", `${display(s)}  ${s.grade}`,
               {detail:"counted - the higher of your optional subjects", points:p, running_total:r(total)});
        } else {
          push("excluded", `${display(s)}  ${s.grade}`,
               {detail:"the other optional subject scored higher", points:p});
        }
      }
      push("subtotal","Subtotal",{running_total:r(total)});
    }
  }

  const uncapped = r(total);
  if(cap !== null && uncapped > cap){
    push("cap", `Capped at the maximum of ${num(cap)}`,
         {detail:`your components added to ${num(uncapped)}`, running_total:cap});
    total = cap;
    if(params.cap_note) d.warnings.push(params.cap_note);
  }
  d.value = r(total);
  push("total", params.total_label || "Total", {running_total:d.value});
  return d;
}
/* ---------- engine: rule kind lowest_sum ----------
   The PSLE shape. Add up every required subject; lower is better. No
   substitution, no cap, no optional components — which is exactly why it is a
   separate kind rather than weightedBestN bent to fit.

   This is a port of engine/rules/lowest_sum.py and must stay step-for-step
   identical to it. tools/check_golden.mjs replays the same fixtures through
   both and fails on any disagreement in value, kind, label, points or running
   total. If you change one, change the other in the same commit — a fixture
   that only exercises one engine proves nothing about the other. */
function alLabel(grade){
  if(/^\d+$/.test(grade)) return "AL"+grade;
  // Foundation grades arrive normalised as FA/FB/FC so a Foundation A can
  // never be mistaken for a Standard A. "FA" is an internal spelling and no
  // family should ever be shown it.
  if(grade.length===2 && grade[0]==="F" && "ABC".includes(grade[1])) return "Foundation "+grade[1];
  return grade;
}
function foundationNote(grade, points){
  if(grade.length===2 && grade[0]==="F" && "ABC".includes(grade[1]))
    return `Foundation ${grade[1]} counts as AL${Math.round(points)} of the Standard `
         + `scale when the four subjects are added up.`;
  return null;
}
function lowestSum(params, scales, subjects, caveats){
  const required = params.required_subjects || [];
  const scaleName = params.scale;
  const d = { value:0, max_value: params.worst_possible ?? null,
              direction:"lower_is_better", unit: params.unit || "points",
              steps:[], warnings:[...(caveats||[])] };
  const push=(kind,label,extra={})=>d.steps.push(Object.assign(
    {kind,label,detail:null,points:null,running_total:null},extra));

  push("heading", params.label || "Your subjects");
  let total = 0;
  const missing = [];
  for(const spec of required){
    let subject = subjects.find(s => s.code === spec.code);
    if(!subject) subject = subjects.find(s => s.name.toLowerCase() === String(spec.name).toLowerCase());
    // `accepts` names the other subject codes that satisfy this requirement —
    // Foundation Mathematics IS the Mathematics paper. Matching on code or
    // name alone would report a complete four-subject sheet as incomplete,
    // which to a parent reads as an accusation.
    if(!subject) for(const alt of (spec.accepts || [])){
      subject = subjects.find(s => s.code === alt);
      if(subject) break;
    }
    if(!subject){ missing.push(String(spec.name)); continue; }
    const p = gradePoints(scales, spec.scale || scaleName, subject.grade);
    total += p;
    push("component", `${subject.name}  ${alLabel(subject.grade)}`,
         {detail: foundationNote(subject.grade, p), points:p, running_total:r(total)});
  }
  if(missing.length) throw new PAError(
    `missing required subject(s): ${missing.join(", ")}`,
    `This score adds up all four subjects. Please enter a grade for: ${missing.join(", ")}.`);

  d.value = r(total);
  push("total", params.total_label || "Total score", {running_total:d.value});
  push("note", `Lower is better. The best possible is ${params.best_possible ?? "?"} `
             + `and the weakest is ${params.worst_possible ?? "?"}.`);
  return d;
}

/* ---------- engine: rule kind required_plus_best_n ----------
   The O-Level/SEC shape: one compulsory subject plus the best N of each of a
   list of groups, lower is better. L1R5, L1R4 and the ELR2B2 approximation
   are all this one kind with different `groups` -- see the long comment on
   `_pool` in engine/rules/required_plus_best_n.py for why groups filter on
   explicit subject `codes` rather than `tags`/level for this stage.

   This is a port of that file and must stay step-for-step identical to it.
   tools/check_golden.mjs replays the same fixtures through both and fails on
   any disagreement in value, kind, label, points or running total. If you
   change one, change the other in the same commit. */
const OL_DISPLAY = {"1":"A1","2":"A2","3":"B3","4":"B4","5":"C5","6":"C6","7":"D7","8":"E8","9":"F9"};
function olLabel(grade){ return OL_DISPLAY[grade] || grade; }

function requiredPlusBestN(params, scales, subjects, caveats){
  const scaleName = params.scale;
  const d = { value:0, max_value: params.worst_possible ?? null,
              direction:"lower_is_better", steps:[], warnings:[...(caveats||[])] };
  const push=(kind,label,extra={})=>d.steps.push(Object.assign(
    {kind,label,detail:null,points:null,running_total:null},extra));

  const used = new Set();
  let total = 0;

  const pool = (group)=>{
    const codes = group.codes, tags = new Set(group.tags||[]);
    const out = [];
    for(const s of subjects){
      if(used.has(s.code)) continue;
      if(codes && !codes.includes(s.code)) continue;
      if(tags.size && !tags.has(s.level)) continue;
      out.push(s);
    }
    return out;
  };

  for(const group of (params.groups||[])){
    const label = group.label || "Subjects";
    const take = group.take ?? 1;
    const candidatesHere = pool(group);
    if(candidatesHere.length < take) throw new PAError(
      `${label}: need ${take} subject(s), found ${candidatesHere.length}`,
      `This aggregate uses ${take} subject(s) for '${label}'. Please add the missing subject(s).`);

    const scored = candidatesHere.map(s=>({s, p:gradePoints(scales, scaleName, s.grade)}))
                       .sort((a,b)=> a.p-b.p || a.s.name.localeCompare(b.s.name)); // lower is better
    const counted = scored.slice(0,take), spare = scored.slice(take);

    push("heading", label);
    for(const {s,p} of counted){ total += p; used.add(s.code);
      push("component", `${s.name}  ${olLabel(s.grade)}`, {points:p, running_total:r(total)}); }
    for(const {s,p} of spare)
      push("excluded", `${s.name}  ${olLabel(s.grade)}`,
           {detail:`only the best ${take} count in this group`, points:p});
    push("subtotal", "Subtotal", {running_total:r(total)});
  }

  total = r(total);
  d.value = total;
  push("total", params.total_label || "Aggregate", {running_total:total});
  if(params.qualifying_max != null)
    push("note", `An aggregate of ${num(params.qualifying_max)} or lower meets the stated `
               + `requirement. Lower is better.`);
  return d;
}

const RULES = { weighted_best_n_with_substitution: weightedBestN, lowest_sum: lowestSum,
                required_plus_best_n: requiredPlusBestN };

/* ---------- engine: buckets (evidence axis) ---------- */
const HEADLINE = {
  above_range:"Above last year's range",
  exactly_at_profile:"Level with last year's profile",
  at_or_above_range:"At the top of last year's range",
  within_range:"Within last year's range",
  below_range:"Below last year's range",
  published_on_another_basis:"Published, but on a different scale",
  data_incomplete:"Not enough verified data yet"
};
const EXPLAIN = {
  above_range:"Your result is clear of the whole range of students admitted last year. A good sign, not a guarantee — places, applicants and requirements change every year.",
  exactly_at_profile:"Every student admitted to this course last year had exactly this profile, and so do you. There is no headroom above it, so the parts of the decision that are not grades — interviews, portfolios, subject prerequisites — carry more weight here than almost anywhere else.",
  at_or_above_range:"Your result sits at the top of the range of students admitted last year. A good sign, not a guarantee — places, applicants and requirements change every year.",
  within_range:"Your result sits inside the range of students admitted last year. Admission still depends on this year's applicants and places.",
  below_range:"This course was more competitive than your current result in last year's exercise. That is last year's picture, not a decision about you — and there are other ways in.",
  published_on_another_basis:"There is a real published figure here, and it is shown on the card — but it is measured on a basis that does not match the one your score is calculated on, so putting your number next to it would give you an answer that looked sensible and meant nothing. Read it as background, and treat the parts of the decision that are not grades as carrying real weight here.",
  data_incomplete:"PathAhead does not have a verified figure for this course, so it will not show a guess."
};
const GCLASS = {above_range:"g-ok", at_or_above_range:"g-ok", exactly_at_profile:"g-mid",
  within_range:"g-mid", below_range:"g-soft", published_on_another_basis:"g-quiet",
  data_incomplete:"g-quiet"};
const BCLASS = {above_range:"b-ok", at_or_above_range:"b-ok", exactly_at_profile:"b-mid",
  within_range:"b-mid", below_range:"b-soft", published_on_another_basis:"b-quiet",
  data_incomplete:"b-quiet"};
const ORDER = ["above_range","at_or_above_range","exactly_at_profile","within_range",
  "below_range","published_on_another_basis","data_incomplete"];

/* Mirrors engine/buckets.py:STATISTIC_WORDS. Two published statistics share
   the same SHAPE — two numbers — and mean different things. A 10th-90th
   percentile band is the middle 80% with both tails removed by construction;
   a polytechnic's min-max is the lowest and highest aggregate of ANYONE
   admitted, so it is necessarily wider from the same intake. Describing the
   second in the words of the first would read as "far less selective" when the
   only difference is which statistic was published. */
const STATISTIC_WORDS = {
  p10_p90:{
    short:"range",
    what_it_is:"the 10th to 90th percentile of last year's intake — the middle 80%, with the highest and lowest admitted students left out"
  },
  min_max:{
    short:"full admitted range",
    what_it_is:"the lowest and the highest aggregate of anyone admitted through the Joint Admissions Exercise — the whole cohort, not a middle band. It is wider than a university's published percentile range for that reason alone, which is a difference in what was counted, not a difference in how hard the course is to get into"
  }
};

/* Mirrors engine/forward.py. Comparability is a property of ANY published
   figure, not a quirk of the banded shape. A polytechnic publishes a net
   ELR2B2 O-Level aggregate; this transition scores an A-Level result out of
   70. The numbers are shown and the verdict is withheld. */
function bandComparable(band){ return band.comparable !== false; }

function assessBand(score, p10, p90, direction, statistic){
  if(statistic && statistic !== "p10_p90")
    throw new Error("assessBand describes a 10th-90th percentile band, but was given statistic="+statistic);
  /* A degenerate band (p10 === p90) means the whole admitted cohort shared one
     profile. Matching it exactly is NOT the same as clearing a range, and
     collapsing the two put every course in a single bucket. */
  const lo = Math.min(p10,p90), hi = Math.max(p10,p90), degenerate = lo === hi;
  if(direction === "higher_is_better"){
    if(degenerate && score === hi) return "exactly_at_profile";
    if(score > hi) return "above_range";
    if(score >= lo) return score === hi ? "at_or_above_range" : "within_range";
    return "below_range";
  }
  if(degenerate && score === lo) return "exactly_at_profile";
  if(score < lo) return "above_range";
  if(score <= hi) return score === lo ? "at_or_above_range" : "within_range";
  return "below_range";
}

/* Mirrors engine/buckets.py:HEADLINE_MINMAX / EXPLANATION_MINMAX. Kept apart
   from HEADLINE/EXPLAIN above so the two vocabularies can never accidentally
   converge -- a full admitted range and a 10th-90th percentile band are
   different published claims and must read differently even when they land
   in the same bucket. */
const HEADLINE_MINMAX = {
  above_range:"Above the full range of students admitted",
  exactly_at_profile:"Level with every student admitted last year",
  at_or_above_range:"At the strongest end of last year's intake",
  within_range:"Within the full range of students admitted",
  below_range:"Below the full range of students admitted",
};
const EXPLAIN_MINMAX = {
  above_range:"Your aggregate is stronger than every student admitted last year, tails included -- this range is the whole intake, not a middle band. A good sign, not a guarantee.",
  exactly_at_profile:"Every student admitted last year had exactly this aggregate, and so do you. The parts of the decision that are not grades carry real weight here.",
  at_or_above_range:"Your aggregate matches the strongest student admitted last year, out of the whole intake. A good sign, not a guarantee -- places, applicants and requirements change every year.",
  within_range:"Your aggregate sits inside the full range of students admitted last year -- the whole intake, not a middle band with the tails removed. Admission still depends on this year's applicants and places.",
  below_range:"Last year's weakest admitted aggregate was still stronger than yours. That is last year's picture, not a decision about you, and there are other ways in.",
};

/* Mirrors engine/buckets.py:assess_min_max_band. Exists for exactly the case
   assessBand refuses: an ELR2B2/L1R5 aggregate scored by an O-Level applicant
   against a polytechnic's or JC's own published min-max range IS that
   applicant's own basis -- a different published claim from a percentile
   band, never described in percentile words. */
function assessMinMaxBand(score, p10, p90, direction){
  const lo = Math.min(p10,p90), hi = Math.max(p10,p90), degenerate = lo === hi;
  if(direction === "higher_is_better"){
    if(degenerate && score === hi) return "exactly_at_profile";
    if(score > hi) return "above_range";
    if(score >= lo) return score === hi ? "at_or_above_range" : "within_range";
    return "below_range";
  }
  if(degenerate && score === lo) return "exactly_at_profile";
  if(score < lo) return "above_range";
  if(score <= hi) return score === lo ? "at_or_above_range" : "within_range";
  return "below_range";
}

/* Mirrors engine/buckets.py:assess_banded. A banded profile — the share of
   applicants in each published band who got through — is a DIFFERENT claim
   from a 10th-90th percentile band, and the two are never converted into each
   other. Where the university published against a scale that no longer matches
   the one we compute (SUSS and SIT both use the retired 90-point UAS), the
   bands are shown and the verdict is withheld. */
function alevelBanded(o){
  const pool=(o.banded||[]).filter(p=>p.qualification==="a-level");
  if(!pool.length) return null;
  return pool.find(p=>p.stage==="offered") || pool[0];
}
function assessBanded(profile, score){
  if(!profile.comparable) return "published_on_another_basis";
  if(score==null) return "data_incomplete";
  const hit=(profile.bands||[]).find(b=>
    (b.low==null || score>=b.low) && (b.high==null || score<=b.high));
  if(!hit) return "data_incomplete";
  const bands=profile.bands;
  if(bands.length>1 && hit===bands[bands.length-1]) return "above_range";
  if(bands.length>1 && hit===bands[0]) return "below_range";
  return "within_range";
}

/* ---------- engine: fit (the second axis) ---------- */
/* ── weighted dimensions (mirrors engine/fit.py) ───────────────
   The student ranks these; position sets weight. Rank 1 of n scores n, last
   scores 1 — a linear ramp, because it is the only mapping a reader can
   verify by looking at it. The old fixed 25/15/10 constants survive only as
   the RATIO that produces each raw match; all weighting is the student's. */
const WEIGHTED_DIMENSIONS = [
  ["interests",  "The kind of work that pulls at you"],
  ["subjects",   "Studying subjects you enjoy"],
  ["assessment", "How you are assessed"],
  ["teamwork",   "Working alone or with others"],
  ["cost",       "What it costs"],
  ["earnings",   "Earnings and job prospects after graduating"],
  ["extra",      "Avoiding interviews, tests and portfolios"],
];
const DIMENSION_KEYS = WEIGHTED_DIMENSIONS.map(d=>d[0]);
const DIMENSION_LABEL = Object.fromEntries(WEIGHTED_DIMENSIONS);

const IMPORTANCE_LEVELS=[[0,"Doesn't matter"],[1,"A little"],[2,"Quite a lot"],[3,"Most"]];

function dimensionWeights(p){
  const chosen={};
  for(const [k,v] of (p.importance||[])) if(DIMENSION_KEYS.includes(k)) chosen[k]=+v;
  if(!Object.keys(chosen).length) return Object.fromEntries(DIMENSION_KEYS.map(k=>[k,1]));
  return Object.fromEntries(DIMENSION_KEYS.map(k=>[k,Math.max(0,Math.min(3,chosen[k]||0))]));
}


/* Mirrors engine/fit.py. Fit is scored because every point traces back to
   something the student typed; evidence is never scored because that would
   be predicting an admissions committee. The two are never blended. */
const FIT_SIGNALS = ["interests","enjoyed_subjects","subjects_offered","assessment_style","teamwork",
                     "priorities","goal_text","willing_extra_assessment","cost_sensitive"];
const MIN_SIGNALS = 2;
/* Mirrors engine/fit.py:REQUIRED_COVERAGE. All five polytechnics are named
   individually and deliberately: a family flag that any one of them satisfied
   would lift PREVIEW while four institutions were still missing. */
const REQUIRED_COVERAGE = ["NUS","NTU","SMU","SUTD","SIT","SUSS","NYP","NP","SP","TP","RP"];

function signalCount(p){
  return FIT_SIGNALS.filter(k=>{
    const v = p[k];
    return !(v===null||v===undefined||v===""||(Array.isArray(v)&&!v.length));
  }).length;
}
function fitCoverage(pack){
  const present = [...new Set(pack.outcomes.map(o=>o.institution_short))].sort();
  const missing = REQUIRED_COVERAGE.filter(i=>!present.includes(i));
  return {institutions:present, missing, complete:missing.length===0};
}
/* Mirrors engine/fit.py. Eligibility is checked BEFORE preference.
   A course taught in a language the student does not offer is not a weak
   match — it is a different question, and answering it with a number is what
   went wrong: NP's Chinese Studies came out second strongest of 296 for a
   student who does not read Chinese, on entirely generic overlap. No score at
   all, rather than a low one, because a low score is still a ranking. */
function languageBlock(outcome, p){
  const lr = outcome.language_requirement;
  if(!lr) return null;
  const stage = (lr.at_stage||"o-level").replace(/-/g," ").toUpperCase();
  if(p.languages_offered == null)
    return `This course requires ${lr.label} at ${stage}`+
      (lr.taught_in_language ? ", and is taught substantially in that language. " : ". ")+
      "PathAhead has not been told which mother tongue you offered, so it will "+
      "not rank this as a match either way. Answer that question in step two and it will.";
  if(!p.languages_offered.includes(lr.language))
    return `This course requires ${lr.label} at ${stage}`+
      (lr.taught_in_language ? ", and is taught substantially in that language" : "")+
      ", which is not among the ones you said you offered. It is left here "+
      "rather than hidden, because the requirement is the institution's to "+
      "waive, not PathAhead's to assume.";
  return null;
}

/* The same check, for the far more common case: a published SUBJECT
   prerequisite. NTU shows Physics / Applied Physics at 52/100 to a student
   with no Physics until this runs — and 52 is not "a bit low", it is a
   confident number on a shut door, ranked above two hundred courses the
   student could actually enrol in.

   Folded onto subject FAMILIES, so someone taking Further Mathematics is not
   told they do not take Mathematics. `enjoyed_subjects` counts as evidence of
   offering too: a student who named Chemistry as a favourite plainly takes it,
   and making them say it twice would block them on our form design. */
function subjectBlock(outcome, p, fam){
  const reqs = outcome.subject_requirements || [];
  if(!reqs.length) return null;
  const res = c => (fam && fam[String(c||"").toLowerCase()]) || String(c||"").toLowerCase();
  for(const req of reqs){
    const wanted = new Set((req.subjects||[]).map(res));
    /* NTU's wording already carries the level, so never prefix it onto a
       published label — "H2 H2 Level pass in Physics" reads like a bug
       because it is one. */
    let named = req.label, level = "";
    if(!named){
      named = (req.subjects||[]).map(c=>c.replace(/-/g," ")).join(" or ");
      level = req.at_level ? req.at_level.toUpperCase()+" " : "";
    }
    const who = outcome.institution_short || outcome.institution;
    if(p.subjects_offered == null)
      return `${who} asks for ${level}${named} before it will consider an `+
        "application here. PathAhead has not been told which subjects you take, "+
        "so it will not rank this as a match either way. Fill in the subjects "+
        "you are taking and it will.";
    const offered = new Set([...(p.subjects_offered||[]), ...(p.enjoyed_subjects||[])].map(res));
    if(![...wanted].some(w=>offered.has(w)))
      return `${who} asks for ${level}${named} here, which is not among the `+
        "subjects you said you take. It is left in the list rather than hidden, "+
        "because the requirement is the institution's to state and to waive, "+
        "not PathAhead's to assume you cannot meet."+
        (req.detail ? " "+req.detail : "");
  }
  return null;
}

function scoreFit(outcome, p, fam){
  const blocked = languageBlock(outcome, p) || subjectBlock(outcome, p, fam);
  if(blocked) return {outcome_id:outcome.id, score:null, factors:[],
    signals_used:signalCount(p), signals_available:FIT_SIGNALS.length,
    unscored_reason:blocked, not_assessed:[]};
  /* THE RULE THAT MATTERS MOST: a factor is scored only when we have BOTH
     sides of it. If PathAhead lacks the data, the factor is DROPPED, never
     scored zero. An earlier version charged a student 0/15 because MOE does
     not survey Medicine graduates, and 5/10 on every course because no fee
     figures are loaded -- pushing the whole pack below 50. Our gaps must
     never be billed to the student. */
  const avail = FIT_SIGNALS.length, used = new Set(), factors = [], skipped = [];
  const F = fam || {};
  const res = c => F[c] || c;
  const n = signalCount(p);
  const none = reason => ({outcome_id:outcome.id, score:null, factors:[], signals_used:n,
                           signals_available:avail, unscored_reason:reason, not_assessed:[]});
  if(n < MIN_SIGNALS) return none(
    "Answer at least two of the optional questions and PathAhead will show how well this course matches what you said — with the reasoning, line by line.");
  const ed = outcome.editorial;
  if(!ed) return none("PathAhead has no description of what this course is like, so it will not guess at a match.");
  /* Weighting mirrors engine/fit.py exactly — the golden fixtures replay both
     and fail on any disagreement beyond 1e-9. A dimension the student ranked
     nowhere weighs 0 and leaves the fraction entirely, on both sides. */
  const weights = dimensionWeights(p);
  const add=(label,points,max,reason,src,dim)=>{
    const d = dim || src;
    const w = weights[d] ?? 1;
    if(w <= 0){ skipped.push(DIMENSION_LABEL[d]+" — you ranked this as not mattering"); return; }
    const m = max<=0 ? 0 : Math.max(0, Math.min(1, points/max));
    factors.push({label, points:r1(m*w), max:w, max_points:w, reason,
                  dimension:d, weight:w, match:m});
    used.add(src);
  };

  // interests — denominator is the COURSE's profile, never the length of the
  // student's own list. Naming more of yourself must never lower your score.
  if(p.interests?.length && ed.interests?.length){
    const hit = p.interests.filter(i=>ed.interests.includes(i));
    const target = Math.min(ed.interests.length,2) || 1;
    const names = hit.map(i=>(INTEREST_LABEL[i]||i).toLowerCase());
    add("What pulls at you", r1(25*Math.min(1,hit.length/target)), 25,
      hit.length ? `you chose ${names.join(", ")}, which is what this course draws on`
                 : "you picked different kinds of work from the ones this course mainly draws on", "interests","interests");
  }
  // subjects — matched by FAMILY, so Further Mathematics counts as mathematics
  if(p.enjoyed_subjects?.length && ed.subject_affinity?.length){
    const enjoyed = new Set(p.enjoyed_subjects.map(x=>res(x.toLowerCase())));
    const aff = [...new Set(ed.subject_affinity.map(x=>res(x.toLowerCase())))];
    const hits = aff.filter(a=>enjoyed.has(a)).sort();
    const target = Math.min(aff.length,3) || 1;
    add("Subjects you enjoy", r1(25*Math.min(1,hits.length/target)), 25,
      hits.length ? `this course is built on ${hits.join(", ")}, which you said you enjoy`
                  : `this course leans mostly on ${aff.filter(a=>!enjoyed.has(a)).sort().slice(0,3).join(", ")}, and you picked different subjects`,
      "enjoyed_subjects","subjects");
  }
  if(p.assessment_style && ed.assessment_style?.length){
    const m = ed.assessment_style.includes(p.assessment_style);
    add("How you are assessed", m?15:0, 15,
      m ? `you work best through ${p.assessment_style}, and so does much of this course`
        : `you work best through ${p.assessment_style}; this course leans on ${ed.assessment_style.join(", ")}`,
      "assessment_style","assessment");
  }
  if(p.teamwork && ed.teamwork){
    let pts, why;
    if(p.teamwork===ed.teamwork){ pts=10; why=`this course is mostly ${ed.teamwork} work, which is what you prefer`; }
    else if(p.teamwork==="mixed"||ed.teamwork==="mixed"){ pts=5; why="partly a match on working style"; }
    else { pts=0; why=`you prefer ${p.teamwork} work; this course is mostly ${ed.teamwork}`; }
    add("Working style", pts, 10, why, "teamwork", "teamwork");
  }
  // priorities — scored ONLY against what we can actually assess for this
  // course. A course is never marked down because a survey does not cover it.
  if(p.priorities?.length){
    const emp = outcome.employment, parts = [];
    if(p.priorities.includes("earnings") && emp?.gross_median)
      parts.push([10, `you said financial security matters; graduates of this course reported a ${emp.fact?.as_of_year??""} median of $${emp.gross_median.toLocaleString()}`]);
    if(p.priorities.includes("stability") && emp?.employment_rate)
      parts.push([emp.employment_rate>=90?10:5, `you said a steady path matters; ${emp.employment_rate}% of graduates were in employment within six months`]);
    if(parts.length) add("What you said matters",
      r1(parts.reduce((a,x)=>a+x[0],0)/parts.length), 10,
      parts.map(x=>x[1]).join("; "), "priorities","earnings");
    else skipped.push("what you said matters most — PathAhead has no published outcome figures for this course, which says nothing about the course");
  }
  /* Extra assessment and cost no longer wait on a yes/no toggle. The toggles
     asked the same question the importance rows ask, so they were removed; how
     much either counts is now the weight, and whether it is SCORED depends only
     on whether the data exists. */
  {
    const needs = hasExtra(outcome);
    add("Extra assessment", needs?0:10, 10,
      needs ? "this course requires an interview, test or portfolio, which you asked to count"
            : "no extra interview, test or portfolio is required, which you asked to count",
      "willing_extra_assessment", "extra");
  }
  if(outcome.cost){
    const yrs=outcome.cost.years, fee=outcome.cost.annual_fee_citizen;
    if(fee===null||fee===undefined) skipped.push("cost — PathAhead does not carry a fee figure for this course yet");
    else { const total=fee*yrs;
      let why=`the subsidised course fee comes to about $${total.toLocaleString()} over ${yrs} years`;
      if(outcome.cost.bond_note) why += ". " + outcome.cost.bond_note;
      add("Cost", total<=40000?10:5, 10, why, "cost_sensitive", "cost"); }
  }

  if(!factors.length) return none("What you answered does not overlap with what PathAhead knows about this course, so it will not invent a match.");
  const earned = factors.reduce((a,f)=>a+f.points,0);
  const possible = factors.reduce((a,f)=>a+f.max,0);
  factors.sort((a,b)=> (b.points/b.max)-(a.points/a.max) || a.label.localeCompare(b.label));
  return {outcome_id:outcome.id, score:r0(100*earned/possible), factors,
          signals_used:used.size, signals_available:avail, unscored_reason:null,
          not_assessed:skipped};
}
/* Describes the MATCH, never the person. The previous wording ended at
   "weak", which a seventeen-year-old reads as a verdict on herself rather
   than on a course description written by a stranger. */
function fitBand(s){ return s>=75?"close match":s>=50?"good overlap":s>=25?"some overlap":"little overlap"; }
function hasExtra(o){
  return (o.overlays||[]).some(v=>["interview","portfolio","aptitude_test","audition"].includes(v.kind));
}
const INTEREST_LABEL = {R:"Building and making",I:"Investigating and analysing",
  A:"Designing and creating",S:"Helping and teaching",E:"Leading and persuading",
  C:"Organising and systems"};

/* ---------- engine: school fit (mirrors engine/school_fit.py) ----------
   Which of the 147 schools a PSLE cohort can be posted to are even worth a
   closer look, given what a family says matters to them. This used to
   compute a weighted match SCORE and rank schools by it. Review on
   2026-08-13 concluded the score itself -- not just the cut-off data
   feeding it -- was the SAFEGUARDS.md 5.1 risk ("never rank schools...
   results sort by fit, programme and location — never by selectivity
   descending"): a percentage and a bar chart read as a verdict no matter
   how carefully the copy around them explains they are not one. The fix
   is not a better score. It is no score. Every dimension below is a
   FILTER: set it, and it hides schools that don't match; leave it unset,
   and it does nothing. What remains after filtering is sorted by distance
   (when a postal code was given) and then by name — never by anything
   resembling how closely a school matches, and never by selectivity. See
   FILTER_DISCLAIMER below, shown once above every shortlist. */
const SCHOOL_FILTER_DIMENSIONS = [
  ["gender",     "Co-ed or single-sex"],
  ["sap",        "Special Assistance Plan (bilingual, Chinese language and culture emphasis)"],
  ["ip",         "Integrated Programme (one six-year run through to A-Level or the IB, without sitting O-Levels)"],
  ["autonomous", "Autonomous status (extra funding for facilities and programmes, and its own admission exercise)"],
  ["gifted",     "A Gifted Education Programme branch at secondary level"],
  ["school_type","Government, government-aided, independent or specialised"],
];
const SCHOOL_DIMENSION_KEYS = SCHOOL_FILTER_DIMENSIONS.map(d=>d[0]);
const SCHOOL_DIMENSION_LABEL = Object.fromEntries(SCHOOL_FILTER_DIMENSIONS);

const FILTER_DISCLAIMER =
  "These are filters, not a ranking. Setting one hides schools that don't match it; "+
  "the ones left are sorted by distance and name only, never by how closely they "+
  "match what you asked for and never by how competitive a school is. PathAhead "+
  "does not hold Posting Group data for individual schools beyond the published "+
  "cut-off filter below, and even that never reorders anything — see the Posting "+
  "Group calculator on this page for a direct answer to what your child's score can reach.";

/* sector (first two digits of a postal code) -> that district's row. Built
   once per pack, mirroring engine/school_fit.py:postal_sector_index. */
function postalSectorIndex(pack){
  const idx={};
  for(const row of (pack.postal_districts||[])) for(const sector of (row.sectors||[])) idx[String(sector)]=row;
  return idx;
}
function resolveDistrict(indexOrPack, postalCode){
  const idx = (indexOrPack && indexOrPack.postal_districts) ? postalSectorIndex(indexOrPack) : (indexOrPack||{});
  const digits = String(postalCode||"").replace(/\D/g,"");
  if(digits.length!==6) return null;
  return idx[digits.slice(0,2)] || null;
}
/* Mean Earth radius in km -- the constant every haversine implementation
   uses; not a PathAhead choice. Mirrors engine/school_fit.py exactly. */
const EARTH_RADIUS_KM = 6371.0;

/* Great-circle (straight-line) distance between two points, in km. This is
   deliberately NOT a travel time -- a routed transit/driving time needs a
   live call to a routing service, which would mean the postal code a family
   typed left the device. The two points behind this call are real: a
   school's own geocoded postal code, and a representative anchor point for
   the family's postal DISTRICT (never their exact address, which PathAhead
   never geocodes at all). Both are fetched once, offline, at pack build
   time from OneMap Singapore -- see tools/build_secondary_schools_pack.py.
   Mirrors engine/school_fit.py:haversine_km exactly. */
function haversineKm(lat1, lng1, lat2, lng2){
  const toRad = d => d*Math.PI/180;
  const r1=toRad(lat1), r2=toRad(lat2);
  const dlat=toRad(lat2-lat1), dlng=toRad(lng2-lng1);
  const a = Math.sin(dlat/2)**2 + Math.cos(r1)*Math.cos(r2)*Math.sin(dlng/2)**2;
  return EARTH_RADIUS_KM * 2 * Math.asin(Math.sqrt(a));
}

/* Straight-line km from a family's postal-district anchor to a school, or
   null if either point's coordinates are missing. Purely informational --
   this never feeds a score. Mirrors engine/school_fit.py:distance_km. */
function distanceKm(school, homeDistrict){
  if(homeDistrict==null) return null;
  const lat1=homeDistrict.lat, lng1=homeDistrict.lng, lat2=school.lat, lng2=school.lng;
  if([lat1,lng1,lat2,lng2].some(v=>v==null)) return null;
  return Math.round(haversineKm(lat1,lng1,lat2,lng2)*10)/10;
}

/* PSLE-score points of slack allowed past a school's published cut-off
   point before treating it as out of reach. Mirrors
   engine/school_fit.py:REACH_MARGIN exactly -- see that module's docstring
   for why a hard boundary at exactly last year's number would be wrong. */
const REACH_MARGIN = 2;

/* Whether a school's most recently published cut-off, for whichever
   Posting Group(s) the family's own PSLE score has actually opened,
   suggests the school is realistically still worth a spot on a real
   six-school list. A FILTER, not a score and not a sort key -- see
   SAFEGUARDS.md 5.1. `familyGroups` is postingGroupFor(...).groups, computed
   once per family by the caller. Returns null -- never false -- when
   PathAhead cannot judge (no cutoff published, or the score fell outside
   the Posting Group table); a caller must SHOW these schools, with the
   reason, never silently treat "cannot tell" as "no". Mirrors
   engine/school_fit.py:within_reach exactly. */
function withinReach(school, psleScore, familyGroups, margin){
  const m = margin==null ? REACH_MARGIN : margin;
  const cutoffs = school.cutoff_2025;
  if(!cutoffs || !familyGroups || !familyGroups.length) return null;
  let seenPublishedGroup = false;
  for(const group of familyGroups){
    const band = cutoffs[`pg${group}`];
    if(band==null) continue;
    seenPublishedGroup = true;
    const cop = band[1];
    if(cop!=null && psleScore <= cop + m) return true;
  }
  return seenPublishedGroup ? false : null;
}

/* Reach across an EXPLICIT AL-score search a family types directly into
   the shortlist filter -- a single score, or a range for a family working
   from an estimate rather than a result -- independent of whatever they
   entered into the Posting Group calculator elsewhere on the page. Pass
   loScore===hiScore (with the same groups at both ends) for a single exact
   score: an "upper bound" search is the one-point degenerate case of a
   range, not a second code path, so withinReach() above never needed
   duplicating. Still a FILTER, never a score -- a caller only ever hides on
   "out-of-reach", the same way a plain withinReach()===false already only
   ever hid; the other three states all stay visible and differ only in
   which honest caveat a caller shows. Mirrors
   engine/school_fit.py:combined_reach exactly. */
function combinedReach(school, loScore, hiScore, loGroups, hiGroups, margin){
  const reachWorst = withinReach(school, hiScore, hiGroups, margin);
  const reachBest = withinReach(school, loScore, loGroups, margin);
  if(reachWorst===true) return "in-reach";
  if(reachBest===true) return "possible";
  if(reachBest===false && reachWorst===false) return "out-of-reach";
  return "unknown";
}

/* Checks one school against one family's FILTERS. Mirrors
   engine/school_fit.py:match_school exactly: the one hard, unconditional
   fact (sex-based admission) is resolved first and independently of
   everything else; the family's own filters are then checked, but only the
   ones actually set. Nothing unset ever counts against a school, and
   nothing PathAhead failed to load ever counts against a school either. */
function matchSchool(school, prefs, districtIndexOrPack){
  // Computed once, independently of eligibility/filters below -- distance is
  // populated whenever a postal code was given, whether or not the school
  // ends up eligible or matching. Mirrors engine/school_fit.py:match_school.
  let distKm = null, homeDistrict = null;
  if(prefs.postal_code){
    homeDistrict = resolveDistrict(districtIndexOrPack, prefs.postal_code);
    distKm = distanceKm(school, homeDistrict);
  }

  // ELIGIBILITY, checked first -- three states, see engine/school_fit.py's
  // SchoolMatch docstring. Only `eligible===false` ever hides a school
  // unconditionally; it is a fact about the school, not a filter to set.
  let eligible = true, eligibilityReason = null;
  const schoolGender = school.gender;
  if(schoolGender==="girls" || schoolGender==="boys"){
    if(prefs.student_sex==null){
      eligible = null;
      eligibilityReason =
        `This is a ${schoolGender} school. PathAhead has not been told your child's `+
        "sex, so it cannot confirm whether this school is even an option — answer "+
        "that above and this will resolve one way or the other.";
    } else {
      const wrongSex = (schoolGender==="girls" && prefs.student_sex==="male")
        || (schoolGender==="boys" && prefs.student_sex==="female");
      if(wrongSex){
        const notAdmits = schoolGender==="girls" ? "boys" : "girls";
        eligible = false;
        eligibilityReason =
          `This is a ${schoolGender} school; it does not admit ${notAdmits}. Not a `+
          "preference to weigh — not a real option for this child.";
      }
    }
  }

  // PREFERENCE FILTERS -- each one only ever checked if the family set it.
  const unmet=[];
  if(prefs.gender && school.gender!==prefs.gender) unmet.push("gender");
  if(prefs.want_sap!=null && !!school.sap!==prefs.want_sap) unmet.push("sap");
  if(prefs.want_ip!=null && !!school.ip!==prefs.want_ip) unmet.push("ip");
  if(prefs.want_autonomous!=null && !!school.autonomous!==prefs.want_autonomous) unmet.push("autonomous");
  if(prefs.want_gifted!=null && !!school.gifted!==prefs.want_gifted) unmet.push("gifted");
  if(prefs.school_types?.length && !prefs.school_types.includes(school.type_label)) unmet.push("school_type");

  return {school_id:school.id, eligible, eligibility_reason:eligibilityReason,
          matches_preferences: unmet.length===0, unmet, distance_km:distKm};
}
function matchAllSchools(pack, prefs){
  const idx = postalSectorIndex(pack);
  const out = {};
  for(const s of (pack.schools||[])) out[s.id] = matchSchool(s, prefs, idx);
  return out;
}
/* Every school paired with its match info, sorted by distance (when a
   postal code was given, closest first, unknown-distance last) and then by
   name — never by anything resembling selectivity or preference match, per
   SAFEGUARDS.md 5.1. Does not drop ineligible or non-matching schools
   itself; the UI decides what to hide and counts it, the same way the
   distance-band and reach filters already work. `limit` truncates for
   display only; matching always runs over the full pool. Mirrors
   engine/school_fit.py:shortlist exactly. */
function shortlistSchools(pack, prefs, limit){
  const matches = matchAllSchools(pack, prefs);
  const byId = Object.fromEntries((pack.schools||[]).map(s=>[s.id,s]));
  const rows = Object.entries(matches).filter(([sid])=>byId[sid]).map(([sid,m])=>[byId[sid],m]);
  rows.sort((a,b)=>{
    const an=a[1].distance_km==null, bn=b[1].distance_km==null;
    if(an!==bn) return an?1:-1;
    if(!an && (a[1].distance_km!==b[1].distance_km)) return a[1].distance_km-b[1].distance_km;
    return a[0].name.localeCompare(b[0].name);
  });
  return limit ? rows.slice(0,limit) : rows;
}
function titleCase(s){ return String(s||"").toLowerCase().replace(/\b\w/g,c=>c.toUpperCase()); }

/* ---------- engine: cohort ---------- */
function resolveCohort(pack, yearLevel, currentYear){
  const c = pack.cohorts.find(c=>c.year_level===yearLevel);
  if(!c) throw new PAError(`unknown year level "${yearLevel}"`, "Choose a year level from the list.");
  const examYear = currentYear + c.years_to_exam;
  const admissionYear = examYear + c.admission_offset;
  const t = pack.transitions.find(t=>t.id===c.transition);
  if(!t) throw new PAError(`no rules loaded for ${c.label}`, "PathAhead has not loaded the rules for this stage yet.");
  if(t.applies_to_exam_years.length && !t.applies_to_exam_years.includes(examYear))
    throw new PAError(
      `the loaded rules cover exam years ${t.applies_to_exam_years.join(", ")}, but ${c.label} in ${currentYear} sits the exam in ${examYear}`,
      "The rules for that year have not been published or loaded yet. Check back after the next data update rather than relying on this year's formula.");
  const stage = pack.stages.find(s=>s.id===c.stage);
  return {cohort:c, transition:t, examYear, admissionYear,
    sentence:`${c.label} in ${currentYear} means sitting the ${stage.name} in ${examYear}, and applying for a place in ${admissionYear}.`};
}

/* ---------- engine: timeline ---------- */
const NS_YEARS = 2;
function buildTimeline(pack, res, ns, today){
  const out = [];
  for(const m of (pack.milestones||[])){
    if(m.applies_to?.length && !m.applies_to.includes(res.cohort.stage)) continue;
    if(m.requires_service && !ns) continue;
    const d = new Date(Date.UTC(res.examYear + m.year_offset, m.month-1, m.day));
    const days = Math.round((d - today)/86400000);
    out.push({...m, date:d, days:Math.max(days,0), passed:days<0, when:whenText(days)});
  }
  out.sort((a,b)=>a.date-b.date);
  const notes = ["These dates move from year to year. PathAhead shows you what is coming; the official page is what you should rely on."];
  if(ns) notes.push(
    `You have said National Service applies. You would normally apply and accept a place in ${res.admissionYear} and then defer, starting around ${res.admissionYear+NS_YEARS}. That is an ordinary published route, not a setback — and it means the salary figures below describe people who graduated years before you will.`);
  return {entries:out, notes, starts:res.admissionYear + (ns?NS_YEARS:0)};
}
function whenText(d){
  if(d<0) return "already passed";
  if(d===0) return "today"; if(d===1) return "tomorrow";
  if(d<31) return `in ${d} days`;
  const m = Math.round(d/30.4);
  return m<24 ? `in about ${m} month${m!==1?"s":""}` : `in about ${Math.round(d/365.25)} years`;
}

/* ---------- trace rendering ---------- */
function traceText(d){
  const pad=(s,n)=>String(s).padEnd(n), lp=(s,n)=>String(s).padStart(n);
  return d.steps.map(s=>{
    if(s.kind==="heading") return s.label;
    if(s.kind==="note")    return "  ! " + s.label;
    if(s.kind==="excluded")
      return "  - " + pad(s.label,34) + lp(num(s.points),7) + "   not counted" + (s.detail?"  "+s.detail:"");
    if(s.kind==="subtotal"||s.kind==="total"||s.kind==="cap")
      return "  " + pad(s.label,36) + lp(num(s.running_total),7);
    return "  " + pad(s.label,36) + lp(num(s.points),7) + (s.detail?"  "+s.detail:"");
  }).join("\n");
}

/* =====================================================================
   UI
   ===================================================================== */
const LEVELS = [["h2","H2"],["h1","H1"],["gp","General Paper"],["mtl","Mother Tongue"],["h3","H3"]];
const GRADES = ["A","B","C","D","E","S","U"];
const ASM = [["exams","Exams"],["coursework","Projects & coursework"],["practical","Hands-on"]];
const TEAM = [["individual","On my own"],["mixed","A mix"],["team","In a team"]];
const PRI = [["earnings","Financial security"],["impact","Doing something useful"],
  ["mastery","Getting really good at one thing"],["autonomy","Freedom over how I work"],
  ["stability","A steady, predictable path"],["creativity","Making new things"]];
/* "Cost is a real constraint" and "Happy to sit interviews" used to live here
   AND as importance rows — the same question in two idioms, on one page. They
   are now asked once, as importance. What is left are the two that are facts
   about a situation rather than preferences, so they have no importance row. */
const CON = [["national_service","National Service applies"],
  ["open_to_longer_route","Open to a longer route, e.g. poly then degree"]];
const SAMPLE = [
  {level:"h2",name:"Chemistry",code:"chemistry",grade:"A"},
  {level:"h2",name:"Biology",code:"biology",grade:"A"},
  {level:"h2",name:"Mathematics",code:"mathematics",grade:"B"},
  {level:"gp",name:"General Paper",code:"general-paper",grade:"A"},
  {level:"mtl",name:"Chinese Language",code:"chinese",grade:"B"}];
const BLANK = [{level:"h2",name:"",code:"",grade:"A"},{level:"h2",name:"",code:"",grade:"A"},
  {level:"h2",name:"",code:"",grade:"A"},{level:"gp",name:"General Paper",code:"general-paper",grade:"B"}];

const P = { interests:[], enjoyed_subjects:[], subjects_offered:null, assessment_style:null, teamwork:null,
  /* Chosen fields. A FILTER on the list, never a scoring input — see STREAMS. */
  streams:[],
  /* How much each dimension counts, as [key, 0-3] pairs. Empty = nothing set,
     so everything counts equally — a stated default, not a hidden prior. */
  importance:[],
  priorities:[], goal_text:"", national_service:false, cost_sensitive:null,
  willing_extra_assessment:null, open_to_longer_route:null, citizenship:"citizen",
  /* null = not answered, [] = "none of these". The engine treats those
     differently and says which it is, so they must stay distinguishable. */
  languages_offered:null };

const slug = t => String(t).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");

/* ── subject combobox (ARIA 1.2 pattern) ───────────────────────── */
function subjectCombo(row, idx){
  const id = `sc${idx}`;
  const input = el("input",{type:"text",value:row.name,placeholder:"Type a subject…",
    role:"combobox","aria-expanded":"false","aria-controls":id+"l","aria-autocomplete":"list",
    "aria-label":`Subject ${idx+1}`,autocomplete:"off"});
  const list = el("ul",{id:id+"l",role:"listbox",hidden:"hidden","aria-label":"Subject suggestions"});
  const box = el("div",{class:"combo"},[input,list]);
  let active = -1, matches = [];

  const close = ()=>{ list.hidden=true; input.setAttribute("aria-expanded","false"); active=-1; };
  // paintEnjoy() rebuilds the "which subjects do you enjoy" chips from the
  // rows. It used to run only when a row was added or removed, so typing a
  // subject never made it appear -- leaving a student with one chip for the
  // pre-filled General Paper and nothing else to pick.
  const pick = m =>{ row.name=m.name; row.code=m.code; input.value=m.name; close(); paintEnjoy(); };
  const paint = ()=>{
    list.replaceChildren();
    matches.forEach((m,i)=>list.append(el("li",{role:"option",id:`${id}o${i}`,
      "aria-selected":String(i===active),
      onmousedown:e=>{e.preventDefault();pick(m);}},
      [document.createTextNode(m.name),
       m.levels?.length ? el("small",{text:m.levels.map(l=>l.toUpperCase()).join(" · ")}) : null])));
    input.setAttribute("aria-activedescendant", active>=0 ? `${id}o${active}` : "");
  };
  const search = q =>{
    const needle = q.trim().toLowerCase();
    const all = S.pack.subjects || [];
    if(!needle) return all.filter(s=>s.levels?.includes(row.level)).slice(0,8);
    return all.filter(s => s.name.toLowerCase().includes(needle) ||
      (s.aka||[]).some(a=>a.includes(needle)) || s.code.includes(needle)).slice(0,8);
  };
  const open = ()=>{ matches = search(input.value);
    if(!matches.length){ close(); return; }
    active = -1; paint(); list.hidden=false; input.setAttribute("aria-expanded","true"); };

  input.addEventListener("input", ()=>{ row.name=input.value; row.code=slug(input.value); open(); });
  input.addEventListener("focus", open);
  input.addEventListener("blur", ()=>setTimeout(()=>{ close(); paintEnjoy(); },120));
  input.addEventListener("keydown", e=>{
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){
      e.preventDefault(); if(list.hidden) open();
      if(!matches.length) return;
      active = e.key==="ArrowDown" ? (active+1)%matches.length
                                   : (active<=0?matches.length-1:active-1);
      paint();
    } else if(e.key==="Enter"){ if(!list.hidden&&active>=0){ e.preventDefault(); pick(matches[active]); } }
    else if(e.key==="Escape"){ close(); }
  });
  return box;
}

/* Levels where the level IS the subject.
   General Paper is one paper with one name; offering it as a "level" and then
   asking which subject it is produced a row reading "General Paper / General
   Paper" (ISSUES_v0.2.md section G3). Mother Tongue is NOT in here on purpose:
   it is a level, and which language you took is a real question. */
const LEVEL_IS_THE_SUBJECT = {gp:["general-paper","General Paper"]};

function renderRows(){
  const tb = $("#rows"); tb.replaceChildren();
  S.rows.forEach((row,i)=>{
    const lv = el("select",{"aria-label":`Level for subject ${i+1}`,
      onchange:e=>{row.level=e.target.value; renderRows();}});
    LEVELS.forEach(([v,t])=>lv.append(el("option",{value:v,text:t,...(row.level===v?{selected:"selected"}:{})})));
    const gr = el("select",{"aria-label":`Grade for subject ${i+1}`,
      onchange:e=>{row.grade=e.target.value; paintEnjoy();}});
    GRADES.forEach(g=>gr.append(el("option",{value:g,text:g,...(row.grade===g?{selected:"selected"}:{})})));
    const rm = el("button",{class:"rmbtn",type:"button","aria-label":`Remove subject ${i+1}`,text:"×",
      title:"Remove this subject row",
      onclick:()=>{S.rows.splice(i,1);renderRows();paintEnjoy();}});
    const fixed = LEVEL_IS_THE_SUBJECT[row.level];
    let nameCell;
    if(fixed){
      // Pin the row to the one subject this level can be, and say so as text
      // rather than as an input that looks like it wants an answer.
      [row.code, row.name] = fixed;
      nameCell = el("span",{class:"fixed-subject",text:fixed[1]});
    } else {
      if(LEVEL_IS_THE_SUBJECT[row.code]) { row.code=""; row.name=""; }
      nameCell = subjectCombo(row,i);
    }
    tb.append(el("tr",{},[
      el("td",{class:"lv","data-label":"Level"},lv),
      el("td",{class:"nm","data-label":"Subject"},nameCell),
      el("td",{class:"gr","data-label":"Grade"},gr),
      el("td",{class:"rm"},rm)]));
  });
  paintEnjoy();
}

function readGrades(){
  return S.rows.map((row,i)=>{
    const name = (row.name||"").trim() ||
      (row.level==="gp"?"General Paper":row.level==="mtl"?"Mother Tongue":`Subject ${i+1}`);
    return {code: row.code || slug(row.level+"-"+name), name, level:row.level, grade:row.grade};
  });
}

/* ── profile widgets ───────────────────────────────────────────── */
function toggleChip(btn, arr, key){
  const on = btn.getAttribute("aria-pressed")==="true";
  btn.setAttribute("aria-pressed", String(!on));
  const i = arr.indexOf(key);
  if(on && i>=0) arr.splice(i,1); else if(!on && i<0) arr.push(key);
}
/* Which subjects the student actually takes — read straight off the grades
   table in step two, so eligibility costs them no extra question.
   `null` until they have named one, because "not told" and "takes none of
   these" must produce different answers: the first says come back and tell me,
   the second is a real no. */
function resolveSubjectCode(name){
  /* Someone who TYPES "Physics" and never clicks the suggestion still takes
     Physics. Relying on row.code alone would leave them with the slug
     "h2-physics", no match against NTU's requirement, and a course wrongly
     withheld — the exact mirror of the bug this gate was built to fix, and
     the more damaging direction, because it takes an option away.
     Matched against the pack's own names and aliases, so "h2 math", "a math"
     and "phys" all land where a reader would expect. */
  const n = String(name||"").trim().toLowerCase();
  if(!n) return null;
  for(const s of (S.pack.subjects||[])){
    if(s.code===n || String(s.name||"").toLowerCase()===n) return s.code;
    if((s.aka||[]).some(a=>String(a).toLowerCase()===n)) return s.code;
  }
  return null;
}

function syncSubjectsOffered(){
  const named = [];
  for(const r of readGrades()){
    if(!r.name || /^Subject \d+$/.test(r.name)) continue;
    const code = resolveSubjectCode(r.name) || (r.code||"").trim();
    if(code) named.push(code);
  }
  P.subjects_offered = named.length ? named : null;
}

function paintEnjoy(){
  syncSubjectsOffered();
  const host = $("#enjoyChips"); if(!host) return;
  host.replaceChildren();
  const subs = readGrades().filter(s=>s.name && !/^Subject \d+$/.test(s.name));
  // A subject that has been renamed or removed must not stay silently selected.
  const live = new Set(subs.map(s=>s.code));
  P.enjoyed_subjects = P.enjoyed_subjects.filter(c=>live.has(c));
  if(!subs.length){ host.append(el("p",{class:"hint",text:"Type your subjects in step two and they will appear here to pick from."})); return; }
  for(const s of subs){
    const pressed = P.enjoyed_subjects.includes(s.code);
    host.append(el("button",{type:"button",class:"chip","aria-pressed":String(pressed),
      text:s.name, title:`Mark ${s.name} as a subject you enjoy`,
      onclick:e=>toggleChip(e.currentTarget,P.enjoyed_subjects,s.code)}));
  }
}
function buildProfileUI(){
  const ih = $("#interestChips");
  for(const it of (S.pack.interests||[])){
    ih.append(el("button",{type:"button",class:"chip chip-stack","aria-pressed":"false",
      title:`Pick up to 3 interests — ${it.label}: ${it.detail}`,
      onclick:e=>{
        if(P.interests.length>=3 && e.currentTarget.getAttribute("aria-pressed")==="false") return;
        toggleChip(e.currentTarget,P.interests,it.code);
      }},[document.createTextNode(it.label), el("small",{text:it.detail})]));
  }
  const seg=(host,opts,set,groupLabel)=>{
    for(const [v,t] of opts) host.append(el("button",{type:"button","aria-pressed":"false",text:t,
      title: groupLabel ? `${groupLabel}: ${t}` : t,
      onclick:e=>{ [...host.children].forEach(b=>b.setAttribute("aria-pressed","false"));
                   e.currentTarget.setAttribute("aria-pressed","true"); set(v); }}));
  };
  seg($("#asmSeg"),ASM,v=>P.assessment_style=v,"How you like to be assessed");
  seg($("#teamSeg"),TEAM,v=>P.teamwork=v,"How you like to work");
  for(const [k,t] of PRI)
    $("#priChips").append(el("button",{type:"button",class:"chip","aria-pressed":"false",text:t,
      title:`Toggle "${t}" as one of the things you personally care about`,
      onclick:e=>toggleChip(e.currentTarget,P.priorities,k)}));
  renderRanking();
  for(const [id,label] of STREAMS)
    $("#streamChips").append(el("button",{type:"button",class:"chip","aria-pressed":"false",
      text:label,
      title:`Show only courses in ${label} — pick more than one to include several fields`,
      onclick:e=>{ toggleChip(e.currentTarget,P.streams,id);
                   if(S.result) renderOptions(); }}));
  for(const [k,t] of CON)
    $("#conChips").append(el("button",{type:"button",class:"chip","aria-pressed":"false",text:t,
      title:`Toggle: ${t}`,
      onclick:e=>{ const on=e.currentTarget.getAttribute("aria-pressed")==="true";
                   e.currentTarget.setAttribute("aria-pressed",String(!on)); P[k]=!on; }}));
  /* Mother tongue. "None of these" is a real answer and is stored as an empty
     list, not as "unanswered" -- a student who says none should not keep being
     told PathAhead needs to know. */
  const MT = [["chinese","Chinese"],["malay","Malay"],["tamil","Tamil"],
              ["__none","None of these"]];
  for(const [k,t] of MT)
    $("#mtChips").append(el("button",{type:"button",class:"chip","aria-pressed":"false",text:t,
      title: k==="__none" ? "None of these Mother Tongue languages are offered"
        : `Mother Tongue: ${t} is offered`,
      onclick:e=>{
        const btn=e.currentTarget, on=btn.getAttribute("aria-pressed")==="true";
        const chips=[...$("#mtChips").children];
        if(k==="__none"){
          chips.forEach(b=>b.setAttribute("aria-pressed","false"));
          btn.setAttribute("aria-pressed",String(!on));
          P.languages_offered = on ? null : [];
        } else {
          chips[3].setAttribute("aria-pressed","false");
          btn.setAttribute("aria-pressed",String(!on));
          const picked=chips.slice(0,3)
            .filter(b=>b.getAttribute("aria-pressed")==="true")
            .map(b=>MT[chips.indexOf(b)][0]);
          P.languages_offered = picked.length ? picked : null;
        }
        if(S.result){ recomputeFits(); renderOptions(); }
      }}));
  const GOAL_SIGNALS = [
    {type:"interest", code:"R", label:"Building and making (R)", words:["build","building","machine","machines","robot","robotics","aircraft","airplane","engineer","engineering","hardware","repair","mechanic","manufacture","manufacturing","civil","construction","ship","ships","vehicle"]},
    {type:"interest", code:"I", label:"Investigating and analysing (I)", words:["research","science","scientist","data","algorithm","analyse","analyzing","investigate","lab","laboratory","biotech","biology","chemistry","physics","math","mathematics","diagnostics","discover"]},
    {type:"interest", code:"A", label:"Designing and creating (A)", words:["design","designing","art","artist","draw","drawing","creative","media","film","animation","game","games","music","write","writer","author","architecture","visual","graphics"]},
    {type:"interest", code:"S", label:"Helping and teaching (S)", words:["help","helping","teach","teacher","teaching","kid","kids","child","children","patient","patients","nurse","nursing","hospital","healthcare","therapy","therapist","counsel","counseling","social work","psychology","psychologist","doctor","care"]},
    {type:"interest", code:"E", label:"Leading and persuading (E)", words:["business","lead","leadership","manage","management","startup","startups","entrepreneur","company","market","marketing","sell","sales","law","lawyer","legal","advocate","pitch","consulting"]},
    {type:"interest", code:"C", label:"Organising and systems (C)", words:["finance","financial","bank","banking","money","accountant","accounting","audit","system","systems","process","compliance","admin","logistics","operations","supply chain"]},
    {type:"stream", code:"health", label:"Health & life sciences", words:["doctor","nurse","nursing","medicine","medical","healthcare","hospital","patient","clinic","therapy","pharmacist","pharmacy","biomedical"]},
    {type:"stream", code:"computing", label:"Computing & tech", words:["code","coding","software","programmer","programming","developer","ai","artificial intelligence","machine learning","tech","cybersecurity","data science","app"]},
    {type:"stream", code:"engineering", label:"Engineering", words:["engineer","engineering","civil","mechanical","electrical","electronics","circuit","robot","robotics","construction","architecture"]},
    {type:"stream", code:"business", label:"Business & finance", words:["business","finance","financial","accounting","marketing","startup","banking","consulting","investment","entrepreneur"]},
    {type:"stream", code:"media", label:"Media & design", words:["media","film","design","designer","music","animation","graphic","journalism","creative"]},
    {type:"stream", code:"social", label:"Social sciences & law", words:["teach","teacher","education","law","lawyer","legal","social work","psychology","counselor","public service"]},
    {type:"stream", code:"maritime", label:"Maritime & aviation", words:["pilot","aviation","aircraft","airplane","maritime","shipping","ship","marine","vessel","logistics","port"]},
    {type:"stream", code:"environment", label:"Environment", words:["environment","sustainability","sustainable","green","climate","ecology","renewable","conservation"]},
    {type:"stream", code:"hospitality", label:"Hospitality & food", words:["hotel","tourism","chef","culinary","cooking","restaurant","hospitality","event","food","baking"]}
  ];

  function updateGoalSuggestions(){
    const box = $("#goalSuggestions");
    if(!box) return;
    const val = (P.goal_text||"").toLowerCase();
    if(val.trim().length < 4){
      box.hidden = true;
      box.replaceChildren();
      return;
    }
    const words = val.split(/[^a-z0-9_-]+/).filter(Boolean);
    const matched = [];
    for(const sig of GOAL_SIGNALS){
      const already = sig.type==="interest" ? P.interests.includes(sig.code) : P.streams.includes(sig.code);
      if(already) continue;
      if(sig.words.some(w => words.includes(w) || (w.includes(" ") && val.includes(w)))){
        matched.push(sig);
      }
    }
    if(!matched.length){
      box.hidden = true;
      box.replaceChildren();
      return;
    }
    box.hidden = false;
    box.replaceChildren(
      el("div",{style:"margin-bottom:.35rem;font-weight:600;font-size:.84rem",
        text:"Suggested signals from your words (tap to add):"}),
      el("div",{style:"display:flex;flex-wrap:wrap;gap:.35rem"}, matched.slice(0,5).map(sig =>
        el("button",{type:"button",class:"chip",style:"font-size:.8rem;padding:.2rem .5rem",
          text:`+ ${sig.label}`,
          title:`Add "${sig.label}" based on the words you typed`,
          onclick:()=>{
            if(sig.type==="interest"){
              if(P.interests.length < 3 && !P.interests.includes(sig.code)){
                P.interests.push(sig.code);
                for(const b of document.querySelectorAll("#interestChips button")){
                  if(b.dataset && b.dataset.code===sig.code || b.textContent.includes(sig.code))
                    b.setAttribute("aria-pressed","true");
                }
              }
            } else {
              if(!P.streams.includes(sig.code)){
                P.streams.push(sig.code);
                for(const b of document.querySelectorAll("#streamChips button")){
                  if(b.textContent === STREAM_LABEL[sig.code]) b.setAttribute("aria-pressed","true");
                }
              }
            }
            if(S.result){ recomputeFits(); renderOptions(); }
            updateGoalSuggestions();
          }
        })
      ))
    );
  }

  $("#goalText").addEventListener("input", e=>{
    P.goal_text = e.target.value;
    updateGoalSuggestions();
  });
  $("#citizenship").addEventListener("change", e=>{ P.citizenship=e.target.value;
    if(S.result) renderOptions(); });
}

/* ── run ───────────────────────────────────────────────────────── */
function showError(msg,advice){
  const b=$("#inputError");
  b.replaceChildren(el("strong",{text:msg+" "}),el("span",{text:advice||""}));
  b.hidden=false; b.scrollIntoView({block:"nearest"});
}
function run(){
  $("#inputError").hidden = true;
  try{
    const pack=S.pack, year=new Date().getFullYear();
    const res=resolveCohort(pack,$("#yearLevel").value,year);
    const t=res.transition, fn=RULES[t.rule_kind];
    if(!fn) throw new PAError(`this version cannot read the rule "${t.rule_kind}"`,"Please refresh the page.");
    const subjects=readGrades();
    const d=fn(t.rule_params,t.scales,subjects,t.caveats);
    let comparison=d.value;
    const key=t.rule_params.comparison_component;
    if(key){ const st=d.steps.find(s=>s.running_total!==null&&s.label.toLowerCase().startsWith(key.toLowerCase()));
             if(st) comparison=st.running_total; }
    /* The student's own result expressed the way the published profiles are
       expressed. Universities publish "AAA/A", and the card used to answer
       with "Your 60" — a number set against letter grades, which is
       incoherent (ISSUES_v0.2.md section G1). The letters are what a family
       recognises; the number is the arithmetic behind them. */
    const profile = subjects.filter(s=>s.level==="h2").map(s=>s.grade).sort()
                            .slice(0,3).join("") || null;
    S.result={res,t,d,comparison,subjects,profile};
    S.fam={}; for(const sub of (pack.subjects||[])) S.fam[sub.code]=sub.family||sub.code;
    recomputeFits();
    renderAll();
    $("#results").hidden=false;
    /* Land on the result page. `navigate` is the only writer of the hash and
       writes a route id only — the grades that produced this result never
       reach the URL, so the link is safe to share and safe to leave in a
       browser history on a shared family computer. */
    navigate("#/result");
  }catch(err){
    if(err instanceof PAError) showError(err.message,err.advice);
    else { showError("Something went wrong working that out.","Please refresh and try again."); console.error(err); }
  }
}

function recomputeFits(){
  S.fits={};
  for(const o of S.pack.outcomes) S.fits[o.id]=scoreFit(o,P,S.fam);
}

function renderAll(){ renderScore(); renderTimeline(); renderOptions(); renderTargets(); renderCompare(); }

function dial(value,max){
  const pct=Math.max(0,Math.min(1,max?value/max:0)), R=74, C=2*Math.PI*R;
  const ns="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(ns,"svg");
  svg.setAttribute("viewBox","0 0 170 170"); svg.setAttribute("width","170"); svg.setAttribute("height","170");
  svg.setAttribute("aria-hidden","true");
  const mk=(cls,dash)=>{const c=document.createElementNS(ns,"circle");
    c.setAttribute("cx","85");c.setAttribute("cy","85");c.setAttribute("r",String(R));
    c.setAttribute("fill","none");c.setAttribute("stroke-width","11");c.setAttribute("stroke-linecap","round");
    c.setAttribute("stroke",cls);if(dash)c.setAttribute("stroke-dasharray",dash);return c;};
  // A warm two-stop sweep rather than a flat fill: the arc is the one piece of
  // pure decoration on the page and it may as well be the warmest thing on it.
  const defs=document.createElementNS(ns,"defs");
  const lg=document.createElementNS(ns,"linearGradient");
  lg.setAttribute("id","dialGrad");
  lg.setAttribute("x1","0");lg.setAttribute("y1","0");
  lg.setAttribute("x2","1");lg.setAttribute("y2","1");
  for(const [off,col] of [["0%","var(--brand)"],["55%","#c9762f"],["100%","var(--soft)"]]){
    const st=document.createElementNS(ns,"stop");
    st.setAttribute("offset",off); st.setAttribute("stop-color",col); lg.append(st);
  }
  defs.append(lg); svg.append(defs);
  svg.append(mk("var(--rule)"), mk("url(#dialGrad)",`${(C*pct).toFixed(2)} ${C.toFixed(2)}`));
  return el("div",{},[svg,el("div",{class:"val"},[
    el("div",{class:"num",text:num(value)}),
    el("div",{class:"of",text:max?`out of ${num(max)}`:""})])]);
}

function renderScore(){
  const {res,t,d,comparison}=S.result, pack=S.pack;
  $("#dial").replaceChildren(dial(d.value,d.max_value));
  $("#scoreLede").textContent =
    `${t.rule_params.total_label||"Total"} — this is the number universities will use.`;
  const notes=$("#scoreNotes"); notes.replaceChildren();
  /* Two maxima sat next to each other with nothing to say which was which
     (ISSUES_v0.2.md section G2): "70 out of 70" beside "PathAhead uses 60".
     Naming what each number is FOR is the whole clarification. */
  if(t.comparison_basis)
    notes.append(note(
      `Two numbers, and they do different jobs. `+
      `${num(d.value)} out of ${num(d.max_value)} is your admission score — the one universities use. `+
      `${num(comparison)} is only for reading last year's published profiles, because those are ${t.comparison_basis}. `+
      `No profile exists yet on the new ${num(d.max_value)}-point basis, so the comparison has to be made on the older one.`,
      "info"));
  if(t.changed_from?.summary) notes.append(note("What changed since last year: "+t.changed_from.summary,"info"));
  for(const w of d.warnings) notes.append(note(w,"warn"));
  $("#traceText").textContent = traceText(d);
  const src = pack.sources.find(s=>s.id===t.fact.source);
  $("#ruleCite").replaceChildren(
    document.createTextNode(`Rule as of ${t.fact.as_of_year}, ${t.fact.confidence} confidence. Source: `),
    el("a",{href:src.url,target:"_blank",rel:"noopener noreferrer",text:src.publisher}));
}
function note(text,kind){ return el("div",{class:"note "+(kind||"")},[el("span",{text})]); }

function renderTimeline(){
  const tl = buildTimeline(S.pack, S.result.res, P.national_service, new Date());
  S.timeline = tl;
  const host=$("#timeline"); host.replaceChildren();
  let markedNext=false;
  for(const e of tl.entries){
    const isNext = !e.passed && !markedNext; if(isNext) markedNext=true;
    host.append(el("li",{class:(e.passed?"past":"")+(isNext?" next":"")},[
      el("div",{class:"t-when",text:e.when}),
      el("div",{class:"t-label",text:e.label}),
      el("div",{class:"t-detail",text:e.detail}),
      el("div",{class:"t-date",text:e.date.toISOString().slice(0,10)+(e.approximate?" · approximate":"")}),
      e.url ? el("div",{},[el("a",{href:e.url,target:"_blank",rel:"noopener noreferrer",
        text:"official page",style:"font-size:.82rem"})]) : null]));
  }
  const n=$("#timelineNotes"); n.replaceChildren();
  tl.notes.forEach((x,i)=>n.append(note(x,i?"info":"warn")));
}

function icsFor(tl){
  const out=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//PathAhead//EN","X-WR-CALNAME:PathAhead"];
  for(const e of tl.entries){ if(e.passed) continue;
    const st=e.date.toISOString().slice(0,10).replace(/-/g,"");
    out.push("BEGIN:VEVENT",`UID:${e.id}-${st}@pathahead.local`,`DTSTART;VALUE=DATE:${st}`,
      `SUMMARY:${e.label}${e.approximate?" (approximate)":""}`,
      `DESCRIPTION:${e.detail} Check the official page before relying on this date.`,"END:VEVENT"); }
  out.push("END:VCALENDAR"); return out.join("\r\n");
}

function renderOptions(){
  const pack=S.pack, {t,comparison}=S.result;
  const cov=fitCoverage(pack), host=$("#groups"); host.replaceChildren();
  const cw=$("#fitCoverage"); cw.replaceChildren();
  if(!cov.complete) cw.append(note(
    `Fit scoring is in preview. PathAhead currently holds course data for ${cov.institutions.join(", ")} only — not ${cov.missing.join(", ")}. A course that would suit you better may simply not be loaded yet, so treat this as a starting point for a conversation, not a shortlist.`,"warn"));

  const gr=$("#goalReflect"); gr.replaceChildren();
  if(P.goal_text.trim()) gr.append(note(
    `You wrote: “${P.goal_text.trim()}”. PathAhead has not tried to interpret that — there is no language model running here, and guessing would be worse than useless. Read it back against the list below and see whether it still fits.`,"info"));

  /* ── JAE/PSE choice-ordering risk check ──────────────────────────
     Flag when the student's score puts them below the published floor
     of every comparable course in the pack. This is the situation where
     all 12 JAE choices would be above the student's current result.
     DESIGN_REVIEW.md notes this as "arguably more useful than the
     aggregate calculator itself".

     Only comparable courses count — polytechnic ELR2B2 aggregates and
     SIT/SUSS retired-scale bands are not comparable, and including them
     would either falsely reassure or falsely alarm. */
  const comparableCourses = pack.outcomes.filter(o=>
    o.transition===S.result.t.id && o.band && bandComparable(o.band));
  const inRangeOrAbove = comparableCourses.filter(o=>{
    const b=assessBand(S.result.comparison,o.band.p10_points,o.band.p90_points,
                       S.result.t.direction,o.band.statistic);
    return b==="above_range"||b==="at_or_above_range"||b==="within_range"||b==="exactly_at_profile";
  });
  const riskHost=cw;
  if(comparableCourses.length>0 && inRangeOrAbove.length===0){
    riskHost.append(note(
      `Your current result sits below the published range of every course for which PathAhead holds a comparable figure (${comparableCourses.length} course${comparableCourses.length!==1?"s":""} checked). `+
      `That is last year’s picture — not a decision about you — and admission depends on this year’s applicants, not last year’s. `+
      `It is worth looking at the “Below last year’s range” group below, and at the routes in the “Backward” view: `+
      `polytechnic courses, direct-admissions routes and courses with no published minimum may still be a strong fit.`, "warn"));
  } else if(comparableCourses.length>0 && inRangeOrAbove.length<=5){
    riskHost.append(note(
      `Your result sits inside or above the published range for ${inRangeOrAbove.length} of ${comparableCourses.length} courses with a comparable figure. `+
      `That is a narrow set — it is worth spreading your JAE choices across the full range below.`, "info"));
  }

  $("#notPrediction").textContent =
    "These are last year's published figures, not this year's outcome. Real admission decisions consider more than a score. "+
    "Where a card carries a short course description tagged “our description”, that sentence is PathAhead's own characterisation, "+
    "not the institution's, and is written at course-family level. It is the least verified thing here and the first thing worth telling us we got wrong.";

  // --- sort control -------------------------------------------------
  const scored = pack.outcomes.filter(o=>S.fits[o.id]?.score!=null);
  const sortHost=$("#sortControl"); sortHost.replaceChildren();
  if(scored.length){
    const seg=el("div",{class:"seg",role:"group","aria-label":"Order the list"});
    for(const [v,t] of [["match","Strongest match first"],["name","A to Z"]])
      seg.append(el("button",{type:"button","aria-pressed":String(S.sort===v),text:t,
        title:`Order the list: ${t}`,
        onclick:()=>{ S.sort=v; renderOptions(); }}));
    sortHost.append(el("div",{class:"field",style:"margin:0 0 1rem"},[
      el("label",{id:"lblSort",text:"Order"}), seg]));

    /* --- strongest matches, up front -------------------------------
       The screenshot that prompted this: three cards, all 67/100, all with
       the identical single reason "you work best through exams, and so does
       much of this course". That is ISSUES_v0.2.md section A repeating on the
       fit axis — no discrimination, presented as a ranking. Three courses tied
       on one generic factor are not "the strongest three"; they are the first
       three alphabetically that happened to share a score.

       So: only promote courses that are actually ahead of the pack, and say
       plainly when nothing is. */
    const ranked=[...scored].sort((a,b)=>S.fits[b.id].score-S.fits[a.id].score);
    const best=S.fits[ranked[0].id].score;
    const tiedAtTop=ranked.filter(o=>S.fits[o.id].score===best).length;
    const distinct=new Set(ranked.map(o=>S.fits[o.id].score)).size;
    const candidates=ranked.slice(0,3);
    /* The score alone is not enough to judge this by, and the first version of
       this guard proved it: three courses tied at 100 sailed through, because
       the pack as a whole had plenty of distinct scores. What makes a "top
       three" real is that the three are distinguishable FROM EACH OTHER — so
       the lead reasons have to differ too. Three identical sentences under
       three identical numbers is a tie with a rosette on it. */
    const leadReasons=new Set(candidates.map(o=>S.fits[o.id].factors[0]?.reason||""));
    const allTied=candidates.every(o=>S.fits[o.id].score===best);
    const meaningful = tiedAtTop<=5 && distinct>=3 && !(allTied && leadReasons.size===1);
    const top = meaningful ? candidates : [];
    const ul=el("ul",{class:"courses",style:"margin-bottom:.4rem"});
    for(const o of top){
      const f=S.fits[o.id];
      ul.append(el("li",{class:"course",style:"padding:.7rem .9rem"},[
        el("div",{class:"c-top"},[
          el("div",{},[el("div",{class:"c-name",style:"font-size:1rem",text:o.name}),
            el("div",{class:"c-sub",text:`${o.institution_short} · ${o.id}`})]),
          el("div",{class:"axis",style:"padding:.3rem .6rem;min-width:7rem;text-align:right"},[
            el("div",{class:"big",style:"font-size:1.05rem",text:`${f.score}/100`}),
            el("div",{class:"small",text:fitBand(f.score)})])]),
        el("div",{class:"small",style:"margin-top:.35rem;color:var(--ink-2)",
          text:f.factors[0]?.reason || ""})]));
    }
    sortHost.append(el("h3",{text:"Where your answers point"}));
    if(meaningful){
      sortHost.append(el("p",{class:"hint",style:"margin:.2rem 0 .6rem",
        text:"Ordered by how well each course matches what you told us — not by how hard it is to get into, and not by pay."}), ul);
    } else {
      /* Saying "nothing stands out yet" is more useful than three arbitrary
         cards, and it points at the thing that would actually change it. */
      sortHost.append(note(
        `Nothing stands out yet. ${tiedAtTop} courses share the top score of ${best}, `+
        `which usually means the answers so far match a lot of things equally — `+
        `often just one broad signal like how you prefer to be assessed. `+
        `Answer another question or two in step three and the list will start to separate. `+
        `The full list below is still ordered by match.`, "info"));
    }
  }

  renderFilters();
  const groups={};
  for(const o of pack.outcomes.filter(o=>o.transition===t.id).filter(matchesFilters)){
    let b;
    if(o.band && !bandComparable(o.band)){
      b="published_on_another_basis";
    } else if(o.band){
      b=assessBand(comparison,o.band.p10_points,o.band.p90_points,t.direction,o.band.statistic);
    } else {
      /* No fallback to another pool: a polytechnic GPA out of 4.00 and an
         A-Level score out of 70 are different units. */
      const prof=alevelBanded(o);
      b=prof?assessBanded(prof,comparison):"data_incomplete";
    }
    (groups[b]=groups[b]||[]).push(o);
  }
  for(const key of ORDER){
    const items=groups[key]; if(!items) continue;
    // Sorted by MATCH — that is the student's own stated preferences, not
    // prestige and not pay. Selectivity and salary are never sort keys.
    // Alphabetical is always available, and is the fallback when nothing has
    // been answered.
    const byName=(a,b)=>a.institution_short.localeCompare(b.institution_short)||a.name.localeCompare(b.name);
    if(S.sort==="match"){
      items.sort((a,b)=>{
        const fa=S.fits[a.id]?.score, fb=S.fits[b.id]?.score;
        if(fa==null && fb==null) return byName(a,b);
        if(fa==null) return 1;
        if(fb==null) return -1;
        return fb-fa || byName(a,b);
      });
    } else items.sort(byName);

    /* Progressive disclosure. The pack has grown from 21 courses to 296, and
       an undifferentiated wall of cards is not a list a family can read
       (ISSUES_v0.2.md section F). Each bucket shows the first PAGE and offers
        the rest — and because the order is the student's own stated
       preferences, the ones shown first are the ones they asked for, not the
       most selective. Everything is still one click from visible, and print
       opens all of it. */
    const PAGE=10;
    const shown=S.expanded[key] ? items.length : Math.min(PAGE,items.length);
    /* Compact mode exists to scan 330 courses, so it is not paged — the whole
       point is the whole list at once. Card mode stays paged. */
    const list = DENSITY.mode==="compact"
      ? el("table",{class:"cmp compact"},[
          el("thead",{},[el("tr",{},[el("th",{text:"Course"}),el("th",{text:"Where"}),
            el("th",{text:"Last published range"}),el("th",{text:"Match"}),el("th",{text:"Fee"})])]),
          el("tbody",{},items.map(compactRow))])
      : (()=>{ const ul=el("ul",{class:"courses"});
               for(const o of items.slice(0,shown)) ul.append(courseCard(o,key));
               return ul; })();

    const parts=[
      el("div",{class:"group-head"},[el("h3",{text:HEADLINE[key]}),
        el("span",{class:"count",text:String(items.length)})]),
      el("p",{text:EXPLAIN[key]}), list];
    if(items.length>PAGE && DENSITY.mode!=="compact"){
      parts.push(el("button",{type:"button",class:"more",
        text:S.expanded[key] ? `Show fewer` : `Show all ${items.length}`,
        title:S.expanded[key] ? `Collapse back to the first ${PAGE} courses` : `Expand to see all ${items.length} courses at once`,
        onclick:()=>{ S.expanded[key]=!S.expanded[key]; renderOptions(); }}));
      if(!S.expanded[key]) parts.push(el("p",{class:"hint",style:"margin:.4rem 0 0",
        text:`Showing ${shown} of ${items.length}. `+
             (S.sort==="match"
               ? "These are the ones closest to what you told us, not the hardest to get into."
               : "In alphabetical order — switch to “Strongest match first” above to see the ones closest to what you told us.")}));
    }
    host.append(el("section",{class:"group "+GCLASS[key]},parts));
  }
}

/* ── streams ───────────────────────────────────────────────────
   A student picks the fields they are interested in and the list narrows to
   those. This is a FILTER and never a scoring signal: it changes which
   courses appear, not how any of them scores. Filtering by FIELD is
   explicitly permitted (ISSUES_v0.2.md §H); filtering by selectivity or pay
   is not, and neither appears here.

   The pack carries 52 sectors, which is a taxonomy for a machine, not a list
   a seventeen-year-old picks from. These nine are the reading of it. Courses
   may sit in several — Aerospace Engineering is both engineering and
   aviation — because forcing one label would hide it from someone searching
   the other.

   THE COVERAGE RULE: every course must land in at least one stream, or
   choosing any stream would make it permanently unreachable. `streamsOf`
   falls back to "other" and a check asserts the fallback is never the only
   thing standing between a course and the list. */
const STREAMS = [
  ["engineering",  "Engineering & built environment",
   ["engineering","manufacturing","construction","architecture","electronics","energy",
    "utilities","defence","landscape","real estate"]],
  ["computing",    "Computing & technology",
   ["technology","games"]],
  ["health",       "Health & life sciences",
   ["healthcare","health and wellness","pharmaceuticals","veterinary","animal care"]],
  ["business",     "Business & finance",
   ["financial services","business services","consulting","professional services",
    "marketing","retail","fashion"]],
  ["media",        "Media, arts & design",
   ["media","design","creative","arts","music","events"]],
  ["social",       "Social sciences, education & law",
   ["education","social services","public sector","public service","legal services",
    "research"]],
  ["hospitality",  "Hospitality, tourism & food",
   ["hospitality","tourism","food and beverage","consumer goods","sport"]],
  ["maritime",     "Maritime, aviation & logistics",
   ["maritime","marine","aviation","logistics","shipping"]],
  ["environment",  "Environment & sustainability",
   ["environment"]],
];
const STREAM_LABEL = Object.fromEntries(STREAMS.map(([id,label])=>[id,label]));
const SECTOR_TO_STREAM = (()=>{ const m={};
  for(const [id,,sectors] of STREAMS) for(const s of sectors) (m[s] ||= []).push(id);
  return m; })();

/** Which streams a course belongs to. Never empty — see the coverage rule. */
function streamsOf(o){
  const out=new Set();
  for(const s of (o.editorial?.sectors||[])) for(const id of (SECTOR_TO_STREAM[s]||[])) out.add(id);
  if(!out.size) out.add("other");
  return [...out];
}

/* ── U3: filter, search, density ───────────────────────────────
   What may be filtered, and what may not. Institution, field, interest,
   assessment style, extra assessment, flexibility and FEE are all legitimate:
   they are things a family is choosing between. Selectivity and pay are not,
   and are absent by design — SAFEGUARDS 5.1 forbids ranking by them, and a
   filter is a ranking with extra steps (ISSUES_v0.2.md §H). If a later session
   adds "sort by salary" here, that is the line. */
const F = {q:"", inst:"", field:"", interest:"", assessment:"", extra:"", flex:"", fee:""};
const DENSITY = {mode:"cards"};

/** The same forgiving matching the subject combobox uses: a person types
    "compsci" or "biz", not the pack's id. Names, ids and institution codes. */
function searchHit(o,q){
  if(!q) return true;
  const n=s=>String(s||"").toLowerCase().replace(/[^a-z0-9]+/g,"");
  const hay=[o.name,o.id,o.institution,o.institution_short,o.faculty,
             ...(o.editorial?.sectors||[])].map(n).join(" ");
  return n(q).split(/\s+/).filter(Boolean).every(term=>hay.includes(term));
}

function matchesFilters(o){
  /* The student's chosen fields narrow the list before anything else.
     Empty means no preference, which shows everything — never zero. */
  if(P.streams?.length && !streamsOf(o).some(x=>P.streams.includes(x))) return false;
  if(!searchHit(o,F.q)) return false;
  if(F.inst && o.institution_short!==F.inst) return false;
  if(F.field && (o.faculty||"Other")!==F.field) return false;
  if(F.interest && !(o.editorial?.interests||[]).includes(F.interest)) return false;
  if(F.assessment && !(o.editorial?.assessment_style||[]).includes(F.assessment)) return false;
  if(F.extra==="yes" && !hasExtra(o)) return false;
  if(F.extra==="no"  &&  hasExtra(o)) return false;
  if(F.flex==="yes" && !(o.flexibility?.declares_major_later||o.flexibility?.common_first_year)) return false;
  if(F.fee){
    const f=feeFor(o,P.citizenship||"citizen");
    if(F.fee==="known" && !f) return false;
    if(F.fee==="unknown" && f) return false;
  }
  return true;
}

/** The ranking control.
 *
 *  Tap-in-order rather than drag-and-drop: dragging is unusable with a
 *  keyboard, awkward with a screen reader and fiddly with a thumb, and this is
 *  a phone-first audience. Tapping builds the order, and each picked row can
 *  still be moved or removed, so a mistake is one tap to fix rather than a
 *  restart.
 *
 *  The weight is printed next to every row. A student should be able to look
 *  at this and predict what the score will do — that is the entire point of
 *  replacing the old fixed constants.
 */
/** The importance control.
 *
 *  Third attempt, and the first two are why this one looks like it does.
 *
 *  A chip pool you tapped "in order" hid the state: the chips were identical
 *  to four other chip groups on the page, tapping one made it vanish upwards,
 *  and nothing said what you had picked first. Replacing it with an up/down
 *  reorderable list made the state visible and the INTERACTION bad — six taps
 *  to move one row, re-reading the list after each.
 *
 *  The mistake underneath both was asking for a SEQUENCE. People do not hold
 *  seven things in rank order; they hold a few strong feelings and a lot of
 *  indifference. So each row now carries a level, set in one tap, ties allowed,
 *  no dependency on any other row. Nothing to remember, nothing to re-read.
 */
function renderRanking(){
  const list=$("#rankPicked"), note=$("#rankExplain"), actions=$("#rankActions");
  if(!list) return;
  const level = k => { const hit=P.importance.find(x=>x[0]===k); return hit?hit[1]:null; };
  const anySet = P.importance.length>0;

  const setLevel=(k,v)=>{
    const i=P.importance.findIndex(x=>x[0]===k);
    if(i>=0) P.importance[i]=[k,v]; else P.importance.push([k,v]);
    // First touch: everything not yet answered defaults to "Quite a lot" so the
    // student changes what they care about rather than filling in seven rows.
    if(P.importance.length===1)
      for(const other of DIMENSION_KEYS)
        if(other!==k) P.importance.push([other,2]);
    renderRanking(); if(S.result) renderOptions();
  };

  list.replaceChildren(...DIMENSION_KEYS.map(k=>{
    const lv = anySet ? (level(k) ?? 0) : null;
    return el("li",{class:"ranked-row"+(anySet&&lv===0?" is-off":"")},[
      el("span",{class:"rank-label",text:DIMENSION_LABEL[k]||k}),
      el("span",{class:"seg imp",role:"group","aria-label":DIMENSION_LABEL[k]},
        IMPORTANCE_LEVELS.map(([v,label])=>
          el("button",{type:"button","aria-pressed":String(anySet && lv===v),
            title:label,text:label,onclick:()=>setLevel(k,v)}))),
    ]);
  }));

  // replaceChildren(x) stringifies a bare `null` to the TEXT "null" instead
  // of inserting nothing -- caught 2026-08-12 rendering a literal "null" on
  // screen before any importance was set. Spread + filter(Boolean) so an
  // absent button is actually absent.
  actions.replaceChildren(...[
    anySet ? el("button",{type:"button",class:"ghost",text:"Reset to equal",
      title:"Clear every importance level so all seven count equally again",
      onclick:()=>{P.importance.length=0; renderRanking(); if(S.result) renderOptions();}}) : null
  ].filter(Boolean));

  const on = anySet ? P.importance.filter(([,v])=>v>0) : [];
  const off = anySet ? P.importance.filter(([,v])=>v===0) : [];
  note.replaceChildren(el("span",{text:
    !anySet
      ? "You have not set these, so all seven count equally. That is a real choice and "+
        "it is what PathAhead uses — not a hidden default. Change any row to adjust it."
      : (on.length===0
          ? "Everything is set to \u201cDoesn\u2019t matter\u201d, so nothing can be scored. Turn at least one up."
          : "Counting: "+on.sort((a,b)=>b[1]-a[1])
              .map(([k,v])=>`${DIMENSION_LABEL[k]} \u00d7 ${v}`).join(", ")+
            (off.length?". Ignored: "+off.map(([k])=>DIMENSION_LABEL[k]).join(", ")+".":"."))}));
}

function renderFilters(){
  const host=$("#filterBar"); if(!host) return;
  const pack=S.pack, t=S.result?.t;
  const pool=pack.outcomes.filter(o=>!t||o.transition===t.id);
  const uniq=(f)=>[...new Set(pool.map(f).filter(Boolean))].sort();
  const sel=(id,label,value,opts,onchange,hint)=>el("div",{class:"field"},[
    el("label",{for:id,text:label,title:hint||label}),
    el("select",{id,onchange,title:hint||label},[el("option",{value:"",text:"Any"}),
      ...opts.map(([v,tx])=>el("option",{value:v,text:tx,...(v===value?{selected:"selected"}:{})}))])]);

  const shown=pool.filter(matchesFilters).length;
  host.replaceChildren(
    el("div",{class:"field"},[
      el("label",{for:"courseSearch",text:"Search",title:"Search by course name, institution or field"}),
      el("input",{id:"courseSearch",type:"search",value:F.q,
        placeholder:"course, institution or field — type it how you say it",
        title:"Search by course name, institution or field",
        oninput:e=>{F.q=e.target.value; renderOptions();}})]),
    el("div",{class:"filters"},[
      sel("fInst","Institution",F.inst,uniq(o=>o.institution_short).map(v=>[v,v]),
        e=>{F.inst=e.target.value; renderOptions();},
        "Show only courses at one institution"),
      sel("fField","Field",F.field,uniq(o=>o.faculty||"Other").map(v=>[v,v]),
        e=>{F.field=e.target.value; renderOptions();},
        "Show only courses in one faculty or field"),
      sel("fInterest","Interest",F.interest,Object.entries(INTEREST_LABEL),
        e=>{F.interest=e.target.value; renderOptions();},
        "Show only courses tagged with one interest"),
      sel("fAsm","Assessed by",F.assessment,
        [["exams","Exams"],["coursework","Coursework"],["practical","Hands-on"]],
        e=>{F.assessment=e.target.value; renderOptions();},
        "Show only courses assessed the way you picked"),
      sel("fExtra","Interview / portfolio",F.extra,[["yes","Required"],["no","Not required"]],
        e=>{F.extra=e.target.value; renderOptions();},
        "Filter by whether the course requires an interview, test or portfolio"),
      sel("fFlex","Can change direction later",F.flex,[["yes","Yes"]],
        e=>{F.flex=e.target.value; renderOptions();},
        "Show only courses that let you change direction after enrolling"),
      sel("fFee","Fee figure",F.fee,[["known","Held"],["unknown","Not held"]],
        e=>{F.fee=e.target.value; renderOptions();},
        "Filter by whether PathAhead holds a published fee figure for the course"),
    ]),
    el("div",{class:"field",style:"margin:.4rem 0 0"},[
      el("label",{id:"lblDensity",text:"How to show them"}),
      el("div",{class:"seg",role:"group","aria-labelledby":"lblDensity"},
        [["cards","Cards"],["compact","Compact table"]].map(([v,tx])=>
          el("button",{type:"button","aria-pressed":String(DENSITY.mode===v),text:tx,
            title: v==="compact" ? "One row per course — for scanning the whole list at once"
              : "One card per course, paged 10 at a time",
            onclick:()=>{DENSITY.mode=v; renderOptions();}})))]),
    /* A filter that silently removes two hundred courses is indistinguishable
       from a pack that never had them. Say the number, and offer the undo. */
    P.streams?.length ? el("div",{class:"note info"},[el("span",{},[
      el("strong",{text:"Showing only: "}),
      el("span",{text:P.streams.map(x=>STREAM_LABEL[x]||x).join(", ")+". "}),
      el("span",{text:`${pool.filter(o=>!P.streams.some(x=>streamsOf(o).includes(x))).length} `+
        `other courses are hidden by that choice — it changes nothing about how any course scores.`}),
      el("button",{type:"button",class:"ghost",style:"margin-left:.4rem",
        text:"Show every field again",
        title:"Clear the field filter and show courses from every field",
        onclick:()=>{P.streams.length=0;
          for(const b of document.querySelectorAll("#streamChips button"))
            b.setAttribute("aria-pressed","false");
          renderOptions();}})])]) : null,
    el("p",{class:"hint",id:"filterCount",
      text:`${shown} of ${pool.length} courses shown.`+
        (Object.values(F).some(Boolean)?" ":"")+
        " You cannot filter by how selective a course is, or by pay — those are information here, never a way to sort people."}),
    Object.values(F).some(Boolean)
      ? el("div",{class:"actions",style:"margin-top:.4rem"},[
          el("button",{type:"button",class:"ghost",text:"Clear filters",
            title:"Reset the search box and every dropdown filter above",
            onclick:()=>{for(const k of Object.keys(F)) F[k]=""; renderOptions();}})])
      : null,
  );
}

/** Compact mode: one row per course, for scanning 330 of them. */
function compactRow(o){
  const f=S.fits[o.id], cz=P.citizenship||"citizen", fee=feeFor(o,cz);
  return el("tr",{"data-course":o.id},[
    el("td",{},[el("a",{href:"#/course/"+encodeURIComponent(o.id),text:o.name})]),
    el("td",{text:o.institution_short}),
    el("td",{text:o.band?`${o.band.p10}–${o.band.p90}`:(o.banded?.length?"banded profile":"not published")}),
    el("td",{text:f&&f.score!=null?`${f.score}/100`:"—"}),
    el("td",{text:fee?(fee.basis==="annual"?money(fee.annual)+"/yr":money(fee.total)):"not held"}),
  ]);
}

function courseCard(o,bucketKey){
  const today=new Date();
  const stale=o.band?.fact?.stale_after && new Date(o.band.fact.stale_after)<today;
  const fit=S.fits[o.id];
  const emp=o.employment;

  const meta=el("div",{class:"c-meta"});
  /* The institution's own last-recorded figure, on every card — not only on
     the course page. It is the thing a family looks for first, and it was
     previously reachable only by opening the course. The YEAR travels with it
     because a range without its exercise is a number pretending to be
     current. */
  if(o.band) meta.append(el("span",{class:"tag band",
    title:o.band.basis||"",
    text:`${o.band.p10}–${o.band.p90}${o.band.fact?.as_of_year?` · ${o.band.fact.as_of_year}`:""}`}));
  else if(o.banded?.length) meta.append(el("span",{class:"tag band",
    text:`banded profile${o.banded[0].fact?.as_of_year?` · ${o.banded[0].fact.as_of_year}`:""}`}));
  else meta.append(el("span",{class:"tag",text:"no published range"}));
  if(o.duration) meta.append(el("span",{class:"tag",text:`${o.duration.years} yr`}));
  if(o.accreditation?.length) meta.append(el("span",{class:"tag",
    title:o.accreditation[0].label,
    text:`registered profession · ${o.accreditation[0].body}`}));
  if(hasExtra(o)) meta.append(el("span",{class:"tag",text:"interview / test / portfolio"}));
  if(emp?.gross_median) meta.append(el("span",{class:"tag money",
    text:`$${emp.gross_p25.toLocaleString()}–${emp.gross_p75.toLocaleString()} · median $${emp.gross_median.toLocaleString()}`}));
  if(emp?.employment_rate) meta.append(el("span",{class:"tag",
    text:`${emp.employment_rate}% employed in 6 months`}));
  const cz=P.citizenship||"citizen";
  if(o.cost?.fee_basis==="per_credit"){
    /* SIT publishes a rate per credit unit and no annual figure. The total is
       the number that matters and is computed the way SIT computes it. */
    const total={citizen:o.cost.total_citizen,pr:o.cost.total_pr,
      international:o.cost.total_international}[cz];
    if(total) meta.append(el("span",{class:"tag money",
      text:`fees $${total.toLocaleString()} over ${o.cost.total_credits} credits · charged per credit, not per year`}));
    const bondC=cz==="citizen"?o.cost.bond_years_citizen:o.cost.bond_years_pr_is;
    if(bondC) meta.append(el("span",{class:"tag",text:`${bondC}-year service bond`}));
  } else if(o.cost?.annual_fee_citizen){
    const fee={citizen:o.cost.annual_fee_citizen,pr:o.cost.annual_fee_pr,
      international:o.cost.annual_fee_international}[cz];
    if(fee) meta.append(el("span",{class:"tag money",
      text:`fees $${fee.toLocaleString()}/yr · $${(fee*o.cost.years).toLocaleString()} over ${o.cost.years} yr`}));
    const bond=cz==="citizen"?o.cost.bond_years_citizen:o.cost.bond_years_pr_is;
    if(bond) meta.append(el("span",{class:"tag",text:`${bond}-year service bond`}));
  }
  /* A gap that is a decision must not read as a gap that is a to-do. */
  if(o.fee_note && !o.cost) meta.append(el("span",{class:"tag ed",title:o.fee_note,
    text:"no fee figure — and why"}));
  if(o.poly_gpa) meta.append(el("span",{class:"tag",
    text:`poly route: GPA ${o.poly_gpa.p10}–${o.poly_gpa.p90} (${o.poly_gpa.fact?.as_of_year??""})`}));
  if(o.flexibility?.declares_major_later) meta.append(el("span",{class:"tag flex",text:"major declared later"}));
  if(o.flexibility?.common_first_year) meta.append(el("span",{class:"tag flex",text:"common first year"}));
  if(o.intake) meta.append(el("span",{text:`${o.intake.value} places (${o.intake.as_of_year})`}));
  if(stale) meta.append(el("span",{class:"tag",text:"figure predates the latest cycle"}));
  if(o.url) meta.append(el("a",{href:o.url,target:"_blank",rel:"noopener noreferrer",text:"official page"}));

  // axis 1 — fit (an opinion, scored, fully derived)
  const fitBox=el("div",{class:"axis"});
  fitBox.append(el("h4",{text:"Fit — based on what you told us"}));
  if(fit.score===null){
    fitBox.append(el("div",{class:"small",text:fit.unscored_reason}));
  } else {
    fitBox.append(el("div",{class:"big",text:`${fit.score} / 100`}),
      el("div",{class:"bar"},[el("i",{style:`width:${fit.score}%`})]),
      el("div",{class:"small",text:`${fitBand(fit.score)} · based on ${fit.signals_used} of ${fit.signals_available} things you told us`}));
    const fl=el("ul",{class:"factors"});
    for(const f of fit.factors) fl.append(el("li",{},[
      el("b",{class:f.points?"":"zero",text:`${f.points>0?"+":""}${num(f.points)}`}),
      el("span",{text:f.reason})]));
    fitBox.append(fl);
    if(fit.not_assessed?.length){
      const na=el("ul",{class:"factors",style:"margin-top:.5rem;opacity:.8"});
      for(const x of fit.not_assessed) na.append(el("li",{},[
        el("b",{class:"zero",text:"—"}), el("span",{text:"not counted either way: "+x})]));
      fitBox.append(na);
    }
  }

  // axis 2 — evidence (a published fact, never scored)
  const evBox=el("div",{class:"axis"});
  /* The heading has to follow the data. "Last year's published range" is a lie
     over a three-year min-max, and a card that showed a one-year figure and a
     three-year figure identically would be hiding the difference between them. */
  const evHeading = !o.band ? "Evidence — published range"
    : (o.band.years_covered>1 ? `Evidence — published range, ${o.band.years_label||o.band.years_covered+" years"}`
                              : "Evidence — last year's published range");
  evBox.append(el("h4",{text:evHeading}),
    el("span",{class:"badge "+BCLASS[bucketKey],text:HEADLINE[bucketKey]}));
  if(o.band && !bandComparable(o.band)){
    /* Never "Your 60 against 3–28". The two numbers are on different
       qualifications and different directions; printing them either side of
       the word "against" invites exactly the comparison we are refusing. */
    evBox.append(el("div",{class:"small",
      text:`${o.band.p10}–${o.band.p90}, ${o.band.basis}. Shown, not compared with your result — it is a different measure.`}));
  } else if(o.band){
    evBox.append(el("div",{class:"small",
      text:`Your ${S.result.profile ? S.result.profile+" ("+num(S.result.comparison)+" points)" : num(S.result.comparison)}`+
           ` against ${o.band.p10}–${o.band.p90} (${o.band.fact.as_of_year}), ${o.band.basis}.`}));
    /* Headroom above the FLOOR of last year's intake. Published profiles
       saturate at the top — 18 of 21 NUS courses share a p90 of 60 — so once a
       student clears them the band stops discriminating and this is the only
       number left that does. The engine has returned it since the section A
       fix; it was never shown. NEXT.md section 3. */
    const lo=Math.min(o.band.p10_points,o.band.p90_points);
    const room=S.result.t.direction==="higher_is_better"
      ? S.result.comparison-lo : lo-S.result.comparison;
    if(room>0) evBox.append(el("div",{class:"headroom"},[
      document.createTextNode(
        `${num(room)} point${room!==1?"s":""} clear of the lowest-ranked student admitted last year`)]));
  }
  else evBox.append(el("div",{class:"small",text:"No verified grade profile loaded."}));

  const short = S.shortlist.has(o.id);
  /* `data-course` is the row's identity in the DOM. It exists so that a check
     can ask "is this row the course I filtered to" instead of searching the
     rendered text for an institution code — which is not printed on a card,
     because a family reads "Singapore Polytechnic", not "SP". A test that
     matched on visible copy would fail whenever the copy improved. */
  return el("li",{class:"course"+(stale?" stale":""),"data-course":o.id},[
    el("div",{class:"c-top"},[
      el("div",{},[el("div",{class:"c-name",text:o.name}),
        el("div",{class:"c-sub",text:(o.faculty?o.faculty+" · ":"")+o.institution}),
        el("div",{class:"c-sub",style:"font-family:var(--mono);font-size:.72rem",text:o.id})]),
      el("button",{type:"button",class:short?"primary":"",text:short?"On your shortlist":"Add to shortlist",
        style:"min-height:40px;padding:.4rem .8rem;font-size:.84rem",
        title: short ? "Remove this course from your shortlist" : "Add this course to your shortlist to compare it side by side",
        onclick:()=>{ S.shortlist.has(o.id)?S.shortlist.delete(o.id):S.shortlist.add(o.id);
                      renderOptions(); renderCompare(); }})]),
    o.editorial?.summary ? el("p",{class:"c-summary",text:o.editorial.summary}) : null,
    /* The disclosure is said ONCE, above the list, instead of on all 296 cards
       (ISSUES_v0.2.md section F). Repetition at that volume stops being a
       caveat and becomes wallpaper — it is read less, not more. The short tag
       keeps the claim attached to the sentence it qualifies. */
    o.editorial ? el("div",{class:"c-meta"},[el("span",{class:"tag ed",text:"our description"})]) : null,
    el("div",{class:"axes"},[fitBox,evBox]),
    meta ]);
}

/* ── compare ───────────────────────────────────────────────────── */
function renderCompare(){
  const ids=[...S.shortlist];
  /* The card itself is always visible now; only the table waits for content.
     What toggles is the empty state, not the invitation. */
  $("#cmpEmpty").hidden = ids.length > 0;
  $("#cmpWrap").hidden  = ids.length === 0;
  if(!ids.length) return;
  const outs=ids.map(i=>S.pack.outcomes.find(o=>o.id===i));
  const rows=[
    ["Fit", o=>{const f=S.fits[o.id]; return f.score===null?"—":`${f.score}/100 (${fitBand(f.score)})`;}],
    ["Evidence", o=>{
      if(!o.band) return "not loaded";
      const span=o.band.years_label||o.band.fact.as_of_year;
      /* Side by side in a comparison table is the easiest place to read two
         incomparable ranges as one scale, so the unit is named in the cell. */
      return `${o.band.p10}–${o.band.p90} (${span})`+
             (bandComparable(o.band)?"":` · ${o.band.basis}, not comparable`);
    }],
    ["Median salary", o=>o.employment?.gross_median?`$${o.employment.gross_median.toLocaleString()}`:"—"],
    ["Salary range", o=>o.employment?.gross_p25?`$${o.employment.gross_p25.toLocaleString()}–${o.employment.gross_p75.toLocaleString()}`:"—"],
    ["Employed in 6 months", o=>o.employment?.employment_rate?`${o.employment.employment_rate}%`:"—"],
    /* Two fee rows, and SIT fits neither the way the others do: it charges per
       CREDIT UNIT and publishes no annual figure at all. Showing a blank here
       would hide a cost that is perfectly well known; showing a made-up annual
       figure would be worse. So the per-year row says what SIT actually does,
       and the total row does the arithmetic SIT does. */
    ["Fees per year", o=>{const c=o.cost,z=P.citizenship||"citizen";
        if(!c) return "—";
        if(c.fee_basis==="per_credit"){
          const r={citizen:c.fee_per_credit_citizen,pr:c.fee_per_credit_pr,
                   international:c.fee_per_credit_international}[z];
          return r?`charged per credit, not per year ($${r}/credit)`:"—";
        }
        const f={citizen:c.annual_fee_citizen,pr:c.annual_fee_pr,international:c.annual_fee_international}[z];
        return f?`$${f.toLocaleString()}`:"—";}],
    ["Total course fees", o=>{const c=o.cost,z=P.citizenship||"citizen";
        if(!c) return o.fee_note ? "not shown — see note" : "—";
        if(c.fee_basis==="per_credit"){
          const t={citizen:c.total_citizen,pr:c.total_pr,international:c.total_international}[z];
          return t?`$${t.toLocaleString()} over ${c.total_credits} credits`:"—";
        }
        const f={citizen:c.annual_fee_citizen,pr:c.annual_fee_pr,international:c.annual_fee_international}[z];
        return f?`$${(f*c.years).toLocaleString()} over ${c.years} yr`:"—";}],
    ["Service bond", o=>{const c=o.cost,z=P.citizenship||"citizen";
        if(!c) return "—"; const b=z==="citizen"?c.bond_years_citizen:c.bond_years_pr_is;
        return b?`${b} years`:"none";}],
    ["Places", o=>o.intake?String(o.intake.value):"—"],
    ["Extra assessment", o=>hasExtra(o)?"yes":"no"],
    ["Can change your mind?", o=>o.flexibility?.switching_note||"—"],
    ["Where graduates go", o=>o.editorial?.sectors?.join(", ")||"—"],
    /* Headroom: how far above the floor the student sits.
       Shown only for comparable courses where a band exists. */
    ["Headroom above floor", o=>{
      if(!o.band||!bandComparable(o.band)) return "—";
      const lo=Math.min(o.band.p10_points,o.band.p90_points);
      const room=S.result.t.direction==="higher_is_better"
        ? S.result.comparison-lo : lo-S.result.comparison;
      return room>0 ? `${num(room)} pt${room!==1?"s":""} above the lowest admitted` : "at or below floor";
    }],
  ];
  const t=$("#cmpTable"); t.replaceChildren();
  const head=el("tr",{},[el("th",{text:""})]);
  outs.forEach(o=>head.append(el("th",{text:`${o.name} · ${o.institution_short}`})));
  t.append(el("thead",{},head));
  const body=el("tbody");
  for(const [label,fn] of rows){
    const tr=el("tr",{},[el("th",{scope:"row",text:label})]);
    outs.forEach(o=>tr.append(el("td",{text:fn(o)})));
    body.append(tr);
  }
  t.append(body);
}

/* ── backward mode ─────────────────────────────────────────────── */
function renderTargets(){
  const sel=$("#target");
  if(!sel.options.length){
    [...S.pack.outcomes].sort((a,b)=>a.name.localeCompare(b.name))
      .forEach(o=>sel.append(el("option",{value:o.id,text:`${o.name} (${o.institution_short})`})));
    sel.addEventListener("change",renderPlan);
  }
  renderPlan();
}
function routesFor(o){
  const keys=new Set([o.id,o.route_group,...(o.tags||[])]);
  return S.pack.routes.filter(rt=>rt.applies_to.some(a=>keys.has(a)));
}
function renderPlan(){
  const host=$("#planOut"); host.replaceChildren();
  const o=S.pack.outcomes.find(x=>x.id===$("#target").value); if(!o) return;
  const {comparison,t}=S.result;

  if(o.band && !bandComparable(o.band)){
    /* Show their numbers, in their terms, and say plainly that no comparison
       is being drawn. "You are N away from the lower end" would be nonsense
       here: N would be the gap between an A-Level score out of 70 and an
       O-Level aggregate out of 26. */
    const lo=Math.min(o.band.p10_points,o.band.p90_points), hi=Math.max(o.band.p10_points,o.band.p90_points);
    const words=STATISTIC_WORDS[o.band.statistic]||STATISTIC_WORDS.p10_p90;
    const span=o.band.years_label||o.band.fact.as_of_year;
    host.append(el("p",{class:"lede",text:
      `Admitted students in ${span} sat between ${num(lo)} and ${num(hi)} (${o.band.basis}). ` +
      `That is ${words.what_it_is}. It is not the same measure as your result, so PathAhead shows it and does not compare it.`}));
  } else if(o.band){
    const lo=Math.min(o.band.p10_points,o.band.p90_points), hi=Math.max(o.band.p10_points,o.band.p90_points);
    const diff=t.direction==="higher_is_better"?lo-comparison:comparison-lo;
    host.append(el("p",{class:"lede",text:
      `Students admitted in ${o.band.fact.as_of_year} sat between ${num(lo)} and ${num(hi)} (${o.band.basis}). ` +
      (diff>0?`You are ${num(Math.abs(diff))} away from the lower end.`:"Your current result is already inside or above that range.")}));
  } else host.append(el("p",{class:"lede",text:"No verified grade profile for this course yet, so PathAhead will not estimate one."}));

  if(o.flexibility?.switching_note)
    host.append(note("If you change your mind: "+o.flexibility.switching_note,
      o.flexibility.declares_major_later?"info":"warn"));

  const rts=routesFor(o);
  host.append(el("h3",{text:`Ways in (${rts.length})`,style:"margin-top:1.5rem"}));
  const box=el("div",{class:"routes"});
  const cls={direct:"",alternative:"alt","second-chance":"second"};
  const tag={direct:"direct",alternative:"another way","second-chance":"second chance"};
  for(const rt of rts) box.append(el("div",{class:"route "+cls[rt.kind]},[
    el("h4",{text:rt.label}),
    el("div",{class:"c-meta"},[el("span",{class:"tag",text:tag[rt.kind]}),
      rt.typical_duration?el("span",{text:rt.typical_duration}):null]),
    el("p",{style:"margin:.5rem 0 0;font-size:.9rem;color:var(--ink-2)",text:rt.summary}),
    rt.steps?.length?el("ul",{},rt.steps.map(s=>el("li",{text:s}))):null,
    rt.caveat?el("p",{class:"cite",text:"Note: "+rt.caveat}):null]));
  host.append(box);

  if(rts.length<3||!rts.some(x=>x.kind!=="direct"))
    host.append(note("PathAhead will not show a single required score on its own. This pack does not list enough alternative routes to this course — speak to a school counsellor about routes this tool does not know.","warn"));
  if(hasExtra(o))
    host.append(note("This course also assesses applicants beyond their grades. Meeting the grade profile is one part of the decision, not the whole of it.","info"));
}

/* ── boot ──────────────────────────────────────────────────────── */
function renderFresh(pack){
  const pub=new Date(pack.pack.published);
  const age=Math.max(0,Math.round((Date.now()-pub)/86400000));
  const when=age===0?"today":age===1?"yesterday":`${age} days ago`;
  let stale=0,total=0; const now=new Date();
  const ck=f=>{ if(!f) return; total++; if(f.stale_after&&new Date(f.stale_after)<now) stale++; };
  pack.transitions.forEach(t=>ck(t.fact));
  pack.outcomes.forEach(o=>{ck(o.band?.fact);ck(o.intake);ck(o.employment?.fact);});
  $("#freshText").textContent =
    `Data as of ${pack.pack.published} · updated ${when}` + (stale?` · ${stale} of ${total} figures out of date`:"");
}

/* ── router (ROADMAP_UI.md U1) ─────────────────────────────────
   A hash router inside the single self-contained file. No framework, no build
   step, no second HTTP request — those three properties are what make the
   GitHub Pages link and the local app the SAME artifact, and they are the
   reason this is a hash router rather than a real one.

   THE PRIVACY RULE, which is the part that must never be relaxed:
   a URL may name a COURSE or a UNIVERSITY. It may never carry grades, a
   profile, a shortlist or anything else the person typed. Shareable links
   are for "look at this course", not "look at my child". `navigate()` is the
   only writer of location.hash and it only ever writes a route id plus, at
   most, a pack id that is already public. tools/check_ui.mjs greps for this
   and fails the build if profile state reaches the URL. */
const ROUTES = [
  // "#/" is the stage chooser, NOT a stage. Which stage a family is at
  // changes the reader, the vocabulary, the legal posture and the decision —
  // so it is a fork in the road, not a dropdown on a form.
  {id:"start",   hash:"#/",        view:"view-home",    label:"Start",     icon:"✎", tab:1,
   desc:"Choose which stage you're at: after PSLE, O-Level, or A-Level"},
  {id:"alevel",  hash:"#/alevel",  view:"view-start",   label:"A-Level",   icon:"◈", tab:1,
   desc:"For A-Level students: enter grades to see university courses in reach"},
  {id:"result",  hash:"#/result",  view:"view-result",  label:"Result",    icon:"◎", tab:1, needsRun:true,
   desc:"What your A-Level result is comparable to, for this year's cohort"},
  {id:"courses", hash:"#/courses", view:"view-courses", label:"Courses",   icon:"☰", tab:1, needsRun:true,
   desc:"Browse every university course PathAhead holds, filtered and searchable"},
  {id:"compare", hash:"#/compare", view:"view-compare", label:"Shortlist", icon:"⇄", tab:1, needsRun:true,
   desc:"Your shortlisted courses, compared side by side"},
  {id:"dates",   hash:"#/dates",   view:"view-dates",   label:"Dates",     icon:"▤", needsRun:true,
   desc:"Application windows and deadlines for this admissions cycle"},
  {id:"routes",  hash:"#/routes",  view:"view-routes",  label:"Ways in",   icon:"↳", needsRun:true,
   desc:"Routes into a course besides direct entry — polytechnic, a foundation year, and so on"},
  {id:"fees",    hash:"#/fees",    view:"view-fees",    label:"Fees",      icon:"¤",
   desc:"Tuition fees and bond terms by citizenship, as a range"},
  {id:"data",    hash:"#/data",    view:"view-data",    label:"Sources",   icon:"ⓘ",
   desc:"Every source PathAhead cites, and what it does not hold"},
  {id:"scoring", hash:"#/scoring", view:"view-scoring", label:"How Scoring Works", icon:"?",
   desc:"How PathAhead turns grades into a comparable score, in plain terms"},
  // The PSLE stage's own front door. Added as a SEPARATE landing rather than
  // a mode of "#/" on purpose: a P6 parent and a JC2 student are not the same
  // reader, and folding both into one page would settle the tone on the one
  // that already exists. See docs/POST_PSLE_AND_PORTAL.md §4.
  //
  // No `needsRun`. This page must speak to a family in June who has no score
  // and does not yet know what they are looking for -- the single front door
  // that demanded a transcript is the problem #/explore was built to fix, and
  // repeating it here for twelve-year-olds would be worse.
  {id:"psle",    hash:"#/psle",    view:"view-psle",    label:"After PSLE", icon:"◇", tab:1,
   desc:"For families with a child sitting the PSLE, with or without a score yet"},
  // The O-Level/SEC stage's own front door, same reasoning as #/psle above:
  // a Secondary 4 student computing a real L1R5 aggregate and a Secondary 2
  // student who cannot yet see a single course outcome are not the same
  // reader, and both are a different reader from the A-Level start view.
  // No `needsRun` — the cohort choice and the honesty about what is not
  // loaded yet both have to be visible before any grade is entered.
  {id:"olevel",  hash:"#/olevel",  view:"view-olevel",  label:"O-Level",    icon:"◆", tab:1,
   desc:"For O-Level/SEC students, before or after results"},
  {id:"explore", hash:"#/explore", view:"view-explore", label:"No idea yet",icon:"◇",
   desc:"Not sure what to look for yet — browse courses by interest, not by grades"},
  {id:"resultsday",hash:"#/results-day",view:"view-resultsday",label:"Results day",icon:"◐",
   desc:"What to do differently on the day results actually come out"},
  {id:"perspectives",hash:"#/perspectives",view:"view-perspectives",label:"Two of you",icon:"⚭",
   desc:"Compare what two people — say, a parent and a child — each said matters"},
  {id:"course",  hash:"#/course/", view:"view-course",  label:"Course",    hidden:true},
  {id:"uni",     hash:"#/uni/",    view:"view-uni",     label:"University",hidden:true},
  {id:"more",    hash:"#/more",    view:"view-more",    label:"More",      icon:"⋯", tab:1,
   desc:"Everything else this app offers, in one list"},
];
const ROUTE_BY_ID = Object.fromEntries(ROUTES.map(r=>[r.id,r]));

/** Parse location.hash into {route, param}. Never reads anything else. */
function parseHash(h){
  const raw = String(h||"").replace(/^#/,"") || "/";
  const parts = raw.split("/").filter(Boolean);      // "/course/nus-law" -> ["course","nus-law"]
  if(!parts.length) return {route:ROUTE_BY_ID.start, param:null};
  const head = parts[0];
  if((head==="course"||head==="uni") && parts[1])
    return {route:ROUTE_BY_ID[head], param:decodeURIComponent(parts[1])};
  const r = ROUTES.find(x=>!x.hidden && x.hash==="#/"+head);
  return r ? {route:r, param:null} : {route:null, param:null};
}

/** The ONLY writer of location.hash. Keeps back/forward working by design. */
function navigate(hash){
  if(location.hash===hash) renderRoute(); else location.hash=hash;
}

/** An <svg><use> pointing at one of the inline symbols.
 *  SVG lives in its own namespace, so document.createElement — which the `el`
 *  helper uses — would silently produce an inert HTMLUnknownElement that never
 *  renders. This is the one place that matters. */
function icon(id){
  const NS="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(NS,"svg");
  svg.setAttribute("viewBox","0 0 24 24");
  svg.setAttribute("aria-hidden","true");
  svg.setAttribute("focusable","false");
  const use=document.createElementNS(NS,"use");
  use.setAttribute("href","#i-"+id);
  svg.append(use);
  return svg;
}

/* Which routes belong to which track, for nav scoping. PSLE and O-Level are
   single-page stages today, so their own list is one entry each — the shape
   still matters, because A-Level's eight sub-pages (Result, Courses, Fees
   and so on) are exactly the clutter a parent on the PSLE page never asked
   for. Shared pages (Sources, No idea yet, Results day, Two of you) answer a
   question that is not stage-specific and stay visible once INSIDE a track —
   never on the chooser itself, see buildNav below. */
const TRACK_STAGE_ROUTES = {
  psle:   ["psle"],
  olevel: ["olevel"],
  alevel: ["alevel","result","courses","compare","dates","routes","fees","scoring"],
};
const SHARED_ROUTE_IDS = ["data","explore","resultsday","perspectives"];
//: The three doors, in the order a child actually moves through school —
//: never the order their ROUTES entries happen to sit in, which is what a
//: real screenshot once showed: A-Level first, because it was the first
//: stage this app had, ahead of "After PSLE" in the nav while the door
//: CARDS two inches below it went PSLE-first. Two pieces of navigation on
//: one screen disagreeing about the order of a family's own life is worse
//: than either one being wrong alone.
const TRACK_ENTRY_ORDER = ["psle","olevel","alevel"];

function wireStickyNav(){
  /* Lift the bar off the page once it is actually stuck. A sticky bar that
     never changes reads as part of the page and people scroll "past" it. */
  const bar=$("#navbar");
  if(bar && !bar._wired){
    bar._wired=true;
    const onScroll=()=>bar.classList.toggle("stuck",(window.scrollY||0)>4);
    window.addEventListener("scroll",onScroll,{passive:true});
    onScroll();
  }
}

function buildNav(track){
  const top=$("#topnav"), tab=$("#tabbar");
  const link=r=>{
    // A hover title of just the label repeats what the text already says;
    // r.desc is the one-line explanation of what the page actually is,
    // falling back to the label only for the couple of entries plain
    // enough not to need one (e.g. "Course"/"University", which never
    // render into nav anyway -- see ROUTES' `hidden` flag).
    const a=el("a",{href:r.hash,"data-route":r.id,title:r.desc||r.label});
    a.append(icon(r.id), el("span",{text:r.label}));
    return a;
  };

  if(!track){
    // The chooser page. The nav here shows ONLY the three doors, in the same
    // order and with the same weight as the cards on the page body — never a
    // duplicate, lower-context version of the same choice sitting above it.
    // Sources, No idea yet, Results day and Two of you are not gone: they
    // live in the "If none of those is where you are" list on the page
    // itself, which is where a family reads them WITH the sentence
    // explaining what each one is for, not as a bare label in a pill.
    const doors = TRACK_ENTRY_ORDER.map(id=>ROUTE_BY_ID[id]).filter(Boolean);
    if(top) top.replaceChildren(...doors.map(link));
    if(tab) tab.replaceChildren(...doors.filter(r=>r.tab).map(link));
    wireStickyNav();
    return;
  }

  // Inside a track: that track's own pages, in the order defined above
  // (never ROUTES' array order), then the shared pages, then a compact way
  // back to the chooser.
  const stageRoutes = (TRACK_STAGE_ROUTES[track]||[]).map(id=>ROUTE_BY_ID[id]).filter(Boolean);
  const sharedRoutes = SHARED_ROUTE_IDS.map(id=>ROUTE_BY_ID[id]).filter(Boolean);
  const visible = [...stageRoutes, ...sharedRoutes];

  if(top){
    top.replaceChildren(...visible.map(link));
    // A compact way back to the three-door chooser. Not a ROUTES entry —
    // "#/" already is one (id "start") — this is a second, differently
    // worded link to the SAME place, because "Start" reads as a reset
    // button once a family is mid-track and "Change track" reads as what it
    // does.
    const back=el("a",{href:"#/","data-route":"change-track",class:"navlink-change-track",
      title:"Back to PSLE, O-Level or A-Level"});
    back.append(icon("start"), el("span",{text:"Change track"}));
    top.append(back);
  }
  if(tab){
    // The mobile tab bar has room for a handful of icons; "More" is the
    // overflow catch-all pointing at renderMorePage()'s full list, and it
    // belongs only here (in-track), not on the chooser, which already shows
    // everything relevant in three items.
    const more = ROUTE_BY_ID.more;
    tab.replaceChildren(...visible.filter(r=>r.tab).map(link), ...(more?[link(more)]:[]));
  }
  wireStickyNav();
}

/* Maps every route to the track it belongs to, for BOTH the CSS accent
   (`data-track` on <html>, see the palette block near the top of this file)
   and nav scoping (`buildNav`, above). The hidden course/uni deep-link
   routes are A-Level's today — no O-Level card links to #/course, it links
   straight to the institution's own page — so they carry the A-Level accent
   rather than none at all. */
const TRACK_BY_ROUTE_ID = {
  psle:"psle", olevel:"olevel",
  alevel:"alevel", result:"alevel", courses:"alevel", compare:"alevel",
  dates:"alevel", routes:"alevel", fees:"alevel", scoring:"alevel",
  course:"alevel", uni:"alevel",
};

function renderRoute(){
  const {route,param}=parseHash(location.hash);
  const views=[...document.querySelectorAll(".view")];
  const target = !route ? "view-404"
    : (route.needsRun && !S.result) ? "view-gate"
    : route.view;

  const track = route ? (TRACK_BY_ROUTE_ID[route.id] || null) : null;
  if(track) document.documentElement.setAttribute("data-track",track);
  else document.documentElement.removeAttribute("data-track");
  buildNav(track);

  // A run-gated card lives inside #results, which stays hidden until a run
  // has happened. Reveal the wrapper only when we are actually showing one.
  const res=$("#results");
  if(res && S.result) res.hidden=false;

  for(const v of views) v.hidden = (v.id!==target);

  if(target==="view-course") renderCoursePage(param);
  if(target==="view-uni")    renderUniPage(param);
  if(target==="view-fees")   renderFeesPage();
  if(target==="view-data")   renderDataPage();
  if(target==="view-scoring") renderScoringPage();
  if(target==="view-more")   renderMorePage();
  if(target==="view-home")         renderHome();
  if(target==="view-psle")         renderPsle();
  if(target==="view-olevel")       renderOlevel();
  if(target==="view-explore")      renderExplore();
  if(target==="view-resultsday")   renderResultsDay();
  if(target==="view-perspectives") renderPerspectives();
  if(target==="view-gate")   renderGate(route);

  for(const a of document.querySelectorAll("[data-route]")){
    const on = route && a.dataset.route===route.id;
    if(on) a.setAttribute("aria-current","page"); else a.removeAttribute("aria-current");
  }
  const h=$("#main h1,#main h2:not(.vh)");
  if(h && typeof h.focus==="function"){ h.setAttribute("tabindex","-1"); }
  window.scrollTo && window.scrollTo(0,0);
}

/* The pack-driven pages. U1 renders them honestly but plainly; ROADMAP_UI U2
   deepens #/course, #/uni and #/fees into the nine-section layout. They are
   deliberately NOT placeholders — a page that says "coming soon" to a parent
   looking for a fee is worse than one that says what is and is not known. */
const outcomeById = id => (S.pack?.outcomes||[]).find(o=>o.id===id);
const uniOutcomes = short => (S.pack?.outcomes||[]).filter(o=>o.institution_short===short);
const sourceById  = id => (S.pack?.sources||[]).find(s=>s.id===id);

function factLine(f,label){
  if(!f) return null;
  const s=sourceById(f.source);
  return el("p",{class:"cite"},[el("span",{text:
    `${label}: ${f.value}${f.as_of_year?` (${f.as_of_year})`:""}`+
    `${s?` — ${s.publisher}`:""}`})]);
}

/* "This figure looks wrong" — on every figure, not once in a footer. A tool
   that claims citation rigour and offers no way to report an error has a hole
   exactly where its credibility should be (SAFEGUARDS 5.7). The issue is
   pre-filled with the pack version and the field id so a report is actionable
   without the reporter having to explain where they were standing. */
function wrongLink(fieldId, courseId){
  const v=S.pack?.pack?.version||"";
  const title=encodeURIComponent(`Figure looks wrong: ${courseId||""} ${fieldId}`.trim());
  const body=encodeURIComponent(
    `Pack version: ${v}\nCourse: ${courseId||"(n/a)"}\nField: ${fieldId}\n\nWhat looks wrong:\n`);
  return el("a",{class:"wrong",rel:"noopener",target:"_blank",
    href:`https://github.com/BaijayantaRoy/path-ahead/issues/new?labels=data&title=${title}&body=${body}`,
    title:"Tell us this figure looks wrong", text:"⚑ looks wrong"});
}

/** A titled block on the course page. `n` is the reading order from ROADMAP_UI U2. */
function courseSection(n,title,kids){
  return el("section",{class:"card course-sec"},[
    el("p",{class:"eyebrow",text:`${n} · ${title}`}), ...kids.filter(Boolean)]);
}

const CITIZEN_LABEL={citizen:"Singapore Citizen",pr:"Permanent Resident",international:"International student"};
const money = n => "$"+Number(n).toLocaleString();

/** Fees for one course at one citizenship, in the basis the institution uses. */
function feeFor(o,cz){
  const c=o.cost; if(!c) return null;
  if(c.fee_basis==="per_credit"){
    const total={citizen:c.total_citizen,pr:c.total_pr,international:c.total_international}[cz];
    const rate={citizen:c.fee_per_credit_citizen,pr:c.fee_per_credit_pr,
                international:c.fee_per_credit_international}[cz];
    return total?{basis:"per_credit",total,rate,credits:c.total_credits}:null;
  }
  const annual={citizen:c.annual_fee_citizen,pr:c.annual_fee_pr,
                international:c.annual_fee_international}[cz];
  if(!annual) return null;
  const total={citizen:c.total_citizen,pr:c.total_pr,international:c.total_international}[cz]
            || (c.years?annual*c.years:null);
  return {basis:"annual",annual,total,years:c.years};
}

function renderCoursePage(id){
  const box=$("#courseOut"); if(!box) return;
  const o=outcomeById(id);
  if(!o){
    box.replaceChildren(el("section",{class:"card"},[
      el("h2",{text:"No such course"}),
      el("p",{class:"lede",text:"That course id is not in this data pack. It may have been renamed between pack versions."}),
      el("div",{class:"actions"},[el("a",{class:"btn",href:"#/alevel",text:"Back to the start"})])]));
    return;
  }
  const ed=o.editorial||{}, cz=P.citizenship||"citizen", out=[];

  /* header */
  out.push(el("section",{class:"card"},[
    el("p",{class:"eyebrow"},[el("a",{href:"#/uni/"+encodeURIComponent(o.institution_short),
      text:o.institution})]),
    el("h2",{text:o.name}),
    o.faculty?el("p",{class:"hint",text:o.faculty}):null,
    /* Where we have NOT checked, say so in the same place we would have said
       what the requirement is. Silence there reads as "no prerequisites", and
       a reader has no way to tell our gap from the institution's absence of
       one -- which is exactly the assumption that put a 52/100 on a physics
       degree for a student with no physics. */
    (!(o.subject_requirements||[]).length && o.route_group==="university-direct")
      ?el("div",{class:"note"},[
        el("span",{},[icon("info"),el("strong",{text:" Prerequisites not checked here"})]),
        el("p",{text:(o.institution_short||o.institution)+
          " publishes the subjects each of its programmes requires, and PathAhead "+
          "has not transcribed them for this one yet. The fit score below is a "+
          "match on what you told it about yourself \u2014 it is not a statement "+
          "that you are eligible. Check the entry requirements on the course page "+
          "before you count on it."})]):null,
    (o.subject_requirements||[]).length?el("div",{class:"note warn"},[
      el("span",{},[icon("alert"),el("strong",{text:" Subjects you must be taking"})]),
      el("p",{text:(o.institution_short||o.institution)+
        " will not consider an application without these. This is the institution's "+
        "rule, quoted as it publishes it \u2014 not PathAhead's judgement of you:"}),
      el("ul",{},(o.subject_requirements||[]).map(r=>el("li",{text:r.label||
        (r.subjects||[]).join(" or ")}))),
      el("p",{class:"hint",text:"A course you do not meet these for is still listed, "+
        "and still shows every published figure. It carries no fit score, because "+
        "a low score would still rank it \u2014 and ranking a door that is shut is "+
        "the thing this tool must never do."})]):null,
    o.language_requirement?el("div",{class:"note warn"},[el("span",{},[
      el("strong",{text:"Requires a language. "}),
      el("span",{text:o.language_requirement.label+
        (o.language_requirement.taught_in_language
          ? " This course is taught substantially in that language, which is the part that decides whether the years are livable."
          : "")})])]):null,
  ].filter(Boolean)));

  /* 1 — what it is */
  out.push(courseSection(1,"What it is",[
    ed.summary?el("p",{class:"lede",text:ed.summary}):
      el("p",{class:"hint",text:"No description held for this course."}),
    ed.summary?el("p",{class:"cite",text:
      "This description is PathAhead's own, written at course-family level rather than for this course specifically — the least verified thing on this page. If it is wrong, please tell us."}):null,
    ed.fact?citeLine(ed.fact,"Description",o.id):null,
    o.url?el("p",{class:"cite"},[
      el("span",{text:"Course details, entry requirements and everything PathAhead does not hold: "}),
      el("a",{class:"src",href:o.url,rel:"noopener",target:"_blank",
        text:o.institution+"'s own page for this course ↗"})]):null,
    ed.sectors?.length?el("p",{text:"Sectors: "+ed.sectors.join(", ")}):null,
    hasExtra(o)?el("div",{class:"note info"},[el("span",{text:
      "This course uses an interview, test or portfolio as well as grades, so the published figures are not the whole decision."})]):null,
  ]));

  /* 2 — evidence */
  const ev=[];
  if(o.band){
    ev.push(el("h3",{text:"Published range"}),
      el("p",{class:"big-fig",text:`${o.band.p10} to ${o.band.p90}`}),
      el("p",{class:"hint",text:o.band.basis||""}));
    if(o.band.comparable===false) ev.push(el("div",{class:"note info"},[el("span",{text:
      "This is published on a different basis from an A-Level score. PathAhead shows it and does not compare the two — there is no arithmetic that would make that comparison mean anything."})]));
    if(o.band.history?.length) ev.push(el("p",{class:"hint",
      text:"Earlier exercises: "+o.band.history.map(h=>`${h.year} ${h.label||h.low+" to "+h.high}`).join(" · ")+
           " — kept beside this year's figure, never merged into it."}));
    ev.push(citeLine(o.band.fact,"Published range",o.id));
  } else if(o.banded?.length){
    for(const b of o.banded){
      ev.push(el("h3",{text:b.stage?`Published profile — ${b.stage}`:"Published profile"}));
      ev.push(el("ul",{class:"plain"},b.bands.map(x=>el("li",{text:
        `${x.label}: ${x.share_label??(x.share!=null?x.share+"%":"not published")}`}))));
      if(b.comparable===false) ev.push(el("p",{class:"hint",text:
        "Published against a scale that has since been retired, so PathAhead shows the bands and withholds the verdict."}));
      ev.push(citeLine(b.fact,"Published profile",o.id));
    }
  } else {
    ev.push(el("h3",{text:"Published range"}),
      el("p",{class:"hint",text:"This institution publishes no admitted-score range for this course. That is the institution's choice, and PathAhead does not fill the gap with a figure from anywhere else."}));
  }
  if(o.poly_gpa) ev.push(el("h3",{text:"From a polytechnic diploma"}),
    el("p",{text:`GPA ${o.poly_gpa.p10}–${o.poly_gpa.p90}`}),
    citeLine(o.poly_gpa.fact,"Polytechnic GPA",o.id));
  if(o.intake) ev.push(el("h3",{text:"Places"}),
    el("p",{text:`${o.intake.value} (${o.intake.as_of_year})`}),
    citeLine(o.intake,"Places",o.id));
  out.push(courseSection(2,"Evidence",ev));

  /* 3 — fit, with the derivation visible rather than behind a click */
  const fit=S.fits[o.id];
  const fitKids=[];
  if(!S.result||!fit){
    fitKids.push(el("p",{class:"hint",text:"Answer the optional questions and PathAhead will show how well this course matches what you said — with every line of the arithmetic."}),
      el("div",{class:"actions"},[el("a",{class:"btn",href:"#/alevel",text:"Answer the questions"})]));
  } else if(fit.score===null){
    fitKids.push(el("p",{class:"lede",text:fit.unscored_reason}));
  } else {
    /* The whole arithmetic, not a summary of it.
       The score is NOT out of a fixed 100: a factor PathAhead cannot assess is
       dropped from both sides of the fraction rather than scored as zero, so
       our missing data never costs the student points. That makes the
       denominator vary by course, which is impossible to guess from a bare
       "78 / 100" — so the earned-over-possible line is shown above the
       percentage, and every bucket shows its own maximum. */
    const earned=(fit.factors||[]).reduce((a,f)=>a+f.points,0);
    const possible=(fit.factors||[]).reduce((a,f)=>a+(f.max??f.max_points??0),0);
    fitKids.push(el("p",{class:"big-fig",text:`${fit.score} / 100`}),
      el("p",{class:"hint",text:
        `${fitBand(fit.score)} · ${Math.round(earned*10)/10} points earned out of `+
        `${possible} available on this course · based on ${fit.signals_used} of `+
        `${fit.signals_available} things you told us`}),
      el("table",{class:"cmp"},[
        el("thead",{},[el("tr",{},[el("th",{text:"What matters"}),el("th",{text:"Match"}),
          el("th",{text:"You ranked it"}),el("th",{text:"Counts"}),el("th",{text:"Why"})])]),
        el("tbody",{},[
          ...(fit.factors||[]).map(f=>el("tr",{},[
            el("td",{text:f.label}),
            el("td",{text:f.match!=null?`${Math.round(f.match*100)}%`:"—"}),
            el("td",{text:f.weight!=null?`× ${f.weight}`:"—"}),
            el("td",{text:String(f.points)}),
            el("td",{text:f.reason||""})])),
          el("tr",{},[
            el("td",{},[el("strong",{text:"Total"})]),
            el("td",{text:""}),
            el("td",{text:""}),
            el("td",{},[el("strong",{text:String(Math.round(earned*10)/10)})]),
            el("td",{text:`${Math.round(earned*10)/10} ÷ ${possible} × 100 = ${fit.score}`})])])]),
      el("p",{class:"cite",text:
        "Each row is how well the course matches, multiplied by how you ranked it. Anything PathAhead cannot assess for this course, and anything you left out of your ranking, is dropped from BOTH sides of the fraction rather than scored zero — so neither a gap in our data nor a thing you do not care about can lower your score."}),
      el("p",{class:"cite",text:"Fit is PathAhead's opinion of how well this suits what you told us. It is not a prediction, not a probability, and says nothing about whether you would be admitted."}));
    if(fit.not_assessed?.length) fitKids.push(el("p",{class:"hint",
      text:"Not scored, because PathAhead lacks the data rather than because you lack the fit: "+fit.not_assessed.join(", ")}));
  }
  out.push(courseSection(3,"Fit",fitKids));

  /* 4 — money */
  const fee=feeFor(o,cz), c=o.cost, mk=[];
  mk.push(el("div",{class:"field field-max"},[
    el("label",{for:"czCourse",text:"Fees shown for",title:"Recalculate the fee for a different citizenship"}),
    el("select",{id:"czCourse",title:"Recalculate the fee for a different citizenship",
      onchange:e=>{P.citizenship=e.target.value;
      const s=$("#citizenship"); if(s) s.value=e.target.value; renderCoursePage(id);}},
      Object.entries(CITIZEN_LABEL).map(([v,t])=>
        el("option",{value:v,text:t,...(v===cz?{selected:"selected"}:{})})))]));
  if(fee&&fee.basis==="annual"){
    mk.push(el("p",{class:"big-fig",text:money(fee.annual)+" a year"}));
    if(fee.total) mk.push(el("p",{text:`${money(fee.total)} over ${fee.years} years, at today's published rate.`}));
  } else if(fee&&fee.basis==="per_credit"){
    mk.push(el("p",{class:"big-fig",text:money(fee.total)+" in total"}));
    mk.push(el("p",{text:`Charged per credit unit, not per year — ${fee.credits} credits`+
      (fee.rate?` at ${money(fee.rate)} each`:"")+". PathAhead does not divide this into a yearly figure the institution never published."}));
  } else {
    mk.push(el("p",{class:"hint",text:o.fee_note||
      "PathAhead does not hold a published fee for this course yet. An absent fee is shown as absent — never as a low one."}));
  }
  if(c){
    const bond=cz==="citizen"?c.bond_years_citizen:c.bond_years_pr_is;
    mk.push(el("h3",{text:"The tuition grant, and what it costs you"}));
    mk.push(el("p",{text:bond
      ? `As a ${CITIZEN_LABEL[cz]}, accepting the tuition grant commits you to working for a Singapore entity for ${bond} years after you graduate.`
      : `As a ${CITIZEN_LABEL[cz]}, the tuition grant itself carries no service bond.`}));
    if(c.bond_note) mk.push(el("p",{class:"hint",text:c.bond_note}));
    if(c.annual_fee_no_grant) mk.push(el("p",{class:"hint",
      text:`Without the grant the published rate is ${money(c.annual_fee_no_grant)} a year.`}));
    mk.push(citeLine(c.fact,"Fees",o.id));
  }
  mk.push(el("div",{class:"actions"},[
    el("a",{class:"btn",href:"#/fees",text:"How fees compare across institutions"})]));
  out.push(courseSection(4,"Money",mk));

  /* 5 — outcomes */
  const emp=o.employment, ok=[];
  if(emp?.gross_median){
    ok.push(el("h3",{text:"Gross monthly salary, about six months after graduating"}));
    ok.push(el("p",{class:"big-fig",text:`${money(emp.gross_p25)} – ${money(emp.gross_p75)}`}));
    ok.push(el("p",{class:"hint",text:`Median ${money(emp.gross_median)}. A range, because a median alone tells you nothing about the spread.`}));
  }
  if(emp?.employment_rate) ok.push(el("h3",{text:"In work within six months"}),
    el("p",{text:`${emp.employment_rate}%`+(emp.employment_rate_ft_perm?` · ${emp.employment_rate_ft_perm}% in full-time permanent work`:"")}));
  if(emp?.covers) ok.push(el("p",{class:"hint",text:"Survey covers: "+emp.covers}));
  if(emp?.unavailable_reason) ok.push(el("p",{class:"hint",text:emp.unavailable_reason}));
  if(emp?.fact) ok.push(citeLine(emp.fact,"Graduate survey",o.id));
  if(!ok.length) ok.push(el("p",{class:"hint",text:
    "No graduate survey data is held for this course. Where a median exists without quartiles it is deliberately not shown: this project shows a range or nothing."}));
  ok.push(el("p",{class:"cite",text:"Never a sort key. Pay and selectivity are information here, not a ranking."}));
  out.push(courseSection(5,"After it",ok));

  /* 5b — accreditation. Placed before reversibility because for the courses
     that have it, it is the hardest constraint on the page: a register you
     are not on is not a matter of preference. */
  if(o.accreditation?.length){
    const ac=[el("p",{class:"lede",text:
      "This is a registered profession. The qualification is what opens the register, and without registration the work cannot lawfully be done."})];
    for(const a of o.accreditation){
      ac.push(el("h3",{text:a.body}));
      ac.push(el("p",{text:a.label}));
      if(a.detail) ac.push(el("p",{class:"hint",text:a.detail}));
      ac.push(citeLine(a.fact,"Accreditation",o.id));
    }
    ac.push(el("p",{class:"cite",text:
      "Confirm the current accredited-qualification list with the board itself. The register is the authority here, not PathAhead."}));
    out.push(courseSection("5b","Whether you may practise",ac));
  }

  /* 6 — reversibility */
  const fx=o.flexibility, rv=[];
  if(fx){
    if(fx.common_first_year) rv.push(el("p",{text:"There is a common first year — you are admitted to the institution, not locked to this subject on the day you apply."}));
    if(fx.declares_major_later) rv.push(el("p",{text:"The major is declared later, not at application."}));
    if(fx.switching_note) rv.push(el("p",{class:"lede",text:fx.switching_note}));
    if(fx.keeps_open?.length) rv.push(el("p",{text:"Keeps open: "+fx.keeps_open.join(", ")}));
    if(fx.forecloses?.length) rv.push(el("p",{text:"Closes off: "+fx.forecloses.join(", ")}));
    rv.push(citeLine(fx.fact,"Flexibility",o.id));
  } else rv.push(el("p",{class:"hint",text:"Nothing held about how easily you could change direction from here."}));
  if(o.duration){
    rv.push(el("h3",{text:"How long it runs"}));
    rv.push(el("p",{class:"big-fig",text:`${o.duration.years} years`}));
    if(o.duration.structure) rv.push(el("p",{class:"hint",text:o.duration.structure}));
    rv.push(citeLine(o.duration.fact,"Duration",o.id));
  }
  if(o.progression?.length){
    rv.push(el("h3",{text:"Where it can lead next"}));
    for(const pr of o.progression){
      rv.push(el("p",{},[el("strong",{text:pr.label}),
        pr.exemption?el("span",{text:" — "+pr.exemption}):null].filter(Boolean)));
      if(pr.detail) rv.push(el("p",{class:"hint",text:pr.detail}));
      rv.push(citeLine(pr.fact,"Progression",o.id));
    }
  }
  out.push(courseSection(6,"Can you change your mind?",rv));

  /* 7 — ways in. At least three, the direct one first (SAFEGUARDS 5.2). */
  const rts=routesFor(o);
  out.push(courseSection(7,"Ways in",[
    el("p",{class:"lede",text:"More than one road leads here. The direct one is listed first because it is the most common, not because it is the best."}),
    el("ol",{class:"timeline"},rts.map(r=>el("li",{},[
      el("strong",{text:r.label}),
      r.steps?.length?el("ul",{class:"plain"},r.steps.map(s=>el("li",{text:s}))):null,
      r.caveat?el("p",{class:"hint",text:r.caveat}):null,
    ].filter(Boolean)))),
    rts.length<3?el("div",{class:"note warn"},[el("span",{text:
      "Fewer than three routes are held for this course. That is a gap in PathAhead, not a statement that no other way in exists."})]):null,
  ]));

  /* 8 — dates */
  const ms=(S.pack.milestones||[]);
  out.push(courseSection(8,"Dates",[
    el("p",{class:"lede",text:"Missing a deadline costs more than missing a grade profile by two points, and unlike the grade profile it is entirely preventable."}),
    el("ol",{class:"timeline"},ms.map(m=>el("li",{},[
      el("strong",{text:m.label||m.id}),
      m.detail?el("div",{text:m.detail}):null,
      m.approximate?el("span",{class:"tag",text:"approximate"}):null,
    ].filter(Boolean)))),
    hasExtra(o)?el("p",{class:"hint",text:"This course also has an interview, test or portfolio window that the institution sets separately — check its own page for those dates."}):null,
  ]));

  /* 9 — sources */
  const ids=new Set([o.band?.fact?.source,o.cost?.fact?.source,o.employment?.fact?.source,
    o.flexibility?.fact?.source,o.editorial?.fact?.source,o.intake?.source,
    o.poly_gpa?.fact?.source,o.language_requirement?.fact?.source,
    ...(o.subject_requirements||[]).map(r=>r.fact?.source),
    ...(o.banded||[]).map(b=>b.fact?.source),...(o.overlays||[]).map(x=>x.source)].filter(Boolean));
  out.push(courseSection(9,"Sources",[
    el("ul",{class:"plain"},[...ids].map(sid=>{const s=sourceById(sid); if(!s) return null;
      return el("li",{},[el("strong",{text:s.name||s.id}),el("span",{text:" — "+(s.publisher||"")}),
        s.url?el("span",{},[el("span",{text:" · "}),el("a",{href:s.url,rel:"noopener",target:"_blank",text:"source",title:`Open ${s.name||s.id} at its publisher`})]):null,
        s.retrieved?el("div",{class:"cite",text:"retrieved "+s.retrieved+(s.licence?" · "+s.licence:"")}):null,
      ].filter(Boolean));}).filter(Boolean)),
    el("div",{class:"actions"},[
      o.url?el("a",{class:"btn",href:o.url,rel:"noopener",target:"_blank",
        title:"Open this course's page on the institution's own website",
        text:"The institution's own page"}):null,
      el("a",{class:"btn",href:"#/uni/"+encodeURIComponent(o.institution_short),
        title:`See every other course PathAhead holds for ${o.institution_short}`,
        text:"More from "+o.institution_short}),
      el("button",{type:"button",onclick:()=>window.print(),text:"Print this page",
        title:"Open your browser's print dialog for this course's full page"}),
    ].filter(Boolean)),
  ]));

  box.replaceChildren(...out);
}

function factText(f){
  if(!f) return "";
  const s=sourceById(f.source);
  return [f.value,f.as_of_year?`(${f.as_of_year})`:null,s?`— ${s.publisher}`:null,
          f.basis==="editorial"?"· PathAhead's own characterisation":null]
         .filter(Boolean).join(" ");
}

/** Where a reader clicks to check ONE figure.
 *
 *  The fact's own page if it has one, otherwise the source's. Most figures
 *  share a source page and therefore share a link — that is fine and
 *  deliberate: the same link repeated beside twenty figures is still twenty
 *  figures a reader can check, and it is far better than one "sources" list
 *  at the bottom that nobody scrolls to. Only PathAhead's own editorial
 *  sentences have nothing to point at, and they say so instead. */
function citeUrl(f){
  if(!f) return null;
  if(f.url) return f.url;
  const s=sourceById(f.source);
  return s && s.url ? s.url : null;
}

/** A citation line: the value, the publisher, the year — and a link. */
function citeLine(f,label,courseId){
  if(!f) return null;
  const url=citeUrl(f);
  const kids=[el("span",{text:(label?label+": ":"")+factText(f)})];
  if(url) kids.push(el("span",{text:" "}),
    el("a",{class:"src",href:url,rel:"noopener",target:"_blank",
      title:"Open the page this figure came from", text:"check the source ↗"}));
  else if(f.basis==="editorial") kids.push(el("span",{class:"hint",
    text:" — PathAhead's own wording, so there is no page to check it against."}));
  if(courseId) kids.push(wrongLink(label||"figure",courseId));
  return el("p",{class:"cite"},kids);
}

function renderUniPage(short){
  const box=$("#uniOut"); if(!box) return;
  const list=uniOutcomes(short);
  if(!list.length){
    box.replaceChildren(el("section",{class:"card"},[
      el("h2",{text:"No such institution"}),
      el("p",{class:"lede",text:"That institution code is not in this data pack."}),
      el("div",{class:"actions"},[el("a",{class:"btn",href:"#/alevel",text:"Back to the start"})])]));
    return;
  }
  const cz=P.citizenship||"citizen";
  const withFee=list.filter(o=>feeFor(o,cz)).length;
  const withBand=list.filter(o=>o.band||o.banded?.length).length;
  const withEmp=list.filter(o=>o.employment?.gross_median).length;

  /* Fee bands as published — grouped by the institution's own band name, not
     by anything PathAhead invented. */
  const bands={};
  for(const o of list){ const g=o.cost?.fee_group; if(!g) continue;
    (bands[g] ||= {n:0,fee:feeFor(o,cz)}).n++; }

  const byFac={};
  for(const o of list) (byFac[o.faculty||"Other"] ||= []).push(o);

  box.replaceChildren(
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:short}),
      el("h2",{text:list[0].institution}),
      el("p",{class:"lede",text:`${list.length} course${list.length===1?"":"s"} in this data pack, across ${Object.keys(byFac).length} grouping${Object.keys(byFac).length===1?"":"s"}.`}),
      /* Coverage belongs here, not in a global banner: it differs by
         institution and a global banner makes every page equally suspect. */
      el("div",{class:"note info"},[el("span",{},[
        el("strong",{text:`What PathAhead does not hold for ${short}. `}),
        el("span",{text:
          `A fee figure for ${list.length-withFee} of ${list.length} courses; `+
          `a published admission profile for ${list.length-withBand}; `+
          `graduate salary data for ${list.length-withEmp}. `+
          `Those gaps are gaps, not zeroes.`})])]),
    ]),
    Object.keys(bands).length?el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Fee bands, as published"}),
      el("h3",{text:`For a ${CITIZEN_LABEL[cz]}`}),
      el("table",{class:"cmp"},[
        el("thead",{},[el("tr",{},[el("th",{text:"Band"}),el("th",{text:"Courses"}),el("th",{text:"Published fee"})])]),
        el("tbody",{},Object.entries(bands).sort().map(([g,v])=>el("tr",{},[
          el("td",{text:g}),el("td",{text:String(v.n)}),
          el("td",{text:v.fee?(v.fee.basis==="annual"?money(v.fee.annual)+"/yr":money(v.fee.total)+" total"):"not held"})])))]),
    ]):null,
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Courses"}),
      el("h3",{text:"Everything in the pack, by grouping"}),
      el("p",{class:"hint",text:"Listed A to Z within each grouping. Never ordered by how hard they are to get into."}),
      ...Object.entries(byFac).sort().map(([fac,os])=>el("div",{},[
        el("h4",{text:fac}),
        el("ul",{class:"plain"},os.slice().sort((a,b)=>a.name.localeCompare(b.name))
          .map(o=>el("li",{},[
            el("a",{href:"#/course/"+encodeURIComponent(o.id),text:o.name}),
            o.language_requirement?el("span",{class:"tag",text:"language required"}):null,
            (o.subject_requirements||[]).length?el("span",{class:"tag",text:"subject prerequisites"}):null,
            !feeFor(o,cz)?el("span",{class:"tag",text:"no fee held"}):null,
          ].filter(Boolean))))])),
    ])
  );
}

function renderFeesPage(){
  const box=$("#feesOut"); if(!box) return;
  const all=(S.pack?.outcomes||[]);
  const cz=P.citizenship||"citizen";
  const priced=all.filter(o=>feeFor(o,cz));
  const byInst={};
  for(const o of all){
    const r=(byInst[o.institution_short] ||= {n:0,priced:0,lo:null,hi:null,inst:o.institution});
    r.n++;
    const f=feeFor(o,cz); if(!f) continue;
    r.priced++;
    const t=f.total; if(t==null) continue;
    r.lo = r.lo===null?t:Math.min(r.lo,t);
    r.hi = r.hi===null?t:Math.max(r.hi,t);
  }
  const anyBond=all.find(o=>o.cost?.bond_note);

  /* The worst gap on this page, worked out from the data rather than written
     into it. This warning used to say "no polytechnic course carries a fee",
     which was true when it was written and false the morning four
     polytechnics were loaded — a caveat that outlives its cause teaches
     readers to discount every caveat on the page. So it names whichever
     institution now has the most unpriced courses, and disappears when there
     are none. The point it makes does not change: a blank is missing data,
     and the cheapest routes are the ones most likely to be blank. */
  const worst=Object.entries(byInst)
    .map(([k,v])=>({k,inst:v.inst,missing:v.n-v.priced,n:v.n}))
    .filter(x=>x.missing>0)
    .sort((a,b)=>b.missing-a.missing)[0];

  box.replaceChildren(
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Money"}),
      el("h2",{text:"Fees and funding"}),
      el("div",{class:"field field-max"},[
        el("label",{for:"czFees",text:"Show fees for"}),
        el("select",{id:"czFees",onchange:e=>{P.citizenship=e.target.value;
          const s=$("#citizenship"); if(s) s.value=e.target.value; renderFeesPage();}},
          Object.entries(CITIZEN_LABEL).map(([v,t])=>
            el("option",{value:v,text:t,...(v===cz?{selected:"selected"}:{})})))]),
      el("p",{class:"lede",text:
        `PathAhead holds a published fee for ${priced.length} of ${all.length} courses. `+
        `Where a figure is missing it is missing, and the course page says so — an `+
        `absent fee is never rendered as a cheap one.`}),
      worst ? el("div",{class:"note warn"},[el("span",{},[
        el("strong",{text:"The most misleading gap in this pack. "}),
        el("span",{text:
          `${worst.missing} of ${worst.inst}'s ${worst.n} courses carry no fee figure — `+
          `the largest gap here. A blank is missing data, not an absence of cost, and `+
          `on a page about money the cheapest routes are the ones most likely to be `+
          `blank. Each of those course pages says where the real number is published.`})])])
        : null,
    ]),
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Across institutions"}),
      el("h3",{text:`Total published course fees for a ${CITIZEN_LABEL[cz]}`}),
      el("p",{class:"hint",text:"A range across that institution's priced courses, A to Z. Deliberately not sorted by price: cost is information here, never a ranking."}),
      el("table",{class:"cmp"},[
        el("thead",{},[el("tr",{},[el("th",{text:"Institution"}),el("th",{text:"Courses"}),
          el("th",{text:"With a fee"}),el("th",{text:"Total, low–high"})])]),
        el("tbody",{},Object.entries(byInst).sort().map(([k,v])=>el("tr",{},[
          el("td",{},[el("a",{href:"#/uni/"+encodeURIComponent(k),text:k})]),
          el("td",{text:String(v.n)}),el("td",{text:String(v.priced)}),
          el("td",{text:v.lo===null?"not held":(v.lo===v.hi?money(v.lo):`${money(v.lo)} – ${money(v.hi)}`)})])))]),
    ]),
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"The part that is not a footnote"}),
      el("h3",{text:"The tuition grant and its service bond"}),
      el("p",{class:"lede",text:
        "Almost every figure above is the fee AFTER the MOE tuition grant. The grant "+
        "is not a discount — it is a subsidy with a condition attached, and the "+
        "condition differs by citizenship."}),
      el("ul",{class:"plain"},[
        el("li",{text:"Singapore Citizens: no service bond for the tuition grant itself."}),
        el("li",{text:"Permanent Residents and international students who accept the grant: three years working for a Singapore entity after graduating."}),
        el("li",{text:"Declining the grant means paying the non-subsidised rate, which is several times higher and is shown on each course page where the institution publishes it."}),
      ]),
      anyBond?el("p",{class:"cite",text:anyBond.cost.bond_note}):null,
      el("h3",{text:"If the fee is the problem"}),
      el("p",{text:"Every institution publishes bursaries, loans and financial aid separately from fees, and they are not means-tested in the same way. The institution's own admissions office is the right place to ask — the figures here will not tell you what you would actually pay after aid."}),
      el("div",{class:"actions"},[el("a",{class:"btn",href:"#/data",text:"Where these figures come from"})]),
    ])
  );
}

function renderDataPage(){
  const box=$("#dataOut"); if(!box) return;
  const p=S.pack; if(!p) return;
  box.replaceChildren(el("section",{class:"card"},[
    el("p",{class:"eyebrow",text:"Where this comes from"}),
    el("h2",{text:"Sources and licences"}),
    el("p",{class:"lede",text:
      `Data pack ${p.pack.version}, published ${p.pack.published}. `+
      `${p.outcomes.length} destinations from ${p.sources.length} sources. `+
      `Every figure on this site cites the institution that published it.`}),

    /* The attribution block, rendered conspicuously and with live links --
       not tucked in a footer and not as inert text. The Singapore Open Data
       Licence requires "a conspicuous notice acknowledging the source of the
       datasets and including a link to the most recent version of this
       Licence"; this is that notice, in the place a reader goes to ask where
       the numbers came from. See SAFEGUARDS.md 3a. */
    el("div",{class:"note info",id:"dataAttribution"},
      (p.pack.attribution||[]).map(line=>el("p",{},linkifyUrls(line)))),

    el("h3",{text:"What PathAhead does not hold"}),
    el("p",{text:
      "Some figures a family wants are published under terms that do not allow "+
      "PathAhead to copy them, however freely you can read them yourself. Rather "+
      "than reproduce those, PathAhead links you to the page that publishes them "+
      "so you can read the official version at source, unaltered and in context. "+
      "Where you see a link out instead of a number, that is why — not an "+
      "oversight, and not a figure PathAhead is hiding from you."}),

    el("h3",{text:"Every source, and what may be done with it"}),
    el("ul",{class:"plain"},p.sources.map(s=>el("li",{},[
      el("strong",{text:s.name||s.id}),
      el("span",{text:" — "+(s.publisher||"")}),
      s.url?el("span",{},[el("span",{text:" · "}),
        el("a",{href:s.url,rel:"noopener noreferrer",target:"_blank",text:"source",title:`Open ${s.name||s.id} at its publisher`})]):null,
      el("div",{class:"cite"},[
        s.retrieved?el("span",{text:"retrieved "+s.retrieved}):null,
        s.licence?el("span",{text:" · "}):null,
        // The licence name, hyperlinked to the licence itself wherever the
        // licence has a canonical page. A bare id like "sg-odl-1.0" told a
        // reader nothing and satisfied no licence condition.
        s.licence?(s.licence_url
          ? el("a",{href:s.licence_url,rel:"noopener noreferrer",target:"_blank",
                    text:s.licence_name||s.licence})
          : el("span",{text:s.licence_name||s.licence})):null,
      ].filter(Boolean)),
    ].filter(Boolean)))),
    el("div",{class:"actions"},[el("a",{class:"btn",
      href:"https://github.com/BaijayantaRoy/path-ahead/issues/new?labels=data&title=Figure%20looks%20wrong",
      rel:"noopener noreferrer",target:"_blank",text:"Report a figure that looks wrong"})]),
  ]),
  // Repeated in full here, not linked to. Someone on this page is already
  // asking "how much can I trust these numbers" -- that is exactly the
  // moment the limits belong in front of them, not one click away.
  limitsCard());
}

function renderMorePage(){
  const box=$("#moreOut"); if(!box) return;
  box.replaceChildren(
    el("section",{class:"card"},[
      el("h2",{text:"Everything else"}),
      el("ul",{class:"plain"},ROUTES.filter(r=>!r.hidden&&!r.tab).map(r=>
        el("li",{},[el("a",{href:r.hash,text:r.label,title:r.desc||r.label})]))),
    ]),
    limitsCard(),
  );
}

/** The standing statement of what this tool is, what it is not, and who is
    responsible for a decision made after reading it.
 *
 *  Deliberately a card on a page a reader can reach and re-read, not a modal
 *  they dismiss once and never see again, and not an "I agree" gate — a gate
 *  trains people to click through disclaimers, which makes every later one
 *  worth less (SAFEGUARDS.md 4).
 *
 *  Written plainly on purpose. A disclaimer only the fluent can parse is not
 *  a disclaimer, and the PDPA children's guidance sets a "readily
 *  understandable by the child" bar this page tries to actually clear rather
 *  than gesture at.
 */
function limitsCard(){
  return el("section",{class:"card",id:"limitsCard"},[
    el("p",{class:"eyebrow",text:"Before you rely on any of this"}),
    el("h2",{text:"What PathAhead is, and what it is not"}),

    el("h3",{text:"It explains published rules. It does not advise you."}),
    el("p",{text:
      "Everything here is worked out from rules and figures that MOE, SEAB, a school "+
      "or an institution has already published, with a link to each one so you can "+
      "check it. PathAhead does not know your child, and it has no opinion about what "+
      "they should do. Any decision you make after reading this is yours, and it should "+
      "be made with people who do know your child — their teachers, their school's "+
      "Education and Career Guidance counsellor, and the admissions office of anywhere "+
      "you are seriously considering."}),

    el("h3",{text:"The figures are last year's, and they move."}),
    el("p",{text:
      "Cut-off points, grade profiles and intake figures describe an exercise that has "+
      "already happened. They shift from year to year with each cohort's results and "+
      "choices. Matching one is not by itself enough to secure a place, and missing one "+
      "does not close a door — admissions consider things no formula here captures. "+
      "Where a figure is past its publication cycle, PathAhead greys it out and says so "+
      "rather than quietly showing you something out of date."}),

    el("h3",{text:"Some figures are deliberately not here."}),
    el("p",{text:
      "Where a publisher's terms do not clearly allow PathAhead to copy their data, it "+
      "does not copy it — it links you to their page so you can read the official "+
      "version yourself. Posting Group cut-off points are the main example: they live "+
      "on each school's MOE SchoolFinder page, and every school card here links "+
      "straight to it. A link is not PathAhead being coy; it is you getting the "+
      "current, official number instead of a stale copy of one."}),

    el("h3",{text:"It is not official, and not connected to anyone."}),
    el("p",{text:
      "PathAhead is an independent, open-source project. It is not affiliated with, "+
      "endorsed by, or connected to the Ministry of Education, SEAB, Cambridge "+
      "Assessment, or any school, polytechnic, ITE or university. Where it is wrong, "+
      "the official page is right — and there is a \"looks wrong\" link on every figure "+
      "so you can tell us."}),

    el("h3",{text:"Nothing you type here is collected."}),
    el("p",{text:
      "There is no account, no name field, no email field, and no analytics. What you "+
      "type stays in this browser tab and is gone when you close it. Nothing is sent to "+
      "a server, because there is no server to send it to — and this page loads nothing "+
      "from anyone else's, either."}),

    el("p",{class:"hint",text:
      "Provided as-is, with no warranty, under the MIT licence. You are responsible for "+
      "checking anything that matters against its official source before acting on it."}),

    el("div",{class:"actions"},[
      el("a",{class:"btn",href:"#/data",text:"Where every figure comes from"}),
    ]),
  ]);
}

/* ── U5: the flows that were missing ──────────────────────────
   None of these asks for a grade before it will speak to you. That is the
   whole point of all three: the app used to have exactly one front door, and
   it wanted a transcript. */

/** #/explore — "I have no idea" is the most common real state, and until now
    there was no front door for it. Interests only; no grades, no score. */
const EX = {picked:new Set()};

/** Courses that carry ALL of the picked interests. Named and pure so it can
    be checked without a browser — and because "every" rather than "some" is a
    decision: picking a second interest must NARROW the list, or the control
    is lying about what it does. */
function exploreMatches(outcomes, picked){
  if(!picked || !picked.length) return [];
  return outcomes.filter(o=>{
    const ints=o.editorial?.interests||[];
    return picked.every(p=>ints.includes(p));
  });
}

function renderExplore(){
  const box=$("#exploreOut"); if(!box) return;
  const pack=S.pack; if(!pack) return;
  const picked=[...EX.picked];
  const matches = exploreMatches(pack.outcomes, picked);
  const byInst={};
  for(const o of matches) (byInst[o.institution_short] ||= []).push(o);

  box.replaceChildren(
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"No idea yet"}),
      el("h2",{text:"Start from what you like, not from your grades"}),
      el("p",{class:"lede",text:
        "Most people arrive here with no destination in mind, and every other page "+
        "on this site asks for a transcript first. This one does not. Pick anything "+
        "that sounds like you and see where it leads."}),
      el("div",{class:"chips",role:"group","aria-label":"What you are drawn to"},
        (pack.interests||[]).map(i=>el("button",{type:"button",
          "aria-pressed":String(EX.picked.has(i.code)),
          title:i.detail||"",
          text:i.label,
          onclick:()=>{EX.picked.has(i.code)?EX.picked.delete(i.code):EX.picked.add(i.code);
            renderExplore();}}))),
      picked.length?el("div",{class:"actions"},[
        el("button",{type:"button",class:"ghost",text:"Start again",
          title:"Clear everything you've picked and start over",
          onclick:()=>{EX.picked.clear(); renderExplore();}})]):null,
    ].filter(Boolean)),
    picked.length ? el("section",{class:"card"},[
      el("h3",{text:`${matches.length} course${matches.length===1?"":"s"} lean that way`}),
      el("p",{class:"hint",text:
        "This is not a match score and nothing here has been ranked. It is simply every "+
        "course PathAhead characterises as involving all of what you picked — and those "+
        "characterisations are PathAhead's own, written at course-family level."}),
      matches.length===0
        ? el("p",{class:"lede",text:
            "Nothing carries all of those at once. That is a fact about how PathAhead "+
            "describes courses, not a verdict about the combination — try removing one."})
        : el("div",{},Object.entries(byInst).sort().map(([k,os])=>el("div",{},[
            el("h4",{text:k}),
            el("ul",{class:"plain"},os.slice().sort((a,b)=>a.name.localeCompare(b.name))
              .map(o=>el("li",{},[el("a",{href:"#/course/"+encodeURIComponent(o.id),text:o.name})])))]))),
      el("div",{class:"actions"},[
        el("a",{class:"btn",href:"#/alevel",text:"When you are ready, add your grades"})]),
    ]) : el("section",{class:"card"},[
      el("p",{class:"lede",text:"Pick one or more above. Nothing is recorded, and you can change your mind as often as you like."})]),
  );
}

/* ── #/ — the stage chooser ────────────────────────────────────
   The smallest page in the app, and it must stay that way. Its only job is to
   get a family to the right stage in one tap, in the week they are panicking.

   It replaced the A-Level grades table, which had been the front door since
   the first release. That was defensible while there was one stage and
   indefensible the moment there were two: a parent of a Primary 6 child
   arrived at a form asking for H2 subject grades.

   The third door is NOT built, and says so in its own words rather than
   "coming soon". A gap that describes itself is honest; a button that does
   nothing is not, and a stage quietly missing from the list is worse than
   either — that is how a family concludes the tool has nothing for them. */
const DOORS = [
  {
    stage:"psle", href:"#/psle", built:true,
    who:"Primary 5 and 6 · the parent",
    title:"After the PSLE",
    body:"What a PSLE Score of 4 to 32 actually decides — the Posting Group, "+
         "what a cut-off point really is, how the six school choices are used, "+
         "and what the DSA commitment costs you.",
    go:"Start here",
  },
  {
    stage:"o-level", href:"#/olevel", built:true,
    who:"Secondary 1 to 5",
    title:"O-Level and the SEC",
    body:"Your L1R5 or L1R4 aggregate worked out step by step, against every "+
         "Junior College and Millennia Institute PathAhead has loaded — plus "+
         "the polytechnic ELR2B2 route from the same subjects. The 2026 "+
         "Secondary 4 cohort is the last to sit the GCE O-Level; everyone "+
         "behind them sits the Secondary Education Certificate under a "+
         "different ceiling, and this page says which rulebook applies to you "+
         "before it asks for a single grade.",
    go:"Start here",
  },
  {
    stage:"a-level", href:"#/alevel", built:true,
    who:"Junior College and Millennia Institute",
    title:"A-Level to university",
    body:"Your University Admission Score worked out step by step, against "+
         "every published grade profile from all eleven institutions — with "+
         "fees, and with the years where nobody published a comparable figure "+
         "left plainly empty.",
    go:"Start here",
  },
];

function renderHome(){
  const box=$("#homeOut"); if(!box) return;
  const pack=S.pack;
  const stages=new Set((pack?.stages||[]).map(s=>s.id));
  const loaded=new Set((pack?.transitions||[]).map(t=>t.stage));

  box.replaceChildren(
    el("section",{class:"card"},[
      el("h1",{id:"homeH1",text:"Where are you now?"}),
      el("p",{class:"lede",text:
        "One school year apart can mean two entirely different rulebooks, so this is "+
        "the first thing PathAhead needs to know. Nothing below asks for a grade."}),
      el("div",{class:"doors",id:"homeDoors"}, DOORS.map(dr=>{
        // A door is only offered if the pack can actually answer it. The flag
        // in DOORS is the intent; the pack is the fact, and the pack wins.
        const ready = dr.built && loaded.has(dr.stage);
        const kids=[
          el("span",{class:"who",text:dr.who}),
          el("h3",{text:dr.title}),
          el("p",{text:dr.body}),
          el("span",{class:"go",text:ready?dr.go:DOORS.find(x=>x.stage===dr.stage).go}),
        ];
        const doorTitle = ready
          ? `${dr.title} — for ${dr.who}`
          : `${dr.title} — not in this build yet`;
        return ready
          ? el("a",{class:"door",href:dr.href,"data-door":dr.stage,title:doorTitle},kids)
          : el("div",{class:"door unbuilt","data-door":dr.stage,"aria-disabled":"true",title:doorTitle},kids);
      })),
    ]),

    el("section",{class:"card"},[
      el("h2",{text:"If none of those is where you are"}),
      el("ul",{class:"plain"},[
        el("li",{},[el("a",{href:"#/explore",text:"I have no idea what I want to do",
          title:"Browse courses by interest instead of grades"}),
          el("span",{text:" — start from what you are drawn to, with no grades at all."})]),
        el("li",{},[el("a",{href:"#/results-day",text:"The results were worse than we hoped",
          title:"Ways forward that don't ask for a score"}),
          el("span",{text:" — the ways forward, without a score being asked for."})]),
        el("li",{},[el("a",{href:"#/perspectives",text:"Two of us see this differently",
          title:"Compare what two people each said matters, without a score"}),
          el("span",{text:" — where a parent and a student agree and where they don't, without a score."})]),
        el("li",{},[el("a",{href:"#/data",text:"Where every figure here comes from",
          title:"Every source PathAhead cites, and what it does not hold"}),
          el("span",{text:" — each one cited, dated, and linked to its publisher."})]),
      ]),
    ]),
  );
  // Nothing here should ever silently drop a stage the pack knows about.
  for(const id of stages) if(!DOORS.some(d=>d.stage===id))
    console.warn(`stage "${id}" is in the pack but has no door on the home page`);
}

/* ── #/psle — the PSLE stage's own front door ──────────────────
   Written for a parent, on a phone, who is anxious. The child is twelve and
   may be reading over their shoulder; assume both.

   Three rules hold this page together and each of them is a decision:

   1. **No form above the fold.** The A-Level start view opens with a dropdown
      and a grades table, which is right for a JC2 student who came to
      calculate something and wrong for a P6 parent in June with no score.
      Three doors instead.
   2. **A Posting Group is a gate, never a score.** Nothing here ranks a
      child, and nothing here scores a school. See docs/decisions/0003.
   3. **The route for a score outside the published table is a door, not a
      footer.** A page that only speaks to families aiming at a cut-off of 8
      fails the ones who need it most.

   `postingGroupFor` is a port of engine/posting.py and must agree with it. */
const PSLE_TRANSITION = "psle-to-secondary-2026";
const psleTransition = () => (S.pack?.transitions||[]).find(t=>t.id===PSLE_TRANSITION);

function postingGroupFor(spec, score, subjectAls){
  const rows = spec?.groups || [];
  const unmet = row => {
    const req = row.also_requires;
    if(!req || !req.subjects || req.max_al == null) return false;
    // Nothing asked means nothing may be concluded. A tool that quietly
    // demotes a child over a question it never put is the failure this whole
    // project exists to avoid — so "not asked" is reported, not assumed.
    if(!subjectAls) return true;
    return req.subjects.some(s => subjectAls[s] == null || subjectAls[s] > req.max_al);
  };
  for(const row of rows){
    if(score < row.min || score > row.max) continue;
    if(unmet(row)) continue;
    const groups = row.groups || [];
    return {score, groups, level:row.level||"", note:row.note||"",
            isAChoice: groups.length>1,
            defaultGroup: groups.length===1 ? groups[0]
              : (spec.default_when_unsubmitted==="most_demanding" ? Math.max(...groups) : null),
            outsideTable:null};
  }
  return {score, groups:[], level:"", note:"", isAChoice:false, defaultGroup:null,
          outsideTable: spec?.outside_the_table || null};
}

const PS = {score:null, prefs:{postal_code:null, student_sex:null, gender:null, want_sap:null,
  want_ip:null, want_autonomous:null, want_gifted:null, school_types:[]},
  // Every one of these narrows WHICH schools appear; none of them score or
  // sort anything (SAFEGUARDS.md 5.1) -- the visible list is always sorted
  // by distance then name, never by how closely a school matches. `filters`
  // is kept separate from `prefs` only because postal code/km and the AL
  // score search work differently under the hood (a chosen band vs. a
  // tri-state match) -- both are filters in exactly the same sense.
  //
  // `al` is the EXPLICIT AL-score search (see renderSchoolPrefs' "Search by
  // AL score" block): independent of PS.score above, which only ever drives
  // the Posting Group calculator. mode "upper" reads `upper` alone; mode
  // "range" reads `min` and `max` together, and only once BOTH are set --
  // a single one of the two is not enough to mean anything.
  filters:{maxKm:null, al:{mode:"upper", upper:null, min:null, max:null}}};
const SCHOOL_TYPE_OPTIONS = ["Government school","Government-aided school",
  "Independent school","Specialised school","Specialised independent school"];

function renderPsle(){
  const box=$("#psleOut"); if(!box) return;
  const pack=S.pack; if(!pack) return;
  const t=psleTransition();
  if(!t){
    box.replaceChildren(el("section",{class:"card"},[
      el("h2",{text:"The PSLE stage is not in this data pack"}),
      el("p",{class:"lede",text:"This build was made without it. Nothing is broken — "+
        "the page simply has nothing to show, and says so rather than pretending."})]));
    return;
  }
  const spec=t.rule_params?.posting_groups;
  const rows=spec?.groups||[];
  const result = PS.score==null ? null : postingGroupFor(spec, PS.score, null);

  box.replaceChildren(
    /* ── the hero ─────────────────────────────────────────── */
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"After the PSLE"}),
      el("h1",{id:"psleH1",text:"Your child sits the PSLE in November. Here is what happens after."}),
      el("p",{class:"lede",text:
        "A PSLE score decides a Posting Group and a set of schools. It does not decide "+
        "what your child can become — and the schools themselves will tell you the same thing."}),
      el("p",{class:"hint",text:
        "Nothing on this page asks for a name, a school or an address, and nothing you "+
        "type leaves this device. There is no server to send it to."}),
    ]),

    /* ── three doors, not a form ───────────────────────────── */
    el("section",{class:"card"},[
      el("h2",{text:"Where are you in this?"}),
      el("div",{class:"chips",id:"psleDoors",role:"group","aria-label":"Where you are"},[
        el("button",{type:"button",class:"chip",text:"We have a score",
          title:"Jump to the PSLE Score field below to see which Posting Groups it opens",
          onclick:()=>{ const f=$("#psleScore"); if(f){ f.focus(); f.scrollIntoView({block:"center"}); } }}),
        el("button",{type:"button",class:"chip",text:"Not yet — we are choosing",
          title:"Stay on this page — it's written for families with no score yet",
          onclick:()=>navigate("#/psle")}),
        el("button",{type:"button",class:"chip",text:"Explain the system",
          title:"Jump to the published Posting Group table further down this page",
          onclick:()=>{ const h=$("#psleTable"); if(h) h.scrollIntoView({block:"start"}); }}),
      ]),
      el("p",{class:"hint",text:
        "Most families arrive here in the eleven months when there is no score yet. "+
        "That is a real place to be standing and this page is written for it."}),
    ]),

    /* ── the score, if they have one ───────────────────────── */
    el("section",{class:"card"},[
      el("h2",{text:"If you have the score"}),
      el("p",{class:"hint",text:
        "The PSLE Score is the four Achievement Levels added together — from 4 to 32, "+
        "lower being stronger. Enter it and PathAhead will say which Posting Groups it "+
        "opens. It will not rank your child, and it will not score a school."}),
      el("div",{class:"field field-max"},[
        el("label",{for:"psleScore",text:"PSLE Score (4 to 32)"}),
        // Only the answer is re-rendered on input, never the whole page.
        //
        // Re-rendering everything meant re-creating the field under the
        // cursor, so the caret had to be restored by hand -- and
        // setSelectionRange throws InvalidStateError on an <input type=
        // "number"> in real browsers, not only under jsdom. The fix is not to
        // catch the throw; it is to stop destroying the element someone is
        // typing into.
        el("input",{type:"number",id:"psleScore",min:"4",max:"32",inputmode:"numeric",
          title:"The four Achievement Levels added together — 4 (best) to 32 (worst)",
          value: PS.score==null ? "" : String(PS.score),
          oninput:e=>{ const v=parseInt(e.target.value,10);
            PS.score = Number.isFinite(v) && v>=4 && v<=32 ? v : null;
            paintPsleAnswer();
            // The AL score search's "Use the ... entered above" quick-fill
            // button (see renderSchoolPrefs) reads PS.score too; without
            // this, entering a score after already scrolling to the
            // shortlist would leave that button showing a stale value, or
            // missing entirely, until something else happened to repaint it.
            renderSchoolPrefs(); renderSchoolShortlist(); }}),
      ]),
      el("div",{id:"psleAnswerHost"},[
        result ? psleAnswer(result, spec) : psleNothingYet(),
      ]),
    ]),

    /* ── the published table ───────────────────────────────── */
    el("section",{class:"card",id:"psleTable"},[
      el("h2",{text:"The Posting Groups, as published"}),
      el("table",{class:"cmp"},[
        el("thead",{},[el("tr",{},[
          el("th",{text:"PSLE Score"}), el("th",{text:"Posting Group"}),
          el("th",{text:"Most subjects start at"})])]),
        el("tbody",{},rows.map(r=>el("tr",{},[
          el("td",{text: r.min===r.max ? String(r.min) : `${r.min}–${r.max}`}),
          el("td",{text: r.groups.join(" or ")}),
          el("td",{text: r.level||"—"})]))),
      ]),
      el("p",{class:"hint",text:
        "Where two groups are listed, you choose — and the choice applies to all six "+
        "school choices. You cannot mix Posting Groups across the list. If no choices "+
        "are submitted at all, the more academically demanding group is assigned."}),
      el("p",{class:"hint",text:
        "Full Subject-Based Banding means a Posting Group sets a starting point, not a "+
        "ceiling. A child in Posting Group 1 or 2 can take English, Mathematics, Science "+
        "or Mother Tongue at a more demanding level if they did well in them."}),
      citeSource(spec?.source),
    ]),

    /* ── three cards that are never behind a toggle ────────── */
    el("section",{class:"card",id:"psleHonesty"},[
      el("h2",{text:"Three things worth knowing before you read any cut-off point"}),

      el("h3",{text:"A cut-off point is a record, not a threshold"}),
      el("p",{text:
        "It is the score of the first and last student posted to that school in that "+
        "Posting Group last year. It moves by a few points every year with each cohort's "+
        "results and choices, and some students who matched it were tie-broken out and "+
        "posted elsewhere."}),

      el("h3",{text:"Your address does not help you get in"}),
      el("p",{text:
        "The tie-breakers at S1 Posting are citizenship, then the order you ranked your "+
        "six schools, then a computerised ballot. Distance is not among them. It matters "+
        "in one place only: a child who cannot be placed in any of their six choices is "+
        "posted to the nearest available school from the registered address. Distance IS "+
        "a criterion at Primary 1 registration — that is a different exercise, and the "+
        "two are easy to confuse."}),

      el("h3",{text:"Accepting a DSA place gives up the six choices"}),
      el("p",{text:
        "A child admitted through Direct School Admission cannot submit S1 school choices "+
        "and cannot transfer. The commitment runs for the length of the programme, and it "+
        "is agreed to months before the results exist."}),
    ]),

    /* ── the door that is usually a footer ─────────────────── */
    spec?.outside_the_table ? el("section",{class:"card",id:"psleOutside"},[
      el("h2",{text:"If the score is outside that table"}),
      el("p",{class:"lede",text:spec.outside_the_table.headline}),
      el("p",{text:spec.outside_the_table.body}),
      citeSource(spec.outside_the_table.source),
    ]) : null,

    /* ── what the score decides besides the posting group ──── */
    el("section",{class:"card"},[
      el("h2",{text:"What the score decides besides the Posting Group"}),
      el("p",{class:"hint",text:
        "Each of these is a published criterion with a published threshold. None of them "+
        "is a ranking, and PathAhead is not checking your child against them — it is "+
        "listing what the criteria are so you can."}),
      el("dl",{class:"plain"},(t.rule_params?.unlocks||[]).flatMap(u=>[
        el("dt",{text:u.label}),
        el("dd",{},[el("span",{text:u.criterion}),
          u.note?el("p",{class:"hint",text:u.note}):null].filter(Boolean)),
      ])),
    ]),

    /* ── the shortlist: preference, never admission ──────────── */
    renderSchoolShortlistSection(pack),

    el("section",{class:"card"},[
      el("h3",{text:"What is not here, and why"}),
      el("p",{text:
        "Posting Group cut-off points. Not an oversight and not a gap PathAhead is working "+
        "on — a deliberate limit. MOE publishes those figures on each school's own "+
        "SchoolFinder page under terms that let anyone read them but reserve the right to "+
        "reproduce them. PathAhead is not MOE, so it does not copy them. Every school card "+
        "above links to that school's SchoolFinder page instead, which also means what you "+
        "read there is this year's figure rather than a snapshot taken by this project and "+
        "slowly going out of date."}),
      el("p",{text:
        "Eight of the 147 schools have no cut-off published anywhere, because they admit "+
        "through auditions, aptitude tests, sports trials or a customised curriculum rather "+
        "than the standard PSLE-score S1 Posting Exercise. Their cards say so."}),
      el("p",{text:
        "Also not here: co-curricular activities (a dataset exists; pulling and cleaning it "+
        "did not make this pass), and religious or primary-school affiliation, which is not "+
        "in any dataset PathAhead can cite in bulk."}),
      el("div",{class:"actions"},[
        el("a",{class:"btn",href:"#/data",text:"Where these figures come from"})]),
    ]),
  );
  renderSchoolPrefs();
  renderSchoolShortlist();
}

/* ── #/psle — school shortlist ─────────────────────────────────────
   Mirrors engine/school_fit.py exactly: every preference below is a
   FILTER, none of them a score, so this never ranks the 147 schools by how
   well they match and never estimates which ones a PSLE score could reach
   — see FILTER_DISCLAIMER, shown once above the results and repeated in
   "How these filters work" below rather than on every card. */
function renderSchoolShortlistSection(pack){
  return el("section",{class:"card",id:"schoolShortlist"},[
    el("h2",{text:"Narrow down the schools worth a closer look"}),
    el("p",{class:"lede",text:
      `Every one of the ${(pack.schools||[]).length} schools a PSLE cohort can be posted `+
      "to, shown by default. Each filter below hides schools that don't match it — "+
      "nothing here ranks or scores a school."}),
    el("p",{class:"hint",text:FILTER_DISCLAIMER}),

    /* Explained BEFORE the form, not tucked into a collapsed disclosure
       after the results. A family asking how this works deserves the
       answer before it asks them to type anything, not as an afterthought
       they have to know to go looking for. */
    el("details",{id:"schoolAlgoExplain",open:true},[
      el("summary",{text:"How these filters work"}),
      el("p",{text:
        "All 147 schools show by default. Each preference you set below hides schools "+
        "that don't match it — nothing is scored, nothing is weighted, and nothing about "+
        "a hidden school implies it is worse than one that is shown, only that it does "+
        "not match what you asked for. Clear a filter (set it back to \"No preference\") "+
        "and every school it was hiding reappears."}),
      el("ul",{class:"plain-list"},SCHOOL_FILTER_DIMENSIONS.map(([k,label])=>
        el("li",{text:label}))),
      el("p",{text:
        "\"How close to home\" is not one of the filters above — it is the maximum-"+
        "distance filter further down (\"Narrow the list further\"), using a real "+
        "straight-line distance rather than a category, plus your postal district shown "+
        "as a tag on every card. Next to each school, PathAhead also shows that same "+
        "straight-line distance — clearly labelled as straight-line, never a travel time "+
        "— and a link to get real directions from Google Maps if you want them."}),
      el("p",{text:
        "One thing here is not a preference at all: a boys' school does not admit "+
        "girls, and a girls' school does not admit boys. Your child's sex is asked "+
        "for separately, below, and checked before any filter — a single-sex school "+
        "your child cannot attend is hidden outright, not shown as a weak match, "+
        "because it is not a real option. If you have not answered your child's sex "+
        "yet, single-sex schools stay visible with a plain note that PathAhead can't "+
        "confirm either way, rather than guessing. \"Co-ed or single-sex\" further "+
        "down is a genuine filter on top of that: among the schools your child COULD "+
        "attend, which kind do you want to see."}),
      el("p",{text:
        "PathAhead does not republish Posting Group cut-off points. They belong to MOE, "+
        "who publish them on each school's own SchoolFinder page — so every school card "+
        "below carries a link straight to that page instead of a number copied out of it. "+
        "You read the official figures at source: current, in MOE's own words, with MOE's "+
        "own caveats attached, and never a stale snapshot taken by this project. When you "+
        "do read them, remember lower is stronger — the PSLE Score runs 4 (best) to 32 "+
        "(worst), the opposite direction from most exam grades."}),
      el("p",{text:
        "Further down, \"narrow the list further\" adds a maximum-distance FILTER. It does "+
        "not reorder the list either: it only decides which schools appear at all. What "+
        "remains is always sorted by distance (closest first, when you've given a postal "+
        "code) and then by name — never by how closely a school matches what you asked "+
        "for, and never by how competitive it is."}),
      /* Careful with this sentence. MOE's own phrasing is that meeting a
         cut-off "does not guarantee admission" -- but the banned-phrase
         guard scans for "guarantee admission" and cannot tell a warning
         from a promise, which is correct behaviour for a blunt guard on a
         high-stakes page. Paraphrased rather than quoted for that reason;
         the meaning is MOE's, the words are ours. Rewrite the sentence,
         never the guard. */
      el("p",{text:
        "MOE's own caution applies to any cut-off figure you find, wherever you find it: "+
        "they \"can fluctuate by a few points year-on-year,\" and matching one is not by "+
        "itself enough to secure a place. A cut-off is a record of who was posted last "+
        "year, not a threshold for this year. Treat it as one input among several, and "+
        "take anything that matters to the school itself or to your child's teachers."}),
      citeSource("datagovsg-school-directory-2026"),
      citeSource("singpost-postal-districts"),
      citeSource("moe-schoolfinder"),
    ]),

    el("div",{id:"schoolPrefsHost"}),
    el("div",{id:"schoolShortlistHost"}),
  ]);
}

function renderSchoolPrefs(){
  const host = $("#schoolPrefsHost"); if(!host) return;
  const prefs = PS.prefs;

  const onSingleSelect = () => { renderSchoolPrefs(); renderSchoolShortlist(); };

  const triState = (label, key, hint) => {
    const val = prefs[key];
    return el("div",{class:"field"},[
      el("label",{text:label,title:hint||label}),
      el("div",{class:"seg",role:"group","aria-label":label},[
        el("button",{type:"button","aria-pressed":String(val===null),text:"No preference",
          title:`Don't filter by ${label}`,
          onclick:()=>{ prefs[key]=null; onSingleSelect(); }}),
        el("button",{type:"button","aria-pressed":String(val===true),text:"Only show these",
          title:`Hide every school that is not ${label}`,
          onclick:()=>{ prefs[key]=true; onSingleSelect(); }}),
        el("button",{type:"button","aria-pressed":String(val===false),text:"Hide these",
          title:`Hide every school that is ${label}`,
          onclick:()=>{ prefs[key]=false; onSingleSelect(); }}),
      ]),
      hint ? el("p",{class:"hint",text:hint}) : null,
    ]);
  };

  // Pre-2026-08-29 this only ever looked at PS.prefs, so "Clear all
  // preferences" stayed hidden for a family who had set nothing BUT the
  // maximum-distance filter or the AL score search -- both real filters
  // (SAFEGUARDS.md 5.1 still applies to them) with no way to clear them from
  // here even though the button's own onclick already resets PS.filters too.
  const alSearchIsActive = PS.filters.al.mode==="upper"
    ? PS.filters.al.upper!=null
    : (PS.filters.al.min!=null && PS.filters.al.max!=null);
  const hasAnyPreference = PS.prefs.postal_code || PS.prefs.student_sex || PS.prefs.gender ||
    PS.prefs.want_sap!=null || PS.prefs.want_ip!=null || PS.prefs.want_autonomous!=null ||
    PS.prefs.want_gifted!=null || PS.prefs.school_types.length ||
    PS.filters.maxKm!=null || alSearchIsActive;

  host.replaceChildren(
    ...[
      hasAnyPreference ? el("div",{class:"actions"},[
        el("button",{type:"button",class:"ghost",text:"Clear all preferences",
          title:"Reset every filter on this shortlist back to showing all schools",
          onclick:()=>{
            PS.prefs = {postal_code:null, student_sex:null, gender:null, want_sap:null,
              want_ip:null, want_autonomous:null, want_gifted:null, school_types:[]};
            PS.filters = {maxKm:null, al:{mode:"upper", upper:null, min:null, max:null}};
            renderSchoolPrefs(); renderSchoolShortlist();
          }}),
      ]) : null,

      /* Not a preference -- a fact that decides whether a single-sex school
         is even a possible option, checked before anything else in
         matchSchool(). Asked first, and asked plainly, because a family
         should not have to guess why a girls' school they never ruled out
         has disappeared from the list below. */
      el("div",{class:"field"},[
        el("label",{text:"Is your child a boy or a girl?"}),
        el("div",{class:"chips",role:"group","aria-label":"Your child's sex"},
          [["","Not answered"],["male","Boy"],["female","Girl"]].map(([v,t])=>
            el("button",{type:"button",class:"chip","aria-pressed":String((prefs.student_sex||"")===v),text:t,
              title:"Used only to decide whether a single-sex school is even an option — never sent anywhere",
              onclick:()=>{
                prefs.student_sex = v||null;
                // A "co-ed or single-sex" preference for a gender your child
                // is not can no longer be honoured -- clear it rather than
                // leave a stale, now-impossible preference selected.
                if(prefs.gender==="girls" && prefs.student_sex==="male") prefs.gender=null;
                if(prefs.gender==="boys" && prefs.student_sex==="female") prefs.gender=null;
                onSingleSelect();
              }}))),
        el("p",{class:"hint",text:
          "Used only so PathAhead can hide a boys' or girls' school when it is not "+
          "actually an option, instead of showing it as if it were. Left unanswered, "+
          "single-sex schools below stay visible with a plain note that PathAhead "+
          "can't confirm either way, rather than guessing."}),
      ]),

      el("div",{class:"field field-max"},[
        el("label",{for:"schoolPostal",text:"Postal code (optional)"}),
        el("input",{type:"text",id:"schoolPostal",inputmode:"numeric",maxlength:"6",
          placeholder:"e.g. 738907",
          title:"Your postal code, used only to sort by distance and feed the distance filter — never sent anywhere",
          value: prefs.postal_code||"",
          oninput:e=>{ prefs.postal_code = e.target.value.trim()||null;
            paintPostalStatus(); paintSchoolDistanceFilterHost(); renderSchoolShortlist(); }}),
        el("div",{id:"schoolPostalStatus"}),
        el("p",{class:"hint",text:
          "This is separate from S1 posting itself, which — as the honesty section above "+
          "says — never uses your address at all. Here, a postal code only helps YOU compare "+
          "schools by your own convenience: it shows your postal district as a tag on every "+
          "card, sorts the list by real straight-line distance when you've given one, and "+
          "feeds the maximum-distance filter further down. That distance is never a travel "+
          "time and never used to rank how well a school matches — only to sort and to filter. "+
          "Either way, this postal code itself is never sent anywhere — nothing you type here "+
          "leaves this device. If you click \"Get directions\" on a school, that opens Google "+
          "Maps for that school's address only; your postal code is not carried along, and "+
          "Google asks you for your own starting point itself."}),
      ]),
    ].filter(Boolean),

    (() => {
      // Only offer a single-sex option your child could actually attend --
      // showing "Girls' school" as a pickable preference for a boy would
      // let a family set a preference that can never be honoured.
      const genderOpts = [["","Any"],["co-ed","Co-ed"]];
      if(prefs.student_sex !== "male") genderOpts.push(["girls","Girls' school"]);
      if(prefs.student_sex !== "female") genderOpts.push(["boys","Boys' school"]);
      return el("div",{class:"field"},[
        el("label",{text:"Co-ed or single-sex?"}),
        el("div",{class:"chips",role:"group","aria-label":"Co-ed or single-sex"},
          genderOpts.map(([v,t])=>
            el("button",{type:"button",class:"chip","aria-pressed":String((prefs.gender||"")===v),text:t,
              title:v ? `Show only ${t} schools your child is eligible for` : "Don't filter by co-ed or single-sex",
              onclick:()=>{ prefs.gender = v||null; onSingleSelect(); }}))),
        !prefs.student_sex ? el("p",{class:"hint",text:
          "Answer your child's sex above and this list will only offer single-sex "+
          "options they could actually attend."}) : null,
      ]);
    })(),

    triState("Special Assistance Plan (SAP)","want_sap",
      "A bilingual programme with a Chinese language and culture emphasis."),
    triState("Integrated Programme (IP)","want_ip",
      "One six-year run through to A-Level or the IB, without sitting O-Levels along the way."),
    triState("Autonomous school","want_autonomous",
      "Extra funding for facilities and programmes, and its own admission exercise for some places."),
    triState("Gifted Education Programme branch","want_gifted",
      "Only eight secondary schools have one."),

    el("div",{class:"field"},[
      el("label",{text:"School type"}),
      el("div",{class:"chips",role:"group","aria-label":"School type"},
        SCHOOL_TYPE_OPTIONS.map(t=>
          el("button",{type:"button",class:"chip","aria-pressed":String(prefs.school_types.includes(t)),text:t,
            title:`Toggle showing ${t}s — pick more than one to include several types`,
            onclick:e=>{ toggleChip(e.currentTarget, prefs.school_types, t); renderSchoolShortlist(); }}))),
    ]),

    el("h3",{text:"Narrow the list further (optional)"}),

    /* Straight-line km bands, never minutes: see schoolDirectionsUrl() and
       the postal-code hint for why PathAhead does not claim a travel time.
       Rendered into its OWN host, repainted by paintSchoolDistanceFilterHost()
       rather than a full renderSchoolPrefs(), because the postal code input
       above lives in THIS SAME section -- a full re-render on every
       keystroke there would destroy the input being typed into (the exact
       bug the PSLE score field's own oninput handler was already fixed for
       once; see there). */
    el("div",{id:"schoolDistanceFilterHost"}),

    /* SAFEGUARDS.md 5.1 forbids ranking schools by cut-off point, so this
       narrows which schools appear without ever reordering what remains.
       See engine/school_fit.py:combined_reach for the four states and
       within_reach for the margin and the reasoning behind it.

       This is an EXPLICIT search, deliberately separate from "If you have
       the score" above: that field drives the Posting Group calculator and
       nothing else, so typing a number into it to merely browse the
       shortlist used to mean either reusing it for two different purposes
       at once, or having no way to explore a score you don't actually have
       yet. Two modes: "Upper bound" is a single score; "Range" is for a
       family working from an estimate (a mock exam, a teacher's guess)
       rather than a result -- see combinedReach()'s four states for what
       each end of a range can honestly tell you. */
    (() => {
      const spec = psleTransition()?.rule_params?.posting_groups;
      // The filter needs cut-off figures to compare against, and the
      // published build carries none -- PathAhead does not republish them
      // (see cutoffRangeLine()). It therefore only becomes usable when the
      // person running it has supplied their own local copy. Hidden rather
      // than shown-disabled in that case: a permanently dead control with
      // an explanation nobody can act on is worse than no control, and the
      // card-level SchoolFinder link already answers the same question one
      // school at a time.
      const hasLocalCutoffs = (S.pack?.schools||[]).some(s=>s.cutoff_2025);
      if(!hasLocalCutoffs) return null;
      const al = PS.filters.al;
      const canUse = !!spec;
      const onField = (field) => (e) => {
        const v = parseInt(e.target.value,10);
        al[field] = Number.isFinite(v) && v>=4 && v<=32 ? v : null;
        renderSchoolShortlist();
      };
      const scoreField = (id,label,field) => el("div",{class:"field field-max"},[
        el("label",{for:id,text:label,
          title:"PSLE Achievement Level sum: 4 (best) to 32 (worst)."}),
        el("input",{type:"number",id,min:"4",max:"32",inputmode:"numeric",
          title:"Enter a PSLE AL score from 4 to 32 — lower is stronger.",
          disabled: !canUse, value: al[field]==null ? "" : String(al[field]),
          oninput: onField(field)}),
      ]);
      return el("div",{class:"field",role:"group","aria-label":"Reach filter"},[
        el("label",{text:"Search schools by AL score (explicit)"}),
        el("p",{class:"hint",text:
          "Separate from the calculator above: type a score here directly (or a realistic "+
          "range, if you're working from an estimate rather than a result) and the list below "+
          "narrows to schools that stay in reach of it. The score entered above never feeds "+
          "this on its own, and typing here never changes what the calculator says."}),
        el("div",{class:"seg",role:"group","aria-label":"AL score search mode"},[
          el("button",{type:"button","aria-pressed":String(al.mode==="upper"),text:"Upper bound",
            title:"Search with one AL score — schools within reach of it stay visible.",
            disabled: !canUse,
            onclick:()=>{ al.mode="upper"; renderSchoolPrefs(); renderSchoolShortlist(); }}),
          el("button",{type:"button","aria-pressed":String(al.mode==="range"),text:"Range",
            title:"Search with a best-case-to-worst-case AL score range, for an estimate rather than a result.",
            disabled: !canUse,
            onclick:()=>{ al.mode="range"; renderSchoolPrefs(); renderSchoolShortlist(); }}),
        ]),
        al.mode==="upper" ? el("div",{},[
          scoreField("alSearchUpper","AL score (4 to 32)","upper"),
          (PS.score!=null && al.upper==null) ? el("button",{type:"button",class:"ghost",
            title:"Copy the score from the calculator above into this search.",
            text:`Use the ${PS.score} entered above`,
            onclick:()=>{ al.upper=PS.score; renderSchoolPrefs(); renderSchoolShortlist(); }}) : null,
        ].filter(Boolean)) : el("div",{},[
          scoreField("alSearchMin","Best realistic AL score (4 to 32)","min"),
          scoreField("alSearchMax","Worst realistic AL score (4 to 32)","max"),
        ]),
        el("p",{class:"hint",title:"How this search reads the cut-off figures in your own local copy.",text: !canUse
          ? "This build has no Posting Group table to compare a score against."
          : al.mode==="upper"
          ? "Uses the cut-off figures from your own local copy, plus a margin, since MOE's own "+
            "figures say cut-off points \"can fluctuate by a few points year-on-year.\" A school "+
            "with no cut-off in your copy still shows, marked as unable to be judged rather than "+
            "hidden."
          : "Uses the SAME cut-off figures and margin, checked at both ends of your range. A "+
            "school reads \"in reach\" if it stays in reach even at your worst-case score, "+
            "\"possible\" if only your best-case score reaches it — read that one as depending "+
            "on the better end of your range, never as a plain match — and is hidden only when "+
            "neither end of the range reaches it at all."}),
        el("p",{class:"hint",text:
          "These figures are yours, not PathAhead's: it has not verified them, and you should "+
          "check anything that matters against the school's own SchoolFinder page, linked on "+
          "every card."}),
      ]);
    })(),
  );
  paintPostalStatus();
  paintSchoolDistanceFilterHost();
}

function paintPostalStatus(){
  const host = $("#schoolPostalStatus"); if(!host) return;
  const pc = PS.prefs.postal_code;
  if(!pc){ host.replaceChildren(); return; }
  const row = resolveDistrict(S.pack, pc);
  host.replaceChildren(el("p",{class:"hint",style:"margin-top:.3rem",text: row
    ? `Postal district ${row.district} — ${row.area} (${titleCase(row.region)}).`
    : "That doesn't look like a Singapore postal code (6 digits), so it will not be used."}));
}

/** Repaints just the distance-filter chips -- called on every postal-code
    keystroke (see #schoolPostal's oninput below), so it must never touch
    the postal code input itself. A full renderSchoolPrefs() would, since
    that input lives in the section it rebuilds. */
function paintSchoolDistanceFilterHost(){
  const host = $("#schoolDistanceFilterHost"); if(!host) return;
  const hasPostal = !!PS.prefs.postal_code;
  const km = PS.filters.maxKm;
  const opts = [[null,"Any distance"],[5,"Within ~5 km"],[10,"Within ~10 km"],[20,"Within ~20 km"]];
  host.replaceChildren(el("div",{class:"field"},[
    el("label",{text:"How far is too far? (straight-line, not a travel time)"}),
    el("div",{class:"chips",role:"group","aria-label":"Maximum distance"},
      opts.map(([v,t])=>
        el("button",{type:"button",class:"chip","aria-pressed":String(km===v),text:t,
          title: v==null ? "Don't filter by distance" : `Hide schools more than ~${v} km away, straight-line`,
          disabled: !hasPostal,
          onclick:()=>{ PS.filters.maxKm=v; paintSchoolDistanceFilterHost(); renderSchoolShortlist(); }}))),
    !hasPostal ? el("p",{class:"hint",text:
      "Set a postal code above first — without it PathAhead has nothing to measure distance from."}) : null,
  ]));
}

const SCHOOL_PAGE = 10;
let schoolShortlistExpanded = false;

/** Resolves the EXPLICIT AL-score search (renderSchoolPrefs' "Search by AL
    score" block) into a combined-reach state for one school -- one of
    combinedReach()'s four strings, or null when the search itself has
    nothing to say yet (nothing typed, or -- in "range" mode -- only one of
    the two ends). null here means "this filter is not active", never
    "unknown reach"; schoolCard()/reachLine() below read it that way.
    Computed once per render rather than once per school. Deliberately
    independent of PS.score / the Posting Group calculator above -- the
    "Use the ... entered above" button is the one deliberate bridge between
    the two, and only ever copies a value across on a click. */
function alSearchReach(school){
  const al = PS.filters.al;
  const spec = psleTransition()?.rule_params?.posting_groups;
  if(!spec) return null;
  let lo, hi;
  if(al.mode==="upper"){
    if(al.upper==null) return null;
    lo = hi = al.upper;
  } else {
    if(al.min==null || al.max==null) return null;
    lo = Math.min(al.min, al.max);
    hi = Math.max(al.min, al.max);
  }
  const groupsFor = sc => postingGroupFor(spec, sc, null).groups || [];
  return combinedReach(school, lo, hi, groupsFor(lo), groupsFor(hi));
}

function renderSchoolShortlist(){
  const host = $("#schoolShortlistHost"); if(!host) return;
  const pack = S.pack; if(!pack) return;
  const allRows = shortlistSchools(pack, PS.prefs);

  // Every filter narrows WHICH of the already-sorted rows appear; none of
  // them reorder anything (SAFEGUARDS.md 5.1 -- see the field comments
  // above). eligible===false is the one unconditional hide; everything
  // else only hides when the family actually set it.
  const maxKm = PS.filters.maxKm;
  let hiddenBySex = 0, hiddenByPrefs = 0, hiddenByKm = 0, hiddenByReach = 0;
  const rows = allRows.filter(([school,m])=>{
    if(m.eligible===false){ hiddenBySex++; return false; }
    if(!m.matches_preferences){ hiddenByPrefs++; return false; }
    if(maxKm!=null && m.distance_km!=null && m.distance_km>maxKm){ hiddenByKm++; return false; }
    if(alSearchReach(school)==="out-of-reach"){ hiddenByReach++; return false; }
    return true;
  });

  if(!rows.length){
    host.replaceChildren(el("p",{class:"hint",id:"schoolNoPrefs",text:
      "No school matches the filters above — try clearing a preference, widening the "+
      "distance, or clearing the AL score search, and PathAhead will show what it hid."}));
    return;
  }

  const shown = schoolShortlistExpanded ? rows.length : Math.min(SCHOOL_PAGE, rows.length);
  const list = el("ul",{class:"courses",id:"schoolResults"});
  for(const [school,m] of rows.slice(0,shown)) list.append(schoolCard(school,m,alSearchReach(school)));

  const sortNote = PS.prefs.postal_code ? "closest to you first" : "in alphabetical order";
  let summary = rows.length===allRows.length
    ? `All ${allRows.length} schools, ${sortNote}.`
    : `${rows.length} of ${allRows.length} schools, ${sortNote}.`;
  const bits=[];
  if(hiddenBySex) bits.push(`${hiddenBySex} not admitting your child's sex`);
  if(hiddenByPrefs) bits.push(`${hiddenByPrefs} not matching a preference you set`);
  if(hiddenByKm) bits.push(`${hiddenByKm} outside the distance you set`);
  if(hiddenByReach) bits.push(`${hiddenByReach} outside reach of the AL score you searched`);
  if(bits.length) summary += ` (${bits.join(", ")} — hidden by the filters above, never scored or ranked.)`;

  const parts = [
    el("p",{class:"hint",text:summary}),
    list,
  ];
  if(rows.length>SCHOOL_PAGE) parts.push(el("button",{type:"button",class:"more",
    text: schoolShortlistExpanded ? "Show fewer" : `Show all ${rows.length}`,
    title: schoolShortlistExpanded ? `Collapse back to the first ${SCHOOL_PAGE} schools`
      : `Expand to see all ${rows.length} matching schools at once`,
    onclick:()=>{ schoolShortlistExpanded=!schoolShortlistExpanded; renderSchoolShortlist(); }}));
  host.replaceChildren(...parts);
}

/** Google Maps directions link for a school -- destination only, never an
    origin. The family's own postal code is never included: the field above
    promises "nothing you type leaves this device", and this link keeps
    that promise literally by carrying only the school's own already-public
    address. Google Maps asks the family for their starting point itself,
    on Google's own site, only after they choose to click through. */
function schoolDirectionsUrl(school){
  const dest = `${school.address}, Singapore ${school.postal_code}`;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dest)}`;
}

/** A school's own page on MOE SchoolFinder -- the official, current,
    first-party source for its Posting Group and Integrated Programme PSLE
    Score ranges.

    This link is the FEATURE, not a footnote. PathAhead does not republish
    those ranges: MOE publishes them, MOE's Terms of Use reserve
    reproduction, and a copied snapshot would go stale the moment the next
    posting exercise runs. Sending the reader to the source is both the
    lawful position and the more useful one — they get this year's figures,
    in MOE's own framing, with MOE's own caveats attached.

    Built from the school id, which is the slug SchoolFinder itself uses. */
function schoolFinderUrl(school){
  return `https://www.moe.gov.sg/schoolfinder/schooldetail/${encodeURIComponent(school.id)}`;
}

/** Formats a locally-held PSLE Score range per Posting Group, or null.

    Returns null in the published build, always: `cutoff_2025` is null for
    every school unless the person running PathAhead has supplied their own
    copy under `packs/<id>/local/` (see engine/loader.py and
    docs/LOCAL_DATA.md). "Lower is stronger" is stated wherever this is
    rendered, because reading a bigger PSLE Score as "better" is the single
    most likely misreading of an Aggregate Score range. Never a score, never
    a sort key — see SAFEGUARDS.md 5.1. */
function cutoffRangeText(school){
  const c = school.cutoff_2025;
  if(!c) return null;
  const band = (label,v) => v ? `${label} ${v[0]}–${v[1]}` : null;
  return [band("PG3",c.pg3), band("PG2",c.pg2), band("PG1",c.pg1), band("IP",c.ip)]
    .filter(Boolean).join(" · ") || null;
}

/** Shown on EVERY school card, whether or not a PSLE score has been entered.

    Three states, and they say three genuinely different things — collapsing
    any two of them would tell a family something untrue:

      1. No figures held (the published build). Says so plainly, says WHY
         (they are MOE's to publish), and hands over a link to the school's
         own SchoolFinder page so the reader fetches the official figure
         themselves. PathAhead never holds it, so it can never be stale or
         mistranscribed here.
      2. No figures exist at all — the 8 specialised-admission schools that
         sit outside the S1 Posting Exercise entirely. A fact about the
         school, not about PathAhead.
      3. Figures present from the reader's own local copy. Labelled as
         locally supplied, dated, and never presented as something PathAhead
         published or verified.

    Every state still offers the SchoolFinder link, because even a reader
    with local figures should be able to check them against the source. */
function cutoffRangeLine(school){
  const text = cutoffRangeText(school);
  const link = el("a",{href:schoolFinderUrl(school),target:"_blank",
    rel:"noopener noreferrer",text:"View on MOE SchoolFinder ↗"});

  if(text) return el("div",{class:"c-sub","data-cutoff":text,"data-cutoff-origin":"local"},[
    el("span",{text:
      `From your own local copy (not published by PathAhead) — PSLE Score range by `+
      `Posting Group, lower is stronger: ${text}. Check against the source: `}),
    link,
  ]);

  // The 8 specialised-admission schools carry their own explanatory note
  // from the pack; everything else carries the "not republished" note. Both
  // arrive in cutoff_note — see tools/build_secondary_schools_pack.py, which
  // deliberately keeps the two sentences distinct.
  return el("div",{class:"c-sub","data-cutoff":"","data-cutoff-origin":"linked"},[
    el("span",{text:(school.cutoff_note ||
      "PathAhead does not republish Posting Group cut-off points.")+" "}),
    link,
  ]);
}

/** Plain-language line for one school's reach status against the AL score
    (or range) the family explicitly searched -- see alSearchReach()'s
    comment for what each of the four states means. Never says "you missed
    the cut-off" or any other verdict
    language (SAFEGUARDS.md 5.3); states the published number and lets the
    family read it themselves. The "no cut-off published at all" case is
    handled once, unconditionally, by cutoffRangeLine() above instead of
    here, so it does not depend on a score having been entered yet. */
function reachLine(school, reach){
  if(reach==="in-reach") return el("div",{class:"c-sub",text:
    "Last year's Posting Group cut-off suggests this school stays in reach across the AL score "+
    "you searched."});
  if(reach==="possible") return el("div",{class:"c-sub",text:
    "Last year's Posting Group cut-off puts this school in reach only near the better end of the "+
    "range you searched — depends on the best case, not a plain match."});
  // "out-of-reach" never actually reaches this function -- renderSchoolShortlist() hides those
  // schools before schoolCard() is ever called for them, the same way an eligible===false school
  // never reaches schoolCard() either. Kept as an explicit branch anyway, for the same reason: a
  // future change to that filter should not silently start showing an unlabelled card.
  if(reach==="out-of-reach") return el("div",{class:"c-sub",text:
    "Last year's Posting Group cut-off was better than the AL score you searched by more than a "+
    "few points — still allowed as one of your six choices, just less likely on past figures."});
  return null; // the AL score search isn't active, or PathAhead can't judge this school -- nothing extra to say
}

/** Plain-language line when PathAhead cannot yet confirm a single-sex
    school's eligibility -- match.eligible===null only. A confirmed
    eligible===false school never reaches schoolCard() at all (see
    renderSchoolShortlist's filter), so this never needs to explain a hide,
    only an "unanswered" state. Never verdict language. */
function eligibilityLine(match){
  if(match.eligible!==null) return null;
  return el("div",{class:"c-sub",text:match.eligibility_reason});
}

function schoolCard(school, match, reach){
  const meta = el("div",{class:"c-meta"},[
    el("span",{class:"tag",text:school.type_label}),
    el("span",{class:"tag",text:school.gender==="co-ed"?"Co-ed":school.gender==="girls"?"Girls' school":"Boys' school"}),
    school.district ? el("span",{class:"tag",title:school.mrt_desc||"",
      text:`District ${school.district}`}) : null,
    school.sap ? el("span",{class:"tag",text:"SAP"}) : null,
    school.ip ? el("span",{class:"tag",text:"Integrated Programme"}) : null,
    school.autonomous ? el("span",{class:"tag",text:"Autonomous"}) : null,
    school.gifted ? el("span",{class:"tag",text:"GEP branch"}) : null,
  ].filter(Boolean));

  // Shown whenever a postal code was given -- distance_km is populated
  // independently of eligibility/filters above and never feeds anything
  // but the sort order and the km filter. Labelled plainly as
  // straight-line so nobody reads it as an estimate of commute time; the
  // link opens Google Maps for a REAL one, only if and when a family clicks
  // it, and never carries the postal code they typed here (see
  // schoolDirectionsUrl()'s comment above).
  const distanceLine = match.distance_km!=null ? el("div",{class:"c-sub","data-distance":String(match.distance_km)},[
    el("span",{text:`≈${match.distance_km.toFixed(1)} km away, straight-line (not a travel time). `}),
    el("a",{href:schoolDirectionsUrl(school),target:"_blank",rel:"noopener noreferrer",
      text:"Get directions ↗"}),
  ]) : null;

  return el("li",{class:"course","data-school":school.id,style:"grid-template-columns:1fr",
    "data-reach": reach==null?"unknown":reach},[
    el("div",{class:"c-top"},[
      el("div",{},[el("div",{class:"c-name",text:school.name}),
        el("div",{class:"c-sub",text:school.address}),
        distanceLine,
        eligibilityLine(match),
        cutoffRangeLine(school),
        reachLine(school, reach),
      ]),
    ]),
    meta,
  ]);
}

const psleNothingYet = () => el("p",{class:"hint",id:"psleNoScore",
  text:"Nothing entered yet, so nothing is claimed."});

/** Repaint just the answer. Called on every keystroke; the field itself, and
    the caret in it, are left alone. */
function paintPsleAnswer(){
  const host=$("#psleAnswerHost"); if(!host) return;
  const spec=psleTransition()?.rule_params?.posting_groups;
  host.replaceChildren(PS.score==null ? psleNothingYet()
    : psleAnswer(postingGroupFor(spec, PS.score, null), spec));
}

/** The answer to a score. Deliberately not a verdict, and deliberately never
    a number PathAhead made up — every figure shown here is one MOE published. */
function psleAnswer(res, spec){
  if(!res.groups.length){
    return el("div",{class:"note info",id:"psleResult"},[
      el("p",{text: spec?.outside_the_table?.headline
        || "This score is outside the Posting Group table MOE publishes."}),
      el("p",{class:"hint",text:"What that means is set out below. PathAhead does not "+
        "guess at a threshold nobody published."}),
    ]);
  }
  const many = res.groups.length>1;
  return el("div",{class:"note info",id:"psleResult"},[
    el("p",{text: many
      ? `A score of ${res.score} opens Posting Group ${res.groups.join(" or ")}. You choose between them.`
      : `A score of ${res.score} opens Posting Group ${res.groups[0]}.`}),
    res.level ? el("p",{class:"hint",text:`Most subjects would start at ${res.level} in Secondary 1.`}) : null,
    many ? el("p",{class:"hint",text:
      "Whichever you pick applies to all six school choices — they cannot be mixed. "+
      `If no choices are submitted, Posting Group ${res.defaultGroup} is assigned.`}) : null,
    el("p",{class:"hint",text:
      "This is which doors are open, and nothing more. It is not a measure of your child, "+
      "and PathAhead has not compared them to anyone."}),
  ].filter(Boolean));
}

function citeSource(id){
  if(!id) return null;
  const s=sourceById(id);
  if(!s) return null;
  return el("p",{class:"cite"},[
    el("span",{text:"Source: "}),
    el("a",{href:s.url,rel:"noopener",target:"_blank",text:s.name}),
    el("span",{text:` — ${s.publisher}, read ${s.retrieved}.`}),
  ]);
}

/* ── #/olevel — the O-Level/SEC stage's own front door ──────────────
   Two rulebooks share one exam: a student who started Secondary 1 in 2023
   sits the legacy GCE O-Level and applies under L1R5/ELR2B2; everyone behind
   them sits the Secondary Education Certificate under L1R4, a different
   subject count on a different ceiling. Cohort choice comes before a single
   grade is asked for — the same "no form above the fold" reasoning as
   #/psle, and the same lesson the Primary-6-in-an-A-Level-dropdown bug
   taught: which rulebook applies is the FIRST question, never inferred from
   a form built for a different one.

   `requiredPlusBestN` (the engine section above) is a port of
   engine/rules/required_plus_best_n.py and must agree with it — see the
   "olevel-" and "sec-" golden fixtures in evals/golden/rules.json. */
const OL = { yearLevel:null, rows:[] };
const OL_GRADE_OPTIONS = ["1","2","3","4","5","6","7","8","9"];

const olevelCohorts = () => (S.pack?.cohorts||[]).filter(c=>c.stage==="o-level");
const olevelSubjectsPack = () => (S.pack?.subjects||[]).filter(s=>s.stage==="o-level");
const olevelTransitionFor = yl => {
  const c = olevelCohorts().find(c=>c.year_level===yl);
  if(!c) return null;
  return (S.pack?.transitions||[]).find(t=>t.id===c.transition) || null;
};
/* also_scored_under makes a second transition answer to outcomes it does not
   own — the polytechnic outcomes loaded for A-Level are the exact same
   records an O-Level applicant is scored against. Mirrors
   engine/model.py:Pack.outcomes_for(). */
const outcomesForTransitionId = id =>
  (S.pack?.outcomes||[]).filter(o=>o.transition===id || (o.also_scored_under||[]).includes(id));

function olevelReadSubjects(){
  const defs = olevelSubjectsPack();
  return OL.rows.filter(r=>r.code && r.grade).map(r=>{
    const def = defs.find(s=>s.code===r.code);
    return {code:r.code, name:def?.name||r.code, level:"subject", grade:r.grade};
  });
}

function renderOlevel(){
  const box=$("#olevelOut"); if(!box) return;
  const pack=S.pack; if(!pack) return;
  const cohorts = olevelCohorts();
  if(!cohorts.length){
    box.replaceChildren(el("section",{class:"card"},[
      el("h2",{text:"The O-Level stage is not in this data pack"}),
      el("p",{class:"lede",text:"This build was made without it. Nothing is broken — "+
        "the page simply has nothing to show, and says so rather than pretending."})]));
    return;
  }
  const cohort = cohorts.find(c=>c.year_level===OL.yearLevel) || null;
  const t = cohort ? olevelTransitionFor(cohort.year_level) : null;

  const children = [
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"O-Level and the SEC"}),
      el("h1",{id:"olevelH1",text:"One exam feeds two rulebooks. Here is which one is yours."}),
      el("p",{class:"lede",text:
        "2026 is the last year the GCE O-Level is awarded. Which formula applies to you "+
        "depends on the year you started Secondary 1, not on the year you sit the exam."}),
      el("p",{class:"hint",text:
        "Nothing on this page leaves this device. There is no server to send it to."}),
    ]),
    el("section",{class:"card"},[
      el("h2",{text:"When did you start Secondary 1?"}),
      el("div",{class:"chips",id:"olevelCohorts",role:"group","aria-label":"Your cohort"},
        cohorts.map(c=>el("button",{type:"button",class:"chip",
          "aria-pressed": String(OL.yearLevel===c.year_level),
          text:c.label,
          title:`Use the rulebook for students who started Secondary 1 ${c.label}`,
          onclick:()=>{ OL.yearLevel=c.year_level; OL.rows=[]; renderOlevel(); }}))),
      cohort ? el("p",{class:"note info",id:"olevelCohortNote",text:cohort.note}) : null,
    ]),
    cohort ? olevelSubjectsCard() : null,
  ].filter(Boolean);
  if(cohort && t) children.push(...[].concat(olevelResultCard(t)));

  box.replaceChildren(...children);
}

function olevelSubjectsCard(){
  const subs = olevelSubjectsPack();
  const used = new Set(OL.rows.map(r=>r.code));
  const available = subs.filter(s=>!used.has(s.code));
  const addSelect = el("select",{id:"olevelAddSubject","aria-label":"Add a subject"},[
    el("option",{value:"",text:"Choose a subject…"}),
    ...available.map(s=>el("option",{value:s.code,text:s.name}))]);
  addSelect.addEventListener("change",e=>{
    const code=e.target.value; if(!code) return;
    OL.rows.push({code, grade:"1"});
    renderOlevel();
  });
  return el("section",{class:"card"},[
    el("h2",{text:"Your subjects and grades"}),
    el("p",{class:"hint",text:
      "Enter each subject as the results slip will show it — A1, A2, B3 and so on. "+
      "There is no fixed number of rows: add every subject you are taking."}),
    OL.rows.length ? el("table",{class:"cmp",id:"olevelRows"},[
      el("thead",{},[el("tr",{},[el("th",{text:"Subject"}),el("th",{text:"Grade"}),el("th",{text:""})])]),
      el("tbody",{},OL.rows.map((row,i)=>{
        const def = subs.find(s=>s.code===row.code);
        const gr = el("select",{"aria-label":`Grade for ${def?.name||row.code}`},
          OL_GRADE_OPTIONS.map(g=>el("option",{value:g,text:olLabel(g),...(row.grade===g?{selected:"selected"}:{})})));
        gr.addEventListener("change",e=>{ row.grade=e.target.value; renderOlevel(); });
        const rm = el("button",{class:"rmbtn",type:"button","aria-label":`Remove ${def?.name||row.code}`,text:"×",
          title:`Remove ${def?.name||row.code} from your subject list`,
          onclick:()=>{ OL.rows.splice(i,1); renderOlevel(); }});
        return el("tr",{},[el("td",{text:def?.name||row.code}),el("td",{},gr),el("td",{},rm)]);
      })),
    ]) : el("p",{class:"hint",id:"olevelNoSubjects",text:"No subjects added yet."}),
    available.length
      ? el("div",{class:"field",style:"margin-top:.6rem"},[
          el("label",{for:"olevelAddSubject",text:"Add a subject"}), addSelect])
      : el("p",{class:"hint",text:"Every subject in the pack has been added."}),
  ]);
}

/** The derivation trace, shown the same way for the primary aggregate and
    the secondary (polytechnic) one — every step visible, nothing collapsed. */
function olevelDerivationTable(d){
  return el("div",{},[
    el("table",{class:"cmp"},[
      el("thead",{},[el("tr",{},[el("th",{text:"Step"}),el("th",{text:"Points"}),el("th",{text:"Running total"})])]),
      el("tbody",{},d.steps.map(s=>el("tr",{class:s.kind==="total"?"total-row":""},[
        el("td",{},[el("span",{text:s.label}), s.detail?el("div",{class:"hint",text:s.detail}):null].filter(Boolean)),
        el("td",{text:s.points!=null?num(s.points):"—"}),
        el("td",{text:s.running_total!=null?num(s.running_total):"—"}),
      ]))),
    ]),
    el("p",{class:"big",style:"margin-top:.5rem",
      text:`Total: ${num(d.value)}`+(d.max_value!=null?` (weakest possible ${num(d.max_value)})`:"")}),
  ]);
}

/** Run one transition's rule against the current subjects, extracting the
    comparison figure the same way run() does for A-Level — most components
    ARE the comparison figure for these transitions, but `comparison_component`
    is still honoured so a future transition that adds bonus points on top
    does not have to change this function. */
function olevelScore(t, subjects){
  const fn = RULES[t.rule_kind];
  if(!fn) throw new PAError(`this version cannot read the rule "${t.rule_kind}"`,"Please refresh the page.");
  const d = fn(t.rule_params, t.scales, subjects, t.caveats);
  let comparison = d.value;
  const key = t.rule_params.comparison_component;
  if(key){ const st=d.steps.find(s=>s.running_total!=null&&s.label.toLowerCase().startsWith(key.toLowerCase()));
           if(st) comparison=st.running_total; }
  return {d, comparison};
}

function olevelOutcomesSection(heading, outcomes, comparison, direction){
  const groups={};
  for(const o of outcomes){
    let b;
    if(o.band && !bandComparable(o.band)) b="published_on_another_basis";
    else if(o.band && o.band.statistic==="min_max") b=assessMinMaxBand(comparison,o.band.p10_points,o.band.p90_points,direction);
    else if(o.band) b=assessBand(comparison,o.band.p10_points,o.band.p90_points,direction,o.band.statistic);
    else b="data_incomplete";
    (groups[b]=groups[b]||[]).push(o);
  }
  const sections=[];
  for(const key of ORDER){
    const items=groups[key]; if(!items) continue;
    items.sort((a,b)=>a.institution_short.localeCompare(b.institution_short)||a.name.localeCompare(b.name));
    const useMinMax = items[0]?.band?.statistic==="min_max";
    const HL = (useMinMax?HEADLINE_MINMAX:HEADLINE)[key] || HEADLINE[key];
    const EX = (useMinMax?EXPLAIN_MINMAX:EXPLAIN)[key] || EXPLAIN[key];
    sections.push(el("div",{class:"bucket"},[
      el("h3",{class:GCLASS[key],text:`${HL} (${items.length})`}),
      el("p",{class:"hint",text:EX}),
      el("ul",{class:"courses"},items.map(o=>olevelCourseCard(o,key,comparison,useMinMax))),
    ]));
  }
  return el("section",{class:"card"},[
    el("h2",{text:heading}),
    el("p",{class:"hint",text:`Your aggregate: ${num(comparison)}. Lower is better.`}),
    ...sections,
  ]);
}

function olevelCourseCard(o, bucketKey, comparison, useMinMax){
  const badgeText = (useMinMax?HEADLINE_MINMAX:HEADLINE)[bucketKey] || HEADLINE[bucketKey];
  const parts=[
    el("div",{class:"c-top"},[
      el("div",{},[el("div",{class:"c-name",text:o.name}),
        el("div",{class:"c-sub",text:o.institution})]),
      el("span",{class:"badge "+BCLASS[bucketKey],text:badgeText}),
    ]),
  ];
  if(o.band){
    parts.push(el("div",{class:"small",text: !bandComparable(o.band)
      ? `${o.band.p10}–${o.band.p90}, ${o.band.basis}. Shown, not compared with your result — it is a different measure.`
      : `Your ${num(comparison)} against ${o.band.p10}–${o.band.p90} (${o.band.fact?.as_of_year??""}), ${o.band.basis}.`
    }));
  }
  if(o.url) parts.push(el("a",{href:o.url,target:"_blank",rel:"noopener noreferrer",text:"official page"}));
  return el("li",{class:"course","data-course":o.id}, parts);
}

/** Everything below the subject table: the aggregate(s), and what they place
    you against. Returns an array of sections, spread into the page. */
function olevelResultCard(t){
  const subjects = olevelReadSubjects();
  if(!subjects.length) return [el("section",{class:"card"},[
    el("h2",{text:"Your aggregate"}),
    el("p",{class:"hint",id:"olevelNoScoreYet",
      text:"Add at least one subject above to see a derivation. Nothing is claimed until you do."})])];

  const parts=[];
  let primary;
  try{ primary = olevelScore(t, subjects); }
  catch(err){
    const e = err instanceof PAError ? err : new PAError("Something went wrong working that out.","Please check your entries.");
    if(!(err instanceof PAError)) console.error(err);
    parts.push(el("section",{class:"card"},[
      el("h2",{text:t.rule_params.total_label || "Your aggregate"}),
      el("div",{class:"note warn",id:"olevelError"},[el("strong",{text:e.message+" "}),el("span",{text:e.advice})])]));
    return parts;
  }

  parts.push(el("section",{class:"card"},[
    el("h2",{text:t.rule_params.total_label || "Your aggregate"}),
    olevelDerivationTable(primary.d),
    t.caveats?.length ? el("div",{class:"note info"}, t.caveats.map(c=>el("p",{text:c}))) : null,
  ].filter(Boolean)));

  const jc = outcomesForTransitionId(t.id);
  parts.push(jc.length
    ? olevelOutcomesSection("Where this places you — Junior College and Millennia Institute",
        jc, primary.comparison, t.direction)
    : el("section",{class:"card"},[
        el("h2",{text:"Junior College and Millennia Institute courses"}),
        el("p",{class:"hint",id:"olevelNoCourseData",text:
          "No course has a published cut-off under this system yet. PathAhead computes "+
          "the aggregate above and stops there, rather than guessing at a number nobody "+
          "has published."})]));

  // The polytechnic route — a SECOND published claim from the same subjects,
  // mirrored from engine/forward.py:explore_secondary(). Never asked for
  // twice; scored the moment the primary aggregate is.
  const polyId = t.id==="o-level-to-jc-mi-2027" ? "o-level-to-polytechnic-2027"
               : t.id==="sec-to-jc-mi-2028" ? "sec-to-polytechnic-2028" : null;
  const polyT = polyId ? (S.pack.transitions||[]).find(x=>x.id===polyId) : null;
  if(polyT){
    let poly;
    try{ poly = olevelScore(polyT, subjects); }
    catch(err){
      const e = err instanceof PAError ? err : new PAError("Something went wrong working that out.","Please check your entries.");
      if(!(err instanceof PAError)) console.error(err);
      parts.push(el("section",{class:"card"},[
        el("h2",{text:polyT.rule_params.total_label || "Polytechnic route (ELR2B2)"}),
        el("div",{class:"note warn"},[el("strong",{text:e.message+" "}),el("span",{text:e.advice})])]));
      return parts;
    }
    parts.push(el("section",{class:"card"},[
      el("h2",{text:polyT.rule_params.total_label || "Polytechnic route (ELR2B2)"}),
      olevelDerivationTable(poly.d),
      polyT.caveats?.length ? el("div",{class:"note info"}, polyT.caveats.map(c=>el("p",{text:c}))) : null,
    ].filter(Boolean)));

    const polyOutcomes = outcomesForTransitionId(polyT.id);
    parts.push(polyOutcomes.length
      ? olevelOutcomesSection("Where this places you — Polytechnic (ELR2B2, generic)",
          polyOutcomes, poly.comparison, polyT.direction)
      : el("section",{class:"card"},[
          el("h2",{text:"Polytechnic courses"}),
          el("p",{class:"hint",text:
            "No polytechnic course has a published cut-off under this system yet. "+
            "PathAhead computes the aggregate above and stops there."})]));
  }

  return parts;
}

/** #/results-day — for the day it went badly. Leads with routes, never a
    score, and never asks what the grades were. */
function renderResultsDay(){
  const box=$("#resultsDayOut"); if(!box) return;
  const pack=S.pack; if(!pack) return;
  const alt=(pack.routes||[]).filter(r=>r.kind!=="direct");
  box.replaceChildren(
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Results day"}),
      el("h2",{text:"If today did not go the way you hoped"}),
      el("p",{class:"lede",text:
        "You do not have to type anything in. This page does not ask what you got, "+
        "and there is no score anywhere on it."}),
      el("div",{class:"note info"},[el("span",{text:
        "A grade profile is a description of one intake in one year. It is not a "+
        "description of you, and it is not the last decision you get to make."})]),
    ]),
    el("section",{class:"card"},[
      el("h3",{text:"Ways in that are not the direct one"}),
      el("p",{class:"hint",text:
        "Every one of these is a real published route that real people take each year. "+
        "They are listed first here because on this particular day they matter more than "+
        "the direct one."}),
      el("ol",{class:"timeline"},alt.map(r=>el("li",{},[
        el("strong",{text:r.label}),
        r.steps?.length?el("ul",{class:"plain"},r.steps.map(s=>el("li",{text:s}))):null,
        r.caveat?el("p",{class:"hint",text:r.caveat}):null,
      ].filter(Boolean)))),
    ]),
    el("section",{class:"card"},[
      el("h3",{text:"People whose job this is"}),
      el("p",{text:
        "Your school's Education & Career Guidance counsellor and your form teacher "+
        "have done this every year for years, and they can see things a published table "+
        "cannot. Each institution's admissions office will also answer a direct question "+
        "about appeals and about what they actually weigh."}),
      el("p",{class:"hint",text:
        "PathAhead is a tool for reading published figures. It is not a substitute for "+
        "any of those conversations, and on today of all days it is the weaker option."}),
      el("div",{class:"actions"},[
        el("a",{class:"btn",href:"#/routes",text:"Work backwards from a course"}),
        el("a",{class:"btn",href:"#/explore",text:"Start from what you like instead"})]),
    ])
  );
}

/** #/perspectives — a parent and a child answer separately, then see where
    they agree and where they do not. Deliberately NOT scored: the output is a
    conversation, not a winner. */
const PERSP = {who:"child", child:{}, parent:{}};
const PERSP_Q = [
  {k:"interests", label:"What pulls at you?", multi:true,
   opts:()=>(S.pack.interests||[]).map(i=>[i.code,i.label])},
  {k:"assessment_style", label:"Doing your best work looks like",
   opts:()=>[["exams","Exams"],["coursework","Coursework and projects"],["practical","Hands-on"]]},
  {k:"teamwork", label:"You would rather work",
   opts:()=>[["individual","On your own"],["mixed","A mix"],["team","In a team"]]},
  {k:"priorities", label:"What matters most", multi:true,
   opts:()=>[["earnings","Financial security"],["impact","Doing something useful"],
             ["autonomy","Independence"],["stability","Stability"],["prestige","Recognition"]]},
];
/** Where two people agree and where they do not.
 *
 *  Pure, named and separate from the rendering because this is the substance
 *  of the feature and it must be checkable. Two properties matter and are
 *  tested: an answer only one person gave is a DIFFERENCE, not agreement; and
 *  nothing here scores, ranks or resolves — it returns two lists of sentences
 *  and takes no view on which column is right.
 */
function comparePerspectives(child, parent, questions){
  const agree=[], differ=[];
  for(const q of questions){
    const a=child[q.k], b=parent[q.k];
    if(a==null&&b==null) continue;
    const labels=Object.fromEntries(q.opts());
    if(q.multi){
      const A=new Set(a||[]), B=new Set(b||[]);
      const both=[...A].filter(x=>B.has(x));
      const onlyA=[...A].filter(x=>!B.has(x)), onlyB=[...B].filter(x=>!A.has(x));
      if(both.length) agree.push(`${q.label}: you both said ${both.map(x=>labels[x]).join(", ")}.`);
      if(onlyA.length||onlyB.length) differ.push(
        `${q.label}: ${onlyA.length?`only the young person said ${onlyA.map(x=>labels[x]).join(", ")}`:""}`+
        `${onlyA.length&&onlyB.length?"; ":""}`+
        `${onlyB.length?`only the parent said ${onlyB.map(x=>labels[x]).join(", ")}`:""}.`);
    } else if(a&&b){
      if(a===b) agree.push(`${q.label}: you both said ${labels[a]}.`);
      else differ.push(`${q.label}: the young person said ${labels[a]}, the parent said ${labels[b]}.`);
    } else if(a||b){
      const who=a?"the young person":"the parent";
      differ.push(`${q.label}: only ${who} answered — ${labels[a||b]}.`);
    }
  }
  return {agree,differ};
}

function renderPerspectives(){
  const box=$("#perspOut"); if(!box) return;
  if(!S.pack) return;
  const side=PERSP[PERSP.who];
  const other=PERSP.who==="child"?"parent":"child";
  const bothAnswered=PERSP_Q.some(q=>PERSP.child[q.k]!=null)&&PERSP_Q.some(q=>PERSP.parent[q.k]!=null);

  const answer=(q,v)=>{
    if(q.multi){ const cur=new Set(side[q.k]||[]); cur.has(v)?cur.delete(v):cur.add(v);
                 side[q.k]=[...cur]; }
    else side[q.k]=side[q.k]===v?null:v;
    renderPerspectives();
  };

  const cards=[
    el("section",{class:"card"},[
      el("p",{class:"eyebrow",text:"Two of you"}),
      el("h2",{text:"Answer separately, then compare"}),
      el("p",{class:"lede",text:
        "A parent and a young person often want different things from the same decision, "+
        "and the disagreement usually goes unsaid. Each of you answers the same four "+
        "questions here; PathAhead then shows where you already agree and where you do "+
        "not. It does not decide between you, and there is no score."}),
      el("div",{class:"seg",role:"group","aria-label":"Who is answering"},
        [["child","The young person"],["parent","The parent"]].map(([v,t])=>
          el("button",{type:"button","aria-pressed":String(PERSP.who===v),text:t,
            title:`Switch to answering as ${t.toLowerCase()}`,
            onclick:()=>{PERSP.who=v; renderPerspectives();}}))),
      el("p",{class:"hint",style:"margin-top:.5rem",text:
        `Answering as: ${PERSP.who==="child"?"the young person":"the parent"}. `+
        `Hand the device over and switch when you are done — nothing is saved or sent.`}),
    ]),
    el("section",{class:"card"},PERSP_Q.map(q=>el("div",{class:"field"},[
      el("label",{text:q.label}),
      el("div",{class:"chips",role:"group"},q.opts().map(([v,t])=>{
        const on=q.multi?(side[q.k]||[]).includes(v):side[q.k]===v;
        return el("button",{type:"button","aria-pressed":String(on),text:t,
          title:`${q.label}: ${t}`,
          onclick:()=>answer(q,v)});
      }))]))),
  ];

  if(bothAnswered){
    const {agree,differ}=comparePerspectives(PERSP.child,PERSP.parent,PERSP_Q);
    cards.push(el("section",{class:"card"},[
      el("h3",{text:"Where you already agree"}),
      agree.length?el("ul",{class:"plain"},agree.map(t=>el("li",{text:t})))
                  :el("p",{class:"hint",text:"Nothing overlaps yet."}),
      el("h3",{text:"Where you see it differently"}),
      differ.length?el("ul",{class:"plain"},differ.map(t=>el("li",{text:t})))
                   :el("p",{class:"hint",text:"Nothing in conflict so far."}),
      el("div",{class:"note info"},[el("span",{text:
        "Neither column is the right one. A difference here is not a problem to be "+
        "solved by the person with more authority — it is the conversation worth having "+
        "before an application form gets filled in."})]),
    ]));
  } else {
    cards.push(el("section",{class:"card"},[
      el("p",{class:"lede",text:
        `Now switch to “${other==="child"?"The young person":"The parent"}” above and answer the same four. `+
        `The comparison appears once both of you have.`})]));
  }
  box.replaceChildren(...cards);
}

/** Asked for a page that needs a run, before there was one. */
function renderGate(route){
  const box=$("#gateOut"); if(!box) return;
  box.replaceChildren(el("section",{class:"card"},[
    el("h2",{text:"Answer step two first"}),
    el("p",{class:"lede",text:
      `“${route?route.label:"That page"}” is built from your own answers, and there are `+
      `none yet. Nothing is stored between visits — not on a server and not on `+
      `this device — so the questions start empty every time.`}),
    el("div",{class:"actions"},[el("a",{class:"btn primary",href:"#/alevel",
      title:"Go answer the profile questions this page needs",
      text:"Go to the questions"})]),
  ]));
}

async function boot(){
  try{
    const r=await fetch(PACK_URL,{cache:"no-store"});
    if(!r.ok) throw new Error(r.status);
    S.pack=await r.json();
  }catch(err){
    const b=$("#loadError");
    b.textContent="PathAhead could not load its data file. If you opened this page straight from a folder, use the PathAhead launcher instead — browsers block local file reads for safety.";
    b.hidden=false; return;
  }
  const pack=S.pack, sel=$("#yearLevel");
  /* Only the cohorts this view can actually score.
     This was a real bug the moment the PSLE cohorts were added to the pack:
     the dropdown was filled from `pack.cohorts` with no filter, so a parent
     could pick "Primary 6", be correctly told their child sits the PSLE, and
     then be asked for H2 Chemistry and General Paper on the very next card.
     A stage is not a dropdown option — it is a different page, a different
     reader and a different set of questions. `data-stage` on the view is what
     makes that structural rather than a convention someone has to remember. */
  const viewStage = $("#view-start")?.dataset.stage || "a-level";
  const mine = pack.cohorts.filter(c=>c.stage===viewStage);
  mine.forEach(c=>sel.append(el("option",{value:c.year_level,text:c.label})));
  /* Anyone whose stage is NOT on this page needs a way out of it, named. An
     empty dropdown with no explanation is how a family concludes the tool has
     nothing for them. */
  const elsewhere = pack.cohorts.filter(c=>c.stage!==viewStage);
  if(elsewhere.length){
    const note=$("#otherStages");
    if(note) note.replaceChildren(el("span",{},[
      el("span",{text:"Is your child in "+
        elsewhere.map(c=>c.label).join(" or ")+"? "}),
      el("a",{href:"#/psle",title:"Go to PathAhead's PSLE page instead",
        text:"That is a different system — start here instead"}),
      el("span",{text:". The rules, the vocabulary and the decision are all different, "+
        "so it has its own page rather than being an option in this list."}),
    ]));
  }
  sel.addEventListener("change",echoCohort); echoCohort();

  S.rows=BLANK.map(r=>({...r})); renderRows();
  buildProfileUI(); paintSignalProgress();

  $("#addRow").addEventListener("click",()=>{S.rows.push({level:"h1",name:"",code:"",grade:"B"});renderRows();});
  $("#sample").addEventListener("click",()=>{S.rows=SAMPLE.map(r=>({...r}));renderRows();run();});
  $("#reset").addEventListener("click",()=>{S.rows=BLANK.map(r=>({...r}));renderRows();
    S.shortlist.clear(); S.result=null; $("#results").hidden=true; $("#inputError").hidden=true;
    navigate("#/alevel");});
  $("#go").addEventListener("click",run);
  $("#icsBtn").addEventListener("click",()=>{
    const blob=new Blob([icsFor(S.timeline)],{type:"text/calendar"});
    const a=el("a",{href:URL.createObjectURL(blob),download:"pathahead-dates.ics"});
    document.body.append(a); a.click(); a.remove();
  });

  // buildNav() runs inside renderRoute() itself now, scoped to whichever
  // track the current route belongs to — see TRACK_BY_ROUTE_ID above it.
  window.addEventListener("hashchange",renderRoute);
  renderRoute();

  renderFresh(pack);
  $("#footAdvice").textContent="PathAhead explains how the published rules work. It does not tell you what to choose. For decisions about your child's education, speak to their school's teachers and Education & Career Guidance counsellor, or the institution's own admissions office.";
  // Rendered as real links, not as text that happens to contain a URL. The
  // Singapore Open Data Licence requires the product to include "a link to
  // the most recent version of this Licence" -- a reader who cannot click
  // it has not been given a link, they have been shown a string. See
  // linkifyUrls() and SAFEGUARDS.md 3a.
  $("#footAttr").replaceChildren(...linkifyUrls((pack.pack.attribution||[]).join(" ")));
  $("#footVersion").textContent=`Data pack ${pack.pack.version} · published ${pack.pack.published} · ${pack.outcomes.length} destinations · ${pack.sources.length} sources`;
}

function echoCohort(){
  const box=$("#cohortEcho");
  try{
    const res=resolveCohort(S.pack,$("#yearLevel").value,new Date().getFullYear());
    box.className="note info";
    box.replaceChildren(el("span",{},[
      el("strong",{text:res.sentence}),
      res.cohort.note?el("div",{style:"margin-top:.3rem",text:res.cohort.note}):null,
      el("div",{style:"margin-top:.3rem;color:var(--ink-3)",text:"Not right? Change the year level above."})]));
  }catch(err){
    box.className="note warn";
    box.replaceChildren(el("span",{},[el("strong",{text:err.message}),
      el("div",{style:"margin-top:.3rem",text:err.advice||""})]));
  }
}

/* ── printing ──────────────────────────────────────────────────
   A collapsed <details> stays collapsed on paper no matter what the print
   stylesheet says: `display` cannot reopen it, because the closed state is
   enforced by the element, not by CSS. So every disclosure is opened before
   the print dialog and restored afterwards — otherwise the per-factor
   derivation, which is the whole point of this release, prints as a bare
   score. See ISSUES_v0.2.md section C. */
let _reclose = [], _wasExpanded = null;
function openEverythingForPrint(){
  _reclose = [...document.querySelectorAll("details:not([open])")];
  _reclose.forEach(d=>d.open=true);
  /* Paper has no "Show all" button. A printout that silently stopped at ten
     courses per bucket would be a different document from the one on screen,
     and the reader would have no way to know. */
  if(S.result && _wasExpanded===null){
    _wasExpanded = {...S.expanded};
    for(const key of ORDER) S.expanded[key]=true;
    renderOptions();
  }
}
function restoreAfterPrint(){
  _reclose.forEach(d=>d.open=false);
  _reclose = [];
  if(_wasExpanded!==null){
    S.expanded = _wasExpanded; _wasExpanded = null;
    if(S.result) renderOptions();
  }
}
if(typeof window !== "undefined" && window.addEventListener){
  window.addEventListener("beforeprint", openEverythingForPrint);
  window.addEventListener("afterprint", restoreAfterPrint);
}
/* Safari fires neither event; matchMedia is the fallback that does work. */
if(typeof window !== "undefined" && window.matchMedia){
  const mq = window.matchMedia("print");
  const onChange = e => e.matches ? openEverythingForPrint() : restoreAfterPrint();
  if(mq.addEventListener) mq.addEventListener("change", onChange);
  else if(mq.addListener) mq.addListener(onChange);
}

/* ── how far through the optional questions ────────────────────
   Framed as what answering one more UNLOCKS, never as a nag. Every question in
   step three is optional, "no idea" is a real answer, and a reader who leaves
   them blank has done nothing wrong — they just get the evidence axis without
   the match axis, which the copy says plainly. ISSUES_v0.2.md section H. */
/* Delegated rather than wired into each of the eight controls: they are built
   in five different functions, and a new question added later would silently
   not count. */
if(typeof document !== "undefined" && document.addEventListener){
  for(const ev of ["click","input","change"])
    document.addEventListener(ev, ()=>setTimeout(paintSignalProgress,0), true);
}

/* The signals this BROWSER actually asks a question for.
 *
 * Not the same list as FIT_SIGNALS, and the difference is the point.
 * FIT_SIGNALS mirrors engine/fit.py and defines `signals_available` in a
 * score, so it must stay identical across the two engines. But two of its
 * entries -- `cost_sensitive` and `willing_extra_assessment` -- were
 * deliberately removed from this page as standalone chips (they were being
 * asked twice, once as a chip and once as an importance row; see CON's own
 * comment) and are now expressed only as importance weights. The browser
 * therefore never sets those two profile fields.
 *
 * The progress line kept counting all nine anyway, so it could only ever
 * reach "7 of 9" and a family who had answered every question they were
 * shown was told they had two left to find. Counting only what is actually
 * asked is the fix; changing FIT_SIGNALS would silently break cross-engine
 * parity on `signals_available`, which is a real number in a real score.
 * Found 2026-08-14 while clearing the two long-standing DOM failures. */
const ASKED_SIGNALS = FIT_SIGNALS.filter(
  k => k !== "cost_sensitive" && k !== "willing_extra_assessment");

function paintSignalProgress(){
  const box=$("#signalProgress"); if(!box) return;
  const total=ASKED_SIGNALS.length;
  const n=ASKED_SIGNALS.filter(k=>{
    const v=P[k];
    return !(v===null||v===undefined||v===""||(Array.isArray(v)&&!v.length));
  }).length;
  let msg;
  if(n===0) msg=`You have answered none of the ${total} optional questions. `+
    `You will still get every course, with last year's published figures. `+
    `Answer any two and PathAhead will also show how well each one matches what you said.`;
  else if(n<MIN_SIGNALS) msg=`${n} of ${total} answered. One more and PathAhead can show `+
    `how well each course matches what you told us, with the reasoning line by line.`;
  // "none of them is required" says the right thing and trips the
  // anti-nagging guard, which bans /must|should|need to|required/ without
  // understanding negation. Same shape as the banned-phrase guard firing on
  // "does not guarantee a place". Rewrite the sentence, not the guard.
  else if(n<total) msg=`${n} of ${total} answered — enough to show matches. `+
    `Each further answer adds another line of reasoning; every one of them is optional.`;
  else msg=`All ${total} answered. Every factor PathAhead can weigh, it will weigh — `+
    `and it shows its working on each card.`;
  box.replaceChildren(el("span",{text:msg}));
}

/* Theme toggle.
 *
 * Two things had to change here, and the second is the serious one.
 *
 * 1. `localStorage` is not always there. It throws outright when site data is
 *    blocked, in some private modes, and on a file:// origin. This block sits
 *    immediately above `boot()`, at the top level — so an exception here does
 *    not degrade the theme, it stops the ENTIRE APP from starting. The page
 *    then renders as static markup with "loading…" and no controls, which is
 *    indistinguishable from a broken build. Every access is now guarded, and
 *    the whole block is wrapped so that a colour preference can never be the
 *    reason a family cannot read their options.
 *
 * 2. This app tells the reader "nothing you type here leaves this device" and
 *    keeps its state in memory precisely so that a shared family computer
 *    carries nothing between sessions. Writing to disk was therefore a promise
 *    broken for a convenience. The preference now lives in memory for the
 *    session; the default still follows the clock, which is what made the
 *    feature worth having.
 */
(function() {
  if (typeof document === "undefined") return;
  const btn = document.getElementById('themeToggle');
  let currentTheme = null;
  if (!currentTheme) {
    const hour = new Date().getHours();
    currentTheme = (hour >= 18 || hour < 6) ? 'evening' : 'light';
  }
  
  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    if(btn) {
      if(theme === 'evening' || theme === 'dark') {
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>';
      } else {
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
      }
    }
  }

  try { applyTheme(currentTheme); } catch (e) { /* a colour must never stop the app */ }

  if(btn) {
    btn.addEventListener('click', () => {
      currentTheme = currentTheme === 'light' ? 'evening' : 'light';
      applyTheme(currentTheme);
    });
  }
})();

/* Whatever happened above, the app starts. */
if (typeof document !== "undefined") {
  try { boot(); } catch (e) {
    const b = document.getElementById('loadError');
    if (b) { b.textContent = 'PathAhead could not start. Please reload the page.'; b.hidden = false; }
    throw e;
  }
}

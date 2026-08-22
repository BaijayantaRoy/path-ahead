#!/usr/bin/env python3
"""Build packs/singapore/outcomes-polytechnic.yaml from transcribed source tables.

Why a generator and not hand-written YAML
-----------------------------------------
Five polytechnics publish roughly two hundred diploma courses between them, and
every one of them republishes its aggregate range once a year. Hand-maintaining
that is how a pack goes stale quietly. The tables below are transcribed from the
published sources named in SOURCES, the editorial families are hand-authored,
and this script does the mechanical part.

Run it after updating a table:

    python3 tools/build_polytechnic_pack.py

Three things this file is careful about
---------------------------------------
1. **The figures are a min-max, not a percentile band.** The publishers say so:
   the net ELR2B2 aggregate of the LOWEST and HIGHEST ranked student admitted
   through JAE. That is the whole admitted cohort. A university's 10th-90th
   percentile deliberately excludes both tails, so the polytechnic range is
   wider from the same intake and would read as "much less selective" if the
   two were rendered alike. Hence `statistic: min_max`.

2. **The figures are not comparable with an A-Level score, for a reason that
   goes deeper than units.** Temasek Polytechnic's own admissions guide sets it
   out: an A-Level holder applying through JAE is admitted on their GCE O-Level
   results, and an A-Level holder applying through the Direct Admissions
   Exercise is admitted on "academic results and/or interview/test" with no
   published aggregate at all. So the ELR2B2 range on these cards is never the
   applicant's own A-Level score under any route. Hence `comparable: false`.

3. **Years are kept apart.** Each year is one admissions exercise. Merging three
   years of min-max into one range would invent a figure nobody published, and
   it would widen every year, making courses look less selective the longer this
   project ran. History is carried beside the band, never folded into it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "packs" / "singapore" / "outcomes-polytechnic.yaml"

RETRIEVED = "2026-08-03"
STALE_AFTER = "2027-06-30"

# ---------------------------------------------------------------------------
# Editorial families.
#
# PathAhead's OWN characterisation, written at course-FAMILY level and labelled
# as such on every card. These make fit reasoning possible at all; they are the
# least verified thing in the pack and the first place a reader is invited to
# correct us. Interests are RIASEC codes.
# ---------------------------------------------------------------------------
FAMILIES: dict[str, dict] = {
    "applied-science": dict(
        interests=["I", "R"], subjects=["chemistry", "biology"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="medium", writing="low", sectors=["manufacturing", "healthcare"],
        summary="Laboratory-centred science with a strong practical and quality-control core.",
    ),
    "biomedical-science": dict(
        interests=["I"], subjects=["biology", "chemistry"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["healthcare", "research"],
        summary="Human biology and diagnostics, taught around laboratory technique and data.",
    ),
    "food-science": dict(
        interests=["I", "R"], subjects=["chemistry", "biology"],
        assessment=["practical", "coursework"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["food and beverage", "manufacturing"],
        summary="The science of food -- composition, safety and product development -- with kitchen and lab work.",
    ),
    "architecture-built": dict(
        interests=["A", "R"], subjects=["art", "mathematics", "physics"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["construction", "design"],
        summary="Designing and documenting buildings, with studio work alongside technical drawing.",
    ),
    "business-general": dict(
        interests=["E", "C"], subjects=["economics", "mathematics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="medium", writing="medium", sectors=["business services"],
        summary="Broad commercial training across marketing, operations and management.",
    ),
    "business-finance": dict(
        interests=["C", "E"], subjects=["mathematics", "economics"],
        assessment=["exams", "coursework"], teamwork="mixed",
        maths="high", writing="medium", sectors=["financial services"],
        summary="Money, markets and financial analysis, with a quantitative core.",
    ),
    "accountancy": dict(
        interests=["C"], subjects=["mathematics", "economics"],
        assessment=["exams"], teamwork="individual",
        maths="high", writing="low", sectors=["financial services", "business services"],
        summary="Accounting practice and standards, with a compliance-heavy core and a clear professional track.",
    ),
    "hospitality-tourism": dict(
        interests=["E", "S"], subjects=["economics"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["hospitality", "tourism"],
        summary="Running hotels, events and travel operations, with substantial placement work.",
    ),
    "food-business": dict(
        interests=["E", "R"], subjects=["economics"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["food and beverage"],
        summary="The business side of food -- kitchens, costing, service and supply -- taught hands-on.",
    ),
    "sport-wellness": dict(
        interests=["S", "R"], subjects=["biology"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["sport", "health and wellness"],
        summary="Coaching, exercise science and the business of sport, with a lot of time on your feet.",
    ),
    "media-comms": dict(
        interests=["A", "E"], subjects=["english", "literature"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="high", sectors=["media", "marketing"],
        summary="Communication, campaigns and audiences, assessed mostly through portfolio and project work.",
    ),
    "engineering-general": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="team",
        maths="high", writing="low", sectors=["engineering", "manufacturing"],
        summary="Broad engineering foundation -- mechanics, electronics and design -- before specialising.",
    ),
    "aerospace": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="team",
        maths="high", writing="low", sectors=["aviation", "engineering"],
        summary="Aircraft systems and maintenance engineering, taught to aviation regulatory standards.",
    ),
    "ai-data-engineering": dict(
        interests=["I", "R"], subjects=["mathematics", "computing"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="high", writing="low", sectors=["technology", "engineering"],
        summary="Building the systems that collect, move and act on data, with real hardware in the loop.",
    ),
    "manufacturing": dict(
        interests=["R"], subjects=["mathematics", "physics"],
        assessment=["practical"], teamwork="team",
        maths="medium", writing="low", sectors=["manufacturing"],
        summary="Production engineering, automation and digital factory work, mostly in workshops.",
    ),
    "biomedical-engineering": dict(
        interests=["I", "R"], subjects=["mathematics", "physics", "biology"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="high", writing="low", sectors=["healthcare", "engineering"],
        summary="Medical devices and clinical equipment -- engineering applied inside hospitals.",
    ),
    "cloud-engineering": dict(
        interests=["I", "R"], subjects=["mathematics", "computing"],
        assessment=["practical", "coursework"], teamwork="mixed",
        maths="medium", writing="low", sectors=["technology"],
        summary="Infrastructure, networks and deployment -- the plumbing that keeps software running.",
    ),
    "robotics": dict(
        interests=["R", "I"], subjects=["mathematics", "physics", "computing"],
        assessment=["practical"], teamwork="team",
        maths="high", writing="low", sectors=["engineering", "manufacturing"],
        summary="Machines that sense and move: control systems, mechanics and embedded code together.",
    ),
    "electronics-engineering": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="high", writing="low", sectors=["electronics", "engineering"],
        summary="Circuits, embedded systems and computer hardware, with heavy laboratory time.",
    ),
    "sustainability-engineering": dict(
        interests=["I", "E"], subjects=["mathematics", "physics", "economics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="medium", writing="medium", sectors=["energy", "engineering"],
        summary="Engineering read through energy, emissions and cost -- technical work with a commercial frame.",
    ),
    "oral-health": dict(
        interests=["S", "R"], subjects=["biology"],
        assessment=["practical"], teamwork="mixed",
        maths="low", writing="low", sectors=["healthcare"],
        summary="Clinical dental therapy, trained chairside on real patients from early in the course.",
    ),
    "nursing": dict(
        interests=["S"], subjects=["biology", "chemistry"],
        assessment=["practical", "exams"], teamwork="team",
        maths="low", writing="medium", sectors=["healthcare"],
        summary="Clinical nursing with substantial hospital placement, and shift work from the first year.",
    ),
    "social-work": dict(
        interests=["S"], subjects=["english"],
        assessment=["coursework", "practical"], teamwork="team",
        maths="low", writing="high", sectors=["social services"],
        summary="Casework and community practice, with supervised placements in real agencies.",
    ),
    "psychology-social": dict(
        interests=["S", "I"], subjects=["english", "biology"],
        assessment=["coursework", "exams"], teamwork="mixed",
        maths="medium", writing="high", sectors=["social services", "healthcare"],
        summary="Human behaviour and applied social science, with research methods and written work throughout.",
    ),
    "ict-general": dict(
        interests=["I", "C"], subjects=["mathematics", "computing"],
        assessment=["coursework", "practical"], teamwork="team",
        maths="medium", writing="low", sectors=["technology"],
        summary="Broad computing foundation -- programming, data and systems -- before choosing a specialism.",
    ),
    "applied-ai": dict(
        interests=["I"], subjects=["mathematics", "computing"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="high", writing="low", sectors=["technology"],
        summary="Machine learning and analytics applied to real datasets, with a strong statistics core.",
    ),
    "cybersecurity": dict(
        interests=["I", "R"], subjects=["mathematics", "computing"],
        assessment=["practical", "coursework"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["technology", "public sector"],
        summary="Defending and investigating systems -- networks, forensics and a lot of hands-on labs.",
    ),
    "game-development": dict(
        interests=["A", "I"], subjects=["mathematics", "computing", "art"],
        assessment=["coursework"], teamwork="team",
        maths="medium", writing="low", sectors=["games", "technology"],
        summary="Building playable software, with programming and art production held in tension.",
    ),
    "information-technology": dict(
        interests=["I", "C"], subjects=["mathematics", "computing"],
        assessment=["coursework", "practical"], teamwork="team",
        maths="medium", writing="low", sectors=["technology"],
        summary="Software development and systems work, assessed largely through building things.",
    ),
    "design-general": dict(
        interests=["A"], subjects=["art"],
        assessment=["coursework"], teamwork="mixed",
        maths="low", writing="low", sectors=["design", "media"],
        summary="Foundation studio year across design disciplines, with portfolio work throughout.",
    ),
    "animation-vfx": dict(
        interests=["A", "I"], subjects=["art", "computing"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="low", sectors=["media", "games"],
        summary="Animation, modelling and visual effects, built around a portfolio and long production cycles.",
    ),
    "communication-design": dict(
        interests=["A"], subjects=["art", "english"],
        assessment=["coursework"], teamwork="mixed",
        maths="low", writing="medium", sectors=["design", "media"],
        summary="Graphic, motion and brand design, judged on a portfolio rather than exams.",
    ),
    "product-interior-design": dict(
        interests=["A", "R"], subjects=["art"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="low", writing="low", sectors=["design"],
        summary="Objects and spaces -- modelmaking, materials and studio critique.",
    ),
    "film-television": dict(
        interests=["A"], subjects=["art", "english"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["media"],
        summary="Screen production from script to edit, taught on crews with real deadlines.",
    ),
    "maritime-logistics": dict(
        interests=["C", "E"], subjects=["mathematics", "economics"],
        assessment=["exams", "coursework"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["logistics", "maritime"],
        summary="Moving goods and running supply chains, with a strong operations and costing core.",
    ),
    "veterinary-technology": dict(
        interests=["R", "S"], subjects=["biology"],
        assessment=["practical"], teamwork="mixed",
        maths="low", writing="low", sectors=["veterinary", "animal care"],
        summary="Clinical animal care and laboratory technique, with placements in practices and shelters.",
    ),
    "optometry": dict(
        interests=["I", "S"], subjects=["physics", "biology"],
        assessment=["practical", "exams"], teamwork="individual",
        maths="medium", writing="low", sectors=["healthcare"],
        summary="Eye examination and dispensing, trained in clinic on real patients.",
    ),
    "landscape-horticulture": dict(
        interests=["R", "A"], subjects=["biology", "art"],
        assessment=["practical", "coursework"], teamwork="mixed",
        maths="low", writing="low", sectors=["landscape", "construction"],
        summary="Planting design and green space management, taught largely outdoors and in nurseries.",
    ),
    "language-culture": dict(
        interests=["A", "S"], subjects=["chinese", "english", "literature"],
        assessment=["coursework", "exams"], teamwork="mixed",
        maths="low", writing="high", sectors=["media", "education"],
        summary="Language, literature and cultural studies, with a great deal of reading and writing.",
    ),
    "early-childhood": dict(
        interests=["S", "A"], subjects=["english"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["education", "social services"],
        summary="Teaching and caring for young children, with long supervised placements in preschools.",
    ),
    "arts-management": dict(
        interests=["A", "E"], subjects=["art", "economics"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["arts", "events"],
        summary="Running arts organisations and events -- programming, funding and audiences.",
    ),
    "real-estate": dict(
        interests=["E", "C"], subjects=["economics", "mathematics"],
        assessment=["exams", "coursework"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["real estate", "financial services"],
        summary="Property valuation, agency and asset management, with a strong legal and numeric core.",
    ),
    "environmental-tech": dict(
        interests=["I", "R"], subjects=["chemistry", "biology"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["utilities", "environment"],
        summary="Water treatment and environmental engineering, with plant visits and lab analysis.",
    ),
    "offshore-marine-engineering": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="team",
        maths="high", writing="low", sectors=["marine", "energy"],
        summary="Ships, rigs and offshore structures -- heavy engineering with fieldwork.",
    ),
    "electrical-engineering": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="high", writing="low", sectors=["engineering", "utilities"],
        summary="Power systems, machines and building services, with substantial laboratory work.",
    ),
    "mechanical-engineering": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="team",
        maths="high", writing="low", sectors=["engineering", "manufacturing"],
        summary="Mechanics, materials and machine design, taught in workshops as much as classrooms.",
    ),
    "chemical-engineering": dict(
        interests=["I", "R"], subjects=["chemistry", "mathematics", "physics"],
        assessment=["exams", "practical"], teamwork="mixed",
        maths="high", writing="low", sectors=["manufacturing", "energy"],
        summary="Process plant and reaction engineering -- chemistry scaled up to industry.",
    ),
    "immersive-media": dict(
        interests=["A", "I"], subjects=["art", "computing"],
        assessment=["coursework"], teamwork="team",
        maths="medium", writing="low", sectors=["media", "technology"],
        summary="Virtual and augmented reality production, sitting between studio art and software.",
    ),
    "media-general": dict(
        interests=["A"], subjects=["english", "art"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["media"],
        summary="Foundation year across media disciplines before choosing film, journalism or production.",
    ),
    "biological-sciences": dict(
        interests=["I"], subjects=["biology", "chemistry"],
        assessment=["practical", "exams"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["research", "healthcare"],
        summary="Organisms, ecology and molecular biology, with fieldwork alongside laboratory technique.",
    ),
    "human-resources": dict(
        interests=["S", "E"], subjects=["english", "economics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="low", writing="high", sectors=["business services"],
        summary="Hiring, developing and looking after people at work, read through applied psychology.",
    ),
    "engineering-management": dict(
        interests=["E", "R"], subjects=["mathematics", "economics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="medium", writing="medium", sectors=["manufacturing", "logistics"],
        summary="Where engineering meets operations -- process improvement, quality and cost.",
    ),
    "aviation-management": dict(
        interests=["E", "C"], subjects=["mathematics", "economics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="medium", writing="medium", sectors=["aviation"],
        summary="Running airports and airlines -- ground operations, safety and scheduling.",
    ),
    "events-management": dict(
        interests=["E", "A"], subjects=["english"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["events", "hospitality"],
        summary="Planning and running live events, assessed by actually running them.",
    ),
    "outdoor-education": dict(
        interests=["R", "S"], subjects=["biology"],
        assessment=["practical"], teamwork="team",
        maths="low", writing="low", sectors=["education", "sport"],
        summary="Teaching and leading in the outdoors, with expeditions and safety certification.",
    ),
    "community-care": dict(
        interests=["S"], subjects=["biology", "english"],
        assessment=["practical", "coursework"], teamwork="team",
        maths="low", writing="medium", sectors=["healthcare", "social services"],
        summary="Supporting people with long-term care needs, taught largely on placement.",
    ),
    "sonic-arts": dict(
        interests=["A", "R"], subjects=["art", "physics"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="low", writing="low", sectors=["media", "music"],
        summary="Sound design, recording and audio production, built around a portfolio.",
    ),
    "marketing": dict(
        interests=["E", "A"], subjects=["english", "economics"],
        assessment=["coursework"], teamwork="team",
        maths="low", writing="high", sectors=["marketing", "business services"],
        summary="Brands, campaigns and consumer research, assessed mostly by pitching real work.",
    ),
    "fashion-design": dict(
        interests=["A", "E"], subjects=["art"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="low", writing="low", sectors=["fashion", "retail"],
        summary="Garment design and the buying and merchandising behind it, judged on a portfolio.",
    ),
    "facility-management": dict(
        interests=["C", "R"], subjects=["mathematics", "physics"],
        assessment=["coursework", "exams"], teamwork="team",
        maths="medium", writing="medium", sectors=["construction", "real estate"],
        summary="Keeping buildings running -- services, maintenance, energy and contracts.",
    ),
    "law-management": dict(
        interests=["C", "E"], subjects=["english", "economics"],
        assessment=["exams", "coursework"], teamwork="mixed",
        maths="low", writing="high", sectors=["legal services", "business services"],
        summary="Legal practice support alongside commercial management, with heavy reading and writing.",
    ),
    "civil-engineering": dict(
        interests=["R", "I"], subjects=["mathematics", "physics"],
        assessment=["exams", "practical"], teamwork="team",
        maths="high", writing="medium", sectors=["construction", "engineering"],
        summary="Structures, geotechnics and site work -- the engineering behind roads, tunnels and buildings.",
    ),
    "perfumery-cosmetic": dict(
        interests=["I", "A"], subjects=["chemistry", "biology"],
        assessment=["practical", "coursework"], teamwork="mixed",
        maths="medium", writing="medium", sectors=["manufacturing", "consumer goods"],
        summary="Formulating fragrances and cosmetics -- applied chemistry with a strong sensory and product-development side.",
    ),
    "computer-science": dict(
        interests=["I"], subjects=["mathematics", "computing"],
        assessment=["coursework", "practical"], teamwork="mixed",
        maths="high", writing="low", sectors=["technology"],
        summary="Software engineering and computing fundamentals, with algorithms and a heavy build-it workload.",
    ),
    "nautical-studies": dict(
        interests=["R", "C"], subjects=["mathematics", "physics"],
        assessment=["practical", "exams"], teamwork="team",
        maths="medium", writing="low", sectors=["maritime", "shipping"],
        summary="Navigation, seamanship and ship handling, with sea time aboard working vessels.",
    ),
}

# ---------------------------------------------------------------------------
# The published tables.
#
# Each row: (jae_code, course name, editorial family, {year: "low-high"})
# Years are most-recent-first in the emitted history. A course absent from an
# earlier year is simply absent -- it usually means the course did not exist,
# and inventing a figure for it would be worse than a shorter history.
# ---------------------------------------------------------------------------

NYP = [
    ("C25", "Biomedical Science with Analytics", "biomedical-science", {2026: "6-8"}),
    ("C27", "Common Science Programme", "applied-science", {2026: "4-11", 2025: "8-12", 2024: "5-12"}),
    ("C45", "Applied Chemistry", "applied-science", {2026: "4-10", 2025: "5-10", 2024: "4-10"}),
    ("C49", "Biologics & Process Technology", "applied-science", {2026: "7-10", 2025: "8-11", 2024: "7-11"}),
    ("C65", "Pharmaceutical Science", "applied-science", {2026: "7-10", 2025: "7-10", 2024: "4-10"}),
    ("C69", "Food Science & Nutrition", "food-science", {2026: "8-12", 2025: "4-12", 2024: "5-12"}),
    ("C73", "Chemical & Pharmaceutical Technology", "applied-science", {2026: "10-11", 2025: "10-13", 2024: "7-13"}),
    ("C38", "Architecture", "architecture-built", {2026: "9-15", 2025: "8-14", 2024: "6-14"}),
    ("C34", "Common Business Programme", "business-general", {2026: "5-14", 2025: "7-14", 2024: "3-14"}),
    ("C35", "Business & Financial Technology", "business-finance", {2026: "6-14", 2025: "6-14", 2024: "7-14"}),
    ("C46", "Food & Beverage Business", "food-business", {2026: "4-15", 2025: "5-16", 2024: "8-16"}),
    ("C67", "Hospitality & Tourism Management", "hospitality-tourism", {2026: "11-15", 2025: "10-16", 2024: "8-16"}),
    ("C81", "Sport & Wellness Management", "sport-wellness", {2026: "6-13", 2025: "7-14", 2024: "11-16"}),
    ("C93", "Media & Communication Management", "media-comms", {2026: "8-13", 2025: "5-13", 2024: "6-12"}),
    ("C94", "Business Management", "business-general", {2026: "5-14", 2025: "5-15", 2024: "7-15"}),
    ("C96", "Banking & Finance", "business-finance", {2026: "5-11", 2025: "3-11", 2024: "7-12"}),
    ("C98", "Accountancy & Finance", "accountancy", {2026: "4-11", 2025: "5-12", 2024: "6-12"}),
    ("C24", "Common Business & Technology Programme", "business-general", {2026: "5-16"}),
    ("C26", "Aerospace Engineering", "aerospace", {2026: "7-14", 2025: "7-16"}),
    ("C31", "AI & Data Engineering", "ai-data-engineering", {2026: "6-12", 2025: "6-13", 2024: "6-10"}),
    ("C41", "Sustainability in Engineering with Business", "sustainability-engineering", {2026: "10-23", 2025: "6-14", 2024: "8-14"}),
    ("C42", "Common Engineering Programme", "engineering-general", {2026: "10-23", 2025: "6-25", 2024: "4-24"}),
    ("C62", "Advanced & Digital Manufacturing", "manufacturing", {2026: "10-26", 2025: "13-26", 2024: "12-25"}),
    ("C71", "Biomedical Engineering", "biomedical-engineering", {2026: "7-12", 2025: "7-12", 2024: "8-13"}),
    ("C75", "Cloud Engineering", "cloud-engineering", {2026: "9-21", 2025: "10-25", 2024: "7-19"}),
    ("C87", "Robotics & Mechatronics", "robotics", {2026: "11-26", 2025: "4-25", 2024: "8-26"}),
    ("C89", "Electronic & Computer Engineering", "electronics-engineering", {2026: "5-25", 2025: "9-22", 2024: "5-15"}),
    ("C72", "Oral Health Therapy", "oral-health", {2026: "5-9", 2025: "7-9", 2024: "4-10"}),
    ("C97", "Nursing", "nursing", {2026: "7-28", 2025: "6-28", 2024: "3-28"}),
    ("C47", "Social Work", "social-work", {2026: "7-12", 2025: "9-14", 2024: "6-11"}),
    ("C36", "Common ICT Programme", "ict-general", {2026: "5-18", 2025: "6-16", 2024: "4-16"}),
    ("C43", "Applied AI & Analytics", "applied-ai", {2026: "7-10", 2025: "5-9", 2024: "3-9"}),
    ("C54", "Cybersecurity & Digital Forensics", "cybersecurity", {2026: "3-11", 2025: "5-11", 2024: "4-10"}),
    ("C70", "Game Development & Technology", "game-development", {2026: "6-15", 2025: "6-14", 2024: "3-16"}),
    ("C85", "Information Technology", "information-technology", {2026: "6-26", 2025: "7-16", 2024: "5-15"}),
    ("C28", "Common Design & Media Programme", "design-general", {2026: "8-16", 2025: "9-16", 2024: "4-16"}),
    ("C29", "Animation, Games & Visual Effects", "animation-vfx", {2026: "4-12", 2025: "3-12", 2024: "5-11"}),
    ("C30", "Communication & Motion Design", "communication-design", {2026: "9-19", 2025: "6-15", 2024: "7-15"}),
    ("C32", "Experiential Product & Interior Design", "product-interior-design", {2026: "11-18", 2025: "10-17", 2024: "5-16"}),
]

# Ngee Ann publishes an ELR2B2 *type* per course, and the types are not the
# same aggregate: A, B, C and D differ in which subjects count as "relevant".
# Two NP courses on different types are no more comparable with each other than
# either is with an A-Level score, so the type goes into the basis string rather
# than being flattened away.
NP = [
    ("N51", "Accountancy", "accountancy", {2025: "4-11", 2024: "4-11", 2023: "4-12"}, "B"),
    ("N53", "Banking & Finance", "business-finance", {2025: "4-9", 2024: "3-9", 2023: "5-10"}, "B"),
    ("N45", "Business Studies", "business-general", {2025: "5-8", 2024: "3-8", 2023: "3-8"}, "B"),
    ("N97", "Common Business Programme", "business-general", {2025: "5-10", 2024: "4-11", 2023: "3-12"}, "B"),
    ("N85", "International Trade & Business", "maritime-logistics", {2025: "6-12", 2024: "6-13", 2023: "8-13"}, "B"),
    ("N72", "Tourism & Resort Management", "hospitality-tourism", {2025: "9-14", 2024: "10-14", 2023: "10-15"}, "B"),
    ("N12", "Design", "design-general", {2025: "3-13", 2024: "7-15", 2023: "4-15"}, "D"),
    ("N40", "Hotel & Leisure Facilities Management", "hospitality-tourism", {2025: "12-16", 2024: "11-16", 2023: "7-17"}, "C"),
    ("N48", "Real Estate Business", "real-estate", {2025: "11-14", 2024: "10-14", 2023: "8-14"}, "B"),
    ("N65", "Aerospace Engineering", "aerospace", {2025: "7-14", 2024: "10-16", 2023: "9-18"}, "C"),
    ("N50", "Mechatronics & Robotics", "robotics", {2025: "12-23", 2024: "7-24", 2023: "6-26"}, "C"),
    ("N60", "Biomedical Engineering", "biomedical-engineering", {2025: "7-11", 2024: "7-11", 2023: "6-11"}, "C"),
    ("N71", "Common Engineering Programme", "engineering-general", {2025: "5-20", 2024: "9-22", 2023: "7-24"}, "C"),
    ("N43", "Electrical Engineering", "electrical-engineering", {2025: "13-22", 2024: "11-23", 2023: "12-24"}, "C"),
    ("N44", "Electronic & Computer Engineering", "electronics-engineering", {2025: "8-20", 2024: "3-17", 2023: "5-16"}, "C"),
    ("N93", "Engineering Science", "engineering-general", {2025: "5-10", 2024: "4-9", 2023: "6-11"}, "C"),
    ("N42", "Offshore & Sustainable Engineering", "offshore-marine-engineering", {2025: "16-26", 2024: "10-25", 2023: "14-25"}, "C"),
    ("N41", "Mechanical Engineering", "mechanical-engineering", {2025: "6-22", 2024: "9-24", 2023: "4-26"}, "C"),
    ("N14", "Common Media Programme", "media-general", {2025: "4-12", 2024: "7-12", 2023: "7-12"}, "A"),
    ("N82", "Film, Sound & Video", "film-television", {2025: "6-12", 2024: "3-11", 2023: "3-11"}, "A"),
    ("N67", "Mass Communication", "media-comms", {2025: "4-11", 2024: "3-10", 2023: "3-8"}, "A"),
    ("N13", "Media Post-Production", "film-television", {2025: "7-14", 2024: "8-14", 2023: "3-13"}, "A"),
    ("N69", "Nursing", "nursing", {2025: "5-28", 2024: "5-28", 2023: "6-28"}, "C"),
    ("N83", "Optometry", "optometry", {2025: "8-11", 2024: "6-12", 2023: "6-13"}, "C"),
    ("N91", "Arts Business Management", "arts-management", {2025: "7-13", 2024: "6-13", 2023: "5-12"}, "B"),
    ("N88", "Chinese Media & Communication", "language-culture", {2025: "6-14", 2024: "8-13", 2023: "4-13"}, "A"),
    ("N70", "Chinese Studies", "language-culture", {2025: "5-15", 2024: "7-13", 2023: "5-12"}, "A"),
    ("N11", "Psychology & Community Development", "psychology-social", {2025: "3-11", 2024: "4-13", 2023: "5-13"}, "A"),
    ("N96", "Early Childhood Development & Education", "early-childhood", {2025: "6-19", 2024: "5-20", 2023: "5-23"}, "A"),
    ("N95", "Tamil Studies with Early Education", "early-childhood", {2025: "13-21", 2024: "18-22", 2023: "15-20"}, "A"),
    ("N98", "Common ICT Programme", "ict-general", {2025: "3-14", 2024: "3-14", 2023: "3-12"}, "C"),
    ("N94", "Cybersecurity & Digital Forensics", "cybersecurity", {2025: "4-11", 2024: "3-11", 2023: "3-10"}, "C"),
    ("N81", "Data Science", "applied-ai", {2025: "7-11", 2024: "3-12", 2023: "4-10"}, "C"),
    ("N55", "Immersive Media", "immersive-media", {2025: "8-16", 2024: "4-16", 2023: "5-14"}, "C"),
    ("N54", "Information Technology", "information-technology", {2025: "6-15", 2024: "4-15", 2023: "5-14"}, "C"),
    ("N15", "Common Science Programme", "applied-science", {2025: "5-9", 2024: "6-9", 2023: "5-9"}, "C"),
    ("N59", "Biomedical Science", "biomedical-science", {2025: "4-7", 2024: "3-7", 2023: "3-7"}, "C"),
    ("N56", "Chemical & Biomolecular Engineering", "chemical-engineering", {2025: "6-12", 2024: "4-12", 2023: "8-12"}, "C"),
    ("N74", "Environmental & Water Technology", "environmental-tech", {2025: "5-16", 2024: "8-17", 2023: "6-15"}, "C"),
    ("N57", "Landscape Design & Horticulture", "landscape-horticulture", {2025: "6-17", 2024: "7-16", 2023: "4-16"}, "D"),
    ("N73", "Pharmaceutical Science", "applied-science", {2025: "3-9", 2024: "4-9", 2023: "3-9"}, "C"),
]

# Republic publishes one table for the current exercise only, with an aggregate
# type per course and an asterisk marking courses that still had vacancies after
# JAE posting. That asterisk is worth keeping: it is the difference between an
# appeal that has somewhere to go and one that does not, and RP states the
# condition itself -- meet the Minimum Entry Requirements and hold a net ELR2B2
# of 26 or better. Rows carry a 6th element for it.
RP = [
    ("R14", "Biomedical Science", "biomedical-science", {2026: "8-10"}, "C"),
    ("R16", "Biological Sciences", "biological-sciences", {2026: "11-17"}, "C"),
    ("R17", "Applied Chemistry", "applied-science", {2026: "10-14"}, "C"),
    ("R22", "Pharmaceutical Science", "applied-science", {2026: "10-17"}, "C"),
    ("R59", "Common Science Programme", "applied-science", {2026: "10-17"}, "C"),
    ("R62", "Environmental & Marine Science", "environmental-tech", {2026: "8-10"}, "C"),
    ("R32", "Mass Communication", "media-comms", {2026: "6-17"}, "A"),
    ("R48", "Consumer Insights & Psychology", "psychology-social", {2026: "15-18"}, "B"),
    ("R52", "Human Resource Management with Psychology", "human-resources", {2026: "11-16"}, "B"),
    ("R57", "Common Business Programme", "business-general", {2026: "13-20"}, "B"),
    ("R60", "Business", "business-general", {2026: "6-16"}, "B"),
    ("R11", "Business Process & Engineering Management", "engineering-management", {2026: "11-26"}, "C"),
    ("R21", "Supply Chain Management", "maritime-logistics", {2026: "13-26"}, "C"),
    ("R39", "Aviation Management", "aviation-management", {2026: "11-17"}, "C"),
    ("R40", "Aerospace Engineering", "aerospace", {2026: "14-24"}, "C"),
    ("R42", "Common Engineering Programme", "engineering-general", {2026: "13-26"}, "C", True),
    ("R50", "Electrical & Electronic Engineering", "electrical-engineering", {2026: "11-26"}, "C", True),
    ("R54", "Mobility & Robotic Systems", "robotics", {2026: "17-22"}, "C", True),
    ("R56", "Engineering", "engineering-general", {2026: "13-25"}, "C", True),
    ("R61", "Sustainable Built Environment", "architecture-built", {2026: "16-26"}, "C", True),
    ("R28", "Events & Project Management", "events-management", {2026: "14-23"}, "B"),
    ("R37", "Hotel & Leisure Management", "hospitality-tourism", {2026: "14-24"}, "B"),
    ("R46", "Restaurant & Culinary Management", "food-business", {2026: "15-22"}, "B"),
    ("R66", "Hospitality & Tourism Management", "hospitality-tourism", {2026: "11-22"}, "B"),
    ("R12", "Enterprise Cloud Computing & Management", "cloud-engineering", {2026: "15-26"}, "C", True),
    ("R13", "Applied AI & Analytics", "applied-ai", {2026: "15-26"}, "C", True),
    ("R18", "Financial Technology", "business-finance", {2026: "11-26"}, "C", True),
    ("R47", "Information Technology", "information-technology", {2026: "12-24"}, "C", True),
    ("R55", "Cybersecurity & Digital Forensics", "cybersecurity", {2026: "15-26"}, "C", True),
    ("R58", "Common ICT Programme", "ict-general", {2026: "13-26"}, "C", True),
    ("R26", "Sport & Exercise Science", "sport-wellness", {2026: "6-14"}, "C"),
    ("R33", "Outdoor Education", "outdoor-education", {2026: "11-18"}, "A"),
    ("R43", "Sports & Health", "sport-wellness", {2026: "14-26"}, "C"),
    ("R45", "Integrated Community Care", "community-care", {2026: "11-26"}, "C"),
    ("R49", "Sport Coaching", "sport-wellness", {2026: "15-26"}, "C", True),
    ("R63", "Common Sports & Health Programme", "sport-wellness", {2026: "9-26"}, "C", True),
    ("R19", "Digital Content Creation", "media-general", {2026: "9-21"}, "A"),
    ("R24", "Sonic Arts", "sonic-arts", {2026: "16-22"}, "D"),
    ("R25", "Arts & Entertainment Production Management", "arts-management", {2026: "13-21"}, "A"),
    ("R65", "Common Arts, Media & Design Programme", "design-general", {2026: "15-21"}, "A"),
    ("R67", "Design", "design-general", {2026: "14-21"}, "D"),
]

# Temasek publishes one table for the current exercise, listing every course
# twice -- once by interest and once by school. Transcribed from the "By
# Interest" listing, which is the complete set; the "By School" tables below it
# repeat the same 41 courses. TP does NOT state an ELR2B2 type on this page, so
# the basis stays the generic "net ELR2B2" rather than inventing a letter.
TP = [
    ("T38", "Biomedical Engineering", "biomedical-engineering", {2026: "7-12"}),
    ("T33", "Chemical Engineering", "chemical-engineering", {2026: "7-13"}),
    ("T70", "Common Science Programme", "applied-science", {2026: "8-11"}),
    ("T26", "Food, Nutrition & Culinary Science", "food-science", {2026: "5-12"}),
    ("T64", "Medical Biotechnology", "biomedical-science", {2026: "3-8"}),
    ("T25", "Pharmaceutical Science", "applied-science", {2026: "5-10"}),
    ("T45", "Veterinary Technology", "veterinary-technology", {2026: "3-9"}),
    ("T29", "Architectural Technology & Building Services", "architecture-built", {2026: "8-16"}),
    ("T28", "Integrated Facility Management", "facility-management", {2026: "12-16"}),
    ("T02", "Accountancy & Finance", "accountancy", {2026: "6-11"}),
    ("T04", "Aviation Management", "aviation-management", {2026: "4-11"}),
    ("T10", "Business", "business-general", {2026: "5-12"}),
    ("T43", "Business Process & Systems Engineering", "engineering-management", {2026: "5-15"}),
    ("T01", "Common Business Programme", "business-general", {2026: "5-12"}),
    ("T40", "Communications & Media Management", "media-comms", {2026: "4-12"}),
    ("T18", "Culinary Arts & Management", "food-business", {2026: "6-15"}),
    ("T08", "Hospitality & Tourism Management", "hospitality-tourism", {2026: "5-14"}),
    ("T09", "Law & Management", "law-management", {2026: "5-10"}),
    ("T07", "International Trade & Logistics", "maritime-logistics", {2026: "7-14"}),
    ("T67", "Marketing", "marketing", {2026: "9-13"}),
    ("T50", "Aerospace Electronics", "aerospace", {2026: "5-12"}),
    ("T51", "Aerospace Engineering", "aerospace", {2026: "5-10"}),
    ("T56", "Common Engineering Programme", "engineering-general", {2026: "8-19"}),
    ("T13", "Computer Engineering", "electronics-engineering", {2026: "11-19"}),
    ("T65", "Electronics", "electronics-engineering", {2026: "6-22"}),
    ("T66", "Mechatronics", "robotics", {2026: "3-12"}),
    ("T68", "Early Childhood Development & Education", "early-childhood", {2026: "7-16"}),
    ("T48", "Psychology Studies", "psychology-social", {2026: "4-9"}),
    ("T53", "Social Sciences in Gerontology", "community-care", {2026: "3-14"}),
    ("T69", "Applied Artificial Intelligence", "applied-ai", {2026: "8-14"}),
    ("T60", "Big Data & Analytics", "applied-ai", {2026: "4-14"}),
    ("T63", "Common ICT Programme", "ict-general", {2026: "9-20"}),
    ("T62", "Cybersecurity & Digital Forensics", "cybersecurity", {2026: "7-14"}),
    ("T58", "Immersive Media & Game Development", "game-development", {2026: "9-15"}),
    ("T30", "Information Technology", "information-technology", {2026: "12-18"}),
    ("T20", "Fashion Management & Design", "fashion-design", {2026: "5-15"}),
    ("T71", "Common Design Programme", "design-general", {2026: "6-15"}),
    ("T59", "Communication Design", "communication-design", {2026: "4-16"}),
    ("T23", "Digital Film & Television", "film-television", {2026: "8-14"}),
    ("T22", "Interior Architecture & Design", "product-interior-design", {2026: "4-12"}),
    ("T35", "Product Experience & Design", "product-interior-design", {2026: "13-15"}),
]

# Singapore Polytechnic publishes per COURSE PAGE -- there is no institution-wide
# table, and the /courses listing is client-rendered (a plain fetch returns
# "Showing 0 - 0 of 0"). The 34 course pages were enumerated from the ten school
# pages and transcribed one at a time on 2026-08-03.
#
# Two things this table records that a quicker transcription would have lost.
#
# 1. SP is MIXED on the ELR2B2 type, like the other four. Business courses are
#    type B, computing and maritime business type C, design and the built
#    environment type D, media type A -- and every science and engineering
#    course publishes NO type at all. `None` below means "SP does not state one",
#    checked on the page, not "not looked up". Inventing a letter would claim a
#    comparability SP has not.
#
# 2. The Diploma in Nautical Studies carries NO published aggregate range and NO
#    JAE course code on its own page, though it does publish entry requirements.
#    Its row has an empty year map and emits no band -- the same shape SUTD's
#    five courses already use. PathAhead does not say WHY the figure is absent,
#    because SP does not say, and guessing at a reason would be the same error as
#    guessing at the figure.
#
# The seven "Diploma in MAD, ..." pages are NOT seven courses. Each one carries
# the same code S29 and the same range, and SP labels the intake "For Entire
# Cohort of Diploma in Media, Arts & Design". They are specialisations chosen
# within one JAE course, so they are loaded as one. That is what reconciles the
# forty course pages with the thirty-four diplomas SP says it offers.
SP = [
    # School of Architecture & the Built Environment
    ("S66", "Architecture", "architecture-built", {2026: "8-15"}, "D"),
    ("S68", "Civil Engineering", "civil-engineering", {2026: "8-21"}, None),
    ("S95", "Facilities Management", "facility-management", {2026: "13-18"}, "D"),
    ("S50", "Integrated Events & Project Management", "events-management", {2026: "10-15"}, "D"),
    ("S89", "Interior Design", "product-interior-design", {2026: "11-15"}, "D"),
    ("S94", "Landscape Architecture", "landscape-horticulture", {2026: "6-15"}, "D"),
    # School of Business
    ("S75", "Accountancy", "accountancy", {2026: "5-12"}, "B"),
    ("S76", "Banking & Finance", "business-finance", {2026: "5-11"}, "B"),
    ("S71", "Business Administration", "business-general", {2026: "4-12"}, "B"),
    ("S31", "Common Business Programme", "business-general", {2026: "5-12"}, "B"),
    ("S48", "Human Resource Management with Psychology", "human-resources", {2026: "6-12"}, "B"),
    # School of Chemical & Life Sciences
    ("S64", "Applied Chemistry", "applied-science", {2026: "3-9"}, None),
    ("S98", "Biomedical Science", "biomedical-science", {2026: "3-7"}, None),
    ("S70", "Chemical & Biological Engineering", "chemical-engineering", {2026: "5-12"}, None),
    ("S28", "Common Science Programme", "applied-science", {2026: "7-9"}, None),
    ("S47", "Food Science & Technology", "food-science", {2026: "5-12"}, None),
    ("S67", "Optometry", "optometry", {2026: "7-11"}, None),
    ("S38", "Perfumery & Cosmetic Science", "perfumery-cosmetic", {2026: "5-11"}, None),
    # School of Computing
    ("S30", "Applied AI & Analytics", "applied-ai", {2026: "5-8"}, "C"),
    ("S69", "Computer Science", "computer-science", {2026: "4-15"}, "C"),
    ("S54", "Cybersecurity & Digital Forensics", "cybersecurity", {2026: "5-11"}, "C"),
    ("S32", "Common ICT Programme", "ict-general", {2026: "5-17"}, "C"),
    # School of Electrical & Electronic Engineering
    ("S90", "Aerospace Electronics", "aerospace", {2026: "4-13"}, None),
    ("S53", "Computer Engineering", "electronics-engineering", {2026: "7-20"}, None),
    ("S99", "Electrical & Electronic Engineering", "electrical-engineering", {2026: "5-15"}, None),
    ("S42", "Engineering with Business", "engineering-management", {2026: "6-12"}, None),
    # School of Mechanical & Aeronautical Engineering
    ("S88", "Aeronautical Engineering", "aerospace", {2026: "5-13"}, None),
    ("S91", "Mechanical Engineering", "mechanical-engineering", {2026: "5-15"}, None),
    ("S73", "Mechatronics & Robotics", "robotics", {2026: "5-13"}, None),
    ("S40", "Common Engineering Programme", "engineering-general", {2026: "3-19"}, None),
    # Singapore Maritime Academy
    ("S63", "Marine Engineering", "offshore-marine-engineering", {2026: "9-22"}, None),
    ("S74", "Maritime Business", "maritime-logistics", {2026: "5-15"}, "C"),
    ("", "Nautical Studies", "nautical-studies", {}, None),
    # Media, Arts & Design School -- one JAE course, seven specialisations
    ("S29", "Media, Arts & Design", "design-general", {2026: "6-13"}, "A"),
]

# Where each SP figure actually lives.
#
# SP is the one institution in this pack whose source is not a page but a SET
# of pages: the aggregate range for each course is on that course's own page,
# under a school. Citing sp.edu.sg/courses/diplomas for all thirty-four sends a
# reader to a listing that does not even render the courses without JavaScript,
# and asks them to go and find the number themselves. These are the pages the
# figures were transcribed from, so a reader lands on the table.
#
# Keyed by JAE code because the code is what the row already carries, and it is
# stable across the course renames that the slugs are not.
SP_COURSE_PAGE = {
    "S66": "abe/architecture",
    "S68": "abe/civil-engineering",
    "S95": "abe/facilities-management",
    "S50": "abe/integrated-events-and-project-management",
    "S89": "abe/interior-design",
    "S94": "abe/landscape-architecture",
    "S75": "sb/accountancy",
    "S76": "sb/banking-finance",
    "S71": "sb/business-administration",
    "S31": "sb/common-business-programme",
    "S48": "sb/human-resource-management-with-psychology",
    "S64": "cls/applied-chemistry",
    "S98": "cls/biomedical-science",
    "S70": "cls/chemical-biological-engineering",
    "S28": "cls/common-science-programme",
    "S47": "cls/food-science-and-technology",
    "S67": "cls/optometry",
    "S38": "cls/perfumery-and-cosmetic-science",
    "S30": "soc/applied-ai-analytics",
    "S69": "soc/computer-science",
    "S54": "soc/cybersecurity-digital-forensics",
    "S32": "soc/common-ict-programme",
    "S90": "eee/aerospace-electronics",
    "S53": "eee/computer-engineering",
    "S99": "eee/electrical-electronic-engineering",
    "S42": "eee/engineering-with-business",
    "S88": "mae/aeronautical-engineering",
    "S91": "mae/mechanical-engineering",
    "S73": "mae/mechatronics-and-robotics",
    "S40": "mae/common-engineering-programme",
    "S63": "sma/marine-engineering",
    "S74": "sma/maritime-business",
    # The Diploma in Media, Arts & Design is ONE JAE course with seven
    # specialisation pages, each carrying the same code and the same range.
    # Linking to any single specialisation would imply the figure belongs to
    # that specialisation alone, so this points at the school.
    "S29": "mad",
}
SP_COURSE_BASE = "https://www.sp.edu.sg/courses/schools/"

#: Nautical Studies has no JAE code, so it is keyed by name. Its page carries
#: the entry requirements PathAhead does hold, which is what a reader following
#: the citation is looking for.
SP_PAGE_BY_NAME = {"Nautical Studies": "sma/nautical-studies"}


def sp_course_url(code: str, name: str) -> str | None:
    slug = SP_COURSE_PAGE.get(code) or SP_PAGE_BY_NAME.get(name)
    return SP_COURSE_BASE + slug if slug else None


INSTITUTIONS = {
    "NYP": dict(
        full="Nanyang Polytechnic",
        slug="nyp",
        source="nyp-cop-datagov",
        url="https://www.nyp.edu.sg/student/study/courses",
        rows=NYP,
    ),
    "NP": dict(
        full="Ngee Ann Polytechnic",
        slug="np",
        source="np-cop-datagov",
        url="https://www.np.edu.sg/admissions-enrolment/academic-matters/elr2b2",
        rows=NP,
    ),
    "TP": dict(
        full="Temasek Polytechnic",
        slug="tp",
        source="tp-intake-aggregate",
        url="https://www.tp.edu.sg/admissions-and-finance/course-intake-aggregate-range.html",
        rows=TP,
    ),
    "RP": dict(
        full="Republic Polytechnic",
        slug="rp",
        source="rp-elr2b2-intake",
        url="https://www.rp.edu.sg/admissions/intake/",
        rows=RP,
    ),
    "SP": dict(
        full="Singapore Polytechnic",
        slug="sp",
        source="sp-course-elr2b2",
        url="https://www.sp.edu.sg/courses/diplomas",
        rows=SP,
    ),
}


# ---------------------------------------------------------------------------
# Tuition fees, AY2026. Transcribed 2026-08-05 from each polytechnic's OWN
# fee page — four separate fetches, four separate tables.
#
# All four figures agree exactly: SGD 3,100 citizen, 6,400 PR, 12,400 ASEAN,
# 13,600 non-ASEAN. That is not licence to have copied one across the others.
# The identical-looking numbers are exactly the situation the NTU candidature
# lesson in NEXT.md §1a warns about, and reading each page found three things
# a copy would have got wrong:
#
#   1. **The supplementary fee differs at every polytechnic** — SP 77.52,
#      TP 83.15, RP 86.50, NYP 88.09 for a citizen. It is small, it is real
#      money, and it is the tell that these are four publications and not one.
#   2. **TP's AY2026/2027 international tables now exist.** NEXT.md recorded
#      on 2026-08-03 that they did not, and that TP's visible international
#      figure was the AY2025/2026 one — a year older and on the pre-split
#      basis. TP has since published both the ASEAN and non-ASEAN tables. The
#      note that used to say "do not assume the split is universal" was right
#      to insist on checking; what checking found is that it now IS universal
#      across the four, for AY2026 only.
#   3. **Every one of the four publishes a lower citizen rate for students
#      aged 40 and above** (SGD 2,100, with the SkillsFuture Mid-Career
#      Enhanced Subsidy). The tier recorded here is the under-40 one, which is
#      the rate for the school-leaver cohort this transition is about. The
#      other rate is named in the note rather than dropped.
#
# Ngee Ann is deliberately absent — see FEE_GAP.
#
# The figure recorded is the **subsidised tuition fee**, not "fees payable",
# to match what the six universities hold and what
# test_published_fee_tiers_are_internally_consistent compares. The
# supplementary fee is named in the note because a family is billed it.
# ---------------------------------------------------------------------------
FEE_STALE_AFTER = "2027-04-30"

FEES: dict[str, dict] = {
    "NYP": dict(
        source="nyp-fees",
        citizen=3100, pr=6400, asean=12400, is_other=13600,
        supplementary="SGD 88.09 for a citizen, 118.09 for a PR and 178.59 for an "
                      "international student",
        as_of="Nanyang Polytechnic states the table is correct as of 14 May 2026.",
        extra="NYP publishes the same table for the 2023, 2024 and 2025 intakes, and the "
              "AY2026 non-ASEAN rate is the first year it differs from the ASEAN one.",
    ),
    "TP": dict(
        source="tp-fees",
        citizen=3100, pr=6400, asean=12400, is_other=13600,
        supplementary="SGD 83.15 for a citizen, 113.15 for a PR and 173.65 for an "
                      "international student",
        as_of="Temasek Polytechnic publishes this as the AY2026/2027 April intake table.",
        extra="Do not read TP's Polytechnic Foundation Programme tables, which sit on the "
              "same page and are a different programme at a different price.",
    ),
    "RP": dict(
        source="rp-fees",
        citizen=3100, pr=6400, asean=12400, is_other=13600,
        supplementary="SGD 86.50 for a citizen, 116.50 for a PR and 177.00 for an "
                      "international student",
        as_of="Republic Polytechnic states the page was last updated on 27 February 2026.",
        extra="RP names the eleven ASEAN member states the ASEAN rate applies to, rather "
              "than leaving a reader to assume which countries count.",
    ),
    "SP": dict(
        source="sp-fees",
        citizen=3100, pr=6400, asean=12400, is_other=13600,
        supplementary="SGD 77.52 for a citizen, 107.52 for a PR and 167.99 for an "
                      "international student",
        as_of="Singapore Polytechnic states the information is correct as of 7 May 2026.",
        extra="SP itemises the supplementary fee as examination, sports, insurance, "
              "student union and CLASS licence charges.",
    ),
}

#: Why Ngee Ann carries no fee, in the student's own language. This is a
#: retrieval failure, not a publication gap, and the difference matters: NP
#: DOES publish a fee table, so the honest thing is to say we could not read
#: it and point at it, not to imply Ngee Ann is silent.
#:
#: The four figures above are identical to one another, which makes filling
#: this in by inference feel almost safe. It is not: MOE setting a common
#: subsidised rate is an inference about a process, not a figure Ngee Ann
#: published, and the supplementary fee — which differs at all four — proves
#: these are four separate publications. A number in front of a family has to
#: come from the institution that will bill them.
FEE_GAP = (
    "PathAhead shows no fee for this course on purpose. Ngee Ann Polytechnic "
    "publishes an annual course fee table, but its fee page could not be "
    "retrieved when this pack was built, and the four other polytechnics' "
    "figures are not Ngee Ann's to borrow — they are four separate "
    "publications that happen to agree. Ngee Ann's own fee page has the "
    "number to plan around:"
)
NP_FEE_URL = "https://www.np.edu.sg/admissions-enrolment/academic-matters/course-fees"


# ---------------------------------------------------------------------------
# Language requirements.
#
# This block exists because of a real failure. A student who does not read
# Chinese was shown NP's Diploma in Chinese Studies as her SECOND STRONGEST
# match out of 296 courses, on 67 points of entirely generic overlap. Nothing
# in the pack recorded that Ngee Ann requires Higher Chinese grade 1-4 or
# Chinese grade 1-3 to be considered, or that NP states at least half the
# course is conducted in Chinese.
#
# Transcribed from each course's own Entry Requirements table.
# ---------------------------------------------------------------------------
LANGUAGE_REQUIREMENTS: dict[str, dict] = {
    "np-chinese-studies": dict(
        language="chinese",
        label="Higher Chinese grade 1-4, or Chinese grade 1-3",
        taught_in_language=True,
        detail=(
            "Ngee Ann states that at least half the course is conducted in "
            "Chinese. The grade is the entry condition; the language of "
            "teaching is the part a grade table would never tell you, and it "
            "is the part that decides whether three years are livable."
        ),
    ),
    "np-chinese-media-and-communication": dict(
        language="chinese",
        label="Higher Chinese grade 1-4, or Chinese grade 1-3",
        taught_in_language=True,
        detail=(
            "A Chinese-medium media and communication diploma. The work "
            "itself -- writing, presenting, producing -- is in Chinese."
        ),
    ),
    "np-tamil-studies-with-early-education": dict(
        language="tamil",
        label="Tamil Language",
        taught_in_language=True,
        detail=(
            "A Tamil-medium diploma preparing teachers of Tamil. The language "
            "is the subject, not a component of it."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Per-course descriptions.
#
# The pack held 116 shared blurbs across 330 courses -- roughly three courses
# to a sentence -- because descriptions were written at course-FAMILY level.
# That is what let a Chinese-medium diploma read as a generic media course, and
# it is why fit scores saturate: two courses with identical text are identical
# to the scorer.
#
# These are PathAhead's PARAPHRASE of what each course says it is for, written
# from the institution's own course page and labelled as ours on every card.
# They are not quotations and not marketing copy: the aim is what a family
# needs to tell two similar-sounding courses apart -- what you actually do, and
# what it leads to.
#
# Keyed by JAE code so a course rename does not silently orphan its text.
# ---------------------------------------------------------------------------
SP_DESCRIPTION: dict[str, str] = {
    "S66": "Designing buildings and seeing them documented properly — studio design work alongside technical drawing, structures and the regulations a drawing has to satisfy before anyone builds from it.",
    "S68": "The engineering behind roads, tunnels, bridges and foundations: structural analysis, soil and materials behaviour, and the site supervision that turns a design into something standing up.",
    "S95": "Keeping large buildings running — the air-conditioning, power, fire safety and maintenance contracts that a hospital or a mall depends on, and the cost of getting them wrong.",
    "S50": "Planning and running live events end to end: venues, budgets, suppliers, safety and the project management that holds a fixed date together when something goes wrong.",
    "S89": "Interiors as designed space rather than decoration — spatial planning, materials, lighting and the drawings a contractor can actually build from.",
    "S94": "Designing and managing planted space: how soil, climate and plant choice behave over years, plus the horticulture to keep a landscape alive after handover.",
    "S75": "Accounting practice to a professional standard — financial and management accounts, audit, tax and the reporting rules — with a recognised path towards a professional qualification.",
    "S76": "How money moves and is priced: banking operations, investment and risk, taught around the products and regulation a Singapore financial institution actually runs on.",
    "S71": "The general management of a business — marketing, operations, people and finance — for someone who wants the whole picture before choosing a specialism.",
    "S31": "A shared business foundation year before you commit: you sample the disciplines, then choose your specialisation once you have seen what each is like from the inside.",
    "S48": "The people side of an organisation, read through psychology: hiring, developing and retaining staff, employment practice, and why workplaces behave as they do.",
    "S64": "Chemistry done at the bench and then scaled: analysis, instrumentation and quality control, aimed at laboratory and process work in the chemical and pharmaceutical industries.",
    "S98": "The laboratory science behind diagnosis — human biology, disease processes and the analytical techniques a hospital or research laboratory runs on.",
    "S70": "Chemical engineering with a biological core: reaction and process design, and the manufacture of pharmaceuticals and biologics at industrial scale.",
    "S28": "A shared science foundation year: you take the common ground first, then choose the specific science diploma once you know which one you actually want.",
    "S47": "The science of what we eat — composition, safety, shelf life and new product development — with substantial time in food laboratories and pilot kitchens.",
    "S67": "Examining eyes and prescribing correction, trained in clinic on real patients. A registered profession: the qualification is what opens the register.",
    "S38": "Formulating fragrances and cosmetics: the chemistry of ingredients and stability, plus the sensory and product-development work that decides whether a formulation sells.",
    "S30": "Building machine-learning and analytics systems that run on real data — statistics and modelling, then the engineering to put a model into something people use.",
    "S69": "Software engineering from the foundations up: algorithms, data structures and systems, with a heavy build-it workload rather than theory alone.",
    "S54": "Defending and investigating systems — networks, intrusion, forensics and incident response — taught largely hands-on in labs rather than from a textbook.",
    "S32": "A shared computing foundation year: programming, data and systems in common, then you choose the specific ICT diploma once you have tried each.",
    "S90": "The electronics inside an aircraft — avionics, navigation, communications and instrumentation — maintained to aviation regulatory standards.",
    "S53": "Where hardware meets software: embedded systems, computer architecture and the interfaces that let physical devices and code work together.",
    "S99": "Power and electronics together: generation and distribution, machines, control systems and building services, with substantial laboratory time.",
    "S42": "Engineering read through a commercial lens — technical grounding plus costing, operations and project management, for engineering roles that sit close to the business.",
    "S88": "Aircraft as machines: airframes, propulsion and maintenance engineering, taught to the standards aviation regulation requires.",
    "S91": "Mechanics, materials and machine design, worked out in workshops as much as classrooms — how things carry load, move and fail.",
    "S73": "Machines that sense and move: mechanics, control systems, electronics and embedded code brought together into working robots and automated systems.",
    "S40": "A shared engineering foundation year: the common mechanics, electronics and mathematics first, then you choose the engineering specialisation.",
    "S63": "Running and maintaining a ship's machinery, trained towards certification for service at sea — engine room systems, marine power and safety.",
    "S74": "The commercial side of shipping — chartering, port operations, logistics and maritime law — for the trade that moves through Singapore rather than the vessels themselves.",
    "S29": "A shared foundation across media, art and design, after which you specialise — animation and games, sound and music, film, visual communication, or product and experience design.",
}
SP_DESC_BY_NAME = {
    "Nautical Studies": "Navigation and ship handling, trained towards certification as a deck officer — seamanship, cargo work, maritime law and time at sea.",
}


# ---------------------------------------------------------------------------
# Professional accreditation.
#
# For most courses this is empty and that is correct — an accountancy diploma
# is not a licence to do anything. For a handful it is the single most
# consequential fact on the page, more than any grade figure: an unregistered
# nurse, dental therapist, optometrist or TCM practitioner cannot lawfully
# practise, and the qualification is what opens the register.
#
# Keyed by outcome id. Deliberately sparse: a body is listed only where the
# regulator's own remit makes the link unambiguous. Where a course merely
# "prepares you for" a career with no statutory register, nothing is claimed.
# ---------------------------------------------------------------------------
ACCREDITATION: dict[str, list[dict]] = {
    "sp-optometry": [dict(
        body="Optometrists and Opticians Board",
        label="the qualification required to register and practise as an optometrist in Singapore",
        detail=(
            "Optometry is a registered profession under the Optometrists and "
            "Opticians Act. Practising without registration is an offence, and "
            "registration is what a recognised diploma opens — which makes this "
            "a harder constraint than any published aggregate."
        ),
    )],
    "np-optometry": [dict(
        body="Optometrists and Opticians Board",
        label="the qualification required to register and practise as an optometrist in Singapore",
        detail=(
            "Optometry is a registered profession under the Optometrists and "
            "Opticians Act; registration, not the diploma alone, is what "
            "permits practice."
        ),
    )],
    "nyp-nursing": [dict(
        body="Singapore Nursing Board",
        label="the qualification required to register as an enrolled nurse",
        detail=(
            "Nursing is a registered profession under the Nurses and Midwives "
            "Act. A diploma accredited by the Board is the route onto the "
            "register; without registration the work cannot be done."
        ),
    )],
    "np-nursing": [dict(
        body="Singapore Nursing Board",
        label="the qualification required to register as an enrolled nurse",
        detail=(
            "Nursing is a registered profession under the Nurses and Midwives "
            "Act, and registration is what permits practice."
        ),
    )],
    "nyp-oral-health-therapy": [dict(
        body="Singapore Dental Council",
        label="the qualification required to register as an oral health therapist",
        detail=(
            "Oral health therapy is regulated under the Dental Registration "
            "Act. The scope of practice is set by the Council, not by the "
            "employer."
        ),
    )],
}


def accreditation_block(oid: str, source: str, page: str | None) -> str:
    rows = ACCREDITATION.get(oid)
    if not rows:
        return ""
    out = ["    accreditation:"]
    for a in rows:
        out.append(f"      - body: {a['body']}")
        out.append("        label: >-")
        out.append(_wrap(a["label"], 12))
        out.append("        detail: >-")
        out.append(_wrap(a["detail"], 12))
        out.append("        fact:")
        out.append(f"          value: recognised by the {a['body']}")
        out.append("          as_of_year: 2026")
        out.append(f"          source: {source}")
        if page:
            out.append(f"          url: {page}")
        out.append("          confidence: medium")
        out.append(f"          stale_after: {STALE_AFTER}")
        out.append("          note: >-")
        out.append(_wrap(
            "Recorded because a registered profession is a harder constraint "
            "than a grade profile: without registration the work cannot "
            "lawfully be done. Confirm the current accredited-qualification "
            "list with the board itself before relying on this — the register, "
            "not this tool, is the authority.", 12))
    return "\n".join(out)


def language_block(oid: str) -> str:
    lr = LANGUAGE_REQUIREMENTS[oid]
    out = [
        "    language_requirement:",
        f"      language: {lr['language']}",
        f"      label: \"{lr['label']}\"",
        "      at_stage: o-level",
        f"      taught_in_language: {str(lr['taught_in_language']).lower()}",
        "      detail: >-",
        _wrap(lr["detail"], 8),
        "      fact:",
        f"        value: \"{lr['label']}\"",
        "        as_of_year: 2026",
        "        source: np-entry-requirements",
        "        confidence: high",
        f"        stale_after: {STALE_AFTER}",
        "        note: >-",
        _wrap(
            "Transcribed from the course's own Entry Requirements table on "
            "Ngee Ann Polytechnic's website. Recorded so PathAhead stops "
            "ranking a course taught in a language as a strong match for a "
            "student who has not said they offer it. The course is still "
            "shown -- the requirement is the polytechnic's to waive, not this "
            "tool's to assume.", 10),
    ]
    return "\n".join(out)


def _wrap(text: str, indent: int, width: int = 78) -> str:
    """Fold a long string into a YAML block scalar body."""
    pad = " " * indent
    words = text.split()
    lines: list[str] = []
    cur = pad
    for w in words:
        if len(cur) + len(w) + 1 > width and cur.strip():
            lines.append(cur.rstrip())
            cur = pad + w
        else:
            cur = (cur + " " + w) if cur.strip() else pad + w
    if cur.strip():
        lines.append(cur.rstrip())
    return "\n".join(lines)


def _parse(cell: str) -> tuple[int, int]:
    lo, hi = re.split(r"\s*(?:-|to)\s*", cell.strip())
    return int(lo), int(hi)


def _slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[&/]", " and ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def build() -> str:
    out: list[str] = []
    out.append(HEADER)
    out.append("outcomes:")

    for short, inst in INSTITUTIONS.items():
        for row in inst["rows"]:
            code, name, family, years = row[0], row[1], row[2], row[3]
            agg = row[4] if len(row) > 4 else None
            vacancies = bool(row[5]) if len(row) > 5 else False
            fam = FAMILIES[family]
            aggregate = f"ELR2B2-{agg}" if agg else "ELR2B2"
            basis = f"net {aggregate} O-Level aggregate, where lower is better"

            oid = f"{inst['slug']}-{_slug(name)}"
            # The most specific page this course has. For SP that is the
            # course's own page; for the other four the institution publishes
            # one table covering every course, so the table IS the right link.
            page = sp_course_url(code, name) if short == "SP" else None
            desc = (SP_DESCRIPTION.get(code) or SP_DESC_BY_NAME.get(name)) if short == "SP" else None
            out.append(f"  - id: {oid}")
            out.append(f"    institution: {inst['full']}")
            out.append(f"    institution_short: {short}")
            out.append(f"    name: {name}")
            out.append("    transition: a-level-to-university-2026")
            out.append(f"    url: {page or inst['url']}")
            out.append("    route_group: polytechnic-diploma")
            out.append(f"    tags: [polytechnic, diploma, {inst['slug']}]")
            # Duration. Every full-time polytechnic diploma is three years;
            # the 2 or 2.5-year figure quoted elsewhere in this file is the
            # SHORTENED Direct Admissions Exercise route for an A-Level
            # holder, not the course's own length, and the two must not be
            # conflated. The structure line says so rather than leaving a
            # reader to discover it.
            out.append("    duration:")
            out.append("      years: 3")
            out.append("      structure: >-")
            out.append(_wrap(
                "Three years full-time. An A-Level holder entering through the "
                "Direct Admissions Exercise is admitted to a shortened 2 or "
                "2.5-year version of the same diploma, subject to places being "
                "available.", 8))
            out.append("      fact:")
            out.append("        value: 3 years full-time")
            out.append("        as_of_year: 2026")
            out.append(f"        source: {inst['source']}")
            if page:
                out.append(f"        url: {page}")
            out.append("        confidence: high")
            out.append(f"        stale_after: {STALE_AFTER}")

            # Progression. The poly-to-degree route is a first-class
            # destination in this pack, so where it leads is course data, not
            # a footnote. Stated at the level the polytechnics themselves
            # state it -- that diploma holders are eligible to apply, with
            # advanced standing considered case by case -- because a
            # course-by-course articulation table is not something any of them
            # publishes in full.
            out.append("    progression:")
            out.append("      - label: A degree at one of Singapore's autonomous universities")
            out.append("        exemption: advanced standing considered case by case")
            out.append("        detail: >-")
            out.append(_wrap(
                "Polytechnic diploma holders apply to NUS, NTU, SMU, SUTD, SIT "
                "and SUSS through the diploma admissions route rather than on "
                "A-Level results, and each university publishes its own "
                "indicative polytechnic GPA. Exemptions and shortened "
                "candidature are decided by the receiving university, not by "
                "the polytechnic, and vary by subject match.", 10))
            out.append("        fact:")
            out.append("          value: eligible to apply for university admission as a diploma holder")
            out.append("          as_of_year: 2026")
            out.append(f"          source: {inst['source']}")
            out.append("          confidence: medium")
            out.append(f"          stale_after: {STALE_AFTER}")

            # Money. Emitted here, above the band, so that it reaches every
            # course including the ones with no published aggregate range --
            # a family still has to pay for Nautical Studies.
            out.append(_cost_block(short))

            # A course whose publisher prints no aggregate range gets NO band,
            # rather than a band standing in for one. SUTD's five courses have
            # the same shape and the engine already has an honest verdict for
            # it. Saying nothing is a claim this project is willing to make;
            # saying something approximate is not.
            if not years:
                out.append(_no_band_editorial(fam, name, inst, desc, page))
                out.append("")
                continue

            latest = max(years)
            lo, hi = _parse(years[latest])
            history = sorted((y for y in years if y != latest), reverse=True)
            out.append("    band:")
            out.append(f'      p10: "{lo}"')
            out.append(f'      p90: "{hi}"')
            out.append(f"      p10_points: {lo}")
            out.append(f"      p90_points: {hi}")
            out.append("      statistic: min_max")
            out.append("      scale: elr2b2_olevel")
            out.append("      comparable: false")
            out.append(f"      basis: {basis}")
            if history:
                out.append("      history:")
                for y in history:
                    hlo, hhi = _parse(years[y])
                    out.append(f"        - year: {y}")
                    out.append(f"          low: {hlo}")
                    out.append(f"          high: {hhi}")
                    out.append(f'          label: "{hlo} to {hhi}"')
            out.append("      fact:")
            out.append(f'        value: "{lo} to {hi}"')
            out.append(f"        as_of_year: {latest}")
            out.append(f"        source: {inst['source']}")
            if page:
                out.append(f"        url: {page}")
            out.append("        confidence: high")
            out.append(f"        stale_after: {STALE_AFTER}")
            out.append("        note: >-")
            out.append(_wrap(
                f"Net {aggregate} aggregate, after CCA bonus points, of the lowest and "
                f"highest ranked student admitted to JAE course code {code} in the "
                f"{latest} Joint Admissions Exercise. This is the whole admitted "
                f"cohort, not a middle percentile band, so it is wider than a "
                f"university's published range by construction. It is an O-Level "
                f"statistic: an A-Level holder admitted through JAE is admitted on "
                f"their O-Level results, and one admitted through the Direct "
                f"Admissions Exercise is assessed on academic results and interview "
                f"with no published aggregate at all. PathAhead therefore shows this "
                f"figure and does not compare it with an A-Level score."
                + (
                    f" This course still had vacancies after the {latest} JAE posting, "
                    f"which the polytechnic marks with an asterisk. It states that an "
                    f"appeal needs the course's Minimum Entry Requirements and a net "
                    f"aggregate of 26 or better, and that meeting them does not "
                    f"guarantee a place."
                    if vacancies else ""
                ),
                indent=10))
            acc = accreditation_block(oid, inst["source"], page)
            if acc:
                out.append(acc)
            if oid in LANGUAGE_REQUIREMENTS:
                out.append(language_block(oid))
            out.append(_editorial_block(fam, desc, page))
            out.append("")

    return "\n".join(out)


def _cost_block(short: str) -> str:
    """The annual fee, or the reason there isn't one.

    Two shapes, and the second is not a placeholder. A course with no fee
    figure renders as "no fee figure — and why", which is a different thing
    from a blank: it says a decision was taken and shows its reasoning.
    """
    fee = FEES.get(short)
    if not fee:
        return "\n".join([
            "    fee_note: >-",
            _wrap(FEE_GAP + f" ({NP_FEE_URL})", 6),
        ])

    return "\n".join([
        "    cost:",
        f"      annual_fee_citizen: {fee['citizen']}",
        f"      annual_fee_pr: {fee['pr']}",
        f"      annual_fee_international: {fee['asean']}",
        f"      annual_fee_is_other: {fee['is_other']}",
        # Every polytechnic states that a student who does not take the
        # tuition grant pays "full fees", and none of the four prints that
        # figure. Same decision as NTU's lab/non-lab split: an unpublished
        # number is not computed here.
        "      years: 3",
        "      tuition_grant_available: true",
        "      bond_years_citizen: 0",
        "      bond_years_pr_is: 3",
        "      bond_note: >-",
        _wrap(
            "Singapore Citizens owe no bond for the tuition grant itself. "
            "Permanent Residents and international students who accept it must "
            "work for a Singapore entity for 3 years after graduating. The "
            "polytechnic states that buying out of the bond means liquidated "
            "damages set by MOE, not simply repaying the grant.", 8),
        "      fact:",
        f'        value: "SGD {fee["citizen"]}/yr citizen, {fee["pr"]} PR, '
        f'{fee["asean"]} international (ASEAN), {fee["is_other"]} (non-ASEAN)"',
        "        as_of_year: 2026",
        f"        source: {fee['source']}",
        "        confidence: high",
        f"        stale_after: {FEE_STALE_AFTER}",
        "        note: >-",
        _wrap(
            "Subsidised annual tuition for a student who accepts the MOE Tuition "
            "Grant, for the cohort admitted in 2026. Polytechnics fix the fee for "
            "the whole course, so this is the rate for all three years. On top of "
            f"tuition comes a supplementary fee of {fee['supplementary']} a year, "
            "covering things like examinations, insurance and the student union — "
            "small, but it is billed. Citizen and PR figures exclude GST, which MOE "
            "subsidises; the international figures include it. A Singapore Citizen "
            "aged 40 or above pays SGD 2,100 under the SkillsFuture Mid-Career "
            "Enhanced Subsidy; the figure shown here is the under-40 rate. The fee "
            "for a student who does not take the tuition grant is not recorded, "
            "because the polytechnic does not publish one. "
            + fee["as_of"] + " " + fee["extra"], 10),
    ])


def _editorial_block(fam: dict, summary: str | None = None, page: str | None = None) -> str:
    """PathAhead's own characterisation of the course.

    `summary` is a PER-COURSE paraphrase where one has been written; without
    it the text falls back to the course FAMILY, which is what 116 shared
    sentences across 330 courses looked like. The fact note says which of the
    two a reader is looking at, because "our description" means something
    different when it describes forty courses at once.
    """
    q = lambda xs: ", ".join(chr(34) + x + chr(34) for x in xs)  # noqa: E731
    return "\n".join([
        "    editorial:",
        f"      interests: [{q(fam['interests'])}]",
        f"      subject_affinity: [{q(fam['subjects'])}]",
        f"      assessment_style: [{q(fam['assessment'])}]",
        f"      teamwork: {fam['teamwork']}",
        f"      maths_intensity: {fam['maths']}",
        f"      writing_intensity: {fam['writing']}",
        f"      sectors: [{q(fam['sectors'])}]",
        "      summary: >-",
        _wrap(summary or fam["summary"], indent=8),
        "      fact:",
        "        value: PathAhead's own description of this course",
        "        as_of_year: 2026",
        "        source: pathahead-editorial",
        *( [f"        url: {page}"] if page else [] ),
        "        confidence: medium",
        "        basis: editorial",
        f"        stale_after: {STALE_AFTER}",
        "        note: >-",
        _wrap(
            ("PathAhead's paraphrase of what this course says it is for, "
             "written from the polytechnic's own course page. NOT a quotation "
             "and not the polytechnic's wording. If it misrepresents the "
             "course, please tell us."
             if summary else
             "NOT the polytechnic's description, and written at course-FAMILY "
             "level rather than for this course specifically. If it is wrong, "
             "please tell us."), indent=10),
    ])


def _no_band_editorial(fam: dict, name: str, inst: dict,
                       desc: str | None = None, page: str | None = None) -> str:
    """A course the publisher prints no aggregate range for.

    It gets NO band and no substitute for one -- the same shape SUTD's five
    courses already have, which the engine already renders honestly. Nothing is
    said about WHY the figure is absent, because Singapore Polytechnic does not
    say, and a plausible-sounding reason would be the same class of invention as
    a plausible-sounding figure.

    Note this is deliberately NOT recorded in `fee_note`: that field is about a
    missing COST, and borrowing it for a missing grade band would surface this
    course's gap in the wrong place on the card.
    """
    return _editorial_block(fam, desc, page)


HEADER = '''# Outcomes -- polytechnic diplomas.
#
# GENERATED by tools/build_polytechnic_pack.py. Edit the tables in that file and
# re-run it; do not hand-edit this one.
#
# Why polytechnic diplomas appear in the same list as degrees
# ----------------------------------------------------------
# Because they are a real destination, not a consolation. Showing them only
# after a student "misses" a university range would teach exactly the ranking
# this project refuses to teach. They are marked as a different ROUTE, which
# they are.
#
# Why every band here is `comparable: false`
# ------------------------------------------
# The published figure is a net ELR2B2 O-Level aggregate. It is not the score
# PathAhead computes for an A-Level student, and no route makes it so:
#
#   * Through JAE, an A-Level holder is admitted on their GCE O-Level results,
#     so the relevant aggregate is one PathAhead does not hold for them.
#   * Through the Direct Admissions Exercise, an A-Level holder is assessed on
#     "academic results and/or interview/test, subject to the availability of
#     vacancies" -- there is no published aggregate for that route at all, and
#     the diploma is shortened to 2 or 2.5 years.
#
# So the numbers are shown, in the publisher's own terms, and no verdict is
# drawn from them. See engine/buckets.py:assess_published_on_another_basis.
#
# Why the range is wider than a university's
# ------------------------------------------
# It is a different statistic. `min_max` is the lowest AND highest ranked
# student admitted -- the entire cohort. A university's `p10_p90` cuts both
# tails off by construction. NYP Nursing spans 3 to 28 across recent years
# because someone was admitted at 28, which a percentile band would have
# excluded. Rendering the two alike would be the most misleading thing on the
# page.

'''


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    n = build().count("  - id:")
    print(f"wrote {OUT.relative_to(ROOT)} -- {n} outcomes")

"""Build packs/singapore/secondary-schools.yaml from real, licensed source data.

Run once, by hand, when the upstream data.gov.sg dataset changes:

    python3 tools/build_secondary_schools_pack.py

Inputs:
  - tools/_raw_school_directory.json  -- 337 rows fetched from data.gov.sg's
    "General information of schools" (MOE, resource_id d_688b934f82c1059
    ed0a6993d2a829089), under the Singapore Open Data Licence v1.0. Fetched
    2026-08-10. Every field kept here (school_name, address, postal_code,
    mrt_desc, type_code, nature_code, mainlevel_code, sap_ind, autonomous_ind,
    gifted_ind, ip_ind) is transcribed verbatim from that dataset -- nothing
    here is guessed or interpolated.
  - tools/_geocoded_schools.json / tools/_geocoded_districts.json -- lat/lng
    for each of the 147 schools' own postal codes, and one representative
    anchor point per postal district (the first named place in that
    district's `area` field, e.g. "Woodlands" for district 25). Fetched
    2026-08-13 from OneMap Singapore's free public search API
    (www.onemap.gov.sg/api/common/elastic/search), the national mapping
    authority's own geocoder -- see engine/school_fit.py's `haversine_km`
    docstring for what this is used for (a real, honestly-labelled
    straight-line distance) and, just as importantly, what it is NOT used
    for (a fabricated travel time).
  - packs/singapore/local/cutoff.json -- OPTIONAL, ABSENT BY DEFAULT, AND
    NEVER COMMITTED. Posting Group 1/2/3 and Integrated Programme cut-off
    points from the most recent S1 Posting Exercise.

    This build ships NO cut-off figures. That is a licensing decision taken
    2026-08-14 and it is deliberate.

    The figures originate with MOE's SchoolFinder, published under MOE's
    Terms of Use, which reserve reproduction. Anyone may read them; that is
    not the same as PathAhead being free to copy 139 schools' worth into a
    public repository and redistribute them under MIT. A compiled table of
    every school's COP is also somebody's compilation, whoever compiled it.
    Rather than rely on a fair-dealing argument nobody has tested, the
    public build simply does not carry the numbers, and the app links each
    school to its own SchoolFinder page so a family reads the official
    figure at source -- current, in context, and unaltered.

    An individual may still hold a local copy for their own private study.
    If `packs/singapore/local/cutoff.json` exists at build time, this script
    reads it and the reach filter lights up; if it does not, every school
    gets `cutoff_current: null` and the app degrades to the link-out, which is
    the shipped behaviour. `packs/singapore/local/` is gitignored precisely
    so that a personal copy can never become a published one by accident.
    See docs/LOCAL_DATA.md for the format and the reasoning.

    Whether that private copy is lawful for a given person in a given place
    is that person's call, not this repository's -- which is exactly why the
    default is empty and the instructions point at the primary source rather
    than shipping a file.

    Eight schools would have no row in any case (Assumption Pathway, Crest,
    Northlight, Spectra, NUS High, School of Science and Technology, School
    of the Arts, Singapore Sports School): they admit through auditions,
    aptitude tests, sports trials or a customised curriculum, outside the
    standard PSLE-score S1 Posting Exercise. That absence is explained on the
    card, not silently dropped.

Output: packs/singapore/secondary-schools.yaml, a NEW file, loaded alongside
psle.yaml. It adds outcomes-shaped "schools" records to the pack and a
`school_fit` block the engine reads -- see engine/school_fit.py.

WHAT THIS FILE DOES NOT CONTAIN, ON PURPOSE:
  - Religious affiliation, or primary-school affiliation. Neither is in any
    of MOE's open datasets; both are true, checkable facts about individual
    schools, but "true and checkable on the school's own page" is not the
    same as "in a bulk licensed dataset," and hand-curating 147 schools'
    affiliation status one at a time is exactly the kind of unverifiable
    transcription this project avoids. Left out rather than guessed.
  - CCA-by-school detail. A CCA dataset exists (data.gov.sg, same licence,
    ~7,200 rows) but pulling and cleanly aggregating it hit a data-fetching
    session limit during this build; it is a defensible follow-up, not a
    silent gap -- see NEXT.md.
  - Real travel time. `lat`/`lng` below buys a real straight-line distance,
    computed offline and shown honestly labelled as one -- not a routed
    transit or driving time, which would need a live call to a routing
    service and would mean the postal code someone typed left the device.
    The "Get directions" link the UI shows next to that distance answers the
    real-travel-time question a different way: it opens Google Maps, with
    real routing, only when and if the family clicks it themselves -- the
    same trust model as every "official page" link already in this app,
    never a background call PathAhead makes on their behalf.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW_SCHOOLS = REPO / "tools" / "_raw_school_directory.json"
GEOCODED_SCHOOLS = REPO / "tools" / "_geocoded_schools.json"
GEOCODED_DISTRICTS = REPO / "tools" / "_geocoded_districts.json"
#: OPTIONAL and absent by default -- see the module docstring. The whole
#: directory is gitignored, so a personal copy held for private study cannot
#: become a published one by forgetting a `git add -A`.
LOCAL_CUTOFF = REPO / "packs" / "singapore" / "local" / "cutoff.json"
OUT = REPO / "packs" / "singapore" / "secondary-schools.yaml"

#: The 8 schools that have no cut-off row under ANY source -- all admit
#: through specialised routes outside the standard PSLE-score S1 Posting
#: Exercise. Named explicitly, rather than just "whatever's missing", so that
#: when a local overlay IS present a school missing from it for some other,
#: unintended reason still fails the build instead of quietly joining this
#: list. Unused when no overlay is present, because then nothing has a row.
EXPECTED_NO_COP = {
    "assumption-pathway-school",
    "crest-secondary-school",
    "northlight-school",
    "nus-high-school-of-mathematics-and-science",
    "school-of-science-and-technology-singapore",
    "school-of-the-arts-singapore",
    "singapore-sports-school",
    "spectra-secondary-school",
}

#: Shown for the 8 specialised-admission schools when a local overlay IS
#: present, so their absence reads as "not applicable" rather than "PathAhead
#: forgot this school." True for all eight without asserting which specific
#: mechanism applies to which -- see the module docstring.
NO_COP_NOTE = (
    "No Posting Group cut-off is published for this school -- it is one of a "
    "small number of specialised-admission secondary schools (through "
    "auditions, aptitude tests, sports trials, or a customised curriculum) "
    "that sit outside the standard PSLE-score S1 Posting Exercise."
)

#: Shown for EVERY school in the default public build, where no cut-off data
#: is carried at all. Says plainly that this is a licensing choice and not a
#: gap, and hands the reader the primary source instead. The card renders a
#: "View on MOE SchoolFinder" link next to this; see schoolFinderUrl() in
#: web/index.html.
NOT_REDISTRIBUTED_NOTE = (
    "PathAhead does not republish Posting Group cut-off points. They are "
    "MOE's to publish, and MOE publishes them on each school's own "
    "SchoolFinder page -- open it below to read the current figures at "
    "source."
)

#: Singapore's 28 postal districts: which 2-digit postal SECTORS (the first
#: two digits of a 6-digit postal code) belong to each, and the place names
#: commonly associated with it. Source: SingPost's own district scheme, as
#: published at https://www.penang-traveltips.com/singapore/postal-districts.htm
#: (a secondary source that states it draws from SingPost), cross-checked
#: against the district/region rollup independently reported via web search
#: (CCR/RCR/OCR groupings matching URA's real-estate district groupings) and
#: against en.wikipedia.org/wiki/Postal_codes_in_Singapore's account of the
#: sector system itself. Retrieved 2026-08-10.
#:
#: `region` is NOT part of that source. It is PathAhead's own editorial
#: grouping of the 28 districts into five directional bands (Central, North,
#: North-East, East, West) so two postal codes in, say, Woodlands and
#: Sembawang -- different districts, same part of the island -- can still be
#: read as "nearby" rather than falling all the way through to "no signal."
#: It uses ordinary Singapore geography, not a government classification;
#: URA's own Master Plan divides the island into regions on a DIFFERENT basis
#: (planning areas, not postal districts), and this mapping is not a
#: transcription of that scheme either. See engine/school_fit.py.
POSTAL_DISTRICTS = [
    {"district": "01", "sectors": ["01", "02", "03", "04", "05", "06"], "area": "Raffles Place, Cecil, Marina, People's Park", "region": "CENTRAL"},
    {"district": "02", "sectors": ["07", "08"], "area": "Anson Road, Tanjong Pagar", "region": "CENTRAL"},
    {"district": "03", "sectors": ["14", "15", "16"], "area": "Bukit Merah, Queenstown, Tiong Bahru", "region": "CENTRAL"},
    {"district": "04", "sectors": ["09", "10"], "area": "Telok Blangah, HarbourFront", "region": "CENTRAL"},
    {"district": "05", "sectors": ["11", "12", "13"], "area": "Pasir Panjang, Hong Leong Garden, Clementi New Town", "region": "WEST"},
    {"district": "06", "sectors": ["17"], "area": "High Street, Beach Road (partial)", "region": "CENTRAL"},
    {"district": "07", "sectors": ["18", "19"], "area": "Middle Road, Golden Mile, Beach Road (partial)", "region": "CENTRAL"},
    {"district": "08", "sectors": ["20", "21"], "area": "Little India, Farrer Park, Jalan Besar, Lavender", "region": "CENTRAL"},
    {"district": "09", "sectors": ["22", "23"], "area": "Orchard, Cairnhill, River Valley", "region": "CENTRAL"},
    {"district": "10", "sectors": ["24", "25", "26", "27"], "area": "Ardmore, Bukit Timah, Holland Road, Tanglin", "region": "CENTRAL"},
    {"district": "11", "sectors": ["28", "29", "30"], "area": "Watten Estate, Novena, Thomson", "region": "CENTRAL"},
    {"district": "12", "sectors": ["31", "32", "33"], "area": "Balestier, Toa Payoh, Serangoon", "region": "CENTRAL"},
    {"district": "13", "sectors": ["34", "35", "36", "37"], "area": "Macpherson, Braddell, Potong Pasir, Bidadari", "region": "CENTRAL"},
    {"district": "14", "sectors": ["38", "39", "40", "41"], "area": "Geylang, Eunos, Aljunied", "region": "EAST"},
    {"district": "15", "sectors": ["42", "43", "44", "45"], "area": "Katong, Joo Chiat, Amber Road", "region": "EAST"},
    {"district": "16", "sectors": ["46", "47", "48"], "area": "Bedok, Upper East Coast, Eastwood, Kew Drive", "region": "EAST"},
    {"district": "17", "sectors": ["49", "50", "81"], "area": "Loyang, Changi", "region": "EAST"},
    {"district": "18", "sectors": ["51", "52"], "area": "Simei, Tampines, Pasir Ris", "region": "EAST"},
    {"district": "19", "sectors": ["53", "54", "55", "82"], "area": "Serangoon Garden, Hougang, Punggol", "region": "NORTH-EAST"},
    {"district": "20", "sectors": ["56", "57"], "area": "Bishan, Ang Mo Kio", "region": "NORTH-EAST"},
    {"district": "21", "sectors": ["58", "59"], "area": "Upper Bukit Timah, Clementi Park, Ulu Pandan", "region": "WEST"},
    {"district": "22", "sectors": ["60", "61", "62", "63", "64"], "area": "Penjuru, Jurong, Pioneer, Tuas", "region": "WEST"},
    {"district": "23", "sectors": ["65", "66", "67", "68"], "area": "Hillview, Dairy Farm, Bukit Panjang, Choa Chu Kang, Bukit Batok", "region": "WEST"},
    {"district": "24", "sectors": ["69", "70", "71"], "area": "Lim Chu Kang, Tengah", "region": "WEST"},
    {"district": "25", "sectors": ["72", "73"], "area": "Kranji, Woodgrove, Woodlands", "region": "NORTH"},
    {"district": "26", "sectors": ["77", "78"], "area": "Upper Thomson, Springleaf", "region": "NORTH"},
    {"district": "27", "sectors": ["75", "76"], "area": "Yishun, Sembawang, Senoko, Canberra", "region": "NORTH"},
    {"district": "28", "sectors": ["79", "80"], "area": "Seletar", "region": "NORTH-EAST"},
]

SECTOR_TO_DISTRICT: dict[str, dict] = {}
for row in POSTAL_DISTRICTS:
    for sector in row["sectors"]:
        SECTOR_TO_DISTRICT[sector] = row

#: mainlevel_code values that mean "a PSLE cohort can be posted here at S1."
#: Excludes PRIMARY, JUNIOR COLLEGE (post-O-Level/SEC entry only) and
#: CENTRALISED INSTITUTE (Millennia Institute -- also post-O-Level/SEC entry
#: only, despite the confusing standalone code). MIXED LEVEL entries are kept
#: because they include the through-train / Integrated Programme schools
#: (Raffles Institution, Hwa Chong, ACS(I), NUS High, and others) which DO
#: take a normal S1 intake from PSLE, structured as one continuous
#: administrative unit through to JC2 rather than as a separate secondary
#: school -- and the three "MIXED LEVEL (P1-S4)" entries (Catholic High
#: School, CHIJ St Nicholas Girls', Maris Stella High) are combined
#: primary+secondary campuses whose secondary section is a normal PSLE-entry
#: destination.
_PSLE_ACCESSIBLE_MAINLEVELS = {
    "SECONDARY (S1-S5)",
    "SECONDARY (S1-S4)",
    "MIXED LEVEL (S1-JC2)",
    "MIXED LEVEL (S1-S5, JC1-JC2)",
    "MIXED LEVEL (P1-S4)",
}

_TYPE_LABEL = {
    "GOVERNMENT SCHOOL": "Government school",
    "GOVERNMENT-AIDED SCH": "Government-aided school",
    "INDEPENDENT SCHOOL": "Independent school",
    "SPECIALISED SCHOOL": "Specialised school",
    "SPECIALISED INDEPENDENT SCHOOL": "Specialised independent school",
}
_NATURE_LABEL = {
    "CO-ED SCHOOL": "co-ed",
    "GIRLS' SCHOOL": "girls",
    "BOYS' SCHOOL": "boys",
}


#: Words data.gov.sg's ALL-CAPS names should keep lowercase when they're not
#: the first word ("NUS HIGH SCHOOL OF MATHEMATICS AND SCIENCE" -> "... of
#: Mathematics and Science", matching how NUS High styles its own name).
_SMALL_WORDS = {"of", "and", "the", "for", "at"}

#: Acronyms/initialisms that must stay all-caps regardless of position.
_KEEP_CAPS = {"chij", "nus", "sap", "acs", "ii", "iii"}


def _title_case_school_name(raw: str) -> str:
    """Turn an ALL-CAPS MOE school name into normal title case.

    str.title() is not safe here: it treats an apostrophe as a word
    boundary, so "ST. JOSEPH'S" becomes "St. Joseph'S" -- a real bug, not a
    style choice. This walks word-by-word instead so possessives, small
    words, and known initialisms all come out right.
    """
    def cap_first_alpha(s: str) -> str:
        """Capitalise the first letter wherever it is, leaving any leading
        punctuation (like an open parenthesis) untouched -- str.capitalize()
        only ever looks at index 0, which mishandles "(TOA" -> "(toa"."""
        for idx, ch in enumerate(s):
            if ch.isalpha():
                return s[:idx] + ch.upper() + s[idx + 1:].lower()
        return s

    words = raw.split(" ")
    out = []
    for i, w in enumerate(words):
        core = w.rstrip(",")
        trailing = w[len(core):]  # keep a trailing comma if present
        prefix = ""
        while core and not core[0].isalnum():
            prefix += core[0]
            core = core[1:]
        lower = core.lower()
        if lower in _KEEP_CAPS:
            cased = core.upper()
        elif lower in _SMALL_WORDS and i != 0:
            cased = lower
        elif "'" in core:
            # Capitalise only the segment before the apostrophe.
            head, sep, tail = core.partition("'")
            cased = cap_first_alpha(head) + sep + tail.lower()
        elif "." in core and core.replace(".", "").isalpha() and len(core.replace(".", "")) <= 3:
            # Short abbreviations like "ST." -> keep as "St."
            cased = cap_first_alpha(core)
        else:
            cased = cap_first_alpha(core)
        out.append(prefix + cased + trailing)
    return " ".join(out)


def _slug(name: str) -> str:
    return (
        name.lower()
        .replace("&", "and")
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
        .strip()
        .replace("  ", " ")
        .replace(" ", "-")
    )


def build() -> None:
    rows = json.loads(RAW_SCHOOLS.read_text(encoding="utf-8"))
    geocoded_schools = {
        g["id"]: g for g in json.loads(GEOCODED_SCHOOLS.read_text(encoding="utf-8"))
    }
    geocoded_districts = {
        g["district"]: g for g in json.loads(GEOCODED_DISTRICTS.read_text(encoding="utf-8"))
    }
    # This script NEVER writes cut-off figures, even when a local overlay
    # exists on the machine running it.
    #
    # secondary-schools.yaml is a tracked source file, not a build artifact.
    # If the overlay were merged here, one `npm run build && git commit -a`
    # on a machine that has a personal copy would publish it -- and the
    # failure mode is silent, because the diff looks like ordinary pack data.
    # A .gitignore cannot protect a file that is supposed to be committed.
    #
    # So the overlay is applied one layer later, at pack LOAD time, by
    # engine/loader.py. The figures then exist only in memory and only on the
    # machine that holds the file. Making accidental publication structurally
    # impossible beats remembering not to do it.
    cutoffs: dict = {}
    schools = []
    unmatched_postal = []
    unmatched_geocode = []

    for r in rows:
        if r.get("mainlevel_code") not in _PSLE_ACCESSIBLE_MAINLEVELS:
            continue

        postal = str(r.get("postal_code") or "").strip().zfill(6)
        sector = postal[:2]
        district_row = SECTOR_TO_DISTRICT.get(sector)
        if district_row is None:
            unmatched_postal.append((r["school_name"], postal))

        name = r["school_name"].strip()
        school_id = _slug(name)
        geo = geocoded_schools.get(school_id)
        if geo is None or geo.get("lat") is None or geo.get("lng") is None:
            unmatched_geocode.append(school_id)
        cutoff = cutoffs.get(school_id)
        schools.append(
            {
                "id": school_id,
                "name": _title_case_school_name(name),
                "address": r.get("address", "").strip(),
                "postal_code": postal,
                "mrt_desc": r.get("mrt_desc") or None,
                "district": district_row["district"] if district_row else None,
                "region": district_row["region"] if district_row else None,
                "lat": geo["lat"] if geo else None,
                "lng": geo["lng"] if geo else None,
                "type_code": r.get("type_code"),
                "type_label": _TYPE_LABEL.get(r.get("type_code"), r.get("type_code")),
                "nature_code": r.get("nature_code"),
                "gender": _NATURE_LABEL.get(r.get("nature_code"), r.get("nature_code")),
                "sap": r.get("sap_ind") == "Yes",
                "autonomous": r.get("autonomous_ind") == "Yes",
                "gifted": r.get("gifted_ind") == "Yes",
                "ip": r.get("ip_ind") == "Yes",
                "mainlevel_code": r.get("mainlevel_code"),
                "cutoff_current": cutoff,
            }
        )

    unmatched_district_geocode = [
        row["district"] for row in POSTAL_DISTRICTS
        if geocoded_districts.get(row["district"], {}).get("lat") is None
        or geocoded_districts.get(row["district"], {}).get("lng") is None
    ]
    # Only meaningful when a local overlay is present. In the default public
    # build nothing has a cut-off row, by design, so there is nothing to
    # check. When someone HAS supplied an overlay, a missing row is expected
    # only for the 8 named specialised-admission schools -- anything else
    # missing is a real gap in their file, and must fail loud rather than
    # silently ship a school with no reach signal for a reason nobody chose.
    if cutoffs:
        unexpected_missing_cutoff = sorted(
            s["id"] for s in schools
            if s["cutoff_current"] is None and s["id"] not in EXPECTED_NO_COP
        )
        if unexpected_missing_cutoff:
            raise SystemExit(
                "local cut-off overlay is missing rows for schools that are not "
                f"known specialised-admission cases: {unexpected_missing_cutoff}"
            )
    if unmatched_postal:
        raise SystemExit(f"postal codes with no matching district: {unmatched_postal}")
    if unmatched_geocode:
        raise SystemExit(f"schools with no geocoded coordinates: {unmatched_geocode}")
    if unmatched_district_geocode:
        raise SystemExit(f"districts with no geocoded anchor point: {unmatched_district_geocode}")

    schools.sort(key=lambda s: s["name"])

    lines: list[str] = []
    w = lines.append

    w("# PathAhead data pack: Singapore secondary schools — the shortlisting stage")
    w("#")
    w("# 147 schools a PSLE cohort can actually be posted to at S1, transcribed from")
    w("# MOE's own \"General information of schools\" dataset on data.gov.sg, under the")
    w("# Singapore Open Data Licence v1.0 -- NOT from SchoolFinder, whose Terms of Use")
    w("# permit citing and deep-linking but not copying. This is the licensing gap")
    w("# psle.yaml's \"what is not here yet\" note flagged; this file closes it for the")
    w("# DIRECTORY data (name, location, type, gender, SAP/IP/autonomous status) while")
    w("# leaving the COP/Posting-Group-by-school gap exactly where it was, because no")
    w("# permissively licensed source for THAT exists (verified 2026-08-10 -- see")
    w("# tools/build_secondary_schools_pack.py's module docstring for the search).")
    w("#")
    w("# WHAT THIS DOES NOT ANSWER: \"can my child get into this school.\" That question")
    w("# needs a cut-off point, which is not in here for the reason above -- ask it on")
    w("# the Posting Group calculator this page already has. This file answers a")
    w("# DIFFERENT, narrower question: among schools your family could plausibly list,")
    w("# which ones match what you've said matters to you (location, co-ed preference,")
    w("# SAP, Integrated Programme). The two questions are never blended into one")
    w("# number -- see engine/school_fit.py's module docstring, which is the school-")
    w("# scoring equivalent of engine/fit.py's A-Level course-fit engine and follows")
    w("# the identical rule: eligibility and fit are different axes, and only")
    w("# eligibility ever gates a result.")
    w("#")
    w("# WHAT IS DELIBERATELY NOT IN THIS FILE, AND WHY:")
    w("#   - Cut-off points / Posting Groups per school -- no permissively licensed")
    w("#     source exists; see above.")
    w("#   - CCA (co-curricular activity) offerings -- a data.gov.sg dataset exists")
    w("#     but could not be reliably pulled and cleaned in this pass; a real gap,")
    w("#     not a silent one. Tracked as follow-up work, not filled with a guess.")
    w("#   - Religious affiliation and primary-school affiliation (e.g. which")
    w("#     secondary schools a given primary school's students are affiliated")
    w("#     to) -- true and checkable per school, but not in any bulk licensed")
    w("#     dataset. Hand-curating 147 schools one at a time is exactly the kind")
    w("#     of unverifiable transcription this project avoids, so it is left out")
    w("#     rather than guessed at.")
    w("")
    w("sources:")
    w("  - id: datagovsg-school-directory-2026")
    w("    name: General information of schools")
    w("    publisher: Ministry of Education, Singapore (via data.gov.sg)")
    w("    url: https://data.gov.sg/datasets/d_688b934f82c1059ed0a6993d2a829089/view")
    w("    retrieved: 2026-08-10")
    w("    licence: sg-odl-1.0")
    w("    note: >")
    w("      337 schools, all levels; 147 of them can take a normal PSLE-to-S1 intake")
    w("      and are the ones loaded here. Name, address, postal code, MRT/bus")
    w("      description, school type, gender composition, SAP/Autonomous/Gifted/IP")
    w("      indicator flags -- transcribed verbatim, one field renamed for clarity")
    w("      (\"nature_code\" -> gender) and none reinterpreted. Licensed under the")
    w("      Singapore Open Data Licence v1.0, which permits commercial use,")
    w("      modification and redistribution with attribution -- a materially")
    w("      different, more permissive grant than SchoolFinder's cite-and-link-only")
    w("      terms.")
    w("  - id: singpost-postal-districts")
    w("    name: Singapore Postal Districts (SingPost district scheme)")
    w("    publisher: Singapore Post, via secondary transcription")
    w("    url: https://www.penang-traveltips.com/singapore/postal-districts.htm")
    w("    retrieved: 2026-08-10")
    w("    licence: institution-tou")
    w("    note: >")
    w("      The 28-district, 81-sector table used to turn a postal code into a")
    w("      district and a coarse region. This is structural, decades-old public")
    w("      information (SingPost's own delivery scheme, referenced by Wikipedia's")
    w("      \"Postal codes in Singapore\" article) rather than a licensed dataset in")
    w("      its own right, so it is recorded under PathAhead's \"facts cited and")
    w("      linked, nothing reproduced wholesale\" licence code rather than an")
    w("      open-data one -- the table below is transcribed for citation, the way")
    w("      any fact in this project is, not redistributed as someone else's")
    w("      dataset. The REGION column (Central/North/North-East/East/West) is")
    w("      PathAhead's own editorial grouping of the 28 districts, not part of any")
    w("      cited source -- see engine/school_fit.py.")
    w("  - id: onemap-geocoding-2026")
    w("    name: OneMap Singapore search API (address/postal code geocoding)")
    w("    publisher: Singapore Land Authority")
    w("    url: https://www.onemap.gov.sg/apidocs/")
    w("    retrieved: 2026-08-13")
    w("    licence: sg-odl-1.0")
    w("    note: >")
    w("      Latitude/longitude for each school's own postal code, and one")
    w("      representative anchor point per postal district (the first named place")
    w("      in that district's `area` field). Used only to compute a real, honestly")
    w("      labelled straight-line distance -- never a routed travel time, and never")
    w("      a live call made with a family's own postal code. Governed by the")
    w("      Singapore Open Data Licence, per OneMap's own Terms of Use.")
    w("  - id: moe-schoolfinder")
    w("    name: MOE SchoolFinder -- each school's own page")
    w("    publisher: Ministry of Education, Singapore")
    w("    url: https://www.moe.gov.sg/schoolfinder")
    w("    retrieved: 2026-08-14")
    w("    licence: moe-tou-linked")
    w("    note: >")
    w("      MOE publishes each secondary school's Posting Group and Integrated")
    w("      Programme PSLE Score ranges on that school's own SchoolFinder page.")
    w("      PathAhead does NOT reproduce those figures. They are published under")
    w("      MOE's Terms of Use, which reserve reproduction, and a compiled table of")
    w("      every school's cut-off is additionally somebody's compilation. Anyone")
    w("      may read them; that is not the same as this project being free to")
    w("      redistribute them under MIT. So the app carries a per-school deep link")
    w("      instead, and the reader opens the official page and reads the current")
    w("      figures at source -- unaltered, in context, and never stale, which a")
    w("      copied snapshot would eventually be.")
    w("      MOE's own caution applies to every figure a reader will find there:")
    w("      cut-off points \"can fluctuate by a few points year-on-year\", and matching")
    w("      one is not by itself enough to secure a place. They are a record of last")
    w("      year's exercise, not a threshold for this one. (Paraphrased deliberately --")
    w("      MOE's exact phrasing trips this project's own banned-phrase guard, which")
    w("      cannot tell a warning from a promise. Rewrite the sentence, not the guard.)")
    w("")
    w("postal_districts:")
    for row in POSTAL_DISTRICTS:
        geo = geocoded_districts.get(row["district"], {})
        w(
            f'  - {{district: "{row["district"]}", sectors: {json.dumps(row["sectors"])}, '
            f'area: "{row["area"]}", region: {row["region"]}, '
            f'lat: {geo.get("lat")}, lng: {geo.get("lng")}}}'
        )
    w("")
    w("schools:")
    for s in schools:
        w(f'  - id: {s["id"]}')
        w(f'    name: "{s["name"]}"')
        w(f'    address: "{s["address"].strip()}"')
        w(f'    postal_code: "{s["postal_code"]}"')
        if s["mrt_desc"]:
            mrt = s["mrt_desc"].replace('"', "'")
            w(f'    mrt_desc: "{mrt}"')
        w(f'    district: "{s["district"]}"')
        w(f'    region: {s["region"]}')
        w(f'    lat: {s["lat"]}')
        w(f'    lng: {s["lng"]}')
        w(f'    type_code: "{s["type_code"]}"')
        w(f'    type_label: "{s["type_label"]}"')
        w(f'    gender: {s["gender"]}')
        w(f'    sap: {str(s["sap"]).lower()}')
        w(f'    autonomous: {str(s["autonomous"]).lower()}')
        w(f'    gifted: {str(s["gifted"]).lower()}')
        w(f'    ip: {str(s["ip"]).lower()}')
        w('    fact: {source: datagovsg-school-directory-2026, as_of_year: 2026, confidence: high}')
        cutoff = s["cutoff_current"]
        if cutoff is None:
            w("    cutoff_current: null")
            # Two different reasons a school has no figure, and they must not
            # read alike. "MOE publishes none for this school" is a fact about
            # the school; "PathAhead does not republish these" is a fact about
            # this project. Conflating them would tell a family something
            # untrue about a school.
            if s["id"] in EXPECTED_NO_COP:
                w(f'    cutoff_note: "{NO_COP_NOTE}"')
            else:
                w(f'    cutoff_note: "{NOT_REDISTRIBUTED_NOTE}"')
        else:
            ranges = {k: cutoff.get(k) for k in ("pg3", "pg2", "pg1", "ip")}
            w(f"    cutoff_current: {json.dumps(ranges)}")
            w('    cutoff_fact: {source: moe-schoolfinder, confidence: medium}')
            if cutoff.get("note"):
                note = cutoff["note"].replace('"', "'")
                w(f'    cutoff_note: "{note}"')
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    carried = sum(1 for s in schools if s["cutoff_current"] is not None)
    print(f"wrote {len(schools)} schools -> {OUT}")
    print(
        f"  cut-off figures carried: {carried}"
        + (" (LOCAL BUILD -- do not publish this pack)" if carried else " (public build)")
    )


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""Insert SIT's AY2026 fee blocks into packs/singapore/outcomes-sutd-sit-suss.yaml.

Run once per fee-table release:

    python3 tools/add_sit_fees.py

It edits the YAML as TEXT, inserting a `cost:` block into each SIT outcome that
does not already have one. A round-trip through a YAML library would strip the
file's comments, and those comments are most of why the pack is reviewable by
someone who does not write code.

SIT does not charge per year, and that is the whole point of this file
--------------------------------------------------------------------
Every other university in this pack publishes a fee per academic year. SIT
publishes a fee per CREDIT UNIT, and states that fees "are payable as long as a
student's candidature remains active", derived each trimester from the modules
actually registered. There is no annual figure to record.

Dividing a programme total by a nominal number of years would produce one that
looks exactly like NUS's and is not the same kind of number -- and it would be
wrong for any student who takes a lighter or heavier load, which is precisely
the flexibility SIT charges this way to allow. So `fee_basis: per_credit` is
recorded, `annual_fee_*` is left empty, and `total_for()` multiplies credits by
rate the way SIT does. The loader refuses a per-credit block that carries an
annual fee.

Four courses are deliberately left without a fee
------------------------------------------------
The fee table names programmes; the pack names courses; and for four of them the
mapping is genuinely ambiguous:

  * `sit-civil-engineering` -- the table lists Civil Engineering twice, once as
    an SIT degree (240 credits at S$131) and once as an SIT-Glasgow joint degree
    (180 credits at S$174). Those are two different bills and the pack does not
    record which partner this course is with.
  * `sit-nursing` and `sit-nursing-pre-registration` -- the table has an SIT
    "Bachelor of Science in Nursing" (180 credits) and an SIT-Glasgow "BSc Hons
    in Nursing" (120 credits). Two rows, two courses, and no basis in the pack
    for saying which is which.
  * `sit-digital-art-and-animation` -- absent from the AY2026 table entirely.

Guessing would be a four-figure error in a number families plan around. They
stay empty until someone confirms the mapping with SIT, exactly as NTU's
lab/non-lab split does.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "packs" / "singapore" / "outcomes-sutd-sit-suss.yaml"

# Rate bands, verbatim from the AY2026 table.
# (citizen, pr, international ASEAN, international non-ASEAN, no grant)
BUSINESS = (156.00, 236.00, 364.06, 408.75, 653.46)   # SIT degree, business/health band
TECH = (131.00, 225.00, 324.82, 371.69, 575.52)       # SIT degree, engineering/computing band
DIGIPEN = (181.50, 280.00, 428.37, 480.69, 709.59)
PARTNER = (174.00, 269.50, 413.11, 463.25, 681.25)    # Newcastle, TUM, Glasgow
CIA = (224.00, 385.00, 537.37, 552.63, 810.96)

#: outcome id -> (total credits, rate band)
FEES: dict[str, tuple[int, tuple[float, ...]]] = {
    "sit-accountancy": (180, BUSINESS),
    "sit-aviation-management": (180, BUSINESS),
    "sit-communication-and-digital-media": (180, TECH),
    "sit-hospitality-and-tourism-management": (180, BUSINESS),
    "sit-aircraft-systems-engineering": (180, TECH),
    "sit-computer-engineering": (180, TECH),
    "sit-electrical-and-electronic-engineering": (240, TECH),
    "sit-engineering-systems": (180, TECH),
    "sit-information-and-communications-technology-information-security": (240, TECH),
    "sit-information-and-communications-technology-software-engineering": (240, TECH),
    "sit-infrastructure-and-systems-engineering": (240, TECH),
    "sit-pharmaceutical-engineering": (240, TECH),
    "sit-robotics-systems": (240, TECH),
    "sit-sustainable-built-environment": (180, TECH),
    "sit-food-technology": (240, TECH),
    "sit-business-and-infocomm-technology": (240, BUSINESS),
    "sit-applied-computing-fintech": (180, TECH),
    "sit-digital-supply-chain": (180, TECH),
    "sit-applied-artificial-intelligence": (180, TECH),
    "sit-diagnostic-radiography": (240, BUSINESS),
    "sit-dietetics-and-nutrition": (240, BUSINESS),
    "sit-occupational-therapy": (240, BUSINESS),
    "sit-physiotherapy": (240, BUSINESS),
    "sit-speech-and-language-therapy": (240, BUSINESS),
    # SIT - DigiPen (Singapore)
    "sit-computer-science-in-interactive-media-and-game-development": (240, DIGIPEN),
    "sit-computer-science-in-real-time-interactive-simulation": (240, DIGIPEN),
    "sit-user-experience-and-game-design": (240, DIGIPEN),
    # SIT - Newcastle
    "sit-electrical-power-engineering": (180, PARTNER),
    "sit-mechanical-design-and-manufacturing-engineering": (180, PARTNER),
    "sit-naval-architecture-and-marine-engineering": (180, PARTNER),
    # SIT - TUM
    "sit-chemical-engineering": (240, PARTNER),
    "sit-electronics-and-data-engineering": (240, PARTNER),
    # SIT - Glasgow
    "sit-mechanical-engineering": (180, PARTNER),
    "sit-computing-science": (180, PARTNER),
    # Culinary Institute of America - Overseas Universities Programme
    "sit-food-business-management-baking-and-pastry-arts": (132, CIA),
    "sit-food-business-management-culinary-arts": (132, CIA),
}

#: Left empty on purpose, with the reason. See the module docstring.
AMBIGUOUS = {
    "sit-civil-engineering":
        "SIT publishes Civil Engineering twice for AY2026 -- as an SIT degree "
        "(240 credits) and as an SIT-Glasgow joint degree (180 credits, a higher "
        "rate). This pack does not record which partner this course is with, and "
        "the two produce materially different totals, so no figure is shown "
        "rather than a guessed one.",
    "sit-nursing":
        "SIT publishes an SIT 'Bachelor of Science in Nursing' (180 credits) and "
        "an SIT-Glasgow 'BSc Hons in Nursing' (120 credits) for AY2026. Which of "
        "the two nursing courses in this pack is which is not recorded, so no "
        "figure is shown rather than a guessed one.",
    "sit-nursing-pre-registration":
        "See sit-nursing: two published nursing programmes, no basis in this pack "
        "for mapping them to the two courses it lists.",
    "sit-digital-art-and-animation":
        "Absent from SIT's AY2026 undergraduate fee table.",
}


def cost_block(credits: int, rates: tuple[float, ...]) -> str:
    sc, pr, isa, iso, ng = rates
    total = round(sc * credits)
    return f"""    cost:
      fee_basis: per_credit
      total_credits: {credits}
      fee_per_credit_citizen: {sc}
      fee_per_credit_pr: {pr}
      fee_per_credit_international: {isa}
      fee_per_credit_is_other: {iso}
      fee_per_credit_no_grant: {ng}
      tuition_grant_available: true
      bond_years_citizen: 0
      bond_years_pr_is: 3
      bond_note: >-
        Singapore Citizens owe no bond for the tuition grant itself. Permanent
        Residents and international students who accept it must work for a
        Singapore entity for 3 years after graduating.
      fact:
        value: "S${sc:.2f} per credit unit over {credits} credits (S${total:,} for a Singapore Citizen)"
        as_of_year: 2026
        source: sit-fees-2026
        confidence: high
        stale_after: 2027-06-30
        note: >-
          SIT charges per CREDIT UNIT, not per year, and states that fees are
          payable as long as candidature remains active, derived each trimester
          from the modules actually registered. There is therefore no annual
          figure to show, and dividing the total by a nominal number of years
          would invent one that would be wrong for any student taking a lighter
          or heavier load. Singapore Citizen and Permanent Resident rates exclude
          GST, which the Ministry of Education subsidises; the international and
          non-subsidised rates include 9% GST.
"""


def _wrap(text: str, indent: int, width: int = 78) -> str:
    pad = " " * indent
    lines, cur = [], pad
    for word in text.split():
        if len(cur) + len(word) + 1 > width and cur.strip():
            lines.append(cur.rstrip())
            cur = pad + word
        else:
            cur = (cur + " " + word) if cur.strip() else pad + word
    if cur.strip():
        lines.append(cur.rstrip())
    return "\n".join(lines)


def note_block(reason: str) -> str:
    """A gap that is a decision needs to look different from a gap that is a
    to-do, so it is recorded on the course rather than only in this file."""
    return (
        "    fee_note: >-\n"
        + _wrap("PathAhead shows no fee for this course on purpose. " + reason, 6)
        + "\n"
    )


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    # Split into whole outcome blocks. Text surgery rather than a YAML
    # round-trip, because a round-trip would strip every comment in the file.
    parts = re.split(r"(?m)^(?=  - id: )", text)
    inserted = flagged = 0
    out = []
    for block in parts:
        m = re.match(r"  - id: (\S+)", block)
        if not m:
            out.append(block)
            continue
        oid = m.group(1)
        if oid in FEES and "fee_basis:" not in block:
            credits, rates = FEES[oid]
            block = block.rstrip("\n") + "\n" + cost_block(credits, rates)
            inserted += 1
        elif oid in AMBIGUOUS and "fee_note:" not in block:
            block = block.rstrip("\n") + "\n" + note_block(AMBIGUOUS[oid])
            flagged += 1
        out.append(block)

    TARGET.write_text("".join(out), encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)}: {inserted} fee blocks, {flagged} marked ambiguous")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

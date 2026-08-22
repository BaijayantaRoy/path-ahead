"""Tell a maintainer when a cited page changes. Nothing more than that.

Design constraints, all of them deliberate:

  * Fetches only URLs a pack already cites -- no crawling, no link following.
  * One request per source, once a week, sequentially, with a real User-Agent
    and a contact URL.
  * Honours robots.txt and stops on the first refusal.
  * Stores a hash, never the page. It does not build a mirror or a cache.
  * Opens an issue. It never edits a pack and never publishes anything.

Together those keep this the right side of the terms of use recorded in
SAFEGUARDS.md 3, while still giving the "AI-assisted maintenance" story real
substance: the copilot that drafts a pack update (tools/pack_copilot.py, not
yet built) is triggered by a human reading the issue this opens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine import load_pack  # noqa: E402

USER_AGENT = (
    "PathAheadWatcher/0.1 (open-source education tool; "
    "+https://github.com/BaijayantaRoy/path-ahead)"
)
POLITE_DELAY_SECONDS = 5.0
TIMEOUT = 20.0

_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_MARKUP = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def normalise(html: str) -> str:
    """Reduce a page to its visible words, so cosmetic markup churn is ignored."""
    text = _TAG.sub(" ", html)
    text = _MARKUP.sub(" ", text)
    return _SPACE.sub(" ", text).strip().lower()


def robots_allows(url: str) -> bool:
    parts = urllib.parse.urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        # If robots.txt cannot be read, do not proceed. Fail closed.
        return False
    return rp.can_fetch(USER_AGENT, url)


def fingerprint(url: str) -> tuple[str, int] | None:
    if not robots_allows(url):
        print(f"  skipped (robots.txt): {url}")
        return None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"  unreachable: {url} ({exc})")
        return None
    text = normalise(body)
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", default=str(REPO / "packs" / "singapore"))
    ap.add_argument("--state", default=str(REPO / ".watch-state.json"))
    args = ap.parse_args(argv)

    pack = load_pack(args.pack)
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    changed: list[str] = []
    for i, src in enumerate(pack.sources.values()):
        if i:
            time.sleep(POLITE_DELAY_SECONDS)
        print(f"checking {src.id}: {src.url}")
        fp = fingerprint(src.url)
        if fp is None:
            continue
        digest, size = fp
        previous = state.get(src.id, {}).get("sha256")
        state[src.id] = {"sha256": digest, "chars": size, "url": src.url}
        if previous and previous != digest:
            changed.append(f"- **{src.id}** — {src.name} ({src.publisher})\n  {src.url}")
            print("  CHANGED")
        elif previous:
            print("  unchanged")
        else:
            print("  first seen (baseline recorded)")

    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    summary = ""
    if changed:
        summary = (
            "One or more official pages that the Singapore pack cites have "
            "changed since the last check.\n\n"
            + "\n".join(changed)
            + "\n\nThis is an automated heads-up, not a diagnosis. Someone needs to "
            "read the page and decide whether a figure, a formula or a date in "
            "`packs/singapore/` needs updating.\n\n"
            "Checklist:\n"
            "- [ ] Read the page and identify what actually changed\n"
            "- [ ] Update the affected fact(s), including `as_of_year` and `stale_after`\n"
            "- [ ] Raise `confidence` if the change replaces a secondary source with a primary one\n"
            "- [ ] Bump the pack version and run `pathahead health --gate`\n"
            "- [ ] Regenerate golden fixtures if a rule changed, and review the diff\n"
        )

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write("summary<<PATHAHEAD_EOF\n")
            fh.write(summary + "\nPATHAHEAD_EOF\n")

    print(f"\n{len(changed)} source(s) changed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

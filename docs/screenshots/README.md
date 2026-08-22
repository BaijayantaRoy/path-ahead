# Screenshots

Referenced by the main [README.md](../../README.md#see-it). Real screenshots of the
running app, taken from a local install with `PathAhead_Start.bat`, cropped to the
viewport (no browser chrome).

| File | Shows |
|---|---|
| `home.png` | The front door: the three stage doors (PSLE / O-Level / A-Level) |
| `psle-landing.png` | The PSLE landing page, before a score is typed |
| `psle-shortlist.png` | The PSLE school shortlist — every school shown by default, filters that hide, never rank |
| `data-sources.png` | The Sources page — every figure dated, cited, and linked to where it came from |
| `alevel-start.png` | A-Level: the one question that decides which rulebook applies |
| `alevel-personalise.png` | A-Level: the optional personalisation questions |

To refresh one: `PathAhead_Install.bat` then `PathAhead_Start.bat`, open the page,
screenshot the viewport only (crop out the browser's own address bar and any OS
chrome), and overwrite the file above with the same name.

Note: `psle-shortlist.png` was captured on a machine with a personal, local-only
cut-off data overlay in place (see [docs/LOCAL_DATA.md](../LOCAL_DATA.md)) — that is
why the screenshot shows real Posting Group figures on the school card. A clean
checkout of this repository never ships that data; every school card instead links
out to the school's own MOE SchoolFinder page. The screenshot is honest about what
the *feature* looks like when a user has chosen to keep their own copy — it is not
data this repository redistributes.

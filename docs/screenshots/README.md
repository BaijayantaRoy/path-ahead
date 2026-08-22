# Screenshots

Referenced by the main [README.md](../../README.md#see-it). Real screenshots of the
running app, taken from a local install with `PathAhead_Start.bat`, cropped to the
viewport (no browser chrome).

| File | Shows |
|---|---|
| `home.png` | The front door: the three stage doors (PSLE / O-Level / A-Level) |
| `psle-landing.png` | The PSLE landing page, before a score is typed |
| `psle-shortlist.png` | The PSLE school shortlist — every school shown by default, cut-off figures linked out to MOE rather than reproduced |
| `data-sources.png` | The Sources page — every figure dated, cited, and linked to where it came from |
| `alevel-start.png` | A-Level: the one question that decides which rulebook applies |
| `alevel-personalise.png` | A-Level: the optional personalisation questions |

To refresh one: `PathAhead_Install.bat` then `PathAhead_Start.bat`, open the page,
screenshot the viewport only (crop out the browser's own address bar and any OS
chrome), and overwrite the file above with the same name.

If you keep a local-only cut-off overlay (docs/LOCAL_DATA.md), move it aside and
**rebuild** before capturing anything that shows a school card. `PathAhead_Start.bat`
only runs `serve` -- it does not recompile the pack, so moving the overlay alone
changes nothing and the browser keeps serving the figures:

    move packs\singapore\local packs\singapore\local.aside
    .venv\Scripts\python.exe app\cli.py build --out web\data

Then hard-refresh (Ctrl+Shift+R) and confirm the count is zero before screenshotting:

    .venv\Scripts\python.exe -c "import json;p=json.load(open('web/data/singapore.json',encoding='utf-8'));print(sum(1 for s in p['schools'] if s.get('cutoff_2025')),'schools carry cut-offs')"

Restore afterwards by moving the folder back and rebuilding again.

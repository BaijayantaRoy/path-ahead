# Security Policy

## The shape of the attack surface

PathAhead has no server, no account, no database, and no network call the
app itself makes — see [SAFEGUARDS.md §1](SAFEGUARDS.md). That removes whole
classes of vulnerability by construction, but it does not remove all of them.
What is actually in scope:

- **The browser app** (`web/index.html`) — a single self-contained file. The
  main risk here is XSS: pack data (school names, course descriptions, source
  notes) is rendered from YAML that a fork's maintainer controls, so it must
  always be escaped, never injected as raw HTML. `tools/check_static.mjs`
  and `tools/check_ui.mjs` assert this in CI; a bypass of that assertion is a
  real finding.
- **The Content-Security-Policy.** `web/index.html` carries its own
  `<meta http-equiv="Content-Security-Policy">` so the guarantee survives
  GitHub Pages, a USB stick, or a `file://` open, not only `tools/serve.py`.
  A change that weakens `default-src 'self'` or widens it beyond the
  documented allowlist in `.github/workflows/ci.yml` is a security
  regression, not a style choice.
- **The desktop build** (`desktop.py`, built via `tools/build_desktop.py`).
  It binds to `127.0.0.1` only — never `0.0.0.0` — so it is not reachable
  from another device on the same network. `tests/test_desktop.py` asserts
  this directly. The released binaries are **not code-signed** (that costs
  money this project does not take); verify `SHA256SUMS.txt` on the release
  page before running one, and prefer running from source if you are not
  comfortable with an unsigned binary.
- **Supply chain.** Python and Node dependencies are pinned in
  `requirements*.txt` and `package.json`. Report a known-vulnerable pinned
  version like any other bug.
- **The data itself.** A wrong or stale figure is a correctness bug, not a
  security one — report it as described in [CONTRIBUTING.md](CONTRIBUTING.md).
  A figure that could deceive someone into an unsafe decision (not merely
  outdated, but actively misleading) should be reported the way a security
  issue would be: promptly, and with the word "urgent" in the title.

## Reporting a vulnerability

Please use GitHub's private
[**Report a vulnerability**](https://github.com/BaijayantaRoy/path-ahead/security/advisories/new)
flow rather than a public issue, so a fix can ship before the details are
public. If that is not available to you, open an issue with the specific
technical details omitted and a request to be contacted privately.

Include what you found, how to reproduce it, and what you think the impact
is. This is a single-maintainer, unfunded, non-commercial project — there is
no bug bounty, but every report is read and taken seriously, and you will be
credited in the fix unless you ask not to be.

## What is explicitly out of scope

- Reports that assume PathAhead has a server, a database, or user accounts —
  it has none of these, by design.
- Reports about the accuracy of a third-party source PathAhead cites (MOE,
  a university, data.gov.sg). Report those to the publisher; PathAhead will
  update the citation once the source itself changes.
- Reports against the unofficial nature of the project itself — see
  [LICENSE](LICENSE) and the [Disclaimers & limitations](README.md#disclaimers--limitations)
  section of the README.

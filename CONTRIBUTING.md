# Contributing to WebBehaviorLab

Thank you for helping make WebBehaviorLab a better educational tool!
This document explains how to contribute code, docs, or bug reports.

## Code of Conduct

Be kind and constructive. We welcome newcomers — questions are good
questions here.

## 1. Fork and branch

```bash
# On GitHub: fork nexo-rei/webbehaviorlab, then:
git clone https://github.com/YOUR-USERNAME/webbehaviorlab.git
cd webbehaviorlab
git remote add upstream https://github.com/nexo-rei/webbehaviorlab.git
git checkout -b feat/my-feature     # or fix/my-bugfix, docs/my-topic
```

Use a clear branch name prefixed with `feat/`, `fix/`, or `docs/`.

## 2. Set up your environment

```bash
bash install.sh          # creates .venv, installs deps, runs a health check
source .venv/bin/activate
pytest                   # all tests must pass before you commit
```

Requirements: Python 3.8+, pip. Termux and plain Linux are both supported.

## 3. Run the tests

```bash
pytest                       # full suite (fast; no browser needed)
pytest tests/test_limiter.py # a single file
pytest -k "hard_limit"       # a single test
```

The suite covers the session limiter, URL validator, configuration
clamping, metrics, reports, logging hygiene, and the engine (via a fake
browser plus a real localhost server), so it runs anywhere — no Chromium
required.

**Every PR must keep the suite green.** If you add a feature, add tests:
new validator rules, new limiter behavior, new report fields, and new
actions all need coverage.

## 4. Make your change

### Coding standards

- Python 3.8+ compatible (no walrus-in-f-strings tricks, no `X | Y` type
  unions in annotations).
- Type hints where practical; docstrings on public functions and modules.
- PEP 8 formatting, meaningful names, small functions.
- No duplicated code — factor helpers into `utils/`.
- Imports must be clean (no unused imports; run `python -m pyflakes src/`).
- No hard-coded secrets, paths, or terminal widths.
- Comments explain *why*, not *what*.

### Documentation requirements

- User-visible change → update the relevant file in `docs/` **and** the
  README section it affects.
- Behavior/config change → update `config/default.json` docs in
  `docs/configuration.md` and add a `CHANGELOG.md` entry under
  *Unreleased*.
- New module → add a module docstring explaining its responsibility.

### The safety review (non-negotiable)

WebBehaviorLab is an authorized-testing education tool. Contributions will
be **rejected** if they:

- increase the hard session limit or weaken its enforcement,
- add proxy rotation, CAPTCHA solving, bot-detection evasion, fingerprint
  spoofing, or traffic-generation features,
- log or store credentials, cookies, or tokens,
- remove authorization checks or safety prompts,
- execute downloaded scripts or add risky shell calls.

If your idea could be misused, discuss it in an issue **before**
implementing; we will look for the safe educational alternative together.

## 5. Commit and submit

Write clear commit messages:

```text
fix(limiter): clamp settings-file values before validation

Settings loaded from disk could briefly hold values above the hard
maximum before clamping; validation now happens during load.
```

Then:

```bash
git add <files>
git commit -m "feat(ui): add compact-mode history table"
git push -u origin feat/my-feature
```

Open a pull request against `main` describing:

- **What** changed and **why**
- How you tested it (commands, screenshots for UI changes)
- Any docs you updated

A maintainer will review, possibly request changes, and merge.

## 6. Reporting bugs

Open an issue with:

1. WebBehaviorLab version (`webbehavior version`)
2. Environment (Termux or Linux, Python version)
3. Exact steps to reproduce
4. What you expected vs. what happened
5. Any Error ID shown (e.g. `ERR-7A21`) — the diagnostic log at
   `~/.webbehavior/logs/diagnostics/` helps too; it is already sanitized,
   but glance at it before posting

Never include real passwords, tokens, or targets you are not authorized to
discuss in an issue.

## 7. Licensing

By contributing, you agree your contributions are licensed under the
project's custom restrictive license (see [`LICENSE`](LICENSE)). If that
does not work for you, please discuss before submitting.

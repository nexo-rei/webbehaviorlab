# Security Policy

WebBehaviorLab is a cybersecurity **education** tool. This policy explains
responsible use, what we consider a vulnerability, and how to report
problems safely.

## Responsible Use

### Authorized testing only

You may use WebBehaviorLab only against:

- your own machine (localhost, 127.0.0.1, private LAN hosts you operate)
- local development and test servers
- staging environments you control
- production websites **you own**
- websites whose owners have given you **explicit written permission** to
  test

Before every test, the application shows a TARGET SAFETY CHECK and requires
you to confirm you are authorized. Keep evidence of authorization (emails,
contracts, scoping documents) for any target you test.

### Prohibited misuse

WebBehaviorLab must never be used to:

- generate artificial traffic, views, clicks, or engagement on systems you
  do not own
- manipulate analytics, advertising, or search metrics
- bypass or attempt to bypass CAPTCHA, bot detection, rate limits, or any
  other security control
- rotate proxies or identities to evade restrictions
- perform denial-of-service, brute-force, credential-stuffing, or any other
  attack
- exfiltrate data from systems you are not authorized to access
- disguise automated traffic as human traffic

The codebase intentionally contains none of these capabilities, and
contributions adding them will be rejected (see CONTRIBUTING.md).

### Built-in guardrails

| Guardrail | Where |
|---|---|
| Hard 10-session limit per run | `src/webbehavior/core/limiter.py` |
| Authorization confirmation before every test | `src/webbehavior/ui/menu.py` |
| HTTP/HTTPS URL validation, credentials rejected | `src/webbehavior/core/validator.py` |
| Mandatory pacing between sessions | `src/webbehavior/core/scheduler.py` |
| No proxy, stealth, or fingerprint features | `src/webbehavior/browser/launcher.py` |
| Secrets scrubbed from logs and diagnostics | `src/webbehavior/monitoring/logger.py` |
| Sanitized report filenames, no shell execution | `src/webbehavior/utils/storage.py` |

## Reporting Security Problems

If you believe you have found a security vulnerability **in WebBehaviorLab
itself**, please report it responsibly:

1. **Do not open a public GitHub issue** for the vulnerability.
2. Email the maintainers via the contact address listed on the repository,
   or use GitHub's *Report a vulnerability* feature on the **Security**
   tab of the repository.
3. Include:
   - a description of the issue and its impact,
   - steps or a proof-of-concept (kept minimal and non-destructive),
   - the WebBehaviorLab version (`webbehavior version`),
   - your operating environment (Termux/Linux details).
4. Please give us **90 days** to respond and remediate before any public
   disclosure.

We commit to:

- acknowledging reports within 7 days,
- keeping you informed of remediation progress,
- crediting reporters (unless you prefer to remain anonymous).

### Responsible disclosure

When we fix a security issue, the fix and a summary will be published in
[`CHANGELOG.md`](CHANGELOG.md) with credit to the reporter. We do not
publish exploit details that would make the issue easier to abuse before
users have had time to update.

## Scope of this Policy

This repository's code, documentation, and release artifacts are in
scope. Third-party dependencies (rich, Playwright, Chromium) should be
reported to their upstream projects, though we welcome heads-up notices
for issues that affect WebBehaviorLab users.

## A Note for Learners

Part of learning web security is learning **ethics and boundaries**. If you
are unsure whether you are allowed to test a target, the answer is simple:
**do not test it** until you have written permission. Curiosity is never a
legal defense.

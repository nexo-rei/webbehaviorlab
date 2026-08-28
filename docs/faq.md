# Frequently Asked Questions

## General

**Is this a botting / traffic tool?**
No. WebBehaviorLab is an educational testing laboratory. It runs at most
10 sessions against a target you confirmed you are authorized to test,
records metrics, and writes a report. There is no proxy rotation,
CAPTCHA solving, fingerprint spoofing, or traffic-generation feature —
and contributions adding them are rejected.

**Do I need to know Python?**
No. Everything happens through menus and prompts.

**Does it work on phones?**
Yes — Termux is a first-class target, with a compact UI for small
screens and Termux-aware browser detection.

## Safety

**Why 10 sessions?**
The limit keeps the tool proportional to its educational purpose and
makes it useless as a traffic generator. It is a hard constant in
`core/limiter.py`; settings can only lower it.

**What counts as an authorized target?**
Systems you own (localhost, your servers, your staging environments) or
systems whose owner explicitly permitted you to test. If you cannot
point at the permission, do not test it.

**Does it hide that it's automated?**
No — deliberately. The test browser runs with normal automation flags.
Understanding how automation *appears* is part of the education;
disguising it is out of scope.

**What data does it collect?**
Timings, HTTP status codes, counts of events/actions, and the target
URL. Never page content beyond that, cookies, headers, tokens, or
credentials. Logs scrub sensitive values automatically.

## Usage

**Can I test a website on the internet?**
Only one you own or are authorized to test. The safety check appears for
every target; remote targets are simply not pre-labeled as local.

**Why did my test say PARTIAL?**
Some sessions succeeded and some failed — often a flaky connection or a
server that intermittently returned errors. Check the per-session lines
in the TXT report.

**Where are my reports?**
`~/.webbehavior/reports/`. JSON is machine-readable; TXT is for humans.
The `[4] Reports` menu lists them.

**Can I run tests without the menu?**
Yes:

```bash
webbehavior start --url http://127.0.0.1:8000/ --sessions 3 --yes
```

`--yes` is your authorization confirmation.

**How do I make my page's button clickable in tests?**
Add `data-wbl-test` to it: `<button data-wbl-test>Go</button>`. See
[configuration.md](configuration.md#making-your-page-test-friendly).

**The demo `click_test_element` says "skipped". Is that an error?**
No. It means the page had no button to click. The action is recorded as
skipped so your run isn't marked failed because of it.

**Headless vs visible browser mode?**
Headless is faster and works everywhere. Visible mode opens a window so
you can *watch* the automation — great for learning. Toggle in
`[5] Settings → [4] Browser Mode`.

## Troubleshooting quick hits

- **Browser won't start** → `webbehavior doctor`, then
  `pkg install chromium` (Termux) or `playwright install chromium`.
- **Command not found** → re-run `bash install.sh`, or `bash run.sh`.
- **Animations feel slow** → Settings → Animation → OFF.
- **Weird error panel** → note the `ERR-XXXX` id and check
  `~/.webbehavior/logs/diagnostics/`.

## Licensing

**Can I use it at my school?**
Educational use is expressly permitted by the license.

**Can I sell it or publish a modified version?**
Not without written permission from the copyright holder — see
[LICENSE](../LICENSE) for the authoritative text and how to request
permission.

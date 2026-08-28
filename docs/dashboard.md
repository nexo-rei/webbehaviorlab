# The Live Dashboard

While a test runs, WebBehaviorLab shows a real-time dashboard. This guide
explains every part of it.

```text
╭────────────── LIVE TEST ──────────────╮

 Target       : localhost:8000
 Sessions     : 03 / 05
 Status       : RUNNING

 Progress:
━━━━━━━━━━━━━━━━━━━━━━░░░░ 60%

 Current Session
 ├─ Browser        ✓
 ├─ Page Load      ✓
 ├─ Response       200 OK
 ├─ Test Actions   ✓
 ├─ Events         8
 └─ Duration       4.31 sec

 Metrics
 ├─ Avg Latency    284 ms
 ├─ Success        3
 └─ Failed         0

╰───────────────────────────────────────╯
```

## Header

| Field | Meaning |
|---|---|
| **Target** | The authorized URL being tested (host:port) |
| **Sessions** | Finished sessions out of the total planned |
| **Status** | `STARTING` → `RUNNING` → `FINISHED` (or `ABORTED` if you press Ctrl+C) |

## Progress bar

`━` marks completed sessions, `░` remaining ones, with the percentage on
the right. It only moves when a session fully finishes — a long bar means
many completed sessions, not many requests (the tool runs **at most 10**
sessions per test).

## Current Session

The stages of the session running right now:

| Stage | Symbol meanings |
|---|---|
| **Browser** | `✓` the test browser is ready |
| **Page Load** | `→` loading, `✓` loaded, `✗` failed |
| **Response** | HTTP status, e.g. `200 OK` or `503 ERR` |
| **Test Actions** | executed/total predefined actions |
| **Events** | count of safe browser events recorded (loads, console messages, requests, responses) |
| **Duration** | wall-clock time of this session |

## Metrics

Rolling totals for the whole run so far:

- **Avg Latency** — mean time to load the page across finished sessions
- **Success** — sessions that loaded with an OK HTTP status
- **Failed** — sessions with network/browser errors or HTTP error statuses

## Symbols and accessibility

Meaning never depends on color alone:

| Symbol | Meaning |
|---|---|
| `✓` | success |
| `✗` | error |
| `⚠` | warning |
| `→` | running |
| `○` | pending |

## Compact mode

Below 70 terminal columns (small phones) the dashboard switches to a
compact layout: narrower bars, shortened labels, tighter panel. No
setting needed — it follows your screen size automatically.

## When output is piped

If stdout is not a terminal (e.g. `webbehavior start … | tee log.txt`),
the dashboard is replaced by one concise line per finished session:

```text
→ session 1/5  ok=1  failed=0  avg=212 ms
```

This keeps logs readable and avoids flicker.

## Animations

The dashboard refreshes about 4 times per second — enough to feel live,
light enough for phones. If your device struggles, disable animations in
`[5] Settings → [2] Animation Speed → OFF`; the dashboard then updates
once per session. 

## During failures

A failing session shows `✗` on the failing stage (e.g. `Page Load ✗`),
its error is stored in the report, and the run **continues** with the next
session. The final status becomes `PARTIAL` (or `FAIL` if nothing
succeeded).

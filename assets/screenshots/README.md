# Screenshots

This folder holds UI screenshots referenced by the README and docs.

## Suggested captures

| File | What to show |
|---|---|
| `menu.png` | The main menu with banner on a phone-sized terminal |
| `dashboard.png` | The LIVE TEST panel mid-run |
| `complete.png` | The TEST COMPLETE summary panel |
| `doctor.png` | `webbehavior doctor` output with all checks passing |
| `compact.png` | Compact mode on a narrow screen |

## How to capture (Termux)

Termux: long-press → *More* → no built-in capture? Use
`termux-media-player`-free options vary; the simplest is the Android
screenshot shortcut while the terminal is open.

Desktop Linux: `gnome-screenshot -w`, `import window.png`
(ImageMagick), or `scrot -u`.

To produce a deterministic, color-correct capture you can also record a
run to HTML and screenshot that:

```bash
webbehavior start --url http://127.0.0.1:8000/ --sessions 2 --yes 2>&1 | tee run.log
```

Only include screenshots of **local/authorized** targets.

# Publication log

## 2026-10-13 — completed states and district catch-up

Master delivery verified: **2026-10-13 13:28:45 America/Chicago**. Tested source commit: **`4991c426d03125bc8d3b1f257e9108bb7ba2717a`**. The `master` branch was fast-forwarded from `cd559313db862274f67a7656a552131df28efac2` through the verified `fine-fiddle` SSH identity. Existing history was preserved.

The published ready catalog contains **39 states and 60 comparison regions**, including the twelve previously completed district breakouts below. All six earlier Chicago/Illinois/NYC/Wisconsin regions and their data/source/geometry assets remain intact. **Eleven state source holds remain excluded from ready comparisons, and Charlotte-Mecklenburg remains source-only, with no released model or browser region.**

Validation: all **657 Python tests** and **20 JavaScript tests** passed; syntax/diff checks, independent source/readiness and catalog/canonical preservation reviews, and HTTP desktop/390-pixel browser checks passed. The canonical database and all 237 served files matched the previously validated release fingerprints. In-memory catalog/guide reconstruction and foreign-key/integrity checks passed. Unavailable counts/intervals and other unaudited scope remain explicit.

| Completed district | Reviewed integration commit | Master delivery verified at |
| --- | --- | --- |
| [Los Angeles Unified](los-angeles-district.md) | `6eb1410` | 2026-10-13 13:28:45 |
| [Miami-Dade County](miami-dade-district.md) | `b49556f` | 2026-10-13 13:28:45 |
| [Clark County](clark-county-district.md) | `a6073d6` | 2026-10-13 13:28:45 |
| [Broward County](broward-district.md) | `ccb8b92` | 2026-10-13 13:28:45 |
| [Hillsborough County](hillsborough-district.md) | `5ce4466` | 2026-10-13 13:28:45 |
| [Orange County](orange-district.md) | `38cd89a` | 2026-10-13 13:28:45 |
| [Palm Beach County](palm-beach-district.md) | `79ef2d4` | 2026-10-13 13:28:45 |
| [Gwinnett County](gwinnett-district.md) | `7bd4a04` | 2026-10-13 13:28:45 |
| [Fairfax County](fairfax-district.md) | `32c1f93` | 2026-10-13 13:28:45 |
| [Houston ISD](houston-district.md) | `04ee524` | 2026-10-13 13:28:45 |
| [Wake County](wake-district.md) | `832194f` | 2026-10-13 13:28:45 |
| [Montgomery County, Maryland](montgomery-district.md) | `a4ee4e2` | 2026-10-13 13:28:45 |

GitHub Pages deployment is verified: the [tested-source run](https://github.com/robot-assisted-projects/FRPL-RMA/actions/runs/38447064502) for `4991c42` and the [delivery-documentation run](https://github.com/robot-assisted-projects/FRPL-RMA/actions/runs/38447387015) for `4cec36e` both completed successfully. Public-site browser readback at **2026-10-13 13:34:14 America/Chicago** confirms 39 states, 60 ready regions, all twelve delivered districts, 77 guide definitions and held-state/Charlotte exclusions. Eight core public assets returned HTTP 200 and matched the tested local files byte for byte. Montgomery's first search, ELA chart/history and unavailable intervals work; true 390-pixel mobile views have no overflow. The only cosmetic limitation is a pre-existing favicon 404, with no application script failures.

This was the user-authorized one-time cleanup of already finished work. Subsequent district work returns to **only the fixed 66 entries in [TODO-breakout_districts.md](../TODO-breakout_districts.md)**, beginning with Charlotte-Mecklenburg. The twelve delivered comparisons above are history, not additional queue entries.

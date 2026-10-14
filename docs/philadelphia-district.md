# Philadelphia original-source and cohort audit

This work covers **2024–25**, exact NCES LEA **`4218990`**, CCD native LEA **`PA-126515001`** and Pennsylvania AUN **`126515001`**. The [source audit](../data/source/philadelphia-district-audit.json), rebuilt by [audit_philadelphia.py](../scripts/audit_philadelphia.py), retains original records and definitions. Source/cohort gate verified **2026-10-13 18:33:36 America/Chicago**; both historical source/modeling approvals remain false. No district fit, canonical import or browser comparison is approved by these prospective counts.

## Identity and population

Original CCD records contain 221 school identities: 220 operational schools and one inactive school. All 220 operational schools match the native grade and individual-income records by authoritative AUN and building code. Native school numbers normalize to nine digits within their exact AUN; CCD's variable-width final school-number component supplies the same authoritative crosswalk. Names do not establish a join.

Native building `000009999`, named Philadelphia City SD, has 3,862 enrolled pupils and no CCD school identity or school-income row. Inactive Meehan Austin Middle, `000006768`, has a CCD identity and no native grade/income/PSSA rows. Keep both records separate and unjoined. The native LEA enrollment total 120,148 equals native grade enrollment including building 9999; matched native operational/income-school enrollment totals 116,286. CCD separately reports district enrollment 120,057 and operational-school enrollment 116,230. LEA low-income enrollment 90,098 and school low-income enrollment 88,634 also differ. These reporting gaps do not assign pupils or income to a school.

The prospective grade-school population has **162** exact operational identities, with complete original lower-grade offers, positive enrolled PSSA grades 3–8, no high/UG/AE offers and zero enrolled grades 9–12. All 162 have individual income and published Math/ELA totals. Barton Clara `000003732` offers/enrolls only K–2 and stays outside, despite its broad lower-grade classification. The remaining operational configurations include 47 high-only and ten mixed-grade schools. All 162 prospective members are noncharter in CCD; charter schools under separate LEAs are outside this district identity, regardless of location. Planning's 162 potential grade schools does not select or approve the audited population. High/mixed/primary/inactive/unmatched records stay explicit.

## Same-year individual income

Use the complete native October 1, 2024 school low-income worksheet, rather than the worksheet limited to schools above 30%. The predictor is the original individual low-income count divided by its own school enrollment, reconciled to the same-year native grade registry. Retain the native four-decimal truncated proportion; the prospective predictor uses the precise count ratio. Pre-K/kindergarten categories remain in the denominator where enrolled.

PIMS field 88 is individual economic-disadvantage status. Permitted poverty sources include TANF, census poor, Medicaid, foster homes and neglected/delinquent institutions; reliable recent FRPL eligibility is a fallback. CEP universal meal eligibility belongs to separate food-program field 131 and cannot determine field 88. Local poverty sources vary, and reporting completeness is unknown. This state-specific administrative proxy differs from uniform FRPL and direct household income. Missing school income remains unavailable.

## Regular PSSA totals and scored counts

Select only original regular PSSA **All Students / Total** Math and ELA school rows, covering tested grades 3–8. Use **Percent Proficient and above** exactly as published to one decimal. Separately rounded Advanced and Proficient rates can sum to a different value; they do not replace the published total. Grade percentages are not averaged, and suppressed rates are not reconstructed.

The source names **Number Scored** and masks proficiency below eleven scored students. The prospective 162-school totals have integer scored counts of at least 42. Count certification belongs to the completed source validation and primary notes; no sampling variance or interval is calculated during this source-only phase. Widener Memorial's outside-cohort totals retain two scored students and masked rates for both subjects.

Workbook notes exclude pupils enrolled after October 1, homeschoolers, pupils excluded from school aggregation, newer English learners, the specified LIFE/English-learner group and pupils who did not attempt. This accountable scored population differs from all spring testers. PASA alternate assessment and Keystone end-of-course exams remain separate. Income describes broader October enrollment, rather than the tested population.

## Verification and next steps

The original inventory preserves nine tables, 22,108 records and 622,260 typed cells, including all 19,408 district PSSA subgroup/grade rows and all 340 original school Total records. Four Pennsylvania originals, four CCD files and the existing Pennsylvania extract retain URLs and whole-file checksums. Full headers, notes, source rows and PIMS field definitions remain auditable. Every retained PSSA row validates nonnegative integer scored counts and finite 0–100 native percentages with one-decimal precision, including unused grade/subgroup rows. Masks and absent values remain distinct from zero. Ten source tests and eleven Pennsylvania/planning regressions pass, with two actual final-code original builds producing the byte-identical **7,253,157-byte** artifact, SHA-256 **`6f6f1a97304ecb286d4da37401b3281fc446dc55dcd9f46bd3561cf1b9213c56`**. Offline replay and compilation pass. Both independent reviews pass: 810,910 original/derived/bounds checks, 124 recorded review rejections and 28 complementary primary controls, with the retained-row validation gap repaired before freeze. Every preceding row in nine canonical tables, all 253 served files and all 315 prior scientific files remain unchanged. Eight original files plus the ninth existing statewide extract are pinned; the statewide extract is a separate cross-check.

Next: independently verify separate Math, ELA and paired Combined full/deleted fits and conditional sampling intervals using every member’s verified subject counts; then validate a separate normalized contract, repeated canonical imports, prior-data preservation and browser behavior. Master delivery follows completion and testing of the approved district scope. Admissions, provider roles and geometry remain unaudited. The [fixed 66-district TODO](../TODO-breakout_districts.md) records the actual start and keeps its finish date blank until verified delivery.

For the original Pennsylvania sources and statewide scope, see the [state data guide](pennsylvania-data.md). Statewide fits do not supply district predictions.

```sh
.venv/bin/python scripts/audit_philadelphia.py --extract
.venv/bin/python scripts/audit_philadelphia.py
.venv/bin/python -m unittest discover -s tests -p 'test_philadelphia_audit.py' -v
```

## Independent numerical audit

The compact [numerical artifact](../data/source/philadelphia-model-audit.json), rebuilt by [audit_philadelphia_models.py](../scripts/audit_philadelphia_models.py), keeps the full original tables stored once in the historical source artifact. Every API, including cached/expected replay, verifies complete current linked source/code/test/policy/raw/schema/definition evidence, literal/runtime policy, original count/rate types and exact native/NCES pointers. Both historical source/numerical approvals remain false; status is `numerically_verified_pending_integration`, scope `numerical_audit_only`.

| Diagnostic | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Eligible schools | 162 | 162 | 162 |
| Intercept | 105.741459 | 116.609942 | 111.175701 |
| Disadvantage slope | -1.044102 | -1.078268 | -1.061185 |
| R² | 0.757766 | 0.815153 | 0.810356 |
| Maximum leverage | 0.123438 | 0.123438 | 0.123438 |
| Maximum Cook distance | 0.169347 | 0.242654 | 0.233249 |

All **486 explicit deleted-school fits** have rank-two designs and positive finite scales, with no hard holds. Full/deleted residual degrees of freedom are 160/159. The same 162 income values make Combined coefficients equal subject means by OLS linearity, while Combined retains its own original paired outcomes, scales, deletion fits, studentized residuals and intervals. Coefficients do not supply Combined's other statistics.

All 324 subject denominators are original certified Number Scored values, minimum42≥native11. Each subject's smoothed binomial variance follows the repository's Jeffreys formula. Combined uses `(sqrt(v_math)+sqrt(v_ELA))²/4`, the maximum positive covariance bound. Each conditional interval propagates **every model member's** variance through `(I−H)`, holding the observed deleted regression scale fixed for `t ± 1.96 SE`. Combined's displayed count is the smaller native subject count, not a paired or deduplicated denominator; both original counts supply the variance calculation. These approximate conditional intervals hold income/design and deleted scale fixed, assume independent school rate errors and do not add source-rounding or income uncertainty. Enrollment never substitutes for scored counts or weights the fit.

Meredith William M `126515001-000003649` retains ELA expectation **100.319561%**; influential Greenfield Albert M `126515001-000005186` retains **100.043559%**. The linear model is unbounded. Jenks Abram's authoritative native `000007227` maps to NCES **`421899003644`**, with differing suffixes preserved; its Combined t is about **4.456091**, interval **[3.322565, 5.589617]**. Influence and residual size do not remove eligible members or establish admissions, causal effectiveness or quality. All 59 outside CCD records and separate native-only building9999 remain linked.

Numerical gate verified **2026-10-13 18:51:54 America/Chicago**. Thirteen numerical tests, two actual fresh byte-identical CLI builds, offline check and compilation pass. The **1,707,603-byte** artifact has SHA-256 **`9ede3ce013d27e1947e698d9e8d1793cbec977f5e6f82822ccf197c1d8d5949d`**. Both reviews pass **191,643 original/pointer/numerical checks**, all 486 independent NumPy deletions and fifteen selected 50-digit Decimal deletion/interval cases, with **248 corruption/freshness rejections**; maximum difference `5.46e-12`. Whole canonical bytes, all nine prior tables, 253 served files and 318 prior scientific files remain unchanged.

```sh
.venv/bin/python scripts/audit_philadelphia_models.py
.venv/bin/python scripts/audit_philadelphia_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_philadelphia_models.py' -v
```

Next: separately validated normalized/canonical/static integration, initially isolated. Main imports remain held until adapter tests, both integration reviews and all nine ownership guards pass; repeated main imports, browser verification and tested master delivery follow. No source/numerical artifact supplies browser readiness.

## Canonical and browser integration

The separately validated [normalized release](../data/source/philadelphia.json), rebuilt by [prepare_philadelphia.py](../scripts/prepare_philadelphia.py), supplies exact dataset `pa-philadelphia-2025` / region `philadelphia` readiness. Both historical source/numerical artifacts retain false approvals. Complete current source/code/test/policy/raw/schema/definition evidence and normalized fingerprints are required before database access, including cached APIs. All nine ownership tables preserve legal shared native identities between this district and Pennsylvania's separate statewide dataset.

The release contains 162 searchable profiles, 162 same-year individual-income observations, 324 original valid-score subject observations, sixteen provenance records and three independent 162-school models. All 486 canonical/current/history results and conditional sampling intervals match the original-source numerical oracle. Both original subject counts feed Combined variance; the smaller displayed count does not claim paired or deduplicated pupils. The interval method propagates every member through (I−H), fixes the deleted residual scale and income/design, and uses maximum positive Math/ELA covariance. Original percentage rounding and income uncertainty are not included. Native masks, outside populations and reporting gaps remain explicit; no influence exclusion or prediction clipping occurs.

Eleven adapter tests, two actual normalized builds and two full-database-copy private imports pass. Both independent integration reviews pass, including 226,363 original/normalized/canonical/current/history comparisons, 269 independent freshness/ownership rejection controls and 97 complementary policy rejections. Two authorized actual main imports repeat every target row and all four export bytes, preserving every preceding row in all nine tables, all 253 prior served files and all 321 preceding scientific files before shared regeneration.

Repeated catalog/assessment-guide/planning exports add only Philadelphia, preserving 64 old regions, 81 guide definitions/provider bindings and geometry. The ready catalog now has 39 states /65 regions and the guide 82 definitions; eleven source holds remain. Planning changes only exact `4218990` to existing Philadelphia; the original 66-district TODO keeps completed rows. All 81 distinct targeted Python tests (ten source, thirteen numerical, eleven adapter and 47 shared regressions), twenty JavaScript tests and syntax/diff checks pass. HTTP/browser and master delivery are recorded separately; finish remains blank until the remote commit is verified. Provider, admissions and geometry remain unaudited.

```sh
.venv/bin/python scripts/prepare_philadelphia.py --extract-only
.venv/bin/python scripts/prepare_philadelphia.py
.venv/bin/python -m unittest discover -s tests -p 'test_philadelphia.py' -v
```

Philadelphia tested master delivery verified **2026-10-13 19:31:11 America/Chicago**, commit `8a185836fa07af8f6e2c3640c436b8adc59c21bb` through fine-fiddle. Local HTTP/browser checks and eight asset/19 Git-blob bindings pass. The original fixed66 TODO retains its completed row; Cypress-Fairbanks source-only work continues. Pages deployment and public readback pass **2026-10-13 19:36:06 America/Chicago**.

Public-site verification passes **15 assertions** at **2026-10-13 19:36:06 America/Chicago**, after the [successful Philadelphia Pages run](https://github.com/robot-assisted-projects/FRPL-RMA/actions/runs/38490641846). All eight public HTTP200 assets match tested release `8a18583`; the separate 162-school counted models, conditional interval displays, exact native-ID cases, first off-page search, two independent Pennsylvania guide links and narrow-screen keyboard/table behavior pass. No application, script or required-data failures were found.

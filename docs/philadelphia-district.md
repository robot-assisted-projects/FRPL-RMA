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

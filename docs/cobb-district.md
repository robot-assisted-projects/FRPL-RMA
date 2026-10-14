# Cobb County district comparison

Exact2024–25 identity: NCES LEA `1301290`, native `GA-633`. Started **2026-10-14 01:13:52 America/Chicago**, in the original [66-district queue](../TODO-breakout_districts.md). Original-source review passed **2026-10-14 02:01:53**; independent numerical verification passed **2026-10-14 02:23:33**. Isolated normalized/import testing is underway. Historical approvals remain false; no canonical/browser release is approved by these audit milestones.

## Original source and cohort audit

The [source audit](../data/source/cobb-district-audit.json), rebuilt by [audit_cobb.py](../scripts/audit_cobb.py), retains thirteen original whole-file pins plus the Georgia AllStudents compact cross-check and statewide secondary evidence. Complete original schema, source rows, masks, definitions and native/full NCES identities remain auditable. Six target tables contain25,662 records /865,003 typed cells;2,260 needed rows /68,573 cells are retained, with complete23,402 omitted ordinal, identity and population inventories.

The110 original CCD directory schools are all Open. Independent offered/enrolled grade reconstruction identifies92 lower,16 high and two mixed configurations; two primary schools remain outside the tested-grade population. All90 source-certified lower profiles have complete same-year individual direct-certification income and original published Math/ELA rates. All90 are non-charter Regular schools; this observed composition is not an exclusion by program or performance. Walton High (`130129000513`) is the one directory charter and remains outside the lower population. School and district membership reconcile at105,738. Planning counts never approve models.

Income uses each school's reported individual direct-certification count divided by its own reported membership for2024–25. It is a benefits proxy distinct from full household-income FRPL and universal meals. Georgia Medicaid/foster identification changes, outside-program preschool treatment and identification-coverage limits remain explicit. No name/suffix inference, district denominator substitution or another-year backfill is allowed.

Use original regular Georgia Milestones **EOG All Students G38 published proficiency**, Levels3–4. Native reported source/name/cut-score flags are retained. Do not average grades or splice EOC rates. Accelerated-pupil EOG/EOC treatment and valid-score counts/floor/variances/intervals remain uncertified. The pinned notes contain no Cobb-named shared-time warning; absence does not certify nonlisted attribution coverage.

Fourteen focused tests, two actual final-code/test/source-bound identical original CLI builds, offline replay and compilation pass. Independent review reopens original files and verifies917,416 original/derived comparisons,66 necessary corruption rejections and13 controls, including coherent public fingerprint/runtime resigning and current cached-source attacks. Source scope remains `source_cohort_audit_only`, both approvals false; separate modeling/import/browser gates are required.

## Independent numerical verification

The separate [numerical audit](../data/source/cobb-model-audit.json), rebuilt by [audit_cobb_models.py](../scripts/audit_cobb_models.py), verifies independent unweighted90-school Math, ELA and paired Combined models and all270 explicit deleted-school fits. Every full/deleted design has rank two and positive finite scales, with residual degrees of freedom88/87. Combined fits its own equally averaged paired responses and scale; externally studentized residuals are not averages of subject t values.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 90 | 90 | 90 |
| Intercept | 74.149200 | 69.202973 | 71.676087 |
| Disadvantage slope | -1.441144 | -1.387480 | -1.414312 |

Bryant Elementary (`130129002158`) has the highest Math Cook influence; Dickerson Middle (`130129001880`) has the highest ELA/Combined influence. Both remain included. Observed predictions are within0–100, while a synthetic valid-response control preserves unbounded predictions. No enrollment weighting, shrinkage, clipping, diagnostic exclusions or admissions inference is introduced. All counts, scored floor, variances and intervals remain unavailable; outside primary/high/mixed/charter records and EOG/EOC limitations remain linked.

Sixteen distinct targeted tests pass. Fourteen unaffected earlier passing checks and two corrected source-alias/wording fixtures are retained transparently; no scientific behavior changed. Two actual final code/test/artifact-bound CLI builds are byte-identical, with offline and compile checks passing. Independent review verifies104,670 original-input/provenance/full/deleted-fit/diagnostic comparisons, all270 NumPy deletions and three full/ten deleted60-digit fits (maximum difference1.82e−12).132 necessary rejections and three controls pass. A reviewer fixture was corrected to expect a deliberate corrupt shared fitter to return numerical holds rather than raise; the held output fails closed and no producer change was needed.

Historical source/numerical six remain immutable with false approvals; the numerical scope alone does not approve canonical or browser release. Current main rows/assets and69 regions /86 guide definitions/provider bindings/geometry remain unchanged. Next: isolated normalized/import validation and independent review, then separately authorized main/shared/browser and tested master/public delivery. Finish remains blank.

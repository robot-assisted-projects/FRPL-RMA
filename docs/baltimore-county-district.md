# Baltimore County district comparison

Exact 2024–25 identity: NCES LEA `2400120`, CCD native `MD-03`, MSDE division `03`. Started **2026-10-13 23:35:01 America/Chicago**. This district belongs to the original [66-district queue](../TODO-breakout_districts.md). Source review passed **2026-10-14 00:19:55**; separate numerical verification passed **2026-10-14 01:02:20**. Isolated normalized integration is underway. Historical approvals remain false. No canonical or browser release is approved yet.

## Original sources and eligible population

The [source audit](../data/source/baltimore-county-district-audit.json), rebuilt by [audit_baltimore_county.py](../scripts/audit_baltimore_county.py), pins eleven original CCD/MSDE files and primary definitions. Eight retained tables contain 4,536 needed records /75,620 typed cells, preserving complete fields, headers, masks and original source rows. Exact omitted-row inventories and digests retain provenance for 18,686 unused school-membership demographic rows,227 LEA-membership rows and468 other-group LEA MCAP rows. Selection does not use performance or model diagnostics.

All178 original native directory NCES cells match operational CCD records. The complete180-row CCD directory includes two closed, native-unjoined records (`MD-03-030058`, `MD-03-031451`), which remain outside. Identity uses authoritative full NCES cells and independently checked native codes; names and suffixes do not repair joins.

Separate original offered/enrolled grades, native E/M/EM span and positive grades3–8 enrollment select **137 lower-grade profiles**, all with usable own same-year Early Attendance economic ratios. Watershed Public Charter (`03-0219`, NCES `240012001753`, CCD `MD-03-030219`) remains in the178-school evidence roster but is outside this cohort because its original offered flags are Adjusted. Meadowood and Crossroads alternative schools remain source-eligible; their masked Math results leave them ELA-only. No program or admissions classification is inferred.

## Income and achievement definitions

Income is each school's original individual **Early Attendance economically disadvantaged count / own total student count**, using the native All band where multiple bands exist. The precise ratio reconciles the native one-decimal display. Its collection as-of date and identification coverage are unspecified. This status is broader than household-income FRPL and distinct from universal meals, tested-student poverty and CCD direct certification. September or CCD membership never replaces its denominator; missing cells are not zero and other years are not backfilled.

Use original regular MCAP **School_Level, Year2025, All Students, All Grades** published Math/ELA proficiency under Levels3–4 standards introduced in2021–22. DLM remains separate. Accelerated Algebra1, Geometry and Algebra2 and the March2025 grade6–7 course-substitution waiver (2024–25 through2027–28) remain explicit population limits. Published All Grades percentages are not replaced by averaged grades, component sums or reconstructed count ratios.

Eleven original `<= 5.0` Math masks remain unavailable. Prospective populations are **126 Math /137 ELA /126 paired Combined**. Combined is the equal mean of paired original rates and needs its own126-school fit, residual scale and deletions; full subject coefficients and t scores cannot be averaged across unequal populations. No models are approved by this source audit.

CCD/September LEA and operational CCD school totals are110,024. Known native September school totals110,015 leave9 unassigned; Early Attendance district110,382 versus known school denominators110,357 leaves25 unassigned. Eight school denominators are missing/suppressed outside the eligible cohort. Aggregate differences never allocate missing values or establish an administrative cause.

Administrative tested counts remain raw evidence. Unique valid-score denominators, the ten-valid-scored floor, sampling variances and intervals remain uncertified/unavailable. Source success does not approve high/mixed populations, provider roles, geometry or causal interpretations.

## Source verification and next gate

Fourteen focused tests, two identical actual original-source CLI builds, offline replay, compilation and independent review pass. The reviewer reopens all eleven original files and verifies **165,999** strict original/derived comparisons,113 meaningful corruption rejections and17 positive/boundary controls. Whole canonical bytes, every previous row in nine tables,265 served assets and348 scientific files remain unchanged at this gate. Root's later Memphis integration is separately authorized.

Review corrected a charter-eligibility sentence in the ignored producer proof; its original bytes are archived and the correction is independently bound. The source artifact, code, tests and cohort were correct and remain unchanged. Immutable source policy, complete raw/schema/definition/identity fingerprints, original metadata digests and current runtime/cached evidence guards prevent self-repinned input drift.

```sh
.venv/bin/python scripts/audit_baltimore_county.py --extract
.venv/bin/python scripts/audit_baltimore_county.py
.venv/bin/python -m unittest discover -s tests -p 'test_baltimore_county_audit.py' -v
```

At this source gate, separate126/137/126 models and all389 explicit deletion fits were next. The completed numerical phase follows below. Historical status remains `audit_pending`, scope `source_cohort_audit_only`, both approvals false. Normalized/import, browser and tested master delivery require their separate gates; finish remains blank.

## Independently verified numerical models

The separate [numerical audit](../data/source/baltimore-county-model-audit.json), rebuilt by [audit_baltimore_county_models.py](../scripts/audit_baltimore_county_models.py), preserves independent unweighted126 Math,137 ELA and126 paired Combined-school fits. All389 explicit deletion fits have rank two and positive finite residual scales. Combined uses its own paired outcomes, coefficients, scale and deleted fits.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 126 | 137 | 126 |
| Intercept | 76.960107 | 96.216426 | 86.065183 |
| Disadvantage slope | -0.797629 | -0.878245 | -0.821878 |

Nineteen distinct targeted tests pass, with two final actual byte-identical CLI builds, offline replay and compilation. Independent review verifies64,709 original/pointer/numerical comparisons, all389 NumPy deletions and three full/fifteen deleted60-digit fits (maximum difference1.82e−12),85 meaningful corruption rejections and six controls. A valid synthetic percentage population retains an unclipped−4.08 prediction. No influence-based exclusions, weights or shrinkage are introduced.

Review found a cached-reference path could self-authorize an altered prediction. The final validator rebuilds its expected result from verified original inputs on every call; supplied expectations and mutable public caches cannot authorize drift. The exact former forgery and caller/builder alias controls now pass independent rejection checks. The nineteen-test evidence records earlier mathematical checks and the final repaired-guard checks separately. Source inputs and all389 scientific fits are unchanged.

The source trio remains frozen; historical source/numerical approvals remain false. Counts, scored floor, variances and intervals remain unavailable, eleven original Math masks persist, Watershed charter remains outside the cohort and Meadowood/Crossroads remain ELA-only. Current canonical and served assets are preserved except root's separately authorized Memphis delivery. Numerical gate recorded **2026-10-14 01:02:20 America/Chicago**. Next: isolated normalized/private imports and independent review; actual main import, browser and tested master delivery require separate gates.

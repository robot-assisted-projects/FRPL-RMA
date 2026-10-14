# Memphis-Shelby County district comparison

Exact 2024–25 identity: NCES LEA `4700148`, CCD native `TN-00792`, original EDC district `792`. Started **2026-10-13 22:18:51 America/Chicago**. Work belongs to the original [66-district queue](../TODO-breakout_districts.md). Source review passed **2026-10-13 23:15:20**; numerical verification is underway. Historical approvals remain false and no canonical/browser release is approved yet.

## Original sources and population

The [source audit](../data/source/memphis-district-audit.json), rebuilt by [audit_memphis.py](../scripts/audit_memphis.py), pins thirteen original CCD/EDC files and primary definitions plus a secondary statewide field cross-check. Retained needed original tables contain 3,368 records /80,349 typed cells, with complete fields, masks, schemas, headers and source rows. Full target inventories contain 48,950 records /1,579,478 cells; exact omitted-population ordinals and identities preserve the 45,582 unused demographic/subgroup rows. Selection does not use metric values or model diagnostics.

The complete CCD directory has 223 operational schools (219 Open, four New):167 offered lower,16 mixed and40 high. Same-year reported offered and enrolled grades select154 pure lower profiles. Native IDs are matched by authoritative twelve-digit NCES IDs and independently checked native district/school fields. Caldwell-Guthrie (`470014802229`, native `792-2067`) lacks a current directory join and remains unjoined; names and NCES suffixes do not repair it.

Income is each school's own reported CCD Final 2a individual Direct Certification Education Unit Total divided by its own positive reported same-year Membership Education Unit Total. This benefits/status proxy is distinct from full household-income FRPL and universal/CEP meal service. Unreported, derived, masked and missing counts do not become zero; no other-year income or funding multiplier is substituted. Pre-K is included where enrolled; Medicaid and certification/reporting coverage can vary and undercount is unknown.

Achievement uses the original EDC v3.1 SEA-sourced regular TNReady All Students native G38 aggregate for grades3–8, Levels3–4, exact `ProficientOrAbove_percent`. Grades/subgroups are never averaged or pooled. Ranges/suppression stay unavailable. Raw EDC tested/performance counts may be constructed and have not been certified as valid-score denominators. Counts, scored floor, variances and sampling intervals remain unavailable; enrollment and participation never replace them.

## School-specific attribution holds

Original [CCD Final 2a Data Notes](https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx), Data Notes row463, Tennessee CCD-0054, names13 district campuses where some or all students receive services while enrolled at a separate school of record. Four overlap the154 pure lower profiles:

| School | NCES ID | Own membership | Direct certification | Status |
| --- | --- | ---: | ---: | --- |
| Germantown Middle | 470014801583 | 606 | 284 | Enrollment/service attribution held |
| Woodstock Middle | 470014801595 | 248 | 176 | Enrollment/service attribution held |
| White Station Middle | 470014801960 | 1,127 | 352 | Enrollment/service attribution held |
| Treadwell Middle | 470014802217 | 764 | 375 | Enrollment/service attribution held |

All four raw school records, income ratios and native outcomes remain evidence. A plausible ratio does not resolve attribution. Nine other named high/mixed campuses remain outside the lower population. The note identifies specific schools; it does not establish a whole-LEA warning or certify attribution coverage at nonlisted campuses. These are source-attribution holds, independent of model influence.

Raw published inputs are146 Math,151 ELA and146 paired Combined; after the four holds, separate prospective usable populations are **142 Math /147 ELA /142 Combined**. All154 profiles remain auditable;41 are charters, with40/41/40 usable in the respective subjects. LEA enrollment111,124 differs from the operational school sum111,125 by−1; the cause is unassigned. No program/admissions/provider/geometry inference is made.

## Source verification and next gate

Thirteen focused tests, two identical actual original-source builds, offline replay, compilation and independent source review pass. The review verifies242,594 original/derived fields and54 meaningful semantic/current-evidence rejection cases with11 controls. Current canonical data, all nine tables and preceding served/scientific files are preserved, including Polk's separately authorized shared rebuilds. Historical status remains `audit_pending`, scope `source_cohort_audit_only`, both approvals false.

```sh
.venv/bin/python scripts/audit_memphis.py --extract
.venv/bin/python scripts/audit_memphis.py
.venv/bin/python -m unittest discover -s tests -p 'test_memphis_audit.py' -v
```

Next: separate original-input numerical verification with431 explicit deletion fits. Combined must fit its own paired142-school population; coefficients cannot be obtained by averaging the full Math and147-school ELA fits. Canonical import, browser checks, independent integration review and tested master delivery follow only after the separate gates pass.

## Independent numerical audit

The separate [numerical audit](../data/source/memphis-model-audit.json), rebuilt by [audit_memphis_models.py](../scripts/audit_memphis_models.py), verifies independent unweighted Math142, ELA147 and paired Combined142-school models. All431 explicit deleted-school fits have rank two and positive finite residual scales. Full/deleted residual degrees of freedom are140/139 for Math/Combined and145/144 for ELA. Externally studentized residuals use the other members' fitted scale.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 142 | 147 | 142 |
| Intercept | 65.761291 | 64.801590 | 64.680060 |
| Disadvantage slope | -0.686444 | -0.660710 | -0.661414 |

Combined uses its own paired outcomes, fit, scale and deletions; the unequal ELA population makes averaging the full subject coefficients invalid. Maxine Smith STEAM Academy (`470014802379`) has the highest Cook influence in every fit and stays eligible. All40/41/40 subject charters remain. Observed predictions lie in0–100; the linear model remains unclamped and unbounded, with a synthetic endpoint guard. No enrollment weights, shrinkage, admissions inference or diagnostic exclusions are introduced.

All154 source profiles, four named attribution holds, native-only Caldwell-Guthrie, masked/missing outcomes and−1 reporting discrepancy remain linked. Nonlisted attribution coverage is not certified. Counts, scored floor, sampling variances and intervals remain uncertified/unavailable modelwide. Raw original tables are stored once; compact typed descriptors preserve exact school/member/grade/field/source-row pointers and current evidence guards.

Fifteen focused tests, two actual byte-identical CLI builds, offline replay and compilation pass. Independent review verifies136,607 original/pointer/math fields and all431 NumPy deletions (maximum difference7.28e−12, including SSE), plus three full and thirteen deleted60-digit fits (maximum3.64e−12). All103 semantic/numeric/input/degenerate/current-literal/cached-file rejection cases and four controls pass. Whole MAIN, every prior nine-table row,263 protected served files and342 preceding scientific files including frozen Polk and Memphis source evidence remain exact, with root's five separately authorized Polk shared changes. Numerical gate verified **2026-10-13 23:36:46 America/Chicago**.

```sh
.venv/bin/python scripts/audit_memphis_models.py
.venv/bin/python scripts/audit_memphis_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_memphis_models.py' -v
```

Historical status remains `numerically_verified_pending_integration`, scope `numerical_audit_only`, both approvals false. Isolated normalized/import testing and independent integration review follow; actual main imports and browser/master delivery remain held until those separate gates pass.

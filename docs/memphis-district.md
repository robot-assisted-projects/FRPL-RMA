# Memphis-Shelby County district comparison

Exact 2024–25 identity: NCES LEA `4700148`, CCD native `TN-00792`, original EDC district `792`. Started **2026-10-13 22:18:51 America/Chicago**. Work belongs to the original [66-district queue](../TODO-breakout_districts.md). Source, numerical, repeated canonical and shared-export gates passed independent review. Local browser and exact HTTP/Git bindings passed; tested release is verified on master. Pages/public readback passed **2026-10-14 01:10:08**. Historical approvals remain false; readiness belongs to the separately validated normalized scope below.

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

At the source gate, separate original-input numerical verification with431 explicit deletion fits was next. Combined requires its own paired142-school population; coefficients cannot be obtained by averaging the full Math and147-school ELA fits. The completed numerical and canonical gates are recorded below; browser and tested master/public delivery follow separately.

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

Historical status remains `numerically_verified_pending_integration`, scope `numerical_audit_only`, both approvals false. At that numerical gate, isolated normalized/import testing and independent integration review were next. The completed canonical phase is recorded below; browser/master delivery remains pending.

## Canonical and browser integration

The separately validated [normalized release](../data/source/memphis.json), rebuilt by [prepare_memphis.py](../scripts/prepare_memphis.py), supplies exact `tn-memphis-2025` /region `memphis` readiness. All six historical source/numerical files remain immutable with false approvals. Every current/cached API validates complete current evidence, literal runtime contracts, normalized fingerprints and all nine ownership tables before canonical writes; legal statewide Tennessee identity overlap remains separate.

All **154 canonical NCES-ID profiles** retain authoritative native crosswalks,154 economic observations,308 native subject observations,21 provenance records and three independent **142 Math /147 ELA /142 Combined** models with431 results. Four named shared-time profiles remain searchable with enrollment and raw original evidence, but usable income/outcomes and all comparison/history metrics are unavailable. Five ELA-only schools,40/41/40 eligible charters, influential Maxine Smith STEAM Academy, native-only Caldwell-Guthrie and the−1 reporting discrepancy remain explicit. Nonlisted attribution coverage is not certified. Counts, scored floor, variances and all sampling intervals remain unavailable; programs are Unclassified, admissions/provider roles and geometry unaudited.

Eleven distinct integration checks pass. A seeded foreign-model fixture had a duplicate primary key; its intended ownership probe was repaired, retaining the other ten passing checks and rerunning the affected method successfully. Production code, inputs and numerical results were unchanged. Two final actual normalized CLI builds and two full-MAIN-copy private imports use the same frozen code/test/normalized trio. Independent review verifies205,591 original/canonical/current/history fields and192 rejection cases with five controls, including all nine ownership tables and current uncached/repinned evidence before writes.

Two separately authorized actual main CLI imports repeat every target row and all four export bytes, preserving every prior row in nine tables and265 earlier served files before shared regeneration. Three source data files equal the final private bytes; the main catalog differs from private only in its two destination URLs, then repeats byte-for-byte. All nine Memphis scientific files remain frozen. All431 current and431 history results retain null counts and interval endpoints.

Repeated catalog/guide/planning exports add only Memphis, preserving67 preceding regions,84 definitions/provider bindings and all geometry. The catalog has **39 states /68 regions**; guide85 definitions, with eleven source holds unchanged. Only planning row4700148 changes scope; all counts/identities/source pins remain. The existing Polk row's misleading audit-pending display label was also corrected; its records and science are unchanged. All **88 distinct targeted Python tests** (13 source,15 numerical,11 integration and49 shared regressions),20 JavaScript tests, syntax and diff checks pass. Final independent scientific/shared review has no unresolved findings.

Canonical/shared gate recorded **2026-10-14 00:47:23 America/Chicago**. Local HTTP browser verification passed **2026-10-14 01:03:43** with17 assertions: initial off-page search and keyboard controls, pagination, all four attribution holds, five ELA-only schools, influential-school histories, exact Caldwell identities, shared/empty/invalid selections, fixed models, guide links and a visually inspected390px layout. No warning/error console logs. Exact HTTP/Git binding and master/public delivery remain; finish stays blank until remote verification.

```sh
.venv/bin/python scripts/prepare_memphis.py --extract-only
.venv/bin/python scripts/prepare_memphis.py
.venv/bin/python -m unittest discover -s tests -p 'test_memphis.py' -v
```

## Tested master delivery

Tested commit `55ef01120872e58156d31ad46da5b2eed5554e66` is verified on remote master and expansion/all-states **2026-10-14 01:07:10 America/Chicago**, using fine-fiddle. All88 targeted Python/20 JavaScript tests,17 local browser assertions, nine exact HTTP/Git asset bindings and all23 changed release-file Git bindings pass independent review. The TODO now records actual completion: eight of the original66 districts finished,58 remaining. Four school attribution holds and all unavailable counts/floor/intervals remain. A push does not confirm deployment; Pages/public verification follows separately.

Pages run [38520339618](https://github.com/robot-assisted-projects/FRPL-RMA/actions/runs/38520339618) completed successfully for the tested release. Public readback passed **2026-10-14 01:10:08 America/Chicago**:12 browser assertions and nine independently fetched HTTP assets exactly match tested Git blobs. Public proof SHA `caab4440e9d7c2a24c69260dcfef597548b75dd38dac2391efa0de1edd4abf0d`. The deployed154 profiles,142/147/142 models, four attribution holds and unavailable sampling intervals agree with local verification.

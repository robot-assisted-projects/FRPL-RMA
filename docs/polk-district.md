# Polk original-source and cohort audit

The [source audit](../data/source/polk-district-audit.json), rebuilt by [audit_polk.py](../scripts/audit_polk.py), covers **2024–25**, exact NCES LEA **1201590**, CCD native LEA **FL-53** and FDOE district **53**. The source/cohort gate passed **2026-10-13 22:19:55 America/Chicago**. Historical status is `audit_pending`, scope `source_cohort_audit_only`; both source/modeling approvals remain false. This artifact creates no fits, canonical import or browser comparison.

## Exact school identities and populations

Seven original tables retain **2,026 records and 48,356 typed cells**, complete headers/notes and exact original row references. Nine original-file pins cover four CCD archives, three Florida workbooks and two primary definition PDFs; the frozen statewide extract is a tenth, separate cross-check. The original directory has 170 records: 163 Open, two Reopened, four Closed and one Future. All 165 operational school identities remain explicit. Exact documented `FL-53-####` codes join native `53-####`; names and corrected digits never establish identity.

There are 159 exact native fall/income matches and six operational IDs without native fall/income records: `53-0991`, `53-1201`, `53-2012`, `53-7004`, `53-9251` and `53-9252`. They stay unjoined, without inferred grades, income or outcomes. No native-only record is found. Of 117 operational offered-lower profiles, **110** satisfy the pure tested-grade contract: complete unadjusted lower offers including a grade 3–8, positive or protected-positive native enrolled grades 3–8 and explicit zero in every grade 9–12. High, mixed, primary and uncertain configurations remain outside. Planning counts do not approve models.

All 110 source profiles have usable individual income. Original published proficiency supplies **109 Math /109 ELA /109 paired Combined** prospective members. Compass Middle Charter, native `53-0932` /NCES `120159003925`, has usable income and enrolled grades 5–8 but no achievement row; its profile remains without a result. All twenty prospective charters remain, nineteen with published rates. Twenty-three profiles retain 79 protected native grade cells and 26 offered/enrolled disagreements; masks never become zero.

## Individual income and reporting differences

Use original **Final Survey 3, February 2025** individual D/F free eligibility plus 3/E reduced eligibility plus C/R direct certification, divided by the same school's own reported PK–12 denominator. Provision 2 code 4 must be explicit zero. Required district-option 6/9 conversions are already reflected in the published counts. Funding-adjusted counts/percentages, USDA 1.6 multipliers, universal meal access, the School Grades economic column and other-year income never replace this individual measure. CEP identification coverage and undercount remain unknown.

CCD LEA enrollment is **111,372**, while the operational-school totals sum to **116,440**: a **5,068** excess in the school sum. Retain both original totals and every school/grade record without assigning a cause, moving pupils or repairing identity. February school income, fall enrolled grades and full-year attributed performance match ID and academic year without claiming identical student membership. None supplies valid-score denominators.

## Original achievement and count limits

Use direct whole-percent **English Language Arts Achievement** and **Mathematics Achievement**, Level 3 or above, from the original 2025 School Grades workbook. No grade percentage averaging, component summation, funding/economic column or count-ratio precision is substituted. The primary calculation guide retains FAST PM3, prescribed B.E.S.T./Access Algebra 1 and Geometry EOCs and eligible FAA Performance Task, with Datafolio separate. Full-year enrollment, home-zoned attribution, above-enrolled-grade testing, two US-school-year ELL inclusion and medical/extraordinary exemptions remain native scope.

One provider-specific row for native `53-7001`, provider **302**, K12 Florida LLC, retains original Math 30 /ELA 45 at worksheet row 3061. It lacks matching provider income and is not assigned to the aggregate campus. No collocated row is found; the exclusion remains enforced.

The at-least-ten-eligible component rule does **not** establish ten valid scored students. Native valid-score denominators, the scored floor, sampling variances and intervals remain uncertified/unavailable. Enrollment, percent tested, participation and federal 95%-rule counts never substitute. Reuse the existing Florida hold; no repeated speculative count investigation is added. A separately verified point-only fit must leave counts, variances and interval endpoints null modelwide. Combined is the equally weighted mean of original paired Math and ELA rates with its own fit/studentization, not proficiency in both subjects.

## Verification and next gate

Thirteen focused source tests and eleven Florida/planning regressions pass. Two actual original-file CLI builds reproduce the exact frozen artifact; offline replay, compilation and both independent source reviews pass. A confirmed replay guard gap was repaired before this gate: all four raw/schema/definition/identity fingerprints now bind to an immutable current runtime contract. Altered raw/identity/primary evidence and coherent public checksum reassignments reject. Complete prior canonical bytes, all nine tables, 261 served assets and 333 preceding scientific files remain unchanged.

Next: independent full and deleted-school numerical verification; then separate normalized/canonical/static validation, repeat imports preserving previous data, browser checks and tested master delivery. Historical approvals remain false. Statewide Florida stays separate; high/mixed/primary, admissions, provider roles and geometry remain unaudited. The [fixed 66-district TODO](../TODO-breakout_districts.md) records source setup start **2026-10-13 21:56:38 America/Chicago**, with original-file reopening at 21:58:14, and keeps finish blank until verified master delivery.

```sh
.venv/bin/python scripts/audit_polk.py --extract
.venv/bin/python scripts/audit_polk.py
.venv/bin/python -m unittest discover -s tests -p 'test_polk_audit.py' -v
```

## Independent numerical audit

The compact [numerical audit](../data/source/polk-model-audit.json), rebuilt by [audit_polk_models.py](../scripts/audit_polk_models.py), verifies separate unweighted 2024–25 grade-school Math, ELA and Combined models. Original raw records remain stored once in the source audit. Every current, cached and expected replay verifies complete source/code/test/policy/raw/schema/definition/identity and immutable runtime evidence. Exact original inputs and typed row/column pointers remain linked.

| Diagnostic | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Usable schools | 109 | 109 | 109 |
| Intercept | 90.657935 | 89.923788 | 90.290862 |
| Disadvantage slope | -0.598339 | -0.616455 | -0.607397 |
| R² | 0.418555 | 0.500983 | 0.480033 |
| Maximum leverage | 0.139972 | 0.139972 | 0.139972 |
| Maximum Cook distance | 0.350452 | 0.285860 | 0.348552 |

All **327 explicit deleted-school fits** have rank two and positive finite residual scales, with full/deleted residual degrees of freedom 107/106 and no hard holds. Externally studentized residuals use the other members' fitted scale. Combined independently fits the equally weighted paired original rates, with its own residual scale, deletions and studentization; the common income vector explains coefficient linearity but never permits averaging subject t scores or scales.

All nineteen rated charters remain included. Cypress Junction Montessori (`53-8171` /NCES `120159008572`) has the highest Cook distance in every subject, with Math/ELA/Combined t approximately -2.756641/-2.473391/-2.748625, and stays in all three models. Lakeland Montessori School House (`53-8141` /NCES `120159004178`) retains the highest leverage and the original 5/122 individual eligibility ratio. Source incomes range 4.09836%–99.04031%. Observed predictions lie in 0–100, but the linear model remains unbounded and unclamped; a synthetic endpoint verifies this behavior. No enrollment weights, shrinkage, admissions inference or diagnostic exclusions are introduced.

All 110 source profiles, Compass's missing achievement, protected grades, exact unjoined identities, provider-specific attribution and the unassigned reporting discrepancy remain linked. Valid-score counts, the scored floor, sampling variances and intervals remain uncertified/unavailable modelwide; any internal zero-variance computational vector is a point-estimate sentinel, never an uncertainty estimate.

Sixteen numerical tests, two actual byte-identical CLI builds, offline replay and compilation pass. The independent review verifies **184,185** original input/pointer/math fields, all 327 NumPy deletions, three 60-digit full fits and ten selected high-precision deletions, with maximum difference `1.82e-12`. All **202** metric/input/degeneracy/current-evidence rejection checks and six controls pass. Complete prior canonical bytes/all nine tables, 261 served assets and the 336 preceding scientific files remain unchanged; concurrently created Memphis source files are separate authorized work. Gate verified **2026-10-13 22:37:20 America/Chicago**.

```sh
.venv/bin/python scripts/audit_polk_models.py
.venv/bin/python scripts/audit_polk_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_polk_models.py' -v
```

Status remains `numerically_verified_pending_integration`, scope `numerical_audit_only`, with both historical source/modeling approvals false. Isolated normalized/canonical/static validation and independent review follow; actual main imports, browser checks and tested master delivery remain held until those separate gates pass.

## Canonical and browser integration

The separately validated [normalized release](../data/source/polk.json), rebuilt by [prepare_polk.py](../scripts/prepare_polk.py), supplies dataset `fl-polk-2025` /region `polk` readiness. All six historical source/numerical files retain false approvals. Complete current evidence, literal runtime contracts, normalized fingerprints and all nine ownership tables are validated before canonical writes. Legal statewide/district identity overlap is preserved.

The release retains all110 exact native `53-####` profiles and authoritative NCES crosswalks,110 same-year individual February economic observations,220 native subject observations,17 provenance records and three independent109-school models. All327 canonical/current/history results match original-source verification. Compass remains searchable and inspectable with unavailable achievement; all twenty profile charters, nineteen rated charters, protected grades, influential Montessori members, six missing native identities, the provider-specific exclusion and5,068-pupil reporting difference remain explicit. No count floor, valid-score counts, variance or sampling intervals are certified. Admissions, provider roles and geometry remain unaudited.

Fourteen adapter tests, two identical actual normalized CLI builds and two private full-database-copy imports pass. Independent review verifies122,741 original/canonical/current/history comparisons and305 rejection cases before writes. Two separately authorized actual main imports preserve all preceding rows in nine tables and261 previous served files; target rows and four export bytes repeat exactly. The six historical audit files remain immutable.

Two identical catalog/guide/planning rebuilds add only exact Polk1201590, preserving66 previous regions,83 definitions/provider bindings and geometry. Catalog:39 states /67 regions; guide84 definitions, eleven source holds unchanged. All90 distinct targeted Python tests (13 source,16 numerical,14 adapter and47 shared regressions),20 JavaScript tests, syntax and diff checks pass. Independent final preservation review has no findings.

Fifteen local HTTP/browser assertions pass **2026-10-13 23:23:17 America/Chicago**: fresh first off-page Winston search and keyboard selection, pagination, all109 fixed points, Compass's missing results, each influential Cypress Junction subject/history result, highest-leverage Lakeland Montessori School House, unavailable intervals, restored shares, empty/invalid selections, eight Florida guide links and390-pixel layout. No application or required-data failures were found. Tested master delivery and public-site readback are recorded separately; finish remains blank until remote verification.

```sh
.venv/bin/python scripts/prepare_polk.py --extract-only
.venv/bin/python scripts/prepare_polk.py
.venv/bin/python -m unittest discover -s tests -p 'test_polk.py' -v
```

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

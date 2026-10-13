# Charlotte-Mecklenburg district audits

The historical **source/cohort audit** is for Charlotte-Mecklenburg Schools, North Carolina, school year **2024–25**: exact NCES LEA **`3702970`**, CCD native LEA **`NC-600`** and DPI PSU **`600`**. [audit_charlotte.py](../scripts/audit_charlotte.py) builds [charlotte-district-audit.json](../data/source/charlotte-district-audit.json) from pinned original files. Status remains **`audit_pending`**, scope **`source_cohort_audit_only`**, and both **`approved_for_source`** and **`approved_for_modeling`** remain **false**. It contains no fitted results. The separately verified numerical phase below also retains false approvals. Readiness belongs only to the separately validated normalized grade-school integration below.

The statewide North Carolina extract is retained as a checksum-pinned cross-check. Its existing point-only source approval does not approve a separate district model. Discovery counts do not determine source membership, and this audit does not extend high-school, mixed-school or alternate-assessment populations.

## Original records and identity

The audit retains all **186 original CCD school directory rows**, all operational: **184 Open and two New**. It preserves exact status, school type, charter and offered-grade flags, NCES and native IDs, original headers, raw cells and original row numbers. There are no nonoperational district rows in this pinned directory release. All 186 are noncharter; observed types are 181 Regular, two Alternative, two Special Education and one Career and Technical. School-type labels do not impose an additional eligibility filter. The CCD directory has no virtual-status field; its value remains unavailable rather than inferred from a name.

| Retained original table | Records | Purpose |
|---|---:|---|
| CCD school directory | 186 | Exact district roster, statuses, types and offered grades |
| CCD school membership total and grade rows | 1,457 | Same-year school totals and complete grade evidence |
| CCD LEA directory | 1 | Exact district identity and discovery reference |
| CCD LEA membership total and grade rows | 17 | Original district fall population |
| DPI All Students performance | 5,667 | Every retained subject, grade and assessment type |
| DPI April 2025 EDS | 187 | All 186 schools and the separate district aggregate |
| DPI RCD location | 187 | All 186 schools and the separate district aggregate |

These seven inventories contain **7,702 rows and 129,992 typed raw cells**, in addition to the complete retained PDF definitions, original EDS webpage markup and RCD data dictionary. Twelve originals are pinned by official URL, local path, byte size and SHA-256. Native performance row numbers refer to the original tab-delimited member; workbook references retain worksheet and row number. ZIP member paths and the RCD location member checksum remain linked to their archive sources.

Identity joins require the same-year CCD `LEAID`, `ST_LEAID`, `NCESSCH` and `ST_SCHID`, plus exact DPI school codes. For example, `NC-600-300` maps to native school code `600300` and NCES `370297001186`; neither a school name nor PSU prefix alone establishes a match. The original RCD location file and dictionary independently retain exact `year`, `agency_code`, `agency_level`, `lea_code`, native grade span, category and school type. Their classifications remain supplemental evidence: they do not replace CCD membership, change native RG/GS scope, establish admissions/provider roles or add another cohort filter.

All selected individual school assessment and April income identities match the original directory. The district aggregate `600LEA` is retained separately in assessment, income and RCD inventories; it never becomes a school. Three schools have no retained All Students assessment rows: the two PK–2 primaries below and high-school `600404` (Harper Middle College High). This absence is preserved, not filled from district or alternate aggregates.

## Offered, enrolled and prospective assessment populations

The original offered-grade flags separate **146 grade-school configurations, 32 high schools, six mixed schools and two primary-only schools**. Complete lower-grade membership contracts include **148 schools**, because the two PK–2 primaries satisfy lower-grade enrollment reconciliation before tested-grade applicability is checked. At least one explicitly offered grade 3–8 is required for a prospective assessment configuration; that leaves **146**. Their exact native regular GS pairs, compatible native lower-grade spans and usable April individual EDS establish **146 source profiles**.

| Prospective population | Profiles | Math usable | ELA usable | Combined usable |
|---|---:|---:|---:|---:|
| Complete lower membership contracts | 148 | 145 | 146 | 145 |
| Tested-grade configurations / native source profiles | 146 | 145 | 146 | 145 |
| High configurations | 32 | 0 | 0 | 0 |
| Mixed configurations | 6 | 0 | 0 | 0 |
| Primary-only configurations | 2 | 0 | 0 | 0 |

Lower membership requires unadjusted reported PK–8 offerings, no high/adult grades, complete reported lower-grade counts that reconcile to the school total, and literal zero outside-grade records with their original Reported/Derived flags. The exact Derived-zero **Not Specified / Not Specified / Not Specified** row establishes no unallocated enrollment; it is not a suppressed grade or a verified tested count. Other Derived counts remain unverified. Missing, suppressed or positive outside-grade membership cannot silently become zero. Offered and enrolled evidence remain separate.

**Billingsville Elementary, `600335` / `370297001201`, and Dilworth Elementary, `600519` / `370297001268`, offer only PK–2.** They retain April economic enrollment/EDS of `356 / 43.3%` and `407 / 15.2%`, respectively, but have no applicable grade 3–8 assessment. They are retained in lower-contract and primary coverage, outside tested source profiles. **Turning Point Middle, `600598` / `370297003663`, is CCD Alternative**, offers grades 6–8 and has published Math 9.4% / ELA 14.6%; it remains eligible under the same source rules. No Regular-only filter removes it.

**Knights View Elementary, `600387` / `370297003648`, has native Math `>95` and ELA 90.7%.** The Math mask remains unavailable and excludes Math and Combined, while ELA remains usable. Original Math/ELA rows 1,012,163 / 1,012,304, April EDS row 1,569 and directory row 66,380 remain linked. The mask is not replaced with 95, an endpoint, an achievement-level reconstruction or an alternate type. Math and Combined each have 145 eligible identities; ELA has 146. Combined requires both eligible native subject rates and equals their equally weighted mean, not the percentage proficient in both.

Discovery reconstructs **146 ES and 25 HS** from original directory and membership rows, with LEA fall enrollment **147,299**. Its ES identities happen to match the 146 native source profiles; the sole Combined difference is Knights View. Seven of the 32 high configurations offer grade 13 and remain outside the planner's HS screen: `600334`, `600404`, `600443`, `600498`, `600567`, `600569` and `600594`. These are discovery distinctions, not approvals or district model filters.

## Individual April income and population differences

The [DPI EDS collection definition](https://www.dpi.nc.gov/documents/economically-disadvantaged-data-collection/open) and [DPI economic-disadvantage page](https://www.dpi.nc.gov/data-reports/economically-disadvantaged) define individual economic eligibility through direct certification, categorical statuses and optional locally verified financial need. The collection covers currently enrolled students, including PK through grade 13 and ungraded, with charter PK excluded. CEP or universal free meals alone does not confer individual EDS eligibility. The retained webpage's stale CEP reimbursement-threshold discussion does not define the individual predictor.

Use published **`pct_eds` from the `APR 2025` worksheet**, with its own current-enrollment denominator `den`. Do not use `pct_nslp`, adjusted reimbursement, a 1.6 multiplier, the tested EDS subgroup, fall enrollment or an inferred low-income numerator. All 186 school April rows have usable individual EDS and positive economic enrollment; no zero or unavailable income ratio is observed here. Numeric zero would remain a valid recorded percentage under the same rule, distinct from a range, suppression or absence.

Original CCD school fall totals sum to **145,014**, while the separate original LEA total is **147,299**, a retained **2,285-student gap**. LEA membership total row 2,530,267 and all 16 original grade rows reconcile to 147,299; the LEA directory row is 13,259. Summing the retained original grade rows locates the entire observed difference in PK: **5,600 at LEA level versus 3,315 across individual schools**; every other grade subtotal agrees. This arithmetic does not establish the gap's cause, allocate it to schools or repair membership. April school economic enrollment sums to **145,900**, exactly matching the separate April district aggregate at worksheet row 1,517. **183 schools differ between April and fall enrollment**. The timing and populations remain explicit; these counts never supply a valid-score denominator or a proficiency weight.

Within each eligible subject set, EDS spans **5.2–83.4%**. Math/Combined have 125 distinct values and sample standard deviation 17.470 percentage points; ELA has 126 distinct values and sample standard deviation 17.588. These are descriptive source-coverage measures, not fitted diagnostics or a causal effectiveness claim.

## Native proficiency, suppression and uncertified counts

The [original DPI performance ZIP](https://accrpt.tops.ncsu.edu/docs/disag_datasets/Disag_2024-25.zip) supplies published **Grade-Level Proficiency (GLP), Achievement Level 3 and above**, for native individual-school `subgroup=ALL`, `type=RG`, `grade=GS` and `subject=MA/RD`. GS means grades 3–8 and includes **grade 8 NC Math 1 EOC** in Math. It is distinct from College-and-Career Ready Levels 4–5. The source definition says the 2024–25 results include **2024 summer school**; this retained assessment population need not match the April EDS children exactly.

All original All Students types are retained: **2,640 RG, 2,658 ALL and 369 X1 rows**. The embedded description calls the alternate code `EXT1`, while the actual native file uses `X1`; the discrepancy stays explicit. Its standalone Math 1 note says grades 9–12, while subject/grade codes say grades 9–13. Neither issue changes the exact RG/GS selection. Grade rows, alternate or all-type totals, EOG/EOC/all-subject aggregates, standalone high-school Math 1 and district rates never substitute for eligible RG/GS Math or ELA, and no grade percentages are averaged.

Published exact numeric percentages from 0 through 100 are retained. `<5`, `>95`, dash, stars, ranges and blanks remain unavailable. The [2024–25 technical guide](https://www.dpi.nc.gov/dpischoolgradetechnicalguidedraft2024-25/open), sections 3.1–3.1.3, distinguishes test-results reporting from School Performance Grades and long-term goals subject to the federal 95% denominator adjustment. No SPG or long-term-goal rate enters this audit. `num_tested` is retained as raw **unverified** evidence; completed tests, enrollment, participation and federal adjusted denominators are not interchangeable verified valid-score counts.

Every verified subject count, sampling variance and sampling interval remains null/unavailable. A ten-valid-scored minimum remains **uncertified**, even where a publication is numeric; publishing a point rate does not certify that floor. The prospective 30-school cohort floor is met by all three subject sets, but provides no source/model approval. Any later point-only numerical model must omit sampling intervals modelwide. High, mixed, unknown and alternate populations remain unreleased.

## Rebuild, replay and remaining gates

The complete statewide source extract is pinned at SHA-256 `8d8cc1a75bbd58b1a73188aef9ad63c3008b9bf3d1334e4b3158e115caf70f28`; its canonical North Carolina snapshot has SHA-256 `fbaf4d121210b4a0b6f039d3693933f77f7c463168bb82dee880804cb46982c0`. All original retained rows, headers, definitions, supplemental location/dictionary and discovery records have canonical SHA-256 **`f9024f38c5a7bf179f94e0afa674fbb0ca8298b440c3352f70ff424abfd02c09`**, enforced unconditionally. No development bypass remains.

Ordinary validation is offline and reads only the committed audit and pinned statewide extract. It never opens original ZIPs, workbooks, ignored caches or a database:

```sh
.venv/bin/python scripts/audit_charlotte.py
.venv/bin/python -m unittest discover -s tests -p 'test_charlotte_audit.py' -v
```

Explicit extraction verifies all twelve original file fingerprints, streams both original CCD membership archives including the school archive's Deflate64 member, reopens the original DPI performance ZIP and April workbook, and rereads the original RCD ZIP, dictionary, PDFs and webpage:

```sh
.venv/bin/python scripts/audit_charlotte.py --extract
```

`--output PATH` writes an alternate audit for reproducibility checks. Two fresh original-source CLI builds reproduce the committed **4,689,158 bytes**, SHA-256 **`7c6ab608d7d9b71e639b527054877b5dac5fcd9e5d1313021ee1e7017c125398`**; copies and logs are retained under ignored `data/build/charlotte-source-implementation/resumed-original-{one,two}` paths. Offline replay matches that artifact.

Twelve focused tests cover original full inventories/typed references, exact identities and years, lower versus tested/primary populations, Knights View subject suppression, Alternative-school inclusion, original April/fall/LEA differences, discovery reconciliation, real-zero versus unavailable/proxy income, native scope and definition discrepancies, Combined, uncertified counts/floors, immutable false approvals and raw-disabled offline replay. Exact typed fingerprints reject missing/extra records, source/header/row changes, wrong populations, booleans versus numeric counts, fabricated sampling evidence and approval drift. Semantic tests with independently repinned fixtures also exercise direct identity, collection-year, demographic/scope and strict integer header-reference gates.

Independent original-source/cohort review, numerical diagnostics and any separately validated canonical/static integration remain distinct gates. This source artifact records no fitted results, new provider/admissions role, ready comparison, deployment or change to existing district/state comparisons. Issue #3 and incomplete source holds remain open.

## Independent numerical audit

[charlotte-model-audit.json](../data/source/charlotte-model-audit.json) and [audit_charlotte_models.py](../scripts/audit_charlotte_models.py) freeze the complete source artifact, source code/tests and policy. Original records reconstruct exact source eligibility before fitting. Three unweighted district models use same-year April individual EDS and native regular RG/GS/ALL published GLP rates. Statewide North Carolina residuals and coefficients are not reused.

| Diagnostic | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Usable schools | 145 | 146 | 145 |
| Intercept | 102.572300 | 95.652984 | 98.863298 |
| Income slope | -0.880229 | -0.911716 | -0.891756 |
| R² | 0.628451 | 0.665790 | 0.672709 |
| Maximum leverage | 0.050724 | 0.049389 | 0.050724 |
| Maximum Cook distance | 0.053324 | 0.034777 | 0.036543 |
| Largest deleted prediction change across observed income range, percentage points | 0.710972 | 0.549577 | 0.538361 |

All full and **436 explicitly deleted-school fits** have rank two and positive finite residual scale. Full residual degrees of freedom are 143/144/143; deleted residual degrees of freedom are 142/143/142. Externally studentized residuals use the scale estimated from the other `N−1` members with `N−3` degrees of freedom. Combined has its own 145-school fit of equally weighted subject rates; averaging subject coefficients or residual scores is not equivalent.

Income spans 5.2–83.4%. Diagnostic flags are descriptive and never remove a school. Turning Point Middle remains in every fit, including its Math influence flag; Knights View remains ELA-only. Observed-range deletion sensitivity does not certify extrapolation, causal effectiveness, enrollment adjustment or shrinkage.

Every valid-score count, sampling variance and interval endpoint remains null modelwide. The ten-valid-scored floor is uncertified. Internal computational zero-variance sentinels do not claim zero sampling uncertainty. All original masks, enrollment differences, assessment/income populations and outside configurations remain retained. The numerical artifact's status is `numerically_verified_pending_integration`, scope `numerical_audit_only`, and both approvals remain false.

Offline numerical rebuild and replay:

```sh
.venv/bin/python scripts/audit_charlotte_models.py
.venv/bin/python scripts/audit_charlotte_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_charlotte_models.py' -v
```

Two actual fresh CLI builds reproduce **11,411,144 bytes**, SHA-256 **`4fcae9ab70d5b2bb16fdece4cd198919e7b3616c6a3915ee003829b8b7ec02ab`**. All twelve focused tests pass. Two independent reviews reconstruct original evidence and fits: the full review verifies 22,294 typed comparisons, all twelve source pins and every deletion; a complementary 50-digit Decimal review checks all full fits and twelve selected deletions. Maximum independent difference is `3.64e-12`; **115 additional corruption/degeneracy attacks** are rejected. Prior canonical and served data remain unchanged at this gate.

The separately validated canonical/static integration below replays these immutable gates; HTTP/browser verification and tested master delivery are recorded separately. High/mixed populations, admissions, geometry and assessment provider roles remain unaudited.

## Canonical and browser integration

[charlotte.json](../data/source/charlotte.json) is the separately validated published-rate release contract for dataset **`nc-charlotte-2025`**, region **`charlotte`**. [prepare_charlotte.py](../scripts/prepare_charlotte.py) pins all six historical source/numerical artifact, code and test files, replays native eligibility and numerical evidence before importing, then independently verifies canonical and static results. Only this normalized grade-school contract has source/modeling approval true. Historical audits remain byte-identical with false approvals.

All **146** tested-grade profiles and same-year April incomes remain searchable. Native outcomes contain 291 exact rates and Knights View's single Math mask, yielding **145 Math / 146 ELA / 145 Combined** results. Turning Point remains in all three models. The full 186-school roster, 148 lower membership contracts, twelve original pins, 7,702 original rows, all typed raw cells and forty outside configurations remain in provenance. No fit diagnostic screens membership. Enrollment and native unverified tested evidence never become valid-score counts: every verified count, sampling variance and interval endpoint remains null modelwide, and the ten-score floor remains uncertified.

The three independent district fits and every current/one-year-history metric match the numerical audit. April income uses its own broader enrolled population; native regular grade-3–8 GLP includes grade-8 Math 1 and the summer-2024 attribution. High/mixed/primary populations, alternate totals, admissions, provider roles and geometry remain unreleased/unaudited. Programs stay Unclassified; map coordinates and boundaries remain unavailable. Statewide North Carolina and Wake County keep separate models and comparison links.

Offline rebuild from committed evidence:

```sh
.venv/bin/python scripts/prepare_charlotte.py --extract-only
.venv/bin/python scripts/prepare_charlotte.py
.venv/bin/python scripts/export_catalog.py
.venv/bin/python scripts/export_assessment_guide.py
.venv/bin/python scripts/plan_district_comparisons.py
```

The descriptor is automatically discovered by `prepare_states.py`. Two actual normalized builds reproduce SHA-256 **`6e1e8bf9eac231b804085a23c97eb23e16ea8cbf91d92b556a152a48355fce85`**. Two actual live imports preserve every prior row in all nine canonical tables and every prior regional/geometry asset; the complete table contents and four Charlotte exports repeat identically. Repeated catalog/guide/planning output is byte-identical. The catalog contains **39 ready states / 61 ready regions** and the assessment guide **78 separate definitions**, retaining eleven state holds. Discovery now has 65 remaining first-tier candidates; the fixed 66-district TODO retains Charlotte's row.

All eleven focused integration tests and 59 relevant source/planning/catalog/snapshot/guide regression tests pass, with all twenty JavaScript URL/guide tests and syntax/diff checks. Independent original-input/canonical/current/history checks match 19,914 values within `1.85e-13`. Two independent integration reviews pass, including 70 complementary corruption/namespace/policy attacks and four valid controls. Three actual preparation calls reject corrupted inputs before writing. Historical approvals, unknown counts and unaudited outside populations remain intact.

HTTP browser verification passes the first search after reload for off-page Turning Point, keyboard selection, all 146 searchable profiles with pagination, Knights View ELA-only eligibility and Math/Combined masks, selected/all-filtered scope without refitting, share restoration, explicit empty selection, invalid URL fallback and one-year chart/table/history values with unavailable intervals. Desktop and true 390-pixel mobile layouts have no document overflow or console warnings/errors. The guide retains 50 state cards, eleven holds and separate North Carolina statewide/Wake/Charlotte links, with provider and target fields unknown. Its native scope and broader income population remain explicit. Master delivery is recorded after remote verification.

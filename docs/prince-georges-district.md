# Prince George's County audit and comparison

The [source-only audit](../data/source/prince-georges-district-audit.json), rebuilt by [audit_prince_georges.py](../scripts/audit_prince_georges.py), covers Prince George's County Public Schools, Maryland, **2024–25**, exact NCES LEA **2400510**, CCD native LEA **MD-16** and MSDE LEA **16**. Source and modeling approvals remain false. Status is `audit_pending`, scope `source_cohort_audit_only`. Numerical models, canonical integration and browser/master delivery are separate later gates.

The complete original inventories retain 201 CCD directory records and 204 native school-directory entries, with exact native two-digit LEA/four-digit school codes and authoritative NCES crosswalks. Native Ellen Ochoa Middle (`16-0218`) publishes malformed 11-digit NCES `24005109050`; no original provides an authoritative correction to CCD `240051090501`. Preserve both records without inferred composition, slicing or a name join. All unmatched, closed, unknown-span, high, mixed, primary and adjusted-offer records remain explicit.

Eight original tables retain 5,404 source rows and 89,640 typed raw cells, with original headers, source rows and eleven whole-file URL/size/checksum pins. Primary MSDE definition HTML, report-card notes and the March 2025 MCAP overview remain linked to their exact historical scope. Current definition links to 2026 suppression guidance never establish 2025 rules.

Source eligibility requires exact operational CCD ownership, native E/M/EM span, complete unadjusted lower offered grades with grades 3–8, at least one positive native September grade 3–8 count and no high-grade row. Reported zero, unknown, ungraded/adult and adjusted flags remain distinct. Discovery size counts cannot select a model. The independently inventoried prospective cohort has 159 exact grade-school profiles, all with usable same-year individual economic ratios; all six charter profiles remain included.

Use original regular **School_Level, Year 2025, All Students, All Grades** MCAP Mathematics and English Language Arts published proficiency percentages, under the regular Levels 3 and 4 standard introduced in 2021–22. DLM remains separate. Native Math includes accelerated Algebra 1/Geometry/Algebra 2; the March 17, 2025 grade 6–7 course-substitution waiver applies from 2024–25 through 2027–28. Course-row presence, component counts and count arithmetic never certify unique valid scores or substitute for the published All Grades percentage. Native Math's thirteen `<= 5.0` masks remain unavailable; prospective Math/ELA/Combined membership is 146/159/146. Combined is the equal mean of available subject rates and would require its own fit over the paired cohort. Math/ELA populations differ; subject fit coefficients or studentized scores cannot be averaged.

Income uses original individual **Early Attendance economically disadvantaged count / its own total student count**, reconciling the native one-decimal display while preserving the exact ratio. Use the whole-school All band where multiple school bands exist. Direct certification includes benefits and categorical statuses; it is separate from FARMS, universal meals, household income and tested-student poverty. The precise Early Attendance as-of date is unspecified. Never replace its denominator with September or CCD enrollment, infer missing cells as zero or backfill another year.

Native September school/district totals are 132,151 versus CCD 132,123, a difference of 28. The unmatched native JACS row reports 28; those facts do not prove the administrative cause or repair ownership. Early Attendance district total 133,427 equals the sum of known native school denominators, while six denominator cells remain unavailable. Aggregate equality never allocates the missing values or makes them zero.

Administrative tested counts and the ten-valid-scored floor remain uncertified. Valid-score counts, sampling variances and intervals remain null/unavailable. Source success cannot approve high/mixed assessment populations, admissions, programs, provider roles or geometry. Two original builds, strict offline replay and independent source reviews precede numerical work. No district finish date or ready catalog entry is created at the source gate.

## Rebuild and verification gates

```sh
.venv/bin/python scripts/audit_prince_georges.py
.venv/bin/python scripts/audit_prince_georges.py --extract --output data/build/prince-georges-replay.json
.venv/bin/python -m unittest discover -s tests -p 'test_prince_georges_audit.py' -v
```

Ordinary replay is offline and opens only committed evidence. Explicit reconstruction verifies every whole original pin and rereads the archives, workbooks, CSVs, HTML and primary PDF. Two actual source reconstructions reproduce **4,845,702 bytes**, SHA-256 **`f097fb88001cb3749fc5ebc31a5786421fa3aebad207d61172ad3baed8a6d33a`**. All eighteen focused source tests, offline replay and compilation pass. The complete canonical database, every prior row in nine tables, all 245 served assets and 289 prior source/code/test files remain unchanged.

Both independent source reviews pass: fresh original reconstruction verifies 166,361 typed original/derived comparisons, 38 corruption rejections and 22 controls. Complementary review independently verifies all eleven primary source pins, 53 primary/population/helper controls and 86 further corruption attacks, including repinned raw/schema cases. All **124 additional corruption rejections** pass, with no remaining source-review finding. Ellen's native and CCD records remain separate and unjoined; the 45 native outside profiles, six unmatched native records, three unmatched CCD records and two closed CCD records are distinct evidence views, never one forced combined count. No numerical fit, normalized release, catalog or browser change is created at this milestone. The original [66-district TODO](../TODO-breakout_districts.md) retains the started date and blank district finish date. Numerical full/deleted fits, a separately validated point-rate contract, repeated canonical/static preservation and HTTP/browser checks must all pass before master delivery. Counts and all outside populations remain explicit holds.

## Independent numerical audit

The compact [prince-georges-model-audit.json](../data/source/prince-georges-model-audit.json), rebuilt by [audit_prince_georges_models.py](../scripts/audit_prince_georges_models.py), independently verifies three unweighted 2024–25 district models. The full original source is stored once; every numerical replay, including cached expected validation, requires current complete source/code/test/policy/raw/schema/definition evidence. Exact identities, original table/worksheet/row/field pointers, x/y, all full/deleted fits and exclusions remain auditable without duplicating the raw tables.

| Diagnostic | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Usable schools | 146 | 159 | 146 |
| Intercept | 48.347324 | 91.020755 | 69.671338 |
| Disadvantage slope | -0.556076 | -0.983258 | -0.765498 |
| R² | 0.366295 | 0.687735 | 0.589896 |
| Maximum leverage | 0.080488 | 0.078252 | 0.080488 |
| Maximum Cook distance | 0.681454 | 0.482766 | 0.518447 |

All **451 explicit deleted-school fits** have rank-two designs and positive finite scales, with no hard holds. Full residual degrees of freedom are 144/157/144 for Math/ELA/Combined; deleted degrees of freedom are 143/156/143. Externally studentized residuals use the scale estimated from other members.

Combined fits the equal mean of the original paired subject rates over 146 schools. Its coefficients differ from averaging the complete 146-school Math and 159-school ELA fits. The paired 146-school ELA linear identity is independently checked, but Combined still has its own scale, deletion fits and studentized scores. Thirteen Math masks remain ELA-only; all six charters remain included. Glenarden Woods' Math t about 7.09 /Combined t about 5.94 and Imagine Andrews' ELA Cook distance about 0.483 are retained. Influence diagnostics describe sensitivity and never remove eligible schools or infer admissions, causal effectiveness or school quality. Observed-income predictions happen to lie in 0–100; the linear model is not clamped or enrollment-adjusted.

Fifteen numerical tests pass. Two actual fresh builds reproduce **1,249,923 bytes**, SHA-256 **`8594f53d2722b913bf1907a0c0d8c53c21405c64b3d108a7b722706281b8f661`**; offline check, compilation and diff checks pass. Both independent reviews verify **174,478 original input/reference/model comparisons**, every NumPy full/deleted fit and 24 selected 50-digit Decimal deletions. All **199 additional corruption/freshness rejections** pass, with maximum scalar difference `3.64e-12`. Complete canonical bytes, prior rows in all nine tables and all 245 served assets remain unchanged.

```sh
.venv/bin/python scripts/audit_prince_georges_models.py
.venv/bin/python scripts/audit_prince_georges_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_prince_georges_models.py' -v
```

Status is `numerically_verified_pending_integration`, scope `numerical_audit_only`, and both historical approvals remain false. Valid-score counts, the scored floor, sampling variances and intervals stay unavailable/uncertified modelwide. Malformed/unmatched identities, broader individual-income population, unspecified Early Attendance date, waiver, DLM separation and all outside records remain unchanged. Separately validated normalized scope, actual repeated canonical imports/exports, preservation and HTTP/browser review must pass before master delivery.

## Canonical and browser integration

The separately validated normalized [prince-georges.json](../data/source/prince-georges.json) supports dataset **`md-prince-georges-2025`**, region **`prince-georges`**, Maryland → Prince George’s County. All **159** exact pure grade-school profiles remain searchable. Native `16-####` school IDs preserve their exact twelve-digit NCES crosswalk and CCD `ST_SCHID`; every identity belongs to its dataset. Identical native IDs in the statewide Maryland, Florida and Delaware populations retain separate ownership. Ellen Ochoa's malformed native NCES remains unjoined.

The release retains **318 original subject observations, three models and 451 results**: 146 Math, 159 ELA and 146 independently fitted Combined members. Thirteen original Math masks remain ELA-only. All six charters and influential Glenarden Woods /Imagine Andrews observations remain. Precise individual Early Attendance ratios use their own whole-school denominators; the as-of date remains unspecified. Regular MCAP All Grades Levels 3–4, accelerated courses, the applicable grade 6–7 waiver and DLM separation remain explicit. Programs stay Unclassified; coordinates, boundaries and provider roles are unavailable.

Historical source and numerical approvals remain false. Readiness belongs only to this exact normalized population. Every replay, including cached paths and preparation before writes, verifies all six complete historical artifact/code/test pins and current policy/definition/raw/schema/identity evidence. Complete raw originals are stored once and referenced through auditable table/worksheet/row/field pointers. A cached live-policy validation gap found during review was repaired in the adapter and tested; the immutable historical artifacts and all numerical values remain unchanged.

Valid-score counts, variances and sampling endpoints remain null throughout every model. Administrative counts never certify score status or the ten-valid-scored floor. High/mixed/primary populations, admissions, provider roles and geometry remain unaudited. Source/model diagnostics never repair missing identities or remove influential eligible schools.

Two actual canonical imports and four district exports repeat exactly. All preceding rows in nine canonical tables and all 245 prior served files remain unchanged before shared catalog/guide regeneration. Independent verification matches all original/canonical/current/history metrics, including all 451 deleted-school fits, with maximum numerical difference `3.41e-13`. Ownership and freshness probes reject altered normalized records, live policies and foreign source/definition/model references before writes.

Repeated shared exports are byte-identical. Only one district region and assessment definition are added, retaining all 62 prior regions, 79 prior guide definitions and provider bindings, geometry and eleven state source holds. The catalog has 39 ready states /63 regions; the guide has 80 definitions. Discovery scope changes only exact LEA `2400510` to an existing comparison, preserving all original planning counts. The original fixed 66-district TODO retains its row and records a finish only after verified master delivery.

```sh
.venv/bin/python scripts/prepare_prince_georges.py --extract-only
.venv/bin/python scripts/prepare_prince_georges.py
.venv/bin/python -m unittest discover -s tests -p 'test_prince_georges.py' -v
```

All **93 distinct targeted Python tests** pass: 18 source, 15 numerical, 13 adapter/integration and 47 Maryland/shared regressions. All twenty JavaScript guide/URL tests and syntax/diff checks pass. HTTP/browser verification passes **26 assertions**, covering first post-reload off-page search, keyboard selection, 75→150→159 pagination, all thirteen Math/Combined masks with ELA retained, fixed models, influential cases, chart/table/history gaps, sharing, explicit empty selection and invalid IDs. Maryland's three separate guide populations, primary waiver/DLM sources and unknown provider roles remain explicit. True 390-pixel layout has no page overflow; keyboard access can scroll the history table. Browser warnings/errors are empty. Eight actual HTTP assets and nineteen release/shared Git blobs match tested source commit `46a12b9`. Master and public delivery are recorded separately in the [publication log](publication-log.md).

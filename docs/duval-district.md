# Duval source and cohort audit

The historical [source/cohort audit](../data/source/duval-district-audit.json), rebuilt by [audit_duval.py](../scripts/audit_duval.py), covers Duval County Public Schools, Florida, **2024–25**, exact NCES LEA **`1200480`**, native CCD LEA **`FL-16`** and Florida district **`16`**. Status is `audit_pending`, scope `source_cohort_audit_only`; both source/modeling approvals remain **false**. This artifact creates no models, canonical import or website comparison. Numerical and normalized/browser release gates follow separately.

Seven original tables preserve **2,495 records /59,985 typed cells**, complete headers, worksheet notes and source-row references. Ten complete original/secondary file pins include all four CCD archives, three native workbooks, both primary definition PDFs and the separately pinned statewide extract. The statewide extract is a cross-check, never a source of district fits. Ordinary replay is offline; explicit reconstruction reopens the originals and verifies their complete byte checksums.

| Retained source table | Records |
| --- | ---: |
| CCD school directory | 211 |
| CCD LEA directory | 1 |
| CCD school total/grade membership | 1,688 |
| CCD LEA total/grade membership | 16 |
| Native fall grade membership | 201 |
| Native February individual income | 201 |
| Native School Grades achievement | 177 |

## Exact identity and enrolled populations

All 211 directory records remain explicit: 201 Open, one New, one Reopened and eight Closed. There are **203 operational schools**, of which 200 match exact same-year native fall IDs. Only the documented CCD `FL-16-####` format maps to native `16-####`; exact NCES identities and source rows remain retained. Names never establish a join. Three operational IDs lack fall records: `16-1981`, `16-7001`, `16-7004`. Native-only `16-0734` remains outside the CCD operational roster.

The prospective population requires complete, unadjusted pure lower CCD offers with an offered grade 3–8, positive or protected-positive native enrolled grades 3–8, and explicit zero in every native enrolled grade 9–12. Protected values never become zero. High, mixed, primary, unknown, closed and unmatched configurations stay outside. The 155 operational offered-lower profiles yield **150 tested-grade profiles**; twenty profiles contain 65 protected grade cells, and 22 offered/enrolled disagreements remain auditable.

Discovery's 151 potential grade schools differ from the source population: Smart Pope Livingston `16-1491` /NCES `120048000704` offers through grade 3 but has zero native enrolled grades 3–8 and no native School Grades row. It stays outside. Planning size or future fit quality never selects members.

All 150 source profiles have usable individual income. Four lack a native achievement row (`16-0061`, `16-0271`, `16-0281`, `16-0171`); missing outcomes stay unavailable, never zero. Original published-rate availability is **146 Math /146 ELA /146 Combined**, with all **30 usable charters** retained. All 61 directory exclusions and every native-only record remain linked to original evidence. Provider-specific and collocated achievement row counts are zero in this district; no broader provider/admissions/geometry approval is inferred.

## Individual economic status and the enrollment gap

Use **Final Survey 3, February 2025** individual free-eligible D/F, reduced-eligible 3/E and CEP direct-eligible C/R counts divided by the same row's own enrolled denominator. Native PK–12 enrollment is broader than the tested achievement population. Required counts must be available and Provision 2 code 4 exactly zero. Neither the funding numerator/percentage nor the School Grades economic column enters income; no 1.6 multiplier is applied. CEP code N describes meal access without individually identified eligibility and stays outside the numerator. Primary Lunch Status element 146025 specifies that codes 6/9 convert to C/D before state reporting; the published final counts are retained as reported.

Direct identification and application-based eligibility differ; reporting coverage/undercount are unknown. Suppressed cells, missing records and numeric zero remain distinct. No October or prior-year income replaces a February record. Exact individual ratios remain separate from the source's adjusted funding measures.

CCD district enrollment is **130,054**, while the 203 operational school totals sum to **129,932**, a difference of **122**. Each school's original grade subtotals reconciles to its own CCD total. Native-only John Love Early Learning Center `16-0734` reports fall PK 122 and February 132 without an exact CCD directory/membership identity. Matching 122 does **not** prove the administrative cause, establish identity or authorize a repair. Retain these records as separate evidence.

## Original proficiency and count limitations

Use the original 2025 School Grades **English Language Arts Achievement** and **Mathematics Achievement** whole-percent components, Level 3 and above. These are proficiency components, not overall points, letter grades, learning gains or percent tested. No grade-rate averaging or count-ratio reconstruction is performed.

The same-year calculation guide retains FAST PM3 ELA grades 3–10; Math FAST PM3 grades 3–8 plus prescribed B.E.S.T./Access Algebra 1 and Geometry EOCs; eligible FAA Performance Task results, excluding Datafolio. Full-year enrollment, home-zoned attribution, students testing above enrolled grade and the two-US-school-year ELL rule remain native scope. Medical/extraordinary exemptions remain excluded. February enrolled income and full-year attributed outcomes match school ID and year, without claiming identical student membership.

The ten-eligible achievement component rule does **not** establish ten valid scored students per member. The 95% percent-tested measure and federal index adjustment use different denominators. School Grades publishes no verified valid-score counts here. Counts, scored floor, variance and sampling intervals remain uncertified/unavailable; no enrollment or participation substitutes are allowed. A later approved point-only model must keep all counts and sampling endpoints null modelwide. Combined is the equal mean of original paired Math and ELA rates, with its own model and studentization, not proficiency in both subjects.

## Rebuild and subsequent gates

```sh
.venv/bin/python scripts/audit_duval.py
.venv/bin/python scripts/audit_duval.py --extract --output data/build/duval-replay.json
.venv/bin/python -m unittest discover -s tests -p 'test_duval_audit.py' -v
```

Two actual original builds reproduce **2,450,652 bytes**, SHA-256 **`7af9098534c3b502f5acdedf52cd0b7dfd1c25c7ec183055018892418ff2e54b`**. All eleven focused source tests, offline replay and compilation pass. Eleven Florida/district-planning regression tests pass separately. The complete canonical database, all prior rows in nine tables, 249 served assets and preceding scientific files remain unchanged. Historical source/model approvals stay false.

The independent original-source review passes **84,785 strict raw/cohort/reference comparisons** and **100 corruption rejections**, with no findings. Complementary primary/method review passes 89 controls and 112 further corruption rejections, including deliberately repinned raw/schema attacks and fifteen independently reread primary PDF pages. Both reviews pass with **212 total additional corruption rejections** and no findings. Source gate verified **2026-10-13 17:18:53 America/Chicago**; separate numerical full/deleted verification is authorized next. Later compact artifacts must verify the complete linked source/code/test/policy/raw/schema/definition evidence on every replay, including cached paths, without duplicating these raw tables. Canonical/static repeatability, independent integration review, HTTP/browser checks and user-authorized master delivery remain separate required gates. The [fixed 66-district TODO](../TODO-breakout_districts.md) retains a blank finish date until verified master delivery.

## Independent numerical audit

The compact [duval-model-audit.json](../data/source/duval-model-audit.json), rebuilt by [audit_duval_models.py](../scripts/audit_duval_models.py), independently verifies three unweighted 2024–25 district models. Full raw records stay in the immutable source audit, stored once. Exact native/NCES identities, original table/worksheet/row/column/field pointers and original x/y remain linked. Every numerical replay, including cached expected validation, verifies complete current source/code/test/policy/raw/schema/definition evidence and typed runtime labels/MIN_SCHOOLS/SUBJECTS against immutable contracts; repinning public fingerprint variables does not bypass that validation.

| Diagnostic | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Usable schools | 146 | 146 | 146 |
| Intercept | 87.331036 | 83.441617 | 85.386327 |
| Disadvantage slope | -0.542791 | -0.612440 | -0.577615 |
| R² | 0.485470 | 0.604029 | 0.575685 |
| Maximum leverage | 0.047789 | 0.047789 | 0.047789 |
| Maximum Cook distance | 0.212625 | 0.117987 | 0.168446 |

All **438 explicit deleted-school fits** have rank-two designs and positive finite scales, with no hard holds. Full/deleted residual degrees of freedom are 144/143 in each model. Minimum deleted scales are about 11.5102 Math /10.2024 ELA /10.2009 Combined. Externally studentized residuals use other members' scale, without enrollment weighting or shrinkage.

Every model has the same 146 members and income vector, so OLS linearity makes Combined's coefficients equal the mean of subject coefficients. Combined still fits the original equally weighted paired subject rates independently and has its own scale, deletion fits and studentized values; subject t scores or scales cannot be averaged. All thirty charters remain included. Tiger Academy `16-1211` retains its original 190/190 individual eligibility, or 100%. Influential Seaside Community Charter `16-5401` and Seaside Charter K–8 `16-5631` remain; diagnostics never remove otherwise eligible schools or infer admissions, causal effectiveness or quality.

Observed-income predictions happen to lie in 0–100; the linear model is unbounded and never clamped. All 150 source profiles, four missing native outcomes, 61 directory exclusions, protected-grade records and the unjoined John Love/enrollment-difference evidence remain linked. Counts, scored floor, variances and intervals stay uncertified/unavailable throughout every model. Authored labels use School Grades and explicitly distinguish Datafolio from percent-tested participation; immutable original source strings remain unchanged.

Sixteen focused numerical tests, two actual byte-identical CLI builds, offline check and compilation pass. Both independent numerical reviews pass **254,529 original input/pointer/model comparisons**, all 438 NumPy deletion fits, three full 50-digit Decimal fits and eleven selected Decimal deletions. All **305 additional numerical/freshness/repinned corruption rejections** pass; maximum numerical difference is `5.46e-12`. Complete canonical bytes, all prior rows in nine tables and all 249 served assets remain unchanged.

```sh
.venv/bin/python scripts/audit_duval_models.py
.venv/bin/python scripts/audit_duval_models.py --check
.venv/bin/python -m unittest discover -s tests -p 'test_duval_models.py' -v
```

Status is `numerically_verified_pending_integration`, scope `numerical_audit_only`; both historical approvals remain false. Separately validated normalized/canonical/static scope, actual repeated imports preserving previous data, independent integration reviews and HTTP/browser/master gates remain required. Integration begins in isolation; the main database and main district exports are held until root authorizes imports after those isolated gates.

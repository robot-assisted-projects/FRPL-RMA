# Northside ISD district comparison

Exact2024–25 identity: NCES LEA `4833120`, CCD native `TX-015915`, TAPR district `015915`. Started **2026-10-14 03:14:21 America/Chicago**, within the original [66-district queue](../TODO-breakout_districts.md). Independent original-source review passed **2026-10-14 03:51:14**; separate numerical verification passed **04:18:51**. The separately validated107-profile point-rate comparison and both private/main import pairs pass independent review. Historical source/numerical approvals remain false; shared/browser/master delivery checks are recorded below.

## Original evidence and population

The [source audit](../data/source/northside-district-audit.json), rebuilt by [audit_northside.py](../scripts/audit_northside.py), retains fifteen original whole-source pins. Independent review reopens15316 district records /306683 typed cells; seven needed tables retain1543 records /59450 cells, with complete13546 omitted school-membership and227 LEA-membership inventories, original ordinals, authoritative identities, population fields and raw digests. Original headers, masks and primary definition evidence remain auditable.

The full131-school CCD directory contains128 operational and three inactive records. Native REF, STUD and enrolled-grade3–8 achievement tables each contain127 campuses. All131 directory charter fields are No;118 schools are Regular and13 Alternative. These observed types never select models or infer admissions/program roles. Exact complete CCD native school IDs crosswalk to already published full nine-digit TAPR campus IDs and six-digit district IDs. Preserve leading zeroes; never infer ownership from names, suffix padding or numeric conversion.

Complete native enrolled EE,PK,K,1–12 counts, reconciled to each campus’s own CPNTALLC enrollment, select107 source-certified lower profiles with positive grades3–8 and no positive9–12 grades. Native high16, mixed3 and primary1 configurations remain separate. CCD level, offered flags, reference grade labels, school type and charter status do not substitute for native enrolled grades. All offered/enrolled evidence is retained separately.

Three lower alternatives (`015915061`, `015915062`, `015915172`) have masked Math and ELA rates. They remain in the107 profiles, with104 usable prospective Math/ELA/paired Combined members, all Regular schools. Suppression is not zero and masked rates are never reconstructed from counts. HOMEBOUND (`015915133`, NCES `483312005564`) is operational in CCD but absent from all three native tables; native enrollment/income/outcomes remain missing. Its directory/offered/membership evidence stays separate, without name/suffix/backfill repair.

## Individual income and published achievement

Income is individual October25,2024 PEIMS economic status, own `CPNTECOC / CPNTALLC`: free/reduced meal eligibility or other public assistance, codes01/02/99, divided by same-year own all-enrolled EE–12 enrollment. ED +nonED and native tenth-percent display must reconcile. This broad state-specific proxy is distinct from uniform household-income FRPL and does not exactly describe tested pupils. CEP requires individual certification/local income surveys; universal meals do not classify every student. Provision2 can retain base-year eligibility for continuously enrolled students. Missing surveys can be00, with unknown undercount. The January16,2025 resubmission extension still requires enrolled/eligible status on October25,2024; it is not another-year backfill.

Outcomes are original All Students TAPR **enrolled-grades3–8 Math/ELA Including EOC, At Meets Grade Level or Above**, using published whole-percent R cells. The documented accountability subset requires the same district/campus at Fall snapshot and testing. Regular/accommodated and Spanish STAAR, Alternate2 and corresponding AlgebraI/EnglishI–II EOC remain in the native definition. Separate all-testers TPRS, participation and both-subject-passing measures are not substituted. Combined will use equally averaged eligible native Math/ELA rates with its own fit/scale, never grade averaging or count-derived rates.

Published rates differ from unverified count arithmetic at103 Math and103 ELA campuses. Raw #Tests/#Meets and their arithmetic remain audit evidence; neither certifies valid-score denominators or selects point-rate membership. Current2025 N/NAAR and M/medical status mapping remains unresolved under the existing source hold. No failed count-source investigation was repeated. Counts, the ten-valid-scored floor, sampling variances and intervals stay uncertified/unavailable. Native masks for denominators1–4 do not establish the project’s scored-count floor.

CCD district/operational-school and native-campus enrollment each total100208. Native PEIMS membership totals99729 and individual economic count49854.72 campus enrollment/membership differences, total479, remain unassigned; administrative equality or differences never supply tested denominators. High/mixed/primary, unmatched/inactive, program/provider/admission and geometry scope remain outside or unaudited.

## Independent source verification

Fourteen final targeted tests pass in8.480s; two actual final code/test/extract-bound original CLI builds are byte-identical, with offline replay and compilation passing. Independent original/derived verification passes327295 strict comparisons, all131 roster records,88 necessary corruption/current/semantic/type/public-repin rejection cases and13 controls. All fifteen missing-original cases, same-size drift and stale full-state caches fail closed. Published zeros/masks and R rates with unavailable counts remain source evidence without count certification.

A separate brief primary-definition review checks six whole primary files,18 exact PDF pages and3410 HTML lines/3428 comparisons, agreeing with individual October income/published-R scope and the unresolved count hold. Producer correction affected only an ignored preservation harness’s Lee metadata path; source code/tests/data were unchanged.

The entire main database and all nine earlier tables,277 served assets,372 scientific files and70 regions/87 guide definitions/provider bindings/geometry/planning are preserved. No source-review fit, import, served comparison, browser change or Git mutation occurred. Source-only approvals remain false. Subsequent numerical verification is recorded below; separate normalization, repeatability, browser and tested master/public delivery remain gated. Finish stays blank.

## Independent numerical verification

The separate [numerical audit](../data/source/northside-model-audit.json), rebuilt by [audit_northside_models.py](../scripts/audit_northside_models.py), verifies unweighted104-member Math/ELA/own paired Combined models and all312 explicit deleted-school fits. Full/deleted designs have rank two, positive scales and residual degrees of freedom102/101. The107 source profiles retain three alternatives with masked rates; neither suppression nor a raw count screen selects invented results.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 104 | 104 | 104 |
| Intercept | 68.130703 | 80.117550 | 74.124127 |
| Disadvantage slope | -0.463215 | -0.501261 | -0.482238 |
| Residual scale | 8.708070 | 6.143146 | 6.832160 |

HELOTES EL (NCES `483312003700`) has the highest Cook influence in all three models and remains included. Original income spread7.23684–94.38776% remains; natural predictions lie within0–100, while a synthetic control preserves unbounded values. Combined uses its own response, fit and scale; its t values differ from averaged subject t values. No influence exclusions, weighting, clipping or shrinkage is introduced. Source masks, HOMEBOUND’s missing native identity,72 unassigned enrollment/membership differences and count/status/floor/variance/interval/program/geometry holds remain.

Eighteen final tests pass in72.777s, with no production or test repairs. Two actual final code/test/artifact-bound numerical CLI outputs are identical; offline replay and compilation pass. Independent review verifies159003 original compact input/reference/full+all312 NumPy result/diagnostic comparisons (maximum difference1.82e−12), three full/twelve selected60-digit fits (maximum9.09e−13),208 necessary rejection cases and seven controls. Fresh original/current/runtime checks across six APIs and numeric/refit/public-expected-authority attacks fail closed. The accepted source327295/88 suites were reused rather than repeated.

Three reviewer fixtures were corrected transparently: a local decimal.py name shadowed the standard library before any calculation, old Cypress influence/gap IDs were replaced with original Northside IDs, and numerical holds correctly omit results rather than include an empty list. Only the affected hold tail was repeated after82 passing preceding guards; failed logs remain. A producer ignored proof-summary field inherited a Florida-only key; its diagnostic lookup was corrected without changing source/code/test/data.

Source/numerical six remain immutable with false approvals. The whole main database and all old nine-table rows,277 served assets and378 scientific files/70 regions/87 guide definitions remain unchanged at this gate. Next: separately validated normalized contract and final-trio-bound private import pair, then authorized main/shared/browser and tested master/public delivery. Finish remains blank.

## Normalized integration and delivery checks

The separately audited [normalized extract](../data/source/northside.json), [adapter](../scripts/prepare_northside.py) and [tests](../tests/test_northside.py) retain107 lower profiles,107 own October income observations,214 subject outcomes, three104-member models and312 results, with22 provenance sources. Three masked alternatives retain searchable full NCES identities, unavailable metrics and explicit subject/history gaps; Homebound133 remains outside with missing native data. Browser school IDs are full NCES IDs; original TAPR IDs remain bound in provenance. Helotes (`483312003700` / native `015915104`) remains influential in all three models. Unknown valid-score counts, N/M status mapping, scored floor, variances and intervals remain unavailable.

Sixteen final focused adapter tests pass in276.788s. The final code/test/extract trio was frozen before two actual identical normalized builds and two full-current-database-copy private imports. The first private import was independently checked before the repeat. Every import/build/validate/export entry freshly validates complete original and trusted numerical evidence, including standalone helpers and an empty namespace before SQL. A draft masked-history fixture was corrected to the established empty-subject/exclusion representation, and fresh numerical validation was strengthened before the final freeze; scientific payloads did not change.

Independent review verifies210754 strict original/normalized/all-nine-canonical/current/history fields, including73357 normalized fields and149 complete source/definition metadata field checks. All312 results match NumPy within1.42e−13.307 necessary rejection cases and five controls pass:27 semantic cases,26 nontrivial SQL fixtures across three entry points and202 uncached original/runtime/alias/expected/builder/standalone-empty/prewrite checks. Reviewer-only fixtures corrected a Texas native-ID assumption, a private-output path and absent Florida constants; failed logs and unaffected earlier cases are retained. No production or scientific repair resulted. Historical source/numerical six remain immutable and false; only the separately validated normalized grade-school contract grants readiness.

Two actual main imports pass independent review and repeat all nine target tables/four exports exactly. All prior nine-table rows including Lee,281 served assets,387 scientific files, frozen Northside/Lee artifacts and Katy numerical evidence remain preserved, after the explicitly audited Lee shared supersession. No influence exclusions, weights, clamping, shrinkage, grade averaging or income/count backfills are introduced. Admissions, programs, provider roles, locations and boundaries remain unaudited.

Two actual shared builds repeat exactly:39 ready states /72 comparisons /89 assessment definitions. All71 old regions,88 definitions, provider bindings and geometry remain unchanged. Planning changes only4833120 to existing_northside;100208 enrollment,128 operational and107/16 potential cohort counts remain discovery evidence. All97 targeted Python checks (14 source,18 numerical,16 adapter,49 shared) and20 JavaScript checks pass. Seventeen actual local browser assertions pass, including107 profiles/104 model members,75→107 pagination, first off-page Nichols search/keyboard, Helotes influence, masked history gaps, fixed models, NCES share/empty/invalid links, separate Texas definitions and390px rendered widths/clean console. Frontend files remain unchanged and no new screenshot inspection is claimed. Final independent shared/prose review and tested master/public delivery follow. The fixed66 tracker retains the actual start and blank finish until the tested master reference is verified.

Rebuild from already pinned local originals, preserving other comparisons:

```sh
.venv/bin/python scripts/prepare_northside.py
.venv/bin/python scripts/export_catalog.py
.venv/bin/python scripts/export_assessment_guide.py
.venv/bin/python scripts/plan_district_comparisons.py
```

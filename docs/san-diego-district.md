# San Diego Unified district comparison audit

Exact 2024–25 identity: NCES `0634320`, CCD `CA-3768338`, CDE CDS prefix `3768338`. Work started **2026-10-14 05:13:48 America/Chicago**, within the original [66-district queue](../TODO-breakout_districts.md). Original-source and numerical review pass; normalized/canonical release checks remain separate. Historical source/model approvals remain false.

## Original population and exclusions

The [source audit](../data/source/san-diego-district-audit.json) and [replay script](../scripts/audit_san_diego.py) retain all175 exact operational CCD schools, with175 native same-year FRPM matches and no roster charters. Authoritative configurations identify143 lower profiles,23 high schools and nine mixed schools. John Muir (`063432005487`) has a substantive CCD K–8/native K–12 conflict and remains outside the certified lower population. California P/KG lower-bound differences retain the original preschool notes rather than changing tested grades.

Of143 lower profiles,141 supply complete expected-grade Math/ELA observations. Porter (`063432011382`) and Nipaquay (`063432014617`) retain missing expected-grade components. Their native grade13 school totals remain separate evidence and never fill the gaps. Fletcher’s masked CCD membership remains missing; its own native FRPM denominator is verified and independently usable. An administrative Alternative School label is retained; names such as “Virtual” never establish provider or admissions attribution.

The native reporting prefix additionally contains41 charters outside exact CCD district membership and one unsupported N/A-grade Nonpublic, Nonsectarian Schools record. Reporting association does not prove roster ownership. Known CCD school membership94828 differs from LEA95175 by347; native K–12 roster enrollment94991 differs by184. The excluded nonpublic enrollment184 has the same number, but the cause of the difference remains unassigned.

## Income, proficiency, and valid scored counts

Income is each school’s own same-year CALPADS Census Day K–12 FRPM-eligible count divided by its own K–12 enrollment. Applications, alternate income forms, direct and categorical certification are included. Universal meals, the age5–17 measure and LCFF unduplicated pupils are separate concepts. Other-year income and CCD enrollment never replace the native denominator.

Regular Smarter Balanced B, All Students group1, supplies Math2 and ELA1. Complete expected grades3–8 use verified valid-performance-score counts as aggregation weights, following the separately approved California/Los Angeles contract. Overall Total equals all four performance levels and Total Students Tested with Scores; the top two levels and published two-decimal rates reconcile. Each expected grade requires at least11 valid scores. Enrollment and participation never substitute. Native grade13 totals and CAA remain separate; no suppressed or missing grade is reconstructed.

All141 eligible members have verified subject counts, with minimum aggregated subject N38. Numerical verification must separately check Jeffreys-smoothed variances and every member’s contribution through `I−H`. Combined uses equally averaged subject proficiency, its own fit/studentization and the conservative maximum positive covariance. The smaller subject count is display information, never a shared variance denominator. Any future eligible member missing a required count removes intervals for its whole model.

## Independent source verification

Fourteen final focused tests, two byte-identical original builds, offline replay and compilation pass. Independent review checks606677 original/derived fields,54 necessary rejection cases and12 controls. Nine whole original pins,3789 needed rows/169260 typed cells and complete18189 omitted-row inventories remain auditable. Primary definitions include eleven workbook worksheets (two FRPM, five layout, four CCD) and1184 research HTML lines. A cached CAPTCHA page supplies no income definition; the original FRPM workbook supplies the dated definition without another failed investigation.

The separate [numerical artifact](../data/source/san-diego-model-audit.json) passes independent review. No normalized contract, canonical import or public district comparison is approved at this milestone. High/mixed/program/provider/admissions/geometry scopes remain outside or unaudited.

## Independent numerical verification

Separate unweighted141-member Math, ELA and paired Combined models retain all423 explicit deleted-school fits, rank-two income designs and residual degrees of freedom139/138. Edison (`063432005449`) has the highest Cook influence in all three models and remains included. No diagnostic cuts, weights, clipping, shrinkage or source-gap repairs are introduced.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 141 | 141 | 141 |
| Intercept | 92.476089 | 94.326085 | 93.401087 |
| Disadvantage slope | -0.745417 | -0.675189 | -0.710303 |
| Residual scale | 10.06278 | 8.72076 | 8.74866 |

Eighteen final focused tests, two byte-identical actual final builds, offline replay and compilation pass. Independent review checks122630 original/input/model/result/interval fields, all423 NumPy deletions and every all-member conditional interval, plus12 selected60-digit cases (maximum discrepancy1.82e−12).155 necessary rejections/three controls pass. Review found two coherent in-memory provenance/comparator helper substitutions could evade the provisional validator. The narrow literal/live-helper repair rejects both direct and cached reproductions; only runtime metadata changed, with all inputs/results/intervals exact. The provisional proof and failed probes remain recorded.

Final independent numerical proof SHA-256 `5653556a781a43dbf239f013c4d068a467d75b2accdafe0bc1649f4d0febd27b`. Historical source/model six remain immutable and false; readiness requires a separately reviewed normalized contract and complete canonical/private/repeat/shared/browser/master gates. All original count, population, identity and attribution limitations remain.

A later formatting correction removed one redundant final newline from the numerical script. Its executable AST, runtime contract, tests and numerical artifact remain exact; two further actual rebuilds match. This changes only the physical code pin, before normalized final testing. Formatting receipt SHA-256 `15113270d112a1e42842b88b5638722316b8af4b0be3474845a101a23655fb4e`.

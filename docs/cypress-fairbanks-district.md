# Cypress-Fairbanks original-source and cohort audit

This historical source audit covers **2024–25**, exact NCES district **4816110**, CCD native district **TX-101907** and TAPR district **101907**. The [source artifact](../data/source/cypress-fairbanks-district-audit.json), rebuilt by [audit_cypress_fairbanks.py](../scripts/audit_cypress_fairbanks.py), retains original records and definitions. Its source/cohort gate passed **2026-10-13 19:49:30 America/Chicago**. Status remains `audit_pending`, scope `source_cohort_audit_only`; both source/modeling approvals remain false. It does not release district fits, canonical data or a browser comparison.

## Exact identities and population

The four original CCD files retain 94 operational school identities: 93 Open and one New. Three original TAPR files contain 92 native campuses. Authoritative district/campus codes join those 92 profiles; names never establish identity. Two operational alternative-campus identities have no native reference, enrollment or assessment record: East, native `101907006` /NCES `481611008601`, and West, native `101907014` /NCES `481611012265`. They remain separate missing-native-data records, without inferred income, grades or outcomes.

Complete native grade counts identify 78 prospective pure tested-grade campuses, thirteen high-school campuses and one primary-only campus. All 78 prospective grade-school campuses retain usable same-year individual income and published Math/ELA proficiency, yielding 78 prospective members for each subject and paired Combined. These are source counts, not model approval. Planning counts do not select the population. High/mixed/primary and unmatched records stay outside this prospective grade-school population; admissions and geometry remain unaudited.

## Individual income and enrollment

The predictor uses original same-year fall individually classified economically disadvantaged pupils divided by that campus's own enrollment. Native economically disadvantaged and non-disadvantaged counts reconcile to the enrollment denominator. CEP/universal meal service and direct-certification funding multipliers do not replace individual status; the retained Texas primary reporting definitions and income-form extension describe the applicable-year administrative measure.

CCD district enrollment, summed operational CCD membership and native enrollment each total **117,927** pupils. Individual economically disadvantaged counts sum to **69,352**. Native membership totals **117,658**, a difference of **269** pupils across 72 campuses. The audit retains both sets of original values and every campus discrepancy without assigning a cause or moving pupils. Enrollment/membership are not valid-score denominators.

## Achievement and unresolved score counts

Use the original direct whole-percent published **R** values for the retained campus Math/ELA grades 3–8 assessment totals, with the exact native TAPR assessment population and suppression definitions. Do not substitute count-ratio precision from the statewide extract or average grade percentages. Missing/suppressed values stay unavailable, never zero. The full original assessment rows and unused numeric fields remain auditable.

Original N/D cells and score-status definitions are retained as evidence, but the exact current N/M valid-score mapping and scored floor remain uncertified. The earlier [Texas hold](texas-data.md) applies; this audit adds no repeated failed count investigation. Counts, sampling variances and sampling intervals remain unavailable for the proposed district model. A later separately audited published-rate fit can use the original unsuppressed rates without manufacturing or screening by an unverified denominator. Provider roles and relative target ambition remain unverified.

## Verification and next steps

Seven complete original tables preserve **1,107 records and 42,828 typed cells**, with fifteen original file/primary-definition pins and the frozen statewide extract as a separate cross-check. Headers, labels, source row numbers, native strings, every identity and suppression token remain reproducible. Eleven source tests and twelve Texas/planning regressions pass, with two actual original-file builds producing byte-identical output and offline replay/compilation passing. Both independent source reviews pass. Every preceding row in all nine canonical tables, all 257 served files and all 324 preceding scientific files remain unchanged; Philadelphia's separately authorized delivery prose is recorded explicitly.

Next: independent full/deleted Math, ELA and paired Combined numerical verification; then a separately validated normalized contract, repeatable canonical imports, browser checks and tested master delivery. The [fixed 66-district TODO](../TODO-breakout_districts.md) records actual start **2026-10-13 19:23:44 America/Chicago** and retains a blank finish date. Statewide Texas remains separate. This historical artifact and its false approval flags remain immutable through later phases.

```sh
.venv/bin/python scripts/audit_cypress_fairbanks.py --extract
.venv/bin/python scripts/audit_cypress_fairbanks.py
.venv/bin/python -m unittest discover -s tests -p 'test_cypress_fairbanks_audit.py' -v
```

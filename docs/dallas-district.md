# Dallas ISD source and cohort audit

This **source/cohort audit only** covers Dallas ISD, Texas, **2024–25**, exact NCES LEA **`4816230`**, native CCD LEA **`TX-057905`** and TAPR district **`057905`**. [audit_dallas.py](../scripts/audit_dallas.py) reconstructs [dallas-district-audit.json](../data/source/dallas-district-audit.json) from original files. Status is `audit_pending`, scope `source_cohort_audit_only`, and both source/modeling approvals remain **false**. No numerical model, canonical import or browser comparison is created by this artifact.

## Original evidence and exact identities

The complete source retains **249 CCD directory records**: 239 Open, nine Inactive and one Closed. All 239 operational identities match the complete native TAPR campus roster; the ten nonoperational records have no native campus and remain explicit. Every native nine-digit `CAMPUS` matches exact `DISTRICT=057905` and CCD `ST_SCHID=TX-057905-057905sss`, with its twelve-digit NCES identity. Names, labels and prefixes alone never establish a join. All 249 CCD charter flags are No; school type does not screen eligibility.

| Retained original table | Records |
| --- | ---: |
| CCD school directory | 249 |
| CCD school total and grade membership | 1,921 |
| CCD LEA directory | 1 |
| CCD LEA total and grade membership | 16 |
| TAPR native reference | 239 |
| TAPR native enrollment, grades and economic status | 239 |
| TAPR native enrolled-grade performance | 239 |

These seven inventories preserve **2,904 original rows and 112,006 typed raw cells**, original headers and source-row references. Fifteen whole original files are pinned by URL, byte size and SHA-256, including CCD archives, TAPR CSVs/dictionary/masking HTML, income definitions, the dated income-form extension, glossary, accountability manual, performance-listing definitions and CCD state notes. Eighteen selected primary PDF pages and original HTML/dictionary/state-note evidence remain retained. Exact integer source-row references and counts reject booleans and floats.

## Enrolled grade populations and boundaries

Complete native `EE`, `PK`, `K` and grades 1–12 enrollment reconciles to `CPNTALLC`. Positive enrolled grades 3–8 with no positive grades 9–12 define the prospective grade-school cohort. This yields **189 grade-school, 37 high, seven mixed and six primary-only** configurations. The 195 native no-high-grade profiles include six primary-only schools, which have no applicable tested grade. These populations remain distinct from reference labels, offered grades, CCD level and reported assessment counts.

**Barbara M Manns Middle DAEP, `057905011`, and Young Women's STEAM, `057905352`, have native middle reference labels but enroll one and 29 ninth graders, respectively.** Their positive high-grade enrollment keeps them mixed and outside the pure grade-school cohort. School type, alternative status and future fit diagnostics never remove otherwise eligible members.

The only grade-school outcome exclusion is **`057905241`, ELEMENTARY' DISCIPLINARY ALTERNATIVE EDUCATION PRG**. Both original subject triplets are blank. Missingness remains unavailable; neither percentages nor counts are filled with zero. All 189 grade-school profiles have usable individual economic status; the published-rate availability is **188 Math / 188 ELA / 188 Combined**. Those counts meet the prospective 30-school screen, which does not approve a source or model. All 60 outside directory configurations (ten nonoperational and fifty operational non-grade-school records) remain auditable.

## Individual income, enrollment and membership

Income is **`100 × CPNTECOC / CPNTALLC`**, individual economic status on the **October 25, 2024** PEIMS enrollment snapshot, for the broader enrolled EE–12 population. Economic and non-economic counts reconcile to enrollment; the native one-decimal percentage is independently checked. All 239 native campuses have usable income. Grade-school income spans approximately **9.5595–100%**; an unsuppressed 100% or zero remains a valid recorded ratio.

The [TAPR glossary](https://tea.texas.gov/school-and-district-leaders/accountability/academic-accountability/performance-reporting/2024-25-comprehensive-tapr-glossary-0.pdf), [individual PEIMS reporting definition](https://www.texasstudentdatasystem.org/sites/texasstudentdatasystem.org/files/TEDS_Data_Submission_Requirements_Student_Identification_and_Demographics_Domain.pdf) and [2024–25 verification extension](https://tea.texas.gov/taa-letters/school-year-2024-2025-income-eligibility-verification-forms-extension) define codes 01/02/99, including meal eligibility or other public assistance. CEP requires individual direct certification and annual local surveys; universal meals alone do not classify every child. Provision 2 can retain base-year eligibility for continuously enrolled pupils. Missing surveys can produce code00 and an unknown undercount. The January 16, 2025 resubmission extension still requires enrollment and eligibility on October 25, 2024. These limits stay explicit; another year's ratio is never backfilled. This is a state-specific economic proxy, not household income or a uniform nationwide FRPL measure.

Original CCD LEA membership, operational-school totals and native enrolled totals all equal **139,802**. Individual economic counts sum to **124,800**. Separate native TAPR membership totals **139,776**, a 26-pupil difference at sixteen campuses. The glossary distinguishes enrollment from membership, including an under-two-hour service distinction; these records do not prove the cause of each difference. Neither enrollment nor membership supplies a valid-score denominator or a proficiency weight.

## Published proficiency and the unresolved count scope

Use exact native **All Students enrolled grades 3–8 Math/Reading Including EOC, At Meets Grade Level or Above**, specifically original whole-percent **`R`** cells. Native scope includes STAAR with/without accommodations, Spanish STAAR, Alternate 2 and the documented EOC inclusion. It uses the TAPR accountability subset, requiring the same campus/district on the fall snapshot and testing date. Separate TPRS all-testers, participation and both-subject passing measures never substitute.

Empty, bullet/asterisk and native `-1/-2/-3` values remain unavailable. Preserve numeric zero; do not reconstruct masked percentages from visible counts. Published subject rates are whole percentages. Combined would be the equally weighted mean of eligible original Math and ELA rates, with its own separate model; it is not the percentage passing both. No grade-rate averaging or enrollment weighting is performed.

Native `#Tests` and `#Meets-or-above` are retained as **unverified raw evidence**. Where available, their ratio reconciles to the source's whole-percent display, but does not certify valid-score scope or the ten-valid-scored minimum. In the prospective grade-school cohort, original published values differ from unverified count arithmetic at **186 Math and 184 ELA** campuses. The district audit preserves the original whole-percent values; statewide arithmetic precision and fits are not reused. Its separately pinned statewide extract is a historical cross-check only.

The existing Texas hold still requires exact current-year mapping of `N/NAAR` and `M/medical exemption` performance statuses to these specific TAPR count fields. This audit does not repeat that failed investigation or treat the count labels as certification. All verified counts, sampling variances and intervals remain null/unavailable; the scored floor remains uncertified. A later explicitly approved point-only model must omit intervals modelwide. High/mixed assessment populations, admissions, provider roles and geometry remain unaudited.

## Rebuild and release gates

Ordinary replay is offline and opens only committed evidence:

```sh
.venv/bin/python scripts/audit_dallas.py
.venv/bin/python -m unittest discover -s tests -p 'test_dallas_audit.py' -v
```

Explicit original reconstruction verifies every whole-file pin and reopens the original archives, CSVs, PDFs, HTML and state notes. `--output PATH` permits independent replay artifacts:

```sh
.venv/bin/python scripts/audit_dallas.py --extract --output data/build/dallas-replay.json
```

Two actual original-source builds reproduce **4,856,854 bytes**, SHA-256 **`f2a0fd319e2a5a77a1454117cbd359f399962234115d9bf611bca68fa49a6b6c`**, including both repeats after the strict planning-reference repair. All **19 focused tests**, offline replay and compilation pass. Independent original reconstruction verifies 133,744 strict comparisons, all source pins and native eligibility, with 56 additional corruption rejections and fifteen valid edge controls. Complementary review passes nineteen primary-definition controls and 38 corruption cases, including deliberately repinned raw/source/policy attacks and the repaired planning-reference types. Both independent source reviews pass with **94 additional corruption rejections** total and no remaining findings.

Numerical full/deleted fits, a separately validated normalized contract, canonical/static preservation and repeatability, HTTP/browser review and tested master delivery remain required. This source-only milestone stays on `expansion/all-states`; its row remains unfinished in the fixed [66-district TODO](../TODO-breakout_districts.md).

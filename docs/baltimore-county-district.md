# Baltimore County district comparison

Exact 2024–25 identity: NCES LEA `2400120`, CCD native `MD-03`, MSDE division `03`. Started **2026-10-13 23:35:01 America/Chicago**. This district belongs to the original [66-district queue](../TODO-breakout_districts.md). Source review passed **2026-10-14 00:19:55**; separate numerical verification passed **2026-10-14 01:02:20**. Repeated actual canonical imports, shared review and local browser checks pass; HTTP/Git binding and tested master delivery pass; public readback passed **2026-10-14 02:26:17**. Historical approvals remain false. Readiness belongs only to the separately validated normalized scope below; historical audits do not approve a release.

## Original sources and eligible population

The [source audit](../data/source/baltimore-county-district-audit.json), rebuilt by [audit_baltimore_county.py](../scripts/audit_baltimore_county.py), pins eleven original CCD/MSDE files and primary definitions. Eight retained tables contain 4,536 needed records /75,620 typed cells, preserving complete fields, headers, masks and original source rows. Exact omitted-row inventories and digests retain provenance for 18,686 unused school-membership demographic rows,227 LEA-membership rows and468 other-group LEA MCAP rows. Selection does not use performance or model diagnostics.

All178 original native directory NCES cells match operational CCD records. The complete180-row CCD directory includes two closed, native-unjoined records (`MD-03-030058`, `MD-03-031451`), which remain outside. Identity uses authoritative full NCES cells and independently checked native codes; names and suffixes do not repair joins.

Separate original offered/enrolled grades, native E/M/EM span and positive grades3–8 enrollment select **137 lower-grade profiles**, all with usable own same-year Early Attendance economic ratios. Watershed Public Charter (`03-0219`, NCES `240012001753`, CCD `MD-03-030219`) remains in the178-school evidence roster but is outside this cohort because its original offered flags are Adjusted. Meadowood and Crossroads alternative schools remain source-eligible; their masked Math results leave them ELA-only. No program or admissions classification is inferred.

## Income and achievement definitions

Income is each school's original individual **Early Attendance economically disadvantaged count / own total student count**, using the native All band where multiple bands exist. The precise ratio reconciles the native one-decimal display. Its collection as-of date and identification coverage are unspecified. This status is broader than household-income FRPL and distinct from universal meals, tested-student poverty and CCD direct certification. September or CCD membership never replaces its denominator; missing cells are not zero and other years are not backfilled.

Use original regular MCAP **School_Level, Year2025, All Students, All Grades** published Math/ELA proficiency under Levels3–4 standards introduced in2021–22. DLM remains separate. Accelerated Algebra1, Geometry and Algebra2 and the March2025 grade6–7 course-substitution waiver (2024–25 through2027–28) remain explicit population limits. Published All Grades percentages are not replaced by averaged grades, component sums or reconstructed count ratios.

Eleven original `<= 5.0` Math masks remain unavailable. Prospective populations are **126 Math /137 ELA /126 paired Combined**. Combined is the equal mean of paired original rates and needs its own126-school fit, residual scale and deletions; full subject coefficients and t scores cannot be averaged across unequal populations. No models are approved by this source audit.

CCD/September LEA and operational CCD school totals are110,024. Known native September school totals110,015 leave9 unassigned; Early Attendance district110,382 versus known school denominators110,357 leaves25 unassigned. Eight school denominators are missing/suppressed outside the eligible cohort. Aggregate differences never allocate missing values or establish an administrative cause.

Administrative tested counts remain raw evidence. Unique valid-score denominators, the ten-valid-scored floor, sampling variances and intervals remain uncertified/unavailable. Source success does not approve high/mixed populations, provider roles, geometry or causal interpretations.

## Source verification and next gate

Fourteen focused tests, two identical actual original-source CLI builds, offline replay, compilation and independent review pass. The reviewer reopens all eleven original files and verifies **165,999** strict original/derived comparisons,113 meaningful corruption rejections and17 positive/boundary controls. Whole canonical bytes, every previous row in nine tables,265 served assets and348 scientific files remain unchanged at this gate. Root's later Memphis integration is separately authorized.

Review corrected a charter-eligibility sentence in the ignored producer proof; its original bytes are archived and the correction is independently bound. The source artifact, code, tests and cohort were correct and remain unchanged. Immutable source policy, complete raw/schema/definition/identity fingerprints, original metadata digests and current runtime/cached evidence guards prevent self-repinned input drift.

```sh
.venv/bin/python scripts/audit_baltimore_county.py --extract
.venv/bin/python scripts/audit_baltimore_county.py
.venv/bin/python -m unittest discover -s tests -p 'test_baltimore_county_audit.py' -v
```

At this source gate, separate126/137/126 models and all389 explicit deletion fits were next. The completed numerical phase follows below. Historical status remains `audit_pending`, scope `source_cohort_audit_only`, both approvals false. Normalized/import, browser and tested master delivery require their separate gates; finish remains blank.

## Independently verified numerical models

The separate [numerical audit](../data/source/baltimore-county-model-audit.json), rebuilt by [audit_baltimore_county_models.py](../scripts/audit_baltimore_county_models.py), preserves independent unweighted126 Math,137 ELA and126 paired Combined-school fits. All389 explicit deletion fits have rank two and positive finite residual scales. Combined uses its own paired outcomes, coefficients, scale and deleted fits.

| Fit | Math | ELA | Combined |
| --- | ---: | ---: | ---: |
| Schools | 126 | 137 | 126 |
| Intercept | 76.960107 | 96.216426 | 86.065183 |
| Disadvantage slope | -0.797629 | -0.878245 | -0.821878 |

Nineteen distinct targeted tests pass, with two final actual byte-identical CLI builds, offline replay and compilation. Independent review verifies64,709 original/pointer/numerical comparisons, all389 NumPy deletions and three full/fifteen deleted60-digit fits (maximum difference1.82e−12),85 meaningful corruption rejections and six controls. A valid synthetic percentage population retains an unclipped−4.08 prediction. No influence-based exclusions, weights or shrinkage are introduced.

Review found a cached-reference path could self-authorize an altered prediction. The final validator rebuilds its expected result from verified original inputs on every call; supplied expectations and mutable public caches cannot authorize drift. The exact former forgery and caller/builder alias controls now pass independent rejection checks. The nineteen-test evidence records earlier mathematical checks and the final repaired-guard checks separately. Source inputs and all389 scientific fits are unchanged.

The source trio remains frozen; historical source/numerical approvals remain false. Counts, scored floor, variances and intervals remain unavailable, eleven original Math masks persist, Watershed charter remains outside the cohort and Meadowood/Crossroads remain ELA-only. Current canonical and served assets are preserved except root's separately authorized Memphis delivery. Numerical gate recorded **2026-10-14 01:02:20 America/Chicago**. At this numerical gate, isolated normalized/private imports and independent review were next. Their completed phases are recorded below; tested master/public delivery follows separately.

## Canonical and browser integration

The separately validated [normalized release](../data/source/baltimore-county.json), rebuilt by [prepare_baltimore_county.py](../scripts/prepare_baltimore_county.py), supplies exact `md-baltimore-county-2025` /region `baltimore-county` readiness. All six historical source/numerical files remain immutable with false approvals. Current literal/runtime/raw/schema/definition/identity and all nine ownership contracts are validated before writes. Legal native school identity overlap with other Maryland datasets remains separate.

All137 source profiles retain their authoritative NCES/native crosswalks, individual own Early Attendance ratios,274 native subject observations,18 provenance records and separate126 Math /137 ELA /126 Combined models with389 results. Eleven Math masks remain ELA-only, including Meadowood and Crossroads alternatives. Watershed charter stays outside due adjusted offered flags. Hereford Middle has the highest Math Cook influence; Prettyboy Elementary has the highest ELA/Combined influence. Both remain eligible. Counts, scored floor, variances and all interval endpoints remain unavailable; programs, admissions/provider roles and geometry remain unaudited.

The discovery screen's139 potential lower schools remains unchanged. Home Assignments-Elementary (`03-0057`, `240012000925`) and White Oak School (`03-0923`, `240012001435`) have masked original September grades3–8 counts, which do not certify positive native tested-grade membership. Their CCD counts and original native evidence remain auditable; suppression means neither zero nor a verified positive value. The source-certified137-school population does not backfill those native counts from CCD.

Fourteen distinct adapter checks pass. Four adapted fixtures were corrected: use the influential negative residual’s absolute magnitude; create a legal foreign-owner result without a duplicate key; target a scored school when altering Math; and check equivalent readable count-limit wording. Ten unchanged earlier passing checks and all four affected reruns are retained transparently; production behavior and normalized bytes did not change. Two final actual normalized CLI builds and a supplemental private import pair bind the final code/test/normalized trio, with independent first checkpoint before repeat. Both the original pair and supplemental final pair remain recorded.

Independent review verifies198,653 original/canonical/current/history comparisons,47,124 normalized original fields and269 meaningful rejections with five controls, covering all nine ownership tables and uncached current-source/policy evidence before mutation. Two separately authorized actual main CLI imports repeat all target rows and four export bytes, preserving every earlier nine-table row and269 preceding served assets. Three data exports match the final private bytes; only the catalog’s two destination URLs change for production, then all four repeat exactly. All nine scientific files remain frozen.

Two actual catalog/guide/planning rebuilds repeat exactly, adding only Baltimore County and preserving68 earlier regions,85 definitions/provider bindings and all geometry. Catalog39 states /69 regions; guide86 definitions, eleven state holds unchanged. Only planning row2400120 changes scope; counts/source pins/identities remain. All96 distinct targeted Python tests (14 source,19 numerical,14 adapter and49 shared),20 JavaScript tests, syntax and diff checks pass. Shared gate recorded **2026-10-14 01:57:20 America/Chicago**. Independent shared semantics/documentation review passes without findings. Local browser verification passed **2026-10-14 02:05:33 America/Chicago** with17 assertions: first off-page search/keyboard, pagination, all eleven masked-Math/Combined profiles retaining ELA, alternatives, excluded uncertified membership/adjusted-charter scope, retained influence/history, native-ID shared links, empty/invalid selections, interval labels, guide links and390px rendered dimensions. No warning/error console logs. Screenshot capture was inconsistent with live geometry, so mobile checks use actual358px heading/control widths,390px scroll width and unchanged previously verified frontend assets. At that local gate, exact HTTP/Git bindings and master/public delivery followed separately, and finish stayed blank until remote verification. Completed delivery is recorded below.

## Tested master delivery

Tested commit `7e7e84014cbdd61e26bf734b753f482ddf062f7d` is verified on master and expansion/all-states **2026-10-14 02:19:44 America/Chicago**, using fine-fiddle. All96 targeted Python/20 JavaScript checks,17 local and three additional independent browser checks, nine exact HTTP/Git asset bindings and all23 changed release-file Git bindings pass. The independent fresh390px check confirms viewport/body/scroll390 and heading/search358, with no overflow. The pinned original Maryland definition identifies the measure as direct certification, with its own native Early Attendance denominator. Nine of the original66 districts are finished,57 remaining. Eleven Math masks, source-membership limits and unavailable counts/floor/intervals remain. A push does not confirm deployment; Pages/public verification follows separately.

Pages run [38527592572](https://github.com/robot-assisted-projects/FRPL-RMA/actions/runs/38527592572) completed successfully for tested commit `7e7e84014cbdd61e26bf734b753f482ddf062f7d`; a duplicate run was superseded and cancelled. Public readback passed **2026-10-14 02:26:17 America/Chicago** with12 browser assertions and nine independent HTTP/Git byte matches. Public proof SHA `dd35281eb75af45d0f17bb358e1992a4d43cb7a62dc4e0607fde218201e462ef`. The deployed137 profiles,126/137/126 models, eleven Math masks and unavailable counts/floor/intervals agree with the reviewed release.

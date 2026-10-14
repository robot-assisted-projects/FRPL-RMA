"""Replay Cypress-Fairbanks ISD's native published-rate fits without importing or publishing."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

import audit_cypress_fairbanks as roster_audit
from prepare_data import fit_model

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/cypress-fairbanks-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = '35f22cc72da43df22624a0ca1b98c3f0b78385eaaaedde3aa6f1aa93494fdb9a'
ROSTER_BYTES = 2109518
SOURCE_CODE = ROOT / 'scripts/audit_cypress_fairbanks.py'
SOURCE_CODE_SHA = 'f590527fb75201336c00cda5a19377be7a9b2946fc9456f384e12b98432563f7'
SOURCE_TESTS = ROOT / 'tests/test_cypress_fairbanks_audit.py'
SOURCE_TESTS_SHA = 'd9f06a36bc72cc1edc8fb975f474371ad968147728a7f31b14916af4d1505026'
MIN_SCHOOLS = 30
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
SUBJECTS = ['math', 'reading', 'combined']
ASSESSMENT = 'STAAR enrolled grades 3–8 Including EOC · TAPR published Meets or Above percentages'
STANDARD = '2024–25 Texas All Students accountability subset; STAAR with/without accommodations, Spanish STAAR, Alternate 2 and applicable Algebra I/English I–II EOC; separate Cypress-Fairbanks no-high-grade population'
SOURCE_POLICY_SHA = '76a4e6d67788097d1159c372f03c751fabbddde32a6d42c1ec14696134e0dcf2'
SOURCE_RAW_SHA = 'a78218830702a4fabeebe6b5655e4d65124bebdd32131b88ec591ec039f86681'
SOURCE_SCHEMA_SHA = 'afaa08ab40ef16e96e0a90e910e8f5df9048581868dc47cea6f1487a262212d6'
SOURCE_DEFINITION_SHA = '41c83100bb0930615830e19b012bf223610e82375602b586dd1d485980605fdc'
SOURCE_IDENTITY_SHA = '900bd6b82a458e1de2d4a3c58933adde692dcff3875f120b015344b854dc924b'
SOURCE_RUNTIME_SHA = 'b619643dc029b91818eba99279e254a2c8e01ea73ef32dcd2c6fcdb1017364d6'
SOURCE_SECONDARY_SHA = 'bb8a0882cc64fd569168bed05853cd9070d4ec4e0940fa27a2c6a029e1d78aac'
POLICY = {
    'identity': roster_audit.POLICY['identity'],
    'population': roster_audit.POLICY['population'],
    'income': roster_audit.POLICY['income'],
    'income_limits': roster_audit.POLICY['income_limits'],
    'assessment': roster_audit.POLICY['assessment'],
    'eligibility': 'Reconstruct exact operational same-year CCD attachments, complete native enrolled EE/PK/K/1–12 counts with positive grades 3–8 and zero grades 9–12, reconciled individual economic status and each original unmasked whole-percent R cell. Preserve all 78 grade-school profiles and their 78 original unmasked Math/ELA/paired Combined members. Exact operational alternative campuses 101907006 and 101907014 remain unmatched to all native originals and are retained outside these fits, without name or zero substitution. Reported tests/numerators, charter/type/reference labels and diagnostics never select membership.',
    'outcome': 'Only original published whole-percent CDA38AM0E225R / CDA38AR0E225R. Do not reconstruct masks, substitute count-ratio precision, reuse statewide or another district’s fits, or average grade percentages.',
    'combined': roster_audit.POLICY['combined'],
    'counts': roster_audit.POLICY['counts'],
    'models': 'Separate unweighted 2024–25 Cypress-Fairbanks grade-school Math, ELA and Combined district OLS. Combined independently fits its paired original-rate means with its own residual scale, deletions and external studentization. Equal cohorts can yield coefficient averages, never averaged studentized scores. No enrollment weights, clamping, fit-driven exclusions or national pooling.',
    'minimum_usable_subject_schools': MIN_SCHOOLS,
    'studentization': 'Externally studentized residuals use every explicit deleted-school fit and N−3 residual degrees of freedom, with independent centered full fits and held-out leverage. Cook distance and line sensitivity are descriptive, never exclusions.',
    'intervals': 'Every valid-score count, sampling variance and interval endpoint is null modelwide; the ten-valid-scored floor is uncertified. An internal zero variance vector is solely a computational sentinel, never an uncertainty estimate.',
    'compact_provenance': 'The complete committed immutable source retains all 1,107 original records / 42,828 typed cells and is the authoritative raw-record store. Exact whole-blob, source-code/tests/policy, raw-input/schema/definition fingerprints are required on every replay. Compact model inputs retain exact x/y/identities and original table row/field references; no loss of raw auditability is authorized.',
    'release': 'Numerical audit only, pending independent review and separate canonical/browser integration. All historical and numerical source/modeling approvals remain false; no high/mixed/primary/nonoperational population or count hold is released.'
}


NUMERIC_POLICY_SHA = '7eddf7fba55ab8030ae89afdc375ef80401e763904c13e2f499cefb59d868763'
RUNTIME_CONTRACT_SHA = '0cfd9b54bd4ca5e59690bc802fa750ddb49899a438bd0019afedfe6e0218b9a6'


def runtime_contract():
    return dict(minimum=MIN_SCHOOLS, subjects=SUBJECTS, assessment=ASSESSMENT, standard=STANDARD,
        absolute_tolerance=ABS_TOLERANCE, relative_tolerance=REL_TOLERANCE, verify_tolerance=VERIFY_TOLERANCE,
        source=dict(path=str(ROSTER.relative_to(ROOT)), sha256=ROSTER_SHA, bytes=ROSTER_BYTES,
            code_path=str(SOURCE_CODE.relative_to(ROOT)), code_sha256=SOURCE_CODE_SHA,
            tests_path=str(SOURCE_TESTS.relative_to(ROOT)), tests_sha256=SOURCE_TESTS_SHA,
            policy_sha256=SOURCE_POLICY_SHA, raw_sha256=SOURCE_RAW_SHA, schema_sha256=SOURCE_SCHEMA_SHA,
            definition_sha256=SOURCE_DEFINITION_SHA, identity_sha256=SOURCE_IDENTITY_SHA,
            runtime_sha256=SOURCE_RUNTIME_SHA, secondary_sha256=SOURCE_SECONDARY_SHA))


def require_runtime_contract():
    # Literal baselines prevent changed live semantics from authorizing themselves
    # by coherently repinning public policy/runtime/source fingerprint variables.
    original_policy = '7eddf7fba55ab8030ae89afdc375ef80401e763904c13e2f499cefb59d868763'
    original_runtime = '0cfd9b54bd4ca5e59690bc802fa750ddb49899a438bd0019afedfe6e0218b9a6'
    if (NUMERIC_POLICY_SHA != original_policy or RUNTIME_CONTRACT_SHA != original_runtime
        or roster_audit.fingerprint(POLICY) != original_policy
        or roster_audit.fingerprint(runtime_contract()) != original_runtime):
        raise ValueError('Frozen current Cypress-Fairbanks numerical policy/types/subject/minimum/source contract changed')
    roster_audit.require_runtime_contract()


def load_roster(path=ROSTER):
    require_runtime_contract()
    source_pins = [(roster_audit.RAW_INPUT_SHA, SOURCE_RAW_SHA),
        (roster_audit.ORIGINAL_SCHEMA_SHA, SOURCE_SCHEMA_SHA), (roster_audit.DEFINITION_INPUT_SHA, SOURCE_DEFINITION_SHA),
        (roster_audit.ORIGINAL_IDENTITY_SHA, SOURCE_IDENTITY_SHA), (roster_audit.RUNTIME_CONTRACT_SHA, SOURCE_RUNTIME_SHA),
        (roster_audit.STATE_EXTRACT_SHA, SOURCE_SECONDARY_SHA)]
    if any(actual != expected for actual, expected in source_pins):
        raise ValueError('Frozen Cypress-Fairbanks source raw/schema/definition/identity/runtime/secondary pins changed')
    if hashlib.sha256(SOURCE_CODE.read_bytes()).hexdigest() != SOURCE_CODE_SHA:
        raise ValueError('Frozen Cypress-Fairbanks ISD source code/policy changed; fresh numerical audit required')
    if hashlib.sha256(SOURCE_TESTS.read_bytes()).hexdigest() != SOURCE_TESTS_SHA:
        raise ValueError('Frozen Cypress-Fairbanks ISD source tests changed; fresh numerical audit required')
    if roster_audit.fingerprint(roster_audit.POLICY) != SOURCE_POLICY_SHA:
        raise ValueError('Frozen Cypress-Fairbanks ISD source policy changed; fresh numerical audit required')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != ROSTER_SHA or len(data) != ROSTER_BYTES:
        raise ValueError('Frozen complete Cypress-Fairbanks ISD source artifact changed; fresh numerical audit required')
    document = json.loads(data)
    roster_audit.validate(document)
    return document


def require_frozen_roster(roster):
    if roster_audit.fingerprint(roster) != roster_audit.fingerprint(load_roster()):
        raise ValueError('In-memory Cypress-Fairbanks ISD source evidence differs from the complete frozen artifact')


def frozen_population(roster):
    links = roster['roster_links']
    return dict(complete_directory_school_ids=sorted(r['school_id'] for r in links),
        operational_school_ids=sorted(r['school_id'] for r in links if r['ccd_flags']['operational']),
        grade_school_configuration_ids=sorted(roster['cohorts']['prospective_grade_school']['nces_school_ids']),
        grade_school_native_ids=sorted(roster['cohorts']['prospective_grade_school']['native_school_ids']),
        eligible_school_ids_by_subject={s:sorted(roster['cohorts']['prospective_grade_school']['subjects'][s]['prospective_nces_school_ids']) for s in SUBJECTS},
        high_school_configuration_ids=sorted(roster['cohorts']['high_only']['nces_school_ids']),
        mixed_configuration_ids=sorted(roster['cohorts']['mixed_grade']['nces_school_ids']),
        primary_configuration_ids=sorted(roster['cohorts']['primary_only']['nces_school_ids']),
        nonoperational_school_ids=sorted(r['school_id'] for r in links if not r['ccd_flags']['operational']),
        complete_native_school_ids=sorted(roster_audit.native_identity(e['raw']) for e in roster['raw_inputs']['ref']['records']),
        operational_without_native_school_ids=sorted(roster['coverage']['ccd_absent_from_native']))


def source_references(roster, link, by_table):
    """Original records stay in the hash-bound source artifact, never duplicated here."""
    native = link['native_school_id']
    return dict(roster_link_index=next(i for i,r in enumerate(roster['roster_links']) if r['school_id']==link['school_id']),
        directory_source_row=link['ccd_source_row'],
        native_source_rows={k:by_table[k][native]['source_row'] for k in ['ref','stud','assessment']},
        income_fields=['CPNTALLC','CPNTECOC','CPNTNEDC','CPNTECOP'],
        enrolled_grade_fields=list(roster_audit.GRADES),
        subject_fields={s:list(roster_audit.FIELDS[s]) for s in ['math','reading']},
        outcome_fields={s:roster_audit.FIELDS[s][2] for s in ['math','reading']})


def selected_inputs(roster, subject):
    """Reconstruct native source membership; no source-usable/count or diagnostic filter."""
    if subject not in SUBJECTS:
        raise ValueError('Only the three separately audited grade-school subjects are supported')
    require_frozen_roster(roster)
    raw = roster['raw_inputs']
    directory = {roster_audit.ccd_identity(e['raw'])[0]:e for e in raw['directory']['records']}
    by_table = {table:{roster_audit.native_identity(e['raw']):e for e in raw[table]['records']} for table in ['ref','stud','assessment']}
    inputs, exclusions, configurations = [], [], []
    required = ['math','reading'] if subject=='combined' else [subject]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key,native = link['school_id'],link['native_school_id']
        profile = directory[key]['raw']
        if native not in by_table['stud']:
            continue
        student = by_table['stud'][native]['raw']
        values = {field:roster_audit.count(student[field]) for field in roster_audit.GRADES}
        total = roster_audit.count(student['CPNTALLC'])
        complete = total is not None and all(v is not None for v in values.values())
        if complete and sum(values.values())!=total:
            raise ValueError('Original enrolled grade vector fails native enrollment reconciliation')
        applicable = (profile['UPDATED_STATUS'] in roster_audit.OPERATIONAL and complete and total>0
                      and sum(values['CPNTG%02dC'%g] for g in range(9,13))==0
                      and sum(values['CPNTG%02dC'%g] for g in range(3,9))>0)
        if not applicable:
            continue
        configurations.append(key)
        low,other = [roster_audit.count(student[f]) for f in ['CPNTECOC','CPNTNEDC']]
        display = roster_audit.number(student['CPNTECOP'])
        income_usable = None not in (low,other,display) and low+other==total and abs(100*low/total-display)<=.050001
        assessment = by_table['assessment'][native]['raw']
        rates = {s:roster_audit.number(assessment[roster_audit.FIELDS[s][2]]) for s in ['math','reading']}
        if any(v is not None and (not 0<=v<=100 or v!=int(v)) for v in rates.values()):
            raise ValueError('Original outcome must be an unmasked whole published percentage')
        reasons = [] if income_usable else ['Native same-year individual income missing, masked or unreconciled']
        reasons += [s+': original published whole-percent rate missing or masked' for s in required if rates[s] is None]
        reference = source_references(roster,link,by_table)
        if reasons:
            exclusions.append(dict(school_id=key,native_school_id=native,name=link['name'],
                reason='; '.join(reasons),raw_published_rates={s:assessment[roster_audit.FIELDS[s][2]] for s in ['math','reading']},source_refs=reference))
            continue
        outcome = (rates['math']+rates['reading'])/2 if subject=='combined' else rates[subject]
        income = 100*low/total
        if income!=link['income']['percentage'] or outcome!=link['subjects'][subject]['proficiency']:
            raise ValueError('Independent native income/display inputs differ from frozen source evidence')
        inputs.append(dict(school_id=key,native_school_id=native,ncessch=key,name=link['name'],level='ES',
            charter=profile['CHARTER_TEXT'],ccd_school_type=profile['SCH_TYPE_TEXT'],
            income_pct=income,income_year=2025,academic_year='2024-2025',
            income_enrollment=total,individual_economic_count=low,
            outcome_pct=outcome,outcome_by_subject=rates,
            raw_published_rates={s:assessment[roster_audit.FIELDS[s][2]] for s in ['math','reading']},
            valid_scores_by_subject={'math':None,'reading':None},display_valid_scores=None,sampling_variance=None,
            ten_valid_scored_floor_certified=False,source_refs=reference))
    expected = sorted(roster['cohorts']['prospective_grade_school']['subjects'][subject]['prospective_nces_school_ids'])
    if configurations!=sorted(roster['cohorts']['prospective_grade_school']['nces_school_ids']) or [r['school_id'] for r in inputs]!=expected:
        raise ValueError('Complete independent subject/configuration membership differs from frozen source')
    coverage = dict(grade_school_configuration_profiles=len(configurations),usable_schools=len(inputs),
        excluded_configuration_profiles=len(exclusions),excluded_configuration_records=exclusions,
        exclusions=dict(sorted(Counter(r['reason'] for r in exclusions).items())),
        charter=dict(sorted(Counter(r['charter'] for r in inputs).items())),
        school_types=dict(sorted(Counter(r['ccd_school_type'] for r in inputs).items())),
        eligible_members_with_verified_denominators=0,ten_valid_scored_floor_certified=False,
        model_sampling_intervals_available=False,source_evidence_path='data/source/cypress-fairbanks-district-audit.json',
        source_evidence_sha256=ROSTER_SHA)
    return inputs,coverage


def verify_independently(x, y, model, results):
    """Centered full OLS, independent leverage and explicit held-out refits; no intervals."""
    require_runtime_contract()
    n = len(x)
    if (n < MIN_SCHOOLS or x.shape != y.shape or x.ndim != 1
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError('Independent verification requires finite complete percentage vectors')
    def finite_number(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

    if (type(model.get('n')) is not int or model['n'] != n or len(results) != n
            or any(not finite_number(model.get(k)) for k in ['intercept', 'slope', 'r2'])
            or any(not finite_number(r.get(k)) for r in results
                   for k in ['actual', 'predicted', 'residual', 'leverage', 'studentized'])
            or any(not 0 <= r['leverage'] < 1 for r in results)):
        raise ValueError('Independent verification requires finite returned coefficients/results and exact model count')
    centered = x - x.mean()
    spread = centered @ centered
    h = 1 / n + centered ** 2 / spread
    design = np.column_stack([np.ones(n), centered])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    predicted = design @ beta
    residual = y - predicted
    sse = float(residual @ residual)
    full_tolerance = 64 * np.finfo(float).eps * max(1., np.linalg.cond(design)) * max(np.linalg.norm(y), np.linalg.norm(predicted))
    if np.linalg.matrix_rank(design) != 2 or not math.isfinite(sse) or np.linalg.norm(residual) <= full_tolerance:
        raise ValueError('Independent full design/positive residual scale is unavailable')
    r2 = 1 - sse / ((y - y.mean()) @ (y - y.mean()))
    if [r['actual'] for r in results] != y.tolist():
        raise ValueError('Independent verification requires exact native actual proficiency')
    if any(r['low'] is not None or r['high'] is not None for r in results):
        raise ValueError('Point-only audit cannot expose numerical interval endpoints')
    errors = {
        'coefficient': max(abs(float(beta[0] - beta[1] * x.mean()) - model['intercept']),
                           abs(float(beta[1]) - model['slope'])),
        'predicted': max(abs(float(v) - r['predicted']) for v, r in zip(predicted, results)),
        'residual': max(abs(float(v) - r['residual']) for v, r in zip(residual, results)),
        'r2': abs(float(r2) - model['r2']), 'leverage': 0., 'studentized': 0.,
        'deleted_sse_identity': 0., 'held_out_prediction_identity': 0.,
        'interval_endpoint': None,
    }
    deleted = []
    for i in range(n):
        keep = np.arange(n) != i
        mean_x = x[keep].mean()
        deleted_centered = x[keep] - mean_x
        X = np.column_stack([np.ones(n - 1), deleted_centered])
        if np.linalg.matrix_rank(X) != 2:
            raise ValueError('Explicit deleted-school income design is rank deficient')
        b = np.linalg.lstsq(X, y[keep], rcond=None)[0]
        e = y[keep] - X @ b
        deleted_sse = float(e @ e)
        residual_tolerance = 64 * np.finfo(float).eps * max(1., np.linalg.cond(X)) * max(
            np.linalg.norm(y[keep]), np.linalg.norm(X @ b))
        if not math.isfinite(deleted_sse) or np.linalg.norm(e) <= residual_tolerance:
            raise ValueError('Explicit deleted-school residual scale is unavailable or numerically unresolved')
        held_out = float(b[0] + b[1] * (x[i] - mean_x))
        predictive_h = 1 / (n - 1) + (x[i] - mean_x) ** 2 / (deleted_centered @ deleted_centered)
        scale = math.sqrt(deleted_sse / (n - 3))
        external_t = (y[i] - held_out) / (scale * math.sqrt(1 + predictive_h))
        errors['studentized'] = max(errors['studentized'], abs(external_t - results[i]['studentized']))
        errors['leverage'] = max(errors['leverage'], abs(h[i] - results[i]['leverage']))
        errors['deleted_sse_identity'] = max(errors['deleted_sse_identity'],
                                             abs(deleted_sse - (sse - residual[i] ** 2 / (1 - h[i]))))
        errors['held_out_prediction_identity'] = max(errors['held_out_prediction_identity'],
                                                      abs(held_out - (predicted[i] - h[i] * residual[i] / (1 - h[i]))))
        deleted.append({'intercept': float(b[0] - b[1] * mean_x), 'slope': float(b[1]),
                        'sse': deleted_sse, 'held_out_prediction': held_out,
                        'held_out_prediction_leverage': float(predictive_h),
                        'residual_scale': scale, 'externally_studentized': float(external_t)})
    if any(v is not None and (not math.isfinite(v) or v > VERIFY_TOLERANCE) for v in errors.values()):
        raise ValueError('Independent full/deleted-fit verification exceeded tolerance')
    # JSON preserves Python float/int/bool types but not NumPy scalar classes.
    # Normalize computed errors before strict typed replay; native evidence is
    # never coerced and booleans remain invalid numerical substitutions.
    return deleted, {k: None if v is None else float(v) for k, v in errors.items()}




def fit_audited_model(inputs, coverage, subject):
    require_runtime_contract()
    if subject not in SUBJECTS:
        raise ValueError('Only three proposed grade-school subjects may be audited')
    if not isinstance(inputs, list) or any(not isinstance(r, dict) for r in inputs):
        raise ValueError('District inputs require original frozen native records')
    if len(inputs) < MIN_SCHOOLS:
        raise ValueError('District subject model requires at least 30 usable schools')
    frozen_inputs, frozen_coverage = selected_inputs(load_roster(), subject)
    if ([r.get('school_id') for r in inputs] != [r['school_id'] for r in frozen_inputs]
            or roster_audit.fingerprint(inputs) != roster_audit.fingerprint(frozen_inputs)
            or roster_audit.fingerprint(coverage) != roster_audit.fingerprint(frozen_coverage)):
        raise ValueError('District fit requires exact frozen native inputs, complete eligible membership and coverage')
    if (len({r['school_id'] for r in inputs}) != len(inputs)
            or len({r['native_school_id'] for r in inputs}) != len(inputs)
            or any(r['level']!='ES' or type(r['income_year']) is not int or r['income_year']!=2025
                   or r['academic_year']!='2024-2025'
                   or not re.fullmatch(roster_audit.DISTRICT+r'\d{3}',r['native_school_id'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
                   or r['school_id']!=r['ncessch']
                   or r['ten_valid_scored_floor_certified'] is not False for r in inputs)):
        raise ValueError('District members require exact same-year native pure grade-school identities and income')
    if any(r['sampling_variance'] is not None or r['display_valid_scores'] is not None
           or r['valid_scores_by_subject'] != {'math': None, 'reading': None} for r in inputs):
        raise ValueError('Point-only source contract prohibits fabricated counts or sampling variance')
    if subject == 'combined' and any(r['outcome_pct'] != (r['outcome_by_subject']['math'] + r['outcome_by_subject']['reading']) / 2 for r in inputs):
        raise ValueError('Combined must be the exact equally weighted subject mean')
    if any(isinstance(r[k], bool) or not isinstance(r[k], (int, float)) for r in inputs for k in ['income_pct', 'outcome_pct']):
        raise ValueError('District income and proficiency require numeric percentage values, never booleans')
    x = np.array([r['income_pct'] for r in inputs], dtype=float)
    y = np.array([r['outcome_pct'] for r in inputs], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any((x < 0) | (x > 100) | (y < 0) | (y > 100)):
        raise ValueError('District income and proficiency must be finite percentages')
    design = np.column_stack([np.ones(len(x)), x])
    rank = int(np.linalg.matrix_rank(design))
    if rank != 2:
        raise ValueError('District income design must have rank two')
    # fit_model requires a variance vector. This zero vector is only its point-estimate
    # computational sentinel; no zero sampling variances or generated endpoints survive.
    model, fitted = fit_model(x, y, np.zeros(len(inputs), dtype=float))
    for row in fitted:
        row.update(low=None, high=None)
    deleted, errors = verify_independently(x, y, model, fitted)
    residual = np.array([r['residual'] for r in fitted])
    sse = float(residual @ residual)
    s2 = sse / (len(x) - 2)
    results = []
    thresholds = {'leverage_2p_over_n': 4 / len(x), 'cooks_4_over_n': 4 / len(x),
                  'absolute_external_t': 2.}
    for school, row, deletion in zip(inputs, fitted, deleted):
        h = row['leverage']
        cook = row['residual'] ** 2 * h / (2 * s2 * (1 - h) ** 2)
        endpoints = np.array([x.min(), x.max()])
        shift = (deletion['intercept'] - model['intercept']) + (deletion['slope'] - model['slope']) * endpoints
        results.append({
            'school_id': school['school_id'], **row, 'valid_scores': None, 'sampling_variance': None,
            'cooks_distance': float(cook), 'deleted_intercept': deletion['intercept'],
            'deleted_slope': deletion['slope'], 'deleted_sse': deletion['sse'],
            'deleted_residual_scale': deletion['residual_scale'],
            'deleted_held_out_prediction': deletion['held_out_prediction'],
            'deleted_held_out_prediction_leverage': deletion['held_out_prediction_leverage'],
            'maximum_prediction_change_on_observed_income_range': float(np.max(np.abs(shift))),
            'review_flags': {'leverage_above_2p_over_n': h > thresholds['leverage_2p_over_n'],
                             'cooks_above_4_over_n': cook > thresholds['cooks_4_over_n'],
                             'absolute_external_t_above_2': abs(row['studentized']) > 2},
        })
    by_id = {r['school_id']: r for r in inputs}
    influence = []
    for row in sorted(results, key=lambda r: (-r['cooks_distance'], r['school_id']))[:10]:
        school = by_id[row['school_id']]
        influence.append({k: school[k] for k in ['school_id', 'name', 'charter', 'ccd_school_type', 'income_pct']} |
                         {k: row[k] for k in ['cooks_distance', 'leverage', 'studentized']})
    return {
        'model_id': f'cypress-fairbanks-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': False, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact Cypress-Fairbanks attached-LEA enrolled positive grades 3–8/no-high-grade population; precise October 2024 individual economic-status count ratio and original published 2024–25 All Students TAPR whole Meets-or-above subject rates',
        'level': 'ES', 'subject': subject, 'assessment': ASSESSMENT,
        'assessment_standard': STANDARD,
        'coverage': coverage, 'inputs': inputs,
        'population_sha256': roster_audit.fingerprint({'policy': POLICY, 'source_audit_sha256': ROSTER_SHA,
                                                      'level': 'ES', 'subject': subject, 'year': 2025,
                                                      'school_ids': [r['school_id'] for r in inputs]}),
        'coefficients': model, 'results': results,
        'review_warnings': [
            'Valid-score denominators remain unverified; no count, sampling variance or interval is available.',
            'Conventional leverage, Cook distance and residual flags require descriptive review, never automatic exclusions.',
            'Individual October economic status covers all enrolled grades, broader than accountable tested children. Original whole-percent rates, STAAR/Spanish/Alternate2/IncludingEOC mixtures and suppression remain limits. Exact2025 N/M valid-score mapping and the ten-valid-scored floor remain unverified.',
        ],
        'intervals': {'available_for_entire_model': False, 'eligible_members': len(inputs),
                      'eligible_members_with_verified_denominators': 0,
                      'valid_score_counts': None, 'sampling_variances': None, 'ten_valid_scored_floor_certified': False,
                      'reason': 'Native Texas performance-status scope and the ten-valid-scored minimum remain uncertified; original unmasked published Meets-or-above R cells support this point-only numerical audit without certified counts or intervals.'},
        'diagnostics': {
            'income_design_rank': rank, 'income_design_condition_number': float(np.linalg.cond(design)),
            'centered_income_design_condition_number': float(np.linalg.cond(np.column_stack([np.ones(len(x)), x - x.mean()]))),
            'income': {'minimum': float(x.min()), 'maximum': float(x.max()), 'mean': float(x.mean()),
                       'standard_deviation_population': float(x.std()), 'distinct': len(set(x.tolist())),
                       'quantiles': {str(q): float(np.quantile(x, q)) for q in [.05, .25, .5, .75, .95]}},
            'residual_sse': sse, 'residual_standard_error': float(math.sqrt(s2)),
            'full_residual_degrees_of_freedom': len(x) - 2,
            'deleted_residual_degrees_of_freedom': len(x) - 3,
            'minimum_deleted_sse': min(r['sse'] for r in deleted),
            'minimum_deleted_residual_scale': min(r['residual_scale'] for r in deleted),
            'maximum_leverage': max(r['leverage'] for r in results),
            'maximum_absolute_studentized_residual': max(abs(r['studentized']) for r in results),
            'maximum_cooks_distance': max(r['cooks_distance'] for r in results),
            'maximum_absolute_deleted_slope_change': max(abs(r['slope'] - model['slope']) for r in deleted),
            'deleted_slope_range': {'minimum': min(r['slope'] for r in deleted), 'maximum': max(r['slope'] for r in deleted)},
            'maximum_prediction_change_on_observed_income_range': max(r['maximum_prediction_change_on_observed_income_range'] for r in results),
            'conventional_review_thresholds': thresholds,
            'conventional_review_flag_counts': {key: sum(r['review_flags'][key] for r in results) for key in results[0]['review_flags']},
            'top_ten_cooks_distance': influence,
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Original whole-percent precision, broader fall individual economic status, accountable tested subset and grade/STAAR/Spanish/Alternate2/EOC mixtures, unverified N/M score-status scope and uncertified ten-valid-scored minimum remain limitations.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Interval verification is inapplicable because all verified valid-score denominators are unavailable; Native enrolled economic denominator, PEIMS/CCD membership and reported performance counts remain linked original provenance, never certified assessment denominators or a scored-count-floor certificate.'},
    }


def build(roster=None):
    roster = load_roster() if roster is None else roster
    require_frozen_roster(roster)
    models, holds = [], []
    for subject in SUBJECTS:
        inputs, coverage = selected_inputs(roster, subject)
        try:
            model = fit_audited_model(inputs, coverage, subject)
        except ValueError as error:
            model = dict(model_id=f'cypress-fairbanks-2025-ES-{subject}', status='numerical_hold', approved_for_source=False,
                         approved_for_modeling=False, level='ES', subject=subject, inputs=inputs, coverage=coverage, reason=str(error))
            holds.append(dict(model_id=model['model_id'], reason=str(error)))
        models.append(model)
    population = frozen_population(roster)
    return dict(schema_version=1,state='TX',year=2025,academic_year='2024-2025',
        nces_lea_id=roster_audit.LEA,native_lea_id=roster_audit.NATIVE_LEA,native_district_id=roster_audit.DISTRICT,
        scope='numerical_audit_only',status='numerical_hold' if holds else 'numerically_verified_pending_integration',
        approved_for_source=False,approved_for_modeling=False,policy=POLICY,
        sources=dict(roster_audit=dict(path='data/source/cypress-fairbanks-district-audit.json',sha256=ROSTER_SHA,bytes=ROSTER_BYTES),
            source_audit_code=dict(path='scripts/audit_cypress_fairbanks.py',sha256=SOURCE_CODE_SHA),
            source_audit_tests=dict(path='tests/test_cypress_fairbanks_audit.py',sha256=SOURCE_TESTS_SHA),
            source_policy_sha256=SOURCE_POLICY_SHA,
            numerical_policy_sha256=NUMERIC_POLICY_SHA, numerical_runtime_sha256=RUNTIME_CONTRACT_SHA,
            source_runtime_sha256=SOURCE_RUNTIME_SHA, source_identity_sha256=SOURCE_IDENTITY_SHA,
            secondary_texas_extract=dict(path="data/source/texas.json",sha256=SOURCE_SECONDARY_SHA),
            original_raw_input_sha256=roster_audit.RAW_INPUT_SHA,
            original_schema_sha256=roster_audit.ORIGINAL_SCHEMA_SHA,
            original_definition_evidence_sha256=roster_audit.DEFINITION_INPUT_SHA,
            native_primary_sources=roster['sources']),
        retained_source_reference=dict(path='data/source/cypress-fairbanks-district-audit.json',sha256=ROSTER_SHA,
            source_scope=roster['scope'],source_status=roster['status'],
            approved_for_source=False,approved_for_modeling=False,
            complete_original_record_count=1107,complete_original_cell_count=42828,
            note='Every original record/header/definition/raw value remains in the immutable linked source artifact and must validate on every numerical replay; compact references never permit unavailable or changed source evidence.'),
        count_definition_status=dict(status='unverified_exact_2025_N_M_performance_scope',
            raw_fields={s:roster_audit.FIELDS[s][:2] for s in ['math','reading']},
            valid_score_counts=None,sampling_variances=None,sampling_intervals_available=False,
            ten_valid_scored_floor_certified=False,
            reason='Exact native reported-performance N/NAAR and M/medical status mapping remains held; native counts/enrollment never screen this published-rate audit or certify the ten-scored floor.'),
        frozen_population=population,frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY,population=population)),
        source_coverage=roster['coverage'],
        retained_scope_exclusions=[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],
            name=r['name'],source_roster_link_index=i,exclusion=r['exclusion'],
            native_scope=None if r['native_enrolled'] is None else r['native_enrolled']['scope'])
            for i,r in enumerate(roster['roster_links']) if r['exclusion'] is not None],
        replay_tolerance=dict(absolute=ABS_TOLERANCE,relative=REL_TOLERANCE,
            scope='Computed finite floating-point metrics only, strict numeric types. Source fingerprints/references, identity, x/y, original whole rates/income, membership, counts, approvals and absent intervals compare exactly.'),
        models=models,hard_holds=holds)


def numeric_equal(actual, expected):
    if type(expected) is float:
        return type(actual) is float and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(numeric_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(numeric_equal(a, e) for a, e in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def validate(document, expected=None):
    # Compact artifacts remain auditable only while the complete immutable
    # source/code/tests/policy still validate, even with a cached expected fit.
    roster = load_roster()
    expected = build(roster) if expected is None else expected
    if not isinstance(document, dict) or roster_audit.fingerprint({k: v for k, v in document.items() if k != 'models'}) != roster_audit.fingerprint({k: v for k, v in expected.items() if k != 'models'}):
        raise ValueError('Cypress-Fairbanks ISD numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('Cypress-Fairbanks ISD numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('Cypress-Fairbanks ISD model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('Cypress-Fairbanks ISD numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('Cypress-Fairbanks ISD independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'sampling_variance', 'low', 'high']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('Cypress-Fairbanks ISD result identities/native outcomes/counts or interval absence changed')
        if not numeric_equal(actual, model):
            raise ValueError('Cypress-Fairbanks ISD numerical metrics failed independent typed/finite replay tolerance')
    return {m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}


def prepare(output=OUTPUT, check=False):
    expected = build()
    if check:
        validate(json.loads(Path(output).read_text()), expected)
    else:
        Path(output).write_text(json.dumps(expected, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    return dict(models={m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}, hard_holds=expected['hard_holds'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute and validate saved audit without rewriting it')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.check), sort_keys=True))

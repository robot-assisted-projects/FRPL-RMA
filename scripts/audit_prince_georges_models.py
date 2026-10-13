"""Replay Prince George's County regular MCAP point-only fits; no import or publication."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

import audit_prince_georges as roster_audit
from prepare_data import fit_model

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/prince-georges-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = 'f097fb88001cb3749fc5ebc31a5786421fa3aebad207d61172ad3baed8a6d33a'
ROSTER_BYTES = 4845702
SOURCE_CODE = ROOT / 'scripts/audit_prince_georges.py'
SOURCE_CODE_SHA = 'df2553327f7a89771574f95585930ae4ad7e3791e0f8f73fa9087172347d751e'
SOURCE_TESTS = ROOT / 'tests/test_prince_georges_audit.py'
SOURCE_TESTS_SHA = 'acbf3b0666687db27b820067ab7adcb67b9eb9268cb047c4ecc348511bc3d13b'
SOURCE_POLICY_SHA = '6bee3876109f64b15621bc28dea7eac88acadb99d3555c9b92962bd07c36ef68'
SOURCE_RAW_SHA = 'd73cee70ffb91b37d7f63ef5e7947621d5c59250264fed969012d4bad7ed8708'
SOURCE_SCHEMA_SHA = 'e2bb249f4fa01a29619d0c2c54c8a1237e7062752a43e66af2d59e2bd0505fb5'
SOURCE_DEFINITION_SHA = '9a3f18b926c3639e4a2152ab0ce93ae513dd5f5b660bd5aafd49af1e1d2e4eac'
SOURCE_IDENTITY_SHA = 'f326855a6626e853568bf1a91cf68b8f6bde256e318971ef76fa85256b3b9f66'
MIN_SCHOOLS = 30
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
SUBJECTS = ['math', 'reading', 'combined']
ASSESSMENT = 'Regular MCAP All Students All Grades published Levels 3/4 proficiency'
STANDARD = '2021–22 four-level regular MCAP standards; 2024–25 Math includes accelerated Algebra 1, Geometry and Algebra 2 with applicable grade 6–7 course waiver; DLM remains separate'
SUBJECT_LABELS = {'math': 'Mathematics All Grades', 'reading': 'English Language Arts All Grades'}
SUBJECT_MEMBERS = {'math': '2025 MCAP MATH Administrative Data Report Card.xlsx', 'reading': '2025 MCAP ELA Administrative Data Report Card.xlsx'}
POLICY = {
    **{k: roster_audit.POLICY[k] for k in ['identity','population','income','denominator','assessment','accelerated_scope','suppression','counts','combined','identity_holds','income_denominator_discrepancy']},
    'eligibility': 'Reconstruct exact original native directory NCES-to-CCD ownership, operational status, complete unadjusted lower offers, strictly positive numeric September grade3–8 and absence of any high-grade row. Select original whole-school All Early Attendance band with its own individual count ratio, and each original regular School_Level Year2025 All Students All Grades published rate. Retain159 searchable prospective source profiles;13 Math masks exclude only Math/Combined. Labels, administrative tests, charters and influence never select membership.',
    'models': 'Separate unweighted centered 2024–25 Prince George’s grade-school Math, ELA and Combined OLS. Combined independently fits the paired146 original-rate means; its population differs from159 ELA and cannot average subject coefficients or studentized scores. No weights, enrollment adjustment, fit-driven exclusions or national pooling.',
    'minimum_usable_subject_schools': MIN_SCHOOLS,
    'studentization': 'Externally studentized residuals use every explicit deleted-school fit and N−3 residual degrees of freedom, independent centered full fits and held-out leverage. Cook distance and prediction sensitivity over the observed income range are descriptive, never exclusions or clamping.',
    'intervals': 'All valid-score counts, sampling variances and interval endpoints are null modelwide; the ten-valid-scored floor is uncertified. An internal zero variance vector is solely a point-estimate computational sentinel, never an uncertainty estimate.',
    'compact_provenance': 'Complete committed immutable source retains all5404 original records/89640 typed cells, headers, primary definitions and identity holds. Exact whole blob, source code/tests/policy/raw/schema/definition/identity fingerprints and current semantic replay are required on every numerical replay, including cached expected fits. Exact inputs and native row/member/worksheet/field references replace repeated raw tables/PDFs.',
    'release': 'Numerical audit only pending independent review and separate canonical/browser integration. Historical source and numerical source/modeling approvals remain false; high/mixed/primary/unknown/unmatched/closed scopes and count holds remain unreleased.'
}


def load_roster(path=ROSTER):
    for source, expected, label in [(SOURCE_CODE,SOURCE_CODE_SHA,'code'),(SOURCE_TESTS,SOURCE_TESTS_SHA,'tests')]:
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen Prince George’s source '+label+' changed; fresh numerical audit required')
    pins = [(roster_audit.fingerprint(roster_audit.POLICY),SOURCE_POLICY_SHA),
            (roster_audit.RAW_INPUT_SHA,SOURCE_RAW_SHA),(roster_audit.ORIGINAL_SCHEMA_SHA,SOURCE_SCHEMA_SHA),
            (roster_audit.DEFINITION_INPUT_SHA,SOURCE_DEFINITION_SHA),(roster_audit.ORIGINAL_IDENTITY_SHA,SOURCE_IDENTITY_SHA)]
    if any(actual!=expected for actual,expected in pins):
        raise ValueError('Frozen Prince George’s source policy/raw/schema/definition/identity pins changed')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=ROSTER_SHA or len(data)!=ROSTER_BYTES:
        raise ValueError('Frozen complete Prince George’s source artifact changed; fresh numerical audit required')
    document=json.loads(data)
    roster_audit.validate(document)
    return document


def require_frozen_roster(roster):
    if roster_audit.fingerprint(roster)!=roster_audit.fingerprint(load_roster()):
        raise ValueError('In-memory Prince George’s source differs from the complete frozen artifact')


def frozen_population(roster):
    links=roster['roster_links'];cohorts=roster['cohorts']
    return dict(complete_native_school_ids=sorted(r['school_id']for r in links),
        complete_directory_ncessch=sorted(e['raw']['NCESSCH']for e in roster['raw_inputs']['directory']['records']),
        operational_directory_ncessch=sorted(e['raw']['NCESSCH']for e in roster['raw_inputs']['directory']['records']if e['raw']['UPDATED_STATUS']in roster_audit.OPERATIONAL),
        grade_school_configuration_ids=sorted(cohorts['native_grade_school_source_profiles']['school_ids']),
        eligible_school_ids_by_subject={s:sorted(cohorts['native_grade_school_source_profiles']['subjects'][s]['eligible_school_ids'])for s in SUBJECTS},
        high_school_configuration_ids=sorted(cohorts['native_high_configurations']['school_ids']),
        mixed_configuration_ids=sorted(cohorts['native_mixed_configurations']['school_ids']),
        primary_configuration_ids=sorted(cohorts['native_primary_configurations']['school_ids']),
        unknown_configuration_ids=sorted(cohorts['native_unknown_configurations']['school_ids']),
        nonoperational_directory_ncessch=sorted(e['raw']['NCESSCH']for e in roster['nonoperational_directory']),
        unmatched_native_school_ids=sorted(roster_audit.native_identity(e['raw'])for e in roster['unmatched_native_directory']),
        unmatched_directory_ncessch=sorted(e['raw']['NCESSCH']for e in roster['unmatched_ccd_directory']))


def original_number(raw, *, count=False):
    if raw is None or type(raw)is str and (not raw.strip()or raw.strip()=='*'or '<'in raw or '>'in raw):
        return None
    if type(raw)is not str or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',raw.strip()):
        raise ValueError('Original native count/rate token must remain numeric string or masked')
    value=float(raw.strip())
    if not math.isfinite(value)or value<0 or count and value!=int(value)or not count and value>100:
        raise ValueError('Original native count/rate is outside its finite domain')
    return int(value)if count else value


def source_references(roster, link, native, ccd, income_rows, selected_income, grades, outcomes):
    return dict(roster_link_index=next(i for i,r in enumerate(roster['roster_links'])if r['school_id']==link['school_id']),
        directory_source_row=ccd['source_row'],native_directory=dict(table='native_directory',source_row=native['source_row'],member=native['member'],worksheet=native['worksheet']),
        income=dict(table='native_income',source_rows=[e['source_row']for e in income_rows],selected_source_row=None if selected_income is None else selected_income['source_row'],
            school_type_field='School Type',selected_school_type=None if selected_income is None else selected_income['raw']['School Type'],
            fields=['Total Student Cnt','Economically Disadvantaged Cnt','Economically Disadvantaged Pct']),
        native_enrollment=dict(table='native_enrollment',source_rows=[e['source_row']for e in grades],fields=['Grade','Enrolled Count']),
        outcomes={s:None if outcomes.get(s)is None else dict(table='native_assessment',source_row=outcomes[s]['source_row'],
            member=outcomes[s]['member'],worksheet=outcomes[s]['worksheet'],assessment=outcomes[s]['raw']['Assessment'],
            fields=['Year','LEA','School','Student Group','Assessment','Proficient Pct','Tested Count','Proficient Count'])for s in ['math','reading']})


def selected_inputs(roster, subject):
    """Rebuild exact source membership from original records independently of source selectors."""
    if subject not in SUBJECTS:
        raise ValueError('Only three separate grade-school subjects may be audited')
    require_frozen_roster(roster)
    raw=roster['raw_inputs'];ccd={e['raw']['NCESSCH']:e for e in raw['directory']['records']}
    directory={roster_audit.native_identity(e['raw']):e for e in raw['native_directory']['records']}
    enrollment,income,assessment=defaultdict(list),defaultdict(list),defaultdict(list)
    for table,target,is_income in [('native_enrollment',enrollment,False),('native_income',income,True),('native_assessment',assessment,False)]:
        for e in raw[table]['records']:
            target[roster_audit.native_identity(e['raw'],income=is_income,aggregate=True)].append(e)
    inputs,exclusions,configurations=[],[],[];required=['math','reading']if subject=='combined'else[subject]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id'];native=directory[key];profile=native['raw'];nces=str(profile['NCES Number']);entry=ccd.get(nces)
        grades=enrollment[key]
        if entry is None:
            continue
        c=entry['raw'];flags={g:c.get('G_'+g+'_OFFERED')for g in roster_audit.GRADES}
        complete=c.get('IGOFFERED')=='As reported'and c.get('NOGRADES')=='No'and all(v in {'Yes','No'}for v in flags.values())
        scoped=(profile['Grade Span']in {'E','M','EM'}and c['UPDATED_STATUS']in roster_audit.OPERATIONAL and complete
                and any(flags[str(g)]=='Yes'for g in range(3,9))and not any(flags[g]=='Yes'for g in [str(n)for n in range(9,14)]+['UG','AE'])
                and re.fullmatch(r'0[3-8]',c.get('GSHI',''))is not None
                and not any(e['raw']['Grade']in [f'Grade {g}'for g in range(9,13)]for e in grades)
                and not any(e['raw']['Grade']not in {'All Grades','Prekindergarten Age 4','Kindergarten'}|{f'Grade {g}'for g in range(1,13)}for e in grades)
                and any(e['raw']['Grade']in [f'Grade {g}'for g in range(3,9)]and original_number(e['raw']['Enrolled Count'],count=True)not in {None,0}for e in grades))
        if scoped is not link['source_profile_eligible']:
            raise ValueError('Independent original grade configuration differs from frozen source')
        if not scoped:
            continue
        configurations.append(key)
        rows=income[key];selected=[e for e in rows if e['raw']['School Type']=='All']if len(rows)>1 else rows
        if len(selected)!=1:
            chosen=None;n=low=display=None
        else:
            chosen=selected[0];r=chosen['raw'];n=original_number(r['Total Student Cnt'],count=True);low=original_number(r['Economically Disadvantaged Cnt'],count=True);display=original_number(r['Economically Disadvantaged Pct'])
        usable_income=None not in (n,low,display)and n>0 and 0<=low<=n and abs(100*low/n-display)<=.0500001
        outcomes={}
        for e in assessment[key]:
            for s in ['math','reading']:
                r=e['raw']
                if (e['member']==SUBJECT_MEMBERS[s]and e['worksheet']=='School_Level'and type(r['Year'])is int and r['Year']==2025
                        and r['Student Group']=='All Students'and r['Assessment'].strip()==SUBJECT_LABELS[s]):
                    if s in outcomes:raise ValueError('Duplicate original All Grades subject row')
                    outcomes[s]=e
        rates={s:None if s not in outcomes else original_number(outcomes[s]['raw']['Proficient Pct'])for s in ['math','reading']}
        references=source_references(roster,link,native,entry,rows,chosen,grades,outcomes)
        reasons=[]if usable_income else['Native individual Early Attendance income missing, masked or unreconciled']
        reasons += [s+': original regular All Grades rate missing or masked'for s in required if rates[s]is None]
        raw_rates={s:None if s not in outcomes else outcomes[s]['raw']['Proficient Pct']for s in ['math','reading']}
        if reasons:
            exclusions.append(dict(school_id=key,native_school_id=c['ST_SCHID'],ncessch=nces,name=link['name'],reason='; '.join(reasons),raw_published_rates=raw_rates,source_refs=references))
            continue
        outcome=(rates['math']+rates['reading'])/2 if subject=='combined'else rates[subject];x=100*low/n
        if x!=link['income']['percentage']or outcome!=link['subjects'][subject]['native_rate']:
            raise ValueError('Independent original income/published outcome differs from frozen source')
        inputs.append(dict(school_id=key,native_school_id=c['ST_SCHID'],ncessch=nces,name=link['name'],level='ES',
            charter=c['CHARTER_TEXT'],ccd_school_type=c['SCH_TYPE_TEXT'],native_grade_span=profile['Grade Span'],
            income_pct=x,income_year=2025,academic_year='2024-2025',income_enrollment=n,individual_economic_count=low,
            outcome_pct=outcome,outcome_by_subject=rates,raw_published_rates=raw_rates,
            valid_scores_by_subject={'math':None,'reading':None},display_valid_scores=None,sampling_variance=None,
            ten_valid_scored_floor_certified=False,source_refs=references))
    cohort=roster['cohorts']['native_grade_school_source_profiles']
    if configurations!=sorted(cohort['school_ids'])or [r['school_id']for r in inputs]!=sorted(cohort['subjects'][subject]['eligible_school_ids']):
        raise ValueError('Complete original subject/configuration membership differs from frozen source')
    coverage=dict(grade_school_configuration_profiles=len(configurations),usable_schools=len(inputs),excluded_configuration_profiles=len(exclusions),excluded_configuration_records=exclusions,
        exclusions=dict(sorted(Counter(r['reason']for r in exclusions).items())),charter=dict(sorted(Counter(r['charter']for r in inputs).items())),
        school_types=dict(sorted(Counter(r['ccd_school_type']for r in inputs).items())),eligible_members_with_verified_denominators=0,
        ten_valid_scored_floor_certified=False,model_sampling_intervals_available=False,
        source_evidence_path='data/source/prince-georges-district-audit.json',source_evidence_sha256=ROSTER_SHA)
    return inputs,coverage


def verify_independently(x, y, model, results):
    """Centered full OLS, independent leverage and explicit held-out refits; no intervals."""
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
                   or not re.fullmatch(r'MD-16-\d{6}',r['native_school_id'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
                   or not re.fullmatch(r'16-\d{4}',r['school_id'])
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
    model, fitted = fit_model(x - x.mean(), y, np.zeros(len(inputs), dtype=float))
    model['intercept'] -= model['slope'] * float(x.mean())
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
        'model_id': f'prince-georges-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': False, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact Prince George’s attached-LEA native E/M/EM positive September grades3–8/no-high-grade population; precise own Early Attendance individual direct-certification ratio and original regular2025 All Students All Grades MCAP published Levels3/4 rates',
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
            'Individual Early Attendance covers all school grades and a different date/population from regular MCAP. Published one-decimal percentages, regular All Grades accelerated-course scope, grade6–7 waiver and source13 Math masks remain limits; DLM stays separate. Administrative tested counts and the ten-valid-scored floor remain uncertified.',
        ],
        'intervals': {'available_for_entire_model': False, 'eligible_members': len(inputs),
                      'eligible_members_with_verified_denominators': 0,
                      'valid_score_counts': None, 'sampling_variances': None, 'ten_valid_scored_floor_certified': False,
                      'reason': 'Regular MCAP valid-score administrative business rules and the ten-valid-scored minimum remain uncertified; original unmasked published Levels3/4 rates support this point-only numerical audit without certified counts or intervals.'},
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
            'predicted_range': {'minimum': min(r['predicted'] for r in results), 'maximum': max(r['predicted'] for r in results)},
            'predictions_outside_percentage_range': sum(r['predicted'] < 0 or r['predicted'] > 100 for r in results),
            'maximum_leverage': max(r['leverage'] for r in results),
            'maximum_absolute_studentized_residual': max(abs(r['studentized']) for r in results),
            'maximum_cooks_distance': max(r['cooks_distance'] for r in results),
            'maximum_absolute_deleted_slope_change': max(abs(r['slope'] - model['slope']) for r in deleted),
            'deleted_slope_range': {'minimum': min(r['slope'] for r in deleted), 'maximum': max(r['slope'] for r in deleted)},
            'maximum_prediction_change_on_observed_income_range': max(r['maximum_prediction_change_on_observed_income_range'] for r in results),
            'conventional_review_thresholds': thresholds,
            'conventional_review_flag_counts': {key: sum(r['review_flags'][key] for r in results) for key in results[0]['review_flags']},
            'top_ten_cooks_distance': influence,
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Native one-decimal precision, broader individual Early Attendance, regular All Grades course mixtures/waiver, unequal146/159/146 source populations and uncertified valid-score/floor definitions remain limitations; predictions are never clamped.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Interval verification is inapplicable because all verified valid-score denominators are unavailable; Native own Early Attendance denominator, September/CCD membership and administrative MCAP counts remain linked original provenance, never certified assessment denominators or a scored-count-floor certificate.'},
    }


def build(roster=None):
    roster=load_roster()if roster is None else roster
    require_frozen_roster(roster)
    models,holds=[],[]
    for subject in SUBJECTS:
        inputs,coverage=selected_inputs(roster,subject)
        try:
            model=fit_audited_model(inputs,coverage,subject)
        except ValueError as error:
            model=dict(model_id=f'prince-georges-2025-ES-{subject}',status='numerical_hold',approved_for_source=False,
                approved_for_modeling=False,level='ES',subject=subject,inputs=inputs,coverage=coverage,reason=str(error))
            holds.append(dict(model_id=model['model_id'],reason=str(error)))
        models.append(model)
    population=frozen_population(roster)
    return dict(schema_version=1,state='MD',year=2025,academic_year='2024-2025',nces_lea_id=roster_audit.LEA,
        native_lea_id=roster_audit.NATIVE_LEA,msde_lea_id=roster_audit.MSDE_LEA,
        scope='numerical_audit_only',status='numerical_hold'if holds else'numerically_verified_pending_integration',approved_for_source=False,approved_for_modeling=False,policy=POLICY,
        sources=dict(roster_audit=dict(path='data/source/prince-georges-district-audit.json',sha256=ROSTER_SHA,bytes=ROSTER_BYTES),
            source_audit_code=dict(path='scripts/audit_prince_georges.py',sha256=SOURCE_CODE_SHA),source_audit_tests=dict(path='tests/test_prince_georges_audit.py',sha256=SOURCE_TESTS_SHA),
            source_policy_sha256=SOURCE_POLICY_SHA,original_raw_input_sha256=SOURCE_RAW_SHA,original_schema_sha256=SOURCE_SCHEMA_SHA,
            original_definition_evidence_sha256=SOURCE_DEFINITION_SHA,original_identity_projection_sha256=SOURCE_IDENTITY_SHA,native_primary_sources=roster['sources']),
        retained_source_reference=dict(path='data/source/prince-georges-district-audit.json',sha256=ROSTER_SHA,source_scope=roster['scope'],source_status=roster['status'],
            approved_for_source=False,approved_for_modeling=False,complete_original_record_count=5404,complete_original_cell_count=89640,
            note='Complete original records, headers, definitions, memberships and identity holds stay in the immutable linked source artifact; every numerical replay requires current available unchanged source/code/tests/policy and semantic validation.'),
        count_definition_status=dict(status='unverified_regular_mcap_valid_score_administrative_rules',raw_fields=['Tested Count','Proficient Count'],
            valid_score_counts=None,sampling_variances=None,sampling_intervals_available=False,ten_valid_scored_floor_certified=False,
            reason='Native administrative counts/grade-course sums are source evidence only; exact valid-score business rules and ten-valid-scored floor remain uncertified. Income and enrollment never substitute or select model membership.'),
        frozen_population=population,frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY,population=population)),
        source_coverage={k:v for k,v in roster['coverage'].items()if k not in {'district_membership_grade_evidence','district_early_attendance_income'}},
        retained_scope_exclusions=[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],ncessch=r['ncessch'],name=r['name'],
            source_roster_link_index=i,native_grade_span=r['native_grade_span'],identity_hold=r['identity_hold'],
            exclusion=r['identity_hold']or r['subjects']['math']['scope_exclusion'])for i,r in enumerate(roster['roster_links'])if not r['source_profile_eligible']],
        replay_tolerance=dict(absolute=ABS_TOLERANCE,relative=REL_TOLERANCE,scope='Computed finite floating-point metrics only, strict numeric types. Source fingerprints/references, exact identity/x/y/raw income/rates, subject membership, counts, approvals and absent intervals compare exactly.'),models=models,hard_holds=holds)


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
        raise ValueError('Prince George’s County numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('Prince George’s County numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('Prince George’s County model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('Prince George’s County numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('Prince George’s County independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'sampling_variance', 'low', 'high']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('Prince George’s County result identities/native outcomes/counts or interval absence changed')
        if not numeric_equal(actual, model):
            raise ValueError('Prince George’s County numerical metrics failed independent typed/finite replay tolerance')
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

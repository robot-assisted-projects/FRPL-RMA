"""Replay Cobb County Georgia Milestones EOG G38 point-only fits; no import or publication."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np
import audit_cobb as roster_audit
from prepare_data import fit_model
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/cobb-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = '979eb0b49e2a34362ffe7fa06103a76344a9378712b1569d1861dac67d7a2cde'
ROSTER_BYTES = 3452278
SOURCE_CODE = ROOT / 'scripts/audit_cobb.py'
SOURCE_CODE_SHA = 'f545a276b1240b46a21375f3fd3ba699a9b25afa19ec67da926cf965e0aa1eb1'
SOURCE_TESTS = ROOT / 'tests/test_cobb_audit.py'
SOURCE_TESTS_SHA = '90b7bdcfd21118fc1dee18fd74f4f76dbe640db03e2ae447249b2b8f9ff32930'
SOURCE_POLICY_SHA = 'e6d705f3db9cbba7b9fd37c1cb555edc13911f05b04f90fb2c024ba334a408ca'
SOURCE_RAW_SHA = '897c2c980a031f4f56e576760d8d42da568d133cdd68c293adb92068e85b6095'
SOURCE_SCHEMA_SHA = 'e17bb75e7e35a0e09cfba5ba5ed2d44d318fbd79544f2450c852a35305dd2384'
SOURCE_DEFINITION_SHA = '0a3b0b7c7318ff0753626aa50d2971b8bdbfdff66395feeace75c53f731ed1b8'
SOURCE_IDENTITY_SHA = '2959a5cb97315bffc80f4960b220d5384fdc22a73a5a71ef09a1af8bab40d2a5'
SOURCE_RUNTIME_SHA = 'cfa96ba5bf716278657cca08affd12e2ef85f110f846c11f044b598fceccb22a'
SOURCE_SECONDARY_SHA = '3b6e55bba0055c582eb14a461697c64131a36e4cd555bca94965e5f77cac91fc'
SOURCE_SNAPSHOT_SHA = '46d47899274835d484be76ac9b13515afb96474c54b5a676c4c43539df289a67'
MIN_SCHOOLS = 30
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
SUBJECTS = ['math', 'reading', 'combined']
ASSESSMENT = '2024–25 Georgia Milestones EOG regular All Students G38 published proficiency'
STANDARD = 'Original EDC v3.1 regular Georgia Milestones EOG All Students aggregate grades 3–8, Levels 3–4. Accelerated EOG/EOC population treatment, original source business rules and valid-score counts remain uncertified.'
SUBJECT_VALUES = {'math': 'math', 'reading': 'ela'}
ASSESSMENT_SELECTOR = dict(roster_audit.ASSESSMENT_SELECTOR)
INCOME_FIELDS = ['DATA_GROUP', 'LUNCH_PROGRAM', 'TOTAL_INDICATOR', 'DMS_FLAG', 'STUDENT_COUNT']
RATE_FIELD = 'ProficientOrAbove_percent'
POLICY = {
    **{k: roster_audit.POLICY[k] for k in ['identity', 'population', 'income', 'income_metadata', 'assessment', 'counts', 'attribution', 'suppression', 'combined', 'limitations']},
    'eligibility': 'Reconstruct exact same-year operational NCES/native ownership, complete lower grade offerings and positive reconciled own reported enrolled grades 3–8, individual reported direct certification / own reported membership, and original regular Georgia Milestones EOG School All Students G38 Math/ELA published-rate tokens. Retain all 90 grade-school profiles; primary-only, high and mixed scopes stay outside. No charter, income extreme, diagnostics, unverified count, grade average or old statewide result selects inputs.',
    'models': 'Separate unweighted centered Cobb County 2024–25 grade-school Math, ELA and Combined OLS. Combined independently fits paired original-rate means with its own scale, explicit deleted fits and external studentization, never averaged studentized scores. No enrollment weights, shrinkage, causal-effect claims, fit-driven exclusions, clamping or national pooling.',
    'minimum_usable_subject_schools': MIN_SCHOOLS,
    'studentization': 'Externally studentized residuals use every explicit deleted-school fit with N−3 residual degrees of freedom, independent centered full fits and held-out leverage. Cook distance and prediction sensitivity over observed income are descriptive, never eligibility filters.',
    'intervals': 'All valid-score counts, sampling variances and endpoints are null modelwide; the ten-valid-scored floor remains uncertified. A zero variance vector supplied to the shared fitter is solely a point-estimate computational sentinel, never an uncertainty estimate.',
    'compact_provenance': 'The complete immutable linked source retains 2,260 needed original records / 68,573 typed cells, full schemas and primary definitions, plus exact omission inventories for 25,662 complete target records / 865,003 cells. Whole source blob/code/tests, original raw/schema/definition/identity and current literal source/numerical policy/runtime checks are required before every replay, including supplied expected fits. Compact exact inputs and table/member/row/header-field references replace duplicated raw evidence. Supplied expected values must match freshly rebuilt source-derived full/deleted fits and cannot authorize themselves.',
    'release': 'Numerical audit only pending independent review and separate canonical/browser integration. Historical source and numerical approvals remain false. Georgia Medicaid/foster direct-certification scope, outside-program prekindergarten membership, nonlisted attribution coverage, accelerated EOG/EOC population uncertainty, masks and count limitations remain explicit.'
}
NUMERIC_POLICY_SHA = '6b25f52709fdd3a73f77bee7f0078ca4049e6049787dca7f689baea107a1575b'
RUNTIME_CONTRACT_SHA = '1c4a0addaa0a0bb5adb51a0a3f8c35d56aee661c1a56422e0f222a399a434ca3'

def runtime_contract():
    return dict(minimum=MIN_SCHOOLS, subjects=SUBJECTS, assessment=ASSESSMENT, standard=STANDARD,
        subject_values=SUBJECT_VALUES, assessment_selector=ASSESSMENT_SELECTOR, income_fields=INCOME_FIELDS,
        rate_field=RATE_FIELD, absolute_tolerance=ABS_TOLERANCE, relative_tolerance=REL_TOLERANCE,
        verify_tolerance=VERIFY_TOLERANCE, frozen_source=dict(path=str(ROSTER.relative_to(ROOT)),sha256=ROSTER_SHA,
        bytes=ROSTER_BYTES,code_path=str(SOURCE_CODE.relative_to(ROOT)),code_sha256=SOURCE_CODE_SHA,
        tests_path=str(SOURCE_TESTS.relative_to(ROOT)),tests_sha256=SOURCE_TESTS_SHA,policy=SOURCE_POLICY_SHA,
        raw=SOURCE_RAW_SHA,schema=SOURCE_SCHEMA_SHA,definitions=SOURCE_DEFINITION_SHA,identity=SOURCE_IDENTITY_SHA,
        runtime=SOURCE_RUNTIME_SHA,secondary=SOURCE_SECONDARY_SHA,snapshot=SOURCE_SNAPSHOT_SHA))

def require_runtime_contract():
    original_policy = '6b25f52709fdd3a73f77bee7f0078ca4049e6049787dca7f689baea107a1575b'
    original_contract = '1c4a0addaa0a0bb5adb51a0a3f8c35d56aee661c1a56422e0f222a399a434ca3'
    if (NUMERIC_POLICY_SHA != original_policy or RUNTIME_CONTRACT_SHA != original_contract
            or roster_audit.fingerprint(POLICY) != original_policy
            or roster_audit.fingerprint(runtime_contract()) != original_contract):
        raise ValueError('Frozen current Cobb numerical policy/types/subject/field/minimum/source contract changed')
    roster_audit.require_runtime_contract()

def load_roster(path=ROSTER):
    require_runtime_contract()
    for source, expected, label in [(SOURCE_CODE,SOURCE_CODE_SHA,'code'),(SOURCE_TESTS,SOURCE_TESTS_SHA,'tests')]:
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen Cobb source '+label+' changed; fresh numerical audit required')
    pins=[(roster_audit.fingerprint(roster_audit.POLICY),SOURCE_POLICY_SHA),(roster_audit.RAW_INPUT_SHA,SOURCE_RAW_SHA),
        (roster_audit.ORIGINAL_SCHEMA_SHA,SOURCE_SCHEMA_SHA),(roster_audit.DEFINITION_INPUT_SHA,SOURCE_DEFINITION_SHA),
        (roster_audit.ORIGINAL_IDENTITY_SHA,SOURCE_IDENTITY_SHA),(roster_audit.RUNTIME_CONTRACT_SHA,SOURCE_RUNTIME_SHA),
        (roster_audit.STATE_EXTRACT_SHA,SOURCE_SECONDARY_SHA),(roster_audit.GA_SNAPSHOT_SHA,SOURCE_SNAPSHOT_SHA)]
    if any(actual!=expected for actual,expected in pins):
        raise ValueError('Frozen Cobb current source policy/raw/schema/definition/identity/runtime pins changed')
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=ROSTER_SHA or len(data)!=ROSTER_BYTES:
        raise ValueError('Frozen complete Cobb source artifact changed; fresh numerical audit required')
    roster=json.loads(data);roster_audit.validate(roster);return roster

def require_frozen_roster(roster):
    if roster_audit.fingerprint(roster)!=roster_audit.fingerprint(load_roster()):
        raise ValueError('In-memory Cobb source differs from complete frozen artifact')

def frozen_population(roster):
    links=roster['roster_links'];c=roster['cohorts']['grade_configuration'];coverage=roster['coverage']
    return dict(complete_directory_ncessch=sorted(r['school_id']for r in links),
        operational_directory_ncessch=sorted(r['school_id']for r in links if r['operational']),
        complete_native_school_ids=sorted({e['raw']['NCESSchoolID']for e in roster['raw_inputs']['assessment']['records']if e['raw']['DataLevel']=='School'}),
        grade_school_configuration_ids=sorted(c['profile_ids']),
        eligible_school_ids_by_subject={sub:sorted(c['subjects'][sub]['member_ids'])for sub in SUBJECTS},
        primary_only_ids=coverage['primary_only_ids'],
        high_school_configuration_ids=sorted(r['school_id']for r in links if r['offered']['scope']=='HS'),
        mixed_configuration_ids=sorted(r['school_id']for r in links if r['offered']['scope']=='mixed'),
        nonoperational_directory_ncessch=sorted(r['school_id']for r in links if not r['operational']),
        outside_charter_ids=sorted(r['school_id']for r in links if not r['source_profile_eligible']and r['ccd_flags']['charter']=='Yes'),
        unmatched_native_school_ids=coverage['native_only_ids'])

def original_count(raw):
    value=raw['STUDENT_COUNT'];flag=raw['DMS_FLAG']
    if type(value)is not str or type(flag)is not str:raise ValueError('Original count/flag must retain string types')
    return int(value)if flag=='Reported'and re.fullmatch(r'\d+',value)else None

def original_rate(value):
    if type(value)is not str:raise ValueError('Original native rate must retain its exact string token')
    if not re.fullmatch(r'(?:0?\.\d+|[01](?:\.\d+)?)',value):return None
    parsed=float(value);return 100*parsed if 0<=parsed<=1 else None

def table_reference(raw,table,entry,fields):
    if entry is None:return None
    section=raw[table]
    return dict(table=table,source_id=section['source_id'],member=section['member'],source_row=entry['source_row'],
        columns=[section['header'].index(f)for f in fields],fields=fields)

def source_references(roster,link,directory,total,grades,direct,pairs):
    raw=roster['raw_inputs'];identity=['SCHOOL_YEAR','LEAID','ST_LEAID','ST_SCHID','NCESSCH']
    return dict(roster_link_index=next(i for i,r in enumerate(roster['roster_links'])if r['school_id']==link['school_id']),
        directory=table_reference(raw,'directory',directory,identity+['UPDATED_STATUS','IGOFFERED','NOGRADES','GSLO','GSHI','CHARTER_TEXT','SCH_TYPE_TEXT']+['G_'+g+'_OFFERED'for g in roster_audit.OFFER_GRADES]),
        membership=table_reference(raw,'membership',total,identity+['GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG','STUDENT_COUNT']),
        enrolled_grades=dict(table='membership',source_id=raw['membership']['source_id'],member=raw['membership']['member'],source_rows={g:entry['source_row']for g,entry in sorted(grades.items())},fields=identity+['GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG','STUDENT_COUNT'],columns=[raw['membership']['header'].index(f)for f in identity+['GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG','STUDENT_COUNT']]),
        direct_certification=table_reference(raw,'lunch',direct,identity+INCOME_FIELDS),
        outcomes={sub:table_reference(raw,'assessment',pairs.get(sub),list(ASSESSMENT_SELECTOR)+['NCESDistrictID','StateAssignedDistID','NCESSchoolID','StateAssignedSchID','Subject',RATE_FIELD,'StudentSubGroup_TotalTested','ProficientOrAbove_count'])for sub in ['math','reading']})

def selected_inputs(roster,subject):
    """Reconstruct membership, own individual income and native rates from pinned original rows."""
    if subject not in SUBJECTS:raise ValueError('Only three separate grade-school subjects may be audited')
    require_frozen_roster(roster);raw=roster['raw_inputs']
    directory={e['raw']['NCESSCH']:e for e in raw['directory']['records']};totals={};grades=defaultdict(dict);direct={};pairs=defaultdict(dict)
    for entry in raw['membership']['records']:
        r=entry['raw'];key=r['NCESSCH']
        if r['TOTAL_INDICATOR']=='Education Unit Total':
            if key in totals:raise ValueError('Duplicate own reported membership total')
            totals[key]=entry
        elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade'and r['RACE_ETHNICITY']==r['SEX']=='No Category Codes':
            if r['GRADE']in grades[key]:raise ValueError('Duplicate own enrolled-grade subtotal')
            grades[key][r['GRADE']]=entry
    for entry in raw['lunch']['records']:
        r=entry['raw'];key=r['NCESSCH']
        if (r['DATA_GROUP'],r['TOTAL_INDICATOR'],r['LUNCH_PROGRAM'])==('Direct Certification','Education Unit Total','Not Applicable'):
            if key in direct:raise ValueError('Duplicate original individual direct-certification total')
            direct[key]=entry
    for entry in raw['assessment']['records']:
        r=entry['raw']
        if all(r[k]==v for k,v in ASSESSMENT_SELECTOR.items())and r['Subject']in SUBJECT_VALUES.values():
            sub='reading'if r['Subject']=='ela'else'math';key=r['NCESSchoolID']
            if sub in pairs[key]:raise ValueError('Duplicate exact school regular All Students G38 native subject')
            pairs[key][sub]=entry
    required=['math','reading']if subject=='combined'else[subject]
    inputs=[];exclusions=[];configurations=[]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id'];d=directory[key];r=d['raw'];n_entry=totals.get(key);own_grades=grades.get(key,{})
        if (r['LEAID'],r['ST_LEAID'],r['SCHOOL_YEAR'])!=('1301290','GA-633','2024-2025'):raise ValueError('Exact same-year native/NCES directory ownership changed')
        flags={g:r['G_'+g+'_OFFERED']for g in roster_audit.OFFER_GRADES}
        complete=r['IGOFFERED']=='As reported'and r['NOGRADES']=='No'and all(v in {'Yes','No'}for v in flags.values())
        lower=[original_count(e['raw'])for g,e in own_grades.items()if g in roster_audit.LOWER_GRADES]
        outside=[e['raw']for g,e in own_grades.items()if g not in roster_audit.LOWER_GRADES]
        n=original_count(n_entry['raw'])if n_entry else None
        reconciled=bool(lower)and all(v is not None for v in lower)and n is not None and sum(lower)==n and all(e['STUDENT_COUNT']=='0'and e['DMS_FLAG']in {'Reported','Derived'}for e in outside)
        enrolled={g:original_count(e['raw'])for g,e in own_grades.items()}
        scoped=r['UPDATED_STATUS']in roster_audit.OPERATIONAL and complete and any(flags[str(g)]=='Yes'for g in range(3,9))and not any(flags[g]=='Yes'for g in [str(v)for v in range(9,14)]+['AE'])and re.fullmatch(r'0[1-8]',r['GSHI'])is not None and (flags['UG']=='No'or enrolled.get('Ungraded')==0)and n is not None and n>0 and reconciled and any((enrolled.get('Grade '+str(g))or 0)>0 for g in range(3,9))
        if scoped is not link['source_profile_eligible']:raise ValueError('Independent original grade configuration differs from frozen source')
        if not scoped:continue
        configurations.append(key);dc_entry=direct.get(key);dc=original_count(dc_entry['raw'])if dc_entry else None
        income_valid=dc is not None and dc<=n
        if link['source_attribution_hold']is not None:raise ValueError('No Cobb source-attribution hold may be invented')
        rates={sub:original_rate(pairs[key][sub]['raw'][RATE_FIELD])if sub in pairs[key]else None for sub in ['math','reading']}
        raw_rates={sub:pairs[key][sub]['raw'][RATE_FIELD]if sub in pairs[key]else None for sub in ['math','reading']}
        x=100*dc/n if income_valid else None;refs=source_references(roster,link,d,n_entry,own_grades,dc_entry,pairs[key])
        reasons=[]if income_valid else['Reported individual direct certification / own membership is unavailable or invalid']
        reasons += [sub+': original published G38 rate missing, ranged or suppressed'for sub in required if rates[sub]is None]
        expected_usable=all(link['subjects'][sub]['usable']for sub in required)
        if bool(not reasons)is not expected_usable:raise ValueError('Independent exact original-rate/income membership differs')
        if reasons:
            exclusions.append(dict(school_id=key,native_school_id=r['ST_SCHID'],ncessch=key,name=link['name'],reason='; '.join(reasons),reported_income_pct=x,
                reported_membership=n,reported_direct_certified_count=dc,source_attribution_hold=link['source_attribution_hold'],raw_published_rates=raw_rates,source_refs=refs));continue
        outcome=(rates['math']+rates['reading'])/2 if subject=='combined'else rates[subject]
        if x!=link['income']['percentage']or outcome!=link['subjects'][subject]['native_rate']:raise ValueError('Independent original benefits income / published outcome differs')
        inputs.append(dict(school_id=key,native_school_id=r['ST_SCHID'],ncessch=key,name=link['name'],level='ES',charter=r['CHARTER_TEXT'],ccd_school_type=r['SCH_TYPE_TEXT'],income_pct=x,
            income_year=2025,academic_year='2024-2025',income_enrollment=n,reported_direct_certified_count=dc,outcome_pct=outcome,outcome_by_subject=rates,raw_published_rates=raw_rates,
            valid_scores_by_subject={'math':None,'reading':None},display_valid_scores=None,sampling_variance=None,ten_valid_scored_floor_certified=False,source_refs=refs))
    cohort=roster['cohorts']['grade_configuration']
    if configurations!=sorted(cohort['profile_ids'])or [r['school_id']for r in inputs]!=sorted(cohort['subjects'][subject]['member_ids']):raise ValueError('Complete original subject/configuration membership differs')
    coverage=dict(grade_school_configuration_profiles=len(configurations),usable_schools=len(inputs),excluded_configuration_profiles=len(exclusions),excluded_configuration_records=exclusions,
        exclusions=dict(sorted(Counter(r['reason']for r in exclusions).items())),charter=dict(sorted(Counter(r['charter']for r in inputs).items())),school_types=dict(sorted(Counter(r['ccd_school_type']for r in inputs).items())),
        eligible_members_with_verified_denominators=0,ten_valid_scored_floor_certified=False,model_sampling_intervals_available=False,
        source_evidence_path='data/source/cobb-district-audit.json',source_evidence_sha256=ROSTER_SHA)
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
                   or not re.fullmatch(roster_audit.NATIVE_LEA+r'-\d{4}',r['native_school_id'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['school_id'])
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
        'model_id': f'cobb-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': False, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact Cobb County operational pure lower offered and reconciled enrolled grades with positive grade 3–8 membership; own reported CCD individual direct certification / reported membership and original regular Georgia Milestones EOG All Students G38 Levels 3–4 rates. Accelerated EOG/EOC population treatment remains uncertified.',
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
            'Own reported CCD individual direct certification includes Georgia Medicaid/foster benefit/status scope, and membership may include outside-program prekindergarten. Native regular EOG G38 achievement covers grades 3–8; accelerated EOG/EOC coverage and nonlisted source attribution are uncertified. Original masks and unverified EDC tested counts remain limits.',
        ],
        'intervals': {'available_for_entire_model': False, 'eligible_members': len(inputs),
                      'eligible_members_with_verified_denominators': 0,
                      'valid_score_counts': None, 'sampling_variances': None, 'ten_valid_scored_floor_certified': False,
                      'reason': 'Original EDC tested/level counts are raw evidence with uncertified valid-score scope; no ten-valid-scored floor or intervals can be asserted. Membership/direct certification never substitutes for valid-score counts.'},
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
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Original EDC native G38 rate precision, broader benefits/status direct certification, nonlisted attribution and accelerated EOG/EOC coverage and uncertified valid-score/floor definitions remain limitations; predictions are never clamped.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Interval verification is inapplicable because all verified valid-score denominators are unavailable; Own reported CCD membership and direct certification plus unverified EDC tested/level counts remain linked original evidence, never certified assessment denominators or a scored-count-floor certificate.'},
    }


def build(roster=None):
    roster=load_roster()if roster is None else roster
    require_frozen_roster(roster);models=[];holds=[]
    for subject in SUBJECTS:
        inputs,coverage=selected_inputs(roster,subject)
        try:model=fit_audited_model(inputs,coverage,subject)
        except ValueError as error:
            model=dict(model_id=f'cobb-2025-ES-{subject}',status='numerical_hold',approved_for_source=False,
                approved_for_modeling=False,level='ES',subject=subject,inputs=inputs,coverage=coverage,reason=str(error))
            holds.append(dict(model_id=model['model_id'],reason=str(error)))
        models.append(model)
    population=frozen_population(roster);coverage=roster['coverage']
    return dict(schema_version=1,state='GA',year=2025,academic_year='2024-2025',nces_lea_id=roster_audit.LEA,
        native_lea_id=roster_audit.NATIVE_LEA,native_district_id=roster_audit.NATIVE_DISTRICT,
        scope='numerical_audit_only',status='numerical_hold'if holds else'numerically_verified_pending_integration',
        approved_for_source=False,approved_for_modeling=False,policy=POLICY,numeric_policy_sha256=NUMERIC_POLICY_SHA,runtime_contract_sha256=RUNTIME_CONTRACT_SHA,
        sources=dict(roster_audit=dict(path='data/source/cobb-district-audit.json',sha256=ROSTER_SHA,bytes=ROSTER_BYTES),
            source_audit_code=dict(path='scripts/audit_cobb.py',sha256=SOURCE_CODE_SHA),source_audit_tests=dict(path='tests/test_cobb_audit.py',sha256=SOURCE_TESTS_SHA),
            source_policy_sha256=SOURCE_POLICY_SHA,source_runtime_sha256=SOURCE_RUNTIME_SHA,original_raw_input_sha256=SOURCE_RAW_SHA,original_schema_sha256=SOURCE_SCHEMA_SHA,
            original_definition_evidence_sha256=SOURCE_DEFINITION_SHA,original_identity_projection_sha256=SOURCE_IDENTITY_SHA,native_primary_sources=roster['sources'],secondary_georgia_extract=roster['state_extract']),
        retained_source_reference=dict(path='data/source/cobb-district-audit.json',sha256=ROSTER_SHA,source_scope=roster['scope'],source_status=roster['status'],approved_for_source=False,approved_for_modeling=False,
            retained_original_record_count=coverage['original_records'],retained_original_cell_count=coverage['original_typed_cells'],complete_original_record_count=coverage['complete_original_records'],
            complete_original_cell_count=coverage['complete_original_typed_cells'],omitted_original_records=coverage['omitted_original_records'],
            note='Complete needed original records, schemas, primary definitions and exact omitted-population/identity/row inventories stay in the immutable linked source. Every numerical replay requires the current unchanged complete source/code/tests and literal policy/runtime semantic validation.'),
        count_definition_status=dict(status='unverified_edc_georgia_eog_valid_score_denominators',raw_fields=['StudentGroup_TotalTested','StudentSubGroup_TotalTested','ProficientOrAbove_count','Lev1_count','Lev2_count','Lev3_count','Lev4_count'],
            valid_score_counts=None,sampling_variances=None,sampling_intervals_available=False,ten_valid_scored_floor_certified=False,
            reason='Original EDC tested/level counts may be constructed and remain uncertified valid-score denominators. Own CCD membership/direct certification never substitutes, filters models or certifies a scored-count floor.'),
        frozen_population=population,frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY,population=population)),source_coverage=coverage,
        source_profiles=[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],ncessch=r['ncessch'],name=r['name'],source_roster_link_index=i,
            source_profile_eligible=True,source_attribution_hold=r['source_attribution_hold'],reported_income_pct=r['income']['reported_percentage'],
            raw_published_rates={s:r['subjects'][s]['raw_rate']for s in ['math','reading']},usable_by_subject={s:r['subjects'][s]['usable']for s in SUBJECTS})for i,r in enumerate(roster['roster_links'])if r['source_profile_eligible']],
        retained_scope_exclusions=[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],ncessch=r['ncessch'],name=r['name'],source_roster_link_index=i,exclusion=r['population_exclusion'])for i,r in enumerate(roster['roster_links'])if not r['source_profile_eligible']],
        retained_outside_source_profiles=roster['outside_native_profiles'],
        replay_tolerance=dict(absolute=ABS_TOLERANCE,relative=REL_TOLERANCE,scope='Computed finite floating-point metrics only, strict numeric types. Exact source/x/y/identities/raw token references, subject membership, attribution holds, counts, approvals and absent intervals compare exactly.'),
        models=models,hard_holds=holds)


def numeric_equal(actual, expected):
    if type(expected) is float:
        return type(actual) is float and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(numeric_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(numeric_equal(a, e) for a, e in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def _compare_numerical_documents(document, expected):
    """Typed numerical/source comparison against a verified immutable-source expectation."""
    if not isinstance(document, dict) or roster_audit.fingerprint({k: v for k, v in document.items() if k != 'models'}) != roster_audit.fingerprint({k: v for k, v in expected.items() if k != 'models'}):
        raise ValueError('Cobb County numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('Cobb County numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('Cobb County model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('Cobb County numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('Cobb County independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'sampling_variance', 'low', 'high']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('Cobb County result identities/native outcomes/counts or interval absence changed')
        if not numeric_equal(actual, model):
            raise ValueError('Cobb County numerical metrics failed independent typed/finite replay tolerance')
    return {m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}

def validate(document, expected=None):
    # Every authorization reconstructs the verified expectation from complete
    # current immutable original inputs. A supplied expected object is merely
    # another value to verify, never its own authority; no reassignable model
    # cache or cache digest can bypass the full/deleted fit checks.
    verified=build(load_roster())
    if expected is not None:
        _compare_numerical_documents(expected,verified)
    return _compare_numerical_documents(document,verified)


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

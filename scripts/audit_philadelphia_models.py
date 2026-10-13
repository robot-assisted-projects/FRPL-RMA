"""Replay Philadelphia regular PSSA models and conditional sampling intervals; no import/publication."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

import audit_philadelphia as roster_audit
from prepare_data import fit_model, sampling_variance

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/philadelphia-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = '6f6f1a97304ecb286d4da37401b3281fc446dc55dcd9f46bd3561cf1b9213c56'
ROSTER_BYTES = 7253157
SOURCE_CODE = ROOT / 'scripts/audit_philadelphia.py'
SOURCE_CODE_SHA = 'ee72dea41077d4e90b25f6138eb1a7c1f44e3637a4338078d3e124df2df43905'
SOURCE_TESTS = ROOT / 'tests/test_philadelphia_audit.py'
SOURCE_TESTS_SHA = 'abb5cfb2df9bbc118b30f38927dd9e99cf0f4785b8af98720cf0b31412f57243'
SOURCE_POLICY_SHA = '7b779ea04f44ac12d7819d033c9f80de7d3c537b3e41bf0329010010942214a5'
SOURCE_RAW_SHA = '79a71288dadbad8aa8a6bf963a5e6cde0baf913afa5180e7913405ccdfca0af9'
SOURCE_SCHEMA_SHA = '9c502fcf5f119c5f999810925d9d24ff1b2ec533f8dcdf9e1b1e1d066ce65e61'
SOURCE_DEFINITION_SHA = 'f0305f3ac6ae4165f769b68a232eefdfff3e95636e2e790d860885a4d0ae434a'
SOURCE_IDENTITY_SHA = '82bf875205d35b593807f9bad7f6ce2b9cd6b3695ccefeb2c0f3f123db4b13d5'
SOURCE_STATE_SHA = '73d39c18bfb472ed65fc32ec55b76f65000b66e8cf8b2312708959448b55fe31'
SOURCE_SNAPSHOT_SHA = 'cb16432cd346287c9c03c0cf39644bec7e391038629d3d9958c6857547776483'
MIN_SCHOOLS = 30
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
SUBJECTS = ['math', 'reading', 'combined']
ASSESSMENT = '2024–25 Pennsylvania regular PSSA All Students / Total grades 3–8'
STANDARD = 'Original published Percent Proficient and above; scored accountable regular PSSA population, one-decimal rounding and fewer-than-11 suppression. Keystone and PASA remain separate.'
SUBJECT_FIELDS = {'math': 14, 'reading': 14}
SUBJECT_LABELS = {'math': 'Math', 'reading': 'English Language Arts'}
INCOME_FIELDS = [5, 6, 7]
COUNT_FIELD = 9
MIN_VALID_SCORES = 11
INTERVAL_MULTIPLIER = 1.96
POLICY = {
    **{k: roster_audit.POLICY[k] for k in ['identity', 'population', 'income', 'income_precision', 'assessment', 'assessment_population', 'suppression', 'counts', 'combined', 'discrepancies']},
    'eligibility': 'Reconstruct exact original Philadelphia CCD and Pennsylvania AUN/school identities, operational status, complete pure lower offered flags, positive October grades 3–8 and explicit-zero grades 9–12. Select matching same-year school individual PIMS income and original regular PSSA All Students / Total subject records. Keep all 162 grade profiles; retain high/mixed/primary/inactive/unmatched/native-9999/subgroup/grade rows through the immutable complete source. No name joins, income backfill, diagnostic exclusions or charter-LEA substitutions.',
    'models': 'Separate unweighted centered 2024–25 Philadelphia grade-school Math, ELA and independently fitted paired Combined OLS. Combined is the equally weighted mean of original subject rates with its own residual scale, every deleted fit and external studentization; never average subject studentized residuals. No enrollment weights, shrinkage, fit-driven exclusions or national pooling.',
    'minimum_usable_subject_schools': MIN_SCHOOLS,
    'studentization': 'Externally studentized residuals use every explicit deleted-school fit, N−3 deleted residual degrees of freedom and held-out leverage. Rank-two full/deleted designs and positive finite scales are hard gates. Cook distance and prediction sensitivity over the observed income range are descriptive, never exclusions or prediction clamping.',
    'intervals': 'Every eligible member has original verified subject Number Scored. Jeffreys p=(published_pct/100*n+0.5)/(n+1), v=10000*p*(1−p)/n; Combined uses (sqrt(vMath)+sqrt(vELA))²/4, the maximum positive covariance bound. Propagate every model member through (I−H), holding each deleted regression scale fixed, for externally studentized t±1.96SE approximate conditional intervals. Count, date, population, rounded-rate, binomial and fixed-scale assumptions remain explicit; these are not causal or overall-school-quality intervals.',
    'combined_count_display': 'Combined displays the smaller original Math/ELA Number Scored only as a conservative subject-count display; it is not a paired, deduplicated or joint denominator. Preserve both exact subject counts and references; use both subject variances with the maximum positive covariance bound.',
    'compact_provenance': 'The complete immutable source retains all 22,108 original records / 622,260 typed cells, complete headers, notes, primary definitions and outside identities. Every numerical API/replay, including cached expected fits, requires the current complete blob, source code/tests, source policy/raw/schema/definition/identity and secondary extract pins plus semantic validation. Compact exact input table/worksheet/row/column references avoid duplicating raw tables/PDFs.',
    'release': 'Numerical audit only pending independent review and separate canonical/browser integration. Historical source and numerical source/modeling approvals stay false; verified scored denominators and numerical intervals never grant publication approval.'
}
NUMERIC_POLICY_SHA = '4faea9722801e0eccc0b3b7b5ed887c6eca84a64e479789d6a0b1a2f1135b139'
RUNTIME_CONTRACT_SHA = 'b9800c5de81b7207d04c5627c848a75b546613eb47a9e5d4dc8f738baa6c6aa6'


def runtime_contract():
    return dict(minimum=MIN_SCHOOLS, subjects=SUBJECTS, assessment=ASSESSMENT,
        standard=STANDARD, subject_fields=SUBJECT_FIELDS, subject_labels=SUBJECT_LABELS,
        income_fields=INCOME_FIELDS, count_field=COUNT_FIELD, minimum_valid_scores=MIN_VALID_SCORES,
        interval_multiplier=INTERVAL_MULTIPLIER, absolute_tolerance=ABS_TOLERANCE,
        relative_tolerance=REL_TOLERANCE, verify_tolerance=VERIFY_TOLERANCE,
        frozen_source_pins=dict(blob=ROSTER_SHA, bytes=ROSTER_BYTES, code=SOURCE_CODE_SHA, tests=SOURCE_TESTS_SHA,
            policy=SOURCE_POLICY_SHA, raw=SOURCE_RAW_SHA, schema=SOURCE_SCHEMA_SHA, definitions=SOURCE_DEFINITION_SHA,
            identities=SOURCE_IDENTITY_SHA, state_extract=SOURCE_STATE_SHA, state_snapshot=SOURCE_SNAPSHOT_SHA))


def require_runtime_contract():
    original_policy = '4faea9722801e0eccc0b3b7b5ed887c6eca84a64e479789d6a0b1a2f1135b139'
    original_contract = 'b9800c5de81b7207d04c5627c848a75b546613eb47a9e5d4dc8f738baa6c6aa6'
    if (NUMERIC_POLICY_SHA != original_policy or RUNTIME_CONTRACT_SHA != original_contract
            or roster_audit.fingerprint(POLICY) != original_policy
            or roster_audit.fingerprint(runtime_contract()) != original_contract):
        raise ValueError('Frozen current Philadelphia numerical policy/types/subject/count/interval/source-pin contract changed')


def load_roster(path=ROSTER):
    require_runtime_contract()
    for source, expected, label in [(SOURCE_CODE, SOURCE_CODE_SHA, 'code'), (SOURCE_TESTS, SOURCE_TESTS_SHA, 'tests')]:
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen Philadelphia source ' + label + ' changed; fresh numerical audit required')
    pins = [(roster_audit.fingerprint(roster_audit.POLICY), SOURCE_POLICY_SHA),
            (roster_audit.RAW_INPUT_SHA, SOURCE_RAW_SHA), (roster_audit.ORIGINAL_SCHEMA_SHA, SOURCE_SCHEMA_SHA),
            (roster_audit.DEFINITION_INPUT_SHA, SOURCE_DEFINITION_SHA), (roster_audit.ORIGINAL_IDENTITY_SHA, SOURCE_IDENTITY_SHA),
            (roster_audit.STATE_EXTRACT_SHA, SOURCE_STATE_SHA), (roster_audit.STATE_SNAPSHOT_SHA, SOURCE_SNAPSHOT_SHA)]
    if any(actual != expected for actual, expected in pins):
        raise ValueError('Frozen Philadelphia source policy/raw/schema/definition/identity pins changed')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != ROSTER_SHA or len(data) != ROSTER_BYTES:
        raise ValueError('Frozen complete Philadelphia source artifact changed; fresh numerical audit required')
    document = json.loads(data)
    roster_audit.validate(document)
    return document


def require_frozen_roster(roster):
    if roster_audit.fingerprint(roster) != roster_audit.fingerprint(load_roster()):
        raise ValueError('In-memory Philadelphia source differs from the complete frozen artifact')


def frozen_population(roster):
    links=roster['roster_links'];cohorts=roster['cohorts']
    return dict(complete_native_school_ids=sorted(roster_audit.native_identity(e['raw'],'native_grades') for e in roster['raw_inputs']['native_grades']['records']),
        complete_directory_ncessch=sorted(r['ncessch'] for r in links),
        operational_directory_ncessch=sorted(r['ncessch'] for r in links if r['operational']),
        grade_school_configuration_ids=sorted(cohorts['prospective_tested_grade_profiles']['school_ids']),
        eligible_school_ids_by_subject={s: sorted(cohorts['prospective_tested_grade_profiles']['subjects'][s]['eligible_school_ids']) for s in SUBJECTS},
        high_school_configuration_ids=sorted(cohorts['high_only']['school_ids']),
        mixed_configuration_ids=sorted(cohorts['mixed_grade']['school_ids']),
        primary_configuration_ids=sorted(cohorts['primary_only']['school_ids']),
        nonoperational_directory_ncessch=sorted(e['raw']['NCESSCH'] for e in roster['nonoperational_directory']),
        unmatched_native_school_ids=sorted(r['school_id'] for r in roster['outside_roster_profiles']),
        directory_without_native_profile_ids=sorted(r['school_id'] for r in links if not r['native_profile_matched']))


def original_count(value):
    return roster_audit.count(value)


def original_rate(value):
    return roster_audit.published_percentage(value)


def verified_sampling_variance(pct, n):
    require_runtime_contract()
    if type(n) is not int or n<MIN_VALID_SCORES or type(pct) not in {int,float} or not math.isfinite(pct) or not 0<=pct<=100:
        raise ValueError('Sampling variance requires original finite rate and strict verified scored denominator')
    p=(pct/100*n+.5)/(n+1)
    variance=10000*p*(1-p)/n
    shared=sampling_variance(pct,n)
    if not math.isfinite(variance) or variance<=0 or shared!=variance:
        raise ValueError('Jeffreys sampling variance differs from independently replayed original rate/count')
    return variance


def table_reference(raw,table,entry,columns):
    if entry is None:return None
    section=raw[table]
    return dict(table=table,source_id=section['source_id'],worksheet=section['worksheet'],
        source_row=entry['source_row'],columns=columns,fields=[section['header_rows'][-1][i] for i in columns])


def source_references(roster,link,directory,grade,income,assessments):
    raw=roster['raw_inputs']
    return dict(roster_link_index=next(i for i,r in enumerate(roster['roster_links']) if r['school_id']==link['school_id']),
        directory=dict(table='directory',source_id=raw['directory']['source_id'],member=raw['directory']['member'],
            source_row=directory['source_row'],fields=['SCHOOL_YEAR','LEAID','ST_LEAID','ST_SCHID','NCESSCH','UPDATED_STATUS','G_3_OFFERED','G_9_OFFERED']),
        native_enrollment=table_reference(raw,'native_grades',grade,list(range(6,28))),
        income=table_reference(raw,'native_income',income,INCOME_FIELDS),
        outcomes={s:table_reference(raw,'native_assessment',assessments.get(s),list(range(15))) for s in ['math','reading']})


def selected_inputs(roster,subject):
    """Independently reconstruct exact scope/x/published y/counts from complete originals."""
    if subject not in SUBJECTS:raise ValueError('Only three separate grade-school subjects may be audited')
    require_frozen_roster(roster)
    raw=roster['raw_inputs']
    directory={roster_audit.ccd_identity(e['raw']):e for e in raw['directory']['records']}
    grades={roster_audit.native_identity(e['raw'],'native_grades'):e for e in raw['native_grades']['records']}
    incomes={roster_audit.native_identity(e['raw'],'native_income'):e for e in raw['native_income']['records']}
    assessment=defaultdict(dict)
    for e in raw['native_assessment']['records']:
        r=e['raw']
        if r[7:9]!=['All Students','Total']:continue
        if type(r[0]) is not int or r[0]!=2025 or r[6] not in SUBJECT_LABELS.values():raise ValueError('Wrong same-year regular PSSA Total population')
        key=roster_audit.native_identity(r,'native_assessment')
        s=next(s for s,label in SUBJECT_LABELS.items() if label==r[6])
        if s in assessment[key]:raise ValueError('Duplicate original regular PSSA subject Total')
        assessment[key][s]=e
    inputs=[];exclusions=[];configurations=[]
    required=['math','reading'] if subject=='combined' else [subject]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id'];entry=directory[key];c=entry['raw'];grade=grades.get(key)
        flags={g:c.get('G_'+g+'_OFFERED') for g in roster_audit.GRADES}
        complete=c.get('IGOFFERED')=='As reported' and c.get('NOGRADES')=='No' and all(v in {'Yes','No'} for v in flags.values())
        native=None if grade is None else grade['raw']
        scoped=(c['UPDATED_STATUS'] in roster_audit.OPERATIONAL and complete
            and any(flags[str(g)]=='Yes' for g in range(3,9))
            and not any(flags[g]=='Yes' for g in [str(n) for n in range(9,14)]+['UG','AE'])
            and native is not None and all(original_count(v)==0 for v in native[23:27])
            and any(original_count(v) not in {None,0} for v in native[17:23]))
        if scoped is not link['source_profile_eligible']:raise ValueError('Independent original grade configuration differs from frozen source')
        if not scoped:continue
        configurations.append(key)
        income=incomes.get(key);r=None if income is None else income['raw']
        n=None if r is None else original_count(r[5]);low=None if r is None else original_count(r[6])
        display=None if r is None else roster_audit.percentage(r[7],1)
        usable_income=n not in {None,0} and low is not None and display is not None and low<=n and -.000001<=low/n-display<=.000101
        cells=assessment.get(key,{})
        rates={s:None if s not in cells else original_rate(cells[s]['raw'][SUBJECT_FIELDS[s]]) for s in ['math','reading']}
        raw_rates={s:None if s not in cells else cells[s]['raw'][SUBJECT_FIELDS[s]] for s in ['math','reading']}
        counts={s:None if s not in cells else original_count(cells[s]['raw'][COUNT_FIELD]) for s in ['math','reading']}
        refs=source_references(roster,link,entry,grade,income,cells)
        reasons=[] if usable_income else ['Original same-year school individual PIMS income missing, masked or unreconciled']
        reasons += [s+': original regular PSSA Total missing or masked' for s in required if rates[s] is None]
        for s in required:
            if rates[s] is not None and (counts[s] is None or counts[s]<MIN_VALID_SCORES):
                raise ValueError('Original usable PSSA total lacks its verified Number Scored floor')
        if reasons:
            exclusions.append(dict(school_id=key,native_school_id=c['ST_SCHID'],ncessch=c['NCESSCH'],name=link['name'],reason='; '.join(reasons),raw_published_rates=raw_rates,source_refs=refs));continue
        outcome=(rates['math']+rates['reading'])/2 if subject=='combined' else rates[subject]
        x=100*low/n
        if x!=link['income']['percentage'] or outcome!=link['subjects'][subject]['native_rate'] or any(counts[s]!=link['subjects'][s]['tested'] for s in required):
            raise ValueError('Independent original individual income/published rate/verified count differs from frozen source')
        variances={s:verified_sampling_variance(rates[s],counts[s]) if rates[s] is not None and counts[s] is not None and counts[s]>=MIN_VALID_SCORES else None for s in ['math','reading']}
        variance=(math.sqrt(variances['math'])+math.sqrt(variances['reading']))**2/4 if subject=='combined' else variances[subject]
        display_count=min(counts.values()) if subject=='combined' else counts[subject]
        inputs.append(dict(school_id=key,native_school_id=c['ST_SCHID'],ncessch=c['NCESSCH'],name=link['name'],level='ES',
            charter=c['CHARTER_TEXT'],ccd_school_type=c['SCH_TYPE_TEXT'],income_pct=x,income_year=2025,academic_year='2024-2025',
            income_enrollment=n,individual_economic_count=low,published_income_proportion=display,outcome_pct=outcome,
            outcome_by_subject=rates,raw_published_rates=raw_rates,valid_scores_by_subject=counts,variance_by_subject=variances,
            display_valid_scores=display_count,sampling_variance=variance,ten_valid_scored_floor_certified=True,source_refs=refs))
    cohort=roster['cohorts']['prospective_tested_grade_profiles']
    if configurations!=sorted(cohort['school_ids']) or [r['school_id'] for r in inputs]!=sorted(cohort['subjects'][subject]['eligible_school_ids']):
        raise ValueError('Complete original subject/configuration membership differs from frozen source')
    coverage=dict(grade_school_configuration_profiles=len(configurations),usable_schools=len(inputs),excluded_configuration_profiles=len(exclusions),
        excluded_configuration_records=exclusions,exclusions=dict(sorted(Counter(r['reason'] for r in exclusions).items())),
        charter=dict(sorted(Counter(r['charter'] for r in inputs).items())),school_types=dict(sorted(Counter(r['ccd_school_type'] for r in inputs).items())),
        eligible_members_with_verified_denominators=len(inputs),ten_valid_scored_floor_certified=bool(inputs),model_sampling_intervals_available=bool(inputs),
        source_evidence_path='data/source/philadelphia-district-audit.json',source_evidence_sha256=ROSTER_SHA)
    return inputs,coverage


def verify_independently(x, y, variance, model, results):
    """Centered OLS, all explicit deletions and independent scalar all-member propagation."""
    require_runtime_contract()
    n = len(x)
    if (n < MIN_SCHOOLS or x.shape != y.shape or x.shape != variance.shape or x.ndim != 1
            or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(variance).all() or np.any(variance<=0)):
        raise ValueError('Independent verification requires finite complete percentage vectors')
    def finite_number(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

    if (type(model.get('n')) is not int or model['n'] != n or len(results) != n
            or any(not finite_number(model.get(k)) for k in ['intercept', 'slope', 'r2'])
            or any(not finite_number(r.get(k)) for r in results
                   for k in ['actual', 'predicted', 'residual', 'leverage', 'studentized', 'low', 'high'])
            or any(not 0 <= r['leverage'] < 1 for r in results)):
        raise ValueError('Independent verification requires finite returned coefficients/results and exact model count')
    centered = x - x.mean()
    spread = centered @ centered
    design = np.column_stack([np.ones(n), centered])
    if np.linalg.matrix_rank(design)!=2 or not math.isfinite(spread) or spread<=0:
        raise ValueError('Independent full income design requires rank two')
    h = 1 / n + centered ** 2 / spread
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
    errors = {
        'coefficient': max(abs(float(beta[0] - beta[1] * x.mean()) - model['intercept']),
                           abs(float(beta[1]) - model['slope'])),
        'predicted': max(abs(float(v) - r['predicted']) for v, r in zip(predicted, results)),
        'residual': max(abs(float(v) - r['residual']) for v, r in zip(residual, results)),
        'r2': abs(float(r2) - model['r2']), 'leverage': 0., 'studentized': 0.,
        'deleted_sse_identity': 0., 'held_out_prediction_identity': 0.,
        'interval_endpoint': 0., 'propagated_sampling_variance': 0., 'studentized_sampling_se': 0.,
    }
    deleted = []
    dense_hat=design @ np.linalg.inv(design.T @ design) @ design.T
    dense_propagation=((np.eye(n)-dense_hat)**2) @ variance
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
        # Scalar centered closed-form hat weights independently propagate EVERY
        # member's input variance, including off-diagonal prediction uncertainty.
        weights=[(1. if i==j else 0.)-(1/n+centered[i]*centered[j]/spread) for j in range(n)]
        propagated=math.fsum(float(w*w*variance[j]) for j,w in enumerate(weights))
        standard_error=math.sqrt(propagated)/(scale*math.sqrt(1-h[i]))
        errors['propagated_sampling_variance']=max(errors['propagated_sampling_variance'],abs(propagated-float(dense_propagation[i])))
        returned_se=(results[i]['high']-results[i]['low'])/(2*INTERVAL_MULTIPLIER)
        errors['studentized_sampling_se']=max(errors['studentized_sampling_se'],abs(standard_error-returned_se))
        errors['interval_endpoint']=max(errors['interval_endpoint'],
            abs((external_t-INTERVAL_MULTIPLIER*standard_error)-results[i]['low']),
            abs((external_t+INTERVAL_MULTIPLIER*standard_error)-results[i]['high']))
        deleted.append({'intercept': float(b[0] - b[1] * mean_x), 'slope': float(b[1]),
                        'sse': deleted_sse, 'held_out_prediction': held_out,
                        'held_out_prediction_leverage': float(predictive_h),
                        'residual_scale': scale, 'externally_studentized': float(external_t),
                        'propagated_sampling_variance': propagated, 'studentized_sampling_se': standard_error})
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
                   or not re.fullmatch(r'PA-126515001-\d{1,9}',r['native_school_id'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
                   or not re.fullmatch(r'126515001-\d{9}',r['school_id'])
                   or r['ten_valid_scored_floor_certified'] is not True for r in inputs)):
        raise ValueError('District members require exact same-year native pure grade-school identities and income')
    if any(type(r['display_valid_scores']) is not int or r['display_valid_scores']<MIN_VALID_SCORES
           or any(type(r['valid_scores_by_subject'][s]) is not int or r['valid_scores_by_subject'][s]<MIN_VALID_SCORES for s in (['math','reading'] if subject=='combined' else [subject]))
           or type(r['sampling_variance']) is not float or not math.isfinite(r['sampling_variance']) or r['sampling_variance']<=0 for r in inputs):
        raise ValueError('Every model member requires its original verified valid-score counts and positive Jeffreys variance')


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
    variance=np.array([r['sampling_variance'] for r in inputs],dtype=float)
    model,fitted=fit_model(x-x.mean(),y,variance)
    model['intercept']-=model['slope']*float(x.mean())
    deleted,errors=verify_independently(x,y,variance,model,fitted)


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
            'school_id': school['school_id'], **row, 'valid_scores': school['display_valid_scores'],
            'valid_scores_by_subject': school['valid_scores_by_subject'], 'sampling_variance': school['sampling_variance'],
            'propagated_sampling_variance': deletion['propagated_sampling_variance'],
            'studentized_sampling_standard_error': deletion['studentized_sampling_se'],
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
        'model_id': f'philadelphia-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': True, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact Philadelphia operational pure lower offered grades with positive October grades 3–8 and explicit-zero grades 9–12; own October PIMS individual income and original 2025 regular PSSA All Students / Total published rates and Number Scored',
        'level': 'ES', 'subject': subject, 'assessment': ASSESSMENT,
        'assessment_standard': STANDARD,
        'coverage': coverage, 'inputs': inputs,
        'population_sha256': roster_audit.fingerprint({'policy': POLICY, 'source_audit_sha256': ROSTER_SHA,
                                                      'level': 'ES', 'subject': subject, 'year': 2025,
                                                      'school_ids': [r['school_id'] for r in inputs]}),
        'coefficients': model, 'results': results,
        'review_warnings': [
            'Conditional sampling intervals propagate every member’s verified Number Scored binomial approximation while holding deleted regression scale fixed; they do not measure causal school effects or all sources of uncertainty.',
            'Conventional leverage, Cook distance and residual flags require descriptive review, never automatic exclusions.',
            'Individual October PIMS poverty coverage, local poverty-source choices, enrolled pre-K/kindergarten, accountable assessment exclusions and one-decimal published-rate rounding remain explicit limits; predictions are never clamped.',
            'Combined uses maximum positive subject covariance and displays the smaller original subject count, not a paired or deduplicated denominator.'
        ],
        'intervals': {'available_for_entire_model': True, 'eligible_members': len(inputs),
            'eligible_members_with_verified_denominators': len(inputs), 'ten_valid_scored_floor_certified': True,
            'valid_score_counts': [r['display_valid_scores'] for r in inputs],
            'subject_counts': [r['valid_scores_by_subject'] for r in inputs],
            'sampling_variances': [r['sampling_variance'] for r in inputs],
            'method': POLICY['intervals'], 'combined_count_display': POLICY['combined_count_display'],
            'assumptions': 'Approximate conditional 95% intervals: independent school rate errors, smoothed binomial variances from rounded published rates, fixed income/design and fixed deleted regression scale; all model members contribute. Combined takes the maximum positive Math/ELA covariance bound.'},


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
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Original one-decimal proficiency, October individual PIMS income, accountable PSSA scored scope and approximate conditional sampling assumptions remain limitations; predictions are never clamped.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Independent scalar centered hat weights propagate every member’s verified Jeffreys variance through (I−H); conditional external-t endpoints hold each explicit deleted scale fixed. Combined uses the maximum positive Math/ELA covariance variance bound and preserves both original scored counts; its smaller display count is not a paired denominator.'},
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
            model = dict(model_id=f'philadelphia-2025-ES-{subject}', status='numerical_hold', approved_for_source=False,
                         approved_for_modeling=False, level='ES', subject=subject, inputs=inputs, coverage=coverage, reason=str(error))
            holds.append(dict(model_id=model['model_id'], reason=str(error)))
        models.append(model)
    population = frozen_population(roster)
    return dict(schema_version=1, state='PA', year=2025, academic_year='2024-2025', nces_lea_id=roster_audit.LEA,
        native_lea_id=roster_audit.NATIVE_LEA, native_aun=roster_audit.AUN,
        scope='numerical_audit_only', status='numerical_hold' if holds else 'numerically_verified_pending_integration',
        approved_for_source=False, approved_for_modeling=False, policy=POLICY, numeric_policy_sha256=NUMERIC_POLICY_SHA,
        runtime_contract_sha256=RUNTIME_CONTRACT_SHA,
        sources=dict(roster_audit=dict(path='data/source/philadelphia-district-audit.json', sha256=ROSTER_SHA, bytes=ROSTER_BYTES),
            source_audit_code=dict(path='scripts/audit_philadelphia.py', sha256=SOURCE_CODE_SHA),
            source_audit_tests=dict(path='tests/test_philadelphia_audit.py', sha256=SOURCE_TESTS_SHA),
            source_policy_sha256=SOURCE_POLICY_SHA, original_raw_input_sha256=SOURCE_RAW_SHA, original_schema_sha256=SOURCE_SCHEMA_SHA,
            original_definition_evidence_sha256=SOURCE_DEFINITION_SHA, original_identity_projection_sha256=SOURCE_IDENTITY_SHA,
            native_primary_sources=roster['sources'], secondary_pennsylvania_extract=roster['state_extract']),
        retained_source_reference=dict(path='data/source/philadelphia-district-audit.json', sha256=ROSTER_SHA, source_scope=roster['scope'],
            source_status=roster['status'], approved_for_source=False, approved_for_modeling=False,
            complete_original_record_count=22108, complete_original_cell_count=622260,
            note='Complete original records, headers, notes, definitions, membership and outside identities stay in the immutable linked source artifact; every numerical replay requires current available unchanged source/code/tests/policy and semantic validation.'),
        count_definition_status=dict(status='verified_regular_pssa_all_students_total_number_scored',
            raw_fields=['Number Scored','Percent Proficient and above'],
            usable_original_subject_count_records=324, sampling_intervals_available=not holds, ten_valid_scored_floor_certified=True,
            minimum_original_eligible_subject_count=min(r['valid_scores_by_subject'][s] for m in models for r in m['inputs'] for s in ['math','reading']),
            reason='Every eligible rate has its exact original same-year regular PSSA All Students/Total Number Scored denominator; source floor is 11, observed minimum 42. Combined retains both subject counts and uses the smaller only for display, never a paired denominator.'),


        frozen_population=population, frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY, population=population)),
        source_coverage=roster['coverage'],
        retained_scope_exclusions=[dict(school_id=r['school_id'], native_school_id=r['native_school_id'], ncessch=r['ncessch'],
            name=r['name'], source_roster_link_index=i, exclusion=r['population_exclusion'])
            for i, r in enumerate(roster['roster_links']) if not r['source_profile_eligible']],
        retained_outside_source_profiles=[dict(school_id=r['school_id'], ncessch=None, grade_source_row=r['grade_source_row'],
            exclusion=r['exclusion']) for r in roster['outside_roster_profiles']],
        replay_tolerance=dict(absolute=ABS_TOLERANCE, relative=REL_TOLERANCE,
            scope='Computed finite floating-point metrics only, strict numeric types. Source fingerprints/references, exact identity/x/y/raw income/rates, subject membership, verified original counts and approvals compare exactly; computed variance propagation, endpoints and diagnostics use finite strict numerical replay.'),
        models=models, hard_holds=holds)


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
        raise ValueError('Philadelphia numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('Philadelphia numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('Philadelphia model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('Philadelphia numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('Philadelphia independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'valid_scores_by_subject', 'sampling_variance']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('Philadelphia result identities/native outcomes/counts or source variance changed')
        if not numeric_equal(actual, model):
            raise ValueError('Philadelphia numerical metrics failed independent typed/finite replay tolerance')
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

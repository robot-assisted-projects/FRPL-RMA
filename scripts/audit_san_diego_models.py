"""Replay San Diego Unified regular Smarter Balanced models and conditional intervals; no import or publication."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import types
import numpy as np
import audit_san_diego as roster_audit
from prepare_data import fit_model, sampling_variance
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/san-diego-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = '97ab750a3b09e86c487d64a34b947b6b7efffb31d749e6a03a77eae8c44b65f2'
ROSTER_BYTES = 17821289
SOURCE_CODE = ROOT / 'scripts/audit_san_diego.py'
SOURCE_CODE_SHA = '568677688041da576a36c491ce3fb452c713aae968eba447fa598e1578fa186d'
SOURCE_TESTS = ROOT / 'tests/test_san_diego_audit.py'
SOURCE_TESTS_SHA = '6207162d17f8e60301365877f65611e1e8a2b65a32ec9f02b798ecf008860541'
SOURCE_POLICY_SHA = 'ca6b2681810ce6f80cf79092b61c325a8abb0209f33a6ce5b9b42440c8ccfb53'
SOURCE_RAW_SHA = '5db2e5058ea6243eb5843cf7f5e8d55b583551576938b7a95b3ea77331f9ad3e'
SOURCE_SCHEMA_SHA = '0720d1f22dde683426ffe2b766b3bf48400c816c558a6cd75c5d9fadc6070619'
SOURCE_DEFINITION_SHA = '8617ecb470fb3e7e5b288a1a504e1d86af060333d02ef373ff37deb48fcb9696'
SOURCE_IDENTITY_SHA = '488a7bc2a9ec19670e87bc6e1071813471b22cd8146e41786ab20024d3f96bd2'
SOURCE_RUNTIME_SHA = '2b725ef1988e3944d25a5c905be3d8808cf8f6ca494e3de5972c60ffec8807c6'
MIN_SCHOOLS = 30
MIN_VALID_SCORES = 11
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
INTERVAL_MULTIPLIER = 1.96
SUBJECTS = ['math', 'reading', 'combined']
SUBJECT_VALUES = {'math':'2', 'reading':'1'}
ASSESSMENT_SELECTOR = {'Test Year':'2025', 'Test Type':'B', 'Student Group ID':'1'}
ASSESSMENT = '2024–25 California regular Smarter Balanced All Students grades 3–8'
STANDARD = 'Regular Smarter Balanced B Math and ELA, Standard Met or Exceeded; complete expected native grades 3–8 aggregate reconciled valid-performance-score counts. All-grades 13 includes grades 3–8 and 11 and never recovers absent or suppressed components; CAA remains separate.'
INCOME_FIELDS = ['Academic Year','County Code','District Code','School Code','Low Grade','High Grade','School Type','Charter School (Y/N)','California Longitudinal Pupil Achievement Data System (CALPADS) Fall 1 Certification Status','Enrollment (K-12)','FRPM Count (K-12)','Percent (%) Eligible FRPM (K-12)']
COUNT_FIELDS = ['Overall Total','Total Students Tested with Scores','Total Students Tested','Count Standard Met and Above','Count Standard Exceeded','Count Standard Met','Count Standard Nearly Met','Count Standard Not Met','Percentage Standard Met and Above']
POLICY = {
    **{k:roster_audit.POLICY[k] for k in ['identity','year','income','assessment','counts','scope','charters','programs','combined']},
    'eligibility':'Reconstruct exact operational same-year NCES/CDS identities, agreeing CCD/native lower configurations, complete expected native grades 3–8 and verified score-count aggregation, plus own individually eligible CALPADS Census Day K–12 FRPM/enrollment. Retain all 143 lower profiles; Porter and Nipaquay remain unavailable without missing component recovery, Fletcher retains own native income despite missing CCD enrollment, and John Muir remains outside the conflicting grade scope. Reporting-prefix charter and NPS records do not join.',
    'models':'Separate unweighted centered San Diego Unified 2025 grade-school Math, ELA and independently fitted paired Combined OLS. Combined is the equal mean of verified subject rates with its own residual scale, explicit deleted fits and external studentization. No enrollment weights, shrinkage, clipping, diagnostic exclusions, grade percentage averaging or national pooling.',
    'minimum_usable_subject_schools':MIN_SCHOOLS,
    'studentization':'All explicit leave-one-out fits require rank two and positive finite residual scales. Externally studentized residuals use N−3 deleted residual degrees of freedom and held-out prediction leverage. Cook distance, leverage and prediction sensitivity are descriptive only; preserve income extremes and every influential member.',
    'intervals':'Every eligible subject has verified valid-performance-score counts from complete expected grades. Jeffreys p=(rate/100*n+0.5)/(n+1), v=10000*p*(1−p)/n. Combined uses (sqrt(vMath)+sqrt(vELA))²/4, the maximum positive covariance bound. Propagate every model member through (I−H), holding each deleted regression scale fixed, for approximate conditional external-t ±1.96SE intervals. These assume fixed income/design, independent school rate errors and approximate binomial variability; they do not represent all uncertainty or causal effects.',
    'combined_count_display':'Combined displays the smaller verified native Math/ELA valid-score count only; it is not a paired, deduplicated or joint denominator. Preserve both subject counts and use both subject variances with maximum positive covariance.',
    'compact_provenance':'The full immutable source retains 3,789 needed original records / 169,260 typed cells, all headers/primary definitions and exact inventories for 18,189 omitted rows. Numerical artifacts link that complete evidence once with exact table/member/worksheet/row/field pointers. Every current, cached or supplied-expected authorization verifies full source/code/tests/original files and literal raw/schema/definition/identity/policy/runtime contracts, then independently rebuilds inputs and fits. Caller expectations or reassignable caches cannot authorize themselves.',
    'release':'Numerical audit only pending independent review and separate normalized/canonical/browser integration. Both historical source and numerical approvals remain false; verified counts and intervals do not grant publication approval.'
}
NUMERIC_POLICY_SHA = '4e3d2efb762a868000a76fdd17972b9372483f21f33fd5d7003e66041f1f4039'
RUNTIME_CONTRACT_SHA = 'fab55e9d2b13154ab04ba3c6e1e05974a4552182cf6e21a315e5e727520acb97'


def semantic_sources():
    names=['table_reference','source_references','numeric_equal','_compare_numerical_documents','original_count','aggregate_subject','_sampling_variance_verified','_selected_inputs_verified','_fit_audited_model_verified','verify_independently','frozen_population','_build_verified']
    text=Path(__file__).read_text();tree=ast.parse(text)
    nodes={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names}
    if set(nodes)!=set(names):raise ValueError('Complete San Diego numerical semantic declarations required')
    return {name:ast.get_source_segment(text,nodes[name]) for name in names}


def runtime_contract():
    return dict(minimum=MIN_SCHOOLS,minimum_valid=MIN_VALID_SCORES,subjects=SUBJECTS,subject_values=SUBJECT_VALUES,
        assessment_selector=ASSESSMENT_SELECTOR,assessment=ASSESSMENT,standard=STANDARD,income_fields=INCOME_FIELDS,
        count_fields=COUNT_FIELDS,interval_multiplier=INTERVAL_MULTIPLIER,absolute_tolerance=ABS_TOLERANCE,
        relative_tolerance=REL_TOLERANCE,verify_tolerance=VERIFY_TOLERANCE,semantic_sources=semantic_sources(),
        frozen_source=dict(path=str(ROSTER.relative_to(ROOT)),sha256=ROSTER_SHA,bytes=ROSTER_BYTES,
            code_path=str(SOURCE_CODE.relative_to(ROOT)),code=SOURCE_CODE_SHA,tests_path=str(SOURCE_TESTS.relative_to(ROOT)),tests=SOURCE_TESTS_SHA,
            policy=SOURCE_POLICY_SHA,raw=SOURCE_RAW_SHA,schema=SOURCE_SCHEMA_SHA,definitions=SOURCE_DEFINITION_SHA,identity=SOURCE_IDENTITY_SHA,runtime=SOURCE_RUNTIME_SHA))


def require_runtime_contract():
    original_policy='4e3d2efb762a868000a76fdd17972b9372483f21f33fd5d7003e66041f1f4039';original_runtime='fab55e9d2b13154ab04ba3c6e1e05974a4552182cf6e21a315e5e727520acb97'
    if NUMERIC_POLICY_SHA!=original_policy or RUNTIME_CONTRACT_SHA!=original_runtime or roster_audit.fingerprint(POLICY)!=original_policy or roster_audit.fingerprint(runtime_contract())!=original_runtime:
        raise ValueError('Frozen San Diego numerical literal policy/types/fields/source/semantic contract changed')
    compiled=compile(Path(__file__).read_text(),str(__file__),'exec',dont_inherit=True)
    reference={c.co_name:c for c in compiled.co_consts if isinstance(c,types.CodeType)}
    for name in semantic_sources():
        actual=globals()[name]
        if not isinstance(actual,types.FunctionType) or roster_audit.code_contract(actual.__code__)!=roster_audit.code_contract(reference[name]):
            raise ValueError('Current San Diego numerical function changed: '+name)
    roster_audit.require_runtime_contract()


def load_roster(path=ROSTER):
    require_runtime_contract()
    for source,expected in [(SOURCE_CODE,SOURCE_CODE_SHA),(SOURCE_TESTS,SOURCE_TESTS_SHA)]:
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('Frozen San Diego source code/tests changed')
    pins=[(roster_audit.fingerprint(roster_audit.POLICY),SOURCE_POLICY_SHA),(roster_audit.RAW_INPUT_SHA,SOURCE_RAW_SHA),
        (roster_audit.ORIGINAL_SCHEMA_SHA,SOURCE_SCHEMA_SHA),(roster_audit.DEFINITION_INPUT_SHA,SOURCE_DEFINITION_SHA),
        (roster_audit.ORIGINAL_IDENTITY_SHA,SOURCE_IDENTITY_SHA),(roster_audit.RUNTIME_CONTRACT_SHA,SOURCE_RUNTIME_SHA)]
    if any(a!=e for a,e in pins):raise ValueError('Frozen current San Diego source fingerprints changed')
    content=Path(path).read_bytes()
    if len(content)!=ROSTER_BYTES or hashlib.sha256(content).hexdigest()!=ROSTER_SHA:raise ValueError('Complete San Diego source blob changed or disappeared')
    roster=json.loads(content);roster_audit.validate(roster);return roster


def require_frozen_roster(roster):
    verified=load_roster()
    if roster_audit.fingerprint(roster)!=roster_audit.fingerprint(verified):raise ValueError('Supplied source differs from immutable complete San Diego artifact')
    return verified


def frozen_population(roster):
    links=roster['roster_links'];cohort=roster['prospective_cohorts']['pure_grade_schools']
    return dict(complete_directory_ncessch=sorted(r['school_id'] for r in links),
        operational_directory_ncessch=sorted(r['school_id'] for r in links if r['operational']),
        complete_native_school_ids=sorted(roster_audit.cds(e['raw']) for e in roster['raw_inputs']['frpm']['records']),
        grade_school_configuration_ids=sorted(cohort['nces_school_ids']),
        eligible_school_ids_by_subject={s:sorted(cohort['subjects'][s]['prospective_nces_school_ids']) for s in SUBJECTS},
        high_school_configuration_ids=sorted(r['school_id'] for r in links if r.get('grade_evidence',{}).get('native_scope')=='HS'),
        mixed_configuration_ids=sorted(r['school_id'] for r in links if r.get('grade_evidence',{}).get('native_scope')=='mixed'),
        substantive_grade_scope_hold_ids=roster['coverage']['substantive_grade_scope_holds'],
        outside_reporting_prefix_native_ids=sorted(r['native_school_id'] for r in roster['outside_roster_native_profiles']))


def original_count(value):
    if value is None or value in ('','*','N/A'):return None
    if type(value)is not str or not re.fullmatch(r'\d+',value):raise ValueError('Exact original nonnegative integer count string required')
    return int(value)


def aggregate_subject(records,expected,income_usable):
    by_grade={int(e['raw']['Grade']):e for e in records}
    if len(by_grade)!=len(records):raise ValueError('Duplicate original subject grade')
    reason=None if expected else 'No applicable tested grade in this level'
    if expected and not set(expected)<=set(by_grade):reason='Missing an expected original tested grade'
    counts=[];met_counts=[]
    if reason is None:
        for grade in expected:
            row=by_grade[grade]['raw'];values={k:original_count(row[k]) for k in COUNT_FIELDS if k!='Percentage Standard Met and Above'}
            rate=row['Percentage Standard Met and Above']
            if any(v is None for v in values.values()) or rate in ('','*'):
                reason='Missing or suppressed original valid-score/count/rate cell';break
            n=values['Overall Total'];met=values['Count Standard Met and Above']
            if n<MIN_VALID_SCORES:reason='Fewer than11 valid performance scores';break
            levels=[values[k] for k in ['Count Standard Exceeded','Count Standard Met','Count Standard Nearly Met','Count Standard Not Met']]
            pct=float(rate)
            if not math.isfinite(pct) or not 0<=pct<=100 or n!=values['Total Students Tested with Scores'] or values['Total Students Tested']<n or met>n or sum(levels)!=n or sum(levels[:2])!=met or abs(pct-100*met/n)>.0051:
                raise ValueError('Original expected grade valid-score/level/rate reconciliation failed')
            counts.append(n);met_counts.append(met)
    if reason is None and not income_usable:reason='Same-year native individual income unavailable'
    n=sum(counts) if reason is None else None;met=sum(met_counts) if reason is None else None
    return dict(proficiency=None if reason else 100*met/n,valid_scores=n,proficient_count=met,exclusion=reason,expected_grades=expected)


def table_reference(raw,table,entry,fields):
    if entry is None:return None
    section=raw[table];namespace='worksheet' if 'worksheet' in section else 'member'
    return dict(table=table,source_id=section['source_id'],**{namespace:section[namespace]},source_row=entry['source_row'],fields=fields,columns=[section['header'].index(f) for f in fields])


def source_references(roster,link,directory,frpm,totals,grades,assessments,expected):
    raw=roster['raw_inputs'];identity=['SCHOOL_YEAR','LEAID','ST_LEAID','NCESSCH','ST_SCHID'];fields=identity+['GRADE','TOTAL_INDICATOR','DMS_FLAG','STUDENT_COUNT']
    assessment_fields=list(ASSESSMENT_SELECTOR)+['County Code','District Code','School Code','Type ID','Test ID','Grade']+COUNT_FIELDS
    return dict(roster_link_index=next(i for i,r in enumerate(roster['roster_links']) if r['school_id']==link['school_id']),
        directory=table_reference(raw,'directory',directory,identity+['UPDATED_STATUS','IGOFFERED','NOGRADES','GSLO','GSHI','CHARTER_TEXT']+['G_'+g+'_OFFERED' for g in roster_audit.GRADES]),
        membership=table_reference(raw,'membership',totals,fields),
        enrolled_grades=dict(table='membership',source_id=raw['membership']['source_id'],member=raw['membership']['member'],source_rows={g:e['source_row'] for g,e in sorted(grades.items())},fields=fields,columns=[raw['membership']['header'].index(f) for f in fields]),
        income=table_reference(raw,'frpm',frpm,INCOME_FIELDS),
        outcomes={s:dict(table='assessment',source_id=raw['assessment']['source_id'],member=raw['assessment']['member'],expected_grades=expected,
            expected_grade_source_rows={str(int(e['raw']['Grade'])):e['source_row'] for e in assessments[s] if int(e['raw']['Grade']) in expected},
            all_original_subject_source_rows=[e['source_row'] for e in assessments[s]],
            grade13_source_row=next((e['source_row'] for e in assessments[s] if e['raw']['Grade']=='13'),None),
            fields=assessment_fields,columns=[raw['assessment']['header'].index(f) for f in assessment_fields]) for s in ['math','reading']})


def _selected_inputs_verified(roster,subject):
    raw=roster['raw_inputs'];directory={e['raw']['NCESSCH']:e for e in raw['directory']['records']}
    native={roster_audit.cds(e['raw']):e for e in raw['frpm']['records']};totals={};grades=defaultdict(dict);outcomes=defaultdict(lambda:defaultdict(list))
    for e in raw['membership']['records']:
        r=e['raw'];key=r['NCESSCH']
        if r['TOTAL_INDICATOR']=='Education Unit Total':totals[key]=e
        else:grades[key][r['GRADE']]=e
    for e in raw['assessment']['records']:
        r=e['raw']
        if any(r[k]!=v for k,v in ASSESSMENT_SELECTOR.items()):raise ValueError('Original regular All Students year changed')
        s=next(s for s,v in SUBJECT_VALUES.items() if r['Test ID']==v);outcomes[roster_audit.cds(r)][s].append(e)
    inputs=[];exclusions=[];configurations=[];required=['math','reading'] if subject=='combined' else [subject]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id'];d=directory[key];c=d['raw'];native_id=roster_audit.ccd_identity(c)[1];profile=native.get(native_id)
        offered=roster_audit.offered_evidence(c,profile['raw']) if profile else None
        high=[e['raw'] for g,e in grades[key].items() if g in ['Grade '+str(n) for n in range(9,13)]]
        high_unknown=any(roster_audit.ccd_count(r)is None for r in high);high_positive=any((roster_audit.ccd_count(r) or 0)>0 for r in high)
        scoped=c['UPDATED_STATUS'] in roster_audit.OPERATIONAL and profile is not None and offered['pure_lower_candidate'] and not high_unknown and not high_positive
        if scoped is not link['prospective_lower_profile']:raise ValueError('Independent native/CCD lower configuration differs')
        if not scoped:continue
        configurations.append(key);income=roster_audit.income_evidence(profile);expected=offered['expected_tested_grades']
        subjects={s:aggregate_subject(outcomes[native_id][s],expected,income['exclusion'] is None) for s in ['math','reading']}
        rates={s:v['proficiency'] for s,v in subjects.items()};counts={s:v['valid_scores'] for s,v in subjects.items()}
        refs=source_references(roster,link,d,profile,totals.get(key),grades[key],outcomes[native_id],expected)
        reasons=[s+': '+subjects[s]['exclusion'] for s in required if subjects[s]['exclusion']]
        expected_usable=all(link['subjects']['ES'][s]['source_usable'] for s in required)
        if (not reasons) is not expected_usable:raise ValueError('Original subject missing-component membership differs')
        if reasons:
            exclusions.append(dict(school_id=key,native_school_id=native_id,ncessch=key,name=link['name'],reason='; '.join(reasons),source_refs=refs));continue
        outcome=(rates['math']+rates['reading'])/2 if subject=='combined' else rates[subject]
        if income['percentage']!=link['income']['percentage'] or outcome!=link['subjects']['ES'][subject]['proficiency'] or any(counts[s]!=link['subjects']['ES'][s]['valid_scores'] for s in required):raise ValueError('Independent original count-weighted proficiency/income differs')
        variances={s:_sampling_variance_verified(rates[s],counts[s]) if rates[s] is not None else None for s in ['math','reading']}
        variance=(math.sqrt(variances['math'])+math.sqrt(variances['reading']))**2/4 if subject=='combined' else variances[subject]
        inputs.append(dict(school_id=key,native_school_id=native_id,ncessch=key,name=link['name'],level='ES',charter=c['CHARTER_TEXT'],ccd_school_type=c['SCH_TYPE_TEXT'],
            income_pct=income['percentage'],income_year=2025,academic_year='2024-2025',income_enrollment=income['enrollment'],individual_FRPM_count=income['eligible'],published_income_fraction=income['published_fraction'],
            outcome_pct=outcome,outcome_by_subject=rates,proficient_counts_by_subject={s:v['proficient_count'] for s,v in subjects.items()},valid_scores_by_subject=counts,
            display_valid_scores=min(counts.values()) if subject=='combined' else counts[subject],variance_by_subject=variances,sampling_variance=variance,ten_valid_scored_floor_certified=True,source_refs=refs))
    cohort=roster['prospective_cohorts']['pure_grade_schools']
    if configurations!=sorted(cohort['nces_school_ids']) or [r['school_id'] for r in inputs]!=sorted(cohort['subjects'][subject]['prospective_nces_school_ids']):raise ValueError('Complete original eligible membership changed')
    return inputs,dict(grade_school_configuration_profiles=len(configurations),usable_schools=len(inputs),excluded_configuration_profiles=len(exclusions),excluded_configuration_records=exclusions,
        exclusions=dict(sorted(Counter(r['reason'] for r in exclusions).items())),charter=dict(sorted(Counter(r['charter'] for r in inputs).items())),school_types=dict(sorted(Counter(r['ccd_school_type'] for r in inputs).items())),
        eligible_members_with_verified_denominators=len(inputs),ten_valid_scored_floor_certified=True,model_sampling_intervals_available=True,source_evidence_path='data/source/san-diego-district-audit.json',source_evidence_sha256=ROSTER_SHA)


def selected_inputs(roster,subject):
    if subject not in SUBJECTS:raise ValueError('Unsupported separate grade-school subject')
    return _selected_inputs_verified(require_frozen_roster(roster),subject)


def _sampling_variance_verified(pct, n):
    if type(n) is not int or n<MIN_VALID_SCORES or type(pct) not in {int,float} or not math.isfinite(pct) or not 0<=pct<=100:
        raise ValueError('Sampling variance requires original finite rate and strict verified scored denominator')
    p=(pct/100*n+.5)/(n+1)
    variance=10000*p*(1-p)/n
    shared=sampling_variance(pct,n)
    if not math.isfinite(variance) or variance<=0 or shared!=variance:
        raise ValueError('Jeffreys sampling variance differs from independently replayed original rate/count')
    return variance

def verified_sampling_variance(pct,n):
    require_runtime_contract()
    return _sampling_variance_verified(pct,n)


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

def _fit_audited_model_verified(inputs, coverage, subject):
    if subject not in SUBJECTS:
        raise ValueError('Only three proposed grade-school subjects may be audited')
    if not isinstance(inputs, list) or any(not isinstance(r, dict) for r in inputs):
        raise ValueError('District inputs require original frozen native records')
    if len(inputs) < MIN_SCHOOLS:
        raise ValueError('District subject model requires at least 30 usable schools')
    if (len({r['school_id'] for r in inputs}) != len(inputs)
            or len({r['native_school_id'] for r in inputs}) != len(inputs)
            or any(r['level']!='ES' or type(r['income_year']) is not int or r['income_year']!=2025
                   or r['academic_year']!='2024-2025'
                   or not re.fullmatch(r'3768338\d{7}',r['native_school_id'])
                   or r['school_id']!=r['ncessch']
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
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
        'model_id': f'san-diego-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': True, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact San Diego Unified operational agreeing CCD/native lower profiles; own CALPADS Census Day K–12 individual FRPM ratio and regular 2025 Smarter Balanced complete expected-grade valid-score aggregation',
        'level': 'ES', 'subject': subject, 'assessment': ASSESSMENT,
        'assessment_standard': STANDARD,
        'coverage': coverage, 'inputs': inputs,
        'population_sha256': roster_audit.fingerprint({'policy': POLICY, 'source_audit_sha256': ROSTER_SHA,
                                                      'level': 'ES', 'subject': subject, 'year': 2025,
                                                      'school_ids': [r['school_id'] for r in inputs]}),
        'coefficients': model, 'results': results,
        'review_warnings': [
            'Conditional sampling intervals propagate every member’s verified valid-performance-score denominator binomial approximation while holding deleted regression scale fixed; they do not measure causal school effects or all sources of uncertainty.',
            'Conventional leverage, Cook distance and residual flags require descriptive review, never automatic exclusions.',
            'Census Day individual FRPM eligibility, K–12 enrollment, exact roster/grade agreement, complete expected-grade coverage and the difference between score and enrollment populations remain explicit limits; predictions are never clamped.',
            'Combined uses maximum positive subject covariance and displays the smaller original subject count, not a paired or deduplicated denominator.'
        ],
        'intervals': {'available_for_entire_model': True, 'eligible_members': len(inputs),
            'eligible_members_with_verified_denominators': len(inputs), 'ten_valid_scored_floor_certified': True,
            'valid_score_counts': [r['display_valid_scores'] for r in inputs],
            'subject_counts': [r['valid_scores_by_subject'] for r in inputs],
            'sampling_variances': [r['sampling_variance'] for r in inputs],
            'method': POLICY['intervals'], 'combined_count_display': POLICY['combined_count_display'],
            'assumptions': 'Approximate conditional 95% intervals: independent school rate errors, smoothed binomial variances from verified native grade-count aggregate rates, fixed income/design and fixed deleted regression scale; all model members contribute. Combined takes the maximum positive Math/ELA covariance bound.'},


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
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Original score-count aggregation, CALPADS Census Day individual FRPM income, regular Smarter Balanced scored scope and approximate conditional sampling assumptions remain limitations; predictions are never clamped.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Independent scalar centered hat weights propagate every member’s verified Jeffreys variance through (I−H); conditional external-t endpoints hold each explicit deleted scale fixed. Combined uses the maximum positive Math/ELA covariance variance bound and preserves both original scored counts; its smaller display count is not a paired denominator.'},
    }


def fit_audited_model(inputs,coverage,subject):
    if subject not in SUBJECTS:raise ValueError('Unsupported separate grade-school subject')
    frozen_inputs,frozen_coverage=_selected_inputs_verified(load_roster(),subject)
    if roster_audit.fingerprint(inputs)!=roster_audit.fingerprint(frozen_inputs) or roster_audit.fingerprint(coverage)!=roster_audit.fingerprint(frozen_coverage):raise ValueError('Caller input/coverage cannot authorize altered native evidence or membership')
    return _fit_audited_model_verified(inputs,coverage,subject)


def _build_verified(roster):
    models=[];holds=[]
    for subject in SUBJECTS:
        inputs,coverage=_selected_inputs_verified(roster,subject)
        try:model=_fit_audited_model_verified(inputs,coverage,subject)
        except ValueError as error:
            model=dict(model_id=f'san-diego-2025-ES-{subject}',status='numerical_hold',approved_for_source=False,approved_for_modeling=False,level='ES',subject=subject,inputs=inputs,coverage=coverage,reason=str(error));holds.append(dict(model_id=model['model_id'],reason=str(error)))
        models.append(model)
    population=frozen_population(roster)
    return dict(schema_version=1,state='CA',year=2025,academic_year='2024-2025',nces_lea_id=roster_audit.LEA,native_lea_id=roster_audit.NATIVE_LEA,native_district_id=roster_audit.CDS_DISTRICT,
        scope='numerical_audit_only',status='numerical_hold' if holds else 'numerically_verified_pending_integration',approved_for_source=False,approved_for_modeling=False,
        policy=POLICY,numeric_policy_sha256=NUMERIC_POLICY_SHA,runtime_contract_sha256=RUNTIME_CONTRACT_SHA,
        sources=dict(roster_audit=dict(path='data/source/san-diego-district-audit.json',sha256=ROSTER_SHA,bytes=ROSTER_BYTES),source_audit_code=dict(path='scripts/audit_san_diego.py',sha256=SOURCE_CODE_SHA),source_audit_tests=dict(path='tests/test_san_diego_audit.py',sha256=SOURCE_TESTS_SHA),source_policy_sha256=SOURCE_POLICY_SHA,source_runtime_sha256=SOURCE_RUNTIME_SHA,
            original_raw_input_sha256=SOURCE_RAW_SHA,original_schema_sha256=SOURCE_SCHEMA_SHA,original_definition_evidence_sha256=SOURCE_DEFINITION_SHA,original_identity_projection_sha256=SOURCE_IDENTITY_SHA,native_primary_sources=roster['sources']),
        retained_source_reference=dict(path='data/source/san-diego-district-audit.json',sha256=ROSTER_SHA,source_scope=roster['scope'],source_status=roster['status'],approved_for_source=False,approved_for_modeling=False,needed_original_record_count=3789,needed_original_cell_count=169260,exact_omitted_original_record_count=18189,note='Complete original typed records, headers, primary definitions, omitted inventories and outside identities remain in the immutable linked source artifact, required freshly on every numerical replay.'),
        count_definition_status=dict(status='verified_complete_expected_grade_valid_performance_scores',raw_fields=COUNT_FIELDS,eligible_subjects_with_verified_counts=282,sampling_intervals_available=not holds,ten_valid_scored_floor_certified=True,minimum_eligible_aggregated_subject_count=min(r['valid_scores_by_subject'][s] for m in models for r in m['inputs'] for s in ['math','reading']),reason='Each expected grade separately requires11 valid performance scores and reconciled four-level/top-two counts. Combined retains both original subject counts; its smaller display is not a paired denominator.'),
        frozen_population=population,frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY,population=population)),source_coverage=roster['coverage'],
        retained_scope_exclusions=[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],name=r['name'],source_roster_link_index=i,exclusion=r['exclusion']) for i,r in enumerate(roster['roster_links']) if not r.get('prospective_lower_profile')],
        retained_outside_source_profiles=[dict(native_school_id=r['native_school_id'],ncessch=None,profile_source_row=r['profile']['source_row'],exclusion=r['exclusion']) for r in roster['outside_roster_native_profiles']],
        replay_tolerance=dict(absolute=ABS_TOLERANCE,relative=REL_TOLERANCE,scope='Computed finite floating-point metrics only with strict types. Exact identities, raw references, input rates/income, subject membership, verified counts and approvals compare exactly; computed variances/endpoints/diagnostics use finite strict numerical replay.'),models=models,hard_holds=holds)


def build(roster=None):
    verified=load_roster() if roster is None else require_frozen_roster(roster)
    return _build_verified(verified)


def numeric_equal(actual, expected):
    if type(expected) is float:
        return type(actual) is float and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(numeric_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(numeric_equal(a, e) for a, e in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected

def _compare_numerical_documents(document, expected):
    if not isinstance(document, dict) or roster_audit.fingerprint({k: v for k, v in document.items() if k != 'models'}) != roster_audit.fingerprint({k: v for k, v in expected.items() if k != 'models'}):
        raise ValueError('San Diego Unified numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('San Diego Unified numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('San Diego Unified model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('San Diego Unified numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('San Diego Unified independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'valid_scores_by_subject', 'sampling_variance']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('San Diego Unified result identities/native outcomes/counts or source variance changed')
        if not numeric_equal(actual, model):
            raise ValueError('San Diego Unified numerical metrics failed independent typed/finite replay tolerance')
    return {m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}

def validate(document,expected=None):
    # A supplied expectation is another value to verify, never its own authority.
    verified=_build_verified(load_roster())
    if expected is not None:_compare_numerical_documents(expected,verified)
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


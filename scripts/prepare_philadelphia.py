"""Canonical/static Philadelphia regular PSSA comparison linked to immutable audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path

import audit_philadelphia as roster_audit
import audit_philadelphia_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot

DATASET = 'pa-philadelphia-2025'
EXTRACT = ROOT / 'data/source/philadelphia.json'
OUTPUT = ROOT / 'data/philadelphia'
NUMERICAL_SHA = '9ede3ce013d27e1947e698d9e8d1793cbec977f5e6f82822ccf197c1d8d5949d'
NUMERICAL_BYTES = 1707603
NUMERICAL_POLICY_SHA = '4faea9722801e0eccc0b3b7b5ed887c6eca84a64e479789d6a0b1a2f1135b139'
NUMERICAL_CODE_SHA = '9c8136f7e297531ba92338b9cf84bb085ecbd9e0816c44fcce314fa9c18cf691'
NUMERICAL_TESTS_SHA = 'a512a456018ba22c50b9ec51d06bc3fd2e01a45b80ba2e0e136c6ce89af2f54d'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':162, 'reading':162, 'combined':162}
ASSESSMENT = 'PSSA school totals · grades 3–8'
STANDARD = model_audit.STANDARD
MODEL_SCOPE = (
    'Philadelphia independent 2024–25 grade-school district models use exact NCES LEA 4218990 / PA-126515001 / '
    'native AUN 126515001 identities. All 162 audited pure lower profiles with positive October grades 3–8 and '
    'explicit-zero grades 9–12 remain searchable and enter separate fixed Math, ELA and independently fitted '
    'Combined models. Original regular PSSA All Students / Total published proficiency and Number Scored are '
    'matched to each school’s own October individual PIMS low-income ratio. Conditional sampling intervals '
    'propagate every model member’s scored-count variance while holding deleted regression scale fixed. '
    'Combined uses the maximum positive Math/ELA covariance bound and displays the smaller subject count; '
    'this display is not a paired or deduplicated denominator. High, mixed, primary, inactive and unmatched '
    'records remain outside the release; Keystone and PASA remain separate.')
COUNT_NOTE = (
    'Number Scored is the original same-year regular PSSA All Students / Total valid-score denominator. '
    'Published usable rates require at least 11 scored; the 324 released subject counts are all at least 42. '
    'Approximate conditional 95% intervals use Jeffreys-smoothed binomial variance from published rounded '
    'rates, all-member (I−H) propagation and a fixed deleted regression scale. Combined uses maximum positive '
    'subject covariance and displays the smaller subject count only, not a paired or deduplicated count. '
    'Enrollment, participation and federal 95%-rule counts never substitute.')
INCOME_LABEL = 'Individual PIMS economic disadvantage'
INCOME_DEFINITION = (
    'October 1, 2024 school individual PIMS Economic Disadvantaged Status Code field 88: own low-income '
    'enrollment divided by own same-year total enrollment, including enrolled pre-K/kindergarten categories. '
    'TANF, census poor, Medicaid, neglected/delinquent institutions and foster homes are allowed sources; '
    'recent reliable FRPL is a fallback. CEP must use individual poverty sources rather than universal meals. '
    'Field 131 food-program eligibility is separate. The published proportion truncates to four decimals; '
    'the comparison uses the precise original count ratio. Local source choices and reporting coverage '
    'remain unknown; no LEA income allocation, another denominator or year is substituted.')
ADAPTER_CONTRACT_SHA = '3aacc9db4ab1c0f986f4f81c91506d9616022a181058a9f02e01eea39c8d8de6'


def same(actual, expected):
    """Typed exact evidence equality; Python bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual) == roster_audit.fingerprint(expected)


def cohorts():
    return [dict(id='grade',level='ES',assessment=ASSESSMENT,label='Grade schools · regular PSSA',
        grades='Pure lower profiles with positive October grades 3–8; original regular PSSA All Students / Total accountable scored scope',
        standard=STANDARD,source_url=roster_audit.SOURCES['pa-assessment-2025']['url'],source='pa-assessment-2025',
        allow_point_only=False,outcome='Proficient · Proficient and Advanced',
        note='Philadelphia independent regular PSSA totals · individual October PIMS income · verified Number Scored · approximate conditional sampling intervals')]


def adapter_contract():
    return dict(dataset=DATASET, expected_n=EXPECTED_N, assessment=ASSESSMENT, standard=STANDARD,
        model_scope=MODEL_SCOPE, count_note=COUNT_NOTE, income_label=INCOME_LABEL,
        income_definition=INCOME_DEFINITION, cohort_metadata=cohorts())


def require_frozen_inputs(roster,numerical):
    """Current semantic contracts and all six complete audit/code/test pins precede every write."""
    model_audit.require_runtime_contract()
    original_adapter='3aacc9db4ab1c0f986f4f81c91506d9616022a181058a9f02e01eea39c8d8de6'
    if ADAPTER_CONTRACT_SHA!=original_adapter or roster_audit.fingerprint(adapter_contract())!=original_adapter:
        raise ValueError('Philadelphia current normalized population/assessment/income/count/interval typed contract changed')
    public_pins=dict(sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES,policy=NUMERICAL_POLICY_SHA,code=NUMERICAL_CODE_SHA,tests=NUMERICAL_TESTS_SHA)
    immutable_pins=dict(sha256='9ede3ce013d27e1947e698d9e8d1793cbec977f5e6f82822ccf197c1d8d5949d',bytes=1707603,
        policy='4faea9722801e0eccc0b3b7b5ed887c6eca84a64e479789d6a0b1a2f1135b139',
        code='9c8136f7e297531ba92338b9cf84bb085ecbd9e0816c44fcce314fa9c18cf691',
        tests='a512a456018ba22c50b9ec51d06bc3fd2e01a45b80ba2e0e136c6ce89af2f54d')
    if not same(public_pins,immutable_pins):raise ValueError('Philadelphia complete immutable numerical pin/strict byte-size contract changed')
    model_audit.require_frozen_roster(roster)
    for path,expected,label in [('scripts/audit_philadelphia_models.py',NUMERICAL_CODE_SHA,'code'),('tests/test_philadelphia_models.py',NUMERICAL_TESTS_SHA,'tests')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise ValueError('Philadelphia frozen numerical '+label+' changed')
    content=model_audit.OUTPUT.read_bytes()
    if len(content)!=NUMERICAL_BYTES or hashlib.sha256(content).hexdigest()!=NUMERICAL_SHA or not same(numerical,json.loads(content)):
        raise ValueError('Philadelphia complete numerical evidence fingerprint changed')
    if (roster_audit.fingerprint(model_audit.POLICY)!=NUMERICAL_POLICY_SHA or not same(model_audit.POLICY,numerical['policy'])
        or not same(model_audit.SUBJECTS,[m['subject'] for m in numerical['models']])
        or not same(model_audit.MIN_SCHOOLS,numerical['policy']['minimum_usable_subject_schools'])
        or not same(model_audit.NUMERIC_POLICY_SHA,numerical['numeric_policy_sha256'])
        or not same(model_audit.RUNTIME_CONTRACT_SHA,numerical['runtime_contract_sha256'])
        or any(m['assessment']!=model_audit.ASSESSMENT or m['assessment_standard']!=model_audit.STANDARD for m in numerical['models'])):
        raise ValueError('Philadelphia current numerical policy/definition/count/interval semantics differ from complete frozen evidence')


def load_inputs():
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster, numerical)
    model_audit.validate(numerical, model_audit.build(roster))
    if (numerical['hard_holds'] or numerical['status'] != 'numerically_verified_pending_integration'
            or numerical['approved_for_source'] is not False or roster['approved_for_source'] is not False
            or numerical['approved_for_modeling'] is not False or roster['approved_for_modeling'] is not False
            or len(numerical['models']) != 3
            or {(m['level'], m['subject']) for m in numerical['models']} != {('ES', s) for s in model_audit.SUBJECTS}
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 162
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model'] is not True
                   or m['coverage']['ten_valid_scored_floor_certified'] is not True for m in numerical['models'])):
        raise ValueError('Philadelphia numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def outcome(link,entry,subject,refs):
    value=link['subjects'][subject];index=model_audit.SUBJECT_FIELDS[subject]
    if entry is None:raise ValueError('Released Philadelphia profile requires exact original subject Total')
    original=entry['raw'][index];rate=model_audit.original_rate(original);scored=model_audit.original_count(entry['raw'][model_audit.COUNT_FIELD])
    if (not same(rate,value['native_rate']) or not same(original,value['raw_rate'])
        or not same(scored,value['tested']) or value['verified_valid_score_scope'] is not True
        or value['ten_valid_scored_floor_certified'] is not True or value['usable'] is not True):
        raise ValueError('Philadelphia original regular PSSA published rate/scored denominator differs from frozen source')
    variance=model_audit.verified_sampling_variance(rate,scored)
    return dict(proficiency=rate,tested=scored,raw_tested=entry['raw'][model_audit.COUNT_FIELD],
        valid_score_evidence=dict(verified=True,year=2025,school_id=link['school_id'],subject=subject,
            population='Regular PSSA All Students / Total',field='Number Scored',source_refs=copy.deepcopy(refs['outcomes'][subject])),
        exclusion=value['exclusion'],source='pa-assessment-2025',source_row=entry['source_row'],
        raw=dict(applicable=value['applicable'],native_usable=value['usable'],outcome_basis='original_regular_pssa_published_total',
            original_native_rate=original,original_rate_column=index,original_rate_field='Percent Proficient and above',
            native_outcome=copy.deepcopy(value),native_school_id=link['school_id'],source_refs=copy.deepcopy(refs['outcomes'][subject]),
            complete_source_sha256=model_audit.ROSTER_SHA,valid_score_count=scored,sampling_variance=variance,
            interval_availability=True,ten_valid_scored_floor_certified=True,count_note=COUNT_NOTE))


def build_snapshot(roster,numerical):
    require_frozen_inputs(roster,numerical)
    configurations=set(numerical['frozen_population']['grade_school_configuration_ids'])
    selected,coverage=model_audit.selected_inputs(roster,'reading')
    refs_by_id={r['school_id']:r['source_refs'] for r in selected}
    refs_by_id.update({r['school_id']:r['source_refs'] for r in coverage['excluded_configuration_records']})
    if set(refs_by_id)!=configurations:raise ValueError('Philadelphia complete 162-profile roster differs from original selector')
    raw=roster['raw_inputs'];directory={e['raw']['NCESSCH']:e['raw'] for e in raw['directory']['records']}
    incomes={e['source_row']:e['raw'] for e in raw['native_income']['records']}
    assessments={e['source_row']:e for e in raw['native_assessment']['records']}
    schools=[]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id']
        if (key in configurations) is not link['source_profile_eligible']:raise ValueError('Philadelphia normalized profile scope differs from immutable source')
        if key not in configurations:continue
        refs=refs_by_id[key];ccd=directory[link['ncessch']];income=link['income'];cells=incomes[refs['income']['source_row']]
        n=model_audit.original_count(cells[5]);low=model_audit.original_count(cells[6]);percentage=100*low/n if n and low is not None else None
        if percentage is None or low>n or not same((percentage,n,low),(income['percentage'],income['enrollment'],income['individual_low_income_count'])):
            raise ValueError('Philadelphia own October individual PIMS income ratio differs from frozen evidence')
        entries={s:assessments[refs['outcomes'][s]['source_row']] for s in ['math','reading']}
        schools.append(dict(id=key,ncessch=link['ncessch'],cohort='grade',name=link['name'],district_id=roster_audit.LEA,
            district=ccd['LEA_NAME'],city=ccd['LCITY'] or None,county='Philadelphia',enrollment=n,low_income=low,income=percentage,
            income_source='pa-income-2025',income_row=refs['income']['source_row'],
            income_raw=dict(individual_income=dict(year=2025,date='October 1, 2024',enrollment=n,individual_low_income_count=low,
                percentage=percentage,published_proportion=cells[7],raw_denominator=cells[5],definition=INCOME_DEFINITION),
                source_refs=copy.deepcopy(refs['income']),complete_source_sha256=model_audit.ROSTER_SHA,valid_score_denominator=False),
            identity_raw=dict(ncessch=link['ncessch'],native_school_id=link['native_school_id'],native_aun=roster_audit.AUN,
                native_normalized_school_id=key,source_refs=copy.deepcopy(refs),complete_source_sha256=model_audit.ROSTER_SHA,
                ccd_flags=copy.deepcopy(link['ccd_flags']),offered_evidence=copy.deepcopy(link['offered']),
                native_october_grade_evidence=copy.deepcopy(link['enrolled']),ccd_membership=copy.deepcopy(link['ccd_membership'])),
            outcomes={s:outcome(link,entries[s],s,refs) for s in ['math','reading']}))
    if len(schools)!=162 or len(numerical['retained_scope_exclusions'])!=59:raise ValueError('Philadelphia release requires162 exact profiles and59 outside CCD records')
    for model in numerical['models']:
        values=[]
        for school in schools:
            rates={s:school['outcomes'][s]['proficiency'] for s in ['math','reading']};counts={s:school['outcomes'][s]['tested'] for s in ['math','reading']}
            y=(rates['math']+rates['reading'])/2 if model['subject']=='combined' else rates[model['subject']]
            values.append(dict(school_id=school['id'],ncessch=school['ncessch'],income_pct=school['income'],outcome_pct=y,
                income_enrollment=school['enrollment'],individual_economic_count=school['low_income'],valid_scores_by_subject=counts))
        if not same(values,[{k:r[k] for k in values[0]} for r in model['inputs']]):raise ValueError('Philadelphia exact normalized source/count inputs differ from audited model')
    source_audit=dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),
        complete_numerical_reference=dict(path='data/source/philadelphia-model-audit.json',sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES),
        audit_code_test_references={k:copy.deepcopy(v) for k,v in numerical['sources'].items() if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_philadelphia_models.py',sha256=NUMERICAL_CODE_SHA),tests=dict(path='tests/test_philadelphia_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=model_audit.SOURCE_RAW_SHA,immutable_schema_fingerprint=model_audit.SOURCE_SCHEMA_SHA,
        immutable_definition_fingerprint=model_audit.SOURCE_DEFINITION_SHA,immutable_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA,immutable_numerical_policy_fingerprint=NUMERICAL_POLICY_SHA,
        immutable_numerical_runtime_fingerprint=model_audit.RUNTIME_CONTRACT_SHA,normalized_metadata_fingerprint=ADAPTER_CONTRACT_SHA,
        operational_roster=copy.deepcopy(numerical['source_coverage']),retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),
        retained_outside_source_profiles=copy.deepcopy(numerical['retained_outside_source_profiles']),
        nonoperational_ccd_references=[dict(source_row=e['source_row'],ncessch=e['raw']['NCESSCH'],native_school_id=e['raw']['ST_SCHID'],status=e['raw']['UPDATED_STATUS_TEXT']) for e in roster['nonoperational_directory']],
        subject_coverage={m['subject']:copy.deepcopy(m['coverage']) for m in numerical['models']},
        native_assessment_definition=dict(state='PA',name=ASSESSMENT,original_numerical_name=model_audit.ASSESSMENT,year=2025,level='ES',grades=cohorts()[0]['grades'],standard=STANDARD,source_url=roster_audit.SOURCES['pa-assessment-2025']['url']),
        historical_state_extract=copy.deepcopy(roster['state_extract']),count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_holds=True,minimum_subject_schools=30,
            historical_audits_approved_for_source=False,historical_audits_approved_for_modeling=False,all_models_point_only=False,
            normalized_source_approved=True,district_modeling_approved=True,verified_valid_score_denominators_available=True,
            ten_valid_scored_floor_certified=True,all_model_members_have_conditional_intervals=True,
            note='Only this separately validated exact 2024–25 grade-school regular PSSA contract is approved. Both historical audits keep false approvals. Every model member has its verified original scored count and conditional sampling interval. High, mixed, primary, inactive and unmatched scopes remain outside.'))
    selection=dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),
        directory_school_ids=[s['id'] for s in schools],subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],school_ids=[r['school_id'] for r in m['inputs']],population_sha256=m['population_sha256']) for m in numerical['models']})
    selection['sha256']=roster_audit.fingerprint(selection)
    sources=copy.deepcopy(roster['sources'])
    sources['historical_pennsylvania_extract']=dict(path=roster['state_extract']['path'],url=PROJECT_SOURCE+roster['state_extract']['path'],sha256=roster['state_extract']['sha256'])
    for key,path,digest in [('roster_audit','data/source/philadelphia-district-audit.json',model_audit.ROSTER_SHA),('numerical_audit','data/source/philadelphia-model-audit.json',NUMERICAL_SHA),
        ('source_audit_code','scripts/audit_philadelphia.py',model_audit.SOURCE_CODE_SHA),('source_audit_tests','tests/test_philadelphia_audit.py',model_audit.SOURCE_TESTS_SHA),
        ('numerical_audit_code','scripts/audit_philadelphia_models.py',NUMERICAL_CODE_SHA),('numerical_audit_tests','tests/test_philadelphia_models.py',NUMERICAL_TESTS_SHA)]:
        sources[key]=dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note=(
        'Philadelphia independent district comparison,2024–25: all162 audited grade schools enter each Math,ELA and Combined model. '
        'Original regular PSSA All Students / Total rates and verified Number Scored match each school’s own October individual '
        'PIMS low-income ratio. Conditional sampling intervals use all model members and fixed deleted scales; Combined uses '
        'maximum positive subject covariance and displays the smaller subject count,not a paired count. The full source preserves '
        '221CCD links,59outside records and the separate native9999 aggregate with no inferred CCD identity or school income. '
        'Native and CCD enrollment/income differences have unassigned causes. Keystone,PASA and charterLEAs remain separate. '
        'Admissions,provider roles,programs,coordinates and boundaries remain unaudited; one year only.')
    shifts='; '.join(('ELA' if m['subject']=='reading' else m['subject'].title())+' '+format(m['diagnostics']['maximum_prediction_change_on_observed_income_range'],'.6f') for m in numerical['models'])
    details=[MODEL_SCOPE,
        'Three separate unweighted OLS fits reproduce all486 audited results and explicit deleted fits. Combined independently '
        'fits the equal mean of original Math and ELA rates,with its own scale and studentization. Filters never refit. '
        'Associations do not establish causal effectiveness or overall quality.',
        'Regular PSSA includes native grades3–8 and the published All Students / Total accountable scored population. '
        'Original notes exclude post-October1 enrollment,homeschoolers,excluded school aggregations,ELL enrolled less than '
        'one year,LIFE pupils enteringEL after the prior testing window and pupils who did not attempt. Proficiency uses '
        'the directly published Proficient and above percentage,with one-decimal rounding; rounded levels and grade rates '
        'are never summed or averaged. Keystone end-of-course and PASA alternate assessment remain separate.',
        INCOME_DEFINITION,
        'Native October LEA enrollment120,148 differs from operational school/income enrollment116,286; CCD reports120,057 '
        'and116,230 respectively. Native9999 accounts for3,862 enrolled pupils but has no exact CCD identity or school '
        'income. Native LEA low-income90,098 versus school88,634 leaves1,464 unassigned. These differences do not establish '
        'their causes or authorize income allocation. Inactive Meehan is never substituted for9999; K–2 Barton remains outside.',
        COUNT_NOTE+' Studentization uses N−3 deleted degrees of freedom; it provides no enrollment adjustment or shrinkage. '
        'Intervals condition on income,design and deleted scale and approximate sampling alone; local poverty-source choice '
        'and accountable population/rounding uncertainty remain limits.',
        'All full and486 deleted designs have rank two and finite positive scales. Largest deleted prediction changes '
        'over observed incomes: '+shifts+' percentage points. Meredith and Greenfield ELA predictions above100% remain '
        'unclipped; Jenks Abram’s authoritative NCES/native school-number suffixes differ. Influence never removes a school.',
        'The complete source preserves22,108 original records and622,260 typed cells with original headers,notes and definitions. '
        'Compact references preserve exact table,worksheet,row and field evidence. Historical audit approvals remain false; '
        'only the separately validated grade-school comparison is released.',
        'High,mixed,primary,inactive,unmatched and separate charter-LEA records remain outside the162 released profiles. '
        'Programs are Unclassified; admissions,provider roles,coordinates and boundaries remain unknown. One year only; '
        'incompatible thresholds and income definitions cannot form a national ranking.']
    # New authored public prose is spaced independently of exact original source labels.
    def prose(value):
        replacements={'comparison,2024':'comparison, 2024','all162':'all 162','Math,ELA':'Math, ELA','count,not':'count, not',
            'links,59':'links, 59','Native9999':'Native 9999',
            '221CCD':'221 CCD','59outside':'59 outside','native9999':'native 9999','Keystone,PASA':'Keystone, PASA','charterLEAs':'charter LEAs',
            'Admissions,provider':'Admissions, provider','roles,programs,coordinates':'roles, programs, coordinates','all486':'all 486',
            'rates,with':'rates, with','grades3–8':'grades 3–8','post-October1':'post-October 1','enrollment,homeschoolers,excluded':'enrollment, homeschoolers, excluded',
            'aggregations,ELL':'aggregations, ELL','year,LIFE':'year, LIFE','enteringEL':'entering EL','percentage,with':'percentage, with',
            'enrollment120':'enrollment 120','enrollment116':'enrollment 116','reports120':'reports 120','and116':'and 116',
            'for3,862':'for 3,862','low-income90':'low-income 90','school88':'school 88','leaves1,464':'leaves 1,464','for9999':'for 9999',
            'income,design':'income, design','and486':'and 486','above100%':'above 100%','preserves22':'preserves 22','and622':'and 622',
            'headers,notes':'headers, notes','table,worksheet,row':'table, worksheet, row','High,mixed,primary,inactive,unmatched':'High, mixed, primary, inactive, unmatched','the162':'the 162','admissions,provider':'admissions, provider','roles,coordinates':'roles, coordinates'}
        for old,new in replacements.items():value=value.replace(old,new)
        return value
    coverage_note=prose(coverage_note);details=[prose(v) for v in details]
    return dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',state=dict(id='PA',name='Pennsylvania'),
        name='Philadelphia 2024–25 regular PSSA district comparison',region='philadelphia',region_name='Philadelphia',statewide=False,
        comparison='Philadelphia · {year} · {assessment} · {note}',prepare_script='scripts/prepare_philadelphia.py',
        source_url=roster_audit.SOURCES['pa-assessment-2025']['url'],retrieved='2026-10-13',model_scope=MODEL_SCOPE,
        release_status='ready',approved_for_source=True,approved_for_modeling=True,
        map_source='School coordinates and district boundaries are unavailable in the audited Philadelphia source release.',
        income_definition=dict(label=INCOME_LABEL,definition=INCOME_DEFINITION,url=roster_audit.SOURCES['pa-pims-2025']['url']),
        sources=sources,cohorts=cohorts(),schools=schools,selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Philadelphia independent regular PSSA grade-school models with individual October PIMS income, verified scored counts and approximate conditional sampling intervals.',
            details=details,sources=[dict(label=label,url=sources[key]['url']) for key,label in [
                ('pa-assessment-2025','PDE 2025 original PSSA school results'),('pa-grades-2025','PDE October 2024 grade enrollment'),
                ('pa-income-2025','PDE 2024–25 individual low-income enrollment'),('pa-pims-2025','PIMS 2024–25 field 88 individual poverty definition'),
                ('ccd_school_directory','CCD exact 2024–25 school roster'),('ccd_school_membership','CCD same-year school membership'),
                ('ccd_lea_directory','CCD exact district identity'),('ccd_lea_membership','CCD same-year district membership')]]))


def build():
    return build_snapshot(*load_inputs())


def validate(payload, expected=None):
    # Cached normalized expectations never bypass complete immutable linked evidence.
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical)
    expected = build() if expected is None else expected
    if not same(payload,expected):
        raise ValueError('Philadelphia normalized extract differs from pinned source/model evidence, scope or selection policy')
    return payload['source_audit']


def extract(destination=EXTRACT):
    payload = build()
    Path(destination).write_text(json.dumps(payload,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n')
    return payload


def validate_canonical(payload, database, numerical, extract_path=EXTRACT):
    """Read every scoped canonical input/result and compare with the passed audits."""
    validate(payload, build_snapshot(model_audit.load_roster(), numerical))
    cohort = payload['cohorts'][0]
    assessment_id = definition_id(DATASET, 2025, cohort['assessment'], 'ES')
    income_id = DATASET + ':income'
    profiles = {s['id']: s for s in payload['schools']}
    number = lambda value: None if value is None else float(value)
    namespace = DATASET + ':%'
    with closing(connect(database)) as db:
        datasets = [dict(r) for r in db.execute('SELECT * FROM dataset WHERE id=? OR id LIKE ?', (DATASET, namespace))]
        if not same(datasets, [dict(id=DATASET, state='PA', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Philadelphia canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Philadelphia canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='PA', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Philadelphia canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Pennsylvania's independent statewide release and other dataset-composite namespaces.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 162 or len(economic_rows) != 162 or len(observation_rows) != 324:
            raise ValueError('Philadelphia canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Philadelphia canonical profile/observation membership changed')
        for order, profile in enumerate(payload['schools']):
            key = profile['id']
            school = dict(schools[key]); school['profile_json'] = json.loads(school['profile_json'])
            expected_school = dict(dataset_id=DATASET, school_id=key, name=profile['name'], district_id=profile['district_id'],
                district_name=profile['district'], city=profile['city'], county=profile['county'], profile_json=profile,
                source_id=DATASET + ':extract', source_order=order)
            econ = dict(economic[key]); econ['raw_json'] = json.loads(econ['raw_json'])
            expected_econ = dict(dataset_id=DATASET, school_id=key, year=2025, definition_id=income_id,
                name=profile['name'], enrollment=number(profile['enrollment']), low_income=number(profile['low_income']),
                percentage=profile['income'], source_label=payload['income_definition']['label'], raw_json=profile['income_raw'],
                source_id=DATASET + ':' + profile['income_source'], source_order=profile['income_row'])
            if not same(school, expected_school) or not same(econ, expected_econ):
                raise ValueError('Philadelphia canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=value['tested'],
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=value['raw_tested'], source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Philadelphia canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Philadelphia canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                assessed_schools=162, excluded_schools=162 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Philadelphia canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Philadelphia canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']))
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'],low=result['low'],high=result['high'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Philadelphia canonical counted/conditional result differs from audited district fit')
            total += len(saved)
        if total != 486 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Philadelphia canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Philadelphia canonical foreign-key integrity failed')
    return {'schools': len(profiles), 'observations': len(observations), 'models': len(runs), 'results': total}


def validate_exports(payload, output, numerical):
    validate(payload, build_snapshot(model_audit.load_roster(), numerical))
    output = Path(output)
    schools = json.loads((output / 'schools.json').read_text())
    history = json.loads((output / 'history.json').read_text())
    coverage = json.loads((output / 'coverage.json').read_text())
    descriptor = json.loads((output / 'catalog.json').read_text())
    exported = {s['id']: s for s in schools['schools']}
    records = {r['school_id']: r for r in history['records']}
    profiles = {s['id']: s for s in payload['schools']}
    if (len(schools['schools']) != 162 or len(history['records']) != 162
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Philadelphia exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Philadelphia export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Philadelphia history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Philadelphia historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                              assessed_schools=162, excluded_schools=162 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Philadelphia exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Philadelphia exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=result['valid_scores'], cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Philadelphia per-school counted/conditional metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Philadelphia profile/history subject set differs from exact audited eligibility')
        expected_exclusions = {s: profile['outcomes'][s]['exclusion'] for s in ['math', 'reading']
                               if profile['outcomes'][s]['exclusion'] is not None}
        if expected_exclusions:
            expected_exclusions['combined'] = '; '.join(
                ('Math' if s == 'math' else 'ELA') + ': ' + expected_exclusions[s]
                for s in ['math', 'reading'] if s in expected_exclusions)
        profile_fields = dict(level='ES', name=profile['name'], short=profile['name'],
            district=profile['district'], income=profile['income'], enrollment=None if profile['enrollment'] is None else float(profile['enrollment']),
            city=profile['city'], county=profile['county'], latitude=None, longitude=None,
            program='Unclassified', programs=['Unclassified'], exclusions=expected_exclusions)
        record_fields = dict(level='ES', year=2025, income_year=2025,
            assessment=ASSESSMENT, name=profile['name'], income=profile['income'],
            enrollment=None if profile['enrollment'] is None else float(profile['enrollment']), income_label=payload['income_definition']['label'],
            exclusions=expected_exclusions)
        if (set(school) != set(profile_fields) | {'id', 'metrics', 'history'}
                or set(record) != set(record_fields) | {'school_id', 'subjects'}
                or not same({k: school.get(k) for k in profile_fields}, profile_fields)
                or not same({k: record.get(k) for k in record_fields}, record_fields)
                or not same(school['history'], [record])):
            raise ValueError('Philadelphia profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 162, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=162, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Philadelphia exported coverage/source exclusions differ from approved selection')
    cohort = payload['cohorts'][0]
    expected_levels = {'ES': dict(year=2025, label=cohort['label'], assessment=cohort['assessment'],
                                  outcome=cohort['outcome'], math_label='Math', note=cohort['note'])}
    header = dict(year=payload['academic_year'], assessment_year=2025,
        income_label=payload['income_definition']['label'], program_options=['Unclassified'],
        levels=expected_levels, history_years=[2025], coverage_note=payload['coverage_note'],
        methodology=payload['methodology'])
    if (set(schools) != set(header) | {'schools', 'models', 'history_models'}
            or set(history) != {'records', 'models'}
            or not same({k: schools.get(k) for k in header}, header)):
        raise ValueError('Philadelphia exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='philadelphia', geography='philadelphia', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Philadelphia ready descriptor must retain distinct district and counted regular PSSA scope')
    return {m['model_id']: m['coefficients']['n'] for m in numerical['models']}


def validate_existing_namespace(payload, database, numerical, extract_path):
    """A repeat import must not erase evidence of a corrupt or foreign namespace."""
    namespace = DATASET + ':%'
    scopes = [
        ('dataset', 'id=? OR id LIKE ?', (DATASET, namespace)),
        ('source', 'dataset_id=? OR id LIKE ?', (DATASET, namespace)),
        ('assessment_definition', 'id LIKE ?', (namespace,)),
        ('economic_definition', 'id LIKE ?', (namespace,)),
        ('school', 'dataset_id=? OR source_id LIKE ?', (DATASET, namespace)),
        ('economic_observation', 'dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?', (DATASET, namespace, namespace)),
        ('assessment_observation', 'dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?', (DATASET, namespace, namespace)),
        ('model_run', 'dataset_id=? OR id LIKE ? OR definition_id LIKE ?', (DATASET, namespace, namespace)),
        ('model_result', 'dataset_id=? OR model_id LIKE ?', (DATASET, namespace)),
    ]
    with closing(connect(database)) as db:
        populated = any(db.execute('SELECT 1 FROM ' + table + ' WHERE ' + where + ' LIMIT 1', parameters).fetchone()
                        for table, where, parameters in scopes)
    if populated:
        validate_canonical(payload, database, numerical, extract_path)


def prepare(database=DEFAULT_DB, output=OUTPUT, extract_path=EXTRACT):
    output, extract_path = Path(output).resolve(), Path(extract_path).resolve()
    # The shared helper emits repository-relative provenance/catalog links.
    # Reject unsupported destinations before opening any database transaction.
    output.relative_to(ROOT)
    extract_path.relative_to(ROOT)
    roster, numerical = load_inputs()
    payload = json.loads(Path(extract_path).read_text())
    validate(payload, build_snapshot(roster, numerical))
    validate_existing_namespace(payload, database, numerical, extract_path)
    coverage = prepare_snapshot(payload, extract_path, output, database)
    descriptor_path = Path(output) / 'catalog.json'
    descriptor = json.loads(descriptor_path.read_text())
    descriptor['regions'][0].update(name=payload['region_name'], statewide=False,
        comparison=payload['comparison'], audit=str((Path(output) / 'coverage.json').relative_to(ROOT)))
    descriptor_path.write_text(json.dumps(descriptor, indent=2) + '\n')
    validate_exports(payload, output, numerical)
    validate_canonical(payload, database, numerical, extract_path)
    return coverage


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true')
    parser.add_argument('--extract-only', action='store_true', help='Rebuild normalized evidence without database import or exports')
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--extract-path', type=Path, default=EXTRACT)
    args = parser.parse_args()
    if args.extract or args.extract_only:
        extract(args.extract_path)
    if args.extract_only:
        print(json.dumps({'dataset': DATASET, 'normalized_extract': str(args.extract_path)}, sort_keys=True))
    else:
        result = prepare(args.database, args.output, args.extract_path)
        print(json.dumps({k: result[k] for k in ['year', 'schools', 'cohorts']}, sort_keys=True))

"""Canonical/static Memphis TNReady comparison linked to immutable point-only audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import audit_memphis as roster_audit
import audit_memphis_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot
DATASET = 'tn-memphis-2025'
EXTRACT = ROOT / 'data/source/memphis.json'
OUTPUT = ROOT / 'data/memphis'
NUMERICAL_SHA = '7aaf909cc10c3703e18ff574b30c09d5327d4c3529358917981349adcd291561'
NUMERICAL_BYTES = 1961906
NUMERICAL_POLICY_SHA = '9fcb82a6693305fc31fe5910bc9c2ebcef55220ca42ac78d310bd76d82b2c020'
NUMERICAL_CODE_SHA = '4575a4fe1ea49f5b12a763d06009655b08de7142997870d79d3aaf52d4561d66'
NUMERICAL_TESTS_SHA = 'eee04e242f5c80840bcd5be163d0a969c42b88c83b312d776c187c81c3152acb'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':142,'reading':147,'combined':142}
ASSESSMENT = 'TNReady regular All Students G38 proficiency'
STANDARD = model_audit.STANDARD
MODEL_SCOPE = (
    'Memphis–Shelby independent 2024–25 grade-school models use exact NCES LEA 4700148 / CCD TN-00792 / EDC 792 identities. '
    'All 154 audited operational pure lower offered and reconciled enrolled grade profiles remain searchable. '
    'Four specifically named shared-time schools retain unresolved enrolled-versus-served income/outcome attribution '
    'and have unavailable comparison metrics. Original TNReady regular All Students G38 Levels 3–4 published rates '
    'and own reported individual direct certification / same-year school membership support separate fixed 142 Math, '
    '147 ELA and independently fitted 142 Combined models. Charters, income extremes and influence remain included. '
    'The school-specific note does not certify attribution coverage at nonlisted schools. Native-only, high, mixed, '
    'primary and other excluded configurations remain outside. Valid-score counts and the ten-valid-scored floor '
    'remain uncertified; all sampling intervals are unavailable.')
COUNT_NOTE = (
    'Original EDC tested and performance-level counts remain unverified valid-score denominators and may be '
    'constructed from other source information. Own CCD membership, direct certification, participation and federal '
    '95%-rule counts never substitute. All valid-score counts, sampling variances and interval endpoints are null '
    'modelwide; the ten-valid-scored floor remains uncertified.')
INCOME_LABEL = 'Reported individual direct certification / school membership'
INCOME_DEFINITION = (
    '2024–25 reported CCD Final 2a individual Direct Certification Education Unit Total divided by that school’s '
    'own reported same-year Membership Education Unit Total, including pre-K where enrolled. This benefits/status '
    'measure is an economic disadvantage proxy, not full household-income FRPL, Tennessee economic disadvantage '
    'or universal/CEP meal receipt. Both counts require Reported flags; masks, missing or derived counts, other-year '
    'income and tested-subgroup denominators never substitute. Certification and Medicaid/reporting coverage vary '
    'and completeness is unknown. Four named shared-time schools retain their original raw ratios but usable income and '
    'proficiency are unavailable because enrolled-versus-served attribution is unresolved.')
ADAPTER_CONTRACT_SHA = 'e53a780a9c140b7e29b0baa53720820d77cdb33dbe7519045303b0ccf2704e5e'
NORMALIZED_PAYLOAD_SHA = '726cb9183dcd797b6404b62285676f1a0776e3b7a09b09104ed5d5cf4b70fff0'

def same(actual,expected):
    """Typed exact evidence equality; bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual)==roster_audit.fingerprint(expected)

def cohorts():
    return [dict(id='grade',level='ES',assessment=ASSESSMENT,label='Grade schools · TNReady regular G38',
        grades='Operational pure lower offered and reconciled enrolled profiles with positive reported grades 3–8; native regular All Students G38',
        standard=STANDARD,source_url=roster_audit.SOURCES['edc_2025']['url'],source='edc_2025',allow_point_only=True,
        outcome='Proficient · Levels 3–4',note='Memphis–Shelby independent district models · individual reported direct certification '
            'and own membership · four named shared-time attribution holds · valid-score counts and floor uncertified · sampling intervals unavailable')]

def adapter_contract():
    return dict(dataset=DATASET,extract_path=str(EXTRACT.relative_to(ROOT)),default_output=str(OUTPUT.relative_to(ROOT)),project_source=PROJECT_SOURCE,expected_n=EXPECTED_N,assessment=ASSESSMENT,standard=STANDARD,model_scope=MODEL_SCOPE,
        count_note=COUNT_NOTE,income_label=INCOME_LABEL,income_definition=INCOME_DEFINITION,cohort_metadata=cohorts())

def require_frozen_inputs(roster, numerical):
    """Current semantic contracts and all six complete audit/code/test pins precede every write."""
    model_audit.require_runtime_contract()
    original_adapter = 'e53a780a9c140b7e29b0baa53720820d77cdb33dbe7519045303b0ccf2704e5e'
    if ADAPTER_CONTRACT_SHA != original_adapter or roster_audit.fingerprint(adapter_contract()) != original_adapter:
        raise ValueError('Memphis–Shelby current normalized population/assessment/income/typed metadata contract changed')
    if NORMALIZED_PAYLOAD_SHA != '726cb9183dcd797b6404b62285676f1a0776e3b7a09b09104ed5d5cf4b70fff0':
        raise ValueError('Memphis immutable normalized fingerprint alias changed')
    public_pins = dict(sha256=NUMERICAL_SHA, bytes=NUMERICAL_BYTES, policy=NUMERICAL_POLICY_SHA,
                       code=NUMERICAL_CODE_SHA, tests=NUMERICAL_TESTS_SHA)
    immutable_pins = dict(sha256='7aaf909cc10c3703e18ff574b30c09d5327d4c3529358917981349adcd291561', bytes=1961906,
        policy='9fcb82a6693305fc31fe5910bc9c2ebcef55220ca42ac78d310bd76d82b2c020',
        code='4575a4fe1ea49f5b12a763d06009655b08de7142997870d79d3aaf52d4561d66',
        tests='eee04e242f5c80840bcd5be163d0a969c42b88c83b312d776c187c81c3152acb')
    if not same(public_pins, immutable_pins):
        raise ValueError('Memphis–Shelby complete immutable numerical pin/strict byte-size contract changed')
    model_audit.require_frozen_roster(roster)
    for path, expected, label in [('scripts/audit_memphis_models.py', NUMERICAL_CODE_SHA, 'code'),
                                 ('tests/test_memphis_models.py', NUMERICAL_TESTS_SHA, 'tests')]:
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Memphis–Shelby frozen numerical ' + label + '/policy fingerprint changed')
    content = model_audit.OUTPUT.read_bytes()
    if len(content) != NUMERICAL_BYTES or hashlib.sha256(content).hexdigest() != NUMERICAL_SHA or not same(numerical, json.loads(content)):
        raise ValueError('Memphis–Shelby complete numerical evidence fingerprint changed')
    if (roster_audit.fingerprint(model_audit.POLICY) != NUMERICAL_POLICY_SHA
            or not same(model_audit.POLICY, numerical['policy'])
            or not same(model_audit.SUBJECTS, [m['subject'] for m in numerical['models']])
            or not same(model_audit.MIN_SCHOOLS, numerical['policy']['minimum_usable_subject_schools'])
            or not same(model_audit.NUMERIC_POLICY_SHA, numerical['numeric_policy_sha256'])
            or not same(model_audit.RUNTIME_CONTRACT_SHA, numerical['runtime_contract_sha256'])
            or any(m['assessment'] != model_audit.ASSESSMENT or m['assessment_standard'] != model_audit.STANDARD
                   for m in numerical['models'])):
        raise ValueError('Memphis–Shelby current numerical policy/definition differs from complete frozen evidence')


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
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 154
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model']
                   or m['coverage']['ten_valid_scored_floor_certified'] is not False for m in numerical['models'])):
        raise ValueError('Memphis–Shelby numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def outcome(link,entry,subject,refs):
    value=link['subjects'][subject];original=None if entry is None else entry['raw'][model_audit.RATE_FIELD]
    reported=None if entry is None else model_audit.original_rate(original)
    if not same((reported,original),(value['native_rate'],value['raw_rate'])):raise ValueError('Memphis original published G38 rate differs from frozen source')
    held=link['source_attribution_hold']is not None
    return dict(proficiency=None if held else reported,tested=None,valid_score_evidence=None,raw_tested=None,
        exclusion=value['exclusion'],source='edc_2025',source_row=0 if entry is None else entry['source_row'],
        raw=dict(native_usable=value['usable'],outcome_basis='original_edc_school_regular_all_students_g38_published_rate',
            original_native_rate=original,original_reported_percentage=reported,original_rate_field=model_audit.RATE_FIELD,
            original_unverified_tested_token=value['raw_tested'],source_attribution_hold=link['source_attribution_hold'],
            native_school_id=None if entry is None else entry['raw']['StateAssignedSchID'],
            source_refs=copy.deepcopy(refs['outcomes'][subject]),complete_source_sha256=model_audit.ROSTER_SHA,
            valid_score_count=None,sampling_variance=None,interval_availability=False,ten_valid_scored_floor_certified=False,count_note=COUNT_NOTE))


def build_snapshot(roster,numerical):
    require_frozen_inputs(roster,numerical);configurations=set(numerical['frozen_population']['grade_school_configuration_ids'])
    selected,coverage=model_audit.selected_inputs(roster,'reading');refs_by_id={r['school_id']:r['source_refs']for r in selected}
    refs_by_id.update({r['school_id']:r['source_refs']for r in coverage['excluded_configuration_records']})
    if set(refs_by_id)!=configurations:raise ValueError('Memphis complete 154-profile roster differs from original selector')
    raw=roster['raw_inputs'];directory={e['raw']['NCESSCH']:e['raw']for e in raw['directory']['records']}
    members={e['source_row']:e['raw']for e in raw['membership']['records']};direct={e['source_row']:e['raw']for e in raw['lunch']['records']};assessments={e['source_row']:e for e in raw['assessment']['records']};schools=[]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id']
        if (key in configurations)is not link['source_profile_eligible']:raise ValueError('Memphis normalized profile scope differs from immutable source')
        if key not in configurations:continue
        refs=refs_by_id[key];ccd=directory[key];income=link['income'];n=model_audit.original_count(members[refs['membership']['source_row']]);low=model_audit.original_count(direct[refs['direct_certification']['source_row']]);reported=100*low/n if n and low is not None and low<=n else None
        if reported is None or not same((reported,n,low),(income['reported_percentage'],income['reported_membership'],income['reported_direct_certification'])):raise ValueError('Memphis own reported individual direct-certification ratio differs from frozen evidence')
        held=link['source_attribution_hold']is not None
        if income['usable']is not(not held):raise ValueError('Memphis source-attribution/income usability differs')
        entries={s:None if refs['outcomes'][s]is None else assessments[refs['outcomes'][s]['source_row']]for s in ['math','reading']}
        edc_native=next((e['raw']['StateAssignedSchID']for e in entries.values()if e is not None),None)
        schools.append(dict(id=key,ncessch=key,cohort='grade',name=link['name'],district_id=roster_audit.LEA,district=ccd['LEA_NAME'],city=ccd['LCITY']or None,county=None,
            enrollment=n,low_income=low,income=None if held else reported,income_source='ccd_lunch_2025',income_row=refs['direct_certification']['source_row'],
            income_raw=dict(individual_income=dict(year=2025,school_year='2024–25',membership=n,reported_direct_certified=low,reported_percentage=reported,
                usable_percentage=None if held else reported,definition=INCOME_DEFINITION),source_attribution_hold=link['source_attribution_hold'],
                source_refs=dict(membership=copy.deepcopy(refs['membership']),direct_certification=copy.deepcopy(refs['direct_certification'])),complete_source_sha256=model_audit.ROSTER_SHA,valid_score_denominator=False),
            identity_raw=dict(ncessch=key,native_school_id=link['native_school_id'],edc_native_school_id=edc_native,source_refs=copy.deepcopy(refs),complete_source_sha256=model_audit.ROSTER_SHA,
                ccd_flags=copy.deepcopy(link['ccd_flags']),offered_scope=link['offered']['scope'],source_profile_eligible=True,source_attribution_hold=link['source_attribution_hold']),
            outcomes={s:outcome(link,entries[s],s,refs)for s in ['math','reading']}))
    if len(schools)!=154 or len(numerical['retained_scope_exclusions'])!=69:raise ValueError('Memphis release requires 154 exact profiles and 69 retained outside records')
    if sum(s['income']is None for s in schools)!=4:raise ValueError('Memphis requires exactly four unavailable source-attribution profiles')
    for model in numerical['models']:
        normalized=[]
        for school in schools:
            rates={s:school['outcomes'][s]['proficiency']for s in ['math','reading']};y=(rates['math']+rates['reading'])/2 if model['subject']=='combined'and all(v is not None for v in rates.values())else rates.get(model['subject'])
            if school['income']is not None and y is not None:normalized.append(dict(school_id=school['id'],ncessch=school['ncessch'],income_pct=school['income'],outcome_pct=y,income_enrollment=school['enrollment'],reported_direct_certified_count=school['low_income']))
        if not same(normalized,[{k:r[k]for k in normalized[0]}for r in model['inputs']]):raise ValueError('Memphis normalized subject inputs differ from audited numerical cohort')
    source_audit=dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),complete_numerical_reference=dict(path='data/source/memphis-model-audit.json',sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES),
        audit_code_test_references={k:copy.deepcopy(v)for k,v in numerical['sources'].items()if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_memphis_models.py',sha256=NUMERICAL_CODE_SHA),tests=dict(path='tests/test_memphis_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=model_audit.SOURCE_RAW_SHA,immutable_schema_fingerprint=model_audit.SOURCE_SCHEMA_SHA,immutable_definition_fingerprint=model_audit.SOURCE_DEFINITION_SHA,immutable_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA,immutable_source_runtime_fingerprint=model_audit.SOURCE_RUNTIME_SHA,immutable_numerical_policy_fingerprint=NUMERICAL_POLICY_SHA,immutable_numerical_runtime_fingerprint=model_audit.RUNTIME_CONTRACT_SHA,normalized_metadata_fingerprint=ADAPTER_CONTRACT_SHA,
        operational_roster=copy.deepcopy(numerical['source_coverage']),retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),retained_outside_source_profiles=copy.deepcopy(numerical['retained_outside_source_profiles']),
        source_attribution_holds=dict(held_ids=copy.deepcopy(numerical['frozen_population']['shared_time_prospective_hold_ids']),primary=copy.deepcopy(numerical['retained_source_reference']['shared_time_primary']),
            basis='Four specifically named school profiles remain searchable with unusable income/outcomes and no metrics; original reported ratios and rates remain in linked raw evidence. Nonlisted attribution coverage is not certified.'),
        subject_coverage={m['subject']:copy.deepcopy(m['coverage'])for m in numerical['models']},nonoperational_ccd_references=[],
        native_assessment_definition=dict(state='TN',name=ASSESSMENT,original_numerical_name=model_audit.ASSESSMENT,year=2025,level='ES',grades=cohorts()[0]['grades'],standard=STANDARD,source_url=roster_audit.SOURCES['edc_2025']['url']),
        historical_state_extract=copy.deepcopy(roster['state_extract']),count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_hard_holds=True,source_attribution_holds_retained=True,minimum_subject_schools=30,
            historical_audits_approved_for_source=False,historical_audits_approved_for_modeling=False,all_models_point_only=True,normalized_source_approved=True,district_modeling_approved=True,
            verified_valid_score_denominators_available=False,ten_valid_scored_floor_certified=False,numerical_success_resolves_count_hold=False,
            note='Only this separately validated exact 154-profile/142 Math147 ELA142 Combined point-only contract is approved. Historical six audits/code/tests remain unchanged with false audit approvals. The four source-attribution holds, native-only/outside scopes, missingness and valid-score/count-floor limits remain unreleased.'))
    selection=dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),directory_school_ids=[s['id']for s in schools],
        subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],school_ids=[r['school_id']for r in m['inputs']],population_sha256=m['population_sha256'])for m in numerical['models']})
    selection['sha256']=roster_audit.fingerprint(selection);sources=copy.deepcopy(roster['sources']);sources['historical_tennessee_extract']=dict(path=roster['state_extract']['path'],url=PROJECT_SOURCE+roster['state_extract']['path'],sha256=roster['state_extract']['sha256'])
    for key,path,digest in [('roster_audit','data/source/memphis-district-audit.json',model_audit.ROSTER_SHA),('numerical_audit','data/source/memphis-model-audit.json',NUMERICAL_SHA),
        ('source_audit_code','scripts/audit_memphis.py',model_audit.SOURCE_CODE_SHA),('source_audit_tests','tests/test_memphis_audit.py',model_audit.SOURCE_TESTS_SHA),('numerical_audit_code','scripts/audit_memphis_models.py',NUMERICAL_CODE_SHA),('numerical_audit_tests','tests/test_memphis_models.py',NUMERICAL_TESTS_SHA)]:sources[key]=dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note=(
        'Memphis–Shelby independent district comparison, 2024–25. All 154 audited grade-school profiles remain searchable; 142 Math, 147 ELA and 142 Combined results use separate fixed district models. '
        'Four named shared-time schools have unavailable income/comparison results because enrolled-versus-served attribution is unresolved; published masks and missing rates remain unavailable. '
        'Own reported CCD individual direct certification / membership is a benefits/status proxy, not full FRPL or universal meal receipt. Native regular All Students TNReady G38 proficiency uses Levels 3–4 original published rates. '
        'The source retains all 223 exact CCD school records, 69 outside this scope, and unjoined native-only Caldwell-Guthrie. District 111,124 minus operational school 111,125 is −1; its cause is unknown. '
        'The school-specific attribution note does not certify nonlisted coverage. Valid-score counts and the ten-valid-scored floor remain uncertified; all sampling intervals are unavailable. '
        'Programs, admissions, provider roles, coordinates and boundaries are unaudited; one year only.')
    shifts='; '.join(('ELA'if m['subject']=='reading'else m['subject'].title())+' '+format(m['diagnostics']['maximum_prediction_change_on_observed_income_range'],'.6f')for m in numerical['models'])
    details=[MODEL_SCOPE,
        'Three separate unweighted OLS fits reproduce all 431 results and explicit deleted fits. Combined independently fits the equal mean of original Math and ELA rates with its own residual scale and studentization. ELA includes five additional schools, so full subject coefficients and studentized scores cannot be averaged. Filters never refit models. Associations do not establish causal school effectiveness or overall quality.',
        'Use original EDC v3.1 school TNReady regular All Students G38 aggregate grades 3–8 proficiency at Levels 3–4. Published fractional tokens are converted to percentages without rebuilding more precise count ratios or averaging grades. Ranged, suppressed and missing rates remain unavailable, never zero. Original EDC source-business-rule limits remain.',
        INCOME_DEFINITION,
        'CCD membership/direct certification cover the school’s reported population, including pre-K where present; native G38 proficiency covers grades 3–8. The source identifies 13 Memphis schools with shared-time status. Four overlap the pure lower profiles: Germantown Middle, Woodstock Middle School, Treadwell Middle School and White Station Middle. Their enrolled-versus-served attribution is unresolved and their comparison results remain unavailable. A plausible DC/membership ratio does not clear the hold. Nine other named schools are outside the grade-school scope; nonlisted attribution coverage is not certified.',
        'The exact CCD district reports 111,124 students while its operational school totals sum 111,125. The difference −1 is not assigned a cause and never replaces an individual school’s own income denominator. Native-only Caldwell-Guthrie has no matching same-year directory identity or income and remains unjoined.',
        COUNT_NOTE+' External studentization uses every deleted-school residual scale and N−3 degrees of freedom; it supplies no enrollment adjustment or shrinkage.',
        'Full and all 431 deleted designs have rank two and positive finite scales. Largest deleted prediction changes over observed income: '+shifts+' percentage points. All 40 Math/Combined and 41 ELA charters, income extremes and influential Maxine Smith STEAM Academy remain included. Diagnostic flags never remove schools or clamp predictions.',
        'The complete linked source retains 3,368 needed original records and 80,349 typed cells, full primary definitions/schemas and exact omission inventories for 48,950 complete target records / 1,579,478 cells. Original identities, source-row/field references, raw ratio/rate values and masks permit auditing without duplicating whole raw tables.',
        'High, mixed, primary and other excluded records remain outside the 154 profiles. Programs are Unclassified; admissions, provider roles, coordinates and boundaries remain unknown. One year only; incompatible income measures and assessment thresholds cannot produce a common national ranking.']
    snapshot=dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',state=dict(id='TN',name='Tennessee'),
        name='Memphis–Shelby 2024–25 TNReady district comparison',region='memphis',region_name='Memphis–Shelby County',statewide=False,
        comparison='Memphis–Shelby · {year} · {assessment} · {note}',prepare_script='scripts/prepare_memphis.py',source_url=roster_audit.SOURCES['edc_2025']['url'],retrieved='2026-10-14',model_scope=MODEL_SCOPE,
        release_status='ready',approved_for_source=True,approved_for_modeling=True,map_source='School coordinates and district boundaries are unavailable in the audited Memphis–Shelby source release.',
        income_definition=dict(label=INCOME_LABEL,definition=INCOME_DEFINITION,url=roster_audit.SOURCES['nces_lunch_definitions']['url']),sources=sources,cohorts=cohorts(),schools=schools,selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Memphis–Shelby independent TNReady regular G38 grade-school models with own reported individual direct certification; four source-attribution holds, valid-score counts/floor uncertified and sampling intervals unavailable.',details=details,
            sources=[dict(label=label,url=sources[key]['url'])for key,label in [('edc_2025','EDC v3.1 original Tennessee TNReady rates'),('edc_codebook_v3_1','EDC original field codebook'),('edc_technical_v3_1','EDC original technical documentation and Tennessee source/standards'),('ccd_directory_2025','CCD exact 2024–25 school roster'),('ccd_membership_2025','CCD same-year own school membership'),('ccd_lunch_2025','CCD Final 2a reported direct-certification counts'),('ccd_state_notes_2025','CCD original Tennessee shared-time/reporting notes'),('nces_lunch_definitions','NCES direct-certification definitions'),('ccd_lea_directory','CCD exact district identity'),('ccd_lea_membership','CCD reported district membership')]]))
    require_normalized(snapshot)
    return snapshot


def build():
    return build_snapshot(*load_inputs())


def require_normalized(payload):
    original_normalized = '726cb9183dcd797b6404b62285676f1a0776e3b7a09b09104ed5d5cf4b70fff0'
    if NORMALIZED_PAYLOAD_SHA != original_normalized or roster_audit.fingerprint(payload) != original_normalized:
        raise ValueError('Memphis complete normalized typed/source/attribution fingerprint changed')


def validate(payload, expected=None):
    # Cached normalized expectations never bypass complete immutable linked evidence.
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical)
    require_normalized(payload)
    expected = build() if expected is None else expected
    if not same(payload,expected):
        raise ValueError('Memphis–Shelby normalized extract differs from pinned source/model evidence, scope or selection policy')
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
        if not same(datasets, [dict(id=DATASET, state='TN', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Memphis–Shelby canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Memphis–Shelby canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='TN', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Memphis–Shelby canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Tennessee's independent statewide release and other dataset-composite namespaces.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 154 or len(economic_rows) != 154 or len(observation_rows) != 308:
            raise ValueError('Memphis–Shelby canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Memphis–Shelby canonical profile/observation membership changed')
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
                raise ValueError('Memphis–Shelby canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=None,
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=None, source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Memphis–Shelby canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Memphis–Shelby canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                assessed_schools=154, excluded_schools=154 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Memphis–Shelby canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Memphis–Shelby canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']), low=None, high=None)
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Memphis–Shelby canonical point-only result differs from audited district fit')
            total += len(saved)
        if total != 431 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Memphis–Shelby canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Memphis–Shelby canonical foreign-key integrity failed')
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
    if (len(schools['schools']) != 154 or len(history['records']) != 154
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Memphis–Shelby exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Memphis–Shelby export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Memphis–Shelby history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Memphis–Shelby historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                              assessed_schools=154, excluded_schools=154 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Memphis–Shelby exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Memphis–Shelby exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=None, cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'low', 'high', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Memphis–Shelby per-school point-only metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Memphis–Shelby profile/history subject set differs from exact audited eligibility')
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
            raise ValueError('Memphis–Shelby profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 154, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=154, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Memphis–Shelby exported coverage/source exclusions differ from approved selection')
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
        raise ValueError('Memphis–Shelby exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='memphis', geography='memphis', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Memphis–Shelby ready descriptor must retain distinct district and point-only scope')
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

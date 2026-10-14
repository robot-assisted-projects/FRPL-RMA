"""Canonical/static Polk FAST/BEST/FAA comparison linked to immutable audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path

import audit_polk as roster_audit
import audit_polk_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot

DATASET = 'fl-polk-2025'
EXTRACT = ROOT / 'data/source/polk.json'
OUTPUT = ROOT / 'data/polk'
NUMERICAL_SHA = 'c551d758bc13c2b38a0f63e3fd977c90a36364853a2ec91afad07f48c5635f1d'
NUMERICAL_BYTES = 994619
NUMERICAL_POLICY_SHA = 'ab1f9fc9b028d33bbe084815c4443afd3aff9be3a5074eda43071d7c63afac91'
NUMERICAL_CODE_SHA = 'd62a1a1f7bdec792079ab026a712d2fd4d0fe930c057dba3cd9e71d3eb5600ed'
NUMERICAL_TESTS_SHA = 'ad0ee8179cb054afea8112b959dd6d5b598972446612e86e7821d0b9a3233bdc'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':109, 'reading':109, 'combined':109}
ASSESSMENT = 'FAST/BEST/FAA School Grades achievement'
STANDARD = model_audit.STANDARD
MODEL_SCOPE = (
    'Polk independent 2024–25 grade-school district models use exact NCES LEA 1201590 / FL-53 / FDOE 53 identities. '
    'All 110 audited pure lower profiles with positive or protected Fall grades 3–8 and explicit-zero grades 9–12 '
    'remain searchable. Original whole-percent School Grades Math and ELA achievement supports 109 schools in '
    'each separate Math, ELA and independently fitted Combined model; Compass Middle Charter School retains missing achievement. '
    'Same-year individual February lunch-status counts use their own school denominator. Published accountable '
    'FAST PM3, BEST/Access EOC and eligible FAA achievement retains full-year, home-zoned, ELL and exemption rules; '
    'Datafolio and percent-tested participation remain separate. High, mixed, primary, closed and unmatched scopes '
    'remain outside this point-only release. Valid-score denominators and the ten-valid-scored floor remain '
    'uncertified; sampling intervals are unavailable modelwide.')
COUNT_NOTE = (
    'School Grades provides no verified valid-score denominators. Its at-least-ten-eligible component rule does '
    'not certify ten valid-scored students. February income denominators, Fall/CCD enrollment, percent tested, '
    'participation and the federal 95%-rule never substitute for valid-score counts. All valid-score counts, '
    'sampling variances and interval endpoints are null; sampling intervals are unavailable.')
INCOME_LABEL = 'Individual free/reduced-price eligibility and direct certification'
INCOME_DEFINITION = (
    '2024–25 Final Survey 3 February PK–12 school individual eligibility: original free lunch D/F plus '
    'reduced-price 3/E plus direct-certification C/R counts divided by that school’s own reported denominator. '
    'Provision 2 code 4 must be explicitly zero. District option 6/9 conversions to C/D are already required '
    'by the original data element. Federal funding multiplier columns, School Grades economic percentages, '
    'universal meal availability, enrollment substitutions and another-year income are not used. '
    'CEP individual identification coverage remains unknown; this is an economic disadvantage proxy.')
ADAPTER_CONTRACT_SHA = '23cefaf609ef4d5bb9a8b7bf7d942a68100610456c731b24e60178b74800dd48'


def same(actual, expected):
    """Typed exact evidence equality; Python bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual) == roster_audit.fingerprint(expected)


def cohorts():
    return [dict(id='grade', level='ES', assessment=ASSESSMENT,
        label='Grade schools · FAST/BEST/FAA School Grades',
        grades='Pure lower profiles with positive/protected Fall grades 3–8; native FAST/BEST/Access EOC/FAA accountable scope',
        standard=STANDARD, source_url=roster_audit.SOURCES['assessment']['url'], source='assessment',
        allow_point_only=True, outcome='Proficient · Level 3 or above',
        note='Polk independent published achievement · individual February income · full-year and home-zoned accountability · '
            'valid-score counts and ten-valid-scored floor uncertified · sampling intervals unavailable')]


def adapter_contract():
    return dict(dataset=DATASET, expected_n=EXPECTED_N, assessment=ASSESSMENT, standard=STANDARD,
        model_scope=MODEL_SCOPE, count_note=COUNT_NOTE, income_label=INCOME_LABEL,
        income_definition=INCOME_DEFINITION, cohort_metadata=cohorts())


def require_frozen_inputs(roster, numerical):
    """Current semantic contracts and all six complete audit/code/test pins precede every write."""
    model_audit.require_runtime_contract()
    original_adapter = '23cefaf609ef4d5bb9a8b7bf7d942a68100610456c731b24e60178b74800dd48'
    if ADAPTER_CONTRACT_SHA != original_adapter or roster_audit.fingerprint(adapter_contract()) != original_adapter:
        raise ValueError('Polk current normalized population/assessment/income/typed metadata contract changed')
    public_pins = dict(sha256=NUMERICAL_SHA, bytes=NUMERICAL_BYTES, policy=NUMERICAL_POLICY_SHA,
                       code=NUMERICAL_CODE_SHA, tests=NUMERICAL_TESTS_SHA)
    immutable_pins = dict(sha256='c551d758bc13c2b38a0f63e3fd977c90a36364853a2ec91afad07f48c5635f1d', bytes=994619,
        policy='ab1f9fc9b028d33bbe084815c4443afd3aff9be3a5074eda43071d7c63afac91',
        code='d62a1a1f7bdec792079ab026a712d2fd4d0fe930c057dba3cd9e71d3eb5600ed',
        tests='ad0ee8179cb054afea8112b959dd6d5b598972446612e86e7821d0b9a3233bdc')
    if not same(public_pins, immutable_pins):
        raise ValueError('Polk complete immutable numerical pin/strict byte-size contract changed')
    model_audit.require_frozen_roster(roster)
    for path, expected, label in [('scripts/audit_polk_models.py', NUMERICAL_CODE_SHA, 'code'),
                                 ('tests/test_polk_models.py', NUMERICAL_TESTS_SHA, 'tests')]:
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Polk frozen numerical ' + label + '/policy fingerprint changed')
    content = model_audit.OUTPUT.read_bytes()
    if len(content) != NUMERICAL_BYTES or hashlib.sha256(content).hexdigest() != NUMERICAL_SHA or not same(numerical, json.loads(content)):
        raise ValueError('Polk complete numerical evidence fingerprint changed')
    if (roster_audit.fingerprint(model_audit.POLICY) != NUMERICAL_POLICY_SHA
            or not same(model_audit.POLICY, numerical['policy'])
            or not same(model_audit.SUBJECTS, [m['subject'] for m in numerical['models']])
            or not same(model_audit.MIN_SCHOOLS, numerical['policy']['minimum_usable_subject_schools'])
            or not same(model_audit.NUMERIC_POLICY_SHA, numerical['numeric_policy_sha256'])
            or not same(model_audit.RUNTIME_CONTRACT_SHA, numerical['runtime_contract_sha256'])
            or any(m['assessment'] != model_audit.ASSESSMENT or m['assessment_standard'] != model_audit.STANDARD
                   for m in numerical['models'])):
        raise ValueError('Polk current numerical policy/definition differs from complete frozen evidence')


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
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 110
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model']
                   or m['coverage']['ten_valid_scored_floor_certified'] is not False for m in numerical['models'])):
        raise ValueError('Polk numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def outcome(link, entry, subject, refs):
    value = link['subjects'][subject]
    index = model_audit.SUBJECT_FIELDS[subject]
    rate = None if entry is None else model_audit.original_rate(entry['raw'][index])
    original = None if entry is None else entry['raw'][index]
    if not same(rate, value['native_rate']) or not same(original, value['raw_rate']):
        raise ValueError('Polk original published rate differs from frozen source audit')
    return dict(proficiency=rate, tested=None, valid_score_evidence=None, raw_tested=None,
        exclusion=value['exclusion'], source='assessment', source_row=0 if entry is None else entry['source_row'],
        raw=dict(applicable=value['applicable'], native_usable=value['usable'], outcome_basis='original_school_grades_published_whole_achievement',
            original_native_rate=original, original_rate_column=index, original_rate_field=model_audit.SUBJECT_LABELS[subject],
            native_outcome=copy.deepcopy(value), native_school_id=link['school_id'],
            source_refs=copy.deepcopy(refs['outcomes'][subject]), complete_source_sha256=model_audit.ROSTER_SHA,
            valid_score_count=None, sampling_variance=None, interval_availability=False,
            ten_valid_scored_floor_certified=False, count_note=COUNT_NOTE))


def build_snapshot(roster, numerical):
    require_frozen_inputs(roster, numerical)
    configurations = set(numerical['frozen_population']['grade_school_configuration_ids'])
    selected_inputs, coverage = model_audit.selected_inputs(roster, 'reading')
    refs_by_id = {r['school_id']: r['source_refs'] for r in selected_inputs}
    refs_by_id.update({r['school_id']: r['source_refs'] for r in coverage['excluded_configuration_records']})
    if set(refs_by_id) != configurations:
        raise ValueError('Polk complete 110-profile roster differs from original selector')
    raw = roster['raw_inputs']
    directory = {e['raw']['NCESSCH']: e['raw'] for e in raw['directory']['records']}
    incomes = {e['source_row']: e['raw'] for e in raw['native_income']['records']}
    assessments = {e['source_row']: e for e in raw['native_assessment']['records']}
    schools = []
    for link in sorted(roster['roster_links'], key=lambda r: r['school_id']):
        key = link['school_id']
        if (key in configurations) is not link['source_profile_eligible']:
            raise ValueError('Polk normalized profile scope differs from immutable source')
        if key not in configurations:
            continue
        refs = refs_by_id[key]; ccd = directory[link['ncessch']]; income = link['income']
        cells = incomes[refs['income']['source_row']]
        n = model_audit.original_count(cells[4])
        components = [model_audit.original_count(cells[i]) for i in [5,6,8]]
        low = None if None in components else sum(components)
        percentage = 100 * low / n if n and low is not None and model_audit.original_count(cells[7]) == 0 else None
        if percentage is None or low > n or not same((percentage,n,low),(income['percentage'],income['survey_enrollment'],income['individual_eligible'])):
            raise ValueError('Polk own February individual eligibility ratio differs from frozen evidence')
        entries = {s:None if refs['outcomes'][s] is None else assessments[refs['outcomes'][s]['source_row']] for s in ['math','reading']}
        schools.append(dict(id=key, ncessch=link['ncessch'], cohort='grade', name=link['name'],
            district_id=roster_audit.LEA, district=ccd['LEA_NAME'], city=ccd['LCITY'] or None, county=None,
            enrollment=n, low_income=low, income=percentage, income_source='income', income_row=refs['income']['source_row'],
            income_raw=dict(individual_income=dict(year=2025, survey='Final Survey 3 February', enrollment=n,
                individual_eligible=low, percentage=percentage, free_D_F=cells[5], reduced_3_E=cells[6],
                provision2_4=cells[7], direct_C_R=cells[8], raw_denominator=cells[4], definition=INCOME_DEFINITION),
                source_refs=copy.deepcopy(refs['income']), complete_source_sha256=model_audit.ROSTER_SHA, valid_score_denominator=False),
            identity_raw=dict(ncessch=link['ncessch'], native_school_id=link['native_school_id'], fdoe_school_id=key,
                source_refs=copy.deepcopy(refs), complete_source_sha256=model_audit.ROSTER_SHA,
                ccd_flags=copy.deepcopy(link['ccd_flags']), offered_evidence=copy.deepcopy(link['offered']),
                native_fall_grade_evidence=copy.deepcopy(link['enrolled']), ccd_membership=copy.deepcopy(link['ccd_membership']),
                native_assessment_flags=copy.deepcopy(link['assessment_flags'])),
            outcomes={s:outcome(link,entries[s],s,refs) for s in ['math','reading']}))
    if len(schools) != 110 or len(numerical['retained_scope_exclusions']) != 60:
        raise ValueError('Polk release requires 110 exact profiles and 60 retained outside CCD records')
    for model in numerical['models']:
        inputs = []
        for school in schools:
            rates = {s:school['outcomes'][s]['proficiency'] for s in ['math','reading']}
            y = (rates['math']+rates['reading'])/2 if model['subject']=='combined' and all(v is not None for v in rates.values()) else rates.get(model['subject'])
            if school['income'] is not None and y is not None:
                inputs.append(dict(school_id=school['id'],ncessch=school['ncessch'],income_pct=school['income'],outcome_pct=y,
                    income_enrollment=school['enrollment'],individual_economic_count=school['low_income']))
        if not same(inputs,[{k:r[k] for k in inputs[0]} for r in model['inputs']]):
            raise ValueError('Polk exact normalized subject inputs differ from audited numerical cohort')
    source_audit = dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),
        complete_numerical_reference=dict(path='data/source/polk-model-audit.json',sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES),
        audit_code_test_references={k:copy.deepcopy(v) for k,v in numerical['sources'].items() if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_polk_models.py',sha256=NUMERICAL_CODE_SHA),tests=dict(path='tests/test_polk_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=model_audit.SOURCE_RAW_SHA, immutable_schema_fingerprint=model_audit.SOURCE_SCHEMA_SHA,
        immutable_definition_fingerprint=model_audit.SOURCE_DEFINITION_SHA, immutable_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA, immutable_numerical_policy_fingerprint=NUMERICAL_POLICY_SHA,
        immutable_numerical_runtime_fingerprint=model_audit.RUNTIME_CONTRACT_SHA, normalized_metadata_fingerprint=ADAPTER_CONTRACT_SHA,
        operational_roster=copy.deepcopy(numerical['source_coverage']), retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),
        retained_outside_source_profiles=copy.deepcopy(numerical['retained_outside_source_profiles']),
        nonoperational_ccd_references=[dict(source_row=e['source_row'],ncessch=e['raw']['NCESSCH'],native_school_id=e['raw']['ST_SCHID'],status=e['raw']['UPDATED_STATUS_TEXT']) for e in roster['nonoperational_directory']],
        subject_coverage={m['subject']:copy.deepcopy(m['coverage']) for m in numerical['models']},
        native_assessment_definition=dict(state='FL',name=ASSESSMENT,original_numerical_name=model_audit.ASSESSMENT,year=2025,level='ES',grades=cohorts()[0]['grades'],standard=STANDARD,source_url=roster_audit.SOURCES['assessment']['url']),
        historical_state_extract=copy.deepcopy(roster['state_extract']),count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_holds=True,minimum_subject_schools=30,
            historical_audits_approved_for_source=False,historical_audits_approved_for_modeling=False,all_models_point_only=True,
            normalized_source_approved=True,district_modeling_approved=True,verified_valid_score_denominators_available=False,
            ten_valid_scored_floor_certified=False,numerical_success_resolves_count_hold=False,
            note='Only this separately validated exact 2024–25 grade-school point-only contract is approved. Historical source and numerical audits retain false approvals. Compact links require all current immutable artifacts/code/tests/policies and semantic replay. High, mixed, primary, closed, unmatched scopes and valid-score/count-floor holds remain unreleased.'))
    selection = dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),
        directory_school_ids=[s['id'] for s in schools],subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],school_ids=[r['school_id'] for r in m['inputs']],population_sha256=m['population_sha256']) for m in numerical['models']})
    selection['sha256'] = roster_audit.fingerprint(selection)
    sources = copy.deepcopy(roster['sources'])
    sources['historical_florida_extract'] = dict(path=roster['state_extract']['path'],url=PROJECT_SOURCE+roster['state_extract']['path'],sha256=roster['state_extract']['sha256'])
    for key,path,digest in [('roster_audit','data/source/polk-district-audit.json',model_audit.ROSTER_SHA),
        ('numerical_audit','data/source/polk-model-audit.json',NUMERICAL_SHA),
        ('source_audit_code','scripts/audit_polk.py',model_audit.SOURCE_CODE_SHA),('source_audit_tests','tests/test_polk_audit.py',model_audit.SOURCE_TESTS_SHA),
        ('numerical_audit_code','scripts/audit_polk_models.py',NUMERICAL_CODE_SHA),('numerical_audit_tests','tests/test_polk_models.py',NUMERICAL_TESTS_SHA)]:
        sources[key] = dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note = (
        'Polk independent district comparison, 2024–25. All 110 audited grade-school profiles are searchable with '
        'individual February income; 109 Math, ELA and Combined results enter separate fixed district models. One '
        'profile, Compass Middle Charter School, has no published achievement and retains missing results. Native whole-percent FAST PM3, '
        'BEST/Access EOC and eligible FAA achievement retains full-year, home-zoned, ELL and exemption rules; '
        'Datafolio and percent-tested participation remain separate. February income, Fall/CCD enrollment and '
        'accountable assessment dates/populations differ. The source retains 170 CCD records, 60 outside the '
        'released scope, including six operational campuses without native Fall records; enrollment differences '
        'do not establish their causes. Valid-score counts and the ten-valid-scored floor remain uncertified; '
        'sampling intervals are unavailable modelwide. Admissions, provider roles, programs, coordinates and '
        'boundaries remain unaudited; one year only.')
    shifts = '; '.join(('ELA' if m['subject']=='reading' else m['subject'].title())+' '+format(m['diagnostics']['maximum_prediction_change_on_observed_income_range'],'.6f') for m in numerical['models'])
    details = [MODEL_SCOPE,
        'Three separate unweighted OLS fits reproduce all 327 audited results and explicit deleted fits. Combined '
        'independently fits the equal mean of original Math and ELA rates, with its own residual scale and studentization. '
        'Equal cohorts permit coefficient linearity but never averaging studentized scores. Filters never refit models. '
        'Associations do not establish causal effectiveness or overall quality.',
        'School Grades publishes whole percentages proficient at Level 3 or above. FAST PM3 ELA, FAST/BEST/Access '
        'Math and eligible FAA performance retain original course, full-year/home-zoned accountability, ELL and '
        'exemption rules. Below-grade-3 pupils testing above grade may enter native ELA achievement. Datafolio '
        'participation belongs only to percent tested. Component percentages are not averaged or rebuilt from counts.',
        INCOME_DEFINITION,
        'February income and Fall membership use different dates and all school grades. CCD district enrollment '
        '111,372 is below the operational school sum 116,440 by 5,068. Different reporting populations do not prove '
        'the cause of this gap and never substitute for each school’s own February income denominator.',
        COUNT_NOTE+' Studentization uses the deleted-school residual scale and N−3 degrees of freedom; it supplies '
        'no enrollment adjustment or shrinkage. Protected counts and missing achievement remain unavailable, never zero.',
        'Full and all 327 deleted designs have rank two and finite positive scales. Largest deleted prediction changes '
        'over observed incomes: '+shifts+' percentage points. All 19 rated charters, observed income extremes and '
        'influential Cypress Junction Montessori remain included. Diagnostic flags never exclude a school or clamp predictions.',
        'The complete source retains 2,026 original records, 48,356 typed cells, original headers, notes and primary '
        'definitions. Linked source references preserve the original school identities, income components, published '
        'rates and excluded records so the comparison can be checked against its sources.',
        'Compass Middle Charter School has missing published Math and ELA and remains searchable. High, mixed, primary, closed and unmatched '
        'records remain outside the 110 released profiles. Programs are Unclassified; admissions, provider roles, '
        'coordinates and boundaries remain unknown. One year only; incompatible thresholds and income definitions '
        'cannot produce a common national ranking.']
    return dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',state=dict(id='FL',name='Florida'),
        name='Polk 2024–25 FAST/BEST/FAA School Grades district comparison',region='polk',region_name='Polk',statewide=False,
        comparison='Polk · {year} · {assessment} · {note}',prepare_script='scripts/prepare_polk.py',
        source_url=roster_audit.SOURCES['assessment']['url'],retrieved='2026-10-14',model_scope=MODEL_SCOPE,
        release_status='ready',approved_for_source=True,approved_for_modeling=True,
        map_source='School coordinates and district boundaries are unavailable in the audited Polk source release.',
        income_definition=dict(label=INCOME_LABEL,definition=INCOME_DEFINITION,url=roster_audit.SOURCES['lunch-guide']['url']),
        sources=sources,cohorts=cohorts(),schools=schools,selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Polk independent FAST/BEST/FAA School Grades grade-school models with individual February income; valid-score counts and ten-valid-scored floor uncertified, sampling intervals unavailable.',
            details=details,sources=[dict(label=label,url=sources[key]['url']) for key,label in [
                ('assessment','FDOE 2024–25 School Grades original achievement'),('grades','FDOE Fall Survey 2 grade membership'),
                ('income','FDOE Final Survey 3 February individual lunch status'),('grade-guide','FDOE 2024–25 School Grades calculation guide'),
                ('lunch-guide','FDOE original lunch-status definition'),('ccd_school_directory','CCD exact 2024–25 school roster'),
                ('ccd_school_membership','CCD same-year school membership'),('ccd_lea_directory','CCD exact district identity'),
                ('ccd_lea_membership','CCD same-year district membership')]]))


def build():
    return build_snapshot(*load_inputs())


def validate(payload, expected=None):
    # Cached normalized expectations never bypass complete immutable linked evidence.
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical)
    expected = build() if expected is None else expected
    if not same(payload,expected):
        raise ValueError('Polk normalized extract differs from pinned source/model evidence, scope or selection policy')
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
        if not same(datasets, [dict(id=DATASET, state='FL', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Polk canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Polk canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='FL', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Polk canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Florida's independent statewide release and other dataset-composite namespaces.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 110 or len(economic_rows) != 110 or len(observation_rows) != 220:
            raise ValueError('Polk canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Polk canonical profile/observation membership changed')
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
                raise ValueError('Polk canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=None,
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=None, source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Polk canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Polk canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                assessed_schools=110, excluded_schools=110 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Polk canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Polk canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']), low=None, high=None)
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Polk canonical point-only result differs from audited district fit')
            total += len(saved)
        if total != 327 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Polk canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Polk canonical foreign-key integrity failed')
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
    if (len(schools['schools']) != 110 or len(history['records']) != 110
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Polk exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Polk export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Polk history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Polk historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                              assessed_schools=110, excluded_schools=110 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Polk exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Polk exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=None, cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'low', 'high', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Polk per-school point-only metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Polk profile/history subject set differs from exact audited eligibility')
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
            raise ValueError('Polk profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 110, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=110, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Polk exported coverage/source exclusions differ from approved selection')
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
        raise ValueError('Polk exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='polk', geography='polk', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Polk ready descriptor must retain distinct district and point-only scope')
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

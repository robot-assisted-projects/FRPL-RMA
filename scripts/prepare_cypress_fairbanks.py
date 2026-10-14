"""Canonical and static Cypress-Fairbanks ISD comparisons linked to complete immutable audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path

import audit_cypress_fairbanks as roster_audit
import audit_cypress_fairbanks_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot

DATASET = 'tx-cypress-fairbanks-2025'
EXTRACT = ROOT / 'data/source/cypress-fairbanks.json'
OUTPUT = ROOT / 'data/cypress-fairbanks'
NUMERICAL_SHA = '32c6593c2171eb31eefbc9bca37a192e514cdb83cec06555c55505cbeb8305b3'
NUMERICAL_BYTES = 490919
NUMERICAL_POLICY_SHA = '7eddf7fba55ab8030ae89afdc375ef80401e763904c13e2f499cefb59d868763'
NUMERICAL_CODE_SHA = 'e5303e2c516977814e6238770537c8861e49a11af0901ef375e1a69c0d4547dc'
NUMERICAL_TESTS_SHA = '9b152770de56f5f4e7aba2d57bb5df0a349587847dc654dbb252e9aadf1cae66'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':78, 'reading':78, 'combined':78}
MODEL_SCOPE = (
    'Cypress-Fairbanks ISD independent 2024–25 published-rate grade-school district models use exact '
    'operational CCD LEA 4816110 / TX-101907 / TAPR district 101907 identities. All 78 native enrolled '
    'positive grades 3–8/no-high-grade profiles remain searchable and enter each separate Math, ELA '
    'and Combined model using original whole-percent All Students Meets or Above rates and precise '
    'same-year individual economic-status enrollment ratios. Thirteen high schools, one primary campus '
    'and two operational alternative campuses without native records remain outside this point-only '
    'release. Valid-score count scope and the ten-valid-scored floor remain uncertified; sampling '
    'intervals are unavailable modelwide.')
COUNT_NOTE = (
    'Valid-score count scope and the ten-valid-scored floor remain uncertified. Native '
    'reported performance #Tests, enrollment, PEIMS/CCD membership, participation and '
    'federal 95%-rule counts never substitute for valid-score denominators. All valid-score counts, '
    'sampling variances and interval endpoints are null; sampling intervals unavailable.')


def same(actual, expected):
    """Typed exact evidence equality; Python bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual) == roster_audit.fingerprint(expected)


INCOME_LABEL = 'Individually classified economic disadvantage'
INCOME_NOTE = (
    'Individual October 25, 2024 PEIMS fall economic status uses each school’s own count of '
    'individually classified economically disadvantaged pupils divided by its own all-enrolled '
    'EE–12 count. State codes '
    '01/02/99 include free or reduced-price meal eligibility or other public assistance. '
    'ED plus non-ED and the native tenth-percent display must reconcile. This broader '
    'state-specific proxy is not uniform FRPL or household income and does not exactly '
    'describe the tested pupils.')
INCOME_COVERAGE_NOTE = (
    'CEP requires individual direct certification and annual local income surveys; universal '
    'meals do not classify all children. Provision 2 may retain base-year eligibility for '
    'continuously enrolled students. Missing surveys may yield code 00; identification '
    'coverage and undercount are unknown. The January 16, 2025 resubmission extension '
    'requires enrollment and eligibility on October 25, 2024, without another-year backfill.')
INCOME_DEFINITION = INCOME_NOTE+' '+INCOME_COVERAGE_NOTE
ASSESSMENT_NOTE = (
    'Original 2024–25 All Students TAPR rates cover enrolled grades 3–8 Math and ELA Including '
    'EOC at Meets Grade Level or Above. Native #Tests and #Meets-or-above remain unverified '
    'reported evidence. The accountability subset requires the same district and campus on '
    'the fall snapshot and testing date. STAAR with or without accommodations, Spanish '
    'STAAR, Alternate 2 and applicable Algebra I and English I–II EOC are included as '
    'documented. Separate TPRS all-testers, both-subject passing and participation measures '
    'are not used.')

ADAPTER_CONTRACT_SHA = 'd745e43322b141be2318ad7af49cd03a469dbe264b63db90f3dde00e49581d70'


def adapter_contract():
    return dict(dataset=DATASET, expected_n=EXPECTED_N, model_scope=MODEL_SCOPE,
        count_note=COUNT_NOTE, cohort_metadata=cohorts(),
        income_label=INCOME_LABEL,income_definition=INCOME_DEFINITION,
        income_note=INCOME_NOTE,income_coverage_note=INCOME_COVERAGE_NOTE,assessment_note=ASSESSMENT_NOTE)


def require_frozen_inputs(roster, numerical):
    """All six immutable audit/code/test pins and current semantics precede writes."""
    model_audit.require_runtime_contract()
    original_adapter = 'd745e43322b141be2318ad7af49cd03a469dbe264b63db90f3dde00e49581d70'
    if ADAPTER_CONTRACT_SHA != original_adapter or roster_audit.fingerprint(adapter_contract()) != original_adapter:
        raise ValueError('Cypress-Fairbanks current normalized population/assessment/income/count contract changed')
    public_pins = dict(sha256=NUMERICAL_SHA, bytes=NUMERICAL_BYTES, policy=NUMERICAL_POLICY_SHA,
        code=NUMERICAL_CODE_SHA, tests=NUMERICAL_TESTS_SHA)
    immutable_pins = {'sha256': '32c6593c2171eb31eefbc9bca37a192e514cdb83cec06555c55505cbeb8305b3', 'bytes': 490919, 'policy': '7eddf7fba55ab8030ae89afdc375ef80401e763904c13e2f499cefb59d868763', 'code': 'e5303e2c516977814e6238770537c8861e49a11af0901ef375e1a69c0d4547dc', 'tests': '9b152770de56f5f4e7aba2d57bb5df0a349587847dc654dbb252e9aadf1cae66'}
    if not same(public_pins, immutable_pins):
        raise ValueError('Cypress-Fairbanks complete immutable numerical pin/strict byte-size contract changed')
    model_audit.require_frozen_roster(roster)
    for path, expected, label in [('scripts/audit_cypress_fairbanks_models.py',NUMERICAL_CODE_SHA,'code'),
        ('tests/test_cypress_fairbanks_models.py',NUMERICAL_TESTS_SHA,'tests')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Cypress-Fairbanks frozen numerical '+label+'/policy fingerprint changed')
    content=model_audit.OUTPUT.read_bytes()
    if len(content)!=NUMERICAL_BYTES or hashlib.sha256(content).hexdigest()!=NUMERICAL_SHA or not same(numerical,json.loads(content)):
        raise ValueError('Cypress-Fairbanks complete numerical evidence fingerprint changed')
    if (not same(model_audit.POLICY,numerical['policy'])
        or not same(model_audit.SUBJECTS,[m['subject']for m in numerical['models']])
        or not same(model_audit.MIN_SCHOOLS,numerical['policy']['minimum_usable_subject_schools'])
        or not same(model_audit.NUMERIC_POLICY_SHA,numerical['sources']['numerical_policy_sha256'])
        or not same(model_audit.RUNTIME_CONTRACT_SHA,numerical['sources']['numerical_runtime_sha256'])
        or any(m['assessment']!=model_audit.ASSESSMENT or m['assessment_standard']!=model_audit.STANDARD for m in numerical['models'])):
        raise ValueError('Cypress-Fairbanks current numerical policy/definition differs from frozen evidence')


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
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 78
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model']
                   or m['coverage']['ten_valid_scored_floor_certified'] is not False
                   for m in numerical['models'])):
        raise ValueError('Cypress-Fairbanks ISD numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def cohorts():
    return [dict(id='grade', level='ES', assessment=model_audit.ASSESSMENT,
        label='Grade schools · enrolled grades 3–8 Including EOC',
        grades='Enrolled grades 3–8, including applicable Algebra I and English I–II EOC',
        standard=model_audit.STANDARD, source_url=roster_audit.SOURCES['assessment']['url'],
        source='assessment', allow_point_only=True,
        outcome='Meets Grade Level or Above · published whole percentages',
        note='Cypress-Fairbanks independent published-rate district models · original whole-percent rates · '
             'individual fall economic status · valid-score count scope and ten-valid-scored floor '
             'uncertified · sampling intervals unavailable')]


def outcome(school, entry, subject, refs):
    value = school['subjects'][subject]
    return dict(proficiency=value['published_rate'], tested=None, valid_score_evidence=None,
        raw_tested=None, exclusion=value['exclusion'], source='assessment', source_row=entry['source_row'],
        raw=dict(applicable=value['applicable'], native_usable=value['source_usable'],
            outcome_basis='original_published_whole_percent_R',
            original_subject_triplet={f:entry['raw'][f] for f in roster_audit.FIELDS[subject]},
            original_rate_field=roster_audit.FIELDS[subject][2],
            unverified_reported_subject_evidence=copy.deepcopy(value),
            native_school_id=school['native_school_id'], source_refs=copy.deepcopy(refs),
            complete_source_sha256=model_audit.ROSTER_SHA,
            valid_score_count=None, sampling_variance=None, interval_availability=False,
            ten_valid_scored_floor_certified=False, count_note=COUNT_NOTE))


def build_snapshot(roster, numerical):
    require_frozen_inputs(roster, numerical)
    raw = roster['raw_inputs']
    directory = {roster_audit.ccd_identity(r['raw'])[0]:r for r in raw['directory']['records']}
    by_table = {t:{roster_audit.native_identity(r['raw']):r for r in raw[t]['records']}
                for t in ['ref','stud','assessment']}
    configurations = set(numerical['frozen_population']['grade_school_configuration_ids'])
    schools = []
    for school in sorted(roster['roster_links'], key=lambda r:r['school_id']):
        key,native = school['school_id'],school['native_school_id']
        if key not in configurations:
            continue
        profile = directory[key]['raw']; income = school['income']
        student,assessment,reference = [by_table[t][native] for t in ['stud','assessment','ref']]
        refs = model_audit.source_references(roster,school,by_table)
        schools.append(dict(id=key,ncessch=key,cohort='grade',name=profile['SCH_NAME'],
            district_id=roster_audit.LEA,district=reference['raw']['DISTNAME'],city=None,
            county=reference['raw']['CNTYNAME'],enrollment=income['enrollment'],
            low_income=income['economic_disadvantage'],income=income['percentage'],
            income_source='stud',income_row=student['source_row'],
            income_raw=dict(individual_income=copy.deepcopy(income),source_refs=copy.deepcopy(refs),
                complete_source_sha256=model_audit.ROSTER_SHA),
            identity_raw=dict(ncessch=key,native_school_id=native,
                ccd_native_school_id=school['ccd_native_school_id'],
                source_refs=copy.deepcopy(refs),complete_source_sha256=model_audit.ROSTER_SHA,
                ccd_flags=copy.deepcopy(school['ccd_flags']),native_enrolled_scope=school['native_enrolled']['scope'],
                original_grade_fields=copy.deepcopy(school['native_enrolled']['raw_grade_counts']),
                native_reference=copy.deepcopy(school['native_reference']),
                ccd_membership_total=school['ccd_membership']['reported_total'],
                native_peims_membership=copy.deepcopy(school['native_peims_membership'])),
            outcomes={s:outcome(school,assessment,s,refs) for s in ['math','reading']}))
    if len(schools)!=78 or len(numerical['retained_scope_exclusions'])!=16:
        raise ValueError('Cypress-Fairbanks ISD release requires 78 exact grade-school configurations and 16 outside records')
    source_audit = dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),
        complete_numerical_reference=dict(path='data/source/cypress-fairbanks-model-audit.json',sha256=NUMERICAL_SHA),
        audit_code_test_references={k:copy.deepcopy(v) for k,v in numerical['sources'].items()
            if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_cypress_fairbanks_models.py',sha256=NUMERICAL_CODE_SHA),
            tests=dict(path='tests/test_cypress_fairbanks_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=roster_audit.RAW_INPUT_SHA,
        immutable_schema_fingerprint=roster_audit.ORIGINAL_SCHEMA_SHA,
        immutable_definition_fingerprint=roster_audit.DEFINITION_INPUT_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA,
        immutable_source_runtime_fingerprint=model_audit.SOURCE_RUNTIME_SHA,
        immutable_source_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_secondary_texas_fingerprint=model_audit.SOURCE_SECONDARY_SHA,
        immutable_numerical_policy_fingerprint=model_audit.NUMERIC_POLICY_SHA,
        immutable_numerical_runtime_fingerprint=model_audit.RUNTIME_CONTRACT_SHA,
        operational_roster=copy.deepcopy(roster['coverage']),
        retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),
        subject_coverage={m['subject']:copy.deepcopy(m['coverage']) for m in numerical['models']},
        native_assessment_definition=dict(state='TX',name=model_audit.ASSESSMENT,year=2025,level='ES',
            grades=cohorts()[0]['grades'],standard=model_audit.STANDARD,source_url=roster_audit.SOURCES['assessment']['url']),
        enrollment_reconciliation=copy.deepcopy(roster['enrollment_reconciliation']),
        historical_state_consistency=copy.deepcopy(roster['historical_state_consistency']),
        count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_holds=True,
            minimum_subject_schools=30,historical_audits_approved_for_source=False,
            historical_audits_approved_for_modeling=False,all_models_point_only=True,
            normalized_source_approved=True,district_modeling_approved=True,
            verified_valid_score_denominators_available=False,ten_valid_scored_floor_certified=False,
            numerical_success_resolves_count_hold=False,
            note='Only this separate exact same-year enrolled-grade point-only contract is approved. Complete original source and numerical audits remain immutable with false historical approvals; compact references require both artifacts and code/test/policy pins on every replay. Count, high/mixed/primary and nonoperational holds remain.'))
    selection = dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),
        directory_school_ids=[r['id'] for r in schools],
        subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],
            school_ids=[r['school_id'] for r in m['inputs']],population_sha256=m['population_sha256']) for m in numerical['models']})
    selection['sha256'] = roster_audit.fingerprint(selection)
    sources = copy.deepcopy(roster['sources'])
    sources.update(roster_audit=dict(path='data/source/cypress-fairbanks-district-audit.json',
        url=PROJECT_SOURCE+'data/source/cypress-fairbanks-district-audit.json',sha256=model_audit.ROSTER_SHA),
        numerical_audit=dict(path='data/source/cypress-fairbanks-model-audit.json',
        url=PROJECT_SOURCE+'data/source/cypress-fairbanks-model-audit.json',sha256=NUMERICAL_SHA))
    for key,path,digest in [('source_audit_code','scripts/audit_cypress_fairbanks.py',model_audit.SOURCE_CODE_SHA),
        ('source_audit_tests','tests/test_cypress_fairbanks_audit.py',model_audit.SOURCE_TESTS_SHA),
        ('numerical_audit_code','scripts/audit_cypress_fairbanks_models.py',NUMERICAL_CODE_SHA),
        ('numerical_audit_tests','tests/test_cypress_fairbanks_models.py',NUMERICAL_TESTS_SHA)]:
        sources[key]=dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note = (
        'Cypress-Fairbanks ISD independent district comparison, 2024–25: all 78 audited enrolled '
        'grades 3–8/no-high-grade profiles enter each separate Math, ELA and Combined model. Exact '
        'CCD LEA 4816110 / TX-101907 / TAPR 101907 crosswalks bind native campuses to NCES identities. '
        'The complete linked audit retains all 94 operational CCD schools and 92 native campuses, '
        'including 13 high schools, one primary-only campus and two alternative CCD campuses without '
        'any native REF, enrollment or assessment record. Those gaps stay missing, never zero or '
        'name-matched. Outcomes are original whole-percent All Students Meets or Above enrolled '
        'grades 3–8 Including EOC, with STAAR, Spanish and Alternate 2. Income uses precise October '
        '25, 2024 individual economic-status counts divided by native enrollment, broader than '
        'uniform FRPL and tested pupils. Valid-score count scope and the ten-valid-scored floor '
        'remain uncertified; sampling intervals unavailable modelwide. Admissions, provider roles, '
        'programs, coordinates and boundaries remain unaudited; one year only.')
    details = [MODEL_SCOPE,
        'Separate unweighted district OLS and externally studentized residuals retain all 78 eligible schools per subject and all 234 explicit deleted fits. Combined is the equal mean of original Math and ELA whole percentages with its own fit, deleted residual scale and studentization, not proficiency in both or averaged subject residuals. Filters never refit; statewide and other district fits are never reused. Associations do not establish causal school effectiveness or overall quality.',
        model_audit.POLICY['eligibility'],model_audit.POLICY['outcome'],
        INCOME_NOTE,INCOME_COVERAGE_NOTE,ASSESSMENT_NOTE,
        'All 92 native campuses reconcile individual ED plus non-ED with native enrollment. Native enrollment and CCD school/LEA totals are 117,927; separate PEIMS membership totals 117,658 and differs at 72 campuses. These concepts remain distinct; differences do not prove a cause or furnish tested denominators.',
        'All 78 Math and ELA published whole-percent rates differ from unverified reported-count ratios. Counts never supply more precise outcomes, certify score status, screen membership or complete missing cells. Operational alternative campuses 101907006/NCES 481611008601 and 101907014/NCES 481611012265 have no original native rows and remain outside the 78-profile comparison, with complete CCD evidence linked.',
        COUNT_NOTE+' Studentization uses each deleted-school residual scale and N−3 degrees of freedom, without enrollment adjustment or shrinkage. Exact 2025 N/NAAR and M/medical scope remains unresolved; this release does not certify a ten-valid-scored minimum.',
        'Full and all deleted designs have rank two and finite positive residual scales. Every observed income endpoint and influential member remains included. Hairgrove has the highest Cook distance in each model and remains eligible. OLS predictions are not clamped; leverage, Cook distance and residual flags are descriptive only.',
        'The complete immutable source audit retains all 1,107 original records, 42,828 typed cells, complete native headers and primary definitions. Compact evidence preserves exact original rows and fields plus the six historical audit/code/test pins. The full source and numerical evidence must remain available and unchanged on every replay and import. Historical approvals remain false; only this separately validated grade-school contract is released.',
        'One year only; programs are Unclassified and admissions, provider roles, map coordinates and district boundaries remain unknown. Varying grade and assessment mixes, rounded displays, broader fall economic status and omitted prior attainment or admissions remain limitations. State thresholds and income proxies do not create a common national ranking.']
    return dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',
        state=dict(id='TX',name='Texas'),name='Cypress-Fairbanks ISD 2024–25 published-rate district comparison',
        region='cypress-fairbanks',region_name='Cypress-Fairbanks ISD',statewide=False,
        comparison='Cypress-Fairbanks ISD · {year} · {assessment} · {note}',prepare_script='scripts/prepare_cypress_fairbanks.py',
        source_url=roster_audit.SOURCES['assessment']['url'],retrieved='2026-10-13',
        model_scope=MODEL_SCOPE,release_status='ready',approved_for_source=True,approved_for_modeling=True,
        map_source='School coordinates and district boundaries are unavailable in the audited Cypress-Fairbanks ISD source release.',
        income_definition=dict(label=INCOME_LABEL,
            definition=INCOME_DEFINITION,
            url=roster_audit.SOURCES['income-guide']['url']),sources=sources,cohorts=cohorts(),schools=schools,
        selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Cypress-Fairbanks ISD independent original published-rate grade-school district models with precise same-year individual economic status; valid-score count scope and ten-valid-scored floor uncertified, sampling intervals unavailable.',
            details=details,sources=[dict(label=label,url=sources[key]['url']) for key,label in [
                ('assessment','TEA original 2024–25 enrolled-grade TAPR rates'),
                ('dictionary','TEA native performance field dictionary'),('stud','TEA enrolled grades and individual economic status'),
                ('ref','TEA campus/district identities'),('glossary','TAPR accountable population and assessment definitions'),
                ('income-guide','Individual economic status reporting rules'),('income-extension','Same-year verification extension'),
                ('accountability-manual','2025 Accountability Manual'),('performance-listing','STAAR performance/participation listing'),
                ('directory','CCD exact same-year school roster'),('membership','CCD supplemental membership')]]))


def build():
    return build_snapshot(*load_inputs())


def validate(payload, expected=None):
    # Cached normalized expectations never bypass complete immutable linked evidence.
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical)
    expected = build() if expected is None else expected
    if not same(payload,expected):
        raise ValueError('Cypress-Fairbanks ISD normalized extract differs from pinned source/model evidence, scope or selection policy')
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
        if not same(datasets, [dict(id=DATASET, state='TX', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Cypress-Fairbanks ISD canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Cypress-Fairbanks ISD canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='TX', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Cypress-Fairbanks ISD canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Texas's independent statewide release.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 78 or len(economic_rows) != 78 or len(observation_rows) != 156:
            raise ValueError('Cypress-Fairbanks ISD canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Cypress-Fairbanks ISD canonical profile/observation membership changed')
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
                raise ValueError('Cypress-Fairbanks ISD canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=None,
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=None, source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Cypress-Fairbanks ISD canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Cypress-Fairbanks ISD canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=model_audit.ASSESSMENT, subject=subject,
                assessed_schools=78, excluded_schools=78 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Cypress-Fairbanks ISD canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Cypress-Fairbanks ISD canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']), low=None, high=None)
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Cypress-Fairbanks ISD canonical point-only result differs from audited district fit')
            total += len(saved)
        if total != 234 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Cypress-Fairbanks ISD canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Cypress-Fairbanks ISD canonical foreign-key integrity failed')
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
    if (len(schools['schools']) != 78 or len(history['records']) != 78
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Cypress-Fairbanks ISD exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Cypress-Fairbanks ISD export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', model_audit.ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Cypress-Fairbanks ISD history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Cypress-Fairbanks ISD historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=model_audit.ASSESSMENT, subject=subject,
                              assessed_schools=78, excluded_schools=78 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Cypress-Fairbanks ISD exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Cypress-Fairbanks ISD exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=None, cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'low', 'high', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Cypress-Fairbanks ISD per-school point-only metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Cypress-Fairbanks ISD profile/history subject set differs from exact audited eligibility')
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
            assessment=model_audit.ASSESSMENT, name=profile['name'], income=profile['income'],
            enrollment=None if profile['enrollment'] is None else float(profile['enrollment']), income_label=payload['income_definition']['label'],
            exclusions=expected_exclusions)
        if (set(school) != set(profile_fields) | {'id', 'metrics', 'history'}
                or set(record) != set(record_fields) | {'school_id', 'subjects'}
                or not same({k: school.get(k) for k in profile_fields}, profile_fields)
                or not same({k: record.get(k) for k in record_fields}, record_fields)
                or not same(school['history'], [record])):
            raise ValueError('Cypress-Fairbanks ISD profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 78, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=78, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Cypress-Fairbanks ISD exported coverage/source exclusions differ from approved selection')
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
        raise ValueError('Cypress-Fairbanks ISD exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='cypress-fairbanks', geography='cypress-fairbanks', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Cypress-Fairbanks ISD ready descriptor must retain distinct district and point-only scope')
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

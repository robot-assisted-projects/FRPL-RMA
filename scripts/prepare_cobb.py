"""Canonical/static Cobb Georgia Milestones EOG comparison linked to immutable point-only audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import audit_cobb as roster_audit
import audit_cobb_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot
DATASET = 'ga-cobb-2025'
EXTRACT = ROOT / 'data/source/cobb.json'
OUTPUT = ROOT / 'data/cobb'
NUMERICAL_SHA = 'ed7bb059531f0d91ddeb959a0b1e54823d50d8aeb3582ed9a7e481f9e2e03bc6'
NUMERICAL_BYTES = 1176631
NUMERICAL_POLICY_SHA = '6b25f52709fdd3a73f77bee7f0078ca4049e6049787dca7f689baea107a1575b'
NUMERICAL_CODE_SHA = '43f8e35e91b0224b799db1e828ae08aa42563fad3e9ddce4d89d2d4a1ebe9427'
NUMERICAL_TESTS_SHA = '9313aef79bf223198d1b35b2481fd397f87e91d0c4896db4130c2bc81ad23230'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':90,'reading':90,'combined':90}
ASSESSMENT = 'Georgia Milestones EOG regular All Students G38 proficiency'
STANDARD = model_audit.STANDARD
MODEL_SCOPE = (
    'Cobb County independent 2024–25 grade-school models use exact NCES LEA 1301290 / native GA-633 identities. '
    'All 90 operational pure lower offered and reconciled enrolled grade profiles remain searchable, with separate '
    'fixed 90-school Math, ELA and Combined models. Outcomes use original regular Georgia Milestones EOG All Students '
    'G38 Levels 3–4 published rates; income uses each school’s own reported individual direct certification divided '
    'by reported same-year membership. Primary-only, high and mixed configurations remain outside. Income extremes '
    'and influence remain included. Georgia Medicaid/foster certification and outside-program prekindergarten '
    'membership are broader population limits. Accelerated EOG/EOC coverage, nonlisted attribution completeness, '
    'valid-score counts and the ten-valid-scored floor remain uncertified; sampling intervals are unavailable.')
COUNT_NOTE = (
    'Original EDC tested and performance-level counts remain unverified valid-score denominators and may be '
    'constructed from other source information. Own CCD membership, direct certification, participation and federal '
    '95%-rule counts never substitute. All valid-score counts, sampling variances and interval endpoints are null '
    'modelwide; the ten-valid-scored floor remains uncertified.')
INCOME_LABEL = 'Reported individual direct certification / school membership'
INCOME_DEFINITION = (
    '2024–25 reported CCD Final 2a individual Direct Certification Education Unit Total divided by that school’s '
    'own reported same-year Membership Education Unit Total, including pre-K where enrolled. Original Georgia notes '
    'say Medicaid income was added to SNAP/TANF certification starting in 2024 and foster records were received. '
    'Membership covers state-funded programs and includes prekindergarten pupils in outside programs. This benefit '
    'and status measure is an economic disadvantage proxy, not full household-income FRPL or universal/CEP meal '
    'receipt. Both counts require Reported flags; masks, missing or derived counts, other-year income and tested '
    'subgroup denominators never substitute. Reporting coverage and completeness are unknown.')
ADAPTER_CONTRACT_SHA = '7fa34ec31ebec043798a4d4cf952f77cbd2ad66975c2173e9fd69ea6ea13d8d6'
NORMALIZED_PAYLOAD_SHA = '308af3ca1022e7e22cd9c815850706c6f37958426536faba9d5a059422199ac8'

def same(actual,expected):
    """Typed exact evidence equality; bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual)==roster_audit.fingerprint(expected)

def cohorts():
    return [dict(id='grade',level='ES',assessment=ASSESSMENT,label='Grade schools · Georgia Milestones regular EOG G38',
        grades='Operational pure lower offered and reconciled enrolled profiles with positive reported grades 3–8; native regular EOG All Students G38',
        standard=STANDARD,source_url=roster_audit.SOURCES['edc_2025']['url'],source='edc_2025',allow_point_only=True,
        outcome='Proficient · Levels 3–4',note='Cobb County independent district models · reported individual direct certification '
            'and own membership · accelerated EOG/EOC coverage, valid-score counts and floor uncertified · sampling intervals unavailable')]


def adapter_contract():
    return dict(dataset=DATASET,extract_path=str(EXTRACT.relative_to(ROOT)),default_output=str(OUTPUT.relative_to(ROOT)),project_source=PROJECT_SOURCE,expected_n=EXPECTED_N,assessment=ASSESSMENT,standard=STANDARD,model_scope=MODEL_SCOPE,
        count_note=COUNT_NOTE,income_label=INCOME_LABEL,income_definition=INCOME_DEFINITION,cohort_metadata=cohorts())

def require_frozen_inputs(roster, numerical):
    """Current semantic contracts and all six complete audit/code/test pins precede every write."""
    model_audit.require_runtime_contract()
    original_adapter = '7fa34ec31ebec043798a4d4cf952f77cbd2ad66975c2173e9fd69ea6ea13d8d6'
    if ADAPTER_CONTRACT_SHA != original_adapter or roster_audit.fingerprint(adapter_contract()) != original_adapter:
        raise ValueError('Cobb County current normalized population/assessment/income/typed metadata contract changed')
    if NORMALIZED_PAYLOAD_SHA != '308af3ca1022e7e22cd9c815850706c6f37958426536faba9d5a059422199ac8':
        raise ValueError('Cobb immutable normalized fingerprint alias changed')
    public_pins = dict(sha256=NUMERICAL_SHA, bytes=NUMERICAL_BYTES, policy=NUMERICAL_POLICY_SHA,
                       code=NUMERICAL_CODE_SHA, tests=NUMERICAL_TESTS_SHA)
    immutable_pins = dict(sha256='ed7bb059531f0d91ddeb959a0b1e54823d50d8aeb3582ed9a7e481f9e2e03bc6', bytes=1176631,
        policy='6b25f52709fdd3a73f77bee7f0078ca4049e6049787dca7f689baea107a1575b',
        code='43f8e35e91b0224b799db1e828ae08aa42563fad3e9ddce4d89d2d4a1ebe9427',
        tests='9313aef79bf223198d1b35b2481fd397f87e91d0c4896db4130c2bc81ad23230')
    if not same(public_pins, immutable_pins):
        raise ValueError('Cobb County complete immutable numerical pin/strict byte-size contract changed')
    model_audit.require_frozen_roster(roster)
    for path, expected, label in [('scripts/audit_cobb_models.py', NUMERICAL_CODE_SHA, 'code'),
                                 ('tests/test_cobb_models.py', NUMERICAL_TESTS_SHA, 'tests')]:
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Cobb County frozen numerical ' + label + '/policy fingerprint changed')
    content = model_audit.OUTPUT.read_bytes()
    if len(content) != NUMERICAL_BYTES or hashlib.sha256(content).hexdigest() != NUMERICAL_SHA or not same(numerical, json.loads(content)):
        raise ValueError('Cobb County complete numerical evidence fingerprint changed')
    if (roster_audit.fingerprint(model_audit.POLICY) != NUMERICAL_POLICY_SHA
            or not same(model_audit.POLICY, numerical['policy'])
            or not same(model_audit.SUBJECTS, [m['subject'] for m in numerical['models']])
            or not same(model_audit.MIN_SCHOOLS, numerical['policy']['minimum_usable_subject_schools'])
            or not same(model_audit.NUMERIC_POLICY_SHA, numerical['numeric_policy_sha256'])
            or not same(model_audit.RUNTIME_CONTRACT_SHA, numerical['runtime_contract_sha256'])
            or any(m['assessment'] != model_audit.ASSESSMENT or m['assessment_standard'] != model_audit.STANDARD
                   for m in numerical['models'])):
        raise ValueError('Cobb County current numerical policy/definition differs from complete frozen evidence')


def load_inputs():
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster, numerical)
    model_audit.validate(numerical)
    if (numerical['hard_holds'] or numerical['status'] != 'numerically_verified_pending_integration'
            or numerical['approved_for_source'] is not False or roster['approved_for_source'] is not False
            or numerical['approved_for_modeling'] is not False or roster['approved_for_modeling'] is not False
            or len(numerical['models']) != 3
            or {(m['level'], m['subject']) for m in numerical['models']} != {('ES', s) for s in model_audit.SUBJECTS}
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 90
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model']
                   or m['coverage']['ten_valid_scored_floor_certified'] is not False for m in numerical['models'])):
        raise ValueError('Cobb County numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def outcome(link,entry,subject,refs):
    value=link['subjects'][subject];original=None if entry is None else entry['raw'][model_audit.RATE_FIELD]
    reported=None if entry is None else model_audit.original_rate(original)
    if not same((reported,original),(value['native_rate'],value['raw_rate'])):raise ValueError('Cobb original published G38 rate differs from frozen source')
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
    if set(refs_by_id)!=configurations:raise ValueError('Cobb complete 90-profile roster differs from original selector')
    raw=roster['raw_inputs'];directory={e['raw']['NCESSCH']:e['raw']for e in raw['directory']['records']}
    members={e['source_row']:e['raw']for e in raw['membership']['records']};direct={e['source_row']:e['raw']for e in raw['lunch']['records']};assessments={e['source_row']:e for e in raw['assessment']['records']};schools=[]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id']
        if (key in configurations)is not link['source_profile_eligible']:raise ValueError('Cobb normalized profile scope differs from immutable source')
        if key not in configurations:continue
        refs=refs_by_id[key];ccd=directory[key];income=link['income'];n=model_audit.original_count(members[refs['membership']['source_row']]);low=model_audit.original_count(direct[refs['direct_certification']['source_row']]);reported=100*low/n if n and low is not None and low<=n else None
        if reported is None or not same((reported,n,low),(income['reported_percentage'],income['reported_membership'],income['reported_direct_certification'])):raise ValueError('Cobb own reported individual direct-certification ratio differs from frozen evidence')
        held=link['source_attribution_hold']is not None
        if income['usable']is not(not held):raise ValueError('Cobb source-attribution/income usability differs')
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
    if len(schools)!=90 or len(numerical['retained_scope_exclusions'])!=20:raise ValueError('Cobb release requires 90 exact profiles and 20 retained outside records')
    if any(s['income']is None for s in schools):raise ValueError('Cobb requires own usable income for every source profile')
    for model in numerical['models']:
        normalized=[]
        for school in schools:
            rates={s:school['outcomes'][s]['proficiency']for s in ['math','reading']};y=(rates['math']+rates['reading'])/2 if model['subject']=='combined'and all(v is not None for v in rates.values())else rates.get(model['subject'])
            if school['income']is not None and y is not None:normalized.append(dict(school_id=school['id'],ncessch=school['ncessch'],income_pct=school['income'],outcome_pct=y,income_enrollment=school['enrollment'],reported_direct_certified_count=school['low_income']))
        if not same(normalized,[{k:r[k]for k in normalized[0]}for r in model['inputs']]):raise ValueError('Cobb normalized subject inputs differ from audited numerical cohort')
    source_audit=dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),complete_numerical_reference=dict(path='data/source/cobb-model-audit.json',sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES),
        audit_code_test_references={k:copy.deepcopy(v)for k,v in numerical['sources'].items()if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_cobb_models.py',sha256=NUMERICAL_CODE_SHA),tests=dict(path='tests/test_cobb_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=model_audit.SOURCE_RAW_SHA,immutable_schema_fingerprint=model_audit.SOURCE_SCHEMA_SHA,immutable_definition_fingerprint=model_audit.SOURCE_DEFINITION_SHA,immutable_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA,immutable_source_runtime_fingerprint=model_audit.SOURCE_RUNTIME_SHA,immutable_numerical_policy_fingerprint=NUMERICAL_POLICY_SHA,immutable_numerical_runtime_fingerprint=model_audit.RUNTIME_CONTRACT_SHA,normalized_metadata_fingerprint=ADAPTER_CONTRACT_SHA,
        operational_roster=copy.deepcopy(numerical['source_coverage']),retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),retained_outside_source_profiles=copy.deepcopy(numerical['retained_outside_source_profiles']),
        attribution_coverage=dict(exact_named_primary_notes=roster['source_definition_evidence']['exact_Cobb_named_notes'],
            nonlisted_attribution_coverage_certified=False,EOG_accelerated_EOC_population_certified=False,
            basis='No Cobb-specific attribution warning is inferred from unrelated districts; absence of a named note does not certify completeness or accelerated EOG/EOC population coverage.'),
        subject_coverage={m['subject']:copy.deepcopy(m['coverage'])for m in numerical['models']},nonoperational_ccd_references=[],
        native_assessment_definition=dict(state='GA',name=ASSESSMENT,original_numerical_name=model_audit.ASSESSMENT,year=2025,level='ES',grades=cohorts()[0]['grades'],standard=STANDARD,source_url=roster_audit.SOURCES['edc_2025']['url']),
        historical_state_extract=copy.deepcopy(roster['state_extract']),count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_hard_holds=True,source_attribution_limits_retained=True,minimum_subject_schools=30,
            historical_audits_approved_for_source=False,historical_audits_approved_for_modeling=False,all_models_point_only=True,normalized_source_approved=True,district_modeling_approved=True,
            verified_valid_score_denominators_available=False,ten_valid_scored_floor_certified=False,numerical_success_resolves_count_hold=False,
            note='Only this separately validated exact 90-profile, 90 Math, 90 ELA and 90 Combined point-only contract is approved. Historical six audits/code/tests remain unchanged with false approvals. Primary/high/mixed scopes, Georgia income definitions, nonlisted attribution and accelerated EOG/EOC coverage, valid-score counts and floor limits remain explicit.'))
    selection=dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),directory_school_ids=[s['id']for s in schools],
        subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],school_ids=[r['school_id']for r in m['inputs']],population_sha256=m['population_sha256'])for m in numerical['models']})
    selection['sha256']=roster_audit.fingerprint(selection);sources=copy.deepcopy(roster['sources']);sources['historical_georgia_extract']=dict(path=roster['state_extract']['path'],url=PROJECT_SOURCE+roster['state_extract']['path'],sha256=roster['state_extract']['sha256'])
    for key,path,digest in [('roster_audit','data/source/cobb-district-audit.json',model_audit.ROSTER_SHA),('numerical_audit','data/source/cobb-model-audit.json',NUMERICAL_SHA),
        ('source_audit_code','scripts/audit_cobb.py',model_audit.SOURCE_CODE_SHA),('source_audit_tests','tests/test_cobb_audit.py',model_audit.SOURCE_TESTS_SHA),('numerical_audit_code','scripts/audit_cobb_models.py',NUMERICAL_CODE_SHA),('numerical_audit_tests','tests/test_cobb_models.py',NUMERICAL_TESTS_SHA)]:sources[key]=dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note=(
        'Cobb County independent district comparison, 2024–25. All 90 grade-school profiles have separate fixed 90-school Math, ELA and Combined results. '
        'Own reported CCD individual direct certification / membership is a benefit and status proxy, not full FRPL or universal meal receipt. Native regular Georgia Milestones EOG All Students G38 proficiency uses Levels 3–4 original published rates. '
        'The source retains all 110 exact CCD schools, with two primary-only, 16 high and two mixed schools outside this comparison; Walton High is the sole source charter and remains outside. '
        'Both district and summed operational school membership are 105,738; this agreement does not certify nonlisted source attribution. Georgia Medicaid/foster certification and outside-program prekindergarten membership remain broader population limits. '
        'Accelerated EOG/EOC coverage, valid-score counts and the ten-valid-scored floor remain uncertified; sampling intervals are unavailable. Programs, admissions, provider roles, coordinates and boundaries are unknown; one year only.')
    shifts='; '.join(('ELA'if m['subject']=='reading'else m['subject'].title())+' '+format(m['diagnostics']['maximum_prediction_change_on_observed_income_range'],'.6f')for m in numerical['models'])
    details=[MODEL_SCOPE,
        'Three separate unweighted OLS fits reproduce all 270 results and explicit deleted fits. Combined independently fits the equal mean of original Math and ELA rates with its own residual scale and studentization; studentized scores cannot be averaged. Filters never refit models. Associations do not establish causal school effectiveness or overall quality.',
        'Use original EDC v3.1 regular Georgia Milestones EOG School All Students G38 aggregate grades 3–8 proficiency at Levels 3–4. Published fractional tokens become percentages without rebuilding more precise count ratios or averaging grades. Ranged, suppressed and missing rates remain unavailable, never zero. Accelerated pupils and EOC course coverage are not established by these originals; no alternate or EOC rates are spliced into the model.',
        INCOME_DEFINITION,
        'CCD membership/direct certification cover the school’s reported population, including pre-K where present; native EOG G38 proficiency covers grades 3–8. No Cobb-specific attribution warning is inferred from unrelated districts, and absence of a named note does not certify nonlisted attribution completeness.',
        'The district and summed operational schools each report 105,738 pupils. Their aggregate agreement never replaces a school’s own income denominator or establishes exact population equivalence with assessed grades.',
        COUNT_NOTE+' External studentization uses every deleted-school residual scale and N−3 degrees of freedom; it supplies no enrollment adjustment or shrinkage.',
        'Full and all 270 deleted designs have rank two and positive finite scales. Largest deleted prediction changes over observed income: '+shifts+' percentage points. Every eligible school, income extreme and influential Bryant Elementary and Dickerson Middle remains included. Diagnostic flags never remove schools or clamp predictions.',
        'The complete linked source retains 2,260 needed original records and 68,573 typed cells, full primary definitions and schemas, and exact omission inventories for 25,662 complete target records / 865,003 cells. Original identities, row/field references, raw ratio/rate values and masks permit auditing without duplicating whole raw tables.',
        'Two primary-only, 16 high and two mixed schools remain outside the 90 profiles. Walton High is the source’s only charter and is outside the tested grade-school population. Programs are Unclassified; admissions, provider roles, coordinates and boundaries remain unknown. One year only; incompatible income measures and assessment thresholds cannot produce a common national ranking.']
    snapshot=dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',state=dict(id='GA',name='Georgia'),
        name='Cobb County 2024–25 Georgia Milestones EOG district comparison',region='cobb',region_name='Cobb County',statewide=False,
        comparison='Cobb County · {year} · {assessment} · {note}',prepare_script='scripts/prepare_cobb.py',source_url=roster_audit.SOURCES['edc_2025']['url'],retrieved='2026-10-14',model_scope=MODEL_SCOPE,
        release_status='ready',approved_for_source=True,approved_for_modeling=True,map_source='School coordinates and district boundaries are unavailable in the audited Cobb County source release.',
        income_definition=dict(label=INCOME_LABEL,definition=INCOME_DEFINITION,url=roster_audit.SOURCES['nces_lunch_definitions']['url']),sources=sources,cohorts=cohorts(),schools=schools,selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Cobb County independent Georgia Milestones regular EOG G38 grade-school models with own reported individual direct certification; accelerated EOG/EOC coverage, valid-score counts and floor uncertified, sampling intervals unavailable.',details=details,
            sources=[dict(label=label,url=sources[key]['url'])for key,label in [('edc_2025','EDC v3.1 original Georgia Milestones EOG rates'),('edc_codebook_v3_1','EDC original field codebook'),('edc_technical_v3_1','EDC original technical documentation and Georgia source/standards'),('ccd_directory_2025','CCD exact 2024–25 school roster'),('ccd_membership_2025','CCD same-year own school membership'),('ccd_lunch_2025','CCD Final 2a reported direct-certification counts'),('ccd_state_notes_2025','CCD original Georgia income/membership reporting notes'),('nces_lunch_definitions','NCES direct-certification definitions'),('ccd_lea_directory','CCD exact district identity'),('ccd_lea_membership','CCD reported district membership')]]))
    require_normalized(snapshot)
    return snapshot


def build():
    return build_snapshot(*load_inputs())


def require_normalized(payload):
    original_normalized = '308af3ca1022e7e22cd9c815850706c6f37958426536faba9d5a059422199ac8'
    if NORMALIZED_PAYLOAD_SHA != original_normalized or roster_audit.fingerprint(payload) != original_normalized:
        raise ValueError('Cobb complete normalized typed/source/attribution fingerprint changed')


def validate(payload, expected=None):
    # Every replay verifies current full linked evidence and an immutable typed
    # normalized payload. A supplied expected object is a value, never authority.
    roster=model_audit.load_roster();numerical=json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical);require_normalized(payload)
    if expected is not None:require_normalized(expected)
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
        if not same(datasets, [dict(id=DATASET, state='GA', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Cobb County canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Cobb County canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='GA', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Cobb County canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Georgia's independent statewide release and other dataset-composite namespaces.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 90 or len(economic_rows) != 90 or len(observation_rows) != 180:
            raise ValueError('Cobb County canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Cobb County canonical profile/observation membership changed')
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
                raise ValueError('Cobb County canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=None,
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=None, source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Cobb County canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Cobb County canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                assessed_schools=90, excluded_schools=90 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Cobb County canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Cobb County canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']), low=None, high=None)
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Cobb County canonical point-only result differs from audited district fit')
            total += len(saved)
        if total != 270 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Cobb County canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Cobb County canonical foreign-key integrity failed')
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
    if (len(schools['schools']) != 90 or len(history['records']) != 90
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Cobb County exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Cobb County export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Cobb County history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Cobb County historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=ASSESSMENT, subject=subject,
                              assessed_schools=90, excluded_schools=90 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Cobb County exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Cobb County exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=None, cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'low', 'high', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Cobb County per-school point-only metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Cobb County profile/history subject set differs from exact audited eligibility')
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
            raise ValueError('Cobb County profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 90, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=90, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Cobb County exported coverage/source exclusions differ from approved selection')
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
        raise ValueError('Cobb County exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='cobb', geography='cobb', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Cobb County ready descriptor must retain distinct district and point-only scope')
    return {m['model_id']: m['coefficients']['n'] for m in numerical['models']}


def validate_existing_namespace(payload, database, numerical, extract_path):
    """A repeat import must not erase evidence of a corrupt or foreign namespace."""
    # A standalone check of an empty namespace still requires current complete
    # evidence before SQL access; caller-supplied numerical objects are values.
    roster=model_audit.load_roster()
    require_frozen_inputs(roster,numerical)
    require_normalized(payload)
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

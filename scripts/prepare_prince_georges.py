"""Canonical/static Prince George's regular MCAP comparison linked to immutable audits."""
import argparse
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path

import audit_prince_georges as roster_audit
import audit_prince_georges_models as model_audit
from database import ROOT, DEFAULT_DB, connect, definition_id
from state_snapshot import prepare_snapshot

DATASET = 'md-prince-georges-2025'
EXTRACT = ROOT / 'data/source/prince-georges.json'
OUTPUT = ROOT / 'data/prince-georges'
NUMERICAL_SHA = '8594f53d2722b913bf1907a0c0d8c53c21405c64b3d108a7b722706281b8f661'
NUMERICAL_BYTES = 1249923
NUMERICAL_POLICY_SHA = '7190bb7c0b722e5cea16bae8aafe03af5cd8aae58190861a8f3e25f48416e201'
NUMERICAL_CODE_SHA = '69e0e8440258b440269a3fda491d7005c49c5ffc2ae3f6027a5aff451160897e'
NUMERICAL_TESTS_SHA = 'ba9ce66ac140d893c392b6b35c7085b5d274e1de6b4538005a9795d34c33b4e9'
PROJECT_SOURCE = 'https://github.com/robot-assisted-projects/FRPL-RMA/blob/expansion/all-states/'
EXPECTED_N = {'math':146,'reading':159,'combined':146}
MODEL_SCOPE = (
    'Prince George’s County independent 2024–25 regular MCAP grade-school district models: exact '
    'operational NCES LEA 2400510 / CCD native MD-16 / MSDE 16 identities. All 159 native E/M/EM '
    'profiles with positive September grades 3–8 and no high-grade row remain searchable. '
    'Original regular School_Level All Students All Grades Levels 3/4 published rates support '
    '146 Math, 159 ELA and 146 independently fitted Combined results; 13 Math masks retain ELA. '
    'Precise same-year individual Early Attendance ratios use their own denominators. Accelerated '
    'Math courses and the applicable grade 6–7 waiver remain in native totals; DLM stays separate. '
    'High, mixed, primary, unknown, unmatched and closed records remain outside this point-only release. '
    'Valid-score count scope and the ten-valid-scored floor remain uncertified; sampling intervals are unavailable modelwide.')
COUNT_NOTE = (
    'Valid-score count scope and the ten-valid-scored floor remain uncertified. Native administrative '
    'Tested Count, Early Attendance income denominators, September/CCD enrollment, participation and '
    'federal 95%-rule counts never substitute for valid-score denominators. All valid-score counts, '
    'sampling variances and interval endpoints are null; sampling intervals are unavailable.')


def same(actual, expected):
    """Typed exact evidence equality; Python bool/int equality is insufficient."""
    return roster_audit.fingerprint(actual) == roster_audit.fingerprint(expected)


def require_frozen_inputs(roster, numerical):
    """All six complete audit/code/test pins remain required with compact links."""
    model_audit.require_frozen_roster(roster)
    if hashlib.sha256((ROOT / 'scripts/audit_prince_georges_models.py').read_bytes()).hexdigest() != NUMERICAL_CODE_SHA:
        raise ValueError('Prince George’s County frozen numerical code/policy fingerprint changed')
    if hashlib.sha256((ROOT / 'tests/test_prince_georges_models.py').read_bytes()).hexdigest() != NUMERICAL_TESTS_SHA:
        raise ValueError('Prince George’s County frozen numerical tests fingerprint changed')
    content = model_audit.OUTPUT.read_bytes()
    if len(content) != NUMERICAL_BYTES or hashlib.sha256(content).hexdigest() != NUMERICAL_SHA or not same(numerical, json.loads(content)):
        raise ValueError('Prince George’s County complete numerical evidence fingerprint changed')
    # Code bytes alone do not bind mutable in-memory policy objects. A cached
    # expected normalized payload must still reject current policy/definition
    # drift against the complete immutable numerical evidence on every entry.
    if (model_audit.roster_audit.fingerprint(model_audit.POLICY) != NUMERICAL_POLICY_SHA
            or not same(model_audit.POLICY, numerical['policy'])
            or not same(model_audit.SUBJECTS, [m['subject'] for m in numerical['models']])
            or not same(model_audit.MIN_SCHOOLS, numerical['policy']['minimum_usable_subject_schools'])
            or any(m['assessment'] != model_audit.ASSESSMENT or m['assessment_standard'] != model_audit.STANDARD
                   for m in numerical['models'])):
        raise ValueError('Prince George’s current numerical policy/definition differs from the complete frozen audit')
    original_refs = numerical['models'][0]['inputs'][0]['source_refs']['outcomes']
    if (not same(model_audit.SUBJECT_MEMBERS, {s: original_refs[s]['member'] for s in ['math','reading']})
            or not same(model_audit.SUBJECT_LABELS, {s: original_refs[s]['assessment'].strip() for s in ['math','reading']})):
        raise ValueError('Prince George’s current numerical subject population/collection definition changed')


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
            or len(numerical['frozen_population']['grade_school_configuration_ids']) != 159
            or any(m['status'] != 'numerically_verified_pending_integration'
                   or m['coefficients']['n'] != EXPECTED_N[m['subject']]
                   or m['intervals']['available_for_entire_model']
                   or m['coverage']['ten_valid_scored_floor_certified'] is not False
                   for m in numerical['models'])):
        raise ValueError('Prince George’s County numerical audit has unresolved grade-school release or population holds')
    return roster, numerical


def cohorts():
    return [dict(id='grade',level='ES',assessment=model_audit.ASSESSMENT,
        label='Grade schools · regular MCAP',grades='3–8 plus accelerated Math courses',
        standard=model_audit.STANDARD,source_url=roster_audit.SOURCES['msde_assessment']['url'],source='msde_assessment',
        allow_point_only=True,outcome='Proficient · Levels 3 and 4',
        note='Prince George’s independent regular MCAP All Grades published rates · individual Early Attendance income · '
            'accelerated Math/grade 6–7 waiver · valid-score count scope and ten-valid-scored floor uncertified · sampling intervals unavailable')]


def outcome(link, entry, subject, refs):
    value=link['subjects'][subject]
    rate=None if entry is None else model_audit.original_number(entry['raw']['Proficient Pct'])
    original=None if entry is None else entry['raw']['Proficient Pct']
    if not same(rate,value['native_rate'])or not same(original,value['raw_rate']):
        raise ValueError('Prince George’s original published rate differs from frozen source audit')
    return dict(proficiency=rate,tested=None,valid_score_evidence=None,raw_tested=None,
        exclusion=value['exclusion'],source='msde_assessment',source_row=0 if entry is None else entry['source_row'],
        raw=dict(applicable=value['applicable'],native_usable=value['usable'],outcome_basis='original_regular_mcap_published_levels3_4',
            original_native_values=None if entry is None else {k:entry['raw'][k]for k in ['Proficient Pct','Tested Count','Proficient Count']},
            original_rate_field='Proficient Pct',native_outcome=copy.deepcopy(value),
            native_school_id=link['school_id'],source_refs=copy.deepcopy(refs['outcomes'][subject]),
            complete_source_sha256=model_audit.ROSTER_SHA,valid_score_count=None,sampling_variance=None,
            interval_availability=False,ten_valid_scored_floor_certified=False,count_note=COUNT_NOTE))


def build_snapshot(roster, numerical):
    """Complete source scope remains independently checked; compact pointers preserve originals."""
    require_frozen_inputs(roster,numerical)
    configurations=set(numerical['frozen_population']['grade_school_configuration_ids'])
    # The frozen ELA cohort includes every prospective source profile. Its original
    # selector independently rechecks configurations, income bands and source rows.
    ela_inputs,_=model_audit.selected_inputs(roster,'reading')
    refs_by_id={r['school_id']:r['source_refs']for r in ela_inputs}
    if set(refs_by_id)!=configurations:
        raise ValueError('Prince George’s complete159-profile roster differs from original selector')
    raw=roster['raw_inputs'];ccd={e['raw']['NCESSCH']:e for e in raw['directory']['records']}
    native={roster_audit.native_identity(e['raw']):e for e in raw['native_directory']['records']}
    incomes={e['source_row']:e for e in raw['native_income']['records']}
    assessments={(e['member'],e['worksheet'],e['source_row']):e for e in raw['native_assessment']['records']}
    schools=[]
    for link in sorted(roster['roster_links'],key=lambda r:r['school_id']):
        key=link['school_id']
        if (key in configurations)is not link['source_profile_eligible']:
            raise ValueError('Prince George’s normalized profile scope differs from immutable source')
        if key not in configurations:
            continue
        refs=refs_by_id[key];profile=native[key]['raw'];directory=ccd[link['ncessch']]['raw'];income=link['income']
        selected=incomes[refs['income']['selected_source_row']]['raw']
        n=model_audit.original_number(selected['Total Student Cnt'],count=True);low=model_audit.original_number(selected['Economically Disadvantaged Cnt'],count=True)
        display=model_audit.original_number(selected['Economically Disadvantaged Pct'])
        percentage=100*low/n if n and low is not None and display is not None else None
        if percentage is None or low>n or abs(percentage-display)>.0500001 or not same((percentage,n,low),(income['percentage'],income['early_attendance_enrollment'],income['individual_low_income_count'])):
            raise ValueError('Prince George’s own whole-school Early Attendance ratio differs from frozen evidence')
        subject_entries={s:None if refs['outcomes'][s]is None else assessments[(refs['outcomes'][s]['member'],refs['outcomes'][s]['worksheet'],refs['outcomes'][s]['source_row'])]for s in ['math','reading']}
        schools.append(dict(id=key,ncessch=link['ncessch'],cohort='grade',name=profile['School Name'],
            district_id=roster_audit.LEA,district=directory['LEA_NAME'],city=directory['LCITY']or None,county=None,
            enrollment=n,low_income=low,income=percentage,income_source='msde_income',income_row=refs['income']['selected_source_row'],
            income_raw=dict(individual_income=dict(year=2025,early_attendance_enrollment=n,individual_low_income_count=low,percentage=percentage,
                raw_denominator=selected['Total Student Cnt'],raw_count=selected['Economically Disadvantaged Cnt'],raw_percentage=selected['Economically Disadvantaged Pct'],
                selected_school_type=selected['School Type'],source_rows=copy.deepcopy(income['source_rows']),selected_source_row=income['selected_source_row'],definition=roster_audit.POLICY['income']),
                source_refs=copy.deepcopy(refs['income']),complete_source_sha256=model_audit.ROSTER_SHA,valid_score_denominator=False),
            identity_raw=dict(ncessch=link['ncessch'],native_school_id=link['native_school_id'],msde_school_id=key,
                source_refs=copy.deepcopy(refs),complete_source_sha256=model_audit.ROSTER_SHA,
                ccd_flags=copy.deepcopy(link['ccd_flags']),native_grade_span=link['native_grade_span'],
                offered_evidence=copy.deepcopy(link['offered']),native_september_enrollment=link['native_september_enrollment'],
                ccd_membership_total=link['enrolled']['reported_total'],early_attendance_minus_ccd=link['early_attendance_minus_ccd'],
                early_attendance_minus_september=link['early_attendance_minus_september']),
            outcomes={s:outcome(link,subject_entries[s],s,refs)for s in ['math','reading']}))
    if len(schools)!=159 or len(numerical['retained_scope_exclusions'])!=45:
        raise ValueError('Prince George’s release requires159exact profiles and45native outside profiles')
    for model in numerical['models']:
        selected=[]
        for school in schools:
            rates={s:school['outcomes'][s]['proficiency']for s in ['math','reading']}
            y=(rates['math']+rates['reading'])/2 if model['subject']=='combined'and all(v is not None for v in rates.values())else rates.get(model['subject'])
            if school['income']is not None and y is not None:
                selected.append(dict(school_id=school['id'],ncessch=school['ncessch'],income_pct=school['income'],outcome_pct=y,
                    income_enrollment=school['enrollment'],individual_economic_count=school['low_income']))
        if not same(selected,[{k:r[k]for k in selected[0]}for r in model['inputs']]):
            raise ValueError('Prince George’s exact normalized subject inputs differ from audited numerical cohort')
    source_audit=dict(complete_source_reference=copy.deepcopy(numerical['retained_source_reference']),
        complete_numerical_reference=dict(path='data/source/prince-georges-model-audit.json',sha256=NUMERICAL_SHA,bytes=NUMERICAL_BYTES),
        audit_code_test_references={k:copy.deepcopy(v)for k,v in numerical['sources'].items()if k in ['source_audit_code','source_audit_tests']},
        numerical_code_test_references=dict(code=dict(path='scripts/audit_prince_georges_models.py',sha256=NUMERICAL_CODE_SHA),tests=dict(path='tests/test_prince_georges_models.py',sha256=NUMERICAL_TESTS_SHA)),
        immutable_raw_input_fingerprint=model_audit.SOURCE_RAW_SHA,immutable_schema_fingerprint=model_audit.SOURCE_SCHEMA_SHA,
        immutable_definition_fingerprint=model_audit.SOURCE_DEFINITION_SHA,immutable_identity_fingerprint=model_audit.SOURCE_IDENTITY_SHA,
        immutable_source_policy_fingerprint=model_audit.SOURCE_POLICY_SHA,immutable_numerical_policy_fingerprint=NUMERICAL_POLICY_SHA,operational_roster=copy.deepcopy(numerical['source_coverage']),
        retained_scope_exclusions=copy.deepcopy(numerical['retained_scope_exclusions']),
        unmatched_ccd_references=[dict(source_row=e['source_row'],ncessch=e['raw']['NCESSCH'],native_school_id=e['raw']['ST_SCHID'],status=e['raw']['UPDATED_STATUS_TEXT'])for e in roster['unmatched_ccd_directory']],
        nonoperational_ccd_references=[dict(source_row=e['source_row'],ncessch=e['raw']['NCESSCH'],native_school_id=e['raw']['ST_SCHID'],status=e['raw']['UPDATED_STATUS_TEXT'])for e in roster['nonoperational_directory']],
        subject_coverage={m['subject']:copy.deepcopy(m['coverage'])for m in numerical['models']},
        native_assessment_definition=dict(state='MD',name=model_audit.ASSESSMENT,year=2025,level='ES',grades=cohorts()[0]['grades'],standard=model_audit.STANDARD,source_url=roster_audit.SOURCES['msde_assessment']['url']),
        historical_state_extract=copy.deepcopy(roster['state_extract']),count_definition_status=copy.deepcopy(numerical['count_definition_status']),
        release_basis=dict(exact_source_roster_replayed=True,numerical_audit_without_holds=True,minimum_subject_schools=30,
            historical_audits_approved_for_source=False,historical_audits_approved_for_modeling=False,all_models_point_only=True,
            normalized_source_approved=True,district_modeling_approved=True,verified_valid_score_denominators_available=False,
            ten_valid_scored_floor_certified=False,numerical_success_resolves_count_hold=False,
            note='Only this separately validated exact 2024–25 regular MCAP grade-school point-only contract is approved. Source and numerical historical audits remain immutable with false approvals; compact references require available unchanged artifacts/code/tests/policy and current semantic replay on every validation/import. High, mixed, primary, unknown, unmatched and closed scopes, valid-score counts and the scored floor remain held.'))
    selection=dict(policy=copy.deepcopy(model_audit.POLICY),frozen_source_population=copy.deepcopy(numerical['frozen_population']),
        directory_school_ids=[s['id']for s in schools],subject_models={m['model_id']:dict(level=m['level'],subject=m['subject'],school_ids=[r['school_id']for r in m['inputs']],population_sha256=m['population_sha256'])for m in numerical['models']})
    selection['sha256']=roster_audit.fingerprint(selection)
    sources=copy.deepcopy(roster['sources'])
    for key,path,digest in [('roster_audit','data/source/prince-georges-district-audit.json',model_audit.ROSTER_SHA),
        ('numerical_audit','data/source/prince-georges-model-audit.json',NUMERICAL_SHA),
        ('source_audit_code','scripts/audit_prince_georges.py',model_audit.SOURCE_CODE_SHA),('source_audit_tests','tests/test_prince_georges_audit.py',model_audit.SOURCE_TESTS_SHA),
        ('numerical_audit_code','scripts/audit_prince_georges_models.py',NUMERICAL_CODE_SHA),('numerical_audit_tests','tests/test_prince_georges_models.py',NUMERICAL_TESTS_SHA)]:
        sources[key]=dict(path=path,url=PROJECT_SOURCE+path,sha256=digest)
    coverage_note = (
        'Prince George’s County independent district comparison, 2024–25: exact NCES LEA 2400510 / MD-16 / MSDE 16. '
        'All 159 audited grade-school profiles are searchable with usable individual Early Attendance income; '
        '146 Math, 159 ELA and 146 Combined results enter separate district fits. The 13 Math <=5.0 masks '
        'remain unavailable for Math/Combined and retain ELA; missingness never means zero. Native regular '
        'MCAP All Grades All Students Levels 3/4 retains accelerated Algebra I, Geometry and Algebra II, '
        'including the applicable grade 6–7 course waiver, separately from alternate DLM. The complete source '
        'retains 201 CCD and 204 native inventories; 45 native profiles outside the grade-school scope and '
        'three unmatched CCD records are distinct views, including Ellen Ochoa’s original malformed NCES '
        'identity left unjoined. Income, September/CCD enrollment and assessment populations and dates differ; '
        'differences do not establish their causes. Valid-score count scope and the ten-valid-scored floor '
        'remain uncertified; sampling intervals are unavailable modelwide. Admissions, provider roles, programs, '
        'coordinates and boundaries remain unaudited; one year only.')
    shifts = '; '.join(('ELA' if m['subject']=='reading' else m['subject'].title()) + ' ' +
        format(m['diagnostics']['maximum_prediction_change_on_observed_income_range'], '.6f') for m in numerical['models'])
    details = [MODEL_SCOPE,
        'Three separate unweighted OLS fits reproduce all 451 audited results and explicit centered deleted fits. '
        'Combined independently fits the paired 146 original Math/ELA rate means, with its own scale and '
        'studentization. ELA has 159 members, so neither coefficients nor studentized scores can be averaged '
        'across subject models. Filters never refit models. Associations do not establish causal effectiveness or overall quality.',
        roster_audit.POLICY['assessment'], roster_audit.POLICY['accelerated_scope'],
        roster_audit.POLICY['income'], roster_audit.POLICY['denominator'],
        'All 159 individual income ratios use their own Early Attendance numerator and denominator. Multiband '
        'native E/M/EM profiles use the unique whole-school All row, never summed bands or September/CCD/another-year '
        'replacement. September district and known-school totals 132,151 differ from CCD 132,123 by 28; an unmatched '
        'JACS native entry has 28, which does not prove the cause or authorize an inferred identity. Early Attendance '
        'district and known-school sums 133,427 agree while six missing denominator cells remain missing, never zero or allocated.',
        COUNT_NOTE + ' Studentization uses the deleted-school residual scale and N−3 degrees of freedom; it provides '
        'no enrollment adjustment or shrinkage. Published one-decimal rates, rounded levels and administrative counts '
        'remain distinct; never reconstruct masked rates or valid-scored counts.',
        'Full and all 451 deleted designs have rank two and finite positive scales. Largest deleted prediction '
        'changes over observed incomes: ' + shifts + ' percentage points. All six eligible charters and influential '
        'Glenarden Woods and Imagine Andrews members remain eligible. Diagnostic flags are descriptive; they never '
        'exclude a school or clamp a prediction.',
        'The complete source retains 5,404 original records, 89,640 typed cells, original headers and primary definitions. '
        'Compact normalized pointers preserve exact row, member, worksheet and field references. Historical audit '
        'approvals remain false; only this separately validated grade-school contract is released.',
        'Names, slicing or composition never correct identities: Ellen Ochoa’s original native 16-0218 NCES 24005109050 '
        'remains unjoined to CCD 240051090501. Closed, high, mixed, primary, unknown and unmatched scopes stay outside '
        'the 159 profiles. Programs are Unclassified; admissions, provider roles, coordinates and boundaries remain '
        'unknown. One year only. Incompatible state thresholds and income definitions cannot produce a common national ranking.']
    return dict(schema_version=1,dataset=DATASET,year=2025,academic_year='2024–25',state=dict(id='MD',name='Maryland'),
        name='Prince George’s County 2024–25 regular MCAP district comparison',region='prince-georges',region_name='Prince George’s County',statewide=False,
        comparison='Prince George’s County · {year} · {assessment} · {note}',prepare_script='scripts/prepare_prince_georges.py',
        source_url=roster_audit.SOURCES['msde_assessment']['url'],retrieved='2026-10-13',model_scope=MODEL_SCOPE,
        release_status='ready',approved_for_source=True,approved_for_modeling=True,
        map_source='School coordinates and district boundaries are unavailable in the audited Prince George’s County source release.',
        income_definition=dict(label='Individual direct-certification economic disadvantage',definition=roster_audit.POLICY['income']+' '+roster_audit.POLICY['denominator'],url=roster_audit.SOURCES['msde_definitions']['url']),
        sources=sources,cohorts=cohorts(),schools=schools,selection=selection,source_audit=source_audit,coverage_note=coverage_note,
        methodology=dict(summary='Prince George’s County independent regular MCAP grade-school district models with individual Early Attendance income; valid-score count scope and ten-valid-scored floor uncertified, sampling intervals unavailable.',
            details=details,sources=[dict(label=label,url=sources[key]['url'])for key,label in [('msde_directory','MSDE 2025 original school directory'),('msde_enrollment','MSDE September grade enrollment'),('msde_income','MSDE Early Attendance individual income'),('msde_assessment','MSDE regular MCAP 2025 All Students All Grades'),('msde_definitions','MSDE original definition notes'),('msde_reportcard','MSDE Levels 3/4 proficiency threshold'),('msde_mcap_overview','March 2025 MCAP overview and grade 6–7 waiver'),('ccd_directory','CCD exact 2024–25 school roster'),('ccd_membership','CCD same-year membership')]]))


def build():
    return build_snapshot(*load_inputs())


def validate(payload, expected=None):
    # Cached normalized expectations never bypass complete immutable linked evidence.
    roster = model_audit.load_roster()
    numerical = json.loads(model_audit.OUTPUT.read_bytes())
    require_frozen_inputs(roster,numerical)
    expected = build() if expected is None else expected
    if not same(payload,expected):
        raise ValueError('Prince George’s County normalized extract differs from pinned source/model evidence, scope or selection policy')
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
        if not same(datasets, [dict(id=DATASET, state='MD', name=payload['name'],
                model_scope=payload['model_scope'], status='ready')]):
            raise ValueError('Prince George’s County canonical dataset release metadata changed')
        sources = dict(payload['sources'])
        sources['extract'] = dict(path=str(Path(extract_path).resolve().relative_to(ROOT)),
                                 url=payload['source_url'], sha256=hashlib.sha256(Path(extract_path).read_bytes()).hexdigest())
        expected_sources = {DATASET + ':' + key: dict(id=DATASET + ':' + key, dataset_id=DATASET,
            path=source['path'], url=source['url'], sha256=source['sha256'], imported_at=payload['retrieved'])
            for key, source in sources.items()}
        actual_sources = {r['id']: dict(r) for r in db.execute(
            'SELECT * FROM source WHERE dataset_id=? OR id LIKE ?', (DATASET, namespace))}
        if not same(actual_sources, expected_sources):
            raise ValueError('Prince George’s County canonical source provenance changed')
        definitions = [dict(r) for r in db.execute('SELECT * FROM assessment_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_definition = dict(id=assessment_id, state='MD', name=cohort['assessment'], year=2025,
            level='ES', grades=cohort['grades'], standard=cohort['standard'], source_url=cohort['source_url'])
        income_rows = [dict(r) for r in db.execute('SELECT * FROM economic_definition WHERE id LIKE ?', (DATASET + ':%',))]
        expected_income = dict(id=income_id, name=payload['income_definition']['label'],
            definition=payload['income_definition']['definition'], source_url=payload['income_definition']['url'])
        if not same(definitions, [expected_definition]) or not same(income_rows, [expected_income]):
            raise ValueError('Prince George’s County canonical native assessment/income definition changed')
        # SQLite foreign keys verify each referenced identity but do not require
        # source/definition/model ownership to match the observation's dataset.
        # Include every namespace reference so a foreign owner cannot hide rows
        # from an otherwise correct dataset-only count. Native school IDs remain
        # shared with Maryland's independent statewide release.
        school_rows = list(db.execute('SELECT * FROM school WHERE dataset_id=? OR source_id LIKE ?',
                                      (DATASET, namespace)))
        economic_rows = list(db.execute('''SELECT * FROM economic_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        observation_rows = list(db.execute('''SELECT * FROM assessment_observation WHERE
            dataset_id=? OR definition_id LIKE ? OR source_id LIKE ?''', (DATASET, namespace, namespace)))
        if len(school_rows) != 159 or len(economic_rows) != 159 or len(observation_rows) != 318:
            raise ValueError('Prince George’s County canonical profile/observation row counts changed')
        schools = {r['school_id']: dict(r) for r in school_rows}
        economic = {r['school_id']: dict(r) for r in economic_rows}
        observations = {(r['school_id'], r['subject']): dict(r) for r in observation_rows}
        if set(schools) != set(profiles) or set(economic) != set(profiles) or set(observations) != {(key, subject) for key in profiles for subject in ['math', 'reading']}:
            raise ValueError('Prince George’s County canonical profile/observation membership changed')
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
                raise ValueError('Prince George’s County canonical raw profile/same-year individual income changed')
            for subject in ['math', 'reading']:
                value = profile['outcomes'][subject]
                actual = dict(observations[(key, subject)])
                actual['raw_value'], actual['raw_tested'] = json.loads(actual['raw_value']), json.loads(actual['raw_tested'])
                expected = dict(dataset_id=DATASET, school_id=key, definition_id=assessment_id, subject=subject,
                    proficiency=number(value['proficiency']), tested=None,
                    status='reported' if value['proficiency'] is not None else 'suppressed_or_not_reported',
                    raw_value=value['raw'], raw_tested=None, source_id=DATASET + ':' + value['source'], source_order=value['source_row'])
                if not same(actual, expected):
                    raise ValueError('Prince George’s County canonical native outcome/raw exclusion/count evidence changed')
        model_rows = list(db.execute('''SELECT * FROM model_run WHERE
            dataset_id=? OR id LIKE ? OR definition_id LIKE ?''', (DATASET, namespace, namespace)))
        runs = {r['subject']: dict(r) for r in model_rows}
        if len(model_rows) != 3 or len(runs) != 3 or set(runs) != set(model_audit.SUBJECTS):
            raise ValueError('Prince George’s County canonical models require exactly three ES subject fits')
        digest = hashlib.sha256(json.dumps([(key, actual_sources[key]['sha256']) for key in sorted(actual_sources)]).encode()).hexdigest()
        total = 0
        for model in numerical['models']:
            subject = model['subject']; run = runs[subject]
            summary = json.loads(run.pop('summary_json'))
            expected_run = dict(id=f'{assessment_id}:{subject}:ols-v1:{digest[:12]}', dataset_id=DATASET,
                definition_id=assessment_id, subject=subject, method_version='ols-studentized-v1', input_sha256=digest)
            expected_summary = dict(year=2025, level='ES', assessment=model_audit.ASSESSMENT, subject=subject,
                assessed_schools=159, excluded_schools=159 - model['coefficients']['n'], **model['coefficients'])
            exact = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
            if (not same(run, expected_run) or not same({k: summary.get(k) for k in exact}, {k: expected_summary[k] for k in exact})
                    or not model_audit.numeric_equal(summary, expected_summary)):
                raise ValueError('Prince George’s County canonical model metadata/coefficients differ from audited fits')
            saved = {r['school_id']: dict(r) for r in db.execute('SELECT * FROM model_result WHERE model_id=?', (run['id'],))}
            reference = {r['school_id']: r for r in model['results']}
            if set(saved) != set(reference):
                raise ValueError('Prince George’s County canonical result membership changed')
            for key, result in reference.items():
                actual = saved[key]
                exact_result = dict(model_id=run['id'], dataset_id=DATASET, school_id=key, actual=float(result['actual']), low=None, high=None)
                expected_result = exact_result | dict(predicted=result['predicted'], studentized=result['studentized'])
                if (not same({k: actual.get(k) for k in exact_result}, exact_result)
                        or not model_audit.numeric_equal(actual, expected_result)):
                    raise ValueError('Prince George’s County canonical point-only result differs from audited district fit')
            total += len(saved)
        if total != 451 or db.execute('SELECT count(*) FROM model_result WHERE dataset_id=? OR model_id LIKE ?',
                                      (DATASET, namespace)).fetchone()[0] != total:
            raise ValueError('Prince George’s County canonical result count changed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Prince George’s County canonical foreign-key integrity failed')
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
    if (len(schools['schools']) != 159 or len(history['records']) != 159
            or set(exported) != set(profiles) or set(records) != set(profiles)):
        raise ValueError('Prince George’s County exported native source directory/history identities differ from selection')
    if set(schools['models']) != {'ES'} or set(schools['models']['ES']) != set(model_audit.SUBJECTS):
        raise ValueError('Prince George’s County export requires only the three independently audited ES models')
    expected_keys = {(2025, 'ES', model_audit.ASSESSMENT, m['subject']) for m in numerical['models']}
    for summaries in [schools['history_models'], history['models']]:
        keyed = {(m['year'], m['level'], m['assessment'], m['subject']): m for m in summaries}
        if len(summaries) != 3 or len(keyed) != 3 or set(keyed) != expected_keys:
            raise ValueError('Prince George’s County history must retain exactly three audited ES model populations')
        if any(not same(summary, schools['models']['ES'][key[3]]) for key, summary in keyed.items()):
            raise ValueError('Prince George’s County historical model summaries differ from current district fits')
    for model in numerical['models']:
        subject = model['subject']
        actual_model = schools['models']['ES'][subject]
        expected_model = dict(year=2025, level='ES', assessment=model_audit.ASSESSMENT, subject=subject,
                              assessed_schools=159, excluded_schools=159 - model['coefficients']['n'], **model['coefficients'])
        exact_model = ['year', 'level', 'assessment', 'subject', 'assessed_schools', 'excluded_schools', 'n']
        if (not same({k: actual_model.get(k) for k in exact_model}, {k: expected_model[k] for k in exact_model})
                or not model_audit.numeric_equal(actual_model, expected_model)):
            raise ValueError('Prince George’s County exported district coefficients/coverage differ from numerical audit')
        reference = {r['school_id']: r for r in model['results']}
        eligible = {s['id'] for s in schools['schools'] if subject in s['metrics']}
        if eligible != set(reference):
            raise ValueError('Prince George’s County exported subject membership differs from passed district audit')
        for key, result in reference.items():
            fields = ['actual', 'predicted', 'residual', 'studentized', 'low', 'high', 'leverage']
            metric = exported[key]['metrics'][subject]
            expected_metric = {k: result[k] for k in fields} | dict(tested=None, cohort_n=model['coefficients']['n'])
            exact = ['actual', 'tested', 'low', 'high', 'cohort_n']
            if (not same({k: metric.get(k) for k in exact}, {k: expected_metric[k] for k in exact})
                    or not model_audit.numeric_equal(metric, expected_metric)
                    or not same(metric, records[key]['subjects'][subject])):
                raise ValueError('Prince George’s County per-school point-only metric differs from verified district fit')
    for key, school in exported.items():
        profile = profiles[key]
        record = records[key]
        expected_subjects = {m['subject'] for m in numerical['models'] if key in {r['school_id'] for r in m['results']}}
        if set(school['metrics']) != expected_subjects or set(record['subjects']) != expected_subjects:
            raise ValueError('Prince George’s County profile/history subject set differs from exact audited eligibility')
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
            raise ValueError('Prince George’s County profile/history/exclusion/geography evidence changed')
    expected_coverage = {'grade': {'directory': 159, 'eligible': {m['subject']: m['coefficients']['n'] for m in numerical['models']}}}
    if not same(coverage, dict(year=2025, schools=159, cohorts=expected_coverage,
            source_audit=payload['source_audit'], exclusions=dict(Counter(
                reason for r in records.values() for reason in r['exclusions'].values())))):
        raise ValueError('Prince George’s County exported coverage/source exclusions differ from approved selection')
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
        raise ValueError('Prince George’s County exported native assessment definition or methodology changed')
    expected_descriptor = dict(schema_version=1, state=payload['state'], prepare_script=payload['prepare_script'],
        regions=[dict(id='prince-georges', geography='prince-georges', name=payload['region_name'], dataset=DATASET,
            statewide=False, status='ready', levels=['ES'], boundaries=None, comparison=payload['comparison'],
            audit=str((output / 'coverage.json').relative_to(ROOT)),
            schools=str((output / 'schools.json').relative_to(ROOT)),
            model_scope=payload['model_scope'], map_source=payload['map_source'])])
    if not same(descriptor, expected_descriptor):
        raise ValueError('Prince George’s County ready descriptor must retain distinct district and point-only scope')
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

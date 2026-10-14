"""Replay Cobb County's original 2024–25 source/cohort evidence, without models or imports."""
import argparse
from collections import Counter, defaultdict
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/cobb-district-audit.json'
LEA, NATIVE_LEA, NATIVE_DISTRICT = '1301290', 'GA-633', '633'
YEAR, ACADEMIC_YEAR = 2025, '2024-2025'
TABLES = ['directory', 'lea_directory', 'membership', 'lea_membership', 'lunch', 'assessment']
OPERATIONAL = {'1', '3', '4', '5', '8'}
OFFER_GRADES = ['PK', 'KG'] + [str(g) for g in range(1, 14)] + ['UG', 'AE']
LOWER_GRADES = ['Pre-Kindergarten', 'Kindergarten'] + [f'Grade {g}' for g in range(1, 9)]
SUBJECTS = {'math': 'math', 'reading': 'ela'}
ASSESSMENT_SELECTOR = {'DataLevel': 'School', 'SchYear': '2024-25', 'StateAbbrev': 'GA',
    'StateFips': '13', 'AssmtName': 'Georgia Milestones EOG', 'AssmtType': 'Regular',
    'GradeLevel': 'G38', 'StudentGroup': 'All Students', 'StudentSubGroup': 'All Students',
    'ProficiencyCriteria': 'Levels 3-4', 'Version': 'V3.1'}
PLANNING_FIELDS = ['nces_lea_id', 'state', 'native_lea_id', 'enrollment', 'enrollment_flag',
    'school_directory_operational_count', 'potential_cohorts', 'potential_school_ids',
    'directory_raw', 'directory_source_row', 'membership_raw', 'membership_source_row']
POLICY = {
    'identity': 'Exact original 2024–25 NCES LEA 1301290 / CCD GA-633 / EDC 633 ownership. Join authoritative twelve-digit NCES IDs and cross-check exact GA-633-#### / 633-#### source fields. Names, corrected digits, padding, county labels and other charter LEAs never establish ownership.',
    'raw_inventory': 'Retain every original field and mask in complete target directory, lunch categories, school/LEA total and grade membership, and all original All Students Math/ELA grade/assessment/school/district records. Whole original-file pins, complete-target hashes and exact omitted population/identity/row inventories preserve unused demographics. Selection never uses metric values, charter labels or fit diagnostics. Complete primary definitions and whole-state original-record cross-checks remain linked.',
    'population': 'Operational exact CCD profiles require complete unadjusted reported grade offers, highest grade 01–08, an offered grade 3–8, no offered grades 9–13/adult, positive own reported membership reconciled to all reported PK–8 subtotals, positive reported enrolled grades 3–8, and only explicit zero outside PK–8. If ungraded is offered, its own subtotal must be explicitly Reported zero. High, mixed, primary, unknown, adjusted, zero or unjoined profiles remain outside; no planning count approves membership.',
    'income': 'Own reported CCD Final 2a Direct Certification Education Unit Total divided by own positive reported same-year Membership Education Unit Total. Preserve the individual benefits/status proxy, including pre-K where enrolled. This is not full household-income FRPL or universal/CEP meal receipt. Both counts require Reported flags; no derived count, funding/claiming multiplier, FRPL fallback, tested subgroup or other-year backfill is used.',
    'income_metadata': 'Original Georgia CCD-0060 says Medicaid income was added to SNAP/TANF certification starting 2024 and foster records were received. Georgia membership covers state-funded programs and includes prekindergarten pupils in outside programs. Neither definition establishes the exact tested G38 population or completeness of direct certification; reporting coverage and undercount remain unknown.',
    'assessment': 'Only exact original EDC v3.1 SEA-sourced Georgia Milestones EOG regular School/All Students/All Students native G38 grades 3–8, Levels 3–4 published ProficientOrAbove_percent supports prospective rates. Use the direct original 0–1 token; never average grades, substitute count ratios, splice alternate assessments or pool subgroup/district rows. Native EOG totals do not establish accelerated pupils or EOC course coverage; that population treatment remains uncertified from the retained definitions. Original assessment-name/cut-score flags remain evidence; no EOC/alternate splice or incompatible history is created.',
    'counts': 'EDC tested, proficient and level counts remain raw unverified evidence and may be constructed from native displays. All valid-score denominators, variances and interval endpoints remain null; the ten-valid-scored floor is uncertified. Enrollment, direct certification, participation and federal 95% measures never substitute. Existing source holds remain without repeated failed investigations.',
    'attribution': 'Retain all original Georgia notes, exact named identities and later-release program gaps. No current Cobb-specific attribution warning is inferred from unrelated districts, and absence of a named note does not certify attribution completeness. School/district enrollment differences, if present, do not establish a cause.',
    'suppression': 'Explicit zero, suppressed/ranged, missing, nonreported and derived values remain distinct. No midpoint, complement or another-year backfill. Native-only identities remain unjoined without inferred school ownership or income.',
    'combined': 'Equal mean of exact usable original Math and ELA rates with own same-year individual income; not proficiency in both. A future Combined model needs its own fit, scale and studentization; this audit creates no models.',
    'limitations': 'Original charter, alternative/type, virtual and grade disagreement evidence is retained without admissions, provider, geometry, causal effectiveness or school-quality inference. Original Georgia EDC business-rule and tested-population limits remain explicit.',
    'approval': 'Source/cohort audit only: audit_pending/source_cohort_audit_only, both approvals false. Numerical, normalized, canonical, static, browser and publication gates remain separate.'}

# Generated immutable original pins and exact retained schemas are filled from
# freshly reopened originals before this module's first scientific freeze.
SOURCES = {'ccd_directory_2025': {'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip', 'bytes': 13352819, 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab'}, 'ccd_membership_2025': {'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip', 'bytes': 212696691, 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d'}, 'ccd_lunch_2025': {'path': 'data/raw/ccd_sch_033_2425_l_2a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_033_2425_l_2a_073025.zip', 'bytes': 14029439, 'sha256': '97bda749e778ee74cb731d181bbcdaf0f9c6cd6edf94cb31518a5bbeab411dd6'}, 'ccd_state_notes_2025': {'path': 'data/raw/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'bytes': 210984, 'sha256': '6476b6b28b700389e261b87377d9cd249935503d53b5919fe1b7ef8b1052d1a7'}, 'edc_codebook_v3_1': {'path': 'data/raw/EDC_codebook_v3.1.xlsx', 'url': 'https://www.eddatacenter.org/data_codebooks/EDC_codebook_v3.1.xlsx', 'bytes': 20401, 'sha256': 'cfaf3eeb482b416106e4a7b775c9554768fbf4900b0518c861979d646b6b2574'}, 'edc_technical_v3_1': {'path': 'data/raw/EDC_technical_documentation_v3.1.pdf', 'url': 'https://www.eddatacenter.org/data_documentation/EDC_technical_documentation_v3.1.pdf', 'bytes': 1100602, 'sha256': '749c52497e37cfd73c0e29afadea3d90d6b50950844f070247594f44254a7968'}, 'nces_lunch_definitions': {'path': 'data/raw/ccd-lunch-definition.html', 'url': 'https://nces.ed.gov/learn/blog/understanding-school-lunch-eligibility-common-core-data', 'bytes': 34948, 'sha256': '03f24547726ebf7529d946cee85f84e3de3ac3962b5dbc8b96e0a4db3744247d'}, 'edc_2025': {'path': 'data/raw/edc-2025/ga.csv', 'url': 'https://www.eddatacenter.org/api/data/3.1?state=GA&year=2025', 'bytes': 93271612, 'sha256': '38e3c39bdebd361d55055478e2f657a9e8c70d60781b9e60f47407c955f8cc6d'}, 'ccd_lea_directory': {'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip', 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', 'bytes': 2830266}, 'ccd_lea_membership': {'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip', 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', 'bytes': 68497561}, 'ccd_lunch_layout': {'path': 'data/raw/SY_2024-25_SCH_Lunch_Companion_2026-005d_2a.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Lunch_Companion_2026-005d_2a.xlsx', 'sha256': '6596d9e9a3c471ddd83b63d19a46514193220b7f3d66b91ddb0ad5e42d252008', 'bytes': 41935}, 'ccd_membership_layout': {'path': 'data/raw/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'sha256': 'cc3afc95a5226da12aec2f77b264477adfe9d85bb250e71c4dab534b5a591fd1', 'bytes': 40687}, 'ccd_directory_layout': {'path': 'data/raw/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'sha256': 'aa3be279c7a175be76ce43e451fb8ba513481e7a80f009abf7de3ad4cf33f8cf', 'bytes': 54414}, 'ga_all_students_crosscheck': {'path': 'data/raw/edc-2025/ga-all-students.json', 'url': 'https://www.eddatacenter.org/api/data/3.1?state=GA&year=2025', 'bytes': 18405919, 'sha256': 'afd8186f90f8814139ac0172b1fb064aa3abedbdbcb9920ed138d1d421da165a', 'role': 'Reproducible whole-state School/All Students/All Students Math/ELA original-record subset; exact original CSV cross-check, not a source of fitted results'}}
ORIGINAL_METADATA = {'directory': {'source_id': 'ccd_directory_2025', 'member': 'ccd_sch_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'SCH_TYPE_TEXT', 'SCH_TYPE', 'RECON_STATUS', 'OUT_OF_STATE_FLAG', 'CHARTER_TEXT', 'CHARTAUTH1', 'CHARTAUTHN1', 'CHARTAUTH2', 'CHARTAUTHN2', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED'], 'selection': 'All original rows belonging to exact NCES LEA1301290 or nativeGA-633, before any population/value selection.'}, 'lea_directory': {'source_id': 'ccd_lea_directory', 'member': 'ccd_lea_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'LEA_TYPE', 'LEA_TYPE_TEXT', 'OUT_OF_STATE_FLAG', 'CHARTER_LEA', 'CHARTER_LEA_TEXT', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED', 'OPERATIONAL_SCHOOLS'], 'selection': 'All original rows belonging to exact NCES LEA1301290 or nativeGA-633, before any population/value selection.'}, 'membership': {'source_id': 'ccd_membership_2025', 'member': 'ccd_sch_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'Complete original total/grade membership rows; explicit Not Specified/Derived-zero rows remain evidence.'}, 'lea_membership': {'source_id': 'ccd_lea_membership', 'member': 'ccd_lea_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'Complete original total/grade membership rows; explicit Not Specified/Derived-zero rows remain evidence.'}, 'lunch': {'source_id': 'ccd_lunch_2025', 'member': 'ccd_sch_033_2425_l_2a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'DATA_GROUP', 'LUNCH_PROGRAM', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'All original rows belonging to exact NCES LEA1301290 or nativeGA-633, before any population/value selection.'}, 'assessment': {'source_id': 'edc_2025', 'member': 'ga.csv', 'header_source_row': 1, 'header': ['State', 'StateAbbrev', 'StateFips', 'SchYear', 'DataLevel', 'DistName', 'SchName', 'NCESDistrictID', 'StateAssignedDistID', 'NCESSchoolID', 'StateAssignedSchID', 'AssmtName', 'AssmtType', 'Subject', 'GradeLevel', 'StudentGroup', 'StudentGroup_TotalTested', 'StudentSubGroup', 'StudentSubGroup_TotalTested', 'Lev1_count', 'Lev1_percent', 'Lev2_count', 'Lev2_percent', 'Lev3_count', 'Lev3_percent', 'Lev4_count', 'Lev4_percent', 'Lev5_count', 'Lev5_percent', 'AvgScaleScore', 'AvgSS_SD', 'ProficiencyCriteria', 'ProficientOrAbove_count', 'ProficientOrAbove_percent', 'ParticipationRate', 'Flag_AssmtNameChange', 'Flag_CutScoreChange_ELA', 'Flag_CutScoreChange_math', 'Flag_CutScoreChange_sci', 'Flag_CutScoreChange_soc', 'DistType', 'DistCharter', 'DistLocale', 'SchType', 'SchLevel', 'SchVirtual', 'CountyName', 'CountyCode', 'Version'], 'selection': 'Complete original All Students Math/ELA school/district grade and assessment rows, without a rate or cohort screen.'}}
ORIGINAL_INVENTORIES = {'directory': 110, 'lea_directory': 1, 'membership': 832, 'lea_membership': 16, 'lunch': 550, 'assessment': 751}
RAW_INPUT_SHA = '897c2c980a031f4f56e576760d8d42da568d133cdd68c293adb92068e85b6095'
ORIGINAL_SCHEMA_SHA = 'e17bb75e7e35a0e09cfba5ba5ed2d44d318fbd79544f2450c852a35305dd2384'
DEFINITION_INPUT_SHA = '0a3b0b7c7318ff0753626aa50d2971b8bdbfdff66395feeace75c53f731ed1b8'
ORIGINAL_IDENTITY_SHA = '2959a5cb97315bffc80f4960b220d5384fdc22a73a5a71ef09a1af8bab40d2a5'
STATE_EXTRACT_SHA = '3b6e55bba0055c582eb14a461697c64131a36e4cd555bca94965e5f77cac91fc'
GA_SNAPSHOT_SHA = '46d47899274835d484be76ac9b13515afb96474c54b5a676c4c43539df289a67'
POLICY_SHA = 'e6d705f3db9cbba7b9fd37c1cb555edc13911f05b04f90fb2c024ba334a408ca'
RUNTIME_CONTRACT_SHA = 'cfa96ba5bf716278657cca08affd12e2ef85f110f846c11f044b598fceccb22a'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def source_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def identity_fingerprint(inputs):
    ccd = ['SCHOOL_YEAR', 'ST', 'FIPST', 'LEAID', 'ST_LEAID', 'NCESSCH', 'ST_SCHID',
           'GRADE', 'TOTAL_INDICATOR', 'DATA_GROUP', 'LUNCH_PROGRAM']
    native = ['StateAbbrev', 'StateFips', 'SchYear', 'DataLevel', 'NCESDistrictID',
              'StateAssignedDistID', 'NCESSchoolID', 'StateAssignedSchID', 'AssmtName',
              'AssmtType', 'Subject', 'GradeLevel', 'StudentGroup', 'StudentSubGroup', 'Version']
    return fingerprint({table: [{'source_row': entry['source_row'],
        'compact_source_row': entry.get('compact_source_row'),
        'identity': {field: entry['raw'].get(field) for field in (native if table == 'assessment' else ccd)}}
        for entry in inputs[table]['records']] for table in TABLES})


def schema_fingerprint(inputs):
    return fingerprint({table: {key: value for key, value in inputs[table].items() if key != 'records'}
                        for table in TABLES})


def runtime_contract():
    return dict(lea=LEA, native_lea=NATIVE_LEA, native_district=NATIVE_DISTRICT, year=YEAR,
        academic_year=ACADEMIC_YEAR, tables=TABLES, operational=sorted(OPERATIONAL),
        offered_grades=OFFER_GRADES, lower_grades=LOWER_GRADES, subjects=SUBJECTS,
        selector=ASSESSMENT_SELECTOR, planning_fields=PLANNING_FIELDS, policy=POLICY,
        sources=SOURCES, metadata=ORIGINAL_METADATA, inventories=ORIGINAL_INVENTORIES,
        raw_sha=RAW_INPUT_SHA, schema_sha=ORIGINAL_SCHEMA_SHA, definition_sha=DEFINITION_INPUT_SHA,
        identity_sha=ORIGINAL_IDENTITY_SHA, secondary_sha=STATE_EXTRACT_SHA, ga_snapshot_sha=GA_SNAPSHOT_SHA)


def require_runtime_contract():
    if (POLICY_SHA != 'e6d705f3db9cbba7b9fd37c1cb555edc13911f05b04f90fb2c024ba334a408ca' or fingerprint(POLICY) != 'e6d705f3db9cbba7b9fd37c1cb555edc13911f05b04f90fb2c024ba334a408ca'
            or RUNTIME_CONTRACT_SHA != 'cfa96ba5bf716278657cca08affd12e2ef85f110f846c11f044b598fceccb22a'
            or fingerprint(runtime_contract()) != 'cfa96ba5bf716278657cca08affd12e2ef85f110f846c11f044b598fceccb22a'):
        raise ValueError('Immutable Cobb source policy/ownership/header/definition/fingerprint runtime changed')


def load_state_snapshot():
    require_runtime_contract()
    content = (ROOT / 'data/source/ccd-state-snapshots.json').read_bytes()
    if hashlib.sha256(content).hexdigest() != STATE_EXTRACT_SHA:
        raise ValueError('Complete original secondary statewide extract changed or disappeared')
    payload = json.loads(content)
    if type(payload['school_year']) is not str or payload['school_year'] != '2024-25':
        raise ValueError('Secondary original academic year changed')
    snapshot = next(s for s in payload['states'] if s['state']['id'] == 'GA')
    if fingerprint(snapshot) != GA_SNAPSHOT_SHA:
        raise ValueError('Complete original Georgia secondary snapshot changed')
    compact = SOURCES['ga_all_students_crosscheck']
    path = ROOT / compact['path']
    if path.stat().st_size != compact['bytes'] or source_sha(path) != compact['sha256']:
        raise ValueError('Complete original Georgia All Students cross-check changed or disappeared')
    return snapshot


def reported_count(raw):
    if raw is None:
        return None
    value = raw['STUDENT_COUNT']
    if type(value) is not str or type(raw['DMS_FLAG']) is not str:
        raise ValueError('Original CCD count/flag must retain strict string types')
    return int(value) if raw['DMS_FLAG'] == 'Reported' and re.fullmatch(r'\d+', value) else None


def exact_rate(value):
    if type(value) is not str:
        raise ValueError('Original published rate must retain its string token')
    if not re.fullmatch(r'(?:0?\.\d+|[01](?:\.\d+)?)', value):
        return None
    number = float(value)
    return 100 * number if 0 <= number <= 1 else None


def ccd_identity(raw, district=False):
    if (raw['SCHOOL_YEAR'], raw['ST'], raw['FIPST'], raw['STATENAME'], raw['LEAID'], raw['ST_LEAID']) != (
            ACADEMIC_YEAR, 'GA', '13', 'GEORGIA', LEA, NATIVE_LEA):
        raise ValueError('Original CCD exact state/year/LEA ownership changed')
    if district:
        return LEA
    if (not re.fullmatch(LEA + r'\d{5}', raw['NCESSCH'])
            or not re.fullmatch(r'GA-633-\d{4}', raw['ST_SCHID'])):
        raise ValueError('Original authoritative school NCES/native identity changed')
    return raw['NCESSCH']


def offered_evidence(raw):
    flags = {grade: raw['G_' + grade + '_OFFERED'] for grade in OFFER_GRADES}
    complete = raw['IGOFFERED'] == 'As reported' and raw['NOGRADES'] == 'No' and all(v in {'Yes', 'No'} for v in flags.values())
    offered = [grade for grade, value in flags.items() if value == 'Yes']
    lower = any(grade in offered for grade in ['PK', 'KG'] + [str(g) for g in range(1, 9)])
    high = any(str(g) in offered for g in range(9, 13))
    extra = any(grade in offered for grade in ['13', 'AE'])
    scope = 'uncertain' if not complete else 'other' if extra or not (lower or high) else 'mixed' if lower and high else 'HS' if high else 'ES'
    return dict(flags=flags, complete_reported_flags=complete, scope=scope, offered=offered,
        tested_grade_offers=[str(g) for g in range(3, 9) if flags[str(g)] == 'Yes'],
        low=raw['GSLO'], high=raw['GSHI'], level=raw['LEVEL'], ungraded_offered=flags['UG'])


def membership_evidence(total, grades):
    n = reported_count(total['raw']) if total else None
    values = {grade: reported_count(entry['raw']) for grade, entry in grades.items()}
    lower = [value for grade, value in values.items() if grade in LOWER_GRADES]
    complete = bool(lower) and all(value is not None for value in lower)
    subtotal = sum(lower) if complete else None
    outside_zero = all(entry['raw']['STUDENT_COUNT'] == '0' and entry['raw']['DMS_FLAG'] in {'Reported', 'Derived'}
                       for grade, entry in grades.items() if grade not in LOWER_GRADES)
    positive = any((values.get(f'Grade {g}') or 0) > 0 for g in range(3, 9))
    return dict(reported_total=n, total_source_row=total['source_row'] if total else None,
        grade_source_rows={grade: entry['source_row'] for grade, entry in grades.items()},
        reported_grade_counts=values, lower_grade_sum=subtotal, explicit_zero_outside_lower=outside_zero,
        positive_reported_tested_grade=positive, reconciled_pure_lower=complete and n is not None and subtotal == n and outside_zero,
        grade_rows_present=sorted(grades))


def income_evidence(total, direct):
    n = reported_count(total['raw']) if total else None
    dc = reported_count(direct['raw']) if direct else None
    if direct and (direct['raw']['DATA_GROUP'], direct['raw']['TOTAL_INDICATOR'], direct['raw']['LUNCH_PROGRAM']) != (
            'Direct Certification', 'Education Unit Total', 'Not Applicable'):
        raise ValueError('Direct certification row is outside its original individual category')
    reason = ('Missing/nonreported/nonpositive own membership' if n is None or n <= 0
              else 'Missing/suppressed/nonreported own direct certification' if dc is None
              else 'Direct certification exceeds own membership' if dc > n else None)
    pct = None if reason else 100 * dc / n
    return dict(reported_membership=n, reported_direct_certification=dc, reported_percentage=pct,
        percentage=pct, usable=reason is None, exclusion=reason,
        membership_source_row=total['source_row'] if total else None,
        direct_source_row=direct['source_row'] if direct else None,
        definition=POLICY['income'], valid_score_denominator=False)


def outcome_evidence(entry, subject, eligible, income):
    raw = entry['raw'] if entry else None
    rate = exact_rate(raw['ProficientOrAbove_percent']) if raw else None
    reason = ('No exact original regular All Students native G38 school row' if raw is None
              else 'Original published G38 rate suppressed/ranged/missing' if rate is None
              else 'Outside pure lower tested-grade configuration' if not eligible else income['exclusion'])
    return dict(subject=subject, native_rate=rate, raw_rate=raw['ProficientOrAbove_percent'] if raw else None,
        usable=reason is None and income['usable'], exclusion=reason, source='edc_2025',
        source_row=entry['source_row'] if entry else None,
        compact_source_row=entry.get('compact_source_row') if entry else None,
        raw_tested=raw['StudentSubGroup_TotalTested'] if raw else None,
        raw_proficient_count=raw['ProficientOrAbove_count'] if raw else None,
        tested=None, valid_scores=None, sampling_variance=None, low=None, high=None,
        sampling_interval_available=False, ten_valid_scored_floor_certified=False)


def retain_original_row(table, raw):
    if table in {'membership', 'lea_membership'}:
        return (raw['TOTAL_INDICATOR'] == 'Education Unit Total'
                or raw['TOTAL_INDICATOR'] == 'Subtotal 4 - By Grade' and (
                    raw['GRADE'] == 'Not Specified' or all(raw[k] == 'No Category Codes' for k in ['RACE_ETHNICITY', 'SEX'])))
    if table == 'assessment':
        return raw['StudentGroup'] == raw['StudentSubGroup'] == 'All Students' and raw['Subject'] in {'math', 'ela'}
    return True


def compact_original_inputs(inputs):
    result, omitted = {}, {}
    for table in TABLES:
        section = inputs[table]
        kept, rows, populations, identities = [], [], Counter(), defaultdict(list)
        for entry in section['records']:
            raw = entry['raw']
            if retain_original_row(table, raw):
                kept.append(entry)
                continue
            rows.append(entry['source_row'])
            if table == 'assessment':
                population = tuple(raw[k] for k in ['DataLevel', 'StudentGroup', 'StudentSubGroup', 'GradeLevel', 'Subject', 'AssmtType'])
                identity = raw['DataLevel'] + ':' + raw['NCESSchoolID']
            else:
                population = tuple(raw[k] for k in ['TOTAL_INDICATOR', 'GRADE', 'RACE_ETHNICITY', 'SEX'])
                identity = raw.get('NCESSCH', raw['LEAID'])
            populations[population] += 1
            identities[identity].append(entry['source_row'])
        selection = ('Complete original total/grade membership rows; explicit Not Specified/Derived-zero rows remain evidence.'
            if table in {'membership', 'lea_membership'} else 'Complete original All Students Math/ELA school/district grade and assessment rows, without a rate or cohort screen.'
            if table == 'assessment' else section['selection'])
        result[table] = {key: value for key, value in section.items() if key != 'records'}
        result[table].update(selection=selection, records=kept)
        omitted[table] = dict(complete_original_records=len(section['records']),
            complete_original_typed_cells=sum(len(e['raw']) for e in section['records']),
            complete_target_records_sha256=fingerprint(section['records']), retained_records=len(kept),
            omitted_records=len(rows), omitted_source_rows=rows,
            omitted_population_counts=[dict(original_population=list(k), records=v) for k, v in sorted(populations.items())],
            omitted_rows_by_original_identity=dict(sorted(identities.items())),
            basis='Original file pins and complete target hashes/ordinals; no numeric, income, charter, eligible-profile or diagnostic selection.')
    result.update(definitions=inputs['definitions'], planning=inputs['planning'],
                  ga_all_students_crosscheck=inputs['ga_all_students_crosscheck'], omitted_original_populations=omitted)
    return result


def validate_raw_inputs(inputs):
    require_runtime_contract()
    if fingerprint(inputs) != RAW_INPUT_SHA or schema_fingerprint(inputs) != ORIGINAL_SCHEMA_SHA:
        raise ValueError('Complete original raw cells, omitted inventory or source schema changed')
    if fingerprint(inputs['definitions']) != DEFINITION_INPUT_SHA or identity_fingerprint(inputs) != ORIGINAL_IDENTITY_SHA:
        raise ValueError('Complete original primary definitions or authoritative identity projection changed')
    for table in TABLES:
        section = inputs[table]
        if {k: v for k, v in section.items() if k != 'records'} != ORIGINAL_METADATA[table]:
            raise ValueError('Original header/member/source selection differs')
        if len(section['records']) != ORIGINAL_INVENTORIES[table]:
            raise ValueError('Original retained-row inventory differs')
        previous = 1
        for entry in section['records']:
            if type(entry['source_row']) is not int or entry['source_row'] <= previous:
                raise ValueError('Original source rows must be strict positive ordered integer references')
            previous = entry['source_row']
            if set(entry) - {'source_row', 'raw', 'compact_source_row'}:
                raise ValueError('Unknown original record envelope')
            if 'compact_source_row' in entry and (type(entry['compact_source_row']) is not int or entry['compact_source_row'] <= 0):
                raise ValueError('Compact original reference must be a strict positive integer')
            if type(entry['raw']) is not dict or set(entry['raw']) != set(section['header']) or any(type(v) is not str for v in entry['raw'].values()):
                raise ValueError('Complete original CSV fields and string cell types required')
    record = inputs['planning']['record']
    for field in ['directory_source_row', 'membership_source_row']:
        if type(record[field]) is not int or record[field] <= 0:
            raise ValueError('Planning original row reference must be a strict positive integer')


def _derive(document, state):
    inputs = document['raw_inputs']
    validate_raw_inputs(inputs)
    expected_header = {key: value for key, value in base_document(inputs).items() if key != 'raw_inputs'}
    if fingerprint({key: document.get(key) for key in expected_header}) != fingerprint(expected_header):
        raise ValueError('Source-only exact ownership/year/provenance/policy/false-approval metadata changed')
    directory, totals, direct, grades = {}, {}, {}, defaultdict(dict)
    for entry in inputs['directory']['records']:
        key = ccd_identity(entry['raw'])
        if key in directory:
            raise ValueError('Duplicate authoritative directory identity')
        directory[key] = entry
    for table in ['membership', 'lunch']:
        for entry in inputs[table]['records']:
            raw = entry['raw']
            key = ccd_identity(raw)
            if key not in directory or raw['ST_SCHID'] != directory[key]['raw']['ST_SCHID']:
                raise ValueError('CCD count identity lacks its exact native/NCES directory attachment')
            if table == 'membership':
                if raw['TOTAL_INDICATOR'] == 'Education Unit Total':
                    if key in totals:
                        raise ValueError('Duplicate school membership total')
                    totals[key] = entry
                elif raw['TOTAL_INDICATOR'] == 'Subtotal 4 - By Grade' and raw['RACE_ETHNICITY'] == raw['SEX'] == 'No Category Codes':
                    if raw['GRADE'] in grades[key]:
                        raise ValueError('Duplicate exact school grade subtotal')
                    grades[key][raw['GRADE']] = entry
            elif raw['DATA_GROUP'] == 'Direct Certification' and raw['TOTAL_INDICATOR'] == 'Education Unit Total':
                if key in direct:
                    raise ValueError('Duplicate individual direct certification total')
                direct[key] = entry
    for table in ['lea_directory', 'lea_membership']:
        for entry in inputs[table]['records']:
            ccd_identity(entry['raw'], district=True)
    if len(inputs['lea_directory']['records']) != 1:
        raise ValueError('Unique original authoritative LEA directory record required')
    native_rows, pairs, district_rows = defaultdict(list), defaultdict(dict), []
    for entry in inputs['assessment']['records']:
        raw = entry['raw']
        if (raw['StateAbbrev'], raw['StateFips'], raw['SchYear'], raw['NCESDistrictID'], raw['StateAssignedDistID'], raw['Version']) != (
                'GA', '13', '2024-25', LEA, NATIVE_DISTRICT, 'V3.1'):
            raise ValueError('Original native assessment crossed exact district/state/year ownership')
        if raw['DataLevel'] == 'School':
            key = raw['NCESSchoolID']
            if not re.fullmatch(LEA + r'\d{5}', key) or not re.fullmatch(r'633-\d{4}', raw['StateAssignedSchID']):
                raise ValueError('Original native school identifier malformed; never repair it')
            if key in directory and 'GA-' + raw['StateAssignedSchID'] != directory[key]['raw']['ST_SCHID']:
                raise ValueError('Native/NCES crosswalk disagrees with authoritative directory')
            native_rows[key].append(entry['source_row'])
        elif raw['DataLevel'] != 'District':
            raise ValueError('Unexpected original native data level')
        selected = all(raw[k] == value for k, value in ASSESSMENT_SELECTOR.items()) and raw['Subject'] in SUBJECTS.values()
        if selected:
            key = raw['NCESSchoolID']
            subject = 'reading' if raw['Subject'] == 'ela' else 'math'
            if subject in pairs[key]:
                raise ValueError('Duplicate exact regular All Students G38 subject')
            pairs[key][subject] = entry
        if raw['DataLevel'] == 'District' and raw['GradeLevel'] == 'G38':
            district_rows.append(entry['source_row'])
    secondary = {row['id']: row for row in state['schools']}
    links = []
    for key, entry in directory.items():
        raw = entry['raw']
        offered = offered_evidence(raw)
        membership = membership_evidence(totals.get(key), grades.get(key, {}))
        operational = raw['UPDATED_STATUS'] in OPERATIONAL
        ungraded_ok = offered['ungraded_offered'] != 'Yes' or membership['reported_grade_counts'].get('Ungraded') == 0
        eligible = bool(operational and offered['scope'] == 'ES' and re.fullmatch(r'0[1-8]', offered['high'])
            and offered['tested_grade_offers'] and membership['reported_total'] is not None and membership['reported_total'] > 0
            and membership['reconciled_pure_lower'] and membership['positive_reported_tested_grade'] and ungraded_ok)
        income = income_evidence(totals.get(key), direct.get(key))
        subjects = {s: outcome_evidence(pairs.get(key, {}).get(s), s, eligible, income) for s in SUBJECTS}
        math, ela = subjects['math'], subjects['reading']
        paired = math['native_rate'] is not None and ela['native_rate'] is not None
        subjects['combined'] = dict(subject='combined', native_rate=(math['native_rate'] + ela['native_rate']) / 2 if paired else None,
            raw_rate={'math': math['raw_rate'], 'reading': ela['raw_rate']}, usable=math['usable'] and ela['usable'],
            exclusion=None if math['usable'] and ela['usable'] else 'Combined requires both exact usable original subjects and own same-year income',
            source='edc_2025', source_row={'math': math['source_row'], 'reading': ela['source_row']},
            raw_tested={'math': math['raw_tested'], 'reading': ela['raw_tested']}, tested=None, valid_scores=None,
            sampling_variance=None, low=None, high=None, sampling_interval_available=False, ten_valid_scored_floor_certified=False)
        cross = secondary.get(key)
        if cross:
            if (cross['enrollment'], cross['low_income'], cross['income']) != (income['reported_membership'], income['reported_direct_certification'], income['reported_percentage']):
                raise ValueError('Secondary same-year original individual income fields differ')
            if any(cross['outcomes'][s]['proficiency'] != subjects[s]['native_rate'] for s in SUBJECTS):
                raise ValueError('Secondary original G38 rates differ; never reuse state fits')
        reason = None if eligible else ('School not operational' if not operational
            else 'Outside complete pure lower grade offerings' if offered['scope'] != 'ES'
            else 'Primary-only: no offered/enrolled tested grades 3–8' if not offered['tested_grade_offers'] or not membership['positive_reported_tested_grade']
            else 'Unreported/nonpositive/unreconciled or ambiguous own enrolled grade scope')
        links.append(dict(school_id=key, ncessch=key, native_school_id=raw['ST_SCHID'], name=raw['SCH_NAME'],
            directory_source_row=entry['source_row'], operational=operational,
            ccd_flags=dict(status=raw['UPDATED_STATUS'], status_text=raw['UPDATED_STATUS_TEXT'],
                           charter=raw['CHARTER_TEXT'], school_type=raw['SCH_TYPE_TEXT']),
            offered=offered, membership=membership, income=income, source_profile_eligible=eligible,
            population_exclusion=reason, source_attribution_hold=None,
            native_school_source_rows=native_rows.get(key, []), subjects=subjects, secondary_original_fields_crosschecked=cross is not None))
    profiles = [row for row in links if row['source_profile_eligible']]
    native_only = [dict(ncessch=key, native_source_rows=native_rows[key],
        g38_source_rows={s: entry['source_row'] for s, entry in pairs.get(key, {}).items()},
        exclusion='Original native identity lacks exact same-year CCD directory attachment; no name repair or inferred income')
        for key in sorted(set(native_rows) - set(directory))]
    lea_totals = [entry for entry in inputs['lea_membership']['records'] if entry['raw']['TOTAL_INDICATOR'] == 'Education Unit Total']
    if len(lea_totals) != 1:
        raise ValueError('Unique original LEA membership total required')
    lea_n = reported_count(lea_totals[0]['raw'])
    operational_n = [row['membership']['reported_total'] for row in links if row['operational']]
    total_n = sum(value for value in operational_n if value is not None)
    planning = inputs['planning']['record']
    if planning['nces_lea_id'] != LEA or planning['native_lea_id'] != NATIVE_LEA or planning['enrollment'] != lea_n:
        raise ValueError('Planning identity/enrollment does not reconcile to fresh original LEA')
    for field, value in planning['directory_raw'].items():
        if inputs['lea_directory']['records'][0]['raw'][field] != value:
            raise ValueError('Planning raw original directory fields differ')
    if planning['directory_source_row'] != inputs['lea_directory']['records'][0]['source_row']:
        raise ValueError('Planning directory reference differs from its original integer row')
    if planning['membership_raw'] != lea_totals[0]['raw'] or planning['membership_source_row'] != lea_totals[0]['source_row']:
        raise ValueError('Planning raw LEA membership/row reference differs')
    notes = inputs['definitions']['ccd_state_notes_2025']['worksheets']
    ga_notes = [dict(worksheet=name, source_row=e['source_row'], raw=e['raw']) for name, sheet in notes.items()
                for e in sheet['records'] if any(type(value) is str and ('Georgia' in value or value == 'GEORGIA') for value in e['raw'])]
    named = [entry for entry in ga_notes if any(type(value) is str and re.search(r'\b1301290(?:\d{5})?\b', value) for value in entry['raw'])]
    omissions = inputs['omitted_original_populations']
    usable = {s: sum(row['subjects'][s]['usable'] for row in profiles) for s in ['math', 'reading', 'combined']}
    raw_rates = {s: sum(row['subjects'][s]['native_rate'] is not None for row in profiles) for s in ['math', 'reading', 'combined']}
    coverage = dict(source_rows={table: len(inputs[table]['records']) for table in TABLES},
        original_records=sum(len(inputs[table]['records']) for table in TABLES),
        original_typed_cells=sum(sum(len(entry['raw']) for entry in inputs[table]['records']) for table in TABLES),
        complete_original_source_rows={table: omissions[table]['complete_original_records'] for table in TABLES},
        complete_original_records=sum(value['complete_original_records'] for value in omissions.values()),
        complete_original_typed_cells=sum(value['complete_original_typed_cells'] for value in omissions.values()),
        omitted_original_records=sum(value['omitted_records'] for value in omissions.values()),
        directory_records=len(links), operational_roster=sum(row['operational'] for row in links),
        status=dict(Counter(row['ccd_flags']['status_text'] for row in links)),
        operational_offered_scope=dict(Counter(row['offered']['scope'] for row in links if row['operational'])),
        operational_CCD_school_types=dict(Counter(row['ccd_flags']['school_type'] for row in links if row['operational'])),
        operational_CCD_charters=dict(Counter(row['ccd_flags']['charter'] for row in links if row['operational'])),
        original_native_assessment_names=sorted({entry['raw']['AssmtName'] for entry in inputs['assessment']['records']}),
        original_native_assessment_types=sorted({entry['raw']['AssmtType'] for entry in inputs['assessment']['records']}),
        original_native_grade_codes=sorted({entry['raw']['GradeLevel'] for entry in inputs['assessment']['records']}),
        EOG_accelerated_EOC_population_certified=False,
        prospective_grade_profiles=len(profiles), prospective_raw_published_rates=raw_rates, prospective_usable=usable,
        prospective_charters=sum(row['ccd_flags']['charter'] == 'Yes' for row in profiles),
        usable_charters={s: sum(row['ccd_flags']['charter'] == 'Yes' and row['subjects'][s]['usable'] for row in profiles) for s in usable},
        primary_only_ids=[row['school_id'] for row in links if row['population_exclusion'] and row['population_exclusion'].startswith('Primary-only')],
        native_only_ids=[row['ncessch'] for row in native_only], native_school_ids=len(native_rows),
        membership_school_totals=len(totals), direct_certification_school_totals=len(direct),
        missing_operational_membership_ids=[row['school_id'] for row in links if row['operational'] and row['membership']['reported_total'] is None],
        missing_operational_direct_certification_ids=[row['school_id'] for row in links if row['operational'] and row['income']['reported_direct_certification'] is None],
        district_reported_enrollment=lea_n, reported_operational_enrollment_sum=total_n,
        missing_operational_enrollment_count=sum(value is None for value in operational_n),
        district_minus_reported_operational_enrollment=lea_n - total_n if lea_n is not None else None,
        secondary_original_profile_matches=sum(row['secondary_original_fields_crosschecked'] for row in links),
        explicit_Cobb_named_primary_notes=len(named), verified_valid_score_counts=0,
        ten_valid_scored_floor_certified=False, model_sampling_intervals_available=False,
        canonical_integration_pending=True, model_results=0)
    return dict(roster_links=links, outside_native_profiles=native_only, district_native_g38_source_rows=district_rows,
        cohorts=dict(grade_configuration=dict(profile_ids=[row['school_id'] for row in profiles],
            subjects={s: dict(raw_published_available=raw_rates[s], usable=usable[s],
                member_ids=[row['school_id'] for row in profiles if row['subjects'][s]['usable']],
                charter=dict(Counter(row['ccd_flags']['charter'] for row in profiles if row['subjects'][s]['usable']))) for s in usable})),
        coverage=coverage, raw_schema_sha256=ORIGINAL_SCHEMA_SHA, raw_definition_sha256=DEFINITION_INPUT_SHA,
        original_identity_sha256=ORIGINAL_IDENTITY_SHA, source_policy_sha256=POLICY_SHA,
        source_runtime_sha256=RUNTIME_CONTRACT_SHA,
        source_definition_evidence=dict(original_definition_sha256=DEFINITION_INPUT_SHA,
            whole_primary_sources=sorted(inputs['definitions']), Georgia_original_notes=ga_notes,
            exact_Cobb_named_notes=named, note_absence_does_not_certify_attribution=True))


def derive(document, snapshot=None):
    state = load_state_snapshot()
    if snapshot is not None and fingerprint(snapshot) != GA_SNAPSHOT_SHA:
        raise ValueError('Cached original Georgia secondary differs')
    return _derive(document, state)


def base_document(inputs):
    return dict(schema_version=1, state='GA', year=YEAR, academic_year=ACADEMIC_YEAR,
        nces_lea_id=LEA, native_lea_id=NATIVE_LEA, native_district_id=NATIVE_DISTRICT,
        status='audit_pending', scope='source_cohort_audit_only', approved_for_source=False,
        approved_for_modeling=False, sources=SOURCES, policy=POLICY, raw_inputs=inputs,
        state_extract=dict(path='data/source/ccd-state-snapshots.json', sha256=STATE_EXTRACT_SHA,
                           GA_snapshot_sha256=GA_SNAPSHOT_SHA))


def validate(document, snapshot=None):
    expected = base_document(document['raw_inputs'])
    expected.update(derive(document, snapshot))
    if fingerprint(document) != fingerprint(expected):
        raise ValueError('Complete original source metadata/cohort/rates/limits/raw replay differs')
    return expected['coverage']


def read_csv_archive(source_id):
    path = ROOT / SOURCES[source_id]['path']
    with zipfile.ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if name.endswith('.csv'))
    process = subprocess.Popen(['unzip', '-p', str(path), member], stdout=subprocess.PIPE, text=True, encoding='utf-8-sig')
    try:
        reader = csv.DictReader(process.stdout)
        rows = [dict(source_row=i, raw=raw) for i, raw in enumerate(reader, 2)
                if raw.get('LEAID') == LEA or raw.get('ST_LEAID') == NATIVE_LEA]
        if process.wait() != 0:
            raise ValueError('Original pinned archive cannot be decompressed')
        return member, reader.fieldnames, rows
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()


def extract_raw_inputs():
    require_runtime_contract()
    for source in SOURCES.values():
        path = ROOT / source['path']
        if path.stat().st_size != source['bytes'] or source_sha(path) != source['sha256']:
            raise ValueError('Complete original source byte pin changed: ' + source['path'])
    inputs = {}
    for table, key in [('directory', 'ccd_directory_2025'), ('lea_directory', 'ccd_lea_directory'),
        ('membership', 'ccd_membership_2025'), ('lea_membership', 'ccd_lea_membership'), ('lunch', 'ccd_lunch_2025')]:
        member, header, rows = read_csv_archive(key)
        inputs[table] = dict(ORIGINAL_METADATA[table], member=member, header=header, records=rows)
    compact_rows, rows, ordinals, ordinal = [], [], defaultdict(list), 0
    with (ROOT / SOURCES['edc_2025']['path']).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        for number, raw in enumerate(reader, 2):
            compact = (raw['DataLevel'] == 'School' and raw['StudentGroup'] == raw['StudentSubGroup'] == 'All Students'
                       and raw['Subject'] in SUBJECTS.values())
            if compact:
                ordinal += 1
                compact_rows.append(raw)
            if raw['NCESDistrictID'] == LEA or raw['StateAssignedDistID'] == NATIVE_DISTRICT:
                entry = dict(source_row=number, raw=raw)
                if compact:
                    entry['compact_source_row'] = ordinal
                    ordinals[raw['NCESSchoolID']].append(ordinal)
                rows.append(entry)
        inputs['assessment'] = dict(ORIGINAL_METADATA['assessment'], header=reader.fieldnames, records=rows)
    if compact_rows != json.loads((ROOT / SOURCES['ga_all_students_crosscheck']['path']).read_text()):
        raise ValueError('Complete original Georgia All Students subset differs from pinned original CSV')
    inputs['ga_all_students_crosscheck'] = dict(source_id='ga_all_students_crosscheck', complete_record_count=ordinal,
        complete_records_sha256=fingerprint(compact_rows), district_original_school_ordinals=dict(ordinals),
        basis='Ordinal in complete original School/All Students/All Students Math/ELA subset, starting at1; every subset row exactly equals the original CSV.')
    import openpyxl
    from pypdf import PdfReader
    def cell(value):
        return dict(original_type=type(value).__name__, value=value.isoformat()) if isinstance(value, (datetime.datetime, datetime.date, datetime.time)) else value
    definitions = {}
    for key in ['ccd_state_notes_2025', 'edc_codebook_v3_1', 'ccd_lunch_layout', 'ccd_membership_layout', 'ccd_directory_layout']:
        book = openpyxl.load_workbook(ROOT / SOURCES[key]['path'], read_only=True, data_only=True)
        try:
            definitions[key] = dict(source_id=key, worksheets={name: dict(worksheet=name,
                records=[dict(source_row=i, raw=[cell(value) for value in row]) for i, row in enumerate(book[name].values, 1)]) for name in book.sheetnames})
        finally:
            book.close()
    definitions['edc_technical_v3_1'] = dict(source_id='edc_technical_v3_1',
        pages=[dict(page_number=i + 1, text=page.extract_text() or '') for i, page in enumerate(PdfReader(ROOT / SOURCES['edc_technical_v3_1']['path']).pages)])
    definitions['nces_lunch_definitions'] = dict(source_id='nces_lunch_definitions', original_html=(ROOT / SOURCES['nces_lunch_definitions']['path']).read_text())
    inputs['definitions'] = definitions
    planning = json.loads((ROOT / 'data/source/district-comparison-candidates.json').read_text())
    row = next(r for r in planning['agencies'] if r['nces_lea_id'] == LEA)
    inputs['planning'] = dict(source='data/source/district-comparison-candidates.json', sources=planning['sources'],
                             record={key: row[key] for key in PLANNING_FIELDS})
    return compact_original_inputs(inputs)


def extract(output=OUTPUT):
    document = base_document(extract_raw_inputs())
    document.update(derive(document))
    validate(document)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(document, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    return document['coverage']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = extract(args.output) if args.extract else validate(json.loads(args.output.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

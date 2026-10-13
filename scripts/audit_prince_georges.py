"""Audit original Prince George’s County 2024–25 sources and cohorts without fitting.

--extract reads pinned MSDE and CCD originals. Normal validation is an offline
replay of the complete retained original district rows, including exclusions.
Neither path imports a database, fits a model or changes website output.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import re
import statistics
import subprocess
import zipfile

import openpyxl

import prepare_maryland as maryland
import plan_district_comparisons as planning
from state_registry import reported_count

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/prince-georges-district-audit.json'
LEA = '2400510'
NATIVE_LEA = 'MD-16'
MSDE_LEA = '16'
YEAR = 2025
ACADEMIC_YEAR = '2024-2025'
STATE_EXTRACT_SHA = '220a515c2193d4251fd2720719b09576ecf0d54a5349cb6b262b5a6a77fd4bb6'
STATE_SNAPSHOT_SHA = '276bcdd97d7041eea68399db61d059f8ebed6d11af973cb60e280082018eae69'
RAW_INPUT_SHA = 'd73cee70ffb91b37d7f63ef5e7947621d5c59250264fed969012d4bad7ed8708'
SOURCES = {
    'msde_directory': dict(path='data/raw/maryland-directory-2025.zip', bytes=146494, sha256='963f3447d40eb95586efa6f7250c96cd55818313015178a30d05b0b637a916fa', url=maryland.BASE+'DataDownloads/FileDownload/539'),
    'msde_enrollment': dict(path='data/raw/maryland-enrollment-2025.zip', bytes=139374, sha256='132b3520b0c75e1cbcb83b40a5b8c8b6fa1f064fb300c14710a75dd72b73c061', url=maryland.BASE+'DataDownloads/FileDownload/541'),
    'msde_income': dict(path='data/raw/maryland-special-services-2025.zip', bytes=60599, sha256='3ed47214da42d4d3bbb88077b3598637a56e8eba52498216dc9c923547984d5c', url=maryland.BASE+'DataDownloads/FileDownload/561'),
    'msde_assessment': dict(path='data/raw/maryland-mcap-2025.zip', bytes=1710773, sha256='61789e732bbeff40a451d14a0e6eeb66c0dac54430c26c7ed49db9718aab583f', url=maryland.BASE+'DataDownloads/FileDownload/562'),
    'msde_definitions': dict(path='data/raw/maryland-definitions.html', bytes=145159, sha256='5086eb37ee1de68c9aa22f9e7d2606f8d7550acfaeb85bd2b139c3f765d2f3f7', url=maryland.DEFINITIONS),
    'msde_reportcard': dict(path='data/raw/maryland-reportcard.html', bytes=110424, sha256='9857e65d009ccc6614beeaa12e289cbb93c37c8c67f809d394226dc19b5f8125', url='https://reportcard.msde.maryland.gov/graphs'),
    'msde_mcap_overview': dict(path='data/raw/montgomery-mcap-overview-march2025.pdf', bytes=98197, sha256='594f383d7917939572b99d293e89582decfc7819f5a888de21e2b9b6cbcb4680', url='https://www.marylandpublicschools.org/about/Documents/DAAIT/Assessment/MCAP/MCAP-Overview-A.pdf', resolved_url='https://msde.maryland.gov/media/17526'),
    'ccd_directory': dict(path='data/raw/ccd_sch_029_2425_w_1a_073025.zip', bytes=13352819, sha256='39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab', url='https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip'),
    'ccd_membership': dict(path='data/raw/ccd_sch_052_2425_l_1a_073025.zip', bytes=212696691, sha256='4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d', url='https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip'),
    'ccd_lea_directory': dict(path='data/raw/ccd_lea_029_2425_w_1a_073025.zip', bytes=2830266, sha256='2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', url='https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip'),
    'ccd_lea_membership': dict(path='data/raw/ccd_lea_052_2425_l_1a_073025.zip', bytes=68497561, sha256='501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', url='https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip'),
}
GRADES = ['PK', 'KG'] + [str(g) for g in range(1, 14)] + ['UG', 'AE']
OPERATIONAL = {'1', '3', '4', '5', '8'}
POLICY = {
    'identity': 'Exact original 2025 MSDE two-digit LEA16 and four-digit school codes join same-year native collections. The native directory NCES Number joins original CCD NCESSCH within NCES LEA2400510/native MD-16. Preserve CCD ST_SCHID separately; names and inferred code conversions never establish ownership.',
    'roster': 'Retain the complete original district MSDE and CCD directories, all exact district CCD school total/grade rows, district total/directory, every native Early Attendance and September grade row including district aggregates, and every original regular Math/ELA School_Level and LEA_Level All Students grade/course/All Grades row. Outside, unmatched, nonoperational and future records remain evidence, never inferred members.',
    'population': 'Prospective grade-school source profiles require original native E/M/EM grade span, exact operational CCD identity, complete unadjusted PK–8 offered-grade flags with a tested grade3–8 and no high/adult/ungraded offers, and native September grade rows with at least one numeric positive grade3–8 count and no grade9–12 row even when zero or suppressed. Adjusted offers, only-zero/unknown lower counts and unknown/ungraded/adult labels never become a certified tested-grade configuration. Independently reconcile CCD total/grade records for descriptive evidence. Native high, mixed, primary and unknown spans stay separate; planning and fit quality never select members.',
    'assessment': 'Use only native regular School_Level Year2025 Student Group=All Students Mathematics All Grades or English Language Arts All Grades published Proficient Pct, preserving its leading/trailing whitespace raw. Original MSDE reportcard assessment notes establish proficiency as Levels3/4 under the regular four-level ELA/math standards introduced in2021–22. Native All Grades Math includes accelerated high-school course tests at middle schools, including Algebra1/Geometry/Algebra2, instead of averaging grades or substituting grade3–8 tests. Alternate DLM is a separate collection and never enters regular MCAP. High/mixed populations remain unreleased.',
    'accelerated_scope': 'The original March2025 MCAP overview documents March17,2025 grade6–7 high-school-course waiver for2024–25 through2027–28. Course row presence does not certify student participation: preserve numeric and starred Algebra1/Geometry/Algebra2 counts separately. Original native All Grades totals, not component sums or averaged grade percentages, are the prospective outcomes.',
    'income': maryland.ECON,
    'denominator': 'Use individual Economically Disadvantaged Cnt divided by its own Early Attendance Total Student Cnt, reconciling the published one-decimal percentage within0.0500001 percentage point. Keep the native whole-school All row for multiband schools; a lone band row establishes the complete native school income record. Never replace with September/CCD enrollment, FARMS, participation, tested subgroup or another year. The collection as-of date is unspecified in the pinned definition.',
    'suppression': 'Published exact numeric percentage0–100 is usable; <=5.0, >=95.0, *, blank and ranges remain unavailable. Do not reconstruct a masked percentage/count from complements, bands, other performance levels, or another denominator.',
    'counts': 'Administrative Tested Count is raw evidence only. Exact valid-score business rules and the ten-valid-scored school minimum remain uncertified. Every normalized tested count, valid score, sampling variance and interval remains null/unavailable. Enrollment, federal95% adjustment and participation are not substitutions.',
    'combined': 'Equally weighted mean of usable native Math and ELA published rates with same-year usable income; not percentage proficient in both.',
    'approval': 'Source/cohort audit only: status audit_pending, scope source_cohort_audit_only, approved_for_source=false, approved_for_modeling=false. No model fits, canonical imports, catalog updates or browser release. Separate independent numerical diagnostics and integration remain required.',
}
POLICY['identity_holds'] = 'Keep all201 CCD rows and204 native profiles. Native16-0218 has an exact original11-digit NCES Number24005109050 and no authoritative crosswalk to CCD240051090501; preserve separately without correction/composition/slicing/name joins. Other native-only and closed CCD entries remain explicit exclusions, never invented matches.'
POLICY['income_denominator_discrepancy'] = 'Native September district132151 differs from CCD132123 by28; unmatched native JACS reports28 but this does not establish administrative cause or repair ownership. Early Attendance133427 equals known native denominators while six cells remain unavailable; aggregate equality does not imply zero or allocate them.'
PLANNING = dict(source='data/source/district-comparison-candidates.json', operational_roster=199,
                enrollment=132123, potential_ES=160, potential_HS=23,
                explanation='Original identities and membership reconstruct the discovery screen; size/planning counts do not approve a district model.')
REPORTCARD_EVIDENCE = dict(source_id='msde_reportcard',section_references=['2022ELASpecAssessFootnote','2022MathSpecAssessFootnote'],
    original_line_references=[1612,1616],
    paraphrase='MSDE identifies the regular four-level ELA and mathematics assessments introduced in2021–22 and defines proficient students as those reaching performance Levels3 or4. This threshold evidence is separate from the March2025 overview of grade/course populations.',
    limitations='The performance-level note does not certify administrative Tested Count as valid scores or establish a ten-valid-scored floor.')


TABLES = ['directory', 'lea_directory', 'membership', 'lea_membership', 'native_directory', 'native_assessment', 'native_enrollment', 'native_income']
ORIGINAL_HEADERS = {'directory': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'SCH_TYPE_TEXT', 'SCH_TYPE', 'RECON_STATUS', 'OUT_OF_STATE_FLAG', 'CHARTER_TEXT', 'CHARTAUTH1', 'CHARTAUTHN1', 'CHARTAUTH2', 'CHARTAUTHN2', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED'], 'lea_directory': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'LEA_TYPE', 'LEA_TYPE_TEXT', 'OUT_OF_STATE_FLAG', 'CHARTER_LEA', 'CHARTER_LEA_TEXT', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED', 'OPERATIONAL_SCHOOLS'], 'membership': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'lea_membership': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'native_directory': ['Year', 'LEA', 'LEA Name', 'School', 'School Name', 'Grade Span', 'School Type', 'Address', 'City', 'State', 'Zip', 'Phone', 'NCES Number', 'Create Date'], 'native_assessment': ['Year', 'LEA', 'LEA Name', 'School', 'School Name', 'Assessment', 'Student Group', 'Tested Count', 'Proficient Count', 'Proficient Pct', 'Level 1 Pct', 'Level 2 Pct', 'Level 3 Pct', 'Level 4 Pct', 'Create Date'], 'native_enrollment': ['Year', 'LEA', 'LEA Name', 'School', 'School Name', 'Grade', 'Enrolled Count', 'Create Date'], 'native_income': ['Academic Year', 'LEA Number', 'LEA Name', 'School Number', 'School Name', 'School Type', 'Ada504 Pct', 'Ada504 Cnt', 'FARMS Pct', 'FARMS Cnt', 'Multilingual Learner Pct', 'Multilingual Learner Cnt', 'Migrant Pct', 'Migrant Cnt', 'Students with Disabilities Pct', 'Students with Disabilities Cnt', 'Title1 Pct', 'Title1 Cnt', 'Homeless Pct', 'Homeless Cnt', 'Foster Care Pct', 'Foster Care Cnt', 'Military Connected Pct', 'Military Connected Cnt', 'Economically Disadvantaged Pct', 'Economically Disadvantaged Cnt', 'Gifted Talented Pct', 'Gifted Talented Cnt', 'Total Student Cnt', 'Create Date']}
ORIGINAL_TABLE_METADATA = {'directory': {'source_id': 'ccd_directory', 'member': 'ccd_sch_029_2425_w_1a_073025.csv', 'header_source_row': 1}, 'lea_directory': {'source_id': 'ccd_lea_directory', 'member': 'ccd_lea_029_2425_w_1a_073025.csv', 'header_source_row': 1}, 'membership': {'source_id': 'ccd_membership', 'member': 'ccd_sch_052_2425_l_1a_073025.csv', 'header_source_row': 1}, 'lea_membership': {'source_id': 'ccd_lea_membership', 'member': 'ccd_lea_052_2425_l_1a_073025.csv', 'header_source_row': 1}, 'native_directory': {'source_id': 'msde_directory', 'worksheets': ['School Directory'], 'header_source_row': 1}, 'native_assessment': {'source_id': 'msde_assessment', 'worksheets': ['School_Level', 'LEA_Level'], 'header_source_row': 1, 'selection': 'Complete original district regular School_Level and LEA_Level All Students grade/course/All Grades rows; district aggregates and alternate assessments never substitute school regular outcomes.'}, 'native_enrollment': {'source_id': 'msde_enrollment', 'member': 'Enrollment_By_Grade_2025.csv', 'header_source_row': 1}, 'native_income': {'source_id': 'msde_income', 'member': '2025_Special_Services.csv', 'header_source_row': 1}}
ORIGINAL_INVENTORIES = {'directory': 201, 'lea_directory': 1, 'membership': 1630, 'lea_membership': 16, 'native_directory': 204, 'native_assessment': 1665, 'native_enrollment': 1432, 'native_income': 255}
ORIGINAL_SCHEMA_SHA = 'e2bb249f4fa01a29619d0c2c54c8a1237e7062752a43e66af2d59e2bd0505fb5'
DEFINITION_INPUT_SHA = '9a3f18b926c3639e4a2152ab0ce93ae513dd5f5b660bd5aafd49af1e1d2e4eac'
POLICY_SHA = '6bee3876109f64b15621bc28dea7eac88acadb99d3555c9b92962bd07c36ef68'
ORIGINAL_IDENTITY_SHA = 'f326855a6626e853568bf1a91cf68b8f6bde256e318971ef76fa85256b3b9f66'
MALFORMED_NATIVE_NCES = {'16-0218': {'raw_nces': 24005109050, 'directory_source_row': 942}}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def identity_fingerprint(inputs):
    fields = {
        'directory': ['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH'],
        'membership': ['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH','TOTAL_INDICATOR','GRADE','RACE_ETHNICITY','SEX','DMS_FLAG'],
        'lea_directory': ['SCHOOL_YEAR','ST','LEAID','ST_LEAID'],
        'lea_membership': ['SCHOOL_YEAR','ST','LEAID','ST_LEAID','TOTAL_INDICATOR','GRADE','RACE_ETHNICITY','SEX','DMS_FLAG'],
        'native_directory': ['Year','LEA','School','NCES Number','State','Grade Span'],
        'native_enrollment': ['Year','LEA','School','Grade'],
        'native_income': ['Academic Year','LEA Number','School Number','School Type'],
        'native_assessment': ['Year','LEA','School','Assessment','Student Group'],
    }
    return fingerprint({table:[dict(source_row=e['source_row'],member=e.get('member'),worksheet=e.get('worksheet'),
        identity={f:e['raw'].get(f) for f in fields[table]}) for e in inputs[table]['records']] for table in TABLES})


def load_maryland(path=maryland.EXTRACT):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != STATE_EXTRACT_SHA:
        raise ValueError('Complete pinned Maryland comparison changed; fresh district audit required')
    snapshot = json.loads(data)
    maryland.validate(snapshot)
    return snapshot


def ccd_identity(raw, *, directory=False, district=False):
    if (raw.get('SCHOOL_YEAR'), raw.get('ST'), raw.get('LEAID'), raw.get('ST_LEAID')) != (ACADEMIC_YEAR, 'MD', LEA, NATIVE_LEA):
        raise ValueError('Exact same-year NCES/native Prince George’s identity required')
    if district:
        return LEA
    if (not re.fullmatch(LEA+r'\d{5}', raw.get('NCESSCH', ''))
            or not re.fullmatch(r'MD-16-\d{6}', raw.get('ST_SCHID', ''))):
        raise ValueError('Exact authoritative CCD school identity required')
    if directory and raw.get('UPDATED_STATUS') not in {str(i) for i in range(1, 9)}:
        raise ValueError('Unknown original school operational status')
    return raw['NCESSCH']


def native_identity(raw, *, income=False, aggregate=False):
    lea, school = (raw.get('LEA Number'), raw.get('School Number')) if income else (raw.get('LEA'), raw.get('School'))
    year = raw.get('Academic Year') if income else raw.get('Year')
    expected_type = str if income or type(year) is str else int
    if (lea != MSDE_LEA or type(lea) is not str or type(year) is not expected_type
            or (year != str(YEAR) if expected_type is str else year != YEAR)):
        raise ValueError('Wrong-year or foreign original MSDE district record')
    if type(school) is not str or not (re.fullmatch(r'\d{4}', school) or aggregate and school == 'A'):
        raise ValueError('Exact native school code or explicit district aggregate required')
    return MSDE_LEA+'-'+school


def offered_evidence(raw):
    flags = {g: raw.get('G_'+g+'_OFFERED') for g in GRADES}
    complete = raw.get('IGOFFERED') == 'As reported' and raw.get('NOGRADES') == 'No' and all(v in {'Yes', 'No'} for v in flags.values())
    offered = [g for g, v in flags.items() if v == 'Yes']
    lower = any(str(g) in offered for g in range(3, 9)); high = any(str(g) in offered for g in range(9, 14))
    band = ('unknown' if not complete else 'other' if any(g in offered for g in ['AE', 'UG']) else
            'mixed' if lower and high else 'grade' if lower else 'high' if high else 'primary')
    return dict(flags=flags, complete_reported_flags=complete, offered=offered, band=band,
                low=raw.get('GSLO'), high=raw.get('GSHI'), level=raw.get('LEVEL'))


def grade_school_contract(profile, ccd, grades):
    offered = offered_evidence(ccd)
    return (profile.get('Grade Span') in {'E', 'M', 'EM'} and ccd.get('UPDATED_STATUS') in OPERATIONAL
            and offered['complete_reported_flags'] and offered['band'] == 'grade'
            and re.fullmatch(r'0[3-8]', ccd.get('GSHI', '')) is not None
            and not any(re.fullmatch(r'Grade (?:9|10|11|12)', r['Grade']) for r in grades)
            and not any(r['Grade'] not in {'All Grades','Prekindergarten Age 4','Kindergarten'} | {f'Grade {g}' for g in range(1,13)} for r in grades)
            and any(r['Grade'] in [f'Grade {g}' for g in range(3,9)] and maryland.count(r['Enrolled Count']) is not None and maryland.count(r['Enrolled Count']) > 0 for r in grades))


def grade_count(raw):
    if (raw.get('GRADE'), raw.get('STUDENT_COUNT'), raw.get('DMS_FLAG'), raw.get('RACE_ETHNICITY'), raw.get('SEX')) == ('Not Specified', '0', 'Derived', 'Not Specified', 'Not Specified'):
        return 0
    return reported_count(raw)


def membership_evidence(total, grades):
    values = [dict(grade=e['raw']['GRADE'], source_row=e['source_row'], reported_count=grade_count(e['raw']), raw=e['raw']) for e in grades]
    full = sum(v['reported_count'] for v in values) if values and all(v['reported_count'] is not None for v in values) else None
    n = None if total is None else reported_count(total['raw'])
    if full is not None and n is not None and full != n:
        raise ValueError('Original CCD grade records do not reconcile to school total')
    return dict(total_source_row=None if total is None else total['source_row'], total_raw=None if total is None else total['raw'],
                reported_total=n, full_grade_sum=full, grade_values=values,
                positive_enrolled_grades=[v['grade'] for v in values if v['reported_count'] is not None and v['reported_count'] > 0],
                missing_or_suppressed_grade_records=[v['grade'] for v in values if v['reported_count'] is None])


def income_evidence(entries):
    if any(type(e.get('source_row')) is not int or e['source_row']<2 or any(type(v) is not str for v in e['raw'].values()) for e in entries):
        raise ValueError('Original Early Attendance entries require strict integer rows and string cells')
    rows = [dict(e['raw'], source_row=e['source_row']) for e in entries]
    for r in rows:
        native_identity(r, income=True, aggregate=True)
    n, low, pct, selected = maryland.income_value(rows)
    reason = ('Missing unique complete native Early Attendance income row' if selected is None else
              'Native individual economic count/percentage is suppressed or unavailable' if pct is None else None)
    return dict(source='msde_income', source_rows=[e['source_row'] for e in entries],
                selected_source_row=None if selected is None else selected['source_row'],
                selected_school_type=None if selected is None else selected['School Type'],
                selected_raw=selected, early_attendance_enrollment=n, individual_low_income_count=low,
                percentage=pct, raw_percentage=None if selected is None else selected['Economically Disadvantaged Pct'],
                raw_count=None if selected is None else selected['Economically Disadvantaged Cnt'],
                raw_denominator=None if selected is None else selected['Total Student Cnt'], exclusion=reason,
                published_rounding_error=None if pct is None else pct-float(selected['Economically Disadvantaged Pct']),
                definition=POLICY['income'])


def outcome_evidence(entry, subject, *, scope, income):
    raw = None if entry is None else dict(entry['raw'], source_row=entry['source_row'])
    if raw is not None:
        if (type(entry.get('source_row')) is not int or entry['source_row']<2 or type(raw.get('Year')) is not int
                or any(type(v) not in {str,type(None)} for k,v in entry['raw'].items() if k!='Year')):
            raise ValueError('Original MCAP entries require strict integer rows/year and string/missing cells')
        native_identity(raw)
        if (raw.get('Student Group') != 'All Students' or entry.get('worksheet') != 'School_Level'
                or entry.get('member') != '2025 MCAP '+('MATH' if subject=='math' else 'ELA')+' Administrative Data Report Card.xlsx'):
            raise ValueError('Outcome is not original All Students')
        derived = maryland.outcome(raw, subject)
        rate = derived['proficiency']
    else:
        rate = None
    outcome_reason = ('Missing native regular All Grades All Students subject row' if raw is None else
                      'Native published proficiency is suppressed or unavailable' if rate is None else None)
    scope_reason = None if scope else 'Native/CCD/September school configuration is high, mixed, primary, unknown or nonoperational'
    reason = scope_reason or income['exclusion'] or outcome_reason
    return dict(source='msde_assessment', source_row=None if entry is None else entry['source_row'],
                worksheet=None if entry is None else entry['worksheet'], applicable=scope and raw is not None, usable=reason is None,
                native_rate=rate, raw_rate=None if raw is None else raw['Proficient Pct'], raw_tested=None if raw is None else raw['Tested Count'],
                raw_proficient_count=None if raw is None else raw['Proficient Count'],
                scope_exclusion=scope_reason, income_exclusion=income['exclusion'], outcome_exclusion=outcome_reason, exclusion=reason,
                tested=None, valid_scores=None, sampling_variance=None, sampling_interval_available=False,
                ten_valid_scored_floor_certified=False)


def summarize(links, predicate, basis):
    rows = [r for r in links if predicate(r)]; subjects = {}
    for subject in ['math', 'reading', 'combined']:
        eligible = [r for r in rows if r['subjects'][subject]['usable']]
        incomes = [r['income']['percentage'] for r in eligible]
        subjects[subject] = dict(applicable=sum(r['subjects'][subject]['applicable'] for r in rows), usable=len(eligible),
            eligible_school_ids=[r['school_id'] for r in eligible], eligible_ncessch=[r['ncessch'] for r in eligible],
            prospective_30_school_floor_met=len(eligible) >= 30,
            exclusions=dict(sorted(Counter(r['subjects'][subject]['exclusion'] for r in rows if not r['subjects'][subject]['usable']).items())),
            verified_valid_score_counts=0, ten_valid_scored_floor_certified=False, model_sampling_intervals_available=False,
            income=dict(minimum=min(incomes) if incomes else None, maximum=max(incomes) if incomes else None,
                distinct=len(set(incomes)), sample_standard_deviation=statistics.stdev(incomes) if len(incomes)>1 else None))
    return dict(profiles=len(rows), school_ids=[r['school_id'] for r in rows], membership_basis=basis, subjects=subjects)


def derive(document, snapshot):
    if fingerprint(POLICY) != POLICY_SHA:
        raise ValueError('Frozen source policy changed')
    if fingerprint(snapshot) != STATE_SNAPSHOT_SHA:
        raise ValueError('Complete pinned Maryland historical comparison changed')
    if (type(document.get('schema_version')) is not int or document.get('schema_version') != 1
            or type(document.get('year')) is not int or document.get('year') != YEAR
            or document.get('academic_year') != ACADEMIC_YEAR or document.get('state') != 'MD'
            or document.get('nces_lea_id') != LEA or document.get('native_lea_id') != NATIVE_LEA or document.get('msde_lea_id') != MSDE_LEA
            or document.get('status') != 'audit_pending' or document.get('scope') != 'source_cohort_audit_only'
            or document.get('approved_for_source') is not False or document.get('approved_for_modeling') is not False
            or fingerprint(document.get('sources')) != fingerprint(SOURCES) or fingerprint(document.get('policy')) != fingerprint(POLICY)
            or fingerprint(document.get('planning')) != fingerprint(PLANNING)
            or document.get('state_extract') != dict(path='data/source/maryland.json', sha256=STATE_EXTRACT_SHA)):
        raise ValueError('Source-only identity, provenance, scope or approval changed')
    inputs = document['raw_inputs']
    if fingerprint(inputs) != RAW_INPUT_SHA:
        raise ValueError('Complete retained original rows, headers, definitions or planning changed')
    schema = {k:{f:v[f] for f in v if f!='records'} for k,v in inputs.items() if k in TABLES}
    if fingerprint(schema) != ORIGINAL_SCHEMA_SHA or fingerprint(inputs.get('definitions')) != DEFINITION_INPUT_SHA:
        raise ValueError('Complete original headers/collection metadata or primary definitions changed')
    if set(inputs) != set(TABLES) | {'definitions','planning'}:
        raise ValueError('Original input tables omitted or added')
    for name in TABLES:
        section = inputs[name]
        if (type(section['header_source_row']) is not int or section['header_source_row'] != 1
                or fingerprint(section['header']) != fingerprint(ORIGINAL_HEADERS[name])
                or fingerprint({k:v for k,v in section.items() if k not in {'records','header'}}) != fingerprint(ORIGINAL_TABLE_METADATA[name])
                or len(section['records']) != ORIGINAL_INVENTORIES[name]):
            raise ValueError('Invalid original header reference')
        seen = set()
        for e in section['records']:
            identity = (e.get('member'), e.get('worksheet'), e['source_row'])
            if type(e['source_row']) is not int or e['source_row'] < 2 or identity in seen or set(e['raw']) != set(section['header']):
                raise ValueError('Invalid original row, duplicate reference or missing field')
            if name in {'directory','membership','lea_directory','lea_membership','native_enrollment','native_income'}:
                if any(type(v) is not str for v in e['raw'].values()):
                    raise ValueError('Original CSV cells must preserve exact string types')
            else:
                for field,value in e['raw'].items():
                    if field=='Year' or name=='native_directory' and field=='NCES Number':
                        if type(value) is not int:
                            raise ValueError('Native Excel year/NCES cells require original integer type')
                    elif value is not None and type(value) is not str:
                        raise ValueError('Native Excel string/missing cells changed type')
            seen.add(identity)
    if identity_fingerprint(inputs) != ORIGINAL_IDENTITY_SHA:
        raise ValueError('Exact original identities, scope labels or source-row references changed')
    ccd = {}
    for e in inputs['directory']['records']:
        key = ccd_identity(e['raw'], directory=True)
        if key in ccd:
            raise ValueError('Duplicate original CCD school identity')
        ccd[key] = e
    directory, crosswalk = {}, {}
    for e in inputs['native_directory']['records']:
        r = e['raw']; key = native_identity(r)
        nces = str(r.get('NCES Number'))
        if r.get('State') != 'MD' or key in directory or nces in crosswalk:
            raise ValueError('Duplicate or foreign native directory identity')
        held = MALFORMED_NATIVE_NCES.get(key)
        if held is not None:
            if type(r.get('NCES Number')) is not int or r['NCES Number'] != held['raw_nces'] or e['source_row'] != held['directory_source_row']:
                raise ValueError('Known malformed original NCES must remain unchanged and unjoined')
        elif not re.fullmatch(LEA+r'\d{5}', nces):
            raise ValueError('Unrecognized malformed or foreign native NCES')
        directory[key] = e; crosswalk[nces] = key
    totals, grade_entries = {}, defaultdict(list)
    for e in inputs['membership']['records']:
        raw = e['raw']; nces = ccd_identity(raw)
        if nces not in ccd or raw['ST_SCHID'] != ccd[nces]['raw']['ST_SCHID']:
            raise ValueError('CCD membership outside exact original school directory')
        indicator = raw['TOTAL_INDICATOR']
        if indicator == 'Education Unit Total':
            if nces in totals or any(raw[k] != 'No Category Codes' for k in ['GRADE', 'RACE_ETHNICITY', 'SEX']):
                raise ValueError('Duplicate or demographic CCD school total')
            totals[nces] = e
        elif indicator == 'Subtotal 4 - By Grade':
            unspecified = grade_count(raw) == 0 and raw['GRADE'] == 'Not Specified'
            if (raw['GRADE'] in {x['raw']['GRADE'] for x in grade_entries[nces]}
                    or not unspecified and any(raw[k] != 'No Category Codes' for k in ['RACE_ETHNICITY', 'SEX'])):
                raise ValueError('Duplicate or demographic CCD grade record')
            grade_entries[nces].append(e)
        else:
            raise ValueError('Unexpected CCD membership population')
    if len(inputs['lea_directory']['records']) != 1:
        raise ValueError('One original exact district directory row required')
    ccd_identity(inputs['lea_directory']['records'][0]['raw'], district=True)
    lea_totals=[]; lea_grades=[]; seen_lea_grades=set()
    for entry in inputs['lea_membership']['records']:
        raw=entry['raw'];ccd_identity(raw,district=True)
        if raw['TOTAL_INDICATOR']=='Education Unit Total':
            if any(raw[k]!='No Category Codes'for k in ['GRADE','RACE_ETHNICITY','SEX']):
                raise ValueError('Unexpected district demographic total')
            lea_totals.append(entry)
        elif raw['TOTAL_INDICATOR']=='Subtotal 4 - By Grade':
            unspecified=grade_count(raw)==0 and raw['GRADE']=='Not Specified'
            if raw['GRADE']in seen_lea_grades or not unspecified and any(raw[k]!='No Category Codes'for k in ['RACE_ETHNICITY','SEX']):
                raise ValueError('Duplicate or demographic district grade membership')
            seen_lea_grades.add(raw['GRADE']);lea_grades.append(entry)
        else:
            raise ValueError('Unexpected district membership population')
    if len(lea_totals)!=1:
        raise ValueError('One original exact district total required')
    lea_total=lea_totals[0];lea_enrolled=membership_evidence(lea_total,lea_grades)
    if reported_count(lea_total['raw']) != PLANNING['enrollment']:
        raise ValueError('Original district total differs from size screen')
    enrollment, income, assessment = defaultdict(list), defaultdict(list), defaultdict(list)
    for name, target, is_income in [('native_enrollment', enrollment, False), ('native_income', income, True), ('native_assessment', assessment, False)]:
        seen = set()
        for e in inputs[name]['records']:
            raw = e['raw']; key = native_identity(raw, income=is_income, aggregate=True)
            if name == 'native_assessment' and raw.get('Student Group') != 'All Students':
                raise ValueError('Original assessment inventory must be All Students')
            if name == 'native_assessment' and (e.get('worksheet') not in {'School_Level','LEA_Level'}
                    or (e['worksheet']=='LEA_Level') != (key=='16-A')
                    or e.get('member') not in {'2025 MCAP MATH Administrative Data Report Card.xlsx','2025 MCAP ELA Administrative Data Report Card.xlsx'}):
                raise ValueError('Native assessment school/district worksheet population changed')
            discriminator = (raw.get('School Type') if is_income else raw.get('Grade') if name == 'native_enrollment' else (e['member'], raw.get('Assessment')))
            if (key, discriminator) in seen:
                raise ValueError('Duplicate native school/band/grade/course record')
            seen.add((key, discriminator)); target[key].append(e)
    state_profiles = {s['id']: s for s in snapshot['schools'] if s['district_id'] == MSDE_LEA}
    links, nonoperational = [], []
    for key, entry in sorted(directory.items()):
        profile = entry['raw']; nces = str(profile['NCES Number']); ccd_entry = ccd.get(nces)
        raw_ccd = None if ccd_entry is None else ccd_entry['raw']; op = raw_ccd is not None and raw_ccd['UPDATED_STATUS'] in OPERATIONAL
        grades = [e['raw'] for e in enrollment[key]]; scoped = raw_ccd is not None and grade_school_contract(profile, raw_ccd, grades)
        eds = income_evidence(income[key]); native_totals = {}
        for e in assessment[key]:
            label = e['raw']['Assessment'].strip()
            subject = 'math' if label == 'Mathematics All Grades' else 'reading' if label == 'English Language Arts All Grades' else None
            if subject:
                if subject in native_totals:
                    raise ValueError('Duplicate native regular All Grades subject')
                native_totals[subject] = e
        subjects = {s: outcome_evidence(native_totals.get(s), s, scope=scoped, income=eds) for s in ['math', 'reading']}
        usable = all(v['usable'] for v in subjects.values())
        subjects['combined'] = dict(applicable=all(v['applicable'] for v in subjects.values()), usable=usable,
            native_rate=(subjects['math']['native_rate']+subjects['reading']['native_rate'])/2 if usable else None,
            exclusion='; '.join(s+': '+v['exclusion'] for s,v in subjects.items() if v['exclusion']) or None,
            tested=None, valid_scores=None, sampling_variance=None, sampling_interval_available=False, ten_valid_scored_floor_certified=False,
            definition=POLICY['combined'])
        member = membership_evidence(totals.get(nces), grade_entries[nces])
        native_fall = [e for e in enrollment[key] if e['raw']['Grade'] == 'All Grades']
        if len(native_fall) > 1:
            raise ValueError('Duplicate native September school total')
        fall = None if not native_fall else maryland.count(native_fall[0]['raw']['Enrolled Count'])
        source_member = scoped
        components=[e for e in assessment[key]if e['member']=='2025 MCAP MATH Administrative Data Report Card.xlsx'and e['raw']['Assessment'].strip()!='Mathematics All Grades']
        component_counts=[maryland.count(e['raw']['Tested Count'])for e in components]
        total_count=None if 'math'not in native_totals else maryland.count(native_totals['math']['raw']['Tested Count'])
        component_sum=sum(component_counts)if components and all(n is not None for n in component_counts)else None
        if component_sum is not None and total_count is not None and component_sum!=total_count:
            raise ValueError('Original numeric administrative math component counts do not reconcile')
        link = dict(school_id=key, ncessch=nces if raw_ccd is not None else None, native_nces_raw=profile['NCES Number'], native_nces_text=nces, identity_hold=('Known malformed original native NCES; no inferred correction' if key in MALFORMED_NATIVE_NCES else 'No exact same-year attached-LEA CCD counterpart' if raw_ccd is None else None), native_school_id=None if raw_ccd is None else raw_ccd['ST_SCHID'], name=profile['School Name'],
            native_directory_source_row=entry['source_row'], directory_source_row=None if ccd_entry is None else ccd_entry['source_row'],
            operational=op, native_grade_span=profile['Grade Span'], native_school_type=profile['School Type'],
            offered=None if raw_ccd is None else offered_evidence(raw_ccd), enrolled=member,
            ccd_flags=None if raw_ccd is None else dict(status=raw_ccd['UPDATED_STATUS'], status_text=raw_ccd['UPDATED_STATUS_TEXT'], school_type=raw_ccd['SCH_TYPE_TEXT'], charter=raw_ccd['CHARTER_TEXT']),
            native_enrollment_rows=[e['source_row'] for e in enrollment[key]], native_all_students_rows=[dict(member=e['member'],source_row=e['source_row']) for e in assessment[key]],
            accelerated_course_rows=[dict(member=e['member'],source_row=e['source_row'],assessment=e['raw']['Assessment'],raw_tested=e['raw']['Tested Count'],raw_rate=e['raw']['Proficient Pct']) for e in assessment[key] if e['raw']['Assessment'].strip() in {'Algebra 1','Geometry','Algebra 2'}],
            administrative_math_component_counts=dict(all_numeric=component_sum is not None and total_count is not None,
                component_sum=component_sum,native_all_grades_raw_count=None if 'math'not in native_totals else native_totals['math']['raw']['Tested Count'],
                equal_when_numeric=component_sum==total_count if component_sum is not None and total_count is not None else None,
                valid_score_certified=False),
            income=eds, subjects=subjects, native_september_enrollment=fall,
            early_attendance_minus_september=None if fall is None or eds['early_attendance_enrollment'] is None else eds['early_attendance_enrollment']-fall,
            early_attendance_minus_ccd=None if member['reported_total'] is None or eds['early_attendance_enrollment'] is None else eds['early_attendance_enrollment']-member['reported_total'],
            historical_state_source_profile=key in state_profiles, source_profile_eligible=source_member)
        if source_member != (key in state_profiles):
            raise ValueError('Independent original scope differs from complete pinned historical state subset')
        if source_member:
            old = state_profiles[key]
            if fingerprint([old['directory_raw'], old['ccd_raw'], old['income'], old['low_income'], old['enrollment'], old['income_raw'], old['grades_raw']]) != fingerprint([dict(profile,source_row=entry['source_row']), raw_ccd, eds['percentage'], eds['individual_low_income_count'], eds['early_attendance_enrollment'], eds['selected_raw'] or {}, [dict(e['raw'],source_row=e['source_row']) for e in enrollment[key]]]):
                raise ValueError('Original identity, income or native grade evidence differs from historical subset')
            if set(old['outcomes']) != set(native_totals):
                raise ValueError('Original outcome subject presence differs from historical subset')
            for subject, native in old['outcomes'].items():
                if fingerprint([native['raw'], native['source_row'], native['proficiency'], native['tested']]) != fingerprint([dict(native_totals[subject]['raw'],source_row=native_totals[subject]['source_row']), native_totals[subject]['source_row'], subjects[subject]['native_rate'], None]):
                    raise ValueError('Original native subject differs from historical state subset')
        links.append(link)
    nonoperational = [e for e in ccd.values() if e['raw']['UPDATED_STATUS'] not in OPERATIONAL]
    potential = {'ES': [], 'HS': []}
    for nces, entry in ccd.items():
        if entry['raw']['UPDATED_STATUS'] in OPERATIONAL:
            level = planning.potential_cohort(entry['raw'], None if nces not in totals else totals[nces]['raw'], {e['raw']['GRADE']:e['raw'] for e in grade_entries[nces]})
            if level:
                potential[level].append(nces)
    potential = {k:sorted(v) for k,v in potential.items()}; recorded=inputs['planning']['record']
    if any(type(recorded.get(k)) is not int or recorded[k] <= 0 for k in ['enrollment','school_directory_operational_count','directory_source_row','membership_source_row']):
        raise ValueError('Planning counts and original row references require strict positive integers')
    if type(recorded.get('potential_cohorts')) is not dict or set(recorded['potential_cohorts']) != {'ES','HS'} or any(type(v) is not int or v<0 for v in recorded['potential_cohorts'].values()):
        raise ValueError('Planning cohort counts require strict nonnegative integers')
    if (recorded['nces_lea_id'] != LEA or recorded['native_lea_id'] != NATIVE_LEA or recorded['state'] != 'MD'
            or recorded['school_directory_operational_count'] != sum(e['raw']['UPDATED_STATUS'] in OPERATIONAL for e in ccd.values())
            or recorded['enrollment'] != reported_count(lea_total['raw']) or recorded['potential_school_ids'] != potential
            or recorded['potential_cohorts'] != {k:len(v) for k,v in potential.items()}
            or recorded['membership_raw'] != lea_total['raw'] or recorded['membership_source_row'] != lea_total['source_row']
            or recorded['directory_source_row'] != inputs['lea_directory']['records'][0]['source_row']
            or any(inputs['lea_directory']['records'][0]['raw'][k] != v for k,v in recorded['directory_raw'].items())):
        raise ValueError('Original district/school rows do not reconstruct planning screen')
    cohorts = {
        'native_grade_school_source_profiles': summarize(links, lambda r:r['source_profile_eligible'], 'Exact native E/M/EM and original CCD/September lower-grade scope; includes masked income/outcome profiles.'),
        'native_high_configurations': summarize(links, lambda r:r['operational'] and r['native_grade_span']=='H', 'Descriptive native high span only; high assessment population remains unreleased.'),
        'native_mixed_configurations': summarize(links, lambda r:r['operational'] and r['native_grade_span'] in {'MH','EMH','EH'}, 'Descriptive native mixed spans; never splice into grade schools.'),
        'native_unknown_configurations': summarize(links, lambda r:r['operational'] and r['native_grade_span'] is None, 'Unknown native span is not inferred from school name.'),
        'native_primary_configurations': summarize(links, lambda r:r['operational'] and r['native_grade_span'] in {'E','M','EM'} and not r['source_profile_eligible'], 'Native lower span without certified tested lower-grade scope remains excluded.'),
    }
    outside = {name:[e for e in inputs[name]['records'] if native_identity(e['raw'],income=name=='native_income',aggregate=True) not in directory] for name in ['native_enrollment','native_income','native_assessment']}
    unmatched = [e for n,e in ccd.items() if n not in crosswalk]
    counts = Counter(e['raw']['Assessment'].strip() for e in inputs['native_assessment']['records'])
    source_rows = {name:len(inputs[name]['records']) for name in inputs if isinstance(inputs[name],dict) and 'records'in inputs[name]}
    school_sum = sum(reported_count(totals[n]['raw']) for n,e in ccd.items() if e['raw']['UPDATED_STATUS'] in OPERATIONAL and n in totals and reported_count(totals[n]['raw']) is not None)
    ea_aggregate = income_evidence(income['16-A']); september_aggregate = [e for e in enrollment['16-A'] if e['raw']['Grade']=='All Grades']
    known_ea=sum(r['income']['early_attendance_enrollment']for r in links if r['income']['early_attendance_enrollment']is not None)
    course_rows=[c for r in links if r['source_profile_eligible']for c in r['accelerated_course_rows']]
    coverage = dict(native_directory=len(directory), ccd_directory=len(ccd), operational_roster=sum(e['raw']['UPDATED_STATUS'] in OPERATIONAL for e in ccd.values()), matched_operational_native_profiles=sum(r['operational'] for r in links), complete_native_profiles=len(links), unmatched_native_profiles=sum(not r['operational'] for r in links), nonoperational_directory=len(nonoperational),
        unmatched_ccd_schools=len(unmatched), outside_native_records={k:len(v) for k,v in outside.items()}, source_rows=source_rows,
        native_grade_spans=dict(sorted(Counter(str(r['native_grade_span']) for r in links).items())),
        offered_bands=dict(sorted(Counter(offered_evidence(e['raw'])['band'] for e in ccd.values() if e['raw']['UPDATED_STATUS'] in OPERATIONAL).items())),
        prospective_source_profiles=cohorts['native_grade_school_source_profiles']['profiles'],
        prospective_usable={s:v['usable'] for s,v in cohorts['native_grade_school_source_profiles']['subjects'].items()},
        prospective_usable_income=sum(r['source_profile_eligible'] and r['income']['exclusion'] is None for r in links),
        native_assessment_inventory=dict(sorted(counts.items())),
        native_assessment_worksheets=dict(sorted(Counter(e['worksheet'] for e in inputs['native_assessment']['records']).items())),
        eligible_accelerated_course_rows=sum(len(r['accelerated_course_rows']) for r in links if r['source_profile_eligible']),
        eligible_course_row_presence=dict(sorted(Counter(c['assessment'].strip()for c in course_rows).items())),
        eligible_course_rows_numeric_administrative_count=dict(sorted(Counter(c['assessment'].strip()for c in course_rows if maryland.count(c['raw_tested'])is not None).items())),
        eligible_administrative_math_component_counts_reconciled=sum(r['source_profile_eligible']and r['administrative_math_component_counts']['equal_when_numeric']is True for r in links),
        school_type_prospective=dict(sorted(Counter(r['ccd_flags']['school_type'] for r in links if r['source_profile_eligible']).items())),
        district_fall_membership=reported_count(lea_total['raw']), operational_school_fall_sum=school_sum,
        district_membership_grade_evidence=lea_enrolled,
        lea_minus_operational_school_fall_enrollment=reported_count(lea_total['raw'])-school_sum,
        district_early_attendance_income=ea_aggregate,
        known_school_early_attendance_enrollment_sum=known_ea,
        district_minus_known_school_early_attendance_enrollment=ea_aggregate['early_attendance_enrollment']-known_ea,
        missing_school_early_attendance_denominator_ids=[r['school_id']for r in links if r['income']['early_attendance_enrollment']is None],
        district_september_enrollment=None if not september_aggregate else maryland.count(september_aggregate[0]['raw']['Enrolled Count']),
        native_september_school_total_sum=sum(r['native_september_enrollment']for r in links if r['native_september_enrollment']is not None),
        missing_native_september_school_total_ids=[r['school_id']for r in links if r['native_september_enrollment']is None],
        suppressed_native_enrollment_cells=sum(maryland.count(e['raw']['Enrolled Count'])is None for e in inputs['native_enrollment']['records']),
        schools_with_early_attendance_ccd_difference=sum(r['early_attendance_minus_ccd'] not in {0,None} for r in links),
        schools_with_early_attendance_september_difference=sum(r['early_attendance_minus_september'] not in {0,None} for r in links),
        verified_valid_score_counts=0, ten_valid_scored_floor_certified=False, model_sampling_intervals_available=False,
        planning_reconstructed_potential_cohorts={k:len(v) for k,v in potential.items()},
        independent_model_diagnostics_required=True, canonical_integration_pending=True,
        source_and_model_approvals=False)
    return dict(roster_links=links, nonoperational_directory=nonoperational, unmatched_ccd_directory=unmatched,
                unmatched_native_directory=[e for e in directory.values() if str(e['raw']['NCES Number']) not in ccd],
                malformed_native_identity_holds=[r for r in links if r['school_id'] in MALFORMED_NATIVE_NCES],
                raw_schema_sha256=ORIGINAL_SCHEMA_SHA, raw_definition_sha256=DEFINITION_INPUT_SHA, source_policy_sha256=POLICY_SHA,
                outside_directory_records=outside, cohorts=cohorts, coverage=coverage,
                source_definition_evidence=inputs['definitions'])


def validate(document, snapshot=None):
    expected = dict(schema_version=1, state='MD', year=YEAR, academic_year=ACADEMIC_YEAR, nces_lea_id=LEA,
        native_lea_id=NATIVE_LEA, msde_lea_id=MSDE_LEA, status='audit_pending', scope='source_cohort_audit_only',
        approved_for_source=False, approved_for_modeling=False, sources=SOURCES, policy=POLICY, planning=PLANNING,
        raw_inputs=document['raw_inputs'], state_extract=dict(path='data/source/maryland.json',sha256=STATE_EXTRACT_SHA))
    expected.update(derive(document, load_maryland() if snapshot is None else snapshot))
    if fingerprint(document) != fingerprint(expected):
        raise ValueError('Derived source/cohort audit changed or extra modeling fields added')
    return expected['coverage']


def read_ccd_rows(source_id, selection):
    path = ROOT/SOURCES[source_id]['path']; member=path.stem+'.csv'
    process = subprocess.Popen(['unzip','-p',str(path),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig')
    try:
        reader=csv.DictReader(process.stdout)
        records=[dict(source_row=n,raw=r) for n,r in enumerate(reader,2) if selection(r)]
        if process.wait()!=0:
            raise ValueError('Original source decompression failed: '+source_id)
        return dict(source_id=source_id,member=member,header_source_row=1,header=reader.fieldnames,records=records)
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate();process.wait()


def read_native_excel(source_id, members, sheets, selection):
    records=[]; header=None
    with zipfile.ZipFile(ROOT/SOURCES[source_id]['path']) as archive:
        for member in members:
            workbook=openpyxl.load_workbook(io.BytesIO(archive.read(member)),read_only=True,data_only=True)
            try:
                for sheet in sheets:
                    rows=workbook[sheet].values; native_header=list(next(rows))
                    if header is not None and native_header != header:
                        raise ValueError('Native subject workbook headers differ')
                    header=native_header
                    for n,values in enumerate(rows,2):
                        if values[0] in ['END OF WORKBOOK','END OF SHEET. Continued on the next sheet.']:
                            break
                        if values[0] is not None and selection(r:=dict(zip(header,values))):
                            records.append(dict(source_row=n,member=member,worksheet=sheet,raw=r))
            finally:
                workbook.close()
    return dict(source_id=source_id,worksheets=sheets,header_source_row=1,header=header,records=records)


def read_native_csv(source_id, member, selection):
    with zipfile.ZipFile(ROOT/SOURCES[source_id]['path']) as archive:
        with archive.open(member) as stream:
            reader=csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig'))
            records=[dict(source_row=n,raw=r) for n,r in enumerate(reader,2) if selection(r)]
            return dict(source_id=source_id,member=member,header_source_row=1,header=reader.fieldnames,records=records)


def extract_raw_inputs():
    for meta in SOURCES.values():
        path=ROOT/meta['path']
        if path.stat().st_size != meta['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:
            raise ValueError('Pinned original source changed: '+meta['path'])
    district=lambda r:r['LEAID']==LEA or r['ST_LEAID']==NATIVE_LEA
    inputs={name:read_ccd_rows(source_id,district) for name,source_id in [('directory','ccd_directory'),('lea_directory','ccd_lea_directory')]}
    inputs['membership']=read_ccd_rows('ccd_membership',lambda r:district(r) and r['TOTAL_INDICATOR']in {'Education Unit Total','Subtotal 4 - By Grade'})
    inputs['lea_membership']=read_ccd_rows('ccd_lea_membership',lambda r:district(r) and r['TOTAL_INDICATOR']in {'Education Unit Total','Subtotal 4 - By Grade'})
    inputs['native_directory']=read_native_excel('msde_directory',['School_Directory_2025.xlsx'],['School Directory'],lambda r:r['LEA']==MSDE_LEA)
    inputs['native_assessment']=read_native_excel('msde_assessment',['2025 MCAP MATH Administrative Data Report Card.xlsx','2025 MCAP ELA Administrative Data Report Card.xlsx'],['School_Level','LEA_Level'],lambda r:r['LEA']==MSDE_LEA and r['Student Group']=='All Students')
    inputs['native_assessment']['selection']='Complete original district regular School_Level and LEA_Level All Students grade/course/All Grades rows; district aggregates and alternate assessments never substitute school regular outcomes.'
    inputs['native_enrollment']=read_native_csv('msde_enrollment','Enrollment_By_Grade_2025.csv',lambda r:r['LEA']==MSDE_LEA)
    inputs['native_income']=read_native_csv('msde_income','2025_Special_Services.csv',lambda r:r['LEA Number']==MSDE_LEA)
    markup=(ROOT/SOURCES['msde_definitions']['path']).read_bytes().decode('utf-8-sig')
    inputs['definitions']=dict(msde_definitions=dict(source_id='msde_definitions',raw_markup=markup,
        plain_text=html.unescape(re.sub(r'<[^>]+>',' ',markup)),
        limitations='Early Attendance as-of date is unnamed; current definition HTML links2026 suppression requirements, which are not applied retroactively to2025. Administrative Tested Count valid-score rules remain uncertified.'))
    inputs['definitions']['msde_mcap_overview']=dict(source_id='msde_mcap_overview',document='MCAP Overview March2025',
        source_pages=[1,2],section_references=['Page1 regular MCAP and separate DLM programs','Page2 Note2 grade6–7 course substitution'],
        paraphrase='MSDE describes regular grade and course assessments separately from alternate DLM. A March17,2025 waiver allows grade6–7 students enrolled in high-school mathematics courses to take those course exams in place of grade-level mathematics. The waiver covers school years2024–25 through2027–28.',
        excerpt='MCAP Participation Requirements',excerpt_word_count=3,
        limitations='The overview establishes assessment population and waiver timing, not administrative Tested Count valid-score rules or a ten-valid-scored floor.')
    from pypdf import PdfReader
    pdf=PdfReader(ROOT/SOURCES['msde_mcap_overview']['path'])
    inputs['definitions']['msde_mcap_overview']['original_pages']=[dict(pdf_page=i+1,text=page.extract_text()) for i,page in enumerate(pdf.pages)]
    lines=(ROOT/SOURCES['msde_reportcard']['path']).read_text().splitlines()
    inputs['definitions']['msde_reportcard']=dict(REPORTCARD_EVIDENCE, original_lines=[dict(source_line=i,html=lines[i-1]) for i in REPORTCARD_EVIDENCE['original_line_references']])
    payload=json.loads((ROOT/PLANNING['source']).read_text()); record=next(r for r in payload['agencies']if r['nces_lea_id']==LEA)
    fields=['nces_lea_id','state','native_lea_id','enrollment','enrollment_flag','school_directory_operational_count','potential_cohorts','potential_school_ids','directory_raw','directory_source_row','membership_raw','membership_source_row']
    inputs['planning']=dict(source=PLANNING['source'],sources=payload['sources'],record={k:record[k]for k in fields})
    return inputs


def extract(output=OUTPUT):
    snapshot=load_maryland();inputs=extract_raw_inputs()
    document=dict(schema_version=1,state='MD',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,
        msde_lea_id=MSDE_LEA,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,
        sources=SOURCES,policy=POLICY,planning=PLANNING,raw_inputs=inputs,state_extract=dict(path='data/source/maryland.json',sha256=STATE_EXTRACT_SHA))
    document.update(derive(document,snapshot));validate(document,snapshot)
    Path(output).write_text(json.dumps(document,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n')
    return document['coverage']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    print(json.dumps(extract(args.output)if args.extract else validate(json.loads(args.output.read_text())),sort_keys=True))

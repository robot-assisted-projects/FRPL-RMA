"""Audit Philadelphia original 2024–25 identities, income and PSSA cohorts; no fits/imports."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

import openpyxl

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/source/philadelphia-district-audit.json'
LEA='4218990'
NATIVE_LEA='PA-126515001'
AUN='126515001'
YEAR=2025
ACADEMIC_YEAR='2024-2025'
OPERATIONAL={'1','3','4','5','8'}
GRADES=['PK','KG']+[str(g) for g in range(1,14)]+['UG','AE']
NATIVE_GRADE_LABELS=['PKA','PKP','PKF','K4A','K4P','K4F','K5A','K5P','K5F']+[str(g) for g in range(1,13)]
SUBJECT_LABELS={'math':'Math','reading':'English Language Arts'}
MASKS={None,'','*','**','***','N/A','NA','Insufficient N','Insufficient Data'}
POLICY={
 'identity':'Exact 2024–25 NCES LEA 4218990 / PA-126515001 / native AUN 126515001 ownership. Official numeric school numbers and digit strings normalize to nine digits under the same AUN; retain original CCD ST_SCHID and 12-digit NCES separately. School-number zero is not a building. No names, NCES suffix guessing, foreign charter LEAs, corrected digits or enrollment joins establish identity.',
 'population':'Prospective pure lower profiles require exact operational CCD ownership, complete unadjusted reported lower offers with grade 3–8 and no grades 9–13/UG/AE, and original October native enrollment with all grades 9–12 explicit zero and positive tested-grade enrollment. Offered and enrolled configurations remain separate; original high/mixed/inactive/primary/unknown records and all subgroup/grade PSSA rows remain source evidence, never pooled by labels or fit diagnostics.',
 'income':'Original October 1, 2024 PIMS individual Economic Disadvantaged Status Code field 88: each school’s own low-income enrollment divided by its own same-year total enrollment, including enrolled pre-K/kindergarten categories. TANF, census poor, Medicaid, neglected/delinquent institutions and foster homes are allowed poverty sources; recent reliable FRPL is a fallback. CEP must use individual poverty sources, not universal meal eligibility. Field 131 food-program eligibility remains separate. Local poverty-source choice and reporting coverage are unknown; this is a broader state proxy, not uniform FRPL or family income.',
 'income_precision':'The published income proportion truncates to four decimals. Preserve it and raw numerator/denominator, but use the precise own count ratio. No other year, LEA allocation, another enrollment, CEP multiplier, threshold-filtered >30% worksheet or universal meals substitutes. Missing or masked income never means zero.',
 'assessment':'Original 2025 regular PSSA All Students / Total school rows for Math and ELA, spanning native tested grades 3–8. Use Percent Proficient and above directly as published, with one-decimal rounding; never add rounded levels, average grade percentages or reconstruct suppression. PSSA excludes separate PASA alternate assessment and Keystone end-of-course scope.',
 'assessment_population':'Original workbook notes exclude pupils enrolled after October 1, homeschoolers, excluded school aggregations, ELL enrolled for less than one year, LIFE pupils entering EL after the previous testing window, and pupils who did not attempt. This is the published accountable scored population, not every spring enrollee.',
 'counts':'Number Scored is the original scored-assessment denominator for the same regular PSSA All Students / Total rate. Published usable totals require at least 11 scored and reconciling native performance percentages. Preserve smaller scored counts with their masked rates and all raw subgroup/grade rows; enrollment, participation and federal 95%-rule counts never substitute. Source-only audit computes no variances, intervals or studentization.',
 'combined':'Equally weighted mean of usable original Math and ELA published total rates, not proficient in both. Preserve each subject’s own verified Number Scored; no invented joint denominator or source-only variance.',
 'suppression':'All original typed masks and explicit zeros remain distinct. Suppressed rates are not reconstructed from scores, neighboring groups or levels. Strict integer counts and row references reject booleans and integral-float aliases.',
 'discrepancies':'Retain native LEA, school and CCD enrollment/income totals as separate observations. Native building 9999 has no school-level income; numerical coincidences or district differences never allocate its income or identify a cause.',
 'approval':'Source/cohort audit only: status audit_pending, scope source_cohort_audit_only, both source/modeling approvals false. No numerical models, canonical imports, normalized/static release or master publication; independent source and later numerical/integration gates remain required.'
}
POLICY_SHA='7b779ea04f44ac12d7819d033c9f80de7d3c537b3e41bf0329010010942214a5'
RUNTIME_CONTRACT_SHA='44cc68e06f18f88c47de3ec385fb9ded3782bf1bab2a8fe655fcb3c51112714f'


SOURCES={'ccd_school_membership': {'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip', 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d', 'bytes': 212696691}, 'ccd_school_directory': {'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip', 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab', 'bytes': 13352819}, 'ccd_lea_directory': {'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip', 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', 'bytes': 2830266}, 'ccd_lea_membership': {'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip', 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', 'bytes': 68497561}, 'pa-assessment-2025': {'path': 'data/raw/pa_assessment_2025.xlsx', 'url': 'https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/data-and-reporting/pssa-and-ayp-results/2025-pssa-school-level-data.xlsx', 'sha256': 'dcc31d40f5c33d0813c7c0b0d394dd325994e75c71d02da1d4ca1e739d01e932', 'bytes': 17988831}, 'pa-income-2025': {'path': 'data/raw/pa_income_2025.xlsx', 'url': 'https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/data-and-reporting/loan-cancellation/public/2425%20public%20schools%20percent%20low%20income.xlsx', 'sha256': 'bb75efef08f121f4a59f86ce55afd1763afbda1907a40e21bd9fd122bc87f741', 'bytes': 386239}, 'pa-grades-2025': {'path': 'data/raw/pa_grades_2025.xlsx', 'url': 'https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/data-and-reporting/enrollment/public-school/enrollment%20public%20schools%202024-25.xlsx', 'sha256': '290213eae0a86d0b339b7b5919e72eb8251724ba4530dcfb28687af71b05cdd7', 'bytes': 2120954}, 'pa-pims-2025': {'path': 'data/raw/pa_pims_2025.pdf', 'url': 'https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/data-and-reporting/pims/pims-manuals/2024-2025%20pims%20manual%20vol%201.pdf', 'sha256': '1de722a967242521f63190786cfba93cc36221451756a472294019602be86ee3', 'bytes': 2241841}}
TABLES=['directory', 'lea_directory', 'membership', 'lea_membership', 'native_grades', 'native_lea_grades', 'native_income', 'native_lea_income', 'native_assessment']
ORIGINAL_METADATA={'directory': {'source_id': 'ccd_school_directory', 'member': 'ccd_sch_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'SCH_TYPE_TEXT', 'SCH_TYPE', 'RECON_STATUS', 'OUT_OF_STATE_FLAG', 'CHARTER_TEXT', 'CHARTAUTH1', 'CHARTAUTHN1', 'CHARTAUTH2', 'CHARTAUTHN2', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED']}, 'lea_directory': {'source_id': 'ccd_lea_directory', 'member': 'ccd_lea_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'LEA_TYPE', 'LEA_TYPE_TEXT', 'OUT_OF_STATE_FLAG', 'CHARTER_LEA', 'CHARTER_LEA_TEXT', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED', 'OPERATIONAL_SCHOOLS']}, 'membership': {'source_id': 'ccd_school_membership', 'member': 'ccd_sch_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG']}, 'lea_membership': {'source_id': 'ccd_lea_membership', 'member': 'ccd_lea_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG']}, 'native_grades': {'source_id': 'pa-grades-2025', 'worksheet': 'LEA and School', 'data_start_row': 6, 'header_rows': [['October 1 Enrollment by LEA and School', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], ['Year: 2024-2025', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], ['AUN', 'LEA Name', 'LEA Type', 'County', 'School Number', 'School Name', 'PKA', 'PKP', 'PKF', 'K4A', 'K4P', 'K4F', 'K5A', 'K5P', 'K5F', '001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', 'Total']]}, 'native_lea_grades': {'source_id': 'pa-grades-2025', 'worksheet': 'LEA', 'data_start_row': 6, 'header_rows': [['October 1 Enrollment by LEA', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], ['Year: 2024-2025', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], ['AUN', 'LEA Name', 'LEA Type', 'County', 'PKA', 'PKP', 'PKF', 'K4A', 'K4P', 'K4F', 'K5A', 'K5P', 'K5F', '001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', 'Total', None]]}, 'native_income': {'source_id': 'pa-income-2025', 'worksheet': '2025 LIP by School', 'data_start_row': 6, 'header_rows': [['Percent Of Enrollments from Low-Income Families', None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None], ['School Level', None, None, None, None, None, None, None, None, None], ['Year: 2024-2025', None, None, None, None, None, None, None, None, None], ['SUBMITTING AUN', 'LEA NAME', 'LEA TYPE', 'SCHOOL NUMBER', 'SCHOOL NAME', 'TOTAL ENROLLMENT', 'LOW-INCOME ENROLLMENT', 'PERCENT OF ENROLLMENT FROM LOW INCOME FAMILIES', None, None]]}, 'native_lea_income': {'source_id': 'pa-income-2025', 'worksheet': '2025 LIP by LEA', 'data_start_row': 7, 'header_rows': [['Percent Of Enrollments from Low-Income Families', None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None], ['LEA Level', None, None, None, None, None, None, None], ['Year: 2024-2025', None, None, None, None, None, None, None], ['SUBMITTING AUN', 'LEA NAME', 'LEA TYPE', 'TOTAL ENROLLMENT', 'LOW INCOME ENROLLMENT', 'PERCENT OF ENROLLMENT FROM LOW INCOME FAMILIES', None, None]]}, 'native_assessment': {'source_id': 'pa-assessment-2025', 'worksheet': 'PSSA', 'data_start_row': 5, 'header_rows': [[None, None, None, '2025 PSSA Grades 3 through 8 - School Proficiency Results', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, 'Proficiency summary data do not include students who:\n - Were enrolled in a school after October 1,\n - Were homeschooled student, \n - Were excluded from school aggregation,\n - Were English Language Learners  (ELL) enrolled in a school for less than one year,\n - Were students with limited or interrupted formal education (LIFE) and enrolled in EL program after the end of the previous testing window, or \n - Did not attempt the assessment. \nProficiency percentages may not add up to 100 due to rounding. Proficiency Information is not displayed for student populations of fewer than 11.', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None], ['Year', 'AUN', 'School Number', 'County', 'District Name', 'School Name', 'Subject', 'Group', 'Grade', 'Number Scored', 'Percent Advanced', 'Percent Proficient', 'Percent Basic', 'Percent Below Basic', 'Percent Proficient and above', None, None, None, None, None, None, None, None, None, None, None, None, None, None]]}}
ORIGINAL_INVENTORIES={'directory': 221, 'lea_directory': 1, 'membership': 2019, 'lea_membership': 16, 'native_grades': 221, 'native_lea_grades': 1, 'native_income': 220, 'native_lea_income': 1, 'native_assessment': 19408}
NATIVE_COLUMN_TYPES={'native_grades': [['int'], ['str'], ['str'], ['str'], ['int'], ['str'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int']], 'native_lea_grades': [['str'], ['str'], ['str'], ['str'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['int'], ['NoneType']], 'native_income': [['str'], ['str'], ['str'], ['str'], ['str'], ['int'], ['int'], ['float', 'int'], ['NoneType'], ['NoneType']], 'native_lea_income': [['str'], ['str'], ['str'], ['int'], ['int'], ['float'], ['NoneType'], ['NoneType']], 'native_assessment': [['int'], ['int'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['int', 'str'], ['int'], ['NoneType', 'float', 'int'], ['NoneType', 'float', 'int'], ['NoneType', 'float', 'int'], ['NoneType', 'float', 'int'], ['NoneType', 'float', 'int'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType'], ['NoneType']]}
RAW_INPUT_SHA='79a71288dadbad8aa8a6bf963a5e6cde0baf913afa5180e7913405ccdfca0af9'
ORIGINAL_SCHEMA_SHA='9c502fcf5f119c5f999810925d9d24ff1b2ec533f8dcdf9e1b1e1d066ce65e61'
DEFINITION_INPUT_SHA='f0305f3ac6ae4165f769b68a232eefdfff3e95636e2e790d860885a4d0ae434a'
STATE_EXTRACT_SHA='73d39c18bfb472ed65fc32ec55b76f65000b66e8cf8b2312708959448b55fe31'
STATE_SNAPSHOT_SHA='cb16432cd346287c9c03c0cf39644bec7e391038629d3d9958c6857547776483'
ORIGINAL_IDENTITY_SHA='82bf875205d35b593807f9bad7f6ce2b9cd6b3695ccefeb2c0f3f123db4b13d5'

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def runtime_contract():
    return dict(lea=LEA,native_lea=NATIVE_LEA,aun=AUN,year=YEAR,academic_year=ACADEMIC_YEAR,
                operational=sorted(OPERATIONAL),grades=GRADES,native_grades=NATIVE_GRADE_LABELS,
                subject_labels=SUBJECT_LABELS,policy=POLICY,sources=SOURCES)


def require_runtime_contract():
    if POLICY_SHA!='7b779ea04f44ac12d7819d033c9f80de7d3c537b3e41bf0329010010942214a5' or fingerprint(POLICY)!='7b779ea04f44ac12d7819d033c9f80de7d3c537b3e41bf0329010010942214a5' or RUNTIME_CONTRACT_SHA!='44cc68e06f18f88c47de3ec385fb9ded3782bf1bab2a8fe655fcb3c51112714f' or fingerprint(runtime_contract())!='44cc68e06f18f88c47de3ec385fb9ded3782bf1bab2a8fe655fcb3c51112714f':
        raise ValueError('Frozen Philadelphia current source policy/identity/year/collection contract changed')


def code(value):
    if type(value) is int and 0<=value<10**9:
        return str(value).zfill(9)
    if type(value) is str and re.fullmatch(r'\d{1,9}',value):
        return value.zfill(9)
    raise ValueError('Official AUN/school code requires strict integer or digit string, never bool/float/name')


def school_id(aun,school):
    if code(aun)!=AUN or code(school)=='000000000':
        raise ValueError('Foreign charter/LEA ownership or non-building zero school code')
    return AUN+'-'+code(school)


def native_identity(raw,table):
    if table=='native_grades':return school_id(raw[0],raw[4])
    if table=='native_income':return school_id(raw[0],raw[3])
    if table=='native_assessment':return school_id(raw[1],raw[2])
    if code(raw[0])!=AUN:raise ValueError('Foreign native LEA row')
    return AUN


def ccd_identity(raw,district=False):
    if (raw.get('SCHOOL_YEAR'),raw.get('ST'),raw.get('FIPST'),raw.get('STATENAME'),raw.get('LEAID'),raw.get('ST_LEAID'))!=(ACADEMIC_YEAR,'PA','42','PENNSYLVANIA',LEA,NATIVE_LEA):
        raise ValueError('Foreign/wrong-year CCD district identity')
    if district:return LEA
    match=re.fullmatch(r'PA-(\d{9})-(\d{1,9})',raw.get('ST_SCHID',''))
    if match is None or not re.fullmatch(LEA+r'\d{5}',raw.get('NCESSCH','')):
        raise ValueError('Malformed exact original CCD school identity')
    return school_id(*match.groups())


def count(value):
    if value in MASKS and type(value) not in {int,float,bool}:return None
    if type(value) is not int or value<0:raise ValueError('Original count requires strict nonnegative integer or mask')
    return value


def percentage(value,maximum=100):
    if value in MASKS and type(value) not in {int,float,bool}:return None
    if type(value) not in {int,float} or not math.isfinite(value) or not 0<=value<=maximum:
        raise ValueError('Original percentage requires finite numeric value, never bool/invalid mask')
    return float(value)


def published_percentage(value):
    result=percentage(value)
    if result is not None and abs(result*10-round(result*10))>1e-7:
        raise ValueError('Original PSSA published percentages require one-decimal precision')
    return result


def offered_evidence(raw):
    flags={g:raw.get('G_'+g+'_OFFERED') for g in GRADES}
    complete=raw.get('IGOFFERED')=='As reported' and raw.get('NOGRADES')=='No' and all(v in {'Yes','No'} for v in flags.values())
    offered=[g for g,v in flags.items() if v=='Yes']; lower=any(g in offered for g in GRADES[:10]); high=any(str(g) in offered for g in range(9,13)); extra=any(g in offered for g in ['13','UG','AE'])
    scope='uncertain' if not complete else 'other' if extra or not(lower or high) else 'mixed' if lower and high else 'ES' if lower else 'HS'
    return dict(flags=flags,complete_reported_flags=complete,scope=scope,offered=offered,
                offered_tested_grades=[str(g) for g in range(3,9) if str(g) in offered],low=raw.get('GSLO'),high=raw.get('GSHI'))


def enrolled_evidence(entry,district=False):
    if entry is None:return None
    raw=entry['raw']; start=4 if district else 6; end=25 if district else 27
    values=[count(v) for v in raw[start:end]]; total=count(raw[end])
    if len(values)!=21 or None in values or total is None or sum(values)!=total:
        raise ValueError('Original October grade counts/own total do not reconcile')
    return dict(source='pa-grades-2025',source_row=entry['source_row'],raw_grade_values=raw[start:end],
        reported_total=total,grade_counts=dict(zip(NATIVE_GRADE_LABELS,values)),
        native_grade_school_contract=all(v==0 for v in values[17:]),
        positive_tested_grades=[str(g) for g,v in zip(range(3,9),values[11:17]) if v>0])


def income_evidence(entry,district=False):
    if entry is None:return dict(source='pa-income-2025',source_row=None,enrollment=None,individual_low_income_count=None,
        percentage=None,published_proportion=None,raw=None,exclusion='Same-year individual PIMS income row missing')
    raw=entry['raw']; start=3 if district else 5
    n,low=count(raw[start]),count(raw[start+1]); display=percentage(raw[start+2],1)
    reason='Individual income count/proportion missing, masked or zero denominator' if None in (n,low,display) or n==0 else None
    if reason is None and (low>n or not -.000001<=low/n-display<=.000101):
        raise ValueError('Published truncated income proportion does not reconcile to own count ratio')
    return dict(source='pa-income-2025',source_row=entry['source_row'],enrollment=n,individual_low_income_count=low,
        percentage=None if reason else 100*low/n,published_proportion=display,raw=raw[start:start+3],
        raw_identity=raw[:start],exclusion=reason,year=YEAR,academic_year=ACADEMIC_YEAR,definition=POLICY['income'])


def outcome_evidence(entry,subject,scope,income):
    raw=None if entry is None else entry['raw']; scored=None if raw is None else count(raw[9]); rate=None if raw is None else published_percentage(raw[14])
    if raw is not None and (type(raw[0]) is not int or raw[0]!=YEAR or raw[6]!=SUBJECT_LABELS[subject] or raw[7:9]!=['All Students','Total']):
        raise ValueError('Scored denominator requires exact regular PSSA same-year All Students/Total subject')
    if raw is not None:native_identity(raw,'native_assessment')
    reason='Original PSSA All Students/Total row missing' if raw is None else 'Original PSSA total proficiency masked (fewer than 11 scored)' if rate is None else None
    if rate is not None:
        levels=[published_percentage(v) for v in raw[10:14]]
        if scored is None or scored<11 or None in levels or abs(sum(levels)-100)>.21 or abs(levels[0]+levels[1]-rate)>.11:
            raise ValueError('Published PSSA total lacks reconciling scored denominator/rounded levels')
    exclusion=scope or income['exclusion'] or reason
    return dict(source='pa-assessment-2025',source_row=None if entry is None else entry['source_row'],
        raw_rate=None if raw is None else raw[14],raw_number_scored=None if raw is None else raw[9],native_rate=rate,
        native_performance_levels=None if raw is None else raw[10:14],reported_scored=scored,
        tested=scored if rate is not None else None,verified_valid_score_scope=raw is not None,
        ten_valid_scored_floor_certified=rate is not None and scored>=11,
        sampling_variance=None,sampling_interval_available=False,applicable=scope is None,usable=exclusion is None,
        scope_exclusion=scope,income_exclusion=income['exclusion'],native_outcome_exclusion=reason,exclusion=exclusion)


def ccd_membership(total,grades):
    values=[]
    for entry in grades:
        r=entry['raw']; value=r['STUDENT_COUNT']
        n=int(value) if re.fullmatch(r'\d+',value) else None
        values.append(dict(source_row=entry['source_row'],grade=r['GRADE'],raw_count=value,reported_count=n,dms_flag=r['DMS_FLAG']))
    reported=None if total is None or not re.fullmatch(r'\d+',total['raw']['STUDENT_COUNT']) else int(total['raw']['STUDENT_COUNT'])
    complete=None if any(v['reported_count'] is None for v in values) else sum(v['reported_count'] for v in values)
    if reported is not None and complete is not None and reported!=complete:raise ValueError('Own original CCD grades do not reconcile to total')
    return dict(total_source_row=None if total is None else total['source_row'],reported_total=reported,
                grade_values=values,full_grade_sum=complete)


def identity_fingerprint(inputs):
    return fingerprint({table:[dict(source_row=e['source_row'],identity=
        {k:e['raw'].get(k) for k in ['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH','GRADE','TOTAL_INDICATOR']}
        if not table.startswith('native_') else [native_identity(e['raw'],table),e['raw'][0] if table=='native_assessment' else None,
            e['raw'][6:9] if table=='native_assessment' else None]) for e in inputs[table]['records']] for table in TABLES})


def load_pennsylvania(path=ROOT/'data/source/pennsylvania.json'):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=STATE_EXTRACT_SHA:raise ValueError('Whole historical Pennsylvania source changed')
    value=json.loads(data)
    if fingerprint(value)!=STATE_SNAPSHOT_SHA or (value['state'],type(value['year']),value['year'],value['school_year'])!=('PA',int,2025,'2024-25'):
        raise ValueError('Historical Pennsylvania source/year payload changed')
    return value


def validate_definition_references(definitions):
    if set(definitions)!={'pa-grades-2025','pa-income-2025','pa-pims-2025'}:
        raise ValueError('Complete primary definition collections required')
    for source,number,width in [('pa-grades-2025',76,11),('pa-income-2025',33,12)]:
        evidence=definitions[source]
        if evidence['source_id']!=source or evidence['worksheet']!='Contact Info & Definitions' or len(evidence['complete_rows'])!=number:
            raise ValueError('Complete original contact/definition worksheet metadata required')
        for expected,entry in enumerate(evidence['complete_rows'],1):
            if type(entry['source_row']) is not int or entry['source_row']!=expected or type(entry['raw']) is not list or len(entry['raw'])!=width:
                raise ValueError('Primary definition worksheet row references require exact integer types')
    manual=definitions['pa-pims-2025']
    if manual['source_id']!='pa-pims-2025' or type(manual['document_pages']) is not int or manual['document_pages']!=224:
        raise ValueError('Original complete PIMS document metadata required')
    pages=manual['original_pages']
    if len(pages)!=4 or any(type(page['page_number']) is not int or page['page_number']!=number or type(page['text']) is not str
        for page,number in zip(pages,[160,161,166,167])):
        raise ValueError('Original PIMS page references require exact integer types')


def summarize(links,selector,note):
    members=[r for r in links if selector(r)]; subjects={}
    for subject in ['math','reading','combined']:
        eligible=[r for r in members if r['subjects'][subject]['usable']]
        subjects[subject]=dict(usable=len(eligible),eligible_school_ids=[r['school_id'] for r in eligible],
            eligible_ncessch=[r['ncessch'] for r in eligible],
            exclusions=dict(sorted(Counter(r['subjects'][subject]['exclusion'] for r in members if not r['subjects'][subject]['usable']).items())),
            charter=dict(Counter(r['ccd_flags']['charter'] for r in eligible)),
            all_eligible_have_verified_scored_denominators=bool(eligible) and all(r['subjects'][subject]['ten_valid_scored_floor_certified'] for r in eligible),
            prospective30school_floor_met=len(eligible)>=30,source_only_variances_and_intervals_uncomputed=True)
    return dict(profiles=len(members),school_ids=[r['school_id'] for r in members],note=note,subjects=subjects)


def derive(document,snapshot):
    require_runtime_contract()
    contract=dict(schema_version=1,state='PA',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_aun=AUN,
        status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,
        sources=SOURCES,policy=POLICY,state_extract=dict(path='data/source/pennsylvania.json',sha256=STATE_EXTRACT_SHA))
    if fingerprint({k:document.get(k) for k in contract})!=fingerprint(contract):raise ValueError('Source-only exact identity/year/provenance/approval contract changed')
    inputs=document['raw_inputs']
    if fingerprint(inputs)!=RAW_INPUT_SHA or set(inputs)!=set(TABLES)|{'definitions','planning'}:raise ValueError('Complete original record/header/definition fingerprint changed')
    metadata={k:{f:v for f,v in inputs[k].items() if f!='records'} for k in TABLES}
    if fingerprint(metadata)!=ORIGINAL_SCHEMA_SHA or fingerprint(inputs['definitions'])!=DEFINITION_INPUT_SHA:
        raise ValueError('Original schema/primary definition evidence changed')
    validate_definition_references(inputs['definitions'])
    for table in TABLES:
        section=inputs[table]
        if fingerprint(metadata[table])!=fingerprint(ORIGINAL_METADATA[table]) or len(section['records'])!=ORIGINAL_INVENTORIES[table]:
            raise ValueError('Original complete table inventory/header metadata changed')
        seen=set()
        for entry in section['records']:
            row=entry['source_row']; r=entry['raw']
            if type(row) is not int or row<(section['data_start_row'] if table.startswith('native_') else 2) or row in seen:
                raise ValueError('Original source row requires strict positive unique integer')
            seen.add(row)
            if table.startswith('native_'):
                if type(r) is not list or len(r)!=len(NATIVE_COLUMN_TYPES[table]) or any(type(v).__name__ not in NATIVE_COLUMN_TYPES[table][i] for i,v in enumerate(r)):
                    raise ValueError('Original native columns/cell types changed')
                native_identity(r,table)
                if table in {'native_grades','native_lea_grades'}:enrolled_evidence(entry,table=='native_lea_grades')
                elif table in {'native_income','native_lea_income'}:income_evidence(entry,table=='native_lea_income')
                elif (type(r[0]) is not int or r[0]!=YEAR or r[6] not in SUBJECT_LABELS.values() or r[8] not in {3,4,5,6,7,8,'Total'} or type(r[7]) is not str):
                    raise ValueError('Wrong regular PSSA year/subject/grade/group source scope')
                else:
                    count(r[9])
                    for value in r[10:15]:published_percentage(value)
            elif type(r) is not dict or set(r)!=set(section['header']) or any(type(v) is not str for v in r.values()):
                raise ValueError('Original CCD cells/headers require exact strings')
    if identity_fingerprint(inputs)!=ORIGINAL_IDENTITY_SHA:raise ValueError('Original exact identity/grade/group/row projection changed')
    directory={}
    for entry in inputs['directory']['records']:
        key=ccd_identity(entry['raw'])
        if key in directory or entry['raw']['UPDATED_STATUS'] not in {str(n) for n in range(1,9)}:raise ValueError('Duplicate/unknown original CCD school identity/status')
        directory[key]=entry
    ccd_identity(inputs['lea_directory']['records'][0]['raw'],True)
    totals={}; bygrade=defaultdict(list); lea_total=[]; lea_grades=[]
    for table in ['membership','lea_membership']:
        for entry in inputs[table]['records']:
            r=entry['raw']; is_lea=table=='lea_membership'; key=ccd_identity(r,is_lea)
            if not is_lea and key not in directory:raise ValueError('School membership outside exact owned roster')
            special=r['GRADE']=='Not Specified' and r['DMS_FLAG']=='Derived' and r['STUDENT_COUNT']=='0'
            if r['TOTAL_INDICATOR']=='Education Unit Total':
                if any(r[k]!='No Category Codes' for k in ['GRADE','RACE_ETHNICITY','SEX']):raise ValueError('Unexpected demographic total')
                if is_lea:lea_total.append(entry)
                elif key in totals:raise ValueError('Duplicate school total')
                else:totals[key]=entry
            elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade':
                target=lea_grades if is_lea else bygrade[key]
                if r['GRADE'] in [e['raw']['GRADE'] for e in target] or not special and any(r[k]!='No Category Codes' for k in ['RACE_ETHNICITY','SEX']):
                    raise ValueError('Duplicate or demographic CCD grade')
                target.append(entry)
            else:raise ValueError('Wrong original CCD membership population')
    if len(lea_total)!=1:raise ValueError('Exactly one original district total required')
    district_ccd=ccd_membership(lea_total[0],lea_grades)
    grades={}; incomes={}; total_outcomes=defaultdict(dict); seen=set()
    for table,target in [('native_grades',grades),('native_income',incomes)]:
        for entry in inputs[table]['records']:
            key=native_identity(entry['raw'],table)
            if key in target or entry['raw'][2]!='SD':raise ValueError('Duplicate or foreign charter/LEA-type native school row')
            target[key]=entry
    for entry in inputs['native_assessment']['records']:
        r=entry['raw']; key=native_identity(r,'native_assessment'); identity=(key,r[6],r[7],r[8])
        if identity in seen:raise ValueError('Duplicate original PSSA school/subject/group/grade record')
        seen.add(identity)
        if r[7]=='All Students' and r[8]=='Total':
            subject=next(s for s,label in SUBJECT_LABELS.items() if label==r[6]); total_outcomes[key][subject]=entry
    state_profiles=[p for p in snapshot['schools'] if p['district_id']==AUN]
    expected_profiles=[]
    for key,entry in grades.items():
        r=entry['raw']; inc=incomes.get(key)
        profile=dict(school_id=key,district_id=AUN,name=r[5],district=r[1],lea_type=r[2],county=r[3],identity_raw=r[:6],
            grades=r[6:27],grade_school=enrolled_evidence(entry)['native_grade_school_contract'],grade_source_row=entry['source_row'],
            income_raw=None if inc is None else inc['raw'][5:8],income_source_row=0 if inc is None else inc['source_row'])
        if inc is not None:profile['income_identity_raw']=inc['raw'][:5]
        expected_profiles.append(profile)
    expected_assessments=[dict(school_id=native_identity(e['raw'],'native_assessment'),subject=next(s for s,label in SUBJECT_LABELS.items() if label==e['raw'][6]),source_row=e['source_row'],identity_raw=e['raw'][:9],raw=e['raw'][9:15])
        for e in inputs['native_assessment']['records'] if e['raw'][7:9]==['All Students','Total']]
    if fingerprint(state_profiles)!=fingerprint(expected_profiles) or fingerprint([r for r in snapshot['assessments'] if r['school_id'].startswith(AUN+'-')])!=fingerprint(expected_assessments):
        raise ValueError('Complete originals differ from frozen Pennsylvania secondary extract')
    links=[]
    for key,entry in directory.items():
        r=entry['raw']; offer=offered_evidence(r); op=r['UPDATED_STATUS'] in OPERATIONAL; grade=grades.get(key); enrolled=enrolled_evidence(grade); income=income_evidence(incomes.get(key))
        if grade is not None and income['enrollment'] is not None and income['enrollment']!=enrolled['reported_total']:
            raise ValueError('School individual income and October grade denominator disagree')
        exclusion=('Nonoperational original CCD status' if not op else 'No exact same-year native October grade row' if enrolled is None else
            'Offered configuration is not complete pure lower grades' if offer['scope']!='ES' else
            'No offered PSSA tested grade in primary-only configuration' if not offer['offered_tested_grades'] else
            'Native October grades 9–12 are enrolled' if not enrolled['native_grade_school_contract'] else
            'No positive October PSSA tested-grade enrollment' if not enrolled['positive_tested_grades'] else None)
        subjects={s:outcome_evidence(total_outcomes.get(key,{}).get(s),s,exclusion,income) for s in ['math','reading']}
        paired=all(v['usable'] for v in subjects.values()); subjects['combined']=dict(applicable=exclusion is None,usable=paired,
            native_rate=(subjects['math']['native_rate']+subjects['reading']['native_rate'])/2 if all(v['native_rate'] is not None for v in subjects.values()) else None,
            verified_valid_scores_by_subject={s:v['tested'] for s,v in subjects.items()},tested=None,sampling_variance=None,sampling_interval_available=False,
            ten_valid_scored_floor_certified=all(v['ten_valid_scored_floor_certified'] for v in subjects.values()),
            exclusion='; '.join(s+': '+v['exclusion'] for s,v in subjects.items() if v['exclusion']) or None,definition=POLICY['combined'])
        links.append(dict(school_id=key,ncessch=r['NCESSCH'],native_school_id=r['ST_SCHID'],name=r['SCH_NAME'],
            directory_source_row=entry['source_row'],operational=op,ccd_flags=dict(status=r['UPDATED_STATUS'],status_text=r['UPDATED_STATUS_TEXT'],charter=r['CHARTER_TEXT'],school_type=r['SCH_TYPE_TEXT']),
            offered=offer,native_profile_matched=grade is not None,native_grade_source_row=None if grade is None else grade['source_row'],
            enrolled=enrolled,ccd_membership=ccd_membership(totals.get(key),bygrade[key]),income=income,
            source_profile_eligible=exclusion is None,population_exclusion=exclusion,subjects=subjects))
    cohorts={'prospective_tested_grade_profiles':summarize(links,lambda r:r['source_profile_eligible'],'Exact operational pure lower offered and October enrolled grade population.'),
        'high_only':summarize(links,lambda r:r['operational'] and r['offered']['scope']=='HS','High configurations remain outside this source proposal.'),
        'mixed_grade':summarize(links,lambda r:r['operational'] and r['offered']['scope']=='mixed','Mixed configurations remain outside this source proposal.'),
        'primary_only':summarize(links,lambda r:r['operational'] and r['offered']['scope']=='ES' and not r['offered']['offered_tested_grades'],'Primary-only configurations remain outside.'),
        'other_uncertain':summarize(links,lambda r:r['operational'] and r['offered']['scope'] in {'uncertain','other'},'Incomplete or other configurations remain outside.')}
    prospective=[r for r in links if r['source_profile_eligible']]
    district_grades=enrolled_evidence(inputs['native_lea_grades']['records'][0],True); district_income=income_evidence(inputs['native_lea_income']['records'][0],True)
    if district_income['enrollment']!=district_grades['reported_total']:raise ValueError('Native district October income/grade total differs')
    record=inputs['planning']['record']
    if any(type(record.get(k)) is not int or record[k]<=0 for k in ['enrollment','school_directory_operational_count','directory_source_row','membership_source_row']) or any(type(v) is not int or v<0 for v in record['potential_cohorts'].values()):
        raise ValueError('Planning row/count references require strict integer types')
    if record['nces_lea_id']!=LEA or record['native_lea_id']!=NATIVE_LEA or record['state']!='PA' or record['enrollment']!=district_ccd['reported_total'] or record['directory_source_row']!=inputs['lea_directory']['records'][0]['source_row'] or record['membership_source_row']!=lea_total[0]['source_row'] or record['membership_raw']!=lea_total[0]['raw']:
        raise ValueError('Original district planning ownership/row references changed')
    coverage=dict(source_rows={k:len(inputs[k]['records']) for k in TABLES},original_records=sum(len(inputs[k]['records']) for k in TABLES),
        original_typed_cells=sum(sum(len(e['raw']) for e in inputs[k]['records']) for k in TABLES),ccd_directory=len(links),
        operational_roster=sum(r['operational'] for r in links),status=dict(Counter(r['ccd_flags']['status_text'] for r in links)),
        operational_offered_scope=dict(Counter(r['offered']['scope'] for r in links if r['operational'])),
        native_grade_profiles=len(grades),native_income_rows=len(incomes),native_total_rows=len(expected_assessments),
        prospective_source_profiles=len(prospective),prospective_usable={s:cohorts['prospective_tested_grade_profiles']['subjects'][s]['usable'] for s in ['math','reading','combined']},
        prospective_income_available=sum(r['income']['percentage'] is not None for r in prospective),
        native_school_income_missing_ids=sorted(set(grades)-set(incomes)),native_grades_without_exact_ccd_ids=sorted(set(grades)-set(directory)),
        native_total_outside_pure_scope_ids=sorted(set(total_outcomes)-{r['school_id'] for r in prospective}),
        district_ccd_enrollment=district_ccd['reported_total'],operational_ccd_enrollment_sum=sum(r['ccd_membership']['reported_total'] or 0 for r in links if r['operational']),
        district_october_enrollment=district_grades['reported_total'],native_school_enrollment_sum=sum(enrolled_evidence(e)['reported_total'] for e in grades.values()),
        district_individual_income_count=district_income['individual_low_income_count'],known_school_income_enrollment_sum=sum(income_evidence(e)['enrollment'] or 0 for e in incomes.values()),
        known_school_individual_income_count_sum=sum(income_evidence(e)['individual_low_income_count'] or 0 for e in incomes.values()),
        usable_regular_pssa_denominator_counts=sum(r['subjects'][s]['usable'] and r['subjects'][s]['tested'] is not None for r in links for s in ['math','reading']),
        eligible_subject_sources_all_have_verified_valid_scores=all(r['subjects'][s]['ten_valid_scored_floor_certified'] for r in prospective for s in ['math','reading']),
        variances_and_intervals_computed=False,independent_numerical_diagnostics_required=True,canonical_integration_pending=True,
        source_and_model_approvals=False)
    outside=[dict(school_id=key,ncessch=None,native_school_id=None,name=entry['raw'][5],
        grade_source_row=entry['source_row'],enrolled=enrolled_evidence(entry),income=income_evidence(incomes.get(key)),
        exclusion='Native building lacks exact same-year CCD school identity; no name or inactive-school substitution')
        for key,entry in grades.items() if key not in directory]
    return dict(roster_links=links,cohorts=cohorts,coverage=coverage,outside_roster_profiles=outside,
        nonoperational_directory=[e for e in inputs['directory']['records'] if e['raw']['UPDATED_STATUS'] not in OPERATIONAL],
        native_profiles_without_ccd=[e for k,e in grades.items() if k not in directory],
        native_income_without_profile=[e for k,e in incomes.items() if k not in grades],
        raw_schema_sha256=ORIGINAL_SCHEMA_SHA,raw_definition_sha256=DEFINITION_INPUT_SHA,
        original_identity_projection_sha256=ORIGINAL_IDENTITY_SHA,source_policy_sha256=POLICY_SHA,
        source_definition_evidence=dict(raw_inputs_reference='definitions',fingerprint=DEFINITION_INPUT_SHA,
            pims_pages=[160,161,166,167],pssa_headers_notes_reference='native_assessment.header_rows',regular_pssa_count_field='Number Scored',suppression_minimum_scored=11),
        district_original_evidence=dict(ccd_membership=district_ccd,october_grade_membership=district_grades,october_individual_income=district_income))


def validate(document,snapshot=None):
    current=load_pennsylvania()
    if snapshot is not None and fingerprint(snapshot)!=fingerprint(current):raise ValueError('Cached historical Pennsylvania source differs')
    expected=dict(schema_version=1,state='PA',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_aun=AUN,
        status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,
        sources=SOURCES,policy=POLICY,raw_inputs=document['raw_inputs'],state_extract=dict(path='data/source/pennsylvania.json',sha256=STATE_EXTRACT_SHA))
    expected.update(derive(document,current))
    if fingerprint(document)!=fingerprint(expected):raise ValueError('Complete source/raw/cohort/definition/count/identity replay differs')
    return expected['coverage']


def read_ccd_rows(source,selection):
    path=ROOT/SOURCES[source]['path'];member=path.stem+'.csv'
    process=subprocess.Popen(['unzip','-p',str(path),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig')
    try:
        reader=csv.DictReader(process.stdout); records=[dict(source_row=i,raw=r) for i,r in enumerate(reader,2) if selection(r)]
        if process.wait()!=0:raise ValueError('Original CCD decompression failed')
        return dict(source_id=source,member=member,header_source_row=1,header=reader.fieldnames,records=records)
    finally:
        process.stdout.close()
        if process.poll() is None:process.terminate();process.wait()


def extract_raw_inputs():
    for source in SOURCES.values():
        path=ROOT/source['path']
        if path.stat().st_size!=source['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Original source byte pin changed')
    same=lambda r:r['LEAID']==LEA or r['ST_LEAID']==NATIVE_LEA
    inputs={k:read_ccd_rows(s,same) for k,s in [('directory','ccd_school_directory'),('lea_directory','ccd_lea_directory')]}
    for k,s in [('membership','ccd_school_membership'),('lea_membership','ccd_lea_membership')]:
        inputs[k]=read_ccd_rows(s,lambda r:same(r) and r['TOTAL_INDICATOR'] in {'Education Unit Total','Subtotal 4 - By Grade'})
    definitions={}
    for source,specs in [('pa-grades-2025',[('native_grades','LEA and School',5,0),('native_lea_grades','LEA',5,0)]),
        ('pa-income-2025',[('native_income','2025 LIP by School',5,0),('native_lea_income','2025 LIP by LEA',6,0)]),
        ('pa-assessment-2025',[('native_assessment','PSSA',4,1)])]:
        book=openpyxl.load_workbook(ROOT/SOURCES[source]['path'],read_only=True,data_only=True)
        try:
            for table,sheet,headers,index in specs:
                values=list(book[sheet].values)
                inputs[table]=dict(source_id=source,worksheet=sheet,data_start_row=headers+1,header_rows=[list(r) for r in values[:headers]],
                    records=[dict(source_row=i,raw=list(r)) for i,r in enumerate(values,1) if i>headers and type(r[index]) in {str,int} and str(r[index])==AUN])
            if 'Contact Info & Definitions' in book.sheetnames:
                definitions[source]=dict(source_id=source,worksheet='Contact Info & Definitions',complete_rows=[dict(source_row=i,raw=list(r)) for i,r in enumerate(book['Contact Info & Definitions'].values,1)])
        finally:book.close()
    from pypdf import PdfReader
    pages=PdfReader(ROOT/SOURCES['pa-pims-2025']['path']).pages
    definitions['pa-pims-2025']=dict(source_id='pa-pims-2025',document_pages=len(pages),original_pages=[dict(page_number=i,text=pages[i-1].extract_text() or '') for i in [160,161,166,167]])
    inputs['definitions']=definitions
    planning=json.loads((ROOT/'data/source/district-comparison-candidates.json').read_text());record=next(r for r in planning['agencies'] if r['nces_lea_id']==LEA)
    fields=['nces_lea_id','state','native_lea_id','enrollment','enrollment_flag','school_directory_operational_count','potential_cohorts','potential_school_ids','directory_raw','directory_source_row','membership_raw','membership_source_row']
    inputs['planning']=dict(source='data/source/district-comparison-candidates.json',sources=planning['sources'],record={k:record[k] for k in fields})
    return inputs


def build(inputs,snapshot=None):
    snapshot=load_pennsylvania() if snapshot is None else snapshot
    document=dict(schema_version=1,state='PA',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_aun=AUN,
        status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,
        sources=SOURCES,policy=POLICY,raw_inputs=inputs,state_extract=dict(path='data/source/pennsylvania.json',sha256=STATE_EXTRACT_SHA))
    document.update(derive(document,snapshot));validate(document,snapshot)
    return document


def extract(output=OUTPUT):
    document=build(extract_raw_inputs())
    Path(output).write_text(json.dumps(document,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n')
    return document['coverage']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args()
    print(json.dumps(extract(args.output) if args.extract else validate(json.loads(args.output.read_text())),sort_keys=True))

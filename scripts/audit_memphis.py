"""Audit exact Memphis–Shelby 2024–25 originals without fitting or publishing.

--extract freshly opens all pinned archives, CSVs, codebooks and definitions.
Default replay validates retained originals and the current complete secondary
state extract. Shared-time attribution holds remain explicit; no old fit is used.
"""
import argparse
from collections import Counter,defaultdict
import csv,datetime,hashlib,json,re,subprocess,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/source/memphis-district-audit.json'
LEA='4700148';NATIVE_LEA='TN-00792';NATIVE_DISTRICT='792';YEAR=2025;ACADEMIC_YEAR='2024-2025'
TABLES=['directory','lea_directory','membership','lea_membership','lunch','assessment']
OPERATIONAL={'1','3','4','5','8'}
OFFER_GRADES=['PK','KG']+[str(i)for i in range(1,14)]+['UG','AE']
LOWER_GRADES=['Pre-Kindergarten','Kindergarten']+[f'Grade {i}'for i in range(1,9)]
SUBJECTS={'math':'math','reading':'ela'}
ASSESSMENT_SELECTOR={'DataLevel':'School','SchYear':'2024-25','StateAbbrev':'TN','StateFips':'47','AssmtName':'TNReady','AssmtType':'Regular','GradeLevel':'G38','StudentGroup':'All Students','StudentSubGroup':'All Students','ProficiencyCriteria':'Levels 3-4','Version':'V3.1'}
PLANNING_FIELDS=['nces_lea_id','state','native_lea_id','enrollment','enrollment_flag','school_directory_operational_count','potential_cohorts','potential_school_ids','directory_raw','directory_source_row','membership_raw','membership_source_row']
POLICY={'identity': 'Exact original 2024–25 NCES LEA 4700148 / CCD native TN-00792 and EDC district 792 ownership. Match authoritative twelve-digit NCES school IDs and cross-check the documented CCD TN-00792-#### and original EDC 792-#### fields. Names, county labels, corrected digits and other charter LEAs never establish ownership.', 'raw_inventory': 'Retain complete needed original target-LEA school/district total and grade membership rows, all Final 2a lunch categories and native All Students G38 Math/ELA school/district/type/outside-ID rows, with every original field and mask. Complete original file checksums, full-target inventory counts and exact omitted-population row ordinals/identity lists preserve unused-population provenance. Selection never uses metric values, model fit, charter or attribution status. Retain full schemas, primary codebooks/notes/technical pages and the secondary original-field cross-check; never reuse old fits.', 'population': 'Pure lower grade-configuration source profiles require an operational exact CCD identity, complete unadjusted reported offered flags with a grade 3–8 offer, no offered 9–13/UG/AE, reported positive own membership with reconciled lower-grade subtotals, positive reported enrolled grade 3–8 and only explicit zero outside PK–8. High, mixed, primary, unknown, adjusted, zero/missing or unjoined configurations remain outside; charter labels and diagnostics never select membership.', 'income': 'Own reported CCD Final 2a Direct Certification Education Unit Total divided by own reported positive same-year Membership Education Unit Total. Preserve benefits/status-based individual certification, including pre-K where enrolled; this is not full household-income FRPL, state economic disadvantage or universal/CEP meal receipt. Both counts require DMS_FLAG=Reported; no negative/masked/derived count, claiming multiplier, FRPL fallback, tested-subgroup denominator or other-year income is substituted. Medicaid and certification/reporting coverage vary; undercount is unknown.', 'assessment': 'Original EDC v3.1 SEA-sourced TNReady regular school All Students native G38 aggregate grades 3–8, Levels 3–4. Use only exact original ProficientOrAbove_percent in 0–1; ranges, suppression and missingness remain unavailable, never midpoint or zero. EDC may sum performance-level percentages within the same native total; do not average grades, reconstruct more precise count ratios or pool subgroup/district rows.', 'counts': 'EDC tested and proficiency/level counts remain unverified raw evidence and may be constructed from other data. All valid-score counts, variances and interval endpoints stay null; ten-valid-scored floor uncertified. CCD membership/direct certification, participation and federal 95% measures never substitute for valid-score denominators. Existing count holds are retained without repeated failed investigations.', 'shared_time': 'Original Final 2a Tennessee CCD-0054 note says some or all students receive services at a school while enrolled in a separate school of record. Preserve all named NCES records and exact note pointers. Four named pure-lower profiles retain raw DC/member ratios and G38 rates but have explicit unresolved enrolled-versus-served attribution holds, separate from unheld usable inputs. A plausible ratio or DC<=membership does not clear this hold. This is a source-attribution exclusion, never a diagnostic or influence exclusion. The note identifies named schools; it does not establish a whole-LEA warning or certify attribution coverage at nonlisted campuses.', 'suppression': 'Keep explicit zero, suppressed/ranged, nonreported/derived and missing rows separate. No complementing ranges or backfilling another year. Native-only NCES IDs have no inferred directory, income or corrected identity.', 'combined': 'Equal mean of exact usable original Math and ELA native rates with own same-year direct-certification ratio, not proficiency in both. A future Combined model must use its own fit and studentization; no model is created by this source audit.', 'limitations': 'Retain original charter, alternative, school-type, virtual, grade disagreement and shared-time evidence without program, admissions, provider, geometry, causal-effect or quality inference. School/district enrollment differences do not establish a cause or supply score denominators. Single 2024–25 snapshot and original EDC source-business-rule limits remain.', 'approval': 'Source/cohort audit only: audit_pending/source_cohort_audit_only and both approval flags false. No numerical fits, normalized adapter, canonical imports, static/shared catalog changes or publication. Separate numerical/integration/release gates remain.'}
# GENERATED_IMMUTABLE_CONSTANTS
SOURCES={'ccd_directory_2025': {'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip', 'bytes': 13352819, 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab'}, 'ccd_membership_2025': {'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip', 'bytes': 212696691, 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d'}, 'ccd_lunch_2025': {'path': 'data/raw/ccd_sch_033_2425_l_2a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_033_2425_l_2a_073025.zip', 'bytes': 14029439, 'sha256': '97bda749e778ee74cb731d181bbcdaf0f9c6cd6edf94cb31518a5bbeab411dd6'}, 'ccd_state_notes_2025': {'path': 'data/raw/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'bytes': 210984, 'sha256': '6476b6b28b700389e261b87377d9cd249935503d53b5919fe1b7ef8b1052d1a7'}, 'edc_codebook_v3_1': {'path': 'data/raw/EDC_codebook_v3.1.xlsx', 'url': 'https://www.eddatacenter.org/data_codebooks/EDC_codebook_v3.1.xlsx', 'bytes': 20401, 'sha256': 'cfaf3eeb482b416106e4a7b775c9554768fbf4900b0518c861979d646b6b2574'}, 'edc_technical_v3_1': {'path': 'data/raw/EDC_technical_documentation_v3.1.pdf', 'url': 'https://www.eddatacenter.org/data_documentation/EDC_technical_documentation_v3.1.pdf', 'bytes': 1100602, 'sha256': '749c52497e37cfd73c0e29afadea3d90d6b50950844f070247594f44254a7968'}, 'nces_lunch_definitions': {'path': 'data/raw/ccd-lunch-definition.html', 'url': 'https://nces.ed.gov/learn/blog/understanding-school-lunch-eligibility-common-core-data', 'bytes': 34948, 'sha256': '03f24547726ebf7529d946cee85f84e3de3ac3962b5dbc8b96e0a4db3744247d'}, 'edc_2025': {'path': 'data/raw/edc-2025/tn.csv', 'url': 'https://www.eddatacenter.org/api/data/3.1?state=TN&year=2025', 'bytes': 77986487, 'sha256': 'a8d7a7d793f36ae42c79d70ee62e7dd5e9e8f8a6c591e3aa39a6c6ecb3c8b786'}, 'ccd_lea_directory': {'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip', 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', 'bytes': 2830266}, 'ccd_lea_membership': {'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip', 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', 'bytes': 68497561}, 'ccd_lunch_layout': {'path': 'data/raw/SY_2024-25_SCH_Lunch_Companion_2026-005d_2a.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Lunch_Companion_2026-005d_2a.xlsx', 'sha256': '6596d9e9a3c471ddd83b63d19a46514193220b7f3d66b91ddb0ad5e42d252008', 'bytes': 41935}, 'ccd_membership_layout': {'path': 'data/raw/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'sha256': 'cc3afc95a5226da12aec2f77b264477adfe9d85bb250e71c4dab534b5a591fd1', 'bytes': 40687}, 'ccd_directory_layout': {'path': 'data/raw/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'sha256': 'aa3be279c7a175be76ce43e451fb8ba513481e7a80f009abf7de3ad4cf33f8cf', 'bytes': 54414}}
ORIGINAL_METADATA={'directory': {'source_id': 'ccd_directory_2025', 'member': 'ccd_sch_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'SCH_TYPE_TEXT', 'SCH_TYPE', 'RECON_STATUS', 'OUT_OF_STATE_FLAG', 'CHARTER_TEXT', 'CHARTAUTH1', 'CHARTAUTHN1', 'CHARTAUTH2', 'CHARTAUTHN2', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED'], 'selection': 'All original rows for exact NCES LEA4700148 or nativeTN-00792; all categories, masks and unused fields retained.'}, 'lea_directory': {'source_id': 'ccd_lea_directory', 'member': 'ccd_lea_029_2425_w_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'LEA_TYPE', 'LEA_TYPE_TEXT', 'OUT_OF_STATE_FLAG', 'CHARTER_LEA', 'CHARTER_LEA_TEXT', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED', 'OPERATIONAL_SCHOOLS'], 'selection': 'All original rows for exact NCES LEA4700148 or nativeTN-00792; all categories, masks and unused fields retained.'}, 'membership': {'source_id': 'ccd_membership_2025', 'member': 'ccd_sch_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'Complete original target LEA total/grade membership rows, with all original fields and explicit NotSpecified grade records.'}, 'lea_membership': {'source_id': 'ccd_lea_membership', 'member': 'ccd_lea_052_2425_l_1a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'Complete original target LEA total/grade membership rows, with all original fields and explicit NotSpecified grade records.'}, 'lunch': {'source_id': 'ccd_lunch_2025', 'member': 'ccd_sch_033_2425_l_2a_073025.csv', 'header_source_row': 1, 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'DATA_GROUP', 'LUNCH_PROGRAM', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'selection': 'All original rows for exact NCES LEA4700148 or nativeTN-00792; all categories, masks and unused fields retained.'}, 'assessment': {'source_id': 'edc_2025', 'member': 'tn.csv', 'header_source_row': 1, 'header': ['State', 'StateAbbrev', 'StateFips', 'SchYear', 'DataLevel', 'DistName', 'SchName', 'NCESDistrictID', 'StateAssignedDistID', 'NCESSchoolID', 'StateAssignedSchID', 'AssmtName', 'AssmtType', 'Subject', 'GradeLevel', 'StudentGroup', 'StudentGroup_TotalTested', 'StudentSubGroup', 'StudentSubGroup_TotalTested', 'Lev1_count', 'Lev1_percent', 'Lev2_count', 'Lev2_percent', 'Lev3_count', 'Lev3_percent', 'Lev4_count', 'Lev4_percent', 'Lev5_count', 'Lev5_percent', 'AvgScaleScore', 'AvgSS_SD', 'ProficiencyCriteria', 'ProficientOrAbove_count', 'ProficientOrAbove_percent', 'ParticipationRate', 'Flag_AssmtNameChange', 'Flag_CutScoreChange_ELA', 'Flag_CutScoreChange_math', 'Flag_CutScoreChange_sci', 'Flag_CutScoreChange_soc', 'DistType', 'DistCharter', 'DistLocale', 'SchType', 'SchLevel', 'SchVirtual', 'CountyName', 'CountyCode', 'Version'], 'selection': 'Complete original AllStudents G38 Math/ELA rows across school/district/assessment types and outside IDs, with all original fields and masks.'}}
ORIGINAL_INVENTORIES={'directory': 223, 'lea_directory': 1, 'membership': 1756, 'lea_membership': 16, 'lunch': 1040, 'assessment': 332}
RAW_INPUT_SHA='1539b708cd071dde01f03e917c302c3c7d7ead5051ac34216ff82ca3c3e0c5a0'
ORIGINAL_SCHEMA_SHA='26e1a67b7f6fd2f9544f997006a3ec62ced2fbe685524295d85161175d983f48'
DEFINITION_INPUT_SHA='0a3b0b7c7318ff0753626aa50d2971b8bdbfdff66395feeace75c53f731ed1b8'
ORIGINAL_IDENTITY_SHA='b535c7002daa9c9da54411aa7d4fa70f560edd060369a3c5e5260d378162cbd9'
STATE_EXTRACT_SHA='3b6e55bba0055c582eb14a461697c64131a36e4cd555bca94965e5f77cac91fc'
TN_SNAPSHOT_SHA='eb409c8b90792f5b4a6778e5a22aaafd2b6714e0a65dd939a7c16cd42a45193e'
SHARED_TIME_IDS=['470014801113', '470014801166', '470014801186', '470014801583', '470014801595', '470014801960', '470014802081', '470014802188', '470014802217', '470014802271', '470014802430', '470014802443', '470014810440']
SHARED_TIME_SOURCE_ROW=463
POLICY_SHA='1d422d6c56ddda504d34cb739d2a50de1b546f60d1306ee5a3453d14068aaa17'
RUNTIME_CONTRACT_SHA='a6006b7299894a4ca5924ab896904f03c5cb602d17cc59ce19e889837555ca9b'
LITERAL_POLICY_SHA='1d422d6c56ddda504d34cb739d2a50de1b546f60d1306ee5a3453d14068aaa17'
LITERAL_RUNTIME_SHA='a6006b7299894a4ca5924ab896904f03c5cb602d17cc59ce19e889837555ca9b'

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def identity_fingerprint(inputs):
    ccd=['SCHOOL_YEAR','ST','FIPST','LEAID','ST_LEAID','NCESSCH','ST_SCHID','GRADE','TOTAL_INDICATOR','DATA_GROUP','LUNCH_PROGRAM']
    edc=['StateAbbrev','StateFips','SchYear','DataLevel','NCESDistrictID','StateAssignedDistID','NCESSchoolID','StateAssignedSchID','AssmtName','AssmtType','Subject','GradeLevel','StudentGroup','StudentSubGroup','Version']
    return fingerprint({t:[dict(source_row=e['source_row'],identity={k:e['raw'].get(k)for k in(edc if t=='assessment'else ccd)})for e in inputs[t]['records']]for t in TABLES})

def runtime_contract():
    return dict(lea=LEA,native_lea=NATIVE_LEA,native_district=NATIVE_DISTRICT,year=YEAR,academic_year=ACADEMIC_YEAR,tables=TABLES,operational=sorted(OPERATIONAL),offered_grades=OFFER_GRADES,lower_grades=LOWER_GRADES,subjects=SUBJECTS,assessment_selector=ASSESSMENT_SELECTOR,planning_fields=PLANNING_FIELDS,policy=POLICY,sources=SOURCES,metadata=ORIGINAL_METADATA,inventories=ORIGINAL_INVENTORIES,raw_sha=RAW_INPUT_SHA,schema_sha=ORIGINAL_SCHEMA_SHA,definition_sha=DEFINITION_INPUT_SHA,identity_sha=ORIGINAL_IDENTITY_SHA,secondary_sha=STATE_EXTRACT_SHA,secondary_tn_sha=TN_SNAPSHOT_SHA,shared_time_ids=SHARED_TIME_IDS,shared_time_source_row=SHARED_TIME_SOURCE_ROW)

def require_runtime_contract():
    if POLICY_SHA!='1d422d6c56ddda504d34cb739d2a50de1b546f60d1306ee5a3453d14068aaa17' or LITERAL_POLICY_SHA!='1d422d6c56ddda504d34cb739d2a50de1b546f60d1306ee5a3453d14068aaa17' or fingerprint(POLICY)!='1d422d6c56ddda504d34cb739d2a50de1b546f60d1306ee5a3453d14068aaa17' or RUNTIME_CONTRACT_SHA!='a6006b7299894a4ca5924ab896904f03c5cb602d17cc59ce19e889837555ca9b' or LITERAL_RUNTIME_SHA!='a6006b7299894a4ca5924ab896904f03c5cb602d17cc59ce19e889837555ca9b' or fingerprint(runtime_contract())!='a6006b7299894a4ca5924ab896904f03c5cb602d17cc59ce19e889837555ca9b':
        raise ValueError('Immutable Memphis current source/policy/identity/year/selector/header/type/original-fingerprint contract changed')

def source_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def load_state_snapshot():
    require_runtime_contract();path=ROOT/'data/source/ccd-state-snapshots.json';blob=path.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=STATE_EXTRACT_SHA:raise ValueError('Complete immutable secondary CCD state extract missing or changed')
    payload=json.loads(blob)
    if type(payload['school_year'])is not str or payload['school_year']!='2024-25':raise ValueError('Secondary original year changed')
    state=next(s for s in payload['states']if s['state']['id']=='TN')
    if fingerprint(state)!=TN_SNAPSHOT_SHA:raise ValueError('Complete original Tennessee secondary snapshot changed')
    return state

def reported_count(raw):
    if raw is None:return None
    v=raw['STUDENT_COUNT']
    if type(v)is not str or type(raw['DMS_FLAG'])is not str:raise ValueError('Original CCD count and flags must retain string types')
    return int(v)if raw['DMS_FLAG']=='Reported'and re.fullmatch(r'\d+',v)else None

def exact_rate(value):
    if type(value)is not str:raise ValueError('Original EDC percentage must retain its string token')
    if not re.fullmatch(r'(?:0?\.\d+|[01](?:\.\d+)?)',value):return None
    parsed=float(value)
    return 100*parsed if 0<=parsed<=1 else None

def ccd_identity(raw,district=False):
    if (raw['SCHOOL_YEAR'],raw['ST'],raw['FIPST'],raw['STATENAME'],raw['LEAID'],raw['ST_LEAID'])!=(ACADEMIC_YEAR,'TN','47','TENNESSEE',LEA,NATIVE_LEA):raise ValueError('Original CCD year/state/exact LEA ownership changed')
    if district:return LEA
    if not re.fullmatch(LEA+r'\d{5}',raw['NCESSCH'])or not re.fullmatch(r'TN-00792-\d{4}',raw['ST_SCHID']):raise ValueError('Original authoritative NCES/native school identity changed')
    return raw['NCESSCH']

def offered_evidence(raw):
    flags={g:raw['G_'+g+'_OFFERED']for g in OFFER_GRADES};complete=raw['IGOFFERED']=='As reported'and raw['NOGRADES']=='No'and all(v in {'Yes','No'}for v in flags.values());offered=[g for g,v in flags.items()if v=='Yes'];lower=any(g in offered for g in ['PK','KG']+[str(i)for i in range(1,9)]);high=any(str(i)in offered for i in range(9,13));extra=any(g in offered for g in ['13','UG','AE']);scope='uncertain'if not complete else'other'if extra or not(lower or high)else'mixed'if lower and high else'HS'if high else'ES'
    return dict(flags=flags,complete_reported_flags=complete,scope=scope,offered=offered,tested_grade_offers=[str(i)for i in range(3,9)if flags[str(i)]=='Yes'],low=raw['GSLO'],high=raw['GSHI'],level=raw['LEVEL'])

def membership_evidence(total,grades):
    n=reported_count(total['raw'])if total else None;values={k:reported_count(e['raw'])for k,e in grades.items()};lower=[v for k,v in values.items()if k in LOWER_GRADES];full=bool(lower)and all(v is not None for v in lower);sum_lower=sum(lower)if full else None;outside={k:e for k,e in grades.items()if k not in LOWER_GRADES};outside_zero=all(e['raw']['STUDENT_COUNT']=='0'and e['raw']['DMS_FLAG']in {'Reported','Derived'}for e in outside.values());positive_tested=any((values.get(f'Grade {i}')or 0)>0 for i in range(3,9));reconciled=full and n is not None and sum_lower==n and outside_zero
    return dict(reported_total=n,total_source_row=total['source_row']if total else None,grade_source_rows={k:e['source_row']for k,e in grades.items()},reported_grade_counts=values,lower_grade_sum=sum_lower,explicit_zero_outside_lower=outside_zero,positive_reported_tested_grade=positive_tested,reconciled_pure_lower=reconciled,grade_rows_present=sorted(grades))

def income_evidence(total,direct,shared_hold):
    n=reported_count(total['raw'])if total else None;dc=reported_count(direct['raw'])if direct else None;reason='Missing/nonreported/zero own same-year membership'if n is None or n<=0 else'Missing/suppressed/nonreported own direct certification'if dc is None else'Direct certification exceeds own membership'if dc>n else None
    if direct and(direct['raw']['DATA_GROUP'],direct['raw']['TOTAL_INDICATOR'],direct['raw']['LUNCH_PROGRAM'])!=('Direct Certification','Education Unit Total','Not Applicable'):raise ValueError('Direct certification row is outside original approved category')
    pct=100*dc/n if reason is None else None
    return dict(reported_membership=n,reported_direct_certification=dc,reported_percentage=pct,percentage=pct,usable=reason is None and not shared_hold,exclusion=shared_hold or reason,membership_source_row=total['source_row']if total else None,direct_source_row=direct['source_row']if direct else None,definition='Reported individual CCD direct certification / own reported same-year membership; not full FRPL or universal meal receipt',valid_score_denominator=False)

def outcome_evidence(entry,subject,population_eligible,income,hold):
    raw=entry['raw']if entry else None;rate=exact_rate(raw['ProficientOrAbove_percent'])if raw else None;reason='No original regular All Students nativeG38 school subject row'if raw is None else'Original published G38 rate suppressed/ranged/missing'if rate is None else'Outside pure-lower grade configuration'if not population_eligible else hold or income['exclusion'];usable=reason is None and income['usable']
    return dict(subject=subject,native_rate=rate,raw_rate=raw['ProficientOrAbove_percent']if raw else None,usable=usable,exclusion=reason,source='edc_2025',source_row=entry['source_row']if entry else None,raw_tested=raw['StudentSubGroup_TotalTested']if raw else None,raw_proficient_count=raw['ProficientOrAbove_count']if raw else None,tested=None,valid_scores=None,sampling_variance=None,low=None,high=None,sampling_interval_available=False,ten_valid_scored_floor_certified=False)

def retain_original_row(table,raw):
    """Source-population selection only, independent of values, fit or diagnostics."""
    if table in {'membership','lea_membership'}:
        return raw['TOTAL_INDICATOR']=='Education Unit Total'or raw['TOTAL_INDICATOR']=='Subtotal 4 - By Grade'and(raw['GRADE']=='Not Specified'or all(raw[k]=='No Category Codes'for k in ['RACE_ETHNICITY','SEX']))
    if table=='assessment':
        return raw['GradeLevel']=='G38'and raw['StudentGroup']=='All Students'and raw['StudentSubGroup']=='All Students'and raw['Subject']in {'math','ela'}
    return True

def compact_original_inputs(inputs):
    omissions={};result={}
    for t in TABLES:
        section=inputs[t];kept=[];omitted=[];groups=Counter();identities=defaultdict(list)
        for e in section['records']:
            r=e['raw']
            if retain_original_row(t,r):kept.append(e);continue
            omitted.append(e['source_row'])
            if t=='assessment':
                group=(r['DataLevel'],r['StudentGroup'],r['StudentSubGroup'],r['GradeLevel'],r['Subject'],r['AssmtType']);identity=r['DataLevel']+':'+r['NCESSchoolID']
            else:
                group=(r['TOTAL_INDICATOR'],r['GRADE'],r['RACE_ETHNICITY'],r['SEX']);identity=r.get('NCESSCH',r['LEAID'])
            groups[group]+=1;identities[identity].append(e['source_row'])
        selection='Complete original target LEA total/grade membership rows, with all original fields and explicit NotSpecified grade records.'if t in {'membership','lea_membership'}else'Complete original AllStudents G38 Math/ELA rows across school/district/assessment types and outside IDs, with all original fields and masks.'if t=='assessment'else section['selection']
        result[t]={k:v for k,v in section.items()if k!='records'};result[t].update(selection=selection,records=kept)
        omissions[t]=dict(complete_original_records=len(section['records']),complete_original_typed_cells=sum(len(e['raw'])for e in section['records']),complete_target_records_sha256=fingerprint(section['records']),retained_records=len(kept),omitted_records=len(omitted),omitted_source_rows=omitted,omitted_population_counts=[dict(original_population=list(k),records=v)for k,v in sorted(groups.items())],omitted_rows_by_original_identity=dict(sorted(identities.items())),basis='No numeric rate/count, eligible-profile, charter, shared-time or diagnostic screen. Complete original file hashes and exact original row ordinals preserve unused-population provenance.')
    result['definitions']=inputs['definitions'];result['planning']=inputs['planning'];result['omitted_original_populations']=omissions
    return result

def _derive(document,state):
    require_runtime_contract()
    if fingerprint(state)!=TN_SNAPSHOT_SHA:raise ValueError('Original complete Tennessee secondary fields changed')
    contract=dict(schema_version=1,state='TN',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,state_extract=dict(path='data/source/ccd-state-snapshots.json',sha256=STATE_EXTRACT_SHA,TN_snapshot_sha256=TN_SNAPSHOT_SHA))
    if fingerprint({k:document.get(k)for k in contract})!=fingerprint(contract):raise ValueError('Source-only identity/year/provenance/policy/false approval contract changed')
    inputs=document['raw_inputs']
    if fingerprint(inputs)!=RAW_INPUT_SHA or set(inputs)!=set(TABLES)|{'definitions','planning','omitted_original_populations'}:raise ValueError('Complete immutable original inputs omitted or changed')
    meta={t:{k:v for k,v in inputs[t].items()if k!='records'}for t in TABLES}
    if fingerprint(meta)!=ORIGINAL_SCHEMA_SHA or fingerprint(inputs['definitions'])!=DEFINITION_INPUT_SHA or identity_fingerprint(inputs)!=ORIGINAL_IDENTITY_SHA:raise ValueError('Original schema/definition/identity/row fingerprint changed')
    for t in TABLES:
        s=inputs[t]
        if fingerprint(meta[t])!=fingerprint(ORIGINAL_METADATA[t])or len(s['records'])!=ORIGINAL_INVENTORIES[t]:raise ValueError('Complete original table header/selection/inventory changed')
        prev=1
        for e in s['records']:
            if type(e['source_row'])is not int or e['source_row']<=prev:raise ValueError('Original source rows require strict positive ascending integer references')
            prev=e['source_row'];r=e['raw']
            if type(r)is not dict or set(r)!=set(s['header'])or any(type(v)is not str for v in r.values()):raise ValueError('All original CSV fields and string cell types must remain exact')
            if t!='assessment':ccd_identity(r,t.startswith('lea_'))
            elif(r['State'],r['StateAbbrev'],r['StateFips'],r['SchYear'],r['NCESDistrictID'],r['StateAssignedDistID'],r['Version'])!=('Tennessee','TN','47','2024-25',LEA,NATIVE_DISTRICT,'V3.1'):raise ValueError('Original EDC year/state/native/NCES district/version ownership changed')
    directory={e['raw']['NCESSCH']:e for e in inputs['directory']['records']}
    if len(directory)!=len(inputs['directory']['records'])or len(inputs['lea_directory']['records'])!=1:raise ValueError('Duplicate school directory or district identity')
    totals={};grades=defaultdict(dict)
    for e in inputs['membership']['records']:
        r=e['raw'];key=r['NCESSCH']
        if key not in directory or r['ST_SCHID']!=directory[key]['raw']['ST_SCHID']:raise ValueError('Membership crosses exact original directory identity')
        if r['TOTAL_INDICATOR']=='Education Unit Total':
            if key in totals or any(r[f]!='No Category Codes'for f in ['GRADE','RACE_ETHNICITY','SEX']):raise ValueError('Duplicate/non-total membership population')
            totals[key]=e
        elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade':
            special=r['GRADE']=='Not Specified'and r['DMS_FLAG']=='Derived'and r['STUDENT_COUNT']=='0'and all(r[f]=='Not Specified'for f in ['RACE_ETHNICITY','SEX'])
            if r['GRADE']in grades[key]or not special and any(r[f]!='No Category Codes'for f in ['RACE_ETHNICITY','SEX']):raise ValueError('Duplicate/non-grade membership subtotal')
            grades[key][r['GRADE']]=e
    direct={}
    for e in inputs['lunch']['records']:
        r=e['raw'];key=r['NCESSCH']
        if key not in directory or r['ST_SCHID']!=directory[key]['raw']['ST_SCHID']:raise ValueError('Lunch crosses exact original directory identity')
        if r['DATA_GROUP']=='Direct Certification'and r['TOTAL_INDICATOR']=='Education Unit Total':
            if key in direct:raise ValueError('Duplicate original direct-certification total')
            direct[key]=e
    pairs=defaultdict(dict);all_native=defaultdict(list);district_g38=[]
    for e in inputs['assessment']['records']:
        r=e['raw']
        if r['DataLevel']=='School':
            if not re.fullmatch(LEA+r'\d{5}',r['NCESSchoolID'])or not re.fullmatch(r'792-\d{4}',r['StateAssignedSchID']):raise ValueError('Original EDC school NCES/native identity malformed')
            all_native[r['NCESSchoolID']].append(e['source_row'])
            if r['NCESSchoolID']in directory and r['StateAssignedSchID']!='792-'+directory[r['NCESSchoolID']]['raw']['ST_SCHID'].rsplit('-',1)[1]:raise ValueError('Native school code differs from authoritative same-NCES directory attachment')
        selected=all(r[k]==v for k,v in ASSESSMENT_SELECTOR.items())and r['Subject']in SUBJECTS.values()
        if selected:
            key=r['NCESSchoolID'];subject='reading'if r['Subject']=='ela'else'math'
            if subject in pairs[key]:raise ValueError('Duplicate exact regular nativeG38 subject')
            pairs[key][subject]=e
        if r['DataLevel']=='District'and r['GradeLevel']=='G38'and r['StudentGroup']=='All Students'and r['StudentSubGroup']=='All Students'and r['Subject']in SUBJECTS.values():district_g38.append(e['source_row'])
    note=next(e for e in inputs['definitions']['ccd_state_notes_2025']['worksheets']['Data Notes']['records']if e['source_row']==SHARED_TIME_SOURCE_ROW)
    if note['raw'][0]!='Tennessee'or note['raw'][5]!='CCD-0054'or sorted(set(re.findall(r'\b4700148\d{5}\b',note['raw'][11])))!=SHARED_TIME_IDS:raise ValueError('Exact original shared-time attribution note or named identities changed')
    hold_text='Unresolved shared-time enrolled-versus-served income/outcome attribution in original Tennessee CCD-0054; plausible reported count ratio does not certify source scope'
    links=[];secondary={r['id']:r for r in state['schools']}
    for key,e in directory.items():
        r=e['raw'];offered=offered_evidence(r);mem=membership_evidence(totals.get(key),grades.get(key,{}));oper=r['UPDATED_STATUS']in OPERATIONAL;eligible=oper and offered['scope']=='ES'and bool(offered['tested_grade_offers'])and mem['reported_total']is not None and mem['reported_total']>0 and mem['reconciled_pure_lower']and mem['positive_reported_tested_grade'];hold=hold_text if key in SHARED_TIME_IDS else None;income=income_evidence(totals.get(key),direct.get(key),hold);outcomes={s:outcome_evidence(pairs.get(key,{}).get(s),s,eligible,income,hold)for s in SUBJECTS};m=outcomes['math'];q=outcomes['reading'];paired=m['native_rate']is not None and q['native_rate']is not None;outcomes['combined']=dict(subject='combined',native_rate=(m['native_rate']+q['native_rate'])/2 if paired else None,raw_rate={'math':m['raw_rate'],'reading':q['raw_rate']},usable=m['usable']and q['usable'],exclusion=None if m['usable']and q['usable']else hold or'Combined requires both exact usable original subject rates and approved source attribution',source='edc_2025',source_row={'math':m['source_row'],'reading':q['source_row']},raw_tested={'math':m['raw_tested'],'reading':q['raw_tested']},tested=None,valid_scores=None,sampling_variance=None,low=None,high=None,sampling_interval_available=False,ten_valid_scored_floor_certified=False)
        cross=secondary.get(key)
        if cross:
            if cross['enrollment']!=income['reported_membership']or cross['low_income']!=income['reported_direct_certification']or cross['income']!=income['reported_percentage']:raise ValueError('Secondary original same-year reported DC/member fields differ')
            for s in SUBJECTS:
                if cross['outcomes'][s]['proficiency']!=outcomes[s]['native_rate']:raise ValueError('Secondary exact original G38 rates differ; no state-fit reuse permitted')
        reason=None if eligible else'School not operational'if not oper else'Outside complete unadjusted pure-lower offered grades'if offered['scope']!='ES'or not offered['tested_grade_offers']else'Missing/nonreported/nonpositive or unreconciled pure-lower enrolled grades'
        links.append(dict(school_id=key,ncessch=key,native_school_id=r['ST_SCHID'],name=r['SCH_NAME'],directory_source_row=e['source_row'],operational=oper,ccd_flags=dict(status=r['UPDATED_STATUS'],status_text=r['UPDATED_STATUS_TEXT'],charter=r['CHARTER_TEXT'],school_type=r['SCH_TYPE_TEXT']),offered=offered,membership=mem,income=income,source_profile_eligible=eligible,population_exclusion=reason,source_attribution_hold=hold,shared_time_note=dict(source='ccd_state_notes_2025',worksheet='Data Notes',source_row=SHARED_TIME_SOURCE_ROW,error_code='CCD-0054')if hold else None,native_school_source_rows=all_native.get(key,[]),subjects=outcomes,secondary_original_fields_crosschecked=cross is not None))
    prospective=[r for r in links if r['source_profile_eligible']];unheld=[r for r in prospective if r['source_attribution_hold']is None];usable={s:sum(r['subjects'][s]['usable']for r in prospective)for s in ['math','reading','combined']};raw_rates={s:sum(r['subjects'][s]['native_rate']is not None for r in prospective)for s in ['math','reading','combined']};leatotals=[e for e in inputs['lea_membership']['records']if e['raw']['TOTAL_INDICATOR']=='Education Unit Total'];assert len(leatotals)==1;lea_count=reported_count(leatotals[0]['raw']);school_values=[r['membership']['reported_total']for r in links if r['operational']];oper_sum=sum(v for v in school_values if v is not None);native_only=[dict(ncessch=k,native_source_rows=all_native[k],g38_source_rows={s:e['source_row']for s,e in pairs.get(k,{}).items()},exclusion='Native NCES school identity absent from exact same-year CCD directory; no inferred income or correction')for k in sorted(set(all_native)-set(directory))]
    coverage=dict(source_rows={t:len(inputs[t]['records'])for t in TABLES},original_records=sum(len(inputs[t]['records'])for t in TABLES),original_typed_cells=sum(sum(len(e['raw'])for e in inputs[t]['records'])for t in TABLES),directory_records=len(links),operational_roster=sum(r['operational']for r in links),status=dict(Counter(r['ccd_flags']['status_text']for r in links)),operational_offered_scope=dict(Counter(r['offered']['scope']for r in links if r['operational'])),membership_school_totals=len(totals),direct_certification_school_totals=len(direct),native_school_ids=len(all_native),native_g38_school_ids=len(pairs),native_only_ids=[r['ncessch']for r in native_only],prospective_grade_profiles=len(prospective),prospective_raw_published_rates=raw_rates,prospective_unheld_grade_profiles=len(unheld),prospective_usable=usable,shared_time_named_ids=SHARED_TIME_IDS,shared_time_named_count=len(SHARED_TIME_IDS),shared_time_prospective_hold_ids=sorted(r['school_id']for r in prospective if r['source_attribution_hold']),shared_time_outside_grade_ids=sorted(k for k in SHARED_TIME_IDS if k not in {r['school_id']for r in prospective}),prospective_charters=sum(r['ccd_flags']['charter']=='Yes'for r in prospective),usable_charters={s:sum(r['ccd_flags']['charter']=='Yes'and r['subjects'][s]['usable']for r in prospective)for s in ['math','reading','combined']},operational_missing_membership_ids=sorted(r['school_id']for r in links if r['operational']and r['membership']['reported_total']is None),operational_missing_direct_certification_ids=sorted(r['school_id']for r in links if r['operational']and r['income']['reported_direct_certification']is None),district_reported_enrollment=lea_count,reported_operational_enrollment_sum=oper_sum,missing_operational_enrollment_count=sum(v is None for v in school_values),district_minus_reported_operational_enrollment=lea_count-oper_sum if lea_count is not None else None,secondary_original_profile_matches=sum(r['secondary_original_fields_crosschecked']for r in links),verified_valid_score_counts=0,ten_valid_scored_floor_certified=False,model_sampling_intervals_available=False,canonical_integration_pending=True,model_results=0)
    omitted=inputs['omitted_original_populations'];coverage.update(complete_original_source_rows={t:omitted[t]['complete_original_records']for t in TABLES},complete_original_records=sum(v['complete_original_records']for v in omitted.values()),complete_original_typed_cells=sum(v['complete_original_typed_cells']for v in omitted.values()),omitted_original_records=sum(v['omitted_records']for v in omitted.values()),retention_basis='Full original file checksums plus complete needed raw rows/fields/masks and exact omitted-population source-row inventories; no value/fit/charter/hold screen')
    return dict(roster_links=links,outside_native_profiles=native_only,district_native_g38_source_rows=district_g38,cohorts=dict(grade_configuration=dict(profile_ids=[r['school_id']for r in prospective],subjects={s:dict(raw_published_available=raw_rates[s],usable=usable[s],member_ids=[r['school_id']for r in prospective if r['subjects'][s]['usable']],charter=dict(Counter(r['ccd_flags']['charter']for r in prospective if r['subjects'][s]['usable'])))for s in ['math','reading','combined']})),coverage=coverage,raw_schema_sha256=ORIGINAL_SCHEMA_SHA,raw_definition_sha256=DEFINITION_INPUT_SHA,original_identity_sha256=ORIGINAL_IDENTITY_SHA,source_policy_sha256=POLICY_SHA,source_runtime_sha256=RUNTIME_CONTRACT_SHA,source_definition_evidence=dict(original_definition_sha256=DEFINITION_INPUT_SHA,whole_primary_sources=sorted(inputs['definitions']),shared_time_note=note))

def derive(document,snapshot=None):
    state=load_state_snapshot()
    if snapshot is not None and fingerprint(snapshot)!=TN_SNAPSHOT_SHA:raise ValueError('Cached Tennessee secondary snapshot differs')
    return _derive(document,state)

def validate(document,snapshot=None):
    expected=base_document(document['raw_inputs']);expected.update(derive(document,snapshot))
    if fingerprint(document)!=fingerprint(expected):raise ValueError('Complete source metadata/raw/grade/income/missingness/attribution/cohort replay differs')
    return expected['coverage']

def base_document(inputs):
    return dict(schema_version=1,state='TN',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,raw_inputs=inputs,state_extract=dict(path='data/source/ccd-state-snapshots.json',sha256=STATE_EXTRACT_SHA,TN_snapshot_sha256=TN_SNAPSHOT_SHA))

def read_csv_archive(source_id,selection):
    p=ROOT/SOURCES[source_id]['path']
    with zipfile.ZipFile(p)as z:member=next(x for x in z.namelist()if x.endswith('.csv'))
    process=subprocess.Popen(['unzip','-p',str(p),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig');reader=csv.DictReader(process.stdout)
    try:
        rows=[dict(source_row=i,raw=r)for i,r in enumerate(reader,2)if selection(r)]
        if process.wait()!=0:raise ValueError('Pinned original archive cannot be decompressed')
    finally:
        process.stdout.close()
        if process.poll()is None:process.terminate();process.wait()
    return member,reader.fieldnames,rows

def extract_raw_inputs():
    require_runtime_contract()
    for s in SOURCES.values():
        p=ROOT/s['path']
        if p.stat().st_size!=s['bytes']or source_sha(p)!=s['sha256']:raise ValueError('Complete original source byte pin changed: '+s['path'])
    inputs={};same=lambda r:r.get('LEAID')==LEA or r.get('ST_LEAID')==NATIVE_LEA
    for t,key in [('directory','ccd_directory_2025'),('lea_directory','ccd_lea_directory'),('membership','ccd_membership_2025'),('lea_membership','ccd_lea_membership'),('lunch','ccd_lunch_2025')]:
        member,header,rows=read_csv_archive(key,same);inputs[t]=dict(ORIGINAL_METADATA[t],member=member,header=header,records=rows)
    with(ROOT/SOURCES['edc_2025']['path']).open(encoding='utf-8-sig',newline='')as h:
        reader=csv.DictReader(h);rows=[dict(source_row=i,raw=r)for i,r in enumerate(reader,2)if r.get('NCESDistrictID')==LEA or r.get('StateAssignedDistID')in {'792','00792','TN-00792'}]
        inputs['assessment']=dict(ORIGINAL_METADATA['assessment'],header=reader.fieldnames,records=rows)
    import openpyxl
    from pypdf import PdfReader
    def cell(v):return dict(original_type=type(v).__name__,value=v.isoformat())if isinstance(v,(datetime.datetime,datetime.date,datetime.time))else v
    definitions={}
    for key in ['ccd_state_notes_2025','edc_codebook_v3_1','ccd_lunch_layout','ccd_membership_layout','ccd_directory_layout']:
        b=openpyxl.load_workbook(ROOT/SOURCES[key]['path'],read_only=True,data_only=True)
        try:definitions[key]=dict(source_id=key,worksheets={name:dict(worksheet=name,records=[dict(source_row=i,raw=[cell(v)for v in row])for i,row in enumerate(b[name].values,1)])for name in b.sheetnames})
        finally:b.close()
    definitions['edc_technical_v3_1']=dict(source_id='edc_technical_v3_1',pages=[dict(page_number=i+1,text=p.extract_text()or'')for i,p in enumerate(PdfReader(ROOT/SOURCES['edc_technical_v3_1']['path']).pages)]);definitions['nces_lunch_definitions']=dict(source_id='nces_lunch_definitions',original_html=(ROOT/SOURCES['nces_lunch_definitions']['path']).read_text());inputs['definitions']=definitions
    payload=json.loads((ROOT/'data/source/district-comparison-candidates.json').read_text());r=next(x for x in payload['agencies']if x['nces_lea_id']==LEA);inputs['planning']=dict(source='data/source/district-comparison-candidates.json',sources=payload['sources'],record={k:r[k]for k in PLANNING_FIELDS})
    return compact_original_inputs(inputs)

def extract(output=OUTPUT):
    doc=base_document(extract_raw_inputs());doc.update(derive(doc));validate(doc);Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(doc,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n');return doc['coverage']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--extract',action='store_true');p.add_argument('--output',type=Path,default=OUTPUT);args=p.parse_args();coverage=extract(args.output)if args.extract else validate(json.loads(args.output.read_text()));print(json.dumps(coverage,indent=2))

if __name__=='__main__':main()

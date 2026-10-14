"""Original 2024–25 Denver CCD/CDE income, enrolled grades and CMAS source audit only."""
import argparse,ast,csv,datetime,hashlib,json,math,re,subprocess,types,zipfile
from collections import Counter,defaultdict
from pathlib import Path
import openpyxl
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/source/denver-district-audit.json'
LEA='0803360';NATIVE_LEA='CO-0880';NATIVE_DISTRICT='0880';YEAR=2025;ACADEMIC_YEAR='2024-2025'
OPERATIONAL={'1','3','4','5','8'}
OFFER_GRADES=['PK','KG']+[str(g)for g in range(1,14)]+['UG','AE']
GRADES=['Pre-K','Half-Day K','Full-Day K','1st','2nd','3rd']+[str(g)+'th'for g in range(4,13)]
TESTED_GRADES=['3rd']+[str(g)+'th'for g in range(4,9)]
HIGH_GRADES=[str(g)+'th'for g in range(9,13)]
SUBJECTS={'math':'Mathematics','reading':'English Language Arts'}
TABLES=['directory','membership','lea_directory','lea_membership','grades','income','cmas','sat']
MIN_VALID=16
POLICY={
 'identity':'Exact complete original2024–25 CCD NCES0803360 / CO-0880. Retain full12-digit NCES IDs and native CO-0880-SSSS. Original CDE organization/district0880 and schoolSSSS are already four-digit strings; exact DDDDSSSS is documented by2025 primary CMAS layout page7. No numeric conversion, zero-padding guesses, suffix/name/address matches or detention aggregate99999999 establish school ownership.',
 'population':'Prospective pure lower source profiles require exact operational CCD identity, complete As reported offered flags with a grade3–8 offer, no9–13/AE, high bound01–08 and no uncertain ungraded membership. Original CDE October2024 full PK/half-K/full-K/grades1–12 enrollment must reconcile to PK–12 and contain a positive grade3–8 with explicit-zero grades9–12. Offered and enrolled evidence remain distinct. Charters, school types, income extremes, influence and proficiency never select scope. High, mixed, primary, missing-native and uncertain configurations remain outside.',
 'income':'Same-year2024–25 Student October K–12 Free and Reduced Lunch Eligibility by School: each school’s own published three-decimal % Free and Reduced fraction times100, preserving source rounding, reconciled to its own K–12 Count and Free and Reduced Count when unmasked. Own K–12 denominator excludes pre-K and matches native grade enrollment after excluding pre-K. No ratio precision substituted for the published fraction, weighted/funding numerator, other-year backfill or masked eligibility reconstructed.',
 'income_definition':'Individual household-income application/alternate income form or categorical/direct-certification eligibility; Healthy School Meals for All supplies no-cost meals regardless of eligibility. Universal meal receipt is not universal economic disadvantage. Native October2024 record uses reported schoolwide eligibility, not the spring assessed-grade subset. Primary current eligibility guidance retains the previous-year eligibility carryover up to30 operating days; exact campus survey coverage and October carryover attribution are not independently certified.',
 'assessment':'Original July2025 CDE District and School Achievement Results, CMAS2020 Colorado Academic Standards, SCHOOL and All Grades rows for Mathematics and English Language Arts only. These are directly published whole-school grades3–8 CMAS totals. CSLA/Spanish, CoAlt, SAT/PSAT, high/mixed/primary scope and other-year columns remain separate original evidence. No grade averages, suppressed-component recovery, statewide fits or alternate assessment splice.',
 'denominators':'Primary2025 CMAS Summary File Layout v3.2 page3 excludes students without scores from performance-level denominators; page10 calls TotNumScored Number of Valid Scores. Use original exact Number of Valid Scores and Number Met or Exceeded Expectations; ratio100*met/N must reconcile to original one-decimal2025 percentage within0.051. Exact valid scores must be at least16 under the existing conservative Colorado extraction threshold. Total records, no scores, participation and enrollment cannot replace valid scores. Source-level counts are evidence only; no fits/interval endpoints are calculated here.',
 'population_rules':'Primary layout group001 excludes report-suppressed registrations and specified other-assessment/duplicate, withdrawn, medical-exemption and part-public/part-home-school invalidations; school-level group001 additionally excludes Expelled=1. Whole-summary valid-score population differs from total registrations, October enrollment and income. Retain low participation/representativeness cautions; native primary population rules do not certify complete admissions/program attribution.',
 'suppression':'Original - -, *, N/A, blanks and bounded <16 values remain unavailable. Real zeros remain zeros; do not infer suppressed counts from margins, use totals to recover missing grade components or substitute published rates with reconstructed precision. Published whole-school total is used directly and never requires suppressed grade components to be recovered.',
 'combined':'Equal mean of usable original whole-school Math and ELA count ratios, with independent subject valid-score counts retained as components. It is not both-subject proficiency and has no invented paired valid-score count.',
 'attribution':'CCD charter/type and original names remain source evidence. No verified admissions, virtual-provider, program or geographic classifications; names and charter status never supply those attributes. Missing Gilliam CO-0880-9803 is not joined to the statewide detention aggregate by name or difference. Exact native school IDs determine attribution.',
 'release':'Source/cohort audit only pending independent source review, separate numerical review and later integration. All source/modeling approvals remain false; no model results, canonical writes or publication.'}

SOURCES = {'ccd_directory': {'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip', 'bytes': 13352819, 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab'}, 'ccd_membership': {'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip', 'bytes': 212696691, 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d'}, 'ccd_lea_directory': {'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip', 'bytes': 2830266, 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9'}, 'ccd_lea_membership': {'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip', 'bytes': 68497561, 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba'}, 'co_grades': {'path': 'data/raw/colorado/grades2025.xlsx', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/7efacffc-8335-4735-9b12-fee840351810', 'bytes': 221914, 'sha256': 'ce0b2fc80bb824e35c16d938ebe92803202574d21629b1e1cd02180cd17680d0'}, 'co_income': {'path': 'data/raw/colorado/frl2025.xlsx', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/edf7f72b-6728-4b48-a3aa-ae75ab2ad968', 'bytes': 190206, 'sha256': '13cddd8450bf45dcc1fabfb41e2e76279d39424b2e66ec572ccb917fa7807629'}, 'co_cmas': {'path': 'data/raw/colorado/cmas2025.xlsx', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/5c130960-c90c-444a-98dc-41b35c11431b', 'bytes': 2854367, 'sha256': '4b98b24812f867ab62910400e3e9a69dfb3a65aa9b7ebb900841b7362f1e69f9'}, 'co_sat': {'path': 'data/raw/colorado/sat2025.xlsx', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/37066be1-57a4-40f4-8235-3c1b10cb0e75', 'bytes': 1313839, 'sha256': 'a557bbab6da5c047671d6b001ae1daec96efb6d7a608ac89f25990d0a5cb247e'}, 'co_cmas_layout': {'path': 'data/raw/colorado/cmas2025-layout.pdf', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/f6b76141-39d7-4787-b7e9-5a5777952cb7', 'bytes': 515699, 'sha256': 'ee55683c20c99d81a9ab763286c790665e8db977445c3c4c39c3ab61c735ddee'}, 'co_sat_layout': {'path': 'data/raw/colorado/sat2025-layout.pdf', 'url': 'https://ed.cde.state.co.us/fs/resource-manager/view/7bd1ffa6-490b-44b9-9dee-933d32a9c0c7', 'bytes': 376435, 'sha256': '29f59e4387af992a29c55174d447bc98125193f95a72980b71a6dbb0b9b3b25e'}, 'co_income_archive': {'path': 'data/raw/colorado/income-page.html', 'url': 'https://ed.cde.state.co.us/cdereval/pupilmembership-statistics/data-insights-resources-archives', 'bytes': 112430, 'sha256': '18df43bdd0bf4de2b549c79b2170ff618d25e689241d5ebe06187ee09702f72b'}, 'co_assessment_page': {'path': 'data/raw/colorado/assessment-page.html', 'url': 'https://ed.cde.state.co.us/assessment/cmas-dataandresults-2025', 'bytes': 54993, 'sha256': '50dc669ae62b10d910aafe6fc4f8e13600ac07b6862ee022cdb30eab4303fd5c'}, 'co_eligibility': {'path': 'data/build/denver-source-implementation/originals/eligibility.html', 'url': 'https://ed.cde.state.co.us/nutrition/manage-program-operations/determine-program-eligibility', 'bytes': 89663, 'sha256': 'd85cc940c9d8d21ac01b7a753184497ad88716896372e57ea19ab47c08a578ff'}, 'ccd_notes': {'path': 'data/raw/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'bytes': 210984, 'sha256': '6476b6b28b700389e261b87377d9cd249935503d53b5919fe1b7ef8b1052d1a7'}, 'ccd_membership_layout': {'path': 'data/raw/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx', 'bytes': 40687, 'sha256': 'cc3afc95a5226da12aec2f77b264477adfe9d85bb250e71c4dab534b5a591fd1'}, 'ccd_directory_layout': {'path': 'data/raw/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx', 'bytes': 54414, 'sha256': 'aa3be279c7a175be76ce43e451fb8ba513481e7a80f009abf7de3ad4cf33f8cf'}, 'co_secondary': {'path': 'data/source/colorado.json', 'url': 'https://ed.cde.state.co.us/assessment/cmas-dataandresults-2025', 'bytes': 5858075, 'sha256': '4cd96d0f29d3c6ebaacbc00bba4d7505927081d3f2b9988d1a0b6c2335ea4acb'}}
ORIGINAL_METADATA = {'directory': {'source_id': 'ccd_directory', 'member': 'ccd_sch_029_2425_w_1a_073025.csv', 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'SCH_TYPE_TEXT', 'SCH_TYPE', 'RECON_STATUS', 'OUT_OF_STATE_FLAG', 'CHARTER_TEXT', 'CHARTAUTH1', 'CHARTAUTHN1', 'CHARTAUTH2', 'CHARTAUTHN2', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED'], 'complete_target_records': 198, 'complete_target_cells': 12870, 'complete_target_sha256': 'cf97df7b50f41f4d756d5ed6e67cc877dd310ad225f14ec0c8c23c74c89222e3', 'retained_records': 198}, 'membership': {'source_id': 'ccd_membership', 'member': 'ccd_sch_052_2425_l_1a_073025.csv', 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'SCH_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'ST_SCHID', 'NCESSCH', 'SCHID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'complete_target_records': 22066, 'complete_target_cells': 397188, 'complete_target_sha256': '89863bba0627ae69e668df8ddf052083c23793f278cbd0e60993e1427fd18aca', 'retained_records': 1342}, 'lea_directory': {'source_id': 'ccd_lea_directory', 'member': 'ccd_lea_029_2425_w_1a_073025.csv', 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'MSTREET1', 'MSTREET2', 'MSTREET3', 'MCITY', 'MSTATE', 'MZIP', 'MZIP4', 'LSTREET1', 'LSTREET2', 'LSTREET3', 'LCITY', 'LSTATE', 'LZIP', 'LZIP4', 'PHONE', 'WEBSITE', 'SY_STATUS', 'SY_STATUS_TEXT', 'UPDATED_STATUS', 'UPDATED_STATUS_TEXT', 'EFFECTIVE_DATE', 'LEA_TYPE', 'LEA_TYPE_TEXT', 'OUT_OF_STATE_FLAG', 'CHARTER_LEA', 'CHARTER_LEA_TEXT', 'NOGRADES', 'G_PK_OFFERED', 'G_KG_OFFERED', 'G_1_OFFERED', 'G_2_OFFERED', 'G_3_OFFERED', 'G_4_OFFERED', 'G_5_OFFERED', 'G_6_OFFERED', 'G_7_OFFERED', 'G_8_OFFERED', 'G_9_OFFERED', 'G_10_OFFERED', 'G_11_OFFERED', 'G_12_OFFERED', 'G_13_OFFERED', 'G_UG_OFFERED', 'G_AE_OFFERED', 'GSLO', 'GSHI', 'LEVEL', 'IGOFFERED', 'OPERATIONAL_SCHOOLS'], 'complete_target_records': 1, 'complete_target_cells': 58, 'complete_target_sha256': 'cb2db1de7c1df5cc99a82ce1ff87591d35d744fbc64a5a9f1583c09d131836cb', 'retained_records': 1}, 'lea_membership': {'source_id': 'ccd_lea_membership', 'member': 'ccd_lea_052_2425_l_1a_073025.csv', 'header': ['SCHOOL_YEAR', 'FIPST', 'STATENAME', 'ST', 'LEA_NAME', 'STATE_AGENCY_NO', 'UNION', 'ST_LEAID', 'LEAID', 'GRADE', 'RACE_ETHNICITY', 'SEX', 'STUDENT_COUNT', 'TOTAL_INDICATOR', 'DMS_FLAG'], 'complete_target_records': 243, 'complete_target_cells': 3645, 'complete_target_sha256': 'e37b56a1611a4ccc58c140aa916a47359ac0588274feda2a7fca71b815aca2d8', 'retained_records': 15}, 'grades': {'source_id': 'co_grades', 'worksheet': '2024-2025 Data', 'header_source_row': 3, 'upper_header_source_row': None, 'raw_header': ['Organization Code', 'Organization Name', 'School Code', 'School Name', 'Pre-K', 'Half-Day K', 'Full-Day K', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th', 'PK-12 Count'], 'upper_raw_header': None, 'header': ['Organization Code', 'Organization Name', 'School Code', 'School Name', 'Pre-K', 'Half-Day K', 'Full-Day K', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th', 'PK-12 Count'], 'complete_target_records': 197, 'complete_target_cells': 3940, 'complete_target_sha256': '3bed62bece8ff324c374f8b7895d06a5367db0e971fc23af2aaaf6e94fc53b06', 'retained_records': 197}, 'income': {'source_id': 'co_income', 'worksheet': '2024-2025 Data', 'header_source_row': 3, 'upper_header_source_row': None, 'raw_header': ['Organization Code', 'Organization Name', 'School Code', 'School Name', 'K-12 Count', 'Free Lunch', 'Reduced Lunch', 'Paid Lunch', 'Free and Reduced Count', '% Free', '% Reduced', '% Free and Reduced', None], 'upper_raw_header': None, 'header': ['Organization Code', 'Organization Name', 'School Code', 'School Name', 'K-12 Count', 'Free Lunch', 'Reduced Lunch', 'Paid Lunch', 'Free and Reduced Count', '% Free', '% Reduced', '% Free and Reduced', None], 'complete_target_records': 195, 'complete_target_cells': 2535, 'complete_target_sha256': '6847b3b457dbaada3edf204e361e585251694104799f746031b5dee1423ba4de', 'retained_records': 195}, 'cmas': {'source_id': 'co_cmas', 'worksheet': 'CMAS ELA and Math', 'header_source_row': 18, 'upper_header_source_row': None, 'raw_header': ['Level', 'District Code', 'District Name', 'School Code', 'School Name', 'Content', 'Grade', 'Number of Total Records', 'Number of Valid Scores', 'Number of No Scores', 'Participation Rate 2025', 'Participation Rate 2024', 'Participation Rate 2023', 'Mean Scale Score', 'Standard Deviation', 'Number Did Not Yet Meet Expectations', 'Percent Did Not Yet Meet Expectations', 'Number Partially Met Expectations', 'Percent Partially Met Expectations', 'Number Approached Expectations', 'Percent Approached Expectations', 'Number Met Expectations', 'Percent Met Expectations', 'Number Exceeded Expectations', 'Percent Exceeded Expectations', 'Number Met or Exceeded Expectations', '2025', 2024, 2023, 'Change\n2025-2024', 'Congressional\nDistrict'], 'upper_raw_header': None, 'header': ['Level', 'District Code', 'District Name', 'School Code', 'School Name', 'Content', 'Grade', 'Number of Total Records', 'Number of Valid Scores', 'Number of No Scores', 'Participation Rate 2025', 'Participation Rate 2024', 'Participation Rate 2023', 'Mean Scale Score', 'Standard Deviation', 'Number Did Not Yet Meet Expectations', 'Percent Did Not Yet Meet Expectations', 'Number Partially Met Expectations', 'Percent Partially Met Expectations', 'Number Approached Expectations', 'Percent Approached Expectations', 'Number Met Expectations', 'Percent Met Expectations', 'Number Exceeded Expectations', 'Percent Exceeded Expectations', 'Number Met or Exceeded Expectations', '2025', '2024', '2023', 'Change 2025-2024', 'Congressional District'], 'complete_target_records': 1500, 'complete_target_cells': 46500, 'complete_target_sha256': 'c9fee38cf24beb172afe1e2c32e71e883902496d568d06f1fb6640f546b1cb28', 'retained_records': 1500}, 'sat': {'source_id': 'co_sat', 'worksheet': 'PSAT_SAT RW and Math', 'header_source_row': 17, 'upper_header_source_row': 16, 'raw_header': ['Level', 'District Code', 'District Name', 'School Code', 'School Name', 'Content', 'Grade', 'Number of Total Records \n2025', 'Number of Valid Scores \n2025', 'Number of No Scores\n 2025', 'Participation Rate \n2025', 'Participation Rate \n2024', 'Participation Rate \n2023', 'Mean Scale Score \n2025', 'Standard Deviation \n2025', 'Number Did Not Yet Meet Expectations \n2025', 'Percent Did Not Yet Meet Expectations\n2025', 'Number Approached Expectations\n2025', 'Percent Approached Expectations\n2025', 'Number Met Expectations\n2025', 'Percent Met Expectations\n2025', 'Number Exceeded Expectations\n2025', 'Percent Exceeded Expectations\n2025', None, None, None, None, None, None], 'upper_raw_header': ['Test Information', None, None, None, None, None, None, 'Participation Information', None, None, None, None, None, 'Score Information', None, 'Performance Level Information', None, None, None, None, None, None, None, 'Number Met or Exceeded Expectations \n2025', 'Percent Met or Exceeded Expectations \n2025', 'Percent Met or Exceeded Expectations \n2024', 'Percent Met or Exceeded Expectations \n2023', 'Change \n 2025-2024', 'Congressional District\n2025'], 'header': ['Level', 'District Code', 'District Name', 'School Code', 'School Name', 'Content', 'Grade', 'Number of Total Records 2025', 'Number of Valid Scores 2025', 'Number of No Scores 2025', 'Participation Rate 2025', 'Participation Rate 2024', 'Participation Rate 2023', 'Mean Scale Score 2025', 'Standard Deviation 2025', 'Number Did Not Yet Meet Expectations 2025', 'Percent Did Not Yet Meet Expectations 2025', 'Number Approached Expectations 2025', 'Percent Approached Expectations 2025', 'Number Met Expectations 2025', 'Percent Met Expectations 2025', 'Number Exceeded Expectations 2025', 'Percent Exceeded Expectations 2025', 'Number Met or Exceeded Expectations 2025', 'Percent Met or Exceeded Expectations 2025', 'Percent Met or Exceeded Expectations 2024', 'Percent Met or Exceeded Expectations 2023', 'Change 2025-2024', 'Congressional District 2025'], 'complete_target_records': 666, 'complete_target_cells': 19314, 'complete_target_sha256': 'e0d9ed15986c62e4acceb74dc5e0b4069694d98ccdffc31b77811648630dfa57', 'retained_records': 666}}
ORIGINAL_INVENTORIES = {'directory': 198, 'membership': 1342, 'lea_directory': 1, 'lea_membership': 15, 'grades': 197, 'income': 195, 'cmas': 1500, 'sat': 666}
RAW_INPUT_SHA = '915ebeceb1f49ab2dce88641f7c794a2382c00c864c3299a1f3bd92728e33073'
ORIGINAL_SCHEMA_SHA = '77200056341d9256899b4620b4e9152a0b931e202b8a28d445b9f88ef77131fe'
DEFINITION_INPUT_SHA = '8e63b07071cff4673ee7b7a417024a5be38624c5cbd96b2cb0805be7c5f35531'
ORIGINAL_IDENTITY_SHA = '6e508f2847ca4bb6bc5d6c2717fb6afbc0db6ee2913db66513358edf4f8780d6'
POLICY_SHA = 'd44463e38170adbe8fcf6ce3d80785aaf5373c4779a41fe49556f9a19999858d'
RUNTIME_CONTRACT_SHA = 'd81f12038df90328b90b0af355341716435af45f0eb5be2cec89230e026b31e5'

def fingerprint(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def source_sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def code_contract(code):
 def constant(v):
  if isinstance(v,types.CodeType):return code_contract(v)
  if isinstance(v,tuple):return['tuple',[constant(q)for q in v]]
  if isinstance(v,frozenset):return['frozenset',sorted((constant(q)for q in v),key=repr)]
  if isinstance(v,slice):return['slice',constant(v.start),constant(v.stop),constant(v.step)]
  if isinstance(v,bytes):return['bytes',v.hex()]
  if v is Ellipsis:return['ellipsis']
  return[type(v).__name__,v]
 return dict(argcount=code.co_argcount,posonly=code.co_posonlyargcount,kwonly=code.co_kwonlyargcount,names=list(code.co_names),varnames=list(code.co_varnames),freevars=list(code.co_freevars),cellvars=list(code.co_cellvars),flags=code.co_flags,bytecode=code.co_code.hex(),constants=[constant(v)for v in code.co_consts])
def semantic_sources():
 names=['source_sha','original_pin','extract_raw_inputs','base_document','validate','native_identity','ccd_identity','number','count','ccd_count','offered_evidence','grade_evidence','income_evidence','outcome_evidence','summarize','schema_fingerprint','identity_fingerprint','validate_raw_inputs']
 text=Path(__file__).read_text();tree=ast.parse(text);nodes={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names}
 if set(nodes)!=set(names):raise ValueError('All original semantic declarations required')
 return{name:ast.get_source_segment(text,nodes[name])for name in names}
def require_live_semantics():
 compiled=compile(Path(__file__).read_text(),str(__file__),'exec',dont_inherit=True);reference={c.co_name:c for c in compiled.co_consts if isinstance(c,types.CodeType)}
 for name in semantic_sources():
  actual=globals()[name]
  if not isinstance(actual,types.FunctionType)or code_contract(actual.__code__)!=code_contract(reference[name]):raise ValueError('Current source semantic helper changed: '+name)
def runtime_contract():return dict(lea=LEA,native_lea=NATIVE_LEA,native_district=NATIVE_DISTRICT,year=YEAR,academic_year=ACADEMIC_YEAR,operational=sorted(OPERATIONAL),offered_grades=OFFER_GRADES,enrolled_grades=GRADES,tested_grades=TESTED_GRADES,high_grades=HIGH_GRADES,subjects=SUBJECTS,tables=TABLES,minimum_valid=MIN_VALID,sources=SOURCES,metadata=ORIGINAL_METADATA,inventories=ORIGINAL_INVENTORIES,raw=RAW_INPUT_SHA,schema=ORIGINAL_SCHEMA_SHA,definitions=DEFINITION_INPUT_SHA,identity=ORIGINAL_IDENTITY_SHA,policy=POLICY,semantic_sources=semantic_sources())
def require_runtime_contract():
 if (POLICY_SHA!='d44463e38170adbe8fcf6ce3d80785aaf5373c4779a41fe49556f9a19999858d'or RUNTIME_CONTRACT_SHA!='d81f12038df90328b90b0af355341716435af45f0eb5be2cec89230e026b31e5'or fingerprint(POLICY)!='d44463e38170adbe8fcf6ce3d80785aaf5373c4779a41fe49556f9a19999858d'or fingerprint(runtime_contract())!='d81f12038df90328b90b0af355341716435af45f0eb5be2cec89230e026b31e5'):raise ValueError('Immutable Denver source policy/identity/schema/semantic runtime changed')
 require_live_semantics()
def require_current_originals():
 require_runtime_contract()
 for key,pin in SOURCES.items():
  path=ROOT/pin['path']
  if path.stat().st_size!=pin['bytes']or source_sha(path)!=pin['sha256']:raise ValueError('Complete current original fingerprint changed: '+key)
def native_identity(raw):
 d=raw.get('Organization Code',raw.get('District Code'));s=raw.get('School Code')
 if type(d)is not str or d!=NATIVE_DISTRICT or type(s)is not str or not re.fullmatch(r'\d{4}',s):raise ValueError('Exact four-digit original native district/school strings required')
 return 'CO-'+d+'-'+s
def ccd_identity(raw,lea=False):
 if(raw['SCHOOL_YEAR'],raw['LEAID'],raw['ST_LEAID'],raw['ST'],raw['FIPST'])!=(ACADEMIC_YEAR,LEA,NATIVE_LEA,'CO','08'):raise ValueError('Complete exact same-year CCD district identity required')
 if lea:return LEA
 if type(raw['NCESSCH'])is not str or not re.fullmatch(LEA+r'\d{5}',raw['NCESSCH'])or type(raw['ST_SCHID'])is not str or not re.fullmatch(NATIVE_LEA+r'-\d{4}',raw['ST_SCHID']):raise ValueError('Exact full original NCES/native school identities required')
 return raw['NCESSCH']
def number(v):
 if v is None:return None
 if type(v)not in{str,int,float}:raise ValueError('Original source numbers cannot be booleans or coerced aliases')
 token=str(v).strip().replace(',','')
 if token in{'','*','- -','--','N/A'}or token.startswith('<'):return None
 if not re.fullmatch(r'-?\d+(?:\.\d+)?',token):raise ValueError('Unexpected original numeric token')
 f=float(token)
 if not math.isfinite(f):raise ValueError('Original finite numeric value required')
 return f
def count(v):
 f=number(v)
 if f is None:return None
 if f<0 or not f.is_integer():raise ValueError('Original exact nonnegative integer count required')
 return int(f)
def ccd_count(raw):
 if type(raw['STUDENT_COUNT'])is not str or type(raw['DMS_FLAG'])is not str:raise ValueError('Original typed CCD count/flag required')
 return int(raw['STUDENT_COUNT'])if raw['DMS_FLAG']=='Reported'and re.fullmatch(r'\d+',raw['STUDENT_COUNT'])else None
def offered_evidence(raw):
 flags={g:raw['G_'+g+'_OFFERED']for g in OFFER_GRADES};complete=raw['IGOFFERED']=='As reported'and raw['NOGRADES']=='No'and all(v in{'Yes','No'}for v in flags.values());offered=[g for g,v in flags.items()if v=='Yes'];low=any(g in['PK','KG']+[str(g)for g in range(1,9)]for g in offered);high=any(str(g)in offered for g in range(9,13));other=any(g in offered for g in['13','AE'])
 scope='uncertain'if not complete else'other'if other or not(low or high)else'mixed'if low and high else'HS'if high else'ES'
 return dict(flags=flags,complete_reported=complete,scope=scope,low=raw['GSLO'],high=raw['GSHI'],level=raw['LEVEL'],ungraded=raw['G_UG_OFFERED'],tested_offers=[str(g)for g in range(3,9)if flags[str(g)]=='Yes'])
def grade_evidence(entry):
 if entry is None:return dict(present=False,scope='missing',counts=None,positive_tested=False,explicit_zero_high=False,reconciled=False,k12=None,pk12=None,source_row=None)
 r=entry['raw'];native_identity(r);values={g:count(r[g])for g in GRADES};n=count(r['PK-12 Count']);reconciled=n is not None and all(v is not None for v in values.values())and sum(values.values())==n
 if n is not None and all(v is not None for v in values.values())and not reconciled:raise ValueError('Native own complete PK–12 enrollment does not reconcile')
 low=any(values[g]is not None and values[g]>0 for g in TESTED_GRADES);high=any(values[g]is not None and values[g]>0 for g in HIGH_GRADES);unknown=any(v is None for v in values.values());scope='uncertain'if unknown else'mixed'if low and high else'HS'if high else'ES'if low else'primary'
 return dict(present=True,scope=scope,counts=values,positive_tested=low,explicit_zero_high=all(values[g]==0 for g in HIGH_GRADES),reconciled=reconciled,k12=None if not reconciled else n-values['Pre-K'],pk12=n,source_row=entry['source_row'])
def income_evidence(entry,grades):
 if entry is None:return dict(present=False,denominator=None,eligible=None,published_fraction=None,percentage=None,usable=False,exclusion='No original same-year native K–12 income record',source_row=None)
 r=entry['raw'];native_identity(r);n=count(r['K-12 Count']);eligible=count(r['Free and Reduced Count']);fraction=number(r['% Free and Reduced']);free=count(r['Free Lunch']);reduced=count(r['Reduced Lunch']);paid=count(r['Paid Lunch'])
 if n is not None and eligible is not None and eligible>n:raise ValueError('Individual eligibility exceeds own K–12 denominator')
 if fraction is not None and not 0<=fraction<=1:raise ValueError('Original eligibility fraction outside0–1')
 if free is not None and reduced is not None and eligible is not None and free+reduced!=eligible:raise ValueError('Original individual free+reduced counts disagree')
 if all(v is not None for v in[n,free,reduced,paid])and free+reduced+paid!=n:raise ValueError('Original eligibility categories do not reconcile to own K–12 denominator')
 if n and eligible is not None and fraction is not None and abs(eligible/n-fraction)>.00051:raise ValueError('Published original three-decimal eligibility fraction does not reconcile')
 if grades['reconciled']and n is not None and n!=grades['k12']:raise ValueError('Same-year own income K–12 denominator differs from complete native enrolled grades')
 usable=n is not None and n>0 and fraction is not None;reason=None if usable else'Original same-year eligibility fraction or K–12 enrollment missing/suppressed'
 return dict(present=True,denominator=n,eligible=eligible,published_fraction=fraction,percentage=100*fraction if usable else None,usable=usable,exclusion=reason,source_row=entry['source_row'],free=free,reduced=reduced,paid=paid,published_fraction_rounding_preserved=True,prekindergarten_excluded=True)
def outcome_evidence(entry,subject):
 if entry is None:return dict(present=False,proficiency=None,valid_scores=None,proficient_count=None,published_percentage=None,source_usable=False,exclusion='No original whole-school CMAS All Grades subject row',source_row=None,ten_valid_scored_floor_certified=False)
 r=entry['raw'];native_identity(r)
 if(r['Level'],r['Grade'],r['Content'])!=('SCHOOL','All Grades',SUBJECTS[subject]):raise ValueError('Original whole-school regular CMAS population/subject changed')
 n=count(r['Number of Valid Scores']);met=count(r['Number Met or Exceeded Expectations']);pct=number(r['2025']);total=count(r['Number of Total Records']);no=count(r['Number of No Scores']);levelkeys=['Did Not Yet Meet','Partially Met','Approached','Met','Exceeded'];levels={k:count(r['Number '+k+' Expectations'])for k in levelkeys}
 if n is not None and total is not None and n>total:raise ValueError('Valid scores exceed original total registrations')
 if n is not None and no is not None and total is not None and n+no!=total:raise ValueError('Original valid+no-score totals do not reconcile')
 if met is not None and n is not None and met>n:raise ValueError('Proficient scores exceed valid scores')
 if pct is not None and not 0<=pct<=100:raise ValueError('Original proficiency percentage outside0–100')
 if n is not None and all(v is not None for v in levels.values())and sum(levels.values())!=n:raise ValueError('Original published performance levels do not sum to valid scores')
 if met is not None and levels['Met']is not None and levels['Exceeded']is not None and levels['Met']+levels['Exceeded']!=met:raise ValueError('Original met+exceeded levels differ')
 usable=n is not None and n>=MIN_VALID and met is not None and pct is not None
 if usable and abs(100*met/n-pct)>.051:raise ValueError('Original whole-school ratio fails one-decimal published rate check')
 return dict(present=True,proficiency=100*met/n if usable else None,valid_scores=n,proficient_count=met,published_percentage=pct,source_usable=usable,exclusion=None if usable else'Original whole-school valid/proficient counts or rate missing, bounded, masked or below16',source_row=entry['source_row'],raw_valid_scores=r['Number of Valid Scores'],raw_proficient_count=r['Number Met or Exceeded Expectations'],raw_published_percentage=r['2025'],total_records=total,no_scores=no,performance_levels=levels,ten_valid_scored_floor_certified=usable and n>=10,no_suppressed_grade_components_reconstructed=True)
def schema_fingerprint(inputs):return fingerprint({t:{k:v for k,v in inputs['tables'][t].items()if k not in{'records','omitted'}}for t in TABLES})
def identity_fingerprint(inputs):
 return fingerprint({t:[dict(source_row=e['source_row'],identity={k:e['raw'].get(k)for k in(['SCHOOL_YEAR','LEAID','ST_LEAID','NCESSCH','ST_SCHID']if t in{'directory','membership'}else['SCHOOL_YEAR','LEAID','ST_LEAID']if t in{'lea_directory','lea_membership'}else['Organization Code','District Code','School Code','Level','Content','Grade'])})for e in inputs['tables'][t]['records']]for t in TABLES})
def validate_raw_inputs(inputs):
 if type(inputs)is not dict or set(inputs)!={'tables','definitions','secondary'}or set(inputs['tables'])!=set(TABLES):raise ValueError('Complete exact original input sections required')
 if fingerprint(inputs)!=RAW_INPUT_SHA or schema_fingerprint(inputs)!=ORIGINAL_SCHEMA_SHA or fingerprint(inputs['definitions'])!=DEFINITION_INPUT_SHA or identity_fingerprint(inputs)!=ORIGINAL_IDENTITY_SHA:raise ValueError('Original full raw/schema/definitions/identity cells or inventories changed')
 for t in TABLES:
  section=inputs['tables'][t]
  if {k:v for k,v in section.items()if k not in{'records','omitted'}}!=ORIGINAL_METADATA[t]or len(section['records'])!=ORIGINAL_INVENTORIES[t]:raise ValueError('Complete original table metadata/inventory changed')
  if len({e['source_row']for e in section['records']})!=len(section['records'])or any(type(e['source_row'])is not int for e in section['records']):raise ValueError('Unique exact original row ordinals required')
  for e in section['records']:
   r=e['raw']
   if t in{'directory','membership','lea_directory','lea_membership'}:ccd_identity(r,lea=t in{'lea_directory','lea_membership'})
   else:native_identity(r)
   if t in{'grades','income','cmas','sat'}and({k:v for k,v in zip(section['header'],e['raw_cells'])if k is not None}!=r):raise ValueError('Complete original typed workbook cells differ from header fields')
def summarize(inputs):
 validate_raw_inputs(inputs);tables=inputs['tables'];dirs={ccd_identity(e['raw']):e for e in tables['directory']['records']};native_to_id={e['raw']['ST_SCHID']:k for k,e in dirs.items()};totals={};grade_rows=defaultdict(dict)
 if len(native_to_id)!=len(dirs):raise ValueError('Duplicate complete original native directory identity')
 for e in tables['membership']['records']:
  r=e['raw'];k=ccd_identity(r)
  if r['TOTAL_INDICATOR']=='Education Unit Total':
   if k in totals:raise ValueError('Duplicate original own membership total')
   totals[k]=e
  elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade'and r['RACE_ETHNICITY']==r['SEX']=='No Category Codes':
   if r['GRADE']in grade_rows[k]:raise ValueError('Duplicate original CCD enrolled-grade subtotal')
   grade_rows[k][r['GRADE']]=e
 native={}
 for t in['grades','income']:
  native[t]={}
  for e in tables[t]['records']:
   k=native_identity(e['raw'])
   if k in native[t]:raise ValueError('Duplicate exact native school identity')
   native[t][k]=e
 selected=defaultdict(dict);all_cmas=defaultdict(list);all_sat=defaultdict(list);district_cmas=[];district_sat=[]
 for t,buckets,aggregate in [('cmas',all_cmas,district_cmas),('sat',all_sat,district_sat)]:
  for e in tables[t]['records']:
   r=e['raw'];k=native_identity(r)
   if r['Level']=='DISTRICT':aggregate.append(e['source_row']);continue
   if r['Level']!='SCHOOL':raise ValueError('Unexpected original Denver assessment level')
   buckets[k].append(e['source_row'])
   if t=='cmas'and r['Grade']=='All Grades'and r['Content']in SUBJECTS.values():
    sub=next(s for s,c in SUBJECTS.items()if c==r['Content'])
    if sub in selected[k]:raise ValueError('Duplicate original whole-school CMAS subject')
    selected[k][sub]=e
 links=[];profiles=[];members={s:[]for s in['math','reading','combined']};scope=Counter();charters=Counter();types_=Counter();missing_native=[];missing_income=[];differences=[];outside_native=[]
 for key,e in sorted(dirs.items()):
  r=e['raw'];nk=r['ST_SCHID'];active=r['UPDATED_STATUS']in OPERATIONAL;off=offered_evidence(r);g=grade_evidence(native['grades'].get(nk));inc=income_evidence(native['income'].get(nk),g);total=totals.get(key);N=ccd_count(total['raw'])if total else None;ug=ccd_count(grade_rows[key]['Ungraded']['raw'])if'Ungraded'in grade_rows[key]else None
  offered_lower=off['complete_reported']and off['scope']=='ES'and bool(off['tested_offers'])and re.fullmatch(r'0[1-8]',off['high'])is not None and(off['ungraded']=='No'or ug==0)
  eligible=bool(active and offered_lower and g['scope']=='ES'and g['positive_tested']and g['explicit_zero_high']and g['reconciled'])
  reason=None if eligible else'Nonoperational CCD status'if not active else'No exact native enrollment'if not g['present']else'Primary-only native enrolled grades'if g['scope']=='primary'else'High/mixed/uncertain offered or enrolled grade configuration'
  subjects={s:outcome_evidence(selected[nk].get(s),s)for s in SUBJECTS}
  for s,p in subjects.items():p.update(usable=eligible and inc['usable']and p['source_usable'],applicable_to_lower=eligible)
  paired=all(subjects[s]['usable']for s in SUBJECTS);subjectpoints=all(subjects[s]['source_usable']for s in SUBJECTS);subjects['combined']=dict(proficiency=(subjects['math']['proficiency']+subjects['reading']['proficiency'])/2 if subjectpoints else None,usable=paired,valid_scores=None,valid_score_components={s:subjects[s]['valid_scores']for s in SUBJECTS},ten_valid_scored_floor_certified=paired and all(subjects[s]['ten_valid_scored_floor_certified']for s in SUBJECTS),no_invented_paired_count=True)
  if eligible:
   profiles.append(key);charters[r['CHARTER_TEXT']]+=1;types_[r['SCH_TYPE_TEXT']]+=1
   for s,p in subjects.items():
    if p['usable']:members[s].append(key)
  if active:scope[g['scope']]+=1
  if active and not g['present']:missing_native.append(key)
  if active and not inc['present']:missing_income.append(key)
  if N is not None and g['pk12']is not None and N!=g['pk12']:differences.append(dict(school_id=key,ccd_membership=N,native_pk12=g['pk12'],difference=N-g['pk12']))
  links.append(dict(school_id=key,ncessch=key,native_school_id=nk,name=r['SCH_NAME'],directory_source_row=e['source_row'],operational=active,ccd_flags=dict(status=r['UPDATED_STATUS'],status_text=r['UPDATED_STATUS_TEXT'],charter=r['CHARTER_TEXT'],school_type=r['SCH_TYPE_TEXT']),offered=off,native_enrollment=g,ccd_membership=dict(reported_total=N,total_source_row=None if total is None else total['source_row'],grade_source_rows={g:e['source_row']for g,e in grade_rows[key].items()},reported_grade_counts={g:ccd_count(e['raw'])for g,e in grade_rows[key].items()}),income=inc,source_profile_eligible=eligible,population_exclusion=reason,source_attribution_hold=None,subjects=subjects,all_original_CMAS_source_rows=all_cmas[nk],all_original_SAT_source_rows=all_sat[nk],admissions=None,program=None,virtual_provider=None,geometry=None))
 for nk in sorted(set(native['grades'])|set(native['income'])|set(all_cmas)|set(all_sat)):
  if nk not in native_to_id:outside_native.append(dict(native_school_id=nk,native_grade_source_row=None if nk not in native['grades']else native['grades'][nk]['source_row'],native_income_source_row=None if nk not in native['income']else native['income'][nk]['source_row'],cmas_source_rows=all_cmas[nk],sat_source_rows=all_sat[nk],source_profile_eligible=False,exclusion='No exact complete original CCD identity'))
 lea=next(e for e in tables['lea_membership']['records']if e['raw']['TOTAL_INDICATOR']=='Education Unit Total');lea_n=ccd_count(lea['raw']);known=sum(l['ccd_membership']['reported_total']for l in links if l['operational']and l['ccd_membership']['reported_total']is not None);native_n=sum(l['native_enrollment']['pk12']for l in links if l['operational']and l['native_enrollment']['pk12']is not None)
 cohorts=dict(profile_ids=profiles,subjects={s:dict(member_ids=ids,usable=len(ids),eligible_charters=sum(l['ccd_flags']['charter']=='Yes'for l in links if l['school_id']in ids),all_members_have_verified_valid_counts=True,prospective_sampling_intervals_supported=bool(ids)and all(l['subjects'][s]['ten_valid_scored_floor_certified']for l in links if l['school_id']in ids))for s,ids in members.items()})
 coverage=dict(directory_records=len(links),operational_records=sum(l['operational']for l in links),status=dict(Counter(l['ccd_flags']['status_text']for l in links)),exact_native_matches=sum(l['native_enrollment']['present']for l in links),native_enrolled_scopes=dict(scope),pure_lower_profiles=len(profiles),lower_charters=dict(charters),lower_school_types=dict(types_),usable={s:len(ids)for s,ids in members.items()},operational_without_native_ids=missing_native,operational_without_income_ids=missing_income,outside_native_ids=[l['native_school_id']for l in outside_native],native_CMAS_school_ids=sum(bool(v)for v in all_cmas.values()),native_SAT_school_ids=sum(bool(v)for v in all_sat.values()),grade_income_denominator_reconciliation=True,CCD_native_PK12_mismatches=differences,district_reported_enrollment=lea_n,known_operational_CCD_membership=known,district_minus_known_CCD_membership=None if lea_n is None else lea_n-known,known_native_operational_PK12=native_n,district_minus_known_native=None if lea_n is None else lea_n-native_n,unassigned_native_membership_difference=True,original_needed_records=sum(len(tables[t]['records'])for t in TABLES),original_needed_typed_cells=sum(sum(len(e.get('raw_cells',e['raw']))for e in tables[t]['records'])for t in TABLES),complete_target_original_records=sum(tables[t]['complete_target_records']for t in TABLES),complete_target_typed_cells=sum(tables[t]['complete_target_cells']for t in TABLES),omitted_original_records=sum(len(tables[t]['omitted'])for t in TABLES),source_approvals_false=True,canonical_integration_pending=True,model_results=0)
 return dict(roster_links=links,outside_native_profiles=outside_native,district_native_source_rows=dict(cmas=district_cmas,sat=district_sat),cohorts=cohorts,coverage=coverage)
def base_document(inputs):return dict(schema_version=1,state='CO',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='source_only_pending_numerical_review',scope='source_and_cohort_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,raw_inputs=inputs,raw_input_sha256=RAW_INPUT_SHA,original_schema_sha256=ORIGINAL_SCHEMA_SHA,original_definition_sha256=DEFINITION_INPUT_SHA,original_identity_sha256=ORIGINAL_IDENTITY_SHA,source_policy_sha256=POLICY_SHA,source_runtime_sha256=RUNTIME_CONTRACT_SHA,**summarize(inputs))
def validate(document):
 require_current_originals()
 if type(document)is not dict:raise ValueError('Complete original source document required')
 expected=base_document(document['raw_inputs'])
 if fingerprint(document)!=fingerprint(expected):raise ValueError('Original source derived identity/cohort/rates/counts/metadata changed')
 return dict(profiles=len(expected['cohorts']['profile_ids']),subjects={s:c['usable']for s,c in expected['cohorts']['subjects'].items()},approved_for_source=False,approved_for_modeling=False)

def original_pin(path,url):return dict(path=str(path.relative_to(ROOT)),url=url,bytes=path.stat().st_size,sha256=source_sha(path))
def cell(v):return dict(original_type=type(v).__name__,value=v.isoformat())if isinstance(v,(datetime.datetime,datetime.date,datetime.time))else v
def extract_raw_inputs():
 require_current_originals()
 sources={};tables={};full={}
 for table,filename in [('directory','ccd_sch_029_2425_w_1a_073025.zip'),('membership','ccd_sch_052_2425_l_1a_073025.zip'),('lea_directory','ccd_lea_029_2425_w_1a_073025.zip'),('lea_membership','ccd_lea_052_2425_l_1a_073025.zip')]:
  p=ROOT/'data/raw'/filename;key='ccd_'+table;sources[key]=original_pin(p,'https://nces.ed.gov/ccd/Data/zip/'+filename)
  with zipfile.ZipFile(p)as z:member=next(n for n in z.namelist()if n.endswith('.csv'))
  proc=subprocess.Popen(['unzip','-p',str(p),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig');reader=csv.DictReader(proc.stdout);rows=[]
  for number,r in enumerate(reader,2):
   if r.get('LEAID')==LEA or r.get('ST_LEAID')==NATIVE_LEA:rows.append(dict(source_row=number,raw=r))
  assert proc.wait()==0;proc.stdout.close();full[table]=rows
  selected=[];omitted=[]
  for e in rows:
   r=e['raw'];keep=table not in{'membership','lea_membership'}or r['TOTAL_INDICATOR']=='Education Unit Total'or(r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade'and r['RACE_ETHNICITY']==r['SEX']=='No Category Codes')
   if keep:selected.append(e)
   else:omitted.append(dict(source_row=e['source_row'],identity={k:r[k]for k in['SCHOOL_YEAR','LEAID','ST_LEAID']+(['NCESSCH','ST_SCHID']if table=='membership'else[])},population={k:r[k]for k in['GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG']},raw_sha256=fingerprint(r)))
  tables[table]=dict(source_id=key,member=member,header=reader.fieldnames,records=selected,complete_target_records=len(rows),complete_target_cells=sum(len(e['raw'])for e in rows),complete_target_sha256=fingerprint(rows),omitted=omitted,retained_records=len(selected))

 urls={
  'grades':('grades2025.xlsx','7efacffc-8335-4735-9b12-fee840351810',3,None),
  'income':('frl2025.xlsx','edf7f72b-6728-4b48-a3aa-ae75ab2ad968',3,None),
  'cmas':('cmas2025.xlsx','5c130960-c90c-444a-98dc-41b35c11431b',18,None),
  'sat':('sat2025.xlsx','37066be1-57a4-40f4-8235-3c1b10cb0e75',17,16)}
 definitions={}
 for table,(filename,uuid,header,upper)in urls.items():
  p=ROOT/'data/raw/colorado'/filename;key='co_'+table;sources[key]=original_pin(p,'https://ed.cde.state.co.us/fs/resource-manager/view/'+uuid);w=openpyxl.load_workbook(p,read_only=True,data_only=True);s=w.active;allrows=[[cell(v)for v in row]for row in s.values];rawheader=allrows[header-1];normalized=[' '.join(str(v).split())if v is not None else None for v in rawheader]
  if upper:normalized=[v or(' '.join(str(allrows[upper-1][i]).split())if allrows[upper-1][i]is not None else None)for i,v in enumerate(normalized)]
  assert len(set(v for v in normalized if v is not None))==sum(v is not None for v in normalized)
  rows=[]
  for number,row in enumerate(allrows[header:],header+1):
   r={k:v for k,v in zip(normalized,row)if k is not None};district=r.get('Organization Code',r.get('District Code'))
   if district=='0880':rows.append(dict(source_row=number,raw=r,raw_cells=row))
  full[table]=rows;tables[table]=dict(source_id=key,worksheet=s.title,header_source_row=header,upper_header_source_row=upper,raw_header=rawheader,upper_raw_header=None if upper is None else allrows[upper-1],header=normalized,records=rows,complete_target_records=len(rows),complete_target_cells=sum(len(e['raw_cells'])for e in rows),complete_target_sha256=fingerprint(rows),omitted=[],retained_records=len(rows))
  definitions[key]=dict(source_id=key,worksheet=s.title,initial_rows=[dict(source_row=i,raw=row)for i,row in enumerate(allrows[:header],1)],footer_rows=[dict(source_row=i,raw=row)for i,row in enumerate(allrows,1)if isinstance(row[0],str)and row[0].lower()=='total'])
  w.close()
 for key,filename,uuid in [('co_cmas_layout','cmas2025-layout.pdf','f6b76141-39d7-4787-b7e9-5a5777952cb7'),('co_sat_layout','sat2025-layout.pdf','7bd1ffa6-490b-44b9-9dee-933d32a9c0c7')]:
  p=ROOT/'data/raw/colorado'/filename;sources[key]=original_pin(p,'https://ed.cde.state.co.us/fs/resource-manager/view/'+uuid);definitions[key]=dict(source_id=key,pages=[dict(page_number=i,text=p.extract_text()or'')for i,p in enumerate(PdfReader(p).pages,1)])
 for key,path,url in [('co_income_archive',ROOT/'data/raw/colorado/income-page.html','https://ed.cde.state.co.us/cdereval/pupilmembership-statistics/data-insights-resources-archives'),('co_assessment_page',ROOT/'data/raw/colorado/assessment-page.html','https://ed.cde.state.co.us/assessment/cmas-dataandresults-2025'),('co_eligibility',ROOT/SOURCES['co_eligibility']['path'],'https://ed.cde.state.co.us/nutrition/manage-program-operations/determine-program-eligibility')]:
  sources[key]=original_pin(path,url);definitions[key]=dict(source_id=key,original_html=path.read_text())
 for key,filename in [('ccd_notes','SY_2024-25_CCD_Final_2a_Data_Notes.xlsx'),('ccd_membership_layout','SY_2024-25_SCH_Membership_Companion_2026-005d.xlsx'),('ccd_directory_layout','SY_2024-25_SCH_Directory_Companion_2026-005d.xlsx')]:
  p=ROOT/'data/raw'/filename;sources[key]=original_pin(p,'https://nces.ed.gov/ccd/xls/'+filename);w=openpyxl.load_workbook(p,read_only=True,data_only=True);definitions[key]=dict(source_id=key,worksheets={s.title:dict(worksheet=s.title,records=[dict(source_row=i,raw=[cell(v)for v in row])for i,row in enumerate(s.values,1)])for s in w});w.close()
 secondary=ROOT/'data/source/colorado.json';sources['co_secondary']=original_pin(secondary,'https://ed.cde.state.co.us/assessment/cmas-dataandresults-2025');payload=json.loads(secondary.read_text());snapshot={k:[r for r in payload[k]if r['school_id'].startswith('0880')]for k in ['profiles','incomes','assessments']}
 assert(payload['state'],payload['year'],payload['academic_year'])==('CO',2025,'2024-2025')
 for table,part in [('grades','profiles'),('income','incomes')]:
  actual={e['source_row']:e['raw']for e in tables[table]['records']};assert len(snapshot[part])==len(actual)
  for e in snapshot[part]:assert e['raw']==actual[e['source_row']]
 actual={t:{e['source_row']:e['raw']for e in tables[t]['records']}for t in ['cmas','sat']}
 for e in snapshot['assessments']:assert e['raw']==actual['cmas'if e['level']=='ES'else'sat'][e['source_row']]
 obj=dict(tables=tables,definitions=definitions,secondary=dict(source_id='co_secondary',snapshot=snapshot,snapshot_sha256=fingerprint(snapshot),only_original_fields_no_source_model_authority=True))

 if sources!=SOURCES:raise ValueError("Complete current original pin manifest changed")
 return obj

def extract(output=OUTPUT):
 inputs=extract_raw_inputs();document=base_document(inputs);result=validate(document)
 Path(output).write_text(json.dumps(document,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n');return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args()
 print(json.dumps(extract(args.output)if args.extract else validate(json.loads(args.output.read_text())),sort_keys=True))

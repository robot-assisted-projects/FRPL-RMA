"""Replay Katy ISD's 2024–25 original-source/cohort audit; never fit or import."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/katy-district-audit.json'
LEA = '4825170'
NATIVE_LEA = 'TX-101914'
DISTRICT = '101914'
YEAR = '2024-2025'
OPERATIONAL = {'1', '3', '4', '5', '8'}
GRADES = ['CPNTGEEC', 'CPNTGPKC', 'CPNTGKNC'] + ['CPNTG%02dC' % g for g in range(1, 13)]
FIELDS = {s: ['CDA38A%s0E025D' % letter, 'CDA38A%s0E225N' % letter,
              'CDA38A%s0E225R' % letter] for s, letter in [('math', 'M'), ('reading', 'R')]}
STATE_EXTRACT_SHA = 'bb8a0882cc64fd569168bed05853cd9070d4ec4e0940fa27a2c6a029e1d78aac'
RAW_INPUT_SHA = '608d0451819c7938658f8eead8bc8684d5c0b3f77c838bc9c63a044960148b7d'
ORIGINAL_SCHEMA_SHA = 'ae2b97bd762a4771639c9c5b5b45aa2c11c39578450e9d153919f064dfd28441'
DEFINITION_INPUT_SHA = '41c83100bb0930615830e19b012bf223610e82375602b586dd1d485980605fdc'
MANUAL_PAGES = [173, 177, 204]
SOURCES = {'assessment': {'bytes': 3806149, 'path': 'data/raw/tx_assessment_2025.csv', 'sha256': 'dcc2e16290ba99a47ace88e2bf3bafc60cb409f6d27d792fd7659df1c74cdf0d', 'url': 'https://rptsvr1.tea.texas.gov/cgi/sas/broker/?_service=marykay&_program=perfrept.perfmast.sas&_debug=0&ccyy=2025&tapr=all_c&sumlev=C&level=Campus&id=&prgopt=reports%2Ftapr%2Fdd%2Fdd_tapr_step_7.sas&datafmt=csv&dsname=STAAR_GR38&key=38AR0E2%7C38AR0E0&key=38AM0E2%7C38AM0E0&var_type=N&var_type=D&var_type=R'}, 'ccd_state_notes': {'bytes': 210984, 'path': 'data/raw/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx', 'sha256': '6476b6b28b700389e261b87377d9cd249935503d53b5919fe1b7ef8b1052d1a7', 'url': 'https://nces.ed.gov/ccd/xls/SY_2024-25_CCD_Final_2a_Data_Notes.xlsx'}, 'dictionary': {'bytes': 270385, 'path': 'data/raw/tx_dictionary_2025.html', 'sha256': '100f1f3d128bbe8a6be2a00e327b907dd15d5e2acc0e680c526bf9b59b4caf66', 'url': 'https://rptsvr1.tea.texas.gov/cgi/sas/broker?_service=marykay&_program=perfrept.perfmast.sas&_debug=0&ccyy=2025&sumlev=C&dsname=STAAR_GR38&dd=performance&asvab=&prgopt=reports%2Ftapr%2Fdd%2Fdd_tapr_dictionary.sas'}, 'directory': {'bytes': 13352819, 'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip'}, 'glossary': {'bytes': 834427, 'path': 'data/raw/tx_glossary_2025.pdf', 'sha256': '846810954d479a13467d9e4add3b0ed626247bd48ca9b677ff8a5ec11aedd416', 'url': 'https://tea.texas.gov/school-and-district-leaders/accountability/academic-accountability/performance-reporting/2024-25-comprehensive-tapr-glossary-0.pdf'}, 'income-extension': {'bytes': 151080, 'path': 'data/raw/tx_income_extension_2025.html', 'sha256': '9f2137a25a1e3bc2006b0b3dfee413bc38b1d6928c155574dd04934bd99a04ef', 'url': 'https://tea.texas.gov/taa-letters/school-year-2024-2025-income-eligibility-verification-forms-extension'}, 'income-guide': {'bytes': 4673648, 'path': 'data/raw/tx_income_reporting_2025.pdf', 'sha256': '05de25f2c0fcc21368d3810ff3124d2866d86289fcc7b5548232bcccc262ac3a', 'url': 'https://www.texasstudentdatasystem.org/sites/texasstudentdatasystem.org/files/TEDS_Data_Submission_Requirements_Student_Identification_and_Demographics_Domain.pdf'}, 'lea_directory': {'bytes': 2830266, 'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip'}, 'lea_membership': {'bytes': 68497561, 'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip'}, 'masking': {'bytes': 55298, 'path': 'data/raw/tx_masking_2025.html', 'sha256': '7b6e5840645656bf3c0d977431e7f9fcd6ea984bb1734b6387471f8ad4851de8', 'url': 'https://rptsvr1.tea.texas.gov/perfreport/tapr/2025/masking.html'}, 'membership': {'bytes': 212696691, 'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip'}, 'ref': {'bytes': 827863, 'path': 'data/raw/tx_ref_2025.csv', 'sha256': '8c75df541a408dfb0f49161aef8c0c0229ff6f5e73765bebf6ce5ef070cdac72', 'url': 'https://rptsvr1.tea.texas.gov/cgi/sas/broker/?_service=marykay&_program=perfrept.perfmast.sas&_debug=0&ccyy=2025&tapr=all_c&sumlev=C&level=Campus&id=&prgopt=reports%2Ftapr%2Fdd%2Fdd_tapr_step_7.sas&datafmt=csv&dsname=REF&key=GRDSPAN&key=GRDTYPE&key=COUNTY%7CCNTYNAME&key=CFLALTED'}, 'stud': {'bytes': 3015524, 'path': 'data/raw/tx_stud_2025.csv', 'sha256': '24e2b867023b8c979d0f7f5d662db4d1eeb3eca00f0413b12bd059790eb7b6f6', 'url': 'https://rptsvr1.tea.texas.gov/cgi/sas/broker/?_service=marykay&_program=perfrept.perfmast.sas&_debug=0&ccyy=2025&tapr=all_c&sumlev=C&level=Campus&id=&prgopt=reports%2Ftapr%2Fdd%2Fdd_tapr_step_7.sas&datafmt=csv&dsname=STUD&key=ETALL%7CNTALL&key=NTECO%7CNTNED%7CNT504%7CNTLEP%7CNTDSL%7CNTFOS%7CNTHOM%7CNTIMM%7CNTMIG%7CNTTT1%7CNTMLC%7CNTRSK%7CNTBIL&key=ETECO%7CETNED%7CET504%7CETLEP%7CETDIS%7CETDSL%7CETFOS%7CETHOM%7CETIMM%7CETMIG%7CETTT1%7CETMLC%7CETRSK&key=NTGEEC%7CNTGEEP%7CNTGPKC%7CNTGPKP%7CNTGP3C%7CNTGP3P%7CNTGP4C%7CNTGP4P%7CNTGKNC%7CNTGKNP%7CNTG01C%7CNTG01P%7CNTG02C%7CNTG02P%7CNTG03C%7CNTG03P%7CNTG04C%7CNTG04P%7CNTG05C%7CNTG05P%7CNTG06C%7CNTG06P%7CNTG07C%7CNTG07P%7CNTG08C%7CNTG08P%7CNTG09C%7CNTG09P%7CNTG10C%7CNTG10P%7CNTG11C%7CNTG11P%7CNTG12C%7CNTG12P&var_type=N&var_type=D&var_type=R'}, 'accountability-manual': {'path': 'data/raw/tx_accountability_manual_2025.pdf', 'url': 'https://tea.texas.gov/texas-schools/accountability/academic-accountability/performance-reporting/2025-accountability-manual-full.pdf', 'bytes': 7524901, 'sha256': '8734f5ce994c9e255ff34da3a8ddf3b2430a17e3d7f18cbff06bba85ae6b649f'}, 'performance-listing': {'path': 'data/raw/tx_performance_participation_listing_2025.pdf', 'url': 'https://sboe.texas.gov/texas-schools/accountability/academic-accountability/performance-reporting/interpreting-staar-performance-participation-student-list-2025.pdf', 'bytes': 319035, 'sha256': '1c1e59441f6733b6f77b70946deeed401c59714a6cbdc4e8609d15a49741b6b1'}}
POLICY = {'identity': 'Exact original2024–25 CCD NCES LEA4825170/ST_LEAID TX-101914 and complete CCD ST_SCHID TX-101914-101914sss crosswalk to the already published full nine-digit TAPR CAMPUS101914sss with original six-digit DISTRICT101914. Names, addresses, suffix padding, numeric coercion and similarly named districts never establish school ownership.', 'population': 'Use complete native 2025 fall enrolled counts EE, PK, K, 1–12 reconciled to CPNTALLC. No positive grades9–12, plus positive grades3–8, defines the prospective grade-school population. Retain primary-only, high-only, mixed, unknown, zero and absent records separately. Do not select by CCD level, reference GRDTYPE/GRDSPAN, school type, charter status or residuals.', 'income': 'Individual October25,2024 PEIMS fall economic status: own CPNTECOC economically disadvantaged count divided by the same campus CPNTALLC enrollment denominator, including free/reduced meal eligibility or other public assistance, codes01/02/99. CPNTALLC includes all enrolled EE–12 pupils; CPNTECOC+CPNTNEDC and native tenth-percent CPNTECOP display must reconcile. CPETALLC membership remains a separate administrative measure and never supplies this denominator. This broader state-specific proxy is neither uniform FRPL nor household income and does not exactly describe tested pupils.', 'income_limits': 'CEP requires individual direct certification and annual local income surveys; universal meals do not classify all children. Provision2 can retain base-year eligibility for continuously enrolled students. Missing surveys may be00; undercount unknown. Jan16,2025 resubmission extension requires enrolled/eligible October25,2024; not another-year backfill.', 'assessment': 'Exact native 2024–25 All Students TAPR enrolled-grades3–8 Math/Reading Including EOC, At Meets Grade Level or Above: the original whole-percent R cells establish prospective outcomes. Native #Tests and #Meets-or-above remain unverified raw evidence. Accountability subset requires same district/campus on fall snapshot and testing date. STAAR with/without accommodations, Spanish STAAR, Alternate2 and corresponding AlgebraI/EnglishI–II EOC are included as documented. Separate TPRS all-testers, both-subject passing and participation measures are not used.', 'counts': 'Native reported #Tests and #Meets-or-above remain complete unverified raw evidence. Where all are available, their arithmetic can be reconciled with the original whole-percent display, but it does not certify valid-score denominators or select point-rate membership. Exact 2025 N/NAAR and M/medical performance-status mapping remains unresolved under the existing hold; no failed investigation is repeated. All valid-score counts, sampling variances and intervals remain null/unavailable, and the ten-valid-scored floor stays uncertified.', 'suppression': 'Empty, bullet/asterisk and -1/-2/-3 are unavailable, never zero. Never reconstruct a masked rate from visible counts. Native source masks small denominators1–4, while the ten-valid-scored floor remains uncertified. This explicit source-only published-rate contract selects only unmasked original R cells and never imposes a reported-count screen. An unsuppressed published zero remains zero.', 'combined': 'Equal mean of eligible original published Math and ELA whole-percent subject rates; not a count-derived ratio or the native fraction passing both. Never average grades or weight by enrollment.', 'approval': 'Source/cohort audit only. Source and modeling approval false; no model, residual, variance, interval, canonical import, served comparison or location crosswalk. Separate numerical audit and canonical/browser integration remain required. High/mixed observations are retained but their assessment populations remain unaudited for district models.', 'unmatched_native': 'Exact operational ARTHUR MILLER CAREER CENTER101914004/NCES482517008625 and PROJECT TYKE101914135/NCES482517008629 are absent all three original REF/STUD/STAAR_GR38 tables. Retain complete original directory/offered grades/CCD membership separately; native enrollment/income/outcomes remain missing. Their CCD membership0 and13 never become substitute native enrollment, income or tested denominators. Two original Future campuses101914149/101914150 also remain separate and unjoined; missingness is never zero.', 'raw_compaction': 'Retain all complete needed original district directory/total/grade/native REF/STUD/performance rows and whole primary definition excerpts. Preserve every omitted CCD demographic row ordinal and full identity/population projection, typed-cell counts and the complete original raw-with-ordinal digest. All seven original district tables and whole source archives remain independently auditable.', 'source_freshness': 'Every replay checks immutable current original byte/size pins and the complete current secondary Texas source even when a cached snapshot is supplied. Offline replay hashes local original files but never reextracts, fits, imports or publishes. Public fingerprint or policy replacement cannot self-authorize altered original evidence.'}
PLANNING = {'source': 'data/source/district-comparison-candidates.json', 'operational_roster': 79, 'enrollment': 96111, 'potential_ES': 65, 'potential_HS': 11, 'explanation': 'Discovery only; original Katy CCD identities/membership replay independently. Planning never selects income, achievement or source/model approval.'}



NATIVE_REQUIRED_LABELS = {'ref': {'CAMPUS': '9 Digit Campus Number', 'DISTRICT': '6 Digit County District Number', 'GRDTYPE': 'Campus Type (E - Elementary, M - Middle, S - High, B - Elementary/Secondary)', 'GRDSPAN': 'Grade Span (Total Enrollment)'}, 'stud': {'CAMPUS': '9 Digit Campus Number', 'DISTRICT': '6 Digit County District Number', 'CPNTALLC': 'Campus 2025 Student Enrollment: All Students Count', 'CPNTECOC': 'Campus 2025 Student Enrollment: Economically Disadvantaged Count', 'CPNTNEDC': 'Campus 2025 Student Enrollment: Non-Educationally Disadv Count', 'CPNTECOP': 'Campus 2025 Student Enrollment: Economically Disadvantaged Percent', 'CPNTGEEC': 'Campus 2025 Student Enrollment: Early Childhood Education Count', 'CPNTGPKC': 'Campus 2025 Student Enrollment: Pre-Kindergarten Count', 'CPNTGKNC': 'Campus 2025 Student Enrollment: Kindergarten Count', 'CPNTG01C': 'Campus 2025 Student Enrollment: Grade 1 Count', 'CPNTG02C': 'Campus 2025 Student Enrollment: Grade 2 Count', 'CPNTG03C': 'Campus 2025 Student Enrollment: Grade 3 Count', 'CPNTG04C': 'Campus 2025 Student Enrollment: Grade 4 Count', 'CPNTG05C': 'Campus 2025 Student Enrollment: Grade 5 Count', 'CPNTG06C': 'Campus 2025 Student Enrollment: Grade 6 Count', 'CPNTG07C': 'Campus 2025 Student Enrollment: Grade 7 Count', 'CPNTG08C': 'Campus 2025 Student Enrollment: Grade 8 Count', 'CPNTG09C': 'Campus 2025 Student Enrollment: Grade 9 Count', 'CPNTG10C': 'Campus 2025 Student Enrollment: Grade 10 Count', 'CPNTG11C': 'Campus 2025 Student Enrollment: Grade 11 Count', 'CPNTG12C': 'Campus 2025 Student Enrollment: Grade 12 Count'}, 'assessment': {'CAMPUS': '9 Digit Campus Number', 'DISTRICT': '6 Digit County District Number', 'CDA38AM0E025D': 'STAAR Performance, Math Including EOC (Grade 3-8), SY 2024-25, All Students, # of Tests', 'CDA38AM0E225N': 'STAAR Performance, Math Including EOC (Grade 3-8), SY 2024-25, All Students, # At Meets GL Standard or Above', 'CDA38AM0E225R': 'STAAR Performance, Math Including EOC (Grade 3-8), SY 2024-25, All Students, % At Meets GL Standard or Above', 'CDA38AR0E025D': 'STAAR Performance, Reading Including EOC (Grade 3-8), SY 2024-25, All Students, # of Tests', 'CDA38AR0E225N': 'STAAR Performance, Reading Including EOC (Grade 3-8), SY 2024-25, All Students, # At Meets GL Standard or Above', 'CDA38AR0E225R': 'STAAR Performance, Reading Including EOC (Grade 3-8), SY 2024-25, All Students, % At Meets GL Standard or Above'}}
EXPECTED_NATIVE_GAPS = {'101914004': '482517008625', '101914135': '482517008629'}
POLICY_SHA = 'c2ef8b9598d2e6eebf7ecb905346a356e684de3064827dbc12e73e562a7dbbdb'
RUNTIME_CONTRACT_SHA = 'c85b0fc675b821fd2e44ffeef5360676957340d5e99a4d5f9d381298c15b2832'
ORIGINAL_IDENTITY_SHA = 'e1aad88a42c240ad7e651b33290ef648979c2726b87b0b18136b04bbef2b3087'


ORIGINAL_METADATA = {'directory': 'f68924760390f8e94514d57461086ed460c9cf8beb74257a04917e0ac42589e6', 'membership': '9a77dcda7ac5fcab18c8d942e9de4a86b2b1f96831b6cb26507c1ccd67d5c306', 'lea_directory': '9a26c257086ce04ee9aa5d185df5c5318a51a581a5015c2e8ed071fec971d7de', 'lea_membership': 'ea9ef1578385be0d6ce0a7d7310a6052eb78873fba512579a8484ab1b9460077', 'ref': '3f9b7c9ed4f98876b3d5a18537fe31d66ee839068f54ca658500cd163674dbed', 'stud': 'e06d117f2729286523597b7178db5a0132596483ee7cfeb14e0787ce399d2539', 'assessment': '1921099ad5aa93ce4606bca6dd815c97a48a1725a6d9811cd2cc373da80019ae'}
ORIGINAL_INVENTORIES = {'directory': 81, 'membership': 586, 'lea_directory': 1, 'lea_membership': 16, 'ref': 77, 'stud': 77, 'assessment': 77}

def runtime_contract():
    return dict(lea=LEA,native_lea=NATIVE_LEA,district=DISTRICT,year=YEAR,operational=sorted(OPERATIONAL),
        grades=GRADES,fields=FIELDS,manual_pages=MANUAL_PAGES,policy=POLICY,sources=SOURCES,
        planning=PLANNING,unmatched_native=EXPECTED_NATIVE_GAPS,state_extract_sha256=STATE_EXTRACT_SHA,
        native_required_labels=NATIVE_REQUIRED_LABELS,raw_fingerprint=RAW_INPUT_SHA,
        schema_fingerprint=ORIGINAL_SCHEMA_SHA,definition_fingerprint=DEFINITION_INPUT_SHA,
        identity_fingerprint=ORIGINAL_IDENTITY_SHA,metadata_digests=ORIGINAL_METADATA,
        inventories=ORIGINAL_INVENTORIES)


def require_runtime_contract():
    if (POLICY_SHA!='c2ef8b9598d2e6eebf7ecb905346a356e684de3064827dbc12e73e562a7dbbdb' or RUNTIME_CONTRACT_SHA!='c85b0fc675b821fd2e44ffeef5360676957340d5e99a4d5f9d381298c15b2832'
        or fingerprint(POLICY)!='c2ef8b9598d2e6eebf7ecb905346a356e684de3064827dbc12e73e562a7dbbdb' or fingerprint(runtime_contract())!='c85b0fc675b821fd2e44ffeef5360676957340d5e99a4d5f9d381298c15b2832'):
        raise ValueError('Frozen current Katy source policy/identity/year/field/status/unmatched contract changed')


def original_identity_fingerprint(inputs):
    return fingerprint({table:[dict(source_row=e['source_row'],identity=
        [e['raw']['SCHOOL_YEAR'],e['raw']['LEAID'],e['raw']['ST_LEAID'],e['raw'].get('NCESSCH'),e['raw'].get('ST_SCHID')]
        if table in {'directory','membership','lea_directory','lea_membership'} else [e['raw']['DISTRICT'],e['raw']['CAMPUS']])
        for e in inputs[table]['records']] for table in ['directory','membership','lea_directory','lea_membership','ref','stud','assessment']})


def validate_definition_references(definitions):
    expected={'glossary':[1,2,3,5,6,28,29],'income-guide':[36,37,38,39,40],
        'accountability-manual':[173,177,204],'performance-listing':[4,6,8]}
    if set(definitions)!=set(expected)|{'ccd_state_notes','dictionary','masking','income-extension'}:
        raise ValueError('Complete original primary definition collections required')
    for key,pages in expected.items():
        section=definitions[key]
        if section.get('source_id')!=key or type(section.get('pages')) is not list or len(section['pages'])!=len(pages):
            raise ValueError('Original primary PDF source/page collection changed')
        for entry,page in zip(section['pages'],pages):
            if type(entry.get('pdf_page')) is not int or entry['pdf_page']!=page or type(entry.get('text')) is not str or not entry['text']:
                raise ValueError('Original PDF page references require strict integers and complete original text')
    notes=definitions['ccd_state_notes']
    if notes.get('source_id')!='ccd_state_notes' or type(notes.get('worksheets')) is not list or not notes['worksheets']:
        raise ValueError('Original CCD Texas notes required')
    for sheet in notes['worksheets']:
        if type(sheet.get('worksheet')) is not str or not sheet['worksheet'] or type(sheet.get('rows')) is not list or not sheet['rows']:
            raise ValueError('Original CCD note sheet namespace missing')
        previous=0
        for entry in sheet['rows']:
            if type(entry.get('source_row')) is not int or entry['source_row']<=previous or type(entry.get('raw')) is not list:
                raise ValueError('Original CCD note row references require strict positive increasing integers')
            previous=entry['source_row']
    for key in ['dictionary','masking','income-extension']:
        section=definitions[key];encoding='utf-8' if key=='income-extension' else 'cp1252'
        if section.get('source_id')!=key or section.get('encoding')!=encoding or type(section.get('lines')) is not list or not section['lines']:
            raise ValueError('Original primary HTML line evidence required')
        previous=0
        for entry in section['lines']:
            if type(entry.get('source_line')) is not int or entry['source_line']<=previous or type(entry.get('html')) is not str:
                raise ValueError('Original HTML source references require strict positive increasing integers')
            previous=entry['source_line']


def validate_native_numeric_cells(table,raw):
    # All retained original subgroup fields remain evidence even though only the
    # separately named All Students cells can supply prospective outcomes.
    for field,value in raw.items():
        if table=='stud' and field.startswith('CP') and field[-1] in {'C','P'}:
            parsed=count(value) if field[-1]=='C' else number(value)
            if parsed is not None and field[-1]=='P' and (not 0<=parsed<=100 or abs(parsed*10-round(parsed*10))>1e-7):
                raise ValueError('Original TAPR student percentages require bounded native tenth-percent precision')
        elif table=='assessment' and field not in {'CAMPUS','CAMPNAME','DISTRICT','DISTNAME'}:
            if field[-1] not in {'N','D','R'}:raise ValueError('Unknown native performance field role')
            parsed=count(value) if field[-1] in {'N','D'} else number(value)
            if parsed is not None and field[-1]=='R' and (not 0<=parsed<=100 or parsed!=int(parsed)):
                raise ValueError('Original TAPR subgroup published rates require bounded whole percentages')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def number(raw):
    if not isinstance(raw, str): raise ValueError('Native Texas cells must remain strings')
    if raw in {'', '-1', '-2', '-3', '*', '**', '•'}: return None
    try: value = Decimal(raw)
    except InvalidOperation as exc: raise ValueError('Invalid native Texas numeric cell') from exc
    if not value.is_finite() or value < 0: raise ValueError('Invalid native Texas numeric cell')
    return float(value)


def count(raw):
    value = number(raw)
    if value is not None: value = Decimal(raw)
    if value is not None and value != int(value): raise ValueError('Nonintegral native Texas count')
    return None if value is None else int(value)


def native_identity(raw):
    key = raw.get('CAMPUS')
    if not isinstance(key, str) or not re.fullmatch(DISTRICT + r'\d{3}', key) or raw.get('DISTRICT') != DISTRICT:
        raise ValueError('Katy requires exact nine-digit native campus and six-digit district')
    return key


def ccd_identity(raw, school=True):
    if raw.get('SCHOOL_YEAR') != YEAR or raw.get('ST') != 'TX' or raw.get('FIPST')!='48' or raw.get('STATENAME')!='TEXAS' or raw.get('LEAID') != LEA or raw.get('ST_LEAID') != NATIVE_LEA:
        raise ValueError('Katy CCD identity/year mismatch')
    if school:
        key, native = raw.get('NCESSCH'), raw.get('ST_SCHID')
        if not isinstance(key, str) or not re.fullmatch(LEA + r'\d{5}', key) or not isinstance(native, str) or not re.fullmatch(NATIVE_LEA + '-' + DISTRICT + r'\d{3}', native):
            raise ValueError('Katy requires complete authoritative CCD school/native identifiers')
        if 'UPDATED_STATUS' in raw and raw['UPDATED_STATUS'] not in {str(n) for n in range(1, 9)}:
            raise ValueError('Katy CCD operational status is not a recognized original status')
        return key, native.rsplit('-', 1)[1]
    return LEA


def grade_evidence(raw):
    values = {k: count(raw[k]) for k in GRADES}; total = count(raw['CPNTALLC'])
    complete = all(v is not None for v in values.values()) and total is not None
    if complete and sum(values.values()) != total: raise ValueError('Native enrolled grades fail enrollment reconciliation')
    lower = sum(values[k] for k in GRADES[:-4]) if complete else None
    high = sum(values[k] for k in GRADES[-4:]) if complete else None
    tested = sum(values['CPNTG%02dC' % g] for g in range(3, 9)) if complete else None
    scope = ('unknown' if not complete else 'zero' if total == 0 else 'mixed' if lower and high
             else 'high' if high else 'grade-school' if tested else 'primary-only')
    return {'raw_grade_counts': {k: raw[k] for k in GRADES}, 'counts': values,
            'enrollment': total, 'complete_reconciled': complete, 'lower_enrollment': lower,
            'high_enrollment': high, 'tested_grades_enrollment': tested, 'scope': scope,
            'no_high_grades': complete and high == 0,
            'prospective_grade_school': scope == 'grade-school',
            'pk_subcategories': {k: raw[k] for k in ['CPNTGP3C', 'CPNTGP4C']},
            'pk_subcategories_note': 'PK3/PK4 are retained subcategories, never added to the enrollment sum twice.'}


def income_evidence(raw):
    total, low, other = [count(raw[k]) for k in ['CPNTALLC', 'CPNTECOC', 'CPNTNEDC']]
    display = number(raw['CPNTECOP'])
    reason = 'Native same-year individual economic status missing or masked' if None in (total, low, other, display) else 'Native enrollment is zero' if total == 0 else None
    if reason is None and (low + other != total or not 0 <= display <= 100 or abs(100 * low / total - display) > .050001):
        raise ValueError('Native economic counts/display percentage do not reconcile')
    return {'raw': {k: raw[k] for k in ['CPNTALLC', 'CPNTECOC', 'CPNTNEDC', 'CPNTECOP']},
            'enrollment': total, 'economic_disadvantage': low, 'not_economic_disadvantage': other,
            'published_percentage': display, 'percentage': None if reason else 100 * low / total,
            'exclusion': reason, 'snapshot_date': '2024-10-25',
            'definition': POLICY['income'], 'limits': POLICY['income_limits']}


def subject_evidence(raw, subject, applicable, income):
    if subject not in FIELDS or type(applicable) is not bool:
        raise ValueError('Prospective subject requires exact Math/ELA and boolean applicability')
    fields = FIELDS[subject]; cells = [raw[k] for k in fields]
    tested, passed, display = count(cells[0]), count(cells[1]), number(cells[2])
    reason = 'Native TAPR published subject percentage missing or masked; suppression preserved' if display is None else None
    if display is not None and (not 0 <= display <= 100 or display != int(display)):
        raise ValueError('Native published TAPR percentage must be a whole percentage from zero through100')
    if tested is not None and passed is not None and passed > tested:
        raise ValueError('Native reported Meets count exceeds reported performance count')
    count_ratio = None
    if tested is not None and passed is not None and tested > 0:
        count_ratio = 100 * passed / tested
        if display is not None and abs(count_ratio - display) > .500001:
            raise ValueError('Native TAPR performance counts fail published-rate reconciliation')
    exclusion = ('Outside the separately audited positive grades3–8/no-high-grade population' if not applicable
                 else income['exclusion'] if income['exclusion'] else reason
                 if reason else None)
    return {'fields': fields, 'raw': cells, 'raw_tested': cells[0], 'raw_meets_or_above': cells[1],
            'raw_published_rate': cells[2], 'reported_tested': tested, 'reported_meets_or_above': passed,
            'published_rate': display, 'proficiency': display,
            'unverified_count_ratio': count_ratio,
            'reported_count_arithmetic_reconciled': count_ratio is not None and display is not None,
            'valid_scores': None,
            'count_evidence': 'Original dictionary/glossary reported performance counts retained unverified. Any display/count rounding reconciliation does not certify exact2025 N/M score-status scope, valid-score counts or the ten-valid-scored floor. Counts do not select source membership or supply modeled outcomes.',
            'native_fields_usable': income['exclusion'] is None and reason is None,
            'outcome_exclusion': reason, 'applicable': applicable,
            'source_usable': exclusion is None, 'exclusion': exclusion,
            'valid_score_verification_status': 'held_pending_exact_2025_N_M_score_status_mapping',
            'sampling_variance': None, 'sampling_interval_available': False,
            'ten_valid_scored_floor_certified': False}


def ccd_count(raw):
    if raw is None or raw.get('DMS_FLAG') not in {'Reported', 'Derived'}: return None
    return count(raw['STUDENT_COUNT'])


def require_current_originals():
    require_runtime_contract()
    for key,meta in SOURCES.items():
        path=ROOT/meta['path'];digest=hashlib.sha256()
        if path.stat().st_size!=meta['bytes']:raise ValueError('Katy complete current original size changed: '+key)
        with path.open('rb')as stream:
            for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
        if digest.hexdigest()!=meta['sha256']:raise ValueError('Katy complete current original fingerprint changed: '+key)


def load_texas(path=ROOT / 'data/source/texas.json'):
    require_runtime_contract()
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != STATE_EXTRACT_SHA:
        raise ValueError('Historical Texas extract changed; separate source review required')
    document = json.loads(content)
    if fingerprint([document.get(k) for k in ['state', 'year', 'academic_year']]) != fingerprint(['TX', 2025, '2024-25']):
        raise ValueError('Historical Texas snapshot/year changed')
    return document


def summarize(links, predicate, note):
    rows = [r for r in links if predicate(r)]
    subjects = {}
    for subject in ['math', 'reading', 'combined']:
        members = [r for r in rows if r['subjects'][subject]['source_usable']]
        subjects[subject] = {'applicable': sum(r['subjects'][subject]['applicable'] for r in rows),
            'usable': len(members), 'native_fields_usable': sum(r['subjects'][subject]['native_fields_usable'] for r in rows), 'prospective_native_school_ids': [r['native_school_id'] for r in members],
            'prospective_nces_school_ids': [r['school_id'] for r in members],
            'exclusions': dict(sorted(Counter(r['subjects'][subject]['exclusion'] for r in rows if r['subjects'][subject]['exclusion']).items())),
            'prospective_30_school_floor_met': len(members) >= 30,
            'approved_for_modeling': False,
            'availability_note': 'Prospective original published-rate availability only; no reported-count screen. Valid-score count scope, the ten-valid-scored minimum and all sampling intervals remain uncertified/unavailable; exact N/M mapping remains held.'}
    for subject in subjects:
        eligible=[r for r in rows if r['subjects'][subject]['source_usable']];xs=[r['income']['percentage']for r in eligible]
        subjects[subject]['income']={'minimum':min(xs)if xs else None,'maximum':max(xs)if xs else None,'distinct':len(set(xs)),'sample_standard_deviation':statistics.stdev(xs)if len(xs)>1 else None}
        subjects[subject]['ccd_charter']=dict(sorted(Counter(r['ccd_flags']['charter']for r in eligible).items()))
        subjects[subject]['ccd_school_type']=dict(sorted(Counter(r['ccd_flags']['school_type']for r in eligible).items()))
    return {'profiles': len(rows), 'native_school_ids': [r['native_school_id'] for r in rows],
            'nces_school_ids': [r['school_id'] for r in rows], 'note': note, 'subjects': subjects,
            'ccd_charter': dict(sorted(Counter(r['ccd_flags']['charter'] for r in rows).items())),
            'ccd_school_type': dict(sorted(Counter(r['ccd_flags']['school_type'] for r in rows).items()))}


def derive(document, snapshot=None):
    require_current_originals()
    expected_base = {'schema_version': 1, 'state': 'TX', 'year': 2025, 'academic_year': YEAR,
        'nces_lea_id': LEA, 'native_lea_id': NATIVE_LEA, 'native_district_id': DISTRICT,
        'status': 'audit_pending', 'scope': 'source_cohort_audit_only',
        'approved_for_source': False, 'approved_for_modeling': False,
        'sources': SOURCES, 'policy': POLICY, 'planning': PLANNING,
        'state_extract': {'path': 'data/source/texas.json', 'sha256': STATE_EXTRACT_SHA}}
    if any(fingerprint(document.get(k)) != fingerprint(v) for k, v in expected_base.items()):
        raise ValueError('Katy source-only identity, metadata, flags or policy changed')
    inputs = document['raw_inputs']
    if fingerprint(inputs) != RAW_INPUT_SHA: raise ValueError('Original Katy input evidence changed')
    schema = {k:{field:value for field,value in inputs[k].items()if field!='records'}for k in ORIGINAL_INVENTORIES}
    if fingerprint(schema) != ORIGINAL_SCHEMA_SHA or fingerprint(inputs.get('definitions')) != DEFINITION_INPUT_SHA:
        raise ValueError('Original source headers/year/population labels or definition evidence changed')
    validate_definition_references(inputs['definitions'])
    if original_identity_fingerprint(inputs)!=ORIGINAL_IDENTITY_SHA:raise ValueError('Original exact identity and source-row projection changed')
    inventories = ORIGINAL_INVENTORIES
    for source, size in inventories.items():
        block = inputs[source]
        if fingerprint({k:v for k,v in block.items()if k!='records'})!=ORIGINAL_METADATA[source]:raise ValueError('Complete original metadata/omitted inventory changed')
        if (block.get('source_id') != source or not isinstance(block.get('header'), list)
                or len(block['records']) != size
                or len(set(block['header'])) != len(block['header'])
                or any(type(e.get('source_row')) is not int or e['source_row'] < (3 if source in {'ref','stud','assessment'} else 2)
                       or not isinstance(e.get('raw'), dict) or set(e['raw']) != set(block['header'])
                       or any(type(v) is not str for v in e['raw'].values()) for e in block['records'])
                or len({e['source_row'] for e in block['records']}) != size):
            raise ValueError('Complete original Katy inventories, typed rows or headers changed')
        if source in {'ref','stud','assessment'}:
            if type(block.get('labels_source_row')) is not int or block['labels_source_row'] != 1 or type(block.get('codes_source_row')) is not int or block['codes_source_row'] != 2:
                raise ValueError('Original TAPR labels/codes require exact integer row1/row2 references')
        elif type(block.get('header_source_row')) is not int or block['header_source_row'] != 1:
            raise ValueError('Original CCD header requires exact integer row1 reference')
    snapshot = load_texas() if snapshot is None else snapshot
    if fingerprint(snapshot) != fingerprint(load_texas()): raise ValueError('Historical Texas snapshot drift')
    directory = {}; by_native = {}; totals = {}; grades = defaultdict(dict)
    for entry in inputs['directory']['records']:
        key, native = ccd_identity(entry['raw'])
        if key in directory or native in by_native: raise ValueError('Duplicate CCD school/native identity')
        directory[key] = entry; by_native[native] = key
    for entry in inputs['membership']['records']:
        raw = entry['raw']; key, native = ccd_identity(raw)
        if key not in directory or by_native[native] != key: raise ValueError('CCD membership has no exact directory attachment')
        if raw['TOTAL_INDICATOR'] == 'Education Unit Total':
            if key in totals: raise ValueError('Duplicate CCD enrollment total')
            totals[key] = entry
        elif raw['TOTAL_INDICATOR'] == 'Subtotal 4 - By Grade':
            if raw['GRADE'] in grades[key]: raise ValueError('Duplicate CCD native grade')
            grades[key][raw['GRADE']] = entry
        else: raise ValueError('Unexpected CCD retained aggregation')
    native_tables = {}
    required = {'ref': ['CAMPUS', 'DISTRICT', 'GRDTYPE', 'GRDSPAN'],
                'stud': ['CAMPUS', 'DISTRICT', 'CPNTALLC', 'CPNTECOC', 'CPNTNEDC', 'CPNTECOP'] + GRADES,
                'assessment': ['CAMPUS', 'DISTRICT'] + sum(FIELDS.values(), [])}
    for table in ['ref', 'stud', 'assessment']:
        source = inputs[table]; rows = {}
        if len(set(source['header'])) != len(source['header']) or len(source['header']) != len(source['labels']) or not set(required[table]) <= set(source['header']):
            raise ValueError('Native TAPR header/label schema changed')
        for field in required[table]:
            label = source['labels'][source['header'].index(field)]
            if type(label) is not str or label!=NATIVE_REQUIRED_LABELS[table][field]:
                raise ValueError('Original native field label changed subject/All Students/enrolled-grade/Including EOC/count-rate role')
            if (field.startswith('CPNT') and not re.search(r'\b2025\b', label)) or (field.startswith('CDA') and not re.search(r'\bSY 2024-25\b', label)):
                raise ValueError('Native required TAPR field is not same-year2025')
        for entry in source['records']:
            key = native_identity(entry['raw'])
            validate_native_numeric_cells(table,entry['raw'])
            if key in rows or key not in by_native or set(entry['raw']) != set(source['header']):
                raise ValueError('Native duplicate, missing CCD identity or incomplete raw row')
            rows[key] = entry
        native_tables[table] = rows
    if len({fingerprint(sorted(v)) for v in native_tables.values()}) != 1:
        raise ValueError('Native same-year table identities differ')
    operational_native={native for native,key in by_native.items() if directory[key]['raw']['UPDATED_STATUS'] in OPERATIONAL}
    missing=operational_native-set(native_tables['stud'])
    if (set(native_tables['stud'])-operational_native or missing!=set(EXPECTED_NATIVE_GAPS)
            or any(by_native[native]!=ncessch for native,ncessch in EXPECTED_NATIVE_GAPS.items())):
        raise ValueError('Original native77 campuses and two exact unmatched operational identities changed; no names or substitutes may join')
    lea_directory = inputs['lea_directory']['records']
    if len(lea_directory) != 1: raise ValueError('Exact CCD agency absent/duplicated')
    ccd_identity(lea_directory[0]['raw'], False)
    lea_total = [e for e in inputs['lea_membership']['records'] if e['raw']['TOTAL_INDICATOR'] == 'Education Unit Total']
    if len(lea_total) != 1: raise ValueError('Exact same-year CCD agency membership absent/duplicated')
    for e in inputs['lea_membership']['records']: ccd_identity(e['raw'], False)
    for source in ['membership', 'lea_membership']:
        for e in inputs[source]['records']:
            r=e['raw']
            unspecified = (r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade' and
                           r['GRADE']==r['RACE_ETHNICITY']==r['SEX']=='Not Specified' and
                           r['STUDENT_COUNT']=='0' and r['DMS_FLAG']=='Derived')
            if not unspecified and (r['RACE_ETHNICITY']!='No Category Codes' or r['SEX']!='No Category Codes'):
                raise ValueError('Original membership requires complete totals/grade rows without demographic filtering')
    from plan_district_comparisons import potential_cohort
    potential = {level: sorted(key for key, e in directory.items() if e['raw']['UPDATED_STATUS'] in OPERATIONAL
        and potential_cohort(e['raw'], totals.get(key, {}).get('raw'), {g: r['raw'] for g, r in grades[key].items()}) == level)
        for level in ['ES', 'HS']}
    planning = inputs['planning']['record']
    if any(type(planning.get(field)) is not int or planning[field] <= 0 for field in
           ['directory_source_row','membership_source_row','enrollment','school_directory_operational_count']):
        raise ValueError('Original planning row references and counts require exact positive integers, never booleans/floats')
    if (fingerprint([planning.get(k) for k in ['nces_lea_id','native_lea_id','state']])
            != fingerprint([LEA,NATIVE_LEA,'TX'])
            or fingerprint(planning.get('potential_cohorts'))
            != fingerprint({level:len(ids) for level,ids in potential.items()})):
        raise ValueError('Original planning district identity and typed cohort counts changed')
    if (fingerprint(planning['potential_school_ids']) != fingerprint(potential)
            or fingerprint(planning['directory_raw']) != fingerprint({k: lea_directory[0]['raw'][k] for k in planning['directory_raw']})
            or fingerprint(planning['membership_raw']) != fingerprint(lea_total[0]['raw'])
            or planning['directory_source_row'] != lea_directory[0]['source_row']
            or planning['membership_source_row'] != lea_total[0]['source_row']
            or planning['enrollment'] != ccd_count(lea_total[0]['raw'])
            or planning['school_directory_operational_count'] != sum(e['raw']['UPDATED_STATUS'] in OPERATIONAL for e in directory.values())):
        raise ValueError('Planning identities/enrollment fail original CCD replay')
    historical = {p['id']: p for p in snapshot['profiles'] if p['profile']['DISTRICT'] == DISTRICT}
    links = []; differences = []
    for key, entry in directory.items():
        raw = entry['raw']; native = ccd_identity(raw)[1]; native_row = native_tables['stud'].get(native)
        ccd_total = ccd_count(totals.get(key, {}).get('raw'))
        ccd_grades = {g: {'source_row': r['source_row'], 'raw_count': r['raw']['STUDENT_COUNT'],
                         'dms_flag': r['raw']['DMS_FLAG'], 'reported_count': ccd_count(r['raw'])} for g, r in sorted(grades[key].items())}
        ref = native_tables['ref'].get(native); outcome = native_tables['assessment'].get(native)
        enrolled = grade_evidence(native_row['raw']) if native_row else None
        income = income_evidence(native_row['raw']) if native_row else {'percentage': None, 'exclusion': 'Native same-year TAPR campus absent'}
        applicable = raw['UPDATED_STATUS'] in OPERATIONAL and bool(enrolled and enrolled['prospective_grade_school'])
        subjects = {s: subject_evidence(outcome['raw'], s, applicable, income) for s in FIELDS} if outcome else {
            s: {'applicable': False, 'source_usable': False, 'exclusion': 'Native same-year TAPR campus absent',
                'proficiency': None, 'valid_scores': None, 'native_fields_usable': False,
                'reported_count_arithmetic_reconciled': False,
                'sampling_variance': None, 'sampling_interval_available': False,
                'ten_valid_scored_floor_certified': False} for s in FIELDS}
        reasons = [subjects[s]['exclusion'] for s in FIELDS if subjects[s]['exclusion']]
        subjects['combined'] = {'applicable': applicable, 'source_usable': not reasons,
            'exclusion': '; '.join(dict.fromkeys(reasons)) if reasons else None,
            'proficiency': (subjects['math']['proficiency'] + subjects['reading']['proficiency']) / 2 if all(subjects[s]['proficiency'] is not None for s in FIELDS) else None,
            'native_fields_usable': all(subjects[s]['native_fields_usable'] for s in FIELDS),
            'valid_scores': None, 'sampling_variance': None, 'sampling_interval_available': False,
            'ten_valid_scored_floor_certified': False,
            'definition': POLICY['combined']}
        if native_row:
            old = historical.get(native)
            if old is None or old['profile_row'] != native_row['source_row'] or old['reference_row'] != ref['source_row'] or old['assessment_row'] != outcome['source_row']:
                raise ValueError('Original CSV row identity disagrees with historical Texas snapshot')
            if any(fingerprint(old['profile'][k]) != fingerprint(native_row['raw'][k]) for k in old['profile']) or fingerprint(old['reference']) != fingerprint(ref['raw']) or any(fingerprint(old['outcomes'][s]) != fingerprint([outcome['raw'][f] for f in FIELDS[s]]) for s in FIELDS):
                raise ValueError('Original native cells disagree with pinned historical snapshot')
            if ccd_total != enrolled['enrollment']: differences.append({'school_id': key, 'native_school_id': native, 'ccd_membership': ccd_total, 'native_enrollment': enrolled['enrollment']})
        offered = {g: raw.get('G_' + g + '_OFFERED') for g in ['PK', 'KG'] + [str(g) for g in range(1, 14)] + ['UG', 'AE']}
        contradiction = bool(enrolled and enrolled['high_enrollment'] and ref['raw']['GRDTYPE'] in {'E', 'M'})
        links.append({'school_id': key, 'native_school_id': native, 'ccd_native_school_id': raw['ST_SCHID'],
            'name': raw['SCH_NAME'], 'ccd_source_row': entry['source_row'],
            'ccd_flags': {'status': raw['UPDATED_STATUS_TEXT'], 'operational': raw['UPDATED_STATUS'] in OPERATIONAL,
                          'school_type': raw['SCH_TYPE_TEXT'], 'charter': raw['CHARTER_TEXT'], 'level': raw['LEVEL'],
                          'virtual_status': None, 'virtual_status_note': 'No virtual field in this CCD directory.'},
            'ccd_offered': {'flags': offered, 'as_reported': raw['IGOFFERED'], 'no_grades': raw['NOGRADES'], 'low': raw['GSLO'], 'high': raw['GSHI']},
            'ccd_membership': {'total_source_row': totals.get(key, {}).get('source_row'), 'reported_total': ccd_total, 'grades': ccd_grades},
            'native_present': native_row is not None,
            'native_peims_membership': {'raw_count': native_row['raw']['CPETALLC'], 'count': count(native_row['raw']['CPETALLC']),
                'note': 'TAPR membership and enrollment are distinct administrative concepts. The glossary describes an under-two-hour service distinction, but no exact cause is assigned to an individual recorded difference. Membership never substitutes for the native enrolled individual-income denominator or an assessment count.'} if native_row else None,
            'native_source_rows': {s: native_tables[s][native]['source_row'] for s in ['ref', 'stud', 'assessment']} if native_row else {},
            'native_reference': ref['raw'] if ref else None, 'native_enrolled': enrolled,
            'native_reference_conflicts_with_positive_high_enrollment': contradiction,
            'income': income, 'subjects': subjects,
            'exclusion': 'Native same-year TAPR campus absent' if not native_row else None if applicable else 'Outside positive grades3–8/no-high-grade cohort: ' + enrolled['scope']})
    cohorts = {'native_no_high_grade_profiles': summarize(links, lambda r: bool(r['native_enrolled'] and r['native_enrolled']['no_high_grades']), 'Complete native EE–8 enrollment profiles; primary-only retained separately, not model members.'),
        'prospective_grade_school': summarize(links, lambda r: bool(r['native_enrolled'] and r['native_enrolled']['prospective_grade_school']), 'Positive native grades3–8, zero native grades9–12; exact same-year individual income and each original published subject rate determine prospective source availability. No reported-count or diagnostic screen.'),
        'primary_only': summarize(links, lambda r: bool(r['native_enrolled'] and r['native_enrolled']['scope'] == 'primary-only'), 'No positive tested grades3–8; native outcome absence preserved.'),
        'high_only': summarize(links, lambda r: bool(r['native_enrolled'] and r['native_enrolled']['scope'] == 'high'), 'Outside audited grade-school population; high-school assessment audit remains required.'),
        'mixed_grade': summarize(links, lambda r: bool(r['native_enrolled'] and r['native_enrolled']['scope'] == 'mixed'), 'Any positive high-grade enrollment excludes this grades3–8-only population, regardless of native reference label.')}
    enrollment = {'ccd_lea_reported': ccd_count(lea_total[0]['raw']), 'ccd_operational_school_sum': sum(r['ccd_membership']['reported_total'] for r in links if r['ccd_flags']['operational']),
        'native_campus_sum': sum(r['native_enrolled']['enrollment'] for r in links if r['native_present']),
        'native_peims_membership_sum': sum(r['native_peims_membership']['count'] for r in links if r['native_present']),
        'native_enrollment_membership_differences': [{'native_school_id': r['native_school_id'], 'enrollment': r['native_enrolled']['enrollment'], 'membership': r['native_peims_membership']['count']} for r in links if r['native_present'] and r['native_enrolled']['enrollment'] != r['native_peims_membership']['count']],
        'native_economic_disadvantage_sum': sum(r['income']['economic_disadvantage'] for r in links if r['native_present']),
        'matched_school_enrollment_differences': differences,
        'definition_note': 'TAPR enrolled and CCD reported membership are independent administrative concepts; equality here does not make either a tested denominator.'}
    coverage = {'complete_omitted_original_inventories':{k:dict({a:b for a,b in inputs[k]['complete_district_inventory'].items()if a not in {'omitted_identity_population_inventory','omitted_source_ordinals'}},complete_inventory_path='raw_inputs.'+k+'.complete_district_inventory')for k in ORIGINAL_INVENTORIES},
        'source_rows':{k:len(inputs[k]['records'])for k in inventories},
        'original_records':sum(len(inputs[k]['records'])for k in inventories),
        'original_typed_cells':sum(sum(len(e['raw'])for e in inputs[k]['records'])for k in inventories),
        'directory_records': len(links), 'operational_schools': sum(r['ccd_flags']['operational'] for r in links),
        'native_campuses': len(native_tables['stud']), 'native_scope_counts': dict(sorted(Counter(r['native_enrolled']['scope'] for r in links if r['native_present']).items())),
        'ccd_school_types': dict(sorted(Counter(r['ccd_flags']['school_type'] for r in links).items())),
        'ccd_charter': dict(sorted(Counter(r['ccd_flags']['charter'] for r in links).items())),
        'native_usable_income': sum(r['income']['exclusion'] is None for r in links),
        'prospective_subject_members': {s: cohorts['prospective_grade_school']['subjects'][s]['usable'] for s in ['math', 'reading', 'combined']},
        'grade_school_published_rates_differing_from_unverified_count_ratios': {
            s: sum(r['subjects'][s]['proficiency'] != r['subjects'][s]['unverified_count_ratio']
                   for r in links if r['subjects'][s]['source_usable']) for s in FIELDS},
        'native_absent_from_ccd': sorted(set(native_tables['stud']) - set(by_native)),
        'ccd_absent_from_native': [r['school_id'] for r in links if not r['native_present']],
        'nonoperational_identities':[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],status=r['ccd_flags']['status'])for r in links if not r['ccd_flags']['operational']],
        'operational_native_gaps':[dict(school_id=r['school_id'],native_school_id=r['native_school_id'])for r in links if r['ccd_flags']['operational']and not r['native_present']],
        'positive_enrolled_grades_not_offered':[dict(school_id=r['school_id'],native_school_id=r['native_school_id'],grades=[k for k,v in r['native_enrolled']['counts'].items()if v and k!='CPNTGEEC'and r['ccd_offered']['flags'].get('PK'if k=='CPNTGPKC'else'KG'if k=='CPNTGKNC'else str(int(k[5:7])))!='Yes'])for r in links if r['native_present']and any(v and k!='CPNTGEEC'and r['ccd_offered']['flags'].get('PK'if k=='CPNTGPKC'else'KG'if k=='CPNTGKNC'else str(int(k[5:7])))!='Yes'for k,v in r['native_enrolled']['counts'].items())],
        'native_reference_high_grade_contradictions': [r['native_school_id'] for r in links if r['native_reference_conflicts_with_positive_high_enrollment']],
        'verified_valid_score_counts': 0,
        'reported_reconciled_performance_arithmetic_rows': {s: sum(r['subjects'][s]['reported_count_arithmetic_reconciled'] for r in links) for s in FIELDS},
        'valid_score_verification_hold': 'Current2025 primary documentation must map N/NAAR and M/medical exemption score statuses to these exact native enrolled-grade3–8 TAPR #Tests fields.',
        'ten_valid_scored_floor_certified': False,
        'sampling_intervals_available': False, 'model_results': 0, 'canonical_import_performed': False, 'served_comparison_created': False}
    outside = [r for r in links if r['exclusion'] is not None]
    if (coverage['directory_records'] != 81 or coverage['operational_schools'] != 79
            or coverage['native_campuses'] != 77
            or coverage['native_scope_counts'] != {'grade-school':65,'high':11,'mixed':1}
            or coverage['prospective_subject_members'] != {'math':64,'reading':64,'combined':64}
            or len(outside)!=16):
        raise ValueError('Frozen original Katy roster/source-cohort coverage changed')
    eligible = cohorts['prospective_grade_school']['subjects']['combined']['prospective_nces_school_ids']
    return {'original_identity_sha256':ORIGINAL_IDENTITY_SHA,'source_policy_sha256':POLICY_SHA,
        'roster_links': links, 'cohorts': cohorts, 'coverage': coverage,
        'outside_grade_school_population': outside, 'enrollment_reconciliation': enrollment,
        'planning_identity_reconciliation': {'potential_school_ids': potential,
            'source_usable_school_ids': eligible, 'source_not_planning_ES': sorted(set(eligible) - set(potential['ES'])),
            'planning_ES_not_source_usable': sorted(set(potential['ES']) - set(eligible)),
            'scope_note': 'Discovery IDs independently replayed; they never select source outcomes or grant model approval.'},
        'historical_state_consistency': {'matched_native_profiles': len(historical), 'original_csv_cells_and_rows_verified': True,
            'selected_outcome_basis': 'Original published whole-percent R cells only; state count-ratio arithmetic and model fits are not reused.',
            'statewide_ratio_precision_is_not_selected': True,
            'district_source_approval': False, 'district_modeling_approval': False}}


def validate(document, snapshot=None):
    expected = derive(document, snapshot)
    fields = {'schema_version', 'state', 'year', 'academic_year', 'nces_lea_id', 'native_lea_id', 'native_district_id',
              'status', 'scope', 'approved_for_source', 'approved_for_modeling', 'sources', 'policy', 'planning', 'raw_inputs', 'state_extract'}
    if set(document) != fields | set(expected) or any(fingerprint(document.get(k)) != fingerprint(v) for k, v in expected.items()):
        raise ValueError('Katy derived memberships, exclusions or arithmetic failed exact replay')
    return expected['coverage']


def native_cell(v):
    return {'cell_type': type(v).__name__, 'iso8601': v.isoformat()} if isinstance(v, (date, datetime)) else v


def read_ccd_rows(key):
    p=ROOT/SOURCES[key]['path'];member=p.stem+'.csv'
    process=subprocess.Popen(['unzip','-p',str(p),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig')
    records=[];omitted=[];digest=hashlib.sha256(b'[');total=0;cells=0;populations=Counter()
    try:
        parser=csv.DictReader(process.stdout)
        for ordinal,row in enumerate(parser,2):
            if row['LEAID']!=LEA and row['ST_LEAID']!=NATIVE_LEA:continue
            total+=1
            if 'directory'in key or row['TOTAL_INDICATOR']in{'Education Unit Total','Subtotal 4 - By Grade'}:records.append(dict(source_row=ordinal,raw=row))
            else:
                if omitted:digest.update(b',')
                digest.update(json.dumps(dict(source_row=ordinal,raw=row),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
                keys=['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH','GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG']
                omitted.append(dict(source_row=ordinal,identity_population={k:row[k]for k in keys if k in row}));cells+=len(row);populations[row.get('TOTAL_INDICATOR','not_applicable')]+=1
        if process.wait()!=0:raise ValueError('Failed original CCD stream')
        digest.update(b']')
        return dict(source_id=key,member=member,header_source_row=1,header=parser.fieldnames,records=records,complete_district_inventory=dict(original_district_rows=total,retained_rows=len(records),omitted_rows=len(omitted),omitted_source_ordinals=[r['source_row']for r in omitted],omitted_identity_population_inventory=omitted,omitted_typed_cells=cells,omitted_raw_ordinal_sha256=digest.hexdigest(),omitted_populations=dict(sorted(populations.items()))))
    finally:
        process.stdout.close()
        if process.poll()is None:process.terminate();process.wait()


def extract_raw_inputs():
    require_current_originals()
    inputs={key:read_ccd_rows(key)for key in ['directory','membership','lea_directory','lea_membership']}
    for key in ['ref', 'stud', 'assessment']:
        with (ROOT / SOURCES[key]['path']).open(newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f); labels = next(reader); codes = next(reader); rows = []
            for i, values in enumerate(reader, 3):
                if len(values) != len(codes): raise ValueError('Malformed original TAPR row')
                raw = dict(zip(codes, values))
                if raw['DISTRICT'] == DISTRICT or raw['CAMPUS'].startswith(DISTRICT): rows.append({'source_row': i, 'raw': raw})
        inputs[key] = {'source_id': key, 'labels_source_row': 1, 'codes_source_row': 2,
                       'labels': labels, 'header': codes, 'records': rows,
                       'complete_district_inventory':dict(original_district_rows=len(rows),retained_rows=len(rows),omitted_rows=0,omitted_source_ordinals=[],omitted_identity_population_inventory=[],omitted_typed_cells=0,omitted_raw_ordinal_sha256=fingerprint([]),omitted_populations={})}
    from pypdf import PdfReader
    import openpyxl
    definitions = {}
    for key, pages in [('glossary', [1, 2, 3, 5, 6, 28, 29]), ('income-guide', [36, 37, 38, 39, 40])]:
        pdf = PdfReader(ROOT / SOURCES[key]['path'])
        definitions[key] = {'source_id': key, 'pages': [{'pdf_page': n, 'text': pdf.pages[n-1].extract_text(extraction_mode='layout')} for n in pages]}
    workbook = openpyxl.load_workbook(ROOT / SOURCES['ccd_state_notes']['path'], read_only=True, data_only=True)
    sheets = []
    try:
        for sheet in workbook:
            rows = [{'source_row': i, 'raw': [native_cell(v) for v in row]} for i, row in enumerate(sheet.iter_rows(values_only=True), 1)
                if i <= 3 or any(isinstance(v, str) and ('Texas' in v or 'Katy' in v or v == 'TEXAS') for v in row)]
            if any(r['source_row'] > 3 for r in rows): sheets.append({'worksheet': sheet.title, 'rows': rows})
    finally: workbook.close()
    definitions['ccd_state_notes'] = {'source_id': 'ccd_state_notes', 'worksheets': sheets}
    for key in ['dictionary', 'masking', 'income-extension']:
        encoding = 'utf-8' if key == 'income-extension' else 'cp1252'
        lines = (ROOT / SOURCES[key]['path']).read_text(encoding=encoding).splitlines()
        rows = [{'source_line': i, 'html': line} for i, line in enumerate(lines, 1)
                if key != 'dictionary' or any(field in line for field in sum(FIELDS.values(), []))]
        definitions[key] = {'source_id': key, 'encoding': encoding, 'lines': rows}
    # Supplemental performance score-code proof is retained as complete PDF pages.
    manual = PdfReader(ROOT / SOURCES['accountability-manual']['path'])
    definitions['accountability-manual'] = {'source_id': 'accountability-manual', 'pages': [
        {'pdf_page': n, 'text': manual.pages[n-1].extract_text(extraction_mode='layout')} for n in MANUAL_PAGES]}
    listing = PdfReader(ROOT / SOURCES['performance-listing']['path'])
    definitions['performance-listing'] = {'source_id': 'performance-listing', 'pages': [{'pdf_page': n, 'text': listing.pages[n-1].extract_text(extraction_mode='layout')} for n in [4, 6, 8]]}
    inputs['definitions'] = definitions
    planning = json.loads((ROOT / PLANNING['source']).read_text())
    agency = next(r for r in planning['agencies'] if r['nces_lea_id'] == LEA)
    fields = ['nces_lea_id', 'state', 'native_lea_id', 'enrollment', 'enrollment_flag', 'school_directory_operational_count',
              'potential_cohorts', 'potential_school_ids', 'directory_raw', 'directory_source_row', 'membership_raw', 'membership_source_row']
    inputs['planning'] = {'source': PLANNING['source'], 'sources': planning['sources'], 'record': {k: agency[k] for k in fields}}
    return inputs


def build(inputs, output=OUTPUT):
    # Original extraction and independent bootstrap may insert definition evidence
    # in different dictionary positions. Normalize that position for stable bytes.
    inputs = dict(inputs)
    if 'definitions' in inputs: inputs['definitions'] = inputs.pop('definitions')
    document = {'schema_version': 1, 'state': 'TX', 'year': 2025, 'academic_year': YEAR,
        'nces_lea_id': LEA, 'native_lea_id': NATIVE_LEA, 'native_district_id': DISTRICT,
        'status': 'audit_pending', 'scope': 'source_cohort_audit_only', 'approved_for_source': False, 'approved_for_modeling': False,
        'sources': SOURCES, 'policy': POLICY, 'planning': PLANNING, 'raw_inputs': inputs,
        'state_extract': {'path': 'data/source/texas.json', 'sha256': STATE_EXTRACT_SHA}}
    document.update(derive(document)); validate(document)
    Path(output).write_text(json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    return document['coverage']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true', help='Reopen all pinned original CSV/PDF/HTML/CCD files')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(extract_raw_inputs(), args.output) if args.extract else validate(json.loads(args.output.read_text()))
    print(json.dumps(result, sort_keys=True))

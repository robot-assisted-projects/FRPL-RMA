"""Audit Lee original 2024–25 CCD and Florida sources without fitting or publishing.

--extract rereads the complete pinned original district inventories. Default
validation is offline replay of retained typed records, primary definitions,
exact school identities, scope, masks and individual income arithmetic.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess

import openpyxl

import prepare_florida as florida
import plan_district_comparisons as planning
from state_registry import reported_count

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/source/lee-district-audit.json'
LEA='1201080'
NATIVE_LEA='FL-36'
NATIVE_DISTRICT='36'
YEAR=2025
ACADEMIC_YEAR='2024-2025'
STATE_EXTRACT_SHA='523afad888444e875fc8d06486b20240896341d55b14d9484e8b935888f66daf'
STATE_SNAPSHOT_SHA='f08640b8501e323cfc9298057500c4087e543bacdfda5fa4a6edb8a49778cfb8'
TABLES=['directory','lea_directory','membership','lea_membership','native_grades','native_income','native_assessment']
OPERATIONAL={'1','3','4','5','8'}
GRADES=['PK','KG']+[str(g)for g in range(1,14)]+['UG','AE']
ENROLLED_GRADES=['PK','KG']+[str(g)for g in range(1,13)]
POLICY={'identity': 'Exact original2024–25 CCD LEA1201080 /FL-36 and FDOE district36 identities. The original2024–25 FDOE elements115225 and172825 document two-digit district and four-digit school widths. Only strictly numeric original integer/digit school codes use that documented zero padding; remove only the explicit FL- prefix from exact CCD FL-36-####. Preserve authoritative full12-digit NCES IDs separately; names, corrected digits, suffix guesses and float/bool substitutions never establish ownership.', 'roster': 'Retain every district36 original CCD directory, district/school total and grade membership record; every native Fall Survey2, Final Survey3 and School Grades row including providers; complete original headers, notes and primary definitions. Nonoperational, unmatched, missing, provider, collocated, high, mixed and primary records remain evidence, never inferred members.', 'population': 'Prospective pure lower profiles require exact operational CCD ownership; complete unadjusted reported PK–8 offered flags with a grade3–8 offer and no9–13/UG/AE; native Fall Survey2 explicit zero in every grade9–12 and at least one positive or protected-positive enrolled grade3–8. Offered and enrolled grades remain separate. Primary, zero-tested, high, mixed and uncertain configurations stay outside. Planning, income extremes, school type, charter status and diagnostic quality never select scope. Original above-grade testing scope does not establish participation in a profile with only zero enrolled tested grades.', 'income': 'Florida 2024–25 Final Survey 3 (February) raw individual Lunch Status counts: D/F free eligibility + 3/E reduced eligibility + C/R CEP direct certification, divided by same-survey enrolled students (PK–12). Never uses the USDA 1.6-adjusted federal funding numerator or published school-grade economic percentage. CEP N means not individually identified eligible and is excluded from the numerator. Provision 2 code 4 reports all enrolled students, so schools with nonzero or masked code 4 have unavailable income. At CEP schools this proxy counts direct certification/household extension rather than a complete income survey of all families; undercount and reporting coverage are unknown. No other-year backfill.', 'income_codes': 'The2024–25 Lunch Status146025 primary definition requires district option6/9 conversions toC/D before reporting. Use each school’s own February Final Survey3 PK–12 denominator and original D/F+3/E+C/R individual counts only when Provision2 code4 is explicit zero. Preserve funding columns9–11 as separate raw evidence, never a model income measure. No USDA1.6 multiplier, School Grades economic percentage, other-year income or enrollment substitution; CEP individual identification coverage remains unknown.', 'assessment': '2024–25 native School Grades English Language Arts Achievement and Mathematics Achievement components: Level 3 or above / valid assessed students under Florida full-year-enrollment and home-zoned attribution rules, including eligible FAA Performance Task but excluding FAA Datafolio. ELA FAST PM3 grades 3–10 and Math FAST PM3 grades 3–8 plus B.E.S.T./Access Algebra 1/Geometry EOCs; this cohort enrolls no grades 9–12 in the same-year Survey 2 registry. ELL included after two US-school years; medical/extraordinary exemptions excluded. Components require at least 10 eligible students. Native whole-percent rates only; score denominators absent, so all model sampling intervals unavailable. Collocated combined results and provider-specific virtual rates are excluded from individual-school matches.', 'native_population': 'Original School Grades2025 Math Achievement column9 and ELA Achievement column6 are published whole Level3-or-above accountable rates. Keep exact native valid accountable population and full-year, home-zoned, ELL-after-two-US-school-years, medical-exemption and eligible FAA performance rules. Preserve prescribed FAST PM3/BEST/Access EOC and above-grade scope; Datafolio and participation remain separate. No grade/component averaging, count-ratio substitution or inferred test administration membership.', 'suppression': 'Protected native Fall counts remain unavailable numeric counts with protected-positive presence, never zero or reconstructed. Missing/masked income or achievement remains unavailable. Explicit zero remains zero. Never complement masks or backfill another year.', 'income_enrollment_discrepancy': 'Own February Final Survey3 PK–12 denominator is distinct from Fall Survey2, CCD membership and full-year accountable performance. Retain every original school/district total and any exact mismatch without assigning a cause or inventing an identity. None supplies an assessment valid-score denominator.', 'exclusions': 'Provider-specific virtual results lack corresponding provider income; collocated combined results cannot be assigned to one school. Preserve raw provider, collocated, charter, alternative/ESE and type flags. None supplies identity, income or an automatic diagnostic exclusion.', 'counts': 'Published School Grades achievement provides no verified valid-score denominators. The primary guide at-least-ten-eligible component condition does not certify ten valid-scored pupils. All valid-score counts, variances and intervals remain null/unavailable and the scored floor remains uncertified. Enrollment, percent tested, participation, federal95%-adjustment and studentization never substitute. The existing count hold is retained without new speculative investigations.', 'combined': 'Equal mean of usable original published Math and ELA rates with own same-year individual income; not the percentage proficient in both.', 'approval': 'Source/cohort audit only: audit_pending/source_cohort_audit_only and both approvals false. No model fits, normalized release, canonical import, served comparison or master publication. Separate numerical and integration reviews remain required.', 'raw_compaction': 'Retain every complete needed original Lee district directory/total/grade/native registry/income/SchoolGrades row, all native provider rows and full primary definitions. Whole original archives remain pinned. For omitted CCD demographic populations, preserve every exact original ordinal and original identity/population fields plus full raw-with-ordinal digest, counts, typed cells and population inventory. Original source selection cannot be repinned through public mutable constants.', 'source_freshness': 'Every source replay verifies current complete original byte/size pins and current Florida secondary source, including caller-cached paths; offline replay hashes local originals but never reextracts/decompresses, refits, imports or publishes.'}
PLANNING={'source': 'data/source/district-comparison-candidates.json', 'enrollment': 102506, 'operational_roster': 119, 'potential_ES': 78, 'potential_HS': 21, 'note': 'Discovery only; exact Lee original CCD/native replay defines scope. Planning never supplies income, achievement or modeling approval.'}

SOURCES={'ccd_school_membership': {'path': 'data/raw/ccd_sch_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip', 'sha256': '4a7f660c5fc5eaae488dd02fd43498f349fc828b227edd0970d5b6995ead4d4d', 'bytes': 212696691}, 'ccd_school_directory': {'path': 'data/raw/ccd_sch_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip', 'sha256': '39326da788aa322353d20ceaf8ad4baed26272502cd05b066cf6c594988b21ab', 'bytes': 13352819}, 'assessment': {'path': 'data/raw/fl_assessment_2025.xlsx', 'url': 'https://cdn.fldoe.org/file/18534/SchoolGrades25.xlsx', 'sha256': '52d3d3d7c2187eb9cbe22477bd088c0c13570f6f2b9f45f74a4b9f771be70a5b', 'bytes': 940291}, 'income': {'path': 'data/raw/fl_income_2025.xlsx', 'url': 'https://cdn.fldoe.org/file/7584/2425LunchStatusFS2-3.xlsx', 'sha256': '48cd9428ea32decf723cc03c2ee7d25528ed8df3db36b20d97e948805344086d', 'bytes': 1542165}, 'grades': {'path': 'data/raw/fl_grades_2025.xlsx', 'url': 'https://cdn.fldoe.org/file/7584/2425MembBySchoolByGrade.xlsx', 'sha256': '930a81159fac3db4b38c6428aebc2e5000e9199ce88bb80ecc7431838ae3c93a', 'bytes': 595543}, 'grade-guide': {'path': 'data/raw/fl_guide_2025.pdf', 'url': 'https://cdn.fldoe.org/file/18534/SchoolGradesCalcGuide25.pdf', 'sha256': '7dd60cd7c45d03f6324d16d9dcdeb244a5da79f5bccb25859badb32cc2932309', 'bytes': 803109}, 'lunch-guide': {'path': 'data/raw/fl_lunch_definition_2025.pdf', 'url': 'https://cdn.fldoe.org/core/fileparse.php/20744/urlt/2425-146025.pdf', 'sha256': '1c8617d492e845e8bdf584c4780de6ac1cf7e7d35e7f2faaa96cec30cf322216', 'bytes': 212633}, 'ccd_lea_directory': {'path': 'data/raw/ccd_lea_029_2425_w_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip', 'sha256': '2745169e4bc7cd53adff179830c3d4b9bb035ac79580ecea01ef389a161936a9', 'bytes': 2830266}, 'ccd_lea_membership': {'path': 'data/raw/ccd_lea_052_2425_l_1a_073025.zip', 'url': 'https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip', 'sha256': '501d72720a01c26e0e041cd3b1aa6653d0a94725ba0a1e85c42c4f183bc627ba', 'bytes': 68497561}, 'school-code': {'path': 'data/build/lee-source-implementation/originals/fl-school-code-2025.pdf', 'url': 'https://www.fldoe.org/core/fileparse.php/20744/urlt/2425-172825.pdf', 'resolved_url': 'https://cdn.fldoe.org/core/fileparse.php/20744/urlt/2425-172825.pdf', 'bytes': 157800, 'sha256': 'd0c1ab18838e4a6078458fd31face66bbec19e11b4dca9108ae8618707779ebe'}, 'district-code': {'path': 'data/build/lee-source-implementation/originals/fl-district-code-2025.pdf', 'url': 'https://www.fldoe.org/core/fileparse.php/20744/urlt/2425-115225.pdf', 'resolved_url': 'https://cdn.fldoe.org/core/fileparse.php/20744/urlt/2425-115225.pdf', 'bytes': 135951, 'sha256': 'c85f7c809e901a723908e7e74597f8004e4b3da69806bc6d0e819ad188707e40'}}
RAW_INPUT_SHA='2355a0fcae20dcd27b5c60c2469ef390c4129bbda872527366b0de66c2e35299'
ORIGINAL_SCHEMA_SHA='3c3d1e2a94a7b45975a61276e27bfc5806931bec97aa3a22410eed34e27c3e4d'
DEFINITION_INPUT_SHA='e0728b5b883a46e74b5cd3d652a59f0def259bdc356f74a7ae2bba2396b793cf'
ORIGINAL_IDENTITY_SHA='032472bb83e34a5fa7307b3df6f35b95fc6162c5f2f3b5c5e5c6ede2123b26de'
ORIGINAL_METADATA={'directory': 'b47704cdbd5f2885f7969385dca8197ac21cfa11eef7625e0debdb14e5029d96', 'lea_directory': 'e0231750b6862fc03c14924d3a49f97bfe63ad6f71642ba8d5ca7849e5df718b', 'membership': 'd0f4e69a7e91c85dbdd646c73ede1cf9727d3b351b0a3f27c8dbb3767d06451c', 'lea_membership': '9b0483dc0e4353b3b5e6564a3d4384379658a0734854bfa34874d70c261c4433', 'native_grades': '4f42fcd27956384653d393765345941c26af460b71ef63192ed29f52933adcea', 'native_income': '2c3640ab24f03f40f05879a223d84774a229831f69168d497a138f8ac77e33bd', 'native_assessment': '19b436f79332e059461a4957c4fcf45a907c8cba58cfdbf69e7b59426529ea12'}
ORIGINAL_INVENTORIES={'directory': 122, 'lea_directory': 1, 'membership': 983, 'lea_membership': 16, 'native_grades': 115, 'native_income': 115, 'native_assessment': 97}
NATIVE_COLUMN_TYPES={'native_grades': [['str'], ['str'], ['str'], ['str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str']], 'native_income': [['int'], ['str'], ['int'], ['str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['int', 'str'], ['float', 'int', 'str']], 'native_assessment': [['str'], ['str'], ['str'], ['str'], ['str'], ['NoneType', 'int'], ['int'], ['int'], ['NoneType', 'int'], ['int'], ['int'], ['NoneType', 'int'], ['NoneType', 'int'], ['NoneType', 'int'], ['NoneType', 'int'], ['NoneType', 'int'], ['NoneType', 'int'], ['int'], ['int'], ['int'], ['int'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['str'], ['float', 'int']]}


POLICY_SHA='df44f3c3f7e1e60874763e20cbe3961fd70a8f44d378a63848625d5ee8dce7c3'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def identity_fingerprint(inputs):
    return fingerprint({t:[dict(source_row=e['source_row'],identity=({k:e['raw'].get(k)for k in ['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH','GRADE','TOTAL_INDICATOR']}if not t.startswith('native_')else[e['raw'][0],e['raw'][2],e['raw'][3]if t=='native_assessment'else None]))for e in inputs[t]['records']]for t in TABLES})


def native_code(value,width):
    if type(value)is int and 0<=value<10**width:
        return str(value).zfill(width)
    if type(value)is str and re.fullmatch(r'\d{1,'+str(width)+'}',value):
        return value.zfill(width)
    raise ValueError('Original native code must be a strict integer or digit string, never bool/float/name')


def native_identity(raw):
    if native_code(raw[0],2)!=NATIVE_DISTRICT:
        raise ValueError('Foreign native district')
    return NATIVE_DISTRICT+'-'+native_code(raw[2],4)


def ccd_identity(raw, *, district=False):
    if (raw.get('SCHOOL_YEAR'),raw.get('ST'),raw.get('FIPST'),raw.get('STATENAME'),raw.get('LEAID'),raw.get('ST_LEAID'))!=(ACADEMIC_YEAR,'FL','12','FLORIDA',LEA,NATIVE_LEA):
        raise ValueError('Exact same-year attached-LEA CCD ownership required')
    if district:
        return LEA
    match=re.fullmatch(r'FL-('+NATIVE_DISTRICT+r'-\d{4})',raw.get('ST_SCHID',''))
    if not match or not re.fullmatch(LEA+r'\d{5}',raw.get('NCESSCH','')):
        raise ValueError('Exact authoritative original CCD school identities required')
    return match.group(1)


def native_count(value):
    if value in [None,'','*','**','***','N/A'] and type(value)not in {bool,float}:
        return None
    if type(value)is not int or value<0:
        raise ValueError('Original native count requires strict nonnegative integer or mask, never bool/float')
    return value


def published_rate(value):
    if value is None or type(value)is str and value in {'','*','**','***','N/A'}:
        return None
    if type(value)is not int or not 0<=value<=100:
        raise ValueError('Original native proficiency requires whole published integer percentage or mask')
    return float(value)


def offered_evidence(raw):
    flags={g:raw.get('G_'+g+'_OFFERED')for g in GRADES}
    complete=(raw.get('IGOFFERED')=='As reported'and raw.get('NOGRADES')=='No'and all(v in {'Yes','No'}for v in flags.values()))
    offered=[g for g,v in flags.items()if v=='Yes'];lower=any(g in offered for g in GRADES[:10]);high=any(str(g)in offered for g in range(9,13));extra=any(g in offered for g in ['13','UG','AE'])
    scope='uncertain'if not complete else'other'if extra or not(lower or high)else'mixed'if lower and high else'ES'if lower else'HS'
    return dict(flags=flags,complete_reported_flags=complete,scope=scope,offered=offered,offered_tested_grades=[str(g)for g in range(3,9)if str(g)in offered],low=raw.get('GSLO'),high=raw.get('GSHI'),level=raw.get('LEVEL'))


def enrolled_evidence(entry, offered=None):
    if entry is None:
        return None
    values={g:dict(raw=v,reported_count=native_count(v),status='protected_positive'if v=='*'else'unavailable'if native_count(v)is None else'explicit_zero'if v==0 else'positive')for g,v in zip(ENROLLED_GRADES,entry['raw'][4:])}
    positive=[g for g,v in values.items()if v['status']in {'positive','protected_positive'}]
    result=dict(source='grades',source_row=entry['source_row'],values=values,native_grade_school_contract=all(values[str(g)]['reported_count']==0 for g in range(9,13)),positive_or_protected_grades=positive,positive_or_protected_tested_grades=[g for g in positive if g in [str(n)for n in range(3,9)]],protected_grades=[g for g,v in values.items()if v['status']=='protected_positive'],known_count_sum=sum(v['reported_count']for v in values.values()if v['reported_count']is not None),complete_count_sum=sum(v['reported_count']for v in values.values())if all(v['reported_count']is not None for v in values.values())else None)
    if offered is not None:
        result.update(offered_with_explicit_zero_enrollment=[g for g in offered['offered']if g in values and values[g]['status']=='explicit_zero'],positive_or_protected_without_offer=[g for g in positive if g not in offered['offered']])
    return result


def income_evidence(entry):
    if entry is None:
        return dict(source='income',source_row=None,survey_enrollment=None,individual_eligible=None,percentage=None,exclusion='Same-year Final Survey3 individual income row missing',raw=None)
    raw=entry['raw']
    for field in range(4,11):native_count(raw[field])
    rate=raw[11]
    if rate is not None and rate not in {'','*','**','***','N/A'} and(type(rate)not in{int,float}or not 0<=rate<=1):raise ValueError('Original funding rate must remain a finite fraction or mask, never bool')
    n=native_count(raw[INCOME_COLUMNS['denominator']]);counts=[native_count(raw[INCOME_COLUMNS[k]])for k in ['free','reduced','provision2','direct']]
    reason='Provision2 code4 is nonzero or masked; individual income unavailable'if counts[2]!=0 else'Individual eligibility counts or denominator missing/masked/zero'if n in {None,0}or None in counts else None
    low=None if reason else counts[0]+counts[1]+counts[3]
    if low is not None and low>n:
        raise ValueError('Individual eligibility exceeds own February denominator')
    return dict(source='income',source_row=entry['source_row'],survey_enrollment=n,individual_eligible=low,percentage=None if reason else 100*low/n,exclusion=reason,raw=raw,fields=dict(enrolled=raw[4],free_D_F=raw[5],reduced_3_E=raw[6],provision2_4=raw[7],CEP_direct_C_R=raw[8],funding_CEP_multiplier=raw[9],funding_numerator=raw[10],funding_rate=raw[11]),year=YEAR,academic_year=ACADEMIC_YEAR,definition=POLICY['income'])


def assessment_flags(entry):
    r=entry['raw']
    if r[47]not in {'Y','N'}or r[49]not in {'YES','NO'}:
        raise ValueError('Unknown native attribution/charter flag')
    return dict(source='assessment',source_row=entry['source_row'],provider=r[3],role='campus'if r[3]in('',None)else'provider_specific_virtual',collocated=r[47],collocated_number=r[48],charter=r[49],title_i=r[50],alternative_ESE=r[51],school_type=r[52],letter_grade=r[21],percent_tested=r[20],published_economic_disadvantage=r[53])


def outcome_evidence(entry, subject, *, scope, income, native_scope):
    raw=None if entry is None else entry['raw'];rate=None if raw is None else published_rate(raw[SUBJECT_COLUMNS[subject]])
    reason=('Native SchoolGrades achievement component not reported'if raw is None else'Provider-specific virtual result lacks matching provider income'if raw[3]not in('',None)else'Collocated combined result cannot match one school income'if raw[47]=='Y'else'Native achievement component unavailable or fewer than10eligible students'if rate is None else None)
    native_reason='Native enrolled grades9–12 nonzero/protected/unavailable'if not native_scope else income['exclusion']or reason
    source_reason=scope or native_reason
    return dict(source='assessment',source_row=None if entry is None else entry['source_row'],native_achievement_field=SUBJECT_COLUMNS[subject],raw_rate=None if raw is None else raw[SUBJECT_COLUMNS[subject]],native_rate=rate,native_outcome_exclusion=reason,income_exclusion=income['exclusion'],scope_exclusion=scope,exclusion=source_reason,applicable=scope is None,usable=source_reason is None,native_grade_school_usable=native_reason is None,tested=None,valid_scores=None,sampling_variance=None,sampling_interval_available=False,ten_valid_scored_floor_certified=False)


def ccd_membership_evidence(total, grades):
    values=[]
    for e in grades:
        raw=e['raw'];n=reported_count(raw)
        if raw['GRADE']=='Not Specified'and raw['STUDENT_COUNT']=='0'and raw['DMS_FLAG']=='Derived':n=0
        values.append(dict(grade=raw['GRADE'],source_row=e['source_row'],raw_count=raw['STUDENT_COUNT'],flag=raw['DMS_FLAG'],reported_count=n))
    n=None if total is None else reported_count(total['raw']);full=sum(v['reported_count']for v in values)if values and all(v['reported_count']is not None for v in values)else None
    if full is not None and n is not None and full!=n:raise ValueError('Original CCD school grade counts do not reconcile to its own total')
    return dict(total_source_row=None if total is None else total['source_row'],reported_total=n,grade_values=values,full_grade_sum=full)


def summarize(links, predicate, basis):
    rows=[r for r in links if predicate(r)];subjects={}
    for s in ['math','reading','combined']:
        eligible=[r for r in rows if r['subjects'][s]['usable']];xs=[r['income']['percentage']for r in eligible]
        subjects[s]=dict(applicable=sum(r['subjects'][s]['applicable']for r in rows),usable=len(eligible),eligible_school_ids=[r['school_id']for r in eligible],eligible_ncessch=[r['ncessch']for r in eligible],exclusions=dict(sorted(Counter(r['subjects'][s]['exclusion']for r in rows if not r['subjects'][s]['usable']).items())),verified_valid_score_counts=0,ten_valid_scored_floor_certified=False,model_sampling_intervals_available=False,prospective30school_floor_met=len(eligible)>=30,income=dict(minimum=min(xs)if xs else None,maximum=max(xs)if xs else None,distinct=len(set(xs)),sample_standard_deviation=statistics.stdev(xs)if len(xs)>1 else None),charter=dict(sorted(Counter(r['ccd_flags']['charter']for r in eligible).items())),school_type=dict(sorted(Counter(r['ccd_flags']['school_type']for r in eligible).items())))
    return dict(profiles=len(rows),school_ids=[r['school_id']for r in rows],membership_basis=basis,subjects=subjects)


SUBJECT_COLUMNS={'math':9,'reading':6}
INCOME_COLUMNS={'denominator':4,'free':5,'reduced':6,'provision2':7,'direct':8}
RUNTIME_CONTRACT_SHA='c7e51f8aa1f2fa6c92697bb08ea5669182a4af977406ab32bc434745a1f301ee'


def runtime_contract():
    return dict(lea=LEA,native_lea=NATIVE_LEA,native_district=NATIVE_DISTRICT,year=YEAR,academic_year=ACADEMIC_YEAR,
        tables=TABLES,operational=sorted(OPERATIONAL),grades=GRADES,enrolled_grades=ENROLLED_GRADES,
        subjects=SUBJECT_COLUMNS,income=INCOME_COLUMNS,policy=POLICY,planning=PLANNING,sources=SOURCES,
        complete_original_metadata_digests=ORIGINAL_METADATA,original_inventories=ORIGINAL_INVENTORIES,
        native_types=NATIVE_COLUMN_TYPES,state_extract_sha256=STATE_EXTRACT_SHA,state_snapshot_sha256=STATE_SNAPSHOT_SHA,
        raw_fingerprint=RAW_INPUT_SHA,schema_fingerprint=ORIGINAL_SCHEMA_SHA,
        definition_fingerprint=DEFINITION_INPUT_SHA,identity_fingerprint=ORIGINAL_IDENTITY_SHA)


def require_runtime_contract():
    if (POLICY_SHA!='df44f3c3f7e1e60874763e20cbe3961fd70a8f44d378a63848625d5ee8dce7c3'or fingerprint(POLICY)!='df44f3c3f7e1e60874763e20cbe3961fd70a8f44d378a63848625d5ee8dce7c3'
        or RUNTIME_CONTRACT_SHA!='c7e51f8aa1f2fa6c92697bb08ea5669182a4af977406ab32bc434745a1f301ee'or fingerprint(runtime_contract())!='c7e51f8aa1f2fa6c92697bb08ea5669182a4af977406ab32bc434745a1f301ee'):
        raise ValueError('Frozen current Lee source identity/year/header/subject/income/type/policy contract changed')


def require_current_originals():
    require_runtime_contract()
    for key,meta in SOURCES.items():
        path=ROOT/meta['path'];digest=hashlib.sha256()
        if path.stat().st_size!=meta['bytes']:raise ValueError('Lee complete current original size changed: '+key)
        with path.open('rb')as stream:
            for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
        if digest.hexdigest()!=meta['sha256']:raise ValueError('Lee complete current original fingerprint changed: '+key)


def load_florida(path=ROOT/'data/source/florida.json'):
    require_runtime_contract()
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=STATE_EXTRACT_SHA:raise ValueError('Complete immutable Florida source extract changed')
    snapshot=json.loads(data)
    if fingerprint(snapshot)!=STATE_SNAPSHOT_SHA or (snapshot['state'],type(snapshot['year']),snapshot['year'],snapshot['academic_year'])!=('FL',int,2025,'2024-25'):raise ValueError('Florida secondary source/year/payload fingerprint changed')
    return snapshot


def derive(document, snapshot):
    require_current_originals()
    if fingerprint(snapshot)!=fingerprint(load_florida()):raise ValueError('Cached Florida evidence differs from current complete frozen source')
    if fingerprint(snapshot)!=STATE_SNAPSHOT_SHA:raise ValueError('Complete historical Florida snapshot changed')
    contract=dict(schema_version=1,state='FL',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,planning=PLANNING,state_extract=dict(path='data/source/florida.json',sha256=STATE_EXTRACT_SHA))
    if fingerprint({k:document.get(k)for k in contract})!=fingerprint(contract):raise ValueError('Source-only identity/provenance/year/scope/approval contract changed')
    inputs=document['raw_inputs']
    if fingerprint(inputs)!=RAW_INPUT_SHA:raise ValueError('Complete retained original rows/headers/definitions/planning fingerprint changed')
    metadata={k:{f:v for f,v in inputs[k].items()if f!='records'}for k in TABLES}
    if fingerprint(metadata)!=ORIGINAL_SCHEMA_SHA or fingerprint(inputs['definitions'])!=DEFINITION_INPUT_SHA or set(inputs)!=set(TABLES)|{'definitions','planning'}:raise ValueError('Original schema/primary definition evidence omitted or changed')
    for name in TABLES:
        section=inputs[name]
        if fingerprint(metadata[name])!=ORIGINAL_METADATA[name]or len(section['records'])!=ORIGINAL_INVENTORIES[name]:raise ValueError('Original complete table metadata/inventory changed')
        seen=set()
        for e in section['records']:
            if type(e['source_row'])is not int or e['source_row']<(section['data_start_row']if name.startswith('native_')else 2)or e['source_row']in seen:raise ValueError('Original source row references require strict positive unique integers')
            seen.add(e['source_row']);r=e['raw']
            if name.startswith('native_'):
                if type(r)is not list or len(r)!=len(NATIVE_COLUMN_TYPES[name])or any(type(v).__name__ not in NATIVE_COLUMN_TYPES[name][i]for i,v in enumerate(r)):raise ValueError('Original native cell types/columns changed; booleans and integral floats cannot substitute')
                native_identity(r)
                if name=='native_assessment':
                    assessment_flags(e)
                    for field in SUBJECT_COLUMNS.values():published_rate(r[field])
                elif name=='native_grades':enrolled_evidence(e)
                else:income_evidence(e)
            elif type(r)is not dict or set(r)!=set(section['header'])or any(type(v)is not str for v in r.values()):raise ValueError('Original CCD CSV fields must retain exact string cells and complete headers')
    if identity_fingerprint(inputs)!=ORIGINAL_IDENTITY_SHA:raise ValueError('Original exact identities, grades, provider scopes or row references changed')
    directory={};totals={};grades=defaultdict(list)
    for e in inputs['directory']['records']:
        key=ccd_identity(e['raw']);nces=e['raw']['NCESSCH']
        if key in directory or any(x['raw']['NCESSCH']==nces for x in directory.values())or e['raw']['UPDATED_STATUS']not in {str(n)for n in range(1,9)}:raise ValueError('Duplicate original CCD identity or unknown status')
        directory[key]=e
    by_nces={e['raw']['NCESSCH']:e for e in directory.values()}
    for e in inputs['membership']['records']:
        r=e['raw'];key=ccd_identity(r)
        if key not in directory or r['NCESSCH']!=directory[key]['raw']['NCESSCH']:raise ValueError('Original school membership crosses attached roster identity')
        if r['TOTAL_INDICATOR']=='Education Unit Total':
            if key in totals or any(r[k]!='No Category Codes'for k in ['GRADE','RACE_ETHNICITY','SEX']):raise ValueError('Duplicate/demographic original school total')
            totals[key]=e
        elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade':
            special=r['GRADE']=='Not Specified'and r['DMS_FLAG']=='Derived'and r['STUDENT_COUNT']=='0'
            if r['GRADE']in[x['raw']['GRADE']for x in grades[key]]or not special and any(r[k]!='No Category Codes'for k in ['RACE_ETHNICITY','SEX']):raise ValueError('Duplicate/demographic original school grade row')
            grades[key].append(e)
        else:raise ValueError('Unexpected CCD membership population')
    if len(inputs['lea_directory']['records'])!=1:raise ValueError('Exactly one district directory row required')
    ccd_identity(inputs['lea_directory']['records'][0]['raw'],district=True)
    lea_totals=[];lea_grades=[]
    for e in inputs['lea_membership']['records']:
        r=e['raw'];ccd_identity(r,district=True)
        if r['TOTAL_INDICATOR']=='Education Unit Total':
            if any(r[k]!='No Category Codes'for k in ['GRADE','RACE_ETHNICITY','SEX']):raise ValueError('Unexpected district demographic total')
            lea_totals.append(e)
        elif r['TOTAL_INDICATOR']=='Subtotal 4 - By Grade':
            special=r['GRADE']=='Not Specified'and r['STUDENT_COUNT']=='0'and r['DMS_FLAG']=='Derived'
            if r['GRADE']in[x['raw']['GRADE']for x in lea_grades]or not special and any(r[k]!='No Category Codes'for k in ['RACE_ETHNICITY','SEX']):raise ValueError('Unexpected duplicate/demographic district grade')
            lea_grades.append(e)
        else:raise ValueError('Unexpected district membership population')
    if len(lea_totals)!=1:raise ValueError('Exactly one original district total required')
    lea=ccd_membership_evidence(lea_totals[0],lea_grades)
    native={};incomes={};assessments=defaultdict(list)
    for name,target in [('native_grades',native),('native_income',incomes)]:
        for e in inputs[name]['records']:
            key=native_identity(e['raw'])
            if key in target:raise ValueError('Duplicate original native school registry/income identity')
            target[key]=e
    seen=set()
    for e in inputs['native_assessment']['records']:
        key=native_identity(e['raw']);provider=e['raw'][3]
        if (key,provider)in seen:raise ValueError('Duplicate original campus/provider assessment identity')
        seen.add((key,provider));assessments[key].append(e)
    state_profiles={p['id']:p for p in snapshot['profiles']if p['id'].startswith(NATIVE_DISTRICT+'-')};state_assessment=[e for e in snapshot['assessments']if e['id'].startswith(NATIVE_DISTRICT+'-')]
    expected_profiles=[dict(id=k,grades=e['raw'],grade_row=e['source_row'],income_raw=None if k not in incomes else incomes[k]['raw'],income_row=None if k not in incomes else incomes[k]['source_row'])for k,e in native.items()]
    expected_assessment=[dict(id=native_identity(e['raw']),row=e['source_row'],raw=e['raw'])for e in inputs['native_assessment']['records']]
    if fingerprint(list(state_profiles.values()))!=fingerprint(expected_profiles)or fingerprint(state_assessment)!=fingerprint(expected_assessment):raise ValueError('Every original native row/reference differs from complete frozen Florida secondary')
    links=[]
    for key,e in directory.items():
        r=e['raw'];offered=offered_evidence(r);op=r['UPDATED_STATUS']in OPERATIONAL;entry=native.get(key);enrolled=enrolled_evidence(entry,offered);inc=income_evidence(incomes.get(key));campuses=[a for a in assessments[key]if a['raw'][3]in('',None)]
        if len(campuses)>1:raise ValueError('Unique exact campus achievement required')
        campus=campuses[0]if campuses else None
        exclusion=('CCD status nonoperational'if not op else'No same-year Fall Survey2 native profile'if entry is None else'CCD offered configuration is not verified pure lower grades'if offered['scope']!='ES'else'No offered grade3–8 in primary-only configuration'if not offered['offered_tested_grades']else'Native grades9–12 nonzero/protected/unavailable'if not enrolled['native_grade_school_contract']else'Onlyzero/unavailable native enrolled grades3–8; tested-grade scope unverified'if not enrolled['positive_or_protected_tested_grades']else None)
        native_scope=entry is not None and enrolled['native_grade_school_contract']
        subjects={s:outcome_evidence(campus,s,scope=exclusion,income=inc,native_scope=native_scope)for s in ['math','reading']}
        subjects['combined']=dict(applicable=all(v['applicable']for v in subjects.values()),usable=all(v['usable']for v in subjects.values()),native_grade_school_usable=all(v['native_grade_school_usable']for v in subjects.values()),native_rate=(subjects['math']['native_rate']+subjects['reading']['native_rate'])/2 if all(v['native_grade_school_usable']for v in subjects.values())else None,exclusion='; '.join(s+': '+v['exclusion']for s,v in subjects.items()if v['exclusion'])or None,tested=None,valid_scores=None,sampling_variance=None,sampling_interval_available=False,ten_valid_scored_floor_certified=False,definition=POLICY['combined'])
        links.append(dict(school_id=key,ncessch=r['NCESSCH'],native_school_id=r['ST_SCHID'],name=r['SCH_NAME'],directory_source_row=e['source_row'],operational=op,ccd_flags=dict(status=r['UPDATED_STATUS'],status_text=r['UPDATED_STATUS_TEXT'],charter=r['CHARTER_TEXT'],school_type=r['SCH_TYPE_TEXT']),offered=offered,native_profile_matched=entry is not None,native_grade_source_row=None if entry is None else entry['source_row'],enrolled=enrolled,ccd_membership=ccd_membership_evidence(totals.get(key),grades[key]),income=inc,assessment_flags=[assessment_flags(a)for a in assessments[key]],campus_assessment_source_row=None if campus is None else campus['source_row'],native_charter_agreement=None if campus is None else({'YES':'Yes','NO':'No'}[campus['raw'][49]]==r['CHARTER_TEXT']),source_profile_eligible=exclusion is None,population_exclusion=exclusion,subjects=subjects))
    prospective=[l for l in links if l['source_profile_eligible']]
    cohorts={'prospective_tested_grade_profiles':summarize(links,lambda l:l['source_profile_eligible'],'Exact operational pure offered lower grades with positive/protected native grades3–8 and explicitzero9–12.'),'operational_pure_lower_directory':summarize(links,lambda l:l['operational']and l['offered']['scope']=='ES','Directory evidence only including primary/missing/zero-tested records.'),'high_only':summarize(links,lambda l:l['operational']and l['offered']['scope']=='HS','High offered configurations remain unreleased.'),'mixed_grade':summarize(links,lambda l:l['operational']and l['offered']['scope']=='mixed','Mixed offered configurations remain unreleased.'),'primary_only':summarize(links,lambda l:l['operational']and l['offered']['scope']=='ES'and not l['offered']['offered_tested_grades'],'Primary offered configuration; source above-grade scope does not establish participation.'),'native_zero_high_registry':dict(profiles=sum(l['operational']and l['enrolled']is not None and l['enrolled']['native_grade_school_contract']for l in links),usable_native_subjects={s:sum(l['operational']and l['subjects'][s]['native_grade_school_usable']for l in links)for s in ['math','reading','combined']},note='Native zero-high contract is broader than separately proposed tested-grade district population; no additional source approval.')}
    potential={'ES':[],'HS':[]}
    for key,e in directory.items():
        if e['raw']['UPDATED_STATUS']in OPERATIONAL:
            level=planning.potential_cohort(e['raw'],None if key not in totals else totals[key]['raw'],{e['raw']['GRADE']:e['raw']for e in grades[key]})
            if level:potential[level].append(e['raw']['NCESSCH'])
    potential={k:sorted(v)for k,v in potential.items()};recorded=inputs['planning']['record']
    if any(type(recorded.get(k))is not int or recorded[k]<=0 for k in ['enrollment','school_directory_operational_count','directory_source_row','membership_source_row'])or type(recorded.get('potential_cohorts'))is not dict or any(type(v)is not int or v<0 for v in recorded['potential_cohorts'].values()):raise ValueError('Planning counts/row references require strict integer types')
    if recorded['nces_lea_id']!=LEA or recorded['native_lea_id']!=NATIVE_LEA or recorded['state']!='FL'or recorded['potential_school_ids']!=potential or recorded['potential_cohorts']!={k:len(v)for k,v in potential.items()}or recorded['enrollment']!=lea['reported_total']or recorded['membership_raw']!=lea_totals[0]['raw']or recorded['membership_source_row']!=lea_totals[0]['source_row']or recorded['directory_source_row']!=inputs['lea_directory']['records'][0]['source_row']or any(inputs['lea_directory']['records'][0]['raw'][k]!=v for k,v in recorded['directory_raw'].items())or recorded['school_directory_operational_count']!=sum(l['operational']for l in links):raise ValueError('Original CCD district/school records fail exact planning discovery replay')
    outside=[dict(school_id=k,ncessch=None,grade_source_row=e['source_row'],income=income_evidence(incomes.get(k)),enrolled=enrolled_evidence(e),assessment_rows=[a['source_row']for a in assessments[k]],exclusion='Native district school without exact same-year CCD operational directory identity')for k,e in native.items()if k not in directory or not directory[k]['raw']['UPDATED_STATUS']in OPERATIONAL]
    operational=[l for l in links if l['operational']];school_sum=sum(l['ccd_membership']['reported_total']for l in operational if l['ccd_membership']['reported_total']is not None)
    differences=[l['school_id']for l in operational if l['enrolled']is not None and(l['enrolled']['offered_with_explicit_zero_enrollment']or l['enrolled']['positive_or_protected_without_offer'])]
    coverage=dict(complete_omitted_original_inventories={k:dict({a:b for a,b in inputs[k]['complete_district_inventory'].items()if a not in {'omitted_identity_population_inventory','omitted_source_ordinals'}},complete_inventory_path='raw_inputs.'+k+'.complete_district_inventory')for k in ['directory','lea_directory','membership','lea_membership']},source_rows={k:len(inputs[k]['records'])for k in TABLES},original_records=sum(len(inputs[k]['records'])for k in TABLES),original_typed_cells=sum(sum(len(e['raw'])for e in inputs[k]['records'])for k in TABLES),ccd_directory=len(links),operational_roster=len(operational),nonoperational_directory=len(links)-len(operational),status=dict(sorted(Counter(l['ccd_flags']['status_text']for l in links).items())),operational_offered_scope=dict(sorted(Counter(l['offered']['scope']for l in operational).items())),native_fall_profiles=len(native),native_income_rows=len(incomes),native_assessment_rows=len(inputs['native_assessment']['records']),exact_operational_fall_matches=sum(l['native_profile_matched']for l in operational),operational_without_native_fall_ids=[l['school_id']for l in operational if not l['native_profile_matched']],outside_native_profile_ids=[l['school_id']for l in outside],native_income_without_fall_ids=sorted(set(incomes)-set(native)),native_assessment_without_operational_directory=[e['source_row']for e in inputs['native_assessment']['records']if native_identity(e['raw'])not in {l['school_id']for l in operational}],provider_assessment_rows=sum(a['raw'][3]not in('',None)for a in inputs['native_assessment']['records']),collocated_assessment_rows=sum(a['raw'][47]=='Y'for a in inputs['native_assessment']['records']),prospective_source_profiles=len(prospective),prospective_usable={s:cohorts['prospective_tested_grade_profiles']['subjects'][s]['usable']for s in ['math','reading','combined']},prospective_usable_income=sum(l['income']['percentage']is not None for l in prospective),income_exclusions=dict(sorted(Counter(l['income']['exclusion']for l in prospective if l['income']['exclusion']).items())),offered_enrolled_disagreement_profiles=len(differences),protected_native_grade_profiles=sum(l['enrolled']is not None and bool(l['enrolled']['protected_grades'])for l in operational),protected_native_grade_cells=sum(len(l['enrolled']['protected_grades'])for l in operational if l['enrolled']is not None),campus_charter_disagreements=sum(l['native_charter_agreement']is False for l in links),district_ccd_enrollment=lea['reported_total'],operational_ccd_enrollment_sum=school_sum,district_minus_operational_enrollment=lea['reported_total']-school_sum,planning_potential_cohorts={k:len(v)for k,v in potential.items()},prospective_not_in_planningES=sorted({l['ncessch']for l in prospective}-set(potential['ES'])),planningES_outside_prospective=sorted(set(potential['ES'])-{l['ncessch']for l in prospective}),verified_valid_score_counts=0,ten_valid_scored_floor_certified=False,model_sampling_intervals_available=False,independent_numerical_diagnostics_required=True,canonical_integration_pending=True,source_and_model_approvals=False)
    return dict(roster_links=links,outside_roster_profiles=outside,nonoperational_directory=[e for e in inputs['directory']['records']if e['raw']['UPDATED_STATUS']not in OPERATIONAL],native_income_without_fall_registry=[e for k,e in incomes.items()if k not in native],offered_enrolled_disagreement_school_ids=differences,cohorts=cohorts,coverage=coverage,source_definition_evidence=inputs['definitions'],raw_schema_sha256=ORIGINAL_SCHEMA_SHA,raw_definition_sha256=DEFINITION_INPUT_SHA,source_policy_sha256=POLICY_SHA,original_identity_projection_sha256=ORIGINAL_IDENTITY_SHA)


def validate(document, snapshot=None):
    snapshot=load_florida()if snapshot is None else snapshot
    expected=dict(schema_version=1,state='FL',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,planning=PLANNING,raw_inputs=document['raw_inputs'],state_extract=dict(path='data/source/florida.json',sha256=STATE_EXTRACT_SHA))
    expected.update(derive(document,snapshot))
    if fingerprint(document)!=fingerprint(expected):raise ValueError('Complete source metadata/raw/derived identities/cohort/income/missingness replay differs')
    return expected['coverage']


def read_ccd_rows(source,needed):
 path=ROOT/SOURCES[source]['path'];member=path.stem+'.csv';process=subprocess.Popen(['unzip','-p',str(path),member],stdout=subprocess.PIPE,text=True,encoding='utf-8-sig');records=[];omitted=[];digest=hashlib.sha256(b'[');rows=0;cells=0;categories=Counter()
 try:
  reader=csv.DictReader(process.stdout)
  for number,row in enumerate(reader,2):
   if row['LEAID']!=LEA and row['ST_LEAID']!=NATIVE_LEA:continue
   rows+=1
   if needed(row):records.append(dict(source_row=number,raw=row))
   else:
    if omitted:digest.update(b',')
    digest.update(json.dumps(dict(source_row=number,raw=row),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
    keys=['SCHOOL_YEAR','ST','LEAID','ST_LEAID','ST_SCHID','NCESSCH','GRADE','RACE_ETHNICITY','SEX','TOTAL_INDICATOR','DMS_FLAG']
    omitted.append(dict(source_row=number,identity_population={k:row[k]for k in keys if k in row}));cells+=len(row);categories[row.get('TOTAL_INDICATOR','not_applicable')]+=1
  assert process.wait()==0
  digest.update(b']')
  return dict(source_id=source,member=member,header_source_row=1,header=reader.fieldnames,records=records,complete_district_inventory=dict(original_district_rows=rows,retained_rows=len(records),omitted_rows=len(omitted),omitted_source_ordinals=[r['source_row']for r in omitted],omitted_identity_population_inventory=omitted,omitted_typed_cells=cells,omitted_raw_ordinal_sha256=digest.hexdigest(),omitted_populations=dict(sorted(categories.items()))))
 finally:
  process.stdout.close()
  if process.poll()is None:process.terminate();process.wait()

def extract_raw_inputs():
    require_runtime_contract();require_current_originals()
    inputs={}
    for table,source in [('directory','ccd_school_directory'),('lea_directory','ccd_lea_directory'),('membership','ccd_school_membership'),('lea_membership','ccd_lea_membership')]:
        inputs[table]=read_ccd_rows(source,(lambda r:True)if 'directory'in table else lambda r:r['TOTAL_INDICATOR']in{'Education Unit Total','Subtotal 4 - By Grade'})
    for table,source,sheet,start,header in [('native_grades','grades','School',3,2),('native_income','income','2425 FS3_Schl',4,3),('native_assessment','assessment','School Grades 2025',5,4)]:
        book=openpyxl.load_workbook(ROOT/SOURCES[source]['path'],read_only=True,data_only=True)
        try:
            values=list(book[sheet].values)
            section=dict(source_id=source,worksheet=sheet,data_start_row=start,header_rows=[list(v)for v in values[:header]],records=[dict(source_row=n,raw=list(r))for n,r in enumerate(values,1)if n>=start and r[0]is not None and native_code(r[0],2)==NATIVE_DISTRICT])
            if table=='native_income':section['notes']=[list(v)for v in book['NOTES'].values]
            inputs[table]=section
        finally:book.close()
    from pypdf import PdfReader
    inputs['definitions']={}
    for key,numbers in [('grade-guide',[1,5,7,8,9,10,11,12,13,14,15,37]),('lunch-guide',[1,2,3]),('school-code',[1,2,3]),('district-code',[1,2])]:
        pages=PdfReader(ROOT/SOURCES[key]['path']).pages
        inputs['definitions'][key]=dict(source_id=key,document={'grade-guide':'2024–25 School Grades calculation guide','lunch-guide':'2024–25 Lunch Status data element146025','school-code':'2024–25 School Number Current Enrollment data element172825','district-code':'2024–25 District Number Current Enrollment data element115225'}[key],original_pages=[dict(page_number=n,text=pages[n-1].extract_text()or'')for n in numbers])
    payload=json.loads((ROOT/PLANNING['source']).read_text());record=next(a for a in payload['agencies']if a['nces_lea_id']==LEA);fields=['nces_lea_id','state','native_lea_id','enrollment','enrollment_flag','school_directory_operational_count','potential_cohorts','potential_school_ids','directory_raw','directory_source_row','membership_raw','membership_source_row'];inputs['planning']=dict(source=PLANNING['source'],sources=payload['sources'],record={k:record[k]for k in fields})
    return inputs

def extract(output=OUTPUT):
    snapshot=load_florida();inputs=extract_raw_inputs();document=dict(schema_version=1,state='FL',year=YEAR,academic_year=ACADEMIC_YEAR,nces_lea_id=LEA,native_lea_id=NATIVE_LEA,native_district_id=NATIVE_DISTRICT,status='audit_pending',scope='source_cohort_audit_only',approved_for_source=False,approved_for_modeling=False,sources=SOURCES,policy=POLICY,planning=PLANNING,raw_inputs=inputs,state_extract=dict(path='data/source/florida.json',sha256=STATE_EXTRACT_SHA));document.update(derive(document,snapshot));validate(document,snapshot);Path(output).write_text(json.dumps(document,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n');return document['coverage']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args();print(json.dumps(extract(args.output)if args.extract else validate(json.loads(args.output.read_text())),sort_keys=True))

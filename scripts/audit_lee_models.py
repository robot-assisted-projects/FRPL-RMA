"""Replay Lee School Grades point-only fits; no import or publication."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

import audit_lee as roster_audit
from prepare_data import fit_model

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/source/lee-model-audit.json'
ROSTER = roster_audit.OUTPUT
ROSTER_SHA = '2cc80d2dd92e5c365f8fbadc978c17260e71cab7d01f23074a731d97c9521029'
ROSTER_BYTES = 6093628
SOURCE_CODE = ROOT / 'scripts/audit_lee.py'
SOURCE_CODE_SHA = 'eef12fe55bd2f93a7fcf9e2ca7e11e29d9e395147e288005059f88f4383fb552'
SOURCE_TESTS = ROOT / 'tests/test_lee_audit.py'
SOURCE_TESTS_SHA = 'abcaf6e628d53a8925e40b12c978794283ded126e9e876003ec2616e2cacb44c'
SOURCE_POLICY_SHA = 'df44f3c3f7e1e60874763e20cbe3961fd70a8f44d378a63848625d5ee8dce7c3'
SOURCE_RAW_SHA = '2355a0fcae20dcd27b5c60c2469ef390c4129bbda872527366b0de66c2e35299'
SOURCE_SCHEMA_SHA = '3c3d1e2a94a7b45975a61276e27bfc5806931bec97aa3a22410eed34e27c3e4d'
SOURCE_DEFINITION_SHA = 'e0728b5b883a46e74b5cd3d652a59f0def259bdc356f74a7ae2bba2396b793cf'
SOURCE_IDENTITY_SHA = '032472bb83e34a5fa7307b3df6f35b95fc6162c5f2f3b5c5e5c6ede2123b26de'
SOURCE_RUNTIME_SHA = 'c7e51f8aa1f2fa6c92697bb08ea5669182a4af977406ab32bc434745a1f301ee'
SOURCE_SECONDARY_SHA = '523afad888444e875fc8d06486b20240896341d55b14d9484e8b935888f66daf'
SOURCE_SNAPSHOT_SHA = 'f08640b8501e323cfc9298057500c4087e543bacdfda5fa4a6edb8a49778cfb8'
MIN_SCHOOLS = 30
ABS_TOLERANCE = 2e-10
REL_TOLERANCE = 2e-10
VERIFY_TOLERANCE = 2e-9
SUBJECTS = ['math', 'reading', 'combined']
ASSESSMENT = '2024–25 FAST/BEST/FAA School Grades published accountable achievement'
STANDARD = 'Original Level 3 or above FAST/BEST/Access/eligible FAA achievement with full-year, home-zoned, ELL and exemption rules; Datafolio and percent-tested participation remain separate.'
SUBJECT_FIELDS = {'math': 9, 'reading': 6}
SUBJECT_LABELS = {'math': 'Mathematics Achievement', 'reading': 'English Language Arts Achievement'}
INCOME_FIELDS = [4, 5, 6, 7, 8]
POLICY = {'identity': 'Exact original2024–25 CCD LEA1201080 /FL-36 and FDOE district36 identities. The original2024–25 FDOE elements115225 and172825 document two-digit district and four-digit school widths. Only strictly numeric original integer/digit school codes use that documented zero padding; remove only the explicit FL- prefix from exact CCD FL-36-####. Preserve authoritative full12-digit NCES IDs separately; names, corrected digits, suffix guesses and float/bool substitutions never establish ownership.', 'population': 'Prospective pure lower profiles require exact operational CCD ownership; complete unadjusted reported PK–8 offered flags with a grade3–8 offer and no9–13/UG/AE; native Fall Survey2 explicit zero in every grade9–12 and at least one positive or protected-positive enrolled grade3–8. Offered and enrolled grades remain separate. Primary, zero-tested, high, mixed and uncertain configurations stay outside. Planning, income extremes, school type, charter status and diagnostic quality never select scope. Original above-grade testing scope does not establish participation in a profile with only zero enrolled tested grades.', 'income': 'Florida 2024–25 Final Survey 3 (February) raw individual Lunch Status counts: D/F free eligibility + 3/E reduced eligibility + C/R CEP direct certification, divided by same-survey enrolled students (PK–12). Never uses the USDA 1.6-adjusted federal funding numerator or published school-grade economic percentage. CEP N means not individually identified eligible and is excluded from the numerator. Provision 2 code 4 reports all enrolled students, so schools with nonzero or masked code 4 have unavailable income. At CEP schools this proxy counts direct certification/household extension rather than a complete income survey of all families; undercount and reporting coverage are unknown. No other-year backfill.', 'income_codes': 'The2024–25 Lunch Status146025 primary definition requires district option6/9 conversions toC/D before reporting. Use each school’s own February Final Survey3 PK–12 denominator and original D/F+3/E+C/R individual counts only when Provision2 code4 is explicit zero. Preserve funding columns9–11 as separate raw evidence, never a model income measure. No USDA1.6 multiplier, School Grades economic percentage, other-year income or enrollment substitution; CEP individual identification coverage remains unknown.', 'assessment': '2024–25 native School Grades English Language Arts Achievement and Mathematics Achievement components: Level 3 or above / valid assessed students under Florida full-year-enrollment and home-zoned attribution rules, including eligible FAA Performance Task but excluding FAA Datafolio. ELA FAST PM3 grades 3–10 and Math FAST PM3 grades 3–8 plus B.E.S.T./Access Algebra 1/Geometry EOCs; this cohort enrolls no grades 9–12 in the same-year Survey 2 registry. ELL included after two US-school years; medical/extraordinary exemptions excluded. Components require at least 10 eligible students. Native whole-percent rates only; score denominators absent, so all model sampling intervals unavailable. Collocated combined results and provider-specific virtual rates are excluded from individual-school matches.', 'native_population': 'Original School Grades2025 Math Achievement column9 and ELA Achievement column6 are published whole Level3-or-above accountable rates. Keep exact native valid accountable population and full-year, home-zoned, ELL-after-two-US-school-years, medical-exemption and eligible FAA performance rules. Preserve prescribed FAST PM3/BEST/Access EOC and above-grade scope; Datafolio and participation remain separate. No grade/component averaging, count-ratio substitution or inferred test administration membership.', 'suppression': 'Protected native Fall counts remain unavailable numeric counts with protected-positive presence, never zero or reconstructed. Missing/masked income or achievement remains unavailable. Explicit zero remains zero. Never complement masks or backfill another year.', 'counts': 'Published School Grades achievement provides no verified valid-score denominators. The primary guide at-least-ten-eligible component condition does not certify ten valid-scored pupils. All valid-score counts, variances and intervals remain null/unavailable and the scored floor remains uncertified. Enrollment, percent tested, participation, federal95%-adjustment and studentization never substitute. The existing count hold is retained without new speculative investigations.', 'combined': 'Equal mean of usable original published Math and ELA rates with own same-year individual income; not the percentage proficient in both.', 'income_enrollment_discrepancy': 'Own February Final Survey3 PK–12 denominator is distinct from Fall Survey2, CCD membership and full-year accountable performance. Retain every original school/district total and any exact mismatch without assigning a cause or inventing an identity. None supplies an assessment valid-score denominator.', 'eligibility': 'Reconstruct exact original CCD and FDOE district36 identities, operational status and complete pure lower offered flags. Require native Fall grades9–12 to be explicit zero and at least one grade3–8 positive or protected-positive. Compute own February D/F +3/E +C/R count ratio only with explicit-zero Provision2 code4. Select exact campus published Math/ELA fields without provider-specific or collocated attribution. Retain all78 eligible profiles, all11 charter schools and THE ISLAND SCHOOL36-4100 original0% income. High/mixed/primary/inactive/missing-native records and count holds remain separate; names, charters, income extremes, influence and residuals never select membership.', 'models': 'Separate unweighted centered2024–25 Lee grade-school Math, ELA and Combined OLS. Combined independently fits the paired78 original-rate means with its own residual scale and external studentization. Each model verifies all78 explicit deleted-school fits,234 across the three models. Equal subject cohorts may yield linear coefficient averages but never justify averaging residual scores. No weights, enrollment adjustment, shrinkage, fit-driven exclusions or national pooling.', 'minimum_usable_subject_schools': 30, 'studentization': 'Externally studentized residuals use every explicit deleted-school fit and N−3 residual degrees of freedom, independent centered full fits and held-out leverage. Cook distance and prediction sensitivity over the observed income range are descriptive, never exclusions or clamping.', 'intervals': 'All valid-score counts, sampling variances and interval endpoints are null modelwide; the ten-valid-scored floor is uncertified. An internal zero variance vector is solely a point-estimate computational sentinel, never an uncertainty estimate.', 'compact_provenance': 'Complete committed immutable Lee source retains all1,449 needed original records/34,610 typed cells, complete headers, notes, primary definitions and outside identities, plus all exact omitted original ordinal/identity/population inventories and raw digests. Whole blob, source code/tests/policy/raw/schema/definition/identity/current runtime fingerprints and fresh semantic replay are required on every numerical replay, including supplied expected fits. Compact exact original table/workbook/worksheet/row/column references replace repeated raw tables/PDFs; no expectation cache can become authority.', 'release': 'Numerical audit only pending independent review and separate canonical/browser integration. Historical source and numerical source/modeling approvals remain false; high/mixed/primary/missing/closed/unmatched scopes and count holds remain unreleased.'}
NUMERIC_POLICY_SHA = 'dc905cc7323365f541ac0c7f40b02e0f4921437a17b7a5b721f4b3b580401ff5'
RUNTIME_CONTRACT_SHA = 'ab5a89b235346e3a242f7b09c7951f233e00f54cf09ad4e609b5bf075c5d3f4d'


def runtime_contract():
    return dict(minimum=MIN_SCHOOLS, subjects=SUBJECTS, assessment=ASSESSMENT,
                standard=STANDARD, subject_fields=SUBJECT_FIELDS, subject_labels=SUBJECT_LABELS,
                income_fields=INCOME_FIELDS, absolute_tolerance=ABS_TOLERANCE,
                relative_tolerance=REL_TOLERANCE, verify_tolerance=VERIFY_TOLERANCE,
        frozen_source=dict(path=str(ROSTER.relative_to(ROOT)),sha256=ROSTER_SHA,bytes=ROSTER_BYTES,
            code_path=str(SOURCE_CODE.relative_to(ROOT)),code_sha256=SOURCE_CODE_SHA,
            tests_path=str(SOURCE_TESTS.relative_to(ROOT)),tests_sha256=SOURCE_TESTS_SHA,
            policy=SOURCE_POLICY_SHA,raw=SOURCE_RAW_SHA,schema=SOURCE_SCHEMA_SHA,
            definitions=SOURCE_DEFINITION_SHA,identity=SOURCE_IDENTITY_SHA,runtime=SOURCE_RUNTIME_SHA,
            secondary=SOURCE_SECONDARY_SHA,snapshot=SOURCE_SNAPSHOT_SHA))


def require_runtime_contract():
    # These literal baselines also prevent an in-memory policy edit from
    # authorizing itself by repinning the public fingerprint variables.
    original_policy = 'dc905cc7323365f541ac0c7f40b02e0f4921437a17b7a5b721f4b3b580401ff5'
    original_contract = 'ab5a89b235346e3a242f7b09c7951f233e00f54cf09ad4e609b5bf075c5d3f4d'
    if (NUMERIC_POLICY_SHA != original_policy or RUNTIME_CONTRACT_SHA != original_contract
            or roster_audit.fingerprint(POLICY) != original_policy
            or roster_audit.fingerprint(runtime_contract()) != original_contract):
        raise ValueError('Frozen current Lee numerical policy/types/subject/field/minimum/source contract changed')
    roster_audit.require_runtime_contract()


def load_roster(path=ROSTER):
    require_runtime_contract()
    for source, expected, label in [(SOURCE_CODE, SOURCE_CODE_SHA, 'code'), (SOURCE_TESTS, SOURCE_TESTS_SHA, 'tests')]:
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen Lee source ' + label + ' changed; fresh numerical audit required')
    pins = [(roster_audit.fingerprint(roster_audit.POLICY), SOURCE_POLICY_SHA),
            (roster_audit.RAW_INPUT_SHA, SOURCE_RAW_SHA), (roster_audit.ORIGINAL_SCHEMA_SHA, SOURCE_SCHEMA_SHA),
            (roster_audit.DEFINITION_INPUT_SHA, SOURCE_DEFINITION_SHA), (roster_audit.ORIGINAL_IDENTITY_SHA, SOURCE_IDENTITY_SHA),
            (roster_audit.RUNTIME_CONTRACT_SHA,SOURCE_RUNTIME_SHA),(roster_audit.STATE_EXTRACT_SHA,SOURCE_SECONDARY_SHA),
            (roster_audit.STATE_SNAPSHOT_SHA,SOURCE_SNAPSHOT_SHA)]
    if any(actual != expected for actual, expected in pins):
        raise ValueError('Frozen Lee source policy/raw/schema/definition/identity pins changed')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != ROSTER_SHA or len(data) != ROSTER_BYTES:
        raise ValueError('Frozen complete Lee source artifact changed; fresh numerical audit required')
    document = json.loads(data)
    roster_audit.validate(document)
    return document


def require_frozen_roster(roster):
    if roster_audit.fingerprint(roster) != roster_audit.fingerprint(load_roster()):
        raise ValueError('In-memory Lee source differs from the complete frozen artifact')


def frozen_population(roster):
    links = roster['roster_links']; cohorts = roster['cohorts']
    return dict(complete_native_school_ids=sorted(roster_audit.native_identity(e['raw']) for e in roster['raw_inputs']['native_grades']['records']),
        complete_directory_ncessch=sorted(r['ncessch'] for r in links),
        operational_directory_ncessch=sorted(r['ncessch'] for r in links if r['operational']),
        grade_school_configuration_ids=sorted(cohorts['prospective_tested_grade_profiles']['school_ids']),
        eligible_school_ids_by_subject={s: sorted(cohorts['prospective_tested_grade_profiles']['subjects'][s]['eligible_school_ids']) for s in SUBJECTS},
        high_school_configuration_ids=sorted(cohorts['high_only']['school_ids']),
        mixed_configuration_ids=sorted(cohorts['mixed_grade']['school_ids']),
        primary_configuration_ids=sorted(cohorts['primary_only']['school_ids']),
        nonoperational_directory_ncessch=sorted(e['raw']['NCESSCH'] for e in roster['nonoperational_directory']),
        unmatched_native_school_ids=sorted(r['school_id'] for r in roster['outside_roster_profiles']),
        operational_without_native_fall_ids=sorted(roster['coverage']['operational_without_native_fall_ids']))


def original_count(value):
    if value is None or type(value) is str and value in {'*', '**', 'N/A', ''}:
        return None
    if type(value) is not int or value < 0:
        raise ValueError('Original native count requires nonnegative strict integer or mask')
    return value


def original_rate(value):
    if value is None or type(value) is str and value in {'*', '**', 'N/A', ''}:
        return None
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('Original native rate requires published whole integer percentage or mask')
    return float(value)


def table_reference(raw, table, entry, columns):
    if entry is None:
        return None
    source = raw[table]
    return dict(table=table, source_id=source['source_id'], worksheet=source['worksheet'],
                source_row=entry['source_row'], columns=columns,
                fields=[source['header_rows'][-1][i] for i in columns])


def source_references(roster, link, directory, grade, income, assessment):
    raw = roster['raw_inputs']
    return dict(roster_link_index=next(i for i, r in enumerate(roster['roster_links']) if r['school_id'] == link['school_id']),
        directory=dict(table='directory', source_id=raw['directory']['source_id'], member=raw['directory']['member'],
            source_row=directory['source_row'], fields=['SCHOOL_YEAR', 'LEAID', 'ST_LEAID', 'ST_SCHID', 'NCESSCH', 'UPDATED_STATUS', 'G_3_OFFERED', 'G_9_OFFERED']),
        native_enrollment=table_reference(raw, 'native_grades', grade, list(range(4, 18))),
        income=table_reference(raw, 'native_income', income, INCOME_FIELDS),
        outcomes={s: table_reference(raw, 'native_assessment', assessment, [0, 2, 3, SUBJECT_FIELDS[s], 20, 47, 48, 49, 52]) for s in ['math', 'reading']})


def selected_inputs(roster, subject):
    """Public selector always verifies a caller's roster against fresh originals."""
    require_frozen_roster(roster)
    return _selected_inputs_verified(roster,subject)


def _selected_inputs_verified(roster, subject):
    """Reconstruct scope, income and native rates directly from complete original records."""
    if subject not in SUBJECTS:
        raise ValueError('Only three separate grade-school subjects may be audited')
    raw = roster['raw_inputs']
    directory = {roster_audit.ccd_identity(e['raw']): e for e in raw['directory']['records']}
    grades = {roster_audit.native_identity(e['raw']): e for e in raw['native_grades']['records']}
    income = {roster_audit.native_identity(e['raw']): e for e in raw['native_income']['records']}
    assessment = defaultdict(list)
    for e in raw['native_assessment']['records']:
        assessment[roster_audit.native_identity(e['raw'])].append(e)
    inputs, exclusions, configurations = [], [], []
    required = ['math', 'reading'] if subject == 'combined' else [subject]
    for link in sorted(roster['roster_links'], key=lambda r: r['school_id']):
        key = link['school_id']; entry = directory[key]; c = entry['raw']; grade = grades.get(key)
        flags = {g: c.get('G_' + g + '_OFFERED') for g in roster_audit.GRADES}
        complete = c.get('IGOFFERED') == 'As reported' and c.get('NOGRADES') == 'No' and all(v in {'Yes', 'No'} for v in flags.values())
        native = None if grade is None else grade['raw']
        scoped = (c['UPDATED_STATUS'] in roster_audit.OPERATIONAL and complete
            and any(flags[str(g)] == 'Yes' for g in range(3, 9))
            and not any(flags[g] == 'Yes' for g in [str(n) for n in range(9, 14)] + ['UG', 'AE'])
            and native is not None and all(original_count(native[g + 5]) == 0 for g in range(9, 13))
            and any(native[g + 5] == '*' or original_count(native[g + 5]) not in {None, 0} for g in range(3, 9)))
        if scoped is not link['source_profile_eligible']:
            raise ValueError('Independent original grade configuration differs from frozen source')
        if not scoped:
            continue
        configurations.append(key)
        inc = income.get(key); inc_raw = None if inc is None else inc['raw']
        n = None if inc_raw is None else original_count(inc_raw[4])
        individual = None if inc_raw is None else [original_count(inc_raw[i]) for i in [5, 6, 8]]
        usable_income = (n not in {None, 0} and individual is not None and None not in individual
                         and original_count(inc_raw[7]) == 0 and sum(individual) <= n)
        low = sum(individual) if usable_income else None
        campuses = [e for e in assessment[key] if e['raw'][3] in {'', None}]
        if len(campuses) > 1:
            raise ValueError('Duplicate original exact campus achievement')
        campus = campuses[0] if campuses else None
        rates = {s: None if campus is None else original_rate(campus['raw'][SUBJECT_FIELDS[s]]) for s in ['math', 'reading']}
        raw_rates = {s: None if campus is None else campus['raw'][SUBJECT_FIELDS[s]] for s in ['math', 'reading']}
        refs = source_references(roster, link, entry, grade, inc, campus)
        reasons = [] if usable_income else ['Native individual February income missing, masked or unreconciled']
        if campus is not None and campus['raw'][47] != 'N':
            reasons.append('Original collocated achievement cannot be assigned to one income profile')
        reasons += [s + ': original campus published rate missing or masked' for s in required if rates[s] is None]
        if reasons:
            exclusions.append(dict(school_id=key, native_school_id=c['ST_SCHID'], ncessch=c['NCESSCH'],
                                   name=link['name'], reason='; '.join(reasons), raw_published_rates=raw_rates, source_refs=refs))
            continue
        outcome = (rates['math'] + rates['reading']) / 2 if subject == 'combined' else rates[subject]
        x = 100 * low / n
        if x != link['income']['percentage'] or outcome != link['subjects'][subject]['native_rate']:
            raise ValueError('Independent original individual income/published outcome differs from frozen source')
        inputs.append(dict(school_id=key, native_school_id=c['ST_SCHID'], ncessch=c['NCESSCH'], name=link['name'],
            level='ES', charter=c['CHARTER_TEXT'], ccd_school_type=c['SCH_TYPE_TEXT'],
            income_pct=x, income_year=2025, academic_year='2024-2025', income_enrollment=n, individual_economic_count=low,
            outcome_pct=outcome, outcome_by_subject=rates, raw_published_rates=raw_rates,
            valid_scores_by_subject={'math': None, 'reading': None}, display_valid_scores=None, sampling_variance=None,
            ten_valid_scored_floor_certified=False, source_refs=refs))
    cohort = roster['cohorts']['prospective_tested_grade_profiles']
    if configurations != sorted(cohort['school_ids']) or [r['school_id'] for r in inputs] != sorted(cohort['subjects'][subject]['eligible_school_ids']):
        raise ValueError('Complete original subject/configuration membership differs from frozen source')
    coverage = dict(grade_school_configuration_profiles=len(configurations), usable_schools=len(inputs),
        excluded_configuration_profiles=len(exclusions), excluded_configuration_records=exclusions,
        exclusions=dict(sorted(Counter(r['reason'] for r in exclusions).items())), charter=dict(sorted(Counter(r['charter'] for r in inputs).items())),
        school_types=dict(sorted(Counter(r['ccd_school_type'] for r in inputs).items())), eligible_members_with_verified_denominators=0,
        ten_valid_scored_floor_certified=False, model_sampling_intervals_available=False,
        source_evidence_path='data/source/lee-district-audit.json', source_evidence_sha256=ROSTER_SHA)
    return inputs, coverage


def verify_independently(x, y, model, results):
    """Centered full OLS, independent leverage and explicit held-out refits; no intervals."""
    require_runtime_contract()
    n = len(x)
    if (n < MIN_SCHOOLS or x.shape != y.shape or x.ndim != 1
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError('Independent verification requires finite complete percentage vectors')
    def finite_number(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

    if (type(model.get('n')) is not int or model['n'] != n or len(results) != n
            or any(not finite_number(model.get(k)) for k in ['intercept', 'slope', 'r2'])
            or any(not finite_number(r.get(k)) for r in results
                   for k in ['actual', 'predicted', 'residual', 'leverage', 'studentized'])
            or any(not 0 <= r['leverage'] < 1 for r in results)):
        raise ValueError('Independent verification requires finite returned coefficients/results and exact model count')
    centered = x - x.mean()
    spread = centered @ centered
    h = 1 / n + centered ** 2 / spread
    design = np.column_stack([np.ones(n), centered])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    predicted = design @ beta
    residual = y - predicted
    sse = float(residual @ residual)
    full_tolerance = 64 * np.finfo(float).eps * max(1., np.linalg.cond(design)) * max(np.linalg.norm(y), np.linalg.norm(predicted))
    if np.linalg.matrix_rank(design) != 2 or not math.isfinite(sse) or np.linalg.norm(residual) <= full_tolerance:
        raise ValueError('Independent full design/positive residual scale is unavailable')
    r2 = 1 - sse / ((y - y.mean()) @ (y - y.mean()))
    if [r['actual'] for r in results] != y.tolist():
        raise ValueError('Independent verification requires exact native actual proficiency')
    if any(r['low'] is not None or r['high'] is not None for r in results):
        raise ValueError('Point-only audit cannot expose numerical interval endpoints')
    errors = {
        'coefficient': max(abs(float(beta[0] - beta[1] * x.mean()) - model['intercept']),
                           abs(float(beta[1]) - model['slope'])),
        'predicted': max(abs(float(v) - r['predicted']) for v, r in zip(predicted, results)),
        'residual': max(abs(float(v) - r['residual']) for v, r in zip(residual, results)),
        'r2': abs(float(r2) - model['r2']), 'leverage': 0., 'studentized': 0.,
        'deleted_sse_identity': 0., 'held_out_prediction_identity': 0.,
        'interval_endpoint': None,
    }
    deleted = []
    for i in range(n):
        keep = np.arange(n) != i
        mean_x = x[keep].mean()
        deleted_centered = x[keep] - mean_x
        X = np.column_stack([np.ones(n - 1), deleted_centered])
        if np.linalg.matrix_rank(X) != 2:
            raise ValueError('Explicit deleted-school income design is rank deficient')
        b = np.linalg.lstsq(X, y[keep], rcond=None)[0]
        e = y[keep] - X @ b
        deleted_sse = float(e @ e)
        residual_tolerance = 64 * np.finfo(float).eps * max(1., np.linalg.cond(X)) * max(
            np.linalg.norm(y[keep]), np.linalg.norm(X @ b))
        if not math.isfinite(deleted_sse) or np.linalg.norm(e) <= residual_tolerance:
            raise ValueError('Explicit deleted-school residual scale is unavailable or numerically unresolved')
        held_out = float(b[0] + b[1] * (x[i] - mean_x))
        predictive_h = 1 / (n - 1) + (x[i] - mean_x) ** 2 / (deleted_centered @ deleted_centered)
        scale = math.sqrt(deleted_sse / (n - 3))
        external_t = (y[i] - held_out) / (scale * math.sqrt(1 + predictive_h))
        errors['studentized'] = max(errors['studentized'], abs(external_t - results[i]['studentized']))
        errors['leverage'] = max(errors['leverage'], abs(h[i] - results[i]['leverage']))
        errors['deleted_sse_identity'] = max(errors['deleted_sse_identity'],
                                             abs(deleted_sse - (sse - residual[i] ** 2 / (1 - h[i]))))
        errors['held_out_prediction_identity'] = max(errors['held_out_prediction_identity'],
                                                      abs(held_out - (predicted[i] - h[i] * residual[i] / (1 - h[i]))))
        deleted.append({'intercept': float(b[0] - b[1] * mean_x), 'slope': float(b[1]),
                        'sse': deleted_sse, 'held_out_prediction': held_out,
                        'held_out_prediction_leverage': float(predictive_h),
                        'residual_scale': scale, 'externally_studentized': float(external_t)})
    if any(v is not None and (not math.isfinite(v) or v > VERIFY_TOLERANCE) for v in errors.values()):
        raise ValueError('Independent full/deleted-fit verification exceeded tolerance')
    # JSON preserves Python float/int/bool types but not NumPy scalar classes.
    # Normalize computed errors before strict typed replay; native evidence is
    # never coerced and booleans remain invalid numerical substitutions.
    return deleted, {k: None if v is None else float(v) for k, v in errors.items()}




def fit_audited_model(inputs, coverage, subject):
    """Public fit reconstructs and verifies exact native inputs before any fit."""
    require_runtime_contract()
    if subject not in SUBJECTS:raise ValueError('Only three proposed grade-school subjects may be audited')
    if not isinstance(inputs,list)or len(inputs)<MIN_SCHOOLS:raise ValueError('District subject model requires at least 30 usable schools')
    frozen_inputs,frozen_coverage=_selected_inputs_verified(load_roster(),subject)
    if (roster_audit.fingerprint(inputs)!=roster_audit.fingerprint(frozen_inputs)
            or roster_audit.fingerprint(coverage)!=roster_audit.fingerprint(frozen_coverage)):
        raise ValueError('District fit requires exact frozen native inputs, complete eligible membership and coverage')
    return _fit_original_inputs(inputs,coverage,subject)


def _fit_original_inputs(inputs, coverage, subject):
    require_runtime_contract()
    if subject not in SUBJECTS:
        raise ValueError('Only three proposed grade-school subjects may be audited')
    if not isinstance(inputs, list) or any(not isinstance(r, dict) for r in inputs):
        raise ValueError('District inputs require original frozen native records')
    if len(inputs) < MIN_SCHOOLS:
        raise ValueError('District subject model requires at least 30 usable schools')
    if (len({r['school_id'] for r in inputs}) != len(inputs)
            or len({r['native_school_id'] for r in inputs}) != len(inputs)
            or any(r['level']!='ES' or type(r['income_year']) is not int or r['income_year']!=2025
                   or r['academic_year']!='2024-2025'
                   or not re.fullmatch(roster_audit.NATIVE_LEA+r'-\d{4}',r['native_school_id'])
                   or not re.fullmatch(roster_audit.LEA+r'\d{5}',r['ncessch'])
                   or not re.fullmatch(roster_audit.NATIVE_DISTRICT+r'-\d{4}',r['school_id'])
                   or r['ten_valid_scored_floor_certified'] is not False for r in inputs)):
        raise ValueError('District members require exact same-year native pure grade-school identities and income')
    if any(r['sampling_variance'] is not None or r['display_valid_scores'] is not None
           or r['valid_scores_by_subject'] != {'math': None, 'reading': None} for r in inputs):
        raise ValueError('Point-only source contract prohibits fabricated counts or sampling variance')
    if subject == 'combined' and any(r['outcome_pct'] != (r['outcome_by_subject']['math'] + r['outcome_by_subject']['reading']) / 2 for r in inputs):
        raise ValueError('Combined must be the exact equally weighted subject mean')
    if any(isinstance(r[k], bool) or not isinstance(r[k], (int, float)) for r in inputs for k in ['income_pct', 'outcome_pct']):
        raise ValueError('District income and proficiency require numeric percentage values, never booleans')
    x = np.array([r['income_pct'] for r in inputs], dtype=float)
    y = np.array([r['outcome_pct'] for r in inputs], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any((x < 0) | (x > 100) | (y < 0) | (y > 100)):
        raise ValueError('District income and proficiency must be finite percentages')
    design = np.column_stack([np.ones(len(x)), x])
    rank = int(np.linalg.matrix_rank(design))
    if rank != 2:
        raise ValueError('District income design must have rank two')
    # fit_model requires a variance vector. This zero vector is only its point-estimate
    # computational sentinel; no zero sampling variances or generated endpoints survive.
    model, fitted = fit_model(x - x.mean(), y, np.zeros(len(inputs), dtype=float))
    model['intercept'] -= model['slope'] * float(x.mean())
    for row in fitted:
        row.update(low=None, high=None)
    deleted, errors = verify_independently(x, y, model, fitted)
    residual = np.array([r['residual'] for r in fitted])
    sse = float(residual @ residual)
    s2 = sse / (len(x) - 2)
    results = []
    thresholds = {'leverage_2p_over_n': 4 / len(x), 'cooks_4_over_n': 4 / len(x),
                  'absolute_external_t': 2.}
    for school, row, deletion in zip(inputs, fitted, deleted):
        h = row['leverage']
        cook = row['residual'] ** 2 * h / (2 * s2 * (1 - h) ** 2)
        endpoints = np.array([x.min(), x.max()])
        shift = (deletion['intercept'] - model['intercept']) + (deletion['slope'] - model['slope']) * endpoints
        results.append({
            'school_id': school['school_id'], **row, 'valid_scores': None, 'sampling_variance': None,
            'cooks_distance': float(cook), 'deleted_intercept': deletion['intercept'],
            'deleted_slope': deletion['slope'], 'deleted_sse': deletion['sse'],
            'deleted_residual_scale': deletion['residual_scale'],
            'deleted_held_out_prediction': deletion['held_out_prediction'],
            'deleted_held_out_prediction_leverage': deletion['held_out_prediction_leverage'],
            'maximum_prediction_change_on_observed_income_range': float(np.max(np.abs(shift))),
            'review_flags': {'leverage_above_2p_over_n': h > thresholds['leverage_2p_over_n'],
                             'cooks_above_4_over_n': cook > thresholds['cooks_4_over_n'],
                             'absolute_external_t_above_2': abs(row['studentized']) > 2},
        })
    by_id = {r['school_id']: r for r in inputs}
    influence = []
    for row in sorted(results, key=lambda r: (-r['cooks_distance'], r['school_id']))[:10]:
        school = by_id[row['school_id']]
        influence.append({k: school[k] for k in ['school_id', 'name', 'charter', 'ccd_school_type', 'income_pct']} |
                         {k: row[k] for k in ['cooks_distance', 'leverage', 'studentized']})
    return {
        'model_id': f'lee-2025-ES-{subject}', 'status': 'numerically_verified_pending_integration',
        'approved_for_source': False, 'approved_for_modeling': False, 'valid_score_floor_certified': False, 'year': 2025, 'academic_year': '2024-2025',
        'population': 'Exact Lee operational pure lower offered grades with positive or protected Fall grades 3–8 and explicit-zero grades 9–12; own February individual lunch-status count ratio and original 2025 School Grades published achievement rates',
        'level': 'ES', 'subject': subject, 'assessment': ASSESSMENT,
        'assessment_standard': STANDARD,
        'coverage': coverage, 'inputs': inputs,
        'population_sha256': roster_audit.fingerprint({'policy': POLICY, 'source_audit_sha256': ROSTER_SHA,
                                                      'level': 'ES', 'subject': subject, 'year': 2025,
                                                      'school_ids': [r['school_id'] for r in inputs]}),
        'coefficients': model, 'results': results,
        'review_warnings': [
            'Valid-score denominators remain unverified; no count, sampling variance or interval is available.',
            'Conventional leverage, Cook distance and residual flags require descriptive review, never automatic exclusions.',
            'Individual February lunch status covers all school grades and a different date/population from accountable School Grades achievement. Published whole percentages, full-year and home-zoned attribution, FAST/BEST/Access EOC/FAA scope, ELL and exemption rules remain limits; Datafolio only contributes to percent tested. No valid-score denominator or ten-valid-scored floor is certified.',
        ],
        'intervals': {'available_for_entire_model': False, 'eligible_members': len(inputs),
                      'eligible_members_with_verified_denominators': 0,
                      'valid_score_counts': None, 'sampling_variances': None, 'ten_valid_scored_floor_certified': False,
                      'reason': 'School Grades contains no verified valid-score denominators. Its at-least-ten-eligible component rule does not certify ten valid-scored students; original published achievement supports point-only numerical audit without counts or intervals.'},
        'diagnostics': {
            'income_design_rank': rank, 'income_design_condition_number': float(np.linalg.cond(design)),
            'centered_income_design_condition_number': float(np.linalg.cond(np.column_stack([np.ones(len(x)), x - x.mean()]))),
            'income': {'minimum': float(x.min()), 'maximum': float(x.max()), 'mean': float(x.mean()),
                       'standard_deviation_population': float(x.std()), 'distinct': len(set(x.tolist())),
                       'quantiles': {str(q): float(np.quantile(x, q)) for q in [.05, .25, .5, .75, .95]}},
            'residual_sse': sse, 'residual_standard_error': float(math.sqrt(s2)),
            'full_residual_degrees_of_freedom': len(x) - 2,
            'deleted_residual_degrees_of_freedom': len(x) - 3,
            'minimum_deleted_sse': min(r['sse'] for r in deleted),
            'minimum_deleted_residual_scale': min(r['residual_scale'] for r in deleted),
            'predicted_range': {'minimum': min(r['predicted'] for r in results), 'maximum': max(r['predicted'] for r in results)},
            'predictions_outside_percentage_range': sum(r['predicted'] < 0 or r['predicted'] > 100 for r in results),
            'maximum_leverage': max(r['leverage'] for r in results),
            'maximum_absolute_studentized_residual': max(abs(r['studentized']) for r in results),
            'maximum_cooks_distance': max(r['cooks_distance'] for r in results),
            'maximum_absolute_deleted_slope_change': max(abs(r['slope'] - model['slope']) for r in deleted),
            'deleted_slope_range': {'minimum': min(r['slope'] for r in deleted), 'maximum': max(r['slope'] for r in deleted)},
            'maximum_prediction_change_on_observed_income_range': max(r['maximum_prediction_change_on_observed_income_range'] for r in results),
            'conventional_review_thresholds': thresholds,
            'conventional_review_flag_counts': {key: sum(r['review_flags'][key] for r in results) for key in results[0]['review_flags']},
            'top_ten_cooks_distance': influence,
            'interpretation': 'Descriptive influence flags only; no school is excluded by leverage, residual or fit quality. Native whole-percent precision, broader February individual income, full-year accountable FAST/BEST/Access/FAA achievement and uncertified valid-score/floor definitions remain limitations; predictions are never clamped.',
        },
        'independent_verification': {'full_income_design_rank': rank, 'full_residual_degrees_of_freedom': len(inputs) - 2,
                                     'explicit_deleted_fits': len(inputs), 'deleted_training_members': len(inputs) - 1,
                                     'deleted_residual_degrees_of_freedom': len(inputs) - 3, 'tolerance_absolute': VERIFY_TOLERANCE,
                                     'maximum_absolute_errors': errors,
                                     'method': 'Centered full OLS; centered closed-form leverage; every explicit leave-one-out fit uses N−3 scale and held-out variance factor 1+h_deleted. Interval verification is inapplicable because all verified valid-score denominators are unavailable; Native own February denominator, Fall/CCD membership, percent tested and component-eligibility rules remain linked original provenance, never certified assessment denominators or a scored-count-floor certificate.'},
    }


def build(roster=None):
    # One fresh immutable source verification owns this synchronous reconstruction.
    # Direct public selector/fit calls still independently verify their arguments.
    if roster is None:roster=load_roster()
    else:require_frozen_roster(roster)
    models, holds = [], []
    for subject in SUBJECTS:
        inputs, coverage = _selected_inputs_verified(roster, subject)
        try:
            model = _fit_original_inputs(inputs, coverage, subject)
        except ValueError as error:
            model = dict(model_id=f'lee-2025-ES-{subject}', status='numerical_hold', approved_for_source=False,
                         approved_for_modeling=False, level='ES', subject=subject, inputs=inputs, coverage=coverage, reason=str(error))
            holds.append(dict(model_id=model['model_id'], reason=str(error)))
        models.append(model)
    population = frozen_population(roster)
    return dict(schema_version=1, state='FL', year=2025, academic_year='2024-2025', nces_lea_id=roster_audit.LEA,
        native_lea_id=roster_audit.NATIVE_LEA, native_district_id=roster_audit.NATIVE_DISTRICT,
        scope='numerical_audit_only', status='numerical_hold' if holds else 'numerically_verified_pending_integration',
        approved_for_source=False, approved_for_modeling=False, policy=POLICY, numeric_policy_sha256=NUMERIC_POLICY_SHA,
        runtime_contract_sha256=RUNTIME_CONTRACT_SHA,
        sources=dict(roster_audit=dict(path='data/source/lee-district-audit.json', sha256=ROSTER_SHA, bytes=ROSTER_BYTES),
            source_audit_code=dict(path='scripts/audit_lee.py', sha256=SOURCE_CODE_SHA),
            source_audit_tests=dict(path='tests/test_lee_audit.py', sha256=SOURCE_TESTS_SHA),
            source_policy_sha256=SOURCE_POLICY_SHA, original_raw_input_sha256=SOURCE_RAW_SHA, original_schema_sha256=SOURCE_SCHEMA_SHA,
            source_runtime_sha256=SOURCE_RUNTIME_SHA,
            original_definition_evidence_sha256=SOURCE_DEFINITION_SHA, original_identity_projection_sha256=SOURCE_IDENTITY_SHA,
            native_primary_sources=roster['sources'], secondary_florida_extract=roster['state_extract']),
        retained_source_reference=dict(path='data/source/lee-district-audit.json', sha256=ROSTER_SHA, source_scope=roster['scope'],
            source_status=roster['status'], approved_for_source=False, approved_for_modeling=False,
            complete_original_record_count=1449, complete_original_cell_count=34610,
            note='Complete original records, headers, notes, definitions, membership and outside identities stay in the immutable linked source artifact; every numerical replay requires current available unchanged source/code/tests/policy and semantic validation.'),
        count_definition_status=dict(status='unverified_schoolgrades_valid_score_denominators', raw_fields=['Percent Tested', 'At least ten eligible component rule'],
            valid_score_counts=None, sampling_variances=None, sampling_intervals_available=False, ten_valid_scored_floor_certified=False,
            reason='Native enrollment, percent tested and eligible component rules are source evidence; no exact valid-score denominator or ten-valid-scored floor is certified. Income and enrollment never substitute or select model membership.'),
        frozen_population=population, frozen_population_sha256=roster_audit.fingerprint(dict(policy=POLICY, population=population)),
        source_coverage=roster['coverage'],
        retained_scope_exclusions=[dict(school_id=r['school_id'], native_school_id=r['native_school_id'], ncessch=r['ncessch'],
            name=r['name'], source_roster_link_index=i, exclusion=r['population_exclusion'])
            for i, r in enumerate(roster['roster_links']) if not r['source_profile_eligible']],
        retained_outside_source_profiles=[dict(school_id=r['school_id'], ncessch=None, grade_source_row=r['grade_source_row'],
            exclusion=r['exclusion']) for r in roster['outside_roster_profiles']],
        replay_tolerance=dict(absolute=ABS_TOLERANCE, relative=REL_TOLERANCE,
            scope='Computed finite floating-point metrics only, strict numeric types. Source fingerprints/references, exact identity/x/y/raw income/rates, subject membership, counts, approvals and absent intervals compare exactly.'),
        models=models, hard_holds=holds)


def numeric_equal(actual, expected):
    if type(expected) is float:
        return type(actual) is float and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(numeric_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(numeric_equal(a, e) for a, e in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def _compare_numerical_documents(document, expected):
    """Typed numerical/source comparison against a verified immutable-source expectation."""
    if not isinstance(document, dict) or roster_audit.fingerprint({k: v for k, v in document.items() if k != 'models'}) != roster_audit.fingerprint({k: v for k, v in expected.items() if k != 'models'}):
        raise ValueError('Lee numerical audit metadata/source evidence changed')
    if not isinstance(document.get('models'), list) or len(document['models']) != len(expected['models']):
        raise ValueError('Lee numerical audit model set changed')
    for actual, model in zip(document['models'], expected['models']):
        if not isinstance(actual, dict):
            raise ValueError('Lee model requires exact typed numerical/source fields')
        for field in ['model_id', 'level', 'subject', 'status', 'approved_for_source', 'approved_for_modeling',
                      'valid_score_floor_certified', 'year', 'academic_year', 'population', 'assessment', 'assessment_standard',
                      'review_warnings', 'coverage', 'inputs', 'population_sha256', 'intervals']:
            if field in model and roster_audit.fingerprint(actual.get(field)) != roster_audit.fingerprint(model[field]):
                raise ValueError('Lee numerical audit source identities, counts, approvals or population changed')
        if 'independent_verification' in model:
            metadata = lambda v: {k: value for k, value in v.items() if k != 'maximum_absolute_errors'}
            if roster_audit.fingerprint(metadata(actual.get('independent_verification', {}))) != roster_audit.fingerprint(metadata(model['independent_verification'])):
                raise ValueError('Lee independent verification metadata/tolerance changed')
        if 'results' in model:
            exact = ['school_id', 'actual', 'valid_scores', 'sampling_variance', 'low', 'high']
            if roster_audit.fingerprint([{k: r.get(k) for k in exact} for r in actual.get('results', [])]) != roster_audit.fingerprint([{k: r[k] for k in exact} for r in model['results']]):
                raise ValueError('Lee result identities/native outcomes/counts or interval absence changed')
        if not numeric_equal(actual, model):
            raise ValueError('Lee numerical metrics failed independent typed/finite replay tolerance')
    return {m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}

def validate(document, expected=None):
    # Every authorization reconstructs the verified expectation from complete
    # current immutable original inputs. A supplied expected object is merely
    # another value to verify, never its own authority; no reassignable model
    # cache or cache digest can bypass the full/deleted fit checks.
    verified=build()
    if expected is not None:
        _compare_numerical_documents(expected,verified)
    return _compare_numerical_documents(document,verified)



def prepare(output=OUTPUT, check=False):
    expected = build()
    if check:
        validate(json.loads(Path(output).read_text()), expected)
    else:
        Path(output).write_text(json.dumps(expected, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    return dict(models={m['model_id']: m['coverage']['usable_schools'] for m in expected['models']}, hard_holds=expected['hard_holds'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute and validate saved audit without rewriting it')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.check), sort_keys=True))

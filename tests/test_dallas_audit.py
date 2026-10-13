import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_dallas as audit


class DallasSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(audit.OUTPUT.read_text())
        cls.inputs = cls.document['raw_inputs']
        cls.links = {r['native_school_id']: r for r in cls.document['roster_links']}
        cls.native = {r['raw']['CAMPUS']: r['raw'] for r in cls.inputs['stud']['records']}
        cls.outcomes = {r['raw']['CAMPUS']: r['raw'] for r in cls.inputs['assessment']['records']}

    def test_exact_source_only_counts_and_no_approval(self):
        c = audit.validate(self.document)
        self.assertEqual((c['directory_records'], c['operational_schools'], c['native_campuses']), (249, 239, 239))
        self.assertEqual(c['native_scope_counts'], {'grade-school': 189, 'high': 37, 'mixed': 7, 'primary-only': 6})
        self.assertEqual(c['prospective_subject_members'], {'math': 188, 'reading': 188, 'combined': 188})
        self.assertEqual(c['ccd_school_types'], {'Alternative School': 6, 'Regular School': 242, 'Special Education School': 1})
        self.assertEqual(c['ccd_charter'], {'No': 249})
        self.assertEqual(self.document['scope'], 'source_cohort_audit_only')
        self.assertEqual(self.document['status'], 'audit_pending')
        self.assertIs(self.document['approved_for_source'], False)
        self.assertIs(self.document['approved_for_modeling'], False)
        for field in ['models', 'model_runs', 'model_results', 'residuals']:
            self.assertNotIn(field, self.document)
        self.assertEqual(c['verified_valid_score_counts'], 0)
        self.assertFalse(c['sampling_intervals_available'])
        self.assertIs(c['ten_valid_scored_floor_certified'], False)
        self.assertEqual(c['reported_reconciled_performance_arithmetic_rows'], {'math': 192, 'reading': 192})
        self.assertIn('N/NAAR', c['valid_score_verification_hold'])

    def test_exact_native_and_full_ccd_ids(self):
        native = self.native['057905212']
        self.assertEqual(audit.native_identity(dict(native, CAMPNAME='Renamed school')), '057905212')
        directory = self.inputs['directory']['records'][0]['raw']
        self.assertEqual(audit.ccd_identity(directory), ('481623000465', '057905212'))
        self.assertEqual(directory['ST_SCHID'], 'TX-057905-057905212')
        for field, value in [('CAMPUS', int('057905212')), ('CAMPUS', '05790568'), ('CAMPUS', '057906212'), ('DISTRICT', '057906')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                audit.native_identity(dict(native, **{field: value}))
        for field, value in [('ST_SCHID', 'TX-057905212'), ('ST_SCHID', 'TX-057905-057906212'), ('ST_LEAID', 'TX-057906'), ('LEAID', '4816231'), ('SCHOOL_YEAR', '2023-2024')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                audit.ccd_identity(dict(directory, **{field: value}))

    def test_complete_native_enrollment_never_reference_type_selects(self):
        r = self.links['057905352']
        self.assertEqual(r['native_reference']['GRDTYPE'], 'M')
        self.assertEqual(r['native_reference']['GRDSPAN'], '06 - 09')
        self.assertEqual(r['native_enrolled']['high_enrollment'], 29)
        self.assertEqual([r['native_enrolled']['counts']['CPNTG%02dC' % g] for g in range(9, 13)], [29, 0, 0, 0])
        self.assertEqual(r['native_enrolled']['scope'], 'mixed')
        self.assertFalse(r['subjects']['combined']['source_usable'])
        self.assertTrue(r['native_reference_conflicts_with_positive_high_enrollment'])
        self.assertEqual(self.document['coverage']['native_reference_high_grade_contradictions'], ['057905011', '057905352'])
        altered = dict(self.native['057905212'], CPNTG09C='1')
        with self.assertRaises(ValueError): audit.grade_evidence(altered)
        altered['CPNTALLC'] = str(int(altered['CPNTALLC']) + 1)
        self.assertEqual(audit.grade_evidence(altered)['scope'], 'mixed')
        missing = dict(self.native['057905212'], CPNTG09C='-1')
        self.assertEqual(audit.grade_evidence(missing)['scope'], 'unknown')
        self.assertFalse(audit.grade_evidence(missing)['prospective_grade_school'])

    def test_primary_and_absent_reported_zero_are_retained(self):
        primary = self.document['cohorts']['primary_only']
        self.assertEqual(primary['profiles'], 6)
        self.assertTrue(all(primary['subjects'][s]['usable'] == 0 for s in ['math', 'reading', 'combined']))
        self.assertTrue(all(self.links[k]['native_enrolled']['tested_grades_enrollment'] == 0 for k in primary['native_school_ids']))
        absent = [r for r in self.document['roster_links'] if not r['native_present']]
        self.assertEqual(len(absent), 10)
        self.assertEqual({r['ccd_flags']['status'] for r in absent}, {'Inactive', 'Closed'})
        missing = self.links['057905030']
        self.assertEqual(missing['school_id'], '481623006965')
        self.assertFalse(missing['ccd_flags']['operational'])
        self.assertFalse(missing['native_present'])
        self.assertIsNone(missing['native_enrolled'])
        self.assertIsNone(missing['income']['percentage'])
        self.assertIsNone(missing['subjects']['math']['proficiency'])
        self.assertEqual(len(self.document['outside_grade_school_population']), 60)
        self.assertEqual(self.document['cohorts']['native_no_high_grade_profiles']['profiles'], 195)

    def test_exact_individual_income_and_distinct_membership(self):
        e = self.document['enrollment_reconciliation']
        self.assertEqual([e[k] for k in ['ccd_lea_reported', 'ccd_operational_school_sum', 'native_campus_sum']], [139802] * 3)
        self.assertEqual(e['native_economic_disadvantage_sum'], 124800)
        self.assertEqual(e['native_peims_membership_sum'], 139776)
        self.assertEqual(len(e['native_enrollment_membership_differences']), 16)
        self.assertEqual(e['matched_school_enrollment_differences'], [])
        for k, raw in self.native.items():
            income = audit.income_evidence(raw)
            self.assertEqual(income['economic_disadvantage'] + income['not_economic_disadvantage'], income['enrollment'])
            self.assertEqual(income['percentage'], 100 * int(raw['CPNTECOC']) / int(raw['CPNTALLC']))
            self.assertEqual(income['snapshot_date'], '2024-10-25')
        raw = dict(self.native['057905001'])
        self.assertNotEqual(raw['CPNTALLC'], raw['CPETALLC'])
        with self.assertRaises(ValueError): audit.income_evidence(dict(raw, CPNTALLC=raw['CPETALLC']))
        total = raw['CPNTALLC']
        zero = audit.income_evidence(dict(raw, CPNTECOC='0', CPNTNEDC=total, CPNTECOP='0'))
        self.assertEqual(zero['percentage'], 0)
        self.assertIsNone(zero['exclusion'])
        self.assertIsNone(audit.income_evidence(dict(raw, CPNTECOC='-1'))['percentage'])

    def test_published_whole_rates_keep_count_arithmetic_as_unverified_evidence(self):
        cohort = self.document['cohorts']['prospective_grade_school']
        for subject, expected in [('math', (50791, 22664, 13)), ('reading', (50878, 26576, 13))]:
            members = [self.links[k]['subjects'][subject] for k in cohort['subjects'][subject]['prospective_native_school_ids']]
            self.assertEqual((sum(r['reported_tested'] for r in members), sum(r['reported_meets_or_above'] for r in members), min(r['reported_tested'] for r in members)), expected)
            for row in members:
                self.assertEqual(row['proficiency'], float(row['raw_published_rate']))
                self.assertEqual(row['unverified_count_ratio'], 100 * row['reported_meets_or_above'] / row['reported_tested'])
                self.assertLessEqual(abs(row['unverified_count_ratio'] - row['published_rate']), .500001)
                self.assertIsNone(row['valid_scores'])
                self.assertIsNone(row['sampling_variance'])
                self.assertFalse(row['sampling_interval_available'])
                self.assertIs(row['ten_valid_scored_floor_certified'], False)
                self.assertIn('held', row['valid_score_verification_status'])
            self.assertTrue(cohort['subjects'][subject]['prospective_30_school_floor_met'])
            self.assertFalse(cohort['subjects'][subject]['approved_for_modeling'])
            self.assertIn('uncertified', cohort['subjects'][subject]['availability_note'])
        math = [self.links[k]['subjects']['math'] for k in cohort['subjects']['math']['prospective_native_school_ids']]
        ela = [self.links[k]['subjects']['reading'] for k in cohort['subjects']['reading']['prospective_native_school_ids']]
        self.assertEqual(sum(r['proficiency'] != r['unverified_count_ratio'] for r in math), 186)
        self.assertEqual(sum(r['proficiency'] != r['unverified_count_ratio'] for r in ela), 184)

    def test_missing_masked_and_true_zero_outcomes_are_distinct(self):
        for k, expected in [('057905241', ['', '', ''])]:
            row = self.links[k]['subjects']['math']
            self.assertEqual(row['raw'], expected)
            self.assertIsNone(row['proficiency'])
            self.assertFalse(row['source_usable'])
            self.assertIn('missing or masked', row['exclusion'])
        alternative = self.links['057905241']
        self.assertEqual(alternative['ccd_flags']['school_type'], 'Alternative School')
        self.assertEqual(alternative['native_enrolled']['enrollment'], 8)
        self.assertTrue(alternative['native_enrolled']['prospective_grade_school'])
        self.assertIn('057905241', self.document['cohorts']['prospective_grade_school']['native_school_ids'])
        income = audit.income_evidence(self.native['057905212'])
        raw = dict(self.outcomes['057905212'])
        fields = audit.FIELDS['math']
        for field, value in zip(fields, ['10', '0', '0']): raw[field] = value
        row = audit.subject_evidence(raw, 'math', True, income)
        self.assertEqual(row['proficiency'], 0)
        self.assertTrue(row['source_usable'])
        for mask in ['', '-1', '-2', '-3', '*', '•']:
            row = audit.subject_evidence(dict(raw, **{fields[2]: mask}), 'math', True, income)
            self.assertIsNone(row['proficiency'])
            self.assertEqual(row['reported_tested'], 10)
            self.assertIsNone(row['valid_scores'])
            self.assertFalse(row['source_usable'])
        for vals in [('10', '11', '100'), ('10', '1', '80'), ('10', '1', '10.5'), ('10', '1', '101')]:
            bad = dict(raw, **dict(zip(fields, vals)))
            with self.subTest(vals=vals), self.assertRaises(ValueError): audit.subject_evidence(bad, 'math', True, income)

    def test_reported_counts_never_screen_or_certify_point_rate_source_membership(self):
        raw = dict(self.outcomes['057905212'], **dict(zip(audit.FIELDS['math'], ['5', '1', '20'])))
        income = audit.income_evidence(self.native['057905212'])
        row = audit.subject_evidence(raw, 'math', True, income)
        self.assertEqual(row['reported_tested'], 5)
        self.assertEqual(row['proficiency'], 20.)
        self.assertTrue(row['source_usable'])
        self.assertIsNone(row['exclusion'])
        self.assertIsNone(row['valid_scores'])
        self.assertIsNone(row['sampling_variance'])
        self.assertIs(row['ten_valid_scored_floor_certified'], False)
        for test_mask in ['', '-1', '-2', '-3']:
            unavailable = audit.subject_evidence(dict(raw, **{audit.FIELDS['math'][0]: test_mask}), 'math', True, income)
            self.assertTrue(unavailable['source_usable'])
            self.assertEqual(unavailable['proficiency'], 20.)
            self.assertIsNone(unavailable['valid_scores'])

    def test_combined_mean_and_outside_observations_never_pooled(self):
        for r in self.document['roster_links']:
            m, e, c = [r['subjects'][s] for s in ['math', 'reading', 'combined']]
            if m['proficiency'] is not None and e['proficiency'] is not None:
                self.assertEqual(c['proficiency'], (m['proficiency'] + e['proficiency']) / 2)
            else: self.assertIsNone(c['proficiency'])
            self.assertIsNone(c['valid_scores'])
        mixed = self.document['cohorts']['mixed_grade']
        self.assertEqual(mixed['profiles'], 7)
        for s in ['math', 'reading', 'combined']:
            self.assertEqual(mixed['subjects'][s]['native_fields_usable'], 4)
            self.assertEqual(mixed['subjects'][s]['usable'], 0)
            self.assertFalse(mixed['subjects'][s]['prospective_30_school_floor_met'])

    def test_complete_raw_headers_rows_and_primary_definition_proof(self):
        for source, expected in [('directory', 249), ('membership', 1921), ('lea_directory', 1), ('lea_membership', 16), ('ref', 239), ('stud', 239), ('assessment', 239)]:
            raw = self.inputs[source]
            self.assertEqual(len(raw['records']), expected)
            self.assertTrue(all(type(e['source_row']) is int and e['source_row'] >= 2 for e in raw['records']))
            self.assertTrue(all(set(e['raw']) == set(raw['header']) for e in raw['records']))
        definitions = self.inputs['definitions']
        glossary = '\n'.join(p['text'] for p in definitions['glossary']['pages'])
        for text in ['accountability subset', 'Spanish STAAR', 'STAAR Alternate 2', 'English I or II EOC', 'Algebra I EOC', 'Enrollment:', 'Membership:']:
            self.assertIn(text, glossary)
        teds = '\n'.join(p['text'] for p in definitions['income-guide']['pages'])
        for text in ['Community Eligibility Provision', 'Provision 2', 'locally developed income survey', 'not returned', 'continuously enrolled']:
            self.assertIn(text, teds)
        self.assertEqual([p['pdf_page'] for p in definitions['accountability-manual']['pages']], [173, 177, 204])
        self.assertEqual([p['pdf_page'] for p in definitions['performance-listing']['pages']], [4, 6, 8])
        self.assertEqual(len(definitions['dictionary']['lines']), 12)
        extension = '\n'.join(e['html'] for e in definitions['income-extension']['lines'])
        self.assertIn('January 16, 2025', extension)
        self.assertIn('October 25, 2024', extension)
        self.assertEqual(audit.fingerprint(self.inputs), audit.RAW_INPUT_SHA)
        self.assertEqual(sum(len(block['records']) for block in self.inputs.values()
                             if isinstance(block, dict) and 'records' in block), 2904)
        self.assertEqual(sum(len(e['raw']) for block in self.inputs.values()
                             if isinstance(block, dict) and 'records' in block for e in block['records']), 112006)
        self.assertEqual(len(self.document['sources']), 15)

    def test_planning_identity_reconstruction_is_separate(self):
        p = self.document['planning_identity_reconciliation']
        self.assertEqual([len(p['potential_school_ids'][s]) for s in ['ES', 'HS']], [189, 37])
        self.assertEqual(p['source_not_planning_ES'], [])
        self.assertEqual(p['planning_ES_not_source_usable'], ['481623009196'])
        self.assertEqual(self.inputs['planning']['record']['directory_source_row'], 17162)
        self.assertEqual(self.inputs['planning']['record']['membership_source_row'], 3309903)
        charter = [r for r in self.document['roster_links'] if r['ccd_flags']['charter'] == 'Yes']
        self.assertEqual(charter, [])

    def test_missing_and_nonintegral_cells_never_zero(self):
        for raw in ['', '-1', '-2', '-3', '*', '**', '•']:
            self.assertIsNone(audit.count(raw)); self.assertIsNone(audit.number(raw))
        self.assertEqual(audit.count('0'), 0)
        self.assertEqual(audit.count('100000000000000000001'), 100000000000000000001)
        for raw in ['-4', 'nan', 'inf', 'abc', True, 1, None]:
            with self.subTest(raw=raw), self.assertRaises(ValueError): audit.count(raw)
        with self.assertRaises(ValueError): audit.count('1.5')

    def test_offline_replay_requires_no_original_download_or_fit(self):
        with mock.patch.object(audit.zipfile, 'ZipFile', side_effect=AssertionError('Original ZIP unavailable')), \
                mock.patch.object(audit.subprocess, 'Popen', side_effect=AssertionError('Original stream unavailable')):
            self.assertEqual(audit.validate(self.document)['native_campuses'], 239)

    def test_rebuild_normalizes_bootstrap_dictionary_position_for_identical_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'audit.json'
            inputs = dict(self.inputs)
            # The original-file parser emits definitions before planning, while
            # a separately extracted bootstrap can put them after planning.
            definitions = inputs.pop('definitions')
            planning = inputs.pop('planning')
            inputs['definitions'] = definitions
            inputs['planning'] = planning
            audit.build(inputs, output)
            self.assertEqual(output.read_bytes(), audit.OUTPUT.read_bytes())
            audit.build(self.inputs, output)
            self.assertEqual(output.read_bytes(), audit.OUTPUT.read_bytes())

    def test_source_and_typed_evidence_corruptions_rejected(self):
        mutations = [
            lambda d: d.update(schema_version=1.0), lambda d: d.update(year=2025.0),
            lambda d: d.update(approved_for_source=0), lambda d: d.update(approved_for_modeling=True),
            lambda d: d.update(models=[]), lambda d: d.update(status='ready'),
            lambda d: d['sources']['assessment'].update(sha256='0' * 64),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CPNTALLC='0'),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CAMPUS=int('057905001')),
            lambda d: d['raw_inputs']['assessment']['records'][0]['raw'].update(CDA38AM0E225R='0'),
            lambda d: d['raw_inputs']['assessment']['records'][0].update(source_row=3),
            lambda d: d['raw_inputs']['directory']['records'].pop(),
            lambda d: d['raw_inputs']['membership']['records'][0]['raw'].update(DMS_FLAG='Suppressed'),
            lambda d: d['raw_inputs']['stud']['labels'].__setitem__(10, '2024'),
            lambda d: d['raw_inputs']['definitions']['performance-listing']['pages'].pop(),
            lambda d: d['raw_inputs']['planning']['record'].update(enrollment=139802.0),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(self.document); mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): audit.validate(changed)

    def test_repinned_raw_fixtures_fail_semantic_identity_grade_income_and_typed_rows(self):
        mutations = [
            lambda d: d['raw_inputs']['directory']['records'][0]['raw'].update(LEAID='4816231'),
            lambda d: d['raw_inputs']['directory']['records'][0]['raw'].update(UPDATED_STATUS='9'),
            lambda d: d['raw_inputs']['directory']['records'][0].update(source_row=True),
            lambda d: d['raw_inputs']['directory']['records'][0].update(source_row=0),
            lambda d: d['raw_inputs']['directory'].update(header_source_row=1.),
            lambda d: d['raw_inputs']['stud'].update(labels_source_row=True),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(DISTRICT='057906'),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CAMPUS='57905001'),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CPNTG09C='-1'),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CPNTALLC='0'),
            lambda d: d['raw_inputs']['stud']['records'][0]['raw'].update(CPNTECOC='0'),
            lambda d: d['raw_inputs']['membership']['records'][0]['raw'].update(SEX='Male'),
            lambda d: d['raw_inputs']['assessment']['records'][0]['raw'].update(CDA38AM0E225R='10.5'),
            lambda d: d['raw_inputs']['assessment']['records'][0]['raw'].update(CDA38AM0E225R='101'),
            lambda d: d['raw_inputs']['definitions']['glossary']['pages'].pop(),
            lambda d: d['raw_inputs']['ref']['records'].pop(),
            lambda d: d['raw_inputs']['stud']['labels'].__setitem__(
                d['raw_inputs']['stud']['header'].index('CPNTALLC'), 'Campus 2024 Student Enrollment: All Students Count'),
        ]
        for index, mutate in enumerate(mutations):
            changed = copy.deepcopy(self.document); mutate(changed)
            with self.subTest(index=index), mock.patch.object(audit, 'RAW_INPUT_SHA', audit.fingerprint(changed['raw_inputs'])), self.assertRaises(ValueError):
                audit.validate(changed)

    def test_plain_income_and_rate_helpers_reject_bad_numeric_types_and_scope(self):
        income = audit.income_evidence(self.native['057905212'])
        for field, value in [('CPNTECOP', True), ('CPNTECOC', 'NaN'), ('CPNTALLC', None)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.income_evidence(dict(self.native['057905212'], **{field:value}))
        for field, value in [(audit.FIELDS['math'][2], True), (audit.FIELDS['math'][0], '1.5')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.subject_evidence(dict(self.outcomes['057905212'], **{field:value}), 'math', True, income)
        for subject, applicable in [('science', True), ('math', 1), ('math', None)]:
            with self.subTest(subject=subject, applicable=applicable), self.assertRaises(ValueError):
                audit.subject_evidence(self.outcomes['057905212'], subject, applicable, income)

    def test_repinned_planning_row_references_require_exact_integer_types(self):
        for field in ['directory_source_row', 'membership_source_row', 'enrollment', 'school_directory_operational_count']:
            for value in [float(self.inputs['planning']['record'][field]), True, 0]:
                changed = copy.deepcopy(self.document)
                changed['raw_inputs']['planning']['record'][field] = value
                with self.subTest(field=field, value=value), mock.patch.object(audit, 'RAW_INPUT_SHA', audit.fingerprint(changed['raw_inputs'])), self.assertRaisesRegex(ValueError, 'exact positive integers'):
                    audit.validate(changed)
        changed = copy.deepcopy(self.document)
        changed['raw_inputs']['planning']['record']['potential_cohorts']['ES'] = 189.
        with mock.patch.object(audit, 'RAW_INPUT_SHA', audit.fingerprint(changed['raw_inputs'])), self.assertRaisesRegex(ValueError, 'typed cohort counts'):
            audit.validate(changed)

    def test_derived_approval_denominator_population_and_income_corruptions_rejected(self):
        mutations = [
            lambda d: d['coverage'].update(verified_valid_score_counts=420),
            lambda d: d['coverage'].update(sampling_intervals_available=True),
            lambda d: d['coverage']['prospective_subject_members'].update(math=188.0),
            lambda d: d['roster_links'][0]['subjects']['math'].update(valid_scores=100),
            lambda d: d['roster_links'][0]['subjects']['math'].update(sampling_variance=0),
            lambda d: d['roster_links'][0]['subjects']['combined'].update(sampling_interval_available=True),
            lambda d: d['roster_links'][0]['income'].update(snapshot_date='2023-10-27'),
            lambda d: d['cohorts']['prospective_grade_school']['subjects']['math'].update(approved_for_modeling=True),
            lambda d: d['cohorts']['prospective_grade_school']['subjects']['combined']['prospective_native_school_ids'].append('057905039'),
            lambda d: d['enrollment_reconciliation'].update(native_campus_sum=139776),
            lambda d: d['outside_grade_school_population'].pop(),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(self.document); mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): audit.validate(changed)
        snapshot = audit.load_texas(); snapshot['profiles'][0]['profile_row'] = 0
        with self.assertRaises(ValueError): audit.validate(self.document, snapshot)


if __name__ == '__main__':
    unittest.main()

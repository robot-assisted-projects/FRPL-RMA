import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_cobb as cobb


class CobbSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(cobb.OUTPUT.read_text())
        cls.snapshot = cobb.load_state_snapshot()

    def test_original_population_individual_income_and_direct_published_rates(self):
        coverage = cobb.validate(self.document)
        self.assertEqual(coverage['directory_records'], 110)
        self.assertEqual(coverage['status'], {'Open': 110})
        self.assertEqual(coverage['prospective_grade_profiles'], 90)
        self.assertEqual(coverage['prospective_usable'], {'math': 90, 'reading': 90, 'combined': 90})
        source = {e['source_row']: e['raw'] for e in self.document['raw_inputs']['assessment']['records']}
        for row in self.document['roster_links']:
            if not row['source_profile_eligible']:
                continue
            self.assertEqual(row['income']['percentage'], 100 * row['income']['reported_direct_certification'] / row['income']['reported_membership'])
            for subject in ['math', 'reading']:
                outcome = row['subjects'][subject]
                raw = source[outcome['source_row']]
                self.assertEqual(outcome['native_rate'], 100 * float(raw['ProficientOrAbove_percent']))
                self.assertEqual(raw['StateAssignedSchID'], row['native_school_id'][3:])
            self.assertEqual(row['subjects']['combined']['native_rate'],
                             (row['subjects']['math']['native_rate'] + row['subjects']['reading']['native_rate']) / 2)

    def test_primary_high_mixed_charter_and_virtual_records_are_preserved(self):
        coverage = self.document['coverage']
        self.assertEqual(coverage['operational_offered_scope'], {'ES': 92, 'HS': 16, 'mixed': 2})
        self.assertEqual(set(coverage['primary_only_ids']), {'130129000552', '130129003528'})
        self.assertEqual(coverage['operational_CCD_charters'], {'No': 109, 'Yes': 1})
        self.assertEqual(coverage['prospective_charters'], 0)
        charter = next(r for r in self.document['roster_links'] if r['ccd_flags']['charter'] == 'Yes')
        self.assertFalse(charter['source_profile_eligible'])
        self.assertEqual(charter['offered']['scope'], 'HS')
        for entry in self.document['raw_inputs']['assessment']['records']:
            self.assertIn('SchVirtual', entry['raw'])
            self.assertIn('Flag_CutScoreChange_math', entry['raw'])

    def test_source_only_false_approvals_and_all_unverified_score_limits(self):
        self.assertEqual(self.document['scope'], 'source_cohort_audit_only')
        self.assertIs(self.document['approved_for_source'], False)
        self.assertIs(self.document['approved_for_modeling'], False)
        self.assertEqual(self.document['coverage']['model_results'], 0)
        self.assertFalse(self.document['coverage']['EOG_accelerated_EOC_population_certified'])
        for row in self.document['roster_links']:
            for result in row['subjects'].values():
                for field in ['tested', 'valid_scores', 'sampling_variance', 'low', 'high']:
                    self.assertIsNone(result[field])
                self.assertFalse(result['ten_valid_scored_floor_certified'])
                self.assertFalse(result['sampling_interval_available'])
        for field, value in [('approved_for_source', True), ('approved_for_modeling', True), ('year', True), ('scope', 'ready')]:
            bad = copy.deepcopy(self.document)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                cobb.derive(bad, self.snapshot)

    def test_complete_original_and_omitted_population_inventories(self):
        coverage = self.document['coverage']
        self.assertEqual((coverage['complete_original_records'], coverage['complete_original_typed_cells']), (25662, 865003))
        self.assertEqual((coverage['original_records'], coverage['original_typed_cells']), (2260, 68573))
        self.assertEqual(coverage['omitted_original_records'], 23402)
        for table in cobb.TABLES:
            raw = self.document['raw_inputs'][table]
            omitted = self.document['raw_inputs']['omitted_original_populations'][table]
            kept = [e['source_row'] for e in raw['records']]
            rows = omitted['omitted_source_rows']
            self.assertEqual(len(set(kept + rows)), omitted['complete_original_records'])
            self.assertEqual(len(rows), omitted['omitted_records'])
            self.assertEqual(sum(x['records'] for x in omitted['omitted_population_counts']), len(rows))
            self.assertEqual(sum(len(x) for x in omitted['omitted_rows_by_original_identity'].values()), len(rows))
            self.assertRegex(omitted['complete_target_records_sha256'], r'^[a-f0-9]{64}$')

    def test_primary_georgia_definitions_and_no_inferred_attribution_clearance(self):
        evidence = self.document['source_definition_evidence']
        note = next(r for r in evidence['Georgia_original_notes'] if r['worksheet'] == 'Data Notes' and r['source_row'] == 129)
        self.assertIn('Medicaid income', note['raw'][9])
        self.assertIn('foster children', note['raw'][9])
        member = next(r for r in evidence['Georgia_original_notes'] if r['worksheet'] == 'CCD Membership Metadata')
        self.assertIn('state funded programs', ' '.join(str(v) for v in member['raw']))
        self.assertIn('outside programs', ' '.join(str(v) for v in member['raw']))
        self.assertEqual(evidence['exact_Cobb_named_notes'], [])
        self.assertTrue(evidence['note_absence_does_not_certify_attribution'])
        self.assertEqual(self.document['coverage']['district_minus_reported_operational_enrollment'], 0)
        self.assertEqual(self.document['coverage']['native_only_ids'], [])

    def test_exact_identity_rejects_names_padding_foreign_state_and_year(self):
        raw = copy.deepcopy(self.document['raw_inputs']['directory']['records'][0]['raw'])
        for field, value in [('NCESSCH', raw['NCESSCH'][1:]), ('ST_SCHID', 'GA-633-194'),
                             ('LEAID', '1302550'), ('ST', 'TN'), ('SCHOOL_YEAR', '2023-2024')]:
            bad = dict(raw, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                cobb.ccd_identity(bad)

    def test_reported_count_types_masks_zeros_and_income_denominator(self):
        for value in [True, 1, 1.0, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                cobb.reported_count({'STUDENT_COUNT': value, 'DMS_FLAG': 'Reported'})
        for value in ['-1', '-9', '', '1.0', '>95']:
            self.assertIsNone(cobb.reported_count({'STUDENT_COUNT': value, 'DMS_FLAG': 'Reported'}))
        self.assertEqual(cobb.reported_count({'STUDENT_COUNT': '0', 'DMS_FLAG': 'Reported'}), 0)
        self.assertIsNone(cobb.reported_count({'STUDENT_COUNT': '0', 'DMS_FLAG': 'Derived'}))
        total = {'source_row': 2, 'raw': {'STUDENT_COUNT': '100', 'DMS_FLAG': 'Reported'}}
        direct = {'source_row': 3, 'raw': {'STUDENT_COUNT': '0', 'DMS_FLAG': 'Reported',
            'DATA_GROUP': 'Direct Certification', 'TOTAL_INDICATOR': 'Education Unit Total', 'LUNCH_PROGRAM': 'Not Applicable'}}
        self.assertEqual(cobb.income_evidence(total, direct)['percentage'], 0)
        direct['raw']['STUDENT_COUNT'] = '101'
        self.assertFalse(cobb.income_evidence(total, direct)['usable'])
        direct['raw']['STUDENT_COUNT'] = '50'
        direct['raw']['DATA_GROUP'] = 'Free Lunch'
        with self.assertRaises(ValueError):
            cobb.income_evidence(total, direct)

    def test_native_rate_masks_ranges_and_direct_precision(self):
        self.assertEqual(cobb.exact_rate('.567'), 56.699999999999996)
        self.assertEqual(cobb.exact_rate('0'), 0)
        self.assertEqual(cobb.exact_rate('1'), 100)
        for value in ['', '-1', '.4-.5', '<.05', '>95', 'NaN', '1.01']:
            self.assertIsNone(cobb.exact_rate(value), value)
        for value in [True, 0.5, None]:
            with self.assertRaises(ValueError):
                cobb.exact_rate(value)

    def test_protected_or_positive_high_grade_never_becomes_lower_zero(self):
        profile = next(r for r in self.document['roster_links'] if r['source_profile_eligible'])
        inputs = self.document['raw_inputs']['membership']['records']
        by_row = {e['source_row']: e for e in inputs}
        total = by_row[profile['membership']['total_source_row']]
        grades = {g: by_row[i] for g, i in profile['membership']['grade_source_rows'].items()}
        for value, flag in [('1', 'Reported'), ('-1', 'Reported'), ('0', 'Suppressed')]:
            bad = copy.deepcopy(grades)
            bad['Grade 9'] = {'source_row': 2, 'raw': {'STUDENT_COUNT': value, 'DMS_FLAG': flag}}
            self.assertFalse(cobb.membership_evidence(total, bad)['reconciled_pure_lower'])
        bad = copy.deepcopy(grades)
        bad['Grade 9'] = {'source_row': 2, 'raw': {'STUDENT_COUNT': '0', 'DMS_FLAG': 'Derived'}}
        self.assertTrue(cobb.membership_evidence(total, bad)['reconciled_pure_lower'])

    def test_raw_headers_row_types_and_omission_loss_reject(self):
        changes = [lambda d: d['raw_inputs']['directory']['records'][0].update(source_row=True),
                   lambda d: d['raw_inputs']['directory']['records'][0].update(source_row=2.0),
                   lambda d: d['raw_inputs']['assessment']['header'].remove('ProficientOrAbove_percent'),
                   lambda d: d['raw_inputs']['planning']['record'].update(directory_source_row=1.0),
                   lambda d: d['raw_inputs']['omitted_original_populations']['assessment']['omitted_source_rows'].pop()]
        for change in changes:
            bad = copy.deepcopy(self.document)
            change(bad)
            with self.assertRaises(ValueError):
                cobb.validate(bad, self.snapshot)

    def test_coherent_raw_schema_definition_identity_and_public_runtime_repins_fail(self):
        for kind in ['raw', 'schema', 'definition', 'identity']:
            bad = copy.deepcopy(self.document)
            inputs = bad['raw_inputs']
            if kind == 'raw':
                inputs['directory']['records'][0]['raw']['WEBSITE'] = 'https://forged.invalid/'
            elif kind == 'schema':
                inputs['assessment']['header'][0] = 'Wrong subject population'
            elif kind == 'definition':
                inputs['definitions']['ccd_state_notes_2025']['worksheets']['Data Notes']['records'][128]['raw'][9] = 'Direct certification is universal school-wide meal receipt.'
            else:
                inputs['directory']['records'][0]['raw']['NCESSCH'] = '130129099999'
            aliases = dict(RAW_INPUT_SHA=cobb.fingerprint(inputs), ORIGINAL_SCHEMA_SHA=cobb.schema_fingerprint(inputs),
                DEFINITION_INPUT_SHA=cobb.fingerprint(inputs['definitions']), ORIGINAL_IDENTITY_SHA=cobb.identity_fingerprint(inputs))
            with self.subTest(kind=kind), patch.multiple(cobb, **aliases):
                with patch.object(cobb, 'RUNTIME_CONTRACT_SHA', cobb.fingerprint(cobb.runtime_contract())):
                    with self.assertRaises(ValueError):
                        cobb.validate(bad, self.snapshot)

    def test_current_policy_selector_year_and_public_pin_changes_fail_cached(self):
        for name, value in [('LEA', '1302550'), ('NATIVE_DISTRICT', '667'), ('YEAR', 2024),
                            ('POLICY_SHA', '0' * 64), ('RUNTIME_CONTRACT_SHA', '0' * 64),
                            ('RAW_INPUT_SHA', '0' * 64), ('DEFINITION_INPUT_SHA', '0' * 64)]:
            with self.subTest(name=name), patch.object(cobb, name, value), self.assertRaises(ValueError):
                cobb.validate(self.document, self.snapshot)
        for field, value in [('AssmtType', 'Alternate'), ('AssmtName', 'Georgia Milestones EOC'),
                             ('StudentGroup', 'Economically Disadvantaged'), ('GradeLevel', 'G03')]:
            selector = dict(cobb.ASSESSMENT_SELECTOR, **{field: value})
            with self.subTest(field=field), patch.object(cobb, 'ASSESSMENT_SELECTOR', selector), self.assertRaises(ValueError):
                cobb.validate(self.document, self.snapshot)

    def test_missing_changed_secondary_inputs_reject_even_cached_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = ['data/source/ccd-state-snapshots.json', cobb.SOURCES['ga_all_students_crosscheck']['path']]
            for name in paths:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cobb.ROOT / name, destination)
            with patch.object(cobb, 'ROOT', root):
                cobb.validate(self.document, self.snapshot)
                for name in paths:
                    target = root / name
                    original = target.read_bytes()
                    target.write_bytes(original + b' ')
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        cobb.validate(self.document, self.snapshot)
                    target.unlink()
                    with self.assertRaises(FileNotFoundError):
                        cobb.derive(self.document, self.snapshot)
                    target.write_bytes(original)
            cached = copy.deepcopy(self.snapshot)
            cached['year'] = 2024
            with self.assertRaises(ValueError):
                cobb.validate(self.document, cached)

    def test_offline_source_replay_is_deterministic_and_writes_no_store_or_exports(self):
        before = cobb.OUTPUT.read_bytes()
        self.assertEqual(cobb.derive(self.document), cobb.derive(self.document, self.snapshot))
        cobb.validate(self.document)
        self.assertEqual(cobb.OUTPUT.read_bytes(), before)
        self.assertFalse((cobb.ROOT / 'data/cobb').exists())
        self.assertNotIn('models', self.document)


if __name__ == '__main__':
    unittest.main()

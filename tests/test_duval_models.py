import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_duval_models as audit


class DuvalNumericalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = audit.load_roster()
        cls.document = json.loads(audit.OUTPUT.read_text())
        cls.expected = audit.build(cls.roster)
        cls.models = {m['subject']: m for m in cls.document['models']}

    def test_compact_pins_complete_rosters_source_scope_and_three_fixed_populations(self):
        self.assertEqual(audit.validate(self.document, self.expected), {f'duval-2025-ES-{s}':146 for s in audit.SUBJECTS})
        self.assertEqual((self.document['scope'], self.document['status']), ('numerical_audit_only', 'numerically_verified_pending_integration'))
        self.assertIs(self.document['approved_for_source'], False); self.assertIs(self.document['approved_for_modeling'], False)
        self.assertEqual(self.document['hard_holds'], [])
        population = self.document['frozen_population']
        for field, count in [('complete_native_school_ids',201), ('complete_directory_ncessch',211),
                ('operational_directory_ncessch',203), ('grade_school_configuration_ids',150),
                ('high_school_configuration_ids',24), ('mixed_configuration_ids',24),
                ('primary_configuration_ids',4), ('nonoperational_directory_ncessch',8),
                ('unmatched_native_school_ids',1), ('operational_without_native_fall_ids',3)]:
            self.assertEqual(len(population[field]), count)
        self.assertEqual(population['unmatched_native_school_ids'], ['16-0734'])
        self.assertEqual(len(self.document['retained_scope_exclusions']), 61)
        self.assertEqual(self.document['retained_outside_source_profiles'][0]['school_id'], '16-0734')
        reference = self.document['retained_source_reference']
        self.assertEqual((reference['complete_original_record_count'], reference['complete_original_cell_count']), (2495,59985))
        self.assertEqual(reference['sha256'], audit.ROSTER_SHA)
        for key in ['raw_inputs', 'retained_source_evidence', 'source_definition_evidence']:
            self.assertNotIn(key, self.document)
        for model in self.document['models']:
            self.assertEqual(model['coefficients']['n'], 146)
            self.assertEqual(model['coverage']['grade_school_configuration_profiles'], 150)
            self.assertEqual(model['coverage']['excluded_configuration_profiles'], 4)
            self.assertEqual(model['coverage']['charter'], {'No':116, 'Yes':30})
            self.assertEqual(model['diagnostics']['income_design_rank'], 2)
            self.assertEqual((model['diagnostics']['full_residual_degrees_of_freedom'], model['diagnostics']['deleted_residual_degrees_of_freedom']), (144,143))
            self.assertEqual(model['independent_verification']['explicit_deleted_fits'], 146)
            self.assertGreater(model['diagnostics']['minimum_deleted_sse'], 0.)
            self.assertGreater(model['diagnostics']['minimum_deleted_residual_scale'], 0.)
            self.assertTrue(all(v is None or v < audit.VERIFY_TOLERANCE for v in model['independent_verification']['maximum_absolute_errors'].values()))

    def test_original_compact_table_worksheet_row_column_fields_exact_ids_and_individual_income(self):
        raw = self.roster['raw_inputs']
        indexed = {name:{e['source_row']:e['raw'] for e in raw[name]['records']} for name in audit.roster_audit.TABLES}
        for model in self.document['models']:
            for row in model['inputs']:
                refs = row['source_refs']; link = self.roster['roster_links'][refs['roster_link_index']]
                directory = indexed['directory'][refs['directory']['source_row']]
                self.assertEqual((directory['LEAID'], directory['ST_LEAID'], directory['NCESSCH'], directory['ST_SCHID']), ('1200480','FL-16',row['ncessch'],row['native_school_id']))
                self.assertEqual(row['school_id'], row['native_school_id'][3:])
                for ref in [refs['income'], refs['native_enrollment']] + list(refs['outcomes'].values()):
                    table = raw[ref['table']]
                    self.assertEqual((ref['source_id'], ref['worksheet']), (table['source_id'], table['worksheet']))
                    self.assertEqual(ref['fields'], [table['header_rows'][-1][i] for i in ref['columns']])
                    cells = indexed[ref['table']][ref['source_row']]
                    self.assertEqual(audit.roster_audit.native_identity(cells), row['school_id'])
                income = indexed['native_income'][refs['income']['source_row']]
                self.assertEqual(refs['income']['columns'], [4,5,6,7,8])
                self.assertEqual((row['income_enrollment'], row['individual_economic_count']), (income[4], income[5]+income[6]+income[8]))
                self.assertEqual(row['income_pct'], 100*(income[5]+income[6]+income[8])/income[4])
                self.assertEqual(income[7], 0)
                grades = indexed['native_grades'][refs['native_enrollment']['source_row']]
                self.assertEqual(grades[14:18], [0]*4)
                self.assertTrue(any(v=='*' or audit.original_count(v) not in {None,0} for v in grades[8:14]))
                for subject in ['math','reading']:
                    ref = refs['outcomes'][subject]; native = indexed['native_assessment'][ref['source_row']]
                    self.assertEqual((native[3], native[47]), ('','N'))
                    self.assertIn(audit.SUBJECT_FIELDS[subject], ref['columns'])
                    self.assertEqual(row['raw_published_rates'][subject], native[audit.SUBJECT_FIELDS[subject]])
                    self.assertEqual(row['outcome_by_subject'][subject], float(native[audit.SUBJECT_FIELDS[subject]]))
                    self.assertEqual(row['outcome_by_subject'][subject], link['subjects'][subject]['native_rate'])
            missing = model['coverage']['excluded_configuration_records']
            self.assertEqual({r['school_id'] for r in missing}, {'16-0061','16-0271','16-0281','16-0171'})
            self.assertTrue(all(r['source_refs']['outcomes'] == {'math':None,'reading':None} for r in missing))

    def test_combined_has_own_fit_scale_deletions_and_external_t_even_when_coefficients_are_linear(self):
        math_model, ela_model, combined = [self.models[s] for s in audit.SUBJECTS]
        self.assertEqual([r['school_id'] for r in math_model['inputs']], [r['school_id'] for r in ela_model['inputs']])
        self.assertEqual([r['school_id'] for r in math_model['inputs']], [r['school_id'] for r in combined['inputs']])
        for key in ['intercept','slope']:
            self.assertAlmostEqual(combined['coefficients'][key], (math_model['coefficients'][key]+ela_model['coefficients'][key])/2, delta=2e-10)
        for row in combined['inputs']:
            self.assertEqual(row['outcome_pct'], (row['outcome_by_subject']['math']+row['outcome_by_subject']['reading'])/2)
        self.assertGreater(abs(combined['diagnostics']['residual_standard_error'] - (math_model['diagnostics']['residual_standard_error']+ela_model['diagnostics']['residual_standard_error'])/2), .1)
        self.assertTrue(any(abs(c['studentized']-(m['studentized']+e['studentized'])/2)>.01 for c,m,e in zip(combined['results'],math_model['results'],ela_model['results'])))
        changed = copy.deepcopy(self.document)
        changed['models'][2]['results'][0]['studentized'] = (math_model['results'][0]['studentized']+ela_model['results'][0]['studentized'])/2
        with self.assertRaises(ValueError): audit.validate(changed, self.expected)

    def test_influence_charters_and_income_extremes_remain_members_without_prediction_clamping(self):
        for model in self.document['models']:
            self.assertEqual(sum(r['charter']=='Yes' for r in model['inputs']), 30)
            self.assertEqual(model['diagnostics']['income']['maximum'], 100.)
            self.assertLess(model['diagnostics']['income']['minimum'], 3.3)
            self.assertEqual(model['diagnostics']['predictions_outside_percentage_range'], 0)
            ids = {r['school_id'] for r in model['inputs']}
            self.assertIn('16-5401', ids); self.assertIn('16-5631', ids)
        self.assertGreater(next(r for r in self.models['math']['results'] if r['school_id']=='16-5401')['cooks_distance'], .21)
        self.assertGreater(next(r for r in self.models['reading']['results'] if r['school_id']=='16-5631')['cooks_distance'], .11)
        changed = copy.deepcopy(self.document); changed['models'][0]['results'].pop()
        with self.assertRaises(ValueError): audit.validate(changed, self.expected)

    def test_independent_selector_strict_native_scope_income_attribution_and_no_count_substitution(self):
        for mutation in ['highpositive','highmask','testedzero','fundingratio','ratecount','provider','collocated','duplicatecampus']:
            changed = copy.deepcopy(self.roster); raw = changed['raw_inputs']
            key = '16-0121'
            if mutation in ['highpositive','highmask','testedzero']:
                e = next(e for e in raw['native_grades']['records'] if audit.roster_audit.native_identity(e['raw'])==key)
                if mutation=='testedzero': e['raw'][8:14]=[0]*6
                else: e['raw'][14] = 1 if mutation=='highpositive' else '*'
            elif mutation=='fundingratio':
                e = next(e for e in raw['native_income']['records'] if audit.roster_audit.native_identity(e['raw'])==key); e['raw'][8]=e['raw'][10]
            else:
                e = next(e for e in raw['native_assessment']['records'] if audit.roster_audit.native_identity(e['raw'])==key)
                if mutation=='ratecount': e['raw'][9]=e['raw'][20]
                elif mutation=='provider': e['raw'][3]='302'
                elif mutation=='collocated': e['raw'][47]='Y'
                else: raw['native_assessment']['records'].append(copy.deepcopy(e))
            with self.subTest(mutation=mutation), mock.patch.object(audit,'require_frozen_roster'), self.assertRaises(ValueError):
                audit.selected_inputs(changed,'math')
        changed = copy.deepcopy(self.roster)
        for e in changed['raw_inputs']['native_income']['records']: e['raw'][9:12]=[999999,999999,1.]
        for e in changed['raw_inputs']['native_assessment']['records']: e['raw'][20]=0; e['raw'][53]=0.
        with mock.patch.object(audit,'require_frozen_roster'):
            values, coverage = audit.selected_inputs(changed,'math')
        self.assertEqual(values, self.models['math']['inputs'])
        self.assertEqual(coverage, self.models['math']['coverage'])
        for value in [False,3.,-1,'3']:
            with self.assertRaises(ValueError): audit.original_count(value)
        for value in [False,3.,-1,101,'3']:
            with self.assertRaises(ValueError): audit.original_rate(value)
        self.assertEqual(audit.original_count(0),0); self.assertEqual(audit.original_rate(0),0.)
        self.assertIsNone(audit.original_count('*')); self.assertIsNone(audit.original_rate(None))

    def test_current_numeric_policy_minimum_subjects_and_field_types_are_bound_on_cached_and_direct_replay(self):
        policy = copy.deepcopy(audit.POLICY); policy['models']='Drop influential schools and infer causal quality'
        mutations = [('POLICY',policy), ('MIN_SCHOOLS',30.), ('MIN_SCHOOLS',False),
            ('SUBJECTS',['math','combined']), ('ASSESSMENT','Different assessment'), ('STANDARD','Different standards'),
            ('SUBJECT_FIELDS',{'math':20,'reading':6}), ('SUBJECT_LABELS',{'math':'Science','reading':'ELA'}),
            ('INCOME_FIELDS',[4,5,6,7,10]), ('VERIFY_TOLERANCE',1.), ('NUMERIC_POLICY_SHA','0'*64), ('RUNTIME_CONTRACT_SHA','0'*64)]
        for field, value in mutations:
            with self.subTest(field=field), mock.patch.object(audit,field,value):
                with self.assertRaises(ValueError): audit.validate(self.document,self.expected)
                with self.assertRaises(ValueError): audit.selected_inputs(self.roster,'math')
        with mock.patch.object(audit,'POLICY',policy), mock.patch.object(audit,'NUMERIC_POLICY_SHA',audit.roster_audit.fingerprint(policy)):
            with self.assertRaises(ValueError): audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'MIN_SCHOOLS',30.):
            repinned = audit.roster_audit.fingerprint(audit.runtime_contract())
            with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',repinned), self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)

    def test_unweighted_raw_design_full_and_every_deleted_fit_reproduce_all_results(self):
        for m in self.document['models']:
            x = np.array([r['income_pct'] for r in m['inputs']]); y = np.array([r['outcome_pct'] for r in m['inputs']]); n = len(x)
            X = np.column_stack([np.ones(n), x]); beta = np.linalg.lstsq(X, y, rcond=None)[0]
            pred = X @ beta; residual = y - pred; sse = float(residual @ residual); scale2 = sse / (n - 2)
            H = X @ np.linalg.inv(X.T @ X) @ X.T
            self.assertAlmostEqual(float(beta[0]), m['coefficients']['intercept'], delta=2e-10)
            self.assertAlmostEqual(float(beta[1]), m['coefficients']['slope'], delta=2e-10)
            self.assertAlmostEqual(1 - sse / float((y - y.mean()) @ (y - y.mean())), m['coefficients']['r2'], delta=2e-10)
            for i, row in enumerate(m['results']):
                keep = np.arange(n) != i; D = X[keep]; b = np.linalg.lstsq(D, y[keep], rcond=None)[0]
                deleted_residual = y[keep] - D @ b; deleted_sse = float(deleted_residual @ deleted_residual)
                deleted_scale = math.sqrt(deleted_sse / (n - 3)); held = float(X[i] @ b)
                h_deleted = float(X[i] @ np.linalg.inv(D.T @ D) @ X[i])
                external_t = (y[i] - held) / (deleted_scale * math.sqrt(1 + h_deleted))
                cook = residual[i] ** 2 * H[i, i] / (2 * scale2 * (1 - H[i, i]) ** 2)
                endpoints = np.column_stack([np.ones(2), [x.min(), x.max()]])
                shift = float(np.max(np.abs(endpoints @ beta - endpoints @ b)))
                with self.subTest(subject=m['subject'], school=row['school_id']):
                    for actual, expected in [(row['predicted'], pred[i]), (row['residual'], residual[i]), (row['leverage'], H[i, i]),
                                             (row['studentized'], external_t), (row['cooks_distance'], cook),
                                             (row['deleted_intercept'], b[0]), (row['deleted_slope'], b[1]),
                                             (row['deleted_residual_scale'], deleted_scale), (row['deleted_held_out_prediction'], held),
                                             (row['deleted_held_out_prediction_leverage'], h_deleted),
                                             (row['maximum_prediction_change_on_observed_income_range'], shift)]:
                        self.assertAlmostEqual(actual, float(expected), delta=2e-9)
                    self.assertAlmostEqual(row['deleted_sse'], deleted_sse, delta=2e-9)

    def test_every_count_variance_endpoint_and_scored_floor_remains_unavailable(self):
        self.assertFalse(self.document['count_definition_status']['ten_valid_scored_floor_certified'])
        for m in self.document['models']:
            self.assertFalse(m['approved_for_source']); self.assertFalse(m['approved_for_modeling']); self.assertFalse(m['valid_score_floor_certified'])
            self.assertFalse(m['intervals']['available_for_entire_model']); self.assertFalse(m['intervals']['ten_valid_scored_floor_certified'])
            self.assertIsNone(m['intervals']['valid_score_counts']); self.assertIsNone(m['intervals']['sampling_variances'])
            for r in m['inputs']:
                self.assertEqual(r['valid_scores_by_subject'], {'math': None, 'reading': None})
                self.assertIsNone(r['display_valid_scores']); self.assertIsNone(r['sampling_variance'])
                self.assertFalse(r['ten_valid_scored_floor_certified'])
            for r in m['results']:
                self.assertTrue(all(r[k] is None for k in ['valid_scores', 'sampling_variance', 'low', 'high']))
        m = self.models['math']; passed = []; real_fit = audit.fit_model
        def capture(x, y, variance):
            passed.append(variance.copy()); return real_fit(x, y, variance)
        with mock.patch.object(audit, 'fit_model', side_effect=capture):
            result = audit.fit_audited_model(m['inputs'], m['coverage'], 'math')
        self.assertTrue(np.array_equal(passed[0], np.zeros(146)))
        self.assertTrue(all(r['low'] is None and r['high'] is None for r in result['results']))

    def test_direct_calls_reject_changed_x_y_original_references_counts_and_membership_before_fit(self):
        m=self.models['math']
        mutations=[lambda x:x.pop(),lambda x:x.reverse(),lambda x:x.append(copy.deepcopy(x[0])),
            lambda x:x[0].update(level='HS'),lambda x:x[0].update(income_year=2024),lambda x:x[0].update(income_year=2025.),
            lambda x:x[0].update(native_school_id='FL-16-9999'),lambda x:x[0].update(ncessch='120048099999'),
            lambda x:x[0].update(income_pct=False),lambda x:x[0].update(outcome_pct=float('nan')),
            lambda x:x[0].update(income_pct=x[0]['income_pct']+1e-12),
            lambda x:x[0].update(sampling_variance=0.),lambda x:x[0].update(display_valid_scores=10),
            lambda x:x[0]['valid_scores_by_subject'].update(math=10),lambda x:x[0].update(ten_valid_scored_floor_certified=True),
            lambda x:x[0]['source_refs'].update(directory_source_row=1.),
            lambda x:x[0]['source_refs']['native_enrollment'].update(source_row=1),
            lambda x:x[0]['source_refs']['outcomes']['math'].update(worksheet='Different worksheet'),
            lambda x:x[0]['raw_published_rates'].update(math=0),
            lambda x:x[0].update(individual_economic_count=0)]
        for i,mutation in enumerate(mutations):
            inputs=copy.deepcopy(m['inputs']);mutation(inputs)
            with self.subTest(i=i),mock.patch.object(audit,'fit_model',side_effect=AssertionError('No fit before source validation')),self.assertRaises(ValueError):
                audit.fit_audited_model(inputs,m['coverage'],'math')
        with mock.patch.object(audit,'fit_model',side_effect=AssertionError('No fit below floor')),self.assertRaisesRegex(ValueError,'at least 30'):
            audit.fit_audited_model(m['inputs'][:29],m['coverage'],'math')
        for subject in ['high','mixed','science']:
            with self.assertRaises(ValueError):audit.fit_audited_model(m['inputs'],m['coverage'],subject)

    def test_rank_positive_full_and_deleted_scales_are_hard_gates(self):
        m = self.models['math']; x = np.array([r['income_pct'] for r in m['inputs']]); y = np.array([r['outcome_pct'] for r in m['inputs']]); zero = np.zeros(len(x))
        for bad_x, bad_y in [(np.full(len(x), 20.), y), (x, 10. + .5 * x), (np.r_[30., np.full(len(x) - 1, 20.)], y)]:
            with self.assertRaises(ValueError): audit.fit_model(bad_x, bad_y, zero)
        one_outlier = 10. + .5 * x; one_outlier[0] += 1.
        # A finite full fit can conceal an exactly linear deleted sample. Construct
        # the purported returned fit directly so the independent verifier's gate
        # is tested even if the shared analytic fitter already rejects this case.
        centered = x - x.mean(); design = np.column_stack([np.ones(len(x)), centered])
        beta = np.linalg.lstsq(design, one_outlier, rcond=None)[0]
        predicted = design @ beta; residual = one_outlier - predicted
        leverage = 1 / len(x) + centered ** 2 / (centered @ centered)
        coefficients = {'n': len(x), 'intercept': float(beta[0] - beta[1] * x.mean()),
                        'slope': float(beta[1]),
                        'r2': float(1 - (residual @ residual) / ((one_outlier - one_outlier.mean()) @ (one_outlier - one_outlier.mean())))}
        rows = [dict(actual=float(a), predicted=float(p), residual=float(e), leverage=float(h),
                     studentized=0., low=None, high=None)
                for a, p, e, h in zip(one_outlier, predicted, residual, leverage)]
        with self.assertRaisesRegex(ValueError, 'deleted-school residual scale'):
            audit.verify_independently(x, one_outlier, coefficients, rows)
        for bad in [np.full(len(x), np.nan), np.full(len(x), np.inf)]:
            with self.assertRaises(ValueError): audit.verify_independently(bad, y, m['coefficients'], m['results'])

    def test_corrupt_fitter_coefficients_results_and_boolean_numbers_fail_independent_verification(self):
        m = self.models['math']; real_fit = audit.fit_model
        for location, key, bad in [('coefficients', 'intercept', 0.), ('coefficients', 'n', False),
                                  ('coefficients', 'r2', float('nan')), ('results', 'actual', 0.),
                                  ('results', 'predicted', float('inf')), ('results', 'residual', False),
                                  ('results', 'studentized', 0.), ('results', 'leverage', False)]:
            def corrupt(x, y, variance):
                coefficients, rows = real_fit(x, y, variance)
                (coefficients if location == 'coefficients' else rows[0])[key] = bad
                return coefficients, rows
            with self.subTest(location=location, key=key), mock.patch.object(audit, 'fit_model', side_effect=corrupt), self.assertRaisesRegex(ValueError, 'Independent'):
                audit.fit_audited_model(m['inputs'], m['coverage'], 'math')

    def test_saved_compact_source_policy_approval_population_and_count_mutations_fail_exact_replay(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),
            lambda d:d.update(scope='ready'),lambda d:d['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['sources']['roster_audit'].update(sha256='0'*64),
            lambda d:d['sources'].update(original_raw_input_sha256='0'*64),
            lambda d:d['retained_source_reference'].update(complete_original_cell_count=59985.),
            lambda d:d['frozen_population']['eligible_school_ids_by_subject']['math'].append('16-0734'),
            lambda d:d['models'][0]['inputs'][0].update(income_pct=25.),
            lambda d:d['models'][0]['inputs'][0]['source_refs']['outcomes']['math'].update(source_row=False),
            lambda d:d['models'][0]['coverage']['excluded_configuration_records'].clear(),
            lambda d:d['models'][0]['intervals'].update(valid_score_counts=100),
            lambda d:d['models'][0]['results'][0].update(actual=d['models'][0]['results'][0]['actual']+1e-12),
            lambda d:d['models'][0]['results'][0].update(low=0.),lambda d:d['models'][0]['results'][0].update(sampling_variance=0.),
            lambda d:d['models'][0]['independent_verification'].update(tolerance_absolute=1.),
            lambda d:d['retained_scope_exclusions'].pop()]
        for i,mutation in enumerate(mutations):
            changed=copy.deepcopy(self.document);mutation(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(changed,self.expected)

    def test_cached_expected_replay_still_requires_available_unchanged_complete_source_and_all_pins(self):
        original=Path.read_bytes
        for corrupt in [b'{}',None]:
            def read(path):
                if path==audit.ROSTER:
                    if corrupt is None:raise FileNotFoundError('Linked complete source missing')
                    return corrupt
                return original(path)
            with self.subTest(corrupt=corrupt),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):
                audit.validate(self.document,self.expected)
        for pin in ['SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA','SOURCE_RAW_SHA','SOURCE_SCHEMA_SHA','SOURCE_DEFINITION_SHA','SOURCE_IDENTITY_SHA']:
            with self.subTest(pin=pin),mock.patch.object(audit,pin,'0'*64),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'load_roster',wraps=audit.load_roster) as source:
            self.assertEqual(audit.validate(self.document,self.expected),{f'duval-2025-ES-{s}':146 for s in audit.SUBJECTS})
            self.assertGreater(source.call_count,0)

    def test_saved_numerical_fields_require_finite_correct_types_and_tolerance(self):
        for key in ['predicted', 'residual', 'studentized', 'leverage', 'cooks_distance', 'deleted_sse', 'deleted_residual_scale', 'maximum_prediction_change_on_observed_income_range']:
            for bad in [False, float('nan'), float('inf')]:
                d = copy.deepcopy(self.document); d['models'][0]['results'][0][key] = bad
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError): audit.validate(d, self.expected)
        d = copy.deepcopy(self.document); d['models'][0]['coefficients']['slope'] += .01
        with self.assertRaises(ValueError): audit.validate(d, self.expected)
        self.assertFalse(audit.numeric_equal(True, 1.)); self.assertFalse(audit.numeric_equal(1, 1.))
        self.assertFalse(audit.numeric_equal(2025., 2025))
        self.assertTrue(audit.numeric_equal(1. + 1e-12, 1.))

    def test_pinned_historical_source_and_in_memory_source_drift_cannot_be_fit(self):
        for path, sha in [(audit.ROSTER, audit.ROSTER_SHA), (audit.SOURCE_CODE, audit.SOURCE_CODE_SHA), (audit.SOURCE_TESTS, audit.SOURCE_TESTS_SHA)]:
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sha)
        self.assertEqual(audit.roster_audit.fingerprint(self.roster['policy']), audit.SOURCE_POLICY_SHA)
        with mock.patch.object(audit, 'SOURCE_TESTS_SHA', '0' * 64), self.assertRaisesRegex(ValueError, 'source tests changed'):
            audit.load_roster()
        with mock.patch.object(audit, 'SOURCE_POLICY_SHA', '0' * 64), self.assertRaisesRegex(ValueError, 'source policy/raw/schema/definition/identity pins changed'):
            audit.load_roster()
        changed = copy.deepcopy(self.roster); changed['roster_links'][0]['income']['percentage'] = 0.
        with self.assertRaises(ValueError): audit.build(changed)
        with self.assertRaises(ValueError): audit.selected_inputs(changed, 'math')
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'changed.json'; p.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): audit.load_roster(p)

    def test_two_numerical_builds_and_read_only_offline_replay_are_identical(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / 'a.json', Path(t) / 'b.json'
            first = audit.prepare(a); second = audit.prepare(b)
            self.assertEqual(first, second); self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(a.read_bytes(), audit.OUTPUT.read_bytes())
            before = a.read_bytes()
            with mock.patch.object(audit.roster_audit.subprocess, 'Popen', side_effect=AssertionError('No original stream')), \
                    mock.patch.object(audit.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original extraction')):
                self.assertEqual(audit.prepare(a, check=True), first)
            self.assertEqual(before, a.read_bytes())


if __name__ == '__main__':
    unittest.main()

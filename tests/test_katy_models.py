import copy
import hashlib
import io
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
import audit_katy_models as audit


class KatyNumericalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = audit.load_roster()
        cls.document = json.loads(audit.OUTPUT.read_text())
        cls.expected = audit.build(cls.roster)
        cls.models = {m['subject']: m for m in cls.document['models']}

    def test_compact_source_pins_and_complete_membership_are_preserved(self):
        self.assertEqual(audit.validate(self.document,self.expected), {f'katy-2025-ES-{s}':64 for s in audit.SUBJECTS})
        self.assertEqual((self.document['scope'],self.document['status']),('numerical_audit_only','numerically_verified_pending_integration'))
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        self.assertEqual(self.document['hard_holds'],[])
        p=self.document['frozen_population']
        for key,count in [('complete_directory_school_ids',81),('operational_school_ids',79),
                          ('grade_school_configuration_ids',65),('grade_school_native_ids',65),
                          ('high_school_configuration_ids',11),('mixed_configuration_ids',1),
                          ('primary_configuration_ids',0),('nonoperational_school_ids',2)]:
            self.assertEqual(len(p[key]),count)
        self.assertEqual(len(self.document['retained_scope_exclusions']),16)
        reference=self.document['retained_source_reference']
        self.assertEqual(reference['complete_original_record_count'],8905)
        self.assertEqual(reference['complete_original_cell_count'],178885)
        self.assertEqual(reference['sha256'],audit.ROSTER_SHA)
        self.assertEqual((reference['retained_original_record_count'],reference['retained_original_cell_count']),(915,35746))
        self.assertEqual(reference['complete_omitted_inventories'],self.roster['coverage']['complete_omitted_original_inventories'])
        self.assertNotIn('raw_inputs',self.document);self.assertNotIn('retained_source_evidence',self.document)
        self.assertEqual(self.document['sources']['original_raw_input_sha256'],audit.roster_audit.RAW_INPUT_SHA)
        for m in self.document['models']:
            self.assertEqual(m['coefficients']['n'],64)
            self.assertEqual(m['coverage']['grade_school_configuration_profiles'],65)
            self.assertEqual(m['coverage']['excluded_configuration_profiles'],1)
            self.assertEqual(m['diagnostics']['income_design_rank'],2)
            self.assertEqual(m['diagnostics']['full_residual_degrees_of_freedom'],62)
            self.assertEqual(m['diagnostics']['deleted_residual_degrees_of_freedom'],61)
            self.assertEqual(m['independent_verification']['explicit_deleted_fits'],64)
            self.assertEqual(m['coverage']['charter'],{'No':64})
            self.assertGreater(m['diagnostics']['minimum_deleted_sse'],0)
            self.assertGreater(m['diagnostics']['minimum_deleted_residual_scale'],0)
            self.assertTrue(all(v is None or v<audit.VERIFY_TOLERANCE for v in m['independent_verification']['maximum_absolute_errors'].values()))

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

    def test_compact_original_row_field_references_preserve_raw_rate_and_individual_income(self):
        rows={table:{e['source_row']:e['raw'] for e in self.roster['raw_inputs'][table]['records']}
              for table in ['directory','stud','ref','assessment']}
        for model in self.document['models']:
            for r in model['inputs']:
                ref=r['source_refs'];link=self.roster['roster_links'][ref['roster_link_index']]
                directory=rows['directory'][ref['directory_source_row']]
                student=rows['stud'][ref['native_source_rows']['stud']]
                assessment=rows['assessment'][ref['native_source_rows']['assessment']]
                self.assertEqual((directory['LEAID'],directory['ST_LEAID'],directory['NCESSCH']),('4825170','TX-101914',r['school_id']))
                self.assertEqual(directory['ST_SCHID'],'TX-101914-'+r['native_school_id'])
                self.assertEqual((student['DISTRICT'],student['CAMPUS']),('101914',r['native_school_id']))
                self.assertEqual(r['income_pct'],100*int(student['CPNTECOC'])/int(student['CPNTALLC']))
                self.assertEqual(r['income_pct'],link['income']['percentage'])
                self.assertEqual(r['income_enrollment'],int(student['CPNTALLC']))
                self.assertEqual(r['individual_economic_count'],int(student['CPNTECOC']))
                self.assertEqual(ref['outcome_fields'],{'math':'CDA38AM0E225R','reading':'CDA38AR0E225R'})
                for subject in ['math','reading']:
                    self.assertEqual(r['raw_published_rates'][subject],assessment[ref['outcome_fields'][subject]])
                    self.assertEqual(r['outcome_by_subject'][subject],float(assessment[ref['outcome_fields'][subject]]))
                self.assertEqual(ref['native_source_rows'],link['native_source_rows'])
                self.assertEqual(ref['directory']['source_row'],ref['directory_source_row'])
                self.assertEqual(ref['directory']['member'],self.roster['raw_inputs']['directory']['member'])
                for table,pointer in ref['native_tables'].items():
                    section=self.roster['raw_inputs'][table]
                    self.assertEqual((pointer['table'],pointer['source_id'],pointer['source_row']),(table,section['source_id'],ref['native_source_rows'][table]))
                    self.assertEqual((pointer['labels_source_row'],pointer['codes_source_row']),(1,2))
                    self.assertEqual(pointer['labels'],[section['labels'][section['header'].index(f)]for f in pointer['fields']])
                    self.assertEqual(pointer['columns'],[section['header'].index(f)+1 for f in pointer['fields']])
                    self.assertEqual(pointer['member'],section.get('member'))
            excluded=model['coverage']['excluded_configuration_records']
            self.assertEqual({r['native_school_id']for r in excluded},{'101914033'})
            self.assertTrue(all(v['raw_published_rates']['math']in {'-1','-2','-3','*','**','•',''}and v['raw_published_rates']['reading']in {'-1','-2','-3','*','**','•',''}for v in excluded))
        self.assertEqual(self.document['frozen_population']['operational_without_native_school_ids'],['482517008625','482517008629'])
        self.assertFalse(any('raw_inputs' in r or 'directory_raw' in r for m in self.document['models'] for r in m['inputs']))

    def test_combined_owns_its_fit_scale_deletions_and_external_studentization(self):
        math_model,ela,combined=[self.models[s] for s in ['math','reading','combined']]
        self.assertEqual([r['income_pct'] for r in math_model['inputs']],[r['income_pct'] for r in ela['inputs']])
        for field in ['intercept','slope']:
            self.assertAlmostEqual(combined['coefficients'][field],(math_model['coefficients'][field]+ela['coefficients'][field])/2,delta=2e-10)
        for r in combined['inputs']:
            self.assertEqual(r['outcome_pct'],(r['outcome_by_subject']['math']+r['outcome_by_subject']['reading'])/2)
        self.assertTrue(any(abs(c['studentized']-(m['studentized']+e['studentized'])/2)>.01
                            for c,m,e in zip(combined['results'],math_model['results'],ela['results'])))

    def test_income_endpoints_and_influence_cases_remain_in_each_fit_without_clamping(self):
        expected_ids=self.roster['cohorts']['prospective_grade_school']['subjects']['combined']['prospective_nces_school_ids']
        for model in self.document['models']:
            self.assertEqual({r['school_id'] for r in model['results']},set(expected_ids))
            self.assertEqual(model['diagnostics']['top_ten_cooks_distance'][0]['school_id'],'482517010769')
            influential=next(r for r in model['results'] if r['school_id']=='482517010769')
            self.assertGreater(influential['cooks_distance'],4/len(model['inputs']))
            self.assertTrue(influential['review_flags']['cooks_above_4_over_n'])
            x=[r['income_pct'] for r in model['inputs']]
            self.assertEqual(model['diagnostics']['income']['minimum'],min(x))
            self.assertEqual(model['diagnostics']['income']['maximum'],max(x))
            for input_row,row in zip(model['inputs'],model['results']):
                expected=model['coefficients']['intercept']+model['coefficients']['slope']*input_row['income_pct']
                self.assertAlmostEqual(row['predicted'],expected,delta=2e-10)
        # A synthetic bounded-rate sample has an OLS expectation above 100 at
        # its observed endpoint. Independent studentization must retain it.
        x=np.linspace(0,100,40);y=np.clip(110-.8*x+np.sin(x)*2,0,100)
        coefficients,rows=audit.fit_model(x,y,np.zeros(40))
        self.assertGreater(rows[0]['predicted'],100.)
        for row in rows:row.update(low=None,high=None)
        deleted,_=audit.verify_independently(x,y,coefficients,rows)
        self.assertEqual(len(deleted),40)
        self.assertGreater(rows[0]['predicted'],100.)


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
        self.assertTrue(np.array_equal(passed[0], np.zeros(64)))
        self.assertTrue(all(r['low'] is None and r['high'] is None for r in result['results']))

    def test_direct_calls_reject_changed_x_y_original_references_counts_and_membership_before_fit(self):
        m=self.models['math']
        mutations=[lambda x:x.pop(),lambda x:x.reverse(),lambda x:x.append(copy.deepcopy(x[0])),
            lambda x:x[0].update(level='HS'),lambda x:x[0].update(income_year=2024),lambda x:x[0].update(income_year=2025.),
            lambda x:x[0].update(native_school_id='101914004'),lambda x:x[0].update(ncessch='482517099999'),
            lambda x:x[0].update(income_pct=False),lambda x:x[0].update(outcome_pct=float('nan')),
            lambda x:x[0].update(income_pct=x[0]['income_pct']+1e-12),
            lambda x:x[0].update(sampling_variance=0.),lambda x:x[0].update(display_valid_scores=10),
            lambda x:x[0]['valid_scores_by_subject'].update(math=10),lambda x:x[0].update(ten_valid_scored_floor_certified=True),
            lambda x:x[0]['source_refs'].update(directory_source_row=1.),
            lambda x:x[0]['source_refs']['native_source_rows'].update(stud=1),
            lambda x:x[0]['source_refs']['outcome_fields'].update(math='CDA38AM0E225N'),
            lambda x:x[0]['raw_published_rates'].update(math='0'),
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
            lambda d:d['retained_source_reference'].update(complete_original_cell_count=178885.),
            lambda d:d['frozen_population']['eligible_school_ids_by_subject']['math'].append('482517008823'),
            lambda d:d['models'][0]['inputs'][0].update(income_pct=25.),
            lambda d:d['models'][0]['inputs'][0]['source_refs']['native_source_rows'].update(assessment=False),
            lambda d:d['models'][0]['coverage']['excluded_configuration_records'].append({'school_id':'482517008625'}),
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
        for pin in ['SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA']:
            with self.subTest(pin=pin),mock.patch.object(audit,pin,'0'*64),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'load_roster',wraps=audit.load_roster) as source:
            self.assertEqual(audit.validate(self.document,self.expected),{f'katy-2025-ES-{s}':64 for s in audit.SUBJECTS})
            self.assertGreater(source.call_count,0)

    def test_cached_and_direct_replay_bind_current_policy_runtime_and_public_pin_literals(self):
        policy=copy.deepcopy(audit.POLICY);policy['models']='Drop influential campuses and infer causal school quality'
        wrong_subjects=['math','combined']
        changed=[('POLICY',policy),('MIN_SCHOOLS',29),('MIN_SCHOOLS',30.),('SUBJECTS',wrong_subjects),
            ('ASSESSMENT','Other assessment'),('STANDARD','Foreign population'),('ABS_TOLERANCE',1.),
            ('ROSTER_SHA','0'*64),('SOURCE_RAW_SHA','0'*64),('SOURCE_RUNTIME_SHA','0'*64)]
        for key,bad in changed:
            with self.subTest(key=key),mock.patch.object(audit,key,bad),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
            with self.subTest(direct=key),mock.patch.object(audit,key,bad),self.assertRaises(ValueError):
                audit.load_roster()
        with mock.patch.object(audit,'POLICY',policy):
            resigned=audit.roster_audit.fingerprint(policy)
            with mock.patch.object(audit,'NUMERIC_POLICY_SHA',resigned),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'MIN_SCHOOLS',30.):
            resigned=audit.roster_audit.fingerprint(audit.runtime_contract())
            with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',resigned),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
        for key in ['RAW_INPUT_SHA','ORIGINAL_SCHEMA_SHA','DEFINITION_INPUT_SHA','ORIGINAL_IDENTITY_SHA','RUNTIME_CONTRACT_SHA','STATE_EXTRACT_SHA']:
            with self.subTest(source_pin=key),mock.patch.object(audit.roster_audit,key,'0'*64),self.assertRaises(ValueError):
                audit.validate(self.document,self.expected)
        bad_source=copy.deepcopy(audit.roster_audit.POLICY);bad_source['assessment']='Other year or subject'
        with mock.patch.object(audit.roster_audit,'POLICY',bad_source),self.assertRaises(ValueError):
            audit.validate(self.document,self.expected)

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
        with mock.patch.object(audit, 'SOURCE_TESTS_SHA', '0' * 64), self.assertRaises(ValueError):
            audit.load_roster()
        with mock.patch.object(audit, 'SOURCE_POLICY_SHA', '0' * 64), self.assertRaises(ValueError):
            audit.load_roster()
        changed = copy.deepcopy(self.roster); changed['roster_links'][0]['income']['percentage'] = -1.
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
            with mock.patch.object(audit.roster_audit.zipfile, 'ZipFile', side_effect=AssertionError('No original archive')), \
                    mock.patch.object(audit.roster_audit.subprocess, 'Popen', side_effect=AssertionError('No original stream')), \
                    mock.patch.object(audit.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original extraction')):
                self.assertEqual(audit.prepare(a, check=True), first)
            self.assertEqual(before, a.read_bytes())

    def test_supplied_expected_builder_mutation_and_coherent_public_cache_are_not_authority(self):
        changed=copy.deepcopy(self.expected);changed['models'][0]['results'][0]['predicted']+=.1
        with self.assertRaises(ValueError):audit.validate(changed,changed)
        with self.assertRaises(ValueError):audit.validate(self.document,changed)
        for cache,digest in [('_VERIFIED_EXPECTATION_CACHE','_VERIFIED_EXPECTATION_CACHE_SHA'),('EXPECTED_JSON','EXPECTED_SHA')]:
            with self.subTest(cache=cache),mock.patch.object(audit,cache,json.dumps(changed),create=True),mock.patch.object(audit,digest,audit.roster_audit.fingerprint(changed),create=True),self.assertRaises(ValueError):audit.validate(changed,changed)
        self.assertEqual(audit.build(),self.document)
        with mock.patch.object(audit,'load_roster',wraps=audit.load_roster)as loader:
            self.assertEqual(audit.validate(self.document,self.expected),{f'katy-2025-ES-{s}':64 for s in audit.SUBJECTS})
            self.assertEqual(loader.call_count,1)

    def test_cached_expected_checks_current_complete_original_and_secondary_sources(self):
        target=ROOT/audit.roster_audit.SOURCES['ref']['path'];data=target.read_bytes();changed=bytes([data[0]^1])+data[1:];original_open=Path.open
        def changed_original(path,*args,**kwargs):return io.BytesIO(changed)if path==target and args and args[0]=='rb'else original_open(path,*args,**kwargs)
        with mock.patch.object(Path,'open',changed_original),self.assertRaisesRegex(ValueError,'current original fingerprint'):audit.validate(self.document,self.expected)
        original_read=Path.read_bytes;secondary=ROOT/'data/source/texas.json'
        def changed_secondary(path):return b'changed'if path==secondary else original_read(path)
        with mock.patch.object(Path,'read_bytes',changed_secondary),self.assertRaises(ValueError):audit.validate(self.document,self.expected)

    def test_selector_published_masks_counts_and_exact_harris_exclusion(self):
        self.assertEqual(self.document['frozen_population']['operational_without_native_school_ids'],['482517008625','482517008629'])
        self.assertEqual(len(self.document['frozen_population']['complete_directory_without_native_school_ids']),4)
        for subject in audit.SUBJECTS:
            inputs,coverage=audit.selected_inputs(self.roster,subject)
            self.assertEqual(len(inputs),64);self.assertEqual(len(coverage['excluded_configuration_records']),1)
            self.assertTrue(all(r['ccd_school_type']=='Regular School'and r['charter']=='No'for r in inputs))
        changed=copy.deepcopy(self.roster)
        for entry in changed['raw_inputs']['assessment']['records']:
            for fields in audit.roster_audit.FIELDS.values():entry['raw'][fields[0]]=entry['raw'][fields[1]]='-1'
        with mock.patch.object(audit,'require_frozen_roster'):
            inputs,coverage=audit.selected_inputs(changed,'combined')
        self.assertEqual(inputs,self.models['combined']['inputs']);self.assertEqual(coverage,self.models['combined']['coverage'])
        first=self.models['math']['inputs'][0]['native_school_id'];changed=copy.deepcopy(self.roster)
        raw=next(r['raw']for r in changed['raw_inputs']['stud']['records']if r['raw']['CAMPUS']==first);raw['CPNTG09C']='-1'
        with mock.patch.object(audit,'require_frozen_roster'),self.assertRaises(ValueError):audit.selected_inputs(changed,'math')


if __name__ == '__main__':
    unittest.main()

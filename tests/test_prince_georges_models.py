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
import audit_prince_georges_models as audit


class PrinceGeorgesNumericalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=audit.load_roster()
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.expected=audit.build(cls.roster)
        cls.models={m['subject']:m for m in cls.document['models']}

    def test_compact_source_pins_full_directory_and_unequal_membership(self):
        expected={f'prince-georges-2025-ES-{s}':n for s,n in [('math',146),('reading',159),('combined',146)]}
        self.assertEqual(audit.validate(self.document,self.expected),expected)
        self.assertEqual((self.document['scope'],self.document['status']),('numerical_audit_only','numerically_verified_pending_integration'))
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        self.assertEqual(self.document['hard_holds'],[])
        p=self.document['frozen_population']
        for key,count in [('complete_native_school_ids',204),('complete_directory_ncessch',201),('operational_directory_ncessch',199),
            ('grade_school_configuration_ids',159),('high_school_configuration_ids',24),('mixed_configuration_ids',5),
            ('primary_configuration_ids',2),('unknown_configuration_ids',8),('nonoperational_directory_ncessch',2),
            ('unmatched_native_school_ids',6),('unmatched_directory_ncessch',3)]:
            self.assertEqual(len(p[key]),count)
        self.assertEqual(len(self.document['retained_scope_exclusions']),45)
        self.assertIn('16-0218',p['unmatched_native_school_ids'])
        held=next(r for r in self.document['retained_scope_exclusions']if r['school_id']=='16-0218')
        self.assertIsNone(held['ncessch']);self.assertIsNone(held['native_school_id']);self.assertIn('malformed',held['identity_hold'])
        reference=self.document['retained_source_reference']
        self.assertEqual(reference['complete_original_record_count'],5404);self.assertEqual(reference['complete_original_cell_count'],89640)
        self.assertEqual(reference['sha256'],audit.ROSTER_SHA)
        self.assertNotIn('raw_inputs',self.document);self.assertNotIn('retained_source_evidence',self.document)
        self.assertNotIn('source_definition_evidence',self.document)
        for m in self.document['models']:
            n=159 if m['subject']=='reading'else 146
            self.assertEqual(m['coefficients']['n'],n);self.assertEqual(m['coverage']['grade_school_configuration_profiles'],159)
            self.assertEqual(m['coverage']['excluded_configuration_profiles'],159-n)
            self.assertEqual(m['diagnostics']['income_design_rank'],2)
            self.assertEqual(m['diagnostics']['full_residual_degrees_of_freedom'],n-2)
            self.assertEqual(m['diagnostics']['deleted_residual_degrees_of_freedom'],n-3)
            self.assertEqual(m['independent_verification']['explicit_deleted_fits'],n)
            self.assertEqual(m['coverage']['charter'],{'No':n-6,'Yes':6})
            self.assertGreater(m['diagnostics']['minimum_deleted_sse'],0)
            self.assertGreater(m['diagnostics']['minimum_deleted_residual_scale'],0)
            self.assertTrue(all(v is None or v<audit.VERIFY_TOLERANCE for v in m['independent_verification']['maximum_absolute_errors'].values()))

    def test_original_member_worksheet_row_field_references_and_precise_individual_income(self):
        tables=self.roster['raw_inputs']
        native={e['source_row']:e for e in tables['native_directory']['records']}
        ccd={e['source_row']:e['raw']for e in tables['directory']['records']}
        income={e['source_row']:e['raw']for e in tables['native_income']['records']}
        grades={e['source_row']:e['raw']for e in tables['native_enrollment']['records']}
        outcomes={(e['member'],e['worksheet'],e['source_row']):e['raw']for e in tables['native_assessment']['records']}
        for model in self.document['models']:
            for r in model['inputs']:
                refs=r['source_refs'];link=self.roster['roster_links'][refs['roster_link_index']]
                original=native[refs['native_directory']['source_row']]
                self.assertEqual((refs['native_directory']['member'],refs['native_directory']['worksheet']),(original['member'],original['worksheet']))
                self.assertEqual(r['ncessch'],str(original['raw']['NCES Number']))
                directory=ccd[refs['directory_source_row']]
                self.assertEqual((directory['LEAID'],directory['ST_LEAID'],directory['NCESSCH'],directory['ST_SCHID']),('2400510','MD-16',r['ncessch'],r['native_school_id']))
                self.assertEqual(r['school_id'],'16-'+original['raw']['School'])
                ed=income[refs['income']['selected_source_row']]
                self.assertEqual(refs['income']['source_rows'],link['income']['source_rows'])
                self.assertEqual(refs['income']['fields'],['Total Student Cnt','Economically Disadvantaged Cnt','Economically Disadvantaged Pct'])
                self.assertEqual(r['income_pct'],100*int(ed['Economically Disadvantaged Cnt'])/int(ed['Total Student Cnt']))
                self.assertEqual((r['income_enrollment'],r['individual_economic_count']),(int(ed['Total Student Cnt']),int(ed['Economically Disadvantaged Cnt'])))
                self.assertEqual(refs['income']['selected_school_type'],ed['School Type'])
                if len(refs['income']['source_rows'])>1:self.assertEqual(ed['School Type'],'All')
                self.assertEqual(refs['native_enrollment']['source_rows'],link['native_enrollment_rows'])
                selected=[grades[i]for i in refs['native_enrollment']['source_rows']]
                self.assertFalse(any(e['Grade']in[f'Grade {g}'for g in range(9,13)]for e in selected))
                self.assertTrue(any(e['Grade']in[f'Grade {g}'for g in range(3,9)]and audit.original_number(e['Enrolled Count'],count=True)not in{None,0}for e in selected))
                for subject in ['math','reading']:
                    ref=refs['outcomes'][subject];raw=outcomes[(ref['member'],ref['worksheet'],ref['source_row'])]
                    self.assertEqual((raw['Year'],raw['LEA'],raw['School'],raw['Student Group'],raw['Assessment'].strip()),(2025,'16',r['school_id'][3:],'All Students',audit.SUBJECT_LABELS[subject]))
                    self.assertEqual(ref['assessment'],raw['Assessment']);self.assertEqual(ref['member'],audit.SUBJECT_MEMBERS[subject])
                    self.assertEqual(r['raw_published_rates'][subject],raw['Proficient Pct'])
                    self.assertEqual(r['outcome_by_subject'][subject],audit.original_number(raw['Proficient Pct']))
                    self.assertIn('Proficient Pct',ref['fields']);self.assertNotIn('Level 3 Pct',ref['fields'])
        excluded=self.models['math']['coverage']['excluded_configuration_records']
        self.assertEqual(len(excluded),13)
        self.assertEqual({r['school_id']for r in excluded},set(self.document['frozen_population']['eligible_school_ids_by_subject']['reading'])-set(self.document['frozen_population']['eligible_school_ids_by_subject']['math']))
        self.assertTrue(all(r['raw_published_rates']['math'].strip()=='<= 5.0'for r in excluded))
        self.assertEqual(self.models['reading']['coverage']['excluded_configuration_records'],[])

    def test_combined_owns_the_paired_fit_and_never_averages_unequal_subject_models(self):
        m,e,c=[self.models[s]for s in ['math','reading','combined']]
        self.assertEqual([r['school_id']for r in m['inputs']],[r['school_id']for r in c['inputs']])
        self.assertEqual((len(m['inputs']),len(e['inputs']),len(c['inputs'])),(146,159,146))
        self.assertGreater(abs(c['coefficients']['intercept']-(m['coefficients']['intercept']+e['coefficients']['intercept'])/2),.005)
        self.assertGreater(abs(c['coefficients']['slope']-(m['coefficients']['slope']+e['coefficients']['slope'])/2),.001)
        for r in c['inputs']:self.assertEqual(r['outcome_pct'],(r['outcome_by_subject']['math']+r['outcome_by_subject']['reading'])/2)
        ela={r['school_id']:r for r in e['results']}
        self.assertTrue(any(abs(cr['studentized']-(mr['studentized']+ela[cr['school_id']]['studentized'])/2)>.01 for cr,mr in zip(c['results'],m['results'])))
        d=copy.deepcopy(self.document);d['models'][2]['coefficients']['slope']=(m['coefficients']['slope']+e['coefficients']['slope'])/2
        with self.assertRaises(ValueError):audit.validate(d,self.expected)

    def test_influence_and_every_eligible_charter_remain_in_each_complete_fixed_model(self):
        for m in self.document['models']:
            self.assertEqual(sum(r['charter']=='Yes'for r in m['inputs']),6)
            self.assertEqual(m['diagnostics']['predictions_outside_percentage_range'],0)
            self.assertTrue(all(r['school_id']in self.document['frozen_population']['eligible_school_ids_by_subject'][m['subject']]for r in m['results']))
        math=next(r for r in self.models['math']['results']if r['school_id']=='16-2010')
        combined=next(r for r in self.models['combined']['results']if r['school_id']=='16-2010')
        ela=next(r for r in self.models['reading']['results']if r['school_id']=='16-0917')
        self.assertGreater(math['studentized'],7.);self.assertGreater(combined['studentized'],5.9)
        self.assertGreater(ela['cooks_distance'],.48)
        self.assertTrue(math['review_flags']['absolute_external_t_above_2']);self.assertTrue(ela['review_flags']['cooks_above_4_over_n'])
        d=copy.deepcopy(self.document);d['models'][0]['results']=[r for r in d['models'][0]['results']if r['school_id']!='16-2010']
        with self.assertRaises(ValueError):audit.validate(d,self.expected)

    def test_independent_original_selector_rejects_high_zero_grade_presence_and_wrong_definition(self):
        def select_changed(changed):
            with mock.patch.object(audit,'require_frozen_roster'):
                audit.selected_inputs(changed,'math')
        for mutation in ['highzero','gradeunknown','onlyzero','allincome','ratecount','duplicateall']:
            r=copy.deepcopy(self.roster);key='0104'
            if mutation in ['highzero','gradeunknown','onlyzero']:
                grades=[e for e in r['raw_inputs']['native_enrollment']['records']if e['raw']['School']==key]
                if mutation=='highzero':grades[0]['raw'].update(Grade='Grade 9',**{'Enrolled Count':'0'})
                elif mutation=='gradeunknown':grades[0]['raw']['Grade']='Unknown Grade'
                else:
                    for e in grades:
                        if e['raw']['Grade']in[f'Grade {g}'for g in range(3,9)]:e['raw']['Enrolled Count']='0'
            elif mutation=='allincome':
                e=next(e for e in r['raw_inputs']['native_income']['records']if e['raw']['School Number']==key and e['raw']['School Type']=='All');e['raw']['School Type']='Elementary'
            elif mutation=='ratecount':
                e=next(e for e in r['raw_inputs']['native_assessment']['records']if e['raw']['School']==key and e['raw']['Assessment'].strip()=='Mathematics All Grades');e['raw']['Proficient Pct']=e['raw']['Tested Count']
            else:
                e=next(e for e in r['raw_inputs']['native_assessment']['records']if e['raw']['School']==key and e['raw']['Assessment'].strip()=='Mathematics All Grades');r['raw_inputs']['native_assessment']['records'].append(copy.deepcopy(e))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):select_changed(r)
        # Administrative tests do not define eligibility or manufacture a scored floor.
        r=copy.deepcopy(self.roster)
        for e in r['raw_inputs']['native_assessment']['records']:e['raw']['Tested Count']='*';e['raw']['Proficient Count']='*'
        with mock.patch.object(audit,'require_frozen_roster'):
            values,coverage=audit.selected_inputs(r,'math')
        self.assertEqual([x['school_id']for x in values],[x['school_id']for x in self.models['math']['inputs']])
        self.assertEqual(coverage['usable_schools'],146);self.assertTrue(all(x['display_valid_scores']is None for x in values))

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
            lambda x:x[0].update(native_school_id='MD-16-160218'),lambda x:x[0].update(ncessch='240051099999'),
            lambda x:x[0].update(income_pct=False),lambda x:x[0].update(outcome_pct=float('nan')),
            lambda x:x[0].update(income_pct=x[0]['income_pct']+1e-12),
            lambda x:x[0].update(sampling_variance=0.),lambda x:x[0].update(display_valid_scores=10),
            lambda x:x[0]['valid_scores_by_subject'].update(math=10),lambda x:x[0].update(ten_valid_scored_floor_certified=True),
            lambda x:x[0]['source_refs'].update(directory_source_row=1.),
            lambda x:x[0]['source_refs']['native_enrollment'].update(source_rows=[1]),
            lambda x:x[0]['source_refs']['outcomes']['math'].update(member='2025 MCAP ELA Administrative Data Report Card.xlsx'),
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
            lambda d:d['retained_source_reference'].update(complete_original_cell_count=89640.),
            lambda d:d['frozen_population']['eligible_school_ids_by_subject']['math'].append('16-0218'),
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
            self.assertEqual(audit.validate(self.document,self.expected),{f'prince-georges-2025-ES-{s}':n for s,n in [('math',146),('reading',159),('combined',146)]})
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
            with mock.patch.object(audit.roster_audit.zipfile, 'ZipFile', side_effect=AssertionError('No original archive')), \
                    mock.patch.object(audit.roster_audit.subprocess, 'Popen', side_effect=AssertionError('No original stream')), \
                    mock.patch.object(audit.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original extraction')):
                self.assertEqual(audit.prepare(a, check=True), first)
            self.assertEqual(before, a.read_bytes())


if __name__ == '__main__':
    unittest.main()

import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest import mock

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_philadelphia_models as audit


class PhiladelphiaNumericalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=audit.load_roster()
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.expected=audit.build(cls.roster)
        cls.models={m['subject']:m for m in cls.document['models']}

    def test_compact_source_only_pins_complete_cohort_and_all_deleted_scales(self):
        self.assertEqual(audit.validate(self.document,self.expected),{f'philadelphia-2025-ES-{s}':162 for s in audit.SUBJECTS})
        self.assertEqual(self.document['hard_holds'],[])
        self.assertFalse(self.document['approved_for_source']);self.assertFalse(self.document['approved_for_modeling'])
        self.assertEqual(self.document['scope'],'numerical_audit_only')
        self.assertEqual(self.document['status'],'numerically_verified_pending_integration')
        population=self.document['frozen_population']
        for key,n in [('complete_native_school_ids',221),('complete_directory_ncessch',221),('operational_directory_ncessch',220),
                ('grade_school_configuration_ids',162),('high_school_configuration_ids',47),('mixed_configuration_ids',10),
                ('primary_configuration_ids',1),('nonoperational_directory_ncessch',1),('unmatched_native_school_ids',1),('directory_without_native_profile_ids',1)]:
            self.assertEqual(len(population[key]),n)
        self.assertEqual(population['unmatched_native_school_ids'],['126515001-000009999'])
        self.assertEqual(population['directory_without_native_profile_ids'],['126515001-000006768'])
        self.assertEqual(len(self.document['retained_scope_exclusions']),59)
        self.assertEqual(self.document['retained_source_reference']['complete_original_record_count'],22108)
        self.assertEqual(self.document['retained_source_reference']['complete_original_cell_count'],622260)
        self.assertNotIn('raw_inputs',self.document)
        for model in self.document['models']:
            self.assertEqual(model['coefficients']['n'],162)
            self.assertEqual(model['coverage']['charter'],{'No':162})
            self.assertEqual((model['diagnostics']['full_residual_degrees_of_freedom'],model['diagnostics']['deleted_residual_degrees_of_freedom']),(160,159))
            self.assertEqual(model['independent_verification']['explicit_deleted_fits'],162)
            self.assertGreater(model['diagnostics']['minimum_deleted_sse'],0)
            self.assertGreater(model['diagnostics']['minimum_deleted_residual_scale'],0)
            self.assertTrue(all(v<audit.VERIFY_TOLERANCE for v in model['independent_verification']['maximum_absolute_errors'].values()))

    def test_original_row_field_references_exact_id_crosswalks_income_rates_and_denominators(self):
        raw=self.roster['raw_inputs']
        index={table:{e['source_row']:e['raw'] for e in raw[table]['records']} for table in audit.roster_audit.TABLES}
        for model in self.document['models']:
            for row in model['inputs']:
                refs=row['source_refs'];directory=index['directory'][refs['directory']['source_row']]
                self.assertEqual((directory['LEAID'],directory['ST_LEAID'],directory['NCESSCH'],directory['ST_SCHID']),('4218990','PA-126515001',row['ncessch'],row['native_school_id']))
                for ref in [refs['native_enrollment'],refs['income']]+list(refs['outcomes'].values()):
                    section=raw[ref['table']]
                    self.assertEqual((ref['source_id'],ref['worksheet']),(section['source_id'],section['worksheet']))
                    self.assertEqual(ref['fields'],[section['header_rows'][-1][i] for i in ref['columns']])
                    cells=index[ref['table']][ref['source_row']]
                    self.assertEqual(audit.roster_audit.native_identity(cells,ref['table']),row['school_id'])
                income=index['native_income'][refs['income']['source_row']]
                self.assertEqual((row['income_enrollment'],row['individual_economic_count'],row['published_income_proportion']),(income[5],income[6],income[7]))
                self.assertEqual(row['income_pct'],100*income[6]/income[5])
                enrolled=index['native_grades'][refs['native_enrollment']['source_row']]
                self.assertEqual(enrolled[23:27],[0]*4);self.assertTrue(any(v>0 for v in enrolled[17:23]))
                for subject,ref in refs['outcomes'].items():
                    cells=index['native_assessment'][ref['source_row']]
                    self.assertEqual((cells[0],cells[6],cells[7],cells[8]),(2025,audit.SUBJECT_LABELS[subject],'All Students','Total'))
                    self.assertEqual(row['raw_published_rates'][subject],cells[14])
                    self.assertIs(type(row['raw_published_rates'][subject]),type(cells[14]))
                    self.assertEqual(row['valid_scores_by_subject'][subject],cells[9])
                    self.assertGreaterEqual(cells[9],11)
        jenks=next(r for r in self.models['combined']['inputs'] if r['school_id']=='126515001-000007227')
        self.assertEqual(jenks['ncessch'],'421899003644')
        self.assertEqual(jenks['native_school_id'],'PA-126515001-7227')

    def test_jeffreys_variance_strict_counts_masks_and_boundary_smoothing(self):
        for pct,n in [(0,11),(100,11),(77.6,42),(12.3,1315)]:
            p=(pct/100*n+.5)/(n+1)
            self.assertEqual(audit.verified_sampling_variance(pct,n),10000*p*(1-p)/n)
            self.assertGreater(audit.verified_sampling_variance(pct,n),0)
        for pct,n in [(50,True),(50,42.),(50,10),(50,None),(50,-1),(False,42),(101,42),(float('nan'),42),(float('inf'),42)]:
            with self.subTest(pct=pct,n=n),self.assertRaises(ValueError):audit.verified_sampling_variance(pct,n)
        for model in self.document['models']:
            for row in model['inputs']:
                for s in ['math','reading']:
                    n=row['valid_scores_by_subject'][s];pct=row['outcome_by_subject'][s];p=(n*pct/100+.5)/(n+1)
                    self.assertAlmostEqual(row['variance_by_subject'][s],10000*p*(1-p)/n,delta=1e-12)

    def test_combined_is_own_fit_maximum_covariance_variance_and_smaller_count_display(self):
        math_model,ela,combined=[self.models[s] for s in audit.SUBJECTS]
        for key in ['intercept','slope']:
            self.assertAlmostEqual(combined['coefficients'][key],(math_model['coefficients'][key]+ela['coefficients'][key])/2,delta=2e-10)
        for row in combined['inputs']:
            self.assertEqual(row['outcome_pct'],sum(row['outcome_by_subject'].values())/2)
            v=row['variance_by_subject']
            self.assertEqual(row['sampling_variance'],(math.sqrt(v['math'])+math.sqrt(v['reading']))**2/4)
            self.assertGreater(row['sampling_variance'],(v['math']+v['reading'])/4)
            self.assertEqual(row['display_valid_scores'],min(row['valid_scores_by_subject'].values()))
        self.assertTrue(any(abs(c['studentized']-(m['studentized']+e['studentized'])/2)>.01 for c,m,e in zip(combined['results'],math_model['results'],ela['results'])))
        self.assertNotEqual(combined['diagnostics']['residual_standard_error'],(math_model['diagnostics']['residual_standard_error']+ela['diagnostics']['residual_standard_error'])/2)
        self.assertIn('not a paired',combined['intervals']['combined_count_display'])

    def test_raw_unweighted_full_and_all_486_deleted_fits_interval_and_influence_metrics(self):
        for model in self.document['models']:
            x=np.array([r['income_pct'] for r in model['inputs']]);y=np.array([r['outcome_pct'] for r in model['inputs']]);v=np.array([r['sampling_variance'] for r in model['inputs']]);n=len(x)
            X=np.column_stack([np.ones(n),x]);beta=np.linalg.lstsq(X,y,rcond=None)[0]
            predicted=X@beta;residual=y-predicted;sse=float(residual@residual);H=X@np.linalg.inv(X.T@X)@X.T
            propagated=((np.eye(n)-H)**2)@v
            self.assertAlmostEqual(model['coefficients']['intercept'],float(beta[0]),delta=2e-10)
            self.assertAlmostEqual(model['coefficients']['slope'],float(beta[1]),delta=2e-10)
            for i,row in enumerate(model['results']):
                keep=np.arange(n)!=i;D=X[keep];b=np.linalg.lstsq(D,y[keep],rcond=None)[0]
                deleted_residual=y[keep]-D@b;deleted_sse=float(deleted_residual@deleted_residual)
                scale=math.sqrt(deleted_sse/(n-3));held=float(X[i]@b);h_deleted=float(X[i]@np.linalg.inv(D.T@D)@X[i])
                t=(y[i]-held)/(scale*math.sqrt(1+h_deleted));se=math.sqrt(propagated[i])/(scale*math.sqrt(1-H[i,i]))
                cook=residual[i]**2*H[i,i]/(2*(sse/(n-2))*(1-H[i,i])**2)
                endpoint=np.column_stack([np.ones(2),[x.min(),x.max()]]);shift=float(np.max(np.abs(endpoint@beta-endpoint@b)))
                with self.subTest(subject=model['subject'],school=row['school_id']):
                    for field,value in [('predicted',predicted[i]),('residual',residual[i]),('leverage',H[i,i]),('studentized',t),
                        ('low',t-1.96*se),('high',t+1.96*se),('deleted_intercept',b[0]),('deleted_slope',b[1]),
                        ('deleted_sse',deleted_sse),('deleted_residual_scale',scale),('deleted_held_out_prediction',held),
                        ('deleted_held_out_prediction_leverage',h_deleted),('propagated_sampling_variance',propagated[i]),
                        ('studentized_sampling_standard_error',se),('cooks_distance',cook),('maximum_prediction_change_on_observed_income_range',shift)]:
                        self.assertAlmostEqual(row[field],float(value),delta=2e-9)

    def test_every_model_member_contributes_uncertainty_with_fixed_scale_and_unchanged_point_fit(self):
        model=self.models['math'];x=np.array([r['income_pct'] for r in model['inputs']]);y=np.array([r['outcome_pct'] for r in model['inputs']]);v=np.array([r['sampling_variance'] for r in model['inputs']])
        coefficients,ordinary=audit.fit_model(x-x.mean(),y,v)
        _,quadrupled=audit.fit_model(x-x.mean(),y,4*v)
        distant=v.copy();distant[-1]*=100;_,modified=audit.fit_model(x-x.mean(),y,distant)
        self.assertNotEqual(ordinary[0]['high']-ordinary[0]['low'],modified[0]['high']-modified[0]['low'])
        for row,larger in zip(ordinary,quadrupled):
            self.assertEqual(row['studentized'],larger['studentized'])
            self.assertAlmostEqual(larger['high']-larger['low'],2*(row['high']-row['low']),delta=2e-12)
        for result in model['results']:
            self.assertLess(result['low'],result['studentized']);self.assertLess(result['studentized'],result['high'])
            self.assertIs(type(result['valid_scores']),int)
        self.assertTrue(model['intervals']['available_for_entire_model'])
        self.assertEqual(model['intervals']['eligible_members_with_verified_denominators'],162)

    def test_influential_crosswalk_and_unbounded_predictions_are_retained(self):
        ela=self.models['reading'];rows={r['school_id']:r for r in ela['results']}
        self.assertGreater(rows['126515001-000003649']['predicted'],100)
        self.assertGreater(rows['126515001-000005186']['predicted'],100)
        self.assertGreater(rows['126515001-000005186']['cooks_distance'],.24)
        combined={r['school_id']:r for r in self.models['combined']['results']}
        self.assertGreater(combined['126515001-000007227']['studentized'],4.4)
        self.assertEqual(combined['126515001-000007227']['valid_scores'],112)
        for model in self.document['models']:
            self.assertFalse(model['approved_for_source']);self.assertFalse(model['approved_for_modeling'])
            self.assertEqual(len(model['results']),162)
            self.assertNotIn('126515001-000009999',{r['school_id'] for r in model['inputs']})
            self.assertNotIn('126515001-000006768',{r['school_id'] for r in model['inputs']})

    def test_direct_fits_fail_closed_before_computation_for_count_variance_identity_and_membership_drift(self):
        model=self.models['combined']
        mutations=[lambda rows:rows.pop(),lambda rows:rows.reverse(),lambda rows:rows[0].update(income_year=2025.),
            lambda rows:rows[0].update(income_pct=rows[0]['income_pct']+1e-12),lambda rows:rows[0].update(outcome_pct=False),
            lambda rows:rows[0]['valid_scores_by_subject'].update(math=None),lambda rows:rows[0]['valid_scores_by_subject'].update(math=42.),
            lambda rows:rows[0].update(display_valid_scores=rows[0]['income_enrollment']),lambda rows:rows[0].update(sampling_variance=0.),
            lambda rows:rows[0].update(sampling_variance=sum(rows[0]['variance_by_subject'].values())/4),
            lambda rows:rows[0].update(ncessch='421899099999'),lambda rows:rows[0]['source_refs']['outcomes']['math'].update(source_row=1.)]
        for i,mutate in enumerate(mutations):
            rows=copy.deepcopy(model['inputs']);mutate(rows)
            with self.subTest(i=i),mock.patch.object(audit,'fit_model',side_effect=AssertionError('No fit before evidence validation')),self.assertRaises(ValueError):
                audit.fit_audited_model(rows,model['coverage'],'combined')
        with mock.patch.object(audit,'fit_model',side_effect=AssertionError('No subfloor fit')),self.assertRaisesRegex(ValueError,'at least 30'):
            audit.fit_audited_model(model['inputs'][:29],model['coverage'],'combined')

    def test_independent_raw_selector_rejects_grade_income_and_pssa_population_count_drift(self):
        key=self.models['math']['inputs'][0]['school_id']
        for mutation in ['highgrade','notestedgrade','income','population','count']:
            roster=copy.deepcopy(self.roster);raw=roster['raw_inputs']
            if mutation in ['highgrade','notestedgrade']:
                r=next(e['raw'] for e in raw['native_grades']['records'] if audit.roster_audit.native_identity(e['raw'],'native_grades')==key)
                if mutation=='highgrade':r[23]=1
                else:r[17:23]=[0]*6
            elif mutation=='income':
                r=next(e['raw'] for e in raw['native_income']['records'] if audit.roster_audit.native_identity(e['raw'],'native_income')==key);r[7]=None
            else:
                r=next(e['raw'] for e in raw['native_assessment']['records'] if audit.roster_audit.native_identity(e['raw'],'native_assessment')==key and e['raw'][6:9]==['Math','All Students','Total'])
                if mutation=='population':r[8]=3
                else:r[9]=10
            with self.subTest(mutation=mutation),mock.patch.object(audit,'require_frozen_roster'),self.assertRaises(ValueError):audit.selected_inputs(roster,'math')

    def test_cached_and_direct_replay_require_current_literal_policy_types_and_public_pins(self):
        policy=copy.deepcopy(audit.POLICY);policy['intervals']='Use only the selected school variance and independent Combined covariance'
        mutations=[('POLICY',policy),('MIN_SCHOOLS',30.),('MIN_VALID_SCORES',False),('INTERVAL_MULTIPLIER',2.),
            ('SUBJECTS',['math','combined']),('SUBJECT_FIELDS',{'math':10,'reading':14}),('COUNT_FIELD',27),('ROSTER_SHA','0'*64),
            ('ASSESSMENT','Different standard'),('INCOME_FIELDS',[5,6,8])]
        for field,value in mutations:
            with self.subTest(field=field),mock.patch.object(audit,field,value):
                with self.assertRaises(ValueError):audit.validate(self.document,self.expected)
                with self.assertRaises(ValueError):audit.selected_inputs(self.roster,'math')
        with mock.patch.object(audit,'POLICY',policy),mock.patch.object(audit,'NUMERIC_POLICY_SHA',audit.roster_audit.fingerprint(policy)),self.assertRaises(ValueError):audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'MIN_SCHOOLS',30.):
            repin=audit.roster_audit.fingerprint(audit.runtime_contract())
            with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',repin),self.assertRaises(ValueError):audit.validate(self.document,self.expected)

    def test_cached_replay_requires_complete_current_blob_code_tests_policy_and_secondary_source(self):
        original=Path.read_bytes
        targets=[audit.ROSTER,audit.SOURCE_CODE,audit.SOURCE_TESTS,ROOT/'data/source/pennsylvania.json']
        for target in targets:
            def altered(path):return b'changed' if path==target else original(path)
            with self.subTest(target=target),mock.patch.object(Path,'read_bytes',altered),self.assertRaises(ValueError):audit.validate(self.document,self.expected)
        def absent(path):
            if path==audit.ROSTER:raise FileNotFoundError('Missing immutable complete source')
            return original(path)
        with mock.patch.object(Path,'read_bytes',absent),self.assertRaises(FileNotFoundError):audit.validate(self.document,self.expected)
        changed=copy.deepcopy(audit.roster_audit.POLICY);changed['counts']='Enrollment is scored'
        with mock.patch.object(audit.roster_audit,'POLICY',changed),self.assertRaises(ValueError):audit.validate(self.document,self.expected)

    def test_rank_finite_variance_and_positive_full_deleted_scale_are_hard_gates(self):
        model=self.models['math'];x=np.array([r['income_pct'] for r in model['inputs']]);y=np.array([r['outcome_pct'] for r in model['inputs']]);v=np.array([r['sampling_variance'] for r in model['inputs']])
        for badx,bady in [(np.full(len(x),20.),y),(x,10+.5*x),(np.r_[30.,np.full(len(x)-1,20.)],y)]:
            with self.assertRaises(ValueError):audit.fit_model(badx,bady,v)
        outlier=10+.5*x;outlier[0]+=1
        with self.assertRaises(ValueError):audit.fit_model(x,outlier,v)
        for variance in [np.zeros(len(x)),np.full(len(x),float('nan')),np.ones(len(x)-1)]:
            with self.assertRaises(ValueError):audit.verify_independently(x,y,variance,model['coefficients'],model['results'])

    def test_saved_numerical_counts_intervals_metadata_and_nonfinite_corruptions_reject(self):
        changes=[lambda d:d.update(approved_for_modeling=True),lambda d:d['models'][0]['inputs'][0].update(display_valid_scores=42.),
            lambda d:d['models'][0]['results'][0].update(low=None),lambda d:d['models'][0]['results'][0].update(high=float('inf')),
            lambda d:d['models'][0]['results'][0].update(studentized=False),lambda d:d['models'][0]['results'][0].update(studentized=100.),
            lambda d:d['models'][0]['results'][0].update(propagated_sampling_variance=0.),lambda d:d['models'][2]['intervals'].update(available_for_entire_model=False),
            lambda d:d['models'][2]['inputs'][0]['source_refs']['outcomes']['reading'].update(worksheet='Keystone')]
        for i,change in enumerate(changes):
            document=copy.deepcopy(self.document);change(document)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(document,self.expected)


if __name__=='__main__':unittest.main()

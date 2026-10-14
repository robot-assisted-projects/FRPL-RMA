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
import audit_san_diego_models as audit


class SanDiegoNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=audit.load_roster()
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.models={m['subject']:m for m in cls.document['models']}

    def test_complete_original_scope_and_all_423_positive_deleted_fits(self):
        d=self.document;self.assertEqual(d['hard_holds'],[])
        self.assertEqual(d['scope'],'numerical_audit_only');self.assertFalse(d['approved_for_source']);self.assertFalse(d['approved_for_modeling'])
        self.assertEqual(d['status'],'numerically_verified_pending_integration');self.assertNotIn('raw_inputs',d)
        pop=d['frozen_population'];self.assertEqual(len(pop['complete_directory_ncessch']),175);self.assertEqual(len(pop['complete_native_school_ids']),217)
        self.assertEqual(len(pop['grade_school_configuration_ids']),143);self.assertEqual(len(pop['outside_reporting_prefix_native_ids']),42)
        self.assertEqual(pop['substantive_grade_scope_hold_ids'],['063432005487'])
        for m in d['models']:
            self.assertEqual(m['coefficients']['n'],141);self.assertEqual(m['coverage']['charter'],{'No':141})
            self.assertEqual(m['coverage']['grade_school_configuration_profiles'],143)
            self.assertEqual(m['independent_verification']['explicit_deleted_fits'],141)
            self.assertEqual((m['diagnostics']['full_residual_degrees_of_freedom'],m['diagnostics']['deleted_residual_degrees_of_freedom']),(139,138))
            self.assertGreater(m['diagnostics']['minimum_deleted_residual_scale'],0)
            self.assertTrue(all(v<audit.VERIFY_TOLERANCE for v in m['independent_verification']['maximum_absolute_errors'].values()))

    def test_exact_original_full_id_namespaces_grade_row_weights_and_income(self):
        raw=self.roster['raw_inputs'];indexes={t:{e['source_row']:e['raw'] for e in raw[t]['records']} for t in audit.roster_audit.ORIGINAL_INVENTORIES}
        for row in self.models['combined']['inputs']:
            refs=row['source_refs'];r=indexes['directory'][refs['directory']['source_row']]
            self.assertEqual((r['LEAID'],r['ST_LEAID'],r['NCESSCH']),('0634320','CA-3768338',row['school_id']))
            self.assertEqual(audit.roster_audit.ccd_identity(r)[1],row['native_school_id'])
            income=indexes['frpm'][refs['income']['source_row']]
            self.assertEqual(row['income_pct'],100*income['FRPM Count (K-12)']/income['Enrollment (K-12)'])
            self.assertEqual(row['individual_FRPM_count'],income['FRPM Count (K-12)'])
            for sub,ref in refs['outcomes'].items():
                self.assertEqual(ref['member'],raw['assessment']['member']);self.assertEqual(ref['fields'],[raw['assessment']['header'][c] for c in ref['columns']])
                counts=[];mets=[]
                self.assertEqual(sorted(map(int,ref['expected_grade_source_rows'])),ref['expected_grades'])
                for grade,ordinal in ref['expected_grade_source_rows'].items():
                    self.assertIs(type(ordinal),int);v=indexes['assessment'][ordinal]
                    self.assertEqual((v['Grade'],v['Test Type'],v['Student Group ID'],v['Test ID']),(grade,'B','1',audit.SUBJECT_VALUES[sub]))
                    self.assertEqual(audit.roster_audit.cds(v),row['native_school_id'])
                    n=int(v['Overall Total']);met=int(v['Count Standard Met and Above'])
                    self.assertEqual(n,int(v['Total Students Tested with Scores']));self.assertGreaterEqual(n,11)
                    counts.append(n);mets.append(met)
                self.assertEqual(row['valid_scores_by_subject'][sub],sum(counts))
                self.assertEqual(row['proficient_counts_by_subject'][sub],sum(mets))
                self.assertEqual(row['outcome_by_subject'][sub],100*sum(mets)/sum(counts))
        f=next(r for r in self.models['math']['inputs'] if r['school_id']=='063432005459')
        self.assertEqual(f['income_enrollment'],163)

    def test_missing_expected_grades_do_not_recover_from_grade13(self):
        for m in self.models.values():
            self.assertEqual({e['school_id'] for e in m['coverage']['excluded_configuration_records']},{'063432011382','063432014617'})
            self.assertNotIn('063432005487',{r['school_id'] for r in m['inputs']})
        link=next(r for r in self.roster['roster_links'] if r['school_id']=='063432011382')
        self.assertIsNotNone(link['subjects']['ES']['math']['native_all_grades13'])
        self.assertIsNone(link['subjects']['ES']['math']['proficiency'])
        # A valid existing all-grades total still does not substitute for an
        # additional expected component that is absent from the original file.
        records=[e for e in self.roster['raw_inputs']['assessment']['records'] if audit.roster_audit.cds(e['raw'])==link['native_school_id'] and e['raw']['Test ID']=='2']
        result=audit.aggregate_subject(records,[3,4,5,6,7,8],True)
        self.assertIsNone(result['proficiency'])

    def test_jeffreys_boundary_variance_requires_verified_strict_scored_counts(self):
        for pct,n in [(0,11),(100,11),(45.678,121)]:
            p=(pct*n/100+.5)/(n+1);self.assertEqual(audit.verified_sampling_variance(pct,n),10000*p*(1-p)/n)
        for pct,n in [(50,True),(50,11.),(50,10),(50,None),(False,11),(101,11),(float('nan'),11),(float('inf'),11)]:
            with self.subTest(pct=pct,n=n),self.assertRaises(ValueError):audit.verified_sampling_variance(pct,n)

    def test_combined_own_scale_studentization_maximum_covariance_and_display_only_count(self):
        math_model,ela,combo=[self.models[s] for s in audit.SUBJECTS]
        for r in combo['inputs']:
            self.assertEqual(r['outcome_pct'],sum(r['outcome_by_subject'].values())/2)
            v=r['variance_by_subject'];self.assertEqual(r['sampling_variance'],(math.sqrt(v['math'])+math.sqrt(v['reading']))**2/4)
            self.assertGreater(r['sampling_variance'],sum(v.values())/4)
            self.assertEqual(r['display_valid_scores'],min(r['valid_scores_by_subject'].values()))
        self.assertIn('not a paired',combo['intervals']['combined_count_display'])
        self.assertTrue(any(abs(c['studentized']-(m['studentized']+e['studentized'])/2)>.01 for c,m,e in zip(combo['results'],math_model['results'],ela['results'])))

    def test_all_423_explicit_deleted_fits_intervals_and_influence_against_raw_numpy(self):
        for m in self.models.values():
            x=np.array([r['income_pct'] for r in m['inputs']]);y=np.array([r['outcome_pct'] for r in m['inputs']]);v=np.array([r['sampling_variance'] for r in m['inputs']]);n=len(x)
            X=np.column_stack([np.ones(n),x]);beta=np.linalg.lstsq(X,y,rcond=None)[0];pred=X@beta;res=y-pred;SSE=float(res@res);H=X@np.linalg.inv(X.T@X)@X.T
            var=((np.eye(n)-H)**2)@v
            for i,row in enumerate(m['results']):
                keep=np.arange(n)!=i;D=X[keep];b=np.linalg.lstsq(D,y[keep],rcond=None)[0];e=y[keep]-D@b;sse=float(e@e);scale=math.sqrt(sse/(n-3));held=float(X[i]@b);hd=float(X[i]@np.linalg.inv(D.T@D)@X[i]);t=(y[i]-held)/(scale*math.sqrt(1+hd));se=math.sqrt(var[i])/(scale*math.sqrt(1-H[i,i]))
                cook=res[i]**2*H[i,i]/(2*(SSE/(n-2))*(1-H[i,i])**2)
                expected={'predicted':pred[i],'residual':res[i],'leverage':H[i,i],'studentized':t,'low':t-1.96*se,'high':t+1.96*se,'deleted_intercept':b[0],'deleted_slope':b[1],'deleted_sse':sse,'deleted_residual_scale':scale,'deleted_held_out_prediction':held,'deleted_held_out_prediction_leverage':hd,'propagated_sampling_variance':var[i],'studentized_sampling_standard_error':se,'cooks_distance':cook}
                for key,value in expected.items():
                    with self.subTest(subject=m['subject'],id=row['school_id'],field=key):self.assertAlmostEqual(row[key],float(value),delta=2e-9)

    def test_every_model_member_contributes_variance_with_deleted_scale_fixed(self):
        m=self.models['math'];x=np.array([r['income_pct'] for r in m['inputs']]);y=np.array([r['outcome_pct'] for r in m['inputs']]);v=np.array([r['sampling_variance'] for r in m['inputs']])
        _,a=audit.fit_model(x-x.mean(),y,v);_,b=audit.fit_model(x-x.mean(),y,4*v)
        shifted=v.copy();shifted[-1]*=100;_,c=audit.fit_model(x-x.mean(),y,shifted)
        self.assertNotEqual(a[0]['high']-a[0]['low'],c[0]['high']-c[0]['low'])
        for left,right in zip(a,b):
            self.assertEqual(left['studentized'],right['studentized']);self.assertAlmostEqual(right['high']-right['low'],2*(left['high']-left['low']),delta=2e-12)

    def test_saved_numerical_corruption_and_caller_expected_cannot_authorize_themselves(self):
        bad=copy.deepcopy(self.document);bad['models'][0]['results'][0]['studentized']+=.5
        with self.assertRaises(ValueError):audit.validate(bad,bad)
        with mock.patch.object(audit,'build',return_value=bad),self.assertRaises(ValueError):audit.validate(bad,bad)

    def test_exact_metadata_counts_reference_types_and_interval_corruptions_reject(self):
        changes=[lambda d:d['models'][0]['inputs'][0].update(income_pct=0),lambda d:d['models'][0]['inputs'][0]['source_refs']['income'].update(source_row=1.),lambda d:d['models'][0]['results'][0].update(valid_scores=True),lambda d:d['models'][0]['results'][0].update(low=None),lambda d:d['models'][0]['results'][0].update(high=float('nan')),lambda d:d.update(approved_for_source=True),lambda d:d['models'][0]['coefficients'].update(n=141.),lambda d:d['models'][2]['inputs'][0].update(sampling_variance=0.)]
        for mutate in changes:
            bad=copy.deepcopy(self.document);mutate(bad)
            with self.assertRaises(ValueError):audit._compare_numerical_documents(bad,self.document)

    def test_public_runtime_policy_and_pin_repins_fail_before_cached_validation(self):
        for name,value in [('MIN_SCHOOLS',29),('MIN_VALID_SCORES',10),('SUBJECT_VALUES',{'math':'1','reading':'2'}),('SOURCE_RAW_SHA','0'*64),('SOURCE_SCHEMA_SHA','0'*64),('SOURCE_DEFINITION_SHA','0'*64),('SOURCE_IDENTITY_SHA','0'*64)]:
            with self.subTest(name=name),mock.patch.object(audit,name,value),self.assertRaises(ValueError):audit.validate(self.document,self.document)
        bad=copy.deepcopy(audit.POLICY);bad['models']='Drop influential cases and infer causality'
        with mock.patch.object(audit,'POLICY',bad),mock.patch.object(audit,'NUMERIC_POLICY_SHA',audit.roster_audit.fingerprint(bad)),self.assertRaises(ValueError):audit.validate(self.document,self.document)

    def test_fresh_changed_missing_complete_source_code_tests_and_originals_reject(self):
        original=Path.read_bytes
        for target in [audit.ROSTER,audit.SOURCE_CODE,audit.SOURCE_TESTS]:
            def changed(path,t=target):return b'changed' if path==t else original(path)
            with self.subTest(path=target),mock.patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):audit.validate(self.document,self.document)
        with mock.patch.object(Path,'read_bytes',side_effect=FileNotFoundError('source missing')),self.assertRaises(FileNotFoundError):audit.validate(self.document,self.document)
        with mock.patch.object(audit.roster_audit,'require_current_originals',side_effect=ValueError('original changed')),self.assertRaises(ValueError):audit.validate(self.document,self.document)

    def test_direct_selector_fit_reject_modified_inputs_and_live_semantics(self):
        inputs=copy.deepcopy(self.models['math']['inputs']);inputs[0]['income_pct']+=1
        with self.assertRaises(ValueError):audit.fit_audited_model(inputs,self.models['math']['coverage'],'math')
        bad=copy.deepcopy(self.roster);bad['coverage']['pure_lower_profiles']=141
        with self.assertRaises(ValueError):audit.selected_inputs(bad,'math')
        with mock.patch.object(audit,'aggregate_subject',return_value={'proficiency':50}),self.assertRaises(ValueError):audit.validate(self.document,self.document)

    def test_degenerate_full_and_deleted_rank_or_positive_scale_fail_closed(self):
        for x,y in [(np.ones(35),np.arange(35,dtype=float)),(np.arange(35,dtype=float),np.ones(35)),(np.arange(35,dtype=float),2*np.arange(35,dtype=float)),(np.arange(35,dtype=float),np.r_[2*np.arange(34),100.])]:
            with self.assertRaises(ValueError):
                model,results=audit.fit_model(x-x.mean(),y,np.ones(35));model['intercept']-=model['slope']*float(x.mean())
                audit.verify_independently(x,y,np.ones(35),model,results)

    def test_unclipped_predictions_and_fixed_model_influence_preserved(self):
        x=np.arange(35,dtype=float);y=110-2*x+np.sin(x)*5;v=np.ones(35)
        model,results=audit.fit_model(x-x.mean(),y,v);model['intercept']-=model['slope']*float(x.mean())
        self.assertGreater(max(r['predicted'] for r in results),100)
        audit.verify_independently(x,y,v,model,results)
        clipped=copy.deepcopy(results);clipped[0]['predicted']=100
        with self.assertRaises(ValueError):audit.verify_independently(x,y,v,model,clipped)
        for m in self.models.values():
            ids={r['school_id'] for r in m['inputs']};self.assertEqual(len(ids),141)
            self.assertTrue(set(r['school_id'] for r in m['diagnostics']['top_ten_cooks_distance'])<=ids)

    def test_contradictory_shared_fitter_creates_explicit_holds_without_changing_membership(self):
        original=audit.fit_model
        def contradictory(x,y,v):
            model,rows=original(x,y,v);model['intercept']+=1
            return model,rows
        with mock.patch.object(audit,'fit_model',contradictory):d=audit.build()
        self.assertEqual(len(d['hard_holds']),3)
        for m in d['models']:
            self.assertEqual(m['status'],'numerical_hold');self.assertEqual(len(m['inputs']),141)
            self.assertFalse(m['approved_for_source']);self.assertFalse(m['approved_for_modeling'])

    def test_coherent_compact_provenance_helper_forgery_rejects_direct_and_cached_expected(self):
        bad=copy.deepcopy(self.document)
        for m in bad['models']:
            for row in m['inputs']+m['coverage']['excluded_configuration_records']:
                row['source_refs']['directory']['source_row']+=1
        original=audit.source_references
        def forged(*args,**kwargs):
            refs=original(*args,**kwargs);refs['directory']['source_row']+=1
            return refs
        for expected in [None,bad]:
            with mock.patch.object(audit,'source_references',forged),self.assertRaises(ValueError):audit.validate(bad,expected)
        original_table=audit.table_reference
        def wrong_table(*args,**kwargs):
            ref=original_table(*args,**kwargs)
            if ref is not None:ref['source_row']+=1
            return ref
        with mock.patch.object(audit,'table_reference',wrong_table),self.assertRaises(ValueError):audit.validate(bad,bad)

    def test_current_comparator_cannot_authorize_altered_metrics_direct_or_cached(self):
        bad=copy.deepcopy(self.document);bad['models'][0]['results'][0]['predicted']+=1
        for expected in [None,bad]:
            with mock.patch.object(audit,'numeric_equal',lambda *args:True),self.assertRaises(ValueError):audit.validate(bad,expected)
        with mock.patch.object(audit,'_compare_numerical_documents',lambda *args:True),self.assertRaises(ValueError):audit.validate(bad,bad)

    def test_fresh_saved_replay_and_compact_provenance_has_no_duplicate_raw_tables(self):
        self.assertEqual(audit.validate(self.document),{f'san-diego-2025-ES-{s}':141 for s in audit.SUBJECTS})
        self.assertEqual(self.document['retained_source_reference']['sha256'],audit.ROSTER_SHA)
        self.assertNotIn('raw_inputs',self.document);self.assertEqual(self.document['count_definition_status']['eligible_subjects_with_verified_counts'],282)
        self.assertTrue(all(m['intervals']['available_for_entire_model'] for m in self.models.values()))


if __name__=='__main__':unittest.main()

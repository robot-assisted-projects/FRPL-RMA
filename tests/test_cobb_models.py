"""Original Cobb source integrity, separate external studentization and point-only contracts."""
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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_cobb_models as audit


class CobbModelAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=audit.load_roster();cls.document=json.loads(audit.OUTPUT.read_text());cls.expected=audit.build(cls.roster)
        cls.models={m['subject']:m for m in cls.document['models']}
        audit.validate(cls.document,cls.expected)

    def test_compact_source_link_false_approvals_and_all_fixed_populations(self):
        d=self.document;self.assertEqual(d['hard_holds'],[]);self.assertFalse(d['approved_for_source']);self.assertFalse(d['approved_for_modeling'])
        self.assertEqual(len(d['source_profiles']),90);self.assertEqual(len(d['retained_scope_exclusions']),20)
        self.assertEqual(d['retained_outside_source_profiles'],[])
        self.assertEqual(d['source_coverage']['district_minus_reported_operational_enrollment'],0)
        ref=d['retained_source_reference'];self.assertEqual((ref['retained_original_record_count'],ref['retained_original_cell_count']),(2260,68573))
        self.assertEqual((ref['complete_original_record_count'],ref['complete_original_cell_count']),(25662,865003));self.assertEqual(ref['omitted_original_records'],23402);self.assertEqual(ref['sha256'],audit.ROSTER_SHA)
        self.assertNotIn('raw_inputs',d);self.assertNotIn('source_definition_evidence',d)
        self.assertEqual(len(d['frozen_population']['complete_directory_ncessch']),110);self.assertEqual(len(d['frozen_population']['complete_native_school_ids']),92)
        for sub in audit.SUBJECTS:
            m=self.models[sub];self.assertEqual(m['coefficients']['n'],90);self.assertEqual(m['coverage']['grade_school_configuration_profiles'],90)
            self.assertEqual(m['coverage']['excluded_configuration_profiles'],0);self.assertEqual(m['independent_verification']['explicit_deleted_fits'],90)
            self.assertEqual((m['diagnostics']['full_residual_degrees_of_freedom'],m['diagnostics']['deleted_residual_degrees_of_freedom']),(88,87))
            self.assertEqual(m['diagnostics']['income_design_rank'],2);self.assertGreater(m['diagnostics']['minimum_deleted_residual_scale'],0)

    def test_exact_original_row_member_header_fields_income_and_fraction_rate_pointers(self):
        raw=self.roster['raw_inputs'];tables={t:{e['source_row']:e['raw']for e in raw[t]['records']}for t in audit.roster_audit.TABLES}
        for m in self.document['models']:
            for r in m['inputs']:
                refs=r['source_refs'];link=self.roster['roster_links'][refs['roster_link_index']];self.assertEqual(link['school_id'],r['school_id']);self.assertIsNone(link['source_attribution_hold'])
                for ref in [refs['directory'],refs['membership'],refs['direct_certification']]+list(refs['outcomes'].values()):
                    if ref is None:continue
                    section=raw[ref['table']];self.assertEqual((ref['source_id'],ref['member']),(section['source_id'],section['member']));self.assertEqual(ref['fields'],[section['header'][i]for i in ref['columns']]);self.assertIs(type(ref['source_row']),int)
                directory=tables['directory'][refs['directory']['source_row']];self.assertEqual((directory['LEAID'],directory['ST_LEAID'],directory['NCESSCH'],directory['ST_SCHID']),('1301290','GA-633',r['school_id'],r['native_school_id']))
                n=tables['membership'][refs['membership']['source_row']];dc=tables['lunch'][refs['direct_certification']['source_row']]
                self.assertEqual((dc['DATA_GROUP'],dc['LUNCH_PROGRAM'],dc['TOTAL_INDICATOR'],dc['DMS_FLAG']),('Direct Certification','Not Applicable','Education Unit Total','Reported'));self.assertEqual(n['DMS_FLAG'],'Reported')
                self.assertEqual((r['income_enrollment'],r['reported_direct_certified_count']),(int(n['STUDENT_COUNT']),int(dc['STUDENT_COUNT'])));self.assertEqual(r['income_pct'],100*int(dc['STUDENT_COUNT'])/int(n['STUDENT_COUNT']))
                grades=refs['enrolled_grades'];self.assertEqual(grades['fields'],[raw['membership']['header'][i]for i in grades['columns']]);self.assertEqual(grades['member'],raw['membership']['member'])
                for grade,row in grades['source_rows'].items():
                    e=tables['membership'][row];self.assertEqual((e['NCESSCH'],e['GRADE']),(r['school_id'],grade))
                    if grade not in audit.roster_audit.LOWER_GRADES:self.assertEqual(e['STUDENT_COUNT'],'0')
                for sub in ['math','reading']:
                    ref=refs['outcomes'][sub]
                    if ref is None:self.assertIsNone(r['outcome_by_subject'][sub]);continue
                    e=tables['assessment'][ref['source_row']];self.assertTrue(all(e[k]==v for k,v in audit.ASSESSMENT_SELECTOR.items()));self.assertEqual(e['NCESSchoolID'],r['school_id'])
                    self.assertEqual(e['Subject'],audit.SUBJECT_VALUES[sub]);self.assertEqual(r['raw_published_rates'][sub],e[audit.RATE_FIELD]);self.assertEqual(r['outcome_by_subject'][sub],audit.original_rate(e[audit.RATE_FIELD]))

    def test_primary_high_mixed_charter_and_uncertified_eog_eoc_scope_are_preserved(self):
        p=self.document['frozen_population']
        self.assertEqual(set(p['primary_only_ids']),{'130129000552','130129003528'})
        self.assertEqual((len(p['high_school_configuration_ids']),len(p['mixed_configuration_ids'])),(16,2))
        self.assertEqual(p['outside_charter_ids'],['130129000513']);self.assertEqual(p['unmatched_native_school_ids'],[])
        self.assertTrue(all(r['source_attribution_hold']is None for r in self.document['source_profiles']))
        self.assertFalse(self.document['source_coverage']['EOG_accelerated_EOC_population_certified'])
        self.assertIn('Medicaid',audit.POLICY['income_metadata']);self.assertIn('foster',audit.POLICY['income_metadata'])
        self.assertIn('does not certify attribution completeness',audit.POLICY['attribution']);self.assertIn('EOC',audit.STANDARD)
        for m in self.models.values():self.assertFalse(set(p['primary_only_ids']+p['outside_charter_ids'])&{r['school_id']for r in m['inputs']})

    def test_combined_uses_own_paired_fit_deletion_scale_and_t(self):
        m,e,c=[self.models[s]for s in audit.SUBJECTS]
        self.assertEqual([r['school_id']for r in m['inputs']],[r['school_id']for r in c['inputs']]);self.assertEqual(len(e['inputs']),90)
        # With identical x/cohorts OLS coefficients are linear, but scales and t are not.
        self.assertAlmostEqual(c['coefficients']['intercept'],(m['coefficients']['intercept']+e['coefficients']['intercept'])/2,places=11)
        self.assertAlmostEqual(c['coefficients']['slope'],(m['coefficients']['slope']+e['coefficients']['slope'])/2,places=11)
        for r in c['inputs']:self.assertEqual(r['outcome_pct'],(r['outcome_by_subject']['math']+r['outcome_by_subject']['reading'])/2)
        by_m={r['school_id']:r for r in m['results']};by_e={r['school_id']:r for r in e['results']}
        self.assertTrue(any(abs(r['studentized']-(by_m[r['school_id']]['studentized']+by_e[r['school_id']]['studentized'])/2)>.01 for r in c['results']))
        changed=copy.deepcopy(self.document)
        for r in changed['models'][2]['results']:r['studentized']=(by_m[r['school_id']]['studentized']+by_e[r['school_id']]['studentized'])/2
        with self.assertRaises(ValueError):audit.validate(changed,self.expected)

    def test_unweighted_full_and_all_270_deleted_fits_match_raw_design_studentization(self):
        total=0
        for m in self.document['models']:
            x=np.array([r['income_pct']for r in m['inputs']]);y=np.array([r['outcome_pct']for r in m['inputs']]);n=len(x);X=np.column_stack([np.ones(n),x]);b=np.linalg.lstsq(X,y,rcond=None)[0];p=X@b;res=y-p;sse=float(res@res);s2=sse/(n-2);H=X@np.linalg.inv(X.T@X)@X.T
            self.assertAlmostEqual(float(b[0]),m['coefficients']['intercept'],delta=2e-9);self.assertAlmostEqual(float(b[1]),m['coefficients']['slope'],delta=2e-9)
            for i,r in enumerate(m['results']):
                keep=np.arange(n)!=i;D=X[keep];db=np.linalg.lstsq(D,y[keep],rcond=None)[0];dr=y[keep]-D@db;dsse=float(dr@dr);scale=math.sqrt(dsse/(n-3));held=float(X[i]@db);h=float(X[i]@np.linalg.inv(D.T@D)@X[i]);t=(y[i]-held)/(scale*math.sqrt(1+h));cook=res[i]**2*H[i,i]/(2*s2*(1-H[i,i])**2);end=np.column_stack([np.ones(2),[x.min(),x.max()]]);shift=float(np.max(np.abs(end@b-end@db)))
                for actual,expected in [(r['predicted'],p[i]),(r['residual'],res[i]),(r['leverage'],H[i,i]),(r['studentized'],t),(r['cooks_distance'],cook),(r['deleted_intercept'],db[0]),(r['deleted_slope'],db[1]),(r['deleted_sse'],dsse),(r['deleted_residual_scale'],scale),(r['deleted_held_out_prediction'],held),(r['deleted_held_out_prediction_leverage'],h),(r['maximum_prediction_change_on_observed_income_range'],shift)]:self.assertAlmostEqual(actual,float(expected),delta=2e-9)
                total+=1
        self.assertEqual(total,270)

    def test_extremes_and_influence_remain_members_and_predictions_are_unclamped(self):
        for sub,key in [('math','130129002158'),('reading','130129001880'),('combined','130129001880')]:
            m=self.models[sub];self.assertEqual(sum(r['charter']=='Yes'for r in m['inputs']),0);self.assertEqual(m['diagnostics']['top_ten_cooks_distance'][0]['school_id'],key);self.assertIn(key,{r['school_id']for r in m['results']})
            self.assertEqual(m['diagnostics']['predictions_outside_percentage_range'],0);self.assertAlmostEqual(m['diagnostics']['income']['minimum'],0.5671077504725898,places=12);self.assertAlmostEqual(m['diagnostics']['income']['maximum'],39.421965317919074,places=12)
        x=np.linspace(0,100,40);y=np.clip(110-.8*x+np.sin(x)*2,0,100);b,rows=audit.fit_model(x,y,np.zeros(40));self.assertGreater(rows[0]['predicted'],100)
        for row in rows:row.update(low=None,high=None)
        deleted,_=audit.verify_independently(x,y,b,rows);self.assertEqual(len(deleted),40);self.assertGreater(rows[0]['predicted'],100)

    def test_original_rate_count_types_masks_zero_and_no_unverified_count_screen(self):
        for v,want in [('0',0.),('1',100.),('.52',52.),('*',None),('.1-.2',None),('',None),('1.01',None)]:self.assertEqual(audit.original_rate(v),want)
        for value in [False,0,1.,None]:
            with self.assertRaises(ValueError):audit.original_rate(value)
        for count,flag,want in [('0','Reported',0),('12','Reported',12),('12','Derived',None),('-9','Missing',None),('*','Suppressed',None)]:self.assertEqual(audit.original_count({'STUDENT_COUNT':count,'DMS_FLAG':flag}),want)
        for value in [False,12,12.]:
            with self.assertRaises(ValueError):audit.original_count({'STUDENT_COUNT':value,'DMS_FLAG':'Reported'})
        changed=copy.deepcopy(self.roster)
        for e in changed['raw_inputs']['assessment']['records']:
            for key in ['StudentGroup_TotalTested','StudentSubGroup_TotalTested','ProficientOrAbove_count','Lev1_count','Lev2_count','Lev3_count','Lev4_count']:e['raw'][key]='0'
        with mock.patch.object(audit,'require_frozen_roster'):
            values,coverage=audit.selected_inputs(changed,'math')
        self.assertEqual(values,self.models['math']['inputs']);self.assertEqual(coverage,self.models['math']['coverage'])

    def test_independent_selector_rejects_grade_income_identity_and_assessment_substitutions(self):
        key=self.models['math']['inputs'][0]['school_id']
        for mutation in ['high','span','membership','derived_income','rate','alternative','native_id','hold']:
            d=copy.deepcopy(self.roster);raw=d['raw_inputs'];link=next(r for r in d['roster_links']if r['school_id']==key)
            if mutation in ['high','span']:next(e for e in raw['directory']['records']if e['raw']['NCESSCH']==key)['raw'][{'high':'G_9_OFFERED','span':'GSHI'}[mutation]]={'high':'Yes','span':'12'}[mutation]
            elif mutation=='membership':next(e for e in raw['membership']['records']if e['raw']['NCESSCH']==key and e['raw']['TOTAL_INDICATOR']=='Education Unit Total')['raw']['STUDENT_COUNT']='0'
            elif mutation=='derived_income':next(e for e in raw['lunch']['records']if e['raw']['NCESSCH']==key and e['raw']['DATA_GROUP']=='Direct Certification')['raw']['DMS_FLAG']='Derived'
            elif mutation in ['rate','alternative','native_id']:
                e=next(e for e in raw['assessment']['records']if e['raw']['NCESSchoolID']==key and e['raw']['Subject']=='math'and e['raw']['GradeLevel']=='G38');e['raw'][{'rate':'ProficientOrAbove_percent','alternative':'AssmtType','native_id':'NCESSchoolID'}[mutation]]={'rate':'.999','alternative':'Alternate','native_id':'130129099999'}[mutation]
            else:link['source_attribution_hold']='Invented attribution hold'
            with self.subTest(mutation=mutation),mock.patch.object(audit,'require_frozen_roster'),self.assertRaises(ValueError):audit.selected_inputs(d,'math')

    def test_direct_fit_rejects_exact_input_count_reference_and_scope_changes_before_fitting(self):
        m=self.models['math'];mutations=[lambda x:x.pop(),lambda x:x.reverse(),lambda x:x.append(copy.deepcopy(x[0])),lambda x:x[0].update(level='HS'),lambda x:x[0].update(income_year=2025.),lambda x:x[0].update(native_school_id='GA-633-9999'),lambda x:x[0].update(income_pct=False),lambda x:x[0].update(income_pct=x[0]['income_pct']+1e-12),lambda x:x[0].update(display_valid_scores=12),lambda x:x[0].update(sampling_variance=0.),lambda x:x[0].update(ten_valid_scored_floor_certified=True),lambda x:x[0]['source_refs']['membership'].update(source_row=1.),lambda x:x[0]['source_refs']['enrolled_grades']['source_rows'].update({'Grade 3':0}),lambda x:x[0]['raw_published_rates'].update(math='0')]
        for i,change in enumerate(mutations):
            values=copy.deepcopy(m['inputs']);change(values)
            with self.subTest(i=i),mock.patch.object(audit,'fit_model',side_effect=AssertionError('Never fit corrupt source input')),self.assertRaises(ValueError):audit.fit_audited_model(values,m['coverage'],'math')
        with mock.patch.object(audit,'fit_model',side_effect=AssertionError('No fit below minimum')),self.assertRaises(ValueError):audit.fit_audited_model(m['inputs'][:29],m['coverage'],'math')

    def test_current_numerical_policy_runtime_types_and_public_repins_fail_cached_replay(self):
        policy=copy.deepcopy(audit.POLICY);policy['models']='Drop influential schools and average full subject coefficients'
        mutations=[('POLICY',policy),('MIN_SCHOOLS',30.),('MIN_SCHOOLS',False),('SUBJECTS',['math','combined']),('SUBJECT_VALUES',{'math':'sci','reading':'ela'}),('ASSESSMENT','Different assessment'),('STANDARD','Different standard'),('ASSESSMENT_SELECTOR',dict(audit.ASSESSMENT_SELECTOR,GradeLevel='G03')),('INCOME_FIELDS',['LUNCH_PROGRAM','STUDENT_COUNT']),('RATE_FIELD','ProficientOrAbove_count'),('VERIFY_TOLERANCE',1.),('SOURCE_RAW_SHA','0'*64)]
        for field,value in mutations:
            with self.subTest(field=field),mock.patch.object(audit,field,value):
                repin=audit.roster_audit.fingerprint(audit.runtime_contract());pol=audit.roster_audit.fingerprint(audit.POLICY)
                with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',repin),mock.patch.object(audit,'NUMERIC_POLICY_SHA',pol):
                    with self.assertRaises(ValueError):audit.validate(self.document,self.expected)
                    with self.assertRaises(ValueError):audit.selected_inputs(self.roster,'math')

    def test_cached_replay_freshly_requires_complete_source_code_tests_secondary_and_current_source_literals(self):
        original=Path.read_bytes;secondary=audit.ROOT/'data/source/ccd-state-snapshots.json'
        for target in [audit.ROSTER,audit.SOURCE_CODE,audit.SOURCE_TESTS,secondary]:
            for missing in [True,False]:
                def read(path):
                    if path==target:
                        if missing:raise FileNotFoundError('Private missing immutable source fixture')
                        return b'{}'
                    return original(path)
                with self.subTest(path=target.name,missing=missing),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):audit.validate(self.document,self.expected)
        for key in ['RAW_INPUT_SHA','ORIGINAL_SCHEMA_SHA','DEFINITION_INPUT_SHA','ORIGINAL_IDENTITY_SHA','STATE_EXTRACT_SHA','GA_SNAPSHOT_SHA']:
            with self.subTest(current_source=key),mock.patch.object(audit.roster_audit,key,'0'*64):
                repin=audit.roster_audit.fingerprint(audit.roster_audit.runtime_contract())
                with mock.patch.object(audit.roster_audit,'RUNTIME_CONTRACT_SHA',repin),mock.patch.object(audit.roster_audit,'LITERAL_RUNTIME_SHA',repin,create=True),self.assertRaises(ValueError):audit.validate(self.document,self.expected)
        with mock.patch.object(audit,'load_roster',wraps=audit.load_roster)as loader:
            self.assertEqual(audit.validate(self.document,self.expected),{f'cobb-2025-ES-{s}':n for s,n in [(s,90)for s in audit.SUBJECTS]});self.assertGreater(loader.call_count,0)

    def test_all_counts_variances_endpoints_and_scored_floor_remain_modelwide_unavailable(self):
        for m in self.document['models']:
            self.assertFalse(m['approved_for_source']);self.assertFalse(m['approved_for_modeling']);self.assertFalse(m['valid_score_floor_certified']);self.assertFalse(m['intervals']['available_for_entire_model']);self.assertIsNone(m['intervals']['valid_score_counts']);self.assertIsNone(m['intervals']['sampling_variances'])
            for r in m['inputs']:
                self.assertEqual(r['valid_scores_by_subject'],{'math':None,'reading':None});self.assertIsNone(r['display_valid_scores']);self.assertIsNone(r['sampling_variance']);self.assertFalse(r['ten_valid_scored_floor_certified'])
            for r in m['results']:self.assertTrue(all(r[k]is None for k in ['valid_scores','sampling_variance','low','high']))
        real=audit.fit_model;seen=[]
        def capture(x,y,variance):seen.append(variance.copy());return real(x,y,variance)
        m=self.models['math']
        with mock.patch.object(audit,'fit_model',side_effect=capture):result=audit.fit_audited_model(m['inputs'],m['coverage'],'math')
        self.assertTrue(np.array_equal(seen[0],np.zeros(90)));self.assertTrue(all(r['low']is None and r['high']is None for r in result['results']))

    def test_rank_full_deleted_positive_scales_and_corrupt_fitter_are_hard_gates(self):
        m=self.models['math'];x=np.array([r['income_pct']for r in m['inputs']]);y=np.array([r['outcome_pct']for r in m['inputs']]);n=len(x)
        for a,b in [(np.full(n,20.),y),(x,10+.5*x),(np.r_[30.,np.full(n-1,20.)],y)]:
            with self.assertRaises(ValueError):audit.fit_model(a,b,np.zeros(n))
        y=10+.5*x;y[0]+=1;z=x-x.mean();X=np.column_stack([np.ones(n),z]);beta=np.linalg.lstsq(X,y,rcond=None)[0];p=X@beta;e=y-p;h=1/n+z*z/(z@z)
        b={'n':n,'intercept':float(beta[0]-beta[1]*x.mean()),'slope':float(beta[1]),'r2':float(1-(e@e)/((y-y.mean())@(y-y.mean())))};rows=[dict(actual=float(a),predicted=float(p),residual=float(e),leverage=float(h),studentized=0.,low=None,high=None)for a,p,e,h in zip(y,p,e,h)]
        with self.assertRaisesRegex(ValueError,'deleted-school residual scale'):audit.verify_independently(x,y,b,rows)
        real=audit.fit_model
        for location,key,bad in [('coefficients','intercept',0.),('coefficients','n',False),('results','predicted',float('inf')),('results','studentized',0.),('results','residual',False)]:
            def corrupt(x,y,v):
                b,r=real(x,y,v);(b if location=='coefficients'else r[0])[key]=bad;return b,r
            with self.subTest(key=key),mock.patch.object(audit,'fit_model',side_effect=corrupt),self.assertRaises(ValueError):audit.fit_audited_model(m['inputs'],m['coverage'],'math')

    def test_saved_metadata_counts_holds_exact_inputs_and_finite_metrics_reject_corruption(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d['source_profiles'][0].update(source_attribution_hold='Invented'),lambda d:d['count_definition_status'].update(ten_valid_scored_floor_certified=True),lambda d:d['sources']['roster_audit'].update(sha256='0'*64),lambda d:d['models'][0]['inputs'][0].update(income_pct=25.),lambda d:d['models'][0]['coverage'].update(usable_schools=89),lambda d:d['models'][0]['intervals'].update(valid_score_counts=100),lambda d:d['models'][0]['results'][0].update(actual=d['models'][0]['results'][0]['actual']+1e-12),lambda d:d['models'][0]['results'][0].update(low=0.),lambda d:d['models'][0]['results'][0].update(sampling_variance=0.),lambda d:d['models'][0]['independent_verification'].update(tolerance_absolute=1.),lambda d:d['retained_scope_exclusions'].pop()]
        for change in mutations:
            d=copy.deepcopy(self.document);change(d)
            with self.assertRaises(ValueError):audit.validate(d,self.expected)
        for key in ['predicted','studentized','deleted_sse','deleted_residual_scale']:
            for bad in [False,float('nan')]:
                d=copy.deepcopy(self.document);d['models'][0]['results'][0][key]=bad
                with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):audit.validate(d,self.expected)
        self.assertFalse(audit.numeric_equal(True,1.));self.assertFalse(audit.numeric_equal(2025.,2025));self.assertTrue(audit.numeric_equal(1.+1e-12,1.))

    def test_two_numerical_builds_and_read_only_offline_replay_are_identical(self):
        for path,sha in [(audit.ROSTER,audit.ROSTER_SHA),(audit.SOURCE_CODE,audit.SOURCE_CODE_SHA),(audit.SOURCE_TESTS,audit.SOURCE_TESTS_SHA)]:self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),sha)
        with tempfile.TemporaryDirectory()as t:
            a,b=Path(t)/'one.json',Path(t)/'two.json';one=audit.prepare(a);two=audit.prepare(b);self.assertEqual(one,two);self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(a.read_bytes(),audit.OUTPUT.read_bytes());before=a.read_bytes()
            with mock.patch.object(audit.roster_audit,'extract_raw_inputs',side_effect=AssertionError('No source re-extraction')),mock.patch.object(audit.roster_audit.subprocess,'Popen',side_effect=AssertionError('No original stream')):self.assertEqual(audit.prepare(a,check=True),one)
            self.assertEqual(before,a.read_bytes())

    def test_supplied_expected_cannot_authorize_its_own_altered_metrics_or_public_alias(self):
        changed=copy.deepcopy(self.document);changed['models'][0]['results'][0]['studentized']+=.1
        with self.assertRaises(ValueError):audit.validate(changed,changed)
        with self.assertRaises(ValueError):audit.validate(self.document,changed)
        # Public, reassignable expected values are not consulted by authorization.
        with mock.patch.object(audit,'EXPECTED_JSON',json.dumps(changed),create=True),mock.patch.object(audit,'EXPECTED_SHA',audit.roster_audit.fingerprint(changed),create=True),self.assertRaises(ValueError):audit.validate(changed,changed)


if __name__=='__main__':unittest.main()

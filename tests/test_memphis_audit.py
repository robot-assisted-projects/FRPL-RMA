"""Meaningful original-source and fail-closed Memphis attribution contracts."""
import copy,json,re,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_memphis as audit

class MemphisSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads(audit.OUTPUT.read_text());cls.snapshot=audit.load_state_snapshot()
    def reject(self,change,repin=False):
        d=copy.deepcopy(self.doc);change(d)
        self.assertNotEqual(audit.fingerprint(d),audit.fingerprint(self.doc))
        with patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])if repin else audit.RAW_INPUT_SHA):
            with self.assertRaises((ValueError,TypeError,KeyError)):audit.validate(d,self.snapshot)
    def test_complete_original_inventory_source_only_and_exact_subject_cohorts(self):
        c=audit.validate(self.doc,self.snapshot)
        self.assertEqual(c['source_rows'],{'directory':223,'lea_directory':1,'membership':1756,'lea_membership':16,'lunch':1040,'assessment':332})
        self.assertEqual((c['original_records'],c['original_typed_cells']),(3368,80349))
        self.assertEqual((c['complete_original_records'],c['complete_original_typed_cells']),(48950,1579478))
        self.assertEqual(c['prospective_grade_profiles'],154)
        self.assertEqual(c['prospective_raw_published_rates'],{'math':146,'reading':151,'combined':146})
        self.assertEqual(c['prospective_usable'],{'math':142,'reading':147,'combined':142})
        self.assertFalse(self.doc['approved_for_source']);self.assertFalse(self.doc['approved_for_modeling']);self.assertNotIn('models',self.doc)
    def test_four_shared_time_attribution_holds_preserve_raw_evidence_not_diagnostics(self):
        ids=['470014801583','470014801595','470014801960','470014802217'];self.assertEqual(self.doc['coverage']['shared_time_prospective_hold_ids'],ids)
        links={r['school_id']:r for r in self.doc['roster_links']}
        for key in ids:
            r=links[key];self.assertTrue(r['source_profile_eligible']);self.assertIsNotNone(r['income']['reported_percentage']);self.assertLessEqual(r['income']['reported_direct_certification'],r['income']['reported_membership']);self.assertFalse(r['income']['usable'])
            for s in ['math','reading','combined']:self.assertIsNotNone(r['subjects'][s]['native_rate']);self.assertFalse(r['subjects'][s]['usable']);self.assertIn('shared-time',r['subjects'][s]['exclusion'])
        self.assertEqual(len(self.doc['coverage']['shared_time_outside_grade_ids']),9)
        self.reject(lambda d:next(r for r in d['roster_links']if r['school_id']==ids[0]).update(source_attribution_hold=None))
    def test_exact_original_income_ratios_and_rates_no_funding_or_count_substitution(self):
        inputs=self.doc['raw_inputs'];lunch={e['source_row']:e['raw']for e in inputs['lunch']['records']};member={e['source_row']:e['raw']for e in inputs['membership']['records']};edc={e['source_row']:e['raw']for e in inputs['assessment']['records']}
        for r in self.doc['roster_links']:
            if not r['source_profile_eligible']:continue
            income=r['income'];n=member[income['membership_source_row']];dc=lunch[income['direct_source_row']];self.assertEqual((dc['DATA_GROUP'],dc['TOTAL_INDICATOR'],dc['DMS_FLAG']),('Direct Certification','Education Unit Total','Reported'));self.assertEqual(n['DMS_FLAG'],'Reported');self.assertEqual(income['reported_percentage'],100*int(dc['STUDENT_COUNT'])/int(n['STUDENT_COUNT']))
            for subject in ['math','reading']:
                v=r['subjects'][subject]
                if v['source_row']is None:continue
                q=edc[v['source_row']];self.assertEqual((q['GradeLevel'],q['DataLevel'],q['AssmtName'],q['AssmtType'],q['StudentGroup'],q['StudentSubGroup']),('G38','School','TNReady','Regular','All Students','All Students'))
                raw=q['ProficientOrAbove_percent'];expected=100*float(raw)if re.fullmatch(r'(?:0?\.\d+|[01](?:\.\d+)?)',raw)and 0<=float(raw)<=1 else None;self.assertEqual(v['native_rate'],expected)
    def test_masks_exact_zero_whole_percent_tokens_and_reported_flags(self):
        for raw,want in [('0',0.),('1',100.),('.07',7.000000000000001),('*',None),('--',None),('.1-.2',None),('',None),('1.01',None)]:self.assertEqual(audit.exact_rate(raw),want)
        for value in [None,False,0,1.]:
            with self.assertRaises(ValueError):audit.exact_rate(value)
        for count,flag,want in [('0','Reported',0),('12','Reported',12),('12','Derived',None),('-9','Missing',None),('','Not reported',None),('*','Suppressed',None)]:self.assertEqual(audit.reported_count({'STUDENT_COUNT':count,'DMS_FLAG':flag}),want)
        for value in [False,12,12.]:
            with self.assertRaises(ValueError):audit.reported_count({'STUDENT_COUNT':value,'DMS_FLAG':'Reported'})
    def test_original_grade_population_includes_charters_and_keeps_high_mixed_missing_outside(self):
        c=self.doc['coverage'];self.assertEqual(c['prospective_charters'],41);self.assertEqual(c['usable_charters'],{'math':40,'reading':41,'combined':40});self.assertEqual(c['operational_offered_scope'],{'ES':167,'mixed':16,'HS':40})
        for r in self.doc['roster_links']:
            if r['source_profile_eligible']:self.assertTrue(r['membership']['reconciled_pure_lower']);self.assertTrue(r['membership']['positive_reported_tested_grade']);self.assertTrue(r['offered']['tested_grade_offers'])
            elif r['offered']['scope']in ['HS','mixed']:self.assertTrue(all(not v['usable']for v in r['subjects'].values()))
        self.reject(lambda d:d['coverage'].update(prospective_charters=0))
    def test_native_only_and_agency_school_difference_are_not_identity_or_cause_repairs(self):
        self.assertEqual(self.doc['coverage']['native_only_ids'],['470014802229']);self.assertEqual(self.doc['coverage']['district_reported_enrollment'],111124);self.assertEqual(self.doc['coverage']['reported_operational_enrollment_sum'],111125);self.assertEqual(self.doc['coverage']['district_minus_reported_operational_enrollment'],-1)
        self.assertNotIn('470014802229',{r['school_id']for r in self.doc['roster_links']});self.assertIn('no inferred',self.doc['outside_native_profiles'][0]['exclusion'])
        self.reject(lambda d:d['outside_native_profiles'][0].update(ncessch='470014810512'))
    def test_all_counts_floor_variances_endpoints_unavailable_no_derived_level_or_participation_use(self):
        for r in self.doc['roster_links']:
            for v in r['subjects'].values():
                for key in ['tested','valid_scores','sampling_variance','low','high']:self.assertIsNone(v[key])
                self.assertFalse(v['sampling_interval_available']);self.assertFalse(v['ten_valid_scored_floor_certified'])
        for mutate in [lambda d:d['roster_links'][0]['subjects']['math'].update(tested=100,valid_scores=100),lambda d:d['roster_links'][0]['subjects']['math'].update(sampling_variance=0.),lambda d:d['coverage'].update(ten_valid_scored_floor_certified=True),lambda d:d.update(approved_for_modeling=True)]:self.reject(mutate)
    def test_current_policy_selectors_types_and_repin_aliases_fail_cached_replay(self):
        cases=[{'YEAR':2025.},{'NATIVE_DISTRICT':'793'},{'SUBJECTS':{'math':'sci','reading':'ela'}},{'ASSESSMENT_SELECTOR':dict(audit.ASSESSMENT_SELECTOR,GradeLevel='G03')},{'SHARED_TIME_IDS':[]},{'RAW_INPUT_SHA':'0'*64},{'ORIGINAL_SCHEMA_SHA':'0'*64},{'DEFINITION_INPUT_SHA':'0'*64},{'ORIGINAL_IDENTITY_SHA':'0'*64}]
        pol=dict(audit.POLICY,income='Use universal meal counts and adjusted full FRPL');cases.append({'POLICY':pol,'POLICY_SHA':audit.fingerprint(pol),'LITERAL_POLICY_SHA':audit.fingerprint(pol)})
        for changes in cases:
            with self.subTest(changes=list(changes)):
                with patch.multiple(audit,**changes):runtime=audit.fingerprint(audit.runtime_contract())
                changes=dict(changes,RUNTIME_CONTRACT_SHA=runtime,LITERAL_RUNTIME_SHA=runtime)
                with patch.multiple(audit,**changes):
                    with self.assertRaises(ValueError):audit.validate(self.doc,self.snapshot)
    def test_coherent_raw_primary_header_and_identity_repins_cannot_resign_originals(self):
        for t in audit.TABLES:
            self.reject(lambda d,t=t:d['raw_inputs'][t]['records'][0].update(source_row=float(d['raw_inputs'][t]['records'][0]['source_row'])),repin=True)
        d=copy.deepcopy(self.doc);d['raw_inputs']['definitions']['edc_technical_v3_1']['pages'][0]['page_number']=59
        changes={'RAW_INPUT_SHA':audit.fingerprint(d['raw_inputs']),'DEFINITION_INPUT_SHA':audit.fingerprint(d['raw_inputs']['definitions'])}
        with patch.multiple(audit,**changes):runtime=audit.fingerprint(audit.runtime_contract())
        changes.update(RUNTIME_CONTRACT_SHA=runtime,LITERAL_RUNTIME_SHA=runtime)
        with patch.multiple(audit,**changes):
            with self.assertRaises(ValueError):audit.validate(d,self.snapshot)
        for change in [lambda d:d['raw_inputs']['directory']['records'][0]['raw'].update(WEBSITE='fake'),lambda d:d['raw_inputs']['lunch']['records'][0]['raw'].update(DATA_GROUP='Direct Certification'),lambda d:d['raw_inputs']['assessment']['records'][0]['raw'].update(GradeLevel='G03',StudentGroup='Economically Disadvantaged')]:self.reject(change,repin=True)
    def test_source_header_year_id_and_native_population_changes_fail(self):
        cases=[lambda d:d.update(year=2024),lambda d:d['raw_inputs']['assessment']['header'].__setitem__(33,'StudentSubGroup_TotalTested'),lambda d:d['raw_inputs']['directory']['records'][0]['raw'].update(ST_LEAID='TN-00793'),lambda d:d['raw_inputs']['membership']['records'][0]['raw'].update(DMS_FLAG=True),lambda d:d['raw_inputs']['assessment']['records'][0]['raw'].update(SchYear='2023-24')]
        for change in cases:self.reject(change)
    def test_secondary_complete_file_is_freshly_required_even_with_cached_snapshot(self):
        original=Path.read_bytes;target=audit.ROOT/'data/source/ccd-state-snapshots.json'
        for missing in [True,False]:
            def read(path,*args,**kwargs):
                if path==target:
                    if missing:raise FileNotFoundError('private missing-secondary fixture')
                    return b'{}'
                return original(path,*args,**kwargs)
            with patch.object(Path,'read_bytes',read):
                with self.assertRaises((ValueError,FileNotFoundError)):audit.validate(self.doc,self.snapshot)
    def test_default_replay_does_not_extract_fit_import_or_mutate_old_state(self):
        with patch.object(audit,'extract_raw_inputs',side_effect=AssertionError('Default replay must not reopen originals')),patch.object(audit.subprocess,'Popen',side_effect=AssertionError('Default replay cannot extract archives')):
            self.assertEqual(audit.validate(self.doc)['model_results'],0)
        self.assertEqual(self.doc['coverage']['secondary_original_profile_matches'],153)
    def test_compact_retention_keeps_all_needed_fields_masks_and_exact_omission_inventories(self):
        raw=self.doc['raw_inputs'];full=0;omitted=0
        for t in audit.TABLES:
            e=raw['omitted_original_populations'][t];kept={x['source_row']for x in raw[t]['records']};unused=e['omitted_source_rows'];self.assertEqual(len(kept),e['retained_records']);self.assertEqual(len(unused),e['omitted_records']);self.assertEqual(len(set(unused)),len(unused));self.assertFalse(kept&set(unused));self.assertEqual(len(kept)+len(unused),e['complete_original_records']);self.assertEqual(sum(x['records']for x in e['omitted_population_counts']),len(unused));self.assertEqual(sorted(x for rows in e['omitted_rows_by_original_identity'].values()for x in rows),unused)
            for record in raw[t]['records']:self.assertEqual(set(record['raw']),set(raw[t]['header']))
            full+=e['complete_original_records'];omitted+=e['omitted_records']
        self.assertEqual(full,48950);self.assertEqual(omitted,45582)
        row=next(e for e in raw['assessment']['records']if e['source_row']==157956);self.assertEqual(row['raw']['ProficientOrAbove_percent'],'*');self.assertEqual(row['raw']['StudentSubGroup_TotalTested'],'172')
        self.reject(lambda d:d['raw_inputs']['omitted_original_populations']['assessment']['omitted_source_rows'].__setitem__(0,0),repin=True)

if __name__=='__main__':unittest.main()

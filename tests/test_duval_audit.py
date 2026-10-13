import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_duval as audit


class DuvalSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.snapshot=audit.load_florida()
        cls.links={r['school_id']:r for r in cls.document['roster_links']}
        cls.inputs=cls.document['raw_inputs']

    def test_complete_original_roster_typed_cells_source_only_and_exact_cohorts(self):
        coverage=audit.validate(self.document,self.snapshot)
        self.assertEqual(coverage['source_rows'],dict(directory=211,lea_directory=1,membership=1688,lea_membership=16,native_grades=201,native_income=201,native_assessment=177))
        self.assertEqual((coverage['original_records'],coverage['original_typed_cells']),(2495,59985))
        self.assertEqual((coverage['ccd_directory'],coverage['operational_roster'],coverage['nonoperational_directory']),(211,203,8))
        self.assertEqual(coverage['operational_offered_scope'],{'ES':155,'HS':24,'mixed':24})
        self.assertEqual((coverage['native_fall_profiles'],coverage['native_income_rows'],coverage['native_assessment_rows'],coverage['exact_operational_fall_matches']),(201,201,177,200))
        self.assertEqual((coverage['prospective_source_profiles'],coverage['prospective_usable_income']),(150,150))
        self.assertEqual(coverage['prospective_usable'],{'math':146,'reading':146,'combined':146})
        self.assertEqual((self.document['scope'],self.document['status']),('source_cohort_audit_only','audit_pending'))
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        for key in ['models','coefficients','canonical_dataset','model_results']:self.assertNotIn(key,self.document)
        for s in ['math','reading','combined']:
            cohort=self.document['cohorts']['prospective_tested_grade_profiles']['subjects'][s]
            self.assertEqual(cohort['charter'],{'No':116,'Yes':30})
            self.assertEqual(set(cohort['eligible_school_ids']),set(self.document['cohorts']['prospective_tested_grade_profiles']['subjects']['math']['eligible_school_ids']))

    def test_offered_native_grade_disagreements_zero_tested_primary_missing_and_unmatched_preserved(self):
        coverage=self.document['coverage']
        self.assertEqual(coverage['operational_without_native_fall_ids'],['16-1981','16-7001','16-7004'])
        self.assertEqual(coverage['outside_native_profile_ids'],['16-0734'])
        self.assertEqual((coverage['offered_enrolled_disagreement_profiles'],coverage['protected_native_grade_profiles'],coverage['protected_native_grade_cells']),(22,20,65))
        smart=self.links['16-1491'];self.assertTrue(smart['offered']['offered_tested_grades']);self.assertEqual(smart['enrolled']['positive_or_protected_tested_grades'],[])
        self.assertFalse(smart['source_profile_eligible']);self.assertEqual(smart['income']['survey_enrollment'],414);self.assertIsNone(smart['campus_assessment_source_row'])
        self.assertEqual(self.document['cohorts']['primary_only']['profiles'],4)
        self.assertEqual(set(self.document['cohorts']['primary_only']['school_ids']),{'16-1981','16-2141','16-2281','16-0261'})
        outside=self.document['outside_roster_profiles'][0]
        self.assertEqual((outside['school_id'],outside['ncessch']),('16-0734',None));self.assertEqual(outside['enrolled']['complete_count_sum'],122)
        self.assertEqual(outside['income']['survey_enrollment'],132)
        self.assertNotIn('16-0734',self.links)
        self.assertEqual(coverage['planningES_outside_prospective'],['120048000704'])
        self.assertEqual(coverage['prospective_not_in_planningES'],[])
        self.assertIn('belowgrade3',audit.POLICY['native_population'])

    def test_precise_own_individual_income_never_uses_funding_or_published_economic_percent(self):
        source={audit.native_identity(e['raw']):e for e in self.inputs['native_income']['records']}
        for link in self.document['roster_links']:
            if not link['native_profile_matched']:continue
            evidence=link['income'];entry=source[link['school_id']];raw=entry['raw']
            self.assertEqual(evidence['source_row'],entry['source_row']);self.assertEqual(evidence['raw'],raw)
            if evidence['percentage']is not None:
                self.assertEqual(evidence['survey_enrollment'],raw[4]);self.assertEqual(evidence['individual_eligible'],raw[5]+raw[6]+raw[8]);self.assertEqual(evidence['percentage'],100*(raw[5]+raw[6]+raw[8])/raw[4]);self.assertEqual(raw[7],0)
        native=next(e for e in self.inputs['native_income']['records']if audit.native_identity(e['raw'])=='16-0121');changed=copy.deepcopy(native)
        baseline=audit.income_evidence(changed)['percentage'];changed['raw'][9:12]=[999999,999999,1.]
        self.assertEqual(audit.income_evidence(changed)['percentage'],baseline)
        for value in [1,'*']:
            altered=copy.deepcopy(native);altered['raw'][7]=value;result=audit.income_evidence(altered)
            self.assertIsNone(result['percentage']);self.assertIn('Provision2',result['exclusion'])
        zero=copy.deepcopy(native);zero['raw'][5:9]=[0,0,0,0]
        self.assertEqual(audit.income_evidence(zero)['percentage'],0.)
        masked=copy.deepcopy(native);masked['raw'][5]='*';self.assertIsNone(audit.income_evidence(masked)['percentage'])
        self.assertEqual((self.document['coverage']['district_ccd_enrollment'],self.document['coverage']['operational_ccd_enrollment_sum'],self.document['coverage']['district_minus_operational_enrollment']),(130054,129932,122))
        self.assertIn('without attributing the cause',audit.POLICY['income_enrollment_discrepancy'])

    def test_original_campus_whole_rates_and_missing_profiles_have_no_validscore_counts_or_intervals(self):
        originals={e['source_row']:e['raw']for e in self.inputs['native_assessment']['records']}
        missing=[]
        for r in self.document['roster_links']:
            for s,index in [('math',9),('reading',6)]:
                value=r['subjects'][s];row=value['source_row']
                if row is not None:
                    self.assertEqual(value['raw_rate'],originals[row][index]);self.assertEqual(value['native_rate'],audit.published_rate(originals[row][index]))
                self.assertTrue(all(value[k]is None for k in ['tested','valid_scores','sampling_variance']))
                self.assertIs(value['ten_valid_scored_floor_certified'],False);self.assertIs(value['sampling_interval_available'],False)
            if r['source_profile_eligible']:
                if r['subjects']['combined']['usable']:
                    self.assertEqual(r['subjects']['combined']['native_rate'],(r['subjects']['math']['native_rate']+r['subjects']['reading']['native_rate'])/2)
                else:missing.append(r['school_id'])
        self.assertEqual(set(missing),{'16-0061','16-0271','16-0281','16-0171'})
        for k in missing:
            self.assertIsNone(self.links[k]['campus_assessment_source_row']);self.assertTrue(self.links[k]['source_profile_eligible'])
        self.assertEqual((self.document['coverage']['provider_assessment_rows'],self.document['coverage']['collocated_assessment_rows'],self.document['coverage']['campus_charter_disagreements']),(0,0,0))
        campus=next(e for e in self.inputs['native_assessment']['records']if audit.native_identity(e['raw'])=='16-0121');income=self.links['16-0121']['income']
        for index,value,term in [(3,'302','Provider-specific'),(47,'Y','Collocated')]:
            row=copy.deepcopy(campus);row['raw'][index]=value
            result=audit.outcome_evidence(row,'math',scope=None,income=income,native_scope=True)
            self.assertFalse(result['usable']);self.assertIn(term,result['exclusion']);self.assertIsNone(result['tested'])

    def test_native_code_count_rate_boolean_float_fraction_and_mask_boundaries(self):
        for value in [True,16.,'DUVAL',-1]:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.native_code(value,2)
        self.assertEqual(audit.native_code(61,4),'0061');self.assertEqual(audit.native_code('0061',4),'0061')
        for value in [False,3.,3.1,'3',-1]:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.native_count(value)
        for value in [False,30.,101,-1,'30']:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.published_rate(value)
        for value in [None,'*','**','N/A']:self.assertIsNone(audit.native_count(value));self.assertIsNone(audit.published_rate(value))
        self.assertEqual(audit.native_count(0),0);self.assertEqual(audit.published_rate(0),0.)
        entry=next(e for e in self.inputs['native_grades']['records']if audit.native_identity(e['raw'])=='16-0121')
        for value in ['*',None,1]:
            r=copy.deepcopy(entry);r['raw'][14]=value;self.assertFalse(audit.enrolled_evidence(r)['native_grade_school_contract'])

    def test_complete_original_snapshots_primary_definition_pages_headers_notes_and_fingerprints(self):
        self.assertEqual(audit.fingerprint(self.inputs),audit.RAW_INPUT_SHA)
        self.assertEqual(audit.identity_fingerprint(self.inputs),audit.ORIGINAL_IDENTITY_SHA)
        self.assertEqual(audit.fingerprint(self.document['policy']),audit.POLICY_SHA)
        self.assertEqual(self.document['state_extract']['sha256'],audit.STATE_EXTRACT_SHA)
        self.assertIn('2024-25, Survey 2',self.inputs['native_grades']['header_rows'][0][0])
        self.assertIn('Final Survey 3',self.inputs['native_income']['header_rows'][0][0])
        self.assertEqual(self.inputs['native_assessment']['header_rows'][3][6],'English Language Arts Achievement')
        self.assertEqual(self.inputs['native_assessment']['header_rows'][3][9],'Mathematics Achievement')
        self.assertEqual(len(self.inputs['definitions']['grade-guide']['original_pages']),12)
        self.assertEqual(len(self.inputs['definitions']['lunch-guide']['original_pages']),3)
        text='\n'.join(e['text']for e in self.inputs['definitions']['lunch-guide']['original_pages'])
        self.assertIn('Codes 6 and 9 should be converted to code C or D',text)
        guide='\n'.join(e['text']for e in self.inputs['definitions']['grade-guide']['original_pages'])
        for term in ['ten (10) students are eligible','Datafolio','home-zoned','two (2) years','valid FAST ELA','Level 3','Algebra 1','Geometry']:self.assertIn(term,guide)

    def test_source_output_scope_approvals_counts_membership_references_and_models_mutations_reject(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d.update(year=2025.),lambda d:d.update(scope='ready'),lambda d:d.update(models=[]),lambda d:d['roster_links'].pop(),lambda d:d['roster_links'][0].update(ncessch='120048099999'),lambda d:d['cohorts']['prospective_tested_grade_profiles']['school_ids'].append('16-0734'),lambda d:d['roster_links'][0]['income'].update(percentage=0.),lambda d:d['roster_links'][0]['subjects']['math'].update(tested=10),lambda d:d['coverage'].update(ten_valid_scored_floor_certified=True),lambda d:d['sources']['assessment'].update(sha256='0'*64),lambda d:d['coverage'].update(prospective_source_profiles=150.)]
        for i,mutate in enumerate(mutations):
            d=copy.deepcopy(self.document);mutate(d)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_repin_raw_semantic_foreign_year_identifiers_header_types_flags_and_definition_omits_reject(self):
        mutations=[lambda x:x['directory']['records'][0]['raw'].update(ST='MD'),lambda x:x['directory']['records'][0]['raw'].update(FIPST='24'),lambda x:x['directory']['records'][0]['raw'].update(STATENAME='MARYLAND'),lambda x:x['directory']['records'][0]['raw'].update(SCHOOL_YEAR='2023-2024'),lambda x:x['directory']['records'][0]['raw'].update(ST_SCHID='FL-15-0061'),lambda x:x['directory']['records'][0]['raw'].update(NCESSCH='240051000978'),lambda x:x['native_grades']['records'][0]['raw'].__setitem__(0,True),lambda x:x['native_income']['records'][0]['raw'].__setitem__(2,61.),lambda x:x['native_grades']['records'][0]['raw'].__setitem__(4,0.),lambda x:x['native_income']['records'][0].update(source_row=1282.),lambda x:x['native_assessment']['records'][0]['raw'].__setitem__(47,'Q'),lambda x:x['native_assessment']['records'][0]['raw'].__setitem__(9,False),lambda x:x['native_income']['header_rows'][2].__setitem__(8,'Funding multiplier numerator'),lambda x:x['native_income']['notes'].clear(),lambda x:x['definitions']['grade-guide']['original_pages'].pop(),lambda x:x['membership']['records'].append(copy.deepcopy(x['membership']['records'][0]))]
        for i,mutate in enumerate(mutations):
            d=copy.deepcopy(self.document);mutate(d['raw_inputs'])
            with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_repin_native_income_and_grade_scope_changes_do_not_get_approved_or_backfilled(self):
        for kind in ['code4','multiplier','highpositive','highmask','allzero','namejoin','badprovider']:
            d=copy.deepcopy(self.document);raw=d['raw_inputs']
            if kind in ['code4','multiplier']:
                e=next(e for e in raw['native_income']['records']if audit.native_identity(e['raw'])=='16-0121');e['raw'][7 if kind=='code4' else 8]=1 if kind=='code4' else e['raw'][10]
            elif kind in ['highpositive','highmask','allzero']:
                e=next(e for e in raw['native_grades']['records']if audit.native_identity(e['raw'])=='16-0121')
                if kind=='allzero':e['raw'][8:14]=[0]*6
                else:e['raw'][14]=1 if kind=='highpositive'else'*'
            elif kind=='namejoin':
                e=next(e for e in raw['native_grades']['records']if audit.native_identity(e['raw'])=='16-0734');e['raw'][2]='1491'
            else:raw['native_assessment']['records'][0]['raw'][3]='302'
            with self.subTest(kind=kind),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(raw)),self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_repin_planning_integer_float_boolean_reference_aliases_and_wrong_cohort_reject(self):
        for field,bad in [('enrollment',130054.),('school_directory_operational_count',203.),('directory_source_row',4004.),('membership_source_row',669548.),('directory_source_row',True),('potential_cohorts',{'ES':151.,'HS':24})]:
            d=copy.deepcopy(self.document);d['raw_inputs']['planning']['record'][field]=bad
            with self.subTest(field=field,bad=bad),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_policy_state_freshness_and_offline_replay_never_fit_import_or_read_original_archives(self):
        with mock.patch.object(audit,'POLICY_SHA','0'*64),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'STATE_SNAPSHOT_SHA','0'*64),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'STATE_EXTRACT_SHA','0'*64),self.assertRaises(ValueError):audit.load_florida()
        with mock.patch.object(audit,'extract_raw_inputs',side_effect=AssertionError('No source extraction')),mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No decompression')),mock.patch.object(audit.florida,'prepare',side_effect=AssertionError('No canonical/model work')):
            self.assertEqual(audit.validate(self.document)['prospective_usable'],{'math':146,'reading':146,'combined':146})
        d=copy.deepcopy(self.snapshot);d['year']=2024
        with self.assertRaises(ValueError):audit.validate(self.document,d)


if __name__=='__main__':unittest.main()

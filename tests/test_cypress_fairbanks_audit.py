import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_cypress_fairbanks as audit


class CypressFairbanksSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text());cls.raw=cls.document['raw_inputs']
        cls.links={r['native_school_id']:r for r in cls.document['roster_links']}
        cls.native={e['raw']['CAMPUS']:e['raw'] for e in cls.raw['stud']['records']}
        cls.assessment={e['raw']['CAMPUS']:e['raw'] for e in cls.raw['assessment']['records']}
        cls.snapshot=audit.load_texas()

    def test_complete_original_scope_false_approvals_and_uncertified_counts(self):
        coverage=audit.validate(self.document,self.snapshot)
        self.assertEqual(coverage['source_rows'],dict(directory=94,membership=720,lea_directory=1,lea_membership=16,ref=92,stud=92,assessment=92))
        self.assertEqual((coverage['original_records'],coverage['original_typed_cells']),(1107,42828))
        self.assertEqual((coverage['directory_records'],coverage['operational_schools'],coverage['native_campuses']),(94,94,92))
        self.assertEqual(coverage['native_scope_counts'],{'grade-school':78,'high':13,'primary-only':1})
        self.assertEqual(coverage['prospective_subject_members'],{'math':78,'reading':78,'combined':78})
        self.assertEqual(coverage['ccd_charter'],{'No':94})
        self.assertEqual(coverage['ccd_school_types'],{'Alternative School':3,'Regular School':91})
        self.assertEqual((self.document['status'],self.document['scope']),('audit_pending','source_cohort_audit_only'))
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        for key in ['models','model_results','residuals','canonical_dataset']:self.assertNotIn(key,self.document)
        self.assertEqual(coverage['verified_valid_score_counts'],0);self.assertFalse(coverage['ten_valid_scored_floor_certified']);self.assertFalse(coverage['sampling_intervals_available'])

    def test_exact_original_crosswalk_no_names_foreign_codes_or_numeric_identity_aliases(self):
        native=self.native['101907041'];ccd=next(e['raw'] for e in self.raw['directory']['records'] if e['raw']['NCESSCH']=='481611001177')
        self.assertEqual(audit.native_identity(dict(native,CAMPNAME='Other name')),'101907041')
        self.assertEqual(audit.ccd_identity(ccd),('481611001177','101907041'))
        for field,bad in [('CAMPUS',101907041),('CAMPUS',101907041.),('CAMPUS',True),('CAMPUS','101908041'),('DISTRICT','101908')]:
            with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):audit.native_identity(dict(native,**{field:bad}))
        for field,bad in [('FIPST','17'),('STATENAME','ILLINOIS'),('ST','IL'),('SCHOOL_YEAR','2023-2024'),('LEAID','4816230'),('ST_SCHID','TX-101907-101908041')]:
            with self.subTest(field=field),self.assertRaises(ValueError):audit.ccd_identity(dict(ccd,**{field:bad}))

    def test_both_operational_alternative_id_gaps_remain_unjoined_and_missing_not_zero(self):
        self.assertEqual(self.document['coverage']['ccd_absent_from_native'],['481611008601','481611012265'])
        for native,ncessch in audit.EXPECTED_NATIVE_GAPS.items():
            link=self.links[native];self.assertEqual(link['school_id'],ncessch)
            self.assertTrue(link['ccd_flags']['operational']);self.assertEqual(link['ccd_flags']['school_type'],'Alternative School')
            self.assertFalse(link['native_present']);self.assertIsNone(link['native_enrolled']);self.assertIsNone(link['native_peims_membership'])
            self.assertIsNone(link['income']['percentage']);self.assertEqual(link['native_source_rows'],{})
            for subject in ['math','reading','combined']:
                self.assertIsNone(link['subjects'][subject]['proficiency']);self.assertIsNone(link['subjects'][subject]['valid_scores']);self.assertFalse(link['subjects'][subject]['source_usable'])
            for table in ['ref','stud','assessment']:self.assertNotIn(native,{e['raw']['CAMPUS'] for e in self.raw[table]['records']})
        self.assertEqual(len(self.document['outside_grade_school_population']),16)

    def test_native_enrolled_grade_counts_define_population_without_reference_labels(self):
        for key,raw in self.native.items():
            evidence=audit.grade_evidence(raw)
            self.assertEqual(evidence,self.links[key]['native_enrolled'])
            self.assertEqual(sum(evidence['counts'].values()),evidence['enrollment'])
        self.assertEqual(self.document['cohorts']['native_no_high_grade_profiles']['profiles'],79)
        self.assertEqual(self.document['cohorts']['primary_only']['native_school_ids'],['101907159'])
        sample=dict(self.native['101907041']);sample['CPNTG09C']='1';sample['CPNTALLC']=str(int(sample['CPNTALLC'])+1)
        self.assertEqual(audit.grade_evidence(sample)['scope'],'mixed')
        sample['CPNTG09C']='-1';self.assertEqual(audit.grade_evidence(sample)['scope'],'unknown')
        self.assertFalse(audit.grade_evidence(sample)['prospective_grade_school'])
        grade_ids=set(self.document['cohorts']['prospective_grade_school']['native_school_ids'])
        self.assertEqual(len(grade_ids),78)
        self.assertTrue(all(self.links[k]['native_enrolled']['high_enrollment']==0 and self.links[k]['native_enrolled']['tested_grades_enrollment']>0 for k in grade_ids))

    def test_precise_own_october_economic_counts_and_distinct_unassigned_membership(self):
        e=self.document['enrollment_reconciliation']
        self.assertEqual([e[k] for k in ['ccd_lea_reported','ccd_operational_school_sum','native_campus_sum']],[117927]*3)
        self.assertEqual((e['native_economic_disadvantage_sum'],e['native_peims_membership_sum']),(69352,117658))
        self.assertEqual(len(e['native_enrollment_membership_differences']),72);self.assertEqual(e['matched_school_enrollment_differences'],[])
        for key,raw in self.native.items():
            income=self.links[key]['income'];n=int(raw['CPNTALLC']);low=int(raw['CPNTECOC'])
            self.assertEqual(income['percentage'],100*low/n)
            self.assertEqual(int(raw['CPNTNEDC'])+low,n)
            self.assertEqual(income['snapshot_date'],'2024-10-25')
            self.assertLessEqual(abs(income['percentage']-float(raw['CPNTECOP'])),.050001)
        zero=dict(self.native['101907041'],CPNTECOC='0',CPNTNEDC=self.native['101907041']['CPNTALLC'],CPNTECOP='0.0')
        self.assertEqual(audit.income_evidence(zero)['percentage'],0.)
        zero['CPNTECOP']='-1';self.assertIsNone(audit.income_evidence(zero)['percentage'])

    def test_original_published_whole_rates_never_count_ratios_or_count_screen(self):
        for key in self.document['cohorts']['prospective_grade_school']['native_school_ids']:
            link=self.links[key];raw=self.assessment[key]
            for subject,fields in audit.FIELDS.items():
                value=link['subjects'][subject]
                self.assertEqual(value['raw'],[raw[field] for field in fields]);self.assertEqual(value['proficiency'],float(raw[fields[2]]))
                self.assertIsNone(value['valid_scores']);self.assertIsNone(value['sampling_variance']);self.assertFalse(value['sampling_interval_available'])
                self.assertFalse(value['ten_valid_scored_floor_certified'])
            self.assertEqual(link['subjects']['combined']['proficiency'],(link['subjects']['math']['proficiency']+link['subjects']['reading']['proficiency'])/2)
        self.assertEqual(self.document['coverage']['grade_school_published_rates_differing_from_unverified_count_ratios'],{'math':78,'reading':78})
        raw=dict(self.assessment['101907041']);fields=audit.FIELDS['math'];raw[fields[0]]='-1';raw[fields[1]]='-1'
        value=audit.subject_evidence(raw,'math',True,{'exclusion':None})
        self.assertTrue(value['source_usable']);self.assertEqual(value['proficiency'],39.)
        raw[fields[0]]='0';raw[fields[1]]='0';raw[fields[2]]='0'
        self.assertTrue(audit.subject_evidence(raw,'math',True,{'exclusion':None})['source_usable'])
        for bad in [False,1.1,-1,'1.1','NaN','-4']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):audit.count(bad)
        self.assertEqual(audit.count('0'),0);self.assertIsNone(audit.count('-1'))

    def test_complete_same_year_primary_definitions_and_strict_source_references(self):
        audit.validate_definition_references(self.raw['definitions'])
        self.assertEqual(sum(len(section.get('pages',[])) for section in self.raw['definitions'].values()),18)
        for subject,fields in audit.FIELDS.items():
            for field in fields:self.assertIn('SY 2024-25',self.raw['assessment']['labels'][self.raw['assessment']['header'].index(field)])
        for kind in ['pdf','worksheet','html']:
            definitions=copy.deepcopy(self.raw['definitions'])
            if kind=='pdf':definitions['glossary']['pages'][0]['pdf_page']=1.
            elif kind=='worksheet':definitions['ccd_state_notes']['worksheets'][0]['rows'][0]['source_row']=True
            else:definitions['masking']['lines'][0]['source_line']=1.
            with self.subTest(kind=kind),self.assertRaises(ValueError):audit.validate_definition_references(definitions)

    def test_source_output_approval_scopes_missingness_and_proxies_reject(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d.update(year=2025.),
            lambda d:d.update(models=[]),lambda d:d['roster_links'].pop(),lambda d:d['coverage'].update(verified_valid_score_counts=78),
            lambda d:d['coverage'].update(ten_valid_scored_floor_certified=True),
            lambda d:next(r for r in d['roster_links'] if r['native_school_id']=='101907006')['income'].update(percentage=0.),
            lambda d:d['cohorts']['prospective_grade_school']['subjects']['combined'].update(approved_for_modeling=True)]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.document);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(changed,self.snapshot)

    def test_repin_raw_unused_numeric_scope_and_source_row_guards(self):
        unused_rate=next(field for field in self.raw['assessment']['header'] if field.endswith('R') and field not in sum(audit.FIELDS.values(),[]))
        mutations=[lambda r:r['directory']['records'][0]['raw'].update(FIPST='17'),
            lambda r:r['stud']['records'][0]['raw'].update(CPNTG09C='1.1'),
            lambda r:r['stud']['records'][0]['raw'].update(CPETECOP='100.1'),
            lambda r:r['assessment']['records'][0]['raw'].__setitem__(unused_rate,'101'),
            lambda r:r['assessment']['records'][0]['raw'].__setitem__(unused_rate,'5.5'),
            lambda r:r['assessment']['records'][0]['raw'].__setitem__('CDA38AM0E025D','-4'),
            lambda r:r['stud']['records'][0].update(source_row=float(r['stud']['records'][0]['source_row'])),
            lambda r:r['planning']['record'].update(directory_source_row=True),
            lambda r:r['planning']['record'].update(membership_source_row=float(r['planning']['record']['membership_source_row']))]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.document);mutate(changed['raw_inputs'])
            with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(changed['raw_inputs'])),self.assertRaises(ValueError):audit.validate(changed,self.snapshot)

    def test_current_source_policy_types_self_repins_and_cached_secondary_source_freshness(self):
        policy=copy.deepcopy(audit.POLICY);policy['counts']='Treat native #Tests as certified valid scores'
        for field,value in [('POLICY',policy),('YEAR',2025),('LEA','4816230'),('OPERATIONAL',{'1'}),('EXPECTED_NATIVE_GAPS',{}),('STATE_EXTRACT_SHA','0'*64)]:
            with self.subTest(field=field),mock.patch.object(audit,field,value),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'POLICY',policy),mock.patch.object(audit,'POLICY_SHA',audit.fingerprint(policy)),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'YEAR',2025):
            repin=audit.fingerprint(audit.runtime_contract())
            with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',repin),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        original=Path.read_bytes;target=ROOT/'data/source/texas.json'
        def changed(path):return b'changed' if path==target else original(path)
        with mock.patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        def missing(path):
            if path==target:raise FileNotFoundError('Missing frozen secondary source')
            return original(path)
        with mock.patch.object(Path,'read_bytes',missing),self.assertRaises(FileNotFoundError):audit.validate(self.document,self.snapshot)

    def test_repin_selected_headers_cannot_change_subject_population_or_count_rate_role(self):
        field='CDA38AM0E225R';original=audit.NATIVE_REQUIRED_LABELS['assessment'][field]
        alternatives=[audit.NATIVE_REQUIRED_LABELS['assessment']['CDA38AR0E225R'],
            original.replace('All Students','Economically Disadvantaged'),
            audit.NATIVE_REQUIRED_LABELS['assessment']['CDA38AM0E025D']]
        for label in alternatives:
            changed=copy.deepcopy(self.document);section=changed['raw_inputs']['assessment']
            section['labels'][section['header'].index(field)]=label
            schema={k:{name:v[name] for name in ['source_id','header','labels','member','header_source_row','labels_source_row','codes_source_row'] if name in v}
                for k,v in changed['raw_inputs'].items() if k in {'directory','membership','lea_directory','lea_membership','ref','stud','assessment'}}
            with self.subTest(label=label),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(changed['raw_inputs'])),mock.patch.object(audit,'ORIGINAL_SCHEMA_SHA',audit.fingerprint(schema)),self.assertRaisesRegex(ValueError,'label changed'):
                audit.validate(changed,self.snapshot)


if __name__=='__main__':unittest.main()

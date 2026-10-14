"""Northside original-source membership and strict preservation contracts, without fits."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_northside as audit


class NorthsideSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text());cls.raw=cls.document['raw_inputs']
        cls.links={r['native_school_id']:r for r in cls.document['roster_links']}
        cls.native={e['raw']['CAMPUS']:e['raw']for e in cls.raw['stud']['records']}
        cls.assessments={e['raw']['CAMPUS']:e['raw']for e in cls.raw['assessment']['records']}
        cls.snapshot=audit.load_texas()

    def test_complete_source_cohort_and_false_approvals(self):
        c=audit.validate(self.document,self.snapshot)
        self.assertEqual(c['source_rows'],dict(directory=131,membership=1014,lea_directory=1,lea_membership=16,ref=127,stud=127,assessment=127))
        self.assertEqual((c['original_records'],c['original_typed_cells']),(1543,59450))
        self.assertEqual((c['directory_records'],c['operational_schools'],c['native_campuses']),(131,128,127))
        self.assertEqual(c['native_scope_counts'],{'grade-school':107,'high':16,'mixed':3,'primary-only':1})
        self.assertEqual(c['prospective_subject_members'],{'math':104,'reading':104,'combined':104})
        self.assertEqual(c['ccd_school_types'],{'Regular School':118,'Alternative School':13});self.assertEqual(c['ccd_charter'],{'No':131})
        self.assertEqual(c['positive_enrolled_grades_not_offered'],[])
        for flag in ['approved_for_source','approved_for_modeling']:self.assertIs(self.document[flag],False)
        for key in ['models','residuals','canonical_dataset']:self.assertNotIn(key,self.document)
        self.assertEqual(c['verified_valid_score_counts'],0);self.assertIs(c['ten_valid_scored_floor_certified'],False)
        self.assertIs(c['sampling_intervals_available'],False);self.assertIs(c['canonical_import_performed'],False)

    def test_complete_original_omitted_inventory_and_ordinal_bindings(self):
        school=self.raw['membership']['complete_district_inventory'];lea=self.raw['lea_membership']['complete_district_inventory']
        self.assertEqual((school['original_district_rows'],school['retained_rows'],school['omitted_rows'],school['omitted_typed_cells']),(14560,1014,13546,243828))
        self.assertEqual((lea['original_district_rows'],lea['retained_rows'],lea['omitted_rows'],lea['omitted_typed_cells']),(243,16,227,3405))
        for key in audit.ORIGINAL_INVENTORIES:
            block=self.raw[key];inventory=block['complete_district_inventory'];ordinals=inventory['omitted_source_ordinals']
            self.assertEqual(len(ordinals),inventory['omitted_rows']);self.assertEqual(len(set(ordinals)),len(ordinals))
            self.assertEqual(ordinals,[r['source_row']for r in inventory['omitted_identity_population_inventory']])
            self.assertTrue(all(type(i)is int and i>=2 for i in ordinals))
            self.assertFalse(set(ordinals)&{e['source_row']for e in block['records']})
            self.assertEqual(audit.fingerprint({k:v for k,v in block.items()if k!='records'}),audit.ORIGINAL_METADATA[key])
        changed=copy.deepcopy(self.document);changed['raw_inputs']['membership']['complete_district_inventory']['omitted_identity_population_inventory'][0]['identity_population']['LEAID']='4816110'
        with self.assertRaises(ValueError):audit.validate(changed,self.snapshot)

    def test_exact_full_ids_leading_zeroes_and_no_name_join(self):
        native=self.native['015915001'];ccd=next(e['raw']for e in self.raw['directory']['records']if e['raw']['ST_SCHID']=='TX-015915-015915001')
        self.assertEqual(audit.native_identity(dict(native,CAMPNAME='A different name')),'015915001')
        self.assertEqual(audit.ccd_identity(ccd),(ccd['NCESSCH'],'015915001'))
        for field,value in [('CAMPUS',15915001),('CAMPUS',15915001.),('CAMPUS',True),('CAMPUS','15915001'),('CAMPUS','101907001'),('DISTRICT','15915'),('DISTRICT','015916')]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):audit.native_identity(dict(native,**{field:value}))
        for field,value in [('FIPST','17'),('STATENAME','ILLINOIS'),('ST','IL'),('SCHOOL_YEAR','2023-2024'),('LEAID','4816110'),('ST_LEAID','TX-015916'),('ST_SCHID','TX-015915-15915001'),('NCESSCH',int(ccd['NCESSCH']))]:
            with self.subTest(field=field),self.assertRaises(ValueError):audit.ccd_identity(dict(ccd,**{field:value}))

    def test_operational_missing_native_and_inactive_rows_remain_unjoined(self):
        self.assertEqual(audit.EXPECTED_NATIVE_GAPS,{'015915133':'483312005564'})
        gap=self.links['015915133'];self.assertEqual((gap['name'],gap['school_id']),('HOMEBOUND','483312005564'))
        self.assertTrue(gap['ccd_flags']['operational']);self.assertFalse(gap['native_present'])
        self.assertIsNone(gap['native_enrolled']);self.assertIsNone(gap['native_peims_membership']);self.assertIsNone(gap['income']['percentage'])
        for subject in ['math','reading','combined']:
            self.assertIsNone(gap['subjects'][subject]['proficiency']);self.assertIsNone(gap['subjects'][subject]['valid_scores']);self.assertFalse(gap['subjects'][subject]['source_usable'])
        self.assertEqual({r['native_school_id']for r in self.document['coverage']['nonoperational_identities']},{'015915250','015915203','015915205'})
        for native in ['015915250','015915203','015915205']:
            r=self.links[native];self.assertFalse(r['ccd_flags']['operational']);self.assertFalse(r['native_present'])
            self.assertIsNone(r['income']['percentage']);self.assertIsNone(r['subjects']['combined']['proficiency'])
        self.assertEqual(len(self.document['outside_grade_school_population']),24)

    def test_grade_population_uses_full_enrolled_counts_and_retains_primary_and_mixed(self):
        for native,raw in self.native.items():
            grade=audit.grade_evidence(raw);self.assertEqual(grade,self.links[native]['native_enrolled'])
            self.assertEqual(sum(grade['counts'].values()),grade['enrollment'])
        self.assertEqual(self.document['cohorts']['native_no_high_grade_profiles']['profiles'],108)
        self.assertEqual(self.document['cohorts']['primary_only']['native_school_ids'],['015915667'])
        self.assertEqual(self.native['015915667']['CPNTALLC'],'45')
        self.assertEqual(set(self.document['cohorts']['mixed_grade']['native_school_ids']),{'015915004','015915013','015915039'})
        sample=dict(self.native['015915043']);sample['CPNTG09C']='1';sample['CPNTALLC']=str(int(sample['CPNTALLC'])+1)
        self.assertEqual(audit.grade_evidence(sample)['scope'],'mixed')
        sample['CPNTG09C']='-1';self.assertEqual(audit.grade_evidence(sample)['scope'],'unknown');self.assertFalse(audit.grade_evidence(sample)['prospective_grade_school'])
        sample=dict(self.native['015915043']);sample['CPNTG03C']=str(int(sample['CPNTG03C'])+1)
        with self.assertRaises(ValueError):audit.grade_evidence(sample)
        members=self.document['cohorts']['prospective_grade_school']['native_school_ids'];self.assertEqual(len(members),107)
        self.assertTrue(all(self.links[k]['native_enrolled']['high_enrollment']==0 and self.links[k]['native_enrolled']['tested_grades_enrollment']>0 for k in members))

    def test_masks_preserved_without_excluding_alternatives_from_source_profiles(self):
        cohort=self.document['cohorts']['prospective_grade_school'];masked={'015915061','015915062','015915172'}
        self.assertEqual(cohort['ccd_school_type'],{'Alternative School':3,'Regular School':104})
        self.assertTrue(masked<=set(cohort['native_school_ids']))
        for subject in ['math','reading','combined']:
            self.assertEqual(cohort['subjects'][subject]['ccd_school_type'],{'Regular School':104})
            self.assertEqual(set(cohort['native_school_ids'])-set(cohort['subjects'][subject]['prospective_native_school_ids']),masked)
            for native in masked:
                entry=self.links[native]['subjects'][subject];self.assertTrue(entry['applicable']);self.assertFalse(entry['source_usable']);self.assertIsNone(entry['proficiency'])
        for native in masked:
            self.assertEqual(self.links[native]['income']['percentage'],100*int(self.native[native]['CPNTECOC'])/int(self.native[native]['CPNTALLC']))

    def test_individual_same_year_income_and_distinct_unassigned_membership(self):
        e=self.document['enrollment_reconciliation']
        self.assertEqual([e[k]for k in ['ccd_lea_reported','ccd_operational_school_sum','native_campus_sum']],[100208]*3)
        self.assertEqual((e['native_peims_membership_sum'],e['native_economic_disadvantage_sum']),(99729,49854))
        self.assertEqual(len(e['native_enrollment_membership_differences']),72);self.assertEqual(e['matched_school_enrollment_differences'],[])
        for native,raw in self.native.items():
            income=self.links[native]['income'];total=int(raw['CPNTALLC']);low=int(raw['CPNTECOC'])
            self.assertEqual(low+int(raw['CPNTNEDC']),total);self.assertEqual(income['percentage'],100*low/total)
            self.assertEqual(income['snapshot_date'],'2024-10-25');self.assertLessEqual(abs(income['percentage']-float(raw['CPNTECOP'])),.050001)
        sample=dict(self.native['015915043']);sample.update(CPNTECOC='0',CPNTNEDC=sample['CPNTALLC'],CPNTECOP='0.0')
        self.assertEqual(audit.income_evidence(sample)['percentage'],0.)
        sample['CPNTECOP']='-1';self.assertIsNone(audit.income_evidence(sample)['percentage'])
        sample['CPNTECOP']='101';self.assertRaises(ValueError,audit.income_evidence,sample)

    def test_whole_published_rates_and_combined_never_unverified_ratios(self):
        for native in self.document['cohorts']['prospective_grade_school']['subjects']['combined']['prospective_native_school_ids']:
            row=self.links[native];raw=self.assessments[native]
            for subject,fields in audit.FIELDS.items():
                v=row['subjects'][subject];self.assertEqual(v['raw'],[raw[f]for f in fields]);self.assertEqual(v['proficiency'],float(raw[fields[2]]))
                self.assertIsNone(v['valid_scores']);self.assertIsNone(v['sampling_variance']);self.assertFalse(v['sampling_interval_available']);self.assertFalse(v['ten_valid_scored_floor_certified'])
            self.assertEqual(row['subjects']['combined']['proficiency'],(row['subjects']['math']['proficiency']+row['subjects']['reading']['proficiency'])/2)
        self.assertEqual(self.document['coverage']['grade_school_published_rates_differing_from_unverified_count_ratios'],{'math':103,'reading':103})
        sample=dict(self.assessments['015915043']);fields=audit.FIELDS['math'];original=float(sample[fields[2]])
        sample[fields[0]]='-1';sample[fields[1]]='-1'
        v=audit.subject_evidence(sample,'math',True,{'exclusion':None});self.assertTrue(v['source_usable']);self.assertEqual(v['proficiency'],original)
        sample[fields[0]]=sample[fields[1]]=sample[fields[2]]='0';self.assertTrue(audit.subject_evidence(sample,'math',True,{'exclusion':None})['source_usable'])
        sample[fields[2]]='-1';self.assertIsNone(audit.subject_evidence(sample,'math',True,{'exclusion':None})['proficiency'])

    def test_native_scalar_types_precision_suppression_and_arithmetic(self):
        for raw in ['', '-1','-2','-3','*','**','•']:self.assertIsNone(audit.number(raw));self.assertIsNone(audit.count(raw))
        self.assertEqual(audit.count('0'),0)
        for value in [False,1.1,-1,'1.1','NaN','Inf','-4']:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.count(value)
        for field,value in [('CPNTG09C','1.1'),('CPETECOP','100.1'),('CPNTECOP','3.55')]:
            with self.subTest(field=field),self.assertRaises(ValueError):audit.validate_native_numeric_cells('stud',dict(self.native['015915043'],**{field:value}))
        unused=next(f for f in self.raw['assessment']['header']if f.endswith('R')and f not in sum(audit.FIELDS.values(),[]))
        for value in ['101','5.5']:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.validate_native_numeric_cells('assessment',dict(self.assessments['015915043'],**{unused:value}))

    def test_primary_definitions_strict_page_row_line_references(self):
        definitions=self.raw['definitions'];audit.validate_definition_references(definitions)
        self.assertEqual(sum(len(v.get('pages',[]))for v in definitions.values()),18)
        self.assertEqual(len(audit.SOURCES),15)
        for kind in ['pdf','worksheet','html']:
            altered=copy.deepcopy(definitions)
            if kind=='pdf':altered['glossary']['pages'][0]['pdf_page']=1.
            elif kind=='worksheet':altered['ccd_state_notes']['worksheets'][0]['rows'][0]['source_row']=True
            else:altered['masking']['lines'][0]['source_line']=1.
            with self.subTest(kind=kind),self.assertRaises(ValueError):audit.validate_definition_references(altered)

    def test_derived_output_and_approval_cannot_self_authorize(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d.update(year=2025.),lambda d:d.update(models=[]),lambda d:d['roster_links'].pop(),lambda d:d['coverage'].update(verified_valid_score_counts=104),lambda d:d['coverage'].update(ten_valid_scored_floor_certified=True),lambda d:next(r for r in d['roster_links']if r['native_school_id']=='015915133')['income'].update(percentage=0.),lambda d:d['cohorts']['prospective_grade_school']['subjects']['combined'].update(approved_for_modeling=True)]
        for i,change in enumerate(mutations):
            altered=copy.deepcopy(self.document);change(altered)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(altered,self.snapshot)

    def test_all_four_public_fingerprint_repins_and_runtime_seals_reject(self):
        altered=copy.deepcopy(self.document);altered['raw_inputs']['stud']['records'][0]['raw']['CPNTECOC']='1'
        fingerprints={'RAW_INPUT_SHA':audit.fingerprint(altered['raw_inputs']),'ORIGINAL_SCHEMA_SHA':'0'*64,'DEFINITION_INPUT_SHA':'1'*64,'ORIGINAL_IDENTITY_SHA':'2'*64}
        for name,value in fingerprints.items():
            with self.subTest(name=name),mock.patch.object(audit,name,value):
                runtime=audit.fingerprint(audit.runtime_contract())
                with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',runtime),self.assertRaises(ValueError):audit.validate(altered,self.snapshot)
        policy=copy.deepcopy(audit.POLICY);policy['counts']='Treat all reported #Tests as certified valid scores'
        with mock.patch.object(audit,'POLICY',policy),mock.patch.object(audit,'POLICY_SHA',audit.fingerprint(policy)):
            with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        for name,value in [('LEA','4816110'),('YEAR',2025),('DISTRICT','15915'),('EXPECTED_NATIVE_GAPS',{}),('OPERATIONAL',{'1'}),('FIELDS',{'math':audit.FIELDS['reading'],'reading':audit.FIELDS['math']})]:
            with self.subTest(name=name),mock.patch.object(audit,name,value),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)

    def test_header_and_omitted_inventory_coherent_public_repins_reject(self):
        for change in ['subject','population','rate-role','omitted','ordinal']:
            altered=copy.deepcopy(self.document);r=altered['raw_inputs'];section=r['assessment'];field='CDA38AM0E225R';index=section['header'].index(field)
            if change=='subject':section['labels'][index]=audit.NATIVE_REQUIRED_LABELS['assessment']['CDA38AR0E225R']
            elif change=='population':section['labels'][index]=section['labels'][index].replace('All Students','Economically Disadvantaged')
            elif change=='rate-role':section['labels'][index]=audit.NATIVE_REQUIRED_LABELS['assessment']['CDA38AM0E025D']
            elif change=='omitted':r['membership']['complete_district_inventory']['omitted_source_ordinals'].pop()
            else:r['stud']['records'][0]['source_row']=float(r['stud']['records'][0]['source_row'])
            metadata={k:{f:v for f,v in r[k].items()if f!='records'}for k in audit.ORIGINAL_INVENTORIES}
            with self.subTest(change=change),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(r)),mock.patch.object(audit,'ORIGINAL_SCHEMA_SHA',audit.fingerprint(metadata)),mock.patch.object(audit,'ORIGINAL_METADATA',{k:audit.fingerprint(v)for k,v in metadata.items()}):
                with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())),self.assertRaises(ValueError):audit.validate(altered,self.snapshot)

    def test_cached_paths_still_check_current_whole_primary_and_secondary_sources(self):
        target=ROOT/audit.SOURCES['ref']['path'];original_open=Path.open;data=target.read_bytes();changed=bytes([data[0]^1])+data[1:]
        def changed_primary(path,*args,**kwargs):return io.BytesIO(changed)if path==target and args and args[0]=='rb'else original_open(path,*args,**kwargs)
        with mock.patch.object(Path,'open',changed_primary),self.assertRaisesRegex(ValueError,'current original fingerprint'):audit.validate(self.document,self.snapshot)
        def missing_primary(path,*args,**kwargs):
            if path==target:raise FileNotFoundError('Frozen original missing')
            return original_open(path,*args,**kwargs)
        with mock.patch.object(Path,'open',missing_primary),self.assertRaises(FileNotFoundError):audit.validate(self.document,self.snapshot)
        secondary=ROOT/'data/source/texas.json';original_read=Path.read_bytes
        def changed_secondary(path):return b'changed'if path==secondary else original_read(path)
        with mock.patch.object(Path,'read_bytes',changed_secondary),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        altered=copy.deepcopy(self.snapshot);altered['academic_year']='2023-24'
        with self.assertRaises(ValueError):audit.validate(self.document,altered)


if __name__=='__main__':unittest.main()

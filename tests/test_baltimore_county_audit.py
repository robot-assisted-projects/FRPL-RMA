"""Baltimore County original source/cohort contracts; no modeling or database writes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_baltimore_county as audit


class BaltimoreCountySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.snapshot=audit.load_maryland()
        cls.inputs=cls.document['raw_inputs']
        cls.links={e['school_id']:e for e in cls.document['roster_links']}
        cls.directory={audit.native_identity(e['raw']):e for e in cls.inputs['native_directory']['records']}
        cls.ccd={e['raw']['NCESSCH']:e for e in cls.inputs['directory']['records']}

    def income(self,key='03-0101'):
        return[e for e in self.inputs['native_income']['records'] if audit.native_identity(e['raw'],income=True,aggregate=True)==key]

    def grades(self,key='03-0101'):
        return[e['raw']for e in self.inputs['native_enrollment']['records']if audit.native_identity(e['raw'],aggregate=True)==key]

    def outcome(self,key='03-0101',subject='math'):
        label='Mathematics All Grades'if subject=='math'else'English Language Arts All Grades'
        return next(e for e in self.inputs['native_assessment']['records']if e['worksheet']=='School_Level'and audit.native_identity(e['raw'],aggregate=True)==key and e['raw']['Assessment'].strip()==label)

    def reject(self,change,repin=False):
        d=copy.deepcopy(self.document);change(d)
        if repin:
            with mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),self.assertRaises(ValueError):audit.validate(d,self.snapshot)
        else:
            with self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_complete_original_counts_types_and_two_directory_views(self):
        c=audit.validate(self.document,self.snapshot)
        self.assertEqual((c['ccd_directory'],c['native_directory'],c['operational_roster'],c['matched_operational_native_profiles']),(180,178,178,178))
        self.assertEqual((c['prospective_source_profiles'],c['prospective_usable_income']),(137,137))
        self.assertEqual(c['prospective_usable'],{'math':126,'reading':137,'combined':126})
        self.assertEqual(sum(audit.ORIGINAL_INVENTORIES.values()),4536)
        self.assertEqual(sum(len(e['raw'])for t in audit.TABLES for e in self.inputs[t]['records']),75620)
        self.assertEqual(len(self.document['unmatched_native_directory']),0)
        self.assertEqual(len(self.document['unmatched_ccd_directory']),2)
        self.assertEqual(len(self.document['nonoperational_directory']),2)
        self.assertEqual({e['raw']['ST_SCHID']for e in self.document['nonoperational_directory']},{'MD-03-030058','MD-03-031451'})
        self.assertEqual({e['raw']['UPDATED_STATUS_TEXT']for e in self.document['nonoperational_directory']},{'Closed'})
        for t in audit.TABLES:
            table=self.inputs[t]
            self.assertEqual(table['header'],audit.ORIGINAL_HEADERS[t])
            self.assertIs(type(table['header_source_row']),int)
            for e in table['records']:
                self.assertIs(type(e['source_row']),int)
                self.assertEqual(set(e['raw']),set(table['header']))
        self.assertEqual(audit.identity_fingerprint(self.inputs),audit.ORIGINAL_IDENTITY_SHA)

    def test_compacted_unused_records_keep_exact_original_inventories(self):
        expected={'membership':(20086,1400,18686,336348),'lea_membership':(243,16,227,3405)}
        for name,counts in expected.items():
            inv=self.inputs[name]['complete_district_inventory']
            self.assertEqual(tuple(inv[k]for k in['original_district_rows','retained_rows','omitted_rows','omitted_typed_cells']),counts)
            rows=inv['omitted_source_rows'];self.assertEqual(len(rows),counts[2]);self.assertEqual(len(set(rows)),counts[2])
            self.assertTrue(all(type(x)is int and x>1 for x in rows));self.assertEqual(len(inv['omitted_raw_sha256']),64)
            self.assertFalse(set(rows)&{e['source_row']for e in self.inputs[name]['records']})
        inv=self.inputs['native_assessment']['complete_district_inventory']
        self.assertEqual(sum(x['omitted_rows']for x in inv),468)
        self.assertEqual(sum(x['omitted_typed_cells']for x in inv),7020)
        self.assertTrue(all(x['omitted_rows']==len(x['omitted_source_rows'])for x in inv))
        self.assertEqual([x['omitted_rows']for x in inv if x['worksheet']=='School_Level'],[0,0])
        self.reject(lambda d:d['raw_inputs']['membership']['complete_district_inventory']['omitted_source_rows'].pop(),repin=True)

    def test_exact_native_nces_and_same_year_foreign_typing_rejected(self):
        for key,link in self.links.items():
            r=self.directory[key]['raw'];ccd=self.ccd[link['ncessch']]['raw']
            self.assertEqual(str(r['NCES Number']),link['ncessch']);self.assertEqual(ccd['ST_SCHID'],link['native_school_id'])
            self.assertEqual(audit.ccd_identity(ccd,directory=True),link['ncessch'])
        raw=self.directory['03-0101']['raw'];ccd=self.ccd['240012000353']['raw']
        for field,value in[('LEA','16'),('School','101'),('School','A'),('Year',2024),('Year',2025.),('Year',True)]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):audit.native_identity(dict(raw,**{field:value}))
        for field,value in[('LEAID','2400510'),('ST_LEAID','MD-16'),('SCHOOL_YEAR','2023-2024'),('ST','DE'),('NCESSCH','240051000353'),('ST_SCHID','MD-16-030101'),('UPDATED_STATUS','9')]:
            with self.subTest(field=field),self.assertRaises(ValueError):audit.ccd_identity(dict(ccd,**{field:value}),directory=True)
        for field,value in[('LEA Number','16'),('School Number','101'),('Academic Year','2024')]:
            with self.subTest(field=field),self.assertRaises(ValueError):audit.native_identity(dict(self.income()[0]['raw'],**{field:value}),income=True)

    def test_positive_lower_grade_configuration_and_protected_boundaries(self):
        profile=self.directory['03-0101']['raw'];ccd=self.ccd['240012000353']['raw'];grades=self.grades()
        self.assertTrue(audit.grade_school_contract(profile,ccd,grades))
        for field,value in[('IGOFFERED','Adjusted'),('G_3_OFFERED','Unknown'),('G_9_OFFERED','Yes'),('G_13_OFFERED','Yes'),('G_UG_OFFERED','Yes'),('G_AE_OFFERED','Yes'),('UPDATED_STATUS','2'),('GSHI','12')]:
            with self.subTest(field=field):self.assertFalse(audit.grade_school_contract(profile,dict(ccd,**{field:value}),grades))
        for span in['H','EH','EMH',None]:self.assertFalse(audit.grade_school_contract(dict(profile,**{'Grade Span':span}),ccd,grades))
        for token in['0','*']:
            self.assertFalse(audit.grade_school_contract(profile,ccd,[dict(r,**{'Enrolled Count':token})for r in grades]))
        for label,count in[('Grade 9','0'),('Grade 9','*'),('Ungraded','1'),('Unknown','1')]:
            self.assertFalse(audit.grade_school_contract(profile,ccd,grades+[dict(grades[0],Grade=label,**{'Enrolled Count':count})]))
        self.assertFalse(audit.grade_school_contract(profile,ccd,[]))
        self.assertTrue(audit.grade_school_contract(profile,dict(ccd,CHARTER_TEXT='Yes',SCH_TYPE_TEXT='Alternative School'),grades))
        self.assertEqual(self.document['coverage']['offered_bands'],{'grade':139,'high':32,'mixed':5,'primary':1,'unknown':1})
        for key in['03-0051','03-0057','03-0062','03-0077']:self.assertFalse(self.links[key]['source_profile_eligible'])
        self.assertEqual([x['school_id']for x in self.links.values()if x['source_profile_eligible']and x['ccd_flags']['school_type']=='Alternative School'],['03-0070','03-0075'])

    def test_income_is_own_individual_early_attendance_not_farms_or_enrollment(self):
        e=audit.income_evidence(self.income());self.assertEqual((e['individual_low_income_count'],e['early_attendance_enrollment']),(334,661));self.assertEqual(e['percentage'],100*334/661)
        for field,value in[('Total Student Cnt','1000'),('Economically Disadvantaged Cnt','662'),('Economically Disadvantaged Pct','99.9')]:
            changed=copy.deepcopy(self.income());changed[0]['raw'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.income_evidence(changed)
        changed=copy.deepcopy(self.income());changed[0]['raw'].update({'FARMS Cnt':'600','FARMS Pct':'90.8'})
        self.assertEqual(audit.income_evidence(changed)['percentage'],e['percentage'])
        for link in self.links.values():
            v=link['income']
            if v['percentage']is not None:
                self.assertEqual(v['percentage'],100*v['individual_low_income_count']/v['early_attendance_enrollment']);self.assertLessEqual(abs(v['published_rounding_error']),.0500001)

    def test_income_whole_all_band_masks_zero_hundred_and_missing(self):
        entries=self.income('03-1253');v=audit.income_evidence(entries)
        self.assertEqual(v['selected_school_type'],'All');self.assertEqual((v['individual_low_income_count'],v['early_attendance_enrollment']),(737,1025))
        self.assertIsNone(audit.income_evidence([e for e in entries if e['raw']['School Type']!='All'])['percentage'])
        with self.assertRaises(ValueError):audit.income_evidence(entries+entries)
        for token in['<= 5.0','>= 95.0','*','','5-10']:
            changed=copy.deepcopy(self.income());changed[0]['raw'].update({'Economically Disadvantaged Pct':token,'Economically Disadvantaged Cnt':'*'})
            self.assertIsNone(audit.income_evidence(changed)['percentage'])
        for token,count in[('0','0'),('100','661')]:
            changed=copy.deepcopy(self.income());changed[0]['raw'].update({'Economically Disadvantaged Pct':token,'Economically Disadvantaged Cnt':count})
            self.assertEqual(audit.income_evidence(changed)['percentage'],float(token))
        self.assertIsNone(audit.income_evidence([])['percentage'])

    def test_native_regular_all_grades_outcome_and_course_scope(self):
        entry=self.outcome();link=self.links['03-0101'];v=audit.outcome_evidence(entry,'math',scope=True,income=link['income'])
        self.assertEqual(v['native_rate'],float(entry['raw']['Proficient Pct']))
        for field,value in[('Assessment','Mathematics 03'),('Student Group','Economically Disadvantaged'),('Year',2024),('LEA','16'),('School','A'),('Proficient Pct','99.9')]:
            changed=copy.deepcopy(entry);changed['raw'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.outcome_evidence(changed,'math',scope=True,income=link['income'])
        for field,value in[('worksheet','LEA_Level'),('member','2025 MCAP ELA Administrative Data Report Card.xlsx')]:
            changed=copy.deepcopy(entry);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.outcome_evidence(changed,'math',scope=True,income=link['income'])
        c=self.document['coverage'];self.assertEqual(c['eligible_course_row_presence'],{'Algebra 1':30,'Algebra 2':7,'Geometry':28})
        self.assertEqual(c['eligible_course_rows_numeric_administrative_count'],{'Algebra 1':27,'Algebra 2':1,'Geometry':27})
        self.assertEqual(c['eligible_administrative_math_component_counts_reconciled'],128)
        self.assertEqual(c['outside_native_records'],{'native_enrollment':18,'native_income':4,'native_assessment':24})

    def test_eleven_math_masks_no_zero_or_count_floor_or_interval_promotion(self):
        profiles=[l for l in self.links.values()if l['source_profile_eligible']];missing=[l for l in profiles if not l['subjects']['math']['usable']]
        self.assertEqual(len(missing),11);self.assertTrue(all(l['subjects']['math']['raw_rate']=='<= 5.0'for l in missing))
        self.assertTrue(all(l['subjects']['reading']['usable']for l in profiles));self.assertTrue(all(not l['subjects']['combined']['usable']for l in missing))
        for l in profiles:
            for subject in['math','reading']:
                v=l['subjects'][subject]
                self.assertIsNone(v['tested']);self.assertIsNone(v['valid_scores']);self.assertIsNone(v['sampling_variance']);self.assertIs(v['ten_valid_scored_floor_certified'],False)
            if l['subjects']['combined']['usable']:self.assertEqual(l['subjects']['combined']['native_rate'],(l['subjects']['math']['native_rate']+l['subjects']['reading']['native_rate'])/2)
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)

    def test_unassigned_school_and_district_enrollment_and_income_differences(self):
        c=self.document['coverage'];self.assertEqual((c['district_fall_membership'],c['operational_school_fall_sum'],c['district_september_enrollment']),(110024,110024,110024))
        self.assertEqual(c['native_september_school_total_sum'],110015);self.assertEqual(c['district_early_attendance_income']['early_attendance_enrollment'],110382)
        self.assertEqual(c['district_early_attendance_income']['individual_low_income_count'],62860)
        self.assertEqual(c['known_school_early_attendance_enrollment_sum'],110357);self.assertEqual(c['district_minus_known_school_early_attendance_enrollment'],25)
        self.assertEqual(c['missing_school_early_attendance_denominator_ids'],['03-0051','03-0052','03-0053','03-0055','03-0056','03-0057','03-0903','03-1274'])
        self.assertEqual(c['suppressed_native_enrollment_cells'],58);self.assertEqual(c['schools_with_early_attendance_ccd_difference'],160)
        self.assertTrue(all(self.links[k]['income']['percentage']is None for k in c['missing_school_early_attendance_denominator_ids']))

    def test_primary_definitions_waiver_threshold_and_unknown_count_scope(self):
        defs=self.inputs['definitions'];pdf=defs['msde_mcap_overview']
        self.assertEqual(pdf['source_pages'],[1,2]);self.assertEqual(len(pdf['original_pages']),2)
        self.assertIn('2027',pdf['original_pages'][1]['text']);self.assertIn('2024',pdf['original_pages'][1]['text'])
        self.assertEqual([e['source_line']for e in defs['msde_reportcard']['original_lines']],[1612,1616])
        self.assertIn('Medicaid',defs['msde_definitions']['plain_text']);self.assertIn('2026',defs['msde_definitions']['raw_markup'])
        self.assertIn('Alternate DLM',audit.POLICY['assessment']);self.assertIs(self.document['coverage']['ten_valid_scored_floor_certified'],False)
        self.assertEqual(len(self.document['sources']),11)

    def test_offline_replay_never_opens_archives_workbooks_database(self):
        with mock.patch.object(audit.zipfile,'ZipFile',side_effect=AssertionError('No ZIP')),mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No archive stream')),mock.patch.object(audit.openpyxl,'load_workbook',side_effect=AssertionError('No workbook')):
            self.assertEqual(audit.validate(self.document)['prospective_source_profiles'],137)

    def test_ordinary_source_derived_policy_and_approval_corruption_rejects(self):
        changes=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d.update(year=2025.),lambda d:d.update(models=[]),
            lambda d:d['raw_inputs']['directory']['header'].pop(),lambda d:d['raw_inputs']['native_directory']['records'].pop(),lambda d:d['sources']['msde_income'].update(sha256='0'*64),
            lambda d:d['raw_inputs']['native_income']['records'][0]['raw'].update({'Economically Disadvantaged Pct':'0'}),lambda d:d['raw_inputs']['native_assessment']['records'][0].update(source_row=1),
            lambda d:d['roster_links'][0]['subjects']['math'].update(valid_scores=100),lambda d:d['coverage'].update(district_minus_known_school_early_attendance_enrollment=0),
            lambda d:d['raw_inputs']['definitions']['msde_mcap_overview'].update(paraphrase='Changed')]
        for i,change in enumerate(changes):
            with self.subTest(i=i):self.reject(change)

    def test_four_original_hashes_and_public_runtime_resigning_cannot_authorize_drift(self):
        changes=[lambda d:d['raw_inputs']['directory']['records'][0]['raw'].update(WEBSITE='https://forged.invalid'),
            lambda d:d['raw_inputs']['native_directory']['records'][0]['raw'].update({'NCES Number':240012099999}),
            lambda d:d['raw_inputs']['definitions']['msde_mcap_overview']['original_pages'][0].update(text='Forged definition'),
            lambda d:d['raw_inputs']['membership']['complete_district_inventory']['omitted_source_rows'].pop(),
            lambda d:d['raw_inputs']['native_directory']['records'][0].update(source_row=7.),
            lambda d:d['raw_inputs']['planning']['record'].update(enrollment=110024.)]
        for i,change in enumerate(changes):
            d=copy.deepcopy(self.document);change(d);r=d['raw_inputs'];schema={k:{f:v[f]for f in v if f!='records'}for k,v in r.items()if k in audit.TABLES}
            with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(r)),mock.patch.object(audit,'ORIGINAL_SCHEMA_SHA',audit.fingerprint(schema)),mock.patch.object(audit,'DEFINITION_INPUT_SHA',audit.fingerprint(r['definitions'])),mock.patch.object(audit,'ORIGINAL_IDENTITY_SHA',audit.identity_fingerprint(r)):
                with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())),self.assertRaises(ValueError):audit.validate(d,self.snapshot)

    def test_current_complete_comparison_policy_and_strict_helpers_fresh_every_replay(self):
        changed=copy.deepcopy(self.snapshot);changed['schools'][0]['name']='Unrelated drift'
        with self.assertRaises(ValueError):audit.validate(self.document,changed)
        with tempfile.TemporaryDirectory()as tmp:
            path=Path(tmp)/'source.json';path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):audit.load_maryland(path)
            with self.assertRaises(FileNotFoundError):audit.load_maryland(Path(tmp)/'absent.json')
        for name,value in[('POLICY',dict(audit.POLICY,counts='certified')),('YEAR',2025.),('MSDE_LEA','16'),('RAW_INPUT_SHA','0'*64)]:
            with self.subTest(name=name),mock.patch.object(audit,name,value),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        for value in[False,1.,'-1','eleven']:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.native_count(value)
        for value in[False,1.,'-1','101','one','90-110']:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.native_percentage(value)
        for field,value in[('source_row',True),('source_row',2.)]:
            e=copy.deepcopy(self.income());e[0][field]=value
            with self.assertRaises(ValueError):audit.income_evidence(e)
        for field,value in[('Tested Count',False),('Year',2025.)]:
            e=copy.deepcopy(self.outcome());e['raw'][field]=value
            with self.assertRaises(ValueError):audit.outcome_evidence(e,'math',scope=True,income=self.links['03-0101']['income'])


if __name__=='__main__':unittest.main()

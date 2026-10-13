"""Original Prince Georges district source/cohort contracts; no model or DB writes."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_prince_georges as audit


class PrinceGeorgesSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.snapshot=audit.load_maryland()
        cls.links={r['school_id']:r for r in cls.document['roster_links']}
        cls.inputs=cls.document['raw_inputs']
        cls.directory={audit.native_identity(e['raw']):e for e in cls.inputs['native_directory']['records']}
        cls.ccd={e['raw']['NCESSCH']:e for e in cls.inputs['directory']['records']}

    def native(self,key,subject='math'):
        label='Mathematics All Grades'if subject=='math'else'English Language Arts All Grades'
        return next(e for e in self.inputs['native_assessment']['records']if e['worksheet']=='School_Level'and audit.native_identity(e['raw'],aggregate=True)==key and e['raw']['Assessment'].strip()==label)

    def income(self,key):
        return [e for e in self.inputs['native_income']['records']if audit.native_identity(e['raw'],income=True,aggregate=True)==key]

    def enrollment(self,key):
        return [e['raw']for e in self.inputs['native_enrollment']['records']if audit.native_identity(e['raw'],aggregate=True)==key]

    def test_foreign_wrong_year_malformed_and_aggregate_id_rejected(self):
        raw=self.directory['16-0105']['raw'];ccd=self.ccd['240051000995']['raw']
        for field,value in [('LEA','14'),('School','51'),('School','A'),('Year',2024),('Year',2025.0)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.native_identity(dict(raw,**{field:value}))
        for field,value in [('LEAID','2400511'),('ST_LEAID','MD-14'),('SCHOOL_YEAR','2023-2024'),('ST','VA'),('NCESSCH','240051100864'),('ST_SCHID','MD-14-160105'),('UPDATED_STATUS','9')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.ccd_identity(dict(ccd,**{field:value}),directory=True)
        income=self.income('16-0105')[0]['raw']
        for field,value in [('LEA Number','14'),('School Number','51'),('Academic Year','2024')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.native_identity(dict(income,**{field:value}),income=True)

    def test_grade_gate_rejects_adjusted_incomplete_high_adult_and_suppressed_high_rows(self):
        profile=self.directory['16-0105']['raw'];ccd=self.ccd['240051000995']['raw'];grades=self.enrollment('16-0105')
        self.assertTrue(audit.grade_school_contract(profile,ccd,grades))
        for field,value in [('IGOFFERED','Imputed'),('G_3_OFFERED','Unknown'),('G_9_OFFERED','Yes'),('G_13_OFFERED','Yes'),('G_UG_OFFERED','Yes'),('G_AE_OFFERED','Yes'),('UPDATED_STATUS','2'),('GSHI','12')]:
            with self.subTest(field=field):
                self.assertFalse(audit.grade_school_contract(profile,dict(ccd,**{field:value}),grades))
        self.assertFalse(audit.grade_school_contract(dict(profile,**{'Grade Span':'EMH'}),ccd,grades))
        self.assertFalse(audit.grade_school_contract(profile,ccd,grades+[dict(grades[0],Grade='Grade 9',**{'Enrolled Count':'*'})]))
        self.assertFalse(audit.grade_school_contract(profile,ccd,[]))

    def test_individual_income_uses_own_counts_and_published_rounding(self):
        income=audit.income_evidence(self.income('16-0105'))
        self.assertEqual((income['individual_low_income_count'],income['early_attendance_enrollment']),(545,795))
        self.assertAlmostEqual(income['percentage'],100*545/795)
        self.assertLessEqual(abs(income['published_rounding_error']),.0500001)
        changed=copy.deepcopy(self.income('16-0105'));changed[0]['raw']['Total Student Cnt']='1000'
        with self.assertRaises(ValueError):audit.income_evidence(changed)
        changed=copy.deepcopy(self.income('16-0105'));changed[0]['raw']['Economically Disadvantaged Pct']='80.0'
        with self.assertRaises(ValueError):audit.income_evidence(changed)
        changed=copy.deepcopy(self.income('16-0105'));changed[0]['raw']['Economically Disadvantaged Cnt']='796'
        with self.assertRaises(ValueError):audit.income_evidence(changed)

    def test_outcome_is_exact_native_school_regular_all_grades(self):
        entry=self.native('16-0105');link=self.links['16-0105']
        outcome=audit.outcome_evidence(entry,'math',scope=True,income=link['income'])
        self.assertEqual(outcome['native_rate'],float(entry['raw']['Proficient Pct']))
        self.assertEqual(entry['raw']['Assessment'],' Mathematics All Grades')
        for field,value in [('Assessment','Mathematics 03'),('Student Group','Economically Disadvantaged'),('Year',2024),('LEA','14'),('School','A'),('Proficient Pct','99.9')]:
            changed=copy.deepcopy(entry);changed['raw'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.outcome_evidence(changed,'math',scope=True,income=link['income'])
        for field,value in [('worksheet','LEA_Level'),('member','2025 MCAP ELA Administrative Data Report Card.xlsx')]:
            changed=copy.deepcopy(entry);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                audit.outcome_evidence(changed,'math',scope=True,income=link['income'])

    def test_offline_replay_never_opens_original_archives_workbooks_or_database(self):
        with mock.patch.object(audit.zipfile,'ZipFile',side_effect=AssertionError('ZIP unavailable')),mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('Original stream unavailable')),mock.patch.object(audit.openpyxl,'load_workbook',side_effect=AssertionError('Workbook unavailable')):
            self.assertEqual(audit.validate(self.document)['prospective_source_profiles'],159)

    def test_original_hashes_headers_derived_values_and_approval_drift_rejected(self):
        changes=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),
            lambda d:d.update(schema_version=1.0),lambda d:d.update(year=2025.0),lambda d:d.update(scope='ready'),lambda d:d.update(models=[]),
            lambda d:d['sources']['msde_income'].update(sha256='0'*64),lambda d:d['raw_inputs']['native_directory']['records'].pop(),
            lambda d:d['raw_inputs']['native_income']['records'][0]['raw'].update({'Economically Disadvantaged Pct':'0'}),
            lambda d:d['raw_inputs']['native_assessment']['records'][0]['raw'].update({'Proficient Pct':'0'}),
            lambda d:d['raw_inputs']['directory']['header'].pop(),lambda d:d['raw_inputs']['lea_membership']['records'].pop(),
            lambda d:d['raw_inputs']['native_assessment']['records'][0].update(source_row=1),
            lambda d:d['raw_inputs']['definitions']['msde_mcap_overview'].update(paraphrase='Changed'),
            lambda d:d['raw_inputs']['planning']['record']['potential_school_ids']['ES'].pop(),
            lambda d:d['roster_links'][0]['subjects']['math'].update(valid_scores=100),
            lambda d:d['roster_links'][0]['subjects']['math'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['cohorts']['native_grade_school_source_profiles']['subjects']['combined'].update(usable=159),
            lambda d:d['coverage'].update(district_minus_known_school_early_attendance_enrollment=1)]
        for i,change in enumerate(changes):
            altered=copy.deepcopy(self.document);change(altered)
            with self.subTest(change=i),self.assertRaises(ValueError):audit.validate(altered,self.snapshot)

    def test_semantic_original_identity_population_and_counts_rejected_after_hash_repin(self):
        changes=[lambda d:d['raw_inputs']['directory']['records'][0]['raw'].update(LEAID='2400511'),
            lambda d:d['raw_inputs']['membership']['records'][0]['raw'].update(ST_SCHID='MD-14-160105'),
            lambda d:d['raw_inputs']['native_income']['records'][0]['raw'].update({'Academic Year':'2024'}),
            lambda d:d['raw_inputs']['native_assessment']['records'][0]['raw'].update({'Student Group':'Economically Disadvantaged'}),
            lambda d:d['raw_inputs']['native_assessment']['records'][0].update(worksheet='LEA_Level'),
            lambda d:d['raw_inputs']['native_assessment']['records'].append(copy.deepcopy(d['raw_inputs']['native_assessment']['records'][0])),
            lambda d:d['raw_inputs']['planning']['record'].update(enrollment=133427),
            lambda d:d['raw_inputs']['native_directory']['records'][0].update(source_row=1)]
        for i,change in enumerate(changes):
            altered=copy.deepcopy(self.document);change(altered)
            with self.subTest(change=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(altered['raw_inputs'])),self.assertRaises(ValueError):
                audit.validate(altered,self.snapshot)

    def test_complete_historical_comparison_change_requires_fresh_audit(self):
        altered=copy.deepcopy(self.snapshot);altered['schools'][0]['name']='Changed unrelated source'
        with self.assertRaises(ValueError):audit.validate(self.document,altered)


    def test_complete_original_inventory_and_native_ccd_views_are_separate(self):
        c=audit.validate(self.document,self.snapshot)
        self.assertEqual((c['native_directory'],c['ccd_directory'],c['operational_roster'],c['matched_operational_native_profiles']),(204,201,199,198))
        self.assertEqual((c['prospective_source_profiles'],c['prospective_usable_income']),(159,159))
        self.assertEqual(c['prospective_usable'],{'math':146,'reading':159,'combined':146})
        self.assertEqual(c['planning_reconstructed_potential_cohorts'],{'ES':160,'HS':23})
        self.assertEqual(c['offered_bands'],{'grade':162,'high':24,'mixed':5,'primary':7,'unknown':1})
        self.assertEqual(len(self.links),204)
        self.assertEqual(sum(not x['source_profile_eligible'] for x in self.links.values()),45)
        self.assertEqual(len(self.document['unmatched_native_directory']),6)
        self.assertEqual(len(self.document['unmatched_ccd_directory']),3)
        self.assertEqual(len(self.document['nonoperational_directory']),2)
        self.assertEqual(self.document['coverage']['source_rows'],audit.ORIGINAL_INVENTORIES)
        self.assertEqual(sum(audit.ORIGINAL_INVENTORIES.values()),5404)
        self.assertEqual(sum(len(e['raw']) for t in audit.TABLES for e in self.inputs[t]['records']),89640)
        for t in audit.TABLES:
            section=self.inputs[t]
            self.assertEqual(section['header'],audit.ORIGINAL_HEADERS[t])
            self.assertIs(type(section['header_source_row']),int)
            for entry in section['records']:
                self.assertEqual(set(entry['raw']),set(section['header']))
                self.assertIs(type(entry['source_row']),int)
        self.assertEqual(audit.identity_fingerprint(self.inputs),audit.ORIGINAL_IDENTITY_SHA)

    def test_exact_crosswalk_preserves_malformed_ellen_without_name_or_local_code_join(self):
        matched=[l for l in self.links.values() if l['operational']]
        self.assertEqual(len(matched),198)
        for link in matched:
            raw=self.directory[link['school_id']]['raw'];ccd=self.ccd[link['ncessch']]['raw']
            self.assertEqual(str(raw['NCES Number']),link['ncessch'])
            self.assertEqual(audit.ccd_identity(ccd,directory=True),link['ncessch'])
            self.assertEqual(link['native_school_id'],ccd['ST_SCHID'])
        ellen=self.links['16-0218']
        self.assertEqual(ellen['native_nces_raw'],24005109050)
        self.assertIsNone(ellen['ncessch']);self.assertIsNone(ellen['native_school_id'])
        self.assertFalse(ellen['operational']);self.assertFalse(ellen['source_profile_eligible'])
        self.assertIn('malformed',ellen['identity_hold'])
        separate=next(e for e in self.document['unmatched_ccd_directory'] if e['raw']['NCESSCH']=='240051090501')
        self.assertEqual(separate['raw']['ST_SCHID'],'MD-16-160218')
        self.assertEqual(separate['raw']['UPDATED_STATUS_TEXT'],'New')
        self.assertEqual(ellen['income']['early_attendance_enrollment'],1103)
        self.assertEqual(ellen['native_september_enrollment'],1086)
        self.assertTrue(all(not v['usable'] for v in ellen['subjects'].values()))
        self.assertEqual({e['raw']['UPDATED_STATUS_TEXT'] for e in self.document['nonoperational_directory']},{'Closed'})

    def test_scope_boundaries_adjusted_unknown_primary_mixed_and_charters_are_audited(self):
        for key in ['16-1001','16-1407','16-0804','16-1437']:
            self.assertFalse(self.links[key]['source_profile_eligible'])
        laurel=self.links['16-1001'];raw=self.ccd[laurel['ncessch']]['raw']
        self.assertEqual(raw['IGOFFERED'],'Adjusted')
        self.assertEqual(self.links['16-1407']['offered']['band'],'primary')
        for key in ['16-0804','16-1437']:
            self.assertIsNone(self.links[key]['native_grade_span'])
            self.assertEqual(self.links[key]['offered']['band'],'grade')
            self.assertEqual(self.links[key]['enrolled']['reported_total'],0)
            self.assertIsNone(self.links[key]['native_september_enrollment'])
        mixed=self.document['cohorts']['native_mixed_configurations']['school_ids']
        self.assertEqual(len(mixed),5)
        self.assertTrue(any(self.links[k]['native_grade_span']=='EH' for k in mixed))
        self.assertTrue(all(not self.links[k]['source_profile_eligible'] for k in mixed))
        charters=[l for l in self.links.values() if l['source_profile_eligible'] and l['ccd_flags']['charter']=='Yes']
        self.assertEqual(len(charters),6)
        self.assertTrue(all(l['subjects']['reading']['usable'] for l in charters))
        profile=self.directory['16-0105']['raw'];ccd=self.ccd['240051000995']['raw'];grades=self.enrollment('16-0105')
        self.assertTrue(audit.grade_school_contract(profile,dict(ccd,CHARTER_TEXT='Yes',SCH_TYPE_TEXT='Alternative School'),grades))

    def test_native_positive_grade_counts_are_required_without_high_or_ungraded_substitution(self):
        profile=self.directory['16-0105']['raw'];ccd=self.ccd['240051000995']['raw'];grades=self.enrollment('16-0105')
        zeros=[dict(r,**{'Enrolled Count':'0'}) for r in grades]
        stars=[dict(r,**{'Enrolled Count':'*'}) for r in grades]
        self.assertFalse(audit.grade_school_contract(profile,ccd,zeros))
        self.assertFalse(audit.grade_school_contract(profile,ccd,stars))
        for label,count in [('Grade 9','0'),('Grade 9','*'),('Ungraded','1'),('Unknown','1')]:
            self.assertFalse(audit.grade_school_contract(profile,ccd,grades+[dict(grades[0],Grade=label,**{'Enrolled Count':count})]))
        grade=copy.deepcopy(self.inputs['membership']['records'][0]['raw'])
        grade.update(GRADE='Not Specified',RACE_ETHNICITY='Not Specified',SEX='Not Specified',STUDENT_COUNT='0',DMS_FLAG='Derived')
        self.assertEqual(audit.grade_count(grade),0)
        grade.update(STUDENT_COUNT='-2',DMS_FLAG='Suppressed')
        self.assertIsNone(audit.grade_count(grade))

    def test_early_attendance_counts_are_separate_from_september_ccd_and_missing_cells(self):
        c=self.document['coverage']
        self.assertEqual((c['district_fall_membership'],c['operational_school_fall_sum']),(132123,132123))
        self.assertEqual((c['district_september_enrollment'],c['native_september_school_total_sum']),(132151,132151))
        self.assertEqual(c['district_membership_grade_evidence']['full_grade_sum'],132123)
        self.assertEqual(c['district_early_attendance_income']['early_attendance_enrollment'],133427)
        self.assertEqual(c['known_school_early_attendance_enrollment_sum'],133427)
        self.assertEqual(c['district_minus_known_school_early_attendance_enrollment'],0)
        self.assertEqual(c['missing_school_early_attendance_denominator_ids'],['16-0303','16-0608','16-0705','16-0804','16-1437','16-2022'])
        self.assertEqual(c['schools_with_early_attendance_ccd_difference'],189)
        self.assertEqual(c['schools_with_early_attendance_september_difference'],191)
        jacs=self.links['16-2217']
        self.assertEqual(jacs['native_september_enrollment'],28)
        self.assertFalse(jacs['operational']);self.assertIsNone(jacs['enrolled']['reported_total'])
        for key in c['missing_school_early_attendance_denominator_ids']:
            self.assertIsNone(self.links[key]['income']['percentage'])
            self.assertIsNone(self.links[key]['income']['individual_low_income_count'])
        for link in self.links.values():
            value=link['income']
            if value['percentage'] is not None:
                self.assertEqual(value['percentage'],100*value['individual_low_income_count']/value['early_attendance_enrollment'])
                self.assertLessEqual(abs(value['published_rounding_error']),.0500001)

    def test_income_all_band_selection_preserves_masks_zero_and_rejects_proxies(self):
        entries=self.income('16-0645');value=audit.income_evidence(entries)
        self.assertEqual(value['selected_school_type'],'All')
        self.assertEqual((value['individual_low_income_count'],value['early_attendance_enrollment']),(352,470))
        self.assertIsNone(audit.income_evidence([e for e in entries if e['raw']['School Type']!='All'])['percentage'])
        with self.assertRaises(ValueError):audit.income_evidence(entries+entries)
        for token in ['<= 5.0','>= 95.0','*','','5-10']:
            changed=copy.deepcopy(self.income('16-0105'));changed[0]['raw'].update({'Economically Disadvantaged Pct':token,'Economically Disadvantaged Cnt':'*','FARMS Pct':'90.0','FARMS Cnt':'700'})
            self.assertIsNone(audit.income_evidence(changed)['percentage'])
        zero=copy.deepcopy(self.income('16-0105'));zero[0]['raw'].update({'Economically Disadvantaged Pct':'0','Economically Disadvantaged Cnt':'0'})
        self.assertEqual(audit.income_evidence(zero)['percentage'],0)
        self.assertIsNone(audit.income_evidence([])['percentage'])

    def test_all_thirteen_math_masks_and_the_independent_paired_combined_population_survive(self):
        profiles=[l for l in self.links.values() if l['source_profile_eligible']]
        masked=[l for l in profiles if not l['subjects']['math']['usable']]
        self.assertEqual(len(masked),13)
        self.assertTrue(all(l['subjects']['math']['raw_rate']=='<= 5.0' for l in masked))
        self.assertTrue(all(l['subjects']['reading']['usable'] for l in profiles))
        self.assertTrue(all(not l['subjects']['combined']['usable'] for l in masked))
        self.assertTrue(all(l['income']['percentage'] is not None for l in profiles))
        for link in profiles:
            for subject in ['math','reading']:
                value=link['subjects'][subject]
                self.assertIsNone(value['tested']);self.assertIsNone(value['valid_scores']);self.assertIsNone(value['sampling_variance'])
                self.assertIs(value['ten_valid_scored_floor_certified'],False)
            if link['subjects']['combined']['usable']:
                self.assertEqual(link['subjects']['combined']['native_rate'],(link['subjects']['math']['native_rate']+link['subjects']['reading']['native_rate'])/2)
        self.assertNotEqual(self.document['cohorts']['native_grade_school_source_profiles']['subjects']['math']['eligible_school_ids'],self.document['cohorts']['native_grade_school_source_profiles']['subjects']['reading']['eligible_school_ids'])

    def test_original_regular_course_waiver_threshold_definitions_and_aggregates_preserved(self):
        c=self.document['coverage']
        self.assertEqual(c['native_assessment_worksheets'],{'LEA_Level':24,'School_Level':1641})
        self.assertEqual(c['outside_native_records'],{'native_enrollment':18,'native_income':4,'native_assessment':24})
        self.assertEqual(c['eligible_course_row_presence'],{'Algebra 1':31,'Algebra 2':1,'Geometry':12})
        self.assertEqual(c['eligible_course_rows_numeric_administrative_count'],{'Algebra 1':29,'Geometry':1})
        self.assertEqual(c['eligible_administrative_math_component_counts_reconciled'],146)
        defs=self.inputs['definitions'];pdf=defs['msde_mcap_overview']
        self.assertEqual(pdf['source_pages'],[1,2]);self.assertEqual(len(pdf['original_pages']),2)
        self.assertIn('2027',pdf['original_pages'][1]['text'])
        self.assertIn('2024',pdf['original_pages'][1]['text'])
        self.assertEqual(defs['msde_reportcard']['section_references'],['2022ELASpecAssessFootnote','2022MathSpecAssessFootnote'])
        self.assertEqual([e['source_line'] for e in defs['msde_reportcard']['original_lines']],[1612,1616])
        self.assertIn('Medicaid',defs['msde_definitions']['plain_text'])
        self.assertIn('2026',defs['msde_definitions']['raw_markup'])
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        self.assertEqual(self.document['scope'],'source_cohort_audit_only')

    def test_repin_cannot_authorize_identity_repair_type_aliases_or_original_schema_omissions(self):
        def rawdir(d,key):return next(e for e in d['raw_inputs']['native_directory']['records'] if e['raw']['School']==key)
        changes=[
            lambda d:rawdir(d,'0218')['raw'].update({'NCES Number':240051090501}),
            lambda d:rawdir(d,'0303')['raw'].update({'NCES Number':240051099999}),
            lambda d:rawdir(d,'0105')['raw'].update({'NCES Number':float(rawdir(d,'0105')['raw']['NCES Number'])}),
            lambda d:d['raw_inputs']['native_income']['records'][0]['raw'].update({'Total Student Cnt':True}),
            lambda d:d['raw_inputs']['native_income']['records'][0]['raw'].update({'Economically Disadvantaged Cnt':1.}),
            lambda d:d['raw_inputs']['native_directory']['records'][0]['raw'].update(Year=2025.),
            lambda d:d['raw_inputs']['native_assessment']['records'][0]['raw'].update({'Tested Count':False}),
            lambda d:d['raw_inputs']['directory'].update(header_source_row=True),
            lambda d:d['raw_inputs']['native_directory']['records'][0].update(source_row=942.),
            lambda d:d['raw_inputs']['native_enrollment']['records'][0].update(source_row=False),
            lambda d:d['raw_inputs']['planning']['record'].update(directory_source_row=7356.),
            lambda d:d['raw_inputs']['planning']['record'].update(membership_source_row=1350127.),
            lambda d:d['raw_inputs']['planning']['record'].update(enrollment=132123.),
            lambda d:d['raw_inputs']['planning']['record']['potential_cohorts'].update(ES=160.),
            lambda d:d['raw_inputs']['membership']['records'].pop(),
            lambda d:d['raw_inputs']['native_directory']['header'].pop(),
            lambda d:d['raw_inputs']['native_assessment'].update(worksheets=['School_Level']),
            lambda d:d['raw_inputs']['definitions']['msde_mcap_overview'].pop('original_pages'),
            lambda d:rawdir(d,'1001')['raw'].update({'Grade Span':'EMH'})]
        for i,change in enumerate(changes):
            d=copy.deepcopy(self.document);change(d)
            with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),self.assertRaises(ValueError):
                audit.validate(d,self.snapshot)
        d=copy.deepcopy(self.document);d['raw_inputs']['native_directory']['header'].pop()
        with mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),mock.patch.object(audit,'ORIGINAL_SCHEMA_SHA',audit.fingerprint({k:{f:v[f] for f in v if f!='records'} for k,v in d['raw_inputs'].items() if k in audit.TABLES})),self.assertRaises(ValueError):audit.validate(d,self.snapshot)
        policy=dict(audit.POLICY);policy.pop('counts')
        with mock.patch.object(audit,'POLICY',policy),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)

    def test_direct_source_helpers_reject_boolean_float_year_count_and_row_aliases(self):
        for key,value in [('source_row',True),('source_row',1057.)]:
            e=copy.deepcopy(self.income('16-0105'));e[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):audit.income_evidence(e)
        for field,value in [('Total Student Cnt',795.),('Economically Disadvantaged Cnt',False)]:
            e=copy.deepcopy(self.income('16-0105'));e[0]['raw'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.income_evidence(e)
        for field,value in [('source_row',3777.),('source_row',False)]:
            e=copy.deepcopy(self.native('16-0105'));e[field]=value
            with self.assertRaises(ValueError):audit.outcome_evidence(e,'math',scope=True,income=self.links['16-0105']['income'])
        for field,value in [('Tested Count',False),('Year',2025.)]:
            e=copy.deepcopy(self.native('16-0105'));e['raw'][field]=value
            with self.assertRaises(ValueError):audit.outcome_evidence(e,'math',scope=True,income=self.links['16-0105']['income'])


if __name__=='__main__':
    unittest.main()

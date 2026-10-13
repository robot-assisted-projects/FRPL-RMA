import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_philadelphia as audit


class PhiladelphiaSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.snapshot=audit.load_pennsylvania()
        cls.raw=cls.document['raw_inputs']
        cls.links={r['school_id']:r for r in cls.document['roster_links']}
        cls.prospects=[r for r in cls.document['roster_links'] if r['source_profile_eligible']]

    def test_complete_original_tables_typed_cells_and_source_only_cohort(self):
        coverage=audit.validate(self.document,self.snapshot)
        self.assertEqual(coverage['source_rows'],dict(directory=221,lea_directory=1,membership=2019,lea_membership=16,
            native_grades=221,native_lea_grades=1,native_income=220,native_lea_income=1,native_assessment=19408))
        self.assertEqual((coverage['original_records'],coverage['original_typed_cells']),(22108,622260))
        self.assertEqual((coverage['ccd_directory'],coverage['operational_roster']),(221,220))
        self.assertEqual(coverage['status'],{'Open':220,'Inactive':1})
        self.assertEqual(coverage['operational_offered_scope'],{'ES':163,'mixed':10,'HS':47})
        self.assertEqual(coverage['prospective_source_profiles'],162)
        self.assertEqual(coverage['prospective_usable'],{'math':162,'reading':162,'combined':162})
        self.assertEqual(coverage['usable_regular_pssa_denominator_counts'],324)
        self.assertTrue(coverage['eligible_subject_sources_all_have_verified_valid_scores'])
        self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
        self.assertEqual((self.document['scope'],self.document['status']),('source_cohort_audit_only','audit_pending'))
        for key in ['models','model_results','coefficients','canonical_dataset']:self.assertNotIn(key,self.document)
        self.assertFalse(coverage['variances_and_intervals_computed'])
        for subject in ['math','reading','combined']:
            c=self.document['cohorts']['prospective_tested_grade_profiles']['subjects'][subject]
            self.assertEqual(c['charter'],{'No':162});self.assertTrue(c['all_eligible_have_verified_scored_denominators'])

    def test_exact_authoritative_codes_no_foreign_charter_or_name_join_and_9999_unmatched(self):
        self.assertEqual(audit.school_id(126515001,7368),'126515001-000007368')
        self.assertEqual(audit.school_id('126515001','000007368'),'126515001-000007368')
        for aun,school in [(126515001,0),(126515002,7368),(126515001,7368.),(False,7368),('Philadelphia City SD',7368)]:
            with self.subTest(aun=aun,school=school),self.assertRaises(ValueError):audit.school_id(aun,school)
        outside=self.document['outside_roster_profiles']
        self.assertEqual(len(outside),1)
        self.assertEqual((outside[0]['school_id'],outside[0]['ncessch'],outside[0]['native_school_id']),('126515001-000009999',None,None))
        self.assertEqual(outside[0]['enrolled']['reported_total'],3862)
        self.assertIsNone(outside[0]['income']['percentage'])
        mee=self.links['126515001-000006768']
        self.assertFalse(mee['operational']);self.assertFalse(mee['native_profile_matched']);self.assertIsNone(mee['enrolled'])
        self.assertNotIn(outside[0]['school_id'],self.links)
        self.assertEqual(len(self.document['coverage']['native_total_outside_pure_scope_ids']),8)
        self.assertEqual(self.document['cohorts']['primary_only']['school_ids'],['126515001-000003732'])

    def test_original_october_individual_income_truncation_own_counts_and_unassigned_differences(self):
        income={audit.native_identity(e['raw'],'native_income'):e for e in self.raw['native_income']['records']}
        for link in self.document['roster_links']:
            if link['school_id'] not in income:continue
            cells=income[link['school_id']]['raw'];evidence=link['income']
            self.assertEqual(evidence['raw'],cells[5:8])
            self.assertEqual(evidence['enrollment'],link['enrolled']['reported_total'])
            if evidence['percentage'] is not None:
                self.assertEqual(evidence['percentage'],100*cells[6]/cells[5])
                self.assertGreaterEqual(cells[6]/cells[5]-cells[7],-.000001)
                self.assertLessEqual(cells[6]/cells[5]-cells[7],.000101)
        c=self.document['coverage']
        self.assertEqual((c['district_october_enrollment'],c['native_school_enrollment_sum']),(120148,120148))
        self.assertEqual((c['known_school_income_enrollment_sum'],c['known_school_individual_income_count_sum']),(116286,88634))
        self.assertEqual(c['district_individual_income_count'],90098)
        self.assertEqual(c['district_individual_income_count']-c['known_school_individual_income_count_sum'],1464)
        self.assertEqual(c['native_school_income_missing_ids'],['126515001-000009999'])
        example=copy.deepcopy(next(iter(income.values())))
        example['raw'][5:8]=[996,71,.0712]
        self.assertEqual(audit.income_evidence(example)['percentage'],100*71/996)
        example['raw'][5:8]=[996,0,0]
        self.assertEqual(audit.income_evidence(example)['percentage'],0.)
        example['raw'][7]='*';self.assertIsNone(audit.income_evidence(example)['percentage'])

    def test_regular_pssa_direct_total_rate_scored_scope_and_floor_without_grade_averaging(self):
        raw_by_row={e['source_row']:e['raw'] for e in self.raw['native_assessment']['records']}
        rounding_difference=False;minimum=10**9
        for link in self.prospects:
            for subject in ['math','reading']:
                out=link['subjects'][subject];raw=raw_by_row[out['source_row']]
                self.assertEqual((raw[0],raw[1],raw[2],raw[6],raw[7],raw[8]),
                    (2025,126515001,link['school_id'].split('-')[1],audit.SUBJECT_LABELS[subject],'All Students','Total'))
                self.assertEqual(out['native_rate'],float(raw[14]))
                self.assertEqual(out['tested'],raw[9]);self.assertGreaterEqual(out['tested'],11)
                self.assertTrue(out['verified_valid_score_scope']);self.assertTrue(out['ten_valid_scored_floor_certified'])
                self.assertIsNone(out['sampling_variance']);self.assertFalse(out['sampling_interval_available'])
                rounding_difference |= abs(raw[10]+raw[11]-raw[14])>.05
                minimum=min(minimum,raw[9])
            combined=link['subjects']['combined']
            self.assertEqual(combined['native_rate'],(link['subjects']['math']['native_rate']+link['subjects']['reading']['native_rate'])/2)
            self.assertIsNone(combined['tested']);self.assertIsNone(combined['sampling_variance'])
        self.assertTrue(rounding_difference);self.assertEqual(minimum,42)
        self.assertEqual(len(self.raw['native_assessment']['records']),19408)
        self.assertTrue(any(e['raw'][7]!='All Students' or e['raw'][8]!='Total' for e in self.raw['native_assessment']['records']))

    def test_small_scored_masks_wrong_population_and_strict_count_numeric_types(self):
        entry=next(e for e in self.raw['native_assessment']['records'] if e['raw'][7:9]==['All Students','Total'] and e['raw'][9]==2)
        subject=next(k for k,v in audit.SUBJECT_LABELS.items() if v==entry['raw'][6])
        income={'exclusion':None}
        out=audit.outcome_evidence(entry,subject,None,income)
        self.assertEqual(out['reported_scored'],2);self.assertIsNone(out['native_rate']);self.assertIsNone(out['tested'])
        self.assertFalse(out['ten_valid_scored_floor_certified']);self.assertIn('masked',out['exclusion'])
        raw=copy.deepcopy(entry);raw['raw'][14]=0
        with self.assertRaises(ValueError):audit.outcome_evidence(raw,subject,None,income)
        healthy=next(e for e in self.raw['native_assessment']['records'] if e['raw'][7:9]==['All Students','Total'] and e['raw'][9]>=42 and type(e['raw'][14]) in {float,int})
        s=next(k for k,v in audit.SUBJECT_LABELS.items() if v==healthy['raw'][6])
        for column,bad in [(0,2024),(0,2025.),(7,'Economically Disadvantaged'),(8,3),(6,'Keystone Algebra I')]:
            altered=copy.deepcopy(healthy);altered['raw'][column]=bad
            with self.subTest(column=column),self.assertRaises(ValueError):audit.outcome_evidence(altered,s,None,income)
        for bad in [False,11.,-1,'11']:
            with self.assertRaises(ValueError):audit.count(bad)
        for bad in [False,float('nan'),float('inf'),-1,101]:
            with self.assertRaises(ValueError):audit.percentage(bad)
        self.assertEqual(audit.count(0),0);self.assertEqual(audit.percentage(0),0.)

    def test_primary_notes_headers_and_field88_131_cep_definition_complete(self):
        notes=' '.join(str(v) for row in self.raw['native_assessment']['header_rows'] for v in row if v is not None)
        for term in ['Number Scored','Percent Proficient and above','fewer than 11','October 1','did not attempt','homeschool','LIFE']:
            self.assertIn(term.casefold(),notes.casefold())
        pages=self.raw['definitions']['pa-pims-2025']['original_pages']
        self.assertEqual([p['page_number'] for p in pages],[160,161,166,167])
        text=' '.join(' '.join(p['text'].split()) for p in pages)
        for term in ['ECONOMIC DISADVANTAGED STATUS CODE','FOOD PROGRAM ELIGIBILITY','Medicaid','foster','Community Eligibility','Field 131']:
            self.assertIn(term,text)
        self.assertIn('not use free and reduced-',text)
        self.assertEqual(self.document['source_definition_evidence']['suppression_minimum_scored'],11)
        self.assertEqual(audit.fingerprint(self.raw),audit.RAW_INPUT_SHA)
        self.assertEqual(audit.identity_fingerprint(self.raw),audit.ORIGINAL_IDENTITY_SHA)
        self.assertEqual(audit.fingerprint(self.document['policy']),audit.POLICY_SHA)
        for kind in ['page','worksheet']:
            definitions=copy.deepcopy(self.raw['definitions'])
            if kind=='page':definitions['pa-pims-2025']['original_pages'][0]['page_number']=160.
            else:definitions['pa-grades-2025']['complete_rows'][0]['source_row']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):audit.validate_definition_references(definitions)

    def test_all_retained_pssa_rows_keep_nonnegative_counts_and_original_rate_precision(self):
        records=self.raw['native_assessment']['records']
        unused=next(i for i,e in enumerate(records) if e['raw'][7:9]!=['All Students','Total'])
        selected=next(i for i,e in enumerate(records) if e['raw'][7:9]==['All Students','Total'] and e['raw'][14] is not None)
        for index,column,bad in [(unused,9,-1),(unused,14,101),(unused,10,5.555),(selected,14,5.555)]:
            changed=copy.deepcopy(self.document);changed['raw_inputs']['native_assessment']['records'][index]['raw'][column]=bad
            with self.subTest(index=index,column=column,bad=bad),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(changed['raw_inputs'])),self.assertRaises(ValueError):
                audit.validate(changed,self.snapshot)
        for value in [None,0,100,5.5,5.500000000000001]:
            self.assertEqual(audit.published_percentage(value),None if value is None else float(value))
        for value in [-.1,100.1,5.555,True,float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):audit.published_percentage(value)
        for entry in records:
            self.assertGreaterEqual(audit.count(entry['raw'][9]),0)
            for value in entry['raw'][10:15]:audit.published_percentage(value)

    def test_source_output_scope_identity_income_counts_and_approval_corruptions_reject(self):
        mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),
            lambda d:d.update(year=2025.),lambda d:d.update(models=[]),lambda d:d['roster_links'].pop(),
            lambda d:d['outside_roster_profiles'][0].update(ncessch='421899006768'),
            lambda d:d['roster_links'][0]['income'].update(percentage=0.),
            lambda d:d['roster_links'][0]['subjects']['math'].update(tested=9999),
            lambda d:d['roster_links'][0]['subjects']['combined'].update(tested=100),
            lambda d:d['coverage'].update(variances_and_intervals_computed=True)]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.document);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(changed,self.snapshot)

    def test_raw_repin_foreign_id_year_subgroup_header_count_and_row_type_reject(self):
        mutations=[lambda r:r['directory']['records'][0]['raw'].update(ST='NJ'),
            lambda r:r['native_grades']['records'][0]['raw'].__setitem__(0,126515002),
            lambda r:r['native_income']['records'][0]['raw'].__setitem__(3,7904.),
            lambda r:r['native_grades']['records'][0]['raw'].__setitem__(17,False),
            lambda r:r['native_assessment']['records'][0]['raw'].__setitem__(0,2025.),
            lambda r:r['native_assessment']['records'][0]['raw'].__setitem__(9,11.),
            lambda r:r['native_assessment']['records'][0]['raw'].__setitem__(8,9),
            lambda r:r['native_income']['records'][0].update(source_row=True),
            lambda r:r['native_assessment']['header_rows'][3].__setitem__(9,'Enrollment'),
            lambda r:r['definitions']['pa-pims-2025']['original_pages'].pop()]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.document);mutate(changed['raw_inputs'])
            with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(changed['raw_inputs'])),self.assertRaises(ValueError):
                audit.validate(changed,self.snapshot)
        for field,bad in [('directory_source_row',True),('membership_source_row',float(self.raw['planning']['record']['membership_source_row']))]:
            changed=copy.deepcopy(self.document);changed['raw_inputs']['planning']['record'][field]=bad
            with self.subTest(field=field),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(changed['raw_inputs'])),self.assertRaises(ValueError):
                audit.validate(changed,self.snapshot)

    def test_current_policy_runtime_and_cached_state_source_freshness_offline_no_fit(self):
        policy=copy.deepcopy(audit.POLICY);policy['counts']='Use enrollment as tested counts'
        for field,bad in [('POLICY',policy),('YEAR',2025.),('SUBJECT_LABELS',{'math':'Keystone','reading':'English Language Arts'}),('AUN','126515002')]:
            with self.subTest(field=field),mock.patch.object(audit,field,bad),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'POLICY',policy),mock.patch.object(audit,'POLICY_SHA',audit.fingerprint(policy)),self.assertRaises(ValueError):
            audit.validate(self.document,self.snapshot)
        original=Path.read_bytes;path=ROOT/'data/source/pennsylvania.json'
        def read(p):return b'{}' if p==path else original(p)
        with mock.patch.object(Path,'read_bytes',read),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
        with mock.patch.object(audit,'extract_raw_inputs',side_effect=AssertionError('No original extraction')),mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No decompression')):
            self.assertEqual(audit.validate(self.document)['prospective_source_profiles'],162)


if __name__=='__main__':unittest.main()

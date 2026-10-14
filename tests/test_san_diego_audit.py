"""Source-only San Diego original evidence, population and authority controls."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_san_diego as audit

class SanDiegoSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads(audit.OUTPUT.read_text())
        cls.rows={r['school_id']:r for r in cls.document['roster_links']}
        cls.raw=cls.document['raw_inputs']

    def test_complete_exact_original_roster_and_scope_are_source_only(self):
        c=audit.validate(self.document)
        self.assertEqual((c['directory_records'],c['operational_schools'],c['exact_native_matches']),(175,175,175))
        self.assertEqual((c['pure_lower_profiles'],c['source_usable_math'],c['source_usable_reading'],c['source_usable_combined']),(143,141,141,141))
        self.assertEqual(c['roster_charter'],{'No':175})
        self.assertEqual(c['lower_school_types'],{'Alternative School':1,'Regular School':142})
        self.assertIs(self.document['approved_for_source'],False)
        self.assertIs(self.document['approved_for_modeling'],False)
        self.assertEqual(c['full_needed_original_records'],3789)
        self.assertEqual(c['full_needed_original_typed_cells'],169260)

    def test_all_raw_tables_complete_headers_typed_cells_and_omitted_inventories(self):
        for table,size in audit.ORIGINAL_INVENTORIES.items():
            b=self.raw[table];self.assertEqual(len(b['records']),size)
            self.assertEqual(audit.fingerprint({k:v for k,v in b.items()if k!='records'}),audit.ORIGINAL_METADATA[table])
            self.assertTrue(all(set(e['raw'])==set(b['header'])for e in b['records']))
            inventory=b['complete_district_inventory']
            self.assertEqual(inventory['retained_rows']+inventory['omitted_rows'],inventory['original_district_rows'])
            self.assertEqual(inventory['omitted_source_ordinals'],[e['source_row']for e in inventory['omitted_identity_population_inventory']])
        self.assertEqual(self.raw['membership']['complete_district_inventory']['omitted_rows'],17945)
        self.assertEqual(self.raw['lea_membership']['complete_district_inventory']['omitted_rows'],227)
        self.assertEqual(len(self.raw['frpm']['header']),27)
        self.assertEqual(len(self.raw['assessment']['header']),69)

    def test_income_own_K12_counts_and_exact_original_eligibility_not_alternative_proxies(self):
        for row in self.rows.values():
            raw=row['native_profile']['raw'];value=row['income']
            self.assertEqual(value['enrollment'],raw['Enrollment (K-12)'])
            self.assertEqual(value['eligible'],raw['FRPM Count (K-12)'])
            self.assertAlmostEqual(value['percentage'],100*value['eligible']/value['enrollment'],12)
            self.assertEqual(value['snapshot_date'],'2024-10-02')
        raw=copy.deepcopy(self.raw['frpm']['records'][0]);raw['raw'].update({'Enrollment (K-12)':20,'FRPM Count (K-12)':0,'Percent (%) Eligible FRPM (K-12)':0.0})
        self.assertEqual(audit.income_evidence(raw)['percentage'],0)
        raw['raw'].update({'Enrollment (K-12)':0,'FRPM Count (K-12)':0})
        self.assertIsNone(audit.income_evidence(raw)['percentage'])
        raw['raw']['Enrollment (K-12)']=True
        with self.assertRaises(ValueError):audit.income_evidence(raw)

    def test_verified_score_denominators_and_weighted_grade_aggregation_not_percentage_mean(self):
        observed_difference=False
        for row in self.rows.values():
            if not row['prospective_lower_profile']:continue
            for subject in ['math','reading']:
                value=row['subjects']['ES'][subject]
                if not value['source_usable']:continue
                points=[audit.valid_grade(e)[0]for e in value['exact_original_expected_grade_refs']]
                n=sum(p['valid_scores']for p in points);met=sum(p['proficient']for p in points)
                self.assertEqual(value['valid_scores'],n);self.assertEqual(value['proficient_count'],met)
                self.assertAlmostEqual(value['proficiency'],100*met/n,12)
                self.assertTrue(all(p['valid_scores']>=11 for p in points))
                self.assertIs(value['all_grades13_counts_match_expected_complete_components'],True)
                if len(points)>1 and abs(sum(p['percentage']for p in points)/len(points)-value['proficiency'])>.01:observed_difference=True
        self.assertTrue(observed_difference)

    def test_published_all_grades_totals_do_not_recover_two_missing_component_records(self):
        for key in ['063432011382','063432014617']:
            row=self.rows[key];self.assertTrue(row['prospective_lower_profile'])
            for subject in ['math','reading']:
                value=row['subjects']['ES'][subject]
                self.assertFalse(value['source_usable']);self.assertIsNone(value['valid_scores']);self.assertIsNone(value['proficiency'])
                self.assertIsNotNone(value['native_all_grades13']['verified'])
                self.assertIn('Missing an expected',value['exclusion'])
            self.assertFalse(row['subjects']['ES']['combined']['source_usable'])

    def test_substantive_grade_conflict_and_literal_preschool_differences_retained(self):
        row=self.rows['063432005487']
        self.assertEqual((row['grade_evidence']['ccd_scope'],row['grade_evidence']['native_scope']),('ES','mixed'))
        self.assertFalse(row['prospective_lower_profile'])
        self.assertEqual(self.document['coverage']['substantive_grade_scope_holds'],['063432005487'])
        preschool=[r for r in self.rows.values()if r['native_profile']['raw']['Low Grade']=='P']
        self.assertTrue(preschool)
        self.assertTrue(all(r['grade_evidence']['native_raw_low']=='P'for r in preschool))
        self.assertTrue(any(r['grade_evidence']['ccd_raw_low']=='KG'for r in preschool))
        self.assertIn('does not report',json.dumps(self.raw['definitions']['ccd_state_notes']))

    def test_CCD_suppression_and_unassigned_membership_differences_never_impute_zero(self):
        row=self.rows['063432005459'];self.assertIsNone(row['ccd_enrollment']['total'])
        self.assertEqual(row['ccd_enrollment']['total_raw']['DMS_FLAG'],'Suppressed')
        self.assertGreater(row['income']['enrollment'],0)
        self.assertTrue(row['prospective_lower_profile'])
        r=self.document['enrollment_reconciliation']
        self.assertEqual((r['ccd_LEA_enrollment'],r['known_operational_school_enrollment'],r['ccd_LEA_minus_known_school_sum']),(95175,94828,347))
        self.assertEqual((r['native_exact_roster_K12_enrollment'],r['ccd_LEA_minus_native_K12_sum']),(94991,184))
        self.assertEqual(r['unknown_operational_totals'],['063432005459'])

    def test_outside_charters_and_program_labels_never_join_by_reporting_prefix_or_name(self):
        outside=self.document['outside_roster_native_profiles'];self.assertEqual(len(outside),42)
        self.assertEqual(sum(r['profile']['raw']['Charter School (Y/N)'].strip()=='Yes'for r in outside),41)
        unsupported=next(r for r in outside if r['native_school_id']=='37683380000001')
        self.assertEqual(unsupported['profile']['raw']['School Type'],'N/A')
        self.assertEqual(unsupported['profile']['raw']['Low Grade'],'N/A')
        self.assertEqual(unsupported['assessment_source_rows'],[])
        self.assertFalse({r['native_school_id']for r in outside}&{r['native_school_id']for r in self.rows.values()})
        row=self.rows['063432012534']
        self.assertEqual(row['ccd_flags']['school_type'],'Alternative School')
        self.assertEqual(row['native_administrative_labels']['Educational Option Type'],'Alternative School of Choice')
        self.assertIn('Unknown',row['programs_admissions_virtual_provider'])
        self.assertTrue(row['prospective_lower_profile'])

    def test_combined_equal_mean_separate_subject_counts_and_discovery_ID_differences(self):
        for row in self.rows.values():
            for values in row['subjects'].values():
                c=values['combined']
                self.assertIsNone(c['valid_scores'])
                if c['source_usable']:self.assertEqual(c['proficiency'],(values['math']['proficiency']+values['reading']['proficiency'])/2)
        p=self.document['planning_reconciliation']
        self.assertEqual(p['planning_only'],['063432005487'])
        self.assertEqual(p['source_only'],['063432005459'])
        self.assertTrue(p['planning_never_approves_model'])

    def test_raw_schema_definition_identity_and_derived_corruptions_reject(self):
        mutations=[
            lambda d:d.__setitem__('approved_for_source',0),
            lambda d:d.__setitem__('approved_for_modeling',True),
            lambda d:d['raw_inputs']['directory']['records'][0].__setitem__('source_row',True),
            lambda d:d['raw_inputs']['directory']['records'][0]['raw'].__setitem__('ST_SCHID','CA-3768338-123'),
            lambda d:d['raw_inputs']['frpm']['records'][0]['raw'].__setitem__('Academic Year','2023-2024'),
            lambda d:d['raw_inputs']['assessment']['records'][0]['raw'].__setitem__('Student Group ID','31'),
            lambda d:d['raw_inputs']['assessment']['header'].__setitem__(0,'Different County'),
            lambda d:d['raw_inputs']['membership']['complete_district_inventory']['omitted_source_ordinals'].__setitem__(0,True),
            lambda d:d['raw_inputs']['definitions']['research_layout']['worksheets'][0]['rows'][0].__setitem__('source_row',1.0),
            lambda d:d['roster_links'][0]['income'].__setitem__('percentage',0),
            lambda d:d['coverage'].__setitem__('source_usable_combined',143),
        ]
        for mutate in mutations:
            d=copy.deepcopy(self.document);mutate(d)
            with self.assertRaises(ValueError):audit.validate(d)

    def test_cached_inputs_public_runtime_repins_and_forged_builder_reject(self):
        d=copy.deepcopy(self.document);d['raw_inputs']['frpm']['records'][0]['raw']['FRPM Count (K-12)']=0
        with patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])):
            with patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())):
                with self.assertRaises(ValueError):audit.validate(d)
        for name,value in [('LEA','063432'),('NATIVE_LEA','CA-3768339'),('MIN_VALID',10),('MIN_VALID',True),('SUBJECTS',{'math':'1','reading':'2'}),('POLICY_SHA','0'*64),('ORIGINAL_SCHEMA_SHA','0'*64),('ORIGINAL_IDENTITY_SHA','0'*64),('DEFINITION_INPUT_SHA','0'*64)]:
            with patch.object(audit,name,value):
                with self.assertRaises(ValueError):audit.validate(self.document)
        with tempfile.TemporaryDirectory(dir=ROOT/'data/build',prefix='san-diego-builder-')as temp:
            destination=Path(temp)/'source.json'
            with self.assertRaises(ValueError):audit.build(d['raw_inputs'],destination)
            self.assertFalse(destination.exists())

    def test_live_semantic_change_rejects_without_python_version_specific_pin(self):
        fn=audit.valid_grade
        constants=tuple(.006 if v==.0051 else v for v in fn.__code__.co_consts)
        altered=types.FunctionType(fn.__code__.replace(co_consts=constants),fn.__globals__,fn.__name__,fn.__defaults__,fn.__closure__)
        with patch.object(audit,'valid_grade',altered):
            with self.assertRaisesRegex(ValueError,'semantic function changed'):audit.validate(self.document)
        audit.require_runtime_contract()

    def test_every_whole_original_missing_changed_and_coherent_public_source_repin_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/build',prefix='san-diego-current-original-')as temp:
            shadow=Path(temp)
            for source in audit.SOURCES.values():
                p=shadow/source['path'];p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(ROOT/source['path'])
            with patch.object(audit,'ROOT',shadow):
                audit.validate(self.document)
                for key,source in audit.SOURCES.items():
                    path=shadow/source['path'];path.unlink()
                    with self.assertRaises(FileNotFoundError):audit.validate(self.document)
                    path.write_bytes(b'corrupt current original')
                    with self.assertRaises(ValueError):audit.validate(self.document)
                    forged=copy.deepcopy(audit.SOURCES);forged[key].update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    with patch.object(audit,'SOURCES',forged):
                        with patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())):
                            with self.assertRaises(ValueError):audit.validate(self.document)
                    path.unlink();path.symlink_to(ROOT/source['path'])

    def test_offline_actual_original_extraction_reproduces_full_retained_and_omitted_evidence(self):
        def denied(*args,**kwargs):raise AssertionError('Source replay must be offline')
        with patch.object(socket,'create_connection',side_effect=denied),patch.object(socket.socket,'connect',side_effect=denied):
            self.assertEqual(audit.fingerprint(audit.extract_raw_inputs()),audit.RAW_INPUT_SHA)
            audit.validate(self.document)

if __name__=='__main__':unittest.main()

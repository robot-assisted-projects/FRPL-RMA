"""Meaningful Lee isolated integration population, replay and prewrite ownership checks."""
import copy
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from database import connect
from state_snapshot import import_snapshot
import state_snapshot
import prepare_lee as lee
TABLES=['dataset','source','assessment_definition','economic_definition','school','economic_observation','assessment_observation','model_run','model_result']
WORK=ROOT/'data/build/lee-integration-implementation'

def rows(db):return{t:[tuple(r)for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]for t in TABLES}
def prior(db):return{t:[r for r in a if not any(type(v)is str and(v==lee.DATASET or v.startswith(lee.DATASET+':'))for v in r)]for t,a in rows(db).items()}
def seed_other(db):
    """A legal same-native-ID Florida comparison owns its independent facts."""
    db.execute("INSERT INTO dataset VALUES ('other-fl','FL','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-fl','other.json','https://example.test/source',?,'2025-01-01')",('1'*64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','FL','Other test',2025,'ES','3','Keep standard','https://example.test/test')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-fl','36-0081','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-fl','36-0081',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-fl','36-0081','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-fl','other-assessment','math','keep-method',?,'{}')",('2'*64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-fl','36-0081',40,45,-1,-2,0)")
def run_prepared(operation,*args):
    handles=[];original=state_snapshot.connect
    def tracked(p):h=original(p);handles.append(h);return h
    try:
        with mock.patch.object(state_snapshot,'connect',side_effect=tracked):return operation(*args)
    finally:
        for h in handles:h.close()

class LeeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True);cls.roster,cls.numerical=lee.load_inputs();cls.payload=json.loads(lee.EXTRACT.read_text());cls.expected=lee.build_snapshot(cls.roster,cls.numerical)
        cls.profiles={s['id']:s for s in cls.payload['schools']};cls.links={s['school_id']:s for s in cls.roster['roster_links']}
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.output=Path(cls.sandbox.name)/'output';cls.database=Path(cls.sandbox.name)/'schools.sqlite'
        with closing(connect(cls.database))as db:db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit()
        run_prepared(lee.prepare,cls.database,cls.output)
    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def test_exact_separate_78_profiles_immutable_history_and_44_outside_records(self):
        self.assertEqual(lee.validate(self.payload,self.expected),self.payload['source_audit']);self.assertEqual(self.payload['dataset'],'fl-lee-2025');self.assertEqual((self.payload['region'],self.payload['region_name']),('lee','Lee County'))
        self.assertEqual(len(self.profiles),78);self.assertEqual(len(self.payload['sources']),18)
        self.assertEqual(set(self.profiles),set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        self.assertIs(self.payload['approved_for_source'],True);self.assertIs(self.payload['approved_for_modeling'],True)
        for old in [self.roster,self.numerical]:self.assertIs(old['approved_for_source'],False);self.assertIs(old['approved_for_modeling'],False)
        src=self.payload['source_audit'];self.assertEqual((src['complete_source_reference']['complete_original_record_count'],src['complete_source_reference']['complete_original_cell_count']),(1449,34610))
        self.assertEqual(len(src['retained_scope_exclusions']),44);self.assertEqual(len(src['nonoperational_ccd_references']),3);self.assertEqual(src['retained_outside_source_profiles'],[])
        for k in ['36-0541','36-0581','36-7001','36-7023','36-9123']:self.assertNotIn(k,self.profiles)
        self.assertNotIn('raw_inputs',self.payload);self.assertNotIn('retained_raw_inputs',src)

    def test_original_crosswalk_own_february_individual_ratio_and_published_whole_rates(self):
        raw=self.roster['raw_inputs'];idx={t:{e['source_row']:e['raw']for e in raw[t]['records']}for t in ['directory','native_income','native_grades','native_assessment']}
        for key,p in self.profiles.items():
            refs=p['identity_raw']['source_refs'];d=idx['directory'][refs['directory']['source_row']];n=idx['native_income'][refs['income']['source_row']]
            self.assertEqual((d['LEAID'],d['ST_LEAID'],d['NCESSCH'],d['ST_SCHID']),('1201080','FL-36',p['ncessch'],p['identity_raw']['native_school_id']))
            self.assertEqual(key,d['ST_SCHID'][3:]);self.assertEqual((p['enrollment'],p['low_income']),(n[4],n[5]+n[6]+n[8]));self.assertEqual(p['income'],100*p['low_income']/p['enrollment']);self.assertEqual(n[7],0)
            self.assertEqual(idx['native_grades'][refs['native_enrollment']['source_row']][14:18],[0]*4)
            for subject in ['math','reading']:
                value=p['outcomes'][subject];ref=value['raw']['source_refs'];cells=idx['native_assessment'][ref['source_row']]
                self.assertEqual(value['proficiency'],float(cells[lee.model_audit.SUBJECT_FIELDS[subject]]));self.assertEqual(value['raw']['original_native_rate'],cells[lee.model_audit.SUBJECT_FIELDS[subject]])
                self.assertEqual(ref['fields'],[raw['native_assessment']['header_rows'][-1][i]for i in ref['columns']]);self.assertIsNone(value['tested']);self.assertIsNone(value['raw_tested']);self.assertIsNone(value['raw']['sampling_variance'])
        island=self.profiles['36-4100'];self.assertEqual((island['income'],island['low_income'],island['enrollment'],island['ncessch']),(0.,0,66,'120108003725'))

    def test_all234_canonical_current_history_metrics_unknown_programs_and_null_intervals(self):
        self.assertEqual(lee.validate_canonical(self.payload,self.database,self.numerical),dict(schools=78,observations=156,models=3,results=234))
        self.assertEqual(lee.validate_exports(self.payload,self.output,self.numerical),{f'lee-2025-ES-{s}':78 for s in lee.EXPECTED_N})
        current=json.loads((self.output/'schools.json').read_text());history=json.loads((self.output/'history.json').read_text());byid={s['id']:s for s in current['schools']};h={s['school_id']:s for s in history['records']}
        for model in self.numerical['models']:
            for r in model['results']:
                metric=byid[r['school_id']]['metrics'][model['subject']];self.assertEqual(metric,h[r['school_id']]['subjects'][model['subject']])
                for k in ['actual','predicted','residual','studentized','leverage']:self.assertAlmostEqual(metric[k],r[k],delta=2e-9)
                for k in ['tested','low','high']:self.assertIsNone(metric[k])
        for s in current['schools']:self.assertEqual(s['program'],'Unclassified');self.assertEqual(s['programs'],['Unclassified']);self.assertIsNone(s['latitude']);self.assertIsNone(s['longitude']);self.assertEqual(s['exclusions'],{})
        self.assertEqual(sum(r['charter']=='Yes'for r in self.numerical['models'][0]['inputs']),11)
        self.assertIn('36-4305',byid);self.assertIn('36-4100',byid)

    def test_combined_own_paired_fit_scale_and_studentization_remain_fixed(self):
        m,e,c=self.numerical['models'];self.assertEqual([r['school_id']for r in m['inputs']],[r['school_id']for r in c['inputs']])
        self.assertTrue(any(abs(cr['studentized']-(mr['studentized']+er['studentized'])/2)>.01 for cr,mr,er in zip(c['results'],m['results'],e['results'])))
        self.assertGreater(abs(c['diagnostics']['residual_standard_error']-(m['diagnostics']['residual_standard_error']+e['diagnostics']['residual_standard_error'])/2),.1)
        for r in c['inputs']:self.assertEqual(r['outcome_pct'],(r['outcome_by_subject']['math']+r['outcome_by_subject']['reading'])/2)
        self.assertIn('Filters never refit models',' '.join(self.payload['methodology']['details']));self.assertIn('do not establish causal',' '.join(self.payload['methodology']['details']))

    def test_repeat_import_preserves_all_nine_tables_and_legal_same_native_other_release(self):
        with closing(connect(':memory:'))as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);before=prior(db);import_snapshot(db,self.payload,lee.EXTRACT);first=rows(db);import_snapshot(db,self.payload,lee.EXTRACT)
            self.assertEqual(first,rows(db));self.assertEqual(before,prior(db));self.assertEqual({t:len(first[t])-len(before[t])for t in TABLES},dict(dataset=1,source=19,assessment_definition=1,economic_definition=1,school=78,economic_observation=78,assessment_observation=156,model_run=0,model_result=0));self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
        before_files={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with closing(connect(self.database))as db:first=rows(db);old=prior(db)
        run_prepared(lee.prepare,self.database,self.output)
        with closing(connect(self.database))as db:self.assertEqual(first,rows(db));self.assertEqual(old,prior(db))
        self.assertEqual(before_files,{p.name:p.read_bytes()for p in self.output.glob('*.json')})

    def test_all_nine_canonical_ownership_changes_reject_before_repeat_delete_or_write(self):
        ds=lee.DATASET;key=self.payload['schools'][0]['id'];second=self.payload['schools'][1]['id']
        cases=[f"UPDATE dataset SET state='GA' WHERE id='{ds}'",f"UPDATE source SET dataset_id='other-fl' WHERE id='{ds}:extract'",f"UPDATE assessment_definition SET year=2024 WHERE id LIKE '{ds}:%'",f"UPDATE economic_definition SET definition='Universal meals' WHERE id='{ds}:income'",f"UPDATE school SET source_id='other-source' WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE assessment_observation SET tested=999 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE model_run SET method_version='standardized-residual' WHERE dataset_id='{ds}' AND subject='math'",f"UPDATE model_result SET studentized=99 WHERE dataset_id='{ds}' AND school_id='{key}'",
            f"INSERT INTO source SELECT id||':ghost','other-fl',path,url,sha256,imported_at FROM source WHERE id='{ds}:extract'",f"INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE '{ds}:%'",f"INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='{ds}:income'",f"INSERT INTO model_run SELECT id||':ghost','other-fl',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='{ds}' AND subject='math'",
            f"UPDATE school SET source_id='{ds}:extract' WHERE dataset_id='other-fl'",f"UPDATE economic_observation SET source_id='{ds}:extract' WHERE dataset_id='other-fl'",f"UPDATE economic_observation SET definition_id='{ds}:income' WHERE dataset_id='other-fl'",f"UPDATE assessment_observation SET source_id='{ds}:extract' WHERE dataset_id='other-fl'",f"UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE '{ds}:%') WHERE dataset_id='other-fl'",f"INSERT INTO model_result VALUES ('other-model','{ds}','{second}',50,51,1,NULL,NULL)"]
        with tempfile.TemporaryDirectory(prefix='namespace-',dir=WORK)as folder:
            wrong=Path(folder)/'wrong.sqlite'
            for sql in cases:
                with closing(connect(self.database))as source,closing(connect(wrong))as db:source.backup(db);db.execute(sql);db.commit()
                before=wrong.read_bytes()
                with self.subTest(sql=sql),self.assertRaises(ValueError):lee.validate_canonical(self.payload,wrong,self.numerical)
                with self.subTest(sql=sql),mock.patch.object(lee,'prepare_snapshot',side_effect=AssertionError('No writer for corrupt namespace')),self.assertRaises(ValueError):lee.prepare(wrong,self.output)
                self.assertEqual(before,wrong.read_bytes())

    def test_standalone_empty_namespace_checks_current_payload_and_numerical_before_sql(self):
        bad=copy.deepcopy(self.payload);bad['schools'][0]['income']+=1e-12
        numeric=copy.deepcopy(self.numerical);numeric['models'][0]['results'][0]['studentized']+=1
        with mock.patch.object(lee,'connect',side_effect=AssertionError('No SQL access before current evidence')):
            with self.assertRaises(ValueError):lee.validate_existing_namespace(bad,':memory:',self.numerical,lee.EXTRACT)
            with self.assertRaises(ValueError):lee.validate_existing_namespace(self.payload,':memory:',numeric,lee.EXTRACT)
        with closing(connect(':memory:'))as db:db.executescript((ROOT/'scripts/schema.sql').read_text())

    def test_normalized_mutations_and_self_expected_public_resigning_are_not_authority(self):
        changes=[lambda d:d['schools'].pop(),lambda d:d['schools'][0].update(income=d['schools'][0]['income']+1e-12),lambda d:d['schools'][0].update(ncessch='120108099999'),lambda d:d['schools'][0]['outcomes']['math'].update(proficiency=99.),lambda d:d['schools'][0]['outcomes']['math'].update(tested=100),lambda d:d['schools'][0]['identity_raw']['source_refs']['income'].update(source_row=1.),lambda d:d.update(approved_for_modeling=1),lambda d:d['schools'][0].update(latitude=0.),lambda d:d['selection']['directory_school_ids'].pop(),lambda d:d['source_audit']['retained_scope_exclusions'].pop(),lambda d:d['source_audit']['release_basis'].update(ten_valid_scored_floor_certified=True)]
        for change in changes:
            d=copy.deepcopy(self.payload);change(d)
            with self.assertRaises(ValueError):lee.validate(d,d)
            with mock.patch.object(lee,'NORMALIZED_PAYLOAD_SHA',lee.roster_audit.fingerprint(d)),self.assertRaises(ValueError):lee.validate(d,d)
        d=copy.deepcopy(self.numerical);d['models'][0]['results'][0]['studentized']+=1
        with self.assertRaises(ValueError):lee.build_snapshot(self.roster,d)

    def test_current_source_numerical_and_adapter_contract_repins_reject_before_sql(self):
        policy=copy.deepcopy(lee.model_audit.POLICY);policy['models']='Use enrollment weights and prune Cook outliers'
        changes=[(lee,'EXPECTED_N',{'math':78.,'reading':78,'combined':78}),(lee,'INCOME_DEFINITION','Universal meals identify everyone'),(lee,'COUNT_NOTE','Use enrollment as scores'),(lee,'NUMERICAL_BYTES',722801.),(lee,'NUMERICAL_SHA','0'*64),(lee.model_audit,'POLICY',policy),(lee.model_audit,'MIN_SCHOOLS',False),(lee.model_audit,'SUBJECT_FIELDS',{'math':20,'reading':6}),(lee.roster_audit,'RAW_INPUT_SHA','0'*64)]
        for module,field,value in changes:
            with self.subTest(field=field),mock.patch.object(module,field,value),mock.patch.object(lee,'connect',side_effect=AssertionError('No SQL access')),mock.patch.object(lee,'prepare_snapshot',side_effect=AssertionError('No writer')):
                with self.assertRaises(ValueError):lee.validate(self.payload,self.payload)
                with self.assertRaises(ValueError):lee.prepare(self.database,self.output)
                with self.assertRaises(ValueError):lee.validate_existing_namespace(self.payload,self.database,self.numerical,lee.EXTRACT)
        with mock.patch.object(lee,'INCOME_DEFINITION','Universal meals'):
            with mock.patch.object(lee,'ADAPTER_CONTRACT_SHA',lee.roster_audit.fingerprint(lee.adapter_contract())),self.assertRaises(ValueError):lee.validate(self.payload,self.payload)

    def test_missing_changed_complete_six_files_and_secondary_reject_cached_before_sql(self):
        original=Path.read_bytes
        targets=[lee.model_audit.ROSTER,lee.model_audit.SOURCE_CODE,lee.model_audit.SOURCE_TESTS,lee.model_audit.OUTPUT,ROOT/'scripts/audit_lee_models.py',ROOT/'tests/test_lee_models.py',ROOT/'data/source/florida.json']
        for target in targets:
            for missing in [True,False]:
                def read(p):
                    if p==target:
                        if missing:raise FileNotFoundError('Controlled linked file missing')
                        return original(p)+b' '
                    return original(p)
                with self.subTest(target=target,missing=missing),mock.patch.object(Path,'read_bytes',read),mock.patch.object(lee,'connect',side_effect=AssertionError('No SQL before current artifacts')):
                    with self.assertRaises((ValueError,FileNotFoundError)):lee.validate(self.payload,self.payload)
                    with self.assertRaises((ValueError,FileNotFoundError)):lee.validate_existing_namespace(self.payload,self.database,self.numerical,lee.EXTRACT)
        target=ROOT/lee.roster_audit.SOURCES['school-code']['path'];original_open=Path.open
        def missing_primary(p,*args,**kwargs):
            if p==target and args and args[0]=='rb':raise FileNotFoundError('Controlled complete primary missing')
            return original_open(p,*args,**kwargs)
        with mock.patch.object(Path,'open',missing_primary),mock.patch.object(lee,'connect',side_effect=AssertionError('No SQL before primary')):
            with self.assertRaises(FileNotFoundError):lee.validate_existing_namespace(self.payload,self.database,self.numerical,lee.EXTRACT)

    def test_static_fake_counts_intervals_program_geography_and_missing_member_reject(self):
        originals={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='static-',dir=WORK)as folder:
            out=Path(folder);catalog=json.loads(originals['catalog.json']);catalog['regions'][0].update(schools=str((out/'schools.json').relative_to(ROOT)),audit=str((out/'coverage.json').relative_to(ROOT)))
            for filename,change in [('schools.json',lambda d:d['schools'][0]['metrics']['math'].update(low=0.)),('schools.json',lambda d:d['schools'][0]['metrics']['math'].update(tested=100)),('schools.json',lambda d:d['schools'][0].update(program='Selective')),('schools.json',lambda d:d['schools'][0].update(latitude=30.)),('schools.json',lambda d:d['schools'].pop()),('history.json',lambda d:d['records'][0]['subjects']['combined'].update(studentized=99.)),('coverage.json',lambda d:d.update(schools=79))]:
                for name,data in originals.items():(out/name).write_bytes(data)
                (out/'catalog.json').write_text(json.dumps(catalog));d=json.loads((out/filename).read_text());change(d);(out/filename).write_text(json.dumps(d))
                with self.subTest(filename=filename),self.assertRaises(ValueError):lee.validate_exports(self.payload,out,self.numerical)

    def test_repeat_normalized_builds_preserve_six_audits_and_source_measure_limits(self):
        paths=[lee.model_audit.ROSTER,lee.model_audit.SOURCE_CODE,lee.model_audit.SOURCE_TESTS,lee.model_audit.OUTPUT,ROOT/'scripts/audit_lee_models.py',ROOT/'tests/test_lee_models.py'];before={p:p.read_bytes()for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-',dir=WORK)as folder:
            one=Path(folder)/'one.json';two=Path(folder)/'two.json';lee.extract(one);lee.extract(two);self.assertEqual(one.read_bytes(),two.read_bytes());self.assertEqual(one.read_bytes(),lee.EXTRACT.read_bytes())
        self.assertEqual(before,{p:p.read_bytes()for p in paths})
        for text in [self.payload['cohorts'][0]['note'],self.payload['coverage_note']]:self.assertIn('valid-score',text);self.assertIn('uncertified',text);self.assertIn('sampling intervals',text)
        self.assertIn('All valid-score counts',lee.COUNT_NOTE);self.assertIn('sampling intervals are unavailable',lee.COUNT_NOTE)
        self.assertIn('Provision 2 code 4',self.payload['income_definition']['definition']);self.assertIn('school’s own reported denominator',self.payload['income_definition']['definition'])
        self.assertIn('FAST/BEST/FAA',self.payload['cohorts'][0]['assessment']);self.assertIn('School Grades',self.payload['cohorts'][0]['assessment'])

if __name__=='__main__':unittest.main()

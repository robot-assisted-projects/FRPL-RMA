"""Isolated Memphis source integrity, complete namespace ownership and static parity."""
import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from database import connect
from state_snapshot import import_snapshot
import state_snapshot
import prepare_memphis as memphis
TABLES=['dataset','source','assessment_definition','economic_definition','school','economic_observation','assessment_observation','model_run','model_result']
WORK=ROOT/'data/build/memphis-integration-implementation'
HELD={'470014801583','470014801595','470014801960','470014802217'}


def rows(db):return {t:[tuple(r)for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]for t in TABLES}
def prior_rows(db):return {t:[r for r in records if not any(isinstance(v,str)and(v==memphis.DATASET or v.startswith(memphis.DATASET+':'))for v in r)]for t,records in rows(db).items()}
def seed_other(db):
    db.execute("INSERT INTO dataset VALUES ('other-tn','TN','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-tn','other.json','https://example.test/source',?,'2025-01-01')",('1'*64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','TN','Other test',2025,'ES','3','Keep standard','https://example.test/test')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-tn','470014801583','Keep shared NCES','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-tn','470014801583',2025,'other-income','Keep shared NCES',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-tn','470014801583','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-tn','other-assessment','math','keep-method',?,'{}')",('2'*64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-tn','470014801583',40,45,-1,-2,0)")

def run_prepared(operation,*args):
    handles=[];original=state_snapshot.connect
    def tracked(path):h=original(path);handles.append(h);return h
    try:
        with mock.patch.object(state_snapshot,'connect',side_effect=tracked):return operation(*args)
    finally:
        for h in handles:h.close()


class MemphisIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True);cls.roster,cls.numerical=memphis.load_inputs();cls.payload=json.loads(memphis.EXTRACT.read_text());cls.expected=memphis.build_snapshot(cls.roster,cls.numerical)
        cls.links={r['school_id']:r for r in cls.roster['roster_links']};cls.profiles={s['id']:s for s in cls.payload['schools']};cls.key=cls.numerical['models'][0]['inputs'][0]['school_id']
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.output=Path(cls.sandbox.name)/'output';cls.database=Path(cls.sandbox.name)/'schools.sqlite'
        with closing(connect(cls.database))as db:db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit()
        run_prepared(memphis.prepare,cls.database,cls.output)
    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def test_repeat_import_all_nine_tables_preserves_legal_same_nces_other_tennessee_release(self):
        with closing(connect(':memory:'))as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);before=prior_rows(db);import_snapshot(db,self.payload,memphis.EXTRACT);first=rows(db);import_snapshot(db,self.payload,memphis.EXTRACT)
            self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db));added={t:len(first[t])-len(before[t])for t in TABLES}
            self.assertEqual(added,dict(dataset=1,source=21,assessment_definition=1,economic_definition=1,school=154,economic_observation=154,assessment_observation=308,model_run=0,model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',(memphis.DATASET,)).fetchone()[0],4)
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',(memphis.DATASET,)).fetchone()[0],289)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall());self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_all_154_profiles_four_held_null_metrics_original_raw_evidence_and_exact_native_crosswalk(self):
        self.assertEqual(len(self.profiles),154);self.assertEqual({s['id']for s in self.payload['schools']if s['income']is None},HELD)
        for key,profile in self.profiles.items():
            link=self.links[key];self.assertEqual(profile['id'],profile['ncessch']);self.assertEqual(profile['identity_raw']['native_school_id'],link['native_school_id']);self.assertTrue(profile['identity_raw']['native_school_id'].startswith('TN-00792-'))
            self.assertEqual((profile['enrollment'],profile['low_income']),(link['income']['reported_membership'],link['income']['reported_direct_certification']))
            raw=profile['income_raw']['individual_income'];self.assertEqual(raw['reported_percentage'],100*profile['low_income']/profile['enrollment'])
            if key in HELD:
                self.assertIsNone(profile['income']);self.assertIsNotNone(profile['income_raw']['source_attribution_hold'])
                for value in profile['outcomes'].values():self.assertIsNone(value['proficiency']);self.assertIsNotNone(value['raw']['original_reported_percentage']);self.assertIsNotNone(value['raw']['source_refs'])
            else:self.assertEqual(profile['income'],raw['reported_percentage'])
        self.assertNotIn('470014802229',self.profiles);self.assertEqual(self.payload['source_audit']['retained_outside_source_profiles'][0]['ncessch'],'470014802229')

    def test_private_current_history_catalog_and_all_431_metrics_match_audited_point_only_models(self):
        self.assertEqual(memphis.validate_canonical(self.payload,self.database,self.numerical),dict(schools=154,observations=308,models=3,results=431))
        self.assertEqual(memphis.validate_exports(self.payload,self.output,self.numerical),{f'memphis-2025-ES-{s}':n for s,n in memphis.EXPECTED_N.items()})
        current=json.loads((self.output/'schools.json').read_text());history=json.loads((self.output/'history.json').read_text());indexed={s['id']:s for s in current['schools']};records={r['school_id']:r for r in history['records']}
        for key in HELD:self.assertEqual(indexed[key]['metrics'],{});self.assertEqual(records[key]['subjects'],{});self.assertIsNone(records[key]['income'])
        for model in self.numerical['models']:
            self.assertEqual(current['models']['ES'][model['subject']]['n'],memphis.EXPECTED_N[model['subject']])
            for result in model['results']:
                metric=indexed[result['school_id']]['metrics'][model['subject']];self.assertEqual(metric,records[result['school_id']]['subjects'][model['subject']]);self.assertIsNone(metric['tested']);self.assertIsNone(metric['low']);self.assertIsNone(metric['high']);self.assertAlmostEqual(metric['studentized'],result['studentized'],delta=2e-9)
        for s in current['schools']:self.assertEqual(s['program'],'Unclassified');self.assertEqual(s['programs'],['Unclassified']);self.assertIsNone(s['latitude']);self.assertIsNone(s['longitude'])
        self.assertIn('completeness is unknown',self.payload['income_definition']['definition']);self.assertIn('nonlisted',self.payload['coverage_note'])

    def test_canonical_all_nine_ownership_raw_year_and_model_corruptions_reject_before_repeat_write(self):
        key=self.key;ds=memphis.DATASET
        sqls=[f"UPDATE dataset SET state='FL' WHERE id='{ds}'",f"UPDATE source SET dataset_id='other-tn' WHERE id='{ds}:extract'",f"UPDATE assessment_definition SET year=2024 WHERE id LIKE '{ds}:%'",f"UPDATE economic_definition SET definition='Universal meal eligibility' WHERE id='{ds}:income'",f"UPDATE school SET name='Wrong school' WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE assessment_observation SET tested=999 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE model_run SET method_version='standardized-residual' WHERE dataset_id='{ds}' AND subject='math'",f"UPDATE model_result SET studentized=99 WHERE dataset_id='{ds}' AND school_id='{key}'",
            f"UPDATE assessment_observation SET proficiency=50,status='reported' WHERE dataset_id='{ds}' AND school_id='470014801583'",f"UPDATE economic_observation SET percentage=50 WHERE dataset_id='{ds}' AND school_id='470014801583'",
            f"INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='{ds}' AND school_id='{key}'",
            f"INSERT INTO source SELECT id||':ghost','other-tn',path,url,sha256,imported_at FROM source WHERE id='{ds}:extract'",f"INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE '{ds}:%'",f"INSERT INTO model_run SELECT id||':ghost','other-tn',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='{ds}' AND subject='math'",
            f"UPDATE school SET source_id='{ds}:extract' WHERE dataset_id='other-tn'",f"UPDATE economic_observation SET source_id='{ds}:extract' WHERE dataset_id='other-tn'",f"UPDATE economic_observation SET definition_id='{ds}:income' WHERE dataset_id='other-tn'",f"UPDATE assessment_observation SET source_id='{ds}:extract' WHERE dataset_id='other-tn'",f"UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE '{ds}:%') WHERE dataset_id='other-tn'",f"INSERT INTO model_result VALUES ('other-model','{ds}','{key}',50,51,1,NULL,NULL)"]
        with tempfile.TemporaryDirectory(prefix='namespace-',dir=WORK)as t:
            wrong=Path(t)/'wrong.sqlite'
            for sql in sqls:
                with closing(connect(self.database))as source,closing(connect(wrong))as db:source.backup(db);db.execute(sql);db.commit();before=rows(db)
                with self.subTest(sql=sql),self.assertRaises(ValueError):memphis.validate_canonical(self.payload,wrong,self.numerical)
                with self.subTest(prewrite=sql),mock.patch.object(memphis,'prepare_snapshot',side_effect=AssertionError('No writer for corrupt namespace')),self.assertRaises(ValueError):memphis.prepare(wrong,self.output)
                with closing(connect(wrong))as db:self.assertEqual(before,rows(db))

    def test_static_held_income_fake_intervals_ghosts_and_provider_inference_reject(self):
        originals={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='static-',dir=WORK)as t:
            out=Path(t);catalog=json.loads(originals['catalog.json']);catalog['regions'][0].update(schools=str((out/'schools.json').relative_to(ROOT)),audit=str((out/'coverage.json').relative_to(ROOT)))
            for filename,change in [('schools.json',lambda d:d['schools'][0].update(latitude=35.)),('schools.json',lambda d:next(s for s in d['schools']if s['id']=='470014801583').update(income=50.)),('schools.json',lambda d:d['schools'][0].update(program='Selective')),('schools.json',lambda d:next(s for s in d['schools']if s['id']==self.key)['metrics']['math'].update(low=0.)),('history.json',lambda d:next(r for r in d['records']if r['school_id']=='470014801583')['subjects'].update(math={'actual':50.})),('coverage.json',lambda d:d.update(schools=155)),('schools.json',lambda d:d['schools'].pop())]:
                for name,data in originals.items():(out/name).write_bytes(data)
                (out/'catalog.json').write_text(json.dumps(catalog));d=json.loads((out/filename).read_text());change(d);(out/filename).write_text(json.dumps(d))
                with self.subTest(filename=filename),self.assertRaises(ValueError):memphis.validate_exports(self.payload,out,self.numerical)

    def test_normalized_typed_scope_income_masks_rates_counts_and_approval_changes_reject_cached(self):
        mutations=[lambda d:d.update(approved_for_source=1),lambda d:d.update(approved_for_modeling=False),lambda d:d.update(dataset='other-tn'),lambda d:d['schools'][0].update(income_year=2024),lambda d:d['schools'][0].update(income=d['schools'][0]['income']+1e-12),lambda d:next(s for s in d['schools']if s['id']=='470014801583').update(income=50.),lambda d:next(s for s in d['schools']if s['id']=='470014801583')['outcomes']['math'].update(proficiency=50.),lambda d:d['schools'][0]['outcomes']['math'].update(tested=100),lambda d:d['source_audit']['release_basis'].update(ten_valid_scored_floor_certified=True),lambda d:d['selection']['directory_school_ids'].pop(),lambda d:d['schools'][0]['identity_raw'].update(edc_native_school_id='792-9999'),lambda d:d['source_audit']['retained_outside_source_profiles'].clear()]
        for change in mutations:
            d=copy.deepcopy(self.payload);change(d)
            with self.assertRaises(ValueError):memphis.validate(d,self.expected)
        d=copy.deepcopy(self.payload);d['schools'][0]['outcomes']['math']['tested']=100
        with mock.patch.object(memphis,'NORMALIZED_PAYLOAD_SHA',memphis.roster_audit.fingerprint(d)),self.assertRaises(ValueError):memphis.validate(d,d)

    def test_current_source_numerical_adapter_policy_and_public_resigning_fail_before_sql(self):
        policy=copy.deepcopy(memphis.model_audit.POLICY);policy['models']='Average subject residuals and discard influence'
        changes=[(memphis,'EXPECTED_N',{'math':142.,'reading':147,'combined':142}),(memphis,'INCOME_DEFINITION','Universal meal receipt'),(memphis,'ASSESSMENT','Different test'),(memphis,'STANDARD','Different standard'),(memphis,'NUMERICAL_BYTES',1961906.),(memphis,'NUMERICAL_SHA','0'*64),(memphis.model_audit,'POLICY',policy),(memphis.model_audit,'MIN_SCHOOLS',30.),(memphis.model_audit,'SUBJECTS',['math','combined']),(memphis.model_audit,'RATE_FIELD','ProficientOrAbove_count'),(memphis.roster_audit,'RAW_INPUT_SHA','0'*64),(memphis.roster_audit,'ASSESSMENT_SELECTOR',dict(memphis.roster_audit.ASSESSMENT_SELECTOR,AssmtType='Alternate'))]
        for module,name,value in changes:
            with self.subTest(name=name),mock.patch.object(module,name,value),mock.patch.object(memphis,'prepare_snapshot',side_effect=AssertionError('No writer for drift')):
                with self.assertRaises(ValueError):memphis.validate(self.payload,self.expected)
                with self.assertRaises(ValueError):memphis.prepare(self.database,self.output)
        with mock.patch.object(memphis,'INCOME_DEFINITION','Universal meals'):
            repin=memphis.roster_audit.fingerprint(memphis.adapter_contract())
            with mock.patch.object(memphis,'ADAPTER_CONTRACT_SHA',repin),self.assertRaises(ValueError):memphis.validate(self.payload,self.expected)

    def test_missing_changed_complete_six_artifacts_and_secondary_reject_cached_without_mutation(self):
        original=Path.read_bytes;paths=[memphis.model_audit.ROSTER,memphis.model_audit.SOURCE_CODE,memphis.model_audit.SOURCE_TESTS,memphis.model_audit.OUTPUT,ROOT/'scripts/audit_memphis_models.py',ROOT/'tests/test_memphis_models.py',ROOT/'data/source/ccd-state-snapshots.json']
        for target in paths:
            for missing in [True,False]:
                def read(path):
                    if path==target:
                        if missing:raise FileNotFoundError('Private missing complete evidence fixture')
                        return b'{}'
                    return original(path)
                with self.subTest(path=target.name,missing=missing),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):memphis.validate(self.payload,self.expected)

    def test_all_historical_six_false_approvals_and_normalized_ready_are_distinct(self):
        for path,sha in [(memphis.model_audit.ROSTER,memphis.model_audit.ROSTER_SHA),(memphis.model_audit.SOURCE_CODE,memphis.model_audit.SOURCE_CODE_SHA),(memphis.model_audit.SOURCE_TESTS,memphis.model_audit.SOURCE_TESTS_SHA),(memphis.model_audit.OUTPUT,memphis.NUMERICAL_SHA),(ROOT/'scripts/audit_memphis_models.py',memphis.NUMERICAL_CODE_SHA),(ROOT/'tests/test_memphis_models.py',memphis.NUMERICAL_TESTS_SHA)]:self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),sha)
        for d in [self.roster,self.numerical]:self.assertFalse(d['approved_for_source']);self.assertFalse(d['approved_for_modeling'])
        self.assertTrue(self.payload['approved_for_source']);self.assertTrue(self.payload['approved_for_modeling']);self.assertEqual(self.payload['release_status'],'ready')
        self.assertEqual(len(self.payload['sources']),20);self.assertNotIn('raw_inputs',self.payload['source_audit']);self.assertEqual(self.payload['source_audit']['operational_roster']['district_minus_reported_operational_enrollment'],-1)

    def test_invalid_destination_and_corrupt_payload_never_reach_shared_writer(self):
        with mock.patch.object(memphis,'prepare_snapshot',side_effect=AssertionError('Never import invalid evidence')):
            with self.assertRaises(ValueError):memphis.prepare(self.database,Path('/private/tmp/outside-memphis'))
            with tempfile.TemporaryDirectory(prefix='bad-payload-',dir=WORK)as t:
                path=Path(t)/'bad.json';d=copy.deepcopy(self.payload);d['schools'].pop();path.write_text(json.dumps(d))
                with self.assertRaises(ValueError):memphis.prepare(self.database,self.output,path)

    def test_two_normalized_builds_and_private_prepares_repeat_all_rows_and_export_bytes(self):
        with tempfile.TemporaryDirectory(prefix='normalized-',dir=WORK)as t:
            a,b=Path(t)/'one.json',Path(t)/'two.json';memphis.extract(a);memphis.extract(b);self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(a.read_bytes(),memphis.EXTRACT.read_bytes())
        with closing(connect(self.database))as db:first=rows(db)
        files={p.name:p.read_bytes()for p in self.output.glob('*.json')};run_prepared(memphis.prepare,self.database,self.output)
        with closing(connect(self.database))as db:self.assertEqual(first,rows(db))
        self.assertEqual(files,{p.name:p.read_bytes()for p in self.output.glob('*.json')})

if __name__=='__main__':unittest.main()

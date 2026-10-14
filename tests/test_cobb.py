"""Isolated Cobb source integrity, complete namespace ownership and static parity."""
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
import prepare_cobb as cobb
TABLES=['dataset','source','assessment_definition','economic_definition','school','economic_observation','assessment_observation','model_run','model_result']
WORK=ROOT/'data/build/cobb-integration-implementation'
HELD=set()


def rows(db):return {t:[tuple(r)for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]for t in TABLES}
def prior_rows(db):return {t:[r for r in records if not any(isinstance(v,str)and(v==cobb.DATASET or v.startswith(cobb.DATASET+':'))for v in r)]for t,records in rows(db).items()}
def seed_other(db):
    db.execute("INSERT INTO dataset VALUES ('other-ga','GA','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-ga','other.json','https://example.test/source',?,'2025-01-01')",('1'*64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','GA','Other test',2025,'ES','3','Keep standard','https://example.test/test')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-ga','130129000511','Keep shared NCES','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-ga','130129000511',2025,'other-income','Keep shared NCES',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-ga','130129000511','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-ga','other-assessment','math','keep-method',?,'{}')",('2'*64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-ga','130129000511',40,45,-1,-2,0)")

def run_prepared(operation,*args):
    handles=[];original=state_snapshot.connect
    def tracked(path):h=original(path);handles.append(h);return h
    try:
        with mock.patch.object(state_snapshot,'connect',side_effect=tracked):return operation(*args)
    finally:
        for h in handles:h.close()


class CobbIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True);cls.roster,cls.numerical=cobb.load_inputs();cls.payload=json.loads(cobb.EXTRACT.read_text());cls.expected=cobb.build_snapshot(cls.roster,cls.numerical)
        cls.links={r['school_id']:r for r in cls.roster['roster_links']};cls.profiles={s['id']:s for s in cls.payload['schools']};cls.key=cls.numerical['models'][0]['inputs'][0]['school_id']
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.output=Path(cls.sandbox.name)/'output';cls.database=Path(cls.sandbox.name)/'schools.sqlite'
        with closing(connect(cls.database))as db:db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit()
        run_prepared(cobb.prepare,cls.database,cls.output)
    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def test_repeat_import_all_nine_tables_preserves_legal_same_nces_other_georgia_release(self):
        with closing(connect(':memory:'))as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);before=prior_rows(db);import_snapshot(db,self.payload,cobb.EXTRACT);first=rows(db);import_snapshot(db,self.payload,cobb.EXTRACT)
            self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db));added={t:len(first[t])-len(before[t])for t in TABLES}
            self.assertEqual(added,dict(dataset=1,source=len(self.payload['sources'])+1,assessment_definition=1,economic_definition=1,school=90,economic_observation=90,assessment_observation=180,model_run=0,model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',(cobb.DATASET,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',(cobb.DATASET,)).fetchone()[0],180)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall());self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_all_90_profiles_own_income_exact_native_crosswalk_and_outside_scopes(self):
        self.assertEqual(len(self.profiles),90);self.assertTrue(all(s['income']is not None for s in self.payload['schools']))
        for key,profile in self.profiles.items():
            link=self.links[key];self.assertEqual(profile['id'],profile['ncessch']);self.assertEqual(profile['identity_raw']['native_school_id'],link['native_school_id']);self.assertTrue(profile['identity_raw']['native_school_id'].startswith('GA-633-'))
            self.assertEqual((profile['enrollment'],profile['low_income']),(link['income']['reported_membership'],link['income']['reported_direct_certification']))
            raw=profile['income_raw']['individual_income'];self.assertEqual(raw['reported_percentage'],100*profile['low_income']/profile['enrollment']);self.assertEqual(profile['income'],raw['reported_percentage'])
            self.assertIsNone(profile['income_raw']['source_attribution_hold'])
            for subject,value in profile['outcomes'].items():self.assertEqual(value['proficiency'],link['subjects'][subject]['native_rate']);self.assertIsNotNone(value['raw']['source_refs'])
        self.assertEqual(self.payload['source_audit']['retained_outside_source_profiles'],[])
        outside={r['school_id']for r in self.payload['source_audit']['retained_scope_exclusions']};self.assertEqual(len(outside),20);self.assertTrue({'130129000552','130129003528','130129000513'}<=outside)
        self.assertFalse(self.payload['source_audit']['attribution_coverage']['EOG_accelerated_EOC_population_certified']);self.assertFalse(self.payload['source_audit']['attribution_coverage']['nonlisted_attribution_coverage_certified'])

    def test_private_current_history_catalog_and_all_270_metrics_match_audited_point_only_models(self):
        self.assertEqual(cobb.validate_canonical(self.payload,self.database,self.numerical),dict(schools=90,observations=180,models=3,results=270))
        self.assertEqual(cobb.validate_exports(self.payload,self.output,self.numerical),{f'cobb-2025-ES-{s}':n for s,n in cobb.EXPECTED_N.items()})
        current=json.loads((self.output/'schools.json').read_text());history=json.loads((self.output/'history.json').read_text());indexed={s['id']:s for s in current['schools']};records={r['school_id']:r for r in history['records']}
        for key in HELD:self.assertEqual(indexed[key]['metrics'],{});self.assertEqual(records[key]['subjects'],{});self.assertIsNone(records[key]['income'])
        for model in self.numerical['models']:
            self.assertEqual(current['models']['ES'][model['subject']]['n'],cobb.EXPECTED_N[model['subject']])
            for result in model['results']:
                metric=indexed[result['school_id']]['metrics'][model['subject']];self.assertEqual(metric,records[result['school_id']]['subjects'][model['subject']]);self.assertIsNone(metric['tested']);self.assertIsNone(metric['low']);self.assertIsNone(metric['high']);self.assertAlmostEqual(metric['studentized'],result['studentized'],delta=2e-9)
        for s in current['schools']:self.assertEqual(s['program'],'Unclassified');self.assertEqual(s['programs'],['Unclassified']);self.assertIsNone(s['latitude']);self.assertIsNone(s['longitude'])
        self.assertIn('Medicaid',self.payload['income_definition']['definition']);self.assertIn('foster',self.payload['income_definition']['definition']);self.assertFalse(self.payload['source_audit']['attribution_coverage']['nonlisted_attribution_coverage_certified'])

    def test_canonical_all_nine_ownership_raw_year_and_model_corruptions_reject_before_repeat_write(self):
        key=self.key;ds=cobb.DATASET
        sqls=[f"UPDATE dataset SET state='FL' WHERE id='{ds}'",f"UPDATE source SET dataset_id='other-ga' WHERE id='{ds}:extract'",f"UPDATE assessment_definition SET year=2024 WHERE id LIKE '{ds}:%'",f"UPDATE economic_definition SET definition='Universal meal eligibility' WHERE id='{ds}:income'",f"UPDATE school SET name='Wrong school' WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE assessment_observation SET tested=999 WHERE dataset_id='{ds}' AND school_id='{key}'",f"UPDATE model_run SET method_version='standardized-residual' WHERE dataset_id='{ds}' AND subject='math'",f"UPDATE model_result SET studentized=99 WHERE dataset_id='{ds}' AND school_id='{key}'",
            f"UPDATE assessment_observation SET proficiency=50,status='reported' WHERE dataset_id='{ds}' AND school_id='130129000511'",f"UPDATE economic_observation SET percentage=50 WHERE dataset_id='{ds}' AND school_id='130129000511'",
            f"INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='{ds}' AND school_id='{key}'",
            f"INSERT INTO source SELECT id||':ghost','other-ga',path,url,sha256,imported_at FROM source WHERE id='{ds}:extract'",f"INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE '{ds}:%'",f"INSERT INTO model_run SELECT id||':ghost','other-ga',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='{ds}' AND subject='math'",
            f"UPDATE school SET source_id='{ds}:extract' WHERE dataset_id='other-ga'",f"UPDATE economic_observation SET source_id='{ds}:extract' WHERE dataset_id='other-ga'",f"UPDATE economic_observation SET definition_id='{ds}:income' WHERE dataset_id='other-ga'",f"UPDATE assessment_observation SET source_id='{ds}:extract' WHERE dataset_id='other-ga'",f"UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE '{ds}:%') WHERE dataset_id='other-ga'",f"INSERT INTO model_result VALUES ('other-model','{ds}','{self.payload['schools'][1]['id']}',50,51,1,NULL,NULL)"]
        with tempfile.TemporaryDirectory(prefix='namespace-',dir=WORK)as t:
            wrong=Path(t)/'wrong.sqlite'
            for sql in sqls:
                with closing(connect(self.database))as source,closing(connect(wrong))as db:source.backup(db);db.execute(sql);db.commit();before=rows(db)
                with self.subTest(sql=sql),self.assertRaises(ValueError):cobb.validate_canonical(self.payload,wrong,self.numerical)
                with self.subTest(prewrite=sql),mock.patch.object(cobb,'prepare_snapshot',side_effect=AssertionError('No writer for corrupt namespace')),self.assertRaises(ValueError):cobb.prepare(wrong,self.output)
                with closing(connect(wrong))as db:self.assertEqual(before,rows(db))

    def test_static_held_income_fake_intervals_ghosts_and_provider_inference_reject(self):
        originals={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='static-',dir=WORK)as t:
            out=Path(t);catalog=json.loads(originals['catalog.json']);catalog['regions'][0].update(schools=str((out/'schools.json').relative_to(ROOT)),audit=str((out/'coverage.json').relative_to(ROOT)))
            for filename,change in [('schools.json',lambda d:d['schools'][0].update(latitude=35.)),('schools.json',lambda d:d['schools'][0].update(income=d['schools'][0]['income']+.1)),('schools.json',lambda d:d['schools'][0].update(program='Selective')),('schools.json',lambda d:next(s for s in d['schools']if s['id']==self.key)['metrics']['math'].update(low=0.)),('history.json',lambda d:d['records'][0]['subjects'].update(math={'actual':50.})),('coverage.json',lambda d:d.update(schools=91)),('schools.json',lambda d:d['schools'].pop())]:
                for name,data in originals.items():(out/name).write_bytes(data)
                (out/'catalog.json').write_text(json.dumps(catalog));d=json.loads((out/filename).read_text());change(d);(out/filename).write_text(json.dumps(d))
                with self.subTest(filename=filename),self.assertRaises(ValueError):cobb.validate_exports(self.payload,out,self.numerical)

    def test_normalized_typed_scope_income_masks_rates_counts_and_approval_changes_reject_cached(self):
        mutations=[lambda d:d.update(approved_for_source=1),lambda d:d.update(approved_for_modeling=False),lambda d:d.update(dataset='other-ga'),lambda d:d['schools'][0].update(income_year=2024),lambda d:d['schools'][0].update(income=d['schools'][0]['income']+1e-12),lambda d:d['schools'][0].update(income=50.),lambda d:d['schools'][0]['outcomes']['math'].update(proficiency=50.),lambda d:d['schools'][0]['outcomes']['math'].update(tested=100),lambda d:d['source_audit']['release_basis'].update(ten_valid_scored_floor_certified=True),lambda d:d['selection']['directory_school_ids'].pop(),lambda d:d['schools'][0]['identity_raw'].update(edc_native_school_id='633-9999'),lambda d:d['source_audit']['retained_scope_exclusions'].pop()]
        for change in mutations:
            d=copy.deepcopy(self.payload);change(d)
            with self.assertRaises(ValueError):cobb.validate(d,self.expected)
        d=copy.deepcopy(self.payload);d['schools'][0]['outcomes']['math']['tested']=100
        with mock.patch.object(cobb,'NORMALIZED_PAYLOAD_SHA',cobb.roster_audit.fingerprint(d)),self.assertRaises(ValueError):cobb.validate(d,d)

    def test_current_source_numerical_adapter_policy_and_public_resigning_fail_before_sql(self):
        policy=copy.deepcopy(cobb.model_audit.POLICY);policy['models']='Average subject residuals and discard influence'
        changes=[(cobb,'EXPECTED_N',{'math':90.,'reading':90,'combined':90}),(cobb,'INCOME_DEFINITION','Universal meal receipt'),(cobb,'ASSESSMENT','Different test'),(cobb,'STANDARD','Different standard'),(cobb,'NUMERICAL_BYTES',1176631.),(cobb,'NUMERICAL_SHA','0'*64),(cobb.model_audit,'POLICY',policy),(cobb.model_audit,'MIN_SCHOOLS',30.),(cobb.model_audit,'SUBJECTS',['math','combined']),(cobb.model_audit,'RATE_FIELD','ProficientOrAbove_count'),(cobb.roster_audit,'RAW_INPUT_SHA','0'*64),(cobb.roster_audit,'ASSESSMENT_SELECTOR',dict(cobb.roster_audit.ASSESSMENT_SELECTOR,AssmtType='Alternate'))]
        for module,name,value in changes:
            with self.subTest(name=name),mock.patch.object(module,name,value),mock.patch.object(cobb,'prepare_snapshot',side_effect=AssertionError('No writer for drift')):
                with self.assertRaises(ValueError):cobb.validate(self.payload,self.expected)
                with self.assertRaises(ValueError):cobb.prepare(self.database,self.output)
        with mock.patch.object(cobb,'INCOME_DEFINITION','Universal meals'):
            repin=cobb.roster_audit.fingerprint(cobb.adapter_contract())
            with mock.patch.object(cobb,'ADAPTER_CONTRACT_SHA',repin),self.assertRaises(ValueError):cobb.validate(self.payload,self.expected)

    def test_missing_changed_complete_six_artifacts_and_secondary_reject_cached_without_mutation(self):
        original=Path.read_bytes;paths=[cobb.model_audit.ROSTER,cobb.model_audit.SOURCE_CODE,cobb.model_audit.SOURCE_TESTS,cobb.model_audit.OUTPUT,ROOT/'scripts/audit_cobb_models.py',ROOT/'tests/test_cobb_models.py',ROOT/'data/source/ccd-state-snapshots.json']
        for target in paths:
            for missing in [True,False]:
                def read(path):
                    if path==target:
                        if missing:raise FileNotFoundError('Private missing complete evidence fixture')
                        return b'{}'
                    return original(path)
                with self.subTest(path=target.name,missing=missing),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):cobb.validate(self.payload,self.expected)

    def test_all_historical_six_false_approvals_and_normalized_ready_are_distinct(self):
        for path,sha in [(cobb.model_audit.ROSTER,cobb.model_audit.ROSTER_SHA),(cobb.model_audit.SOURCE_CODE,cobb.model_audit.SOURCE_CODE_SHA),(cobb.model_audit.SOURCE_TESTS,cobb.model_audit.SOURCE_TESTS_SHA),(cobb.model_audit.OUTPUT,cobb.NUMERICAL_SHA),(ROOT/'scripts/audit_cobb_models.py',cobb.NUMERICAL_CODE_SHA),(ROOT/'tests/test_cobb_models.py',cobb.NUMERICAL_TESTS_SHA)]:self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),sha)
        for d in [self.roster,self.numerical]:self.assertFalse(d['approved_for_source']);self.assertFalse(d['approved_for_modeling'])
        self.assertTrue(self.payload['approved_for_source']);self.assertTrue(self.payload['approved_for_modeling']);self.assertEqual(self.payload['release_status'],'ready')
        self.assertEqual(len(self.payload['sources']),21);self.assertNotIn('raw_inputs',self.payload['source_audit']);self.assertEqual(self.payload['source_audit']['operational_roster']['district_minus_reported_operational_enrollment'],0)

    def test_invalid_destination_and_corrupt_payload_never_reach_shared_writer(self):
        with mock.patch.object(cobb,'prepare_snapshot',side_effect=AssertionError('Never import invalid evidence')):
            with self.assertRaises(ValueError):cobb.prepare(self.database,Path('/private/tmp/outside-cobb'))
            with tempfile.TemporaryDirectory(prefix='bad-payload-',dir=WORK)as t:
                path=Path(t)/'bad.json';d=copy.deepcopy(self.payload);d['schools'].pop();path.write_text(json.dumps(d))
                with self.assertRaises(ValueError):cobb.prepare(self.database,self.output,path)

    def test_two_normalized_builds_and_private_prepares_repeat_all_rows_and_export_bytes(self):
        with tempfile.TemporaryDirectory(prefix='normalized-',dir=WORK)as t:
            a,b=Path(t)/'one.json',Path(t)/'two.json';cobb.extract(a);cobb.extract(b);self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(a.read_bytes(),cobb.EXTRACT.read_bytes())
        with closing(connect(self.database))as db:first=rows(db)
        files={p.name:p.read_bytes()for p in self.output.glob('*.json')};run_prepared(cobb.prepare,self.database,self.output)
        with closing(connect(self.database))as db:self.assertEqual(first,rows(db))
        self.assertEqual(files,{p.name:p.read_bytes()for p in self.output.glob('*.json')})

    def test_standalone_empty_namespace_requires_complete_current_evidence_before_sql(self):
        bad=copy.deepcopy(self.payload);bad['schools'][0]['income']+=.1
        numerical=copy.deepcopy(self.numerical);numerical['models'][0]['coefficients']['slope']+=.1
        destination=WORK/'must-not-create.sqlite';self.assertFalse(destination.exists())
        with mock.patch.object(cobb,'connect',side_effect=AssertionError('No SQL for invalid evidence')):
            with self.assertRaises(ValueError):cobb.validate_existing_namespace(bad,destination,self.numerical,cobb.EXTRACT)
            with self.assertRaises(ValueError):cobb.validate_existing_namespace(self.payload,destination,numerical,cobb.EXTRACT)
            read=Path.read_bytes
            def missing(path):
                if path==cobb.model_audit.ROSTER:raise FileNotFoundError('Linked whole source missing')
                return read(path)
            with mock.patch.object(Path,'read_bytes',missing),self.assertRaises(FileNotFoundError):cobb.validate_existing_namespace(self.payload,destination,self.numerical,cobb.EXTRACT)
        self.assertFalse(destination.exists())

if __name__=='__main__':unittest.main()

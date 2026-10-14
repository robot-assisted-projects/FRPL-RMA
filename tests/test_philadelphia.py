import copy
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from database import connect
import state_snapshot
import prepare_philadelphia as philadelphia

TABLES=['dataset','source','assessment_definition','economic_definition','school','economic_observation','assessment_observation','model_run','model_result']
WORK=ROOT/'data/build/philadelphia-integration-implementation'

def rows(db):return {table:[tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')] for table in TABLES}

def seed_other(db,key):
    db.execute("INSERT INTO dataset VALUES ('other-pa','PA','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-pa','other.json','https://example.test/source',?,'2025-01-01')",('1'*64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','PA','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-pa',?,'Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)",(key,))
    db.execute("INSERT INTO economic_observation VALUES ('other-pa',?,2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)",(key,))
    db.execute("INSERT INTO assessment_observation VALUES ('other-pa',?,'other-assessment','math',40,100,'reported','{}','100','other-source',1)",(key,))
    db.execute("INSERT INTO model_run VALUES ('other-model','other-pa','other-assessment','math','keep-method',?,'{}')",('2'*64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-pa',?,40,45,-1,-2,0)",(key,))

def run_prepared(operation,*args):
    handles=[];original=state_snapshot.connect
    def tracked(path):
        handle=original(path);handles.append(handle);return handle
    try:
        with mock.patch.object(state_snapshot,'connect',side_effect=tracked):return operation(*args)
    finally:
        for handle in handles:handle.close()


class PhiladelphiaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True)
        cls.roster,cls.numerical=philadelphia.load_inputs()
        cls.payload=json.loads(philadelphia.EXTRACT.read_text());cls.expected=philadelphia.build_snapshot(cls.roster,cls.numerical)
        cls.profiles={s['id']:s for s in cls.payload['schools']}
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.database=Path(cls.sandbox.name)/'database.sqlite';cls.output=Path(cls.sandbox.name)/'output'
        with closing(connect(cls.database)) as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db,cls.payload['schools'][0]['id']);db.commit();cls.old_rows=rows(db)
        run_prepared(philadelphia.prepare,cls.database,cls.output)

    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def guarded(self,operation,*args):
        # Namespace probes reuse already-verified scientific expectations; the
        # ordinary validator still freshly checks all complete linked evidence.
        with mock.patch.object(philadelphia,'load_inputs',return_value=(self.roster,self.numerical)),mock.patch.object(philadelphia,'build_snapshot',return_value=self.expected):
            return operation(*args)

    def test_new_counted_release_is_separate_from_false_historical_audits_and_full_raw_store(self):
        philadelphia.validate(self.payload,self.expected)
        self.assertEqual((self.payload['dataset'],self.payload['region']),('pa-philadelphia-2025','philadelphia'))
        self.assertEqual(len(self.payload['schools']),162);self.assertEqual(len(self.payload['sources']),15)
        self.assertTrue(self.payload['approved_for_source']);self.assertTrue(self.payload['approved_for_modeling'])
        self.assertFalse(self.roster['approved_for_source']);self.assertFalse(self.numerical['approved_for_modeling'])
        self.assertFalse(self.payload['cohorts'][0]['allow_point_only'])
        basis=self.payload['source_audit']['release_basis'];self.assertTrue(basis['all_model_members_have_conditional_intervals'])
        self.assertEqual(len(self.payload['source_audit']['retained_scope_exclusions']),59)
        self.assertEqual(self.payload['source_audit']['retained_outside_source_profiles'][0]['school_id'],'126515001-000009999')
        self.assertNotIn('raw_inputs',self.payload)
        self.assertIn('not a paired',philadelphia.COUNT_NOTE)

    def test_complete_canonical_current_history_counts_and_all486_conditional_results(self):
        self.guarded(philadelphia.validate_canonical,self.payload,self.database,self.numerical)
        self.guarded(philadelphia.validate_exports,self.payload,self.output,self.numerical)
        exported=json.loads((self.output/'schools.json').read_text());history=json.loads((self.output/'history.json').read_text())
        current={s['id']:s for s in exported['schools']};records={r['school_id']:r for r in history['records']}
        with closing(connect(self.database)) as db:
            counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0]-len(self.old_rows[table]) for table in TABLES}
            self.assertEqual(counts,dict(dataset=1,source=16,assessment_definition=1,economic_definition=1,school=162,economic_observation=162,assessment_observation=324,model_run=3,model_result=486))
            self.assertEqual(db.execute('SELECT min(tested) FROM assessment_observation WHERE dataset_id=?',(philadelphia.DATASET,)).fetchone()[0],42)
        for model in self.numerical['models']:
            for result in model['results']:
                metric=current[result['school_id']]['metrics'][model['subject']]
                self.assertEqual(metric['tested'],result['valid_scores'])
                for field in ['actual','predicted','residual','leverage','studentized','low','high']:
                    self.assertAlmostEqual(metric[field],result[field],delta=2e-9)
                self.assertEqual(metric,records[result['school_id']]['subjects'][model['subject']])
        for school in current.values():
            self.assertEqual(school['programs'],['Unclassified']);self.assertIsNone(school['latitude']);self.assertIsNone(school['longitude'])

    def test_precise_october_individual_income_and_original_total_scored_fields_dereference(self):
        raw=self.roster['raw_inputs'];index={table:{e['source_row']:e['raw'] for e in raw[table]['records']} for table in ['native_grades','native_income','native_assessment']}
        for school in self.payload['schools']:
            refs=school['identity_raw']['source_refs'];income=index['native_income'][refs['income']['source_row']]
            self.assertEqual((school['enrollment'],school['low_income'],school['income']),(income[5],income[6],100*income[6]/income[5]))
            self.assertEqual(school['income_raw']['individual_income']['published_proportion'],income[7])
            for subject,value in school['outcomes'].items():
                native=index['native_assessment'][value['source_row']]
                self.assertEqual(native[6:9],[philadelphia.model_audit.SUBJECT_LABELS[subject],'All Students','Total'])
                self.assertEqual(value['proficiency'],float(native[14]));self.assertEqual(value['tested'],native[9])
                self.assertIs(type(value['raw_tested']),int);self.assertTrue(value['valid_score_evidence']['verified'])
                self.assertEqual(value['raw']['source_refs'],refs['outcomes'][subject])
        jenks=self.profiles['126515001-000007227']
        self.assertEqual(jenks['ncessch'],'421899003644');self.assertEqual(jenks['identity_raw']['native_school_id'],'PA-126515001-7227')
        self.assertNotIn('126515001-000009999',self.profiles);self.assertNotIn('126515001-000006768',self.profiles)

    def test_combined_two_count_variance_and_unbounded_expectations_survive_export(self):
        exported={s['id']:s for s in json.loads((self.output/'schools.json').read_text())['schools']}
        for model in self.numerical['models']:
            for result in model['results']:
                if model['subject']=='combined':
                    school=self.profiles[result['school_id']];self.assertEqual(result['valid_scores'],min(v['tested'] for v in school['outcomes'].values()))
        self.assertGreater(exported['126515001-000003649']['metrics']['reading']['predicted'],100)
        self.assertGreater(exported['126515001-000005186']['metrics']['reading']['predicted'],100)
        self.assertEqual(exported['126515001-000007227']['metrics']['combined']['tested'],112)
        self.assertGreater(exported['126515001-000007227']['metrics']['combined']['studentized'],4.4)

    def test_repeated_private_prepare_preserves_shared_native_identity_and_all_nine_prior_tables(self):
        before_files={p.name:p.read_bytes() for p in self.output.glob('*.json')}
        with closing(connect(self.database)) as db:first=rows(db)
        self.guarded(run_prepared,philadelphia.prepare,self.database,self.output)
        with closing(connect(self.database)) as db:
            self.assertEqual(first,rows(db))
            for table,old in self.old_rows.items():
                current=rows(db)[table];self.assertTrue(all(record in current for record in old),table)
        self.assertEqual(before_files,{p.name:p.read_bytes() for p in self.output.glob('*.json')})

    def test_all_nine_foreign_namespace_owners_reject_before_any_import_write(self):
        target=philadelphia.DATASET
        attacks={
            'dataset':f"INSERT INTO dataset VALUES ('{target}:ghost','PA','Other','Other','ready')",
            'source':f"INSERT INTO source SELECT id||':ghost','other-pa',path,url,sha256,imported_at FROM source WHERE id='{target}:extract'",
            'assessment_definition':f"INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE '{target}:%'",
            'economic_definition':f"INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='{target}:income'",
            'school':f"UPDATE school SET source_id='{target}:extract' WHERE dataset_id='other-pa'",
            'economic_observation':f"UPDATE economic_observation SET definition_id='{target}:income' WHERE dataset_id='other-pa'",
            'assessment_observation':f"UPDATE assessment_observation SET source_id='{target}:extract' WHERE dataset_id='other-pa'",
            'model_run':f"UPDATE model_run SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE '{target}:%') WHERE dataset_id='other-pa'",
            'model_result':f"UPDATE model_result SET dataset_id='{target}' WHERE dataset_id='other-pa'"}
        with tempfile.TemporaryDirectory(prefix='namespace-',dir=WORK) as folder:
            wrong=Path(folder)/'wrong.sqlite'
            for table,sql in attacks.items():
                with closing(connect(self.database)) as original,closing(connect(wrong)) as db:
                    original.backup(db);db.execute(sql);db.commit();before=rows(db)
                with self.subTest(table=table),self.assertRaises(ValueError):self.guarded(philadelphia.validate_existing_namespace,self.payload,wrong,self.numerical,philadelphia.EXTRACT)
                with self.subTest(prewrite=table),mock.patch.object(philadelphia,'prepare_snapshot',side_effect=AssertionError('No writes before namespace rejection')),self.assertRaises(ValueError):
                    self.guarded(philadelphia.prepare,wrong,self.output)
                with closing(connect(wrong)) as db:self.assertEqual(before,rows(db))

    def test_normalized_count_interval_scope_identity_and_approval_repins_fail_closed(self):
        mutations=[lambda p:p['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment'),
            lambda p:p['schools'][0]['outcomes']['math'].update(tested=42.),lambda p:p['schools'][0]['outcomes']['math']['raw'].update(interval_availability=False),
            lambda p:p['cohorts'][0].update(allow_point_only=True),lambda p:p['schools'][0].update(ncessch='421899099999'),
            lambda p:p['schools'][0]['identity_raw'].update(native_school_id='PA-126515001-9999'),
            lambda p:p['source_audit']['release_basis'].update(historical_audits_approved_for_source=True)]
        for i,mutate in enumerate(mutations):
            payload=copy.deepcopy(self.payload);mutate(payload)
            payload['selection']['sha256']=philadelphia.roster_audit.fingerprint({k:v for k,v in payload['selection'].items() if k!='sha256'})
            with self.subTest(i=i),self.assertRaises(ValueError):philadelphia.validate(payload,self.expected)

    def test_current_cached_policy_and_public_fingerprint_repins_reject_before_sql_or_output(self):
        policy=copy.deepcopy(philadelphia.model_audit.POLICY);policy['intervals']='Use only own-school variance and independent covariance'
        for owner,field,value in [(philadelphia,'COUNT_NOTE','Use enrollment'),(philadelphia,'NUMERICAL_BYTES',1707603.),
                (philadelphia.model_audit,'POLICY',policy),(philadelphia.model_audit,'COUNT_FIELD',27),
                (philadelphia.model_audit,'INTERVAL_MULTIPLIER',2),(philadelphia.model_audit,'MIN_VALID_SCORES',10),
                (philadelphia.model_audit,'ROSTER_SHA','0'*64)]:
            with self.subTest(field=field),mock.patch.object(owner,field,value):
                with self.assertRaises(ValueError):philadelphia.validate(self.payload,self.expected)
                with mock.patch.object(philadelphia,'connect',side_effect=AssertionError('No SQL before policy guard')),mock.patch.object(philadelphia,'prepare_snapshot',side_effect=AssertionError('No output before policy guard')),self.assertRaises(ValueError):philadelphia.prepare(self.database,self.output)
        with mock.patch.object(philadelphia,'COUNT_NOTE','Use enrollment'):
            repin=philadelphia.roster_audit.fingerprint(philadelphia.adapter_contract())
            with mock.patch.object(philadelphia,'ADAPTER_CONTRACT_SHA',repin),self.assertRaises(ValueError):philadelphia.validate(self.payload,self.expected)
        with mock.patch.object(philadelphia.model_audit,'POLICY',policy),mock.patch.object(philadelphia.model_audit,'NUMERIC_POLICY_SHA',philadelphia.roster_audit.fingerprint(policy)),self.assertRaises(ValueError):philadelphia.validate(self.payload,self.expected)

    def test_cached_validation_requires_all_six_current_artifacts_and_secondary_source(self):
        original=Path.read_bytes
        paths=[philadelphia.model_audit.ROSTER,philadelphia.model_audit.SOURCE_CODE,philadelphia.model_audit.SOURCE_TESTS,
            philadelphia.model_audit.OUTPUT,ROOT/'scripts/audit_philadelphia_models.py',ROOT/'tests/test_philadelphia_models.py',ROOT/'data/source/pennsylvania.json']
        for path in paths:
            def changed(p):return b'changed' if p==path else original(p)
            with self.subTest(path=path),mock.patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):philadelphia.validate(self.payload,self.expected)
        def absent(p):
            if p==philadelphia.model_audit.ROSTER:raise FileNotFoundError('Complete source unavailable')
            return original(p)
        with mock.patch.object(Path,'read_bytes',absent),self.assertRaises(FileNotFoundError):philadelphia.validate(self.payload,self.expected)

    def test_static_count_interval_nonfinite_and_directory_corruption_reject(self):
        originals={p.name:p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='static-',dir=WORK) as name:
            folder=Path(name);descriptor=json.loads(originals['catalog.json']);descriptor['regions'][0].update(schools=str((folder/'schools.json').relative_to(ROOT)),audit=str((folder/'coverage.json').relative_to(ROOT)))
            originals['catalog.json']=json.dumps(descriptor).encode()
            mutations=[('schools.json',lambda p:p['schools'][0]['metrics']['combined'].update(tested=999999)),
                ('schools.json',lambda p:p['schools'][0]['metrics']['math'].update(low=None)),
                ('schools.json',lambda p:p['schools'][0]['metrics']['math'].update(high=float('nan'))),
                ('schools.json',lambda p:p['schools'].append(copy.deepcopy(p['schools'][0]))),
                ('schools.json',lambda p:p['schools'][0].update(programs=['Selective'])),
                ('history.json',lambda p:p['records'][0]['subjects']['reading'].update(low=0)),
                ('coverage.json',lambda p:p['source_audit']['release_basis'].update(all_models_point_only=True)),
                ('catalog.json',lambda p:p['regions'][0].update(statewide=True))]
            for filename,mutate in mutations:
                for file,data in originals.items():(folder/file).write_bytes(data)
                payload=json.loads((folder/filename).read_text());mutate(payload);(folder/filename).write_text(json.dumps(payload))
                with self.subTest(filename=filename),self.assertRaises(ValueError):self.guarded(philadelphia.validate_exports,self.payload,folder,self.numerical)

    def test_corrupt_existing_canonical_counts_and_intervals_cannot_be_repaired_by_repeat_import(self):
        with tempfile.TemporaryDirectory(prefix='metric-',dir=WORK) as name:
            wrong=Path(name)/'wrong.sqlite'
            for statement in ["UPDATE assessment_observation SET tested=100 WHERE dataset_id=?", "UPDATE model_result SET low=NULL WHERE dataset_id=?", "UPDATE model_result SET predicted=100 WHERE dataset_id=?"]:
                with closing(connect(self.database)) as original,closing(connect(wrong)) as db:
                    original.backup(db);db.execute(statement,(philadelphia.DATASET,));db.commit();before=rows(db)
                with mock.patch.object(philadelphia,'prepare_snapshot',side_effect=AssertionError('No deletion before corruption rejection')),self.assertRaises(ValueError):self.guarded(philadelphia.prepare,wrong,self.output)
                with closing(connect(wrong)) as db:self.assertEqual(before,rows(db))


if __name__=='__main__':unittest.main()

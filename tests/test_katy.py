import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from database import connect
from state_snapshot import import_snapshot, prepare_snapshot
import state_snapshot
import prepare_katy as katy

TABLES = ['dataset', 'source', 'assessment_definition', 'economic_definition', 'school',
          'economic_observation', 'assessment_observation', 'model_run', 'model_result']
WORK = ROOT / 'data/build/katy-integration-implementation'
MISSING_INCOME = set()


def rows(db):
    return {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in TABLES}


def prior_rows(db):
    return {table: [r for r in records if not any(isinstance(v, str) and
            (v == katy.DATASET or v.startswith(katy.DATASET + ':')) for v in r)]
            for table, records in rows(db).items()}


def seed_other(db):
    """Same native school identity in an independent same-state release."""
    db.execute("INSERT INTO dataset VALUES ('other-tx','TX','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-tx','other.json','https://example.test/source',?,'2025-01-01')", ('1' * 64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','TX','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-tx','482517002806','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-tx','482517002806',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-tx','482517002806','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-tx','other-assessment','math','keep-method',?,'{}')", ('2' * 64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-tx','482517002806',40,45,-1,-2,0)")


def run_prepared(operation, *args):
    """Own helper connections while preserving its ordinary transaction contexts."""
    handles = []
    original = state_snapshot.connect
    def tracked(path):
        handle = original(path)
        handles.append(handle)
        return handle
    try:
        with mock.patch.object(state_snapshot, 'connect', side_effect=tracked):
            return operation(*args)
    finally:
        for handle in handles:
            handle.close()


class KatyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        cls.roster, cls.numerical = katy.load_inputs()
        cls.payload = json.loads(katy.EXTRACT.read_text())
        cls.expected = katy.build_snapshot(cls.roster, cls.numerical)
        cls.links = {r['school_id']: r for r in cls.roster['roster_links']}
        cls.profiles = {r['id']: r for r in cls.payload['schools']}
        cls.native = {r['source_row']: r for r in cls.roster['raw_inputs']['assessment']['records']}
        cls.sandbox = tempfile.TemporaryDirectory(prefix='test-', dir=WORK)
        cls.output = Path(cls.sandbox.name) / 'output'
        cls.database = Path(cls.sandbox.name) / 'schools.sqlite'
        with closing(connect(cls.database)) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db); db.commit()
        run_prepared(katy.prepare, cls.database, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.cleanup()


    def test_repeat_import_preserves_shared_identity_all_nine_tables(self):
        with closing(connect(':memory:')) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db)
            before = prior_rows(db)
            import_snapshot(db, self.payload, katy.EXTRACT); first = rows(db)
            import_snapshot(db, self.payload, katy.EXTRACT)
            self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            additions = {t: len(rows(db)[t]) - len(before[t]) for t in TABLES}
            self.assertEqual(additions, dict(dataset=1, source=22, assessment_definition=1,
                economic_definition=1, school=65, economic_observation=65,
                assessment_observation=130, model_run=0, model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',
                                       (katy.DATASET,)).fetchone()[0], 128)
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',
                                       (katy.DATASET,)).fetchone()[0], 0)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
    def test_canonical_proxies_orphans_raw_drift_and_foreign_namespace_rejected(self):
        corruptions = [
            "UPDATE model_result SET studentized=99 WHERE dataset_id='tx-katy-2025' AND school_id='482517002806'",
            "UPDATE assessment_observation SET tested=893 WHERE dataset_id='tx-katy-2025' AND school_id='482517002807'",
            "UPDATE assessment_observation SET proficiency=95,status='reported' WHERE dataset_id='tx-katy-2025' AND school_id='482517008823' AND subject='math'",
            "UPDATE assessment_observation SET proficiency=NULL,status='suppressed_or_not_reported' WHERE dataset_id='tx-katy-2025' AND school_id='482517002807'",
            "UPDATE economic_observation SET percentage=0,low_income=0 WHERE dataset_id='tx-katy-2025' AND school_id='482517002807'",
            "UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='tx-katy-2025' AND school_id='482517002806'",
            "UPDATE school SET name='Wrong school' WHERE dataset_id='tx-katy-2025' AND school_id='482517002806'",
            "UPDATE assessment_observation SET raw_value='{}' WHERE dataset_id='tx-katy-2025' AND school_id='482517002807'",
            "INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='tx-katy-2025' AND school_id='482517002806'",
            "INSERT INTO model_run SELECT id||':ghost',dataset_id,definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='tx-katy-2025' AND subject='math'",
            "INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='tx-katy-2025:income'",
            "INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE 'tx-katy-2025:%'",
            "INSERT INTO model_result VALUES ('other-model','tx-katy-2025','482517002807',9.4,90,1,NULL,NULL)",
            "INSERT INTO source SELECT id||':ghost','other-tx',path,url,sha256,imported_at FROM source WHERE id='tx-katy-2025:extract'",
            "INSERT INTO model_run SELECT id||':ghost','other-tx',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='tx-katy-2025' AND subject='math'",
            "UPDATE school SET source_id='tx-katy-2025:extract' WHERE dataset_id='other-tx'",
            "UPDATE economic_observation SET definition_id='tx-katy-2025:income' WHERE dataset_id='other-tx'",
            "UPDATE economic_observation SET source_id='tx-katy-2025:extract' WHERE dataset_id='other-tx'",
            "UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE 'tx-katy-2025:%') WHERE dataset_id='other-tx'",
            "UPDATE assessment_observation SET source_id='tx-katy-2025:extract' WHERE dataset_id='other-tx'",
        ]
        with tempfile.TemporaryDirectory(prefix='corrupt-db-', dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.sqlite'
            for sql in corruptions:
                with closing(connect(self.database)) as source, closing(connect(wrong)) as db:
                    source.backup(db); db.execute(sql); db.commit()
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    katy.validate_canonical(self.payload, wrong, self.numerical)
    def test_static_ghosts_counts_income_promotion_and_nonfinite_metrics_rejected(self):
        originals = {p.name: p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='corrupt-export-', dir=WORK) as folder:
            folder = Path(folder); descriptor = json.loads(originals['catalog.json'])
            descriptor['regions'][0].update(schools=str((folder / 'schools.json').relative_to(ROOT)),
                audit=str((folder / 'coverage.json').relative_to(ROOT)))
            originals['catalog.json'] = json.dumps(descriptor).encode()
            for filename, mutate in [
                ('schools.json', lambda d: d['models'].update(HS=d['models']['ES'])),
                ('schools.json', lambda d: d['models']['ES']['math'].update(n=64.)),
                ('schools.json', lambda d: d['models']['ES']['math'].update(slope=float('nan'))),
                ('schools.json', lambda d: d['schools'].append(copy.deepcopy(d['schools'][0]))),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(studentized=99.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(tested=False)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(low=0.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(cohort_n=64.)),
                ('schools.json', lambda d: d['schools'][0].update(latitude=0.)),
                ('schools.json', lambda d: d['schools'][0].update(hidden_model={})),
                ('schools.json', lambda d: d.update(hidden_history=[])),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '482517002807').update(income=0.)),
                ('schools.json', lambda d: d['schools'][0]['exclusions'].update(math='Invented exclusion')),
                ('schools.json', lambda d: d['schools'][0]['metrics'].pop('math')),
                ('history.json', lambda d: d['models'][0].update(intercept=-99.)),
                ('history.json', lambda d: d['records'][0].update(income_year=2024)),
                ('history.json', lambda d: d['records'][0]['subjects'].update(extra={})),
                ('history.json', lambda d: d['records'][0].update(raw_count_proxy=100)),
                ('history.json', lambda d: d.update(ghost_records=[])),
                ('coverage.json', lambda d: d['cohorts']['grade']['eligible'].update(combined=79)),
                ('coverage.json', lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].append({'school_id':'482517008625'})),
                ('catalog.json', lambda d: d['regions'][0].update(name='Statewide', statewide=True)),
            ]:
                for name, content in originals.items(): (folder / name).write_bytes(content)
                changed = json.loads((folder / filename).read_text()); mutate(changed)
                (folder / filename).write_text(json.dumps(changed))
                with self.subTest(filename=filename, mutate=mutate), self.assertRaises(ValueError):
                    katy.validate_exports(self.payload, folder, self.numerical)
    def test_offline_extract_repeatability_keeps_historical_pins_immutable(self):
        paths = [katy.model_audit.ROSTER, katy.model_audit.OUTPUT,
                 ROOT / 'scripts/audit_katy.py', ROOT / 'scripts/audit_katy_models.py',
                 ROOT / 'tests/test_katy_audit.py', ROOT / 'tests/test_katy_models.py']
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-repeat-', dir=WORK) as folder:
            first, second = Path(folder) / 'one.json', Path(folder) / 'two.json'
            with mock.patch.object(katy.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original archive access')):
                katy.extract(first); katy.extract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), katy.EXTRACT.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(hashlib.sha256(katy.model_audit.ROSTER.read_bytes()).hexdigest(), katy.model_audit.ROSTER_SHA)
        self.assertEqual(hashlib.sha256(katy.model_audit.OUTPUT.read_bytes()).hexdigest(), katy.NUMERICAL_SHA)


    def test_exact_searchable_cohort_compact_links_and_separate_release_approval(self):
        katy.validate(self.payload, self.expected)
        self.assertEqual(self.payload['dataset'], 'tx-katy-2025')
        self.assertEqual(self.payload['state'], {'id': 'TX', 'name': 'Texas'})
        self.assertEqual((self.payload['region'], self.payload['region_name']), ('katy', 'Katy ISD'))
        self.assertIs(self.payload['statewide'], False)
        self.assertIs(self.payload['approved_for_source'], True)
        self.assertIs(self.payload['approved_for_modeling'], True)
        self.assertEqual(len(self.profiles), 65)
        self.assertEqual(set(self.profiles), set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        self.assertEqual(len(self.payload['sources']), 21)
        for key, count in [('high_school_configuration_ids',11),('mixed_configuration_ids',1),
                           ('primary_configuration_ids',0),('nonoperational_school_ids',2)]:
            self.assertEqual(len(self.numerical['frozen_population'][key]), count)
            self.assertFalse(set(self.profiles).intersection(self.numerical['frozen_population'][key]))
        for audit in [self.roster, self.numerical]:
            self.assertIs(audit['approved_for_source'], False)
            self.assertIs(audit['approved_for_modeling'], False)
        source = self.payload['source_audit']
        reference = source['complete_source_reference']
        self.assertEqual((reference['complete_original_record_count'], reference['complete_original_cell_count']), (8905,178885))
        self.assertEqual(reference['sha256'], katy.model_audit.ROSTER_SHA)
        self.assertNotIn('retained_raw_inputs', source)
        self.assertNotIn('raw_inputs', self.payload)
        self.assertEqual(len(source['retained_scope_exclusions']),16)
        self.assertIs(source['release_basis']['ten_valid_scored_floor_certified'], False)
        selection = dict(self.payload['selection']); digest = selection.pop('sha256')
        self.assertEqual(digest, katy.roster_audit.fingerprint(selection))
        self.assertFalse(source['count_definition_status']['ten_valid_scored_floor_certified'])
        self.assertTrue(all(not c['intervals']['available_for_entire_model'] for c in self.numerical['models']))

    def test_every_original_row_field_income_and_whole_rate_reference_reconciles(self):
        raw = self.roster['raw_inputs']
        tables = {t: {r['source_row']: r for r in raw[t]['records']} for t in ['directory', 'ref', 'stud', 'assessment']}
        for profile in self.payload['schools']:
            link = self.links[profile['id']]; refs = profile['identity_raw']['source_refs']
            ccd = tables['directory'][refs['directory_source_row']]['raw']
            student = tables['stud'][refs['native_source_rows']['stud']]['raw']
            assessment = tables['assessment'][refs['native_source_rows']['assessment']]['raw']
            self.assertEqual((ccd['NCESSCH'], ccd['LEAID']), (profile['id'], '4825170'))
            self.assertEqual(ccd['ST_LEAID'], 'TX-101914')
            self.assertEqual(student['CAMPUS'], profile['identity_raw']['native_school_id'])
            self.assertEqual(student['DISTRICT'], '101914')
            self.assertEqual(profile['enrollment'], int(student['CPNTALLC']))
            self.assertEqual(profile['low_income'], int(student['CPNTECOC']))
            self.assertEqual(profile['income'], 100 * int(student['CPNTECOC']) / int(student['CPNTALLC']))
            self.assertEqual(profile['income_raw']['individual_income'], link['income'])
            self.assertEqual(profile['identity_raw']['native_enrolled_scope'], 'grade-school')
            for subject in ['math', 'reading']:
                outcome = profile['outcomes'][subject]; fields = katy.roster_audit.FIELDS[subject]
                self.assertEqual(outcome['raw']['original_subject_triplet'], {f: assessment[f] for f in fields})
                self.assertEqual(outcome['raw']['original_rate_field'], fields[2])
                self.assertEqual(outcome['proficiency'], link['subjects'][subject]['published_rate'])
                self.assertIsNone(outcome['tested']); self.assertIsNone(outcome['valid_score_evidence'])
                self.assertIsNone(outcome['raw_tested']); self.assertIsNone(outcome['raw']['sampling_variance'])
                self.assertIs(outcome['raw']['ten_valid_scored_floor_certified'], False)
        self.assertFalse({'482517008625'}.intersection(self.profiles))
        self.assertEqual(self.numerical['frozen_population']['operational_without_native_school_ids'],['482517008625','482517008629'])
        self.assertEqual(set(self.numerical['frozen_population']['mixed_configuration_ids']).intersection(self.profiles),set())

    def test_individual_income_counts_are_valid_while_assessment_counts_remain_held(self):
        r = self.payload['source_audit']['enrollment_reconciliation']
        self.assertEqual((r['ccd_lea_reported'], r['ccd_operational_school_sum'], r['native_campus_sum']), (96111,96111,96098))
        self.assertEqual(r['native_peims_membership_sum'],95919)
        self.assertEqual(r['native_economic_disadvantage_sum'],41024)
        self.assertEqual(len(r['native_enrollment_membership_differences']),48)
        changed = [p for p in self.payload['schools'] if p['identity_raw']['native_peims_membership']['count'] != p['enrollment']]
        self.assertTrue(changed)
        self.assertTrue(all(p['income'] == 100*p['low_income']/p['enrollment'] for p in changed))
        self.assertIn('All valid-score counts', katy.COUNT_NOTE)
        for term in ['October 25, 2024', 'codes 01/02/99', 'CEP', 'Provision 2', 'January 16, 2025']:
            self.assertIn(term, self.payload['income_definition']['definition'])

    def test_all_192_canonical_current_and_history_metrics_match_numerical_audit(self):
        self.assertEqual(katy.validate_canonical(self.payload, self.database, self.numerical),
                         {'schools':65,'observations':130,'models':3,'results':192})
        self.assertEqual(katy.validate_exports(self.payload, self.output, self.numerical),
                         {f'katy-2025-ES-{s}':64 for s in katy.model_audit.SUBJECTS})
        served = json.loads((self.output/'schools.json').read_text())
        selected = {p['id']: p for p in served['schools']}
        for key, school in selected.items():
            if self.profiles[key]['outcomes']['math']['proficiency']is None:
                self.assertEqual(school['metrics'],{});self.assertEqual(set(school['exclusions']),{'math','reading','combined'})
            else:
                self.assertEqual(set(school['metrics']),{'math','reading','combined'});self.assertEqual(school['exclusions'],{})
            self.assertEqual((school['program'], school['latitude'], school['longitude']), ('Unclassified', None, None))
            self.assertTrue(all(v['tested'] is None and v['low'] is None and v['high'] is None and 'variance' not in v for v in school['metrics'].values()))
        self.assertGreater(selected['482517010769']['metrics']['combined']['studentized'],2.)
        for model in self.numerical['models']:
            for row in model['results']:
                self.assertAlmostEqual(selected[row['school_id']]['metrics'][model['subject']]['predicted'],row['predicted'],delta=2e-10)
        with closing(connect(self.database)) as db:
            self.assertEqual({t: len(rows(db)[t])-1 for t in TABLES}, dict(dataset=1,source=22,
                assessment_definition=1,economic_definition=1,school=65,economic_observation=65,
                assessment_observation=130,model_run=3,model_result=192))

    def test_combined_owns_residual_scale_and_studentization_despite_linear_coefficients(self):
        models = {m['subject']:m for m in self.numerical['models']}
        combined = models['combined']
        for k in ['intercept', 'slope']:
            self.assertAlmostEqual(combined['coefficients'][k], (models['math']['coefficients'][k]+models['reading']['coefficients'][k])/2, places=11)
        self.assertTrue(any(abs(c['studentized']-(m['studentized']+r['studentized'])/2) > .01
            for c,m,r in zip(combined['results'], models['math']['results'], models['reading']['results'])))
        for row in combined['inputs']:
            self.assertEqual(row['outcome_pct'], (row['outcome_by_subject']['math']+row['outcome_by_subject']['reading'])/2)
        served = json.loads((self.output/'schools.json').read_text())['models']['ES']['combined']
        self.assertAlmostEqual(served['intercept'],combined['coefficients']['intercept'],places=10)
        self.assertAlmostEqual(served['slope'],combined['coefficients']['slope'],places=10)
        self.assertAlmostEqual(served['r2'],combined['coefficients']['r2'],places=10)

    def test_normalized_mutations_and_direct_evidence_drift_are_rejected(self):
        mutations = [
            lambda d:d['schools'].pop(), lambda d:d['schools'][0].update(id='101914033'),
            lambda d:d['schools'][0]['identity_raw'].update(native_school_id='101912001'),
            lambda d:d['schools'][0]['identity_raw']['source_refs'].update(directory_source_row=1.),
            lambda d:d['schools'][0]['identity_raw']['ccd_flags'].update(charter='Yes'),
            lambda d:d['schools'][0]['income_raw']['individual_income']['raw'].update(CPNTALLC='1'),
            lambda d:d['schools'][0]['outcomes']['math']['raw'].update(sampling_variance=0.),
            lambda d:d['schools'][0]['outcomes']['reading'].update(proficiency=99.),
            lambda d:d['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment'),
            lambda d:d['schools'][0].update(income=True), lambda d:d['schools'][0].update(low_income=0),
            lambda d:d['schools'][0]['outcomes']['math'].update(proficiency=0.),
            lambda d:d['cohorts'][0].update(allow_point_only=False),
            lambda d:d['cohorts'][0].update(assessment='All grades'),
            lambda d:d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].append({'school_id':'482517008625'}),
            lambda d:d['source_audit']['retained_scope_exclusions'].clear(),
            lambda d:d['source_audit']['complete_source_reference'].update(complete_original_cell_count=59450.),
            lambda d:d['source_audit']['release_basis'].update(historical_audits_approved_for_modeling=0),
            lambda d:d['source_audit']['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['sources']['numerical_audit'].update(sha256='0'*64),
            lambda d:d['selection']['directory_school_ids'].pop(),
            lambda d:d.update(statewide=0), lambda d:d.update(approved_for_modeling=1),
            lambda d:d['schools'][0].update(latitude=0.), lambda d:d['methodology']['details'].clear()]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.payload);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):katy.validate(changed,self.expected)
        for kind in ['source','numerical','bool']:
            source,numeric=copy.deepcopy(self.roster),copy.deepcopy(self.numerical)
            if kind=='source':source['roster_links'].pop()
            elif kind=='numerical':numeric['models'][0]['results'][0]['studentized']+=1.
            else:numeric['approved_for_source']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):katy.build_snapshot(source,numeric)

    def test_cached_normalized_validation_checks_missing_changed_blobs_and_all_pins(self):
        original = Path.read_bytes
        for path in [katy.model_audit.ROSTER, katy.model_audit.OUTPUT]:
            for bad in [b'{}', None]:
                def read(p):
                    if p==path:
                        if bad is None:raise FileNotFoundError('Linked complete evidence missing')
                        return bad
                    return original(p)
                with self.subTest(path=path,bad=bad),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):
                    katy.validate(self.payload,self.expected)
        for owner,keys in [(katy,['NUMERICAL_SHA','NUMERICAL_CODE_SHA','NUMERICAL_TESTS_SHA']),
                           (katy.model_audit,['ROSTER_SHA','SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA'])]:
            for key in keys:
                with self.subTest(key=key),mock.patch.object(owner,key,'0'*64),self.assertRaises(ValueError):
                    katy.validate(self.payload,self.expected)

    def test_current_policy_metadata_and_coherent_public_repins_reject_before_database_access(self):
        owner=katy;numeric=katy.model_audit
        policy=copy.deepcopy(numeric.POLICY);policy['models']='Drop influential schools and infer causal effectiveness'
        bad_adapter_n={'math':103,'reading':64,'combined':64}
        for module,key,bad in [(numeric,'POLICY',policy),(numeric,'MIN_SCHOOLS',30.),
            (numeric,'SUBJECTS',['math','combined']),(numeric,'ASSESSMENT','Foreign assessment'),
            (owner,'MODEL_SCOPE','Statewide pooled model'),(owner,'COUNT_NOTE','Counts certified'),
            (owner,'EXPECTED_N',bad_adapter_n),(owner,'NUMERICAL_BYTES',owner.NUMERICAL_BYTES*1.)]:
            with self.subTest(key=key),mock.patch.object(module,key,bad),self.assertRaises(ValueError):
                owner.validate(self.payload,self.expected)
            with self.subTest(prewrite=key),mock.patch.object(module,key,bad),mock.patch.object(owner,'connect',side_effect=AssertionError('No database access')),self.assertRaises(ValueError):
                owner.prepare(self.database,self.output)
        with mock.patch.object(owner,'EXPECTED_N',bad_adapter_n):
            resigned=owner.roster_audit.fingerprint(owner.adapter_contract())
            with mock.patch.object(owner,'ADAPTER_CONTRACT_SHA',resigned),self.assertRaises(ValueError):owner.validate(self.payload,self.expected)
        with mock.patch.object(numeric,'POLICY',policy):
            resigned=owner.roster_audit.fingerprint(policy)
            with mock.patch.object(numeric,'NUMERIC_POLICY_SHA',resigned),self.assertRaises(ValueError):owner.validate(self.payload,self.expected)

    def test_prepare_repeat_and_rejection_preserve_prior_rows_and_exports_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='repeat-',dir=WORK) as name:
            folder=Path(name);database=folder/'schools.sqlite';output=folder/'output'
            with closing(connect(database)) as db:
                db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit();before=rows(db)
            run_prepared(katy.prepare,database,output)
            first_files={p.name:p.read_bytes() for p in output.glob('*.json')}
            with closing(connect(database)) as db:first=rows(db)
            run_prepared(katy.prepare,database,output)
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})

            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db))
            bad=copy.deepcopy(self.payload);bad['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment')
            path=folder/'bad.json';path.write_text(json.dumps(bad))
            with mock.patch.object(katy,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):katy.prepare(database,output,path)
                with mock.patch.object(katy,'NUMERICAL_SHA','0'*64),self.assertRaises(ValueError):katy.prepare(database,output)
                with self.assertRaises(ValueError):katy.prepare(database,Path('/tmp/katy-output'))
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));db.execute("UPDATE model_result SET studentized=99 WHERE dataset_id='tx-katy-2025'");db.commit();corrupt=rows(db)
            with mock.patch.object(katy,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):katy.prepare(database,output)
            with closing(connect(database)) as db:self.assertEqual(corrupt,rows(db))
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})

    def test_public_normalized_self_repin_and_mutated_builder_expected_reject(self):
        changed=copy.deepcopy(self.payload);changed['schools'][0]['income']+=.1
        with self.assertRaises(ValueError):katy.validate(changed,changed)
        with mock.patch.object(katy,'NORMALIZED_PAYLOAD_SHA',katy.roster_audit.fingerprint(changed)),self.assertRaises(ValueError):katy.validate(changed,changed)
        with self.assertRaises(ValueError):katy.validate(self.payload,changed)
        self.assertEqual(katy.build(),self.payload)

    def test_all_empty_namespace_entry_checks_source_and_payload_before_SQL(self):
        changed=copy.deepcopy(self.payload);changed['source_audit']['count_definition_status']['ten_valid_scored_floor_certified']=True
        for operation in [katy.validate_existing_namespace,katy.validate_canonical]:
            with self.subTest(operation=operation.__name__),mock.patch.object(katy,'connect',side_effect=AssertionError('No SQL before complete source/payload guard')),self.assertRaises(ValueError):operation(changed,WORK/'unused.sqlite',self.numerical,katy.EXTRACT)
        for field in ['RAW_INPUT_SHA','ORIGINAL_SCHEMA_SHA','DEFINITION_INPUT_SHA','ORIGINAL_IDENTITY_SHA']:
            with mock.patch.object(katy.roster_audit,field,'0'*64),mock.patch.object(katy,'connect',side_effect=AssertionError('No SQL before current source guard')),self.assertRaises(ValueError):katy.validate_existing_namespace(self.payload,WORK/'unused.sqlite',self.numerical,katy.EXTRACT)

    def test_masked_alternative_profiles_and_separate_enrollment_denominator_retained(self):
        masked=[s for s in self.payload['schools']if s['outcomes']['math']['proficiency']is None]
        self.assertEqual({s['identity_raw']['native_school_id']for s in masked},{'101914033'})
        served={s['id']:s for s in json.loads((self.output/'schools.json').read_text())['schools']};history={s['school_id']:s for s in json.loads((self.output/'history.json').read_text())['records']}
        for profile in masked:
            self.assertIsNotNone(profile['income']);self.assertEqual(served[profile['id']]['metrics'],{})
            self.assertEqual(history[profile['id']]['subjects'],{})
            self.assertEqual(set(history[profile['id']]['exclusions']),{'math','reading','combined'})
        self.assertIn('CPNTALLC enrollment denominator',katy.INCOME_NOTE)
        self.assertIn('CPETALLC membership',katy.INCOME_NOTE)


if __name__ == '__main__':
    unittest.main()

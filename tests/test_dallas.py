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
import prepare_dallas as dallas

TABLES = ['dataset', 'source', 'assessment_definition', 'economic_definition', 'school',
          'economic_observation', 'assessment_observation', 'model_run', 'model_result']
WORK = ROOT / 'data/build/dallas-integration-implementation'
MISSING_INCOME = set()


def rows(db):
    return {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in TABLES}


def prior_rows(db):
    return {table: [r for r in records if not any(isinstance(v, str) and
            (v == dallas.DATASET or v.startswith(dallas.DATASET + ':')) for v in r)]
            for table, records in rows(db).items()}


def seed_other(db):
    """Same native school identity in an independent same-state release."""
    db.execute("INSERT INTO dataset VALUES ('other-tx','TX','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-tx','other.json','https://example.test/source',?,'2025-01-01')", ('1' * 64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','TX','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-tx','481623000465','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-tx','481623000465',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-tx','481623000465','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-tx','other-assessment','math','keep-method',?,'{}')", ('2' * 64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-tx','481623000465',40,45,-1,-2,0)")


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


class DallasIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        cls.roster, cls.numerical = dallas.load_inputs()
        cls.payload = json.loads(dallas.EXTRACT.read_text())
        cls.expected = dallas.build_snapshot(cls.roster, cls.numerical)
        cls.links = {r['school_id']: r for r in cls.roster['roster_links']}
        cls.profiles = {r['id']: r for r in cls.payload['schools']}
        cls.native = {r['source_row']: r for r in cls.roster['raw_inputs']['assessment']['records']}
        cls.sandbox = tempfile.TemporaryDirectory(prefix='test-', dir=WORK)
        cls.output = Path(cls.sandbox.name) / 'output'
        cls.database = Path(cls.sandbox.name) / 'schools.sqlite'
        with closing(connect(cls.database)) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db); db.commit()
        run_prepared(dallas.prepare, cls.database, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.cleanup()


    def test_repeat_import_preserves_shared_identity_all_nine_tables(self):
        with closing(connect(':memory:')) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db)
            before = prior_rows(db)
            import_snapshot(db, self.payload, dallas.EXTRACT); first = rows(db)
            import_snapshot(db, self.payload, dallas.EXTRACT)
            self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            additions = {t: len(rows(db)[t]) - len(before[t]) for t in TABLES}
            self.assertEqual(additions, dict(dataset=1, source=22, assessment_definition=1,
                economic_definition=1, school=189, economic_observation=189,
                assessment_observation=378, model_run=0, model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',
                                       (dallas.DATASET,)).fetchone()[0], 376)
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',
                                       (dallas.DATASET,)).fetchone()[0], 0)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
    def test_canonical_proxies_orphans_raw_drift_and_foreign_namespace_rejected(self):
        corruptions = [
            "UPDATE model_result SET studentized=99 WHERE dataset_id='tx-dallas-2025' AND school_id='481623000465'",
            "UPDATE assessment_observation SET tested=893 WHERE dataset_id='tx-dallas-2025' AND school_id='481623001279'",
            "UPDATE assessment_observation SET proficiency=95,status='reported' WHERE dataset_id='tx-dallas-2025' AND school_id='481623009196' AND subject='math'",
            "UPDATE assessment_observation SET proficiency=NULL,status='suppressed_or_not_reported' WHERE dataset_id='tx-dallas-2025' AND school_id='481623001279'",
            "UPDATE economic_observation SET percentage=0,low_income=0 WHERE dataset_id='tx-dallas-2025' AND school_id='481623001279'",
            "UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='tx-dallas-2025' AND school_id='481623000465'",
            "UPDATE school SET name='Wrong school' WHERE dataset_id='tx-dallas-2025' AND school_id='481623000465'",
            "UPDATE assessment_observation SET raw_value='{}' WHERE dataset_id='tx-dallas-2025' AND school_id='481623001279'",
            "INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='tx-dallas-2025' AND school_id='481623000465'",
            "INSERT INTO model_run SELECT id||':ghost',dataset_id,definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='tx-dallas-2025' AND subject='math'",
            "INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='tx-dallas-2025:income'",
            "INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE 'tx-dallas-2025:%'",
            "INSERT INTO model_result VALUES ('other-model','tx-dallas-2025','481623001279',9.4,90,1,NULL,NULL)",
            "INSERT INTO source SELECT id||':ghost','other-tx',path,url,sha256,imported_at FROM source WHERE id='tx-dallas-2025:extract'",
            "INSERT INTO model_run SELECT id||':ghost','other-tx',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='tx-dallas-2025' AND subject='math'",
            "UPDATE school SET source_id='tx-dallas-2025:extract' WHERE dataset_id='other-tx'",
            "UPDATE economic_observation SET definition_id='tx-dallas-2025:income' WHERE dataset_id='other-tx'",
            "UPDATE economic_observation SET source_id='tx-dallas-2025:extract' WHERE dataset_id='other-tx'",
            "UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE 'tx-dallas-2025:%') WHERE dataset_id='other-tx'",
            "UPDATE assessment_observation SET source_id='tx-dallas-2025:extract' WHERE dataset_id='other-tx'",
        ]
        with tempfile.TemporaryDirectory(prefix='corrupt-db-', dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.sqlite'
            for sql in corruptions:
                with closing(connect(self.database)) as source, closing(connect(wrong)) as db:
                    source.backup(db); db.execute(sql); db.commit()
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    dallas.validate_canonical(self.payload, wrong, self.numerical)
    def test_static_ghosts_counts_income_promotion_and_nonfinite_metrics_rejected(self):
        originals = {p.name: p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='corrupt-export-', dir=WORK) as folder:
            folder = Path(folder); descriptor = json.loads(originals['catalog.json'])
            descriptor['regions'][0].update(schools=str((folder / 'schools.json').relative_to(ROOT)),
                audit=str((folder / 'coverage.json').relative_to(ROOT)))
            originals['catalog.json'] = json.dumps(descriptor).encode()
            for filename, mutate in [
                ('schools.json', lambda d: d['models'].update(HS=d['models']['ES'])),
                ('schools.json', lambda d: d['models']['ES']['math'].update(n=188.)),
                ('schools.json', lambda d: d['models']['ES']['math'].update(slope=float('nan'))),
                ('schools.json', lambda d: d['schools'].append(copy.deepcopy(d['schools'][0]))),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(studentized=99.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(tested=False)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(low=0.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(cohort_n=188.)),
                ('schools.json', lambda d: d['schools'][0].update(latitude=0.)),
                ('schools.json', lambda d: d['schools'][0].update(hidden_model={})),
                ('schools.json', lambda d: d.update(hidden_history=[])),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '481623001279').update(income=0.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '481623009196')['exclusions'].clear()),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '481623009196')['metrics'].update(math=d['schools'][0]['metrics']['math'])),
                ('history.json', lambda d: d['models'][0].update(intercept=-99.)),
                ('history.json', lambda d: d['records'][0].update(income_year=2024)),
                ('history.json', lambda d: d['records'][0]['subjects'].update(extra={})),
                ('history.json', lambda d: d['records'][0].update(raw_count_proxy=100)),
                ('history.json', lambda d: d.update(ghost_records=[])),
                ('coverage.json', lambda d: d['cohorts']['grade']['eligible'].update(combined=189)),
                ('coverage.json', lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear()),
                ('catalog.json', lambda d: d['regions'][0].update(name='Statewide', statewide=True)),
            ]:
                for name, content in originals.items(): (folder / name).write_bytes(content)
                changed = json.loads((folder / filename).read_text()); mutate(changed)
                (folder / filename).write_text(json.dumps(changed))
                with self.subTest(filename=filename, mutate=mutate), self.assertRaises(ValueError):
                    dallas.validate_exports(self.payload, folder, self.numerical)
    def test_offline_extract_repeatability_keeps_historical_pins_immutable(self):
        paths = [dallas.model_audit.ROSTER, dallas.model_audit.OUTPUT,
                 ROOT / 'scripts/audit_dallas.py', ROOT / 'scripts/audit_dallas_models.py',
                 ROOT / 'tests/test_dallas_audit.py', ROOT / 'tests/test_dallas_models.py']
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-repeat-', dir=WORK) as folder:
            first, second = Path(folder) / 'one.json', Path(folder) / 'two.json'
            with mock.patch.object(dallas.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original archive access')):
                dallas.extract(first); dallas.extract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), dallas.EXTRACT.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(hashlib.sha256(dallas.model_audit.ROSTER.read_bytes()).hexdigest(), dallas.model_audit.ROSTER_SHA)
        self.assertEqual(hashlib.sha256(dallas.model_audit.OUTPUT.read_bytes()).hexdigest(), dallas.NUMERICAL_SHA)


    def test_exact_searchable_cohort_compact_links_and_separate_release_approval(self):
        dallas.validate(self.payload, self.expected)
        self.assertEqual(self.payload['dataset'], 'tx-dallas-2025')
        self.assertEqual(self.payload['state'], {'id': 'TX', 'name': 'Texas'})
        self.assertEqual((self.payload['region'], self.payload['region_name']), ('dallas', 'Dallas ISD'))
        self.assertIs(self.payload['statewide'], False)
        self.assertIs(self.payload['approved_for_source'], True)
        self.assertIs(self.payload['approved_for_modeling'], True)
        self.assertEqual(len(self.profiles), 189)
        self.assertEqual(set(self.profiles), set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        self.assertEqual(len(self.payload['sources']), 21)
        for key, count in [('high_school_configuration_ids', 37), ('mixed_configuration_ids', 7),
                           ('primary_configuration_ids', 6), ('nonoperational_school_ids', 10)]:
            self.assertEqual(len(self.numerical['frozen_population'][key]), count)
            self.assertFalse(set(self.profiles).intersection(self.numerical['frozen_population'][key]))
        for audit in [self.roster, self.numerical]:
            self.assertIs(audit['approved_for_source'], False)
            self.assertIs(audit['approved_for_modeling'], False)
        source = self.payload['source_audit']
        reference = source['complete_source_reference']
        self.assertEqual((reference['complete_original_record_count'], reference['complete_original_cell_count']), (2904, 112006))
        self.assertEqual(reference['sha256'], dallas.model_audit.ROSTER_SHA)
        self.assertNotIn('retained_raw_inputs', source)
        self.assertNotIn('raw_inputs', self.payload)
        self.assertEqual(len(source['retained_scope_exclusions']), 60)
        self.assertIs(source['release_basis']['ten_valid_scored_floor_certified'], False)
        selection = dict(self.payload['selection']); digest = selection.pop('sha256')
        self.assertEqual(digest, dallas.roster_audit.fingerprint(selection))
        for text in [self.payload['cohorts'][0]['note'], self.payload['coverage_note'], self.payload['methodology']['summary']]:
            for term in ['valid-score count scope', 'ten-valid-scored floor', 'uncertified', 'sampling intervals', 'unavailable']:
                self.assertIn(term, text.casefold())

    def test_every_original_row_field_income_and_whole_rate_reference_reconciles(self):
        raw = self.roster['raw_inputs']
        tables = {t: {r['source_row']: r for r in raw[t]['records']} for t in ['directory', 'ref', 'stud', 'assessment']}
        for profile in self.payload['schools']:
            link = self.links[profile['id']]; refs = profile['identity_raw']['source_refs']
            ccd = tables['directory'][refs['directory_source_row']]['raw']
            student = tables['stud'][refs['native_source_rows']['stud']]['raw']
            assessment = tables['assessment'][refs['native_source_rows']['assessment']]['raw']
            self.assertEqual((ccd['NCESSCH'], ccd['LEAID']), (profile['id'], '4816230'))
            self.assertEqual(ccd['ST_LEAID'], 'TX-057905')
            self.assertEqual(student['CAMPUS'], profile['identity_raw']['native_school_id'])
            self.assertEqual(student['DISTRICT'], '057905')
            self.assertEqual(profile['enrollment'], int(student['CPNTALLC']))
            self.assertEqual(profile['low_income'], int(student['CPNTECOC']))
            self.assertEqual(profile['income'], 100 * int(student['CPNTECOC']) / int(student['CPNTALLC']))
            self.assertEqual(profile['income_raw']['individual_income'], link['income'])
            self.assertEqual(profile['identity_raw']['native_enrolled_scope'], 'grade-school')
            for subject in ['math', 'reading']:
                outcome = profile['outcomes'][subject]; fields = dallas.roster_audit.FIELDS[subject]
                self.assertEqual(outcome['raw']['original_subject_triplet'], {f: assessment[f] for f in fields})
                self.assertEqual(outcome['raw']['original_rate_field'], fields[2])
                self.assertEqual(outcome['proficiency'], link['subjects'][subject]['published_rate'])
                self.assertIsNone(outcome['tested']); self.assertIsNone(outcome['valid_score_evidence'])
                self.assertIsNone(outcome['raw_tested']); self.assertIsNone(outcome['raw']['sampling_variance'])
                self.assertIs(outcome['raw']['ten_valid_scored_floor_certified'], False)
        blank = self.profiles['481623009196']
        self.assertEqual(blank['identity_raw']['native_school_id'], '057905241')
        self.assertEqual((blank['enrollment'], blank['low_income'], blank['income']), (8, 8, 100.))
        self.assertTrue(all(blank['outcomes'][s]['proficiency'] is None for s in ['math', 'reading']))
        self.assertTrue(all(set(blank['outcomes'][s]['raw']['original_subject_triplet'].values()) == {''} for s in ['math', 'reading']))
        self.assertEqual(blank['identity_raw']['ccd_flags']['school_type'], 'Alternative School')
        self.assertEqual(set(self.numerical['frozen_population']['mixed_configuration_ids']).intersection(self.profiles), set())

    def test_individual_income_counts_are_valid_while_assessment_counts_remain_held(self):
        r = self.payload['source_audit']['enrollment_reconciliation']
        self.assertEqual((r['ccd_lea_reported'], r['ccd_operational_school_sum'], r['native_campus_sum']), (139802, 139802, 139802))
        self.assertEqual(r['native_peims_membership_sum'], 139776)
        self.assertEqual(r['native_economic_disadvantage_sum'], 124800)
        self.assertEqual(len(r['native_enrollment_membership_differences']), 16)
        changed = [p for p in self.payload['schools'] if p['identity_raw']['native_peims_membership']['count'] != p['enrollment']]
        self.assertTrue(changed)
        self.assertTrue(all(p['income'] == 100*p['low_income']/p['enrollment'] for p in changed))
        self.assertIn('All valid-score counts', dallas.COUNT_NOTE)
        for term in ['October25,2024', 'codes01/02/99', 'CEP', 'Provision2', 'Jan16,2025']:
            self.assertIn(term, self.payload['income_definition']['definition'])

    def test_all_564_canonical_current_and_history_metrics_match_numerical_audit(self):
        self.assertEqual(dallas.validate_canonical(self.payload, self.database, self.numerical),
                         {'schools': 189, 'observations': 378, 'models': 3, 'results': 564})
        self.assertEqual(dallas.validate_exports(self.payload, self.output, self.numerical),
                         {f'dallas-2025-ES-{s}': 188 for s in dallas.model_audit.SUBJECTS})
        served = json.loads((self.output/'schools.json').read_text())
        selected = {p['id']: p for p in served['schools']}
        for key, school in selected.items():
            if key == '481623009196':
                self.assertEqual(school['metrics'], {})
                self.assertEqual(set(school['exclusions']), {'math', 'reading', 'combined'})
                self.assertEqual(school['history'][0]['subjects'], {})
            else:
                self.assertEqual(set(school['metrics']), {'math', 'reading', 'combined'})
                self.assertEqual(school['exclusions'], {})
            self.assertEqual((school['program'], school['latitude'], school['longitude']), ('Unclassified', None, None))
            self.assertTrue(all(v['tested'] is None and v['low'] is None and v['high'] is None and 'variance' not in v for v in school['metrics'].values()))
        self.assertGreater(max(p['metrics'].get('reading', {}).get('predicted', 0) for p in selected.values()), 100)
        self.assertGreater(selected['481623013856']['metrics']['combined']['studentized'], 5)
        for native in ['057905051', '057905142']:
            key = next(k for k,p in self.profiles.items() if p['identity_raw']['native_school_id'] == native)
            self.assertEqual(selected[key]['income'], 100.)
            self.assertEqual(set(selected[key]['metrics']), {'math', 'reading', 'combined'})
        with closing(connect(self.database)) as db:
            self.assertEqual({t: len(rows(db)[t])-1 for t in TABLES}, dict(dataset=1,source=22,
                assessment_definition=1,economic_definition=1,school=189,economic_observation=189,
                assessment_observation=378,model_run=3,model_result=564))

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
        self.assertAlmostEqual(served['intercept'], 99.1030702299696, places=10)
        self.assertAlmostEqual(served['slope'], -.5649647450068581, places=10)
        self.assertAlmostEqual(served['r2'], .45807840161548397, places=10)

    def test_normalized_mutations_and_direct_evidence_drift_are_rejected(self):
        mutations = [
            lambda d:d['schools'].pop(), lambda d:d['schools'][0].update(id='057905001'),
            lambda d:d['schools'][0]['identity_raw'].update(native_school_id='101912001'),
            lambda d:d['schools'][0]['identity_raw']['source_refs'].update(directory_source_row=1.),
            lambda d:d['schools'][0]['identity_raw']['ccd_flags'].update(charter='Yes'),
            lambda d:d['schools'][0]['income_raw']['individual_income']['raw'].update(CPNTALLC='1'),
            lambda d:d['schools'][0]['outcomes']['math']['raw'].update(sampling_variance=0.),
            lambda d:d['schools'][0]['outcomes']['reading'].update(proficiency=99.),
            lambda d:d['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment'),
            lambda d:d['schools'][0].update(income=True), lambda d:d['schools'][0].update(low_income=0),
            lambda d:next(s for s in d['schools'] if s['id']=='481623009196')['outcomes']['math'].update(proficiency=0.),
            lambda d:d['cohorts'][0].update(allow_point_only=False),
            lambda d:d['cohorts'][0].update(assessment='All grades'),
            lambda d:d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear(),
            lambda d:d['source_audit']['retained_scope_exclusions'].clear(),
            lambda d:d['source_audit']['complete_source_reference'].update(complete_original_cell_count=112006.),
            lambda d:d['source_audit']['release_basis'].update(historical_audits_approved_for_modeling=0),
            lambda d:d['source_audit']['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['sources']['numerical_audit'].update(sha256='0'*64),
            lambda d:d['selection']['directory_school_ids'].pop(),
            lambda d:d.update(statewide=0), lambda d:d.update(approved_for_modeling=1),
            lambda d:d['schools'][0].update(latitude=0.), lambda d:d['methodology']['details'].clear()]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.payload);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):dallas.validate(changed,self.expected)
        for kind in ['source','numerical','bool']:
            source,numeric=copy.deepcopy(self.roster),copy.deepcopy(self.numerical)
            if kind=='source':source['roster_links'].pop()
            elif kind=='numerical':numeric['models'][0]['results'][0]['studentized']+=1.
            else:numeric['approved_for_source']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):dallas.build_snapshot(source,numeric)

    def test_cached_normalized_validation_checks_missing_changed_blobs_and_all_pins(self):
        original = Path.read_bytes
        for path in [dallas.model_audit.ROSTER, dallas.model_audit.OUTPUT]:
            for bad in [b'{}', None]:
                def read(p):
                    if p==path:
                        if bad is None:raise FileNotFoundError('Linked complete evidence missing')
                        return bad
                    return original(p)
                with self.subTest(path=path,bad=bad),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):
                    dallas.validate(self.payload,self.expected)
        for owner,keys in [(dallas,['NUMERICAL_SHA','NUMERICAL_CODE_SHA','NUMERICAL_TESTS_SHA']),
                           (dallas.model_audit,['ROSTER_SHA','SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA'])]:
            for key in keys:
                with self.subTest(key=key),mock.patch.object(owner,key,'0'*64),self.assertRaises(ValueError):
                    dallas.validate(self.payload,self.expected)

    def test_prepare_repeat_and_rejection_preserve_prior_rows_and_exports_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='repeat-',dir=WORK) as name:
            folder=Path(name);database=folder/'schools.sqlite';output=folder/'output'
            with closing(connect(database)) as db:
                db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit();before=rows(db)
            run_prepared(dallas.prepare,database,output)
            first_files={p.name:p.read_bytes() for p in output.glob('*.json')}
            with closing(connect(database)) as db:first=rows(db)
            run_prepared(dallas.prepare,database,output)
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db))
            bad=copy.deepcopy(self.payload);bad['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment')
            path=folder/'bad.json';path.write_text(json.dumps(bad))
            with mock.patch.object(dallas,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):dallas.prepare(database,output,path)
                with mock.patch.object(dallas,'NUMERICAL_SHA','0'*64),self.assertRaises(ValueError):dallas.prepare(database,output)
                with self.assertRaises(ValueError):dallas.prepare(database,Path('/tmp/dallas-output'))
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));db.execute("UPDATE model_result SET studentized=99 WHERE dataset_id='tx-dallas-2025'");db.commit();corrupt=rows(db)
            with mock.patch.object(dallas,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):dallas.prepare(database,output)
            with closing(connect(database)) as db:self.assertEqual(corrupt,rows(db))
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})


if __name__ == '__main__':
    unittest.main()

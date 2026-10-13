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
import prepare_charlotte as charlotte

TABLES = ['dataset', 'source', 'assessment_definition', 'economic_definition', 'school',
          'economic_observation', 'assessment_observation', 'model_run', 'model_result']
WORK = ROOT / 'data/build/charlotte-integration-implementation'
MISSING_INCOME = set()


def rows(db):
    return {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in TABLES}


def prior_rows(db):
    return {table: [r for r in records if not any(isinstance(v, str) and
            (v == charlotte.DATASET or v.startswith(charlotte.DATASET + ':')) for v in r)]
            for table, records in rows(db).items()}


def seed_other(db):
    """Same native school identity in an independent same-state release."""
    db.execute("INSERT INTO dataset VALUES ('other-nc','NC','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-nc','other.json','https://example.test/source',?,'2025-01-01')", ('1' * 64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','NC','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-nc','600300','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-nc','600300',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-nc','600300','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-nc','other-assessment','math','keep-method',?,'{}')", ('2' * 64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-nc','600300',40,45,-1,-2,0)")


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


class CharlotteIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        cls.roster, cls.numerical = charlotte.load_inputs()
        cls.payload = json.loads(charlotte.EXTRACT.read_text())
        cls.expected = charlotte.build_snapshot(cls.roster, cls.numerical)
        cls.links = {r['school_id']: r for r in cls.roster['roster_links']}
        cls.profiles = {r['id']: r for r in cls.payload['schools']}
        cls.native = {r['source_row']: r for r in cls.roster['raw_inputs']['assessment']['records']}
        cls.sandbox = tempfile.TemporaryDirectory(prefix='test-', dir=WORK)
        cls.output = Path(cls.sandbox.name) / 'output'
        cls.database = Path(cls.sandbox.name) / 'schools.sqlite'
        with closing(connect(cls.database)) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db); db.commit()
        run_prepared(charlotte.prepare, cls.database, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.cleanup()

    def test_full_nullable_configuration_cohort_and_separate_release_approval(self):
        charlotte.validate(self.payload, self.expected)
        self.assertEqual(self.payload['dataset'], 'nc-charlotte-2025')
        self.assertEqual(self.payload['state'], {'id': 'NC', 'name': 'North Carolina'})
        self.assertEqual((self.payload['region'], self.payload['region_name'], self.payload['release_status']),
                         ('charlotte', 'Charlotte-Mecklenburg', 'ready'))
        self.assertIs(self.payload['statewide'], False)
        self.assertIs(self.payload['approved_for_source'], True)
        self.assertIs(self.payload['approved_for_modeling'], True)
        self.assertEqual(len(self.profiles), 146)
        self.assertEqual(set(self.profiles), set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        self.assertEqual({s['id'] for s in self.payload['schools'] if s['income'] is None}, MISSING_INCOME)
        for scope in ['high_school_configuration_ids', 'mixed_configuration_ids', 'primary_configuration_ids', 'nonoperational_school_ids']:
            self.assertFalse(set(self.profiles).intersection(self.numerical['frozen_population'][scope]))
        for audit in [self.roster, self.numerical]:
            self.assertIs(audit['approved_for_source'], False)
            self.assertIs(audit['approved_for_modeling'], False)
        self.assertEqual(len(self.payload['sources']), 18)
        selection = dict(self.payload['selection']); digest = selection.pop('sha256')
        self.assertEqual(digest, charlotte.roster_audit.fingerprint(selection))
        cohort = self.payload['cohorts'][0]
        self.assertEqual((cohort['assessment'], cohort['standard']), (charlotte.model_audit.ASSESSMENT, charlotte.model_audit.STANDARD))
        self.assertEqual(cohort['grades'], '3–8')
        self.assertTrue(cohort['allow_point_only'])
        for text in [cohort['note'], self.payload['coverage_note'], self.payload['methodology']['summary']]:
            for term in ['valid-score count scope', 'ten-valid-scored floor', 'uncertified', 'sampling intervals', 'unavailable']:
                self.assertIn(term, text.casefold())

    def test_all_raw_sources_masks_definitions_and_outside_records_retained(self):
        evidence = self.payload['source_audit']
        self.assertEqual(charlotte.roster_audit.fingerprint(evidence['retained_raw_inputs']), charlotte.roster_audit.RAW_INPUT_SHA)
        self.assertEqual([len(evidence['retained_raw_inputs'][s]['records']) for s in
                          ['directory', 'membership', 'assessment', 'income']], [186, 1457, 5667, 187])
        self.assertEqual(evidence['source_definition_evidence'], self.roster['source_definition_evidence'])
        self.assertEqual(evidence['planning_identity_reconciliation'], self.roster['planning_identity_reconciliation'])
        self.assertEqual(len(evidence['excluded_operational_roster_records']), 40)
        self.assertEqual(len(evidence['nonoperational_directory']), 0)
        self.assertEqual(len(evidence['retained_raw_inputs']['native_location']['records']), 187)
        self.assertEqual(len(evidence['cohorts']['ccd_lower_membership_contracts']['school_ids']), 148)
        self.assertEqual({r['school_id'] for r in evidence['excluded_operational_roster_records']
                          if r['offered']['band'] == 'primary'}, {'600335', '600519'})
        self.assertEqual([evidence['subject_coverage'][s]['excluded_configuration_profiles']
                          for s in charlotte.model_audit.SUBJECTS], [1, 0, 1])
        self.assertEqual([evidence['subject_coverage'][s]['native_source_profiles']
                          for s in charlotte.model_audit.SUBJECTS], [146, 146, 146])
        for key, school in self.profiles.items():
            link = self.links[key]
            self.assertEqual(school['ncessch'], link['ncessch'])
            self.assertEqual(school['identity_raw']['native_school_id'], link['native_school_id'])
            self.assertEqual(school['identity_raw']['enrolled_evidence'], link['enrolled'])
            self.assertEqual(school['identity_raw']['supplemental_native_location'], link['native_location'])
            self.assertEqual(school['city'], school['identity_raw']['ccd']['raw']['LCITY'] or None)
            self.assertEqual(school['income_raw']['individual_eds_evidence'], link['income'])
            self.assertEqual(school['income'], link['income']['percentage'])
            self.assertIsNone(school['low_income'])
            self.assertEqual(school['enrollment'], link['income']['april_enrollment'])
            for subject in ['math', 'reading']:
                value = school['outcomes'][subject]
                row = self.native[value['source_row']]['raw']
                self.assertEqual((row['type'], row['grade'], row['subgroup'], row['school_code']), ('RG', 'GS', 'ALL', key))
                self.assertEqual(value['proficiency'], charlotte.roster_audit.north_carolina.exact_percent(row['pct_glp']))
                self.assertEqual(value['raw']['assessment_raw'], row)
                self.assertTrue(all(value[k] is None for k in ['tested', 'valid_score_evidence', 'raw_tested']))
                self.assertIsNone(value['raw']['sampling_variance'])
                self.assertIsNone(value['raw']['valid_score_count'])
                self.assertIs(value['raw']['ten_valid_scored_floor_certified'], False)
        self.assertEqual(self.profiles['600598']['outcomes']['math']['proficiency'], 9.4)
        self.assertEqual(self.profiles['600598']['outcomes']['reading']['proficiency'], 14.6)
        self.assertEqual(self.profiles['600598']['identity_raw']['ccd_flags']['school_type'], 'Alternative School')
        self.assertEqual(self.profiles['600387']['outcomes']['reading']['proficiency'], 90.7)
        self.assertIsNone(self.profiles['600387']['outcomes']['math']['proficiency'])
        self.assertEqual(self.profiles['600387']['outcomes']['math']['raw']['native_rate'], '>95')

    def test_income_april_denominator_remains_separate_from_ccd_fall(self):
        coverage = self.payload['source_audit']['operational_roster']
        self.assertEqual((coverage['lea_fall_enrollment'], coverage['operational_school_fall_enrollment'],
                          coverage['lea_minus_operational_school_fall_enrollment']), (147299, 145014, 2285))
        self.assertEqual(coverage['operational_school_april_enrollment'], 145900)
        self.assertEqual(coverage['april_district_aggregate_enrollment'], 145900)
        self.assertEqual(coverage['april_enrollment_different_from_fall'], 183)
        changed = [s for s in self.payload['schools'] if s['identity_raw']['april_minus_fall_enrollment'] != 0]
        self.assertTrue(changed)
        for school in changed:
            self.assertNotEqual(school['enrollment'], school['identity_raw']['enrolled_evidence']['reported_total'])
        definition = self.payload['income_definition']['definition']
        for term in ['currently enrolled', 'PK through 13', 'Medicaid', 'no low-income count is inferred']:
            self.assertIn(term, definition)

    def test_repeat_import_preserves_shared_identity_all_nine_tables(self):
        with closing(connect(':memory:')) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db)
            before = prior_rows(db)
            import_snapshot(db, self.payload, charlotte.EXTRACT); first = rows(db)
            import_snapshot(db, self.payload, charlotte.EXTRACT)
            self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            additions = {t: len(rows(db)[t]) - len(before[t]) for t in TABLES}
            self.assertEqual(additions, dict(dataset=1, source=19, assessment_definition=1,
                economic_definition=1, school=146, economic_observation=146,
                assessment_observation=292, model_run=0, model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',
                                       (charlotte.DATASET,)).fetchone()[0], 291)
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',
                                       (charlotte.DATASET,)).fetchone()[0], 0)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_prepare_twice_preserves_complete_state_models_and_rejects_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='repeat-', dir=WORK) as folder:
            folder = Path(folder); database = folder / 'schools.sqlite'; output = folder / 'output'
            state = charlotte.roster_audit.load_north_carolina()
            with closing(connect(database)) as db:
                db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db); db.commit()
            run_prepared(prepare_snapshot, state, charlotte.roster_audit.north_carolina.EXTRACT, folder / 'state-output', database)
            with closing(connect(database)) as db: before = prior_rows(db)
            run_prepared(charlotte.prepare, database, output)
            first_files = {p.name: p.read_bytes() for p in output.glob('*.json')}
            with closing(connect(database)) as db: first = rows(db)
            run_prepared(charlotte.prepare, database, output)
            self.assertEqual(first_files, {p.name: p.read_bytes() for p in output.glob('*.json')})
            with closing(connect(database)) as db:
                self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            bad = copy.deepcopy(self.payload)
            bad['schools'][0]['outcomes']['math'].update(tested=100, valid_score_evidence='Enrollment')
            wrong = folder / 'wrong.json'; wrong.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run_prepared(charlotte.prepare, database, output, wrong)
            with closing(connect(database)) as db: self.assertEqual(first, rows(db))
            self.assertEqual(first_files, {p.name: p.read_bytes() for p in output.glob('*.json')})
            with mock.patch.object(charlotte, 'prepare_snapshot', side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError): charlotte.prepare(database, Path('/tmp/charlotte-output'), charlotte.EXTRACT)

    def test_every_canonical_and_static_metric_matches_independent_numerical_audit(self):
        self.assertEqual(charlotte.validate_canonical(self.payload, self.database, self.numerical),
                         {'schools': 146, 'observations': 292, 'models': 3, 'results': 436})
        self.assertEqual(charlotte.validate_exports(self.payload, self.output, self.numerical),
                         {f'charlotte-2025-ES-{s}': charlotte.EXPECTED_N[s] for s in charlotte.model_audit.SUBJECTS})
        schools = json.loads((self.output / 'schools.json').read_text())
        selected = {s['id']: s for s in schools['schools']}
        for key, school in selected.items():
            if key in MISSING_INCOME:
                self.assertEqual(school['metrics'], {})
                self.assertIsNone(school['income'])
                self.assertEqual(set(school['exclusions']), {'math', 'reading', 'combined'})
                self.assertEqual(school['history'][0]['subjects'], {})
            elif key == '600387':
                self.assertEqual(set(school['metrics']), {'reading'})
                self.assertEqual(set(school['exclusions']), {'math', 'combined'})
            else:
                self.assertEqual(set(school['metrics']), {'math', 'reading', 'combined'})
                self.assertEqual(school['exclusions'], {})
            self.assertTrue(all(v['tested'] is None and v['low'] is None and v['high'] is None
                                and 'variance' not in v for v in school['metrics'].values()))
            self.assertEqual((school['program'], school['latitude'], school['longitude']), ('Unclassified', None, None))
        for model in self.numerical['models']:
            alternative = {i['school_id'] for i in model['inputs'] if i['ccd_school_type'] == 'Alternative School'}
            self.assertEqual(alternative, {'600598'})
            self.assertTrue(all(model['subject'] in selected[key]['metrics'] for key in alternative))
        with closing(connect(self.database)) as db:
            self.assertEqual({t: len(rows(db)[t]) - 1 for t in TABLES}, dict(dataset=1, source=19,
                assessment_definition=1, economic_definition=1, school=146,
                economic_observation=146, assessment_observation=292, model_run=3, model_result=436))

    def test_combined_is_separately_fitted_from_equal_original_rate_means(self):
        models = {m['subject']: m for m in self.numerical['models']}
        combined = models['combined']
        # ELA has one additional member: averaging the two whole-cohort lines is wrong.
        mean_intercept = (models['math']['coefficients']['intercept'] + models['reading']['coefficients']['intercept']) / 2
        self.assertGreater(abs(combined['coefficients']['intercept'] - mean_intercept), .05)
        for row in combined['inputs']:
            self.assertEqual(row['outcome_pct'], (row['outcome_by_subject']['math'] + row['outcome_by_subject']['reading']) / 2)
        exported = json.loads((self.output / 'schools.json').read_text())['models']['ES']['combined']
        self.assertAlmostEqual(exported['intercept'], 98.86329823202577, places=10)
        self.assertAlmostEqual(exported['slope'], -.8917557486960666, places=10)
        self.assertAlmostEqual(exported['r2'], .6727091847580442, places=10)

    def test_strict_normalized_source_and_direct_frozen_input_guards(self):
        mutations = [
            lambda d: d['schools'].pop(),
            lambda d: d['schools'][0].update(id='600LEA'),
            lambda d: d['schools'][0]['identity_raw']['ccd']['raw'].update(LEAID='3702971'),
            lambda d: d['schools'][0]['identity_raw']['ccd_flags'].update(charter='Yes'),
            lambda d: d['schools'][0]['income_raw']['april_income']['raw'].update(collection_code='OCT'),
            lambda d: d['schools'][0]['outcomes']['math']['raw'].update(sampling_variance=0.),
            lambda d: d['schools'][0]['outcomes']['reading'].update(proficiency=99.),
            lambda d: d['schools'][0]['outcomes']['math'].update(tested=100, valid_score_evidence='CCD membership'),
            lambda d: next(s for s in d['schools'] if s['id'] == '600598').update(income=0., low_income=0),
            lambda d: d['cohorts'][0].update(allow_point_only=False),
            lambda d: d['cohorts'][0].update(assessment='All test types'),
            lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear(),
            lambda d: d['source_audit']['excluded_operational_roster_records'].clear(),
            lambda d: d['source_audit']['outside_directory_records']['assessment'].clear(),
            lambda d: d['source_audit']['retained_raw_inputs']['membership']['records'][0]['raw'].update(STUDENT_COUNT='0'),
            lambda d: d['source_audit']['release_basis'].update(historical_audits_approved_for_modeling=0),
            lambda d: d['source_audit']['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d: d['sources']['numerical_audit'].update(sha256='0' * 64),
            lambda d: d['selection']['directory_school_ids'].pop(),
            lambda d: d.update(statewide=0),
            lambda d: d.update(approved_for_modeling=1),
            lambda d: d['schools'][0].update(income=True),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(self.payload); mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): charlotte.validate(changed, self.expected)
        for kind in ['source', 'numerical', 'bool']:
            roster, numerical = copy.deepcopy(self.roster), copy.deepcopy(self.numerical)
            if kind == 'source': roster['roster_links'].pop()
            elif kind == 'numerical': numerical['models'][0]['results'][0]['studentized'] += 1.
            else: numerical['approved_for_source'] = 0
            with self.subTest(kind=kind), self.assertRaises(ValueError): charlotte.build_snapshot(roster, numerical)
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.json'; wrong.write_text('{}')
            with mock.patch.object(charlotte.model_audit, 'OUTPUT', wrong), self.assertRaisesRegex(ValueError, 'fingerprint'):
                charlotte.load_inputs()

    def test_canonical_proxies_orphans_raw_drift_and_foreign_namespace_rejected(self):
        corruptions = [
            "UPDATE model_result SET studentized=99 WHERE dataset_id='nc-charlotte-2025' AND school_id='600300'",
            "UPDATE assessment_observation SET tested=893 WHERE dataset_id='nc-charlotte-2025' AND school_id='600598'",
            "UPDATE assessment_observation SET proficiency=95,status='reported' WHERE dataset_id='nc-charlotte-2025' AND school_id='600387' AND subject='math'",
            "UPDATE assessment_observation SET proficiency=NULL,status='suppressed_or_not_reported' WHERE dataset_id='nc-charlotte-2025' AND school_id='600598'",
            "UPDATE economic_observation SET percentage=0,low_income=0 WHERE dataset_id='nc-charlotte-2025' AND school_id='600598'",
            "UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='nc-charlotte-2025' AND school_id='600300'",
            "UPDATE school SET name='Wrong school' WHERE dataset_id='nc-charlotte-2025' AND school_id='600300'",
            "UPDATE assessment_observation SET raw_value='{}' WHERE dataset_id='nc-charlotte-2025' AND school_id='600598'",
            "INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='nc-charlotte-2025' AND school_id='600300'",
            "INSERT INTO model_run SELECT id||':ghost',dataset_id,definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='nc-charlotte-2025' AND subject='math'",
            "INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='nc-charlotte-2025:income'",
            "INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE 'nc-charlotte-2025:%'",
            "INSERT INTO model_result VALUES ('other-model','nc-charlotte-2025','600598',9.4,90,1,NULL,NULL)",
            "INSERT INTO source SELECT id||':ghost','other-nc',path,url,sha256,imported_at FROM source WHERE id='nc-charlotte-2025:extract'",
            "INSERT INTO model_run SELECT id||':ghost','other-nc',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='nc-charlotte-2025' AND subject='math'",
            "UPDATE school SET source_id='nc-charlotte-2025:extract' WHERE dataset_id='other-nc'",
            "UPDATE economic_observation SET definition_id='nc-charlotte-2025:income' WHERE dataset_id='other-nc'",
            "UPDATE economic_observation SET source_id='nc-charlotte-2025:extract' WHERE dataset_id='other-nc'",
            "UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE 'nc-charlotte-2025:%') WHERE dataset_id='other-nc'",
            "UPDATE assessment_observation SET source_id='nc-charlotte-2025:extract' WHERE dataset_id='other-nc'",
        ]
        with tempfile.TemporaryDirectory(prefix='corrupt-db-', dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.sqlite'
            for sql in corruptions:
                with closing(connect(self.database)) as source, closing(connect(wrong)) as db:
                    source.backup(db); db.execute(sql); db.commit()
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    charlotte.validate_canonical(self.payload, wrong, self.numerical)

    def test_static_ghosts_counts_income_promotion_and_nonfinite_metrics_rejected(self):
        originals = {p.name: p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='corrupt-export-', dir=WORK) as folder:
            folder = Path(folder); descriptor = json.loads(originals['catalog.json'])
            descriptor['regions'][0].update(schools=str((folder / 'schools.json').relative_to(ROOT)),
                audit=str((folder / 'coverage.json').relative_to(ROOT)))
            originals['catalog.json'] = json.dumps(descriptor).encode()
            for filename, mutate in [
                ('schools.json', lambda d: d['models'].update(HS=d['models']['ES'])),
                ('schools.json', lambda d: d['models']['ES']['math'].update(n=145.)),
                ('schools.json', lambda d: d['models']['ES']['math'].update(slope=float('nan'))),
                ('schools.json', lambda d: d['schools'].append(copy.deepcopy(d['schools'][0]))),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(studentized=99.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(tested=False)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(low=0.)),
                ('schools.json', lambda d: d['schools'][0]['metrics']['math'].update(cohort_n=145.)),
                ('schools.json', lambda d: d['schools'][0].update(latitude=0.)),
                ('schools.json', lambda d: d['schools'][0].update(hidden_model={})),
                ('schools.json', lambda d: d.update(hidden_history=[])),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '600598').update(income=0.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '600387')['exclusions'].clear()),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '600387')['metrics'].update(math=d['schools'][0]['metrics']['math'])),
                ('history.json', lambda d: d['models'][0].update(intercept=-99.)),
                ('history.json', lambda d: d['records'][0].update(income_year=2024)),
                ('history.json', lambda d: d['records'][0]['subjects'].update(extra={})),
                ('history.json', lambda d: d['records'][0].update(raw_count_proxy=100)),
                ('history.json', lambda d: d.update(ghost_records=[])),
                ('coverage.json', lambda d: d['cohorts']['grade']['eligible'].update(combined=146)),
                ('coverage.json', lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear()),
                ('catalog.json', lambda d: d['regions'][0].update(name='Statewide', statewide=True)),
            ]:
                for name, content in originals.items(): (folder / name).write_bytes(content)
                changed = json.loads((folder / filename).read_text()); mutate(changed)
                (folder / filename).write_text(json.dumps(changed))
                with self.subTest(filename=filename, mutate=mutate), self.assertRaises(ValueError):
                    charlotte.validate_exports(self.payload, folder, self.numerical)

    def test_offline_extract_repeatability_keeps_historical_pins_immutable(self):
        paths = [charlotte.model_audit.ROSTER, charlotte.model_audit.OUTPUT,
                 ROOT / 'scripts/audit_charlotte.py', ROOT / 'scripts/audit_charlotte_models.py',
                 ROOT / 'tests/test_charlotte_audit.py', ROOT / 'tests/test_charlotte_models.py']
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-repeat-', dir=WORK) as folder:
            first, second = Path(folder) / 'one.json', Path(folder) / 'two.json'
            with mock.patch.object(charlotte.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original archive access')):
                charlotte.extract(first); charlotte.extract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), charlotte.EXTRACT.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(hashlib.sha256(charlotte.model_audit.ROSTER.read_bytes()).hexdigest(), charlotte.model_audit.ROSTER_SHA)
        self.assertEqual(hashlib.sha256(charlotte.model_audit.OUTPUT.read_bytes()).hexdigest(), charlotte.NUMERICAL_SHA)


if __name__ == '__main__':
    unittest.main()

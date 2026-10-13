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
import prepare_duval as duval

TABLES = ['dataset', 'source', 'assessment_definition', 'economic_definition', 'school',
          'economic_observation', 'assessment_observation', 'model_run', 'model_result']
WORK = ROOT / 'data/build/duval-integration-implementation'
MISSING_INCOME = set()


def rows(db):
    return {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in TABLES}


def prior_rows(db):
    return {table: [r for r in records if not any(isinstance(v, str) and
            (v == duval.DATASET or v.startswith(duval.DATASET + ':')) for v in r)]
            for table, records in rows(db).items()}


def seed_other(db):
    """Same native school identity in an independent same-state release."""
    db.execute("INSERT INTO dataset VALUES ('other-fl','FL','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-fl','other.json','https://example.test/source',?,'2025-01-01')", ('1' * 64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','FL','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-fl','16-0121','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-fl','16-0121',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-fl','16-0121','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-fl','other-assessment','math','keep-method',?,'{}')", ('2' * 64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-fl','16-0121',40,45,-1,-2,0)")


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


class DuvalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True)
        cls.roster,cls.numerical=duval.load_inputs()
        cls.payload=json.loads(duval.EXTRACT.read_text());cls.expected=duval.build_snapshot(cls.roster,cls.numerical)
        cls.links={r['school_id']:r for r in cls.roster['roster_links']};cls.profiles={r['id']:r for r in cls.payload['schools']}
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.output=Path(cls.sandbox.name)/'output';cls.database=Path(cls.sandbox.name)/'schools.sqlite'
        with closing(connect(cls.database))as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit()
        run_prepared(duval.prepare,cls.database,cls.output)

    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def test_repeat_import_preserves_shared_identity_all_nine_tables(self):
        with closing(connect(':memory:')) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db)
            before = prior_rows(db)
            import_snapshot(db, self.payload, duval.EXTRACT); first = rows(db)
            import_snapshot(db, self.payload, duval.EXTRACT)
            self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            additions = {t: len(rows(db)[t]) - len(before[t]) for t in TABLES}
            self.assertEqual(additions, dict(dataset=1, source=17, assessment_definition=1,
                economic_definition=1, school=150, economic_observation=150,
                assessment_observation=300, model_run=0, model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',
                                       (duval.DATASET,)).fetchone()[0], 292)
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',
                                       (duval.DATASET,)).fetchone()[0], 0)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
    def test_canonical_proxies_orphans_raw_drift_and_foreign_namespace_rejected(self):
        corruptions = [
            "UPDATE model_result SET studentized=99 WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE assessment_observation SET tested=893 WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE assessment_observation SET proficiency=95,status='reported' WHERE dataset_id='fl-duval-2025' AND school_id='16-0061' AND subject='math'",
            "UPDATE assessment_observation SET proficiency=NULL,status='suppressed_or_not_reported' WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE economic_observation SET percentage=0,low_income=0 WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE school SET name='Wrong school' WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "UPDATE assessment_observation SET raw_value='{}' WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='fl-duval-2025' AND school_id='16-0121'",
            "INSERT INTO model_run SELECT id||':ghost',dataset_id,definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='fl-duval-2025' AND subject='math'",
            "INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='fl-duval-2025:income'",
            "INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE 'fl-duval-2025:%'",
            "INSERT INTO model_result VALUES ('other-model','fl-duval-2025','16-0171',9.4,90,1,NULL,NULL)",
            "INSERT INTO source SELECT id||':ghost','other-fl',path,url,sha256,imported_at FROM source WHERE id='fl-duval-2025:extract'",
            "INSERT INTO model_run SELECT id||':ghost','other-fl',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='fl-duval-2025' AND subject='math'",
            "UPDATE school SET source_id='fl-duval-2025:extract' WHERE dataset_id='other-fl'",
            "UPDATE economic_observation SET definition_id='fl-duval-2025:income' WHERE dataset_id='other-fl'",
            "UPDATE economic_observation SET source_id='fl-duval-2025:extract' WHERE dataset_id='other-fl'",
            "UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE 'fl-duval-2025:%') WHERE dataset_id='other-fl'",
            "UPDATE assessment_observation SET source_id='fl-duval-2025:extract' WHERE dataset_id='other-fl'",
        ]
        with tempfile.TemporaryDirectory(prefix='corrupt-db-', dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.sqlite'
            for sql in corruptions:
                with closing(connect(self.database)) as source, closing(connect(wrong)) as db:
                    source.backup(db); db.execute(sql); db.commit()
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    duval.validate_canonical(self.payload, wrong, self.numerical)
    def test_static_ghosts_counts_income_promotion_and_nonfinite_metrics_rejected(self):
        originals = {p.name: p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='corrupt-export-', dir=WORK) as folder:
            folder = Path(folder); descriptor = json.loads(originals['catalog.json'])
            descriptor['regions'][0].update(schools=str((folder / 'schools.json').relative_to(ROOT)),
                audit=str((folder / 'coverage.json').relative_to(ROOT)))
            originals['catalog.json'] = json.dumps(descriptor).encode()
            for filename, mutate in [
                ('schools.json', lambda d: d['models'].update(HS=d['models']['ES'])),
                ('schools.json', lambda d: d['models']['ES']['math'].update(n=146.)),
                ('schools.json', lambda d: d['models']['ES']['math'].update(slope=float('nan'))),
                ('schools.json', lambda d: d['schools'].append(copy.deepcopy(d['schools'][0]))),
                ('schools.json', lambda d: next(s for s in d['schools'] if 'math' in s['metrics'])['metrics']['math'].update(studentized=99.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if 'math' in s['metrics'])['metrics']['math'].update(tested=False)),
                ('schools.json', lambda d: next(s for s in d['schools'] if 'math' in s['metrics'])['metrics']['math'].update(low=0.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if 'math' in s['metrics'])['metrics']['math'].update(cohort_n=146.)),
                ('schools.json', lambda d: d['schools'][0].update(latitude=0.)),
                ('schools.json', lambda d: d['schools'][0].update(hidden_model={})),
                ('schools.json', lambda d: d.update(hidden_history=[])),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '16-0121').update(income=0.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '16-0061')['exclusions'].clear()),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '16-0061')['metrics'].update(math=next(s for s in d['schools'] if 'math' in s['metrics'])['metrics']['math'])),
                ('history.json', lambda d: d['models'][0].update(intercept=-99.)),
                ('history.json', lambda d: d['records'][0].update(income_year=2024)),
                ('history.json', lambda d: d['records'][0]['subjects'].update(extra={})),
                ('history.json', lambda d: d['records'][0].update(raw_count_proxy=100)),
                ('history.json', lambda d: d.update(ghost_records=[])),
                ('coverage.json', lambda d: d['cohorts']['grade']['eligible'].update(combined=150)),
                ('coverage.json', lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear()),
                ('catalog.json', lambda d: d['regions'][0].update(name='Statewide', statewide=True)),
            ]:
                for name, content in originals.items(): (folder / name).write_bytes(content)
                changed = json.loads((folder / filename).read_text()); mutate(changed)
                (folder / filename).write_text(json.dumps(changed))
                with self.subTest(filename=filename, mutate=mutate), self.assertRaises(ValueError):
                    duval.validate_exports(self.payload, folder, self.numerical)
    def test_offline_extract_repeatability_keeps_historical_pins_immutable(self):
        paths = [duval.model_audit.ROSTER, duval.model_audit.OUTPUT,
                 ROOT / 'scripts/audit_prince_georges.py', ROOT / 'scripts/audit_prince_georges_models.py',
                 ROOT / 'tests/test_prince_georges_audit.py', ROOT / 'tests/test_prince_georges_models.py']
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-repeat-', dir=WORK) as folder:
            first, second = Path(folder) / 'one.json', Path(folder) / 'two.json'
            with mock.patch.object(duval.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original archive access')):
                duval.extract(first); duval.extract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), duval.EXTRACT.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(hashlib.sha256(duval.model_audit.ROSTER.read_bytes()).hexdigest(), duval.model_audit.ROSTER_SHA)
        self.assertEqual(hashlib.sha256(duval.model_audit.OUTPUT.read_bytes()).hexdigest(), duval.NUMERICAL_SHA)


    def test_searchable150_exact_profiles_and_separate_point_only_release(self):
        duval.validate(self.payload,self.expected)
        self.assertEqual(self.payload['dataset'],'fl-duval-2025'); self.assertEqual(self.payload['state'],{'id':'FL','name':'Florida'})
        self.assertEqual((self.payload['region'],self.payload['region_name']),('duval','Duval'))
        self.assertIs(self.payload['statewide'],False)
        self.assertIs(self.payload['approved_for_source'],True); self.assertIs(self.payload['approved_for_modeling'],True)
        self.assertEqual(len(self.profiles),150); self.assertEqual(len(self.payload['sources']),16)
        self.assertEqual(set(self.profiles),set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        for key,count in [('high_school_configuration_ids',24),('mixed_configuration_ids',24),('primary_configuration_ids',4),('unmatched_native_school_ids',1)]:
            self.assertEqual(len(self.numerical['frozen_population'][key]),count)
            self.assertFalse(set(self.profiles).intersection(self.numerical['frozen_population'][key]))
        self.assertNotIn('16-0734',self.profiles)
        for artifact in [self.roster,self.numerical]:
            self.assertIs(artifact['approved_for_source'],False); self.assertIs(artifact['approved_for_modeling'],False)
        source=self.payload['source_audit']; reference=source['complete_source_reference']
        self.assertEqual((reference['complete_original_record_count'],reference['complete_original_cell_count']),(2495,59985))
        self.assertEqual(reference['sha256'],duval.model_audit.ROSTER_SHA)
        self.assertNotIn('retained_raw_inputs',source); self.assertNotIn('raw_inputs',self.payload)
        self.assertNotIn('source_definition_evidence',source)
        self.assertEqual(len(source['retained_scope_exclusions']),61)
        self.assertEqual(len(source['nonoperational_ccd_references']),8)
        self.assertEqual(source['retained_outside_source_profiles'][0]['school_id'],'16-0734')
        self.assertIs(source['release_basis']['ten_valid_scored_floor_certified'],False)
        selection=dict(self.payload['selection']); digest=selection.pop('sha256')
        self.assertEqual(digest,duval.roster_audit.fingerprint(selection))
        self.assertIn('FAST/BEST/FAA',self.payload['cohorts'][0]['assessment'])
        self.assertIn('School Grades',self.payload['cohorts'][0]['assessment'])
        self.assertEqual(source['native_assessment_definition']['original_numerical_name'],duval.model_audit.ASSESSMENT)
        for text in [self.payload['cohorts'][0]['note'],self.payload['coverage_note'],self.payload['methodology']['summary']]:
            for term in ['valid-score count','ten-valid-scored floor','uncertified','sampling intervals','unavailable']:
                self.assertIn(term,text.casefold())

    def test_original_native_crosswalks_february_components_and_whole_published_rates_dereference(self):
        raw=self.roster['raw_inputs']
        tables={t:{e['source_row']:e['raw']for e in raw[t]['records']}for t in ['directory','native_income','native_grades','native_assessment']}
        missing=[]
        for profile in self.payload['schools']:
            link=self.links[profile['id']]; refs=profile['identity_raw']['source_refs']
            ccd=tables['directory'][refs['directory']['source_row']]
            self.assertEqual((ccd['NCESSCH'],ccd['LEAID'],ccd['ST_LEAID'],ccd['ST_SCHID']),
                             (profile['ncessch'],'1200480','FL-16',profile['identity_raw']['native_school_id']))
            self.assertEqual(profile['id'],ccd['ST_SCHID'][3:])
            income=tables['native_income'][refs['income']['source_row']]
            self.assertEqual(profile['enrollment'],income[4])
            self.assertEqual(profile['low_income'],income[5]+income[6]+income[8])
            self.assertEqual(profile['income'],100*profile['low_income']/profile['enrollment'])
            self.assertEqual(income[7],0)
            self.assertEqual(profile['income_raw']['source_refs'],refs['income'])
            self.assertEqual(profile['income_raw']['individual_income']['raw_denominator'],income[4])
            self.assertEqual(refs['native_enrollment']['source_row'],link['native_grade_source_row'])
            self.assertEqual(tables['native_grades'][refs['native_enrollment']['source_row']][14:18],[0]*4)
            for subject in ['math','reading']:
                outcome=profile['outcomes'][subject]; ref=outcome['raw']['source_refs']
                if ref is None:
                    self.assertIsNone(outcome['proficiency']); self.assertIsNone(outcome['raw']['original_native_rate'])
                else:
                    record=tables['native_assessment'][ref['source_row']]
                    self.assertEqual(duval.roster_audit.native_identity(record),profile['id'])
                    self.assertEqual(outcome['raw']['original_native_rate'],record[duval.model_audit.SUBJECT_FIELDS[subject]])
                    self.assertEqual(outcome['proficiency'],duval.model_audit.original_rate(record[duval.model_audit.SUBJECT_FIELDS[subject]]))
                self.assertIsNone(outcome['tested']); self.assertIsNone(outcome['raw_tested'])
                self.assertIsNone(outcome['raw']['sampling_variance']); self.assertIs(outcome['raw']['ten_valid_scored_floor_certified'],False)
            if profile['outcomes']['math']['proficiency']is None: missing.append(profile['id'])
        self.assertEqual(set(missing),{'16-0061','16-0171','16-0271','16-0281'})
        self.assertTrue(all(self.profiles[key]['outcomes']['reading']['proficiency']is None for key in missing))

    def test_own_income_denominator_survives_other_population_discrepancies_and_identity_hold(self):
        coverage=self.payload['source_audit']['operational_roster']
        self.assertEqual((coverage['district_ccd_enrollment'],coverage['operational_ccd_enrollment_sum'],coverage['district_minus_operational_enrollment']),(130054,129932,122))
        self.assertEqual(coverage['outside_native_profile_ids'],['16-0734'])
        different=[p for p in self.payload['schools']if p['identity_raw']['ccd_membership']['reported_total']!=p['enrollment']]
        self.assertTrue(different); self.assertTrue(all(p['income']==100*p['low_income']/p['enrollment']for p in different))
        self.assertIn('All valid-score counts',duval.COUNT_NOTE)
        self.assertIn('school’s own reported denominator',self.payload['income_definition']['definition'])
        self.assertIn('Federal funding multiplier',self.payload['income_definition']['definition'])
        self.assertIn('does not prove the cause',' '.join(self.payload['methodology']['details']))

    def test_all438_canonical_current_history_results_missing_profiles_charters_unknown_metadata(self):
        self.assertEqual(duval.validate_canonical(self.payload,self.database,self.numerical),{'schools':150,'observations':300,'models':3,'results':438})
        self.assertEqual(duval.validate_exports(self.payload,self.output,self.numerical),{f'duval-2025-ES-{s}':n for s,n in duval.EXPECTED_N.items()})
        served=json.loads((self.output/'schools.json').read_text()); selected={p['id']:p for p in served['schools']}
        missing=[]
        for key,school in selected.items():
            if self.profiles[key]['outcomes']['math']['proficiency']is None:
                missing.append(key); self.assertEqual(school['metrics'],{})
                self.assertEqual(set(school['exclusions']),{'math','reading','combined'})
                self.assertEqual(school['history'][0]['subjects'],{})
            else:
                self.assertEqual(set(school['metrics']),{'math','reading','combined'}); self.assertEqual(school['exclusions'],{})
            self.assertEqual((school['program'],school['latitude'],school['longitude']),('Unclassified',None,None))
            self.assertTrue(all(v['tested']is None and v['low']is None and v['high']is None and 'variance'not in v for v in school['metrics'].values()))
        self.assertEqual(len(missing),4)
        self.assertIn('16-5401',selected); self.assertIn('16-5631',selected)
        self.assertTrue(any(s['income']==100. and s['metrics'] for s in selected.values()))
        self.assertEqual(sum(r['charter']=='Yes'for r in self.numerical['models'][0]['inputs']),30)
        with closing(connect(self.database))as db:
            self.assertEqual({t:len(rows(db)[t])-1 for t in TABLES},dict(dataset=1,source=17,assessment_definition=1,economic_definition=1,school=150,economic_observation=150,assessment_observation=300,model_run=3,model_result=438))

    def test_combined_retains_paired146_population_and_own_studentization(self):
        models={m['subject']:m for m in self.numerical['models']}; m,e,c=[models[s]for s in ['math','reading','combined']]
        self.assertEqual((m['coefficients']['n'],e['coefficients']['n'],c['coefficients']['n']),(146,146,146))
        self.assertAlmostEqual(c['coefficients']['slope'],(m['coefficients']['slope']+e['coefficients']['slope'])/2,places=12)
        self.assertTrue(any(abs(cr['studentized']-(mr['studentized']+er['studentized'])/2)>.01 for cr,mr,er in zip(c['results'],m['results'],e['results'])))
        for row in c['inputs']: self.assertEqual(row['outcome_pct'],(row['outcome_by_subject']['math']+row['outcome_by_subject']['reading'])/2)
        served=json.loads((self.output/'schools.json').read_text())['models']['ES']['combined']
        self.assertAlmostEqual(served['intercept'],c['coefficients']['intercept'],places=10)
        self.assertAlmostEqual(served['slope'],c['coefficients']['slope'],places=10)

    def test_adapter_live_metadata_and_repinned_public_contract_reject_before_writes(self):
        fields=[('EXPECTED_N',{'math':146,'reading':146.,'combined':146}),('ASSESSMENT','Other test'),
            ('STANDARD','Different standards'),('COUNT_NOTE','Use income enrollment as valid scores'),
            ('MODEL_SCOPE','Infer causal quality'),('ADAPTER_CONTRACT_SHA','0'*64),('NUMERICAL_BYTES',1324364.)]
        for field,bad in fields:
            with self.subTest(field=field),mock.patch.object(duval,field,bad):
                with self.assertRaises(ValueError): duval.validate(self.payload,self.expected)
                with self.assertRaises(ValueError): duval.build_snapshot(self.roster,self.numerical)
                with mock.patch.object(duval,'prepare_snapshot',side_effect=AssertionError('No writes')),self.assertRaises(ValueError):
                    duval.prepare(self.database,self.output)
        with mock.patch.object(duval,'COUNT_NOTE','Use enrollment as valid scores'):
            repinned=duval.roster_audit.fingerprint(duval.adapter_contract())
            with mock.patch.object(duval,'ADAPTER_CONTRACT_SHA',repinned),self.assertRaises(ValueError):
                duval.validate(self.payload,self.expected)
        policy=copy.deepcopy(duval.model_audit.POLICY); policy['models']='Remove influential members'
        with mock.patch.object(duval.model_audit,'POLICY',policy),mock.patch.object(duval.model_audit,'NUMERIC_POLICY_SHA',duval.roster_audit.fingerprint(policy)),self.assertRaises(ValueError):
            duval.validate(self.payload,self.expected)

    def test_normalized_mutations_and_direct_evidence_drift_are_rejected(self):
        mutations = [
            lambda d:d['schools'].pop(), lambda d:d['schools'][0].update(id='16-0218'),
            lambda d:d['schools'][0]['identity_raw'].update(native_school_id='FL-16-0734'),
            lambda d:d['schools'][0]['identity_raw']['source_refs']['directory'].update(source_row=1.),
            lambda d:d['schools'][0]['identity_raw']['ccd_flags'].update(charter='Yes'),
            lambda d:d['schools'][0]['income_raw']['individual_income'].update(raw_denominator='1'),
            lambda d:d['schools'][0]['outcomes']['math']['raw'].update(sampling_variance=0.),
            lambda d:d['schools'][0]['outcomes']['reading'].update(proficiency=99.),
            lambda d:d['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment'),
            lambda d:d['schools'][0].update(income=True), lambda d:d['schools'][0].update(low_income=0),
            lambda d:next(s for s in d['schools'] if s['id']=='16-0061')['outcomes']['math'].update(proficiency=0.),
            lambda d:d['cohorts'][0].update(allow_point_only=False),
            lambda d:d['cohorts'][0].update(assessment='All grades'),
            lambda d:d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear(),
            lambda d:d['source_audit']['retained_scope_exclusions'].clear(),
            lambda d:d['source_audit']['complete_source_reference'].update(complete_original_cell_count=59985.),
            lambda d:d['source_audit']['release_basis'].update(historical_audits_approved_for_modeling=0),
            lambda d:d['source_audit']['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['sources']['numerical_audit'].update(sha256='0'*64),
            lambda d:d['selection']['directory_school_ids'].pop(),
            lambda d:d.update(statewide=0), lambda d:d.update(approved_for_modeling=1),
            lambda d:d['schools'][0].update(latitude=0.), lambda d:d['methodology']['details'].clear()]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.payload);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):duval.validate(changed,self.expected)
        for kind in ['source','numerical','bool']:
            source,numeric=copy.deepcopy(self.roster),copy.deepcopy(self.numerical)
            if kind=='source':source['roster_links'].pop()
            elif kind=='numerical':numeric['models'][0]['results'][0]['studentized']+=1.
            else:numeric['approved_for_source']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):duval.build_snapshot(source,numeric)

    def test_cached_normalized_validation_checks_missing_changed_blobs_and_all_pins(self):
        original = Path.read_bytes
        for path in [duval.model_audit.ROSTER, duval.model_audit.OUTPUT]:
            for bad in [b'{}', None]:
                def read(p):
                    if p==path:
                        if bad is None:raise FileNotFoundError('Linked complete evidence missing')
                        return bad
                    return original(p)
                with self.subTest(path=path,bad=bad),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):
                    duval.validate(self.payload,self.expected)
        for owner,keys in [(duval,['NUMERICAL_SHA','NUMERICAL_CODE_SHA','NUMERICAL_TESTS_SHA','NUMERICAL_POLICY_SHA']),
                           (duval.model_audit,['ROSTER_SHA','SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA','SOURCE_RAW_SHA','SOURCE_SCHEMA_SHA','SOURCE_DEFINITION_SHA','SOURCE_IDENTITY_SHA'])]:
            for key in keys:
                with self.subTest(key=key),mock.patch.object(owner,key,'0'*64),self.assertRaises(ValueError):
                    duval.validate(self.payload,self.expected)

    def test_current_numerical_policy_drift_rejects_cached_direct_and_prewrite_paths(self):
        before_files={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with closing(connect(self.database))as db:before=rows(db)
        for field,bad in [('models','Infer causal effectiveness after dropping influential schools'),('counts','Use enrollment as valid scores'),('minimum_usable_subject_schools',True)]:
            policy=copy.deepcopy(duval.model_audit.POLICY);policy[field]=bad
            with self.subTest(field=field),mock.patch.object(duval.model_audit,'POLICY',policy):
                with self.assertRaisesRegex(ValueError,'policy'):duval.validate(self.payload,self.expected)
                with self.assertRaisesRegex(ValueError,'policy'):duval.build_snapshot(self.roster,self.numerical)
                with mock.patch.object(duval,'prepare_snapshot',side_effect=AssertionError('No writes before policy validation')),self.assertRaises(ValueError):duval.prepare(self.database,self.output)
        for field,bad in [('MIN_SCHOOLS',True),('ASSESSMENT','DLM alternate'),('STANDARD','Other standard'),('SUBJECTS',['math','reading']),
                          ('SUBJECT_LABELS',{'math':'Algebra 1','reading':'English Language Arts All Grades'}),
                          ('SUBJECT_FIELDS',{'math':20,'reading':6})]:
            with self.subTest(field=field),mock.patch.object(duval.model_audit,field,bad),self.assertRaises(ValueError):duval.validate(self.payload,self.expected)
        with closing(connect(self.database))as db:self.assertEqual(before,rows(db))
        self.assertEqual(before_files,{p.name:p.read_bytes()for p in self.output.glob('*.json')})

    def test_prepare_repeat_and_rejection_preserve_prior_rows_and_exports_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='repeat-',dir=WORK) as name:
            folder=Path(name);database=folder/'schools.sqlite';output=folder/'output'
            with closing(connect(database)) as db:
                db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit();before=rows(db)
            run_prepared(duval.prepare,database,output)
            first_files={p.name:p.read_bytes() for p in output.glob('*.json')}
            with closing(connect(database)) as db:first=rows(db)
            run_prepared(duval.prepare,database,output)
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db))
            bad=copy.deepcopy(self.payload);bad['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment')
            path=folder/'bad.json';path.write_text(json.dumps(bad))
            with mock.patch.object(duval,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):duval.prepare(database,output,path)
                with mock.patch.object(duval,'NUMERICAL_SHA','0'*64),self.assertRaises(ValueError):duval.prepare(database,output)
                with self.assertRaises(ValueError):duval.prepare(database,Path('/tmp/duval-output'))
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));db.execute("UPDATE model_result SET studentized=99 WHERE dataset_id='fl-duval-2025'");db.commit();corrupt=rows(db)
            with mock.patch.object(duval,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):duval.prepare(database,output)
            with closing(connect(database)) as db:self.assertEqual(corrupt,rows(db))
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})


if __name__ == '__main__':
    unittest.main()

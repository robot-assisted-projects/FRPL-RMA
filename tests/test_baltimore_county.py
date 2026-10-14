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
import prepare_baltimore_county as pg

TABLES = ['dataset', 'source', 'assessment_definition', 'economic_definition', 'school',
          'economic_observation', 'assessment_observation', 'model_run', 'model_result']
WORK = ROOT / 'data/build/baltimore-county-integration-implementation'
MISSING_INCOME = set()


def rows(db):
    return {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in TABLES}


def prior_rows(db):
    return {table: [r for r in records if not any(isinstance(v, str) and
            (v == pg.DATASET or v.startswith(pg.DATASET + ':')) for v in r)]
            for table, records in rows(db).items()}


def seed_other(db):
    """Same native school identity in an independent same-state release."""
    db.execute("INSERT INTO dataset VALUES ('other-md','MD','Keep release','Keep population','ready')")
    db.execute("INSERT INTO source VALUES ('other-source','other-md','other.json','https://example.test/source',?,'2025-01-01')", ('1' * 64,))
    db.execute("INSERT INTO assessment_definition VALUES ('other-assessment','MD','Other test',2025,'ES','3','Keep standard','https://example.test/assessment')")
    db.execute("INSERT INTO economic_definition VALUES ('other-income','Keep income','Keep definition','https://example.test/income')")
    db.execute("INSERT INTO school VALUES ('other-md','03-0101','Keep school','other-district','Keep district',NULL,NULL,'{}','other-source',1)")
    db.execute("INSERT INTO economic_observation VALUES ('other-md','03-0101',2025,'other-income','Keep school',100,30,30,'Keep income','{}','other-source',1)")
    db.execute("INSERT INTO assessment_observation VALUES ('other-md','03-0101','other-assessment','math',40,100,'reported','{}','100','other-source',1)")
    db.execute("INSERT INTO model_run VALUES ('other-model','other-md','other-assessment','math','keep-method',?,'{}')", ('2' * 64,))
    db.execute("INSERT INTO model_result VALUES ('other-model','other-md','03-0101',40,45,-1,-2,0)")


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


class BaltimoreCountyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True,exist_ok=True)
        cls.roster,cls.numerical=pg.load_inputs()
        cls.payload=json.loads(pg.EXTRACT.read_text());cls.expected=pg.build_snapshot(cls.roster,cls.numerical)
        cls.links={r['school_id']:r for r in cls.roster['roster_links']};cls.profiles={r['id']:r for r in cls.payload['schools']}
        cls.sandbox=tempfile.TemporaryDirectory(prefix='test-',dir=WORK);cls.output=Path(cls.sandbox.name)/'output';cls.database=Path(cls.sandbox.name)/'schools.sqlite'
        with closing(connect(cls.database))as db:
            db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit()
        run_prepared(pg.prepare,cls.database,cls.output)

    @classmethod
    def tearDownClass(cls):cls.sandbox.cleanup()

    def test_repeat_import_preserves_shared_identity_all_nine_tables(self):
        with closing(connect(':memory:')) as db:
            db.executescript((ROOT / 'scripts/schema.sql').read_text()); seed_other(db)
            before = prior_rows(db)
            import_snapshot(db, self.payload, pg.EXTRACT); first = rows(db)
            import_snapshot(db, self.payload, pg.EXTRACT)
            self.assertEqual(first, rows(db)); self.assertEqual(before, prior_rows(db))
            additions = {t: len(rows(db)[t]) - len(before[t]) for t in TABLES}
            self.assertEqual(additions, dict(dataset=1, source=18, assessment_definition=1,
                economic_definition=1, school=137, economic_observation=137,
                assessment_observation=274, model_run=0, model_result=0))
            self.assertEqual(db.execute('SELECT count(*) FROM assessment_observation WHERE dataset_id=? AND status="reported"',
                                       (pg.DATASET,)).fetchone()[0], 263)
            self.assertEqual(db.execute('SELECT count(*) FROM economic_observation WHERE dataset_id=? AND percentage IS NULL',
                                       (pg.DATASET,)).fetchone()[0], 0)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
    def test_canonical_proxies_orphans_raw_drift_and_foreign_namespace_rejected(self):
        corruptions = [
            "UPDATE model_result SET studentized=99 WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE assessment_observation SET tested=893 WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE assessment_observation SET proficiency=95,status='reported' WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-1253' AND subject='math'",
            "UPDATE assessment_observation SET proficiency=NULL,status='suppressed_or_not_reported' WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE economic_observation SET percentage=0,low_income=0 WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE economic_observation SET percentage=percentage+1e-12 WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE school SET name='Wrong school' WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "UPDATE assessment_observation SET raw_value='{}' WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "INSERT INTO economic_observation SELECT dataset_id,school_id,2024,definition_id,name,enrollment,low_income,percentage,source_label,raw_json,source_id,source_order FROM economic_observation WHERE dataset_id='md-baltimore-county-2025' AND school_id='03-0101'",
            "INSERT INTO model_run SELECT id||':ghost',dataset_id,definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='md-baltimore-county-2025' AND subject='math'",
            "INSERT INTO economic_definition SELECT id||':ghost',name,definition,source_url FROM economic_definition WHERE id='md-baltimore-county-2025:income'",
            "INSERT INTO assessment_definition SELECT id||':ghost',state,name,year,level,grades,standard,source_url FROM assessment_definition WHERE id LIKE 'md-baltimore-county-2025:%'",
            "INSERT INTO model_result VALUES ('other-model','md-baltimore-county-2025','03-0070',9.4,90,1,NULL,NULL)",
            "INSERT INTO source SELECT id||':ghost','other-md',path,url,sha256,imported_at FROM source WHERE id='md-baltimore-county-2025:extract'",
            "INSERT INTO model_run SELECT id||':ghost','other-md',definition_id,subject,method_version,input_sha256,summary_json FROM model_run WHERE dataset_id='md-baltimore-county-2025' AND subject='math'",
            "UPDATE school SET source_id='md-baltimore-county-2025:extract' WHERE dataset_id='other-md'",
            "UPDATE economic_observation SET definition_id='md-baltimore-county-2025:income' WHERE dataset_id='other-md'",
            "UPDATE economic_observation SET source_id='md-baltimore-county-2025:extract' WHERE dataset_id='other-md'",
            "UPDATE assessment_observation SET definition_id=(SELECT id FROM assessment_definition WHERE id LIKE 'md-baltimore-county-2025:%') WHERE dataset_id='other-md'",
            "UPDATE assessment_observation SET source_id='md-baltimore-county-2025:extract' WHERE dataset_id='other-md'",
        ]
        with tempfile.TemporaryDirectory(prefix='corrupt-db-', dir=WORK) as folder:
            wrong = Path(folder) / 'wrong.sqlite'
            for sql in corruptions:
                with closing(connect(self.database)) as source, closing(connect(wrong)) as db:
                    source.backup(db); db.execute(sql); db.commit()
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    pg.validate_canonical(self.payload, wrong, self.numerical)
    def test_static_ghosts_counts_income_promotion_and_nonfinite_metrics_rejected(self):
        originals = {p.name: p.read_bytes() for p in self.output.glob('*.json')}
        with tempfile.TemporaryDirectory(prefix='corrupt-export-', dir=WORK) as folder:
            folder = Path(folder); descriptor = json.loads(originals['catalog.json'])
            descriptor['regions'][0].update(schools=str((folder / 'schools.json').relative_to(ROOT)),
                audit=str((folder / 'coverage.json').relative_to(ROOT)))
            originals['catalog.json'] = json.dumps(descriptor).encode()
            for filename, mutate in [
                ('schools.json', lambda d: d['models'].update(HS=d['models']['ES'])),
                ('schools.json', lambda d: d['models']['ES']['math'].update(n=126.)),
                ('schools.json', lambda d: d['models']['ES']['math'].update(slope=float('nan'))),
                ('schools.json', lambda d: d['schools'].append(copy.deepcopy(d['schools'][0]))),
                ('schools.json', lambda d: next(x for x in d['schools']if x['id']=='03-0101')['metrics']['math'].update(studentized=99.)),
                ('schools.json', lambda d: next(x for x in d['schools']if x['id']=='03-0101')['metrics']['math'].update(tested=False)),
                ('schools.json', lambda d: next(x for x in d['schools']if x['id']=='03-0101')['metrics']['math'].update(low=0.)),
                ('schools.json', lambda d: next(x for x in d['schools']if x['id']=='03-0101')['metrics']['math'].update(cohort_n=126.)),
                ('schools.json', lambda d: d['schools'][0].update(latitude=0.)),
                ('schools.json', lambda d: d['schools'][0].update(hidden_model={})),
                ('schools.json', lambda d: d.update(hidden_history=[])),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '03-0101').update(income=0.)),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '03-1253')['exclusions'].clear()),
                ('schools.json', lambda d: next(s for s in d['schools'] if s['id'] == '03-1253')['metrics'].update(math=next(x for x in d['schools']if x['id']=='03-0101')['metrics']['math'])),
                ('history.json', lambda d: d['models'][0].update(intercept=-99.)),
                ('history.json', lambda d: d['records'][0].update(income_year=2024)),
                ('history.json', lambda d: d['records'][0]['subjects'].update(extra={})),
                ('history.json', lambda d: d['records'][0].update(raw_count_proxy=100)),
                ('history.json', lambda d: d.update(ghost_records=[])),
                ('coverage.json', lambda d: d['cohorts']['grade']['eligible'].update(combined=137)),
                ('coverage.json', lambda d: d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear()),
                ('catalog.json', lambda d: d['regions'][0].update(name='Statewide', statewide=True)),
            ]:
                for name, content in originals.items(): (folder / name).write_bytes(content)
                changed = json.loads((folder / filename).read_text()); mutate(changed)
                (folder / filename).write_text(json.dumps(changed))
                with self.subTest(filename=filename, mutate=mutate), self.assertRaises(ValueError):
                    pg.validate_exports(self.payload, folder, self.numerical)
    def test_offline_extract_repeatability_keeps_historical_pins_immutable(self):
        paths = [pg.model_audit.ROSTER, pg.model_audit.OUTPUT,
                 ROOT / 'scripts/audit_baltimore_county.py', ROOT / 'scripts/audit_baltimore_county_models.py',
                 ROOT / 'tests/test_baltimore_county_audit.py', ROOT / 'tests/test_baltimore_county_models.py']
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory(prefix='extract-repeat-', dir=WORK) as folder:
            first, second = Path(folder) / 'one.json', Path(folder) / 'two.json'
            with mock.patch.object(pg.roster_audit, 'extract_raw_inputs', side_effect=AssertionError('No original archive access')):
                pg.extract(first); pg.extract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), pg.EXTRACT.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(hashlib.sha256(pg.model_audit.ROSTER.read_bytes()).hexdigest(), pg.model_audit.ROSTER_SHA)
        self.assertEqual(hashlib.sha256(pg.model_audit.OUTPUT.read_bytes()).hexdigest(), pg.NUMERICAL_SHA)


    def test_searchable137_native_profiles_and_separate_point_only_release(self):
        pg.validate(self.payload,self.expected)
        self.assertEqual(self.payload['dataset'],'md-baltimore-county-2025');self.assertEqual(self.payload['state'],{'id':'MD','name':'Maryland'})
        self.assertEqual((self.payload['region'],self.payload['region_name']),('baltimore-county','Baltimore County'))
        self.assertIs(self.payload['statewide'],False);self.assertIs(self.payload['approved_for_source'],True);self.assertIs(self.payload['approved_for_modeling'],True)
        self.assertEqual(len(self.profiles),137);self.assertEqual(len(self.payload['sources']),17)
        self.assertEqual(set(self.profiles),set(self.numerical['frozen_population']['grade_school_configuration_ids']))
        for key,count in [('high_school_configuration_ids',31),('mixed_configuration_ids',3),('primary_configuration_ids',3),('unknown_configuration_ids',4),('unmatched_native_school_ids',0)]:
            self.assertEqual(len(self.numerical['frozen_population'][key]),count);self.assertFalse(set(self.profiles).intersection(self.numerical['frozen_population'][key]))
        self.assertNotIn('03-0219',self.profiles)
        for artifact in [self.roster,self.numerical]:self.assertIs(artifact['approved_for_source'],False);self.assertIs(artifact['approved_for_modeling'],False)
        source=self.payload['source_audit'];reference=source['complete_source_reference']
        self.assertEqual((reference['complete_original_record_count'],reference['complete_original_cell_count']),(4536,75620))
        self.assertEqual(reference['sha256'],pg.model_audit.ROSTER_SHA)
        self.assertNotIn('retained_raw_inputs',source);self.assertNotIn('raw_inputs',self.payload);self.assertNotIn('source_definition_evidence',source)
        self.assertEqual(len(source['retained_scope_exclusions']),41);self.assertEqual(len(source['unmatched_ccd_references']),2);self.assertEqual(len(source['nonoperational_ccd_references']),2)
        self.assertIs(source['release_basis']['ten_valid_scored_floor_certified'],False)
        selection=dict(self.payload['selection']);digest=selection.pop('sha256');self.assertEqual(digest,pg.roster_audit.fingerprint(selection))
        for text in [self.payload['cohorts'][0]['note'],self.payload['coverage_note'],self.payload['methodology']['summary']]:
            for term in ['valid-score count','ten-valid-scored floor','uncertified','sampling intervals','unavailable']:self.assertIn(term,text.casefold())

    def test_all_original_income_bands_native_crosswalks_and_published_masks_dereference(self):
        raw=self.roster['raw_inputs'];tables={t:{e['source_row']:e['raw']for e in raw[t]['records']}for t in ['directory','native_directory','native_income','native_enrollment']}
        assessment={(e['member'],e['worksheet'],e['source_row']):e['raw']for e in raw['native_assessment']['records']}
        multi=[]
        for profile in self.payload['schools']:
            link=self.links[profile['id']];refs=profile['identity_raw']['source_refs'];ccd=tables['directory'][refs['directory_source_row']];native=tables['native_directory'][refs['native_directory']['source_row']]
            self.assertEqual((ccd['NCESSCH'],ccd['LEAID'],ccd['ST_LEAID'],ccd['ST_SCHID']),(profile['ncessch'],'2400120','MD-03',profile['identity_raw']['native_school_id']))
            self.assertEqual(str(native['NCES Number']),profile['ncessch']);self.assertEqual(profile['id'],'03-'+native['School'])
            income=tables['native_income'][refs['income']['selected_source_row']]
            self.assertEqual(profile['enrollment'],int(income['Total Student Cnt']));self.assertEqual(profile['low_income'],int(income['Economically Disadvantaged Cnt']))
            self.assertEqual(profile['income'],100*profile['low_income']/profile['enrollment'])
            self.assertEqual(profile['income_raw']['source_refs'],refs['income']);self.assertEqual(refs['income']['source_rows'],link['income']['source_rows'])
            if len(refs['income']['source_rows'])>1:multi.append(profile['id']);self.assertEqual(income['School Type'],'All')
            self.assertEqual(profile['income_raw']['individual_income']['raw_percentage'],income['Economically Disadvantaged Pct'])
            self.assertEqual(refs['native_enrollment']['source_rows'],link['native_enrollment_rows'])
            for subject in ['math','reading']:
                outcome=profile['outcomes'][subject];ref=outcome['raw']['source_refs'];record=assessment[(ref['member'],ref['worksheet'],ref['source_row'])]
                self.assertEqual((record['Year'],record['LEA'],record['School'],record['Student Group'],record['Assessment'].strip()),(2025,'03',profile['id'][3:],'All Students',pg.model_audit.SUBJECT_LABELS[subject]))
                self.assertEqual(outcome['raw']['original_native_values'],{k:record[k]for k in ['Proficient Pct','Tested Count','Proficient Count']})
                self.assertEqual(outcome['proficiency'],pg.model_audit.original_number(record['Proficient Pct']))
                self.assertIsNone(outcome['tested']);self.assertIsNone(outcome['raw_tested']);self.assertIsNone(outcome['raw']['sampling_variance']);self.assertIs(outcome['raw']['ten_valid_scored_floor_certified'],False)
        self.assertTrue(multi);self.assertIn('03-1253',multi)
        masked=[s for s in self.payload['schools']if s['outcomes']['math']['proficiency']is None]
        self.assertEqual(len(masked),11);self.assertTrue(all(s['outcomes']['reading']['proficiency']is not None for s in masked))
        self.assertTrue(all(s['outcomes']['math']['raw']['original_native_values']['Proficient Pct'].strip()=='<= 5.0'for s in masked))

    def test_individual_income_own_denominator_survives_other_population_discrepancies(self):
        r=self.payload['source_audit']['operational_roster']
        self.assertEqual((r['district_fall_membership'],r['district_september_enrollment'],r['native_september_school_total_sum']),(110024,110024,110015))
        self.assertEqual(r['known_school_early_attendance_enrollment_sum'],110357)
        self.assertEqual(len(r['missing_school_early_attendance_denominator_ids']),8)
        different=[p for p in self.payload['schools']if p['identity_raw']['native_september_enrollment']!=p['enrollment']]
        self.assertTrue(different);self.assertTrue(all(p['income']==100*p['low_income']/p['enrollment']for p in different))
        self.assertIn('All valid-score counts',pg.COUNT_NOTE)
        self.assertIn('own Early Attendance',self.payload['income_definition']['definition'])
        self.assertIn('FARMS',self.payload['income_definition']['definition'])
        self.assertIn('as-of date is unspecified',self.payload['income_definition']['definition'])

    def test_all389_canonical_current_history_results_masks_charters_unknown_metadata(self):
        self.assertEqual(pg.validate_canonical(self.payload,self.database,self.numerical),{'schools':137,'observations':274,'models':3,'results':389})
        self.assertEqual(pg.validate_exports(self.payload,self.output,self.numerical),{f'baltimore-county-2025-ES-{s}':n for s,n in pg.EXPECTED_N.items()})
        served=json.loads((self.output/'schools.json').read_text());selected={p['id']:p for p in served['schools']}
        masked=[]
        for key,school in selected.items():
            if self.profiles[key]['outcomes']['math']['proficiency']is None:
                masked.append(key);self.assertEqual(set(school['metrics']),{'reading'});self.assertEqual(set(school['exclusions']),{'math','combined'})
                self.assertEqual(set(school['history'][0]['subjects']),{'reading'})
            else:self.assertEqual(set(school['metrics']),{'math','reading','combined'});self.assertEqual(school['exclusions'],{})
            self.assertEqual((school['program'],school['latitude'],school['longitude']),('Unclassified',None,None))
            self.assertTrue(all(v['tested']is None and v['low']is None and v['high']is None and 'variance'not in v for v in school['metrics'].values()))
        self.assertEqual(len(masked),11);self.assertTrue(abs(selected['03-0855']['metrics']['math']['studentized'])>2)
        self.assertEqual(sum(self.links[key]['ccd_flags']['charter']=='Yes'for key in selected),0)
        with closing(connect(self.database))as db:
            self.assertEqual({t:len(rows(db)[t])-1 for t in TABLES},dict(dataset=1,source=18,assessment_definition=1,economic_definition=1,school=137,economic_observation=137,assessment_observation=274,model_run=3,model_result=389))

    def test_combined_retains_paired126_population_and_own_studentization(self):
        models={m['subject']:m for m in self.numerical['models']};m,e,c=[models[s]for s in ['math','reading','combined']]
        self.assertEqual((m['coefficients']['n'],e['coefficients']['n'],c['coefficients']['n']),(126,137,126))
        self.assertGreater(abs(c['coefficients']['slope']-(m['coefficients']['slope']+e['coefficients']['slope'])/2),.001)
        ela={r['school_id']:r for r in e['results']}
        self.assertTrue(any(abs(cr['studentized']-(mr['studentized']+ela[cr['school_id']]['studentized'])/2)>.01 for cr,mr in zip(c['results'],m['results'])))
        for row in c['inputs']:self.assertEqual(row['outcome_pct'],(row['outcome_by_subject']['math']+row['outcome_by_subject']['reading'])/2)
        served=json.loads((self.output/'schools.json').read_text())['models']['ES']['combined']
        self.assertAlmostEqual(served['intercept'],c['coefficients']['intercept'],places=10);self.assertAlmostEqual(served['slope'],c['coefficients']['slope'],places=10)

    def test_normalized_mutations_and_direct_evidence_drift_are_rejected(self):
        mutations = [
            lambda d:d['schools'].pop(), lambda d:d['schools'][0].update(id='03-0219'),
            lambda d:d['schools'][0]['identity_raw'].update(native_school_id='MD-03-160218'),
            lambda d:d['schools'][0]['identity_raw']['source_refs'].update(directory_source_row=1.),
            lambda d:d['schools'][0]['identity_raw']['ccd_flags'].update(charter='Yes'),
            lambda d:d['schools'][0]['income_raw']['individual_income'].update(raw_denominator='1'),
            lambda d:d['schools'][0]['outcomes']['math']['raw'].update(sampling_variance=0.),
            lambda d:d['schools'][0]['outcomes']['reading'].update(proficiency=99.),
            lambda d:d['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment'),
            lambda d:d['schools'][0].update(income=True), lambda d:d['schools'][0].update(low_income=0),
            lambda d:next(s for s in d['schools'] if s['id']=='03-1253')['outcomes']['math'].update(proficiency=0.),
            lambda d:d['cohorts'][0].update(allow_point_only=False),
            lambda d:d['cohorts'][0].update(assessment='All grades'),
            lambda d:d['source_audit']['subject_coverage']['math']['excluded_configuration_records'].clear(),
            lambda d:d['source_audit']['retained_scope_exclusions'].clear(),
            lambda d:d['source_audit']['complete_source_reference'].update(complete_original_cell_count=75620.),
            lambda d:d['source_audit']['release_basis'].update(historical_audits_approved_for_modeling=0),
            lambda d:d['source_audit']['count_definition_status'].update(ten_valid_scored_floor_certified=True),
            lambda d:d['sources']['numerical_audit'].update(sha256='0'*64),
            lambda d:d['selection']['directory_school_ids'].pop(),
            lambda d:d.update(statewide=0), lambda d:d.update(approved_for_modeling=1),
            lambda d:d['schools'][0].update(latitude=0.), lambda d:d['methodology']['details'].clear()]
        for i,mutate in enumerate(mutations):
            changed=copy.deepcopy(self.payload);mutate(changed)
            with self.subTest(i=i),self.assertRaises(ValueError):pg.validate(changed,self.expected)
        for kind in ['source','numerical','bool']:
            source,numeric=copy.deepcopy(self.roster),copy.deepcopy(self.numerical)
            if kind=='source':source['roster_links'].pop()
            elif kind=='numerical':numeric['models'][0]['results'][0]['studentized']+=1.
            else:numeric['approved_for_source']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):pg.build_snapshot(source,numeric)

    def test_cached_normalized_validation_checks_missing_changed_blobs_and_all_pins(self):
        original = Path.read_bytes
        for path in [pg.model_audit.ROSTER, pg.model_audit.OUTPUT]:
            for bad in [b'{}', None]:
                def read(p):
                    if p==path:
                        if bad is None:raise FileNotFoundError('Linked complete evidence missing')
                        return bad
                    return original(p)
                with self.subTest(path=path,bad=bad),mock.patch.object(Path,'read_bytes',read),self.assertRaises((ValueError,FileNotFoundError)):
                    pg.validate(self.payload,self.expected)
        for owner,keys in [(pg,['NUMERICAL_SHA','NUMERICAL_CODE_SHA','NUMERICAL_TESTS_SHA','NUMERICAL_POLICY_SHA']),
                           (pg.model_audit,['ROSTER_SHA','SOURCE_CODE_SHA','SOURCE_TESTS_SHA','SOURCE_POLICY_SHA','SOURCE_RAW_SHA','SOURCE_SCHEMA_SHA','SOURCE_DEFINITION_SHA','SOURCE_IDENTITY_SHA'])]:
            for key in keys:
                with self.subTest(key=key),mock.patch.object(owner,key,'0'*64),self.assertRaises(ValueError):
                    pg.validate(self.payload,self.expected)

    def test_current_numerical_policy_drift_rejects_cached_direct_and_prewrite_paths(self):
        before_files={p.name:p.read_bytes()for p in self.output.glob('*.json')}
        with closing(connect(self.database))as db:before=rows(db)
        for field,bad in [('models','Infer causal effectiveness after dropping influential schools'),('counts','Use enrollment as valid scores'),('minimum_usable_subject_schools',True)]:
            policy=copy.deepcopy(pg.model_audit.POLICY);policy[field]=bad
            with self.subTest(field=field),mock.patch.object(pg.model_audit,'POLICY',policy):
                with self.assertRaises(ValueError):pg.validate(self.payload,self.expected)
                with self.assertRaises(ValueError):pg.build_snapshot(self.roster,self.numerical)
                with mock.patch.object(pg,'prepare_snapshot',side_effect=AssertionError('No writes before policy validation')),self.assertRaises(ValueError):pg.prepare(self.database,self.output)
        for field,bad in [('MIN_SCHOOLS',True),('ASSESSMENT','DLM alternate'),('STANDARD','Other standard'),('SUBJECTS',['math','reading']),
                          ('SUBJECT_LABELS',{'math':'Algebra 1','reading':'English Language Arts All Grades'}),
                          ('SUBJECT_MEMBERS',{'math':'2025 MCAP ELA Administrative Data Report Card.xlsx','reading':'2025 MCAP ELA Administrative Data Report Card.xlsx'})]:
            with self.subTest(field=field),mock.patch.object(pg.model_audit,field,bad),self.assertRaises(ValueError):pg.validate(self.payload,self.expected)
        with closing(connect(self.database))as db:self.assertEqual(before,rows(db))
        self.assertEqual(before_files,{p.name:p.read_bytes()for p in self.output.glob('*.json')})

    def test_prepare_repeat_and_rejection_preserve_prior_rows_and_exports_before_mutation(self):
        with tempfile.TemporaryDirectory(prefix='repeat-',dir=WORK) as name:
            folder=Path(name);database=folder/'schools.sqlite';output=folder/'output'
            with closing(connect(database)) as db:
                db.executescript((ROOT/'scripts/schema.sql').read_text());seed_other(db);db.commit();before=rows(db)
            run_prepared(pg.prepare,database,output)
            first_files={p.name:p.read_bytes() for p in output.glob('*.json')}
            with closing(connect(database)) as db:first=rows(db)
            run_prepared(pg.prepare,database,output)
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));self.assertEqual(before,prior_rows(db))
            bad=copy.deepcopy(self.payload);bad['schools'][0]['outcomes']['math'].update(tested=100,valid_score_evidence='Enrollment')
            path=folder/'bad.json';path.write_text(json.dumps(bad))
            with mock.patch.object(pg,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):pg.prepare(database,output,path)
                with mock.patch.object(pg,'NUMERICAL_SHA','0'*64),self.assertRaises(ValueError):pg.prepare(database,output)
                with self.assertRaises(ValueError):pg.prepare(database,Path('/tmp/baltimore-county-output'))
            with closing(connect(database)) as db:
                self.assertEqual(first,rows(db));db.execute("UPDATE model_result SET studentized=99 WHERE dataset_id='md-baltimore-county-2025'");db.commit();corrupt=rows(db)
            with mock.patch.object(pg,'prepare_snapshot',side_effect=AssertionError('No mutation')):
                with self.assertRaises(ValueError):pg.prepare(database,output)
            with closing(connect(database)) as db:self.assertEqual(corrupt,rows(db))
            self.assertEqual(first_files,{p.name:p.read_bytes() for p in output.glob('*.json')})


    def test_changed_expected_and_coherently_resigned_normalized_public_pin_rejects(self):
        for change in [lambda d:d['schools'][0].update(income=d['schools'][0]['income']+1e-12),
            lambda d:d['schools'][0]['outcomes']['math'].update(tested=10),lambda d:d['cohorts'][0].update(standard='Different threshold')]:
            changed=copy.deepcopy(self.payload);change(changed)
            with mock.patch.object(pg,'NORMALIZED_PAYLOAD_SHA',pg.roster_audit.fingerprint(changed)),self.assertRaises(ValueError):pg.validate(changed,changed)
        built=pg.build_snapshot(self.roster,self.numerical);built['schools'][0]['income']+=1
        with self.assertRaises(ValueError):pg.validate(built,built)
        for name,value in [('MODEL_SCOPE','Pooled release'),('EXPECTED_N',dict(pg.EXPECTED_N,math=126.)),('NUMERICAL_BYTES',float(pg.NUMERICAL_BYTES)),('INCOME_LABEL','FARMS')]:
            with self.subTest(name=name),mock.patch.object(pg,name,value),mock.patch.object(pg,'ADAPTER_CONTRACT_SHA',pg.roster_audit.fingerprint(pg.adapter_contract())),self.assertRaises(ValueError):pg.validate(self.payload,self.expected)

if __name__ == '__main__':
    unittest.main()

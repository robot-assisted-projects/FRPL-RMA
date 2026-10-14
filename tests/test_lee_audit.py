import copy,io,json,sys,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import audit_lee as audit

class LeeOriginalSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.document=json.loads(audit.OUTPUT.read_text());cls.snapshot=audit.load_florida();cls.inputs=cls.document['raw_inputs'];cls.links={r['school_id']:r for r in cls.document['roster_links']}
 def test_complete_source_only_roster_native_membership_and_charters(self):
  c=audit.validate(self.document,self.snapshot)
  self.assertEqual(c['source_rows'],dict(directory=122,lea_directory=1,membership=983,lea_membership=16,native_grades=115,native_income=115,native_assessment=97))
  self.assertEqual((c['original_records'],c['original_typed_cells']),(1449,34610))
  self.assertEqual((c['ccd_directory'],c['operational_roster'],c['nonoperational_directory']),(122,119,3))
  self.assertEqual(c['operational_offered_scope'],{'ES':80,'HS':23,'mixed':16})
  self.assertEqual((c['prospective_source_profiles'],c['prospective_usable_income']),(78,78));self.assertEqual(c['prospective_usable'],dict(math=78,reading=78,combined=78))
  for s in ['math','reading','combined']:self.assertEqual(self.document['cohorts']['prospective_tested_grade_profiles']['subjects'][s]['charter'],{'No':67,'Yes':11})
  self.assertEqual((self.document['scope'],self.document['status']),('source_cohort_audit_only','audit_pending'))
  self.assertIs(self.document['approved_for_source'],False);self.assertIs(self.document['approved_for_modeling'],False)
  for k in ['models','model_results','coefficients','canonical_dataset']:self.assertNotIn(k,self.document)
 def test_exact_original_identity_documented_widths_and_closed_unjoined_holds(self):
  for row in self.inputs['directory']['records']:
   native=audit.ccd_identity(row['raw']);self.assertEqual(native,row['raw']['ST_SCHID'][3:]);self.assertTrue(row['raw']['NCESSCH'].startswith('1201080'));self.assertEqual(len(row['raw']['NCESSCH']),12)
  self.assertEqual(audit.native_code(71,4),'0071');self.assertEqual(audit.native_code('0071',4),'0071')
  for value in [True,71.,'Island School','71x',-1]:
   with self.subTest(v=value),self.assertRaises(ValueError):audit.native_code(value,4)
  self.assertEqual(set(self.document['coverage']['operational_without_native_fall_ids']),{'36-0581','36-0541','36-7001','36-7023'})
  self.assertEqual({r['raw']['ST_SCHID']for r in self.document['nonoperational_directory']},{'FL-36-0782','FL-36-4012','FL-36-4021'})
  self.assertEqual(self.document['coverage']['outside_native_profile_ids'],[])
  for key in ['36-0581','36-0541','36-7001','36-7023']:
   r=self.links[key];self.assertFalse(r['source_profile_eligible']);self.assertIsNone(r['enrolled']);self.assertIsNone(r['income']['percentage'])
  for key,term in [('school-code','four-digit'),('district-code','two-digit')]:
   text=' '.join(p['text']for p in self.inputs['definitions'][key]['original_pages']);self.assertIn(term,text);self.assertIn('2024-25',text)
 def test_complete_omitted_original_ordinals_identity_population_and_digest_inventories(self):
  for table,count in [('membership',13198),('lea_membership',227),('directory',0),('lea_directory',0)]:
   section=self.inputs[table];v=section['complete_district_inventory'];rows=v['omitted_source_ordinals'];self.assertEqual(len(rows),count);self.assertEqual(rows,sorted(set(rows)))
   self.assertEqual([r['source_row']for r in v['omitted_identity_population_inventory']],rows);self.assertFalse(set(rows)&{r['source_row']for r in section['records']})
   self.assertEqual(v['original_district_rows'],len(section['records'])+count);self.assertEqual(sum(v['omitted_populations'].values()),count);self.assertEqual(v['omitted_typed_cells'],count*len(section['header']))
   for row in v['omitted_identity_population_inventory']:self.assertEqual(row['identity_population']['LEAID'],'1201080');self.assertEqual(row['identity_population']['ST_LEAID'],'FL-36')
   self.assertEqual(audit.fingerprint({k:x for k,x in section.items()if k!='records'}),audit.ORIGINAL_METADATA[table])
 def test_original_income_arithmetic_own_February_denominators_and_real_zero(self):
  native={audit.native_identity(e['raw']):e for e in self.inputs['native_income']['records']}
  for r in self.document['roster_links']:
   if not r['source_profile_eligible']:continue
   raw=native[r['school_id']]['raw'];self.assertEqual(r['income']['survey_enrollment'],raw[4]);self.assertEqual(r['income']['individual_eligible'],raw[5]+raw[6]+raw[8]);self.assertEqual(r['income']['percentage'],100*(raw[5]+raw[6]+raw[8])/raw[4]);self.assertEqual(raw[7],0)
  zero=self.links['36-4100'];self.assertEqual(zero['name'],'THE ISLAND SCHOOL');self.assertEqual((zero['income']['survey_enrollment'],zero['income']['individual_eligible'],zero['income']['percentage']),(66,0,0.))
  c=self.document['coverage'];self.assertEqual((c['district_ccd_enrollment'],c['operational_ccd_enrollment_sum'],c['district_minus_operational_enrollment']),(102506,102506,0))
  self.assertIn('February',audit.POLICY['income']);self.assertIn('1.6',audit.POLICY['income'])
 def test_funding_columns_never_substitute_and_provision2_masks_remain_unknown(self):
  entry=next(e for e in self.inputs['native_income']['records']if audit.native_identity(e['raw'])=='36-0791');baseline=audit.income_evidence(entry)
  changed=copy.deepcopy(entry);changed['raw'][9:12]=[999999,999999,1.]
  self.assertEqual(audit.income_evidence(changed)['percentage'],baseline['percentage'])
  for value in [1,'*',None]:
   row=copy.deepcopy(entry);row['raw'][7]=value;result=audit.income_evidence(row);self.assertIsNone(result['percentage']);self.assertIn('Provision2',result['exclusion'])
  row=copy.deepcopy(entry);row['raw'][5]='*';self.assertIsNone(audit.income_evidence(row)['individual_eligible'])
  row=copy.deepcopy(entry);row['raw'][5:9]=[0,0,0,0];self.assertEqual(audit.income_evidence(row)['percentage'],0.)
 def test_primary_and_provider_missing_scope_offered_and_enrolled_are_separate(self):
  primary=self.links['36-9123'];self.assertFalse(primary['source_profile_eligible']);self.assertEqual(primary['enrolled']['positive_or_protected_tested_grades'],[])
  native=next(e for e in self.inputs['native_income']['records']if audit.native_identity(e['raw'])=='36-9123');self.assertEqual(primary['income']['survey_enrollment'],native['raw'][4])
  self.assertFalse(self.links['36-7023']['source_profile_eligible']);self.assertIsNone(self.links['36-7023']['income']['percentage'])
  self.assertEqual((self.document['coverage']['protected_native_grade_profiles'],self.document['coverage']['protected_native_grade_cells'],self.document['coverage']['offered_enrolled_disagreement_profiles']),(25,70,16))
  entry=next(e for e in self.inputs['native_grades']['records']if audit.native_identity(e['raw'])=='36-0791')
  lower=copy.deepcopy(entry);lower['raw'][8]='*';e=audit.enrolled_evidence(lower);self.assertIsNone(e['values']['3']['reported_count']);self.assertEqual(e['values']['3']['status'],'protected_positive');self.assertIn('3',e['positive_or_protected_tested_grades'])
  for value in [1,'*',None]:
   high=copy.deepcopy(entry);high['raw'][14]=value;self.assertFalse(audit.enrolled_evidence(high)['native_grade_school_contract'])
 def test_whole_original_published_rates_no_grade_averaging_and_no_counts_floor_intervals(self):
  originals={e['source_row']:e['raw']for e in self.inputs['native_assessment']['records']}
  for r in self.document['roster_links']:
   for subject,column in [('math',9),('reading',6)]:
    outcome=r['subjects'][subject]
    if outcome['source_row']is not None:self.assertEqual(outcome['raw_rate'],originals[outcome['source_row']][column]);self.assertEqual(outcome['native_rate'],audit.published_rate(originals[outcome['source_row']][column]))
    for k in ['tested','valid_scores','sampling_variance']:self.assertIsNone(outcome[k])
    self.assertIs(outcome['sampling_interval_available'],False);self.assertIs(outcome['ten_valid_scored_floor_certified'],False)
   if r['source_profile_eligible']:self.assertEqual(r['subjects']['combined']['native_rate'],(r['subjects']['math']['native_rate']+r['subjects']['reading']['native_rate'])/2)
  self.assertEqual((self.document['coverage']['provider_assessment_rows'],self.document['coverage']['collocated_assessment_rows'],self.document['coverage']['campus_charter_disagreements']),(0,0,0))
  row=next(e for e in self.inputs['native_assessment']['records']if audit.native_identity(e['raw'])=='36-0791');income=self.links['36-0791']['income']
  for field,value,term in [(3,'302','Provider-specific'),(47,'Y','Collocated')]:
   changed=copy.deepcopy(row);changed['raw'][field]=value;r=audit.outcome_evidence(changed,'math',scope=None,income=income,native_scope=True);self.assertFalse(r['usable']);self.assertIn(term,r['exclusion'])
  changed=copy.deepcopy(row);changed['raw'][7]=100;self.assertEqual(audit.outcome_evidence(changed,'math',scope=None,income=income,native_scope=True)['native_rate'],row['raw'][9])
 def test_complete_primary_workbook_headers_notes_and_assessment_definitions(self):
  self.assertIn('2024-25, Survey 2',self.inputs['native_grades']['header_rows'][0][0]);self.assertIn('Final Survey 3',self.inputs['native_income']['header_rows'][0][0])
  self.assertEqual(self.inputs['native_assessment']['header_rows'][3][6],'English Language Arts Achievement');self.assertEqual(self.inputs['native_assessment']['header_rows'][3][9],'Mathematics Achievement')
  guide=' '.join(p['text']for p in self.inputs['definitions']['grade-guide']['original_pages'])
  for term in ['Datafolio','home-zoned','two (2) years','Level 3','Algebra 1','Geometry','ten (10) students are eligible']:self.assertIn(term,guide)
  lunch=' '.join(p['text']for p in self.inputs['definitions']['lunch-guide']['original_pages']);self.assertIn('Codes 6 and 9 should be converted to code C or D',lunch)
  self.assertTrue(self.inputs['native_income']['notes']);self.assertEqual(len(audit.SOURCES),11)
 def test_source_only_output_approval_integer_aliases_cohort_income_and_counts_reject(self):
  mutations=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d.update(year=2025.),lambda d:d.update(models=[]),lambda d:d['coverage'].update(prospective_source_profiles=78.),lambda d:d['coverage'].update(ten_valid_scored_floor_certified=True),lambda d:d['roster_links'][0]['income'].update(percentage=-1),lambda d:d['roster_links'][0].update(ncessch='120108099999'),lambda d:d['roster_links'][0]['subjects']['math'].update(tested=10)]
  for i,f in enumerate(mutations):
   d=copy.deepcopy(self.document);f(d)
   with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(d,self.snapshot)
 def test_original_raw_header_row_definitions_identity_population_self_repins_fail(self):
  changes=[lambda x:x['directory']['records'][0]['raw'].update(LEAID='1201590'),lambda x:x['directory']['records'][0]['raw'].update(SCHOOL_YEAR='2023-2024'),lambda x:x['native_income']['records'][0]['raw'].__setitem__(2,71.),lambda x:x['native_assessment']['header_rows'][3].__setitem__(9,'English Language Arts Achievement'),lambda x:x['native_income']['notes'].clear(),lambda x:x['definitions']['school-code']['original_pages'].pop(),lambda x:x['membership']['complete_district_inventory']['omitted_identity_population_inventory'].pop(),lambda x:x['membership']['complete_district_inventory']['omitted_source_ordinals'].__setitem__(0,0)]
  for i,f in enumerate(changes):
   d=copy.deepcopy(self.document);f(d['raw_inputs'])
   with self.subTest(i=i),mock.patch.object(audit,'RAW_INPUT_SHA',audit.fingerprint(d['raw_inputs'])),self.assertRaises(ValueError):audit.validate(d,self.snapshot)
 def test_current_runtime_policy_fields_headers_and_coherent_public_resign_reject(self):
  policy=copy.deepcopy(audit.POLICY);policy['income']='Use funding numerator'
  for key,value in [('POLICY',policy),('SUBJECT_COLUMNS',dict(math=6,reading=9)),('INCOME_COLUMNS',dict(denominator=4,free=5,reduced=6,provision2=7,direct=9)),('YEAR',2025.),('NATIVE_DISTRICT','53'),('ORIGINAL_METADATA',{})]:
   with self.subTest(key=key),mock.patch.object(audit,key,value),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
  with mock.patch.object(audit,'POLICY',policy),mock.patch.object(audit,'POLICY_SHA',audit.fingerprint(policy)):
   with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
  changed=copy.deepcopy(audit.SOURCES);changed['income']['sha256']='0'*64
  with mock.patch.object(audit,'SOURCES',changed),mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',audit.fingerprint(audit.runtime_contract())),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
 def test_current_original_missing_and_changed_pins_reject_even_cached_snapshots(self):
  original_open=Path.open;original_stat=Path.stat
  for key,source in audit.SOURCES.items():
   target=ROOT/source['path']
   def broken_stat(path,*args,**kwargs):
    if path==target:raise FileNotFoundError(key)
    return original_stat(path,*args,**kwargs)
   def broken_open(path,*args,**kwargs):
    if path==target:return io.BytesIO(b'changed pinned original')
    return original_open(path,*args,**kwargs)
   with self.subTest(source=key,case='missing'),mock.patch.object(Path,'stat',broken_stat),self.assertRaises(FileNotFoundError):audit.validate(self.document,self.snapshot)
   with self.subTest(source=key,case='changed'),mock.patch.object(Path,'open',broken_open),self.assertRaises(ValueError):audit.validate(self.document,self.snapshot)
 def test_current_complete_secondary_freshness_and_caller_snapshot_aliases_reject(self):
  original=Path.read_bytes
  for bad in [None,b'{}']:
   def replaced(path):
    if path==ROOT/'data/source/florida.json':
     if bad is None:raise FileNotFoundError('Missing Florida source')
     return bad
    return original(path)
   with self.subTest(bad=bad),mock.patch.object(Path,'read_bytes',replaced),self.assertRaises((ValueError,FileNotFoundError)):audit.validate(self.document,self.snapshot)
  changed=copy.deepcopy(self.snapshot);changed['year']=2024
  with self.assertRaises(ValueError):audit.validate(self.document,changed)
 def test_offline_replay_never_decompresses_models_imports_or_original_extracts(self):
  with mock.patch.object(audit,'extract_raw_inputs',side_effect=AssertionError('No extraction')),mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No decompression')),mock.patch.object(audit.florida,'prepare',side_effect=AssertionError('No fits/imports')):
   self.assertEqual(audit.validate(self.document)['prospective_usable'],dict(math=78,reading=78,combined=78))

if __name__=='__main__':unittest.main()

"""Denver source-only original identity, population, income, valid-score and freshness gates."""
import copy,hashlib,io,json,math
from pathlib import Path
import sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_denver as audit
class DenverSourceAuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.document=json.loads(audit.OUTPUT.read_text());cls.inputs=cls.document['raw_inputs'];cls.links={r['school_id']:r for r in cls.document['roster_links']};audit.validate(cls.document)
 def test_exact_original_roster_native_matches_lower_members_and_charters(self):
  d=self.document;c=d['coverage'];self.assertEqual((c['directory_records'],c['operational_records'],c['exact_native_matches']),(198,198,197));self.assertEqual(c['status'],{'Open':197,'New':1})
  self.assertEqual(c['native_enrolled_scopes'],{'HS':43,'ES':138,'mixed':11,'missing':1,'primary':5});self.assertEqual(c['lower_charters'],{'No':103,'Yes':35});self.assertEqual(c['lower_school_types'],{'Regular School':138});self.assertEqual(c['usable'],{'math':131,'reading':134,'combined':131})
  self.assertEqual((c['native_CMAS_school_ids'],c['native_SAT_school_ids']),(150,55));self.assertEqual(c['outside_native_ids'],[]);self.assertEqual(c['model_results'],0)
  for s,n,charters in [('math',131,32),('reading',134,34),('combined',131,32)]:
   cohort=d['cohorts']['subjects'][s];self.assertEqual(len(cohort['member_ids']),n);self.assertEqual(cohort['eligible_charters'],charters);self.assertTrue(cohort['all_members_have_verified_valid_counts']);self.assertTrue(cohort['prospective_sampling_intervals_supported'])
 def test_exact_original_income_fraction_precision_own_counts_and_k12_denominator(self):
  tables=self.inputs['tables'];income={audit.native_identity(e['raw']):e for e in tables['income']['records']}
  for l in self.links.values():
   v=l['income'];entry=income.get(l['native_school_id'])
   if entry is None:self.assertFalse(v['usable']);continue
   raw=entry['raw'];self.assertEqual(v['source_row'],entry['source_row']);self.assertEqual(v['denominator'],audit.count(raw['K-12 Count']));self.assertEqual(v['eligible'],audit.count(raw['Free and Reduced Count']))
   if l['native_enrollment']['reconciled']:self.assertEqual(v['denominator'],l['native_enrollment']['k12'])
   if v['usable']:
    self.assertEqual(v['percentage'],100*audit.number(raw['% Free and Reduced']));self.assertLessEqual(abs(v['eligible']/v['denominator']-v['published_fraction']),.00051);self.assertTrue(v['prekindergarten_excluded'])
  # Published three-decimal precision is retained rather than replaced by count ratio.
  self.assertTrue(any(l['income']['usable']and l['income']['percentage']!=100*l['income']['eligible']/l['income']['denominator']for l in self.links.values()))
 def test_native_identity_never_uses_names_numeric_padding_or_other_districts(self):
  good={'District Code':'0880','School Code':'0099'};self.assertEqual(audit.native_identity(good),'CO-0880-0099')
  for raw in [dict(good,**{'District Code':880}),dict(good,**{'School Code':99}),dict(good,**{'School Code':99.}),dict(good,**{'School Code':True}),dict(good,**{'School Code':'099'}),dict(good,**{'School Code':'0099.0'}),dict(good,**{'District Code':'1010'}),{'School Name':'Academy 360'}]:
   with self.subTest(raw=raw),self.assertRaises(ValueError):audit.native_identity(raw)
  original=copy.deepcopy(self.inputs['tables']['directory']['records'][0]['raw']);self.assertEqual(audit.ccd_identity(original),original['NCESSCH'])
  for field,value in [('NCESSCH','80336000330'),('ST_SCHID','CO-0881-0010'),('LEAID','0803361'),('ST_LEAID','CO-1010'),('SCHOOL_YEAR','2023-2024')]:
   with self.subTest(field=field),self.assertRaises(ValueError):audit.ccd_identity(dict(original,**{field:value}))
 def test_original_offered_enrolled_high_primary_and_uncertain_rules_are_distinct(self):
  entry=next(e for e in self.inputs['tables']['grades']['records']if e['raw']['School Code']=='0099');g=audit.grade_evidence(entry);self.assertEqual(g['scope'],'ES');self.assertTrue(g['positive_tested']);self.assertTrue(g['explicit_zero_high'])
  d=copy.deepcopy(entry);d['raw']['9th']=1;d['raw']['PK-12 Count']+=1;self.assertEqual(audit.grade_evidence(d)['scope'],'mixed')
  d=copy.deepcopy(entry);d['raw']['9th']='*';self.assertEqual(audit.grade_evidence(d)['scope'],'uncertain');self.assertFalse(audit.grade_evidence(d)['explicit_zero_high'])
  d=copy.deepcopy(entry);d['raw']['PK-12 Count']+=1
  with self.assertRaises(ValueError):audit.grade_evidence(d)
  r=next(e['raw']for e in self.inputs['tables']['directory']['records']if e['raw']['ST_SCHID']=='CO-0880-0099');changed=dict(r,IGOFFERED='Adjusted');self.assertEqual(audit.offered_evidence(changed)['scope'],'uncertain')
  self.assertFalse(self.links['080336006345']['source_profile_eligible'])
  self.assertEqual(sum(l['native_enrollment']['scope']=='primary'for l in self.links.values()),5)
 def test_native_whole_school_cmas_exact_valid_score_ratio_and_population_pointers(self):
  table=self.inputs['tables']['cmas'];by_row={e['source_row']:e['raw']for e in table['records']}
  self.assertEqual(table['worksheet'],'CMAS ELA and Math');self.assertEqual(table['header_source_row'],18)
  for l in self.links.values():
   for s,content in audit.SUBJECTS.items():
    p=l['subjects'][s]
    if not p['present']:continue
    r=by_row[p['source_row']];self.assertEqual((r['District Code'],r['School Code'],r['Level'],r['Grade'],r['Content']),('0880',l['native_school_id'][-4:],'SCHOOL','All Grades',content))
    self.assertEqual(p['valid_scores'],audit.count(r['Number of Valid Scores']));self.assertEqual(p['proficient_count'],audit.count(r['Number Met or Exceeded Expectations']))
    if p['source_usable']:self.assertEqual(p['proficiency'],100*p['proficient_count']/p['valid_scores']);self.assertLessEqual(abs(p['proficiency']-p['published_percentage']),.051);self.assertGreaterEqual(p['valid_scores'],16);self.assertTrue(p['ten_valid_scored_floor_certified'])
  self.assertEqual(min(l['subjects']['math']['valid_scores']for l in self.links.values()if l['subjects']['math']['usable']),52);self.assertEqual(min(l['subjects']['reading']['valid_scores']for l in self.links.values()if l['subjects']['reading']['usable']),22)
 def test_combined_is_paired_mean_with_subject_counts_and_no_invented_paired_count(self):
  for l in self.links.values():
   m,e,c=[l['subjects'][s]for s in['math','reading','combined']];self.assertIsNone(c['valid_scores']);self.assertTrue(c['no_invented_paired_count']);self.assertEqual(c['usable'],m['usable']and e['usable']);self.assertEqual(c['valid_score_components'],{'math':m['valid_scores'],'reading':e['valid_scores']})
   if m['source_usable']and e['source_usable']:self.assertEqual(c['proficiency'],(m['proficiency']+e['proficiency'])/2)
  self.assertEqual(set(self.document['cohorts']['subjects']['combined']['member_ids']),set(self.document['cohorts']['subjects']['math']['member_ids'])&set(self.document['cohorts']['subjects']['reading']['member_ids']))
 def test_masks_remain_profiles_ela_survives_math_gaps_and_gilliam_never_name_joins(self):
  for key in ['080336000362','080336006592','080336006748']:
   l=self.links[key];self.assertTrue(l['source_profile_eligible']);self.assertFalse(l['subjects']['math']['usable']);self.assertTrue(l['subjects']['reading']['usable']);self.assertFalse(l['subjects']['combined']['usable'])
  for key in ['080336000375','080336000410','080336006457','080336006559']:
   l=self.links[key];self.assertTrue(l['source_profile_eligible']);self.assertIsNone(l['income']['percentage']);self.assertTrue(l['subjects']['math']['source_usable']);self.assertFalse(l['subjects']['reading']['usable'])
  g=self.links['080336006345'];self.assertEqual(g['native_school_id'],'CO-0880-9803');self.assertFalse(g['native_enrollment']['present']);self.assertEqual(g['ccd_membership']['reported_total'],21)
  self.assertEqual(self.document['coverage']['district_reported_enrollment'],90471);self.assertEqual(self.document['coverage']['known_native_operational_PK12'],90450);self.assertEqual(self.document['coverage']['district_minus_known_native'],21);self.assertTrue(self.document['coverage']['unassigned_native_membership_difference'])
  self.assertTrue(all(l[k]is None for l in self.links.values()for k in['admissions','program','virtual_provider','geometry']))
 def test_complete_needed_omitted_original_inventories_headers_and_typed_cells(self):
  c=self.document['coverage'];self.assertEqual((c['original_needed_records'],c['original_needed_typed_cells']),(4114,109598));self.assertEqual((c['complete_target_original_records'],c['complete_target_typed_cells']),(25066,486050));self.assertEqual(c['omitted_original_records'],20952)
  for table,s in self.inputs['tables'].items():
   self.assertEqual(len(s['records']),audit.ORIGINAL_INVENTORIES[table]);self.assertEqual(len(s['records'])+len(s['omitted']),s['complete_target_records']);self.assertEqual(len({e['source_row']for e in s['records']+s['omitted']}),s['complete_target_records'])
   for e in s['omitted']:self.assertEqual(len(e['raw_sha256']),64);self.assertIn('identity',e);self.assertIn('population',e)
   if table in{'grades','income','cmas','sat'}:
    for e in s['records']:self.assertEqual(e['raw'],{k:v for k,v in zip(s['header'],e['raw_cells'])if k is not None})
  self.assertIsNone(self.inputs['tables']['income']['raw_header'][-1]);self.assertEqual(audit.fingerprint(self.inputs),audit.RAW_INPUT_SHA)
 def test_whole_primary_definitions_native_headers_and_valid_score_population_notes(self):
  d=self.inputs['definitions'];pdf=d['co_cmas_layout']['pages'];self.assertEqual(len(pdf),26);self.assertEqual(len(d['co_sat_layout']['pages']),14);self.assertIn('Students without scores are not included in the denominator',pdf[2]['text']);self.assertIn('Number of Valid Scores',pdf[9]['text']);self.assertIn('DDDDSSSS',pdf[6]['text']);self.assertIn('Expelled',pdf[3]['text']);self.assertIn('Medical Exemption',pdf[3]['text'])
  self.assertIn('2024-2025',str(d['co_grades']['initial_rows'][1]));self.assertIn('Based on the 2020 Colorado Academic Standards',str(d['co_cmas']['initial_rows']));self.assertIn('The 2024-2025 Pupil Membership data is based upon the Student October Count',d['co_income_archive']['original_html']);self.assertIn('regardless of eligibility',d['co_eligibility']['original_html'])
  self.assertEqual(self.inputs['secondary']['source_id'],'co_secondary');self.assertTrue(self.inputs['secondary']['only_original_fields_no_source_model_authority'])
 def test_raw_source_rows_header_cell_types_primary_and_omission_corruptions_reject(self):
  changes=[lambda d:d['raw_inputs']['tables']['income']['records'][0]['raw_cells'].__setitem__(4,True),lambda d:d['raw_inputs']['tables']['directory']['header'].reverse(),lambda d:d['raw_inputs']['tables']['membership']['omitted'][0]['identity'].update(LEAID='0803361'),lambda d:d['raw_inputs']['tables']['cmas']['records'][0]['raw'].update(Content='Science'),lambda d:d['raw_inputs']['definitions']['co_cmas_layout']['pages'][0].update(text='Different year/definition'),lambda d:d['raw_inputs']['tables']['grades']['records'][0].update(source_row=522.),lambda d:d['raw_inputs']['secondary']['snapshot']['profiles'].pop()]
  for i,change in enumerate(changes):
   d=copy.deepcopy(self.document);change(d)
   with self.subTest(i=i),self.assertRaises(ValueError):audit.validate(d)
 def test_literal_policy_runtime_types_and_coherent_public_repin_cannot_authorize(self):
  policy=copy.deepcopy(audit.POLICY);policy['income']='All free meals imply100% disadvantage'
  changes=[('POLICY',policy),('MIN_VALID',16.),('MIN_VALID',False),('LEA','0803361'),('NATIVE_DISTRICT','1010'),('GRADES',audit.GRADES[:-1]),('SUBJECTS',dict(audit.SUBJECTS,reading='Spanish Language Arts')),('RAW_INPUT_SHA','0'*64),('ORIGINAL_SCHEMA_SHA','0'*64),('DEFINITION_INPUT_SHA','0'*64),('ORIGINAL_IDENTITY_SHA','0'*64)]
  for field,value in changes:
   with self.subTest(field=field),mock.patch.object(audit,field,value):
    resigned=audit.fingerprint(audit.runtime_contract());policy_sha=audit.fingerprint(audit.POLICY)
    with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',resigned),mock.patch.object(audit,'POLICY_SHA',policy_sha),self.assertRaises(ValueError):audit.validate(self.document)
 def test_current_whole_original_and_secondary_files_cannot_disappear_or_change_under_cached_replay(self):
  original_open=Path.open
  for key,pin in audit.SOURCES.items():
   target=audit.ROOT/pin['path']
   for missing in[True,False]:
    def corrupt(path,*args,**kwargs):
     if path==target and args and args[0]=='rb':
      if missing:raise FileNotFoundError('Private missing current original fixture')
      return io.BytesIO(b'X'*pin['bytes'])
     return original_open(path,*args,**kwargs)
    with self.subTest(source=key,missing=missing),mock.patch.object(Path,'open',corrupt),self.assertRaises((FileNotFoundError,ValueError)):audit.validate(self.document)
  sources=copy.deepcopy(audit.SOURCES);next(iter(sources.values()))['sha256']='0'*64
  with mock.patch.object(audit,'SOURCES',sources):
   resigned=audit.fingerprint(audit.runtime_contract())
   with mock.patch.object(audit,'RUNTIME_CONTRACT_SHA',resigned),self.assertRaises(ValueError):audit.validate(self.document)
 def test_current_semantic_helpers_cannot_use_saved_literal_inputs_to_bypass_fresh_contract(self):
  for helper in['native_identity','income_evidence','outcome_evidence','summarize','source_sha','extract_raw_inputs']:
   with self.subTest(helper=helper),mock.patch.object(audit,helper,lambda *a,**k:None),self.assertRaises(ValueError):audit.validate(self.document)
  self.assertEqual(audit.validate(self.document),{'profiles':138,'subjects':{'math':131,'reading':134,'combined':131},'approved_for_source':False,'approved_for_modeling':False})
 def test_saved_derived_values_count_aliases_approvals_profiles_and_metadata_require_exact_replay(self):
  changes=[lambda d:d.update(approved_for_source=0),lambda d:d.update(approved_for_modeling=True),lambda d:d['coverage'].update(directory_records=198.),lambda d:d['roster_links'][0].update(native_school_id='CO-0880-9999'),lambda d:d['roster_links'].pop(),lambda d:d['sources']['co_cmas'].update(sha256='0'*64),lambda d:d['cohorts']['subjects']['combined']['member_ids'].pop(),lambda d:d.update(schema_version=True)]
  key=next(i for i,r in enumerate(self.document['roster_links'])if r['subjects']['math']['usable'])
  changes.extend([lambda d:d['roster_links'][key]['income'].update(percentage=d['roster_links'][key]['income']['percentage']+1e-12),lambda d:d['roster_links'][key]['subjects']['math'].update(valid_scores=False),lambda d:d['roster_links'][key]['subjects']['math'].update(proficiency=float('nan')),lambda d:d['roster_links'][key]['subjects']['combined'].update(valid_scores=100)])
  for i,change in enumerate(changes):
   d=copy.deepcopy(self.document);change(d)
   with self.subTest(i=i),self.assertRaises((ValueError,TypeError)):audit.validate(d)
 def test_zero_counts_masks_bounded_values_and_own_income_never_recover_missing_eligibility(self):
  for value,want in[(0,0),('0',0),(' 1,234 ',1234),('*',None),('< 16',None),('- -',None),(None,None)]:self.assertEqual(audit.count(value),want)
  for value in[False,True,1.5,-1,float('nan')]:
   with self.assertRaises(ValueError):audit.count(value)
  key=next(k for k,l in self.links.items()if l['source_profile_eligible']and l['income']['usable']);l=self.links[key];entry=next(e for e in self.inputs['tables']['income']['records']if audit.native_identity(e['raw'])==l['native_school_id']);zero=copy.deepcopy(entry);n=zero['raw']['K-12 Count'];zero['raw'].update({'Free Lunch':0,'Reduced Lunch':0,'Free and Reduced Count':0,'Paid Lunch':n,'% Free and Reduced':0.})
  v=audit.income_evidence(zero,l['native_enrollment']);self.assertTrue(v['usable']);self.assertEqual(v['percentage'],0.)
  zero['raw']['% Free and Reduced']='*';v=audit.income_evidence(zero,l['native_enrollment']);self.assertFalse(v['usable']);self.assertIsNone(v['percentage'])
 def test_offline_validation_reuses_complete_cells_without_reextracting_or_writing(self):
  before=audit.OUTPUT.read_bytes()
  with mock.patch.object(audit,'extract_raw_inputs',wraps=audit.extract_raw_inputs)as extractor,mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No original stream required in offline validation')):
   # Wrapping a guarded semantic declaration is correctly rejected. The actual
   # offline positive path patches only subprocess and leaves source helpers intact.
   with self.assertRaises(ValueError):audit.validate(self.document)
  with mock.patch.object(audit.subprocess,'Popen',side_effect=AssertionError('No original stream required in offline validation')):self.assertEqual(audit.validate(self.document)['profiles'],138)
  self.assertEqual(before,audit.OUTPUT.read_bytes())
if __name__=='__main__':unittest.main()

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plan_district_comparisons import (EXTRACT, membership_totals,
    potential_cohort, scope, size_tier, validate)


class DistrictPlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(EXTRACT.read_text())
        cls.rows = {row['nces_lea_id']: row for row in cls.payload['agencies']}

    def test_native_district_totals_and_existing_scopes_are_preserved(self):
        validate(self.payload)
        # LEA totals differ from summing individual school membership. The
        # planning screen must use the independently published LEA population.
        self.assertEqual(self.rows['0622710']['enrollment'], 408026)
        self.assertEqual(self.rows['0622710']['scope'], 'existing_los_angeles')
        self.assertEqual(self.rows['1200390']['scope'], 'existing_miami_dade')
        self.assertEqual(self.rows['1200480']['scope'], 'existing_duval')
        self.assertEqual(self.rows['1200480']['native_lea_id'], 'FL-16')
        self.assertEqual(self.rows['1200480']['enrollment'], 130054)
        self.assertEqual(self.rows['1200480']['potential_cohorts'], {'ES': 151, 'HS': 24})
        self.assertEqual(self.rows['1201590']['scope'], 'existing_polk')
        self.assertEqual(self.rows['1201590']['native_lea_id'], 'FL-53')
        self.assertEqual(self.rows['1201590']['enrollment'], 111372)
        self.assertEqual(self.rows['1201590']['potential_cohorts'], {'ES': 110, 'HS': 16})
        self.assertEqual(self.rows['1201080']['scope'], 'existing_lee')
        self.assertEqual(self.rows['1201080']['native_lea_id'], 'FL-36')
        self.assertEqual(self.rows['1201080']['enrollment'], 102506)
        self.assertEqual(self.rows['1201080']['potential_cohorts'], {'ES': 78, 'HS': 21})
        self.assertEqual(self.rows['1301290']['scope'], 'existing_cobb')
        self.assertEqual(self.rows['1301290']['native_lea_id'], 'GA-633')
        self.assertEqual(self.rows['1301290']['enrollment'], 105738)
        self.assertEqual(self.rows['1301290']['potential_cohorts'], {'ES': 90, 'HS': 16})
        self.assertEqual(self.rows['2400120']['scope'], 'existing_baltimore_county')
        self.assertEqual(self.rows['2400120']['native_lea_id'], 'MD-03')
        self.assertEqual(self.rows['2400120']['enrollment'], 110024)
        self.assertEqual(self.rows['2400120']['potential_cohorts'], {'ES': 139, 'HS': 30})
        self.assertEqual(self.rows['4700148']['scope'], 'existing_memphis')
        self.assertEqual(self.rows['4700148']['native_lea_id'], 'TN-00792')
        self.assertEqual(self.rows['4700148']['enrollment'], 111124)
        self.assertEqual(self.rows['4700148']['potential_cohorts'], {'ES': 154, 'HS': 36})
        self.assertEqual(self.rows['4218990']['scope'], 'existing_philadelphia')
        self.assertEqual(self.rows['4218990']['native_lea_id'], 'PA-126515001')
        self.assertEqual(self.rows['4218990']['enrollment'], 120057)
        self.assertEqual(self.rows['4218990']['potential_cohorts'], {'ES': 162, 'HS': 47})
        self.assertEqual(self.rows['4833120']['scope'], 'existing_northside')
        self.assertEqual(self.rows['4833120']['native_lea_id'], 'TX-015915')
        self.assertEqual(self.rows['4833120']['enrollment'], 100208)
        self.assertEqual(self.rows['4833120']['potential_cohorts'], {'ES': 107, 'HS': 16})
        self.assertEqual(self.rows['4816110']['scope'], 'existing_cypress_fairbanks')
        self.assertEqual(self.rows['4816110']['native_lea_id'], 'TX-101907')
        self.assertEqual(self.rows['4816110']['enrollment'], 117927)
        self.assertEqual(self.rows['4816110']['potential_cohorts'], {'ES': 78, 'HS': 13})
        self.assertEqual(self.rows['1200180']['scope'], 'existing_broward')
        self.assertEqual(self.rows['1200180']['enrollment'], 243553)
        self.assertEqual(self.rows['1200180']['potential_cohorts'], {'ES': 243, 'HS': 45})
        self.assertEqual(self.rows['1200870']['scope'], 'existing_hillsborough')
        self.assertEqual(self.rows['1200870']['enrollment'], 220360)
        self.assertEqual(self.rows['1200870']['potential_cohorts'], {'ES': 218, 'HS': 34})
        self.assertEqual(self.rows['1201440']['scope'], 'existing_orange')
        self.assertEqual(self.rows['1201440']['enrollment'], 205853)
        self.assertEqual(self.rows['1201440']['potential_cohorts'], {'ES': 206, 'HS': 31})
        self.assertEqual(self.rows['1201500']['scope'], 'existing_palm_beach')
        self.assertEqual(self.rows['1201500']['enrollment'], 189634)
        self.assertEqual(self.rows['1201500']['potential_cohorts'], {'ES': 168, 'HS': 26})
        self.assertEqual(self.rows['1302550']['scope'], 'existing_gwinnett')
        self.assertEqual(self.rows['1302550']['enrollment'], 182518)
        self.assertEqual(self.rows['1302550']['potential_cohorts'], {'ES': 111, 'HS': 24})
        self.assertEqual(self.rows['5101260']['scope'], 'existing_fairfax')
        self.assertEqual(self.rows['5101260']['native_lea_id'], 'VA-029')
        self.assertEqual(self.rows['5101260']['enrollment'], 179323)
        self.assertEqual(self.rows['5101260']['potential_cohorts'], {'ES': 162, 'HS': 25})
        self.assertEqual(self.rows['4823640']['scope'], 'existing_houston')
        self.assertEqual(self.rows['4823640']['native_lea_id'], 'TX-101912')
        self.assertEqual(self.rows['4823640']['enrollment'], 176727)
        self.assertEqual(self.rows['4823640']['potential_cohorts'], {'ES': 212, 'HS': 42})
        self.assertEqual(self.rows['3704720']['scope'], 'existing_wake')
        self.assertEqual(self.rows['3704720']['native_lea_id'], 'NC-920')
        self.assertEqual(self.rows['3704720']['enrollment'], 163325)
        self.assertEqual(self.rows['3704720']['potential_cohorts'], {'ES': 162, 'HS': 29})
        self.assertEqual(self.rows['2400480']['scope'], 'existing_montgomery')
        self.assertEqual(self.rows['2400480']['native_lea_id'], 'MD-15')
        self.assertEqual(self.rows['2400480']['enrollment'], 159181)
        self.assertEqual(self.rows['2400480']['potential_cohorts'], {'ES': 172, 'HS': 25})
        self.assertEqual(self.rows['3702970']['scope'], 'existing_charlotte')
        self.assertEqual(self.rows['3702970']['native_lea_id'], 'NC-600')
        self.assertEqual(self.rows['3702970']['enrollment'], 147299)
        self.assertEqual(self.rows['3702970']['potential_cohorts'], {'ES': 146, 'HS': 25})
        self.assertEqual(self.rows['4816230']['scope'], 'existing_dallas')
        self.assertEqual(self.rows['4816230']['native_lea_id'], 'TX-057905')
        self.assertEqual(self.rows['4816230']['enrollment'], 139802)
        self.assertEqual(self.rows['4816230']['potential_cohorts'], {'ES': 189, 'HS': 37})
        self.assertEqual(self.rows['2400510']['scope'], 'existing_prince_georges')
        self.assertEqual(self.rows['2400510']['native_lea_id'], 'MD-16')
        self.assertEqual(self.rows['2400510']['enrollment'], 132123)
        self.assertEqual(self.rows['2400510']['potential_cohorts'], {'ES': 160, 'HS': 23})
        self.assertEqual(self.rows['3200060']['scope'], 'existing_clark_county')
        self.assertEqual(self.rows['3200060']['enrollment'], 306038)
        self.assertEqual(self.rows['3200060']['potential_cohorts'], {'ES': 296, 'HS': 10})
        self.assertNotEqual(self.rows['0622710']['enrollment'], 406717)
        self.assertEqual(self.rows['1709930']['enrollment'], 324130)
        self.assertEqual(self.rows['1709930']['scope'], 'existing_chicago')
        self.assertEqual(self.rows['1500030']['scope'], 'existing_hawaii_statewide')
        self.assertEqual(self.rows['3600077']['scope'], 'existing_nyc_component')
        self.assertEqual(self.rows['4800211']['scope'], 'other_agency_scope_review')
        self.assertEqual(self.rows['5102250']['scope'], 'district_charter_status_review')
        self.assertFalse(self.payload['approved_for_modeling'])
        self.assertFalse(self.payload['browser_catalog'])

    def test_duplicate_wrong_year_or_demographic_subtotal_is_rejected(self):
        original = self.rows['0622710']['membership_raw']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            membership_totals([original, original])
        for field, value, pattern in [('SCHOOL_YEAR', '2023-2024', 'Wrong-year'),
                                      ('GRADE', 'Grade 3', 'demographic subtotal')]:
            bad = dict(original, **{field: value})
            with self.assertRaisesRegex(ValueError, pattern):
                membership_totals([bad])

    def test_foreign_identity_unreported_enrollment_and_false_approval_fail(self):
        for field, value, pattern in [('enrollment', 406717, 'enrollment differs'),
                                      ('native_lea_id', 'CA-0000000', 'identity differs')]:
            payload = copy.deepcopy(self.payload)
            payload['agencies'][0][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                validate(payload)
        payload = copy.deepcopy(self.payload)
        payload['agencies'][0]['membership_raw']['DMS_FLAG'] = 'Not reported'
        with self.assertRaisesRegex(ValueError, 'enrollment differs'):
            validate(payload)
        payload = copy.deepcopy(self.payload)
        payload['agencies'][0]['potential_school_ids']['ES'][0] = '120039000001'
        with self.assertRaisesRegex(ValueError, 'foreign or duplicated'):
            validate(payload)
        payload = copy.deepcopy(self.payload)
        payload['approved_for_modeling'] = True
        with self.assertRaisesRegex(ValueError, 'cannot grant modeling approval'):
            validate(payload)

    def test_high_school_population_cannot_hide_lower_grade_enrollment(self):
        profile = dict(IGOFFERED='As reported', GSHI='12')
        profile.update({field: 'No' for field in ['G_PK_OFFERED', 'G_KG_OFFERED',
            'G_UG_OFFERED', 'G_AE_OFFERED'] + [f'G_{g}_OFFERED' for g in range(1, 14)]})
        profile['G_9_OFFERED'] = 'Yes'
        total = dict(STUDENT_COUNT='100', DMS_FLAG='Reported')
        grades = {'Grade 9': dict(total)}
        self.assertEqual(potential_cohort(profile, total, grades), 'HS')
        # Even when offers say no lower grades, the enrolled composition wins.
        grades['Grade 9']['STUDENT_COUNT'] = '90'
        grades['Kindergarten'] = dict(STUDENT_COUNT='10', DMS_FLAG='Reported')
        self.assertIsNone(potential_cohort(profile, total, grades))
        grades = {'Grade 9': dict(total)}
        profile['G_8_OFFERED'] = 'Yes'
        self.assertIsNone(potential_cohort(profile, total, grades))
        profile['G_8_OFFERED'] = 'No'
        profile['IGOFFERED'] = 'Adjusted'
        self.assertIsNone(potential_cohort(profile, total, grades))

    def test_primary_only_schools_and_missing_membership_are_not_potential_test_cohorts(self):
        profile = dict(IGOFFERED='As reported', GSHI='02')
        profile.update({field: 'No' for field in ['G_PK_OFFERED', 'G_KG_OFFERED',
            'G_UG_OFFERED', 'G_AE_OFFERED'] + [f'G_{g}_OFFERED' for g in range(1, 14)]})
        profile['G_2_OFFERED'] = 'Yes'
        total = dict(STUDENT_COUNT='100', DMS_FLAG='Reported')
        self.assertIsNone(potential_cohort(profile, total, {'Grade 2': dict(total)}))
        profile['GSHI'] = '03'; profile['G_3_OFFERED'] = 'Yes'
        self.assertEqual(potential_cohort(profile, total, {'Grade 3': dict(total)}), 'ES')
        self.assertIsNone(potential_cohort(profile,
            dict(STUDENT_COUNT='-9', DMS_FLAG='Not reported'), {'Grade 3': dict(total)}))

    def test_district_names_never_determine_identity_or_scope(self):
        cps = copy.deepcopy(self.rows['1709930']['directory_raw'])
        cps['LEAID'] = '9999999'
        self.assertEqual(scope(cps), 'new_district_candidate')
        union = dict(cps, LEAID='3620580', LEA_TYPE='3')
        self.assertEqual(scope(union), 'other_agency_scope_review')
        special = dict(cps, LEAID='3600135', LEA_TYPE='2')
        self.assertEqual(scope(special), 'nyc_special_population_review')
        self.assertIsNone(size_tier(100000, dict(ES=29, HS=29)))
        self.assertEqual(size_tier(40000, dict(ES=0, HS=35)), 'secondary')


if __name__ == '__main__':
    unittest.main()

import unittest
try:
 import formal_snapshot_import as f
except ImportError:
 f=None
class ImportTest(unittest.TestCase):
 def setUp(self): self.assertIsNotNone(f)
 def test_preserves_existing_id_only_for_same_person_and_exact_text(self):
  old=[{'id':'old','speaker_id':'02','text':'原句'}]
  rows=f.parse_tab('2026-10-15','02女：\n原句','t',{'02':{'gender':'女'}},old)
  self.assertEqual(rows[0]['id'],'old')
  rows=f.parse_tab('2026-10-15','02女：\n修订句','t',{'02':{'gender':'女'}},old)
  self.assertNotEqual(rows[0]['id'],'old')
 def test_gender_conflict_stays_out_of_adopted_history(self):
  row=f.parse_tab('2026-10-15','10男：\n原话','t',{'10':{'gender':'女'}},[])[0]
  self.assertEqual(row['status'],'REVIEW_ROLE_MISMATCH')
 def test_duplicate_and_standalone_label(self):
  rows=f.parse_tab('2026-10-15','02女\n原话\n02女：\n原话','t',{'02':{'gender':'女'}},[])
  self.assertEqual(rows[0]['status'],'ADOPTED_IN_USER_SUBMITTED_STORY')
  self.assertEqual(rows[1]['status'],'EXCLUDED_EXACT_DUPLICATE')
if __name__=='__main__': unittest.main()

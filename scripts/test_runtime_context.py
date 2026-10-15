import unittest
from sync_runtime_memory import records_from_members
from validate_runtime_context import ROOT, BEGIN, END, validate

class RuntimeContextTest(unittest.TestCase):
    def setUp(self):
        self.text=(ROOT/'skills/p004-chat-suite/references/runtime-context-v1.5.2.txt').read_text(encoding='utf-8')

    def test_all_five_complete_prompts_match_actual_sources(self):
        for path in (ROOT/'integrations/chatgpt-scheduled').glob('*.txt'):
            self.assertEqual(validate(path.read_text(encoding='utf-8'))['identities'],65)

    def test_missing_identity_rejected(self):
        lines=self.text.splitlines()
        start=lines.index('[IDENTITY_CSV]')
        del lines[start+2]
        with self.assertRaises(ValueError): validate('\n'.join(lines))

    def test_identity_change_rejected(self):
        with self.assertRaises(ValueError): validate(self.text.replace('Ion Dumitrescu','Changed Identity',1))

    def test_voice_change_rejected(self):
        start=self.text.index('[VOICE_REFERENCE]')
        changed=self.text[:start]+self.text[start:].replace('01|','99|',1)
        with self.assertRaises(ValueError): validate(changed)

    def test_unadopted_memory_rejected(self):
        start=self.text.index('[ADOPTED_MEMORY_CONFIRMED]')
        changed=self.text[:start]+self.text[start:].replace('"message_id":','"invented_id":',1)
        with self.assertRaises((ValueError,KeyError)): validate(changed)

    def test_all_current_confirmed_events_present(self):
        result=validate(self.text)
        records=records_from_members()
        self.assertEqual(result['adopted_memory_entries'],len(records))
        self.assertEqual(result['members_with_adopted_history'],len({r['id'] for r in records}))

    def test_cross_member_memory_assignment_rejected(self):
        target='\"id\":\"02\",\"message_id\":\"M006\"'
        self.assertIn(target,self.text)
        with self.assertRaises(ValueError):
            validate(self.text.replace(target,'\"id\":\"65\",\"message_id\":\"M006\"',1))

    def test_truncated_prompt_rejected(self):
        with self.assertRaises(ValueError): validate(self.text.split(END)[0])

    def test_duplicate_snapshot_rejected(self):
        with self.assertRaises(ValueError): validate(self.text+self.text)

if __name__ == '__main__': unittest.main()


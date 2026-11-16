import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from session_handoff import main


class HandoffTests(unittest.TestCase):
    def test_write_check_and_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            artifact = root/'artifact'; artifact.write_text('one')
            draft = {'schema_version': 'session-handoff/1.0', 'objective': 'batch', 'run_dir': str(root),
                     'batch_scope': ['doc-1'], 'completed_artifacts': [{'path': str(artifact), 'sha256': ''}],
                     'next_command': 'check', 'stop_condition': 'done', 'open_blockers': [], 'authorization_refs': []}
            source = root/'draft.json'; source.write_text(json.dumps(draft))
            output = root/'handoff.json'
            with patch('sys.argv', ['handoff', 'write', '--input', str(source), '--output', str(output)]):
                self.assertEqual(main(), 0)
            with patch('sys.argv', ['handoff', 'check', '--handoff', str(output)]):
                self.assertEqual(main(), 0)
            artifact.write_text('changed')
            with patch('sys.argv', ['handoff', 'check', '--handoff', str(output)]):
                self.assertEqual(main(), 2)
            with patch('sys.argv', ['handoff', 'write', '--input', str(source), '--output', str(output)]):
                self.assertEqual(main(), 2)
            draft['extra'] = 'forbidden'; source.write_text(json.dumps(draft))
            with patch('sys.argv', ['handoff', 'write', '--input', str(source), '--output', str(root/'other.json')]):
                self.assertEqual(main(), 2)


if __name__ == '__main__':
    unittest.main()

"""Offline safety checks for the standalone download entry point."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import download_papers as tool

class DownloadSafetyTests(unittest.TestCase):
    def test_elsevier_missing_key_never_requests(self):
        with patch.object(tool.requests, 'get', side_effect=AssertionError('network')):
            self.assertEqual(tool.try_elsevier('10.1016/example', ''), (None, 'no_api_key'))
            self.assertEqual(tool.elsevier_pii_and_si('10.1016/example', ''), (None, [], 'no_api_key'))

    def test_unpaywall_missing_email_skips_with_reason(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(tool.requests, 'get', side_effect=AssertionError('network')), contextlib.redirect_stderr(output):
            self.assertEqual(tool.unpaywall_pdfs('10.1000/example'), [])
        self.assertIn('UNPAYWALL_EMAIL missing', output.getvalue())

    def test_unpaywall_explicit_email_is_used(self):
        from unittest.mock import Mock
        reply = Mock(status_code=200)
        reply.json.return_value = {'oa_locations': [{'url_for_pdf': 'https://example.org/paper.pdf'}]}
        with patch.dict(os.environ, {'UNPAYWALL_EMAIL': 'reader@example.org'}), patch.object(tool.requests, 'get', return_value=reply) as request:
            self.assertEqual(tool.unpaywall_pdfs('10.1000/example'), ['https://example.org/paper.pdf'])
            self.assertEqual(request.call_args.kwargs['params'], {'email': 'reader@example.org'})

    def test_dry_run_does_not_network_or_create_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); dois = root / 'dois.txt'; dois.write_text('10.1016/example\n10.1007/example\n', encoding='utf-8')
            argv = ['download_papers.py', '--dois', str(dois), '--state', str(root/'state'), '--out', str(root/'pdf'), '--dry-run']
            with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'argv', argv), patch.object(tool.requests.sessions.Session, 'request', side_effect=AssertionError('network')), contextlib.redirect_stdout(io.StringIO()) as output:
                tool.main()
            self.assertIn('example', output.getvalue())
            self.assertFalse((root/'state').exists())
            self.assertFalse((root/'pdf').exists())

    def test_missing_credentials_reject_elsevier_before_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); dois = root/'dois.txt'; dois.write_text('10.1016/example\n', encoding='utf-8')
            argv = ['download_papers.py', '--dois', str(dois), '--state', str(root/'state'), '--out', str(root/'pdf')]
            with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'argv', argv), patch.object(tool.requests.sessions.Session, 'request', side_effect=AssertionError('network')), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, 'ELSEVIER_API_KEY missing'):
                    tool.main()
            self.assertFalse((root/'pdf').exists())

if __name__ == '__main__':
    unittest.main()

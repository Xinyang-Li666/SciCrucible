import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ingest_prepare import prepare, DOI, normalize_doi
from extract_pdf import render_pages


class PrepareTests(unittest.TestCase):
    def test_pdf_doi_delimiters_and_elsevier_parentheses(self):
        text = '10.1063/1.3371680兴 10.1063/1.4863841] 10.1016/S0039-6028(01)01050-0.'
        self.assertEqual([normalize_doi(d) for d in DOI.findall(text)],
                         ['10.1063/1.3371680', '10.1063/1.4863841',
                          '10.1016/s0039-6028(01)01050-0'])

    def test_pages_preserve_empty_page(self):
        text = render_pages(['first', '', 'third'])
        self.assertIn('PDF page 2', text)
        self.assertIn('PDF page 3', text)

    def test_batch_isolation_duplicates_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / 'raw/new-papers'
            papers.mkdir(parents=True)
            for name, data in [('a.pdf', b'a'), ('b.pdf', b'a'),
                               ('broken.pdf', b'bad'), ('single.pdf', b's')]:
                (papers / name).write_bytes(data)
            def extract(path):
                if path.name == 'broken.pdf':
                    raise ValueError('damaged PDF')
                if path.name == 'single.pdf':
                    return ['one page']
                return ['doi:10.1234/example ' + 'body ' * 100, 'results ' * 100]
            with patch('ingest_prepare.extract_pages', side_effect=extract):
                result = prepare(root, topic='SiNx')
            self.assertEqual([r['status'] for r in result['papers']],
                             ['ready', 'duplicate_sha256', 'error', 'needs_review'])
            self.assertTrue((papers / 'b.pdf').exists())
            with patch('ingest_prepare.extract_pages', side_effect=extract) as mocked:
                again = prepare(root, topic='SiNx')
                self.assertEqual(mocked.call_count, 1)  # retry only damaged PDF
            self.assertTrue(again['papers'][0]['cache_hit'])
            self.assertEqual(json.loads((root / '.kiro/.ingest_cache/manifest.json').read_text(encoding='utf8'))['topic'], 'SiNx')

    def test_doi_candidates_never_silently_deduplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / 'raw/new-papers'
            papers.mkdir(parents=True)
            (papers / 'a.pdf').write_bytes(b'a')
            (papers / 'b.pdf').write_bytes(b'b')
            (root / 'wiki').mkdir()
            (root / 'wiki/literature_index.json').write_text(json.dumps({'10.1234/example': {'file': 'existing.md'}}))
            pages = ['10.1234/EXAMPLE ' + 'text ' * 100, 'results ' * 100]
            with patch('ingest_prepare.extract_pages', return_value=pages):
                result = prepare(root)
            self.assertTrue(all(r['status'] == 'needs_review' for r in result['papers']))
            self.assertIn('10.1234/example', result['papers'][0]['index_matches'])


if __name__ == '__main__':
    unittest.main()

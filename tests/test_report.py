import tempfile
import unittest
from pathlib import Path
from driftguard.report import render_html, write_html
from driftguard.__main__ import main


class HtmlReportTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {'rows_sampled': 2, 'columns': {'id': {'type': 'integer', 'nulls': 0}}}
        self.current = {'rows_sampled': 1, 'columns': {'id': {'type': 'string', 'nulls': 0}}}

    def test_counts_and_empty_state(self):
        report = {'breaking': True, 'changes': [
            {'column': 'id', 'change': 'type integer -> string', 'severity': 'breaking'},
            {'column': 'extra', 'change': 'added', 'severity': 'informational'}]}
        html = render_html(report, self.baseline, self.current)
        self.assertIn('ACTION REQUIRED', html)
        self.assertIn('type integer -&gt; string', html)
        self.assertIn('No reportable schema changes.', render_html(
            {'breaking': False, 'changes': []}, self.baseline, self.current))

    def test_escapes_untrusted_headers(self):
        report = {'breaking': True, 'changes': [
            {'column': '<script>alert(1)</script>', 'change': '<img src=x onerror=alert(1)>', 'severity': 'breaking'}]}
        html = render_html(report, self.baseline, self.current)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img', html)

    def test_rejects_unknown_severity(self):
        with self.assertRaises(ValueError):
            render_html({'breaking': False, 'changes': [
                {'column': 'x', 'change': 'added', 'severity': 'urgent'}]}, self.baseline, self.current)

    def test_portable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'audit.html'
            write_html(dest, {'breaking': False, 'changes': []}, self.baseline, self.current)
            self.assertTrue(dest.read_text(encoding='utf-8').startswith('<!doctype html>'))

    def test_cli_writes_report_and_preserves_breaking_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'before.csv'
            source.write_text('id\\n1\\n'.replace('\\n', '\n'), encoding='utf-8')
            changed = root / 'after.csv'
            changed.write_text('id\\ntext\\n'.replace('\\n', '\n'), encoding='utf-8')
            baseline = root / 'baseline.json'
            output = root / 'report.html'
            self.assertEqual(main(['snapshot', str(source), '--output', str(baseline)]), 0)
            self.assertEqual(main(['check', str(changed), '--baseline', str(baseline),
                                   '--html-report', str(output)]), 2)
            self.assertIn('ACTION REQUIRED', output.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

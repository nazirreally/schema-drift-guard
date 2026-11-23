import tempfile
import gzip
import json
from unittest.mock import patch
import unittest
from pathlib import Path
from driftguard.core import profile, compare
from driftguard.__main__ import main


class DriftGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def csv(self, name, text):
        path = self.root / name
        path.write_text(text, encoding='utf-8')
        return path

    def test_profile(self):
        p = profile(self.csv('a.csv', 'id,price,name\n1,1.2,A\n2,,B\n'))
        self.assertEqual(p['columns']['id']['type'], 'integer')
        self.assertEqual(p['columns']['price']['type'], 'number')
        self.assertEqual(p['columns']['price']['nulls'], 1)

    def test_removed_column_breaks(self):
        old = profile(self.csv('a.csv', 'id,name\n1,A\n'))
        new = profile(self.csv('b.csv', 'id\n1\n'))
        self.assertTrue(compare(old, new)['breaking'])

    def test_added_column_is_informational(self):
        old = profile(self.csv('a.csv', 'id\n1\n'))
        new = profile(self.csv('b.csv', 'id,name\n1,A\n'))
        self.assertFalse(compare(old, new)['breaking'])

    def test_type_widening(self):
        old = profile(self.csv('a.csv', 'id\n1\n'))
        new = profile(self.csv('b.csv', 'id\n1.5\n'))
        self.assertFalse(compare(old, new)['breaking'])

    def test_type_change_breaks(self):
        old = profile(self.csv('a.csv', 'id\n1\n'))
        new = profile(self.csv('b.csv', 'id\nabc\n'))
        self.assertTrue(compare(old, new)['breaking'])

    def test_new_null_breaks(self):
        old = profile(self.csv('a.csv', 'id\n1\n'))
        new = profile(self.csv('b.csv', 'id\n\n'))
        self.assertTrue(compare(old, new)['breaking'])

    def test_malformed_row_rejected(self):
        with self.assertRaises(ValueError):
            profile(self.csv('a.csv', 'id,name\n1\n'))

    def test_cli_exit_codes(self):
        original = self.csv('a.csv', 'id\n1\n')
        changed = self.csv('b.csv', 'id\ntext\n')
        baseline = self.root / 'schema.json'
        self.assertEqual(main(['snapshot', str(original), '--output', str(baseline)]), 0)
        self.assertEqual(main(['check', str(changed), '--baseline', str(baseline)]), 2)

    def test_json_report_is_persisted_on_breaking_drift(self):
        original = self.csv('baseline.csv', 'id,amount\n1,12.5\n')
        changed = self.csv('incoming.csv', 'id,amount\n2,unknown\n')
        baseline = self.root / 'baseline.json'
        report = self.root / 'audit.json'
        self.assertEqual(main(['snapshot', str(original), '--output', str(baseline)]), 0)
        self.assertEqual(main(['check', str(changed), '--baseline', str(baseline),
                               '--json-report', str(report)]), 2)
        data = json.loads(report.read_text(encoding='utf-8'))
        self.assertTrue(data['breaking'])
        self.assertTrue(any(change['column'] == 'amount' for change in data['changes']))

    def test_json_report_is_persisted_when_no_drift(self):
        source = self.csv('baseline.csv', 'id\n1\n')
        baseline = self.root / 'baseline.json'
        report = self.root / 'audit.json'
        self.assertEqual(main(['snapshot', str(source), '--output', str(baseline)]), 0)
        self.assertEqual(main(['check', str(source), '--baseline', str(baseline),
                               '--json-report', str(report)]), 0)
        self.assertEqual(json.loads(report.read_text())['changes'], [])

    def test_json_report_write_failure_returns_error(self):
        source = self.csv('baseline.csv', 'id\n1\n')
        baseline = self.root / 'baseline.json'
        self.assertEqual(main(['snapshot', str(source), '--output', str(baseline)]), 0)
        self.assertEqual(main(['check', str(source), '--baseline', str(baseline),
                               '--json-report', str(self.root / 'missing' / 'audit.json')]), 1)

    def test_gzip_profile_matches_plain_csv(self):
        raw = 'id,amount,name\n1,12.5,A\n2,,B\n'
        plain = self.csv('feed.csv', raw)
        compressed = self.root / 'feed.csv.gz'
        with gzip.open(compressed, 'wt', encoding='utf-8') as stream:
            stream.write(raw)
        self.assertEqual(profile(plain), profile(compressed))
        self.assertEqual(profile(compressed, sample_limit=1)['rows_sampled'], 1)

    def test_gzip_snapshot_and_check_exit_codes(self):
        original = self.root / 'baseline.csv.gz'
        changed = self.root / 'incoming.csv.gz'
        with gzip.open(original, 'wt', encoding='utf-8') as stream:
            stream.write('id,amount\n1,12.5\n')
        with gzip.open(changed, 'wt', encoding='utf-8') as stream:
            stream.write('id,amount\n2,unknown\n')
        baseline = self.root / 'baseline.json'
        report = self.root / 'audit.json'
        self.assertEqual(main(['snapshot', str(original), '--output', str(baseline)]), 0)
        self.assertEqual(main(['check', str(changed), '--baseline', str(baseline),
                               '--json-report', str(report)]), 2)
        self.assertTrue(json.loads(report.read_text())['breaking'])

    def test_invalid_gzip_is_controlled_cli_error(self):
        invalid = self.csv('invalid.csv.gz', 'id\n1\n')
        self.assertEqual(main(['snapshot', str(invalid),
                               '--output', str(self.root / 'baseline.json')]), 1)

    def test_limit(self):
        p = profile(self.csv('a.csv', 'id\n1\n2\n'), 1)
        self.assertEqual(p['rows_sampled'], 1)

    def test_duplicate_header_rejected(self):
        with self.assertRaises(ValueError):
            profile(self.csv('a.csv', 'id,id\n1,2\n'))


if __name__ == '__main__':
    unittest.main()

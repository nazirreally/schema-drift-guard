import json
import tempfile
import unittest
from pathlib import Path
from driftguard.core import profile, read_json, compare


class DefensiveInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'input'

    def test_nonfinite_tokens_are_not_numeric(self):
        for value in ('NaN', 'Infinity', '-inf', '1e999'):
            with self.subTest(value=value):
                self.path.write_text('amount\n' + value + '\n')
                self.assertEqual(profile(self.path)['columns']['amount']['type'], 'string')

    def test_finite_exponent_is_numeric(self):
        self.path.write_text('amount\n1e3\n')
        self.assertEqual(profile(self.path)['columns']['amount']['type'], 'number')

    def test_blank_header_rejected(self):
        for header in ('id,\n1,2\n', 'id,   \n1,2\n'):
            with self.subTest(header=header):
                self.path.write_text(header)
                with self.assertRaises(ValueError):
                    profile(self.path)

    def test_corrupt_baseline_rejected(self):
        bad = [
            {'columns': {}},
            {'rows_sampled': True, 'columns': {}},
            {'rows_sampled': -1, 'columns': {}},
            {'rows_sampled': 1, 'columns': {'a': {'type': 'float', 'nulls': 0}}},
            {'rows_sampled': 1, 'columns': {'a': {'type': 'integer', 'nulls': 2}}},
            {'rows_sampled': 1, 'columns': {'a': {'type': 'integer', 'nulls': True}}},
            {'rows_sampled': 1, 'columns': {'a': 'integer'}},
        ]
        for baseline in bad:
            with self.subTest(baseline=baseline):
                self.path.write_text(json.dumps(baseline))
                with self.assertRaises(ValueError):
                    read_json(self.path)

    def test_valid_snapshot_round_trip(self):
        self.path.write_text('id,amount\n1,2.5\n')
        snapshot = profile(self.path)
        self.path.write_text(json.dumps(snapshot))
        self.assertFalse(compare(read_json(self.path), snapshot)['breaking'])


if __name__ == '__main__':
    unittest.main()

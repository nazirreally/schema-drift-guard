import json
import tempfile
import unittest
from pathlib import Path
from driftguard.policy import load_policy, apply_policy


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'policy.json'

    def load(self, data):
        self.path.write_text(json.dumps(data))
        return load_policy(self.path)

    def test_missing_required_column(self):
        policy = self.load({'required_columns': ['customer_id']})
        result = apply_policy({'breaking': False, 'changes': []}, {'columns': {}}, policy)
        self.assertTrue(result['breaking'])
        self.assertEqual(result['changes'][0]['column'], 'customer_id')

    def test_rule_changes_severity(self):
        policy = self.load({'rules': [{'column': 'metadata_*', 'change': 'added', 'severity': 'breaking'}]})
        report = {'breaking': False, 'changes': [{'column': 'metadata_version', 'change': 'added', 'severity': 'informational'}]}
        self.assertTrue(apply_policy(report, {'columns': {}}, policy)['breaking'])
        self.assertFalse(report['breaking'])

    def test_ignore_rule(self):
        policy = self.load({'rules': [{'column': '*', 'change': 'new_null_values', 'severity': 'ignore'}]})
        report = {'breaking': True, 'changes': [{'column': 'x', 'change': 'new null values', 'severity': 'breaking'}]}
        self.assertEqual(apply_policy(report, {'columns': {}}, policy), {'breaking': False, 'changes': []})

    def test_first_rule_wins(self):
        policy = self.load({'rules': [
            {'column': 'internal_*', 'change': 'removed', 'severity': 'ignore'},
            {'column': '*', 'change': 'removed', 'severity': 'breaking'}]})
        report = {'breaking': True, 'changes': [{'column': 'internal_id', 'change': 'removed', 'severity': 'breaking'}]}
        self.assertFalse(apply_policy(report, {'columns': {}}, policy)['breaking'])

    def test_invalid_policy(self):
        for data in ({'rules': [{'column': '*', 'change': 'added', 'severity': 'critical'}]},
                     {'required_columns': 'id'}, {'unexpected': 1}, []):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)

    def test_required_existing(self):
        policy = self.load({'required_columns': ['id']})
        result = apply_policy({'breaking': False, 'changes': []}, {'columns': {'id': {'type': 'integer', 'nulls': 0}}}, policy)
        self.assertFalse(result['breaking'])

    def test_no_duplicate_required_missing(self):
        policy = self.load({'required_columns': ['id']})
        report = {'breaking': True, 'changes': [{'column': 'id', 'change': 'removed', 'severity': 'breaking'}]}
        self.assertEqual(len(apply_policy(report, {'columns': {}}, policy)['changes']), 1)


if __name__ == '__main__':
    unittest.main()

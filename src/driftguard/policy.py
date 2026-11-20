"""Configurable data contract policies for CSV drift reports."""
import fnmatch
import json
from pathlib import Path

VALID_SEVERITIES = {'breaking', 'informational', 'ignore'}
VALID_RULES = {'added', 'removed', 'type', 'new_null_values'}


def load_policy(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) - {'rules', 'required_columns'}:
        raise ValueError('Policy must be an object containing only rules and required_columns')
    rules = data.get('rules', [])
    required = data.get('required_columns', [])
    if not isinstance(rules, list) or not isinstance(required, list) or not all(isinstance(s, str) and s for s in required):
        raise ValueError('rules must be a list and required_columns a list of names')
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'column', 'change', 'severity'}:
            raise ValueError('Each rule must specify column, change, and severity')
        if not isinstance(rule['column'], str) or not rule['column'] or rule['change'] not in VALID_RULES or rule['severity'] not in VALID_SEVERITIES:
            raise ValueError('Invalid policy rule')
    return {'rules': rules, 'required_columns': required}


def apply_policy(report, current, policy):
    """Apply first matching rule; never modify the input report."""
    changes = [dict(change) for change in report['changes']]
    for column in policy['required_columns']:
        if column not in current['columns'] and not any(c['column'] == column and c['change'] == 'removed' for c in changes):
            changes.append({'column': column, 'change': 'required column missing', 'severity': 'breaking'})
    for change in changes:
        category = ('type' if change['change'].startswith('type ') else
                    'new_null_values' if change['change'] == 'new null values' else change['change'])
        for rule in policy['rules']:
            if category == rule['change'] and fnmatch.fnmatchcase(change['column'], rule['column']):
                change['severity'] = rule['severity']
                break
    changes = [c for c in changes if c['severity'] != 'ignore']
    return {'breaking': any(c['severity'] == 'breaking' for c in changes),
            'changes': sorted(changes, key=lambda c: (c['column'], c['change']))}

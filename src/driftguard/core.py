import csv
import json
import math
from collections import Counter
from pathlib import Path

VALID_TYPES = {'integer', 'number', 'string', 'unknown'}


def profile(path, sample_limit=10000):
    """Profile a CSV without loading it entirely into memory."""
    if sample_limit < 1:
        raise ValueError('sample_limit must be positive')
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or any(not field or not field.strip() for field in fields) or len(set(fields)) != len(fields):
            raise ValueError('CSV must have a nonempty, unique header')
        stats = {field: {'nulls': 0, 'types': Counter()} for field in fields}
        rows = 0
        for row in reader:
            if rows >= sample_limit:
                break
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'malformed CSV row {rows + 2}')
            rows += 1
            for field, value in row.items():
                if not value or not value.strip():
                    stats[field]['nulls'] += 1
                    continue
                value = value.strip()
                try:
                    int(value)
                    kind = 'integer'
                except ValueError:
                    try:
                        number = float(value)
                        kind = 'number' if math.isfinite(number) else 'string'
                    except ValueError:
                        kind = 'string'
                stats[field]['types'][kind] += 1
    def infer(counts):
        kinds = set(counts)
        if not kinds:
            return 'unknown'
        if kinds <= {'integer'}:
            return 'integer'
        if kinds <= {'integer', 'number'}:
            return 'number'
        return 'string'
    return {'rows_sampled': rows, 'columns': {name: {'type': infer(info['types']), 'nulls': info['nulls']} for name, info in stats.items()}}


def compare(baseline, current):
    old, new = baseline['columns'], current['columns']
    changes = []
    for name in sorted(old.keys() - new.keys()):
        changes.append({'column': name, 'change': 'removed', 'severity': 'breaking'})
    for name in sorted(new.keys() - old.keys()):
        changes.append({'column': name, 'change': 'added', 'severity': 'informational'})
    for name in sorted(old.keys() & new.keys()):
        before, after = old[name]['type'], new[name]['type']
        if before != after:
            severity = 'informational' if (before, after) in {('integer', 'number'), ('unknown', 'integer'), ('unknown', 'number'), ('unknown', 'string')} else 'breaking'
            changes.append({'column': name, 'change': f'type {before} -> {after}', 'severity': severity})
        if old[name]['nulls'] == 0 and new[name]['nulls'] > 0:
            changes.append({'column': name, 'change': 'new null values', 'severity': 'breaking'})
    return {'breaking': any(x['severity'] == 'breaking' for x in changes), 'changes': changes}


def read_json(path):
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get('columns'), dict):
        raise ValueError('Invalid baseline: missing columns object')
    rows = data.get('rows_sampled')
    if type(rows) is not int or rows < 0:
        raise ValueError('Invalid baseline: rows_sampled must be a nonnegative integer')
    for name, info in data['columns'].items():
        if (not isinstance(name, str) or not name.strip() or not isinstance(info, dict)
                or info.get('type') not in VALID_TYPES or type(info.get('nulls')) is not int
                or not 0 <= info['nulls'] <= rows):
            raise ValueError(f'Invalid baseline column: {name!r}')
    return data


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')

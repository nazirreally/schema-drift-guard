import argparse
import json
import sys
from .core import profile, compare, read_json, write_json
from .policy import load_policy, apply_policy


def main(argv=None):
    parser = argparse.ArgumentParser(description='Detect breaking CSV schema changes')
    sub = parser.add_subparsers(dest='command', required=True)
    snapshot = sub.add_parser('snapshot', help='Create baseline JSON')
    snapshot.add_argument('csv')
    snapshot.add_argument('--output', required=True)
    check = sub.add_parser('check', help='Compare CSV against baseline')
    check.add_argument('csv')
    check.add_argument('--baseline', required=True)
    check.add_argument('--policy', help='Optional JSON data contract policy')
    for command in (snapshot, check):
        command.add_argument('--sample-limit', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        current = profile(args.csv, args.sample_limit)
        if args.command == 'snapshot':
            write_json(args.output, current)
            print(f'Baseline saved to {args.output}')
            return 0
        result = compare(read_json(args.baseline), current)
        if args.policy:
            result = apply_policy(result, current, load_policy(args.policy))
        print(json.dumps(result, indent=2))
        return 2 if result['breaking'] else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

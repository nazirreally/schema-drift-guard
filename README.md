# Schema Drift Guard

A dependency-free Python CLI that detects breaking changes in CSV feeds before they enter ETL jobs.

## Features
- Streams and profiles up to 10,000 rows by default
- Infers integer, number, string, and unknown types
- Detects removed/added columns, type changes, and newly introduced nulls
- Exit code 0 = no breaking drift, 2 = breaking drift, 1 = input/configuration error
- JSON baseline suitable for committing alongside pipeline code
- Python 3.10+, standard library runtime only

## Quick start

```bash
python -m pip install -e .
printf 'id,amount\n1,12.5\n' > baseline.csv
printf 'id,amount\n2,unknown\n' > incoming.csv
python -m driftguard snapshot baseline.csv --output schema.json
python -m driftguard check incoming.csv --baseline schema.json
# exit code 2 (numeric -> string)
```

On Windows PowerShell, create CSV files using Set-Content rather than printf.

## CI integration

Commit schema.json and run `python -m driftguard check path/to/feed.csv --baseline schema.json` in a GitHub Actions step. A breaking change fails the job with exit code 2.

## Design decisions and limitations

- Type inference is based on sampled non-null values; leading-zero identifiers may be inferred as integers.
- A newly added column is informational; a removed column is breaking.
- Integer-to-number widening is informational; other observed type changes are breaking.
- A previously null-free column receiving null values is breaking.
- It checks CSV structure, not business semantics, unique keys, freshness, or historical distributions.
- Only the first `--sample-limit` records are examined.

## Testing

```bash
python -m unittest discover -s tests -v
```

## License
MIT (see LICENSE).

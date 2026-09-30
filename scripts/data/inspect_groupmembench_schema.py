#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.groupmembench import (  # noqa: E402
    DOMAINS,
    download_domain,
    iter_messages,
    load_domain_file,
    sample_records,
    summarize_schema,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect raw GroupMemBench domain JSON schema."
    )
    parser.add_argument(
        "--domain",
        choices=DOMAINS,
        default="Finance",
        help="Domain name used for metadata and optional download.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Local GroupMemBench domain JSON file. If omitted, use --download.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the selected domain JSON from Hugging Face first.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "groupmembench",
        help="Where downloaded raw domain files should be stored.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "schema_summary.json",
        help="Where to write the schema summary JSON.",
    )
    parser.add_argument(
        "--sample-output",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "message_sample.json",
        help="Where to write a small message sample.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=25,
        help="Number of messages to include in the sample output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = args.input
    if args.download:
        input_path = download_domain(args.domain, args.raw_dir)

    if input_path is None:
        raise SystemExit("Provide --input PATH or use --download.")

    data = load_domain_file(input_path)
    records = iter_messages(data, domain=args.domain)
    summary = summarize_schema(records)
    sample = sample_records(records, args.sample_size)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sample_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    args.sample_output.write_text(json.dumps(sample, indent=2), encoding="utf-8")

    print(f"Loaded {summary['message_count']} messages from {input_path}")
    print(f"Wrote schema summary to {args.output}")
    print(f"Wrote message sample to {args.sample_output}")


if __name__ == "__main__":
    main()

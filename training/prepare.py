from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

REQUIRED = {"document_id", "image", "instruction", "answer", "task"}
TASKS = {"ocr", "table", "formula", "chart"}


def validate(records: list[dict]) -> None:
    seen_images: dict[str, str] = {}
    for index, record in enumerate(records):
        missing = REQUIRED - record.keys()
        if missing:
            raise ValueError(f"record {index} misses fields: {sorted(missing)}")
        if record["task"] not in TASKS or not all(isinstance(record[key], str) and record[key] for key in REQUIRED):
            raise ValueError(f"record {index} has invalid task or empty textual fields")
        digest = hashlib.sha256(Path(record["image"]).read_bytes()).hexdigest()
        prior = seen_images.setdefault(digest, record["document_id"])
        if prior != record["document_id"]:
            raise ValueError(f"duplicate pixel content crosses document groups: {prior}, {record['document_id']}")


def split(records: list[dict]) -> dict[str, list[dict]]:
    groups = sorted({item["document_id"] for item in records})
    assignments = {group: ("test" if index % 10 == 0 else "validation" if index % 10 == 1 else "train")
                   for index, group in enumerate(groups)}
    result: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        result[assignments[record["document_id"]]].append(record)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
    validate(records)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, values in split(records).items():
        (args.output / f"{name}.jsonl").write_text(
            "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values), encoding="utf-8"
        )


if __name__ == "__main__":
    main()

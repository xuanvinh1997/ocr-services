"""Report candidate package releases; this script never mutates an environment."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from urllib.request import urlopen

PACKAGES = ("paddleocr", "paddlepaddle", "vllm", "transformers", "peft")


def stable_version(package: str) -> str:
    with urlopen(f"https://pypi.org/pypi/{package}/json", timeout=15) as response:
        data = json.load(response)
    return data["info"]["version"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "packages": {package: stable_version(package) for package in PACKAGES},
        "approval_required": True,
    }
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def parse_perf_stat(lines):
    result = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = re.match(r"^\s*([\d.]+)\s+seconds\s+(user|sys)\s*$", line)
        if m:
            value, key = float(m.group(1)), m.group(2)
            result[key] = value
            continue

        m = re.match(r"^\s*([\d,.]+)\s+\w+\s+([^\s#]+)", line)
        if m:
            value_str, metric = m.group(1).replace(",", ""), m.group(2)
            try:
                value = int(value_str)
            except ValueError:
                value = float(value_str)
            result[metric] = value
            continue

        m = re.match(r"^\s*([\d,.]+)\s+([^\s#]+)", line)
        if m:
            value_str, metric = m.group(1).replace(",", ""), m.group(2)
            try:
                value = int(value_str)
            except ValueError:
                value = float(value_str)
            result[metric] = value
    return result


def main(input_file):
    lines = Path(input_file).read_text(encoding="utf-8").splitlines()
    parsed = parse_perf_stat(lines)
    output_file = Path(input_file).with_suffix(".json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=4)
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Using: python3 parse_perf.py <perf_output_file>")
        sys.exit(1)
    main(sys.argv[1])

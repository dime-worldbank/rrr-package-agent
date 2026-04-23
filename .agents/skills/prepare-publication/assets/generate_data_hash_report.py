#!/usr/bin/env python3
"""
Data Hash Report Generator for PRWP Reproducibility Packages
------------------------------------------------------------
Generates SHA-256 hashes for all files in the data folder.
Run from the root of the reproducibility package:

    python generate_data_hash_report.py

Output: data_hash_report.csv in the current directory.
"""
import hashlib
import os
import csv
from pathlib import Path
from datetime import datetime

# ── Configure these paths ────────────────────────────────────────────
# Folder containing the raw data to hash (adjust if your package uses
# a different folder name, e.g. "Data", "data", "01_data/raw")
DATA_FOLDER = Path("data")

# Output file location (top level of the package)
OUTPUT_FILE = Path("data_hash_report.csv")
# ─────────────────────────────────────────────────────────────────────


def sha256_hash(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not DATA_FOLDER.exists():
        print(f"ERROR: Data folder '{DATA_FOLDER}' not found.")
        print("Please adjust DATA_FOLDER at the top of this script.")
        return

    rows = []
    skipped = []

    for path in sorted(DATA_FOLDER.rglob("*")):
        if not path.is_file():
            continue
        # Skip hidden files and system files
        if path.name.startswith(".") or path.name in {"Thumbs.db", "desktop.ini"}:
            skipped.append(str(path))
            continue
        try:
            file_hash = sha256_hash(path)
            rows.append({
                "file": str(path.relative_to(DATA_FOLDER)),
                "size_bytes": path.stat().st_size,
                "sha256": file_hash,
                "hashed_on": datetime.now().strftime("%Y-%m-%d"),
            })
        except (PermissionError, OSError) as e:
            skipped.append(f"{path} ({e})")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "size_bytes", "sha256", "hashed_on"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Hash report written to: {OUTPUT_FILE}")
    print(f"  Files hashed: {len(rows)}")
    if skipped:
        print(f"  Files skipped: {len(skipped)}")
        for s in skipped:
            print(f"    - {s}")


if __name__ == "__main__":
    main()

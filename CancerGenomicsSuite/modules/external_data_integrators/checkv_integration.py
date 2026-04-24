import os
import subprocess
from typing import Tuple


def run_checkv(input_fasta: str, output_dir: str, threads: int = 4) -> str:
    """Run CheckV end-to-end analysis on a FASTA file.

    Returns the path to the generated quality_summary.tsv.
    """
    cmd = [
        "checkv",
        "end_to_end",
        input_fasta,
        output_dir,
        "-t",
        str(threads),
        "--quiet",
    ]
    subprocess.run(cmd, check=True)
    return os.path.join(output_dir, "quality_summary.tsv")


def parse_quality_summary(quality_summary_path: str):
    """Parse CheckV quality_summary.tsv into a list of dict rows."""
    rows = []
    if not os.path.exists(quality_summary_path):
        return rows
    with open(quality_summary_path, "r", encoding="utf-8") as fh:
        header = None
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            row = {h: v for h, v in zip(header, parts)}
            rows.append(row)
    return rows


def extract_completeness_contamination(rows) -> Tuple[list, list]:
    """Extract completeness and contamination arrays from parsed rows."""
    completeness = []
    contamination = []
    for row in rows:
        try:
            completeness.append(float(row.get("completeness", 0)))
            contamination.append(float(row.get("contamination", 0)))
        except (TypeError, ValueError):
            continue
    return completeness, contamination


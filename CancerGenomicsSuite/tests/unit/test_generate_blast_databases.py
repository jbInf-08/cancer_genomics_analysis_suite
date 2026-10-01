"""The BLAST database script must import and build sequences on current Biopython.

It imported generic_dna and generic_protein from Bio.Alphabet, which Biopython
removed in 1.78; the project requires biopython>=1.81, so the script could never
import, and neither could scripts/example_usage.py, which imports it.

Restoring the import would not have been enough. Seq's second positional
parameter is now `length`, so Seq(sequence, generic_dna) would pass an alphabet
object where an integer length is expected.
"""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path

import pytest

SUITE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def generator_cls():
    # The script is run from CancerGenomicsSuite/, where `scripts` is a package.
    sys.path.insert(0, str(SUITE))
    try:
        from scripts.generate_blast_databases import BlastDatabaseGenerator
    finally:
        sys.path.remove(str(SUITE))
    return BlastDatabaseGenerator


@pytest.fixture
def generator(generator_cls):
    gen = generator_cls.__new__(generator_cls)  # skip network/tool checks in __init__
    gen.logger = logging.getLogger("test_generate_blast_databases")
    return gen


def test_no_bio_alphabet_reference_remains():
    source = (SUITE / "scripts" / "generate_blast_databases.py").read_text(
        encoding="utf-8"
    )
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    for name in ("Bio.Alphabet", "generic_dna", "generic_protein"):
        assert name not in code, f"{name} is still referenced"


@pytest.mark.parametrize(
    ("seq_type", "residues"),
    [("nucl", set("ATCG")), ("prot", set("ACDEFGHIKLMNPQRSTVWY"))],
)
def test_mock_sequences_round_trip_through_fasta(generator, seq_type, residues):
    from Bio import SeqIO

    records = generator.generate_mock_sequences(["TP53", "BRCA1"], seq_type)
    buffer = io.StringIO()
    SeqIO.write(records, buffer, "fasta")
    buffer.seek(0)
    parsed = list(SeqIO.parse(buffer, "fasta"))

    assert [r.id for r in parsed] == ["TP53", "BRCA1"]
    for record in parsed:
        assert len(record.seq) > 0
        assert set(str(record.seq)) <= residues


def test_example_usage_imports():
    """scripts/example_usage.py imports the generator, so it failed with it."""
    sys.path.insert(0, str(SUITE))
    try:
        import importlib

        importlib.import_module("scripts.example_usage")
    finally:
        sys.path.remove(str(SUITE))

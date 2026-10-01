"""BlastPipeline builds its BLAST+ command itself.

It used Biopython's NcbiblastnCommandline / NcbiblastpCommandline, which
Biopython removed along with the rest of Bio.Application. On current releases
(CI installs 1.88) tasks/blast_pipeline.py could not import, and nor could the
tasks package, which imports it. The flags blast_command produces were checked
against the old wrappers' output, on a Biopython that still has them, for both
programs at the default configuration: identical.
"""

import pytest

from CancerGenomicsSuite.tasks.blast_pipeline import BlastConfig, blast_command


def _flags(argv):
    rest = argv[1:]
    assert len(rest) % 2 == 0, argv
    return dict(zip(rest[::2], rest[1::2]))


def test_blastn_command():
    cfg = BlastConfig(database_path="db/nt", evalue=1e-5, outfmt="5")
    argv = blast_command(cfg, "q.fa", "out.xml")
    assert argv[0] == "blastn"
    assert _flags(argv) == {
        "-query": "q.fa",
        "-db": "db/nt",
        "-evalue": "1e-05",
        "-outfmt": "5",
        "-out": "out.xml",
        "-num_threads": "4",
        "-max_target_seqs": "100",
        "-word_size": "11",
        "-gapopen": "5",
        "-gapextend": "2",
        "-penalty": "-1",
        "-reward": "1",
    }


def test_blastp_command_has_no_nucleotide_scoring():
    cfg = BlastConfig(database_path="db/nr", program="blastp")
    argv = blast_command(cfg, "q.fa", "out.xml")
    assert argv[0] == "blastp"
    flags = _flags(argv)
    assert "-penalty" not in flags and "-reward" not in flags
    assert flags["-db"] == "db/nr" and flags["-query"] == "q.fa"


def test_unsupported_program_is_rejected():
    with pytest.raises(ValueError, match="tblastx"):
        blast_command(BlastConfig(database_path="db", program="tblastx"), "q", "o")

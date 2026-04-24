import os
from unittest import mock

from modules.external_data_integrators.checkv_integration import run_checkv, parse_quality_summary, extract_completeness_contamination


def test_run_checkv_constructs_summary_path(tmp_path):
    input_fasta = str(tmp_path / "contigs.fasta")
    output_dir = str(tmp_path / "checkv_out")
    os.makedirs(output_dir, exist_ok=True)
    with open(input_fasta, "w", encoding="utf-8") as fh:
        fh.write(">c1\nACTG\n")

    with mock.patch("subprocess.run") as mrun:
        summary = run_checkv(input_fasta, output_dir, threads=2)
        assert summary.endswith("quality_summary.tsv")
        mrun.assert_called()


def test_parse_quality_summary_and_extract(tmp_path):
    qs = tmp_path / "quality_summary.tsv"
    with open(qs, "w", encoding="utf-8") as fh:
        fh.write("contig\tcompleteness\tcontamination\n")
        fh.write("c1\t90.5\t1.2\n")
        fh.write("c2\t75.0\t0.5\n")

    rows = parse_quality_summary(str(qs))
    comp, cont = extract_completeness_contamination(rows)
    assert comp == [90.5, 75.0]
    assert cont == [1.2, 0.5]



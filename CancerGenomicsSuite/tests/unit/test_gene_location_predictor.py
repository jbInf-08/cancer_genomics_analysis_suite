"""Unit tests for gene locus annotation helpers."""

from unittest.mock import MagicMock, patch

from CancerGenomicsSuite.modules.gene_annotation.gene_location_predictor import (
    GeneLocationPredictor,
    build_vep_vcf_variant_line,
    normalize_chromosome,
    region_to_ensembl_string,
)


def test_normalize_chromosome():
    assert normalize_chromosome("chr17") == "17"
    assert normalize_chromosome("17") == "17"
    assert normalize_chromosome("chrX") == "X"


def test_region_to_ensembl_string():
    assert region_to_ensembl_string("chr17", 43000000, 43100000) == "17:43000001-43100000"


def test_build_vep_vcf_variant_line_snv():
    line, err = build_vep_vcf_variant_line("chr17", 43094695, "G", "A")
    assert err is None
    assert line == "17 43094695 . G A"


def test_build_vep_vcf_variant_line_indel():
    line, err = build_vep_vcf_variant_line("chr17", 43094695, "G", "GT")
    assert err is None
    assert line == "17 43094695 . G GT"


def test_build_vep_vcf_variant_line_invalid():
    line, err = build_vep_vcf_variant_line("chr17", 43094695, "G", "G")
    assert line is None
    assert err and err.get("error_kind") == "invalid_allele"


@patch(
    "CancerGenomicsSuite.modules.gene_annotation.gene_location_predictor.http_post_json"
)
def test_predict_vep_region_post_parses_rows(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://rest.ensembl.org/vep/human/region?minimal=1"
    mock_resp.text = "[]"
    mock_resp.json.return_value = [
        {
            "transcript_consequences": [
                {
                    "gene_symbol": "BRCA1",
                    "gene_id": "ENSG1",
                    "transcript_id": "ENST1",
                    "consequence_terms": ["missense_variant"],
                    "impact": "MODERATE",
                    "biotype": "protein_coding",
                    "amino_acids": "G/E",
                }
            ]
        }
    ]
    mock_post.return_value = (mock_resp, None)

    g = GeneLocationPredictor()
    rows = g.predict_vep_region_post(["17 43094695 . G AC"], reference_genome="hg38")
    assert len(rows) == 1
    assert rows[0]["gene_symbol"] == "BRCA1"
    assert rows[0]["ref_allele"] == "G"
    assert rows[0]["alt_allele"] == "AC"
    called_url = mock_post.call_args[0][0]
    assert "/vep/human/region" in called_url
    assert "minimal=1" in called_url


@patch(
    "CancerGenomicsSuite.modules.gene_annotation.gene_location_predictor.http_get_with_errors"
)
def test_predict_genes_in_region_parses_genes(mock_http):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {
            "feature_type": "gene",
            "id": "ENSG00000012048",
            "external_name": "BRCA1",
            "biotype": "protein_coding",
            "strand": -1,
            "start": 43044295,
            "end": 43170245,
            "description": "BRCA1 DNA repair associated",
        },
        {"feature_type": "transcript", "id": "ENST0001"},
    ]
    mock_http.return_value = (mock_resp, None)

    g = GeneLocationPredictor()
    out = g.predict_genes_in_region("chr17", 43090000, 43095000, reference_genome="hg38")
    assert len(out) == 1
    assert out[0]["symbol"] == "BRCA1"
    assert out[0]["gene_id"] == "ENSG00000012048"
    called_url = mock_http.call_args[0][0]
    assert "overlap/region/human/" in called_url


def test_predict_genes_at_position():
    g = GeneLocationPredictor()
    with patch.object(g, "predict_genes_in_region", return_value=[]) as m:
        g.predict_genes_at_position("chr1", 1000000, flank=5000, reference_genome="hg38")
    m.assert_called_once()
    args, kwargs = m.call_args
    assert args[0] == "chr1"
    # Default one_based_vcf: POS=1_000_000 → 0-based window [POS-1-flank, POS-1+flank+1)
    assert args[1] == 994999
    assert args[2] == 1005000

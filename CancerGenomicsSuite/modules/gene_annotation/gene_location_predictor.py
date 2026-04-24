"""
Predict / resolve gene locations (Ensembl overlap) and optional VEP consequences.

Coordinates for overlap queries default to **1-based VCF-style POS** for the
variant center (``position_convention='one_based_vcf'``): the interval is built
in 0-based half-open space as ``[POS-1-flank, POS-1+flank+1)`` so the variant
base at VCF POS ``P`` is included.

Ensembl overlap URLs use **1-based inclusive** region endpoints per Ensembl REST.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from CancerGenomicsSuite.modules.gene_annotation.ensembl_api_utils import (
    build_ensembl_error_payload,
    ensembl_rest_base,
    http_get_with_errors,
    http_post_json,
    safe_response_json_list,
    species_for_reference,
)

logger = logging.getLogger(__name__)

ENSEMBL_REST = "https://rest.ensembl.org"


def normalize_chromosome(chromosome: str) -> str:
    """Strip ``chr`` prefix for Ensembl region strings."""
    c = (chromosome or "").strip()
    if c.lower().startswith("chr"):
        return c[3:]
    return c


_ALLOWED_VEP_DNA = set("ACGTN")


def build_vep_vcf_variant_line(
    chromosome: str,
    pos_vcf_one_based: int,
    ref: str,
    alt: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Build a single-line VCF-style variant for Ensembl VEP ``POST .../vep/:species/region``.

    Format: ``CHR POS . REF ALT`` (chromosome without ``chr``, dot ID placeholder).
    Use together with query ``minimal=1`` so Ensembl can left/right-normalize indels.
    """
    ch = normalize_chromosome(chromosome)
    r = (ref or "").strip().upper().replace(".", "")
    a = (alt or "").strip().upper().replace(".", "")
    if not r or not a:
        return None, build_ensembl_error_payload(
            kind="invalid_allele",
            status_code=None,
            url="",
            message="VEP requires non-empty reference and alternate alleles (VCF-style).",
        )
    if any(b not in _ALLOWED_VEP_DNA for b in r) or any(b not in _ALLOWED_VEP_DNA for b in a):
        return None, build_ensembl_error_payload(
            kind="invalid_allele",
            status_code=None,
            url="",
            message="Alleles must use DNA symbols A, C, G, T, or N.",
        )
    if r == a:
        return None, build_ensembl_error_payload(
            kind="invalid_allele",
            status_code=None,
            url="",
            message="Reference and alternate alleles must differ.",
        )
    p = int(pos_vcf_one_based)
    line = f"{ch} {p} . {r} {a}"
    return line, None


def region_to_ensembl_string(chromosome: str, start: int, end: int) -> str:
    """
    Build Ensembl region ``seq_region:start-end`` (1-based inclusive end).

    Assumes ``start``/``end`` follow 0-based half-open ``[start, end)``.
    """
    ch = normalize_chromosome(chromosome)
    start_1 = int(start) + 1
    end_1 = int(end)
    return f"{ch}:{start_1}-{end_1}"


class GeneLocationPredictor:
    """Query Ensembl overlap/region and optional VEP region endpoints."""

    def __init__(self, base_url: str = ENSEMBL_REST, timeout: int = 45) -> None:
        self.default_base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CancerGenomicsAnalysisSuite/1.0 (gene annotation)",
        }

    def _base(self, reference_genome: str) -> str:
        return ensembl_rest_base(reference_genome).rstrip("/")

    def predict_genes_in_region(
        self,
        chromosome: str,
        start: int,
        end: int,
        reference_genome: str = "hg38",
        features: str = "gene",
    ) -> List[Dict[str, Any]]:
        """
        Return overlapping gene features from Ensembl overlap/region.

        On HTTP/parse failure returns a one-element list with an ``error`` dict
        (includes ``user_message``, ``error_code``, ``retry_after_seconds``).
        """
        species = species_for_reference(reference_genome)
        region = region_to_ensembl_string(chromosome, start, end)
        base = self._base(reference_genome)
        url = f"{base}/overlap/region/{species}/{region}"
        params = {"feature": features, "content-type": "application/json"}

        resp, err = http_get_with_errors(
            url, headers=self.headers, timeout=self.timeout, params=params
        )
        if err:
            return [err]

        data, jerr = safe_response_json_list(resp)
        if jerr:
            return [jerr]

        rows: List[Dict[str, Any]] = []
        for item in data:
            if item.get("feature_type") != "gene":
                continue
            rows.append(
                {
                    "gene_id": item.get("id"),
                    "symbol": item.get("external_name") or item.get("id"),
                    "biotype": item.get("biotype"),
                    "strand": item.get("strand"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "description": item.get("description"),
                    "source": "ensembl",
                }
            )
        return rows

    def predict_genes_at_position(
        self,
        chromosome: str,
        position: int,
        flank: int = 50_000,
        reference_genome: str = "hg38",
        position_convention: str = "one_based_vcf",
    ) -> List[Dict[str, Any]]:
        """
        Build a window around ``position`` and query overlap.

        position_convention:
            ``one_based_vcf`` (default): ``position`` is VCF POS (1-based). Window
            in 0-based half-open coords: ``[P-1-flank, P-1+flank+1)``.
            ``zero_based_center``: legacy symmetric window ``[pos-flank, pos+flank)``.
        """
        pos = int(position)
        fl = max(1, int(flank))
        if position_convention == "zero_based_center":
            start = max(0, pos - fl)
            end = pos + fl
        else:
            p0 = pos - 1
            start = max(0, p0 - fl)
            end = p0 + fl + 1
        return self.predict_genes_in_region(
            chromosome, start, end, reference_genome=reference_genome
        )

    def _vep_transcript_rows_from_payload(
        self,
        data: Any,
        *,
        status_code: Optional[int],
        url: str,
        response_text: str,
        ref_display: Optional[str],
        alt_display: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Parse VEP JSON list body into lightweight transcript consequence dicts."""
        if isinstance(data, dict) and "error" in data:
            return [
                build_ensembl_error_payload(
                    kind="ensembl_api_error",
                    status_code=status_code,
                    url=url,
                    message=str(data.get("error")),
                    response_text_snippet=response_text,
                )
            ]

        if not isinstance(data, list):
            return [
                build_ensembl_error_payload(
                    kind="unexpected_shape",
                    status_code=status_code,
                    url=url,
                    message=f"Expected list from VEP, got {type(data).__name__}",
                )
            ]

        out: List[Dict[str, Any]] = []
        for item in data:
            for tc in item.get("transcript_consequences") or []:
                out.append(
                    {
                        "source": "vep",
                        "gene_symbol": tc.get("gene_symbol"),
                        "gene_id": tc.get("gene_id"),
                        "transcript_id": tc.get("transcript_id"),
                        "consequence_terms": tc.get("consequence_terms") or [],
                        "impact": tc.get("impact"),
                        "biotype": tc.get("biotype"),
                        "amino_acids": tc.get("amino_acids"),
                        "codons": tc.get("codons"),
                        "protein_position": tc.get("protein_start"),
                        "sift_prediction": tc.get("sift_prediction"),
                        "polyphen_prediction": tc.get("polyphen_prediction"),
                        "ref_allele": ref_display,
                        "alt_allele": alt_display,
                    }
                )
        return out

    def predict_vep_region_post(
        self,
        variant_lines: List[str],
        reference_genome: str = "hg38",
        *,
        minimal: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        POST variants to Ensembl VEP region endpoint (supports indels / MNV via VCF-style lines).

        Each line should look like ``17 43094695 . G AC`` (chrom, VCF POS, ``.``, REF, ALT).
        When ``minimal`` is True, Ensembl normalizes representation before consequence calculation.
        """
        if not variant_lines:
            return [
                build_ensembl_error_payload(
                    kind="invalid_input",
                    status_code=None,
                    url="",
                    message="No variant lines supplied for VEP POST.",
                )
            ]
        species = species_for_reference(reference_genome)
        base = self._base(reference_genome)
        url = f"{base}/vep/{species}/region"
        params: Dict[str, str] = {"content-type": "application/json"}
        if minimal:
            params["minimal"] = "1"

        full = url
        if params:
            q = "&".join(f"{k}={v}" for k, v in params.items())
            full = f"{url}?{q}"

        resp, err = http_post_json(
            full,
            json_body={"variants": variant_lines},
            headers=self.headers,
            timeout=self.timeout,
        )
        if err:
            return [err]

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            return [
                build_ensembl_error_payload(
                    kind="json_decode",
                    status_code=resp.status_code,
                    url=resp.url,
                    message=str(e),
                    response_text_snippet=resp.text,
                )
            ]

        ref_d = None
        alt_d = None
        parts = variant_lines[0].split()
        if len(parts) >= 5:
            ref_d, alt_d = parts[3], parts[4]
        return self._vep_transcript_rows_from_payload(
            data,
            status_code=resp.status_code,
            url=resp.url,
            response_text=resp.text,
            ref_display=ref_d,
            alt_display=alt_d,
        )

    def predict_vep_variant(
        self,
        chromosome: str,
        position_one_based: int,
        ref_allele: str,
        alt_allele: str,
        reference_genome: str = "hg38",
        strand: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        VEP consequences for a VCF-style variant (SNV via GET, indels/MNV via POST + minimal).

        ``position_one_based`` is VCF POS (1-based). ``ref_allele`` / ``alt_allele`` are VCF REF/ALT
        strings (may differ in length for indels).
        """
        ra = (ref_allele or "").strip().upper()
        aa = (alt_allele or "").strip().upper()
        if (
            len(ra) == 1
            and len(aa) == 1
            and ra in "ACGT"
            and aa in "ACGT"
            and ra != aa
        ):
            return self.predict_vep_region_allele(
                chromosome,
                int(position_one_based),
                aa,
                reference_genome=reference_genome,
                strand=strand,
                ref_allele=ra,
            )
        line, verr = build_vep_vcf_variant_line(
            chromosome, int(position_one_based), ra, aa
        )
        if verr:
            return [verr]
        return self.predict_vep_region_post([line], reference_genome=reference_genome, minimal=True)

    def predict_vep_region_allele(
        self,
        chromosome: str,
        position_one_based: int,
        alt_allele: str,
        reference_genome: str = "hg38",
        strand: int = 1,
        ref_allele: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Call Ensembl VEP **region** endpoint for a single-nucleotide substitution.

        ``position_one_based`` is the VCF POS (first base of the variant, 1-based).
        ``alt_allele`` is the alternate base (A/C/G/T). ``ref_allele`` is optional
        for display only (not sent to Ensembl path allele slot).

        Returns list of lightweight consequence dicts, or ``[error_dict]`` on failure.
        """
        species = species_for_reference(reference_genome)
        ch = normalize_chromosome(chromosome)
        p = int(position_one_based)
        alt = (alt_allele or "").strip().upper()
        if len(alt) != 1 or alt not in "ACGT":
            return [
                build_ensembl_error_payload(
                    kind="invalid_alt",
                    status_code=None,
                    url="",
                    message="VEP requires a single-letter alternate allele (A/C/G/T).",
                )
            ]

        base = self._base(reference_genome)
        region = f"{ch}:{p}-{p}:{strand}"
        url = f"{base}/vep/{species}/region/{region}/{alt}"
        params = {"content-type": "application/json"}

        resp, err = http_get_with_errors(
            url, headers=self.headers, timeout=self.timeout, params=params
        )
        if err:
            return [err]

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            return [
                build_ensembl_error_payload(
                    kind="json_decode",
                    status_code=resp.status_code,
                    url=resp.url,
                    message=str(e),
                    response_text_snippet=resp.text,
                )
            ]

        return self._vep_transcript_rows_from_payload(
            data,
            status_code=resp.status_code,
            url=resp.url,
            response_text=resp.text,
            ref_display=ref_allele,
            alt_display=alt,
        )

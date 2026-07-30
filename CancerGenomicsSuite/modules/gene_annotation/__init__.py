"""Gene locus annotation via public Ensembl REST (overlap + optional VEP)."""

from .ensembl_api_utils import (
    REFERENCE_TO_ENSEMBL_BASE,
    ensembl_rest_base,
    species_for_reference,
)
from .gene_location_predictor import GeneLocationPredictor

__all__ = [
    "GeneLocationPredictor",
    "REFERENCE_TO_ENSEMBL_BASE",
    "ensembl_rest_base",
    "species_for_reference",
]

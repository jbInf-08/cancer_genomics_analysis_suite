"""Gene locus annotation via public Ensembl REST (overlap + optional VEP)."""

from .gene_location_predictor import GeneLocationPredictor
from .ensembl_api_utils import (
    REFERENCE_TO_ENSEMBL_BASE,
    ensembl_rest_base,
    species_for_reference,
)

__all__ = [
    "GeneLocationPredictor",
    "REFERENCE_TO_ENSEMBL_BASE",
    "ensembl_rest_base",
    "species_for_reference",
]

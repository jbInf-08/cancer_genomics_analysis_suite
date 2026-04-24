"""
Mutation Effect Predictor Module

This module provides functionality for predicting the effects of genetic mutations
on protein structure, function, and disease association. It includes various
prediction algorithms and integrates with external databases and tools.
"""

import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
from pathlib import Path
import pickle
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Mutation:
    """Represents a genetic mutation with all relevant information."""
    gene_symbol: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    mutation_type: str  # SNP, insertion, deletion, etc.
    transcript_id: Optional[str] = None
    protein_position: Optional[int] = None
    ref_amino_acid: Optional[str] = None
    alt_amino_acid: Optional[str] = None
    mutation_id: Optional[str] = None
    clinical_significance: Optional[str] = None
    population_frequency: Optional[float] = None
    
    def __post_init__(self):
        """Validate mutation data."""
        if not self.gene_symbol:
            raise ValueError("Gene symbol is required")
        if not self.chromosome:
            raise ValueError("Chromosome is required")
        if self.position < 0:
            raise ValueError("Position must be non-negative")
        if not self.ref_allele or not self.alt_allele:
            raise ValueError("Reference and alternative alleles are required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mutation to dictionary."""
        return asdict(self)
    
    def get_mutation_key(self) -> str:
        """Get unique key for this mutation."""
        return f"{self.chromosome}:{self.position}:{self.ref_allele}:{self.alt_allele}"


@dataclass
class PredictionResult:
    """Represents the result of a mutation effect prediction."""
    mutation: Mutation
    predictor_name: str
    prediction_score: float
    prediction_class: str  # pathogenic, benign, uncertain, etc.
    confidence: float
    additional_info: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction result to dictionary."""
        result_dict = asdict(self)
        result_dict['timestamp'] = self.timestamp.isoformat()
        return result_dict


class MutationEffectPredictor:
    """
    Main class for predicting the effects of genetic mutations.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the mutation effect predictor.
        
        Args:
            model_path: Path to pre-trained model file
        """
        self.model_path = model_path
        self.models = {}
        self.feature_extractors = {}
        self.prediction_cache = {}
        
        # Initialize default predictors
        self._initialize_predictors()
        
        # Supported mutation types
        self.supported_mutation_types = [
            "SNP", "insertion", "deletion", "indel", "complex"
        ]
        
        # Prediction classes
        self.prediction_classes = [
            "pathogenic", "likely_pathogenic", "uncertain_significance",
            "likely_benign", "benign"
        ]
    
    def _initialize_predictors(self):
        """Initialize available prediction models."""
        self.predictors = {
            "sift": self._predict_sift,
            "polyphen2": self._predict_polyphen2,
            "cadd": self._predict_cadd,
            "revel": self._predict_revel,
            "clinvar": self._predict_clinvar,
            "conservation": self._predict_conservation,
            "structural": self._predict_structural
        }
        
        logger.info(f"Initialized {len(self.predictors)} prediction methods")
    
    def predict_mutation_effect(self, mutation: Mutation, 
                              predictors: Optional[List[str]] = None) -> List[PredictionResult]:
        """
        Predict the effect of a mutation using specified predictors.
        
        Args:
            mutation: Mutation object to analyze
            predictors: List of predictor names to use (uses all if None)
            
        Returns:
            List of PredictionResult objects
        """
        if predictors is None:
            predictors = list(self.predictors.keys())
        
        results = []
        mutation_key = mutation.get_mutation_key()
        
        for predictor_name in predictors:
            if predictor_name not in self.predictors:
                logger.warning(f"Unknown predictor: {predictor_name}")
                continue
            
            # Check cache first
            cache_key = f"{mutation_key}_{predictor_name}"
            if cache_key in self.prediction_cache:
                logger.info(f"Using cached result for {predictor_name}")
                results.append(self.prediction_cache[cache_key])
                continue
            
            try:
                logger.info(f"Running {predictor_name} prediction for {mutation.gene_symbol}")
                result = self.predictors[predictor_name](mutation)
                
                # Cache the result
                self.prediction_cache[cache_key] = result
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error in {predictor_name} prediction: {e}")
                # Create error result
                error_result = PredictionResult(
                    mutation=mutation,
                    predictor_name=predictor_name,
                    prediction_score=0.0,
                    prediction_class="error",
                    confidence=0.0,
                    additional_info={"error": str(e)},
                    timestamp=datetime.now()
                )
                results.append(error_result)
        
        return results
    
    def _predict_sift(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect using SIFT (Sorting Intolerant From Tolerant).
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate SIFT prediction (in real implementation, would call SIFT API)
        # SIFT scores: 0.0-1.0, where <0.05 is deleterious
        
        # Mock prediction based on amino acid properties
        if mutation.alt_amino_acid and mutation.ref_amino_acid:
            # Simple scoring based on amino acid similarity
            similarity_score = self._calculate_amino_acid_similarity(
                mutation.ref_amino_acid, mutation.alt_amino_acid
            )
            sift_score = 1.0 - similarity_score
            
            if sift_score < 0.05:
                prediction_class = "pathogenic"
                confidence = 0.9
            elif sift_score < 0.2:
                prediction_class = "likely_pathogenic"
                confidence = 0.7
            elif sift_score > 0.8:
                prediction_class = "benign"
                confidence = 0.8
            else:
                prediction_class = "uncertain_significance"
                confidence = 0.5
        else:
            sift_score = 0.5
            prediction_class = "uncertain_significance"
            confidence = 0.3
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="sift",
            prediction_score=sift_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "SIFT",
                "description": "Sorting Intolerant From Tolerant",
                "score_interpretation": "Score < 0.05 indicates deleterious effect"
            },
            timestamp=datetime.now()
        )
    
    def _predict_polyphen2(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect using PolyPhen-2.
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate PolyPhen-2 prediction
        # PolyPhen-2 scores: 0.0-1.0, where >0.5 is probably damaging
        
        if mutation.alt_amino_acid and mutation.ref_amino_acid:
            # Mock prediction based on amino acid properties
            impact_score = self._calculate_amino_acid_impact(
                mutation.ref_amino_acid, mutation.alt_amino_acid
            )
            
            if impact_score > 0.8:
                prediction_class = "pathogenic"
                confidence = 0.9
            elif impact_score > 0.5:
                prediction_class = "likely_pathogenic"
                confidence = 0.7
            elif impact_score < 0.2:
                prediction_class = "benign"
                confidence = 0.8
            else:
                prediction_class = "uncertain_significance"
                confidence = 0.5
        else:
            impact_score = 0.5
            prediction_class = "uncertain_significance"
            confidence = 0.3
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="polyphen2",
            prediction_score=impact_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "PolyPhen-2",
                "description": "Polymorphism Phenotyping v2",
                "score_interpretation": "Score > 0.5 indicates probably damaging"
            },
            timestamp=datetime.now()
        )
    
    def _predict_cadd(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect using CADD (Combined Annotation Dependent Depletion).
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate CADD prediction
        # CADD scores: 0-100, where >15 is likely deleterious
        
        # Mock CADD score based on mutation type and position
        base_score = 10.0
        
        if mutation.mutation_type == "SNP":
            if mutation.alt_amino_acid and mutation.ref_amino_acid:
                # Increase score for non-synonymous mutations
                if mutation.alt_amino_acid != mutation.ref_amino_acid:
                    base_score += 15.0
        elif mutation.mutation_type in ["insertion", "deletion"]:
            base_score += 20.0
        
        # Add some randomness to simulate real CADD scores
        cadd_score = base_score + np.random.normal(0, 5)
        cadd_score = max(0, min(100, cadd_score))  # Clamp to 0-100
        
        if cadd_score > 30:
            prediction_class = "pathogenic"
            confidence = 0.9
        elif cadd_score > 15:
            prediction_class = "likely_pathogenic"
            confidence = 0.7
        elif cadd_score < 5:
            prediction_class = "benign"
            confidence = 0.8
        else:
            prediction_class = "uncertain_significance"
            confidence = 0.5
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="cadd",
            prediction_score=cadd_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "CADD",
                "description": "Combined Annotation Dependent Depletion",
                "score_interpretation": "Score > 15 indicates likely deleterious effect"
            },
            timestamp=datetime.now()
        )
    
    def _predict_revel(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect using REVEL (Rare Exome Variant Ensemble Learner).
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate REVEL prediction
        # REVEL scores: 0.0-1.0, where >0.5 is likely pathogenic
        
        # Mock REVEL score
        revel_score = np.random.beta(2, 2)  # Beta distribution for 0-1 scores
        
        if revel_score > 0.7:
            prediction_class = "pathogenic"
            confidence = 0.9
        elif revel_score > 0.5:
            prediction_class = "likely_pathogenic"
            confidence = 0.7
        elif revel_score < 0.3:
            prediction_class = "benign"
            confidence = 0.8
        else:
            prediction_class = "uncertain_significance"
            confidence = 0.5
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="revel",
            prediction_score=revel_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "REVEL",
                "description": "Rare Exome Variant Ensemble Learner",
                "score_interpretation": "Score > 0.5 indicates likely pathogenic effect"
            },
            timestamp=datetime.now()
        )
    
    def _predict_clinvar(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect using ClinVar database.
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate ClinVar lookup
        # In real implementation, would query ClinVar API
        
        # Mock ClinVar data
        clinvar_significance = mutation.clinical_significance or "uncertain_significance"
        
        # Map ClinVar terms to our prediction classes
        significance_mapping = {
            "pathogenic": "pathogenic",
            "likely_pathogenic": "likely_pathogenic",
            "uncertain_significance": "uncertain_significance",
            "likely_benign": "likely_benign",
            "benign": "benign"
        }
        
        prediction_class = significance_mapping.get(clinvar_significance, "uncertain_significance")
        
        # Confidence based on ClinVar review status (simulated)
        confidence = 0.8 if clinvar_significance in ["pathogenic", "benign"] else 0.6
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="clinvar",
            prediction_score=0.5,  # ClinVar doesn't provide scores
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "ClinVar",
                "description": "Clinical significance from ClinVar database",
                "clinical_significance": clinvar_significance,
                "review_status": "reviewed_by_expert_panel"
            },
            timestamp=datetime.now()
        )
    
    def _predict_conservation(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect based on evolutionary conservation.
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate conservation score
        # Higher conservation = more likely to be pathogenic when mutated
        
        conservation_score = np.random.uniform(0, 1)
        
        if conservation_score > 0.8:
            prediction_class = "likely_pathogenic"
            confidence = 0.7
        elif conservation_score < 0.3:
            prediction_class = "likely_benign"
            confidence = 0.6
        else:
            prediction_class = "uncertain_significance"
            confidence = 0.4
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="conservation",
            prediction_score=conservation_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "Conservation",
                "description": "Evolutionary conservation analysis",
                "score_interpretation": "Higher scores indicate higher conservation"
            },
            timestamp=datetime.now()
        )
    
    def _predict_structural(self, mutation: Mutation) -> PredictionResult:
        """
        Predict mutation effect based on protein structure analysis.
        
        Args:
            mutation: Mutation to analyze
            
        Returns:
            PredictionResult object
        """
        # Simulate structural impact prediction
        # Based on protein domain, secondary structure, etc.
        
        structural_score = np.random.uniform(0, 1)
        
        if structural_score > 0.7:
            prediction_class = "likely_pathogenic"
            confidence = 0.6
        elif structural_score < 0.3:
            prediction_class = "likely_benign"
            confidence = 0.5
        else:
            prediction_class = "uncertain_significance"
            confidence = 0.4
        
        return PredictionResult(
            mutation=mutation,
            predictor_name="structural",
            prediction_score=structural_score,
            prediction_class=prediction_class,
            confidence=confidence,
            additional_info={
                "method": "Structural",
                "description": "Protein structure impact analysis",
                "score_interpretation": "Higher scores indicate greater structural impact"
            },
            timestamp=datetime.now()
        )
    
    def _calculate_amino_acid_similarity(self, ref_aa: str, alt_aa: str) -> float:
        """
        Calculate similarity between two amino acids.
        
        Args:
            ref_aa: Reference amino acid
            alt_aa: Alternative amino acid
            
        Returns:
            Similarity score (0-1)
        """
        # Simple amino acid similarity matrix
        similarity_matrix = {
            ('A', 'A'): 1.0, ('A', 'V'): 0.7, ('A', 'L'): 0.6, ('A', 'I'): 0.6,
            ('A', 'M'): 0.5, ('A', 'F'): 0.3, ('A', 'Y'): 0.2, ('A', 'W'): 0.2,
            ('A', 'S'): 0.6, ('A', 'T'): 0.5, ('A', 'N'): 0.4, ('A', 'Q'): 0.4,
            ('A', 'C'): 0.3, ('A', 'G'): 0.7, ('A', 'P'): 0.3, ('A', 'R'): 0.2,
            ('A', 'H'): 0.3, ('A', 'K'): 0.2, ('A', 'D'): 0.2, ('A', 'E'): 0.2,
            # Add more pairs as needed...
        }
        
        # Get similarity score (symmetric)
        key1 = (ref_aa, alt_aa)
        key2 = (alt_aa, ref_aa)
        
        if key1 in similarity_matrix:
            return similarity_matrix[key1]
        elif key2 in similarity_matrix:
            return similarity_matrix[key2]
        else:
            return 0.1  # Default low similarity for unknown pairs
    
    def _calculate_amino_acid_impact(self, ref_aa: str, alt_aa: str) -> float:
        """
        Calculate functional impact of amino acid change.
        
        Args:
            ref_aa: Reference amino acid
            alt_aa: Alternative amino acid
            
        Returns:
            Impact score (0-1)
        """
        # Amino acid properties
        aa_properties = {
            'A': {'size': 'small', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'V': {'size': 'small', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'L': {'size': 'medium', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'I': {'size': 'medium', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'M': {'size': 'medium', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'F': {'size': 'large', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'Y': {'size': 'large', 'polarity': 'polar', 'charge': 'neutral'},
            'W': {'size': 'large', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'S': {'size': 'small', 'polarity': 'polar', 'charge': 'neutral'},
            'T': {'size': 'small', 'polarity': 'polar', 'charge': 'neutral'},
            'N': {'size': 'medium', 'polarity': 'polar', 'charge': 'neutral'},
            'Q': {'size': 'medium', 'polarity': 'polar', 'charge': 'neutral'},
            'C': {'size': 'small', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'G': {'size': 'tiny', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'P': {'size': 'small', 'polarity': 'nonpolar', 'charge': 'neutral'},
            'R': {'size': 'large', 'polarity': 'polar', 'charge': 'positive'},
            'H': {'size': 'medium', 'polarity': 'polar', 'charge': 'positive'},
            'K': {'size': 'medium', 'polarity': 'polar', 'charge': 'positive'},
            'D': {'size': 'small', 'polarity': 'polar', 'charge': 'negative'},
            'E': {'size': 'medium', 'polarity': 'polar', 'charge': 'negative'}
        }
        
        if ref_aa not in aa_properties or alt_aa not in aa_properties:
            return 0.5  # Default impact
        
        ref_props = aa_properties[ref_aa]
        alt_props = aa_properties[alt_aa]
        
        impact = 0.0
        
        # Size change impact
        if ref_props['size'] != alt_props['size']:
            impact += 0.3
        
        # Polarity change impact
        if ref_props['polarity'] != alt_props['polarity']:
            impact += 0.4
        
        # Charge change impact
        if ref_props['charge'] != alt_props['charge']:
            impact += 0.3
        
        return min(1.0, impact)
    
    def batch_predict(self, mutations: List[Mutation], 
                     predictors: Optional[List[str]] = None) -> Dict[str, List[PredictionResult]]:
        """
        Predict effects for multiple mutations in batch.
        
        Args:
            mutations: List of Mutation objects
            predictors: List of predictor names to use
            
        Returns:
            Dictionary mapping mutation keys to prediction results
        """
        results = {}
        
        for mutation in mutations:
            mutation_key = mutation.get_mutation_key()
            results[mutation_key] = self.predict_mutation_effect(mutation, predictors)
        
        logger.info(f"Completed batch prediction for {len(mutations)} mutations")
        return results
    
    def get_consensus_prediction(self, results: List[PredictionResult]) -> Dict[str, Any]:
        """
        Get consensus prediction from multiple predictor results.
        
        Args:
            results: List of PredictionResult objects
            
        Returns:
            Dictionary with consensus information
        """
        if not results:
            return {"consensus": "no_predictions", "confidence": 0.0}
        
        # Count predictions by class
        class_counts = {}
        total_confidence = 0.0
        
        for result in results:
            if result.prediction_class not in class_counts:
                class_counts[result.prediction_class] = 0
            class_counts[result.prediction_class] += 1
            total_confidence += result.confidence
        
        # Find most common prediction
        consensus_class = max(class_counts, key=class_counts.get)
        consensus_count = class_counts[consensus_class]
        consensus_ratio = consensus_count / len(results)
        avg_confidence = total_confidence / len(results)
        
        return {
            "consensus_class": consensus_class,
            "consensus_ratio": consensus_ratio,
            "average_confidence": avg_confidence,
            "total_predictors": len(results),
            "class_distribution": class_counts
        }
    
    def export_predictions(self, results: List[PredictionResult], 
                          format: str = "json") -> str:
        """
        Export prediction results to various formats.
        
        Args:
            results: List of PredictionResult objects
            format: Export format ('json', 'csv', 'tsv')
            
        Returns:
            Exported data as string
        """
        if format == "json":
            data = {
                "predictions": [result.to_dict() for result in results],
                "export_timestamp": datetime.now().isoformat(),
                "total_predictions": len(results)
            }
            return json.dumps(data, indent=2)
        
        elif format in ["csv", "tsv"]:
            # Convert to DataFrame
            data = []
            for result in results:
                row = {
                    "gene_symbol": result.mutation.gene_symbol,
                    "chromosome": result.mutation.chromosome,
                    "position": result.mutation.position,
                    "ref_allele": result.mutation.ref_allele,
                    "alt_allele": result.mutation.alt_allele,
                    "predictor": result.predictor_name,
                    "prediction_score": result.prediction_score,
                    "prediction_class": result.prediction_class,
                    "confidence": result.confidence,
                    "timestamp": result.timestamp.isoformat()
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            delimiter = "," if format == "csv" else "\t"
            return df.to_csv(index=False, sep=delimiter)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the predictor.
        
        Returns:
            Dictionary with predictor statistics
        """
        return {
            "total_predictors": len(self.predictors),
            "available_predictors": list(self.predictors.keys()),
            "supported_mutation_types": self.supported_mutation_types,
            "prediction_classes": self.prediction_classes,
            "cache_size": len(self.prediction_cache),
            "model_loaded": self.model_path is not None
        }


def create_sample_mutations() -> List[Mutation]:
    """
    Create sample mutations for testing.
    
    Returns:
        List of sample Mutation objects
    """
    mutations = [
        Mutation(
            gene_symbol="BRCA1",
            chromosome="chr17",
            position=43094695,
            ref_allele="G",
            alt_allele="A",
            mutation_type="SNP",
            transcript_id="NM_007294.3",
            protein_position=185,
            ref_amino_acid="G",
            alt_amino_acid="E",
            mutation_id="rs80357382",
            clinical_significance="pathogenic",
            population_frequency=0.0001
        ),
        Mutation(
            gene_symbol="TP53",
            chromosome="chr17",
            position=7574003,
            ref_allele="C",
            alt_allele="T",
            mutation_type="SNP",
            transcript_id="NM_000546.5",
            protein_position=175,
            ref_amino_acid="R",
            alt_amino_acid="H",
            mutation_id="rs28934578",
            clinical_significance="pathogenic",
            population_frequency=0.0002
        ),
        Mutation(
            gene_symbol="EGFR",
            chromosome="chr7",
            position=55241707,
            ref_allele="G",
            alt_allele="A",
            mutation_type="SNP",
            transcript_id="NM_005228.3",
            protein_position=858,
            ref_amino_acid="G",
            alt_amino_acid="S",
            mutation_id="rs121434568",
            clinical_significance="pathogenic",
            population_frequency=0.0003
        )
    ]
    
    return mutations


def create_sample_predictor() -> MutationEffectPredictor:
    """
    Create a sample predictor with example data.
    
    Returns:
        MutationEffectPredictor instance
    """
    predictor = MutationEffectPredictor()
    
    # Add some sample mutations to cache
    sample_mutations = create_sample_mutations()
    for mutation in sample_mutations:
        predictor.predict_mutation_effect(mutation)
    
    return predictor


if __name__ == "__main__":
    # Example usage
    predictor = create_sample_predictor()
    
    print("Mutation Effect Predictor Statistics:")
    stats = predictor.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSample Predictions:")
    sample_mutations = create_sample_mutations()
    for mutation in sample_mutations:
        print(f"\nAnalyzing {mutation.gene_symbol} {mutation.ref_amino_acid}{mutation.protein_position}{mutation.alt_amino_acid}")
        results = predictor.predict_mutation_effect(mutation)
        
        for result in results:
            print(f"  {result.predictor_name}: {result.prediction_class} (score: {result.prediction_score:.3f}, confidence: {result.confidence:.3f})")
        
        consensus = predictor.get_consensus_prediction(results)
        print(f"  Consensus: {consensus['consensus_class']} (ratio: {consensus['consensus_ratio']:.2f})")

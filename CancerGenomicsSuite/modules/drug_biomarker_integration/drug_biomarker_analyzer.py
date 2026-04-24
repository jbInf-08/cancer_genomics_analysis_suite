"""
Drug-Biomarker Integration Analyzer for Cancer Genomics Analysis

This module provides comprehensive integration between drug discovery and biomarker analysis
for personalized medicine and clinical decision support.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor
from sklearn.svm import SVR, SVC
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.model_selection import cross_val_score, GridSearchCV, train_test_split
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score, accuracy_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
import xgboost as xgb
import lightgbm as lgb

# Network Analysis
import networkx as nx
from networkx.algorithms import centrality, community

# Statistical Analysis
import scipy.stats as stats
from scipy.stats import pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)


@dataclass
class DrugBiomarkerInteraction:
    """Data class for drug-biomarker interaction results."""
    drug_id: str
    biomarker_id: str
    interaction_type: str
    interaction_strength: float
    p_value: float
    effect_size: float
    clinical_significance: str
    mechanism: str
    supporting_evidence: List[str]
    metadata: Dict[str, Any]


@dataclass
class PersonalizedTreatment:
    """Data class for personalized treatment recommendations."""
    patient_id: str
    recommended_drugs: List[str]
    biomarker_profile: Dict[str, float]
    drug_scores: Dict[str, float]
    confidence_scores: Dict[str, float]
    contraindications: List[str]
    monitoring_biomarkers: List[str]
    treatment_plan: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class PharmacogenomicsProfile:
    """Data class for pharmacogenomics profile."""
    patient_id: str
    genetic_variants: Dict[str, str]
    drug_metabolism: Dict[str, str]
    drug_transport: Dict[str, str]
    drug_targets: Dict[str, str]
    adverse_reactions: List[str]
    dose_adjustments: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass
class DrugBiomarkerConfig:
    """Configuration for drug-biomarker integration analysis."""
    min_interaction_strength: float = 0.3
    p_value_threshold: float = 0.05
    effect_size_threshold: float = 0.2
    confidence_threshold: float = 0.7
    cross_validation_folds: int = 5
    random_state: int = 42
    min_samples_per_group: int = 10


class DrugBiomarkerAnalyzer:
    """Main drug-biomarker integration analyzer."""
    
    def __init__(self, config: Optional[DrugBiomarkerConfig] = None):
        """Initialize the drug-biomarker analyzer."""
        self.config = config or DrugBiomarkerConfig()
        self.interactions = []
        self.treatment_recommendations = []
        self.logger = logging.getLogger(__name__)
        
    def analyze_drug_biomarker_interactions(self, 
                                          drug_data: pd.DataFrame,
                                          biomarker_data: pd.DataFrame,
                                          response_data: pd.DataFrame,
                                          **kwargs) -> List[DrugBiomarkerInteraction]:
        """
        Analyze interactions between drugs and biomarkers.
        
        Args:
            drug_data: Drug features and properties
            biomarker_data: Biomarker expression/levels
            response_data: Drug response data
            **kwargs: Additional parameters
            
        Returns:
            List of drug-biomarker interactions
        """
        self.logger.info("Starting drug-biomarker interaction analysis")
        
        interactions = []
        
        # Analyze each drug-biomarker pair
        for drug_id in drug_data.index:
            for biomarker_id in biomarker_data.columns:
                try:
                    interaction = self._analyze_single_interaction(
                        drug_id, biomarker_id, drug_data, biomarker_data, response_data
                    )
                    
                    if interaction and interaction.interaction_strength > self.config.min_interaction_strength:
                        interactions.append(interaction)
                        
                except Exception as e:
                    self.logger.warning(f"Error analyzing interaction {drug_id}-{biomarker_id}: {e}")
                    continue
        
        # Multiple testing correction
        p_values = [i.p_value for i in interactions]
        corrected_p_values = multipletests(
            p_values, 
            method='fdr_bh'
        )[1]
        
        for i, interaction in enumerate(interactions):
            interaction.p_value = corrected_p_values[i]
        
        # Filter by corrected p-values
        filtered_interactions = [
            i for i in interactions 
            if i.p_value < self.config.p_value_threshold
        ]
        
        self.interactions = filtered_interactions
        self.logger.info(f"Found {len(filtered_interactions)} significant drug-biomarker interactions")
        
        return filtered_interactions
    
    def _analyze_single_interaction(self, 
                                  drug_id: str,
                                  biomarker_id: str,
                                  drug_data: pd.DataFrame,
                                  biomarker_data: pd.DataFrame,
                                  response_data: pd.DataFrame) -> Optional[DrugBiomarkerInteraction]:
        """Analyze interaction between a single drug and biomarker."""
        try:
            # Get data for this drug-biomarker pair
            drug_response = response_data[drug_id].dropna()
            biomarker_levels = biomarker_data[biomarker_id].dropna()
            
            # Find common samples
            common_samples = drug_response.index.intersection(biomarker_levels.index)
            
            if len(common_samples) < self.config.min_samples_per_group:
                return None
            
            drug_response_common = drug_response[common_samples]
            biomarker_levels_common = biomarker_levels[common_samples]
            
            # Calculate correlation
            correlation, p_value = pearsonr(drug_response_common, biomarker_levels_common)
            
            # Calculate effect size
            effect_size = abs(correlation)
            
            # Determine interaction type
            interaction_type = self._determine_interaction_type(correlation, p_value)
            
            # Calculate interaction strength
            interaction_strength = self._calculate_interaction_strength(
                correlation, p_value, effect_size
            )
            
            # Assess clinical significance
            clinical_significance = self._assess_clinical_significance(
                interaction_strength, p_value, effect_size
            )
            
            # Get mechanism
            mechanism = self._get_interaction_mechanism(drug_id, biomarker_id)
            
            # Get supporting evidence
            supporting_evidence = self._get_supporting_evidence(drug_id, biomarker_id)
            
            interaction = DrugBiomarkerInteraction(
                drug_id=drug_id,
                biomarker_id=biomarker_id,
                interaction_type=interaction_type,
                interaction_strength=interaction_strength,
                p_value=p_value,
                effect_size=effect_size,
                clinical_significance=clinical_significance,
                mechanism=mechanism,
                supporting_evidence=supporting_evidence,
                metadata={
                    'correlation': correlation,
                    'n_samples': len(common_samples),
                    'analysis_timestamp': pd.Timestamp.now().isoformat()
                }
            )
            
            return interaction
            
        except Exception as e:
            self.logger.warning(f"Error in single interaction analysis: {e}")
            return None
    
    def _determine_interaction_type(self, correlation: float, p_value: float) -> str:
        """Determine the type of drug-biomarker interaction."""
        if p_value >= self.config.p_value_threshold:
            return 'no_interaction'
        elif correlation > 0.3:
            return 'positive_correlation'
        elif correlation < -0.3:
            return 'negative_correlation'
        else:
            return 'weak_interaction'
    
    def _calculate_interaction_strength(self, 
                                      correlation: float, 
                                      p_value: float, 
                                      effect_size: float) -> float:
        """Calculate interaction strength score."""
        # Combine correlation strength, significance, and effect size
        strength = (
            abs(correlation) * 0.4 +  # Correlation component
            (1 - p_value) * 0.3 +     # Significance component
            effect_size * 0.3         # Effect size component
        )
        
        return min(strength, 1.0)
    
    def _assess_clinical_significance(self, 
                                    interaction_strength: float, 
                                    p_value: float, 
                                    effect_size: float) -> str:
        """Assess clinical significance of interaction."""
        if interaction_strength > 0.8 and p_value < 0.001 and effect_size > 0.5:
            return 'high'
        elif interaction_strength > 0.6 and p_value < 0.01 and effect_size > 0.3:
            return 'moderate'
        elif interaction_strength > 0.4 and p_value < 0.05 and effect_size > 0.2:
            return 'low'
        else:
            return 'minimal'
    
    def _get_interaction_mechanism(self, drug_id: str, biomarker_id: str) -> str:
        """Get mechanism of drug-biomarker interaction."""
        # Mock implementation - would use knowledge bases
        mechanisms = {
            ('erlotinib', 'EGFR'): 'Direct target inhibition',
            ('vemurafenib', 'BRAF'): 'Direct target inhibition',
            ('pembrolizumab', 'PDL1'): 'Immune checkpoint modulation',
            ('metformin', 'glucose'): 'Metabolic pathway modulation'
        }
        
        return mechanisms.get((drug_id, biomarker_id), 'Mechanism not well characterized')
    
    def _get_supporting_evidence(self, drug_id: str, biomarker_id: str) -> List[str]:
        """Get supporting evidence for drug-biomarker interaction."""
        # Mock implementation - would query literature databases
        evidence = {
            ('erlotinib', 'EGFR'): ['PMID:12345678', 'Clinical trial data'],
            ('vemurafenib', 'BRAF'): ['PMID:87654321', 'FDA approval data'],
            ('pembrolizumab', 'PDL1'): ['PMID:11223344', 'Biomarker companion diagnostic']
        }
        
        return evidence.get((drug_id, biomarker_id), ['Limited evidence'])
    
    def predict_drug_response(self, 
                            patient_biomarkers: Dict[str, float],
                            drug_candidates: List[str],
                            **kwargs) -> Dict[str, float]:
        """
        Predict drug response based on patient biomarkers.
        
        Args:
            patient_biomarkers: Patient's biomarker profile
            drug_candidates: List of candidate drugs
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of drug response predictions
        """
        self.logger.info(f"Predicting drug response for {len(drug_candidates)} drugs")
        
        predictions = {}
        
        for drug_id in drug_candidates:
            try:
                # Get relevant interactions for this drug
                drug_interactions = [
                    i for i in self.interactions 
                    if i.drug_id == drug_id and i.biomarker_id in patient_biomarkers
                ]
                
                if not drug_interactions:
                    predictions[drug_id] = 0.5  # Default prediction
                    continue
                
                # Calculate response score based on interactions
                response_score = self._calculate_response_score(
                    patient_biomarkers, drug_interactions
                )
                
                predictions[drug_id] = response_score
                
            except Exception as e:
                self.logger.warning(f"Error predicting response for {drug_id}: {e}")
                predictions[drug_id] = 0.5
        
        return predictions
    
    def _calculate_response_score(self, 
                                patient_biomarkers: Dict[str, float],
                                drug_interactions: List[DrugBiomarkerInteraction]) -> float:
        """Calculate drug response score based on patient biomarkers and interactions."""
        if not drug_interactions:
            return 0.5
        
        weighted_scores = []
        weights = []
        
        for interaction in drug_interactions:
            biomarker_id = interaction.biomarker_id
            patient_level = patient_biomarkers.get(biomarker_id, 0.0)
            
            # Calculate score based on interaction type and patient biomarker level
            if interaction.interaction_type == 'positive_correlation':
                # Higher biomarker level = better response
                score = patient_level * interaction.interaction_strength
            elif interaction.interaction_type == 'negative_correlation':
                # Lower biomarker level = better response
                score = (1 - patient_level) * interaction.interaction_strength
            else:
                score = 0.5 * interaction.interaction_strength
            
            weighted_scores.append(score)
            weights.append(interaction.interaction_strength)
        
        # Calculate weighted average
        if weights:
            response_score = np.average(weighted_scores, weights=weights)
        else:
            response_score = 0.5
        
        return min(max(response_score, 0.0), 1.0)
    
    def get_top_interactions(self, n: int = 10) -> List[DrugBiomarkerInteraction]:
        """Get top N drug-biomarker interactions by strength."""
        if not self.interactions:
            return []
        
        sorted_interactions = sorted(
            self.interactions, 
            key=lambda x: x.interaction_strength, 
            reverse=True
        )
        
        return sorted_interactions[:n]
    
    def export_interactions(self, filepath: str, format: str = 'csv') -> None:
        """Export drug-biomarker interactions to file."""
        if not self.interactions:
            self.logger.warning("No interactions to export")
            return
        
        # Convert interactions to DataFrame
        interactions_data = []
        for interaction in self.interactions:
            row = {
                'drug_id': interaction.drug_id,
                'biomarker_id': interaction.biomarker_id,
                'interaction_type': interaction.interaction_type,
                'interaction_strength': interaction.interaction_strength,
                'p_value': interaction.p_value,
                'effect_size': interaction.effect_size,
                'clinical_significance': interaction.clinical_significance,
                'mechanism': interaction.mechanism,
                'supporting_evidence': '; '.join(interaction.supporting_evidence)
            }
            row.update(interaction.metadata)
            interactions_data.append(row)
        
        df = pd.DataFrame(interactions_data)
        
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False)
        elif format.lower() == 'excel':
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Interactions exported to {filepath}")


class PharmacogenomicsIntegrator:
    """Specialized class for pharmacogenomics integration."""
    
    def __init__(self, config: Optional[DrugBiomarkerConfig] = None):
        self.config = config or DrugBiomarkerConfig()
        self.logger = logging.getLogger(__name__)
        
        # Pharmacogenomics databases (mock)
        self.cyp_variants = {
            'CYP2D6': {'*1': 'normal', '*2': 'normal', '*3': 'poor', '*4': 'poor', '*5': 'null'},
            'CYP2C19': {'*1': 'normal', '*2': 'poor', '*3': 'poor', '*17': 'ultra_rapid'},
            'CYP3A4': {'*1': 'normal', '*22': 'poor', '*1B': 'normal'}
        }
        
        self.drug_metabolism = {
            'erlotinib': {'CYP3A4': 0.8, 'CYP1A2': 0.2},
            'vemurafenib': {'CYP3A4': 0.9, 'CYP2D6': 0.1},
            'metformin': {'OCT1': 0.6, 'OCT2': 0.4}
        }
    
    def create_pharmacogenomics_profile(self, 
                                      patient_id: str,
                                      genetic_variants: Dict[str, str],
                                      **kwargs) -> PharmacogenomicsProfile:
        """Create pharmacogenomics profile for a patient."""
        self.logger.info(f"Creating pharmacogenomics profile for patient {patient_id}")
        
        # Analyze drug metabolism
        drug_metabolism = self._analyze_drug_metabolism(genetic_variants)
        
        # Analyze drug transport
        drug_transport = self._analyze_drug_transport(genetic_variants)
        
        # Analyze drug targets
        drug_targets = self._analyze_drug_targets(genetic_variants)
        
        # Identify adverse reactions
        adverse_reactions = self._identify_adverse_reactions(genetic_variants)
        
        # Calculate dose adjustments
        dose_adjustments = self._calculate_dose_adjustments(
            drug_metabolism, drug_transport, drug_targets
        )
        
        profile = PharmacogenomicsProfile(
            patient_id=patient_id,
            genetic_variants=genetic_variants,
            drug_metabolism=drug_metabolism,
            drug_transport=drug_transport,
            drug_targets=drug_targets,
            adverse_reactions=adverse_reactions,
            dose_adjustments=dose_adjustments,
            metadata={
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'variants_analyzed': len(genetic_variants)
            }
        )
        
        return profile
    
    def _analyze_drug_metabolism(self, genetic_variants: Dict[str, str]) -> Dict[str, str]:
        """Analyze drug metabolism based on genetic variants."""
        metabolism_profile = {}
        
        for gene, variant in genetic_variants.items():
            if gene in self.cyp_variants:
                metabolism_profile[gene] = self.cyp_variants[gene].get(variant, 'unknown')
        
        return metabolism_profile
    
    def _analyze_drug_transport(self, genetic_variants: Dict[str, str]) -> Dict[str, str]:
        """Analyze drug transport based on genetic variants."""
        transport_profile = {}
        
        # Mock implementation for transport genes
        transport_genes = ['ABCB1', 'ABCC2', 'ABCG2', 'OCT1', 'OCT2', 'OATP1B1']
        
        for gene in transport_genes:
            if gene in genetic_variants:
                variant = genetic_variants[gene]
                # Simple classification
                if 'del' in variant or 'null' in variant:
                    transport_profile[gene] = 'reduced'
                elif 'dup' in variant or 'gain' in variant:
                    transport_profile[gene] = 'increased'
                else:
                    transport_profile[gene] = 'normal'
        
        return transport_profile
    
    def _analyze_drug_targets(self, genetic_variants: Dict[str, str]) -> Dict[str, str]:
        """Analyze drug targets based on genetic variants."""
        target_profile = {}
        
        # Mock implementation for target genes
        target_genes = ['EGFR', 'BRAF', 'KRAS', 'PIK3CA', 'TP53']
        
        for gene in target_genes:
            if gene in genetic_variants:
                variant = genetic_variants[gene]
                # Simple classification
                if 'mut' in variant or 'del' in variant:
                    target_profile[gene] = 'mutated'
                elif 'amp' in variant or 'gain' in variant:
                    target_profile[gene] = 'amplified'
                else:
                    target_profile[gene] = 'wild_type'
        
        return target_profile
    
    def _identify_adverse_reactions(self, genetic_variants: Dict[str, str]) -> List[str]:
        """Identify potential adverse reactions based on genetic variants."""
        adverse_reactions = []
        
        # Mock implementation
        if 'HLA-B*57:01' in genetic_variants.values():
            adverse_reactions.append('Abacavir hypersensitivity')
        
        if 'CYP2D6' in genetic_variants and genetic_variants['CYP2D6'] in ['*3', '*4', '*5']:
            adverse_reactions.append('Codeine toxicity (poor metabolizer)')
        
        if 'DPYD' in genetic_variants and 'del' in genetic_variants['DPYD']:
            adverse_reactions.append('5-FU toxicity')
        
        return adverse_reactions
    
    def _calculate_dose_adjustments(self, 
                                  drug_metabolism: Dict[str, str],
                                  drug_transport: Dict[str, str],
                                  drug_targets: Dict[str, str]) -> Dict[str, float]:
        """Calculate dose adjustments based on pharmacogenomics profile."""
        dose_adjustments = {}
        
        # Mock implementation
        for drug, metabolism_genes in self.drug_metabolism.items():
            adjustment_factor = 1.0
            
            for gene, contribution in metabolism_genes.items():
                if gene in drug_metabolism:
                    phenotype = drug_metabolism[gene]
                    if phenotype == 'poor':
                        adjustment_factor *= 0.5
                    elif phenotype == 'ultra_rapid':
                        adjustment_factor *= 1.5
            
            dose_adjustments[drug] = adjustment_factor
        
        return dose_adjustments
    
    def predict_drug_response_with_pharmacogenomics(self, 
                                                  patient_biomarkers: Dict[str, float],
                                                  pharmacogenomics_profile: PharmacogenomicsProfile,
                                                  drug_candidates: List[str]) -> Dict[str, float]:
        """Predict drug response incorporating pharmacogenomics data."""
        predictions = {}
        
        for drug_id in drug_candidates:
            try:
                # Base prediction from biomarkers
                base_prediction = 0.5  # Would use biomarker-based prediction
                
                # Adjust based on pharmacogenomics
                if drug_id in pharmacogenomics_profile.dose_adjustments:
                    dose_adjustment = pharmacogenomics_profile.dose_adjustments[drug_id]
                    
                    # Adjust prediction based on dose adjustment
                    if dose_adjustment < 0.5:  # Poor metabolizer
                        adjusted_prediction = base_prediction * 0.7
                    elif dose_adjustment > 1.5:  # Ultra-rapid metabolizer
                        adjusted_prediction = base_prediction * 1.2
                    else:
                        adjusted_prediction = base_prediction
                    
                    predictions[drug_id] = min(adjusted_prediction, 1.0)
                else:
                    predictions[drug_id] = base_prediction
                    
            except Exception as e:
                self.logger.warning(f"Error in pharmacogenomics prediction for {drug_id}: {e}")
                predictions[drug_id] = 0.5
        
        return predictions


class PersonalizedMedicineEngine:
    """Engine for personalized medicine recommendations."""
    
    def __init__(self, config: Optional[DrugBiomarkerConfig] = None):
        self.config = config or DrugBiomarkerConfig()
        self.logger = logging.getLogger(__name__)
    
    def generate_treatment_recommendations(self, 
                                        patient_id: str,
                                        patient_biomarkers: Dict[str, float],
                                        pharmacogenomics_profile: Optional[PharmacogenomicsProfile] = None,
                                        drug_candidates: List[str] = None,
                                        **kwargs) -> PersonalizedTreatment:
        """Generate personalized treatment recommendations."""
        self.logger.info(f"Generating treatment recommendations for patient {patient_id}")
        
        if drug_candidates is None:
            drug_candidates = ['erlotinib', 'vemurafenib', 'pembrolizumab', 'metformin']
        
        # Predict drug responses
        if pharmacogenomics_profile:
            from .drug_biomarker_analyzer import DrugBiomarkerAnalyzer
            analyzer = DrugBiomarkerAnalyzer(self.config)
            drug_scores = analyzer.predict_drug_response(patient_biomarkers, drug_candidates)
        else:
            drug_scores = {drug: 0.5 for drug in drug_candidates}
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            patient_biomarkers, drug_scores, pharmacogenomics_profile
        )
        
        # Identify contraindications
        contraindications = self._identify_contraindications(
            patient_biomarkers, pharmacogenomics_profile
        )
        
        # Select monitoring biomarkers
        monitoring_biomarkers = self._select_monitoring_biomarkers(
            patient_biomarkers, drug_candidates
        )
        
        # Generate treatment plan
        treatment_plan = self._generate_treatment_plan(
            drug_scores, confidence_scores, contraindications
        )
        
        # Select recommended drugs
        recommended_drugs = self._select_recommended_drugs(
            drug_scores, confidence_scores, contraindications
        )
        
        treatment = PersonalizedTreatment(
            patient_id=patient_id,
            recommended_drugs=recommended_drugs,
            biomarker_profile=patient_biomarkers,
            drug_scores=drug_scores,
            confidence_scores=confidence_scores,
            contraindications=contraindications,
            monitoring_biomarkers=monitoring_biomarkers,
            treatment_plan=treatment_plan,
            metadata={
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'pharmacogenomics_included': pharmacogenomics_profile is not None,
                'n_biomarkers': len(patient_biomarkers),
                'n_drugs_evaluated': len(drug_candidates)
            }
        )
        
        return treatment
    
    def _calculate_confidence_scores(self, 
                                   patient_biomarkers: Dict[str, float],
                                   drug_scores: Dict[str, float],
                                   pharmacogenomics_profile: Optional[PharmacogenomicsProfile]) -> Dict[str, float]:
        """Calculate confidence scores for drug recommendations."""
        confidence_scores = {}
        
        for drug_id, score in drug_scores.items():
            confidence = 0.5  # Base confidence
            
            # Increase confidence based on biomarker coverage
            biomarker_coverage = len(patient_biomarkers) / 10.0  # Normalize to 0-1
            confidence += biomarker_coverage * 0.3
            
            # Increase confidence if pharmacogenomics data available
            if pharmacogenomics_profile:
                confidence += 0.2
            
            # Adjust based on drug score
            if score > 0.8 or score < 0.2:
                confidence += 0.1  # High confidence for extreme scores
            
            confidence_scores[drug_id] = min(confidence, 1.0)
        
        return confidence_scores
    
    def _identify_contraindications(self, 
                                  patient_biomarkers: Dict[str, float],
                                  pharmacogenomics_profile: Optional[PharmacogenomicsProfile]) -> List[str]:
        """Identify contraindications for treatment."""
        contraindications = []
        
        # Check biomarker-based contraindications
        if 'liver_function' in patient_biomarkers and patient_biomarkers['liver_function'] < 0.3:
            contraindications.append('Severe liver dysfunction')
        
        if 'kidney_function' in patient_biomarkers and patient_biomarkers['kidney_function'] < 0.3:
            contraindications.append('Severe kidney dysfunction')
        
        # Check pharmacogenomics contraindications
        if pharmacogenomics_profile:
            contraindications.extend(pharmacogenomics_profile.adverse_reactions)
        
        return contraindications
    
    def _select_monitoring_biomarkers(self, 
                                    patient_biomarkers: Dict[str, float],
                                    drug_candidates: List[str]) -> List[str]:
        """Select biomarkers for treatment monitoring."""
        monitoring_biomarkers = []
        
        # Add key biomarkers for monitoring
        key_biomarkers = ['liver_function', 'kidney_function', 'blood_count', 'inflammation']
        monitoring_biomarkers.extend([b for b in key_biomarkers if b in patient_biomarkers])
        
        # Add drug-specific monitoring biomarkers
        drug_monitoring = {
            'erlotinib': ['EGFR_expression', 'skin_toxicity'],
            'vemurafenib': ['BRAF_mutation', 'skin_toxicity'],
            'pembrolizumab': ['PDL1_expression', 'immune_response'],
            'metformin': ['glucose_level', 'lactate_level']
        }
        
        for drug in drug_candidates:
            if drug in drug_monitoring:
                monitoring_biomarkers.extend(drug_monitoring[drug])
        
        return list(set(monitoring_biomarkers))  # Remove duplicates
    
    def _generate_treatment_plan(self, 
                               drug_scores: Dict[str, float],
                               confidence_scores: Dict[str, float],
                               contraindications: List[str]) -> Dict[str, Any]:
        """Generate detailed treatment plan."""
        treatment_plan = {
            'primary_treatment': None,
            'alternative_treatments': [],
            'monitoring_schedule': 'weekly',
            'dose_adjustment_needed': False,
            'special_considerations': contraindications
        }
        
        # Select primary treatment (highest score with high confidence)
        best_drug = None
        best_score = 0.0
        
        for drug_id, score in drug_scores.items():
            confidence = confidence_scores.get(drug_id, 0.0)
            combined_score = score * confidence
            
            if combined_score > best_score:
                best_score = combined_score
                best_drug = drug_id
        
        if best_drug:
            treatment_plan['primary_treatment'] = best_drug
            
            # Select alternative treatments
            sorted_drugs = sorted(
                drug_scores.items(), 
                key=lambda x: x[1] * confidence_scores.get(x[0], 0.0), 
                reverse=True
            )
            
            treatment_plan['alternative_treatments'] = [
                drug for drug, score in sorted_drugs[1:3]  # Top 2 alternatives
            ]
        
        return treatment_plan
    
    def _select_recommended_drugs(self, 
                                drug_scores: Dict[str, float],
                                confidence_scores: Dict[str, float],
                                contraindications: List[str]) -> List[str]:
        """Select recommended drugs based on scores and contraindications."""
        # Filter out contraindicated drugs
        available_drugs = {
            drug: score for drug, score in drug_scores.items()
            if not any(contraindication.lower() in drug.lower() for contraindication in contraindications)
        }
        
        # Sort by combined score
        sorted_drugs = sorted(
            available_drugs.items(),
            key=lambda x: x[1] * confidence_scores.get(x[0], 0.0),
            reverse=True
        )
        
        # Return top 3 recommendations
        return [drug for drug, score in sorted_drugs[:3]]

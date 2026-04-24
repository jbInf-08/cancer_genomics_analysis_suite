"""
Drug Analyzer for Cancer Genomics Analysis

This module provides comprehensive drug discovery and analysis capabilities
including target identification, repurposing, and mechanism analysis.
"""

import numpy as np
import pandas as pd
import requests
import json
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.svm import SVR, SVC
from sklearn.linear_model import ElasticNet, LogisticRegression
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb
import lightgbm as lgb

# Network Analysis
import networkx as nx
from networkx.algorithms import centrality, community

# Bioinformatics
from Bio import Entrez
from Bio.Entrez import efetch, esearch

logger = logging.getLogger(__name__)


@dataclass
class DrugResult:
    """Data class for drug analysis results."""
    drug_id: str
    drug_name: str
    drug_type: str
    target_genes: List[str]
    mechanism_of_action: str
    therapeutic_indication: str
    efficacy_score: float
    safety_score: float
    repurposing_potential: float
    clinical_evidence: List[str]
    supporting_literature: List[str]
    metadata: Dict[str, Any]


@dataclass
class DrugTarget:
    """Data class for drug target information."""
    target_id: str
    target_name: str
    target_type: str
    gene_symbol: str
    protein_name: str
    pathway: str
    druggability_score: float
    expression_level: float
    mutation_frequency: float
    clinical_relevance: str
    metadata: Dict[str, Any]


@dataclass
class DrugDiscoveryConfig:
    """Configuration for drug discovery analysis."""
    min_efficacy_score: float = 0.6
    min_safety_score: float = 0.7
    repurposing_threshold: float = 0.8
    target_druggability_threshold: float = 0.5
    network_centrality_threshold: float = 0.3
    cross_validation_folds: int = 5
    random_state: int = 42


class DrugAnalyzer:
    """Main drug analyzer class."""
    
    def __init__(self, config: Optional[DrugDiscoveryConfig] = None):
        """Initialize the drug analyzer."""
        self.config = config or DrugDiscoveryConfig()
        self.drug_database = {}
        self.target_database = {}
        self.results = []
        self.logger = logging.getLogger(__name__)
        
    def analyze_drugs(self, 
                     genomic_data: pd.DataFrame,
                     drug_data: pd.DataFrame,
                     analysis_type: str = 'comprehensive',
                     **kwargs) -> List[DrugResult]:
        """
        Analyze drugs for cancer treatment potential.
        
        Args:
            genomic_data: Genomic features (genes, mutations, expression)
            drug_data: Drug response or interaction data
            analysis_type: Type of analysis to perform
            **kwargs: Additional parameters
            
        Returns:
            List of analyzed drugs with scores and recommendations
        """
        self.logger.info(f"Starting {analysis_type} drug analysis")
        
        if analysis_type == 'comprehensive':
            results = self._comprehensive_analysis(genomic_data, drug_data)
        elif analysis_type == 'repurposing':
            results = self._repurposing_analysis(genomic_data, drug_data)
        elif analysis_type == 'target_identification':
            results = self._target_identification_analysis(genomic_data, drug_data)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        self.results = results
        self.logger.info(f"Analyzed {len(results)} drugs")
        
        return results
    
    def _comprehensive_analysis(self, 
                              genomic_data: pd.DataFrame, 
                              drug_data: pd.DataFrame) -> List[DrugResult]:
        """Perform comprehensive drug analysis."""
        results = []
        
        # Get drug targets
        drug_targets = self._identify_drug_targets(genomic_data)
        
        # Analyze each drug
        for drug_id in drug_data.index:
            try:
                drug_info = drug_data.loc[drug_id]
                
                # Calculate efficacy score
                efficacy_score = self._calculate_efficacy_score(
                    drug_id, drug_info, genomic_data, drug_targets
                )
                
                # Calculate safety score
                safety_score = self._calculate_safety_score(drug_id, drug_info)
                
                # Calculate repurposing potential
                repurposing_potential = self._calculate_repurposing_potential(
                    drug_id, drug_info, genomic_data
                )
                
                # Get mechanism of action
                mechanism = self._get_mechanism_of_action(drug_id, drug_targets)
                
                # Get clinical evidence
                clinical_evidence = self._get_clinical_evidence(drug_id)
                
                # Get supporting literature
                literature = self._get_supporting_literature(drug_id)
                
                result = DrugResult(
                    drug_id=drug_id,
                    drug_name=drug_info.get('name', drug_id),
                    drug_type=drug_info.get('type', 'unknown'),
                    target_genes=drug_targets.get(drug_id, []),
                    mechanism_of_action=mechanism,
                    therapeutic_indication=drug_info.get('indication', 'cancer'),
                    efficacy_score=efficacy_score,
                    safety_score=safety_score,
                    repurposing_potential=repurposing_potential,
                    clinical_evidence=clinical_evidence,
                    supporting_literature=literature,
                    metadata={
                        'analysis_type': 'comprehensive',
                        'genomic_features': list(genomic_data.columns),
                        'analysis_timestamp': pd.Timestamp.now().isoformat()
                    }
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Error analyzing drug {drug_id}: {e}")
                continue
        
        # Sort by combined score
        results.sort(key=lambda x: (x.efficacy_score + x.safety_score + x.repurposing_potential) / 3, 
                    reverse=True)
        
        return results
    
    def _repurposing_analysis(self, 
                            genomic_data: pd.DataFrame, 
                            drug_data: pd.DataFrame) -> List[DrugResult]:
        """Perform drug repurposing analysis."""
        results = []
        
        # Focus on existing drugs with new indications
        for drug_id in drug_data.index:
            try:
                drug_info = drug_data.loc[drug_id]
                
                # Calculate repurposing score based on genomic profile
                repurposing_score = self._calculate_repurposing_score(
                    drug_id, drug_info, genomic_data
                )
                
                # Check if drug has existing cancer indication
                has_cancer_indication = self._check_cancer_indication(drug_id)
                
                if repurposing_score > self.config.repurposing_threshold and not has_cancer_indication:
                    result = DrugResult(
                        drug_id=drug_id,
                        drug_name=drug_info.get('name', drug_id),
                        drug_type=drug_info.get('type', 'unknown'),
                        target_genes=self._get_drug_targets(drug_id),
                        mechanism_of_action=self._get_mechanism_of_action(drug_id),
                        therapeutic_indication='cancer_repurposing',
                        efficacy_score=repurposing_score,
                        safety_score=self._calculate_safety_score(drug_id, drug_info),
                        repurposing_potential=repurposing_score,
                        clinical_evidence=self._get_clinical_evidence(drug_id),
                        supporting_literature=self._get_supporting_literature(drug_id),
                        metadata={'analysis_type': 'repurposing'}
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                self.logger.warning(f"Error in repurposing analysis for {drug_id}: {e}")
                continue
        
        return results
    
    def _target_identification_analysis(self, 
                                      genomic_data: pd.DataFrame, 
                                      drug_data: pd.DataFrame) -> List[DrugResult]:
        """Perform drug target identification analysis."""
        results = []
        
        # Identify potential drug targets
        potential_targets = self._identify_potential_targets(genomic_data)
        
        # For each potential target, find existing drugs
        for target in potential_targets:
            try:
                existing_drugs = self._find_drugs_for_target(target)
                
                for drug_id in existing_drugs:
                    drug_info = drug_data.loc[drug_id] if drug_id in drug_data.index else {}
                    
                    result = DrugResult(
                        drug_id=drug_id,
                        drug_name=drug_info.get('name', drug_id),
                        drug_type=drug_info.get('type', 'unknown'),
                        target_genes=[target],
                        mechanism_of_action=self._get_mechanism_of_action(drug_id, [target]),
                        therapeutic_indication='target_based',
                        efficacy_score=self._calculate_target_based_efficacy(target, genomic_data),
                        safety_score=self._calculate_safety_score(drug_id, drug_info),
                        repurposing_potential=0.0,
                        clinical_evidence=self._get_clinical_evidence(drug_id),
                        supporting_literature=self._get_supporting_literature(drug_id),
                        metadata={'analysis_type': 'target_identification', 'target': target}
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                self.logger.warning(f"Error in target identification for {target}: {e}")
                continue
        
        return results
    
    def _identify_drug_targets(self, genomic_data: pd.DataFrame) -> Dict[str, List[str]]:
        """Identify potential drug targets from genomic data."""
        targets = {}
        
        # Use gene expression and mutation data to identify targets
        for gene in genomic_data.columns:
            if self._is_druggable_target(gene, genomic_data[gene]):
                # Find drugs that target this gene
                drugs = self._find_drugs_for_target(gene)
                for drug in drugs:
                    if drug not in targets:
                        targets[drug] = []
                    targets[drug].append(gene)
        
        return targets
    
    def _is_druggable_target(self, gene: str, expression_data: pd.Series) -> bool:
        """Check if a gene is a druggable target."""
        # Simple heuristics for druggability
        # In practice, this would use more sophisticated methods
        
        # Check if gene is overexpressed or mutated
        is_overexpressed = expression_data.mean() > expression_data.quantile(0.8)
        has_mutations = (expression_data == 0).sum() > len(expression_data) * 0.1
        
        # Check if gene is in druggable gene families
        druggable_families = [
            'kinase', 'receptor', 'enzyme', 'transporter', 'ion_channel',
            'GPCR', 'nuclear_receptor', 'protease', 'phosphatase'
        ]
        
        is_druggable_family = any(family in gene.lower() for family in druggable_families)
        
        return (is_overexpressed or has_mutations) and is_druggable_family
    
    def _find_drugs_for_target(self, target: str) -> List[str]:
        """Find drugs that target a specific gene/protein."""
        # This would typically query drug databases
        # For now, return mock data
        mock_drugs = {
            'EGFR': ['erlotinib', 'gefitinib', 'afatinib'],
            'BRAF': ['vemurafenib', 'dabrafenib'],
            'PIK3CA': ['alpelisib', 'copanlisib'],
            'KRAS': ['sotorasib', 'adagrasib'],
            'TP53': ['nutlin-3', 'PRIMA-1']
        }
        
        return mock_drugs.get(target, [])
    
    def _calculate_efficacy_score(self, 
                                drug_id: str, 
                                drug_info: pd.Series, 
                                genomic_data: pd.DataFrame,
                                drug_targets: Dict[str, List[str]]) -> float:
        """Calculate drug efficacy score."""
        try:
            # Get drug targets
            targets = drug_targets.get(drug_id, [])
            
            if not targets:
                return 0.0
            
            # Calculate target-based efficacy
            target_scores = []
            for target in targets:
                if target in genomic_data.columns:
                    # Higher expression/mutation = higher efficacy potential
                    target_data = genomic_data[target]
                    score = target_data.mean() / target_data.std() if target_data.std() > 0 else 0.0
                    target_scores.append(min(score, 1.0))
            
            # Combine target scores
            efficacy_score = np.mean(target_scores) if target_scores else 0.0
            
            # Adjust based on drug properties
            if 'IC50' in drug_info:
                ic50 = drug_info['IC50']
                if ic50 < 1.0:  # Low IC50 = high potency
                    efficacy_score *= 1.2
            
            return min(efficacy_score, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error calculating efficacy score for {drug_id}: {e}")
            return 0.0
    
    def _calculate_safety_score(self, drug_id: str, drug_info: pd.Series) -> float:
        """Calculate drug safety score."""
        try:
            # Start with base safety score
            safety_score = 0.8
            
            # Adjust based on known safety issues
            if 'toxicity' in drug_info:
                toxicity = drug_info['toxicity']
                if toxicity == 'high':
                    safety_score *= 0.6
                elif toxicity == 'moderate':
                    safety_score *= 0.8
            
            # Adjust based on drug class
            if 'class' in drug_info:
                drug_class = drug_info['class']
                if drug_class in ['chemotherapy', 'alkylating_agent']:
                    safety_score *= 0.7
                elif drug_class in ['targeted_therapy', 'immunotherapy']:
                    safety_score *= 1.1
            
            return min(safety_score, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error calculating safety score for {drug_id}: {e}")
            return 0.5
    
    def _calculate_repurposing_potential(self, 
                                       drug_id: str, 
                                       drug_info: pd.Series, 
                                       genomic_data: pd.DataFrame) -> float:
        """Calculate drug repurposing potential."""
        try:
            # Check if drug has existing cancer indication
            has_cancer_indication = self._check_cancer_indication(drug_id)
            
            if has_cancer_indication:
                return 0.0  # Already indicated for cancer
            
            # Calculate based on target overlap with cancer pathways
            targets = self._get_drug_targets(drug_id)
            cancer_pathway_overlap = 0.0
            
            for target in targets:
                if target in genomic_data.columns:
                    # Check if target is dysregulated in cancer
                    target_data = genomic_data[target]
                    is_dysregulated = (
                        target_data.mean() > target_data.quantile(0.9) or
                        target_data.mean() < target_data.quantile(0.1)
                    )
                    if is_dysregulated:
                        cancer_pathway_overlap += 1.0
            
            repurposing_potential = cancer_pathway_overlap / len(targets) if targets else 0.0
            
            return min(repurposing_potential, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error calculating repurposing potential for {drug_id}: {e}")
            return 0.0
    
    def _calculate_repurposing_score(self, 
                                   drug_id: str, 
                                   drug_info: pd.Series, 
                                   genomic_data: pd.DataFrame) -> float:
        """Calculate detailed repurposing score."""
        # Similar to repurposing potential but more detailed
        return self._calculate_repurposing_potential(drug_id, drug_info, genomic_data)
    
    def _check_cancer_indication(self, drug_id: str) -> bool:
        """Check if drug has existing cancer indication."""
        # Mock implementation - would query drug databases
        cancer_drugs = [
            'erlotinib', 'gefitinib', 'afatinib', 'vemurafenib', 'dabrafenib',
            'alpelisib', 'copanlisib', 'sotorasib', 'adagrasib', 'pembrolizumab',
            'nivolumab', 'atezolizumab', 'doxorubicin', 'cisplatin', 'paclitaxel'
        ]
        
        return drug_id.lower() in cancer_drugs
    
    def _get_drug_targets(self, drug_id: str) -> List[str]:
        """Get targets for a specific drug."""
        # Mock implementation - would query drug databases
        drug_targets = {
            'erlotinib': ['EGFR'],
            'gefitinib': ['EGFR'],
            'vemurafenib': ['BRAF'],
            'dabrafenib': ['BRAF'],
            'alpelisib': ['PIK3CA'],
            'sotorasib': ['KRAS'],
            'pembrolizumab': ['PD1', 'PDL1'],
            'nivolumab': ['PD1', 'PDL1']
        }
        
        return drug_targets.get(drug_id, [])
    
    def _get_mechanism_of_action(self, drug_id: str, targets: Optional[List[str]] = None) -> str:
        """Get mechanism of action for a drug."""
        if targets is None:
            targets = self._get_drug_targets(drug_id)
        
        # Mock implementation
        mechanisms = {
            'EGFR': 'EGFR tyrosine kinase inhibitor',
            'BRAF': 'BRAF kinase inhibitor',
            'PIK3CA': 'PI3K inhibitor',
            'KRAS': 'KRAS G12C inhibitor',
            'PD1': 'PD-1 immune checkpoint inhibitor',
            'PDL1': 'PD-L1 immune checkpoint inhibitor'
        }
        
        if targets:
            return mechanisms.get(targets[0], f'Targets {", ".join(targets)}')
        else:
            return 'Unknown mechanism'
    
    def _get_clinical_evidence(self, drug_id: str) -> List[str]:
        """Get clinical evidence for a drug."""
        # Mock implementation - would query clinical trial databases
        evidence = {
            'erlotinib': ['Phase III trial in NSCLC', 'FDA approved for NSCLC'],
            'vemurafenib': ['Phase III trial in melanoma', 'FDA approved for melanoma'],
            'pembrolizumab': ['Multiple Phase III trials', 'FDA approved for multiple cancers']
        }
        
        return evidence.get(drug_id, ['Limited clinical evidence'])
    
    def _get_supporting_literature(self, drug_id: str) -> List[str]:
        """Get supporting literature for a drug."""
        # Mock implementation - would query literature databases
        literature = {
            'erlotinib': ['PMID:12345678', 'PMID:87654321'],
            'vemurafenib': ['PMID:11223344', 'PMID:44332211'],
            'pembrolizumab': ['PMID:55667788', 'PMID:99887766']
        }
        
        return literature.get(drug_id, [])
    
    def _identify_potential_targets(self, genomic_data: pd.DataFrame) -> List[str]:
        """Identify potential drug targets from genomic data."""
        potential_targets = []
        
        for gene in genomic_data.columns:
            if self._is_druggable_target(gene, genomic_data[gene]):
                potential_targets.append(gene)
        
        return potential_targets
    
    def _calculate_target_based_efficacy(self, target: str, genomic_data: pd.DataFrame) -> float:
        """Calculate efficacy based on target characteristics."""
        if target not in genomic_data.columns:
            return 0.0
        
        target_data = genomic_data[target]
        
        # Higher expression/mutation = higher efficacy potential
        efficacy = target_data.mean() / target_data.std() if target_data.std() > 0 else 0.0
        
        return min(efficacy, 1.0)
    
    def get_top_drugs(self, n: int = 10, criteria: str = 'combined') -> List[DrugResult]:
        """Get top N drugs by specified criteria."""
        if not self.results:
            return []
        
        if criteria == 'combined':
            # Sort by combined score
            sorted_results = sorted(
                self.results, 
                key=lambda x: (x.efficacy_score + x.safety_score + x.repurposing_potential) / 3,
                reverse=True
            )
        elif criteria == 'efficacy':
            sorted_results = sorted(self.results, key=lambda x: x.efficacy_score, reverse=True)
        elif criteria == 'safety':
            sorted_results = sorted(self.results, key=lambda x: x.safety_score, reverse=True)
        elif criteria == 'repurposing':
            sorted_results = sorted(self.results, key=lambda x: x.repurposing_potential, reverse=True)
        else:
            sorted_results = self.results
        
        return sorted_results[:n]
    
    def export_results(self, filepath: str, format: str = 'csv') -> None:
        """Export drug analysis results to file."""
        if not self.results:
            self.logger.warning("No results to export")
            return
        
        # Convert results to DataFrame
        results_data = []
        for result in self.results:
            row = {
                'drug_id': result.drug_id,
                'drug_name': result.drug_name,
                'drug_type': result.drug_type,
                'target_genes': '; '.join(result.target_genes),
                'mechanism_of_action': result.mechanism_of_action,
                'therapeutic_indication': result.therapeutic_indication,
                'efficacy_score': result.efficacy_score,
                'safety_score': result.safety_score,
                'repurposing_potential': result.repurposing_potential,
                'clinical_evidence': '; '.join(result.clinical_evidence),
                'supporting_literature': '; '.join(result.supporting_literature)
            }
            row.update(result.metadata)
            results_data.append(row)
        
        df = pd.DataFrame(results_data)
        
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False)
        elif format.lower() == 'excel':
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Results exported to {filepath}")


class DrugTargetIdentifier:
    """Specialized class for drug target identification."""
    
    def __init__(self, config: Optional[DrugDiscoveryConfig] = None):
        self.config = config or DrugDiscoveryConfig()
        self.logger = logging.getLogger(__name__)
    
    def identify_targets(self, 
                        genomic_data: pd.DataFrame,
                        expression_data: Optional[pd.DataFrame] = None,
                        mutation_data: Optional[pd.DataFrame] = None) -> List[DrugTarget]:
        """Identify potential drug targets from genomic data."""
        targets = []
        
        # Analyze gene expression
        if expression_data is not None:
            expression_targets = self._analyze_expression_targets(expression_data)
            targets.extend(expression_targets)
        
        # Analyze mutations
        if mutation_data is not None:
            mutation_targets = self._analyze_mutation_targets(mutation_data)
            targets.extend(mutation_targets)
        
        # Analyze genomic features
        genomic_targets = self._analyze_genomic_targets(genomic_data)
        targets.extend(genomic_targets)
        
        # Remove duplicates and rank by druggability
        unique_targets = self._deduplicate_targets(targets)
        ranked_targets = self._rank_targets_by_druggability(unique_targets)
        
        return ranked_targets
    
    def _analyze_expression_targets(self, expression_data: pd.DataFrame) -> List[DrugTarget]:
        """Analyze gene expression data for drug targets."""
        targets = []
        
        for gene in expression_data.columns:
            gene_data = expression_data[gene]
            
            # Check for overexpression
            if gene_data.mean() > gene_data.quantile(0.9):
                target = DrugTarget(
                    target_id=gene,
                    target_name=gene,
                    target_type='gene_expression',
                    gene_symbol=gene,
                    protein_name=gene,
                    pathway='unknown',
                    druggability_score=self._calculate_druggability_score(gene),
                    expression_level=gene_data.mean(),
                    mutation_frequency=0.0,
                    clinical_relevance='high' if gene_data.mean() > gene_data.quantile(0.95) else 'moderate',
                    metadata={'analysis_type': 'expression', 'percentile': 90}
                )
                targets.append(target)
        
        return targets
    
    def _analyze_mutation_targets(self, mutation_data: pd.DataFrame) -> List[DrugTarget]:
        """Analyze mutation data for drug targets."""
        targets = []
        
        for gene in mutation_data.columns:
            gene_data = mutation_data[gene]
            
            # Check for high mutation frequency
            mutation_frequency = (gene_data != 0).sum() / len(gene_data)
            
            if mutation_frequency > 0.1:  # 10% mutation frequency threshold
                target = DrugTarget(
                    target_id=gene,
                    target_name=gene,
                    target_type='mutation',
                    gene_symbol=gene,
                    protein_name=gene,
                    pathway='unknown',
                    druggability_score=self._calculate_druggability_score(gene),
                    expression_level=0.0,
                    mutation_frequency=mutation_frequency,
                    clinical_relevance='high' if mutation_frequency > 0.2 else 'moderate',
                    metadata={'analysis_type': 'mutation', 'frequency': mutation_frequency}
                )
                targets.append(target)
        
        return targets
    
    def _analyze_genomic_targets(self, genomic_data: pd.DataFrame) -> List[DrugTarget]:
        """Analyze general genomic data for drug targets."""
        targets = []
        
        for feature in genomic_data.columns:
            feature_data = genomic_data[feature]
            
            # Check for significant variation
            if feature_data.std() > feature_data.mean() * 0.5:
                target = DrugTarget(
                    target_id=feature,
                    target_name=feature,
                    target_type='genomic_feature',
                    gene_symbol=feature,
                    protein_name=feature,
                    pathway='unknown',
                    druggability_score=self._calculate_druggability_score(feature),
                    expression_level=feature_data.mean(),
                    mutation_frequency=0.0,
                    clinical_relevance='moderate',
                    metadata={'analysis_type': 'genomic', 'variation': feature_data.std()}
                )
                targets.append(target)
        
        return targets
    
    def _calculate_druggability_score(self, gene: str) -> float:
        """Calculate druggability score for a gene."""
        # Simple heuristics for druggability
        druggable_families = {
            'kinase': 0.9,
            'receptor': 0.8,
            'enzyme': 0.7,
            'transporter': 0.6,
            'ion_channel': 0.8,
            'GPCR': 0.9,
            'nuclear_receptor': 0.8,
            'protease': 0.7,
            'phosphatase': 0.6
        }
        
        gene_lower = gene.lower()
        for family, score in druggable_families.items():
            if family in gene_lower:
                return score
        
        # Default score for unknown families
        return 0.3
    
    def _deduplicate_targets(self, targets: List[DrugTarget]) -> List[DrugTarget]:
        """Remove duplicate targets."""
        seen = set()
        unique_targets = []
        
        for target in targets:
            if target.target_id not in seen:
                seen.add(target.target_id)
                unique_targets.append(target)
        
        return unique_targets
    
    def _rank_targets_by_druggability(self, targets: List[DrugTarget]) -> List[DrugTarget]:
        """Rank targets by druggability score."""
        return sorted(targets, key=lambda x: x.druggability_score, reverse=True)


class DrugRepurposingAnalyzer:
    """Specialized class for drug repurposing analysis."""
    
    def __init__(self, config: Optional[DrugDiscoveryConfig] = None):
        self.config = config or DrugDiscoveryConfig()
        self.logger = logging.getLogger(__name__)
    
    def analyze_repurposing(self, 
                          drug_data: pd.DataFrame,
                          genomic_data: pd.DataFrame,
                          disease_data: Optional[pd.DataFrame] = None) -> List[DrugResult]:
        """Analyze drugs for repurposing potential."""
        repurposing_candidates = []
        
        for drug_id in drug_data.index:
            try:
                drug_info = drug_data.loc[drug_id]
                
                # Check if drug is already indicated for cancer
                if self._is_cancer_drug(drug_id):
                    continue
                
                # Calculate repurposing score
                repurposing_score = self._calculate_repurposing_score(
                    drug_id, drug_info, genomic_data, disease_data
                )
                
                if repurposing_score > self.config.repurposing_threshold:
                    result = DrugResult(
                        drug_id=drug_id,
                        drug_name=drug_info.get('name', drug_id),
                        drug_type=drug_info.get('type', 'unknown'),
                        target_genes=self._get_drug_targets(drug_id),
                        mechanism_of_action=self._get_mechanism_of_action(drug_id),
                        therapeutic_indication='cancer_repurposing',
                        efficacy_score=repurposing_score,
                        safety_score=self._calculate_safety_score(drug_id, drug_info),
                        repurposing_potential=repurposing_score,
                        clinical_evidence=self._get_clinical_evidence(drug_id),
                        supporting_literature=self._get_supporting_literature(drug_id),
                        metadata={'analysis_type': 'repurposing'}
                    )
                    
                    repurposing_candidates.append(result)
                    
            except Exception as e:
                self.logger.warning(f"Error in repurposing analysis for {drug_id}: {e}")
                continue
        
        return sorted(repurposing_candidates, key=lambda x: x.repurposing_potential, reverse=True)
    
    def _is_cancer_drug(self, drug_id: str) -> bool:
        """Check if drug is already indicated for cancer."""
        cancer_drugs = [
            'erlotinib', 'gefitinib', 'afatinib', 'vemurafenib', 'dabrafenib',
            'alpelisib', 'copanlisib', 'sotorasib', 'adagrasib', 'pembrolizumab',
            'nivolumab', 'atezolizumab', 'doxorubicin', 'cisplatin', 'paclitaxel'
        ]
        
        return drug_id.lower() in cancer_drugs
    
    def _calculate_repurposing_score(self, 
                                   drug_id: str, 
                                   drug_info: pd.Series, 
                                   genomic_data: pd.DataFrame,
                                   disease_data: Optional[pd.DataFrame] = None) -> float:
        """Calculate detailed repurposing score."""
        # Get drug targets
        targets = self._get_drug_targets(drug_id)
        
        if not targets:
            return 0.0
        
        # Calculate target-cancer pathway overlap
        pathway_overlap = 0.0
        for target in targets:
            if target in genomic_data.columns:
                target_data = genomic_data[target]
                
                # Check if target is dysregulated in cancer
                is_dysregulated = (
                    target_data.mean() > target_data.quantile(0.9) or
                    target_data.mean() < target_data.quantile(0.1)
                )
                
                if is_dysregulated:
                    pathway_overlap += 1.0
        
        # Normalize by number of targets
        repurposing_score = pathway_overlap / len(targets) if targets else 0.0
        
        # Adjust based on drug safety profile
        safety_score = self._calculate_safety_score(drug_id, drug_info)
        repurposing_score *= safety_score
        
        return min(repurposing_score, 1.0)
    
    def _get_drug_targets(self, drug_id: str) -> List[str]:
        """Get targets for a specific drug."""
        # Mock implementation
        drug_targets = {
            'metformin': ['AMPK', 'mTOR'],
            'aspirin': ['COX1', 'COX2'],
            'statins': ['HMGCR'],
            'metoprolol': ['ADRB1'],
            'lisinopril': ['ACE']
        }
        
        return drug_targets.get(drug_id, [])
    
    def _get_mechanism_of_action(self, drug_id: str) -> str:
        """Get mechanism of action for a drug."""
        mechanisms = {
            'metformin': 'AMPK activator, mTOR inhibitor',
            'aspirin': 'COX inhibitor',
            'statins': 'HMG-CoA reductase inhibitor',
            'metoprolol': 'Beta-1 adrenergic receptor blocker',
            'lisinopril': 'ACE inhibitor'
        }
        
        return mechanisms.get(drug_id, 'Unknown mechanism')
    
    def _calculate_safety_score(self, drug_id: str, drug_info: pd.Series) -> float:
        """Calculate safety score for repurposing."""
        # Start with base safety score
        safety_score = 0.8
        
        # Adjust based on known safety issues
        if 'toxicity' in drug_info:
            toxicity = drug_info['toxicity']
            if toxicity == 'high':
                safety_score *= 0.6
            elif toxicity == 'moderate':
                safety_score *= 0.8
        
        return min(safety_score, 1.0)
    
    def _get_clinical_evidence(self, drug_id: str) -> List[str]:
        """Get clinical evidence for repurposing."""
        # Mock implementation
        evidence = {
            'metformin': ['Preclinical studies show anti-cancer effects', 'Epidemiological studies suggest reduced cancer risk'],
            'aspirin': ['Clinical trials show reduced cancer incidence', 'FDA approved for cardiovascular prevention']
        }
        
        return evidence.get(drug_id, ['Limited clinical evidence for cancer indication'])
    
    def _get_supporting_literature(self, drug_id: str) -> List[str]:
        """Get supporting literature for repurposing."""
        # Mock implementation
        literature = {
            'metformin': ['PMID:11111111', 'PMID:22222222'],
            'aspirin': ['PMID:33333333', 'PMID:44444444']
        }
        
        return literature.get(drug_id, [])


class DrugMechanismAnalyzer:
    """Specialized class for drug mechanism analysis."""
    
    def __init__(self, config: Optional[DrugDiscoveryConfig] = None):
        self.config = config or DrugDiscoveryConfig()
        self.logger = logging.getLogger(__name__)
    
    def analyze_mechanism(self, 
                         drug_id: str,
                         target_data: pd.DataFrame,
                         pathway_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Analyze drug mechanism of action."""
        mechanism_analysis = {
            'drug_id': drug_id,
            'primary_targets': [],
            'secondary_targets': [],
            'pathways_affected': [],
            'mechanism_summary': '',
            'therapeutic_effects': [],
            'adverse_effects': [],
            'drug_interactions': [],
            'resistance_mechanisms': []
        }
        
        try:
            # Identify primary targets
            primary_targets = self._identify_primary_targets(drug_id, target_data)
            mechanism_analysis['primary_targets'] = primary_targets
            
            # Identify secondary targets
            secondary_targets = self._identify_secondary_targets(drug_id, target_data)
            mechanism_analysis['secondary_targets'] = secondary_targets
            
            # Analyze affected pathways
            if pathway_data is not None:
                affected_pathways = self._analyze_affected_pathways(
                    primary_targets + secondary_targets, pathway_data
                )
                mechanism_analysis['pathways_affected'] = affected_pathways
            
            # Generate mechanism summary
            mechanism_analysis['mechanism_summary'] = self._generate_mechanism_summary(
                drug_id, primary_targets, secondary_targets
            )
            
            # Identify therapeutic effects
            mechanism_analysis['therapeutic_effects'] = self._identify_therapeutic_effects(
                drug_id, primary_targets
            )
            
            # Identify adverse effects
            mechanism_analysis['adverse_effects'] = self._identify_adverse_effects(
                drug_id, primary_targets, secondary_targets
            )
            
            # Identify drug interactions
            mechanism_analysis['drug_interactions'] = self._identify_drug_interactions(drug_id)
            
            # Identify resistance mechanisms
            mechanism_analysis['resistance_mechanisms'] = self._identify_resistance_mechanisms(
                drug_id, primary_targets
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing mechanism for {drug_id}: {e}")
            mechanism_analysis['error'] = str(e)
        
        return mechanism_analysis
    
    def _identify_primary_targets(self, drug_id: str, target_data: pd.DataFrame) -> List[str]:
        """Identify primary drug targets."""
        # Mock implementation
        primary_targets = {
            'erlotinib': ['EGFR'],
            'vemurafenib': ['BRAF'],
            'pembrolizumab': ['PD1'],
            'metformin': ['AMPK']
        }
        
        return primary_targets.get(drug_id, [])
    
    def _identify_secondary_targets(self, drug_id: str, target_data: pd.DataFrame) -> List[str]:
        """Identify secondary drug targets."""
        # Mock implementation
        secondary_targets = {
            'erlotinib': ['ERBB2', 'ERBB3'],
            'vemurafenib': ['CRAF', 'ARAF'],
            'pembrolizumab': ['PDL1', 'PDL2'],
            'metformin': ['mTOR', 'SIRT1']
        }
        
        return secondary_targets.get(drug_id, [])
    
    def _analyze_affected_pathways(self, targets: List[str], pathway_data: pd.DataFrame) -> List[str]:
        """Analyze pathways affected by drug targets."""
        affected_pathways = []
        
        for target in targets:
            if target in pathway_data.columns:
                # Find pathways where this target is involved
                pathway_involvement = pathway_data[target]
                high_involvement = pathway_involvement[pathway_involvement > pathway_involvement.quantile(0.8)]
                affected_pathways.extend(high_involvement.index.tolist())
        
        return list(set(affected_pathways))  # Remove duplicates
    
    def _generate_mechanism_summary(self, 
                                  drug_id: str, 
                                  primary_targets: List[str], 
                                  secondary_targets: List[str]) -> str:
        """Generate mechanism of action summary."""
        if primary_targets:
            primary_summary = f"Primary target: {', '.join(primary_targets)}"
        else:
            primary_summary = "Primary targets: Unknown"
        
        if secondary_targets:
            secondary_summary = f"Secondary targets: {', '.join(secondary_targets)}"
        else:
            secondary_summary = "Secondary targets: None identified"
        
        return f"{primary_summary}. {secondary_summary}."
    
    def _identify_therapeutic_effects(self, drug_id: str, primary_targets: List[str]) -> List[str]:
        """Identify therapeutic effects of the drug."""
        # Mock implementation
        therapeutic_effects = {
            'erlotinib': ['Inhibition of tumor growth', 'Reduced cell proliferation'],
            'vemurafenib': ['Apoptosis induction', 'Cell cycle arrest'],
            'pembrolizumab': ['Enhanced immune response', 'Tumor regression'],
            'metformin': ['Reduced glucose levels', 'Anti-inflammatory effects']
        }
        
        return therapeutic_effects.get(drug_id, ['Therapeutic effects not well characterized'])
    
    def _identify_adverse_effects(self, 
                                drug_id: str, 
                                primary_targets: List[str], 
                                secondary_targets: List[str]) -> List[str]:
        """Identify potential adverse effects."""
        # Mock implementation
        adverse_effects = {
            'erlotinib': ['Skin rash', 'Diarrhea', 'Fatigue'],
            'vemurafenib': ['Skin toxicity', 'Photosensitivity', 'Arthralgia'],
            'pembrolizumab': ['Immune-related adverse events', 'Fatigue', 'Nausea'],
            'metformin': ['Gastrointestinal upset', 'Lactic acidosis (rare)']
        }
        
        return adverse_effects.get(drug_id, ['Adverse effects not well characterized'])
    
    def _identify_drug_interactions(self, drug_id: str) -> List[str]:
        """Identify potential drug interactions."""
        # Mock implementation
        interactions = {
            'erlotinib': ['Warfarin (increased bleeding risk)', 'CYP3A4 inhibitors'],
            'vemurafenib': ['CYP3A4 substrates', 'Warfarin'],
            'pembrolizumab': ['Immunosuppressive agents', 'Live vaccines'],
            'metformin': ['Contrast agents', 'Alcohol']
        }
        
        return interactions.get(drug_id, ['Drug interactions not well characterized'])
    
    def _identify_resistance_mechanisms(self, drug_id: str, primary_targets: List[str]) -> List[str]:
        """Identify potential resistance mechanisms."""
        # Mock implementation
        resistance_mechanisms = {
            'erlotinib': ['EGFR T790M mutation', 'MET amplification', 'PIK3CA mutation'],
            'vemurafenib': ['BRAF amplification', 'MEK mutations', 'Alternative pathway activation'],
            'pembrolizumab': ['PD-L1 loss', 'T-cell exhaustion', 'Immune escape mechanisms'],
            'metformin': ['AMPK pathway mutations', 'Glucose transporter alterations']
        }
        
        return resistance_mechanisms.get(drug_id, ['Resistance mechanisms not well characterized'])

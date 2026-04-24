"""
Comprehensive Biomarker and Drug Analysis Example

This example demonstrates the complete biomarker discovery and drug analysis
pipeline including integration and personalized medicine recommendations.
"""

import sys
import os
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.biomarker_discovery.biomarker_analyzer import (
    BiomarkerAnalyzer, StatisticalBiomarkerDiscovery, MLBiomarkerDiscovery,
    BiomarkerDiscoveryConfig
)
from modules.drug_discovery.drug_analyzer import (
    DrugAnalyzer, DrugRepurposingAnalyzer, DrugTargetIdentifier,
    DrugDiscoveryConfig
)
from modules.drug_biomarker_integration.drug_biomarker_analyzer import (
    DrugBiomarkerAnalyzer, PharmacogenomicsIntegrator, PersonalizedMedicineEngine,
    DrugBiomarkerConfig
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_data():
    """Generate mock data for demonstration."""
    logger.info("Generating mock data...")
    
    np.random.seed(42)
    n_samples = 100
    n_genes = 50
    n_drugs = 20
    
    # Generate mock gene expression data
    gene_expression = pd.DataFrame(
        np.random.randn(n_genes, n_samples),
        index=[f'Gene_{i}' for i in range(n_genes)],
        columns=[f'Sample_{i}' for i in range(n_samples)]
    )
    
    # Generate mock mutation data
    mutation_data = pd.DataFrame(
        np.random.choice([0, 1], size=(n_genes, n_samples), p=[0.9, 0.1]),
        index=[f'Gene_{i}' for i in range(n_genes)],
        columns=[f'Sample_{i}' for i in range(n_samples)]
    )
    
    # Generate mock labels (binary classification: 0 = normal, 1 = cancer)
    labels = pd.Series(
        np.random.choice([0, 1], size=n_samples, p=[0.4, 0.6]),
        index=[f'Sample_{i}' for i in range(n_samples)]
    )
    
    # Generate mock drug data
    drug_data = pd.DataFrame({
        'name': [f'Drug_{i}' for i in range(n_drugs)],
        'type': np.random.choice(['targeted', 'chemotherapy', 'immunotherapy'], n_drugs),
        'indication': np.random.choice(['cancer', 'other'], n_drugs),
        'IC50': np.random.exponential(1.0, n_drugs),
        'toxicity': np.random.choice(['low', 'moderate', 'high'], n_drugs)
    }, index=[f'Drug_{i}' for i in range(n_drugs)])
    
    # Generate mock drug response data
    drug_response = pd.DataFrame(
        np.random.rand(n_drugs, n_samples),
        index=[f'Drug_{i}' for i in range(n_drugs)],
        columns=[f'Sample_{i}' for i in range(n_samples)]
    )
    
    # Generate mock patient data
    patient_biomarkers = {
        f'Gene_{i}': np.random.rand() for i in range(10)  # Top 10 genes
    }
    
    # Generate mock genetic variants
    genetic_variants = {
        'CYP2D6': '*1',
        'CYP2C19': '*2',
        'CYP3A4': '*1',
        'EGFR': 'wild_type',
        'BRAF': 'V600E',
        'KRAS': 'G12D'
    }
    
    logger.info(f"Generated data: {n_samples} samples, {n_genes} genes, {n_drugs} drugs")
    
    return {
        'gene_expression': gene_expression,
        'mutation_data': mutation_data,
        'labels': labels,
        'drug_data': drug_data,
        'drug_response': drug_response,
        'patient_biomarkers': patient_biomarkers,
        'genetic_variants': genetic_variants
    }


def run_biomarker_discovery(data: Dict[str, Any]):
    """Run biomarker discovery analysis."""
    logger.info("Starting biomarker discovery analysis...")
    
    # Configure biomarker discovery
    config = BiomarkerDiscoveryConfig(
        p_value_threshold=0.05,
        effect_size_threshold=0.2,
        auc_threshold=0.7,
        multiple_testing_correction='fdr_bh',
        cross_validation_folds=5
    )
    
    # Run comprehensive biomarker discovery
    analyzer = BiomarkerAnalyzer(config)
    results = analyzer.discover_biomarkers(
        data['gene_expression'], 
        data['labels'],
        biomarker_type='gene_expression'
    )
    
    logger.info(f"Discovered {len(results)} biomarkers")
    
    # Get top biomarkers
    top_biomarkers = analyzer.get_top_biomarkers(10)
    logger.info("Top 10 biomarkers:")
    for i, biomarker in enumerate(top_biomarkers, 1):
        logger.info(f"{i}. {biomarker.biomarker_name}: "
                   f"p={biomarker.p_value:.2e}, "
                   f"effect_size={biomarker.effect_size:.3f}, "
                   f"AUC={biomarker.auc_score:.3f}")
    
    # Run statistical biomarker discovery
    logger.info("\nRunning statistical biomarker discovery...")
    stat_analyzer = StatisticalBiomarkerDiscovery(config)
    stat_results = stat_analyzer.discover_biomarkers(
        data['gene_expression'], 
        data['labels']
    )
    logger.info(f"Statistical analysis found {len(stat_results)} biomarkers")
    
    # Run ML biomarker discovery
    logger.info("\nRunning ML biomarker discovery...")
    ml_analyzer = MLBiomarkerDiscovery(config)
    ml_results = ml_analyzer.discover_biomarkers(
        data['gene_expression'], 
        data['labels']
    )
    logger.info(f"ML analysis found {len(ml_results)} biomarkers")
    
    return {
        'comprehensive_results': results,
        'statistical_results': stat_results,
        'ml_results': ml_results
    }


def run_drug_discovery(data: Dict[str, Any]):
    """Run drug discovery analysis."""
    logger.info("Starting drug discovery analysis...")
    
    # Configure drug discovery
    config = DrugDiscoveryConfig(
        min_efficacy_score=0.6,
        min_safety_score=0.7,
        repurposing_threshold=0.8,
        target_druggability_threshold=0.5
    )
    
    # Run comprehensive drug analysis
    analyzer = DrugAnalyzer(config)
    results = analyzer.analyze_drugs(
        data['gene_expression'], 
        data['drug_data'],
        analysis_type='comprehensive'
    )
    
    logger.info(f"Analyzed {len(results)} drugs")
    
    # Get top drugs
    top_drugs = analyzer.get_top_drugs(10)
    logger.info("Top 10 drug candidates:")
    for i, drug in enumerate(top_drugs, 1):
        logger.info(f"{i}. {drug.drug_name}: "
                   f"efficacy={drug.efficacy_score:.3f}, "
                   f"safety={drug.safety_score:.3f}, "
                   f"repurposing={drug.repurposing_potential:.3f}")
    
    # Run drug repurposing analysis
    logger.info("\nRunning drug repurposing analysis...")
    repurposing_analyzer = DrugRepurposingAnalyzer(config)
    repurposing_results = repurposing_analyzer.analyze_repurposing(
        data['drug_data'], 
        data['gene_expression']
    )
    logger.info(f"Found {len(repurposing_results)} repurposing candidates")
    
    # Run target identification
    logger.info("\nRunning target identification...")
    target_identifier = DrugTargetIdentifier(config)
    target_results = target_identifier.identify_targets(
        data['gene_expression'],
        data['gene_expression'],  # Using expression data as both genomic and expression
        data['mutation_data']
    )
    logger.info(f"Identified {len(target_results)} potential targets")
    
    return {
        'comprehensive_results': results,
        'repurposing_results': repurposing_results,
        'target_results': target_results
    }


def run_drug_biomarker_integration(data: Dict[str, Any], biomarker_results: Dict[str, Any], drug_results: Dict[str, Any]):
    """Run drug-biomarker integration analysis."""
    logger.info("Starting drug-biomarker integration analysis...")
    
    # Configure integration
    config = DrugBiomarkerConfig(
        min_interaction_strength=0.3,
        p_value_threshold=0.05,
        effect_size_threshold=0.2,
        confidence_threshold=0.7
    )
    
    # Run drug-biomarker interaction analysis
    analyzer = DrugBiomarkerAnalyzer(config)
    interactions = analyzer.analyze_drug_biomarker_interactions(
        data['drug_data'],
        data['gene_expression'],
        data['drug_response']
    )
    
    logger.info(f"Found {len(interactions)} drug-biomarker interactions")
    
    # Get top interactions
    top_interactions = analyzer.get_top_interactions(10)
    logger.info("Top 10 drug-biomarker interactions:")
    for i, interaction in enumerate(top_interactions, 1):
        logger.info(f"{i}. {interaction.drug_id}-{interaction.biomarker_id}: "
                   f"strength={interaction.interaction_strength:.3f}, "
                   f"p_value={interaction.p_value:.2e}")
    
    # Predict drug response
    logger.info("\nPredicting drug response...")
    predictions = analyzer.predict_drug_response(
        data['patient_biomarkers'],
        list(data['drug_data'].index)[:10]  # Top 10 drugs
    )
    
    logger.info("Drug response predictions:")
    for drug, score in sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"{drug}: {score:.3f}")
    
    # Create pharmacogenomics profile
    logger.info("\nCreating pharmacogenomics profile...")
    pg_integrator = PharmacogenomicsIntegrator(config)
    pg_profile = pg_integrator.create_pharmacogenomics_profile(
        'Patient_001',
        data['genetic_variants']
    )
    
    logger.info(f"Created pharmacogenomics profile for {pg_profile.patient_id}")
    logger.info(f"Drug metabolism: {pg_profile.drug_metabolism}")
    logger.info(f"Adverse reactions: {pg_profile.adverse_reactions}")
    logger.info(f"Dose adjustments: {pg_profile.dose_adjustments}")
    
    return {
        'interactions': interactions,
        'predictions': predictions,
        'pharmacogenomics_profile': pg_profile
    }


def run_personalized_medicine(data: Dict[str, Any], integration_results: Dict[str, Any]):
    """Run personalized medicine analysis."""
    logger.info("Starting personalized medicine analysis...")
    
    # Configure personalized medicine
    config = DrugBiomarkerConfig()
    
    # Generate treatment recommendations
    engine = PersonalizedMedicineEngine(config)
    recommendations = engine.generate_treatment_recommendations(
        patient_id='Patient_001',
        patient_biomarkers=data['patient_biomarkers'],
        pharmacogenomics_profile=integration_results['pharmacogenomics_profile'],
        drug_candidates=list(data['drug_data'].index)[:10]
    )
    
    logger.info(f"Generated treatment recommendations for {recommendations.patient_id}")
    logger.info(f"Recommended drugs: {recommendations.recommended_drugs}")
    logger.info(f"Drug scores: {recommendations.drug_scores}")
    logger.info(f"Confidence scores: {recommendations.confidence_scores}")
    logger.info(f"Contraindications: {recommendations.contraindications}")
    logger.info(f"Monitoring biomarkers: {recommendations.monitoring_biomarkers}")
    
    return recommendations


def export_results(biomarker_results: Dict[str, Any], drug_results: Dict[str, Any], integration_results: Dict[str, Any]):
    """Export analysis results."""
    logger.info("Exporting results...")
    
    try:
        # Export biomarker results
        biomarker_analyzer = BiomarkerAnalyzer()
        biomarker_analyzer.results = biomarker_results['comprehensive_results']
        biomarker_analyzer.export_results('biomarker_results.csv', 'csv')
        logger.info("Biomarker results exported to biomarker_results.csv")
        
        # Export drug results
        drug_analyzer = DrugAnalyzer()
        drug_analyzer.results = drug_results['comprehensive_results']
        drug_analyzer.export_results('drug_results.csv', 'csv')
        logger.info("Drug results exported to drug_results.csv")
        
        # Export integration results
        integration_analyzer = DrugBiomarkerAnalyzer()
        integration_analyzer.interactions = integration_results['interactions']
        integration_analyzer.export_interactions('drug_biomarker_interactions.csv', 'csv')
        logger.info("Integration results exported to drug_biomarker_interactions.csv")
        
    except Exception as e:
        logger.error(f"Error exporting results: {e}")


def main():
    """Main function to run the complete analysis pipeline."""
    logger.info("Starting comprehensive biomarker and drug analysis example...")
    
    try:
        # Generate mock data
        data = generate_mock_data()
        
        # Run biomarker discovery
        biomarker_results = run_biomarker_discovery(data)
        
        # Run drug discovery
        drug_results = run_drug_discovery(data)
        
        # Run drug-biomarker integration
        integration_results = run_drug_biomarker_integration(data, biomarker_results, drug_results)
        
        # Run personalized medicine
        personalized_results = run_personalized_medicine(data, integration_results)
        
        # Export results
        export_results(biomarker_results, drug_results, integration_results)
        
        logger.info("Analysis completed successfully!")
        
        # Print summary
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)
        print(f"Biomarkers discovered: {len(biomarker_results['comprehensive_results'])}")
        print(f"Drugs analyzed: {len(drug_results['comprehensive_results'])}")
        print(f"Drug-biomarker interactions: {len(integration_results['interactions'])}")
        print(f"Recommended treatments: {len(personalized_results.recommended_drugs)}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {e}")
        raise


if __name__ == "__main__":
    main()

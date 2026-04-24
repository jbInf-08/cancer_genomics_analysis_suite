"""
API Routes for Biomarker and Drug Analysis

This module provides Flask-based REST API endpoints for biomarker discovery,
drug analysis, and integration services.
"""

from flask import Flask, request, jsonify, Blueprint
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import traceback

# Import our analysis modules
from ..biomarker_discovery.biomarker_analyzer import (
    BiomarkerAnalyzer, StatisticalBiomarkerDiscovery, MLBiomarkerDiscovery,
    BiomarkerDiscoveryConfig
)
from ..drug_discovery.drug_analyzer import (
    DrugAnalyzer, DrugRepurposingAnalyzer, DrugTargetIdentifier,
    DrugDiscoveryConfig
)
from ..drug_biomarker_integration.drug_biomarker_analyzer import (
    DrugBiomarkerAnalyzer, PharmacogenomicsIntegrator, PersonalizedMedicineEngine,
    DrugBiomarkerConfig
)

logger = logging.getLogger(__name__)


def create_biomarker_api() -> Blueprint:
    """Create biomarker discovery API blueprint."""
    biomarker_bp = Blueprint('biomarker', __name__, url_prefix='/api/biomarker')
    
    @biomarker_bp.route('/discover', methods=['POST'])
    def discover_biomarkers():
        """Discover biomarkers from omics data."""
        try:
            # Parse request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            omics_data = pd.DataFrame(data.get('omics_data', {}))
            labels = pd.Series(data.get('labels', {}))
            analysis_type = data.get('analysis_type', 'comprehensive')
            config_params = data.get('config', {})
            
            # Validate data
            if omics_data.empty or labels.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = BiomarkerDiscoveryConfig(**config_params)
            
            # Initialize analyzer
            if analysis_type == 'statistical':
                analyzer = StatisticalBiomarkerDiscovery(config)
            elif analysis_type == 'ml':
                analyzer = MLBiomarkerDiscovery(config)
            else:
                analyzer = BiomarkerAnalyzer(config)
            
            # Run analysis
            results = analyzer.discover_biomarkers(omics_data, labels)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'biomarker_id': result.biomarker_id,
                    'biomarker_name': result.biomarker_name,
                    'biomarker_type': result.biomarker_type,
                    'p_value': result.p_value,
                    'effect_size': result.effect_size,
                    'sensitivity': result.sensitivity,
                    'specificity': result.specificity,
                    'auc_score': result.auc_score,
                    'clinical_significance': result.clinical_significance,
                    'validation_status': result.validation_status,
                    'supporting_evidence': result.supporting_evidence,
                    'metadata': result.metadata
                })
            
            return jsonify({
                'status': 'success',
                'results': formatted_results,
                'summary': {
                    'total_biomarkers': len(results),
                    'significant_biomarkers': len([r for r in results if r.p_value < 0.05]),
                    'high_effect_biomarkers': len([r for r in results if r.effect_size > 0.5]),
                    'high_auc_biomarkers': len([r for r in results if r.auc_score > 0.8])
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in biomarker discovery: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    
    @biomarker_bp.route('/validate', methods=['POST'])
    def validate_biomarkers():
        """Validate discovered biomarkers."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            biomarkers = data.get('biomarkers', [])
            validation_data = pd.DataFrame(data.get('validation_data', {}))
            validation_labels = pd.Series(data.get('validation_labels', {}))
            
            if not biomarkers or validation_data.empty or validation_labels.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Initialize validator
            from ..biomarker_discovery.biomarker_analyzer import BiomarkerValidator
            validator = BiomarkerValidator()
            
            # Validate each biomarker
            validation_results = []
            for biomarker_data in biomarkers:
                from ..biomarker_discovery.biomarker_analyzer import BiomarkerResult
                biomarker = BiomarkerResult(**biomarker_data)
                
                validation_result = validator.validate_biomarker(
                    biomarker, validation_data, validation_labels
                )
                validation_results.append(validation_result)
            
            return jsonify({
                'status': 'success',
                'validation_results': validation_results,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in biomarker validation: {e}")
            return jsonify({'error': str(e)}), 500
    
    @biomarker_bp.route('/export/<format>', methods=['POST'])
    def export_biomarkers(format: str):
        """Export biomarker results."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            biomarkers = data.get('biomarkers', [])
            if not biomarkers:
                return jsonify({'error': 'No biomarkers to export'}), 400
            
            # Create temporary analyzer with results
            analyzer = BiomarkerAnalyzer()
            analyzer.results = [
                BiomarkerResult(**biomarker) for biomarker in biomarkers
            ]
            
            # Export results
            filename = f'biomarker_results.{format}'
            analyzer.export_results(filename, format)
            
            return jsonify({
                'status': 'success',
                'message': f'Results exported to {filename}',
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in biomarker export: {e}")
            return jsonify({'error': str(e)}), 500
    
    return biomarker_bp


def create_drug_api() -> Blueprint:
    """Create drug discovery API blueprint."""
    drug_bp = Blueprint('drug', __name__, url_prefix='/api/drug')
    
    @drug_bp.route('/analyze', methods=['POST'])
    def analyze_drugs():
        """Analyze drugs for cancer treatment potential."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            genomic_data = pd.DataFrame(data.get('genomic_data', {}))
            drug_data = pd.DataFrame(data.get('drug_data', {}))
            analysis_type = data.get('analysis_type', 'comprehensive')
            config_params = data.get('config', {})
            
            # Validate data
            if genomic_data.empty or drug_data.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = DrugDiscoveryConfig(**config_params)
            
            # Initialize analyzer
            analyzer = DrugAnalyzer(config)
            
            # Run analysis
            results = analyzer.analyze_drugs(genomic_data, drug_data, analysis_type)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'drug_id': result.drug_id,
                    'drug_name': result.drug_name,
                    'drug_type': result.drug_type,
                    'target_genes': result.target_genes,
                    'mechanism_of_action': result.mechanism_of_action,
                    'therapeutic_indication': result.therapeutic_indication,
                    'efficacy_score': result.efficacy_score,
                    'safety_score': result.safety_score,
                    'repurposing_potential': result.repurposing_potential,
                    'clinical_evidence': result.clinical_evidence,
                    'supporting_literature': result.supporting_literature,
                    'metadata': result.metadata
                })
            
            return jsonify({
                'status': 'success',
                'results': formatted_results,
                'summary': {
                    'total_drugs': len(results),
                    'high_efficacy_drugs': len([r for r in results if r.efficacy_score > 0.8]),
                    'high_safety_drugs': len([r for r in results if r.safety_score > 0.8]),
                    'repurposing_candidates': len([r for r in results if r.repurposing_potential > 0.8])
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in drug analysis: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    
    @drug_bp.route('/repurpose', methods=['POST'])
    def repurpose_drugs():
        """Analyze drugs for repurposing potential."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            drug_data = pd.DataFrame(data.get('drug_data', {}))
            genomic_data = pd.DataFrame(data.get('genomic_data', {}))
            disease_data = pd.DataFrame(data.get('disease_data', {})) if data.get('disease_data') else None
            config_params = data.get('config', {})
            
            # Validate data
            if drug_data.empty or genomic_data.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = DrugDiscoveryConfig(**config_params)
            
            # Initialize repurposing analyzer
            analyzer = DrugRepurposingAnalyzer(config)
            
            # Run repurposing analysis
            results = analyzer.analyze_repurposing(drug_data, genomic_data, disease_data)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'drug_id': result.drug_id,
                    'drug_name': result.drug_name,
                    'drug_type': result.drug_type,
                    'target_genes': result.target_genes,
                    'mechanism_of_action': result.mechanism_of_action,
                    'therapeutic_indication': result.therapeutic_indication,
                    'efficacy_score': result.efficacy_score,
                    'safety_score': result.safety_score,
                    'repurposing_potential': result.repurposing_potential,
                    'clinical_evidence': result.clinical_evidence,
                    'supporting_literature': result.supporting_literature,
                    'metadata': result.metadata
                })
            
            return jsonify({
                'status': 'success',
                'results': formatted_results,
                'summary': {
                    'total_candidates': len(results),
                    'high_potential_candidates': len([r for r in results if r.repurposing_potential > 0.8])
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in drug repurposing: {e}")
            return jsonify({'error': str(e)}), 500
    
    @drug_bp.route('/targets', methods=['POST'])
    def identify_targets():
        """Identify potential drug targets."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            genomic_data = pd.DataFrame(data.get('genomic_data', {}))
            expression_data = pd.DataFrame(data.get('expression_data', {})) if data.get('expression_data') else None
            mutation_data = pd.DataFrame(data.get('mutation_data', {})) if data.get('mutation_data') else None
            config_params = data.get('config', {})
            
            # Validate data
            if genomic_data.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = DrugDiscoveryConfig(**config_params)
            
            # Initialize target identifier
            identifier = DrugTargetIdentifier(config)
            
            # Run target identification
            results = identifier.identify_targets(genomic_data, expression_data, mutation_data)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'target_id': result.target_id,
                    'target_name': result.target_name,
                    'target_type': result.target_type,
                    'gene_symbol': result.gene_symbol,
                    'protein_name': result.protein_name,
                    'pathway': result.pathway,
                    'druggability_score': result.druggability_score,
                    'expression_level': result.expression_level,
                    'mutation_frequency': result.mutation_frequency,
                    'clinical_relevance': result.clinical_relevance,
                    'metadata': result.metadata
                })
            
            return jsonify({
                'status': 'success',
                'results': formatted_results,
                'summary': {
                    'total_targets': len(results),
                    'high_druggability_targets': len([r for r in results if r.druggability_score > 0.7])
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in target identification: {e}")
            return jsonify({'error': str(e)}), 500
    
    @drug_bp.route('/export/<format>', methods=['POST'])
    def export_drugs(format: str):
        """Export drug analysis results."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            drugs = data.get('drugs', [])
            if not drugs:
                return jsonify({'error': 'No drugs to export'}), 400
            
            # Create temporary analyzer with results
            analyzer = DrugAnalyzer()
            analyzer.results = [
                DrugResult(**drug) for drug in drugs
            ]
            
            # Export results
            filename = f'drug_results.{format}'
            analyzer.export_results(filename, format)
            
            return jsonify({
                'status': 'success',
                'message': f'Results exported to {filename}',
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in drug export: {e}")
            return jsonify({'error': str(e)}), 500
    
    return drug_bp


def create_integration_api() -> Blueprint:
    """Create drug-biomarker integration API blueprint."""
    integration_bp = Blueprint('integration', __name__, url_prefix='/api/integration')
    
    @integration_bp.route('/analyze', methods=['POST'])
    def analyze_integration():
        """Analyze drug-biomarker interactions."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            drug_data = pd.DataFrame(data.get('drug_data', {}))
            biomarker_data = pd.DataFrame(data.get('biomarker_data', {}))
            response_data = pd.DataFrame(data.get('response_data', {}))
            config_params = data.get('config', {})
            
            # Validate data
            if drug_data.empty or biomarker_data.empty or response_data.empty:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = DrugBiomarkerConfig(**config_params)
            
            # Initialize analyzer
            analyzer = DrugBiomarkerAnalyzer(config)
            
            # Run analysis
            results = analyzer.analyze_drug_biomarker_interactions(
                drug_data, biomarker_data, response_data
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'drug_id': result.drug_id,
                    'biomarker_id': result.biomarker_id,
                    'interaction_type': result.interaction_type,
                    'interaction_strength': result.interaction_strength,
                    'p_value': result.p_value,
                    'effect_size': result.effect_size,
                    'clinical_significance': result.clinical_significance,
                    'mechanism': result.mechanism,
                    'supporting_evidence': result.supporting_evidence,
                    'metadata': result.metadata
                })
            
            return jsonify({
                'status': 'success',
                'results': formatted_results,
                'summary': {
                    'total_interactions': len(results),
                    'significant_interactions': len([r for r in results if r.p_value < 0.05]),
                    'high_strength_interactions': len([r for r in results if r.interaction_strength > 0.7])
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in integration analysis: {e}")
            return jsonify({'error': str(e)}), 500
    
    @integration_bp.route('/predict', methods=['POST'])
    def predict_response():
        """Predict drug response based on biomarkers."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            patient_biomarkers = data.get('patient_biomarkers', {})
            drug_candidates = data.get('drug_candidates', [])
            interactions = data.get('interactions', [])
            
            # Validate data
            if not patient_biomarkers or not drug_candidates:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Initialize analyzer
            analyzer = DrugBiomarkerAnalyzer()
            analyzer.interactions = [
                DrugBiomarkerInteraction(**interaction) for interaction in interactions
            ]
            
            # Predict response
            predictions = analyzer.predict_drug_response(
                patient_biomarkers, drug_candidates
            )
            
            return jsonify({
                'status': 'success',
                'predictions': predictions,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in response prediction: {e}")
            return jsonify({'error': str(e)}), 500
    
    @integration_bp.route('/pharmacogenomics', methods=['POST'])
    def create_pharmacogenomics_profile():
        """Create pharmacogenomics profile."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            patient_id = data.get('patient_id')
            genetic_variants = data.get('genetic_variants', {})
            
            # Validate data
            if not patient_id or not genetic_variants:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Initialize integrator
            integrator = PharmacogenomicsIntegrator()
            
            # Create profile
            profile = integrator.create_pharmacogenomics_profile(patient_id, genetic_variants)
            
            # Format result
            formatted_profile = {
                'patient_id': profile.patient_id,
                'genetic_variants': profile.genetic_variants,
                'drug_metabolism': profile.drug_metabolism,
                'drug_transport': profile.drug_transport,
                'drug_targets': profile.drug_targets,
                'adverse_reactions': profile.adverse_reactions,
                'dose_adjustments': profile.dose_adjustments,
                'metadata': profile.metadata
            }
            
            return jsonify({
                'status': 'success',
                'profile': formatted_profile,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in pharmacogenomics profile creation: {e}")
            return jsonify({'error': str(e)}), 500
    
    return integration_bp


def create_clinical_api() -> Blueprint:
    """Create clinical decision support API blueprint."""
    clinical_bp = Blueprint('clinical', __name__, url_prefix='/api/clinical')
    
    @clinical_bp.route('/recommendations', methods=['POST'])
    def generate_recommendations():
        """Generate personalized treatment recommendations."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            patient_id = data.get('patient_id')
            patient_biomarkers = data.get('patient_biomarkers', {})
            pharmacogenomics_profile = data.get('pharmacogenomics_profile')
            drug_candidates = data.get('drug_candidates', [])
            config_params = data.get('config', {})
            
            # Validate data
            if not patient_id or not patient_biomarkers or not drug_candidates:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Create configuration
            config = DrugBiomarkerConfig(**config_params)
            
            # Initialize personalized medicine engine
            engine = PersonalizedMedicineEngine(config)
            
            # Convert pharmacogenomics profile if provided
            pg_profile = None
            if pharmacogenomics_profile:
                from ..drug_biomarker_integration.drug_biomarker_analyzer import PharmacogenomicsProfile
                pg_profile = PharmacogenomicsProfile(**pharmacogenomics_profile)
            
            # Generate recommendations
            recommendations = engine.generate_treatment_recommendations(
                patient_id, patient_biomarkers, pg_profile, drug_candidates
            )
            
            # Format result
            formatted_recommendations = {
                'patient_id': recommendations.patient_id,
                'recommended_drugs': recommendations.recommended_drugs,
                'biomarker_profile': recommendations.biomarker_profile,
                'drug_scores': recommendations.drug_scores,
                'confidence_scores': recommendations.confidence_scores,
                'contraindications': recommendations.contraindications,
                'monitoring_biomarkers': recommendations.monitoring_biomarkers,
                'treatment_plan': recommendations.treatment_plan,
                'metadata': recommendations.metadata
            }
            
            return jsonify({
                'status': 'success',
                'recommendations': formatted_recommendations,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in treatment recommendations: {e}")
            return jsonify({'error': str(e)}), 500
    
    @clinical_bp.route('/risk-assessment', methods=['POST'])
    def assess_risk():
        """Assess treatment risk for a patient."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Extract parameters
            patient_id = data.get('patient_id')
            patient_biomarkers = data.get('patient_biomarkers', {})
            proposed_treatment = data.get('proposed_treatment', {})
            pharmacogenomics_profile = data.get('pharmacogenomics_profile')
            
            # Validate data
            if not patient_id or not patient_biomarkers or not proposed_treatment:
                return jsonify({'error': 'Invalid data format'}), 400
            
            # Mock risk assessment (in practice, this would use more sophisticated models)
            risk_factors = []
            risk_score = 0.0
            
            # Check biomarker-based risk factors
            if 'liver_function' in patient_biomarkers and patient_biomarkers['liver_function'] < 0.3:
                risk_factors.append('Severe liver dysfunction')
                risk_score += 0.3
            
            if 'kidney_function' in patient_biomarkers and patient_biomarkers['kidney_function'] < 0.3:
                risk_factors.append('Severe kidney dysfunction')
                risk_score += 0.3
            
            # Check pharmacogenomics risk factors
            if pharmacogenomics_profile and pharmacogenomics_profile.get('adverse_reactions'):
                risk_factors.extend(pharmacogenomics_profile['adverse_reactions'])
                risk_score += 0.2
            
            # Determine risk level
            if risk_score > 0.7:
                risk_level = 'high'
            elif risk_score > 0.4:
                risk_level = 'moderate'
            else:
                risk_level = 'low'
            
            return jsonify({
                'status': 'success',
                'risk_assessment': {
                    'patient_id': patient_id,
                    'risk_level': risk_level,
                    'risk_score': risk_score,
                    'risk_factors': risk_factors,
                    'recommendations': self._generate_risk_recommendations(risk_level, risk_factors)
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """Generate risk-based recommendations."""
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append('Consider alternative treatment options')
            recommendations.append('Implement enhanced monitoring protocols')
            recommendations.append('Consult with specialist before proceeding')
        elif risk_level == 'moderate':
            recommendations.append('Proceed with caution and close monitoring')
            recommendations.append('Consider dose adjustments')
        else:
            recommendations.append('Standard treatment protocol appropriate')
        
        if 'liver dysfunction' in ' '.join(risk_factors):
            recommendations.append('Monitor liver function closely')
        
        if 'kidney dysfunction' in ' '.join(risk_factors):
            recommendations.append('Monitor kidney function closely')
        
        return recommendations
    
    return clinical_bp


def register_all_apis(app: Flask):
    """Register all API blueprints with the Flask app."""
    app.register_blueprint(create_biomarker_api())
    app.register_blueprint(create_drug_api())
    app.register_blueprint(create_integration_api())
    app.register_blueprint(create_clinical_api())
    
    # Add health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': ['biomarker', 'drug', 'integration', 'clinical']
        })
    
    logger.info("All biomarker and drug analysis APIs registered successfully")

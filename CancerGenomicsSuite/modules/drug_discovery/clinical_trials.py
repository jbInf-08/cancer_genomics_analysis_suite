"""
Clinical Trial Integration and Analysis for Cancer Genomics

This module provides comprehensive clinical trial matching, analysis, and integration
capabilities for drug discovery and personalized medicine.
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
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.linear_model import LogisticRegression, ElasticNet
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb
import lightgbm as lgb

# Network Analysis
import networkx as nx
from networkx.algorithms import centrality, community

logger = logging.getLogger(__name__)


@dataclass
class ClinicalTrial:
    """Data class for clinical trial information."""
    trial_id: str
    title: str
    phase: str
    status: str
    condition: str
    intervention: str
    eligibility_criteria: Dict[str, Any]
    primary_endpoints: List[str]
    secondary_endpoints: List[str]
    locations: List[str]
    sponsor: str
    start_date: str
    completion_date: str
    enrollment: int
    study_type: str
    allocation: str
    masking: str
    primary_purpose: str
    official_title: str
    brief_summary: str
    detailed_description: str
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    outcome_measures: List[Dict[str, Any]]
    contacts: List[Dict[str, str]]
    metadata: Dict[str, Any]


@dataclass
class TrialMatch:
    """Data class for clinical trial matching results."""
    patient_id: str
    trial_id: str
    match_score: float
    eligibility_status: str
    matching_criteria: List[str]
    exclusion_reasons: List[str]
    enrollment_probability: float
    travel_requirements: List[str]
    time_commitment: str
    potential_benefits: List[str]
    potential_risks: List[str]
    metadata: Dict[str, Any]


@dataclass
class DrugResponsePrediction:
    """Data class for drug response predictions."""
    patient_id: str
    drug_id: str
    predicted_response: str
    response_probability: float
    confidence_score: float
    key_biomarkers: List[str]
    biomarker_values: Dict[str, float]
    predicted_side_effects: List[str]
    dose_recommendation: str
    monitoring_requirements: List[str]
    alternative_treatments: List[str]
    metadata: Dict[str, Any]


@dataclass
class ClinicalTrialConfig:
    """Configuration for clinical trial analysis."""
    min_match_score: float = 0.7
    max_travel_distance: float = 100.0  # miles
    min_enrollment_probability: float = 0.5
    include_phase_1: bool = True
    include_phase_2: bool = True
    include_phase_3: bool = True
    include_phase_4: bool = False
    max_trials_per_patient: int = 10
    response_prediction_threshold: float = 0.6


class ClinicalTrialMatcher:
    """Clinical trial matching system."""
    
    def __init__(self, config: Optional[ClinicalTrialConfig] = None):
        """Initialize the clinical trial matcher."""
        self.config = config or ClinicalTrialConfig()
        self.trial_database = {}
        self.logger = logging.getLogger(__name__)
        
        # Mock clinical trial database (in practice, this would connect to real databases)
        self._initialize_mock_trials()
    
    def _initialize_mock_trials(self):
        """Initialize mock clinical trial database."""
        mock_trials = [
            {
                'trial_id': 'NCT00123456',
                'title': 'Phase II Study of Drug A in Advanced Cancer',
                'phase': 'Phase 2',
                'status': 'Recruiting',
                'condition': 'Advanced Solid Tumors',
                'intervention': 'Drug A',
                'eligibility_criteria': {
                    'age_min': 18,
                    'age_max': 75,
                    'ecog_performance_status': [0, 1],
                    'life_expectancy': '>3 months',
                    'organ_function': 'adequate'
                },
                'primary_endpoints': ['Overall Response Rate', 'Progression-Free Survival'],
                'secondary_endpoints': ['Overall Survival', 'Safety Profile'],
                'locations': ['New York, NY', 'Los Angeles, CA', 'Chicago, IL'],
                'sponsor': 'Pharmaceutical Company A',
                'start_date': '2023-01-01',
                'completion_date': '2025-12-31',
                'enrollment': 150,
                'study_type': 'Interventional',
                'allocation': 'Randomized',
                'masking': 'Double',
                'primary_purpose': 'Treatment',
                'official_title': 'A Phase II, Randomized, Double-Blind Study of Drug A vs Placebo in Advanced Solid Tumors',
                'brief_summary': 'This study evaluates the efficacy and safety of Drug A in patients with advanced solid tumors.',
                'detailed_description': 'Detailed description of the study protocol and procedures.',
                'inclusion_criteria': [
                    'Age 18-75 years',
                    'Histologically confirmed advanced solid tumor',
                    'ECOG performance status 0-1',
                    'Adequate organ function',
                    'Life expectancy >3 months'
                ],
                'exclusion_criteria': [
                    'Prior treatment with Drug A',
                    'Active brain metastases',
                    'Pregnancy or breastfeeding',
                    'Severe cardiac disease'
                ],
                'outcome_measures': [
                    {'measure': 'Overall Response Rate', 'time_frame': '12 months'},
                    {'measure': 'Progression-Free Survival', 'time_frame': '24 months'}
                ],
                'contacts': [
                    {'name': 'Dr. John Smith', 'email': 'john.smith@hospital.com', 'phone': '555-1234'}
                ]
            },
            {
                'trial_id': 'NCT00234567',
                'title': 'Phase III Study of Drug B in Lung Cancer',
                'phase': 'Phase 3',
                'status': 'Recruiting',
                'condition': 'Non-Small Cell Lung Cancer',
                'intervention': 'Drug B',
                'eligibility_criteria': {
                    'age_min': 18,
                    'age_max': 80,
                    'ecog_performance_status': [0, 1, 2],
                    'life_expectancy': '>6 months',
                    'organ_function': 'adequate',
                    'specific_mutations': ['EGFR', 'KRAS']
                },
                'primary_endpoints': ['Overall Survival'],
                'secondary_endpoints': ['Progression-Free Survival', 'Quality of Life'],
                'locations': ['Boston, MA', 'Houston, TX', 'Seattle, WA'],
                'sponsor': 'Pharmaceutical Company B',
                'start_date': '2023-06-01',
                'completion_date': '2026-06-30',
                'enrollment': 500,
                'study_type': 'Interventional',
                'allocation': 'Randomized',
                'masking': 'Open Label',
                'primary_purpose': 'Treatment',
                'official_title': 'A Phase III, Randomized, Open-Label Study of Drug B vs Standard Care in NSCLC',
                'brief_summary': 'This study compares Drug B with standard care in patients with NSCLC.',
                'detailed_description': 'Detailed description of the study protocol.',
                'inclusion_criteria': [
                    'Age 18-80 years',
                    'Histologically confirmed NSCLC',
                    'ECOG performance status 0-2',
                    'EGFR or KRAS mutation',
                    'Life expectancy >6 months'
                ],
                'exclusion_criteria': [
                    'Prior treatment with Drug B',
                    'Active brain metastases',
                    'Severe liver disease'
                ],
                'outcome_measures': [
                    {'measure': 'Overall Survival', 'time_frame': '36 months'}
                ],
                'contacts': [
                    {'name': 'Dr. Jane Doe', 'email': 'jane.doe@hospital.com', 'phone': '555-5678'}
                ]
            }
        ]
        
        for trial_data in mock_trials:
            trial = ClinicalTrial(**trial_data, metadata={})
            self.trial_database[trial.trial_id] = trial
    
    def match_patient_to_trials(self, 
                               patient_profile: Dict[str, Any],
                               patient_location: Optional[str] = None) -> List[TrialMatch]:
        """
        Match a patient to relevant clinical trials.
        
        Args:
            patient_profile: Patient's clinical and genomic profile
            patient_location: Patient's location (optional)
            
        Returns:
            List of trial matches sorted by match score
        """
        self.logger.info(f"Matching patient {patient_profile.get('patient_id', 'Unknown')} to clinical trials")
        
        matches = []
        
        for trial_id, trial in self.trial_database.items():
            try:
                match_score = self._calculate_match_score(patient_profile, trial)
                
                if match_score >= self.config.min_match_score:
                    eligibility_status, matching_criteria, exclusion_reasons = self._assess_eligibility(
                        patient_profile, trial
                    )
                    
                    enrollment_probability = self._calculate_enrollment_probability(
                        patient_profile, trial, match_score
                    )
                    
                    if enrollment_probability >= self.config.min_enrollment_probability:
                        travel_requirements = self._assess_travel_requirements(
                            patient_location, trial.locations
                        )
                        
                        time_commitment = self._estimate_time_commitment(trial)
                        potential_benefits = self._assess_potential_benefits(patient_profile, trial)
                        potential_risks = self._assess_potential_risks(patient_profile, trial)
                        
                        match = TrialMatch(
                            patient_id=patient_profile.get('patient_id', 'Unknown'),
                            trial_id=trial_id,
                            match_score=match_score,
                            eligibility_status=eligibility_status,
                            matching_criteria=matching_criteria,
                            exclusion_reasons=exclusion_reasons,
                            enrollment_probability=enrollment_probability,
                            travel_requirements=travel_requirements,
                            time_commitment=time_commitment,
                            potential_benefits=potential_benefits,
                            potential_risks=potential_risks,
                            metadata={
                                'trial_phase': trial.phase,
                                'trial_status': trial.status,
                                'sponsor': trial.sponsor
                            }
                        )
                        
                        matches.append(match)
                        
            except Exception as e:
                self.logger.warning(f"Error matching patient to trial {trial_id}: {e}")
                continue
        
        # Sort by match score and return top matches
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:self.config.max_trials_per_patient]
    
    def _calculate_match_score(self, 
                             patient_profile: Dict[str, Any], 
                             trial: ClinicalTrial) -> float:
        """Calculate match score between patient and trial."""
        score = 0.0
        total_weight = 0.0
        
        # Age matching
        patient_age = patient_profile.get('age', 50)
        age_min = trial.eligibility_criteria.get('age_min', 18)
        age_max = trial.eligibility_criteria.get('age_max', 80)
        
        if age_min <= patient_age <= age_max:
            score += 0.2
        total_weight += 0.2
        
        # Condition matching
        patient_condition = patient_profile.get('condition', '').lower()
        trial_condition = trial.condition.lower()
        
        if patient_condition in trial_condition or trial_condition in patient_condition:
            score += 0.3
        total_weight += 0.3
        
        # Performance status matching
        patient_ecog = patient_profile.get('ecog_performance_status', 1)
        trial_ecog = trial.eligibility_criteria.get('ecog_performance_status', [0, 1, 2])
        
        if patient_ecog in trial_ecog:
            score += 0.2
        total_weight += 0.2
        
        # Genomic matching
        patient_mutations = patient_profile.get('mutations', [])
        trial_mutations = trial.eligibility_criteria.get('specific_mutations', [])
        
        if trial_mutations:
            mutation_overlap = len(set(patient_mutations) & set(trial_mutations))
            if mutation_overlap > 0:
                score += 0.2 * (mutation_overlap / len(trial_mutations))
        else:
            score += 0.1  # No specific mutation requirements
        total_weight += 0.2
        
        # Prior treatment matching
        patient_prior_treatments = patient_profile.get('prior_treatments', [])
        trial_intervention = trial.intervention.lower()
        
        if trial_intervention not in [t.lower() for t in patient_prior_treatments]:
            score += 0.1
        total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _assess_eligibility(self, 
                          patient_profile: Dict[str, Any], 
                          trial: ClinicalTrial) -> Tuple[str, List[str], List[str]]:
        """Assess patient eligibility for a trial."""
        matching_criteria = []
        exclusion_reasons = []
        
        # Check age
        patient_age = patient_profile.get('age', 50)
        age_min = trial.eligibility_criteria.get('age_min', 18)
        age_max = trial.eligibility_criteria.get('age_max', 80)
        
        if age_min <= patient_age <= age_max:
            matching_criteria.append(f"Age {patient_age} within range {age_min}-{age_max}")
        else:
            exclusion_reasons.append(f"Age {patient_age} outside range {age_min}-{age_max}")
        
        # Check performance status
        patient_ecog = patient_profile.get('ecog_performance_status', 1)
        trial_ecog = trial.eligibility_criteria.get('ecog_performance_status', [0, 1, 2])
        
        if patient_ecog in trial_ecog:
            matching_criteria.append(f"ECOG performance status {patient_ecog} acceptable")
        else:
            exclusion_reasons.append(f"ECOG performance status {patient_ecog} not acceptable")
        
        # Check organ function
        organ_function = patient_profile.get('organ_function', 'adequate')
        if organ_function == 'adequate':
            matching_criteria.append("Adequate organ function")
        else:
            exclusion_reasons.append(f"Inadequate organ function: {organ_function}")
        
        # Check specific mutations
        patient_mutations = patient_profile.get('mutations', [])
        trial_mutations = trial.eligibility_criteria.get('specific_mutations', [])
        
        if trial_mutations:
            mutation_overlap = set(patient_mutations) & set(trial_mutations)
            if mutation_overlap:
                matching_criteria.append(f"Required mutations present: {list(mutation_overlap)}")
            else:
                exclusion_reasons.append(f"Required mutations missing: {trial_mutations}")
        
        # Determine overall eligibility
        if len(exclusion_reasons) == 0:
            eligibility_status = 'eligible'
        elif len(exclusion_reasons) <= 2:
            eligibility_status = 'potentially_eligible'
        else:
            eligibility_status = 'not_eligible'
        
        return eligibility_status, matching_criteria, exclusion_reasons
    
    def _calculate_enrollment_probability(self, 
                                        patient_profile: Dict[str, Any], 
                                        trial: ClinicalTrial, 
                                        match_score: float) -> float:
        """Calculate probability of successful enrollment."""
        base_probability = match_score
        
        # Adjust based on trial phase
        phase_adjustments = {
            'Phase 1': 0.8,  # Lower probability for Phase 1
            'Phase 2': 0.9,
            'Phase 3': 1.0,
            'Phase 4': 1.1
        }
        
        phase_adjustment = phase_adjustments.get(trial.phase, 1.0)
        base_probability *= phase_adjustment
        
        # Adjust based on trial status
        if trial.status == 'Recruiting':
            base_probability *= 1.0
        elif trial.status == 'Active':
            base_probability *= 0.9
        else:
            base_probability *= 0.5
        
        # Adjust based on patient factors
        if patient_profile.get('willing_to_travel', True):
            base_probability *= 1.1
        
        if patient_profile.get('previous_trial_participation', False):
            base_probability *= 1.05
        
        return min(base_probability, 1.0)
    
    def _assess_travel_requirements(self, 
                                  patient_location: Optional[str], 
                                  trial_locations: List[str]) -> List[str]:
        """Assess travel requirements for trial participation."""
        if not patient_location:
            return ["Location information not available"]
        
        travel_requirements = []
        
        for location in trial_locations:
            # Mock distance calculation (in practice, would use real distance calculation)
            distance = np.random.uniform(10, 500)  # miles
            
            if distance <= 50:
                travel_requirements.append(f"{location}: Local (< 50 miles)")
            elif distance <= 100:
                travel_requirements.append(f"{location}: Regional (< 100 miles)")
            else:
                travel_requirements.append(f"{location}: Long distance ({distance:.0f} miles)")
        
        return travel_requirements
    
    def _estimate_time_commitment(self, trial: ClinicalTrial) -> str:
        """Estimate time commitment for trial participation."""
        # Mock estimation based on trial phase and duration
        if trial.phase == 'Phase 1':
            return "High (frequent visits, extensive monitoring)"
        elif trial.phase == 'Phase 2':
            return "Moderate (regular visits, standard monitoring)"
        elif trial.phase == 'Phase 3':
            return "Moderate (regular visits, long-term follow-up)"
        else:
            return "Low (minimal visits, post-marketing surveillance)"
    
    def _assess_potential_benefits(self, 
                                 patient_profile: Dict[str, Any], 
                                 trial: ClinicalTrial) -> List[str]:
        """Assess potential benefits of trial participation."""
        benefits = [
            "Access to investigational treatment",
            "Close medical monitoring",
            "Contribution to medical research",
            "Potential for improved outcomes"
        ]
        
        # Add specific benefits based on trial
        if trial.phase in ['Phase 2', 'Phase 3']:
            benefits.append("Potential for significant clinical benefit")
        
        if trial.allocation == 'Randomized':
            benefits.append("Equal chance of receiving active treatment")
        
        return benefits
    
    def _assess_potential_risks(self, 
                              patient_profile: Dict[str, Any], 
                              trial: ClinicalTrial) -> List[str]:
        """Assess potential risks of trial participation."""
        risks = [
            "Unknown side effects",
            "Time commitment",
            "Travel requirements",
            "Potential for placebo assignment"
        ]
        
        # Add specific risks based on trial phase
        if trial.phase == 'Phase 1':
            risks.append("Higher risk of unknown side effects")
        
        if trial.masking == 'Double':
            risks.append("Uncertainty about treatment received")
        
        return risks


class TrialAnalyzer:
    """Clinical trial analysis and statistics."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_trial_landscape(self, 
                              condition: str,
                              phase: Optional[str] = None) -> Dict[str, Any]:
        """Analyze the clinical trial landscape for a condition."""
        self.logger.info(f"Analyzing trial landscape for {condition}")
        
        # Mock analysis (in practice, would query real trial databases)
        analysis = {
            'condition': condition,
            'total_trials': np.random.randint(50, 200),
            'active_trials': np.random.randint(20, 80),
            'recruiting_trials': np.random.randint(10, 40),
            'phase_distribution': {
                'Phase 1': np.random.randint(10, 30),
                'Phase 2': np.random.randint(15, 40),
                'Phase 3': np.random.randint(5, 20),
                'Phase 4': np.random.randint(2, 10)
            },
            'intervention_types': {
                'Drug': np.random.randint(30, 80),
                'Biological': np.random.randint(10, 30),
                'Device': np.random.randint(5, 15),
                'Behavioral': np.random.randint(2, 10)
            },
            'geographic_distribution': {
                'North America': np.random.randint(20, 60),
                'Europe': np.random.randint(15, 40),
                'Asia': np.random.randint(10, 30),
                'Other': np.random.randint(5, 20)
            },
            'enrollment_trends': {
                'increasing': np.random.randint(10, 30),
                'stable': np.random.randint(20, 50),
                'decreasing': np.random.randint(5, 15)
            }
        }
        
        return analysis
    
    def predict_trial_success(self, 
                            trial: ClinicalTrial,
                            historical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Predict the likelihood of trial success."""
        self.logger.info(f"Predicting success for trial {trial.trial_id}")
        
        # Mock prediction (in practice, would use ML models trained on historical data)
        success_probability = np.random.uniform(0.3, 0.8)
        
        # Adjust based on trial characteristics
        if trial.phase == 'Phase 1':
            success_probability *= 0.7
        elif trial.phase == 'Phase 2':
            success_probability *= 0.8
        elif trial.phase == 'Phase 3':
            success_probability *= 0.9
        
        if trial.allocation == 'Randomized':
            success_probability *= 1.1
        
        if trial.masking == 'Double':
            success_probability *= 1.05
        
        prediction = {
            'trial_id': trial.trial_id,
            'success_probability': min(success_probability, 1.0),
            'confidence_level': 'moderate',
            'key_factors': [
                'Trial phase',
                'Study design',
                'Patient population',
                'Primary endpoint'
            ],
            'risk_factors': [
                'Sample size',
                'Enrollment challenges',
                'Regulatory requirements'
            ]
        }
        
        return prediction


class DrugTrialIntegrator:
    """Integration between drug analysis and clinical trials."""
    
    def __init__(self, config: Optional[ClinicalTrialConfig] = None):
        self.config = config or ClinicalTrialConfig()
        self.trial_matcher = ClinicalTrialMatcher(config)
        self.trial_analyzer = TrialAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    def integrate_drug_trial_analysis(self, 
                                    drug_results: List[Any],
                                    patient_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate drug analysis with clinical trial matching."""
        self.logger.info("Integrating drug analysis with clinical trial matching")
        
        # Get clinical trial matches
        trial_matches = self.trial_matcher.match_patient_to_trials(patient_profile)
        
        # Analyze trial landscape
        patient_condition = patient_profile.get('condition', 'cancer')
        trial_landscape = self.trial_analyzer.analyze_trial_landscape(patient_condition)
        
        # Integrate with drug results
        integrated_results = {
            'patient_id': patient_profile.get('patient_id', 'Unknown'),
            'drug_analysis': {
                'total_drugs_analyzed': len(drug_results),
                'top_drugs': drug_results[:5] if drug_results else []
            },
            'clinical_trials': {
                'total_matches': len(trial_matches),
                'top_matches': trial_matches[:3] if trial_matches else [],
                'landscape_analysis': trial_landscape
            },
            'recommendations': self._generate_integrated_recommendations(
                drug_results, trial_matches
            ),
            'next_steps': self._generate_next_steps(drug_results, trial_matches)
        }
        
        return integrated_results
    
    def _generate_integrated_recommendations(self, 
                                           drug_results: List[Any], 
                                           trial_matches: List[TrialMatch]) -> List[str]:
        """Generate integrated recommendations based on drug and trial analysis."""
        recommendations = []
        
        if drug_results:
            recommendations.append("Consider approved drugs with high efficacy scores")
        
        if trial_matches:
            recommendations.append("Explore clinical trial participation for investigational treatments")
        
        if drug_results and trial_matches:
            recommendations.append("Compare approved vs investigational treatment options")
        
        recommendations.extend([
            "Discuss treatment options with oncologist",
            "Consider second opinion from specialist",
            "Evaluate quality of life considerations"
        ])
        
        return recommendations
    
    def _generate_next_steps(self, 
                           drug_results: List[Any], 
                           trial_matches: List[TrialMatch]) -> List[str]:
        """Generate next steps for patient care."""
        next_steps = []
        
        if drug_results:
            next_steps.append("Schedule consultation with oncologist")
            next_steps.append("Review drug options and side effects")
        
        if trial_matches:
            next_steps.append("Contact trial coordinators for eligible trials")
            next_steps.append("Complete trial screening process")
        
        next_steps.extend([
            "Obtain comprehensive genomic profiling",
            "Consider biomarker testing",
            "Evaluate treatment goals and preferences"
        ])
        
        return next_steps

"""
External Drug Database Integration

This module provides integration with external drug databases including DrugBank,
ChEMBL, and PubChem for comprehensive drug information retrieval and analysis.
"""

import requests
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class DrugInfo:
    """Data class for drug information."""
    drug_id: str
    name: str
    synonyms: List[str]
    drug_type: str
    mechanism_of_action: str
    targets: List[str]
    indications: List[str]
    contraindications: List[str]
    side_effects: List[str]
    interactions: List[str]
    pharmacokinetics: Dict[str, Any]
    pharmacodynamics: Dict[str, Any]
    chemical_properties: Dict[str, Any]
    clinical_data: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class ChemicalStructure:
    """Data class for chemical structure information."""
    compound_id: str
    smiles: str
    inchi: str
    molecular_formula: str
    molecular_weight: float
    logp: float
    hbd: int  # Hydrogen bond donors
    hba: int  # Hydrogen bond acceptors
    tpsa: float  # Topological polar surface area
    rotatable_bonds: int
    aromatic_rings: int
    heavy_atoms: int
    metadata: Dict[str, Any]


class DrugBankClient:
    """Client for DrugBank database integration."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://go.drugbank.com"):
        """Initialize DrugBank client."""
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
    
    def search_drug(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for drugs in DrugBank."""
        self.logger.info(f"Searching DrugBank for: {query}")
        
        try:
            # Mock implementation - in practice would use real DrugBank API
            mock_results = [
                {
                    'drug_id': 'DB00001',
                    'name': 'Lepirudin',
                    'drug_type': 'Biotech',
                    'mechanism_of_action': 'Direct thrombin inhibitor',
                    'targets': ['F2'],
                    'indications': ['Heparin-induced thrombocytopenia'],
                    'synonyms': ['Hirudin', 'Recombinant hirudin']
                },
                {
                    'drug_id': 'DB00002', 
                    'name': 'Cetuximab',
                    'drug_type': 'Biotech',
                    'mechanism_of_action': 'EGFR inhibitor',
                    'targets': ['EGFR'],
                    'indications': ['Colorectal cancer', 'Head and neck cancer'],
                    'synonyms': ['Erbitux', 'IMC-C225']
                }
            ]
            
            # Filter results based on query
            filtered_results = [
                result for result in mock_results 
                if query.lower() in result['name'].lower() or 
                   any(query.lower() in syn.lower() for syn in result.get('synonyms', []))
            ]
            
            return filtered_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Error searching DrugBank: {e}")
            return []
    
    def get_drug_info(self, drug_id: str) -> Optional[DrugInfo]:
        """Get detailed drug information from DrugBank."""
        self.logger.info(f"Getting DrugBank info for drug: {drug_id}")
        
        try:
            # Mock implementation - in practice would use real DrugBank API
            mock_drug_info = {
                'drug_id': drug_id,
                'name': 'Mock Drug',
                'synonyms': ['Synonym 1', 'Synonym 2'],
                'drug_type': 'Small molecule',
                'mechanism_of_action': 'Inhibits target protein',
                'targets': ['TARGET1', 'TARGET2'],
                'indications': ['Cancer', 'Inflammation'],
                'contraindications': ['Pregnancy', 'Liver disease'],
                'side_effects': ['Nausea', 'Fatigue', 'Rash'],
                'interactions': ['Drug A', 'Drug B'],
                'pharmacokinetics': {
                    'half_life': '2-4 hours',
                    'clearance': 'Hepatic',
                    'bioavailability': '80%'
                },
                'pharmacodynamics': {
                    'ic50': '1.5 μM',
                    'ki': '0.8 μM'
                },
                'chemical_properties': {
                    'molecular_weight': 350.4,
                    'logp': 2.1,
                    'solubility': 'Soluble in water'
                },
                'clinical_data': {
                    'phase': 'Approved',
                    'fda_approval_date': '2020-01-01',
                    'clinical_trials': 15
                },
                'metadata': {
                    'source': 'DrugBank',
                    'last_updated': '2024-01-01'
                }
            }
            
            return DrugInfo(**mock_drug_info)
            
        except Exception as e:
            self.logger.error(f"Error getting DrugBank info for {drug_id}: {e}")
            return None
    
    def get_drug_targets(self, drug_id: str) -> List[Dict[str, Any]]:
        """Get drug targets from DrugBank."""
        self.logger.info(f"Getting targets for drug: {drug_id}")
        
        try:
            # Mock implementation
            mock_targets = [
                {
                    'target_id': 'TARGET1',
                    'target_name': 'Target Protein 1',
                    'target_type': 'Protein',
                    'uniprot_id': 'P12345',
                    'gene_symbol': 'TARGET1',
                    'action': 'Inhibitor',
                    'ki': '0.8 μM',
                    'ic50': '1.5 μM'
                },
                {
                    'target_id': 'TARGET2',
                    'target_name': 'Target Protein 2', 
                    'target_type': 'Protein',
                    'uniprot_id': 'P67890',
                    'gene_symbol': 'TARGET2',
                    'action': 'Agonist',
                    'ec50': '2.3 μM'
                }
            ]
            
            return mock_targets
            
        except Exception as e:
            self.logger.error(f"Error getting targets for {drug_id}: {e}")
            return []
    
    def get_drug_interactions(self, drug_id: str) -> List[Dict[str, Any]]:
        """Get drug interactions from DrugBank."""
        self.logger.info(f"Getting interactions for drug: {drug_id}")
        
        try:
            # Mock implementation
            mock_interactions = [
                {
                    'interacting_drug_id': 'DB00003',
                    'interacting_drug_name': 'Interacting Drug',
                    'interaction_type': 'Major',
                    'description': 'Increases risk of bleeding',
                    'severity': 'High',
                    'clinical_significance': 'Contraindicated'
                },
                {
                    'interacting_drug_id': 'DB00004',
                    'interacting_drug_name': 'Another Drug',
                    'interaction_type': 'Moderate',
                    'description': 'May increase drug levels',
                    'severity': 'Medium',
                    'clinical_significance': 'Monitor closely'
                }
            ]
            
            return mock_interactions
            
        except Exception as e:
            self.logger.error(f"Error getting interactions for {drug_id}: {e}")
            return []


class ChEMBLClient:
    """Client for ChEMBL database integration."""
    
    def __init__(self, base_url: str = "https://www.ebi.ac.uk/chembl/api/data"):
        """Initialize ChEMBL client."""
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
    
    def search_compounds(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for compounds in ChEMBL."""
        self.logger.info(f"Searching ChEMBL for: {query}")
        
        try:
            # Mock implementation - in practice would use real ChEMBL API
            mock_results = [
                {
                    'chembl_id': 'CHEMBL123',
                    'pref_name': 'Compound A',
                    'molecule_type': 'Small molecule',
                    'max_phase': 4,
                    'first_approval': 2015,
                    'indication_class': 'Anticancer',
                    'molecular_weight': 350.4,
                    'logp': 2.1,
                    'smiles': 'CC(C)NC1=CC=C(C=C1)C(=O)O'
                },
                {
                    'chembl_id': 'CHEMBL456',
                    'pref_name': 'Compound B',
                    'molecule_type': 'Small molecule',
                    'max_phase': 3,
                    'first_approval': None,
                    'indication_class': 'Anticancer',
                    'molecular_weight': 425.6,
                    'logp': 3.2,
                    'smiles': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C'
                }
            ]
            
            # Filter results based on query
            filtered_results = [
                result for result in mock_results 
                if query.lower() in result['pref_name'].lower()
            ]
            
            return filtered_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Error searching ChEMBL: {e}")
            return []
    
    def get_compound_info(self, chembl_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed compound information from ChEMBL."""
        self.logger.info(f"Getting ChEMBL info for compound: {chembl_id}")
        
        try:
            # Mock implementation
            mock_compound_info = {
                'chembl_id': chembl_id,
                'pref_name': 'Mock Compound',
                'molecule_type': 'Small molecule',
                'max_phase': 4,
                'first_approval': 2020,
                'indication_class': 'Anticancer',
                'molecular_weight': 350.4,
                'logp': 2.1,
                'smiles': 'CC(C)NC1=CC=C(C=C1)C(=O)O',
                'inchi': 'InChI=1S/C10H13NO2/c1-7(2)11-9-5-3-8(4-6-9)10(12)13/h3-7,11H,1-2H3',
                'molecular_formula': 'C10H13NO2',
                'hbd': 2,
                'hba': 3,
                'tpsa': 49.33,
                'rotatable_bonds': 3,
                'aromatic_rings': 1,
                'heavy_atoms': 13,
                'bioactivity_data': {
                    'total_activities': 150,
                    'targets': 25,
                    'assays': 100
                },
                'clinical_data': {
                    'indications': ['Cancer', 'Inflammation'],
                    'mechanism_of_action': 'Inhibits target protein',
                    'adverse_effects': ['Nausea', 'Fatigue']
                }
            }
            
            return mock_compound_info
            
        except Exception as e:
            self.logger.error(f"Error getting ChEMBL info for {chembl_id}: {e}")
            return None
    
    def get_bioactivity_data(self, chembl_id: str) -> List[Dict[str, Any]]:
        """Get bioactivity data for a compound from ChEMBL."""
        self.logger.info(f"Getting bioactivity data for compound: {chembl_id}")
        
        try:
            # Mock implementation
            mock_bioactivity = [
                {
                    'assay_id': 'ASSAY001',
                    'target_id': 'TARGET1',
                    'target_name': 'Target Protein 1',
                    'activity_type': 'IC50',
                    'activity_value': 1.5,
                    'activity_unit': 'uM',
                    'activity_relation': '=',
                    'confidence_score': 9,
                    'assay_type': 'B',
                    'assay_description': 'Inhibition of target protein'
                },
                {
                    'assay_id': 'ASSAY002',
                    'target_id': 'TARGET2',
                    'target_name': 'Target Protein 2',
                    'activity_type': 'Ki',
                    'activity_value': 0.8,
                    'activity_unit': 'uM',
                    'activity_relation': '=',
                    'confidence_score': 8,
                    'assay_type': 'B',
                    'assay_description': 'Binding to target protein'
                }
            ]
            
            return mock_bioactivity
            
        except Exception as e:
            self.logger.error(f"Error getting bioactivity data for {chembl_id}: {e}")
            return []
    
    def get_mechanism_of_action(self, chembl_id: str) -> List[Dict[str, Any]]:
        """Get mechanism of action data from ChEMBL."""
        self.logger.info(f"Getting mechanism of action for compound: {chembl_id}")
        
        try:
            # Mock implementation
            mock_mechanisms = [
                {
                    'target_id': 'TARGET1',
                    'target_name': 'Target Protein 1',
                    'mechanism_type': 'Inhibitor',
                    'mechanism_description': 'Competitive inhibitor of target protein',
                    'evidence_type': 'Direct',
                    'evidence_description': 'Crystal structure shows binding to active site'
                }
            ]
            
            return mock_mechanisms
            
        except Exception as e:
            self.logger.error(f"Error getting mechanism of action for {chembl_id}: {e}")
            return []


class PubChemClient:
    """Client for PubChem database integration."""
    
    def __init__(self, base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"):
        """Initialize PubChem client."""
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
    
    def search_compounds(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for compounds in PubChem."""
        self.logger.info(f"Searching PubChem for: {query}")
        
        try:
            # Mock implementation - in practice would use real PubChem API
            mock_results = [
                {
                    'cid': 12345,
                    'name': 'Compound A',
                    'molecular_formula': 'C10H13NO2',
                    'molecular_weight': 179.22,
                    'smiles': 'CC(C)NC1=CC=C(C=C1)C(=O)O',
                    'inchi': 'InChI=1S/C10H13NO2/c1-7(2)11-9-5-3-8(4-6-9)10(12)13/h3-7,11H,1-2H3',
                    'synonyms': ['Synonym 1', 'Synonym 2']
                },
                {
                    'cid': 67890,
                    'name': 'Compound B',
                    'molecular_formula': 'C8H10N4O2',
                    'molecular_weight': 194.19,
                    'smiles': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
                    'inchi': 'InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3',
                    'synonyms': ['Caffeine', '1,3,7-Trimethylxanthine']
                }
            ]
            
            # Filter results based on query
            filtered_results = [
                result for result in mock_results 
                if query.lower() in result['name'].lower() or 
                   any(query.lower() in syn.lower() for syn in result.get('synonyms', []))
            ]
            
            return filtered_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Error searching PubChem: {e}")
            return []
    
    def get_compound_properties(self, cid: int) -> Optional[ChemicalStructure]:
        """Get compound properties from PubChem."""
        self.logger.info(f"Getting PubChem properties for CID: {cid}")
        
        try:
            # Mock implementation
            mock_properties = {
                'compound_id': str(cid),
                'smiles': 'CC(C)NC1=CC=C(C=C1)C(=O)O',
                'inchi': 'InChI=1S/C10H13NO2/c1-7(2)11-9-5-3-8(4-6-9)10(12)13/h3-7,11H,1-2H3',
                'molecular_formula': 'C10H13NO2',
                'molecular_weight': 179.22,
                'logp': 2.1,
                'hbd': 2,
                'hba': 3,
                'tpsa': 49.33,
                'rotatable_bonds': 3,
                'aromatic_rings': 1,
                'heavy_atoms': 13,
                'metadata': {
                    'source': 'PubChem',
                    'last_updated': '2024-01-01'
                }
            }
            
            return ChemicalStructure(**mock_properties)
            
        except Exception as e:
            self.logger.error(f"Error getting PubChem properties for {cid}: {e}")
            return None
    
    def get_compound_synonyms(self, cid: int) -> List[str]:
        """Get compound synonyms from PubChem."""
        self.logger.info(f"Getting synonyms for CID: {cid}")
        
        try:
            # Mock implementation
            mock_synonyms = [
                'Compound A',
                'Synonym 1',
                'Synonym 2',
                'Chemical Name',
                'Trade Name'
            ]
            
            return mock_synonyms
            
        except Exception as e:
            self.logger.error(f"Error getting synonyms for {cid}: {e}")
            return []
    
    def get_compound_activities(self, cid: int) -> List[Dict[str, Any]]:
        """Get compound bioactivities from PubChem."""
        self.logger.info(f"Getting bioactivities for CID: {cid}")
        
        try:
            # Mock implementation
            mock_activities = [
                {
                    'assay_id': 'AID001',
                    'assay_name': 'Inhibition of target protein',
                    'activity_type': 'IC50',
                    'activity_value': 1.5,
                    'activity_unit': 'uM',
                    'target_name': 'Target Protein 1',
                    'organism': 'Human',
                    'assay_description': 'In vitro inhibition assay'
                },
                {
                    'assay_id': 'AID002',
                    'assay_name': 'Binding to target protein',
                    'activity_type': 'Ki',
                    'activity_value': 0.8,
                    'activity_unit': 'uM',
                    'target_name': 'Target Protein 2',
                    'organism': 'Human',
                    'assay_description': 'In vitro binding assay'
                }
            ]
            
            return mock_activities
            
        except Exception as e:
            self.logger.error(f"Error getting bioactivities for {cid}: {e}")
            return []


class DrugDatabaseIntegrator:
    """Integrator for multiple drug databases."""
    
    def __init__(self, 
                 drugbank_client: Optional[DrugBankClient] = None,
                 chembl_client: Optional[ChEMBLClient] = None,
                 pubchem_client: Optional[PubChemClient] = None):
        """Initialize drug database integrator."""
        self.drugbank_client = drugbank_client or DrugBankClient()
        self.chembl_client = chembl_client or ChEMBLClient()
        self.pubchem_client = pubchem_client or PubChemClient()
        self.logger = logging.getLogger(__name__)
    
    def search_all_databases(self, query: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search all drug databases for a query."""
        self.logger.info(f"Searching all databases for: {query}")
        
        results = {}
        
        # Search DrugBank
        try:
            drugbank_results = self.drugbank_client.search_drug(query, limit)
            results['drugbank'] = drugbank_results
        except Exception as e:
            self.logger.warning(f"Error searching DrugBank: {e}")
            results['drugbank'] = []
        
        # Search ChEMBL
        try:
            chembl_results = self.chembl_client.search_compounds(query, limit)
            results['chembl'] = chembl_results
        except Exception as e:
            self.logger.warning(f"Error searching ChEMBL: {e}")
            results['chembl'] = []
        
        # Search PubChem
        try:
            pubchem_results = self.pubchem_client.search_compounds(query, limit)
            results['pubchem'] = pubchem_results
        except Exception as e:
            self.logger.warning(f"Error searching PubChem: {e}")
            results['pubchem'] = []
        
        return results
    
    def get_comprehensive_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """Get comprehensive drug information from all databases."""
        self.logger.info(f"Getting comprehensive info for: {drug_name}")
        
        comprehensive_info = {
            'drug_name': drug_name,
            'drugbank_info': None,
            'chembl_info': None,
            'pubchem_info': None,
            'integrated_info': {}
        }
        
        # Get DrugBank info
        try:
            drugbank_results = self.drugbank_client.search_drug(drug_name, 1)
            if drugbank_results:
                drug_id = drugbank_results[0]['drug_id']
                comprehensive_info['drugbank_info'] = self.drugbank_client.get_drug_info(drug_id)
        except Exception as e:
            self.logger.warning(f"Error getting DrugBank info: {e}")
        
        # Get ChEMBL info
        try:
            chembl_results = self.chembl_client.search_compounds(drug_name, 1)
            if chembl_results:
                chembl_id = chembl_results[0]['chembl_id']
                comprehensive_info['chembl_info'] = self.chembl_client.get_compound_info(chembl_id)
        except Exception as e:
            self.logger.warning(f"Error getting ChEMBL info: {e}")
        
        # Get PubChem info
        try:
            pubchem_results = self.pubchem_client.search_compounds(drug_name, 1)
            if pubchem_results:
                cid = pubchem_results[0]['cid']
                comprehensive_info['pubchem_info'] = self.pubchem_client.get_compound_properties(cid)
        except Exception as e:
            self.logger.warning(f"Error getting PubChem info: {e}")
        
        # Integrate information
        comprehensive_info['integrated_info'] = self._integrate_drug_info(comprehensive_info)
        
        return comprehensive_info
    
    def _integrate_drug_info(self, drug_info: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate drug information from multiple databases."""
        integrated = {
            'name': drug_info['drug_name'],
            'synonyms': [],
            'mechanism_of_action': '',
            'targets': [],
            'indications': [],
            'side_effects': [],
            'interactions': [],
            'chemical_properties': {},
            'clinical_data': {},
            'bioactivity_data': []
        }
        
        # Integrate from DrugBank
        if drug_info['drugbank_info']:
            db_info = drug_info['drugbank_info']
            integrated['synonyms'].extend(db_info.synonyms)
            integrated['mechanism_of_action'] = db_info.mechanism_of_action
            integrated['targets'].extend(db_info.targets)
            integrated['indications'].extend(db_info.indications)
            integrated['side_effects'].extend(db_info.side_effects)
            integrated['interactions'].extend(db_info.interactions)
            integrated['chemical_properties'].update(db_info.chemical_properties)
            integrated['clinical_data'].update(db_info.clinical_data)
        
        # Integrate from ChEMBL
        if drug_info['chembl_info']:
            chembl_info = drug_info['chembl_info']
            integrated['synonyms'].append(chembl_info['pref_name'])
            integrated['chemical_properties'].update({
                'molecular_weight': chembl_info.get('molecular_weight'),
                'logp': chembl_info.get('logp'),
                'smiles': chembl_info.get('smiles'),
                'inchi': chembl_info.get('inchi'),
                'molecular_formula': chembl_info.get('molecular_formula')
            })
            integrated['clinical_data'].update(chembl_info.get('clinical_data', {}))
        
        # Integrate from PubChem
        if drug_info['pubchem_info']:
            pubchem_info = drug_info['pubchem_info']
            integrated['chemical_properties'].update({
                'molecular_weight': pubchem_info.molecular_weight,
                'logp': pubchem_info.logp,
                'smiles': pubchem_info.smiles,
                'inchi': pubchem_info.inchi,
                'molecular_formula': pubchem_info.molecular_formula,
                'hbd': pubchem_info.hbd,
                'hba': pubchem_info.hba,
                'tpsa': pubchem_info.tpsa,
                'rotatable_bonds': pubchem_info.rotatable_bonds,
                'aromatic_rings': pubchem_info.aromatic_rings,
                'heavy_atoms': pubchem_info.heavy_atoms
            })
        
        # Remove duplicates
        integrated['synonyms'] = list(set(integrated['synonyms']))
        integrated['targets'] = list(set(integrated['targets']))
        integrated['indications'] = list(set(integrated['indications']))
        integrated['side_effects'] = list(set(integrated['side_effects']))
        integrated['interactions'] = list(set(integrated['interactions']))
        
        return integrated
    
    def get_drug_target_network(self, drug_name: str) -> Dict[str, Any]:
        """Get drug-target network information."""
        self.logger.info(f"Getting drug-target network for: {drug_name}")
        
        network_info = {
            'drug_name': drug_name,
            'targets': [],
            'interactions': [],
            'pathways': [],
            'network_metrics': {}
        }
        
        # Get comprehensive drug info
        drug_info = self.get_comprehensive_drug_info(drug_name)
        
        if drug_info['integrated_info']:
            integrated = drug_info['integrated_info']
            network_info['targets'] = integrated['targets']
            
            # Get target information (mock implementation)
            for target in integrated['targets']:
                target_info = {
                    'target_id': target,
                    'target_name': f'Target {target}',
                    'target_type': 'Protein',
                    'interaction_type': 'Inhibitor',
                    'confidence': 'High'
                }
                network_info['interactions'].append(target_info)
        
        return network_info
    
    def export_drug_data(self, drug_name: str, format: str = 'json') -> str:
        """Export drug data to specified format."""
        self.logger.info(f"Exporting drug data for: {drug_name}")
        
        # Get comprehensive drug info
        drug_info = self.get_comprehensive_drug_info(drug_name)
        
        if format.lower() == 'json':
            return json.dumps(drug_info, indent=2, default=str)
        elif format.lower() == 'csv':
            # Convert to CSV format (simplified)
            df = pd.DataFrame([drug_info['integrated_info']])
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

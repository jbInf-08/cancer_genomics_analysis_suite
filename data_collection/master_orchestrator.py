"""
Master Data Orchestrator

This module provides the master orchestrator for coordinating data collection
from multiple sources. It manages parallel collection, error handling, and
result aggregation across all available data collectors.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import traceback

from .base_collector import DataCollectorBase


class MasterDataOrchestrator:
    """
    Master orchestrator for coordinating data collection from multiple sources.
    
    This class provides:
    - Parallel collection from multiple sources
    - Error handling and recovery
    - Progress tracking and reporting
    - Result aggregation and validation
    - Resource management and optimization
    """
    
    def __init__(self, 
                 config_file: str = "data_collection/config.json",
                 output_dir: str = "data/external_sources",
                 max_workers: int = 4,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the master orchestrator.
        
        Args:
            config_file: Path to configuration file
            output_dir: Directory for collected data
            max_workers: Maximum number of parallel workers
            logger: Optional logger instance
        """
        self.config_file = Path(config_file)
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.logger = logger or self._setup_logger()
        
        # Load configuration
        self.config = self._load_config()
        
        # Collection results
        self.collection_results = {
            "start_time": None,
            "end_time": None,
            "total_sources": 0,
            "successful_sources": 0,
            "failed_sources": 0,
            "total_files_created": 0,
            "total_samples_collected": 0,
            "source_results": {},
            "errors": [],
            "warnings": []
        }
        
        # Available collectors registry
        self.collectors_registry = {}
        self._register_collectors()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for the orchestrator."""
        logger = logging.getLogger("MasterDataOrchestrator")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Loaded configuration from {self.config_file}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def _register_collectors(self):
        """Register all available collectors."""
        # This will be populated by importing individual collectors
        # For now, we'll define the registry structure
        self.collectors_registry = {
            # Genomic & Expression Data
            "tcga": "TCGACollector",
            "geo": "GEOCollector", 
            "icgc": "ICGCCollector",
            "ega": "EGACollector",
            "gdc": "GDCCollector",
            "ncbi": "NCBICollector",
            
            # Clinical & Registry Data
            "seer": "SEERCollector",
            "ncdb": "NCDBCollector",
            "cdc": "CDCCollector",
            "nih": "NIHCollector",
            "nci": "NCICollector",
            "nih_clinical": "NIHClinicalCollector",
            
            # Imaging & Radiomics Data
            "tcia": "TCIACollector",
            "miccai": "MICCAICollector",
            "prostate_x": "ProstateXCollector",
            "pathlaion": "PathLAIONCollector",
            "camelyon": "CAMELYONCollector",
            "pancancer_atlas": "PanCancerAtlasCollector",
            "lidc_idri": "LIDCIDRICollector",
            "nsclc_radiogenomics": "NSCLCRadiogenomicsCollector",
            "luna16": "Luna16Collector",
            "brats": "BraTSCollector",
            "rembrandt": "REMBRANDTCollector",
            "tcia_glioblastoma": "TCIAGlioblastomaCollector",
            
            # Skin & Dermatology Data
            "isic": "ISICCollector",
            "ham10000": "HAM10000Collector",
            
            # Breast Cancer Data
            "ddsm": "DDSMCollector",
            "inbreast": "INbreastCollector",
            "wisconsin_breast_cancer": "WisconsinBreastCancerCollector",
            
            # Mutation & Variant Data
            "cosmic": "COSMICCollector",
            "clinvar": "ClinVarCollector",
            "oncokb": "OncoKBCollector",
            
            # Drug & Cell Line Data
            "ccle": "CCLECollector",
            "gdsc": "GDSCCollector",
            "nci_60": "NCI60Collector",
            
            # Literature & Research Data
            "pubmed": "PubMedCollector",
            "cbioportal": "CBioPortalCollector",
            "firecloud_terra": "FireCloudTerraCollector",
            "google_cloud_healthcare": "GoogleCloudHealthcareCollector",
            
            # Challenge & Competition Data
            "kaggle": "KaggleCollector",
            "mimic": "MIMICCollector",
            
            # Additional Genomic & Expression Data
            "gtex": "GTEXCollector",
            "encode": "ENCODECollector",
            
            # Additional Clinical & Registry Data
            "clinicaltrials_gov": "ClinicalTrialsGovCollector",
            "euctr": "EUCTRCollector",
            
            # Additional Mutation & Variant Data
            "dbnsfp": "DBNSFPCollector",
            "exac": "EXACCollector",
            "gnomad": "GNOMADCollector",
            "topmed": "TOPMEDCollector",
            
            # Additional Drug & Cell Line Data
            "depmap": "DepMapCollector",
            "pharmacodb": "PharmacoDBCollector",
            
            # Proteomics & Multi-omics Data
            "cptac": "CPTACCollector",
            "cptac_proteomics": "CPTACProteomicsCollector",
            "human_protein_atlas": "HumanProteinAtlasCollector",
            "canprovar": "CanProVarCollector",
            "proteomicsdb": "ProteomicsDBCollector",
            "massive": "MASSIVECollector",
            "pride": "PRIDECollector",
            
            # Metabolomics Data
            "metabolomics_workbench": "MetabolomicsWorkbenchCollector",
            "hmdb": "HMDBCollector",
            "metabolights": "MetaboLightsCollector",
            "gnps": "GNPSCollector",
            
            # Pathway & Network Data
            "kegg": "KEGGCollector",
            "reactome": "ReactomeCollector",
            "pathway_commons": "PathwayCommonsCollector",
            "string_db": "StringDBCollector",
            "biogrid": "BioGRIDCollector",
            "intact": "IntActCollector",
            
            # Disease & Target Data
            "disgenet": "DisGeNETCollector",
            "opentargets": "OpenTargetsCollector",
            "cancer_genome_interpreter": "CancerGenomeInterpreterCollector",
            "cancer_target_discovery": "CancerTargetDiscoveryCollector",
            "cancer_immunome": "CancerImmunomeCollector",
            
            # Drug & Chemical Data
            "drugbank": "DrugBankCollector",
            "chembl": "ChEMBLCollector",
            "pubchem": "PubChemCollector",
            
            # Sequence & Annotation Data
            "uniprot": "UniProtCollector",
            "ensembl": "EnsemblCollector",
            "gencode": "GENCODECollector",
            "refseq": "RefSeqCollector",
            "genbank": "GenBankCollector",
            
            # Population Genomics & Biobanks
            "uk_biobank": "UKBiobankCollector",
            "finnish_biobank": "FinnishBiobankCollector",
            "estonian_biobank": "EstonianBiobankCollector",
            
              # Analysis & Visualization Platforms
              "ucsc_xena": "UCSCXenaCollector",
              "icgc_argo": "ICGCArgoCollector",
              
              # Biomarker Databases
              "nci_biomarker_database": "NCIBiomarkerDatabaseCollector",
              "fda_biomarker_qualification": "FDABiomarkerQualificationCollector",
              "ebi_biomarker_database": "EBIBiomarkerDatabaseCollector",
              "biomarkers_consortium": "BiomarkersConsortiumCollector",
              "precision_medicine_biomarkers": "PrecisionMedicineBiomarkersCollector",
              "cancer_biomarker_atlas": "CancerBiomarkerAtlasCollector",
              "biomarker_validation_database": "BiomarkerValidationDatabaseCollector",
              "liquid_biopsy_biomarkers": "LiquidBiopsyBiomarkersCollector",
              "immunotherapy_biomarkers": "ImmunotherapyBiomarkersCollector",
              
              # Drug Databases
              "pharmacogenomics_database": "PharmacogenomicsDatabaseCollector",
              "who_atc_ddd": "WHOATCDDDCollector",
              "nsduh": "NSDUHCollector",
              "iqvia_npa": "IQVIANPACollector",
              "rxnorm": "RxNormCollector",
              "dailymed": "DailyMedCollector",
              "faers": "FAERSCollector",
              "medicare_part_d": "MedicarePartDCollector",
              "drug_interaction_database": "DrugInteractionDatabaseCollector",
              "clinical_trials_drugs": "ClinicalTrialsDrugsCollector",
              "drug_approval_database": "DrugApprovalDatabaseCollector",
              "orphan_drug_database": "OrphanDrugDatabaseCollector",
              "drug_shortage_database": "DrugShortageDatabaseCollector",
              "drug_recall_database": "DrugRecallDatabaseCollector",
              "drug_pricing_database": "DrugPricingDatabaseCollector",
              "drug_effectiveness_database": "DrugEffectivenessDatabaseCollector",
              "drug_metabolism_database": "DrugMetabolismDatabaseCollector",
              "drug_transport_database": "DrugTransportDatabaseCollector",
              "drug_target_database": "DrugTargetDatabaseCollector",
              "drug_mechanism_database": "DrugMechanismDatabaseCollector",
              "drug_formulation_database": "DrugFormulationDatabaseCollector",
              "drug_stability_database": "DrugStabilityDatabaseCollector",
              "drug_manufacturing_database": "DrugManufacturingDatabaseCollector",
              "drug_regulatory_database": "DrugRegulatoryDatabaseCollector",
              "drug_patent_database": "DrugPatentDatabaseCollector",
              "drug_market_database": "DrugMarketDatabaseCollector",
              "drug_competitor_database": "DrugCompetitorDatabaseCollector",
              "drug_development_pipeline": "DrugDevelopmentPipelineCollector",
              "drug_investment_database": "DrugInvestmentDatabaseCollector",
              "drug_licensing_database": "DrugLicensingDatabaseCollector",
              "drug_publication_database": "DrugPublicationDatabaseCollector",
              "drug_news_database": "DrugNewsDatabaseCollector"
          }
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of all available data sources.
        
        Returns:
            List of dictionaries containing source information
        """
        sources = []
        for source_id, collector_class in self.collectors_registry.items():
            source_config = self.config.get(source_id, {})
            sources.append({
                "id": source_id,
                "name": collector_class,
                "description": self._get_source_description(source_id),
                "data_types": source_config.get("data_types", []),
                "cancer_types": source_config.get("cancer_types", []),
                "sample_limit": source_config.get("sample_limit", 0),
                "base_url": source_config.get("base_url", ""),
                "status": "available"
            })
        
        return sources
    
    def _get_source_description(self, source_id: str) -> str:
        """Get description for a data source."""
        descriptions = {
            "tcga": "The Cancer Genome Atlas - Comprehensive cancer genomics data",
            "geo": "Gene Expression Omnibus - Gene expression and genomic data",
            "cosmic": "Catalogue of Somatic Mutations in Cancer - Cancer mutation database",
            "icgc": "International Cancer Genome Consortium - International cancer genomics",
            "tcia": "The Cancer Imaging Archive - Cancer imaging data",
            "seer": "Surveillance, Epidemiology, and End Results - Cancer statistics",
            "pubmed": "PubMed - Biomedical literature database",
            "kaggle": "Kaggle - Machine learning datasets and competitions"
        }
        return descriptions.get(source_id, f"Data source: {source_id}")
    
    def collect_from_single_source(self, 
                                 source_id: str,
                                 data_type: Optional[str] = None,
                                 **kwargs) -> Dict[str, Any]:
        """
        Collect data from a single source.
        
        Args:
            source_id: Identifier for the data source
            data_type: Specific data type to collect
            **kwargs: Additional parameters for collection
            
        Returns:
            Dictionary containing collection results
        """
        if source_id not in self.collectors_registry:
            error_msg = f"Unknown data source: {source_id}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "source": source_id
            }
        
        try:
            # Import and instantiate collector
            collector_class = self._get_collector_class(source_id)
            if not collector_class:
                return {
                    "success": False,
                    "error": f"Could not import collector for {source_id}",
                    "source": source_id
                }
            
            # Get source configuration
            source_config = self.config.get(source_id, {})
            
            # Initialize collector
            collector = collector_class(
                output_dir=str(self.output_dir / source_id),
                config=source_config,
                logger=self.logger
            )
            
            # Prepare collection parameters
            collection_params = {
                "data_type": data_type,
                **kwargs
            }
            
            # Remove None values
            collection_params = {k: v for k, v in collection_params.items() if v is not None}
            
            # Collect data
            self.logger.info(f"Starting collection from {source_id}")
            with collector:
                results = collector.collect_data(**collection_params)
            
            # Get collection summary
            summary = collector.get_collection_summary()
            
            self.logger.info(f"Completed collection from {source_id}: {summary['files_created']} files, {summary['samples_collected']} samples")
            
            return {
                "success": True,
                "source": source_id,
                "summary": summary,
                "results": results
            }
            
        except Exception as e:
            error_msg = f"Collection failed for {source_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            
            return {
                "success": False,
                "error": error_msg,
                "source": source_id,
                "traceback": traceback.format_exc()
            }
    
    def collect_from_multiple_sources(self, 
                                    collection_plan: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect data from multiple sources in parallel.
        
        Args:
            collection_plan: Dictionary mapping source IDs to collection parameters
            
        Returns:
            Dictionary containing results from all sources
        """
        self.logger.info(f"Starting parallel collection from {len(collection_plan)} sources")
        self.collection_results["start_time"] = datetime.now().isoformat()
        self.collection_results["total_sources"] = len(collection_plan)
        
        # Execute collections in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all collection tasks
            future_to_source = {
                executor.submit(
                    self.collect_from_single_source, 
                    source_id, 
                    **params
                ): source_id
                for source_id, params in collection_plan.items()
            }
            
            # Process completed tasks
            for future in as_completed(future_to_source):
                source_id = future_to_source[future]
                try:
                    result = future.result()
                    self.collection_results["source_results"][source_id] = result
                    
                    if result["success"]:
                        self.collection_results["successful_sources"] += 1
                        self.collection_results["total_files_created"] += result["summary"]["files_created"]
                        self.collection_results["total_samples_collected"] += result["summary"]["samples_collected"]
                    else:
                        self.collection_results["failed_sources"] += 1
                        self.collection_results["errors"].append({
                            "source": source_id,
                            "error": result["error"]
                        })
                        
                except Exception as e:
                    self.collection_results["failed_sources"] += 1
                    error_msg = f"Unexpected error for {source_id}: {str(e)}"
                    self.collection_results["errors"].append({
                        "source": source_id,
                        "error": error_msg
                    })
                    self.logger.error(error_msg)
        
        # Finalize results
        self.collection_results["end_time"] = datetime.now().isoformat()
        
        # Save results
        self._save_collection_results()
        
        self.logger.info(
            f"Completed parallel collection: {self.collection_results['successful_sources']} successful, "
            f"{self.collection_results['failed_sources']} failed"
        )
        
        return self.collection_results
    
    def run_comprehensive_collection(self, 
                                   sources: Optional[List[str]] = None,
                                   data_types: Optional[List[str]] = None,
                                   cancer_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run comprehensive data collection from all or selected sources.
        
        Args:
            sources: List of source IDs to collect from (None for all)
            data_types: List of data types to collect (None for all)
            cancer_types: List of cancer types to focus on (None for all)
            
        Returns:
            Dictionary containing comprehensive collection results
        """
        # Determine sources to collect from
        if sources is None:
            sources = list(self.collectors_registry.keys())
        
        # Filter sources based on configuration
        available_sources = self.get_available_sources()
        valid_sources = [s["id"] for s in available_sources if s["id"] in sources]
        
        if not valid_sources:
            return {
                "success": False,
                "error": "No valid sources found for collection",
                "sources_requested": sources,
                "sources_available": [s["id"] for s in available_sources]
            }
        
        # Create collection plan
        collection_plan = {}
        for source_id in valid_sources:
            source_config = self.config.get(source_id, {})
            
            # Build collection parameters
            params = {}
            
            # Add data types if specified
            if data_types:
                available_data_types = source_config.get("data_types", [])
                params["data_types"] = [dt for dt in data_types if dt in available_data_types]
            
            # Add cancer types if specified
            if cancer_types:
                available_cancer_types = source_config.get("cancer_types", [])
                params["cancer_types"] = [ct for ct in cancer_types if ct in available_cancer_types]
            
            collection_plan[source_id] = params
        
        self.logger.info(f"Running comprehensive collection from {len(collection_plan)} sources")
        
        # Execute collection
        results = self.collect_from_multiple_sources(collection_plan)
        
        return results
    
    def _get_collector_class(self, source_id: str):
        """
        Dynamically import and return collector class for a source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Collector class or None if import fails
        """
        try:
            # Import the specific collector module
            module_name = f"data_collection.{source_id}_collector"
            module = __import__(module_name, fromlist=[self.collectors_registry[source_id]])
            collector_class = getattr(module, self.collectors_registry[source_id])
            return collector_class
        except ImportError as e:
            self.logger.warning(f"Could not import collector for {source_id}: {e}")
            return None
        except AttributeError as e:
            self.logger.warning(f"Could not find collector class for {source_id}: {e}")
            return None
    
    def _save_collection_results(self):
        """Save collection results to file."""
        try:
            results_dir = self.output_dir / "collection_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"comprehensive_collection_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(self.collection_results, f, indent=2, default=str)
            
            # Also save a summary
            summary_file = results_dir / f"collection_summary_{timestamp}.json"
            summary = {
                "start_time": self.collection_results["start_time"],
                "end_time": self.collection_results["end_time"],
                "total_sources": self.collection_results["total_sources"],
                "successful_sources": self.collection_results["successful_sources"],
                "failed_sources": self.collection_results["failed_sources"],
                "total_files_created": self.collection_results["total_files_created"],
                "total_samples_collected": self.collection_results["total_samples_collected"],
                "error_count": len(self.collection_results["errors"]),
                "warning_count": len(self.collection_results["warnings"])
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.logger.info(f"Saved collection results to {results_file}")
            self.logger.info(f"Saved collection summary to {summary_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save collection results: {e}")
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status."""
        return {
            "status": "completed" if self.collection_results["end_time"] else "running",
            "progress": {
                "total_sources": self.collection_results["total_sources"],
                "completed_sources": self.collection_results["successful_sources"] + self.collection_results["failed_sources"],
                "successful_sources": self.collection_results["successful_sources"],
                "failed_sources": self.collection_results["failed_sources"]
            },
            "results": {
                "total_files_created": self.collection_results["total_files_created"],
                "total_samples_collected": self.collection_results["total_samples_collected"],
                "errors": len(self.collection_results["errors"]),
                "warnings": len(self.collection_results["warnings"])
            }
        }

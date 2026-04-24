"""
GEO Data Collector

This module provides data collection capabilities for the Gene Expression Omnibus (GEO).
GEO is a public functional genomics data repository supporting MIAME-compliant data
submissions and providing tools for browsing, querying, and retrieving gene expression
and other functional genomics data.
"""

import pandas as pd
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from .base_collector import DataCollectorBase


class GEOCollector(DataCollectorBase):
    """
    Data collector for Gene Expression Omnibus (GEO).
    
    GEO provides:
    - Gene expression data (microarray, RNA-seq)
    - DNA methylation data
    - ChIP-seq data
    - Copy number data
    - Clinical and phenotypic data
    """
    
    def __init__(self, output_dir: str = "data/external_sources/geo", **kwargs):
        """Initialize GEO collector."""
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
        self.max_datasets = self.config.get("max_datasets", 5)
        self.search_terms = self.config.get("search_terms", ["breast cancer", "lung cancer"])
        self.data_types = self.config.get("data_types", ["expression", "methylation"])
    
    def collect_data(self, 
                    search_term: str = "breast cancer",
                    data_type: str = "expression",
                    max_datasets: Optional[int] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from GEO.
        
        Args:
            search_term: Search term for datasets
            data_type: Type of data to collect
            max_datasets: Maximum number of datasets to collect
            
        Returns:
            Dictionary containing collection results
        """
        if max_datasets is None:
            max_datasets = self.max_datasets
        
        self.logger.info(f"Collecting {data_type} data for '{search_term}' from GEO")
        
        try:
            if data_type == "expression":
                return self._collect_expression_data(search_term, max_datasets)
            elif data_type == "methylation":
                return self._collect_methylation_data(search_term, max_datasets)
            elif data_type == "chip_seq":
                return self._collect_chip_seq_data(search_term, max_datasets)
            elif data_type == "rna_seq":
                return self._collect_rna_seq_data(search_term, max_datasets)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def _search_geo_datasets(self, search_term: str, max_results: int = 100) -> List[str]:
        """Search for GEO datasets matching the search term."""
        self.logger.info(f"Searching GEO for datasets matching '{search_term}'")
        
        # Search for datasets
        search_params = {
            "db": "gds",
            "term": f"{search_term}[Title] AND gse[ETYP]",
            "retmax": max_results,
            "retmode": "xml"
        }
        
        search_response = self.make_request(
            f"{self.base_url}/esearch.fcgi",
            params=search_params
        )
        
        # Parse XML response
        root = ET.fromstring(search_response.text)
        dataset_ids = []
        
        for id_elem in root.findall(".//Id"):
            if id_elem.text:
                dataset_ids.append(id_elem.text)
        
        self.logger.info(f"Found {len(dataset_ids)} datasets matching search term")
        return dataset_ids
    
    def _get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """Get detailed information about a GEO dataset."""
        summary_params = {
            "db": "gds",
            "id": dataset_id,
            "retmode": "xml"
        }
        
        summary_response = self.make_request(
            f"{self.base_url}/esummary.fcgi",
            params=summary_params
        )
        
        # Parse XML response
        root = ET.fromstring(summary_response.text)
        
        dataset_info = {
            "id": dataset_id,
            "title": "",
            "summary": "",
            "platform": "",
            "samples": 0,
            "organism": "",
            "type": ""
        }
        
        # Extract information from XML
        for doc in root.findall(".//DocumentSummary"):
            for child in doc:
                if child.tag == "title":
                    dataset_info["title"] = child.text or ""
                elif child.tag == "summary":
                    dataset_info["summary"] = child.text or ""
                elif child.tag == "platform":
                    dataset_info["platform"] = child.text or ""
                elif child.tag == "n_samples":
                    try:
                        dataset_info["samples"] = int(child.text or "0")
                    except ValueError:
                        dataset_info["samples"] = 0
                elif child.tag == "taxon":
                    dataset_info["organism"] = child.text or ""
                elif child.tag == "gdsType":
                    dataset_info["type"] = child.text or ""
        
        return dataset_info
    
    def _collect_expression_data(self, search_term: str, max_datasets: int) -> Dict[str, Any]:
        """Collect gene expression data."""
        self.logger.info(f"Collecting expression data for '{search_term}'")
        
        # Search for datasets
        dataset_ids = self._search_geo_datasets(search_term, max_datasets * 2)
        
        if not dataset_ids:
            self.logger.warning(f"No datasets found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        collected_datasets = []
        all_expression_data = []
        
        for i, dataset_id in enumerate(dataset_ids[:max_datasets]):
            try:
                # Get dataset information
                dataset_info = self._get_dataset_info(dataset_id)
                
                if not dataset_info["title"]:
                    continue
                
                self.logger.info(f"Processing dataset {i+1}/{max_datasets}: {dataset_info['title']}")
                
                # Get dataset details
                detail_params = {
                    "db": "gds",
                    "id": dataset_id,
                    "retmode": "xml"
                }
                
                detail_response = self.make_request(
                    f"{self.base_url}/efetch.fcgi",
                    params=detail_params
                )
                
                # Parse dataset details
                root = ET.fromstring(detail_response.text)
                
                # Extract sample information
                samples = []
                for sample in root.findall(".//Sample"):
                    sample_info = {
                        "dataset_id": dataset_id,
                        "sample_id": "",
                        "title": "",
                        "organism": "",
                        "type": "",
                        "characteristics": {}
                    }
                    
                    for child in sample:
                        if child.tag == "Accession":
                            sample_info["sample_id"] = child.text or ""
                        elif child.tag == "Title":
                            sample_info["title"] = child.text or ""
                        elif child.tag == "Organism":
                            sample_info["organism"] = child.text or ""
                        elif child.tag == "Type":
                            sample_info["type"] = child.text or ""
                        elif child.tag == "Characteristics":
                            if child.text:
                                # Parse characteristics
                                char_parts = child.text.split(": ")
                                if len(char_parts) == 2:
                                    sample_info["characteristics"][char_parts[0]] = char_parts[1]
                    
                    if sample_info["sample_id"]:
                        samples.append(sample_info)
                
                # Create dataset summary
                dataset_summary = {
                    "dataset_id": dataset_id,
                    "title": dataset_info["title"],
                    "summary": dataset_info["summary"],
                    "platform": dataset_info["platform"],
                    "organism": dataset_info["organism"],
                    "type": dataset_info["type"],
                    "n_samples": len(samples),
                    "samples": samples
                }
                
                collected_datasets.append(dataset_summary)
                
                # Add sample data to overall collection
                for sample in samples:
                    all_expression_data.append({
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_info["title"],
                        "sample_id": sample["sample_id"],
                        "sample_title": sample["title"],
                        "organism": sample["organism"],
                        "sample_type": sample["type"],
                        "characteristics": str(sample["characteristics"])
                    })
                
                self.logger.debug(f"Processed dataset {dataset_id}: {len(samples)} samples")
                
            except Exception as e:
                self.logger.warning(f"Failed to process dataset {dataset_id}: {e}")
                continue
        
        if collected_datasets:
            # Save dataset information
            datasets_df = pd.DataFrame(collected_datasets)
            datasets_filename = self.generate_filename(
                f"expression_datasets_{search_term.replace(' ', '_')}",
                sample_count=len(collected_datasets)
            )
            datasets_filepath = self.save_data(datasets_df, datasets_filename, "csv")
            
            # Save sample information
            samples_df = pd.DataFrame(all_expression_data)
            samples_filename = self.generate_filename(
                f"expression_samples_{search_term.replace(' ', '_')}",
                sample_count=len(all_expression_data)
            )
            samples_filepath = self.save_data(samples_df, samples_filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(all_expression_data)
            
            return {
                "datasets_collected": len(collected_datasets),
                "samples_collected": len(all_expression_data),
                "files_created": [datasets_filepath, samples_filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _collect_methylation_data(self, search_term: str, max_datasets: int) -> Dict[str, Any]:
        """Collect DNA methylation data."""
        self.logger.info(f"Collecting methylation data for '{search_term}'")
        
        # Search for methylation datasets
        search_params = {
            "db": "gds",
            "term": f"{search_term}[Title] AND methylation[Title] AND gse[ETYP]",
            "retmax": max_datasets * 2,
            "retmode": "xml"
        }
        
        search_response = self.make_request(
            f"{self.base_url}/esearch.fcgi",
            params=search_params
        )
        
        # Parse XML response
        root = ET.fromstring(search_response.text)
        dataset_ids = []
        
        for id_elem in root.findall(".//Id"):
            if id_elem.text:
                dataset_ids.append(id_elem.text)
        
        if not dataset_ids:
            self.logger.warning(f"No methylation datasets found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        collected_datasets = []
        all_methylation_data = []
        
        for i, dataset_id in enumerate(dataset_ids[:max_datasets]):
            try:
                # Get dataset information
                dataset_info = self._get_dataset_info(dataset_id)
                
                if not dataset_info["title"]:
                    continue
                
                self.logger.info(f"Processing methylation dataset {i+1}/{max_datasets}: {dataset_info['title']}")
                
                # Get dataset details
                detail_params = {
                    "db": "gds",
                    "id": dataset_id,
                    "retmode": "xml"
                }
                
                detail_response = self.make_request(
                    f"{self.base_url}/efetch.fcgi",
                    params=detail_params
                )
                
                # Parse dataset details
                root = ET.fromstring(detail_response.text)
                
                # Extract sample information
                samples = []
                for sample in root.findall(".//Sample"):
                    sample_info = {
                        "dataset_id": dataset_id,
                        "sample_id": "",
                        "title": "",
                        "organism": "",
                        "type": "",
                        "characteristics": {}
                    }
                    
                    for child in sample:
                        if child.tag == "Accession":
                            sample_info["sample_id"] = child.text or ""
                        elif child.tag == "Title":
                            sample_info["title"] = child.text or ""
                        elif child.tag == "Organism":
                            sample_info["organism"] = child.text or ""
                        elif child.tag == "Type":
                            sample_info["type"] = child.text or ""
                        elif child.tag == "Characteristics":
                            if child.text:
                                char_parts = child.text.split(": ")
                                if len(char_parts) == 2:
                                    sample_info["characteristics"][char_parts[0]] = char_parts[1]
                    
                    if sample_info["sample_id"]:
                        samples.append(sample_info)
                
                # Create dataset summary
                dataset_summary = {
                    "dataset_id": dataset_id,
                    "title": dataset_info["title"],
                    "summary": dataset_info["summary"],
                    "platform": dataset_info["platform"],
                    "organism": dataset_info["organism"],
                    "type": dataset_info["type"],
                    "n_samples": len(samples),
                    "samples": samples
                }
                
                collected_datasets.append(dataset_summary)
                
                # Add sample data to overall collection
                for sample in samples:
                    all_methylation_data.append({
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_info["title"],
                        "sample_id": sample["sample_id"],
                        "sample_title": sample["title"],
                        "organism": sample["organism"],
                        "sample_type": sample["type"],
                        "characteristics": str(sample["characteristics"])
                    })
                
                self.logger.debug(f"Processed methylation dataset {dataset_id}: {len(samples)} samples")
                
            except Exception as e:
                self.logger.warning(f"Failed to process methylation dataset {dataset_id}: {e}")
                continue
        
        if collected_datasets:
            # Save dataset information
            datasets_df = pd.DataFrame(collected_datasets)
            datasets_filename = self.generate_filename(
                f"methylation_datasets_{search_term.replace(' ', '_')}",
                sample_count=len(collected_datasets)
            )
            datasets_filepath = self.save_data(datasets_df, datasets_filename, "csv")
            
            # Save sample information
            samples_df = pd.DataFrame(all_methylation_data)
            samples_filename = self.generate_filename(
                f"methylation_samples_{search_term.replace(' ', '_')}",
                sample_count=len(all_methylation_data)
            )
            samples_filepath = self.save_data(samples_df, samples_filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(all_methylation_data)
            
            return {
                "datasets_collected": len(collected_datasets),
                "samples_collected": len(all_methylation_data),
                "files_created": [datasets_filepath, samples_filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _collect_chip_seq_data(self, search_term: str, max_datasets: int) -> Dict[str, Any]:
        """Collect ChIP-seq data."""
        self.logger.info(f"Collecting ChIP-seq data for '{search_term}'")
        
        # Search for ChIP-seq datasets
        search_params = {
            "db": "gds",
            "term": f"{search_term}[Title] AND chip-seq[Title] AND gse[ETYP]",
            "retmax": max_datasets * 2,
            "retmode": "xml"
        }
        
        search_response = self.make_request(
            f"{self.base_url}/esearch.fcgi",
            params=search_params
        )
        
        # Parse XML response
        root = ET.fromstring(search_response.text)
        dataset_ids = []
        
        for id_elem in root.findall(".//Id"):
            if id_elem.text:
                dataset_ids.append(id_elem.text)
        
        if not dataset_ids:
            self.logger.warning(f"No ChIP-seq datasets found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        # Process datasets (similar to expression data collection)
        collected_datasets = []
        all_chip_data = []
        
        for i, dataset_id in enumerate(dataset_ids[:max_datasets]):
            try:
                dataset_info = self._get_dataset_info(dataset_id)
                
                if not dataset_info["title"]:
                    continue
                
                self.logger.info(f"Processing ChIP-seq dataset {i+1}/{max_datasets}: {dataset_info['title']}")
                
                # Get dataset details and process samples
                detail_params = {
                    "db": "gds",
                    "id": dataset_id,
                    "retmode": "xml"
                }
                
                detail_response = self.make_request(
                    f"{self.base_url}/efetch.fcgi",
                    params=detail_params
                )
                
                root = ET.fromstring(detail_response.text)
                
                samples = []
                for sample in root.findall(".//Sample"):
                    sample_info = {
                        "dataset_id": dataset_id,
                        "sample_id": "",
                        "title": "",
                        "organism": "",
                        "type": "",
                        "characteristics": {}
                    }
                    
                    for child in sample:
                        if child.tag == "Accession":
                            sample_info["sample_id"] = child.text or ""
                        elif child.tag == "Title":
                            sample_info["title"] = child.text or ""
                        elif child.tag == "Organism":
                            sample_info["organism"] = child.text or ""
                        elif child.tag == "Type":
                            sample_info["type"] = child.text or ""
                        elif child.tag == "Characteristics":
                            if child.text:
                                char_parts = child.text.split(": ")
                                if len(char_parts) == 2:
                                    sample_info["characteristics"][char_parts[0]] = char_parts[1]
                    
                    if sample_info["sample_id"]:
                        samples.append(sample_info)
                
                dataset_summary = {
                    "dataset_id": dataset_id,
                    "title": dataset_info["title"],
                    "summary": dataset_info["summary"],
                    "platform": dataset_info["platform"],
                    "organism": dataset_info["organism"],
                    "type": dataset_info["type"],
                    "n_samples": len(samples),
                    "samples": samples
                }
                
                collected_datasets.append(dataset_summary)
                
                for sample in samples:
                    all_chip_data.append({
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_info["title"],
                        "sample_id": sample["sample_id"],
                        "sample_title": sample["title"],
                        "organism": sample["organism"],
                        "sample_type": sample["type"],
                        "characteristics": str(sample["characteristics"])
                    })
                
                self.logger.debug(f"Processed ChIP-seq dataset {dataset_id}: {len(samples)} samples")
                
            except Exception as e:
                self.logger.warning(f"Failed to process ChIP-seq dataset {dataset_id}: {e}")
                continue
        
        if collected_datasets:
            # Save dataset information
            datasets_df = pd.DataFrame(collected_datasets)
            datasets_filename = self.generate_filename(
                f"chip_seq_datasets_{search_term.replace(' ', '_')}",
                sample_count=len(collected_datasets)
            )
            datasets_filepath = self.save_data(datasets_df, datasets_filename, "csv")
            
            # Save sample information
            samples_df = pd.DataFrame(all_chip_data)
            samples_filename = self.generate_filename(
                f"chip_seq_samples_{search_term.replace(' ', '_')}",
                sample_count=len(all_chip_data)
            )
            samples_filepath = self.save_data(samples_df, samples_filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(all_chip_data)
            
            return {
                "datasets_collected": len(collected_datasets),
                "samples_collected": len(all_chip_data),
                "files_created": [datasets_filepath, samples_filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _collect_rna_seq_data(self, search_term: str, max_datasets: int) -> Dict[str, Any]:
        """Collect RNA-seq data."""
        self.logger.info(f"Collecting RNA-seq data for '{search_term}'")
        
        # Search for RNA-seq datasets
        search_params = {
            "db": "gds",
            "term": f"{search_term}[Title] AND rna-seq[Title] AND gse[ETYP]",
            "retmax": max_datasets * 2,
            "retmode": "xml"
        }
        
        search_response = self.make_request(
            f"{self.base_url}/esearch.fcgi",
            params=search_params
        )
        
        # Parse XML response
        root = ET.fromstring(search_response.text)
        dataset_ids = []
        
        for id_elem in root.findall(".//Id"):
            if id_elem.text:
                dataset_ids.append(id_elem.text)
        
        if not dataset_ids:
            self.logger.warning(f"No RNA-seq datasets found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        # Process datasets (similar to expression data collection)
        collected_datasets = []
        all_rna_seq_data = []
        
        for i, dataset_id in enumerate(dataset_ids[:max_datasets]):
            try:
                dataset_info = self._get_dataset_info(dataset_id)
                
                if not dataset_info["title"]:
                    continue
                
                self.logger.info(f"Processing RNA-seq dataset {i+1}/{max_datasets}: {dataset_info['title']}")
                
                # Get dataset details and process samples
                detail_params = {
                    "db": "gds",
                    "id": dataset_id,
                    "retmode": "xml"
                }
                
                detail_response = self.make_request(
                    f"{self.base_url}/efetch.fcgi",
                    params=detail_params
                )
                
                root = ET.fromstring(detail_response.text)
                
                samples = []
                for sample in root.findall(".//Sample"):
                    sample_info = {
                        "dataset_id": dataset_id,
                        "sample_id": "",
                        "title": "",
                        "organism": "",
                        "type": "",
                        "characteristics": {}
                    }
                    
                    for child in sample:
                        if child.tag == "Accession":
                            sample_info["sample_id"] = child.text or ""
                        elif child.tag == "Title":
                            sample_info["title"] = child.text or ""
                        elif child.tag == "Organism":
                            sample_info["organism"] = child.text or ""
                        elif child.tag == "Type":
                            sample_info["type"] = child.text or ""
                        elif child.tag == "Characteristics":
                            if child.text:
                                char_parts = child.text.split(": ")
                                if len(char_parts) == 2:
                                    sample_info["characteristics"][char_parts[0]] = char_parts[1]
                    
                    if sample_info["sample_id"]:
                        samples.append(sample_info)
                
                dataset_summary = {
                    "dataset_id": dataset_id,
                    "title": dataset_info["title"],
                    "summary": dataset_info["summary"],
                    "platform": dataset_info["platform"],
                    "organism": dataset_info["organism"],
                    "type": dataset_info["type"],
                    "n_samples": len(samples),
                    "samples": samples
                }
                
                collected_datasets.append(dataset_summary)
                
                for sample in samples:
                    all_rna_seq_data.append({
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_info["title"],
                        "sample_id": sample["sample_id"],
                        "sample_title": sample["title"],
                        "organism": sample["organism"],
                        "sample_type": sample["type"],
                        "characteristics": str(sample["characteristics"])
                    })
                
                self.logger.debug(f"Processed RNA-seq dataset {dataset_id}: {len(samples)} samples")
                
            except Exception as e:
                self.logger.warning(f"Failed to process RNA-seq dataset {dataset_id}: {e}")
                continue
        
        if collected_datasets:
            # Save dataset information
            datasets_df = pd.DataFrame(collected_datasets)
            datasets_filename = self.generate_filename(
                f"rna_seq_datasets_{search_term.replace(' ', '_')}",
                sample_count=len(collected_datasets)
            )
            datasets_filepath = self.save_data(datasets_df, datasets_filename, "csv")
            
            # Save sample information
            samples_df = pd.DataFrame(all_rna_seq_data)
            samples_filename = self.generate_filename(
                f"rna_seq_samples_{search_term.replace(' ', '_')}",
                sample_count=len(all_rna_seq_data)
            )
            samples_filepath = self.save_data(samples_df, samples_filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(all_rna_seq_data)
            
            return {
                "datasets_collected": len(collected_datasets),
                "samples_collected": len(all_rna_seq_data),
                "files_created": [datasets_filepath, samples_filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets from GEO."""
        datasets = []
        
        for search_term in self.search_terms:
            for data_type in self.data_types:
                datasets.append({
                    "search_term": search_term,
                    "data_type": data_type,
                    "description": f"GEO {data_type} data for {search_term}",
                    "estimated_datasets": self.max_datasets,
                    "source": "GEO"
                })
        
        return datasets

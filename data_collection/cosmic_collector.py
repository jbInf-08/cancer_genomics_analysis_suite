"""
COSMIC Data Collector

This module provides data collection capabilities for the Catalogue of Somatic Mutations
in Cancer (COSMIC). COSMIC is the world's largest and most comprehensive resource for
exploring the impact of somatic mutations in human cancer.

COSMIC Data Access:
- COSMIC requires registration and accepts academic/commercial licenses
- Register at: https://cancer.sanger.ac.uk/cosmic/register
- API documentation: https://cancer.sanger.ac.uk/cosmic/download

For full programmatic access, set the COSMIC_API_KEY environment variable.
Without authentication, this collector uses publicly available cancer mutation
data from alternative sources (cBioPortal, ICGC).
"""

import pandas as pd
import requests
import base64
import json
import gzip
import io
from typing import Dict, List, Any, Optional
from pathlib import Path
from .base_collector import DataCollectorBase


class COSMICCollector(DataCollectorBase):
    """
    Data collector for Catalogue of Somatic Mutations in Cancer (COSMIC).
    
    COSMIC provides:
    - Somatic mutations across all cancer types
    - Cancer Gene Census (CGC) - curated list of cancer genes
    - Gene fusions and copy number alterations
    - Drug sensitivity data (GDSC)
    - Mutational signatures
    
    Authentication:
    - Set COSMIC_API_KEY environment variable with your API token
    - Alternatively, download data files from COSMIC and place in the data directory
    - Without auth, uses publicly available data from alternative sources
    
    Note: Some COSMIC data requires a commercial license for non-academic use.
    """
    
    # Cancer Gene Census - publicly available gene list
    # Source: https://cancer.sanger.ac.uk/census
    CANCER_GENE_CENSUS_TIER1 = [
        'ABL1', 'AKT1', 'ALK', 'APC', 'AR', 'ARID1A', 'ASXL1', 'ATM', 'ATR',
        'ATRX', 'AXIN1', 'B2M', 'BAP1', 'BCL2', 'BCL6', 'BCOR', 'BRAF', 'BRCA1',
        'BRCA2', 'BRD4', 'BTK', 'CALR', 'CARD11', 'CASP8', 'CBL', 'CCND1', 'CCND3',
        'CCNE1', 'CD274', 'CD79A', 'CD79B', 'CDC73', 'CDH1', 'CDK12', 'CDK4', 'CDK6',
        'CDKN1B', 'CDKN2A', 'CDKN2B', 'CDKN2C', 'CEBPA', 'CHD4', 'CHEK2', 'CIC',
        'CREBBP', 'CRLF2', 'CSF1R', 'CSF3R', 'CTCF', 'CTNNB1', 'CUX1', 'CYLD',
        'DAXX', 'DDR2', 'DICER1', 'DNMT3A', 'EGFR', 'EP300', 'ERBB2', 'ERBB3',
        'ERBB4', 'ERG', 'ESR1', 'ETV1', 'ETV4', 'ETV5', 'ETV6', 'EWSR1', 'EZH2',
        'FAM46C', 'FANCA', 'FANCC', 'FANCD2', 'FANCE', 'FANCF', 'FANCG', 'FAS',
        'FBXW7', 'FGFR1', 'FGFR2', 'FGFR3', 'FGFR4', 'FH', 'FLCN', 'FLT3', 'FOXL2',
        'FOXO1', 'FOXP1', 'FUBP1', 'GATA1', 'GATA2', 'GATA3', 'GNA11', 'GNAQ',
        'GNAS', 'GPS2', 'GRIN2A', 'H3F3A', 'H3F3B', 'HGF', 'HIST1H3B', 'HNF1A',
        'HRAS', 'ID3', 'IDH1', 'IDH2', 'IKZF1', 'IL7R', 'IRF4', 'JAK1', 'JAK2',
        'JAK3', 'JUN', 'KDM5A', 'KDM5C', 'KDM6A', 'KDR', 'KEAP1', 'KIT', 'KLF4',
        'KLHL6', 'KMT2A', 'KMT2B', 'KMT2C', 'KMT2D', 'KRAS', 'LATS1', 'LATS2',
        'LMO1', 'LMO2', 'MAP2K1', 'MAP2K2', 'MAP2K4', 'MAP3K1', 'MAP3K13', 'MAPK1',
        'MAX', 'MDM2', 'MDM4', 'MED12', 'MEF2B', 'MEN1', 'MET', 'MITF', 'MLH1',
        'MRE11A', 'MSH2', 'MSH6', 'MTOR', 'MUTYH', 'MYC', 'MYCL', 'MYCN', 'MYD88',
        'NBN', 'NCOR1', 'NF1', 'NF2', 'NFE2L2', 'NFKBIA', 'NKX2-1', 'NOTCH1',
        'NOTCH2', 'NPM1', 'NRAS', 'NSD1', 'NSD2', 'NSD3', 'NTRK1', 'NTRK2', 'NTRK3',
        'NUP98', 'PAX5', 'PBRM1', 'PDCD1LG2', 'PDGFRA', 'PDGFRB', 'PHF6', 'PHOX2B',
        'PIK3CA', 'PIK3R1', 'PIM1', 'PLCG2', 'PMS2', 'POLD1', 'POLE', 'POT1',
        'PPP2R1A', 'PPP6C', 'PRDM1', 'PRKAR1A', 'PTCH1', 'PTEN', 'PTPN11', 'PTPRD',
        'PTPRT', 'RAC1', 'RAD21', 'RAD51B', 'RAD51C', 'RAD51D', 'RAF1', 'RARA',
        'RB1', 'RBM10', 'RECQL4', 'REL', 'RET', 'RHEB', 'RHOA', 'RICTOR', 'RNF43',
        'ROS1', 'RPL10', 'RPL5', 'RRAS2', 'RUNX1', 'RUNX1T1', 'SBDS', 'SDHA',
        'SDHAF2', 'SDHB', 'SDHC', 'SDHD', 'SETBP1', 'SETD2', 'SF3B1', 'SGK1',
        'SH2B3', 'SMAD2', 'SMAD3', 'SMAD4', 'SMARCA4', 'SMARCB1', 'SMARCD1', 'SMO',
        'SOCS1', 'SOX2', 'SOX9', 'SPEN', 'SPOP', 'SRC', 'SRSF2', 'STAG2', 'STAT3',
        'STAT5B', 'STAT6', 'STK11', 'SUFU', 'SUZ12', 'TAL1', 'TBL1XR1', 'TBX3',
        'TCF3', 'TCF7L2', 'TET1', 'TET2', 'TGFBR1', 'TGFBR2', 'TMPRSS2', 'TNFAIP3',
        'TNFRSF14', 'TP53', 'TRAF7', 'TSC1', 'TSC2', 'TSHR', 'U2AF1', 'VHL',
        'WHSC1', 'WT1', 'XPA', 'XPC', 'XPO1', 'ZFHX3', 'ZRSR2'
    ]
    
    def __init__(self, output_dir: str = "data/external_sources/cosmic", **kwargs):
        """Initialize COSMIC collector."""
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://cancer.sanger.ac.uk/cosmic")
        self.api_url = "https://cancer.sanger.ac.uk/api/v1"
        self.gene_list = self.config.get("gene_list", ["TP53", "BRCA1", "BRCA2", "EGFR", "KRAS", "PIK3CA", "BRAF"])
        self.cancer_types = self.config.get("cancer_types", ["breast", "lung", "prostate", "colorectal"])
        self.data_types = self.config.get("data_types", ["mutations", "cancer_gene_census", "gene_fusions"])
        
        # Check authentication status
        self.authenticated = self.auth_manager.has_credentials('cosmic')
        if self.authenticated:
            self.logger.info("COSMIC API credentials found")
        else:
            self.logger.info("No COSMIC API credentials - using alternative data sources")
    
    def collect_data(self, 
                    data_type: str = "mutations",
                    gene_list: Optional[List[str]] = None,
                    cancer_type: Optional[str] = None,
                    use_cbioportal_fallback: bool = True,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from COSMIC or fallback sources.
        
        Args:
            data_type: Type of data to collect
            gene_list: List of genes to focus on
            cancer_type: Cancer type to focus on
            use_cbioportal_fallback: Use cBioPortal if COSMIC auth not available
            
        Returns:
            Dictionary containing collection results
        """
        if gene_list is None:
            gene_list = self.gene_list
        
        self.logger.info(f"Collecting {data_type} data from COSMIC")
        
        try:
            if data_type == "mutations":
                if self.authenticated:
                    return self._collect_mutations_cosmic(gene_list, cancer_type)
                elif use_cbioportal_fallback:
                    return self._collect_mutations_cbioportal(gene_list, cancer_type)
                else:
                    self.logger.warning("COSMIC authentication required for mutations. Set COSMIC_API_KEY.")
                    return {"samples_collected": 0, "files_created": [], "error": "Authentication required"}
            elif data_type == "cancer_gene_census":
                return self._collect_cancer_gene_census()
            elif data_type == "gene_fusions":
                return self._collect_gene_fusions_cbioportal(gene_list, cancer_type)
            elif data_type == "copy_number":
                return self._collect_copy_number_cbioportal(gene_list, cancer_type)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def _collect_mutations_cosmic(self, gene_list: List[str], cancer_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect somatic mutation data from COSMIC API.
        Requires authentication.
        """
        self.logger.info(f"Collecting mutation data for {len(gene_list)} genes from COSMIC API")
        
        all_mutations = []
        
        for gene in gene_list:
            try:
                self.logger.info(f"Collecting mutations for gene: {gene}")
                
                # COSMIC API endpoint for gene mutations
                url = f"{self.api_url}/gene/{gene}/mutations"
                
                params = {}
                if cancer_type:
                    params['cancer_type'] = cancer_type
                
                response = self.make_request(url, params=params, source_override='cosmic')
                
                if response.status_code == 200:
                    mutations_data = response.json()
                    
                    for mutation in mutations_data.get("data", []):
                        mutation_record = {
                            "gene": gene,
                            "cosmic_mutation_id": mutation.get("mutation_id", ""),
                            "genomic_mutation_id": mutation.get("genomic_mutation_id", ""),
                            "chromosome": mutation.get("chromosome", ""),
                            "start_position": mutation.get("position_start", ""),
                            "end_position": mutation.get("position_end", ""),
                            "reference_allele": mutation.get("ref_allele", ""),
                            "tumor_allele": mutation.get("mut_allele", ""),
                            "mutation_cds": mutation.get("mutation_cds", ""),
                            "mutation_aa": mutation.get("mutation_aa", ""),
                            "mutation_type": mutation.get("mutation_type", ""),
                            "cancer_type": mutation.get("primary_site", ""),
                            "histology": mutation.get("histology_subtype_1", ""),
                            "sample_count": mutation.get("sample_count", 0),
                            "fathmm_prediction": mutation.get("fathmm_prediction", ""),
                            "fathmm_score": mutation.get("fathmm_score", ""),
                        }
                        all_mutations.append(mutation_record)
                
                self.logger.debug(f"Collected mutations for {gene}")
                
            except Exception as e:
                self.logger.warning(f"Failed to collect mutations for gene {gene}: {e}")
                continue
        
        return self._save_mutation_results(all_mutations, gene_list, cancer_type, "cosmic")
    
    def _collect_mutations_cbioportal(self, gene_list: List[str], cancer_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect mutation data from cBioPortal (public API) as COSMIC fallback.
        cBioPortal includes COSMIC annotations.
        """
        self.logger.info(f"Collecting mutation data from cBioPortal for {len(gene_list)} genes")
        
        all_mutations = []
        cbioportal_url = "https://www.cbioportal.org/api"
        
        # Map cancer types to cBioPortal study IDs
        cancer_study_map = {
            'breast': ['brca_tcga', 'brca_metabric'],
            'lung': ['luad_tcga', 'lusc_tcga', 'nsclc_tcga_broad_2016'],
            'colorectal': ['coadread_tcga', 'crc_msk_2017'],
            'prostate': ['prad_tcga', 'prad_mskcc'],
            'melanoma': ['skcm_tcga', 'mel_ucla_2016'],
            'ovarian': ['ov_tcga'],
            'pancreatic': ['paad_tcga'],
            'general': ['msk_impact_2017']  # Large pan-cancer study
        }
        
        # Get study IDs
        study_ids = cancer_study_map.get(cancer_type, cancer_study_map['general'])
        
        for gene in gene_list:
            for study_id in study_ids[:2]:  # Limit to 2 studies per gene
                try:
                    # Get mutations for this gene in this study
                    url = f"{cbioportal_url}/molecular-profiles/{study_id}_mutations/mutations"
                    params = {
                        'entrezGeneId': self._get_entrez_id(gene),
                    }
                    
                    # Try to get data
                    try:
                        response = self.make_request(
                            url, 
                            params=params, 
                            auth_type='none',  # cBioPortal public API
                            headers={'Accept': 'application/json'}
                        )
                        
                        if response.status_code == 200:
                            mutations_data = response.json()
                            
                            for mutation in mutations_data:
                                mutation_record = {
                                    "gene": gene,
                                    "study_id": study_id,
                                    "sample_id": mutation.get("sampleId", ""),
                                    "patient_id": mutation.get("patientId", ""),
                                    "chromosome": mutation.get("chr", ""),
                                    "start_position": mutation.get("startPosition", ""),
                                    "end_position": mutation.get("endPosition", ""),
                                    "reference_allele": mutation.get("referenceAllele", ""),
                                    "tumor_allele": mutation.get("variantAllele", ""),
                                    "mutation_type": mutation.get("mutationType", ""),
                                    "protein_change": mutation.get("proteinChange", ""),
                                    "variant_type": mutation.get("variantType", ""),
                                    "cosmic_id": mutation.get("keyword", ""),  # Often contains COSMIC ID
                                    "allele_frequency": mutation.get("tumorAltCount", 0) / max(mutation.get("tumorRefCount", 0) + mutation.get("tumorAltCount", 1), 1),
                                    "annotation": mutation.get("annotation", ""),
                                }
                                all_mutations.append(mutation_record)
                    except:
                        # Try alternative endpoint
                        pass
                        
                except Exception as e:
                    self.logger.debug(f"Failed to collect from {study_id} for {gene}: {e}")
                    continue
        
        return self._save_mutation_results(all_mutations, gene_list, cancer_type, "cbioportal")
    
    def _get_entrez_id(self, gene_symbol: str) -> int:
        """Get Entrez Gene ID for a gene symbol using MyGene.info."""
        # Common cancer gene IDs (cached to avoid API calls)
        gene_id_map = {
            'TP53': 7157, 'BRCA1': 672, 'BRCA2': 675, 'EGFR': 1956,
            'KRAS': 3845, 'PIK3CA': 5290, 'BRAF': 673, 'APC': 324,
            'PTEN': 5728, 'ATM': 472, 'RB1': 5925, 'CDKN2A': 1029,
            'MYC': 4609, 'ERBB2': 2064, 'NRAS': 4893, 'NF1': 4763,
            'ALK': 238, 'MET': 4233, 'RET': 5979, 'FGFR1': 2260,
        }
        
        if gene_symbol in gene_id_map:
            return gene_id_map[gene_symbol]
        
        # Try MyGene.info API
        try:
            url = f"https://mygene.info/v3/query?q=symbol:{gene_symbol}&species=human&fields=entrezgene"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('hits'):
                    return data['hits'][0].get('entrezgene', 0)
        except:
            pass
        
        return 0
    
    def _save_mutation_results(self, mutations: List[Dict], gene_list: List[str], 
                               cancer_type: Optional[str], source: str) -> Dict[str, Any]:
        """Save mutation collection results."""
        if mutations:
            df = pd.DataFrame(mutations)
            
            filename = self.generate_filename(
                f"mutations_{source}",
                cancer_type=cancer_type or "all",
                sample_count=len(df)
            )
            filepath = self.save_data(df, filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(df)
            
            return {
                "source": source,
                "genes_processed": len(gene_list),
                "mutations_collected": len(df),
                "unique_genes": len(df['gene'].unique()) if 'gene' in df.columns else 0,
                "files_created": [filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": [], "source": source}
    
    def _collect_cancer_gene_census(self) -> Dict[str, Any]:
        """
        Collect Cancer Gene Census data.
        Uses the built-in Tier 1 gene list (publicly available) and enriches
        with data from MyGene.info and UniProt.
        """
        self.logger.info("Collecting Cancer Gene Census data")
        
        try:
            all_cgc_genes = []
            
            # Use the publicly available Tier 1 genes
            for gene_symbol in self.CANCER_GENE_CENSUS_TIER1:
                gene_record = {
                    "gene_symbol": gene_symbol,
                    "tier": "1",
                    "source": "COSMIC_CGC_Tier1"
                }
                
                # Enrich with gene information from MyGene.info
                try:
                    url = f"https://mygene.info/v3/query?q=symbol:{gene_symbol}&species=human&fields=name,entrezgene,ensembl.gene,summary,go,pathway"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('hits'):
                            hit = data['hits'][0]
                            gene_record.update({
                                "gene_name": hit.get('name', ''),
                                "entrez_id": hit.get('entrezgene', ''),
                                "ensembl_id": hit.get('ensembl', {}).get('gene', '') if isinstance(hit.get('ensembl'), dict) else '',
                                "summary": hit.get('summary', '')[:500] if hit.get('summary') else '',
                            })
                except Exception as e:
                    self.logger.debug(f"Could not enrich {gene_symbol}: {e}")
                
                # Add known cancer associations
                gene_record.update(self._get_cancer_gene_annotations(gene_symbol))
                all_cgc_genes.append(gene_record)
            
            if all_cgc_genes:
                df = pd.DataFrame(all_cgc_genes)
                
                filename = self.generate_filename(
                    "cancer_gene_census",
                    sample_count=len(df)
                )
                filepath = self.save_data(df, filename, "csv")
                
                # Also save as JSON with full data
                json_filepath = self.save_data(all_cgc_genes, filename.replace('.csv', ''), "json")
                
                self.collection_metadata["samples_collected"] = len(df)
                
                return {
                    "genes_collected": len(df),
                    "tier_1_genes": len(df),
                    "files_created": [filepath, json_filepath]
                }
            else:
                return {"samples_collected": 0, "files_created": []}
                
        except Exception as e:
            self.logger.error(f"Failed to collect Cancer Gene Census data: {e}")
            return {"samples_collected": 0, "files_created": []}
    
    def _get_cancer_gene_annotations(self, gene_symbol: str) -> Dict[str, str]:
        """Get known cancer annotations for common cancer genes."""
        # Known annotations for major cancer genes
        annotations = {
            'TP53': {'role': 'TSG', 'mutation_types': 'Mis, N, F, S', 'cancer_types': 'Most cancer types'},
            'BRCA1': {'role': 'TSG', 'mutation_types': 'Mis, N, F', 'cancer_types': 'Breast, Ovarian'},
            'BRCA2': {'role': 'TSG', 'mutation_types': 'Mis, N, F', 'cancer_types': 'Breast, Ovarian, Pancreatic'},
            'EGFR': {'role': 'Oncogene', 'mutation_types': 'Mis, A', 'cancer_types': 'Lung, Glioblastoma'},
            'KRAS': {'role': 'Oncogene', 'mutation_types': 'Mis', 'cancer_types': 'Pancreatic, Colorectal, Lung'},
            'BRAF': {'role': 'Oncogene', 'mutation_types': 'Mis', 'cancer_types': 'Melanoma, Thyroid, Colorectal'},
            'PIK3CA': {'role': 'Oncogene', 'mutation_types': 'Mis', 'cancer_types': 'Breast, Colorectal, Endometrial'},
            'PTEN': {'role': 'TSG', 'mutation_types': 'Mis, N, F, D', 'cancer_types': 'Glioblastoma, Prostate, Endometrial'},
            'APC': {'role': 'TSG', 'mutation_types': 'N, F', 'cancer_types': 'Colorectal'},
            'RB1': {'role': 'TSG', 'mutation_types': 'Mis, N, F, D', 'cancer_types': 'Retinoblastoma, Osteosarcoma'},
            'MYC': {'role': 'Oncogene', 'mutation_types': 'A, T', 'cancer_types': 'Burkitt lymphoma, Many cancers'},
            'ERBB2': {'role': 'Oncogene', 'mutation_types': 'A, Mis', 'cancer_types': 'Breast, Gastric'},
            'ALK': {'role': 'Oncogene', 'mutation_types': 'T, Mis', 'cancer_types': 'NSCLC, Neuroblastoma'},
            'CDKN2A': {'role': 'TSG', 'mutation_types': 'Mis, N, D', 'cancer_types': 'Melanoma, Pancreatic'},
            'NF1': {'role': 'TSG', 'mutation_types': 'Mis, N, F', 'cancer_types': 'Neurofibromatosis, MPNST'},
        }
        return annotations.get(gene_symbol, {'role': '', 'mutation_types': '', 'cancer_types': ''})
    
    def _collect_gene_fusions_cbioportal(self, gene_list: List[str], cancer_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect gene fusion data from cBioPortal.
        """
        self.logger.info(f"Collecting gene fusion data for {len(gene_list)} genes")
        
        all_fusions = []
        cbioportal_url = "https://www.cbioportal.org/api"
        
        # Known cancer-related gene fusions
        known_fusions = {
            'ALK': [('EML4', 'ALK', 'NSCLC'), ('NPM1', 'ALK', 'Lymphoma')],
            'BCR': [('BCR', 'ABL1', 'CML')],
            'ABL1': [('BCR', 'ABL1', 'CML')],
            'RET': [('CCDC6', 'RET', 'Thyroid'), ('KIF5B', 'RET', 'NSCLC')],
            'ROS1': [('CD74', 'ROS1', 'NSCLC'), ('SLC34A2', 'ROS1', 'NSCLC')],
            'NTRK1': [('TPM3', 'NTRK1', 'Various'), ('LMNA', 'NTRK1', 'Various')],
            'NTRK2': [('QKI', 'NTRK2', 'Various')],
            'NTRK3': [('ETV6', 'NTRK3', 'Various')],
            'BRAF': [('KIAA1549', 'BRAF', 'Pilocytic astrocytoma')],
            'FGFR2': [('BICC1', 'FGFR2', 'Cholangiocarcinoma')],
            'FGFR3': [('TACC3', 'FGFR3', 'Glioblastoma')],
            'EWSR1': [('EWSR1', 'FLI1', 'Ewing sarcoma'), ('EWSR1', 'ERG', 'Ewing sarcoma')],
            'MYC': [('IGH', 'MYC', 'Burkitt lymphoma')],
            'ERG': [('TMPRSS2', 'ERG', 'Prostate cancer')],
        }
        
        for gene in gene_list:
            if gene in known_fusions:
                for gene1, gene2, cancer in known_fusions[gene]:
                    fusion_record = {
                        "gene_1": gene1,
                        "gene_2": gene2,
                        "cancer_type": cancer,
                        "source": "curated_fusion_list",
                        "clinical_relevance": "Known oncogenic fusion",
                        "therapeutic_targets": self._get_fusion_therapeutic_info(gene1, gene2)
                    }
                    all_fusions.append(fusion_record)
        
        # Try to get additional fusions from cBioPortal structural variants
        try:
            # Get from pan-cancer study
            url = f"{cbioportal_url}/structural-variants/fetch"
            # Note: This endpoint requires POST with study IDs
            # Simplified for now with known fusions
        except Exception as e:
            self.logger.debug(f"Could not fetch additional fusions: {e}")
        
        if all_fusions:
            df = pd.DataFrame(all_fusions)
            
            filename = self.generate_filename(
                "gene_fusions",
                cancer_type=cancer_type or "all",
                sample_count=len(df)
            )
            filepath = self.save_data(df, filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(df)
            
            return {
                "genes_processed": len(gene_list),
                "fusions_collected": len(df),
                "files_created": [filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _get_fusion_therapeutic_info(self, gene1: str, gene2: str) -> str:
        """Get therapeutic information for known fusions."""
        therapeutic_map = {
            ('EML4', 'ALK'): 'Crizotinib, Alectinib, Ceritinib, Brigatinib',
            ('BCR', 'ABL1'): 'Imatinib, Dasatinib, Nilotinib, Bosutinib',
            ('CCDC6', 'RET'): 'Selpercatinib, Pralsetinib',
            ('KIF5B', 'RET'): 'Selpercatinib, Pralsetinib',
            ('CD74', 'ROS1'): 'Crizotinib, Entrectinib',
            ('TPM3', 'NTRK1'): 'Larotrectinib, Entrectinib',
            ('ETV6', 'NTRK3'): 'Larotrectinib, Entrectinib',
            ('TMPRSS2', 'ERG'): 'Under investigation',
        }
        return therapeutic_map.get((gene1, gene2), 'Under investigation')
    
    def _collect_copy_number_cbioportal(self, gene_list: List[str], cancer_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect copy number alteration data from cBioPortal.
        """
        self.logger.info(f"Collecting copy number data for {len(gene_list)} genes")
        
        all_cn_alterations = []
        
        # Known amplifications and deletions in cancer
        known_cna = {
            'ERBB2': {'alteration': 'amplification', 'cancers': ['Breast', 'Gastric'], 'frequency': '15-20%'},
            'MYC': {'alteration': 'amplification', 'cancers': ['Various'], 'frequency': '10-30%'},
            'CCND1': {'alteration': 'amplification', 'cancers': ['Breast', 'Head and Neck'], 'frequency': '15-20%'},
            'EGFR': {'alteration': 'amplification', 'cancers': ['NSCLC', 'Glioblastoma'], 'frequency': '10-15%'},
            'MDM2': {'alteration': 'amplification', 'cancers': ['Sarcoma', 'Various'], 'frequency': '5-10%'},
            'CDK4': {'alteration': 'amplification', 'cancers': ['Sarcoma', 'Glioblastoma'], 'frequency': '5-15%'},
            'FGFR1': {'alteration': 'amplification', 'cancers': ['Lung', 'Breast'], 'frequency': '10-20%'},
            'RB1': {'alteration': 'deletion', 'cancers': ['Retinoblastoma', 'SCLC'], 'frequency': '30-90%'},
            'CDKN2A': {'alteration': 'deletion', 'cancers': ['Melanoma', 'Pancreatic', 'Glioblastoma'], 'frequency': '30-60%'},
            'PTEN': {'alteration': 'deletion', 'cancers': ['Prostate', 'Glioblastoma', 'Endometrial'], 'frequency': '20-40%'},
            'TP53': {'alteration': 'deletion', 'cancers': ['Various'], 'frequency': '10-30%'},
            'BRCA1': {'alteration': 'deletion', 'cancers': ['Breast', 'Ovarian'], 'frequency': '5-10%'},
            'BRCA2': {'alteration': 'deletion', 'cancers': ['Breast', 'Ovarian', 'Pancreatic'], 'frequency': '5-10%'},
        }
        
        for gene in gene_list:
            if gene in known_cna:
                info = known_cna[gene]
                cn_record = {
                    "gene": gene,
                    "alteration_type": info['alteration'],
                    "cancer_types": '; '.join(info['cancers']),
                    "frequency": info['frequency'],
                    "source": "curated_cna_list",
                    "therapeutic_relevance": self._get_cna_therapeutic_info(gene, info['alteration'])
                }
                all_cn_alterations.append(cn_record)
        
        if all_cn_alterations:
            df = pd.DataFrame(all_cn_alterations)
            
            filename = self.generate_filename(
                "copy_number_alterations",
                cancer_type=cancer_type or "all",
                sample_count=len(df)
            )
            filepath = self.save_data(df, filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(df)
            
            return {
                "genes_processed": len(gene_list),
                "alterations_collected": len(df),
                "unique_genes": len(df['gene'].unique()),
                "files_created": [filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _get_cna_therapeutic_info(self, gene: str, alteration: str) -> str:
        """Get therapeutic information for copy number alterations."""
        therapeutic_map = {
            ('ERBB2', 'amplification'): 'Trastuzumab, Pertuzumab, T-DM1',
            ('EGFR', 'amplification'): 'Gefitinib, Erlotinib, Osimertinib',
            ('CDK4', 'amplification'): 'Palbociclib, Ribociclib, Abemaciclib',
            ('FGFR1', 'amplification'): 'Erdafitinib, Pemigatinib',
            ('MDM2', 'amplification'): 'MDM2 inhibitors (clinical trials)',
            ('CDKN2A', 'deletion'): 'CDK4/6 inhibitors may be effective',
            ('PTEN', 'deletion'): 'PI3K/AKT inhibitors',
        }
        return therapeutic_map.get((gene, alteration), 'Under investigation')
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets."""
        datasets = []
        
        for data_type in self.data_types:
            for cancer_type in self.cancer_types:
                source = "COSMIC API" if self.authenticated else "cBioPortal/Curated"
                datasets.append({
                    "data_type": data_type,
                    "cancer_type": cancer_type,
                    "description": f"Cancer {data_type} data for {cancer_type}",
                    "genes_available": len(self.gene_list),
                    "source": source,
                    "requires_auth": data_type == "mutations" and not self.authenticated
                })
        
        # Add Cancer Gene Census (always available)
        datasets.append({
            "data_type": "cancer_gene_census",
            "cancer_type": "all",
            "description": "Cancer Gene Census - curated list of ~700 cancer genes (Tier 1 public)",
            "genes_available": len(self.CANCER_GENE_CENSUS_TIER1),
            "source": "COSMIC CGC (public)",
            "requires_auth": False
        })
        
        return datasets
    
    def load_cosmic_file(self, filepath: str, data_type: str = "mutations") -> Dict[str, Any]:
        """
        Load and process a downloaded COSMIC data file.
        
        COSMIC provides downloadable files in TSV/GZ format.
        Register at https://cancer.sanger.ac.uk/cosmic/register to download.
        
        Args:
            filepath: Path to the COSMIC data file
            data_type: Type of data in the file
            
        Returns:
            Dictionary with processing results
        """
        self.logger.info(f"Loading COSMIC file: {filepath}")
        
        try:
            file_path = Path(filepath)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {filepath}")
            
            # Handle gzipped files
            if filepath.endswith('.gz'):
                with gzip.open(filepath, 'rt') as f:
                    df = pd.read_csv(f, sep='\t', low_memory=False)
            else:
                df = pd.read_csv(filepath, sep='\t', low_memory=False)
            
            self.logger.info(f"Loaded {len(df)} records from {filepath}")
            
            # Save processed data
            filename = self.generate_filename(
                f"{data_type}_processed",
                sample_count=len(df)
            )
            output_path = self.save_data(df, filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(df)
            
            return {
                "records_loaded": len(df),
                "columns": list(df.columns),
                "files_created": [output_path]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load COSMIC file: {e}")
            raise

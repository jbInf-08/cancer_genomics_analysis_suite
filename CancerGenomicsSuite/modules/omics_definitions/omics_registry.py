"""
Omics Field Registry

This module defines the comprehensive registry of all omics fields with their metadata,
data structures, processing requirements, and analysis capabilities.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable
import json
import logging

logger = logging.getLogger(__name__)


class OmicsDataType(Enum):
    """Enumeration of omics data types."""
    SEQUENCE = "sequence"
    EXPRESSION = "expression"
    ABUNDANCE = "abundance"
    INTERACTION = "interaction"
    STRUCTURE = "structure"
    MODIFICATION = "modification"
    METABOLITE = "metabolite"
    NETWORK = "network"
    PHENOTYPE = "phenotype"
    EXPOSURE = "exposure"
    FLUX = "flux"
    KINETIC = "kinetic"


class OmicsAnalysisType(Enum):
    """Enumeration of omics analysis types."""
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    COMPARATIVE = "comparative"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    NETWORK = "network"
    PATHWAY = "pathway"
    CORRELATION = "correlation"
    PREDICTION = "prediction"


@dataclass
class OmicsFieldDefinition:
    """Definition of an omics field with all its metadata and capabilities."""
    
    # Basic information
    name: str
    full_name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    
    # Data characteristics
    data_type: OmicsDataType = OmicsDataType.EXPRESSION
    analysis_types: List[OmicsAnalysisType] = field(default_factory=list)
    
    # Data structure information
    primary_entities: List[str] = field(default_factory=list)  # e.g., genes, proteins, metabolites
    measurement_units: List[str] = field(default_factory=list)  # e.g., FPKM, counts, ppm
    data_formats: List[str] = field(default_factory=list)  # e.g., FASTQ, VCF, CSV
    
    # Processing requirements
    preprocessing_steps: List[str] = field(default_factory=list)
    normalization_methods: List[str] = field(default_factory=list)
    quality_control_metrics: List[str] = field(default_factory=list)
    
    # Analysis capabilities
    supported_analyses: List[str] = field(default_factory=list)
    integration_methods: List[str] = field(default_factory=list)
    visualization_types: List[str] = field(default_factory=list)
    
    # Dependencies and tools
    required_tools: List[str] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    
    # Metadata
    complexity_level: str = "intermediate"  # basic, intermediate, advanced
    maturity_level: str = "established"  # emerging, developing, established, mature
    clinical_relevance: str = "high"  # low, medium, high, critical
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)


class OmicsFieldRegistry:
    """Central registry for all omics field definitions."""
    
    def __init__(self):
        """Initialize the omics field registry."""
        self.fields: Dict[str, OmicsFieldDefinition] = {}
        self._initialize_core_omics()
        self._initialize_structural_functional_omics()
        self._initialize_specialized_omics()
        self._initialize_microbiome_environmental_omics()
        self._initialize_emerging_omics()
        
    def _initialize_core_omics(self):
        """Initialize core genomics-related omics fields."""
        
        # Genomics
        self.fields['genomics'] = OmicsFieldDefinition(
            name='genomics',
            full_name='Genomics',
            description='Study of complete DNA sequences and genetic material',
            category='Core Genomics',
            data_type=OmicsDataType.SEQUENCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE],
            primary_entities=['genes', 'genomes', 'chromosomes', 'variants'],
            measurement_units=['bp', 'coverage', 'allele_frequency'],
            data_formats=['FASTA', 'FASTQ', 'VCF', 'BAM', 'CRAM'],
            preprocessing_steps=['quality_control', 'alignment', 'variant_calling'],
            normalization_methods=['coverage_normalization', 'gc_bias_correction'],
            quality_control_metrics=['coverage_depth', 'mapping_rate', 'duplicate_rate'],
            supported_analyses=['variant_analysis', 'structural_variation', 'copy_number'],
            integration_methods=['genomic_coordinates', 'gene_annotation'],
            visualization_types=['genome_browser', 'circos_plot', 'manhattan_plot'],
            required_tools=['BWA', 'GATK', 'SAMtools', 'BCFtools'],
            data_sources=['TCGA', 'ICGC', '1000_Genomes', 'gnomAD'],
            clinical_relevance='critical'
        )
        
        # Transcriptomics
        self.fields['transcriptomics'] = OmicsFieldDefinition(
            name='transcriptomics',
            full_name='Transcriptomics',
            description='Study of RNA transcripts and gene expression',
            category='Core Genomics',
            data_type=OmicsDataType.EXPRESSION,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['genes', 'transcripts', 'exons', 'isoforms'],
            measurement_units=['FPKM', 'TPM', 'RPKM', 'counts', 'CPM'],
            data_formats=['FASTQ', 'BAM', 'GTF', 'GFF3', 'CSV'],
            preprocessing_steps=['quality_control', 'alignment', 'quantification'],
            normalization_methods=['TMM', 'DESeq2', 'quantile', 'upper_quartile'],
            quality_control_metrics=['mapping_rate', 'duplicate_rate', 'strand_bias'],
            supported_analyses=['differential_expression', 'pathway_analysis', 'splicing_analysis'],
            integration_methods=['gene_symbols', 'pathway_mapping', 'transcription_factors'],
            visualization_types=['heatmap', 'volcano_plot', 'ma_plot', 'pathway_diagram'],
            required_tools=['STAR', 'HISAT2', 'Salmon', 'Kallisto', 'DESeq2'],
            data_sources=['TCGA', 'GEO', 'GTEx', 'ENCODE'],
            clinical_relevance='critical'
        )
        
        # Proteomics
        self.fields['proteomics'] = OmicsFieldDefinition(
            name='proteomics',
            full_name='Proteomics',
            description='Study of proteins and protein expression',
            category='Core Genomics',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.STRUCTURE],
            primary_entities=['proteins', 'peptides', 'protein_complexes'],
            measurement_units=['intensity', 'abundance', 'fold_change', 'spectral_count'],
            data_formats=['mzML', 'mzXML', 'RAW', 'CSV', 'FASTA'],
            preprocessing_steps=['peak_detection', 'feature_alignment', 'quantification'],
            normalization_methods=['median_normalization', 'quantile', 'loess'],
            quality_control_metrics=['missing_values', 'coefficient_variation', 'reproducibility'],
            supported_analyses=['differential_protein', 'pathway_analysis', 'protein_networks'],
            integration_methods=['protein_gene_mapping', 'pathway_databases', 'protein_interactions'],
            visualization_types=['heatmap', 'volcano_plot', 'protein_network', 'pathway_diagram'],
            required_tools=['MaxQuant', 'ProteomeDiscoverer', 'Skyline', 'Perseus'],
            data_sources=['CPTAC', 'PRIDE', 'ProteomeXchange', 'Human_Proteome'],
            clinical_relevance='high'
        )
        
        # Metabolomics
        self.fields['metabolomics'] = OmicsFieldDefinition(
            name='metabolomics',
            full_name='Metabolomics',
            description='Study of metabolites and metabolic processes',
            category='Core Genomics',
            data_type=OmicsDataType.METABOLITE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.PATHWAY],
            primary_entities=['metabolites', 'metabolic_pathways', 'enzymes'],
            measurement_units=['intensity', 'concentration', 'ppm', 'fold_change'],
            data_formats=['mzML', 'mzXML', 'CSV', 'NMR_fid', 'CDF'],
            preprocessing_steps=['peak_detection', 'alignment', 'normalization', 'identification'],
            normalization_methods=['median_normalization', 'quantile', 'pqn', 'is'],
            quality_control_metrics=['missing_values', 'rsd', 'batch_effects'],
            supported_analyses=['metabolic_profiling', 'pathway_analysis', 'biomarker_discovery'],
            integration_methods=['metabolite_pathway_mapping', 'enzyme_gene_mapping'],
            visualization_types=['heatmap', 'pca_plot', 'pathway_diagram', 'metabolite_network'],
            required_tools=['XCMS', 'MetaboAnalyst', 'MZmine', 'OpenMS'],
            data_sources=['HMDB', 'KEGG', 'MetaboLights', 'GNPS'],
            clinical_relevance='high'
        )
        
        # Epigenomics
        self.fields['epigenomics'] = OmicsFieldDefinition(
            name='epigenomics',
            full_name='Epigenomics',
            description='Study of epigenetic modifications (DNA methylation, histone modifications)',
            category='Core Genomics',
            data_type=OmicsDataType.MODIFICATION,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.SPATIAL],
            primary_entities=['cpg_sites', 'histone_marks', 'chromatin_regions'],
            measurement_units=['beta_value', 'm_value', 'coverage', 'enrichment'],
            data_formats=['IDAT', 'BED', 'BIGWIG', 'CSV', 'VCF'],
            preprocessing_steps=['quality_control', 'normalization', 'background_correction'],
            normalization_methods=['ssnoob', 'dasen', 'quantile', 'funnorm'],
            quality_control_metrics=['detection_pvalue', 'bisulfite_conversion', 'dye_bias'],
            supported_analyses=['differential_methylation', 'region_analysis', 'chromatin_analysis'],
            integration_methods=['genomic_coordinates', 'gene_annotation', 'chromatin_states'],
            visualization_types=['manhattan_plot', 'heatmap', 'track_viewer', 'circos_plot'],
            required_tools=['minfi', 'ChAMP', 'MethylKit', 'Bismark'],
            data_sources=['TCGA', 'ENCODE', 'Roadmap', 'GEO'],
            clinical_relevance='high'
        )
    
    def _initialize_structural_functional_omics(self):
        """Initialize structural and functional omics fields."""
        
        # Connectomics
        self.fields['connectomics'] = OmicsFieldDefinition(
            name='connectomics',
            full_name='Connectomics',
            description='Study of neural connections and brain connectivity',
            category='Structural and Functional',
            data_type=OmicsDataType.NETWORK,
            analysis_types=[OmicsAnalysisType.NETWORK, OmicsAnalysisType.SPATIAL, OmicsAnalysisType.COMPARATIVE],
            primary_entities=['neurons', 'synapses', 'brain_regions', 'neural_pathways'],
            measurement_units=['connection_strength', 'path_length', 'clustering_coefficient'],
            data_formats=['SWC', 'NIFTI', 'DICOM', 'JSON', 'CSV'],
            preprocessing_steps=['image_preprocessing', 'tractography', 'network_construction'],
            normalization_methods=['z_score', 'min_max', 'percentile'],
            quality_control_metrics=['signal_to_noise', 'motion_artifacts', 'connectivity_reliability'],
            supported_analyses=['network_analysis', 'graph_theory', 'connectivity_mapping'],
            integration_methods=['atlas_mapping', 'functional_connectivity', 'structural_connectivity'],
            visualization_types=['brain_network', 'connectivity_matrix', 'graph_visualization'],
            required_tools=['FSL', 'AFNI', 'SPM', 'Connectome_Workbench'],
            data_sources=['Human_Connectome', 'UK_Biobank', 'ABCD_Study'],
            clinical_relevance='medium'
        )
        
        # Interactomics
        self.fields['interactomics'] = OmicsFieldDefinition(
            name='interactomics',
            full_name='Interactomics',
            description='Study of molecular interactions (protein-protein, protein-DNA, etc.)',
            category='Structural and Functional',
            data_type=OmicsDataType.INTERACTION,
            analysis_types=[OmicsAnalysisType.NETWORK, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.PATHWAY],
            primary_entities=['proteins', 'dna', 'rna', 'metabolites', 'interaction_pairs'],
            measurement_units=['binding_affinity', 'confidence_score', 'interaction_strength'],
            data_formats=['PSI_MI', 'BIOGRID', 'CSV', 'JSON', 'XML'],
            preprocessing_steps=['interaction_filtering', 'confidence_scoring', 'network_construction'],
            normalization_methods=['confidence_normalization', 'frequency_normalization'],
            quality_control_metrics=['interaction_confidence', 'experimental_evidence', 'coverage'],
            supported_analyses=['network_analysis', 'module_detection', 'pathway_enrichment'],
            integration_methods=['protein_annotation', 'pathway_databases', 'functional_annotation'],
            visualization_types=['interaction_network', 'heatmap', 'pathway_diagram'],
            required_tools=['Cytoscape', 'STRING', 'IntAct', 'BioGRID'],
            data_sources=['STRING', 'BioGRID', 'IntAct', 'MINT', 'DIP'],
            clinical_relevance='high'
        )
        
        # Secretomics
        self.fields['secretomics'] = OmicsFieldDefinition(
            name='secretomics',
            full_name='Secretomics',
            description='Study of secreted proteins and molecules',
            category='Structural and Functional',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['secreted_proteins', 'cytokines', 'hormones', 'extracellular_vesicles'],
            measurement_units=['concentration', 'abundance', 'secretion_rate'],
            data_formats=['CSV', 'mzML', 'ELISA_data', 'Luminex_data'],
            preprocessing_steps=['sample_preparation', 'concentration_measurement', 'normalization'],
            normalization_methods=['protein_concentration', 'cell_count', 'volume_normalization'],
            quality_control_metrics=['detection_limit', 'reproducibility', 'linearity'],
            supported_analyses=['secretome_profiling', 'biomarker_discovery', 'pathway_analysis'],
            integration_methods=['protein_annotation', 'pathway_mapping', 'disease_association'],
            visualization_types=['heatmap', 'volcano_plot', 'pathway_diagram', 'network_plot'],
            required_tools=['MaxQuant', 'ProteomeDiscoverer', 'Cytoscape', 'STRING'],
            data_sources=['SecretedProteinDB', 'ExoCarta', 'Vesiclepedia'],
            clinical_relevance='high'
        )
        
        # Degradomics
        self.fields['degradomics'] = OmicsFieldDefinition(
            name='degradomics',
            full_name='Degradomics',
            description='Study of protein degradation and proteases',
            category='Structural and Functional',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.KINETIC, OmicsAnalysisType.COMPARATIVE],
            primary_entities=['proteases', 'substrates', 'degradation_products', 'protease_inhibitors'],
            measurement_units=['activity', 'degradation_rate', 'half_life', 'cleavage_efficiency'],
            data_formats=['CSV', 'mzML', 'activity_data', 'kinetic_data'],
            preprocessing_steps=['activity_assay', 'substrate_identification', 'kinetic_analysis'],
            normalization_methods=['time_normalization', 'concentration_normalization'],
            quality_control_metrics=['activity_reproducibility', 'substrate_specificity', 'kinetic_parameters'],
            supported_analyses=['protease_profiling', 'substrate_identification', 'kinetic_modeling'],
            integration_methods=['protease_annotation', 'substrate_mapping', 'pathway_analysis'],
            visualization_types=['activity_heatmap', 'kinetic_curves', 'substrate_network'],
            required_tools=['MEROPS', 'CutDB', 'Proteasix', 'MaxQuant'],
            data_sources=['MEROPS', 'CutDB', 'Proteasix', 'UniProt'],
            clinical_relevance='medium'
        )
        
        # Glycomics
        self.fields['glycomics'] = OmicsFieldDefinition(
            name='glycomics',
            full_name='Glycomics',
            description='Study of carbohydrates and glycan structures',
            category='Structural and Functional',
            data_type=OmicsDataType.STRUCTURE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.STRUCTURE, OmicsAnalysisType.COMPARATIVE],
            primary_entities=['glycans', 'glycoproteins', 'glycolipids', 'sugars'],
            measurement_units=['abundance', 'relative_intensity', 'composition'],
            data_formats=['CSV', 'mzML', 'glycan_notation', 'JSON'],
            preprocessing_steps=['glycan_release', 'derivatization', 'separation', 'identification'],
            normalization_methods=['internal_standard', 'total_ion_current', 'relative_abundance'],
            quality_control_metrics=['reproducibility', 'identification_confidence', 'coverage'],
            supported_analyses=['glycan_profiling', 'structural_analysis', 'biomarker_discovery'],
            integration_methods=['protein_glycan_mapping', 'pathway_analysis', 'disease_association'],
            visualization_types=['glycan_structures', 'heatmap', 'pathway_diagram', 'network_plot'],
            required_tools=['GlycoWorkbench', 'GlycoMod', 'GlycoPeakfinder', 'MassLynx'],
            data_sources=['GlyTouCan', 'UniCarbKB', 'GlycomeDB', 'CFG'],
            clinical_relevance='medium'
        )
        
        # Lipidomics
        self.fields['lipidomics'] = OmicsFieldDefinition(
            name='lipidomics',
            full_name='Lipidomics',
            description='Study of lipids and lipid metabolism',
            category='Structural and Functional',
            data_type=OmicsDataType.METABOLITE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.PATHWAY],
            primary_entities=['lipids', 'fatty_acids', 'sterols', 'phospholipids'],
            measurement_units=['concentration', 'abundance', 'molar_ratio'],
            data_formats=['CSV', 'mzML', 'lipid_notation', 'JSON'],
            preprocessing_steps=['lipid_extraction', 'separation', 'identification', 'quantification'],
            normalization_methods=['internal_standard', 'total_lipid', 'protein_normalization'],
            quality_control_metrics=['reproducibility', 'identification_confidence', 'recovery_rate'],
            supported_analyses=['lipid_profiling', 'metabolic_pathway_analysis', 'biomarker_discovery'],
            integration_methods=['lipid_pathway_mapping', 'metabolite_networks', 'disease_association'],
            visualization_types=['lipid_structures', 'heatmap', 'pathway_diagram', 'network_plot'],
            required_tools=['LipidBlast', 'LipidXplorer', 'LipidMatch', 'Skyline'],
            data_sources=['LIPIDMAPS', 'LipidBlast', 'LipidHome', 'HMDB'],
            clinical_relevance='high'
        )
    
    def _initialize_specialized_omics(self):
        """Initialize specialized omics fields."""
        
        # Pharmacogenomics
        self.fields['pharmacogenomics'] = OmicsFieldDefinition(
            name='pharmacogenomics',
            full_name='Pharmacogenomics',
            description='Study of genetic factors affecting drug responses',
            category='Specialized Omics',
            data_type=OmicsDataType.SEQUENCE,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.PREDICTION, OmicsAnalysisType.CORRELATION],
            primary_entities=['drug_targets', 'pharmacogenes', 'variants', 'drug_response'],
            measurement_units=['ic50', 'ec50', 'fold_change', 'response_rate'],
            data_formats=['VCF', 'CSV', 'JSON', 'XML'],
            preprocessing_steps=['variant_annotation', 'drug_response_association', 'statistical_analysis'],
            normalization_methods=['dose_response_normalization', 'population_normalization'],
            quality_control_metrics=['response_reproducibility', 'variant_quality', 'statistical_power'],
            supported_analyses=['drug_response_prediction', 'biomarker_discovery', 'dose_optimization'],
            integration_methods=['drug_databases', 'variant_databases', 'clinical_data'],
            visualization_types=['manhattan_plot', 'forest_plot', 'dose_response_curve'],
            required_tools=['PharmGKB', 'CPIC', 'PharmVar', 'PLINK'],
            data_sources=['PharmGKB', 'CPIC', 'PharmVar', 'ClinVar'],
            clinical_relevance='critical'
        )
        
        # Nutrigenomics
        self.fields['nutrigenomics'] = OmicsFieldDefinition(
            name='nutrigenomics',
            full_name='Nutrigenomics',
            description='Study of gene-nutrition interactions',
            category='Specialized Omics',
            data_type=OmicsDataType.EXPRESSION,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.CORRELATION, OmicsAnalysisType.TEMPORAL],
            primary_entities=['genes', 'nutrients', 'metabolites', 'dietary_components'],
            measurement_units=['expression_fold_change', 'nutrient_concentration', 'metabolite_levels'],
            data_formats=['CSV', 'VCF', 'JSON', 'XML'],
            preprocessing_steps=['diet_assessment', 'gene_expression_analysis', 'metabolite_profiling'],
            normalization_methods=['nutrient_normalization', 'expression_normalization'],
            quality_control_metrics=['diet_compliance', 'expression_reproducibility', 'metabolite_quality'],
            supported_analyses=['nutrient_gene_interaction', 'metabolic_pathway_analysis', 'biomarker_discovery'],
            integration_methods=['nutrient_databases', 'gene_annotation', 'metabolite_networks'],
            visualization_types=['interaction_network', 'heatmap', 'pathway_diagram'],
            required_tools=['NutriGenomeDB', 'FoodDB', 'KEGG', 'Reactome'],
            data_sources=['NutriGenomeDB', 'FoodDB', 'USDA', 'KEGG'],
            clinical_relevance='medium'
        )
        
        # Toxicogenomics
        self.fields['toxicogenomics'] = OmicsFieldDefinition(
            name='toxicogenomics',
            full_name='Toxicogenomics',
            description='Study of genetic responses to toxic substances',
            category='Specialized Omics',
            data_type=OmicsDataType.EXPRESSION,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL, OmicsAnalysisType.DOSE_RESPONSE],
            primary_entities=['genes', 'toxins', 'pathways', 'biomarkers'],
            measurement_units=['expression_fold_change', 'toxin_concentration', 'dose_response'],
            data_formats=['CSV', 'VCF', 'JSON', 'XML'],
            preprocessing_steps=['toxin_exposure_assessment', 'gene_expression_analysis', 'dose_response_modeling'],
            normalization_methods=['dose_normalization', 'time_normalization', 'expression_normalization'],
            quality_control_metrics=['exposure_accuracy', 'expression_reproducibility', 'dose_response_fit'],
            supported_analyses=['toxicity_prediction', 'biomarker_discovery', 'mechanism_analysis'],
            integration_methods=['toxin_databases', 'pathway_analysis', 'biomarker_networks'],
            visualization_types=['dose_response_curve', 'heatmap', 'pathway_diagram'],
            required_tools=['CTD', 'ToxCast', 'Tox21', 'LINCS'],
            data_sources=['CTD', 'ToxCast', 'Tox21', 'LINCS'],
            clinical_relevance='high'
        )
        
        # Immunogenomics
        self.fields['immunogenomics'] = OmicsFieldDefinition(
            name='immunogenomics',
            full_name='Immunogenomics',
            description='Study of immune system genetics',
            category='Specialized Omics',
            data_type=OmicsDataType.SEQUENCE,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.NETWORK, OmicsAnalysisType.CORRELATION],
            primary_entities=['immune_genes', 'hla_alleles', 'tcr_bcr', 'immune_cells'],
            measurement_units=['allele_frequency', 'expression_level', 'cell_count'],
            data_formats=['VCF', 'CSV', 'FASTA', 'JSON'],
            preprocessing_steps=['hla_typing', 'tcr_bcr_analysis', 'immune_cell_quantification'],
            normalization_methods=['cell_count_normalization', 'allele_frequency_normalization'],
            quality_control_metrics=['typing_accuracy', 'cell_purity', 'reproducibility'],
            supported_analyses=['immune_profiling', 'hla_association', 'tcr_bcr_repertoire'],
            integration_methods=['immune_databases', 'hla_databases', 'cell_type_annotation'],
            visualization_types=['hla_network', 'tcr_network', 'immune_heatmap'],
            required_tools=['HLA-HD', 'MiXCR', 'TRUST4', 'Immcantation'],
            data_sources=['IPD-IMGT/HLA', 'VDJdb', 'IEDB', 'ImmPort'],
            clinical_relevance='high'
        )
        
        # Neurogenomics
        self.fields['neurogenomics'] = OmicsFieldDefinition(
            name='neurogenomics',
            full_name='Neurogenomics',
            description='Study of nervous system genetics',
            category='Specialized Omics',
            data_type=OmicsDataType.SEQUENCE,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.NETWORK, OmicsAnalysisType.SPATIAL],
            primary_entities=['neurons', 'glial_cells', 'neural_genes', 'brain_regions'],
            measurement_units=['expression_level', 'cell_count', 'connectivity_strength'],
            data_formats=['VCF', 'CSV', 'NIFTI', 'JSON'],
            preprocessing_steps=['brain_region_annotation', 'cell_type_identification', 'connectivity_analysis'],
            normalization_methods=['cell_count_normalization', 'region_normalization'],
            quality_control_metrics=['cell_purity', 'region_accuracy', 'connectivity_reliability'],
            supported_analyses=['neural_profiling', 'connectivity_analysis', 'disease_association'],
            integration_methods=['brain_atlases', 'neural_databases', 'connectivity_databases'],
            visualization_types=['brain_network', 'connectivity_matrix', 'neural_heatmap'],
            required_tools=['Allen_Brain_Atlas', 'Human_Connectome', 'BrainSpan', 'PsychENCODE'],
            data_sources=['Allen_Brain_Atlas', 'Human_Connectome', 'BrainSpan', 'PsychENCODE'],
            clinical_relevance='high'
        )
        
        # Pharmacoproteomics
        self.fields['pharmacoproteomics'] = OmicsFieldDefinition(
            name='pharmacoproteomics',
            full_name='Pharmacoproteomics',
            description='Study of protein changes in response to drugs',
            category='Specialized Omics',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL, OmicsAnalysisType.DOSE_RESPONSE],
            primary_entities=['proteins', 'drug_targets', 'pathways', 'protein_complexes'],
            measurement_units=['abundance_fold_change', 'drug_concentration', 'protein_activity'],
            data_formats=['mzML', 'CSV', 'JSON', 'XML'],
            preprocessing_steps=['drug_treatment', 'protein_extraction', 'quantification'],
            normalization_methods=['drug_dose_normalization', 'protein_concentration_normalization'],
            quality_control_metrics=['treatment_consistency', 'protein_reproducibility', 'dose_response'],
            supported_analyses=['drug_response_profiling', 'target_identification', 'mechanism_analysis'],
            integration_methods=['drug_databases', 'protein_networks', 'pathway_analysis'],
            visualization_types=['protein_heatmap', 'pathway_diagram', 'dose_response_curve'],
            required_tools=['MaxQuant', 'ProteomeDiscoverer', 'STRING', 'Reactome'],
            data_sources=['DrugBank', 'ChEMBL', 'UniProt', 'Reactome'],
            clinical_relevance='high'
        )
    
    def _initialize_microbiome_environmental_omics(self):
        """Initialize microbiome and environmental omics fields."""
        
        # Metagenomics
        self.fields['metagenomics'] = OmicsFieldDefinition(
            name='metagenomics',
            full_name='Metagenomics',
            description='Study of genetic material from environmental samples',
            category='Microbiome and Environmental',
            data_type=OmicsDataType.SEQUENCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['microorganisms', 'genes', 'pathways', 'taxonomic_groups'],
            measurement_units=['relative_abundance', 'absolute_abundance', 'coverage'],
            data_formats=['FASTQ', 'FASTA', 'SAM', 'VCF'],
            preprocessing_steps=['quality_control', 'host_contamination_removal', 'assembly'],
            normalization_methods=['rarefaction', 'css', 'tss', 'clr'],
            quality_control_metrics=['read_quality', 'contamination_rate', 'assembly_quality'],
            supported_analyses=['taxonomic_profiling', 'functional_annotation', 'diversity_analysis'],
            integration_methods=['taxonomic_databases', 'functional_databases', 'environmental_metadata'],
            visualization_types=['taxonomic_heatmap', 'diversity_plot', 'functional_heatmap'],
            required_tools=['QIIME2', 'MOTHUR', 'MetaPhlAn', 'HUMAnN'],
            data_sources=['MG-RAST', 'EBI_Metagenomics', 'NCBI_SRA', 'IMG/M'],
            clinical_relevance='high'
        )
        
        # Microbiomics
        self.fields['microbiomics'] = OmicsFieldDefinition(
            name='microbiomics',
            full_name='Microbiomics',
            description='Study of microbial communities',
            category='Microbiome and Environmental',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['microbes', 'microbial_communities', 'ecological_guilds'],
            measurement_units=['relative_abundance', 'absolute_abundance', 'diversity_index'],
            data_formats=['CSV', 'BIOM', 'FASTA', 'FASTQ'],
            preprocessing_steps=['community_analysis', 'diversity_calculation', 'compositional_analysis'],
            normalization_methods=['rarefaction', 'css', 'tss', 'clr'],
            quality_control_metrics=['community_stability', 'diversity_reproducibility', 'composition_accuracy'],
            supported_analyses=['community_profiling', 'diversity_analysis', 'ecological_analysis'],
            integration_methods=['taxonomic_databases', 'ecological_databases', 'environmental_metadata'],
            visualization_types=['community_heatmap', 'diversity_plot', 'ecological_network'],
            required_tools=['QIIME2', 'MOTHUR', 'phyloseq', 'vegan'],
            data_sources=['MG-RAST', 'EBI_Metagenomics', 'NCBI_SRA', 'Earth_Microbiome'],
            clinical_relevance='high'
        )
        
        # Exposomics
        self.fields['exposomics'] = OmicsFieldDefinition(
            name='exposomics',
            full_name='Exposomics',
            description='Study of environmental exposures and their biological effects',
            category='Microbiome and Environmental',
            data_type=OmicsDataType.EXPOSURE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.CORRELATION, OmicsAnalysisType.TEMPORAL],
            primary_entities=['environmental_factors', 'exposure_biomarkers', 'biological_responses'],
            measurement_units=['exposure_concentration', 'biomarker_level', 'effect_size'],
            data_formats=['CSV', 'JSON', 'XML', 'GIS_data'],
            preprocessing_steps=['exposure_assessment', 'biomarker_measurement', 'temporal_alignment'],
            normalization_methods=['exposure_normalization', 'biomarker_normalization', 'temporal_normalization'],
            quality_control_metrics=['exposure_accuracy', 'biomarker_reproducibility', 'temporal_consistency'],
            supported_analyses=['exposure_profiling', 'biomarker_discovery', 'effect_assessment'],
            integration_methods=['exposure_databases', 'biomarker_databases', 'environmental_models'],
            visualization_types=['exposure_heatmap', 'biomarker_plot', 'temporal_plot'],
            required_tools=['Exposome-Explorer', 'HELIX', 'EXPOsOMICS', 'GIS_tools'],
            data_sources=['Exposome-Explorer', 'HELIX', 'EXPOsOMICS', 'NHANES'],
            clinical_relevance='high'
        )
    
    def _initialize_emerging_omics(self):
        """Initialize emerging and specialized omics fields."""
        
        # Fluxomics
        self.fields['fluxomics'] = OmicsFieldDefinition(
            name='fluxomics',
            full_name='Fluxomics',
            description='Study of metabolic flux rates',
            category='Emerging and Specialized',
            data_type=OmicsDataType.FLUX,
            analysis_types=[OmicsAnalysisType.KINETIC, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['metabolic_fluxes', 'enzymes', 'metabolites', 'pathways'],
            measurement_units=['flux_rate', 'turnover_rate', 'flux_ratio'],
            data_formats=['CSV', 'JSON', 'SBML', 'XML'],
            preprocessing_steps=['flux_measurement', 'model_construction', 'flux_estimation'],
            normalization_methods=['flux_normalization', 'biomass_normalization'],
            quality_control_metrics=['flux_accuracy', 'model_validation', 'reproducibility'],
            supported_analyses=['flux_profiling', 'pathway_analysis', 'metabolic_modeling'],
            integration_methods=['metabolic_models', 'pathway_databases', 'enzyme_databases'],
            visualization_types=['flux_heatmap', 'pathway_diagram', 'flux_network'],
            required_tools=['COBRApy', 'FBA', 'MOMA', 'FVA'],
            data_sources=['BiGG', 'KEGG', 'Reactome', 'MetaCyc'],
            clinical_relevance='medium'
        )
        
        # Phenomics
        self.fields['phenomics'] = OmicsFieldDefinition(
            name='phenomics',
            full_name='Phenomics',
            description='Study of phenotypes on a large scale',
            category='Emerging and Specialized',
            data_type=OmicsDataType.PHENOTYPE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.CORRELATION],
            primary_entities=['phenotypes', 'traits', 'diseases', 'clinical_measurements'],
            measurement_units=['phenotype_score', 'trait_value', 'disease_severity'],
            data_formats=['CSV', 'JSON', 'XML', 'HL7_FHIR'],
            preprocessing_steps=['phenotype_extraction', 'trait_quantification', 'normalization'],
            normalization_methods=['population_normalization', 'age_sex_normalization'],
            quality_control_metrics=['phenotype_accuracy', 'trait_reproducibility', 'measurement_consistency'],
            supported_analyses=['phenotype_profiling', 'trait_association', 'disease_prediction'],
            integration_methods=['phenotype_databases', 'trait_databases', 'clinical_databases'],
            visualization_types=['phenotype_heatmap', 'trait_plot', 'disease_network'],
            required_tools=['PhenX', 'HPO', 'OMIM', 'ClinVar'],
            data_sources=['PhenX', 'HPO', 'OMIM', 'ClinVar', 'UK_Biobank'],
            clinical_relevance='critical'
        )
        
        # Kinomics
        self.fields['kinomics'] = OmicsFieldDefinition(
            name='kinomics',
            full_name='Kinomics',
            description='Study of protein kinases and kinase activity',
            category='Emerging and Specialized',
            data_type=OmicsDataType.ABUNDANCE,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.KINETIC, OmicsAnalysisType.COMPARATIVE],
            primary_entities=['kinases', 'substrates', 'phosphorylation_sites', 'kinase_inhibitors'],
            measurement_units=['kinase_activity', 'phosphorylation_level', 'inhibition_ic50'],
            data_formats=['CSV', 'mzML', 'JSON', 'XML'],
            preprocessing_steps=['kinase_assay', 'substrate_identification', 'activity_measurement'],
            normalization_methods=['kinase_activity_normalization', 'substrate_normalization'],
            quality_control_metrics=['activity_reproducibility', 'substrate_specificity', 'inhibition_accuracy'],
            supported_analyses=['kinase_profiling', 'substrate_identification', 'inhibitor_screening'],
            integration_methods=['kinase_databases', 'substrate_databases', 'inhibitor_databases'],
            visualization_types=['kinase_heatmap', 'substrate_network', 'inhibitor_plot'],
            required_tools=['KinasePhos', 'PhosphoSitePlus', 'KEGG', 'Reactome'],
            data_sources=['KinasePhos', 'PhosphoSitePlus', 'KEGG', 'Reactome'],
            clinical_relevance='high'
        )
        
        # Phosphoproteomics
        self.fields['phosphoproteomics'] = OmicsFieldDefinition(
            name='phosphoproteomics',
            full_name='Phosphoproteomics',
            description='Study of protein phosphorylation',
            category='Emerging and Specialized',
            data_type=OmicsDataType.MODIFICATION,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['phosphoproteins', 'phosphorylation_sites', 'kinases', 'phosphatases'],
            measurement_units=['phosphorylation_level', 'site_occupancy', 'fold_change'],
            data_formats=['mzML', 'CSV', 'JSON', 'XML'],
            preprocessing_steps=['phosphopeptide_enrichment', 'identification', 'quantification'],
            normalization_methods=['phosphorylation_normalization', 'protein_normalization'],
            quality_control_metrics=['enrichment_efficiency', 'identification_confidence', 'quantification_accuracy'],
            supported_analyses=['phosphorylation_profiling', 'kinase_analysis', 'pathway_analysis'],
            integration_methods=['phosphorylation_databases', 'kinase_databases', 'pathway_databases'],
            visualization_types=['phosphorylation_heatmap', 'kinase_network', 'pathway_diagram'],
            required_tools=['MaxQuant', 'ProteomeDiscoverer', 'PhosphoSitePlus', 'KinasePhos'],
            data_sources=['PhosphoSitePlus', 'KinasePhos', 'UniProt', 'Reactome'],
            clinical_relevance='high'
        )
        
        # Ubiquitomics
        self.fields['ubiquitomics'] = OmicsFieldDefinition(
            name='ubiquitomics',
            full_name='Ubiquitomics',
            description='Study of ubiquitin modifications',
            category='Emerging and Specialized',
            data_type=OmicsDataType.MODIFICATION,
            analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['ubiquitinated_proteins', 'ubiquitin_sites', 'ubiquitin_ligases', 'deubiquitinases'],
            measurement_units=['ubiquitination_level', 'site_occupancy', 'fold_change'],
            data_formats=['mzML', 'CSV', 'JSON', 'XML'],
            preprocessing_steps=['ubiquitin_enrichment', 'identification', 'quantification'],
            normalization_methods=['ubiquitination_normalization', 'protein_normalization'],
            quality_control_metrics=['enrichment_efficiency', 'identification_confidence', 'quantification_accuracy'],
            supported_analyses=['ubiquitination_profiling', 'ligase_analysis', 'pathway_analysis'],
            integration_methods=['ubiquitination_databases', 'ligase_databases', 'pathway_databases'],
            visualization_types=['ubiquitination_heatmap', 'ligase_network', 'pathway_diagram'],
            required_tools=['MaxQuant', 'ProteomeDiscoverer', 'UbiquitinDB', 'UbPred'],
            data_sources=['UbiquitinDB', 'UbPred', 'UniProt', 'Reactome'],
            clinical_relevance='medium'
        )
        
        # Chromatomics
        self.fields['chromatomics'] = OmicsFieldDefinition(
            name='chromatomics',
            full_name='Chromatomics',
            description='Study of chromatin structure and organization',
            category='Emerging and Specialized',
            data_type=OmicsDataType.STRUCTURE,
            analysis_types=[OmicsAnalysisType.SPATIAL, OmicsAnalysisType.COMPARATIVE, OmicsAnalysisType.TEMPORAL],
            primary_entities=['chromatin_regions', 'histone_modifications', 'chromatin_loops', 'tads'],
            measurement_units=['contact_frequency', 'enrichment_score', 'loop_strength'],
            data_formats=['BED', 'BIGWIG', 'HIC', 'CSV'],
            preprocessing_steps=['contact_mapping', 'loop_calling', 'domain_identification'],
            normalization_methods=['contact_normalization', 'distance_normalization'],
            quality_control_metrics=['contact_quality', 'loop_confidence', 'domain_validation'],
            supported_analyses=['chromatin_profiling', 'loop_analysis', 'domain_analysis'],
            integration_methods=['chromatin_databases', 'histone_databases', 'transcription_databases'],
            visualization_types=['contact_heatmap', 'loop_plot', 'domain_plot'],
            required_tools=['HiC-Pro', 'Juicer', 'Cooler', 'HiCExplorer'],
            data_sources=['4D_Nucleome', 'ENCODE', 'Roadmap', 'GEO'],
            clinical_relevance='medium'
        )
        
        # Additional emerging omics fields
        additional_omics = [
            ('acetylomics', 'Acetylomics', 'Study of protein acetylation'),
            ('allergomics', 'Allergomics', 'Study of allergens and allergic responses'),
            ('bibliomics', 'Bibliomics', 'Study of scientific literature and publications'),
            ('cytomics', 'Cytomics', 'Study of cell populations and their properties'),
            ('editomics', 'Editomics', 'Study of RNA editing'),
            ('foodomics', 'Foodomics', 'Study of food composition and effects'),
            ('hologenomics', 'Hologenomics', 'Study of host and microbiome genomes together'),
            ('ionomics', 'Ionomics', 'Study of elemental composition'),
            ('membranomics', 'Membranomics', 'Study of membrane proteins and lipids'),
            ('metallomics', 'Metallomics', 'Study of metals in biological systems'),
            ('methylomics', 'Methylomics', 'Study of DNA methylation patterns'),
            ('obesomics', 'Obesomics', 'Study of obesity-related molecular changes'),
            ('organomics', 'Organomics', 'Study of organ-specific molecular profiles'),
            ('parvomics', 'Parvomics', 'Study of parvovirus genomes'),
            ('physiomics', 'Physiomics', 'Study of physiological processes'),
            ('regulomics', 'Regulomics', 'Study of gene regulation'),
            ('speechomics', 'Speechomics', 'Study of speech and language genetics'),
            ('synaptomics', 'Synaptomics', 'Study of synaptic proteins and functions'),
            ('synthetomics', 'Synthetomics', 'Study of synthetic biology systems'),
            ('toponomics', 'Toponomics', 'Study of spatial organization of molecules'),
            ('toxomics', 'Toxomics', 'Study of toxicological responses'),
            ('antibodyomics', 'Antibodyomics', 'Study of antibody repertoires'),
            ('embryomics', 'Embryomics', 'Study of embryonic development'),
            ('interferomics', 'Interferomics', 'Study of interferon responses'),
            ('mechanomics', 'Mechanomics', 'Study of mechanical properties of cells'),
            ('researchomics', 'Researchomics', 'Study of research methodologies'),
            ('trialomics', 'Trialomics', 'Study of clinical trial data'),
            ('dynomics', 'Dynomics', 'Study of dynamic molecular processes')
        ]
        
        for name, full_name, description in additional_omics:
            self.fields[name] = OmicsFieldDefinition(
                name=name,
                full_name=full_name,
                description=description,
                category='Emerging and Specialized',
                data_type=OmicsDataType.EXPRESSION,
                analysis_types=[OmicsAnalysisType.QUANTITATIVE, OmicsAnalysisType.COMPARATIVE],
                primary_entities=['molecules', 'processes', 'systems'],
                measurement_units=['abundance', 'activity', 'level'],
                data_formats=['CSV', 'JSON', 'XML'],
                preprocessing_steps=['data_processing', 'normalization', 'quality_control'],
                normalization_methods=['standard_normalization'],
                quality_control_metrics=['reproducibility', 'accuracy'],
                supported_analyses=['profiling', 'comparative_analysis'],
                integration_methods=['database_integration'],
                visualization_types=['heatmap', 'plot'],
                required_tools=['standard_tools'],
                data_sources=['public_databases'],
                clinical_relevance='medium',
                maturity_level='emerging'
            )
    
    def get_field(self, name: str) -> Optional[OmicsFieldDefinition]:
        """Get an omics field definition by name."""
        return self.fields.get(name.lower())
    
    def get_fields_by_category(self, category: str) -> List[OmicsFieldDefinition]:
        """Get all omics fields in a specific category."""
        return [field for field in self.fields.values() if field.category == category]
    
    def get_all_fields(self) -> Dict[str, OmicsFieldDefinition]:
        """Get all omics field definitions."""
        return self.fields.copy()
    
    def get_field_names(self) -> List[str]:
        """Get all omics field names."""
        return list(self.fields.keys())
    
    def get_categories(self) -> List[str]:
        """Get all omics categories."""
        return list(set(field.category for field in self.fields.values()))
    
    def search_fields(self, query: str) -> List[OmicsFieldDefinition]:
        """Search omics fields by name, description, or category."""
        query = query.lower()
        results = []
        for field in self.fields.values():
            if (query in field.name.lower() or 
                query in field.full_name.lower() or 
                query in field.description.lower() or 
                query in field.category.lower()):
                results.append(field)
        return results
    
    def export_definitions(self, file_path: str, format: str = 'json'):
        """Export omics field definitions to a file."""
        if format.lower() == 'json':
            with open(file_path, 'w') as f:
                json.dump({
                    name: {
                        'name': field.name,
                        'full_name': field.full_name,
                        'description': field.description,
                        'category': field.category,
                        'data_type': field.data_type.value,
                        'analysis_types': [t.value for t in field.analysis_types],
                        'primary_entities': field.primary_entities,
                        'measurement_units': field.measurement_units,
                        'data_formats': field.data_formats,
                        'preprocessing_steps': field.preprocessing_steps,
                        'normalization_methods': field.normalization_methods,
                        'quality_control_metrics': field.quality_control_metrics,
                        'supported_analyses': field.supported_analyses,
                        'integration_methods': field.integration_methods,
                        'visualization_types': field.visualization_types,
                        'required_tools': field.required_tools,
                        'data_sources': field.data_sources,
                        'complexity_level': field.complexity_level,
                        'maturity_level': field.maturity_level,
                        'clinical_relevance': field.clinical_relevance,
                        'properties': field.properties
                    }
                    for name, field in self.fields.items()
                }, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the omics field registry."""
        categories = {}
        data_types = {}
        maturity_levels = {}
        clinical_relevance = {}
        
        for field in self.fields.values():
            # Count by category
            categories[field.category] = categories.get(field.category, 0) + 1
            
            # Count by data type
            data_types[field.data_type.value] = data_types.get(field.data_type.value, 0) + 1
            
            # Count by maturity level
            maturity_levels[field.maturity_level] = maturity_levels.get(field.maturity_level, 0) + 1
            
            # Count by clinical relevance
            clinical_relevance[field.clinical_relevance] = clinical_relevance.get(field.clinical_relevance, 0) + 1
        
        return {
            'total_fields': len(self.fields),
            'categories': categories,
            'data_types': data_types,
            'maturity_levels': maturity_levels,
            'clinical_relevance': clinical_relevance
        }


# Global registry instance
omics_registry = OmicsFieldRegistry()


def get_omics_registry() -> OmicsFieldRegistry:
    """Get the global omics field registry instance."""
    return omics_registry

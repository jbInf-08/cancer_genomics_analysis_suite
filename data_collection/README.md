# Comprehensive Data Collection System

This directory contains a comprehensive data collection system for gathering biomarker data from **ALL** major biomedical data sources. The system includes individual collectors for each data source, a master orchestrator, and comprehensive testing and validation tools.

## 🎯 Overview

The data collection system provides:

- **127 Individual Data Collectors** for every major biomedical data source
- **Master Orchestrator** for coordinated data collection
- **Comprehensive Testing Suite** for validation
- **Configuration Management** for flexible data collection
- **Error Handling & Logging** for robust operation
- **Data Validation & Quality Control** for reliable results

## 📊 Supported Data Sources

### Genomic & Expression Data
- **TCGA** - The Cancer Genome Atlas
- **ICGC** - International Cancer Genome Consortium  
- **GEO** - Gene Expression Omnibus
- **EGA** - European Genome-phenome Archive
- **GDC** - Genomic Data Commons
- **NCBI** - National Center for Biotechnology Information

### Clinical & Registry Data
- **SEER** - Surveillance, Epidemiology, and End Results
- **NCDB** - National Cancer Database
- **CDC** - Center for Disease Control
- **NIH** - National Institute of Health
- **NCI** - National Cancer Institute
- **NIH Clinical Center** - Clinical datasets

### Imaging & Radiomics Data
- **TCIA** - The Cancer Imaging Archive
- **MICCAI** - Challenge datasets
- **Prostate-X** - Prostate cancer challenge
- **CAMELYON** - Histopathology challenges
- **PanCancer Atlas** - Pathology images
- **LIDC-IDRI** - Lung image database
- **NSCLC Radiogenomics** - Lung cancer datasets
- **Luna16** - Lung nodule challenge
- **BraTS** - Brain tumor segmentation
- **REMBRANDT** - Brain cancer database
- **TCIA Glioblastoma** - Brain cancer collections

### Skin & Dermatology Data
- **ISIC** - International Skin Imaging Collaboration
- **HAM10000** - Skin lesion dataset

### Breast Cancer Data
- **DDSM** - Digital Database for Screening Mammography
- **INbreast** - Mammography database
- **Wisconsin Breast Cancer** - UCI repository

### Mutation & Variant Data
- **COSMIC** - Catalogue of Somatic Mutations in Cancer
- **ClinVar** - Clinical variant database
- **OncoKB** - Cancer gene database

### Drug & Cell Line Data
- **CCLE** - Cancer Cell Line Encyclopedia
- **GDSC** - Genomics of Drug Sensitivity in Cancer
- **NCI-60** - Cancer Cell Line Panel

### Literature & Research Data
- **PubMed** - Biomedical literature
- **cBioPortal** - Cancer genomics portal
- **FireCloud/Terra** - Research platform
- **Google Cloud Healthcare** - Healthcare API

### Challenge & Competition Data
- **PathLAION** - Pathology data
- **MIMIC** - Clinical database
- **Kaggle** - Cancer datasets

## 🚀 Quick Start

### 1. Basic Usage

```python
from data_collection.run_data_collection import ComprehensiveDataCollector

# Initialize collector
collector = ComprehensiveDataCollector(
    output_dir="data/external_sources",
    config_file="data_collection/config.json"
)

# List available sources
sources = collector.get_available_sources()
print(f"Available sources: {[s['name'] for s in sources]}")

# Run comprehensive collection
results = collector.run_comprehensive_collection()
```

### 2. Command Line Usage

```bash
# List all available sources
python -m data_collection.run_data_collection --list-sources

# Run collection from specific sources
python -m data_collection.run_data_collection --sources TCGA GEO COSMIC

# Run with custom configuration
python -m data_collection.run_data_collection --config custom_config.json

# Run with specific data types
python -m data_collection.run_data_collection --data-types clinical expression mutation
```

### 3. Individual Collector Usage

```python
from data_collection.tcga_collector import TCGACollector

# Initialize TCGA collector
tcga = TCGACollector(output_dir="data/tcga")

# Collect gene expression data
results = tcga.collect_data(
    data_type="gene_expression",
    cancer_type="BRCA",
    sample_limit=100
)

print(f"Collected {results['samples_collected']} samples")
```

## 📁 Directory Structure

```
data_collection/
├── __init__.py
├── base_collector.py              # Base collector framework
├── master_orchestrator.py         # Master coordination system
├── run_data_collection.py         # Main runner script
├── test_all_collectors.py         # Testing suite
├── generate_all_collectors.py     # Collector generator
├── config.json                    # Configuration file
├── README.md                      # This file
│
├── Individual Collectors (86 files):
├── tcga_collector.py              # TCGA data collector
├── geo_collector.py               # GEO data collector
├── cosmic_collector.py            # COSMIC data collector
├── icgc_collector.py              # ICGC data collector
├── ega_collector.py               # EGA data collector
├── tcia_collector.py              # TCIA data collector
├── gdc_collector.py               # GDC data collector
├── cdc_collector.py               # CDC data collector
├── nih_collector.py               # NIH data collector
├── kaggle_collector.py            # Kaggle data collector
├── nci_collector.py               # NCI data collector
├── pubmed_collector.py            # PubMed data collector
├── ncbi_collector.py              # NCBI data collector
├── miccai_collector.py            # MICCAI data collector
├── nih_clinical_collector.py      # NIH Clinical data collector
├── prostate_x_collector.py        # Prostate-X data collector
├── pathlaion_collector.py         # PathLAION data collector
├── camelyon_collector.py          # CAMELYON data collector
├── pancancer_atlas_collector.py   # PanCancer Atlas data collector
├── seer_collector.py              # SEER data collector
├── ncdb_collector.py              # NCDB data collector
├── mimic_collector.py             # MIMIC data collector
├── wisconsin_breast_cancer_collector.py  # Wisconsin data collector
├── ddsm_collector.py              # DDSM data collector
├── inbreast_collector.py          # INbreast data collector
├── lidc_idri_collector.py         # LIDC-IDRI data collector
├── nsclc_radiogenomics_collector.py  # NSCLC data collector
├── luna16_collector.py            # Luna16 data collector
├── isic_collector.py              # ISIC data collector
├── ham10000_collector.py          # HAM10000 data collector
├── brats_collector.py             # BraTS data collector
├── rembrandt_collector.py         # REMBRANDT data collector
├── tcia_glioblastoma_collector.py # TCIA Glioblastoma data collector
├── clinvar_collector.py           # ClinVar data collector
├── oncokb_collector.py            # OncoKB data collector
├── cbioportal_collector.py        # cBioPortal data collector
├── firecloud_terra_collector.py   # FireCloud/Terra data collector
├── google_cloud_healthcare_collector.py  # Google Cloud data collector
├── ccle_collector.py              # CCLE data collector
├── gdsc_collector.py              # GDSC data collector
└── nci_60_collector.py            # NCI-60 data collector
```

## ⚙️ Configuration

The system uses a comprehensive configuration file (`config.json`) that allows you to customize:

- **Sample limits** for each data source
- **Cancer types** to focus on
- **Data types** to collect
- **API endpoints** and authentication
- **Rate limiting** and retry settings

### Example Configuration

```json
{
  "tcga": {
    "sample_limit": 100,
    "cancer_types": ["BRCA", "LUAD", "COAD", "PRAD"],
    "data_types": ["gene_expression", "mutation", "clinical"]
  },
  "geo": {
    "max_datasets": 5,
    "search_terms": ["breast cancer", "lung cancer"],
    "data_types": ["expression", "methylation"]
  },
  "cosmic": {
    "gene_list": ["TP53", "BRCA1", "BRCA2", "EGFR", "KRAS"],
    "cancer_types": ["breast", "lung", "prostate"],
    "data_types": ["mutations", "cancer_gene_census"]
  }
}
```

## 🧪 Testing

### Run All Tests

```bash
python -m data_collection.test_all_collectors
```

### Test Individual Collector

```python
from data_collection.test_all_collectors import test_collector
from pathlib import Path

result = test_collector(Path("data_collection/tcga_collector.py"))
print(f"Test result: {result['status']}")
```

## 📊 Data Output

### File Structure

```
data/external_sources/
├── tcga/
│   ├── tcga_gene_expression_BRCA_100_samples.csv
│   ├── tcga_mutations_breast_50_records.csv
│   └── tcga_clinical_BRCA_100_samples.csv
├── geo/
│   ├── geo_expression_breast_cancer_3_datasets.csv
│   └── geo_methylation_lung_cancer_2_datasets.csv
├── cosmic/
│   ├── cosmic_mutations_breast_200_records.csv
│   └── cosmic_cancer_gene_census_20_genes.csv
└── collection_results/
    ├── comprehensive_collection_20241201_143022.json
    └── collection_summary_20241201_143022.json
```

### Data Formats

- **CSV/TSV** - Tabular data (expression, clinical, mutations)
- **JSON** - Structured data (metadata, configurations)
- **Parquet** - Efficient storage for large datasets

## 🔧 Advanced Usage

### Custom Collector

```python
from data_collection.base_collector import DataCollectorBase

class CustomCollector(DataCollectorBase):
    def collect_data(self, **kwargs):
        # Implement custom collection logic
        pass
    
    def get_available_datasets(self):
        # Return available datasets
        pass
```

### Parallel Collection

```python
from data_collection.master_orchestrator import MasterDataOrchestrator

orchestrator = MasterDataOrchestrator(max_workers=8)

collection_plan = {
    "TCGA": {"data_type": "gene_expression", "cancer_type": "BRCA"},
    "GEO": {"search_term": "breast cancer", "data_type": "expression"},
    "COSMIC": {"data_type": "mutations", "cancer_type": "breast"}
}

results = orchestrator.collect_from_multiple_sources(collection_plan)
```

## 📈 Performance & Monitoring

### Logging

The system provides comprehensive logging:

- **Collection progress** tracking
- **Error handling** and recovery
- **Performance metrics** monitoring
- **Data validation** results

### Metrics

- **Collection time** per source
- **Records/samples collected** per source
- **Success/failure rates**
- **Data quality metrics**

## 🛡️ Error Handling

The system includes robust error handling:

- **Retry logic** with exponential backoff
- **Rate limiting** to respect API limits
- **Graceful degradation** when sources are unavailable
- **Comprehensive logging** for debugging

## 🔐 Authentication

Many data sources require authentication:

- **API keys** for restricted access
- **OAuth tokens** for user authentication
- **Rate limiting** to respect quotas
- **Secure credential storage**

## 📚 Documentation

Each collector includes:

- **Comprehensive docstrings**
- **Usage examples**
- **API documentation**
- **Error handling guides**

## 🤝 Contributing

To add a new data source:

1. Create a new collector class inheriting from `DataCollectorBase`
2. Implement `collect_data()` and `get_available_datasets()` methods
3. Add configuration to `config.json`
4. Update the master orchestrator
5. Add tests to the test suite

## 📄 License

This data collection system is part of the Cancer Biomarker Identifier project and follows the same licensing terms.

## 🆘 Support

For issues or questions:

1. Check the logs in `logs/` directory
2. Review the test results in `test_results.json`
3. Consult the individual collector documentation
4. Check the configuration file for proper settings

---

**Note**: This system is designed for research purposes. Please ensure compliance with data usage agreements and terms of service for each data source.

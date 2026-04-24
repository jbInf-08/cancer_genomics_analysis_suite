# Auto-Generation Scripts

This directory contains comprehensive auto-generation scripts for the Cancer Genomics Analysis Suite, designed to automatically create BLAST databases and mock data for testing, development, and demonstration purposes.

## 🚀 Quick Start

### Full Setup (Recommended)
```bash
# Run complete setup with all dependencies and data generation
python setup_auto_generation.py full-setup
```

### Individual Components
```bash
# Generate BLAST databases only
python setup_auto_generation.py blast-databases

# Generate mock data only  
python setup_auto_generation.py mock-data

# Check system dependencies
python setup_auto_generation.py check-dependencies
```

## 📁 Scripts Overview

### 1. `setup_auto_generation.py` - Main Setup Manager
- **Purpose**: Unified interface for all auto-generation tasks
- **Features**: 
  - Dependency checking and installation
  - Configuration management
  - Directory setup
  - Coordinated execution of other scripts
  - Docker and Makefile generation

### 2. `generate_blast_databases.py` - BLAST Database Generator
- **Purpose**: Creates BLAST databases for cancer genomics analysis
- **Features**:
  - Multiple database types (cancer genes, oncogenes, tumor suppressors, etc.)
  - API integration with Ensembl for real sequences
  - Mock sequence generation as fallback
  - Custom database creation from FASTA files
  - Comprehensive logging and reporting

### 3. `generate_mock_data.py` - Mock Data Generator
- **Purpose**: Generates realistic synthetic datasets for testing
- **Features**:
  - Clinical data with patient demographics and outcomes
  - Gene expression data with cancer-specific patterns
  - Mutation data with functional annotations
  - Variant annotations with prediction scores
  - Pathway data and protein structures
  - NGS file metadata

## 🛠️ Installation & Dependencies

### Required Python Packages
```bash
pip install numpy pandas biopython requests scipy
```

### Required External Tools
- **BLAST+ Suite**: `blastn`, `blastp`, `makeblastdb`
  - Download from: https://blast.ncbi.nlm.nih.gov/Blast.cgi?PAGE_TYPE=BlastDocs&DOC_TYPE=Download
  - Ensure tools are in your system PATH

### Automatic Dependency Installation
```bash
python setup_auto_generation.py install-dependencies
```

## ⚙️ Configuration

Configuration is managed through `auto_generation_config.json`:

```json
{
  "blast_databases": {
    "enabled": true,
    "output_dir": "blast_databases",
    "use_api": true,
    "use_mock": true,
    "databases": ["cancer_genes", "oncogenes", "tumor_suppressors"]
  },
  "mock_data": {
    "enabled": true,
    "output_dir": "data",
    "num_patients": 1000,
    "num_samples": 1200,
    "cancer_types": ["BRCA", "NSCLC", "COAD", "PRAD"]
  }
}
```

## 📊 Generated Data

### BLAST Databases
**Location**: `blast_databases/`
- `cancer_genes/` - Cancer-related gene sequences
- `oncogenes/` - Oncogene sequences  
- `tumor_suppressors/` - Tumor suppressor gene sequences
- `cancer_proteins/` - Cancer-related protein sequences
- `dna_repair_genes/` - DNA repair gene sequences

### Mock Data
**Location**: `data/`
- `mock_clinical_data.csv` - Patient clinical information
- `mock_expression_data.csv` - Gene expression profiles
- `mock_mutation_data.csv` - Mutation/variant data
- `mock_variant_annotations/` - Functional predictions
- `mock_pathway_data.json` - Pathway information
- `mock_protein_structures/` - PDB structure files
- `mock_ngs_data.csv` - NGS file metadata

## 🐳 Docker Support

### Using Docker Compose
```bash
# Generate Docker Compose file
python setup_auto_generation.py create-docker

# Run with Docker
docker-compose -f docker-compose.auto-generation.yml up --build
```

### Using Makefile
```bash
# Generate Makefile
python setup_auto_generation.py create-makefile

# Use Makefile commands
make setup          # Full setup
make blast-db       # BLAST databases only
make mock-data      # Mock data only
make clean          # Clean generated files
```

## 📝 Usage Examples

### Basic Usage
```bash
# Full setup with default settings
python setup_auto_generation.py full-setup

# Custom configuration
python generate_mock_data.py --num-patients 500 --cancer-types BRCA NSCLC
python generate_blast_databases.py --output-dir custom_blast_db --no-api
```

### Advanced Usage
```bash
# Create custom BLAST database from FASTA file
python generate_blast_databases.py --custom-db my_sequences.fasta --db-name custom_db --db-type nucl

# Generate specific data types only
python generate_mock_data.py --clinical-only
python generate_mock_data.py --expression-only
python generate_mock_data.py --mutations-only
```

### Integration with Existing Pipeline
```python
from tasks.blast_pipeline import BlastPipeline, BlastConfig

# Use generated BLAST database
config = BlastConfig(
    database_path="blast_databases/cancer_genes",
    program="blastn"
)
pipeline = BlastPipeline(config)
results = pipeline.run_blast("query_sequence.fasta")
```

## 🔧 Troubleshooting

### Common Issues

1. **BLAST tools not found**
   ```bash
   # Check if BLAST is installed
   blastn -version
   makeblastdb -version
   
   # Install BLAST+ if missing
   # Windows: Download from NCBI website
   # Linux: sudo apt-get install ncbi-blast+
   # macOS: brew install blast
   ```

2. **API connection issues**
   ```bash
   # Use mock data instead of API
   python generate_blast_databases.py --no-api --mock-only
   ```

3. **Memory issues with large datasets**
   ```bash
   # Reduce dataset size
   python generate_mock_data.py --num-patients 100 --num-samples 120
   ```

4. **Permission errors**
   ```bash
   # Ensure write permissions to output directories
   # Or run with different output directory
   python setup_auto_generation.py full-setup --output-dir /path/to/writable/dir
   ```

### Log Files
Check log files for detailed information:
- `setup.log` - Setup process logs
- `blast_db_generation.log` - BLAST database generation logs
- `mock_data_generation.log` - Mock data generation logs

## 🧪 Testing

### Validate Generated Data
```bash
# Check BLAST database
blastdbcmd -db blast_databases/cancer_genes -info

# Validate mock data
python -c "import pandas as pd; df = pd.read_csv('data/mock_clinical_data.csv'); print(f'Patients: {len(df)}')"
```

### Integration Tests
```python
# Test BLAST pipeline with generated database
from tasks.blast_pipeline import BlastPipeline, BlastConfig

config = BlastConfig(database_path="blast_databases/cancer_genes")
pipeline = BlastPipeline(config)
# Run test queries...
```

## 📈 Performance

### Typical Generation Times
- **BLAST Databases**: 2-5 minutes (with API), 30 seconds (mock only)
- **Mock Data (1000 patients)**: 1-3 minutes
- **Full Setup**: 5-10 minutes

### Resource Requirements
- **Memory**: 2-4 GB RAM recommended
- **Disk Space**: 500 MB - 2 GB depending on dataset size
- **CPU**: Multi-core recommended for faster generation

## 🔄 Updates & Maintenance

### Updating Scripts
```bash
# Check for updates
git pull origin main

# Regenerate data with new scripts
python setup_auto_generation.py full-setup
```

### Cleaning Generated Data
```bash
# Remove all generated files
python setup_auto_generation.py clean

# Or use Makefile
make clean
```

## 📚 Additional Resources

- [BLAST+ Documentation](https://www.ncbi.nlm.nih.gov/books/NBK279690/)
- [Ensembl REST API](https://rest.ensembl.org/)
- [Cancer Genomics Analysis Suite Documentation](../README.md)

## 🤝 Contributing

To contribute to the auto-generation scripts:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the same license as the Cancer Genomics Analysis Suite.

---

**Generated on**: $(date)  
**Version**: 1.0.0  
**Compatibility**: Python 3.7+, BLAST+ 2.10+

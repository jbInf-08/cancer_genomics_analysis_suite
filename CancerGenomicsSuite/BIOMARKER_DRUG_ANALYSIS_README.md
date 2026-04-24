# Biomarker and Drug Analysis Module

This document provides a comprehensive overview of the biomarker discovery and drug analysis capabilities integrated into the Cancer Genomics Analysis Suite.

## 🎯 Overview

The biomarker and drug analysis module provides a complete pipeline for:
- **Biomarker Discovery**: Statistical and machine learning-based identification of cancer biomarkers
- **Drug Discovery**: Target identification, drug repurposing, and mechanism analysis
- **Drug-Biomarker Integration**: Analysis of drug-biomarker interactions and personalized medicine
- **Clinical Decision Support**: Treatment recommendations and risk assessment

## 📊 Key Features

### Biomarker Discovery
- **Statistical Analysis**: T-test, Mann-Whitney U, correlation analysis
- **Machine Learning**: Random Forest, XGBoost, LightGBM-based biomarker discovery
- **Multi-omics Integration**: Integration across genomics, transcriptomics, proteomics
- **Validation**: Cross-validation and independent dataset validation
- **Visualization**: Volcano plots, Manhattan plots, ROC curves, network analysis

### Drug Discovery
- **Target Identification**: Identification of druggable targets from genomic data
- **Drug Repurposing**: Analysis of existing drugs for new cancer indications
- **Mechanism Analysis**: Understanding drug mechanisms of action
- **Safety Assessment**: Drug safety and toxicity evaluation
- **Clinical Evidence**: Integration with clinical trial and literature data

### Drug-Biomarker Integration
- **Interaction Analysis**: Statistical analysis of drug-biomarker interactions
- **Pharmacogenomics**: Integration of genetic variants affecting drug response
- **Personalized Medicine**: Treatment recommendations based on patient profiles
- **Risk Assessment**: Evaluation of treatment risks and contraindications

## 🚀 Quick Start

### Basic Biomarker Discovery

```python
from modules.biomarker_discovery import BiomarkerAnalyzer, BiomarkerDiscoveryConfig

# Configure analysis
config = BiomarkerDiscoveryConfig(
    p_value_threshold=0.05,
    effect_size_threshold=0.2,
    auc_threshold=0.7
)

# Initialize analyzer
analyzer = BiomarkerAnalyzer(config)

# Run analysis
results = analyzer.discover_biomarkers(gene_expression_data, labels)

# Get top biomarkers
top_biomarkers = analyzer.get_top_biomarkers(10)
```

### Basic Drug Analysis

```python
from modules.drug_discovery import DrugAnalyzer, DrugDiscoveryConfig

# Configure analysis
config = DrugDiscoveryConfig(
    min_efficacy_score=0.6,
    min_safety_score=0.7,
    repurposing_threshold=0.8
)

# Initialize analyzer
analyzer = DrugAnalyzer(config)

# Run analysis
results = analyzer.analyze_drugs(genomic_data, drug_data)

# Get top drugs
top_drugs = analyzer.get_top_drugs(10)
```

### Personalized Medicine

```python
from modules.drug_biomarker_integration import PersonalizedMedicineEngine

# Initialize engine
engine = PersonalizedMedicineEngine()

# Generate recommendations
recommendations = engine.generate_treatment_recommendations(
    patient_id='Patient_001',
    patient_biomarkers=biomarker_profile,
    pharmacogenomics_profile=pg_profile,
    drug_candidates=drug_list
)
```

## 📁 Module Structure

```
modules/
├── biomarker_discovery/
│   ├── biomarker_analyzer.py          # Core biomarker analysis
│   ├── biomarker_integration.py       # Multi-omics integration
│   ├── biomarker_validation.py        # Validation methods
│   ├── biomarker_dashboard.py         # Interactive dashboard
│   └── biomarker_database.py          # Database integration
├── drug_discovery/
│   ├── drug_analyzer.py               # Core drug analysis
│   ├── drug_response.py               # Response prediction
│   ├── drug_database.py               # Drug databases
│   ├── clinical_trials.py             # Clinical trial integration
│   └── drug_dashboard.py              # Interactive dashboard
├── drug_biomarker_integration/
│   ├── drug_biomarker_analyzer.py     # Integration analysis
│   ├── drug_response_prediction.py    # Response prediction
│   ├── clinical_decision_support.py   # Clinical support
│   └── integration_dashboard.py       # Integration dashboard
└── biomarker_drug_api/
    ├── api_routes.py                  # REST API endpoints
    ├── api_models.py                  # API data models
    └── api_utils.py                   # API utilities
```

## 🔧 Configuration

### Biomarker Discovery Configuration

```python
@dataclass
class BiomarkerDiscoveryConfig:
    p_value_threshold: float = 0.05
    effect_size_threshold: float = 0.2
    auc_threshold: float = 0.7
    multiple_testing_correction: str = 'fdr_bh'
    cross_validation_folds: int = 5
    random_state: int = 42
    min_samples_per_group: int = 10
    feature_selection_method: str = 'mutual_info'
    n_top_features: int = 100
```

### Drug Discovery Configuration

```python
@dataclass
class DrugDiscoveryConfig:
    min_efficacy_score: float = 0.6
    min_safety_score: float = 0.7
    repurposing_threshold: float = 0.8
    target_druggability_threshold: float = 0.5
    network_centrality_threshold: float = 0.3
    cross_validation_folds: int = 5
    random_state: int = 42
```

### Integration Configuration

```python
@dataclass
class DrugBiomarkerConfig:
    min_interaction_strength: float = 0.3
    p_value_threshold: float = 0.05
    effect_size_threshold: float = 0.2
    confidence_threshold: float = 0.7
    cross_validation_folds: int = 5
    random_state: int = 42
    min_samples_per_group: int = 10
```

## 📊 Data Formats

### Input Data

**Gene Expression Data** (pandas DataFrame):
- Rows: Genes/features
- Columns: Samples
- Values: Expression levels

**Mutation Data** (pandas DataFrame):
- Rows: Genes
- Columns: Samples
- Values: 0 (no mutation), 1 (mutation)

**Drug Data** (pandas DataFrame):
- Rows: Drugs
- Columns: Properties (name, type, indication, IC50, toxicity)

**Labels** (pandas Series):
- Index: Sample IDs
- Values: Binary (0/1) or continuous

### Output Data

**Biomarker Results**:
```python
@dataclass
class BiomarkerResult:
    biomarker_id: str
    biomarker_name: str
    biomarker_type: str
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    sensitivity: float
    specificity: float
    auc_score: float
    clinical_significance: str
    validation_status: str
    supporting_evidence: List[str]
    metadata: Dict[str, Any]
```

**Drug Results**:
```python
@dataclass
class DrugResult:
    drug_id: str
    drug_name: str
    drug_type: str
    target_genes: List[str]
    mechanism_of_action: str
    therapeutic_indication: str
    efficacy_score: float
    safety_score: float
    repurposing_potential: float
    clinical_evidence: List[str]
    supporting_literature: List[str]
    metadata: Dict[str, Any]
```

## 🌐 API Endpoints

### Biomarker Discovery API

- `POST /api/biomarker/discover` - Discover biomarkers
- `POST /api/biomarker/validate` - Validate biomarkers
- `POST /api/biomarker/export/<format>` - Export results

### Drug Discovery API

- `POST /api/drug/analyze` - Analyze drugs
- `POST /api/drug/repurpose` - Drug repurposing
- `POST /api/drug/targets` - Identify targets
- `POST /api/drug/export/<format>` - Export results

### Integration API

- `POST /api/integration/analyze` - Analyze interactions
- `POST /api/integration/predict` - Predict response
- `POST /api/integration/pharmacogenomics` - Create PGx profile

### Clinical API

- `POST /api/clinical/recommendations` - Generate recommendations
- `POST /api/clinical/risk-assessment` - Assess risk

## 📈 Visualization

### Interactive Dashboards

1. **Biomarker Discovery Dashboard** (Port 8050)
   - Volcano plots
   - Manhattan plots
   - ROC curves
   - Effect size distributions
   - Biomarker networks

2. **Drug Discovery Dashboard** (Port 8051)
   - Efficacy vs safety plots
   - Drug score comparisons
   - Target analysis
   - Repurposing potential
   - Drug-target networks

### Visualization Engine

```python
from modules.biomarker_discovery import BiomarkerVisualizationEngine
from modules.drug_discovery import DrugVisualizationEngine

# Create visualizations
viz_engine = BiomarkerVisualizationEngine()
volcano_plot = viz_engine.create_volcano_plot(biomarker_results)
manhattan_plot = viz_engine.create_manhattan_plot(biomarker_results)

drug_viz_engine = DrugVisualizationEngine()
efficacy_safety_plot = drug_viz_engine.create_efficacy_safety_plot(drug_results)
```

## 🧪 Example Usage

See `examples/biomarker_drug_analysis_example.py` for a complete example that demonstrates:

1. **Data Generation**: Mock data creation
2. **Biomarker Discovery**: Statistical and ML analysis
3. **Drug Discovery**: Comprehensive drug analysis
4. **Integration**: Drug-biomarker interactions
5. **Personalized Medicine**: Treatment recommendations
6. **Export**: Results export to CSV/Excel

## 🔬 Advanced Features

### Multi-omics Integration

```python
from modules.biomarker_discovery import MultiOmicsBiomarkerIntegrator

integrator = MultiOmicsBiomarkerIntegrator()
integrated_results = integrator.integrate_omics_data(
    genomics_data=genomic_data,
    transcriptomics_data=expression_data,
    proteomics_data=protein_data,
    metabolomics_data=metabolite_data
)
```

### Network Analysis

```python
from modules.biomarker_discovery import BiomarkerNetworkAnalyzer

network_analyzer = BiomarkerNetworkAnalyzer()
network_results = network_analyzer.analyze_biomarker_network(
    biomarker_results,
    interaction_data
)
```

### Clinical Validation

```python
from modules.biomarker_discovery import ClinicalBiomarkerValidator

validator = ClinicalBiomarkerValidator()
validation_results = validator.validate_clinical_significance(
    biomarker_results,
    clinical_data
)
```

## 📚 Dependencies

### Core Dependencies
- pandas >= 1.3.0
- numpy >= 1.21.0
- scikit-learn >= 1.0.0
- scipy >= 1.7.0
- xgboost >= 1.5.0
- lightgbm >= 3.2.0

### Visualization Dependencies
- plotly >= 5.0.0
- dash >= 2.0.0
- matplotlib >= 3.5.0
- seaborn >= 0.11.0

### API Dependencies
- flask >= 2.0.0
- flask-cors >= 3.0.0

### Network Analysis Dependencies
- networkx >= 2.6.0

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Example**:
   ```bash
   python examples/biomarker_drug_analysis_example.py
   ```

3. **Start Dashboards**:
   ```python
   from modules.biomarker_discovery import BiomarkerDiscoveryDashboard
   from modules.drug_discovery import DrugDiscoveryDashboard
   
   # Start biomarker dashboard
   biomarker_dash = BiomarkerDiscoveryDashboard()
   biomarker_dash.run_server(port=8050)
   
   # Start drug dashboard
   drug_dash = DrugDiscoveryDashboard()
   drug_dash.run_server(port=8051)
   ```

4. **Use API**:
   ```python
   from modules.biomarker_drug_api import register_all_apis
   from flask import Flask
   
   app = Flask(__name__)
   register_all_apis(app)
   app.run(debug=True)
   ```

## 📖 Documentation

- **API Documentation**: Available at `/api/docs` when running the API server
- **Dashboard Help**: Built-in help in the interactive dashboards
- **Code Examples**: See the `examples/` directory for comprehensive examples

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This module is part of the Cancer Genomics Analysis Suite and is licensed under the same terms as the main project.

## 🆘 Support

For questions and support:
- Check the documentation
- Review the examples
- Open an issue on GitHub
- Contact the development team

---

**Note**: This module is designed for research purposes. Always validate results with independent datasets and consult with clinical experts before making treatment decisions.

# Biomarker Integration - Complete Guide

## 🎯 Overview

This document provides a comprehensive guide for using the integrated biomarker analysis system that connects the Cancer Genomics Analysis Suite (CGAS) with the biomarker_identifier project. The integration provides a unified interface for biomarker discovery and analysis across both systems.

## 🚀 Quick Start

### 1. Basic Usage

```python
from biomarker_integration import discover_biomarkers, check_services

# Check available services
status = check_services()
print(f"Available services: {status}")

# Create sample data
import pandas as pd
import numpy as np

data = pd.DataFrame(np.random.randn(100, 50), 
                   columns=[f"Gene_{i}" for i in range(50)])
labels = np.random.choice([0, 1], size=100, p=[0.6, 0.4])

# Discover biomarkers
biomarkers = discover_biomarkers(data, labels)
print(f"Found {len(biomarkers)} biomarkers")
```

### 2. Advanced Usage

```python
from biomarker_integration import BiomarkerIntegration

# Create integration instance
integration = BiomarkerIntegration()

# Configure analysis
biomarkers = integration.discover_biomarkers(
    data=data,
    labels=labels,
    biomarker_type='gene_expression',
    prefer_service='biomarker_identifier'  # or 'simple'
)

# Compare services
comparison = integration.compare_services(data, labels)
```

## 🔧 Configuration

### Environment Variables

Set these environment variables to configure the integration:

```bash
# Biomarker Identifier Service
export BIOMARKER_IDENTIFIER_URL="http://localhost:8000"
export BIOMARKER_IDENTIFIER_TIMEOUT="30"

# Analysis Options
export ENABLE_SIMPLE_ANALYSIS="true"
```

### Configuration File

You can also create a configuration dictionary:

```python
config = {
    'biomarker_identifier_url': 'http://localhost:8000',
    'timeout': 30,
    'enable_simple_analysis': True
}

integration = BiomarkerIntegration(config)
```

## 🏗️ Architecture

### Service Integration

The integration system consists of:

1. **Biomarker Identifier Service** - Advanced ML-based biomarker analysis
2. **Simple Analysis Fallback** - Statistical analysis using scipy
3. **Service Discovery** - Automatic health checking and routing
4. **Unified Interface** - Single API for both services

### Data Flow

```
User Data → Integration Layer → Service Selection → Analysis → Results
```

## 📊 Supported Data Formats

### Input Data

The integration supports multiple data formats:

```python
# Pandas DataFrame
data = pd.DataFrame(...)

# Numpy arrays
data = np.array(...)

# Python lists
data = [[...], [...], ...]

# Dictionaries
data = {'feature1': [...], 'feature2': [...]}
```

### Labels

Labels can be provided as:

```python
# Pandas Series
labels = pd.Series([0, 1, 0, 1, ...])

# Numpy arrays
labels = np.array([0, 1, 0, 1, ...])

# Python lists
labels = [0, 1, 0, 1, ...]
```

## 🔍 Analysis Types

### 1. Biomarker Discovery

Discover biomarkers from omics data:

```python
biomarkers = discover_biomarkers(data, labels)

# Each biomarker contains:
for biomarker in biomarkers:
    print(f"Name: {biomarker.name}")
    print(f"P-value: {biomarker.p_value}")
    print(f"Effect Size: {biomarker.effect_size}")
    print(f"AUC Score: {biomarker.auc_score}")
    print(f"Service: {biomarker.service}")
```

### 2. Service Comparison

Compare results from different services:

```python
comparison = compare_services(data, labels)

for service, result in comparison['service_results'].items():
    if 'error' in result:
        print(f"{service}: Error - {result['error']}")
    else:
        print(f"{service}: {result['count']} biomarkers")
```

## 🛠️ Service Management

### Health Checking

```python
integration = BiomarkerIntegration()

# Check individual service health
is_healthy = integration.check_biomarker_identifier_health()
print(f"Biomarker Identifier: {'Healthy' if is_healthy else 'Unhealthy'}")

# Get full service status
status = integration.get_service_status()
for service, info in status.items():
    print(f"{service}: {info['available']}")
```

### Service Selection

The integration automatically selects the best service based on:

- Service availability
- Data size and complexity
- User preferences

You can also force a specific service:

```python
# Force biomarker_identifier service
biomarkers = integration.discover_biomarkers(
    data, labels, prefer_service='biomarker_identifier'
)

# Force simple analysis
biomarkers = integration.discover_biomarkers(
    data, labels, prefer_service='simple'
)
```

## 📈 Results and Output

### Biomarker Results

Each biomarker result contains:

```python
@dataclass
class BiomarkerResult:
    id: str                    # Unique identifier
    name: str                  # Biomarker name
    p_value: float            # Statistical significance
    effect_size: float        # Effect size (Cohen's d)
    auc_score: float          # Area under ROC curve
    service: str              # Service that generated the result
    metadata: Dict[str, Any]  # Additional information
```

### Analysis Metadata

The metadata includes:

- Statistical test results
- Group means and sizes
- Confidence intervals
- Validation information

## 🔧 Troubleshooting

### Common Issues

1. **Service Not Available**
   ```
   Solution: Check if biomarker_identifier service is running
   Check: http://localhost:8000/health
   ```

2. **Import Errors**
   ```
   Solution: Use the standalone integration module
   Import: from biomarker_integration import discover_biomarkers
   ```

3. **Data Format Issues**
   ```
   Solution: Ensure data and labels have compatible shapes
   Check: len(data) == len(labels)
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run your analysis
biomarkers = discover_biomarkers(data, labels)
```

## 🚀 Starting Services

### Option 1: Manual Startup

```bash
# Terminal 1: Start CGAS
cd CancerGenomicsSuite
python main_dashboard.py

# Terminal 2: Start Biomarker Identifier
cd biomarker_identifier
docker-compose up
```

### Option 2: Using Startup Script

```bash
# Start both services
python scripts/start_integrated_services.py

# Start with custom configuration
python scripts/start_integrated_services.py --config integrated_services_config.json
```

## 📚 Examples

### Example 1: Basic Analysis

```python
import pandas as pd
import numpy as np
from biomarker_integration import discover_biomarkers

# Create sample data
np.random.seed(42)
data = pd.DataFrame(
    np.random.randn(100, 50),
    columns=[f"Gene_{i:03d}" for i in range(50)]
)
labels = np.random.choice([0, 1], size=100, p=[0.6, 0.4])

# Discover biomarkers
biomarkers = discover_biomarkers(data, labels)

# Display results
print(f"Found {len(biomarkers)} biomarkers")
for i, biomarker in enumerate(biomarkers[:5]):
    print(f"{i+1}. {biomarker.name}: p={biomarker.p_value:.4f}, "
          f"effect={biomarker.effect_size:.3f}, AUC={biomarker.auc_score:.3f}")
```

### Example 2: Service Comparison

```python
from biomarker_integration import compare_services

# Compare services on same data
comparison = compare_services(data, labels)

print("Service Comparison Results:")
for service, result in comparison['service_results'].items():
    if 'error' in result:
        print(f"  {service}: Error - {result['error']}")
    else:
        print(f"  {service}: {result['count']} biomarkers found")
```

### Example 3: Custom Configuration

```python
from biomarker_integration import BiomarkerIntegration

# Custom configuration
config = {
    'biomarker_identifier_url': 'http://localhost:8000',
    'timeout': 60,
    'enable_simple_analysis': True
}

integration = BiomarkerIntegration(config)

# Use with custom settings
biomarkers = integration.discover_biomarkers(
    data, labels, 
    biomarker_type='gene_expression',
    prefer_service='biomarker_identifier'
)
```

## 🔗 Integration with Existing Code

### Replacing Old biomarker_analysis

If you were using the old `biomarker_analysis` directory, you can now use:

```python
# Old way (if it existed)
# from biomarker_analysis import analyze_biomarkers

# New way
from biomarker_integration import discover_biomarkers

# Same interface, better functionality
biomarkers = discover_biomarkers(data, labels)
```

### Integration with CGAS

The integration works seamlessly with existing CGAS modules:

```python
# Use with existing CGAS data
from modules.data_processing import load_expression_data
from biomarker_integration import discover_biomarkers

# Load data using existing CGAS functions
data, labels = load_expression_data('path/to/data.csv')

# Analyze using integrated system
biomarkers = discover_biomarkers(data, labels)
```

## 📋 API Reference

### Main Functions

- `discover_biomarkers(data, labels, **kwargs)` - Discover biomarkers
- `check_services()` - Check service status
- `compare_services(data, labels)` - Compare service results

### Main Classes

- `BiomarkerIntegration` - Main integration class
- `BiomarkerResult` - Result data class

### Configuration

- Environment variables for service URLs and timeouts
- Configuration dictionaries for custom settings
- Automatic fallback mechanisms

## 🎉 Success!

The biomarker integration is now fully functional and provides:

✅ **Unified Interface** - Single API for both services  
✅ **Automatic Fallback** - Works even when services are unavailable  
✅ **Multiple Data Formats** - Supports various input formats  
✅ **Service Comparison** - Compare results from different services  
✅ **Health Monitoring** - Automatic service health checking  
✅ **Easy Configuration** - Environment variables and config files  
✅ **Comprehensive Testing** - Full test suite included  

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Run the test suite: `python test_biomarker_integration.py`
3. Check service health: `python -c "from biomarker_integration import check_services; print(check_services())"`
4. Review the logs for detailed error information

The integration is designed to be robust and provide meaningful results even when some services are unavailable, ensuring your biomarker analysis workflows continue to work reliably.
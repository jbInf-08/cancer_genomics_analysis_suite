# Contributing to Cancer Genomics Analysis Suite

Thank you for your interest in contributing to the Cancer Genomics Analysis Suite! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community Guidelines](#community-guidelines)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Docker (for containerized development)
- Kubernetes (for deployment testing)
- Basic knowledge of bioinformatics and genomics

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/<your-username>/cancer_genomics_analysis_suite.git
   cd cancer_genomics_analysis_suite
   ```

   The upstream project is <https://github.com/jbInf-08/cancer_genomics_analysis_suite> if you are not forking.

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   # Install the package in development mode
   pip install -e .
   
   # Install development dependencies
   pip install -e ".[dev,test,docs]"
   ```

4. **Set Up Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Or: cp CancerGenomicsSuite/environment.template .env
   # Edit .env with your configuration
   ```

## Contributing Process

### 1. Choose an Issue

- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it
- If you want to work on something not in the issues, please create an issue first

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-number
```

### 3. Make Your Changes

- Follow the coding standards outlined below
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Test Your Changes

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov=CancerGenomicsSuite --cov-report=html
```

### 5. Submit a Pull Request

- Push your branch to your fork
- Create a pull request using our template
- Link to any related issues
- Request review from maintainers

## Coding Standards

### Python Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **MyPy**: Type checking
- **Flake8**: Linting
- **Bandit**: Security linting

#### Code Formatting

```bash
# Format code with Black
black CancerGenomicsSuite/

# Sort imports with isort
isort CancerGenomicsSuite/

# Check types with MyPy
mypy CancerGenomicsSuite/

# Lint with Flake8
flake8 CancerGenomicsSuite/

# Security check with Bandit
bandit -r CancerGenomicsSuite/
```

#### Naming Conventions

- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Protected methods**: `__double_underscore`

#### Type Hints

All functions should include type hints:

```python
from typing import List, Dict, Optional, Union

def process_mutations(
    mutations: List[Dict[str, str]], 
    threshold: float = 0.5
) -> Optional[Dict[str, Union[str, float]]]:
    """Process mutation data with optional threshold."""
    pass
```

#### Docstrings

Use Google-style docstrings:

```python
def analyze_gene_expression(
    expression_data: pd.DataFrame,
    gene_list: List[str],
    method: str = "t-test"
) -> Dict[str, float]:
    """Analyze gene expression data for specified genes.
    
    Args:
        expression_data: DataFrame containing gene expression values
        gene_list: List of gene symbols to analyze
        method: Statistical method to use ('t-test', 'wilcoxon', 'anova')
        
    Returns:
        Dictionary mapping gene symbols to p-values
        
    Raises:
        ValueError: If method is not supported
        KeyError: If gene symbols are not found in data
        
    Example:
        >>> data = pd.DataFrame({'GENE1': [1, 2, 3], 'GENE2': [4, 5, 6]})
        >>> result = analyze_gene_expression(data, ['GENE1', 'GENE2'])
        >>> print(result)
        {'GENE1': 0.05, 'GENE2': 0.03}
    """
    pass
```

### File Organization

```
CancerGenomicsSuite/
├── app/                    # Flask application
├── modules/               # Feature modules
│   ├── __init__.py
│   ├── mutation_analysis/
│   ├── gene_expression/
│   └── ...
├── tests/                 # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/               # Configuration
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## Testing Guidelines

### Test Structure

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test module interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test system performance
- **Security Tests**: Test security vulnerabilities

### Writing Tests

Focus tests on **behavior and risk** (see [docs/testing_confidence.md](docs/testing_confidence.md)). Use `@pytest.mark.critical` sparingly on regressions and core paths; run them with `pytest CancerGenomicsSuite/tests/ -m critical --no-cov`. Raise the global coverage floor in `pyproject.toml` only when the suite’s measured total actually increases.

```python
import pytest
from unittest.mock import Mock, patch
from CancerGenomicsSuite.modules.mutation_analysis import MutationAnalyzer

class TestMutationAnalyzer:
    """Test cases for MutationAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a MutationAnalyzer instance for testing."""
        return MutationAnalyzer()
    
    @pytest.fixture
    def sample_mutations(self):
        """Sample mutation data for testing."""
        return [
            {"gene": "TP53", "mutation": "R175H", "impact": "high"},
            {"gene": "KRAS", "mutation": "G12D", "impact": "high"},
        ]
    
    def test_analyze_mutations_success(self, analyzer, sample_mutations):
        """Test successful mutation analysis."""
        result = analyzer.analyze_mutations(sample_mutations)
        
        assert result is not None
        assert "high_impact_count" in result
        assert result["high_impact_count"] == 2
    
    def test_analyze_mutations_empty_input(self, analyzer):
        """Test mutation analysis with empty input."""
        result = analyzer.analyze_mutations([])
        
        assert result is not None
        assert result["high_impact_count"] == 0
    
    @pytest.mark.parametrize("invalid_input", [None, "string", 123])
    def test_analyze_mutations_invalid_input(self, analyzer, invalid_input):
        """Test mutation analysis with invalid input."""
        with pytest.raises(ValueError):
            analyzer.analyze_mutations(invalid_input)
    
    @patch('CancerGenomicsSuite.modules.mutation_analysis.requests.get')
    def test_fetch_external_data(self, mock_get, analyzer):
        """Test fetching external data with mocked requests."""
        mock_get.return_value.json.return_value = {"data": "test"}
        
        result = analyzer.fetch_external_data("test_url")
        
        assert result == {"data": "test"}
        mock_get.assert_called_once_with("test_url")
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_integration_workflow():
    pass

@pytest.mark.e2e
def test_end_to_end_process():
    pass

@pytest.mark.slow
def test_performance_benchmark():
    pass

@pytest.mark.security
def test_security_vulnerability():
    pass
```

### Running tests

Tests live in **`CancerGenomicsSuite/tests/`**; `pyproject.toml` sets `testpaths` so you can run `pytest` from the repository root.

```bash
# Run all tests (default includes coverage; see pyproject.toml)
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run tests with coverage
pytest --cov=CancerGenomicsSuite --cov-report=html

# Run tests in parallel
pytest -n auto

# Run a specific file (example path; adjust to a file that exists)
pytest CancerGenomicsSuite/tests/unit/test_plugin_registry.py

# Run a specific test
pytest CancerGenomicsSuite/tests/unit/test_plugin_registry.py -k "test_"
```

There is no top-level `tests/` package; do not use paths like `tests/unit/...` unless you create that layout.

## Documentation

### Code Documentation

- All public functions, classes, and methods must have docstrings
- Use Google-style docstrings
- Include type hints for all parameters and return values
- Add inline comments for complex logic

### API Documentation

- Update OpenAPI specifications for API changes
- Include examples in docstrings
- Document error conditions and exceptions

### User Documentation

- Update README.md for significant changes
- Add or update user guides
- Include installation and setup instructions
- Provide usage examples

### Developer Documentation

- Document architecture decisions
- Include setup and development instructions
- Document testing procedures
- Explain deployment processes

## Pull Request Process

### Before Submitting

1. **Ensure Tests Pass**
   ```bash
   pytest
   ```

2. **Check Code Quality**
   ```bash
   black --check CancerGenomicsSuite/
   isort --check-only CancerGenomicsSuite/
   mypy CancerGenomicsSuite/
   flake8 CancerGenomicsSuite/
   bandit -r CancerGenomicsSuite/
   ```

3. **Update Documentation**
   - Update docstrings for new functions
   - Update README.md if needed
   - Update API documentation

4. **Test Your Changes**
   - Test in multiple environments
   - Verify backward compatibility
   - Check performance impact

### Pull Request Template

Use the provided pull request template and fill out all relevant sections:

- Description of changes
- Type of change
- Related issues
- Testing performed
- Screenshots/videos (if applicable)
- Checklist completion

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: Maintainers review code quality and functionality
3. **Testing**: Changes are tested in staging environment
4. **Approval**: At least one maintainer approval required
5. **Merge**: Changes are merged to main branch

## Issue Reporting

### Bug Reports

Use the bug report template and include:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Error logs or screenshots

### Feature Requests

Use the feature request template and include:

- Clear description of the feature
- Problem it solves
- Proposed solution
- Use cases
- Acceptance criteria

### Security Issues

For security vulnerabilities:

- **DO NOT** create public issues
- Email security concerns to: security@cancer-genomics.com
- Use the private security advisory system

## Community Guidelines

### Communication

- **Be Respectful**: Treat all community members with respect
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Patient**: Remember that maintainers are volunteers
- **Be Clear**: Use clear, concise language

### Getting Help

- **Documentation**: Check existing documentation first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Community**: Join our community channels

### Recognition

Contributors are recognized in:

- CONTRIBUTORS.md file
- Release notes
- Project documentation
- Community acknowledgments

## Development Workflow

### Branch Naming

- `feature/description`: New features
- `bugfix/issue-number`: Bug fixes
- `hotfix/description`: Critical fixes
- `docs/description`: Documentation updates
- `refactor/description`: Code refactoring

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```
feat(mutation-analysis): add support for VCF file processing

fix(api): resolve authentication token expiration issue

docs(readme): update installation instructions for Windows
```

### Release Process

1. **Version Bumping**: Update version in pyproject.toml
2. **Changelog**: Update CHANGELOG.md
3. **Tagging**: Create git tag for release
4. **Building**: Build and test packages
5. **Publishing**: Publish to PyPI
6. **Announcement**: Announce release to community

## Getting Help

### Resources

- **Documentation**: [Project Documentation](https://cancer-genomics-analysis-suite.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/your-org/cancer-genomics-analysis-suite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/cancer-genomics-analysis-suite/discussions)
- **Community**: [Slack Channel](https://cancer-genomics.slack.com)

### Contact

- **General Questions**: Open a GitHub Discussion
- **Bug Reports**: Create a GitHub Issue
- **Security Issues**: Email security@cancer-genomics.com
- **Maintainers**: @maintainer1, @maintainer2

## Thank You

Thank you for contributing to the Cancer Genomics Analysis Suite! Your contributions help advance cancer research and improve patient outcomes.

---

**Remember**: Every contribution, no matter how small, makes a difference. Whether it's fixing a typo, adding a test, or implementing a new feature, your work is valued and appreciated.

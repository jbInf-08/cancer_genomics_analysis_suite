"""
Pytest configuration and shared fixtures for the Cancer Genomics Analysis Suite.

This module provides common fixtures and configuration for all test modules.
"""

import logging
import os
import shutil

# Add the project root to the Python path
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest
from celery import Celery
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from CancerGenomicsSuite.app import create_app
from CancerGenomicsSuite.config.settings import TestConfig


@pytest.fixture(scope="session", autouse=True)
def cgas_session_upload_folder(tmp_path_factory) -> Path:
    """Single session upload root for TestConfig (avoids per-instance temp dirs under pytest)."""
    folder = tmp_path_factory.mktemp("cgas_flask_uploads")
    os.environ["CGAS_TEST_UPLOAD_FOLDER"] = str(folder)
    yield folder
    os.environ.pop("CGAS_TEST_UPLOAD_FOLDER", None)


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary file for testing."""
    temp_file = temp_dir / "test_file.txt"
    temp_file.touch()
    yield temp_file
    if temp_file.exists():
        temp_file.unlink()


@pytest.fixture(scope="function")
def sample_mutation_data() -> pd.DataFrame:
    """Provide sample mutation data for testing."""
    return pd.DataFrame(
        {
            "gene": ["TP53", "KRAS", "EGFR", "BRAF", "PIK3CA"],
            "mutation": ["R175H", "G12D", "L858R", "V600E", "H1047R"],
            "impact": ["high", "high", "high", "high", "moderate"],
            "chromosome": ["17", "12", "7", "7", "3"],
            "position": [7574003, 25398284, 55241707, 140753336, 178916876],
            "ref_allele": ["C", "G", "T", "T", "A"],
            "alt_allele": ["T", "A", "G", "A", "G"],
            "sample_id": [
                "SAMPLE_001",
                "SAMPLE_001",
                "SAMPLE_002",
                "SAMPLE_002",
                "SAMPLE_003",
            ],
        }
    )


@pytest.fixture(scope="function")
def sample_expression_data() -> pd.DataFrame:
    """Provide sample gene expression data for testing."""
    np.random.seed(42)
    genes = ["TP53", "KRAS", "EGFR", "BRAF", "PIK3CA", "MYC", "RB1", "PTEN"]
    samples = ["SAMPLE_001", "SAMPLE_002", "SAMPLE_003", "SAMPLE_004", "SAMPLE_005"]

    data = np.random.lognormal(mean=5, sigma=1, size=(len(genes), len(samples)))
    return pd.DataFrame(data, index=genes, columns=samples)


@pytest.fixture(scope="function")
def sample_clinical_data() -> pd.DataFrame:
    """Provide sample clinical data for testing."""
    return pd.DataFrame(
        {
            "sample_id": [
                "SAMPLE_001",
                "SAMPLE_002",
                "SAMPLE_003",
                "SAMPLE_004",
                "SAMPLE_005",
            ],
            "patient_id": [
                "PATIENT_001",
                "PATIENT_002",
                "PATIENT_003",
                "PATIENT_004",
                "PATIENT_005",
            ],
            "age": [65, 72, 58, 45, 68],
            "gender": ["M", "F", "M", "F", "M"],
            "cancer_type": ["Lung", "Breast", "Colon", "Lung", "Prostate"],
            "stage": ["III", "II", "IV", "I", "III"],
            "survival_days": [365, 730, 180, 1095, 450],
            "status": ["alive", "alive", "dead", "alive", "dead"],
        }
    )


@pytest.fixture(scope="function")
def sample_vcf_data() -> str:
    """Provide sample VCF data for testing."""
    return """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE_001
17	7574003	.	C	T	100	PASS	DP=100;AF=0.5	GT:DP	0/1:100
12	25398284	.	G	A	95	PASS	DP=95;AF=0.4	GT:DP	0/1:95
7	55241707	.	T	G	90	PASS	DP=90;AF=0.3	GT:DP	0/1:90
"""


@pytest.fixture(scope="function")
def sample_fastq_data() -> str:
    """Provide sample FASTQ data for testing."""
    return """@read1
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
@read2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""


@pytest.fixture(scope="function")
def mock_database():
    """Provide a mock database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture(scope="function")
def mock_redis():
    """Provide a mock Redis client for testing."""
    with patch("redis.Redis") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        yield mock_redis_instance


@pytest.fixture(scope="function")
def mock_kafka_producer():
    """Provide a mock Kafka producer for testing."""
    with patch("kafka.KafkaProducer") as mock_producer:
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        yield mock_producer_instance


@pytest.fixture(scope="function")
def mock_neo4j_driver():
    """Provide a mock Neo4j driver for testing."""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_driver_instance = Mock()
        mock_driver.return_value = mock_driver_instance
        yield mock_driver_instance


@pytest.fixture(scope="function")
def mock_celery_app():
    """Provide a mock Celery app for testing."""
    with patch("celery.Celery") as mock_celery:
        mock_celery_instance = Mock()
        mock_celery.return_value = mock_celery_instance
        yield mock_celery_instance


@pytest.fixture(scope="function")
def mock_requests():
    """Provide a mock requests module for testing."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post, patch(
        "requests.put"
    ) as mock_put, patch("requests.delete") as mock_delete:
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.status_code = 200
        mock_response.text = '{"status": "success"}'

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        mock_put.return_value = mock_response
        mock_delete.return_value = mock_response

        yield {
            "get": mock_get,
            "post": mock_post,
            "put": mock_put,
            "delete": mock_delete,
        }


@pytest.fixture(scope="function")
def mock_file_system(temp_dir: Path):
    """Provide a mock file system for testing."""
    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.is_file"
    ) as mock_is_file, patch("pathlib.Path.is_dir") as mock_is_dir, patch(
        "pathlib.Path.mkdir"
    ) as mock_mkdir, patch(
        "pathlib.Path.unlink"
    ) as mock_unlink:
        # Configure mocks to work with temp_dir
        def exists_side_effect(self):
            return (temp_dir / self.name).exists()

        def is_file_side_effect(self):
            return (temp_dir / self.name).is_file()

        def is_dir_side_effect(self):
            return (temp_dir / self.name).is_dir()

        mock_exists.side_effect = exists_side_effect
        mock_is_file.side_effect = is_file_side_effect
        mock_is_dir.side_effect = is_dir_side_effect

        yield {
            "exists": mock_exists,
            "is_file": mock_is_file,
            "is_dir": mock_is_dir,
            "mkdir": mock_mkdir,
            "unlink": mock_unlink,
        }


@pytest.fixture(scope="function")
def mock_ml_model():
    """Provide a mock machine learning model for testing."""
    mock_model = Mock()
    mock_model.predict.return_value = np.array([0.8, 0.6, 0.9, 0.7, 0.5])
    mock_model.predict_proba.return_value = np.array(
        [[0.2, 0.8], [0.4, 0.6], [0.1, 0.9], [0.3, 0.7], [0.5, 0.5]]
    )
    mock_model.score.return_value = 0.85
    return mock_model


@pytest.fixture(scope="function")
def mock_bioinformatics_tools():
    """Provide mocks for bioinformatics tools."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Tool output", stderr="")
        yield mock_run


@pytest.fixture(scope="function")
def mock_galaxy_client():
    """Provide a mock Galaxy client for testing."""
    with patch("bioblend.galaxy.GalaxyInstance") as mock_galaxy:
        mock_instance = Mock()
        mock_galaxy.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_r_interface():
    """Provide a mock R interface for testing."""
    with patch("rpy2.robjects") as mock_r:
        mock_r_instance = Mock()
        mock_r.return_value = mock_r_instance
        yield mock_r_instance


@pytest.fixture(scope="function")
def mock_matlab_engine():
    """Provide a mock MATLAB engine for testing."""
    with patch("matlab.engine") as mock_matlab:
        mock_engine = Mock()
        mock_matlab.start_matlab.return_value = mock_engine
        yield mock_engine


@pytest.fixture(scope="function")
def mock_pymol():
    """Provide a mock PyMOL for testing."""
    with patch("pymol.cmd") as mock_pymol:
        yield mock_pymol


@pytest.fixture(scope="function")
def sample_protein_structure():
    """Provide sample protein structure data for testing."""
    return {
        "pdb_id": "1CRN",
        "sequence": "TTCCPSIVARSNFNVCRLPGTPEAICATYTGCIIIPGATCPGDYAN",
        "structure": "ATOM      1  N   CYS A   1      20.154  16.967  23.862  1.00 11.18           N",
        "resolution": 1.5,
        "method": "X-RAY DIFFRACTION",
    }


@pytest.fixture(scope="function")
def sample_pathway_data():
    """Provide sample pathway data for testing."""
    return {
        "pathway_id": "hsa04010",
        "pathway_name": "MAPK signaling pathway",
        "genes": ["KRAS", "BRAF", "MAPK1", "MAPK3", "EGFR"],
        "description": "The MAPK signaling pathway is involved in cell proliferation and differentiation.",
    }


@pytest.fixture(scope="function")
def sample_network_data():
    """Provide sample network data for testing."""
    return {
        "nodes": [
            {"id": "TP53", "label": "TP53", "type": "gene"},
            {"id": "MDM2", "label": "MDM2", "type": "gene"},
            {"id": "CDKN1A", "label": "CDKN1A", "type": "gene"},
        ],
        "edges": [
            {"source": "TP53", "target": "MDM2", "type": "regulates"},
            {"source": "TP53", "target": "CDKN1A", "type": "regulates"},
        ],
    }


# Test markers
pytest_plugins = []


def _silence_rpy2_loggers() -> None:
    """Send rpy2 logs to NullHandler so atexit handlers do not write to closed streams."""
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if isinstance(name, str) and name.startswith("rpy2"):
            lg = logging.getLogger(name)
            lg.handlers[:] = [logging.NullHandler()]
            lg.propagate = False


def pytest_configure(config):
    """Configure pytest with custom markers."""
    _silence_rpy2_loggers()
    # Avoid intermittent WinError 32 on the default ``.coverage`` file (IDE/antivirus locks).
    if "COVERAGE_FILE" not in os.environ:
        os.environ["COVERAGE_FILE"] = str(
            project_root / f".coverage.pytest.{os.getpid()}"
        )
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "bioinformatics: mark test as bioinformatics-specific"
    )
    config.addinivalue_line("markers", "ml: mark test as machine learning test")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "database: mark test as database test")
    config.addinivalue_line("markers", "celery: mark test as celery task test")
    config.addinivalue_line("markers", "kafka: mark test as kafka test")
    config.addinivalue_line("markers", "neo4j: mark test as neo4j test")
    config.addinivalue_line("markers", "galaxy: mark test as galaxy integration test")
    config.addinivalue_line("markers", "r: mark test as R integration test")
    config.addinivalue_line("markers", "matlab: mark test as MATLAB integration test")
    config.addinivalue_line("markers", "pymol: mark test as PyMOL integration test")
    config.addinivalue_line(
        "markers",
        "critical: high-confidence tests for product-risk areas (use sparingly)",
    )


def pytest_sessionfinish(session, exitstatus):
    _silence_rpy2_loggers()


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        fp = str(item.fspath).replace("\\", "/")
        # Directory-based markers
        if "/tests/unit/" in fp:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in fp:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in fp:
            item.add_marker(pytest.mark.e2e)
        elif "/performance/" in fp:
            item.add_marker(pytest.mark.performance)
        elif "/security/" in fp:
            item.add_marker(pytest.mark.security)
        elif "/CancerGenomicsSuite/tests/" in fp and "conftest" not in fp:
            if item.get_closest_marker("integration") is None:
                item.add_marker(pytest.mark.unit)

        # Add markers based on test name
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        if "bioinformatics" in item.name.lower():
            item.add_marker(pytest.mark.bioinformatics)
        if "ml" in item.name.lower() or "machine_learning" in item.name.lower():
            item.add_marker(pytest.mark.ml)
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)
        if "database" in item.name.lower():
            item.add_marker(pytest.mark.database)
        if "celery" in item.name.lower():
            item.add_marker(pytest.mark.celery)
        if "kafka" in item.name.lower():
            item.add_marker(pytest.mark.kafka)
        if "neo4j" in item.name.lower():
            item.add_marker(pytest.mark.neo4j)
        if "galaxy" in item.name.lower():
            item.add_marker(pytest.mark.galaxy)
        if "r_" in item.name.lower() or "r_integration" in item.name.lower():
            item.add_marker(pytest.mark.r)
        if "matlab" in item.name.lower():
            item.add_marker(pytest.mark.matlab)
        if "pymol" in item.name.lower():
            item.add_marker(pytest.mark.pymol)

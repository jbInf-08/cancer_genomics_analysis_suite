#!/usr/bin/env python3
"""
Auto-Generation Setup Script

This script provides a unified interface for setting up and running auto-generation
scripts for BLAST databases and mock data. It includes configuration management,
dependency checking, and automated setup procedures.

Usage:
    python setup_auto_generation.py [command] [options]

Author: Cancer Genomics Analysis Suite
"""

import os
import sys
import argparse
import logging
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import platform
import importlib.util

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AutoGenerationSetup:
    """Setup and configuration manager for auto-generation scripts."""
    
    def __init__(self, config_file: str = "auto_generation_config.json"):
        """
        Initialize the auto-generation setup.
        
        Args:
            config_file (str): Path to configuration file
        """
        self.config_file = Path(config_file)
        self.scripts_dir = Path(__file__).parent
        self.project_root = self.scripts_dir.parent
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.scripts_dir / 'setup.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.default_config = {
            "blast_databases": {
                "enabled": True,
                "output_dir": "blast_databases",
                "use_api": True,
                "use_mock": True,
                "databases": [
                    "cancer_genes",
                    "oncogenes", 
                    "tumor_suppressors",
                    "cancer_proteins",
                    "dna_repair_genes"
                ]
            },
            "mock_data": {
                "enabled": True,
                "output_dir": "data",
                "num_patients": 1000,
                "num_samples": 1200,
                "num_genes": 20000,
                "num_mutations": 5000,
                "seed": 42,
                "cancer_types": [
                    "BRCA", "NSCLC", "COAD", "PRAD", "STAD", "LIHC", "THCA",
                    "BLCA", "HNSC", "KIRC", "LUSC", "UCEC", "CESC", "SARC",
                    "DLBC", "LGG", "GBM", "OV", "SKCM", "PAAD"
                ]
            },
            "dependencies": {
                "python_packages": [
                    "numpy", "pandas", "biopython", "requests", "scipy"
                ],
                "external_tools": [
                    "blastn", "blastp", "makeblastdb"
                ]
            },
            "paths": {
                "blast_databases": "blast_databases",
                "mock_data": "data",
                "logs": "logs"
            }
        }
        
        # Load or create configuration
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                self.logger.warning(f"Error loading config: {e}. Using defaults.")
                return self.default_config
        else:
            self.logger.info("No config file found. Creating default configuration.")
            self.save_config(self.default_config)
            return self.default_config
    
    def save_config(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to file."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        self.logger.info("Checking dependencies...")
        
        results = {
            "python_packages": {},
            "external_tools": {}
        }
        
        # Check Python packages
        for package in self.config["dependencies"]["python_packages"]:
            try:
                spec = importlib.util.find_spec(package)
                results["python_packages"][package] = spec is not None
                if spec is not None:
                    self.logger.info(f"[OK] {package} is installed")
                else:
                    self.logger.warning(f"[MISSING] {package} is not installed")
            except Exception as e:
                results["python_packages"][package] = False
                self.logger.warning(f"[ERROR] Error checking {package}: {e}")
        
        # Check external tools
        for tool in self.config["dependencies"]["external_tools"]:
            try:
                result = subprocess.run([tool, "-version"], 
                                      capture_output=True, text=True, timeout=10)
                results["external_tools"][tool] = result.returncode == 0
                if result.returncode == 0:
                    self.logger.info(f"[OK] {tool} is available")
                else:
                    self.logger.warning(f"[MISSING] {tool} is not available")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                results["external_tools"][tool] = False
                self.logger.warning(f"[MISSING] {tool} is not installed or not in PATH")
        
        return results
    
    def install_dependencies(self) -> bool:
        """Install missing Python dependencies."""
        self.logger.info("Installing missing Python dependencies...")
        
        missing_packages = []
        for package, installed in self.config["dependencies"]["python_packages"].items():
            if not installed:
                missing_packages.append(package)
        
        if not missing_packages:
            self.logger.info("All Python dependencies are already installed")
            return True
        
        try:
            # Install missing packages
            cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            self.logger.info(f"Successfully installed: {', '.join(missing_packages)}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install dependencies: {e}")
            self.logger.error(f"stderr: {e.stderr}")
            return False
    
    def setup_directories(self) -> None:
        """Create necessary directories."""
        self.logger.info("Setting up directories...")
        
        directories = [
            self.config["paths"]["blast_databases"],
            self.config["paths"]["mock_data"],
            self.config["paths"]["logs"]
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created directory: {dir_path}")
    
    def run_blast_database_generation(self) -> bool:
        """Run BLAST database generation."""
        if not self.config["blast_databases"]["enabled"]:
            self.logger.info("BLAST database generation is disabled")
            return True
        
        self.logger.info("Starting BLAST database generation...")
        
        script_path = self.scripts_dir / "generate_blast_databases.py"
        if not script_path.exists():
            self.logger.error(f"BLAST generation script not found: {script_path}")
            return False
        
        try:
            cmd = [
                sys.executable,
                str(script_path),
                "--output-dir", self.config["blast_databases"]["output_dir"]
            ]
            
            if not self.config["blast_databases"]["use_api"]:
                cmd.append("--no-api")
            
            if self.config["blast_databases"]["use_mock"]:
                cmd.append("--mock-only")
            
            result = subprocess.run(cmd, cwd=self.project_root, check=True)
            
            self.logger.info("BLAST database generation completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"BLAST database generation failed: {e}")
            return False
    
    def run_mock_data_generation(self) -> bool:
        """Run mock data generation."""
        if not self.config["mock_data"]["enabled"]:
            self.logger.info("Mock data generation is disabled")
            return True
        
        self.logger.info("Starting mock data generation...")
        
        script_path = self.scripts_dir / "generate_mock_data.py"
        if not script_path.exists():
            self.logger.error(f"Mock data generation script not found: {script_path}")
            return False
        
        try:
            cmd = [
                sys.executable,
                str(script_path),
                "--output-dir", self.config["mock_data"]["output_dir"],
                "--num-patients", str(self.config["mock_data"]["num_patients"]),
                "--num-samples", str(self.config["mock_data"]["num_samples"]),
                "--num-genes", str(self.config["mock_data"]["num_genes"]),
                "--num-mutations", str(self.config["mock_data"]["num_mutations"]),
                "--seed", str(self.config["mock_data"]["seed"])
            ]
            
            if self.config["mock_data"]["cancer_types"]:
                cmd.extend(["--cancer-types"] + self.config["mock_data"]["cancer_types"])
            
            result = subprocess.run(cmd, cwd=self.project_root, check=True)
            
            self.logger.info("Mock data generation completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Mock data generation failed: {e}")
            return False
    
    def run_full_setup(self) -> bool:
        """Run complete setup process."""
        self.logger.info("Starting full auto-generation setup...")
        
        success = True
        
        # Check dependencies
        deps = self.check_dependencies()
        
        # Install missing Python packages
        if not self.install_dependencies():
            success = False
        
        # Setup directories
        self.setup_directories()
        
        # Run BLAST database generation
        if not self.run_blast_database_generation():
            success = False
        
        # Run mock data generation
        if not self.run_mock_data_generation():
            success = False
        
        if success:
            self.logger.info("Full setup completed successfully!")
        else:
            self.logger.error("Setup completed with errors")
        
        return success
    
    def create_environment_file(self) -> str:
        """Create environment configuration file."""
        env_file = self.project_root / "auto_generation.env"
        
        env_content = f"""# Auto-Generation Environment Configuration
# Generated on {self.get_timestamp()}

# BLAST Database Configuration
BLAST_DB_DIR={self.config['blast_databases']['output_dir']}
BLAST_USE_API={str(self.config['blast_databases']['use_api']).lower()}
BLAST_USE_MOCK={str(self.config['blast_databases']['use_mock']).lower()}

# Mock Data Configuration
MOCK_DATA_DIR={self.config['mock_data']['output_dir']}
MOCK_NUM_PATIENTS={self.config['mock_data']['num_patients']}
MOCK_NUM_SAMPLES={self.config['mock_data']['num_samples']}
MOCK_NUM_GENES={self.config['mock_data']['num_genes']}
MOCK_NUM_MUTATIONS={self.config['mock_data']['num_mutations']}
MOCK_SEED={self.config['mock_data']['seed']}

# Paths
PROJECT_ROOT={self.project_root}
SCRIPTS_DIR={self.scripts_dir}
LOGS_DIR={self.config['paths']['logs']}

# System Information
PLATFORM={platform.system()}
PYTHON_VERSION={sys.version.split()[0]}
"""
        
        try:
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            self.logger.info(f"Environment file created: {env_file}")
            return str(env_file)
            
        except Exception as e:
            self.logger.error(f"Error creating environment file: {e}")
            return None
    
    def create_docker_compose(self) -> str:
        """Create Docker Compose file for auto-generation."""
        compose_file = self.scripts_dir / "docker-compose.auto-generation.yml"
        
        compose_content = f"""version: '3.8'

services:
  blast-db-generator:
    build:
      context: ..
      dockerfile: Dockerfile
    volumes:
      - ../{self.config['blast_databases']['output_dir']}:/app/blast_databases
      - ../{self.config['paths']['logs']}:/app/logs
    environment:
      - BLAST_DB_DIR=/app/blast_databases
      - BLAST_USE_API=false
      - BLAST_USE_MOCK=true
    command: python scripts/generate_blast_databases.py --output-dir /app/blast_databases --mock-only

  mock-data-generator:
    build:
      context: ..
      dockerfile: Dockerfile
    volumes:
      - ../{self.config['mock_data']['output_dir']}:/app/data
      - ../{self.config['paths']['logs']}:/app/logs
    environment:
      - MOCK_DATA_DIR=/app/data
      - MOCK_NUM_PATIENTS={self.config['mock_data']['num_patients']}
      - MOCK_NUM_SAMPLES={self.config['mock_data']['num_samples']}
      - MOCK_SEED={self.config['mock_data']['seed']}
    command: python scripts/generate_mock_data.py --output-dir /app/data --num-patients {self.config['mock_data']['num_patients']} --num-samples {self.config['mock_data']['num_samples']}

volumes:
  blast_databases:
  mock_data:
  logs:
"""
        
        try:
            with open(compose_file, 'w') as f:
                f.write(compose_content)
            
            self.logger.info(f"Docker Compose file created: {compose_file}")
            return str(compose_file)
            
        except Exception as e:
            self.logger.error(f"Error creating Docker Compose file: {e}")
            return None
    
    def create_makefile(self) -> str:
        """Create Makefile for easy command execution."""
        makefile = self.scripts_dir / "Makefile"
        
        makefile_content = f"""# Auto-Generation Makefile
# Generated on {self.get_timestamp()}

.PHONY: help setup check-deps install-deps blast-db mock-data full-setup clean

help:
	@echo "Available commands:"
	@echo "  setup          - Run full setup process"
	@echo "  check-deps     - Check dependencies"
	@echo "  install-deps   - Install missing dependencies"
	@echo "  blast-db       - Generate BLAST databases"
	@echo "  mock-data      - Generate mock data"
	@echo "  full-setup     - Run complete setup"
	@echo "  clean          - Clean generated files"
	@echo "  docker-setup   - Run setup using Docker"

setup: check-deps install-deps full-setup

check-deps:
	python setup_auto_generation.py check-dependencies

install-deps:
	python setup_auto_generation.py install-dependencies

blast-db:
	python setup_auto_generation.py blast-databases

mock-data:
	python setup_auto_generation.py mock-data

full-setup:
	python setup_auto_generation.py full-setup

clean:
	rm -rf ../{self.config['blast_databases']['output_dir']}
	rm -rf ../{self.config['mock_data']['output_dir']}
	rm -rf ../{self.config['paths']['logs']}

docker-setup:
	docker-compose -f docker-compose.auto-generation.yml up --build
"""
        
        try:
            with open(makefile, 'w') as f:
                f.write(makefile_content)
            
            self.logger.info(f"Makefile created: {makefile}")
            return str(makefile)
            
        except Exception as e:
            self.logger.error(f"Error creating Makefile: {e}")
            return None
    
    def get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_documentation(self) -> str:
        """Generate documentation for auto-generation scripts."""
        doc_file = self.scripts_dir / "AUTO_GENERATION_README.md"
        
        doc_content = f"""# Auto-Generation Scripts Documentation

This directory contains scripts for automatically generating BLAST databases and mock data for the Cancer Genomics Analysis Suite.

## Overview

The auto-generation system consists of three main components:

1. **BLAST Database Generator** (`generate_blast_databases.py`)
2. **Mock Data Generator** (`generate_mock_data.py`)
3. **Setup Manager** (`setup_auto_generation.py`)

## Quick Start

### Full Setup
```bash
# Run complete setup
python setup_auto_generation.py full-setup

# Or use the Makefile
make setup
```

### Individual Components
```bash
# Generate BLAST databases only
python setup_auto_generation.py blast-databases

# Generate mock data only
python setup_auto_generation.py mock-data

# Check dependencies
python setup_auto_generation.py check-dependencies
```

## Configuration

Configuration is stored in `auto_generation_config.json`. You can modify this file to customize:

- Number of patients/samples to generate
- Cancer types to include
- BLAST database types
- Output directories
- API usage settings

## Generated Files

### BLAST Databases
- Location: `{self.config['blast_databases']['output_dir']}/`
- Types: cancer_genes, oncogenes, tumor_suppressors, cancer_proteins, dna_repair_genes
- Format: BLAST database files (.nhr, .nin, .nsq, etc.)

### Mock Data
- Location: `{self.config['mock_data']['output_dir']}/`
- Files:
  - `mock_clinical_data.csv` - Patient clinical information
  - `mock_expression_data.csv` - Gene expression data
  - `mock_mutation_data.csv` - Mutation/variant data
  - `mock_variant_annotations/` - Functional annotations
  - `mock_pathway_data.json` - Pathway information
  - `mock_protein_structures/` - PDB structure files
  - `mock_ngs_data.csv` - NGS file metadata

## Dependencies

### Python Packages
- numpy
- pandas
- biopython
- requests
- scipy

### External Tools
- BLAST suite (blastn, blastp, makeblastdb)

## Docker Support

Use Docker for isolated execution:

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.auto-generation.yml up --build

# Or use the Makefile
make docker-setup
```

## Troubleshooting

### Common Issues

1. **BLAST tools not found**
   - Install BLAST+ suite
   - Ensure tools are in PATH

2. **API connection issues**
   - Use `--no-api` flag for BLAST generation
   - Check internet connection

3. **Memory issues with large datasets**
   - Reduce number of patients/samples
   - Use smaller gene lists

### Logs

Check log files in the `{self.config['paths']['logs']}/` directory for detailed information about the generation process.

## Customization

### Adding New Cancer Types
Edit the configuration file to add new cancer types to the `cancer_types` list.

### Custom Gene Lists
Modify the `gene_list` in the configuration or pass custom lists to the scripts.

### Custom BLAST Databases
Use the `--custom-db` option with the BLAST generator to create databases from your own FASTA files.

## Support

For issues or questions:
1. Check the log files
2. Review the configuration
3. Ensure all dependencies are installed
4. Try running individual components

Generated on: {self.get_timestamp()}
"""
        
        try:
            with open(doc_file, 'w') as f:
                f.write(doc_content)
            
            self.logger.info(f"Documentation created: {doc_file}")
            return str(doc_file)
            
        except Exception as e:
            self.logger.error(f"Error creating documentation: {e}")
            return None


def main():
    """Main function to run the setup manager."""
    parser = argparse.ArgumentParser(
        description="Setup and manage auto-generation scripts for BLAST databases and mock data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full setup
  python setup_auto_generation.py full-setup
  
  # Check dependencies
  python setup_auto_generation.py check-dependencies
  
  # Generate only BLAST databases
  python setup_auto_generation.py blast-databases
  
  # Generate only mock data
  python setup_auto_generation.py mock-data
  
  # Install missing dependencies
  python setup_auto_generation.py install-dependencies
        """
    )
    
    parser.add_argument(
        "command",
        choices=[
            "full-setup", "check-dependencies", "install-dependencies",
            "blast-databases", "mock-data", "setup-dirs", "create-env",
            "create-docker", "create-makefile", "create-docs"
        ],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--config",
        default="auto_generation_config.json",
        help="Configuration file path (default: auto_generation_config.json)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize setup manager
    setup = AutoGenerationSetup(args.config)
    
    # Execute command
    if args.command == "full-setup":
        success = setup.run_full_setup()
        sys.exit(0 if success else 1)
    
    elif args.command == "check-dependencies":
        deps = setup.check_dependencies()
        python_ok = all(pkg_ok for pkg_ok in deps["python_packages"].values())
        tools_ok = all(tool_ok for tool_ok in deps["external_tools"].values())
        all_ok = python_ok and tools_ok
        sys.exit(0 if all_ok else 1)
    
    elif args.command == "install-dependencies":
        success = setup.install_dependencies()
        sys.exit(0 if success else 1)
    
    elif args.command == "blast-databases":
        success = setup.run_blast_database_generation()
        sys.exit(0 if success else 1)
    
    elif args.command == "mock-data":
        success = setup.run_mock_data_generation()
        sys.exit(0 if success else 1)
    
    elif args.command == "setup-dirs":
        setup.setup_directories()
    
    elif args.command == "create-env":
        setup.create_environment_file()
    
    elif args.command == "create-docker":
        setup.create_docker_compose()
    
    elif args.command == "create-makefile":
        setup.create_makefile()
    
    elif args.command == "create-docs":
        setup.generate_documentation()


if __name__ == "__main__":
    main()

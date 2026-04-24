#!/usr/bin/env python3
"""
BLAST Database Auto-Generation Script

This script automatically generates BLAST databases for the Cancer Genomics Analysis Suite.
It creates nucleotide and protein databases from various genomic data sources including:
- Reference genomes
- Gene sequences
- Protein sequences
- Custom cancer-related sequences

Usage:
    python generate_blast_databases.py [options]

Author: Cancer Genomics Analysis Suite
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_dna, generic_protein
import gzip
import json
from datetime import datetime

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.blast_pipeline import BlastPipeline, BlastConfig


class BlastDatabaseGenerator:
    """Auto-generates BLAST databases for cancer genomics analysis."""
    
    def __init__(self, output_dir: str = "blast_databases", log_level: str = "INFO"):
        """
        Initialize the BLAST database generator.
        
        Args:
            output_dir (str): Directory to store generated databases
            log_level (str): Logging level
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'blast_db_generation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Database configurations
        self.db_configs = {
            'cancer_genes': {
                'type': 'nucl',
                'description': 'Cancer-related gene sequences',
                'genes': [
                    'TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'MYC', 'PIK3CA',
                    'PTEN', 'APC', 'RB1', 'VHL', 'CDKN2A', 'MLH1', 'MSH2',
                    'ATM', 'CHEK2', 'PALB2', 'BARD1', 'RAD51C', 'RAD51D'
                ]
            },
            'oncogenes': {
                'type': 'nucl',
                'description': 'Oncogene sequences',
                'genes': [
                    'MYC', 'KRAS', 'EGFR', 'PIK3CA', 'BRAF', 'ALK', 'RET',
                    'MET', 'FGFR1', 'FGFR2', 'FGFR3', 'PDGFRA', 'KIT',
                    'ABL1', 'BCR', 'JAK2', 'FLT3', 'NPM1', 'MLL'
                ]
            },
            'tumor_suppressors': {
                'type': 'nucl',
                'description': 'Tumor suppressor gene sequences',
                'genes': [
                    'TP53', 'BRCA1', 'BRCA2', 'PTEN', 'APC', 'RB1', 'VHL',
                    'CDKN2A', 'MLH1', 'MSH2', 'MSH6', 'PMS2', 'ATM', 'CHEK2',
                    'PALB2', 'BARD1', 'RAD51C', 'RAD51D', 'NF1', 'NF2'
                ]
            },
            'cancer_proteins': {
                'type': 'prot',
                'description': 'Cancer-related protein sequences',
                'genes': [
                    'TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'MYC', 'PIK3CA',
                    'PTEN', 'APC', 'RB1', 'VHL', 'CDKN2A', 'MLH1', 'MSH2',
                    'ATM', 'CHEK2', 'PALB2', 'BARD1', 'RAD51C', 'RAD51D'
                ]
            },
            'dna_repair_genes': {
                'type': 'nucl',
                'description': 'DNA repair gene sequences',
                'genes': [
                    'BRCA1', 'BRCA2', 'ATM', 'CHEK2', 'PALB2', 'BARD1',
                    'RAD51C', 'RAD51D', 'MLH1', 'MSH2', 'MSH6', 'PMS2',
                    'XPA', 'XPC', 'XPD', 'XPF', 'ERCC1', 'ERCC2', 'ERCC3'
                ]
            }
        }
        
        # Ensembl REST API base URL
        self.ensembl_api = "https://rest.ensembl.org"
        
    def validate_blast_installation(self) -> bool:
        """Validate that BLAST tools are installed and accessible."""
        try:
            subprocess.run(["makeblastdb", "-version"], capture_output=True, check=True)
            subprocess.run(["blastn", "-version"], capture_output=True, check=True)
            subprocess.run(["blastp", "-version"], capture_output=True, check=True)
            self.logger.info("BLAST tools are properly installed")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"BLAST tools not found: {e}")
            return False
    
    def fetch_gene_sequence(self, gene_symbol: str, species: str = "human") -> Optional[SeqRecord]:
        """
        Fetch gene sequence from Ensembl API.
        
        Args:
            gene_symbol (str): Gene symbol
            species (str): Species name
            
        Returns:
            SeqRecord: Gene sequence record
        """
        try:
            # Get gene ID
            gene_url = f"{self.ensembl_api}/lookup/symbol/{species}/{gene_symbol}"
            response = requests.get(gene_url, headers={"Content-Type": "application/json"})
            
            if response.status_code != 200:
                self.logger.warning(f"Could not find gene {gene_symbol}: {response.status_code}")
                return None
            
            gene_data = response.json()
            gene_id = gene_data['id']
            
            # Get sequence
            seq_url = f"{self.ensembl_api}/sequence/id/{gene_id}"
            response = requests.get(seq_url, headers={"Content-Type": "text/plain"})
            
            if response.status_code != 200:
                self.logger.warning(f"Could not fetch sequence for {gene_symbol}")
                return None
            
            sequence = response.text.strip()
            
            # Create SeqRecord
            record = SeqRecord(
                Seq(sequence, generic_dna),
                id=gene_symbol,
                description=f"{gene_symbol} gene sequence from {species}"
            )
            
            self.logger.debug(f"Fetched sequence for {gene_symbol} ({len(sequence)} bp)")
            return record
            
        except Exception as e:
            self.logger.error(f"Error fetching sequence for {gene_symbol}: {e}")
            return None
    
    def fetch_protein_sequence(self, gene_symbol: str, species: str = "human") -> Optional[SeqRecord]:
        """
        Fetch protein sequence from Ensembl API.
        
        Args:
            gene_symbol (str): Gene symbol
            species (str): Species name
            
        Returns:
            SeqRecord: Protein sequence record
        """
        try:
            # Get gene ID
            gene_url = f"{self.ensembl_api}/lookup/symbol/{species}/{gene_symbol}"
            response = requests.get(gene_url, headers={"Content-Type": "application/json"})
            
            if response.status_code != 200:
                self.logger.warning(f"Could not find gene {gene_symbol}: {response.status_code}")
                return None
            
            gene_data = response.json()
            gene_id = gene_data['id']
            
            # Get protein sequence
            protein_url = f"{self.ensembl_api}/sequence/id/{gene_id}/protein"
            response = requests.get(protein_url, headers={"Content-Type": "text/plain"})
            
            if response.status_code != 200:
                self.logger.warning(f"Could not fetch protein sequence for {gene_symbol}")
                return None
            
            sequence = response.text.strip()
            
            # Create SeqRecord
            record = SeqRecord(
                Seq(sequence, generic_protein),
                id=gene_symbol,
                description=f"{gene_symbol} protein sequence from {species}"
            )
            
            self.logger.debug(f"Fetched protein sequence for {gene_symbol} ({len(sequence)} aa)")
            return record
            
        except Exception as e:
            self.logger.error(f"Error fetching protein sequence for {gene_symbol}: {e}")
            return None
    
    def generate_mock_sequences(self, gene_symbols: List[str], seq_type: str = "nucl") -> List[SeqRecord]:
        """
        Generate mock sequences for genes when API is unavailable.
        
        Args:
            gene_symbols (List[str]): List of gene symbols
            seq_type (str): Sequence type ('nucl' or 'prot')
            
        Returns:
            List[SeqRecord]: Generated sequence records
        """
        records = []
        
        for gene in gene_symbols:
            if seq_type == "nucl":
                # Generate mock DNA sequence (1000-5000 bp)
                import random
                length = random.randint(1000, 5000)
                sequence = ''.join(random.choices('ATCG', k=length))
                alphabet = generic_dna
                description = f"{gene} mock gene sequence"
            else:
                # Generate mock protein sequence (200-1000 aa)
                import random
                length = random.randint(200, 1000)
                sequence = ''.join(random.choices('ACDEFGHIKLMNPQRSTVWY', k=length))
                alphabet = generic_protein
                description = f"{gene} mock protein sequence"
            
            record = SeqRecord(
                Seq(sequence, alphabet),
                id=gene,
                description=description
            )
            records.append(record)
        
        self.logger.info(f"Generated {len(records)} mock {seq_type} sequences")
        return records
    
    def create_database(self, db_name: str, sequences: List[SeqRecord], 
                       db_type: str, description: str) -> str:
        """
        Create a BLAST database from sequences.
        
        Args:
            db_name (str): Database name
            sequences (List[SeqRecord]): Sequence records
            db_type (str): Database type ('nucl' or 'prot')
            description (str): Database description
            
        Returns:
            str: Path to created database
        """
        if not sequences:
            self.logger.warning(f"No sequences provided for database {db_name}")
            return None
        
        # Create temporary FASTA file
        temp_fasta = self.output_dir / f"{db_name}_temp.fasta"
        
        try:
            # Write sequences to temporary file
            with open(temp_fasta, 'w') as handle:
                SeqIO.write(sequences, handle, "fasta")
            
            self.logger.info(f"Created temporary FASTA file: {temp_fasta}")
            self.logger.info(f"Database contains {len(sequences)} sequences")
            
            # Create BLAST database
            db_path = self.output_dir / db_name
            
            cmd = [
                "makeblastdb",
                "-in", str(temp_fasta),
                "-dbtype", db_type,
                "-out", str(db_path),
                "-title", f"{db_name} - {description}",
                "-parse_seqids"
            ]
            
            self.logger.info(f"Creating BLAST database: {db_name}")
            self.logger.debug(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully created database: {db_path}")
                
                # Create database info file
                info_file = self.output_dir / f"{db_name}_info.json"
                info_data = {
                    "database_name": db_name,
                    "description": description,
                    "type": db_type,
                    "sequence_count": len(sequences),
                    "created_at": datetime.now().isoformat(),
                    "sequences": [{"id": seq.id, "description": seq.description, "length": len(seq)} for seq in sequences]
                }
                
                with open(info_file, 'w') as f:
                    json.dump(info_data, f, indent=2)
                
                return str(db_path)
            else:
                self.logger.error(f"Database creation failed: {result.stderr}")
                return None
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error creating database {db_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating database {db_name}: {e}")
            return None
        finally:
            # Clean up temporary file
            if temp_fasta.exists():
                temp_fasta.unlink()
    
    def generate_all_databases(self, use_api: bool = True, use_mock: bool = True) -> Dict[str, str]:
        """
        Generate all configured BLAST databases.
        
        Args:
            use_api (bool): Whether to use Ensembl API
            use_mock (bool): Whether to use mock sequences as fallback
            
        Returns:
            Dict[str, str]: Mapping of database names to paths
        """
        if not self.validate_blast_installation():
            self.logger.error("BLAST tools not available. Cannot generate databases.")
            return {}
        
        created_databases = {}
        
        for db_name, config in self.db_configs.items():
            self.logger.info(f"Generating database: {db_name}")
            
            sequences = []
            gene_symbols = config['genes']
            db_type = config['type']
            description = config['description']
            
            # Try to fetch sequences from API if enabled
            if use_api:
                self.logger.info(f"Fetching sequences from Ensembl API for {db_name}")
                for gene in gene_symbols:
                    if db_type == "nucl":
                        seq_record = self.fetch_gene_sequence(gene)
                    else:
                        seq_record = self.fetch_protein_sequence(gene)
                    
                    if seq_record:
                        sequences.append(seq_record)
                    else:
                        self.logger.warning(f"Could not fetch sequence for {gene}")
            
            # Use mock sequences if API failed or is disabled
            if not sequences and use_mock:
                self.logger.info(f"Using mock sequences for {db_name}")
                sequences = self.generate_mock_sequences(gene_symbols, db_type)
            
            if sequences:
                db_path = self.create_database(db_name, sequences, db_type, description)
                if db_path:
                    created_databases[db_name] = db_path
            else:
                self.logger.error(f"No sequences available for database {db_name}")
        
        return created_databases
    
    def create_custom_database(self, sequences_file: str, db_name: str, 
                              db_type: str, description: str = "") -> str:
        """
        Create a custom BLAST database from a FASTA file.
        
        Args:
            sequences_file (str): Path to FASTA file
            db_name (str): Database name
            db_type (str): Database type ('nucl' or 'prot')
            description (str): Database description
            
        Returns:
            str: Path to created database
        """
        if not os.path.exists(sequences_file):
            self.logger.error(f"Sequences file not found: {sequences_file}")
            return None
        
        try:
            # Read sequences
            sequences = list(SeqIO.parse(sequences_file, "fasta"))
            self.logger.info(f"Loaded {len(sequences)} sequences from {sequences_file}")
            
            return self.create_database(db_name, sequences, db_type, description)
            
        except Exception as e:
            self.logger.error(f"Error reading sequences file {sequences_file}: {e}")
            return None
    
    def generate_summary_report(self, databases: Dict[str, str]) -> str:
        """
        Generate a summary report of created databases.
        
        Args:
            databases (Dict[str, str]): Created databases
            
        Returns:
            str: Path to summary report
        """
        report_file = self.output_dir / "database_generation_summary.txt"
        
        with open(report_file, 'w') as f:
            f.write("BLAST Database Generation Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output directory: {self.output_dir}\n\n")
            
            f.write(f"Total databases created: {len(databases)}\n\n")
            
            for db_name, db_path in databases.items():
                f.write(f"Database: {db_name}\n")
                f.write(f"  Path: {db_path}\n")
                f.write(f"  Type: {self.db_configs[db_name]['type']}\n")
                f.write(f"  Description: {self.db_configs[db_name]['description']}\n")
                f.write(f"  Genes: {', '.join(self.db_configs[db_name]['genes'])}\n\n")
            
            f.write("Usage Instructions:\n")
            f.write("-" * 20 + "\n")
            f.write("To use these databases with the BLAST pipeline:\n\n")
            
            for db_name in databases.keys():
                f.write(f"# {db_name} database\n")
                f.write(f"config = BlastConfig(\n")
                f.write(f"    database_path='{databases[db_name]}',\n")
                f.write(f"    program='blastn' if '{self.db_configs[db_name]['type']}' == 'nucl' else 'blastp'\n")
                f.write(f")\n")
                f.write(f"pipeline = BlastPipeline(config)\n\n")
        
        self.logger.info(f"Summary report saved to: {report_file}")
        return str(report_file)


def main():
    """Main function to run the BLAST database generator."""
    parser = argparse.ArgumentParser(
        description="Auto-generate BLAST databases for cancer genomics analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all default databases
  python generate_blast_databases.py
  
  # Generate databases in custom directory
  python generate_blast_databases.py --output-dir /path/to/databases
  
  # Generate only using mock data (no API calls)
  python generate_blast_databases.py --no-api --mock-only
  
  # Create custom database from FASTA file
  python generate_blast_databases.py --custom-db my_sequences.fasta --db-name custom_db --db-type nucl
        """
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="blast_databases",
        help="Output directory for databases (default: blast_databases)"
    )
    
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Skip API calls and use only mock data"
    )
    
    parser.add_argument(
        "--mock-only",
        action="store_true",
        help="Use only mock sequences (implies --no-api)"
    )
    
    parser.add_argument(
        "--custom-db",
        help="Create custom database from FASTA file"
    )
    
    parser.add_argument(
        "--db-name",
        help="Name for custom database"
    )
    
    parser.add_argument(
        "--db-type",
        choices=["nucl", "prot"],
        default="nucl",
        help="Type for custom database (default: nucl)"
    )
    
    parser.add_argument(
        "--description",
        default="",
        help="Description for custom database"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = BlastDatabaseGenerator(
        output_dir=args.output_dir,
        log_level=args.log_level
    )
    
    # Handle custom database creation
    if args.custom_db:
        if not args.db_name:
            generator.logger.error("--db-name is required when using --custom-db")
            sys.exit(1)
        
        generator.logger.info(f"Creating custom database from {args.custom_db}")
        db_path = generator.create_custom_database(
            args.custom_db,
            args.db_name,
            args.db_type,
            args.description
        )
        
        if db_path:
            generator.logger.info(f"Custom database created successfully: {db_path}")
        else:
            generator.logger.error("Failed to create custom database")
            sys.exit(1)
        
        return
    
    # Generate all databases
    use_api = not args.no_api and not args.mock_only
    use_mock = args.mock_only or True  # Always allow mock as fallback
    
    generator.logger.info("Starting BLAST database generation...")
    databases = generator.generate_all_databases(use_api=use_api, use_mock=use_mock)
    
    if databases:
        generator.logger.info(f"Successfully created {len(databases)} databases")
        
        # Generate summary report
        generator.generate_summary_report(databases)
        
        generator.logger.info("Database generation completed successfully!")
    else:
        generator.logger.error("No databases were created")
        sys.exit(1)


if __name__ == "__main__":
    main()

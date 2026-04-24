"""
BLAST Pipeline Module

This module provides comprehensive BLAST sequence analysis pipeline capabilities
for the Cancer Genomics Analysis Suite, including sequence alignment, similarity
search, and result processing workflows.
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np
from Bio import SeqIO
from Bio.Blast import NCBIXML
from Bio.Blast.Applications import NcbiblastnCommandline, NcbiblastpCommandline


@dataclass
class BlastConfig:
    """BLAST configuration parameters."""
    database_path: str
    program: str = "blastn"  # blastn, blastp, blastx, tblastn, tblastx
    evalue: float = 1e-5
    max_target_seqs: int = 100
    word_size: int = 11
    gapopen: int = 5
    gapextend: int = 2
    penalty: int = -1
    reward: int = 1
    outfmt: str = "5"  # XML format
    num_threads: int = 4
    output_file: Optional[str] = None


@dataclass
class BlastResult:
    """BLAST result data structure."""
    query_id: str
    subject_id: str
    identity: float
    alignment_length: int
    mismatches: int
    gap_opens: int
    query_start: int
    query_end: int
    subject_start: int
    subject_end: int
    evalue: float
    bit_score: float
    query_sequence: str
    subject_sequence: str
    alignment: str


class BlastPipeline:
    """
    A comprehensive BLAST analysis pipeline for cancer genomics research.
    
    This class provides methods for sequence alignment, similarity search,
    and result processing using various BLAST programs.
    """
    
    def __init__(self, config: BlastConfig):
        """
        Initialize the BLAST pipeline.
        
        Args:
            config (BlastConfig): BLAST configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.results: List[BlastResult] = []
        
        # Validate BLAST installation
        self._validate_blast_installation()
    
    def _validate_blast_installation(self):
        """Validate that BLAST is installed and accessible."""
        try:
            if self.config.program == "blastn":
                subprocess.run(["blastn", "-version"], capture_output=True, check=True)
            elif self.config.program == "blastp":
                subprocess.run(["blastp", "-version"], capture_output=True, check=True)
            else:
                raise ValueError(f"Unsupported BLAST program: {self.config.program}")
            
            self.logger.info(f"BLAST {self.config.program} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"BLAST {self.config.program} is not installed or not in PATH")
    
    def run_blast(self, query_sequences: Union[str, List[str]], 
                  database_name: Optional[str] = None) -> str:
        """
        Run BLAST analysis on query sequences.
        
        Args:
            query_sequences (Union[str, List[str]]): Query sequences (file path or list of sequences)
            database_name (str, optional): Database name override
            
        Returns:
            str: Path to BLAST output file
        """
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as query_file:
            query_path = query_file.name
            
            if isinstance(query_sequences, str):
                # Assume it's a file path
                if os.path.exists(query_sequences):
                    with open(query_sequences, 'r') as f:
                        query_file.write(f.read())
                else:
                    # Treat as a single sequence
                    query_file.write(f">query_sequence\n{query_sequences}\n")
            else:
                # List of sequences
                for i, seq in enumerate(query_sequences):
                    query_file.write(f">query_{i}\n{seq}\n")
        
        # Determine output file
        if self.config.output_file:
            output_path = self.config.output_file
        else:
            output_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
            output_path = output_file.name
            output_file.close()
        
        # Build BLAST command
        if self.config.program == "blastn":
            blast_cmd = NcbiblastnCommandline(
                query=query_path,
                db=self.config.database_path,
                evalue=self.config.evalue,
                outfmt=self.config.outfmt,
                out=output_path,
                num_threads=self.config.num_threads,
                max_target_seqs=self.config.max_target_seqs,
                word_size=self.config.word_size,
                gapopen=self.config.gapopen,
                gapextend=self.config.gapextend,
                penalty=self.config.penalty,
                reward=self.config.reward
            )
        elif self.config.program == "blastp":
            blast_cmd = NcbiblastpCommandline(
                query=query_path,
                db=self.config.database_path,
                evalue=self.config.evalue,
                outfmt=self.config.outfmt,
                out=output_path,
                num_threads=self.config.num_threads,
                max_target_seqs=self.config.max_target_seqs,
                word_size=self.config.word_size,
                gapopen=self.config.gapopen,
                gapextend=self.config.gapextend
            )
        else:
            raise ValueError(f"Unsupported BLAST program: {self.config.program}")
        
        # Execute BLAST
        self.logger.info(f"Running BLAST {self.config.program} analysis...")
        self.logger.info(f"Command: {blast_cmd}")
        
        try:
            stdout, stderr = blast_cmd()
            
            if stderr:
                self.logger.warning(f"BLAST stderr: {stderr}")
            
            self.logger.info(f"BLAST analysis completed. Results saved to: {output_path}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"BLAST execution failed: {e}")
            raise
        
        finally:
            # Clean up temporary query file
            if os.path.exists(query_path):
                os.unlink(query_path)
        
        return output_path
    
    def parse_blast_results(self, blast_output_file: str) -> List[BlastResult]:
        """
        Parse BLAST XML results.
        
        Args:
            blast_output_file (str): Path to BLAST XML output file
            
        Returns:
            List[BlastResult]: Parsed BLAST results
        """
        results = []
        
        try:
            with open(blast_output_file, 'r') as handle:
                blast_records = NCBIXML.parse(handle)
                
                for blast_record in blast_records:
                    query_id = blast_record.query
                    
                    for alignment in blast_record.alignments:
                        subject_id = alignment.title
                        
                        for hsp in alignment.hsps:
                            result = BlastResult(
                                query_id=query_id,
                                subject_id=subject_id,
                                identity=hsp.identities / hsp.align_length * 100,
                                alignment_length=hsp.align_length,
                                mismatches=hsp.mismatches,
                                gap_opens=hsp.gap_opens,
                                query_start=hsp.query_start,
                                query_end=hsp.query_end,
                                subject_start=hsp.sbjct_start,
                                subject_end=hsp.sbjct_end,
                                evalue=hsp.expect,
                                bit_score=hsp.bits,
                                query_sequence=hsp.query,
                                subject_sequence=hsp.sbjct,
                                alignment=hsp.match
                            )
                            results.append(result)
            
            self.results = results
            self.logger.info(f"Parsed {len(results)} BLAST results")
            
        except Exception as e:
            self.logger.error(f"Error parsing BLAST results: {e}")
            raise
        
        return results
    
    def filter_results(self, min_identity: float = 80.0, 
                      max_evalue: float = 1e-5,
                      min_alignment_length: int = 50) -> List[BlastResult]:
        """
        Filter BLAST results based on criteria.
        
        Args:
            min_identity (float): Minimum identity percentage
            max_evalue (float): Maximum E-value
            min_alignment_length (int): Minimum alignment length
            
        Returns:
            List[BlastResult]: Filtered results
        """
        filtered_results = []
        
        for result in self.results:
            if (result.identity >= min_identity and
                result.evalue <= max_evalue and
                result.alignment_length >= min_alignment_length):
                filtered_results.append(result)
        
        self.logger.info(f"Filtered {len(filtered_results)} results from {len(self.results)} total")
        return filtered_results
    
    def results_to_dataframe(self, results: Optional[List[BlastResult]] = None) -> pd.DataFrame:
        """
        Convert BLAST results to pandas DataFrame.
        
        Args:
            results (List[BlastResult], optional): Results to convert (uses self.results if None)
            
        Returns:
            pd.DataFrame: Results as DataFrame
        """
        if results is None:
            results = self.results
        
        data = []
        for result in results:
            data.append({
                'query_id': result.query_id,
                'subject_id': result.subject_id,
                'identity': result.identity,
                'alignment_length': result.alignment_length,
                'mismatches': result.mismatches,
                'gap_opens': result.gap_opens,
                'query_start': result.query_start,
                'query_end': result.query_end,
                'subject_start': result.subject_start,
                'subject_end': result.subject_end,
                'evalue': result.evalue,
                'bit_score': result.bit_score
            })
        
        return pd.DataFrame(data)
    
    def get_top_hits(self, n: int = 10, 
                    sort_by: str = "bit_score") -> List[BlastResult]:
        """
        Get top N hits sorted by specified criteria.
        
        Args:
            n (int): Number of top hits to return
            sort_by (str): Sort criteria (bit_score, evalue, identity)
            
        Returns:
            List[BlastResult]: Top hits
        """
        if not self.results:
            return []
        
        # Sort results
        if sort_by == "bit_score":
            sorted_results = sorted(self.results, key=lambda x: x.bit_score, reverse=True)
        elif sort_by == "evalue":
            sorted_results = sorted(self.results, key=lambda x: x.evalue)
        elif sort_by == "identity":
            sorted_results = sorted(self.results, key=lambda x: x.identity, reverse=True)
        else:
            raise ValueError(f"Invalid sort criteria: {sort_by}")
        
        return sorted_results[:n]
    
    def create_blast_database(self, sequences_file: str, 
                            database_name: str,
                            db_type: str = "nucl") -> str:
        """
        Create a BLAST database from sequences.
        
        Args:
            sequences_file (str): Path to sequences file (FASTA format)
            database_name (str): Name for the database
            db_type (str): Database type (nucl for nucleotide, prot for protein)
            
        Returns:
            str: Path to created database
        """
        if db_type == "nucl":
            makeblastdb_cmd = "makeblastdb"
        elif db_type == "prot":
            makeblastdb_cmd = "makeblastdb"
        else:
            raise ValueError(f"Invalid database type: {db_type}")
        
        db_path = f"{database_name}"
        
        cmd = [
            makeblastdb_cmd,
            "-in", sequences_file,
            "-dbtype", db_type,
            "-out", db_path,
            "-title", database_name
        ]
        
        self.logger.info(f"Creating BLAST database: {database_name}")
        self.logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Database created successfully: {db_path}")
            return db_path
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Database creation failed: {e}")
            self.logger.error(f"stderr: {e.stderr}")
            raise
    
    def batch_blast_analysis(self, query_files: List[str], 
                           output_dir: str) -> Dict[str, str]:
        """
        Run BLAST analysis on multiple query files.
        
        Args:
            query_files (List[str]): List of query file paths
            output_dir (str): Output directory for results
            
        Returns:
            Dict[str, str]: Mapping of query file to output file
        """
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        
        for query_file in query_files:
            self.logger.info(f"Processing query file: {query_file}")
            
            # Generate output filename
            query_name = Path(query_file).stem
            output_file = os.path.join(output_dir, f"{query_name}_blast_results.xml")
            
            # Update config for this run
            self.config.output_file = output_file
            
            try:
                # Run BLAST
                result_file = self.run_blast(query_file)
                results[query_file] = result_file
                
                # Parse and save results
                blast_results = self.parse_blast_results(result_file)
                df = self.results_to_dataframe(blast_results)
                
                # Save as CSV
                csv_file = os.path.join(output_dir, f"{query_name}_blast_results.csv")
                df.to_csv(csv_file, index=False)
                
                self.logger.info(f"Results saved to: {csv_file}")
                
            except Exception as e:
                self.logger.error(f"Error processing {query_file}: {e}")
                results[query_file] = None
        
        return results
    
    def generate_summary_report(self, output_file: str):
        """
        Generate a summary report of BLAST results.
        
        Args:
            output_file (str): Path to output report file
        """
        if not self.results:
            self.logger.warning("No results to summarize")
            return
        
        df = self.results_to_dataframe()
        
        with open(output_file, 'w') as f:
            f.write("BLAST Analysis Summary Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total number of hits: {len(self.results)}\n")
            f.write(f"Number of unique queries: {df['query_id'].nunique()}\n")
            f.write(f"Number of unique subjects: {df['subject_id'].nunique()}\n\n")
            
            f.write("Identity Statistics:\n")
            f.write(f"  Mean: {df['identity'].mean():.2f}%\n")
            f.write(f"  Median: {df['identity'].median():.2f}%\n")
            f.write(f"  Min: {df['identity'].min():.2f}%\n")
            f.write(f"  Max: {df['identity'].max():.2f}%\n\n")
            
            f.write("E-value Statistics:\n")
            f.write(f"  Mean: {df['evalue'].mean():.2e}\n")
            f.write(f"  Median: {df['evalue'].median():.2e}\n")
            f.write(f"  Min: {df['evalue'].min():.2e}\n")
            f.write(f"  Max: {df['evalue'].max():.2e}\n\n")
            
            f.write("Bit Score Statistics:\n")
            f.write(f"  Mean: {df['bit_score'].mean():.2f}\n")
            f.write(f"  Median: {df['bit_score'].median():.2f}\n")
            f.write(f"  Min: {df['bit_score'].min():.2f}\n")
            f.write(f"  Max: {df['bit_score'].max():.2f}\n\n")
            
            f.write("Top 10 Hits by Bit Score:\n")
            top_hits = self.get_top_hits(10, "bit_score")
            for i, hit in enumerate(top_hits, 1):
                f.write(f"  {i}. {hit.subject_id} (Score: {hit.bit_score:.2f}, "
                       f"Identity: {hit.identity:.2f}%, E-value: {hit.evalue:.2e})\n")
        
        self.logger.info(f"Summary report saved to: {output_file}")
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """
        Clean up temporary files.
        
        Args:
            file_paths (List[str]): List of file paths to remove
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Could not remove {file_path}: {e}")

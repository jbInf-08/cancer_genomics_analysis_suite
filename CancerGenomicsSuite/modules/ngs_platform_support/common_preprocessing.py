"""
Common Preprocessing Utilities for NGS Platforms

This module provides shared preprocessing utilities that can be used across
different NGS platforms (Illumina, Ion Torrent, PacBio, Nanopore).
Includes FASTQ processing, quality trimming, adapter removal, contaminant filtering,
read deduplication, and quality metrics calculation.
"""

import os
import subprocess
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import json
import gzip
import time
from datetime import datetime
import warnings
from collections import defaultdict, Counter

# Try to import bioinformatics libraries
try:
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    logging.warning("Biopython not available. Some sequence operations will be limited.")

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class FastqProcessor:
    """
    General FASTQ file processing utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools = {
            "fastp": "fastp",
            "cutadapt": "cutadapt",
            "trimmomatic": "trimmomatic",
            "seqtk": "seqtk"
        }
    
    def process_fastq(self, input_file: str, output_file: str, 
                     operations: List[str]) -> Dict[str, Any]:
        """
        Process FASTQ file with specified operations.
        
        Args:
            input_file: Input FASTQ file path
            output_file: Output FASTQ file path
            operations: List of operations to perform
            
        Returns:
            Processing results
        """
        try:
            current_file = input_file
            results = {"operations": []}
            
            for operation in operations:
                if operation == "quality_trim":
                    result = self._quality_trim(current_file, output_file)
                elif operation == "adapter_trim":
                    result = self._adapter_trim(current_file, output_file)
                elif operation == "length_filter":
                    result = self._length_filter(current_file, output_file)
                elif operation == "quality_filter":
                    result = self._quality_filter(current_file, output_file)
                elif operation == "deduplicate":
                    result = self._deduplicate(current_file, output_file)
                else:
                    result = {"status": "skipped", "reason": f"Unknown operation: {operation}"}
                
                results["operations"].append({
                    "operation": operation,
                    "result": result
                })
                
                if result.get("status") == "success":
                    current_file = result.get("output_file", current_file)
            
            return {
                "status": "success",
                "final_file": current_file,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"FASTQ processing failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _quality_trim(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Quality-based trimming."""
        try:
            cmd = [
                self.tools["fastp"],
                "-i", input_file,
                "-o", output_file,
                "-q", "20",  # Quality threshold
                "-l", "50",  # Minimum length
                "--thread", "4"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "output_file": output_file,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _adapter_trim(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Adapter trimming."""
        try:
            cmd = [
                self.tools["cutadapt"],
                "-a", "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA",  # Illumina adapter
                "-o", output_file,
                "--threads", "4",
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "output_file": output_file,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _length_filter(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Length-based filtering."""
        try:
            cmd = [
                self.tools["seqtk"],
                "seq",
                "-L", "50",  # Minimum length
                input_file
            ]
            
            with open(output_file, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "output_file": output_file,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _quality_filter(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Quality-based filtering."""
        try:
            cmd = [
                self.tools["seqtk"],
                "fqchk",
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Simple quality filtering using seqtk
            cmd = [
                self.tools["seqtk"],
                "seq",
                "-q", "20",  # Quality threshold
                input_file
            ]
            
            with open(output_file, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "output_file": output_file,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _deduplicate(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Remove duplicate reads."""
        try:
            if not BIOPYTHON_AVAILABLE:
                return {"status": "failed", "error": "Biopython not available"}
            
            seen_sequences = set()
            unique_records = []
            
            with open(input_file, 'r') as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    seq = str(record.seq)
                    if seq not in seen_sequences:
                        seen_sequences.add(seq)
                        unique_records.append(record)
            
            with open(output_file, 'w') as handle:
                SeqIO.write(unique_records, handle, "fastq")
            
            return {
                "status": "success",
                "output_file": output_file,
                "duplicates_removed": len(seen_sequences) - len(unique_records)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}


class QualityTrimmer:
    """
    Quality-based trimming utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools = {
            "fastp": "fastp",
            "trimmomatic": "trimmomatic",
            "seqtk": "seqtk"
        }
    
    def trim_quality(self, input_files: Union[str, Dict[str, str]], 
                    output_dir: Path, quality_threshold: int = 20,
                    min_length: int = 50) -> Dict[str, str]:
        """
        Trim reads based on quality scores.
        
        Args:
            input_files: Input file(s) - single file path or dict of file paths
            output_dir: Output directory
            quality_threshold: Quality score threshold
            min_length: Minimum read length after trimming
            
        Returns:
            Dictionary of trimmed file paths
        """
        trimmed_files = {}
        
        if isinstance(input_files, str):
            input_files = {"input": input_files}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_quality_trimmed.fastq.gz"
                
                try:
                    result = self._trim_single_file(
                        file_path, output_file, quality_threshold, min_length
                    )
                    
                    if result["status"] == "success":
                        trimmed_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Quality trimming failed for {file_path}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error trimming {file_path}: {str(e)}")
        
        return trimmed_files
    
    def _trim_single_file(self, input_file: str, output_file: str, 
                         quality_threshold: int, min_length: int) -> Dict[str, Any]:
        """Trim a single file."""
        try:
            # Use fastp for quality trimming
            cmd = [
                self.tools["fastp"],
                "-i", input_file,
                "-o", str(output_file),
                "-q", str(quality_threshold),
                "-l", str(min_length),
                "--thread", str(self.config.get("threads", 4)),
                "--json", str(output_file.with_suffix('.json')),
                "--html", str(output_file.with_suffix('.html'))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse fastp results
                stats = self._parse_fastp_results(output_file.with_suffix('.json'))
                return {
                    "status": "success",
                    "output_file": str(output_file),
                    "statistics": stats
                }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_fastp_results(self, json_file: Path) -> Dict[str, Any]:
        """Parse fastp JSON results."""
        try:
            if json_file.exists():
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                return {
                    "before_filtering": data.get("summary", {}).get("before_filtering", {}),
                    "after_filtering": data.get("summary", {}).get("after_filtering", {}),
                    "filtering_result": data.get("summary", {}).get("filtering_result", {})
                }
            else:
                return {"error": "JSON file not found"}
                
        except Exception as e:
            return {"error": str(e)}


class AdapterRemover:
    """
    Adapter sequence removal utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools = {
            "cutadapt": "cutadapt",
            "fastp": "fastp",
            "trimmomatic": "trimmomatic"
        }
        
        # Common adapter sequences
        self.adapters = {
            "illumina": {
                "universal": "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA",
                "indexed": "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA"
            },
            "ion_torrent": {
                "adapter": "ATCTCGTATGCCGTCTTCTGCTTG"
            },
            "pacbio": {
                "adapter": "ATCTCTCTCAACAACAACAACGGAGGAGGAGGAAAAGAGAGAGAT"
            },
            "nanopore": {
                "adapter": "AATGTACTTCGTTCAGTTACGTATTGCT"
            }
        }
    
    def remove_adapters(self, input_files: Union[str, Dict[str, str]], 
                       output_dir: Path, platform: str = "illumina") -> Dict[str, str]:
        """
        Remove adapter sequences from reads.
        
        Args:
            input_files: Input file(s)
            output_dir: Output directory
            platform: Sequencing platform
            
        Returns:
            Dictionary of adapter-trimmed file paths
        """
        adapter_trimmed_files = {}
        
        if isinstance(input_files, str):
            input_files = {"input": input_files}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_adapter_trimmed.fastq.gz"
                
                try:
                    result = self._remove_adapters_single_file(
                        file_path, output_file, platform
                    )
                    
                    if result["status"] == "success":
                        adapter_trimmed_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Adapter removal failed for {file_path}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error removing adapters from {file_path}: {str(e)}")
        
        return adapter_trimmed_files
    
    def _remove_adapters_single_file(self, input_file: str, output_file: str, 
                                   platform: str) -> Dict[str, Any]:
        """Remove adapters from a single file."""
        try:
            # Get adapter sequences for platform
            platform_adapters = self.adapters.get(platform, self.adapters["illumina"])
            
            # Use cutadapt for adapter removal
            cmd = [
                self.tools["cutadapt"],
                "--threads", str(self.config.get("threads", 4)),
                "--minimum-length", "20",
                "--output", str(output_file)
            ]
            
            # Add adapter sequences
            for adapter_name, adapter_seq in platform_adapters.items():
                cmd.extend(["-a", adapter_seq])
            
            cmd.append(input_file)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse cutadapt output
                stats = self._parse_cutadapt_output(result.stdout)
                return {
                    "status": "success",
                    "output_file": str(output_file),
                    "statistics": stats
                }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_cutadapt_output(self, stdout: str) -> Dict[str, Any]:
        """Parse cutadapt output statistics."""
        try:
            stats = {}
            lines = stdout.strip().split('\n')
            
            for line in lines:
                if "Total reads processed:" in line:
                    stats["total_reads"] = int(line.split(":")[1].strip().replace(",", ""))
                elif "Reads with adapters:" in line:
                    stats["reads_with_adapters"] = int(line.split(":")[1].strip().replace(",", ""))
                elif "Reads written (passing filters):" in line:
                    stats["reads_written"] = int(line.split(":")[1].strip().replace(",", ""))
                elif "Total basepairs processed:" in line:
                    stats["total_bp"] = int(line.split(":")[1].strip().replace(",", ""))
                elif "Total written (filtered):" in line:
                    stats["bp_written"] = int(line.split(":")[1].strip().replace(",", ""))
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}


class ContaminantFilter:
    """
    Contaminant filtering utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools = {
            "fastp": "fastp",
            "bwa": "bwa",
            "bowtie2": "bowtie2"
        }
        
        # Common contaminant sequences
        self.contaminants = {
            "phix": "phix174.fasta",
            "ecoli": "ecoli.fasta",
            "human": "human_contamination.fasta",
            "adapter": "adapter_sequences.fasta"
        }
    
    def filter_contaminants(self, input_files: Union[str, Dict[str, str]], 
                           output_dir: Path, 
                           contaminant_type: str = "phix") -> Dict[str, str]:
        """
        Filter out contaminant sequences.
        
        Args:
            input_files: Input file(s)
            output_dir: Output directory
            contaminant_type: Type of contaminant to filter
            
        Returns:
            Dictionary of filtered file paths
        """
        filtered_files = {}
        
        if isinstance(input_files, str):
            input_files = {"input": input_files}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_contaminant_filtered.fastq.gz"
                
                try:
                    result = self._filter_contaminants_single_file(
                        file_path, output_file, contaminant_type
                    )
                    
                    if result["status"] == "success":
                        filtered_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Contaminant filtering failed for {file_path}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error filtering contaminants from {file_path}: {str(e)}")
        
        return filtered_files
    
    def _filter_contaminants_single_file(self, input_file: str, output_file: str, 
                                       contaminant_type: str) -> Dict[str, Any]:
        """Filter contaminants from a single file."""
        try:
            # Use fastp for contaminant filtering
            cmd = [
                self.tools["fastp"],
                "-i", input_file,
                "-o", str(output_file),
                "--thread", str(self.config.get("threads", 4))
            ]
            
            # Add contaminant filtering if reference available
            contaminant_ref = self.contaminants.get(contaminant_type)
            if contaminant_ref and os.path.exists(contaminant_ref):
                cmd.extend(["--adapter_fasta", contaminant_ref])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "output_file": str(output_file),
                    "contaminant_type": contaminant_type
                }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }


class ReadDeduplicator:
    """
    Read deduplication utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools = {
            "fastp": "fastp",
            "seqtk": "seqtk"
        }
    
    def deduplicate_reads(self, input_files: Union[str, Dict[str, str]], 
                         output_dir: Path) -> Dict[str, str]:
        """
        Remove duplicate reads.
        
        Args:
            input_files: Input file(s)
            output_dir: Output directory
            
        Returns:
            Dictionary of deduplicated file paths
        """
        deduplicated_files = {}
        
        if isinstance(input_files, str):
            input_files = {"input": input_files}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_deduplicated.fastq.gz"
                
                try:
                    result = self._deduplicate_single_file(file_path, output_file)
                    
                    if result["status"] == "success":
                        deduplicated_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Deduplication failed for {file_path}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error deduplicating {file_path}: {str(e)}")
        
        return deduplicated_files
    
    def _deduplicate_single_file(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Deduplicate reads in a single file."""
        try:
            if not BIOPYTHON_AVAILABLE:
                return {"status": "failed", "error": "Biopython not available"}
            
            seen_sequences = set()
            unique_records = []
            duplicate_count = 0
            
            # Handle gzipped files
            open_func = gzip.open if input_file.endswith('.gz') else open
            mode = 'rt' if input_file.endswith('.gz') else 'r'
            
            with open_func(input_file, mode) as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    seq = str(record.seq)
                    if seq not in seen_sequences:
                        seen_sequences.add(seq)
                        unique_records.append(record)
                    else:
                        duplicate_count += 1
            
            # Write unique records
            open_func_out = gzip.open if str(output_file).endswith('.gz') else open
            mode_out = 'wt' if str(output_file).endswith('.gz') else 'w'
            
            with open_func_out(output_file, mode_out) as handle:
                SeqIO.write(unique_records, handle, "fastq")
            
            return {
                "status": "success",
                "output_file": str(output_file),
                "total_reads": len(seen_sequences) + duplicate_count,
                "unique_reads": len(unique_records),
                "duplicates_removed": duplicate_count
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }


class QualityMetrics:
    """
    Quality metrics calculation utilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def calculate_metrics(self, input_files: Union[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Calculate comprehensive quality metrics.
        
        Args:
            input_files: Input file(s)
            
        Returns:
            Quality metrics dictionary
        """
        if isinstance(input_files, str):
            input_files = {"input": input_files}
        
        metrics = {}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                try:
                    file_metrics = self._calculate_file_metrics(file_path)
                    metrics[file_type] = file_metrics
                except Exception as e:
                    logger.error(f"Failed to calculate metrics for {file_path}: {str(e)}")
                    metrics[file_type] = {"error": str(e)}
        
        return metrics
    
    def _calculate_file_metrics(self, file_path: str) -> Dict[str, Any]:
        """Calculate metrics for a single file."""
        if not BIOPYTHON_AVAILABLE:
            return {"error": "Biopython not available"}
        
        try:
            total_reads = 0
            total_bases = 0
            quality_scores = []
            read_lengths = []
            gc_counts = []
            n_counts = []
            
            # Handle gzipped files
            open_func = gzip.open if file_path.endswith('.gz') else open
            mode = 'rt' if file_path.endswith('.gz') else 'r'
            
            with open_func(file_path, mode) as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    total_reads += 1
                    seq_length = len(record.seq)
                    total_bases += seq_length
                    read_lengths.append(seq_length)
                    
                    # Quality scores
                    if hasattr(record, 'letter_annotations'):
                        quals = record.letter_annotations.get('phred_quality', [])
                        if quals:
                            quality_scores.extend(quals)
                    
                    # GC content
                    seq = str(record.seq).upper()
                    gc_count = seq.count('G') + seq.count('C')
                    gc_counts.append(gc_count)
                    
                    # N content
                    n_count = seq.count('N')
                    n_counts.append(n_count)
            
            if total_reads == 0:
                return {"error": "No reads found"}
            
            # Calculate statistics
            metrics = {
                "total_reads": total_reads,
                "total_bases": total_bases,
                "average_read_length": np.mean(read_lengths),
                "median_read_length": np.median(read_lengths),
                "min_read_length": np.min(read_lengths),
                "max_read_length": np.max(read_lengths),
                "std_read_length": np.std(read_lengths),
                "average_gc_content": (np.sum(gc_counts) / total_bases * 100) if total_bases > 0 else 0,
                "average_n_content": (np.sum(n_counts) / total_bases * 100) if total_bases > 0 else 0
            }
            
            # Quality statistics
            if quality_scores:
                metrics.update({
                    "average_quality": np.mean(quality_scores),
                    "median_quality": np.median(quality_scores),
                    "min_quality": np.min(quality_scores),
                    "max_quality": np.max(quality_scores),
                    "std_quality": np.std(quality_scores),
                    "q20_percentage": (np.sum(np.array(quality_scores) >= 20) / len(quality_scores) * 100),
                    "q30_percentage": (np.sum(np.array(quality_scores) >= 30) / len(quality_scores) * 100)
                })
            
            # Length distribution
            metrics["length_distribution"] = {
                "short_reads": len([x for x in read_lengths if x < 100]),
                "medium_reads": len([x for x in read_lengths if 100 <= x < 1000]),
                "long_reads": len([x for x in read_lengths if x >= 1000])
            }
            
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_quality_report(self, metrics: Dict[str, Any], 
                               output_file: str) -> Dict[str, Any]:
        """Generate a comprehensive quality report."""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {},
                "detailed_metrics": metrics,
                "recommendations": []
            }
            
            # Generate summary
            total_reads = sum(m.get("total_reads", 0) for m in metrics.values() if isinstance(m, dict) and "error" not in m)
            total_bases = sum(m.get("total_bases", 0) for m in metrics.values() if isinstance(m, dict) and "error" not in m)
            
            report["summary"] = {
                "total_files": len(metrics),
                "total_reads": total_reads,
                "total_bases": total_bases,
                "average_read_length": total_bases / total_reads if total_reads > 0 else 0
            }
            
            # Generate recommendations
            recommendations = []
            for file_type, file_metrics in metrics.items():
                if isinstance(file_metrics, dict) and "error" not in file_metrics:
                    if file_metrics.get("average_quality", 0) < 20:
                        recommendations.append(f"Low quality in {file_type}: consider quality trimming")
                    
                    if file_metrics.get("average_n_content", 0) > 5:
                        recommendations.append(f"High N content in {file_type}: check for sequencing issues")
                    
                    if file_metrics.get("q20_percentage", 0) < 80:
                        recommendations.append(f"Low Q20 percentage in {file_type}: consider quality filtering")
            
            report["recommendations"] = list(set(recommendations))
            
            # Write report to file
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            return {
                "status": "success",
                "report_file": output_file,
                "report": report
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }


class PreprocessingPipeline:
    """
    Comprehensive preprocessing pipeline orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.fastq_processor = FastqProcessor(self.config)
        self.quality_trimmer = QualityTrimmer(self.config)
        self.adapter_remover = AdapterRemover(self.config)
        self.contaminant_filter = ContaminantFilter(self.config)
        self.read_deduplicator = ReadDeduplicator(self.config)
        self.quality_metrics = QualityMetrics(self.config)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default preprocessing configuration."""
        return {
            "quality_threshold": 20,
            "min_length": 50,
            "adapter_trimming": True,
            "quality_trimming": True,
            "contaminant_filtering": True,
            "deduplication": True,
            "platform": "illumina",
            "threads": 4,
            "output_dir": "./preprocessing_output"
        }
    
    def run_preprocessing_pipeline(self, input_files: Union[str, Dict[str, str]], 
                                  sample_id: str) -> Dict[str, Any]:
        """
        Run the complete preprocessing pipeline.
        
        Args:
            input_files: Input file(s)
            sample_id: Sample identifier
            
        Returns:
            Preprocessing results
        """
        try:
            logger.info(f"Starting preprocessing pipeline for sample {sample_id}")
            
            # Create output directory
            output_dir = Path(self.config["output_dir"]) / sample_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            results = {
                "sample_id": sample_id,
                "pipeline_start": datetime.now().isoformat(),
                "input_files": input_files,
                "config": self.config,
                "steps": {}
            }
            
            current_files = input_files
            
            # Step 1: Initial quality assessment
            logger.info("Running initial quality assessment...")
            initial_metrics = self.quality_metrics.calculate_metrics(current_files)
            results["steps"]["initial_quality"] = initial_metrics
            
            # Step 2: Quality trimming
            if self.config.get("quality_trimming", True):
                logger.info("Running quality trimming...")
                trimmed_files = self.quality_trimmer.trim_quality(
                    current_files, output_dir, 
                    self.config["quality_threshold"], 
                    self.config["min_length"]
                )
                results["steps"]["quality_trimming"] = trimmed_files
                current_files = trimmed_files
            
            # Step 3: Adapter removal
            if self.config.get("adapter_trimming", True):
                logger.info("Running adapter removal...")
                adapter_trimmed_files = self.adapter_remover.remove_adapters(
                    current_files, output_dir, self.config.get("platform", "illumina")
                )
                results["steps"]["adapter_removal"] = adapter_trimmed_files
                current_files = adapter_trimmed_files
            
            # Step 4: Contaminant filtering
            if self.config.get("contaminant_filtering", True):
                logger.info("Running contaminant filtering...")
                filtered_files = self.contaminant_filter.filter_contaminants(
                    current_files, output_dir
                )
                results["steps"]["contaminant_filtering"] = filtered_files
                current_files = filtered_files
            
            # Step 5: Deduplication
            if self.config.get("deduplication", True):
                logger.info("Running deduplication...")
                deduplicated_files = self.read_deduplicator.deduplicate_reads(
                    current_files, output_dir
                )
                results["steps"]["deduplication"] = deduplicated_files
                current_files = deduplicated_files
            
            # Step 6: Final quality assessment
            logger.info("Running final quality assessment...")
            final_metrics = self.quality_metrics.calculate_metrics(current_files)
            results["steps"]["final_quality"] = final_metrics
            
            # Step 7: Generate quality report
            logger.info("Generating quality report...")
            report_file = output_dir / "quality_report.json"
            report_result = self.quality_metrics.generate_quality_report(
                {"initial": initial_metrics, "final": final_metrics}, 
                str(report_file)
            )
            results["steps"]["quality_report"] = report_result
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["status"] = "completed"
            results["final_files"] = current_files
            
            logger.info(f"Preprocessing pipeline completed successfully for sample {sample_id}")
            return results
            
        except Exception as e:
            logger.error(f"Preprocessing pipeline failed: {str(e)}")
            return {
                "sample_id": sample_id,
                "status": "failed",
                "error": str(e)
            }
    
    def run_custom_pipeline(self, input_files: Union[str, Dict[str, str]], 
                           operations: List[str], output_dir: Path) -> Dict[str, Any]:
        """
        Run a custom preprocessing pipeline with specified operations.
        
        Args:
            input_files: Input file(s)
            operations: List of operations to perform
            output_dir: Output directory
            
        Returns:
            Pipeline results
        """
        try:
            logger.info(f"Running custom preprocessing pipeline with operations: {operations}")
            
            results = {
                "operations": operations,
                "pipeline_start": datetime.now().isoformat(),
                "steps": {}
            }
            
            current_files = input_files
            
            for i, operation in enumerate(operations):
                logger.info(f"Running operation {i+1}/{len(operations)}: {operation}")
                
                if operation == "quality_trim":
                    step_files = self.quality_trimmer.trim_quality(current_files, output_dir)
                elif operation == "adapter_trim":
                    step_files = self.adapter_remover.remove_adapters(current_files, output_dir)
                elif operation == "contaminant_filter":
                    step_files = self.contaminant_filter.filter_contaminants(current_files, output_dir)
                elif operation == "deduplicate":
                    step_files = self.read_deduplicator.deduplicate_reads(current_files, output_dir)
                else:
                    logger.warning(f"Unknown operation: {operation}")
                    step_files = current_files
                
                results["steps"][operation] = step_files
                current_files = step_files
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["status"] = "completed"
            results["final_files"] = current_files
            
            return results
            
        except Exception as e:
            logger.error(f"Custom preprocessing pipeline failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

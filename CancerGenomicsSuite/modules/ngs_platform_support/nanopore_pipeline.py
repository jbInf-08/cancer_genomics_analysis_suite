"""
Oxford Nanopore Sequencing Pipeline

This module provides comprehensive support for Oxford Nanopore sequencing platforms,
including basecalling, quality control, alignment, variant calling, assembly, and analysis.
Supports various Nanopore platforms: MinION, GridION, PromethION, and Flongle.
"""

import os
import subprocess
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import json
import time
from datetime import datetime
import warnings

# Try to import bioinformatics libraries
try:
    import pysam
    PYSAM_AVAILABLE = True
except ImportError:
    PYSAM_AVAILABLE = False
    logging.warning("pysam not available. Some BAM operations will be limited.")

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


class NanoporePipeline:
    """
    Main Oxford Nanopore sequencing pipeline orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Nanopore pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.platform_info = self._get_platform_info()
        self.basecalling = NanoporeBasecalling(self.config)
        self.quality_control = NanoporeQualityControl(self.config)
        self.alignment = NanoporeAlignment(self.config)
        self.variant_calling = NanoporeVariantCalling(self.config)
        self.assembly = NanoporeAssembly(self.config)
        
        # Pipeline state
        self.current_step = None
        self.pipeline_status = "initialized"
        self.results = {}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default pipeline configuration."""
        return {
            "platform": "nanopore",
            "read_type": "long_read",
            "read_length": 15000,  # Average read length
            "quality_threshold": 7,  # Q-score threshold
            "basecalling": True,  # Run basecalling from raw data
            "adapter_trimming": True,
            "quality_trimming": True,
            "duplicate_removal": True,
            "alignment_tool": "minimap2",  # minimap2, ngmlr, graphmap2
            "variant_caller": "clair3",  # clair3, deepvariant, medaka
            "assembly_tool": "flye",  # flye, canu, wtdbg2
            "reference_genome": None,
            "annotation_file": None,
            "output_dir": "./nanopore_output",
            "threads": 8,
            "memory": "32G",
            "temp_dir": "./temp"
        }
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get Nanopore platform-specific information."""
        return {
            "supported_platforms": ["minion", "gridion", "promethion", "flongle"],
            "read_lengths": {
                "minion": [1000, 10000, 50000, 100000],
                "gridion": [2000, 15000, 60000, 200000],
                "promethion": [5000, 25000, 100000, 500000],
                "flongle": [500, 5000, 20000, 50000]
            },
            "throughput": {
                "minion": "low",
                "gridion": "medium",
                "promethion": "very_high",
                "flongle": "very_low"
            },
            "error_rates": {
                "minion": 0.12,
                "gridion": 0.10,
                "promethion": 0.08,
                "flongle": 0.15
            },
            "basecalling_accuracy": {
                "minion": 0.88,
                "gridion": 0.90,
                "promethion": 0.92,
                "flongle": 0.85
            }
        }
    
    def run_full_pipeline(self, input_files: Dict[str, str], 
                         sample_id: str) -> Dict[str, Any]:
        """
        Run the complete Nanopore sequencing pipeline.
        
        Args:
            input_files: Dictionary with 'fast5' or 'fastq' file paths
            sample_id: Sample identifier
            
        Returns:
            Pipeline results dictionary
        """
        try:
            logger.info(f"Starting Nanopore pipeline for sample {sample_id}")
            self.pipeline_status = "running"
            
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
            
            # Step 1: Basecalling (if raw FAST5 files provided)
            if "fast5" in input_files and self.config.get("basecalling", True):
                self.current_step = "basecalling"
                logger.info("Running basecalling...")
                basecalling_results = self.basecalling.run_basecalling(input_files["fast5"], output_dir)
                results["steps"]["basecalling"] = basecalling_results
                input_files["fastq"] = basecalling_results["fastq_file"]
            
            # Step 2: Quality Control
            self.current_step = "quality_control"
            logger.info("Running quality control...")
            qc_results = self.quality_control.run_quality_control(input_files, output_dir)
            results["steps"]["quality_control"] = qc_results
            
            # Step 3: Preprocessing
            self.current_step = "preprocessing"
            logger.info("Running preprocessing...")
            preprocessed_files = self._run_preprocessing(input_files, output_dir)
            results["steps"]["preprocessing"] = preprocessed_files
            
            # Step 4: Alignment
            self.current_step = "alignment"
            logger.info("Running alignment...")
            alignment_results = self.alignment.run_alignment(preprocessed_files, output_dir)
            results["steps"]["alignment"] = alignment_results
            
            # Step 5: Variant Calling
            self.current_step = "variant_calling"
            logger.info("Running variant calling...")
            variant_results = self.variant_calling.run_variant_calling(
                alignment_results["bam_file"], output_dir
            )
            results["steps"]["variant_calling"] = variant_results
            
            # Step 6: Assembly (if requested)
            if self.config.get("run_assembly", False):
                self.current_step = "assembly"
                logger.info("Running assembly...")
                assembly_results = self.assembly.run_assembly(preprocessed_files, output_dir)
                results["steps"]["assembly"] = assembly_results
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["status"] = "completed"
            self.pipeline_status = "completed"
            
            logger.info(f"Nanopore pipeline completed successfully for sample {sample_id}")
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed at step {self.current_step}: {str(e)}")
            self.pipeline_status = "failed"
            return {
                "sample_id": sample_id,
                "status": "failed",
                "error": str(e),
                "failed_step": self.current_step
            }
    
    def _run_preprocessing(self, input_files: Dict[str, str], 
                          output_dir: Path) -> Dict[str, str]:
        """Run preprocessing steps."""
        preprocessed_files = {}
        
        # Quality trimming
        if self.config.get("quality_trimming", True):
            trimmed_files = self.quality_control.trim_quality(
                input_files, output_dir, self.config["quality_threshold"]
            )
            preprocessed_files.update(trimmed_files)
        else:
            preprocessed_files = input_files
        
        # Adapter trimming
        if self.config.get("adapter_trimming", True):
            adapter_trimmed_files = self.quality_control.trim_adapters(
                preprocessed_files, output_dir
            )
            preprocessed_files.update(adapter_trimmed_files)
        
        return preprocessed_files


class NanoporeBasecalling:
    """
    Basecalling utilities for Oxford Nanopore raw data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "guppy": "guppy_basecaller",
            "bonito": "bonito",
            "dorado": "dorado"
        }
    
    def run_basecalling(self, fast5_dir: str, output_dir: Path) -> Dict[str, Any]:
        """
        Run basecalling on FAST5 files.
        
        Args:
            fast5_dir: Directory containing FAST5 files
            output_dir: Output directory path
            
        Returns:
            Basecalling results
        """
        basecalling_tool = self.config.get("basecalling_tool", "guppy")
        
        if basecalling_tool == "guppy":
            return self._run_guppy_basecalling(fast5_dir, output_dir)
        elif basecalling_tool == "bonito":
            return self._run_bonito_basecalling(fast5_dir, output_dir)
        elif basecalling_tool == "dorado":
            return self._run_dorado_basecalling(fast5_dir, output_dir)
        else:
            raise ValueError(f"Unsupported basecalling tool: {basecalling_tool}")
    
    def _run_guppy_basecalling(self, fast5_dir: str, output_dir: Path) -> Dict[str, Any]:
        """Run Guppy basecalling."""
        try:
            basecalling_output = output_dir / "basecalling"
            basecalling_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["guppy"],
                "-i", fast5_dir,
                "-s", str(basecalling_output),
                "--config", "dna_r9.4.1_450bps_hac.cfg",  # Default config
                "--num_callers", str(self.config.get("threads", 8)),
                "--cpu_threads_per_caller", "1"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Guppy basecalling failed: {result.stderr}")
            
            # Find the output FASTQ file
            fastq_files = list(basecalling_output.glob("*.fastq"))
            if not fastq_files:
                raise RuntimeError("No FASTQ files generated by Guppy")
            
            fastq_file = fastq_files[0]  # Take the first one
            
            return {
                "fastq_file": str(fastq_file),
                "output_dir": str(basecalling_output),
                "basecalling_tool": "guppy",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Guppy basecalling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_bonito_basecalling(self, fast5_dir: str, output_dir: Path) -> Dict[str, Any]:
        """Run Bonito basecalling."""
        try:
            basecalling_output = output_dir / "basecalling"
            basecalling_output.mkdir(exist_ok=True)
            
            fastq_file = basecalling_output / "basecalls.fastq"
            
            cmd = [
                self.tools["bonito"],
                "basecall",
                "dna_r9.4.1",  # Model name
                fast5_dir,
                "--output", str(fastq_file),
                "--threads", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Bonito basecalling failed: {result.stderr}")
            
            return {
                "fastq_file": str(fastq_file),
                "output_dir": str(basecalling_output),
                "basecalling_tool": "bonito",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Bonito basecalling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_dorado_basecalling(self, fast5_dir: str, output_dir: Path) -> Dict[str, Any]:
        """Run Dorado basecalling."""
        try:
            basecalling_output = output_dir / "basecalling"
            basecalling_output.mkdir(exist_ok=True)
            
            fastq_file = basecalling_output / "basecalls.fastq"
            
            cmd = [
                self.tools["dorado"],
                "basecaller",
                "dna_r9.4.1_e8_sup@v3.3",  # Model name
                fast5_dir,
                "--threads", str(self.config.get("threads", 8)),
                "--output-format", "fastq"
            ]
            
            with open(fastq_file, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Dorado basecalling failed: {result.stderr}")
            
            return {
                "fastq_file": str(fastq_file),
                "output_dir": str(basecalling_output),
                "basecalling_tool": "dorado",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Dorado basecalling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }


class NanoporeQualityControl:
    """
    Quality control utilities for Oxford Nanopore sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "fastqc": "fastqc",
            "cutadapt": "cutadapt",
            "fastp": "fastp",
            "porechop": "porechop"
        }
    
    def run_quality_control(self, input_files: Dict[str, str], 
                           output_dir: Path) -> Dict[str, Any]:
        """
        Run comprehensive quality control analysis for Nanopore data.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Quality control results
        """
        qc_results = {
            "fastqc_reports": [],
            "quality_metrics": {},
            "read_length_analysis": {},
            "preprocessing_recommendations": []
        }
        
        # Run FastQC
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                fastqc_result = self._run_fastqc(file_path, output_dir)
                qc_results["fastqc_reports"].append(fastqc_result)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(input_files)
        qc_results["quality_metrics"] = quality_metrics
        
        # Analyze read length distribution
        read_length_analysis = self._analyze_read_lengths(input_files)
        qc_results["read_length_analysis"] = read_length_analysis
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quality_metrics, read_length_analysis)
        qc_results["preprocessing_recommendations"] = recommendations
        
        return qc_results
    
    def _run_fastqc(self, input_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run FastQC analysis."""
        try:
            fastqc_dir = output_dir / "fastqc"
            fastqc_dir.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["fastqc"],
                "-o", str(fastqc_dir),
                "-t", str(self.config.get("threads", 8)),
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "input_file": input_file,
                "output_dir": str(fastqc_dir),
                "status": "success" if result.returncode == 0 else "failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            logger.error(f"FastQC failed for {input_file}: {str(e)}")
            return {
                "input_file": input_file,
                "status": "failed",
                "error": str(e)
            }
    
    def _calculate_quality_metrics(self, input_files: Dict[str, str]) -> Dict[str, Any]:
        """Calculate basic quality metrics from FASTQ files."""
        metrics = {}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                try:
                    file_metrics = self._analyze_fastq_file(file_path)
                    metrics[file_type] = file_metrics
                except Exception as e:
                    logger.error(f"Failed to analyze {file_path}: {str(e)}")
                    metrics[file_type] = {"error": str(e)}
        
        return metrics
    
    def _analyze_fastq_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single FASTQ file."""
        if not BIOPYTHON_AVAILABLE:
            return {"error": "Biopython not available"}
        
        try:
            total_reads = 0
            total_bases = 0
            quality_scores = []
            read_lengths = []
            
            with open(file_path, 'r') as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    total_reads += 1
                    total_bases += len(record.seq)
                    read_lengths.append(len(record.seq))
                    
                    # Calculate average quality score
                    if hasattr(record, 'letter_annotations'):
                        quals = record.letter_annotations.get('phred_quality', [])
                        if quals:
                            quality_scores.extend(quals)
            
            return {
                "total_reads": total_reads,
                "total_bases": total_bases,
                "average_read_length": np.mean(read_lengths) if read_lengths else 0,
                "median_read_length": np.median(read_lengths) if read_lengths else 0,
                "max_read_length": np.max(read_lengths) if read_lengths else 0,
                "min_read_length": np.min(read_lengths) if read_lengths else 0,
                "average_quality": np.mean(quality_scores) if quality_scores else 0,
                "min_quality": np.min(quality_scores) if quality_scores else 0,
                "max_quality": np.max(quality_scores) if quality_scores else 0,
                "gc_content": self._calculate_gc_content(file_path)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_gc_content(self, file_path: str) -> float:
        """Calculate GC content of sequences."""
        if not BIOPYTHON_AVAILABLE:
            return 0.0
        
        try:
            total_bases = 0
            gc_bases = 0
            
            with open(file_path, 'r') as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    seq = str(record.seq).upper()
                    total_bases += len(seq)
                    gc_bases += seq.count('G') + seq.count('C')
            
            return (gc_bases / total_bases * 100) if total_bases > 0 else 0.0
            
        except Exception as e:
            return 0.0
    
    def _analyze_read_lengths(self, input_files: Dict[str, str]) -> Dict[str, Any]:
        """Analyze read length distribution."""
        read_length_analysis = {}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                try:
                    analysis = self._analyze_read_length_distribution(file_path)
                    read_length_analysis[file_type] = analysis
                except Exception as e:
                    logger.error(f"Failed to analyze read lengths in {file_path}: {str(e)}")
                    read_length_analysis[file_type] = {"error": str(e)}
        
        return read_length_analysis
    
    def _analyze_read_length_distribution(self, file_path: str) -> Dict[str, Any]:
        """Analyze read length distribution in a single file."""
        if not BIOPYTHON_AVAILABLE:
            return {"error": "Biopython not available"}
        
        try:
            read_lengths = []
            
            with open(file_path, 'r') as handle:
                for record in SeqIO.parse(handle, "fastq"):
                    read_lengths.append(len(record.seq))
            
            if not read_lengths:
                return {"error": "No reads found"}
            
            return {
                "total_reads": len(read_lengths),
                "mean_length": np.mean(read_lengths),
                "median_length": np.median(read_lengths),
                "std_length": np.std(read_lengths),
                "min_length": np.min(read_lengths),
                "max_length": np.max(read_lengths),
                "n50": self._calculate_n50(read_lengths),
                "n90": self._calculate_n90(read_lengths),
                "length_distribution": {
                    "short_reads": len([x for x in read_lengths if x < 1000]),
                    "medium_reads": len([x for x in read_lengths if 1000 <= x < 10000]),
                    "long_reads": len([x for x in read_lengths if x >= 10000])
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_n50(self, read_lengths: List[int]) -> int:
        """Calculate N50 statistic."""
        sorted_lengths = sorted(read_lengths, reverse=True)
        total_length = sum(read_lengths)
        cumulative_length = 0
        
        for length in sorted_lengths:
            cumulative_length += length
            if cumulative_length >= total_length * 0.5:
                return length
        
        return 0
    
    def _calculate_n90(self, read_lengths: List[int]) -> int:
        """Calculate N90 statistic."""
        sorted_lengths = sorted(read_lengths, reverse=True)
        total_length = sum(read_lengths)
        cumulative_length = 0
        
        for length in sorted_lengths:
            cumulative_length += length
            if cumulative_length >= total_length * 0.9:
                return length
        
        return 0
    
    def _generate_recommendations(self, quality_metrics: Dict[str, Any], 
                                 read_length_analysis: Dict[str, Any]) -> List[str]:
        """Generate preprocessing recommendations."""
        recommendations = []
        
        for file_type, metrics in quality_metrics.items():
            if "error" in metrics:
                continue
            
            # Quality score recommendations (Nanopore has lower quality scores)
            if metrics.get("average_quality", 0) < 7:
                recommendations.append(f"Low average quality ({metrics['average_quality']:.1f}) in {file_type}. Consider quality filtering.")
            
            # Read length recommendations
            if metrics.get("average_read_length", 0) < 1000:
                recommendations.append(f"Short average read length ({metrics['average_read_length']:.0f}) in {file_type}. Consider filtering short reads.")
        
        # Read length analysis recommendations
        for file_type, analysis in read_length_analysis.items():
            if "error" in analysis:
                continue
            
            if analysis.get("n50", 0) < 5000:
                recommendations.append(f"Low N50 ({analysis['n50']}) in {file_type}. Consider filtering short reads for better assembly.")
            
            if analysis.get("length_distribution", {}).get("short_reads", 0) > analysis.get("total_reads", 1) * 0.5:
                recommendations.append(f"High proportion of short reads in {file_type}. Consider filtering.")
        
        return list(set(recommendations))  # Remove duplicates
    
    def trim_quality(self, input_files: Dict[str, str], output_dir: Path, 
                    quality_threshold: int) -> Dict[str, str]:
        """Trim reads based on quality scores."""
        trimmed_files = {}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_trimmed.fastq.gz"
                
                try:
                    # Use fastp for quality trimming
                    cmd = [
                        self.tools["fastp"],
                        "-i", file_path,
                        "-o", str(output_file),
                        "-q", str(quality_threshold),
                        "-l", "100",  # Minimum read length
                        "--thread", str(self.config.get("threads", 8))
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        trimmed_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Quality trimming failed for {file_path}")
                        
                except Exception as e:
                    logger.error(f"Error trimming {file_path}: {str(e)}")
        
        return trimmed_files
    
    def trim_adapters(self, input_files: Dict[str, str], output_dir: Path) -> Dict[str, str]:
        """Trim adapter sequences from reads."""
        adapter_trimmed_files = {}
        
        for file_type, file_path in input_files.items():
            if file_path and os.path.exists(file_path):
                output_file = output_dir / f"{Path(file_path).stem}_adapter_trimmed.fastq.gz"
                
                try:
                    # Use Porechop for Nanopore adapter trimming
                    cmd = [
                        self.tools["porechop"],
                        "-i", file_path,
                        "-o", str(output_file),
                        "--threads", str(self.config.get("threads", 8))
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        adapter_trimmed_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Adapter trimming failed for {file_path}")
                        
                except Exception as e:
                    logger.error(f"Error trimming adapters from {file_path}: {str(e)}")
        
        return adapter_trimmed_files


class NanoporeAlignment:
    """
    Alignment utilities for Oxford Nanopore long-read sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "minimap2": "minimap2",
            "ngmlr": "ngmlr",
            "graphmap2": "graphmap2",
            "samtools": "samtools"
        }
    
    def run_alignment(self, input_files: Dict[str, str], 
                     output_dir: Path) -> Dict[str, Any]:
        """
        Run sequence alignment.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Alignment results
        """
        alignment_tool = self.config.get("alignment_tool", "minimap2")
        
        if alignment_tool == "minimap2":
            return self._run_minimap2_alignment(input_files, output_dir)
        elif alignment_tool == "ngmlr":
            return self._run_ngmlr_alignment(input_files, output_dir)
        elif alignment_tool == "graphmap2":
            return self._run_graphmap2_alignment(input_files, output_dir)
        else:
            raise ValueError(f"Unsupported alignment tool: {alignment_tool}")
    
    def _run_minimap2_alignment(self, input_files: Dict[str, str], 
                               output_dir: Path) -> Dict[str, Any]:
        """Run Minimap2 alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            # Run Minimap2
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["minimap2"],
                "-ax", "map-ont",  # Nanopore preset
                "-t", str(self.config.get("threads", 8)),
                reference_genome,
                input_files.get("fastq", "")
            ]
            
            with open(sam_file, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Minimap2 alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "minimap2",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Minimap2 alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_ngmlr_alignment(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """Run NGMLR alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["ngmlr"],
                "-r", reference_genome,
                "-q", input_files.get("fastq", ""),
                "-t", str(self.config.get("threads", 8)),
                "-o", str(sam_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"NGMLR alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "ngmlr",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"NGMLR alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_graphmap2_alignment(self, input_files: Dict[str, str], 
                                output_dir: Path) -> Dict[str, Any]:
        """Run GraphMap2 alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["graphmap2"],
                "align",
                "-r", reference_genome,
                "-d", input_files.get("fastq", ""),
                "-o", str(sam_file),
                "-t", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"GraphMap2 alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "graphmap2",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"GraphMap2 alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _sam_to_bam(self, sam_file: Path, bam_file: Path):
        """Convert SAM to BAM and sort."""
        # Convert to BAM
        bam_temp = bam_file.with_suffix('.temp.bam')
        cmd = [self.tools["samtools"], "view", "-bS", str(sam_file), "-o", str(bam_temp)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"SAM to BAM conversion failed: {result.stderr}")
        
        # Sort BAM
        cmd = [self.tools["samtools"], "sort", str(bam_temp), "-o", str(bam_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"BAM sorting failed: {result.stderr}")
        
        # Index BAM
        cmd = [self.tools["samtools"], "index", str(bam_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"BAM indexing failed: {result.stderr}")
        
        # Clean up temp file
        if bam_temp.exists():
            bam_temp.unlink()
    
    def _calculate_alignment_stats(self, bam_file: Path) -> Dict[str, Any]:
        """Calculate alignment statistics."""
        try:
            cmd = [self.tools["samtools"], "flagstat", str(bam_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": "Failed to calculate alignment statistics"}
            
            stats = {}
            for line in result.stdout.strip().split('\n'):
                if '+' in line:
                    parts = line.split('+')
                    if len(parts) == 2:
                        key = parts[1].strip()
                        value = int(parts[0].strip())
                        stats[key] = value
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}


class NanoporeVariantCalling:
    """
    Variant calling utilities for Oxford Nanopore long-read sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "clair3": "clair3",
            "deepvariant": "run_deepvariant",
            "medaka": "medaka",
            "samtools": "samtools"
        }
    
    def run_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """
        Run variant calling analysis.
        
        Args:
            bam_file: Path to BAM file
            output_dir: Output directory path
            
        Returns:
            Variant calling results
        """
        variant_caller = self.config.get("variant_caller", "clair3")
        
        if variant_caller == "clair3":
            return self._run_clair3_variant_calling(bam_file, output_dir)
        elif variant_caller == "deepvariant":
            return self._run_deepvariant_variant_calling(bam_file, output_dir)
        elif variant_caller == "medaka":
            return self._run_medaka_variant_calling(bam_file, output_dir)
        else:
            raise ValueError(f"Unsupported variant caller: {variant_caller}")
    
    def _run_clair3_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run Clair3 variant calling (optimized for Nanopore)."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["clair3"],
                "--bam_fn", bam_file,
                "--ref_fn", reference_genome,
                "--threads", str(self.config.get("threads", 8)),
                "--platform", "ont",
                "--output", str(output_dir / "clair3_output")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Clair3 variant calling failed: {result.stderr}")
            
            # Find the output VCF file
            vcf_files = list((output_dir / "clair3_output").glob("*.vcf"))
            if vcf_files:
                vcf_file = vcf_files[0]
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "clair3",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Clair3 variant calling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_deepvariant_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run DeepVariant variant calling."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["deepvariant"],
                "--model_type=ONT",
                f"--ref={reference_genome}",
                f"--reads={bam_file}",
                f"--output_vcf={vcf_file}",
                f"--num_shards={self.config.get('threads', 8)}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"DeepVariant variant calling failed: {result.stderr}")
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "deepvariant",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"DeepVariant variant calling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_medaka_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run Medaka variant calling (Nanopore specific)."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["medaka"],
                "variant",
                "--model", "r941_min_high_g360",  # Default model
                "--threads", str(self.config.get("threads", 8)),
                reference_genome,
                bam_file,
                str(vcf_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Medaka variant calling failed: {result.stderr}")
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "medaka",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Medaka variant calling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _calculate_variant_stats(self, vcf_file: Path) -> Dict[str, Any]:
        """Calculate variant statistics from VCF file."""
        try:
            stats = {
                "total_variants": 0,
                "snps": 0,
                "indels": 0,
                "passing_variants": 0,
                "quality_distribution": {}
            }
            
            with open(vcf_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) >= 8:
                        stats["total_variants"] += 1
                        
                        # Check if variant passes filters
                        if parts[6] == 'PASS':
                            stats["passing_variants"] += 1
                        
                        # Determine variant type
                        ref = parts[3]
                        alt = parts[4]
                        
                        if len(ref) == 1 and len(alt) == 1:
                            stats["snps"] += 1
                        else:
                            stats["indels"] += 1
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}


class NanoporeAssembly:
    """
    Assembly utilities for Oxford Nanopore long-read sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "flye": "flye",
            "canu": "canu",
            "wtdbg2": "wtdbg2"
        }
    
    def run_assembly(self, input_files: Dict[str, str], 
                    output_dir: Path) -> Dict[str, Any]:
        """
        Run genome assembly.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Assembly results
        """
        assembly_tool = self.config.get("assembly_tool", "flye")
        
        if assembly_tool == "flye":
            return self._run_flye_assembly(input_files, output_dir)
        elif assembly_tool == "canu":
            return self._run_canu_assembly(input_files, output_dir)
        elif assembly_tool == "wtdbg2":
            return self._run_wtdbg2_assembly(input_files, output_dir)
        else:
            raise ValueError(f"Unsupported assembly tool: {assembly_tool}")
    
    def _run_flye_assembly(self, input_files: Dict[str, str], 
                          output_dir: Path) -> Dict[str, Any]:
        """Run Flye assembly."""
        try:
            assembly_output = output_dir / "flye_assembly"
            assembly_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["flye"],
                "--nano-raw", input_files.get("fastq", ""),
                "--out-dir", str(assembly_output),
                "--threads", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Flye assembly failed: {result.stderr}")
            
            # Parse assembly results
            results = self._parse_flye_results(assembly_output)
            
            return {
                "output_dir": str(assembly_output),
                "assembly_tool": "flye",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Flye assembly failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_canu_assembly(self, input_files: Dict[str, str], 
                          output_dir: Path) -> Dict[str, Any]:
        """Run Canu assembly."""
        try:
            assembly_output = output_dir / "canu_assembly"
            assembly_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["canu"],
                "-p", "assembly",
                "-d", str(assembly_output),
                "-nanopore-raw", input_files.get("fastq", ""),
                "genomeSize=100m",  # Default genome size
                "maxThreads=" + str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Canu assembly failed: {result.stderr}")
            
            # Parse assembly results
            results = self._parse_canu_results(assembly_output)
            
            return {
                "output_dir": str(assembly_output),
                "assembly_tool": "canu",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Canu assembly failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_wtdbg2_assembly(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """Run wtdbg2 assembly."""
        try:
            assembly_output = output_dir / "wtdbg2_assembly"
            assembly_output.mkdir(exist_ok=True)
            
            # Step 1: Build graph
            cmd = [
                self.tools["wtdbg2"],
                "-x", "ont",  # Nanopore preset
                "-g", "100m",  # Genome size
                "-i", input_files.get("fastq", ""),
                "-t", str(self.config.get("threads", 8)),
                "-fo", str(assembly_output / "assembly")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"wtdbg2 graph building failed: {result.stderr}")
            
            # Step 2: Generate consensus
            cmd = [
                "wtpoa-cns",
                "-t", str(self.config.get("threads", 8)),
                "-i", str(assembly_output / "assembly.ctg.lay.gz"),
                "-fo", str(assembly_output / "assembly.ctg.fa")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"wtdbg2 consensus generation failed: {result.stderr}")
            
            # Parse assembly results
            results = self._parse_wtdbg2_results(assembly_output)
            
            return {
                "output_dir": str(assembly_output),
                "assembly_tool": "wtdbg2",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"wtdbg2 assembly failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_flye_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse Flye assembly results."""
        try:
            assembly_file = output_dir / "assembly.fasta"
            if not assembly_file.exists():
                return {"error": "Assembly file not found"}
            
            # Basic assembly statistics
            stats = self._calculate_assembly_stats(assembly_file)
            
            return {
                "assembly_file": str(assembly_file),
                "statistics": stats
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_canu_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse Canu assembly results."""
        try:
            assembly_file = output_dir / "assembly.contigs.fasta"
            if not assembly_file.exists():
                return {"error": "Assembly file not found"}
            
            # Basic assembly statistics
            stats = self._calculate_assembly_stats(assembly_file)
            
            return {
                "assembly_file": str(assembly_file),
                "statistics": stats
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_wtdbg2_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse wtdbg2 assembly results."""
        try:
            assembly_file = output_dir / "assembly.ctg.fa"
            if not assembly_file.exists():
                return {"error": "Assembly file not found"}
            
            # Basic assembly statistics
            stats = self._calculate_assembly_stats(assembly_file)
            
            return {
                "assembly_file": str(assembly_file),
                "statistics": stats
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_assembly_stats(self, assembly_file: Path) -> Dict[str, Any]:
        """Calculate basic assembly statistics."""
        if not BIOPYTHON_AVAILABLE:
            return {"error": "Biopython not available"}
        
        try:
            contig_lengths = []
            total_length = 0
            
            with open(assembly_file, 'r') as handle:
                for record in SeqIO.parse(handle, "fasta"):
                    length = len(record.seq)
                    contig_lengths.append(length)
                    total_length += length
            
            if not contig_lengths:
                return {"error": "No contigs found"}
            
            contig_lengths.sort(reverse=True)
            
            # Calculate N50, N90
            n50 = self._calculate_n50(contig_lengths)
            n90 = self._calculate_n90(contig_lengths)
            
            return {
                "total_contigs": len(contig_lengths),
                "total_length": total_length,
                "largest_contig": contig_lengths[0],
                "smallest_contig": contig_lengths[-1],
                "average_contig_length": np.mean(contig_lengths),
                "n50": n50,
                "n90": n90
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_n50(self, contig_lengths: List[int]) -> int:
        """Calculate N50 statistic."""
        total_length = sum(contig_lengths)
        cumulative_length = 0
        
        for length in contig_lengths:
            cumulative_length += length
            if cumulative_length >= total_length * 0.5:
                return length
        
        return 0
    
    def _calculate_n90(self, contig_lengths: List[int]) -> int:
        """Calculate N90 statistic."""
        total_length = sum(contig_lengths)
        cumulative_length = 0
        
        for length in contig_lengths:
            cumulative_length += length
            if cumulative_length >= total_length * 0.9:
                return length
        
        return 0

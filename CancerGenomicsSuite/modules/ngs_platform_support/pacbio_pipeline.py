"""
PacBio Sequencing Pipeline

This module provides comprehensive support for PacBio long-read sequencing platforms,
including quality control, alignment, variant calling, assembly, and isoform analysis.
Supports various PacBio platforms: RS II, Sequel, Sequel II, and Revio.
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


class PacBioPipeline:
    """
    Main PacBio sequencing pipeline orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize PacBio pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.platform_info = self._get_platform_info()
        self.quality_control = PacBioQualityControl(self.config)
        self.alignment = PacBioAlignment(self.config)
        self.variant_calling = PacBioVariantCalling(self.config)
        self.assembly = PacBioAssembly(self.config)
        self.isoform_analysis = PacBioIsoformAnalysis(self.config)
        
        # Pipeline state
        self.current_step = None
        self.pipeline_status = "initialized"
        self.results = {}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default pipeline configuration."""
        return {
            "platform": "pacbio",
            "read_type": "long_read",
            "read_length": 10000,  # Average read length
            "quality_threshold": 0.8,  # CCS quality threshold
            "ccs_generation": True,  # Generate Circular Consensus Sequences
            "adapter_trimming": True,
            "quality_trimming": True,
            "duplicate_removal": True,
            "alignment_tool": "minimap2",  # minimap2, ngmlr, pbmm2
            "variant_caller": "deepvariant",  # deepvariant, gatk, freebayes
            "assembly_tool": "flye",  # flye, canu, wtdbg2
            "isoform_tool": "isoseq",  # isoseq, stringtie
            "reference_genome": None,
            "annotation_file": None,
            "output_dir": "./pacbio_output",
            "threads": 8,
            "memory": "32G",
            "temp_dir": "./temp"
        }
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get PacBio platform-specific information."""
        return {
            "supported_platforms": ["rs_ii", "sequel", "sequel_ii", "revio"],
            "read_lengths": {
                "rs_ii": [1000, 5000, 10000, 20000],
                "sequel": [2000, 8000, 15000, 30000],
                "sequel_ii": [5000, 15000, 25000, 50000],
                "revio": [10000, 25000, 40000, 75000]
            },
            "throughput": {
                "rs_ii": "low",
                "sequel": "medium",
                "sequel_ii": "high",
                "revio": "very_high"
            },
            "error_rates": {
                "rs_ii": 0.15,
                "sequel": 0.13,
                "sequel_ii": 0.10,
                "revio": 0.08
            },
            "ccs_accuracy": {
                "rs_ii": 0.99,
                "sequel": 0.995,
                "sequel_ii": 0.999,
                "revio": 0.9995
            }
        }
    
    def run_full_pipeline(self, input_files: Dict[str, str], 
                         sample_id: str) -> Dict[str, Any]:
        """
        Run the complete PacBio sequencing pipeline.
        
        Args:
            input_files: Dictionary with 'subreads' or 'ccs' file paths
            sample_id: Sample identifier
            
        Returns:
            Pipeline results dictionary
        """
        try:
            logger.info(f"Starting PacBio pipeline for sample {sample_id}")
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
            
            # Step 1: Quality Control
            self.current_step = "quality_control"
            logger.info("Running quality control...")
            qc_results = self.quality_control.run_quality_control(input_files, output_dir)
            results["steps"]["quality_control"] = qc_results
            
            # Step 2: CCS Generation (if subreads provided)
            if "subreads" in input_files and self.config.get("ccs_generation", True):
                self.current_step = "ccs_generation"
                logger.info("Generating Circular Consensus Sequences...")
                ccs_results = self._run_ccs_generation(input_files["subreads"], output_dir)
                results["steps"]["ccs_generation"] = ccs_results
                input_files["ccs"] = ccs_results["ccs_file"]
            
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
            
            # Step 7: Isoform Analysis (if RNA-seq)
            if self.config.get("analysis_type") == "rna_seq":
                self.current_step = "isoform_analysis"
                logger.info("Running isoform analysis...")
                isoform_results = self.isoform_analysis.run_isoform_analysis(
                    preprocessed_files, output_dir
                )
                results["steps"]["isoform_analysis"] = isoform_results
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["status"] = "completed"
            self.pipeline_status = "completed"
            
            logger.info(f"PacBio pipeline completed successfully for sample {sample_id}")
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
    
    def _run_ccs_generation(self, subreads_file: str, output_dir: Path) -> Dict[str, Any]:
        """Generate Circular Consensus Sequences from subreads."""
        try:
            ccs_file = output_dir / "ccs.bam"
            
            cmd = [
                "ccs",
                "--num-threads", str(self.config.get("threads", 8)),
                "--min-passes", "3",
                "--min-length", "50",
                "--max-length", "50000",
                subreads_file,
                str(ccs_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"CCS generation failed: {result.stderr}")
            
            # Convert BAM to FASTQ
            ccs_fastq = output_dir / "ccs.fastq"
            cmd = [
                "bam2fastq",
                "-o", str(ccs_fastq.with_suffix('')),
                str(ccs_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"BAM to FASTQ conversion failed: {result.stderr}")
                ccs_fastq = None
            
            return {
                "ccs_file": str(ccs_file),
                "ccs_fastq": str(ccs_fastq) if ccs_fastq else None,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"CCS generation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
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


class PacBioQualityControl:
    """
    Quality control utilities for PacBio sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "fastqc": "fastqc",
            "cutadapt": "cutadapt",
            "fastp": "fastp",
            "pbccs": "ccs"
        }
    
    def run_quality_control(self, input_files: Dict[str, str], 
                           output_dir: Path) -> Dict[str, Any]:
        """
        Run comprehensive quality control analysis for PacBio data.
        
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
            
            # Quality score recommendations
            if metrics.get("average_quality", 0) < 0.8:
                recommendations.append(f"Low average quality ({metrics['average_quality']:.2f}) in {file_type}. Consider CCS generation or quality filtering.")
            
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
                    quality_threshold: float) -> Dict[str, str]:
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
                        "-q", str(int(quality_threshold * 100)),  # Convert to Phred score
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
                    # Use cutadapt for adapter trimming
                    cmd = [
                        self.tools["cutadapt"],
                        "-a", "ATCTCTCTCAACAACAACAACGGAGGAGGAGGAAAAGAGAGAGAT",  # PacBio adapter
                        "-o", str(output_file),
                        "--threads", str(self.config.get("threads", 8)),
                        file_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        adapter_trimmed_files[file_type] = str(output_file)
                    else:
                        logger.error(f"Adapter trimming failed for {file_path}")
                        
                except Exception as e:
                    logger.error(f"Error trimming adapters from {file_path}: {str(e)}")
        
        return adapter_trimmed_files


class PacBioAlignment:
    """
    Alignment utilities for PacBio long-read sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "minimap2": "minimap2",
            "ngmlr": "ngmlr",
            "pbmm2": "pbmm2",
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
        elif alignment_tool == "pbmm2":
            return self._run_pbmm2_alignment(input_files, output_dir)
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
                "-ax", "map-pb",  # PacBio preset
                "-t", str(self.config.get("threads", 8)),
                reference_genome,
                input_files.get("ccs", input_files.get("fastq", ""))
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
                "-q", input_files.get("ccs", input_files.get("fastq", "")),
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
    
    def _run_pbmm2_alignment(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """Run PBMM2 alignment (PacBio specific)."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["pbmm2"],
                "align",
                "--preset", "CCS",
                "--sort",
                "--num-threads", str(self.config.get("threads", 8)),
                reference_genome,
                input_files.get("ccs", input_files.get("fastq", "")),
                str(bam_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"PBMM2 alignment failed: {result.stderr}")
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "bam_file": str(bam_file),
                "alignment_tool": "pbmm2",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"PBMM2 alignment failed: {str(e)}")
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


class PacBioVariantCalling:
    """
    Variant calling utilities for PacBio long-read sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "deepvariant": "run_deepvariant",
            "gatk": "gatk",
            "freebayes": "freebayes",
            "bcftools": "bcftools",
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
        variant_caller = self.config.get("variant_caller", "deepvariant")
        
        if variant_caller == "deepvariant":
            return self._run_deepvariant_variant_calling(bam_file, output_dir)
        elif variant_caller == "gatk":
            return self._run_gatk_variant_calling(bam_file, output_dir)
        elif variant_caller == "freebayes":
            return self._run_freebayes_variant_calling(bam_file, output_dir)
        elif variant_caller == "bcftools":
            return self._run_bcftools_variant_calling(bam_file, output_dir)
        else:
            raise ValueError(f"Unsupported variant caller: {variant_caller}")
    
    def _run_deepvariant_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run DeepVariant variant calling (optimized for long reads)."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["deepvariant"],
                "--model_type=PACBIO",
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
    
    def _run_gatk_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run GATK variant calling."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            # GATK HaplotypeCaller
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["gatk"], "HaplotypeCaller",
                "-R", reference_genome,
                "-I", bam_file,
                "-O", str(vcf_file),
                "--native-pair-hmm-threads", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"GATK variant calling failed: {result.stderr}")
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "gatk",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"GATK variant calling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_freebayes_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run FreeBayes variant calling."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            cmd = [
                self.tools["freebayes"],
                "-f", reference_genome,
                "-v", str(vcf_file),
                "--threads", str(self.config.get("threads", 8)),
                bam_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"FreeBayes variant calling failed: {result.stderr}")
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "freebayes",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"FreeBayes variant calling failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_bcftools_variant_calling(self, bam_file: str, output_dir: Path) -> Dict[str, Any]:
        """Run BCFtools variant calling."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            vcf_file = output_dir / "variants.vcf"
            
            # BCFtools mpileup
            cmd = [
                self.tools["bcftools"], "mpileup",
                "-f", reference_genome,
                "-o", str(vcf_file.with_suffix('.bcf')),
                bam_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"BCFtools mpileup failed: {result.stderr}")
            
            # BCFtools call
            cmd = [
                self.tools["bcftools"], "call",
                "-mv",
                "-o", str(vcf_file),
                str(vcf_file.with_suffix('.bcf'))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"BCFtools call failed: {result.stderr}")
            
            # Calculate variant statistics
            stats = self._calculate_variant_stats(vcf_file)
            
            return {
                "vcf_file": str(vcf_file),
                "variant_caller": "bcftools",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"BCFtools variant calling failed: {str(e)}")
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


class PacBioAssembly:
    """
    Assembly utilities for PacBio long-read sequencing data.
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
                "--pacbio-hifi", input_files.get("ccs", input_files.get("fastq", "")),
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
                "-pacbio-hifi", input_files.get("ccs", input_files.get("fastq", "")),
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
                "-x", "sq",  # PacBio HiFi preset
                "-g", "100m",  # Genome size
                "-i", input_files.get("ccs", input_files.get("fastq", "")),
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


class PacBioIsoformAnalysis:
    """
    Isoform analysis utilities for PacBio RNA-seq data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "isoseq": "isoseq3",
            "stringtie": "stringtie"
        }
    
    def run_isoform_analysis(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """
        Run isoform analysis.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Isoform analysis results
        """
        isoform_tool = self.config.get("isoform_tool", "isoseq")
        
        if isoform_tool == "isoseq":
            return self._run_isoseq_analysis(input_files, output_dir)
        elif isoform_tool == "stringtie":
            return self._run_stringtie_analysis(input_files, output_dir)
        else:
            raise ValueError(f"Unsupported isoform tool: {isoform_tool}")
    
    def _run_isoseq_analysis(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """Run IsoSeq analysis."""
        try:
            isoseq_output = output_dir / "isoseq_output"
            isoseq_output.mkdir(exist_ok=True)
            
            # Step 1: CCS generation (if subreads provided)
            if "subreads" in input_files:
                ccs_file = isoseq_output / "ccs.bam"
                cmd = [
                    "ccs",
                    "--num-threads", str(self.config.get("threads", 8)),
                    input_files["subreads"],
                    str(ccs_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"CCS generation failed: {result.stderr}")
            else:
                ccs_file = input_files.get("ccs", "")
            
            # Step 2: Lima (primer removal)
            lima_output = isoseq_output / "lima_output"
            lima_output.mkdir(exist_ok=True)
            
            cmd = [
                "lima",
                "--num-threads", str(self.config.get("threads", 8)),
                str(ccs_file),
                "primers.fasta",  # Primer sequences file
                str(lima_output / "demux")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Lima primer removal failed: {result.stderr}")
            
            # Step 3: Refine
            refine_output = isoseq_output / "refine_output"
            refine_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["isoseq"],
                "refine",
                "--num-threads", str(self.config.get("threads", 8)),
                str(lima_output / "demux.bam"),
                "primers.fasta",
                str(refine_output / "flnc.bam")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"IsoSeq refine failed: {result.stderr}")
            
            # Step 4: Cluster
            cluster_output = isoseq_output / "cluster_output"
            cluster_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["isoseq"],
                "cluster",
                str(refine_output / "flnc.bam"),
                str(cluster_output / "polished.bam"),
                "--num-threads", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"IsoSeq cluster failed: {result.stderr}")
            
            # Parse results
            results = self._parse_isoseq_results(isoseq_output)
            
            return {
                "output_dir": str(isoseq_output),
                "isoform_tool": "isoseq",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"IsoSeq analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_stringtie_analysis(self, input_files: Dict[str, str], 
                               output_dir: Path) -> Dict[str, Any]:
        """Run StringTie analysis."""
        try:
            stringtie_output = output_dir / "stringtie_output"
            stringtie_output.mkdir(exist_ok=True)
            
            # StringTie assembly
            gtf_file = stringtie_output / "transcripts.gtf"
            
            cmd = [
                self.tools["stringtie"],
                input_files.get("ccs", input_files.get("fastq", "")),
                "-o", str(gtf_file),
                "-p", str(self.config.get("threads", 8))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"StringTie analysis failed: {result.stderr}")
            
            # Parse results
            results = self._parse_stringtie_results(stringtie_output)
            
            return {
                "output_dir": str(stringtie_output),
                "isoform_tool": "stringtie",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"StringTie analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_isoseq_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse IsoSeq results."""
        try:
            results = {
                "isoforms": 0,
                "genes": 0,
                "transcripts": 0
            }
            
            # Count isoforms from cluster output
            cluster_file = output_dir / "cluster_output" / "polished.bam"
            if cluster_file.exists():
                # Use samtools to count reads
                cmd = ["samtools", "view", "-c", str(cluster_file)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    results["isoforms"] = int(result.stdout.strip())
            
            return results
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_stringtie_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse StringTie results."""
        try:
            gtf_file = output_dir / "transcripts.gtf"
            if not gtf_file.exists():
                return {"error": "GTF file not found"}
            
            results = {
                "transcripts": 0,
                "genes": 0,
                "isoforms": 0
            }
            
            with open(gtf_file, 'r') as f:
                for line in f:
                    if not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            feature_type = parts[2]
                            if feature_type == "transcript":
                                results["transcripts"] += 1
                            elif feature_type == "gene":
                                results["genes"] += 1
            
            results["isoforms"] = results["transcripts"]
            
            return results
            
        except Exception as e:
            return {"error": str(e)}

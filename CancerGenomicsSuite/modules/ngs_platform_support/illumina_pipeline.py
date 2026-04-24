"""
Illumina Sequencing Pipeline

This module provides comprehensive support for Illumina sequencing platforms,
including quality control, alignment, variant calling, and expression analysis.
Supports various Illumina platforms: HiSeq, MiSeq, NovaSeq, NextSeq, and iSeq.
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


class IlluminaPipeline:
    """
    Main Illumina sequencing pipeline orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Illumina pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.platform_info = self._get_platform_info()
        self.quality_control = IlluminaQualityControl(self.config)
        self.alignment = IlluminaAlignment(self.config)
        self.variant_calling = IlluminaVariantCalling(self.config)
        self.expression_analysis = IlluminaExpressionAnalysis(self.config)
        
        # Pipeline state
        self.current_step = None
        self.pipeline_status = "initialized"
        self.results = {}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default pipeline configuration."""
        return {
            "platform": "illumina",
            "read_type": "paired_end",  # single_end, paired_end
            "read_length": 150,
            "quality_threshold": 20,
            "adapter_trimming": True,
            "quality_trimming": True,
            "duplicate_removal": True,
            "alignment_tool": "bwa",  # bwa, bowtie2, hisat2
            "variant_caller": "gatk",  # gatk, freebayes, bcftools
            "expression_tool": "salmon",  # salmon, kallisto, star
            "reference_genome": None,
            "annotation_file": None,
            "output_dir": "./illumina_output",
            "threads": 4,
            "memory": "8G",
            "temp_dir": "./temp"
        }
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get Illumina platform-specific information."""
        return {
            "supported_platforms": ["hiseq", "miseq", "novaseq", "nextseq", "iseq"],
            "read_lengths": {
                "hiseq": [50, 75, 100, 125, 150],
                "miseq": [50, 75, 150, 250, 300],
                "novaseq": [50, 75, 100, 150, 300],
                "nextseq": [75, 150],
                "iseq": [75, 150]
            },
            "throughput": {
                "hiseq": "high",
                "miseq": "medium", 
                "novaseq": "very_high",
                "nextseq": "high",
                "iseq": "low"
            },
            "error_rates": {
                "hiseq": 0.1,
                "miseq": 0.1,
                "novaseq": 0.1,
                "nextseq": 0.1,
                "iseq": 0.1
            }
        }
    
    def run_full_pipeline(self, input_files: Dict[str, str], 
                         sample_id: str) -> Dict[str, Any]:
        """
        Run the complete Illumina sequencing pipeline.
        
        Args:
            input_files: Dictionary with 'r1', 'r2' (optional) file paths
            sample_id: Sample identifier
            
        Returns:
            Pipeline results dictionary
        """
        try:
            logger.info(f"Starting Illumina pipeline for sample {sample_id}")
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
            
            # Step 2: Preprocessing
            self.current_step = "preprocessing"
            logger.info("Running preprocessing...")
            preprocessed_files = self._run_preprocessing(input_files, output_dir)
            results["steps"]["preprocessing"] = preprocessed_files
            
            # Step 3: Alignment
            self.current_step = "alignment"
            logger.info("Running alignment...")
            alignment_results = self.alignment.run_alignment(preprocessed_files, output_dir)
            results["steps"]["alignment"] = alignment_results
            
            # Step 4: Variant Calling
            self.current_step = "variant_calling"
            logger.info("Running variant calling...")
            variant_results = self.variant_calling.run_variant_calling(
                alignment_results["bam_file"], output_dir
            )
            results["steps"]["variant_calling"] = variant_results
            
            # Step 5: Expression Analysis (if RNA-seq)
            if self.config.get("analysis_type") == "rna_seq":
                self.current_step = "expression_analysis"
                logger.info("Running expression analysis...")
                expression_results = self.expression_analysis.run_expression_analysis(
                    preprocessed_files, output_dir
                )
                results["steps"]["expression_analysis"] = expression_results
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["status"] = "completed"
            self.pipeline_status = "completed"
            
            logger.info(f"Illumina pipeline completed successfully for sample {sample_id}")
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


class IlluminaQualityControl:
    """
    Quality control utilities for Illumina sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "fastqc": "fastqc",
            "trimmomatic": "trimmomatic",
            "cutadapt": "cutadapt",
            "fastp": "fastp"
        }
    
    def run_quality_control(self, input_files: Dict[str, str], 
                           output_dir: Path) -> Dict[str, Any]:
        """
        Run comprehensive quality control analysis.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Quality control results
        """
        qc_results = {
            "fastqc_reports": [],
            "quality_metrics": {},
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
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quality_metrics)
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
                "-t", str(self.config.get("threads", 4)),
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
    
    def _generate_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate preprocessing recommendations based on quality metrics."""
        recommendations = []
        
        for file_type, metrics in quality_metrics.items():
            if "error" in metrics:
                continue
            
            # Quality score recommendations
            if metrics.get("average_quality", 0) < 20:
                recommendations.append(f"Low average quality ({metrics['average_quality']:.1f}) in {file_type}. Consider quality trimming.")
            
            if metrics.get("min_quality", 0) < 10:
                recommendations.append(f"Very low minimum quality ({metrics['min_quality']}) in {file_type}. Aggressive quality trimming recommended.")
            
            # Read length recommendations
            if metrics.get("average_read_length", 0) < 50:
                recommendations.append(f"Short average read length ({metrics['average_read_length']:.1f}) in {file_type}. Consider adapter trimming.")
            
            # GC content recommendations
            gc_content = metrics.get("gc_content", 0)
            if gc_content < 30 or gc_content > 70:
                recommendations.append(f"Unusual GC content ({gc_content:.1f}%) in {file_type}. Check for contamination.")
        
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
                        "-l", "20",  # Minimum read length
                        "--thread", str(self.config.get("threads", 4))
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
                        "-a", "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA",  # Illumina adapter
                        "-A", "AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT",  # Illumina adapter
                        "-o", str(output_file),
                        "--threads", str(self.config.get("threads", 4)),
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


class IlluminaAlignment:
    """
    Alignment utilities for Illumina sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "bwa": "bwa",
            "bowtie2": "bowtie2",
            "hisat2": "hisat2",
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
        alignment_tool = self.config.get("alignment_tool", "bwa")
        
        if alignment_tool == "bwa":
            return self._run_bwa_alignment(input_files, output_dir)
        elif alignment_tool == "bowtie2":
            return self._run_bowtie2_alignment(input_files, output_dir)
        elif alignment_tool == "hisat2":
            return self._run_hisat2_alignment(input_files, output_dir)
        else:
            raise ValueError(f"Unsupported alignment tool: {alignment_tool}")
    
    def _run_bwa_alignment(self, input_files: Dict[str, str], 
                          output_dir: Path) -> Dict[str, Any]:
        """Run BWA alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            # BWA index if needed
            self._ensure_bwa_index(reference_genome)
            
            # Run BWA mem
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["bwa"], "mem",
                "-t", str(self.config.get("threads", 4)),
                reference_genome
            ]
            
            # Add input files
            if "r1" in input_files:
                cmd.append(input_files["r1"])
            if "r2" in input_files:
                cmd.append(input_files["r2"])
            
            with open(sam_file, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"BWA alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "bwa",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"BWA alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_bowtie2_alignment(self, input_files: Dict[str, str], 
                              output_dir: Path) -> Dict[str, Any]:
        """Run Bowtie2 alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            # Bowtie2 index if needed
            self._ensure_bowtie2_index(reference_genome)
            
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["bowtie2"],
                "-x", reference_genome,
                "-p", str(self.config.get("threads", 4))
            ]
            
            # Add input files
            if "r1" in input_files and "r2" in input_files:
                cmd.extend(["-1", input_files["r1"], "-2", input_files["r2"]])
            elif "r1" in input_files:
                cmd.extend(["-U", input_files["r1"]])
            
            cmd.extend(["-S", str(sam_file)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Bowtie2 alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "bowtie2",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Bowtie2 alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_hisat2_alignment(self, input_files: Dict[str, str], 
                             output_dir: Path) -> Dict[str, Any]:
        """Run HISAT2 alignment."""
        try:
            reference_genome = self.config.get("reference_genome")
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            
            # HISAT2 index if needed
            self._ensure_hisat2_index(reference_genome)
            
            sam_file = output_dir / "alignment.sam"
            bam_file = output_dir / "alignment.bam"
            
            cmd = [
                self.tools["hisat2"],
                "-x", reference_genome,
                "-p", str(self.config.get("threads", 4))
            ]
            
            # Add input files
            if "r1" in input_files and "r2" in input_files:
                cmd.extend(["-1", input_files["r1"], "-2", input_files["r2"]])
            elif "r1" in input_files:
                cmd.extend(["-U", input_files["r1"]])
            
            cmd.extend(["-S", str(sam_file)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"HISAT2 alignment failed: {result.stderr}")
            
            # Convert SAM to BAM and sort
            self._sam_to_bam(sam_file, bam_file)
            
            # Calculate alignment statistics
            stats = self._calculate_alignment_stats(bam_file)
            
            return {
                "sam_file": str(sam_file),
                "bam_file": str(bam_file),
                "alignment_tool": "hisat2",
                "statistics": stats,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"HISAT2 alignment failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _ensure_bwa_index(self, reference_genome: str):
        """Ensure BWA index exists."""
        index_files = [f"{reference_genome}.amb", f"{reference_genome}.ann", 
                      f"{reference_genome}.bwt", f"{reference_genome}.pac", f"{reference_genome}.sa"]
        
        if not all(os.path.exists(f) for f in index_files):
            logger.info(f"Building BWA index for {reference_genome}")
            cmd = [self.tools["bwa"], "index", reference_genome]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"BWA indexing failed: {result.stderr}")
    
    def _ensure_bowtie2_index(self, reference_genome: str):
        """Ensure Bowtie2 index exists."""
        index_files = [f"{reference_genome}.1.bt2", f"{reference_genome}.2.bt2",
                      f"{reference_genome}.3.bt2", f"{reference_genome}.4.bt2",
                      f"{reference_genome}.rev.1.bt2", f"{reference_genome}.rev.2.bt2"]
        
        if not all(os.path.exists(f) for f in index_files):
            logger.info(f"Building Bowtie2 index for {reference_genome}")
            cmd = [self.tools["bowtie2-build"], reference_genome, reference_genome]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Bowtie2 indexing failed: {result.stderr}")
    
    def _ensure_hisat2_index(self, reference_genome: str):
        """Ensure HISAT2 index exists."""
        index_files = [f"{reference_genome}.1.ht2", f"{reference_genome}.2.ht2",
                      f"{reference_genome}.3.ht2", f"{reference_genome}.4.ht2",
                      f"{reference_genome}.5.ht2", f"{reference_genome}.6.ht2",
                      f"{reference_genome}.7.ht2", f"{reference_genome}.8.ht2"]
        
        if not all(os.path.exists(f) for f in index_files):
            logger.info(f"Building HISAT2 index for {reference_genome}")
            cmd = [self.tools["hisat2-build"], reference_genome, reference_genome]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"HISAT2 indexing failed: {result.stderr}")
    
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


class IlluminaVariantCalling:
    """
    Variant calling utilities for Illumina sequencing data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
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
        variant_caller = self.config.get("variant_caller", "gatk")
        
        if variant_caller == "gatk":
            return self._run_gatk_variant_calling(bam_file, output_dir)
        elif variant_caller == "freebayes":
            return self._run_freebayes_variant_calling(bam_file, output_dir)
        elif variant_caller == "bcftools":
            return self._run_bcftools_variant_calling(bam_file, output_dir)
        else:
            raise ValueError(f"Unsupported variant caller: {variant_caller}")
    
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
                "--native-pair-hmm-threads", str(self.config.get("threads", 4))
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
                "--threads", str(self.config.get("threads", 4)),
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


class IlluminaExpressionAnalysis:
    """
    Expression analysis utilities for Illumina RNA-seq data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {
            "salmon": "salmon",
            "kallisto": "kallisto",
            "star": "STAR"
        }
    
    def run_expression_analysis(self, input_files: Dict[str, str], 
                               output_dir: Path) -> Dict[str, Any]:
        """
        Run expression analysis.
        
        Args:
            input_files: Dictionary with input file paths
            output_dir: Output directory path
            
        Returns:
            Expression analysis results
        """
        expression_tool = self.config.get("expression_tool", "salmon")
        
        if expression_tool == "salmon":
            return self._run_salmon_analysis(input_files, output_dir)
        elif expression_tool == "kallisto":
            return self._run_kallisto_analysis(input_files, output_dir)
        elif expression_tool == "star":
            return self._run_star_analysis(input_files, output_dir)
        else:
            raise ValueError(f"Unsupported expression tool: {expression_tool}")
    
    def _run_salmon_analysis(self, input_files: Dict[str, str], 
                            output_dir: Path) -> Dict[str, Any]:
        """Run Salmon expression analysis."""
        try:
            reference_transcriptome = self.config.get("reference_transcriptome")
            if not reference_transcriptome:
                raise ValueError("Reference transcriptome path not specified")
            
            salmon_output = output_dir / "salmon_output"
            salmon_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["salmon"], "quant",
                "-i", reference_transcriptome,
                "-p", str(self.config.get("threads", 4)),
                "-o", str(salmon_output)
            ]
            
            # Add input files
            if "r1" in input_files and "r2" in input_files:
                cmd.extend(["-1", input_files["r1"], "-2", input_files["r2"]])
            elif "r1" in input_files:
                cmd.extend(["-r", input_files["r1"]])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Salmon analysis failed: {result.stderr}")
            
            # Parse results
            results = self._parse_salmon_results(salmon_output)
            
            return {
                "output_dir": str(salmon_output),
                "expression_tool": "salmon",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Salmon analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_kallisto_analysis(self, input_files: Dict[str, str], 
                              output_dir: Path) -> Dict[str, Any]:
        """Run Kallisto expression analysis."""
        try:
            reference_transcriptome = self.config.get("reference_transcriptome")
            if not reference_transcriptome:
                raise ValueError("Reference transcriptome path not specified")
            
            kallisto_output = output_dir / "kallisto_output"
            kallisto_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["kallisto"], "quant",
                "-i", reference_transcriptome,
                "-t", str(self.config.get("threads", 4)),
                "-o", str(kallisto_output)
            ]
            
            # Add input files
            if "r1" in input_files and "r2" in input_files:
                cmd.extend([input_files["r1"], input_files["r2"]])
            elif "r1" in input_files:
                cmd.extend(["--single", "-l", "200", "-s", "20", input_files["r1"]])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Kallisto analysis failed: {result.stderr}")
            
            # Parse results
            results = self._parse_kallisto_results(kallisto_output)
            
            return {
                "output_dir": str(kallisto_output),
                "expression_tool": "kallisto",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Kallisto analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _run_star_analysis(self, input_files: Dict[str, str], 
                          output_dir: Path) -> Dict[str, Any]:
        """Run STAR expression analysis."""
        try:
            reference_genome = self.config.get("reference_genome")
            annotation_file = self.config.get("annotation_file")
            
            if not reference_genome:
                raise ValueError("Reference genome path not specified")
            if not annotation_file:
                raise ValueError("Annotation file path not specified")
            
            star_output = output_dir / "star_output"
            star_output.mkdir(exist_ok=True)
            
            cmd = [
                self.tools["star"],
                "--runMode", "alignReads",
                "--genomeDir", reference_genome,
                "--readFilesIn"
            ]
            
            # Add input files
            if "r1" in input_files and "r2" in input_files:
                cmd.extend([input_files["r1"], input_files["r2"]])
            elif "r1" in input_files:
                cmd.append(input_files["r1"])
            
            cmd.extend([
                "--outFileNamePrefix", str(star_output / ""),
                "--outSAMtype", "BAM", "SortedByCoordinate",
                "--quantMode", "GeneCounts",
                "--sjdbGTFfile", annotation_file,
                "--runThreadN", str(self.config.get("threads", 4))
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"STAR analysis failed: {result.stderr}")
            
            # Parse results
            results = self._parse_star_results(star_output)
            
            return {
                "output_dir": str(star_output),
                "expression_tool": "star",
                "results": results,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"STAR analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_salmon_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse Salmon results."""
        try:
            quant_file = output_dir / "quant.sf"
            if not quant_file.exists():
                return {"error": "Quantification file not found"}
            
            df = pd.read_csv(quant_file, sep='\t')
            
            return {
                "total_transcripts": len(df),
                "expressed_transcripts": len(df[df['TPM'] > 0]),
                "mean_tpm": df['TPM'].mean(),
                "median_tpm": df['TPM'].median(),
                "top_transcripts": df.nlargest(10, 'TPM')[['Name', 'TPM']].to_dict('records')
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_kallisto_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse Kallisto results."""
        try:
            abundance_file = output_dir / "abundance.tsv"
            if not abundance_file.exists():
                return {"error": "Abundance file not found"}
            
            df = pd.read_csv(abundance_file, sep='\t')
            
            return {
                "total_transcripts": len(df),
                "expressed_transcripts": len(df[df['tpm'] > 0]),
                "mean_tpm": df['tpm'].mean(),
                "median_tpm": df['tpm'].median(),
                "top_transcripts": df.nlargest(10, 'tpm')[['target_id', 'tpm']].to_dict('records')
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_star_results(self, output_dir: Path) -> Dict[str, Any]:
        """Parse STAR results."""
        try:
            counts_file = output_dir / "ReadsPerGene.out.tab"
            if not counts_file.exists():
                return {"error": "Gene counts file not found"}
            
            df = pd.read_csv(counts_file, sep='\t', header=None, 
                           names=['gene_id', 'unstranded', 'forward', 'reverse'])
            
            # Use unstranded counts
            df['counts'] = df['unstranded']
            
            return {
                "total_genes": len(df),
                "expressed_genes": len(df[df['counts'] > 0]),
                "mean_counts": df['counts'].mean(),
                "median_counts": df['counts'].median(),
                "top_genes": df.nlargest(10, 'counts')[['gene_id', 'counts']].to_dict('records')
            }
            
        except Exception as e:
            return {"error": str(e)}

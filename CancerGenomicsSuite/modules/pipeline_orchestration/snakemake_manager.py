#!/usr/bin/env python3
"""
Snakemake Pipeline Manager

This module provides comprehensive Snakemake pipeline management capabilities
for cancer genomics analysis workflows.
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

logger = logging.getLogger(__name__)


class SnakemakeManager:
    """
    Manager for Snakemake pipeline execution and monitoring.
    
    Provides functionality to:
    - Execute Snakemake pipelines
    - Monitor pipeline progress
    - Manage pipeline configurations
    - Handle pipeline outputs
    """
    
    def __init__(self, work_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize Snakemake manager.
        
        Args:
            work_dir: Working directory for pipeline execution
            config_file: Path to Snakemake configuration file
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "snakemake_work"
        self.config_file = config_file
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline execution tracking
        self.active_pipelines: Dict[str, Dict] = {}
        self.pipeline_history: List[Dict] = []
        
        # Default Snakemake configuration
        self.default_config = {
            "cores": 4,
            "memory": "8GB",
            "timeout": 3600,
            "retries": 3,
            "latency_wait": 5,
            "keep_going": True,
            "rerun_incomplete": True,
            "use_conda": True,
            "use_singularity": False,
            "conda_prefix": str(self.work_dir / "conda_envs"),
            "singularity_prefix": str(self.work_dir / "singularity_images")
        }
    
    def create_config_file(self, config: Optional[Dict] = None) -> str:
        """
        Create Snakemake configuration file.
        
        Args:
            config: Configuration dictionary to use
            
        Returns:
            Path to created configuration file
        """
        config_data = config or self.default_config
        
        config_file = self.work_dir / "config.yaml"
        
        with open(config_file, 'w') as f:
            f.write("# Snakemake configuration for Cancer Genomics Analysis\n")
            f.write(f"# Generated on {datetime.now().isoformat()}\n\n")
            
            for key, value in config_data.items():
                if isinstance(value, str):
                    f.write(f"{key}: \"{value}\"\n")
                else:
                    f.write(f"{key}: {value}\n")
        
        return str(config_file)
    
    def execute_pipeline(
        self,
        snakefile: str,
        targets: Optional[List[str]] = None,
        config: Optional[Dict] = None,
        profile: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a Snakemake pipeline.
        
        Args:
            snakefile: Path to Snakefile
            targets: List of target files to generate
            config: Configuration overrides
            profile: Snakemake profile to use
            pipeline_name: Name for the pipeline execution
            dry_run: If True, only show what would be executed
            
        Returns:
            Dictionary with execution details and results
        """
        pipeline_name = pipeline_name or f"snakemake_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create execution directory
        exec_dir = self.work_dir / pipeline_name
        exec_dir.mkdir(parents=True, exist_ok=True)
        
        # Create configuration file if needed
        config_file = None
        if config:
            config_file = self.create_config_file(config)
        
        # Build Snakemake command
        cmd = ["snakemake"]
        
        if config_file:
            cmd.extend(["--configfile", config_file])
        
        if profile:
            cmd.extend(["--profile", profile])
        
        if targets:
            cmd.extend(targets)
        
        if dry_run:
            cmd.append("--dry-run")
        
        # Add common options
        cmd.extend([
            "--cores", str(self.default_config["cores"]),
            "--latency-wait", str(self.default_config["latency_wait"]),
            "--rerun-incomplete"
        ])
        
        if self.default_config["keep_going"]:
            cmd.append("--keep-going")
        
        if self.default_config["use_conda"]:
            cmd.extend(["--use-conda", "--conda-prefix", self.default_config["conda_prefix"]])
        
        if self.default_config["use_singularity"]:
            cmd.extend(["--use-singularity", "--singularity-prefix", self.default_config["singularity_prefix"]])
        
        # Execute pipeline
        logger.info(f"Executing Snakemake pipeline: {pipeline_name}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(exec_dir)
            )
            
            # Store pipeline information
            pipeline_info = {
                "name": pipeline_name,
                "snakefile": snakefile,
                "targets": targets or [],
                "config": config,
                "profile": profile,
                "exec_dir": str(exec_dir),
                "process": process,
                "start_time": datetime.now(),
                "status": "running",
                "dry_run": dry_run
            }
            
            self.active_pipelines[pipeline_name] = pipeline_info
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            # Update pipeline status
            pipeline_info.update({
                "end_time": datetime.now(),
                "status": "completed" if process.returncode == 0 else "failed",
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            })
            
            # Move to history
            self.pipeline_history.append(pipeline_info)
            del self.active_pipelines[pipeline_name]
            
            logger.info(f"Pipeline {pipeline_name} completed with status: {pipeline_info['status']}")
            
            return pipeline_info
            
        except Exception as e:
            logger.error(f"Failed to execute pipeline {pipeline_name}: {e}")
            
            # Update pipeline status
            if pipeline_name in self.active_pipelines:
                self.active_pipelines[pipeline_name].update({
                    "end_time": datetime.now(),
                    "status": "error",
                    "error": str(e)
                })
                self.pipeline_history.append(self.active_pipelines[pipeline_name])
                del self.active_pipelines[pipeline_name]
            
            raise
    
    def get_pipeline_status(self, pipeline_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a pipeline execution.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Pipeline status information or None if not found
        """
        if pipeline_name in self.active_pipelines:
            pipeline_info = self.active_pipelines[pipeline_name].copy()
            pipeline_info["duration"] = (datetime.now() - pipeline_info["start_time"]).total_seconds()
            return pipeline_info
        
        # Check history
        for pipeline in self.pipeline_history:
            if pipeline["name"] == pipeline_name:
                return pipeline
        
        return None
    
    def list_pipelines(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all pipelines with optional status filter.
        
        Args:
            status: Filter by status (running, completed, failed, error)
            
        Returns:
            List of pipeline information dictionaries
        """
        all_pipelines = list(self.active_pipelines.values()) + self.pipeline_history
        
        if status:
            all_pipelines = [p for p in all_pipelines if p.get("status") == status]
        
        return all_pipelines
    
    def stop_pipeline(self, pipeline_name: str) -> bool:
        """
        Stop a running pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to stop
            
        Returns:
            True if pipeline was stopped successfully
        """
        if pipeline_name not in self.active_pipelines:
            return False
        
        pipeline_info = self.active_pipelines[pipeline_name]
        process = pipeline_info.get("process")
        
        if process and process.poll() is None:
            process.terminate()
            pipeline_info.update({
                "end_time": datetime.now(),
                "status": "stopped"
            })
            
            # Move to history
            self.pipeline_history.append(pipeline_info)
            del self.active_pipelines[pipeline_name]
            
            logger.info(f"Pipeline {pipeline_name} stopped")
            return True
        
        return False
    
    def get_pipeline_outputs(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get outputs from a completed pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Dictionary with output file information
        """
        pipeline_info = self.get_pipeline_status(pipeline_name)
        if not pipeline_info or pipeline_info["status"] not in ["completed", "failed"]:
            return {}
        
        exec_dir = Path(pipeline_info["exec_dir"])
        outputs = {
            "execution_directory": str(exec_dir),
            "files": [],
            "logs": {}
        }
        
        # Find output files
        for file_path in exec_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(exec_dir)
                outputs["files"].append({
                    "path": str(rel_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        # Find Snakemake logs
        log_files = {
            "snakemake_log": ".snakemake/log",
            "conda_logs": ".snakemake/conda-logs",
            "benchmark": ".snakemake/benchmarks"
        }
        
        for log_type, log_path in log_files.items():
            full_log_path = exec_dir / log_path
            if full_log_path.exists():
                outputs["logs"][log_type] = str(full_log_path)
        
        return outputs
    
    def create_cancer_genomics_snakefile(self, pipeline_type: str) -> str:
        """
        Create a pre-configured cancer genomics Snakefile.
        
        Args:
            pipeline_type: Type of pipeline (variant_calling, expression_analysis, etc.)
            
        Returns:
            Path to created Snakefile
        """
        pipeline_dir = self.work_dir / "snakefiles"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        
        if pipeline_type == "variant_calling":
            return self._create_variant_calling_snakefile(pipeline_dir)
        elif pipeline_type == "expression_analysis":
            return self._create_expression_analysis_snakefile(pipeline_dir)
        elif pipeline_type == "multi_omics":
            return self._create_multi_omics_snakefile(pipeline_dir)
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
    
    def _create_variant_calling_snakefile(self, pipeline_dir: Path) -> str:
        """Create variant calling Snakefile."""
        snakefile = pipeline_dir / "variant_calling.smk"
        
        script_content = '''#!/usr/bin/env python3
"""
Cancer Genomics Variant Calling Snakefile

This Snakefile performs variant calling on cancer genomics data
using best practices for somatic variant detection.
"""

import os
from pathlib import Path

# Configuration
configfile: "config.yaml"

# Input files
SAMPLES, = glob_wildcards("data/{sample}_R1.fastq.gz")
REFERENCE = config["reference"]
KNOWN_SITES = config["known_sites"]
OUTPUT_DIR = config["output_dir"]

# Rule all
rule all:
    input:
        expand(f"{OUTPUT_DIR}/{{sample}}_annotated.vcf", sample=SAMPLES)

# Quality control
rule fastqc:
    input:
        r1 = "data/{sample}_R1.fastq.gz",
        r2 = "data/{sample}_R2.fastq.gz"
    output:
        html = f"{OUTPUT_DIR}/{{sample}}_fastqc.html",
        zip = f"{OUTPUT_DIR}/{{sample}}_fastqc.zip"
    conda:
        "envs/fastqc.yaml"
    shell:
        "fastqc {input.r1} {input.r2} -o {OUTPUT_DIR}"

# Trimming
rule trimmomatic:
    input:
        r1 = "data/{sample}_R1.fastq.gz",
        r2 = "data/{sample}_R2.fastq.gz"
    output:
        r1_trimmed = f"{OUTPUT_DIR}/{{sample}}_trimmed_R1.fastq.gz",
        r1_unpaired = f"{OUTPUT_DIR}/{{sample}}_unpaired_R1.fastq.gz",
        r2_trimmed = f"{OUTPUT_DIR}/{{sample}}_trimmed_R2.fastq.gz",
        r2_unpaired = f"{OUTPUT_DIR}/{{sample}}_unpaired_R2.fastq.gz"
    conda:
        "envs/trimmomatic.yaml"
    shell:
        "trimmomatic PE {input.r1} {input.r2} "
        "{output.r1_trimmed} {output.r1_unpaired} "
        "{output.r2_trimmed} {output.r2_unpaired} "
        "ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 "
        "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36"

# Alignment
rule bwa_mem:
    input:
        r1 = f"{OUTPUT_DIR}/{{sample}}_trimmed_R1.fastq.gz",
        r2 = f"{OUTPUT_DIR}/{{sample}}_trimmed_R2.fastq.gz",
        reference = REFERENCE
    output:
        bam = f"{OUTPUT_DIR}/{{sample}}.bam"
    conda:
        "envs/bwa.yaml"
    shell:
        "bwa mem -t {threads} {input.reference} {input.r1} {input.r2} | "
        "samtools view -bS - > {output.bam}"

# Mark duplicates
rule mark_duplicates:
    input:
        bam = f"{OUTPUT_DIR}/{{sample}}.bam"
    output:
        bam = f"{OUTPUT_DIR}/{{sample}}_dedup.bam",
        metrics = f"{OUTPUT_DIR}/{{sample}}_dedup.metrics"
    conda:
        "envs/gatk.yaml"
    shell:
        "gatk MarkDuplicates "
        "-I {input.bam} "
        "-O {output.bam} "
        "-M {output.metrics}"

# Base quality score recalibration
rule bqsr:
    input:
        bam = f"{OUTPUT_DIR}/{{sample}}_dedup.bam",
        reference = REFERENCE,
        known_sites = KNOWN_SITES
    output:
        bam = f"{OUTPUT_DIR}/{{sample}}_recal.bam",
        table = f"{OUTPUT_DIR}/{{sample}}_recal.table"
    conda:
        "envs/gatk.yaml"
    shell:
        "gatk BaseRecalibrator "
        "-I {input.bam} "
        "-R {input.reference} "
        "--known-sites {input.known_sites} "
        "-O {output.table} && "
        "gatk ApplyBQSR "
        "-I {input.bam} "
        "-R {input.reference} "
        "-bqsr {output.table} "
        "-O {output.bam}"

# Variant calling
rule mutect2:
    input:
        bam = f"{OUTPUT_DIR}/{{sample}}_recal.bam",
        reference = REFERENCE
    output:
        vcf = f"{OUTPUT_DIR}/{{sample}}_variants.vcf"
    conda:
        "envs/gatk.yaml"
    shell:
        "gatk Mutect2 "
        "-I {input.bam} "
        "-R {input.reference} "
        "-O {output.vcf}"

# Variant filtering
rule filter_variants:
    input:
        vcf = f"{OUTPUT_DIR}/{{sample}}_variants.vcf"
    output:
        vcf = f"{OUTPUT_DIR}/{{sample}}_filtered.vcf"
    conda:
        "envs/gatk.yaml"
    shell:
        "gatk FilterMutectCalls "
        "-V {input.vcf} "
        "-O {output.vcf}"

# Variant annotation
rule annovar:
    input:
        vcf = f"{OUTPUT_DIR}/{{sample}}_filtered.vcf"
    output:
        vcf = f"{OUTPUT_DIR}/{{sample}}_annotated.vcf"
    conda:
        "envs/annovar.yaml"
    shell:
        "convert2annovar.pl -format vcf4 {input.vcf} > {input.vcf}.avinput && "
        "annotate_variation.pl -geneanno -buildver hg38 {input.vcf}.avinput humandb/ && "
        "cp {input.vcf} {output.vcf}"
'''
        
        with open(snakefile, 'w') as f:
            f.write(script_content)
        
        # Create conda environment files
        self._create_conda_envs(pipeline_dir)
        
        return str(snakefile)
    
    def _create_expression_analysis_snakefile(self, pipeline_dir: Path) -> str:
        """Create expression analysis Snakefile."""
        snakefile = pipeline_dir / "expression_analysis.smk"
        
        script_content = '''#!/usr/bin/env python3
"""
Cancer Genomics Expression Analysis Snakefile

This Snakefile performs RNA-seq expression analysis for cancer genomics
including quality control, alignment, quantification, and differential expression.
"""

import os
from pathlib import Path

# Configuration
configfile: "config.yaml"

# Input files
SAMPLES, = glob_wildcards("data/{sample}_R1.fastq.gz")
REFERENCE = config["reference"]
GTF = config["gtf"]
OUTPUT_DIR = config["output_dir"]

# Rule all
rule all:
    input:
        f"{OUTPUT_DIR}/deseq2_results.csv",
        f"{OUTPUT_DIR}/deseq2_plots.pdf"

# Quality control
rule fastqc:
    input:
        r1 = "data/{sample}_R1.fastq.gz",
        r2 = "data/{sample}_R2.fastq.gz"
    output:
        html = f"{OUTPUT_DIR}/{{sample}}_fastqc.html",
        zip = f"{OUTPUT_DIR}/{{sample}}_fastqc.zip"
    conda:
        "envs/fastqc.yaml"
    shell:
        "fastqc {input.r1} {input.r2} -o {OUTPUT_DIR}"

# Trimming
rule trimmomatic:
    input:
        r1 = "data/{sample}_R1.fastq.gz",
        r2 = "data/{sample}_R2.fastq.gz"
    output:
        r1_trimmed = f"{OUTPUT_DIR}/{{sample}}_trimmed_R1.fastq.gz",
        r1_unpaired = f"{OUTPUT_DIR}/{{sample}}_unpaired_R1.fastq.gz",
        r2_trimmed = f"{OUTPUT_DIR}/{{sample}}_trimmed_R2.fastq.gz",
        r2_unpaired = f"{OUTPUT_DIR}/{{sample}}_unpaired_R2.fastq.gz"
    conda:
        "envs/trimmomatic.yaml"
    shell:
        "trimmomatic PE {input.r1} {input.r2} "
        "{output.r1_trimmed} {output.r1_unpaired} "
        "{output.r2_trimmed} {output.r2_unpaired} "
        "ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 "
        "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36"

# Alignment
rule star:
    input:
        r1 = f"{OUTPUT_DIR}/{{sample}}_trimmed_R1.fastq.gz",
        r2 = f"{OUTPUT_DIR}/{{sample}}_trimmed_R2.fastq.gz",
        reference = REFERENCE,
        gtf = GTF
    output:
        bam = f"{OUTPUT_DIR}/{{sample}}Aligned.sortedByCoord.out.bam",
        log = f"{OUTPUT_DIR}/{{sample}}Log.final.out"
    conda:
        "envs/star.yaml"
    shell:
        "STAR --runMode alignReads "
        "--genomeDir star_index "
        "--readFilesIn {input.r1} {input.r2} "
        "--readFilesCommand zcat "
        "--outSAMtype BAM SortedByCoordinate "
        "--outFileNamePrefix {OUTPUT_DIR}/{wildcards.sample} "
        "--runThreadN {threads}"

# Quantification
rule featurecounts:
    input:
        bam = f"{OUTPUT_DIR}/{{sample}}Aligned.sortedByCoord.out.bam",
        gtf = GTF
    output:
        counts = f"{OUTPUT_DIR}/{{sample}}_counts.txt"
    conda:
        "envs/subread.yaml"
    shell:
        "featureCounts -a {input.gtf} -o {output.counts} {input.bam}"

# Quality assessment
rule rseqc:
    input:
        bam = f"{OUTPUT_DIR}/{{sample}}Aligned.sortedByCoord.out.bam",
        gtf = GTF
    output:
        coverage = f"{OUTPUT_DIR}/{{sample}}_geneBodyCoverage.txt",
        experiment = f"{OUTPUT_DIR}/{{sample}}_infer_experiment.txt"
    conda:
        "envs/rseqc.yaml"
    shell:
        "geneBody_coverage.py -i {input.bam} -r {input.gtf} -o {OUTPUT_DIR}/{wildcards.sample} && "
        "infer_experiment.py -i {input.bam} -r {input.gtf} > {output.experiment}"

# Differential expression
rule deseq2:
    input:
        counts = expand(f"{OUTPUT_DIR}/{{sample}}_counts.txt", sample=SAMPLES)
    output:
        results = f"{OUTPUT_DIR}/deseq2_results.csv",
        plots = f"{OUTPUT_DIR}/deseq2_plots.pdf"
    conda:
        "envs/deseq2.yaml"
    script:
        "scripts/deseq2_analysis.R"
'''
        
        with open(snakefile, 'w') as f:
            f.write(script_content)
        
        # Create R script for DESeq2
        self._create_deseq2_script(pipeline_dir)
        
        return str(snakefile)
    
    def _create_multi_omics_snakefile(self, pipeline_dir: Path) -> str:
        """Create multi-omics integration Snakefile."""
        snakefile = pipeline_dir / "multi_omics.smk"
        
        script_content = '''#!/usr/bin/env python3
"""
Cancer Genomics Multi-Omics Integration Snakefile

This Snakefile integrates multiple omics data types for comprehensive
cancer genomics analysis including genomics, transcriptomics, and epigenomics.
"""

import os
from pathlib import Path

# Configuration
configfile: "config.yaml"

# Input files
GENOMICS_FILES = glob_wildcards("data/genomics/{sample}.vcf")[0]
TRANSCRIPTOMICS_FILES = glob_wildcards("data/transcriptomics/{sample}.bam")[0]
EPIGENOMICS_FILES = glob_wildcards("data/epigenomics/{sample}.bed")[0]
REFERENCE = config["reference"]
GTF = config["gtf"]
OUTPUT_DIR = config["output_dir"]

# Rule all
rule all:
    input:
        f"{OUTPUT_DIR}/integrated_omics_data.csv",
        f"{OUTPUT_DIR}/pathway_analysis_results.csv"

# Process genomics data
rule process_genomics:
    input:
        vcf = "data/genomics/{sample}.vcf"
    output:
        vcf = f"{OUTPUT_DIR}/genomics/{{sample}}_processed.vcf"
    conda:
        "envs/bcftools.yaml"
    shell:
        "bcftools filter -i 'QUAL>20 && DP>10' {input.vcf} > {output.vcf}"

# Process transcriptomics data
rule process_transcriptomics:
    input:
        bam = "data/transcriptomics/{sample}.bam",
        gtf = GTF
    output:
        expression = f"{OUTPUT_DIR}/transcriptomics/{{sample}}_expression.txt"
    conda:
        "envs/subread.yaml"
    shell:
        "featureCounts -a {input.gtf} -o {output.expression}.counts {input.bam} && "
        "Rscript -e \""
        "counts <- read.table('{output.expression}.counts', header=TRUE, row.names=1); "
        "normalized <- log2(counts + 1); "
        "write.table(normalized, '{output.expression}', sep='\\t', quote=FALSE)"
        "\""

# Process epigenomics data
rule process_epigenomics:
    input:
        bed = "data/epigenomics/{sample}.bed"
    output:
        bed = f"{OUTPUT_DIR}/epigenomics/{{sample}}_processed.bed"
    conda:
        "envs/bedtools.yaml"
    shell:
        "sort -k1,1 -k2,2n {input.bed} > {output.bed}.sorted && "
        "bedtools merge -i {output.bed}.sorted > {output.bed}"

# Integrate omics data
rule integrate_omics:
    input:
        genomics = expand(f"{OUTPUT_DIR}/genomics/{{sample}}_processed.vcf", sample=GENOMICS_FILES),
        transcriptomics = expand(f"{OUTPUT_DIR}/transcriptomics/{{sample}}_expression.txt", sample=TRANSCRIPTOMICS_FILES),
        epigenomics = expand(f"{OUTPUT_DIR}/epigenomics/{{sample}}_processed.bed", sample=EPIGENOMICS_FILES)
    output:
        integrated = f"{OUTPUT_DIR}/integrated_omics_data.csv"
    conda:
        "envs/r.yaml"
    script:
        "scripts/integrate_omics.R"

# Pathway analysis
rule pathway_analysis:
    input:
        integrated_data = f"{OUTPUT_DIR}/integrated_omics_data.csv"
    output:
        results = f"{OUTPUT_DIR}/pathway_analysis_results.csv",
        plots = f"{OUTPUT_DIR}/pathway_plots.pdf"
    conda:
        "envs/clusterprofiler.yaml"
    script:
        "scripts/pathway_analysis.R"
'''
        
        with open(snakefile, 'w') as f:
            f.write(script_content)
        
        return str(snakefile)
    
    def _create_conda_envs(self, pipeline_dir: Path):
        """Create conda environment files for the pipeline."""
        envs_dir = pipeline_dir / "envs"
        envs_dir.mkdir(exist_ok=True)
        
        # FastQC environment
        fastqc_env = envs_dir / "fastqc.yaml"
        with open(fastqc_env, 'w') as f:
            f.write('''channels:
  - bioconda
  - conda-forge
dependencies:
  - fastqc=0.11.9
''')
        
        # Trimmomatic environment
        trimmomatic_env = envs_dir / "trimmomatic.yaml"
        with open(trimmomatic_env, 'w') as f:
            f.write('''channels:
  - bioconda
  - conda-forge
dependencies:
  - trimmomatic=0.39
''')
        
        # BWA environment
        bwa_env = envs_dir / "bwa.yaml"
        with open(bwa_env, 'w') as f:
            f.write('''channels:
  - bioconda
  - conda-forge
dependencies:
  - bwa=0.7.17
  - samtools=1.17
''')
        
        # GATK environment
        gatk_env = envs_dir / "gatk.yaml"
        with open(gatk_env, 'w') as f:
            f.write('''channels:
  - bioconda
  - conda-forge
dependencies:
  - gatk4=4.4.0.0
''')
        
        # Annovar environment
        annovar_env = envs_dir / "annovar.yaml"
        with open(annovar_env, 'w') as f:
            f.write('''channels:
  - bioconda
  - conda-forge
dependencies:
  - annovar=2020-06-07
''')
    
    def _create_deseq2_script(self, pipeline_dir: Path):
        """Create DESeq2 analysis R script."""
        scripts_dir = pipeline_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        deseq2_script = scripts_dir / "deseq2_analysis.R"
        with open(deseq2_script, 'w') as f:
            f.write('''#!/usr/bin/env Rscript
"""
DESeq2 Analysis Script for Cancer Genomics Expression Analysis
"""

library(DESeq2)
library(ggplot2)
library(dplyr)

# Read command line arguments
args <- commandArgs(trailingOnly = TRUE)
count_files <- args[1:length(args)]

# Read count data
count_data <- list()
for (file in count_files) {
    sample_name <- basename(file)
    sample_name <- gsub("_counts.txt", "", sample_name)
    count_data[[sample_name]] <- read.table(file, header=TRUE, row.names=1)
}

# Combine count data
count_matrix <- do.call(cbind, count_data)

# Create sample metadata
col_data <- data.frame(
    condition = c(rep("control", ncol(count_matrix)/2), rep("treatment", ncol(count_matrix)/2)),
    row.names = colnames(count_matrix)
)

# Create DESeq2 object
dds <- DESeqDataSetFromMatrix(countData = count_matrix, colData = col_data, design = ~ condition)

# Run DESeq2
dds <- DESeq(dds)
res <- results(dds)

# Save results
write.csv(res, "deseq2_results.csv")

# Create plots
pdf("deseq2_plots.pdf")
plotMA(res)
plotDispEsts(dds)
dev.off()
''')

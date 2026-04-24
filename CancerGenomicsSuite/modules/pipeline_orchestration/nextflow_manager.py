#!/usr/bin/env python3
"""
Nextflow Pipeline Manager

This module provides comprehensive Nextflow pipeline management capabilities
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


class NextflowManager:
    """
    Manager for Nextflow pipeline execution and monitoring.
    
    Provides functionality to:
    - Execute Nextflow pipelines
    - Monitor pipeline progress
    - Manage pipeline configurations
    - Handle pipeline outputs
    """
    
    def __init__(self, work_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize Nextflow manager.
        
        Args:
            work_dir: Working directory for pipeline execution
            config_file: Path to Nextflow configuration file
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "nextflow_work"
        self.config_file = config_file
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline execution tracking
        self.active_pipelines: Dict[str, Dict] = {}
        self.pipeline_history: List[Dict] = []
        
        # Default Nextflow configuration
        self.default_config = {
            "process": {
                "cpus": 4,
                "memory": "8.GB",
                "time": "1.h"
            },
            "executor": {
                "name": "local",
                "queueSize": 100
            },
            "workDir": str(self.work_dir),
            "report": {
                "enabled": True,
                "file": "pipeline_report.html"
            },
            "timeline": {
                "enabled": True,
                "file": "pipeline_timeline.html"
            },
            "trace": {
                "enabled": True,
                "file": "pipeline_trace.txt"
            }
        }
    
    def create_config_file(self, config: Optional[Dict] = None) -> str:
        """
        Create Nextflow configuration file.
        
        Args:
            config: Configuration dictionary to use
            
        Returns:
            Path to created configuration file
        """
        config_data = config or self.default_config
        
        config_file = self.work_dir / "nextflow.config"
        
        with open(config_file, 'w') as f:
            f.write("// Nextflow configuration for Cancer Genomics Analysis\n")
            f.write("// Generated on {}\n\n".format(datetime.now().isoformat()))
            
            # Write process configuration
            if "process" in config_data:
                f.write("process {\n")
                for key, value in config_data["process"].items():
                    f.write(f"    {key} = {value}\n")
                f.write("}\n\n")
            
            # Write executor configuration
            if "executor" in config_data:
                f.write("executor {\n")
                for key, value in config_data["executor"].items():
                    f.write(f"    {key} = {value}\n")
                f.write("}\n\n")
            
            # Write other configurations
            for section, settings in config_data.items():
                if section not in ["process", "executor"]:
                    f.write(f"{section} {{\n")
                    if isinstance(settings, dict):
                        for key, value in settings.items():
                            f.write(f"    {key} = {value}\n")
                    else:
                        f.write(f"    {settings}\n")
                    f.write("}\n\n")
        
        return str(config_file)
    
    def execute_pipeline(
        self,
        pipeline_script: str,
        params: Optional[Dict[str, Any]] = None,
        profile: Optional[str] = None,
        config: Optional[Dict] = None,
        pipeline_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a Nextflow pipeline.
        
        Args:
            pipeline_script: Path to Nextflow pipeline script
            params: Pipeline parameters
            profile: Nextflow profile to use
            config: Configuration overrides
            pipeline_name: Name for the pipeline execution
            
        Returns:
            Dictionary with execution details and results
        """
        pipeline_name = pipeline_name or f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create execution directory
        exec_dir = self.work_dir / pipeline_name
        exec_dir.mkdir(parents=True, exist_ok=True)
        
        # Create configuration file if needed
        config_file = None
        if config:
            config_file = self.create_config_file(config)
        
        # Build Nextflow command
        cmd = ["nextflow", "run", pipeline_script]
        
        if config_file:
            cmd.extend(["-c", config_file])
        
        if profile:
            cmd.extend(["-profile", profile])
        
        if params:
            for key, value in params.items():
                cmd.extend(["--" + key, str(value)])
        
        # Add output directory
        cmd.extend(["-w", str(exec_dir)])
        
        # Execute pipeline
        logger.info(f"Executing Nextflow pipeline: {pipeline_name}")
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
                "script": pipeline_script,
                "params": params or {},
                "profile": profile,
                "config": config,
                "exec_dir": str(exec_dir),
                "process": process,
                "start_time": datetime.now(),
                "status": "running"
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
            "reports": {}
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
        
        # Find Nextflow reports
        report_files = {
            "report": "pipeline_report.html",
            "timeline": "pipeline_timeline.html",
            "trace": "pipeline_trace.txt"
        }
        
        for report_type, filename in report_files.items():
            report_path = exec_dir / filename
            if report_path.exists():
                outputs["reports"][report_type] = str(report_path)
        
        return outputs
    
    def create_cancer_genomics_pipeline(self, pipeline_type: str) -> str:
        """
        Create a pre-configured cancer genomics pipeline.
        
        Args:
            pipeline_type: Type of pipeline (variant_calling, expression_analysis, etc.)
            
        Returns:
            Path to created pipeline script
        """
        pipeline_dir = self.work_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        
        if pipeline_type == "variant_calling":
            return self._create_variant_calling_pipeline(pipeline_dir)
        elif pipeline_type == "expression_analysis":
            return self._create_expression_analysis_pipeline(pipeline_dir)
        elif pipeline_type == "multi_omics":
            return self._create_multi_omics_pipeline(pipeline_dir)
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
    
    def _create_variant_calling_pipeline(self, pipeline_dir: Path) -> str:
        """Create variant calling pipeline script."""
        pipeline_script = pipeline_dir / "variant_calling.nf"
        
        script_content = '''#!/usr/bin/env nextflow

/*
 * Cancer Genomics Variant Calling Pipeline
 * 
 * This pipeline performs variant calling on cancer genomics data
 * using best practices for somatic variant detection.
 */

params.reads = "data/*_R{1,2}.fastq.gz"
params.reference = "reference/hg38.fa"
params.output_dir = "results"
params.known_sites = "reference/dbsnp.vcf.gz"

workflow {
    // Quality control
    FASTQC(Channel.fromFilePairs(params.reads))
    
    // Trimming
    TRIMMOMATIC(FASTQC.out)
    
    // Alignment
    BWA_MEM(TRIMMOMATIC.out, params.reference)
    
    // Mark duplicates
    MARK_DUPLICATES(BWA_MEM.out)
    
    // Base quality score recalibration
    BQSR(MARK_DUPLICATES.out, params.reference, params.known_sites)
    
    // Variant calling
    MUTECT2(BQSR.out, params.reference)
    
    // Variant filtering
    FILTER_VARIANTS(MUTECT2.out)
    
    // Annotation
    ANNOVAR(FILTER_VARIANTS.out)
}

process FASTQC {
    cpus 4
    memory '8.GB'
    
    input:
    tuple val(sample), path(reads)
    
    output:
    path("${sample}_fastqc.html"), emit: html
    path("${sample}_fastqc.zip"), emit: zip
    
    script:
    """
    fastqc ${reads} -o .
    """
}

process TRIMMOMATIC {
    cpus 4
    memory '8.GB'
    
    input:
    tuple val(sample), path(reads)
    
    output:
    tuple val(sample), path("${sample}_trimmed_R{1,2}.fastq.gz"), emit: trimmed
    
    script:
    """
    trimmomatic PE ${reads} \\
        ${sample}_trimmed_R1.fastq.gz ${sample}_unpaired_R1.fastq.gz \\
        ${sample}_trimmed_R2.fastq.gz ${sample}_unpaired_R2.fastq.gz \\
        ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 \\
        LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36
    """
}

process BWA_MEM {
    cpus 8
    memory '16.GB'
    
    input:
    tuple val(sample), path(reads)
    path reference
    
    output:
    path("${sample}.bam"), emit: bam
    
    script:
    """
    bwa mem -t ${task.cpus} ${reference} ${reads} | \\
    samtools view -bS - > ${sample}.bam
    """
}

process MARK_DUPLICATES {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    
    output:
    path("${bam.baseName}_dedup.bam"), emit: bam
    path("${bam.baseName}_dedup.metrics"), emit: metrics
    
    script:
    """
    gatk MarkDuplicates \\
        -I ${bam} \\
        -O ${bam.baseName}_dedup.bam \\
        -M ${bam.baseName}_dedup.metrics
    """
}

process BQSR {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    path reference
    path known_sites
    
    output:
    path("${bam.baseName}_recal.bam"), emit: bam
    path("${bam.baseName}_recal.table"), emit: table
    
    script:
    """
    gatk BaseRecalibrator \\
        -I ${bam} \\
        -R ${reference} \\
        --known-sites ${known_sites} \\
        -O ${bam.baseName}_recal.table
    
    gatk ApplyBQSR \\
        -I ${bam} \\
        -R ${reference} \\
        -bqsr ${bam.baseName}_recal.table \\
        -O ${bam.baseName}_recal.bam
    """
}

process MUTECT2 {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    path reference
    
    output:
    path("${bam.baseName}_variants.vcf"), emit: vcf
    
    script:
    """
    gatk Mutect2 \\
        -I ${bam} \\
        -R ${reference} \\
        -O ${bam.baseName}_variants.vcf
    """
}

process FILTER_VARIANTS {
    cpus 2
    memory '4.GB'
    
    input:
    path vcf
    
    output:
    path("${vcf.baseName}_filtered.vcf"), emit: vcf
    
    script:
    """
    gatk FilterMutectCalls \\
        -V ${vcf} \\
        -O ${vcf.baseName}_filtered.vcf
    """
}

process ANNOVAR {
    cpus 2
    memory '4.GB'
    
    input:
    path vcf
    
    output:
    path("${vcf.baseName}_annotated.vcf"), emit: vcf
    
    script:
    """
    convert2annovar.pl -format vcf4 ${vcf} > ${vcf.baseName}.avinput
    annotate_variation.pl -geneanno -buildver hg38 ${vcf.baseName}.avinput humandb/
    """
}
'''
        
        with open(pipeline_script, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(pipeline_script, 0o755)
        
        return str(pipeline_script)
    
    def _create_expression_analysis_pipeline(self, pipeline_dir: Path) -> str:
        """Create expression analysis pipeline script."""
        pipeline_script = pipeline_dir / "expression_analysis.nf"
        
        script_content = '''#!/usr/bin/env nextflow

/*
 * Cancer Genomics Expression Analysis Pipeline
 * 
 * This pipeline performs RNA-seq expression analysis for cancer genomics
 * including quality control, alignment, quantification, and differential expression.
 */

params.reads = "data/*_R{1,2}.fastq.gz"
params.reference = "reference/hg38.fa"
params.gtf = "reference/hg38.gtf"
params.output_dir = "results"

workflow {
    // Quality control
    FASTQC(Channel.fromFilePairs(params.reads))
    
    // Trimming
    TRIMMOMATIC(FASTQC.out)
    
    // Alignment
    STAR(TRIMMOMATIC.out, params.reference, params.gtf)
    
    // Quantification
    FEATURECOUNTS(STAR.out, params.gtf)
    
    // Quality assessment
    RSEQC(STAR.out)
    
    // Differential expression
    DESEQ2(FEATURECOUNTS.out)
}

process FASTQC {
    cpus 4
    memory '8.GB'
    
    input:
    tuple val(sample), path(reads)
    
    output:
    path("${sample}_fastqc.html"), emit: html
    path("${sample}_fastqc.zip"), emit: zip
    
    script:
    """
    fastqc ${reads} -o .
    """
}

process TRIMMOMATIC {
    cpus 4
    memory '8.GB'
    
    input:
    tuple val(sample), path(reads)
    
    output:
    tuple val(sample), path("${sample}_trimmed_R{1,2}.fastq.gz"), emit: trimmed
    
    script:
    """
    trimmomatic PE ${reads} \\
        ${sample}_trimmed_R1.fastq.gz ${sample}_unpaired_R1.fastq.gz \\
        ${sample}_trimmed_R2.fastq.gz ${sample}_unpaired_R2.fastq.gz \\
        ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 \\
        LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36
    """
}

process STAR {
    cpus 8
    memory '32.GB'
    
    input:
    tuple val(sample), path(reads)
    path reference
    path gtf
    
    output:
    path("${sample}Aligned.sortedByCoord.out.bam"), emit: bam
    path("${sample}Log.final.out"), emit: log
    
    script:
    """
    STAR --runMode alignReads \\
        --genomeDir star_index \\
        --readFilesIn ${reads} \\
        --readFilesCommand zcat \\
        --outSAMtype BAM SortedByCoordinate \\
        --outFileNamePrefix ${sample} \\
        --runThreadN ${task.cpus}
    """
}

process FEATURECOUNTS {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    path gtf
    
    output:
    path("${bam.baseName}_counts.txt"), emit: counts
    
    script:
    """
    featureCounts -a ${gtf} -o ${bam.baseName}_counts.txt ${bam}
    """
}

process RSEQC {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    
    output:
    path("${bam.baseName}_geneBodyCoverage.txt"), emit: coverage
    path("${bam.baseName}_infer_experiment.txt"), emit: experiment
    
    script:
    """
    geneBody_coverage.py -i ${bam} -r ${gtf} -o ${bam.baseName}
    infer_experiment.py -i ${bam} -r ${gtf} > ${bam.baseName}_infer_experiment.txt
    """
}

process DESEQ2 {
    cpus 4
    memory '8.GB'
    
    input:
    path counts
    
    output:
    path("deseq2_results.csv"), emit: results
    path("deseq2_plots.pdf"), emit: plots
    
    script:
    """
    Rscript -e "
    library(DESeq2)
    library(ggplot2)
    
    # Read count data
    counts <- read.table('${counts}', header=TRUE, row.names=1)
    
    # Create sample metadata
    colData <- data.frame(
        condition = c(rep('control', ncol(counts)/2), rep('treatment', ncol(counts)/2))
    )
    
    # Create DESeq2 object
    dds <- DESeqDataSetFromMatrix(countData = counts, colData = colData, design = ~ condition)
    
    # Run DESeq2
    dds <- DESeq(dds)
    res <- results(dds)
    
    # Save results
    write.csv(res, 'deseq2_results.csv')
    
    # Create plots
    pdf('deseq2_plots.pdf')
    plotMA(res)
    plotDispEsts(dds)
    dev.off()
    "
    """
}
'''
        
        with open(pipeline_script, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(pipeline_script, 0o755)
        
        return str(pipeline_script)
    
    def _create_multi_omics_pipeline(self, pipeline_dir: Path) -> str:
        """Create multi-omics integration pipeline script."""
        pipeline_script = pipeline_dir / "multi_omics.nf"
        
        script_content = '''#!/usr/bin/env nextflow

/*
 * Cancer Genomics Multi-Omics Integration Pipeline
 * 
 * This pipeline integrates multiple omics data types for comprehensive
 * cancer genomics analysis including genomics, transcriptomics, and epigenomics.
 */

params.genomics_data = "data/genomics/*.vcf"
params.transcriptomics_data = "data/transcriptomics/*.bam"
params.epigenomics_data = "data/epigenomics/*.bed"
params.reference = "reference/hg38.fa"
params.output_dir = "results"

workflow {
    // Process genomics data
    PROCESS_GENOMICS(Channel.fromPath(params.genomics_data))
    
    // Process transcriptomics data
    PROCESS_TRANSCRIPTOMICS(Channel.fromPath(params.transcriptomics_data))
    
    // Process epigenomics data
    PROCESS_EPIGENOMICS(Channel.fromPath(params.epigenomics_data))
    
    // Integrate omics data
    INTEGRATE_OMICS(PROCESS_GENOMICS.out, PROCESS_TRANSCRIPTOMICS.out, PROCESS_EPIGENOMICS.out)
    
    // Pathway analysis
    PATHWAY_ANALYSIS(INTEGRATE_OMICS.out)
}

process PROCESS_GENOMICS {
    cpus 4
    memory '8.GB'
    
    input:
    path vcf
    
    output:
    path("${vcf.baseName}_processed.vcf"), emit: vcf
    
    script:
    """
    # Filter variants
    bcftools filter -i 'QUAL>20 && DP>10' ${vcf} > ${vcf.baseName}_filtered.vcf
    
    # Annotate variants
    annovar annotate_variation.pl -geneanno -buildver hg38 ${vcf.baseName}_filtered.vcf humandb/
    
    # Create processed output
    cp ${vcf.baseName}_filtered.vcf ${vcf.baseName}_processed.vcf
    """
}

process PROCESS_TRANSCRIPTOMICS {
    cpus 4
    memory '8.GB'
    
    input:
    path bam
    
    output:
    path("${bam.baseName}_expression.txt"), emit: expression
    
    script:
    """
    # Count reads
    featureCounts -a ${gtf} -o ${bam.baseName}_counts.txt ${bam}
    
    # Normalize expression
    Rscript -e "
    counts <- read.table('${bam.baseName}_counts.txt', header=TRUE, row.names=1)
    normalized <- log2(counts + 1)
    write.table(normalized, '${bam.baseName}_expression.txt', sep='\\t', quote=FALSE)
    "
    """
}

process PROCESS_EPIGENOMICS {
    cpus 4
    memory '8.GB'
    
    input:
    path bed
    
    output:
    path("${bed.baseName}_processed.bed"), emit: bed
    
    script:
    """
    # Sort and merge peaks
    sort -k1,1 -k2,2n ${bed} > ${bed.baseName}_sorted.bed
    bedtools merge -i ${bed.baseName}_sorted.bed > ${bed.baseName}_processed.bed
    """
}

process INTEGRATE_OMICS {
    cpus 8
    memory '16.GB'
    
    input:
    path genomics
    path transcriptomics
    path epigenomics
    
    output:
    path("integrated_omics_data.csv"), emit: integrated
    
    script:
    """
    Rscript -e "
    library(GenomicRanges)
    library(SummarizedExperiment)
    
    # Read genomics data
    genomics <- read.table('${genomics}', header=TRUE)
    
    # Read transcriptomics data
    transcriptomics <- read.table('${transcriptomics}', header=TRUE)
    
    # Read epigenomics data
    epigenomics <- read.table('${epigenomics}', header=FALSE)
    
    # Integrate data
    integrated_data <- data.frame(
        gene_id = rownames(transcriptomics),
        expression = transcriptomics[,1],
        mutation_count = sapply(rownames(transcriptomics), function(gene) {
            sum(genomics[genomics[,'Gene.refGene'] == gene, 'ExonicFunc.refGene'] != 'synonymous SNV')
        }),
        peak_count = sapply(rownames(transcriptomics), function(gene) {
            # Count overlapping peaks (simplified)
            nrow(epigenomics)
        })
    )
    
    write.csv(integrated_data, 'integrated_omics_data.csv', row.names=FALSE)
    "
    """
}

process PATHWAY_ANALYSIS {
    cpus 4
    memory '8.GB'
    
    input:
    path integrated_data
    
    output:
    path("pathway_analysis_results.csv"), emit: results
    path("pathway_plots.pdf"), emit: plots
    
    script:
    """
    Rscript -e "
    library(clusterProfiler)
    library(org.Hs.eg.db)
    library(ggplot2)
    
    # Read integrated data
    data <- read.csv('${integrated_data}')
    
    # Perform pathway analysis
    gene_list <- data[data[,'expression'] > 2, 'gene_id']
    
    # Convert gene symbols to ENTREZ IDs
    gene_entrez <- bitr(gene_list, fromType='SYMBOL', toType='ENTREZID', OrgDb=org.Hs.eg.db)
    
    # GO enrichment
    go_results <- enrichGO(gene=gene_entrez[,'ENTREZID'], 
                          OrgDb=org.Hs.eg.db, 
                          ont='BP', 
                          pAdjustMethod='BH')
    
    # KEGG enrichment
    kegg_results <- enrichKEGG(gene=gene_entrez[,'ENTREZID'], 
                              organism='hsa', 
                              pAdjustMethod='BH')
    
    # Save results
    write.csv(go_results@result, 'pathway_analysis_results.csv')
    
    # Create plots
    pdf('pathway_plots.pdf')
    if(nrow(go_results@result) > 0) {
        barplot(go_results, showCategory=20)
        dotplot(go_results, showCategory=20)
    }
    if(nrow(kegg_results@result) > 0) {
        barplot(kegg_results, showCategory=20)
        dotplot(kegg_results, showCategory=20)
    }
    dev.off()
    "
    """
}
'''
        
        with open(pipeline_script, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(pipeline_script, 0o755)
        
        return str(pipeline_script)

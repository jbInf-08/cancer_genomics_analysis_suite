#!/usr/bin/env nextflow

/*
 * Cancer Genomics Analysis Pipeline
 * 
 * This Nextflow pipeline performs comprehensive cancer genomics analysis including:
 * - BLAST sequence alignment
 * - Variant annotation
 * - Machine learning prediction
 * - Report generation
 * 
 * Author: Cancer Genomics Team
 * Version: 1.0.0
 */

nextflow.enable.dsl = 2

// Pipeline parameters
params {
    // Input parameters
    input_dir = "data/input"
    output_dir = "results"
    reference_genome = "data/reference/hg38.fa"
    blast_db = "data/blastdb/nr"
    
    // BLAST parameters
    blast_evalue = "1e-5"
    blast_max_target_seqs = 100
    blast_num_threads = 4
    
    // ML parameters
    ml_model_path = "models/cancer_prediction_model.pkl"
    ml_threshold = 0.5
    
    // Resource parameters
    max_memory = "8.GB"
    max_cpus = 4
    max_time = "2.h"
    
    // Output parameters
    publish_dir = "results"
    publish_mode = "copy"
    
    // Help
    help = false
}

// Print help information
if (params.help) {
    log.info """
    Cancer Genomics Analysis Pipeline
    =================================
    
    Usage:
    nextflow run cancer_genomics_pipeline.nf --input_dir data/input --output_dir results
    
    Parameters:
    --input_dir          Input directory containing sequence files (default: data/input)
    --output_dir         Output directory for results (default: results)
    --reference_genome   Reference genome FASTA file (default: data/reference/hg38.fa)
    --blast_db          BLAST database path (default: data/blastdb/nr)
    --blast_evalue      BLAST E-value threshold (default: 1e-5)
    --blast_max_target_seqs Maximum number of target sequences (default: 100)
    --blast_num_threads Number of BLAST threads (default: 4)
    --ml_model_path     Path to ML model (default: models/cancer_prediction_model.pkl)
    --ml_threshold      ML prediction threshold (default: 0.5)
    --max_memory        Maximum memory per process (default: 8.GB)
    --max_cpus          Maximum CPUs per process (default: 4)
    --max_time          Maximum time per process (default: 2.h)
    --publish_dir       Directory to publish results (default: results)
    --publish_mode      Publish mode (default: copy)
    --help              Show this help message
    
    Examples:
    nextflow run cancer_genomics_pipeline.nf --input_dir /path/to/sequences --blast_evalue 1e-3
    nextflow run cancer_genomics_pipeline.nf --ml_threshold 0.7 --max_memory 16.GB
    """
    exit 0
}

// Include subworkflows
include { BLAST_ALIGNMENT } from './subworkflows/blast_alignment'
include { VARIANT_ANNOTATION } from './subworkflows/variant_annotation'
include { ML_PREDICTION } from './subworkflows/ml_prediction'
include { REPORT_GENERATION } from './subworkflows/report_generation'

// Main workflow
workflow {
    // Input channel
    Channel
        .fromPath("${params.input_dir}/*.{fasta,fa,fq,fastq}")
        .map { file -> 
            tuple(file.baseName, file) 
        }
        .set { input_files }
    
    // Check if input files exist
    if (input_files.isEmpty()) {
        error "No input files found in ${params.input_dir}"
    }
    
    // Run BLAST alignment
    BLAST_ALIGNMENT (
        input_files,
        params.blast_db,
        params.blast_evalue,
        params.blast_max_target_seqs,
        params.blast_num_threads
    )
    
    // Run variant annotation
    VARIANT_ANNOTATION (
        BLAST_ALIGNMENT.out.blast_results,
        params.reference_genome
    )
    
    // Run ML prediction
    ML_PREDICTION (
        VARIANT_ANNOTATION.out.annotated_variants,
        params.ml_model_path,
        params.ml_threshold
    )
    
    // Generate reports
    REPORT_GENERATION (
        ML_PREDICTION.out.predictions,
        BLAST_ALIGNMENT.out.blast_results,
        VARIANT_ANNOTATION.out.annotated_variants
    )
    
    // Publish results
    REPORT_GENERATION.out.reports
        .publishDir(params.publish_dir, mode: params.publish_mode)
}

// Workflow completion
workflow.onComplete {
    log.info """
    ================================================
    Cancer Genomics Pipeline completed successfully!
    ================================================
    
    Results published to: ${params.publish_dir}
    Pipeline execution time: ${workflow.duration}
    Successfully completed processes: ${workflow.successCount}
    Failed processes: ${workflow.failCount}
    
    """
}

// Workflow error handling
workflow.onError {
    log.error """
    ================================================
    Cancer Genomics Pipeline failed!
    ================================================
    
    Error: ${workflow.errorMessage}
    Pipeline execution time: ${workflow.duration}
    Successfully completed processes: ${workflow.successCount}
    Failed processes: ${workflow.failCount}
    
    """
    exit 1
}

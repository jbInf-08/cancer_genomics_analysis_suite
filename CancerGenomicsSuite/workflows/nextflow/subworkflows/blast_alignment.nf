/*
 * BLAST Alignment Subworkflow
 * 
 * This subworkflow performs BLAST sequence alignment for cancer genomics analysis
 */

nextflow.enable.dsl = 2

workflow BLAST_ALIGNMENT {
    take:
    input_files      // channel: [sample_id, file]
    blast_db         // path to BLAST database
    blast_evalue     // E-value threshold
    blast_max_target_seqs // maximum target sequences
    blast_num_threads // number of threads
    
    main:
    ch_versions = Channel.empty()
    
    // Prepare BLAST database
    BLAST_DB_PREPARE (
        blast_db
    )
    ch_versions = ch_versions.mix(BLAST_DB_PREPARE.out.versions)
    
    // Run BLAST alignment
    BLAST_ALIGN (
        input_files,
        BLAST_DB_PREPARE.out.blast_db,
        blast_evalue,
        blast_max_target_seqs,
        blast_num_threads
    )
    ch_versions = ch_versions.mix(BLAST_ALIGN.out.versions)
    
    // Parse BLAST results
    BLAST_PARSE (
        BLAST_ALIGN.out.blast_results
    )
    ch_versions = ch_versions.mix(BLAST_PARSE.out.versions)
    
    // Filter BLAST results
    BLAST_FILTER (
        BLAST_PARSE.out.parsed_results
    )
    ch_versions = ch_versions.mix(BLAST_FILTER.out.versions)
    
    emit:
    blast_results = BLAST_FILTER.out.filtered_results
    versions = ch_versions
}

// Process to prepare BLAST database
process BLAST_DB_PREPARE {
    tag "blast_db_prepare"
    label 'process_medium'
    
    input:
    path blast_db
    
    output:
    path "blast_db/*", emit: blast_db
    path "versions.yml", emit: versions
    
    script:
    """
    # Create output directory
    mkdir -p blast_db
    
    # Copy BLAST database files
    cp -r ${blast_db}/* blast_db/
    
    # Create versions file
    echo "BLAST_DB_PREPARE:" > versions.yml
    echo "  blast_db: ${blast_db}" >> versions.yml
    echo "  timestamp: \$(date)" >> versions.yml
    """
}

// Process to run BLAST alignment
process BLAST_ALIGN {
    tag "${sample_id}"
    label 'process_high'
    cpus params.blast_num_threads
    memory params.max_memory
    time params.max_time
    
    input:
    tuple val(sample_id), path(input_file)
    path blast_db
    val blast_evalue
    val blast_max_target_seqs
    val blast_num_threads
    
    output:
    path "${sample_id}_blast_results.xml", emit: blast_results
    path "versions.yml", emit: versions
    
    script:
    """
    # Run BLAST alignment
    blastn \\
        -query ${input_file} \\
        -db ${blast_db}/nr \\
        -out ${sample_id}_blast_results.xml \\
        -outfmt 5 \\
        -evalue ${blast_evalue} \\
        -max_target_seqs ${blast_max_target_seqs} \\
        -num_threads ${blast_num_threads} \\
        -word_size 11 \\
        -reward 2 \\
        -penalty -3 \\
        -gapopen 5 \\
        -gapextend 2
    
    # Create versions file
    echo "BLAST_ALIGN:" > versions.yml
    echo "  sample_id: ${sample_id}" >> versions.yml
    echo "  blast_evalue: ${blast_evalue}" >> versions.yml
    echo "  blast_max_target_seqs: ${blast_max_target_seqs}" >> versions.yml
    echo "  blast_num_threads: ${blast_num_threads}" >> versions.yml
    echo "  timestamp: \$(date)" >> versions.yml
    """
}

// Process to parse BLAST results
process BLAST_PARSE {
    tag "${sample_id}"
    label 'process_low'
    
    input:
    path blast_results
    
    output:
    path "${sample_id}_parsed_results.tsv", emit: parsed_results
    path "versions.yml", emit: versions
    
    script:
    """
    # Parse BLAST XML results to TSV
    python3 -c "
    import xml.etree.ElementTree as ET
    import sys
    
    def parse_blast_xml(xml_file, output_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        with open(output_file, 'w') as f:
            f.write('query_id\\tquery_length\\tsubject_id\\tsubject_length\\tidentity\\talignment_length\\tquery_start\\tquery_end\\tsubject_start\\tsubject_end\\tevalue\\tbit_score\\tquery_sequence\\tsubject_sequence\\n')
            
            for iteration in root.findall('BlastOutput_iterations/Iteration'):
                query_id = iteration.find('Iteration_query-def').text if iteration.find('Iteration_query-def') is not None else 'unknown'
                query_length = iteration.find('Iteration_query-len').text if iteration.find('Iteration_query-len') is not None else '0'
                
                for hit in iteration.findall('Iteration_hits/Hit'):
                    subject_id = hit.find('Hit_id').text if hit.find('Hit_id') is not None else 'unknown'
                    subject_length = hit.find('Hit_len').text if hit.find('Hit_len') is not None else '0'
                    
                    for hsp in hit.findall('Hit_hsps/Hsp'):
                        identity = hsp.find('Hsp_identity').text if hsp.find('Hsp_identity') is not None else '0'
                        alignment_length = hsp.find('Hsp_align-len').text if hsp.find('Hsp_align-len') is not None else '0'
                        query_start = hsp.find('Hsp_query-from').text if hsp.find('Hsp_query-from') is not None else '0'
                        query_end = hsp.find('Hsp_query-to').text if hsp.find('Hsp_query-to') is not None else '0'
                        subject_start = hsp.find('Hsp_hit-from').text if hsp.find('Hsp_hit-from') is not None else '0'
                        subject_end = hsp.find('Hsp_hit-to').text if hsp.find('Hsp_hit-to') is not None else '0'
                        evalue = hsp.find('Hsp_evalue').text if hsp.find('Hsp_evalue') is not None else '1'
                        bit_score = hsp.find('Hsp_bit-score').text if hsp.find('Hsp_bit-score') is not None else '0'
                        query_sequence = hsp.find('Hsp_qseq').text if hsp.find('Hsp_qseq') is not None else ''
                        subject_sequence = hsp.find('Hsp_hseq').text if hsp.find('Hsp_hseq') is not None else ''
                        
                        f.write(f'{query_id}\\t{query_length}\\t{subject_id}\\t{subject_length}\\t{identity}\\t{alignment_length}\\t{query_start}\\t{query_end}\\t{subject_start}\\t{subject_end}\\t{evalue}\\t{bit_score}\\t{query_sequence}\\t{subject_sequence}\\n')
    
    parse_blast_xml('${blast_results}', '${sample_id}_parsed_results.tsv')
    "
    
    # Create versions file
    echo "BLAST_PARSE:" > versions.yml
    echo "  sample_id: ${sample_id}" >> versions.yml
    echo "  timestamp: \$(date)" >> versions.yml
    """
}

// Process to filter BLAST results
process BLAST_FILTER {
    tag "${sample_id}"
    label 'process_low'
    
    input:
    path parsed_results
    
    output:
    path "${sample_id}_filtered_results.tsv", emit: filtered_results
    path "versions.yml", emit: versions
    
    script:
    """
    # Filter BLAST results based on quality criteria
    python3 -c "
    import pandas as pd
    import sys
    
    def filter_blast_results(input_file, output_file):
        # Read parsed results
        df = pd.read_csv(input_file, sep='\\t')
        
        # Filter criteria
        # 1. E-value < 1e-5
        df = df[df['evalue'] < 1e-5]
        
        # 2. Identity > 80%
        df = df[df['identity'] / df['alignment_length'] > 0.8]
        
        # 3. Alignment length > 50
        df = df[df['alignment_length'] > 50]
        
        # 4. Bit score > 50
        df = df[df['bit_score'] > 50]
        
        # Sort by bit score (descending)
        df = df.sort_values('bit_score', ascending=False)
        
        # Keep top 10 hits per query
        df = df.groupby('query_id').head(10)
        
        # Save filtered results
        df.to_csv(output_file, sep='\\t', index=False)
        
        print(f'Filtered {len(df)} high-quality BLAST hits')
    
    filter_blast_results('${parsed_results}', '${sample_id}_filtered_results.tsv')
    "
    
    # Create versions file
    echo "BLAST_FILTER:" > versions.yml
    echo "  sample_id: ${sample_id}" >> versions.yml
    echo "  timestamp: \$(date)" >> versions.yml
    """
}

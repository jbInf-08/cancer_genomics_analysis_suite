# GROMACS molecular dynamics and Ensembl annotation reference

This document describes what the Cancer Genomics Analysis Suite **does** and **does not** do for structure-based MD and for Ensembl-powered locus annotation, so expectations stay aligned with research and clinical governance.

---

## 1. Coordinate systems and assemblies

### 1.1 Reference genomes (dashboards)

| Key   | Ensembl REST host              | Species key (Ensembl)   |
|-------|--------------------------------|-------------------------|
| hg38  | `https://rest.ensembl.org`     | `human` (GRCh38)       |
| hg19  | `https://grch37.rest.ensembl.org` | `human` (GRCh37)   |
| mm10  | `https://rest.ensembl.org`     | `mouse`                |
| mm9   | `https://rest.ensembl.org`     | `mouse`                |
| dm6   | `https://rest.ensembl.org`   | `drosophila_melanogaster` |
| ce11  | `https://rest.ensembl.org`   | `caenorhabditis_elegans` |

**Important:** VCF files must use coordinates consistent with the assembly you select. Mixing hg19 coordinates against the hg38 host (or vice versa) will yield incorrect genes and VEP results.

### 1.2 Gene overlap window (`predict_genes_at_position`)

- **`one_based_vcf` (default):** `position` is interpreted as **VCF POS** (first base of the variant, **1-based**). The overlap interval is built in **0-based half-open** space as:

  \[
  [\texttt{POS} - 1 - \texttt{flank},\; \texttt{POS} - 1 + \texttt{flank} + 1)
  \]

  so the variant base is included.

- **`zero_based_center`:** legacy symmetric window \([\texttt{pos} - \texttt{flank},\, \texttt{pos} + \texttt{flank})\) around the integer (matches older browser-style experiments).

Ensembl `overlap/region` URLs use **1-based inclusive** segment notation; the suite converts from half-open intervals internally.

### 1.3 VEP region call (mutation dashboard)

The optional VEP step uses **Ensembl VEP region/allele** with:

- Chromosome (with or without `chr` prefix; normalized for the API),
- **`position` as 1-based VCF POS** when overlap convention is `one_based_vcf`; when overlap convention is `zero_based_center`, POS is approximated as `position + 1` for the VEP call (documented limitation—prefer `one_based_vcf` for clinical-style SNVs),
- A single-letter **alternate** allele (required),
- Optional **reference** allele for display only.

Only **single-nucleotide substitutions** are supported in the UI path.

---

## 2. Ensembl and UniProt reliability

### 2.1 Rate limits and errors

Public Ensembl is throttled. The suite surfaces:

- HTTP status (e.g. **429**, **503**, **400**),
- **`Retry-After`** when present,
- A short **response snippet** for debugging,
- A **`user_message`** suitable for dashboards.

**Operational guidance:** cache results where possible; avoid tight loops from the UI; for production, consider local mirrors, caching proxies, or institutional VEP/annotation services.

### 2.2 UniProt search (AlphaFold gene path)

Gene-symbol → UniProt uses `rest.uniprot.org` search (`gene_exact` + `organism_id`, default human **9606**). Ambiguous symbols or missing genes return structured errors; always prefer an explicit **UniProt accession** when available.

---

## 3. Structure sources for MD

Resolution order in `MolecularDynamicsWorkflow.run`:

1. **`pdb_path`** — local PDB/mmCIF file on disk.  
2. **`pdb_id`** — RCSB `files.rcsb.org` download (four-character id, **A–Z0–9**).  
3. **`alphafold_uniprot`** — AlphaFold DB **model_v4** PDB:  
   `https://alphafold.ebi.ac.uk/files/AF-<ACCESSION>-F1-model_v4.pdb`  
4. **`alphafold_gene_symbol`** — UniProt search → accession → same AlphaFold URL.  
5. **`tpr_path`** — skip download; run `mdrun` with provided `.tpr`.

Downloads are **size-capped** (default max **80 MiB**) with clear errors if exceeded.

---

## 4. GROMACS: what is actually run

### 4.1 Pipeline

When `gmx` is on `PATH`, the suite runs a **short in-vacuum steepest-descent energy minimization** after `pdb2gmx` → `editconf` → `grompp` → `mdrun`:

- Tries force fields in order: **amber99sb-ildn**, **oplsaa**, **charmm27** (first successful `pdb2gmx` wins).
- Water model flag used in `pdb2gmx` is **tip3p** (standard for these setups).
- This is **not** explicit-solvent equilibration, **not** production MD, and **not** validated for free-energy or docking workflows.

### 4.2 Limitations

- Large multimeric PDBs, cryo-EM maps, or missing heavy atoms may cause `pdb2gmx` or `grompp` to fail—errors are returned to the UI.
- **Windows vs Linux:** GROMACS availability and MPI flags differ; the code uses `-ntmpi 1` for broader compatibility.
- **Clinical / regulatory:** do not use this path as a primary evidence source for variant interpretation.

---

## 5. Workflow history persistence

`WorkflowExecutor` appends each completed record (including MD runs) to:

- **Default file:** `<work_dir>/workflow_history.jsonl`
- **Override constructor:** `history_persist_path=Path(...)` or `""` to disable.
- **Environment override:** `WORKFLOW_HISTORY_JSONL` points to a JSONL file (handy for workers sharing a volume with the web app).

Each line is one JSON object with ISO8601 timestamps where applicable. On startup, the executor **loads the tail** (last **5000** lines) into `workflow_history` so recent jobs survive process restarts.

---

## 6. Celery background execution

Task name: `celery_worker.tasks.md_workflow_tasks.run_md_workflow`

- Queues `run_molecular_dynamics_workflow` on a worker with the same `work_dir` / `history_persist_path` you pass from the UI so JSONL audit stays consistent.
- The Dash UI shows the **Celery task id**; it does **not** poll task state—use Flower, logs, or a future API for status.

Worker import path assumes the project root is configured so `celery_worker` and `CancerGenomicsSuite` resolve (same as other suite tasks).

---

## 7. Where to look in code

| Concern              | Module / path |
|----------------------|----------------|
| Ensembl overlap/VEP | `CancerGenomicsSuite/modules/gene_annotation/gene_location_predictor.py` |
| HTTP error shaping   | `CancerGenomicsSuite/modules/gene_annotation/ensembl_api_utils.py` |
| Dash error rendering | `CancerGenomicsSuite/modules/gene_annotation/dash_error_display.py` |
| MD downloads + GROMACS | `CancerGenomicsSuite/modules/pipeline_orchestration/md_workflow.py`, `.../gromacs_integration/gromacs_client.py` |
| History JSONL        | `CancerGenomicsSuite/modules/pipeline_orchestration/workflow_executor.py` |
| Celery MD task       | `CancerGenomicsSuite/celery_worker/tasks/md_workflow_tasks.py` |

---

## 8. Disclaimer

All public API usage (Ensembl, UniProt, RCSB, AlphaFold DB) is subject to third-party terms, rate limits, and data accuracy. This software is provided for research and integration prototyping; **variant and structure conclusions require independent expert review** before any clinical or diagnostic use.

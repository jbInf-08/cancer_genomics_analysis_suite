"""
Mutation Effect Predictor Dash Dashboard

This module provides a Dash-based web interface for mutation effect prediction,
allowing users to input mutations, run predictions, and visualize results
with various prediction algorithms and consensus analysis.
"""

import time

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table, no_update
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import numpy as np

from .predictor import (
    MutationEffectPredictor,
    Mutation,
    PredictionResult,
    create_sample_mutations,
    create_sample_predictor,
)

from CancerGenomicsSuite.modules.gene_annotation.gene_location_predictor import (
    GeneLocationPredictor,
)
from CancerGenomicsSuite.modules.gene_annotation.dash_error_display import (
    structured_error_to_dash as _render_structured_api_error,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll import (
    poll_md_async_result,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.md_workflow_dash_display import (
    md_workflow_result_to_div,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import (
    WorkflowExecutor,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MutationEffectDashboard:
    """
    Dash dashboard for mutation effect prediction.
    """
    
    def __init__(self, app_name: str = "Mutation Effect Predictor"):
        """
        Initialize the mutation effect prediction dashboard.
        
        Args:
            app_name: Name of the Dash app
        """
        self.app = dash.Dash(__name__)
        self.app.title = app_name
        self.predictor = create_sample_predictor()
        self.current_predictions = []
        self._gene_loc = GeneLocationPredictor()
        self._workflow_executor = WorkflowExecutor()
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Mutation Effect Predictor", className="header-title"),
                html.P("Predict the functional impact of genetic mutations using multiple algorithms", className="header-subtitle")
            ], className="header"),
            
            # Input Panel
            html.Div([
                html.H3("Mutation Input"),
                html.Div([
                    html.Div([
                        html.Label("Gene Symbol:"),
                        dcc.Input(
                            id="gene-symbol-input",
                            type="text",
                            value="BRCA1",
                            placeholder="e.g., BRCA1, TP53, EGFR"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Chromosome:"),
                        dcc.Input(
                            id="chromosome-input",
                            type="text",
                            value="chr17",
                            placeholder="e.g., chr1, chrX, chrM"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Position:"),
                        dcc.Input(
                            id="position-input",
                            type="number",
                            value=43094695,
                            min=0
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Reference Allele:"),
                        dcc.Input(
                            id="ref-allele-input",
                            type="text",
                            value="G",
                            placeholder="e.g., A, T, G, C"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Alternative Allele:"),
                        dcc.Input(
                            id="alt-allele-input",
                            type="text",
                            value="A",
                            placeholder="e.g., A, T, G, C"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Mutation Type:"),
                        dcc.Dropdown(
                            id="mutation-type-dropdown",
                            options=[
                                {"label": "SNP", "value": "SNP"},
                                {"label": "Insertion", "value": "insertion"},
                                {"label": "Deletion", "value": "deletion"},
                                {"label": "Indel", "value": "indel"},
                                {"label": "Complex", "value": "complex"}
                            ],
                            value="SNP",
                            clearable=False
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Protein Position (optional):"),
                        dcc.Input(
                            id="protein-position-input",
                            type="number",
                            value=185,
                            min=0
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Reference Amino Acid:"),
                        dcc.Input(
                            id="ref-amino-acid-input",
                            type="text",
                            value="G",
                            placeholder="e.g., A, R, N, D, C, Q, E, G, H, I, L, K, M, F, P, S, T, W, Y, V"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Alternative Amino Acid:"),
                        dcc.Input(
                            id="alt-amino-acid-input",
                            type="text",
                            value="E",
                            placeholder="e.g., A, R, N, D, C, Q, E, G, H, I, L, K, M, F, P, S, T, W, Y, V"
                        )
                    ], className="input-group"),
                    
                    html.Div([
                        html.Label("Clinical Significance (optional):"),
                        dcc.Dropdown(
                            id="clinical-significance-dropdown",
                            options=[
                                {"label": "Pathogenic", "value": "pathogenic"},
                                {"label": "Likely Pathogenic", "value": "likely_pathogenic"},
                                {"label": "Uncertain Significance", "value": "uncertain_significance"},
                                {"label": "Likely Benign", "value": "likely_benign"},
                                {"label": "Benign", "value": "benign"}
                            ],
                            value="pathogenic",
                            clearable=True
                        )
                    ], className="input-group")
                ], className="input-grid"),
                
                html.Div([
                    html.Button("Predict Mutation Effect", id="predict-button", className="predict-button"),
                    html.Button("Load Sample Mutations", id="load-samples-button", className="sample-button"),
                    html.Button("Clear Results", id="clear-button", className="clear-button")
                ], className="button-group")
            ], className="input-panel"),

            html.Div([
                html.H3("Gene context (Ensembl + optional VEP)"),
                html.P(
                    title=(
                        "Gene overlap uses Ensembl overlap/region. VEP uses region/allele for a SNV. "
                        "hg19 uses the GRCh37 Ensembl REST host. This is not a clinical-grade pipeline—"
                        "verify all coordinates and consequences in your LIMS / diagnostic workflow."
                    ),
                    children=(
                        "Resolve overlapping genes at the locus and optionally run Ensembl VEP "
                        "for the variant above (VCF-style ref/alt; SNVs use GET, indels/MNV use POST)."
                    ),
                ),
                html.Div([
                    html.Span(
                        [
                            html.Label("Reference assembly"),
                            html.Span(
                                " ⓘ",
                                title=(
                                    "hg38 → GRCh38 (rest.ensembl.org). hg19 → GRCh37 "
                                    "(grch37.rest.ensembl.org). Match this to your VCF / BAM reference."
                                ),
                            ),
                        ]
                    ),
                    dcc.Dropdown(
                        id="annotation-ref-genome-dropdown",
                        options=[
                            {"label": "Human GRCh38 (hg38)", "value": "hg38"},
                            {"label": "Human GRCh37 (hg19)", "value": "hg19"},
                            {"label": "Mouse GRCm38 (mm10)", "value": "mm10"},
                            {"label": "Mouse NCBIM37 (mm9)", "value": "mm9"},
                            {"label": "Drosophila BDGP6 (dm6)", "value": "dm6"},
                            {"label": "C. elegans WBcel235 (ce11)", "value": "ce11"},
                        ],
                        value="hg38",
                        clearable=False,
                        style={"minWidth": "260px"},
                    ),
                ], className="input-group"),
                html.Div([
                    html.Span(
                        [
                            html.Label("Position convention (overlap window)"),
                            html.Span(
                                " ⓘ",
                                title=(
                                    "1-based VCF POS: position field is VCF POS (first base of variant). "
                                    "0-based center: symmetric window [pos±flank) in integer coordinates "
                                    "(legacy; less standard for VCF)."
                                ),
                            ),
                        ]
                    ),
                    dcc.Dropdown(
                        id="position-convention-dropdown",
                        options=[
                            {"label": "1-based VCF POS (recommended)", "value": "one_based_vcf"},
                            {"label": "0-based center (legacy)", "value": "zero_based_center"},
                        ],
                        value="one_based_vcf",
                        clearable=False,
                        style={"minWidth": "280px"},
                    ),
                ], className="input-group"),
                html.Div([
                    html.Span(
                        [
                            html.Label("Flank (bp) around position"),
                            html.Span(
                                " ⓘ",
                                title=(
                                    "Half-width of the overlap query in bp. Very large values may be "
                                    "rejected or throttled by Ensembl; start near 50–200 kb."
                                ),
                            ),
                        ]
                    ),
                    dcc.Input(
                        id="gene-flank-input",
                        type="number",
                        value=100000,
                        min=1000,
                        step=1000,
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="include-vep-checklist",
                        options=[
                            {
                                "label": "Also run Ensembl VEP for this variant (SNV + indels/MNV)",
                                "value": "vep",
                            }
                        ],
                        value=[],
                        inputStyle={"marginRight": "8px"},
                    ),
                    html.Span(
                        " ⓘ",
                        title=(
                            "VEP uses chromosome and 1-based VCF POS with REF/ALT strings. "
                            "Simple SNVs use the region GET endpoint; indels and multi-base changes use "
                            "VEP region POST with minimal allele normalization."
                        ),
                    ),
                ], className="input-group"),
                html.Button(
                    "Annotate locus with Ensembl",
                    id="annotate-locus-button",
                    className="sample-button",
                ),
                html.Div(id="gene-context-output", className="results-summary"),
                html.Hr(),
                html.H3("Molecular dynamics (GROMACS)"),
                html.P(
                    title=(
                        "This path runs short in-vacuum steepest-descent energy minimization—not "
                        "solvent MD, not ensemble sampling, and not validated for drug discovery."
                    ),
                    children=(
                        "Structure source: RCSB PDB ID, UniProt accession for AlphaFold DB model_v4, "
                        "or AlphaFold via gene symbol (UniProt search). Then vacuum EM if GROMACS is installed."
                    ),
                ),
                html.Div([
                    html.Span(
                        [
                            html.Label("PDB ID (RCSB)"),
                            html.Span(
                                " ⓘ",
                                title="Four-character PDB identifier (e.g. 1OAY). Downloaded from files.rcsb.org.",
                            ),
                        ]
                    ),
                    dcc.Input(
                        id="md-pdb-id-input",
                        type="text",
                        placeholder="e.g. 1OAY",
                        value="",
                    ),
                ], className="input-group"),
                html.Div([
                    html.Span(
                        [
                            html.Label("UniProt accession (AlphaFold)"),
                            html.Span(
                                " ⓘ",
                                title=(
                                    "If set (e.g. P04637), downloads AlphaFold DB PDB model_v4 when PDB ID "
                                    "is empty. Overrides gene-symbol AlphaFold when both are set."
                                ),
                            ),
                        ]
                    ),
                    dcc.Input(
                        id="md-alphafold-uniprot-input",
                        type="text",
                        placeholder="e.g. P04637",
                        value="",
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="md-alphafold-use-gene-checklist",
                        options=[
                            {
                                "label": "Use gene symbol for AlphaFold (UniProt search → AlphaFold PDB)",
                                "value": "use_gene",
                            }
                        ],
                        value=[],
                        inputStyle={"marginRight": "8px"},
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="md-run-via-celery-checklist",
                        options=[
                            {
                                "label": "Submit MD via Celery worker (non-blocking; requires running worker)",
                                "value": "celery",
                            }
                        ],
                        value=[],
                        inputStyle={"marginRight": "8px"},
                    ),
                    html.Span(
                        " ⓘ",
                        title=(
                            "When enabled, the job is queued on the Celery ``md_workflow_tasks`` queue. "
                            "Optionally poll the Celery result backend below for live state and the final MD summary."
                        ),
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="md-poll-celery-results-checklist",
                        options=[
                            {
                                "label": "Poll Celery result backend in this tab (task state / final summary)",
                                "value": "poll",
                            }
                        ],
                        value=["poll"],
                        inputStyle={"marginRight": "8px"},
                    ),
                    html.Span(
                        " ⓘ",
                        title=(
                            "Requires a configured result backend (e.g. Redis) on the worker and web app. "
                            "If polling fails, use Flower or worker logs."
                        ),
                    ),
                ], className="input-group"),
                dcc.Store(id="md-celery-task-store", data=None),
                dcc.Interval(
                    id="md-celery-poll-interval",
                    interval=3000,
                    n_intervals=0,
                    disabled=True,
                ),
                html.Button(
                    "Run MD workflow",
                    id="run-md-workflow-button",
                    className="clear-button",
                ),
                html.Div(id="md-workflow-output", className="results-summary"),
            ], className="input-panel"),
            
            # Predictor Selection
            html.Div([
                html.H3("Select Predictors"),
                html.Div([
                    dcc.Checklist(
                        id="predictor-checklist",
                        options=[
                            {"label": "SIFT", "value": "sift"},
                            {"label": "PolyPhen-2", "value": "polyphen2"},
                            {"label": "CADD", "value": "cadd"},
                            {"label": "REVEL", "value": "revel"},
                            {"label": "ClinVar", "value": "clinvar"},
                            {"label": "Conservation", "value": "conservation"},
                            {"label": "Structural", "value": "structural"}
                        ],
                        value=["sift", "polyphen2", "cadd", "revel"],
                        inline=True,
                        className="predictor-checklist"
                    )
                ])
            ], className="predictor-panel"),
            
            # Results Visualization
            html.Div([
                html.H3("Prediction Results"),
                html.Div(id="results-summary", className="results-summary"),
                dcc.Graph(id="prediction-plot", className="prediction-plot"),
                html.Div(id="consensus-analysis", className="consensus-analysis")
            ], className="results-panel"),
            
            # Detailed Results Table
            html.Div([
                html.H3("Detailed Results"),
                html.Div(id="results-table-container")
            ], className="table-panel"),
            
            # Export Panel
            html.Div([
                html.H3("Export Results"),
                html.Div([
                    html.Label("Format:"),
                    dcc.Dropdown(
                        id="export-format-dropdown",
                        options=[
                            {"label": "JSON", "value": "json"},
                            {"label": "CSV", "value": "csv"},
                            {"label": "TSV", "value": "tsv"}
                        ],
                        value="json",
                        clearable=False,
                        style={"width": "150px"}
                    ),
                    html.Button("Export", id="export-button", className="export-button")
                ], className="export-controls"),
                html.Div(id="export-output", className="export-output")
            ], className="export-panel"),
            
            # Statistics Panel
            html.Div([
                html.H3("Predictor Statistics"),
                html.Div(id="statistics-display", className="statistics-display")
            ], className="statistics-panel"),
            
            # Hidden div to store current mutation
            html.Div(id="current-mutation", style={"display": "none"})
        ], className="main-container")
    
    def setup_callbacks(self):
        """Set up Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output("current-mutation", "children"),
             Output("results-summary", "children"),
             Output("prediction-plot", "figure"),
             Output("consensus-analysis", "children"),
             Output("results-table-container", "children")],
            [Input("predict-button", "n_clicks"),
             Input("load-samples-button", "n_clicks")],
            [State("gene-symbol-input", "value"),
             State("chromosome-input", "value"),
             State("position-input", "value"),
             State("ref-allele-input", "value"),
             State("alt-allele-input", "value"),
             State("mutation-type-dropdown", "value"),
             State("protein-position-input", "value"),
             State("ref-amino-acid-input", "value"),
             State("alt-amino-acid-input", "value"),
             State("clinical-significance-dropdown", "value"),
             State("predictor-checklist", "value")]
        )
        def run_prediction(predict_clicks, load_samples_clicks, gene_symbol, chromosome, 
                          position, ref_allele, alt_allele, mutation_type, protein_position,
                          ref_amino_acid, alt_amino_acid, clinical_significance, selected_predictors):
            """Run mutation effect prediction."""
            
            ctx = callback_context
            if not ctx.triggered:
                # Initial load
                return "", "", go.Figure(), "", ""
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "load-samples-button" and load_samples_clicks:
                # Load sample mutations
                sample_mutations = create_sample_mutations()
                all_results = []
                
                for mutation in sample_mutations:
                    results = self.predictor.predict_mutation_effect(mutation, selected_predictors)
                    all_results.extend(results)
                
                self.current_predictions = all_results
                mutation_json = json.dumps([m.to_dict() for m in sample_mutations])
                
            elif button_id == "predict-button" and predict_clicks:
                # Predict single mutation
                try:
                    mutation = Mutation(
                        gene_symbol=gene_symbol,
                        chromosome=chromosome,
                        position=position,
                        ref_allele=ref_allele,
                        alt_allele=alt_allele,
                        mutation_type=mutation_type,
                        protein_position=protein_position,
                        ref_amino_acid=ref_amino_acid,
                        alt_amino_acid=alt_amino_acid,
                        clinical_significance=clinical_significance
                    )
                    
                    results = self.predictor.predict_mutation_effect(mutation, selected_predictors)
                    self.current_predictions = results
                    mutation_json = json.dumps(mutation.to_dict())
                    
                except Exception as e:
                    logger.error(f"Error creating mutation: {e}")
                    return f"Error: {str(e)}", "", go.Figure(), "", ""
            else:
                return "", "", go.Figure(), "", ""
            
            # Generate visualizations
            summary = self._create_results_summary()
            plot_figure = self._create_prediction_plot()
            consensus = self._create_consensus_analysis()
            table = self._create_results_table()
            
            return mutation_json, summary, plot_figure, consensus, table

        @self.app.callback(
            Output("gene-context-output", "children"),
            [Input("annotate-locus-button", "n_clicks")],
            [
                State("gene-symbol-input", "value"),
                State("chromosome-input", "value"),
                State("position-input", "value"),
                State("gene-flank-input", "value"),
                State("annotation-ref-genome-dropdown", "value"),
                State("position-convention-dropdown", "value"),
                State("include-vep-checklist", "value"),
                State("ref-allele-input", "value"),
                State("alt-allele-input", "value"),
            ],
        )
        def annotate_locus_with_ensembl(
            n_clicks,
            gene_symbol,
            chromosome,
            position,
            flank,
            ref_genome,
            pos_convention,
            vep_flags,
            ref_allele,
            alt_allele,
        ):
            if not n_clicks:
                return ""
            if not chromosome or position is None:
                return html.P("Chromosome and position are required.", className="error-message")
            flank_bp = int(flank) if flank is not None else 100_000
            ref_g = ref_genome or "hg38"
            pconv = pos_convention or "one_based_vcf"
            try:
                genes = self._gene_loc.predict_genes_at_position(
                    str(chromosome),
                    int(position),
                    flank=flank_bp,
                    reference_genome=ref_g,
                    position_convention=pconv,
                )
            except Exception as e:
                logger.exception("Gene annotation failed")
                return html.P(f"Annotation error: {e}", className="error-message")

            if not genes:
                return html.P("No overlapping genes returned for this locus.")

            if genes and (
                genes[0].get("error_kind")
                or genes[0].get("user_message")
                or (isinstance(genes[0].get("error"), str) and genes[0].get("source") == "ensembl")
            ):
                return _render_structured_api_error(genes[0])

            rows = []
            for g in genes[:50]:
                rows.append(
                    html.Tr(
                        [
                            html.Td(g.get("symbol") or ""),
                            html.Td(g.get("gene_id") or ""),
                            html.Td(str(g.get("start") or "")),
                            html.Td(str(g.get("end") or "")),
                            html.Td(str(g.get("strand") or "")),
                            html.Td((g.get("biotype") or "")),
                        ]
                    )
                )
            caption = html.P(
                [
                    html.Strong("Overlap query: "),
                    f"{gene_symbol or '—'} @ {chromosome}:{int(position):,} — assembly {ref_g}, "
                    f"convention {pconv}, flank ±{flank_bp:,} bp",
                ]
            )
            table = html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Symbol"),
                                html.Th("Gene ID"),
                                html.Th("Start"),
                                html.Th("End"),
                                html.Th("Strand"),
                                html.Th("Biotype"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="gene-context-table",
            )
            blocks: List[Any] = [caption, table]

            if vep_flags and "vep" in vep_flags:
                ra = (ref_allele or "").strip().upper()
                aa = (alt_allele or "").strip().upper()
                if not ra or not aa:
                    blocks.append(
                        html.Div(
                            [
                                html.H4("VEP skipped"),
                                html.P(
                                    "VEP requires non-empty reference and alternate alleles (VCF-style).",
                                    className="error-message",
                                ),
                            ]
                        )
                    )
                else:
                    vep_pos = int(position)
                    if pconv == "zero_based_center":
                        vep_pos = int(position) + 1
                    vep_rows = self._gene_loc.predict_vep_variant(
                        str(chromosome),
                        vep_pos,
                        ra,
                        aa,
                        reference_genome=ref_g,
                        strand=1,
                    )
                    if vep_rows and (
                        vep_rows[0].get("error_kind") or vep_rows[0].get("user_message")
                    ):
                        blocks.append(html.H4("VEP"))
                        blocks.append(_render_structured_api_error(vep_rows[0]))
                    elif not vep_rows:
                        blocks.append(
                            html.Div(
                                [
                                    html.H4("VEP"),
                                    html.P("No transcript consequences returned."),
                                ]
                            )
                        )
                    else:
                        vbody = []
                        for vr in vep_rows[:80]:
                            cons = vr.get("consequence_terms") or []
                            cons_s = ", ".join(cons) if isinstance(cons, list) else str(cons)
                            vbody.append(
                                html.Tr(
                                    [
                                        html.Td(vr.get("gene_symbol") or ""),
                                        html.Td(vr.get("transcript_id") or ""),
                                        html.Td(cons_s[:200]),
                                        html.Td(vr.get("impact") or ""),
                                        html.Td(str(vr.get("amino_acids") or "")),
                                    ]
                                )
                            )
                        blocks.append(html.H4("VEP (transcript consequences)"))
                        blocks.append(
                            html.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("Gene"),
                                                html.Th("Transcript"),
                                                html.Th("Consequence"),
                                                html.Th("Impact"),
                                                html.Th("AA change"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(vbody),
                                ],
                                className="gene-context-table",
                            )
                        )

            return html.Div(blocks)

        @self.app.callback(
            [
                Output("md-workflow-output", "children"),
                Output("md-celery-task-store", "data"),
                Output("md-celery-poll-interval", "disabled"),
            ],
            [Input("run-md-workflow-button", "n_clicks")],
            [
                State("md-pdb-id-input", "value"),
                State("md-alphafold-uniprot-input", "value"),
                State("md-alphafold-use-gene-checklist", "value"),
                State("md-run-via-celery-checklist", "value"),
                State("md-poll-celery-results-checklist", "value"),
                State("gene-symbol-input", "value"),
                State("chromosome-input", "value"),
                State("position-input", "value"),
                State("ref-allele-input", "value"),
                State("alt-allele-input", "value"),
            ],
        )
        def run_md_from_mutation_dashboard(
            n_clicks,
            pdb_id,
            af_uniprot,
            af_gene_flags,
            celery_flags,
            poll_flags,
            gene,
            chrom,
            pos,
            ref_a,
            alt_a,
        ):
            if not n_clicks:
                return "", None, True
            pid = (pdb_id or "").strip().upper()
            up = (af_uniprot or "").strip().upper()
            use_af_gene = af_gene_flags and "use_gene" in af_gene_flags
            use_celery = celery_flags and "celery" in celery_flags
            want_poll = poll_flags and "poll" in poll_flags

            summary_bits = []
            if gene:
                summary_bits.append(str(gene))
            if chrom is not None and pos is not None:
                summary_bits.append(f"{chrom}:{pos}")
            if ref_a and alt_a:
                summary_bits.append(f"{ref_a}>{alt_a}")
            mutation_summary = " / ".join(summary_bits) if summary_bits else None

            md_config: Dict[str, Any] = {
                "gene_symbol": gene,
                "mutation_summary": mutation_summary,
            }
            wf_suffix = "md"
            if len(pid) == 4:
                md_config["pdb_id"] = pid
                wf_suffix = pid
            elif up and len(up) >= 6:
                md_config["alphafold_uniprot"] = up
                wf_suffix = up
            elif use_af_gene and gene:
                md_config["alphafold_gene_symbol"] = str(gene).strip()
                wf_suffix = str(gene).strip()[:20]
            else:
                err = html.Div(
                    [
                        html.P(
                            "Provide one of: a four-letter PDB ID, a UniProt accession for AlphaFold, "
                            "or tick “Use gene symbol for AlphaFold” with a non-empty gene symbol.",
                            className="error-message",
                        )
                    ]
                )
                return err, None, True

            workflow_name = (
                f"md_mutation_dash_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{wf_suffix}"
            )

            if use_celery:
                try:
                    from celery_worker.tasks.md_workflow_tasks import run_md_workflow
                except ImportError:
                    run_md_workflow = None
                if run_md_workflow is None:
                    return (
                        html.P(
                            "Celery task module could not be imported; run MD without Celery or install worker deps.",
                            className="error-message",
                        ),
                        None,
                        True,
                    )
                hp = self._workflow_executor.history_persist_path
                async_res = run_md_workflow.delay(
                    md_config,
                    workflow_name,
                    work_dir=str(self._workflow_executor.work_dir),
                    history_persist_path=str(hp) if hp else None,
                )
                tid = async_res.id
                if want_poll:
                    return (
                        html.Div(
                            [
                                html.P([html.Strong("Celery task submitted — polling")]),
                                html.P(
                                    [
                                        "Task id: ",
                                        html.Code(tid, style={"wordBreak": "break-all"}),
                                    ]
                                ),
                                html.P(
                                    "Workflow name (JSONL / history): " + workflow_name,
                                    style={"fontSize": "0.95em"},
                                ),
                                html.P(
                                    "Status updates appear here while the result backend reports progress.",
                                    style={"fontSize": "0.9em"},
                                ),
                            ]
                        ),
                        {
                            "task_id": tid,
                            "workflow_name": workflow_name,
                            "t_mono": time.monotonic(),
                        },
                        False,
                    )
                return (
                    html.Div(
                        [
                            html.P([html.Strong("Celery task submitted")]),
                            html.P(
                                [
                                    "Task id: ",
                                    html.Code(tid, style={"wordBreak": "break-all"}),
                                ]
                            ),
                            html.P(
                                "Workflow name (for JSONL / history): " + workflow_name,
                                style={"fontSize": "0.95em"},
                            ),
                            html.P(
                                "Polling is off — enable “Poll Celery result backend” or use Flower / worker logs.",
                                style={"fontSize": "0.9em"},
                            ),
                        ]
                    ),
                    None,
                    True,
                )

            try:
                result = self._workflow_executor.run_molecular_dynamics_workflow(
                    md_config,
                    workflow_name=workflow_name,
                )
            except Exception as e:
                logger.exception("MD workflow failed")
                return (
                    html.P(f"MD workflow error: {e}", className="error-message"),
                    None,
                    True,
                )

            return (
                md_workflow_result_to_div(
                    result, workflow_name, _render_structured_api_error
                ),
                None,
                True,
            )

        @self.app.callback(
            Output("md-workflow-output", "children", allow_duplicate=True),
            Output("md-celery-task-store", "data", allow_duplicate=True),
            Output("md-celery-poll-interval", "disabled", allow_duplicate=True),
            Input("md-celery-poll-interval", "n_intervals"),
            State("md-celery-task-store", "data"),
            prevent_initial_call=True,
        )
        def poll_md_celery_task(_n_intervals, store):
            if not store or not store.get("task_id"):
                return no_update, no_update, no_update
            div, stop = poll_md_async_result(
                str(store["task_id"]),
                str(store.get("workflow_name") or ""),
                structured_error_to_dash=_render_structured_api_error,
                started_monotonic=store.get("t_mono"),
            )
            if stop:
                return div, None, True
            return div, store, False
        
        @self.app.callback(
            Output("export-output", "children"),
            [Input("export-button", "n_clicks")],
            [State("export-format-dropdown", "value")]
        )
        def export_results(export_clicks, format_type):
            """Export prediction results."""
            if not export_clicks or not self.current_predictions:
                return ""
            
            try:
                exported_data = self.predictor.export_predictions(self.current_predictions, format_type)
                
                if format_type == "json":
                    # Pretty print JSON
                    data_dict = json.loads(exported_data)
                    formatted_data = json.dumps(data_dict, indent=2)
                else:
                    formatted_data = exported_data
                
                return html.Div([
                    html.H4(f"Exported Data ({format_type.upper()})"),
                    html.Pre(formatted_data, className="export-data")
                ])
                
            except Exception as e:
                return html.Div([
                    html.H4("Export Error"),
                    html.P(f"Error exporting data: {str(e)}")
                ], className="error-message")
        
        @self.app.callback(
            Output("statistics-display", "children"),
            [Input("predict-button", "n_clicks"),
             Input("load-samples-button", "n_clicks")]
        )
        def update_statistics(predict_clicks, load_samples_clicks):
            """Update predictor statistics."""
            stats = self.predictor.get_statistics()
            
            return html.Div([
                html.P([
                    html.Strong("Available Predictors: "), ", ".join(stats["available_predictors"]),
                    html.Br(),
                    html.Strong("Supported Mutation Types: "), ", ".join(stats["supported_mutation_types"]),
                    html.Br(),
                    html.Strong("Prediction Classes: "), ", ".join(stats["prediction_classes"]),
                    html.Br(),
                    html.Strong("Cache Size: "), str(stats["cache_size"]),
                    html.Br(),
                    html.Strong("Model Loaded: "), "Yes" if stats["model_loaded"] else "No"
                ])
            ])
    
    def _create_results_summary(self) -> html.Div:
        """Create results summary display."""
        if not self.current_predictions:
            return html.P("No predictions available")
        
        # Group predictions by mutation
        mutation_groups = {}
        for result in self.current_predictions:
            mutation_key = result.mutation.get_mutation_key()
            if mutation_key not in mutation_groups:
                mutation_groups[mutation_key] = []
            mutation_groups[mutation_key].append(result)
        
        summary_items = []
        for mutation_key, results in mutation_groups.items():
            mutation = results[0].mutation
            consensus = self.predictor.get_consensus_prediction(results)
            
            summary_items.append(html.Div([
                html.H4(f"{mutation.gene_symbol} {mutation.ref_amino_acid}{mutation.protein_position}{mutation.alt_amino_acid}"),
                html.P([
                    html.Strong("Location: "), f"{mutation.chromosome}:{mutation.position:,}",
                    html.Br(),
                    html.Strong("Change: "), f"{mutation.ref_allele} → {mutation.alt_allele}",
                    html.Br(),
                    html.Strong("Consensus: "), consensus["consensus_class"],
                    html.Br(),
                    html.Strong("Confidence: "), f"{consensus['average_confidence']:.2f}",
                    html.Br(),
                    html.Strong("Predictors: "), f"{len(results)}"
                ])
            ], className="mutation-summary"))
        
        return html.Div(summary_items)
    
    def _create_prediction_plot(self) -> go.Figure:
        """Create prediction visualization plot."""
        if not self.current_predictions:
            return go.Figure().add_annotation(
                text="No predictions to display",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Prepare data for plotting
        plot_data = []
        for result in self.current_predictions:
            plot_data.append({
                "predictor": result.predictor_name,
                "score": result.prediction_score,
                "class": result.prediction_class,
                "confidence": result.confidence,
                "mutation": f"{result.mutation.gene_symbol} {result.mutation.ref_amino_acid}{result.mutation.protein_position}{result.mutation.alt_amino_acid}"
            })
        
        df = pd.DataFrame(plot_data)
        
        # Create color mapping for prediction classes
        color_map = {
            "pathogenic": "#d62728",
            "likely_pathogenic": "#ff7f0e", 
            "uncertain_significance": "#2ca02c",
            "likely_benign": "#1f77b4",
            "benign": "#9467bd",
            "error": "#7f7f7f"
        }
        
        df["color"] = df["class"].map(color_map)
        
        # Create scatter plot
        fig = go.Figure()
        
        for mutation in df["mutation"].unique():
            mutation_data = df[df["mutation"] == mutation]
            
            fig.add_trace(go.Scatter(
                x=mutation_data["predictor"],
                y=mutation_data["score"],
                mode="markers",
                marker=dict(
                    size=mutation_data["confidence"] * 20 + 5,
                    color=mutation_data["color"],
                    opacity=0.7,
                    line=dict(width=2, color="white")
                ),
                name=mutation,
                text=mutation_data["class"],
                hovertemplate="<b>%{x}</b><br>Score: %{y:.3f}<br>Class: %{text}<br>Confidence: %{marker.size}<extra></extra>"
            ))
        
        fig.update_layout(
            title="Mutation Effect Predictions",
            xaxis_title="Predictor",
            yaxis_title="Prediction Score",
            height=500,
            showlegend=True,
            hovermode="closest"
        )
        
        return fig
    
    def _create_consensus_analysis(self) -> html.Div:
        """Create consensus analysis display."""
        if not self.current_predictions:
            return html.P("No predictions for consensus analysis")
        
        # Group by mutation
        mutation_groups = {}
        for result in self.current_predictions:
            mutation_key = result.mutation.get_mutation_key()
            if mutation_key not in mutation_groups:
                mutation_groups[mutation_key] = []
            mutation_groups[mutation_key].append(result)
        
        consensus_items = []
        for mutation_key, results in mutation_groups.items():
            consensus = self.predictor.get_consensus_prediction(results)
            mutation = results[0].mutation
            
            consensus_items.append(html.Div([
                html.H4(f"Consensus for {mutation.gene_symbol} {mutation.ref_amino_acid}{mutation.protein_position}{mutation.alt_amino_acid}"),
                html.P([
                    html.Strong("Consensus Class: "), consensus["consensus_class"],
                    html.Br(),
                    html.Strong("Agreement Ratio: "), f"{consensus['consensus_ratio']:.2f}",
                    html.Br(),
                    html.Strong("Average Confidence: "), f"{consensus['average_confidence']:.2f}",
                    html.Br(),
                    html.Strong("Total Predictors: "), str(consensus["total_predictors"])
                ]),
                html.Details([
                    html.Summary("Class Distribution"),
                    html.Ul([
                        html.Li(f"{class_name}: {count}")
                        for class_name, count in consensus["class_distribution"].items()
                    ])
                ])
            ], className="consensus-item"))
        
        return html.Div(consensus_items)
    
    def _create_results_table(self) -> html.Div:
        """Create detailed results table."""
        if not self.current_predictions:
            return html.P("No results to display")
        
        # Prepare data for table
        table_data = []
        for result in self.current_predictions:
            table_data.append({
                "Gene": result.mutation.gene_symbol,
                "Location": f"{result.mutation.chromosome}:{result.mutation.position:,}",
                "Change": f"{result.mutation.ref_allele} → {result.mutation.alt_allele}",
                "Protein Change": f"{result.mutation.ref_amino_acid}{result.mutation.protein_position}{result.mutation.alt_amino_acid}" if result.mutation.protein_position else "N/A",
                "Predictor": result.predictor_name,
                "Score": f"{result.prediction_score:.3f}",
                "Class": result.prediction_class,
                "Confidence": f"{result.confidence:.3f}",
                "Timestamp": result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f9f9f9"
                },
                {
                    "if": {"filter_query": "{Class} = pathogenic"},
                    "backgroundColor": "#ffebee"
                },
                {
                    "if": {"filter_query": "{Class} = benign"},
                    "backgroundColor": "#e8f5e8"
                }
            ],
            page_size=20,
            sort_action="native",
            filter_action="native",
            export_format="csv"
        )
    
    def run(self, debug: bool = True, port: int = 8051):
        """
        Run the dashboard.
        
        Args:
            debug: Enable debug mode
            port: Port to run the app on
        """
        logger.info(f"Starting Mutation Effect Predictor Dashboard on port {port}")
        self.app.run_server(debug=debug, port=port)


# CSS Styles
custom_css = """
.main-container {
    fontFamily: 'Inter', sans-serif;
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    color: white;
    border-radius: 10px;
}

.header-title {
    margin: 0;
    font-size: 2.5em;
    font-weight: 700;
}

.header-subtitle {
    margin: 10px 0 0 0;
    font-size: 1.1em;
    opacity: 0.9;
}

.input-panel, .predictor-panel, .results-panel, .table-panel, .export-panel, .statistics-panel {
    margin-bottom: 20px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.input-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.input-group {
    display: flex;
    flex-direction: column;
}

.input-group label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.button-group {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.predict-button {
    background: #e74c3c;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    font-size: 1.1em;
    transition: background-color 0.2s;
}

.predict-button:hover {
    background: #c0392b;
}

.sample-button {
    background: #3498db;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
}

.sample-button:hover {
    background: #2980b9;
}

.clear-button {
    background: #95a5a6;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
}

.clear-button:hover {
    background: #7f8c8d;
}

.predictor-checklist {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
}

.predictor-checklist .form-check {
    margin-right: 20px;
}

.results-summary {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}

.mutation-summary {
    background: white;
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 5px;
    border-left: 4px solid #e74c3c;
}

.prediction-plot {
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
}

.consensus-analysis {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-top: 20px;
}

.consensus-item {
    background: white;
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 5px;
    border-left: 4px solid #3498db;
}

.export-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-button {
    background: #27ae60;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.export-button:hover {
    background: #229954;
}

.export-data {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
    max-height: 400px;
    overflow-y: auto;
    fontFamily: 'Courier New', monospace;
    font-size: 0.9em;
}

.statistics-display {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
}

.error-message {
    color: #dc3545;
    background: #f8d7da;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
}
"""


def create_mutation_effect_dashboard() -> MutationEffectDashboard:
    """
    Create and return a mutation effect prediction dashboard instance.
    
    Returns:
        MutationEffectDashboard instance
    """
    return MutationEffectDashboard()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = create_mutation_effect_dashboard()
    
    # Add custom CSS
    dashboard.app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>{{%title%}}</title>
            {{%favicon%}}
            {{%css%}}
            <style>{custom_css}</style>
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """
    
    dashboard.run(debug=True, port=8051)

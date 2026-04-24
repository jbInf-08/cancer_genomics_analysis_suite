"""
Lightweight mutation list analysis utilities.

Used by dashboards and tests; keeps logic deterministic and side-effect free
except for ``fetch_external_data`` (HTTP) and file I/O helpers.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = (
    "gene",
    "mutation",
    "impact",
    "chromosome",
    "position",
    "ref_allele",
    "alt_allele",
    "sample_id",
)
_VALID_IMPACT = frozenset({"high", "moderate", "low"})


def _mutation_key(m: Dict[str, Any]) -> Tuple[str, str, str]:
    return (str(m["gene"]), str(m["mutation"]), str(m["sample_id"]))


class MutationAnalyzer:
    """Analyze and filter lists of mutation dictionaries."""

    def _validate_record(self, m: Dict[str, Any], *, strict: bool = False) -> None:
        if not isinstance(m, dict):
            raise ValueError("Invalid input")
        missing = [f for f in _REQUIRED_FIELDS if f not in m]
        if missing:
            raise ValueError("Missing required fields")
        if strict and str(m.get("impact", "")).lower() not in _VALID_IMPACT:
            raise ValueError("Invalid input")

    def analyze_mutations(self, mutations: Any) -> Dict[str, int]:
        if mutations is None or isinstance(mutations, (str, int, dict)):
            raise ValueError("Invalid input")
        if not isinstance(mutations, list):
            raise ValueError("Invalid input")
        for m in mutations:
            self._validate_record(m, strict=True)
        hi = mo = lo = 0
        for m in mutations:
            imp = str(m["impact"]).lower()
            if imp == "high":
                hi += 1
            elif imp == "moderate":
                mo += 1
            elif imp == "low":
                lo += 1
        return {
            "total_mutations": len(mutations),
            "high_impact_count": hi,
            "moderate_impact_count": mo,
            "low_impact_count": lo,
        }

    def filter_mutations_by_impact(
        self, mutations: List[Dict[str, Any]], impact: str
    ) -> List[Dict[str, Any]]:
        return [
            m for m in mutations if str(m.get("impact", "")).lower() == impact.lower()
        ]

    def filter_mutations_by_gene(
        self, mutations: List[Dict[str, Any]], gene: str
    ) -> List[Dict[str, Any]]:
        return [m for m in mutations if str(m.get("gene", "")) == gene]

    def filter_mutations_by_sample(
        self, mutations: List[Dict[str, Any]], sample_id: str
    ) -> List[Dict[str, Any]]:
        return [m for m in mutations if str(m.get("sample_id", "")) == sample_id]

    def calculate_mutation_frequency(
        self, mutations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        return dict(Counter(str(m["gene"]) for m in mutations))

    def get_mutation_summary(self, mutations: List[Dict[str, Any]]) -> Dict[str, Any]:
        dist = {"high": 0, "moderate": 0, "low": 0}
        for m in mutations:
            imp = str(m.get("impact", "")).lower()
            if imp in dist:
                dist[imp] += 1
        return {
            "total_mutations": len(mutations),
            "unique_genes": len({str(m["gene"]) for m in mutations}),
            "unique_samples": len({str(m["sample_id"]) for m in mutations}),
            "impact_distribution": dist,
        }

    def fetch_external_data(self, url: str) -> Any:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            raise Exception("Failed to fetch data")
        return r.json()

    def validate_mutation_format(self, mutation: Dict[str, Any]) -> bool:
        try:
            self._validate_record(mutation, strict=False)
            if str(mutation.get("impact", "")).lower() not in _VALID_IMPACT:
                return False
        except ValueError:
            return False
        return True

    def convert_to_dataframe(self, mutations: List[Dict[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(mutations)

    def export_mutations(self, mutations: List[Dict[str, Any]], path: Any) -> None:
        p = Path(path)
        p.write_text(json.dumps(mutations, indent=2), encoding="utf-8")

    def import_mutations(self, path: Any) -> List[Dict[str, Any]]:
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Invalid input")
        return data

    def compare_mutations(
        self, first: List[Dict[str, Any]], second: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        k1 = {_mutation_key(m) for m in first}
        k2 = {_mutation_key(m) for m in second}
        common_keys = k1 & k2
        only1 = k1 - k2
        only2 = k2 - k1
        common = [m for m in first if _mutation_key(m) in common_keys]
        u1 = [m for m in first if _mutation_key(m) in only1]
        u2 = [m for m in second if _mutation_key(m) in only2]
        return {
            "common_mutations": common,
            "unique_to_first": u1,
            "unique_to_second": u2,
        }

    def analyze_mutation_patterns(
        self, mutations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        genes = [str(m["gene"]) for m in mutations]
        top = Counter(genes).most_common(5)
        chroms = Counter(str(m["chromosome"]) for m in mutations)
        return {
            "hotspot_genes": [{"gene": g, "count": c} for g, c in top],
            "mutation_types": {},
            "chromosome_distribution": dict(chroms),
        }

    def predict_mutation_impact(self, mutation: Dict[str, Any]) -> str:
        if "impact" in mutation and str(mutation["impact"]).lower() in _VALID_IMPACT:
            return str(mutation["impact"]).lower()
        return "unknown"

    def get_mutation_context(self, mutation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "gene_function": f"annotated:{mutation.get('gene', '')}",
            "protein_domain": "unknown",
            "conservation_score": 0.0,
        }

    def analyze_mutation_cooccurrence(
        self, mutations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        by_sample: Dict[str, List[str]] = {}
        for m in mutations:
            sid = str(m["sample_id"])
            by_sample.setdefault(sid, []).append(str(m["gene"]))
        pairs = []
        for genes in by_sample.values():
            if len(genes) > 1:
                for i, a in enumerate(genes):
                    for b in genes[i + 1 :]:
                        pairs.append(tuple(sorted((a, b))))
        return {"cooccurring_pairs": pairs, "cooccurrence_matrix": {}}

    def generate_mutation_report(
        self, mutations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        summary = self.get_mutation_summary(mutations)
        return {
            "summary": summary,
            "detailed_analysis": self.analyze_mutation_patterns(mutations),
            "recommendations": [],
        }

    def analyze_mutation_network(
        self, mutations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        nodes = list({str(m["gene"]) for m in mutations})
        edges = []
        co = self.analyze_mutation_cooccurrence(mutations)["cooccurring_pairs"]
        for a, b in co:
            edges.append({"source": a, "target": b})
        return {
            "nodes": [{"id": n} for n in nodes],
            "edges": edges,
            "network_metrics": {"n_nodes": len(nodes), "n_edges": len(edges)},
        }

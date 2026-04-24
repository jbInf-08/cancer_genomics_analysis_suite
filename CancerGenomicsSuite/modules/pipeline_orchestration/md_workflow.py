"""
Molecular dynamics workflow: resolve structure inputs (RCSB PDB, AlphaFold,
local files) and run GROMACS vacuum energy minimization.

Error reporting uses structured fields (``error_detail``) for UI surfaces.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

import requests

from CancerGenomicsSuite.modules.gromacs_integration.gromacs_client import GROMACSClient

logger = logging.getLogger(__name__)

RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
ALPHAFOLD_PDB_URL = (
    "https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v4.pdb"
)
UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024


def _http_download(
    url: str,
    dest: Path,
    *,
    timeout: int,
    label: str,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Stream download with size cap. Returns (ok, error_detail_or_none).
    """
    try:
        req = urllib_request.Request(
            url,
            headers={"User-Agent": "CancerGenomicsAnalysisSuite/1.0 (MD workflow)"},
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            total = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as out:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        dest.unlink(missing_ok=True)
                        return False, {
                            "error_kind": "download_too_large",
                            "user_message": (
                                f"{label}: download exceeded {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MiB; "
                                "aborting for safety."
                            ),
                            "url": url,
                        }
                    out.write(chunk)
        if dest.stat().st_size < 50:
            dest.unlink(missing_ok=True)
            return False, {
                "error_kind": "empty_or_tiny_file",
                "user_message": f"{label}: file was empty or too small; check the URL or ID.",
                "url": url,
            }
    except urllib_error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            pass
        return False, {
            "error_kind": "http_error",
            "http_status": e.code,
            "user_message": (
                f"{label}: HTTP {e.code} from remote server. "
                + ("Not found — check PDB ID or UniProt accession." if e.code == 404 else str(e.reason))
            ),
            "url": url,
            "response_snippet": body,
        }
    except urllib_error.URLError as e:
        return False, {
            "error_kind": "network",
            "user_message": f"{label}: network error — {e.reason or e}",
            "url": url,
        }
    except TimeoutError:
        return False, {
            "error_kind": "timeout",
            "user_message": f"{label}: timed out after {timeout}s.",
            "url": url,
        }
    except Exception as e:
        logger.exception("%s download failed", label)
        return False, {
            "error_kind": "unknown",
            "user_message": f"{label}: {e}",
            "url": url,
        }
    return True, None


def download_pdb_rcsb(pdb_id: str, dest_dir: Path, timeout: int = 90) -> Tuple[Path, Optional[Dict[str, Any]]]:
    pid = pdb_id.strip().upper()
    if len(pid) != 4 or not re.match(r"^[0-9A-Z]{4}$", pid):
        raise ValueError(
            "PDB ID must be four alphanumeric characters (typical RCSB entry id, e.g. 1CRN)."
        )
    url = RCSB_PDB_URL.format(pdb_id=pid)
    dest = dest_dir / f"{pid}.pdb"
    ok, err = _http_download(url, dest, timeout=timeout, label="RCSB PDB")
    if not ok:
        return dest, err
    return dest, None


def download_alphafold_model(uniprot: str, dest_dir: Path, timeout: int = 120) -> Tuple[Path, Optional[Dict[str, Any]]]:
    acc = uniprot.strip().upper()
    if not re.match(r"^[A-NR-Z0-9]{6,15}$", acc):
        raise ValueError("UniProt accession looks invalid (expected 6–15 letter/digit characters).")
    url = ALPHAFOLD_PDB_URL.format(uniprot=acc)
    dest = dest_dir / f"AF-{acc}-F1-model_v4.pdb"
    ok, err = _http_download(url, dest, timeout=timeout, label="AlphaFold DB")
    if not ok:
        return dest, err
    return dest, None


def resolve_uniprot_from_gene_symbol(
    gene_symbol: str,
    organism_id: str = "9606",
    timeout: int = 30,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Best-effort UniProt accession (Swiss-Prot/TrEMBL) for a gene symbol.
    """
    sym = (gene_symbol or "").strip()
    if not sym:
        return None, {
            "error_kind": "missing_gene",
            "user_message": "Gene symbol is empty; cannot query UniProt.",
        }
    query = f"(gene_exact:{sym}) AND (organism_id:{organism_id})"
    try:
        r = requests.get(
            UNIPROT_SEARCH,
            params={"query": query, "format": "json", "size": 5},
            headers={"User-Agent": "CancerGenomicsAnalysisSuite/1.0"},
            timeout=timeout,
        )
        if not r.ok:
            return None, {
                "error_kind": "uniprot_http",
                "http_status": r.status_code,
                "user_message": f"UniProt search failed (HTTP {r.status_code}).",
                "response_snippet": r.text[:800],
            }
        payload = r.json()
        results = payload.get("results") or []
        if not results:
            return None, {
                "error_kind": "uniprot_not_found",
                "user_message": (
                    f"No UniProt entry found for gene symbol {sym!r} (organism {organism_id}). "
                    "Try supplying a UniProt accession explicitly."
                ),
            }
        acc = results[0].get("primaryAccession")
        if not acc:
            return None, {
                "error_kind": "uniprot_shape",
                "user_message": "UniProt response missing primaryAccession.",
            }
        return str(acc), None
    except requests.Timeout:
        return None, {
            "error_kind": "uniprot_timeout",
            "user_message": f"UniProt search timed out after {timeout}s.",
        }
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        return None, {
            "error_kind": "uniprot_error",
            "user_message": f"UniProt search error: {e}",
        }


class MolecularDynamicsWorkflow:
    """
    High-level MD workflow: fetch a structure (RCSB, AlphaFold, or local PDB),
    then run vacuum steepest-descent energy minimization when GROMACS is available.
    """

    def __init__(self, work_root: Optional[str] = None) -> None:
        root = Path(work_root) if work_root else Path.cwd() / "md_workflow_work"
        self.work_root = root
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._client = GROMACSClient()

    def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute MD preparation / minimization from config.

        Structure resolution (first match wins):
            1. ``pdb_path`` — local file
            2. ``pdb_id`` — RCSB four-letter code
            3. ``alphafold_uniprot`` — UniProt accession for AlphaFold DB model_v4 PDB
            4. ``alphafold_gene_symbol`` (+ optional ``alphafold_organism_id``, default 9606)
            5. ``tpr_path`` — pre-built GROMACS run input

        Other keys:
            ``gene_symbol``, ``mutation_summary`` — metadata echoed in results
            ``keep_workdir`` — always retain ``work_dir`` path in the result
            ``rcsb_timeout``, ``alphafold_timeout`` — override download timeouts (seconds)

        Returns:
            Dict including ``success``, ``work_dir``, ``pdb_file``, ``structure_source``,
            ``error``, optional ``error_detail`` (for dashboards), and GROMACS fields.
        """
        cfg = dict(config or {})
        meta: Dict[str, Any] = {
            "gene_symbol": cfg.get("gene_symbol"),
            "mutation_summary": cfg.get("mutation_summary"),
        }
        rcsb_timeout = int(cfg.get("rcsb_timeout") or 90)
        af_timeout = int(cfg.get("alphafold_timeout") or 120)

        if cfg.get("tpr_path"):
            tpr = Path(cfg["tpr_path"])
            if not tpr.is_file():
                return {
                    "success": False,
                    "error": f"TPR not found: {tpr}",
                    "error_detail": {"error_kind": "missing_file", "path": str(tpr)},
                    **meta,
                }
            run_dir = Path(tempfile.mkdtemp(prefix="md_tpr_", dir=self.work_root))
            shutil.copy2(tpr, run_dir / "simulation.tpr")
            sim = self._client.run_simulation({"tpr": str(run_dir / "simulation.tpr")}, {})
            sim.update({"work_dir": str(run_dir), "structure_source": "tpr", **meta})
            return sim

        pdb_path = cfg.get("pdb_path")
        pdb_id = cfg.get("pdb_id")
        af_up = cfg.get("alphafold_uniprot")
        af_gene = cfg.get("alphafold_gene_symbol")
        organism = str(cfg.get("alphafold_organism_id") or "9606")

        if not any([pdb_path, pdb_id, af_up, af_gene]):
            return {
                "success": False,
                "error": (
                    "Provide one of: pdb_path, pdb_id, alphafold_uniprot, "
                    "alphafold_gene_symbol, or tpr_path"
                ),
                "error_detail": {"error_kind": "missing_inputs"},
                **meta,
            }

        run_dir = Path(tempfile.mkdtemp(prefix="md_run_", dir=self.work_root))
        keep = bool(cfg.get("keep_workdir"))
        pdb_file: Optional[Path] = None
        structure_source = ""

        try:
            if pdb_path:
                src = Path(pdb_path)
                if not src.is_file():
                    return {
                        "success": False,
                        "error": f"PDB file not found: {pdb_path}",
                        "error_detail": {"error_kind": "missing_file", "path": str(pdb_path)},
                        "work_dir": str(run_dir),
                        **meta,
                    }
                pdb_file = run_dir / "input.pdb"
                shutil.copy2(src, pdb_file)
                structure_source = "local_pdb"
            elif pdb_id:
                try:
                    pdb_file, dl_err = download_pdb_rcsb(str(pdb_id), run_dir, timeout=rcsb_timeout)
                except ValueError as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_detail": {"error_kind": "invalid_pdb_id"},
                        "work_dir": str(run_dir),
                        **meta,
                    }
                if dl_err:
                    return {
                        "success": False,
                        "error": dl_err.get("user_message", "RCSB download failed"),
                        "error_detail": dl_err,
                        "work_dir": str(run_dir),
                        "structure_source": "rcsb",
                        **meta,
                    }
                structure_source = "rcsb"
            elif af_up:
                try:
                    pdb_file, dl_err = download_alphafold_model(str(af_up), run_dir, timeout=af_timeout)
                except ValueError as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_detail": {"error_kind": "invalid_uniprot"},
                        "work_dir": str(run_dir),
                        **meta,
                    }
                if dl_err:
                    return {
                        "success": False,
                        "error": dl_err.get("user_message", "AlphaFold download failed"),
                        "error_detail": dl_err,
                        "work_dir": str(run_dir),
                        "structure_source": "alphafold",
                        **meta,
                    }
                structure_source = "alphafold"
            else:
                acc, uerr = resolve_uniprot_from_gene_symbol(str(af_gene), organism_id=organism)
                if uerr or not acc:
                    return {
                        "success": False,
                        "error": (uerr or {}).get("user_message", "UniProt resolution failed"),
                        "error_detail": uerr or {"error_kind": "uniprot_failed"},
                        "work_dir": str(run_dir),
                        **meta,
                    }
                pdb_file, dl_err = download_alphafold_model(acc, run_dir, timeout=af_timeout)
                if dl_err:
                    return {
                        "success": False,
                        "error": dl_err.get("user_message", "AlphaFold download failed"),
                        "error_detail": dl_err,
                        "work_dir": str(run_dir),
                        "structure_source": "alphafold",
                        "resolved_uniprot": acc,
                        **meta,
                    }
                structure_source = "alphafold"
                meta["resolved_uniprot"] = acc

            assert pdb_file is not None

            if not self._client.is_available():
                return {
                    "success": False,
                    "error": "GROMACS (gmx) not found on PATH",
                    "pdb_file": str(pdb_file),
                    "work_dir": str(run_dir),
                    "gromacs_version": self._client.get_version(),
                    "structure_source": structure_source,
                    "hint": (
                        "Install GROMACS and ensure `gmx` is on PATH, or pass tpr_path with a "
                        "pre-built .tpr."
                    ),
                    **meta,
                }

            em = self._client.run_energy_minimization_from_pdb(str(pdb_file), str(run_dir))
            em["pdb_file"] = str(pdb_file)
            em["gromacs_version"] = self._client.get_version()
            em["structure_source"] = structure_source
            em.update(meta)
            em["work_dir"] = str(run_dir)
            if not keep and em.get("success"):
                pass
            return em
        except Exception as e:
            logger.exception("MD workflow failed")
            return {
                "success": False,
                "error": str(e),
                "error_detail": {"error_kind": "exception", "exception_type": type(e).__name__},
                "work_dir": str(run_dir),
                **meta,
            }

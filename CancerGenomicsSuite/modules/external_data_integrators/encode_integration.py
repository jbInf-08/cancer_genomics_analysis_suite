import requests
from typing import Any, Dict, List


def query_encode(term: str, assay: str = "ChIP-seq", limit: int = 5) -> List[Dict[str, Any]]:
    """Query ENCODE for datasets.

    Docs: https://www.encodeproject.org/help/rest-api/
    """
    url = "https://www.encodeproject.org/search/"
    params = {
        "searchTerm": term,
        "type": "Experiment",
        "assay_title": assay,
        "limit": limit,
        "format": "json",
    }
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("@graph", [])


def fetch_file_metadata(file_accession: str) -> Dict[str, Any]:
    """Fetch ENCODE file metadata by accession."""
    url = f"https://www.encodeproject.org/files/{file_accession}/?format=json"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


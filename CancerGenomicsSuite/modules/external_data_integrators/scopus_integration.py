import os
from typing import Any, Dict, List

import requests


SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")


def search_scopus(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """Query Scopus articles by keyword.

    Requires SCOPUS_API_KEY in environment.
    """
    headers = {
        "X-ELS-APIKey": SCOPUS_API_KEY or "",
        "Accept": "application/json",
    }
    params = {
        "query": query,
        "count": count,
    }
    url = "https://api.elsevier.com/content/search/scopus"
    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("search-results", {}).get("entry", [])


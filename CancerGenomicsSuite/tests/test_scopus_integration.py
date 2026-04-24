from unittest import mock

from modules.external_data_integrators.scopus_integration import search_scopus


def test_search_scopus_returns_entries():
    fake = {"search-results": {"entry": [{"dc:title": "Paper A"}]}}
    with mock.patch("requests.get") as mget:
        mget.return_value.json.return_value = fake
        mget.return_value.raise_for_status.return_value = None
        entries = search_scopus("TP53", count=1)
        assert entries == fake["search-results"]["entry"]



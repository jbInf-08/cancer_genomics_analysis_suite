from unittest import mock

from modules.external_data_integrators.encode_integration import query_encode, fetch_file_metadata


def test_query_encode_parses_graph():
    fake = {"@graph": [{"accession": "ENCSR000AAA"}]}
    with mock.patch("requests.get") as mget:
        mget.return_value.json.return_value = fake
        mget.return_value.raise_for_status.return_value = None
        data = query_encode("TP53", limit=1)
        assert data == fake["@graph"]


def test_fetch_file_metadata_returns_json():
    fake = {"status": "released"}
    with mock.patch("requests.get") as mget:
        mget.return_value.json.return_value = fake
        mget.return_value.raise_for_status.return_value = None
        res = fetch_file_metadata("ENCFF000AAA")
        assert res == fake



"""sync_gene_variants must return what it synced, not the whole local table.

The function searched ClinVar, synced each hit, computed the ids that succeeded
-- and then returned ``get_local_variants(gene_symbol)``, which is every row
stored for that gene. The computed ids went unused, so:

* variants already stored from an earlier run came back as though this call had
  synced them, and
* a call in which every single sync failed still returned a full list, which
  reads as success at the call site.

These tests drive the function through a stub client, so they need no network
and no sqlite database -- ``sync_client`` is an injectable parameter.
"""

from __future__ import annotations

from CancerGenomicsSuite.api_integrations.clinvar_sync import (
    ClinVarVariant,
    sync_gene_variants,
)


def make_variant(variant_id: str, gene_symbol: str = "BRCA1") -> ClinVarVariant:
    """A ClinVarVariant with only the two fields these tests care about set."""
    return ClinVarVariant(
        variant_id=variant_id,
        gene_symbol=gene_symbol,
        variant_name=f"variant-{variant_id}",
        chromosome="17",
        position=43000000,
        ref_allele="A",
        alt_allele="G",
        clinical_significance="Pathogenic",
        pathogenicity="Pathogenic",
        review_status="reviewed by expert panel",
        last_evaluated=None,
        condition="Hereditary breast and ovarian cancer",
        phenotype="",
        inheritance="autosomal dominant",
        age_of_onset="",
        prevalence="",
        penetrance="",
        modifiers="",
        evidence=[],
        submissions=[],
    )


class StubSync:
    """Stands in for ClinVarSync, recording calls and returning canned data."""

    def __init__(self, search_ids, sync_results, local_variants):
        self._search_ids = search_ids
        self._sync_results = sync_results
        self._local_variants = local_variants
        self.searched_queries: list[str] = []
        self.batch_called_with: list[list[str]] = []

    def search_variants(self, query):
        self.searched_queries.append(query)
        return self._search_ids

    def batch_sync_variants(self, variant_ids):
        self.batch_called_with.append(list(variant_ids))
        return self._sync_results

    def get_local_variants(self, gene_symbol=None):
        return list(self._local_variants)


def test_only_successfully_synced_variants_are_returned():
    """Two of three synced; the stored-but-failed one must not come back."""
    client = StubSync(
        search_ids=["1", "2", "3"],
        sync_results={"1": True, "2": False, "3": True},
        # The local table holds all three -- "2" from some earlier run.
        local_variants=[make_variant("1"), make_variant("2"), make_variant("3")],
    )

    result = sync_gene_variants("BRCA1", sync_client=client)

    assert [v.variant_id for v in result] == ["1", "3"]


def test_variants_stored_locally_but_not_touched_are_excluded():
    """A pre-existing row for the gene is not passed off as freshly synced."""
    client = StubSync(
        search_ids=["1"],
        sync_results={"1": True},
        local_variants=[make_variant("1"), make_variant("999")],
    )

    result = sync_gene_variants("BRCA1", sync_client=client)

    assert [v.variant_id for v in result] == ["1"]


def test_total_sync_failure_returns_empty_rather_than_stale_rows():
    """The case that made the old behaviour dangerous.

    Every sync failed, yet the local table still had rows, so the caller
    received a populated list and no indication anything had gone wrong.
    """
    client = StubSync(
        search_ids=["1", "2"],
        sync_results={"1": False, "2": False},
        local_variants=[make_variant("1"), make_variant("2")],
    )

    assert sync_gene_variants("BRCA1", sync_client=client) == []


def test_no_search_hits_returns_empty():
    client = StubSync(search_ids=[], sync_results={}, local_variants=[])
    assert sync_gene_variants("NOSUCHGENE", sync_client=client) == []


def test_synced_id_missing_from_local_store_is_skipped():
    """Reported success but nothing stored -- return what is actually there."""
    client = StubSync(
        search_ids=["1", "2"],
        sync_results={"1": True, "2": True},
        local_variants=[make_variant("1")],
    )

    assert [v.variant_id for v in sync_gene_variants("BRCA1", client)] == ["1"]


def test_search_query_and_batch_input_are_unchanged():
    """Pin the surrounding behaviour the filtering must not disturb."""
    client = StubSync(
        search_ids=["1", "2"],
        sync_results={"1": True, "2": True},
        local_variants=[make_variant("1"), make_variant("2")],
    )

    sync_gene_variants("TP53", sync_client=client)

    assert client.searched_queries == ["TP53[gene]"]
    assert client.batch_called_with == [["1", "2"]]


def test_returned_order_follows_the_local_store():
    """Filtering preserves get_local_variants' ordering, not the sync order."""
    client = StubSync(
        search_ids=["3", "1", "2"],
        sync_results={"3": True, "1": True, "2": True},
        local_variants=[make_variant("1"), make_variant("2"), make_variant("3")],
    )

    result = sync_gene_variants("BRCA1", sync_client=client)

    assert [v.variant_id for v in result] == ["1", "2", "3"]

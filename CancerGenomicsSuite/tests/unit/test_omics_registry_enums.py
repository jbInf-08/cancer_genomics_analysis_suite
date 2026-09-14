"""The omics registry must be constructible, and it names its own enum members.

``omics_registry`` builds the full field registry at import time -- the module
ends with ``omics_registry = OmicsFieldRegistry()``. So any name it gets wrong in
an ``analysis_types`` list is not a latent bug: it raises AttributeError before
the module finishes loading, and every importer goes down with it.

That is what happened. Seven entries referenced ``OmicsAnalysisType.STRUCTURE``,
``.KINETIC`` and ``.DOSE_RESPONSE``, none of which existed on the enum. Importing
the whole suite showed 19 modules failing on this one cause alone.

These tests fail loudly rather than subtly if a member is referenced without
being declared.
"""

from __future__ import annotations

from CancerGenomicsSuite.modules.omics_definitions.omics_registry import (
    OmicsAnalysisType,
    OmicsDataType,
    OmicsFieldRegistry,
)


def test_registry_can_be_constructed():
    """The bare construction is the thing that used to raise at import."""
    registry = OmicsFieldRegistry()
    assert registry.fields, "registry built no fields"


def test_every_analysis_type_is_a_real_enum_member():
    """Guards the whole class of bug, not just the three names that were wrong."""
    registry = OmicsFieldRegistry()
    valid = set(OmicsAnalysisType)
    offenders = {
        name: [a for a in field.analysis_types if a not in valid]
        for name, field in registry.fields.items()
        if any(a not in valid for a in field.analysis_types)
    }
    assert not offenders, f"fields referencing unknown analysis types: {offenders}"


def test_every_data_type_is_a_real_enum_member():
    registry = OmicsFieldRegistry()
    valid = set(OmicsDataType)
    offenders = {
        name: field.data_type
        for name, field in registry.fields.items()
        if field.data_type not in valid
    }
    assert not offenders, f"fields with unknown data types: {offenders}"


def test_the_three_previously_missing_members_exist():
    for member in ("STRUCTURE", "KINETIC", "DOSE_RESPONSE"):
        assert hasattr(OmicsAnalysisType, member), f"OmicsAnalysisType.{member} missing"


def test_analysis_types_are_distinct_from_data_types():
    """STRUCTURE and KINETIC exist on both enums and mean different things.

    OmicsDataType says what a field measures; OmicsAnalysisType says what is
    done with it. proteomics is ABUNDANCE data analysed structurally, so the
    two must not be collapsed into one another.
    """
    registry = OmicsFieldRegistry()
    proteomics = registry.fields["proteomics"]
    assert proteomics.data_type is OmicsDataType.ABUNDANCE
    assert OmicsAnalysisType.STRUCTURE in proteomics.analysis_types
    assert OmicsAnalysisType.STRUCTURE is not OmicsDataType.STRUCTURE


def test_the_fields_that_needed_the_new_members_carry_them():
    registry = OmicsFieldRegistry()
    expected = {
        "proteomics": OmicsAnalysisType.STRUCTURE,
        "glycomics": OmicsAnalysisType.STRUCTURE,
        "degradomics": OmicsAnalysisType.KINETIC,
        "fluxomics": OmicsAnalysisType.KINETIC,
        "kinomics": OmicsAnalysisType.KINETIC,
        "toxicogenomics": OmicsAnalysisType.DOSE_RESPONSE,
        "pharmacoproteomics": OmicsAnalysisType.DOSE_RESPONSE,
    }
    for field_name, analysis in expected.items():
        assert field_name in registry.fields, f"{field_name} missing from registry"
        assert analysis in registry.fields[field_name].analysis_types


def test_enum_values_are_unique():
    values = [m.value for m in OmicsAnalysisType]
    assert len(values) == len(set(values)), f"duplicate values: {values}"

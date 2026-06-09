"""Unit tests for apps/api/standards/loader.py — Phase 5c.

These tests validate that:
1. All 20 bundled schemas are registered on startup.
2. Registration is idempotent (calling register_all() twice is safe).
3. Catalog listing includes all bundled standards.
4. Each schema carries correct metadata (type=standard, format_id, status=approved, version).
5. Deterministic IDs are stable across calls.
6. Individual field-level correctness (required/optional, paths).
7. Bundle schemas (FHIR_R4, OMOP_CDM_5_4) are created by register_bundles().
8. Bundles are idempotent and carry correct composite field counts.
"""

from __future__ import annotations

import pytest

from apps.api.standards.loader import (
    register_all,
    register_bundles,
    _build_canonical,
    _field_id,
    _schema_id,
)
from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import CatalogService
from packages.catalog.models.schema_descriptor import ApprovalStatus, SchemaType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_catalog() -> CatalogService:
    """A brand-new CatalogService with no pre-registered schemas."""
    registry = AdapterRegistry()
    register_defaults(registry)
    return CatalogService(adapter_registry=registry)


# ---------------------------------------------------------------------------
# Expected constants
# ---------------------------------------------------------------------------

_EXPECTED_SCHEMAS = [
    ("OMOP_CARE_SITE",              "omop_cdm",      "5.4"),
    ("OMOP_PERSON",                 "omop_cdm",      "5.4"),
    ("OMOP_PROCEDURE_OCCURRENCE",   "omop_cdm",      "5.4"),
    ("OMOP_VISIT_OCCURRENCE",       "omop_cdm",      "5.4"),
    ("OMOP_CONDITION_OCCURRENCE",   "omop_cdm",      "5.4"),
    ("OMOP_DRUG_EXPOSURE",          "omop_cdm",      "5.4"),
    ("OMOP_MEASUREMENT",            "omop_cdm",      "5.4"),
    ("OMOP_OBSERVATION",            "omop_cdm",      "5.4"),
    ("OMOP_DEATH",                  "omop_cdm",      "5.4"),
    ("OMOP_PROVIDER",               "omop_cdm",      "5.4"),
    ("OMOP_LOCATION",               "omop_cdm",      "5.4"),
    ("FHIR_Encounter",              "fhir_profile",  "R4"),
    ("FHIR_Organization",           "fhir_profile",  "R4"),
    ("FHIR_Patient",                "fhir_profile",  "R4"),
    ("FHIR_Condition",              "fhir_profile",  "R4"),
    ("FHIR_Observation",            "fhir_profile",  "R4"),
    ("FHIR_Procedure",              "fhir_profile",  "R4"),
    ("FHIR_Practitioner",           "fhir_profile",  "R4"),
    ("FHIR_PractitionerRole",       "fhir_profile",  "R4"),
    ("FHIR_Location",               "fhir_profile",  "R4"),
]

_TOTAL = len(_EXPECTED_SCHEMAS)  # 20


# ---------------------------------------------------------------------------
# 1. All schemas are registered
# ---------------------------------------------------------------------------

def test_register_all_returns_seven(fresh_catalog):
    count = register_all(fresh_catalog)
    assert count == _TOTAL, f"Expected {_TOTAL} registrations, got {count}"


def test_all_schemas_present_in_catalog(fresh_catalog):
    register_all(fresh_catalog)
    entries = fresh_catalog.list_entries()
    names = {e.descriptor.name for e in entries}
    for schema_name, _, _ in _EXPECTED_SCHEMAS:
        assert schema_name in names, f"Schema {schema_name!r} missing from catalog"


# ---------------------------------------------------------------------------
# 2. Idempotency
# ---------------------------------------------------------------------------

def test_register_all_is_idempotent(fresh_catalog):
    first = register_all(fresh_catalog)
    second = register_all(fresh_catalog)
    assert first == _TOTAL
    assert second == 0, "Second call should register nothing (all already present)"


def test_idempotent_does_not_duplicate_entries(fresh_catalog):
    register_all(fresh_catalog)
    register_all(fresh_catalog)
    entries = fresh_catalog.list_entries()
    assert len(entries) == _TOTAL


# ---------------------------------------------------------------------------
# 3. Correct metadata on every schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_type_is_standard(fresh_catalog, schema_name, format_id, version):
    register_all(fresh_catalog)
    entries = fresh_catalog.list_entries(schema_type=SchemaType.STANDARD)
    names = {e.descriptor.name for e in entries}
    assert schema_name in names


@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_approval_status_is_approved(fresh_catalog, schema_name, format_id, version):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == schema_name
    )
    assert entry.descriptor.approval_status == ApprovalStatus.APPROVED


@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_format_id(fresh_catalog, schema_name, format_id, version):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == schema_name
    )
    assert entry.descriptor.format_id == format_id


@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_version_label(fresh_catalog, schema_name, format_id, version):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == schema_name
    )
    latest = entry.get_latest_version()
    assert latest is not None
    assert latest.version_label == version


@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_source_tag_is_bundled(fresh_catalog, schema_name, format_id, version):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == schema_name
    )
    assert entry.descriptor.metadata_tags.get("source") == "bundled"


# ---------------------------------------------------------------------------
# 4. Filtering by type and format_id
# ---------------------------------------------------------------------------

def test_filter_by_type_standard(fresh_catalog):
    register_all(fresh_catalog)
    standard_entries = fresh_catalog.list_entries(schema_type=SchemaType.STANDARD)
    assert len(standard_entries) == _TOTAL


def test_filter_by_format_omop(fresh_catalog):
    register_all(fresh_catalog)
    omop_entries = fresh_catalog.list_entries(format_id="omop_cdm")
    assert len(omop_entries) == 11  # 4 original + CONDITION_OCCURRENCE, DRUG_EXPOSURE, MEASUREMENT, OBSERVATION, DEATH, PROVIDER, LOCATION


def test_filter_by_format_fhir(fresh_catalog):
    register_all(fresh_catalog)
    fhir_entries = fresh_catalog.list_entries(format_id="fhir_profile")
    assert len(fhir_entries) == 9  # 3 original + Condition, Observation, Procedure, Practitioner, PractitionerRole, Location


def test_filter_by_approved_status(fresh_catalog):
    register_all(fresh_catalog)
    approved = fresh_catalog.list_entries(approval_status=ApprovalStatus.APPROVED)
    assert len(approved) == _TOTAL


# ---------------------------------------------------------------------------
# 5. Deterministic IDs
# ---------------------------------------------------------------------------

def test_schema_ids_are_deterministic(fresh_catalog):
    register_all(fresh_catalog)
    # _build_canonical for OMOP_PERSON should always yield the same id
    bundle = {
        "schema_name": "OMOP_PERSON",
        "format_id": "omop_cdm",
        "version": "5.4",
        "fields": [],
    }
    canonical = _build_canonical(bundle)
    expected_id = _schema_id("omop_cdm", "OMOP_PERSON", "5.4")
    assert canonical.id == expected_id


def test_field_ids_are_deterministic():
    id1 = _field_id("omop_cdm", "OMOP_PERSON", "5.4", "person.person_id")
    id2 = _field_id("omop_cdm", "OMOP_PERSON", "5.4", "person.person_id")
    assert id1 == id2


def test_different_paths_yield_different_ids():
    id1 = _field_id("omop_cdm", "OMOP_PERSON", "5.4", "person.person_id")
    id2 = _field_id("omop_cdm", "OMOP_PERSON", "5.4", "person.gender_concept_id")
    assert id1 != id2


# ---------------------------------------------------------------------------
# 6. Field-level correctness
# ---------------------------------------------------------------------------

def test_omop_person_has_required_person_id(fresh_catalog):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == "OMOP_PERSON"
    )
    version = entry.get_latest_version()
    schema = version.resolve_canonical()
    person_id_field = next(
        (f for f in schema.fields if f.path == "person.person_id"), None
    )
    assert person_id_field is not None
    assert person_id_field.constraints.required is True


def test_omop_person_optional_field_is_not_required(fresh_catalog):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == "OMOP_PERSON"
    )
    version = entry.get_latest_version()
    schema = version.resolve_canonical()
    month_field = next(
        (f for f in schema.fields if f.path == "person.month_of_birth"), None
    )
    assert month_field is not None
    assert month_field.constraints.required is False


def test_fhir_encounter_required_fields(fresh_catalog):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == "FHIR_Encounter"
    )
    version = entry.get_latest_version()
    schema = version.resolve_canonical()
    required_paths = {
        f.path for f in schema.fields if f.constraints.required
    }
    assert "Encounter.status" in required_paths
    assert "Encounter.class" in required_paths
    assert "Encounter.subject" in required_paths


def test_fhir_patient_has_expected_field_count(fresh_catalog):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == "FHIR_Patient"
    )
    version = entry.get_latest_version()
    schema = version.resolve_canonical()
    assert len(schema.fields) >= 10


def test_omop_care_site_field_count(fresh_catalog):
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == "OMOP_CARE_SITE"
    )
    version = entry.get_latest_version()
    schema = version.resolve_canonical()
    assert len(schema.fields) == 6


# ---------------------------------------------------------------------------
# 7. Schema snapshot is resolvable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_name,format_id,version", _EXPECTED_SCHEMAS)
def test_schema_snapshot_resolvable(fresh_catalog, schema_name, format_id, version):
    """Every registered version can be deserialized back to a CanonicalSchema."""
    register_all(fresh_catalog)
    entry = next(
        e for e in fresh_catalog.list_entries()
        if e.descriptor.name == schema_name
    )
    latest = entry.get_latest_version()
    canonical = latest.resolve_canonical()
    assert canonical.name == schema_name
    assert canonical.version == version
    assert len(canonical.fields) > 0


# ---------------------------------------------------------------------------
# 8. Bundle schemas (register_bundles)
# ---------------------------------------------------------------------------

@pytest.fixture()
def loaded_catalog(fresh_catalog) -> CatalogService:
    """Catalog with individual schemas + bundles — mirrors API startup."""
    register_all(fresh_catalog)
    register_bundles(fresh_catalog)
    return fresh_catalog


def test_register_bundles_returns_two(fresh_catalog):
    register_all(fresh_catalog)
    count = register_bundles(fresh_catalog)
    assert count == 2  # FHIR_R4 and OMOP_CDM_5_4


def test_bundles_present_in_catalog(loaded_catalog):
    names = {e.descriptor.name for e in loaded_catalog.list_entries()}
    assert "FHIR_R4" in names
    assert "OMOP_CDM_5_4" in names


def test_register_bundles_is_idempotent(fresh_catalog):
    register_all(fresh_catalog)
    first = register_bundles(fresh_catalog)
    second = register_bundles(fresh_catalog)
    assert first == 2
    assert second == 0


def test_idempotent_bundles_no_duplicates(loaded_catalog):
    register_bundles(loaded_catalog)  # second call
    bundle_entries = [
        e for e in loaded_catalog.list_entries()
        if e.descriptor.metadata_tags.get("bundle") == "true"
    ]
    assert len(bundle_entries) == 2


def test_fhir_bundle_tag(loaded_catalog):
    entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == "FHIR_R4")
    assert entry.descriptor.metadata_tags.get("bundle") == "true"
    assert entry.descriptor.metadata_tags.get("standard") == "FHIR"
    assert entry.descriptor.metadata_tags.get("standard_version") == "R4"


def test_omop_bundle_tag(loaded_catalog):
    entry = next(
        e for e in loaded_catalog.list_entries() if e.descriptor.name == "OMOP_CDM_5_4"
    )
    assert entry.descriptor.metadata_tags.get("bundle") == "true"
    assert entry.descriptor.metadata_tags.get("standard") == "OMOP CDM"
    assert entry.descriptor.metadata_tags.get("standard_version") == "5.4"


def test_bundle_approval_status_approved(loaded_catalog):
    for name in ("FHIR_R4", "OMOP_CDM_5_4"):
        entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == name)
        assert entry.descriptor.approval_status == ApprovalStatus.APPROVED


def test_fhir_bundle_contains_patient_fields(loaded_catalog):
    entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == "FHIR_R4")
    canonical = entry.get_latest_version().resolve_canonical()
    paths = {f.path for f in canonical.fields}
    assert "Patient.id" in paths
    assert "Patient.birthDate" in paths


def test_fhir_bundle_contains_organization_fields(loaded_catalog):
    entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == "FHIR_R4")
    canonical = entry.get_latest_version().resolve_canonical()
    paths = {f.path for f in canonical.fields}
    assert "Organization.id" in paths
    assert "Organization.name" in paths


def test_fhir_bundle_contains_encounter_fields(loaded_catalog):
    entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == "FHIR_R4")
    canonical = entry.get_latest_version().resolve_canonical()
    paths = {f.path for f in canonical.fields}
    assert "Encounter.status" in paths
    assert "Encounter.subject" in paths


def test_omop_bundle_contains_person_fields(loaded_catalog):
    entry = next(
        e for e in loaded_catalog.list_entries() if e.descriptor.name == "OMOP_CDM_5_4"
    )
    canonical = entry.get_latest_version().resolve_canonical()
    paths = {f.path for f in canonical.fields}
    assert "person.person_id" in paths
    assert "person.year_of_birth" in paths


def test_omop_bundle_contains_visit_occurrence_fields(loaded_catalog):
    entry = next(
        e for e in loaded_catalog.list_entries() if e.descriptor.name == "OMOP_CDM_5_4"
    )
    canonical = entry.get_latest_version().resolve_canonical()
    paths = {f.path for f in canonical.fields}
    assert "visit_occurrence.visit_occurrence_id" in paths
    assert "visit_occurrence.visit_start_date" in paths


def test_fhir_bundle_total_field_count(loaded_catalog):
    """FHIR_R4 bundle should have fields from all 9 profiles combined."""
    entry = next(e for e in loaded_catalog.list_entries() if e.descriptor.name == "FHIR_R4")
    canonical = entry.get_latest_version().resolve_canonical()
    # Patient=15, Organization=11, Encounter=16, Condition=14, Observation=18,
    # Procedure=15, Practitioner=10, PractitionerRole=11, Location=14 → 124 total
    assert len(canonical.fields) == 124


def test_omop_bundle_total_field_count(loaded_catalog):
    """OMOP_CDM_5_4 bundle should have fields from all 11 tables combined."""
    entry = next(
        e for e in loaded_catalog.list_entries() if e.descriptor.name == "OMOP_CDM_5_4"
    )
    canonical = entry.get_latest_version().resolve_canonical()
    # PERSON=18, CARE_SITE=6, VISIT_OCCURRENCE=17, PROCEDURE_OCCURRENCE=16,
    # CONDITION_OCCURRENCE=15, DRUG_EXPOSURE=20, MEASUREMENT=18, OBSERVATION=16,
    # DEATH=7, PROVIDER=13, LOCATION=11 → 157 total
    assert len(canonical.fields) == 157


def test_bundle_skipped_when_individuals_absent(fresh_catalog):
    """Calling register_bundles before register_all returns 0 (nothing to merge)."""
    count = register_bundles(fresh_catalog)
    assert count == 0


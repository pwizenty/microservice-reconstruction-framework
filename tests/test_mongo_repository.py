"""Unit tests for the persistence of reconstruction results.

Runs against ``mongomock`` rather than a MongoDB: what is under test is which
documents a save leaves behind, not the database.
"""

import mongomock
import pytest
from mrf.modules.domain_data import Context, DataStructure
from mrf.repositories import mongo_repository


@pytest.fixture
def database(monkeypatch):
    """Redirect the repository to an in-memory database."""
    client = mongomock.MongoClient()
    monkeypatch.setattr(mongo_repository, "__setup_database", lambda: client["mrf"])
    return client["mrf"]


def context(name: str, structures: list[str]) -> Context:
    reconstructed = Context(f"com.example.{name}", name, f"{name}Application.java")
    for structure in structures:
        reconstructed.data_structures.append(
            DataStructure(f"com.example.{name}.{structure}", structure, "file.java")
        )
    return reconstructed


def test_saving_the_same_context_twice_keeps_one_document(database):
    mongo_repository.save_contexts([context("CustomerCore", ["Customer"])])
    mongo_repository.save_contexts([context("CustomerCore", ["Customer"])])

    assert database["context"].count_documents({}) == 1


def test_saving_again_updates_the_stored_context(database):
    mongo_repository.save_contexts([context("CustomerCore", ["Customer"])])
    mongo_repository.save_contexts([context("CustomerCore", ["Customer", "Address"])])

    stored = database["context"].find_one({"name": "CustomerCore"})
    assert [s["name"] for s in stored["data_structures"]] == ["Customer", "Address"]


def test_a_context_of_another_run_is_kept(database):
    mongo_repository.save_contexts([context("CustomerCore", [])])
    mongo_repository.save_contexts([context("PolicyManagement", [])])

    assert sorted(c["name"] for c in database["context"].find()) == [
        "CustomerCore",
        "PolicyManagement",
    ]


def test_replace_drops_what_an_earlier_run_saved(database):
    mongo_repository.save_contexts([context("CustomerCore", [])])
    mongo_repository.save_contexts([context("PolicyManagement", [])], replace=True)

    assert [c["name"] for c in database["context"].find()] == ["PolicyManagement"]

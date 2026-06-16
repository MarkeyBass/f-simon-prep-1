"""
Tests for the catalog service. Having even a handful of these is a big part
of what 'the code needs to be good' means. Run with: pytest

The Firestore dependency is overridden with an in-memory repository, so these
run anywhere with no credentials and no network.
"""

from fastapi.testclient import TestClient

from main import app
from repository import InMemoryProductRepository, get_repository

# A single fake repo instance, reset per test in setup_function. The override
# returns this same instance so multiple requests in one test share state.
_repo = InMemoryProductRepository()
app.dependency_overrides[get_repository] = lambda: _repo

client = TestClient(app)


def setup_function() -> None:
    # Fresh, empty store between tests.
    global _repo
    _repo = InMemoryProductRepository()


SAMPLE = {
    "products": [
        {
            "id": "1",
            "title": "Black Boots",
            "category": "shoes",
            "price": 90,
            "tags": ["black", "leather"],
        },
        {
            "id": "2",
            "title": "Brown Boots",
            "category": "shoes",
            "price": 120,
            "tags": ["brown", "leather"],
        },
        {
            "id": "3",
            "title": "Red Scarf",
            "category": "accessories",
            "price": 30,
            "tags": ["red"],
        },
    ]
}


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_and_list() -> None:
    r = client.post("/products", json=SAMPLE)
    assert r.status_code == 201
    assert r.json()["ingested"] == 3

    r = client.get("/products", params={"category": "shoes"})
    assert r.json()["total"] == 2


def test_filter_and_paginate() -> None:
    client.post("/products", json=SAMPLE)
    r = client.get("/products", params={"max_price": 100, "limit": 1})
    body = r.json()
    assert body["total"] == 2  # boots@90 and scarf@30
    assert len(body["items"]) == 1  # paginated to 1


def test_missing_product_is_404() -> None:
    assert client.get("/products/nope").status_code == 404


def test_similar_ranks_by_shared_tags() -> None:
    client.post("/products", json=SAMPLE)
    r = client.get("/products/1/similar")
    items = r.json()["items"]
    assert items[0]["id"] == "2"  # same category + shares 'leather'

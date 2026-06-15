"""
Tests for the catalog service. Having even a handful of these is a big part
of what 'the code needs to be good' means. Run with: pytest
"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def setup_function() -> None:
    # Clean state between tests — the in-memory store is module-level.
    main._CATALOG.clear()


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

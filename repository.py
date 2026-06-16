"""
Storage layer for the catalog.

The routes depend on the `ProductRepository` protocol, not on a concrete
backend. That keeps the API testable (inject an in-memory fake — no credentials
needed) and makes the swap from a dict to Firestore a single-file change that
never touches a route.

Firestore makes the service stateless, so it scales horizontally on Cloud Run.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Protocol

from google.cloud import firestore

from models import Product


class ProductRepository(Protocol):
    """Everything the routes need from storage — nothing more."""

    def upsert_many(self, products: Iterable[Product]) -> int:
        """Upsert products by id. Returns the number written."""
        ...

    def all(self) -> list[Product]:
        ...

    def get(self, product_id: str) -> Product | None:
        ...

    def count(self) -> int:
        ...


class InMemoryProductRepository:
    """Dict-backed store. Local dev + tests — no credentials, no network."""

    def __init__(self) -> None:
        self._items: dict[str, Product] = {}

    def upsert_many(self, products: Iterable[Product]) -> int:
        count = 0
        for product in products:
            self._items[product.id] = product
            count += 1
        return count

    def all(self) -> list[Product]:
        return list(self._items.values())

    def get(self, product_id: str) -> Product | None:
        return self._items.get(product_id)

    def count(self) -> int:
        return len(self._items)


class FirestoreProductRepository:
    """
    Firestore-backed store. Stateless across requests, so the service scales
    horizontally on Cloud Run.

    Scale note: `all()` streams the whole collection and the routes filter in
    Python — fine for a demo catalog. For real volume, push filters into the
    query (`where(filter=FieldFilter(...))`), paginate with cursors instead of
    large offsets, and add the composite indexes Firestore prompts for.
    """

    _COLLECTION = "products"
    _BATCH_LIMIT = 500  # Firestore caps a write batch at 500 operations.

    def __init__(self, client: firestore.Client) -> None:
        self._client = client
        self._col = client.collection(self._COLLECTION)

    def upsert_many(self, products: Iterable[Product]) -> int:
        batch = self._client.batch()
        pending = 0
        total = 0
        for product in products:
            batch.set(self._col.document(product.id), product.model_dump())
            pending += 1
            total += 1
            if pending == self._BATCH_LIMIT:
                batch.commit()
                batch = self._client.batch()
                pending = 0
        if pending:
            batch.commit()
        return total

    def all(self) -> list[Product]:
        return [Product.model_validate(doc.to_dict()) for doc in self._col.stream()]

    def get(self, product_id: str) -> Product | None:
        doc = self._col.document(product_id).get()
        return Product.model_validate(doc.to_dict()) if doc.exists else None

    def count(self) -> int:
        # Aggregation query — counts server-side without reading every document.
        results = self._col.count(alias="all").get()
        return int(results[0][0].value)


@lru_cache(maxsize=1)
def _firestore_client() -> firestore.Client:
    # Constructed lazily and cached — never at import time, so importing the app
    # needs no credentials (tests override the dependency below). Credentials
    # resolve via ADC locally (`gcloud auth application-default login`) and via
    # the runtime service account on Cloud Run. No key files.
    return firestore.Client()


def get_repository() -> ProductRepository:
    """FastAPI dependency. Tests override this with an in-memory fake."""
    return FirestoreProductRepository(_firestore_client())

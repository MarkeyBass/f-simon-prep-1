"""
Fast Simon practice service — a small, clean backend for Cloud Run.

Domain-relevant on purpose: ingest a product catalog, query it with
filters + pagination, and return "similar" products. Mirrors the kind of
data-flow + discovery work the role is about.

Storage is in-memory here so it runs anywhere. The swap to Firestore is
noted inline — in a real assignment, do that swap to show you can handle
persistence and horizontal scale.

Run locally:   uvicorn main:app --reload --port 8080
Test:          pytest
Deploy:        gcloud run deploy fastsimon-practice --source . --region europe-west1 --allow-unauthenticated
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Fast Simon Practice — Catalog Service")


# ---- Models --------------------------------------------------------------

class Product(BaseModel):
    id: str
    title: str
    category: str
    price: float = Field(ge=0)
    tags: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    products: list[Product]


# ---- "Storage" -----------------------------------------------------------
# In-memory for the demo. In the assignment, back this with Firestore:
#   from google.cloud import firestore
#   db = firestore.Client()
#   db.collection("products").document(p.id).set(p.model_dump())
# That makes the service stateless and horizontally scalable on Cloud Run.

_CATALOG: dict[str, Product] = {}


# ---- Routes --------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check — handy as the stub you deploy first."""
    return {"status": "ok"}


@app.post("/products", status_code=201)
def ingest(req: IngestRequest) -> dict[str, int]:
    """Bulk-ingest a catalog. Upserts by id."""
    for p in req.products:
        _CATALOG[p.id] = p
    return {"ingested": len(req.products), "catalog_size": len(_CATALOG)}


@app.get("/products")
def list_products(
    category: str | None = None,
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """List products with filtering + pagination (the 'data flow' part)."""
    items = list(_CATALOG.values())
    if category:
        items = [p for p in items if p.category == category]
    if max_price is not None:
        items = [p for p in items if p.price <= max_price]
    total = len(items)
    page = items[offset : offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "items": page}


@app.get("/products/{product_id}")
def get_product(product_id: str) -> Product:
    product = _CATALOG.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@app.get("/products/{product_id}/similar")
def similar(product_id: str, limit: int = Query(default=5, ge=1, le=50)) -> dict:
    """
    Naive 'shop similar': same category, ranked by shared tags.
    In a real system this is vector similarity over embeddings — the
    exact machinery you built in Confy. Say that out loud if asked.
    """
    target = _CATALOG.get(product_id)
    if target is None:
        raise HTTPException(status_code=404, detail="product not found")

    def score(p: Product) -> int:
        return len(set(p.tags) & set(target.tags))

    candidates = [
        p for p in _CATALOG.values()
        if p.id != product_id and p.category == target.category
    ]
    ranked = sorted(candidates, key=score, reverse=True)[:limit]
    return {"of": product_id, "items": ranked}

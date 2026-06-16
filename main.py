"""
Fast Simon practice service — a small, clean backend for Cloud Run.

Ingest a product catalog, query it with filters + pagination, and return
"similar" products. Storage is Firestore, behind a repository abstraction
(see repository.py), so the service is stateless and scales horizontally on
Cloud Run.

Run locally:
    gcloud auth application-default login    # one-time, sets up ADC
    uvicorn main:app --reload --port 8080
Test:
    pytest                                   # uses an in-memory fake, no creds
Deploy:
    gcloud run deploy fastsimon-practice --source . --region europe-west1 --allow-unauthenticated
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status

from models import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    Product,
    ProductPage,
    SimilarProducts,
)
from repository import ProductRepository, get_repository

app = FastAPI(title="Fast Simon Practice — Catalog Service")

# Routes depend on the abstraction, not on Firestore directly. Tests override
# `get_repository` to inject an in-memory fake.
RepositoryDep = Annotated[ProductRepository, Depends(get_repository)]
# ---- "Storage" -----------------------------------------------------------
# In-memory for the demo. In the assignment, back this with Firestore:
#   from google.cloud import firestore
#   db = firestore.Client()
#   db.collection("products").document(p.id).set(p.model_dump())
# That makes the service stateless and horizontally scalable on Cloud Run.

# _CATALOG: dict[str, Product] = {}

# ---- Routes --------------------------------------------------------------

@app.get("/health")
def health() -> HealthResponse:
    """Liveness check — handy as the stub you deploy first."""
    return HealthResponse(status="ok")


@app.post("/products", status_code=status.HTTP_201_CREATED)
def ingest(req: IngestRequest, repo: RepositoryDep) -> IngestResponse:
    """Bulk-ingest a catalog. Upserts by id."""
    ingested = repo.upsert_many(req.products)
    return IngestResponse(ingested=ingested, catalog_size=repo.count())


@app.get("/products")
def list_products(
    repo: RepositoryDep,
    category: str | None = None,
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductPage:
    """List products with filtering + pagination (the 'data flow' part)."""
    items = repo.all()
    if category:
        items = [p for p in items if p.category == category]
    if max_price is not None:
        items = [p for p in items if p.price <= max_price]
    total = len(items)
    page = items[offset : offset + limit]
    return ProductPage(total=total, limit=limit, offset=offset, items=page)


@app.get("/products/{product_id}")
def get_product(product_id: str, repo: RepositoryDep) -> Product:
    product = repo.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="product not found"
        )
    return product


@app.get("/products/{product_id}/similar")
def similar(
    product_id: str,
    repo: RepositoryDep,
    limit: int = Query(default=5, ge=1, le=50),
) -> SimilarProducts:
    """
    Naive 'shop similar': same category, ranked by shared tags.
    In a real system this is vector similarity over embeddings — the exact
    machinery you built in Confy. Say that out loud if asked.
    """
    target = repo.get(product_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="product not found"
        )

    def score(p: Product) -> int:
        return len(set(p.tags) & set(target.tags))

    candidates = [
        p
        for p in repo.all()
        if p.id != product_id and p.category == target.category
    ]
    ranked = sorted(candidates, key=score, reverse=True)[:limit]
    return SimilarProducts(of=product_id, items=ranked)

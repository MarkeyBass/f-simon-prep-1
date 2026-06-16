"""Pydantic v2 models for the catalog service — the API contract.

Kept in their own module so both the routes (main.py) and the storage layer
(repository.py) can depend on them without a circular import.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    title: str
    category: str
    price: float = Field(ge=0)
    tags: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    products: list[Product]


class IngestResponse(BaseModel):
    ingested: int
    catalog_size: int


class ProductPage(BaseModel):
    """A page of products with the filters/pagination that produced it."""

    total: int
    limit: int
    offset: int
    items: list[Product] = Field(default_factory=list)


class SimilarProducts(BaseModel):
    """'Shop similar' result: the source product id and its ranked matches."""

    of: str
    items: list[Product] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str

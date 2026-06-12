# app/services/shopee_service.py (atualizado)
import os
from app.mock.products import MOCK_PRODUCTS
from app.services.amazon_service import search_products as amazon_search
from app.services.amazon_service import get_product_by_asin

USE_MOCK = os.getenv("ENVIRONMENT", "development") == "development"
USE_AMAZON = os.getenv("USE_AMAZON", "false").lower() == "true"

def search_products(keyword: str) -> list:
    if USE_AMAZON:
        results = amazon_search(keyword)
        return results if results else []

    if USE_MOCK:
        keyword_lower = keyword.lower()
        results = [
            p for p in MOCK_PRODUCTS
            if keyword_lower in p["title"].lower()
            or keyword_lower in p["category"].lower()
        ]
        return results if results else MOCK_PRODUCTS

    raise NotImplementedError("Nenhuma fonte de dados configurada")

def get_product_by_id(product_id: str) -> dict | None:
    if USE_AMAZON:
        return get_product_by_asin(product_id)

    if USE_MOCK:
        return next(
            (p for p in MOCK_PRODUCTS if p["id"] == product_id),
            None
        )
    return None
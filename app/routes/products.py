from fastapi import APIRouter, HTTPException, Query
from app.services.amazon_service import search_products, get_product_by_asin
from app.services.ai_service import format_product_message

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/search")
async def search(
    keyword: str = Query(..., description="Palavra-chave para busca"),
    channel: str = Query("telegram", description="Canal: telegram ou whatsapp")
):
    """Busca produtos e formata mensagem com IA"""
    products = search_products(keyword)

    if not products:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado")

    # Formata o primeiro resultado com IA
    product = products[0]
    formatted = format_product_message(product, channel)

    return {
        "product": product,
        "formatted_message": formatted,
        "total_found": len(products)
    }

@router.get("/all")
async def get_all():
    """Lista todos os produtos mockados"""
    return {"products": search_products(""), "total": len(search_products(""))}

@router.get("/{product_id}/format")
async def format_product(
    product_id: str,
    channel: str = Query("telegram", description="Canal: telegram ou whatsapp")
):
    """Formata mensagem de um produto específico com IA"""
    product = get_product_by_asin(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    formatted = format_product_message(product, channel)

    return {
        "product": product,
        "formatted_message": formatted
    }
from fastapi import FastAPI
from app.routes.products import router as products_router

app = FastAPI(
    title="Shopee Bot API",
    description="API para divulgação de produtos Shopee via Telegram e WhatsApp",
    version="1.0.0"
)

app.include_router(products_router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Shopee Bot API rodando!",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

ML_AFFILIATE_ID = os.getenv("ML_AFFILIATE_ID", "crev9575727")

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.8",
        "Connection": "keep-alive",
    }
]

def get_headers():
    return random.choice(HEADERS_LIST)

def build_affiliate_url(product_url: str) -> str:
    """Monta o link de afiliado do ML"""
    # Remove parâmetros existentes e adiciona o affid
    clean_url = product_url.split("?")[0]
    return f"{clean_url}?affid={ML_AFFILIATE_ID}"

def extract_price(text: str) -> float | None:
    """Extrai preço de um texto"""
    if not text:
        return None
    clean = text.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(clean)
    except ValueError:
        return None

def search_products(keyword: str, max_results: int = 8) -> list:
    """Busca produtos no Mercado Livre"""
    time.sleep(random.uniform(4, 8))

    search_url = f"https://lista.mercadolivre.com.br/{keyword.replace(' ', '-')}"

    try:
        response = requests.get(
            search_url,
            headers=get_headers(),
            timeout=15
        )

        if response.status_code == 503:
            print(f"  ⚠️ 503 no ML para {keyword}, aguardando 30s...")
            time.sleep(30)
            response = requests.get(search_url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"  Status {response.status_code} ao buscar ML: {keyword}")
            return []

        soup = BeautifulSoup(response.content, "lxml")
        products = []

        # Seleciona os cards de produto
        items = soup.select("li.ui-search-layout__item")

        for item in items[:max_results]:
            try:
                # Título
                title_el = item.select_one("h2.ui-search-item__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Link do produto
                link_el = item.select_one("a.ui-search-link")
                if not link_el:
                    continue
                product_url = link_el.get("href", "").split("?")[0]

                # ID do produto (MLB...)
                product_id = ""
                id_match = re.search(r"MLB-?(\d+)", product_url)
                if id_match:
                    product_id = f"MLB{id_match.group(1)}"

                # Preço atual
                price = None
                price_el = item.select_one(".andes-money-amount__fraction")
                if price_el:
                    cents_el = item.select_one(".andes-money-amount__cents")
                    price_text = price_el.get_text(strip=True)
                    if cents_el:
                        price_text += f",{cents_el.get_text(strip=True)}"
                    price = extract_price(price_text)

                # Preço original
                original_price = None
                original_el = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
                if original_el:
                    original_price = extract_price(original_el.get_text(strip=True))

                # Desconto
                discount = 0
                discount_el = item.select_one(".ui-search-price__discount")
                if discount_el:
                    discount_text = discount_el.get_text(strip=True)
                    discount_match = re.search(r"(\d+)", discount_text)
                    if discount_match:
                        discount = int(discount_match.group(1))
                elif price and original_price and original_price > price:
                    discount = int(((original_price - price) / original_price) * 100)

                # Rating
                rating = 0.0
                rating_el = item.select_one(".ui-search-reviews__rating-number")
                if rating_el:
                    try:
                        rating = float(rating_el.get_text(strip=True).replace(",", "."))
                    except ValueError:
                        pass

                # Reviews
                review_count = 0
                review_el = item.select_one(".ui-search-reviews__amount")
                if review_el:
                    review_text = re.sub(r"[^\d]", "", review_el.get_text(strip=True))
                    try:
                        review_count = int(review_text)
                    except ValueError:
                        pass

                # Imagem
                image_url = ""
                img_el = item.select_one("img.ui-search-result-image__element")
                if img_el:
                    image_url = img_el.get("data-src") or img_el.get("src", "")
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "seutag-20")

# Headers que simulam um navegador real
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
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

def build_affiliate_url(asin: str) -> str:
    """Monta o link de afiliado com o Associate Tag"""
    return f"https://www.amazon.com.br/dp/{asin}?tag={ASSOCIATE_TAG}"

def extract_asin_from_url(url: str) -> str | None:
    """Extrai o ASIN de uma URL da Amazon"""
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def search_products(keyword: str, max_results: int = 5) -> list:
    """Busca produtos na Amazon Brasil"""
    # Delay aleatório para não parecer robô
    time.sleep(random.uniform(1.5, 3.0))

    search_url = f"https://www.amazon.com.br/s?k={keyword.replace(' ', '+')}"

    try:
        response = requests.get(
            search_url,
            headers=get_headers(),
            timeout=15
        )

        if response.status_code == 503:
            print(f"  ⚠️ 503 em {keyword}, aguardando 30s e tentando novamente...")
            time.sleep(30)
            response = requests.get(search_url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            print(f"Status {response.status_code} ao buscar: {keyword}")
            return []

        soup = BeautifulSoup(response.content, "lxml")
        products = []

        # Seleciona os cards de produto
        items = soup.select("div[data-component-type='s-search-result']")

        for item in items[:max_results]:
            try:
                asin = item.get("data-asin")
                if not asin:
                    continue

                # Título
                title_el = item.select_one("h2 span")
                title = title_el.get_text(strip=True) if title_el else "Sem título"

                # Preço atual
                price = None
                price_el = item.select_one(".a-price .a-offscreen")
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price_text = price_text.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    try:
                        price = float(price_text)
                    except ValueError:
                        pass

                # Preço original (riscado)
                original_price = None
                original_el = item.select_one(".a-price.a-text-price .a-offscreen")
                if original_el:
                    orig_text = original_el.get_text(strip=True)
                    orig_text = orig_text.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    try:
                        original_price = float(orig_text)
                    except ValueError:
                        pass

                # Desconto
                discount = 0
                if price and original_price and original_price > price:
                    discount = int(((original_price - price) / original_price) * 100)

                # Rating
                rating = 0.0
                rating_el = item.select_one(".a-icon-star-small .a-icon-alt")
                if rating_el:
                    rating_text = rating_el.get_text(strip=True).split(" ")[0].replace(",", ".")
                    try:
                        rating = float(rating_text)
                    except ValueError:
                        pass

                # Número de reviews
                review_count = 0
                review_el = item.select_one(".a-size-small .a-size-base")
                if review_el:
                    review_text = review_el.get_text(strip=True).replace(".", "").replace(",", "")
                    try:
                        review_count = int(review_text)
                    except ValueError:
                        pass

                # Imagem
                image_url = ""
                img_el = item.select_one("img.s-image")
                if img_el:
                    image_url = img_el.get("src", "")

                # Só adiciona se tiver preço
                if price:
                    products.append({
                        "id": asin,
                        "asin": asin,
                        "title": title,
                        "price": price,
                        "original_price": original_price or price,
                        "discount": discount,
                        "rating": rating,
                        "review_count": review_count,
                        "category": "Amazon",
                        "image_url": image_url,
                        "affiliate_url": build_affiliate_url(asin),
                        "is_available": True,
                        "features": []
                    })

            except Exception as e:
                print(f"Erro ao processar item: {e}")
                continue

        return products

    except Exception as e:
        print(f"Erro na busca Amazon: {e}")
        return []

def get_product_by_asin(asin: str) -> dict | None:
    """Busca detalhes de um produto pelo ASIN"""
    time.sleep(random.uniform(1.5, 2.5))

    url = f"https://www.amazon.com.br/dp/{asin}"

    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, "lxml")

        # Título
        title_el = soup.select_one("#productTitle")
        title = title_el.get_text(strip=True) if title_el else "Sem título"

        # Preço
        price = None
        for selector in [".a-price .a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice"]:
            price_el = soup.select_one(selector)
            if price_el:
                price_text = price_el.get_text(strip=True)
                price_text = price_text.replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    price = float(price_text)
                    break
                except ValueError:
                    continue

        # Features (bullet points)
        features = []
        feature_els = soup.select("#feature-bullets li span.a-list-item")
        for f in feature_els[:4]:
            text = f.get_text(strip=True)
            if text and len(text) > 5:
                features.append(text)

        # Rating
        rating = 0.0
        rating_el = soup.select_one("#acrPopover .a-icon-alt")
        if rating_el:
            try:
                rating = float(rating_el.get_text(strip=True).split(" ")[0].replace(",", "."))
            except ValueError:
                pass

        # Reviews
        review_count = 0
        review_el = soup.select_one("#acrCustomerReviewText")
        if review_el:
            try:
                review_count = int(review_el.get_text(strip=True).split(" ")[0].replace(".", "").replace(",", ""))
            except ValueError:
                pass

        return {
            "id": asin,
            "asin": asin,
            "title": title,
            "price": price or 0.0,
            "original_price": price or 0.0,
            "discount": 0,
            "rating": rating,
            "review_count": review_count,
            "category": "Amazon",
            "image_url": "",
            "affiliate_url": build_affiliate_url(asin),
            "is_available": price is not None,
            "features": features
        }

    except Exception as e:
        print(f"Erro ao buscar ASIN {asin}: {e}")
        return None
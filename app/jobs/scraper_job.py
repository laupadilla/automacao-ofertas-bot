import json
import os
import random
import time
from datetime import datetime, date, timedelta
from anthropic import Anthropic
from app.db.database import SessionLocal, init_db
from app.db.models import Product, SentProduct, DailyQueue
from app.services.amazon_service import search_products as amazon_search
from app.services.mercadolivre_service import search_products as ml_search
from app.services.ai_service import format_product_message

# Categorias Amazon (15 produtos)
AMAZON_CATEGORIES = {
    "Eletrônicos": [
        "fone bluetooth", "smartwatch", "carregador portatil",
        "cabo usb-c", "caixa de som bluetooth", "headphone",
        "tablet", "teclado sem fio", "mouse gamer", "webcam"
    ],
    "Casa e Cozinha": [
        "air fryer", "panela pressao eletrica", "organizer cozinha",
        "jogo de panelas", "porta temperos", "fritadeira eletrica",
        "liquidificador", "cafeteira", "escorredor", "pote hermetico"
    ],
    "Beleza": [
        "protetor solar facial", "creme hidratante", "escova cabelo",
        "kit skincare", "perfume feminino", "shampoo",
        "serum facial", "batom", "mascara cabelo", "condicionador"
    ]
}

# Categorias Mercado Livre (15 produtos)
ML_CATEGORIES = {
    "Eletrônicos ML": [
        "fone de ouvido bluetooth", "relogio smartwatch",
        "carregador portatil celular", "cabo usb tipo c",
        "caixa de som portatil", "teclado bluetooth",
        "mouse sem fio", "webcam full hd"
    ],
    "Casa e Cozinha ML": [
        "air fryer digital", "panela eletrica",
        "jogo panelas antiaderente", "cafeteira eletrica",
        "fritadeira sem oleo", "liquidificador potente"
    ],
    "Moda e Esporte ML": [
        "tenis feminino", "mochila escolar",
        "kit maquiagem", "perfume importado",
        "suplemento whey protein", "roupa academia"
    ]
}

SCHEDULED_TIMES   = ["07:30", "12:00", "18:30", "21:00"]
PRODUCTS_PER_SLOT = [8, 7, 8, 7]

def already_sent(db, asin: str, channel_id: str, days: int = 30) -> bool:
    cutoff = datetime.utcnow() - timedelta(days=days)
    return db.query(SentProduct).filter(
        SentProduct.asin == asin,
        SentProduct.channel_id == channel_id,
        SentProduct.sent_at >= cutoff
    ).first() is not None

def in_todays_queue(db, asin: str) -> bool:
    today = str(date.today())
    return db.query(DailyQueue).filter(
        DailyQueue.asin == asin,
        DailyQueue.queue_date == today
    ).first() is not None

def shorten_title(product: dict) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": (
                f"Crie um título curto e persuasivo com no máximo 60 caracteres "
                f"com emoji no início para este produto:\n"
                f"Produto: {product['title']}\n"
                f"Preço: R$ {product['price']:.2f}\n"
                f"Desconto: {product['discount']}%\n"
                f"Retorne APENAS o título, sem aspas ou explicações."
            )
        }]
    )
    return msg.content[0].text.strip()[:60]

def collect_from_source(db, search_fn, categories, target, channel_id, source_name):
    """Coleta produtos de uma fonte (Amazon ou ML)"""
    collected = []

    for category, keywords in categories.items():
        print(f"\n  📦 [{source_name}] {category}")
        random.shuffle(keywords)

        for keyword in keywords:
            cat_count = len([p for p in collected if p["category"] == category])
            if cat_count >= 5:
                break

            if len(collected) >= target:
                break

            print(f"    🔍 {keyword}")
            products = search_fn(keyword, max_results=8)
            time.sleep(random.uniform(2, 4))

            for product in products:
                asin = product["asin"]
                if not asin:
                    continue
                if product["discount"] < 10:
                    continue
                if already_sent(db, asin, channel_id, days=30):
                    print(f"    ⏭️ {asin} já enviado")
                    continue
                if in_todays_queue(db, asin):
                    continue

                # Upsert no banco
                existing = db.query(Product).filter(Product.asin == asin).first()
                if existing:
                    existing.price      = product["price"]
                    existing.discount   = product["discount"]
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(Product(
                        asin           = asin,
                        title          = product["title"],
                        price          = product["price"],
                        original_price = product["original_price"],
                        discount       = product["discount"],
                        rating         = product["rating"],
                        review_count   = product["review_count"],
                        category       = category,
                        image_url      = product["image_url"],
                        affiliate_url  = product["affiliate_url"],
                        features       = json.dumps(product.get("features", []))
                    ))
                db.commit()

                product["category"] = category
                collected.append(product)
                break

        if len(collected) >= target:
            break

    return collected

def run_scraper():
    init_db()
    db         = SessionLocal()
    today      = str(date.today())
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")

    print(f"\n🚀 Scraper iniciado — {today}")

    # Limpa filas antigas não enviadas
    db.query(DailyQueue).filter(
        DailyQueue.queue_date != today,
        DailyQueue.sent == False
    ).delete(synchronize_session=False)
    db.commit()

    # Coleta 15 da Amazon + 15 do ML
    print("\n🛒 Coletando Amazon...")
    amazon_products = collect_from_source(
        db, amazon_search, AMAZON_CATEGORIES,
        target=15, channel_id=channel_id, source_name="Amazon"
    )

    print("\n🛍️ Coletando Mercado Livre...")
    ml_products = collect_from_source(
        db, ml_search, ML_CATEGORIES,
        target=15, channel_id=channel_id, source_name="ML"
    )

    # Intercala Amazon e ML na lista final
    all_products = []
    for i in range(max(len(amazon_products), len(ml_products))):
        if i < len(amazon_products):
            all_products.append(amazon_products[i])
        if i < len(ml_products):
            all_products.append(ml_products[i])

    print(f"\n✅ {len(all_products)} produtos coletados")
    print(f"   Amazon: {len(amazon_products)} | ML: {len(ml_products)}")
    print("🤖 Gerando mensagens com IA...\n")

    slot_index = 0
    slot_count = 0

    for product in all_products[:30]:
        try:
            formatted   = format_product_message(product, "telegram")
            title_short = shorten_title(product)
        except Exception as e:
            print(f"  ⚠️ Erro IA {product['asin']}: {e}")
            continue

        scheduled_time = SCHEDULED_TIMES[slot_index]
        slot_count += 1
        if slot_count >= PRODUCTS_PER_SLOT[slot_index]:
            slot_index = min(slot_index + 1, len(SCHEDULED_TIMES) - 1)
            slot_count = 0

        db.add(DailyQueue(
            asin             = product["asin"],
            category         = product["category"],
            title_short      = title_short,
            message_telegram = formatted["emoji"] + " " + formatted["text"],
            affiliate_url    = product["affiliate_url"],
            image_url        = product["image_url"],
            price            = product["price"],
            discount         = product["discount"],
            scheduled_time   = scheduled_time,
            queue_date       = today,
            sent             = False
        ))

        source = "🛒" if product.get("source") != "mercadolivre" else "🛍️"
        print(f"  ✅ {source} [{scheduled_time}] {title_short}")

    db.commit()
    db.close()
    print(f"\n🎉 Fila do dia montada!")
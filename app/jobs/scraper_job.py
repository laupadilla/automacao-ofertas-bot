import json
import os
import random
import time
from datetime import datetime, date, timedelta
from anthropic import Anthropic
from app.db.database import SessionLocal, init_db
from app.db.models import Product, SentProduct, DailyQueue
from app.services.amazon_service import search_products
from app.services.ai_service import format_product_message

CATEGORIES = {
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
        "kit skincare", "perfume feminino", "shampoo", "condicionador",
        "sérum facial", "batom", "mascara cabelo"
    ]
}

SCHEDULED_TIMES  = ["07:30", "12:00", "18:30", "21:00"]
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

def run_scraper():
    init_db()
    db = SessionLocal()
    today = str(date.today())
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")

    print(f"\n🚀 Scraper iniciado — {today}")

    # Limpa filas de dias anteriores não enviadas
    db.query(DailyQueue).filter(
        DailyQueue.queue_date != today,
        DailyQueue.sent == False
    ).delete(synchronize_session=False)
    db.commit()

    collected = []

    for category, keywords in CATEGORIES.items():
        print(f"\n📦 Categoria: {category}")
        random.shuffle(keywords)

        for keyword in keywords:
            cat_count = len([p for p in collected if p["category"] == category])
            if cat_count >= 10:
                break

            print(f"  🔍 {keyword}")
            products = search_products(keyword, max_results=12)
            time.sleep(random.uniform(8, 15))

            for product in products:
                asin = product["asin"]

                if product["discount"] < 10:
                    continue
                if already_sent(db, asin, channel_id, days=30):
                    print(f"    ⏭️ {asin} já enviado recentemente")
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
                        asin          = asin,
                        title         = product["title"],
                        price         = product["price"],
                        original_price= product["original_price"],
                        discount      = product["discount"],
                        rating        = product["rating"],
                        review_count  = product["review_count"],
                        category      = category,
                        image_url     = product["image_url"],
                        affiliate_url = product["affiliate_url"],
                        features      = json.dumps(product.get("features", []))
                    ))
                db.commit()

                product["category"] = category
                collected.append(product)
                break

        if len(collected) >= 30:
            break

    print(f"\n✅ {len(collected)} produtos coletados")
    print("🤖 Gerando mensagens com IA...\n")

    slot_index = 0
    slot_count = 0

    for product in collected[:30]:
        try:
            formatted    = format_product_message(product, "telegram")
            title_short  = shorten_title(product)
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

        print(f"  ✅ [{scheduled_time}] {title_short}")

    db.commit()
    db.close()
    print("\n🎉 Fila do dia montada!")
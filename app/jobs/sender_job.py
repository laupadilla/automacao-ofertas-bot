import os
import asyncio
from datetime import datetime, date
from telegram import Bot
from telegram.error import TelegramError
from app.db.database import SessionLocal, init_db
from app.db.models import DailyQueue, SentProduct

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
DELAY_SECONDS       = 180  # 3 min entre mensagens

async def send_product(bot: Bot, item: DailyQueue) -> bool:
    message = (
        f"{item.message_telegram}\n\n"
        f"🔗 [Ver na Amazon]({item.affiliate_url})"
    )
    try:
        if item.image_url:
            await bot.send_photo(
                chat_id    = TELEGRAM_CHANNEL_ID,
                photo      = item.image_url,
                caption    = message,
                parse_mode = "Markdown"
            )
        else:
            await bot.send_message(
                chat_id    = TELEGRAM_CHANNEL_ID,
                text       = message,
                parse_mode = "Markdown"
            )
        return True
    except TelegramError as e:
        print(f"  ❌ Telegram erro: {e}")
        return False

async def run_sender():
    init_db()
    db          = SessionLocal()
    bot         = Bot(token=TELEGRAM_BOT_TOKEN)
    today       = str(date.today())
    current_time = datetime.now().strftime("%H:%M")

    print(f"\n📤 Sender — {current_time}")

    items = db.query(DailyQueue).filter(
        DailyQueue.queue_date      == today,
        DailyQueue.scheduled_time  == current_time,
        DailyQueue.sent            == False
    ).all()

    if not items:
        print(f"  ℹ️ Sem itens para {current_time}")
        db.close()
        return

    print(f"  📦 {len(items)} produtos a enviar")

    for item in items:
        success = await send_product(bot, item)
        if success:
            item.sent = True
            db.add(SentProduct(
                asin         = item.asin,
                channel_id   = TELEGRAM_CHANNEL_ID,
                message_text = item.message_telegram
            ))
            db.commit()
            print(f"  ✅ {item.title_short}")
            await asyncio.sleep(DELAY_SECONDS)
        else:
            print(f"  ❌ Falhou: {item.asin}")

    db.close()
    print("✅ Sender concluído!")

def run_sender_sync():
    asyncio.run(run_sender())
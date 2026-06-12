import logging
import os
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:8000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Sou o *Automação Ofertas Bot*!\n\n"
        "Veja o que posso fazer por você:\n\n"
        "🔍 /buscar `<produto>` — busca um produto\n"
        "🔥 /ofertas — top ofertas do dia\n"
        "❓ /ajuda — lista de comandos\n\n"
        "_Recebemos comissão pelas compras qualificadas._",
        parse_mode="Markdown"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *Comandos disponíveis:*\n\n"
        "🔍 /buscar `<produto>` — ex: `/buscar fone bluetooth`\n"
        "🔥 /ofertas — melhores ofertas do momento\n"
        "❓ /ajuda — esta mensagem\n\n"
        "_Recebemos comissão pelas compras qualificadas._",
        parse_mode="Markdown"
    )

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Me diz o que você quer buscar!\n"
            "Exemplo: `/buscar fone bluetooth`",
            parse_mode="Markdown"
        )
        return

    keyword = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando *{keyword}*...", parse_mode="Markdown")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_URL}/products/search",
                params={"keyword": keyword, "channel": "telegram"}
            )

        if response.status_code == 404:
            await update.message.reply_text(
                f"😕 Nenhum produto encontrado para *{keyword}*.\n"
                "Tente outra palavra-chave!",
                parse_mode="Markdown"
            )
            return

        data = response.json()
        product = data["product"]
        formatted = data["formatted_message"]

        # Monta a mensagem final
        message = (
            f"{formatted['emoji']} {formatted['text']}\n\n"
            f"🔗 [Ver na Shopee]({product['affiliate_url']})\n\n"
            f"_Recebemos comissão pelas compras qualificadas._"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Erro ao buscar produto: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro ao buscar o produto. Tente novamente!"
        )

async def ofertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Buscando as melhores ofertas...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_URL}/products/all")

        data = response.json()
        products = data["products"]

        await update.message.reply_text(
            "🔥 *Melhores ofertas de hoje:*\n\n"
            + "\n".join([
                f"{i+1}. {p['title'][:40]}... — *R$ {p['price']:.2f}* (-{p['discount']}%)"
                for i, p in enumerate(products[:5])
            ])
            + "\n\nUse /buscar `<nome>` para ver detalhes!",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Erro ao buscar ofertas: {e}")
        await update.message.reply_text("❌ Erro ao buscar ofertas. Tente novamente!")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN não configurado no .env")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("ofertas", ofertas))

    logger.info("Bot iniciado! Aguardando mensagens...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
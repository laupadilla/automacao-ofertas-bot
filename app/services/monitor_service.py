import os
import asyncio
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

MONITOR_CHAT_ID = os.getenv("MONITOR_CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

class Monitor:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = MONITOR_CHAT_ID
        self.start_time = None
        self.errors = []
        self.stats = {
            "amazon": 0,
            "total": 0,
            "skipped": 0,
            "errors_503": 0,
        }

    def _send(self, text: str):
        """Envia mensagem de forma síncrona"""
        try:
            asyncio.get_event_loop().run_until_complete(
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode="Markdown"
                )
            )
        except Exception as e:
            print(f"Erro ao enviar monitor: {e}")

    def start(self):
        self.start_time = datetime.now()
        self._send(
            f"🚀 *Scraper iniciado*\n"
            f"📅 {self.start_time.strftime('%d/%m/%Y %H:%M:%S')}"
        )

    def log_category(self, source: str, category: str):
        self._send(f"📦 *[{source}]* Buscando: _{category}_")

    def log_keyword(self, keyword: str, found: int):
        if found > 0:
            self._send(f"  ✅ `{keyword}` → {found} produtos")
        else:
            self._send(f"  ⚠️ `{keyword}` → sem resultados")

    def log_error_503(self, keyword: str):
        self.stats["errors_503"] += 1
        self._send(f"  🔴 *503* em `{keyword}` — aguardando 30s...")

    def log_skipped(self, reason: str):
        self.stats["skipped"] += 1

    def log_product_added(self, title: str, price: float, discount: int, source: str):
        self.stats["total"] += 1
        if source == "amazon":
            self.stats["amazon"] += 1

    def log_error(self, error: str):
        self.errors.append(error)
        self._send(f"❌ *Erro:* `{error}`")

    def finish(self, queue_count: int):
        duration = datetime.now() - self.start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)

        error_text = ""
        if self.errors:
            error_text = "\n\n❌ *Erros:*\n" + "\n".join([f"• {e}" for e in self.errors])

        report = (
            f"📊 *Relatório Final do Scraper*\n"
            f"{'─' * 30}\n"
            f"✅ *Produtos coletados:* {self.stats['total']}\n"
            f"🛒 *Amazon:* {self.stats['amazon']}\n"
            f"⏭️ *Ignorados:* {self.stats['skipped']}\n"
            f"🔴 *Erros 503:* {self.stats['errors_503']}\n"
            f"📋 *Fila gerada:* {queue_count} produtos\n"
            f"⏱️ *Duração:* {minutes}m {seconds}s\n"
            f"{'─' * 30}\n"
            f"⏰ *Próximo envio:* 07:30"
            f"{error_text}"
        )
        self._send(report)

    def log_sender_start(self, time_slot: str, count: int):
        self._send(
            f"📤 *Sender iniciado — {time_slot}*\n"
            f"📦 {count} produtos para enviar"
        )

    def log_sender_finish(self, sent: int, failed: int):
        self._send(
            f"✅ *Sender concluído*\n"
            f"✅ Enviados: {sent}\n"
            f"❌ Falhas: {failed}"
        )

    def log_sender_empty(self, time_slot: str):
        self._send(f"ℹ️ *Sender {time_slot}* — nenhum produto na fila")
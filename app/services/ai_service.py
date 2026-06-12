import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def format_product_message(product: dict, channel: str = "telegram") -> dict:
    discount_value = ""
    if product.get("discount", 0) > 0:
        economy = product["original_price"] - product["price"]
        discount_value = (
            f"de R$ {product['original_price']:.2f} por R$ {product['price']:.2f} "
            f"({product['discount']}% OFF — economia de R$ {economy:.2f})"
        )
    else:
        discount_value = f"R$ {product['price']:.2f}"

    prompt = f"""Você é especialista em grupos de ofertas do Telegram brasileiro.

Crie uma mensagem CURTA e DIRETA no estilo de grupos de promoções, igual a este exemplo:

EXEMPLO DE FORMATO IDEAL:
---
creatina monohidratada 1kg soldiers nutrition
de R$ 249,90 por 🔥R$ 51,92🔥
selecionem a opção de 1 quilo!!!! 😵🚨
---

PRODUTO:
- Nome: {product['title'][:80]}
- Preço: {discount_value}
- Avaliação: {product['rating']} estrelas

REGRAS OBRIGATÓRIAS:
1. Máximo 4 linhas no total
2. Primeira linha: nome curto e direto do produto (sem marca longa)
3. Segunda linha: preço com emoji de fogo 🔥 no valor final
4. Terceira linha: frase curta de urgência com emojis (😵🚨⚡💥)
5. NUNCA mencione comissão, afiliado ou parceria
6. NUNCA use separadores como ━━━ ou ===
7. NUNCA escreva parágrafos longos
8. Tom informal como amigo passando oferta no grupo

Retorne APENAS JSON válido sem markdown:
{{"emoji": "<emoji principal>", "text": "<mensagem curta em 4 linhas>"}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    return {
        "emoji": result.get("emoji", "🛍️"),
        "text": result.get("text", ""),
        "channel": channel
    }
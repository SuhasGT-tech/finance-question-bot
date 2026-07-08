"""
Sends a digest message to Telegram using the free Bot API.

Setup:
1. Message @BotFather on Telegram -> /newbot -> follow prompts -> get a token
2. Start a chat with your new bot (or add it to a group/channel)
3. Get your chat_id:
   - For personal chat: message the bot, then visit
     https://api.telegram.org/bot<TOKEN>/getUpdates
     and read the "chat":{"id": ...} value
4. Set as env vars / GitHub secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4000  # Telegram limit is 4096, leave some buffer


def format_digest(items: list) -> str:
    if not items:
        return "No new finance questions found this run."

    lines = ["🎥 *New finance questions worth a video:*\n"]
    for i, item in enumerate(items, 1):
        source_tag = {
            "reddit": f"r/{item.get('subreddit', '')}",
            "stocktwits": f"${item.get('symbol', '')}",
            "quora": "Quora",
        }.get(item["source"], item["source"])

        lines.append(
            f"{i}. *[{source_tag}]* {item['title']}\n"
            f"   👍 {item.get('score', 0)} | 💬 {item.get('num_comments', 0)}\n"
            f"   {item['url']}\n"
        )
    return "\n".join(lines)


def send_telegram_digest(items: list):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    text = format_digest(items)

    # Split into chunks if too long
    chunks = [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)] or [text]

    for chunk in chunks:
        resp = requests.post(
            TELEGRAM_API.format(token=token),
            data={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[telegram_notifier] Failed to send message: {resp.text}")

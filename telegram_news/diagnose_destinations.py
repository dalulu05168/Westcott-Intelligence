"""Read-only probe for existing Telegram secret *names* and destination types.

This does not output secret values, chat IDs, usernames, participant metadata,
or API response bodies. Never sends messages or alters Telegram bot settings.
"""
from __future__ import annotations
import os
import requests

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
EXPECTED = "nuvexacheckbot"

def request(method, payload):
    response = requests.post(
        "https://api.telegram.org/bot" + TOKEN + "/" + method,
        json=payload, timeout=12,
    )
    if not response.ok:
        return None, "HTTP_" + str(response.status_code)
    try:
        data = response.json()
    except ValueError:
        return None, "INVALID_RESPONSE"
    if not data.get("ok"):
        return None, "TELEGRAM_REJECTED"
    return data.get("result"), "OK"

def main():
    if not TOKEN:
        print("BOT_TOKEN: MISSING")
        return
    bot, status = request("getMe", {})
    if status != "OK":
        print("BOT_AUTH:", status)
        return
    if not isinstance(bot, dict) or str(bot.get("username", "")).casefold() != EXPECTED:
        print("BOT_IDENTITY: WRONG_BOT")
        return
    print("BOT_IDENTITY: MATCHED")
    for label, key in [
        ("EXISTING_CHAT_SECRET", "TELEGRAM_CHAT_ID"),
        ("PRIVATE_CHAT_SECRET", "TELEGRAM_PRIVATE_CHAT_ID"),
    ]:
        value = (os.getenv(key) or "").strip()
        if not value:
            print(label + ": MISSING")
            continue
        if value.isdigit():
            print(label + ": FORMAT_POSITIVE_NUMBER")
        elif value.startswith("-") and value[1:].isdigit():
            print(label + ": FORMAT_NEGATIVE_NUMBER")
        else:
            print(label + ": FORMAT_NONNUMERIC")
        chat, result = request("getChat", {"chat_id": value})
        if result != "OK":
            print(label + ": DESTINATION_" + result)
            continue
        kind = chat.get("type") if isinstance(chat, dict) else None
        if kind == "private":
            print(label + ": TELEGRAM_TYPE_PRIVATE")
        elif kind in ("group", "supergroup"):
            print(label + ": TELEGRAM_TYPE_GROUP")
        elif kind == "channel":
            print(label + ": TELEGRAM_TYPE_CHANNEL")
        else:
            print(label + ": TELEGRAM_TYPE_UNKNOWN")
    print("NO_MESSAGES_SENT: TRUE")

if __name__ == "__main__":
    main()

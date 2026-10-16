"""Manual private Telegram bot discovery and delivery verification. Never prints bot tokens."""
import os
import sys
from datetime import datetime, timezone

import requests

from main import ensure_private_destination, send_message

SESSION = requests.Session()


def api(token, method, payload):
    response = SESSION.post(
        "https://api.telegram.org/bot" + token + "/" + method,
        json=payload, timeout=20,
    )
    if response.status_code == 409:
        raise RuntimeError("Telegram getUpdates unavailable: bot has an active webhook; do not delete it without permission")
    if not response.ok:
        raise RuntimeError("Telegram API " + method + " HTTP " + str(response.status_code))
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError("Telegram API " + method + " returned not-ok")
    return data["result"]


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN GitHub Actions secret is missing")
    mode = os.getenv("CONNECT_MODE", "discover").strip()
    bot = api(token, "getMe", {})
    print("Connected Telegram bot username: @" + str(bot.get("username", "<not_set>")))
    if mode == "discover":
        updates = api(token, "getUpdates", {"limit": 100, "timeout": 0})
        matches = []
        for event in updates:
            msg = event.get("message", {})
            chat = msg.get("chat", {})
            if (chat.get("type") == "private"
                    and str(msg.get("text", "")).strip().startswith("/start")
                    and str(chat.get("id", "")).isdigit()):
                matches.append((event.get("update_id", 0), chat))
        if not matches:
            print("NO_PRIVATE_START_FOUND: Open your Telegram bot, send /start, then rerun discovery.")
            return
        _, match = max(matches, key=lambda pair: pair[0])
        print("Latest private /start chat_id:", match["id"])
        print("Telegram username, if configured: @" + str(match.get("username", "<unset>")))
        print("Confirm this is your own account before saving the ID as secret TELEGRAM_PRIVATE_CHAT_ID; preserve the original group TELEGRAM_CHAT_ID.")
        print("Discovery does not send a message and does not consume or delete updates.")
    elif mode == "test":
        chat_id = os.getenv("TELEGRAM_PRIVATE_CHAT_ID", "").strip()
        if not chat_id:
            raise RuntimeError("TELEGRAM_PRIVATE_CHAT_ID GitHub Actions secret is missing; never replace the existing group TELEGRAM_CHAT_ID")
        ensure_private_destination(token, chat_id)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        mid = send_message(token, chat_id,
                           "✅ ELLERY WESTCOTT｜Telegram 私人新闻推送连接测试\n"
                           "已通过 Telegram 私聊目标检查。测试时间：" + now
                           + "\n这是一条连接测试，不是财经新闻。")
        print("PRIVATE_TEST_SENT: Telegram acknowledged message_id", mid)
        print("Open your personal Telegram conversation to confirm actual receipt.")
    else:
        raise RuntimeError("Unsupported CONNECT_MODE; choose discover or test")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("CONNECT_ERROR:", str(exc).split("https://")[0][:200], file=sys.stderr)
        raise SystemExit(1)

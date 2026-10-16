"""Read-only dual-country Telegram readiness, aligned with existing group publisher.

Telegram delivery is already configured for the existing '🌐~~~资讯快报' group.
Do not infer that a missing optional private-chat Secret breaks group transport.
Never print Bot token, chat IDs, or Telegram API URLs.
"""
import json
import os
import sys
import requests


def valid_existing_group_id(value):
    """Telegram group chat IDs are typically NEGATIVE integers."""
    return isinstance(value, str) and value.startswith("-") and value[1:].isdigit()


def check_telegram_identity(token):
    if not token:
        return False
    try:
        response = requests.post(
            "https://api.telegram.org/bot" + token + "/getMe", json={}, timeout=18)
        if not response.ok:
            return False
        body = response.json()
        bot = body.get("result") or {}
        return (body.get("ok") is True and bot.get("is_bot") is True
                and str(bot.get("username", "")).casefold() == "nuvexacheckbot")
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return False


def check_existing_group(token, group_id, expected_title):
    """Read-only getChat, independently verify group kind and *exact* title."""
    if not token or not valid_existing_group_id(group_id):
        return False
    try:
        response = requests.post(
            "https://api.telegram.org/bot" + token + "/getChat",
            json={"chat_id": group_id}, timeout=18)
        if not response.ok:
            return False
        body = response.json()
        chat = body.get("result") or {}
        return (body.get("ok") is True and chat.get("type") in ("group", "supergroup")
                and chat.get("title", "").strip() == expected_title)
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return False


def readiness():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    group_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    expected_title = os.getenv("TELEGRAM_EXPECTED_GROUP_TITLE", "🌐~~~资讯快报").strip()
    bot_valid = check_telegram_identity(token)
    checks = {
        "bot_token_present": bool(token),
        "existing_group_chat_secret_present": bool(group_id),
        "existing_group_chat_integer_format": valid_existing_group_id(group_id),
        "telegram_bot_token_accepted": bot_valid,
        "existing_group_chat_type_and_title_verified": (
            bot_valid and check_existing_group(token, group_id, expected_title)),
        "ai_api_key_present": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "ai_model_selected": bool(os.getenv("OPENAI_NEWS_MODEL", "").strip()),
        "licensed_us_index_data_key_present": bool(os.getenv("TWELVE_DATA_API_KEY", "").strip()),
        "official_image_reuse_approved": os.getenv("OFFICIAL_IMAGE_REUSE_APPROVED") == "true",
        "old_single_market_automation_disabled": (
            os.getenv("LEGACY_TELEGRAM_NEWS_ENABLED") != "true"),
        "new_dual_market_automation_enabled": (
            os.getenv("TELEGRAM_DUAL_MARKET_ENABLED") == "true"),
        "new_dual_market_explicit_live_approval": (
            os.getenv("TELEGRAM_DUAL_MARKET_LIVE_APPROVED") == "true"),
    }
    for key, value in checks.items():
        print("READINESS", key, "PASS" if value else "NOT_READY")
    print("OPTIONAL_PRIVATE_CHAT_ID_PRESENT:",
          bool(os.getenv("TELEGRAM_PRIVATE_CHAT_ID", "").strip()))
    print("PUBLICATION_PATH: existing reviewed group publisher; unreviewed direct send blocked")
    if all(checks.values()):
        print("READINESS_RESULT: CONFIG_PRESENT_ONLY; independent source, review and real-news acceptance still required")
    else:
        print("READINESS_RESULT: NOT_READY; do not enable unattended news publishing")
    with open("telegram-readiness.json", "w", encoding="utf-8") as file:
        json.dump(checks, file, indent=2)
    return checks


if __name__ == "__main__":
    try:
        readiness()
    except Exception as exc:
        print("READINESS_PROBE_FAILURE:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)

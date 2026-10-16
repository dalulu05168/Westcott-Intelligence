"""Read-only production readiness checks; never print credentials or chat identifiers."""
import os
import json
import sys
import requests

from main import ensure_private_destination


def check():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    private_chat = os.getenv("TELEGRAM_PRIVATE_CHAT_ID", "").strip()
    ai_key = os.getenv("OPENAI_API_KEY", "").strip()
    ai_model = os.getenv("OPENAI_NEWS_MODEL", "").strip()
    licensed_market_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    image_rights = os.getenv("OFFICIAL_IMAGE_REUSE_APPROVED") == "true"
    legacy = os.getenv("LEGACY_TELEGRAM_NEWS_ENABLED") == "true"
    dual = os.getenv("TELEGRAM_DUAL_MARKET_ENABLED") == "true"
    live_approved = os.getenv("TELEGRAM_DUAL_MARKET_LIVE_APPROVED") == "true"
    checks = {
        "bot_token_present": bool(token),
        "private_chat_secret_present": bool(private_chat),
        "private_chat_is_positive_integer": private_chat.isdigit(),
        "ai_api_key_present": bool(ai_key),
        "ai_model_selected": bool(ai_model),
        "licensed_us_index_data_key_present": bool(licensed_market_key),
        "official_image_reuse_approved": image_rights,
        "old_single_market_automation_disabled": not legacy,
        "new_dual_market_automation_enabled": dual,
        "new_dual_market_explicit_live_approval": live_approved,
    }
    if token:
        try:
            response = requests.post("https://api.telegram.org/bot" + token + "/getMe",
                                     json={}, timeout=18)
            # Do not include Telegram's request URL in exception messages.
            checks["telegram_bot_token_accepted"] = (
                response.ok and response.json().get("ok")
                and response.json().get("result", {}).get("username", "").casefold() == "nuvexacheckbot"
            )
        except (requests.RequestException, ValueError):
            checks["telegram_bot_token_accepted"] = False
    else:
        checks["telegram_bot_token_accepted"] = False
    if checks["telegram_bot_token_accepted"] and private_chat.isdigit():
        try:
            checks["private_chat_is_real_private_destination"] = ensure_private_destination(token, private_chat)
        except (requests.RequestException, RuntimeError, ValueError):
            checks["private_chat_is_real_private_destination"] = False
    else:
        checks["private_chat_is_real_private_destination"] = False
    for key, value in checks.items():
        print("READINESS", key, "PASS" if value else "NOT_READY")
    print("READINESS_RESULT: " + (
        "ALL_PREREQUISITES_PRESENT (still requires a real delivery acceptance test)"
        if all(checks.values()) else "NOT_READY; live sending remains disabled until corrected"))
    with open("telegram-readiness.json", "w", encoding="utf-8") as file:
        json.dump(checks, file, indent=2)
    # Read-only probe: missing credentials are a business blocker, not a CI failure.
    # It must NEVER send a Telegram message, create a webhook, or reveal IDs.


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:
        print("READINESS_PROBE_FAILURE:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)

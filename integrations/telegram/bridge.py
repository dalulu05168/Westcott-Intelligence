"""ELLERY WESTCOTT Telegram group transport. Requires an external verified publisher."""
import argparse
import json
import os
import sys
import uuid
import urllib.error
import urllib.request


class TelegramError(RuntimeError):
    pass


def _required(env, key):
    value = env.get(key, "").strip()
    if not value:
        raise TelegramError("Missing " + key + "; configure in a secure secret store.")
    return value


def call_api(token, method, body=None):
    """Never print the URL; it contains the secret Telegram Bot token."""
    url = "https://api.telegram.org/bot" + token + "/" + method
    data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise TelegramError("Telegram HTTP status " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Ambiguous network failures are NOT retried: sendMessage might have succeeded.
        raise TelegramError("Telegram request failed; delivery status unknown.") from None
    if not isinstance(result, dict) or not result.get("ok"):
        error_code = result.get("error_code", "unknown") if isinstance(result, dict) else "unknown"
        raise TelegramError("Telegram API rejected request (code: " + str(error_code) + ")")
    return result.get("result")


def verify_bot_identity(token, env=None):
    """Fail closed unless the token belongs to the user-selected Bot."""
    env = env if env is not None else os.environ
    expected = env.get("TELEGRAM_EXPECTED_BOT_USERNAME", "NuvexaCheckBot").strip().lstrip("@")
    if not expected:
        raise TelegramError("Missing TELEGRAM_EXPECTED_BOT_USERNAME.")
    account = call_api(token, "getMe")
    if not isinstance(account, dict) or not account.get("is_bot"):
        raise TelegramError("Telegram token does not identify a bot.")
    actual = account.get("username", "")
    if actual.casefold() != expected.casefold():
        raise TelegramError("Bot username mismatch; refusing group access or delivery.")
    return {"id": account.get("id"), "username": actual}


def group_target(token, chat_id, env=None):
    """Verify Telegram's actual destination type and title before sending."""
    env = env if env is not None else os.environ
    expected_title = env.get("TELEGRAM_EXPECTED_GROUP_TITLE", "资讯快报").strip()
    if not expected_title:
        raise TelegramError("Missing TELEGRAM_EXPECTED_GROUP_TITLE.")
    chat = call_api(token, "getChat", {"chat_id": chat_id})
    if not isinstance(chat, dict) or chat.get("type") not in ("group", "supergroup"):
        raise TelegramError("Configured TELEGRAM_CHAT_ID is not a group/supergroup.")
    if chat.get("title", "").strip() != expected_title:
        raise TelegramError("Group title mismatch; refusing delivery to unintended chat.")
    return {"id": chat.get("id"), "title": chat["title"], "type": chat["type"]}


def chunks(text, max_units=3900):
    """Telegram limit is 4096 characters; count UTF-16 units conservatively."""
    section, units = [], 0
    for char in text:
        count = 2 if ord(char) > 0xFFFF else 1
        if units + count > max_units:
            yield "".join(section)
            section, units = [], 0
        section.append(char)
        units += count
    if section:
        yield "".join(section)


def validated_message(message):
    if not isinstance(message, str) or not message.strip():
        raise TelegramError("Message is empty.")
    if not message.lstrip().startswith("===== 资讯助理 ====="):
        raise TelegramError("News message must start with the agreed assistant heading.")
    if "\x00" in message:
        raise TelegramError("Invalid message character.")
    return message.strip()


def send_group_news(message, env=None):
    """Only sends supplied text. Does NOT fetch news or certify any market claim."""
    env = env if env is not None else os.environ
    token = _required(env, "TELEGRAM_BOT_TOKEN")
    chat_id = _required(env, "TELEGRAM_CHAT_ID")
    verify_bot_identity(token, env)
    group = group_target(token, chat_id, env)
    text = validated_message(message)
    thread = env.get("TELEGRAM_MESSAGE_THREAD_ID", "").strip()
    receipts = []
    for part in chunks(text):
        request = {"chat_id": chat_id, "text": part, "disable_notification": False}
        if thread:
            request["message_thread_id"] = int(thread)
        sent = call_api(token, "sendMessage", request)
        if not isinstance(sent, dict) or not isinstance(sent.get("message_id"), int):
            raise TelegramError("No Telegram message_id in response; verify delivery.")
        receipts.append(sent["message_id"])
    return {"group_id": group["id"], "group_title": group["title"],
            "message_ids": receipts, "parts": len(receipts)}


def call_photo_api(token, chat_id, png_bytes, thread=""):
    """Upload an actual PNG as Telegram multipart/form-data; do not log token/URL."""
    if not isinstance(png_bytes, bytes) or not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise TelegramError("Expected PNG image bytes.")
    if len(png_bytes) > 9_000_000:
        raise TelegramError("News image exceeds permitted upload size.")
    boundary = "Westcott" + uuid.uuid4().hex
    fields = {"chat_id": str(chat_id), "disable_notification": "false"}
    if thread:
        fields["message_thread_id"] = str(int(thread))
    segments = []
    for name, value in fields.items():
        segments.append(("--" + boundary + "\r\n"
                         + 'Content-Disposition: form-data; name="' + name + '"\r\n\r\n'
                         + value + "\r\n").encode("utf-8"))
    segments.append(("--" + boundary + "\r\n"
                     + 'Content-Disposition: form-data; name="photo"; filename="westcott-news.png"\r\n'
                     + "Content-Type: image/png\r\n\r\n").encode("ascii")
                    + png_bytes + b"\r\n")
    segments.append(("--" + boundary + "--\r\n").encode("ascii"))
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendPhoto",
        data=b"".join(segments),
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise TelegramError("Telegram photo HTTP status " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise TelegramError("Telegram photo request failed; delivery status unknown.") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise TelegramError("Telegram rejected photo upload.")
    return result.get("result")


def send_group_news_with_image(message, png_bytes, env=None):
    """Photo then reviewed text. Never automatically retry if delivery is ambiguous."""
    env = env if env is not None else os.environ
    token = _required(env, "TELEGRAM_BOT_TOKEN")
    chat_id = _required(env, "TELEGRAM_CHAT_ID")
    verified = validated_message(message)
    verify_bot_identity(token, env)
    group = group_target(token, chat_id, env)
    thread = env.get("TELEGRAM_MESSAGE_THREAD_ID", "").strip()
    photo = call_photo_api(token, chat_id, png_bytes, thread)
    if not isinstance(photo, dict) or not isinstance(photo.get("message_id"), int):
        raise TelegramError("Telegram did not return photo message_id; delivery unknown.")
    ids = []
    for part in chunks(verified):
        body = {"chat_id": chat_id, "text": part, "disable_notification": False}
        if thread:
            body["message_thread_id"] = int(thread)
        sent = call_api(token, "sendMessage", body)
        if not isinstance(sent, dict) or not isinstance(sent.get("message_id"), int):
            raise TelegramError("Telegram did not return text message_id; delivery unknown.")
        ids.append(sent["message_id"])
    return {"group_id": group["id"], "group_title": group["title"],
            "photo_message_id": photo["message_id"], "message_ids": ids,
            "parts": len(ids)}


def send_group_news_from_official_article(message, article_url, image_url=None, env=None):
    """Send reviewed article photo by ORIGINAL URL, or text with article link preview.

    Does not create, edit, download or rehost images. The caller must verify
    source relevance and permission before supplying an image_url.
    """
    env = env if env is not None else os.environ
    token = _required(env, "TELEGRAM_BOT_TOKEN")
    chat_id = _required(env, "TELEGRAM_CHAT_ID")
    verified = validated_message(message)
    verify_bot_identity(token, env)
    group = group_target(token, chat_id, env)
    thread = env.get("TELEGRAM_MESSAGE_THREAD_ID", "").strip()
    photo_id = None
    if image_url:
        request = {"chat_id": chat_id, "photo": image_url, "disable_notification": False}
        if thread:
            request["message_thread_id"] = int(thread)
        photo = call_api(token, "sendPhoto", request)
        if not isinstance(photo, dict) or not isinstance(photo.get("message_id"), int):
            raise TelegramError("Photo delivery status unknown: no Telegram message_id.")
        photo_id = photo["message_id"]
    ids = []
    for i, part in enumerate(chunks(verified)):
        request = {"chat_id": chat_id, "text": part, "disable_notification": False}
        if thread:
            request["message_thread_id"] = int(thread)
        if not image_url and i == 0:
            # Telegram normally renders the site's original og:image preview.
            # Never claim that the publisher exposes or Telegram shows one.
            request["link_preview_options"] = {
                "url": article_url, "is_disabled": False, "prefer_large_media": True
            }
        sent = call_api(token, "sendMessage", request)
        if not isinstance(sent, dict) or not isinstance(sent.get("message_id"), int):
            raise TelegramError("Text delivery status unknown: no Telegram message_id.")
        ids.append(sent["message_id"])
    return {"group_id": group["id"], "group_title": group["title"],
            "photo_message_id": photo_id, "message_ids": ids,
            "image_delivery": "source_photo" if image_url else "article_link_preview",
            "parts": len(ids)}


def discover_groups(env=None):
    env = env if env is not None else os.environ
    token = _required(env, "TELEGRAM_BOT_TOKEN")
    verify_bot_identity(token, env)
    updates = call_api(token, "getUpdates", {"limit": 100, "timeout": 0})
    groups = {}
    for update in updates or []:
        if not isinstance(update, dict):
            continue
        obj = (update.get("message") or update.get("my_chat_member")
               or update.get("channel_post") or {})
        chat = obj.get("chat", {})
        if (chat.get("type") in ("group", "supergroup")
                and chat.get("title", "").strip() == env.get("TELEGRAM_EXPECTED_GROUP_TITLE", "资讯快报").strip()):
            groups[str(chat.get("id"))] = {
                "chat_id": chat["id"], "title": chat.get("title", ""),
                "type": chat["type"]
            }
    return list(groups.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Westcott Telegram group delivery")
    parser.add_argument("command", choices=["discover", "verify", "smoke", "send"])
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            result = {"groups": discover_groups()}
        elif args.command == "verify":
            token = _required(os.environ, "TELEGRAM_BOT_TOKEN")
            identity = verify_bot_identity(token)
            group = group_target(token, _required(os.environ, "TELEGRAM_CHAT_ID"))
            result = {"bot": identity, "group": group}
        elif args.command == "smoke":
            # An explicit test, not a news push.
            result = send_group_news("===== 资讯助理 =====\nELLERY WESTCOTT Telegram 群组连接测试。")
        else:
            # Input supplied by an external human-verified/news-gated publisher.
            result = send_group_news(_required(os.environ, "WESTCOTT_APPROVED_NEWS_TEXT"))
        print(json.dumps({"status": "OK", "result": result}, ensure_ascii=False))
        return 0
    except (TelegramError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

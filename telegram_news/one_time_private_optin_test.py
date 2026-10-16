"""One-time opt-in Telegram PRIVATE connection check; no financial news.

Never sends to a group or channel and never prints chat IDs or Bot token.
Only acts for exactly ONE recent private /start, after bot identity checks.
"""
from __future__ import annotations
from datetime import datetime, timezone
import os
import requests

TOKEN=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
S=requests.Session()

def telegram(method, payload):
    resp=S.post("https://api.telegram.org/bot"+TOKEN+"/"+method,json=payload,timeout=18)
    if not resp.ok:
        raise RuntimeError("TELEGRAM_"+method+"_HTTP_"+str(resp.status_code))
    obj=resp.json()
    if not obj.get("ok"):
        raise RuntimeError("TELEGRAM_"+method+"_REJECTED")
    return obj["result"]

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN_MISSING")
    me=telegram("getMe",{})
    if me.get("username","").casefold()!="nuvexacheckbot" or not me.get("is_bot"):
        raise RuntimeError("BOT_IDENTITY_MISMATCH")
    web=telegram("getWebhookInfo",{})
    if web.get("url"):
        raise RuntimeError("EXISTING_WEBHOOK_PRESENT_STOP")
    updates=telegram("getUpdates",{"limit":100,"timeout":0})
    now=datetime.now(timezone.utc).timestamp()
    selected={}
    for update in updates:
        message=update.get("message") or {}
        chat=message.get("chat") or {}
        sender=message.get("from") or {}
        ident=chat.get("id")
        if (isinstance(ident,int) and ident>0 and chat.get("type")=="private"
                and sender.get("id")==ident and sender.get("is_bot") is False
                and str(message.get("text","")).strip()=="/start"
                and isinstance(message.get("date"),int)
                and 0 <= now-message["date"] <= 48*3600):
            selected[ident]=max(selected.get(ident,0),message["date"])
    print("RECENT_PRIVATE_START_CANDIDATES:",len(selected))
    if len(selected)!=1:
        raise RuntimeError("NOT_EXACTLY_ONE_RECENT_CONSENTING_PRIVATE_START")
    chat_id=next(iter(selected))
    info=telegram("getChat",{"chat_id":chat_id})
    if info.get("type")!="private" or info.get("id")!=chat_id:
        raise RuntimeError("DESTINATION_IS_NOT_VERIFIED_PRIVATE")
    sent=telegram("sendMessage",{
        "chat_id":chat_id,
        "text":"✅ ELLERY WESTCOTT｜Telegram 私人连接测试\n"
               "这是 GitHub 上新建的新闻机器人连接验证消息，不是财经新闻。\n"
               "机器人仅检查了近期唯一的私人 /start 会话；未改动原有群组推送。",
        "disable_web_page_preview":True,
    })
    if sent.get("chat",{}).get("type")!="private" or sent.get("chat",{}).get("id")!=chat_id:
        raise RuntimeError("TELEGRAM_RESPONSE_DESTINATION_MISMATCH")
    msg=sent.get("message_id")
    if not isinstance(msg,int):
        raise RuntimeError("TELEGRAM_MISSING_MESSAGE_ID")
    print("PRIVATE_DELIVERY_TEST_ACKNOWLEDGED: TRUE")
    print("MESSAGE_ID:",msg)
    print("NO_GROUP_DELIVERY: TRUE")
    print("NEWS_DELIVERY: FALSE")
    print("CONFIRM_ACTUAL_RECEIPT_IN_TELEGRAM: REQUIRED")

if __name__=="__main__":
    try:
        main()
    except (RuntimeError,requests.RequestException,ValueError) as exc:
        print("DELIVERY_TEST_FAILED:",type(exc).__name__,str(exc).split("https://")[0][:120])
        raise SystemExit(1)

"""Official-announcement Telegram briefing. Safe by default: titles only, no invented market data."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup

TZ = ZoneInfo("Europe/Bucharest")
BVB_URL = "https://bvb.ro/AboutUs/MediaCenter/PressReleases"
FEEDS = {
    "ECB": "https://www.ecb.europa.eu/rss/press.html",
    "FED": "https://www.federalreserve.gov/feeds/press_all.xml",
}
SLOTS = {
    "35 7 * * 1-5": ("N01", "全天备料", "07:50", "07:35"),
    "45 7 * * 1-5": ("N02", "上午开群", "08:00", "07:45"),
    "0 9 * * 1-5": ("N03", "盘前观察", "09:15", "09:00"),
    "30 9 * * 1-5": ("N04", "集合竞价", "09:45", "09:30"),
    "45 9 * * 1-5": ("N05", "开盘观察", "10:00", "09:45"),
    "15 11 * * 1-5": ("N06", "午间资讯", "11:30", "11:15"),
    "45 13 * * 1-5": ("N07", "国际财经", "14:00", "13:45"),
    "45 15 * * 1-5": ("N08", "欧美联动", "16:00", "15:45"),
    "30 17 * * 1-5": ("N09", "BVB尾盘", "17:45", "17:30"),
    "45 19 * * 1-5": ("N10", "晚间课程备料", "20:00", "19:45"),
    "45 20 * * 1-5": ("N11", "互动问答备料", "21:00", "20:45"),
    "45 21 * * 1-5": ("N12", "收尾作业备料", "22:00", "21:45"),
}
LABELS = {details[0]: details for details in SLOTS.values()}
LABELS["RADAR"] = ("RADAR", "重大公告雷达", "实时检查", "每小时:15")
LOCAL = {"N03", "N04", "N05", "N09"}
INTERNATIONAL = {"N07", "N08"}
PRIORITY = re.compile(
    r"\b(rate|rates|interest|monetary|inflation|cpi|employment|"
    r"earnings|results|financial|profit|merger|acquisition|"
    r"dob[aâ]nd|infla[tț]i|rezultat|fuziune|achizi[tț]i|"
    r"dividend|bilan[tț]|politic[aă] monetar[aă])\b", re.I
)
USER_AGENT = "Westcott-Intelligence-Telegram/1.0 (official-announcements-only)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def normalize(s):
    return " ".join(str(s).split())


def item(source, title, url, published):
    title = normalize(title)
    if not title or not url.startswith("https://") or published is None:
        return None
    if published.tzinfo is None:
        return None
    return {
        "id": hashlib.sha256((source + "|" + url.split("#")[0]).encode()).hexdigest()[:24],
        "source": source, "title": title[:300],
        "url": url.split("#")[0], "published": published.isoformat(),
    }


def retrieve(url):
    response = SESSION.get(url, timeout=18)
    response.raise_for_status()
    return response.content


def fetch_bvb():
    """BVB site is authoritative for the original press-release headline/date."""
    soup = BeautifulSoup(retrieve(BVB_URL), "html.parser")
    urls = []
    seen = set()
    for a in soup.select('a[href*="/AboutUs/MediaCenter/PressItem/"]'):
        href = urljoin(BVB_URL, a.get("href", ""))
        host = urlparse(href).hostname or ""
        if host not in {"bvb.ro", "www.bvb.ro"} or href in seen:
            continue
        seen.add(href)
        urls.append(href)
        if len(urls) >= 10:
            break
    results = []
    for url in urls:
        try:
            page = BeautifulSoup(retrieve(url), "html.parser")
            heading = page.select_one("h1")
            if not heading:
                continue
            title = heading.get_text(" ", strip=True)
            # Match date next to the article title, not dates deep in the article.
            body_text = page.get_text(" ", strip=True)
            idx = body_text.find(title)
            nearby = body_text[idx + len(title):idx + len(title) + 160] if idx >= 0 else ""
            found = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", nearby)
            if not found:
                continue
            day, month, year = map(int, found.groups())
            published = datetime(year, month, day, tzinfo=TZ)
            parsed = item("BVB", title, url, published)
            if parsed:
                results.append(parsed)
        except (requests.RequestException, ValueError) as exc:
            print("BVB article skipped:", type(exc).__name__)
    return results


def fetch_feed(source, url):
    """Official RSS / Atom announcements; copy official title, do not infer facts."""
    feed = feedparser.parse(retrieve(url))
    if feed.bozo and not feed.entries:
        raise ValueError("RSS parse failed")
    results = []
    for entry in feed.entries[:35]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        host = urlparse(link).hostname or ""
        trusted = {"ECB": ("ecb.europa.eu",), "FED": ("federalreserve.gov",)}
        if not any(host == d or host.endswith("." + d) for d in trusted[source]):
            continue
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        if not stamp:
            continue
        published = datetime(*stamp[:6], tzinfo=timezone.utc).astimezone(TZ)
        parsed = item(source, title, link, published)
        if parsed:
            results.append(parsed)
    return results


def collect():
    records = []
    errors = []
    sources_ok = []
    for source, url in [("BVB", BVB_URL), *FEEDS.items()]:
        try:
            articles = fetch_bvb() if source == "BVB" else fetch_feed(source, url)
            records.extend(articles)
            sources_ok.append(source)
            print("Source", source, "records", len(articles))
        except (requests.RequestException, ValueError) as exc:
            errors.append(source)
            print("Source unavailable", source, type(exc).__name__)
    return records, sources_ok, errors


def recent(records, now, node, seen):
    freshness = 4 if node == "RADAR" else (48 if node == "N02" else 30)
    chosen = []
    for record in records:
        stamp = datetime.fromisoformat(record["published"])
        if record["id"] in seen or stamp > now + timedelta(minutes=15):
            continue
        if now - stamp > timedelta(hours=freshness):
            continue
        if node in LOCAL and record["source"] != "BVB":
            continue
        if node == "RADAR" and not PRIORITY.search(record["title"]):
            continue
        chosen.append(record)
    def rank(r):
        source_score = (r["source"] in {"ECB", "FED"}) if node in INTERNATIONAL else (r["source"] == "BVB")
        return (source_score, r["published"])
    return sorted(chosen, key=rank, reverse=True)[:2]


def get_state(token, repo):
    if not token or not repo:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY required for live delivery")
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    base = "https://api.github.com/repos/" + repo
    name = "telegram-news-state"
    ref = SESSION.get(base + "/git/ref/heads/" + name, headers=headers, timeout=15)
    if ref.status_code == 404:
        main = SESSION.get(base + "/git/ref/heads/main", headers=headers, timeout=15)
        main.raise_for_status()
        creation = SESSION.post(base + "/git/refs", headers=headers, timeout=15, json={
            "ref": "refs/heads/" + name, "sha": main.json()["object"]["sha"]
        })
        if creation.status_code not in (201, 422):
            creation.raise_for_status()
    elif not ref.ok:
        ref.raise_for_status()
    path = "/contents/.telegram-news-delivery-state.json?ref=" + name
    response = SESSION.get(base + path, headers=headers, timeout=15)
    if response.status_code == 404:
        return {"sent": {}, "empty": {}}, None, (base, headers, name)
    response.raise_for_status()
    data = response.json()
    saved = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    if not isinstance(saved.get("sent"), dict) or not isinstance(saved.get("empty"), dict):
        raise ValueError("Invalid persisted state; refusing to reset it")
    return saved, data["sha"], (base, headers, name)


def save_state(state, sha, target):
    base, headers, branch = target
    state["sent"] = dict(list(state["sent"].items())[-500:])
    state["empty"] = dict(list(state["empty"].items())[-90:])
    payload = {"branch": branch, "message": "telegram-news: record successful delivery",
               "content": base64.b64encode(
                   (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
               ).decode()}
    if sha:
        payload["sha"] = sha
    response = SESSION.put(base + "/contents/.telegram-news-delivery-state.json",
                           headers=headers, json=payload, timeout=20)
    response.raise_for_status()


def build_message(node, records, now):
    code, label, official, advance = LABELS[node]
    if node == "RADAR":
        heading = "📡 ELLERY WESTCOTT｜重大公告雷达"
    else:
        heading = f"📰 ELLERY WESTCOTT｜{code} {label}"
    lines = [heading, f"罗马尼亚时间：{now:%Y-%m-%d %H:%M}",
             f"正式节点：{official}｜准备节点：{advance}", "",
             "官方公告原标题（仅报道原文标题，不含实时行情）："]
    for index, record in enumerate(records, 1):
        date = datetime.fromisoformat(record["published"]).strftime("%Y-%m-%d")
        lines += [f"{index}. [{record['source']}] {record['title']}",
                  f"发布时间日期：{date}", record["url"], ""]
    if node in LOCAL:
        lines.append("未接入经验证的实时竞价/成交数据，不提供当下价量结论。")
    if node in {"N10", "N11", "N12"}:
        lines.append("以上仅供晚课选题参考；不代表Jonathan课程或正式作业。")
    return "\n".join(lines).strip()[:4096]


def ensure_private_destination(token, chat_id):
    """Fail closed: this news bot may deliver only to an individual private chat."""
    if not str(chat_id).strip().isdigit():
        raise RuntimeError("PRIVATE_ONLY: a numeric private chat ID is required")
    response = SESSION.post(
        "https://api.telegram.org/bot" + token + "/getChat",
        json={"chat_id": str(chat_id)}, timeout=20)
    if response.status_code != 200:
        raise RuntimeError("Telegram private-chat check HTTP " + str(response.status_code))
    data = response.json()
    if not data.get("ok") or data.get("result", {}).get("type") != "private":
        raise RuntimeError("PRIVATE_ONLY: destination is not a private Telegram chat")
    if str(data["result"].get("id")) != str(chat_id):
        raise RuntimeError("PRIVATE_ONLY: destination ID mismatch")
    return True


def send_message(token, chat_id, message):
    raise RuntimeError("Headline-only delivery is disabled; use a reviewed evidence ledger with integrations/telegram/reviewed_publish.py")


def run():
    now = datetime.now(TZ)
    cron = os.getenv("EVENT_SCHEDULE", "").strip()
    node = os.getenv("NODE_INPUT", "").strip() or (
        "RADAR" if cron == "15 * * * *" else SLOTS.get(cron, ("",))[0]
    )
    if node not in LABELS:
        raise ValueError("Unknown node or unmatched schedule: " + str(cron))
    dry_run = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
    if not dry_run:
        raise RuntimeError("Headline-only delivery is disabled; use a reviewed evidence ledger")
    if cron and node != "RADAR" and not dry_run:
        # Skip stale scheduled events; do not send yesterday's briefing as today's.
        planned = LABELS[node][3]
        hour, minute = [int(n) for n in planned.split(":")]
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if abs((now - scheduled).total_seconds()) > 75 * 60:
            print("Skipped stale scheduled workflow:", node)
            return
    records, ok_sources, failed_sources = collect()
    print("Node:", node, "time:", now.isoformat(), "working_sources:", ok_sources,
          "failed_sources:", failed_sources)
    if node == "N01":
        print("Internal preparation only; no Telegram message.")
        return
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not dry_run and (not token or not chat):
        raise RuntimeError("Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as GitHub secrets")
    if dry_run:
        state, sha, target = {"sent": {}, "empty": {}}, None, None
    else:
        state, sha, target = get_state(os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_REPOSITORY"))
    selected = recent(records, now, node, state["sent"])
    if not selected:
        if node == "N06" and ok_sources:
            empty_key = now.strftime("%Y-%m-%d") + "|N06"
            if empty_key not in state["empty"]:
                message = (f"📰 ELLERY WESTCOTT｜N06 午间资讯\n罗马尼亚时间：{now:%Y-%m-%d %H:%M}\n"
                           "本轮官方来源中暂无可核实且未推送的新公告；不编造行情或补凑旧闻。")
                if dry_run:
                    print("DRY RUN\n" + message)
                else:
                    mid = send_message(token, chat, message)
                    state["empty"][empty_key] = {"message_id": mid, "at": now.isoformat()}
                    save_state(state, sha, target)
            return
        print("No publishable new official announcements; no message sent.")
        return
    message = build_message(node, selected, now)
    if dry_run:
        print("DRY RUN\n" + message)
        return
    mid = send_message(token, chat, message)
    for record in selected:
        state["sent"][record["id"]] = {
            "node": node, "message_id": mid, "at": now.isoformat(),
            "url": record["url"],
        }
    save_state(state, sha, target)
    print("Telegram acknowledged message_id:", mid, "node:", node,
          "articles:", len(selected))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        # Never print exception URLs or payloads that could contain bot credentials.
        print("ERROR", type(exc).__name__, str(exc).split("https://")[0][:180], file=sys.stderr)
        raise SystemExit(1)


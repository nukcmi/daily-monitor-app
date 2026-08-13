"""
Google News RSS 수집. 키 불필요.

한 종목당 keywords 리스트를 OR 로 묶어 조회하고,
최근 N일 내 기사만 남긴다.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import requests

RSS = "https://news.google.com/rss/search"


def fetch_news(keywords: list[str], days: int = 4, lang: str = "ko",
               limit: int = 5) -> list[dict]:
    if not keywords:
        return []
    q = " OR ".join(f'"{k}"' for k in keywords)
    params = {"q": q, "hl": lang,
              "gl": "KR" if lang == "ko" else "US",
              "ceid": f"{'KR:ko' if lang == 'ko' else 'US:en'}"}
    url = f"{RSS}?{urllib.parse.urlencode(params)}"
    r = requests.get(url, timeout=15,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    root = ElementTree.fromstring(r.content)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        try:
            dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").replace(
                tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        if dt < cutoff:
            continue
        src = title.rsplit(" - ", 1)[-1] if " - " in title else ""
        out.append({
            "date": dt.strftime("%m/%d"),
            "title": title.rsplit(" - ", 1)[0] if src else title,
            "url": link, "source": src or "뉴스",
        })
        if len(out) >= limit:
            break
    return out

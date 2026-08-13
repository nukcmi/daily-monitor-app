"""
SEC EDGAR 공시 수집 (미국 종목).

CIK는 config에 직접 넣는다 (LMND = 0001691421).
SEC는 User-Agent에 연락처를 요구한다.
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

UA = {"User-Agent": "Hanwha Strategy Monitor (contact@example.com)"}

WATCH = {"8-K", "10-Q", "10-K", "S-1", "424B4", "SC 13D", "SC 13G"}


def fetch_filings(cik: str, days: int = 3) -> list[dict]:
    cik10 = str(cik).zfill(10)
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik10}.json",
                     headers=UA, timeout=15)
    r.raise_for_status()
    recent = r.json().get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    cutoff = date.today() - timedelta(days=days)

    out = []
    for i, form in enumerate(forms[:40]):
        try:
            d = date.fromisoformat(dates[i])
        except Exception:
            continue
        if d < cutoff or form not in WATCH:
            continue
        acc = accs[i].replace("-", "")
        out.append({
            "date": dates[i],
            "title": f"{form} 제출",
            "url": (f"https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik)}/{acc}/{docs[i]}"),
            "source": "SEC",
        })
    return out

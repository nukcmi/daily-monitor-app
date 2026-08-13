"""
DART 전자공시 수집 (국내 종목)

DART API는 종목코드(6자리)가 아니라 고유번호(corp_code, 8자리)를 쓴다.
매핑표는 CORPCODE.xml.zip 한 번 받아 캐싱한다.

환경변수: DART_API_KEY
"""
from __future__ import annotations

import io
import os
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree

import requests

BASE = "https://opendart.fss.or.kr/api"
_CORP_MAP: dict[str, str] | None = None


def _key() -> str:
    k = os.environ.get("DART_API_KEY", "").strip()
    if not k:
        raise RuntimeError("DART_API_KEY 미설정")
    return k


def _corp_map() -> dict[str, str]:
    """{종목코드: 고유번호}"""
    global _CORP_MAP
    if _CORP_MAP is not None:
        return _CORP_MAP
    r = requests.get(f"{BASE}/corpCode.xml", params={"crtfc_key": _key()}, timeout=30)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml = z.read(z.namelist()[0])
    root = ElementTree.fromstring(xml)
    m = {}
    for c in root.iter("list"):
        stock = (c.findtext("stock_code") or "").strip()
        corp = (c.findtext("corp_code") or "").strip()
        if stock and stock != " " and corp:
            m[stock] = corp
    _CORP_MAP = m
    return m


def fetch_disclosures(stock_code: str, days: int = 7) -> list[dict]:
    """최근 N일 공시. [{date, title, url}]"""
    corp = _corp_map().get(stock_code)
    if not corp:
        return []
    end = date.today()
    start = end - timedelta(days=days)
    r = requests.get(f"{BASE}/list.json", params={
        "crtfc_key": _key(), "corp_code": corp,
        "bgn_de": start.strftime("%Y%m%d"), "end_de": end.strftime("%Y%m%d"),
        "page_count": 30,
    }, timeout=15)
    r.raise_for_status()
    d = r.json()
    if d.get("status") not in ("000", "013"):      # 013 = 조회 결과 없음
        raise RuntimeError(f"DART {d.get('status')}: {d.get('message')}")
    out = []
    for x in d.get("list", []):
        rcp = x.get("rcept_no", "")
        out.append({
            "date": x.get("rcept_dt", ""),
            "title": x.get("report_nm", "").strip(),
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp}",
            "source": "DART",
        })
    return out

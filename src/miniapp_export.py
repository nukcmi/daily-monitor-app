"""
Mini App(daily-monitor-app)이 읽을 JSON 페이로드 조립.
"""
from __future__ import annotations

import re

from model import (Row, big_local, krw_big, krw_sub, market_close_caption,
                   money, pct, vol_fmt)

_GRADE = {"high": "A", "mid": "B", "low": "C"}


def _sanitize(text: str, term_map: dict[str, str]) -> str:
    """hide_terms(예: 'Lemonade')를 표시명(예: '루멘')으로 치환.
    analyze.py는 AI가 만드는 headline/bullets/checkpoints만 치환하므로,
    원문 그대로 노출되는 sources 제목은 여기서 별도로 한 번 더 치환한다."""
    if not text:
        return text
    for term, name in term_map.items():
        text = re.sub(re.escape(term), name, text, flags=re.IGNORECASE)
    return text


def _kpi_row(r: Row) -> list[list]:
    """8개 지표. 외화면 각 금액 항목에 원화 환산을 sub로 덧붙인다."""
    is_krw = r.currency == "KRW"

    close_sub = None if is_krw else krw_sub(r.close_krw)
    cost_sub = (None if is_krw or not r.held
               else krw_sub(r.avg_cost_krw, r.acq_label))
    mcap_sub = None if is_krw else krw_big(r.mktcap_krw)

    vr = r.vol_ratio
    vol_txt = vol_fmt(r.volume)
    if vr:
        vol_txt = f"{vol_txt} · {vr:.2f}x"

    return [
        ["종가", money(r.close, r.currency), close_sub],
        ["취득가", money(r.avg_cost, r.currency) if r.held else "-", cost_sub],
        ["취득가대비", pct(r.vs_cost), None],
        ["전일대비", pct(r.vs_prev), None],
        ["전주대비", pct(r.vs_week), None],
        ["거래량(20일比)", vol_txt, None],
        ["시가총액", big_local(r.mktcap_local, r.currency), mcap_sub],
        ["52주 고점대비", pct(r.vs_52w_high), None],
    ]


def build_payload(rows: list[Row], analysis: dict, items_by_code: dict[str, dict],
                  as_of: str, updated: str, fx_line: str = "",
                  raw_items_by_code: dict[str, list[dict]] | None = None) -> dict:
    raw_items_by_code = raw_items_by_code or {}
    companies = []
    attention = None
    name_to_url = {}   # 이벤트의 회사명 → 원문 URL 매칭용 폴백

    for r in rows:
        sig = analysis.get("signals", {}).get(r.code, {})
        level = sig.get("level", "low")
        grade = _GRADE.get(level, "C")
        headline = sig.get("headline", "주요 변동 없음")
        bullets = sig.get("bullets") or ["공시·기사 기준 특이사항 없음"]
        checkpoints = sig.get("checkpoints", [])
        item = items_by_code.get(r.code, {})

        term_map = {term: r.name for term in item.get("hide_terms", [])}

        raw_items = raw_items_by_code.get(r.code, [])
        source_url = raw_items[0]["url"] if raw_items else None
        name_to_url[r.name] = source_url
        sources = [
            {"title": _sanitize(it["title"], term_map), "url": it["url"],
             "source": it.get("source", ""), "date": it.get("date", "")}
            for it in raw_items[:4]
        ]

        tags = [pct(r.vs_prev)]
        if r.tag:
            tags.append(r.tag)

        companies.append({
            "id": r.code,
            "name": r.name,
            "ticker": r.sub or r.code,          # 실제 ticker 아님. 표시용 구분자만
            "g": grade,
            "event": headline,
            "tags": tags[:3],
            "priceText": money(r.close, r.currency),   # 카드 상단 "현재가" 라벨용
            "thesis": item.get("role", headline),
            "kpis": _kpi_row(r),
            "cardKpis": item.get("cardKpis", []),   # 카드에 크게 보일 지표 2개 (config 관리)
            "events": bullets,
            "watch": checkpoints,
            "spark": [{"date": f"{d.month}/{d.day}", "close": round(v, 4)}
                     for d, v in r.spark],
            "avgCost": r.avg_cost,
            "currency": r.currency,
            "exchangeLine": market_close_caption(r.quote_date, r.market),  # "KRX · 8/12 종가" 등
            "sourceUrl": source_url,   # 최신 원문(공시·기사) 링크. 없으면 null
            "sources": sources,        # 원문 목록(제목·링크·출처). 각 항목이 실제 기사/공시로 연결
        })

        if grade == "A" and attention is None:
            attention = {"company": r.name, "text": bullets[0], "url": source_url}

    if attention is None:
        evs = analysis.get("events", [])
        if evs:
            ev_name = evs[0].get("name", "")
            attention = {"company": ev_name, "text": evs[0].get("summary", ""),
                        "url": name_to_url.get(ev_name)}
        else:
            attention = {"company": "-", "text": "금일 특이 이벤트 없음", "url": None}

    return {
        "asOf": as_of,
        "updated": updated,
        "fx": fx_line,
        "attention": attention,
        "companies": companies,
    }

"""
표 데이터 모델 및 파생지표 계산.

컬럼: 종목 | 추세 | 취득가 | 종가 | 취득가대비 | 전일대비 | 전주대비
      | 거래량 | 거래량(20일 평균대비) | 시가총액 | 52주 고점대비
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence

FX = {"KRW": 1.0, "USD": 1385.0, "IDR": 0.0855}

_MARKET_TZ = {
    "KRX": ("Asia/Seoul", "15:30"),
    "KOSPI": ("Asia/Seoul", "15:30"),
    "KOSDAQ": ("Asia/Seoul", "15:30"),
    "NYSE": ("America/New_York", "16:00"),
    "NASDAQ": ("America/New_York", "16:00"),
    "IDX": ("Asia/Jakarta", "16:00"),
}
_EXCHANGE_LABEL = {
    "KRX": "KRX", "KOSPI": "KRX", "KOSDAQ": "KRX",
    "NYSE": "NYSE", "NASDAQ": "NASDAQ", "IDX": "IDX",
}
_TZ_SUFFIX = {  # 국내는 시차 설명이 불필요해 괄호를 안 붙인다
    "NYSE": "ET", "NASDAQ": "ET", "IDX": "WIB",
}


def market_close_caption(quote_date, market: str | None) -> str:
    """카드에 표시할 '거래소 · 종가 기준일' 한 줄.
    시차 때문에 '오늘 종가'처럼 보여도 실제로는 하루이틀 전 마감일 수 있어
    거래소별 최근 마감일을 명시한다. 국내·해외 모두 동일 형식을 쓴다.
    예: "KRX · 8/12 종가", "NYSE · 8/12 종가 (ET)", "IDX · 8/12 종가 (WIB)"
    """
    if not quote_date or not market or market.upper() not in _MARKET_TZ:
        return ""
    label = _EXCHANGE_LABEL[market.upper()]
    suffix = _TZ_SUFFIX.get(market.upper())
    base = f"{label} · {quote_date.month}/{quote_date.day} 종가"
    return f"{base} ({suffix})" if suffix else base

TAG_STYLE = {          # 뱃지 라벨 → CSS 클래스
    "당사 투자": "own",
    "벤치마크": "bench",
    "관계사": "affil",
    "자회사": "affil",
    "관심종목": "watch",
}


@dataclass
class Row:
    code: str
    name: str
    ticker: str
    currency: str
    tag: str
    sub: str                       # 종목명 아래 보조 설명 (국가 등)
    avg_cost: float | None
    close: float
    prev_close: float
    week_ref_close: float
    open: float
    high: float
    low: float
    volume: float | None
    vol_avg20: float | None
    high_52w: float | None
    mktcap_krw: float
    mktcap_local: float = 0.0
    acq_fx: float | None = None      # 취득 당시 환율 (현지통화 1단위당 원)
    acq_label: str = ""              # 취득 시점 표기 (예 "23.3월")
    market: str | None = None        # KRX/NYSE/NASDAQ/IDX 등
    quote_date: object = None        # 종가가 속한 거래일 (date)
    spark: Sequence[tuple] = field(default_factory=list)

    @property
    def held(self) -> bool:
        return self.avg_cost is not None

    @property
    def vs_cost(self) -> float | None:
        return None if not self.held else self.close / self.avg_cost - 1

    @property
    def vs_prev(self) -> float:
        return self.close / self.prev_close - 1

    @property
    def vs_week(self) -> float:
        return self.close / self.week_ref_close - 1

    @property
    def close_krw(self) -> float:
        return self.close * FX[self.currency]

    @property
    def avg_cost_krw(self) -> float | None:
        """취득가의 원화 환산. acq_fx(취득 당시 환율)가 있으면 그것을 쓴다."""
        if not self.held:
            return None
        fx = self.acq_fx if self.acq_fx else FX[self.currency]
        return self.avg_cost * fx

    @property
    def vol_ratio(self) -> float | None:
        """당일 거래량 / 20일 평균. 1.0 = 평소 수준"""
        if not self.volume or not self.vol_avg20:
            return None
        return self.volume / self.vol_avg20

    @property
    def vs_52w_high(self) -> float | None:
        if not self.high_52w:
            return None
        return self.close / self.high_52w - 1


def week_ref_close(hist: Sequence[dict], mode: str = "last_week_close") -> float:
    """hist: fetch_history 결과(최신순)"""
    if mode == "t_minus_5":
        return hist[min(5, len(hist) - 1)]["close"]
    today = hist[0]["date"]
    this_monday = today - timedelta(days=today.weekday())
    for r in hist:
        if r["date"] < this_monday:
            return r["close"]
    return hist[-1]["close"]


def build_row(item: dict, quote: dict, hist: Sequence[dict],
              week_mode: str = "last_week_close") -> Row:
    cur = item["currency"]
    hid = item.get("id", item.get("code"))

    vols = [r["volume"] for r in hist[1:21] if r["volume"]]
    highs = [r["high"] for r in hist[:252] if r["high"]]

    return Row(
        code=hid,
        name=item["name"],
        ticker=item.get("ticker", hid),
        currency=cur,
        tag=item.get("tag", "관심종목"),
        sub=item.get("sub", ""),
        avg_cost=item.get("avg_cost"),
        close=quote["close"],
        prev_close=quote["prev_close"],
        week_ref_close=week_ref_close(hist, week_mode),
        open=quote["open"],
        high=quote["high"],
        low=quote["low"],
        volume=quote.get("volume"),
        vol_avg20=(sum(vols) / len(vols)) if vols else None,
        high_52w=max(highs) if highs else None,
        mktcap_krw=quote["mktcap_local"] * FX[cur],
        mktcap_local=quote["mktcap_local"],
        acq_fx=item.get("acq_fx"),
        acq_label=item.get("acq_label", ""),
        market=item.get("market"),
        quote_date=quote.get("date"),
        spark=[(r["date"], r["close"]) for r in reversed(hist[:63])],   # 약 3개월
    )


# ── 포맷터 ────────────────────────────────────────────────
SYM = {"KRW": "₩", "USD": "$", "IDR": "Rp"}


def money(v: float | None, cur: str) -> str:
    if v is None:
        return "-"
    dec = 2 if cur == "USD" else 0
    return f"{SYM[cur]}{v:,.{dec}f}"


def pct(v: float | None) -> str:
    return "-" if v is None else f"{v * 100:+.2f}%"


def vol_fmt(v: float | None) -> str:
    if not v:
        return "-"
    if v >= 1e8:
        return f"{v/1e8:.2f}억"
    if v >= 1e4:
        return f"{v/1e4:.2f}만"
    if v >= 1e3:
        return f"{v/1e3:.2f}천"
    return f"{v:,.0f}"


def big_local(v: float, cur: str) -> str:
    """현지통화 기준 대금액. 달러는 억 달러, 루피아는 조 루피아 단위."""
    if not v:
        return "-"
    if cur == "KRW":
        return krw_big(v)
    if cur == "USD":
        if v >= 1e9:
            return f"${v/1e9:,.2f}B"
        if v >= 1e6:
            return f"${v/1e6:,.1f}M"
        return f"${v:,.0f}"
    if cur == "IDR":
        if v >= 1e12:
            return f"Rp{v/1e12:,.1f}조"
        return f"Rp{v/1e8:,.0f}억"
    return f"{v:,.0f}"


def krw_sub(v: float | None, label: str = "") -> str:
    """보조 표기용 원화. 소액은 원 단위, 대금액은 억/조."""
    if v is None:
        return ""
    if abs(v) >= 1e8:
        body = krw_big(v)
    elif abs(v) >= 1000:
        body = f"₩{v:,.0f}"
    else:
        body = f"₩{v:,.1f}"
    return f"{body} · {label}" if label else body


def krw_big(v: float) -> str:
    if not v:
        return "-"
    if v >= 1e12:
        return f"{v/1e12:.2f}조"
    return f"{v/1e8:,.0f}억"

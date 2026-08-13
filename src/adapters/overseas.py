"""
해외/국내 시세 어댑터 (yfinance 단일 소스)

핵심 원칙: 장이 아직 끝나지 않은 당일 봉은 "종가"로 쓰지 않는다.
yfinance는 장중에도 그날 봉을 실시간 변동값으로 채워서 돌려주는데,
이걸 그대로 쓰면 조회 시점마다 숫자가 달라지고 "종가"라는 라벨과
실제 값(장중 변동가)이 어긋난다. → 시장별 마감시각을 기준으로,
그 거래일이 실제로 마감됐는지 확인한 뒤에만 최신 봉으로 인정한다.
아직 마감 전이면 그 직전(=전일 마감) 봉을 최신으로 취급한다.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import yfinance as yf

_SUFFIX = {"IDX": ".JK", "KOSPI": ".KS", "KOSDAQ": ".KQ"}

# 시장별 (시간대, 정규장 마감시각). 목록에 없는 시장은 항상 마감된 것으로 간주.
_MARKET_CLOSE = {
    "KRX": ("Asia/Seoul", time(15, 30)),
    "KOSPI": ("Asia/Seoul", time(15, 30)),
    "KOSDAQ": ("Asia/Seoul", time(15, 30)),
    "NYSE": ("America/New_York", time(16, 0)),
    "NASDAQ": ("America/New_York", time(16, 0)),
    "IDX": ("Asia/Jakarta", time(16, 0)),
}


def _resolve(symbol: str, market: str | None = None) -> str:
    if "." in symbol:
        return symbol
    if market and market.upper() in _SUFFIX:
        return symbol + _SUFFIX[market.upper()]
    return symbol


def _is_session_closed(bar_date: date, market: str | None) -> bool:
    """해당 거래일의 정규장이 '지금' 시점 기준으로 이미 끝났는지."""
    if not market or market.upper() not in _MARKET_CLOSE:
        return True  # 매핑 없는 시장은 필터링하지 않음
    tz_name, close_t = _MARKET_CLOSE[market.upper()]
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    close_dt = datetime.combine(bar_date, close_t, tzinfo=tz)
    return now_local >= close_dt


def _drop_unclosed(h, market: str | None):
    """장중 실시간으로 채워지는 당일 미마감 봉을 제거."""
    if h.empty:
        return h
    last_date = h.index[-1].date()
    if not _is_session_closed(last_date, market):
        h = h.iloc[:-1]
    return h


def _market_cap(t) -> float:
    fi = getattr(t, "fast_info", None)
    for key in ("market_cap", "marketCap"):
        try:
            v = fi[key] if fi is not None else None
            if v:
                return float(v)
        except Exception:
            pass
    try:
        v = t.info.get("marketCap")
        if v:
            return float(v)
    except Exception:
        pass
    try:
        shares, price = fi["shares"], fi["last_price"]
        if shares and price:
            return float(shares) * float(price)
    except Exception:
        pass
    return 0.0


def fetch_history(symbol: str, n: int = 260, market: str | None = None) -> list[dict]:
    """최신순 정렬. [{date, close, high, low, volume}, ...]
    미마감 당일 봉은 제외 — 항상 '완결된' 거래일만 포함한다."""
    h = yf.Ticker(_resolve(symbol, market)).history(period="2y", interval="1d")
    h = h[h["Close"].notna()]
    h = _drop_unclosed(h, market)
    if h.empty:
        raise RuntimeError(f"시세 없음: {symbol}")
    rows = [{
        "date": i.date(),
        "close": float(r["Close"]),
        "high": float(r["High"]),
        "low": float(r["Low"]),
        "volume": float(r["Volume"]) if r["Volume"] == r["Volume"] else 0.0,
    } for i, r in h.iterrows()]
    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:n]


def fetch_quote(symbol: str, market: str | None = None) -> dict:
    t = yf.Ticker(_resolve(symbol, market))
    h = t.history(period="5d", interval="1d")
    h = h[h["Close"].notna()]
    h = _drop_unclosed(h, market)
    if h.empty:
        raise RuntimeError(f"시세 없음: {symbol}")
    last = h.iloc[-1]
    prev = h.iloc[-2] if len(h) > 1 else last
    return {
        "close": float(last["Close"]),
        "prev_close": float(prev["Close"]),
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "volume": float(last["Volume"]) if last["Volume"] else None,
        "mktcap_local": _market_cap(t),
        "date": last.name.date(),
    }


def fetch_daily(symbol: str, n: int = 32, market: str | None = None
                ) -> list[tuple[date, float]]:
    return [(r["date"], r["close"]) for r in fetch_history(symbol, n, market)]

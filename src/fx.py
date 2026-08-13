"""
일일 환율 조회.

USD를 축으로 2개 페어만 조회하고, IDR→KRW는 크로스레이트로 파생시킨다.
페어를 독립적으로 가져오면 기준시점이 어긋나 평가손익이 미세하게 틀어진다.

    USD/KRW = 1,385.20      (1달러당 원)
    USD/IDR = 16,240.00     (1달러당 루피아)
    → IDR/KRW = 1,385.20 / 16,240.00 = 0.08530   (1루피아당 원)

소스
  1순위 yfinance (KRW=X, IDR=X)  : 시장 종가 기준. 시세와 동일 기준시점 → 정합성 유리
  2순위 open.er-api.com          : 무키 REST. yfinance 스키마 변경 대비 폴백
  3순위 config 고정값             : 둘 다 실패 시. 리포트에 ⚠️ 표기

주의(실무): 여기서 쓰는 건 시장환율이다. 회계상 평가손익 확정이나 대외
보고에는 서울외국환중개 매매기준율을 써야 하므로 수치가 소폭 달라진다.
"""
from __future__ import annotations

from datetime import date
from typing import NamedTuple


class FxRates(NamedTuple):
    usd_krw: float
    usd_idr: float
    as_of: str
    source: str

    @property
    def idr_krw(self) -> float:
        """크로스레이트. 1 IDR당 원화"""
        return self.usd_krw / self.usd_idr

    def to_krw_table(self) -> dict[str, float]:
        """report_table.FX 에 주입할 원화 환산 계수"""
        return {"KRW": 1.0, "USD": self.usd_krw, "IDR": self.idr_krw}

    def caption(self) -> str:
        # 이모지는 matplotlib에서 두부(□)로 깨지므로 PNG/텍스트 공용은 기호만 사용
        label = {"yfinance": "시장환율", "er-api": "시장환율(대체)",
                 "fixed": "※ 고정값 폴백 — 조회 실패"}.get(self.source, self.source)
        return (f"환율 {self.as_of} · {label}   "
                f"1 USD = ₩{self.usd_krw:,.2f}   |   "
                f"1 USD = {self.usd_idr:,.2f} IDR   |   "
                f"1 IDR = ₩{self.idr_krw:,.5f}")


def _from_yfinance() -> FxRates:
    import yfinance as yf
    out = {}
    for sym, key in (("KRW=X", "usd_krw"), ("IDR=X", "usd_idr")):
        h = yf.Ticker(sym).history(period="5d", interval="1d")
        if h.empty:
            raise RuntimeError(f"환율 조회 실패: {sym}")
        out[key] = float(h["Close"].iloc[-1])
        as_of = h.index[-1].date().isoformat()
    return FxRates(out["usd_krw"], out["usd_idr"], as_of, "yfinance")


def _from_erapi() -> FxRates:
    import requests
    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
    r.raise_for_status()
    d = r.json()
    rates = d["rates"]
    as_of = d.get("time_last_update_utc", "")[5:16] or date.today().isoformat()
    return FxRates(float(rates["KRW"]), float(rates["IDR"]), as_of, "er-api")


def fetch_rates(fallback: dict | None = None) -> FxRates:
    for fn in (_from_yfinance, _from_erapi):
        try:
            return fn()
        except Exception as e:
            print(f"[warn] {fn.__name__} 실패: {type(e).__name__}: {e}")

    fb = fallback or {}
    usd_krw = float(fb.get("USD", 1385.0))
    idr_krw = float(fb.get("IDR", 0.0855))
    return FxRates(usd_krw, usd_krw / idr_krw, date.today().isoformat(), "fixed")

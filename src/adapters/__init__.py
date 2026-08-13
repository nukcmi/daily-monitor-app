"""
시장별 시세 어댑터 라우터.

현재는 전 종목 yfinance 단일 소스를 사용한다.
market 값은 심볼 접미사(.KS/.KQ/.JK) 결정에만 쓰인다.
"""
from . import overseas


def get_adapter(market: str | None = None):
    return overseas

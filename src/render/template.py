"""3단 구조 리포트 HTML 생성 (모바일 카드형)."""
from __future__ import annotations

import html

from model import (Row, TAG_STYLE, big_local, krw_big, krw_sub,
                   market_close_caption, money, pct, vol_fmt)

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b0d10;color:#e8eaed;font-family:'Noto Sans KR','Noto Sans CJK KR',sans-serif;
     width:760px;padding:20px}
.hdr{display:flex;flex-direction:column;gap:4px;margin-bottom:18px}
.hdr h1{font-size:26px;font-weight:800;letter-spacing:-.5px}
.hdr .sub{font-size:16px;color:#9aa0a6}
.hdr .upd{font-size:12.5px;color:#6b7076}
.sec{background:#12151a;border:1px solid #232830;border-radius:12px;
     padding:16px;margin-bottom:16px}
.sec-h{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:6px}
.sec-n{background:#2f6fed;color:#fff;width:26px;height:26px;border-radius:6px;
       font-size:14px;font-weight:700;display:flex;align-items:center;justify-content:center}
.sec-t{font-size:19px;font-weight:700}
.sec-s{font-size:13px;color:#8b9096;font-weight:400;width:100%}
.sec-r{font-size:12.5px;color:#8b9096;line-height:1.7;width:100%;margin-top:2px}

.stock-card{border-bottom:1px solid #1c2027;padding:16px 0}
.stock-card:last-child{border-bottom:none}
.sc-top{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px}
.sc-name{flex:1;min-width:0}
.code{font-size:18px;font-weight:700;line-height:1.3}
.nm{font-size:13px;color:#9aa0a6;line-height:1.4}
.sb{font-size:11.5px;color:#6b7076}
.tag{display:inline-block;margin-top:5px;padding:2.5px 9px;border-radius:5px;
     font-size:11.5px;font-weight:600}
.own{background:#2a3a55;color:#7fb0ff}
.bench{background:#3a3350;color:#b39ddb}
.affil{background:#173d33;color:#5fd0a8}
.watch{background:#2c3036;color:#9aa0a6}
.sc-spark{flex-shrink:0}
.sc-price{text-align:right;flex-shrink:0}
.sc-close{font-size:20px;font-weight:700}
.sc-cost{font-size:12px;color:#8b9096;margin-top:2px}
.sub2{font-size:11px;color:#7a8088;margin-top:1px}
.mkt-close{font-size:10px;color:#e8a33d;margin-top:3px}
.sc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
.gcell{background:#171b21;border-radius:8px;padding:8px 10px}
.gcell .gl{font-size:10.5px;color:#8b9096;margin-bottom:3px}
.gcell .gv{font-size:14.5px;font-weight:700}
.up{color:#f0616d}.down{color:#4a90e2}.mut{color:#8b9096}
.note{margin-top:12px;font-size:11px;color:#6b7076;line-height:1.6}

.sig{padding:16px 0;border-bottom:1px solid #1c2027}
.sig:last-child{border-bottom:none}
.sig-name{margin-bottom:8px}
.sig-top{display:flex;align-items:flex-start;gap:10px;margin-bottom:6px}
.dot{width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:5px}
.d-high{background:#f0616d}.d-mid{background:#e8a33d}.d-low{background:#4a4f57}
.sig-h{font-size:16.5px;font-weight:700;flex:1}
.h-high{color:#f0616d}.h-mid{color:#e8c33d}.h-low{color:#c8ccd0}
.sig-m li{font-size:13.5px;color:#b8bdc4;margin:0 0 4px 18px;line-height:1.55}
.chk{margin-top:10px;background:#171b21;border-radius:8px;padding:11px 13px}
.chk-t{font-size:12px;font-weight:700;color:#c8ccd0;margin-bottom:6px}
.chk div{font-size:12px;color:#9aa0a6;line-height:1.8}
.sig-tag{margin:6px 0 0 22px}

.ev{padding:14px 0;border-bottom:1px solid #1c2027}
.ev:last-child{border-bottom:none}
.ev-top{display:flex;align-items:center;gap:9px;margin-bottom:6px}
.ev-n{font-size:14.5px;font-weight:700;color:#7fb0ff}
.ev-n span{font-size:11.5px;color:#6b7076;font-weight:400;margin-left:6px}
.ev-l{margin-left:auto;font-size:12px;white-space:nowrap}
.ev-s{font-size:13.5px;color:#d4d8dc;line-height:1.55;margin-bottom:6px}
.ev-b{display:inline-block;background:#232830;color:#9aa0a6;font-size:11px;
      padding:3px 9px;border-radius:5px;margin-bottom:5px}
.ev-i{font-size:12.5px;color:#9aa0a6;line-height:1.55}
"""


def _spark(vals, cost=None, w=90, h=34) -> str:
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    if cost:
        lo, hi = min(lo, cost), max(hi, cost)
    rng = (hi - lo) or 1
    up = vals[-1] >= vals[0]
    col = "#f0616d" if up else "#4a90e2"
    step = w / (len(vals) - 1)
    pts = " ".join(f"{i*step:.1f},{h-(v-lo)/rng*h:.1f}" for i, v in enumerate(vals))
    fill = f"0,{h} {pts} {w},{h}"
    line = ""
    if cost:
        y = h - (cost - lo) / rng * h
        line = (f'<polyline points="0,{y:.1f} {w},{y:.1f}" fill="none" '
                f'stroke="#8b9096" stroke-width="1" stroke-dasharray="3,2"/>')
    return (f'<svg width="{w}" height="{h}">'
            f'<polygon points="{fill}" fill="{col}" opacity="0.15"/>{line}'
            f'<polyline points="{pts}" fill="none" stroke="{col}" '
            f'stroke-width="1.6"/></svg>')


def _c(v):
    if v is None:
        return "mut"
    return "up" if v >= 0 else "down"


def _esc(s):
    return html.escape(str(s or ""))


def build_html(rows: list[Row], analysis: dict, as_of: str,
               fx_line: str, updated: str, section: str = "all") -> str:
    """section: 'all' | '1' | '2' | '3' — 지정 섹션만 렌더링."""
    # ── 1. Market Snapshot (카드형) ──
    cards = []
    for r in rows:
        tag_cls = TAG_STYLE.get(r.tag, "watch")
        vr = r.vol_ratio
        vr_txt = f"{vr:.2f}x" if vr else "-"
        vr_cls = "up" if vr and vr >= 1 else ("down" if vr else "mut")

        close_sub = (f'<div class="sub2">{krw_sub(r.close_krw)}</div>'
                    if r.currency != "KRW" else "")
        close_caption = market_close_caption(r.quote_date, r.market)
        close_time_line = (f'<div class="mkt-close">{_esc(close_caption)}</div>'
                           if close_caption else "")
        cost_sub = (f'<div class="sub2">{krw_sub(r.avg_cost_krw, r.acq_label)}</div>'
                   if r.held and r.currency != "KRW" else "")
        mcap_sub = (f'<div class="sub2">{krw_big(r.mktcap_krw)}</div>'
                   if r.currency != "KRW" else "")

        cards.append(f"""<div class="stock-card">
<div class="sc-top">
<div class="sc-spark">{_spark([v for _, v in r.spark], r.avg_cost)}</div>
<div class="sc-name"><div class="code">{_esc(r.code)}</div>
<div class="nm">{_esc(r.name)}</div>
{f'<div class="sb">{_esc(r.sub)}</div>' if r.sub else ''}</div>
<div class="sc-price"><div class="sc-close">{money(r.close, r.currency)}</div>
{close_sub}{close_time_line}
<div class="sc-cost">취득 {money(r.avg_cost, r.currency)}</div>{cost_sub}</div>
</div>
<div class="sc-grid">
<div class="gcell"><div class="gl">취득가대비</div>
<div class="gv {_c(r.vs_cost)}">{pct(r.vs_cost)}</div></div>
<div class="gcell"><div class="gl">전일대비</div>
<div class="gv {_c(r.vs_prev)}">{pct(r.vs_prev)}</div></div>
<div class="gcell"><div class="gl">전주대비</div>
<div class="gv {_c(r.vs_week)}">{pct(r.vs_week)}</div></div>
<div class="gcell"><div class="gl">거래량 (20일比)</div>
<div class="gv {vr_cls}">{vol_fmt(r.volume)} · {vr_txt}</div></div>
<div class="gcell"><div class="gl">시가총액</div>
<div class="gv mut">{big_local(r.mktcap_local, r.currency)}</div>{mcap_sub}</div>
<div class="gcell"><div class="gl">52주 고점대비</div>
<div class="gv {_c(r.vs_52w_high)}">{pct(r.vs_52w_high)}</div></div>
</div></div>""")

    # ── 2. 종목 동향 ──
    sigs = []
    for r in rows:
        s = analysis.get("signals", {}).get(r.code, {})
        lv = s.get("level", "low")
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in s.get("bullets", []))
        chks = "".join(f"<div>☐ {_esc(c)}</div>" for c in s.get("checkpoints", []))
        chk_box = (f'<div class="chk"><div class="chk-t">앞으로 볼 포인트</div>{chks}</div>'
                   if chks else "")
        sigs.append(f"""<div class="sig">
<div class="sig-name"><span class="code">{_esc(r.code)}</span>
<span class="nm" style="margin-left:6px">{_esc(r.name)}</span></div>
<div class="sig-top"><div class="dot d-{lv}"></div>
<div class="sig-h h-{lv}">{_esc(s.get('headline','-'))}</div></div>
<ul style="margin-left:22px;margin-top:8px">{bullets}</ul>{chk_box}</div>""")

    # ── 3. Key Events ──
    evs = []
    for e in analysis.get("events", [])[:6]:
        lv = e.get("level", "low")
        label = {"high": "높음", "mid": "중간", "low": "낮음"}.get(lv, "낮음")
        col = {"high": "#f0616d", "mid": "#e8a33d", "low": "#5fd0a8"}[lv]
        evs.append(f"""<div class="ev">
<div class="ev-top"><div class="dot d-{lv}"></div>
<div class="ev-n">{_esc(e.get('name'))}<span>{_esc(e.get('date'))}</span></div>
<div class="ev-l" style="color:{col}">● {label}</div></div>
<div class="ev-s">{_esc(e.get('summary'))}</div>
<div class="ev-b">당사 영향</div>
<div class="ev-i">{_esc(e.get('impact'))}</div></div>""")
    if not evs:
        evs.append('<div class="ev"><div class="ev-s mut">'
                   '해당 기간 특이 공시·기사 없음</div></div>')

    sec1 = f"""<div class="sec"><div class="sec-h"><div class="sec-n">1</div>
<div class="sec-t">시세 현황</div>
<div class="sec-r">{_esc(fx_line)}</div></div>
{''.join(cards)}
<div class="note">※ 괄호 아래 회색 표기는 원화 환산 (취득가는 취득 시점 환율 적용)<br>
※ 52주 고점대비: (종가 / 52주 고점 − 1) &nbsp;&nbsp;
※ 추세선의 점선은 취득가</div></div>"""

    sec2 = f"""<div class="sec"><div class="sec-h"><div class="sec-n">2</div>
<div class="sec-t">종목 동향</div>
<div class="sec-s">최근 공시·기사 기반 국면 진단</div></div>{''.join(sigs)}</div>"""

    sec3 = f"""<div class="sec"><div class="sec-h"><div class="sec-n">3</div>
<div class="sec-t">주요 이벤트</div>
<div class="sec-r">영향도: <span style="color:#f0616d">●</span> 높음 &nbsp;
<span style="color:#e8a33d">●</span> 중간 &nbsp;
<span style="color:#5fd0a8">●</span> 낮음</div></div>{''.join(evs)}
<div class="note">※ 영향도는 당사 보유·투자 지분의 재무·자본구조에 미치는 영향 정도 기준입니다.<br>
※ 본 정보는 참고용이며 투자 권유가 아닙니다.</div></div>"""

    header = f"""<div class="hdr"><h1>일일 모니터링</h1>
<div class="sub">{_esc(as_of)} 장마감 기준</div>
<div class="upd">업데이트: {_esc(updated)}</div></div>"""

    body_map = {
        "1": header + sec1,
        "2": sec2,
        "3": sec3,
        "all": header + sec1 + sec2 + sec3,
    }
    body = body_map.get(section, body_map["all"])

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{body}</body></html>"""

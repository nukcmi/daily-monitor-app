"""
전략팀 일일 모니터링 - 엔트리포인트

usage: python src/main.py --config config/portfolio.json [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))

from adapters import overseas                                  # noqa: E402
from analyze import analyze                                    # noqa: E402
from fx import FxRates, fetch_rates                            # noqa: E402
from miniapp_export import build_payload                       # noqa: E402
from model import FX, build_row, pct                           # noqa: E402
from render.capture import capture                             # noqa: E402
from render.template import build_html                         # noqa: E402
from notify.telegram import send_photo                         # noqa: E402
from sources import dart, news, sec                            # noqa: E402

KST = ZoneInfo("Asia/Seoul")


def collect_items(item: dict) -> list[dict]:
    """종목별 공시 + 뉴스. 소스 하나가 죽어도 나머지는 살린다."""
    out = []
    if item.get("dart_code"):
        try:
            out += dart.fetch_disclosures(item["dart_code"])
        except Exception as e:
            print(f"[warn] DART {item['id']}: {type(e).__name__}: {e}")
    if item.get("sec_cik"):
        try:
            out += sec.fetch_filings(item["sec_cik"])
        except Exception as e:
            print(f"[warn] SEC {item['id']}: {type(e).__name__}: {e}")
    try:
        out += news.fetch_news(item.get("keywords", []),
                               lang=item.get("news_lang", "ko"))
    except Exception as e:
        print(f"[warn] NEWS {item['id']}: {type(e).__name__}: {e}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/portfolio.json")
    ap.add_argument("--out", default="out/daily_monitor.png")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-ai", action="store_true", help="Claude 호출 건너뜀")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    week_mode = cfg.get("week_ref_mode", "last_week_close")
    now = datetime.now(KST)
    as_of = now.strftime("%Y-%m-%d")

    # 환율
    if cfg.get("fx_mode", "auto") == "fixed":
        fb = cfg.get("fx", {})
        rates = FxRates(fb.get("USD", 1385.0),
                        fb.get("USD", 1385.0) / fb.get("IDR", 0.0855),
                        as_of, "fixed")
    else:
        rates = fetch_rates(fallback=cfg.get("fx"))
    FX.update(rates.to_krw_table())
    print(f"[fx] {rates.caption()}")

    # 시세 + 소스
    rows, ctx, failed = [], [], []
    items_by_code = {}
    raw_items_by_code = {}
    for item in cfg["items"]:
        sym = item.get("ticker", item["id"])
        try:
            quote = overseas.fetch_quote(sym, item.get("market"))
            hist = overseas.fetch_history(sym, 260, item.get("market"))
            r = build_row(item, quote, hist, week_mode)
            rows.append(r)
            items_by_code[r.code] = item
            raw = collect_items(item)
            raw_items_by_code[r.code] = raw
            ctx.append({"code": r.code, "name": r.name,
                        "role": item.get("role", ""),
                        "purpose": item.get("purpose", ""),
                        "watch_axes": item.get("watch_axes", []),
                        "price_move": pct(r.vs_prev),
                        "items": raw,
                        "hide_terms": item.get("hide_terms", [])})
        except Exception as e:
            failed.append(f"{item['id']}({type(e).__name__}: {e})")

    if not rows:
        print("[fatal] 조회 성공 종목 없음", file=sys.stderr)
        return 1

    if args.no_ai:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    analysis = analyze(ctx)

    updated = now.strftime("%Y-%m-%d %H:%M")
    out_dir = os.path.dirname(args.out) or "out"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.out))[0]

    # Mini App용 JSON — 3장 PNG와 같은 rows/analysis를 재사용해 저장만 추가
    payload = build_payload(rows, analysis, items_by_code, as_of, updated,
                            fx_line=rates.caption(),
                            raw_items_by_code=raw_items_by_code)
    miniapp_json_path = os.path.join(out_dir, "miniapp_data.json")
    with open(miniapp_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[miniapp] {miniapp_json_path} 생성 완료")

    paths = {}
    for sec in ("1", "2", "3"):
        p = os.path.join(out_dir, f"{base}_{sec}.png")
        html = build_html(rows, analysis, as_of, rates.caption(), updated,
                          section=sec)
        capture(html, p)
        paths[sec] = p

    caption = f"⚠️ 조회 실패: {', '.join(failed)}" if failed else ""
    if failed:
        print(caption)

    if args.dry_run:
        print(f"[dry-run] {out_dir}/{base}_1.png / _2.png / _3.png 생성 완료")
        return 0

    titles = {"1": "1️⃣ 시세 현황", "2": "2️⃣ 종목 동향", "3": "3️⃣ 주요 이벤트"}
    for i, sec in enumerate(("1", "2", "3")):
        cap = f"<b>일일 모니터링</b>  {as_of}\n{titles[sec]}"
        if sec == "3" and caption:
            cap += f"\n{caption}"
        send_photo(paths[sec], cap)
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())

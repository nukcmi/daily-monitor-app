"""
Claude API 기반 요약 / 당사 영향 판단.

2번(종목 동향), 3번(주요 변동사항)의 문안을 생성한다.
API 실패 시에도 파이프라인은 죽지 않고, 원문 제목만 표시하는 폴백으로 내려간다.

환경변수: ANTHROPIC_API_KEY
"""
from __future__ import annotations

import json
import os
import re

import requests

API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

SYSTEM = """당신은 한화손해보험 전략기획실 소속 시니어 애널리스트다.
보유·검토 종목의 공시와 뉴스를 읽고 임원 보고용 문안을 작성한다.

당신이 속한 조직의 성격:
- 신규 투자를 검토하고 의견을 내는 조직이지, 트레이딩 데스크가 아니다.
- 주주가치와 사업 포트폴리오 방향성 관점에서 "큰 그림"을 포착하는 것이
  임무다. 일간 주가 변동 자체, 반복적 홍보성 기사, 사소한 임원 인터뷰
  같은 지엽적 디테일은 굳이 포착하지 않는다.
- "큰 그림"의 기준은 종목마다 다르다. 당사가 실제 지분을 보유한 종목,
  아직 투자하지 않은 벤치마크·검토 대상, 그룹 계열 관계사·자회사는 모니터링
  목적 자체가 다르므로 같은 잣대를 적용하지 않는다. 각 종목별로 프롬프트에
  주어지는 '모니터링 목적'을 반드시 참고해 그 종목에 맞는 기준으로 판단한다.
- 판단 기준은 항상 "이 사건이 그 종목의 모니터링 목적 관점에서 실제로
  영향을 주는가"이지, "오늘 화제가 됐는가"가 아니다.

원칙:
- 사실과 해석을 섞지 않는다. 공시·기사에 없는 내용을 지어내지 않는다.
- 문장은 짧고 압축적으로. 수식어 금지.
- 당사(한화손해보험) 관점의 영향을 명시한다.
- headline과 events 요약은 주가 반응이 아니라 그 배경이 되는 사업적
  변화를 설명한다. 예를 들어 "단일 세션 +7.98% 급등"처럼 주가 움직임
  자체를 헤드라인으로 쓰지 않는다. 그 상승을 유발한 사업적 사실
  (예: 반기보고서상 투자자산 확대)을 헤드라인으로 쓴다.
- 종목명은 반드시 프롬프트에 주어진 표시명을 그대로 쓴다. 원문 기사·공시에
  다른 회사명이 등장하더라도 그 이름을 절대 노출하지 않는다.
- 보험·재무·투자 통상 용어(GWP, Loss Ratio, RBC, IFP, CB, EBITDA 등)는
  설명 없이 그대로 쓴다. 다만 바이오·의료 등 비보험 전문용어(CGT, CDMO 등)는
  최초 등장 시 괄호 안에 짧은 한국어 설명을 병기한다.
  예: CGT(세포·유전자치료제), CDMO(위탁개발생산). 설명은 길게 쓰지 않는다.
- 반드시 JSON만 출력한다. 마크다운 코드펜스나 설명을 붙이지 않는다."""


def _call(prompt: str, max_tokens: int = 3000) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    try:
        r = requests.post(API, timeout=90, headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }, json={
            "model": MODEL, "max_tokens": max_tokens,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        })
        if r.status_code != 200:
            print(f"[warn] Claude {r.status_code}: {r.text[:200]}")
            return None
        txt = "".join(b.get("text", "") for b in r.json().get("content", []))
        txt = txt.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            if txt.startswith("json"):
                txt = txt[4:]
        i = txt.find("{")
        if i < 0:
            print(f"[warn] JSON 없음: {txt[:200]}")
            return None
        # 모델이 JSON 뒤에 설명을 덧붙이는 경우를 대비해 첫 객체만 파싱
        obj, _ = json.JSONDecoder().raw_decode(txt[i:])
        return obj
    except Exception as e:
        print(f"[warn] Claude 호출 실패: {type(e).__name__}: {e}")
        return None


def _sanitize_text(text: str, term_map: dict[str, str]) -> str:
    """hide_terms(예: 'Lemonade')를 표시명(예: '루멘')으로 치환."""
    if not text:
        return text
    for term, name in term_map.items():
        text = re.sub(re.escape(term), name, text, flags=re.IGNORECASE)
    return text


def _sanitize_analysis(analysis: dict, term_map: dict[str, str]) -> dict:
    if not term_map:
        return analysis
    for sig in analysis.get("signals", {}).values():
        sig["headline"] = _sanitize_text(sig.get("headline", ""), term_map)
        sig["bullets"] = [_sanitize_text(b, term_map) for b in sig.get("bullets", [])]
        sig["checkpoints"] = [_sanitize_text(c, term_map)
                              for c in sig.get("checkpoints", [])]
    for ev in analysis.get("events", []):
        for k in ("name", "summary", "impact"):
            ev[k] = _sanitize_text(ev.get(k, ""), term_map)
    return analysis


def _items_text(items: list[dict], term_map: dict[str, str]) -> str:
    if not items:
        return "(해당 기간 공시·기사 없음)"
    return "\n".join(
        f"- [{i['source']}] ({i.get('date', '날짜 미상')}) "
        f"{_sanitize_text(i['title'], term_map)}"
        for i in items[:10]
    )


def analyze(rows_ctx: list[dict]) -> dict:
    """
    rows_ctx: [{code, name, role, items:[{source,title}], price_move, hide_terms}]
    반환: {"signals": {code: {...}}, "events": [{...}]}
    """
    # 종목별 숨김어 → 표시명 전역 매핑 (모델 입력·출력 양쪽에 적용)
    term_map: dict[str, str] = {}
    for c in rows_ctx:
        for term in c.get("hide_terms", []):
            term_map[term] = c["name"]

    payload = []
    for c in rows_ctx:
        axes_txt = ""
        if c.get("watch_axes"):
            axes_txt = ("우선 관전 축(이 범위 안에서 checkpoints 선정, "
                       "최신 동향으로 구체화): " + " / ".join(c["watch_axes"]))
        payload.append(
            f"### {c['name']} ({c['code']})\n"
            f"모니터링 목적 (이 종목에서 '큰 그림'이 무엇인지의 기준):\n"
            f"{c.get('purpose', '')}\n"
            f"당사 관점: {c.get('role','')}\n"
            f"{axes_txt}\n"
            f"주가: 전일대비 {c['price_move']}\n"
            f"최근 공시·기사:\n{_items_text(c['items'], term_map)}"
        )

    prompt = f"""아래는 당사가 모니터링 중인 종목별 최근 공시·기사다.

{chr(10).join(payload)}

두 가지를 JSON으로 작성하라.

1) signals: 종목코드를 키로 하는 객체. 각 값은
   - headline: 현재 국면을 한 줄로 (12자 내외, 예 "CGT/CDMO 사업 모멘텀 유지").
     주가 등락 자체가 아니라 사업적·구조적 변화를 요약한다.
     특이사항이 없으면 "주요 변동 없음"으로 쓴다.
   - level: "high" | "mid" | "low"  (아래 기준 참고)
   - bullets: 근거 1~2개. 각 40자 이내. 공시·기사에 근거한 사실만.
     특이사항이 없으면 ["공시·기사 기준 특이사항 없음"]
   - checkpoints: 앞으로 확인할 포인트 3개. 각 20자 이내.
     각 종목에 '우선 관전 축'이 주어지면 반드시 그 범위 안에서 선정하고,
     막연한 일반론이 아니라 그 축을 오늘 시점 상황에 맞게 구체화한다.
     (예: "자금조달 동향" 대신 "3분기 CB 상환 재원 확보 여부")

2) events: 주요 변동사항 배열. 최대 5개. 아래 두 조건을 모두 만족하는
   것만 선정한다 — ①실제 공시·기사가 있고, ②주주가치나 사업 방향성에
   실질적 영향을 주는 사안이다. 단순 주가 등락, 반복적 홍보·마케팅 기사,
   일상적 임원 인터뷰처럼 자잘한 소식은 공시·기사가 있어도 제외한다.
   특이사항 없는 종목도 포함하지 않는다.

   예외(반드시 포함) — 당사(한화손해보험)가 기사·공시에 직접 등장하거나
   당사와의 협력·파트너십·MOU·공동사업이 주제인 경우는 "홍보성 기사"
   제외 규칙을 적용하지 않고 반드시 포함한다. 이런 기사는 종목 자체의
   소식이 아니라 지분투자의 실제 시너지가 실현되는 신호이므로, 오히려
   가장 중요한 신호로 취급한다. (예: "OO그룹, 한화손보와 헬스케어 협력",
   "한화손보 임직원 대상 OO 연구소장 강연", "한화손보·OO그룹 OO 동맹")

   - name: 종목 표시명
   - date: "MM/DD". 반드시 위 "최근 공시·기사" 목록에 괄호로 주어진
     실제 날짜를 그대로 옮긴다. 절대 추측하거나 지어내지 않는다.
   - summary: 사실 요약 55자 이내. 주가 반응이 아니라 사업적 사실 중심.
   - impact: 당사 영향 55자 이내. 주주가치·사업 방향성 관점에서 서술.
   - level: "high" | "mid" | "low"

영향도(level) 판단 순서 (아래 순서대로 확인하며 조건에 먼저 걸리는 등급 적용):
   0. 당사(한화손해보험)와의 협력·파트너십·공동사업이 기사·공시의 주제인가?
      → 사업 시너지가 실제로 실현되는 신호이므로 high (기사 수준이어도 high)
   1. 당사 보유·투자 지분가치에 직접 영향이 있는가?
      Yes + 확정 공시(뉴스 아님) → high
      Yes + 기사 수준(미확정) → mid
   2. 재무구조·실적에 유의미한 영향이 있는가? (자금조달, 대규모 계약, 실적 서프라이즈 등)
      Yes + 확정 공시 → high
      Yes + 기사 수준 → mid
   3. 사업 방향성·시장 포지션에 영향은 있으나 재무 영향은 불확실한가?
      (신사업, 파트너십, 신제품, IR 활동 등) → mid
   4. 위 어디에도 해당 안 되는 참고 수준 뉴스 → low
   ※ 경영 의사결정이 필요한 사안이면 위 결과에서 한 단계 상향한다.

출력 형식:
{{"signals": {{"085660": {{"headline":"","level":"","bullets":[],"checkpoints":[]}}}}, "events": []}}"""

    out = _call(prompt)
    if out and isinstance(out.get("signals"), dict):
        return _sanitize_analysis(out, term_map)

    # 폴백: 원문 제목만 (이미 _items_text 단계에서 sanitize된 제목 재사용)
    signals, events = {}, []
    for c in rows_ctx:
        its = [{**i, "title": _sanitize_text(i["title"], term_map)}
               for i in c["items"]]
        signals[c["code"]] = {
            "headline": "주요 변동 없음" if not its else "공시·기사 확인 필요",
            "level": "low" if not its else "mid",
            "bullets": ([i["title"][:40] for i in its[:2]]
                        or ["공시·기사 기준 특이사항 없음"]),
            "checkpoints": [],
        }
        for i in its[:2]:
            events.append({"name": c["name"], "date": i.get("date", ""),
                           "summary": i["title"][:55], "impact": "-",
                           "level": "low"})
    return {"signals": signals, "events": events[:5]}

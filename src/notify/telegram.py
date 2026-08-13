"""
Telegram 발송. 표는 PNG, 요약은 HTML 캡션.

TELEGRAM_CHAT_ID는 콤마(,)로 구분해 여러 명에게 동시 발송할 수 있다.
  예: "111111111,222222222,333333333"
한 명에게 발송이 실패해도(예: 봇 차단, 잘못된 id) 나머지에게는 정상 발송된다.
"""
from __future__ import annotations

import os
import requests

API = "https://api.telegram.org/bot{token}/{method}"
CAPTION_LIMIT = 1024   # sendPhoto 캡션 제한. 초과 시 본문을 별도 메시지로 분리


def _token() -> str:
    return os.environ["TELEGRAM_BOT_TOKEN"]


def _chat_ids() -> list[str]:
    raw = os.environ["TELEGRAM_CHAT_ID"]
    return [c.strip() for c in raw.split(",") if c.strip()]


def _send_text_to(token: str, chat: str, text: str) -> None:
    r = requests.post(API.format(token=token, method="sendMessage"),
                      data={"chat_id": chat, "text": text,
                            "parse_mode": "HTML",              # Markdown 금지
                            "disable_web_page_preview": True},
                      timeout=15)
    r.raise_for_status()


def _send_photo_to(token: str, chat: str, path: str, caption: str) -> None:
    long_caption = len(caption) > CAPTION_LIMIT
    with open(path, "rb") as f:
        r = requests.post(API.format(token=token, method="sendPhoto"),
                          data={"chat_id": chat,
                                "caption": "" if long_caption else caption,
                                "parse_mode": "HTML"},
                          files={"photo": f}, timeout=30)
    r.raise_for_status()
    if long_caption:
        _send_text_to(token, chat, caption)


def send_text(text: str) -> None:
    """등록된 모든 수신자에게 발송. 한 명 실패해도 나머지는 계속 진행."""
    token = _token()
    for chat in _chat_ids():
        try:
            _send_text_to(token, chat, text)
        except Exception as e:
            print(f"[warn] 텍스트 발송 실패 (chat_id={chat}): {type(e).__name__}: {e}")


def send_photo(path: str, caption: str = "") -> None:
    """등록된 모든 수신자에게 발송. 한 명 실패해도 나머지는 계속 진행."""
    token = _token()
    for chat in _chat_ids():
        try:
            _send_photo_to(token, chat, path, caption)
        except Exception as e:
            print(f"[warn] 사진 발송 실패 (chat_id={chat}): {type(e).__name__}: {e}")

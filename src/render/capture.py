"""HTML → PNG 캡처 (Playwright/Chromium)."""
from __future__ import annotations

import os


def capture(html: str, path: str, width: int = 800) -> str:
    """body 요소만 캡처 — 실제 렌더 크기에 정확히 맞아 여백/잘림이 없다."""
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-color-profile=srgb"])
        pg = b.new_page(viewport={"width": width, "height": 1200},
                        device_scale_factor=2)
        pg.set_content(html, wait_until="load")
        pg.wait_for_timeout(400)
        pg.locator("body").screenshot(path=path)
        b.close()
    return path

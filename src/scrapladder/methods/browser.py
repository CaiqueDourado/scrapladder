"""Browser rungs: Playwright (Chromium), Camoufox (Firefox) and Scrapling.

A browser runs the page's JavaScript, so it gets content that plain HTTP never sees and passes
checks that only ask "are you a browser?". It is also 10 to 50 times slower, so these rungs
come after the HTTP ones unless the domain memory says a browser is what works there.

The browser is started on first use and reused; call :meth:`close` (or use the ladder as a
context manager) to stop it. The sync Playwright API is not thread-safe: use one ladder per
thread.
"""

from __future__ import annotations

from .base import Method, Response, require


class Playwright(Method):
    name = "playwright"
    default_priority = 0.4

    def __init__(self, *, headless: bool = True, wait_ms: int = 3000, launch_args: list[str] | None = None, **kw):
        super().__init__(**kw)
        self.headless, self.wait_ms = headless, wait_ms
        self.launch_args = launch_args or ["--no-sandbox", "--disable-dev-shm-usage"]
        self._pw = self._browser = None

    def check(self) -> None:
        require("playwright", "browser")

    def _ensure(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self.headless, args=self.launch_args)
        return self._browser

    def fetch(self, url: str) -> Response:
        ctx = self._ensure().new_context(user_agent=self.headers.get("User-Agent"),
                                         locale="pt-BR", extra_http_headers={"Accept-Language": self.headers.get("Accept-Language", "pt-BR")})
        try:
            page = ctx.new_page()
            resp = page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(self.wait_ms)
            return Response(resp.status if resp else None, page.content(),
                            dict(resp.headers) if resp else {}, page.url)
        finally:
            ctx.close()

    def close(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            finally:
                self._pw.stop()
                self._pw = self._browser = None


class Camoufox(Method):
    """Firefox build whose fingerprint looks like an ordinary user's (``camoufox`` package)."""

    name = "camoufox"
    default_priority = 0.3

    def __init__(self, *, headless: bool = True, wait_ms: int = 3000, options: dict | None = None, **kw):
        super().__init__(**kw)
        self.headless, self.wait_ms, self.options = headless, wait_ms, options or {}
        self._cm = self._browser = None

    def check(self) -> None:
        require("camoufox", "camoufox")

    def _ensure(self):
        if self._browser is None:
            from camoufox.sync_api import Camoufox as _Camoufox
            self._cm = _Camoufox(headless=self.headless, **self.options)
            self._browser = self._cm.__enter__()
        return self._browser

    def fetch(self, url: str) -> Response:
        page = self._ensure().new_page()
        try:
            resp = page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(self.wait_ms)
            return Response(resp.status if resp else None, page.content(), dict(resp.headers) if resp else {}, page.url)
        finally:
            page.close()

    def close(self) -> None:
        if self._cm is not None:
            try:
                self._cm.__exit__(None, None, None)
            finally:
                self._cm = self._browser = None


class Scrapling(Method):
    """Scrapling's ``StealthyFetcher`` (a patched browser with a common fingerprint).

    Extra keyword arguments go straight to ``StealthyFetcher.fetch``; see Scrapling's docs for
    what they do.
    """

    name = "scrapling"
    default_priority = 0.3

    def __init__(self, *, headless: bool = True, fetch_options: dict | None = None, **kw):
        super().__init__(**kw)
        self.headless, self.fetch_options = headless, fetch_options or {}

    def check(self) -> None:
        require("scrapling", "scrapling")

    def fetch(self, url: str) -> Response:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(url, headless=self.headless, timeout=int(self.timeout * 1000), **self.fetch_options)
        html = getattr(page, "html_content", None) or getattr(page, "body", None) or str(page)
        if isinstance(html, bytes):
            html = html.decode("utf-8", "ignore")
        return Response(getattr(page, "status", None), html, dict(getattr(page, "headers", {}) or {}), getattr(page, "url", url))

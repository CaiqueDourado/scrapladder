"""Plain HTTP rungs: requests, httpx and curl_cffi (browser TLS fingerprint)."""

from __future__ import annotations

import importlib.util

from .base import Method, Response, require


class Requests(Method):
    name = "requests"
    default_priority = 0.6

    def check(self) -> None:
        require("requests", "http")

    def fetch(self, url: str) -> Response:
        import requests
        r = requests.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
        return Response(r.status_code, r.text, dict(r.headers), str(r.url))


class Httpx(Method):
    name = "httpx"
    default_priority = 0.65

    def check(self) -> None:
        require("httpx", "http")

    def fetch(self, url: str) -> Response:
        import httpx
        http2 = importlib.util.find_spec("h2") is not None
        with httpx.Client(http2=http2, headers=self.headers, follow_redirects=True, timeout=self.timeout) as c:
            r = c.get(url)
        return Response(r.status_code, r.text, dict(r.headers), str(r.url))


class CurlCffi(Method):
    """HTTP with the TLS and HTTP/2 fingerprint of a real browser (``impersonate``).

    Many sites answer 403 to Python HTTP clients only because their TLS handshake does not look
    like a browser's. In the author's crawler this was the rung that got the page first on
    75% of 643 domains.
    """

    name = "curl_cffi"
    default_priority = 0.8

    def __init__(self, *, impersonate: str = "chrome", **kw) -> None:
        super().__init__(**kw)
        self.impersonate = impersonate
        # curl_cffi sets a User-Agent consistent with the impersonated browser; a different one
        # would contradict the fingerprint, so only the other headers are sent.
        self.headers = {k: v for k, v in self.headers.items() if k.lower() != "user-agent"}

    def check(self) -> None:
        require("curl_cffi", "curl")

    def fetch(self, url: str) -> Response:
        from curl_cffi import requests as cr
        r = cr.get(url, headers=self.headers, impersonate=self.impersonate, timeout=self.timeout, allow_redirects=True)
        return Response(r.status_code, r.text, dict(r.headers), str(r.url))

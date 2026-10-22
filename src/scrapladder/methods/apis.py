"""Paid scraping APIs as the top rung.

They fetch the page from their own pool of IPs and browsers and charge per request (more when
JavaScript rendering is on). The ladder tries them only after every free rung failed, unless
one of them already won on that domain. Keys come from the constructor or the environment
(``SCRAPERAPI_KEY``, ``SCRAPINGBEE_KEY``, ``SCRAPINGDOG_KEY``, ``SCRAPEDO_KEY``).
"""

from __future__ import annotations

import os

from .base import Method, MethodUnavailable, Response, require


class _ScrapingApi(Method):
    paid = True
    default_priority = 0.1
    endpoint = ""
    key_param = "api_key"
    env = ""
    render_param: tuple[str, str] = ("render", "true")

    def __init__(self, *, key: str | None = None, render: bool = True, **kw):
        kw.setdefault("timeout", 125.0)  # rendering APIs are slow
        super().__init__(**kw)
        self.key = key or os.environ.get(self.env)
        self.render = render

    def check(self) -> None:
        require("requests", "http")
        if not self.key:
            raise MethodUnavailable(f"{self.name}: no key (set {self.env})")

    def params(self, url: str) -> dict:
        p = {self.key_param: self.key, "url": url}
        if self.render:
            p[self.render_param[0]] = self.render_param[1]
        return p

    def fetch(self, url: str) -> Response:
        import requests
        r = requests.get(self.endpoint, params=self.params(url), timeout=self.timeout)
        return Response(r.status_code, r.text, dict(r.headers), url)


class ScraperAPI(_ScrapingApi):
    name, endpoint, env = "scraperapi", "https://api.scraperapi.com/", "SCRAPERAPI_KEY"


class ScrapingBee(_ScrapingApi):
    name, endpoint, env = "scrapingbee", "https://app.scrapingbee.com/api/v1/", "SCRAPINGBEE_KEY"
    render_param = ("render_js", "true")


class ScrapingDog(_ScrapingApi):
    name, endpoint, env = "scrapingdog", "https://api.scrapingdog.com/scrape", "SCRAPINGDOG_KEY"
    render_param = ("dynamic", "true")


class ScrapeDo(_ScrapingApi):
    name, endpoint, env, key_param = "scrapedo", "https://api.scrape.do/", "SCRAPEDO_KEY", "token"

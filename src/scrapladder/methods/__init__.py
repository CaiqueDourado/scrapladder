from .apis import ScrapeDo, ScraperAPI, ScrapingBee, ScrapingDog
from .base import DEFAULT_HEADERS, DEFAULT_UA, Method, MethodUnavailable, Response
from .browser import Camoufox, Playwright, Scrapling
from .http import CurlCffi, Httpx, Requests

ALL = [CurlCffi, Httpx, Requests, Playwright, Scrapling, Camoufox, ScrapeDo, ScrapingDog, ScrapingBee, ScraperAPI]


def default_methods(**kw) -> list[Method]:
    """Every rung whose package (and key, for paid APIs) is available here."""
    out = []
    for cls in ALL:
        m = cls(**kw)
        if m.available():
            out.append(m)
    return out


__all__ = ["Method", "MethodUnavailable", "Response", "DEFAULT_HEADERS", "DEFAULT_UA", "default_methods", "ALL",
           "Requests", "Httpx", "CurlCffi", "Playwright", "Scrapling", "Camoufox",
           "ScraperAPI", "ScrapingBee", "ScrapingDog", "ScrapeDo"]

"""Recognise block pages.

A block page is an answer that is not the page you asked for: a bot challenge, a CAPTCHA, an
"Access Denied" from a WAF, or a rate limit. Two kinds matter, because they lead to different
decisions:

- **terminal**: the block is at network or CDN level (Akamai "Access Denied", a short
  "403 Forbidden" page). Every method goes through the same IP, so trying the next rung is a
  waste: stop.
- **challenge**: the site asks the client to prove it is a browser (Cloudflare "Just a moment",
  DataDome, PerimeterX, a CAPTCHA). A heavier rung (a real browser) may get the page: go on.

Rate limits (HTTP 429) are reported as their own kind, ``rate_limited``: the ladder stops and
waits, it does not try to get around them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

TERMINAL = "terminal"
CHALLENGE = "challenge"
RATE_LIMITED = "rate_limited"

# Block pages are short and say what they are near the top. Long pages that merely contain
# "too many requests" in a script are real pages, so only the head of the HTML is checked.
HEAD_CHARS = 8000
SHORT_PAGE = 4000


@dataclass(frozen=True)
class Block:
    kind: str      # TERMINAL, CHALLENGE or RATE_LIMITED
    reason: str    # short id of the signature that matched, e.g. "cloudflare_challenge"
    vendor: str = ""

    @property
    def terminal(self) -> bool:
        return self.kind == TERMINAL


# (reason, vendor, kind, substrings that must ALL appear in the lowered head)
_BODY_RULES: list[tuple[str, str, str, tuple[str, ...]]] = [
    # Terminal: network / CDN level
    ("akamai_edgesuite", "Akamai", TERMINAL, ("edgesuite.net",)),
    ("akamai_reference", "Akamai", TERMINAL, ("access denied", "reference #")),
    ("permission_denied", "", TERMINAL, ("you don't have permission to access",)),
    ("permission_denied", "", TERMINAL, ("you don&#39;t have permission to access",)),
    ("access_denied_server", "", TERMINAL, ("access denied on this server",)),
    ("incapsula_incident", "Imperva", TERMINAL, ("incapsula incident id",)),
    ("sucuri_firewall", "Sucuri", TERMINAL, ("sucuri website firewall", "access denied")),
    # Challenge: a browser may pass
    ("cloudflare_challenge", "Cloudflare", CHALLENGE, ("cf-chl",)),
    ("cloudflare_challenge", "Cloudflare", CHALLENGE, ("just a moment...", "cloudflare")),
    ("cloudflare_challenge", "Cloudflare", CHALLENGE, ("attention required!", "cloudflare")),
    ("datadome", "DataDome", CHALLENGE, ("captcha-delivery.com",)),
    ("perimeterx", "HUMAN/PerimeterX", CHALLENGE, ("px-captcha",)),
    ("perimeterx", "HUMAN/PerimeterX", CHALLENGE, ("_pxappid",)),
    ("aws_waf_challenge", "AWS WAF", CHALLENGE, ("awswaf",)),
    ("hcaptcha", "", CHALLENGE, ("hcaptcha.com/1/api.js",)),
    ("recaptcha", "", CHALLENGE, ("google.com/recaptcha", "verify")),
    ("captcha_path", "", CHALLENGE, ("verify/captcha",)),
    ("traffic_check", "", CHALLENGE, ("verify/traffic",)),
    ("verify_human", "", CHALLENGE, ("verify you are human",)),
    ("verify_human", "", CHALLENGE, ("are you a robot",)),
    ("verify_human", "", CHALLENGE, ("click on the checkbox to continue",)),
    ("verify_human_ptbr", "", CHALLENGE, ("não é um robô",)),
    ("verify_human_ptbr", "", CHALLENGE, ("você precisa verificar",)),
    ("bot_protection", "", CHALLENGE, ("bot protection",)),
    ("access_denied", "", CHALLENGE, ("access denied",)),
    ("too_many_requests", "", RATE_LIMITED, ("too many requests",)),
]

_SHORT_PAGE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("access_denied_page", ("<title>access denied</title>", "<h1>access denied</h1>")),
    ("403_forbidden_page", ("<title>403 forbidden</title>", "<h1>403 forbidden</h1>")),
]

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _lower_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    return {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}


def detect(html: str | bytes | None, status: int | None = None,
           headers: Mapping[str, str] | None = None) -> Block | None:
    """Return the :class:`Block` the answer looks like, or ``None`` for a normal page.

    ``status`` and ``headers`` are optional; with them, the answer is classified more surely
    (``cf-mitigated: challenge``, ``server: AkamaiGHost`` with 403, 429).
    """
    h = _lower_headers(headers)
    if status == 429:
        return Block(RATE_LIMITED, "http_429")
    if h.get("cf-mitigated") == "challenge":
        return Block(CHALLENGE, "cloudflare_challenge", "Cloudflare")
    if "x-datadome" in h and status in (401, 403):
        return Block(CHALLENGE, "datadome", "DataDome")
    if status == 403 and "akamaighost" in h.get("server", ""):
        return Block(TERMINAL, "akamai_403", "Akamai")

    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="ignore")
    if not html:
        return None
    head = html[:HEAD_CHARS].lower()

    if len(html) < SHORT_PAGE:
        for reason, needles in _SHORT_PAGE_RULES:
            if any(n in head for n in needles):
                return Block(TERMINAL, reason)

    for reason, vendor, kind, needles in _BODY_RULES:
        if all(n in head for n in needles):
            return Block(kind, reason, vendor)

    m = _TITLE.search(html[:SHORT_PAGE])
    if m and "cloudflare" in m.group(1).lower():
        return Block(CHALLENGE, "cloudflare_title", "Cloudflare")
    return None


def retry_after_seconds(headers: Mapping[str, str] | None, default: float = 60.0) -> float:
    """Seconds asked by a ``Retry-After`` header (seconds or HTTP date), else ``default``."""
    value = _lower_headers(headers).get("retry-after")
    if not value:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone
    try:
        when = parsedate_to_datetime(value)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return default

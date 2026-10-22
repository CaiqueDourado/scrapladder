"""Pace per domain, honour 429 and robots.txt."""

from __future__ import annotations

import threading
import time
import urllib.robotparser
from urllib.parse import urlsplit


def domain_of(url: str) -> str:
    return (urlsplit(url).hostname or url).lower()


class Throttle:
    """At least ``min_interval`` seconds between requests to the same domain.

    ``cool_down(domain, seconds)`` pushes the next allowed request further, which is what a
    ``429 Retry-After`` asks for. ``wait(domain)`` sleeps until the domain is allowed again,
    unless that is more than ``max_wait`` away, in which case it returns the remaining seconds
    without sleeping, so the caller can decide to come back later.
    """

    def __init__(self, min_interval: float = 4.0, max_wait: float = 300.0, clock=time.monotonic, sleep=time.sleep):
        self.min_interval = min_interval
        self.max_wait = max_wait
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()
        self._clock, self._sleep = clock, sleep

    def wait(self, domain: str) -> float:
        with self._lock:
            now = self._clock()
            remaining = self._next.get(domain, 0.0) - now
            if remaining > self.max_wait:
                return remaining
            start = max(now, self._next.get(domain, 0.0))
            self._next[domain] = start + self.min_interval
        if remaining > 0:
            self._sleep(remaining)
        return 0.0

    def cool_down(self, domain: str, seconds: float) -> None:
        with self._lock:
            self._next[domain] = max(self._next.get(domain, 0.0), self._clock() + seconds)

    def remaining(self, domain: str) -> float:
        return max(0.0, self._next.get(domain, 0.0) - self._clock())


class Robots:
    """robots.txt cache. Unreachable robots.txt counts as allow-all, as most crawlers do."""

    def __init__(self, user_agent: str = "*", fetch=None):
        self.user_agent = user_agent
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._fetch = fetch  # callable(url) -> (status, text); None uses urllib
        self._lock = threading.Lock()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        root = f"{parts.scheme}://{parts.netloc}"
        with self._lock:
            rp = self._cache.get(root)
        if rp is None:
            rp = self._load(root)
            with self._lock:
                self._cache[root] = rp
        return rp.can_fetch(self.user_agent, url)

    def _load(self, root: str) -> urllib.robotparser.RobotFileParser:
        rp = urllib.robotparser.RobotFileParser()
        try:
            if self._fetch:
                status, text = self._fetch(root + "/robots.txt")
            else:
                from urllib.request import urlopen
                with urlopen(root + "/robots.txt", timeout=10) as r:
                    status, text = r.status, r.read().decode("utf-8", "ignore")
        except Exception:
            status, text = 0, ""
        if status == 200:
            rp.parse(text.splitlines())
        else:
            rp.parse([])
        return rp

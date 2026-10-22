import json

import pytest

from scrapladder import (BLOCKED, DISALLOWED, NOT_FOUND, OK, RATE_LIMITED, TERMINAL, Ladder, Memory, Robots,
                         Throttle)
from scrapladder.methods import Method, Response

PAGE = "<html><title>Fone KZ ZSN</title>" + "texto " * 200 + "</html>"
CF = "<html><title>Just a moment...</title>cloudflare</html>"
AKAMAI = "<html><title>Access Denied</title>Reference #18.1 errors.edgesuite.net</html>"


class Fake(Method):
    """A rung that answers from a script: {domain: Response or Exception}."""

    def __init__(self, name, answers, priority=0.5, paid=False):
        super().__init__()
        self.name, self.default_priority, self.paid = name, priority, paid
        self.answers, self.calls = answers, []

    def fetch(self, url):
        self.calls.append(url)
        a = self.answers.get(url.split("/")[2], Response(200, PAGE))
        if isinstance(a, Exception):
            raise a
        return a


def ladder(methods, **kw):
    kw.setdefault("respect_robots", False)
    kw.setdefault("throttle", Throttle(0, sleep=lambda s: None))
    return Ladder(methods, **kw)


def test_first_rung_that_gets_the_page_wins_and_is_remembered(tmp_path):
    http = Fake("http", {"a.com": Response(403, CF)}, priority=0.9)
    browser = Fake("browser", {}, priority=0.4)
    mem = tmp_path / "m.json"
    with ladder([http, browser], memory=str(mem)) as lad:
        r = lad.fetch("https://a.com/p/1")
        assert r.ok and r.method == "browser"
        assert [a.outcome for a in r.attempts] == ["challenged", "ok"]
        # next URL on the same domain starts with the winner
        r2 = lad.fetch("https://a.com/p/2")
        assert [a.method for a in r2.attempts] == ["browser"]
    saved = json.loads(mem.read_text())
    assert saved["domains"]["a.com"]["winners"] == ["browser"]


def test_rung_blocked_three_times_is_skipped():
    http = Fake("http", {"a.com": Response(403, CF)}, priority=0.9)
    browser = Fake("browser", {"a.com": Response(403, CF)}, priority=0.4)
    lad = ladder([http, browser])
    for _ in range(3):
        assert lad.fetch("https://a.com/x").outcome == BLOCKED
    assert lad.order("a.com") == []


def test_terminal_block_stops_the_ladder():
    http = Fake("http", {"a.com": Response(403, AKAMAI)}, priority=0.9)
    browser = Fake("browser", {}, priority=0.4)
    r = ladder([http, browser]).fetch("https://a.com/x")
    assert r.outcome == TERMINAL and browser.calls == []


def test_429_stops_and_cools_down_the_domain():
    clock = [0.0]
    th = Throttle(0, max_wait=10, clock=lambda: clock[0], sleep=lambda s: None)
    http = Fake("http", {"a.com": Response(429, "", {"Retry-After": "120"})}, priority=0.9)
    browser = Fake("browser", {}, priority=0.4)
    lad = ladder([http, browser], throttle=th)
    r = lad.fetch("https://a.com/x")
    assert r.outcome == RATE_LIMITED and r.retry_after == 120 and browser.calls == []
    # the next fetch does not hammer the domain: it returns at once with the time left
    r2 = lad.fetch("https://a.com/y")
    assert r2.outcome == RATE_LIMITED and r2.retry_after == pytest.approx(120)
    assert http.calls == ["https://a.com/x"]


def test_404_is_final():
    http = Fake("http", {"a.com": Response(404, "nope")})
    other = Fake("other", {}, priority=0.1)
    r = ladder([http, other]).fetch("https://a.com/x")
    assert r.outcome == NOT_FOUND and other.calls == []


def test_errors_and_rejected_pages_fall_through():
    http = Fake("http", {"a.com": TimeoutError()}, priority=0.9)
    thin = Fake("thin", {"a.com": Response(200, "<html>home</html>")}, priority=0.8)
    good = Fake("good", {}, priority=0.1)
    r = ladder([http, thin, good]).fetch("https://a.com/x")
    assert r.ok and r.method == "good"
    assert [(a.outcome, a.reason) for a in r.attempts[:2]] == [("error", "TimeoutError"), ("rejected", "too_short")]


def test_must_contain_rejects_the_wrong_page():
    http = Fake("http", {}, priority=0.9)
    r = ladder([http]).fetch("https://a.com/x", must_contain="ZSX Pro")
    assert r.outcome == "failed" and r.attempts[0].reason == "missing_text"


def test_paid_rungs_come_last_unless_they_won_before():
    paid = Fake("api", {}, priority=0.99, paid=True)
    free = Fake("http", {}, priority=0.1)
    lad = ladder([paid, free])
    assert [m.name for m in lad.order("a.com")] == ["http", "api"]
    lad.memory.record_success("b.com", "api")
    assert [m.name for m in lad.order("b.com")] == ["api", "http"]


def test_robots_disallow():
    robots = Robots(fetch=lambda url: (200, "User-agent: *\nDisallow: /private"))
    r = ladder([Fake("http", {})], robots=robots, respect_robots=True).fetch("https://a.com/private/1")
    assert r.outcome == DISALLOWED


def test_old_cache_format_is_read(tmp_path):
    f = tmp_path / "domain_method_cache.json"
    f.write_text(json.dumps({"a.com": ["curl_cffi", "playwright"], "b.com": "httpx"}))
    mem = Memory(f)
    assert mem.winners("a.com") == ["curl_cffi", "playwright"] and mem.winners("b.com") == ["httpx"]


def test_explain_tries_every_rung_without_learning():
    http = Fake("http", {"a.com": Response(403, CF)}, priority=0.9)
    browser = Fake("browser", {}, priority=0.4)
    lad = ladder([http, browser])
    rows = lad.explain("https://a.com/x")
    assert [(r.method, r.outcome) for r in rows] == [("http", "challenged"), ("browser", "ok")]
    assert lad.memory.winners("a.com") == []

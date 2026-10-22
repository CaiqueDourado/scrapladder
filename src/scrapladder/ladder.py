"""The ladder: try fetch methods from cheapest to heaviest, learn what works per domain."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import blocks
from .memory import Memory
from .methods import Method, default_methods
from .politeness import Robots, Throttle, domain_of

# Outcomes of one attempt
OK = "ok"
NOT_FOUND = "not_found"
CHALLENGED = "challenged"
TERMINAL = "terminal_block"
RATE_LIMITED = "rate_limited"
REJECTED = "rejected"     # got a page, but it failed the content checks
ERROR = "error"           # network error, timeout, 5xx
# Extra outcomes of a whole fetch
BLOCKED = "blocked"       # every rung was challenged
FAILED = "failed"
DISALLOWED = "disallowed"  # robots.txt


@dataclass
class Attempt:
    method: str
    outcome: str
    status: int | None = None
    reason: str = ""
    seconds: float = 0.0
    size: int = 0


@dataclass
class Result:
    url: str
    outcome: str
    html: str = ""
    method: str = ""
    status: int | None = None
    final_url: str = ""
    attempts: list[Attempt] = field(default_factory=list)
    block: blocks.Block | None = None
    retry_after: float = 0.0

    @property
    def ok(self) -> bool:
        return self.outcome == OK

    def summary(self) -> str:
        steps = " > ".join(f"{a.method}:{a.outcome}" + (f"({a.reason})" if a.reason else "") for a in self.attempts)
        return f"{self.outcome} via {self.method or '-'} [{steps}]"


class Ladder:
    """Fetch pages trying methods in order, learning per domain which one works.

    >>> with Ladder(memory="scrapladder.json") as ladder:
    ...     r = ladder.fetch("https://example.com/product/1", must_contain="Product")
    ...     if r.ok: print(r.method, len(r.html))

    Parameters
    ----------
    methods:
        Rungs to use. Default: every rung installed here (see :func:`methods.default_methods`).
    memory:
        A :class:`Memory`, a path to its JSON file, or ``None`` for an in-memory one.
    min_interval:
        Seconds between requests to the same domain (default 4).
    respect_robots:
        Check robots.txt before fetching (default True).
    min_length:
        A page shorter than this is not accepted (default 500 characters).
    must_contain:
        Text the page must contain (case-insensitive), e.g. the product name. Catches the
        pages that are neither blocked nor the one you wanted (home page, "item not found").
    accept:
        Extra check ``accept(html) -> bool``.
    max_wait:
        Longest wait for a domain's turn (or a ``Retry-After``) before giving up with
        ``rate_limited`` and letting the caller come back later.
    """

    def __init__(self, methods: Iterable[Method] | None = None, *, memory: Memory | str | None = None,
                 min_interval: float = 4.0, respect_robots: bool = True, robots_user_agent: str = "*",
                 min_length: int = 500, must_contain: str | None = None,
                 accept: Callable[[str], bool] | None = None, max_wait: float = 300.0,
                 throttle: Throttle | None = None, robots: Robots | None = None,
                 log: Callable[[str], None] | None = None) -> None:
        self.methods = list(methods) if methods is not None else default_methods()
        if not self.methods:
            raise ValueError("no fetch method available: pip install 'scrapladder[http]'")
        self.memory = memory if isinstance(memory, Memory) else Memory(memory)
        self.throttle = throttle or Throttle(min_interval, max_wait)
        self.robots = robots or (Robots(robots_user_agent) if respect_robots else None)
        self.min_length, self.must_contain, self.accept = min_length, must_contain, accept
        self.log = log or (lambda msg: None)

    # ---- order ---------------------------------------------------------------------------
    def order(self, domain: str) -> list[Method]:
        """Rungs for ``domain``: past winners, then free rungs by priority, then paid ones.

        Rungs blocked ``fail_threshold`` times on the domain are left out.
        """
        by_name = {m.name: m for m in self.methods}
        skip = self.memory.blocked_methods(domain)
        winners = [by_name[n] for n in self.memory.winners(domain) if n in by_name and n not in skip]
        rest = [m for m in self.methods if m not in winners and m.name not in skip]
        prio = lambda m: -self.memory.priority(m.name, m.default_priority, m.paid)
        free = sorted((m for m in rest if not m.paid), key=prio)
        paid = sorted((m for m in rest if m.paid), key=prio)
        return winners + free + paid

    # ---- fetch ---------------------------------------------------------------------------
    def fetch(self, url: str, *, must_contain: str | None = None,
              accept: Callable[[str], bool] | None = None) -> Result:
        domain = domain_of(url)
        if self.robots and not self.robots.allowed(url):
            return Result(url, DISALLOWED)
        wait = self.throttle.wait(domain)
        if wait > 0:
            return Result(url, RATE_LIMITED, retry_after=wait)

        result = Result(url, FAILED)
        challenged = False
        for method in self.order(domain):
            attempt, html, resp, block = self._try(method, url, must_contain, accept)
            result.attempts.append(attempt)
            self.log(f"{domain} {method.name}: {attempt.outcome} {attempt.reason}".rstrip())

            if attempt.outcome == OK:
                self.memory.record_success(domain, method.name)
                self.memory.save()
                result.outcome, result.html, result.method = OK, html, method.name
                result.status, result.final_url = resp.status, resp.url or url
                return result
            if attempt.outcome == NOT_FOUND:
                result.outcome, result.method, result.status = NOT_FOUND, method.name, resp.status
                return result
            if attempt.outcome == RATE_LIMITED:
                seconds = blocks.retry_after_seconds(resp.headers if resp else None)
                self.throttle.cool_down(domain, seconds)
                result.outcome, result.block, result.retry_after = RATE_LIMITED, block, seconds
                return result
            if attempt.outcome == TERMINAL:
                # Network/CDN-level block: every rung leaves from the same IP. Stop here.
                result.outcome, result.block, result.method = TERMINAL, block, method.name
                return result
            if attempt.outcome == CHALLENGED:
                challenged = True
                result.block = block
                self.memory.record_block(domain, method.name)
            else:
                self.memory.record_failure(method.name)

        if challenged:
            result.outcome = BLOCKED
        return result

    def _try(self, method: Method, url: str, must_contain, accept):
        start = time.monotonic()
        try:
            resp = method.fetch(url)
        except Exception as e:  # network error, timeout, browser crash
            return Attempt(method.name, ERROR, reason=type(e).__name__, seconds=time.monotonic() - start), "", None, None
        secs = time.monotonic() - start
        html = resp.html or ""
        att = Attempt(method.name, OK, resp.status, seconds=secs, size=len(html))

        if resp.status in (404, 410):
            att.outcome = NOT_FOUND
            return att, html, resp, None
        block = blocks.detect(html, resp.status, resp.headers)
        if block is None and resp.status in (401, 403):
            block = blocks.Block(blocks.CHALLENGE, f"http_{resp.status}")
        if block:
            att.outcome = {blocks.TERMINAL: TERMINAL, blocks.RATE_LIMITED: RATE_LIMITED}.get(block.kind, CHALLENGED)
            att.reason = block.reason
            return att, html, resp, block
        if resp.status is not None and resp.status >= 400:
            att.outcome, att.reason = ERROR, f"http_{resp.status}"
            return att, html, resp, None

        why = self._reject_reason(html, must_contain or self.must_contain, accept or self.accept)
        if why:
            att.outcome, att.reason = REJECTED, why
        return att, html, resp, None

    def _reject_reason(self, html: str, must_contain, accept) -> str:
        if len(html) < self.min_length:
            return "too_short"
        if must_contain and must_contain.lower() not in html.lower():
            return "missing_text"
        if accept and not accept(html):
            return "accept_false"
        return ""

    # ---- diagnostics ---------------------------------------------------------------------
    def explain(self, url: str) -> list[Attempt]:
        """Try EVERY rung on ``url`` (memory is neither used nor updated) and report each one.

        Use it on a new site to see which rungs get the page, how fast, and what blocks the
        others. Rungs still wait ``min_interval`` between them.
        """
        domain = domain_of(url)
        out = []
        for method in self.methods:
            self.throttle.wait(domain)
            out.append(self._try(method, url, None, None)[0])
        return out

    def close(self) -> None:
        for m in self.methods:
            try:
                m.close()
            except Exception:
                pass
        self.memory.save()

    def __enter__(self) -> "Ladder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

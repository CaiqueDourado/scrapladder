"""What the ladder remembers between runs.

Per domain:

- **winners**: the last methods that got a real page, most recent first (two by default). They
  are tried first next time, so a site that only answers to a browser does not pay for three
  failed HTTP attempts on every URL.
- **fails**: how many times each method hit a block on that domain. At ``fail_threshold``
  (three by default) the method is skipped for that domain. A success resets its counter.

Per method, across all domains, a priority mixes a moving average of recent results with a
default: ``0.5 * ewma + 0.3 * last five + 0.2 * overall``, blended half and half with the
method's default priority. Paid methods are scaled down so they stay last resort.

Everything is a plain JSON file, readable and editable by hand. The old format of the
author's crawler, ``{"domain": ["method", ...]}``, is read as winners.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

EWMA_ALPHA = 0.25
HISTORY = 10
PAID_FACTOR = 0.3


@dataclass
class MethodStats:
    success: int = 0
    total: int = 0
    ewma: float = 0.5
    recent: list[bool] = field(default_factory=list)

    def add(self, ok: bool) -> None:
        self.total += 1
        self.success += int(ok)
        self.ewma = float(ok) if self.total == 1 else EWMA_ALPHA * float(ok) + (1 - EWMA_ALPHA) * self.ewma
        self.recent.append(ok)
        del self.recent[:-HISTORY]

    def priority(self, default: float, paid: bool = False) -> float:
        if self.total == 0:
            learned = default
        else:
            last5 = self.recent[-5:]
            recent_rate = sum(last5) / len(last5)
            overall = self.success / self.total
            learned = 0.5 * (0.5 * self.ewma + 0.3 * recent_rate + 0.2 * overall) + 0.5 * default
        return learned * (PAID_FACTOR if paid else 1.0)


@dataclass
class DomainState:
    winners: list[str] = field(default_factory=list)
    fails: dict[str, int] = field(default_factory=dict)


class Memory:
    """Domain winners, block counters and method statistics, optionally kept in a JSON file."""

    def __init__(self, path: str | os.PathLike | None = None, *, keep_winners: int = 2,
                 fail_threshold: int = 3) -> None:
        self.path = Path(path) if path else None
        self.keep_winners = keep_winners
        self.fail_threshold = fail_threshold
        self.domains: dict[str, DomainState] = {}
        self.methods: dict[str, MethodStats] = {}
        self._lock = threading.Lock()
        if self.path and self.path.exists():
            self.load()

    # ---- queries -------------------------------------------------------------------------
    def winners(self, domain: str) -> list[str]:
        st = self.domains.get(domain)
        return list(st.winners) if st else []

    def blocked_methods(self, domain: str) -> set[str]:
        st = self.domains.get(domain)
        if not st:
            return set()
        return {m for m, n in st.fails.items() if n >= self.fail_threshold}

    def priority(self, method: str, default: float, paid: bool = False) -> float:
        return self.methods.get(method, MethodStats()).priority(default, paid)

    # ---- updates -------------------------------------------------------------------------
    def record_success(self, domain: str, method: str) -> None:
        with self._lock:
            st = self.domains.setdefault(domain, DomainState())
            if method in st.winners:
                st.winners.remove(method)
            st.winners.insert(0, method)
            del st.winners[self.keep_winners:]
            st.fails.pop(method, None)
            self.methods.setdefault(method, MethodStats()).add(True)

    def record_block(self, domain: str, method: str) -> int:
        """Count a block for ``method`` on ``domain``; returns the new count."""
        with self._lock:
            st = self.domains.setdefault(domain, DomainState())
            st.fails[method] = st.fails.get(method, 0) + 1
            self.methods.setdefault(method, MethodStats()).add(False)
            return st.fails[method]

    def record_failure(self, method: str) -> None:
        """A failure that says nothing about the domain (timeout, empty page)."""
        with self._lock:
            self.methods.setdefault(method, MethodStats()).add(False)

    def forget(self, domain: str) -> None:
        with self._lock:
            self.domains.pop(domain, None)

    # ---- persistence ---------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "domains": {d: {"winners": s.winners, "fails": s.fails} for d, s in sorted(self.domains.items())},
            "methods": {m: {"success": s.success, "total": s.total, "ewma": round(s.ewma, 4), "recent": s.recent}
                        for m, s in sorted(self.methods.items())},
        }

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if "domains" not in data:  # old format: {"domain": ["method", ...]} or {"domain": "method"}
            data = {"domains": {d: {"winners": [v] if isinstance(v, str) else list(v)} for d, v in data.items()}}
        for d, v in data.get("domains", {}).items():
            self.domains[d] = DomainState(list(v.get("winners", []))[: self.keep_winners], dict(v.get("fails", {})))
        for m, v in data.get("methods", {}).items():
            self.methods[m] = MethodStats(v.get("success", 0), v.get("total", 0), v.get("ewma", 0.5), list(v.get("recent", [])))

    def save(self) -> None:
        if not self.path:
            return
        with self._lock:
            payload = json.dumps(self.to_dict(), indent=1, ensure_ascii=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".scrapladder-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, self.path)  # atomic: a crash never leaves half a file

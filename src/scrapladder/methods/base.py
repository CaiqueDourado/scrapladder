from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


@dataclass
class Response:
    status: int | None
    html: str
    headers: Mapping[str, str] = field(default_factory=dict)
    url: str = ""


class MethodUnavailable(RuntimeError):
    """The method's package (or API key) is not installed or configured."""


class Method:
    """One rung of the ladder.

    Subclasses set ``name``, ``default_priority`` (0..1, higher is tried first), ``paid``
    (a paid scraping API: always after the free rungs unless it already won on the domain)
    and implement :meth:`fetch`. ``fetch`` returns a :class:`Response` for any HTTP answer,
    including 403 and 404, and raises for network errors and timeouts.
    """

    name = "method"
    default_priority = 0.5
    paid = False

    def __init__(self, *, timeout: float = 30.0, headers: Mapping[str, str] | None = None) -> None:
        self.timeout = timeout
        self.headers = {**DEFAULT_HEADERS, **(headers or {})}

    def available(self) -> bool:
        try:
            self.check()
            return True
        except MethodUnavailable:
            return False

    def check(self) -> None:
        """Raise :class:`MethodUnavailable` if the method cannot run here."""

    def fetch(self, url: str) -> Response:  # pragma: no cover - interface
        raise NotImplementedError

    def close(self) -> None:
        """Release browsers or sessions. Safe to call twice."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"


def require(module: str, extra: str) -> None:
    import importlib.util
    if importlib.util.find_spec(module) is None:
        raise MethodUnavailable(f"{module} is not installed (pip install 'scrapladder[{extra}]')")

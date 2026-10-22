"""scrapladder: fetch web pages by climbing a ladder of methods, learning per domain which rung works."""

from . import blocks, methods
from .blocks import Block, detect
from .ladder import (BLOCKED, CHALLENGED, DISALLOWED, ERROR, FAILED, NOT_FOUND, OK, RATE_LIMITED,
                     REJECTED, TERMINAL, Attempt, Ladder, Result)
from .memory import Memory
from .politeness import Robots, Throttle, domain_of

__version__ = "0.1.0"
__all__ = ["Ladder", "Result", "Attempt", "Memory", "Block", "detect", "Throttle", "Robots", "domain_of",
           "blocks", "methods", "OK", "NOT_FOUND", "CHALLENGED", "TERMINAL", "RATE_LIMITED", "REJECTED",
           "ERROR", "BLOCKED", "FAILED", "DISALLOWED"]

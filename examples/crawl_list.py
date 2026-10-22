"""Fetch a list of URLs, save each page, print what happened.

    python examples/crawl_list.py urls.txt pages/
"""
import hashlib
import sys
from pathlib import Path

from scrapladder import Ladder

urls = [u.strip() for u in Path(sys.argv[1]).read_text().splitlines() if u.strip()]
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
later = []

with Ladder(memory=out / "scrapladder.json", log=print) as ladder:
    for url in urls:
        r = ladder.fetch(url)
        print(url, "->", r.summary())
        if r.ok:
            (out / (hashlib.sha1(url.encode()).hexdigest()[:12] + ".html")).write_text(r.html, encoding="utf-8")
        elif r.outcome == "rate_limited":
            later.append(url)  # come back after r.retry_after seconds

if later:
    print(f"{len(later)} URLs to retry later (rate limited)")

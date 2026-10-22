# Changelog

## [0.1.0] - 2026-10-22

### Added
- `Ladder`: tries fetch methods in order and remembers per domain the last two winners and the rungs blocked three times.
- Rungs: requests, httpx, curl_cffi (browser TLS fingerprint), Playwright, Scrapling, Camoufox, and paid scraping APIs (ScraperAPI, ScrapingBee, ScrapingDog, Scrape.do) as last resort.
- Block detection (`blocks.detect`): terminal (Akamai, WAF 403, Imperva, Sucuri), challenge (Cloudflare, DataDome, PerimeterX, AWS WAF, CAPTCHA, pt-BR robot checks), rate limit (429).
- Politeness: per-domain interval, `Retry-After`, robots.txt.
- Memory in a JSON file (atomic writes), with method priority learned by moving average; reads the older `{"domain": [methods]}` format.
- CLI: `methods`, `explain`, `fetch`, `stats`.

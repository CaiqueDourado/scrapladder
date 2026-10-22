from scrapladder import blocks
from scrapladder.blocks import CHALLENGE, RATE_LIMITED, TERMINAL, detect

LONG_PAGE = "<html><head><title>Fone XYZ</title></head><body>" + "conteúdo real " * 1000 + "</body></html>"


def test_normal_page_is_not_a_block():
    assert detect(LONG_PAGE, 200) is None


def test_long_page_mentioning_too_many_requests_late_is_not_a_block():
    html = LONG_PAGE + "<script>throw 'too many requests'</script>"
    assert detect(html, 200) is None


def test_akamai_access_denied_is_terminal():
    html = "<html><title>Access Denied</title>You don't have permission to access ... Reference #18.22bb1002 errors.edgesuite.net</html>"
    b = detect(html, 403)
    assert b.kind == TERMINAL and b.terminal


def test_short_403_page_is_terminal():
    assert detect("<html><head><title>403 Forbidden</title></head></html>", 403).kind == TERMINAL


def test_cloudflare_header_is_challenge():
    b = detect("<html>...</html>", 403, {"CF-Mitigated": "challenge"})
    assert (b.kind, b.vendor) == (CHALLENGE, "Cloudflare")


def test_cloudflare_just_a_moment_is_challenge():
    html = "<html><head><title>Just a moment...</title></head><body>cloudflare</body></html>"
    assert detect(html, 503).reason == "cloudflare_challenge"


def test_datadome_is_challenge():
    html = "<html><script src='https://geo.captcha-delivery.com/captcha/'></script></html>"
    assert detect(html, 403).vendor == "DataDome"


def test_ptbr_robot_check_is_challenge():
    assert detect("<p>Verifique que você não é um robô</p>", 200).kind == CHALLENGE


def test_429_is_rate_limited():
    assert detect("", 429).kind == RATE_LIMITED


def test_retry_after_seconds_and_default():
    assert blocks.retry_after_seconds({"Retry-After": "120"}) == 120
    assert blocks.retry_after_seconds({}, default=7) == 7
    assert blocks.retry_after_seconds({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}) == 0


def test_bytes_are_accepted():
    assert detect(b"<title>Attention Required! | Cloudflare</title>", 403).kind == CHALLENGE

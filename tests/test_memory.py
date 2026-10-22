from scrapladder.memory import Memory, MethodStats
from scrapladder.politeness import Throttle


def test_success_resets_fail_counter_and_keeps_two_winners():
    m = Memory()
    m.record_block("a.com", "x")
    m.record_block("a.com", "x")
    m.record_success("a.com", "x")
    m.record_success("a.com", "y")
    m.record_success("a.com", "z")
    assert m.winners("a.com") == ["z", "y"]
    assert m.blocked_methods("a.com") == set()


def test_priority_learns_and_paid_is_scaled():
    s = MethodStats()
    assert s.priority(0.6) == 0.6
    for ok in (True, True, False, True):
        s.add(ok)
    assert 0.6 < s.priority(0.6) < 0.8
    assert s.priority(0.6, paid=True) < s.priority(0.6)


def test_memory_round_trip(tmp_path):
    f = tmp_path / "m.json"
    m = Memory(f)
    m.record_success("a.com", "curl_cffi")
    m.record_block("a.com", "httpx")
    m.save()
    m2 = Memory(f)
    assert m2.winners("a.com") == ["curl_cffi"] and m2.domains["a.com"].fails == {"httpx": 1}
    assert m2.methods["curl_cffi"].total == 1


def test_throttle_spaces_requests_per_domain():
    t, slept = [0.0], []
    th = Throttle(4, clock=lambda: t[0], sleep=slept.append)
    th.wait("a.com")
    th.wait("a.com")
    th.wait("b.com")
    assert slept == [4]

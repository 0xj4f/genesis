from concurrent.futures import ThreadPoolExecutor

import pytest

from app.utils.security_store import MemorySecurityStore, SecurityStoreUnavailable, get_security_store


def test_process_uses_one_store_without_a_service():
    assert get_security_store() is get_security_store()
    assert isinstance(get_security_store(), MemorySecurityStore)


def test_expiry_queue_is_bounded_by_tracked_rate_keys():
    clock = [1000.0]
    store = MemorySecurityStore(max_keys=100, clock=lambda: clock[0])
    for _ in range(50):
        for ip in range(100):
            assert store.check_rate(str(ip), 100, 60) == 0
    assert len(store.rates) == len(store._rate_expiries) == 100
    with pytest.raises(SecurityStoreUnavailable):
        store.check_rate("overflow", 100, 60)
    clock[0] += 60
    assert store.check_rate("after-expiry", 100, 60) == 0
    assert len(store.rates) == len(store._rate_expiries) == 1


def test_hot_keys_are_rescheduled_without_premature_expiry():
    clock = [1000.0]
    store = MemorySecurityStore(clock=lambda: clock[0])
    assert store.check_rate("ip", 2, 1) == 0
    clock[0] += 0.9
    assert store.check_rate("ip", 2, 1) == 0
    clock[0] += 0.2
    assert store.check_rate("ip", 2, 1) == 0
    assert store.check_rate("ip", 2, 1) == 1
    assert len(store._rate_expiries) == 1
    clock[0] += 1.01
    assert store.check_rate("ip", 2, 1) == 0
    assert len(store._rate_expiries) == 1


def test_concurrent_request_check_is_atomic_at_full_cardinality():
    store = MemorySecurityStore(max_keys=10000)
    for ip in range(9999):
        store.check_rate(str(ip), 30, 60)
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: store.check_rate("target", 30, 60), range(100)))
    assert results.count(0) == 30
    assert len(store.rates) == len(store._rate_expiries) == 10000


def test_sso_state_capacity_ttl_and_consumption_are_bounded():
    clock = [1000.0]
    store = MemorySecurityStore(max_keys=2, clock=lambda: clock[0])
    store.put_state("long-lived", {"state": 1}, 600)
    store.put_state("short-lived", {"state": 2}, 1)
    with pytest.raises(SecurityStoreUnavailable):
        store.put_state("overflow", {}, 600)
    clock[0] += 2
    store.put_state("replacement", {"state": 3}, 600)
    assert len(store.states) == 2
    assert store.pop_state("short-lived") is None
    assert store.pop_state("replacement") == {"state": 3}
    assert store.pop_state("replacement") is None
    assert len(store.states) == 1

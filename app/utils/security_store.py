"""Bounded, thread-safe security state for the existing single-worker deployment."""

import heapq
import math
import threading
import time
from collections import OrderedDict, deque
from functools import lru_cache

class SecurityStoreUnavailable(Exception):
    pass


class MemorySecurityStore:
    def __init__(self, max_keys=10000, clock=time.monotonic):
        self.rates = {}
        # One expiry entry per tracked rate key. Active keys are rescheduled
        # lazily, avoiding both a full scan and a new heap entry on every hit.
        self._rate_expiries = []
        self.states = OrderedDict()
        # Per-account login failures: key -> [recent failure times, locked_until, lockouts].
        # Least-recently-used entries are evicted instead of failing closed, so a
        # flood of unknown usernames cannot block every login.
        self.failures = OrderedDict()
        self.max_keys = max_keys
        self.clock = clock
        self.lock = threading.Lock()

    def _expire_rates(self, now):
        while self._rate_expiries and self._rate_expiries[0][0] <= now:
            _, key = heapq.heappop(self._rate_expiries)
            expires_at, _ = self.rates[key]
            if expires_at <= now:
                del self.rates[key]
            else:
                heapq.heappush(self._rate_expiries, (expires_at, key))

    def check_rate(self, key: str, limit: int, window: int) -> int:
        with self.lock:
            now = self.clock()
            self._expire_rates(now)
            if key not in self.rates:
                if len(self.rates) >= self.max_keys:
                    raise SecurityStoreUnavailable()
                self.rates[key] = (now + window, deque())
                heapq.heappush(self._rate_expiries, (now + window, key))
            _, hits = self.rates[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window - now))
            hits.append(now)
            self.rates[key] = (now + window, hits)
            return 0

    def put_state(self, key: str, value: dict, ttl: int):
        with self.lock:
            now = self.clock()
            # SSO writes are infrequent and separate from the request limiter's
            # hot path. Handle different TTLs without retaining consumed keys.
            for expired in [k for k, (expiry, _) in self.states.items() if expiry <= now]:
                del self.states[expired]
            if key not in self.states and len(self.states) >= self.max_keys:
                raise SecurityStoreUnavailable()
            self.states[key] = (now + ttl, value)

    def pop_state(self, key: str):
        with self.lock:
            item = self.states.pop(key, None)
            return item[1] if item and item[0] > self.clock() else None


    def login_retry_after(self, key: str) -> int:
        """Seconds until this account may try again (0 when not locked)."""
        with self.lock:
            entry = self.failures.get(key)
            if not entry:
                return 0
            remaining = entry[1] - self.clock()
            return max(1, math.ceil(remaining)) if remaining > 0 else 0

    def record_login_failure(self, key: str, max_failures: int, window: int, max_lockout: int) -> int:
        """Record a failed attempt. Returns the lockout length when this failure
        locks the account; each further lockout doubles, up to max_lockout."""
        with self.lock:
            now = self.clock()
            entry = self.failures.pop(key, None)
            if entry is None or (not entry[0] and entry[1] <= now - window):
                entry = [deque(), 0.0, 0]
            hits = entry[0]
            while hits and hits[0] <= now - window:
                hits.popleft()
            hits.append(now)
            locked_for = 0
            if len(hits) >= max_failures:
                entry[2] += 1
                locked_for = min(60 * 2 ** (entry[2] - 1), max_lockout)
                entry[1] = now + locked_for
                hits.clear()
            self.failures[key] = entry
            while len(self.failures) > self.max_keys:
                self.failures.popitem(last=False)
            return locked_for

    def clear_login_failures(self, key: str) -> None:
        with self.lock:
            self.failures.pop(key, None)


@lru_cache()
def get_security_store():
    return MemorySecurityStore()

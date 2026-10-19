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


@lru_cache()
def get_security_store():
    return MemorySecurityStore()

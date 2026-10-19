"""Isolated limiter benchmark, using a saved baseline image and current source.

Server: python benchmarks/security_limiter.py serve --mode memory --keys 9000
Client: python benchmarks/security_limiter.py load --host bench-memory
Micro:  python benchmarks/security_limiter.py micro --mode memory --keys 9000

BENCH_SOURCE selects /app (saved Redis baseline) or /candidate (current source).
Redis is only used when explicitly benchmarking the removed baseline, whose
image already includes that dependency. It is not an application requirement.
The server is a synthetic health endpoint with no database or password hashing.
"""

import argparse
import asyncio
from collections import Counter
import importlib
import json
import math
import os
import platform
import resource
import statistics
import sys
import time
from uuid import uuid4


def percentile(values, q):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * q) - 1)] if values else 0


def get_store(mode, keys):
    sys.path.insert(0, os.environ.get("BENCH_SOURCE", "/candidate"))
    module = importlib.import_module("app.utils.security_store")
    if mode == "redis":
        store = module.RedisSecurityStore(os.environ["BENCH_REDIS_URL"])
    else:
        store = module.MemorySecurityStore()
    prefix = uuid4().hex
    for key in range(keys):
        # Keep synthetic active metadata stable across all load-test repeats.
        # The production request window still runs at one second.
        store.check_rate(f"seed:{prefix}:{key}", 10000, 600)
    return store


def serve(args):
    import uvicorn
    from fastapi import FastAPI

    store = get_store(args.mode, args.keys) if args.mode != "none" else None
    app = FastAPI()
    if store:
        module = importlib.import_module("app.middleware.security")
        settings_class = importlib.import_module("app.config").Settings
        module.get_security_store = lambda: store
        # Raise only the benchmark ceiling to measure allowed-request capacity;
        # the default production limits are tested separately for correctness.
        app.add_middleware(module.SecurityMiddleware, settings=settings_class(RATE_LIMIT_PER_SECOND=args.limit))

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "genesis-iam"}

    class SyntheticClients:
        async def __call__(self, scope, receive, send):
            # Benchmark-only IP simulation on a private, unpublished network.
            # Production middleware never reads this header.
            for name, value in scope.get("headers", []):
                if name == b"x-benchmark-client":
                    scope = {**scope, "client": (value.decode(), 12345)}
            await app(scope, receive, send)

    uvicorn.run(SyntheticClients(), host="0.0.0.0", port=8000, workers=1, access_log=False, proxy_headers=False)


async def one_request(reader, writer, host, ip):
    started = time.perf_counter()
    writer.write(f"GET /health HTTP/1.1\r\nHost: {host}\r\nX-Benchmark-Client: {ip}\r\nConnection: keep-alive\r\n\r\n".encode())
    await writer.drain()
    raw_headers = await reader.readuntil(b"\r\n\r\n")
    lines = raw_headers.split(b"\r\n")
    status = int(lines[0].split()[1])
    length = next(int(line.split(b":", 1)[1]) for line in lines if line.lower().startswith(b"content-length:"))
    await reader.readexactly(length)
    return (time.perf_counter() - started) * 1000, status


async def measure(host, duration, concurrency, paced=False):
    samples = []
    counts = Counter()
    cpu_before = time.process_time()
    started = time.perf_counter()
    deadline = started + duration

    async def worker(index):
        reader, writer = await asyncio.open_connection(host, 8000)
        next_request = started
        try:
            while time.perf_counter() < deadline:
                if paced:
                    await asyncio.sleep(max(0, next_request - time.perf_counter()))
                    if time.perf_counter() >= deadline:
                        break
                    next_request += 0.1
                latency, status = await one_request(reader, writer, host, f"192.0.2.{index + 1}")
                samples.append(latency)
                counts[status] += 1
        finally:
            writer.close()
            await writer.wait_closed()

    await asyncio.gather(*(worker(i) for i in range(concurrency)))
    elapsed = time.perf_counter() - started
    return {
        "requests": len(samples), "seconds": round(elapsed, 3),
        "requests_per_second": round(len(samples) / elapsed, 1),
        "latency_ms": {"p50": round(percentile(samples, 0.5), 3), "p95": round(percentile(samples, 0.95), 3), "p99": round(percentile(samples, 0.99), 3)},
        "status_counts": dict(counts), "client_cpu_seconds": round(time.process_time() - cpu_before, 3),
    }


async def load(args):
    await measure(args.host, 1, 4)  # Warmup, excluded from results.
    human = await measure(args.host, 5, 1, paced=True)
    trials = [await measure(args.host, args.seconds, args.concurrency) for _ in range(args.repeats)]
    print(json.dumps({"host": args.host, "paced_10_rps": human, "saturated_trials": trials,
        "median_requests_per_second": round(statistics.median(t["requests_per_second"] for t in trials), 1),
        "median_p95_ms": round(statistics.median(t["latency_ms"]["p95"] for t in trials), 3)}, sort_keys=True))


async def defaults(args):
    counts = Counter()
    started = time.perf_counter()

    async def burst_worker():
        reader, writer = await asyncio.open_connection(args.host, 8000)
        try:
            for _ in range(10):
                _, status = await one_request(reader, writer, args.host, "192.0.2.1")
                counts[status] += 1
        finally:
            writer.close()
            await writer.wait_closed()

    await asyncio.gather(*(burst_worker() for _ in range(10)))
    elapsed = time.perf_counter() - started
    assert elapsed < 1, f"Burst crossed window boundary ({elapsed:.3f}s); rerun"
    assert counts == {200: 30, 429: 70}, counts
    await asyncio.sleep(1.1)
    human = await measure(args.host, 5, 1, paced=True)
    assert human["status_counts"] == {200: 50}, human
    print(json.dumps({"burst": {"requests": 100, "seconds": round(elapsed, 3), "status_counts": dict(counts)}, "paced_10_rps": human}, sort_keys=True))


def micro(args):
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    store = get_store(args.mode, args.keys)
    prefix = uuid4().hex
    times = []
    for i in range(10000):
        started = time.perf_counter_ns()
        assert store.check_rate(f"target:{prefix}:{i % 32}", 10000, 60) == 0
        times.append((time.perf_counter_ns() - started) / 1000)
    state_times = []
    for i in range(1000):
        key = f"state:{prefix}:{i}"
        started = time.perf_counter_ns()
        store.put_state(key, {"provider": "google"}, 600)
        assert store.pop_state(key) == {"provider": "google"}
        state_times.append((time.perf_counter_ns() - started) / 1000)
    print(json.dumps({"mode": args.mode, "synthetic_active_keys": args.keys, "operations": len(times),
        "check_rate_us": {"p50": round(percentile(times, .5), 3), "p95": round(percentile(times, .95), 3), "p99": round(percentile(times, .99), 3)},
        "state_put_and_pop_us": {"p50": round(percentile(state_times, .5), 3), "p95": round(percentile(state_times, .95), 3)},
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "starting_peak_rss_kib": before,
        "python": platform.python_version(), "architecture": platform.machine()}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["serve", "micro"]:
        p = sub.add_parser(command)
        p.add_argument("--mode", choices=["none", "memory", "redis"], required=True)
        p.add_argument("--keys", type=int, default=0)
        if command == "serve":
            p.add_argument("--limit", type=int, default=10000)
    p = sub.add_parser("load")
    p.add_argument("--host", required=True)
    p.add_argument("--seconds", type=float, default=5)
    p.add_argument("--concurrency", type=int, default=32)
    p.add_argument("--repeats", type=int, default=3)
    p = sub.add_parser("defaults")
    p.add_argument("--host", required=True)
    args = parser.parse_args()
    if args.command == "serve":
        serve(args)
    elif args.command == "micro":
        micro(args)
    elif args.command == "load":
        asyncio.run(load(args))
    else:
        asyncio.run(defaults(args))

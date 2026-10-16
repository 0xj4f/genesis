# Redis decision and performance verification

**Decision: Redis is unnecessary for the current deployment and has been removed.**
The application, production Compose configuration, and CI no longer require
a Redis package, connection, environment variable, or service. Development and
production use the same bounded, thread-safe in-process store.

## Reasoning before measurement

The original reason for adding Redis was coordination: several workers or
replicas need to agree on a rate budget and single-use SSO state. I introduced
that dependency without first checking the actual deployment or asking whether
an infrastructure change was acceptable. That exceeded the hardening scope.

The existing `mac-mini-m1-infrastructure` repository establishes:

- `public/iam/templates/api.yaml` deploys **one** Genesis replica with **Recreate**
  updates, avoiding simultaneous old/new pods.
- The application starts one Uvicorn worker. The entrypoint now makes that
  existing assumption explicit with `--workers 1`.
- MySQL already persists sessions, token rotation, and authorization codes.
- Cloudflare and Traefik already handle public ingress. The ingress allow-list
  does not currently publish SSO routes.

There is no cross-process coordination requirement in that design. Local
memory provides the required per-IP limits and atomic SSO state consumption
without another service or network operation. Rate-map expiry uses a bounded
queue rather than scanning every tracked IP for each request.

The tradeoff is explicit: process restarts clear rate counters and pending SSO
flows, and multiple workers/replicas would have separate state. Database-backed
sessions and revocations are unaffected. If scaling is later requested, evaluate
the existing ingress for shared rate limiting and existing MySQL for single-use
state before proposing another service. Redis remains an option, not a requirement.

This matches [Uvicorn's worker model](https://www.uvicorn.org/deployment/) and
the distributed-instance use case described in
[Redis's rate-limiting documentation](https://redis.io/docs/latest/develop/use-cases/rate-limiter/).
Redis's purpose here would be coordination; adding it does not itself identify
bots or increase the capacity of password hashing and database operations.

## Performance measurements

Measured on 2026-10-16 in local ARM64 Docker, using Python 3.13.16. The Docker VM
had 8 CPUs and approximately 4 GiB RAM. Each API test server had a one-CPU limit
and 512 MiB memory limit; the load generator ran separately with two CPUs. Redis
was a temporary private container, with no published port. The production Mac
mini and Kubernetes deployment were not accessed or modified.

The HTTP comparison used an identical synchronous health endpoint, 9,000
synthetic active rate keys, one-second warmup, then three five-second saturated
trials with 32 persistent connections. The per-IP ceiling was raised to 10,000
only for capacity measurement so valid requests would not be replaced by 429s.
All measured capacity requests returned 200. Production defaults remain 30/s.

| Variant | Median allowed requests/s | Median p95 latency under saturation | p95 latency at 10 requests/s |
|---|---:|---:|---:|
| No security middleware, reference only | 12,162 | 3.817 ms | 3.148 ms |
| Previous Redis implementation | 4,162 | 18.462 ms | 4.392 ms |
| In-process implementation | 10,431 | 4.500 ms | 3.775 ms |

The in-process implementation delivered approximately **2.5 times** the
throughput of the Redis implementation previously added. At human browsing
rates both had small latency; the measured p95 difference was about 0.6 ms.
The no-middleware comparison also excludes headers and request-body checks,
so its difference is not exclusively rate-limiter cost.

Direct checks, measured over 10,000 operations with 9,000 synthetic active keys,
had p95 costs of **0.708 microseconds** in-process and **102.456 microseconds**
with the previous Redis client. State insertion plus single-use consumption
had p95 costs of 0.917 and 66.206 microseconds respectively.

These results compare the actual code added in the first sweep: a synchronous
Redis client dispatched through a threadpool versus a direct in-process check.
They do not claim that every Redis implementation has this performance.
An asynchronous Redis design could perform differently, but would still add a
service to solve a coordination problem absent from the present deployment.

The synthetic endpoint excludes database operations, JWT verification,
password hashing, uploads, TLS, Cloudflare, Traefik, and Kubernetes networking.
Its request rate is **not** a production login-capacity estimate or a Mac mini
load-test result. The short paced samples are indicative rather than an SLO.

Raw measurements: [JSON results](benchmarks/security-limiter-2026-10-16.json).
Harness: [security_limiter.py](../benchmarks/security_limiter.py). `BENCH_SOURCE`
selects the saved baseline image's `/app` or the current checkout mounted at
`/candidate`. The raw results record the baseline image digest, limits, repeats,
latency distributions, status counts, and direct operation measurements.

## Conclusion after measurement

**Keep the existing deployment design and use the in-process limiter.** Redis
provided no required correctness benefit for one worker and added latency,
an availability dependency, and deployment work. It has been removed rather
than retained as an optional production prerequisite. No infrastructure chart
or network policy was changed, and no deployment was performed.

The fresh application image was checked to contain no Redis package. **All 68
security/MySQL concurrency tests and all 52 existing end-to-end tests passed**
without a Redis connection. At the actual default rate ceiling, an HTTP burst
of 100 requests in 45 ms admitted exactly 30 and returned 429 for 70; all 50
requests paced at 10/s then succeeded. The temporary
Redis container was solely a benchmark reference and is removed after testing.

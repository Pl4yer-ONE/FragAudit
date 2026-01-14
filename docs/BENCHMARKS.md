# FragAudit Performance Benchmarks

## Test Environment

- **Machine**: Apple Silicon Mac
- **Python**: 3.13.2
- **Date**: 2026-01-14
- **Version**: v3.3.0

## Benchmark Results (5 Demos)

| Demo | Map | Parse (s) | Analyze (s) | Total (s) | RAM (MB) | Events | Events/sec | Status |
|------|-----|-----------|-------------|-----------|----------|--------|------------|--------|
| phoenix-vs-rave-m1-nuke | de_nuke | 3.918 | 1.138 | 5.056 | 105.6 | 555 | 110 | FAIL |
| boss-vs-m80-m2-ancient | de_ancient | 4.496 | 1.668 | 6.164 | 130.2 | 843 | 137 | FAIL |
| phantom-vs-hyperspirit-m1-mirage | de_mirage | 3.463 | 1.249 | 4.712 | 96.3 | 583 | 124 | **PASS** |
| phoenix-vs-rave-m3-ancient | de_ancient | 3.864 | 1.250 | 5.114 | 120.2 | 569 | 111 | FAIL |
| ec-banga-vs-semperfi-mirage | de_mirage | 4.974 | 1.772 | 6.745 | 143.9 | 746 | 111 | FAIL |

## Summary Statistics

| Metric | Average | Min | Max |
|--------|---------|-----|-----|
| Parse Time | 4.14s | 3.46s | 4.97s |
| Analysis Time | 1.42s | 1.14s | 1.77s |
| **Total Runtime** | **5.56s** | 4.71s | 6.75s |
| Peak Memory | 119.2 MB | 96.3 MB | 143.9 MB |
| Events/sec | 118.6 | 110 | 137 |

## Performance Thresholds

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Runtime | < 5s | 5.56s avg | ⚠️ MARGINAL |
| Peak RAM | < 500 MB | 119 MB | ✅ PASS |
| Events/sec | > 100 | 118 | ✅ PASS |

## Bottleneck Analysis

```
Parse Time:    ████████████████████░░░░░ 74% of runtime
Analysis Time: ██████░░░░░░░░░░░░░░░░░░░ 26% of runtime
```

**Primary Bottleneck**: Demo parsing (demoparser2)

The parsing phase accounts for ~74% of total runtime. The analysis engine itself is fast (1.4s avg). Optimization opportunities:
1. Parser caching
2. Lazy parsing (only extract needed fields)
3. Consider awpy fallback for smaller demos

## Verdict

- **Memory**: ✅ Well under 500MB limit
- **Throughput**: ✅ 118 events/sec is production-ready
- **Runtime**: ⚠️ Marginally over 5s target (5.56s avg)

**Recommendation**: Acceptable for v3.3 release. Parser optimization can be addressed in v3.5.

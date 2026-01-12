# Roadmap

Locked scope. No feature creep.

---

## v3.1 — Combat Intelligence

**ETA:** When ready, not rushed

### Features
- [ ] **Trade Detection** — Who traded whom, within what window
- [ ] **Flash Awareness** — Was player flashed before death
- [ ] **Trade Window Metrics** — 0-3 second trade analysis

### What this enables
- Tradeable death classification
- Flash impact scoring
- Team coordination metrics

---

## v3.2 — Positioning Analysis

**ETA:** After v3.1 is stable

### Features
- [ ] **Multi-angle Exposure** — How many enemy FOV cones visible
- [ ] **Spacing Errors** — Too close/far from teammates
- [ ] **Multi-demo Compare** — Same player across matches

### What this enables
- Positioning mistake detection
- Team spacing analysis
- Performance trends over time

---

## What We Do NOT Do

| Forbidden | Reason |
|-----------|--------|
| ❌ Engine rewrites | It works |
| ❌ Random features | Scope creep |
| ❌ UI changes | Demo player is done |
| ❌ Micro-optimizations | Not bottlenecked |
| ❌ Renaming | Churn |

---

## Maintenance Mode Rules

1. **Say no** to feature requests that don't fit roadmap
2. **Protect quality** — No regressions
3. **Only patch real exploits** — Not theoretical ones
4. **Tests before merge** — CI must pass

---

## Version History

| Version | Focus | Status |
|---------|-------|--------|
| v1.x | Core parsing | ✅ Done |
| v2.x | Rating engine | ✅ Done |
| v3.0 | Demo player | ✅ Shipped |
| v3.1 | Trade detection | 🔲 Planned |
| v3.2 | Positioning | 🔲 Planned |

---

*This roadmap is locked. Changes require justification.*

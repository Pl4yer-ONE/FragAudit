# Contributing to FragAudit

Thanks for your interest in contributing. Read this before submitting anything.

---

## License Agreement

By contributing, you agree that:

1. Your contributions are licensed under **PolyForm Noncommercial 1.0.0**
2. You have the right to submit the contribution
3. Commercial use of your contribution is prohibited without permission

---

## What We Accept

✅ Bug fixes with tests  
✅ Performance improvements  
✅ Documentation fixes  
✅ New analysis metrics (with rationale)  
✅ Demo player improvements (functional, not cosmetic)

---

## What We Reject

❌ **Commercial forks or monetization attempts**  
❌ Paywalls or premium features  
❌ Telemetry or tracking  
❌ License bypass or removal  
❌ AI/ML buzzword features without substance  
❌ Web UI rewrites  
❌ Cosmetic-only changes  

---

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `main` (name: `feature/xyz` or `fix/xyz`)
3. **Write tests** for new functionality
4. **Run tests locally**: `python -m pytest tests/ -v`
5. **Ensure CI passes** before requesting review
6. **One PR = One feature/fix** (no mega-PRs)

---

## Code Style

- Python 3.11+
- Type hints where practical
- Docstrings for public functions
- No wildcard imports
- Keep functions under 50 lines when possible

---

## Commit Messages

Format:
```
type: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`

Example:
```
feat: add kill timeline markers to demo player

Renders vertical markers on the timeline for each kill event.
Clicking a marker jumps to that tick.
```

---

## Tests Required

All new features must include tests. No exceptions.

```bash
python -m pytest tests/ -v --tb=short
```

Coverage should not decrease.

---

## Questions?

Open an issue with `[Question]` in the title.

# Contributing to FragAudit

Thank you for your interest in contributing to FragAudit! We welcome contributions from the community to make this the best CS2 coaching tool available.

## ⚖️ Legal & Licensing (Read Carefully)

**FragAudit is a Dual-Licensed project.**

By submitting a Pull Request (PR) to this repository, you agree to the following **Contributor License Agreement (CLA)** terms:

1.  **Grant of License**: You grant the project maintainers a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable license to reproduce, prepare derivative works of, publicly display, publicly perform, sublicense, and distribute your contribution (in whole or in part) as part of:
    -   The **Community Edition** (licensed under GNU GPLv3).
    -   The **Commercial Edition** (licensed under proprietary terms).

2.  **Copyright Retention**: You retain ownership of the copyright to your contribution. You are simply giving us permission to use it in both versions of the software.

3.  **Originality**: You certify that the code you are submitting is your original work or that you have the right to license it to us under these terms.

*If you do not agree to these terms, please do not submit a PR.*

---

## 🛠️ How to Contribute

1.  **Fork the Repository**: Click the "Fork" button on GitHub.
2.  **Create a Branch**: `git checkout -b feature/amazing-feature`
3.  **Make Changes**: Write clean, documented code.
4.  **Test**: Ensure all unit tests pass.
    ```bash
    python -m pytest tests/ -v
    ```
5.  **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/).
    ```bash
    git commit -m "feat: add new round timeline visualization"
    ```
6.  **Push & PR**: Push to your fork and open a Pull Request against `main`.

---

## ✅ What We Accept

-   **Bug Fixes**: Fixes for demonstrable issues (please include a test case).
-   **New Features**: Improvements that align with the roadmap (e.g., new detection rules).
-   **Documentation**: Clarity updates, typo fixes, or new examples.
-   **Performance**: Optimizations for demo parsing or rendering.

## ❌ What We Don't Accept

-   **Breaking Changes**: Unless previously discussed in an Issue.
-   **No Tests**: Features submitted without accompanying unit tests.
-   **Spaghetti Code**: Unstructured or undocumented code.
-   **Dependencies**: Adding heavy libraries without justification.

---

## 💻 Code Style

-   **Python**: Follow PEP 8.
-   **Type Hints**: Strongly encouraged for all public functions.
-   **Docstrings**: Required for modules, classes, and complex functions.
-   **Imports**: Sorted and unused imports removed.

---

## 🐞 Found a Bug?

Please open an issue on GitHub with:
1.  The `.dem` file (if public) or a description of the scenario.
2.  The command you ran.
3.  The expected vs. actual output.

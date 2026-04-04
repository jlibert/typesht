# Contributing to TypeSht

Thank you for your interest in contributing! This guide explains how to get set up and how we work.

---

## Getting Started

**1. Fork the repository and clone your fork:**
```bash
git clone https://github.com/YOUR_USERNAME/typesht.git
cd typesht
```

**2. Install dependencies:**
```bash
pip install -e ".[dev]"
```

**3. Run the test suite to make sure everything works:**
```bash
python -m pytest tests/ -v --cov=compiler --cov-report=term-missing --cov-fail-under=89
```

---

## Branch Strategy

We follow a `main` / `develop` / `feature` workflow:

| Branch | Purpose |
|--------|---------|
| `main` | Production code — releases are cut from here |
| `develop` | Integration branch — all feature branches merge here |
| `feature/*` | Individual work — branched off `develop` |

**Always branch off `develop`, never `main`:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Branch Naming Conventions

Use a prefix that matches the type of change:

| Prefix | IEEE Type | Use for |
|--------|-----------|---------|
| `feature/` | Perfective | New language features, stdlib additions |
| `fix/` | Corrective | Bug fixes, wrong compilation output |
| `docs/` | Preventive | README, docstrings, comments |
| `chore/` | Adaptive | CI changes, dependency updates, tooling |

**Examples:**
```
feature/try-except-support
feature/fstring-format-specs
fix/floor-division-negative-numbers
fix/negative-index-slice
docs/update-standard-library-table
chore/bump-typescript-version
```

---

## Making Changes

- Keep changes focused — one feature or fix per branch
- Add tests for any new language features or bug fixes
- Make sure coverage stays at or above 89%
- Update the README if you're adding a new language feature

---

## Submitting a Pull Request

1. Push your branch to your fork:
```bash
git push origin feature/your-feature-name
```

2. Open a PR from your branch into `develop` (not `main`)
3. Fill out the PR template completely
4. All CI checks must pass before merging

---

## Commit Message Style

Use short, descriptive commit messages with the same prefix as your branch:

```
feature: add try/except support
fix: correct floor division for negative numbers
docs: add lambda examples to README
chore: bump pytest to 8.x
```

---

## Reporting Issues

Use the issue templates on GitHub:
- **Bug Report** — for incorrect compilation output or compiler errors
- **Feature Request** — for new language features or stdlib additions

For questions, use [GitHub Discussions](https://github.com/jlibert/typesht/discussions).

---

## Code Style

- Follow existing code style in `compiler/`
- No external dependencies in the compiler — it must stay pure Python
- Type hints are encouraged but not required for internal code

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
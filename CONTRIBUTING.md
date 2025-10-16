# 🧩 Contributing to BundleCraft

Thanks for contributing to **BundleCraft** — a unified CLI for building, verifying, and converting CA trust bundles.

This guide defines a reproducible local setup, coding standards, testing, and (optional) packaging steps so contributors and CI get the same results.

---

## ⚙️ Development Setup

### 1) Clone and enter the repository

```bash
git clone https://github.com/your-org/bundlecraft.git
cd bundlecraft
```

### 2) Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3) Install dependencies and the CLI (editable)

```bash
pip install -r requirements.txt
pip install -e .
```

This installs runtime + dev tools and exposes the `bundlecraft` command.

> **Note:** Keep your trust-bundle output directory named something other than `build/` (e.g., `dist/` or `artifacts/`) to avoid conflicts with the Python packaging tool named `build`.

---

## 🧱 Repository Layout

```
bundlecraft/
├── bundlecraft/
│   ├── __init__.py        # version metadata
│   ├── cli.py             # main CLI entrypoint
│   ├── builder.py         # bundle build logic
│   ├── verifier.py        # verification logic
│   ├── converter.py       # format conversion logic
│   └── helpers/           # internal utilities (utils, convert_utils, verify_utils)
├── config/                # environment and bundle definitions
├── sources/               # source certificate files
├── dist/                  # build outputs (avoid naming this 'build/')
├── pyproject.toml         # packaging metadata
├── requirements.txt       # dependency pinning for dev + CI
└── CONTRIBUTING.md        # this file
```

---

## 🧪 Running the CLI

### Installed CLI usage (recommended)

```bash
bundlecraft build   --env dev --bundle internal
bundlecraft verify  --target dist/dev/internal --verify-all
bundlecraft convert --pem-file dist/dev/internal/ca-trust.pem --output-dir dist/dev/internal/
```

### Module form (no install)

```bash
python -m bundlecraft.cli build --env dev --bundle internal
```

Each subcommand supports `--help` for detailed options.

---

## 🚀 GitHub Workflow Integration

This repository includes a **sample, fully functional GitHub Actions workflow** located under `.github/workflows/`.
It automatically:

1. Installs dependencies and BundleCraft in editable mode.
2. Runs `bundlecraft build` for all configured environments and bundles.
3. Verifies outputs using `bundlecraft verify`.
4. Uploads artifacts (PEM, JKS, P12, P7B, and manifests) as a release package.

This pipeline demonstrates how BundleCraft can be executed end-to-end as part of a CI/CD process. It can also serve as a reference for private enterprise pipelines or GitHub Releases.

---

## 🧰 (Optional) Packaging & Release

BundleCraft is primarily a **repo-scoped CLI** for pipelines. Packaging is optional, but the steps below are standardized if you decide to cut a release.

### 1) Ensure packaging tools

```bash
pip install build twine
```

### 2) Build distributions

```bash
python -m build
```

Distributions appear in the top-level `dist/` directory.

### 3) Validate artifacts

```bash
twine check dist/*
```

### 4) Tag and (optionally) publish

```bash
git tag -a v0.1.0 -m "Initial BundleCraft release"
git push origin v0.1.0
# Optional (PyPI):
twine upload dist/*
```

---

## 🧾 Coding Standards

* Follow [PEP 8](https://peps.python.org/pep-0008/).
* Use **black** for formatting and **flake8** for linting.
* Prefer explicit, consistent Click options across subcommands.
* Keep logging readable and deterministic; consider `--quiet`/`--json` flags in future versions.

### Formatting & Linting

```bash
black .
flake8
```

---

## 🧩 Testing

### Run tests locally

```bash
pytest -v
```

### Test guidance

* Place tests under `bundlecraft/tests/`.
* Use `click.testing.CliRunner` for CLI tests.
* Include tiny, non-sensitive PEM fixtures for functional tests.

---

## 🔐 Security Notes

* Never commit private keys or internal CA material.
* Treat any sample certs as test fixtures only.
* Future roadmap may include optional signing of manifests/bundles (GPG/OpenPGP).

---

## ✅ Quick Command Reference

| Action          | Command                                                                                        |
| --------------- | ---------------------------------------------------------------------------------------------- |
| Build bundle    | `bundlecraft build --env dev --bundle internal`                                                |
| Verify bundle   | `bundlecraft verify --target dist/dev/internal --verify-all`                                   |
| Convert formats | `bundlecraft convert --pem-file dist/dev/internal/ca-trust.pem --output-dir dist/dev/internal` |
| Run tests       | `pytest -v`                                                                                    |
| Make dists      | `python -m build`                                                                              |
| Validate dists  | `twine check dist/*`                                                                           |

---

## 🤝 Pull Requests

1. Branch from `main` and keep PRs focused.
2. Include tests for new behavior.
3. Ensure `black`, `flake8`, and `pytest` pass locally.
4. Provide a clear PR description with context and rationale.

---

**Thank you for helping make BundleCraft better ☺️**

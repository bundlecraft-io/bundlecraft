# Changelog

All notable changes to BundleCraft will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2025-10-26
<!-- markdownlint-disable MD024 -->

### Added

- Official release pipeline with GitHub Actions (`.github/workflows/release.yaml`) that:
  - Builds and publishes the Python package to PyPI (via Trusted Publishing)
  - Builds and publishes the container image to GHCR
  - Creates a GitHub Release with packaged artifacts and generated changelog
- Dockerfile for building and publishing the container image
- Makefile targets for local build/test/release workflows
- `scripts/prepare_test_configs.sh` to generate throwaway example configs/certs for CI and local smoke tests (with `--cleanup`)
- `.githooks/pre-push` hook to block pushing tags without matching CHANGELOG.md entries
- `CHANGELOG.md` now tracks version updates using Keep a Changelog
- New BundleCraft CLI: `bundlecraft build-all`
  - This is a shortcut to invoking the build process against all config files instead of a specific one
  - This makes the tool independent for CI builds, no longer relying on `scripts/detect_env_targets.py` to provide config targets
  - Users can also scope build-all to read from a specific subdir (i.e. `configs/envs/my_sub_envs/`) for more fine grained control

### Changed

- Documentation overhaul: `CONTRIBUTING.md` now documents the two-stage release flow (pre-release → Test PyPI → main → PyPI), adds Quickstart, repo structure, and security model
- CI/CD consolidated to the new `release.yaml`; the legacy `bundlecraft.yaml` will be templatized and moved to an example/demo repo

### Fixed

- Minor polish and miscellaneous fixes across scripts and docs

---

## Pre-Releases

## [0.1.3-beta.13] - 2025-10-26

### Added

- Initial pre-release version

### Changed

- Release workflow improvements

### Fixed

- Container immutable release handling

---

## [0.1.3-beta.14] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow

---

## [0.1.3-beta.15] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow

---

## [0.1.3-beta.16] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow

---

## [0.1.3-beta.17] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow (hoping this message shows up!)

---

## [0.1.3-beta.18] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow (hoping this message shows up!)

---

## [0.1.3-beta.19] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow (hoping this message shows up, cmon pypi)

---

## [0.1.3-beta.20] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow (hoping this message shows up, cmon pypi, pass verification)

---

## [0.1.3-beta.21] - 2025-10-26

### Changed

- No changes, refining CI/CD workflow (hoping this message shows up, cmon pypi, pass verification)

---

## [0.1.3-beta.22] - 2025-10-26

### Changed

- `bundlecraft build-all` !

---

## [0.1.3-beta.22] - 2025-10-26

### Changed

- New option: `bundlecraft build-all --recursive`
- Small fixes

---

## Stable Releases

---
<!-- markdownlint-enable MD024 -->

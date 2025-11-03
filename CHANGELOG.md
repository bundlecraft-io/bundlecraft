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
  - For backwards compatibility, `bundlecraft build-all --print-plan` will output the build targets that can be used to inform CI/CD
  - Users can also scope build-all to read from a specific subdir (i.e. `configs/envs/my_sub_envs/`) for more fine grained control
- BundleCraft build manifest now includes `build_path`

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

## [0.1.3-beta.23] - 2025-10-26

### Changed

- New option: `bundlecraft build-all --recursive`
- Small fixes

---

## [0.1.3-beta.24] - 2025-10-27

### Changed

- N/A, more release tests

---

## [0.1.3-beta.25] - 2025-10-28

### Changed

- `bundlecraft build-all --print-plan` now prints `build_path`

---

## [0.1.3-beta.26] - 2025-10-28

### Changed

- feat: add build_path field to manifest

---

## [0.1.3-beta.27] - 2025-10-28

### Changed

- feat: enforce build_path to be a subdirectory within dist/env for security

---

## [0.1.3-beta.28] - 2025-10-30

### Changed

- OpenJDK has been replaced by PyJKS
  - Makes BundleCraft less reliant on a system dependency and reduces image file size
  - All keytool operations are now python native
  - All behavior with respect to JKS bundle creation remains the same as before

---

## [0.1.3-beta.29] - 2025-10-30

### Changed

- N/A, more release tests

---

## [0.1.3-beta.30] - 2025-10-30

### Changed

- N/A, more release tests

---

## [0.1.3-beta.31] - 2025-10-30

### Changed

- Openssl dependencies removed
  - BundleCraft is now 100% python native - no more system dependencies!
  - Operations that relied on openssl (like p7b conversions) now use python deps

---

## Stable Releases

---
<!-- markdownlint-enable MD024 -->

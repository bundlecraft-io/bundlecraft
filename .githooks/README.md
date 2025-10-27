# Git Hooks for BundleCraft

This directory contains custom Git hooks to enforce repository policies.

## Installation

To enable these hooks for your local repository:

```bash
git config core.hooksPath .githooks
```

## Available Hooks

### pre-push

Validates that every version tag being pushed has a corresponding entry in `CHANGELOG.md`.

**What it checks:**

- When pushing a tag like `v0.1.3-beta.20`, it verifies that `CHANGELOG.md` contains a section starting with `## [0.1.3-beta.20]`
- Blocks the push if the changelog entry is missing
- Provides helpful error messages with example format

**Example workflow:**

```bash
# 1. Update CHANGELOG.md
echo "## [0.1.4-beta.1] - $(date +%Y-%m-%d)" >> CHANGELOG.md
echo "" >> CHANGELOG.md
echo "### Changed" >> CHANGELOG.md
echo "- New awesome feature" >> CHANGELOG.md
echo "" >> CHANGELOG.md
echo "---" >> CHANGELOG.md

# 2. Commit the changelog
git add CHANGELOG.md
git commit -m "Update changelog for v0.1.4-beta.1"

# 3. Create and push tag
git tag v0.1.4-beta.1
git push origin v0.1.4-beta.1  # ✅ Hook passes
```

**Bypass (emergency only):**

```bash
# Skip hooks if absolutely necessary
git push --no-verify origin v0.1.4-beta.1
```

## CI/CD Integration

These hooks are for local development. The GitHub Actions release workflow doesn't rely on them, so:

- ✅ Developers get immediate feedback before pushing
- ✅ CI/CD remains independent and doesn't fail due to hook issues
- ✅ Changelog validation happens at development time, not release time

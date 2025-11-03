# Dependency Lock File Management

## Overview

BundleCraft uses a `requirements-lock.txt` file to ensure deterministic and reproducible production builds. This document provides detailed information about the lock file, its purpose, and how to manage it.

## Purpose

The lock file serves several critical purposes:

1. **Deterministic Builds** - Ensures identical dependency versions across all production deployments
2. **Security** - Protects against supply chain attacks by preventing unexpected dependency changes
3. **Reproducibility** - Allows exact reproduction of any production build
4. **Auditability** - Provides a clear record of all dependencies used in production
5. **Stability** - Prevents breaking changes from dependency updates during releases

## File Location

```
bundlecraft/
├── pyproject.toml          # Defines minimum version constraints
└── requirements-lock.txt   # Locks exact versions for production
```

## Lock File Format

The lock file is a standard `pip freeze` output with additional documentation:

```
# Header comments explaining the file's purpose
# and how to regenerate it

# Dependency with comment explaining its purpose
package-name==exact.version.number

# Example:
click==8.1.7  # CLI framework (direct dependency)
```

### Direct vs. Transitive Dependencies

The lock file includes both:

- **Direct dependencies** - Listed in `pyproject.toml` under `[project.dependencies]`
- **Transitive dependencies** - Required by direct dependencies

All dependencies are commented to indicate:
- Their purpose
- Whether they are direct or transitive
- What package requires them (for transitive deps)

## When to Update the Lock File

Update `requirements-lock.txt` in these situations:

### 1. Before Major Releases

Before tagging a production release (e.g., `v1.0.0`), update the lock file to capture the latest stable versions.

### 2. After Security Updates

When a dependency has a critical security fix:

```bash
# Check for vulnerabilities
pip-audit

# Update the specific package
pip install --upgrade package-name==new.version

# Regenerate lock file
pip freeze > requirements-lock.txt
```

### 3. When Adding New Dependencies

After modifying `pyproject.toml` to add new dependencies:

```bash
# Install the new dependencies
pip install -e .

# Update lock file
pip freeze > requirements-lock.txt
```

### 4. Periodic Updates

Update dependencies every 2-3 months to stay current with:
- Bug fixes
- Performance improvements
- Security patches

## How to Update the Lock File

### Standard Process

Follow these steps to safely update the lock file:

```bash
# 1. Create a clean virtual environment with Python 3.11
python3.11 -m venv .venv-lock

# 2. Activate the environment
source .venv-lock/bin/activate  # Linux/macOS
# or
.venv-lock\Scripts\activate      # Windows

# 3. Upgrade pip to latest version
pip install --upgrade pip

# 4. Install bundlecraft with all dependencies
pip install -e .

# 5. Generate the lock file
pip freeze > requirements-lock.txt

# 6. Add helpful comments (see next section)
# Edit requirements-lock.txt to add package descriptions

# 7. Review changes
git diff requirements-lock.txt

# 8. Test the lock file
pip install -r requirements-lock.txt

# 9. Run tests to ensure compatibility
pytest -v

# 10. Commit the changes
git add requirements-lock.txt
git commit -m "chore: update requirements lock file"

# 11. Clean up
deactivate
rm -rf .venv-lock
```

### Adding Comments to Lock File

After generating the raw `pip freeze` output, add comments for clarity:

```python
# Example format:
# package-name==version  # Purpose (direct/transitive from X)

click==8.1.7                # CLI framework (direct dependency)
certifi==2024.8.30          # Root certificates for TLS (transitive from requests)
```

This makes it easier to:
- Understand why each package is included
- Identify what to update when a vulnerability is found
- Review changes during pull requests

## CI/CD Integration

### Release Workflow

The release workflow (`release.yaml`) uses the lock file:

```yaml
- name: Install dependencies from lock file
  run: |
    pip install -r requirements-lock.txt
```

This ensures production builds use exact dependency versions.

### Lock File Validation

The test workflow (`test-pytest.yaml`) validates the lock file:

```yaml
jobs:
  validate-lockfile:
    name: 🔒 Validate Requirements Lock File
    steps:
      - name: 🔍 Check lock file exists
      - name: 🔧 Install from lock file
      - name: ✅ Verify installation
```

This catches issues like:
- Missing lock file
- Invalid package versions
- Installation conflicts

## Troubleshooting

### Lock File Installation Fails

If `pip install -r requirements-lock.txt` fails:

1. **Check Python version** - Lock file is for Python 3.11
   ```bash
   python --version  # Should be 3.11.x
   ```

2. **Clear pip cache**
   ```bash
   pip cache purge
   pip install -r requirements-lock.txt
   ```

3. **Regenerate lock file** - Follow update process above

### Dependency Conflicts

If dependencies conflict with new requirements:

1. **Update pyproject.toml constraints** - Adjust version ranges
2. **Regenerate lock file** - Use clean environment
3. **Test thoroughly** - Run full test suite

### Package Not Found

If a package in the lock file is unavailable:

1. **Check PyPI status** - Package may be yanked
2. **Find alternative version** - Check package history
3. **Update lock file** - Use available version

## Best Practices

### Version Selection

When updating dependencies:

1. **Review changelogs** - Check for breaking changes
2. **Test incrementally** - Update one package at a time if issues occur
3. **Use stable versions** - Avoid pre-release versions (alpha/beta)
4. **Stay within constraints** - Respect version ranges in `pyproject.toml`

### Security

1. **Scan for vulnerabilities**
   ```bash
   pip-audit -r requirements-lock.txt
   ```

2. **Review security advisories** - Check GitHub Security Advisories
3. **Update promptly** - Address critical vulnerabilities quickly
4. **Document changes** - Note security updates in commit messages

### Testing

After updating the lock file:

1. **Run unit tests**
   ```bash
   pytest -v
   ```

2. **Run integration tests**
   ```bash
   make test-pypi-build
   ```

3. **Test in production-like environment** - Use Docker/containers

4. **Verify all features** - Manual smoke testing

## Relationship to pyproject.toml

The lock file and `pyproject.toml` serve different purposes:

| File | Purpose | Version Specification |
|------|---------|----------------------|
| `pyproject.toml` | Define minimum requirements | Ranges (e.g., `>=8.0,<9.0`) |
| `requirements-lock.txt` | Lock exact versions | Exact (e.g., `==8.1.7`) |

**Development workflow:**

1. Update `pyproject.toml` with new/changed dependencies
2. Install with `pip install -e .` (uses pyproject.toml ranges)
3. Generate lock file with `pip freeze` (captures exact versions)
4. Commit both files

## Related Documentation

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contributing guide with lock file section
- [SECURITY.md](../SECURITY.md) - Security policy mentioning lock files
- [CI-CD.md](CI-CD.md) - CI/CD pipeline documentation

## References

- [pip freeze documentation](https://pip.pypa.io/en/stable/cli/pip_freeze/)
- [pip-tools](https://github.com/jazzband/pip-tools) - Alternative lock file management (for future consideration)
- [Poetry](https://python-poetry.org/) - Alternative dependency management (for future consideration)
- SECURITY.md Supply Chain Attacks section

## Questions or Issues?

If you encounter issues with the lock file:

1. Check [troubleshooting.md](troubleshooting.md)
2. Open an issue on [GitHub Issues](https://github.com/bundlecraft-io/bundlecraft/issues)
3. Contact maintainers at hello@bundlecraft.io

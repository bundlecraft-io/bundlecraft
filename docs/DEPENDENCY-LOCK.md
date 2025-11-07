# Dependency Lock File Management

## Overview

BundleCraft uses a requirements lock file (`requirements-lock.txt`) to ensure deterministic and reproducible production builds. This addresses supply chain security concerns by pinning exact dependency versions for releases.

## Lock File Location

- **Lock file**: `requirements-lock.txt` (root directory)
- **Source**: `pyproject.toml` (defines dependency constraints)

## Lock File Management with pip-tools

We use [pip-tools](https://github.com/jazzband/pip-tools) to generate and maintain the lock file.

### Installation

```bash
pip install pip-tools
```

### Generating the Lock File

To generate or update the lock file:

**Using Make (recommended):**
```bash
make lock-requirements
```

**Using the generation script:**
```bash
./scripts/generate_lock_file.sh
```

**Manually:**
```bash
pip install pip-tools
pip-compile pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking
```

This command:
- Reads dependencies from `pyproject.toml`
- Resolves all transitive dependencies
- Pins exact versions
- Outputs to `requirements-lock.txt`

### When to Update the Lock File

The lock file should be updated:

1. **Before releases** - Always update before creating a release tag
2. **After adding dependencies** - When modifying `pyproject.toml` dependencies
3. **Security updates** - When updating a dependency for security reasons
4. **Quarterly maintenance** - Regular updates to stay current (recommended)

### Updating Specific Dependencies

To update a specific package:

```bash
pip-compile pyproject.toml --output-file=requirements-lock.txt --upgrade-package <package-name>
```

To update all dependencies:

```bash
pip-compile pyproject.toml --output-file=requirements-lock.txt --upgrade
```

## Development vs Production

- **Development**: Install with editable mode from `pyproject.toml`
  ```bash
  pip install -e ".[dev]"
  ```

- **Production/CI**: Install from lock file for reproducibility
  ```bash
  pip install -r requirements-lock.txt
  ```

## CI/CD Integration

### Release Builds

The release workflow (`.github/workflows/release.yaml`) uses the lock file to ensure:
- Exact dependency versions for production releases
- Reproducible builds across environments
- Protection against supply chain attacks

### Lock File Validation

CI workflows validate the lock file:
- Ensures lock file is up-to-date with `pyproject.toml`
- Runs `pip-compile --dry-run` to check for drift
- Alerts if manual updates are needed

## Makefile Targets

Convenient make targets are provided:

```bash
# Generate the lock file
make lock-requirements

# Validate the lock file is up-to-date
make validate-lock

# Update the lock file
make update-lock
```

## Troubleshooting

### Lock file out of sync

If CI reports the lock file is out of date:

1. Update your dependencies:
   ```bash
   pip install --upgrade pip-tools
   ```

2. Regenerate the lock file:
   ```bash
   make lock-requirements
   ```

3. Commit the updated lock file:
   ```bash
   git add requirements-lock.txt
   git commit -m "chore: update requirements lock file"
   ```

### Dependency conflicts

If you encounter dependency conflicts:

1. Check `pyproject.toml` constraints - they may be too restrictive
2. Use pip-compile's verbose mode to diagnose:
   ```bash
   pip-compile -v pyproject.toml --output-file=requirements-lock.txt
   ```
3. Consider adjusting version constraints in `pyproject.toml`

### Build failures after lock file update

If builds fail after updating the lock file:

1. Verify all dependencies install correctly:
   ```bash
   pip install -r requirements-lock.txt
   ```

2. Run tests with the new dependencies:
   ```bash
   pip install -r requirements-lock.txt
   pip install -e ".[dev]"
   pytest
   ```

3. If issues persist, pin the problematic package version in `pyproject.toml`

## Security Considerations

The lock file provides security benefits:

1. **Supply chain protection**: Prevents automatic updates that could introduce malicious code
2. **Reproducibility**: Ensures the same build every time
3. **Audit trail**: Git history tracks all dependency changes
4. **Dependency scanning**: Tools can scan the lock file for known vulnerabilities

Regular updates are still important:
- Review security advisories (GitHub Dependabot, PyPI advisories)
- Update dependencies proactively
- Test thoroughly after updates

## References

- [pip-tools documentation](https://github.com/jazzband/pip-tools)
- [SECURITY.md](../SECURITY.md) - Supply Chain Attacks section
- [PEP 665](https://peps.python.org/pep-0665/) - Specifying Installation Requirements

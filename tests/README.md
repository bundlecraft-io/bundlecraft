# Testing BundleCraft

This document provides comprehensive guidance for running, understanding, and maintaining the BundleCraft test suite. **No prior pytest experience required!**

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Test Structure](#-test-structure)
- [Running Tests](#-running-tests)
- [Understanding Test Output](#-understanding-test-output)
- [Common Issues & Solutions](#-common-issues--solutions)
- [Writing New Tests](#-writing-new-tests)
- [Test Fixtures Explained](#-test-fixtures-explained)
- [Debugging Failed Tests](#-debugging-failed-tests)
- [When to Run Tests](#-when-to-run-tests)
- [CI/CD Integration](#-cicd-integration)
- [Maintenance Tips](#-maintenance-tips)

---

## 🚀 Quick Start

```bash
# 1. Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# 2. Install test dependencies (if not already installed)
pip install -e ".[dev]"

# 3. Run all tests
pytest

# 4. Run with verbose output (recommended for troubleshooting)
pytest -v

# 5. Run a specific test file
pytest tests/test_cli.py -v
```

**Exit Codes:**
- `0` = All tests passed ✅
- `1` = Some tests failed ❌
- `2` = Test execution was interrupted (syntax errors, import errors) 🚫

---

## 🧪 Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures (test helpers)
├── pytest.ini               # Pytest configuration (in project root)
├── data/                    # Test data files
│   ├── certs/              # Sample certificates for testing
│   │   └── sample.pem      # Valid test certificate
│   └── configs/            # Test configuration YAML files
│       ├── bundles/        # Bundle configuration examples
│       └── envs/         # Craft configuration examples
├── test_builder.py         # Tests for bundle building (bundlecraft build)
├── test_cli.py             # Tests for main CLI interface
├── test_commands.py        # Tests for all CLI commands
├── test_converter.py       # Tests for format conversion (bundlecraft convert)
├── test_verifier.py        # Tests for certificate verification (bundlecraft verify)
└── test_helpers.py         # Tests for utility functions
```

### What Each Test File Does

| File | Purpose | Tests |
|------|---------|-------|
| `test_cli.py` | Main CLI entry point | `bundlecraft --help`, `--version` |
| `test_builder.py` | Bundle creation logic | Build workflows, certificate processing |
| `test_converter.py` | Format conversion | PEM→JKS, PEM→P7B, PEM→P12, etc. |
| `test_verifier.py` | Certificate validation | Integrity checks, expiry validation |
| `test_commands.py` | All subcommands | Integration of all CLI commands |
| `test_helpers.py` | Utility functions | File operations, YAML loading, checksums |

---

## 🏃 Running Tests

### Basic Commands

```bash
# Run all tests (compact output)
pytest

# Run all tests (verbose - shows each test name)
pytest -v

# Run all tests (very verbose - shows detailed output)
pytest -vv

# Run with less verbose tracebacks (cleaner output)
pytest -v --tb=short

# Run with minimal traceback (one line per failure)
pytest -v --tb=line
```

### Running Specific Tests

```bash
# Run a single test file
pytest tests/test_cli.py -v

# Run a specific test class
pytest tests/test_builder.py::TestBuilder -v

# Run a single test function
pytest tests/test_cli.py::TestCLI::test_cli_help -v

# Run tests matching a pattern
pytest -k "converter" -v          # Runs all tests with "converter" in name
pytest -k "not slow" -v           # Skip slow tests
```

### Running Tests by Category

Tests are organized with markers (tags):

```bash
# Run only builder tests
pytest -m builder -v

# Run only converter tests
pytest -m converter -v

# Run only verifier tests
pytest -m verifier -v

# List all available markers
pytest --markers
```

### Coverage Reports

```bash
# Run tests with coverage report
pytest --cov=bundlecraft

# Generate HTML coverage report
pytest --cov=bundlecraft --cov-report=html

# View the HTML report (creates htmlcov/ directory)
# Open htmlcov/index.html in your browser
```

---

## 📊 Understanding Test Output

### Successful Test Run

```
tests/test_cli.py::TestCLI::test_cli_help PASSED           [ 20%]
tests/test_cli.py::TestCLI::test_cli_version PASSED        [ 40%]
============================= 32 passed in 5.23s =============================
```

**What this means:**
- `PASSED` = Test succeeded ✅
- `[ 20%]` = Progress indicator (20% of tests completed)
- `32 passed in 5.23s` = Summary: 32 tests passed, took 5.23 seconds

### Failed Test Example

```
tests/test_converter.py::TestConverter::test_convert_to_jks FAILED [ 60%]

FAILED tests/test_converter.py::TestConverter::test_convert_to_jks
E   AssertionError: assert False
E    +  where False = exists()
```

**What this means:**
- `FAILED` = Test failed ❌
- `AssertionError` = The test made an assertion that wasn't true
- `assert False` = The specific assertion that failed
- `where False = exists()` = Shows what value caused the failure

### Skipped Test Example

```
tests/test_builder.py::TestBuilder::test_build_basic_bundle SKIPPED [ 10%]
SKIPPED (TODO: Refactor to use CLI runner instead of build_trust_store function)
```

**What this means:**
- `SKIPPED` = Test was intentionally skipped ⏭️
- The message explains why (usually marked TODO for future work)
- Skipped tests don't count as failures

### Error During Collection

```
ERROR collecting tests/test_builder.py
ImportError: cannot import name 'build_trust_store' from 'bundlecraft.builder'
```

**What this means:**
- `ERROR collecting` = pytest couldn't even load the test file 🚫
- This is worse than a failed test - the code has syntax or import errors
- **Fix these first** before worrying about test failures

---

## 🔧 Common Issues & Solutions

### Issue 1: Import Errors

**Error:**
```
ImportError: cannot import name 'some_function' from 'bundlecraft.module'
```

**Causes:**
- Function was renamed or deleted in the source code
- Typo in the import statement
- Module doesn't exist

**Fix:**
1. Check if the function exists: `grep -r "def some_function" bundlecraft/`
2. Update the import in the test file to use the correct name
3. If the function is gone, mark the test as skipped:
   ```python
   pytest.skip("TODO: Function removed, needs refactor")
   ```

### Issue 2: Fixture Errors

**Error:**
```
FileExistsError: [Errno 17] File exists: '/tmp/tmp32ftxx__/sources'
```

**Causes:**
- Fixture trying to create a directory that already exists
- Missing `dirs_exist_ok=True` parameter

**Fix:**
```python
# In conftest.py, use:
shutil.copytree(src, dst, dirs_exist_ok=True)
```

### Issue 3: Syntax Errors

**Error:**
```
IndentationError: unexpected indent
```

**Causes:**
- Mixed tabs and spaces
- Incorrect indentation level
- Missing indentation

**Fix:**
1. Check the line number in the error message
2. Ensure consistent indentation (4 spaces per level)
3. Use your editor's "show whitespace" feature

### Issue 4: Assertion Failures

**Error:**
```
AssertionError: assert (output_dir / "ca-trust.jks").exists()
```

**Causes:**
- Expected file wasn't created
- Wrong filename (e.g., standardized name changed)
- Function failed silently

**Fix:**
1. Check if filename changed (look for `bundlecraft-ca-trust.*` naming)
2. Add debug output:
   ```python
   print(f"Files in output_dir: {list(output_dir.glob('*'))}")
   assert (output_dir / "bundlecraft-ca-trust.jks").exists()
   ```
3. Run test with `-s` flag to see print statements

### Issue 5: Deprecated Options

**Error:**
```
Error: No such option: --formats
(Possible options: --force, --input-format, --output-format)
```

**Causes:**
- Test is using an old CLI option name
- CLI interface was updated but test wasn't

**Fix:**
```python
# Update test from:
["--formats", "p7b"]

# To:
["--output-format", "p7b"]
```

---

## ✍️ Writing New Tests

### Test File Structure

```python
"""Tests for [module name]."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from bundlecraft.module import function_to_test


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.module_name  # Use appropriate marker
class TestClassName:
    """Test suite for [what you're testing]."""

    def test_something_specific(self, fixture_name):
        """Test that [specific behavior] works correctly."""
        # Arrange: Set up test data
        input_data = "test value"

        # Act: Run the code being tested
        result = function_to_test(input_data)

        # Assert: Verify the result
        assert result == expected_value
        assert result.status == "success"
```

### Test Naming Conventions

✅ **Good:**
- `test_converter_creates_jks_file()`
- `test_build_fails_with_expired_cert()`
- `test_cli_help_displays_version()`

❌ **Bad:**
- `test1()` - Not descriptive
- `test_conversion()` - Too vague
- `test_works()` - Doesn't say what works

### Using Fixtures

Fixtures are test helpers that set up data or environment:

```python
def test_with_temp_workspace(self, temp_workspace):
    """Fixture automatically provides a clean temp directory."""
    # temp_workspace is a Path object to a temporary directory
    test_file = temp_workspace / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
```

### Testing CLI Commands

```python
def test_cli_command(self, cli_runner):
    """Test a CLI command."""
    result = cli_runner.invoke(
        main_command,
        ["--option", "value", "argument"]
    )

    assert result.exit_code == 0  # Success
    assert "Expected text" in result.output
```

### Testing Exceptions

```python
def test_function_raises_error(self):
    """Test that invalid input raises an error."""
    with pytest.raises(ValueError) as exc_info:
        function_that_should_fail("bad input")

    # Optionally verify the error message
    assert "expected error text" in str(exc_info.value)
```

### Parameterized Tests

Test the same function with multiple inputs:

```python
@pytest.mark.parametrize("format,expected_ext", [
    ("p7b", ".p7b"),
    ("jks", ".jks"),
    ("p12", ".p12"),
])
def test_multiple_formats(self, format, expected_ext):
    """Test conversion to multiple formats."""
    result = convert(format=format)
    assert result.endswith(expected_ext)
```

---

## 🛠️ Test Fixtures Explained

Fixtures are defined in `conftest.py` and provide reusable test setup.

### Available Fixtures

#### `temp_dir`
Creates a temporary directory that's automatically cleaned up.

```python
def test_with_temp_dir(self, temp_dir):
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")
    assert file_path.exists()
    # temp_dir is automatically deleted after test
```

#### `temp_workspace`
Creates a complete workspace with standard directory structure and test data.

```python
def test_with_workspace(self, temp_workspace):
    # Provides:
    # - sources/internal/
    # - config/bundles/
    # - config/envs/
    # - build/
    # Plus copies of test data from tests/data/
    config = temp_workspace / "config" / "bundles" / "test.yaml"
    assert config.exists()
```

#### `sample_cert_path`
Path to a valid test certificate.

```python
def test_with_cert(self, sample_cert_path):
    assert sample_cert_path.exists()
    assert sample_cert_path.suffix == ".pem"
```

#### `cli_runner`
Click CLI test runner for testing command-line interfaces.

```python
def test_cli(self, cli_runner):
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
```

### Creating New Fixtures

Add to `conftest.py`:

```python
@pytest.fixture
def my_custom_fixture():
    """Description of what this fixture provides."""
    # Setup code
    data = setup_test_data()

    yield data  # Provide to test

    # Teardown code (runs after test)
    cleanup_test_data()
```

---

## 🐛 Debugging Failed Tests

### Step 1: Run with Verbose Output

```bash
pytest tests/test_converter.py::TestConverter::test_convert_to_jks -vv
```

### Step 2: Show Print Statements

```bash
pytest tests/test_converter.py::TestConverter::test_convert_to_jks -s
```

Add debug output to your test:
```python
def test_something(self):
    result = function()
    print(f"DEBUG: result = {result}")  # Will show with -s flag
    assert result == expected
```

### Step 3: Use Traceback Options

```bash
# Short traceback (recommended)
pytest --tb=short

# One line per error
pytest --tb=line

# Full traceback (verbose, can be overwhelming)
pytest --tb=long
```

### Step 4: Drop into Debugger

```bash
# Stop at first failure and open debugger
pytest --pdb

# Or add breakpoint in test code:
def test_something(self):
    import pdb; pdb.set_trace()  # Debugger will stop here
    result = function()
```

### Step 5: Isolate the Problem

```bash
# Run just one test
pytest tests/test_file.py::TestClass::test_specific -vv

# Run with increased timeout (if test is slow)
pytest --timeout=60

# Run without capturing output
pytest --capture=no
```

---

## ⏰ When to Run Tests

### TL;DR - Quick Answer

**Best Practice Summary:**
- ✅ **Before commit:** Run affected tests (fast, < 10 seconds)
- ✅ **Before push:** Run full test suite with pre-commit hooks
- ✅ **On PR creation:** Automatic - GitHub Actions runs tests
- ✅ **Before merge:** Automatic - CI must pass before merge allowed
- ⚠️ **Manual runs:** Anytime you're unsure if your changes broke something

### Detailed Workflow

#### 1. **During Development** (Optional but Recommended)

While actively coding, run tests for the module you're working on:

```bash
# Working on converter? Test just that:
pytest tests/test_converter.py -v

# Working on builder? Test just that:
pytest tests/test_builder.py -v

# Quick sanity check (exits on first failure):
pytest -x
```

**Why:** Catch issues immediately while the code is fresh in your mind.

**When to skip:** If you're making many small experimental changes, wait until you have something working.

#### 2. **Before Every Commit** (Recommended)

BundleCraft uses **pre-commit hooks** that automatically run on `git commit`:

```bash
git add .
git commit -m "feat: add new feature"

# Pre-commit will automatically:
# ✓ Fix trailing whitespace
# ✓ Fix YAML formatting
# ✓ Run ruff linter
# ✓ Run black formatter
# ✓ Check for merge conflicts
# ✓ (Does NOT run pytest by default - too slow)
```

**Manual test run before commit:**
```bash
# Quick test run (recommended minimum)
pytest -x  # Stop at first failure

# Or test only what you changed
pytest tests/test_converter.py -v  # If you modified converter
```

**Why not auto-run pytest on every commit?**
- Tests can take 10-15 seconds (slows down your workflow)
- You might make multiple commits while working on a feature
- Better to run full suite before push instead

#### 3. **Before Every Push** (Strongly Recommended)

Before pushing to GitHub, run the full test suite:

```bash
# Full test suite
pytest -v

# If all pass, then push
git push origin your-branch
```

**Time investment:** ~10-15 seconds
**Value:** Prevents pushing broken code that will fail in CI

**Pro tip:** Create a git alias:
```bash
# Add to ~/.gitconfig
[alias]
    pushtest = "!pytest -v && git push"

# Then use:
git pushtest origin your-branch
```

#### 4. **On Pull Request** (Automatic)

When you create a PR, GitHub Actions automatically runs tests.

**Current setup:** BundleCraft has a GitHub Actions workflow (`.github/workflows/bundlecraft.yaml`) that:
- ✅ Runs on `workflow_dispatch` (manual trigger)
- ⚠️ **Does NOT automatically run on PR** (you should add this - see CI/CD section below)

**What you'll see:**
- Green checkmark ✅ = All tests passed
- Red X ❌ = Some tests failed (click to see details)
- Yellow circle 🟡 = Tests are still running

#### 5. **Before Merging** (Automatic + Manual Check)

**Automatic protection:**
- If you enable branch protection rules on GitHub, PRs can't be merged unless CI passes
- This prevents broken code from entering your main branch

**Manual check:**
```bash
# Before clicking "Merge PR", verify:
# 1. All CI checks are green ✅
# 2. No unresolved review comments
# 3. Branch is up to date with main

# Optionally, pull the PR branch locally and test:
git checkout pr-branch
pytest -v
# If passes, safe to merge
```

### Testing Strategy by Change Type

| Change Type | Minimum Testing | Recommended |
|-------------|----------------|-------------|
| **Bug fix** | Related module tests | Full suite |
| **New feature** | New tests + related modules | Full suite |
| **Refactoring** | Affected module + integration tests | Full suite |
| **Documentation only** | None required | Quick sanity check |
| **Config changes** | Integration tests | Full suite |
| **Dependency updates** | Full suite (mandatory) | Full suite + manual testing |

### Speed Optimization Tips

```bash
# Run tests in parallel (if you have pytest-xdist installed)
pytest -n auto

# Skip slow tests during development
pytest -m "not slow"

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

---

## 🤖 CI/CD Integration

### Current Setup

BundleCraft uses **GitHub Actions** for CI/CD. The workflow file is located at:
```
.github/workflows/bundlecraft.yaml
```

**Current capabilities:**
- ✅ Multi-stage pipeline (Discover → Build → Collect → Verify → Publish)
- ✅ Matrix builds (multiple bundles × environments)
- ✅ Artifact uploads
- ⚠️ **Missing:** Automatic test runs on PR/push

### Recommended: Add Automated Testing

#### Step 1: Add a Test Job to GitHub Actions

Add this to `.github/workflows/bundlecraft.yaml`:

```yaml
# =========================================================
#  STAGE 0: TEST - Run test suite on PRs and pushes
# =========================================================
test:
  runs-on: ubuntu-latest
  steps:
    - name: 🧾 Checkout repository
      uses: actions/checkout@v4

    - name: 🐍 Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: 📦 Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: 🧪 Run tests
      run: |
        pytest -v --tb=short

    - name: 📊 Generate coverage report
      run: |
        pytest --cov=bundlecraft --cov-report=xml --cov-report=term

    - name: 📈 Upload coverage to Codecov (optional)
      uses: codecov/codecov-action@v4
      if: always()
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

#### Step 2: Update Workflow Triggers

Change the `on:` section to run on PRs and pushes:

```yaml
on:
  push:
    branches:
      - main
      - develop
  pull_request:
    branches:
      - main
      - develop
  workflow_dispatch:  # Keep manual trigger option
```

#### Step 3: Make Test Job a Dependency

Update other jobs to depend on tests passing:

```yaml
build:
  needs: test  # Add this line
  runs-on: ubuntu-latest
  # ... rest of build job
```

### GitHub Branch Protection Rules

Enable these settings in your GitHub repository to enforce testing:

**Settings → Branches → Add branch protection rule**

For `main` branch:
- ✅ **Require pull request before merging**
- ✅ **Require status checks to pass before merging**
  - Select: `test` (your test job name)
  - Select: Any other required checks
- ✅ **Require branches to be up to date before merging**
- ⚠️ Optional: **Require linear history**
- ⚠️ Optional: **Require signed commits**

**Effect:** PRs cannot be merged if tests fail.

### Pre-commit CI Integration

BundleCraft uses **pre-commit.ci** (free for public repos):

**Already configured in `.pre-commit-config.yaml`:**
```yaml
ci:
  autofix_prs: true  # Auto-fix style issues in PRs
  autofix_commit_msg: 'chore(pre-commit): auto-fix code style issues'
  skip: []  # Don't skip any hooks
```

**What it does:**
- Runs on every PR
- Automatically fixes formatting issues
- Commits fixes back to your PR branch
- Shows check status in PR

### Adding pytest to Pre-commit Hooks

If you want tests to run on every commit (can be slow):

Add to `.pre-commit-config.yaml`:

```yaml
  # Python tests (optional - can be slow)
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [-v, --tb=short, -x]  # Stop on first failure
```

**Pros:**
- Catches issues immediately
- Enforces test discipline

**Cons:**
- Slows down commits (10-15 seconds)
- Can be frustrating during rapid development

**Recommendation:** Don't add pytest to pre-commit hooks. Instead:
1. Run tests manually before pushing
2. Let GitHub Actions run tests on PR
3. Use branch protection to prevent merging failing PRs

### Continuous Integration Best Practices

#### ✅ DO:
- Run full test suite on every PR
- Block merges if tests fail
- Run tests on multiple Python versions (3.10, 3.11, 3.12)
- Cache dependencies to speed up CI
- Fail fast (stop on first test failure in CI)
- Show test coverage trends

#### ❌ DON'T:
- Skip tests to "save time" (you'll pay later)
- Merge PRs with failing tests
- Ignore flaky tests (fix them or remove them)
- Run tests only on main branch (too late!)
- Have tests that depend on external services without mocking

### Example: Multi-Python Version Testing

Add a matrix strategy to test multiple Python versions:

```yaml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ['3.10', '3.11', '3.12']
  steps:
    - name: 🧾 Checkout repository
      uses: actions/checkout@v4

    - name: 🐍 Setup Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: 📦 Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: 🧪 Run tests
      run: pytest -v
```

### Monitoring Test Health

**Key metrics to track:**
- **Pass rate:** Should be > 95%
- **Flaky test rate:** Should be 0%
- **Test execution time:** Should be < 30 seconds
- **Code coverage:** Should be > 80%

**GitHub Actions insights:**
- Go to "Actions" tab → Select workflow → "..." menu → "View workflow runs"
- Check success rate over time
- Identify slow or flaky tests

### Troubleshooting CI Failures

**Test passes locally but fails in CI:**

Common causes:
1. **Different Python version**
   ```bash
   # Test locally with same version as CI
   pyenv install 3.11
   pyenv local 3.11
   pytest -v
   ```

2. **Missing dependencies**
   ```bash
   # Check CI logs for "ModuleNotFoundError"
   # Add missing package to pyproject.toml [project.dependencies]
   ```

3. **Path differences** (Windows vs Linux)
   ```python
   # Use pathlib.Path for cross-platform compatibility
   from pathlib import Path
   path = Path("dir") / "file.txt"  # ✅ Works everywhere
   path = "dir/file.txt"  # ❌ Breaks on Windows
   ```

4. **Timezone issues**
   ```python
   # Always use UTC or timezone-aware datetimes
   from datetime import datetime, timezone
   now = datetime.now(timezone.utc)  # ✅ Correct
   now = datetime.now()  # ❌ Ambiguous
   ```

5. **File system case sensitivity** (macOS is case-insensitive, Linux is case-sensitive)
   ```bash
   # Make sure file names match exactly
   # CI may fail if you have: File.py but import: file.py
   ```

**Quick fix workflow:**
```bash
# 1. Pull the exact commit that failed in CI
git checkout <commit-sha>

# 2. Run tests with same conditions as CI
pytest -v --tb=short

# 3. Fix the issue
# ... make changes ...

# 4. Verify fix
pytest -v

# 5. Push fix
git add .
git commit -m "fix: resolve CI test failure"
git push
```

---

## 🔄 Maintenance Tips

### When Code Changes

**If you rename a function:**
1. Search for the old name in tests: `grep -r "old_function_name" tests/`
2. Update all test imports and calls
3. Run affected tests: `pytest -k "function_name" -v`

**If you change CLI options:**
1. Find tests using old option: `grep -r "\-\-old-option" tests/`
2. Update to new option name
3. Run CLI tests: `pytest tests/test_cli.py tests/test_commands.py -v`

**If you change output filenames:**
1. Search for old patterns: `grep -r "old-filename-pattern" tests/`
2. Update assertions to match new naming
3. Run converter tests: `pytest tests/test_converter.py -v`

### Dealing with Skipped Tests

Skipped tests are marked with `pytest.skip()` and have TODO comments:

```python
def test_something(self):
    pytest.skip("TODO: Needs refactoring after API change")
```

**When to fix them:**
- Before a major release
- When you're working on related code
- When you have time for test maintenance

**How to fix them:**
1. Read the TODO comment to understand why it was skipped
2. Update the test to work with current code
3. Remove the `pytest.skip()` line
4. Run the test to verify it passes

### Test Coverage Goals

```bash
# Check current coverage
pytest --cov=bundlecraft --cov-report=term-missing

# Aim for:
# - 80%+ overall coverage
# - 90%+ for critical paths (builder, converter, verifier)
# - 60%+ for CLI/UI code (harder to test)
```

### Regular Maintenance Checklist

- [ ] Run full test suite: `pytest -v`
- [ ] Check for deprecation warnings
- [ ] Review skipped tests - can any be fixed?
- [ ] Update test data if certificate formats changed
- [ ] Verify tests still match CLI help text
- [ ] Run coverage report and check for gaps

### Performance Monitoring

```bash
# Find slowest tests
pytest --durations=10

# Example output:
# 5.23s call     tests/test_converter.py::test_convert_to_jks
# 3.45s call     tests/test_builder.py::test_build_bundle
```

Mark slow tests:
```python
@pytest.mark.slow
def test_large_bundle_processing(self):
    pass
```

Skip slow tests during development:
```bash
pytest -m "not slow"
```

---

## 📚 Additional Resources

### pytest Documentation
- Official docs: https://docs.pytest.org/
- Fixtures guide: https://docs.pytest.org/en/stable/fixture.html
- Parametrize guide: https://docs.pytest.org/en/stable/parametrize.html

### Click Testing
- Click testing docs: https://click.palletsprojects.com/en/stable/testing/

### Quick Reference Card

```bash
# Essential commands
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest -k "pattern"            # Run tests matching pattern
pytest tests/test_file.py      # Run specific file
pytest -m marker               # Run tests with marker
pytest --lf                    # Run last failed tests
pytest --ff                    # Run failures first, then others
pytest -x                      # Stop at first failure
pytest --pdb                   # Debug on failure
pytest -s                      # Show print statements
pytest --collect-only          # Show what tests would run
```

---

## ❓ Getting Help

**Test failing and you're stuck?**

1. **Read the error message carefully** - It usually tells you exactly what's wrong
2. **Run with `-vv`** - Get maximum detail
3. **Add print statements** - Debug what's happening
4. **Check git history** - See what changed: `git log tests/test_file.py`
5. **Isolate the test** - Run just one test to focus
6. **Check fixtures** - Make sure `conftest.py` fixtures are working

**Common Questions:**

**Q: Why are tests skipped?**
A: They're marked TODO for refactoring. See the skip message for details.

**Q: How do I run just failed tests?**
A: Use `pytest --lf` (last failed)

**Q: Tests pass locally but fail in CI?**
A: Check for environment differences (paths, Python version, dependencies). See the "Troubleshooting CI Failures" section.

**Q: How do I update test fixtures?**
A: Edit `conftest.py` or add test data to `tests/data/`

**Q: Should I commit test changes?**
A: Yes! Tests are code. Always commit test updates with related code changes.

**Q: Do I need to run tests before every commit?**
A: Not necessarily. Run tests before pushing. Let GitHub Actions catch issues in PRs.

**Q: Can GitHub run pytest automatically?**
A: Yes! Add a test job to `.github/workflows/bundlecraft.yaml`. See the "CI/CD Integration" section for complete setup.

**Q: What if tests are too slow?**
A: Use `pytest -x` (stop on first failure), `pytest -n auto` (parallel), or `pytest -m "not slow"` (skip slow tests).

---

**Remember:** Tests are your friends! They catch bugs before users do. When a test fails, it's protecting you from shipping broken code. 🛡️

(but yes they can still be annoying, valid)

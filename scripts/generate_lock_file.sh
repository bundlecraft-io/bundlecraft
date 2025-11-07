#!/usr/bin/env bash
#
# Generate requirements lock file from pyproject.toml
#
# This script installs pip-tools and generates requirements-lock.txt
# with exact dependency versions for deterministic production builds.
#
# Usage:
#   ./scripts/generate_lock_file.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔒 Generating requirements lock file..."
echo ""

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: pyproject.toml not found${NC}"
    echo "   Please run this script from the repository root"
    exit 1
fi

# Install pip-tools if not available
if ! command -v pip-compile &> /dev/null; then
    echo "📦 Installing pip-tools..."
    pip install --quiet pip-tools || {
        echo -e "${RED}❌ Failed to install pip-tools${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ pip-tools installed${NC}"
    echo ""
fi

# Generate the lock file
echo "🔧 Running pip-compile..."
echo "   Command: pip-compile pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking"
echo ""

if pip-compile pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking; then
    echo ""
    echo -e "${GREEN}✅ Lock file generated successfully!${NC}"
    echo ""
    echo "📄 Generated file: requirements-lock.txt"
    
    # Show summary
    if [ -f "requirements-lock.txt" ]; then
        NUM_PACKAGES=$(grep -cE "^[a-zA-Z0-9]" requirements-lock.txt || echo "0")
        echo "📦 Number of pinned packages: $NUM_PACKAGES"
    fi
    
    echo ""
    echo "Next steps:"
    echo "  1. Review the generated requirements-lock.txt"
    echo "  2. Test that it installs correctly: pip install -r requirements-lock.txt"
    echo "  3. Commit the file: git add requirements-lock.txt && git commit -m 'chore: update requirements lock file'"
    echo ""
    echo "For more information, see: docs/DEPENDENCY-LOCK.md"
else
    echo ""
    echo -e "${RED}❌ Failed to generate lock file${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check your internet connection"
    echo "  - Verify pyproject.toml is valid"
    echo "  - Try updating pip: pip install --upgrade pip"
    echo "  - Check for dependency conflicts in pyproject.toml"
    echo ""
    exit 1
fi

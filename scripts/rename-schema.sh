#!/usr/bin/env bash
#
# Schema Rename Script - Comprehensive refactor for BundleCraft naming schema
#
# Changes:
# - config/envs → config/envs
# - config/sources → config/sources
# - targets → bundles (in env configs)
# - includes → include_sources
# - craft → env terminology throughout codebase
# - target → bundle terminology throughout codebase
#

set -euo pipefail

echo "🔄 BundleCraft Schema Rename - Phase 2 (Python/Docs/CI)"
echo "=============================================="
echo ""

# Track changes
CHANGES_MADE=0

# Function to perform replacements in a file
rename_in_file() {
    local file="$1"
    local backup="${file}.bak"

    # Skip if file doesn't exist
    [[ ! -f "$file" ]] && return

    # Create backup
    cp "$file" "$backup"

    # Perform replacements (careful ordering to avoid double-replacements)
    sed -i \
        -e 's/config\/crafts/config\/envs/g' \
        -e 's/config\/bundles/config\/sources/g' \
        -e 's/config_dir\/crafts/config_dir\/envs/g' \
        -e 's/config_dir\/bundles/config_dir\/sources/g' \
        -e 's/CONFIG_DIR \/ "crafts"/CONFIG_DIR \/ "envs"/g' \
        -e 's/CONFIG_DIR \/ "bundles"/CONFIG_DIR \/ "sources"/g' \
        -e 's/validate_craft_config/validate_env_config/g' \
        -e 's/validate_bundle_config/validate_source_config/g' \
        -e 's/craft_path/env_path/g' \
        -e 's/craft_cfg/env_cfg_raw/g' \
        -e 's/craft_name/env_name/g' \
        -e 's/safe_craft/safe_env/g' \
        -e 's/targets_to_build/bundles_to_build/g' \
        -e 's/target_name/bundle_name/g' \
        -e 's/include_bundles/include_sources/g' \
        -e 's/targets_map/bundles_map/g' \
        -e 's/per_target/per_bundle/g' \
        -e 's/target_info/bundle_info/g' \
        -e 's/target_bundles/bundle_sources/g' \
        -e 's/bundle_targets/bundle_sources/g' \
        -e 's/raw_targets/raw_bundles/g' \
        "$file"

    # Check if file changed
    if ! diff -q "$file" "$backup" > /dev/null 2>&1; then
        echo "  ✓ Updated: $file"
        CHANGES_MADE=$((CHANGES_MADE + 1))
        rm "$backup"
    else
        # No changes, restore from backup
        mv "$backup" "$file"
    fi
}

# Update Python modules
echo "📝 Updating Python modules..."
for pyfile in bundlecraft/*.py bundlecraft/helpers/*.py; do
    rename_in_file "$pyfile"
done

# Update test files
echo ""
echo "🧪 Updating test files..."
for testfile in tests/*.py tests/fixtures/*.py 2>/dev/null; do
    [[ -f "$testfile" ]] && rename_in_file "$testfile"
done

# Update CI workflows
echo ""
echo "⚙️  Updating CI workflows..."
for workflow in .github/workflows/*.yaml .github/workflows/*.yml 2>/dev/null; do
    [[ -f "$workflow" ]] && rename_in_file "$workflow"
done

# Update documentation
echo ""
echo "📚 Updating documentation..."
for doc in README.md CONTRIBUTING.md docs/*.md; do
    [[ -f "$doc" ]] && rename_in_file "$doc"
done

# Update scripts
echo ""
echo "🔧 Updating scripts..."
for script in scripts/*.py scripts/*.sh; do
    [[ -f "$script" ]] && rename_in_file "$script"
done

echo ""
echo "=============================================="
echo "✅ Schema rename complete!"
echo "   Files updated: $CHANGES_MADE"
echo ""
echo "⚠️  Manual review required for:"
echo "   - Comments and docstrings referencing old terminology"
echo "   - CLI help text and user-facing messages"
echo "   - Release notes and changelogs"
echo ""
echo "🧪 Next steps:"
echo "   1. Review git diff for unexpected changes"
echo "   2. Run: pytest -v"
echo "   3. Run: python -m bundlecraft.builder --help"
echo "   4. Test: bundlecraft build --env dev --bundle internal"
echo ""

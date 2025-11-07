#!/bin/bash
# Lil helper script for quickly git tags (which triggers releases on GitHub)
#
# Takes in either "pre-release" or "main-release" as an arg, then reads the latest
# changelog entry from the relevant section of CHANGELOG.md to create a git tag,
# which it will then push to origin.
#
# WARNING:
# Deletes existing tag both locally and remotely before re-creating and pushing it!
# Make sure CHANGELOG has been updated too!
#
# Usage: ./deploy-tag.sh <pre-release|main-release>

RELEASE_CHANNEL=$1
FORCE_PUSH=${2:-false}

# Determine the git tag based on the changelog
if [ "$RELEASE_CHANNEL" == "pre-release" ]; then
    # Top pre-release (has dash, e.g. 1.0.0-beta.1)
    GIT_TAG="v$(grep -m1 -oP '^\#\# \[\K[0-9]+\.[0-9]+\.[0-9]+-[a-zA-Z0-9.]+(?=\])' CHANGELOG.md)"
elif [ "$RELEASE_CHANNEL" == "main-release" ]; then
    # Top stable release (no dash, e.g. 1.0.0)
    GIT_TAG="v$(grep -m1 -oP '^\#\# \[\K[0-9]+\.[0-9]+\.[0-9]+(?=\])' CHANGELOG.md)"
else
    echo "Invalid release channel specified. Use 'pre-release' or 'main-release'."
    exit 1
fi

# Check if tag already exists locally
# Delete if force push is true, exit script if false
if [ "$(git tag -l "$GIT_TAG")" ]; then
    if [ "$FORCE_PUSH" = false ]; then
        echo "Tag $GIT_TAG already exists locally. Use '$0 $1 true' to overwrite."
        exit 1
    elif [ "$FORCE_PUSH" = true ]; then
        echo "Tag $GIT_TAG already exists locally, but going to delete (force = true)"
        git tag -d $GIT_TAG
        echo "Tag $GIT_TAG deleted locally."
    fi
fi

# Check if tag already exists remotely
# Delete if force push is true, exit script if false
if git ls-remote --tags origin | grep -q "refs/tags/$GIT_TAG"; then
    if [ "$FORCE_PUSH" = false ]; then
        echo "Tag $GIT_TAG already exists on remote. Use '$0 $1 true' to overwrite."
        exit 1
    elif [ "$FORCE_PUSH" = true ]; then
        echo "Tag $GIT_TAG already exists on remote, but going to delete (force = true)"
        git push --delete origin $GIT_TAG
        echo "Tag $GIT_TAG deleted from remote."
    fi

fi

# Create and push the tag
git tag $GIT_TAG && git push origin --tags
if [ "$FORCE_PUSH" = false ]; then
    echo "Tag $GIT_TAG created and pushed to remote."
elif [ "$FORCE_PUSH" = true ]; then
    echo "Tag $GIT_TAG re-created and re-pushed to remote."
fi
echo "You can monitor the release process here:"
echo "🌍 https://github.com/bundlecraft-io/bundlecraft/actions/workflows/release.yaml?query=branch%3A${GIT_TAG}"

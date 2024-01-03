#!/bin/bash
# ./update-prow-config.sh <VERSION> <BRANCH>

VERSION=$1
BRANCH=$2

export VERSION BRANCH

if [ -z "$VERSION" ] || [ -z "$BRANCH" ]; then
    echo "Provide values for \$VERSION and \$BRANCH variables."
    exit 1
fi

template="openshift-openshift-docs-BRANCH.yaml"
new_prow_config="openshift-openshift-docs-${BRANCH}.yaml"

# Create a new Prow config
envsubst < "$template" > "$new_prow_config"

echo "New Prow config created: $new_prow_config"

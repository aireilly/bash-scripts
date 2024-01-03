#!/bin/bash
# ./update-prow-config-branches.sh expects branches.csv in the currect dir

while IFS=, read -r BRANCH VERSION; do
    export VERSION BRANCH
    if [ -z "$VERSION" ] || [ -z "$BRANCH" ]; then
        echo "Provide values for \$VERSION and \$BRANCH variables."
        exit 1
    fi

    template="openshift-openshift-docs-BRANCH.yaml"
    new_prow_config="openshift-openshift-docs-${BRANCH}.yaml"

    # Check if the template file exists
    if [ ! -f "$template" ]; then
        echo "Template file $template does not exist."
        continue
    fi

    # Create a new Prow config
    envsubst < "$template" > "$new_prow_config"

    echo "New Prow config created: $new_prow_config"
done < branches.csv

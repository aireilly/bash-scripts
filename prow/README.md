# Create prow jobs for openshift-docs

2. Run the `update-prow-config.sh` script to populate the `~/release` directory with the updated branch. Pass the `$VERSION` and `$BRANCH` variables. 
3. Change to the `~/release` directory or wherever you cloned the [openshift/release](https://github.com/openshift/release) repo.
4. Run the following: 
```cmd
make CONTAINER_ENGINE=podman registry-metadata

make CONTAINER_ENGINE=podman ci-operator-config

make jobs CONTAINER_ENGINE=podman WHAT=openshift/openshift-docs
```
5. Open a PR against the [openshift/release](https://github.com/openshift/release) master branch.
#!/usr/bin/env bash

# copy PR URL & checkout that branch, for example:
# $ ocp-checkout-other https://github.com/openshift/openshift-docs/pull/49805

set -e

PR_URL=$1

REPO_PATH="/home/aireilly/openshift-docs"

cd $REPO_PATH

PR_NUMBER=$(echo $PR_URL | sed "s|https://github.com/openshift/openshift-docs/pull/||")

git fetch upstream pull/$PR_NUMBER/head:"$PR_NUMBER"_review
git checkout "$PR_NUMBER"_review
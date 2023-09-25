#!/usr/bin/env bash

#copy branch path from github UI and checkout that branch directly from anywhere

set -e

REPO_PATH="/home/aireilly/openshift-docs"
USERNAME="aireilly"
USERNAME_BRANCH=$1

cd $REPO_PATH

BRANCH=$(echo $USERNAME_BRANCH | sed "s/$USERNAME://")

git checkout $BRANCH

$SHELL

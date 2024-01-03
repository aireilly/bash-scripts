#!/bin/bash
# Opens the GH Create PR dialog with correct compare branch opened

current_user=$(git config --get user.name)
current_branch=$(git rev-parse --abbrev-ref HEAD)
target_branch=$(git reflog show --format=%gs | grep "checkout: moving from" | grep $current_branch | awk -F 'from ' '{print $2}' | awk '{print $1}')

xdg-open https://github.com/openshift/openshift-docs/compare/"${target_branch}"..."${current_user}":openshift-docs:"${current_branch}"?expand=1
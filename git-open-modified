#!/usr/bin/bash

set -e

# count of most recent commits to open files from
NUM_COMMITS=$1

# count defaults to 1
if [[ -z "$NUM_COMMITS" ]]; then
    NUM_COMMITS="1"
fi

# open the files in Sublime Text  
subl -add $(git log -"$NUM_COMMITS" --name-only --pretty=format: --diff-filter=ACMR)

# open the files in VS Code
# code $(git log -"$NUM_COMMITS" --name-only --pretty=format: --diff-filter=ACMR)

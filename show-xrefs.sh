#!/bin/bash
#
# Pass a module ($MODULE) and an optional assembly ($PARENT) param to generate a list of possible xrefs for the module.
# The script searches the repo for module include statements and uses this to build a list of possible xrefs.
# You can pass relative, symlink, or complete paths to the script.
# Usage: show-xrefs [MODULE] [ASSEMBLY]

set -e

if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "ERROR: run this script from the openshift-docs Git repository." 1>&2
  exit 1
fi

REPO_PATH="$(git config -f ~/.gitconfig ocpd-repo.name)"
#resolve symlinks
MODULE=$(readlink -f $1)
#subtract $REPO_PATH from $1 with bash substring replacement
MODULE=${MODULE//"$REPO_PATH/"/}
PARENT_ASSEMBLY=$2
PARENT_FOLDER=$(dirname "$PARENT_ASSEMBLY")
ASSEMBLIES=$(grep -rnwl $REPO_PATH --include=\*.adoc -e $MODULE | awk '/(.*)\.adoc/')
MODULE_ID=$(grep '^\[id="[a-zA-Z0-9_-]*_{context}"\]' $MODULE | sed 's/_{context}"\]//' | sed 's/\[id="//')
MODULE_TITLE=$(grep '^=\s[a-zA-Z0-9]*' $MODULE | sed 's/=\s//')

cd $REPO_PATH

for ASSEMBLY in $ASSEMBLIES; do
  #if assembly is not provided, assume one level down from root
  if [[ -z "$PARENT_ASSEMBLY" ]]; then
    RELATIVE_ASSEMBLY=${ASSEMBLY//"$REPO_PATH/"/}
    ASSEMBLY_REL_PATH="../$RELATIVE_ASSEMBLY"
  else
    #calculate relative path of parent assembly folder
    ASSEMBLY_REL_PATH=$(realpath --relative-to="$PARENT_FOLDER" "$REPO_PATH")
  fi
  #prep for final xref
  ASSEMBLY=${ASSEMBLY//"$REPO_PATH/"/}
  ASSEMBLY_CONTEXT=$(grep ':context:\s[a-zA-Z0-9_-]*' $ASSEMBLY | sed 's/:context:\s//')
  echo ""
  echo "=================================="
  echo "generated the following xref(s)..."
  echo "=================================="
  echo ""
  if [[ -z "$PARENT_ASSEMBLY" ]]; then
    echo "xref:$ASSEMBLY_REL_PATH#"$MODULE_ID"_$ASSEMBLY_CONTEXT[$MODULE_TITLE]"
  else
    echo "xref:$ASSEMBLY_REL_PATH/$ASSEMBLY#"$MODULE_ID"_$ASSEMBLY_CONTEXT[$MODULE_TITLE]"
  fi
  echo ""
done
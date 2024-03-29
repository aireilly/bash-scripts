#!/usr/bin/env bash
# 
# Return all AsciiDoc files in current dir and lower that contain the search term.
# Wrap sentence fragments search terms in quotes. For example, 
# $ ff "bare-metal host"

set -e

SEARCH_TERM=$*
blue=$'\e[1;34m'

if [[ -z "$SEARCH_TERM" ]]; then
  echo "Oop! Enter a search term..."
else
  echo ""
  RETURNS=$(grep -E -rwl ${PWD} --include=\*.adoc --exclude-dir={drupal-build,_preview} -e "$SEARCH_TERM")
  for ITEM in $RETURNS
    do printf ''${blue}'\e]8;;file:///'$ITEM'\e\\'$ITEM'\e]8;;\e\\\n'${blue}''
  done
fi
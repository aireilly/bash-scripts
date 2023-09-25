#!/bin/bash
#
# Checks to see which YAML files listed in a text file are not referenced in AsciiDoc source files.

# Pass a text file containing the YAML filenames (one per line)
FILES="$1"

OCPDOCS_DIR="/home/aireilly/openshift-docs"

# Read $FILES, search for $FILENAME in AsciiDoc, if not found, report the missing file
while IFS= read -r FILENAME; do
  find "$OCPDOCS_DIR" -type f -name "*.adoc" -exec grep -qF "$FILENAME" {} \; || echo "$FILENAME is not used."
done < "$FILES"
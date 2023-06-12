#!/bin/bash
#
# grabs the reference CRs listed in $1 and copies them to /openshift-docs/snippets with a _ztp prefix.
# for example:
# $ ./get-ref-yaml.sh ran_ref_crs.txt 4.13

# pass a text file containing the reference CR filenames
FILES="$1"

# pass the OCP version as the second variable, for example, 4.13
OCP_VERSION="$2"

OCPDOCS_DIR="/home/aireilly/openshift-docs"

# clean up previous
rm -rf out ref && mkdir out ref

# pull the ztp container & extract the source
podman pull registry.redhat.io/openshift4/ztp-site-generate-rhel8:v"$OCP_VERSION"

podman run --log-driver=none --rm registry.redhat.io/openshift4/ztp-site-generate-rhel8:v"$OCP_VERSION" extract /home/ztp --tar | tar x -C ./out

# Read $FILES, find $FILE in /out, and copy to /ref 
while IFS= read -r FILENAME; do
    find out -name "$FILENAME" -exec cp {} ref \;
done < "$FILES"

# prepend a _ztp prefix to the found files and put them in /openshift-docs 
for OUT_FILE in ref/*; do
    BASENAME=$(basename "$OUT_FILE")
    mv "$OUT_FILE" "$OCPDOCS_DIR/snippets/ztp_$BASENAME"
done

echo " Put ZTP $OCP_VERSION CRs in $OCPDOCS_DIR/snippets"

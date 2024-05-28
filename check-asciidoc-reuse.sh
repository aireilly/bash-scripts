#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <directory_path>"
    exit 1
else 
    FOLDER="$1"
fi

INCL_REGEX='^include::modules\/.*\.adoc'

INCLUDES=()

FILES=$(find "$FOLDER" -type f -name '*.adoc')

# Initialize an associative array to count occurrences
declare -A OCCURRENCES

for FILE in $FILES; do
    while IFS= read -r line; do
        if [[ $line =~ $INCL_REGEX ]]; then
            INCLUDES+=("$line")
            ((OCCURRENCES["$line"]++))
        fi
    done < "$FILE"
done

# Print OCCURRENCES
# {
#     for line in "${!OCCURRENCES[@]}"; do
#         echo "$line: ${OCCURRENCES[$line]}"
#     done
# } > OCCURRENCES

# Count the number of includes
TOTAL=${#INCLUDES[@]}

# Count the number of duplicates
DUPLICATES=0
for count in "${OCCURRENCES[@]}"; do
    if (( count > 1 )); then
        ((DUPLICATES++))
    fi
done

# Calculate the percentage reuse
if (( TOTAL > 0 )); then
    percentage=$(echo "scale=2; ($DUPLICATES / $TOTAL) * 100" | bc)
else
    percentage=0
fi

echo "$percentage% of asciidoc modules are reused in the repo 🎉"
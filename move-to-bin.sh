#!/bin/bash

source_dir="."

dest_dir="$HOME/bin"

for file in "$source_dir"/*.sh; do
  if [ "$file" != "$source_dir/move-to-bin.sh" ]; then
    file_no_ext=$(basename "$file" .sh)
    cp "$file" "$dest_dir/$file_no_ext"
  fi
done

sudo chmod a+x "$dest_dir"/*.sh

echo "Moved and made *.sh files executable in $dest_dir"

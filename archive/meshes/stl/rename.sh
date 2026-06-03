#!/bin/bash

# for file in Texture.*.stl; do
  # new_file=$(echo "$file" | sed 's/Texture\.\([0-9]\{3\}\)\.stl/Texture\1.stl/')
for file in G-__*.stl; do
  new_file=$(echo "$file" | sed -E 's/G-__([0-9]+)\.([0-9]{3})\.stl/G\1_\2.stl/')

  mv "$file" "$new_file"
done

echo "Renaming complete!"

#!/usr/bin/env bash
set -eu

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <target_directory>"
  exit 1
fi

TARGET_DIR="$1"
echo "Sanitizing filenames under '$TARGET_DIR'..."

# Generate file list first to avoid infinite renaming loop
mapfile -t files < <(find "$TARGET_DIR" -depth -type f \( -iname '*.wav' -o -iname '*.txt' \))

for oldpath in "${files[@]}"; do
  dir=$(dirname "$oldpath")
  filename=$(basename "$oldpath")

  newname=$(python3 - <<'PYCODE' "$filename"
import sys, unicodedata, re

name = sys.argv[1]
s = unicodedata.normalize('NFKD', name)
s = ''.join(ch for ch in s if not unicodedata.combining(ch))
s = s.lower()
s = re.sub(r'[\s\-]+', '_', s)
s = re.sub(r'[^a-z0-9._]', '', s)
s = re.sub(r'_+', '_', s).strip('_')
print(s)
PYCODE
)

  if [[ "$filename" == "$newname" ]]; then
    continue
  fi

  old_full="$oldpath"
  new_full="$dir/$newname"

  if [[ -e "$new_full" ]]; then
    ts=$(date +%s)
    ext="${newname##*.}"
    base="${newname%.*}"
    new_full="$dir/${base}_${ts}.${ext}"
    echo "⚠ Collision: renaming to '$new_full'"
  fi

  echo "Renaming: '$old_full' → '$new_full'"
  mv "$old_full" "$new_full"
done

echo "✅ Done sanitizing."

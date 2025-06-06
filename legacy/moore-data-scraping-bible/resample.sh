
for f in MooreBible/raw/Mooré/*.mp3; do
  filename="$(basename "$f")"
  stem="${filename%.*}"
  ffmpeg -i "$f" -ac 1 -ar 16000 "MooreBible/raw/Mooré_resampled/${stem}.wav"
done
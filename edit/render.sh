#!/bin/bash
# Re-renders the reel from the original clips and the full song.
# Needs: ffmpeg (with zscale/libzimg), python3 + numpy + opencv-python-headless.
set -e
cd "$(dirname "$0")"
# 1. the song: 36 s starting where the reference reel's segment starts (211.881 s), -14 LUFS
SONG_SRC=$(ls ../*[Aa]ngreza*.mp4 ../*[Aa]ngreza*.m4a ../*[Aa]ngreza*.mp3 2>/dev/null | head -1)
[ -n "$SONG_SRC" ] || { echo "Put the full 'Slow Motion Angreza' song file in the repo root first."; exit 1; }
ffmpeg -v error -y -ss 211.881 -t 36.0 -i "$SONG_SRC" -vn -ac 2 -ar 48000 \
       -af "volume=-4.70dB,alimiter=limit=0.84:level=false" song_36s.wav
# 2. the edit decision list
python3 make_edl.py edl.json
# 3. render (HDR -> SDR tone-mapping, time remaps, whip transitions, grade, H.264 + AAC)
python3 reel.py edl.json ../Goa_Villa_Reel.mp4
# 4. silent version for adding the song inside Instagram
ffmpeg -v error -y -i ../Goa_Villa_Reel.mp4 -an -c:v copy -movflags +faststart ../Goa_Villa_Reel_no_music.mp4

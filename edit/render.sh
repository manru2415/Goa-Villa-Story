#!/bin/bash
# Re-renders the reel from the original clips.
# Needs: ffmpeg (with zscale/libzimg), python3 + numpy + opencv-python-headless.
set -e
cd "$(dirname "$0")"
# 1. the song segment = the audio of the reference reel
ffmpeg -v error -y -i "../Reference Story.MOV" -vn -ac 2 -ar 44100 song_segment.wav
# 2. the edit decision list
python3 make_edl.py edl.json
# 3. render (HDR -> SDR tone-mapping, time remaps, whip transitions, grade, H.264 + AAC)
python3 reel.py edl.json ../Goa_Villa_Reel.mp4
# 4. silent version for adding the song inside Instagram
ffmpeg -v error -y -i ../Goa_Villa_Reel.mp4 -an -c:v copy -movflags +faststart ../Goa_Villa_Reel_no_music.mp4

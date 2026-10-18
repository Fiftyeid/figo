#!/usr/bin/env bash
# Rebuild "World's Fastest Military Helicopter Explained" from sources in this folder.
# Requirements: python3, pip install pillow numpy scipy imageio-ffmpeg
set -euo pipefail
cd "$(dirname "$0")/src"
python3 timing.py                # narration timing + build/narration.wav + build/timeline.json
python3 check_timing.py          # lint storyboard timings
python3 render.py all 2 16 --resume  # frames -> build/video_noaudio.mp4
python3 music.py                 # original score + SFX + final mix -> build/final_audio.m4a
python3 deliverables.py          # subtitles, chapters/description, script, thumbnail -> output/
cd ../build
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -y -v error -i video_noaudio.mp4 -i final_audio.m4a \
    -map 0:v -map 1:a -c:v libx264 -preset veryfast -crf 23 \
    -maxrate 850k -bufsize 1700k -profile:v high -pix_fmt yuv420p \
    -c:a copy -movflags +faststart ../output/worlds_fastest_military_helicopter.mp4
echo "done -> heli/output/worlds_fastest_military_helicopter.mp4"

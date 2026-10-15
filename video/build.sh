#!/usr/bin/env bash
# Rebuild the whole video from the sources in this folder.
# Requirements: python3, pip install pillow numpy scipy shapely imageio-ffmpeg
#               + libfribidi (Arabic text shaping in Pillow, e.g. `apt install libfribidi0`)
set -euo pipefail
cd "$(dirname "$0")/src"
python3 timing.py          # narration timing + build/narration.wav + build/timeline.json
python3 render.py all 2 8  # frames -> build/video_noaudio.mp4   (≈25 min on 2 cores)
python3 music.py           # original score + SFX + final mix -> build/final_audio.m4a
python3 deliverables.py    # subtitles, chapters, script.md, thumbnail -> output/
cd ../build
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -y -v error -i video_noaudio.mp4 -c:v libx264 -preset medium -b:v 760k -pass 1 -passlogfile x264pass \
    -profile:v high -pix_fmt yuv420p -an -f null /dev/null
$FF -y -v error -i video_noaudio.mp4 -i final_audio.m4a -map 0:v -map 1:a -c:v libx264 -preset medium \
    -b:v 760k -maxrate 2800k -bufsize 5600k -pass 2 -passlogfile x264pass -profile:v high -pix_fmt yuv420p \
    -c:a copy -movflags +faststart ../output/egypt_governorates_names.mp4
echo "done -> video/output/egypt_governorates_names.mp4"

#!/bin/bash
# Build the listener-study assets:
#  1. Generate stimulus excerpts (calls build_stimuli.py)
#  2. Convert WAV → MP3 (smaller for web delivery; uses ffmpeg)
#  3. Generate a warm-up clip (a synth-tone test signal)
#
# Requires: ffmpeg
set -e
DIR=/Volumes/MAC_M3_Store/Projects/listener_study_2026
PY=/Volumes/MAC_M3_Store/Dev_Tools/miniforge3/bin/python
cd "$DIR"

echo "=== Step 1: Generate stimulus excerpts (WAV) ==="
$PY build_stimuli.py

echo ""
echo "=== Step 2: Convert WAV → MP3 (web-friendly) ==="
if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: ffmpeg not installed. Install via 'brew install ffmpeg'."
    exit 1
fi

for wav in stimuli/*.wav; do
    mp3="${wav%.wav}.mp3"
    if [ -f "$mp3" ]; then
        echo "  skip (exists): $mp3"
        continue
    fi
    ffmpeg -y -hide_banner -loglevel warning -i "$wav" -codec:a libmp3lame -b:a 128k "$mp3"
    echo "  wrote: $mp3"
done

echo ""
echo "=== Step 3: Generate warm-up clip ==="
$PY -c "
import numpy as np, soundfile as sf
sr = 44100; t = np.linspace(0, 4, sr*4, endpoint=False)
# A modest synthesised tone: a tone with vibrato + fade in/out
freq = 220 * 2 ** (np.linspace(0, 0.6, len(t)))
phase = np.cumsum(2*np.pi*freq/sr)
sig = 0.18 * np.sin(phase) + 0.05 * np.sin(2*phase)
# Envelope
env = np.minimum(t/0.2, 1.0) * np.minimum((4 - t)/0.3, 1.0)
sig *= env
sf.write('stimuli/warmup.wav', sig.astype(np.float32), sr)
print('wrote stimuli/warmup.wav (4s pitch sweep — listener volume reference)')
"

echo ""
echo "=== Done. Stimuli in stimuli/ ==="
ls -la stimuli/*.mp3 2>/dev/null | head

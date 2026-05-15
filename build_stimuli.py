#!/usr/bin/env python3
"""Generate stimuli for the brand-identification listener study (v2 design).

Uses musical VA demo renders (not calibration sweeps) so listeners hear
musically-meaningful audio. Each stimulus is associated with a ground-truth
system label (Buchla 200, Serge, EMS/VCS3, Soundfreak); the survey asks
participants to identify the system.

The methodology pivot's prediction is that listener identification accuracy
should follow the system-clustering pattern from §6.5: Soundfreak should
be easiest to identify (single-designer aesthetic), Buchla 200 hardest
(intra-system heterogeneity per Verbos/Buchla USA interviews).
"""
from __future__ import annotations
import json, hashlib, random
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, sosfiltfilt

DEMOS_DIR = Path("/Volumes/MAC_M3_Store/Documents/va_comparison_renders/musical_demos")
STIM_DIR = Path("/Volumes/MAC_M3_Store/Projects/listener_study_2026/stimuli")
STIM_DIR.mkdir(exist_ok=True, parents=True)

SR = 44100
EXCERPT_S = 12.0   # 12s excerpts from 15s demos (drop last few seconds for clean fade)
START_S = 1.0       # skip first 1s

# Curated stimulus selection. Each entry: (label, file, system, start_s, dur_s).
# Per-clip start_s/dur_s overrides handle source files with leading silence or
# atypical lengths (e.g. DUSG's source is only 10s with a 2.25s silent attack).
# EMS VCS3 oscillator removed — source render `08_vcs3_oscillator.wav` is silent.
STIMULI = [
    # (label, file, system, start_s, dur_s)
    # start_s = "auto" picks best window by spectral-flux variance.
    # Smooth parameter changes preserved — no gating/AM is applied.
    # Buchla 200 series — 9 stimuli
    ("Buchla 292 LPG (vactrol)",      "25_buchla_292_lpg.wav",       "buchla_200", 0.5, 7.0),
    ("Buchla 292 vintage",            "22_buchla_292_vintage.wav",   "buchla_200", 1.0, 12.0),
    ("Buchla 281 function gen",       "02_buchla_281_function_gen.wav","buchla_200", 1.75, 12.0),
    ("Buchla 285 frequency shifter",  "14_buchla_285_freqshifter.wav","buchla_200", "auto", 12.0),
    ("Buchla 296 spectral processor", "16_buchla_296_spectral.wav",  "buchla_200", "auto", 12.0),
    ("Buchla 259 oscillator",         "10_buchla_259_oscillator.wav","buchla_200", "auto", 12.0),
    ("Buchla 265 source-of-uncertainty","04_buchla_265_uncertainty.wav","buchla_200", "auto", 12.0),
    ("Buchla 291 filter",             "21_buchla_291_filter.wav",    "buchla_200", "auto", 12.0),
    ("Buchla 277 signal delay",       "09_buchla_277_delay.wav",     "buchla_200", "auto", 12.0),
    # Serge Modular — 6 stimuli
    ("Serge PCO oscillator",          "13_serge_pco.wav",             "serge", "auto", 9.0),
    ("Serge VCFQ filter",             "19_serge_vcfq.wav",            "serge", 1.0, 12.0),
    ("Serge DUSG envelope",           "24_serge_dusg.wav",            "serge", 2.5, 7.0),
    ("Serge wave multiplier",         "05_serge_wave_multiplier.wav", "serge", "auto", 12.0),
    ("Serge NTO oscillator",          "23_serge_nto.wav",             "serge", "auto", 9.0),
    ("Serge frequency shifter",       "17_serge_frequency_shifter.wav","serge", "auto", 12.0),
    # Soundfreak — 2 stimuli
    ("Soundfreak filter",             "03_soundfreak_filter.wav",     "soundfreak", "auto", 12.0),
    ("Soundfreak envelope",           "01_soundfreak_envelope.wav",   "soundfreak", 1.0, 12.0),
]

SYSTEM_LABELS = {
    "buchla_200":  "Buchla 200 series",
    "serge":       "Serge Modular",
    "ems_vcs3":    "EMS / VCS3 (Synthi)",
    "soundfreak":  "Soundfreak (or other obscure vintage modular)",
}
# Note: EMS / VCS3 stays in the choice menu as a foil — no source clip survived QC.
# Listeners selecting "EMS" therefore always answer wrong, which lets us measure
# brand confusion / overconfident attribution as a free signal.

# Placebo / control stimuli for attention checks. Ground-truth system is
# 'placebo_modern' (expected listener choice: "modern/digital" or "unknown").
# Repeats of regular stimuli (consistency check) are added at runtime.
PLACEBO_REPEAT_INDICES = [0, 5]   # repeat stimuli 0 and 5 of the main list

# NOTE: peer-distance (capture-vs-VA) trials were removed by design — the
# capture-vs-VA distance is already measured by the J=1.33 vs family-floor
# metric chain (\\S6.5 in the thesis); asking listeners to A/B the boring
# calibration sweeps was redundant and listening-fatigue-heavy. The study now
# focuses purely on brand-identification of VA-rendered musical demos.


def ac_couple(x, sr=SR, fc=20.0):
    if len(x) < 32: return x
    sos = butter(4, fc / (sr * 0.5), btype="high", output="sos")
    return sosfiltfilt(sos, x).astype(x.dtype)


def load_excerpt(p: Path, start_s=START_S, dur_s=EXCERPT_S):
    a, sr = sf.read(str(p), always_2d=True)
    mono = a[:, 0].astype(np.float32)
    if sr != SR: mono = librosa.resample(mono, orig_sr=sr, target_sr=SR)
    mono = ac_couple(mono, SR)
    start = int(start_s * SR)
    n = int(dur_s * SR)
    end = min(start + n, len(mono))
    return mono[start:end]


def rms_normalize(x, target_rms=0.15):
    rms = float(np.sqrt(np.mean(x ** 2)))
    if rms < 1e-9: return x
    return np.clip(x * (target_rms / rms), -0.95, 0.95)


def find_musical_window(x, sr, dur_s, hop_s=0.25):
    """Pick the dur_s-second window with the most spectral activity (variance of
    short-time RMS — proxy for note-onset density / CV-modulation events)."""
    win_n = int(dur_s * sr)
    if len(x) <= win_n:
        return 0
    # Short-time RMS curve at 100 ms resolution
    win = sr // 10
    n_win = len(x) // win
    rms = np.array([np.sqrt(np.mean(x[i*win:(i+1)*win] ** 2)) for i in range(n_win)])
    # Sliding variance across a dur_s window
    var_win_n = int(dur_s * 10)   # 100 ms hops
    if len(rms) <= var_win_n:
        return 0
    scores = []
    for i in range(0, len(rms) - var_win_n, int(hop_s * 10)):
        scores.append(rms[i:i + var_win_n].std())
    best_idx = int(np.argmax(scores))
    return best_idx * hop_s  # seconds


def musical_gate(x, sr, bpm=110.0, division=4, depth=0.30):
    """Apply a subtle tempo-locked AM gate to add rhythmic articulation to
    continuous-tone stimuli. Gentle: depth=0.30 means the signal never drops
    below 70% — adds groove without sounding chopped. Short attack (40 ms),
    longer decay shape. division=4 → quarter notes, division=8 → eighths."""
    beat_s = 60.0 / bpm
    note_s = beat_s * 4 / division
    t = np.arange(len(x)) / sr
    phase = (t / note_s) % 1.0
    attack_frac = 0.08
    env = np.where(phase < attack_frac,
                   phase / attack_frac,
                   1.0 - (phase - attack_frac) / (1.0 - attack_frac))
    env = np.clip(env, 0.0, 1.0)
    gate = (1.0 - depth) + depth * env
    return (x * gate.astype(x.dtype))


def fade_inout(x, ms=30):
    n = int(ms / 1000 * SR)
    if n * 2 > len(x): return x
    fade = np.linspace(0, 1, n) ** 2
    y = x.copy()
    y[:n] *= fade
    y[-n:] *= fade[::-1]
    return y


def make_id(label):
    return hashlib.md5(label.encode()).hexdigest()[:8]


def synth_modern_placebo_bell():
    """Generate a 'modern digital' placebo: FM-bell timbre with vibrato.
    Clearly not vintage analog modular — sounds like a Yamaha DX7 / VST."""
    dur = EXCERPT_S
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    # FM bell: carrier modulated by harmonic
    carrier_freq = 440.0
    mod_freq = 2.0 * carrier_freq      # bell-like ratio
    mod_index = 5.0 * np.exp(-t * 0.6) # decaying brightness
    carrier_phase = 2*np.pi*carrier_freq*t + mod_index * np.sin(2*np.pi*mod_freq*t)
    # Pluck envelope per note, with sequence of notes
    notes_hz = [440, 554.37, 659.25, 587.33, 440, 369.99, 440, 880]  # arpeggio
    note_len = dur / len(notes_hz)
    sig = np.zeros_like(t)
    for i, f in enumerate(notes_hz):
        n_start = int(i * note_len * SR)
        n_end   = int(min((i + 1) * note_len * SR, len(t)))
        tt = t[:n_end - n_start]
        env = np.exp(-tt * 5)
        carrier_phase = 2*np.pi*f*tt + mod_index[:n_end-n_start] * np.sin(2*np.pi*f*2*tt)
        sig[n_start:n_end] = 0.4 * env * np.sin(carrier_phase)
    return sig.astype(np.float32)


def synth_modern_placebo_supersaw():
    """Generate a 'supersaw lead' placebo: characteristic modern digital sound,
    not in any way vintage analog. Wide stack of detuned saws + slight phasing."""
    dur = EXCERPT_S
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    base_freq = 261.63   # C4
    detune = [0.99, 0.995, 1.0, 1.005, 1.01, 1.015, 0.985]
    sig = np.zeros_like(t)
    for d in detune:
        f = base_freq * d
        # Sawtooth via additive
        for h in range(1, 16):
            sig += (1.0 / h) * np.sin(2*np.pi * f * h * t)
    sig /= len(detune)
    # LFO modulation on amplitude
    lfo = 0.5 + 0.5 * np.sin(2*np.pi * 0.5 * t)
    # Fade in/out + chord progression by detuning over time
    bend = 1.0 + 0.05 * np.sin(2*np.pi * 0.25 * t)
    sig = sig * lfo * 0.3
    return sig.astype(np.float32)


def main():
    stimuli = []
    print(f"Building {len(STIMULI)} stimulus clips for brand-identification study...")
    for item in STIMULI:
        label, fname, system = item[0], item[1], item[2]
        start_s = item[3] if len(item) > 3 else START_S
        dur_s   = item[4] if len(item) > 4 else EXCERPT_S
        gate_div = item[5] if len(item) > 5 else 0
        src = DEMOS_DIR / fname
        if not src.exists():
            print(f"  SKIP {label}: missing {fname}")
            continue
        try:
            # AUTO_WINDOW: pick best start by spectral-flux variance
            if start_s == "auto":
                # Load full file briefly to find best window
                a, sr = sf.read(str(src), always_2d=True)
                mono = a[:, 0].astype(np.float32)
                if sr != SR: mono = librosa.resample(mono, orig_sr=sr, target_sr=SR)
                mono = ac_couple(mono, SR)
                start_s = find_musical_window(mono, SR, dur_s)
            audio = load_excerpt(src, start_s=start_s, dur_s=dur_s)
            if gate_div > 0:
                audio = musical_gate(audio, SR, bpm=110.0, division=gate_div, depth=0.30)
            audio = fade_inout(rms_normalize(audio))
        except Exception as e:
            print(f"  SKIP {label}: {e}")
            continue
        gate_note = f"gate=1/{gate_div}" if gate_div > 0 else "no-gate"
        sid = make_id(label)
        sf.write(STIM_DIR / f"{sid}.wav", audio, SR, subtype="PCM_16")
        stimuli.append({
            "id": sid,
            "label": label,
            "file": f"{sid}.mp3",
            "system": system,
            "system_label": SYSTEM_LABELS[system],
        })
        print(f"  OK   {label} → {sid}.wav  ({system}, start={start_s:.2f}s, {gate_note})")

    # === PLACEBO STIMULI ===
    print("\nGenerating modern-digital placebo stimuli...")
    placebo_stimuli = []
    for plabel, gen_fn in [("Modern Digital — FM Bell",  synth_modern_placebo_bell),
                            ("Modern Digital — Supersaw", synth_modern_placebo_supersaw)]:
        audio = fade_inout(rms_normalize(gen_fn()))
        sid = make_id(plabel)
        sf.write(STIM_DIR / f"{sid}.wav", audio, SR, subtype="PCM_16")
        s = {"id": sid, "label": plabel, "file": f"{sid}.mp3",
             "system": "placebo_modern",
             "system_label": "modern/digital placebo (ground truth: not vintage modular)",
             "is_placebo": True}
        placebo_stimuli.append(s)
        print(f"  OK   {plabel} → {sid}.wav  (PLACEBO)")
    stimuli += placebo_stimuli

    # === TRIAL LIST ===
    trials = []
    # 1. Main stimuli — 1 trial each
    for s in [x for x in stimuli if not x.get("is_placebo")]:
        trials.append({
            "stimulus_id": s["id"],
            "file": s["file"],
            "label": s["label"],
            "true_system": s["system"],
            "category": "main",
        })
    # 2. Placebo modern-digital trials (expected answer: "modern")
    for s in placebo_stimuli:
        trials.append({
            "stimulus_id": s["id"],
            "file": s["file"],
            "label": s["label"],
            "true_system": "placebo_modern",
            "category": "placebo_modern",
        })
    # 3. Repeat-consistency trials: present 2 of the existing stimuli a second time
    main_only = [x for x in stimuli if not x.get("is_placebo")]
    for idx in PLACEBO_REPEAT_INDICES:
        if idx < len(main_only):
            s = main_only[idx]
            trials.append({
                "stimulus_id": s["id"],   # SAME stimulus_id as the original trial
                "file": s["file"],
                "label": s["label"] + " (repeat)",
                "true_system": s["system"],
                "category": "repeat_consistency",
            })

    out = {
        "stimuli": stimuli,
        "trials": trials,
        "system_options": SYSTEM_LABELS,
        "extra_options": {
            "unknown": "I don't recognise this style",
            "modern":  "Sounds modern / digital, not vintage modular",
        },
        "sample_rate": SR,
        "duration_s": EXCERPT_S,
        "placebo_design": {
            "modern_digital_placebos": len(placebo_stimuli),
            "repeat_consistency_trials": len(PLACEBO_REPEAT_INDICES),
            "main_trials": len(main_only),
            "total_trials": len(trials),
        },
    }
    out_path = STIM_DIR.parent / "trial_list.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {len(stimuli)} stimuli, {len(trials)} trials")
    print(f"trial_list.json saved to {out_path}")
    print(f"\nGround-truth distribution (brand-ID trials only):")
    from collections import Counter
    brand_trials = [t for t in trials if "true_system" in t]
    for sys, n in Counter(t["true_system"] for t in brand_trials).most_common():
        label = SYSTEM_LABELS.get(sys, sys)
        print(f"  {label}: {n}")
    print(f"\nTrial category breakdown:")
    for cat, n in Counter(t.get("category", "main") for t in trials).most_common():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    raise SystemExit(main())

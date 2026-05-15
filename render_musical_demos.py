#!/usr/bin/env python3
"""Re-render the listener-study modules with melodic input.

Uses the same simulate() functions the VST wraps. Fast path:
  - Oscillators take array pitch_cv directly → no segmenting, ~1× realtime
  - Filters/effects take time-varying CV arrays + melodic saw audio_in
  - LPG/envelopes get per-note gate at musical intervals
  - Parameter sweeps remain smooth (incommensurate triangle waves)

`use_spice=False` is used where available (DSP / neural-fallback path); the
audio loses some sub-percent SPICE detail but renders in real time and runs
the same brand-character signal-path as the deployed VST plugin.
"""
import os, sys, time
import numpy as np
import soundfile as sf
from pathlib import Path

REPO = Path('/Users/georgeredpath/modular-ir-capture')
sys.path.insert(0, str(REPO / 'python' / 'src'))

SR = 48000
OUT_DIR = Path('/Volumes/MAC_M3_Store/Projects/listener_study_2026/musical_renders')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# === MELODIC PHRASE: D minor pentatonic, 32 eighth-notes ===
PHRASE = [0, 3, 5, 7, 5, 3, 0, -5,
          5, 7, 10, 7, 5, 3, 0, 0,
          3, 5, 7, 10, 12, 10, 7, 5,
          7, 5, 3, 0, -5, 0, 3, 0]
BPM = 110.0
NOTE_S = 60.0 / BPM / 2.0    # eighth note
ROOT_HZ = 220.0
DUR = 8.5     # 32 × 0.273 → 8.7s, round down a touch
N = int(DUR * SR)
RATES = [0.071, 0.113, 0.157, 0.193, 0.229, 0.271]


def melodic_voct(dur_s=DUR, v_per_oct=1.0):
    """Per-sample V/oct trajectory (V relative to root)."""
    n = int(dur_s * SR); note_n = int(NOTE_S * SR)
    out = np.zeros(n, dtype=np.float64)
    for i in range(n):
        idx = (i // note_n) % len(PHRASE)
        out[i] = PHRASE[idx] * v_per_oct / 12.0
    return out


def melodic_pitch_cv(dur_s=DUR, center=5.0, swing=2.0, v_min=0.0, v_max=10.0):
    """Pitch-CV trajectory centred at `center` V with stepwise melody."""
    voct = melodic_voct(dur_s)         # ±1.4V approx
    cv = center + voct * (swing / 1.4)
    return np.clip(cv, v_min, v_max)


def melodic_saw(dur_s=DUR, attack_ms=5, decay_ms=80):
    """Melodic bandlimited sawtooth with per-note envelope."""
    n = int(dur_s * SR); note_n = int(NOTE_S * SR)
    out = np.zeros(n, dtype=np.float64)
    phase = 0.0
    nyq = SR / 2
    for i in range(n):
        idx = (i // note_n) % len(PHRASE)
        f = ROOT_HZ * 2 ** (PHRASE[idx] / 12.0)
        phase += 2 * np.pi * f / SR
        s = 0.0
        for h in range(1, 16):
            if f * h >= nyq: break
            s += np.sin(h * phase) / h
        out[i] = s * 0.3
    a = int(attack_ms / 1000 * SR); d = int(decay_ms / 1000 * SR)
    env = np.ones(note_n); env[:a] = np.linspace(0, 1, a); env[-d:] *= np.linspace(1, 0.65, d)
    for i in range(0, n, note_n):
        seg = env[:min(note_n, n - i)]
        out[i:i + len(seg)] *= seg
    return out


def melodic_sine(dur_s=DUR):
    n = int(dur_s * SR); note_n = int(NOTE_S * SR)
    out = np.zeros(n, dtype=np.float64); phase = 0.0
    for i in range(n):
        idx = (i // note_n) % len(PHRASE)
        f = ROOT_HZ * 2 ** (PHRASE[idx] / 12.0)
        phase += 2 * np.pi * f / SR
        out[i] = np.sin(phase)
    return out * 0.6


def gate_pattern(dur_s=DUR, duty=0.4, hi_v=10.0):
    n = int(dur_s * SR); note_n = int(NOTE_S * SR)
    g = np.zeros(n, dtype=np.float64); on_n = int(duty * note_n)
    for i in range(0, n, note_n):
        g[i:i + on_n] = hi_v
    return g


def tri_sweep(rate_hz, lo, hi, length=N):
    t = np.arange(length) / SR
    p = (t * rate_hz) % 1.0
    tri = 2.0 * np.abs(2.0 * p - 1.0) - 1.0
    return lo + (tri + 1.0) / 2.0 * (hi - lo)


def first_array(r, min_len=1000):
    if isinstance(r, np.ndarray) and len(r) > min_len: return r
    if isinstance(r, dict):
        for v in r.values():
            if isinstance(v, np.ndarray) and len(v) > min_len: return v
    if isinstance(r, (tuple, list)):
        for v in r:
            if isinstance(v, np.ndarray) and len(v) > min_len: return v
    return None


def save_norm(name, out, target_rms=0.18, peak_max=0.95):
    if out is None or len(out) < 1000:
        print(f"  WARN {name}: no audio"); return False
    out = np.asarray(out, dtype=np.float64).flatten()
    out = out - np.mean(out)
    rms = float(np.sqrt(np.mean(out ** 2)))
    if rms < 1e-9: print(f"  WARN {name}: silent"); return False
    peak = float(np.max(np.abs(out)))
    g = min(target_rms / rms, peak_max / max(peak, 1e-9))
    out = (out * g).astype(np.float32)
    sf.write(str(OUT_DIR / f"{name}.wav"), out, SR, subtype='PCM_16')
    print(f"  OK   {name}.wav  ({len(out)/SR:.1f}s, peak={20*np.log10(peak*g+1e-9):+.1f}dB)")
    return True


def attempt(name, fn):
    t0 = time.time()
    try:
        out = fn()
        if not save_norm(name, out): return False
    except Exception as e:
        print(f"  FAIL {name}: {type(e).__name__}: {str(e)[:120]}")
        return False
    finally:
        sys.stdout.flush()
    print(f"        [{time.time()-t0:.1f}s]")
    return True


def main():
    ok = fail = 0
    t0 = time.time()

    # === OSCILLATORS (array pitch_cv, use_spice=False) ===

    def r_259():
        # 259 uses 8x oversampling internally → arrays need to be at INTERNAL_SR (384kHz)
        os.environ['VA_FAST_MODE'] = '1'   # reduce to 2x oversample
        from models.spice import buchla_259_oscillator as mod259
        import importlib; importlib.reload(mod259)
        from models.spice.buchla_259_oscillator import simulate as f, INTERNAL_SR as ISR
        N_int = int(DUR * ISR)
        def at_internal(arr):
            return np.interp(np.linspace(0, len(arr)-1, N_int), np.arange(len(arr)), arr)
        r = f(pitch_cv=at_internal(melodic_pitch_cv(center=5.0, swing=2.5)),
              mod_freq_cv=at_internal(tri_sweep(RATES[1], 2.0, 6.0)),
              mod_index_cv=at_internal(tri_sweep(RATES[2], 1.0, 6.0)),
              timbre_cv=at_internal(tri_sweep(RATES[3], 2.0, 8.0)),
              symmetry=at_internal(tri_sweep(RATES[4], 3.0, 7.0)),
              waveshape='saw', order=1, pitch_mod=False, timbre_mod=True,
              ampl_mod=False, phase_lock=False, use_spice=False,
              duration_s=DUR, sample_rate=SR)
        return first_array(r)
    ok += attempt('buchla_259_oscillator', r_259)

    def r_nto():
        from models.spice.serge_nto import simulate as f
        r = f(pitch_cv=melodic_pitch_cv(center=2.5, swing=1.2, v_max=5.0),
              vc_wave=tri_sweep(RATES[1], 1.0, 4.0),
              fm_voltage=tri_sweep(RATES[2], 1.0, 3.0),
              vc_port=tri_sweep(RATES[3], 1.0, 4.0),
              vc_aux=tri_sweep(RATES[4], 1.0, 4.0),
              duration_s=DUR, sample_rate=SR, use_spice=False)
        return first_array(r)
    ok += attempt('serge_nto', r_nto)

    def r_pco():
        from models.spice.serge_pco import simulate as f
        r = f(pitch_cv=melodic_pitch_cv(center=2.5, swing=1.2, v_max=5.0),
              voct_vcf=tri_sweep(RATES[1], 1.0, 4.0),
              vc_f=tri_sweep(RATES[2], 1.0, 4.0),
              in_fm=tri_sweep(RATES[3], 0.0, 1.0),
              vc_k=tri_sweep(RATES[4], 1.0, 4.0),
              vc_l=tri_sweep(RATES[0], 1.0, 4.0),
              sync=False, hi_lo='hi',
              duration_s=DUR, sample_rate=SR)
        return first_array(r)
    ok += attempt('serge_pco', r_pco)

    # === FILTERS (melodic saw input + smooth filter sweep) ===

    def r_291():
        from models.spice.buchla_291_filter import simulate as f
        audio = melodic_saw()
        r = f(audio,
              freq_cv=tri_sweep(RATES[0], 1.0, 9.0),
              bw_cv=tri_sweep(RATES[1], 1.0, 8.0),
              fm_cv=tri_sweep(RATES[2], 0.0, 3.0),
              section='a', use_spice=False)
        if isinstance(r, dict):
            for k in ['lp12', 'bp12', 'bp6', 'hp']:
                if k in r and len(r[k]) > 1000: return r[k][:N]
        return first_array(r)[:N]
    ok += attempt('buchla_291_filter', r_291)

    def r_vcfq():
        from models.spice.serge_vcfq import simulate as f
        audio = melodic_saw()
        r = f(audio,
              cutoff_cv=tri_sweep(RATES[0], 2.0, 7.0),
              q_cv=np.full(N, 8.0),
              voct=melodic_voct() * 5.0,
              trigger_cv=gate_pattern(duty=0.2),
              range_mode='hi')
        return first_array(r)[:N] if r is not None else None
    ok += attempt('serge_vcfq', r_vcfq)

    # === EFFECTS ===

    def r_277():
        # 277 ngspice times out; render shorter (4.25s = half of phrase) then loop
        from models.spice.buchla_277_delay import simulate as f
        audio = melodic_saw(dur_s=4.25)
        n_half = int(4.25 * SR)
        r = f(audio, delay_time_cv=tri_sweep(RATES[0], 2.0, 8.0, length=n_half))
        out = first_array(r)
        if out is None: return None
        out = out[:n_half]
        return np.tile(out, 2)[:N]   # loop to fill full duration
    ok += attempt('buchla_277_delay', r_277)

    # === LPG (melodic saw + per-note vactrol gate) ===

    def r_292_lpg():
        from models.spice.buchla_292_lpg import simulate as f
        audio = melodic_saw()
        r = f(audio_in=audio, cv_in=gate_pattern(duty=0.3), mode='lp')
        return first_array(r)[:N]
    ok += attempt('buchla_292_lpg', r_292_lpg)

    # === ENVELOPE × melodic saw (DUSG is envelope, drive a VCA externally) ===

    def r_dusg():
        from models.spice.serge_dusg import simulate as f
        r = f(trigger=gate_pattern(duty=0.3),
              rise_cv=tri_sweep(RATES[0], 1.0, 4.0),
              fall_cv=tri_sweep(RATES[1], 2.0, 5.0),
              voct=melodic_voct() * 5.0,
              signal_in=melodic_saw(),
              duration_s=DUR, sample_rate=SR)
        return first_array(r)[:N]
    ok += attempt('serge_dusg', r_dusg)

    # === Wave multiplier (melodic sine through wave folder) ===

    def r_wavemult():
        from models.spice.serge_wave_multiplier import simulate as f
        r = f(audio_voltage=melodic_sine(),
              fold_cv=tri_sweep(RATES[0], 1.0, 9.0),
              duration_s=DUR, sample_rate=SR, use_spice=False)
        return first_array(r)[:N]
    ok += attempt('serge_wave_multiplier', r_wavemult)

    print(f"\n=== Done: {ok} ok, {9-ok} failed in {time.time()-t0:.1f}s ===")
    print(f"Output: {OUT_DIR}")


if __name__ == '__main__':
    main()

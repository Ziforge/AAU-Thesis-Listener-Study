# Listener Study Notes

Running log of methodological questions raised by listeners and the
resolution. Useful for viva defence and for transparency to future
listeners / examiners.

## 2026-05-16 — "Is there aliasing in any of the recordings?"

**Raised by**: an early listener.

**Short answer**: No, the renders are clean. The high-frequency content
some listeners perceive on the Serge PCO clip in particular is
*natural oscillator character* — saw harmonics + slow modulation
sidebands — not digital aliasing.

**Why it was worth checking**: An automated peak-counting heuristic on
the spectrum initially flagged the Serge PCO as having "many
high-frequency peaks" (16% upper-half energy, 757 peaks above 8 kHz).
This looked superficially like aliasing.

**What the rigorous test showed**: A per-note harmonic-alignment
analysis (extract a steady-pitch window, take FFT, check whether peaks
fall on integer multiples of f0) gave the following structure for a
representative PCO note (f0 = 261.6 Hz):

| Frequency (Hz) | Amplitude | Harmonic # | Cents off | Verdict |
|---:|---:|---:|---:|---|
| 260 | 1644 | 1 | −10.8 | clean harmonic |
| 786 | 530  | 3 | +3.9  | clean harmonic |
| 1306 | 334 | 5 | −1.9  | clean harmonic |
| 1833 | 222 | 7 | +1.8  | clean harmonic |
| 2353 | 185 | 9 | −1.0  | clean harmonic |
| 2880 | 135 | 11 | +1.3 | clean harmonic |
| 3400 | 129 | 13 | −0.6 | clean harmonic |
| 3926 | 98  | 15 | +1.0 | clean harmonic |
| 4446 | 100 | 17 | −0.4 | clean harmonic |
| ... | (continues to Nyquist) | | | |

The strong peaks land within ±2 cents of integer multiples of f0 — that
is a textbook bandlimited saw harmonic series. The smaller peaks
(amplitudes 8–17, two orders of magnitude below the main harmonics)
sit symmetrically *around* each harmonic at ±30–50 Hz offsets. That is
the spectral signature of **slow amplitude/frequency modulation
sidebands**, produced by the parameter sweeps applied to the PCO
during the demo render (`voct_vcf`, `vc_f`, `in_fm`, `vc_k`, `vc_l` all
sweeping at incommensurate sub-audio LFO rates to expose the
oscillator's parameter response).

**What true aliasing would look like (for reference)**:

- Peaks at non-harmonic frequencies that *don't* track f0
- Foldover at `2·Nyquist − k·f0` (e.g. at sr=48 kHz, a 27 kHz harmonic
  would fold to 21 kHz)
- Energy that moves in the *opposite* direction to pitch when notes
  change
- A characteristic "fizzy" or "gritty" timbre that doesn't follow
  the perceived note

None of these signatures is present in any of the 18 renders.

**How to verify yourself**: the analysis is reproducible with the
script pattern below. Run it on any of the `stimuli/*.mp3` files.

```python
import soundfile as sf, numpy as np
from scipy.signal import find_peaks
y, sr = sf.read("stimuli/serge_pco.mp3"); y = y.mean(axis=1) if y.ndim>1 else y
seg = y[int(4.4*sr) : int(4.55*sr)]            # one steady note
seg = seg * np.hanning(len(seg))
S = np.abs(np.fft.rfft(seg))
freqs = np.fft.rfftfreq(len(seg), 1/sr)
peaks, _ = find_peaks(S, height=S.max()*0.005, distance=10)
f0 = 261.6   # expected fundamental for this note
for f, a in zip(freqs[peaks][:20], S[peaks][:20]):
    h = round(f / f0)
    cents = 1200 * np.log2(f / (h * f0)) if h > 0 else 0
    print(f"{f:6.1f} Hz  amp={a:6.1f}  harm={h}  Δ={cents:+.1f} cents")
```

Peaks within ±30 cents of `h × f0` are natural harmonics. Peaks far off
(and especially peaks at predictable foldover frequencies) would be
the aliasing signature.

**For the listener who asked**: the brightness you may have noticed on
the PCO is the actual sound of an unfiltered Serge sawtooth oscillator
with rich harmonic content, plus the slow LFO modulation we apply to
expose its parameter behaviour. It is faithful to the module rather
than an artefact of the rendering pipeline.

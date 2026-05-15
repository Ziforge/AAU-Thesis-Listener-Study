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

---

## 2026-05-16 — "I think there's aliasing at ~6 s and ~14 s on recording 1"

**Raised by**: a listener who supplied a spectrum-analyser screenshot
showing a tuner reading **G4 (391.97 Hz), 0 cents off, −14 dB / −13.9
LUFS**, with the spectrum collapsing from rich harmonic content into a
single horizontal line as their flagged moment approached.

**Short answer**: That's not aliasing — it's **filter
self-oscillation**, an authentic analog behaviour of the high-Q
filters (Serge VCFQ, Buchla 291, Soundfreak filter) when the cutoff
sweep + Q combination drives the filter into ringing. The screenshot
is, ironically, the evidence that it isn't aliasing.

**How to read their screenshot**:

- The colourful spectrogram on the left = rich harmonic content (saw
  through the filter at moderate Q).
- The transition where the spectrum collapses to a single horizontal
  line = Q rising sharply, the filter beginning to ring at a single
  frequency.
- The clean steady waveform on the right + the tuner reading G4 / 0
  cents = the filter has fully self-oscillated and is now emitting a
  pure sine wave at 391.97 Hz. That is a *musical* pitch (G4), not a
  foldover frequency.

**Why digital aliasing would look different**:

| Signature | Filter self-oscillation (what their screenshot shows) | Digital aliasing |
|---|---|---|
| Spectrum at the flagged moment | One clean line at a musical pitch | Foldback components mirrored around Nyquist |
| Tuner reading | A specific musical note (G4, 0 cents) | An inharmonic frequency that doesn't track f0 |
| Spectral texture | A single horizontal line | A "fizzy" mesh that doesn't follow the note |
| When pitch changes | The single-line frequency moves smoothly with the cutoff CV | Components move in opposite directions to pitch |
| Audible character | A clean, pitched ringing — the "screaming filter" sound the modules are famous for | A gritty / sandy / metallic texture that doesn't sound musical |

**Which renders this can appear on**: Any of the high-Q filters during
their cutoff sweep — at 30 s render duration with my sweep rates, the
self-oscillation peaks land at roughly t ≈ 6 s and t ≈ 14 s on
recordings that include the Serge VCFQ, Buchla 291, Soundfreak filter,
or Buchla 292 vintage. The signature is `pure sine wave at a specific
musical pitch` followed (or preceded) by `wider harmonic content`. If
the tuner can name it as a single musical note, it's the filter
behaving as it was designed to.

**Thesis-side relevance** (the Stradivarius parallel in action): even
this listener, who used professional spectrum-analyser and tuner tools
to investigate their suspicion, misidentified analog filter
self-oscillation as digital aliasing. Without design-context
familiarity with the canonical Serge / Buchla resonance behaviour,
even the correct audio measurements look ambiguous. This is exactly
the prediction of the methodology pivot: brand-character requires
design-context familiarity to interpret correctly, and audio
measurements alone — even with proper instrumentation — are not
sufficient to recover the cultural-acoustic category. The
mis-classification itself is data, not noise.

---

## 2026-05-16 — Vicariously-transmitted expertise (listener self-report)

**Raised by**: the same listener who supplied the spectrum-analyser
screenshot, in a follow-up — they added that their knowledge of
Serge/Buchla concepts comes from other people (records, demos, forum
descriptions, peer conversations), not from direct first-person
experience with the modules.

**Why this is a methodologically important data point**: it makes
explicit a structural feature of the modular-synth community that the
methodology pivot of the thesis implicitly relies on. Most "informed
listeners", even highly engaged ones with professional audio tools,
carry **vicariously-transmitted knowledge** of brand-character rather
than first-person calibration against specific units.

**The expertise hierarchy this exposes**:

| Tier | Knowledge source | Approximate population |
|---|---|---|
| Design authority | First-person hands-on design / build experience over decades | ~15 globally per module family |
| Owner-practitioner | Direct experience with one or a few specific units they own | Low hundreds globally per module |
| Vicarious informed listener | Records, YouTube demos, magazine articles, forum descriptions, peer conversations | Tens of thousands globally |
| Novice | No prior exposure | The general public |

**Implications for the listener study and the methodology pivot**:

1. Even a panel of modular-synth practitioners (e.g.\ recruited via
   r/modular, Lines, Discord) is sampling primarily from the
   "vicarious informed listener" tier, not the design-authority tier.
2. The cultural knowledge of "what a Buchla sounds like" that such a
   panel carries was constructed from records, demos, and performances
   — all of which already filter through specific captured units that
   the listener never had direct acoustic calibration on. The brand-
   recognition reference is itself a peer-distance measurement, not
   ground truth.
3. This is the Stradivarius case **taken one tier further**: Fritz
   \emph{et al.}'s soloists had real first-person exposure to Stradivari
   instruments and still couldn't discriminate. Most modular-synth
   listeners have less than that — they have never held the specific
   module they are being asked to identify.
4. The Superbooth interviews are therefore not a "weaker substitute"
   for a hypothetical listener panel — they are evidence from a
   structurally different (higher) tier of the expertise hierarchy
   than any feasible listener panel could ever populate.

**For the thesis discussion**: this is an unsolicited in-the-wild
articulation, by an informed listener with audio tools, of exactly
the epistemic structure the methodology pivot rests on. It should
appear in the discussion chapter when defending the four-chain
convergence argument.

**Additional observation — measurement tools do not bridge the
interpretation gap**: the same listener also volunteered that they were
using an analysis tool (spectrum analyser + tuner + LUFS meter,
visible in the screenshot) to investigate the audio rather than
relying on naked-ear judgement alone. They cross-checked their
auditory percept with visual measurement — the responsible thing to
do — and still arrived at the wrong interpretation. The tools
correctly reported the underlying *accuracy-side* signal (a clean
sine at 391.97 Hz, G4, 0 cents off, −14 dB) but the
*cultural-side* interpretation (``this is the canonical Serge VCFQ
self-oscillation behaviour, the module doing what it is designed to
do'') was not recoverable from the measurement alone. Without
design-context familiarity with what high-Q Serge / Buchla filters
sound and look like when they ring, even a correct
spectrum-analyser reading remains ambiguous. This separates the
two-evidence framing of \S\ref{sec:perceptual}:

\begin{itemize}\itemsep0pt
  \item The \textbf{accuracy question} (``what does the signal contain,
    quantitatively'') is answerable by tools alone.
  \item The \textbf{cultural question} (``what does this signal mean
    --- is it the module behaving authentically or a digital
    artefact?'') is not. It requires either first-person experience
    with the canonical hardware behaviour, or expert testimony from
    someone who has it.
\end{itemize}

The thesis's four-chain convergence is therefore not redundant: the
metric chain (J = 1.33, peer-distance, silhouettes) answers the
accuracy question; the expert-testimony chain (Superbooth interviews
\cite{verbos2026superbooth, buchla2026superbooth}) answers the
cultural question; the listener-study chain measures the limit of
vicarious-expertise listeners attempting to bridge the two without
design-context. All three are needed.

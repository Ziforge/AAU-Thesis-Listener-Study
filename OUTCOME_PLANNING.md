# Listener Study Outcome Planning

Pre-data evaluation of likely results and their thesis interpretations.
Written before data collection so we have a prepared response for each
plausible outcome shape.

---

## Two hypotheses being tested

| H | Statement | Threshold of support |
|---|---|---|
| **H1** | Listeners identify some system above chance | At least one system >25% accuracy with binomial p<0.05 |
| **H2** | Per-system ordering matches Test 4 silhouettes | Soundfreak > Serge > Buchla 200 descriptively |

(A peer-distance H3 was considered and dropped — the capture-vs-VA distance is already measured by the J=1.33 vs family-floor metric chain; a redundant listener-side A/B of calibration sweeps would have added listening fatigue without measurement-chain-independent information.)

## Probability-weighted outcome scenarios

### Scenario A: "Best case" (15-20% likely)
**H1 ✓, H2 ✓ — both hypotheses confirmed**
- Soundfreak ~60-70% accuracy, Serge ~40-50%, Buchla ~30-40%
- Ordering Soundfreak > Serge > Buchla matches Test 4

**Thesis writeup angle:**
> "Strong listener-side validation of the methodology pivot. The per-system identification accuracy follows the same ordering as the silhouette analysis of Test 4, providing convergent evidence from four mechanically independent measurement chains (ESR, hand-crafted Mahalanobis, CLAP, informed-listener identification)."

### Scenario B: "Good but mixed" (35-40% likely — MOST LIKELY)
**H1 partial, H2 partial**
- Soundfreak ~50-60% above chance, Serge and Buchla near chance or just above
- Partial ordering: Soundfreak clearly highest, Serge/Buchla similar

**Thesis writeup angle:**
> "The strongest-clustering system (Soundfreak, +0.79 silhouette in Test 4) is reliably identifiable from VA renders; the heterogeneous Buchla 200 system (-0.04 silhouette by design) approaches chance, consistent with the design-philosophy interview record (Verbos, Buchla USA) that the Buchla 200 was designed as a collection of distinct sonic objects rather than a unified palette. This per-system pattern at the listener level replicates the per-system pattern at the feature-space silhouette level, providing convergent evidence for the system-character argument."

### Scenario C: "Honest mixed" (25-30% likely)
**H1 supported only for Soundfreak, H2 partial**
- Soundfreak ~50%+ above chance, Serge ~30% (just above), Buchla ~25% (chance)
- Ordering matches partially

**Thesis writeup angle:**
> "Listeners reliably identify the tightest-clustering system (Soundfreak) above chance; for the more heterogeneous systems (Buchla 200 in particular), identification approaches chance, which is consistent with the system-internal heterogeneity finding of Test 4 and the design-philosophy interview record. The descriptive-pilot scale of the study (N=10-15) limits inferential power; the qualitative pattern observed matches the methodology pivot's prediction."

### Scenario D: "Disappointing" (15-20% likely)
**H1 not supported, listeners near chance for everything**
- All systems ~25-35% accuracy
- No clear per-system ordering

**Thesis writeup angle:**
> "Listener identification of modular synthesiser families from VA-rendered musical demos does not exceed chance baseline in this pilot study. Two interpretations: (a) the recruited population, while modular-synth-engaged, may not have the specific brand-recognition expertise required for system identification from short audio clips; or (b) the VA-rendered demos express more general 'vintage modular' character than system-specific signatures. The result is informative in either case: it underscores the methodology pivot's argument that brand-recognition listener panels are not the appropriate evaluation method for this corpus. The metric-side evidence (\\S\\ref{sec:perceptual_empirical}, \\S\\ref{sec:system_signatures}) remains unaffected; this study adds an honest descriptive listener-side data point rather than a contradictory finding."

## Honest interpretation framework

**The thesis's load-bearing claims don't depend on the listener study.** The listener study is a supplementary fourth measurement chain that:
- If it confirms the metric-side picture → strengthens the thesis
- If it produces a mixed picture → still informative, matches Test 4 predictions
- If it doesn't confirm → adds honest disclosed limitation, but doesn't refute the metric-side evidence

## Key defensive lines (prepared in advance)

| Anticipated examiner question | Prepared response |
|---|---|
| "Your sample size is too small to draw conclusions" | Pre-registered as a descriptive pilot; load-bearing claims rest on the metric-side measurement chains (3 already validated) |
| "Why didn't you run MUSHRA?" | Four-layer impossibility argument (\\S6.5 methodology pivot) explains why MUSHRA isn't appropriate for this corpus |
| "Your listeners aren't representative of the design-authority expert population" | Correct — they're informed listeners (modular synth practitioners). Design-authority experts were elicited via the Superbooth interviews (Verbos, Buchla USA). The two evidence types are complementary, not substitutable. |
| "What if listeners can't identify Buchla?" | This is consistent with the system-internal heterogeneity finding of Test 4 (silhouette -0.04) and matches the design-philosophy interview record (Buchla 200 as a collection of distinct objects). Scenario B/C is the most likely outcome. |
| "Why no capture-vs-VA listener A/B?" | That distance is already measured by the J=1.33 vs family-floor metric chain (\\S6.5). A listener-side A/B of calibration sweeps is fatiguing and adds no measurement-chain-independent information. |

## Probability-weighted expected outcome

Combined probability: about **60-70% chance** of landing in Scenarios B or C — honest mixed results that match Test 4's per-system pattern. The thesis writeup is prepared for any of A through D with a defensible interpretation in each.

## What to do post-data

1. **Run analyze.py** on the CSVs
2. **Determine which scenario** the data lands in
3. **Use the prepared writeup angle** as the starting draft for §6.5.X "Informed-Listener Identification Study (Results)"
4. **Add the limitations** that are scenario-specific
5. **Recompile** thesis

## Bottom line

This planning means **no result is a surprise we're unprepared for**. Every plausible outcome has a prepared thesis interpretation that maintains the load-bearing claims while reporting the listener study honestly.

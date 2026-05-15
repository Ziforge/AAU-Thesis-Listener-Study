# Listener Study (v2: brand-identification) — Saturday Deployment Checklist

A web-based brand-identification study for the AAU SMC MSc thesis.
Web-deployable, QR-shareable, anonymous, ~7 minutes per participant.

**Task:** Each participant hears 14 short musical clips (12s each), one at a time, and identifies which family of vintage modular synthesisers the clip most sounds like (Buchla 200 / Serge / EMS-VCS3 / Soundfreak), plus a confidence rating.

**Why this design:** Validates the methodology pivot's family-membership claim directly at the listener level. Connects to the system-clustering analysis (§6.5 Test 4): listener identification accuracy should follow the same per-system pattern as the silhouette analysis — Soundfreak easiest, Buchla heterogeneous-by-design hardest.

## Local build (do this first, ~10 min)

```sh
cd /Volumes/MAC_M3_Store/Projects/listener_study_2026
chmod +x build_assets.sh
./build_assets.sh
```

This generates:
- `stimuli/*.wav` — 16 audio clips (8 capture + 8 VA pairs) at 44.1 kHz, RMS-normalised, 5 s each
- `stimuli/*.mp3` — same clips as 128 kbps MP3 (smaller, faster web delivery)
- `stimuli/warmup.wav` — a 4-second pitch-sweep tone for participant volume calibration
- `trial_list.json` — 30 randomised trial pairs (capture-vs-VA + cross-module-controls)

Open `index.html` in your browser locally to verify the survey works end-to-end.
You can click through trials but submission won't yet work (needs the endpoint configured).

## Step 1: Set up Google Apps Script endpoint (5-10 min)

1. Open https://script.google.com → "New Project"
2. Delete the default `function myFunction()`
3. Open `apps_script.gs` from this directory and paste the contents in
4. File menu → "Project Properties" → set Time Zone (e.g. Europe/Copenhagen)
5. Click "Deploy" (top-right) → "New deployment"
   - Type: "Web app"
   - Description: "Listener Study v1.0"
   - Execute as: **Me (your Google account)**
   - Who has access: **Anyone**
6. Click "Deploy" → grant permissions when prompted
7. Copy the deployment URL (looks like `https://script.google.com/macros/s/.../exec`)

## Step 2: Configure the survey

Open `assets/survey.js` and replace:
```js
const APPS_SCRIPT_URL = "REPLACE_WITH_YOUR_GOOGLE_APPS_SCRIPT_URL";
```
with the URL from step 1.

## Step 3: Deploy the static site (5 min)

Pick one option:

### Option A: Netlify Drop (easiest, no account needed)
1. Open https://app.netlify.com/drop
2. Drag the entire `listener_study_2026` folder into the page
3. Netlify gives you a public URL (e.g. `https://abc123.netlify.app`)
4. Done. Copy that URL.

### Option B: GitHub Pages
1. `git init && git add . && git commit -m "Listener study"` in this directory
2. Push to a GitHub repo
3. In repo Settings → Pages → enable GitHub Pages on the main branch
4. URL: `https://<your-username>.github.io/<repo-name>/`

### Option C: Vercel / Cloudflare Pages
- Same idea as Netlify — drag-and-drop deploy

## Step 4: Generate QR code

```sh
# macOS — uses qrencode (install via brew install qrencode)
echo "https://YOUR_NETLIFY_URL_HERE" | qrencode -o qr.png -s 12
```

Or use any free online QR generator (e.g. https://www.qr-code-generator.com).

Print/share the QR code for in-person recruitment (Superbooth-equivalent venues, modular meetups, university listening sessions, etc.).

For online recruitment, just share the URL directly:
- r/modular Reddit
- Lines forum (https://llllllll.co)
- Eurorack Modules Facebook group
- Discord servers (Vintage Synth Explorer, Mutable Instruments, Make Noise)
- Twitter/X to your network
- WhatsApp / Telegram modular synth groups

Suggested message:
> "I'm running a quick (~8 min) anonymous listener study for my MSc thesis on virtual analog modelling of vintage Buchla 200, Serge, and EMS-derived hardware. Compare ~30 short audio clips and rate similarity. Headphones recommended. Help shape the future of analog modelling research! [URL]"

## Step 5: Monitor responses

Open the Google Sheet "Listener Study Responses 2026" in your Drive (auto-created on first response). Two tabs:
- `participants` — one row per participant with metadata
- `responses` — one row per individual rating

Watch the response count climb in real time.

## Step 6: Analyse (when N ≥ 20-50)

```sh
# Open the Google Sheet → File → Download → CSV (do this for both tabs)
# Save as analysis/responses.csv and analysis/participants.csv
cd analysis
/Volumes/MAC_M3_Store/Dev_Tools/miniforge3/bin/python analyze.py
```

Outputs:
- `summary.json` — numbers ready to drop into the thesis
- `rating_distributions.pdf` — figure for the thesis
- Inter-rater agreement (Krippendorff α), per-module mean ratings, sanity-check controls

## Expected results to validate

For the study to "work" (no implementation bugs), you should see:
- `cap_vs_cap_diff` (cross-module captures) → mean rating ≤ 3 (raters distinguish different sounds)
- `cap_vs_va` (same-module capture vs VA) → mean rating ≥ 4 (raters recognise the VA as related to the capture)
- Krippendorff α > 0.4 (raters somewhat agree)

The interesting science:
- Per-module cap-vs-VA ratings: which modules are perceived as "more similar to capture"
- Compare against the existing per-module $\mathcal{J}$ table — do listener perceptions align with the J score?
- Distribution shape: is there a clear difference between "VA looks like capture" (rating > 4) and "cross-module captures" (rating < 3)?

## Time budget

- Local build: 10 min
- Apps Script deploy: 10 min
- Survey deploy + QR: 5 min
- Recruitment / sharing: 30 min
- Wait for responses: 1-3 days
- Analysis: 30 min once CSV downloaded
- Thesis writeup integration: 1 hour

Total active time: ~2 hours. Total wall time including data collection: 2-4 days.

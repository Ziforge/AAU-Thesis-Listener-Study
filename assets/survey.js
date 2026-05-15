// Vintage modular synth listener study — TWO-STAGE button trial flow (v3.1).
// Stage 1: pick system (Buchla / Serge / EMS / Soundfreak / Modern / Unknown).
// Stage 2: if it's a system pick (not Modern / Unknown), pick the specific
//          module from that system's catalogue. Else auto-advance.
// On any module-pick, all buttons grey out, response is recorded, auto-advance
// to the next trial after a short delay. This gives us TWO separate accuracy
// signals: system_correct vs module_correct.

// === CONFIG ============================================================
const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw07f_GozLn2FrAMa_Wl8PlFmnKcmoD5pGmpuZ4-XvYZ7VYg8hCLVv9hP0fYKJZHKf0yw/exec";
const STUDY_VERSION = "v3.1_two_stage_buttons_2026-05-15";
const ADVANCE_DELAY_MS = 700;
// =======================================================================

let trials = [];
let stimuli = [];
let systemOptions = {};
let moduleOptions = {};   // {system_key: [[module_id, label], ...]}
let extraOptions = {};
let currentTrial = 0;
let responses = [];
let participantInfo = {};
let trialStartTime = 0;
let stageSystemPick = null;   // system chosen in stage 1 (per-trial)
const startedAt = new Date().toISOString();

const $ = id => document.getElementById(id);
const showScreen = id => {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  $(id).classList.add("active");
};

// === Welcome screen ====================================================
const REQUIRED_FIELDS = ["age_band", "experience", "years_music",
                         "familiarity", "prior_attempt", "headphones"];
function checkStartReady() {
  const allFilled = REQUIRED_FIELDS.every(id => $(id).value);
  const consent = $("consent").checked;
  $("btn-start").disabled = !(allFilled && consent);
}
REQUIRED_FIELDS.forEach(id => $(id).addEventListener("change", checkStartReady));
$("consent").addEventListener("change", checkStartReady);

$("btn-start").addEventListener("click", async () => {
  participantInfo = {
    age_band: $("age_band").value,
    experience: $("experience").value,
    years_music: $("years_music").value,
    familiarity: $("familiarity").value,
    prior_attempt: $("prior_attempt").value,
    listening_device: $("headphones").value,
    country: $("country").value || "",
    consent: true,
    started_at: startedAt,
    study_version: STUDY_VERSION,
  };
  await loadTrials();
  if (trials.length === 0) {
    alert("Failed to load trials. Refresh and try again.");
    return;
  }
  shuffleWithRepeatSeparation();
  currentTrial = 0;
  showScreen("screen-trial");
  renderTrial();
});

function shuffleWithRepeatSeparation(maxAttempts = 50) {
  const MIN_GAP = 3;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    for (let i = trials.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [trials[i], trials[j]] = [trials[j], trials[i]];
    }
    const positions = {};
    let valid = true;
    for (let k = 0; k < trials.length; k++) {
      const sid = trials[k].stimulus_id;
      if (!sid) continue;
      if (positions[sid] !== undefined && k - positions[sid] <= MIN_GAP) {
        valid = false; break;
      }
      positions[sid] = k;
    }
    if (valid) return;
  }
}

async function loadTrials() {
  try {
    const r = await fetch("trial_list.json?v=20260515c");
    const data = await r.json();
    stimuli = data.stimuli;
    trials = data.trials;
    systemOptions = data.system_options || {};
    moduleOptions = data.module_options || {};
    extraOptions = data.extra_options || {};
  } catch (e) {
    console.error("Failed to load trial_list.json", e);
  }
}

// === Trial rendering ===================================================

function renderTrial() {
  const t = trials[currentTrial];
  const pct = (currentTrial / trials.length) * 100;
  $("progress-bar").style.width = pct + "%";
  $("progress-text").textContent = `Trial ${currentTrial + 1} of ${trials.length}`;
  $("audio-stim").src = `stimuli/${t.file}`;
  $("audio-stim").load();
  stageSystemPick = null;
  renderStageOneButtons();
  $("advance-hint").textContent = "Tap which family it sounds like.";
  $("advance-hint").style.visibility = "visible";
  trialStartTime = performance.now();
}

// --- Stage 1: pick the SYSTEM family ---
function renderStageOneButtons() {
  const container = $("choice-buttons");
  container.innerHTML = "";
  const sysKeys = Object.keys(systemOptions);
  // Randomise system order per trial
  for (let i = sysKeys.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [sysKeys[i], sysKeys[j]] = [sysKeys[j], sysKeys[i]];
  }
  const all = [
    ...sysKeys.map(k => [k, systemOptions[k]]),
    ["unknown", extraOptions.unknown],
    ["modern",  extraOptions.modern],
  ];
  all.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "choice-btn";
    btn.dataset.key = key;
    btn.textContent = label;
    btn.addEventListener("click", () => onSystemPick(key, btn));
    container.appendChild(btn);
  });
}

function onSystemPick(systemKey, clickedBtn) {
  stageSystemPick = systemKey;
  // Visual lock on stage 1 buttons, highlight chosen
  document.querySelectorAll(".choice-btn").forEach(b => {
    b.disabled = true;
    if (b === clickedBtn) b.classList.add("selected");
  });
  // If modern or unknown, no sub-type → record + advance directly
  if (systemKey === "modern" || systemKey === "unknown") {
    recordAndAdvance(systemKey, "");
    return;
  }
  // Else show stage 2 (module pick) for that system after short pause
  $("advance-hint").textContent = "Now: which module within that family?";
  setTimeout(() => renderStageTwoButtons(systemKey), 400);
}

// --- Stage 2: pick the specific MODULE within the chosen system ---
function renderStageTwoButtons(systemKey) {
  const container = $("choice-buttons");
  container.innerHTML = "";
  const opts = moduleOptions[systemKey] || [];
  opts.forEach(([modId, label]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "choice-btn";
    btn.dataset.key = modId;
    btn.textContent = label;
    btn.addEventListener("click", () => onModulePick(modId, btn));
    container.appendChild(btn);
  });
}

function onModulePick(moduleKey, clickedBtn) {
  document.querySelectorAll(".choice-btn").forEach(b => {
    b.disabled = true;
    if (b === clickedBtn) b.classList.add("selected");
  });
  recordAndAdvance(stageSystemPick, moduleKey);
}

function recordAndAdvance(systemPick, modulePick) {
  const t = trials[currentTrial];
  // System-correct: special-case placebo_modern (correct if modern/unknown)
  const systemCorrect = (t.true_system === "placebo_modern")
    ? (systemPick === "modern" || systemPick === "unknown")
    : (systemPick === t.true_system);
  const moduleCorrect = (t.true_module && modulePick)
    ? (modulePick === t.true_module)
    : null;   // null if module pick wasn't applicable (placebo, or stage-1 was modern/unknown)
  responses.push({
    trial_idx: currentTrial,
    category: t.category || "main",
    stimulus_id: t.stimulus_id,
    stimulus_label: t.label,
    true_system: t.true_system,
    true_module: t.true_module || "",
    listener_system: systemPick,
    listener_module: modulePick || "",
    system_correct: systemCorrect,
    module_correct: moduleCorrect,
    response_time_ms: Math.round(performance.now() - trialStartTime),
    rated_at: new Date().toISOString(),
  });
  $("advance-hint").style.visibility = "hidden";
  try { $("audio-stim").pause(); } catch (e) {}
  setTimeout(() => {
    currentTrial++;
    if (currentTrial >= trials.length) showScreen("screen-submit");
    else renderTrial();
  }, ADVANCE_DELAY_MS);
}

// === Submit screen =====================================================
$("btn-submit").addEventListener("click", async () => {
  $("btn-submit").disabled = true;
  $("submit-status").textContent = "Submitting...";
  $("submit-status").className = "submit-status";

  const payload = {
    participant: participantInfo,
    comment: $("comment").value.substring(0, 500),
    submitted_at: new Date().toISOString(),
    responses: responses,
  };

  try {
    if (APPS_SCRIPT_URL.startsWith("REPLACE")) {
      throw new Error("Endpoint not configured");
    }
    await fetch(APPS_SCRIPT_URL, {
      method: "POST",
      mode: "no-cors",
      headers: {"Content-Type": "text/plain;charset=utf-8"},
      body: JSON.stringify(payload),
    });
    $("submit-status").textContent = "Done. Thank you!";
    $("submit-status").className = "submit-status ok";
    setTimeout(() => showScreen("screen-done"), 600);
  } catch (e) {
    console.error("Submit failed", e);
    $("submit-status").textContent = "Submit failed: " + e.message + ". Save the JSON below as backup.";
    $("submit-status").className = "submit-status error";
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `listener_response_${Date.now()}.json`;
    a.textContent = "Download response JSON";
    a.style.display = "block";
    a.style.marginTop = "12px";
    $("submit-status").after(a);
    $("btn-submit").disabled = false;
  }
});

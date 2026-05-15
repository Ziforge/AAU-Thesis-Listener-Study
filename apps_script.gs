// Google Apps Script — receives listener-study response payloads and writes
// them to a Google Sheet. To deploy:
//
//   1. Open https://script.google.com → New Project
//   2. Paste this entire file
//   3. File → Project Properties → set TimeZone (e.g. Europe/Copenhagen)
//   4. Click "Deploy" → "New Deployment" → "Web app"
//        - Description: "Listener Study v1.0"
//        - Execute as: Me
//        - Who has access: Anyone
//   5. Copy the deployment URL (looks like https://script.google.com/.../exec)
//   6. Paste that URL into assets/survey.js as APPS_SCRIPT_URL
//
// The first time a response arrives, this script will create a new
// Google Sheet called "Listener Study Responses 2026" in your Drive
// and write rows to it. Each fetch from the survey appends one row per
// trial, plus one row per participant for metadata.

const SHEET_NAME_RESPONSES = "responses";
const SHEET_NAME_PARTICIPANTS = "participants";
const SHEET_TITLE = "Listener Study Responses 2026";

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    const ss = getOrCreateSheet();
    appendParticipant(ss, payload);
    appendResponses(ss, payload);
    refreshNResponses(ss, payload.participant_id);
    return ContentService.createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({error: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  // Wipe endpoint — only triggers with the correct one-time token in URL
  // (protects against accidental wipe from random GETs).
  if (e && e.parameter && e.parameter.wipe === "yes-please-reset-2026-05-15") {
    const ss = getOrCreateSheet();
    ss.getSheetByName(SHEET_NAME_PARTICIPANTS).clear();
    ss.getSheetByName(SHEET_NAME_RESPONSES).clear();
    // Re-write headers (ensureHeaderRow runs on next doPost; here we set them now)
    ss.getSheetByName(SHEET_NAME_PARTICIPANTS).appendRow(PARTICIPANT_HEADERS);
    ss.getSheetByName(SHEET_NAME_RESPONSES).appendRow(RESPONSE_HEADERS);
    return ContentService.createTextOutput("WIPED — sheet reset, headers re-written")
      .setMimeType(ContentService.MimeType.TEXT);
  }
  return ContentService.createTextOutput("OK — listener study endpoint")
    .setMimeType(ContentService.MimeType.TEXT);
}

const PARTICIPANT_HEADERS = ["participant_id", "submitted_at", "started_at",
  "age_band", "experience", "years_music", "familiarity", "prior_attempt",
  "listening_device", "country", "consent", "study_version", "comment",
  "n_responses"];

const RESPONSE_HEADERS = ["participant_id", "trial_idx", "category",
  "stimulus_id", "stimulus_label", "true_system", "true_module",
  "listener_system", "listener_module", "system_correct", "module_correct",
  "response_time_ms", "rated_at"];

function ensureHeaderRow(sheet, expected) {
  const lastCol = sheet.getLastColumn();
  if (lastCol < expected.length) {
    sheet.clear();
    sheet.appendRow(expected);
    return;
  }
  const first = sheet.getRange(1, 1, 1, expected.length).getValues()[0];
  for (let i = 0; i < expected.length; ++i) {
    if (first[i] !== expected[i]) {
      // Schema drift detected — clear sheet and rewrite header.
      sheet.clear();
      sheet.appendRow(expected);
      return;
    }
  }
}

function getOrCreateSheet() {
  const files = DriveApp.getFilesByName(SHEET_TITLE);
  let ss;
  if (files.hasNext()) {
    ss = SpreadsheetApp.open(files.next());
    // Ensure both tabs exist; create missing
    if (!ss.getSheetByName(SHEET_NAME_PARTICIPANTS)) ss.insertSheet(SHEET_NAME_PARTICIPANTS);
    if (!ss.getSheetByName(SHEET_NAME_RESPONSES))   ss.insertSheet(SHEET_NAME_RESPONSES);
  } else {
    ss = SpreadsheetApp.create(SHEET_TITLE);
    ss.getSheets()[0].setName(SHEET_NAME_PARTICIPANTS);
    ss.insertSheet(SHEET_NAME_RESPONSES);
  }
  // Always validate + repair headers on every fetch — self-healing across
  // schema changes between deployments.
  ensureHeaderRow(ss.getSheetByName(SHEET_NAME_PARTICIPANTS), PARTICIPANT_HEADERS);
  ensureHeaderRow(ss.getSheetByName(SHEET_NAME_RESPONSES),    RESPONSE_HEADERS);
  return ss;
}

// Upsert participant row. Client provides participant_id (UUID generated at
// session start), so incremental POSTs all share the same id. We update the
// existing row (n_responses, submitted_at, comment) or insert a new row.
// Falls back to server-side UUID if client didn't provide one (old clients).
function appendParticipant(ss, p) {
  const sheet = ss.getSheetByName(SHEET_NAME_PARTICIPANTS);
  let pid = (p.participant && p.participant.participant_id) || "";
  if (!pid) {
    pid = Utilities.getUuid();
    if (p.participant) p.participant.participant_id = pid;
  }
  p.participant_id = pid;   // store on payload for appendResponses

  // Search column A for existing pid
  const lastRow = sheet.getLastRow();
  let existingRow = -1;
  if (lastRow > 1) {
    const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
    for (let i = 0; i < ids.length; i++) {
      if (ids[i][0] === pid) { existingRow = i + 2; break; }
    }
  }

  const rowValues = [
    pid,
    p.submitted_at || "",
    p.participant.started_at || "",
    p.participant.age_band || "",
    p.participant.experience || "",
    p.participant.years_music || "",
    p.participant.familiarity || "",
    p.participant.prior_attempt || "",
    p.participant.listening_device || "",
    p.participant.country || "",
    p.participant.consent ? "yes" : "no",
    p.participant.study_version || "",
    p.comment || "",
    0,   // n_responses placeholder; updated below after appendResponses
  ];

  if (existingRow > 0) {
    // Preserve existing n_responses, will be recomputed after appendResponses
    const existing = sheet.getRange(existingRow, 1, 1, PARTICIPANT_HEADERS.length).getValues()[0];
    rowValues[12] = p.comment || existing[12] || "";    // keep last non-empty comment
    sheet.getRange(existingRow, 1, 1, PARTICIPANT_HEADERS.length).setValues([rowValues]);
  } else {
    sheet.appendRow(rowValues);
  }
}

// Recompute n_responses for this participant by counting rows in responses tab
function refreshNResponses(ss, pid) {
  const partSheet = ss.getSheetByName(SHEET_NAME_PARTICIPANTS);
  const respSheet = ss.getSheetByName(SHEET_NAME_RESPONSES);
  const lastResp = respSheet.getLastRow();
  let count = 0;
  if (lastResp > 1) {
    const ids = respSheet.getRange(2, 1, lastResp - 1, 1).getValues();
    for (let i = 0; i < ids.length; i++) if (ids[i][0] === pid) count++;
  }
  const lastPart = partSheet.getLastRow();
  if (lastPart > 1) {
    const partIds = partSheet.getRange(2, 1, lastPart - 1, 1).getValues();
    for (let i = 0; i < partIds.length; i++) {
      if (partIds[i][0] === pid) {
        partSheet.getRange(i + 2, PARTICIPANT_HEADERS.length).setValue(count);
        return;
      }
    }
  }
}

// Append response rows. Dedupes within the sheet: if a (pid, trial_idx) row
// already exists (e.g., listener went back / retry), overwrite it. Otherwise
// append. This makes the per-trial incremental POSTs idempotent.
function appendResponses(ss, p) {
  const sheet = ss.getSheetByName(SHEET_NAME_RESPONSES);
  const pid = p.participant_id;
  const lastRow = sheet.getLastRow();
  // Build (pid, trial_idx) → rowIdx index for fast dedupe lookup
  const existingIdx = {};
  if (lastRow > 1) {
    const data = sheet.getRange(2, 1, lastRow - 1, 2).getValues();
    for (let i = 0; i < data.length; i++) {
      if (data[i][0] === pid) existingIdx[data[i][1]] = i + 2;
    }
  }
  const toAppend = [];
  (p.responses || []).forEach(r => {
    const row = [
      pid, r.trial_idx, r.category || "main",
      r.stimulus_id || "", r.stimulus_label || "",
      r.true_system || "", r.true_module || "",
      r.listener_system || "", r.listener_module || "",
      r.system_correct === undefined ? "" : r.system_correct,
      r.module_correct === undefined || r.module_correct === null ? "" : r.module_correct,
      r.response_time_ms || "", r.rated_at || "",
    ];
    if (existingIdx[r.trial_idx] !== undefined) {
      sheet.getRange(existingIdx[r.trial_idx], 1, 1, row.length).setValues([row]);
    } else {
      toAppend.push(row);
    }
  });
  if (toAppend.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, toAppend.length, toAppend[0].length).setValues(toAppend);
  }
}

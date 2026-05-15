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
    return ContentService.createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({error: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  // Health check
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

function appendParticipant(ss, p) {
  const sheet = ss.getSheetByName(SHEET_NAME_PARTICIPANTS);
  const pid = Utilities.getUuid();
  p.participant_id = pid;
  sheet.appendRow([
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
    (p.responses || []).length,
  ]);
}

function appendResponses(ss, p) {
  const sheet = ss.getSheetByName(SHEET_NAME_RESPONSES);
  const pid = p.participant_id;
  const rows = (p.responses || []).map(r => [
    pid, r.trial_idx, r.category || "main",
    r.stimulus_id || "", r.stimulus_label || "",
    r.true_system || "", r.true_module || "",
    r.listener_system || "", r.listener_module || "",
    r.system_correct === undefined ? "" : r.system_correct,
    r.module_correct === undefined || r.module_correct === null ? "" : r.module_correct,
    r.response_time_ms || "", r.rated_at || "",
  ]);
  if (rows.length > 0) sheet.getRange(sheet.getLastRow()+1, 1, rows.length, rows[0].length).setValues(rows);
}

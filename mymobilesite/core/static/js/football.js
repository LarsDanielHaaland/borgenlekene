document.addEventListener('DOMContentLoaded', function() {
  const eventDiv = document.getElementById('football-data');
  if (!eventDiv) return;
  const eventId = eventDiv.getAttribute('data-event-id');
  const activityId = parseInt(eventDiv.getAttribute('data-activity-id'), 10);

  // Helper to read saved rankings from the hidden inputs (they use json_script)
  function readSaved(id) {
    const el = document.getElementById(id);
    if (!el) return [];
    try {
      // json_script outputs a <script> tag with JSON in textContent
      return JSON.parse(el.textContent || el.innerText || '[]');
    } catch (e) {
      return [];
    }
  }

  const savedRound1 = readSaved('round1-data');
  const savedRound2 = readSaved('round2-data');
  const savedRound3 = readSaved('round3-data');
  const savedFinal = readSaved('final-data');

  // keep the latest computed points map so controls can reference it
  let currentPointsMap = null;

  // Setup tables
  const round1Table = document.getElementById('round1-table');
  const round2Table = document.getElementById('round2-table');
  const round3Table = document.getElementById('round3-table');
  const finalTable = document.getElementById('final-standing');

  // attach generic move controls for rounds using shared helper
  [round1Table, round2Table, round3Table].forEach(t => attachMoveControls(t, () => updateRoundScores(t)));

  // Final controls and visibility will be handled by shared helpers

  // Pre-fill saved orders using shared helper
  applySavedOrder(round1Table, savedRound1);
  applySavedOrder(round2Table, savedRound2);
  applySavedOrder(round3Table, savedRound3);
  applySavedOrder(finalTable, savedFinal);

  // Update round scores visuals after applying saved orders
  [round1Table, round2Table, round3Table].forEach(t => updateRoundScores(t));
  // Compute and populate final totals using shared compute and attach final controls
  currentPointsMap = computeFinalOrderShared([round1Table, round2Table, round3Table], finalTable);
  attachFinalControlsShared(finalTable, currentPointsMap);

  // No elimination UI: rounds are reordered manually with arrows only.

  // computeFinalOrderShared is used for computing and ordering final table

  document.getElementById('compute-final').addEventListener('click', (e) => {
    currentPointsMap = computeFinalOrderShared([round1Table, round2Table, round3Table], finalTable);
    attachFinalControlsShared(finalTable, currentPointsMap);
  });

  // Save handlers: use shared saveManualOrder and showNotification
  document.getElementById('save-round-1').addEventListener('click', () => {
    saveManualOrder(activityId, round1Table, 1).then(data => { if(data.success) showNotification('Saved', 'success'); else showNotification('Save failed: ' + (data.error||JSON.stringify(data)), 'error'); }).catch(e => showNotification('Network error: ' + e, 'error'));
  });

  document.getElementById('save-round-2').addEventListener('click', () => {
    saveManualOrder(activityId, round2Table, 2).then(data => { if(data.success) showNotification('Saved', 'success'); else showNotification('Save failed: ' + (data.error||JSON.stringify(data)), 'error'); }).catch(e => showNotification('Network error: ' + e, 'error'));
  });

  document.getElementById('save-round-3').addEventListener('click', () => {
    saveManualOrder(activityId, round3Table, 3).then(data => { if(data.success) showNotification('Saved', 'success'); else showNotification('Save failed: ' + (data.error||JSON.stringify(data)), 'error'); }).catch(e => showNotification('Network error: ' + e, 'error'));
  });

  document.getElementById('save-final').addEventListener('click', () => {
    saveManualOrder(activityId, finalTable, null).then(data => { if(data.success) showNotification('Saved', 'success'); else showNotification('Save failed: ' + (data.error||JSON.stringify(data)), 'error'); }).catch(e => showNotification('Network error: ' + e, 'error'));
  });

});

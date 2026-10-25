document.addEventListener('DOMContentLoaded', function() {
  const tournamentData = document.getElementById('tournament-data');
  if (!tournamentData) return;
  const activityId = parseInt(tournamentData.getAttribute('data-activity-id'), 10);

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

  // Pre-fill saved orders using shared helper
  applySavedOrder(round1Table, savedRound1);
  applySavedOrder(round2Table, savedRound2);
  applySavedOrder(round3Table, savedRound3);
  applySavedOrder(finalTable, savedFinal);

  // Update round scores visuals after applying saved orders
  [round1Table, round2Table, round3Table].forEach(t => updateRoundScores(t));
  // Compute and populate final totals using shared compute and attach final controls
  currentPointsMap = computeFinalOrderShared([round1Table, round2Table, round3Table], finalTable);
  const roundTables = [round1Table, round2Table, round3Table];
  roundTables.forEach((table, index) => {
    const roundNum = index + 1;
    Scoreboard.attachDragAndDrop(table, {
      onMove: updateRoundScores,
      saveOrder: (currentTable, order) => saveManualOrder(activityId, currentTable, roundNum, order)
    });
  });
  const saveFinalOrder = (table, order) => saveManualOrder(activityId, table, null, order);
  attachFinalDragAndDropShared(finalTable, currentPointsMap, { saveOrder: saveFinalOrder });

  document.getElementById('compute-final').addEventListener('click', () => {
    currentPointsMap = computeFinalOrderShared([round1Table, round2Table, round3Table], finalTable);
    attachFinalDragAndDropShared(finalTable, currentPointsMap, { saveOrder: saveFinalOrder });
    Scoreboard.saveCurrentOrder(finalTable, true);
  });
});

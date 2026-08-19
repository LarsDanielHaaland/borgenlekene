// Basketball JS - copied and adapted from football.js
// Expected page-prefixed POST endpoint: `${window.location.pathname}api/set_manual_order/`

(function(){
  function $(s, root=document) { return root.querySelector(s); }
  function $all(s, root=document) { return Array.from(root.querySelectorAll(s)); }

  const roundTables = [$('#round1-table'), $('#round2-table'), $('#round3-table')];
  const finalTable = $('#final-standing');
  const computeBtn = $('#compute-final');
  const saveButtons = {
    1: $('#save-round-1'),
    2: $('#save-round-2'),
    3: $('#save-round-3'),
    final: $('#save-final')
  };

  // load saved orders from json_script
  const round1Data = JSON.parse(document.getElementById('round1-data').textContent || '[]');
  const round2Data = JSON.parse(document.getElementById('round2-data').textContent || '[]');
  const round3Data = JSON.parse(document.getElementById('round3-data').textContent || '[]');
  const finalData = JSON.parse(document.getElementById('final-data').textContent || '[]');

  const eventDiv = document.getElementById('basketball-data');
  const EVENT_ID = eventDiv.dataset.eventId;
  const ACTIVITY_ID = eventDiv.dataset.activityId; // should be 3

  // Keep a global points map for the final calculation
  let currentPointsMap = {};

  function initRoundTable(table, savedOrder){
    // If savedOrder is present, reorder rows to match
    if(savedOrder && savedOrder.length){
      const tbody = table.querySelector('tbody');
      const rowsById = {};
      $all('tbody tr', tbody).forEach(r => rowsById[parseInt(r.dataset.nicknameId, 10)] = r);
      tbody.innerHTML = '';
      savedOrder.forEach(id => {
        const idInt = parseInt(id, 10);
        if(rowsById[idInt]) tbody.appendChild(rowsById[idInt]);
      });
      // append any not in saved order at the end
      Object.values(rowsById).forEach(r => { 
        if(!savedOrder.includes(parseInt(r.dataset.nicknameId, 10))) tbody.appendChild(r); 
      });
    }
    // use shared attachMoveControls from tournament_base.js
    attachMoveControls(table, () => updateRoundScores(table));
    updateRoundScores(table);
  }

  function moveRowUp(row){
    const prev = row.previousElementSibling;
    if(prev) row.parentNode.insertBefore(row, prev);
  }

  function moveRowDown(row){
    const next = row.nextElementSibling;
    if(next) row.parentNode.insertBefore(next, row);
  }

  function updateRoundScores(table){
    const rows = $all('tbody tr', table);
    const n = rows.length;
    rows.forEach((r, idx) => {
      const scoreCell = r.querySelector('.round-score-cell');
      scoreCell.textContent = (n - idx); // N..1
    });
  }

  function getOrderFromTable(table){
    return $all('tbody tr', table).map(r => parseInt(r.dataset.nicknameId, 10));
  }

  function postOrder(order, round=null){
    // use shared saveManualOrder helper
    return saveManualOrder(ACTIVITY_ID, { querySelector: ()=>null, // placeholder not used by helper
    }, round).then(()=>({ success: false, error: 'deprecated' }));
  }

  // compute final totals: points per round are N..1 based on position
  function computeFinal(){
    // Reuse the same robust ordering logic as football.js's computeFinalOrder
    function readOrder(table) {
      return $all('tbody tr', table).map(r => r.dataset.nicknameId);
    }

    const r1Order = readOrder(roundTables[0]);
    const r2Order = readOrder(roundTables[1]);
    const r3Order = readOrder(roundTables[2]);
    const allIds = readOrder(finalTable);

    const N = allIds.length;
    const r1Pos = {}, r2Pos = {}, r3Pos = {};
    r1Order.forEach((id, idx) => { r1Pos[id] = idx; });
    r2Order.forEach((id, idx) => { r2Pos[id] = idx; });
    r3Order.forEach((id, idx) => { r3Pos[id] = idx; });

    const pointsMap = {};
    allIds.forEach(id => {
      // Ensure numeric arithmetic and never allow 0 points — minimum 1
      const p1raw = (r1Pos[id] !== undefined) ? (N - r1Pos[id]) : 1;
      const p2raw = (r2Pos[id] !== undefined) ? (N - r2Pos[id]) : 1;
      const p3raw = (r3Pos[id] !== undefined) ? (N - r3Pos[id]) : 1;
      const p1 = Math.max(1, Number(p1raw));
      const p2 = Math.max(1, Number(p2raw));
      const p3 = Math.max(1, Number(p3raw));
      pointsMap[id] = { r1: p1, r2: p2, r3: p3, total: p1 + p2 + p3 };
    });

    // Sort final order by total desc, then r3, r2, r1 as tiebreakers
    const finalOrder = allIds.slice().sort((a,b) => {
      if (pointsMap[b].total !== pointsMap[a].total) return pointsMap[b].total - pointsMap[a].total;
      if (pointsMap[b].r3 !== pointsMap[a].r3) return pointsMap[b].r3 - pointsMap[a].r3;
      if (pointsMap[b].r2 !== pointsMap[a].r2) return pointsMap[b].r2 - pointsMap[a].r2;
      return pointsMap[b].r1 - pointsMap[a].r1;
    });

    // Reorder final table rows
    const tbody = finalTable.querySelector('tbody');
    const map = {};
    $all('tbody tr', finalTable).forEach(r => { map[r.dataset.nicknameId] = r; });
    finalOrder.forEach(id => { const r = map[id]; if (r) tbody.appendChild(r); });

    // Update rank and total cells
    $all('tbody tr', finalTable).forEach((r, idx) => {
      const id = r.dataset.nicknameId;
      const rc = r.querySelector('.rank-cell'); if (rc) rc.textContent = idx+1;
      const tot = r.querySelector('.total-cell'); if (tot) tot.textContent = pointsMap[id].total;
    });

    currentPointsMap = pointsMap;
    // Debug: log computed points so we can inspect unexpected zeros
    console.debug('basketball: computed pointsMap', pointsMap);
    updateFinalControlsVisibility();
    attachFinalControls();
  }

  function updateFinalControlsVisibility(){
    const rows = $all('tbody tr', finalTable);
    rows.forEach((r, i) => {
      const cell = r.querySelector('.order-controls');
      cell.innerHTML = '';
      const up = document.createElement('button'); up.textContent='▲'; up.className='btn btn-sm btn-link move-up-final';
      const down = document.createElement('button'); down.textContent='▼'; down.className='btn btn-sm btn-link move-down-final';
      // default hide
      up.style.display = 'none'; down.style.display = 'none';
      // show up if previous exists and totals equal
      const prev = rows[i-1];
      if(prev){
        const curTot = currentPointsMap[r.dataset.nicknameId].total;
        const prevTot = currentPointsMap[prev.dataset.nicknameId].total;
        if(curTot === prevTot) up.style.display='';
      }
      const next = rows[i+1];
      if(next){
        const curTot = currentPointsMap[r.dataset.nicknameId].total;
        const nextTot = currentPointsMap[next.dataset.nicknameId].total;
        if(curTot === nextTot) down.style.display='';
      }
      cell.appendChild(up); cell.appendChild(down);
    });
  }

  function attachFinalControls(){
    // attach a single handler to final table
    finalTable.removeEventListener('click', finalTable._handler || (()=>{}));
    const handler = function(e){
      if(!e.target.classList.contains('move-up-final') && !e.target.classList.contains('move-down-final')) return;
      e.preventDefault();
      const btn = e.target; const row = btn.closest('tr');
      const id = row.dataset.nicknameId;
      if(btn.classList.contains('move-up-final')){
        const prev = row.previousElementSibling;
        if(!prev) return;
        if(currentPointsMap[id].total !== currentPointsMap[prev.dataset.nicknameId].total) return; // only allow tie swaps
        row.parentNode.insertBefore(row, prev);
      } else {
        const next = row.nextElementSibling;
        if(!next) return;
        if(currentPointsMap[id].total !== currentPointsMap[next.dataset.nicknameId].total) return;
        row.parentNode.insertBefore(next, row);
      }
      // after swap, update ranks and reorder visibility
      $all('tbody tr', finalTable).forEach((r,i) => r.querySelector('.rank-cell').textContent = i+1);
      updateFinalControlsVisibility();
    };
    finalTable.addEventListener('click', handler);
    finalTable._handler = handler;
  }

  // initialize
  document.addEventListener('DOMContentLoaded', function(){
    initRoundTable(roundTables[0], round1Data);
    initRoundTable(roundTables[1], round2Data);
    initRoundTable(roundTables[2], round3Data);
    // final: apply saved final order if present
    if(finalData && finalData.length){
      const tbody = finalTable.querySelector('tbody');
      const rowsById = {};
      $all('tbody tr', finalTable).forEach(r => rowsById[parseInt(r.dataset.nicknameId, 10)] = r);
      tbody.innerHTML = '';
      finalData.forEach(id => { 
        const idInt = parseInt(id, 10);
        if(rowsById[idInt]) tbody.appendChild(rowsById[idInt]); 
      });
      Object.values(rowsById).forEach(r => { 
        if(!finalData.includes(parseInt(r.dataset.nicknameId, 10))) tbody.appendChild(r); 
      });
      $all('tbody tr', finalTable).forEach((r,i) => { r.querySelector('.rank-cell').textContent = i+1; });
    }

    // Auto-compute final results on page load if there's any saved round data
    if((round1Data && round1Data.length) || (round2Data && round2Data.length) || (round3Data && round3Data.length)){
      computeFinal();
    }

    // wire compute and save
    computeBtn.addEventListener('click', computeFinal);
  saveButtons[1].addEventListener('click', () => {
    saveManualOrder(ACTIVITY_ID, roundTables[0], 1).then(data=>{ if(data.success) showNotification('Saved round 1','success'); else showNotification('Save failed: '+(data.error||JSON.stringify(data)),'error'); }).catch(e=>showNotification('Network error: '+e,'error'));
  });
  saveButtons[2].addEventListener('click', () => {
    saveManualOrder(ACTIVITY_ID, roundTables[1], 2).then(data=>{ if(data.success) showNotification('Saved round 2','success'); else showNotification('Save failed: '+(data.error||JSON.stringify(data)),'error'); }).catch(e=>showNotification('Network error: '+e,'error'));
  });
  saveButtons[3].addEventListener('click', () => {
    saveManualOrder(ACTIVITY_ID, roundTables[2], 3).then(data=>{ if(data.success) showNotification('Saved round 3','success'); else showNotification('Save failed: '+(data.error||JSON.stringify(data)),'error'); }).catch(e=>showNotification('Network error: '+e,'error'));
  });
  saveButtons.final.addEventListener('click', () => {
    saveManualOrder(ACTIVITY_ID, finalTable, null).then(data=>{ if(data.success) showNotification('Saved final','success'); else showNotification('Save failed: '+(data.error||JSON.stringify(data)),'error'); }).catch(e=>showNotification('Network error: '+e,'error'));
  });
  });

})();

// Notification helper for this file
function showNotification(message, type='info'){
  const el = document.createElement('div');
  el.className = 'bm-notification';
  el.style.position = 'fixed';
  el.style.right = '16px';
  el.style.bottom = '16px';
  el.style.padding = '8px 12px';
  el.style.borderRadius = '6px';
  el.style.color = '#fff';
  el.style.zIndex = 2000;
  el.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
  if(type === 'success') el.style.background = '#198754';
  else if(type === 'error') el.style.background = '#dc3545';
  else el.style.background = '#6c757d';
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(()=>{ el.style.transition='opacity 0.3s'; el.style.opacity='0'; setTimeout(()=>el.remove(),300); }, 3000);
}

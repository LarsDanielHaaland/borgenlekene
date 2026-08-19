// Shared tournament utilities used by football/basketball/dice pages
(function(window){
  const Tournament = {};

  function getRowId(row){
    const attr = row.getAttribute('data-nickname-id');
    if(attr !== null) return parseInt(attr, 10);
    if(row.dataset && row.dataset.nicknameId) return parseInt(row.dataset.nicknameId, 10);
    return null;
  }

  Tournament.getRowId = getRowId;

  Tournament.getCookie = function(name){
    const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
  };

  Tournament.showNotification = function(message, type='info'){
    const el = document.createElement('div');
    el.className = 'tm-notification';
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
  };

  // Attach up/down controls to a table's rows. onMove(table) is called after any move.
  Tournament.attachMoveControls = function(table, onMove){
    if(!table) return;
    const tbody = table.querySelector('tbody');
    // clear existing controls
    Array.from(tbody.querySelectorAll('.order-controls')).forEach(c=>{ c.innerHTML = ''; });

    Array.from(tbody.querySelectorAll('tr')).forEach(tr => {
      const controls = tr.querySelector('.order-controls');
      if(!controls) return;
      const up = document.createElement('button'); up.type='button'; up.className='btn btn-sm btn-link move-up'; up.textContent='▲';
      const down = document.createElement('button'); down.type='button'; down.className='btn btn-sm btn-link move-down'; down.textContent='▼';
      controls.appendChild(up); controls.appendChild(down);
    });

    // event delegation on tbody
    // remove any previous delegated handler
    if(tbody._moveHandler) tbody.removeEventListener('click', tbody._moveHandler);
    const handler = function(e){
      const up = e.target.closest('.move-up');
      const down = e.target.closest('.move-down');
      if(!up && !down) return;
      const tr = e.target.closest('tr'); if(!tr) return;
      if(up){ const prev = tr.previousElementSibling; if(prev) prev.parentNode.insertBefore(tr, prev); }
      if(down){ const next = tr.nextElementSibling; if(next) next.parentNode.insertBefore(next, tr); }
      if(typeof onMove === 'function') onMove(table);
    };
    tbody._moveHandler = handler;
    tbody.addEventListener('click', handler);
  };

  Tournament.updateRoundScores = function(table){
    if(!table) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const N = rows.length;
    rows.forEach((r, idx) => { const sc = r.querySelector('.round-score-cell'); if(sc) sc.textContent = (N - idx); });
  };

  Tournament.applySavedOrder = function(table, savedOrder){
    if(!table || !savedOrder || !savedOrder.length) return;
    const tbody = table.querySelector('tbody');
    const map = {};
    Array.from(tbody.querySelectorAll('tr')).forEach(r => { const id = getRowId(r); if(id !== null) map[id] = r; });
    savedOrder.forEach(id => { const r = map[id]; if(r) tbody.appendChild(r); });
  };

  Tournament.getOrderFromTable = function(table){
    if(!table) return [];
    return Array.from(table.querySelectorAll('tbody tr')).map(r => getRowId(r));
  };

  Tournament.saveManualOrder = async function(activityId, table, roundNum){
    const ids = Tournament.getOrderFromTable(table);
    const payload = { activity_id: Number(activityId), order: ids };
    if(roundNum) payload.round = roundNum;
    const path = `${window.location.pathname}api/set_manual_order/`;
    try{
      const resp = await fetch(path, { method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':Tournament.getCookie('csrftoken')}, body: JSON.stringify(payload) });
      const data = await resp.json();
      return data;
    }catch(err){
      return { success: false, error: String(err) };
    }
  };

  // Compute final order given an array of round tables and a final table.
  // Returns pointsMap { id: { r1, r2, r3, total } }
  Tournament.computeFinalOrder = function(roundTables, finalTable){
    function readOrder(table){ if(!table) return []; return Array.from(table.querySelectorAll('tbody tr')).map(r => getRowId(r)); }
    const rOrders = roundTables.map(t => readOrder(t));
    const allIds = readOrder(finalTable);
    const N = allIds.length;
    const posMaps = rOrders.map(arr => { const m = {}; arr.forEach((id, idx) => { m[id] = idx; }); return m; });

    const pointsMap = {};
    allIds.forEach(id => {
      const parts = {};
      for(let i=0;i<posMaps.length;i++){
        const pidx = posMaps[i][id];
        const val = (pidx !== undefined) ? (N - pidx) : 1;
        parts['r'+(i+1)] = Math.max(1, Number(val));
      }
      let total = 0; Object.keys(parts).forEach(k => { total += parts[k]; });
      parts.total = total;
      pointsMap[id] = parts;
    });

    // sort final table by total desc, then by last round -> first as tiebreakers
    const finalOrder = allIds.slice().sort((a,b) => {
      if(pointsMap[b].total !== pointsMap[a].total) return pointsMap[b].total - pointsMap[a].total;
      // tiebreaker: compare rounds from last to first
      for(let i=posMaps.length-1;i>=0;i--){
        const rk = 'r'+(i+1);
        if(pointsMap[b][rk] !== pointsMap[a][rk]) return pointsMap[b][rk] - pointsMap[a][rk];
      }
      return 0;
    });

    // Reorder finalTable rows
    const tbody = finalTable.querySelector('tbody');
    const map = {};
    Array.from(tbody.querySelectorAll('tr')).forEach(r => { map[getRowId(r)] = r; });
    finalOrder.forEach(id => { const r = map[id]; if(r) tbody.appendChild(r); });

    // Update rank and total cells
    Array.from(tbody.querySelectorAll('tr')).forEach((r, idx) => {
      const id = getRowId(r);
      const rc = r.querySelector('.rank-cell'); if(rc) rc.textContent = idx+1;
      const tot = r.querySelector('.total-cell'); if(tot) tot.textContent = (pointsMap[id] ? pointsMap[id].total : '');
    });

    return pointsMap;
  };

  // Attach final tie-only controls for swapping adjacent equal-total rows.
  Tournament.attachFinalControls = function(finalTable, pointsMap){
    if(!finalTable) return;
    // ensure controls exist
    Array.from(finalTable.querySelectorAll('tbody tr')).forEach(tr => {
      const controls = tr.querySelector('.order-controls'); if(!controls) return; controls.innerHTML = '';
      const up = document.createElement('button'); up.type='button'; up.className='btn btn-sm btn-link move-up'; up.textContent='▲'; up.style.display='none';
      const down = document.createElement('button'); down.type='button'; down.className='btn btn-sm btn-link move-down'; down.textContent='▼'; down.style.display='none';
      controls.appendChild(up); controls.appendChild(down);
    });

    // update visibility
    Tournament.updateFinalControlsVisibility(finalTable, pointsMap);

    // attach single click handler
    const tableEl = finalTable;
    if(tableEl._finalHandler) tableEl.removeEventListener('click', tableEl._finalHandler);
    const handler = (e) => {
      const up = e.target.closest('.move-up');
      const down = e.target.closest('.move-down');
      if(!up && !down) return;
      const tr = e.target.closest('tr'); if(!tr) return;
      const curId = getRowId(tr);
      if(up){ const prev = tr.previousElementSibling; if(prev){ const prevId = getRowId(prev); if(pointsMap[curId] && pointsMap[prevId] && pointsMap[curId].total === pointsMap[prevId].total) prev.parentNode.insertBefore(tr, prev); } }
      if(down){ const next = tr.nextElementSibling; if(next){ const nextId = getRowId(next); if(pointsMap[curId] && pointsMap[nextId] && pointsMap[curId].total === pointsMap[nextId].total) next.parentNode.insertBefore(next, tr); } }

      // update ranks
      Array.from(finalTable.querySelectorAll('tbody tr')).forEach((r, idx) => { const id = getRowId(r); const rc = r.querySelector('.rank-cell'); if(rc) rc.textContent = idx+1; const tot = r.querySelector('.total-cell'); if(tot) tot.textContent = (pointsMap[id] ? pointsMap[id].total : ''); });
      // refresh visibility
      Tournament.updateFinalControlsVisibility(finalTable, pointsMap);
    };
    tableEl._finalHandler = handler;
    tableEl.addEventListener('click', handler);
  };

  Tournament.updateFinalControlsVisibility = function(finalTable, pointsMap){
    if(!finalTable) return;
    const rows = Array.from(finalTable.querySelectorAll('tbody tr'));
    rows.forEach((r, idx) => {
      const up = r.querySelector('.move-up'); const down = r.querySelector('.move-down');
      if(up) up.style.display = 'none'; if(down) down.style.display = 'none';
      const id = getRowId(r);
      const prev = rows[idx-1]; if(prev){ const prevId = getRowId(prev); if(pointsMap && pointsMap[id] && pointsMap[prevId] && pointsMap[id].total === pointsMap[prevId].total) if(up) up.style.display = ''; }
      const next = rows[idx+1]; if(next){ const nextId = getRowId(next); if(pointsMap && pointsMap[id] && pointsMap[nextId] && pointsMap[id].total === pointsMap[nextId].total) if(down) down.style.display = ''; }
    });
  };

  // expose
  window.Tournament = Tournament;
  window.getCookie = Tournament.getCookie;
  window.showNotification = Tournament.showNotification;
  window.attachMoveControls = Tournament.attachMoveControls;
  window.applySavedOrder = Tournament.applySavedOrder;
  window.updateRoundScores = Tournament.updateRoundScores;
  window.getOrderFromTable = Tournament.getOrderFromTable;
  window.saveManualOrder = Tournament.saveManualOrder;
  window.computeFinalOrderShared = Tournament.computeFinalOrder;
  window.attachFinalControlsShared = Tournament.attachFinalControls;
  window.updateFinalControlsVisibilityShared = Tournament.updateFinalControlsVisibility;

})(window);

// Shared tournament utilities used by football/basketball/dice pages
(function(window){
  const Tournament = {};
  const Scoreboard = {};

  function tableRows(table){
    return table ? Array.from(table.querySelectorAll('tbody tr')) : [];
  }

  function canMove(row, neighbor, movement){
    if(movement !== 'ties') return true;
    const value = row.dataset.tieValue;
    return value !== undefined && value !== '' && value === neighbor.dataset.tieValue;
  }

  Scoreboard.getOrder = function(table){
    return tableRows(table).map(row => getRowId(row));
  };

  Scoreboard.updateRanks = function(table){
    tableRows(table).forEach((row, index) => {
      const rank = row.querySelector('.rank-cell');
      if(rank) rank.textContent = index + 1;
    });
  };

  Scoreboard.renderRows = function(table, rows, columns){
    const tbody = table.querySelector('tbody');
    tbody.replaceChildren();
    rows.forEach((row, index) => {
      const tr = document.createElement('tr');
      tr.dataset.nicknameId = row.id;
      if(row.tieValue !== undefined && row.tieValue !== null) tr.dataset.tieValue = row.tieValue;

      const rank = document.createElement('td');
      rank.className = 'rank-cell';
      rank.textContent = row.rank || index + 1;
      tr.appendChild(rank);

      const name = document.createElement('td');
      name.className = 'scoreboard-player';
      name.textContent = row.name;
      tr.appendChild(name);

      columns.forEach(column => {
        const cell = document.createElement('td');
        cell.className = column.cellClass || '';
        if(column.emphasize) cell.classList.add('scoreboard-emphasis');
        const value = row.metrics ? row.metrics[column.key] : '';
        cell.textContent = value === undefined || value === null || value === '' ? '-' : value;
        tr.appendChild(cell);
      });

      const controls = document.createElement('td');
      controls.className = 'order-controls';
      tr.appendChild(controls);
      tbody.appendChild(tr);
    });
    Scoreboard.updateRanks(table);
  };

  Scoreboard.refreshControls = function(table, movement){
    const rows = tableRows(table);
    rows.forEach((row, index) => {
      const cell = row.querySelector('.order-controls');
      if(!cell) return;
      cell.replaceChildren();

      const previous = rows[index - 1];
      if(previous && canMove(row, previous, movement)) {
        const up = document.createElement('button');
        up.type = 'button';
        up.className = 'btn btn-sm btn-link move-up';
        up.textContent = '\u25b2';
        up.title = 'Flytt opp';
        up.setAttribute('aria-label', 'Flytt opp');
        cell.appendChild(up);
      }

      const next = rows[index + 1];
      if(next && canMove(row, next, movement)) {
        const down = document.createElement('button');
        down.type = 'button';
        down.className = 'btn btn-sm btn-link move-down';
        down.textContent = '\u25bc';
        down.title = 'Flytt ned';
        down.setAttribute('aria-label', 'Flytt ned');
        cell.appendChild(down);
      }
    });
  };

  Scoreboard.attachMoveControls = function(table, options){
    if(!table) return;
    if(typeof options === 'function') options = { onMove: options };
    options = options || {};
    const movement = options.movement || table.dataset.movePolicy || 'free';
    Scoreboard.refreshControls(table, movement);
    if(table._scoreboardMoveHandler) table.removeEventListener('click', table._scoreboardMoveHandler);
    table._scoreboardMoveHandler = event => {
      const up = event.target.closest('.move-up');
      const down = event.target.closest('.move-down');
      if(!up && !down) return;
      const row = event.target.closest('tr');
      if(!row || !table.contains(row)) return;
      const neighbor = up ? row.previousElementSibling : row.nextElementSibling;
      if(!neighbor || !canMove(row, neighbor, movement)) return;
      if(up) neighbor.parentNode.insertBefore(row, neighbor);
      else neighbor.parentNode.insertBefore(neighbor, row);

      Scoreboard.updateRanks(table);
      Scoreboard.refreshControls(table, movement);
      if(typeof options.onMove === 'function') options.onMove(table);
    };
    table.addEventListener('click', table._scoreboardMoveHandler);
  };

  window.Scoreboard = Scoreboard;

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

  Tournament.attachMoveControls = function(table, onMove){
    Scoreboard.attachMoveControls(table, { onMove });
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
    const restored = new Set();
    savedOrder.forEach(id => {
      const row = map[id];
      if(row){
        tbody.appendChild(row);
        restored.add(Number(id));
      }
    });
    Object.entries(map).forEach(([id, row]) => {
      if(!restored.has(Number(id))) tbody.appendChild(row);
    });
    Scoreboard.updateRanks(table);
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
      if(pointsMap[id]) r.dataset.tieValue = pointsMap[id].total;
    });

    return pointsMap;
  };

  // Attach final tie-only controls for swapping adjacent equal-total rows.
  Tournament.attachFinalControls = function(finalTable, pointsMap){
    if(!finalTable) return;
    Array.from(finalTable.querySelectorAll('tbody tr')).forEach(row => {
      const points = pointsMap[getRowId(row)];
      if(points) row.dataset.tieValue = points.total;
    });
    Scoreboard.attachMoveControls(finalTable, { movement: 'ties' });
  };

  Tournament.updateFinalControlsVisibility = function(finalTable, pointsMap){
    if(!finalTable) return;
    if(pointsMap){
      Array.from(finalTable.querySelectorAll('tbody tr')).forEach(row => {
        const points = pointsMap[getRowId(row)];
        if(points) row.dataset.tieValue = points.total;
      });
    }
    Scoreboard.refreshControls(finalTable, 'ties');
  };

  Tournament.Scoreboard = Scoreboard;

  // expose
  window.Tournament = Tournament;
  window.Scoreboard = Scoreboard;
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

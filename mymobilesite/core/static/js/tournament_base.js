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

  function updateDraggableRows(table, movement){
    const rows = tableRows(table);
    rows.forEach(row => {
      const canDrag = rows.length > 1 && (
        movement !== 'ties'
        || rows.some(neighbor => neighbor !== row && canMove(row, neighbor, movement))
      );
      row.classList.toggle('scoreboard-row-draggable', canDrag);
    });
  }

  function ordersEqual(first, second){
    return first.length === second.length && first.every((id, index) => id === second[index]);
  }

  function isCompleteOrder(table, order){
    const rowCount = tableRows(table).length;
    return rowCount > 0
      && order.length === rowCount
      && order.every(Number.isInteger)
      && new Set(order).size === rowCount;
  }

  function setSaveStatus(table, status, message){
    const element = table.closest('.scoreboard-wrapper')?.querySelector('[data-scoreboard-save-status]');
    if(!element) return;
    element.textContent = message;
    element.className = `scoreboard-save-status scoreboard-save-status--${status}`;
  }

  function restoreOrder(table, order){
    const tbody = table.querySelector('tbody');
    const rows = new Map(tableRows(table).map(row => [getRowId(row), row]));
    order.forEach(id => {
      const row = rows.get(id);
      if(row) tbody.appendChild(row);
    });
    Scoreboard.updateRanks(table);
  }

  function clearInvalidTarget(state){
    if(state.invalidTarget) state.invalidTarget.classList.remove('scoreboard-drop-invalid');
    state.invalidTarget = null;
  }

  function setInvalidTarget(state, row){
    clearInvalidTarget(state);
    if(row) row.classList.add('scoreboard-drop-invalid');
    state.invalidTarget = row || null;
  }

  function moveRowToPointer(state, clientX, clientY){
    const { table, row, movement } = state;
    const tableRect = table.getBoundingClientRect();
    if(clientX < tableRect.left || clientX > tableRect.right) {
      state.invalidDrop = true;
      setInvalidTarget(state, null);
      return;
    }

    const candidates = tableRows(table).filter(candidate => candidate !== row && canMove(row, candidate, movement));
    if(!candidates.length) return;
    const target = candidates.reduce((closest, candidate) => {
      const rect = candidate.getBoundingClientRect();
      const distance = Math.abs(clientY - (rect.top + rect.height / 2));
      return !closest || distance < closest.distance
        ? { row: candidate, rect, distance }
        : closest;
    }, null);

    state.invalidDrop = false;
    setInvalidTarget(state, null);
    const afterTarget = clientY > target.rect.top + target.rect.height / 2;
    const reference = afterTarget ? target.row.nextElementSibling : target.row;
    if(reference !== row) table.querySelector('tbody').insertBefore(row, reference);
    state.changed = !ordersEqual(state.startOrder, Scoreboard.getOrder(table));
  }

  function autoScroll(state){
    if(!state.dragging || state.autoScrollFrame) return;
    const edgeSize = 56;
    const maxStep = 12;
    const tick = () => {
      if(!state.dragging) {
        state.autoScrollFrame = null;
        return;
      }

      const y = state.lastY;
      const height = window.innerHeight;
      let step = 0;
      if(y < edgeSize) step = -Math.min(maxStep, Math.ceil((edgeSize - y) / 5));
      else if(y > height - edgeSize) step = Math.min(maxStep, Math.ceil((y - height + edgeSize) / 5));
      if(step) {
        const previousScrollY = window.scrollY;
        window.scrollBy(0, step);
        if(window.scrollY === previousScrollY) {
          state.autoScrollFrame = null;
          return;
        }
        moveRowToPointer(state, state.lastX, state.lastY);
        state.autoScrollFrame = window.requestAnimationFrame(tick);
      } else {
        state.autoScrollFrame = null;
      }
    };
    state.autoScrollFrame = window.requestAnimationFrame(tick);
  }

  function saveCurrentOrder(table, state, force=false){
    if(typeof state.options.saveOrder !== 'function') return;
    const order = Scoreboard.getOrder(table);
    if(!isCompleteOrder(table, order)) {
      state.pendingOrder = null;
      restoreOrder(table, state.lastSavedOrder);
      if(typeof state.options.onMove === 'function') state.options.onMove(table);
      setSaveStatus(table, 'error', 'Kunne ikke lagre rekkefølgen.');
      Tournament.showNotification('Kunne ikke lagre rekkefølgen.', 'error');
      return;
    }

    if(state.saving) {
      state.pendingOrder = !force && ordersEqual(order, state.inFlightOrder) ? null : order;
      return;
    }
    if(!force && ordersEqual(order, state.lastSavedOrder)) {
      setSaveStatus(table, 'saved', 'Lagret');
      return;
    }

    state.pendingOrder = order;
    flushSaveQueue(table, state);
  }

  async function flushSaveQueue(table, state){
    if(state.saving || !state.pendingOrder) return;
    const order = state.pendingOrder;
    state.pendingOrder = null;
    state.saving = true;
    state.inFlightOrder = order;
    setSaveStatus(table, 'saving', 'Lagrer…');

    let result;
    try {
      result = await state.options.saveOrder(table, order);
    } catch(error) {
      result = { success: false, error: String(error) };
    }
    state.saving = false;
    state.inFlightOrder = null;

    if(!result || result.success !== true) {
      state.pendingOrder = null;
      restoreOrder(table, state.lastSavedOrder);
      if(typeof state.options.onMove === 'function') state.options.onMove(table);
      setSaveStatus(table, 'error', 'Lagring mislyktes.');
      Tournament.showNotification(
        `Kunne ikke lagre rekkefølgen: ${result?.error || 'Ukjent feil'}`,
        'error'
      );
      return;
    }

    state.lastSavedOrder = order;
    if(state.pendingOrder && ordersEqual(state.pendingOrder, state.lastSavedOrder)) {
      state.pendingOrder = null;
    }
    if(state.pendingOrder) {
      flushSaveQueue(table, state);
      return;
    }
    setSaveStatus(table, 'saved', 'Lagret');
  }

  function finishDrag(state, cancelled=false){
    const { table, row } = state;
    window.clearTimeout(state.longPressTimer);
    if(!state.dragging) {
      state.pendingRow = null;
      return;
    }

    if(cancelled || state.invalidDrop) {
      restoreOrder(table, state.startOrder);
      if(typeof state.options.onMove === 'function') state.options.onMove(table);
    } else if(state.changed) {
      Scoreboard.updateRanks(table);
      if(typeof state.options.onMove === 'function') state.options.onMove(table);
      saveCurrentOrder(table, state);
    }

    clearInvalidTarget(state);
    row.classList.remove('scoreboard-row-dragging');
    table.classList.remove('scoreboard-dragging');
    document.body.classList.remove('scoreboard-drag-active');
    if(state.preventTouchScroll) {
      table.removeEventListener('touchmove', state.preventTouchScroll);
      state.preventTouchScroll = null;
    }
    state.dragging = false;
    state.pendingRow = null;
    state.row = null;
    state.changed = false;
    state.invalidDrop = false;
    if(state.autoScrollFrame) {
      window.cancelAnimationFrame(state.autoScrollFrame);
      state.autoScrollFrame = null;
    }
  }

  function beginDrag(state){
    if(!state.pendingRow || state.dragging) return;
    state.dragging = true;
    state.row = state.pendingRow;
    state.startOrder = Scoreboard.getOrder(state.table);
    state.changed = false;
    state.invalidDrop = false;
    state.lastX = state.startX;
    state.lastY = state.startY;
    state.row.classList.add('scoreboard-row-dragging');
    state.table.classList.add('scoreboard-dragging');
    document.body.classList.add('scoreboard-drag-active');
    if(state.pointerType === 'touch') {
      if(typeof navigator.vibrate === 'function') navigator.vibrate(10);
      state.preventTouchScroll = touchEvent => {
        if(touchEvent.cancelable) touchEvent.preventDefault();
      };
      state.table.addEventListener('touchmove', state.preventTouchScroll, { passive: false });
    }
    autoScroll(state);
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

      tbody.appendChild(tr);
    });
    Scoreboard.updateRanks(table);
    setSaveStatus(table, 'idle', '');
    const state = table._scoreboardDragState;
    if(state) {
      const currentOrder = Scoreboard.getOrder(table);
      state.lastSavedOrder = currentOrder;
      state.pendingOrder = state.saving && isCompleteOrder(table, currentOrder)
        ? currentOrder
        : null;
    }
  };

  Scoreboard.attachDragAndDrop = function(table, options){
    if(!table) return;
    if(typeof options === 'function') options = { onMove: options };
    options = options || {};
    let state = table._scoreboardDragState;
    if(!state) {
      state = {
        table,
        options,
        movement: options.movement || table.dataset.movePolicy || 'free',
        lastSavedOrder: Scoreboard.getOrder(table),
        pendingOrder: null,
        saving: false,
        inFlightOrder: null,
        pendingRow: null,
        dragging: false,
      };
      table._scoreboardDragState = state;
    } else {
      state.options = options;
      state.movement = options.movement || table.dataset.movePolicy || 'free';
    }
    updateDraggableRows(table, state.movement);
    if(state.dragEventsAttached) return;

    const start = event => {
      const row = event.target.closest('tbody tr');
      if(!row || !table.contains(row) || !row.classList.contains('scoreboard-row-draggable')
        || event.target.closest('a, button, input, select, textarea, [contenteditable="true"]')
        || (event.pointerType !== 'touch' && event.button !== 0)) return;

      window.clearTimeout(state.longPressTimer);
      state.pendingRow = row;
      state.pointerId = event.pointerId;
      state.pointerType = event.pointerType;
      state.startX = event.clientX;
      state.startY = event.clientY;
      state.dragging = false;
      table.setPointerCapture(event.pointerId);

      if(event.pointerType === 'touch') {
        state.longPressTimer = window.setTimeout(() => beginDrag(state), 250);
      }
    };

    const move = event => {
      if(event.pointerId !== state.pointerId || !state.pendingRow) return;
      const distance = Math.hypot(event.clientX - state.startX, event.clientY - state.startY);
      if(!state.dragging && state.pointerType === 'touch') {
        if(distance > 10) {
          window.clearTimeout(state.longPressTimer);
          state.pendingRow = null;
        }
        return;
      }
      if(!state.dragging) {
        if(distance < 3) return;
        beginDrag(state);
      }
      event.preventDefault();
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      moveRowToPointer(state, event.clientX, event.clientY);
      autoScroll(state);
    };

    const end = event => {
      if(event.pointerId !== state.pointerId) return;
      finishDrag(state);
      state.pointerId = null;
    };

    const cancel = event => {
      if(event.pointerId !== state.pointerId) return;
      finishDrag(state, true);
      state.pointerId = null;
    };

    table.addEventListener('pointerdown', start);
    table.addEventListener('pointermove', move, { passive: false });
    table.addEventListener('pointerup', end);
    table.addEventListener('pointercancel', cancel);
    state.dragEventsAttached = true;
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

  Scoreboard.saveCurrentOrder = function(table, force=false){
    const state = table?._scoreboardDragState;
    if(state) saveCurrentOrder(table, state, force);
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

  Tournament.saveManualOrder = async function(activityId, table, roundNum, orderOverride){
    const ids = orderOverride || Tournament.getOrderFromTable(table);
    if(!isCompleteOrder(table, ids)) {
      return { success: false, error: 'Order must include every participant exactly once.' };
    }
    const payload = { activity_id: Number(activityId), order: ids };
    if(roundNum) payload.round = roundNum;
    const path = `${window.location.pathname}api/set_manual_order/`;
    try{
      const resp = await fetch(path, { method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':Tournament.getCookie('csrftoken')}, body: JSON.stringify(payload) });
      const data = await resp.json();
      if(!resp.ok || data.success !== true) {
        return { success: false, error: data.error || `Request failed (${resp.status})` };
      }
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

  Tournament.attachFinalDragAndDrop = function(finalTable, pointsMap, options){
    if(!finalTable) return;
    Array.from(finalTable.querySelectorAll('tbody tr')).forEach(row => {
      const points = pointsMap[getRowId(row)];
      if(points) row.dataset.tieValue = points.total;
    });
    Scoreboard.attachDragAndDrop(finalTable, { ...options, movement: 'ties' });
  };

  Tournament.Scoreboard = Scoreboard;

  // expose
  window.Tournament = Tournament;
  window.Scoreboard = Scoreboard;
  window.getCookie = Tournament.getCookie;
  window.showNotification = Tournament.showNotification;
  window.applySavedOrder = Tournament.applySavedOrder;
  window.updateRoundScores = Tournament.updateRoundScores;
  window.getOrderFromTable = Tournament.getOrderFromTable;
  window.saveManualOrder = Tournament.saveManualOrder;
  window.computeFinalOrderShared = Tournament.computeFinalOrder;
  window.attachFinalDragAndDropShared = Tournament.attachFinalDragAndDrop;

})(window);

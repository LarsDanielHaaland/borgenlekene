document.addEventListener('DOMContentLoaded', () => {
  const modeIndividual = document.getElementById('mode-individual');
  const modeGroup = document.getElementById('mode-group');
  const saveBtn = document.getElementById('save-running-btn');
  const statusEl = document.getElementById('running-status');
  const participantList = document.getElementById('participants-list');
  const standingsBody = document.getElementById('running-standings');
  // Modal elements
  const manualSetModalEl = document.getElementById('manualSetModal');
  const resetConfirmModalEl = document.getElementById('resetConfirmModal');
  const manualSetMinutes = document.getElementById('manual-set-minutes');
  const manualSetSeconds = document.getElementById('manual-set-seconds');
  const manualSetError = document.getElementById('manual-set-error');
  const manualSetConfirm = document.getElementById('manual-set-confirm');
  const resetConfirmBtn = document.getElementById('reset-confirm-btn');
  let manualTargetId = null;
  let resetTargetId = null;

  let mode = 'individual';
  let timers = {}; // nickname_id -> start timestamp
  let recorded = {}; // nickname_id -> time_seconds
  let clockInterval = null;
  let manualOrder = null; // array of nickname ids representing user ordering for ties

  function formatSeconds(ms) {
    // return total seconds (integer)
    return Math.round(ms / 1000);
  }

  function formatMMSS(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs.toString().padStart(2,'0')}`;
  }

  function recalcStandings() {
    // Reset any previously computed manual order when rebuilding standings
    manualOrder = null;
    // Build an array of results from recorded times or existing time spans.
    const rows = [];
    participantList.querySelectorAll('li.list-group-item').forEach(item => {
      const nameEl = item.querySelector('strong');
      const timeSpan = item.querySelector('span[data-nickname-id]');
      if (!nameEl || !timeSpan) return;
      const id = parseInt(timeSpan.getAttribute('data-nickname-id'), 10);
      let timeSeconds = null;
      if (recorded[id] !== undefined) timeSeconds = recorded[id];
      else {
        const text = timeSpan.textContent.trim();
        if (text && text !== '-') {
          // support MM:SS (e.g. 1:23) or plain seconds like '3s' or '3'
          if (text.indexOf(':') !== -1) {
            const parts = text.split(':');
            const mins = parseInt(parts[0], 10);
            const secs = parseInt(parts[1], 10);
            if (!Number.isNaN(mins) && !Number.isNaN(secs)) timeSeconds = mins * 60 + secs;
          } else {
            const parsed = parseFloat(text.replace(/s$/,''));
            if (!Number.isNaN(parsed)) timeSeconds = Math.round(parsed);
          }
        }
      }
      if (timeSeconds !== null) rows.push({ id, name: nameEl.textContent.trim(), time: timeSeconds });
    });

    // Sort ascending (best time first)
    rows.sort((a,b) => a.time - b.time);

    // Render Name, Time, Poeng (points mirror update_total_scores: total - rank + 1) and controls column
    standingsBody.innerHTML = '';
    const total = rows.length;
    rows.forEach((r, idx) => {
      const points = total - idx; // idx is 0-based rank
      const tr = document.createElement('tr');
      tr.setAttribute('data-nickname-id', r.id);
      tr.setAttribute('data-time', r.time);
      tr.innerHTML = `<td>${r.name}</td><td>${formatMMSS(r.time)}</td><td class="fw-bold">${points}</td><td class="order-controls"></td>`;
      standingsBody.appendChild(tr);
    });

      // Add move up/down controls for tied adjacent rows
      attachRunningMoveControls();
  }

  // Toggle modes and show/hide group vs individual buttons
  function setMode(newMode) {
    mode = newMode;
    if (mode === 'individual') {
      modeIndividual.classList.add('active'); modeGroup.classList.remove('active');
      document.querySelectorAll('.individual-start, .individual-stop').forEach(el => el.style.display = 'inline-block');
      document.querySelectorAll('.group-start, .group-stop').forEach(el => el.style.display = 'none');
    } else {
      modeGroup.classList.add('active'); modeIndividual.classList.remove('active');
      document.querySelectorAll('.individual-start, .individual-stop').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.group-start, .group-stop').forEach(el => el.style.display = 'inline-block');
    }
  }
  modeIndividual.addEventListener('click', () => setMode('individual'));
  modeGroup.addEventListener('click', () => {
    if (mode !== 'group' && hasAnyRecordedTime()) {
      if (!confirm('Minst en deltaker har allerede fått en tid. Vil du bytte til gruppestart?')) return;
    }
    setMode('group');
  });

  // Returns true if any participant currently has a time recorded (in-memory or shown in the UI)
  function hasAnyRecordedTime() {
    if (Object.keys(recorded).length > 0) return true;
    return Array.from(participantList.querySelectorAll('.time-display')).some(
      span => span.textContent.trim() !== '-'
    );
  }

  // Start/stop handlers
  participantList.addEventListener('click', (e) => {
    const startBtn = e.target.closest('.start-btn');
    const stopBtn = e.target.closest('.stop-btn');
    if (startBtn) {
      const id = parseInt(startBtn.dataset.nicknameId, 10);
      // no undo prompt; starting will simply begin a new timing session

      // start timer for individual or group
      if (mode === 'individual') {
        timers[id] = Date.now();
        // show live clock
        const live = participantList.querySelector(`.live-clock[data-nickname-id="${id}"]`);
  if (live) { live.style.display = 'inline-block'; live.textContent = formatMMSS(0); }

        startBtn.disabled = true;
        startBtn.classList.remove('btn-outline-success');
        startBtn.classList.add('btn-success');
        const siblingStop = startBtn.closest('div').querySelector('.individual-stop');
        if (siblingStop) siblingStop.disabled = false;
      } else {
        // group mode: start all that don't have timers
        const now = Date.now();
        participantList.querySelectorAll('.group-start').forEach(b => {
          const nid = parseInt(b.dataset.nicknameId, 10);
          if (!timers[nid]) {
            timers[nid] = now;
            b.disabled = true;
            b.classList.remove('btn-outline-primary');
            b.classList.add('btn-primary');
            const stop = b.closest('div').querySelector('.group-stop');
            if (stop) stop.disabled = false;
            const live = participantList.querySelector(`.live-clock[data-nickname-id="${nid}"]`);
            if (live) { live.style.display = 'inline-block'; live.textContent = formatMMSS(0); }
          }
        });
      }
      statusEl.textContent = 'Timing started.';
    }
    if (stopBtn) {
      const id = parseInt(stopBtn.dataset.nicknameId, 10);
      const startTime = timers[id];
      if (startTime) {
        const elapsed = Date.now() - startTime;
  const seconds = formatSeconds(elapsed);
  recorded[id] = seconds;
  // Place the time into the UI span (MM:SS)
  const span = participantList.querySelector(`.time-display[data-nickname-id="${id}"]`);
  if (span) span.textContent = formatMMSS(seconds);
        // hide live clock
        const live = participantList.querySelector(`.live-clock[data-nickname-id="${id}"]`);
        if (live) live.style.display = 'none';
        // reset buttons
        const start = stopBtn.closest('div').querySelector('.start-btn');
        if (start) { start.disabled = false; start.classList.remove('btn-success'); start.classList.add('btn-outline-success'); }
        stopBtn.disabled = true;
        delete timers[id];
        statusEl.textContent = `Recorded ${formatMMSS(seconds)} for participant ${id}.`;
        recalcStandings();
      }
    }
  });

  // Reset and Manual Set handlers
  participantList.addEventListener('click', (e) => {
    const resetBtn = e.target.closest('.reset-btn');
    const manualBtn = e.target.closest('.manual-set-btn');
    if (resetBtn) {
      // open reset confirmation modal
      resetTargetId = parseInt(resetBtn.dataset.nicknameId, 10);
      const resetModal = new bootstrap.Modal(resetConfirmModalEl);
      resetModal.show();
    }
    if (manualBtn) {
      // open manual set modal and remember target
      manualTargetId = parseInt(manualBtn.dataset.nicknameId, 10);
      manualSetMinutes.value = '';
      manualSetSeconds.value = '';
      manualSetError.style.display = 'none';
      const manualModal = new bootstrap.Modal(manualSetModalEl);
      manualModal.show();
    }
  });

  // Manual set confirm handler (MM:SS)
  manualSetConfirm.addEventListener('click', () => {
    const minVal = parseInt(manualSetMinutes.value, 10);
    const secVal = parseInt(manualSetSeconds.value, 10);
    if (Number.isNaN(minVal) || Number.isNaN(secVal) || minVal < 0 || secVal < 0 || secVal >= 60) {
      manualSetError.textContent = 'Enter valid minutes and seconds (0-59).';
      manualSetError.style.display = 'block';
      return;
    }
    const totalSeconds = (minVal * 60) + secVal;
    if (manualTargetId === null) return;
    recorded[manualTargetId] = totalSeconds;
    const span = participantList.querySelector(`.time-display[data-nickname-id="${manualTargetId}"]`);
    if (span) span.textContent = formatMMSS(totalSeconds);
    // stop any running timer
    if (timers[manualTargetId]) delete timers[manualTargetId];
    const live = participantList.querySelector(`.live-clock[data-nickname-id="${manualTargetId}"]`);
    if (live) live.style.display = 'none';
    statusEl.textContent = `Set ${formatMMSS(totalSeconds)} for participant ${manualTargetId}.`;
    recalcStandings();
    stopClockIntervalIfIdle();
    // hide modal
    const manualModal = bootstrap.Modal.getInstance(manualSetModalEl);
    if (manualModal) manualModal.hide();
    manualTargetId = null;
  });

  // Reset confirm handler
  resetConfirmBtn.addEventListener('click', async () => {
    if (resetTargetId === null) return;
    const id = resetTargetId;
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      const resp = await fetch(`${window.location.pathname}api/delete_running/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ nickname_id: id })
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || 'Delete failed');
      // update UI
      if (timers[id]) delete timers[id];
      delete recorded[id];
      const span = participantList.querySelector(`.time-display[data-nickname-id="${id}"]`);
      if (span) span.textContent = '-';
      const live = participantList.querySelector(`.live-clock[data-nickname-id="${id}"]`);
      if (live) live.style.display = 'none';
      statusEl.textContent = `Reset timer for participant ${id}.`;
      recalcStandings();
      stopClockIntervalIfIdle();
    } catch (err) {
      console.error('Delete running result failed', err);
      statusEl.textContent = 'Failed to reset on server.';
    }
    const resetModal = bootstrap.Modal.getInstance(resetConfirmModalEl);
    if (resetModal) resetModal.hide();
    resetTargetId = null;
  });

  // Live clock updater: updates visible .live-clock spans for active timers
  function startClockInterval() {
    if (clockInterval) return;
    clockInterval = setInterval(() => {
      Object.entries(timers).forEach(([id, startTs]) => {
        const live = participantList.querySelector(`.live-clock[data-nickname-id="${id}"]`);
        if (!live) return;
        const elapsed = Date.now() - startTs;
        live.textContent = formatMMSS(formatSeconds(elapsed));
      });
    }, 1000); // update once per second is enough for MM:SS
  }
  function stopClockIntervalIfIdle() {
    if (Object.keys(timers).length === 0 && clockInterval) {
      clearInterval(clockInterval);
      clockInterval = null;
    }
  }

  // Ensure clock interval runs whenever timers are non-empty
  const origStartHandler = startClockInterval;
  // start interval when any start action is taken
  ['click'].forEach(evt => participantList.addEventListener(evt, startClockInterval));
  // stop interval check after stop actions (also on save reload)
  participantList.addEventListener('click', stopClockIntervalIfIdle);

  // Handle move up/down clicks in the standings
  standingsBody.addEventListener('click', (e) => {
    const up = e.target.closest('.move-up');
    const down = e.target.closest('.move-down');
    if (!up && !down) return;
    const tr = e.target.closest('tr');
    if (!tr) return;
    const time = parseInt(tr.getAttribute('data-time'), 10);
    if (up) {
      const prev = tr.previousElementSibling;
      if (prev) {
        const prevTime = parseInt(prev.getAttribute('data-time'), 10);
        if (prevTime === time) {
          prev.parentNode.insertBefore(tr, prev);
        }
      }
    }
    if (down) {
      const next = tr.nextElementSibling;
      if (next) {
        const nextTime = parseInt(next.getAttribute('data-time'), 10);
        if (nextTime === time) {
          next.parentNode.insertBefore(next, tr);
        }
      }
    }
    // recompute manual order from DOM and reattach controls
    manualOrder = Array.from(standingsBody.querySelectorAll('tr')).map(r => parseInt(r.getAttribute('data-nickname-id'), 10));
    attachRunningMoveControls();
  });

  function attachRunningMoveControls() {
    const trs = Array.from(standingsBody.querySelectorAll('tr'));
    trs.forEach((tr, i) => {
      const time = parseInt(tr.getAttribute('data-time'), 10);
      const controls = tr.querySelector('.order-controls');
      if (!controls) return;
      controls.innerHTML = '';
      if (i > 0) {
        const prev = trs[i-1];
        const prevTime = parseInt(prev.getAttribute('data-time'), 10);
        if (prevTime === time) {
          const up = document.createElement('button');
          up.className = 'btn btn-sm btn-light move-up me-1';
          up.textContent = '▲';
          controls.appendChild(up);
        }
      }
      if (i < trs.length - 1) {
        const next = trs[i+1];
        const nextTime = parseInt(next.getAttribute('data-time'), 10);
        if (nextTime === time) {
          const down = document.createElement('button');
          down.className = 'btn btn-sm btn-light move-down';
          down.textContent = '▼';
          controls.appendChild(down);
        }
      }
    });
  }

  // Save results: send recorded times to the API for persistence
  saveBtn.addEventListener('click', async () => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) { statusEl.textContent = 'CSRF missing; cannot save.'; return; }
    const payloads = [];
    for (const [id, time] of Object.entries(recorded)) {
      payloads.push({ nickname_id: parseInt(id,10), time_seconds: time });
    }
    if (payloads.length === 0) { statusEl.textContent = 'No times to save.'; return; }

    statusEl.textContent = 'Saving...';
    try {
      for (const p of payloads) {
        const resp = await fetch(`${window.location.pathname}api/record_running/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(p)
        });
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || 'Save failed');
      }
      // If user reordered tied rows, persist manual ordering for running (activity_id=4)
      if (manualOrder && manualOrder.length > 0) {
        const resp2 = await fetch(`${window.location.pathname}api/set_manual_order/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ activity_id: 4, order: manualOrder })
        });
        const data2 = await resp2.json();
        if (!data2.success) throw new Error(data2.error || 'Failed to persist manual order');
      }
      statusEl.textContent = 'Saved.';
      // After saving, reload standings from server by reloading page or by
      // triggering update functions. For simplicity, reload.
      window.location.reload();
    } catch (err) {
      console.error('Error saving running results', err);
      statusEl.textContent = 'Error saving results.';
    }
  });

  // Initial standings render
  recalcStandings();
});

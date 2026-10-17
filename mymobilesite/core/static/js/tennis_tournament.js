document.addEventListener('DOMContentLoaded', () => {
    // Get the container for our data attributes
    const tournamentData = document.getElementById('tournament-data');
    if (!tournamentData) {
      console.error('Tournament data element not found!');
      return;
    }

    const finalTable = document.getElementById('final-standing');
    const standingsColumns = [
      { key: 'wins', cellClass: 'wins-cell', emphasize: true },
      { key: 'losses', cellClass: 'losses-cell' }
    ];
    Scoreboard.attachMoveControls(finalTable, { movement: 'ties' });
  
    // Save tiebreaks button: save the current standings order for tiebreak resolution
    const saveTiebreaksBtn = document.getElementById('save-tiebreaks-btn');
    if (saveTiebreaksBtn) {
      saveTiebreaksBtn.addEventListener('click', async () => {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const statusEl = document.getElementById('tiebreaks-status');
        if (!csrfToken) {
          if (statusEl) statusEl.textContent = 'CSRF token not found; cannot save tiebreaks.';
          return;
        }
        const finalTable = document.getElementById('final-standing');
        const tbody = finalTable ? finalTable.querySelector('tbody') : document.getElementById('standings-body');
        if (!tbody) {
          if (statusEl) statusEl.textContent = 'Standings table not found.';
          return;
        }
        const order = Array.from(tbody.querySelectorAll('tr')).map(r => parseInt(r.getAttribute('data-nickname-id'), 10));
        if (!order.length) {
          if (statusEl) statusEl.textContent = 'No standings to save.';
          return;
        }
        try {
          const response = await fetch(`${window.location.pathname}api/set_manual_order/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ activity_id: 1, order: order })
          });
          const data = await response.json();
          if (data.success) {
            if (statusEl) statusEl.textContent = 'Tiebreaks lagret!';
          } else {
            if (statusEl) statusEl.textContent = 'Error: ' + (data.error || 'Unknown error');
          }
        } catch (err) {
          console.error('Error saving tiebreaks:', err);
          if (statusEl) statusEl.textContent = 'Network error: ' + err;
        }
      });
    }
  
    // Read the URL from the data attribute
    const recordMatchUrl = tournamentData.dataset.recordMatchUrl;
    const winnerButtons = document.querySelectorAll('.winner-btn');
    const saveBtn = document.getElementById('save-results-btn');

    function syncWinnerState(matchButtons, winnerId) {
      matchButtons.forEach(b => {
        const isWinner = Number(b.dataset.winnerId) === Number(winnerId);

        b.classList.remove('btn-success', 'btn-outline-primary');
        b.classList.remove('btn-outline-secondary');

        if (isWinner) {
          b.classList.add('btn-success');
          b.setAttribute('aria-pressed', 'true');
          b.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
          b.style.border = '2px solid #10b981';
          b.style.color = '#fff';
        } else {
          b.classList.add('btn-outline-primary');
          b.setAttribute('aria-pressed', 'false');
          b.style.background = '';
          b.style.border = '2px solid #e5e7eb';
          b.style.color = '#374151';
        }

        b.classList.add('winner-updated');
        setTimeout(() => b.classList.remove('winner-updated'), 300);
      });
    }
    
    winnerButtons.forEach(button => {
      button.addEventListener('click', (event) => {
        const btn = event.currentTarget;
        const { player1Id, player2Id, winnerId } = btn.dataset;
        const matchButtons = btn.parentElement ? btn.parentElement.querySelectorAll('.winner-btn') : [btn];

        syncWinnerState(matchButtons, winnerId);

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    if (!csrfToken) {
      const statusEl = document.getElementById('save-status');
      if (statusEl) statusEl.textContent = 'CSRF token not found; cannot record match now.';
      console.error('CSRF token input field is missing from the page.');
      return;
    }
  
        fetch(recordMatchUrl, { // Use the URL we read from the HTML
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            player1_id: player1Id,
            player2_id: player2Id,
            winner_id: winnerId
          })
        })
        .then(response => {
          if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data.success) {
            syncWinnerState(matchButtons, winnerId);
          } else {
            const statusEl = document.getElementById('save-status');
            if (statusEl) statusEl.textContent = `Error recording match: ${data.error}`;
            console.error('Error recording match:', data.error);
          }
        })
        .catch(error => {
          const statusEl = document.getElementById('save-status');
          if (statusEl) statusEl.textContent = 'Network error while recording match.';
          console.error('Fetch error:', error);
        });
      });
    });

    // Save results button: gather all declared winners and persist them,
    // then update the standings table in-place.
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const statusEl = document.getElementById('save-status');
        if (!csrfToken) {
          if (statusEl) statusEl.textContent = 'CSRF token not found; cannot save results.';
          return;
        }

        // Collect unique canonical matches that have a selected winner
        const declared = {};
        document.querySelectorAll('.winner-btn.btn-success').forEach(b => {
          const p1 = parseInt(b.dataset.player1Id, 10);
          const p2 = parseInt(b.dataset.player2Id, 10);
          const player1Id = Math.min(p1, p2);
          const player2Id = Math.max(p1, p2);
          const winnerId = parseInt(b.dataset.winnerId, 10);
          const key = `${player1Id}-${player2Id}`;
          declared[key] = { player1_id: player1Id, player2_id: player2Id, winner_id: winnerId };
        });

        if (Object.keys(declared).length === 0) {
          if (statusEl) statusEl.textContent = 'No declared winners to save.';
          return;
        }

        // Send each declared match to the record endpoint sequentially and collect standings
        let latestStandings = null;
        try {
          for (const key of Object.keys(declared)) {
            const payload = declared[key];
            const response = await fetch(recordMatchUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
              },
              body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Unknown error');
            latestStandings = data.standings || latestStandings;
          }

          // Update standings table if we received standings
          if (latestStandings) {
            if (finalTable) {
              Scoreboard.renderRows(finalTable, latestStandings.map(standing => ({
                id: standing.id,
                name: standing.name,
                tieValue: standing.wins,
                metrics: { wins: standing.wins, losses: standing.losses }
              })), standingsColumns);
              Scoreboard.attachMoveControls(finalTable, { movement: 'ties' });
            }
            if (statusEl) statusEl.textContent = 'Kampresultater lagret. Lagre Tiebreaks for å lagre rekkefølgen.';
          } else {
            if (statusEl) statusEl.textContent = 'Results saved. Refresh the page to see updated standings.';
          }
        } catch (err) {
          console.error('Error saving results:', err);
          if (statusEl) statusEl.textContent = 'Error saving results: ' + err;
        }
      });
    }
  });
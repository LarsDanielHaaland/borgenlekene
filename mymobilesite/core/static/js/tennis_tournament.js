document.addEventListener('DOMContentLoaded', () => {
    // Get the container for our data attributes
    const tournamentData = document.getElementById('tournament-data');
    if (!tournamentData) {
      console.error('Tournament data element not found!');
      return;
    }
  
    // Read the URL from the data attribute
    const recordMatchUrl = tournamentData.dataset.recordMatchUrl;
    const winnerButtons = document.querySelectorAll('.winner-btn');
    const saveBtn = document.getElementById('save-results-btn');
    
    winnerButtons.forEach(button => {
      button.addEventListener('click', (event) => {
        const btn = event.currentTarget;
        const { player1Id, player2Id, winnerId } = btn.dataset;
        
        // Get CSRF token. This requires a {% csrf_token %} to be present somewhere
        // on the rendered page, usually inside a <form>.
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
            // On success, update the two buttons for this match in-place so
            // the players don't jump positions. Find sibling buttons that
            // share the same player1/player2 data attributes and toggle
            // classes so the declared winner becomes green.
            // Match buttons can be rendered with player1/player2 in either
            // order in the markup, so select both permutations to update
            const selectorA = `.winner-btn[data-player1-id="${player1Id}"][data-player2-id="${player2Id}"]`;
            const selectorB = `.winner-btn[data-player1-id="${player2Id}"][data-player2-id="${player1Id}"]`;
            const matchButtons = document.querySelectorAll(`${selectorA}, ${selectorB}`);
            matchButtons.forEach(b => {
              const bid = b.dataset.winnerId;
              if (bid === winnerId) {
                b.classList.remove('btn-outline-primary');
                b.classList.add('btn-success');
                b.setAttribute('aria-pressed', 'true');
                b.classList.add('winner-updated');
                setTimeout(() => b.classList.remove('winner-updated'), 300);
              } else {
                b.classList.remove('btn-success');
                b.classList.add('btn-outline-primary');
                b.setAttribute('aria-pressed', 'false');
                b.classList.add('winner-updated');
                setTimeout(() => b.classList.remove('winner-updated'), 300);
              }
            });

            // Also update the standings area by fetching a fragment or
            // simply notifying the user. For simplicity we update the button
            // states only; the user can refresh the page to see updated
            // standings, or we can implement a small AJAX refresher later.
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
            const tbody = document.getElementById('standings-body');
            tbody.innerHTML = '';
            latestStandings.forEach((s, idx) => {
              const tr = document.createElement('tr');
              tr.innerHTML = `
                <th scope="row">${idx + 1}</th>
                <td>${s.name}</td>
                <td>${s.wins}</td>
                <td>${s.losses}</td>
              `;
              tbody.appendChild(tr);
            });
            if (statusEl) statusEl.textContent = 'Results saved and standings updated.';
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
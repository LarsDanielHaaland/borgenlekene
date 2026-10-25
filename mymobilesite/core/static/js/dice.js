// Minimal Dice game JS: allow reordering the final table and save final order via page-prefixed API
(function(){
  function $(s, root=document){ return root.querySelector(s); }
  function $all(s, root=document){ return Array.from(root.querySelectorAll(s)); }

  const finalTable = $('#final-standing');
  const finalData = JSON.parse(document.getElementById('final-data').textContent || '[]');
  const eventDiv = document.getElementById('dice-data');
  const ACTIVITY_ID = eventDiv.dataset.activityId;

  function applySavedFinal(){
    if(finalData && finalData.length){
      const tbody = finalTable.querySelector('tbody');
      const map = {};
      $all('tbody tr', finalTable).forEach(r => map[parseInt(r.dataset.nicknameId, 10)] = r);
      tbody.innerHTML = '';
      finalData.forEach(id => { if(map[id]) tbody.appendChild(map[id]); });
      Object.values(map).forEach(r => { if(!finalData.includes(parseInt(r.dataset.nicknameId, 10))) tbody.appendChild(r); });
      $all('tbody tr', finalTable).forEach((r,i)=> r.querySelector('.rank-cell').textContent = i+1);
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    applySavedFinal();
    Scoreboard.attachDragAndDrop(finalTable, {
      movement: 'free',
      saveOrder: (table, order) => saveManualOrder(ACTIVITY_ID, table, null, order)
    });
  });
})();

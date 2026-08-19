// Minimal Dice game JS: allow reordering the final table and save final order via page-prefixed API
(function(){
  function $(s, root=document){ return root.querySelector(s); }
  function $all(s, root=document){ return Array.from(root.querySelectorAll(s)); }

  const finalTable = $('#final-standing');
  const saveBtn = $('#save-final');
  const finalData = JSON.parse(document.getElementById('final-data').textContent || '[]');
  const eventDiv = document.getElementById('dice-data');
  const ACTIVITY_ID = eventDiv.dataset.activityId;

  function attachRowControls(table){
    // use shared attachMoveControls which delegates and calls the onMove callback
    attachMoveControls(table, (t) => { $all('tbody tr', t).forEach((r,i)=> r.querySelector('.rank-cell').textContent = i+1); });
  }

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

  function getOrder(){ return $all('tbody tr', finalTable).map(r => parseInt(r.dataset.nicknameId, 10)); }

  function postOrder(order){
    // use shared saveManualOrder helper
    return saveManualOrder(ACTIVITY_ID, finalTable, null);
  }

  // use shared showNotification

  document.addEventListener('DOMContentLoaded', function(){
    attachRowControls(finalTable);
    applySavedFinal();
    saveBtn.addEventListener('click', function(){
      postOrder(getOrder()).then(data => { if(data.success) showNotification('Saved','success'); else showNotification('Save failed: ' + (data.error||JSON.stringify(data)),'error'); }).catch(e=>showNotification('Network error: '+e,'error'));
    });
  });
})();

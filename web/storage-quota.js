/* Read-only storage quota badge. No OAuth IDs, S3 keys or tenant names in UI. */
(function(){
  'use strict';
  const box=document.getElementById('storageQuota');
  const line=document.getElementById('storageQuotaText');
  const meter=document.getElementById('storageQuotaBar');
  if(!box||!line||!meter)return;
  function gb(bytes){ return (bytes/1e9).toLocaleString(undefined,{maximumFractionDigits:1}); }
  function render(data){
    const nums=['quota_bytes','used_bytes','reserved_bytes','available_bytes'];
    if(!data||nums.some(k=>!Number.isSafeInteger(data[k])||data[k]<0)||
       data.quota_bytes<=0||data.used_bytes+data.reserved_bytes+data.available_bytes!==data.quota_bytes){
      throw new Error('unavailable quota');
    }
    const percent=100*(data.used_bytes+data.reserved_bytes)/data.quota_bytes;
    line.textContent=`${gb(data.used_bytes)} / ${gb(data.quota_bytes)} GB · ${gb(data.available_bytes)} GB available`;
    meter.value=Math.min(100,Math.max(0,percent));
    // Fill-level color: muted green at low usage, Montara orange at capacity.
    // Keep the color proportional to current occupancy, not a static rainbow.
    const mix=Math.min(1,Math.max(0,percent/100));
    const start=[123,173,139], end=[255,79,46];
    const rgb=start.map((channel,i)=>Math.round(channel+(end[i]-channel)*mix));
    meter.style.setProperty('--storage-fill',`rgb(${rgb.join(',')})`);
    meter.setAttribute('aria-label','Storage used and reserved');
    box.dataset.status='ready';
    box.title=`Storage: ${gb(data.used_bytes)} GB used, ${gb(data.reserved_bytes)} GB reserved, ${gb(data.available_bytes)} GB available`;
  }
  async function refresh(){
    try{
      const res=await fetch('/api/v1/storage/quota',{method:'GET',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
      if(!res.ok)throw new Error('quota unavailable');
      render(await res.json());
    }catch(_e){
      box.dataset.status='unavailable';
      box.title='Cloud storage quota is not connected for this account yet.';
      line.textContent='Cloud storage: not connected';
      meter.removeAttribute('value');
    }
  }
  refresh();
  document.addEventListener('montara:upload-finished',refresh);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
})();

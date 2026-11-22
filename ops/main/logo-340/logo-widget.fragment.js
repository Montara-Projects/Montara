async function loadBranding() {
  try {
    const data = await api("/montara/branding");
    state.branding = data.mode;
    state.hasLogo = Boolean(data.has_logo);
    const radio = document.querySelector(`input[name=branding][value="${data.mode}"]`);
    if (radio) radio.checked = true;
    if (data.has_logo) await showLogoPreview();
    renderFiles();
  } catch (error) { console.warn('Could not load branding', error); }
}
async function showLogoPreview() {
  const img = $("#myLogoPreview");
  const response = await fetch(`/montara/logo?t=${Date.now()}`, {cache:'no-store'});
  if (!response.ok) throw new Error('The saved logo could not be loaded. Choose it again.');
  const blob = await response.blob();
  if (!blob.size || !/^image\/(png|jpeg|webp)$/.test(blob.type))
    throw new Error('The saved logo is not a valid image. Choose it again.');
  const url = URL.createObjectURL(blob);
  await new Promise((resolve,reject)=>{
    const check=new Image();
    check.onload=resolve;
    check.onerror=()=>reject(new Error('The saved logo is not a readable image.'));
    check.src=url;
  }).catch(error=>{URL.revokeObjectURL(url);throw error;});
  if (img.dataset.logoUrl) URL.revokeObjectURL(img.dataset.logoUrl);
  img.src=img.dataset.logoUrl=url;
  img.hidden=false;
  $("#pickLogo").textContent="Change logo";
}
$$("input[name=branding]").forEach((radio)=>radio.addEventListener("change",()=>{
  state.branding=radio.value;
  if (radio.value==="mine" && !state.hasLogo) $("#logoInput").click();
  renderFiles();
}));
$("#pickLogo").addEventListener("click",(event)=>{
  event.preventDefault();
  $("#logoInput").click();
});
$("#logoInput").addEventListener("change",async(event)=>{
  const file=event.target.files[0];
  event.target.value="";
  if (!file)return;
  if (file.size > 9*1024*1024) {
    toast('Choose a logo smaller than 9 MiB.',true);
    return;
  }
  const button=$("#pickLogo");
  button.disabled=true;
  button.textContent='Saving logo…';
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),45000);
  try {
    const body=new FormData();body.append('file',file);
    const response=await fetch('/montara/logo',{method:'POST',body,signal:controller.signal});
    const result=await response.json().catch(()=>({}));
    if (!response.ok)
      throw new Error(result.error?.message || result.error || 'Logo upload failed ('+response.status+').');
    await showLogoPreview();
    state.hasLogo=true;
    state.branding='mine';
    document.querySelector('input[name=branding][value="mine"]').checked=true;
    toast('Logo saved. Continue is available.');
  } catch(error) {
    toast(error.name==='AbortError'?'Logo upload timed out. Retry the same image.':error.message || 'Logo upload failed.',true);
  } finally {
    clearTimeout(timeout);
    button.disabled=false;
    if (!state.hasLogo) button.textContent='Choose logo';
    renderFiles();
  }
});

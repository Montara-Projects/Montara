(() => {
  'use strict';
  const base = '/urano/v1/companion/';
  const embedded = document.getElementById('montara-companion-pilot');
  const panel = embedded || document.querySelector('main');
  const element = id => panel.querySelector('#' + (embedded ? 'montara-pilot-' : '') + id);
  let csrf;
  let job;
  let requestId;
  let starting = false;
  let invitationTimer;
  let refreshRunning = false;

  async function request(route, method = 'GET', body) {
    const headers = {};
    if (method !== 'GET') {
      if (window.montaraCompanionPilotCsrf) csrf = await window.montaraCompanionPilotCsrf();
      if (!csrf) {
        const response = await fetch('/urano/v1/session/refresh', {method:'POST', cache:'no-store'});
        if (!response.ok) throw new Error('Vuelve a iniciar sesión.');
        csrf = (await response.json()).csrf;
      }
      headers['X-Urano-CSRF'] = csrf;
    }
    if (body) headers['Content-Type'] = 'application/json';
    const response = await fetch(base + route, {method, headers, cache:'no-store',
      body: body && JSON.stringify(body)});
    if (response.status === 403) csrf = undefined;
    if (!response.ok) throw new Error('La operación no se completó. Comprueba la sesión y vuelve a intentarlo.');
    return response.status === 204 ? null : response.json();
  }

  function hideCode() {
    clearTimeout(invitationTimer);
    element('pairing').hidden = true;
    element('code').value = '';
  }

  function options(select, rows) {
    const current = select.value;
    select.replaceChildren(...rows.map(([id, name]) => new Option(name, id)));
    if (rows.some(row => row[0] === current)) select.value = current;
  }

  async function refresh() {
    if (refreshRunning) return;
    refreshRunning = true;
    try {
      const data = await request('devices');
      options(element('device'), data.online.map(id => [id, 'Companion · ' + id.slice(-6)]));
      element('connection').textContent = data.online.length ? 'Companion conectado' :
        (element('pairing').hidden ? 'Companion no conectado' : 'Esperando autorización de Companion');
      if (data.online.length) hideCode();
      element('devices').replaceChildren(...data.online.map(id => {
        const button = document.createElement('button');
        button.textContent = 'Revocar Companion · ' + id.slice(-6);
        button.onclick = async () => {
          try { await request('devices/' + id, 'DELETE'); await refresh(); }
          catch (error) { element('error').textContent = error.message; }
        };
        return button;
      }));
      if (job) {
        const status = await request(job);
        const messages = {pending:'En cola', running:'Renderizando', ready:'MP4 listo',
          cancelled:'Render cancelado', expired:'Trabajo caducado', failed:'Render fallido'};
        element('state').textContent = messages[status.state] || 'Estado desconocido';
        element('progress').value = status.progress;
        const active = ['pending', 'running'].includes(status.state);
        element('cancel').hidden = !active;
        element('download').hidden = status.state !== 'ready';
        if (status.state === 'ready') element('download').href = base + job + '/result';
        else element('download').removeAttribute('href');
        if (!active) job = undefined;
      }
      element('start').disabled = starting || Boolean(job) || !data.online.length || !element('project').value;
    } catch (error) {
      element('error').textContent = error.message;
    } finally { refreshRunning = false; }
  }

  element('connect').onclick = async () => {
    try {
      const result = await request('invite', 'POST', {});
      hideCode();
      element('code').value = result.code;
      element('pairing').hidden = false;
      invitationTimer = setTimeout(hideCode, result.expires_in * 1000);
      await refresh();
    } catch (error) { element('error').textContent = error.message; }
  };
  element('hide-code').onclick = hideCode;
  element('render').onsubmit = async event => {
    event.preventDefault();
    if (starting || job) return;
    starting = true;
    element('start').disabled = true;
    const project = element('project').value;
    const device = element('device').value;
    const scope = project + '/' + device;
    if (requestId?.scope !== scope) requestId = {scope, id:crypto.randomUUID().replaceAll('-', '')};
    try {
      const created = await request('projects/' + project + '/jobs', 'POST',
        {device, request_id:requestId.id});
      requestId = undefined;
      job = 'projects/' + project + '/jobs/' + created.id;
      element('download').hidden = true;
    } catch (error) { element('error').textContent = error.message; }
    finally { starting = false; await refresh(); }
  };
  element('cancel').onclick = async () => {
    try { if (job) await request(job, 'DELETE'); await refresh(); }
    catch (error) { element('error').textContent = error.message; }
  };
  request('projects').then(rows => options(element('project'), rows.map(row => [row.id, row.title])))
    .then(refresh).catch(error => { element('error').textContent = error.message; });
  setInterval(refresh, 2500);
})();

const tokenInputEl   = document.getElementById('tokenInput');
const tokenFieldEl   = document.getElementById('tokenField');
const tokenInd       = document.getElementById('tokenIndicator');
const tokenHintEl    = document.getElementById('tokenHint');
const tokenChgBtn    = document.getElementById('tokenChangeBtn');
const errorEl        = document.getElementById('errorEl');
const statsEl        = document.getElementById('stats');
const tableWrap      = document.getElementById('tableWrap');
const tableBody      = document.getElementById('tableBody');
const emptyEl        = document.getElementById('emptyEl');
const statTotal      = document.getElementById('statTotal');
const statPermanent  = document.getElementById('statPermanent');
const statSize       = document.getElementById('statSize');
const cleanupCardEl  = document.getElementById('cleanupCard');
const triggerBtn     = document.getElementById('triggerBtn');
const histToggleBtn  = document.getElementById('historyToggleBtn');
const histWrap       = document.getElementById('cleanupHistoryWrap');
const histBody       = document.getElementById('cleanupHistoryBody');

const STORAGE_KEY = 'dropit_admin_token';
let historyVisible = false;

function fmtSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function asUtc(iso) {
  if (!iso) return null;
  const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
  return new Date(normalized);
}

function fmtUtc(iso) {
  const d = asUtc(iso);
  if (!d) return '—';
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
}

function getToken() {
  return localStorage.getItem(STORAGE_KEY) || '';
}

function showField(hint) {
  tokenFieldEl.style.display = '';
  tokenInd.style.display = 'none';
  if (hint) {
    tokenHintEl.textContent = hint;
    tokenHintEl.style.display = '';
  } else {
    tokenHintEl.style.display = 'none';
  }
}

function showIndicator() {
  tokenFieldEl.style.display = 'none';
  tokenInd.style.display = '';
  cleanupCardEl.classList.add('visible');
}

tokenInputEl.addEventListener('keydown', e => { if (e.key === 'Enter') tryConnect(); });
tokenInputEl.addEventListener('blur', () => { if (tokenInputEl.value.trim()) tryConnect(); });

tokenChgBtn.addEventListener('click', () => {
  localStorage.removeItem(STORAGE_KEY);
  tokenInputEl.value = '';
  showField();
  clearAll();
});

async function tryConnect() {
  const token = tokenInputEl.value.trim();
  if (!token) return;
  localStorage.setItem(STORAGE_KEY, token);
  await loadPages();
  await loadCleanupStatus();
}

async function loadPages() {
  const token = getToken();
  if (!token) return;
  errorEl.classList.remove('visible');

  try {
    const res = await fetch('/admin/pages', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 403 || res.status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      showField('Invalid admin token');
      clearAll();
      return;
    }
    if (!res.ok) throw new Error(`Error ${res.status}`);

    const pages = await res.json();
    showIndicator();
    renderTable(pages);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
}

function clearAll() {
  while (tableBody.firstChild) tableBody.removeChild(tableBody.firstChild);
  tableWrap.classList.remove('visible');
  statsEl.classList.remove('visible');
  emptyEl.classList.remove('visible');
  cleanupCardEl.classList.remove('visible');
  histWrap.classList.remove('visible');
  historyVisible = false;
  histToggleBtn.textContent = 'Show history';
}

function renderTable(pages) {
  while (tableBody.firstChild) tableBody.removeChild(tableBody.firstChild);
  tableWrap.classList.remove('visible');
  statsEl.classList.remove('visible');
  emptyEl.classList.remove('visible');

  let totalSize = 0;
  let permanentCount = 0;

  pages.forEach(p => {
    totalSize += p.file_size || 0;
    if (!p.expires_at) permanentCount++;
  });

  statTotal.textContent = pages.length;
  statPermanent.textContent = permanentCount;
  statSize.textContent = fmtSize(totalSize);
  statsEl.classList.add('visible');

  if (!pages.length) {
    emptyEl.classList.add('visible');
    return;
  }

  pages.forEach(p => {
    const tr = document.createElement('tr');

    const tdUrl = document.createElement('td');
    tdUrl.className = 'td-url';
    const a = document.createElement('a');
    a.href = p.url;
    a.textContent = p.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    tdUrl.appendChild(a);

    const tdFile = document.createElement('td');
    tdFile.className = 'td-filename';
    tdFile.textContent = p.filename || '—';

    const tdCreated = document.createElement('td');
    tdCreated.className = 'td-created';
    tdCreated.textContent = p.created_at ? fmtDate(p.created_at) : '—';

    const tdUp = document.createElement('td');
    tdUp.className = 'td-uploader';
    tdUp.textContent = p.token_hint;

    const tdExp = document.createElement('td');
    tdExp.className = p.expires_at ? 'td-expires' : 'td-expires permanent';
    tdExp.textContent = p.expires_at ? fmtDate(p.expires_at) : 'permanent';

    const tdSize = document.createElement('td');
    tdSize.className = 'td-size';
    tdSize.textContent = fmtSize(p.file_size || 0);

    const tdAct = document.createElement('td');
    const btn = document.createElement('button');
    btn.className = 'del-btn';
    btn.textContent = 'Delete';
    btn.addEventListener('click', () => deletePage(p.id, tr));
    tdAct.appendChild(btn);

    tr.appendChild(tdUrl);
    tr.appendChild(tdFile);
    tr.appendChild(tdCreated);
    tr.appendChild(tdUp);
    tr.appendChild(tdExp);
    tr.appendChild(tdSize);
    tr.appendChild(tdAct);
    tableBody.appendChild(tr);
  });

  tableWrap.classList.add('visible');
}

async function deletePage(id, tr) {
  const token = getToken();
  try {
    const res = await fetch(`/admin/pages/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    tr.remove();
    if (!tableBody.firstChild) {
      tableWrap.classList.remove('visible');
      emptyEl.classList.add('visible');
    }
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
}

function renderTriggeredBy(container, triggeredBy) {
  while (container.firstChild) container.removeChild(container.firstChild);
  if (!triggeredBy) return;
  const badge = document.createElement('span');
  badge.className = 'trigger-badge ' + (triggeredBy === 'scheduler' ? 'scheduler' : 'manual');
  badge.textContent = triggeredBy;
  container.appendChild(badge);
}

async function loadCleanupStatus() {
  const token = getToken();
  if (!token) return;
  try {
    const res = await fetch('/admin/cleanup/status', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const data = await res.json();

    const lastRun = data.last_run;
    document.getElementById('cleanupLastRun').textContent   = lastRun ? fmtUtc(lastRun.ran_at) : 'No runs yet';
    document.getElementById('cleanupDeletedCount').textContent = lastRun ? lastRun.deleted_count : '—';
    renderTriggeredBy(document.getElementById('cleanupTriggeredBy'), lastRun ? lastRun.triggered_by : null);
    document.getElementById('cleanupNextRun').textContent   = fmtUtc(data.next_run);
  } catch (_) {
    // cleanup status is non-critical — fail silently
  }
}

async function loadCleanupHistory() {
  const token = getToken();
  if (!token) return;
  try {
    const res = await fetch('/admin/cleanup/history', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const runs = await res.json();

    while (histBody.firstChild) histBody.removeChild(histBody.firstChild);

    runs.forEach(run => {
      const tr = document.createElement('tr');

      const tdTime = document.createElement('td');
      tdTime.textContent = fmtUtc(run.ran_at);

      const tdCount = document.createElement('td');
      tdCount.textContent = run.deleted_count;

      const tdBy = document.createElement('td');
      renderTriggeredBy(tdBy, run.triggered_by);

      tr.appendChild(tdTime);
      tr.appendChild(tdCount);
      tr.appendChild(tdBy);
      histBody.appendChild(tr);
    });
  } catch (_) {
    // fail silently
  }
}

triggerBtn.addEventListener('click', async () => {
  const token = getToken();
  triggerBtn.disabled = true;
  triggerBtn.textContent = 'Running…';
  errorEl.classList.remove('visible');
  try {
    const res = await fetch('/admin/cleanup/trigger', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    await loadCleanupStatus();
    if (historyVisible) await loadCleanupHistory();
    await loadPages();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  } finally {
    triggerBtn.disabled = false;
    triggerBtn.textContent = 'Run now';
  }
});

histToggleBtn.addEventListener('click', async () => {
  historyVisible = !historyVisible;
  if (historyVisible) {
    await loadCleanupHistory();
    histWrap.classList.add('visible');
    histToggleBtn.textContent = 'Hide history';
  } else {
    histWrap.classList.remove('visible');
    histToggleBtn.textContent = 'Show history';
  }
});

// Boot
const stored = localStorage.getItem(STORAGE_KEY);
if (stored) {
  tokenInputEl.value = stored;
  loadPages();
  loadCleanupStatus();
} else {
  showField();
}

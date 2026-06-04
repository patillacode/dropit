import { getToken as _getToken, showTokenField, showTokenIndicator } from '/static/js/token-shared.js';
import { showTokenModal, showConfirmModal } from '/static/js/token-modal.js';
import { fmtExpiry } from '/static/js/utils.js';

const tokenInputEl   = document.getElementById('tokenInput');
const tokenFieldEl   = document.getElementById('tokenField');
const tokenInd       = document.getElementById('tokenIndicator');
const tokenHintEl    = document.getElementById('tokenHint');
const tokenNameEl    = document.getElementById('tokenName');
const tokenChgBtn    = document.getElementById('tokenChangeBtn');
const tokenForm      = document.getElementById('tokenForm');
const usersCardEl    = document.getElementById('usersCard');
const usersBodyEl    = document.getElementById('usersBody');
const userCreateForm = document.getElementById('userCreateForm');
const newUserNameEl  = document.getElementById('newUserName');
const newUserAdminEl = document.getElementById('newUserAdmin');
const errorEl        = document.getElementById('errorEl');
const statsEl        = document.getElementById('stats');
const tableWrap      = document.getElementById('tableWrap');
const tableBody      = document.getElementById('tableBody');
const pagesSection   = document.getElementById('pagesSection');
const emptyEl        = document.getElementById('emptyEl');
const statTotal      = document.getElementById('statTotal');
const statPermanent  = document.getElementById('statPermanent');
const statSize       = document.getElementById('statSize');
const statUsers      = document.getElementById('statUsers');
const cleanupCardEl  = document.getElementById('cleanupCard');
const triggerBtn     = document.getElementById('triggerBtn');
const histToggleBtn  = document.getElementById('historyToggleBtn');
const histWrap       = document.getElementById('cleanupHistoryWrap');
const histBody       = document.getElementById('cleanupHistoryBody');

const STORAGE_KEY = 'dropit_token';
const _tokenEls = { fieldEl: tokenFieldEl, indicatorEl: tokenInd, hintEl: tokenHintEl };
let historyVisible = false;
let currentUserName = null;

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

function showIndicator() {
  showTokenIndicator(
    { fieldEl: tokenFieldEl, indicatorEl: tokenInd, nameEl: tokenNameEl },
    currentUserName || 'admin'
  );
  cleanupCardEl.classList.add('visible');
  usersCardEl.classList.add('visible');
}

tokenForm.addEventListener('submit', e => { e.preventDefault(); tryConnect(); });
tokenInputEl.addEventListener('blur', () => { if (tokenInputEl.value.trim()) tryConnect(); });

tokenChgBtn.addEventListener('click', () => {
  localStorage.removeItem(STORAGE_KEY);
  tokenInputEl.value = '';
  currentUserName = null;
  showTokenField(_tokenEls);
  clearAll();
});

async function tryConnect() {
  const token = tokenInputEl.value.trim();
  if (!token) return;
  localStorage.setItem(STORAGE_KEY, token);
  await connect();
}

async function connect() {
  const token = _getToken(STORAGE_KEY);
  if (!token) { showTokenField(_tokenEls); return; }
  errorEl.classList.remove('visible');
  let me;
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      showTokenField(_tokenEls, 'Invalid token');
      clearAll();
      return;
    }
    if (!res.ok) throw new Error(`Error ${res.status}`);
    me = await res.json();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
    return;
  }
  currentUserName = me.name;
  if (!me.is_admin) {
    showTokenField(_tokenEls, 'This token does not have admin access');
    clearAll();
    return;
  }
  showIndicator();
  await loadPages();
  await loadCleanupStatus();
  await loadUsers();
}

async function loadPages() {
  const token = _getToken(STORAGE_KEY);
  if (!token) return;
  errorEl.classList.remove('visible');

  try {
    const res = await fetch('/admin/pages', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 403 || res.status === 401) {
      showTokenField(_tokenEls, 'This token does not have admin access');
      clearAll();
      return;
    }
    if (!res.ok) throw new Error(`Error ${res.status}`);

    const pages = await res.json();
    renderTable(pages);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
}

function clearAll() {
  while (tableBody.firstChild) tableBody.removeChild(tableBody.firstChild);
  tableWrap.classList.remove('visible');
  pagesSection.classList.remove('visible');
  statsEl.classList.remove('visible');
  emptyEl.classList.remove('visible');
  cleanupCardEl.classList.remove('visible');
  usersCardEl.classList.remove('visible');
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
  pagesSection.classList.add('visible');

  if (!pages.length) {
    emptyEl.classList.add('visible');
    return;
  }

  pages.forEach(p => {
    const tr = document.createElement('tr');
    tr.className = 'page-row';

    const tdUrl = document.createElement('td');
    tdUrl.className = 'td-url';
    const a = document.createElement('a');
    a.href = p.url;
    a.textContent = p.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    tdUrl.appendChild(a);

    const tdExp = document.createElement('td');
    const { text: expText, cls: expCls } = fmtExpiry(p.expires_at);
    tdExp.className = `td-expires ${expCls}`;
    tdExp.textContent = expText;

    const tdUp = document.createElement('td');
    tdUp.className = 'td-uploader';
    tdUp.textContent = p.token_hint;

    const tdAct = document.createElement('td');
    tdAct.className = 'page-actions';

    const detailsBtn = document.createElement('button');
    detailsBtn.className = 'btn';
    detailsBtn.textContent = 'Details';

    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn--danger';
    delBtn.textContent = 'Delete';

    tdAct.appendChild(detailsBtn);
    tdAct.appendChild(delBtn);

    tr.appendChild(tdUrl);
    tr.appendChild(tdExp);
    tr.appendChild(tdUp);
    tr.appendChild(tdAct);

    const detailTr = document.createElement('tr');
    detailTr.className = 'page-detail';
    const detailTd = document.createElement('td');
    detailTd.colSpan = 4;
    const grid = document.createElement('div');
    grid.className = 'detail-grid';
    grid.appendChild(detailItem('File', p.filename || '—'));
    grid.appendChild(detailItem('Uploaded', p.created_at ? fmtDate(p.created_at) : '—'));
    grid.appendChild(detailItem('Expires', p.expires_at ? fmtDate(p.expires_at) : 'never'));
    grid.appendChild(detailItem('Size', fmtSize(p.file_size || 0)));
    detailTd.appendChild(grid);
    detailTr.appendChild(detailTd);

    detailsBtn.addEventListener('click', () => {
      const open = detailTr.classList.toggle('open');
      detailsBtn.textContent = open ? 'Hide' : 'Details';
    });
    delBtn.addEventListener('click', () => deletePage(p.id, tr, detailTr));

    tableBody.appendChild(tr);
    tableBody.appendChild(detailTr);
  });

  tableWrap.classList.add('visible');
}

function detailItem(key, value) {
  const item = document.createElement('div');
  item.className = 'detail-item';
  const k = document.createElement('span');
  k.className = 'detail-key';
  k.textContent = key;
  const v = document.createElement('span');
  v.className = 'detail-val';
  v.textContent = value;
  item.appendChild(k);
  item.appendChild(v);
  return item;
}

async function deletePage(id, tr, detailTr) {
  const token = _getToken(STORAGE_KEY);
  try {
    const res = await fetch(`/admin/pages/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    tr.remove();
    detailTr.remove();
    if (!tableBody.firstChild) {
      tableWrap.classList.remove('visible');
      emptyEl.classList.add('visible');
    }
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
}

async function loadUsers() {
  const token = _getToken(STORAGE_KEY);
  if (!token) return;
  try {
    const res = await fetch('/admin/users', { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    renderUsers(await res.json());
  } catch (_) {
    // non-critical
  }
}

function renderUsers(users) {
  statUsers.textContent = users.length;
  while (usersBodyEl.firstChild) usersBodyEl.removeChild(usersBodyEl.firstChild);
  users.forEach(u => {
    const tr = document.createElement('tr');

    const tdName = document.createElement('td');
    tdName.textContent = u.name;

    const tdAdmin = document.createElement('td');
    tdAdmin.textContent = u.is_admin ? 'yes' : '—';

    const tdCreated = document.createElement('td');
    tdCreated.textContent = u.created_at ? fmtDate(u.created_at) : '—';

    const tdAct = document.createElement('td');
    tdAct.className = 'user-actions';

    const regenBtn = document.createElement('button');
    regenBtn.className = 'btn';
    regenBtn.textContent = 'Regenerate';
    regenBtn.addEventListener('click', () => regenerateUser(u));
    tdAct.appendChild(regenBtn);

    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn--danger';
    delBtn.textContent = 'Delete';
    if (u.name === currentUserName) {
      delBtn.disabled = true;
      delBtn.title = 'You cannot delete yourself';
    } else {
      delBtn.addEventListener('click', () => deleteUser(u, tr));
    }
    tdAct.appendChild(delBtn);

    tr.appendChild(tdName);
    tr.appendChild(tdAdmin);
    tr.appendChild(tdCreated);
    tr.appendChild(tdAct);
    usersBodyEl.appendChild(tr);
  });
}

userCreateForm.addEventListener('submit', async e => {
  e.preventDefault();
  const name = newUserNameEl.value.trim();
  if (!name) return;
  const token = _getToken(STORAGE_KEY);
  errorEl.classList.remove('visible');
  try {
    const res = await fetch('/admin/users', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, is_admin: newUserAdminEl.checked }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
    newUserNameEl.value = '';
    newUserAdminEl.checked = false;
    showTokenModal(data.token, {
      title: `Token for ${data.name}`,
      subtitle: "Copy this token and hand it to the user — it won't be shown again.",
    });
    await loadUsers();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
});

async function regenerateUser(u) {
  const ok = await showConfirmModal({
    title: `Regenerate ${u.name}'s token?`,
    message: 'Their current token stops working immediately, everywhere it is used.',
    confirmLabel: 'Regenerate',
    danger: true,
  });
  if (!ok) return;
  const token = _getToken(STORAGE_KEY);
  errorEl.classList.remove('visible');
  try {
    const res = await fetch(`/admin/users/${u.id}/regenerate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
    // if an admin regenerated their own token, keep this session alive
    if (u.name === currentUserName) localStorage.setItem(STORAGE_KEY, data.token);
    showTokenModal(data.token, {
      title: `New token for ${u.name}`,
      subtitle: "Copy it now — it won't be shown again. The old token no longer works.",
    });
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  }
}

async function deleteUser(u, tr) {
  const ok = await showConfirmModal({
    title: `Delete user ${u.name}?`,
    message: 'Their uploaded pages are kept. This cannot be undone.',
    confirmLabel: 'Delete',
    danger: true,
  });
  if (!ok) return;
  const token = _getToken(STORAGE_KEY);
  errorEl.classList.remove('visible');
  try {
    const res = await fetch(`/admin/users/${u.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Error ${res.status}`);
    }
    tr.remove();
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
  const token = _getToken(STORAGE_KEY);
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
  const token = _getToken(STORAGE_KEY);
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
  const token = _getToken(STORAGE_KEY);
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
  connect();
} else {
  showTokenField(_tokenEls);
}

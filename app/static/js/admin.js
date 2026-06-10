import { apiFetch } from '/static/js/api.js';
import { clearToken, getToken, initNav, setToken } from '/static/js/auth.js';
import { renderPagesTable } from '/static/js/pages-table.js';
import { showConfirmModal, showTokenModal } from '/static/js/token-modal.js';
import { showTokenField, showTokenIndicator } from '/static/js/token-shared.js';
import { asUtc, fmtDate, fmtSize } from '/static/js/utils.js';

const tokenInputEl = document.getElementById('tokenInput');
const tokenFieldEl = document.getElementById('tokenField');
const tokenInd = document.getElementById('tokenIndicator');
const tokenHintEl = document.getElementById('tokenHint');
const tokenNameEl = document.getElementById('tokenName');
const tokenChgBtn = document.getElementById('tokenChangeBtn');
const tokenRegenBtn = document.getElementById('tokenRegenBtn');
const tokenForm = document.getElementById('tokenForm');
const usersCardEl = document.getElementById('usersCard');
const usersBodyEl = document.getElementById('usersBody');
const userCreateForm = document.getElementById('userCreateForm');
const newUserNameEl = document.getElementById('newUserName');
const newUserAdminEl = document.getElementById('newUserAdmin');
const errorEl = document.getElementById('errorEl');
const statsEl = document.getElementById('stats');
const tableWrap = document.getElementById('tableWrap');
const pagesSection = document.getElementById('pagesSection');
const emptyEl = document.getElementById('emptyEl');
const statTotal = document.getElementById('statTotal');
const statPermanent = document.getElementById('statPermanent');
const statSize = document.getElementById('statSize');
const statUsers = document.getElementById('statUsers');
const cleanupCardEl = document.getElementById('cleanupCard');
const triggerBtn = document.getElementById('triggerBtn');
const histToggleBtn = document.getElementById('historyToggleBtn');
const histWrap = document.getElementById('cleanupHistoryWrap');
const histBody = document.getElementById('cleanupHistoryBody');

const _tokenEls = { fieldEl: tokenFieldEl, indicatorEl: tokenInd, hintEl: tokenHintEl };
let historyVisible = false;
let currentUserName = null;

function fmtUtc(iso) {
  const d = asUtc(iso);
  if (!d) return '—';
  return `${d.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.add('visible');
}

function showIndicator() {
  showTokenIndicator(
    { fieldEl: tokenFieldEl, indicatorEl: tokenInd, nameEl: tokenNameEl },
    currentUserName || 'admin',
  );
  cleanupCardEl.classList.add('visible');
  usersCardEl.classList.add('visible');
}

tokenForm.addEventListener('submit', (e) => {
  e.preventDefault();
  tryConnect();
});

tokenChgBtn.addEventListener('click', () => {
  clearToken();
  tokenInputEl.value = '';
  currentUserName = null;
  showTokenField(_tokenEls);
  clearAll();
});

tokenRegenBtn.addEventListener('click', async () => {
  const ok = await showConfirmModal({
    title: 'Regenerate your token?',
    message: 'Your current token stops working everywhere immediately.',
    confirmLabel: 'Regenerate',
    danger: true,
  });
  if (!ok) return;
  try {
    const data = await apiFetch('/me/regenerate', { method: 'POST' });
    setToken(data.token);
    showTokenModal(data.token, {
      title: 'New token',
      subtitle: "Copy it now — it won't be shown again. The old token no longer works.",
    });
  } catch (err) {
    showError(err.message);
  }
});

async function tryConnect() {
  const token = tokenInputEl.value.trim();
  if (!token) return;
  await connect(token);
}

async function connect(tokenArg) {
  const token = tokenArg ?? getToken();
  if (!token) {
    showTokenField(_tokenEls);
    return;
  }
  errorEl.classList.remove('visible');
  let me;
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) {
      clearToken();
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
  setToken(token);
  showIndicator();
  await loadPages();
  await loadCleanupStatus();
  await loadUsers();
}

async function connectFromNav(user) {
  const token = getToken();
  if (!user.is_admin) {
    clearToken();
    showTokenField(_tokenEls, 'This token does not have admin access');
    clearAll();
    return;
  }
  tokenInputEl.value = token;
  currentUserName = user.name;
  showIndicator();
  await loadPages();
  await loadCleanupStatus();
  await loadUsers();
}

async function loadPages() {
  if (!getToken()) return;
  errorEl.classList.remove('visible');

  let pages;
  try {
    pages = await apiFetch('/admin/pages');
  } catch (err) {
    if (err.status === 401 || err.status === 403) {
      showTokenField(_tokenEls, 'This token does not have admin access');
      clearAll();
      return;
    }
    showError(err.message);
    return;
  }
  updateStats(pages);
  renderPagesTable(pages, {
    tableWrap,
    emptyEl,
    errorEl,
    showUploader: true,
    deletePage: deletePageFetch,
  });
  pagesSection.classList.add('visible');
}

function updateStats(pages) {
  let totalSize = 0;
  let permanentCount = 0;
  for (const p of pages) {
    totalSize += p.file_size || 0;
    if (!p.expires_at) permanentCount++;
  }
  statTotal.textContent = pages.length;
  statPermanent.textContent = permanentCount;
  statSize.textContent = fmtSize(totalSize);
  statsEl.classList.add('visible');
}

async function deletePageFetch(p) {
  await apiFetch(`/admin/pages/${encodeURIComponent(p.id)}`, { method: 'DELETE' });
}

function clearAll() {
  while (tableWrap.firstChild) tableWrap.removeChild(tableWrap.firstChild);
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

async function loadUsers() {
  if (!getToken()) return;
  try {
    renderUsers(await apiFetch('/admin/users'));
  } catch (_) {
    // non-critical
  }
}

function renderUsers(users) {
  statUsers.textContent = users.length;
  while (usersBodyEl.firstChild) usersBodyEl.removeChild(usersBodyEl.firstChild);
  users.forEach((u) => {
    const tr = document.createElement('tr');

    const tdName = document.createElement('td');
    tdName.dataset.label = 'Name';
    tdName.textContent = u.name;

    const tdAdmin = document.createElement('td');
    tdAdmin.dataset.label = 'Admin';
    tdAdmin.textContent = u.is_admin ? 'yes' : '—';

    const tdCreated = document.createElement('td');
    tdCreated.dataset.label = 'Created';
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

userCreateForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = newUserNameEl.value.trim();
  if (!name) return;
  errorEl.classList.remove('visible');
  try {
    const data = await apiFetch('/admin/users', {
      method: 'POST',
      json: { name, is_admin: newUserAdminEl.checked },
    });
    newUserNameEl.value = '';
    newUserAdminEl.checked = false;
    showTokenModal(data.token, {
      title: `Token for ${data.name}`,
      subtitle: "Copy this token and hand it to the user — it won't be shown again.",
    });
    await loadUsers();
  } catch (err) {
    showError(err.message);
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
  errorEl.classList.remove('visible');
  try {
    const data = await apiFetch(`/admin/users/${u.id}/regenerate`, { method: 'POST' });
    // if an admin regenerated their own token, keep this session alive
    if (u.name === currentUserName) setToken(data.token);
    showTokenModal(data.token, {
      title: `New token for ${u.name}`,
      subtitle: "Copy it now — it won't be shown again. The old token no longer works.",
    });
  } catch (err) {
    showError(err.message);
  }
}

async function deleteUser(u, tr) {
  const ok = await showConfirmModal({
    title: `Delete user ${u.name}?`,
    message: 'All their pages and collections will be permanently deleted. This cannot be undone.',
    confirmLabel: 'Delete',
    danger: true,
  });
  if (!ok) return;
  errorEl.classList.remove('visible');
  try {
    await apiFetch(`/admin/users/${u.id}`, { method: 'DELETE' });
    tr.remove();
  } catch (err) {
    showError(err.message);
  }
}

function renderTriggeredBy(container, triggeredBy) {
  while (container.firstChild) container.removeChild(container.firstChild);
  if (!triggeredBy) return;
  const badge = document.createElement('span');
  badge.className = `trigger-badge ${triggeredBy === 'scheduler' ? 'scheduler' : 'manual'}`;
  badge.textContent = triggeredBy;
  container.appendChild(badge);
}

async function loadCleanupStatus() {
  if (!getToken()) return;
  try {
    const data = await apiFetch('/admin/cleanup/status');

    const lastRun = data.last_run;
    document.getElementById('cleanupLastRun').textContent = lastRun
      ? fmtUtc(lastRun.ran_at)
      : 'No runs yet';
    document.getElementById('cleanupDeletedCount').textContent = lastRun
      ? lastRun.deleted_count
      : '—';
    renderTriggeredBy(
      document.getElementById('cleanupTriggeredBy'),
      lastRun ? lastRun.triggered_by : null,
    );
    document.getElementById('cleanupNextRun').textContent = fmtUtc(data.next_run);
  } catch (_) {
    // cleanup status is non-critical — fail silently
  }
}

async function loadCleanupHistory() {
  if (!getToken()) return;
  try {
    const runs = await apiFetch('/admin/cleanup/history');

    while (histBody.firstChild) histBody.removeChild(histBody.firstChild);

    runs.forEach((run) => {
      const tr = document.createElement('tr');

      const tdTime = document.createElement('td');
      tdTime.dataset.label = 'Ran at';
      tdTime.textContent = fmtUtc(run.ran_at);

      const tdCount = document.createElement('td');
      tdCount.dataset.label = 'Deleted';
      tdCount.textContent = run.deleted_count;

      const tdBy = document.createElement('td');
      tdBy.dataset.label = 'Triggered by';
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
  triggerBtn.disabled = true;
  triggerBtn.textContent = 'Running…';
  errorEl.classList.remove('visible');
  try {
    await apiFetch('/admin/cleanup/trigger', { method: 'POST' });
    await loadCleanupStatus();
    if (historyVisible) await loadCleanupHistory();
    await loadPages();
  } catch (err) {
    showError(err.message);
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
initNav({
  onLogin: connectFromNav,
  onLogout: () => {
    clearAll();
    showTokenField(_tokenEls);
  },
});
if (!getToken()) showTokenField(_tokenEls);

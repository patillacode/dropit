import { getToken, clearToken, initNav } from '/static/js/auth.js';
import { showConfirmModal, showInputModal } from '/static/js/token-modal.js';
import { fmtExpiry } from '/static/js/utils.js';

if (!getToken()) { window.location.href = '/'; }

let collections = [];
let activeFilter = 'all';

const errorEl      = document.getElementById('errorEl');
const tableBody    = document.getElementById('tableBody');
const tableWrap    = document.getElementById('tableWrap');
const emptyEl      = document.getElementById('emptyEl');
const panelTitle   = document.getElementById('panelTitle');
const sidebarColls = document.getElementById('sidebarColls');
const newCollForm  = document.getElementById('newCollForm');
const newCollName  = document.getElementById('newCollName');
const tokenIndicator = document.getElementById('tokenIndicator');
const tokenName    = document.getElementById('tokenName');
const tokenChangeBtn = document.getElementById('tokenChangeBtn');

tokenChangeBtn.addEventListener('click', () => {
  clearToken();
  window.location.href = '/';
});

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.style.display = msg ? '' : 'none';
}

async function loadCollections() {
  const res = await fetch('/collections', { headers: authHeaders() });
  if (res.status === 401) {
    sidebarColls.innerHTML = '';
    newCollForm.style.display = 'none';
    const hint = document.createElement('p');
    hint.className = 'token-hint';
    hint.style.padding = '0.25rem 0';
    hint.textContent = 'Collections unavailable with break-glass token. Create a DB user to use collections.';
    sidebarColls.appendChild(hint);
    return;
  }
  if (!res.ok) { showError('Failed to load collections'); return; }
  newCollForm.style.display = '';
  collections = await res.json();
  renderSidebar();
}

async function loadFiles() {
  let url = '/me/pages';
  let title = 'All files';
  if (activeFilter === 'uncollected') {
    url = '/me/pages?uncollected=true';
    title = 'Uncollected';
  } else if (typeof activeFilter === 'number') {
    const coll = collections.find(c => c.id === activeFilter);
    if (coll) {
      url = `/me/pages?collection=${encodeURIComponent(coll.name)}`;
      title = coll.name;
    }
  }
  panelTitle.textContent = title;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) { showError('Failed to load files'); return; }
  renderFiles(await res.json());
}

function renderSidebar() {
  document.querySelectorAll('.sidebar-filters .sidebar-btn').forEach(btn => {
    btn.classList.toggle('sidebar-btn--active', btn.dataset.filter === activeFilter);
  });

  sidebarColls.innerHTML = '';
  for (const coll of collections) {
    const row = document.createElement('div');
    row.className = 'sidebar-coll-row';

    const btn = document.createElement('button');
    btn.className = 'sidebar-btn sidebar-coll-btn' + (activeFilter === coll.id ? ' sidebar-btn--active' : '');
    const nameSpan = document.createElement('span');
    nameSpan.className = 'coll-name';
    nameSpan.textContent = coll.name;
    const countSpan = document.createElement('span');
    countSpan.className = 'coll-count';
    countSpan.textContent = coll.page_count;
    btn.append(nameSpan, countSpan);
    btn.addEventListener('click', () => { activeFilter = coll.id; renderSidebar(); loadFiles(); });

    const renameBtn = document.createElement('button');
    renameBtn.className = 'sidebar-icon-btn';
    renameBtn.title = 'Rename';
    renameBtn.textContent = '✎';
    renameBtn.addEventListener('click', e => { e.stopPropagation(); renameCollection(coll.id); });

    const delBtn = document.createElement('button');
    delBtn.className = 'sidebar-icon-btn sidebar-icon-btn--danger';
    delBtn.title = 'Delete';
    delBtn.textContent = '×';
    delBtn.addEventListener('click', e => { e.stopPropagation(); deleteCollection(coll.id); });

    row.append(btn, renameBtn, delBtn);
    sidebarColls.appendChild(row);
  }
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fmtSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
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
  item.append(k, v);
  return item;
}

function renderFiles(pages) {
  tableBody.innerHTML = '';
  showError('');
  if (!pages.length) {
    tableWrap.style.display = 'none';
    emptyEl.style.display = '';
    return;
  }
  tableWrap.style.display = '';
  emptyEl.style.display = 'none';

  for (const p of pages) {
    const pageId = new URL(p.url).hostname.split('.')[0];
    const expiry = fmtExpiry(p.expires_at);

    const tr = document.createElement('tr');
    tr.className = 'page-row';

    const tdFile = document.createElement('td');
    const a = document.createElement('a');
    a.href = p.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = p.filename || pageId;
    tdFile.appendChild(a);

    const tdColl = document.createElement('td');
    if (p.collection_name) {
      const badge = document.createElement('span');
      badge.className = 'coll-badge';
      badge.textContent = p.collection_name;
      tdColl.appendChild(badge);
    } else {
      tdColl.textContent = '—';
    }

    const tdExp = document.createElement('td');
    tdExp.className = expiry.cls;
    tdExp.textContent = expiry.text;

    const tdAct = document.createElement('td');
    const actDiv = document.createElement('div');
    actDiv.className = 'page-actions';

    const detailsBtn = document.createElement('button');
    detailsBtn.className = 'btn';
    detailsBtn.textContent = 'Details';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn';
    copyBtn.textContent = 'Copy URL';
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(p.url);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = 'Copy URL'; }, 1500);
      } catch { /* clipboard unavailable */ }
    });

    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn--danger';
    delBtn.textContent = 'Delete';

    actDiv.append(detailsBtn, copyBtn, delBtn);
    tdAct.appendChild(actDiv);
    tr.append(tdFile, tdColl, tdExp, tdAct);

    const detailTr = document.createElement('tr');
    detailTr.className = 'page-detail';
    const detailTd = document.createElement('td');
    detailTd.colSpan = 4;
    const grid = document.createElement('div');
    grid.className = 'detail-grid';
    grid.appendChild(detailItem('URL', p.url));
    grid.appendChild(detailItem('Expires', p.expires_at ? fmtDate(p.expires_at) : 'never'));
    if (p.collection_name) grid.appendChild(detailItem('Collection', p.collection_name));
    if (p.file_size) grid.appendChild(detailItem('Size', fmtSize(p.file_size)));
    detailTd.appendChild(grid);
    detailTr.appendChild(detailTd);

    detailsBtn.addEventListener('click', () => {
      const open = detailTr.classList.toggle('open');
      detailsBtn.textContent = open ? 'Hide' : 'Details';
    });
    delBtn.addEventListener('click', () => deleteFile(pageId, tr, detailTr));

    tableBody.appendChild(tr);
    tableBody.appendChild(detailTr);
  }
}

async function deleteFile(pageId, tr, detailTr) {
  const ok = await showConfirmModal({
    title: 'Delete file?',
    message: 'This will permanently remove the file and its public URL.',
    confirmLabel: 'Delete',
    danger: true,
  });
  if (!ok) return;
  const res = await fetch(`/me/pages/${pageId}`, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) { showError('Failed to delete file'); return; }
  tr.remove();
  detailTr.remove();
  if (!tableBody.querySelector('.page-row')) {
    tableWrap.style.display = 'none';
    emptyEl.style.display = '';
  }
  if (typeof activeFilter === 'number') {
    const coll = collections.find(c => c.id === activeFilter);
    if (coll) { coll.page_count = Math.max(0, coll.page_count - 1); renderSidebar(); }
  }
}

async function renameCollection(collId) {
  const coll = collections.find(c => c.id === collId);
  if (!coll) return;
  const name = await showInputModal({
    title: 'Rename collection',
    defaultValue: coll.name,
    confirmLabel: 'Rename',
  });
  if (!name || name === coll.name) return;
  const res = await fetch(`/collections/${collId}`, {
    method: 'PATCH',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) { showError('Failed to rename collection'); return; }
  await loadCollections();
  loadFiles();
}

async function deleteCollection(collId) {
  const ok = await showConfirmModal({
    title: 'Delete collection?',
    message: 'Files in this collection will become uncollected.',
    confirmLabel: 'Delete',
    danger: true,
  });
  if (!ok) return;
  const res = await fetch(`/collections/${collId}`, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) { showError('Failed to delete collection'); return; }
  if (activeFilter === collId) activeFilter = 'all';
  await loadCollections();
  loadFiles();
}

newCollForm.addEventListener('submit', async e => {
  e.preventDefault();
  const name = newCollName.value.trim();
  if (!name) return;
  const res = await fetch('/collections', {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    showError(data.detail || 'Failed to create collection');
    return;
  }
  newCollName.value = '';
  await loadCollections();
});

document.querySelectorAll('.sidebar-filters .sidebar-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    activeFilter = btn.dataset.filter;
    renderSidebar();
    loadFiles();
  });
});

initNav({
  onLogin(user) {
    tokenIndicator.style.display = '';
    tokenName.textContent = user.name;
    loadCollections();
    loadFiles();
  },
  onLogout() { window.location.href = '/'; },
});

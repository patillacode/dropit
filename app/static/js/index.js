import { showTokenField, showTokenIndicator } from '/static/js/token-shared.js';
import { showTokenModal, showConfirmModal, showNoticeModal } from '/static/js/token-modal.js';
import { asUtc, fmtExpiry } from '/static/js/utils.js';

const STORAGE_KEY = 'dropit_token';

const tokenInputEl   = document.getElementById('token');
const tokenFieldEl   = document.getElementById('tokenField');
const tokenIndicator = document.getElementById('tokenIndicator');
const tokenNameEl    = document.getElementById('tokenName');
const tokenHintEl    = document.getElementById('tokenHint');
const tokenChangeBtn = document.getElementById('tokenChangeBtn');
const tokenRegenBtn  = document.getElementById('tokenRegenBtn');
const tokenForm      = document.getElementById('tokenForm');
const ttlSelect      = document.getElementById('ttl');
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const dzUrl          = document.getElementById('dzUrl');
const dzExpires      = document.getElementById('dzExpires');
const dzResetBtn     = document.getElementById('dzResetBtn');
const dzErrorMsg     = document.getElementById('dzErrorMsg');
const historyEl      = document.getElementById('history');
const historyList    = document.getElementById('historyList');
const adminSepEl     = document.getElementById('adminSep');
const adminLinkEl    = document.getElementById('adminLink');
const srStatus       = document.getElementById('srStatus');

const _tokenEls     = { fieldEl: tokenFieldEl, indicatorEl: tokenIndicator, hintEl: tokenHintEl };
const _indicatorEls = { fieldEl: tokenFieldEl, indicatorEl: tokenIndicator, nameEl: tokenNameEl };

let selectedFile = null;
let currentUser  = null;
let appConfig    = null;

function setState(state) {
  dropZone.dataset.state = state;
  if (state === 'success') {
    srStatus.textContent = 'Upload complete — your link is ready to share';
  } else if (state === 'error') {
    srStatus.textContent = dzErrorMsg.textContent;
  } else {
    srStatus.textContent = '';
  }
}

async function init() {
  appConfig = await fetch('/config').then(r => r.json());
  const stored = localStorage.getItem('dropit_token');
  if (stored) {
    await checkToken(stored);
  } else {
    showTokenField(_tokenEls,'Contact your admin to get a token');
    populateTTL(false);
    renderHistory([]);
  }
}

async function checkToken(token) {
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) {
      currentUser = await res.json();
      localStorage.setItem(STORAGE_KEY, token);
      showTokenIndicator(_indicatorEls,currentUser.name);
      populateTTL(currentUser.is_admin);
      if (currentUser.is_admin) {
        adminSepEl.style.display  = '';
        adminLinkEl.style.display = '';
      }
      await fetchAndRenderHistory();
    } else if (res.status === 429) {
      showTokenField(_tokenEls, 'Too many requests — wait a minute before trying again');
    } else {
      localStorage.removeItem('dropit_token');
      currentUser = null;
      showTokenField(_tokenEls,'Invalid token — ask your admin for a new one');
      populateTTL(false);
    }
  } catch {
    showTokenField(_tokenEls,'Contact your admin to get a token');
    populateTTL(false);
  }
}


function populateTTL(isAdmin) {
  if (!appConfig) return;
  const ttls = isAdmin ? appConfig.allowed_ttls : appConfig.user_ttls;
  const defaultTtl = isAdmin ? appConfig.default_ttl : appConfig.user_default_ttl;
  while (ttlSelect.firstChild) ttlSelect.removeChild(ttlSelect.firstChild);
  ttls.forEach(t => {
    const opt = document.createElement('option');
    opt.value    = t;
    opt.textContent = t;
    opt.selected = t === defaultTtl;
    ttlSelect.appendChild(opt);
  });
}

tokenForm.addEventListener('submit', e => { e.preventDefault(); saveToken(); });

async function saveToken() {
  const token = tokenInputEl.value.trim();
  if (!token) return;
  await checkToken(token);
}

tokenChangeBtn.addEventListener('click', () => {
  localStorage.removeItem('dropit_token');
  currentUser = null;
  tokenInputEl.value = '';
  adminSepEl.style.display  = 'none';
  adminLinkEl.style.display = 'none';
  showTokenField(_tokenEls);
  populateTTL(false);
});

tokenRegenBtn.addEventListener('click', async () => {
  const token = localStorage.getItem(STORAGE_KEY) || tokenInputEl.value.trim();
  if (!token) return;
  const ok = await showConfirmModal({
    title: 'Regenerate your token?',
    message: 'Your current token stops working everywhere immediately — other devices, the CLI, and other browsers.',
    confirmLabel: 'Regenerate',
    danger: true,
  });
  if (!ok) return;
  try {
    const res = await fetch('/me/regenerate', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(
      res.status === 429
        ? 'Rate limit reached — wait a minute before regenerating your token'
        : (data.detail || `Error ${res.status}`)
    );
    localStorage.setItem('dropit_token', data.token);
    showTokenModal(data.token, {
      title: 'Your new token',
      subtitle: "Copy it now — it won't be shown again. Your old token no longer works.",
    });
  } catch (err) {
    showNoticeModal({ title: 'Could not regenerate', message: err.message });
  }
});

dropZone.addEventListener('click', () => {
  const state = dropZone.dataset.state;
  if (state === 'idle' || state === 'error') fileInput.click();
});
dropZone.addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') &&
      (dropZone.dataset.state === 'idle' || dropZone.dataset.state === 'error')) {
    e.preventDefault();
    fileInput.click();
  }
});
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', e => {
  if (!dropZone.contains(e.relatedTarget)) dropZone.classList.remove('drag-over');
});
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) pick(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) pick(fileInput.files[0]); });

function pick(f) {
  selectedFile = f;
  doUpload();
}

async function doUpload() {
  const token = localStorage.getItem(STORAGE_KEY) || tokenInputEl.value.trim();
  if (!token) {
    dzErrorMsg.textContent = 'No token — enter your API token above';
    setState('error');
    return;
  }

  if (appConfig && selectedFile.size > appConfig.max_upload_size) {
    const mb = (appConfig.max_upload_size / 1_048_576).toFixed(0);
    dzErrorMsg.textContent = `File too large — maximum is ${mb} MB`;
    setState('error');
    return;
  }

  setState('uploading');

  const body = new FormData();
  body.append('file', selectedFile);

  try {
    const res = await fetch(`/upload?ttl=${encodeURIComponent(ttlSelect.value)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(
      res.status === 429
        ? 'Too many uploads — wait a minute before trying again'
        : (data.detail || `Error ${res.status}`)
    );

    dzUrl.textContent     = data.url;
    dzUrl.href            = data.url;
    dzUrl.title           = data.url;
    dzExpires.textContent = data.expires_at
      ? `Expires ${asUtc(data.expires_at).toLocaleString()}`
      : 'Never expires — permanent';
    setState('success');

    if (!currentUser) {
      await checkToken(token);
    } else {
      await fetchAndRenderHistory();
    }
  } catch (err) {
    dzErrorMsg.textContent = err.message;
    setState('error');
  }
}


dzResetBtn.addEventListener('click', e => {
  e.stopPropagation();
  selectedFile = null;
  fileInput.value = '';
  setState('idle');
});

async function fetchAndRenderHistory() {
  const token = localStorage.getItem(STORAGE_KEY);
  if (!token) { renderHistory([]); return; }
  try {
    const res = await fetch('/me/pages', { headers: { Authorization: `Bearer ${token}` } });
    renderHistory(res.ok ? await res.json() : []);
  } catch {
    renderHistory([]);
  }
}

function renderHistory(pages) {
  while (historyList.firstChild) historyList.removeChild(historyList.firstChild);
  historyEl.classList.add('visible');

  if (!pages.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.className = 'history-empty';
    td.colSpan = 3;
    td.textContent = 'No uploads yet';
    tr.appendChild(td);
    historyList.appendChild(tr);
    return;
  }

  pages.forEach(item => {
    const row = document.createElement('tr');
    row.className = 'history-item';

    const name = document.createElement('td');
    name.className   = 'history-filename';
    name.textContent = item.filename;
    name.title       = item.filename;

    const urlCell = document.createElement('td');
    urlCell.className = 'history-url-cell';
    const link = document.createElement('a');
    link.className   = 'history-url';
    link.href        = item.url;
    link.textContent = item.url;
    link.target      = '_blank';
    link.rel         = 'noopener noreferrer';
    urlCell.appendChild(link);

    const exp = document.createElement('td');
    const { text: expText, cls: expCls } = fmtExpiry(item.expires_at);
    exp.className   = `history-exp ${expCls}`;
    exp.textContent = expText;

    row.appendChild(name);
    row.appendChild(urlCell);
    row.appendChild(exp);
    historyList.appendChild(row);
  });
}

init();

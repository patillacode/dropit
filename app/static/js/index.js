const tokenInputEl   = document.getElementById('token');
const tokenFieldEl   = document.getElementById('tokenField');
const tokenIndicator = document.getElementById('tokenIndicator');
const tokenNameEl    = document.getElementById('tokenName');
const tokenHintEl    = document.getElementById('tokenHint');
const tokenChangeBtn = document.getElementById('tokenChangeBtn');
const ttlSelect      = document.getElementById('ttl');
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const dzUrl          = document.getElementById('dzUrl');
const dzCopyBtn      = document.getElementById('dzCopyBtn');
const dzExpires      = document.getElementById('dzExpires');
const dzResetBtn     = document.getElementById('dzResetBtn');
const dzErrorMsg     = document.getElementById('dzErrorMsg');
const historyEl      = document.getElementById('history');
const historyList    = document.getElementById('historyList');
const adminSepEl     = document.getElementById('adminSep');
const adminLinkEl    = document.getElementById('adminLink');

let selectedFile = null;
let currentUser  = null;
let appConfig    = null;

function setState(state) {
  dropZone.dataset.state = state;
}

async function init() {
  appConfig = await fetch('/config').then(r => r.json());
  const stored = localStorage.getItem('dropit_token');
  if (stored) {
    await checkToken(stored);
  } else {
    showField('Contact your admin to get a token');
    populateTTL(false);
  }
  renderHistory();
}

async function checkToken(token) {
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) {
      currentUser = await res.json();
      showIndicator(currentUser.name);
      populateTTL(currentUser.is_admin);
      if (currentUser.is_admin) {
        adminSepEl.style.display  = '';
        adminLinkEl.style.display = '';
      }
    } else {
      localStorage.removeItem('dropit_token');
      currentUser = null;
      showField('Invalid token — ask your admin for a new one');
      populateTTL(false);
    }
  } catch {
    showField('Contact your admin to get a token');
    populateTTL(false);
  }
}

function showField(hint) {
  tokenFieldEl.style.display  = '';
  tokenIndicator.style.display = 'none';
  if (hint) {
    tokenHintEl.textContent    = hint;
    tokenHintEl.style.display  = '';
  } else {
    tokenHintEl.style.display  = 'none';
  }
}

function showIndicator(name) {
  tokenFieldEl.style.display   = 'none';
  tokenIndicator.style.display = '';
  tokenNameEl.textContent      = name;
}

function populateTTL(isAdmin) {
  if (!appConfig) return;
  const ttls = isAdmin ? appConfig.allowed_ttls : appConfig.user_ttls;
  while (ttlSelect.firstChild) ttlSelect.removeChild(ttlSelect.firstChild);
  ttls.forEach(t => {
    const opt = document.createElement('option');
    opt.value    = t;
    opt.textContent = t;
    opt.selected = t === appConfig.default_ttl;
    ttlSelect.appendChild(opt);
  });
}

tokenInputEl.addEventListener('keydown', e => { if (e.key === 'Enter') saveToken(); });
tokenInputEl.addEventListener('blur',    () => { if (tokenInputEl.value.trim()) saveToken(); });

async function saveToken() {
  const token = tokenInputEl.value.trim();
  if (!token) return;
  localStorage.setItem('dropit_token', token);
  await checkToken(token);
}

tokenChangeBtn.addEventListener('click', () => {
  localStorage.removeItem('dropit_token');
  currentUser = null;
  tokenInputEl.value = '';
  adminSepEl.style.display  = 'none';
  adminLinkEl.style.display = 'none';
  showField();
  populateTTL(false);
});

dropZone.addEventListener('click', () => {
  const state = dropZone.dataset.state;
  if (state === 'idle' || state === 'error') fileInput.click();
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

function getToken() {
  return localStorage.getItem('dropit_token') || tokenInputEl.value.trim();
}

async function doUpload() {
  const token = getToken();
  if (!token) {
    dzErrorMsg.textContent = 'No token — enter your API token above';
    setState('error');
    return;
  }

  setState('uploading');

  if (!currentUser) localStorage.setItem('dropit_token', token);

  const body = new FormData();
  body.append('file', selectedFile);

  try {
    const res = await fetch(`/upload?ttl=${encodeURIComponent(ttlSelect.value)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    dzUrl.textContent     = data.url;
    dzUrl.title           = data.url;
    dzExpires.textContent = data.expires_at
      ? `Expires ${new Date(data.expires_at).toLocaleString()}`
      : 'Never expires — permanent';
    setState('success');

    addToHistory(data.url, selectedFile.name, data.expires_at);
    renderHistory();

    if (!currentUser) await checkToken(token);
  } catch (err) {
    dzErrorMsg.textContent = err.message;
    setState('error');
  }
}

dzCopyBtn.addEventListener('click', e => {
  e.stopPropagation();
  navigator.clipboard.writeText(dzUrl.textContent).then(() => {
    dzCopyBtn.textContent = 'Copied!';
    setTimeout(() => { dzCopyBtn.textContent = 'Copy'; }, 2000);
  });
});

dzResetBtn.addEventListener('click', e => {
  e.stopPropagation();
  selectedFile = null;
  fileInput.value = '';
  setState('idle');
});

const HISTORY_KEY = 'dropit_history';

function addToHistory(url, filename, expires_at) {
  let hist = [];
  try { hist = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { }
  hist.unshift({ url, filename, expires_at });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(hist.slice(0, 5)));
}

function renderHistory() {
  const now  = Date.now();
  let hist   = [];
  try { hist = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { }
  const alive = hist.filter(item => !item.expires_at || new Date(item.expires_at).getTime() > now);
  if (!alive.length) { historyEl.classList.remove('visible'); return; }

  while (historyList.firstChild) historyList.removeChild(historyList.firstChild);
  alive.forEach(item => {
    const row  = document.createElement('div');
    row.className = 'history-item';

    const name = document.createElement('span');
    name.className   = 'history-filename';
    name.textContent = item.filename;
    name.title       = item.filename;

    const link = document.createElement('a');
    link.className  = 'history-url';
    link.href       = item.url;
    link.textContent = item.url;
    link.target     = '_blank';
    link.rel        = 'noopener noreferrer';

    const exp = document.createElement('span');
    exp.className   = 'history-exp';
    exp.textContent = item.expires_at ? new Date(item.expires_at).toLocaleDateString() : 'permanent';

    row.appendChild(name);
    row.appendChild(link);
    row.appendChild(exp);
    historyList.appendChild(row);
  });
  historyEl.classList.add('visible');
}

init();

const tokenInputEl   = document.getElementById('token');
const tokenFieldEl   = document.getElementById('tokenField');
const tokenIndicator = document.getElementById('tokenIndicator');
const tokenNameEl    = document.getElementById('tokenName');
const tokenHintEl    = document.getElementById('tokenHint');
const tokenChangeBtn = document.getElementById('tokenChangeBtn');
const ttlSelect      = document.getElementById('ttl');
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const fileNameEl     = document.getElementById('fileName');
const uploadBtn      = document.getElementById('uploadBtn');
const resultEl       = document.getElementById('result');
const resultUrl      = document.getElementById('resultUrl');
const copyBtn        = document.getElementById('copyBtn');
const resultExp      = document.getElementById('resultExpires');
const errorEl        = document.getElementById('errorEl');
const historyEl      = document.getElementById('history');
const historyList    = document.getElementById('historyList');
const adminSepEl     = document.getElementById('adminSep');
const adminLinkEl    = document.getElementById('adminLink');

let selectedFile = null;
let currentUser  = null;
let appConfig    = null;

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
  sync();
}

function showIndicator(name) {
  tokenFieldEl.style.display   = 'none';
  tokenIndicator.style.display = '';
  tokenNameEl.textContent      = name;
  sync();
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
tokenInputEl.addEventListener('input',   sync);

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

dropZone.addEventListener('click',    () => fileInput.click());
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
  fileNameEl.textContent = f.name;
  sync();
}

function getToken() {
  return localStorage.getItem('dropit_token') || tokenInputEl.value.trim();
}

function sync() {
  const indicatorShown = tokenIndicator.style.display !== 'none';
  const hasToken = indicatorShown ? (currentUser !== null) : tokenInputEl.value.trim().length > 0;
  uploadBtn.disabled = !selectedFile || !hasToken;
}

sync();

uploadBtn.addEventListener('click', async () => {
  errorEl.classList.remove('visible');
  resultEl.classList.remove('visible');
  uploadBtn.disabled  = true;
  uploadBtn.textContent = 'Uploading...';

  const token = getToken();
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

    resultUrl.textContent = data.url;
    resultUrl.title       = data.url;
    resultExp.textContent = data.expires_at
      ? `Expires ${new Date(data.expires_at).toLocaleString()}`
      : 'Never expires — permanent';
    resultEl.classList.add('visible');

    addToHistory(data.url, selectedFile.name, data.expires_at);
    renderHistory();

    if (!currentUser) await checkToken(token);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add('visible');
  } finally {
    uploadBtn.textContent = 'Upload';
    sync();
  }
});

copyBtn.addEventListener('click', () => {
  navigator.clipboard.writeText(resultUrl.textContent).then(() => {
    copyBtn.textContent = 'Copied!';
    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
  });
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

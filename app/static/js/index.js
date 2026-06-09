import { showTokenField, showTokenIndicator } from '/static/js/token-shared.js';
import { showTokenModal, showConfirmModal, showNoticeModal } from '/static/js/token-modal.js';
import { asUtc } from '/static/js/utils.js';
import { getToken, setToken, clearToken, initNav } from '/static/js/auth.js';

const tokenInputEl      = document.getElementById('tokenInput');
const tokenFieldEl      = document.getElementById('tokenField');
const tokenIndicator    = document.getElementById('tokenIndicator');
const tokenNameEl       = document.getElementById('tokenName');
const tokenHintEl       = document.getElementById('tokenHint');
const tokenChangeBtn    = document.getElementById('tokenChangeBtn');
const tokenRegenBtn     = document.getElementById('tokenRegenBtn');
const tokenForm         = document.getElementById('tokenForm');
const ttlSelect         = document.getElementById('ttl');
const dropZone          = document.getElementById('dropZone');
const fileInput         = document.getElementById('fileInput');
const dzUrl             = document.getElementById('dzUrl');
const dzExpires         = document.getElementById('dzExpires');
const dzResetBtn        = document.getElementById('dzResetBtn');
const dzCopyBtn         = document.getElementById('dzCopyBtn');
const dzErrorMsg        = document.getElementById('dzErrorMsg');
const srStatus          = document.getElementById('srStatus');
const collectionField   = document.getElementById('collectionField');
const collectionSelect  = document.getElementById('collectionSelect');
const newCollectionInput = document.getElementById('newCollectionInput');
const noCollsHint       = document.getElementById('noCollsHint');
const breakGlassHint    = document.getElementById('breakGlassHint');

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

async function onLogin(user) {
  currentUser = user;
  showTokenIndicator(_indicatorEls, user.name);
  populateTTL(user.is_admin);
  const token = getToken();
  try {
    const res = await fetch('/collections', { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) {
      collectionField.style.display = 'none';
      noCollsHint.style.display = 'none';
      breakGlassHint.style.display = '';
    } else if (res.ok) {
      const colls = await res.json();
      breakGlassHint.style.display = 'none';
      if (colls.length === 0) {
        collectionField.style.display = 'none';
        noCollsHint.style.display = '';
      } else {
        noCollsHint.style.display = 'none';
        collectionField.style.display = '';
        populateCollectionSelect(colls);
      }
    }
  } catch {
    collectionField.style.display = 'none';
  }
}

function populateCollectionSelect(colls) {
  collectionSelect.innerHTML = '';
  const noneOpt = document.createElement('option');
  noneOpt.value = '';
  noneOpt.textContent = '— no collection —';
  collectionSelect.appendChild(noneOpt);
  for (const c of colls) {
    const opt = document.createElement('option');
    opt.value = c.name;
    opt.textContent = c.name;
    collectionSelect.appendChild(opt);
  }
  const newOpt = document.createElement('option');
  newOpt.value = '__new__';
  newOpt.textContent = '＋ New collection…';
  collectionSelect.appendChild(newOpt);
  newCollectionInput.style.display = 'none';
}

function onLogout() {
  currentUser = null;
  collectionField.style.display = 'none';
  noCollsHint.style.display = 'none';
  breakGlassHint.style.display = 'none';
  newCollectionInput.style.display = 'none';
  showTokenField(_tokenEls);
  populateTTL(false);
}

async function init() {
  appConfig = await fetch('/config').then(r => r.json());
  populateTTL(false);
  if (!getToken()) showTokenField(_tokenEls, 'Contact your admin to get a token');
  initNav({ onLogin, onLogout });
}

async function checkToken(token) {
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) {
      const user = await res.json();
      setToken(token);
      await onLogin(user);
    } else if (res.status === 429) {
      showTokenField(_tokenEls, 'Too many requests — wait a minute before trying again');
    } else {
      clearToken();
      currentUser = null;
      showTokenField(_tokenEls, 'Invalid token — ask your admin for a new one');
      populateTTL(false);
    }
  } catch {
    showTokenField(_tokenEls, 'Contact your admin to get a token');
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
    opt.value = t;
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

collectionSelect.addEventListener('change', () => {
  const isNew = collectionSelect.value === '__new__';
  newCollectionInput.style.display = isNew ? '' : 'none';
  if (isNew) newCollectionInput.focus();
});

tokenChangeBtn.addEventListener('click', () => {
  clearToken();
  currentUser = null;
  tokenInputEl.value = '';
  collectionField.style.display = 'none';
  noCollsHint.style.display = 'none';
  breakGlassHint.style.display = 'none';
  newCollectionInput.style.display = 'none';
  showTokenField(_tokenEls);
  populateTTL(false);
});

tokenRegenBtn.addEventListener('click', async () => {
  const token = getToken() || tokenInputEl.value.trim();
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
    setToken(data.token);
    showTokenModal(data.token, {
      title: 'Your new token',
      subtitle: "Copy it now — it won't be shown again. Your old token no longer works.",
    });
  } catch (err) {
    showNoticeModal({ title: 'Could not regenerate', message: err.message });
  }
});

dzCopyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(dzUrl.href);
    dzCopyBtn.textContent = 'Copied!';
    setTimeout(() => { dzCopyBtn.textContent = 'Copy URL'; }, 1500);
  } catch {
    // clipboard API unavailable
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
  const token = getToken() || tokenInputEl.value.trim();
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
    let collectionValue = '';
    if (collectionSelect && collectionField.style.display !== 'none') {
      if (collectionSelect.value === '__new__') {
        collectionValue = newCollectionInput.value.trim();
      } else {
        collectionValue = collectionSelect.value;
      }
    }
    const collectionParam = collectionValue ? `&collection=${encodeURIComponent(collectionValue)}` : '';
    const res = await fetch(`/upload?ttl=${encodeURIComponent(ttlSelect.value)}${collectionParam}`, {
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

    dzUrl.textContent = data.url;
    dzUrl.href        = data.url;
    dzUrl.title       = data.url;
    dzExpires.textContent = data.expires_at
      ? `Expires ${asUtc(data.expires_at).toLocaleString()}`
      : 'Never expires — permanent';
    setState('success');

    if (!currentUser) await checkToken(token);
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

init();

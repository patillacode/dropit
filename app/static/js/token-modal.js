// Shared modals: show-once token reveal, confirmation, and notice.
function mkBtn(label, cls) {
  const b = document.createElement('button');
  b.className = cls;
  b.textContent = label;
  return b;
}

function buildModal({ title, bodyNodes = [], actions = [], onDismiss }) {
  const overlay = document.createElement('div');
  overlay.className = 'token-modal-overlay';

  const modal = document.createElement('div');
  modal.className = 'token-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');

  const h = document.createElement('h2');
  h.className = 'token-modal-title';
  h.textContent = title;
  modal.appendChild(h);

  bodyNodes.forEach(n => modal.appendChild(n));

  const act = document.createElement('div');
  act.className = 'token-modal-actions';
  actions.forEach(b => act.appendChild(b));
  modal.appendChild(act);

  overlay.appendChild(modal);

  const close = () => overlay.remove();
  overlay.addEventListener('click', e => {
    if (e.target === overlay) {
      close();
      if (onDismiss) onDismiss();
    }
  });

  document.body.appendChild(overlay);
  return { overlay, close };
}

async function copyToken(codeEl, btn, token) {
  let copied = false;
  if (navigator.clipboard && window.isSecureContext) {
    try { await navigator.clipboard.writeText(token); copied = true; } catch { /* fall through */ }
  }
  if (!copied) {
    const range = document.createRange();
    range.selectNodeContents(codeEl);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    try { copied = document.execCommand('copy'); } catch { copied = false; }
    sel.removeAllRanges();
  }
  btn.textContent = copied ? 'Copied!' : 'Copy failed';
}

export function showTokenModal(token, opts) {
  const { title = 'New token', subtitle = "Copy this token — it won't be shown again." } = opts || {};

  const sub = document.createElement('p');
  sub.className = 'token-modal-sub';
  sub.textContent = subtitle;

  const codeEl = document.createElement('code');
  codeEl.className = 'token-modal-token';
  codeEl.textContent = token;

  const copyBtn = mkBtn('Copy', 'btn btn--accent');
  const closeBtn = mkBtn('Done', 'btn');

  const { close } = buildModal({ title, bodyNodes: [sub, codeEl], actions: [copyBtn, closeBtn] });
  copyBtn.addEventListener('click', () => copyToken(codeEl, copyBtn, token));
  closeBtn.addEventListener('click', close);
}

export function showConfirmModal(opts) {
  const {
    title = 'Are you sure?',
    message = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    danger = false,
  } = opts || {};

  return new Promise(resolve => {
    const msg = document.createElement('p');
    msg.className = 'token-modal-sub';
    msg.textContent = message;

    const cancelBtn = mkBtn(cancelLabel, 'btn');
    const confirmBtn = mkBtn(confirmLabel, danger ? 'btn btn--danger' : 'btn btn--accent');

    let done = false;
    const finish = value => {
      if (done) return;
      done = true;
      close();
      resolve(value);
    };

    const { close } = buildModal({
      title,
      bodyNodes: [msg],
      actions: [cancelBtn, confirmBtn],
      onDismiss: () => finish(false),
    });

    cancelBtn.addEventListener('click', () => finish(false));
    confirmBtn.addEventListener('click', () => finish(true));
  });
}

export function showNoticeModal(opts) {
  const { title = 'Notice', message = '' } = opts || {};
  const msg = document.createElement('p');
  msg.className = 'token-modal-sub';
  msg.textContent = message;
  const okBtn = mkBtn('OK', 'btn');
  const { close } = buildModal({ title, bodyNodes: [msg], actions: [okBtn] });
  okBtn.addEventListener('click', close);
}

// Shared modals: show-once token reveal, confirmation, and notice.
import { copyToClipboard } from '/static/js/utils.js';

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

  for (const n of bodyNodes) modal.appendChild(n);

  const act = document.createElement('div');
  act.className = 'token-modal-actions';
  for (const b of actions) act.appendChild(b);
  modal.appendChild(act);

  overlay.appendChild(modal);

  const close = () => overlay.remove();
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      close();
      if (onDismiss) onDismiss();
    }
  });

  document.body.appendChild(overlay);
  return { overlay, close };
}

async function copyToken(btn, token) {
  const copied = await copyToClipboard(token);
  btn.textContent = copied ? 'Copied!' : 'Copy failed';
}

export function showTokenModal(token, opts) {
  const { title = 'New token', subtitle = "Copy this token — it won't be shown again." } =
    opts || {};

  const sub = document.createElement('p');
  sub.className = 'token-modal-sub';
  sub.textContent = subtitle;

  const codeEl = document.createElement('code');
  codeEl.className = 'token-modal-token';
  codeEl.textContent = token;

  const copyBtn = mkBtn('Copy', 'btn btn--accent');
  const closeBtn = mkBtn('Done', 'btn');

  const { close } = buildModal({ title, bodyNodes: [sub, codeEl], actions: [copyBtn, closeBtn] });
  copyBtn.addEventListener('click', () => copyToken(copyBtn, token));
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

  return new Promise((resolve) => {
    const msg = document.createElement('p');
    msg.className = 'token-modal-sub';
    msg.textContent = message;

    const cancelBtn = mkBtn(cancelLabel, 'btn');
    const confirmBtn = mkBtn(confirmLabel, danger ? 'btn btn--danger' : 'btn btn--accent');

    let done = false;
    const finish = (value) => {
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

export function showInputModal(opts) {
  const {
    title = '',
    message = '',
    defaultValue = '',
    confirmLabel = 'Save',
    cancelLabel = 'Cancel',
    placeholder = '',
  } = opts || {};

  return new Promise((resolve) => {
    const nodes = [];
    if (message) {
      const msg = document.createElement('p');
      msg.className = 'token-modal-sub';
      msg.textContent = message;
      nodes.push(msg);
    }

    const input = document.createElement('input');
    input.type = 'text';
    input.value = defaultValue;
    input.placeholder = placeholder;
    input.style.marginBottom = '0.25rem';
    nodes.push(input);

    const cancelBtn = mkBtn(cancelLabel, 'btn');
    const confirmBtn = mkBtn(confirmLabel, 'btn btn--accent');

    let done = false;
    const finish = (value) => {
      if (done) return;
      done = true;
      close();
      resolve(value);
    };

    const { close } = buildModal({
      title,
      bodyNodes: nodes,
      actions: [cancelBtn, confirmBtn],
      onDismiss: () => finish(null),
    });

    setTimeout(() => {
      input.focus();
      input.select();
    }, 0);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        finish(input.value.trim() || null);
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        finish(null);
      }
    });
    cancelBtn.addEventListener('click', () => finish(null));
    confirmBtn.addEventListener('click', () => finish(input.value.trim() || null));
  });
}

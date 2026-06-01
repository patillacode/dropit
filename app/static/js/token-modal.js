// Shared show-once token modal. Tokens are never retrievable again, so this is
// the only chance to copy them.
function showTokenModal(token, opts) {
  const { title = 'New token', subtitle = "Copy this token — it won't be shown again." } = opts || {};

  const overlay = document.createElement('div');
  overlay.className = 'token-modal-overlay';

  const modal = document.createElement('div');
  modal.className = 'token-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');

  const h = document.createElement('h2');
  h.className = 'token-modal-title';
  h.textContent = title;

  const sub = document.createElement('p');
  sub.className = 'token-modal-sub';
  sub.textContent = subtitle;

  const tokenBox = document.createElement('code');
  tokenBox.className = 'token-modal-token';
  tokenBox.textContent = token;

  const actions = document.createElement('div');
  actions.className = 'token-modal-actions';

  const copyBtn = document.createElement('button');
  copyBtn.className = 'token-modal-copy';
  copyBtn.textContent = 'Copy';

  const closeBtn = document.createElement('button');
  closeBtn.className = 'token-modal-close';
  closeBtn.textContent = 'Done';

  copyBtn.addEventListener('click', async () => {
    let copied = false;
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(token); copied = true; } catch { /* fall through */ }
    }
    if (!copied) {
      const range = document.createRange();
      range.selectNodeContents(tokenBox);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      try { copied = document.execCommand('copy'); } catch { copied = false; }
      sel.removeAllRanges();
    }
    copyBtn.textContent = copied ? 'Copied!' : 'Copy failed';
  });

  const close = () => overlay.remove();
  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

  actions.appendChild(copyBtn);
  actions.appendChild(closeBtn);
  modal.appendChild(h);
  modal.appendChild(sub);
  modal.appendChild(tokenBox);
  modal.appendChild(actions);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

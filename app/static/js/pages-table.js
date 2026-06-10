import { showConfirmModal } from '/static/js/token-modal.js';
import { fmtDate, fmtExpiry, fmtSize } from '/static/js/utils.js';

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

export function renderPagesTable(
  pages,
  { tableWrap, emptyEl, errorEl, showUploader = false, deletePage },
) {
  const existing = tableWrap.querySelector('table');
  if (existing) existing.remove();

  tableWrap.classList.remove('visible');
  emptyEl.classList.remove('visible');

  if (!pages.length) {
    emptyEl.classList.add('visible');
    return;
  }

  const colCount = showUploader ? 5 : 4;
  const table = document.createElement('table');

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const headers = ['URL', 'Expires in', ...(showUploader ? ['Uploaded by'] : []), 'Collection'];
  for (const label of headers) {
    const th = document.createElement('th');
    th.textContent = label;
    headerRow.appendChild(th);
  }
  const thAct = document.createElement('th');
  thAct.className = 'th-actions';
  headerRow.appendChild(thAct);
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  for (const p of pages) {
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

    const { text: expText, cls: expCls } = fmtExpiry(p.expires_at);
    const tdExp = document.createElement('td');
    tdExp.className = `td-expires ${expCls}`;
    tdExp.textContent = expText;

    tr.append(tdUrl, tdExp);

    if (showUploader) {
      const tdUp = document.createElement('td');
      tdUp.className = 'td-uploader';
      tdUp.textContent = p.user_name || p.token_hint || '—';
      tr.appendChild(tdUp);
    }

    const tdColl = document.createElement('td');
    tdColl.className = 'td-collection';
    if (p.collection_name) {
      const badge = document.createElement('span');
      badge.className = 'coll-badge';
      badge.textContent = p.collection_name;
      tdColl.appendChild(badge);
    } else {
      tdColl.textContent = '—';
    }

    const tdAct = document.createElement('td');
    tdAct.className = 'page-actions';

    const detailsBtn = document.createElement('button');
    detailsBtn.className = 'btn';
    detailsBtn.textContent = 'Details';

    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn--danger';
    delBtn.textContent = 'Delete';

    tdAct.append(detailsBtn, delBtn);
    tr.append(tdColl, tdAct);

    const detailTr = document.createElement('tr');
    detailTr.className = 'page-detail';
    const detailTd = document.createElement('td');
    detailTd.colSpan = colCount;
    const grid = document.createElement('div');
    grid.className = 'detail-grid';
    grid.appendChild(detailItem('File', p.filename));
    grid.appendChild(detailItem('Uploaded', p.created_at ? fmtDate(p.created_at) : '—'));
    grid.appendChild(detailItem('Expires', p.expires_at ? fmtDate(p.expires_at) : 'never'));
    grid.appendChild(detailItem('Size', fmtSize(p.file_size)));
    detailTd.appendChild(grid);
    detailTr.appendChild(detailTd);

    detailsBtn.addEventListener('click', () => {
      const open = detailTr.classList.toggle('open');
      detailsBtn.textContent = open ? 'Hide' : 'Details';
    });

    delBtn.addEventListener('click', async () => {
      const ok = await showConfirmModal({
        title: 'Delete this page?',
        message: 'The file and its link will be permanently removed. This cannot be undone.',
        confirmLabel: 'Delete',
        danger: true,
      });
      if (!ok) return;
      try {
        await deletePage(p);
        tr.remove();
        detailTr.remove();
        if (!tbody.querySelector('.page-row')) {
          tableWrap.classList.remove('visible');
          emptyEl.classList.add('visible');
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = err.message;
          errorEl.classList.add('visible');
        }
      }
    });

    tbody.append(tr, detailTr);
  }

  table.appendChild(tbody);
  tableWrap.appendChild(table);
  tableWrap.classList.add('visible');
}

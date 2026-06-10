export function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function fmtSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export function asUtc(iso) {
  if (!iso) return null;
  const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
  return new Date(normalized);
}

export function fmtExpiry(isoStr) {
  if (!isoStr) return { text: 'permanent', cls: 'exp-permanent' };
  const diff = new Date(isoStr) - Date.now();
  if (diff <= 0) return { text: 'Expired', cls: 'exp-expired' };
  const mins = Math.floor(diff / 60000);
  const hrs  = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  const text = days >= 1 ? `${days} day${days !== 1 ? 's' : ''}`
             : hrs  >= 1 ? `${hrs} hour${hrs !== 1 ? 's' : ''}`
             : mins >= 1 ? `${mins} minute${mins !== 1 ? 's' : ''}`
             : '< 1 minute';
  return { text, cls: 'exp-timed' };
}

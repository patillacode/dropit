import { authHeaders } from '/static/js/auth.js';

// Thin fetch wrapper: attaches the bearer token, JSON-encodes `json`, parses the
// response, and throws a friendly Error (with .status and .data) on failure.
export async function apiFetch(url, { method = 'GET', json, headers = {}, ...rest } = {}) {
  const opts = { method, headers: authHeaders(headers), ...rest };
  if (json !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(json);
  }
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message =
      res.status === 429
        ? 'Too many requests — wait a minute and try again'
        : data.detail || `Error ${res.status}`;
    const err = new Error(message);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

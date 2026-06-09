export const STORAGE_KEY = 'dropit_token';

export function getToken() {
  return localStorage.getItem(STORAGE_KEY) || '';
}

export function setToken(t) {
  localStorage.setItem(STORAGE_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(STORAGE_KEY);
}

export async function fetchMe(token) {
  try {
    const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export function initNav({ onLogin, onLogout } = {}) {
  const navAdminEl = document.querySelector('.nav-admin');

  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    const active = href === '/' ? path === '/' : path === href || path.startsWith(href + '/');
    link.classList.toggle('nav-link--active', active);
  });

  const token = getToken();
  if (token) {
    fetchMe(token).then(user => {
      if (user) {
        if (navAdminEl) navAdminEl.style.display = user.is_admin ? '' : 'none';
        if (onLogin) onLogin(user);
      } else {
        clearToken();
        if (navAdminEl) navAdminEl.style.display = 'none';
        if (onLogout) onLogout();
      }
    });
  } else {
    if (navAdminEl) navAdminEl.style.display = 'none';
  }
}

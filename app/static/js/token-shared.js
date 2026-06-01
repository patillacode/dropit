export function getToken(storageKey) {
  return localStorage.getItem(storageKey) || '';
}

export function showTokenField({ fieldEl, indicatorEl, hintEl }, hint) {
  fieldEl.style.display = '';
  indicatorEl.style.display = 'none';
  if (hint) {
    hintEl.textContent = hint;
    hintEl.style.display = '';
  } else {
    hintEl.style.display = 'none';
  }
}

export function showTokenIndicator({ fieldEl, indicatorEl, nameEl }, name) {
  fieldEl.style.display = 'none';
  indicatorEl.style.display = '';
  nameEl.textContent = name;
}

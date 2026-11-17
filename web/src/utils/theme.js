// Theme preference ('system' | 'light' | 'dark'), resolved onto <html data-theme>.
// The preference is a per-browser convenience; storage may be unavailable.
const KEY = 'genesis.theme';
const media = window.matchMedia('(prefers-color-scheme: light)');

export function getThemePreference() {
  try {
    const value = localStorage.getItem(KEY);
    return ['light', 'dark'].includes(value) ? value : 'system';
  } catch {
    return 'system';
  }
}

function apply(preference) {
  const theme = preference === 'system' ? (media.matches ? 'light' : 'dark') : preference;
  document.documentElement.dataset.theme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', theme === 'light' ? '#f6f7f9' : '#0b0d12');
}

export function setThemePreference(preference) {
  try {
    if (preference === 'system') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, preference);
  } catch {
    /* keep it for this page only */
  }
  apply(preference);
}

export function initTheme() {
  apply(getThemePreference());
  media.addEventListener('change', () => apply(getThemePreference()));
}
